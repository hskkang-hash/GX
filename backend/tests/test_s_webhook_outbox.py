# -*- coding: utf-8 -*-
"""UX-19 — 나가는 웹훅 **CAP 1.2**: 구독 → 발송 → 서명 검증 → 재시도 (차선 S · 2026-09-05 TC).

캐시 처리: 우회 — `X-No-Cache` (D-341 착시 ⑦). 이 시험이 재는 것은 **구독의 현재 상태**다.
    구독을 등록·해지하고 **곧바로** 목록을 다시 읽어 그것이 반영됐는지 보는데,
    캐시가 적중하면 **해지한 구독이 살아 있는 것처럼 보인다**. 그러면 이 시험은
    「해지가 된다」를 초록으로 적으면서 실은 **캐시를 재고 있는 것**이 된다.
    ★ 이 자리가 특히 나쁜 이유: 캐시가 덮는 것이 **경보를 받는 사람의 목록**이다 —
      해지된 줄 알았던 구독으로 경보가 계속 나가는 것을 시험이 놓치게 된다.

이 파일이 왜 생겼나 — **문이 없어서 규약이 잠들어 있었다**
----------------------------------------------------------
지난 턴에 규약(SEC-16 · `common/webhook_contract.py`)이 **문보다 먼저** 섰고, 그
대가로 `dormant` 게이트가 규약의 함수 셋(`attempts_from`·`giveup_record`·
`outbound_headers`)을 「아무도 안 부른다」로 잡고 빨간 채였다. 그 빨강이 옳았다
(D-377 · 착시 ⑨ **함수는 문이 아니다**). 이 턴에 문이 서면서 빨강이 초록이 된다.

무엇을 재는가 — **완주 하나**
-----------------------------
    ① 구독      로그인한 계정이 등록한다. 무계정 구독이 없다 (P-37)
    ② 발송      나가는 것이 **우리 스키마가 아니라 CAP 1.2** 다 (UX-19 의 전부)
    ③ 서명 검증 우리가 붙인 헤더를 **규약의 `verify()`** 가 통과시킨다.
                한 글자만 바꿔도 거절한다 — 그것이 「서명했다」의 증거다
    ④ 재시도    죽은 상대를 **정확히 5회** 두드리고 멈추고, 포기가 **행으로** 남는다

무엇을 **못** 재는가 (D-301 — 못 재는 것을 적는다)
--------------------------------------------------
  · **진짜 네트워크를 때리지 않는다.** 발송기(`sender=`)를 넣어 상대를 흉내 낸다.
    실제 타임아웃은 `common/external_http.py` 가 `settings.EXTERNAL_HTTP_TIMEOUT`
    으로 걸고, 그 숫자를 여기 다시 적지 않는다(D-212).
    ★ 대신 **기본 발송기가 그 모듈을 지나는지**는 잰다 — 지나지 않으면 타임아웃 없는
      호출이 태어나고, 그 하나가 워커를 잡는다(W0-17).
  · **잠을 자지 않는다.** 지수 백오프의 대기는 `sleeper=` 로 받아 셈으로만 잰다.
    **기다린 초의 합**이 정책과 같은지는 값으로 대조한다.
  · **상대가 실제로 검증에 성공하는지는 못 잰다.** 우리가 낼 수 있는 것은
    「우리 규약의 `verify()` 가 통과시키는 헤더를 붙였다」까지다.

캐시 처리: **해당 없음** — HTTP 를 때리지 않는다 (D-341 규약).

절대 금지 (AGENT_LOOP 절대금지 #4 · D-105): 이 파일의 시험을 skip·xfail 하지 말 것.

실행
    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \\
      python -m pytest tests/test_s_webhook_outbox.py -q --nomigrations -p no:randomly
"""
from __future__ import annotations

import json

from django.apps import apps
from django.http import Http404
from django.test import override_settings
from django.utils import timezone

from tests.test_k2_notify_kernel import K2Fixture

#: 시험용 서명키. **저장소의 진짜 키가 아니다** — 이 값으로 서명한 것은 아무 데도
#: 안 나간다. 진짜 값은 환경에만 있다(D-204).
KEY_NAME = "test-partner"
KEY_VALUE = "not-a-real-key-only-for-this-test"

SIGNING = {"WEBHOOK_SIGNING_KEYS": {KEY_NAME: KEY_VALUE},
           "CAP_SENDER": "guardianx.test"}


class Receiver:
    """상대를 흉내 낸다. **응답을 미리 정해 두고 받은 것을 전부 기록한다.**

    mock 라이브러리를 쓰지 않는 이유: 무엇을 받았는지 **시험이 직접 들고 있어야**
    서명 검증을 그 자리에서 할 수 있다. 받은 것을 못 보는 흉내는 「보냈다」만 재고
    「무엇을 보냈다」를 못 잰다.
    """

    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls: list[tuple[str, bytes, dict]] = []

    def __call__(self, url, body, headers):
        self.calls.append((url, body, dict(headers)))
        index = min(len(self.calls) - 1, len(self.statuses) - 1)
        status = self.statuses[index]
        return status, ("" if status is not None else "연결 실패(흉내)")


