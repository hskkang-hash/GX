#!/usr/bin/env python
"""소유자 백필 **dry-run 리포트** — created_by / group (W0-13 ③ · D-209 · D-254).

이 스크립트는 **한 행도 쓰지 않는다.** D-209 가 강제한 순서(조사 → 표기 → 백필 → 제거)에서
"백필 직전"에 서는 리포트를 만든다. 적용 스크립트는 이 리포트를 대표가 확인한 뒤에 만든다.

무엇을 세는가 — 구멍은 **둘**이고 방향이 반대다
    ① `created_by IS NULL`  → dj-core 매니저가 `Q(created_by__isnull=True)` 를 OR 로 붙여
                              **전 테넌트에 보인다** (노출).
    ② `group IS NULL`       → W0-14 의 명시적 group 필터에서 **아무에게도 안 보인다** (손실).
    두 구멍이 겹치는 행(둘 다 NULL)은 소유를 말할 근거가 아무것도 없다 — 사람이 정해야 한다.

귀속 규칙 (우선순위 · 이 리포트가 각 규칙의 적용 가능 행 수를 센다)
    R1  group 이 있고 created_by 가 없다      → created_by := 그 group 의 대표 사용자
    R2  created_by 가 있고 group 이 없다      → group := created_by 의 소속 group
    R3  둘 다 없다 · **부모가 있다**           → group := 부모 레코드의 group
                                                 (MissionWaypoint→mission, OrderHistory→order …)
    R4  둘 다 없고 **부모도 없다**             → 자동 귀속 불가. 사람이 정하거나 시스템 소유로
                                                 표기한다 (D-209 ②). 이 부류의 상당수는
                                                 애초에 테넌트 데이터가 아니다(국가·시간대·메뉴)

제외 (귀속하면 기능이 깨진다 — impact.md §3)
    `operation_settings` 계열은 `created_by IS NULL` 을 **"시스템 기본 설정"의 뜻으로 이미
    사용**한다 (`operation_settings_service.py:32` · `tasks.py:27,100`). 여기에 소유자를
    채우면 기본 설정 조회가 깨진다.

사용:
    docker exec -i -e DB_NAME=<복제본> -w /app gx-shell python - < scripts/backfill_owner_dryrun.py
    (기본 DB 로 돌려도 **읽기 전용**이다. 그래도 복제본 권장 — D-245)

출력: 표 + `MARKDOWN` 섹션(evidence 에 붙여넣는 용). JSON 은 `--json`.
"""
from __future__ import annotations

import json
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.apps import apps  # noqa: E402
from django.db import connection  # noqa: E402
from django.db import models  # noqa: E402
from django.db.models import Q  # noqa: E402

#: 소유자를 채우면 **기능이 깨지는** 앱. 사유는 모듈 docstring 참조.
SYSTEM_OWNED_APPS = {"operation_settings"}


def tenantish_models():
    """`created_by` 와 (`group` 또는 `groups`) 를 가진 모델 — 테넌트성 데이터."""
    for model in apps.get_models():
        names = {f.name for f in model._meta.get_fields()}
        if "created_by" not in names:
            continue
        if not ({"group", "groups"} & names):
            continue
        yield model, ("group" if "group" in names else "groups")


def count(model, condition: Q | None = None) -> int:
    """**필터를 우회해서** 진짜 수를 센다 — 매니저의 테넌트 필터가 수를 왜곡한다."""
    qs = model._base_manager.all()
    if condition is not None:
        qs = qs.filter(condition)
    return qs.count()


def group_representative_users() -> dict:
    """group 별 대표 사용자 1명 (R1 이 쓸 값). 활성·역할 보유자 중 최소 id."""
    with connection.cursor() as c:
        c.execute(
            """
            SELECT l.group_id, min(u.id)
            FROM user_profile_link l
            JOIN user_coreuser u ON u.id = l.user_id
            WHERE l.deleted IS NULL AND l.group_id IS NOT NULL AND u.is_active
              AND EXISTS (SELECT 1 FROM user_coreuser_roles r WHERE r.coreuser_id = u.id)
            GROUP BY l.group_id
            """
        )
        return {row[0]: row[1] for row in c.fetchall()}


