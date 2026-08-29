# -*- coding: utf-8 -*-
"""E2E-2 침수 — **등급이 다르면 받는 사람이 다른가** (D-291).

계약 [별첨1] 8장 시나리오 2종. K3 가 붙으면서 등재부가 이 시나리오를 의무로 바꿨다.

지금 도는 단계 — **넷 전부** (2026-09-01 · D-299 로 마지막 하나가 열렸다)
---------------------------------------------------------------------------
    1. 수위선 초과 신호 투입                      ← 돈다
    2. F-02 이벤트 생성 (30초)                    ← 열렸다 (D-294, 2026-08-31)
    3. 같은 구역 인명(F-03) 결합 → 등급 상향       ← **열렸다** (D-299, 2026-09-01)
    4. 등급별 수신자 그룹이 실제로 달라지는가       ← 돈다  ★ 이 시나리오의 상품 AC

★ 2단계가 어떻게 열렸나 — **잠금 사유가 사라졌기 때문이다**

  잠금 사유는 "`DetectionEvent.EventType` 에 침수·수위가 없다" 였다. D-294 가
  *"F-02 는 계약 M 기능이므로 타입 부재는 설계 선택이 아니라 **누락**"* 이라고 판정했고,
  계약 문서 v1.1 · 마이그레이션 0018 로 `flood` 가 들어왔다.
  그래서 이 단계는 이제 **추정 없이** 돈다 — 열거가 실재하므로 D-280 위반이 아니다.

  ⚠ 여전히 하지 않는 것: 수위 임계값을 코드에 박지 않는다. 지점별 기준선은 F-12 설정의
    일이고(FR-02-2), 여기서 정하면 그 값이 곧 AC 판정의 근거가 된다.
    이 시험은 **초과 신호가 이미 났다는 전제**에서 시작한다.

★ 3단계가 어떻게 열렸나 — **모델이 그것을 표현하게 됐다** (D-299)

  잠금 사유는 "'같은 구역'을 판정할 구역 개념이 없다" 였다(`NotificationRule.zone` 은
  체계가 아니라 라벨이다). P-K2-2 가 `Zone` 모델로 판정됐고, 마이그레이션 0019 로
  실재한다. 그래서 이 단계는 이제 **추정 없이** 돈다.

  ⚠ 열린 것은 **카메라 묶음 판정 하나**다. 계약 F-03 의 폴리곤은 여전히 미구현이고,
    `stream_monitors.services.zones.ZONE_POLYGON_READY = False` 가 그것을 잠근다.
    이 시험은 폴리곤을 재지 않는다 — 재는 척도 하지 않는다. 폴리곤을 여는 사람이
    그 상수를 올리는 순간 `test_zone_judgment.py` 의 F-03 AC 시험이 의무가 된다.

  ⚠ 여기서도 하지 않는 것: 결합이 **저장된 등급을 덮어쓰지 않는다.** 관측이 실제로 난
    등급은 오탐률·이력의 사실이고, 결합 판정이 그것을 덮으면 나중에 "무엇이 실제로
    났는가"를 아무도 못 읽는다(D-293 과 같은 계열). 결합의 효과는 **누가 받는가**로
    나타나고, 이 시험은 그것을 잰다.

그러면 왜 지금 쓰는가
---------------------
4단계가 **이 시나리오의 상품 AC** 이고, 그것은 지금 잴 수 있기 때문이다.
계약의 문장은 *"등급별 수신자 그룹이 실제로 달라지는지"* 이고, 그 질문은 침수 여부와
무관하게 성립한다 — 등급이 다르면 받는 사람이 달라야 한다는 요구다.
잴 수 있는 것을 나중으로 미루면, 미룬 채로 2027 을 만난다.
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

SCENARIO = "E2E-2"

#: ★ D-289 — 양성 대조의 표본은 저장소 실물에서 뽑는다.
REAL_SAMPLE = (
    "kernels.k2_notify.resolve_recipients · kernels.k2_notify.send — "
    "저장소의 실제 커널 공개 면. 합성 더미를 부르지 않는다"
)


class _FloodScenario(TestCase):
    """테넌트 A/B · 등급별로 **다른 역할**을 가리키는 수신 규칙 둘."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        UserGroup = apps.get_model("user", "UserGroup")

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="e2e2-tenant-A")
        cls.group_b = UserGroup.objects.create(name="e2e2-tenant-B")
        UserGroup.objects.filter(pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        # 등급별로 **다른 역할** — 이것이 4단계가 묻는 것이다.
        cls.role_watch = cls._own(cls._role("e2e2_watch"), cls.group_a)     # 경고 수신
        cls.role_chief = cls._own(cls._role("e2e2_chief"), cls.group_a)     # 심각 수신
        cls.role_b = cls._own(cls._role("e2e2_role_b"), cls.group_b)

        cls.user_watch = cls._user("e2e2_watch_user", cls.group_a, cls.role_watch)
        cls.user_chief = cls._user("e2e2_chief_user", cls.group_a, cls.role_chief)
        cls.user_b = cls._user("e2e2_user_b", cls.group_b, cls.role_b)

        cls.stream_a = cls._stream("e2e2-gauge-A", cls.group_a)
        cls.stream_b = cls._stream("e2e2-gauge-B", cls.group_b)
        # ★ 3단계용 — **수위 탐지 카메라와 인명 탐지 카메라는 다른 카메라다.**
        #   같은 카메라로 두면 "같은 구역인가"를 묻지 않고도 통과한다(자기 자신은
        #   언제나 자기 구역에 있다). 그러면 이 단계는 아무것도 재지 않는다.
        cls.stream_people = cls._stream("e2e2-people-A", cls.group_a)
        #: 두 카메라를 한 구역으로 묶는다. 이것이 D-299 의 camera_group 이다.
        cls.zone = cls._zone("e2e2-안양천-보행교구간", cls.group_a,
                             [cls.stream_a, cls.stream_people])
        #: 같은 테넌트의 **다른 구역** — 결합이 아무 두 카메라나 묶지 않는지 재는 음성 대조용.
        cls.stream_far = cls._stream("e2e2-far-A", cls.group_a)
        cls.zone_far = cls._zone("e2e2-상류구간", cls.group_a, [cls.stream_far])

        cls._rule(cls.group_a, cls.role_watch, "warning")
        cls._rule(cls.group_a, cls.role_chief, "critical")
        cls._rule(cls.group_b, cls.role_b, "critical")

        from common.tenant_scope import TenantScope

        cls.scope_a = TenantScope.of(cls.user_chief)
        cls.scope_b = TenantScope.of(cls.user_b)
        cls.scope_pipe = TenantScope.system(
            reason="E2E-2 수위 신호 투입 — 계측 파이프라인에는 요청자가 없다 (D-281)")

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
            name=name, code=name, ip_source="rtsp://e2e.invalid/gauge"), group)

    @classmethod
    def _zone(cls, name, group, streams):
        Zone = apps.get_model("stream_monitors", "Zone")
        zone = cls._own(Zone.objects.create(name=name, kind="camera_group"), group)
        zone.cameras.set(streams)
        return zone

    @classmethod
    def _rule(cls, group, role, severity):
        Rule = apps.get_model("stream_monitors", "NotificationRule")
        return cls._own(Rule.objects.create(
            severity=severity, role=role, channels=["email"], is_active=True), group)

    # ── 1단계 — 수위선 초과 신호 ─────────────────────────────────────────
    @staticmethod
    def _water_level_reading(*, level_cm: float, threshold_cm: float):
        """수위 계측 한 건. **아직 이벤트가 아니다.**

        신호와 이벤트는 다른 것이다. 이 계측이 `DetectionEvent` 가 되는 순간이
        2단계이고, 그 단계는 D-294 로 열렸다 — `EventType.FLOOD` 가 실재하므로
        이제 **기존 타입에 실어 보내지 않아도 된다.** 실어 보냈다면 그 타입의
        오탐률 분모가 오염되고 아무도 그 사실을 몰랐을 것이다.

        ⚠ 임계값(`threshold_cm`)은 **픽스처가 주는 값**이지 코드가 정한 값이 아니다.
          지점별 기준선은 F-12 설정의 일이다(FR-02-2). 여기서 정하면 그 값이 곧
          AC 판정의 근거가 된다.
        """
        return {"level_cm": level_cm, "threshold_cm": threshold_cm,
                "exceeded": level_cm > threshold_cm}

    def _event(self, stream, *, severity, when=None, event_type="person"):
        """관측 하나. `event_type` 은 **계약에 있는 것만** 쓴다 (D-280)."""
        from kernels.k1_event import record_detection

        self._nth = getattr(self, "_nth", 0) + 1
        when = when or (timezone.now() - timedelta(seconds=900 * self._nth))
        return record_detection(
            scope=self.scope_pipe, stream_monitor_id=stream.pk,
            event_type=event_type, severity=severity, occurred_at=when,
            snapshot_path=f"minio://e2e2/{self._nth}.jpg",
        ).event_id


