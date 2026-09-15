#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-112 — **한 낱말이 74계정을 연다.** 그 낱말을 쓰는 계정을 전수로 회전시킨다.

무엇이 있었나 [실측 2026-09-10 · gx-shell · `check_password` 전수 · 로그인 0회]
--------------------------------------------------------------------------------
    전체 계정 **114** · 그중 같은 비밀번호 하나를 쓰는 계정 **74** (활성 **73**)
    그 74 안에 이 저장소의 **유일한 superuser `phatlh`** 가 있다.
    -> 한 사람이 그 한 낱말을 알면 74계정과 관리자 권한이 **함께** 열린다.

    ⚠ 값은 이 파일 어디에도 없다. 찾을 낱말은 **환경변수 이름**으로만 받고,
      증거에는 `sha256[:12] + 길이` 만 적는다 (D-335 규약 ④).

반경 먼저, 회전 나중 — **게이트를 잠그지 않는다**
-------------------------------------------------
[실측 2026-09-10 · `.env.gates` 대조] 게이트가 쓰는 비밀번호 넷
(`GX_ROUTE_PASSWORD` · `GX_SEED_ROLE_PASSWORD` · `GX_PROBE_PASSWORD` ·
`GX_ROUTE_PASSWORD_ROLE0`)의 sha256[:12] 는 공유 낱말의 것과 **하나도 같지 않다.**
게이트 계정(`gxseed_*` · `gxprobe_*`) 중 74 안에 든 것은 **0개**다.
그러므로 이 회전은 게이트 자격증명을 **한 자도 건드리지 않는다.**
그래도 `NEVER_TOUCH` 로 한 겹 더 둔다 — 반경이 넓어지는 날을 위해서다.

새 값은 어디로 가나 — **저장소 밖**
-----------------------------------
`--ledger` 에 적힌 파일 하나로만 나간다. 그 파일을 저장소 안에 두지 않는다.
stdout 에는 `sha256[:12]` 와 길이만 나온다 — 파이프로 흘러도 값이 안 샌다.

    # 마른 실행 (아무것도 안 바꾼다)
    docker exec -e DJANGO_SETTINGS_MODULE=config.settings -e GX_SHARED_PW=... gx-shell \
        python /repo/scripts/rotate_shared_passwords.py --env-var GX_SHARED_PW

    # 실제 회전
    ... --env-var GX_SHARED_PW --apply --ledger /tmp/p112_ledger.txt
    docker cp gx-shell:/tmp/p112_ledger.txt <저장소 밖 경로>
    docker exec gx-shell rm -f /tmp/p112_ledger.txt

되돌리기
--------
**없다 — 되돌릴 수 없는 것이 요점이다.** 옛 낱말로 돌아가는 것은 사고로 돌아가는 것이다.
새 값은 원장 파일에 있고, 잃으면 관리자가 다시 발급한다.

종료 코드: 0 성공 · 1 회전이 검증에 실패 · 2 판정 불가(환경변수 없음 등)
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import secrets
import string
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: ★ **절대 건드리지 않는 이름.** 게이트와 차선 탐침이 이 이름으로 인증한다.
#: 이 목록에 든 계정이 공유 낱말을 쓰고 있으면 **회전하지 않고 빨강으로 알린다** —
#: 조용히 건너뛰면 「반경 0」이라는 거짓 초록이 남는다 (D-301).
NEVER_TOUCH: frozenset = frozenset({
    "gxseed_u1_operator", "gxseed_u2_manager", "gxseed_u3_field",
    "gxseed_u4_official", "gxseed_u5_sysop",
    "gxprobe_s", "gxprobe_q", "gxprobe_e", "gxprobe_c", "gxprobe_v", "gxprobe_e2e",
})

#: 새 비밀번호의 길이. CPO 정책의 하한(12)보다 **넉넉히** 위다 — 사람이 외울 값이
#: 아니라 원장에 적힌 값이므로 짧게 만들 이유가 없다.
NEW_LENGTH = 24

#: 네 계열을 **각각 최소 하나씩** 넣는다. 어떤 제품 규칙에도 걸리지 않게.
_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*-_=+"


