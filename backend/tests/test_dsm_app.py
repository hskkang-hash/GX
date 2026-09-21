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
from django.test import TestCase, override_settings
from django.utils import timezone

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "apps.dsm.services (F-09~F-12 조립부) · kernels.k1~k4 공개 면 · adapters.sdn — "
    "저장소의 실제 App 과 실제 커널. 합성 더미를 부르지 않는다"
)


#: ★ P-41 (2026-09-05) — **실발송 허용 도메인이 채널보다 앞에 선다.**
#:   `EmailChannel` 은 목록 밖 도메인을 `send_mail` 앞에서 **로그 어댑터로**
#:   떨어뜨린다. 이 픽스처를 쓰는 시험에는 「메일이 실제로 나갔다」·「F-10 의
#:   두 점이 찍혔다」를 재는 것이 있으므로 **어느 도메인을 허용했는지 밝힌다.**
#:   밝히지 않고 서는 초록은 운영에서 재현되지 않는다 — 운영의 목록은 비어 있다.
#:   강제: `scripts/verify_send_allowlist.py`
@override_settings(K2_SEND_ALLOWED_DOMAINS=["test.invalid"])
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
class LinkStateSecrecyTest(DsmFixture):
    """P-27 [P0] — **화면이 받는 것에 상대사명·계약번호·조항이 없는가.**

    사고 (2026-09-25): `preset=system` 화면의 「연계 상태」 상자가 `reason` 을 그대로
    그렸고, 그 문단에는 상대사명 · 계약번호 · 조항 · 미이행 사실이 들어 있었다.

    ★ 이 시험이 **응답 조립부를 직접 부른다.** 화면 코드를 보는 시험이었다면 다음 화면이
      같은 병을 다시 앓는다 — 막는 곳은 화면이 아니라 서버다.
    """

    #: 화면에 있으면 안 되는 것들. `verify_ui_secrets.py` 의 목록과 **같은 뿌리**다.
    FORBIDDEN = ("DEV-SBIT", "에스비정보기술", "조2항", "조3항", "D-2", "D-3")

    def _payload(self, user):
        from apps.dsm import api, services

        class _Req:
            pass

        req = _Req()
        req.user = user
        return api._link_payload(services.link_state(), req)

    def test_a_watch_officer_gets_one_word_and_nothing_else(self) -> None:
        """관제요원 응답에는 **상태 하나**뿐이다. 사유 칸 자체가 없다."""
        payload = self._payload(self.user_a)
        self.assertEqual({"status"}, set(payload),
                         "관제요원 응답에 사유 칸이 있으면, 화면이 안 그려도 "
                         "개발자 도구를 연 사람은 읽습니다.")
        self.assertEqual("waiting", payload["status"])

    def test_the_contract_paragraph_cannot_reach_any_screen(self) -> None:
        """관리자 응답까지 훑는다 — **관리자 상세에도** 상대사명·계약번호·조항은 없다."""
        import adapters.sdn as sdn

        #: 먼저 그 문단이 **지금도 우리 쪽에는 있다**를 확인한다. 없으면 이 시험은
        #: 아무것도 재지 않은 것이다 (D-277 음성 대조가 무의미해진다).
        self.assertIn("에스비정보기술", sdn.NOT_READY_REASON)

        CoreUser = apps.get_model("user", "CoreUser")
        admin = CoreUser.objects.create_user(
            username="dsm_admin_secrecy", password="test-only-not-a-secret",
            is_active=True, email="dsm_admin_secrecy@test.invalid", is_superuser=True)

        for who, user in (("관제요원", self.user_a), ("관리자", admin)):
            body = str(self._payload(user))
            for needle in self.FORBIDDEN:
                self.assertNotIn(needle, body,
                                 f"{who} 응답에 '{needle}' 가 실렸습니다 — "
                                 f"그것은 화면이 아니라 문서의 자리입니다.")

    def test_the_admin_line_comes_from_the_dictionary_not_from_the_reason(self) -> None:
        """관리자 한 줄은 **사전에서** 온다. 지어내면 다음 문장이 또 누출이다."""
        from apps.dsm import services

        CoreUser = apps.get_model("user", "CoreUser")
        admin = CoreUser.objects.create_user(
            username="dsm_admin_dict", password="test-only-not-a-secret",
            is_active=True, email="dsm_admin_dict@test.invalid", is_superuser=True)

        payload = self._payload(admin)
        self.assertIn("detail", payload, "관리자에게는 「자세히」 한 줄이 있어야 합니다.")
        self.assertIn(payload["detail"], set(services.LINK_DETAIL.values()),
                      "사전에 없는 문구를 만들지 않습니다.")

    def test_the_dictionary_covers_every_status(self) -> None:
        """상태가 늘면 사전이 빈다. **비면 보이게** 한다 — 조용한 빈칸을 만들지 않는다."""
        from apps.dsm.services import LINK_DETAIL, LinkStatus

        for status in LinkStatus:
            self.assertTrue(LINK_DETAIL.get(status),
                            f"'{status.value}' 에 사용자 언어 한 줄이 없습니다.")


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

    def test_every_contract_domain_is_now_available(self) -> None:
        """★ 2026-09-10 — **다섯이 전부 열렸다** (D-366 · D-368).

        이 자리는 원래 「막힌 영역이 사유와 함께 멈추는가」를 재던 시험이었다.
        열릴 때마다 그 목록에서 이름이 빠졌고, 오늘 마지막 하나(`grade_rules`)가 빠지며
        **목록이 비었다.**

            2026-09-06  `thresholds` · `api_keys` — K5 표 ①② (D-325)
            2026-09-10  `zones` — 좌표계 확정(D-365) + 편집 면(D-366)
            2026-09-10  `grade_rules` — 표 ③ (D-368)

        ★ 빈 목록을 도는 시험을 남겨 두지 않는다. 0건을 도는 for 문은 **언제나
          통과하는 시험** — 즉 시험이 아닌 것 — 이고, 그 초록은 아무것도 증명하지
          않는다 (D-301 「검사 못함 ≠ 0건 검사」). 그래서 술어를 **뒤집는다**:
          「막힌 것이 사유를 갖는가」에서 **「전부 열렸는가」**로.

        ★ 그리고 「없는 영역」 갈래는 사라지지 않았다 —
          `test_an_unknown_domain_is_still_refused` 가 그것을 이어받는다.
          F-12 가 다루지 않는 이름은 여전히 멈춘다.
        """
        from apps.dsm import services
        from apps.dsm.services import SETTING_DOMAINS

        still_blocked = {d: why for d, why in SETTING_DOMAINS.items() if why}
        self.assertEqual(
            {}, still_blocked,
            "아직 막힌 F-12 설정 영역이 있습니다 — 열렸다면 사유를 비우고, "
            "안 열렸다면 그 사유가 왜 남는지를 여기 적으십시오: %r" % still_blocked)

        # 다섯이 **실제로** 응답을 낸다. 목록에서 이름이 빠진 것만으로는
        # 아무것도 재지 않은 것이다 (D-277 양성 대조).
        for domain in ("recipients", "widgets", "zones", "thresholds",
                       "grade_rules", "api_keys"):
            with self.subTest(domain=domain):
                out = services.setting_overview(scope=self.scope_a, domain=domain)
                self.assertIsInstance(
                    out, dict,
                    f"{domain} 이 dict 를 안 돌려줍니다 — 열렸다고 적었는데 "
                    f"화면이 읽을 것이 없습니다.")

    def test_an_unknown_domain_is_still_refused(self) -> None:
        """★ 「없는 영역」 갈래는 **사라지지 않았다.**

        다섯이 다 열렸다고 아무 이름이나 받으면, 오타가 빈 설정 화면이 된다 —
        그리고 사용자는 **설정 기능이 있는데 비어 있다**고 읽는다(D-284 · D-290).
        """
        from apps.dsm import services
        from apps.dsm.exceptions import SettingNotAvailable

        with self.assertRaises(SettingNotAvailable) as caught:
            services.setting_overview(scope=self.scope_a, domain="zoness")
        self.assertTrue(str(caught.exception).strip(),
                        "사유 없이 막혔습니다 — 모르는 것을 모른다고 말할 때도 "
                        "이유를 적습니다 (D-264).")

    def test_the_two_new_tables_are_actually_available(self) -> None:
        """★ 양성 대조 — **열렸다고 적었으면 실제로 나와야 한다** (D-325 · D-277).

        위 시험에서 이름 둘을 빼는 것만으로는 아무것도 재지 않은 것이다.
        """
        from apps.dsm import services

        out = services.setting_overview(scope=self.scope_a, domain="thresholds")
        self.assertTrue(out["thresholds"], "표 ①이 비었습니다 — K5 를 부르지 않았습니다.")
        out = services.setting_overview(scope=self.scope_a, domain="api_keys")
        self.assertTrue(out["api_keys"], "표 ②가 비었습니다 — K5 를 부르지 않았습니다.")

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
# F-12 「구역」 — **위험구역을 지정하는 면** (D-366)
# ═══════════════════════════════════════════════════════════════════════════
class ZoneSettingTest(DsmFixture):
    """★ 계약 F-12 「구역」 절 — 관리자 설정에서 위험구역을 **한 곳에서 관리한다.**

    직전까지 이 절은 「미착수」였고 사유는 *"위험구역을 저장할 표가 없다"* 였다.
    실측해 보니 막고 있던 것은 표가 아니라 **체계**였다 — 행정구역인지 카메라
    묶음인지 폴리곤인지가 미정이었고, 표(`Zone`)는 D-299 로 이미 서 있었다.
    D-365 가 그 체계를 정하면서 사유가 해소됐고, 이 시험이 그 해소를 잰다.

    ★ **사유가 사라진 것과 절이 갚아진 것은 다른 사실이다**(D-314). 그래서
      「열렸다」로 적지 않고 네 갈래를 실제로 부른다: 읽기 · 쓰기 · 무권한 · 격리.
    """

    #: 좌표계·표현은 L3 이 정한다. 시험이 자기 상수를 두면 두 벌이 되고 갈린다.
    SQUARE = {"type": "Polygon", "coordinates": [[
        [126.970, 37.560], [126.980, 37.560],
        [126.980, 37.570], [126.970, 37.570]]]}

    def setUp(self) -> None:
        super().setUp()
        from common.tenant_roles import tenant_admin_role_code

        self.admin_role = self._own(
            self._role(tenant_admin_role_code(self.group_a.pk)), self.group_a)
        self.user_a.roles.add(self.admin_role)
        self.user_a.refresh_from_db()

    # ── ① 읽기 ───────────────────────────────────────────────────────────
    def test_the_zones_domain_is_actually_readable(self) -> None:
        """★ 양성 대조 — 「열렸다」고 적었으면 **실제로 나와야 한다** (D-277).

        `SETTING_DOMAINS['zones']` 의 사유를 지우는 것만으로는 아무것도 재지 않은 것이다.
        """
        from apps.dsm import services

        out = services.setting_overview(scope=self.scope_a, domain="zones")
        self.assertIn("zones", out)
        self.assertEqual(out["crs"], "WGS84",
                         "좌표계가 응답에 안 실렸습니다 — 화면이 좌표를 어느 계로 "
                         "보낼지 모르면 뒤집힌 좌표가 들어옵니다.")

    # ── ② 쓰기 ───────────────────────────────────────────────────────────
    def test_a_polygon_zone_can_be_created_and_then_judges(self) -> None:
        """★ **지정한 구역이 실제로 판정한다.** 저장만 되고 안 도는 것을 막는다.

        F-12 「구역」과 F-03 「지정 위험구역(폴리곤)」은 **한 뿌리**다 — 지정하는 면이
        없으면 판정기는 픽스처로만 도는 코드이고, 판정이 없으면 지정은 장식이다.
        그래서 한 시험에서 둘을 잇는다.
        """
        from apps.dsm import services
        from stream_monitors.services import zones

        saved = services.save_zone_setting(
            scope=self.scope_a, name="하천 범람 위험구역", kind="polygon",
            geometry=self.SQUARE)

        self.assertEqual(saved["geometry_status"], "ready",
                         "폴리곤을 넣었는데 geometry_status 가 ready 가 아닙니다 — "
                         "부르는 쪽이 정하게 두면 도형 없는 ready 가 생깁니다.")
        self.assertTrue(saved["audit_id"], "성공이 감사에 안 남았습니다 (AC-12).")

        Zone = apps.get_model("stream_monitors", "Zone")
        zone = Zone._base_manager.get(pk=saved["zone_id"])
        self.assertTrue(zones.contains(zone, lat=37.565, lng=126.975),
                        "지정한 구역이 그 안의 좌표를 '밖'으로 판정합니다.")
        self.assertFalse(zones.contains(zone, lat=37.565, lng=126.990))

    def test_a_camera_group_zone_can_be_created(self) -> None:
        """카메라 묶음 구역도 같은 문으로 만든다 — 종류마다 문을 만들지 않는다."""
        from apps.dsm import services

        saved = services.save_zone_setting(
            scope=self.scope_a, name="보행교 구간", kind="camera_group",
            camera_ids=[self.stream_a.pk])

        Zone = apps.get_model("stream_monitors", "Zone")
        zone = Zone._base_manager.get(pk=saved["zone_id"])
        self.assertEqual([self.stream_a.pk],
                         list(zone.cameras.values_list("pk", flat=True)))
        self.assertEqual(saved["geometry_status"], "not_implemented",
                         "카메라 묶음인데 도형이 '가동'으로 적혔습니다 — "
                         "도형 없는 ready 는 판정에서만 사라지는 구역이 됩니다.")

    def test_a_broken_polygon_is_refused_at_the_door(self) -> None:
        """★ **잘못 그린 구역은 저장되지 않는다.**

        저장해 두고 부를 때 터지면 화면에는 '가동'인 구역이 판정에서만 사라진다 —
        그 상태는 아무도 신고하지 않는다(D-284).
        """
        from apps.dsm import services
        from stream_monitors.services.zones import InvalidPolygon

        Zone = apps.get_model("stream_monitors", "Zone")
        before = Zone._base_manager.count()
        bowtie = {"type": "Polygon", "coordinates": [[
            [0.0, 0.0], [2.0, 2.0], [2.0, 0.0], [0.0, 2.0]]]}

        with self.assertRaises(InvalidPolygon):
            services.save_zone_setting(scope=self.scope_a, name="나비넥타이",
                                       kind="polygon", geometry=bowtie)
        self.assertEqual(before, Zone._base_manager.count(),
                         "판정 불가 도형이 저장됐습니다.")

    def test_a_polygon_zone_without_geometry_is_refused(self) -> None:
        """도형 없는 폴리곤 구역은 만들 수 없다 — 화면에는 구역인데 아무것도 안 잡는다."""
        from apps.dsm import services

        with self.assertRaises(ValueError):
            services.save_zone_setting(scope=self.scope_a, name="빈 폴리곤",
                                       kind="polygon", geometry=None)

    # ── ③ 무권한 ─────────────────────────────────────────────────────────
    def test_a_non_admin_cannot_create_a_zone(self) -> None:
        """★ AC-12 「무권한은 차단하며」 — 구역 쓰기도 그 차단 안이다.

        구역 지정은 "어디를 위험하다고 볼 것인가" 를 바꾸는 일이다. 읽기만 막고
        쓰기를 열어 두면 아무나 위험구역을 지울 수 있다.
        """
        from apps.dsm import services
        from apps.dsm.exceptions import PermissionDeniedForSetting

        Zone = apps.get_model("stream_monitors", "Zone")
        before = Zone._base_manager.count()

        with self.assertRaises(PermissionDeniedForSetting) as caught:
            services.save_zone_setting(scope=self.scope_b, name="남이 만든 구역",
                                       kind="camera_group")
        self.assertTrue(caught.exception.audit_id,
                        "차단이 감사에 안 남았습니다 — '시도가 없었다' 와 "
                        "'시도가 막혔다' 가 같은 상태가 됩니다 (AC-12).")
        self.assertEqual(before, Zone._base_manager.count())

    # ── ④ 격리 ───────────────────────────────────────────────────────────
    def test_another_tenants_camera_cannot_be_pulled_into_my_zone(self) -> None:
        """★ 남의 카메라를 내 위험구역에 붙일 수 없다.

        붙으면 남의 테넌트 카메라의 진입이 **내 화면에 뜬다** — 읽기 격리가 아무리
        완전해도 이 한 줄이 열려 있으면 격리가 아니다(D-290).
        """
        from django.core.exceptions import PermissionDenied

        from apps.dsm import services

        with self.assertRaises(PermissionDenied):
            services.save_zone_setting(
                scope=self.scope_a, name="남의 카메라 끌어오기",
                kind="camera_group", camera_ids=[self.stream_b.pk])

    def test_another_tenants_zone_is_not_visible_or_editable(self) -> None:
        """남의 구역은 **목록에 없고, 고칠 수도 없다.** 없는 것으로 답한다(404 · D-269)."""
        from django.http import Http404

        from apps.dsm import services

        mine = services.save_zone_setting(scope=self.scope_a, name="내 구역",
                                          kind="camera_group")

        self.user_b.roles.add(self._own(self._role_admin_b(), self.group_b))
        self.user_b.refresh_from_db()
        from common.tenant_scope import TenantScope

        scope_b_admin = TenantScope.of(self.user_b)

        listed = services.setting_overview(scope=scope_b_admin, domain="zones")
        self.assertNotIn(mine["zone_id"], [z["zone_id"] for z in listed["zones"]],
                         "남의 구역이 목록에 보입니다.")
        with self.assertRaises(Http404):
            services.save_zone_setting(scope=scope_b_admin, zone_id=mine["zone_id"],
                                       name="가로채기", kind="camera_group")

    def _role_admin_b(self):
        from common.tenant_roles import tenant_admin_role_code

        return self._role(tenant_admin_role_code(self.group_b.pk))


