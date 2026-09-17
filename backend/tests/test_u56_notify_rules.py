# -*- coding: utf-8 -*-
"""턴 S · U56 — S-16 「알림 받는 사람·채널」(UX-43 · WS-14) · S-15 「내 정보」.

무엇을 재는가 — **네 가지, 그리고 그중 둘이 이 절의 전부다**
------------------------------------------------------------
    ① **심각 0명 금지가 실제로 막는가** — 그리고 막았을 때 **행이 안 바뀌는가**(되돌림).
       거절만 재고 행을 안 재면 「거절했다고 말하면서 저장은 된」 상태를 못 본다.
       그 상태가 정확히 D-284 의 조용한 성공이다.
    ② **시험 발송이 훈련 채널로만 가는가** — 그리고 `DeliveryRecord` 를 **안 만드는가.**
       그 표는 F-10 의 30초와 5분 억제가 세는 자리다. 시험 한 건이 끼면 **그 다음
       진짜 경보가 억제로 삼켜진다** — 화면 어디에도 안 나타나는 사고다.
    ③ 낮은 문(`save_notification_rule`)은 **여전히 지난다** — 시드가 첫 규칙을 세우는
       순간 스스로 막히면 안 된다(두 문턱 설계가 실제로 두 문턱인가).
    ④ 라우트가 **삼켜지지 않았는가** — `/settings/notify-rules`(두 조각)는
       `GET /settings/{domain}` 에 삼켜진다. 세 조각으로 연 경로가 405 가 아니라
       실제 판정(200/403/401)을 내는지 HTTP 왕복으로 잰다.

★ 픽스처를 새로 짓지 않는다 (D-379) — 커널 쪽은 `K2Fixture`, HTTP 쪽은 `DsmFixture`.
  두 벌로 지으면 두 픽스처가 갈리고, 갈린 픽스처 위의 두 시험은 다른 세상을 잰다.

캐시 처리: 우회 (`tests.no_cache.NO_CACHE`) — 관문을 재는 시험이 캐시를 재면 안 된다(D-341).
"""
from __future__ import annotations

import json
import uuid

from django.apps import apps
from django.conf import settings
from django.test import Client

from tests.no_cache import NO_CACHE
from tests.test_dsm_app import DsmFixture
from tests.test_k2_notify_kernel import K2Fixture


# ═══════════════════════════════════════════════════════════════════════════
# ① · ② · ③ 커널 — 심각 0명 금지 · 시험 발송 · 두 문턱
# ═══════════════════════════════════════════════════════════════════════════
class SaveRuleGuardTest(K2Fixture):
    """`save_rule` 은 **심각을 0명으로 만드는 저장을 거절한다.**

    `K2Fixture` 는 group_a 에 critical 규칙 하나(role_a · email)와 그 역할의 사람
    (user_a)을 갖고 있다 — 즉 **착수 시점의 심각 수신자는 1명**이다.
    """

    def test_overview_reports_critical_reach(self) -> None:
        """★ 양성 대조 — 막기 전에, **지금 닿는다는 것**을 먼저 잰다."""
        from kernels.k2_notify import notify_rule_overview

        view = notify_rule_overview(scope=self.scope_a)
        self.assertEqual(1, view["critical_recipient_count"])
        self.assertFalse(view["critical_blocked"])
        self.assertTrue(view["rules"], "규칙 목록이 비었습니다.")
        #: 시험 발송이 나갈 곳을 **누르기 전에** 말해 준다.
        self.assertEqual("log", view["test_channel"])

    def test_deactivating_the_last_critical_rule_is_refused_and_rolled_back(self) -> None:
        """★★ **이 시험이 이 절의 전부다.**

        마지막 심각 규칙을 끄면 그 테넌트의 심각 경보는 아무에게도 안 간다.
        거절이 실제로 일어나는가 — 그리고 **행이 그대로 살아 있는가**(되돌림).
        """
        from kernels.k2_notify import CriticalWithoutRecipients, save_rule

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        before = Rule._base_manager.get(pk=self.rule_a.pk)
        self.assertTrue(before.is_active, "전제가 깨졌습니다 — 규칙이 이미 꺼져 있습니다.")

        with self.assertRaises(CriticalWithoutRecipients):
            save_rule(scope=self.scope_a, severity="critical",
                      role_code=self.role_a.code, channels=["email"],
                      is_active=False, rule_id=self.rule_a.pk)

        after = Rule._base_manager.get(pk=self.rule_a.pk)
        self.assertTrue(
            after.is_active,
            "거절했다고 말하면서 **저장은 됐다** — 트랜잭션이 안 되돌아갔습니다. "
            "화면에는 「저장하지 못했습니다」가 뜨고 심각 경보는 꺼진 상태입니다(D-284).")

    def test_the_low_door_still_lets_the_seed_through(self) -> None:
        """★ 두 문턱이 **실제로 두 문턱인가** — 낮은 문은 그대로 지나야 한다.

        `save_notification_rule` 까지 심각 검사를 걸면 `seed_alert_routing` 이 첫 규칙을
        세우는 순간(그때는 당연히 0명이다) **스스로 막힌다.**
        """
        from kernels.k2_notify import save_notification_rule

        view = save_notification_rule(
            scope=self.scope_a, severity="critical", role_code=self.role_a.code,
            channels=["email"], is_active=False, rule_id=self.rule_a.pk)
        self.assertFalse(view.is_active,
                         "낮은 문이 막혔습니다 — 시드가 첫 규칙을 못 세웁니다.")

    def test_webpush_is_a_savable_channel_name(self) -> None:
        """★ [실측 2026-09-16] **스키마와 검사가 다른 이름을 쓰고 있었다.**

        `DsmNotifyPrefs.channels` 는 「`email`·`sms`·`webpush` 중에서」라고 적어 두었는데
        `channels.UNAVAILABLE` 에 `webpush` 가 없어 **저장하면 「모르는 채널」로 400** 이었다.
        화면이 고를 수 있는 채널을 서버가 거절하는 자리다(D-212 — 두 벌이 갈렸다).
        """
        from kernels.k2_notify import save_rule

        view = save_rule(scope=self.scope_a, severity="warning",
                         role_code=self.role_a.code, channels=["webpush"])
        self.assertEqual(("webpush",), view.channels)

    def test_unknown_channel_is_still_refused(self) -> None:
        """★ 음성 대조 — 위 시험이 「아무 이름이나 받는다」로 통과하지 않았는지 가른다."""
        from kernels.k2_notify import InvalidNotifyInput, save_rule

        with self.assertRaises(InvalidNotifyInput):
            save_rule(scope=self.scope_a, severity="warning",
                      role_code=self.role_a.code, channels=["carrier-pigeon"])


