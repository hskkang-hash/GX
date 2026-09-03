# -*- coding: utf-8 -*-
"""오탐 결합 규칙 — **붙이되 코드에서는 맞물리지 않게** (P-16 · 2026-09-20).

무엇을 묻는가
-------------
세종 판정(09-18 §1)은 셋을 함께 요구했다. 셋을 **따로** 잰다 — 한 시험이 셋을 물으면
어느 것이 깨졌는지 모른다.

    ① `rejected` 판정 하나가 대응 축을 **자동으로 종결**시키는가 (자동 1건)
    ② `confirmed` 로 **재판정해도 대응 축은 그대로**인가 (역방향 없음)
    ③ **다른 테넌트의 판정에는 반응하지 않는가** (격리 탐침)

그리고 결합이 **어디에 사는지**를 함께 잠근다:

    ④ `review_event` 가 `response_state` 를 **직접 쓰지 않는가** — 소비자를 떼면
      결합이 사라져야 한다. 사라지지 않으면 결합이 두 곳에 있다는 뜻이다.
    ⑤ 통지는 **1회**인가 — 두 번 알리면 「오탐이 두 번 일어났다」로 읽힌다
    ⑥ 라우트가 거절을 **4xx 로 나누는가** (404 · 422 · 403)

★ 왜 ④가 있는가. ①만 재면 「어디서든 닫히기만 하면」 초록이다. 그러면 다음 사람이
  `review_event` 안에 한 줄을 넣어도 시험은 그대로 초록이고, D-399 가 가른 두 축은
  조용히 다시 맞물린다. **수는 원인을 말하지 않는다** (세종 09-18 §0-4).
"""
from __future__ import annotations

from tests.test_dsm_app import DsmFixture


class _FakeRequest:
    """`_scope(request)` 가 읽는 최소한만 든 요청 (test_response_flow 와 같은 뜻)."""

    def __init__(self, user):
        self.user = user
        self.auth = user
        self.headers = {}
        self.META = {}
        self.GET = {}


class FalsePositiveCouplingFixture(DsmFixture):
    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        super().setUpTestData()
        from stream_monitors.models import DetectionEvent

        cls.S = DetectionEvent.ResponseState
        cls.Event = DetectionEvent

    def _row(self, event_id):
        return self.Event._base_manager.get(pk=event_id)


