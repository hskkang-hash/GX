# -*- coding: utf-8 -*-
"""QA-12 알림 예산 시뮬레이션 — **[시험]이 건수를 낸다** (2026-09-04 · 차선 Q).

무엇을 재는가
-------------
    ① 저장 전에 **수가 나온다** — 지금 [시험]은 판정만 보여 준다 [실측 등재]
    ② 시간당 6건을 넘으면 **주황**. 빨강이 아니다 (ISA-101: 빨강은 critical 전용)
    ③ 상한 6은 **EEMUA 191 [인용]** — 우리가 지은 수가 아니고, 이름에 출처가 박혀 있다
    ④ 세는 것은 **5분 억제를 지난 뒤의 수**다 — 이벤트 수를 그대로 내면 실제보다 크다
    ⑤ **아무것도 저장하지 않는다** — 규칙도, 발송 이력도 (읽기 전용)
    ⑥ 남의 테넌트 이벤트를 세지 않는다 — 세면 그 수는 이 고객의 예산이 아니다
    ⑦ 수신자 0명일 때 예산 0은 **좋은 상태가 아니다** — 그 사실이 단서에 남는다

★ **시험을 고쳐 초록을 만들지 않는다** (D-327). 아래는 상한 6을 상수에서 인용한다 —
  여기에 6을 적으면 인용이 아니라 사본이 되고, 사본은 원본과 갈린다.
"""
from __future__ import annotations

from datetime import timedelta

from django.apps import apps
from django.test import TestCase
from django.utils import timezone

from tests.test_k2_notify_kernel import K2Fixture


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — DB 없이
# ═══════════════════════════════════════════════════════════════════════════
class BudgetJudgeTest(TestCase):
    """`_judge` 와 `_fold_by_suppression`. 상한 언저리를 DB 없이 잰다."""

    def setUp(self) -> None:
        from kernels.k2_notify import alarm_budget as ab

        self.ab = ab
        self.limit = ab.EEMUA_191_ALARMS_PER_OPERATOR_HOUR

    def test_over_the_cited_limit_is_orange_not_red(self) -> None:
        """★ 주황이지 빨강이 아니다. 예산 초과는 **저장을 막지 않는다** — 보여 줄 뿐이다."""
        level, headline = self.ab._judge(self.limit + 0.5)
        self.assertEqual(self.ab.BUDGET_ORANGE, level)
        self.assertNotIn("red", level)
        self.assertIn("EEMUA 191", headline, "상한의 출처가 문장에서 사라지면 "
                                             "다음 사람은 그것을 우리 수로 읽는다")

    def test_at_the_limit_is_not_over(self) -> None:
        """상한 **그 값**은 초과가 아니다 — 경계에서 색이 뒤집히면 아무도 안 믿는다."""
        self.assertEqual(self.ab.BUDGET_OK, self.ab._judge(self.limit)[0])
        self.assertEqual(self.ab.BUDGET_ORANGE, self.ab._judge(self.limit + 0.01)[0])

    def test_headline_always_carries_the_number(self) -> None:
        """★ 이 절이 존재하는 이유 — **건수를 말하지 않는 판정은 지금 것과 같다.**"""
        for rate in (0.0, 1.0, self.limit, 100.0):
            _level, headline = self.ab._judge(rate)
            self.assertIn("시간당", headline)
            self.assertIn(f"{rate:.1f}", headline)

    def test_suppression_folds_repeats_of_the_same_camera_and_type(self) -> None:
        """★ 5분 억제를 흉내 내지 않고 **같은 상수를 인용해** 접는다 (D-212)."""
        from kernels.k2_notify.schemas import SUPPRESS_WINDOW

        base = timezone.now()
        rows = [(("cam1", "fire"), base + timedelta(seconds=60 * i)) for i in range(10)]
        kept = self.ab._fold_by_suppression(rows)
        self.assertEqual(2, kept,
                         f"10분에 1분 간격 10건은 {SUPPRESS_WINDOW} 억제를 지나면 2건이다")

    def test_different_cameras_are_not_folded_into_each_other(self) -> None:
        """억제는 `(카메라, 유형)` 별이다. 뭉치면 **다른 카메라의 경보가 사라진다.**"""
        base = timezone.now()
        rows = [(("cam1", "fire"), base), (("cam2", "fire"), base),
                (("cam1", "flood"), base)]
        self.assertEqual(3, self.ab._fold_by_suppression(rows))


