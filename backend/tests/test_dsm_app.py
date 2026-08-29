# -*- coding: utf-8 -*-
"""DSM App (L4) — **F-09 · F-10 · F-11 · F-12 조립 시험**.

App 층의 시험이 물어야 하는 것은 커널 시험과 다르다
---------------------------------------------------
커널 시험은 *"판정이 옳은가"* 를 묻는다. App 시험은 **그것을 다시 묻지 않는다** —
두 번 물으면 같은 사실을 두 벌로 재고, 커널이 바뀔 때 시험이 두 곳에서 깨진다.

App 시험이 묻는 것은 셋이다:

    ① **얇은가** — App 이 판정·집계를 다시 하고 있지 않은가 (DA-04 §1-1)
    ② **옮기다 잃지 않는가** — 커널이 낸 것(특히 상태·실패)이 응답에서 사라지지 않는가
    ③ **없는 것을 있다고 하지 않는가** — 빈 목록으로 미구현을 덮지 않는가 (D-284)

②가 App 층 고유의 위험이다. 커널이 `state=ERROR` 를 냈는데 App 이 그 칸을 빼고
보내면, 화면은 **오류를 빈 칸으로** 그린다 — DA-03 §2-5 규칙 1이 금지한 자리다.
"""
from __future__ import annotations

import contextlib
from datetime import timedelta

from django.apps import apps
from django.test import TestCase
from django.utils import timezone

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "apps.dsm.services (F-09~F-12 조립부) · kernels.k1~k4 공개 면 · adapters.sdn — "
    "저장소의 실제 App 과 실제 커널. 합성 더미를 부르지 않는다"
)


