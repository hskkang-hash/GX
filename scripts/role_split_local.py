# -*- coding: utf-8 -*-
"""superuser 역할 분리 — 실행 스크립트 (W0-16 (c) · D-243 · D-247).

무엇을 하나
    ① 전역 역할 `gaion_global_admin` 을 만들고 **GAION 운영 테넌트 계정에만** 준다.
    ② 고객 테넌트마다 `tenant_admin_<group_id>` 대체역할을 만들고, 그 테넌트의
       레거시 `superuser` 보유자에게 **먼저 준다** (무중단 · D-243 ②).
    ③ (`--revoke`) 검증이 끝난 계정에서 레거시 `superuser` 역할을 뗀다.

무엇을 하지 않나
    · 운영 DB·운영 서버에 손대지 않는다. **DB 이름으로 막는다** (§가드).
    · dj-core 를 수정하지 않는다 (§0.4 · 금지 #10).
    · 기본 동작은 **dry-run 리포트**다. `--apply` 없이는 한 행도 쓰지 않는다 (D-209).

권한의 실체
    `superuser` 역할은 메뉴/탭 권한 행(menu_rolemenu · menu_roletab)도 갖고 있지만,
    실제로는 `core/role/permission.py:475` 가 **검사 자체를 건너뛴다.** 그래서 역할을
    떼면 그 계정은 권한 행이 없는 상태가 된다 — 화면이 통째로 사라진다.
    대체역할은 그 사고를 막으려고 **superuser 역할의 권한 행을 그대로 복제**한다.
    달라지는 것은 하나뿐이다: **우회가 없으므로 테넌트 필터가 실제로 걸린다.**

사용법
    python scripts/role_split_local.py                       # dry-run 리포트 (읽기만)
    python scripts/role_split_local.py --apply               # 역할 생성 + 대체역할 부여
    python scripts/role_split_local.py --apply --revoke 4    # 그 위에 user id 4 의 레거시 회수
    python scripts/role_split_local.py --apply --revoke all  # 고객 테넌트 보유자 전원 회수

    --global-groups 5,7   GAION 운영 테넌트 목록 (기본 5,7). 이 테넌트의 보유자는
                          대체역할이 아니라 전역 역할을 받는다. 되돌리는 knob 은 이것이다.
"""
from __future__ import annotations

import argparse
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings  # noqa: E402
from django.db import connection, transaction  # noqa: E402

from common.tenant_roles import LEGACY_GLOBAL_ROLE_CODE, tenant_admin_role_code  # noqa: E402

# --- 가드 -------------------------------------------------------------------
# database_guardianx 는 운영 복제본이다 (D-245: 무변경 확인만). 쓰기를 막는다.
PROTECTED_DBS = {"database_guardianx"}


def db_name() -> str:
    return connection.settings_dict["NAME"]


def guard_write() -> None:
    name = db_name()
    if name in PROTECTED_DBS:
        raise SystemExit(
            "거부: '%s' 은 운영 복제본이다 (D-245). 쓰기는 별도 복제본에서만 한다.\n"
            "  docker exec postgres psql -U postgres -c "
            '"CREATE DATABASE rolesplit_guardianx TEMPLATE %s"\n'
            "  docker exec -e DB_NAME=rolesplit_guardianx gx-shell "
            "python scripts/role_split_local.py --apply" % (name, name)
        )


# --- 조회 -------------------------------------------------------------------
def fetch(sql: str, params: tuple = ()) -> list[tuple]:
    with connection.cursor() as c:
        c.execute(sql, params)
        return c.fetchall()


def legacy_holders() -> list[tuple]:
    """레거시 superuser 역할 보유자 — (user_id, username, group_id, group_name)."""
    return fetch(
        """
        SELECT u.id, u.username, l.group_id, g.name
        FROM user_coreuser_roles ur
        JOIN user_coreuser u ON u.id = ur.coreuser_id
        LEFT JOIN user_profile_link l ON l.user_id = u.id AND l.deleted IS NULL
        LEFT JOIN user_usergroup g ON g.id = l.group_id
        WHERE ur.role_id = (SELECT id FROM role_role WHERE code = %s AND deleted IS NULL)
        ORDER BY l.group_id NULLS FIRST, u.id
        """,
        (LEGACY_GLOBAL_ROLE_CODE,),
    )


