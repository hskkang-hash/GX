# -*- coding: utf-8 -*-
"""훈련 모드 — **끄는 스위치를 남이 켤 수 있는가** (UX-17 · 차선 C · 2026-09-24).

이 파일이 묻는 것
-----------------
① **격리.** 남의 테넌트를 훈련 모드로 바꿀 수 있으면 그쪽 **진짜 경보**가 로그로 흘러
   아무에게도 안 간다. 켜는 스위치가 아니라 **끄는** 스위치라, 이 면은 다른 어떤
   쓰기보다 조용하게 사고를 만든다. `WRITE_PROBES` 가 선등재해 둔 자리다.
② **사유 없는 전환을 거절하는가.** 사후에 「그 시각에 왜 안 갔나」를 묻는 사람이
   반드시 생기고, 그때 답이 없으면 그 미발송은 **장애와 구별되지 않는다.**
③ **창이 남는가.** 「지금 켜져 있나」만이 아니라 **언제부터 · 누가 · 왜**가 남아야
   훈련 종료 보고서를 쓸 수 있다.
④ **보고서가 분모와 함께 0 을 말하는가** (D-301). 분모 없는 0 은 「발송 자체가
   없었다」와 구별되지 않고, 그러면 스위치가 안 걸린 채 아무 일도 없던 밤이
   「훈련 성공」이 된다.

★ 이 파일이 묻지 **않는** 것 — **채널이 실제로 바뀌는가.**
  실채널 우회는 `kernels/k2_notify/` 안에서 일어나야 하고(발송 경로는 하나다),
  그 파일은 조율자의 것이다. 이 차선은 스위치까지 세우고 멈췄다.
  ★ 2026-09-24 — **배선이 왔다.** 조율자가 `kernels/k2_notify/services._send_one` 에
    한 자리를 이었고, 그 순간 부작위 시험이 빨개졌다. 갈아 끼운 것이
    `DrillIsWiredToChannelsTest` 다 — 「훈련 중에는 채널이 log 로 간다」와 그 양성 대조.
"""
from __future__ import annotations

from tests.test_dsm_app import DsmFixture

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "stream_monitors.services.drill(set_drill_mode · drill_state · is_drill_mode · "
    "is_drill_event · drill_report) · apps.dsm.services · logger.AuditLogs · "
    "kernels.k2_notify.channels — 저장소의 실제 모듈. 합성 더미를 부르지 않는다"
)


class DrillSwitchIsolationTest(DsmFixture):
    """① ★ **남의 테넌트를 훈련 모드로 바꿀 수 있는가.** 있으면 격리 실패다."""

    def test_a_tenant_cannot_switch_another_tenants_drill_mode(self) -> None:
        from django.core.exceptions import PermissionDenied

        from stream_monitors.services import drill

        with self.assertRaises(PermissionDenied):
            drill.set_drill_mode(scope=self.scope_a, enabled=True,
                                 reason="시험 — 남의 테넌트를 끄려 한다",
                                 group_id=self.group_b.pk)

        #: ★ 거절만으로는 부족하다 — **행이 안 바뀌었는지**까지 본다.
        #:   거절 뒤에 조용히 켜져 있으면 그것이 정확히 D-284 의 조용한 성공이다.
        self.assertFalse(drill.is_drill_mode(group_id=self.group_b.pk),
                         "거절했는데 남의 테넌트가 훈련 모드로 켜졌습니다.")

    def test_a_tenant_cannot_read_another_tenants_drill_state(self) -> None:
        """훈련 중인지도 **남의 정보다.** 「지금 알림이 안 나가는 테넌트」를 아는 것은
        공격자에게 값있는 사실이다."""
        from django.core.exceptions import PermissionDenied

        from stream_monitors.services import drill

        with self.assertRaises(PermissionDenied):
            drill.drill_state(scope=self.scope_a, group_id=self.group_b.pk)

    def test_a_system_scope_cannot_flip_the_switch(self) -> None:
        """사람이 없는 호출이 켤 수 있으면 「누가 켰나」가 영원히 빈다 (D-281)."""
        from stream_monitors.services import drill

        with self.assertRaises(Exception) as caught:
            drill.set_drill_mode(scope=self.scope_pipe, enabled=True,
                                 reason="시험 — 요청자 없는 호출")
        self.assertNotIsInstance(caught.exception, AssertionError)

    def test_the_owner_can_switch_their_own_tenant(self) -> None:
        """★ 양성도 함께 본다 — 전부 거절하는 문지기는 문지기가 아니다."""
        from stream_monitors.services import drill

        result = drill.set_drill_mode(scope=self.scope_a, enabled=True,
                                      reason="시험 — 제 테넌트 훈련 시작")
        self.assertTrue(result["drill_mode"])
        self.assertTrue(result["changed"])
        self.assertTrue(drill.is_drill_mode(group_id=self.group_a.pk))
        #: 그리고 **남의 테넌트는 그대로다.**
        self.assertFalse(drill.is_drill_mode(group_id=self.group_b.pk))


