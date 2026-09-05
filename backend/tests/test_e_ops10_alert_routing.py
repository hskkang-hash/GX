# -*- coding: utf-8 -*-
"""OPS-10 — 경보가 **사람에게 나갈 수 있는 모양인가** (2026-09-24 · 차선 E).

이 파일이 세우려는 사실은 하나다: **주소 하나만 넣으면 경보가 나간다.**
그 문장을 문서가 아니라 시험이 말해야 한다 — 없는 시험은 문서다.

착수 전 실측 (개발 DB · 소속 4 ETRI-Group)
------------------------------------------
    규칙 4건 · **전부 채널 `log`** → 사람에게 도달하는 경보 **0건**
    `info` 규칙 0건 · `warning` 규칙 0건 → 그 등급의 이벤트는 아무에게도 안 간다

★ 여기서 재지 **않는** 것 — 그것이 이 절의 요점이다
---------------------------------------------------
이 시험은 「사람이 받았다」를 재지 않는다. **잴 수 없다.** locmem 백엔드의
`mail.outbox` 는 「보낼 물건이 만들어졌다」이지 「수신함에 들어갔다」가 아니고,
`DeliveryRecord` 행은 「보냈다」이지 「받았다」가 아니다.

    ⚠ **발송 기록은 증거가 아니다.** 이 절을 닫는 증거는 사람이 실제로 받은
      수신함 캡처 하나뿐이다. 그 캡처가 오기 전까지 절의 상태는 「구현」이 아니라
      **「발송까지 · 수신 대기」**다.

그러므로 이 파일이 재는 것은 셋뿐이다:
  ① 자리 표시자 SMTP 를 **회색이라고 말하는가** (「설정 안 함」과 「설정했는데 틀림」)
  ② 도달할 수 없는 주소를 **도달한다고 세지 않는가** (`@…invalid`)
  ③ 주소가 살아 있으면 **실제로 메일 물건이 만들어지는가** — 그리고 채널이 `log` 면
     행은 남되 **메일은 안 만들어지는가** (양성 대조)
"""
from __future__ import annotations

import contextlib
from datetime import timedelta

from django.apps import apps
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

#: 자리 표시자 — `config/settings.py::EMAIL_PLACEHOLDER_VALUES` 와 **같은 뜻**의 값이다.
#: 시험이 그 목록을 복사하지 않고 `override_settings` 로 **직접 넣는다** — 목록을
#: 복사하면 목록이 바뀔 때 시험이 옛 목록을 계속 통과시킨다(D-369).
PLACEHOLDERS = ("your-email@gmail.com", "your-app-password", "CHANGE_ME", "")

REAL_SMTP = dict(
    EMAIL_PLACEHOLDER_VALUES=PLACEHOLDERS,
    EMAIL_HOST="smtp.example-real.test",
    EMAIL_HOST_USER="alerts@example-real.test",
    EMAIL_HOST_PASSWORD="not-a-real-secret-value",
    DEFAULT_FROM_EMAIL="alerts@example-real.test",
)