def role_id(code: str):
    rows = fetch("SELECT id FROM role_role WHERE code = %s AND deleted IS NULL", (code,))
    return rows[0][0] if rows else None


def grant_counts(rid: int) -> tuple[int, int]:
    menus = fetch("SELECT count(*) FROM menu_rolemenu WHERE role_id = %s AND deleted IS NULL", (rid,))[0][0]
    tabs = fetch("SELECT count(*) FROM menu_roletab WHERE role_id = %s AND deleted IS NULL", (rid,))[0][0]
    return menus, tabs


# --- 쓰기 -------------------------------------------------------------------
def ensure_role(code: str, name: str, group_id, description: str) -> int:
    existing = role_id(code)
    if existing:
        return existing
    with connection.cursor() as c:
        c.execute(
            """
            INSERT INTO role_role (role_name, code, description, is_default, group_id,
                                   created_on, modified_on, deleted_by_cascade)
            VALUES (%s, %s, %s, false, %s, now(), now(), false)
            RETURNING id
            """,
            (name, code, description, group_id),
        )
        return c.fetchone()[0]


def clone_grants(src_role: int, dst_role: int, group_id) -> tuple[int, int]:
    """superuser 역할의 메뉴/탭 권한 행을 대체역할로 복제한다 (이미 있는 것은 건너뛴다)."""
    with connection.cursor() as c:
        c.execute(
            """
            INSERT INTO menu_rolemenu (menu_id, role_id, group_id, permit_read, permit_create,
                                       permit_update, permit_delete, created_on, modified_on,
                                       deleted_by_cascade)
            SELECT s.menu_id, %s, %s, s.permit_read, s.permit_create, s.permit_update,
                   s.permit_delete, now(), now(), false
            FROM menu_rolemenu s
            WHERE s.role_id = %s AND s.deleted IS NULL
              AND NOT EXISTS (SELECT 1 FROM menu_rolemenu d
                              WHERE d.role_id = %s AND d.menu_id = s.menu_id)
            """,
            (dst_role, group_id, src_role, dst_role),
        )
        menus = c.rowcount
        c.execute(
            """
            INSERT INTO menu_roletab (tab_id, role_id, group_id, permit_read, permit_create,
                                      permit_update, permit_delete, created_on, modified_on,
                                      deleted_by_cascade)
            SELECT s.tab_id, %s, %s, s.permit_read, s.permit_create, s.permit_update,
                   s.permit_delete, now(), now(), false
            FROM menu_roletab s
            WHERE s.role_id = %s AND s.deleted IS NULL
              AND NOT EXISTS (SELECT 1 FROM menu_roletab d
                              WHERE d.role_id = %s AND d.tab_id = s.tab_id)
            """,
            (dst_role, group_id, src_role, dst_role),
        )
        tabs = c.rowcount
    return menus, tabs


def assign(user_id: int, rid: int) -> bool:
    with connection.cursor() as c:
        c.execute(
            """
            INSERT INTO user_coreuser_roles (coreuser_id, role_id)
            SELECT %s, %s
            WHERE NOT EXISTS (SELECT 1 FROM user_coreuser_roles
                              WHERE coreuser_id = %s AND role_id = %s)
            """,
            (user_id, rid, user_id, rid),
        )
        return c.rowcount > 0


def revoke(user_id: int, rid: int) -> bool:
    with connection.cursor() as c:
        c.execute("DELETE FROM user_coreuser_roles WHERE coreuser_id = %s AND role_id = %s",
                  (user_id, rid))
        return c.rowcount > 0


