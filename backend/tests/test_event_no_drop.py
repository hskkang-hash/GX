# -*- coding: utf-8 -*-
"""D-367 — **재난 시스템에서 폭주는 정상 동작이다. 이벤트는 버리지 않는다.**

이 파일이 답하는 질문은 세종이 물은 그 질문이다:

    「`skipping` 이 이벤트를 **버리는 것인지 미루는 것인지 모릅니다.**
      버리는 거라면 **재난이 몰릴 때 이벤트가 사라집니다.**」

[실측 2026-09-11] 답은 둘로 갈렸다. 그 갈림을 **시험으로 못박는다** —
문장으로만 적으면 다음 사람이 또 판다(D-323).

    ① 이벤트 **행** 은 버려진 적이 없다.
       `kernels/k1_event/services.py::record_detection` 은 `@transaction.atomic`
       안에서 저장하고, 그 경로에는 상한도 큐도 없다.
       → `EventRowsNeverDroppedTest` 가 **투입 n = 저장 n** 으로 못박는다.

    ② 그러나 버려지던 것이 있었다 — **캐시 무효화**다.
       `common/cache_signal_protection.py::rate_limited` 가 200/분을 넘으면
       `return` 했다(= drop). 무효화를 버리면 **낡은 화면이 남고**, 폭주는 곧
       재난이므로 그때 관제 화면이 옛 데이터를 보여 준다.
       → `InvalidationDeferredNotDroppedTest` 가 **미룬 것이 다 처리됨**을 못박는다.

★ 부작위 시험이다 (D-300). 「이벤트가 생겼다」가 아니라 **「하나도 안 사라졌다」**를 본다.
  기능 시험은 있는 것을 보고, 이 시험은 **없어야 할 것이 없음**을 본다.

★ 등급 상수 (D-367 ③): **심각 등급은 어떤 경우에도 버리지 않는다.**
  `SeverityNeverDroppedTest` 가 그 상수를 지킨다.
"""
from __future__ import annotations

import contextlib

from django.apps import apps
from django.test import SimpleTestCase, TestCase

from common.cache_signal_protection import (
    CRITICAL_MODELS,
    DEFER_QUEUE_MAX,
    PRIORITY_CRITICAL,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    SignalProtection,
    priority_of,
    rate_limited,
)

#: 폭주 표본 (D-310 자기표본) — 부하시험에서 처음 `skipping` 이 뜬 조건 그대로:
#: **분당 상한(200)보다 많은 저장이 1분 안에 들어온다.**
SURGE_LIMIT = 200
SURGE_INPUT = 300

#: `common/cache_signal_protection.py::CRITICAL_MODELS` 와 **같은 커밋에서** 고친다.
#: 두 벌은 반드시 어긋난다 (D-369) — 그래서 아래 시험이 두 벌을 대조한다.
EXPECTED_CRITICAL_MODELS = {
    "detectionevent", "eventclip", "notificationrule", "deliveryrecord",
}


class _Sender:
    """`sender._meta.model_name` 만 보는 코드에 먹일 최소한의 대역."""

    def __init__(self, model_name: str):
        self._meta = type("M", (), {"model_name": model_name})()
        self.__name__ = model_name


class _Row:
    def __init__(self, pk: int):
        self.pk = pk


def _drain_all(limit=None, rounds: int = 200) -> int:
    total = 0
    for _ in range(rounds):
        done = SignalProtection.drain_deferred(limit)
        total += done
        if not done:
            break
    return total