class Clock:
    """`sleeper=` 로 넣는 가짜 잠. **자지 않고 초만 센다.**"""

    def __init__(self):
        self.waited: list[float] = []

    def __call__(self, seconds):
        self.waited.append(seconds)


class OutboxFixture(K2Fixture):
    """K2 픽스처(테넌트 A/B · 스트림 · 규칙)를 그대로 쓴다 — **두 벌로 만들지 않는다.**"""

    def _subscribe(self, scope=None, **kwargs):
        from kernels.k1_event import subscribe

        options = {"event_types": (), "min_severity": "", "payload_format": "json"}
        options.update(kwargs.pop("filters", {}))
        return subscribe(
            scope=scope or self.scope_a,
            webhook_url=kwargs.pop("webhook_url", "https://partner.test.invalid/hook"),
            signing_key_ref=kwargs.pop("signing_key_ref", KEY_NAME),
            filters=options)

    @staticmethod
    def _row(subscription_id):
        Sub = apps.get_model("stream_monitors", "WebhookSubscription")
        return Sub._base_manager.get(pk=subscription_id)

    @staticmethod
    def _webhook_deliveries(event_id):
        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        return Delivery._base_manager.filter(event_id=event_id, channel="webhook")


# ═══════════════════════════════════════════════════════════════════════════
# ① 구독 — **계정이 등록한다.** 무계정 구독이 없다 (세종 §3 함정 ① · P-37)
# ═══════════════════════════════════════════════════════════════════════════
@override_settings(**SIGNING)
class SubscriptionIsOwnedByAnAccountTest(OutboxFixture):

    def test_a_logged_in_account_can_register_and_read_back(self) -> None:
        """양성 대조 — 제 것으로는 **된다** (D-277). 되지 않으면 아래 음성은 무의미하다."""
        from apps.dsm import services

        sub = self._subscribe()
        self.assertTrue(sub.is_active)
        self.assertEqual(KEY_NAME, sub.signing_key_ref)

        rows = services.webhook_subscriptions(scope=self.scope_a)
        self.assertEqual([sub.subscription_id], [r.subscription_id for r in rows])

    def test_the_row_carries_the_registering_tenant(self) -> None:
        """**주인은 서버가 정한다.** 요청이 「누구 것으로 만들지」를 말할 수 없다.

        주인 없는 행은 §0.4 의 `created_by__isnull=True` OR 절을 타고 **모든
        테넌트에게 보인다** — 남의 수신 URL 이 보이는 상태가 된다.
        """
        sub = self._subscribe()
        row = self._row(sub.subscription_id)
        self.assertEqual(self.group_a.pk, row.group_id,
                         "구독 행에 주인이 안 박혔습니다 — 주인 없는 행은 모두에게 보입니다.")
        self.assertEqual(self.user_a.pk, row.created_by_id)

    def test_a_system_scope_cannot_register(self) -> None:
        """★ 사람 없는 호출로는 구독을 못 만든다.

        만들 수 있으면 「누가 등록했는지 모르는 구독」이 생기고, 그것은 **우리가
        관리하지 않는 계정**과 같다. 무계정 링크를 안 만든다는 말의 실제 내용이 이것이다.
        """
        from common.tenant_scope import SystemScopeCannotRead

        with self.assertRaises(SystemScopeCannotRead):
            self._subscribe(scope=self.scope_pipe)

    def test_the_subscription_row_has_no_column_for_the_key_value(self) -> None:
        """★ **서명키 값을 담을 칸 자체가 없다** (D-204 · `CredentialRecord` 와 같은 규약).

        「마스킹해서 저장」은 저장이다. 칸이 있으면 언젠가 채워지고, 채워진 값은
        덤프·백업·화면·로그로 흘러나간다.
        """
        Sub = apps.get_model("stream_monitors", "WebhookSubscription")
        names = {f.name for f in Sub._meta.get_fields()}
        for forbidden in ("signing_key", "secret", "signing_secret", "key_value"):
            self.assertNotIn(forbidden, names,
                             f"구독 표에 서명키 값을 담을 칸({forbidden})이 있습니다.")

    def test_the_view_that_goes_out_carries_only_the_key_name(self) -> None:
        """나가는 값에 키가 섞이지 않는다 — **이름만 나간다.**"""
        sub = self._subscribe()
        self.assertNotIn(KEY_VALUE, json.dumps(sub.__dict__, default=str))


