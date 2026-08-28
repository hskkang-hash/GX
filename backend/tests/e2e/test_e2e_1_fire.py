# -*- coding: utf-8 -*-
"""E2E-1 화재 — **프레임 투입부터 알림 발송까지** (D-291).

계약 [별첨1] 8장 시나리오 1종. 2027.1 통합시험의 과녁을 **지금부터 자동으로 쌓는다** —
그때 수동 시연을 하지 않기 위해서다.

지금 도는 단계 (1~6) — 나머지는 커널이 붙을 때 늘어난다
------------------------------------------------------
    1. 프레임 투입 → AI 탐지 결과가 파이프라인에 들어온다
    2. K1 이벤트 기록 — 소유가 스트림에서 물려진다
    3. F-04 판정 — 동일 이벤트 5분 내 중복 알림 0건
    4. K2 수신자 결정 — 등급 × 역할 수신그룹
    5. K2 발송 기록 — occurred_at → sent_at **30초 이내** (F-10)
    6. K6 피드백 — 판정이 오탐률 분모·분자로 돌아온다
    8. K3 대시보드 프레임 — 프리셋 도달 0클릭 · 패널 5상태
    10. K4 보고서 PDF — 이벤트·조치·캡처 치환 (조치는 **K2 의 그 행 그대로**)
    7 · 9. SDN QoS · 영상 3초 — **해금 전**. 등재부가 자동으로 늘린다.

★ 9단계(영상 3초)를 8단계에서 **떼어냈다.** K3 가 붙었다고 영상이 측정되는 것이 아니다 —
  재생 경로가 아직 없다. 한 칸에 두면 프레임이 초록일 때 영상까지 초록으로 읽힌다.

★ 왜 "지금 도는 단계"를 코드가 정하나
  단계를 손으로 켜고 끄면 누군가 끄고 잊는다. `e2e_contract.SCENARIOS` 가 커널
  패키지의 **import 가능 여부**로 해금을 판정하고, 이 파일은 그 판정을 읽는다 —
  K3 가 붙는 순간 8단계가 계획에 들어오고, 시험이 그것을 **미측정으로 표에 낸다.**

공통 규약 (D-291) — 하나라도 빠지면 E2E 로 인정하지 않는다
--------------------------------------------------------
  ① 실 마이그레이션 DB — `test_runs_on_migrated_database` 가 **표를 DB 에 직접 묻는다**
  ② 격리 양방향 — `test_isolation_read_and_write_are_blocked`
  ③ 양성 대조 — `test_positive_control_without_the_event`
  ④ 저하 변형 — `test_degraded_variant_keeps_core_path`
  ⑤ 논리 시계 — `sleep` 을 쓰지 않는다. 시각은 `occurred_at` 을 **주어서** 만든다
  ⑥ 증거 — `docs/agent/evidence/e2e/E2E-1/steps.md` 에 단계표를 남긴다
"""
from __future__ import annotations

import contextlib
from datetime import timedelta

from django.apps import apps
from django.core import mail
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from tests.e2e.e2e_contract import SCENARIOS, StepLedger

#: 규약이 요구하는 모듈 변수 (`e2e_contract.REQUIRED_ATTRS`).
SCENARIO = "E2E-1"

#: ★ D-289 — **양성 대조의 표본은 저장소 실물에서 뽑는다.**
#:   이 E2E 는 합성 더미를 부르지 않는다. 아래 이름들이 실제 산출 경로이고,
#:   양성 대조는 그중 하나(K1 기록)를 빼는 것으로 만든다.
REAL_SAMPLE = (
    "kernels.k1_event.record_detection · kernels.k2_notify.send · "
    "kernels.k6_feedback.false_positive_rate — 저장소의 실제 커널 공개 면"
)