# ═══════════════════════════════════════════════════════════════════════════
# ① 이벤트 **행** — 투입 n = 저장 n
# ═══════════════════════════════════════════════════════════════════════════
class EventRowsNeverDroppedTest(TestCase):
    """폭주 상황에서 **투입 n건 = 저장 n건.** 지연은 허용, 소실은 불허.

    ★ 왜 300건인가: 상한이 200/분이므로 **넘겨야** 재는 뜻이 있다. 200 아래에서
      초록이 나오는 시험은 그 상한을 한 번도 건드리지 않은 것이고, 그런 초록은
      「폭주 때 안전하다」를 말하지 못한다 (D-271 착시).

    ★ 왜 `event_type` 을 돌려 가며 넣는가: K1 은 같은 stream+type 의 10초 내
      재발을 **접는다**(`DEDUP_WINDOW`). 접기는 소실이 아니라 설계지만, 이 시험이
      재려는 것은 접기가 아니라 **소실**이다. 접기가 섞이면 「몇 건이 사라졌는가」를
      셀 수 없게 되므로 접히지 않는 투입을 만든다 (D-350 — 측정기를 먼저 의심한다).
    """

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        UserGroup = apps.get_model("user", "UserGroup")
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        from kernels.k1_event.services import _owner_field

        cls.group = UserGroup.objects.create(name="d367-tenant")
        UserGroup.objects.filter(pk=cls.group.pk).update(created_by=None)

        cls.streams = []
        for i in range(3):
            sm = StreamMonitor.objects.create(
                name=f"d367-stream-{i}", code=f"d367-stream-{i}",
                ip_source="rtsp://test.invalid/x")
            if _owner_field(StreamMonitor) == "groups":
                sm.groups.set([cls.group])
            else:
                sm.group = cls.group
                sm.save(update_fields=["group"])
            cls.streams.append(sm)

    def test_surge_input_equals_stored_rows(self) -> None:
        from datetime import timedelta

        from django.utils import timezone

        from common.tenant_scope import TenantScope
        from kernels.k1_event.services import record_detection

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        types = list(Event.EventType.values)
        scope = TenantScope.system(
            reason="D-367 폭주 시험 — 검출 파이프라인에는 요청자가 없다")

        before = Event._base_manager.count()
        base = timezone.now()
        put = 0
        for i in range(SURGE_INPUT):
            # 접히지 않게: 같은 (stream, type) 의 재발은 10초보다 멀리 둔다
            stream = self.streams[i % len(self.streams)]
            event_type = types[i % len(types)]
            record_detection(
                scope=scope,
                stream_monitor_id=stream.pk,
                event_type=event_type,
                severity="critical",
                occurred_at=base + timedelta(seconds=i * 60),
            )
            put += 1

        stored = Event._base_manager.count() - before
        self.assertEqual(
            stored, put,
            f"★ 폭주 소실: 투입 {put}건 · 저장 {stored}건 — {put - stored}건이 "
            f"사라졌다. 재난안전 시스템이 재난 때 이벤트를 잃으면, 평시에 아무리 "
            f"초록이어도 제품이 아니다 (D-367)")

    def test_no_rate_limit_stands_between_detection_and_the_row(self) -> None:
        """★ 부작위 — `record_detection` 경로에 **상한도 큐도 없다**는 사실을 잠근다.

        기록 경로에 속도 제한이 새로 붙는 날 이 시험이 빨개진다. 붙이는 것 자체가
        금지는 아니지만, **버리는 상한**이 붙으면 그때 이 시험이 그 사실을 말한다.
        """
        import inspect

        from kernels.k1_event import services

        src = inspect.getsource(services.record_detection)
        for banned in ("rate_limited", "check_rate_limit", "throttle"):
            self.assertNotIn(
                banned, src,
                f"record_detection 에 {banned!r} 이 들어왔다 — 기록 경로에 상한을 "
                f"두려면 **버리지 않는 상한**이어야 한다 (D-367)")


