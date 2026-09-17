# -*- coding: utf-8 -*-
"""턴 S · 차선 U1 — 큐 카드의 **현장 신호**(지원 요청 · 조치 완료)를 잰다.

이 파일이 묻는 것 여섯
----------------------
  ① 분류가 **두 후보를 다 받는다** — 정형 접두(`[지원요청] …`)와 종류 칸(`kind`)
  ② 회신이 와도 **종류가 하나도 안 달려 있으면 `wired=False`** — 「데이터 없음」이
     아니라 **「배선 대기」**다. 둘을 가르는 것이 이 절의 값이다
  ③ 접두가 붙은 회신 하나로 `support_requested` 가 서고 `wired` 가 참이 된다
  ④ **남의 테넌트 사건은 목록에서 조용히 빠진다** — 404 도 403 도 내지 않는다
     (존재 여부도 누출이다). 물은 수와 읽은 수로만 드러난다
  ⑤ **상한이 실재한다** — 31개를 물어도 30까지만 읽는다
  ⑥ **문이 익명에게 안 열린다**(SEC-04) — HTTP 로 두드린다

★ **재조회로 잰다.** 회신을 실제 쓰기 경로(`services.field_reply`)로 남기고,
  읽는 것은 새 모듈이 부르는 그 함수다 — 합성 더미를 만들지 않는다(D-289).

★ **실재하지 않는 id 로 문을 두드린다**(⑥). 쓰기 면이 아니지만 관례는 같다 —
  이 시험이 묻는 것은 「관문이 서는가」이지 「값이 오는가」가 아니다.
"""
from __future__ import annotations

from types import SimpleNamespace

from django.test import Client, TestCase

from tests.test_dsm_app import DsmFixture

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "apps.dsm.queue_signals(신설) · apps.dsm.services.field_reply · "
    "apps.dsm.services.field_replies · logger.AuditLogs — 저장소의 실제 App 과 감사 "
    "표. 회신은 실제 쓰기 경로로 남긴다"
)


class ClassifyTest(TestCase):
    """① 분류 — **순수 함수다.** DB 없이 갈래 전부를 잰다."""

    def test_the_prefix_form_is_read(self) -> None:
        from apps.dsm import queue_signals

        self.assertEqual(
            "support",
            queue_signals.classify(SimpleNamespace(text="[지원요청] 사다리차 필요")))
        self.assertEqual(
            "support",
            queue_signals.classify(SimpleNamespace(text="[지원 요청] 인원 2명")))
        self.assertEqual(
            "done",
            queue_signals.classify(SimpleNamespace(text="[조치완료] 잔불 없음")))

    def test_the_kind_field_is_read_when_it_exists(self) -> None:
        """★ 그 칸은 **아직 없다**(턴 S 실측). 생기는 날 저절로 살아나는지를 잰다."""
        from apps.dsm import queue_signals

        self.assertEqual("support", queue_signals.classify(
            SimpleNamespace(text="사다리차 필요", kind="support_request")))
        self.assertEqual("done", queue_signals.classify(
            SimpleNamespace(text="끝났습니다", kind="action_done")))

    def test_a_plain_line_is_not_classified(self) -> None:
        """음성 대조 — 늘 참이면 그것은 분류가 아니다(D-277)."""
        from apps.dsm import queue_signals

        self.assertEqual("", queue_signals.classify(
            SimpleNamespace(text="현장 도착, 연기 없음")))
        # 접두는 **머리에 있을 때만**이다. 문장 안의 낱말은 신호가 아니다.
        self.assertEqual("", queue_signals.classify(
            SimpleNamespace(text="추가 [지원요청] 은 아직 필요 없습니다")))


