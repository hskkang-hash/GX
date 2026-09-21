# -*- coding: utf-8 -*-
"""P-206 / D-508 — **청구서에서 씨앗을 뺀다** (2026-09-20 · 차선 U56).

이 파일이 묻는 것
-----------------
① **심어도 안 움직이는가** — probe 4 · drill 4 를 심기 **전후**로 계량의 수가
   한 건도 안 달라진다. 게이트가 심은 사건과 훈련은 행으로 남지만 **돈으로는 안 간다.**
② ★ **그런데 정말 세기는 하는가** — 실사건 **1 건**을 심으면 **정확히 +1**.
   ⚠ ①만 재면 **「전부 0으로 만드는 코드」가 통과한다.** 0 을 돌려주는 계량은
     가장 얇고, 가장 조용하고, 가장 틀렸다. 그래서 두 방향을 **같은 시험 안에서** 잰다.
③ **두 축을 다 잰다** — 사건(K1)과 발송(K2)은 다른 커널이고, 한쪽만 막으면 절반이다
   (P-193 이 실제로 그렇게 반만 닫혔다).
④ **테넌트** — B 가 무엇을 심어도 A 의 청구서는 안 움직인다.
⑤ **달 경계는 반열린** — 다음 달 1일 0시 정각의 한 건은 이 달 청구서에 없다.
⑥ **짝 맞추기** — 훈련 표식의 낱말이 `drill.DATA_SOURCE` 와 갈리지 않았는가.
⑦ **아직 못 뺀 것** — 표식 없는 옛 훈련 사건. 0으로 덮지 않고 시험으로 적어 둔다.

캐시 처리: 캐시를 타지 않는다 — 이 시험은 HTTP 를 한 번도 때리지 않고 계량 함수
(`apps.dsm.metering.usage`)를 **직접** 부른다. 응답 캐시도 `cache_page` 도 경유하지
않으므로 「적중 본문이 언제나 200」인 자리가 없다. 그래서 「심기 전」과 「심은 뒤」의
두 수는 **같은 실행에서 두 번 실제로 센 수**다.

★ 스레드에 남은 요청을 매번 지운다 — HTTP 를 때린 앞 시험이 남긴 요청이 `objects`
  필터에 실리면 **없는 격리가 초록으로 보인다**(턴 P 실측).
"""
from datetime import timedelta

from django.apps import apps
from django.utils import timezone

from tests.test_dsm_app import DsmFixture

#: ★ D-289 — 표본은 저장소 실물이다. 가짜 표를 만들어 재지 않는다.
REAL_SAMPLE = (
    "apps.dsm.metering.usage · kernels.k1_event.count_events · "
    "kernels.k2_notify.count_deliveries · common.billing_marks · "
    "common.probe_marker · stream_monitors.{DetectionEvent,DeliveryRecord} — "
    "저장소의 실제 모듈과 표"
)

#: 심는 수. **넷씩**인 것은 지시서가 정한 표본 크기다 — 1건이면 「우연히 안 셌다」와
#: 「안 세도록 만들었다」가 구별되지 않는다.
SEED_N = 4


def _code_string_literals(src: str) -> set:
    """소스에서 **독스트링이 아닌** 문자열 리터럴만 뽑는다.

    독스트링은 `Module`·`ClassDef`·`FunctionDef` 본문 맨 앞의 홀로 선 문자열이다.
    그것을 빼야 「설명했다」와 「적었다」가 갈린다.
    """
    import ast

    tree = ast.parse(src)
    docstrings = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            docstrings.add(id(first.value))
    return {n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docstrings}


def _clear_thread_request() -> None:
    """dj-core 가 스레드에 매단 요청을 끊는다. 없으면 조용히 지나간다."""
    try:
        from core.middleware.refresh_token import thread_local

        thread_local.request = None
    except Exception:                                        # noqa: BLE001
        pass