@override_settings(**SIGNING)
class RegistrationRefusesWhatItCannotDeliverTest(OutboxFixture):
    """등록은 됐는데 보낼 수 없는 구독을 만들지 않는다 — 그 구독은 **믿는 상대**를 만든다."""

    def test_an_unknown_signing_key_is_refused_at_registration(self) -> None:
        from common.webhook_outbox import UnknownSigningKey

        with self.assertRaises(UnknownSigningKey):
            self._subscribe(signing_key_ref="no-such-key")

    def test_an_empty_signing_key_ref_is_refused(self) -> None:
        from common.webhook_outbox import WebhookSubscriptionError

        with self.assertRaises(WebhookSubscriptionError):
            self._subscribe(signing_key_ref="")

    def test_plaintext_http_is_refused(self) -> None:
        """서명은 **위조**를 막고, 평문은 **읽히는 것**을 못 막는다. 본문에 위치가 있다."""
        from common.webhook_outbox import WebhookSubscriptionError

        with self.assertRaises(WebhookSubscriptionError):
            self._subscribe(webhook_url="http://partner.test.invalid/hook")

    def test_inside_addresses_are_refused(self) -> None:
        """★ 등록만으로 **우리 서버가 남의 대리인**이 되는 자리를 막는다.

        밖에서 못 닿는 주소를 우리가 대신 두드리게 된다 — 본문을 되돌려 주지 않아도
        두드리는 것 자체가 쓰기다.
        """
        from common.webhook_outbox import WebhookSubscriptionError

        for url in ("https://127.0.0.1/hook", "https://10.0.0.5/hook",
                    "https://169.254.169.254/latest/meta-data",
                    "https://localhost/hook"):
            with self.subTest(url=url), self.assertRaises(WebhookSubscriptionError):
                self._subscribe(webhook_url=url)

    def test_a_public_https_address_is_still_accepted(self) -> None:
        """음성 대조가 **전부를 막는 것**이 되지 않았는지 (D-277)."""
        sub = self._subscribe(webhook_url="https://8.8.8.8/hook")
        self.assertTrue(sub.is_active)