class _FireScenario(TestCase):
    """화재 시나리오의 픽스처 — 테넌트 A(우리) · 테넌트 B(남).

    ⚠ `--nomigrations` 없이 돈다 (규약 ①). 그래서 느리다. 느린 것이 요점이다 —
      착시 ⑤(D-282)는 **빠른 경로가 실물과 다른 자리에서 재고 있었다**는 사실이었다.
    """

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        UserGroup = apps.get_model("user", "UserGroup")

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="e2e1-tenant-A")
        cls.group_b = UserGroup.objects.create(name="e2e1-tenant-B")
        UserGroup.objects.filter(pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.role_a = cls._own(cls._role("e2e1_watch_a"), cls.group_a)
        cls.role_b = cls._own(cls._role("e2e1_watch_b"), cls.group_b)
        cls.user_a = cls._user("e2e1_user_a", cls.group_a, cls.role_a)
        cls.user_b = cls._user("e2e1_user_b", cls.group_b, cls.role_b)
        cls.stream_a = cls._stream("e2e1-cam-A", cls.group_a)
        cls.stream_b = cls._stream("e2e1-cam-B", cls.group_b)
        cls._rule(cls.group_a, cls.role_a)
        cls._rule(cls.group_b, cls.role_b)

        from common.tenant_scope import TenantScope

        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)
        cls.scope_pipe = TenantScope.system(
            reason="E2E-1 프레임 투입 — gRPC 검출 콜백에는 요청자가 없다 (D-281)")

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
            name=name, code=name, ip_source="rtsp://e2e.invalid/fire"), group)

    @classmethod
    def _rule(cls, group, role):
        Rule = apps.get_model("stream_monitors", "NotificationRule")
        return cls._own(Rule.objects.create(
            severity="critical", role=role, channels=["email"], is_active=True), group)

    def _report_template(self):
        """A 테넌트의 보고서 템플릿 하나. 세 변수를 **전부 자리 잡아 둔다.**"""
        Template = apps.get_model("report_template", "ReportTemplate")
        return self._own(Template.objects.create(
            name="e2e1-화재보고", is_default=False, is_enabled=True,
            template=("<h1>화재 상황보고</h1>"
                      "<section>{{ events }}</section>"
                      "<section>{{ actions }}</section>"
                      "<section>{{ captures }}</section>"),
        ), self.group_a)

    # ── 프레임 투입 — 1단계 ──────────────────────────────────────────────
    @staticmethod
    def _frame_detection(*, label="fire", confidence=0.93):
        """AI 가 돌려주는 검출 하나의 모양.

        `frame_detection.proto` 실측(D-284): `x·y·width·height·label·confidence·color`.
        **severity 는 proto 에 없다** — 그래서 배선이 매핑한다 (P-W2-2-1 잠정 A안).
        여기서 그 사실을 다시 적는 이유는, 이 E2E 가 언젠가 AI 서버 응답으로
        바뀔 때 무엇이 추가돼야 하는지가 여기서 보이게 하기 위해서다.
        """
        return {"x": 0.31, "y": 0.44, "width": 0.12, "height": 0.20,
                "label": label, "confidence": confidence, "color": "#ff0000"}