def fingerprint(value: str) -> str:
    """값 대신 남기는 것. **이것만 로그·증거에 적는다** (D-335 규약 ④)."""
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:12]


def make_password(length: int = NEW_LENGTH) -> str:
    """네 계열을 모두 포함하는 임의 비밀번호. `secrets` 로만 만든다."""
    while True:
        pw = "".join(secrets.choice(_ALPHABET) for _ in range(length))
        if (any(c.islower() for c in pw) and any(c.isupper() for c in pw)
                and any(c.isdigit() for c in pw)
                and any(c in "!@#$%^&*-_=+" for c in pw)):
            return pw



#: ★ [D-270 ③ · 2026-09-15 턴 P · `verify_classification` 이 잡음] 이 도구는 **데이터를 쓴다**
#:   (`u.save()` — 사용자 비밀번호). 쓰는 도구는 분류 등록부를 참조해야 한다: 공용 마스터를
#:   건드리는지, 소유가 비어 있는 행을 건드리는지 모르고 쓰면 그것이 D-270 이 막은 사고다.
#:   회전 대상 `user.CoreUser` 는 등록부의 `DEFERRED` 칸이다(소유는 UserProfileLink.group 이
#:   말한다) — 공용 마스터가 **아니므로** 쓸 수 있다. 그것을 **읽어서 확인한 뒤** 쓴다.
#:   ⚠ 등록부를 못 읽으면 **진행하지 않는다** — 실패했을 때 안전한 쪽은 멈춤이다.
ROTATED_MODEL = "user.CoreUser"