# ═══════════════════════════════════════════════════════════════════════════
# ② 발송 — **우리 스키마가 아니라 CAP 1.2 로 나간다** (UX-19 의 전부)
# ═══════════════════════════════════════════════════════════════════════════
@override_settings(**SIGNING)
class WhatGoesOutIsTheStandardTest(OutboxFixture):

    def _dispatch(self, statuses=(200,), **kwargs):
        from common import webhook_outbox

        event_id = kwargs.pop("event_id", None) or self._event(self.stream_a)
        receiver = Receiver(statuses)
        clock = Clock()
        views = webhook_outbox.dispatch_event(
            scope=self.scope_a, event_id=event_id, sender=receiver, sleeper=clock)
        return event_id, receiver, clock, views

    def test_the_body_is_a_cap_1_2_alert_not_our_event_view(self) -> None:
        """★ **이 시험이 UX-19 다.**

        우리 `EventView` 의 칸 이름(`event_id`·`severity`·`response_state`)이 본문의
        **최상위**에 있으면, 그것은 우리 스키마를 그대로 내보낸 것이다. 그러면 우리가
        칸 하나를 바꾸는 날 상급기관·SDN·에스비 App 셋이 함께 깨진다.
        """
        self._subscribe()
        _, receiver, _, _ = self._dispatch()

        self.assertEqual(1, len(receiver.calls))
        body = json.loads(receiver.calls[0][1].decode("utf-8"))

        for required in ("identifier", "sender", "sent", "status", "msgType", "scope"):
            self.assertIn(required, body,
                          f"CAP 1.2 의 필수 요소 <{required}> 가 없습니다 — 받는 쪽 파서가 "
                          f"거절합니다.")
        for ours in ("event_id", "severity", "event_type", "response_state",
                     "stream_monitor_id"):
            self.assertNotIn(ours, body,
                             f"우리 스키마의 칸 {ours!r} 이 본문 최상위에 있습니다 — "
                             f"표준으로 내보낸 것이 아닙니다.")

    def test_every_value_we_emit_is_inside_caps_closed_vocabulary(self) -> None:
        """★ 닫힌 어휘를 **지어내지 않는다.** 어휘 밖 낱말은 받는 쪽이 거절한다."""
        from common import cap_1_2

        self._subscribe()
        _, receiver, _, _ = self._dispatch()
        body = json.loads(receiver.calls[0][1].decode("utf-8"))
        info = body["info"][0]

        self.assertIn(body["status"], cap_1_2.CAP_STATUS)
        self.assertIn(body["msgType"], cap_1_2.CAP_MSG_TYPE)
        self.assertIn(body["scope"], cap_1_2.CAP_SCOPE)
        self.assertIn(info["urgency"], cap_1_2.CAP_URGENCY)
        self.assertIn(info["severity"], cap_1_2.CAP_SEVERITY)
        self.assertIn(info["certainty"], cap_1_2.CAP_CERTAINTY)
        for category in info["category"]:
            self.assertIn(category, cap_1_2.CAP_CATEGORY)

    def test_restricted_scope_carries_a_restriction(self) -> None:
        """CAP 은 `scope=Restricted` 면 `restriction` 을 요구한다. 수신 URL 은 본문에 없다."""
        sub = self._subscribe()
        _, receiver, _, _ = self._dispatch()
        body = json.loads(receiver.calls[0][1].decode("utf-8"))

        self.assertEqual("Restricted", body["scope"])
        self.assertTrue(body.get("restriction"))
        self.assertNotIn(sub.endpoint_url, json.dumps(body, ensure_ascii=False),
                         "수신 URL 이 본문에 실렸습니다 — 본문이 지나가는 모든 자리에 남습니다.")

    def test_the_sent_time_carries_an_offset_not_a_z(self) -> None:
        """★ CAP 1.2 는 `Z` 를 허용하지 않는다. 오프셋이 없으면 **몇 시간이 조용히 어긋난다.**"""
        self._subscribe()
        _, receiver, _, _ = self._dispatch()
        sent = json.loads(receiver.calls[0][1].decode("utf-8"))["sent"]
        self.assertFalse(sent.endswith("Z"), f"CAP 시각이 Z 로 끝납니다: {sent}")
        self.assertRegex(sent, r"[+-]\d{2}:\d{2}$")

    def test_the_event_type_table_is_exhaustive(self) -> None:
        """★ 새 `EventType` 이 표에 없으면 그 이벤트는 조용히 `Other` 로 나간다.

        받는 쪽은 그것이 무엇인지 영영 모른다. 표가 전수인지는 **여기서** 잰다 —
        번역기 자신은 막지 않는다(막으면 새 유형 하나가 모든 발송을 멈춘다).
        """
        from common.cap_1_2 import EVENT_TYPE_TO_CAP

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        declared = {value for value, _ in Event.EventType.choices}
        missing = sorted(declared - set(EVENT_TYPE_TO_CAP))
        self.assertEqual(
            [], missing,
            f"CAP 유형 표에 없는 이벤트 유형: {missing}. 표에 없으면 `Other` 로 나가고, "
            f"받는 쪽은 그것이 무엇인지 모릅니다 (common/cap_1_2.py EVENT_TYPE_TO_CAP).")

    def test_xml_is_available_because_that_is_caps_own_form(self) -> None:
        """상급기관 연계는 대개 XML 을 요구한다 — JSON 만 내면 「표준으로 낸다」가 반만 참이다."""
        self._subscribe(filters={"payload_format": "xml"})
        _, receiver, _, _ = self._dispatch()
        url, body, headers = receiver.calls[0]
        text = body.decode("utf-8")
        self.assertIn("urn:oasis:names:tc:emergency:cap:1.2", text)
        self.assertIn("<alert", text)
        self.assertEqual("application/cap+xml", headers["Content-Type"])

    def test_filters_decide_who_gets_it(self) -> None:
        """**빈 목록은 「전부」다.** 끄는 것은 필터가 아니라 `is_active` 다."""
        from common import webhook_outbox

        self._subscribe(filters={"event_types": ("flood",)})
        fire = self._event(self.stream_a, event_type="fire")
        receiver = Receiver([200])
        webhook_outbox.dispatch_event(scope=self.scope_a, event_id=fire,
                                      sender=receiver, sleeper=Clock())
        self.assertEqual([], receiver.calls,
                         "유형 필터 밖의 이벤트가 나갔습니다.")

    def test_a_revoked_subscription_receives_nothing(self) -> None:
        from apps.dsm import services
        from common import webhook_outbox

        sub = self._subscribe()
        services.revoke_webhook_subscription(scope=self.scope_a,
                                             subscription_id=sub.subscription_id)
        receiver = Receiver([200])
        webhook_outbox.dispatch_event(scope=self.scope_a,
                                      event_id=self._event(self.stream_a),
                                      sender=receiver, sleeper=Clock())
        self.assertEqual([], receiver.calls, "해지한 구독으로 계속 나갑니다.")
        self.assertFalse(self._row(sub.subscription_id).is_active)
        # ★ 행은 **남는다** — 지우면 그 구독이 무엇을 받았는지가 함께 사라진다.
        self.assertIsNotNone(self._row(sub.subscription_id))

    def test_a_success_leaves_a_delivery_row_of_the_same_shape_as_a_human_one(self) -> None:
        """발송 이력을 두 벌로 만들지 않는다 — 화면과 보고서가 웹훅을 따로 세면 어긋난다."""
        self._subscribe()
        event_id, _, _, views = self._dispatch()

        self.assertEqual(1, len(views))
        self.assertTrue(views[0].succeeded)
        self.assertIsNotNone(views[0].sent_at)
        rows = self._webhook_deliveries(event_id)
        self.assertEqual(1, rows.count())
        self.assertEqual("webhook", rows.first().channel)

    def test_the_channel_name_matches_the_model_enum(self) -> None:
        """두 벌로 적은 이름이 갈리지 않았는가 (D-212)."""
        from common.webhook_outbox import CHANNEL

        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        self.assertEqual(Delivery.Channel.WEBHOOK.value, CHANNEL)


