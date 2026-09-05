# -*- coding: utf-8 -*-
"""경보가 **어느 등급에서 누구에게 어떤 경로로** 가는가를 세운다 (OPS-10 · 2026-09-24 · E).

    OPS-10 경보 발송처 — "지금 **모든 규칙의 채널이 `log`** 다 — 사람에게 도달하는
    경보 0건. info·warning 등급은 규칙 0건."          — 차선 E 지시 2026-09-24 §2

착수 전 실측 — **배선은 살아 있고, 켜져 있지 않았다**
-----------------------------------------------------
    [실측 2026-09-24 · database_guardianx · 소속 4 ETRI-Group]
      규칙 #9  critical / fire_user           channels=['log']
      규칙 #10 critical / operator            channels=['log']
      규칙 #11 critical / fire_admin          channels=['log']
      규칙 #12 critical / view_only_-_anyang  channels=['log']
      info    규칙 **0건**
      warning 규칙 **0건**   ← 시드 이벤트의 침입·사람·시스템 이벤트가 이 등급이다

`log` 는 사람이 아니라 로그에 도달한다(`kernels/k2_notify/channels.py::LogChannel`).
그러므로 위 표가 말하는 것은 「경보가 네 갈래로 간다」가 아니라
**「사람에게 도달하는 경보가 0건이다」**다.

이 명령이 하는 일 — **주소 하나만 넣으면 나가는 상태**까지
------------------------------------------------------------
    ① 세 등급(`info`·`warning`·`critical`) 전부에 규칙을 세운다
    ② 채널을 고를 수 있게 한다 (`--channel log|email`, 기본값은
       `settings.K2_ALERT_CHANNEL` ← 환경변수 `K2_ALERT_CHANNEL`)
    ③ `email` 을 고르면 **보낼 수 있는 모양인지 먼저 묻는다.** SMTP 가 자리 표시자
       그대로이거나 도달 가능한 수신 주소가 하나도 없으면 **심지 않고 멈춘다**

★ ③이 이 명령의 요점이다 — **주소 없이 규칙만 email 로 바꾸면 더 나빠진다**
---------------------------------------------------------------------------
그렇게 하면 발송 이력이 **전부 실패 행**이 된다. 모바일 M1(내게 온 이벤트)은
「알림이 있었다」와 「알림이 실패했다」를 구별하는 화면이어야 하는데, 실패만 보이는
화면이 된다. 그리고 그 실패는 **배선의 사실이 아니라 환경의 사실**이다 —
같은 착시를 `seed_dsm_events` 가 `log` 채널을 고른 이유로 이미 적어 두었다.

★ **발송 기록은 증거가 아니다.** 증거는 사람이 실제로 받은 수신함이다
---------------------------------------------------------------------
이 명령이 초록이어도 그것이 말하는 것은 「보낼 수 있는 모양이 됐다」까지다.
「사람이 받았다」는 **수신함 캡처만** 말할 수 있다. 그 둘을 섞으면
`DeliveryRecord` 행 하나가 도달의 증거로 둔갑한다(D-284 조용한 성공).

    python manage.py seed_alert_routing --user gxprobe_e2e --report
    python manage.py seed_alert_routing --user gxprobe_e2e                  # 기본 채널
    K2_ALERT_CHANNEL=email K2_ALERT_EMAIL_TO=… \
        python manage.py seed_alert_routing --user gxprobe_e2e --channel email

⚠ 수신 주소·SMTP 자격증명은 **저장소에 넣지 않는다**(D-204). 로컬 `.env` 로만 온다.

⚠ **`seed_dsm_events --purge` 와 겹치는 자리가 있다.** 그 명령의 `_purge_rules` 는
  「채널이 `[log]` 인 규칙」을 그 소속에서 지운다 — 채널 하나가 「시드가 만든 규칙」의
  유일한 근거이기 때문이다. 그러므로 이 명령이 `log` 로 세운 `info`·`warning` 규칙도
  그때 함께 지워진다. 지워졌다면 이 명령을 다시 부르면 된다(두 번 돌려도 두 배가
  되지 않는다). 채널을 `email` 로 바꾼 뒤에는 그 purge 가 이 규칙들을 **못 찾는다** —
  그것도 사실이므로 적어 둔다.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

# ═══════════════════════════════════════════════════════════════════════════
# 등급 × 역할 — **[판정]이다. 인용이 아니다**
# ═══════════════════════════════════════════════════════════════════════════
#
# 계약에 「info 는 누구에게 가는가」가 적혀 있지 않다(실측 — DA-04 §2 K2 는 등급별
# 수신자를 정하지 않았다). 그러므로 아래 표는 **이 명령의 판정**이고, 판정에는 근거가
# 붙어야 한다. 근거는 하나다:
#
#   ★ **등급이 낮을수록 좁게 부른다.** 낮은 등급까지 전원을 부르면 경보 피로가 생기고,
#     경보 피로는 `critical` 을 못 보게 만든다 — 즉 낮은 등급을 넓게 잡는 것이
#     **높은 등급의 도달을 깎는다.** 알림 예산(`k2_notify/alarm_budget.py`)이 같은 말을
#     수로 하고 있다.
#
#   ⚠ 이 표는 **개발 DB 를 세우는 값**이지 고객의 정책이 아니다. 고객 환경의 정책은
#     화면(수신자 그룹 위젯)에서 정하고, 그 화면은 같은 `save_notification_rule` 을
#     부른다 — 즉 이 명령과 화면은 **같은 자리**를 통과한다.
ROUTING = (
    # (등급, 역할코드들, 왜 이 등급에 이 사람인가)
    ("critical", ("fire_user", "operator", "fire_admin", "view_only_-_anyang"),
     "재난이다. 당직자·팀장·담당 공무원 전원이 안다 — 여기서 좁히면 사람이 죽는다"),
    ("warning", ("fire_user", "operator", "fire_admin"),
     "조치가 필요하지만 재난은 아니다. 화면 앞 당직자와 팀장까지. "
     "열람 전용 공무원(U4)을 여기서 부르면 그가 critical 을 못 알아본다"),
    ("info", ("fire_user", "operator"),
     "알아두면 되는 일. **화면 앞에 앉아 있는 사람만** 부른다 — "
     "이 등급을 넓히면 경보 피로가 생기고, 경보 피로는 critical 의 도달을 깎는다"),
)

#: 구역 라벨. `None` 이면 모든 구역이다 — 구역 체계는 P-K2-2 로 적재돼 있고(미정),
#: 미정인 체계를 시드가 지어내지 않는다(D-280).
ZONE = None


class Command(BaseCommand):
    help = "세 등급 전부에 알림 규칙을 세운다 — 채널을 고를 수 있다 (OPS-10)"

    def add_arguments(self, parser):
        parser.add_argument("--user", default="gxprobe_e2e",
                            help="이 계정의 소속에 규칙을 세운다")
        parser.add_argument("--channel", default=None,
                            help="log | email. 없으면 settings.K2_ALERT_CHANNEL 을 읽는다")
        parser.add_argument("--report", action="store_true", help="세기만 한다")
        parser.add_argument("--allow-undeliverable", action="store_true",
                            help="도달할 수 없는 주소뿐이어도 email 규칙을 세운다. "
                                 "**이력이 전부 실패 행이 된다** — 그것을 알고 켜는 스위치다")

    # ── 소속 ─────────────────────────────────────────────────────────────
    def _group(self, username):
        """소속은 **제품이 읽는 방식 그대로** 읽는다 — 두 벌로 읽으면 갈린다(D-369)."""
        from django.contrib.auth import get_user_model

        from common.tenant_filters import get_user_group

        user = get_user_model()._base_manager.filter(username=username).first()
        if user is None:
            raise CommandError("계정이 없다: %s" % username)
        group = get_user_group(user)
        if group is None:
            raise CommandError("%s 에 소속이 없다 — 격리를 끄지 않는다(D-105)" % username)
        return user, group

    # ── 채널을 고를 수 있는가 ────────────────────────────────────────────
    def _check_channel(self, channel, scope, group, allow_undeliverable):
        """**보낼 수 있는 모양인가**를 먼저 묻는다. 못 보내면 심지 않는다.

        ★ 여기서 통과했다고 「사람이 받는다」가 아니다. 통과한 것은
          「보낼 수 있는 모양」까지이고, 도달은 수신함만 답한다.
        """
        from kernels.k2_notify import channels as ch
        from kernels.k2_notify import resolve_recipients

        if ch.get(channel) is None:
            raise CommandError("보낼 수 없는 채널이다: %s" % ch.why_unavailable(channel))

        if channel in ch.NON_HUMAN:
            self.stdout.write(
                "[ROUTE] ⚠ 채널 `%s` 는 **사람이 아니라 로그에 도달한다.** 이 규칙으로는 "
                "당직자가 아무것도 못 받는다 — 그 사실은 발송 이력의 channel 칸에 남는다"
                % channel)
            return

        if channel != ch.EmailChannel.name:
            return

        ready = ch.EmailChannel.configured()
        if not ready.ok:
            raise CommandError(
                "%s\n"
                "  → 규칙만 email 로 바꾸면 발송 이력이 **전부 실패 행**이 된다. "
                "그것은 배선의 사실이 아니라 환경의 사실이다. 심지 않는다." % ready.reason)

        # 도달 가능한 주소를 가진 사람이 하나라도 있는가 — **주소가 있다와 도달한다는 다르다**
        reachable, unreachable = [], []
        for severity, codes, _why in ROUTING:
            for r in resolve_recipients(scope=scope, severity=severity, group=group):
                if r.role_code not in codes:
                    continue
                verdict = ch.EmailChannel.deliverable(r.address)
                (reachable if verdict.ok else unreachable).append(
                    (r.display_name, r.address, verdict.reason))
        if not reachable and not allow_undeliverable:
            raise CommandError(
                "SMTP 는 섰는데 **도달할 수 있는 주소가 0개**다. 지금 잡히는 주소: %s\n"
                "  → 수신 주소는 저장소에 오지 않는다(대표가 로컬 `.env`·계정으로 준다). "
                "주소 하나가 들어오면 이 명령을 다시 부르는 것으로 끝난다. "
                "정말로 실패 행을 남기려면 --allow-undeliverable 을 준다."
                % (", ".join(sorted({a for _n, a, _r in unreachable})) or "없다"))
        self.stdout.write("[ROUTE] [실측] 도달 가능한 주소를 가진 수신자 %d명 · "
                          "도달 불가 %d명" % (len(reachable), len(unreachable)))

    # ── 규칙 ─────────────────────────────────────────────────────────────
    def _apply(self, scope, group, channel):
        """세 등급 전부에 규칙을 세운다. **두 번 돌려도 두 배가 되지 않는다.**

        규칙의 정체는 (등급 · 역할 · 구역)이다 — **채널은 정체가 아니다.** 그래서
        같은 (등급·역할·구역) 행이 있으면 채널만 고쳐 쓴다. 채널까지 정체로 보면
        `log` 규칙 옆에 `email` 규칙이 하나 더 서고, 그때 당직자는 **두 번 받는다.**
        """
        from django.apps import apps

        from kernels.k2_notify import save_notification_rule
        from kernels.k2_notify.exceptions import InvalidNotifyInput

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        made = fixed = 0
        for severity, codes, why in ROUTING:
            self.stdout.write("[ROUTE] %-8s ← %s" % (severity, why))
            for code in codes:
                existing = Rule._base_manager.filter(
                    severity=severity, role__code=code, zone__isnull=True).first()
                try:
                    view = save_notification_rule(
                        scope=scope, severity=severity, role_code=code,
                        channels=[channel], zone=ZONE, is_active=True,
                        rule_id=existing.pk if existing else None, group=group)
                except InvalidNotifyInput as exc:
                    self.stdout.write("[ROUTE]   ⚠ %s/%s 를 못 세웠다: %s"
                                      % (severity, code, exc))
                    continue
                if existing:
                    fixed += 1
                else:
                    made += 1
                self.stdout.write("[ROUTE]   %-22s #%s 채널=%s %s"
                                  % (code, view.rule_id, ",".join(view.channels),
                                     "(고침)" if existing else "(새로)"))
        return made, fixed

    # ── 보고 ─────────────────────────────────────────────────────────────
    def _report(self, scope, group):
        """등급별로 **규칙 수**와 **닿는 사람 수**를 따로 센다.

        둘을 합쳐 세면 「규칙이 있다」가 「사람이 받는다」로 읽힌다 — 그 둘이 다른
        사실이라는 것이 이 절의 전부다(D-301).
        """
        from django.apps import apps

        from kernels.k2_notify import channels as ch
        from kernels.k2_notify import resolve_recipients

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        self.stdout.write("[ROUTE] ── 등급별 규칙 · 수신자 (소속 %s) ──" % group.pk)
        for severity in Event.Severity.values:
            rows = list(Rule._base_manager.filter(severity=severity))
            chans = sorted({c for r in rows for c in (r.channels or [])})
            human = [c for c in chans if c not in ch.NON_HUMAN]
            try:
                people = resolve_recipients(scope=scope, severity=severity, group=group)
            except Exception as exc:                        # noqa: BLE001
                self.stdout.write("[ROUTE]   %-9s 규칙 %d건 · 수신자 **못 쟀다**(%s)"
                                  % (severity, len(rows), exc))
                continue
            # ★ 세 상태를 **갈라서** 적는다. 규칙이 0건인 것과 규칙이 있는데 `log`
            #   인 것은 다른 사실이다 — 앞은 「잊힌 자리」이고 뒤는 「결정된 자리」다.
            #   합쳐서 「✗」로 적으면 info·warning 이 왜 안 가는지 표가 답하지 못한다.
            if not rows:
                reach = "**규칙이 없다 — 아무에게도 안 간다**"
            elif human:
                reach = "○ (%s)" % ",".join(human)
            else:
                reach = "**✗ 로그로만 간다 — 사람은 못 받는다**"
            self.stdout.write(
                "[ROUTE]   %-9s 규칙 %d건 · 채널 %s · 수신자 %d명 · 사람에게 도달 %s"
                % (severity, len(rows), ",".join(chans) or "없음", len(people), reach))

    # ── 본체 ─────────────────────────────────────────────────────────────
    def handle(self, *args, **opts):
        from django.conf import settings

        from common.tenant_scope import TenantScope

        user, group = self._group(opts["user"])
        scope = TenantScope.of(user)

        self.stdout.write("[ROUTE] ── 착수 전 ──")
        self._report(scope, group)
        if opts["report"]:
            return

        channel = (opts["channel"]
                   or getattr(settings, "K2_ALERT_CHANNEL", None) or "log")
        channel = str(channel).strip()
        self.stdout.write("[ROUTE] 채널 = %r (%s)"
                          % (channel, "인자" if opts["channel"] else
                             "settings.K2_ALERT_CHANNEL"))
        self._check_channel(channel, scope, group, opts["allow_undeliverable"])

        made, fixed = self._apply(scope, group, channel)
        self.stdout.write("[ROUTE] ── 착수 후 ──")
        self._report(scope, group)
        self.stdout.write("[ROUTE] 새로 세운 규칙 %d건 · 고친 규칙 %d건" % (made, fixed))
        if channel in ("log",):
            self.stdout.write(
                "[ROUTE] ★ 지금 상태는 **발송까지 · 수신 대기**다. 채널이 `log` 인 동안 "
                "사람에게 도달하는 경보는 0건이고, 그 사실은 이력에 그대로 남는다. "
                "주소가 오면 `--channel email` 한 번으로 끝난다.")
