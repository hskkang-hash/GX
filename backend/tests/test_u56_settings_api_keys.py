# -*- coding: utf-8 -*-
"""U6#1 · SEC-22 — 「API Key 발급 문이 403 을 낸다」의 뿌리를 문으로 잰다 (턴 Q · 차선 U56).

무엇을 재는가
--------------
`scripts/verify_click_completes.py` 는 U6(연계 담당) 흐름의 마지막 한 줄에서
`POST /api/dsm/settings/api-keys` 를 **관리자 자격**으로만 두드린다(그 파일의 주석
[실측 08:24 · U6#1·#4] · `api.py:986` `PermissionDeniedForSetting` → 403). 설정 문은
`common/tenant_roles.is_tenant_admin`(코드 `tenant_admin_<group_id>`) 또는
`is_global_admin` 만 지난다(`apps/dsm/services.py::_decide`) — **판정식은 한 곳**이고
여기서 복사하지 않는다(D-212).

턴 Q 판정: 게이트가 403 을 받은 것은 제품의 결함이 아니라 **자격의 결함**이었다 — 발급
문을 두드린 계정(`gxprobe_q`)에게 `tenant_admin_<자기 group_id>` 역할이 없었다. 이
시험은 그 자격이 **있을 때 문이 실제로 200 을 내는가**를 Django 시험 클라이언트로
(서비스 함수를 직접 부르지 않고) 라우트까지 통째로 증명한다 — 권한 검사 자체를
약하게 만들지 않는다(닫힌 쪽으로 닫는다).

★ 값은 시험에서도 출력하지 않는다 — `secret` 길이만 확인하고 값 자체는 assert 문
  밖으로 내지 않는다(§ 공통 규칙 5).
"""
from __future__ import annotations

import json
import uuid

from django.apps import apps
from django.conf import settings
from django.test import Client

from tests.no_cache import NO_CACHE
from tests.test_dsm_app import DsmFixture


class ApiKeyIssueDoorTest(DsmFixture):
    """설정 문(F-05 「발급」)이 **역할에 따라 갈리는가** — HTTP 왕복으로."""

    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    # ── 자격 ─────────────────────────────────────────────────────────────
    def _tenant_admin_user(self):
        """`self.user_a` 에 `tenant_admin_<group_a>` 역할을 **더한다** — 대체하지 않는다.

        기존 `dsm_watch_a` 역할은 그대로 둔다 — 역할을 더하는 것이지 바꿔치는 것이
        아니다. 실제 부여(`gxprobe_q`)도 이 규약을 그대로 따랐다(§ 최종 보고).
        """
        from common.tenant_roles import tenant_admin_role_code

        Role = apps.get_model("role", "Role")
        code = tenant_admin_role_code(self.group_a.pk)
        role, _ = Role.objects.get_or_create(code=code, defaults={"role_name": code})
        role = self._own(role, self.group_a)
        self.user_a.roles.add(role)
        self.user_a.refresh_from_db()
        return self.user_a

    def _bearer(self, user) -> dict:
        """세션까지 묶은 접근 토큰 — `force_login` 만으로는 ninja JWT 라우터가 401 이다
        (test_tenant_isolation.py 의 같은 도우미와 동일한 세 단계: session_id → access
        → jti 저장)."""
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

    # ── 시험 ─────────────────────────────────────────────────────────────
    def test_tenant_admin_role_issues_a_key_over_http(self):
        """★ 닫는 조건 — `tenant_admin_<group>` 을 가진 계정은 200 을 받는다."""
        admin = self._tenant_admin_user()
        resp = self.client.post(
            "/api/dsm/settings/api-keys?name=u56-p141-sec22",
            **self._bearer(admin), **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(
            200, resp.status_code,
            (resp.content or b"")[:400].decode("utf-8", "replace"))
        body = json.loads(resp.content.decode("utf-8"))
        # ★ 값 자체는 검사하지 않는다 — **있다는 사실**과 **모양**만 잰다.
        self.assertIn("secret", body, "발급 응답에 secret 칸이 없습니다.")
        self.assertTrue(body["secret"], "secret 이 비어 있습니다.")
        self.assertIn("audit_id", body, "발급이 감사에 남지 않았습니다 (AC-12).")

    def test_a_plain_role_still_gets_403_not_weakened(self):
        """★ 대조군 — 역할이 없는 계정(`dsm_watch_a`)은 **여전히** 403 이다.

        SEC-22 를 닫는다고 문지기를 느슨하게 만들지 않았다는 증거.
        """
        resp = self.client.post(
            "/api/dsm/settings/api-keys?name=u56-should-not-issue",
            **self._bearer(self.user_a), **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(
            403, resp.status_code,
            (resp.content or b"")[:400].decode("utf-8", "replace"))

    def test_anonymous_gets_401_not_403(self):
        """익명은 인증 자체가 없다 — 401. 이 자리가 403 으로 새면 인증 경로가 흔들린 것."""
        resp = self.client.post(
            "/api/dsm/settings/api-keys?name=u56-anon",
            **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(401, resp.status_code)
