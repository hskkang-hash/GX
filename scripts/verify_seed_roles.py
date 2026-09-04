#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""U2·U4 역할 사람이 **지금 이 환경에 있는가** — 네 수를 잰다 (2026-09-04 · 차선 E3).

    "첫 일: 시드 확장 — U2·U4 역할 사람 각 1명(`data_source=seed`)"
        — RESUME_NEXT 2026-09-04 §E3

왜 판정기가 따로 있는가 — **심었다와 있다는 다른 사실이다**
------------------------------------------------------------
`seed_role_users` 가 끝에 찍는 수는 **자기가 방금 한 일**이다. 이 판정기는 시드를
부르지 않고 지금 있는 것만 센다. 갈리는 자리가 실제로 셋이나 있었다:

  · `create-user` 는 **원자적이지 않다** — 프로필 생성에서 죽으면 `CoreUser` 행만
    남고 응답은 `400 Failed to create user.` 다. 부른 쪽은 "안 생겼다"고 읽는데
    **반쪽 사람이 남아 있다** [실측 2026-09-04]
  · `user_profile_link.employee_id` 에 UNIQUE 가 걸려 있다 — 같은 표를 둘에게 달면
    둘째가 죽는다. 그 사유는 **응답에 실리지 않는다**
  · 역할이 붙어도 **소속이 없으면** K2 수신자에도, 어느 화면에도 안 잡힌다