# ═══════════════════════════════════════════════════════════════════════════
# 층 규약 — App 은 얇은가
# ═══════════════════════════════════════════════════════════════════════════
class AppStaysThinTest(TestCase):
    """★ ①얇은가 — 이 App 이 **커널의 일을 다시 하고 있지 않은가** (DA-04 §1-1).

    `scripts/verify_layers.py` 가 import 를 본다. 여기서는 **본문**을 본다 —
    import 를 안 해도 로직은 베낄 수 있다.
    """

    #: ★ P-206 (2026-09-20 · 차선 U56 · D-508) — **계량이 범위 밖이었다.**
    #:   이 시험은 `services` · `api` 만 봤고, 그래서 `apps/dsm/metering.py` 가
    #:   `apps.get_model` 로 표를 직접 세는 것을 **아무도 못 봤다.** 그 수는 청구서로
    #:   갔고, 게이트가 심은 씨앗(P-193)과 훈련(P-201)이 거기 들어 있었다.
    #:   *구멍이 살아 있던 이유는 코드가 아니라 보는 눈의 범위였다.*
    METERING = "apps.dsm.metering"

    #: ⚠ **계량에 남아 있던 직접 셈 셋 — 갚았다** (P-178 U56 ② · 2026-09-21 · 턴 Z).
    #:   `_alive` · `_cameras` · `_users` · `_storage` 가 여기 있었다. 사유는
    #:   *"카메라·계정·미디어 장부를 세는 커널 면이 아직 없다"* 였고, 그것이 틀렸다 —
    #:   `kernels.k6_feedback.usage_snapshot` 이 DA-04 §2 K6 표에 **이름으로** 서
    #:   있었다(그 표의 `W4-1` 이 이 빚이 가리키던 「갚는 날」이다). 없던 것은 커널
    #:   면이 아니라 그 면의 **구현**이었고, 빚 문서가 그 둘을 같은 말로 적었다.
    #:   ★ 이 목록은 **늘어날 수 없다.** 새 함수가 모델을 만지면 아래 시험이 빨강이다.
    #:   ★ 줄어드는 방향만 허용한다 — 이제 **빈 집합**이고, 다시 채우려면 그 이유를
    #:     여기 적어야 한다. 빈 칸이 곧 「계량은 제 손으로 세지 않는다」의 집행이다.
    METERING_ORM_DEBT: frozenset = frozenset()

    #: 본문에서 잡는 「모델을 직접 만졌다」의 냄새. 세 파일이 같은 목록을 쓴다.
    MODEL_SMELLS = ("apps.get_model(", "_base_manager", ".objects.filter(",
                    "models.Model")

    def test_the_app_does_not_touch_django_models(self) -> None:
        import inspect

        from apps.dsm import api, services

        for module in (services, api):
            src = inspect.getsource(module)
            for smell in self.MODEL_SMELLS:
                self.assertNotIn(
                    smell, src,
                    f"{module.__name__} 이 모델을 직접 만집니다({smell}). App 이 만질 수 "
                    f"있는 것은 커널의 서비스 함수뿐입니다 (DA-04 §1-4).\n"
                    f"    ※ 감사(apps/dsm/audit.py)는 예외다 — logger.AuditLogs 는 "
                    f"커널이 없는 dj-core 표이고, 새 감사 표를 만들지 않기 위해 "
                    f"직접 쓴다. 그 예외는 그 파일 안에 적혀 있다.")

    def test_the_bill_is_not_counted_by_the_app(self) -> None:
        """★ P-206 — **청구서의 수를 앱이 제 손으로 세지 않는가** (`metering.py`).

        `apps.get_model` 한 줄로 표를 세면 그 셈은 **커널을 안 지난다** — 표식도
        (P-193 probe · P-201 drill) 소프트 삭제도 테넌트 못박기도 그 수에 없다.
        그렇게 센 수가 청구서로 가면 **우리가 심은 가짜 사건에 고객이 돈을 낸다.**

        ★ **함수 단위로 묻는다.** 파일 전체에 문자열 검사를 걸면 「어디선가 만진다」
          까지밖에 못 말하고, 남은 빚(`METERING_ORM_DEBT`)이 있는 동안 이 시험은
          늘 빨강이 된다 — 늘 빨간 시험은 꺼진다. 그래서 **어느 함수가** 만지는지를
          AST 로 묻고, 그 집합이 **빚 목록과 정확히 같은가**를 잰다.
        """
        import ast
        import importlib
        import inspect

        module = importlib.import_module(self.METERING)
        src = inspect.getsource(module)
        tree = ast.parse(src)

        offenders = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            # ★ **독스트링을 뺀 본문만** 본다. 「왜 커널이 세는가」를 설명하는 주석에
            #   그 이름이 나오는 것은 당연하고, 그것까지 잡으면 이 시험은 늘 빨강이며
            #   **늘 빨간 시험은 꺼진다**(이 파일이 `BaseResponse` 를 AST 로 물은
            #   것과 같은 자리). 설명은 죄가 아니다 — 호출이 죄다.
            body = "\n".join(
                ast.get_source_segment(src, stmt) or ""
                for stmt in node.body
                if not (isinstance(stmt, ast.Expr)
                        and isinstance(stmt.value, ast.Constant)
                        and isinstance(stmt.value.value, str)))
            if any(smell in body for smell in self.MODEL_SMELLS):
                offenders.add(node.name)

        new = sorted(offenders - self.METERING_ORM_DEBT)
        self.assertEqual(
            [], new,
            f"{self.METERING} 의 {new} 가 모델을 직접 셉니다. 청구서에 적을 수는 "
            f"커널이 셉니다 — kernels.k1_event.count_events · "
            f"kernels.k2_notify.count_deliveries (P-206 · D-508).\n"
            f"    ※ 앱이 세면 표식(probe·drill)도 소프트 삭제도 그 수에 없습니다. "
            f"그 수는 청구서로 갑니다.")

        stale = sorted(self.METERING_ORM_DEBT - offenders)
        self.assertEqual(
            [], stale,
            f"빚 목록에 있는 {stale} 가 이제 모델을 안 만집니다 — **목록에서 지우십시오.**\n"
            f"    ※ 낡은 예외는 다음에 생길 구멍의 문입니다: 이름이 목록에 남아 있는 한 "
            f"그 이름으로 새 직접 셈이 들어와도 이 시험은 초록입니다.")

    def test_the_billing_counts_come_from_the_kernels(self) -> None:
        """★ P-206 — 세는 **세 자리**가 정말 커널 함수를 부르는가.

        위 시험은 「모델을 안 만진다」만 잰다. 안 만지면서 **아무것도 안 세는** 코드도
        그것을 통과한다(전부 0을 돌려주는 코드가 가장 얇다). 그래서 **부르는가**를
        따로 묻는다 — 두 시험이 함께여야 「얇고 또 센다」가 된다.
        """
        import ast
        import importlib
        import inspect

        module = importlib.import_module(self.METERING)
        src = inspect.getsource(module)
        #: ⚠ 계량은 커널을 **직접 안 부른다.** 「K1 의 App 소비자는 하나뿐」이라
        #:   `apps/dsm/services.py` 의 문을 지난다(`test_f05_event_api.py::
        #:   EntrySurfaceIsOneTest`). 그래서 사슬을 **두 칸으로** 잰다 — 한 칸만 재면
        #:   문이 커널을 안 부르는 날에도 이 시험이 초록이다.
        want = {"_events": "count_billable_events",
                "_notifications": "count_billable_deliveries",
                "_notifications_failed": "count_billable_deliveries",
                #: ★ 턴 Z — 장부 셋(카메라·계정·저장)이 여기 들어왔다. 셋은 같은
                #:   시점의 잔량이라 **한 문**(`count_billable_ledgers`)을 지나고,
                #:   `_cameras`·`_users`·`_storage` 는 그 한 번의 답에서 칸만 꺼낸다.
                #:   그래서 사슬을 `_ledgers` 에서 잰다 — 셋을 각각 재면 「문을 부른다」가
                #:   세 번 적히고, 세 번 적힌 규칙은 한 번 어긋나도 두 번 초록이다.
                "_ledgers": "count_billable_ledgers"}
        found = {}
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.FunctionDef) and node.name in want:
                found[node.name] = ast.get_source_segment(src, node) or ""

        self.assertEqual(sorted(found), sorted(want),
                         f"계량의 세는 함수가 사라졌거나 이름이 바뀌었습니다: "
                         f"{sorted(set(want) - set(found))}")
        for name, call in want.items():
            self.assertIn(
                f"{call}(", found[name],
                f"{self.METERING}.{name} 이 청구 셈의 문 `{call}` 을 부르지 않습니다. "
                f"세지 않는 계량은 **0원짜리 청구서**이고, 그것은 빈 칸보다 나쁩니다 — "
                f"0은 「안 썼다」로 읽힙니다 (D-301).")

        #: 둘째 칸 — **문이 정말 커널을 부르는가.**
        from apps.dsm import services

        for door, kernel_fn in (("count_billable_events", "count_events"),
                                ("count_billable_deliveries", "count_deliveries"),
                                ("count_billable_ledgers", "usage_snapshot")):
            body = inspect.getsource(getattr(services, door))
            self.assertIn(
                f"{kernel_fn}(", body,
                f"apps.dsm.services.{door} 가 커널 셈 함수 `{kernel_fn}` 을 부르지 "
                f"않습니다 — 문만 있고 세는 사람이 없습니다.")

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
