# -*- coding: utf-8 -*-
"""차선 D — **재알림 N분**과 **현장 회신** (U3 · M3 · 모바일).

두 쓰기 면이 이번 턴에 열렸다. 둘 다 `tests/test_tenant_isolation.WRITE_NO_PROBE` 에
**선등재된 이름**이고(P-8), 면이 열렸으므로 그 줄은 probe 로 옮겨져야 한다.
그 파일은 공용 등록부라 차선이 고치지 않는다 — 그래서 **같은 시나리오를 여기서 먼저
세운다.** (E2 가 `save_notification_rule` 에서 한 것과 같은 방식이다.)

이 파일이 재는 것 — 초록보다 **빨강이 보이는가**
------------------------------------------------
  ② 시나리오  재알림 다섯 갈래(원발송 없음·이르다·이미 접수·범위 밖·보낸다)를 각각 지난다
  ③ 모수·술어 「보냈다」를 보고가 아니라 **발송 이력 행의 증가**로 읽는다
  ④ 탐지기    격리 음성(남의 것 → 거절 + **행이 안 늘어난다**) + 양성(제 것은 된다)
  ⑤ 환경      두 벌로 적은 상수가 갈리지 않았는가
"""
from __future__ import annotations

from datetime import timedelta

from django.apps import apps
from django.http import Http404
from django.utils import timezone

from tests.test_k2_notify_kernel import K2Fixture


def _delivery_count(event_id: int) -> int:
    Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
    return Delivery.objects.filter(event_id=event_id).count()


