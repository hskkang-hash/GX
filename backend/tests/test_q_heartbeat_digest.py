# -*- coding: utf-8 -*-
"""OPS-14 생존 알림(dead man's switch) — **안 오면 장애다** (2026-09-04 · 차선 Q).

무엇을 재는가
-------------
    ① 08:00 에 부르면 **발송 기록 1건**이 남는다 ← 이 절이 요구한 첫 증거
    ② 본문에 「정상 · 어제 이벤트 N · 카메라 맥박 N/N」 셋이 다 있다
    ③ 규약 문장(**안 오면 장애다**)이 본문에 실린다 — 매뉴얼과 코드가 갈리지 않게
    ④ 수신자 0명이면 **멈춘다** — 아무에게도 안 가는 생존 알림은 그 자체가 침묵이다
    ⑤ 남의 테넌트 수가 내 통에 실리지 않는다 (반출)
    ⑥ 한 번 보낼 때 감사 **한 줄**이다 — 사람 수만큼 남기면 「보냈는가」가 흐려진다
    ⑦ `digest_clock.is_late` 가 「아직 안 왔다」와 「늦었다」를 가른다

왜 ①이 「발송 기록」인가 — **새 표를 만들지 않는다** (D-333)
-----------------------------------------------------------
`DeliveryRecord` 는 이벤트에 매달린 표이고(`event` FK 는 null 이 아니다), 그 표는
F-10 의 30초를 재는 자리다. 생존 알림을 그 표에 넣으려고 FK 를 null 로 열면 그 측정이
흐려진다. 그래서 `logger.AuditLogs` 에 한 줄로 남고, 이 시험이 그 한 줄을 센다.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from django.apps import apps
from django.test import TestCase
from django.utils import timezone

from tests.test_k2_notify_kernel import K2Fixture


def _at_eight(days_ago: int = 0):
    """오늘 08:00 (현지). 크론이 부르는 그 시각으로 얼려 부른다."""
    now = timezone.localtime(timezone.now()) - timedelta(days=days_ago)
    return now.replace(hour=8, minute=0, second=0, microsecond=0)


class DigestClockTest(TestCase):
    """★ 「아직 안 왔다」와 「늦었다」를 가른다. 순수 판정 — DB 를 안 본다.

    둘을 뭉치면 매일 아침 유예 동안 장애 경보가 뜨고, 매일 뜨는 경보는 꺼진다(D-290).
    """

    def setUp(self) -> None:
        from kernels.k2_notify import digest_clock
        from kernels.k2_notify.heartbeat import DIGEST_GRACE, DIGEST_HOUR

        self.clock = digest_clock
        self.hour = DIGEST_HOUR
        self.grace = DIGEST_GRACE

    def test_before_the_grace_expires_nothing_is_late(self) -> None:
        now = datetime(2026, 9, 4, self.hour, 30)
        late, why = self.clock.is_late(None, now)
        self.assertFalse(late, why)

    def test_no_record_at_all_after_the_grace_is_an_outage(self) -> None:
        """★ 발송이 **한 건도 없는** 상태 — 이 절의 착수 전 실측이 정확히 이것이다."""
        now = datetime(2026, 9, 4, self.hour) + self.grace + timedelta(minutes=1)
        late, why = self.clock.is_late(None, now)
        self.assertTrue(late)
        self.assertIn("한 건도 없다", why)

    def test_yesterdays_digest_does_not_count_as_todays(self) -> None:
        """★ 어제 것으로 오늘을 덮으면 죽은 날을 못 잡는다."""
        now = datetime(2026, 9, 4, self.hour) + self.grace + timedelta(minutes=1)
        late, why = self.clock.is_late(datetime(2026, 9, 3, self.hour, 0), now)
        self.assertTrue(late)
        self.assertIn("장애다", why)

    def test_todays_digest_is_not_late(self) -> None:
        now = datetime(2026, 9, 4, self.hour) + self.grace + timedelta(minutes=1)
        late, _why = self.clock.is_late(datetime(2026, 9, 4, self.hour, 1), now)
        self.assertFalse(late)


class HeartbeatDigestTest(K2Fixture):
    """08:00 1통. **기록이 남는가 · 본문에 세 수가 있는가 · 남의 것이 안 섞이는가.**"""

    def _events_yesterday(self, stream, count: int):
        from kernels.k1_event import record_detection

        base = _at_eight() - timedelta(days=1)
        base = base.replace(hour=12)
        for i in range(count):
            record_detection(
                scope=self.scope_pipe, stream_monitor_id=stream.pk,
                event_type="fire", severity="critical",
                occurred_at=base + timedelta(minutes=17 * i))

    def _digest_rows(self):
        from common import audit_writer
        from kernels.k2_notify.heartbeat import DIGEST_ACTION, DIGEST_LOGGER

        return audit_writer.read(logger_name=DIGEST_LOGGER, action=DIGEST_ACTION)

    def test_eight_oclock_call_leaves_exactly_one_send_record(self) -> None:
        """★★ **이 절이 요구한 첫 증거 — 08:00 발송 기록 1건.**"""
        from kernels.k2_notify import send_heartbeat_digest

        self.assertEqual((), self._digest_rows(), "착수 전 발송 기록은 0건이다")

        result = send_heartbeat_digest(scope=self.scope_a, now=_at_eight())

        rows = self._digest_rows()
        self.assertEqual(1, len(rows),
                         f"08:00 발송 기록이 {len(rows)}건이다 — dead man's switch 는 "
                         f"1인가 0인가만 물어야 한다")
        self.assertEqual(rows[0].audit_id, result.audit_id)
        self.assertEqual(8, result.sent_at.hour)

    def test_one_row_per_send_not_per_recipient(self) -> None:
        """★ 사람 수만큼 남기면 「오늘 보냈는가」가 사람 수에 따라 다른 수가 된다."""
        from kernels.k2_notify import save_notification_rule, send_heartbeat_digest

        CoreUser = apps.get_model("user", "CoreUser")
        extra = CoreUser.objects.create_user(
            username="q_digest_second", password="test-only-not-a-secret",
            is_active=True, email="q_digest_second@test.invalid")
        link = CoreUser._meta.get_field("userprofilelink")
        link.related_model.objects.create(
            **{link.remote_field.name: extra, "group": self.group_a})
        extra.roles.add(self.role_a)
        save_notification_rule(scope=self.scope_a, severity="warning",
                               role_code=self.role_a.code, channels=["email"])

        result = send_heartbeat_digest(scope=self.scope_a, now=_at_eight())
        self.assertEqual(2, result.recipients)
        self.assertEqual(1, len(self._digest_rows()))

    def test_body_carries_the_three_numbers_and_the_rule(self) -> None:
        """★ 「정상 · 어제 이벤트 N · 카메라 맥박 N/N」 + **안 오면 장애다**."""
        from stream_monitors.services.camera_pulse import record_frame

        from kernels.k2_notify import send_heartbeat_digest
        from kernels.k2_notify.heartbeat import DEAD_MAN_RULE

        now = _at_eight()
        record_frame(scope=self.scope_pipe, stream_monitor_id=self.stream_a.pk, at=now)
        self._events_yesterday(self.stream_a, 3)

        result = send_heartbeat_digest(scope=self.scope_a, now=now)
        self.assertIn("GuardianX 정상", result.body)
        self.assertIn("이벤트 3건", result.body)
        self.assertIn("카메라 맥박 1/1", result.body)
        self.assertIn(DEAD_MAN_RULE, result.body,
                      "규약을 문서에만 적으면 규약이 바뀌는 날 문서만 옛말이 된다 (D-286)")
        self.assertEqual(3, result.events_yesterday)
        self.assertEqual((1, 1), (result.cameras_alive, result.cameras_total))

    def test_body_says_whether_the_audit_trail_is_being_written(self) -> None:
        """★ P-65 — 「정상」이라는 편지는 **그 정상을 증명할 기록이 쓰이고 있을 때만** 참이다.

        [실측 턴 E] celery 워커가 0개이던 사흘 동안 감사 쓰기 12,468건이 큐에 갇혀
        있었고, 그동안에도 이 편지는 「정상」이라고 나갈 수 있었다. 본문에 한 줄이
        있어야 받는 사람이 **증거가 밀리고 있다**는 것을 안다.
        """
        from kernels.k2_notify import send_heartbeat_digest

        result = send_heartbeat_digest(scope=self.scope_a, now=_at_eight())
        self.assertIn("감사 기록 대기", result.body,
                      "감사 큐가 밀리는 것을 본문이 말하지 않으면, 사흘이 지나도 "
                      "받는 사람은 「정상」만 읽는다 (P-65)")

    def test_the_audit_line_says_the_numbers_when_it_can_measure(self) -> None:
        """★ **양성과 음성을 함께** — 잴 수 있으면 수를 적고, 못 재면 「못 쟀다」다.

        브로커가 없는 시험 환경에서도 이 줄은 서야 한다. 그러나 **0건이라고 적으면
        안 된다** — 못 잰 것과 0은 다른 사실이다 (D-301).
        """
        from common.audit_queue import digest_line, judge_lag

        # 음성: 밀린 것이 0건이면 지연도 0이다
        self.assertEqual(0.0, judge_lag(0, 0.0, 99999)[0])
        # 양성: 턴 E 의 실측 수 — 밀렸고 아무것도 안 쓰였다 → 하한을 적는다
        self.assertEqual(259200.0, judge_lag(12468, 0.0, 259200)[0])
        # 회색: 브로커에 못 닿으면 None 이다. 0이 아니다
        self.assertIsNone(judge_lag(None, 1.0, 1)[0])

        line = digest_line({"backlog": 12468, "lag_seconds": 259200.0, "errors": {}})
        self.assertIn("12468", line)
        blind = digest_line({"backlog": None, "errors": {"backlog": "ConnectionError"}})
        self.assertIn("못 쟀다", blind)

    def test_it_actually_reaches_the_channel(self) -> None:
        """★ 「기록이 남았다」와 「나갔다」는 다른 사실이다 — 둘 다 잰다."""
        from django.core import mail

        from kernels.k2_notify import send_heartbeat_digest

        mail.outbox = []
        result = send_heartbeat_digest(scope=self.scope_a, now=_at_eight())
        self.assertEqual(1, result.delivered)
        self.assertEqual(0, result.failed)
        self.assertEqual(1, len(mail.outbox))
        self.assertIn("GuardianX", mail.outbox[0].subject)

    def test_another_tenants_numbers_do_not_ride_along(self) -> None:
        """★ 격리 — 본문에 실리는 것은 **그 테넌트의 관제 현황**이다.
        잘못 가면 그것은 안부 인사가 아니라 반출이다."""
        from kernels.k2_notify import send_heartbeat_digest

        self._events_yesterday(self.stream_b, 9)
        self._events_yesterday(self.stream_a, 2)

        result = send_heartbeat_digest(scope=self.scope_a, now=_at_eight())
        self.assertEqual(2, result.events_yesterday,
                         "남의 테넌트 어제 이벤트가 내 요약에 실렸다")
        self.assertNotIn(self.user_b.email, result.body)

    def test_zero_recipients_stops_instead_of_reporting_success(self) -> None:
        """★★ 부작위 — 아무에게도 안 가는 dead man's switch 는 **그 자체가 침묵**이다.

        조용히 성공으로 세면 「매일 보내고 있다」는 기록만 남고 아무도 안 받는다.
        """
        from kernels.k2_notify import send_heartbeat_digest
        from kernels.k2_notify.exceptions import NoRecipients

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        Rule._base_manager.all().delete()

        with self.assertRaises(NoRecipients):
            send_heartbeat_digest(scope=self.scope_a, now=_at_eight())
        self.assertEqual((), self._digest_rows(),
                         "못 보냈는데 발송 기록이 남았다 — 그 기록이 다음 날 "
                         "「왔다」로 읽힌다")

    def test_system_scope_without_a_group_is_refused(self) -> None:
        """★ group 없는 크론 호출은 **전 테넌트의 수를 한 통에** 싣는다 (D-281)."""
        from kernels.k2_notify import send_heartbeat_digest
        from kernels.k2_notify.exceptions import InvalidNotifyInput

        with self.assertRaises(InvalidNotifyInput):
            send_heartbeat_digest(scope=self.scope_pipe, now=_at_eight())

    def test_cron_call_with_a_group_works(self) -> None:
        """★ 양성 대조 — 거절만 재면 「전부 막힌 것」도 초록이다 (D-282 ④)."""
        from kernels.k2_notify import send_heartbeat_digest

        result = send_heartbeat_digest(scope=self.scope_pipe, now=_at_eight(),
                                       group=self.group_a)
        self.assertEqual(1, len(self._digest_rows()))
        self.assertGreaterEqual(result.recipients, 1)

    def test_a_person_cannot_point_group_at_another_tenant(self) -> None:
        """★★ **격리 — `group=` 은 테넌트를 고르는 손잡이가 아니다.**

        이 갈래가 없던 동안 A 테넌트 사용자가 `group=B` 로 **B 의 어제 이벤트 수와
        카메라 맥박**을 뽑아 A 의 수신자에게 메일로 보낼 수 있었다. 읽기 격리를 온전히
        지키고도 새는 자리이고, `WRITE_NO_PROBE` 의 이 함수 항목이 정확히 그것을
        경고하고 있었다 — 「남의 관제 현황 반출」.
        """
        from kernels.k2_notify import send_heartbeat_digest
        from kernels.k2_notify.exceptions import InvalidNotifyInput

        self._events_yesterday(self.stream_b, 9)
        with self.assertRaises(InvalidNotifyInput):
            send_heartbeat_digest(scope=self.scope_a, group=self.group_b,
                                  now=_at_eight())
        self.assertEqual((), self._digest_rows(),
                         "거절했다면서 발송 기록이 남았다 — 거절이 아니라 지연이다")

    def test_a_person_may_pass_their_own_group(self) -> None:
        """★ 양성 대조 — 거절만 재면 「전부 막힌 것」도 초록이다 (D-282 ④)."""
        from kernels.k2_notify import send_heartbeat_digest

        result = send_heartbeat_digest(scope=self.scope_a, group=self.group_a,
                                       now=_at_eight())
        self.assertGreaterEqual(result.recipients, 1)

    def test_unknown_channel_is_refused_with_a_reason(self) -> None:
        from kernels.k2_notify import send_heartbeat_digest
        from kernels.k2_notify.exceptions import InvalidNotifyInput

        with self.assertRaises(InvalidNotifyInput):
            send_heartbeat_digest(scope=self.scope_a, now=_at_eight(),
                                  channel="carrier-pigeon")

    def test_the_record_is_queryable_by_the_documented_names(self) -> None:
        """★ 매뉴얼이 인용하는 이름으로 실제로 찾아지는가 — 못 찾으면 규약이 빈말이다."""
        from kernels.k2_notify import (DIGEST_ACTION, DIGEST_HOUR, DIGEST_LOGGER,
                                       send_heartbeat_digest)

        self.assertEqual(8, DIGEST_HOUR)
        send_heartbeat_digest(scope=self.scope_a, now=_at_eight())

        from common import audit_writer

        rows = audit_writer.read(logger_name=DIGEST_LOGGER, action=DIGEST_ACTION)
        self.assertEqual(1, len(rows))
        self.assertIn("맥박", rows[0].reason)


class HeartbeatWatchTest(K2Fixture):
    """★ **안 온 것을 누가 아는가** — dead man's switch 의 나머지 절반 (조율자 · 2026-09-24).

    보내는 것만 있으면 이 절은 「보낸다」에서 끝난다. 「안 오면 장애다」의 값은
    **안 온 것을 알아채는 자리**에 있고, 그 답이 사람의 기억이면 장치가 아니다.

    ★ 이 시험 둘이 `scripts/verify_tenant_scope.py` 의 `KERNEL_PUBLIC` 등재를 뒷받침한다 —
      그 등재는 면제가 아니라 **선언**이고, 선언은 시험이 받쳐야 한다(D-261 c).
    """

    def test_a_person_cannot_run_the_watch(self) -> None:
        """★ 사람이 부르면 **전 테넌트의 「알림이 안 나가는 상태」**가 한 응답에 실린다.

        그것은 감시가 아니라 정찰이다. 좁힐 대상이 없으므로 문지기로 좁히지 않고
        **문 자체를 시스템에만 연다.**
        """
        from kernels.k2_notify import heartbeat_watch
        from kernels.k2_notify.exceptions import NotifyPermissionDenied

        with self.assertRaises(NotifyPermissionDenied):
            heartbeat_watch(scope=self.scope_a)

    def test_the_watch_reports_every_tenant_not_only_the_late_ones(self) -> None:
        """★ **늦지 않은 것도 돌려준다.**

        늦은 것만 내면 「한 번도 본 적이 없다」와 「봤는데 괜찮다」가 **같은 빈 목록**이
        된다(D-290). 그 둘이 같아지는 순간 이 감시는 꺼져 있어도 초록이다.
        """
        from datetime import timedelta

        from django.apps import apps

        from kernels.k2_notify import heartbeat_watch

        rows = heartbeat_watch(scope=self.scope_pipe, now=_at_eight())
        self.assertEqual(
            apps.get_model("user", "UserGroup").objects.count(), len(rows),
            "테넌트 수와 줄 수가 다르다 — 안 본 테넌트가 있으면 그 테넌트는 "
            "영원히 초록이다")
        for _gid, late, why in rows:
            self.assertTrue(why, "판정에 사유가 없다 — 늦지 않은 이유도 사유다")
            self.assertIsInstance(late, bool)

        # ★ 유예가 지나고 기록이 없으면 **늦었다**로 갈린다 (양성 대조 · D-277)
        late_rows = heartbeat_watch(
            scope=self.scope_pipe, now=_at_eight() + timedelta(hours=12))
        self.assertTrue(
            any(late for (_g, late, _w) in late_rows),
            "유예가 한참 지났는데 아무도 늦지 않았다 — 그러면 이 감시는 "
            "**언제나 초록**이고 아무것도 재지 않는다")