class E2E1FireTest(_FireScenario):
    """★ 화재 시나리오 본체 — 단계표를 남기며 끝까지 간다."""

    def setUp(self) -> None:
        self.ledger = StepLedger(scenario=SCENARIO)
        self.scenario = SCENARIOS[SCENARIO]

    def tearDown(self) -> None:
        # ★ 규약 ⑥ — 성공이든 실패든 **어디까지 갔는지**를 남긴다 (D-274 의 E2E 판).
        #
        # 단계를 하나도 기록하지 않은 시험(규약 ①~④ 의 보조 시험들)은 **쓰지 않는다.**
        # 쓰면 마지막에 돈 보조 시험이 본 시나리오의 표를 "0/6 도달" 로 덮어쓴다 —
        # 실측으로 그렇게 됐다. 빈 표를 증거로 남기면 그것은 증거가 아니라 **오보**다.
        if not self.ledger.rows:
            return
        with contextlib.suppress(Exception):
            self.ledger.write_evidence(self.scenario)

    def _step(self, no: int):
        return next(s for s in self.scenario.steps if s.no == no)

    def test_fire_scenario_runs_end_to_end(self) -> None:
        """프레임 투입 → 이벤트 → F-04 → 수신자 → 30초 발송 → 오탐률."""
        from kernels.k1_event import query_events, record_detection
        from kernels.k2_notify import resolve_recipients, send, suppress
        from kernels.k6_feedback import false_positive_rate, record_feedback

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        now = timezone.now()

        # ── 1. 프레임 투입 ────────────────────────────────────────────
        detection = self._frame_detection()
        self.assertEqual("fire", detection["label"])
        self.ledger.record(self._step(1), True, "proto 실측 모양 그대로")

        # ── 2. K1 이벤트 기록 ─────────────────────────────────────────
        first = record_detection(
            scope=self.scope_pipe, stream_monitor_id=self.stream_a.pk,
            event_type=detection["label"], severity="critical", occurred_at=now,
            confidence=detection["confidence"],
            bbox={k: detection[k] for k in ("x", "y", "width", "height")},
            snapshot_path="minio://e2e1/frame-0001.jpg",
        )
        self.assertTrue(first.created, "검출이 이벤트로 기록되지 않았습니다.")
        row = Event._base_manager.get(pk=first.event_id)
        self.assertEqual(self.stream_a.pk, row.stream_monitor_id)
        self.ledger.record(self._step(2), True, f"event_id={first.event_id}")

        # ── 3. F-04 — 5분 내 중복 알림 0건 ────────────────────────────
        #    ★ 논리 시계 (규약 ⑤): 30초를 **기다리지 않는다.** 두 번째 검출의
        #      `occurred_at` 을 30초 뒤로 **주어서** 같은 갈래를 지나간다.
        second = record_detection(
            scope=self.scope_pipe, stream_monitor_id=self.stream_a.pk,
            event_type=detection["label"], severity="critical",
            occurred_at=now + timedelta(seconds=30),
            snapshot_path="minio://e2e1/frame-0002.jpg",
        )
        self.assertTrue(first.should_notify, "첫 검출이 알림 대상이 아닙니다.")
        self.assertFalse(second.should_notify,
                         "5분 안의 두 번째 검출이 또 알림 대상입니다 — F-04 위반입니다.")
        self.ledger.record(self._step(3), True, "첫 건만 알림 대상")

        # ── 4. K2 수신자 결정 ─────────────────────────────────────────
        recipients = resolve_recipients(scope=self.scope_a, severity="critical")
        self.assertEqual([self.user_a.pk], [r.user_id for r in recipients])
        self.ledger.record(self._step(4), True, f"수신자 {len(recipients)}명")

        # ── 5. K2 발송 — F-10 30초 ────────────────────────────────────
        mail.outbox.clear()
        records = send(scope=self.scope_a, event_id=first.event_id)
        self.assertEqual(1, len(records))
        record = records[0]
        self.assertTrue(record.succeeded, f"발송 실패: {record.failure_reason}")
        self.assertTrue(
            record.meets_f10,
            f"[F-10] occurred_at → sent_at 이 30초를 넘겼습니다: {record.latency_seconds}초")
        self.assertEqual(1, len(mail.outbox), "메일이 실제로 나가지 않았습니다.")
        self.ledger.record(self._step(5), True, f"{record.latency_seconds:.2f}s ≤ 30s")

        # 두 번째 이벤트는 K2 도 접는다 — 두 창의 판정이 같은 결론에 이른다.
        self.assertTrue(suppress(scope=self.scope_a, event_id=second.event_id))

        # ── 6. K6 피드백 ──────────────────────────────────────────────
        record_feedback(first.event_id, verdict="rejected", reason="연기 아님",
                        scope=self.scope_a)
        rate = false_positive_rate(scope=self.scope_a, since=now - timedelta(hours=1))
        self.assertEqual(1, rate.total.reviewed)
        self.assertEqual(1, rate.total.rejected)
        self.assertEqual(1.0, rate.total.rate)
        self.ledger.record(self._step(6), True, "분모 1 · 분자 1")

        # 조회로도 같은 이벤트가 보인다 — 화면이 볼 것과 같은 경로 (F-05)
        found = query_events(scope=self.scope_a, since=now - timedelta(hours=1))
        self.assertIn(first.event_id, [e.event_id for e in found])

        # ── 8. K3 대시보드 프레임 ─────────────────────────────────────
        #    K3 가 붙는 순간 등재부가 이 단계를 열었다. **여는 것은 코드다** —
        #    커널 패키지가 import 되는지로 판정하므로, 사람이 켜고 끄지 못한다.
        from kernels.k3_dashboard import (
            FIVE_STATES,
            SERVER_EMITTED_STATES,
            get_preset,
            resolve_layout,
        )

        preset = get_preset(scope=self.scope_a)
        self.assertEqual(0, preset.clicks_to_reach,
                         "[U3] 로그인 직후 화면에 도달하는 클릭이 0 이 아닙니다.")
        self.assertEqual(5, len(FIVE_STATES), "[F-09] 5상태가 다섯이 아닙니다.")

        panels = resolve_layout(scope=self.scope_a)
        for panel in panels:
            self.assertIn(
                panel.state, SERVER_EMITTED_STATES,
                f"서버가 낼 수 없는 상태를 냈습니다: {panel.state}")
        self.ledger.record(
            self._step(8), True,
            f"프리셋 {preset.preset}(matched={preset.matched}) · 패널 {len(panels)}칸")

        # ── 10. K4 보고서 PDF ─────────────────────────────────────────
        #    K4 가 붙으면서 등재부가 이 단계를 열었다.
        #    ★ 여기가 재사용의 증거다 — 보고서의 "조치 이력"은 K2 의 발송 기록
        #      **그 행 그대로**다. 두 벌로 적재하지 않는다 (DA-04 §2 K2).
        from kernels.k4_report import REQUIRED_VARIABLES, build_context, render
        from kernels.k4_report import renderers as k4_renderers

        class _CapturingRenderer:
            name = "weasyprint"

            def __init__(self):
                self.html = ""

            def render(self, *, html):
                from kernels.k4_report.renderers import RenderOutcome

                self.html = html
                return RenderOutcome(True, pdf=b"%PDF-1.4 e2e1")

        capturing = _CapturingRenderer()
        undo = k4_renderers.register(capturing)
        self.addCleanup(undo)

        template = self._report_template()
        context = build_context(scope=self.scope_a, since=now - timedelta(hours=1))
        for name in REQUIRED_VARIABLES:
            self.assertTrue(hasattr(context, name),
                            f"[F-11] 치환 변수 {name} 가 없습니다.")
        self.assertTrue(context.actions,
                        "보고서에 조치 이력이 안 실렸습니다 — K2 발송 기록을 못 읽었습니다.")
        self.assertEqual(
            [r.delivery_id for r in records], [a.delivery_id for a in context.actions],
            "보고서의 조치 행이 5단계에서 만든 발송 이력과 다릅니다 — 두 벌로 적재했습니다.")
        self.assertTrue(context.captures, "[F-11] 캡처가 안 실렸습니다.")
        self.assertEqual((), context.manual_fields,
                         "[U2] 손으로 채울 칸이 남았습니다 — 10분은 그 수가 0 일 때입니다.")

        pdf = render(scope=self.scope_a, template_id=template.pk, context=context)
        self.assertTrue(pdf.startswith(b"%PDF"), "PDF 가 아닙니다.")
        self.ledger.record(
            self._step(10), True,
            f"이벤트 {len(context.events)} · 조치 {len(context.actions)} · "
            f"캡처 {len(context.captures)} · 손입력 0")

        print("\n" + self.ledger.render(self.scenario.active_steps))

    # ── 규약 ① ───────────────────────────────────────────────────────────
    def test_runs_on_migrated_database(self) -> None:
        """★ 규약 ① — **재는 자리가 실물인가** (착시 ⑤ · D-282 · D-288 ②눈).

        `--nomigrations` 는 **모델 선언에서** 테스트 DB 를 만든다. 그래서
        `DetectionEvent` 표가 실물 DB 에 없는 동안에도 초록이었다.
        여기서는 **DB 에 직접 묻는다** — 선언이 아니라 `information_schema` 다.
        """
        needed = {"stream_monitors_detectionevent",
                  "stream_monitors_notificationrule",
                  "stream_monitors_deliveryrecord"}
        present = set(connection.introspection.table_names())
        missing = sorted(needed - present)
        self.assertEqual(
            [], missing,
            f"이 E2E 가 도는 DB 에 표가 없습니다: {missing}\n"
            "E2E 는 `--nomigrations` 없이 돌아야 합니다 (D-291 규약 ①). "
            "빠른 경로가 실물과 다른 자리에서 재고 있으면 그 초록은 실물을 말하지 않습니다.")

        # 마이그레이션 그래프까지 함께 본다 — 표가 있어도 **미적용 마이그레이션**이
        # 남아 있으면 이 DB 는 정본 스키마가 아니다 (D-288 ②눈).
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)
        self.assertEqual([], plan,
                         f"미적용 마이그레이션이 {len(plan)}건 남아 있습니다 — "
                         "이 DB 는 정본 스키마가 아닙니다 (D-288 ②눈).")

    # ── 규약 ② ───────────────────────────────────────────────────────────
    def test_isolation_read_and_write_are_blocked(self) -> None:
        """★ 규약 ② — **읽기·쓰기 양방향** (D-290).

        전 단계의 산출물(이벤트 · 발송 이력 · 오탐률)을 다른 테넌트 계정으로 물어
        **0건**인지 보고, 그 계정으로 **심을 수 있는지**도 본다.
        읽기만 보던 동안 쓰기가 열려 있었다 — 그것이 D-290 이 인정한 구멍이다.
        """
        from django.http import Http404

        from kernels.k1_event import query_events, record_detection
        from kernels.k2_notify import list_deliveries, send
        from kernels.k6_feedback import false_positive_rate

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        now = timezone.now()

        mine = record_detection(
            scope=self.scope_pipe, stream_monitor_id=self.stream_a.pk,
            event_type="fire", severity="critical", occurred_at=now,
            snapshot_path="minio://e2e1/iso.jpg")
        send(scope=self.scope_a, event_id=mine.event_id)

        # ── 읽기 방향 ────────────────────────────────────────────────
        self.assertEqual(
            [], [e.event_id for e in query_events(scope=self.scope_b)
                 if e.event_id == mine.event_id],
            "다른 테넌트가 우리 이벤트를 조회했습니다.")
        self.assertEqual(
            [], [d for d in list_deliveries(scope=self.scope_b)
                 if d.event_id == mine.event_id],
            "다른 테넌트가 우리 발송 이력을 조회했습니다 — 수신자 주소가 샙니다.")
        self.assertEqual(
            0, false_positive_rate(scope=self.scope_b,
                                   since=now - timedelta(hours=1)).total.unreviewed,
            "다른 테넌트의 오탐률 분모에 우리 이벤트가 섞였습니다.")

        # ── 쓰기 방향 (D-290) ────────────────────────────────────────
        before = Event._base_manager.filter(stream_monitor=self.stream_a).count()
        with self.assertRaises(Http404):
            record_detection(
                scope=self.scope_b, stream_monitor_id=self.stream_a.pk,
                event_type="fire", severity="critical",
                snapshot_path="minio://e2e1/planted.jpg")
        self.assertEqual(
            before, Event._base_manager.filter(stream_monitor=self.stream_a).count(),
            "다른 테넌트가 우리 스트림에 이벤트를 심었습니다 — 쓰기 IDOR 입니다.")
        with self.assertRaises(Http404):
            send(scope=self.scope_b, event_id=mine.event_id)

    # ── 규약 ③ ───────────────────────────────────────────────────────────
    def test_positive_control_without_the_event(self) -> None:
        """★ 규약 ③ — **이벤트를 심지 않으면 이 E2E 가 실패하는가** (D-277 · D-289).

        전부 통과하는 시험은 아무것도 증명하지 않는다. 여기서는 **1단계를 빼고**
        나머지를 그대로 돌려, 5단계(발송)가 **도달하지 못하는지**를 본다.

        표본은 합성이 아니다 — 부르는 것은 위 시험과 **같은 실물 커널 공개 면**이다
        (`REAL_SAMPLE`). 합성 더미를 세워 대조하면 "내가 만든 것만 잡는" 상태가 된다.
        """
        from kernels.k2_notify import InvalidNotifyInput, send
        from kernels.k6_feedback import false_positive_rate

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        ghost_id = (Event._base_manager.order_by("-pk").values_list("pk", flat=True)
                    .first() or 0) + 10_000

        with self.assertRaises(InvalidNotifyInput):
            send(scope=self.scope_a, event_id=ghost_id)

        rate = false_positive_rate(scope=self.scope_a,
                                   since=timezone.now() - timedelta(hours=1))
        self.assertEqual(0, rate.total.reviewed,
                         "이벤트를 심지 않았는데 분모가 0 이 아닙니다 — "
                         "이 E2E 는 자기가 만든 것 밖의 무언가를 세고 있습니다.")
        self.assertIsNone(rate.total.rate,
                          "표본이 없는데 비율이 나왔습니다 (D-290).")

    # ── 규약 ④ ───────────────────────────────────────────────────────────
    def test_degraded_variant_keeps_core_path(self) -> None:
        """★ 규약 ④ — **외부 의존을 죽여도 핵심 경로가 사는가** (W0-17 · DA2-21 (4)).

        메일 서버를 죽인다. 그래도:
          · 이벤트 기록은 된다 (관제의 핵심)
          · 발송은 **실패 이력으로 남는다** — 조용히 사라지지 않는다
          · 조회·오탐률은 그대로 답한다
        """
        from kernels.k1_event import query_events, record_detection
        from kernels.k2_notify import channels, list_deliveries, send

        class _DeadMailServer:
            name = "email"

            def send(self, *, address, subject, body):
                raise ConnectionError("E2E 저하 변형 — 메일 서버가 죽었다")

        undo = channels.register(_DeadMailServer())
        self.addCleanup(undo)

        now = timezone.now()
        result = record_detection(
            scope=self.scope_pipe, stream_monitor_id=self.stream_a.pk,
            event_type="fire", severity="critical", occurred_at=now,
            snapshot_path="minio://e2e1/degraded.jpg")
        self.assertTrue(result.created, "메일이 죽었다고 이벤트 기록이 멈췄습니다.")

        records = send(scope=self.scope_a, event_id=result.event_id)  # 예외가 나면 실패
        self.assertEqual(1, len(records))
        self.assertFalse(records[0].succeeded)
        self.assertTrue(records[0].failure_reason, "왜 못 갔는지가 비었습니다.")

        rows = list_deliveries(scope=self.scope_a, event_id=result.event_id)
        self.assertEqual(1, len(rows),
                         "실패가 이력으로 남지 않았습니다 — 조용한 유실입니다.")
        found = query_events(scope=self.scope_a, since=now - timedelta(minutes=1))
        self.assertIn(result.event_id, [e.event_id for e in found],
                      "메일 장애가 이벤트 조회까지 끌고 내려갔습니다 — 저하 운전이 아니라 "
                      "전면 정지입니다.")

    # ── 단계표가 미측정을 통과로 읽지 않는가 ─────────────────────────────
    def test_unreached_steps_are_reported_as_unmeasured(self) -> None:
        """해금 전 단계(7~9)를 **통과로 세지 않는다.**

        E2E 는 길다. "6/9 통과"라고만 적으면 나머지 셋이 실패인지 미측정인지 모른다.
        미측정을 통과로 읽는 것이 이 저장소가 반복해서 만난 실패 모양이다 (D-274).
        """
        planned = self.scenario.steps
        active = self.scenario.active_steps
        table = self.ledger.render(planned)

        self.assertLess(len(active), len(planned),
                        "모든 단계가 해금됐다면 이 시험을 지우고 전 단계를 재십시오.")
        self.assertIn("미측정", table, "해금 전 단계가 표에 미측정으로 나오지 않습니다.")
        for step in planned:
            self.assertIn(step.title[:20], table,
                          f"{step.no}단계가 표에서 빠졌습니다 — 빠진 줄은 보이지 않습니다.")