def main() -> int:
    as_json = "--json" in sys.argv
    reps = group_representative_users()

    rows = []
    unreadable = []
    for model, group_field in tenantish_models():
        label = model._meta.label
        app_label = model._meta.app_label
        excluded = app_label in SYSTEM_OWNED_APPS
        soft = Q()
        if any(f.name == "deleted" for f in model._meta.get_fields()):
            soft = Q(deleted__isnull=True)

        try:
            total = count(model, soft)
            if total == 0:
                continue
            cb_null = count(model, soft & Q(created_by__isnull=True))
            null_group = Q(group__isnull=True) if group_field == "group" else Q(groups__isnull=True)
            has_group = ~null_group
            grp_null = count(model, soft & null_group)
            both = count(model, soft & Q(created_by__isnull=True) & null_group)
            r1 = count(model, soft & Q(created_by__isnull=True) & has_group)
            r2 = count(model, soft & Q(created_by__isnull=False) & null_group)
            # R3 — 부모 레코드에서 소유를 물려받을 수 있는가.
            # 가장 많이 덮는 부모 하나를 고른다 (여러 부모가 있으면 실측으로 비교).
            best_parent, best_cover = None, 0
            for f in model._meta.get_fields():
                if not isinstance(f, models.ForeignKey):
                    continue
                parent = f.related_model
                pnames = {pf.name for pf in parent._meta.get_fields()}
                if not ({"group", "groups"} & pnames):
                    continue
                lookup = f"{f.name}__group__isnull" if "group" in pnames                     else f"{f.name}__groups__isnull"
                try:
                    cover = count(model, soft & null_group & Q(**{lookup: False}))
                except Exception:
                    continue
                if cover > best_cover:
                    best_parent, best_cover = f"{f.name} → {parent._meta.label}", cover
        except Exception as exc:  # 저장소 모델과 운영 스키마가 어긋난 테이블 (P-LOCAL-4)
            unreadable.append({"model": label, "error": str(exc).splitlines()[0][:120]})
            continue

        rows.append({
            "model": label, "app": app_label, "group_field": group_field,
            "total": total, "created_by_null": cb_null, "group_null": grp_null,
            "both_null": both, "r1_fixable": r1, "r2_fixable": r2,
            "r3_parent": best_parent, "r3_fixable": best_cover,
            "excluded": excluded,
        })

    rows.sort(key=lambda r: (-(r["created_by_null"] + r["group_null"]), r["model"]))
    totals = {
        k: sum(r[k] for r in rows if not r["excluded"])
        for k in ("total", "created_by_null", "group_null", "both_null",
                  "r1_fixable", "r2_fixable", "r3_fixable")
    }

    if as_json:
        print(json.dumps({"rows": rows, "totals": totals, "unreadable": unreadable,
                          "group_representatives": reps}, ensure_ascii=False, indent=2))
        return 0

    print(f"{'model':46} {'total':>7} {'cb_null':>8} {'grp_null':>9} "
          f"{'both':>6} {'R1':>4} {'R2':>4} {'R3':>6}  parent / note")
    for r in rows:
        note = "SYSTEM-OWNED · 제외" if r["excluded"] else (r["r3_parent"] or "부모 없음")
        print(f"{r['model']:46} {r['total']:7d} {r['created_by_null']:8d} "
              f"{r['group_null']:9d} {r['both_null']:6d} {r['r1_fixable']:4d} "
              f"{r['r2_fixable']:4d} {r['r3_fixable']:6d}  {note}")
    print()
    print("[합계 · 제외분 빼고] " + " · ".join(f"{k}={v}" for k, v in totals.items()))
    print(f"[group 대표 사용자] {len(reps)}개 group — {reps}")
    if unreadable:
        print()
        print(f"[셀 수 없음 · 저장소 모델과 운영 스키마 불일치 {len(unreadable)}건 — P-LOCAL-4]")
        for u in unreadable:
            print(f"  {u['model']:52} {u['error']}")
    print()
    print("R1 = group 있고 created_by 없음 → created_by 채울 수 있다")
    print("R2 = created_by 있고 group 없음 → group 채울 수 있다")
    print("R3 = group 이 없지만 **부모 레코드에 group 이 있다** → 물려받을 수 있다")
    print("부모 없음 = 자동 귀속 불가. 사람이 정하거나 시스템 소유로 표기 (D-209 ②)")
    print()
    print("※ 이 스크립트는 한 행도 쓰지 않는다. 적용본은 대표 확인 후 별도로 만든다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