# --- 본체 -------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제로 쓴다 (없으면 dry-run)")
    ap.add_argument("--revoke", default="", help="all 또는 user id 목록(쉼표) — 레거시 역할 회수")
    ap.add_argument("--global-groups", default="5,7", help="GAION 운영 테넌트 group id 목록")
    args = ap.parse_args()

    global_groups = {int(x) for x in args.global_groups.split(",") if x.strip()}
    global_code = (getattr(settings, "TENANT_GLOBAL_ADMIN_ROLE_CODES", []) or ["gaion_global_admin"])[0]

    src = role_id(LEGACY_GLOBAL_ROLE_CODE)
    if src is None:
        raise SystemExit("'%s' 역할이 없다 — 대상 DB 를 확인하라." % LEGACY_GLOBAL_ROLE_CODE)
    src_menus, src_tabs = grant_counts(src)

    holders = legacy_holders()
    by_group: dict = {}
    for uid, uname, gid, gname in holders:
        by_group.setdefault(gid, []).append((uid, uname, gname))

    mode = "APPLY" if args.apply else "DRY-RUN"
    print("[%s] db=%s  legacy_role=%s(id=%s) grants: menus=%d tabs=%d"
          % (mode, db_name(), LEGACY_GLOBAL_ROLE_CODE, src, src_menus, src_tabs))
    print("[%s] 전역 테넌트=%s  전역 역할 코드=%s" % (mode, sorted(global_groups), global_code))
    print("[%s] 레거시 보유자 %d명 / %d개 테넌트" % (mode, len(holders), len(by_group)))

    for gid in sorted(by_group, key=lambda x: (x is None, x)):
        users = by_group[gid]
        gname = users[0][2]
        if gid in global_groups:
            print("  group %s (%s) — GAION 운영: %d명 → 역할 '%s' 부여"
                  % (gid, gname, len(users), global_code))
        else:
            print("  group %s (%s) — 고객 테넌트: %d명 → 역할 '%s' 신설 + 부여"
                  % (gid, gname, len(users), tenant_admin_role_code(gid)))
        for uid, uname, _ in users:
            print("      · id=%s %s" % (uid, uname))

    if not args.apply:
        print("\n[%s] 한 행도 쓰지 않았다. 적용하려면 --apply (D-209)." % mode)
        return 0

    guard_write()
    revoke_targets = set()
    if args.revoke == "all":
        revoke_targets = {u for gid, us in by_group.items() if gid not in global_groups
                          for u, _, _ in us}
    elif args.revoke:
        revoke_targets = {int(x) for x in args.revoke.split(",") if x.strip()}

    with transaction.atomic():
        # ① 전역 역할
        grole = ensure_role(global_code, "GAION Global Admin", None,
                            "전역 관리 (GAION 운영자 전용) — W0-16")
        m, t = clone_grants(src, grole, None)
        print("[APPLY] 역할 '%s' id=%s · 권한 복제 menus+%d tabs+%d" % (global_code, grole, m, t))

        # ② 테넌트별 대체역할
        for gid in sorted(by_group, key=lambda x: (x is None, x)):
            users = by_group[gid]
            if gid in global_groups:
                for uid, uname, _ in users:
                    if assign(uid, grole):
                        print("[APPLY] +전역역할  id=%s %s" % (uid, uname))
                continue
            if gid is None:
                print("[APPLY] ⚠ group 없는 보유자 %d명 — 대체역할을 정할 수 없다. 건너뜀" % len(users))
                continue
            code = tenant_admin_role_code(gid)
            rid = ensure_role(code, "Tenant Admin (%s)" % users[0][2], gid,
                              "자기 테넌트 관리 — group %s · W0-16" % gid)
            m, t = clone_grants(src, rid, gid)
            print("[APPLY] 역할 '%s' id=%s · 권한 복제 menus+%d tabs+%d" % (code, rid, m, t))
            for uid, uname, _ in users:
                if assign(uid, rid):
                    print("[APPLY] +대체역할  id=%s %s → %s" % (uid, uname, code))

        # ③ 회수 (지정된 것만)
        for uid in sorted(revoke_targets):
            if revoke(uid, src):
                print("[APPLY] -레거시역할 id=%s (%s 회수)" % (uid, LEGACY_GLOBAL_ROLE_CODE))

    left = len(legacy_holders())
    print("[APPLY] 완료. 레거시 '%s' 잔여 보유자 %d명" % (LEGACY_GLOBAL_ROLE_CODE, left))
    print("[APPLY] 다음: settings TENANT_TRUST_LEGACY_SUPERUSER=False 로 내리고 재검증 "
          "(evidence/W0-16/revocation_runbook.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
