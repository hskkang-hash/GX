# -*- coding: utf-8 -*-
"""K4 보고서 엔진 — **이중 AC 시험** (DA-04 §2 K4).

    [F-11 계약] 템플릿 변수(**이벤트 · 조치 · 캡처**) 치환 및 PDF 출력
    [U2 상품]  보고서 생성 시간 **≤ 10분**

★ 이 파일에서 가장 중요한 시험은 **"조치 없음"과 "조치를 못 가져옴"이 갈리는가**이다.
  둘을 빈 목록 하나로 표현하면, 발송 조회가 실패한 보고서가 "조치 없음"으로 **인쇄되어
  고객에게 나간다.** 그 종이는 되돌릴 수 없다 — D-290 이 종이 위에서 벌어지는 판이다.

두 번째는 **10분이 렌더 시간이 아니라는 것**이다. DA-04: *"줄이는 것은 `build_context`
의 자동 취합 범위다 — 사람이 손으로 옮겨 적는 항목이 0 이면 10분이 된다."*
그래서 여기서 재는 것은 초가 아니라 **`manual_fields` 의 개수**다.
"""
from __future__ import annotations

import contextlib
from datetime import timedelta

from django.apps import apps
from django.test import TestCase
from django.utils import timezone


class K4Fixture(TestCase):
    """테넌트 A/B · 각자의 템플릿·스트림·수신규칙."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        UserGroup = apps.get_model("user", "UserGroup")

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="k4-tenant-A")
        cls.group_b = UserGroup.objects.create(name="k4-tenant-B")
        UserGroup.objects.filter(pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.role_a = cls._own(cls._role("k4_role_a"), cls.group_a)
        cls.role_b = cls._own(cls._role("k4_role_b"), cls.group_b)
        cls.user_a = cls._user("k4_user_a", cls.group_a, cls.role_a)
        cls.user_b = cls._user("k4_user_b", cls.group_b, cls.role_b)

        cls.stream_a = cls._stream("k4-cam-A", cls.group_a)
        cls.stream_b = cls._stream("k4-cam-B", cls.group_b)
        cls._rule(cls.group_a, cls.role_a)
        cls._rule(cls.group_b, cls.role_b)

        cls.tpl_a = cls._template("K4-A 템플릿", cls.group_a,
                                  body="<h1>보고</h1><p>{{ events }}</p><p>{{ actions }}</p>")
        cls.tpl_b = cls._template("K4-B 템플릿", cls.group_b, body="<h1>B</h1>")

        from common.tenant_scope import TenantScope

        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)
        cls.scope_pipe = TenantScope.system(reason="K4 시험 픽스처 — 검출 파이프라인 모사")

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
            name=name, code=name, ip_source="rtsp://k4.invalid/x"), group)

    @classmethod
    def _rule(cls, group, role):
        Rule = apps.get_model("stream_monitors", "NotificationRule")
        return cls._own(Rule.objects.create(
            severity="critical", role=role, channels=["email"], is_active=True), group)

    @classmethod
    def _template(cls, name, group, *, body="<p>{{ events }}</p>", default=False):
        Template = apps.get_model("report_template", "ReportTemplate")
        return cls._own(Template.objects.create(
            name=name, template=body, is_default=default, is_enabled=True), group)

    def _event_with_delivery(self, stream, scope, *, when=None):
        """이벤트 하나 + 그 이벤트의 발송 이력 하나. **조치의 원천이 K2 임을 그대로 쓴다.**"""
        from kernels.k1_event import record_detection
        from kernels.k2_notify import send

        self._nth = getattr(self, "_nth", 0) + 1
        when = when or (timezone.now() - timedelta(seconds=600 * self._nth))
        result = record_detection(
            scope=self.scope_pipe, stream_monitor_id=stream.pk,
            event_type="fire", severity="critical", occurred_at=when,
            snapshot_path=f"minio://k4/{self._nth}.jpg")
        send(scope=scope, event_id=result.event_id)
        return result.event_id


class _RecordingRenderer:
    """받은 HTML 을 그대로 들고 있는 렌더러. 실제 PDF 엔진을 부르지 않는다."""

    name = "weasyprint"

    def __init__(self) -> None:
        self.seen: list[str] = []

    def render(self, *, html: str):
        from kernels.k4_report.renderers import RenderOutcome

        self.seen.append(html)
        return RenderOutcome(True, pdf=b"%PDF-1.4 k4-test")


class _EmptyPdfRenderer:
    """0바이트를 내는 엔진. **성공으로 세면 안 된다** (D-284)."""

    name = "weasyprint"

    def render(self, *, html: str):
        from kernels.k4_report.renderers import RenderOutcome

        return RenderOutcome(True, pdf=b"")


# ═══════════════════════════════════════════════════════════════════════════
# [F-11 계약 AC] — 치환 변수 3종
# ═══════════════════════════════════════════════════════════════════════════
class RequiredVariablesTest(K4Fixture):
    """★ 이벤트 · 조치 · 캡처가 **자동으로** 다 모이는가."""

    def test_context_carries_all_three_contract_variables(self) -> None:
        from kernels.k4_report import REQUIRED_VARIABLES, build_context

        self._event_with_delivery(self.stream_a, self.scope_a)
        ctx = build_context(scope=self.scope_a,
                            since=timezone.now() - timedelta(days=1))

        for name in REQUIRED_VARIABLES:
            self.assertTrue(hasattr(ctx, name), f"F-11 변수 {name} 가 없습니다.")
        self.assertEqual((), ctx.missing_variables)
        self.assertTrue(ctx.events, "이벤트가 안 모였습니다.")
        self.assertTrue(ctx.actions, "조치(발송 이력)가 안 모였습니다.")
        self.assertTrue(ctx.captures, "캡처가 안 모였습니다.")

    def test_actions_come_from_k2_not_a_second_ledger(self) -> None:
        """★ **두 벌로 적재하지 않는다** (DA-04 §2 K2 이중 AC).

        보고서의 조치 행과 K2 의 발송 이력이 **같은 행**인지 id 로 확인한다.
        따로 만들었다면 id 가 갈린다.
        """
        from kernels.k2_notify import list_deliveries
        from kernels.k4_report import build_context

        event_id = self._event_with_delivery(self.stream_a, self.scope_a)
        since = timezone.now() - timedelta(days=1)

        ctx = build_context(scope=self.scope_a, since=since)
        k2_rows = list_deliveries(scope=self.scope_a, since=since)

        self.assertEqual(
            [d.delivery_id for d in k2_rows],
            [a.delivery_id for a in ctx.actions],
            "보고서의 조치 행이 K2 의 발송 이력과 다릅니다 — 두 벌로 적재했습니다.")
        self.assertEqual({event_id}, {a.event_id for a in ctx.actions})

    def test_template_vars_always_include_the_three_keys(self) -> None:
        """0건이어도 키를 빼지 않는다 — 빼면 템플릿이 조용히 빈 문자열을 그린다."""
        from kernels.k4_report import build_context

        ctx = build_context(scope=self.scope_a,
                            since=timezone.now() - timedelta(minutes=1))
        variables = ctx.as_template_vars()
        for key in ("events", "actions", "captures"):
            self.assertIn(key, variables, f"{key} 키가 빠졌습니다.")

    def test_failed_action_source_is_not_reported_as_no_actions(self) -> None:
        """★ 이 파일에서 가장 중요한 시험.

        "조치가 없었다"와 "조치를 못 가져왔다"는 **다른 사실**이다. 둘을 빈 목록으로
        뭉개면 발송 조회가 실패한 보고서가 "조치 없음"으로 인쇄돼 나간다 (D-290).
        """
        from unittest import mock

        from kernels.k4_report import build_context

        self._event_with_delivery(self.stream_a, self.scope_a)
        with mock.patch("kernels.k2_notify.list_deliveries",
                        side_effect=RuntimeError("발송 이력 조회 실패")):
            ctx = build_context(scope=self.scope_a,
                                since=timezone.now() - timedelta(days=1))

        self.assertEqual((), ctx.actions, "실패했는데 조치 행이 생겼습니다.")
        self.assertTrue(
            any(s.startswith("actions") for s in ctx.sources_failed),
            "조치 출처 실패가 기록되지 않았습니다 — 빈 목록과 구별되지 않습니다.")
        self.assertFalse(ctx.is_complete,
                         "출처가 실패했는데 완전한 컨텍스트로 보고합니다.")

    def test_empty_actions_is_complete_but_failed_is_not(self) -> None:
        """★ 양성 대조 — **진짜로 0건일 때는 완전해야 한다** (D-277).

        전부 불완전으로 표시하면 위의 시험은 아무것도 증명하지 않는다.
        """
        from kernels.k4_report import build_context

        ctx = build_context(scope=self.scope_a,
                            since=timezone.now() - timedelta(minutes=1))
        self.assertEqual((), ctx.actions)
        self.assertEqual((), ctx.sources_failed)
        self.assertTrue(ctx.is_complete,
                        "조치가 0건인 것을 실패로 봤습니다 — 대기와 신고를 뒤집었습니다.")


# ═══════════════════════════════════════════════════════════════════════════
# [U2 상품 AC] — 10분은 **사람의 작업 시간**이다
# ═══════════════════════════════════════════════════════════════════════════
class ManualWorkTest(K4Fixture):
    """★ 재는 것은 초가 아니라 **손으로 채울 칸의 개수**다 (DA-04 §2 K4)."""

    def test_no_field_needs_manual_entry(self) -> None:
        from kernels.k4_report import build_context

        self._event_with_delivery(self.stream_a, self.scope_a)
        ctx = build_context(scope=self.scope_a,
                            since=timezone.now() - timedelta(days=1))
        self.assertEqual(
            (), ctx.manual_fields,
            f"사람이 손으로 옮겨 적어야 하는 칸이 {len(ctx.manual_fields)}개 남았습니다: "
            f"{ctx.manual_fields}. U2 의 10분은 그 수가 0 일 때 달성됩니다 (DA-04 §2 K4).")

    def test_incomplete_context_is_refused_by_default(self) -> None:
        """불완전한 컨텍스트로 **기본값으로는 인쇄하지 않는다.** 종이는 되돌릴 수 없다."""
        from kernels.k4_report import InvalidReportInput, ReportContext, render

        broken = ReportContext(
            since=timezone.now() - timedelta(days=1), until=timezone.now(),
            sources_failed=("actions: RuntimeError",))
        with self.assertRaises(InvalidReportInput):
            render(scope=self.scope_a, template_id=self.tpl_a.pk, context=broken)

    def test_incomplete_can_be_printed_only_when_said_out_loud(self) -> None:
        """찍어야 한다면 **명시적으로** 말한다 — 그리고 실패 사실이 본문에 실린다."""
        from kernels.k4_report import ReportContext, render, renderers

        recorder = _RecordingRenderer()
        undo = renderers.register(recorder)
        self.addCleanup(undo)

        broken = ReportContext(
            since=timezone.now() - timedelta(days=1), until=timezone.now(),
            sources_failed=("actions: RuntimeError",))
        pdf = render(scope=self.scope_a, template_id=self.tpl_a.pk,
                     context=broken, allow_incomplete=True)
        self.assertTrue(pdf)
        self.assertIn("actions: RuntimeError", recorder.seen[0],
                      "불완전 사실이 보고서 본문에 실리지 않았습니다 — "
                      "받는 사람이 완전한 줄 압니다.")


# ═══════════════════════════════════════════════════════════════════════════
# 렌더 — 빈 PDF 는 성공이 아니다
# ═══════════════════════════════════════════════════════════════════════════
class RenderTest(K4Fixture):

    def test_render_returns_pdf_bytes(self) -> None:
        from kernels.k4_report import build_context, render, renderers

        undo = renderers.register(_RecordingRenderer())
        self.addCleanup(undo)

        self._event_with_delivery(self.stream_a, self.scope_a)
        ctx = build_context(scope=self.scope_a,
                            since=timezone.now() - timedelta(days=1))
        pdf = render(scope=self.scope_a, template_id=self.tpl_a.pk, context=ctx)
        self.assertTrue(pdf.startswith(b"%PDF"), "PDF 가 아닙니다.")

    def test_zero_byte_pdf_is_a_failure_not_a_success(self) -> None:
        """★ 0바이트 PDF 는 열리기는 하고 내용이 없다 — **조용한 성공**이다 (D-284)."""
        from kernels.k4_report import RenderFailed, build_context, render, renderers

        undo = renderers.register(_EmptyPdfRenderer())
        self.addCleanup(undo)

        ctx = build_context(scope=self.scope_a,
                            since=timezone.now() - timedelta(minutes=1))
        with self.assertRaises(RenderFailed):
            render(scope=self.scope_a, template_id=self.tpl_a.pk, context=ctx)

    def test_usage_count_rises_only_on_success(self) -> None:
        """실패까지 세면 U2 의 분모가 부푼다."""
        from kernels.k4_report import RenderFailed, build_context, render, renderers

        Template = apps.get_model("report_template", "ReportTemplate")
        before = Template._base_manager.get(pk=self.tpl_a.pk).usage_count

        undo = renderers.register(_EmptyPdfRenderer())
        ctx = build_context(scope=self.scope_a,
                            since=timezone.now() - timedelta(minutes=1))
        with self.assertRaises(RenderFailed):
            render(scope=self.scope_a, template_id=self.tpl_a.pk, context=ctx)
        undo()
        self.assertEqual(
            before, Template._base_manager.get(pk=self.tpl_a.pk).usage_count,
            "실패한 렌더가 사용 횟수를 올렸습니다.")

        undo2 = renderers.register(_RecordingRenderer())
        self.addCleanup(undo2)
        render(scope=self.scope_a, template_id=self.tpl_a.pk, context=ctx)
        self.assertEqual(
            before + 1, Template._base_manager.get(pk=self.tpl_a.pk).usage_count,
            "성공했는데 사용 횟수가 안 올랐습니다 — 양성 대조 실패.")


# ═══════════════════════════════════════════════════════════════════════════
# 격리 — 템플릿에는 고객사 로고와 문구가 들어간다
# ═══════════════════════════════════════════════════════════════════════════
class KernelTenantScopeTest(K4Fixture):

    def test_positive_control_own_template_is_listed(self) -> None:
        from kernels.k4_report import list_templates

        ids = {t.template_id for t in list_templates(scope=self.scope_a)}
        self.assertIn(self.tpl_a.pk, ids, "자기 템플릿을 못 찾았습니다.")

    def test_other_tenant_template_is_never_listed(self) -> None:
        from kernels.k4_report import list_templates

        ids = {t.template_id for t in list_templates(scope=self.scope_a)}
        self.assertNotIn(self.tpl_b.pk, ids,
                         "남의 템플릿이 보입니다 — 템플릿에는 고객사 로고·문구가 들어갑니다.")

    def test_render_with_another_tenants_template_is_404(self) -> None:
        """쓰기 쪽 IDOR — 남의 템플릿으로 찍을 수 없다 (D-290)."""
        from django.http import Http404

        from kernels.k4_report import build_context, render

        ctx = build_context(scope=self.scope_a,
                            since=timezone.now() - timedelta(minutes=1))
        with self.assertRaises(Http404):
            render(scope=self.scope_a, template_id=self.tpl_b.pk, context=ctx)

    def test_context_never_contains_another_tenants_actions(self) -> None:
        from kernels.k4_report import build_context

        self._event_with_delivery(self.stream_b, self.scope_b)
        ctx = build_context(scope=self.scope_a,
                            since=timezone.now() - timedelta(days=1))
        self.assertEqual((), ctx.actions,
                         "남의 테넌트 발송 이력이 우리 보고서에 들어왔습니다.")

    def test_system_scope_cannot_build_or_list(self) -> None:
        from common.tenant_scope import SystemScopeCannotRead

        from kernels.k4_report import build_context, list_templates

        for call in (lambda: list_templates(scope=self.scope_pipe),
                     lambda: build_context(scope=self.scope_pipe)):
            with self.assertRaises(SystemScopeCannotRead):
                call()


class HonestAbsenceTest(K4Fixture):
    """구현이 없는 공개 면은 **성공을 반환하지 않는다** (D-284)."""

    def test_render_period_raises_instead_of_returning_empty(self) -> None:
        from kernels.k4_report import NotImplementedYet, render_period

        with self.assertRaises(NotImplementedYet) as caught:
            render_period(scope=self.scope_a, template_id=self.tpl_a.pk,
                          since=timezone.now() - timedelta(days=30),
                          until=timezone.now())
        self.assertIn("두 벌", str(caught.exception),
                      "왜 아직 안 만들었는지를 말하지 않습니다.")


class OpenIssuePremiseTest(TestCase):
    """★ **DA-01 OPEN-03 의 전제를 시험으로 못박는다** (D-210 실측 우선).

    OPEN-03: *"`ReportTemplate` 은 `BaseModel` 상속 — group 격리 없음"*
    실측은 다르다 — 실행 중인 dj-core 의 `BaseModel` 이 **이미** `group` FK 와
    `CustomManagerGroup` 을 갖고, `BaseModelWithGroup` 은 그 파일에서
    **DEPRECATED** 로 표시된 채 필드를 하나도 더 정의하지 않는다.

    이 시험이 있는 이유: 전제가 바뀌면(사내 패키지가 갱신되어 정말로 갈리면)
    **여기서 멈춰야** 한다. 문서만 고쳐 두면 아무도 모른다 (D-286).
    """

    def test_report_template_has_the_same_isolation_as_grouped_models(self) -> None:
        from tests.test_tenant_isolation import has_group_fk, has_group_m2m

        Template = apps.get_model("report_template", "ReportTemplate")
        self.assertTrue(
            has_group_fk(Template) or has_group_m2m(Template),
            "ReportTemplate 에 테넌트 필드가 없습니다 — OPEN-03 의 전제가 참이 됐습니다. "
            "그렇다면 기저 클래스 전환과 백필을 다시 판단해야 합니다.")

    def test_base_model_and_base_model_with_group_declare_the_same_tenant_field(self) -> None:
        from core.base import BaseModel, BaseModelWithGroup

        def tenant_fields(model):
            return {f.name for f in model._meta.get_fields()
                    if getattr(f, "name", None) in ("group", "groups")}

        self.assertEqual(
            tenant_fields(BaseModel), tenant_fields(BaseModelWithGroup),
            "BaseModel 과 BaseModelWithGroup 의 테넌트 필드가 갈렸습니다 — "
            "OPEN-03 정정(2026-08-30)의 근거가 무너졌습니다. 다시 실측하십시오.")


class KernelScopeSignatureTest(TestCase):
    """[D-281] 커널 공개 함수는 **스코프 없이는 호출 자체가 불가능**해야 한다."""

    def test_every_public_function_refuses_to_run_without_scope(self) -> None:
        import inspect

        from kernels import k4_report

        problems = []
        for name in ("render", "build_context", "list_templates", "render_period"):
            sig = inspect.signature(getattr(k4_report, name))
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
    """DA-04 §2 K4 표가 정한 공개 면 3개가 **실재하는가.**"""

    #: DA-04 §2 K4 의 "공개 면" 열 그대로.
    SURFACE = ["render", "build_context", "list_templates"]

    def test_public_surface_matches_da04(self) -> None:
        from kernels import k4_report

        missing = [n for n in self.SURFACE if not hasattr(k4_report, n)]
        self.assertEqual(
            [], missing,
            f"DA-04 §2 K4 표의 공개 면이 커널에 없습니다: {missing}\n"
            "표를 바꾸려면 DA-04 와 이 목록을 **같은 커밋에서** 함께 고치십시오.")

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

    def test_engine_is_reached_through_the_registry_only(self) -> None:
        """★ 커널 코드에 App 이름이 나오는 자리를 **한 곳으로 몰았는가.**

        `verify_layers.py` 는 지금 이 위반을 못 본다 — 그 검사는 `apps.` 로 시작하는
        import 를 찾는데 이 저장소의 App 은 최상위에 있다(대상 0건 · D-285 (3)).
        **보이지 않는다고 없는 것이 아니므로** 여기서 설계로 지킨다.
        """
        import ast
        from pathlib import Path

        import kernels.k4_report as pkg

        # ★ 문자열이 아니라 **AST** 로 본다. 줄 단위 문자열 검사는 독스트링 안의
        #   **예시 코드**를 위반으로 잡았다(실측: `__init__.py` 의 "이러면 경계가 사라진다"
        #   예시). 오탐하는 탐지기는 곧 아무도 안 믿는 탐지기가 된다 — D-277 이 양성 대조를
        #   요구하는 이유가 이것이고, 여기서는 그 반대 방향(오탐)을 고쳤다.
        root = Path(pkg.__file__).parent
        offenders = []
        for path in sorted(root.glob("*.py")):
            if path.name == "renderers.py":
                continue          # 엔진을 찾는 유일한 자리 — 여기만 허용한다
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                for name in names:
                    if name.split(".")[0] == "report_template":
                        offenders.append(f"{path.name}:{node.lineno}: {name}")
        self.assertEqual(
            [], offenders,
            f"커널이 App 을 직접 가져옵니다: {offenders}. 엔진은 renderers.py 의 "
            "레지스트리를 통해서만 만납니다 — 그래야 엔진을 갈아 끼울 수 있습니다.")