# ═══════════════════════════════════════════════════════════════════════════
# ③ 서명 검증 — **규약의 `verify()` 가 통과시키는가**
# ═══════════════════════════════════════════════════════════════════════════
@override_settings(**SIGNING)
class WhatWeSendVerifiesUnderTheContractTest(OutboxFixture):
    """★ 이 반이 SEC-16 이 존재하는 이유다: **서명 없는 웹훅은 누구나 보낼 수 있는 경보다.**"""

    def _one_call(self):
        from common import webhook_outbox

        self._subscribe()
        receiver = Receiver([200])
        webhook_outbox.dispatch_event(scope=self.scope_a,
                                      event_id=self._event(self.stream_a),
                                      sender=receiver, sleeper=Clock())
        return receiver.calls[0]

    def test_the_headers_we_attach_pass_the_contracts_verify(self) -> None:
        from common.webhook_contract import verify

        _, body, headers = self._one_call()
        ok, why = verify(KEY_VALUE, body, headers)
        self.assertTrue(ok, f"우리가 보낸 것을 우리 규약이 거절했습니다: {why}")

    def test_the_whole_contract_rides_on_the_wire(self) -> None:
        from common.webhook_contract import (
            EVENT_ID_HEADER, SCHEMA_HEADER, SCHEMA_VERSION, SIGNATURE_HEADER,
            SIGNATURE_PREFIX, TIMESTAMP_HEADER,
        )

        _, _, headers = self._one_call()
        self.assertEqual(SCHEMA_VERSION, headers[SCHEMA_HEADER])
        self.assertTrue(headers[SIGNATURE_HEADER].startswith(SIGNATURE_PREFIX))
        self.assertTrue(headers[TIMESTAMP_HEADER].isdigit())
        self.assertIn(EVENT_ID_HEADER, headers,
                      "이벤트 식별자가 없습니다 — 재시도가 있는 규약에서 중복 도착은 "
                      "결함이 아니라 정상이고, 상대는 그것을 이 값으로 가릅니다.")

    def test_one_changed_byte_is_rejected(self) -> None:
        """★ **거절하지 못하면 서명한 것이 아니다.** 본문 한 글자를 바꾼다."""
        from common.webhook_contract import REJECT_SIGNATURE_MISMATCH, verify

        _, body, headers = self._one_call()
        ok, why = verify(KEY_VALUE, body + b" ", headers)
        self.assertFalse(ok)
        self.assertEqual(REJECT_SIGNATURE_MISMATCH, why)

    def test_another_partners_key_does_not_verify_ours(self) -> None:
        """구독마다 키가 다르다는 말의 실제 내용."""
        from common.webhook_contract import verify

        _, body, headers = self._one_call()
        ok, _ = verify("some-other-partners-key", body, headers)
        self.assertFalse(ok, "남의 키로도 우리 서명이 통과합니다 — 서명이 무의미합니다.")

    def test_nothing_goes_out_when_the_key_cannot_be_resolved(self) -> None:
        """★ 키가 없으면 **보내지 않는다.** 규약의 `verify()` 가 키 없음을 통과가 아니라
        거절로 못박은 것과 같은 판단이다 — 서명 없이 나간 경보는 회수할 수 없다."""
        from common import webhook_outbox

        self._subscribe()
        event_id = self._event(self.stream_a)
        receiver = Receiver([200])
        with override_settings(WEBHOOK_SIGNING_KEYS={}):
            views = webhook_outbox.dispatch_event(
                scope=self.scope_a, event_id=event_id,
                sender=receiver, sleeper=Clock())

        self.assertEqual([], receiver.calls, "서명키 없이 밖으로 나갔습니다.")
        # **그래도 행은 남는다** — 「보낸 적 없음」과 「못 보냄」은 다른 상태다 (D-290).
        self.assertEqual(1, len(views))
        self.assertFalse(views[0].succeeded)
        self.assertIn("서명키", views[0].failure_reason)


