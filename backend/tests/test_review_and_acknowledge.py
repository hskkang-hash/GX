# -*- coding: utf-8 -*-
"""WO-GX-20260915-01 §5 · AC-2 — **판정 + 접수 한 트랜잭션**.

이 파일이 묻는 것 다섯 — 지시서 §3 AC-2 검증 방법 그대로
------------------------------------------------------------
  ① 성공          재조회 `verdict=confirmed` · `response_state=acknowledged` · 감사 1행
  ② 중간 실패 주입  둘 다 안 바뀐다(롤백) — 판정만 되고 접수가 안 되는 반쪽짜리가 없다
  ③ 다른 테넌트     남의 이벤트는 404(존재 여부도 새면 누출이다 · IDOR)
  ④ 읽기 전용 역할   403 — `RoleGateMiddleware`(P-119)가 **이 라우트를 새로 안 것 없이** 막는다
  ⑤ 이미 종결       `closed` 에서 `acknowledged` 로는 못 간다(409) · 판정도 함께 롤백

★ **재조회로 잰다** (기억 속 스레드 요청지 말고 캐시가 아니라 대상을 잰다 · QA-05).
  `review_and_acknowledge()` 가 돌려준 dict 를 믿지 않고, 매번 `services.event_detail`·
  `services.response_state` 를 **새로 불러** 확인한다 — 반환값과 실제 저장이 갈리는
  것이 이 종류 버그의 전형이다.

★ **기존 함수를 고치지 않는다.** `review_event`·`advance_response` 는 그대로 두고,
  이 시험도 그 둘을 다시 묻지 않는다(전이표 자체는 `tests/test_response_flow.py` 의
  일이다) — 여기서 다시 물으면 같은 사실을 두 벌로 재고 커널이 바뀔 때 두 곳에서 깨진다.
"""
from __future__ import annotations

import json
from unittest import mock

from django.apps import apps
from django.http import Http404
from django.test import Client, TestCase

from tests.test_dsm_app import DsmFixture

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "apps.dsm.services.review_and_acknowledge(신설) · kernels.k1_event.services."
    "review_event · kernels.k1_event.response_flow.advance_response · logger.AuditLogs · "
    "common.role_gate.RoleGateMiddleware — 저장소의 실제 App·커널·미들웨어. 합성 더미를 "
    "부르지 않는다"
)


def _forget_leftover_request() -> None:
    """스레드에 남은 요청을 지운다 — 이 파일의 HTTP 시험 뒤에 오는 시험을 위해서다
    (메모리 「스레드에 남은 요청이 거짓 초록을 만든다」와 같은 사유)."""
    import contextlib

    with contextlib.suppress(Exception):
        from core.middleware.refresh_token import thread_local

        thread_local.request = None


class _CleanThreadLocal:
    def setUp(self):
        _forget_leftover_request()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        _forget_leftover_request()


class ReviewAndAcknowledgeTest(DsmFixture):
    """① 성공 · ② 롤백 · ③ 다른 테넌트 · ⑤ 이미 종결 — 함수를 직접 불러 잰다."""

    def _audit_count(self) -> int:
        from kernels.k1_event.response_flow import LOGGER_NAME

        AuditLogs = apps.get_model("logger", "AuditLogs")
        return AuditLogs._base_manager.filter(logger_name=LOGGER_NAME).count()

    # ── ① 성공 ──────────────────────────────────────────────────────────
    def test_success_sets_verdict_and_acknowledges_in_one_audit_row(self) -> None:
        from apps.dsm import services

        eid = self._event(self.stream_a)
        before_audit = self._audit_count()

        result = services.review_and_acknowledge(scope=self.scope_a, event_id=eid)

        self.assertEqual(result["verdict"], "confirmed")
        self.assertEqual(result["response_state"], "acknowledged")
        self.assertIsNotNone(result["audit_id"])

        # ★ **재조회다.** 함수가 돌려준 값이 아니라 DB 를 다시 읽는다.
        fresh_event = services.event_detail(scope=self.scope_a, event_id=eid)
        fresh_state = services.response_state(scope=self.scope_a, event_id=eid)
        self.assertEqual(fresh_event.verdict, "confirmed")
        self.assertIsNotNone(fresh_event.reviewed_at)
        self.assertEqual(fresh_state["response_state"], "acknowledged")
        self.assertEqual(fresh_state["allowed_next"], ["in_progress"])

        # ★ 감사는 **한 행**이다 — 판정 함수는 감사를 쓰지 않고, 접수 함수가 쓰는
        #   그 한 행이 둘을 함께 말한다(WO-01 §5).
        self.assertEqual(self._audit_count() - before_audit, 1,
                         "판정+접수 한 트랜잭션이 감사를 한 행이 아니게 남겼습니다.")

    # ── ② 중간 실패 주입 시 롤백 ───────────────────────────────────────
    def test_a_failure_in_the_second_half_rolls_back_the_first(self) -> None:
        """접수 쪽(둘째)에서 실패를 주입한다 — **판정(첫째)도 함께 안 남아야 한다.**"""
        from apps.dsm import services

        eid = self._event(self.stream_a)
        before_audit = self._audit_count()

        with mock.patch(
            "apps.dsm.services.advance_response",
            side_effect=RuntimeError("주입한 실패 — 접수 쪽에서 터진다"),
        ):
            with self.assertRaises(RuntimeError):
                services.review_and_acknowledge(scope=self.scope_a, event_id=eid)

        fresh_event = services.event_detail(scope=self.scope_a, event_id=eid)
        fresh_state = services.response_state(scope=self.scope_a, event_id=eid)
        self.assertIsNone(
            fresh_event.verdict,
            "접수가 실패했는데 판정이 남았습니다 — 반쪽짜리 사건이 생겼습니다.")
        self.assertIsNone(fresh_event.reviewed_at)
        self.assertEqual(
            fresh_state["response_state"], "occurred",
            "접수가 실패했는데 처리 단계가 움직였습니다.")
        self.assertEqual(
            self._audit_count(), before_audit,
            "롤백됐는데 감사 행이 남았습니다 — 일어나지 않은 일이 기록됐습니다.")

    # ── ③ 다른 테넌트 사건 거부 ─────────────────────────────────────────
    def test_another_tenants_event_is_404_not_leaked(self) -> None:
        """남의 이벤트는 **404** 다 — 403 이 아니다(존재 여부도 새면 누출이다)."""
        from apps.dsm import services

        eid = self._event(self.stream_a)
        with self.assertRaises(Http404):
            services.review_and_acknowledge(scope=self.scope_b, event_id=eid)

        # ★ 문지기가 먼저 서므로 A 쪽 사실도 안 바뀐다.
        fresh_event = services.event_detail(scope=self.scope_a, event_id=eid)
        self.assertIsNone(fresh_event.verdict)

    # ── ⑤ 이미 종결된 사건의 전이 거부 (+ 롤백의 두 번째 증거) ────────────
    def test_an_already_closed_event_rejects_the_transition_and_rolls_back(self) -> None:
        from apps.dsm import services

        eid = self._event(self.stream_a)
        for state in ("acknowledged", "in_progress", "closed"):
            services.advance_response(scope=self.scope_a, event_id=eid, to_state=state)

        with self.assertRaises(services.ResponseTransitionForbidden):
            services.review_and_acknowledge(scope=self.scope_a, event_id=eid)

        fresh_event = services.event_detail(scope=self.scope_a, event_id=eid)
        fresh_state = services.response_state(scope=self.scope_a, event_id=eid)
        self.assertIsNone(
            fresh_event.verdict,
            "이미 종결된 사건인데 판정이 남았습니다 — 접수는 거절됐는데 판정만 된 "
            "반쪽짜리 사건이 생겼습니다.")
        self.assertEqual(fresh_state["response_state"], "closed",
                         "종결된 사건의 처리 단계가 거절된 요청으로 움직였습니다.")


