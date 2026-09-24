# -*- coding: utf-8 -*-
"""대응 시계 — **네 시각을 어디서 세우는가, 그리고 무엇을 분모에서 빼는가**
(UX-13 · UX-14 · 차선 C · 2026-09-24).

이 파일이 묻는 것 셋
--------------------
① **네 시각이 실제로 세워지는가.** 착수 전 실측이 지시서를 고쳤다: 넷 중 모델에
   있는 것은 `occurred_at` 하나뿐이고 나머지 셋은 대응 전이 **감사**에 있다.
   그러니 이 시험은 「칸이 있는가」가 아니라 **「감사를 읽어 셋이 나오는가」**를 묻는다.

② **자동 종결이 분모에서 빠지는가** (지시서 §3-4). 빼지 않으면 오탐 자동 종결이
   대응 시간을 좋게 만든다 — 규칙이 0초 만에 닫은 건이 분모에 들어가면 **오탐이
   많은 달일수록 대응이 빨라 보인다.** 지표가 사실의 정반대를 말하는 자리다.
   ★ 이 시험이 이 파일에서 가장 값있다. 나머지는 계산을 보고, 이것은 **설계**를 본다.

③ **묶어도 수가 줄지 않는가** (UX-13). 카드는 접히고 이벤트는 안 접힌다.
   `total_events`(원본)와 `card_total`(카드)이 **다른 수로 함께** 나가는지를 본다 —
   둘을 같은 수로 내면 F-14 통계와 화면이 다른 말을 하게 된다.

무엇을 다시 묻지 않나
---------------------
전이 규칙(D-399)은 `tests/test_response_flow.py` 가, 오탐률(K6)은 K6 시험이 잰다.
여기서 다시 물으면 같은 사실을 두 벌로 재고, 커널이 바뀔 때 두 곳에서 깨진다.
"""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from tests.test_dsm_app import DsmFixture

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "stream_monitors.services.response_clock · apps.dsm.services.response_clock / "
    "response_latency / focus_queue · kernels.k1_event.response_flow(advance_response · "
    "close_as_false_positive) · logger.AuditLogs — 저장소의 실제 모듈과 실제 감사 표. "
    "합성 더미를 부르지 않는다"
)


class ConstantsMatchTheKernelTest(DsmFixture):
    """★ **두 벌을 두되 갈라지는 것을 시험이 본다** (D-337 계열).

    `response_clock.py` 는 `LOGGER_NAME`·`AUTO_CLOSE_ACTOR`·상태 넷을 **글자로** 든다.
    커널을 import 하면 그 파일이 K1 소비자가 되어 `test_f05_event_api.K1_CONSUMERS`
    대장을 늘려야 하고, 그것은 「감사 한 표를 읽는다」에 비해 과한 선언이다.
    그래서 두 벌을 두고 **여기서 대조한다** — `response_flow.py` 가 `STATES` 에 대해
    쓴 것과 같은 규약이다.
    """

    def test_the_logger_name_matches(self) -> None:
        from kernels.k1_event import response_flow
        from stream_monitors.services import response_clock

        self.assertEqual(
            response_flow.LOGGER_NAME, response_clock.LOGGER_NAME,
            "대응 전이 감사의 이름이 두 벌로 갈렸습니다 — 갈리면 시계가 **아무 전이도 "
            "못 찾고**, 못 찾은 시계는 「아무도 대응 안 함」과 같은 그림입니다.")

    def test_the_auto_close_actor_matches(self) -> None:
        from kernels.k1_event import response_flow
        from stream_monitors.services import response_clock

        self.assertEqual(
            response_flow.FALSE_POSITIVE_ACTOR, response_clock.AUTO_CLOSE_ACTOR,
            "자동 종결 행위자의 이름이 갈렸습니다 — 갈리면 자동 종결이 **분모에서 안 "
            "빠지고**, 그러면 오탐이 많을수록 대응 시간이 좋아집니다(§3-4).")

    def test_the_four_states_match(self) -> None:
        from kernels.k1_event import response_flow
        from stream_monitors.services import response_clock

        self.assertEqual(
            list(response_flow.STATES),
            [response_clock.OCCURRED, response_clock.ACKNOWLEDGED,
             response_clock.IN_PROGRESS, response_clock.CLOSED])


