# -*- coding: utf-8 -*-
"""P-160 ③ 웹푸시 발송 문 — **끝까지 서는가** (2026-09-17 · 턴 T · 차선 U3).

캐시 처리: 우회 — 라우트 함수를 직접 부른다(응답 캐시가 판정을 덮지 않게 · D-341).

무엇을 재는가
-------------
    ① `POST /api/dsm/push-subscriptions/test-send` 가 커널 `send_webpush` 를 타고
       `deliveries` 행 `channel=webpush` 를 남긴다 — 성공 1(`succeeded=true`) ·
       실패 1(`WebPushException` → `failure_reason` 에 예외 **이름**).
    ② VAPID 환경이 비면 **503** + `missing_env=` 이름 목록 · 행 0.
    ③ 훈련 표식 행은 5분 억제의 근거가 아니다.
    ④ 규칙 경로: 사건 → 규칙(`webpush`) → 구독자 → 행 `channel=webpush`.
    ⑤ **차단 시간대 안이면 발송 0** — 행은 `failure_reason=quiet_hours` 로 남는다.
    ⑥ 커널과 App 이 읽는 감사 행 상수가 같다(두 벌이 갈리면 구독이 커널에 안 보인다).

★ 값은 시험에도 적지 않는다 — 환경변수에 넣는 것은 `fake-…` 글자다. `pywebpush.webpush`
  는 **mock** 이다 — 이 시험은 외부로 한 바이트도 보내지 않는다.
"""
from __future__ import annotations

import contextlib
import os
from datetime import timedelta
from unittest import mock

from django.apps import apps
from django.test import RequestFactory, TestCase
from django.utils import timezone

from common.tenant_scope import TenantScope

FAKE_ENDPOINT = "https://push.invalid/send/u3-turn-t-fake-endpoint"
FAKE_P256DH = "BFakeP256dhKeyForTestsOnly_not_a_real_key"
FAKE_AUTH = "FakeAuthSecretForTests"

#: 이름은 실제 이름(어댑터가 읽는 그 이름) · 값은 **가짜 글자**다.
FAKE_ENV = {
    "GX_VAPID_PUBLIC_KEY": "fake-public-for-tests",
    "GX_VAPID_PRIVATE_KEY": "fake-private-for-tests",
    "GX_VAPID_SUBJECT": "mailto:test@test.invalid",
}
EMPTY_ENV = {k: "" for k in FAKE_ENV}