# ═══════════════════════════════════════════════════════════════════════════
# ① SMTP 미설정은 **회색이다.** 회색은 초록이 아니다
# ═══════════════════════════════════════════════════════════════════════════
class EmailChannelReadinessTest(TestCase):
    """★ 왜 이 시험이 필요한가 — **자리 표시자는 값처럼 보인다.**

    `EMAIL_HOST_USER` 의 기본값은 `your-email@gmail.com` 이다. 진위로 물으면
    「값이 있다」가 나오고, 진짜 실패는 발송을 시도한 뒤 SMTP 인증 오류로만 드러난다.
    그러면 「설정 안 함」과 「설정했는데 틀림」이 같은 모양이 된다(D-290).
    """

    def test_placeholder_smtp_is_reported_as_unconfigured(self) -> None:
        from kernels.k2_notify.channels import EmailChannel

        with override_settings(
                EMAIL_PLACEHOLDER_VALUES=PLACEHOLDERS,
                EMAIL_HOST="smtp.gmail.com",
                EMAIL_HOST_USER="your-email@gmail.com",
                EMAIL_HOST_PASSWORD="your-app-password",
                DEFAULT_FROM_EMAIL="your-email@gmail.com"):
            verdict = EmailChannel.configured()

        self.assertFalse(
            verdict.ok,
            "자리 표시자 그대로인데 **설정됐다**고 답했습니다 — 그러면 "
            "「설정 안 함」과 「설정했는데 틀림」이 같은 모양이 됩니다.")
        for key in ("EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD", "DEFAULT_FROM_EMAIL"):
            self.assertIn(key, verdict.reason,
                          f"어느 칸이 비었는지 사유가 말하지 않습니다: {verdict.reason}")

    def test_real_smtp_values_are_reported_as_configured(self) -> None:
        """★ **양성 대조.** 늘 회색인 판정기는 아무것도 판정하지 않는다(D-277)."""
        from kernels.k2_notify.channels import EmailChannel

        with override_settings(**REAL_SMTP):
            verdict = EmailChannel.configured()
        self.assertTrue(verdict.ok,
                        f"실값을 넣었는데도 회색입니다: {verdict.reason}")

    def test_readiness_does_not_send_anything(self) -> None:
        """설정을 묻는 것이 **발송이 되면 안 된다** — 이력이 오염된다."""
        from kernels.k2_notify.channels import EmailChannel

        with override_settings(**REAL_SMTP):
            EmailChannel.configured()
        self.assertEqual(0, len(mail.outbox),
                         "「보낼 수 있는가」를 묻는 것만으로 메일이 나갔습니다.")


# ═══════════════════════════════════════════════════════════════════════════
# ② 주소가 있다 ≠ 사람이 받는다
# ═══════════════════════════════════════════════════════════════════════════
class DeliverableAddressTest(TestCase):
    """시드 사람의 주소는 `@seed.invalid` 다 — RFC 2606 이 「절대 존재하지 않는다」고
    못 박은 TLD 이고, 일부러 그렇게 두었다. 그 주소를 「수신자 1명」으로 세면
    **경보가 도달한다**는 거짓 초록이 선다.
    """

    def test_invalid_tld_is_not_deliverable(self) -> None:
        from kernels.k2_notify.channels import EmailChannel

        for address in ("gxseed_u1_operator@seed.invalid", "x@test.invalid"):
            with self.subTest(address=address):
                verdict = EmailChannel.deliverable(address)
                self.assertFalse(verdict.ok,
                                 f"{address} 를 도달 가능하다고 답했습니다.")
                self.assertIn(".invalid", verdict.reason)

    def test_empty_address_is_not_deliverable(self) -> None:
        from kernels.k2_notify.channels import EmailChannel

        self.assertFalse(EmailChannel.deliverable("").ok)
        self.assertFalse(EmailChannel.deliverable("   ").ok)

    def test_ordinary_address_is_deliverable(self) -> None:
        """양성 대조 — 전부 거절하는 판정기는 판정기가 아니다."""
        from kernels.k2_notify.channels import EmailChannel

        self.assertTrue(EmailChannel.deliverable("duty@example-real.test").ok)