class MeteringSeedFixture(DsmFixture):
    """심는 손과 재는 손. **시험은 아래 클래스들에 있다**(여긴 0건)."""

    def setUp(self):
        _clear_thread_request()
        self.month = timezone.localtime().strftime("%Y-%m")
        self._seq = 0

    # ── 재는 손 ──────────────────────────────────────────────────────────
    def _bill(self, scope=None):
        """계량이 내는 **청구서의 수 세 개**. 부를 때마다 실제로 다시 센다."""
        from apps.dsm.metering import usage

        _clear_thread_request()
        got = usage(scope=scope or self.scope_a, month=self.month)
        by_key = {c["key"]: c["value"] for c in got["cells"]}
        return {
            "events": by_key["events"],
            "notifications": by_key["notifications"],
            "notifications_failed": got["notifications_failed"],
        }

    # ── 심는 손 ──────────────────────────────────────────────────────────
    def _plant_event(self, *, track_id=None, stream=None, when=None):
        """사건 하나를 **K1 생성 경로로** 심는다. 게이트가 심는 그 길이다.

        ⚠ 시각을 매번 벌린다 — K1 은 10초 창 안의 같은 스트림·유형을 **접는다**
          (`DEDUP_WINDOW`). 접히면 넷을 심었다고 믿으면서 하나를 심게 되고, 그
          시험은 아무것도 재지 않는다.
        """
        from kernels.k1_event import record_detection

        _clear_thread_request()
        self._seq += 1
        stream = stream or self.stream_a
        when = when or (timezone.now() - timedelta(seconds=30 * self._seq))
        result = record_detection(
            scope=self.scope_pipe, stream_monitor_id=stream.pk,
            event_type="fire", severity="critical", occurred_at=when,
            track_id=track_id,
            snapshot_path=f"minio://dsm/u56-{self._seq}.jpg")
        self.assertFalse(
            result.folded_into_existing,
            "심은 사건이 앞 건에 접혔습니다 — 시각 간격을 넓히십시오(표본 고장).")
        return result.event_id

    def _plant_delivery(self, event_id, *, succeeded=True, group=None):
        """발송 한 행. **사건에서 소유를 물려받는다** — 주인 없는 행은 §0.4 의
        `created_by__isnull` OR 절을 타고 모두에게 보인다.

        실패 행의 `sent_at` 은 **`None`** 이다(models.py). 여기서 시각을 넣으면
        「못 보낸 알림」이 「보낸 알림」과 같은 칸으로 세어진다.
        """
        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        event = Event._base_manager.get(pk=event_id)
        now = timezone.now()
        row = Delivery._base_manager.create(
            event=event, recipient=self.user_a,
            recipient_address="u56@test.invalid", channel="email",
            occurred_at=event.occurred_at,
            sent_at=now if succeeded else None,
            succeeded=succeeded,
            failure_reason=None if succeeded else "시험용 실패")
        return self._own(row, group or self.group_a)

    # ── 표식 ─────────────────────────────────────────────────────────────
    @staticmethod
    def _probe_mark(n: int) -> str:
        from common.probe_marker import PROBE_MARKER

        return f"{PROBE_MARKER};run=20260920T160000{n}"

    @staticmethod
    def _drill_mark(n: int) -> str:
        from common.probe_marker import DRILL_MARKER

        return f"{DRILL_MARKER};run=20260920T160000{n}"


