# -*- coding: utf-8 -*-
"""F-04 **억제 키 — 계약의 정본 한 곳** (2026-09-21 · 턴 Z · 차선 U1 · 세종).

계약 한 줄
----------
    억제 키는 `event_id` 가 **아니라** **「같은 스트림 + 같은 유형 + 직전 발송 시각」**이다.

이유: **억제는 사람에게 「같은 일이 또 왔다」를 막는 것이지 사건 번호를 막는 것이
아니다.** 사건 번호로 억제하면 같은 카메라에서 같은 일이 10번 나도 10번 다 울린다 —
번호가 매번 다르기 때문이다. 받는 사람에게 그것은 **한 가지 일**이다.

문안 — **GX-COPY 사전 그대로** (낱말을 새로 짓지 않는다)
-------------------------------------------------------
    짧은 말   「5분 안에 같은 사건 재발송 억제」
    화면의 말 「새로 보낸 알림이 없습니다. 같은 사건의 알림은 5분 안에 다시 보내지
               않습니다. 아래 발송 이력을 확인하십시오.」
               (GX-COPY_v1 §2026-09-15 턴 Q · 발송 응답 `total` 이 0 일 때)

⚠ 사전의 **「같은 사건」은 「같은 사건 번호」가 아니라 「같은 카메라에서 같은 종류의
  일」**이다. 그 뜻을 여기서 못박는다 — 뜻이 글자 밖에 있으면 다음 사람이 번호로 읽는다.

왜 이 파일이 생겼나 — **흩어진 시험 넷**
----------------------------------------
같은 계약을 네 시험이 **조각으로** 들고 있었다. 조각은 각자 옳았지만, 어느 것이
계약인지는 아무 데도 없었다:

    backend/tests/test_k2_notify_kernel.py::SuppressionTest
        옆 사건이 접힌다 · 같은 사건을 두 번 눌러도 접힌다 · 5분 밖은 안 접힌다 ·
        실패한 발송은 억제 근거가 아니다
    backend/tests/test_u56_notify_repeat_count.py
        같은 스트림·같은 종류·5분 안 → `total=0`(행이 안 는다) · **다른 종류는 안 접힌다**
    backend/tests/test_s_webhook_outbox.py
        접힌 알림은 **웹훅도 안 나간다**(억제는 채널의 규칙이 아니라 알림의 규칙)
    backend/tests/test_d_mobile_field.py
        **재알림은 이 판정을 안 본다**(`respect_suppression=False` · 문턱이 다르다)

넷은 **그대로 남는다** — 각자 제 갈래(웹훅 팬아웃 · API 응답 수 · 재알림)를 계속 잰다.
바뀐 것은 하나다: **키의 정본은 이 파일이고**, 커널의 키는
`kernels/k2_notify/services.py::_suppression_key` **한 곳**에 있다.

이 파일이 재는 것 — 네 갈래 + 이 저장소에 없던 대조 둘
-------------------------------------------------------
    ① 키에 `event_id` 가 **없다**       — 옆 사건도 접힌다 · 자기 사건도 접힌다
    ② 유형이 다르면 **안 접힌다**       (양성 대조)
    ③ **스트림이 다르면 안 접힌다**     ← 없던 대조. 키의 첫 칸을 아무도 안 재고 있었다
    ④ 시계는 **`sent_at`**             — 사건 발생 시각이 아무리 옛날이어도 방금 보냈으면
                                          접히고, 보낸 지 5분이 지나면 안 접힌다
    ⑤ **실패한 발송**은 억제 근거가 아니다
    ⑥ **훈련(`drill:`) 발송**은 억제 근거가 아니다 — 시험 한 통이 다음 진짜 경보를
      삼키지 않는다
    ⑦ **키가 한 곳인가** ← 없던 대조. `suppress` 본문이 키를 손으로 다시 적으면 빨강
"""
from __future__ import annotations

import inspect
from datetime import timedelta