def check_tenant_classification() -> str:
    """분류 등록부(`backend/tests/tenant_classification.py`)에서 회전 대상의 칸을 읽는다."""
    here = Path(__file__).resolve().parent
    for cand in (Path("/app/tests/tenant_classification.py"),
                 here.parent / "backend" / "tests" / "tenant_classification.py"):
        if cand.is_file():
            spec = importlib.util.spec_from_file_location("tenant_classification", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if ROTATED_MODEL in dict(mod.SHARED_MASTERS):
                raise SystemExit("[P-112] %s 가 SHARED_MASTERS 에 있다 — 공용 마스터는 "
                                 "회전하지 않는다. 멈춘다." % ROTATED_MODEL)
            for name in ("TENANT_UNASSIGNED", "DEFERRED"):
                if ROTATED_MODEL in dict(getattr(mod, name, {}) or {}):
                    return name
            raise SystemExit("[P-112] %s 가 분류 등록부 어느 칸에도 없다 — 분류되지 않은 "
                             "모델에는 쓰지 않는다. 멈춘다." % ROTATED_MODEL)
    raise SystemExit("[P-112] 분류 등록부(tenant_classification.py)를 찾지 못했다 — 멈춘다.")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-var", required=True,
                    help="찾을 비밀번호가 담긴 **환경변수 이름**. 값을 인자로 받지 않는다")
    ap.add_argument("--apply", action="store_true", help="실제로 바꾼다 (없으면 마른 실행)")
    ap.add_argument("--ledger", help="새 값을 적을 파일. **저장소 밖이어야 한다**")
    ap.add_argument("--evidence", help="값 없는 증거 JSON 경로")
    args = ap.parse_args()

    shared = os.environ.get(args.env_var)
    if not shared:
        print("[P-112] 환경변수 %s 가 비었다 — **판정 불가**(회색은 초록이 아니다)"
              % args.env_var)
        return 2
    if args.apply and not args.ledger:
        print("[P-112] --apply 에는 --ledger 가 필요하다 — 새 값을 어디에도 안 적으면 "
              "74계정이 잠긴다")
        return 2
    if args.ledger and "guardianx-source" in os.path.abspath(args.ledger).replace("\\", "/"):
        print("[P-112] 원장을 저장소 안에 둘 수 없다: %s" % args.ledger)
        return 2

    sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.contrib.auth import get_user_model

    User = get_user_model()
    total = User.objects.count()
    hits = [u for u in User.objects.all().order_by("id") if u.check_password(shared)]

    print("[P-112] 공유 낱말 sha256[:12]=%s 길이=%d" % (fingerprint(shared), len(shared)))
    print("[P-112] 전체 %d 계정 중 **%d** 이 이 낱말을 쓴다 (활성 %d · superuser %d)"
          % (total, len(hits), sum(1 for u in hits if u.is_active),
             sum(1 for u in hits if u.is_superuser)))

    protected = [u.username for u in hits if u.username in NEVER_TOUCH]
    if protected:
        print("[P-112] ★빨강 — 게이트 계정이 공유 낱말을 쓴다: %s" % ", ".join(protected))
        print("        회전하면 게이트가 눈이 먼다. 사람이 먼저 `.env.gates` 를 정하고 "
              "이 이름들을 따로 돌려라.")
        return 1

    if not args.apply:
        print("[P-112] 마른 실행 — 아무것도 안 바꿨다. 바꾸려면 --apply --ledger")
        return 0

    print("[P-112] 분류 등록부: %s 는 %s 칸 — 공용 마스터 아님, 쓴다"
          % (ROTATED_MODEL, check_tenant_classification()))

    rows = []
    lines = ["# P-112 회전 원장 — **저장소 밖 전용.** %s"
             % datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "# 형식: username<TAB>new_password",
             "# 옛 낱말 sha256[:12]=%s" % fingerprint(shared)]
    for u in hits:
        new = make_password()
        u.set_password(new)
        # ★ dj-core 는 `last_password_reset is None` 을 보고 로그인 응답에
        #   `must_change_password: True` 를 싣는다 (core/api/v1/auth.py:737).
        #   그 판정은 **superuser·superuser 역할에만** 걸린다 — 나머지 계정에는
        #   이 제품에 강제 변경 장치가 **없다.** 그 사실을 숨기지 않는다:
        #   여기서는 값을 세워 두고, 「첫 로그인 강제 변경」은 정책 문서의 몫이다.
        u.last_password_reset = None
        u.save()
        lines.append("%s\t%s" % (u.username, new))
        rows.append({"id": u.id, "username": u.username, "active": u.is_active,
                     "is_superuser": u.is_superuser,
                     "new_sha256_12": fingerprint(new), "new_length": len(new)})

    with open(args.ledger, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    try:
        os.chmod(args.ledger, 0o600)
    except OSError:
        pass

    # ── 검증 — **바꿨다고 말하지 말고 다시 재라** (D-210) ─────────────────────
    still = [u.username for u in User.objects.all() if u.check_password(shared)]
    ok = 0
    for row, line in zip(rows, lines[3:]):
        _name, new = line.split("\t", 1)
        if User.objects.get(pk=row["id"]).check_password(new):
            ok += 1
    print("[P-112] 회전 **%d계정** · 새 값 검증 통과 %d/%d · 옛 낱말이 남은 계정 **%d**"
          % (len(rows), ok, len(rows), len(still)))
    print("[P-112] 원장 -> %s (값은 여기에만 있다. stdout 에는 없다)" % args.ledger)

    if args.evidence:
        import json
        os.makedirs(os.path.dirname(os.path.abspath(args.evidence)), exist_ok=True)
        with open(args.evidence, "w", encoding="utf-8") as fh:
            json.dump({
                "decision": "P-112",
                "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "old_password_sha256_12": fingerprint(shared),
                "old_password_length": len(shared),
                "accounts_total": total,
                "rotated": len(rows),
                "verified_new": ok,
                "still_on_old_password": len(still),
                "never_touch_hit": protected,
                "new_length": NEW_LENGTH,
                "note": ("값은 저장소 밖 원장에만 있다. 이 파일에는 sha256[:12] 와 "
                         "길이만 있다 (D-335 규약 ④)."),
                "accounts": rows,
            }, fh, ensure_ascii=False, indent=2)
        print("[P-112] 증거(값 없음) -> %s" % args.evidence)

    return 0 if (ok == len(rows) and not still) else 1


if __name__ == "__main__":
    sys.exit(main())