class FourStampsComeFromTheAuditTest(DsmFixture):
    """① 네 시각이 **감사에서** 세워지는가."""

    def test_a_fresh_event_has_only_the_first_stamp(self) -> None:
        """전이 전에는 **셋이 비어 있다 — 0 이 아니다** (D-290).

        빈 것을 0 으로 내면 「아무도 접수 안 함」이 「즉시 접수」로 보인다.
        """
        from apps.dsm import services

        eid = self._event(self.stream_a)
        clock = services.response_clock(scope=self.scope_a, event_id=eid)

        self.assertIsNotNone(clock["occurred_at"])
        for name in ("acknowledged_at", "arrived_at", "closed_at"):
            self.assertIsNone(clock[name], f"{name} 이 비어 있지 않습니다.")
        for name in ("acknowledge_seconds", "arrive_seconds", "close_seconds"):
            self.assertIsNone(
                clock[name],
                f"{name} 이 None 이 아닙니다 — 「아직 안 일어났다」를 0 으로 내면 "
                f"「즉시 대응」과 구별되지 않습니다.")

    def test_each_forward_step_fills_exactly_one_stamp(self) -> None:
        """한 칸 옮길 때마다 시각이 **하나씩** 채워진다."""
        from apps.dsm import services

        eid = self._event(self.stream_a)

        services.advance_response(scope=self.scope_a, event_id=eid,
                                  to_state="acknowledged")
        clock = services.response_clock(scope=self.scope_a, event_id=eid)
        self.assertIsNotNone(clock["acknowledged_at"], "접수 시각이 안 세워졌습니다.")
        self.assertIsNone(clock["arrived_at"])

        services.advance_response(scope=self.scope_a, event_id=eid,
                                  to_state="in_progress")
        clock = services.response_clock(scope=self.scope_a, event_id=eid)
        self.assertIsNotNone(clock["arrived_at"], "조치 착수 시각이 안 세워졌습니다.")
        self.assertIsNone(clock["closed_at"])

        services.advance_response(scope=self.scope_a, event_id=eid,
                                  to_state="closed")
        clock = services.response_clock(scope=self.scope_a, event_id=eid)
        self.assertIsNotNone(clock["closed_at"], "종결 시각이 안 세워졌습니다.")
        self.assertFalse(clock["auto_closed"],
                         "사람이 닫은 것을 자동 종결로 세었습니다.")
        #: 시계가 **멈춘다.** 닫힌 이벤트가 계속 커지면 화면이 「급한 것」을 잘못 가리킨다.
        self.assertIsNone(clock["elapsed_seconds"])
        self.assertEqual(0, clock["urgency_tier"])
        self.assertEqual(3, len(clock["transitions"]))

    def test_the_stamps_are_ordered_and_measured_from_occurrence(self) -> None:
        """구간 셋은 **발생부터** 잰다 — 접수부터가 아니다.

        사람이 늦게 접수한 시간도 현장이 기다린 시간이다. 접수부터 재면 접수를
        늦게 할수록 「도착이 빨랐다」가 된다.
        """
        from apps.dsm import services

        eid = self._event(self.stream_a)
        for state in ("acknowledged", "in_progress", "closed"):
            services.advance_response(scope=self.scope_a, event_id=eid, to_state=state)
        clock = services.response_clock(scope=self.scope_a, event_id=eid)

        self.assertLessEqual(clock["acknowledge_seconds"], clock["arrive_seconds"])
        self.assertLessEqual(clock["arrive_seconds"], clock["close_seconds"])
        #: 발생은 60초 전(픽스처)이므로 세 구간 모두 그보다 크다.
        self.assertGreater(clock["acknowledge_seconds"], 0)

    def test_the_clock_does_not_leak_across_tenants(self) -> None:
        """★ 남의 이벤트 시계를 못 본다. **문지기는 K1 이 그대로 선다** — 새로 만들지 않았다."""
        from django.http import Http404

        from apps.dsm import services

        eid = self._event(self.stream_a)
        with self.assertRaises(Http404):
            services.response_clock(scope=self.scope_b, event_id=eid)


