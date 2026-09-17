# -*- coding: utf-8 -*-
"""WS-17 「webhook filters」 — 저장·왕복 · 불일치 사건은 발송 0 (턴 T · 차선 U56).

무엇을 잰다
-----------
  ① 저장 → 재조회 왕복: `POST …/{id}/filters` 뒤 `GET …/{id}/filters` 가 같은 모양을 낸다.
  ② 발급 문에 `filters` 를 실으면 행에 그대로 박힌다(`WebhookSubscription.filters`).
  ③ 모르는 키 · JSON 아님 → 400 · 남의 구독 → 404.
  ④ 판정 `subscription_accepts` — 종류·심각도·카메라 불일치는 False · 빈 dict 는 True.
  ⑤ ★ 발송기 실물: 불일치 사건 → `dispatch_event` 발송 **0**.
     ⚠ 그 판정을 발송기(`common/webhook_outbox.py::_passes_filter`)가 부르는 한 줄은 이
       차선 소유 밖이라 **등록 요청**이다. 배선 전엔 이 시험이 빨강이므로 `xfail(strict=True)`
       로 둔다 — 배선이 서면 XPASS 가 실패로 뜨고, 그때 이 표식을 지운다(회색을 초록으로
       안 판다 · 빨강을 조용히 지우지도 않는다).

★ 서명키 값은 assert 밖으로 내지 않는다 — 여기서는 아예 읽지 않는다.
"""
from __future__ import annotations

import json
import uuid
from urllib.parse import urlencode

import pytest
from django.apps import apps
from django.conf import settings
from django.test import Client

from tests.no_cache import NO_CACHE
from tests.test_dsm_app import DsmFixture

ISSUE = "/api/dsm/settings/webhook-subscriptions/issue"


def _filters_url(sub_id) -> str:
    return "/api/dsm/settings/webhook-subscriptions/%s/filters" % sub_id


class _Fake:
    def __init__(self, event_type="fire", severity="critical", cam=None):
        self.event_type = event_type
        self.severity = severity
        self.stream_monitor_id = cam


class WebhookFiltersJudgeTest(DsmFixture):
    """④ 순수 판정 — DB 없이."""

    def test_empty_filters_accept_everything(self):
        from apps.dsm.webhook_key_service import subscription_accepts

        self.assertTrue(subscription_accepts({}, _Fake()))
        self.assertTrue(subscription_accepts(None, _Fake()))

    def test_type_severity_camera_mismatch_each_reject(self):
        from apps.dsm.webhook_key_service import subscription_accepts

        self.assertFalse(subscription_accepts({"type": ["smoke"]}, _Fake(event_type="fire")))
        self.assertFalse(subscription_accepts({"severity": ["info"]}, _Fake(severity="critical")))
        self.assertFalse(subscription_accepts({"camera": ["7"]}, _Fake(cam=8)))
        self.assertTrue(subscription_accepts(
            {"type": ["fire"], "severity": ["critical"], "camera": ["8"]}, _Fake(cam=8)))

    def test_normalize_rejects_unknown_key_and_non_object(self):
        from apps.dsm.webhook_key_service import InvalidWebhookFilters, normalize_filters

        self.assertEqual({"type": ["fire"]}, normalize_filters('{"type": ["fire", " ", "fire"]}'))
        self.assertEqual({}, normalize_filters('{"type": []}'))
        with self.assertRaises(InvalidWebhookFilters):
            normalize_filters('{"zone": ["a"]}')
        with self.assertRaises(InvalidWebhookFilters):
            normalize_filters("[1,2]")
        with self.assertRaises(InvalidWebhookFilters):
            normalize_filters("not json")