class _Fixture(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        UserGroup = apps.get_model("user", "UserGroup")
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        cls.group = UserGroup.objects.create(name="webpush-tenant")
        UserGroup.objects.filter(pk=cls.group.pk).update(created_by=None)
        cls.user = cls._user("webpush_user", cls.group)
        cls.stream = cls._stream("webpush-cam", cls.group)

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

    @classmethod
    def _own(cls, row, group):
        if hasattr(row, "group_id"):
            row.group = group
            row.save(update_fields=["group"])
        elif hasattr(row, "groups"):
            row.groups.add(group)
        return row

    @classmethod
    def _stream(cls, name, group):
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        sm = StreamMonitor.objects.create(name=name, code=name,
                                          ip_source="rtsp://test.invalid/x")
        return cls._own(sm, group)

    def _event(self, *, minutes_ago=30, event_type="fire"):
        from kernels.k1_event import record_detection

        return record_detection(
            scope=TenantScope.system(reason="시험 씨앗"),
            stream_monitor_id=self.stream.pk, event_type=event_type,
            severity="critical",
            occurred_at=timezone.now() - timedelta(minutes=minutes_ago),
            snapshot_path="").event_id

    def _req(self, method="post"):
        request = getattr(RequestFactory(), method)("/api/dsm/push-subscriptions")
        request.user = self.user
        return request

    def _subscribe(self):
        """[P-166] 비밀은 본문(`PushSubscriptionIn`)으로만 조립한다 — 쿼리 인자가 아니다."""
        from apps.dsm.api_u3 import DsmU3API, PushSubscriptionIn

        payload = PushSubscriptionIn(
            endpoint=FAKE_ENDPOINT, p256dh=FAKE_P256DH, auth_secret=FAKE_AUTH,
            label="시험용 휴대전화")
        return DsmU3API.create_push_subscription(DsmU3API(), self._req(), payload)

    def _test_send(self, **kwargs):
        from apps.dsm.api_u3 import DsmU3API

        return DsmU3API.push_test_send(DsmU3API(), self._req(), **kwargs)

    def tearDown(self) -> None:
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().tearDown()


class TestSendRouteTest(_Fixture):
    """① ② ③"""

    def test_success_leaves_a_webpush_row_with_succeeded_true(self) -> None:
        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        self._subscribe()
        event_id = self._event()
        with mock.patch.dict(os.environ, FAKE_ENV), \
                mock.patch("pywebpush.webpush", return_value=None) as sender:
            result = self._test_send()
        self.assertEqual(1, sender.call_count, "발송기가 한 번 불려야 합니다.")
        row = Delivery._base_manager.get(pk=result["delivery_id"])
        self.assertEqual("webpush", row.channel)
        self.assertTrue(row.succeeded)
        self.assertTrue(result["succeeded"])
        self.assertIsNone(result["failure_reason"])
        self.assertEqual(event_id, row.event_id)
        self.assertIsNotNone(row.sent_at)
        self.assertTrue(row.recipient_address.startswith("drill:webpush:"))
        #: 행 어디에도 엔드포인트·키가 없다.
        self.assertNotIn(FAKE_ENDPOINT, row.recipient_address)
        self.assertNotIn(FAKE_P256DH, str(row.failure_reason))
        self.assertTrue(result["title"].startswith("[훈련]"))
        #: 발송기에 실제 값이 갔는가 — 값은 여기 가짜다. 이름을 대조한다.
        kwargs = sender.call_args.kwargs
        self.assertEqual(FAKE_ENDPOINT, kwargs["subscription_info"]["endpoint"])

    def test_failure_leaves_a_row_with_the_exception_name(self) -> None:
        from pywebpush import WebPushException

        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        self._subscribe()
        self._event()
        with mock.patch.dict(os.environ, FAKE_ENV), \
                mock.patch("pywebpush.webpush",
                           side_effect=WebPushException("Push failed: 410 Gone")):
            result = self._test_send()
        row = Delivery._base_manager.get(pk=result["delivery_id"])
        self.assertEqual("webpush", row.channel)
        self.assertFalse(row.succeeded)
        self.assertIsNone(row.sent_at)
        self.assertIn("WebPushException", row.failure_reason)
        self.assertEqual(row.failure_reason, result["failure_reason"])
        self.assertEqual(0, result["sent"])
        self.assertEqual(1, result["devices"])

    def test_missing_vapid_env_is_503_with_names_and_no_row(self) -> None:
        from ninja.errors import HttpError

        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        self._subscribe()
        self._event()
        before = Delivery._base_manager.count()
        with mock.patch.dict(os.environ, EMPTY_ENV), \
                mock.patch("pywebpush.webpush") as sender:
            with self.assertRaises(HttpError) as caught:
                self._test_send()
        self.assertEqual(503, caught.exception.status_code)
        message = str(caught.exception)
        self.assertIn("missing_env=", message)
        for name in FAKE_ENV:
            self.assertIn(name, message)
        self.assertEqual(0, sender.call_count)
        self.assertEqual(before, Delivery._base_manager.count(), "자격 없는 발송이 행을 남겼습니다.")

    def test_no_event_in_tenant_is_409(self) -> None:
        from ninja.errors import HttpError

        self._subscribe()
        with mock.patch.dict(os.environ, FAKE_ENV):
            with self.assertRaises(HttpError) as caught:
                self._test_send()
        self.assertEqual(409, caught.exception.status_code)

    def test_a_drill_row_does_not_suppress_the_next_real_alert(self) -> None:
        """③ 시험 한 통이 다음 진짜 경보를 삼키지 않는다."""
        from kernels.k2_notify import suppress

        self._subscribe()
        first = self._event(minutes_ago=3)
        with mock.patch.dict(os.environ, FAKE_ENV), mock.patch("pywebpush.webpush"):
            self._test_send(event_id=first)
        later = self._event(minutes_ago=1)
        scope = TenantScope.of(self.user)
        self.assertFalse(suppress(scope=scope, event_id=later),
                         "훈련 표식 행이 5분 억제의 근거가 됐습니다.")


class RulePathTest(_Fixture):
    """④ ⑤ — 사건 → 규칙(`webpush`) → 구독자 → 행."""

    def _rule(self):
        Rule = apps.get_model("stream_monitors", "NotificationRule")
        Role = apps.get_model("role", "Role")
        role = Role.objects.filter(code="webpush_field").first()
        if role is None:
            role = self._own(Role.objects.create(role_name="webpush_field", code="webpush_field"),
                             self.group)
        self.user.roles.add(role)
        rule = Rule.objects.create(severity="critical", role=role, zone=None,
                                   channels=["webpush"], is_active=True)
        return self._own(rule, self.group)

    def _prefs(self, **kwargs):
        from apps.dsm import notify_prefs

        return notify_prefs.save_notify_prefs(scope=TenantScope.of(self.user), **kwargs)

    def test_rule_delivers_to_the_subscriber_as_webpush(self) -> None:
        from kernels.k2_notify import send

        self._subscribe()
        self._rule()
        event_id = self._event()
        with mock.patch.dict(os.environ, FAKE_ENV), \
                mock.patch("pywebpush.webpush", return_value=None) as sender:
            views = send(scope=TenantScope.of(self.user), event_id=event_id,
                         respect_suppression=False)
        self.assertEqual(1, len(views))
        self.assertEqual("webpush", views[0].channel)
        self.assertTrue(views[0].succeeded)
        self.assertEqual(1, sender.call_count)
        self.assertTrue(views[0].recipient_address.startswith("webpush:"))
        self.assertNotIn(FAKE_ENDPOINT, views[0].recipient_address)

    def test_inside_quiet_hours_nothing_is_sent_and_the_row_says_why(self) -> None:
        """⑤ 차단 시간대 안 → 발송 0 · 행 `failure_reason=quiet_hours`."""
        from kernels.k2_notify import QUIET_HOURS_REASON, send

        self._subscribe()
        self._rule()
        event_id = self._event()
        #: 지금 시각을 품는 창 — 시험이 언제 돌아도 안이다.
        now = timezone.localtime(timezone.now())
        start = (now - timedelta(hours=1)).strftime("%H:%M")
        end = (now + timedelta(hours=1)).strftime("%H:%M")
        self._prefs(quiet_start=start, quiet_end=end)
        with mock.patch.dict(os.environ, FAKE_ENV), \
                mock.patch("pywebpush.webpush") as sender:
            views = send(scope=TenantScope.of(self.user), event_id=event_id,
                         respect_suppression=False)
        self.assertEqual(0, sender.call_count, "차단 시간대 안인데 발송기가 불렸습니다.")
        self.assertEqual(1, len(views), "막힌 발송도 행으로 남아야 합니다(D-290).")
        self.assertFalse(views[0].succeeded)
        self.assertEqual(QUIET_HOURS_REASON, views[0].failure_reason)
        self.assertEqual("quiet_hours", QUIET_HOURS_REASON)

    def test_outside_quiet_hours_it_sends(self) -> None:
        from kernels.k2_notify import send

        self._subscribe()
        self._rule()
        event_id = self._event()
        now = timezone.localtime(timezone.now())
        start = (now + timedelta(hours=2)).strftime("%H:%M")
        end = (now + timedelta(hours=3)).strftime("%H:%M")
        self._prefs(quiet_start=start, quiet_end=end)
        with mock.patch.dict(os.environ, FAKE_ENV), \
                mock.patch("pywebpush.webpush", return_value=None) as sender:
            views = send(scope=TenantScope.of(self.user), event_id=event_id,
                         respect_suppression=False)
        self.assertEqual(1, sender.call_count)
        self.assertTrue(views[0].succeeded)

    def test_a_channel_not_chosen_in_m4_is_blocked_by_name(self) -> None:
        from kernels.k2_notify import CHANNEL_NOT_CHOSEN_REASON, send

        self._subscribe()
        self._rule()
        event_id = self._event()
        self._prefs(channels="email")
        with mock.patch.dict(os.environ, FAKE_ENV), mock.patch("pywebpush.webpush") as sender:
            views = send(scope=TenantScope.of(self.user), event_id=event_id,
                         respect_suppression=False)
        self.assertEqual(0, sender.call_count)
        self.assertEqual(CHANNEL_NOT_CHOSEN_REASON, views[0].failure_reason)

    def test_without_a_subscription_the_person_is_not_a_recipient(self) -> None:
        from kernels.k2_notify import resolve_recipients

        self._rule()
        got = resolve_recipients(scope=TenantScope.of(self.user), severity="critical")
        self.assertEqual((), got, "구독 0인 사람이 webpush 수신자로 잡혔습니다.")


class ConstantsMatchTest(TestCase):
    """⑥ 커널과 App 이 같은 감사 행을 같은 이름으로 읽는다."""

    def test_audit_row_names_are_identical(self) -> None:
        from apps.dsm import notify_prefs
        from kernels.k2_notify import webpush

        self.assertEqual(notify_prefs.LOGGER_NAME, webpush.SUBSCRIPTION_LOGGER)
        self.assertEqual(notify_prefs.ACTION_SUBSCRIBE, webpush.ACTION_SUBSCRIBE)
        self.assertEqual(notify_prefs.ACTION_TEST_SEND, webpush.ACTION_TEST_SEND)


class NotifyPrefsM4Test(_Fixture):
    """M4 — PUT → GET 왕복 · 잘못된 시간대 422 · 문자는 선택지에 없다 · 승인 칸은 서버 값."""

    def _get(self):
        from apps.dsm.api_u3 import DsmU3API

        return DsmU3API.get_notify_prefs(DsmU3API(), self._req("get"))

    def _put(self, **kwargs):
        from apps.dsm.api_u3 import DsmU3API

        return DsmU3API.put_notify_prefs(DsmU3API(), self._req("put"), **kwargs)

    def test_put_then_get_round_trips(self) -> None:
        self._put(quiet_start="22:00", quiet_end="07:00", zone_ids="3,4", channels="email,webpush")
        got = self._get()
        self.assertEqual("22:00", got["quiet_start"])
        self.assertEqual("07:00", got["quiet_end"])
        self.assertEqual([3, 4], got["zone_ids"])
        self.assertEqual(["email", "webpush"], got["channels"])
        self.assertTrue(got["saved"])
        self.assertEqual("not_required", got["approval"]["status"])
        self.assertEqual([], got["approval"]["items"])

    def test_a_malformed_quiet_window_is_422(self) -> None:
        from ninja.errors import HttpError

        for start, end in (("25:00", "07:00"), ("22", "07:00"), ("22:00", "")):
            with self.assertRaises(HttpError, msg=f"{start!r}→{end!r}") as caught:
                self._put(quiet_start=start, quiet_end=end)
            self.assertEqual(422, caught.exception.status_code)

    def test_sms_is_not_a_choice(self) -> None:
        from ninja.errors import HttpError

        self.assertEqual(["email", "webpush"], self._get()["allowed_channels"])
        with self.assertRaises(HttpError) as caught:
            self._put(channels="sms")
        self.assertEqual(422, caught.exception.status_code)


class CrossTenantWriteTest(_Fixture):
    """격리 — A 의 사람이 **B 의 사건**에 시험 발송을 매달 수 없다(쓰기 IDOR · D-290).

    `tests/test_tenant_isolation.WRITE_NO_PROBE` 의 `kernels.k2_notify.send_webpush` 줄이
    「다른 파일이 잰다」로 가리키는 자리가 여기다: 음성(남의 사건 → 404 · 행 0) · 양성(제 사건 → 행 1).
    """

    def test_a_cannot_hang_a_drill_send_on_bs_event(self) -> None:
        from django.http import Http404

        from kernels.k2_notify import send_webpush

        UserGroup = apps.get_model("user", "UserGroup")
        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        group_b = UserGroup.objects.create(name="webpush-tenant-B")
        UserGroup.objects.filter(pk=group_b.pk).update(created_by=None)
        stream_b = self._stream("webpush-cam-B", group_b)
        from kernels.k1_event import record_detection

        event_b = record_detection(
            scope=TenantScope.system(reason="시험 씨앗"), stream_monitor_id=stream_b.pk,
            event_type="fire", severity="critical",
            occurred_at=timezone.now() - timedelta(minutes=5), snapshot_path="").event_id
        subscription = {"endpoint": FAKE_ENDPOINT,
                        "keys": {"p256dh": FAKE_P256DH, "auth": FAKE_AUTH}}
        before = Delivery._base_manager.count()
        with mock.patch.dict(os.environ, FAKE_ENV), mock.patch("pywebpush.webpush") as sender:
            with self.assertRaises(Http404):
                send_webpush(scope=TenantScope.of(self.user), subscription=subscription,
                             title="[훈련] x", body="y", event_id=event_b)
        self.assertEqual(0, sender.call_count)
        self.assertEqual(before, Delivery._base_manager.count(), "남의 사건에 행이 남았습니다.")
