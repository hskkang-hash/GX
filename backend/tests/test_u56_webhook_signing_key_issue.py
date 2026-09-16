# -*- coding: utf-8 -*-
"""P-145 — 「서명키는 우리가 만든다」의 닫는 조건: **구독 1 → 키 1 → 발송 서명 검증 시험 1**
(턴 R · 차선 U56).

무엇이 문제였나 [`tests/test_u56_webhook_signing_key.py` 의 실측 · 턴 Q]
------------------------------------------------------------------------
이 개발 환경의 `settings.WEBHOOK_SIGNING_KEYS` 는 **비어 있었다** — 그래서 기존
`POST /webhook-subscriptions`(이름을 미리 알아야 하는 문)는 이 환경에서 어떤
이름으로도 늘 422 였다(값을 저장소 밖 `.env` 에 아직 아무도 안 넣었기 때문).
그 문제는 "코드 결함"이 아니라 "값이 없다"는 환경 문제였다.

이 파일이 잰다 — **값이 없어도 되는 길**
------------------------------------------
`POST /api/dsm/settings/webhook-subscriptions/issue`(이번 턴에 새로 난 문)는 이름도
값도 **호출자에게 요구하지 않는다.** `secrets.token_urlsafe(48)` 로 값을 직접
만들어 그 자리에서 표를 채운다(`kernels.k5_trust.generate_signing_key`) — 그래서
환경 변수가 비어 있어도 구독 1건이 실제로 서고, 그 값으로 서명한 요청이 우리
자신의 검증기(`common.webhook_contract.verify`)를 통과한다는 것까지 잰다.

★ 값은 이 시험에서도 **assert 문 밖으로 내지 않는다** — 길이와 sha256 앞 12자,
  그리고 "본문에 값이 두 번 나오지 않는다"만 본다(§ 공통 규칙 5).
"""
from __future__ import annotations

import hashlib
import json
import uuid

from django.apps import apps
from django.conf import settings
from django.test import Client

from tests.no_cache import NO_CACHE
from tests.test_dsm_app import DsmFixture


class WebhookSigningKeyIssuanceTest(DsmFixture):
    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    # ── 자격 — U5 시드와 같은 모양: `admin` 역할 하나(P-146 매핑을 그대로 탄다) ──
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

    def test_subscription_issues_a_key_and_the_key_signs_a_verifiable_delivery(self):
        """★ 닫는 조건 전부 — 구독 1 → 키 1 → 발송 서명 검증 1."""
        admin = self._admin_user()

        # ── 구독 1 → 키 1 ────────────────────────────────────────────────
        resp = self.client.post(
            "/api/dsm/settings/webhook-subscriptions/issue"
            "?endpoint_url=https://receiver.test.invalid/hook&event_types=fire",
            **self._bearer(admin), **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(
            200, resp.status_code,
            (resp.content or b"")[:400].decode("utf-8", "replace"))
        body = json.loads(resp.content.decode("utf-8"))

        self.assertTrue(body.get("subscription_id"), "구독이 서지 않았습니다.")
        name = body.get("signing_key_name")
        secret = body.get("signing_key_secret")
        self.assertTrue(name, "서명키 이름이 응답에 없습니다.")
        self.assertTrue(secret, "서명키 값이 응답에 없습니다.")
        self.assertGreaterEqual(len(secret), 48, "값 길이가 예상보다 짧습니다.")
        self.assertIn("audit_id", body, "발급이 감사에 남지 않았습니다.")

        # ── 값은 한 번만 — 목록 조회에는 값이 없다 ──────────────────────
        list_resp = self.client.get(
            "/api/dsm/webhook-subscriptions",
            **self._bearer(admin), **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(200, list_resp.status_code)
        self.assertNotIn(
            secret, list_resp.content.decode("utf-8", "replace"),
            "목록 조회 응답에 서명키 값이 다시 실렸습니다 — 한 번만이라는 규칙 위반.")

        # ── 발송 서명 검증 1 — 그 값이 실제로 서명·검증에 쓰이는가 ─────
        from common import webhook_contract, webhook_outbox

        vault_value = webhook_outbox.signing_secret(name)
        self.assertEqual(
            secret, vault_value,
            "금고(설정 표)에서 되읽은 값이 응답값과 다릅니다 — 등록에 쓰인 이름과 "
            "실제로 채워진 값이 어긋났을 수 있습니다.")

        body_bytes = b'{"event_id": 1, "event_type": "fire"}'
        headers = webhook_contract.outbound_headers(vault_value, body_bytes, event_id="1")
        ok, why = webhook_contract.verify(vault_value, body_bytes, headers)
        self.assertTrue(ok, "우리가 만든 값으로 서명한 요청이 우리 검증기를 통과하지 "
                           "못했습니다: %s" % why)

        # ── 대조군 — 다른 값으로는 검증이 떨어진다(문지기가 느슨해지지 않았다) ──
        wrong_ok, wrong_why = webhook_contract.verify(
            "not-the-real-secret-at-all", body_bytes, headers)
        self.assertFalse(wrong_ok)
        self.assertEqual(webhook_contract.REJECT_SIGNATURE_MISMATCH, wrong_why)

        # ── 값은 지문(앞 12자)으로만 대조 가능 — 원문은 이 시험 밖으로 안 나간다 ──
        sha12 = hashlib.sha256(secret.encode("utf-8")).hexdigest()[:12]
        self.assertEqual(12, len(sha12))

    def test_a_plain_role_cannot_mint_a_signing_key(self):
        """★ 대조군 — 역할 없는 계정은 여전히 403. 문지기를 느슨하게 하지 않았다."""
        resp = self.client.post(
            "/api/dsm/settings/webhook-subscriptions/issue"
            "?endpoint_url=https://receiver.test.invalid/hook",
            **self._bearer(self.user_a), **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(
            403, resp.status_code,
            (resp.content or b"")[:400].decode("utf-8", "replace"))

    def test_anonymous_gets_401_not_403(self):
        """익명은 인증 자체가 없다 — 401."""
        resp = self.client.post(
            "/api/dsm/settings/webhook-subscriptions/issue"
            "?endpoint_url=https://receiver.test.invalid/hook",
            **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(401, resp.status_code)