# ═══════════════════════════════════════════════════════════════════════════
# ② 캐시 무효화 — 미룬 것은 **다 처리된다**
# ═══════════════════════════════════════════════════════════════════════════
class InvalidationDeferredNotDroppedTest(SimpleTestCase):
    """상한을 넘은 무효화는 **미뤄지고, 미뤄진 것은 처리된다.**"""

    def setUp(self) -> None:
        SignalProtection.reset_defer_state()

    def tearDown(self) -> None:
        SignalProtection.reset_defer_state()

    def test_surge_runs_every_input_exactly_once(self) -> None:
        ran: list[int] = []

        @rate_limited(max_per_minute=SURGE_LIMIT)
        def handler(sender, instance, **kwargs):
            ran.append(instance.pk)

        sender = _Sender("detectionevent")
        for pk in range(SURGE_INPUT):
            handler(sender, _Row(pk))
        _drain_all(None)

        stats = SignalProtection.defer_stats()
        self.assertEqual(stats["dropped"], 0,
                         f"무효화를 {stats['dropped']}건 버렸다 — 0 이어야 한다")
        self.assertEqual(
            len(ran), SURGE_INPUT,
            f"투입 {SURGE_INPUT}건 · 실행 {len(ran)}건 — 지연은 허용이고 소실은 불허다")
        self.assertEqual(len(set(ran)), SURGE_INPUT, "같은 행이 두 번 세어졌다")
        self.assertEqual(stats["queue_len"], 0,
                         "흘린 뒤에도 큐가 남았다 — 미루기가 사실상 버리기가 된다")
        self.assertGreater(stats["deferred"], 0,
                           "상한을 넘겼는데 미룬 것이 0건이다 — 시험이 상한을 "
                           "건드리지 못했다. 그 초록은 아무 뜻이 없다 (D-271)")

    def test_same_row_is_folded_not_dropped(self) -> None:
        """같은 행의 반복은 **접는다.** 접기는 버리기가 아니다 — 마지막 상태로 한 번."""
        seen: list[object] = []

        def handler(sender, instance, **kwargs):
            seen.append(instance)

        sender = _Sender("detectionevent")
        rows = [_Row(7) for _ in range(5)]
        for row in rows:
            SignalProtection.defer(handler, sender, row, {},
                                   priority=PRIORITY_CRITICAL,
                                   model_name="detectionevent")
        _drain_all(None)

        stats = SignalProtection.defer_stats()
        self.assertEqual(stats["dropped"], 0, "접기를 버리기로 세었다")
        self.assertEqual(stats["coalesced"], 4, "접은 횟수가 통계에 안 남았다 (D-290)")
        self.assertEqual(len(seen), 1, "같은 행을 여러 번 무효화했다")
        self.assertIs(seen[0], rows[-1],
                      "접을 때 **마지막 상태**가 아니라 첫 상태를 남겼다 — "
                      "무효화는 최신 상태 기준이어야 한다")


# ═══════════════════════════════════════════════════════════════════════════
# ③ 등급 — **심각 등급은 어떤 경우에도 버리지 않는다.** 이건 상수다
# ═══════════════════════════════════════════════════════════════════════════
#: 큐를 채우려 시도하는 최대 바퀴 수. 흘리개가 비우는 속도가 채우는 속도를 넘으면
#: 영원히 안 차므로 **유한하게** 시도하고, 못 채우면 그 사실로 실패한다 —
#: 무한 재시도는 「못 쟀다」를 「통과」로 바꾸는 가장 흔한 길이다.
DEFER_ROUNDS_MAX = 5


