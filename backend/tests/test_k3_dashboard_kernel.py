# -*- coding: utf-8 -*-
"""K3 역할별 대시보드 프레임 — **이중 AC 시험** (DA-04 §2 K3).

    [F-09 계약] 5상태(기본/로딩/빈/오류/권한없음) 100% · 클릭→영상 3초
    [U3 상품]  역할별 대시보드 **도달 클릭 ≤ 2**

★ 이 파일에서 가장 중요한 시험은 **다섯 상태가 서로 안 섞이는가**이다.
  DA-03 §2-5: *"'빈'과 '오류'를 같은 문구로 쓰지 않는다. 데이터가 없는 것과 못 가져온
  것은 다른 사실이고, 관제요원의 다음 행동이 다르다 — 전자는 대기, 후자는 신고."*
  D-290 이 서버에서 말한 것을 화면 쪽에서 그대로 말한 문장이다.

두 번째로 중요한 것은 **"권한없음"이 격리를 대신하지 않는다**는 것이다.
DA-03 §3-4: *"화면에서 감추는 것은 통제가 아니다."*
"""
from __future__ import annotations

import contextlib

from django.apps import apps
from django.test import TestCase


class K3Fixture(TestCase):
    """테넌트 A/B · 각자의 대시보드와 패널 · 역할 하나씩."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        UserGroup = apps.get_model("user", "UserGroup")

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="k3-tenant-A")
        cls.group_b = UserGroup.objects.create(name="k3-tenant-B")
        UserGroup.objects.filter(pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.role_a = cls._own(cls._role("k3_operator_a"), cls.group_a)
        cls.role_b = cls._own(cls._role("k3_operator_b"), cls.group_b)
        cls.user_a = cls._user("k3_user_a", cls.group_a, cls.role_a)
        cls.user_b = cls._user("k3_user_b", cls.group_b, cls.role_b)

        cls.board_a = cls._board("k3-board-A", cls.group_a)
        cls.board_b = cls._board("k3-board-B", cls.group_b)
        cls.panel_a = cls._panel(cls.board_a, "A-패널", cls.group_a,
                                 config={"series": [1, 2, 3]})
        cls.panel_b = cls._panel(cls.board_b, "B-패널", cls.group_b,
                                 config={"series": [9]})

        from common.tenant_scope import TenantScope

        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)
        cls.scope_pipe = TenantScope.system(reason="K3 시험 — 화면 없는 호출 대조용")

    # ── 픽스처 도우미 ────────────────────────────────────────────────────
    @staticmethod
    def _own(obj, group):
        from kernels.k1_event.services import _owner_field

        if _owner_field(type(obj)) == "groups":
            obj.groups.set([group])
        else:
            obj.group = group
            obj.save(update_fields=["group"])
        return obj

    @classmethod
    def _role(cls, code):
        Role = apps.get_model("role", "Role")
        return Role.objects.create(role_name=code, code=code)

    @classmethod
    def _user(cls, username, group, role):
        CoreUser = apps.get_model("user", "CoreUser")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": group})
        user.roles.add(role)
        return user

    @classmethod
    def _board(cls, code, group):
        Dashboard = apps.get_model("dashboard", "Dashboard")
        return cls._own(Dashboard.objects.create(name=code, code=code), group)

    @classmethod
    def _panel(cls, board, title, group, *, config=None, panel_type="chart"):
        Panel = apps.get_model("dashboard", "DashboardPanel")
        return cls._own(Panel.objects.create(
            dashboard=board, panel_title=title, panel_type=panel_type,
            panel_config=config), group)


# ═══════════════════════════════════════════════════════════════════════════
# [U3 상품 AC] — 도달 클릭 ≤ 2
# ═══════════════════════════════════════════════════════════════════════════
class PresetRoutingTest(K3Fixture):
    """★ U3 의 답은 **프리셋 라우팅**이다 (DA-04 §2 K3)."""

    def test_preset_requires_no_choice_from_the_user(self) -> None:
        """[U3] 도달 클릭 **0**. 고르게 하는 순간 하나가 늘고, 그 하나가 여유분 전부다."""
        from kernels.k3_dashboard import get_preset

        view = get_preset(scope=self.scope_a)
        self.assertLessEqual(view.clicks_to_reach, 2,
                             "U3 는 도달 클릭 ≤ 2 입니다.")
        self.assertEqual(0, view.clicks_to_reach,
                         "프리셋이 로그인 직후 화면을 정하면 0 이어야 합니다 (DA-04 K3).")
        self.assertTrue(view.preset, "프리셋 이름이 비었습니다 — 갈 곳이 없습니다.")

    def test_unmapped_role_falls_back_to_the_narrowest_preset(self) -> None:
        """★ 모르면 **좁게** 보여 준다 (4원칙 ①).

        넓은 쪽으로 떨어뜨리면 역할을 못 알아본 사람이 기관장 화면을 봅니다.
        좁은 쪽이면 못 보는 것이 생기고, 그것은 **눈에 띄어 신고됩니다.**
        """
        from kernels.k3_dashboard import FALLBACK_PRESET, get_preset

        with self.settings(K3_ROLE_PRESET_MAP={}):
            view = get_preset(scope=self.scope_a)
        self.assertEqual(FALLBACK_PRESET.value, view.preset)
        self.assertFalse(
            view.matched,
            "매핑을 못 찾았는데 matched=True 입니다 — '설정을 안 했는데도 잘 돌아간다'가 "
            "되고 그 상태가 운영에 그대로 나갑니다 (D-290).")
        self.assertIn("P-K3-1", view.reason,
                      "왜 떨어졌는지와 어디서 풀리는지를 말하지 않습니다.")

    def test_mapped_role_is_reported_as_matched(self) -> None:
        """★ 양성 대조 — 매핑이 있으면 **찾아야 한다** (D-277).

        `matched` 가 늘 거짓이면 위의 시험은 아무것도 증명하지 않습니다.
        """
        from kernels.k3_dashboard import get_preset

        with self.settings(K3_ROLE_PRESET_MAP={"k3_operator_a": "MANAGER"}):
            view = get_preset(scope=self.scope_a)
        self.assertEqual("MANAGER", view.preset)
        self.assertTrue(view.matched, "매핑이 있는데 못 찾았습니다 — 판정기가 눈이 멀었습니다.")

    def test_multiple_roles_take_the_widest_preset(self) -> None:
        """역할을 겸한 사람은 **넓은 쪽**을 본다 — 좁히면 관리자가 관리자 화면을 못 본다."""
        from kernels.k3_dashboard import get_preset

        extra = self._own(self._role("k3_chief_a"), self.group_a)
        self.user_a.roles.add(extra)
        with self.settings(K3_ROLE_PRESET_MAP={"k3_operator_a": "OPERATOR",
                                               "k3_chief_a": "EXECUTIVE"}):
            view = get_preset(scope=self.scope_a)
        self.assertEqual("EXECUTIVE", view.preset)

    def test_preset_returns_no_other_tenants_data(self) -> None:
        """돌려주는 것은 프리셋 이름과 **자기 역할 코드**뿐이다 (KERNEL_PUBLIC 등재 근거)."""
        from kernels.k3_dashboard import get_preset

        view = get_preset(scope=self.scope_a)
        self.assertNotIn("k3_operator_b", view.role_codes,
                         "남의 테넌트 역할 코드가 섞였습니다.")
        for code in view.role_codes:
            self.assertIn(code, {"k3_operator_a", "k3_chief_a"},
                          f"요청자의 것이 아닌 역할 코드가 나왔습니다: {code}")

    def test_bad_preset_name_in_settings_is_refused_loudly(self) -> None:
        """설정 오타를 **조용히 버리지 않는다** — 버리면 '매핑했는데 안 먹는' 상태가 된다."""
        from kernels.k3_dashboard import get_preset

        with self.settings(K3_ROLE_PRESET_MAP={"k3_operator_a": "BOSS"}):
            with self.assertRaises(ValueError):
                get_preset(scope=self.scope_a)


# ═══════════════════════════════════════════════════════════════════════════
# [F-09 계약 AC] — 5상태 100%
# ═══════════════════════════════════════════════════════════════════════════
class FiveStateTest(K3Fixture):
    """★ 다섯이 **서로 안 섞이는가** (DA-03 §0 · §2-5)."""

    def test_five_states_are_defined_by_name(self) -> None:
        """검수의 "5상태 100%"는 세는 것이 아니라 **이름을 보여 주는 것**이다.

        위젯마다 다시 세면 그 수는 언제나 100% 가 나온다 (D-249 부착률 착시).
        """
        from kernels.k3_dashboard import FIVE_STATES

        self.assertEqual(
            ("data", "loading", "empty", "error", "forbidden"), FIVE_STATES,
            "DA-03 §0 이 고정한 다섯과 다릅니다. 늘리거나 줄이려면 그 문서와 "
            "`WidgetState` 를 **같은 커밋에서** 고치십시오.")

    def test_data_state_carries_content(self) -> None:
        from kernels.k3_dashboard import WidgetState, resolve_layout

        panels = resolve_layout(scope=self.scope_a)
        self.assertEqual(1, len(panels), "자기 패널을 못 찾았습니다.")
        self.assertIs(WidgetState.DATA, panels[0].state)
        self.assertEqual({"series": [1, 2, 3]}, panels[0].config)

    def test_empty_and_error_are_not_the_same_value(self) -> None:
        """★ 이 파일에서 가장 중요한 시험.

        데이터가 없는 것과 못 가져온 것은 **다른 사실**이고, 관제요원의 다음 행동이
        다르다 — 전자는 대기, 후자는 신고 (DA-03 §2-5 규칙 1 · D-290).
        """
        from kernels.k3_dashboard import WidgetState, resolve_layout

        empty = resolve_layout(scope=self.scope_a, panel_source=lambda p: [])
        self.assertIs(WidgetState.EMPTY, empty[0].state)

        def _boom(panel):
            raise ConnectionError("집계 서버가 응답하지 않는다")

        error = resolve_layout(scope=self.scope_a, panel_source=_boom)
        self.assertIs(WidgetState.ERROR, error[0].state)

        self.assertNotEqual(
            empty[0].state, error[0].state,
            "'빈'과 '오류'가 같은 값입니다 — 화면이 같은 문구를 그리고, "
            "관제요원이 대기해야 할 때 신고하거나 그 반대가 됩니다.")
        self.assertIn("0건", empty[0].reason)
        self.assertIn("ConnectionError", error[0].reason)

    def test_error_state_never_carries_stale_content(self) -> None:
        """오류인데 옛 데이터를 함께 주면 화면이 그것을 그린다 — 거짓 화면이다."""
        from kernels.k3_dashboard import WidgetState, resolve_layout

        def _boom(panel):
            raise RuntimeError("실패")

        panels = resolve_layout(scope=self.scope_a, panel_source=_boom)
        self.assertIs(WidgetState.ERROR, panels[0].state)
        self.assertFalse(panels[0].config,
                         "오류 상태에 내용이 실려 있습니다 — '빈'과 '오류'를 가른 이유가 "
                         "사라집니다 (DA-03 §2-5).")

    def test_server_never_emits_loading(self) -> None:
        """★ `LOADING` 은 **클라이언트의 시간**이지 서버의 사실이 아니다.

        서버가 LOADING 을 내면 화면은 영원히 스피너다 — DA-03 §0-1 이 실측한
        "로딩 상태가 오류 상태를 삼킨다"가 그것이다.
        """
        from kernels.k3_dashboard import SERVER_EMITTED_STATES, PanelView, WidgetState

        self.assertNotIn(WidgetState.LOADING, SERVER_EMITTED_STATES)
        with self.assertRaises(ValueError):
            PanelView(panel_id=1, dashboard_id=1, title="x", panel_type="chart",
                      state=WidgetState.LOADING)

        for panels in (resolve_all := [
            _resolve(self.scope_a),
            _resolve(self.scope_a, source=lambda p: []),
            _resolve(self.scope_a, source=_raise),
        ]):
            for panel in panels:
                self.assertIn(panel.state, SERVER_EMITTED_STATES,
                              f"서버가 {panel.state} 를 냈습니다.")
        self.assertTrue(resolve_all, "아무 갈래도 지나가지 않았습니다.")

    def test_forbidden_is_decided_before_content_is_fetched(self) -> None:
        """권한 없는 칸은 **내용을 가져오지도 않는다.**

        가져온 뒤에 가리면 그 조회가 이미 남의 데이터를 만졌을 수 있다.
        """
        from kernels.k3_dashboard import WidgetState, resolve_layout

        self._panel(self.board_a, "설정-패널", self.group_a,
                    config={"widget": "threshold"})
        touched = []

        def _source(panel):
            touched.append(panel.pk)
            return {"v": 1}

        with self.settings(K3_WIDGET_MATRIX={"k3_operator_a": {"threshold": "hidden"}}):
            panels = resolve_layout(scope=self.scope_a, panel_source=_source)

        forbidden = [p for p in panels if p.state is WidgetState.FORBIDDEN]
        self.assertEqual(1, len(forbidden), "권한없음 갈래를 지나가지 않았습니다.")
        self.assertNotIn(forbidden[0].panel_id, touched,
                         "권한 없는 칸의 내용을 가져왔습니다 — 가리기 전에 이미 읽었습니다.")
        self.assertFalse(forbidden[0].config)


def _raise(panel):
    raise RuntimeError("실패")


def _resolve(scope, source=None):
    from kernels.k3_dashboard import resolve_layout

    return resolve_layout(scope=scope, panel_source=source)


# ═══════════════════════════════════════════════════════════════════════════
# 가시성 — **화면에서 감추는 것은 통제가 아니다**
# ═══════════════════════════════════════════════════════════════════════════
class WidgetPermissionTest(K3Fixture):
    """DA-03 §3-4 매트릭스의 서버측 판정."""

    def test_editable_is_never_true_without_configuration(self) -> None:
        """★ 편집은 **설정 없이는 절대 참이 되지 않는다.**

        설정을 안 한 상태에서 편집이 열리면, 아무도 설정하지 않은 채로 운영에 나간다.
        """
        from kernels.k3_dashboard import SETTING_WIDGETS, Visibility, widget_permission

        with self.settings(K3_WIDGET_MATRIX={}):
            for widget in SETTING_WIDGETS:
                level = widget_permission(widget, scope=self.scope_a)
                self.assertFalse(
                    level.can_write,
                    f"[{widget}] 설정이 비었는데 편집이 열렸습니다: {level}")
                self.assertIs(Visibility.VISIBLE, level,
                              f"[{widget}] 읽기까지 막으면 '권한없음'이 "
                              "'아직 설정 안 함'을 덮어 원인을 못 찾습니다.")

    def test_configured_editable_is_honoured(self) -> None:
        """★ 양성 대조 — 설정하면 **열려야 한다** (D-277)."""
        from kernels.k3_dashboard import Visibility, widget_permission

        with self.settings(K3_WIDGET_MATRIX={"k3_operator_a": {"threshold": "editable"}}):
            self.assertIs(Visibility.EDITABLE,
                          widget_permission("threshold", scope=self.scope_a))

    def test_unknown_widget_is_refused(self) -> None:
        """DA-03 §3-4 가 이름 붙이지 않은 항목은 **없는 항목**이다 (D-285 ②)."""
        from kernels.k3_dashboard import InvalidLayoutInput, widget_permission

        with self.assertRaises(InvalidLayoutInput):
            widget_permission("secret_button", scope=self.scope_a)

    def test_visibility_does_not_replace_tenant_isolation(self) -> None:
        """★ DA-03 §3-4 불변 규칙 1 — **화면에서 감추는 것은 통제가 아니다.**

        B 에게 위젯이 `VISIBLE` 이어도, 그 위젯이 읽는 데이터는 여전히 A 의 것이 아니다.
        """
        from kernels.k3_dashboard import Visibility, resolve_layout, widget_permission

        with self.settings(K3_WIDGET_MATRIX={}):
            level = widget_permission("audit_log", scope=self.scope_b)
        self.assertIs(Visibility.VISIBLE, level, "가시성 전제가 깨졌습니다.")

        seen = {p.panel_id for p in resolve_layout(scope=self.scope_b)}
        self.assertNotIn(self.panel_a.pk, seen,
                         "위젯이 보인다는 이유로 남의 테넌트 패널이 나왔습니다 — "
                         "가시성이 격리를 대신했습니다.")


# ═══════════════════════════════════════════════════════════════════════════
# 격리 — 프레임도 문지기를 탄다
# ═══════════════════════════════════════════════════════════════════════════
class KernelTenantScopeTest(K3Fixture):
    """대시보드 격리 — **부모를 좁혔으니 자식은 안전하다**고 보지 않는다 (D-272)."""

    def test_positive_control_own_panels_are_found(self) -> None:
        from kernels.k3_dashboard import resolve_layout

        self.assertEqual(
            1, len(resolve_layout(scope=self.scope_a)),
            "자기 패널을 못 찾았습니다 — 조회가 죽었습니다.")

    def test_other_tenant_panels_are_never_returned(self) -> None:
        from kernels.k3_dashboard import resolve_layout

        seen = {p.panel_id for p in resolve_layout(scope=self.scope_a)}
        self.assertNotIn(self.panel_b.pk, seen, "남의 테넌트 패널이 보입니다.")

    def test_child_is_filtered_even_when_parent_is_shared(self) -> None:
        """★ D-272 — 부모가 열려도 **자식이 통째로 나가면 안 된다.**

        남의 패널을 우리 대시보드에 매단다(잘못된 배선의 모사). 부모는 우리 것이지만
        패널의 소유는 B 다 — 그때도 나오면 안 된다.
        """
        from kernels.k3_dashboard import resolve_layout

        stray = self._panel(self.board_a, "B-소유 패널", self.group_b,
                            config={"series": [7]})
        seen = {p.panel_id for p in resolve_layout(scope=self.scope_a)}
        self.assertNotIn(
            stray.pk, seen,
            "부모가 우리 것이라는 이유로 남의 소유 패널이 나왔습니다 — "
            "자식 필터가 없습니다 (D-272).")

    def test_system_scope_cannot_read_the_frame(self) -> None:
        from common.tenant_scope import SystemScopeCannotRead

        from kernels.k3_dashboard import get_preset, resolve_layout, widget_permission

        for call in (lambda: get_preset(scope=self.scope_pipe),
                     lambda: resolve_layout(scope=self.scope_pipe),
                     lambda: widget_permission("audit_log", scope=self.scope_pipe)):
            with self.assertRaises(SystemScopeCannotRead):
                call()


class KernelScopeSignatureTest(TestCase):
    """[D-281] 커널 공개 함수는 **스코프 없이는 호출 자체가 불가능**해야 한다."""

    def test_every_public_function_refuses_to_run_without_scope(self) -> None:
        import inspect

        from kernels import k3_dashboard

        problems = []
        for name in ("get_preset", "resolve_layout", "widget_permission"):
            sig = inspect.signature(getattr(k3_dashboard, name))
            scope = sig.parameters.get("scope")
            if scope is None:
                problems.append(f"{name}: scope 인자가 없다")
                continue
            if scope.kind is not inspect.Parameter.KEYWORD_ONLY:
                problems.append(f"{name}: scope 가 키워드 전용이 아니다")
            if scope.default is not inspect.Parameter.empty:
                problems.append(f"{name}: scope 에 기본값이 있다 — 필수가 아니다")
        self.assertEqual([], problems, f"D-281 위반: {problems}")


class KernelPublicSurfaceTest(TestCase):
    """DA-04 §2 K3 표가 정한 공개 면 3개가 **실재하는가.**"""

    #: DA-04 §2 K3 의 "공개 면" 열 그대로.
    SURFACE = ["get_preset", "resolve_layout", "widget_permission"]

    def test_public_surface_matches_da04(self) -> None:
        from kernels import k3_dashboard

        missing = [n for n in self.SURFACE if not hasattr(k3_dashboard, n)]
        self.assertEqual(
            [], missing,
            f"DA-04 §2 K3 표의 공개 면이 커널에 없습니다: {missing}\n"
            "표를 바꾸려면 DA-04 와 이 목록을 **같은 커밋에서** 함께 고치십시오.")

    def test_no_fourth_preset(self) -> None:
        """재난용 프리셋을 따로 만들면 **U3 수렴이 깨진다** (DA-04 K3 · DA-03 D3-2)."""
        from kernels.k3_dashboard import Preset

        self.assertEqual({"OPERATOR", "MANAGER", "EXECUTIVE"},
                         {p.value for p in Preset},
                         "프리셋이 셋이 아닙니다. 늘리려면 DA-04 §2 K3 와 W3-2 를 "
                         "같은 커밋에서 고치십시오.")

    def test_da04_precondition_dashboardpanel_is_isolation_registered(self) -> None:
        """★ DA-04 §2 K3 이 **착수 전 조건**으로 적은 것을 시험이 지킨다.

        DA-04 원문: *"⚠ `dashboard.DashboardPanel` 이 테넌트 격리 시험 레지스트리에
        **미등록**이라는 실측이 있다(W0-14 2026-08-24 항목). **K3 착수 전 등록한다.**"*

        조건을 사람의 기억에 맡기면 다음 커널에서 같은 조건이 또 빠진다 (D-286).
        그래서 **K3 의 시험이 그 조건을 붙들고 있게** 한다 — 등재가 빠지면 K3 가 멈춘다.
        """
        from tests.test_tenant_isolation import MODELS

        registered = {f"{t.app_label}.{t.model_name}" for t in MODELS}
        for label in ("dashboard.Dashboard", "dashboard.DashboardPanel"):
            self.assertIn(
                label, registered,
                f"{label} 이 격리 시험 레지스트리에서 빠졌습니다 — "
                "DA-04 §2 K3 의 착수 전 조건입니다. K3 는 이 등재 위에 섭니다.")

    def test_kernel_does_not_import_apps(self) -> None:
        """계층 역전 금지 (D-278)."""
        import subprocess
        import sys
        from pathlib import Path

        here = Path(__file__).resolve()
        script = next(
            (c for c in (Path("/repo") / "scripts" / "verify_layers.py",
                         *(p / "scripts" / "verify_layers.py" for p in here.parents[1:4]))
             if c.is_file()), None)
        self.assertIsNotNone(script, "verify_layers.py 를 찾지 못했습니다 (D-285 (4)).")
        out = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(0, out.returncode, out.stdout + out.stderr)
