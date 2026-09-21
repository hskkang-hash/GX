# -*- coding: utf-8 -*-
"""K6 피드백·계측 커널 — **이중 AC 시험** (DA-04 §2 K6).

    [F-14 계약] 월간 오탐률 리포트 생성
    [U1 상품]  오탐률 추이 **월 하락**
    [U4 상품]  요금 = 시스템 집계

★ 이 파일에서 가장 중요한 것은 **분모다.**
  비율 하나는 3/10 인지 300/1000 인지 말해 주지 않고, 그 둘은 회의에서 다른 문장이다.
  그리고 분모를 잘못 잡으면 **판정을 미루기만 해도 오탐률이 좋아진다** — 지표가
  지표를 죽이는 모양이고, U1 의 "월 하락"이 그렇게 달성되면 그 숫자는 거짓말이다.

시험 순서는 착시 5형(D-282)을 그대로 따라간다:
  ② 시나리오 — 분모·분자·미판정을 각각 다른 갈래로 지나간다
  ③ 모수와 술어 — "무엇을 몇 개 중에서 셌나"를 시험이 스스로 말한다
  ④ 탐지기 — 양성 대조. 이벤트를 심지 않으면 이 시험이 실패하는가
  ⑤ 환경 — 표가 DB 에 실재하는가 (`--nomigrations` 가 가린 것 · D-288 ②눈)
"""
from __future__ import annotations

import contextlib
from datetime import timedelta

from django.apps import apps
from django.test import TestCase
from django.utils import timezone


