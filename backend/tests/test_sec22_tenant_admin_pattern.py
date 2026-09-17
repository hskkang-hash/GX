# -*- coding: utf-8 -*-
"""SEC-22 — `tenant_admin_<n>` 은 **이름 열거가 아니라 패턴**으로 알아본다 (D-478 · 턴 T · 차선 F).

무엇이 문제였나 [실측 · D-478 · `scripts/verify_seed_roles.py` exit 1]
------------------------------------------------------------------
`tenant_admin_4` 가 「매핑도 선언도 없다」로 빨개졌다. 처방으로 그 이름을 목록에
적으면 다음 테넌트가 `tenant_admin_5` 를 만들고 같은 빨강이 다시 뜬다 —
**이름으로 막으면 테넌트 수만큼 구멍이 는다.**

어디서 문자열로 비교했나 [grep 실측 2026-09-17]
---------------------------------------------
    common/tenant_roles.py:120     `tenant_admin_role_code(group.id) in codes`   ← 글자 일치 (판정식)
    common/role_request.py:112     `tenant_admin_role_code(group.id)` 로 역할을 **찾는다** (조회 · 판정 아님)
    kernels/k3_dashboard/services.py:102  `mapping[c] for c in codes if c in mapping`  ← 글자 일치 (프리셋)
    scripts/verify_seed_roles.py:259      `any(c in mapping for c in codes)`         ← 글자 일치 (판정기)
판정식은 `common/tenant_roles.py` 한 곳으로 모았다 — `is_tenant_admin_role_code(code)` ·
`tenant_admin_role_group_id(code)`. 프리셋·판정기는 이 함수를 **부르면** 된다(등록 요청).

이 파일이 못박는 것 넷
----------------------
  1) 패턴 — `tenant_admin_7` 허용 · `tenant_admin` 허용 ·
     `tenant_administrator_x` · `xtenant_admin_1` · `tenant_admin_` · `tenant_admin_a` 거절
  2) 번호 — `tenant_admin_7` → 7 · `tenant_admin` → None
  3) 경계 — 사람 판정 `is_tenant_admin(user)` 은 **자기 테넌트 번호**만 통과시킨다:
     A 소속 사람이 `tenant_admin_<A>` 면 참 · `tenant_admin_<B>` 면 거짓 · 둘 다 아니면 거짓
  4) 판정식이 한 곳이다 — `is_tenant_admin` 이 접두사를 다시 적지 않고 패턴 함수를 부른다

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105 · D-224)
    skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import contextlib
import inspect

from django.apps import apps
from django.test import SimpleTestCase, TestCase, override_settings

from common import tenant_roles
from common.tenant_roles import (
    is_tenant_admin,
    is_tenant_admin_role_code,
    tenant_admin_role_code,
    tenant_admin_role_group_id,
)


class TenantAdminRoleCodePatternTest(SimpleTestCase):
    def test_accepts_prefix_and_numbered(self):
        for code in ("tenant_admin", "tenant_admin_7", "tenant_admin_4", "tenant_admin_12345"):
            self.assertTrue(is_tenant_admin_role_code(code), code)

    def test_rejects_lookalikes(self):
        for code in ("tenant_administrator_x", "xtenant_admin_1", "tenant_admin_",
                     "tenant_admin_a", "tenant_admin_7_x", "TENANT_ADMIN_7",
                     " tenant_admin_7", "tenant_admin_7 ", "", None, 7):
            self.assertFalse(is_tenant_admin_role_code(code), repr(code))

    def test_group_id_is_read_from_the_code(self):
        self.assertEqual(tenant_admin_role_group_id("tenant_admin_7"), 7)
        self.assertIsNone(tenant_admin_role_group_id("tenant_admin"))
        self.assertIsNone(tenant_admin_role_group_id("xtenant_admin_1"))

    def test_code_builder_and_pattern_agree(self):
        """만드는 쪽과 알아보는 쪽이 같은 규약이다 — 갈리면 만든 역할을 못 알아본다."""
        for gid in (1, 4, 99):
            code = tenant_admin_role_code(gid)
            self.assertTrue(is_tenant_admin_role_code(code), code)
            self.assertEqual(tenant_admin_role_group_id(code), gid)

    @override_settings(TENANT_ADMIN_ROLE_PREFIX="ops_lead")
    def test_prefix_comes_from_settings(self):
        self.assertTrue(is_tenant_admin_role_code("ops_lead_3"))
        self.assertFalse(is_tenant_admin_role_code("tenant_admin_3"))

    def test_decision_lives_in_one_place(self):
        """`is_tenant_admin` 이 접두사 문자열을 다시 적지 않는다 (D-212)."""
        src = inspect.getsource(tenant_roles.is_tenant_admin)
        self.assertIn("is_tenant_admin_role_code", src)
        self.assertNotIn('"tenant_admin', src)


class TenantAdminBoundaryTest(TestCase):
    """사람 판정 — 패턴이 맞아도 **남의 테넌트 번호**면 거짓이다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        UserGroup = apps.get_model("user", "UserGroup")
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        cls.group_a = UserGroup.objects.create(name="sec22-tenant-A")
        cls.group_b = UserGroup.objects.create(name="sec22-tenant-B")
        UserGroup.objects.filter(pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

    @staticmethod
    def _role(code):
        Role = apps.get_model("role", "Role")
        return Role.objects.create(role_name=code, code=code)

    @classmethod
    def _user(cls, username, group, *roles):
        CoreUser = apps.get_model("user", "CoreUser")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": group})
        for r in roles:
            user.roles.add(r)
        return user

    def test_own_tenant_number_passes(self):
        u = self._user("sec22_own", self.group_a, self._role(tenant_admin_role_code(self.group_a.pk)))
        self.assertTrue(is_tenant_admin(u))

    def test_other_tenant_number_is_rejected(self):
        u = self._user("sec22_other", self.group_a, self._role(tenant_admin_role_code(self.group_b.pk)))
        self.assertFalse(is_tenant_admin(u))

    def test_lookalike_is_rejected(self):
        u = self._user("sec22_look", self.group_a,
                       self._role(f"xtenant_admin_{self.group_a.pk}"),
                       self._role("tenant_administrator_x"))
        self.assertFalse(is_tenant_admin(u))

    def test_no_role_is_rejected(self):
        u = self._user("sec22_none", self.group_a)
        self.assertFalse(is_tenant_admin(u))
