# -*- coding: utf-8 -*-
"""턴 W · 차선 U1 · P-188 — 큐 카드 **1클릭 판정 3**이 기대는 서버 약속을 잰다.

무엇을 고쳤길래 이 시험이 생겼나
--------------------------------
큐 화면(`FocusQueue.tsx`)의 단추 셋은 **초점 카드 한 장에만** 있었다. 대기 카드에는
「열기」뿐이라, 두 번째로 급한 사건을 처리하려면 **상세로 들어갔다 나와야** 했다 —
UX-33 이 없애기로 한 바로 그 왕복이고, 온보딩 U1#11 이 ○ 로 찍힌 자리다.

이제 대기 카드도 단추를 그린다. 그런데 그 단추는 **화면이 지어낸 것이면 안 된다** —
서버가 `allowed_next` 로 말한 갈래만 그려야 한다(D-399). 대기 카드에는 큐 응답이
`allowed_next` 를 주지 않으므로, 화면은 **기존 문** `GET /api/dsm/queue/field-signals`
가 내는 `signals[].allowed_next` 를 쓴다. **새 라우트를 만들지 않았다.**

이 파일이 묻는 것 다섯
----------------------
  ① `/queue/field-signals` 의 `allowed_next` 가 **상세가 쓰는 표와 같은 값**인가.
     갈리면 큐 카드와 상세 화면이 서로 다른 단추를 그린다 — 표는 하나여야 한다.
  ② **종결된 사건은 `allowed_next` 가 빈 목록**인가. 화면은 그때 단추를 0개 그리고
     「더 갈 곳이 없습니다」를 적는다 — 그 글자가 거짓이 아니어야 한다.
  ③ 목록에 **없는 사건**(남의 테넌트·없는 번호)은 화면이 `allowed_next` 를 **못 받는다**.
     그때 화면이 적는 말은 「없음」이 아니라 **「아직 못 들었다」**여야 하고, 이 시험은
     그 둘을 화면이 가를 수 있게 서버가 **빈 목록과 부재를 다르게** 낸다는 것을 못박는다.
  ④ `allowed_next` 에 **없는 갈래를 눌러도 서버가 거절한다.** 화면이 그 단추를 감추는
     것은 **편의**이지 방벽이 아니다 — 감춘 것을 지나쳐 부르면 서버가 막아야 한다.
  ⑤ `allowed_next` 에 **있는 갈래는 실제로 열린다** — 감출 이유가 없는 것을 감추고
     있지 않다는 반대 방향의 증거다. **분모 0인 초록을 만들지 않는다.**

★ **재조회로 잰다.** 옮긴 뒤 같은 문을 다시 읽어 값이 바뀌었는지 본다 — 호출이
  200 을 냈다는 것은 증거가 아니다(「누른 뒤를 본 것만 초록」).
★ 시험이 전이표를 **손으로 적지 않는다.** 기대값은 언제나 서버가 방금 말한 것과
  견주고, 표가 자라는 날 이 파일이 거짓 빨강을 내지 않게 한다.
"""
from __future__ import annotations

from django.test import TestCase

from tests.test_dsm_app import DsmFixture

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "apps.dsm.queue_signals.queue_field_signals · apps.dsm.services.response_state · "
    "apps.dsm.services.advance_response · kernels.k1_event.response_flow — "
    "화면이 실제로 부르는 그 함수들이다. 합성 더미를 만들지 않는다"
)

#: 전이표의 **끝 칸 이름**만 빌려 온다. 순서는 빌리지 않는다 — 순서를 시험이 들면
#: 그것이 두 번째 전이표가 된다.
CLOSED = "closed"