class CouplingHappensTest(FalsePositiveCouplingFixture):
    """① 자동 1건 · ② 역방향 없음."""

    def test_rejecting_closes_the_response_axis_once(self) -> None:
        """★ ① U1 이 「오탐」을 한 번 누르면 **대응 축도 닫힌다.**

        안 닫히면 사용자는 종결 버튼을 한 번 더 눌러야 하고, 그때 화면에는
        **두 종류의 종결**이 보인다 — P-1 화면 규칙이 막으려던 그 모양이다.
        """
        from kernels.k1_event import review_event

        eid = self._event(self.stream_a)
        self.assertEqual(self._row(eid).response_state, self.S.OCCURRED)

        review_event(eid, verdict="rejected", reason="연기가 아니라 안개였다",
                     scope=self.scope_a)

        self.assertEqual(
            self._row(eid).response_state, self.S.CLOSED,
            "오탐 판정이 대응 축을 닫지 않았습니다 — 결합 소비자가 안 돌고 있습니다 "
            "(stream_monitors/apps.py ready 에서 잇습니다).")

    def test_the_auto_close_is_recorded_as_the_rule_not_as_the_person(self) -> None:
        """★ 감사에는 **`system:false_positive`** 가 남는다.

        사람 이름으로 남기면 감사가 「그 사람이 종결했다」고 말한다 — 그 사람이 한 것은
        판정이고 종결은 규칙이 했다. 감사는 일어난 일을 적는 자리다.
        """
        from common import audit_writer
        from kernels.k1_event import review_event
        from kernels.k1_event.response_flow import FALSE_POSITIVE_ACTOR, LOGGER_NAME

        eid = self._event(self.stream_a)
        review_event(eid, verdict="rejected", reason="오탐", scope=self.scope_a)

        rows = audit_writer.read(logger_name=LOGGER_NAME, limit=20)
        self.assertTrue(rows, "대응 전이 감사가 한 줄도 없습니다.")

        Audit = self._audit_model()
        row = Audit._base_manager.filter(
            logger_name=LOGGER_NAME).order_by("-id").first()
        self.assertEqual(
            row.username, FALSE_POSITIVE_ACTOR,
            f"자동 종결의 행위자가 {row.username!r} 입니다 — 규칙이 한 일을 사람 이름으로 "
            f"적으면 감사가 거짓말을 합니다.")
        self.assertIn("reviewed_by", row.data_after or {},
                      "누가 오탐이라 눌렀는지가 본문에 없습니다 — 행위자 칸은 규칙의 "
                      "것이고, 그 규칙을 켠 사람은 본문에서 읽혀야 합니다.")

    @staticmethod
    def _audit_model():
        from common.audit_writer import _model

        return _model()

    def test_reconfirming_later_does_not_reopen_the_response_axis(self) -> None:
        """★ ② `rejected → confirmed` 재판정에도 대응 축은 **그대로 종결**이다.

        자동으로 다시 열면 두 축이 서로를 끌어당기고, 그 순간 「지금 어디까지 왔나」가
        판정의 그림자가 된다. 다시 여는 것은 사람이 한다 — U2 의 되돌림(사유 필수).
        """
        from kernels.k1_event import review_event

        eid = self._event(self.stream_a)
        review_event(eid, verdict="rejected", reason="오탐", scope=self.scope_a)
        self.assertEqual(self._row(eid).response_state, self.S.CLOSED)

        review_event(eid, verdict="confirmed", reason="다시 보니 진짜였다",
                     scope=self.scope_a)

        row = self._row(eid)
        self.assertEqual(row.verdict, "confirmed", "재판정이 판정 칸에 안 실렸습니다.")
        self.assertEqual(
            row.response_state, self.S.CLOSED,
            "재판정이 대응 축을 되돌렸습니다 — 대응 축은 verdict 를 읽지 않습니다 "
            "(역방향 없음 · P-16).")


class CouplingLivesInOnePlaceTest(FalsePositiveCouplingFixture):
    """④ **결합이 어디에 사는가** — 소비자를 떼면 결합도 사라져야 한다."""

    def test_review_event_itself_does_not_touch_the_response_axis(self) -> None:
        """★ 소비자를 잠시 떼고 판정하면 대응 축은 **움직이지 않아야** 한다.

        움직인다면 결합이 `review_event` 안에도 있다는 뜻이고, 그러면 D-399 가 가른
        두 축이 코드에서 다시 맞물린 것이다. 「닫히기만 하면 된다」로 재면 이 사실이
        안 보인다 — 그래서 이 시험이 있다.
        """
        from kernels.k1_event import review_event
        from kernels.k1_event.verdict_events import verdict_changed
        from stream_monitors.services.false_positive_closer import close_when_rejected

        eid = self._event(self.stream_a)
        verdict_changed.disconnect(close_when_rejected,
                                   dispatch_uid="gx.false_positive_closer")
        try:
            review_event(eid, verdict="rejected", reason="오탐", scope=self.scope_a)
            self.assertEqual(
                self._row(eid).response_state, self.S.OCCURRED,
                "소비자를 뗐는데도 대응 축이 닫혔습니다 — 결합이 두 곳에 있습니다.")
        finally:
            verdict_changed.connect(close_when_rejected,
                                    dispatch_uid="gx.false_positive_closer")

        # 다시 이었으니 같은 규칙이 다시 돈다 — **뗀 채로 끝나지 않는다.**
        eid2 = self._event(self.stream_a)
        review_event(eid2, verdict="rejected", reason="오탐", scope=self.scope_a)
        self.assertEqual(self._row(eid2).response_state, self.S.CLOSED)