# ═══════════════════════════════════════════════════════════════════════════
# 1. 재알림 N분 — 다섯 갈래
# ═══════════════════════════════════════════════════════════════════════════
class RenotifyScenarioTest(K2Fixture):
    """다섯 갈래를 **각각** 지나간다. 하나로 뭉치면 어느 갈래가 죽었는지 안 보인다."""

    def test_no_original_delivery_is_not_a_renotify(self) -> None:
        """원 발송이 없으면 **재알림이 아니다** — 조용히 최초 발송을 하지 않는다."""
        from kernels.k2_notify import renotify

        event_id = self._event(self.stream_a)
        before = _delivery_count(event_id)

        result = renotify(scope=self.scope_a, event_id=event_id, after_minutes=10)

        self.assertFalse(result.sent)
        self.assertIn("원 발송이 없다", result.skipped_reason)
        # ★ 「없다」와 「0초」를 가른다 (D-290).
        self.assertIsNone(result.elapsed_seconds)
        self.assertEqual(before, _delivery_count(event_id),
                         "재알림이 아닌데 발송 행이 생겼습니다 — 최초 발송을 몰래 했습니다.")

    def test_too_early_does_not_send(self) -> None:
        """보낸 지 얼마 안 됐으면 안 보낸다. **사유가 값 안에 있다.**"""
        from kernels.k2_notify import renotify, send

        event_id = self._event(self.stream_a)
        sent = send(scope=self.scope_a, event_id=event_id)
        self.assertTrue(sent, "픽스처 전제가 깨졌습니다 — 최초 발송이 0행입니다.")
        before = _delivery_count(event_id)

        result = renotify(scope=self.scope_a, event_id=event_id, after_minutes=10)

        self.assertFalse(result.sent)
        self.assertIn("아직 이르다", result.skipped_reason)
        self.assertIsNotNone(result.elapsed_seconds)
        self.assertEqual(before, _delivery_count(event_id))

    def test_after_the_window_it_sends_again(self) -> None:
        """★ 이 파일의 양성 대조 — **창이 지나면 실제로 행이 는다.**

        시간은 `now=` 로 민다. 발송 이력 행을 손으로 고쳐 과거로 미는 것은
        `_base_manager` 직접 쓰기와 같은 일이고, 그러면 이 시험이 재는 것이
        「배선」이 아니라 「내가 심은 행」이 된다.
        """
        from kernels.k2_notify import renotify, send

        event_id = self._event(self.stream_a)
        first = send(scope=self.scope_a, event_id=event_id)
        before = _delivery_count(event_id)
        self.assertEqual(len(first), before)

        result = renotify(
            scope=self.scope_a, event_id=event_id, after_minutes=10,
            now=timezone.now() + timedelta(minutes=11))

        self.assertTrue(result.sent, f"보내지 않았습니다: {result.skipped_reason}")
        self.assertEqual("", result.skipped_reason)
        self.assertGreater(_delivery_count(event_id), before,
                           "「보냈다」고 했는데 발송 이력이 늘지 않았습니다 — 보고는 증거가 아닙니다.")
        self.assertEqual(len(result.deliveries), _delivery_count(event_id) - before)

    def test_five_minute_suppression_would_not_have_stopped_it(self) -> None:
        """★ [실측 2026-09-04] **5분 억제는 같은 이벤트의 재발송을 접지 않는다.**

        이 시험이 없으면 「억제가 접어 준다」는 잘못된 믿음 위에 재알림 문이 선다.
        `suppress` 가 여기서 **거짓**이라는 것이 `renotify` 가 자기 문턱을 따로
        재야 하는 이유의 전부다.
        """
        from kernels.k2_notify import send, suppress

        event_id = self._event(self.stream_a)
        send(scope=self.scope_a, event_id=event_id)

        self.assertFalse(
            suppress(scope=self.scope_a, event_id=event_id),
            "5분 억제가 같은 이벤트의 재발송을 접었습니다 — 그렇다면 renotify 의 "
            "문턱 설명이 틀린 것이므로 코드가 아니라 이 시험이 먼저 답을 냅니다.")

    def test_already_acknowledged_is_not_renotified(self) -> None:
        """이미 사람이 접수했으면 다시 울리지 않는다 — 재알림은 **무응답**을 깨운다."""
        from kernels.k1_event import advance_response
        from kernels.k2_notify import renotify, send

        event_id = self._event(self.stream_a)
        send(scope=self.scope_a, event_id=event_id)
        advance_response(event_id, to_state="acknowledged", scope=self.scope_a)
        before = _delivery_count(event_id)

        result = renotify(
            scope=self.scope_a, event_id=event_id, after_minutes=10,
            now=timezone.now() + timedelta(minutes=11))

        self.assertFalse(result.sent)
        self.assertIn("이미 손댔다", result.skipped_reason)
        self.assertEqual("acknowledged", result.response_state)
        self.assertEqual(before, _delivery_count(event_id))

    def test_out_of_range_window_is_refused_not_clamped(self) -> None:
        """범위 밖은 **거절**이다. 잘라 맞추면 「설정했는데 안 바뀌는」 자리가 된다."""
        from kernels.k2_notify import renotify
        from kernels.k2_notify.exceptions import InvalidNotifyInput

        event_id = self._event(self.stream_a)
        for bad in (0, -5, 60 * 25, "열분"):
            with self.subTest(after_minutes=bad):
                with self.assertRaises(InvalidNotifyInput):
                    renotify(scope=self.scope_a, event_id=event_id, after_minutes=bad)


class RenotifyIsolationTest(K2Fixture):
    """★ P-8 시나리오 — **남의 이벤트로 남의 수신자에게 알림을 일으킬 수 있는가.**

    읽기 격리가 온전해도 이 자리가 열려 있으면 격리가 아니다. 그 이벤트는 원래
    그쪽 테넌트의 것이라 **어떤 읽기 시험도 그것을 이상하다고 하지 않는다.**
    """

    def test_foreign_event_is_refused_and_nothing_changes(self) -> None:
        from kernels.k2_notify import renotify, send

        victim = self._event(self.stream_b)
        send(scope=self.scope_b, event_id=victim)      # 그쪽의 정상 발송
        before = _delivery_count(victim)

        with self.assertRaises(Http404):
            renotify(scope=self.scope_a, event_id=victim, after_minutes=10,
                     now=timezone.now() + timedelta(minutes=11))

        # ★ 거절만으로는 부족하다 — **행이 안 늘어난 것**까지 본다.
        self.assertEqual(before, _delivery_count(victim),
                         "거절했는데 남의 테넌트에 발송 행이 늘었습니다.")

    def test_own_event_is_allowed_positive_control(self) -> None:
        """양성 대조 — 문지기가 **전부 막는** 것으로 초록이 되지 않게 한다."""
        from kernels.k2_notify import renotify, send

        event_id = self._event(self.stream_a)
        send(scope=self.scope_a, event_id=event_id)
        result = renotify(scope=self.scope_a, event_id=event_id, after_minutes=10,
                          now=timezone.now() + timedelta(minutes=11))
        self.assertTrue(result.sent, f"제 이벤트인데 막혔습니다: {result.skipped_reason}")


