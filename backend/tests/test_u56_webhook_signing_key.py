# -*- coding: utf-8 -*-
"""U6#4 · SEC-16 — 「웹훅 구독을 만들면 서명키가 실리는가」를 HTTP 왕복으로 잰다
(턴 Q · 차선 U56).

무엇을 재는가 — **구독 1 → 서명키 1**
---------------------------------------
`scripts/verify_click_completes.py` 의 U6#4 는
`POST /api/dsm/webhook-subscriptions?...&signing_key_ref=p118-gate&...` 를 두드리고,
그 뒤 목록(U6#12 류)이 비어 있는 것으로 판정됐다. 이 파일은 그 자리를 재현한다.

★ 실측 (2026-09-15 · gx-shell · 개발 DB · `docker exec ... manage.py shell`)
    settings.WEBHOOK_SIGNING_KEYS 의 이름만 읽었다(값은 출력하지 않는다) →
    **키 0개.** 환경변수 `WEBHOOK_SIGNING_KEYS` 가 이 환경에 아예 없다.

`common/webhook_outbox.py::register()` 는 `signing_secret(ref)` 가 빈 문자열이면
`UnknownSigningKey`(422)로 **등록 자체를 거절한다**(같은 파일 202~220행 · D-204).
즉 이 환경에서는 **어떤 이름으로도 구독이 절대 안 만들어진다** — 구독이 0건이니
목록도 0건이고, 그래서 "서명키 목록이 비어 있다"로 보인다.

★ 이 시험이 가르는 것 — **코드 결함인가, 환경 결함인가**
------------------------------------------------------------
`test_s_webhook_outbox.py` 는 이미 `WEBHOOK_SIGNING_KEYS` 를 채운 채로 43개 시험을
통과시킨다(서비스 층). 이 파일은 그 사실을 **API 라우트까지** 넓혀 같은 결론을
Django 시험 클라이언트로 다시 잰다:

    ① `override_settings(WEBHOOK_SIGNING_KEYS={})` — **지금 이 환경과 같은 모양**을
       라우트로 재현한다. 422 가 나와야 하고, 그것은 **제품이 옳게 거절한 것**이다
       (등록은 됐는데 못 보내는 구독을 만들지 않는다).
    ② `override_settings(WEBHOOK_SIGNING_KEYS={...})` — 이름 하나를 채우면 같은 요청이
       200 이 되고, 등록 직후 목록에 그 구독 1건과 `signing_key_ref` 가 그대로 실린다
       (구독 1 → 서명키 1).

②가 통과하므로 **`common/webhook_outbox.py` 자체에는 결함이 없다.** 닫는 조건은
이 환경의 `WEBHOOK_SIGNING_KEYS` 값을 채우는 것 — 저장소 밖(.env.gates·.env)이라
이 차선은 값을 넣지 못한다(§ 공통 규칙 4 `.env*` 금지). **등록 요청**으로 최종 보고에
남긴다.

★ 값은 시험에서도 출력하지 않는다 — 서명키 값은 이 파일이 스스로 짓는 시험용 문자열
  하나뿐이고, assert 는 **이름**(`signing_key_ref`)만 비교한다.
"""
from __future__ import annotations

import json
import uuid

from django.conf import settings
from django.test import Client, override_settings

from tests.no_cache import NO_CACHE
from tests.test_dsm_app import DsmFixture

#: 이 시험만의 서명키 이름 · 값. **값은 assert 에 쓰지 않는다** — 있다/없다만 잰다.
_KEY_NAME = "u56-p141-sec16-test"
_KEY_VALUE = "not-a-real-secret-test-only"


@override_settings(WEBHOOK_ALLOWED_SCHEMES=("https",))
class WebhookSubscriptionSigningKeyDoorTest(DsmFixture):
    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

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

    def _register(self, ref: str):
        return self.client.post(
            "/api/dsm/webhook-subscriptions"
            "?endpoint_url=https://receiver.test.invalid/hook"
            "&signing_key_ref=%s&event_types=fire" % ref,
            **self._bearer(self.user_a), **{"HTTP_X_NO_CACHE": "true"})

    # ── ① 지금 이 환경과 같은 모양 — 서명키 표가 비어 있다 ──────────────────
    @override_settings(WEBHOOK_SIGNING_KEYS={})
    def test_an_empty_signing_key_table_refuses_registration_not_silently(self):
        """★ 재현 — 실측한 이 환경의 모양(키 0개) 그대로. 422 가 **옳은** 결과다."""
        resp = self._register(_KEY_NAME)
        self.assertEqual(
            422, resp.status_code,
            (resp.content or b"")[:400].decode("utf-8", "replace"))
        list_resp = self.client.get(
            "/api/dsm/webhook-subscriptions",
            **self._bearer(self.user_a), **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(200, list_resp.status_code)
        body = json.loads(list_resp.content.decode("utf-8"))
        self.assertEqual(
            0, body["total"],
            "등록이 거절됐는데 구독이 생겼습니다 — 거절과 저장이 따로 놉니다.")

    # ── ② 이름 하나를 채우면 — 구독 1 → 서명키 1 ────────────────────────────
    @override_settings(WEBHOOK_SIGNING_KEYS={_KEY_NAME: _KEY_VALUE})
    def test_one_configured_key_makes_one_subscription_carry_that_key(self):
        """★ 닫는 조건 — 이름이 풀리면 등록은 200 이고, 목록에 그 이름이 그대로 실린다."""
        resp = self._register(_KEY_NAME)
        self.assertEqual(
            200, resp.status_code,
            (resp.content or b"")[:400].decode("utf-8", "replace"))
        body = json.loads(resp.content.decode("utf-8"))
        self.assertEqual(_KEY_NAME, body["signing_key_ref"])
        self.assertNotIn("signing_key_value", body)
        self.assertNotIn(_KEY_VALUE, json.dumps(body),
                         "응답에 서명키 값이 실렸습니다 — SEC-16 이 막으려는 유출입니다.")

        list_resp = self.client.get(
            "/api/dsm/webhook-subscriptions",
            **self._bearer(self.user_a), **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(200, list_resp.status_code)
        list_body = json.loads(list_resp.content.decode("utf-8"))
        self.assertEqual(1, list_body["total"], "구독 1 → 서명키 1 이 아닙니다.")
        self.assertEqual(_KEY_NAME, list_body["subscriptions"][0]["signing_key_ref"])
        self.assertNotIn(_KEY_VALUE, json.dumps(list_body),
                         "목록 응답에 서명키 값이 실렸습니다.")