class TestSendTest(K2Fixture):
    """시험 발송 — **훈련 채널로만 · 이력을 안 만든다.**"""

    def test_test_send_goes_to_the_drill_channel_only(self) -> None:
        from kernels.k2_notify import send_test_notification

        result = send_test_notification(scope=self.scope_a, severity="critical")
        self.assertEqual("log", result["channel"])
        self.assertEqual(1, result["recipients"])
        self.assertEqual(1, result["sent"])
        self.assertFalse(
            result["reaches_people"],
            "시험 발송이 「사람에게 닿았다」고 주장합니다 — 훈련 채널은 로그입니다(D-284).")

    def test_test_send_creates_no_delivery_record(self) -> None:
        """★★ `DeliveryRecord` 는 F-10 의 30초와 **5분 억제**가 세는 표다.

        시험 한 건이 끼면 그 다음 진짜 경보가 억제로 삼켜진다 — 화면 어디에도
        안 나타나는 사고이므로, 여기서 행 수를 **직접** 센다.
        """
        from kernels.k2_notify import send_test_notification

        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        before = Delivery._base_manager.count()
        send_test_notification(scope=self.scope_a, severity="critical")
        self.assertEqual(
            before, Delivery._base_manager.count(),
            "시험 발송이 발송 이력을 남겼습니다 — 그 행은 5분 억제에 잡혀 "
            "**다음 진짜 경보를 삼킵니다.**")

    def test_test_send_creates_no_event(self) -> None:
        """P-156 — 측정이 자기가 재는 표본을 바꾸지 않는다."""
        from kernels.k2_notify import send_test_notification

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        before = Event._base_manager.count()
        send_test_notification(scope=self.scope_a, severity="critical")
        self.assertEqual(before, Event._base_manager.count(),
                         "시험 발송이 사건을 만들었습니다 — 그 사건이 다음 회 표본에 듭니다.")


class MyNotifyReachTest(K2Fixture):
    """S-15 「내 정보」 — 나는 무엇을 받는가. **읽기뿐이다.**"""

    def test_reports_my_own_identity_and_what_reaches_me(self) -> None:
        from kernels.k2_notify import my_notify_reach

        me = my_notify_reach(scope=self.scope_a)
        self.assertEqual(self.user_a.pk, me["user_id"])
        self.assertEqual(self.group_a.pk, me["group_id"])
        self.assertIn(self.role_a.code, me["roles"])
        self.assertFalse(me["receives_nothing"])
        self.assertTrue(any(r["severity"] == "critical" for r in me["receives"]))
        #: 「내 알림 설정」의 쓰기 면은 U3 의 WS-02 다 — 안 열렸다는 것을 **말해 준다.**
        self.assertFalse(me["prefs_surface_open"])

    def test_does_not_leak_the_other_tenant(self) -> None:
        """B 의 규칙은 A 의 「내 정보」에 **한 줄도** 오지 않는다."""
        from kernels.k2_notify import my_notify_reach

        me = my_notify_reach(scope=self.scope_a)
        self.assertNotIn(self.role_b.code, me["roles"])