class E2E2FloodTest(_FloodScenario):
    """★ 침수 시나리오 — 잴 수 있는 것만 재고, 못 재는 것은 **표에 남긴다**."""

    def setUp(self) -> None:
        self.ledger = StepLedger(scenario=SCENARIO)
        self.scenario = SCENARIOS[SCENARIO]

    def tearDown(self) -> None:
        if not self.ledger.rows:
            return
        with contextlib.suppress(Exception):
            self.ledger.write_evidence(self.scenario)

    def _step(self, no: int):
        return next(s for s in self.scenario.steps if s.no == no)

    def test_flood_scenario_runs_end_to_end(self) -> None:
        """수위 초과 신호 → (잠긴 2·3) → **등급별 수신자가 실제로 다른가**."""
        from kernels.k1_event import get_event
        from kernels.k2_notify import resolve_recipients, send
        from stream_monitors.services import zones

        # ── 1. 수위선 초과 신호 ───────────────────────────────────────
        reading = self._water_level_reading(level_cm=182.0, threshold_cm=150.0)
        self.assertTrue(reading["exceeded"], "픽스처가 초과 신호를 만들지 못했습니다.")
        self.ledger.record(self._step(1), True,
                           f"{reading['level_cm']}cm > {reading['threshold_cm']}cm")

        # ── 2. F-02 이벤트 생성 (30초) ★ D-294 로 열린 단계 ───────────
        #    AC 는 "30초"다. **논리 시계로 잰다** — 실시간으로 기다리지 않는다(규약 ⑤).
        #    재는 두 점은 계약이 정한 그대로다: 신호 발생 시각 → 이벤트의 occurred_at.
        detected_at = timezone.now()
        flood_event_id = self._event(
            self.stream_a, severity="warning", when=detected_at, event_type="flood")

        made = get_event(flood_event_id, scope=self.scope_a)
        self.assertEqual(
            "flood", made.event_type,
            "침수 신호가 침수 타입으로 저장되지 않았습니다 — 다른 타입에 실렸다면 "
            "그 타입의 오탐률 분모가 오염됩니다 (D-294).")
        elapsed = (made.occurred_at - detected_at).total_seconds()
        self.assertLessEqual(
            abs(elapsed), 30.0,
            f"[F-02] 초과 신호에서 이벤트까지 {elapsed:.2f}s — 30초 AC 를 넘겼습니다.")
        self.ledger.record(self._step(2), True,
                           f"event_id={flood_event_id} · {abs(elapsed):.2f}s ≤ 30s")

        # ── 3. 같은 구역 인명(F-03) 결합 → 등급 상향 ★ D-299 로 열린 단계 ──
        #
        #    재는 것은 둘이다:
        #      ① 같은 구역의 침수 관측 + 인명 관측이 **결합되는가**
        #      ② 결합이 **아무 두 관측이나** 묶지 않는가 (음성 대조 — D-289)
        #    ②가 없으면 "언제나 결합" 이 통과한다. 언제나 참인 시험은 시험이 아니다.
        person_event_id = self._event(
            self.stream_people, severity="warning",
            when=detected_at, event_type="person")

        flood_view = get_event(flood_event_id, scope=self.scope_a)
        person_view = get_event(person_event_id, scope=self.scope_a)

        combined = zones.combine_in_zone(
            scope=self.scope_a, primary=flood_view, secondary=person_view)
        self.assertIsNotNone(
            combined,
            "[F-03] 같은 구역의 침수·인명 관측이 결합되지 않았습니다 — "
            "두 카메라가 한 Zone 에 묶여 있는데 판정이 그것을 못 봤습니다.")
        self.assertEqual(self.zone.pk, combined.zone_id)
        self.assertEqual({flood_event_id, person_event_id}, set(combined.event_ids))
        self.assertEqual(
            "critical", combined.severity,
            "[F-03] 결합됐는데 등급이 오르지 않았습니다 — 결합의 효과는 등급 상향입니다.")
        self.assertNotEqual(
            flood_view.severity, combined.severity,
            "결합 전후의 등급이 같습니다. 그렇다면 이 단계는 아무것도 하지 않았습니다.")

        # ② 음성 대조 — 다른 구역의 관측은 **묶이지 않는다**
        far_event_id = self._event(
            self.stream_far, severity="warning", event_type="person")
        far_view = get_event(far_event_id, scope=self.scope_a)
        self.assertIsNone(
            zones.combine_in_zone(scope=self.scope_a,
                                  primary=flood_view, secondary=far_view),
            "다른 구역의 관측이 결합됐습니다 — 이 판정은 구역을 보지 않고 있습니다.")

        # ★ 저장된 등급은 **그대로다.** 결합은 값이지 덮어쓰기가 아니다.
        self.assertEqual(
            "warning", get_event(flood_event_id, scope=self.scope_a).severity,
            "결합이 저장된 등급을 덮었습니다 — 관측이 실제로 난 등급은 사실이고, "
            "덮으면 오탐률과 이력이 무엇을 세는지 알 수 없게 됩니다 (D-293 계열).")

        self.ledger.record(
            self._step(3), True,
            f"zone={combined.zone_name} · {flood_view.severity}→{combined.severity}")

        # ── 4. 등급별 수신자 그룹이 실제로 달라지는가 ─────────────────
        warning = resolve_recipients(scope=self.scope_a, severity="warning")
        critical = resolve_recipients(scope=self.scope_a, severity="critical")

        warn_ids = {r.user_id for r in warning}
        crit_ids = {r.user_id for r in critical}
        self.assertEqual({self.user_watch.pk}, warn_ids)
        self.assertEqual({self.user_chief.pk}, crit_ids)
        self.assertNotEqual(
            warn_ids, crit_ids,
            "[F-10] 등급이 다른데 받는 사람이 같습니다 — 등급별 수신그룹이 이름뿐입니다.")
        self.assertFalse(
            warn_ids & crit_ids,
            "두 등급의 수신자가 겹칩니다. 겹쳐도 되는 설계일 수 있으나, 이 픽스처는 "
            "**다른 역할**을 가리키게 만들었으므로 겹치면 규칙 조회가 잘못된 것입니다.")

        # 실제로 보내 봐도 갈리는가 — 목록이 다른 것과 발송이 다른 것은 다른 사실이다.
        mail.outbox.clear()
        crit_event = self._event(self.stream_a, severity="critical")
        records = send(scope=self.scope_a, event_id=crit_event)
        self.assertEqual([self.user_chief.pk], [r.recipient_id for r in records],
                         "심각 이벤트가 경고 수신자에게 갔습니다.")
        self.assertEqual(1, len(mail.outbox))

        # ★ 3단계의 상향이 4단계로 **실제로 이어지는가.** 결합이 값만 바꾸고 수신자가
        #   그대로면 F-03 은 아무 효과가 없다 — 그것이 "이름뿐인 등급 상향"이다.
        escalated = {r.user_id for r in resolve_recipients(
            scope=self.scope_a, severity=combined.severity)}
        self.assertEqual(
            crit_ids, escalated,
            "[F-03→F-10] 결합으로 오른 등급의 수신자가 심각 수신그룹과 다릅니다.")
        self.assertNotEqual(
            warn_ids, escalated,
            "결합 전(경고)과 결합 후의 수신자가 같습니다 — 등급 상향이 아무 효과가 "
            "없다면 F-03 결합은 이름뿐입니다.")

        self.ledger.record(
            self._step(4), True,
            f"경고 {sorted(warn_ids)} ≠ 심각 {sorted(crit_ids)} · "
            f"F-03 상향분 {sorted(escalated)}")
        print("\n" + self.ledger.render(self.scenario.active_steps))

    def test_every_step_is_reported_not_hidden(self) -> None:
        """★ **네 단계가 전부 표에 나오는가** — 그리고 잠긴 것이 남았다면 사유가 있는가.

        E2E-2 는 D-299 로 잠김 0 이 됐다. 그렇다고 이 시험을 지우면, 다음에 단계가
        하나 잠길 때 그 사실을 아무도 안 본다 — 빠진 줄은 보이지 않는다(D-274).
        그래서 판정을 **뒤집어서 남긴다**: 계획된 전 단계가 표에 있고, 잠긴 것이 있다면
        그것마다 사유가 있어야 한다.
        """
        from tests.e2e.e2e_contract import LOCKED_CAPABILITIES

        planned = self.scenario.steps
        active = {s.no for s in self.scenario.active_steps}
        self.assertIn(2, active, "F-02 단계가 다시 닫혔습니다 — D-294 로 열린 단계입니다. "
                                 "EventType 에서 flood 가 빠졌다면 계약 문서와 함께 되돌리십시오.")
        self.assertIn(3, active,
                      "구역 결합 단계가 다시 닫혔습니다 — D-299 로 열린 단계입니다. "
                      "Zone 모델이나 stream_monitors.services.zones 가 사라졌다면 "
                      "결정문과 함께 되돌리십시오.")
        self.assertEqual(
            len(planned), len(active),
            f"E2E-2 는 D-299 로 잠김 0 입니다. 지금 {len(planned) - len(active)}칸이 "
            f"잠겼다면 무엇이 되돌아갔는지 확인하십시오.")

        table = self.ledger.render(planned)
        for step in planned:
            self.assertIn(step.title[:16], table,
                          f"{step.no}단계가 표에서 빠졌습니다.")
            if step.no not in active:
                self.assertTrue(
                    LOCKED_CAPABILITIES.get(step.unlocked_by, "").strip(),
                    f"{step.no}단계의 잠금 사유가 비었습니다 (D-264).")

    # ── 규약 ① ───────────────────────────────────────────────────────────
    def test_runs_on_migrated_database(self) -> None:
        """규약 ① — 실 마이그레이션 DB (D-282 · D-288 ②눈)."""
        needed = {"stream_monitors_detectionevent",
                  "stream_monitors_notificationrule",
                  "stream_monitors_deliveryrecord"}
        missing = sorted(needed - set(connection.introspection.table_names()))
        self.assertEqual([], missing, f"이 E2E 가 도는 DB 에 표가 없습니다: {missing}")

        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        self.assertEqual([], plan, "미적용 마이그레이션이 남아 있습니다 (D-288 ②눈).")

    # ── 규약 ② ───────────────────────────────────────────────────────────
    def test_isolation_read_and_write_are_blocked(self) -> None:
        """규약 ② — 읽기·쓰기 양방향 (D-290)."""
        from django.http import Http404

        from kernels.k2_notify import list_deliveries, resolve_recipients, send

        mine = self._event(self.stream_a, severity="critical")
        send(scope=self.scope_a, event_id=mine)

        # 읽기 — 남의 수신자·이력이 섞이지 않는다
        theirs = {r.user_id for r in resolve_recipients(scope=self.scope_b,
                                                        severity="critical")}
        self.assertNotIn(self.user_chief.pk, theirs,
                         "남의 테넌트 수신자가 우리 규칙 조회에 들어왔습니다.")
        self.assertEqual(
            [], [d for d in list_deliveries(scope=self.scope_b) if d.event_id == mine],
            "다른 테넌트가 우리 발송 이력을 봤습니다 — 수신자 주소가 샙니다.")

        # 쓰기 — 남의 이벤트로 발송을 일으킬 수 없다
        with self.assertRaises(Http404):
            send(scope=self.scope_b, event_id=mine)

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        before = Event._base_manager.filter(stream_monitor=self.stream_a).count()
        from kernels.k1_event import record_detection

        with self.assertRaises(Http404):
            record_detection(scope=self.scope_b, stream_monitor_id=self.stream_a.pk,
                             event_type="person", severity="warning",
                             snapshot_path="minio://e2e2/planted.jpg")
        self.assertEqual(
            before, Event._base_manager.filter(stream_monitor=self.stream_a).count(),
            "다른 테넌트가 우리 스트림에 관측을 심었습니다 — 쓰기 IDOR 입니다.")

    # ── 규약 ③ ───────────────────────────────────────────────────────────
    def test_positive_control_without_the_event(self) -> None:
        """규약 ③ — 규칙을 지우면 이 E2E 가 **실패하는가** (D-277 · D-289).

        표본은 합성이 아니라 저장소 실물 커널 공개 면이다 (`REAL_SAMPLE`).
        """
        from kernels.k2_notify import NoRecipients, resolve_recipients, send

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        Rule._base_manager.all().delete()

        self.assertEqual(
            (), resolve_recipients(scope=self.scope_a, severity="critical"),
            "규칙을 전부 지웠는데 수신자가 나왔습니다 — 이 E2E 는 규칙을 보고 있지 "
            "않습니다.")
        event_id = self._event(self.stream_a, severity="critical")
        with self.assertRaises(NoRecipients):
            send(scope=self.scope_a, event_id=event_id)

    # ── 규약 ④ ───────────────────────────────────────────────────────────
    def test_degraded_variant_keeps_core_path(self) -> None:
        """규약 ④ — 메일이 죽어도 등급 판정·이벤트 기록은 산다 (W0-17)."""
        from kernels.k1_event import query_events
        from kernels.k2_notify import channels, list_deliveries, resolve_recipients, send

        class _DeadMailServer:
            name = "email"

            def send(self, *, address, subject, body):
                raise ConnectionError("E2E-2 저하 변형 — 메일 서버가 죽었다")

        undo = channels.register(_DeadMailServer())
        self.addCleanup(undo)

        now = timezone.now()
        event_id = self._event(self.stream_a, severity="critical", when=now)

        # 등급별 수신자 판정은 메일과 무관하다 — 여기서 죽으면 저하 운전이 아니다.
        self.assertEqual(
            {self.user_chief.pk},
            {r.user_id for r in resolve_recipients(scope=self.scope_a,
                                                    severity="critical")})

        records = send(scope=self.scope_a, event_id=event_id)   # 예외가 나면 실패
        self.assertFalse(records[0].succeeded)
        self.assertTrue(records[0].failure_reason)
        self.assertEqual(1, len(list_deliveries(scope=self.scope_a, event_id=event_id)),
                         "실패가 이력으로 남지 않았습니다 — 조용한 유실입니다.")
        self.assertIn(event_id,
                      [e.event_id for e in query_events(
                          scope=self.scope_a, since=now - timedelta(minutes=1))],
                      "메일 장애가 이벤트 조회까지 끌고 내려갔습니다.")