class RenotifyConstantsTest(K2Fixture):
    """⑤ 환경 — **두 벌로 적은 값이 갈리지 않았는가** (D-337 계열)."""

    def test_untouched_state_matches_k1(self) -> None:
        from kernels.k1_event.response_flow import OCCURRED
        from kernels.k2_notify.renotify import _UNTOUCHED_RESPONSE_STATE

        self.assertEqual(
            OCCURRED, _UNTOUCHED_RESPONSE_STATE,
            "재알림이 「손대지 않음」이라 부르는 값과 K1 의 첫 칸이 갈렸습니다 — "
            "갈리면 재알림이 영원히 울리거나 영원히 안 울립니다.")

    def test_renotify_is_on_the_public_surface(self) -> None:
        """대장이 커널 `__all__` 을 훑는다 — 면에서 감추면 대장 밖에서 자란다(D-301)."""
        from kernels import k2_notify

        self.assertIn("renotify", k2_notify.__all__)


# ═══════════════════════════════════════════════════════════════════════════
# 2. 현장 회신 (M3 서버 면)
# ═══════════════════════════════════════════════════════════════════════════
class FieldReplyTest(K2Fixture):
    """U3 #9 「현장 상황 한 줄 보고」의 서버 면."""

    def test_a_reply_is_stored_and_read_back(self) -> None:
        from kernels.k1_event.field_reply import list_field_replies, reply_from_field

        event_id = self._event(self.stream_a)
        saved = reply_from_field(scope=self.scope_a, event_id=event_id,
                                 text="  도착. 실화재 아님 — 조리 연기.  ")

        self.assertEqual(event_id, saved.event_id)
        self.assertEqual("도착. 실화재 아님 — 조리 연기.", saved.text)   # 앞뒤 공백은 턴다
        self.assertEqual(self.user_a.pk, saved.author_id)

        rows = list_field_replies(scope=self.scope_a, event_id=event_id)
        self.assertEqual(1, len(rows))
        self.assertEqual(saved.reply_id, rows[0].reply_id)
        self.assertEqual(saved.text, rows[0].text)

    def test_replies_do_not_pollute_the_delivery_table(self) -> None:
        """★ 회신은 `DeliveryRecord` 를 만들지 않는다 — 그 표는 F-10 을 재는 자리다."""
        from kernels.k1_event.field_reply import reply_from_field

        event_id = self._event(self.stream_a)
        before = _delivery_count(event_id)
        reply_from_field(scope=self.scope_a, event_id=event_id, text="현장 도착")
        self.assertEqual(before, _delivery_count(event_id))

    def test_replies_do_not_pollute_the_response_audit(self) -> None:
        """★ 대응 전이 전건(`guardianx.dsm.response`)이 회신 수만큼 부풀지 않는다."""
        from kernels.k1_event.field_reply import reply_from_field
        from kernels.k1_event.response_flow import LOGGER_NAME as RESPONSE_LOGGER

        AuditLogs = apps.get_model("logger", "AuditLogs")
        before = AuditLogs.objects.filter(logger_name=RESPONSE_LOGGER).count()

        event_id = self._event(self.stream_a)
        reply_from_field(scope=self.scope_a, event_id=event_id, text="현장 도착")

        self.assertEqual(
            before, AuditLogs.objects.filter(logger_name=RESPONSE_LOGGER).count(),
            "현장 회신이 대응 전이 전건에 섞였습니다 — 「전이 N건」이 회신만큼 부풀어 오릅니다.")

    def test_empty_and_oversized_replies_are_refused(self) -> None:
        """빈 회신·상한 초과는 거절이다. **잘라 저장하지 않는다.**"""
        from kernels.k1_event.exceptions import InvalidEventInput
        from kernels.k1_event.field_reply import MAX_REPLY_CHARS, reply_from_field

        event_id = self._event(self.stream_a)
        for bad in ("", "   ", "가" * (MAX_REPLY_CHARS + 1)):
            with self.subTest(length=len(bad)):
                with self.assertRaises(InvalidEventInput):
                    reply_from_field(scope=self.scope_a, event_id=event_id, text=bad)

    def test_system_scope_cannot_reply(self) -> None:
        """**무계정 링크 금지의 집행** — 행위자 없는 회신은 회신이 아니다.

        ★ [실측 2026-09-04] 막는 것은 이 모듈의 ②가 아니라 **K1 의 읽기 문지기**다.
          `get_event` 가 `scope.require_actor()` 에서 `SystemScopeCannotRead` 를
          던지므로 회신 코드까지 오지 못한다. 시험을 코드에 맞춰 느슨하게 하지 않고
          **실제로 무엇이 막았는지**를 적는다 — 이 자리가 나중에 열리면 이 시험이
          멈추고, 그때 볼 것은 문지기다.
        """
        from common.tenant_scope import SystemScopeCannotRead
        from kernels.k1_event.field_reply import reply_from_field

        event_id = self._event(self.stream_a)
        with self.assertRaises(SystemScopeCannotRead):
            reply_from_field(scope=self.scope_pipe, event_id=event_id, text="자동 회신")


