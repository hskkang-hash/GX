# -*- coding: utf-8 -*-
"""P-439 — `backend/conftest.py::clear_thread_request`(autouse)가 매 시험 전후로
`core.middleware.refresh_token.thread_local.request` 를 비우는가 (턴 AQ · 차선 Q).

앞 시험(`test_1_…`)이 스레드에 요청을 **심고 치우지 않는다** — 턴 AP 전량 1회차의 가해
시험 모양 그대로(`created_by=53` 오염). 다음 시험(`test_2_…`)이 **비었음**을 확인한다.
unittest 는 메서드 이름 순으로 돈다(`-p no:randomly`) — 그래서 이름에 순번을 붙였다.

캐시 처리: 해당 없음 — HTTP 를 안 두드리고 DB 도 안 쓴다(`SimpleTestCase`).
"""
from __future__ import annotations

from django.test import SimpleTestCase


class _Planted:
    """앞 시험이 남긴 요청 흉내 — `user.id=53`(턴 AP 관측값)."""

    class user:  # noqa: N801
        id = 53
        pk = 53


class ThreadRequestIsClearedBetweenTests(SimpleTestCase):
    def test_1_plant_leftover_request_and_do_not_clean(self) -> None:
        from core.middleware.refresh_token import thread_local

        self.assertIsNone(getattr(thread_local, "request", None),
                          "시험이 시작할 때부터 스레드에 요청이 남아 있다 — autouse 가 안 돌았다")
        thread_local.request = _Planted()           # 일부러 치우지 않는다(가해 시험 모양)
        self.assertIs(thread_local.request.__class__, _Planted)

    def test_2_next_test_sees_no_leftover_request(self) -> None:
        from core.middleware.refresh_token import thread_local

        self.assertIsNone(getattr(thread_local, "request", None),
                          "앞 시험이 심은 요청이 다음 시험까지 남았다 — P-439 회귀")

    def test_3_fixture_is_registered_as_autouse(self) -> None:
        import conftest

        fx = getattr(conftest, "clear_thread_request", None)
        self.assertIsNotNone(fx, "conftest 에 clear_thread_request 픽스처가 없다")
        marker = getattr(fx, "_pytestfixturefunction", None) or getattr(fx, "_fixture_function_marker", None)
        if marker is not None:
            self.assertTrue(getattr(marker, "autouse", False), "autouse 가 아니다")