class CouplingRespectsTenantsTest(FalsePositiveCouplingFixture):
    """③ 격리 탐침 — **남의 테넌트 판정에는 반응하지 않는다.**"""

    def test_a_foreign_tenants_event_cannot_be_rejected_or_closed(self) -> None:
        """B 의 이벤트를 A 가 오탐이라 하면 **거절되고, B 의 대응 축은 그대로**다.

        ★ 여기서 재는 것은 두 가지다: 판정이 막히는가(이미 D-290 이 잡는다) **그리고**
          결합이 그 문지기를 우회하지 않는가. 소비자가 시스템 행위자로 감사에 남는다고
          해서 문지기가 없어지면 「시스템이 하는 일에는 테넌트가 없다」가 되고,
          그것이 격리의 부재다 (D-281).
        """
        from django.http import Http404

        from kernels.k1_event import review_event

        victim = self._event(self.stream_b)
        with self.assertRaises((Http404, PermissionError)):
            review_event(victim, verdict="rejected", reason="남의 것",
                         scope=self.scope_a)

        row = self._row(victim)
        self.assertEqual(row.response_state, self.S.OCCURRED,
                         "남의 판정 시도가 우리 대응 축을 닫았습니다 — 격리가 없습니다.")
        self.assertIn(row.verdict, ("", None),
                      "남의 판정 시도가 판정 칸에 실렸습니다.")

    def test_the_signal_itself_cannot_close_a_foreign_event(self) -> None:
        """★ 신호를 **직접** 쏴도 못 닫는다 — 문지기는 소비자 안에도 있다.

        판정 라우트를 지나지 않고 신호만 흉내 내는 코드가 나중에 생길 수 있다.
        그때도 테넌트가 지켜지는지를 여기서 잠근다.
        """
        from django.http import Http404

        from kernels.k1_event.verdict_events import verdict_changed

        victim = self._event(self.stream_b)
        with self.assertRaises(Http404):
            verdict_changed.send(
                sender=self.Event, event_id=victim, verdict="rejected",
                previous="", scope=self.scope_a)
        self.assertEqual(self._row(victim).response_state, self.S.OCCURRED)


class FalsePositiveNoticeTest(FalsePositiveCouplingFixture):
    """⑤ 오탐 종결 통지 — **원 수신자에게 1회** (오탐 ③)."""

    def _notified(self, event_id):
        from kernels.k2_notify.services import FP_NOTICE_LOGGER, _fp_notice_key
        from common import audit_writer

        return audit_writer.read(logger_name=FP_NOTICE_LOGGER,
                                 action=_fp_notice_key(event_id), limit=5)

    def test_a_notified_event_that_becomes_a_false_positive_notifies_once(self) -> None:
        """알림이 **나갔던** 이벤트가 오탐이 되면 한 번 알린다. 두 번은 안 알린다."""
        from kernels.k1_event import review_event
        from kernels.k2_notify import send

        eid = self._event(self.stream_a)
        sent = send(scope=self.scope_a, event_id=eid)
        self.assertTrue(sent, "픽스처가 발송을 한 건도 못 만들었습니다.")

        review_event(eid, verdict="rejected", reason="오탐", scope=self.scope_a)
        self.assertEqual(len(self._notified(eid)), 1,
                         "오탐 종결 통지가 1회가 아닙니다.")

        # 두 번째 오탐 판정(같은 값)은 전이가 아니므로 통지도 늘지 않는다.
        review_event(eid, verdict="confirmed", reason="정정", scope=self.scope_a)
        review_event(eid, verdict="rejected", reason="다시 오탐", scope=self.scope_a)
        self.assertEqual(
            len(self._notified(eid)), 1,
            "오탐을 두 번 누르자 통지가 늘었습니다 — 받는 사람에게는 「오탐이 두 번 "
            "일어났다」로 읽힙니다.")

    def test_an_event_that_was_never_notified_notifies_nobody(self) -> None:
        """★ 알림이 안 나갔으면 알릴 사람도 없다 — **0명과 실패는 다른 사실**이다."""
        from kernels.k1_event import review_event

        eid = self._event(self.stream_a)
        review_event(eid, verdict="rejected", reason="오탐", scope=self.scope_a)
        self.assertEqual(
            self._notified(eid), (),
            "받은 적 없는 사람에게 정정을 보냈습니다 — 없던 경보를 만들어 냅니다.")
        self.assertEqual(self._row(eid).response_state, self.S.CLOSED,
                         "통지가 없다고 종결까지 안 일어나면 안 됩니다.")

    def test_the_notice_does_not_create_a_delivery_row(self) -> None:
        """★★ 통지는 **발송이 아니라 뒷정리**다.

        `DeliveryRecord` 에 행을 만들면 두 가지가 함께 망가진다:
          · F-10 의 30초 지연 통계가 **경보가 아닌 것**을 경보로 세고
          · 5분 억제가 이 통지를 최근 발송으로 읽어 **다음 진짜 경보를 삼킨다**
        """
        from django.apps import apps as django_apps

        from kernels.k1_event import review_event
        from kernels.k2_notify import send

        Delivery = django_apps.get_model("stream_monitors", "DeliveryRecord")
        eid = self._event(self.stream_a)
        send(scope=self.scope_a, event_id=eid)
        before = Delivery._base_manager.filter(event_id=eid).count()

        review_event(eid, verdict="rejected", reason="오탐", scope=self.scope_a)

        self.assertEqual(
            before, Delivery._base_manager.filter(event_id=eid).count(),
            "오탐 통지가 발송 이력에 행을 남겼습니다 — F-10 지연과 5분 억제가 "
            "그 행을 경보로 셉니다.")