from django.apps import apps
from django.utils import timezone

from tests.test_k2_notify_kernel import K2Fixture


def _deliveries():
    return apps.get_model("stream_monitors", "DeliveryRecord")._base_manager


class F04SuppressionKeyContractTest(K2Fixture):
    """**억제 키의 정본.** 이 클래스가 깨지면 고칠 것은 시험이 아니라 계약 문서다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        super().setUpTestData()
        #: 같은 테넌트의 **둘째 카메라**. 키의 첫 칸(스트림)을 재려면 같은 테넌트 안에
        #: 카메라가 둘이어야 한다 — 다른 테넌트의 카메라로 재면 문지기가 먼저 걸려
        #: 「스코프가 막았다」와 「키가 갈랐다」가 한 답이 된다.
        cls.stream_a2 = cls._make_stream("k2-stream-A2", cls.group_a)

    # ── ① 키에 `event_id` 가 없다 ────────────────────────────────────────
    def test_the_key_has_no_event_id_so_a_neighbour_event_is_also_folded(self) -> None:
        """**같은 카메라에서 같은 일이 또 났다** — 번호는 다르지만 접힌다.

        이것이 계약의 전부다. 번호로 억제하면 이 시험이 빨강이 되고, 그 빨강이
        「같은 카메라에서 같은 일이 10번 나면 10번 다 울린다」의 시험 판이다.
        """
        from kernels.k2_notify import send, suppress

        now = timezone.now()
        first = self._event(self.stream_a, when=now - timedelta(minutes=2))
        send(scope=self.scope_a, event_id=first)

        second = self._event(self.stream_a, when=now)
        self.assertNotEqual(first, second, "표본 고장 — 두 사건이 같은 행입니다.")
        self.assertTrue(
            suppress(scope=self.scope_a, event_id=second),
            "번호가 다른 옆 사건이 안 접혔습니다 — 억제 키가 `event_id` 로 좁혀졌다는 "
            "뜻이고, 그러면 같은 카메라의 같은 일이 날 때마다 매번 울립니다 (F-04).")

    def test_the_same_event_pressed_twice_is_folded_too(self) -> None:
        """**자기 자신도 접힌다** — 키에 번호가 없다는 것의 나머지 절반.

        ★ 턴 Y 가 고친 자리다. 종전 질의는 `occurred_at__lt = event.occurred_at` 로
          **자기 발송만 잘라 내서** 옆 사건은 접으면서 자기 자신은 못 접었다
          — 문안과 정반대였다. 두 시험이 **함께** 서야 「번호를 안 본다」가 참이 된다.
        """
        from kernels.k2_notify import send, suppress

        event_id = self._event(self.stream_a, when=timezone.now())
        sent = send(scope=self.scope_a, event_id=event_id)
        self.assertTrue(sent and sent[0].succeeded, "첫 발송이 실패했습니다(표본 고장).")

        self.assertTrue(suppress(scope=self.scope_a, event_id=event_id),
                        "방금 보낸 사건을 다시 눌렀는데 안 접힙니다 (GX-COPY 문안).")
        self.assertEqual((), send(scope=self.scope_a, event_id=event_id),
                         "억제됐는데 발송 이력이 다시 생겼습니다 — 화면은 200 을 받고 "
                         "사람은 아무것도 모릅니다.")

    # ── ② 유형이 다르면 안 접힌다 (양성 대조) ────────────────────────────
    def test_a_different_event_type_is_not_folded(self) -> None:
        """억제는 「발송이 죽었다」가 아니라 「**같은** 경보를 두 번 안 보낸다」이다."""
        from kernels.k2_notify import send, suppress

        now = timezone.now()
        fire = self._event(self.stream_a, when=now - timedelta(minutes=1),
                           event_type="fire")
        send(scope=self.scope_a, event_id=fire)

        flood = self._event(self.stream_a, when=now, event_type="flood")
        self.assertFalse(
            suppress(scope=self.scope_a, event_id=flood),
            "같은 카메라의 **다른 종류**까지 접었습니다 — 불을 알린 뒤 5분 안에 물이 "
            "차면 아무도 못 듣습니다.")

    # ── ③ 스트림이 다르면 안 접힌다 (없던 대조) ──────────────────────────
    def test_a_different_stream_is_not_folded(self) -> None:
        """★ **키의 첫 칸.** 이 저장소의 어느 시험도 이것을 안 재고 있었다.

        카메라가 다르면 **다른 현장**이다. 옆 현장의 불을 이쪽 카메라가 이미 알렸다는
        이유로 접으면, 그 구역은 알림 없이 탄다.
        """
        from kernels.k2_notify import send, suppress

        now = timezone.now()
        first = self._event(self.stream_a, when=now - timedelta(minutes=1))
        send(scope=self.scope_a, event_id=first)

        other_camera = self._event(self.stream_a2, when=now)
        self.assertFalse(
            suppress(scope=self.scope_a, event_id=other_camera),
            "**다른 카메라**의 같은 종류까지 접었습니다 — 억제 키의 첫 칸(스트림)이 "
            "빠졌다는 뜻입니다.")

    # ── ④ 시계는 `sent_at` 이다 ──────────────────────────────────────────
    def test_the_clock_is_the_last_sent_at_not_the_event_time(self) -> None:
        """**16일 지난 사건을 눌러도 방금 보냈으면 접힌다** — 기준은 보낸 시각이다."""
        from kernels.k2_notify import send, suppress

        old = timezone.now() - timedelta(days=16)
        event_id = self._event(self.stream_a, when=old)
        sent = send(scope=self.scope_a, event_id=event_id)
        self.assertTrue(sent and sent[0].succeeded, "첫 발송이 실패했습니다(표본 고장).")

        self.assertTrue(
            suppress(scope=self.scope_a, event_id=event_id),
            "발생 시각이 옛날이라고 억제가 풀렸습니다 — 기준이 `occurred_at` 으로 "
            "돌아갔다는 뜻입니다.")

    def test_beyond_the_window_since_the_last_send_is_not_folded(self) -> None:
        """양성 대조 — 억제기가 **모든 것을 접지는 않는다.**

        시계를 기다리지 않는다. 기다리는 시험은 느린 것이 아니라 **재현되지 않는다.**
        """
        from kernels.k2_notify import send, suppress
        from kernels.k2_notify.schemas import SUPPRESS_WINDOW

        now = timezone.now()
        first = self._event(self.stream_a, when=now - timedelta(minutes=1))
        send(scope=self.scope_a, event_id=first)
        _deliveries().filter(event_id=first, succeeded=True).update(
            sent_at=now - SUPPRESS_WINDOW - timedelta(minutes=1))

        second = self._event(self.stream_a, when=now)
        self.assertFalse(
            suppress(scope=self.scope_a, event_id=second),
            f"직전 발송이 창({SUPPRESS_WINDOW}) 밖인데 접었습니다 — 억제기가 과합니다.")

    # ── ⑤ 실패한 발송은 억제 근거가 아니다 ──────────────────────────────
    def test_a_failed_delivery_is_not_a_ground_for_suppression(self) -> None:
        """**못 보낸 알림은 「이미 알렸다」가 아니다.**

        여기가 K1 의 판정과 갈리는 자리다 — 실패를 억제로 세면 장애 5분 동안의 재난
        알림이 통째로 사라지고, 그 5분이 정확히 알림이 가장 필요한 5분이다.
        """
        from kernels.k2_notify import send, suppress

        now = timezone.now()
        first = self._event(self.stream_a, when=now - timedelta(minutes=1))
        send(scope=self.scope_a, event_id=first)
        #: 성공한 행을 **실패로 되돌린다** — 어댑터를 부수는 것과 같은 사실을
        #: 행에 직접 적는다(이 파일이 재는 것은 어댑터가 아니라 **키**다).
        _deliveries().filter(event_id=first).update(
            succeeded=False, sent_at=None, failure_reason="시험: 메일 서버가 죽었다")

        second = self._event(self.stream_a, when=now)
        self.assertFalse(
            suppress(scope=self.scope_a, event_id=second),
            "실패한 발송이 억제로 세어졌습니다 — 장애 구간의 알림이 사라집니다.")

    # ── ⑥ 훈련 발송은 억제 근거가 아니다 ────────────────────────────────
    def test_a_drill_send_is_not_a_ground_for_suppression(self) -> None:
        """**시험 한 통이 다음 진짜 경보를 삼키지 않는다** (턴 T · U3 · `webpush.py` ②).

        훈련 표식은 행의 `recipient_address` 머리(`drill:`)에 있다.
        """
        from kernels.k2_notify import send, suppress
        from kernels.k2_notify import webpush as webpush_gate

        now = timezone.now()
        first = self._event(self.stream_a, when=now - timedelta(minutes=1))
        send(scope=self.scope_a, event_id=first)
        _deliveries().filter(event_id=first, succeeded=True).update(
            recipient_address=f"{webpush_gate.DRILL_ADDRESS_PREFIX}webpush:abc123def456")

        second = self._event(self.stream_a, when=now)
        self.assertFalse(
            suppress(scope=self.scope_a, event_id=second),
            "훈련(시험) 발송이 억제 근거가 됐습니다 — 「내 기기로 한 통」을 누른 사람이 "
            "5분 동안 진짜 경보를 못 받습니다.")

    # ── ⑦ 키가 한 곳인가 ────────────────────────────────────────────────
    def test_the_key_lives_in_exactly_one_place(self) -> None:
        """★ **구조 시험** — 키를 질의에 손으로 다시 적으면 빨강.

        키가 두 벌이 되는 것은 값이 틀리는 것보다 나쁘다: 한쪽만 고쳐진 채로 조용히
        살고, 조용한 쪽이 이긴다(`common/probe_marker.py` 가 존재하는 이유와 같다).
        """
        from kernels.k2_notify import services

        key_src = inspect.getsource(services._suppression_key)
        suppress_src = inspect.getsource(services.suppress)

        for field in ("event__stream_monitor_id", "event__event_type"):
            self.assertIn(field, key_src,
                          f"`_suppression_key` 가 {field} 를 안 듭니다 — 키가 여기 없습니다.")
            #: `suppress` 본문에서는 **주석 밖**에 이 글자가 없어야 한다.
            code_lines = [ln for ln in suppress_src.splitlines()
                          if not ln.lstrip().startswith("#")]
            self.assertNotIn(
                field, "\n".join(code_lines),
                f"`suppress` 가 {field} 를 손으로 다시 적었습니다 — 키가 두 벌입니다. "
                f"`_suppression_key()` 를 펼쳐 쓰십시오.")

    def test_the_key_dict_never_carries_the_event_number(self) -> None:
        """키가 내는 것에 **번호가 없다** — 계약을 값으로 확인한다."""
        from kernels.k2_notify import services

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        event_id = self._event(self.stream_a, when=timezone.now())
        event = Event._base_manager.get(pk=event_id)

        key = services._suppression_key(event)
        self.assertEqual(
            {"event__stream_monitor_id", "event__event_type"}, set(key),
            "억제 키의 칸이 계약과 다릅니다 — 계약은 「같은 스트림 + 같은 유형 + "
            "직전 발송 시각」이고, 시각은 창으로 걸립니다.")
        self.assertEqual(event.stream_monitor_id, key["event__stream_monitor_id"])
        self.assertEqual(event.event_type, key["event__event_type"])
        for name in key:
            self.assertNotIn("event_id", name,
                             "억제 키에 사건 번호가 들어왔습니다 (F-04 계약 위반).")
