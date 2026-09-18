# -*- coding: utf-8 -*-
"""CH-03 웹푸시 구독 · M4 내 알림 설정 (2026-09-16 · 턴 S · 차선 U3).

캐시 처리: 우회 — 구독·설정은 저장 직후 다시 읽는 시험이라 응답 캐시가 적중하면
방금 저장한 값이 가려진다(D-341). `tests.no_cache.NO_CACHE` 로 우회한다.

무엇을 재는가 — 여섯
--------------------
    ① **익명은 401**            구독은 계정이 건다. 무계정 링크 금지의 집행이다.
    ② **자격이 응답에 안 실린다**  푸시 엔드포인트는 그 기기로 알림을 밀어 넣는 주소다.
       나가는 것은 지문 12자와 기기 이름뿐 — 엔드포인트·p256dh·auth 는 **한 글자도**
       나가면 안 된다. 이 시험은 응답을 통째로 직렬화해 그 값들을 **찾아본다.**
    ③ **남의 기기는 안 보이고 못 끈다**  구독은 기관의 것이 아니라 한 사람의 한 기기다.
       같은 기관 동료의 구독이 보이면 그것도 누출이고, 끌 수 있으면 그 사람의 경보가
       조용히 멈춘다(P-8 쓰기 방향).
    ④ **시험 발송이 발송 이력을 오염시키지 않는다**  `DeliveryRecord` 행이 늘면
       F-10 지연 통계가 경보 아닌 것을 세고 5분 억제가 다음 진짜 경보를 삼킨다.
    ⑤ **못 보내면 못 보낸다고 말한다**  이 환경에는 발송기(`pywebpush`)도 VAPID 키도
       없다 [실측 2026-09-16]. 그 상태의 `ok=True` 가 「조용한 성공」이다(D-284).
    ⑥ **[P-166 · D-486] 구독 비밀은 본문으로만 — 쿼리에 있으면 본문이 옳아도 400**
       턴 T 실측: `endpoint`·`p256dh`·`auth_secret` 이 쿼리 문자열로 갔고 그 줄이
       접근 로그에 남았다. 이 시험은 ⓐ 본문(JSON `PushSubscriptionIn`)만으로 등록이
       되는가 ⓑ 같은 이름이 쿼리에 실리면(본문이 맞아도) 400 이고 아무것도 저장되지
       않는가를 잰다.

★ 값은 시험에도 적지 않는다 — 여기 쓰는 엔드포인트·키는 전부 `*.invalid` 의
  **가짜**이고, 진짜 자격은 이 저장소 어디에도 없다(D-204).
"""
from __future__ import annotations

import contextlib
import json
from unittest import mock

from django.apps import apps
from django.test import Client, RequestFactory, TestCase

from common.tenant_scope import TenantScope

#: 가짜 구독 한 벌. `.invalid` 는 절대 존재하지 않는 TLD 다(RFC 2606) — 실수로
#: 진짜 발송이 시도돼도 갈 곳이 없다.
FAKE_ENDPOINT = "https://push.invalid/send/u3-turn-s-fake-endpoint"
FAKE_P256DH = "BFakeP256dhKeyForTestsOnly_not_a_real_key"
FAKE_AUTH = "FakeAuthSecretForTests"