class FieldReplyIsolationTest(K2Fixture):
    """★ P-8 시나리오 — **남의 이벤트에 내 글을 남길 수 있는가.**

    남으면 남의 관제 기록에 우리 문장이 섞이고, 그 기록은 대외 보고의 근거가 된다.
    읽기 격리가 온전해도 이것은 격리가 아니다.
    """

    def _reply_count(self, event_id: int) -> int:
        from kernels.k1_event.field_reply import ACTION, LOGGER_NAME, _payload_of

        AuditLogs = apps.get_model("logger", "AuditLogs")
        rows = AuditLogs.objects.filter(logger_name=LOGGER_NAME, api_name=ACTION)
        return sum(1 for r in rows if _payload_of(r).get("event_id") == event_id)

    def test_writing_to_a_foreign_event_is_refused_and_nothing_is_written(self) -> None:
        from kernels.k1_event.field_reply import reply_from_field

        victim = self._event(self.stream_b)
        before = self._reply_count(victim)

        with self.assertRaises(Http404):
            reply_from_field(scope=self.scope_a, event_id=victim, text="남의 사건에 남기기")

        self.assertEqual(before, self._reply_count(victim),
                         "거절했는데 남의 이벤트에 회신 행이 남았습니다.")

    def test_reading_a_foreign_events_replies_is_refused(self) -> None:
        """★ 순서가 뜻이다 — 문지기가 **번호로 뽑기 전에** 선다."""
        from kernels.k1_event.field_reply import list_field_replies, reply_from_field

        victim = self._event(self.stream_b)
        reply_from_field(scope=self.scope_b, event_id=victim, text="그쪽 현장 회신")

        with self.assertRaises(Http404):
            list_field_replies(scope=self.scope_a, event_id=victim)

    def test_own_event_is_allowed_positive_control(self) -> None:
        """양성 대조 — 전부 막아서 초록이 되는 것을 막는다."""
        from kernels.k1_event.field_reply import list_field_replies, reply_from_field

        event_id = self._event(self.stream_a)
        reply_from_field(scope=self.scope_a, event_id=event_id, text="우리 현장 회신")
        self.assertEqual(1, len(list_field_replies(scope=self.scope_a, event_id=event_id)))

    def test_replies_of_one_event_do_not_leak_into_another(self) -> None:
        """같은 테넌트 안에서도 **사건이 섞이지 않는다.**"""
        from kernels.k1_event.field_reply import list_field_replies, reply_from_field

        first = self._event(self.stream_a)
        second = self._event(self.stream_a)
        reply_from_field(scope=self.scope_a, event_id=first, text="첫 사건")
        reply_from_field(scope=self.scope_a, event_id=second, text="둘째 사건")

        self.assertEqual(["첫 사건"],
                         [r.text for r in list_field_replies(scope=self.scope_a, event_id=first)])
        self.assertEqual(["둘째 사건"],
                         [r.text for r in list_field_replies(scope=self.scope_a, event_id=second)])
