#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""U1·U2·U4·U5 역할 사람이 **지금 이 환경에 있는가** — 다섯 수를 잰다 (2026-09-04 · E3).

★ [2026-09-06 · 턴 G] U5(`admin`)가 넷째로 들어왔다. 그 사람이 생기기 전까지
  `verify_sidebar` 의 U5 사이드바 수는 **아무도 로그인해서 본 적 없는 재현**이었다.

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

재는 것 다섯
------------
  ① 시드 사람 4명 (U1·U2·U4·U5) 이 있고 **표식 셋**을 다 갖췄는가
  ② 각자의 역할이 정확히 하나이고, 기대한 코드인가
  ③ K3 가 그 사람에게 주는 프리셋이 기대값인가 (`matched=True`)
  ④ K2 `critical` 수신자에 **경보 자리로 선언한** 역할이 각각 1명 이상 잡히는가
     — 선언은 `seed_role_users.SEED_PEOPLE["alarm_destination"]` 한 곳이다. 면제가
       아니라 선언이고, 칸을 안 적으면 **엄한 쪽**(경보 자리)으로 본다
     — 「역할을 가진 사람이 있다」와 「알림이 그 사람에게 간다」는 다른 사실이다(D-301)
  ⑤ **첫 로그인 역할 매핑 경고**가 남아 있는가 (2026-09-24 추가)
     `get_preset` 은 매핑을 못 찾으면 `matched=False` 로 가장 좁은 화면에 떨어뜨리고
     그 사유를 경고로 남긴다. 그 경고에는 **두 종류**가 섞여 있다:
       ㉠ `K3_UNMAPPED_BY_DECISION` 에 이름이 적힌 역할 — **일부러 안 매핑한 것**
       ㉡ 어디에도 안 적힌 역할        — **매핑을 빠뜨린 것**
     ⑤가 세는 것은 ㉡뿐이다. ㉠까지 세면 「매핑하지 않기로 했다」가 결함으로 보이고,
     그러면 결함을 지우려고 배송 역할을 재난 화면에 매핑하게 된다(D-264).
     ㉠과, 역할이 아예 0개인 사람은 **[실측]으로 따로 찍는다** — 판정하지 않고 센다.

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
    {"key": "U1", "username": "gxseed_u1_operator",
     "role_code": "fire_user", "expect_preset": "OPERATOR",
     "alarm_destination": True},
    {"key": "U2", "username": "gxseed_u2_manager",
     "role_code": "fire_admin", "expect_preset": "MANAGER",
     "alarm_destination": True},
    {"key": "U4", "username": "gxseed_u4_official",
     "role_code": "view_only_-_anyang", "expect_preset": "EXECUTIVE",
     "alarm_destination": True},
    {"key": "U5", "username": "gxseed_u5_sysop",
     "role_code": "admin", "expect_preset": "MANAGER",
     "alarm_destination": False},
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
                ("수신자", False, "못 쟀다"),
                ("매핑 경고", False, "못 쟀다")]

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
        # ★ **경보가 갈 자리로 선언된 역할만** 잰다 (2026-09-06 · 턴 G).
        #
        #   왜 「시드 역할 전부」가 아닌가: U5(`admin`)를 심자마자 이 줄이 빨개졌다.
        #   K2 규칙 어디도 `admin` 을 가리키지 않기 때문이다. 그 빨강을 지우는 가장
        #   빠른 길은 `admin` 에게 critical 규칙을 만드는 것이고, 그러면 **판정기가
        #   알림 정책을 발명한다** — 재난 경보를 누가 받는지는 판정기가 정할 일이
        #   아니다(D-264: 결함을 지우려고 결정을 뒤집지 않는다).
        #
        #   ⚠ 이것은 면제가 아니라 **선언**이다. 칸을 안 적은 역할은 종전대로
        #     「경보가 갈 자리」로 본다 — 기본값이 엄한 쪽이어야 다음 사람이
        #     칸을 빠뜨렸을 때 조용히 통과하지 않는다.
        want = [s["role_code"] for s in expect
                if s.get("alarm_destination", True)]
        aside = [(s["role_code"], by_role.get(s["role_code"], 0)) for s in expect
                 if not s.get("alarm_destination", True)]
        zero = [c for c in want if by_role.get(c, 0) < 1]
        note = "critical 수신자 %d명 · %s" % (
            found.get("recipients_total", -1),
            json.dumps(by_role, ensure_ascii=False))
        if aside:
            note += " · 경보 자리가 **아니라고 선언한** 역할: %s" % ", ".join(
                "%s(%d명)" % (c, n) for c, n in aside)
        out.append(("K2 수신자", not zero, note if not zero else
                    "규칙은 있는데 **닿는 사람이 0명**인 역할: %s" % ", ".join(zero)))

    # ⑤ 매핑 경고 — **빠뜨린 것만** 센다 (㉡). ㉠·역할 0개는 아래에서 실측으로 찍는다.
    holes = found.get("mapping_holes")
    if holes is None:
        out.append(("매핑 경고", False, "**못 쟀다** — K3 매핑을 읽지 못했다"))
    else:
        out.append(("매핑 경고", not holes,
                    "매핑을 빠뜨린 역할 0종 — 첫 로그인 경고 없음"
                    if not holes else
                    "**매핑을 빠뜨린 역할**(선언도 안 됐다): %s — "
                    "이 역할로 처음 로그인하면 가장 좁은 화면에 떨어지고 경고가 뜬다"
                    % ", ".join("%s(%d명)" % (c, n) for c, n in sorted(holes.items()))))
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

        # ── ⑤ 첫 로그인 역할 매핑 경고 ────────────────────────────────────
        # 이 소속의 **활성 사용자 전수**를 훑는다. 시드 사람만 보면 「우리가 심은 셋은
        # 멀쩡하다」밖에 말하지 못하고, 경고를 실제로 보는 사람은 나머지다.
        #
        # ★ 판정식을 복제하지 않는다(D-212·D-369): 매핑은 `settings.K3_ROLE_PRESET_MAP`,
        #   「일부러 안 매핑한 것」은 `settings.K3_UNMAPPED_BY_DECISION` 이 정본이다.
        #   여기서 역할 목록을 다시 적으면 두 벌이 되고, 두 벌은 반드시 어긋난다.
        try:
            from django.conf import settings as dj_settings

            mapping = set(getattr(dj_settings, "K3_ROLE_PRESET_MAP", None) or {})
            declared = set(getattr(dj_settings, "K3_UNMAPPED_BY_DECISION", None) or {})
            holes, by_decision, roleless = {}, {}, []
            for u in User._base_manager.filter(
                    userprofilelink__group=group, is_active=True).distinct():
                codes = sorted(r.code for r in u.roles.all())
                if not codes:
                    roleless.append(u.username)
                    continue
                if any(c in mapping for c in codes):
                    continue                       # 하나라도 매핑되면 경고가 안 뜬다
                for c in codes:
                    bucket = by_decision if c in declared else holes
                    bucket[c] = bucket.get(c, 0) + 1
            found["mapping_holes"] = holes
            found["mapping_by_decision"] = by_decision
            found["roleless"] = sorted(roleless)
        except Exception as exc:                              # noqa: BLE001
            found["mapping_holes"] = None
            found["mapping_error"] = "%s: %s" % (type(exc).__name__, exc)

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
             "recipients_total": 12, "recipients_by_role": {"operator": 12},
             "mapping_holes": {}}
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
            "recipients_total": 12, "recipients_by_role": {"operator": 12},
            "mapping_holes": {"fire_user": 1}}
    r = judge(half, expect)
    ok &= not any(p for _, p, _ in r)

    # 온전 → 넷 다 통과
    good = {"people": {s["username"]: {"roles": [s["role_code"]], "group_ok": True,
                                       "marked": True, "preset": s["expect_preset"],
                                       "matched": True} for s in expect},
            "recipients_total": 15,
            "recipients_by_role": {"fire_user": 1, "operator": 12, "fire_admin": 1,
                                   "view_only_-_anyang": 1},
            "mapping_holes": {}}
    r = judge(good, expect)
    ok &= all(p for _, p, _ in r)

    # 사람은 있는데 수신자 0 → ④만 실패해야 한다 (역할과 도달은 다른 사실이다)
    unreached = dict(good)
    unreached["recipients_by_role"] = {"operator": 12}
    r = judge(unreached, expect)
    ok &= [p for _, p, _ in r] == [True, True, True, False, True]

    # ── ④ 선언 갈래 — **경보 자리가 아니라고 선언한 역할**은 0명이어도 초록 ──
    #   [출생 표본 2026-09-06] U5(`admin`)를 심자마자 ④가 빨개졌다. 그 빨강은
    #   결함이 아니라 **물음이 틀린 것**이었다.
    declared_aside = dict(good)
    declared_aside["recipients_by_role"] = {
        "fire_user": 1, "operator": 12, "fire_admin": 1, "view_only_-_anyang": 1}
    r = judge(declared_aside, expect)          # expect 의 U5 는 alarm_destination=False
    ok &= all(p for _, p, _ in r)
    #: ⚠ 그리고 **선언하지 않으면 여전히 빨강이어야 한다** — 기본값이 엄한 쪽이다.
    #:   이 줄이 없으면 「칸을 빠뜨리면 통과」가 되고, 그것이 곧 조용한 면제다.
    unmarked = tuple({k: v for k, v in s.items() if k != "alarm_destination"}
                     for s in expect)
    r = judge(declared_aside, unmarked)
    ok &= [p for _, p, _ in r] == [True, True, True, False, True]

    # ── ⑤ 매핑 경고 — **㉠(선언된 결정)과 ㉡(빠뜨린 것)을 가르는가** ──────
    #   [실측 2026-09-24] 소속 4 에는 `order` 역할 9명이 matched=False 로 떨어진다.
    #   그 역할은 `K3_UNMAPPED_BY_DECISION` 에 이름이 적혀 있다 — **배송 역할을 재난
    #   화면에 매핑하지 않기로 한 결정**이다. 이것을 경고로 세면, 경고를 지우는 가장
    #   빠른 길이 「배송 역할을 재난 화면에 매핑하는 것」이 된다. 그러면 §0.4 금지구역의
    #   사람들이 재난 관제 화면을 얻고, 판정기가 그 사고의 원인이 된다.
    by_decision_only = dict(good)
    by_decision_only["mapping_holes"] = {}
    by_decision_only["mapping_by_decision"] = {"order": 9}
    r = judge(by_decision_only, expect)
    ok &= all(p for _, p, _ in r)

    hole = dict(good)
    hole["mapping_holes"] = {"surveillance_order": 3}
    r = judge(hole, expect)
    ok &= [p for _, p, _ in r] == [True, True, True, True, False]

    # 매핑을 **못 읽었다** → ⑤는 초록이 아니다. 회색은 초록이 아니다(D-301)
    blind = dict(good)
    blind["mapping_holes"] = None
    r = judge(blind, expect)
    ok &= [p for _, p, _ in r] == [True, True, True, True, False]

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

    # ── 판정하지 않고 **세는** 두 줄. 없애야 할 것과 그냥 그런 것을 가른다 ──
    by_dec = found.get("mapping_by_decision")
    if by_dec is not None:
        print("  [실측] 일부러 매핑하지 않은 역할로 로그인하는 사람: %s"
              % (", ".join("%s(%d명)" % kv for kv in sorted(by_dec.items()))
                 or "없다"))
        print("         — `K3_UNMAPPED_BY_DECISION` 에 이름이 적혀 있다. **선언된 결정**이지")
        print("           빠뜨린 자리가 아니다. 이들을 재난 화면에 매핑하면 그 순간")
        print("           「매핑하지 않기로 했다」가 사라진다(D-264).")
    roleless = found.get("roleless")
    if roleless is not None:
        print("  [실측] 역할이 **0개**인 활성 계정: %s"
              % (", ".join(roleless) or "없다"))
        print("         — 매핑의 문제가 아니라 **계정의 문제**다. 역할이 없으면 고를 프리셋도")
        print("           없다. 이 판정기는 세기만 한다 — 누구에게 어떤 역할을 줄지는")
        print("           시드가 정할 일이 아니다.")
    return EXIT_OK if all(p for _, p, _ in rows) else EXIT_FAIL


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        target="gx-shell 컨테이너 · DJANGO_SETTINGS_MODULE=config.settings (앱과 같은 설정) · 호스트에서 부르면 docker exec 로 위임한다",
        as_="(HTTP 계정 없음) — gx-shell 안 Django ORM 으로 읽는다 · DB 자격은 앱이 들고 있는 것 그대로(이름: DATABASE_URL / POSTGRES_*)",
        source="살아 있는 DB·앱 레지스트리 (django.setup 뒤 ORM) — 파일 사진이 아니다",
    )
    raise SystemExit(main())