class DrillNeedsAReasonTest(DsmFixture):
    """② 사유 없는 전환은 **거절된다.**"""

    def test_a_blank_reason_is_refused(self) -> None:
        from stream_monitors.services import drill

        for blank in ("", "   ", "\n"):
            with self.assertRaises(ValueError):
                drill.set_drill_mode(scope=self.scope_a, enabled=True, reason=blank)
        self.assertFalse(drill.is_drill_mode(group_id=self.group_a.pk),
                         "사유 없이 거절했는데 스위치가 켜졌습니다.")

    def test_flipping_twice_records_once(self) -> None:
        """같은 사실을 두 줄로 적으면 「언제부터 훈련인가」가 밀려 창이 짧아진다."""
        from stream_monitors.services import drill

        first = drill.set_drill_mode(scope=self.scope_a, enabled=True, reason="첫 켜기")
        again = drill.set_drill_mode(scope=self.scope_a, enabled=True, reason="또 켜기")
        self.assertTrue(first["changed"])
        self.assertFalse(again["changed"], "같은 상태를 두 번 적었습니다.")
        self.assertEqual(first["since"], again["since"], "훈련 시작 시각이 밀렸습니다.")


class DrillWindowTest(DsmFixture):
    """③ 「지금」만이 아니라 **창**이 남는가."""

    def test_the_state_carries_who_when_and_why(self) -> None:
        from stream_monitors.services import drill

        drill.set_drill_mode(scope=self.scope_a, enabled=True,
                             reason="야간 대응 훈련 — 2026-09-24 22:00")
        state = drill.drill_state(scope=self.scope_a)

        self.assertTrue(state.enabled)
        self.assertIsNotNone(state.since, "언제부터인지 없으면 창이 아닙니다.")
        self.assertEqual(self.user_a.username, state.by)
        self.assertIn("야간 대응 훈련", state.reason)

    def test_never_switched_is_not_the_same_as_switched_off(self) -> None:
        """「켠 적이 없다」와 「껐다」는 다른 사실이다 (D-290)."""
        from stream_monitors.services import drill

        virgin = drill.drill_state(scope=self.scope_a)
        self.assertFalse(virgin.enabled)
        self.assertEqual("", virgin.last_action,
                         "켠 적이 없는 테넌트가 「껐다」와 같은 모양입니다.")

        drill.set_drill_mode(scope=self.scope_a, enabled=True, reason="켠다")
        drill.set_drill_mode(scope=self.scope_a, enabled=False, reason="끈다")
        turned_off = drill.drill_state(scope=self.scope_a)
        self.assertFalse(turned_off.enabled)
        self.assertEqual(drill.OFF, turned_off.last_action)

    def test_an_event_inside_the_window_is_a_drill_event(self) -> None:
        """`data_source=drill` 의 판정 — **창이 표시다.**

        칸을 새로 만들지 않은 이유: 새 칸은 태어나는 순간 과거가 비어 있고,
        빈 과거는 「전부 실사건이었다」로 읽힌다. 창은 감사에 있고 과거도 함께 온다.
        """
        from django.utils import timezone

        from stream_monitors.services import drill

        before = timezone.now()
        drill.set_drill_mode(scope=self.scope_a, enabled=True, reason="훈련 시작")
        during = timezone.now()

        self.assertFalse(
            drill.is_drill_event(occurred_at=before, group_id=self.group_a.pk),
            "훈련 시작 **전**의 이벤트가 훈련으로 표시됐습니다 — 실사건이 훈련으로 "
            "적히면 그 사건은 보고서에서 사라집니다.")
        self.assertTrue(
            drill.is_drill_event(occurred_at=during, group_id=self.group_a.pk))
        #: 남의 테넌트 이벤트는 우리 창에 안 들어온다.
        self.assertFalse(
            drill.is_drill_event(occurred_at=during, group_id=self.group_b.pk))

    def test_unknown_tenant_defaults_to_live_not_drill(self) -> None:
        """★ **안전한 기본값은 실발송이다.** 「모르니까 훈련일 수도」로 참을 내면
        테넌트를 못 읽은 순간 진짜 경보가 통째로 로그로 간다."""
        from stream_monitors.services import drill

        self.assertFalse(drill.is_drill_mode(group_id=None))


