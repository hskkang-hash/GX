#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-10 — **경보 발송처 표.** 누구에게 · 어떤 경로로 (2026-09-04 · 차선 E3).

    OPS-10 경보 발송처 (누구에게 · 어떤 경로로)
      "대표 결정(문자/카톡/앱) 대기 — **채널 결정 전에도 로그 어댑터로 발송처 표는
       세울 수 있다**"        — docs/agent/remaining_40.md 66행

왜 채널 결정 없이도 표가 서나
------------------------------
「어떤 경로로」는 두 질문이 겹쳐 있다:

    ㉠ **누구에게 가는가**  — 등급 × 역할 × 소속 → 사람. 지금 다 정해져 있다
    ㉡ **무엇을 타고 가는가** — 문자·카톡·앱. 업체 미선정(DA-04 D4-1)이라 미정

㉡이 미정이라고 ㉠까지 못 적는 것이 아니다. 오히려 ㉠을 안 적어 두면, 업체가 정해지는
날 「그래서 누구 번호를 넣지?」가 그제서야 질문이 된다. 그리고 **㉠에 구멍이 있으면
채널을 붙여도 그 구멍으로 새어 나간다** — 규칙은 있는데 그 역할에 사람이 0명인 자리가
정확히 그것이다(D-301: 규칙이 있다 ≠ 받을 사람이 있다).

그래서 이 판정기는 표를 **세우고**, 세우면서 구멍을 센다.

★ `log` 채널은 **사람에게 가지 않는다** — 표가 그렇게 말해야 한다
------------------------------------------------------------------
지금 규칙이 쓰는 채널은 `log` 다(`k2_notify.channels.NON_HUMAN`). 발송 이력이 쌓이므로
배선은 살아 있지만 **당직자는 아무것도 못 받는다.** 이 표에서 그 줄은
「사람에게 도달 ✗」로 찍힌다 — 「보냈다」로 읽히면 안 된다. 판정식은 복제하지 않고
커널의 `NON_HUMAN` 을 그대로 읽는다(D-212).

    docker exec -w /app -e PYTHONPATH=/app gx-shell \
        python /repo/scripts/ops_alert_routing.py \
            --evidence /docs/agent/evidence/OPS-10/routing_table.md
    python scripts/ops_alert_routing.py --self-test      # 판정 규칙만 (Django 없이)