# ═══════════════════════════════════════════════════════════════════════════
# ④ 재시도 — **5회에서 멈추고, 포기가 행으로 남는다** (SEC-16 닫는 조건 ②)
# ═══════════════════════════════════════════════════════════════════════════
@override_settings(**SIGNING)
class RetryStopsAtFiveAndLeavesARowTest(OutboxFixture):

    def test_a_dead_receiver_is_hit_exactly_five_times(self) -> None:
        from common import webhook_outbox
        from common.webhook_contract import MAX_ATTEMPTS

        self._subscribe()
        event_id = self._event(self.stream_a)
        receiver = Receiver([503])
        clock = Clock()
        views = webhook_outbox.dispatch_event(
            scope=self.scope_a, event_id=event_id, sender=receiver, sleeper=clock)

        self.assertEqual(MAX_ATTEMPTS, len(receiver.calls),
                         "죽은 상대를 정확히 5회 두드리지 않았습니다.")
        self.assertFalse(views[0].succeeded)
        self.assertEqual(MAX_ATTEMPTS - 1, views[0].retry_count)

    def test_the_waiting_between_attempts_is_the_policys_own_number(self) -> None:
        """대기를 **여기서 다시 적지 않는다** (D-212) — 정책이 낸 값과 대조한다."""
        from common import webhook_outbox
        from common.webhook_contract import RetryPolicy

        self._subscribe()
        receiver, clock = Receiver([503]), Clock()
        webhook_outbox.dispatch_event(scope=self.scope_a,
                                      event_id=self._event(self.stream_a),
                                      sender=receiver, sleeper=clock)
        self.assertEqual(RetryPolicy().total_wait(), sum(clock.waited))

    def test_a_client_error_is_not_retried(self) -> None:
        """4xx 는 다시 보내도 같은 답이 온다 — 재시도는 「상대가 잠깐 죽었다」를 위한 것이다."""
        from common import webhook_outbox

        self._subscribe()
        receiver = Receiver([400])
        views = webhook_outbox.dispatch_event(
            scope=self.scope_a, event_id=self._event(self.stream_a),
            sender=receiver, sleeper=Clock())
        self.assertEqual(1, len(receiver.calls))
        self.assertIn("rejected_by_receiver", views[0].failure_reason)

    def test_no_response_at_all_is_retried(self) -> None:
        """응답을 못 받은 것과 답을 거절한 것은 다르다."""
        from common import webhook_outbox
        from common.webhook_contract import MAX_ATTEMPTS

        self._subscribe()
        receiver = Receiver([None])
        webhook_outbox.dispatch_event(scope=self.scope_a,
                                      event_id=self._event(self.stream_a),
                                      sender=receiver, sleeper=Clock())
        self.assertEqual(MAX_ATTEMPTS, len(receiver.calls))

    def test_a_success_on_the_third_try_stops_there(self) -> None:
        """양성 대조 — 되살아난 상대에게는 그만 보낸다."""
        from common import webhook_outbox

        self._subscribe()
        receiver = Receiver([503, 503, 200])
        views = webhook_outbox.dispatch_event(
            scope=self.scope_a, event_id=self._event(self.stream_a),
            sender=receiver, sleeper=Clock())
        self.assertEqual(3, len(receiver.calls))
        self.assertTrue(views[0].succeeded)
        self.assertEqual(2, views[0].retry_count)

    def test_giving_up_leaves_a_row_that_names_why(self) -> None:
        """★ **조용히 사라지는 것이 이 제품에서 가장 나쁜 실패다.**

        5회를 다 쓰고 못 간 경보가 아무 자국도 남기지 않으면, 상대는 못 받았고
        우리는 보냈다고 믿는다 — 둘 다 모르는 채로.
        """
        from common import webhook_outbox
        from common.webhook_contract import GIVEUP_EXHAUSTED

        self._subscribe()
        event_id = self._event(self.stream_a)
        webhook_outbox.dispatch_event(scope=self.scope_a, event_id=event_id,
                                      sender=Receiver([503]), sleeper=Clock())

        rows = self._webhook_deliveries(event_id)
        self.assertEqual(1, rows.count(), "포기가 행으로 남지 않았습니다.")
        row = rows.first()
        self.assertFalse(row.succeeded)
        self.assertIsNone(row.sent_at,
                          "실패에 발송 시각이 찍혔습니다 — F-10 의 30초가 실패한 발송으로 "
                          "달성됩니다.")
        self.assertIn(GIVEUP_EXHAUSTED, row.failure_reason)
        self.assertEqual(4, row.retry_count)

    def test_the_two_kinds_of_giving_up_are_not_the_same_word(self) -> None:
        """「실패」 한 낱말로 뭉치지 않는다 — **고치는 사람이 다르다.**"""
        from common import webhook_outbox
        from common.webhook_contract import GIVEUP_EXHAUSTED, GIVEUP_REJECTED

        self._subscribe()
        dead = webhook_outbox.dispatch_event(
            scope=self.scope_a, event_id=self._event(self.stream_a),
            sender=Receiver([503]), sleeper=Clock())
        rude = webhook_outbox.dispatch_event(
            scope=self.scope_a, event_id=self._event(self.stream_a),
            sender=Receiver([422]), sleeper=Clock())

        self.assertIn(GIVEUP_EXHAUSTED, dead[0].failure_reason)
        self.assertIn(GIVEUP_REJECTED, rude[0].failure_reason)

    def test_a_failed_subscription_does_not_update_last_delivered(self) -> None:
        """「한 번도 도달한 적 없다」가 「보냈다」로 둔갑하지 않는다."""
        from common import webhook_outbox

        sub = self._subscribe()
        webhook_outbox.dispatch_event(scope=self.scope_a,
                                      event_id=self._event(self.stream_a),
                                      sender=Receiver([503]), sleeper=Clock())
        self.assertIsNone(self._row(sub.subscription_id).last_delivered_at)