# ═══════════════════════════════════════════════════════════════════════════
# ④ 읽기 전용 역할 403 — **문을 두드린다** (D-210). 함수가 아니라 HTTP 다.
# ═══════════════════════════════════════════════════════════════════════════
class ReadOnlyRoleIsBlockedByTheExistingGateTest(_CleanThreadLocal, TestCase):
    """P-119 `RoleGateMiddleware` 는 **전역 규칙**이다 — 이 라우트를 새로 안 것이
    하나도 없어도 읽기 전용 계정의 쓰기를 막는다(WO-01 §5 재사용 — 새 인증 경로 없음).

    캐시 처리: **우회** — `X-No-Cache`(D-341 착시 ⑦). 관문을 재는 시험이 캐시를 재면
    이 라우트가 없어도 초록이 뜬다.
    """

    PASSWORD = "gx-review-ack-test-only-not-a-secret"  # noqa: S105 — 시험 전용, 저장소 밖 값 아님

    @classmethod
    def setUpTestData(cls) -> None:
        _forget_leftover_request()
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")

        view_only = Role.objects.create(
            role_name="View Only - ReviewAck", code="view_only_-_review_ack")
        other = Role.objects.create(role_name="review_ack_op", code="review_ack_op")

        cls.reader = CoreUser.objects.create_user(
            username="gx_review_ack_reader", password=cls.PASSWORD, is_active=True,
            email="gx_review_ack_reader@test.invalid")
        cls.reader.roles.add(view_only)

        cls.writer = CoreUser.objects.create_user(
            username="gx_review_ack_writer", password=cls.PASSWORD, is_active=True,
            email="gx_review_ack_writer@test.invalid")
        cls.writer.roles.add(other)

    def setUp(self):
        super().setUp()
        from tests.no_cache import NO_CACHE

        self.client = Client(**NO_CACHE)

    def _hit(self, user):
        from tests.test_api_contract import _bearer

        # ★ **실재하지 않는 id 로 두드린다** (메모리 「라우트 삼킴 함정」·P-119 의
        #   관례 그대로) — 쓰기 면을 실재 사건 id 로 때리는 것이 곧 사고다. 이 시험이
        #   묻는 것은 「관문이 서는가」이지 「전이가 되는가」가 아니다.
        return self.client.post(
            "/api/dsm/events/999999999/review-and-acknowledge",
            data=b"{}", content_type="application/json",
            **_bearer(user),
        )

    def test_read_only_write_is_403_with_no_tenant_data(self) -> None:
        from common import role_gate

        resp = self._hit(self.reader)
        self.assertEqual(resp.status_code, 403)
        body = json.loads(resp.content)
        self.assertEqual(body.get("code"), role_gate.READONLY_DENIAL_CODE)
        self.assertEqual(body.get("status_code"), 403)
        self.assertIn("ko", body.get("message", {}))

    def test_the_same_door_is_not_403_for_another_role(self) -> None:
        """★ **음성 대조.** 관문이 늘 빨간불이면 그것은 관문이 아니다(D-277).

        `other` 역할은 읽기 전용이 아니므로 이 관문에서는 403 이 나지 않는다 — 그
        뒤(테넌트·존재 여부)에서 무엇이 나든 이 시험이 보려는 것은 **관문 하나**뿐이다.
        """
        resp = self._hit(self.writer)
        self.assertNotEqual(resp.status_code, 403)