# ═══════════════════════════════════════════════════════════════════════════
# 등급 × 역할 표 — **세 등급 전부에 규칙이 서는가**
# ═══════════════════════════════════════════════════════════════════════════
class RoutingMatrixTest(TestCase):
    """[실측 2026-09-24 착수 전] `info`·`warning` 은 규칙 **0건**이었다.

    규칙이 0건인 등급의 이벤트는 채널을 아무리 고쳐도 아무에게도 가지 않는다 —
    채널보다 **앞선** 구멍이다.
    """

    def test_every_severity_has_a_row(self) -> None:
        from stream_monitors.management.commands.seed_alert_routing import ROUTING

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        covered = {severity for severity, _codes, _why in ROUTING}
        missing = [s for s in Event.Severity.values if s not in covered]
        self.assertFalse(
            missing,
            f"규칙이 서지 않는 등급이 있습니다: {missing} — "
            f"그 등급의 이벤트는 채널과 무관하게 아무에게도 가지 않습니다.")

    def test_lower_severity_is_never_wider(self) -> None:
        """★ 이 표의 **근거 자체**를 시험한다.

        근거는 「등급이 낮을수록 좁게 부른다」이고, 그 이유는 경보 피로다 —
        낮은 등급을 넓게 잡으면 `critical` 의 도달이 깎인다. 근거를 주석으로만
        적어 두면 다음 사람이 한 줄 늘리면서 그 근거를 깬다.
        """
        from stream_monitors.management.commands.seed_alert_routing import ROUTING

        by_severity = {sev: set(codes) for sev, codes, _why in ROUTING}
        self.assertLessEqual(by_severity["info"], by_severity["warning"],
                             "info 가 warning 보다 넓습니다 — 경보 피로의 방향이 뒤집혔습니다.")
        self.assertLessEqual(by_severity["warning"], by_severity["critical"],
                             "warning 이 critical 보다 넓습니다 — 같은 이유로 뒤집혔습니다.")

    def test_no_delivery_domain_role_leaks_into_disaster_routing(self) -> None:
        """§0.4 금지구역의 역할이 재난 경보 수신자로 새어 들어오지 않는가.

        배송·주문·드론 역할은 이 제품(재난안전)의 역할이 아니다. 그 역할이 표에
        들어오면 **남의 도메인 사람에게 재난 경보가 간다.**
        """
        from stream_monitors.management.commands.seed_alert_routing import ROUTING

        forbidden = ("order", "delivery_", "drone_robot_")
        for severity, codes, _why in ROUTING:
            for code in codes:
                self.assertFalse(
                    code.startswith(forbidden),
                    f"{severity} 에 §0.4 도메인 역할이 있습니다: {code}")