# ═══════════════════════════════════════════════════════════════════════════
# 격리 — **남의 구독은 못 만지고, 남의 이벤트는 내 주소로 안 온다**
# ═══════════════════════════════════════════════════════════════════════════
@override_settings(**SIGNING)
class CrossTenantTest(OutboxFixture):
    """★ 대장(`tests/test_tenant_isolation.WRITE_NO_PROBE`)이 이 반을 이름으로 가리킨다.

    `subscribe` 에는 **남의 것을 가리킬 인자가 없다**(주인은 서버가 정한다). 이 면의
    진짜 교차 쓰기는 **해지**이고, 그것은 남의 구독 번호를 인자로 받는다.
    """

    def test_another_tenant_cannot_see_my_subscription(self) -> None:
        from apps.dsm import services

        self._subscribe(scope=self.scope_a)
        self.assertEqual([], list(services.webhook_subscriptions(scope=self.scope_b)),
                         "남의 테넌트 수신 URL 이 보입니다.")

    def test_another_tenant_cannot_revoke_mine(self) -> None:
        """★ 거절만으로는 부족하다 — **남의 구독이 안 꺼진 것**까지 잰다 (SEC-07 과 같은 형).

        끄면 그 기관의 경보가 **조용히** 멈춘다. 아무 일도 일어나지 않는 모양이라
        사고를 늦게 안다.
        """
        from apps.dsm import services

        sub = self._subscribe(scope=self.scope_a)

        with self.assertRaises(Http404):
            services.revoke_webhook_subscription(
                scope=self.scope_b, subscription_id=sub.subscription_id)

        self.assertTrue(self._row(sub.subscription_id).is_active,
                        "거절은 했는데 남의 구독이 꺼졌습니다.")

    def test_the_owner_can_revoke_it(self) -> None:
        """양성 대조 — 제 것은 꺼진다 (D-277). 아니면 위 음성은 「기능이 없다」와 같다."""
        from apps.dsm import services

        sub = self._subscribe(scope=self.scope_a)
        services.revoke_webhook_subscription(scope=self.scope_a,
                                             subscription_id=sub.subscription_id)
        self.assertFalse(self._row(sub.subscription_id).is_active)

    def test_my_subscription_does_not_receive_another_tenants_event(self) -> None:
        """★ 구독은 **이벤트의 테넌트**를 따른다 — 요청자를 따르지 않는다.

        따르지 않으면 남의 재난이 우리 주소로 나가고, 그것은 읽기 격리를 온전히
        지키고도 새는 자리다.
        """
        from common import webhook_outbox

        self._subscribe(scope=self.scope_a)
        foreign = self._event(self.stream_b)
        receiver = Receiver([200])
        webhook_outbox.dispatch_event(scope=self.scope_a, event_id=foreign,
                                      sender=receiver, sleeper=Clock())
        self.assertEqual([], receiver.calls, "남의 테넌트 이벤트가 내 주소로 나갔습니다.")


