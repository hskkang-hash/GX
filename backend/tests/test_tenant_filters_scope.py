# -*- coding: utf-8 -*-
"""테넌트 필터의 '경계를 넘어도 되는가' 판정 시험 (W0-14 · D-247).

무엇을 지키는 시험인가
    `common/tenant_filters` 에는 dj-core `core/base.py:308` 의 우회를 글자 그대로
    복제한 `is_superuser()` 가 있었다. 그래서 뷰를 좁혀도 통과 대상이 같았다.
    이제 판정은 `common/tenant_roles.is_global_admin()` **한 곳**이 낸다.

    이 시험이 잡는 회귀는 둘이다:
      ① 판정식이 이 파일에 되살아나는 것 (복사본 하나 = 우회 지점 하나 · D-212)
      ② 회수 플래그(`TENANT_TRUST_LEGACY_SUPERUSER=False`)를 내렸는데도
         레거시 `superuser` 역할이 필터를 통과하는 것

DB 를 쓰지 않는다 — queryset 은 대역이다. dj-core 1.1.6 은 마이그레이션을 0부터
쌓지 못해(P-LOCAL-1) test DB 생성에 의존하는 시험은 이 환경에서 돌지 않는다.
"""
from __future__ import annotations

import inspect
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from common import tenant_filters
from common.tenant_filters import filter_by_group_field, filter_users_by_group

GLOBAL_ROLES = ["gaion_global_admin"]


class _Roles:
    def __init__(self, codes):
        self._codes = list(codes)

    def values_list(self, *_args, **_kwargs):
        return list(self._codes)


class _User:
    """`is_authenticated` · `is_superuser` · `roles` · `userprofilelink` 만 본다."""

    def __init__(self, codes=(), is_superuser=False, group=None):
        self.roles = _Roles(codes)
        self.is_superuser = is_superuser
        self.is_authenticated = True
        self.userprofilelink = _Link(group) if group is not None else None


class _Link:
    def __init__(self, group):
        self.group = group


class _Group:
    def __init__(self, pk):
        self.id = pk


class _QuerySet:
    """`filter()` / `none()` 이 무엇으로 불렸는지만 기록하는 대역."""

    def __init__(self):
        self.filtered_with = None
        self.is_none = False

    def filter(self, **kwargs):
        out = _QuerySet()
        out.filtered_with = kwargs
        return out

    def none(self):
        out = _QuerySet()
        out.is_none = True
        return out


@override_settings(
    TENANT_GLOBAL_ADMIN_ROLE_CODES=GLOBAL_ROLES, TENANT_TRUST_LEGACY_SUPERUSER=False
)
class AfterRevocationTest(SimpleTestCase):
    """회수 완료 상태 — 레거시 역할은 더 이상 경계를 넘지 못한다."""

    def test_legacy_superuser_is_narrowed_to_own_tenant(self):
        user = _User(["superuser"], group=_Group(7))
        out = filter_users_by_group(_QuerySet(), user)
        self.assertEqual({"userprofilelink__group": user.userprofilelink.group}, out.filtered_with)

    def test_legacy_superuser_without_group_gets_nothing(self):
        """소속이 없으면 여는 쪽이 아니라 닫는 쪽이 기본값이다."""
        out = filter_users_by_group(_QuerySet(), _User(["superuser"]))
        self.assertTrue(out.is_none)

    def test_group_field_filter_also_narrows(self):
        user = _User(["superuser"], group=_Group(7))
        out = filter_by_group_field(_QuerySet(), user)
        self.assertEqual({"group": user.userprofilelink.group}, out.filtered_with)

    def test_explicit_global_role_still_passes(self):
        """전역(GAION 운영) 역할은 통과한다 — 그것이 이 역할의 정의다."""
        out = filter_users_by_group(_QuerySet(), _User(GLOBAL_ROLES, group=_Group(7)))
        self.assertIsNone(out.filtered_with)
        self.assertFalse(out.is_none)


@override_settings(
    TENANT_GLOBAL_ADMIN_ROLE_CODES=GLOBAL_ROLES, TENANT_TRUST_LEGACY_SUPERUSER=True
)
class DuringTransitionTest(SimpleTestCase):
    """전환기 — 무중단을 위해 레거시 역할이 아직 통과한다 (D-243 ②)."""

    def test_legacy_superuser_still_passes_while_trusted(self):
        out = filter_users_by_group(_QuerySet(), _User(["superuser"], group=_Group(7)))
        self.assertIsNone(out.filtered_with)
        self.assertFalse(out.is_none)

    def test_plain_user_is_narrowed_even_during_transition(self):
        user = _User(["operator"], group=_Group(3))
        out = filter_users_by_group(_QuerySet(), user)
        self.assertEqual({"userprofilelink__group": user.userprofilelink.group}, out.filtered_with)


class SingleSourceOfJudgementTest(SimpleTestCase):
    """판정식이 이 모듈에 되살아나면 실패한다 (D-212)."""

    def test_module_has_no_local_superuser_predicate(self):
        source = Path(inspect.getfile(tenant_filters)).read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines()
            if not line.lstrip().startswith("#")
        )
        self.assertNotIn(
            "def is_superuser", code,
            "경계 판정을 이 모듈에 다시 정의했습니다. "
            "common/tenant_roles.is_global_admin() 하나만 씁니다 (D-212 · W0-14).",
        )
        self.assertNotIn(
            'code", None) == "superuser"', code,
            "레거시 역할 문자열 판정이 되살아났습니다. tenant_roles 를 통해서만 봅니다.",
        )