# ═══════════════════════════════════════════════════════════════════════════
# ③ 주소가 살아 있으면 **나간다** · 채널이 log 면 **안 나간다**
# ═══════════════════════════════════════════════════════════════════════════
class OneAddressAwayTest(TestCase):
    """「주소 하나만 넣으면 나간다」를 **실물로** 보인다.

    ⚠ 여기서 보이는 것은 「메일 물건이 만들어졌다」까지다. 도달은 수신함만 답한다.
    """

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        # ★ 스레드에 남은 요청이 거짓 초록을 만든다 — 앞선 시험이 HTTP 를 때렸으면
        #   여기서 `Model.objects` 가 통째로 빈다(`_base_manager` 는 안 빈다).
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        UserGroup = apps.get_model("user", "UserGroup")
        Role = apps.get_model("role", "Role")
        CoreUser = apps.get_model("user", "CoreUser")
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")

        cls.group = UserGroup.objects.create(name="ops10-tenant")
        UserGroup.objects.filter(pk=cls.group.pk).update(created_by=None)

        cls.role = cls._own(Role.objects.create(role_name="ops10_duty",
                                                code="ops10_duty"))
        #: **도달 가능한 주소**다. `.invalid` 가 아니다 — 그것이 이 시험의 전부다.
        cls.address = "duty@example-real.test"
        cls.user = CoreUser.objects.create_user(
            username="ops10_duty_user", password="test-only-not-a-secret",
            is_active=True, email=cls.address)
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: cls.user, "group": cls.group})
        cls.user.roles.add(cls.role)

        cls.stream = cls._own(StreamMonitor.objects.create(
            name="ops10-stream", code="ops10-stream",
            ip_source="rtsp://test.invalid/ops10"))

        from common.tenant_scope import TenantScope

        cls.scope = TenantScope.of(cls.user)
        cls.scope_pipe = TenantScope.system(
            reason="OPS-10 시험 — 발송 파이프라인에는 요청자가 없다 (D-281)")

    @staticmethod
    def _own(obj):
        """소유 필드 이름은 **커널의 판단기**를 그대로 쓴다 (D-212)."""
        from kernels.k1_event.services import _owner_field

        group = OneAddressAwayTest.group
        if _owner_field(type(obj)) == "groups":
            obj.groups.set([group])
        else:
            obj.group = group
            obj.save(update_fields=["group"])
        return obj

    def _rule(self, channel, severity="critical"):
        """규칙은 **K2 진입 경로로** 만든다 — 행을 직접 만들면 네 검사가 안 돈다."""
        from kernels.k2_notify import save_notification_rule

        return save_notification_rule(
            scope=self.scope, severity=severity, role_code=self.role.code,
            channels=[channel], zone=None, is_active=True, group=self.group)

    def _event(self, severity="critical"):
        from kernels.k1_event import record_detection

        self._nth = getattr(self, "_nth", 0) + 1
        return record_detection(
            scope=self.scope_pipe, stream_monitor_id=self.stream.pk,
            event_type="fire", severity=severity,
            occurred_at=timezone.now() - timedelta(seconds=600 * self._nth),
            snapshot_path=f"minio://ops10/{self._nth}.jpg",
        ).event_id

    def test_email_channel_actually_produces_a_message(self) -> None:
        from kernels.k2_notify import send

        self._rule("email")
        records = send(scope=self.scope, event_id=self._event())

        self.assertEqual(1, len(records), "수신자 1명인데 이력이 1건이 아닙니다.")
        self.assertTrue(records[0].succeeded,
                        f"발송이 실패했습니다: {records[0].failure_reason}")
        self.assertEqual(1, len(mail.outbox),
                         "채널을 email 로 했는데 **메일 물건이 만들어지지 않았습니다.**")
        self.assertIn(self.address, mail.outbox[0].to,
                      "메일이 그 사람의 주소로 가지 않았습니다.")

    def test_log_channel_leaves_a_row_but_reaches_no_human(self) -> None:
        """★ **양성 대조.** `log` 가 조용히 사람에게 도달하면 안 된다.

        [실측 2026-09-24] 개발 DB 의 규칙 4건이 전부 이 채널이었다. 그 상태에서
        발송 이력은 쌓이고 화면은 조용하다 — 「보냈다」로 읽히는 자리다.
        """
        from kernels.k2_notify import channels as ch
        from kernels.k2_notify import send

        self._rule("log")
        records = send(scope=self.scope, event_id=self._event())

        self.assertEqual(1, len(records), "행이 남지 않았습니다 — 실패도 행이어야 합니다.")
        self.assertEqual(0, len(mail.outbox),
                         "`log` 채널인데 메일이 나갔습니다 — 이름을 가장한 것입니다.")
        self.assertIn("log", ch.NON_HUMAN,
                      "`log` 가 사람에게 도달하는 채널로 등록돼 있습니다.")

    def test_switching_the_channel_is_the_only_change_needed(self) -> None:
        """규칙의 정체는 (등급·역할·구역)이고 **채널은 정체가 아니다.**

        같은 자리를 다시 저장하면 규칙이 하나 더 서는 것이 아니라 채널만 바뀌어야
        한다. 하나 더 서면 그 순간 당직자는 **두 번 받는다.**
        """
        from kernels.k2_notify import save_notification_rule, send

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        first = self._rule("log")
        self.assertEqual(1, Rule.objects.filter(role=self.role).count())

        save_notification_rule(
            scope=self.scope, severity="critical", role_code=self.role.code,
            channels=["email"], zone=None, is_active=True,
            rule_id=first.rule_id, group=self.group)
        self.assertEqual(
            1, Rule.objects.filter(role=self.role).count(),
            "채널을 바꿨더니 규칙이 하나 더 섰습니다 — 당직자가 두 번 받습니다.")

        send(scope=self.scope, event_id=self._event())
        self.assertEqual(1, len(mail.outbox),
                         "채널 한 칸을 바꿨는데 메일이 나가지 않았습니다 — "
                         "「주소 하나만 넣으면 나간다」가 거짓이 됩니다.")