# ═══════════════════════════════════════════════════════════════════════════
# 배선 — **문이 실제로 규약을 부르는가** (착시 ⑨ · D-377)
# ═══════════════════════════════════════════════════════════════════════════
class TheDoorActuallyCallsTheContractTest(OutboxFixture):
    """★ 이 반이 이번 턴의 첫 증거다.

    지난 턴에 규약이 문 없이 태어났고 `dormant` 가 그것을 빨강으로 잡았다.
    여기서 재는 것은 「함수가 있다」가 아니라 **「문이 그것을 부른다」**이다 —
    그 둘의 차이가 정확히 착시 ⑨(함수는 문이 아니다)이다.
    """

    def test_the_outbox_calls_the_three_names_the_gate_was_watching(self) -> None:
        import ast
        import inspect

        from common import webhook_outbox

        tree = ast.parse(inspect.getsource(webhook_outbox))
        called = {node.func.id for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        for name in ("outbound_headers", "giveup_record", "attempts_from"):
            self.assertIn(name, called,
                          f"문이 규약의 {name}() 를 부르지 않습니다 — 규약이 다시 "
                          f"잠듭니다(D-377 · 착시 ⑨).")

    def test_the_default_sender_goes_through_the_timeout_module(self) -> None:
        """★ 타임아웃 숫자를 호출부에 적지 않는다 (D-212 · W0-17).

        `requests` 를 직접 부르면 타임아웃 없는 호출이 태어나고, 그 하나가 늦으면
        워커가 잡히고 잡힌 워커가 쌓이면 서비스가 선다.
        """
        import inspect

        from common import webhook_outbox

        src = inspect.getsource(webhook_outbox._post)
        self.assertIn("external_http.request", src)
        self.assertNotIn("requests.post", src)

    def test_the_module_declares_no_routes(self) -> None:
        """함정 — **새 인증 경로를 만들지 않는다** (세종 §4-4 · P-37).

        문은 `apps/dsm/api.py` 가 낸다. 이 모듈이 자기 라우트를 내면 그것이
        F-05 진입면 밖의 두 번째 문이 된다.
        """
        import inspect

        from common import cap_1_2, webhook_outbox

        for module in (webhook_outbox, cap_1_2):
            src = inspect.getsource(module)
            for mark in ("@route.", "@api_controller", "urlpatterns", "re_path("):
                self.assertNotIn(mark, src,
                                 f"{module.__name__} 이 라우트를 냈습니다 ({mark}).")

    def test_the_inbound_key_surface_was_not_widened(self) -> None:
        """★ `INBOUND_KEY_ALLOWED` 를 한 줄도 넓히지 않았다.

        키로 구독을 걸 수 있으면 키 하나가 **자기에게 이벤트를 계속 흘려보내는 관**이
        되고, 키를 폐기해도 그 관은 남는다.
        """
        import inspect

        from apps.dsm import api

        # ★ `getsource(api.DsmAPI)` 를 쓰지 않는다 — ninja_extra 가 컨트롤러를 감싸서
        #   클래스 정의를 못 찾는다(OSError). 모듈 원문을 읽는 것이 사실에 더 가깝다.
        src = inspect.getsource(api)
        block = src[src.index("webhook-subscriptions"):]
        head = block[:block.index("def delete_webhook_subscription")]
        self.assertNotIn("inbound_key=True", head,
                         "구독 라우트가 들어오는 키를 받습니다 — 진입면이 넓어졌습니다.")


class TheNotifyDoorFansOutTest(OutboxFixture):
    """발송 문(F-10)이 구독에게도 내보내는가 — 그리고 **없으면 아무 일도 없는가.**"""

    def test_with_no_subscription_the_notify_route_behaves_exactly_as_before(self) -> None:
        """★ 켜기 전과 후가 같다. 이것이 이 배선을 안전하게 만드는 성질이다."""
        from apps.dsm import services

        event_id = self._event(self.stream_a, when=timezone.now())
        records = services.notify_event(scope=self.scope_a, event_id=event_id)
        self.assertTrue(all(r.channel != "webhook" for r in records))
        self.assertEqual(0, self._webhook_deliveries(event_id).count())

    @override_settings(**SIGNING)
    def test_the_suppressed_case_does_not_send_a_webhook_either(self) -> None:
        """★ 억제는 **채널의 규칙이 아니라 알림의 규칙**이다 (F-04 5분).

        여기서 웹훅만 나가면 5분 안에 같은 경보가 상급기관에 두 번 간다.

        ★ **키의 정본은 `backend/tests/test_f04_suppression_key.py`** (2026-09-21 ·
          턴 Z · 세종: 「같은 스트림 + 같은 유형 + 직전 발송 시각」). 이 시험이
          전제로 삼는 억제는 그 계약이다.
        """
        from apps.dsm import services
        from kernels.k2_notify import suppress

        self._subscribe()
        first = self._event(self.stream_a, when=timezone.now())
        services.notify_event(scope=self.scope_a, event_id=first)

        second = self._event(self.stream_a, when=timezone.now())
        # 전제를 **단언으로** 적는다. 조건문으로 비껴가면 이 시험은 억제가 꺼진 날
        # 조용히 아무것도 안 재게 된다 — 그것이 「초록인데 안 잰 것」이다(D-301).
        self.assertTrue(
            suppress(scope=self.scope_a, event_id=second),
            "전제가 깨졌습니다 — 5분 억제가 두 번째 이벤트를 접지 않습니다. "
            "그렇다면 웹훅 팬아웃의 억제 근거도 다시 봐야 합니다.")
        records = services.notify_event(scope=self.scope_a, event_id=second)
        self.assertEqual((), tuple(records))
        self.assertEqual(0, self._webhook_deliveries(second).count(),
                         "억제된 알림인데 웹훅은 나갔습니다 — 5분 안에 두 번 갑니다.")