class AutoCloseLeavesTheDenominatorTest(DsmFixture):
    """② ★ **자동 종결은 대응 시간의 분모에서 빠진다** (지시서 §3-4).

    이 시험이 이 파일에서 가장 값있는 자리다. 나머지는 계산을 보고 이것은 설계를 본다.
    """

    def _auto_close(self, event_id: int) -> None:
        from kernels.k1_event.response_flow import close_as_false_positive

        close_as_false_positive(event_id, reason="시험 — 오탐 자동 종결",
                                scope=self.scope_a)

    def test_an_auto_closed_event_is_marked_as_such(self) -> None:
        """「사람이 닫았다」와 **같은 모양으로 내보내지 않는다.**"""
        from apps.dsm import services

        eid = self._event(self.stream_a)
        self._auto_close(eid)
        clock = services.response_clock(scope=self.scope_a, event_id=eid)

        self.assertIsNotNone(clock["closed_at"])
        self.assertTrue(
            clock["auto_closed"],
            "규칙이 닫은 건이 사람이 닫은 것과 같은 모양으로 나갑니다 — 그러면 "
            "대응 시간 통계가 오탐을 「잘한 일」로 셉니다.")
        #: 계단을 오르지 않았다. 접수·착수는 **여전히 비어 있어야** 한다 —
        #: 세 번의 가짜 전이로 흉내 내면 감사가 「누가 접수했다」고 거짓말을 한다.
        self.assertIsNone(clock["acknowledged_at"])
        self.assertIsNone(clock["arrived_at"])

    def test_auto_closed_events_do_not_enter_the_latency_denominator(self) -> None:
        """★ **본론.** 자동 종결을 빼지 않으면 오탐이 많을수록 대응이 빨라 보인다.

        사람이 닫은 1건(느림)과 규칙이 닫은 3건(0초에 가까움)을 섞어 둔다.
        분모에서 안 빼면 p50 이 **0초 쪽으로 끌려간다** — 그것이 착시다.
        """
        from apps.dsm import services

        slow = self._event(self.stream_a)
        for state in ("acknowledged", "in_progress", "closed"):
            services.advance_response(scope=self.scope_a, event_id=slow, to_state=state)

        for _ in range(3):
            self._auto_close(self._event(self.stream_a))

        stats = services.response_latency(scope=self.scope_a)

        self.assertEqual(
            3, stats["excluded_auto_closed"],
            f"자동 종결 3건을 분모에서 빼지 않았습니다: {stats}")
        self.assertEqual(
            1, stats["close"]["n"],
            "종결 구간의 분모에 자동 종결이 섞여 있습니다 — 그러면 오탐이 많은 달일수록 "
            "대응 시간이 좋아집니다(§3-4).")
        #: 사람이 닫은 그 1건이 그대로 p50 이어야 한다.
        self.assertTrue(stats["close"]["measurable"])
        self.assertGreater(stats["close"]["p50"], 0)

    def test_an_empty_denominator_is_null_not_zero(self) -> None:
        """분모 0 이면 p50 은 **`null` 이다 — 0.0 이 아니다** (D-301 계열).

        0.0 으로 내면 「아무도 대응 안 한 달」이 「즉시 대응한 달」과 같은 숫자가 된다.
        """
        from apps.dsm import services

        self._event(self.stream_a)                # 전이 없음 — 잴 것이 없다
        stats = services.response_latency(scope=self.scope_a)

        self.assertEqual(0, stats["close"]["n"])
        self.assertIsNone(stats["close"]["p50"])
        self.assertIsNone(stats["close"]["p95"])
        self.assertFalse(stats["close"]["measurable"])

    def test_the_reported_numbers_carry_their_denominators(self) -> None:
        """비율만 내지 않는다 — **분자·분모를 함께** 낸다 (D-271 ③ · D-301)."""
        from apps.dsm import services

        self._event(self.stream_a)
        stats = services.response_latency(scope=self.scope_a)
        for key in ("events", "counted", "excluded_auto_closed", "sampled",
                    "sample_cap", "sample_capped", "tier_thresholds_sec"):
            self.assertIn(key, stats, f"{key} 가 응답에 없습니다 — 모수 없는 백분위는 "
                                      f"7건과 700건을 같은 숫자로 내보냅니다.")


