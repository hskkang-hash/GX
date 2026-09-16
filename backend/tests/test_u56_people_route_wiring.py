# -*- coding: utf-8 -*-
"""턴 R · U56 ④ — `apps/dsm/people.py` 를 **부르는 자리**가 실제로 있는가 (라우트까지).

왜 또 하나의 시험인가 — `test_u56_people_deactivate_401.py` 와 무엇이 다른가
------------------------------------------------------------------------------
그 파일은 `create_person`/`deactivate_person` 을 **파이썬 함수로 직접** 부른다.
`scripts/verify_dormant.py` 는 그것도 "부르는 자리"로 보지 않는다 —
"시험만 부르는 것도 여기다: 운영에서는 죽은 것이다"(㉠ 호출 없음). 그래서 턴 R 은
이 함수들을 **부르는 라우트**(`apps/dsm/api_u56.py`)를 새로 냈다. 이 파일은 그
라우트를 HTTP 왕복으로 두드려 잰다 — 함수 호출이 아니라 **문**을 두드린다.

★ 경로 함정 — 이 시험이 잡을 뻔한 것
--------------------------------------
`/api/dsm/settings/people`(한 조각)은 `api.py` 의 `GET /settings/{domain}` 에
**삼켜져 405 를 낸다**(선언 순서가 곧 라우팅). 그래서 라우트는 두 조각
(`/settings/people/create`)으로 열었다 — 이 시험은 그 경로를 그대로 두드려
405 가 아니라 실제 판정(200/403/401)이 나오는지를 확인한다.
"""
from __future__ import annotations

import json
import uuid

from django.apps import apps
from django.conf import settings
from django.test import Client

from tests.no_cache import NO_CACHE
from tests.test_dsm_app import DsmFixture


class PeopleRouteWiringTest(DsmFixture):
    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)
        self.username = "u56_r_person_%s" % uuid.uuid4().hex[:8]

    def _admin_user(self):
        Role = apps.get_model("role", "Role")
        role, _ = Role.objects.get_or_create(code="admin", defaults={"role_name": "admin"})
        role = self._own(role, self.group_a)
        self.user_a.roles.add(role)
        self.user_a.refresh_from_db()
        return self.user_a

    def _bearer(self, user) -> dict:
        import jwt as pyjwt
        from ninja_jwt.tokens import RefreshToken

        session_id = str(uuid.uuid4())
        refresh = RefreshToken.for_user(user)
        refresh["session_id"] = session_id
        access = str(refresh.access_token)
        decoded = pyjwt.decode(
            access, settings.NINJA_JWT["SIGNING_KEY"],
            algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")])
        setter = getattr(user, "set_encrypted_session_token", None)
        if setter is not None:
            setter(session_id, decoded.get("jti"))
            user.save()
        return {"HTTP_AUTHORIZATION": "Bearer %s" % access}

    def _create(self, admin, username: str):
        return self.client.post(
            "/api/dsm/settings/people/create"
            "?username=%s&email=%s@test.invalid&password=not-a-real-secret-1!"
            "&group_id=%s&display_name=%s" % (
                username, username, self.group_a.pk, username),
            **self._bearer(admin), **{"HTTP_X_NO_CACHE": "true"})

    def test_admin_creates_and_deactivates_a_person_over_http(self):
        """★ 닫는 조건 — 발급 1(생성) · 폐기 1(비활성화)이 **라우트**로 된다."""
        admin = self._admin_user()

        resp = self._create(admin, self.username)
        self.assertEqual(
            200, resp.status_code,
            (resp.content or b"")[:400].decode("utf-8", "replace"))
        body = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(body.get("user_id"))
        self.assertEqual(self.username, body.get("username"))
        self.assertIn("audit_id", body)

        CoreUser = apps.get_model("user", "CoreUser")
        row = CoreUser._base_manager.filter(pk=body["user_id"]).first()
        self.assertIsNotNone(row, "라우트가 실제 생성 경로를 안 탔습니다 — 행이 없습니다.")
        self.assertTrue(row.is_active)

        deact = self.client.post(
            "/api/dsm/settings/people/%s/deactivate" % body["user_id"],
            **self._bearer(admin), **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(
            200, deact.status_code,
            (deact.content or b"")[:400].decode("utf-8", "replace"))
        row.refresh_from_db()
        self.assertFalse(row.is_active, "비활성화 라우트를 탔는데 계정이 그대로 켜져 있습니다.")

    def test_a_plain_role_cannot_create_a_person(self):
        """★ 대조군 — 역할 없는 계정은 403. dj-core 문 자체엔 권한 검사가 없으므로
        (`people.py` 머리말), 이 라우트의 `guard_setting` 이 **유일한 문지기**다."""
        resp = self._create(self.user_a, "u56_r_should_not_%s" % uuid.uuid4().hex[:6])
        self.assertEqual(
            403, resp.status_code,
            (resp.content or b"")[:400].decode("utf-8", "replace"))

    def test_anonymous_gets_401_not_403(self):
        resp = self.client.post(
            "/api/dsm/settings/people/create"
            "?username=x&email=x@test.invalid&password=x&group_id=%s" % self.group_a.pk,
            **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(401, resp.status_code)