class WebhookFiltersRoundTripTest(DsmFixture):
    """①②③ HTTP 실물."""

    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def _admin(self, user, group):
        Role = apps.get_model("role", "Role")
        role, _ = Role.objects.get_or_create(code="admin", defaults={"role_name": "admin"})
        role = self._own(role, group)
        user.roles.add(role)
        user.refresh_from_db()
        return user

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
        return {"HTTP_AUTHORIZATION": "Bearer %s" % access, "HTTP_X_NO_CACHE": "true"}

    def _issue(self, user, **extra):
        q = {"endpoint_url": "https://receiver.test.invalid/hook", **extra}
        resp = self.client.post(ISSUE + "?" + urlencode(q), **self._bearer(user))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        return json.loads(resp.content.decode("utf-8"))

    def test_save_then_read_back_round_trip(self):
        admin = self._admin(self.user_a, self.group_a)
        sub = self._issue(admin)["subscription_id"]

        spec = {"type": ["fire"], "severity": ["critical", "warning"],
                "camera": [str(self.stream_a.pk)]}
        resp = self.client.post(
            _filters_url(sub) + "?" + urlencode({"filters": json.dumps(spec)}),
            **self._bearer(admin))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        saved = json.loads(resp.content.decode("utf-8"))
        self.assertEqual(sorted(spec["severity"]), saved["filters"]["severity"])
        self.assertIn("audit_id", saved)

        back = self.client.get(_filters_url(sub), **self._bearer(admin))
        self.assertEqual(200, back.status_code, back.content[:300])
        got = json.loads(back.content.decode("utf-8"))["filters"]
        self.assertEqual({"type": ["fire"], "severity": ["critical", "warning"],
                          "camera": [str(self.stream_a.pk)]}, got)

        Sub = apps.get_model("stream_monitors", "WebhookSubscription")
        self.assertEqual(got, Sub._base_manager.get(pk=sub).filters)

        # 되돌리기 = 빈 객체
        resp = self.client.post(
            _filters_url(sub) + "?" + urlencode({"filters": "{}"}), **self._bearer(admin))
        self.assertEqual(200, resp.status_code)
        self.assertEqual({}, Sub._base_manager.get(pk=sub).filters)

    def test_issue_carries_filters_into_the_row(self):
        admin = self._admin(self.user_a, self.group_a)
        body = self._issue(admin, filters=json.dumps({"type": ["smoke"]}))
        self.assertEqual({"type": ["smoke"]}, body["filters"])
        Sub = apps.get_model("stream_monitors", "WebhookSubscription")
        self.assertEqual({"type": ["smoke"]},
                         Sub._base_manager.get(pk=body["subscription_id"]).filters)

    def test_bad_filters_400_and_foreign_subscription_404(self):
        admin = self._admin(self.user_a, self.group_a)
        sub = self._issue(admin)["subscription_id"]
        resp = self.client.post(
            _filters_url(sub) + "?" + urlencode({"filters": json.dumps({"zone": ["x"]})}),
            **self._bearer(admin))
        self.assertEqual(400, resp.status_code, resp.content[:300])

        other = self._admin(self.user_b, self.group_b)
        resp = self.client.post(
            _filters_url(sub) + "?" + urlencode({"filters": "{}"}), **self._bearer(other))
        self.assertEqual(404, resp.status_code, resp.content[:300])
        resp = self.client.get(_filters_url(sub), **self._bearer(other))
        self.assertEqual(404, resp.status_code, resp.content[:300])


class WebhookFiltersDispatchTest(DsmFixture):
    """⑤ 발송기 실물 — 불일치 사건은 발송 0."""

    def _subscribe_with_filters(self, spec):
        from apps.dsm.webhook_key_service import issue_webhook_subscription
        from common.tenant_scope import TenantScope

        Role = apps.get_model("role", "Role")
        role, _ = Role.objects.get_or_create(code="admin", defaults={"role_name": "admin"})
        self._own(role, self.group_a)
        self.user_a.roles.add(role)
        self.user_a.refresh_from_db()
        scope = TenantScope.of(self.user_a)
        body = issue_webhook_subscription(
            scope=scope, endpoint_url="https://receiver.test.invalid/hook",
            filters=spec)
        return scope, body["subscription_id"]

    def _dispatch(self, scope, event_id):
        from common import webhook_outbox

        calls = []

        def sender(url, body, headers):
            calls.append(url)
            return 200, ""

        webhook_outbox.dispatch_event(scope=scope, event_id=event_id,
                                      sender=sender, sleeper=lambda s: None)
        return calls

    def test_matching_event_is_sent(self):
        scope, _ = self._subscribe_with_filters({"type": ["fire"]})
        calls = self._dispatch(scope, self._event(self.stream_a, event_type="fire"))
        self.assertEqual(1, len(calls))

    # (턴 T 병합) `xfail(strict)` 표식을 뗐다 — `webhook_outbox._passes_filter` 가 이제 부른다.
    def test_mismatching_event_is_not_sent(self):
        scope, _ = self._subscribe_with_filters({"type": ["smoke"]})
        calls = self._dispatch(scope, self._event(self.stream_a, event_type="fire"))
        self.assertEqual(0, len(calls), "필터 불일치 사건이 나갔다 — 발송 0 이어야 한다")