class SeedsDoNotReachTheBillTest(MeteringSeedFixture):
    """①②③ — **심어도 안 움직이고, 실사건 하나면 정확히 +1.**"""

    def test_probe_and_drill_seeds_do_not_move_the_event_count(self) -> None:
        before = self._bill()

        probe_ids = [self._plant_event(track_id=self._probe_mark(i))
                     for i in range(SEED_N)]
        drill_ids = [self._plant_event(track_id=self._drill_mark(i))
                     for i in range(SEED_N)]

        # ★ **정말 심겼는가를 먼저 확인한다.** 안 심겼는데 「안 움직였다」로 초록이
        #   나는 것이 이 시험이 낼 수 있는 가장 나쁜 거짓말이다.
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        self.assertEqual(
            2 * SEED_N,
            Event._base_manager.filter(pk__in=probe_ids + drill_ids).count(),
            "표본이 안 심겼습니다 — 「안 움직였다」는 아무 뜻이 없습니다.")

        after = self._bill()
        self.assertEqual(
            before["events"], after["events"],
            f"게이트 씨앗 {SEED_N}건 · 훈련 {SEED_N}건을 심었더니 청구서의 이벤트 수가 "
            f"{before['events']} → {after['events']} 로 움직였습니다. "
            f"우리가 심은 사건에 고객이 돈을 냅니다 (P-206 · D-508).")

    def test_one_real_event_moves_the_event_count_by_exactly_one(self) -> None:
        """★ ②의 절반 — **전부 0으로 만드는 코드를 여기서 떨어뜨린다.**"""
        before = self._bill()
        self._plant_event(track_id=None)
        after = self._bill()
        self.assertEqual(
            before["events"] + 1, after["events"],
            f"실사건 1건을 심었는데 청구서가 {before['events']} → {after['events']} "
            f"입니다. **안 세는 계량은 0원짜리 청구서**이고, 그것은 과금 오류보다 "
            f"늦게 발견됩니다 — 아무도 항의하지 않기 때문입니다.")

    def test_both_directions_in_one_run(self) -> None:
        """①과 ②를 **한 실행 안에서** 잰다 — 두 시험이 따로 서면 한쪽만 도는 날이 온다."""
        base = self._bill()
        for i in range(SEED_N):
            self._plant_event(track_id=self._probe_mark(i))
            self._plant_event(track_id=self._drill_mark(i))
        seeded = self._bill()
        self.assertEqual(base["events"], seeded["events"])

        self._plant_event(track_id=None)
        real = self._bill()
        self.assertEqual(
            base["events"] + 1, real["events"],
            "씨앗 8건과 실사건 1건을 함께 심었을 때 청구서는 **정확히 1** 올라야 합니다.")

    def test_seeded_deliveries_do_not_move_the_notification_count(self) -> None:
        """③ **발송 축.** 표식은 발송 행에 없다 — `event` FK 너머에 있다."""
        before = self._bill()

        for i in range(SEED_N):
            self._plant_delivery(self._plant_event(track_id=self._probe_mark(i)))
            self._plant_delivery(self._plant_event(track_id=self._drill_mark(i)))

        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        self.assertGreaterEqual(
            Delivery._base_manager.count(), 2 * SEED_N,
            "발송 표본이 안 심겼습니다 — 「안 움직였다」는 아무 뜻이 없습니다.")

        after = self._bill()
        self.assertEqual(
            before["notifications"], after["notifications"],
            f"씨앗 때문에 나간 알림이 청구서에 올랐습니다: "
            f"{before['notifications']} → {after['notifications']}.")

    def test_one_real_delivery_moves_the_notification_count_by_exactly_one(self) -> None:
        before = self._bill()
        self._plant_delivery(self._plant_event(track_id=None))
        after = self._bill()
        self.assertEqual(
            before["notifications"] + 1, after["notifications"],
            "실제로 보낸 알림 1건이 청구서에 안 올랐습니다 — 매출이 조용히 샙니다.")

    def test_a_failed_delivery_is_counted_apart_and_not_billed(self) -> None:
        """실패는 **청구 칸에 안 들어가고**, 그렇다고 사라지지도 않는다 (D-290)."""
        before = self._bill()
        self._plant_delivery(self._plant_event(track_id=None), succeeded=False)
        after = self._bill()
        self.assertEqual(
            before["notifications"], after["notifications"],
            "못 보낸 알림에 돈을 받고 있습니다.")
        self.assertEqual(
            before["notifications_failed"] + 1, after["notifications_failed"],
            "실패가 어디에도 안 세어집니다 — 「보낸 적 없음」과 구별되지 않습니다. "
            "⚠ 실패 행의 `sent_at` 은 None 이라 그 칸으로 세면 이 수는 언제나 0 입니다.")

    def test_a_seeded_failure_is_not_counted_either(self) -> None:
        """실패 칸도 **씨앗을 안 센다** — 한 칸만 막으면 훈련 보고가 실패로 부풀었다."""
        before = self._bill()
        for i in range(SEED_N):
            self._plant_delivery(self._plant_event(track_id=self._drill_mark(i)),
                                 succeeded=False)
        after = self._bill()
        self.assertEqual(
            before["notifications_failed"], after["notifications_failed"],
            "훈련 중의 실패가 운영 실패 건수로 세어집니다.")


class TheBillStaysInsideTheTenantTest(MeteringSeedFixture):
    """④ — B 가 무엇을 심어도 A 의 청구서는 안 움직인다."""

    def test_the_other_tenants_events_never_reach_our_bill(self) -> None:
        before = self._bill(self.scope_a)
        for _ in range(SEED_N):
            self._plant_event(track_id=None, stream=self.stream_b)
        after = self._bill(self.scope_a)
        self.assertEqual(
            before["events"], after["events"],
            "남의 테넌트 사건이 우리 청구서에 올랐습니다. 이것은 틀린 청구가 아니라 "
            "**유출**입니다 — 남의 사건 수는 남의 사업 규모입니다.")

    def test_the_other_tenant_sees_its_own_count(self) -> None:
        """양성 대조 — B 쪽은 **오른다.** 안 오르면 위 초록은 「아무도 안 센다」다."""
        before = self._bill(self.scope_b)
        self._plant_event(track_id=None, stream=self.stream_b)
        after = self._bill(self.scope_b)
        self.assertEqual(before["events"] + 1, after["events"])


class TheMonthBoundaryIsHalfOpenTest(MeteringSeedFixture):
    """⑤ — 다음 달 1일 0시 정각의 한 건은 **이 달 청구서에 없다.**

    닫힌 구간으로 세면 그 한 건이 **두 장의 청구서**에 오른다. 고객은 같은 사건에
    두 번 돈을 내고, 우리는 그 사실을 다음 달에도 모른다.
    """

    def test_the_first_instant_of_next_month_is_not_in_this_month(self) -> None:
        from apps.dsm.metering import month_bounds

        start, end = month_bounds(self.month)
        before = self._bill()
        self._plant_event(track_id=None, when=end)
        after = self._bill()
        self.assertEqual(
            before["events"], after["events"],
            f"{end.isoformat()} (다음 달 1일 0시 정각)의 사건이 이 달({self.month}) "
            f"청구서에 들어왔습니다 — 반열린 구간이 아닙니다. 그 한 건은 다음 달에도 "
            f"세어져 두 번 청구됩니다.")
        self.assertLess(start, end)


