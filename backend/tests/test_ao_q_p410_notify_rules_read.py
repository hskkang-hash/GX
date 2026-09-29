# -*- coding: utf-8 -*-
"""P-410 — U2 관제팀장(`fire_admin`)에게 알림 규칙 **읽기**를 연다 (턴 AO · 차선 Q).

무엇이 문제였나
---------------
온보딩 U2#16 「알림 규칙 확인」(`/dsm/notify` → `GET /api/dsm/settings/notify-rules/list`)
을 `gxseed_u2_manager`(역할 `fire_admin`)로 누르면 **403** 이었다
(`docs/agent/evidence/P-118/click_completes.json::observations.U2#16`).

문은 하나다 — `backend/apps/dsm/api_u56.py::notify_rules_list` 가 부르는
`backend/apps/dsm/services.py::guard_setting` → `_decide()`. 그 함수는 전역
관리자·테넌트 관리자만 통과시켰다. `fire_admin`(U2 관제팀장)은 둘 다 아니다.

고친 것 — **행위 하나만, 문자열을 정확히 맞춰서**
--------------------------------------------------
`_decide()` 에 예외를 한 줄 더했다: `action == "read:notify-rules"` 이고 행위자가
`config.k3_roles.K3_ROLE_MANAGERS`(`fire_admin` · `surveillance_order`) 역할을 가지면
통과. **접두어 `"read:"` 전부를 열지 않는다** — 그러면 `read:system:storage` ·
`read:system:backup-receipts` · `read:inbound-api-key:scopes:...` ·
`setting_overview()` 가 내는 `f"read:{domain}"`(들어오는 키 설정 영역 포함)까지 같이 열린다.
그것들은 이번 청구 밖이다. 쓰기(`write:notify-rules:...`)는 그대로 관리자만이다.

이 시험이 묻는 것 넷
--------------------
① U2(`fire_admin`) 는 `read:notify-rules` 를 **지난다**(양성 대조 — 고친 것 자체).
② U2 는 `write:notify-rules:...` 는 **여전히 막힌다**(넓힌 쪽이 쓰기까지 안 샜다).
③ U2 는 **다른** `read:` 행위(`read:zones` · `read:system:storage`)는 **여전히
   막힌다**(접두어로 넓어지지 않았다 — 가장 위험한 회귀).
④ HTTP 왕복 — 실제 라우트(`GET /api/dsm/settings/notify-rules/list`)가 U2 에게
   200 을, 관리자 아닌 역할 없는 계정에게는 그대로 403 을 낸다(D-210 — 함수가
   아니라 문을 두드린다).

캐시 처리: 우회(`tests.no_cache.NO_CACHE`) — 관문을 재는 시험이 캐시를 재면 안 된다.
"""
from __future__ import annotations

import contextlib

from django.apps import apps
from django.test import TestCase

from tests.no_cache import NO_CACHE
from tests.test_api_contract import _bearer

PASSWORD = "test-only-not-a-secret"


def _forget_leftover_request() -> None:
    """스레드에 남은 요청을 지운다 (MEMORY: 스레드에 남은 요청이 거짓 초록을 만든다)."""
    with contextlib.suppress(Exception):
        from core.middleware.refresh_token import thread_local

        thread_local.request = None


