# -*- coding: utf-8 -*-
"""D-371 ① — **역할이 보는 것만 보이는가.** 화면 셋에 역할 4종으로 들어가 본다.

지시가 요구한 것: *"각 화면에 **역할 4종으로 접근해 보는 시험**을 붙여라.
보이면 안 되는 것이 안 보이는지(**부작위**)."*

★ 왜 화면이 아니라 여기서 재나 (D-347 · DA-03 §3-4 불변 규칙 1)
----------------------------------------------------------------
    **화면에서 감추는 것은 통제가 아니다.**

화면이 탭을 안 그려도 API 는 열려 있을 수 있고, 열려 있으면 그것이 통제의 부재다.
그래서 역할 시험은 **서버 판정**(`widget_permission` · 라우트)에 건다.
화면 캡처는 그 위에 얹는 별개의 증거이고, 지금은 브라우저 구동체가 없어 0장이다
(`DA-05/blockers.yaml :: BROWSER_E2E_HARNESS`) — **0장인 것과 안 막힌 것은 다르다.**

★ 이 파일이 대조하는 두 벌 (D-369)
----------------------------------
    정본     docs/design/DA-03_화면설계안_v1.0.md §3-4 표
    배선     backend/config/k3_roles.py

아래 `DA03_MATRIX` 는 **정본을 손으로 옮긴 셋째 벌**이다. 셋째 벌을 굳이 두는 이유는
하나 — 배선을 고치면 이 시험이 빨개져야 하기 때문이다. 배선에서 값을 읽어 오면
「배선이 배선과 같다」를 확인하게 되고, 그런 시험은 무엇도 잡지 못한다.
"""
from __future__ import annotations

import contextlib

from django.apps import apps
from django.test import TestCase, override_settings

from config.k3_roles import (
    K3_ROLE_EXECUTIVES,
    K3_ROLE_MANAGERS,
    K3_ROLE_OPERATORS,
    K3_ROLE_SYSOPS,
    K3_UNMAPPED_BY_DECISION,
)
from kernels.k3_dashboard import SETTING_WIDGETS, Visibility, get_preset, widget_permission

V, E, H = Visibility.VISIBLE, Visibility.EDITABLE, Visibility.HIDDEN

#: DA-03 §3-4 표를 **손으로** 옮긴 것. 배선에서 읽지 않는다 (위 머리말).
#:   `–` = HIDDEN · `V` = 볼 수 있다 · `E` = 편집할 수 있다
DA03_MATRIX: dict[str, dict[str, Visibility]] = {
    "관제요원":        {"danger_zone": V, "threshold": H, "severity_rule": V,
                        "recipient_group": H, "sdn_link": H, "role_management": H,
                        "api_key": H, "audit_log": H},
    "재난관제 관리자": {"danger_zone": E, "threshold": E, "severity_rule": E,
                        "recipient_group": E, "sdn_link": V, "role_management": V,
                        "api_key": H, "audit_log": V},
    "기관장/부서장":   {"danger_zone": V, "threshold": H, "severity_rule": V,
                        "recipient_group": V, "sdn_link": H, "role_management": H,
                        "api_key": H, "audit_log": V},
    "운영자":          {"danger_zone": V, "threshold": V, "severity_rule": H,
                        "recipient_group": H, "sdn_link": E, "role_management": E,
                        "api_key": E, "audit_log": V},
}

#: 역할 4종 — 지시가 말한 넷. 넷째는 **매핑이 없는 사람**이다.
#: 「매핑을 깜빡한 사람」이 무엇을 보는가가 이 시험에서 가장 중요한 칸이다.
FOUR_ROLES = (
    ("관제요원", K3_ROLE_OPERATORS[0], "OPERATOR", True),
    ("재난관제 관리자", K3_ROLE_MANAGERS[0], "MANAGER", True),
    ("기관장/부서장", K3_ROLE_EXECUTIVES[0], "EXECUTIVE", True),
    ("운영자", K3_ROLE_SYSOPS[0], "MANAGER", True),
)
UNMAPPED_ROLE = next(iter(K3_UNMAPPED_BY_DECISION))