class QueueCardAllowedNextTest(DsmFixture):
    """①~③ — 큐 카드가 단추를 그릴 때 보는 값."""

    def test_the_card_sees_the_same_table_the_detail_screen_sees(self) -> None:
        """① **표는 하나다.** 큐 카드의 `allowed_next` = 상세의 `allowed_next`.

        갈리면 같은 사건에 대해 큐 화면과 상세 화면이 **다른 단추**를 그린다.
        그때 사람은 「큐에서는 되는데 상세에서는 안 된다」를 겪고, 그 둘 중
        어느 쪽이 참인지 화면만 보고는 알 수 없다.
        """
        from apps.dsm import queue_signals, services

        eid = self._event(self.stream_a)

        from_detail = services.response_state(scope=self.scope_a, event_id=eid)
        out = queue_signals.queue_field_signals(
            scope=self.scope_a, event_ids=[eid])
        from_card = out["signals"][0]

        self.assertEqual(
            from_detail["allowed_next"], from_card["allowed_next"],
            "큐 카드와 상세가 서로 다른 전이표를 봅니다 — 화면 둘이 다른 단추를 "
            "그리게 됩니다 (D-399).")
        self.assertEqual(
            from_detail["response_state"], from_card["response_state"])
        self.assertTrue(
            from_card["allowed_next"],
            "미처리 사건인데 갈 곳이 하나도 없습니다 — 그러면 큐 카드는 단추를 "
            "한 개도 못 그리고, 1클릭 판정이 **분모 0인 초록**이 됩니다.")

    def test_a_closed_event_still_offers_the_rollback_and_that_one_is_not_one_click(
            self) -> None:
        """② ★★ **여기서 1차판이 틀렸다** — 시험이 화면의 거짓 초록을 잡았다.

        이 시험의 1차판은 「종결된 사건은 `allowed_next` 가 **빈 목록**이다」를 적고
        빨개졌다. 실제는 다르다 — `closed` 에서도 **되돌림**(`closed → in_progress`)이
        `allowed_next` 에 **들어 있다**(`kernels/k1_event/response_flow.py:100·121`).

        그리고 그 칸은 **그냥 눌러서는 안 열린다**:
          · 사유가 없으면 `ResponseTransitionNeedsReason` (**400**)
          · 관제요원 계정이면 `ResponseTransitionNeedsManager` (**403** · 팀장만)

        즉 **`allowed_next` 를 그대로 단추로 그리면, 그중 하나는 누르면 반드시
        실패하는 단추다.** 큐 카드가 이 값만 보고 「1클릭」을 그리면 그 한 칸은
        **1클릭이 아니다** — 그것이 이 시험이 잡은 것이고, 화면(`FocusQueue.tsx`)은
        그래서 거절의 **상태코드에 따라 다른 일**을 한다(400 이면 사유 칸을 열고
        같은 칸으로 다시 · 403 이면 「팀장이 해야 한다」를 적는다).

        ★ 시험이 전이표를 손으로 적지 않는다 — 걸어가는 길도, 끝의 이름도 서버에게
          물어서 정한다.
        """
        from apps.dsm import queue_signals, services

        eid = self._event(self.stream_a)

        #: 전이표를 손으로 적지 않는다 — **앞으로만** 걸어간다(되돌림은 안 밟는다).
        seen = {services.response_state(
            scope=self.scope_a, event_id=eid)["response_state"]}
        for _ in range(8):
            allowed = services.response_state(
                scope=self.scope_a, event_id=eid)["allowed_next"]
            forward = [s for s in allowed if s not in seen]
            if not forward:
                break
            services.advance_response(
                scope=self.scope_a, event_id=eid, to_state=forward[0])
            seen.add(forward[0])

        row = queue_signals.queue_field_signals(
            scope=self.scope_a, event_ids=[eid])["signals"][0]

        self.assertEqual(CLOSED, row["response_state"])
        self.assertTrue(row["closed"])
        self.assertTrue(
            row["allowed_next"],
            "종결된 사건의 갈 곳이 빈 목록이 되었습니다 — 되돌림이 사라졌다면 "
            "화면의 400/403 처리가 **분모 0**이 됩니다. 표가 바뀐 것이니 화면도 "
            "같이 읽으십시오.")

        #: ★ 그 칸은 **사유 없이는 안 열린다** — 큐 카드의 「1클릭」이 여기서는 거짓이다.
        rollback = row["allowed_next"][0]
        with self.assertRaises(services.ResponseTransitionError) as caught:
            services.advance_response(
                scope=self.scope_a, event_id=eid, to_state=rollback)
        self.assertIn(
            type(caught.exception).__name__,
            ("ResponseTransitionNeedsReason", "ResponseTransitionNeedsManager"),
            "되돌림이 사유·권한 없이 그냥 열렸습니다 — 그러면 종결이 되돌려진 "
            "기록에 **왜** 가 없습니다.")

        #: **재조회로 확인한다** — 거절당했으면 값이 그대로여야 한다.
        self.assertEqual(
            CLOSED,
            services.response_state(
                scope=self.scope_a, event_id=eid)["response_state"])

    def test_an_unreadable_event_gives_no_row_at_all_not_an_empty_list(self) -> None:
        """③ **「빈 목록」과 「줄이 없다」는 다른 사실이다.**

        화면은 이 둘을 다르게 적는다 — 빈 목록이면 「더 갈 곳이 없습니다」이고,
        줄이 없으면 **「서버가 아직 말하지 않았습니다」**다. 뒤엣것을 앞엣것으로
        적으면 화면이 **모르는 것을 안다고** 말하는 것이다.
        """
        from apps.dsm import queue_signals

        mine = self._event(self.stream_a)
        theirs = self._event(self.stream_b)

        out = queue_signals.queue_field_signals(
            scope=self.scope_a, event_ids=[mine, theirs, 99_000_111])

        got = {row["event_id"] for row in out["signals"]}
        self.assertEqual({mine}, got,
                         "남의/없는 사건이 목록에 들어왔습니다 — 읽기 IDOR 입니다.")
        self.assertEqual(3, out["asked"])
        self.assertEqual(1, out["read"])
        #: 물은 수와 읽은 수가 다르다 — 화면은 그 차이로 「못 들은 카드」를 안다.
        self.assertNotEqual(
            out["asked"], out["read"],
            "물은 수와 읽은 수가 같으면 화면은 「못 들은 카드」를 알 방법이 없습니다.")