class UrgencyTierTest(DsmFixture):
    """카드 글자가 커지는 문턱 — **30초 · 2분 · 5분 · 8분.**"""

    def test_the_thresholds_are_the_four_the_instruction_named(self) -> None:
        from stream_monitors.services.response_clock import URGENCY_THRESHOLDS_SEC

        self.assertEqual((30, 120, 300, 480), URGENCY_THRESHOLDS_SEC)

    def test_each_threshold_raises_the_tier_by_exactly_one(self) -> None:
        """**한 단계씩** 오른다. 두 단계를 건너뛰면 사람이 「무슨 일이 있었나」를 못 읽는다."""
        from stream_monitors.services.response_clock import urgency_tier

        self.assertEqual(0, urgency_tier(0))
        self.assertEqual(0, urgency_tier(29.9))
        self.assertEqual(1, urgency_tier(30))
        self.assertEqual(2, urgency_tier(120))
        self.assertEqual(3, urgency_tier(300))
        self.assertEqual(4, urgency_tier(480))
        self.assertEqual(4, urgency_tier(99_999))

    def test_a_stopped_clock_is_tier_zero(self) -> None:
        """닫힌 이벤트는 커지지 않는다 — 계속 커지면 화면이 「급한 것」을 잘못 가리킨다."""
        from stream_monitors.services.response_clock import urgency_tier

        self.assertEqual(0, urgency_tier(None))

    def test_the_threshold_table_travels_with_the_answer(self) -> None:
        """★ 표를 **응답에 실어 보낸다** — 화면이 자기 표를 들면 통계와 글자가 갈린다.

        `allowed_next` 를 서버가 주는 것과 같은 규약이다(D-399).
        """
        from apps.dsm import services

        self._event(self.stream_a)
        queue = services.focus_queue(scope=self.scope_a)
        self.assertEqual([30, 120, 300, 480], queue["tier_thresholds_sec"])