종료 코드: 0 표를 세웠고 구멍이 없다 · 1 세웠고 **구멍이 있다** · 2 못 쟀다
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — 순수 함수 (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(table: list[dict] | None, channels: dict | None) -> list[tuple[str, bool, str]]:
    if table is None or channels is None:
        return [("① 표를 세웠는가", False, "**못 쟀다** — DB·커널에 닿지 못했다"),
                ("② 닿는 사람 0명", False, "못 쟀다"),
                ("③ 미구현 채널", False, "못 쟀다"),
                ("④ 사람에게 도달", False, "못 쟀다")]
    out = []
    out.append(("① 표를 세웠는가", bool(table),
                "규칙 %d줄을 폈다" % len(table) if table
                else "규칙이 **한 줄도 없다** — 경보는 아무에게도 가지 않는다"))

    empty = ["%s/%s/%s" % (r["group"], r["severity"], r["role"])
             for r in table if r["people_count"] == 0]
    out.append(("② 닿는 사람 0명", not empty,
                "모든 규칙에 받을 사람이 있다" if not empty
                else "규칙은 있는데 **받을 사람이 0명**: %s" % ", ".join(empty)))

    known = set(channels.get("registered") or ())
    unavail = set(channels.get("unavailable") or ())
    broken = sorted({c for r in table for c in r["channels"]
                     if c in unavail or c not in known})
    out.append(("③ 미구현 채널", not broken,
                "규칙이 가리키는 채널이 전부 등록돼 있다" if not broken
                else "**보낼 수 없는 채널**을 가리키는 규칙이 있다: %s" % ", ".join(broken)))

    non_human = set(channels.get("non_human") or ())
    human_rows = [r for r in table if any(c not in non_human for c in r["channels"])]
    out.append(("④ 사람에게 도달", bool(human_rows),
                "사람에게 닿는 규칙 %d줄" % len(human_rows) if human_rows
                else "**모든 규칙이 `log` 다 — 사람에게 도달하는 경보가 0건이다.** "
                     "배선은 살아 있고 수신 채널만 미정이다(DA-04 D4-1)"))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 수집
# ═══════════════════════════════════════════════════════════════════════════
def collect():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        import django
        django.setup()
    except Exception as exc:                                   # noqa: BLE001
        return None, None, "Django 를 못 세웠다: %s: %s" % (type(exc).__name__, exc), []

    try:
        from django.apps import apps

        from common.tenant_scope import TenantScope
        from kernels.k2_notify import resolve_recipients
        from kernels.k2_notify import channels as ch

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        Event = apps.get_model("stream_monitors", "DetectionEvent")
    except Exception as exc:                                   # noqa: BLE001
        return None, None, "커널·모델을 못 읽었다: %s: %s" % (type(exc).__name__, exc), []

    from django.contrib.auth import get_user_model
    User = get_user_model()

    channels = {
        "registered": sorted(ch.REGISTRY),
        "unavailable": dict(ch.UNAVAILABLE),
        "non_human": sorted(ch.NON_HUMAN),
    }

    # 규칙이 어느 소속에 걸리는지는 모델마다 칸 이름이 다르다 — K1 의 판정을 빌린다.
    from kernels.k1_event.services import _owner_field
    field = _owner_field(Rule)

    table: list[dict] = []
    try:
        for rule in Rule._base_manager.select_related("role").all().order_by("pk"):
            if field == "groups":
                groups = list(rule.groups.all())
            else:
                groups = [rule.group] if getattr(rule, "group", None) else []
            for group in groups:
                # 수신자는 **K2 에게 묻는다.** 여기서 다시 세면 판정식이 두 벌이 된다(D-369).
                actor = User.objects.filter(
                    userprofilelink__group=group, is_active=True).first()
                scope = (TenantScope.of(actor) if actor is not None
                         else TenantScope.system(reason="OPS-10 발송처 표 — 소속에 사람이 없다"))
                try:
                    people = resolve_recipients(scope=scope, severity=rule.severity,
                                                group=group)
                except Exception as exc:                        # noqa: BLE001
                    people = ()
                    err = "%s: %s" % (type(exc).__name__, exc)
                else:
                    err = None
                mine = [p for p in people if p.rule_id == rule.pk]
                table.append({
                    "group": "%s(%s)" % (group.pk, getattr(group, "name", "?")),
                    "severity": rule.severity,
                    "role": getattr(rule.role, "code", "?"),
                    "channels": list(rule.channels or []),
                    "zone": getattr(rule, "zone", None),
                    "active": bool(getattr(rule, "is_active", True)),
                    "people_count": len({p.user_id for p in mine}),
                    "people": sorted({p.display_name for p in mine}),
                    "error": err,
                })
    except Exception as exc:                                    # noqa: BLE001
        return None, channels, "규칙을 펴다 죽었다: %s: %s" % (type(exc).__name__, exc), []

    # ★ 구멍은 **규칙이 하나라도 있는 소속에 대해서만** 센다. 규칙이 아예 없는 소속은
    #   「경보를 안 쓰는 테넌트」이지 구멍이 아니다 — 그 둘을 합치면 표가 남의 테넌트의
    #   결정을 결함으로 세게 된다(D-264: 안 한 것과 못 한 것을 가른다).
    covered = {(r["group"], r["severity"]) for r in table}
    groups_with_rules = sorted({r["group"] for r in table})
    holes = [(g, sev) for g in groups_with_rules
             for sev in Event.Severity.values if (g, sev) not in covered]
    return table, channels, None, holes


def self_test() -> int:
    ok = True
    chans = {"registered": ["email", "log"], "unavailable": {"sms": "미선정"},
             "non_human": ["log"]}
    ok &= all(not p for _, p, _ in judge(None, None))

    good = [{"group": "4(ETRI)", "severity": "critical", "role": "fire_admin",
             "channels": ["email"], "people_count": 1}]
    ok &= all(p for _, p, _ in judge(good, chans))

    zero = [dict(good[0], people_count=0)]
    r = judge(zero, chans)
    ok &= [p for _, p, _ in r] == [True, False, True, True]

    sms = [dict(good[0], channels=["sms"])]
    r = judge(sms, chans)
    ok &= [p for _, p, _ in r] == [True, True, False, True]

    onlylog = [dict(good[0], channels=["log"])]
    r = judge(onlylog, chans)
    ok &= [p for _, p, _ in r] == [True, True, True, False]

    r = judge([], chans)
    ok &= not r[0][1]

    print("self-test: %s" % ("통과" if ok else "실패"))
    return EXIT_OK if ok else EXIT_FAIL


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    table, channels, why, holes = collect()
    if why:
        print("판정 불가(exit 2): %s" % why)
        print("  회색은 초록이 아니다 — 못 잰 것을 통과로 적지 않는다.")
        return EXIT_UNDECIDABLE

    log: list[str] = []

    def say(line: str = "") -> None:
        print(line)
        log.append(line)

    say("## 1. 발송처 표 — **누구에게**")
    say()
    say("| 소속 | 등급 | 역할 | 채널 | 사람에게 도달 | 받는 사람 수 | 받는 사람 |")
    say("|---|---|---|---|---|---|---|")
    non_human = set(channels.get("non_human") or ())
    for r in sorted(table, key=lambda x: (x["group"], x["severity"], x["role"])):
        reaches = any(c not in non_human for c in r["channels"])
        say("| %s | %s | %s | %s | %s | %d | %s |"
            % (r["group"], r["severity"], r["role"], ", ".join(r["channels"]) or "없음",
               "○" if reaches else "**✗ 로그로만 간다**",
               r["people_count"], ", ".join(r["people"]) or "**아무도 없다**"))
    say()

    say("## 2. 덮이지 않은 자리 — **아무 규칙도 없는 등급**")
    say()
    if holes:
        for g, s in holes:
            say("  · %s / `%s` — 이 등급의 이벤트는 **아무에게도 가지 않는다**" % (g, s))
        say()
        say("  ★ 이것이 결함인지 결정인지는 이 판정기가 정하지 않는다. `info`·`warning` 을")
        say("    알리지 않기로 한 것이라면 그 결정이 어디에도 안 적혀 있다는 뜻이고,")
        say("    적혀 있지 않은 결정은 **잊힌 자리**와 구별되지 않는다(D-264).")
    else:
        say("  없다 — 모든 등급에 규칙이 하나 이상 있다.")
    say()

    say("## 3. **어떤 경로로** — 채널의 지금 상태")
    say()
    say("| 채널 | 상태 | 사람에게 도달 | 사유 |")
    say("|---|---|---|---|")
    for name in sorted(set(channels["registered"]) | set(channels["unavailable"])):
        if name in channels["registered"]:
            state = "등록됨"
            reason = "어댑터가 있다"
            # ★ 등록된 채널만 「도달하는가」를 물을 수 있다. 미구현 채널에 ○/✗ 를 찍으면
            #   「보낼 수 있는데 사람에게 간다」로 읽힌다 — 보낼 수가 없다.
            reach = "✗ (로그로만)" if name in non_human else "○"
        else:
            state = "**미구현**"
            reason = channels["unavailable"][name]
            reach = "— (보낼 수 없다)"
        say("| `%s` | %s | %s | %s |" % (name, state, reach, reason))
    say()
    say("★ `log` 는 **사람이 아니라 로그에 도달한다**(`k2_notify.channels.NON_HUMAN`).")
    say("  검수 환경에 도달할 수신자가 없고 업체도 미정(DA-04 D4-1)이라 메일로 보내면")
    say("  이력이 **전부 실패 행**이 된다 — 그것은 배선의 사실이 아니라 환경의 사실이다.")
    say()

    say("## 4. 판정")
    say()
    rows = judge(table, channels)
    for name, passed, why2 in rows:
        say("  %s %-16s %s" % ("OK  " if passed else "FAIL", name, why2))
    ok = all(p for _, p, _ in rows)
    say()
    say("판정 **%s**." % ("통과" if ok else "실패"))
    say("④가 빨간 것은 **배선의 결함이 아니라 대표 결정 대기**다(DA-04 D4-1). 그 결정이")
    say("오면 고칠 자리는 규칙의 `channels` 한 칸이고, ①②③이 초록이면 그 한 칸을 바꾸는")
    say("것만으로 사람에게 간다 — 그것을 미리 확인해 두는 것이 이 표의 값이다.")

    if args.evidence:
        try:
            os.makedirs(os.path.dirname(args.evidence), exist_ok=True)
            with io.open(args.evidence, "w", encoding="utf-8") as f:
                f.write("# OPS-10 — 경보 발송처 표 (%s)\n\n"
                        % time.strftime("%Y-%m-%d %H:%M:%S"))
                f.write("**이 파일은 `scripts/ops_alert_routing.py` 가 실행하며 적었다.**\n"
                        "표의 사람·수는 K2 커널(`resolve_recipients`)이 답한 그대로다 —\n"
                        "판정식을 복제하지 않았다(D-369).\n\n")
                f.write("\n".join(log) + "\n")
            print("증거를 적었다: %s" % args.evidence)
        except OSError as exc:
            print("⚠ 증거를 못 적었다: %s" % exc)
    return EXIT_OK if ok else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