class QueueFieldSignalsTest(DsmFixture):
    """②~⑤ — 실제 사건과 실제 회신으로 잰다."""

    def test_replies_without_a_kind_are_waiting_for_wiring_not_empty(self) -> None:
        """② **「데이터 없음」과 「배선 대기」를 가른다.**

        회신은 왔다(`reply_total` ≥ 1). 그런데 종류가 하나도 안 달려 있다
        (`typed_total` 0 · `wired` 거짓) — 그것은 현장이 조용한 것이 아니라
        **우리가 종류를 못 읽는 것**이다. 화면은 그 둘을 다르게 적어야 한다.
        """
        from apps.dsm import queue_signals, services

        eid = self._event(self.stream_a)
        services.field_reply(scope=self.scope_a, event_id=eid,
                             text="현장 도착, 연기 없음")

        out = queue_signals.queue_field_signals(
            scope=self.scope_a, event_ids=[eid])

        self.assertEqual(1, out["read"])
        self.assertEqual(1, out["signals"][0]["reply_total"])
        self.assertEqual(0, out["typed_total"])
        self.assertFalse(
            out["wired"],
            "회신은 왔는데 종류가 하나도 없습니다 — 그것은 「배선 대기」이지 "
            "「데이터 없음」이 아닙니다.")
        self.assertFalse(out["signals"][0]["support_requested"])

    def test_no_replies_at_all_is_also_not_wired(self) -> None:
        """회신이 0건이어도 `wired` 는 거짓이다 — 분류할 것이 없었으므로."""
        from apps.dsm import queue_signals

        eid = self._event(self.stream_a)
        out = queue_signals.queue_field_signals(
            scope=self.scope_a, event_ids=[eid])

        self.assertEqual(1, out["read"])
        self.assertEqual(0, out["signals"][0]["reply_total"])
        self.assertFalse(out["wired"])

    def test_a_support_request_marker_raises_the_badge(self) -> None:
        """③ 접두 하나로 배지가 서고 배선이 참이 된다."""
        from apps.dsm import queue_signals, services

        eid = self._event(self.stream_a)
        services.field_reply(scope=self.scope_a, event_id=eid,
                             text="[지원요청] 진입로가 막혔습니다")

        out = queue_signals.queue_field_signals(
            scope=self.scope_a, event_ids=[eid])
        row = out["signals"][0]

        self.assertTrue(row["support_requested"])
        self.assertIn("진입로", row["support_text"])
        self.assertFalse(row["action_done"])
        self.assertTrue(out["wired"])
        self.assertEqual(1, out["support_count"])

    def test_an_action_done_marker_opens_the_close_card(self) -> None:
        """③′ 「조치 완료」가 종결 확인 카드를 여는 신호다."""
        from apps.dsm import queue_signals, services

        eid = self._event(self.stream_a)
        services.field_reply(scope=self.scope_a, event_id=eid,
                             text="[조치완료] 잔불 없음, 철수합니다")

        row = queue_signals.queue_field_signals(
            scope=self.scope_a, event_ids=[eid])["signals"][0]

        self.assertTrue(row["action_done"])
        self.assertIn("잔불", row["action_done_text"])
        self.assertFalse(row["support_requested"])

    def test_another_tenants_event_is_dropped_silently(self) -> None:
        """④ 남의 사건은 **목록에 없다.** 404 도 403 도 내지 않는다 — 존재 여부도 누출이다."""
        from apps.dsm import queue_signals, services

        mine = self._event(self.stream_a)
        theirs = self._event(self.stream_b)
        services.field_reply(scope=self.scope_b, event_id=theirs,
                             text="[지원요청] 남의 테넌트 회신")

        out = queue_signals.queue_field_signals(
            scope=self.scope_a, event_ids=[mine, theirs])

        self.assertEqual(2, out["asked"])
        self.assertEqual(1, out["read"], "남의 테넌트 사건이 읽혔습니다 — 격리 실패입니다.")
        self.assertEqual([mine], [s["event_id"] for s in out["signals"]])
        self.assertEqual(
            0, out["support_count"],
            "남의 테넌트 지원 요청이 내 큐의 배지로 샜습니다.")

    def test_a_missing_event_looks_exactly_like_someone_elses(self) -> None:
        """④′ **같은 답이어야 한다.** 다르면 그 차이가 곧 존재 여부의 누출이다."""
        from apps.dsm import queue_signals

        theirs = self._event(self.stream_b)
        gone = 999_999_999

        a = queue_signals.queue_field_signals(
            scope=self.scope_a, event_ids=[theirs])
        b = queue_signals.queue_field_signals(
            scope=self.scope_a, event_ids=[gone])

        self.assertEqual(a["read"], b["read"])
        self.assertEqual(a["signals"], b["signals"])

    def test_the_cap_is_real(self) -> None:
        """⑤ 상한이 **실재한다** — 안 그러면 큐 전체가 읽기 폭풍이 된다."""
        from apps.dsm import queue_signals

        asked = list(range(900_000, 900_000 + queue_signals.MAX_EVENT_IDS + 5))
        out = queue_signals.queue_field_signals(scope=self.scope_a, event_ids=asked)

        self.assertEqual(queue_signals.MAX_EVENT_IDS, out["asked"])

    def test_duplicate_ids_are_asked_once(self) -> None:
        """같은 카드를 두 번 물어도 읽기는 한 번이다."""
        from apps.dsm import queue_signals

        eid = self._event(self.stream_a)
        out = queue_signals.queue_field_signals(
            scope=self.scope_a, event_ids=[eid, eid, eid])

        self.assertEqual(1, out["asked"])
        self.assertEqual(1, out["read"])


class TheDoorIsNotOpenToAnonymousTest(TestCase):
    """⑥ SEC-04 — **문을 두드린다.** 함수는 문이 아니다(F-05 착시 ⑨).

    캐시 처리: 우회(`X-No-Cache`) — 관문을 재는 시험이 캐시를 재면 문이 없어도 초록이 뜬다.
    """

    def setUp(self):
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().setUp()

        from tests.no_cache import NO_CACHE

        self.client = Client(**NO_CACHE)

    def test_anonymous_is_rejected(self) -> None:
        # ★ 실재하지 않는 id 로 두드린다 — 이 시험이 묻는 것은 관문 하나다.
        resp = self.client.get(
            "/api/dsm/queue/field-signals?event_ids=999999999")
        self.assertIn(
            resp.status_code, (401, 403),
            f"익명에게 {resp.status_code} 를 냈습니다 — 이 문은 계정 뒤에 서야 합니다.")

    def test_the_route_exists_at_all(self) -> None:
        """★ 음성 대조 — 401 이 **라우트가 없어서** 난 것이면 이 시험은 아무것도 안 잰 것이다.

        없는 경로는 404 다. 401/403 과 404 가 갈리는 것이 「문이 있다」의 증거다.
        """
        resp = self.client.get("/api/dsm/queue/field-signals-does-not-exist")
        self.assertEqual(
            404, resp.status_code,
            "없는 경로가 404 가 아닙니다 — 위 시험의 401 이 무엇을 뜻하는지 알 수 없습니다.")