class FocusQueueTest(DsmFixture):
    """③ 단일 초점 큐 — **가장 급한 하나**와 5분 창 묶음 (UX-13)."""

    def test_the_top_is_one_not_a_list(self) -> None:
        """최상단은 **하나**다. 나머지는 `queue` 로 내려간다."""
        from apps.dsm import services

        for _ in range(4):
            self._event(self.stream_a)
        result = services.focus_queue(scope=self.scope_a)

        self.assertIsNotNone(result["focus"], "가장 급한 하나가 없습니다.")
        self.assertNotIn(result["focus"]["event_id"],
                         [c["event_id"] for c in result["queue"]],
                         "초점이 대기 큐에 또 나옵니다 — 같은 사건이 두 자리를 먹습니다.")

    def test_closed_cards_do_not_sit_in_the_queue(self) -> None:
        """★★ **끝난 일은 「지금 처리할 것」이 아니다** (P-288 · 2026-09-24 턴 AH).

        ★ 출생 표본 — **대표가 화면을 보고 찾았다.** 「대기 카드 12장」이라 적혀 있는데
          그 **열둘이 전부 종결**이었다. 관제요원의 첫 화면이 「할 일 12개」라고 말하면서
          실제 할 일은 **0개**였고, 게이트는 그동안 초록이었다.

        왜 아무도 못 봤나: 종전 정렬은 닫힌 것을 **뒤로 미루기만** 했다. 열린 것이
        하나라도 있으면 그것이 최상단에 오니 `focus` 는 늘 옳았다 — **틀린 것은 그
        아래 꼬리였고, 시험은 최상단만 보고 있었다.**
        """
        from apps.dsm import services

        #: ★ 카드가 갈리도록 유형을 달리한다 — 같은 `stream+type` 은 5분 창이 한 장으로
        #:   묶어, 닫아도 카드가 안 닫힌다(위 시험의 조율자 실측 참조).
        eids = [self._event(self.stream_a, event_type=t)
                for t in ("fire", "intrusion", "flood")]
        for eid in eids[1:]:
            for state in ("acknowledged", "in_progress", "closed"):
                services.advance_response(scope=self.scope_a, event_id=eid,
                                          to_state=state)

        result = services.focus_queue(scope=self.scope_a)
        still = [c for c in result["queue"] if c["closed_at"] is not None]
        self.assertEqual(
            [], still,
            "종결된 카드가 대기 큐에 %d장 앉아 있습니다. 화면은 「할 일」이라 말하는데 "
            "누를 것이 없습니다 — 「종결 확인」 절이 그 카드를 보여 주는 자리입니다."
            % len(still))

    def test_the_hidden_count_is_told_not_swallowed(self) -> None:
        """★ **조용히 빼지 않는다.** 뺀 수를 함께 낸다.

        이 칸이 없으면 화면은 「대기 0장」이라 말하는데 사람은 **왜 0 인지** 모른다 —
        「일이 없다」와 「다 끝났다」는 다른 사실이고, 첫 근무일에 그 둘을 못 가르면
        관제요원은 화면이 고장 난 줄 안다.
        """
        from apps.dsm import services

        #: ★★ [조율자 실측 — 첫 판이 여기서 빨갰다] 같은 스트림·같은 유형으로 셋을
        #:   만들면 **5분 창이 한 장으로 묶는다.** 그러면 둘을 닫아도 **카드는 안
        #:   닫히고** 뺀 수가 0 이다 — 시험이 틀린 게 아니라 **표본이 틀렸다.**
        #:   카드가 갈리려면 `stream+type` 이 달라야 한다(`GROUP_WINDOW_SECONDS` 규약).
        eids = [self._event(self.stream_a, event_type=t)
                for t in ("fire", "intrusion", "flood")]
        for eid in eids[1:]:
            for state in ("acknowledged", "in_progress", "closed"):
                services.advance_response(scope=self.scope_a, event_id=eid,
                                          to_state=state)

        result = services.focus_queue(scope=self.scope_a)
        self.assertGreater(
            result["closed_cards_hidden"], 0,
            "종결 카드를 뺐는데 뺀 수가 0 입니다 — 조용히 사라졌습니다.")
        #: ★★ **수는 줄지 않는다.** `total_events`·`card_total` 은 「무슨 일이 있었나」를
        #:   세는 수이고 종결도 거기 든다. 큐에서만 뺀 것이지 기록에서 뺀 것이 아니다.
        self.assertEqual(
            len(eids), result["total_events"],
            "큐에서 뺐더니 **원본 건수까지** 줄었습니다 — 접히는 것은 화면이지 기록이 "
            "아닙니다(F-14 통계가 이 수를 셉니다).")
        self.assertEqual(
            result["card_total"],
            (1 if result["focus"] else 0) + len(result["queue"])
            + result["closed_cards_hidden"],
            "카드 수가 안 맞습니다 — `card_total` 과 화면이 **다른 함수로** 세고 "
            "있으면 두 수가 갈리고, 갈린 쪽이 조용히 이깁니다.")

    def test_all_closed_means_no_focus_not_a_closed_focus(self) -> None:
        """★ 음성 대조 — **전부 닫힌 날**에 「가장 급한 하나」가 있으면 안 된다.

        종전에는 `ordered[0]` 이라 **이미 끝난 사건이 최상단에** 섰다. 그 화면은
        「할 일이 없다」가 아니라 **「이걸 하라」**고 말한다 — 정반대다.
        """
        from apps.dsm import services

        eid = self._event(self.stream_a)
        for state in ("acknowledged", "in_progress", "closed"):
            services.advance_response(scope=self.scope_a, event_id=eid,
                                      to_state=state)

        result = services.focus_queue(scope=self.scope_a)
        self.assertIsNone(
            result["focus"],
            "전부 닫혔는데 「가장 급한 하나」가 있습니다 — 끝난 사건을 하라고 "
            "가리키는 화면입니다.")
        self.assertEqual([], result["queue"])
        self.assertGreater(result["closed_cards_hidden"], 0,
                           "전부 닫혔는데 뺀 수가 0 입니다.")

    def test_the_focus_is_the_oldest_open_one_not_the_newest(self) -> None:
        """★ **최신순이 아니다.** 최신순이면 새 이벤트가 계속 최상단을 밀어내고,
        가장 오래 방치된 사건이 영원히 안 보인다 — 지금 화면이 그 모양이다."""
        from apps.dsm import services

        now = timezone.now()
        old = self._event(self.stream_a, when=now - timedelta(minutes=30))
        # 같은 카메라·같은 유형이면 한 카드로 묶이므로 **다른 카메라**로 심는다.
        stream_a2 = self._stream("dsm-stream-A2", self.group_a)
        self._event(stream_a2, when=now - timedelta(seconds=5))

        result = services.focus_queue(scope=self.scope_a)
        self.assertEqual(
            old, result["focus"]["event_id"],
            "최신 이벤트가 최상단에 왔습니다 — 가장 오래 기다린 사건이 밀려납니다.")

    def test_repeats_collapse_into_one_card_but_the_count_survives(self) -> None:
        """★ **이벤트는 접지 않는다.** 카드만 접히고 원본 건수는 그대로 나간다.

        F-14 통계는 원본을 세고, 두 수를 **다른 이름으로 함께** 내보내는 것이
        그 약속의 증거다.
        """
        from apps.dsm import services

        now = timezone.now()
        ids = [self._event(self.stream_a, when=now - timedelta(seconds=10 * i))
               for i in range(7)]
        result = services.focus_queue(scope=self.scope_a)

        self.assertEqual(7, result["total_events"],
                         "원본 건수가 줄었습니다 — 접히는 것은 화면이지 기록이 아닙니다.")
        self.assertEqual(1, result["card_total"],
                         "5분 창 안의 같은 카메라·같은 유형이 한 장으로 안 묶였습니다.")
        self.assertEqual(7, result["focus"]["count"], "×N 배지의 수가 틀립니다.")
        self.assertEqual(sorted(ids), sorted(result["focus"]["member_event_ids"]),
                         "무엇이 묶였는지를 낼 수 없으면 「1장으로 줄었다」와 "
                         "「6건이 사라졌다」가 구별되지 않습니다(D-290).")

    def test_events_outside_the_window_are_not_collapsed(self) -> None:
        """창 밖은 **다른 카드**다. 창이 없으면 어제 것과 지금 것이 한 장이 된다."""
        from apps.dsm import services

        now = timezone.now()
        self._event(self.stream_a, when=now - timedelta(seconds=30))
        self._event(self.stream_a, when=now - timedelta(minutes=40))

        result = services.focus_queue(scope=self.scope_a)
        self.assertEqual(2, result["total_events"])
        self.assertEqual(2, result["card_total"],
                         "5분 창 밖의 이벤트가 같은 카드로 묶였습니다.")

    def test_different_types_on_the_same_camera_stay_apart(self) -> None:
        """묶는 키는 `stream+type` 둘이다. 카메라만 보면 **화재와 침수가 한 장**이 된다."""
        from apps.dsm import services

        now = timezone.now()
        self._event(self.stream_a, event_type="fire", when=now - timedelta(seconds=20))
        self._event(self.stream_a, event_type="flood", when=now - timedelta(seconds=10))

        result = services.focus_queue(scope=self.scope_a)
        self.assertEqual(2, result["card_total"])

    def test_the_queue_does_not_leak_across_tenants(self) -> None:
        """★ 남의 테넌트 이벤트가 최상단에 오면 격리 실패다."""
        from apps.dsm import services

        self._event(self.stream_b)
        result = services.focus_queue(scope=self.scope_a)
        self.assertEqual(0, result["total_events"])
        self.assertIsNone(result["focus"])

    def test_the_focus_carries_the_transition_table_from_the_server(self) -> None:
        """버튼은 서버가 준 `allowed_next` 로만 그린다 — 화면이 표를 들면
        **서버가 거절하는 버튼**을 그리게 된다 (D-399)."""
        from apps.dsm import services

        self._event(self.stream_a)
        result = services.focus_queue(scope=self.scope_a)
        self.assertEqual(["acknowledged"], result["focus"]["allowed_next"])
