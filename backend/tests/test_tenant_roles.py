# -*- coding: utf-8 -*-
"""전역/테넌트 역할 판정 단위시험 (W0-16).

DB 를 쓰지 않는다. 판정식만 검사한다 — `tenant_roles` 는 `settings` 와 `user.roles`
두 입력만 보므로 가짜 객체로 전부 덮을 수 있다. dj-core 설치본이나 테스트 DB
생성(P-LOCAL-1: dj-core 1.1.6 은 마이그레이션을 0부터 못 쌓는다)에 의존하지 않는
것이 이 시험의 요점이다.

무엇을 지키는 시험인가
    "레거시 superuser 역할을 전역으로 인정하지 않는다" 는 전환의 핵심이고,
    그것을 되돌리는 실수(전환 플래그를 켠 채 배포)를 잡는 것이 여기다.
"""
from __future__ import annotations

from django.test import SimpleTestCase, override_settings

from common.tenant_roles import (
    global_admin_reason,
    is_global_admin,
    tenant_admin_role_code,
    trusts_legacy_superuser,
)


class _Role:
    def __init__(self, code: str):
        self.code = code


class _Roles:
    """`user.roles` 대역 — `values_list('code', flat=True)` 만 쓴다."""

    def __init__(self, codes):
        self._codes = list(codes)

    def values_list(self, *_args, **_kwargs):
        return list(self._codes)

    def all(self):
        return [_Role(c) for c in self._codes]


class _User:
    def __init__(self, codes=(), is_superuser=False, authenticated=True):
        self.roles = _Roles(codes)
        self.is_superuser = is_superuser
        self.is_authenticated = authenticated


GLOBAL = ["gaion_global_admin"]


@override_settings(TENANT_GLOBAL_ADMIN_ROLE_CODES=GLOBAL, TENANT_TRUST_LEGACY_SUPERUSER=True)
class LegacyTrustedTest(SimpleTestCase):
    """전환기 — 레거시 역할이 아직 전역이다 (무중단 · D-243 ②)."""

    def test_legacy_superuser_is_global_while_trusted(self):
        self.assertTrue(is_global_admin(_User(["superuser"])))
        self.assertEqual(global_admin_reason(_User(["superuser"])), "legacy-superuser")

    def test_flag_reports_transition_state(self):
        self.assertTrue(trusts_legacy_superuser())


@override_settings(TENANT_GLOBAL_ADMIN_ROLE_CODES=GLOBAL, TENANT_TRUST_LEGACY_SUPERUSER=False)
class LegacyRevokedTest(SimpleTestCase):
    """전환 후 — 레거시 역할은 더 이상 전역이 아니다. **이 시험이 회귀를 막는다.**"""

    def test_legacy_superuser_is_not_global(self):
        self.assertFalse(is_global_admin(_User(["superuser"])))
        self.assertIsNone(global_admin_reason(_User(["superuser"])))

    def test_explicit_global_role_is_global(self):
        user = _User(["gaion_global_admin"])
        self.assertTrue(is_global_admin(user))
        self.assertEqual(global_admin_reason(user), "role:gaion_global_admin")

    def test_db_flag_still_global(self):
        # Django 원형. 실계정에는 0명이지만 판정에서 빠지면 관리자가 잠긴다.
        self.assertTrue(is_global_admin(_User([], is_superuser=True)))
        self.assertEqual(global_admin_reason(_User([], is_superuser=True)), "db-flag")

    def test_tenant_admin_is_not_global(self):
        self.assertFalse(is_global_admin(_User(["tenant_admin_6"])))

    def test_anonymous_is_not_global(self):
        self.assertFalse(is_global_admin(_User(["superuser"], authenticated=False)))
        self.assertFalse(is_global_admin(None))


class TenantAdminCodeTest(SimpleTestCase):
    @override_settings(TENANT_ADMIN_ROLE_PREFIX="tenant_admin")
    def test_code_convention(self):
        self.assertEqual(tenant_admin_role_code(6), "tenant_admin_6")

    @override_settings(TENANT_ADMIN_ROLE_PREFIX="ops")
    def test_prefix_is_configurable(self):
        self.assertEqual(tenant_admin_role_code(6), "ops_6")