class _P410Fixture(TestCase):
    """관제팀장(`fire_admin`) 하나 · 역할 없는 계정 하나 · 각자의 테넌트."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        _forget_leftover_request()
        UserGroup = apps.get_model("user", "UserGroup")
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")

        cls.group = UserGroup.objects.create(name="p410-tenant")
        UserGroup.objects.filter(pk=cls.group.pk).update(created_by=None)

        cls.fire_admin_role = Role.objects.create(
            role_name="p410_fire_admin", code="fire_admin")

        cls.u2_manager = CoreUser.objects.create_user(
            username="p410_u2_manager", password=PASSWORD, is_active=True,
            email="p410_u2_manager@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: cls.u2_manager, "group": cls.group})
        cls.u2_manager.roles.add(cls.fire_admin_role)

        cls.no_role_user = CoreUser.objects.create_user(
            username="p410_no_role", password=PASSWORD, is_active=True,
            email="p410_no_role@test.invalid")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: cls.no_role_user, "group": cls.group})

        from common.tenant_scope import TenantScope

        cls.scope_u2 = TenantScope.of(cls.u2_manager)
        cls.scope_no_role = TenantScope.of(cls.no_role_user)

    def setUp(self) -> None:
        _forget_leftover_request()

    def tearDown(self) -> None:
        _forget_leftover_request()


# ═══════════════════════════════════════════════════════════════════════════
# ①②③ — 함수 수준 (`guard_setting` 직접)
# ═══════════════════════════════════════════════════════════════════════════
class NotifyRulesReadGateTest(_P410Fixture):
    def test_u2_manager_now_passes_the_exact_read_action(self) -> None:
        """① 양성 대조 — 고친 그 행위 문자열, 그 역할."""
        from apps.dsm.services import guard_setting

        access = guard_setting(scope=self.scope_u2, action="read:notify-rules",
                               api_method="GET")
        self.assertTrue(access.allowed, access.reason)

    def test_u2_manager_still_blocked_from_writing_rules(self) -> None:
        """② 넓힌 쪽이 쓰기로 새지 않았다."""
        from apps.dsm.services import guard_setting

        access = guard_setting(
            scope=self.scope_u2, action="write:notify-rules:critical:fire_admin",
            api_method="POST")
        self.assertFalse(access.allowed)

    def test_u2_manager_still_blocked_from_unrelated_read_actions(self) -> None:
        """③ **가장 중요한 회귀 방지** — 접두어 `read:` 전체가 아니라
        `read:notify-rules` 딱 그 문자열만 열었다. 하나라도 새면(예: 저장용량·
        백업·API 키 스코프) 그것은 이번 절이 요청하지 않은 확장이다."""
        from apps.dsm.services import SETTING_DOMAINS, guard_setting

        #: 영역 이름은 제품 정본(`SETTING_DOMAINS`)에서 받는다 — 손으로 적지 않는다(턴 AO 병합).
        domain_reads = tuple("read:%s" % d for d in SETTING_DOMAINS
                             if "read:%s" % d != "read:notify-rules")
        for other_action in domain_reads + ("read:system:storage", "read:system:backup-receipts",
                                            "read:inbound-api-key:scopes:1"):
            with self.subTest(action=other_action):
                access = guard_setting(scope=self.scope_u2, action=other_action,
                                       api_method="GET")
                self.assertFalse(access.allowed,
                                 "%s 가 열렸다 — read: 접두어 전체가 샜다" % other_action)

    def test_role_zero_is_still_blocked_from_the_notify_rules_read(self) -> None:
        """음성 대조 — 역할이 아예 없으면 여전히 막힌다(전역/테넌트 관리자도
        `fire_admin` 도 아니다)."""
        from apps.dsm.services import guard_setting

        access = guard_setting(scope=self.scope_no_role, action="read:notify-rules",
                               api_method="GET")
        self.assertFalse(access.allowed)


# ═══════════════════════════════════════════════════════════════════════════
# ④ — 문을 두드린다 (D-210)
# ═══════════════════════════════════════════════════════════════════════════
class NotifyRulesReadRouteTest(_P410Fixture):
    def test_u2_manager_gets_200_over_http(self) -> None:
        resp = self.client.get("/api/dsm/settings/notify-rules/list",
                               **_bearer(self.u2_manager), **NO_CACHE)
        self.assertEqual(200, resp.status_code,
                         (resp.content or b"")[:300].decode("utf-8", "replace"))

    def test_role_zero_still_gets_403_over_http(self) -> None:
        """되돌리지 않은 것의 증거 — 역할 없는 계정은 여전히 막힌다."""
        resp = self.client.get("/api/dsm/settings/notify-rules/list",
                               **_bearer(self.no_role_user), **NO_CACHE)
        self.assertEqual(403, resp.status_code)

    def test_anonymous_still_gets_401_not_403(self) -> None:
        resp = self.client.get("/api/dsm/settings/notify-rules/list", **NO_CACHE)
        self.assertEqual(401, resp.status_code)