class SeverityNeverDroppedTest(SimpleTestCase):

    def setUp(self) -> None:
        SignalProtection.reset_defer_state()

    def tearDown(self) -> None:
        SignalProtection.reset_defer_state()

    def test_critical_model_list_matches_the_second_copy(self) -> None:
        """두 벌은 반드시 어긋난다 (D-369) — 그러니 두 벌을 **대조한다.**"""
        self.assertEqual(set(CRITICAL_MODELS), EXPECTED_CRITICAL_MODELS)

    def test_detection_event_is_critical_regardless_of_its_severity(self) -> None:
        """★ 등급은 **모델**로 정한다 — `severity='info'` 인 탐지도 심각 경로다.

        낮은 등급의 탐지를 버리면 U1 의 **오탐률 분모**가 조용히 줄고, 그러면
        그 수가 거짓이 된다. 「낮은 등급 이벤트」와 「이벤트가 아닌 것」은 다르다.
        """
        self.assertEqual(priority_of(_Sender("detectionevent"), _Row(1)),
                         PRIORITY_CRITICAL)
        self.assertEqual(priority_of(_Sender("deliveryrecord"), _Row(1)),
                         PRIORITY_CRITICAL)
        self.assertEqual(priority_of(_Sender("periodictask"), _Row(1)),
                         PRIORITY_NORMAL)

    def test_full_queue_of_criticals_runs_inline_instead_of_dropping(self) -> None:
        def handler(sender, instance, **kwargs):
            pass

        sender = _Sender("detectionevent")

        # ★ **큐를 채웠다는 것을 먼저 확인한다** [실측 2026-09-06 · 턴 H]
        #   `_defer_queue` 는 **클래스 전역**이고 `_flush_loop` 이라는 데몬 스레드가
        #   그것을 비운다. 그 스레드는 첫 미룸 때 뜨고 **멈추는 손잡이가 없다.**
        #   그래서 이 파일을 혼자 돌리면(스레드가 안 뜬다) 통과하고, 앞선 시험이
        #   실제 m2m 무효화를 한 뒤에 돌면 채우는 사이 흘리개가 비워서
        #   `queued != run_now` 로 **진다.** 그날 실제로 그랬다:
        #     혼자: 8 passed · 묶음(1,149): 이 한 건만 실패
        #   ⚠ 그 빨강은 **규칙이 틀렸다는 뜻이 아니라 경주에서 졌다는 뜻**이다.
        #     둘을 같은 색으로 내면 다음 사람이 D-367 ③ 을 의심하게 된다 —
        #     의심해야 할 것은 이 시험의 격리다.
        #   그래서 **차오를 때까지 보충**하고, 그래도 안 차면 그 사실로 실패한다.
        pk = 0
        for _ in range(DEFER_ROUNDS_MAX):
            if SignalProtection.defer_stats()["queue_len"] >= DEFER_QUEUE_MAX:
                break
            for _ in range(DEFER_QUEUE_MAX):
                SignalProtection.defer(handler, sender, _Row(pk), {},
                                       priority=PRIORITY_CRITICAL,
                                       model_name="detectionevent")
                pk += 1
        queued_len = SignalProtection.defer_stats()["queue_len"]
        self.assertGreaterEqual(
            queued_len, DEFER_QUEUE_MAX,
            f"큐를 못 채웠다({queued_len}/{DEFER_QUEUE_MAX}) — 흘리개 스레드가 "
            f"채우는 속도보다 빠르게 비웠다. **이것은 D-367 ③ 의 반증이 아니라 "
            f"이 시험이 자기 상태를 못 세웠다는 뜻이다.**")

        outcome = SignalProtection.defer(handler, sender, _Row(10 ** 9), {},
                                         priority=PRIORITY_CRITICAL,
                                         model_name="detectionevent")
        self.assertEqual(
            outcome, "run_now",
            "큐가 심각 등급으로 찼는데 새 심각 등급을 큐에 넣거나 버렸다 — "
            "버릴 수 없으면 **그 자리에서 처리한다** (D-367 ③)")
        self.assertEqual(SignalProtection.defer_stats()["dropped"], 0)

    def test_full_queue_evicts_the_lowest_grade_not_the_oldest(self) -> None:
        """가장 **오래된** 것을 심각 등급으로 두고, 낮은 등급이 나가는지 본다."""
        def handler(sender, instance, **kwargs):
            pass

        crit, low = _Sender("detectionevent"), _Sender("sometable")
        SignalProtection.defer(handler, crit, _Row(1), {},
                               priority=PRIORITY_CRITICAL,
                               model_name="detectionevent")
        for pk in range(2, DEFER_QUEUE_MAX + 1):
            SignalProtection.defer(handler, low, _Row(pk), {},
                                   priority=PRIORITY_LOW, model_name="sometable")
        SignalProtection.defer(handler, low, _Row(10 ** 9), {},
                               priority=PRIORITY_NORMAL, model_name="sometable")

        stats = SignalProtection.defer_stats()
        self.assertEqual(stats["dropped"], 1, "자리를 하나만 비웠어야 한다")
        self.assertNotIn("detectionevent", stats["drop_detail"],
                         "★ 가장 오래된 것이 심각 등급인데 그것을 버렸다 — "
                         "버릴 것은 나이가 아니라 **가장 낮은 등급**이다")