class _PushFixture(TestCase):
    """테넌트 A/B · 사람 둘. 구독은 **사람**의 것이므로 사람이 둘 필요하다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        UserGroup = apps.get_model("user", "UserGroup")
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="push-tenant-A")
        cls.group_b = UserGroup.objects.create(name="push-tenant-B")
        UserGroup.objects.filter(
            pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.user_a = cls._user("push_user_a", cls.group_a)
        #: ★ **같은 기관**의 동료다 — 테넌트가 갈라 주지 않는 자리를 재려면 그래야 한다.
        cls.user_a2 = cls._user("push_user_a2", cls.group_a)
        cls.user_b = cls._user("push_user_b", cls.group_b)

    @classmethod
    def _user(cls, username, group):
        CoreUser = apps.get_model("user", "CoreUser")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": group})
        return user

    def tearDown(self) -> None:
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().tearDown()

    # ── 라우트를 직접 부른다(관문 하나만 스택을 탄다 — 캐시가 판정을 덮지 않게) ──
    def _req(self, user, method="post"):
        factory = RequestFactory()
        request = getattr(factory, method)("/api/dsm/push-subscriptions")
        request.user = user
        return request

    def _subscribe(self, user, *, endpoint=FAKE_ENDPOINT, p256dh=FAKE_P256DH,
                   auth_secret=FAKE_AUTH, label="시험용 휴대전화", query=""):
        """[P-166] 비밀은 **본문**으로만 조립한다. `query` 는 쿼리 문자열에 얹을 덩어리
        (예: `"endpoint=x"`) — 비밀이 거기 실리면 본문이 옳아도 거절돼야 한다(⑥)."""
        from apps.dsm.api_u3 import DsmU3API, PushSubscriptionIn

        path = "/api/dsm/push-subscriptions"
        if query:
            path = f"{path}?{query}"
        request = RequestFactory().post(path)
        request.user = user
        payload = PushSubscriptionIn(
            endpoint=endpoint, p256dh=p256dh, auth_secret=auth_secret, label=label)
        return DsmU3API.create_push_subscription(DsmU3API(), request, payload)

    def _list(self, user):
        from apps.dsm.api_u3 import DsmU3API

        return DsmU3API.list_push_subscriptions(DsmU3API(), self._req(user, "get"))

    def _unsubscribe(self, user, subscription_id):
        from apps.dsm.api_u3 import DsmU3API

        return DsmU3API.delete_push_subscription(
            DsmU3API(), self._req(user, "delete"), subscription_id)


class PushSubscriptionRouteTest(_PushFixture):

    # ── ① 익명은 401 ─────────────────────────────────────────────────────
    def test_rule1_anonymous_cannot_subscribe(self) -> None:
        from tests.no_cache import NO_CACHE

        client = Client(raise_request_exception=False)
        resp = client.post(
            "/api/dsm/push-subscriptions"
            f"?endpoint={FAKE_ENDPOINT}&p256dh={FAKE_P256DH}&auth_secret={FAKE_AUTH}",
            **NO_CACHE)
        self.assertEqual(401, resp.status_code)

    # ── ② 자격이 응답에 안 실린다 ─────────────────────────────────────────
    def test_rule2_the_credential_never_leaves_the_server(self) -> None:
        saved = self._subscribe(self.user_a)
        listed = self._list(self.user_a)

        blob = json.dumps([saved, listed], default=str)
        for secret in (FAKE_ENDPOINT, FAKE_P256DH, FAKE_AUTH):
            self.assertNotIn(
                secret, blob,
                "구독 자격이 응답에 실렸습니다 — 푸시 엔드포인트는 그 기기로 알림을 "
                "밀어 넣는 주소이고, 한 번 새면 회수할 수 없습니다.")
        self.assertEqual(12, len(saved["endpoint_sha12"]))
        self.assertEqual("시험용 휴대전화", saved["label"])

    # ── ③ 남의 기기는 안 보이고 못 끈다 ───────────────────────────────────
    def test_rule3_a_colleague_in_the_same_tenant_sees_nothing_of_mine(self) -> None:
        self._subscribe(self.user_a)
        self.assertEqual(1, self._list(self.user_a)["total"])
        self.assertEqual(
            0, self._list(self.user_a2)["total"],
            "같은 기관 동료의 화면에 내 휴대전화 구독이 보입니다 — 테넌트가 갈라 "
            "주지 않는 자리이고, 그래서 함수가 갈라야 합니다.")
        self.assertEqual(0, self._list(self.user_b)["total"])

    def test_rule3_another_user_cannot_turn_my_device_off(self) -> None:
        from ninja.errors import HttpError

        saved = self._subscribe(self.user_a)
        for other in (self.user_a2, self.user_b):
            with self.subTest(user=other.username):
                with self.assertRaises(HttpError) as caught:
                    self._unsubscribe(other, saved["subscription_id"])
                #: 404 다 — 403 을 내면 「그 번호는 있는데 네 것이 아니다」가 샌다.
                self.assertEqual(404, caught.exception.status_code)
        self.assertEqual(1, self._list(self.user_a)["total"],
                         "남이 껐는데 내 구독이 사라졌습니다.")

    def test_unsubscribing_keeps_the_audit_line_and_empties_the_list(self) -> None:
        """**행을 지우지 않는다** — 언제 무엇을 받았는지가 함께 사라진다."""
        from apps.dsm import notify_prefs

        AuditLogs = apps.get_model("logger", "AuditLogs")
        saved = self._subscribe(self.user_a)
        before = AuditLogs._base_manager.filter(
            logger_name=notify_prefs.LOGGER_NAME).count()

        self._unsubscribe(self.user_a, saved["subscription_id"])

        self.assertEqual(0, self._list(self.user_a)["total"])
        self.assertEqual(
            before + 1,
            AuditLogs._base_manager.filter(
                logger_name=notify_prefs.LOGGER_NAME).count(),
            "해지가 감사 한 줄을 남기지 않았습니다 — 그러면 「그 밤에 왜 안 왔나」에 "
            "답할 수 없습니다.")

    def test_a_plaintext_or_keyless_subscription_is_refused(self) -> None:
        from ninja.errors import HttpError

        for label, kwargs in (
            ("평문 http", {"endpoint": "http://push.invalid/send/x"}),
            ("키 없음", {"p256dh": "", "auth_secret": ""}),
        ):
            with self.subTest(case=label):
                with self.assertRaises(HttpError) as caught:
                    self._subscribe(self.user_a, **kwargs)
                self.assertEqual(422, caught.exception.status_code)
        self.assertEqual(0, self._list(self.user_a)["total"])

    def test_resubscribing_the_same_device_does_not_double_count_it(self) -> None:
        """브라우저가 구독을 갱신하면 키만 바뀐다 — 사람은 같은 기기라고 생각한다."""
        self._subscribe(self.user_a)
        self._subscribe(self.user_a, p256dh=FAKE_P256DH + "2")
        self.assertEqual(1, self._list(self.user_a)["total"])


class PushSubscriptionSecretsGoOnlyInTheBodyTest(_PushFixture):
    """⑥ [P-166 · D-486] 본문은 옳게 · 쿼리에 비밀 이름이 있으면 **본문이 옳아도 400**."""

    # ── ⓐ 본문(JSON Schema)만으로 등록이 된다 ───────────────────────────────
    def test_a_body_only_request_succeeds(self) -> None:
        saved = self._subscribe(self.user_a)
        self.assertEqual(12, len(saved["endpoint_sha12"]))
        self.assertEqual(1, self._list(self.user_a)["total"])

    # ── ⓑ 쿼리에 비밀 이름이 하나라도 있으면 — 본문이 옳아도 400 · 저장 0 ──────
    def test_each_secret_name_in_the_query_string_is_refused_alone(self) -> None:
        from ninja.errors import HttpError

        for name in ("endpoint", "p256dh", "auth_secret", "auth"):
            with self.subTest(query_name=name):
                with self.assertRaises(HttpError) as caught:
                    self._subscribe(self.user_a, query=f"{name}=whatever")
                self.assertEqual(400, caught.exception.status_code)
        self.assertEqual(
            0, self._list(self.user_a)["total"],
            "쿼리에 비밀 이름이 있었는데도 구독이 저장됐습니다 — 본문이 옳았다는 "
            "이유로 거절을 건너뛰면 안 됩니다.")

    def test_all_three_secrets_in_the_query_together_are_refused(self) -> None:
        from ninja.errors import HttpError

        with self.assertRaises(HttpError) as caught:
            self._subscribe(
                self.user_a,
                query=f"endpoint={FAKE_ENDPOINT}&p256dh={FAKE_P256DH}"
                      f"&auth_secret={FAKE_AUTH}")
        self.assertEqual(400, caught.exception.status_code)
        blob = str(caught.exception)
        for secret in (FAKE_ENDPOINT, FAKE_P256DH, FAKE_AUTH):
            self.assertNotIn(
                secret, blob,
                "거절 사유 문장에 비밀 값이 그대로 인용됐습니다 — 이름만 적어야 합니다.")

    def test_a_harmless_query_string_does_not_block_the_body(self) -> None:
        """비밀이 아닌 쿼리(예: 캐시 우회 표식)는 걸리지 않는다 — 이름만 가린다."""
        saved = self._subscribe(self.user_a, query="ignored=1")
        self.assertEqual(12, len(saved["endpoint_sha12"]))

    # ── 실물 HTTP 왕복 — ninja 라우팅을 실제로 태운다 ──────────────────────
    def _give_role(self, user, group):
        """이 사람에게 역할 하나를 준다 — `role_gate`(P-105)가 「역할 0」으로 403 을
        내지 않게(`tests/test_dsm_app.py::DsmFixture._own`·`_role` 과 같은 조립).
        이 비밀-쿼리 시험 둘만 실물 HTTP 를 태우고, 나머지는 함수를 직접 부르므로
        미들웨어를 안 지나 이 역할이 없어도 됐다."""
        from kernels.k1_event.services import _owner_field

        Role = apps.get_model("role", "Role")
        role = Role.objects.create(
            role_name=f"push-test-role-{user.pk}", code=f"push_test_{user.pk}")
        if _owner_field(type(role)) == "groups":
            role.groups.set([group])
        else:
            role.group = group
            role.save(update_fields=["group"])
        user.roles.add(role)
        user.refresh_from_db()
        return user

    def _bearer(self, user) -> dict:
        import uuid

        import jwt as pyjwt
        from django.conf import settings
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

    def test_real_http_json_body_reaches_200_and_carries_no_secret_back(self) -> None:
        """ninja 라우팅을 실제로 태운다 — `PushSubscriptionIn` 이 진짜 본문 파서를 탄다."""
        self._give_role(self.user_a, self.group_a)
        client = Client(raise_request_exception=False)
        body = json.dumps({
            "endpoint": FAKE_ENDPOINT, "p256dh": FAKE_P256DH,
            "auth_secret": FAKE_AUTH, "label": "실물 HTTP 시험"})
        resp = client.post(
            "/api/dsm/push-subscriptions", data=body,
            content_type="application/json", **self._bearer(self.user_a))
        self.assertIn(resp.status_code, (200, 201), resp.content[:300])
        blob = resp.content.decode("utf-8")
        for secret in (FAKE_ENDPOINT, FAKE_P256DH, FAKE_AUTH):
            self.assertNotIn(secret, blob)

    def test_real_http_query_secrets_are_400_even_with_a_correct_body(self) -> None:
        self._give_role(self.user_a, self.group_a)
        client = Client(raise_request_exception=False)
        body = json.dumps({
            "endpoint": FAKE_ENDPOINT, "p256dh": FAKE_P256DH,
            "auth_secret": FAKE_AUTH, "label": "실물 HTTP 쿼리 시험"})
        resp = client.post(
            "/api/dsm/push-subscriptions?endpoint=%s&p256dh=%s&auth_secret=%s" % (
                FAKE_ENDPOINT, FAKE_P256DH, FAKE_AUTH),
            data=body, content_type="application/json", **self._bearer(self.user_a))
        self.assertEqual(400, resp.status_code, resp.content[:300])


class VapidStatusTest(_PushFixture):
    """VAPID — **이름만 있고 값은 환경에만 있다.**"""

    def test_absent_credentials_are_declared_not_silently_missing(self) -> None:
        from apps.dsm import notify_prefs

        with mock.patch.dict("os.environ", {}, clear=False) as _env:
            for name in (notify_prefs.VAPID_PUBLIC_ENV,
                         notify_prefs.VAPID_PRIVATE_ENV,
                         notify_prefs.VAPID_SUBJECT_ENV):
                _env.pop(name, None)
            status = notify_prefs.vapid_status()

        self.assertFalse(status["configured"])
        self.assertEqual(3, len(status["missing_env"]))
        self.assertTrue(status["reason"], "없음을 사유 없이 적었습니다 — 회색입니다.")

    def test_the_status_carries_no_key_values_at_all(self) -> None:
        """★ [조율자 지시 · 턴 S] 상태는 **있다/없다 · 이름 · sha256 앞 12자**까지다.

        공개키 값조차 여기 실리지 않는다 — 「상태를 물었을 뿐인데 값이 따라 나오는」
        자리가 로그·증거·캡처에 값을 흘린다.
        """
        from apps.dsm import notify_prefs

        secret = "private-key-value-that-must-not-appear"
        public = "public-key-value-that-belongs-only-in-the-route"
        with mock.patch.dict("os.environ", {
                notify_prefs.VAPID_PUBLIC_ENV: public,
                notify_prefs.VAPID_PRIVATE_ENV: secret,
                notify_prefs.VAPID_SUBJECT_ENV: "mailto:ops@example.invalid"}):
            status = notify_prefs.vapid_status()

        self.assertTrue(status["configured"])
        blob = json.dumps(status)
        self.assertNotIn(secret, blob, "비밀키 값이 상태에 실렸습니다.")
        self.assertNotIn(public, blob, "공개키 **값**이 상태에 실렸습니다 — 상태는 지문까지입니다.")
        self.assertEqual(12, len(status["public_key_sha12"]))

    def test_only_the_route_carries_the_public_key_value(self) -> None:
        """★ 그 값이 나가는 자리는 **하나**다 — 브라우저의 `applicationServerKey`."""
        from apps.dsm import notify_prefs
        from apps.dsm.api_u3 import DsmU3API

        public = "public-key-value-for-the-browser"
        request = RequestFactory().get("/api/dsm/push-subscriptions/vapid-key")
        request.user = self.user_a
        with mock.patch.dict("os.environ", {
                notify_prefs.VAPID_PUBLIC_ENV: public,
                notify_prefs.VAPID_PRIVATE_ENV: "private-value",
                notify_prefs.VAPID_SUBJECT_ENV: "mailto:ops@example.invalid"}):
            payload = DsmU3API.push_vapid_key(DsmU3API(), request)

        self.assertEqual(public, payload["public_key"])
        self.assertNotIn("private-value", json.dumps(payload),
                         "비밀키 값이 라우트 응답에 실렸습니다.")


class WebPushChannelTest(TestCase):
    """발송 어댑터 — **못 보내면 못 보낸다고 말한다.**"""

    def test_the_channel_is_registered_by_name(self) -> None:
        from kernels.k2_notify import channels

        self.assertIsNotNone(
            channels.get("webpush"),
            "웹푸시 어댑터가 등록되지 않았습니다 — 여기 없는 채널은 없는 채널입니다.")

    def test_a_subscription_it_cannot_read_is_a_stated_failure(self) -> None:
        from kernels.k2_notify.channels import WebPushChannel

        outcome = WebPushChannel().send(
            address="엔드포인트만 있고 키가 없다", subject="제목", body="본문")
        self.assertFalse(outcome.ok)
        self.assertTrue(outcome.reason)

    def test_it_never_reports_success_without_a_sender_and_credentials(self) -> None:
        """★ 이 환경에는 발송기도 자격도 없다 [실측] — 그 상태의 `ok=True` 가 거짓 초록이다."""
        from kernels.k2_notify.channels import WebPushChannel

        ready = WebPushChannel.configured()
        if ready.ok:
            self.skipTest("이 환경에는 발송기와 VAPID 자격이 모두 있다 — 이 시험의 전제가 아니다.")
        self.assertTrue(ready.reason, "못 보내는 사유가 비었습니다 — 회색은 초록이 아닙니다.")

        outcome = WebPushChannel().send(
            address=json.dumps({"endpoint": FAKE_ENDPOINT,
                                "keys": {"p256dh": FAKE_P256DH, "auth": FAKE_AUTH}}),
            subject="[훈련] 시험", body="이 알림은 시험입니다")
        self.assertFalse(
            outcome.ok,
            "발송기도 자격도 없는데 「보냈다」고 답했습니다 — 아무에게도 안 간 알림이 "
            "간 것으로 집계됩니다(D-284 조용한 성공).")

    def test_the_failure_reason_does_not_echo_the_credential(self) -> None:
        from kernels.k2_notify.channels import WebPushChannel

        outcome = WebPushChannel().send(
            address=json.dumps({"endpoint": FAKE_ENDPOINT,
                                "keys": {"p256dh": FAKE_P256DH, "auth": FAKE_AUTH}}),
            subject="제목", body="본문")
        self.assertNotIn(FAKE_ENDPOINT, outcome.reason)
        self.assertNotIn(FAKE_AUTH, outcome.reason)


class PushTestSendTest(_PushFixture):
    """④ 시험 발송은 **경보가 아니다.**"""

    def _send(self, user):
        from apps.dsm.api_u3 import DsmU3API

        return DsmU3API.push_test_send(DsmU3API(), self._req(user))

    def test_without_a_device_it_says_so_instead_of_succeeding_emptily(self) -> None:
        from ninja.errors import HttpError

        with self.assertRaises(HttpError) as caught:
            self._send(self.user_a)
        self.assertEqual(422, caught.exception.status_code)

    def test_without_vapid_env_it_is_503_and_no_row(self) -> None:
        """④' [턴 T] 문이 열렸다 — 행은 **훈련 표식**으로 남고(`tests/test_u3_webpush_send.py`),
        자격이 없는 환경에서는 **행 0 · 503 · 이름 목록**이다."""
        import os
        from ninja.errors import HttpError

        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        self._subscribe(self.user_a)
        before = Delivery._base_manager.count()
        empty = {"GX_VAPID_PUBLIC_KEY": "", "GX_VAPID_PRIVATE_KEY": "", "GX_VAPID_SUBJECT": ""}
        with mock.patch.dict(os.environ, empty):
            with self.assertRaises(HttpError) as caught:
                self._send(self.user_a)
        self.assertEqual(503, caught.exception.status_code)
        self.assertIn("missing_env=", str(caught.exception))
        self.assertEqual(before, Delivery._base_manager.count())

    def test_the_body_says_it_is_a_drill(self) -> None:
        """★ 잠금화면에 이 글자가 뜬다 — 없으면 시험 한 번이 출동 한 번이 된다."""
        from apps.dsm import notify_prefs

        self.assertIn("훈련", notify_prefs.DRILL_TITLE)
        #: 사람이 제목을 줘도 `[훈련]` 이 앞에 붙는다 — 실제 발송 시험은 `test_u3_webpush_send.py`.


class NotifyPrefsRouteTest(_PushFixture):
    """M4 「내 알림 설정」 — 골격 (WS-02)."""

    def _get(self, user):
        from apps.dsm.api_u3 import DsmU3API

        return DsmU3API.get_notify_prefs(DsmU3API(), self._req(user, "get"))

    def _put(self, user, **kwargs):
        from apps.dsm.api_u3 import DsmU3API

        request = RequestFactory().put("/api/dsm/me/notify-prefs")
        request.user = user
        return DsmU3API.put_notify_prefs(DsmU3API(), request, **kwargs)

    def test_an_unset_preference_is_empty_not_missing(self) -> None:
        view = self._get(self.user_a)
        self.assertFalse(view["saved"])
        self.assertEqual("", view["quiet_start"])
        self.assertEqual([], view["channels"])
        self.assertIn("좁히", view["note"])

    def test_saving_a_quiet_window_reads_back(self) -> None:
        saved = self._put(self.user_a, quiet_start="22:00", quiet_end="07:00",
                          channels="webpush,email", zone_ids="3,4")
        self.assertTrue(saved["saved"])
        self.assertEqual("22:00", saved["quiet_start"])
        self.assertEqual("07:00", saved["quiet_end"])
        self.assertEqual(["webpush", "email"], saved["channels"])
        self.assertEqual([3, 4], saved["zone_ids"])
        self.assertEqual(saved["quiet_start"], self._get(self.user_a)["quiet_start"])

    def test_half_a_quiet_window_is_refused_in_words_not_by_the_database(self) -> None:
        from ninja.errors import HttpError

        with self.assertRaises(HttpError) as caught:
            self._put(self.user_a, quiet_start="22:00")
        self.assertEqual(422, caught.exception.status_code)
        self.assertIn("함께", str(caught.exception))

    def test_an_unknown_channel_is_refused(self) -> None:
        from ninja.errors import HttpError

        with self.assertRaises(HttpError) as caught:
            self._put(self.user_a, channels="carrier-pigeon")
        self.assertEqual(422, caught.exception.status_code)

    def test_saving_twice_keeps_exactly_one_live_row(self) -> None:
        Prefs = apps.get_model("stream_monitors", "DsmNotifyPrefs")
        self._put(self.user_a, channels="email")
        self._put(self.user_a, channels="webpush")
        self.assertEqual(
            1,
            Prefs._base_manager.filter(user_id=self.user_a.pk,
                                       deleted__isnull=True).count(),
            "살아 있는 설정이 둘이면 어느 쪽이 이기는지 아무도 모릅니다.")
        self.assertEqual(["webpush"], self._get(self.user_a)["channels"])

    def test_one_persons_settings_are_not_anothers(self) -> None:
        self._put(self.user_a, quiet_start="22:00", quiet_end="07:00")
        self.assertEqual("", self._get(self.user_a2)["quiet_start"],
                         "남의 근무 외 시간이 내 설정으로 보입니다.")

    def test_the_row_carries_its_purpose_code(self) -> None:
        """ISO-03 — 이 행이 **무슨 목적으로** 생겼는가(설계서 §3 ③)."""
        from apps.dsm import notify_prefs

        Prefs = apps.get_model("stream_monitors", "DsmNotifyPrefs")
        self._put(self.user_a, channels="email")
        row = Prefs._base_manager.filter(user_id=self.user_a.pk).first()
        self.assertEqual(notify_prefs.PURPOSE_CODE, row.purpose_code)
        self.assertEqual(self.group_a.pk, row.group_id)
