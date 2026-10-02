# -*- coding: utf-8 -*-
"""WO-GRDX-20261002-10 AC-2 — GCS 경유: 화면은 GCS 키를 들지 않고, 서버가 제 자격으로 부른다.

출생 표본 [실측 2026-10-02 · `-06` AC-5] 배포 번들에 GCS bearer 키 원문 4벌(`VITE_CGS_APIKEY`).
이 시험은 경유 문이 닫힌 쪽이 기본인지 잰다: 로그인 없음 401 · 역할 0 403 · 읽기 전용의 쓰기 403 ·
허용 밖 경로 404 · 정상 200(GCS 는 가짜) — 그리고 서버 키가 **위로만** 가고 응답에 안 실리는지.

캐시 처리: 우회 — `tests.no_cache.NO_CACHE` 로 응답 캐시를 타지 않는다.
"""
from __future__ import annotations

import contextlib
from unittest import mock

from django.apps import apps
from django.test import Client, TestCase, override_settings

from apps.gcs import api as gcs
from tests.no_cache import NO_CACHE
from tests.test_api_contract import _bearer

PASSWORD = "wo10-test-only-not-a-secret"
FAKE_KEY = "FAKE_gcs_key_for_test_only_0000000000"


def _forget_leftover_request() -> None:
    with contextlib.suppress(Exception):
        from core.middleware.refresh_token import thread_local
        thread_local.request = None


class _Up:
    status_code = 200
    content = b'{"drones": []}'
    headers = {"Content-Type": "application/json"}


@override_settings(GCS_APIKEY=FAKE_KEY, FLIGHTBRID_URL="http://gcs.test.invalid:8009")
class GcsProxyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        _forget_leftover_request()
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")

        def _mk(name, *codes):
            u = CoreUser.objects.create_user(username=name, password=PASSWORD, is_active=True,
                                             email=f"{name}@test.invalid",
                                             first_name="me", last_name="probe")
            for c in codes:
                u.roles.add(Role.objects.get_or_create(code=c, defaults={"role_name": c})[0])
            return u

        cls.operator = _mk("wo10_operator", "fire_user")
        cls.no_role = _mk("wo10_norole")
        cls.view_only = _mk("wo10_viewonly", "view_only_-_anyang")

    def tearDown(self):
        _forget_leftover_request()

    def _get(self, path, user=None, method="get"):
        c = Client(raise_request_exception=False, **NO_CACHE)
        extra = _bearer(user) if user else {}
        r = getattr(c, method)(path, **extra)
        _forget_leftover_request()
        return r

    def test_anonymous_is_401_and_never_calls_gcs(self):
        with mock.patch.object(gcs.requests, "request") as up:
            r = self._get("/api/gcs/drones")
        self.assertEqual(r.status_code, 401)
        up.assert_not_called()

    def test_no_role_is_403(self):
        with mock.patch.object(gcs.requests, "request") as up:
            r = self._get("/api/gcs/drones", self.no_role)
        self.assertEqual(r.status_code, 403)
        up.assert_not_called()

    def test_read_only_role_cannot_write(self):
        with mock.patch.object(gcs.requests, "request") as up:
            r = self._get("/api/gcs/drones/drones/u1/command", self.view_only, method="post")
        self.assertEqual(r.status_code, 403)
        up.assert_not_called()

    def test_operator_gets_gcs_answer_and_key_goes_only_upstream(self):
        with mock.patch.object(gcs.requests, "request", return_value=_Up()) as up:
            r = self._get("/api/gcs/drones?access_key=leak&group_id=7", self.operator)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b'{"drones": []}')
        args, kwargs = up.call_args
        self.assertEqual(args, ("GET", "http://gcs.test.invalid:8009/drones"))
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {FAKE_KEY}")
        self.assertEqual(kwargs["params"], [("group_id", "7")])  # 쿼리 자격은 버린다
        self.assertNotIn(FAKE_KEY.encode(), r.content)

    def test_paths_outside_the_library_are_404(self):
        with mock.patch.object(gcs.requests, "request") as up:
            for p in ("/api/gcs/auth/login", "/api/gcs/admin", "/api/gcs/api/secret", "/api/gcs/drones/../auth"):
                r = self._get(p, self.operator)
                self.assertIn(r.status_code, (404,), p)
        up.assert_not_called()

    def test_unreachable_gcs_is_502_without_address(self):
        import requests as _rq
        with mock.patch.object(gcs.requests, "request", side_effect=_rq.ConnectionError("http://gcs.test.invalid:8009 down")):
            r = self._get("/api/gcs/health", self.operator)
        self.assertEqual(r.status_code, 502)
        self.assertNotIn(b"gcs.test.invalid", r.content)


def test_allowed_path_table():
    assert gcs.allowed_path("drones")
    assert gcs.allowed_path("api/drone/profile/3")
    assert gcs.allowed_path("api/v1/groups")
    assert not gcs.allowed_path("api/v2/x")
    assert not gcs.allowed_path("auth/login")
    assert not gcs.allowed_path("")
    assert not gcs.allowed_path("drones/../auth")