재는 것 넷
----------
  ① 시드 사람 2명 (U2·U4) 이 있고 **표식 셋**을 다 갖췄는가
  ② 각자의 역할이 정확히 하나이고, 기대한 코드인가
  ③ K3 가 그 사람에게 주는 프리셋이 기대값인가 (`matched=True`)
  ④ K2 `critical` 수신자에 그 두 역할이 **각각 1명 이상** 잡히는가
     — 「역할을 가진 사람이 있다」와 「알림이 그 사람에게 간다」는 다른 사실이다(D-301)

    docker exec -w /app -e PYTHONPATH=/app gx-shell python /repo/scripts/verify_seed_roles.py
    python scripts/verify_seed_roles.py --self-test     # 판정 규칙만 (Django 없이)

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 **못 쟀다**(환경 없음). 회색은 초록이 아니다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 기대값. 시드 명령에서 **읽어 온다** — 여기에 복사하면 두 벌이 되고 어긋난다(D-369).
#: 이 상수는 커맨드 모듈을 못 읽었을 때의 마지막 그물이다.
FALLBACK_EXPECT = (
    {"key": "U2", "username": "gxseed_u2_manager",
     "role_code": "fire_admin", "expect_preset": "MANAGER"},
    {"key": "U4", "username": "gxseed_u4_official",
     "role_code": "view_only_-_anyang", "expect_preset": "EXECUTIVE"},
)
FALLBACK_MARKER = "GX-SEED-ROLE"


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — 함수로 떼어 둔 이유는 **시험하기 위해서다** (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(found: dict, expect: tuple) -> list[tuple[str, bool, str]]:
    """`found` 는 「지금 있는 것」. `None` 은 **못 쟀다**이지 0 이 아니다 (D-301)."""
    out: list[tuple[str, bool, str]] = []

    people = found.get("people")
    if people is None:
        return [("시드 사람", False, "**못 쟀다** — DB 에 닿지 못했다"),
                ("역할", False, "못 쟀다"),
                ("프리셋", False, "못 쟀다"),
                ("수신자", False, "못 쟀다")]

    # ① 있는가 + 표식
    missing = [s["username"] for s in expect if s["username"] not in people]
    if missing:
        out.append(("시드 사람", False, "없다: %s" % ", ".join(missing)))
    else:
        unmarked = [n for n, p in people.items() if not p.get("marked")]
        out.append(("시드 사람", not unmarked,
                    "%d명 · 표식 온전" % len(people) if not unmarked
                    else "표식이 없는 사람: %s" % ", ".join(unmarked)))

    # ② 역할
    bad = []
    for s in expect:
        p = people.get(s["username"])
        if p is None:
            bad.append("%s 없음" % s["username"]); continue
        if p.get("roles") != [s["role_code"]]:
            bad.append("%s 역할 %s (기대 %s)"
                       % (s["username"], p.get("roles"), [s["role_code"]]))
        if not p.get("group_ok"):
            bad.append("%s 소속 없음/다름 — 어느 화면에도 안 보인다" % s["username"])
    out.append(("역할·소속", not bad, "; ".join(bad) or "각 1개 · 소속 일치"))

    # ③ 프리셋
    bad = []
    for s in expect:
        p = people.get(s["username"]) or {}
        if p.get("preset") != s["expect_preset"]:
            bad.append("%s 프리셋 %s (기대 %s)"
                       % (s["username"], p.get("preset"), s["expect_preset"]))
        elif p.get("matched") is False:
            bad.append("%s 는 매핑을 못 찾고 기본값으로 떨어졌다 (matched=False)"
                       % s["username"])
    out.append(("K3 프리셋", not bad, "; ".join(bad) or "기대와 같다 · matched=True"))

    # ④ 수신자
    by_role = found.get("recipients_by_role")
    if by_role is None:
        out.append(("K2 수신자", False, "**못 쟀다** — K2 를 부르지 못했다"))
    else:
        want = [s["role_code"] for s in expect]
        zero = [c for c in want if by_role.get(c, 0) < 1]
        out.append(("K2 수신자", not zero,
                    "critical 수신자 %d명 · %s" % (found.get("recipients_total", -1),
                                                json.dumps(by_role, ensure_ascii=False))
                    if not zero else
                    "규칙은 있는데 **닿는 사람이 0명**인 역할: %s" % ", ".join(zero)))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 수집 — Django 가 있어야 한다. 없으면 **회색**이다
# ═══════════════════════════════════════════════════════════════════════════
def collect() -> tuple[dict, tuple, str | None]:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    #: ★ 컨테이너는 `/repo` 와 `/app`(=backend) 이 **따로** 마운트된다 — `/repo` 에서
    #:   부르면 `config` 가 이름 공간에 없다. 자리를 하나로 못 박지 않고 더해 둔다
    #:   (`verify_seed_p20.py` 가 같은 줄을 같은 사유로 갖는다).
    for candidate in ("/app", str(Path(__file__).resolve().parent.parent / "backend")):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)
    try:
        import django
        django.setup()
    except Exception as exc:                                  # noqa: BLE001
        return {}, FALLBACK_EXPECT, "Django 를 못 세웠다: %s: %s" % (type(exc).__name__, exc)

    expect, marker, prefix = FALLBACK_EXPECT, FALLBACK_MARKER, "gxseed_"
    try:
        from stream_monitors.management.commands import seed_role_users as cmd
        expect = tuple(cmd.SEED_PEOPLE)
        marker = cmd.SEED_MARKER
        prefix = cmd.SEED_PREFIX
    except Exception:                                         # noqa: BLE001
        pass                                                  # 그물로 간다

    found: dict = {}
    try:
        from django.contrib.auth import get_user_model

        from common.tenant_filters import get_user_group
        from common.tenant_scope import TenantScope
        from django.apps import apps

        User = get_user_model()
        Profile = apps.get_model("user", "UserProfileLink")
        peer = User._base_manager.filter(
            username=os.environ.get("GX_SEED_PEER", "gxprobe_e2e")).first()
        if peer is None:
            return {}, expect, "기준 계정(gxprobe_e2e)이 없다 — 어느 소속을 잴지 모른다"
        group = get_user_group(peer)
        if group is None:
            return {}, expect, "기준 계정에 소속이 없다"

        people = {}
        for spec in expect:
            u = User._base_manager.filter(username=spec["username"]).first()
            if u is None:
                continue
            prof = Profile.objects.filter(user=u).first()
            entry = {
                "roles": sorted(r.code for r in u.roles.all()),
                "group_ok": bool(prof and prof.group_id == group.pk),
                "marked": bool(prof and (prof.employee_id or "").startswith(marker)
                               and u.username.startswith(prefix)),
                "active": bool(u.is_active),
            }
            try:
                from kernels.k3_dashboard.services import get_preset
                view = get_preset(scope=TenantScope.of(u))
                entry["preset"] = getattr(view, "preset", None)
                entry["matched"] = getattr(view, "matched", None)
            except Exception as exc:                          # noqa: BLE001
                entry["preset"] = None
                entry["matched"] = "못 쟀다: %s" % exc
            people[spec["username"]] = entry
        found["people"] = people

        from kernels.k2_notify import resolve_recipients
        rec = resolve_recipients(scope=TenantScope.of(peer),
                                 severity="critical", group=group)
        by = {}
        for r in rec:
            by[r.role_code] = by.get(r.role_code, 0) + 1
        found["recipients_total"] = len(rec)
        found["recipients_by_role"] = by
        found["group"] = "%s(%s)" % (group.pk, getattr(group, "name", "?"))
    except Exception as exc:                                  # noqa: BLE001
        return found, expect, "DB 를 읽다 죽었다: %s: %s" % (type(exc).__name__, exc)
    return found, expect, None