class HiddenBranchesAreReallyForbiddenTest(DsmFixture):
    """④⑤ — 감춘 단추가 **정말로 막힌 길**인가, 열린 단추가 **정말로 열리는가**."""

    def test_a_branch_the_server_did_not_allow_is_rejected_when_pressed(self) -> None:
        """④ 화면이 감추는 것은 **편의**다. 방벽은 서버다.

        큐 카드는 `allowed_next` 에 없는 갈래를 **안 그린다**(회색으로 남기지
        않는다 — 못 누르는 단추는 「곧 될 것」으로 읽힌다). 그러나 감추기는
        관문이 아니다. 감춘 길을 지나쳐 불렀을 때 **서버가 막아야** 감춘 것이
        옳은 감춤이다.
        """
        from apps.dsm import services

        eid = self._event(self.stream_a)
        allowed = services.response_state(
            scope=self.scope_a, event_id=eid)["allowed_next"]

        #: 서버가 **말하지 않은** 칸을 고른다. 전이표를 손으로 적지 않기 위해
        #: 「지금 값도 아니고 허용 목록에도 없는 칸」을 실제 값들 중에서 찾는다.
        state = services.response_state(scope=self.scope_a, event_id=eid)
        forbidden = None
        for candidate in ("occurred", "acknowledged", "in_progress", CLOSED):
            if candidate not in allowed and candidate != state["response_state"]:
                forbidden = candidate
                break

        self.assertIsNotNone(
            forbidden,
            "지금 상태에서 막힌 칸이 하나도 없습니다 — 그러면 ④ 는 **분모 0**이라 "
            "이 시험이 아무것도 재지 않습니다.")

        with self.assertRaises(services.ResponseTransitionError):
            services.advance_response(
                scope=self.scope_a, event_id=eid, to_state=forbidden)

        #: **재조회로 확인한다** — 거절당했다면 값이 그대로여야 한다.
        after = services.response_state(scope=self.scope_a, event_id=eid)
        self.assertEqual(state["response_state"], after["response_state"],
                         "거절당했는데 값이 움직였습니다.")

    def test_a_branch_the_server_allowed_really_opens(self) -> None:
        """⑤ 반대 방향 — **열린 것을 감추고 있지 않다.**

        ④ 만 있으면 「전부 감추면 언제나 초록」이 된다. 서버가 허락한 칸이
        실제로 열린다는 것을 함께 재야 「감춤」이 게으름이 아니다.
        """
        from apps.dsm import queue_signals, services

        eid = self._event(self.stream_a)
        allowed = services.response_state(
            scope=self.scope_a, event_id=eid)["allowed_next"]
        self.assertTrue(allowed, "허락된 칸이 0개면 ⑤ 는 분모가 0입니다.")

        target = allowed[0]
        services.advance_response(
            scope=self.scope_a, event_id=eid, to_state=target)

        #: 큐 카드가 보는 바로 그 문으로 **다시 읽는다.**
        row = queue_signals.queue_field_signals(
            scope=self.scope_a, event_ids=[eid])["signals"][0]
        self.assertEqual(
            target, row["response_state"],
            "허락된 칸으로 옮겼는데 큐 카드가 보는 값이 안 따라왔습니다 — "
            "카드의 상태 칸이 거짓말을 하게 됩니다.")


class RouteIsNotNewTest(TestCase):
    """새 라우트를 **만들지 않았다**는 것을 코드로 못박는다.

    큐 카드 1클릭은 기존 문 셋만 쓴다:
      · `GET  /api/dsm/queue/field-signals`            (턴 S · U1 · 읽기)
      · `POST /api/dsm/events/{id}/review-and-acknowledge` (턴 Q · U1)
      · `POST /api/dsm/events/{id}/response`           (D-399)
      · `POST /api/dsm/events/{id}/review`             (오탐 · 재사용)

    이 시험이 하는 일은 **그 넷이 이미 선언돼 있다**를 확인하는 것이다. 새로
    생긴 문이 있으면 조율자의 쓰기 면 대장(WS-27)에 표 밖 1건으로 세어야 한다.
    """

    #: ★ 화면이 실제로 부르는 문자열과 **같은 자리**를 본다.
    EXPECTED = (
        "/queue/field-signals",
        "/events/{int:event_id}/review-and-acknowledge",
    )

    def test_the_u1_surface_already_declares_what_the_card_presses(self) -> None:
        import inspect

        from apps.dsm import api_u1

        source = inspect.getsource(api_u1)
        for path in self.EXPECTED:
            self.assertIn(
                path, source,
                f"{path} 가 U1 진입면에 없습니다 — 큐 카드가 **새 문**을 부르고 "
                f"있다는 뜻이고, 그러면 WS-27 은 표 밖 1건입니다.")

    def test_the_response_and_review_doors_are_the_shared_ones(self) -> None:
        import inspect

        from apps.dsm import api

        source = inspect.getsource(api)
        for path in ("/events/{int:event_id}/response",
                     "/events/{int:event_id}/review"):
            self.assertIn(
                path, source,
                f"{path} 가 공용 진입면에 없습니다 — 큐 카드가 부를 문이 사라졌습니다.")