class RoleFrameFixture(TestCase):
    """역할 하나씩 붙은 사용자 다섯. 전부 **같은 테넌트** — 이 시험은 격리가 아니라
    **역할**을 잰다. 격리는 `test_tenant_isolation.py` 가 따로 잰다(축을 섞지 않는다)."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        UserGroup = apps.get_model("user", "UserGroup")
        cls.group = UserGroup.objects.create(name="k3-role-tenant")
        UserGroup.objects.filter(pk=cls.group.pk).update(created_by=None)

        cls.users: dict[str, object] = {}
        for label, code, _preset, _matched in FOUR_ROLES:
            cls.users[code] = cls._make_user(f"k3_{code}", code)
        cls.users[UNMAPPED_ROLE] = cls._make_user("k3_unmapped", UNMAPPED_ROLE)

    @classmethod
    def _make_user(cls, username: str, role_code: str):
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid",
        )
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_model = link_field.related_model
        link_model.objects.create(
            **{link_field.remote_field.name: user, "group": cls.group})
        role, _ = Role._base_manager.get_or_create(
            code=role_code, defaults={"role_name": role_code})
        user.roles.add(role)
        return user

    def _scope(self, code: str):
        from common.tenant_scope import TenantScope

        return TenantScope.of(self.users[code])


class PresetRoutingTest(RoleFrameFixture):
    """① 로그인 직후 **어느 화면으로 떨어지는가** (U3 — 도달 클릭 ≤ 2)."""

    def test_each_role_lands_on_its_preset(self) -> None:
        for label, code, expected, matched in FOUR_ROLES:
            with self.subTest(role=label):
                view = get_preset(scope=self._scope(code))
                self.assertEqual(view.preset, expected,
                                 f"{label}({code}) 가 {view.preset} 으로 떨어졌다")
                self.assertTrue(view.matched, f"{label} 매핑을 못 찾았다: {view.reason}")

    def test_unmapped_role_falls_to_the_narrowest_and_says_so(self) -> None:
        """★ 매핑 없는 사람은 **가장 좁은 화면**으로 떨어지고, 떨어진 것을 말한다.

        넓은 쪽으로 떨어뜨리면 역할을 못 알아본 사람이 기관장 화면을 본다.
        좁은 쪽으로 떨어뜨리면 못 보는 것이 생기고 **그것은 눈에 띄어 신고된다** —
        두 실패 중 눈에 띄는 쪽을 고른다 (4원칙 ①).

        그리고 `matched=False` 여야 한다. 참으로 두면 「설정을 안 했는데도 잘
        돌아간다」가 되고 그 상태가 운영에 그대로 나간다 (D-290).
        """
        view = get_preset(scope=self._scope(UNMAPPED_ROLE))
        self.assertEqual(view.preset, "OPERATOR")
        self.assertFalse(view.matched,
                         "매핑이 없는데 찾았다고 말한다 — 설정 누락이 안 보이게 된다")


class WidgetVisibilityTest(RoleFrameFixture):
    """② **보이면 안 되는 것이 안 보이는가** — 부작위 (D-300)."""

    def test_matrix_matches_da03_exactly(self) -> None:
        """32칸(위젯 8 × 역할 4)을 **한 칸씩** 정본과 대조한다."""
        for label, code, _preset, _matched in FOUR_ROLES:
            expected_row = DA03_MATRIX[label]
            for widget in SETTING_WIDGETS:
                with self.subTest(role=label, widget=widget):
                    got = widget_permission(widget, scope=self._scope(code))
                    self.assertEqual(
                        got, expected_row[widget],
                        f"DA-03 §3-4 는 {label}×{widget} 를 "
                        f"{expected_row[widget].value} 라고 적었는데 "
                        f"코드가 {got.value} 를 낸다")

    def test_operator_cannot_see_the_six_management_widgets(self) -> None:
        """★ 부작위 — 관제요원에게 **없어야 하는 여섯**이 정말 없는가.

        하나라도 보이면 그것은 「관제요원이 임계값을 본다」이고, 임계값이 보이면
        다음 화면에서 고칠 수 있는지가 물어진다. 안 보이는 것이 먼저다.
        """
        hidden_for_operator = ("threshold", "recipient_group", "sdn_link",
                               "role_management", "api_key", "audit_log")
        scope = self._scope(K3_ROLE_OPERATORS[0])
        for widget in hidden_for_operator:
            with self.subTest(widget=widget):
                self.assertIs(widget_permission(widget, scope=scope), Visibility.HIDDEN)

    def test_only_the_sysop_can_edit_api_keys(self) -> None:
        """★ 부작위 — API Key 발급은 **운영자 하나**다 (DA-03 §3-4).

        키를 발급할 수 있으면 그 키로 F-05 진입면에 닿는다. 발급 면이 넓어지는 것은
        읽기 면이 넓어지는 것과 같은 일이다 (D-335).
        """
        for label, code, _p, _m in FOUR_ROLES:
            got = widget_permission("api_key", scope=self._scope(code))
            with self.subTest(role=label):
                if code in K3_ROLE_SYSOPS:
                    self.assertIs(got, Visibility.EDITABLE)
                else:
                    self.assertIsNot(
                        got, Visibility.EDITABLE,
                        f"{label} 가 API Key 를 발급할 수 있다 — DA-03 §3-4 위반")

    def test_unmapped_role_gets_no_edit_anywhere(self) -> None:
        """★ 매핑 없는 사람에게 **편집은 절대 안 난다** (`presets.py` 의 기본값 규약)."""
        scope = self._scope(UNMAPPED_ROLE)
        for widget in SETTING_WIDGETS:
            with self.subTest(widget=widget):
                self.assertIsNot(widget_permission(widget, scope=scope),
                                 Visibility.EDITABLE)


@override_settings(K3_ROLE_PRESET_MAP={}, K3_WIDGET_MATRIX={})
class UnwiredFrameTest(RoleFrameFixture):
    """③ **배선을 빼면 시험이 빨개지는가** — 양성 대조 (D-277).

    이 시험이 없으면 위의 초록이 「배선이 있어서 초록」인지 「원래 초록」인지
    구별되지 않는다. 배선 전 상태가 정확히 이 클래스가 그리는 그림이고,
    그 상태가 **⑦사용성이 두 턴 동안 0%p 였던 자리**다.
    """

    def test_without_wiring_everyone_lands_on_the_same_screen(self) -> None:
        for label, code, _preset, _matched in FOUR_ROLES:
            view = get_preset(scope=self._scope(code))
            with self.subTest(role=label):
                self.assertFalse(view.matched)
                self.assertEqual(view.preset, "OPERATOR")

    def test_without_wiring_nothing_is_hidden(self) -> None:
        """★ 배선이 없으면 **아무것도 안 숨는다** — 그것이 고쳐야 했던 상태다."""
        scope = self._scope(K3_ROLE_OPERATORS[0])
        for widget in SETTING_WIDGETS:
            with self.subTest(widget=widget):
                self.assertIs(widget_permission(widget, scope=scope), Visibility.VISIBLE)