# ═══════════════════════════════════════════════════════════════════════════
# 배선 — 실제 이벤트로 되돌려 돌린다
# ═══════════════════════════════════════════════════════════════════════════
class BudgetSimulationTest(K2Fixture):
    """`simulate_alarm_budget`. **아직 없는 규칙**을 최근 7일로 잰다."""

    def _flood(self, stream, count: int, *, severity="critical", spacing_minutes=30):
        """`count` 건을 서로 억제되지 않게 흩어 심는다."""
        from kernels.k1_event import record_detection

        now = timezone.now()
        for i in range(count):
            record_detection(
                scope=self.scope_pipe, stream_monitor_id=stream.pk,
                event_type="fire", severity=severity,
                occurred_at=now - timedelta(minutes=spacing_minutes * (i + 1)))

    def test_it_reports_a_count_not_only_a_verdict(self) -> None:
        """★ 이 절의 요점 — 화면이 그릴 **수**가 실제로 나오는가."""
        from kernels.k2_notify import simulate_alarm_budget

        self._flood(self.stream_a, 12)
        view = simulate_alarm_budget(scope=self.scope_a, severity="critical")
        self.assertEqual(12, view.matched_events)
        self.assertEqual(12, view.after_suppression, "30분 간격은 5분 억제에 안 걸린다")
        self.assertAlmostEqual(12 / (7 * 24), view.per_operator_hour, places=6)
        self.assertGreater(view.window_hours, 0)

    def test_over_budget_rule_is_flagged_orange_with_the_number(self) -> None:
        """★ 7일 × 24시간 × 6건 = 1008건을 넘으면 주황. 그리고 **수가 문장에 있다.**"""
        from kernels.k2_notify import (EEMUA_191_ALARMS_PER_OPERATOR_HOUR,
                                       simulate_alarm_budget)

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        now = timezone.now()
        # 억제에 안 걸리게 **다른 카메라**로 흩는다 — 한 카메라에 몰면 5분 억제가
        # 접어 버리고, 그러면 이 시험은 규칙이 아니라 억제를 재게 된다.
        streams = [self.stream_a]
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        for i in range(9):
            extra = StreamMonitor.objects.create(
                name=f"q-budget-{i}", code=f"q-budget-{i}",
                ip_source="rtsp://test.invalid/x")
            self._own(extra, self.group_a)
            streams.append(extra)

        rows = []
        need = int(EEMUA_191_ALARMS_PER_OPERATOR_HOUR * 7 * 24) + 50
        for i in range(need):
            rows.append(Event(
                stream_monitor=streams[i % len(streams)], event_type="fire",
                severity="critical", occurred_at=now - timedelta(minutes=(i % 9000) + 1),
                snapshot_path=""))
        Event._base_manager.bulk_create(rows)
        for row in Event._base_manager.filter(stream_monitor__in=streams):
            self._own(row, self.group_a)

        view = simulate_alarm_budget(scope=self.scope_a, severity="critical")
        self.assertTrue(view.over_budget,
                        f"시간당 {view.per_operator_hour:.2f}건인데 경고가 없다")
        self.assertEqual("orange", view.level)
        self.assertIn("EEMUA 191", view.headline)
        self.assertIn(f"{view.per_operator_hour:.1f}", view.headline,
                      "★ 건수가 문장에 없으면 지금 [시험]과 같다 — 판정만 있고 수가 없다")

    def test_a_quiet_rule_is_not_flagged(self) -> None:
        """★ 부작위 — 조용한 규칙에 주황을 칠하면 그 색이 곧 무뎌진다."""
        from kernels.k2_notify import simulate_alarm_budget

        self._flood(self.stream_a, 3)
        view = simulate_alarm_budget(scope=self.scope_a, severity="critical")
        self.assertFalse(view.over_budget, view.headline)
        self.assertEqual("ok", view.level)

    def test_simulation_writes_nothing(self) -> None:
        """★ 부작위 — **규칙도 발송 이력도 안 만든다.** 저장 전에 재는 것이 목적이다."""
        from kernels.k2_notify import simulate_alarm_budget

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        self._flood(self.stream_a, 4)
        before = (Rule._base_manager.count(), Delivery._base_manager.count())

        simulate_alarm_budget(scope=self.scope_a, severity="critical")
        simulate_alarm_budget(scope=self.scope_a, severity="warning")

        self.assertEqual(
            before, (Rule._base_manager.count(), Delivery._base_manager.count()),
            "[시험]이 무언가를 남겼다 — 재는 행위가 재는 대상을 바꾼다")

    def test_suppression_is_applied_so_the_number_is_not_inflated(self) -> None:
        """★ 이벤트 수와 알림 수는 다르다. 부풀린 수는 두 번 해롭다 —
        한 번 놀라고, 다음번에 안 믿는다."""
        from kernels.k2_notify import simulate_alarm_budget

        self._flood(self.stream_a, 8, spacing_minutes=1)
        view = simulate_alarm_budget(scope=self.scope_a, severity="critical")
        self.assertEqual(8, view.matched_events)
        self.assertLess(view.after_suppression, view.matched_events)
        self.assertIn("5분 억제", view.caveat)

    def test_it_does_not_count_another_tenants_events(self) -> None:
        """★ 격리 — 남의 이벤트를 세면 그 수는 **이 고객의 예산이 아니다.**"""
        from kernels.k2_notify import simulate_alarm_budget

        self._flood(self.stream_b, 20)
        view = simulate_alarm_budget(scope=self.scope_a, severity="critical")
        self.assertEqual(0, view.matched_events,
                         "남의 테넌트 이벤트가 내 예산에 실렸다")

    def test_zero_recipients_is_reported_as_a_problem_not_as_a_good_number(self) -> None:
        """★ 예산 0이 **아무에게도 안 가서**인 경우를 조용히 초록으로 내지 않는다 (D-290)."""
        from kernels.k2_notify import simulate_alarm_budget

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        Rule._base_manager.all().delete()
        view = simulate_alarm_budget(scope=self.scope_a, severity="critical")
        self.assertEqual(0, view.recipients)
        self.assertIn("0명", view.caveat)

    def test_unknown_zone_label_widens_instead_of_silently_returning_zero(self) -> None:
        """★ 없는 구역 라벨로 좁혀 0건을 내면 「그 구역엔 아무 일도 없었다」로 읽힌다."""
        from kernels.k2_notify import simulate_alarm_budget

        self._flood(self.stream_a, 5)
        view = simulate_alarm_budget(scope=self.scope_a, severity="critical",
                                     zone="q-no-such-zone")
        self.assertEqual(5, view.matched_events)
        self.assertIn("좁히지 않고", view.caveat)

    def test_a_person_cannot_point_group_at_another_tenant(self) -> None:
        """★★ 격리 — `group=` 으로 **남의 이벤트 수**를 예산으로 삼을 수 없다."""
        from kernels.k2_notify import simulate_alarm_budget
        from kernels.k2_notify.exceptions import InvalidNotifyInput

        self._flood(self.stream_b, 20)
        with self.assertRaises(InvalidNotifyInput):
            simulate_alarm_budget(scope=self.scope_a, severity="critical",
                                  group=self.group_b)

    def test_a_person_may_pass_their_own_group(self) -> None:
        """★ 양성 대조 (D-282 ④)."""
        from kernels.k2_notify import simulate_alarm_budget

        self._flood(self.stream_a, 4)
        view = simulate_alarm_budget(scope=self.scope_a, severity="critical",
                                     group=self.group_a)
        self.assertEqual(4, view.matched_events)

    def test_bad_input_is_refused_instead_of_returning_a_made_up_number(self) -> None:
        from kernels.k2_notify import simulate_alarm_budget
        from kernels.k2_notify.exceptions import InvalidNotifyInput

        for kwargs in (dict(severity="urgent"), dict(severity="critical", days=0)):
            with self.assertRaises(InvalidNotifyInput, msg=str(kwargs)):
                simulate_alarm_budget(scope=self.scope_a, **kwargs)

    def test_limit_is_a_citation_not_our_invention(self) -> None:
        """★ 이름에 출처가 박혀 있다. `MAX_ALARMS` 였다면 불편할 때 8로 고쳤을 것이다."""
        from kernels.k2_notify import (EEMUA_191_ALARMS_PER_OPERATOR_HOUR,
                                       simulate_alarm_budget)

        self.assertEqual(6.0, EEMUA_191_ALARMS_PER_OPERATOR_HOUR)
        view = simulate_alarm_budget(scope=self.scope_a, severity="critical")
        self.assertIn("EEMUA 191", view.citation)
        self.assertEqual(EEMUA_191_ALARMS_PER_OPERATOR_HOUR, view.limit,
                         "화면이 자기 숫자를 들면 그 숫자가 상수와 갈린다 (D-212)")