class DrillReportTest(DsmFixture):
    """④ 보고서 1장 — **0 을 분모와 함께** 말하는가."""

    def test_a_tenant_that_never_drilled_says_so(self) -> None:
        from stream_monitors.services import drill

        report = drill.drill_report(scope=self.scope_a)
        self.assertFalse(report["measurable"])
        self.assertIn("한 번도", report["reason"])

    def test_the_report_carries_the_real_channel_count_and_its_denominator(self) -> None:
        """★ **첫 증거는 「실채널 발송 0」이다** — 그리고 분모가 함께 나온다.

        분모 없는 0 은 「발송 자체가 없었다」와 구별되지 않는다. 그러면 스위치가
        안 걸린 채 아무 일도 없던 밤이 「훈련 성공」이 된다.
        """
        from stream_monitors.services import drill

        drill.set_drill_mode(scope=self.scope_a, enabled=True, reason="훈련 시작")
        self._event(self.stream_a)
        report = drill.drill_report(scope=self.scope_a)

        self.assertTrue(report["measurable"])
        self.assertTrue(report["in_progress"])
        for key in ("real_channel_sends", "sends_total", "events_total",
                    "sends_by_channel", "events_by_type"):
            self.assertIn(key, report, f"{key} 가 보고서에 없습니다 — 분모 없는 0 은 "
                                       f"아무것도 증명하지 않습니다(D-301).")
        self.assertEqual(0, report["real_channel_sends"])

    def test_the_report_does_not_leak_across_tenants(self) -> None:
        from django.core.exceptions import PermissionDenied

        from stream_monitors.services import drill

        drill.set_drill_mode(scope=self.scope_b, enabled=True, reason="B 의 훈련")
        with self.assertRaises(PermissionDenied):
            drill.drill_report(scope=self.scope_a, group_id=self.group_b.pk)


class DrillIsWiredToChannelsTest(DsmFixture):
    """★ **배선이 왔다** (2026-09-24 · 조율자가 K2 에 이었다).

    직전까지 이 자리에는 부작위 시험 하나가 서 있었다 —
    `test_the_notify_path_does_not_consult_the_drill_switch_yet`.
    차선 C 는 스위치·창·보고서까지 세우고 **채널 앞에서 멈췄고**(발송 경로는 하나이고
    그 파일은 조율자의 것이다), 없는 것을 없다고 적어 두었다.

    ⚠ **그 시험은 배선이 들어오는 순간 빨개지게 되어 있었고, 실제로 그랬다.**
      지우고 이 시험으로 갈아 끼우는 일이 곧 「배선이 왔다」는 선언이다 —
      부작위 시험을 조용히 지우면 이 저장소는 배선 없이 「훈련 모드가 있다」고 말한다.
    """

    def test_while_drilling_the_channel_becomes_log(self) -> None:
        """★ 훈련 중에는 **사람에게 안 간다.** 그리고 그 사실이 행에 남는다.

        ⚠ 채널 이름을 **가장하지 않는다**: 행의 `channel` 이 `log` 여야 종료 보고서가
          「사람이 아니라 로그로 갔다」를 말할 수 있다. 원래 이름을 적어 두고 몰래
          로그로 보내면 그 행은 **보냈다는 거짓말**이다(D-284).
        """
        from kernels.k2_notify import Recipient, send
        from stream_monitors.services import drill

        drill.set_drill_mode(scope=self.scope_a, enabled=True,
                             reason="시험 — 훈련 중 발송 채널을 본다")
        event_id = self._event(self.stream_a)
        views = send(
            scope=self.scope_a, event_id=event_id,
            recipients=(Recipient(user_id=self.user_a.pk, display_name="drill-probe",
                                  address="drill-probe@invalid", channel="email",
                                  rule_id=0),))
        self.assertEqual(1, len(views))
        self.assertEqual(
            drill.DRILL_CHANNEL, views[0].channel,
            "훈련 중인데 발송이 실채널로 갔습니다 — 그날로 알림이 꺼집니다.")

    def test_outside_a_drill_the_channel_is_untouched(self) -> None:
        """★ 양성 대조 — 거절만 재면 「전부 로그로 간다」도 초록이다 (D-277).

        ⚠ 안전한 기본값은 **실발송**이다. 스위치를 못 읽는 상태에서 조용해지는 것이
          이 절이 막으려는 사고 그 자체다.
        """
        from kernels.k2_notify import Recipient, send

        event_id = self._event(self.stream_a)
        views = send(
            scope=self.scope_a, event_id=event_id,
            recipients=(Recipient(user_id=self.user_a.pk, display_name="drill-probe",
                                  address="drill-probe@invalid", channel="email",
                                  rule_id=0),))
        self.assertEqual("email", views[0].channel,
                         "훈련 중이 아닌데 채널이 바뀌었습니다.")

    def test_the_log_channel_the_switch_points_at_actually_exists(self) -> None:
        """가리키는 채널이 **실재하는지**는 지금 잴 수 있다 — 없는 이름을 가리키면
        배선이 오는 날 조용히 아무 데도 안 간다."""
        from kernels.k2_notify import channels
        from stream_monitors.services import drill

        self.assertIsNotNone(
            channels.get(drill.DRILL_CHANNEL),
            f"훈련 채널 {drill.DRILL_CHANNEL!r} 이 K2 레지스트리에 없습니다.")
        self.assertIn(
            drill.DRILL_CHANNEL, channels.NON_HUMAN,
            "훈련 채널이 **사람에게 도달하는** 채널입니다 — 훈련 중에 진짜 알림이 "
            "나갑니다.")