class ReviewRouteRefusalIsFourXXTest(FalsePositiveCouplingFixture):
    """⑥ 판정 라우트 — 거절이 **4xx 로 갈린다** (오탐 ②)."""

    def _status_of(self, event_id, verdict, user=None):
        from ninja.errors import HttpError

        from apps.dsm.api import DsmAPI

        try:
            DsmAPI.review_event(DsmAPI, _FakeRequest(user or self.user_a),
                                event_id=event_id, verdict=verdict, reason="시험")
        except HttpError as exc:
            return exc.status_code
        return 200

    def test_a_real_review_returns_200_with_both_axes(self) -> None:
        """★ 양성 대조 — 전부 거절하는 문은 격리가 아니라 **죽은 문**이다.

        그리고 응답이 **두 축을 함께** 실어야 한다. 화면이 종결 상태를 한 번 더 물어야
        하면 그 사이에 두 종류의 종결이 보인다.
        """
        from apps.dsm.api import DsmAPI

        eid = self._event(self.stream_a)
        out = DsmAPI.review_event(DsmAPI, _FakeRequest(self.user_a),
                                  event_id=eid, verdict="rejected", reason="안개였다")
        self.assertEqual(out["verdict"], "rejected")
        self.assertEqual(out["response_state"], self.S.CLOSED,
                         "판정 응답이 대응 축의 결과를 안 실었습니다 — 화면이 한 번 더 "
                         "물어야 하고, 그 사이가 P-1 이 막으려던 자리입니다.")

    def test_an_unknown_verdict_is_422_not_200(self) -> None:
        """`closed` 는 판정값이 아니다 — 종료는 다른 문이다. **422**."""
        eid = self._event(self.stream_a)
        self.assertEqual(422, self._status_of(eid, "closed"))
        self.assertEqual(self._row(eid).response_state, self.S.OCCURRED,
                         "거절됐는데 대응 축이 움직였습니다 — 반쯤 간 상태입니다.")

    def test_a_missing_event_is_404(self) -> None:
        """없는 이벤트도 **남의 이벤트**도 404 다 — 존재 여부가 새는 것도 누출이다."""
        self.assertEqual(404, self._status_of(10_000_000, "rejected"))

    def test_a_foreign_event_is_404_too(self) -> None:
        victim = self._event(self.stream_b)
        self.assertEqual(404, self._status_of(victim, "rejected"))
        self.assertEqual(self._row(victim).response_state, self.S.OCCURRED)