def self_test() -> int:
    """판정 규칙만 시험한다. Django 없이 돈다 — **판정기도 시험받는다**(D-277).

    ★ **출생 표본** (D-310) — 이 판정기를 만들게 한 사례는 합성이 아니다.
      [실측 2026-09-24 착수 전] 개발 DB 의 상태가 아래 `birth` 다:
      `fire_admin` **0명** · `view_only_-_anyang` **0명** · critical 수신자 12명이
      **전부 `operator`**. 사람은 있는데 **역할이 없어서** K3 프리셋이
      「역할 매핑을 찾지 못해 가장 좁은 화면으로 떨어졌습니다」를 냈고, 그래서
      U2·U4 의 화면을 U2·U4 의 화면이라고 부를 수 없었다.
      ★ 그 상태가 **초록으로 보이던 것**이 이 도구를 만든 이유다: 계정은 있었고
        로그인도 됐다. 없는 것은 역할이었고, 역할은 아무 시험도 안 보고 있었다.
    """
    ok = True
    expect = FALLBACK_EXPECT

    # ── 출생 표본 — **역할이 0명이던 날.** 사람은 있고 역할이 없다 ──────────
    birth = {"people": {s["username"]: {"roles": [], "group_ok": True, "marked": True,
                                        "preset": "OPERATOR", "matched": False}
                        for s in expect},
             "recipients_total": 12, "recipients_by_role": {"operator": 12}}
    r = judge(birth, expect)
    #: ★ 출생 표본의 요점은 **초록이 아니어야 한다**는 것이다. 「전부 빨강」이 아니라
    #:   「하나라도 빨강」으로 잰다 — 그날 소속과 표식은 멀쩡했고 **역할만** 없었다.
    #:   전부 빨강으로 재면 이 표본은 `half`(반쪽 사람)와 같은 것을 재게 되고,
    #:   그러면 출생 표본이 아니라 그 표본의 복사본이다.
    ok &= not all(p for _, p, _ in r)

    # 아무것도 못 쟀다 → 넷 다 실패, 「0건」이 아니라 「못 쟀다」로 말해야 한다
    r = judge({}, expect)
    ok &= all(not p for _, p, _ in r) and "못 쟀다" in r[0][2]

    # 반쪽 사람(행은 있는데 역할·소속이 없다) → 통과하면 안 된다
    half = {"people": {s["username"]: {"roles": [], "group_ok": False, "marked": False,
                                       "preset": "OPERATOR", "matched": False}
                       for s in expect},
            "recipients_total": 12, "recipients_by_role": {"operator": 12}}
    r = judge(half, expect)
    ok &= not any(p for _, p, _ in r)

    # 온전 → 넷 다 통과
    good = {"people": {s["username"]: {"roles": [s["role_code"]], "group_ok": True,
                                       "marked": True, "preset": s["expect_preset"],
                                       "matched": True} for s in expect},
            "recipients_total": 14,
            "recipients_by_role": {"operator": 12, "fire_admin": 1,
                                   "view_only_-_anyang": 1}}
    r = judge(good, expect)
    ok &= all(p for _, p, _ in r)

    # 사람은 있는데 수신자 0 → ④만 실패해야 한다 (역할과 도달은 다른 사실이다)
    unreached = dict(good)
    unreached["recipients_by_role"] = {"operator": 12}
    r = judge(unreached, expect)
    ok &= [p for _, p, _ in r] == [True, True, True, False]

    print("self-test: %s" % ("통과" if ok else "실패"))
    return EXIT_OK if ok else EXIT_FAIL


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    found, expect, why = collect()
    if why:
        print("판정 불가(exit 2): %s" % why)
        print("  회색은 초록이 아니다 — 못 잰 것을 통과로 적지 않는다.")
        return EXIT_UNDECIDABLE

    print("[verify_seed_roles] 소속 %s" % found.get("group"))
    rows = judge(found, expect)
    for name, passed, why2 in rows:
        print("  %s %-12s %s" % ("OK  " if passed else "FAIL", name, why2))
    return EXIT_OK if all(p for _, p, _ in rows) else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
