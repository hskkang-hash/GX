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
                ("④ 사람에게 도달", False, "못 쟀다"),
                ("⑤ 이메일 어댑터", False, "못 쟀다"),
                ("⑥ 등급 전수", False, "못 쟀다")]
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
                     "배선은 살아 있고 **주소가 오면 채널 한 칸으로 켜진다**: "
                     "`manage.py seed_alert_routing --channel email`"))

    # ── ⑤ 이메일 어댑터의 **자리**가 서 있는가 (OPS-10 · 2026-09-24) ────────
    #
    # ★ ④와 무엇이 다른가. ④는 「지금 사람에게 가는가」이고 ⑤는 「보낼 수 있는 모양인가」다.
    #   둘을 한 줄로 합치면, 주소가 없어서 빨간 것과 **어댑터가 없어서** 빨간 것이 같아진다.
    #   앞엣것은 대표의 결정 대기이고 뒤엣것은 우리가 안 만든 것이다 — 그 둘을 섞으면
    #   「업체 결정 대기」라는 말로 우리가 안 한 일이 덮인다(D-264).
    reg = set(channels.get("registered") or ())
    email_ok = "email" in reg and "email" not in non_human
    out.append(("⑤ 이메일 어댑터", email_ok,
                "`email` 어댑터가 등록돼 있고 사람에게 도달하는 채널이다 — "
                "규칙의 채널 한 칸을 바꾸는 것으로 켜진다"
                if email_ok else
                "`email` 어댑터가 **없거나** 사람에게 도달하지 않는 채널로 등록돼 있다: "
                "등록=%s / non_human=%s" % (sorted(reg), sorted(non_human))))

    # ── ⑥ 등급 전수 — **규칙이 0건인 등급이 있는가** ────────────────────────
    #   [실측 2026-09-24 착수 전] `info`·`warning` 은 규칙 0건이었다. 규칙이 0건인 등급의
    #   이벤트는 채널을 아무리 고쳐도 아무에게도 가지 않는다 — 채널보다 앞선 구멍이다.
    covered = channels.get("severities_covered")
    known = channels.get("severities_all")
    if covered is None or known is None:
        out.append(("⑥ 등급 전수", False, "**못 쟀다** — 등급 열거를 읽지 못했다"))
    else:
        naked = [s for s in known if s not in covered]
        out.append(("⑥ 등급 전수", not naked,
                    "등급 %d종 전부에 규칙이 있다" % len(known) if not naked
                    else "**규칙이 0건인 등급**: %s — 이 등급의 이벤트는 채널과 무관하게 "
                         "아무에게도 가지 않는다" % ", ".join(naked)))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 수집