class K6Fixture(TestCase):
    """테넌트 A/B 와 각자의 스트림. `test_k1_event_kernel.K1Fixture` 규약을 따른다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        UserGroup = apps.get_model("user", "UserGroup")

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="k6-tenant-A")
        cls.group_b = UserGroup.objects.create(name="k6-tenant-B")
        UserGroup.objects.filter(pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.user_a = cls._make_user("k6_user_a", cls.group_a)
        cls.user_b = cls._make_user("k6_user_b", cls.group_b)
        cls.stream_a = cls._make_stream("k6-stream-A", cls.group_a)
        cls.stream_b = cls._make_stream("k6-stream-B", cls.group_b)

        from common.tenant_scope import TenantScope

        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)
        cls.scope_pipe = TenantScope.system(
            reason="K6 시험 픽스처 — 검출 파이프라인에는 요청자가 없다 (D-281)")

    @classmethod
    def _make_user(cls, username: str, group):
        CoreUser = apps.get_model("user", "CoreUser")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid",
        )
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_model = link_field.related_model
        link_model.objects.create(**{link_field.remote_field.name: user, "group": group})
        return user

    @classmethod
    def _make_stream(cls, name: str, group):
        from kernels.k1_event.services import _owner_field

        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        sm = StreamMonitor.objects.create(name=name, code=name,
                                          ip_source="rtsp://test.invalid/x")
        if _owner_field(StreamMonitor) == "groups":
            sm.groups.set([group])
        else:
            sm.group = group
            sm.save(update_fields=["group"])
        return sm

    # ── 이벤트를 심는다 ──────────────────────────────────────────────────
    def _event(self, stream, *, when=None, event_type="fire", severity="critical"):
        """이벤트 1건. **10초 창을 피해** 시각을 벌린다 — 접히면 셈이 달라진다."""
        from kernels.k1_event import record_detection

        self._nth = getattr(self, "_nth", 0) + 1
        when = when or (timezone.now() - timedelta(seconds=60 * self._nth))
        result = record_detection(
            scope=self.scope_pipe, stream_monitor_id=stream.pk,
            event_type=event_type, severity=severity, occurred_at=when,
            snapshot_path=f"minio://k6/{self._nth}.jpg",
        )
        return result.event_id

    def _judge(self, event_id, verdict, *, scope=None):
        from kernels.k6_feedback import record_feedback

        return record_feedback(event_id, verdict=verdict, reason="k6-test",
                               scope=scope or self.scope_a)


# ═══════════════════════════════════════════════════════════════════════════
# [F-14 계약 AC] × [U1 상품 AC] — **분모가 요구사항이다**
# ═══════════════════════════════════════════════════════════════════════════
class FalsePositiveDenominatorTest(K6Fixture):
    """★ 이 파일에서 가장 중요한 시험.

    F-14 만 보면 "오탐률을 내라"가 되고, 그렇게 내면 분모를 아무거나 쓸 수 있다.
    U1 의 "월 하락"이 붙는 순간 분모의 선택이 **곧 지표의 정직성**이 된다.
    """

    def test_unreviewed_events_are_not_in_the_denominator(self) -> None:
        """미판정은 분모가 아니다 — **판정을 미루기만 해도 좋아지는 지표**를 만들지 않는다."""
        from kernels.k6_feedback import false_positive_rate

        judged = [self._event(self.stream_a) for _ in range(4)]
        unjudged = [self._event(self.stream_a) for _ in range(6)]
        self._judge(judged[0], "rejected")
        self._judge(judged[1], "rejected")
        self._judge(judged[2], "confirmed")
        self._judge(judged[3], "confirmed")

        out = false_positive_rate(scope=self.scope_a,
                                  since=timezone.now() - timedelta(days=1))
        self.assertEqual(2, out.total.rejected, "분자(기각)가 실측과 다릅니다.")
        self.assertEqual(4, out.total.reviewed,
                         "분모에 미판정이 섞였습니다 — 판정을 미루면 오탐률이 떨어집니다.")
        self.assertEqual(len(unjudged), out.total.unreviewed,
                         "미판정 수를 보고하지 않으면 표본이 얇다는 사실이 숨습니다 (D-271 ③).")
        self.assertAlmostEqual(0.5, out.total.rate)

    def test_zero_denominator_is_none_not_zero(self) -> None:
        """★ 분모 0 은 `None` 이다. **0.0 이 아니다** (D-290).

        0.0 으로 내면 "아직 아무도 판정하지 않았다"가 "오탐이 하나도 없었다"로 읽힌다.
        그 둘은 정반대의 사실이고, 후자로 읽힌 순간 U1 의 월 하락이 거짓으로 달성된다.
        """
        from kernels.k6_feedback import false_positive_rate

        for _ in range(3):
            self._event(self.stream_a)   # 심되 판정하지 않는다

        out = false_positive_rate(scope=self.scope_a,
                                  since=timezone.now() - timedelta(days=1))
        self.assertEqual(0, out.total.reviewed)
        self.assertIsNone(out.total.rate,
                          "분모 0 인데 비율이 나왔습니다 — 없는 것과 0 을 같은 값으로 "
                          "표현하지 않습니다 (D-290).")
        self.assertFalse(out.is_measurable,
                         "쓸 수 없는 수치를 쓸 수 있다고 보고했습니다.")

    def test_rejected_event_is_counted_not_deleted(self) -> None:
        """기각은 삭제가 아니다 — 지우면 분자가 함께 사라진다 (K1 과 같은 계약)."""
        from kernels.k6_feedback import false_positive_rate

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        event_id = self._event(self.stream_a)
        self._judge(event_id, "rejected")

        self.assertTrue(Event._base_manager.filter(pk=event_id).exists(),
                        "기각된 이벤트 행이 사라졌습니다 — 분자를 셀 수 없게 됩니다.")
        out = false_positive_rate(scope=self.scope_a,
                                  since=timezone.now() - timedelta(days=1))
        self.assertEqual(1, out.total.rejected)


class MonthlyReportTest(K6Fixture):
    """[F-14] 월간 리포트와 [U1] 추이가 **같은 집계 경로**에서 나오는가."""

    def test_month_buckets_come_from_the_same_query_as_the_total(self) -> None:
        """★ DA-04: *"집계 경로를 하나로 유지하는 것 자체가 요구사항이다."*

        칸의 합이 전체와 다르면 두 벌로 센 것이다. 갈린 숫자는 고객 앞에서 못 쓴다.
        """
        from kernels.k6_feedback import false_positive_rate

        now = timezone.now().replace(day=15, hour=12, minute=0, second=0, microsecond=0)
        last_month = (now.replace(day=1) - timedelta(days=5)).replace(day=10)

        a = self._event(self.stream_a, when=last_month)
        b = self._event(self.stream_a, when=last_month + timedelta(hours=1))
        c = self._event(self.stream_a, when=now - timedelta(hours=2))
        self._judge(a, "rejected")
        self._judge(b, "confirmed")
        self._judge(c, "rejected")

        out = false_positive_rate(
            scope=self.scope_a, bucket="month",
            since=last_month - timedelta(days=1), until=now + timedelta(hours=1))

        self.assertGreaterEqual(len(out.buckets), 2, "월별 칸이 나오지 않았습니다.")
        self.assertEqual(out.total.reviewed, sum(w.reviewed for w in out.buckets),
                         "칸의 분모 합이 전체와 다릅니다 — 두 벌로 셌습니다.")
        self.assertEqual(out.total.rejected, sum(w.rejected for w in out.buckets),
                         "칸의 분자 합이 전체와 다릅니다 — 두 벌로 셌습니다.")

    def test_unknown_bucket_is_refused(self) -> None:
        """달력을 두 벌로 만들지 않는다 — 같은 기간이 두 보고에서 다른 칸이 되면 안 된다."""
        from kernels.k6_feedback import InvalidMetricInput, false_positive_rate

        with self.assertRaises(InvalidMetricInput):
            false_positive_rate(scope=self.scope_a, bucket="week")


class ClosedEventKeepsItsVerdictTest(K6Fixture):
    """★ **P-K6-1 을 닫는다 — 종료가 판정을 지우지 않는다** (D-293).

    이 시험의 이전 판은 정반대를 단언했다: 종료하면 분모가 준다는 **그때의 사실**을
    적고, "전제가 바뀌면 이 시험과 P-K6-1 을 같은 커밋에서 닫으라"는 문장을 남겼다.
    지금이 그 커밋이다.

    무엇이 바뀌었나 — 칸 하나
    -------------------------
    `status` 는 **판정**(confirmed/rejected)과 **수명**(new/closed)을 한 값에 실었고,
    종료가 마지막에 오므로 판정을 덮었다. 그래서 오래된 이벤트일수록 분모에서
    빠졌고, U1 의 "오탐률 월 하락"이 **판정을 종료하기만 해도** 달성될 수 있었다.

    D-293 이 그것을 금지했다. 판정은 덮이지 않는 칸(`verdict`)에 남고, 오탐률은
    거기서만 센다. 종료는 여전히 `status` 를 옮기고 K4 보고서를 트리거한다 —
    **F-11 의 트리거 계약은 그대로다.**
    """

    def test_closing_a_judged_event_keeps_it_in_the_denominator(self) -> None:
        from kernels.k1_event import close_event, get_event
        from kernels.k6_feedback import false_positive_rate

        rejected = self._event(self.stream_a)
        confirmed = self._event(self.stream_a)
        self._judge(rejected, "rejected")
        self._judge(confirmed, "confirmed")

        since = timezone.now() - timedelta(days=1)
        before = false_positive_rate(scope=self.scope_a, since=since)
        self.assertEqual(2, before.total.reviewed)
        self.assertEqual(1, before.total.rejected)

        close_event(rejected, scope=self.scope_a)
        after = false_positive_rate(scope=self.scope_a, since=since)

        self.assertEqual(
            before.total.reviewed, after.total.reviewed,
            "종료가 분모를 깎았습니다 — 지표가 스스로 좋아지는 구조가 돌아왔습니다 (D-293).")
        self.assertEqual(
            before.total.rejected, after.total.rejected,
            "종료가 분자를 깎았습니다 — 기각이 종료되면 오탐이 없던 일이 됩니다 (D-293).")
        self.assertEqual(
            before.total.rate, after.total.rate,
            "같은 코호트인데 종료 전후로 오탐률이 달라졌습니다.")

    def test_the_lifecycle_still_moves(self) -> None:
        """종료가 **무의미해진 것이 아니다** — status 는 옮겨간다.

        판정을 지키려다 종료 자체를 없애면 K4(F-11 보고서)의 트리거가 사라진다.
        두 칸이 각자 자기 일을 하는지 함께 본다.
        """
        from kernels.k1_event import close_event, get_event

        event_id = self._event(self.stream_a)
        self._judge(event_id, "rejected")
        closed = close_event(event_id, scope=self.scope_a)

        self.assertEqual("closed", closed.status, "종료가 수명주기를 옮기지 않았습니다.")
        self.assertEqual("rejected", closed.verdict, "종료가 판정을 지웠습니다 (D-293).")
        self.assertEqual("rejected", get_event(event_id, scope=self.scope_a).verdict,
                         "다시 읽으면 판정이 사라집니다 — 저장되지 않았습니다.")

    def test_closing_without_a_verdict_is_counted_and_named(self) -> None:
        """판정 없이 닫힌 것은 **미판정**이지 손실이 아니다 — 그러나 보고한다.

        이 수가 크면 지표가 나쁜 것이 아니라 **판정 절차가 종료에 밀리고 있다**는 뜻이다.
        숨기면 얇은 표본 위의 비율이 두꺼운 표본처럼 읽힌다 (D-271 ③).
        """
        from kernels.k1_event import close_event
        from kernels.k6_feedback import false_positive_rate

        never_judged = self._event(self.stream_a)
        close_event(never_judged, scope=self.scope_a)

        out = false_positive_rate(scope=self.scope_a,
                                  since=timezone.now() - timedelta(days=1))
        self.assertEqual(0, out.total.reviewed, "판정한 적 없는 것이 분모에 들었습니다.")
        self.assertEqual(1, out.total.unreviewed,
                         "판정 없이 닫힌 이벤트가 미판정 수에서 빠졌습니다 — 모수가 조용히 줄었습니다.")
        self.assertEqual(1, out.total.closed_without_verdict,
                         "판정 없이 닫힌 수를 보고하지 않으면 표본이 왜 얇은지 아무도 모릅니다.")


class KernelTenantScopeTest(K6Fixture):
    """계측도 격리된다 — **전 테넌트 집계는 격리의 부재다** (D-281)."""

    def test_positive_control_own_events_are_counted(self) -> None:
        """★ 양성 대조 — 자기 것은 세어지는가 (D-277).

        "남의 것이 안 보인다"는 격리일 수도 있고 **집계기가 눈이 먼 것**일 수도 있다.
        """
        from kernels.k6_feedback import false_positive_rate

        self._judge(self._event(self.stream_a), "rejected")
        out = false_positive_rate(scope=self.scope_a,
                                  since=timezone.now() - timedelta(days=1))
        self.assertEqual(1, out.total.reviewed,
                         "자기 테넌트 이벤트를 세지 못했습니다 — 집계기가 눈이 멀었습니다.")

    def test_other_tenant_events_are_not_in_my_rate(self) -> None:
        from kernels.k6_feedback import false_positive_rate

        self._judge(self._event(self.stream_b), "rejected", scope=self.scope_b)
        out = false_positive_rate(scope=self.scope_a,
                                  since=timezone.now() - timedelta(days=1))
        self.assertEqual(0, out.total.reviewed,
                         "남의 테넌트 판정이 내 오탐률에 섞였습니다.")

    def test_system_scope_cannot_measure(self) -> None:
        """시스템 스코프로 오탐률을 물으면 그것은 **전 테넌트 집계**다."""
        from common.tenant_scope import SystemScopeCannotRead
        from kernels.k6_feedback import false_positive_rate

        with self.assertRaises(SystemScopeCannotRead):
            false_positive_rate(scope=self.scope_pipe)

    def test_record_feedback_of_other_tenant_is_404(self) -> None:
        """쓰기 위임도 K1 의 문지기를 그대로 탄다 — K6 이 우회로가 되지 않는다."""
        from django.http import Http404

        victim = self._event(self.stream_b)
        with self.assertRaises(Http404):
            self._judge(victim, "rejected", scope=self.scope_a)


class SingleWritePathTest(K6Fixture):
    """★ 쓰기 경로가 **하나**인가 (DA-04 K6 "집계 경로를 하나로")."""

    def test_record_feedback_delegates_to_k1_review_event(self) -> None:
        """K6 이 `status` 를 직접 쓰지 않는다 — 쓰는 곳이 둘이면 이미 갈린 것이다.

        위임을 **관찰로** 확인한다: K1 을 막으면 K6 도 못 쓴다. 소스를 읽어
        "부르는 것처럼 보인다"고 판정하지 않는다 (D-249 부착률 착시와 같은 계열).
        """
        from unittest import mock

        event_id = self._event(self.stream_a)
        with mock.patch("kernels.k1_event.services.review_event",
                        side_effect=RuntimeError("K1 이 막혔다")) as k1:
            with mock.patch("kernels.k1_event.review_event", k1):
                with self.assertRaises(RuntimeError):
                    self._judge(event_id, "rejected")

    def test_kernel_has_no_model_of_its_own(self) -> None:
        """★ K6 에 `models.py` 가 없는 것은 **설계다.**

        DA-04 K6: *"별도 집계 테이블을 만들지 않는다 — 두 벌로 세면 숫자가 갈리고,
        갈린 숫자는 고객 앞에서 못 쓴다."* 누가 편의로 표를 하나 만들면 여기서 멈춘다.
        """
        from pathlib import Path

        import kernels.k6_feedback as pkg

        offenders = [p.name for p in Path(pkg.__file__).parent.glob("models.py")]
        self.assertEqual(
            [], offenders,
            "K6 에 models.py 가 생겼습니다. 오탐률의 분모·분자는 DetectionEvent.status "
            "하나에서 나옵니다 — 별도 집계 표를 만들면 숫자가 갈립니다 (DA-04 §2 K6).")


class HonestAbsenceTest(K6Fixture):
    """구현이 없는 공개 면은 **성공을 반환하지 않는다** (D-284).

    ★ 2026-09-21 (P-178 U56 ②) — `usage_snapshot` 은 **더 이상 여기 없다.** 구현됐다.
      그 자리의 정직함(0을 안 돌려준다 · 남의 테넌트를 안 센다 · 지운 행을 안 센다)은
      아래 `UsageSnapshotLedgersTest` 가 **값으로** 묻는다. 「미구현이라 안 센다」를
      「구현했으니 됐다」로 지우면 그 자리에 남는 시험이 0개가 된다.
    """

    def test_kpi_series_raises_instead_of_returning_empty(self) -> None:
        from kernels.k6_feedback import NotImplementedYet, kpi_series

        with self.assertRaises(NotImplementedYet):
            kpi_series("event_to_alert_seconds", scope=self.scope_a)

    def test_absent_surface_still_demands_scope_first(self) -> None:
        """미구현이어도 스코프는 **지금** 요구한다 — 나중에 붙이는 문턱은 안 붙는다."""
        from kernels.k6_feedback import usage_snapshot

        with self.assertRaises(TypeError):
            usage_snapshot()  # type: ignore[call-arg]


class UsageSnapshotLedgersTest(K6Fixture):
    """★ P-178 U56 ② — **장부 셋**(카메라·계정·저장)을 K6 이 센다.

    `apps/dsm/metering.py` 가 `apps.get_model` 로 직접 세던 자리다. 커널로 옮긴 것만으로는
    아무것도 증명되지 않는다 — **옮긴 뒤에도 같은 세 규칙이 서 있는가**를 값으로 묻는다:
    ㉠ 제 테넌트만 · ㉡ 지운 행은 안 센다 · ㉢ 못 세면 0이 아니라 **던진다**.
    """

    def test_it_counts_only_its_own_tenant(self) -> None:
        """남의 카메라 대수가 내 청구서에 실리면 **개인정보 유출**이다(남의 사업 규모다)."""
        from kernels.k6_feedback import usage_snapshot

        a = usage_snapshot(scope=self.scope_a)
        b = usage_snapshot(scope=self.scope_b)
        self.assertEqual(1, a["cameras"], "A 의 카메라는 하나다 — B 의 것이 섞였습니다")
        self.assertEqual(1, b["cameras"], "B 의 카메라는 하나다 — A 의 것이 섞였습니다")
        self.assertEqual(1, a["users"], "A 의 계정은 하나다 — B 의 것이 섞였습니다")

    def test_it_does_not_count_a_deleted_camera(self) -> None:
        """고객이 지운 카메라에 돈을 받지 않는다.

        dj-core 의 `objects` 는 safedelete 매니저가 **아니라** 지운 행이 평범한 조회에
        그대로 보인다 — 그래서 이 시험이 잡는 것은 「빼먹은 필터 한 줄」이고,
        그 한 줄은 **청구서에서만** 티가 난다.
        """
        from django.utils import timezone as tz

        from kernels.k6_feedback import usage_snapshot

        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        before = usage_snapshot(scope=self.scope_a)["cameras"]
        StreamMonitor._base_manager.filter(pk=self.stream_a.pk).update(deleted=tz.now())
        try:
            after = usage_snapshot(scope=self.scope_a)["cameras"]
        finally:
            StreamMonitor._base_manager.filter(pk=self.stream_a.pk).update(deleted=None)
        self.assertEqual((1, 0), (before, after),
                         "소프트 삭제된 카메라가 청구 셈에 남아 있습니다 "
                         "(common/billing_marks.exclude_soft_deleted)")

    def test_a_scope_without_a_tenant_raises_instead_of_returning_zero(self) -> None:
        """★ **0 은 「안 썼다」로 읽힌다** (D-301). 소속 없는 요청자에게 0 을 주면
        그 달 청구서가 조용히 0원이 되고, 아무도 그것을 결함으로 못 읽는다.
        아무 테넌트나 고르는 것은 더 나쁘다 — 남의 수가 청구서에 오른다(W0-12).
        """
        from common.tenant_scope import TenantScope
        from kernels.k6_feedback import K6Error, usage_snapshot

        CoreUser = apps.get_model("user", "CoreUser")
        orphan = CoreUser.objects.create_user(
            username="k6_user_no_group", password="test-only-not-a-secret",
            is_active=True, email="k6_user_no_group@test.invalid")
        with self.assertRaises(K6Error):
            usage_snapshot(scope=TenantScope.of(orphan))

    def test_storage_says_it_is_a_lower_bound_when_sizes_are_missing(self) -> None:
        """**크기를 모르는 파일은 「0바이트」가 아니다.** 하한을 총량처럼 청구하면
        그것은 우리에게 유리한 반올림이다 — 응답이 스스로 그렇게 말해야 한다.
        """
        from kernels.k6_feedback import usage_snapshot

        Media = apps.get_model("file_management", "UserMediaFile")
        Media.objects.create(group=self.group_a, file_name="k6-unsized.bin",
                             file_size=None)
        storage = usage_snapshot(scope=self.scope_a)["storage"]
        self.assertEqual(1, storage["unsized"])
        self.assertIn("하한", storage["why"],
                      "크기를 모르는 파일이 있는데 응답이 「하한」이라고 말하지 않습니다")


class KernelScopeSignatureTest(TestCase):
    """[D-281] 커널 공개 함수는 **스코프 없이는 호출 자체가 불가능**해야 한다."""

    def test_every_public_function_refuses_to_run_without_scope(self) -> None:
        import inspect

        from kernels import k6_feedback

        problems = []
        for name in ("record_feedback", "false_positive_rate",
                     "usage_snapshot", "kpi_series"):
            func = getattr(k6_feedback, name)
            sig = inspect.signature(func)
            scope = sig.parameters.get("scope")
            if scope is None:
                problems.append(f"{name}: scope 인자가 없다")
                continue
            if scope.kind is not inspect.Parameter.KEYWORD_ONLY:
                problems.append(f"{name}: scope 가 키워드 전용이 아니다")
            if scope.default is not inspect.Parameter.empty:
                problems.append(f"{name}: scope 에 기본값이 있다 — 필수가 아니다")
        self.assertEqual(
            [], problems,
            f"D-281 위반 — 커널 공개 함수는 `*, scope: TenantScope` 를 필수로 받습니다: "
            f"{problems}")


class KernelPublicSurfaceTest(TestCase):
    """DA-04 §2 K6 표가 정한 공개 면 4개가 **실재하는가.**"""

    #: DA-04 §2 K6 의 "공개 면" 열 그대로.
    SURFACE = ["record_feedback", "false_positive_rate", "usage_snapshot", "kpi_series"]

    def test_public_surface_matches_da04(self) -> None:
        from kernels import k6_feedback

        missing = [n for n in self.SURFACE if not hasattr(k6_feedback, n)]
        self.assertEqual(
            [], missing,
            f"DA-04 §2 K6 표의 공개 면이 커널에 없습니다: {missing}\n"
            "표를 바꾸려면 DA-04 와 이 목록을 **같은 커밋에서** 함께 고치십시오.")

    def test_kernel_does_not_import_apps(self) -> None:
        """계층 역전 금지 (D-278) — K6 도 App 을 import 하지 않는다."""
        import subprocess
        import sys
        from pathlib import Path

        here = Path(__file__).resolve()
        script = next(
            (c for c in (Path("/repo") / "scripts" / "verify_layers.py",
                         *(p / "scripts" / "verify_layers.py" for p in here.parents[1:4]))
             if c.is_file()), None)
        self.assertIsNotNone(
            script,
            "verify_layers.py 를 찾지 못했습니다 — docker-compose 의 "
            "`./scripts:/repo/scripts:ro` 마운트를 확인하십시오 (D-285 (4)).")
        out = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(0, out.returncode, out.stdout + out.stderr)