class DsmFixture(TestCase):
    """테넌트 A/B · 스트림 · 수신 규칙. `K6Fixture` 규약을 따른다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        UserGroup = apps.get_model("user", "UserGroup")

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="dsm-tenant-A")
        cls.group_b = UserGroup.objects.create(name="dsm-tenant-B")
        UserGroup.objects.filter(pk__in=[cls.group_a.pk, cls.group_b.pk]).update(
            created_by=None)

        cls.role_a = cls._own(cls._role("dsm_watch_a"), cls.group_a)
        cls.user_a = cls._user("dsm_user_a", cls.group_a, cls.role_a)
        cls.user_b = cls._user("dsm_user_b", cls.group_b, cls._own(
            cls._role("dsm_watch_b"), cls.group_b))

        cls.stream_a = cls._stream("dsm-stream-A", cls.group_a)
        cls.stream_b = cls._stream("dsm-stream-B", cls.group_b)
        cls._rule(cls.group_a, cls.role_a, "critical")

        from common.tenant_scope import TenantScope

        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)
        cls.scope_pipe = TenantScope.system(
            reason="DSM 시험 픽스처 — 검출 파이프라인에는 요청자가 없다 (D-281)")

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
    def _stream(cls, name, group):
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        return cls._own(StreamMonitor.objects.create(
            name=name, code=name, ip_source="rtsp://dsm.invalid/x"), group)

    @classmethod
    def _rule(cls, group, role, severity):
        Rule = apps.get_model("stream_monitors", "NotificationRule")
        return cls._own(Rule.objects.create(
            severity=severity, role=role, channels=["email"], is_active=True), group)

    def _event(self, stream, *, severity="critical", event_type="fire", when=None):
        from kernels.k1_event import record_detection

        self._nth = getattr(self, "_nth", 0) + 1
        when = when or (timezone.now() - timedelta(seconds=60 * self._nth))
        return record_detection(
            scope=self.scope_pipe, stream_monitor_id=stream.pk, event_type=event_type,
            severity=severity, occurred_at=when,
            snapshot_path=f"minio://dsm/{self._nth}.jpg").event_id


# ═══════════════════════════════════════════════════════════════════════════
# F-09 재난 대시보드
# ═══════════════════════════════════════════════════════════════════════════
class DashboardFrameTest(DsmFixture):
    """AC-09 ① — **5상태가 전 위젯에 대해 정의·구현되는가.**"""

    def test_the_five_states_come_from_the_kernel_not_from_here(self) -> None:
        """★ ①얇은가 — App 이 다섯을 **다시 세지 않는가.**

        App 이 자기 목록을 만들면 커널이 상태를 하나 늘릴 때 화면만 옛 다섯을 본다.
        같은 값을 두 곳에서 정하지 않는다 (D-212).
        """
        from kernels.k3_dashboard import FIVE_STATES

        from apps.dsm import services

        frame = services.dashboard_frame(scope=self.scope_a)
        self.assertEqual(FIVE_STATES, frame.five_states,
                         "App 이 5상태 목록을 따로 갖고 있습니다 — 두 벌은 갈립니다.")
        self.assertEqual(5, len(frame.five_states))

    def test_state_counts_report_the_denominator(self) -> None:
        """**분모를 함께 낸다** (D-271) — "정상 3칸" 만 보면 전체가 3인지 30인지 모른다."""
        from apps.dsm import services

        frame = services.dashboard_frame(scope=self.scope_a)
        self.assertEqual(
            len(frame.panels), sum(frame.state_counts.values()),
            "상태별 칸 수의 합이 전체 칸 수와 다릅니다 — 어느 칸이 어디에도 안 세어졌습니다.")
        for state in frame.five_states:
            self.assertIn(state, frame.state_counts,
                          f"{state} 상태가 집계표에서 빠졌습니다 — 0칸도 0으로 보여야 "
                          f"합니다. 빠진 줄은 보이지 않습니다 (D-274).")

    def test_error_panels_are_not_flattened_into_empty(self) -> None:
        """★ ②옮기다 잃지 않는가 — **오류가 빈 칸으로 둔갑하지 않는가.**

        DA-03 §2-5 규칙 1: 대기와 신고는 다른 행동이다. App 이 상태를 떨어뜨리면
        화면은 오류를 빈 칸으로 그리고, 사람은 기다린다.
        """
        from kernels.k3_dashboard import WidgetState

        from apps.dsm import services
        from apps.dsm.api import _panel_payload

        board, panel = self._panel()

        def _boom(_panel):
            raise RuntimeError("패널 출처가 죽었다")

        frame = services.dashboard_frame(scope=self.scope_a, panel_source=_boom)
        states = {p.state for p in frame.panels}
        self.assertIn(WidgetState.ERROR, states,
                      "출처를 죽였는데 오류 상태가 없습니다 — 이 시험이 그 갈래를 "
                      "지나가지 못했습니다.")
        payloads = [_panel_payload(p) for p in frame.panels]
        self.assertTrue(
            any(p["state"] == "error" and p["reason"] for p in payloads),
            "응답에서 오류 상태나 사유가 사라졌습니다 — 화면이 오류를 빈 칸으로 그립니다.")

    def _panel(self):
        Dashboard = apps.get_model("dashboard", "Dashboard")
        Panel = apps.get_model("dashboard", "DashboardPanel")
        board = self._own(Dashboard.objects.create(
            name="dsm-board", code="dsm-board"), self.group_a)
        panel = self._own(Panel.objects.create(
            dashboard=board, panel_title="이상징후", panel_type="chart",
            panel_config={"widget": "abnormal"}), self.group_a)
        return board, panel

    def test_other_tenant_panels_do_not_appear(self) -> None:
        """격리 — 좁히기는 커널이 하지만, **App 이 그 결과를 넓히지 않는지** 본다."""
        Dashboard = apps.get_model("dashboard", "Dashboard")
        Panel = apps.get_model("dashboard", "DashboardPanel")
        board_b = self._own(Dashboard.objects.create(
            name="dsm-board-b", code="dsm-board-b"), self.group_b)
        panel_b = self._own(Panel.objects.create(
            dashboard=board_b, panel_title="남의 칸", panel_type="chart",
            panel_config={"widget": "abnormal"}), self.group_b)

        from apps.dsm import services

        frame = services.dashboard_frame(scope=self.scope_a)
        self.assertNotIn(panel_b.pk, [p.panel_id for p in frame.panels],
                         "남의 테넌트 패널이 우리 프레임에 들어왔습니다.")


class LinkStateTest(DsmFixture):
    """FR-09-4 — **연계 정상 / 대기 / 끊김**.

    ★ 이 칸이 지금 정확한 것이 SDN 연결 표준의 첫 값이다. 어댑터가 하나도 없는데
      화면은 이미 "연계 대기 — 명세 미수령" 을 정확히 말할 수 있다.
    """

    def test_waiting_not_down_while_the_spec_is_missing(self) -> None:
        """**대기와 끊김을 가른다.** 둘을 뭉치면 관제원이 장애 신고를 한다.

        명세 미수령은 장애가 아니다 — 우리가 아직 연결하지 않은 것이다.
        """
        from apps.dsm.services import LinkStatus, link_state

        state = link_state()
        self.assertEqual(LinkStatus.WAITING, state.status)
        self.assertNotEqual(LinkStatus.DOWN, state.status,
                            "명세 미수령을 '끊김' 으로 보고하면 관제원이 장애 신고를 "
                            "합니다 — 우리가 아직 연결하지 않은 것입니다.")
        self.assertIn("명세", state.reason,
                      "왜 대기인지 말하지 않으면 화면 앞의 사람은 기다려야 하는지 "
                      "신고해야 하는지 모릅니다.")

    def test_positive_control_a_live_port_reads_as_normal(self) -> None:
        """★ 양성 대조 (D-277) — 이 함수가 **대기 말고 다른 값도 낼 수 있는가.**

        늘 '대기' 를 내는 함수라면 위 시험은 아무것도 재지 않은 것이다.
        """
        import adapters.sdn as sdn

        from apps.dsm.services import LinkStatus, link_state

        class _Live(sdn.SdnPort):
            name = "live-stub"

            def request_qos(self, intent):
                raise NotImplementedError

            def request_reroute(self, intent):
                raise NotImplementedError

            def poll_link_states(self):
                return ()

            def on_link_state(self, notice):
                return None

            def fetch_results(self, *, since):
                return ()

            def check_auth(self):
                return True

        undo = sdn.register(_Live())
        self.addCleanup(undo)
        original, sdn.KERNEL_READY = sdn.KERNEL_READY, True
        try:
            self.assertEqual(LinkStatus.NORMAL, link_state().status)
        finally:
            sdn.KERNEL_READY = original

    def test_a_dead_port_reads_as_down(self) -> None:
        """끊김도 낼 수 있는가 — 세 값이 전부 도달 가능해야 3표시다."""
        import adapters.sdn as sdn

        from apps.dsm.services import LinkStatus, link_state

        class _Dead(sdn.SdnPort):
            name = "dead-stub"

            def request_qos(self, intent):
                raise NotImplementedError

            def request_reroute(self, intent):
                raise NotImplementedError

            def poll_link_states(self):
                return ()

            def on_link_state(self, notice):
                return None

            def fetch_results(self, *, since):
                return ()

            def check_auth(self):
                raise sdn.SdnUnavailable("SDN 컨트롤러에 닿지 않는다")

        undo = sdn.register(_Dead())
        self.addCleanup(undo)
        original, sdn.KERNEL_READY = sdn.KERNEL_READY, True
        try:
            self.assertEqual(LinkStatus.DOWN, link_state().status)
        finally:
            sdn.KERNEL_READY = original


# ═══════════════════════════════════════════════════════════════════════════
# F-10 알림 발송
# ═══════════════════════════════════════════════════════════════════════════
class NotifyTest(DsmFixture):
    """AC-10 — 심각 이벤트에 30초 내 발송 기록."""

    def test_send_and_history_come_from_the_same_rows(self) -> None:
        """★ ①얇은가 — 발송 목록과 이력이 **같은 표**에서 나오는가 (DA-04 K2)."""
        from apps.dsm import services

        event_id = self._event(self.stream_a)
        sent = services.notify_event(scope=self.scope_a, event_id=event_id)
        self.assertTrue(sent, "수신 규칙이 있는데 발송이 0건입니다.")

        history = services.delivery_history(scope=self.scope_a, event_id=event_id)
        self.assertEqual(
            [r.delivery_id for r in sent], [r.delivery_id for r in history],
            "발송 결과와 이력이 다른 행을 가리킵니다 — 두 벌로 적재됐습니다.")

    def test_a_failed_send_stays_visible_as_a_row(self) -> None:
        """★ ②옮기다 잃지 않는가 — **실패가 응답에서 사라지지 않는가** (D-290).

        실패를 빼고 보내면 "보낸 적 없음"(행 없음)과 "보내려다 실패" 가 같아진다.
        """
        from kernels.k2_notify import channels

        from apps.dsm import services

        class _DeadMail:
            name = "email"

            def send(self, *, address, subject, body):
                raise ConnectionError("메일 서버가 죽었다")

        undo = channels.register(_DeadMail())
        self.addCleanup(undo)

        event_id = self._event(self.stream_a)
        records = services.notify_event(scope=self.scope_a, event_id=event_id)
        self.assertTrue(records, "발송이 실패했다고 행이 사라졌습니다.")
        self.assertFalse(records[0].succeeded)
        self.assertTrue(records[0].failure_reason,
                        "실패했는데 사유가 비었습니다 — 조용한 실패입니다.")

    def test_other_tenants_event_cannot_be_notified(self) -> None:
        """쓰기 방향 격리 (D-290) — 남의 이벤트로 발송을 일으킬 수 없다."""
        from django.http import Http404

        from apps.dsm import services

        mine = self._event(self.stream_a)
        with self.assertRaises(Http404):
            services.notify_event(scope=self.scope_b, event_id=mine)


# ═══════════════════════════════════════════════════════════════════════════
# F-12 관리자 설정 — 무권한 차단 + 감사로그 전건
# ═══════════════════════════════════════════════════════════════════════════
class SettingGuardTest(DsmFixture):
    """AC-12 — *"무권한 계정의 설정 변경 시도가 차단되고, **성공·실패 모두** 감사로그에 남는다."*"""

    def test_denied_attempt_is_recorded(self) -> None:
        """★ **차단은 조용하다.** 남기지 않으면 시도가 없던 것과 같아진다."""
        from apps.dsm import audit, services
        from apps.dsm.exceptions import PermissionDeniedForSetting

        before = len(audit.entries())
        with self.assertRaises(PermissionDeniedForSetting) as caught:
            services.setting_overview(scope=self.scope_a, domain="recipients")

        after = audit.entries()
        self.assertEqual(before + 1, len(after),
                         "차단됐는데 감사에 아무것도 남지 않았습니다 (AC-12).")
        self.assertEqual(audit.DENIED, after[0].outcome)
        self.assertEqual(caught.exception.audit_id, after[0].audit_id,
                         "응답이 가리키는 감사 번호와 실제 감사 행이 다릅니다 — "
                         "'남겼다' 는 말이 응답에만 있습니다.")

    def test_allowed_attempt_is_recorded_too(self) -> None:
        """성공**도** 남는가. 실패만 남기면 "누가 언제 바꿨나" 에 답하지 못한다."""
        from common.tenant_roles import tenant_admin_role_code

        from apps.dsm import audit, services

        self._make_tenant_admin()
        before = len(audit.entries())
        out = services.setting_overview(scope=self.scope_a, domain="recipients")

        self.assertIn("recipients", out)
        after = audit.entries()
        self.assertEqual(before + 1, len(after),
                         "통과했는데 감사에 남지 않았습니다 — '전건' 이 아닙니다 (AC-12).")
        self.assertEqual(audit.ALLOWED, after[0].outcome)

    def _make_tenant_admin(self):
        from common.tenant_roles import tenant_admin_role_code

        code = tenant_admin_role_code(self.group_a.pk)
        role = self._own(self._role(code), self.group_a)
        self.user_a.roles.add(role)
        self.user_a.refresh_from_db()
        return role

    def test_the_role_decision_is_not_copied(self) -> None:
        """FR-12-3 · D-212 — **판정식을 복사하지 않는다.**

        복사본 하나가 우회 지점 하나이고, 실제로 그 복사본이 이 저장소 격리 사고의
        원인이었다. App 이 자기 역할 판정을 갖고 있으면 여기서 잡는다.
        """
        import inspect

        from apps.dsm import services

        src = inspect.getsource(services)
        self.assertIn("from common.tenant_roles import", src)
        for smell in ("is_superuser", "role_name ==", 'code == "admin"',
                      "roles.filter("):
            self.assertNotIn(
                smell, src,
                f"App 이 역할 판정을 스스로 합니다({smell}) — 판정은 "
                f"common/tenant_roles.py 한 곳에서만 합니다 (FR-12-3 · D-212).")


class SettingHonestAbsenceTest(DsmFixture):
    """★ ③없는 것을 있다고 하지 않는가 (D-284 · D-290).

    F-12 가 계약상 관리해야 하는 다섯 중 **셋은 저장할 표가 없다.**
    빈 목록을 돌려주면 화면은 "설정이 없습니다" 를 그리고, 사용자는
    **기능이 있는데 비어 있다**고 읽는다.
    """

    def setUp(self) -> None:
        super().setUp()
        code_role = self._role_for_admin()
        self.user_a.roles.add(code_role)

    def _role_for_admin(self):
        from common.tenant_roles import tenant_admin_role_code

        return self._own(self._role(tenant_admin_role_code(self.group_a.pk)),
                         self.group_a)

    def test_unavailable_domains_raise_instead_of_returning_empty(self) -> None:
        from apps.dsm import services
        from apps.dsm.exceptions import SettingNotAvailable

        for domain in ("zones", "thresholds", "grade_rules", "api_keys"):
            with self.subTest(domain=domain):
                with self.assertRaises(SettingNotAvailable) as caught:
                    services.setting_overview(scope=self.scope_a, domain=domain)
                self.assertTrue(
                    str(caught.exception).strip(),
                    f"{domain} 이 사유 없이 막혔습니다 — 모르는 것을 모른다고 말할 때도 "
                    f"이유를 적습니다 (D-264).")

    def test_available_domains_actually_return_something(self) -> None:
        """양성 대조 — **전부 막는 함수**라면 위 시험은 아무것도 재지 않은 것이다."""
        from apps.dsm import services

        out = services.setting_overview(scope=self.scope_a, domain="widgets")
        self.assertIn("widgets", out)
        self.assertTrue(out["widgets"], "위젯 가시성이 비었습니다 — K3 를 부르지 "
                                        "않았거나 SETTING_WIDGETS 가 비었습니다.")

    def test_every_contract_domain_has_a_row(self) -> None:
        """FR-12-1 이 든 다섯이 **전부 이름으로 등재돼 있는가** (D-285 ②).

        빠진 것은 보이지 않는다 — 목록에 없으면 "못 한다" 조차 말하지 못한다.
        """
        from apps.dsm.services import SETTING_DOMAINS

        for domain in ("recipients", "zones", "thresholds", "grade_rules", "api_keys"):
            self.assertIn(domain, SETTING_DOMAINS,
                          f"FR-12-1 의 '{domain}' 이 설정 영역 목록에서 빠졌습니다.")


# ═══════════════════════════════════════════════════════════════════════════
# 층 규약 — App 은 얇은가
# ═══════════════════════════════════════════════════════════════════════════
class AppStaysThinTest(TestCase):
    """★ ①얇은가 — 이 App 이 **커널의 일을 다시 하고 있지 않은가** (DA-04 §1-1).

    `scripts/verify_layers.py` 가 import 를 본다. 여기서는 **본문**을 본다 —
    import 를 안 해도 로직은 베낄 수 있다.
    """

    def test_the_app_does_not_touch_django_models(self) -> None:
        import inspect

        from apps.dsm import api, services

        for module in (services, api):
            src = inspect.getsource(module)
            for smell in ("apps.get_model(", "_base_manager", ".objects.filter(",
                          "models.Model"):
                self.assertNotIn(
                    smell, src,
                    f"{module.__name__} 이 모델을 직접 만집니다({smell}). App 이 만질 수 "
                    f"있는 것은 커널의 서비스 함수뿐입니다 (DA-04 §1-4).\n"
                    f"    ※ 감사(apps/dsm/audit.py)는 예외다 — logger.AuditLogs 는 "
                    f"커널이 없는 dj-core 표이고, 새 감사 표를 만들지 않기 위해 "
                    f"직접 쓴다. 그 예외는 그 파일 안에 적혀 있다.")

    def test_the_app_does_not_recompute_kernel_decisions(self) -> None:
        """중복 억제·오탐률·상태 판정을 App 이 다시 하지 않는가."""
        import inspect

        from apps.dsm import services

        src = inspect.getsource(services)
        for smell in ("DEDUP_WINDOW", "NOTIFY_WINDOW", "timedelta(seconds=10)",
                      "rejected /", "false_positive"):
            self.assertNotIn(
                smell, src,
                f"App 이 커널의 판정을 다시 합니다({smell}) — 두 벌은 어긋나고, "
                f"그 어긋남은 아무도 못 봅니다.")

    def test_routes_do_not_declare_a_single_response_schema(self) -> None:
        """W0-18 실측 — `response=<단일 스키마>` 는 **거부 사실을 소멸시켰다**.

        그 8건은 P-W0-18-1 A 안으로 전부 뗐다. 새로 만들지 않는다.
        """
        import inspect

        from apps.dsm import api

        # ★ **데코레이터 줄만** 본다. 본문의 `response["Content-Disposition"]` 같은
        #   지역 변수까지 잡으면 이 시험은 늘 빨간불이고, 늘 빨간불인 시험은 꺼진다.
        decorator_lines = [line for line in inspect.getsource(api).splitlines()
                           if line.lstrip().startswith("@route.")]
        offenders = [line.strip() for line in decorator_lines if "response=" in line]
        self.assertEqual(
            [], offenders,
            f"신규 라우트에 response= 선언이 생겼습니다: {offenders}. 거부 dict 가 그 "
            f"스키마를 통과하면 200 + {{}} 가 되고 거부 사실이 사라집니다 (W0-18 실측).")

    def test_errors_are_http_errors_not_success_false(self) -> None:
        """오류는 **HTTP 상태**로 낸다. `BaseResponse(status_code=…)` 는 언제나 200 이다."""
        import inspect

        from apps.dsm import api

        src = inspect.getsource(api)
        self.assertIn("HttpError", src)

        # ★ 문서에서 **언급**하는 것과 **호출**하는 것은 다르다. 이 파일의 독스트링은
        #   "왜 BaseResponse 를 쓰지 않나" 를 설명하므로 그 이름이 본문에 등장한다.
        #   문자열로 찾으면 그 설명 때문에 시험이 늘 빨간불이고, 늘 빨간불인 시험은
        #   결국 꺼진다 — 그래서 **호출인지**를 AST 로 묻는다.
        import ast

        called = {
            node.func.id
            for node in ast.walk(ast.parse(src))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertNotIn(
            "BaseResponse", called,
            "신규 라우트가 BaseResponse 를 씁니다 — 그 값은 언제나 HTTP 200 으로 "
            "나가고, 그것이 W0-18 이 고친 바로 그 모양입니다.")