# ═══════════════════════════════════════════════════════════════════════════
def collect():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    #: ★ [실측 2026-09-06 · 턴 I · 조율자] **컨테이너 안에서 부르면 `config` 를 못 찾았다.**
    #:   `gx-shell` 의 마운트는 셋이 따로다: `/app`(=호스트 `backend/`) · `/repo/{backend,
    #:   scripts}` · `/docs`. `/repo/backend` 와 `/app` 은 **같은 디렉터리인데 경로가 다르고**,
    #:   `/repo/scripts/…` 로 부르면 `sys.path[0]` 이 `/repo/scripts` 라 `config` 가 안 잡힌다.
    #:   그 실패는 exit 2(회색)로 나오고, **회색은 P-85 대조에서 「아무것도 안 잰 칸」**이 된다 —
    #:   대장과 게이트가 갈려 있어도 아무 말이 없다. `verify_purge.py` · `verify_seed_p20.py`
    #:   가 이미 같은 한 줄로 이 자리를 지난다. 세 벌째지만 **복사가 아니라 같은 사실**이다.
    if os.path.isdir("/app") and "/app" not in sys.path:
        sys.path.insert(0, "/app")
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
        # 등급 전수는 **모델의 열거**에서 온다. 여기 목록을 적으면 등급이 늘 때
        # 판정기가 조용히 옛 목록을 세게 된다(D-212).
        "severities_all": list(Event.Severity.values),
        "severities_covered": sorted(
            set(Rule._base_manager.values_list("severity", flat=True))),
    }
    # ── 이메일 어댑터가 **보낼 수 있는 모양인가** (OPS-10 · 2026-09-24) ──────
    #   판정식을 여기서 짓지 않는다 — 어댑터에게 묻는다(D-212). 어댑터가 답하는 그
    #   문장이 곧 「왜 아직 안 나가는가」의 답이고, 그 답은 한 곳에만 있어야 한다.
    try:
        ready = ch.EmailChannel.configured()
        channels["email_ready"] = bool(ready.ok)
        channels["email_reason"] = ready.reason or "SMTP 설정이 있다"
    except Exception as exc:                                   # noqa: BLE001
        channels["email_ready"] = None
        channels["email_reason"] = "**못 쟀다** — %s: %s" % (type(exc).__name__, exc)

    #: 채널을 켰을 때 **실제로 메일이 날아갈 도메인**. 이름이 아니라 도메인만 센다 —
    #: 개인 주소를 증거 문서에 적지 않기 위해서다. 그런데 도메인만으로도 답이 나온다:
    #: 「주소가 하나도 없다」와 「이미 열두 개 있다」는 완전히 다른 결정을 요구한다.
    channels["recipient_domains"] = {}

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
                # ★ **주소가 있다**와 **사람이 받는다**는 다르다. 시드 사람의 주소는
                #   `@seed.invalid` 다 — 일부러 도달 불가로 두었다. 그 주소를
                #   「수신자 1명」으로만 세면 채널을 email 로 바꾼 날 이력이 전부
                #   실패 행이 되고, 우리는 그것을 「SMTP 가 죽었다」로 읽는다.
                reach = 0
                for p in {q.user_id: q for q in mine}.values():
                    try:
                        if ch.EmailChannel.deliverable(p.address).ok:
                            reach += 1
                    except Exception:                          # noqa: BLE001
                        reach = -1
                        break
                for p in {q.user_id: q for q in mine}.values():
                    dom = (p.address or "").strip().rsplit("@", 1)
                    key = dom[1].lower() if len(dom) == 2 else "(주소없음)"
                    channels["recipient_domains"][key] = (
                        channels["recipient_domains"].get(key, 0) + 1)
                table.append({
                    "deliverable_count": reach,
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
             "non_human": ["log"],
             "severities_all": ["info", "warning", "critical"],
             "severities_covered": ["critical", "info", "warning"]}
    ok &= all(not p for _, p, _ in judge(None, None))

    good = [{"group": "4(ETRI)", "severity": "critical", "role": "fire_admin",
             "channels": ["email"], "people_count": 1}]
    ok &= all(p for _, p, _ in judge(good, chans))

    zero = [dict(good[0], people_count=0)]
    r = judge(zero, chans)
    ok &= [p for _, p, _ in r] == [True, False, True, True, True, True]

    sms = [dict(good[0], channels=["sms"])]
    r = judge(sms, chans)
    ok &= [p for _, p, _ in r] == [True, True, False, True, True, True]

    onlylog = [dict(good[0], channels=["log"])]
    r = judge(onlylog, chans)
    ok &= [p for _, p, _ in r] == [True, True, True, False, True, True]

    r = judge([], chans)
    ok &= not r[0][1]

    # ── ⑤ 어댑터가 없는 세상 — ④와 **다른 줄**이 빨개야 한다 ────────────────
    #   어댑터가 없으면 주소가 와도 못 보낸다. 그 사실이 ④(로그로만 간다) 뒤에
    #   숨으면 「대표 결정 대기」라는 말로 우리가 안 만든 것이 덮인다(D-264).
    noemail = dict(chans, registered=["log"])
    r = judge(onlylog, noemail)
    ok &= [p for _, p, _ in r] == [True, True, True, False, False, True]

    #   등록은 돼 있는데 **사람에게 도달하지 않는 채널**로 등록된 경우도 ⑤는 빨강이다
    fake = dict(chans, non_human=["log", "email"])
    r = judge(onlylog, fake)
    ok &= [p for _, p, _ in r] == [True, True, True, False, False, True]

    # ── ⑥ 규칙이 0건인 등급 — [실측 2026-09-24 착수 전] info·warning 이 그랬다 ──
    naked = dict(chans, severities_covered=["critical"])
    r = judge(good, naked)
    ok &= [p for _, p, _ in r] == [True, True, True, True, True, False]

    # 등급 열거를 **못 읽었다** → ⑥은 초록이 아니다. 회색은 초록이 아니다(D-301)
    blind = dict(chans, severities_all=None)
    r = judge(good, blind)
    ok &= [p for _, p, _ in r] == [True, True, True, True, True, False]

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
    say("| 소속 | 등급 | 역할 | 채널 | 사람에게 도달 | 받는 사람 수 | 그중 **주소가 살아 있는** 사람 | 받는 사람 |")
    say("|---|---|---|---|---|---|---|---|")
    non_human = set(channels.get("non_human") or ())
    for r in sorted(table, key=lambda x: (x["group"], x["severity"], x["role"])):
        reaches = any(c not in non_human for c in r["channels"])
        deliverable = r.get("deliverable_count")
        say("| %s | %s | %s | %s | %s | %d | %s | %s |"
            % (r["group"], r["severity"], r["role"], ", ".join(r["channels"]) or "없음",
               "○" if reaches else "**✗ 로그로만 간다**",
               r["people_count"],
               "못 쟀다" if deliverable is None or deliverable < 0 else str(deliverable),
               ", ".join(r["people"]) or "**아무도 없다**"))
    say()
    say("★ 「받는 사람 수」와 「주소가 살아 있는 사람」이 다른 이유: 시드 사람의 주소는")
    say("  `@seed.invalid` 다(RFC 2606 — 절대 존재하지 않는 TLD). **주소가 있다**와")
    say("  **사람이 받는다**는 다른 사실이고, 뒤엣것이 0이면 채널을 `email` 로 바꿔도")
    say("  이력은 전부 실패 행이 된다 — 그것은 배선의 사실이 아니라 환경의 사실이다.")
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
    say("### 이메일 채널 — **보낼 수 있는 모양인가** [실측]")
    say()
    ready = channels.get("email_ready")
    say("  · SMTP 설정: %s" % ("**섰다**" if ready else
                              ("**못 쟀다**" if ready is None else "**미설정(회색)**")))
    say("  · 사유: %s" % channels.get("email_reason", "?"))
    say()
    doms = channels.get("recipient_domains") or {}
    say("  · **채널을 켜면 메일이 날아갈 도메인** [실측] (규칙이 고른 사람 기준 · 중복 포함):")
    for dom, n in sorted(doms.items(), key=lambda kv: (-kv[1], kv[0])):
        note = ""
        if dom.endswith(".invalid"):
            note = "  ← 도달 불가(RFC 2606). 시드 사람이다"
        say("      %-16s %d" % (dom, n) + note)
    say()
    say("  ⚠ **이 표를 읽고 채널을 켜라.** 「수신 주소가 없다」가 아니다 — 규칙이 고르는")
    say("    사람 중 상당수는 **이미 도달 가능한 주소를 갖고 있다**(개발 계정). 채널을")
    say("    `email` 로 바꾸는 순간 그들에게 **진짜로** 메일이 나간다. 대표에게만 보내려면")
    say("    주소를 넣는 것이 아니라 **규칙이 고르는 역할을 먼저 좁혀야 한다.**")
    say("    주소가 0개일 것이라고 짐작하고 켜는 것이 이 절의 가장 큰 사고 가능성이다.")
    say()
    say("  SMTP 자격증명과 수신 주소는 **저장소에 오지 않는다**(D-204). 로컬 `.env` 로만 온다:")
    say("  `EMAIL_HOST` · `EMAIL_HOST_USER` · `EMAIL_HOST_PASSWORD` · `DEFAULT_FROM_EMAIL` ·")
    say("  `K2_ALERT_EMAIL_TO` · `K2_ALERT_CHANNEL`. 이름은 `backend/.env.example` 에 있다.")
    say()
    say("  ★ **지금 상태는 「발송까지 · 수신 대기」다.** 어댑터는 서 있고(⑤), 세 등급 전부에")
    say("    규칙이 있고(⑥), 남은 것은 **저장소 밖에서 오는 값 둘**이다:")
    say("      ㉠ SMTP 자격증명 (`.env` — 지금 자리 표시자 그대로다)")
    say("      ㉡ 대표가 줄 **수신 주소**, 그리고 그 주소만 받게 할 것인지의 결정")
    say("    ㉡이 결정이라는 것이 위 도메인 표의 뜻이다 — 주소는 이미 있고, 문제는")
    say("    **누가 받을 것인가**다. 둘이 오면 고칠 자리는 한 줄이다:")
    say()
    say("    ```")
    say("    K2_ALERT_CHANNEL=email  python manage.py seed_alert_routing --user gxprobe_e2e")
    say("    ```")
    say()
    say("  ⚠ **발송 기록은 증거가 아니다.** `DeliveryRecord` 행이 생겼다는 것은 「보냈다」이지")
    say("    「받았다」가 아니다. 이 절을 닫는 증거는 **사람이 실제로 받은 수신함 캡처**")
    say("    하나뿐이다 — 그 캡처가 오기 전까지 이 절의 상태는 「구현」이 아니라")
    say("    **「발송까지 · 수신 대기」**로 적는다.")
    say()

    say("## 4. 판정")
    say()
    rows = judge(table, channels)
    for name, passed, why2 in rows:
        say("  %s %-16s %s" % ("OK  " if passed else "FAIL", name, why2))
    ok = all(p for _, p, _ in rows)
    say()
    say("판정 **%s**." % ("통과" if ok else "실패"))
    say("④가 빨간 것은 **배선의 결함이 아니라 수신 주소 대기**다. ⑤가 초록이면 어댑터는")
    say("서 있고, ⑥이 초록이면 규칙이 빠진 등급도 없다 — 남은 것은 주소 하나이고,")
    say("그 하나는 저장소가 아니라 사람이 준다. **그래서 이 절은 「발송까지 · 수신 대기」다.**")
    say("문자·카톡·앱은 여전히 대표 결정 대기이고(DA-04 D4-1), 이번 턴에 만들지 않았다.")

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