# ═══════════════════════════════════════════════════════════════════════════
# ④ 라우트 — **삼켜지지 않았는가** (HTTP 왕복)
# ═══════════════════════════════════════════════════════════════════════════
class NotifyRuleRouteWiringTest(DsmFixture):
    """`/settings/notify-rules/*` 세 조각이 405 가 아니라 **실제 판정**을 내는가.

    ⚠ 두 조각(`/settings/notify-rules`)이면 `api.py` 의 `GET /settings/{domain}` 이
      삼켜 GET 501 · POST 405 다. 이 시험이 그 함정을 지킨다.
    """

    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def _admin_user(self):
        Role = apps.get_model("role", "Role")
        role, _ = Role.objects.get_or_create(
            code="admin", defaults={"role_name": "admin"})
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

    def test_list_route_is_not_swallowed(self) -> None:
        """★ 200 이어야 한다. **405·501 이면 삼켜진 것**이다."""
        admin = self._admin_user()
        resp = self.client.get("/api/dsm/settings/notify-rules/list",
                               **self._bearer(admin), **NO_CACHE)
        self.assertNotIn(
            resp.status_code, (405, 501),
            "라우트가 `GET /settings/{domain}` 에 삼켜졌습니다 — 경로를 세 조각으로 두십시오.")
        self.assertEqual(200, resp.status_code,
                         (resp.content or b"")[:400].decode("utf-8", "replace"))
        body = json.loads(resp.content.decode("utf-8"))
        for key in ("severities", "rules", "channels", "critical_blocked"):
            self.assertIn(key, body)

    def test_save_route_is_not_swallowed_and_refuses_zero_critical(self) -> None:
        """★ 저장 문이 살아 있고, **심각 0명을 409 로** 거절하는가."""
        admin = self._admin_user()
        # 이 픽스처(`DsmFixture`)의 심각 규칙은 role_a 하나다 — 그것을 끄려 한다.
        Rule = apps.get_model("stream_monitors", "NotificationRule")
        rule = Rule._base_manager.filter(severity="critical", group=self.group_a).first()
        self.assertIsNotNone(rule, "전제가 깨졌습니다 — 심각 규칙이 없습니다.")

        resp = self.client.post(
            "/api/dsm/settings/notify-rules/save"
            "?severity=critical&role_code=%s&channels=email&is_active=false&rule_id=%s"
            % (self.role_a.code, rule.pk),
            **self._bearer(admin), **NO_CACHE)
        self.assertNotIn(resp.status_code, (405, 501), "저장 문이 삼켜졌습니다.")
        self.assertEqual(
            409, resp.status_code,
            (resp.content or b"")[:400].decode("utf-8", "replace"))
        rule.refresh_from_db()
        self.assertTrue(rule.is_active, "409 를 냈는데 행은 꺼졌습니다 — 되돌림 실패.")

    def test_test_send_route_reports_the_drill_channel(self) -> None:
        admin = self._admin_user()
        resp = self.client.post(
            "/api/dsm/settings/notify-rules/test?severity=critical",
            **self._bearer(admin), **NO_CACHE)
        self.assertNotIn(resp.status_code, (405, 501), "시험 발송 문이 삼켜졌습니다.")
        self.assertEqual(200, resp.status_code,
                         (resp.content or b"")[:400].decode("utf-8", "replace"))
        body = json.loads(resp.content.decode("utf-8"))
        self.assertEqual("log", body["channel"])
        self.assertFalse(body["reaches_people"])

    def test_a_plain_role_cannot_read_or_save(self) -> None:
        """★ 대조군 — 역할 없는 계정은 403. `guard_setting` 이 유일한 문지기다."""
        resp = self.client.get("/api/dsm/settings/notify-rules/list",
                               **self._bearer(self.user_b), **NO_CACHE)
        self.assertEqual(403, resp.status_code,
                         (resp.content or b"")[:300].decode("utf-8", "replace"))

    def test_anonymous_gets_401_not_403(self) -> None:
        resp = self.client.get("/api/dsm/settings/notify-rules/list", **NO_CACHE)
        self.assertEqual(401, resp.status_code)

    def test_me_route_is_open_to_any_logged_in_person(self) -> None:
        """★ 「내 정보」에는 `guard_setting` 이 **없다** — 관제요원도 자기 것을 본다.

        관리자만 지나게 하면 온보딩 U1 #7 「내 정보 확인」이 영영 안 닫힌다.
        """
        resp = self.client.get("/api/dsm/me", **self._bearer(self.user_a), **NO_CACHE)
        self.assertNotIn(resp.status_code, (405, 501), "`/me` 가 삼켜졌습니다.")
        self.assertEqual(200, resp.status_code,
                         (resp.content or b"")[:400].decode("utf-8", "replace"))
        body = json.loads(resp.content.decode("utf-8"))
        self.assertEqual(self.user_a.pk, body["user_id"])
        self.assertFalse(body["prefs_surface_open"])

    def test_me_is_anonymous_401(self) -> None:
        resp = self.client.get("/api/dsm/me", **NO_CACHE)
        self.assertEqual(401, resp.status_code)