class TheTwoMarkersAgreeTest(MeteringSeedFixture):
    """⑥ 짝 맞추기 — 낱말이 갈리면 한쪽이 조용히 이긴다."""

    def test_the_drill_marker_uses_the_same_word_as_the_drill_switch(self) -> None:
        from common.probe_marker import DRILL_MARKER
        from stream_monitors.services.drill import DATA_SOURCE

        self.assertEqual(
            DRILL_MARKER, f"data_source={DATA_SOURCE}",
            f"행 표식({DRILL_MARKER})과 창 판정의 출처 이름({DATA_SOURCE})이 다른 "
            f"낱말입니다. 두 축이 한 낱말로 모여야 화면이 한 배지를 그립니다 (P-201).")

    def test_the_billing_side_knows_both_markers_and_invents_neither(self) -> None:
        import inspect

        from common import billing_marks, probe_marker

        self.assertEqual(
            (probe_marker.PROBE_MARKER, probe_marker.DRILL_MARKER),
            billing_marks.UNBILLABLE_MARKERS,
            "청구 쪽이 아는 표식과 정본이 갈렸습니다.")
        # ★ **독스트링은 빼고 코드만** 본다. 「왜 probe 로는 drill 이 안 빠지는가」를
        #   설명하려면 그 글자를 적어야 하고, 설명까지 잡으면 이 시험은 늘 빨강이며
        #   **늘 빨간 시험은 꺼진다.** 설명은 죄가 아니다 — **리터럴이 죄다.**
        written = sorted(
            s for s in _code_string_literals(inspect.getsource(billing_marks))
            if s.startswith("data_source="))
        self.assertEqual(
            [], written,
            f"`common/billing_marks.py` 가 표식 문자열 {written} 를 **제 손으로 "
            f"적습니다.** 정본은 `common/probe_marker.py` 한 곳이고, 두 벌이 되는 "
            f"순간 한쪽을 고칠 때 다른 쪽은 안 고쳐집니다 (P-193 이 존재하는 이유).")

    def test_the_counting_face_takes_no_marker_switch(self) -> None:
        """P-201 이 **이름으로 금지한 칸**이 커널 셈 함수에 생기지 않았는가."""
        import inspect

        from kernels.k1_event import count_events
        from kernels.k2_notify import count_deliveries

        for fn in (count_events, count_deliveries):
            params = set(inspect.signature(fn).parameters)
            bad = sorted(p for p in params if "probe" in p or "drill" in p)
            self.assertEqual(
                [], bad,
                f"{fn.__name__} 에 표식 스위치 {bad} 가 생겼습니다. 청구의 셈은 "
                f"**언제나** 둘 다 뺍니다 — 「이번만 포함」이 생기면 그 자리가 다음 "
                f"달 청구서의 구멍입니다 (P-201).")


class WhatWeStillCannotSubtractTest(MeteringSeedFixture):
    """⑦ **아직 못 뺀 것을 0으로 덮지 않는다** (D-301).

    훈련의 정본 판정은 본래 **창(window)** 이다 — `stream_monitors/services/drill.py`
    의 감사 한 줄. 표식(P-201)은 그 위에 얹힌 **행 표시**이고, 표식이 **없는** 훈련
    사건(창 안에서 났지만 `track_id` 가 빈 행)은 표식 갈래로 못 뺀다. 창 판정을 셈에
    쓰려면 행마다 감사를 물어야 하고, 한 달 셈이 감사 전수 조회가 된다.

    ★ 이 시험은 **빚의 크기를 재는 시험**이다. 갚으면 빨강이 된다 —
      그때 이 클래스를 지우고 `common/billing_marks.py` 머리말의 ⚠ 절을 고치십시오.
      *빨강이 나는 것이 이 시험의 목적이다.*
    """

    def test_an_unmarked_event_is_still_billed_today(self) -> None:
        before = self._bill()
        self._plant_event(track_id=None)
        after = self._bill()
        self.assertEqual(
            before["events"] + 1, after["events"],
            "표식 없는 사건이 청구에서 빠졌습니다 — 빚이 갚혔거나(축하합니다) "
            "실사건이 안 세어지고 있습니다. 둘은 **다른 사실**이니 가려서 이 시험을 "
            "고치십시오(머리말 ★).")
