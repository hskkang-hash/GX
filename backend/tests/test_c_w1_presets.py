# -*- coding: utf-8 -*-
"""W1 관제 프리셋 넷 — **서버가 거르는가** (차선 C · 2026-09-23).

이 파일이 묻는 것은 하나다
--------------------------
    **화면이 페이지를 받아 자기가 거른 것이 아니라, 서버가 걸러서 준 것인가.**

왜 그것만 묻나. 화면이 거르면 두 가지가 동시에 깨진다:

    ① **페이지 밖 이벤트는 없는 것이 된다.** 상한 50건을 받아 화면이 미처리를
       세면, 51번째 미처리는 화면에게 존재하지 않는다. 그리고 그 사실이
       화면에 안 나온다 — 「미처리 3건」이라고 적히고, 그것이 거짓말이다.
    ② **격리.** 화면이 거르기 전의 목록은 이미 브라우저에 와 있다.

그래서 이 시험은 **상한보다 많은 이벤트를 심고**, 상한을 넘겨 걸러지는지를 본다.
상한 안에서만 재면 두 구현(서버 필터 · 화면 필터)이 **같은 답을 낸다** — 그러면
이 시험은 아무것도 재지 않는다.

무엇을 다시 묻지 않나
---------------------
전이 규칙(D-399)·오탐률 계산(K6)은 커널 시험이 이미 잰다. 여기서 다시 물으면
같은 사실을 두 벌로 재고, 커널이 바뀔 때 두 곳에서 깨진다 (test_dsm_app 규약).
"""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from tests.test_dsm_app import DsmFixture

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "apps.dsm.api.DsmAPI.events / events_summary · apps.dsm.services.recent_events · "
    "kernels.k1_event.query_events · kernels.k6_feedback.false_positive_rate — "
    "저장소의 실제 라우트와 실제 커널. 합성 더미를 부르지 않는다"
)


class W1PresetServerFilterTest(DsmFixture):
    """프리셋 넷이 **서버 질의**로 걸러지는가."""

    def test_unhandled_preset_is_filtered_by_the_server_beyond_the_page(self) -> None:
        """「미처리」 — **상한 밖에서도 걸러지는가.**

        ★ 이 시험의 요점은 `limit` 이다. 심는 수를 상한보다 크게 두면, 화면이
          거르는 구현은 여기서 **반드시 다른 답**을 낸다: 상한만큼 받아서 세면
          미처리가 상한 안에 몇 개 들어왔는지에 따라 답이 흔들린다.
        """
        from apps.dsm import services

        # 미처리 3 · 접수 확인 5. 상한을 4로 두면 「받아서 세기」로는 절대 3이 안 나온다.
        pending = [self._event(self.stream_a) for _ in range(3)]
        for _ in range(5):
            moved = self._event(self.stream_a)
            services.advance_response(scope=self.scope_a, event_id=moved,
                                      to_state="acknowledged")

        rows = services.recent_events(scope=self.scope_a,
                                      response_state="occurred", limit=4)
        self.assertEqual(
            sorted(pending), sorted(r.event_id for r in rows),
            "서버가 `response_state=occurred` 로 걸러 주지 않았습니다 — 상한 4건을 "
            "받아 화면이 세면 이 목록에 접수 확인된 건이 섞입니다(온보딩 U2 #2).")
        for row in rows:
            self.assertEqual("occurred", row.response_state)

    def test_the_list_carries_the_response_axis(self) -> None:
        """목록 응답에 `response_state` 가 **실려 나가는가**.

        09-21 실측: `EVENT_RESPONSE_KEYS` 에 이 칸이 없어 U2 가 눈짐작을 했다.
        칸이 다시 빠지면 화면은 오류 없이 「대응」 열을 빈칸으로 그린다 —
        **빠진 칸은 보이지 않는다**(D-274).
        """
        from apps.dsm import services

        self._event(self.stream_a)
        rows = services.recent_events(scope=self.scope_a, limit=10)
        self.assertTrue(rows, "이벤트를 심었는데 목록이 비었습니다 — 픽스처 고장입니다.")
        for row in rows:
            self.assertTrue(
                getattr(row, "response_state", None),
                "목록 행에 `response_state` 가 없습니다. 이 칸이 없으면 W1 「미처리」 "
                "프리셋을 서버가 걸러 줄 수 없습니다.")

    def test_recent_window_is_closed_on_both_ends(self) -> None:
        """「지난 12시간」 — **창의 두 끝**을 서버가 받는가.

        `since` 만 있으면 그것은 「지난 12시간」이 아니라 「12시간 전부터 미래까지」다.
        미래 시각을 가진 이벤트가 하나라도 생기면(시계 어긋남·수동 입력) 그 차이가
        드러나고, 드러나기 전까지는 두 구현이 같은 답을 낸다 — 그래서 여기서 잰다.
        """
        from apps.dsm import services

        now = timezone.now()
        inside = self._event(self.stream_a, when=now - timedelta(hours=2))
        self._event(self.stream_a, when=now - timedelta(hours=30))     # 창 이전
        self._event(self.stream_a, when=now + timedelta(hours=2))      # 창 이후(미래)

        rows = services.recent_events(
            scope=self.scope_a, since=now - timedelta(hours=12), until=now, limit=50)
        self.assertEqual(
            [inside], [r.event_id for r in rows],
            "`until` 이 걸리지 않았습니다 — 창이 닫히지 않으면 「지난 12시간」이 "
            "미래를 포함합니다.")

    def test_mine_preset_narrows_to_the_reviewer(self) -> None:
        """「내 담당」 — **판정자로** 좁혀지는가.

        ⚠ 「내가 판정한 것」이지 「내가 대응한 것」이 아니다. 대응 전이의 행위자는
          행이 아니라 감사에 있고(D-399), 둘을 한 칸으로 읽으면 두 축이 다시 섞인다.
        """
        from apps.dsm import services

        mine = self._event(self.stream_a)
        self._event(self.stream_a)            # 아무도 판정하지 않은 것
        services.review_event(scope=self.scope_a, event_id=mine, verdict="confirmed")

        rows = services.recent_events(
            scope=self.scope_a, reviewed_by_id=self.user_a.pk, limit=50)
        self.assertEqual([mine], [r.event_id for r in rows])

        # 남의 사번으로 좁히면 **내 테넌트 안에서도** 아무것도 안 나온다.
        other = services.recent_events(
            scope=self.scope_a, reviewed_by_id=self.user_b.pk, limit=50)
        self.assertEqual([], [r.event_id for r in other])

    def test_the_preset_filters_do_not_cross_tenants(self) -> None:
        """★ 새 필터가 **격리를 우회하지 않는가.**

        필터를 더할 때 가장 쉬운 사고가 이것이다: 좁히는 조건을 하나 더 걸면서
        스코프 좁히기보다 **먼저** 걸면, 조건에 맞는 남의 행이 통과한다.
        `reviewed_by_id` 는 사람의 사번이라 특히 위험하다 — 남의 테넌트에도
        같은 사번이 존재할 수 있다.
        """
        from apps.dsm import services

        theirs = self._event(self.stream_b)
        services.review_event(scope=self.scope_b, event_id=theirs, verdict="rejected")

        rows = services.recent_events(
            scope=self.scope_a, reviewed_by_id=self.user_b.pk, limit=50)
        self.assertNotIn(theirs, [r.event_id for r in rows],
                         "남의 테넌트 이벤트가 판정자 필터를 타고 넘어왔습니다.")

        rows = services.recent_events(scope=self.scope_a,
                                      response_state="occurred", limit=50)
        self.assertNotIn(theirs, [r.event_id for r in rows])


class W1SummaryLineTest(DsmFixture):
    """요약 한 줄 — **분모를 함께 내는가**, 그리고 **App 이 세지 않는가.**"""

    def test_the_summary_reports_numerator_and_denominator(self) -> None:
        """「오탐 4건」만 내면 그것이 12건 중 4인지 400건 중 4인지 모른다 (D-271 ③)."""
        from kernels.k6_feedback import false_positive_rate

        from apps.dsm import services

        now = timezone.now()
        rejected = self._event(self.stream_a, when=now - timedelta(minutes=10))
        confirmed = self._event(self.stream_a, when=now - timedelta(minutes=11))
        self._event(self.stream_a, when=now - timedelta(minutes=12))   # 미판정
        services.review_event(scope=self.scope_a, event_id=rejected, verdict="rejected")
        services.review_event(scope=self.scope_a, event_id=confirmed, verdict="confirmed")

        window = false_positive_rate(scope=self.scope_a,
                                     since=now - timedelta(hours=12), until=now).total
        self.assertEqual(1, window.rejected)
        self.assertEqual(2, window.reviewed)
        self.assertEqual(1, window.unreviewed,
                         "미판정이 모수에서 빠졌습니다 — 모수를 숨기면 오탐률이 "
                         "판정을 안 할수록 좋아 보입니다.")

    def test_rate_is_none_not_zero_when_nothing_was_reviewed(self) -> None:
        """★ 분모 0 이면 **`None` 이다 — 0.0 이 아니다.**

        0.0 으로 내면 「판정을 안 하기만 해도 오탐률이 좋아지는」 지표가 된다.
        화면이 그 둘을 가를 수 있어야 하므로 여기서 못박는다.
        """
        from kernels.k6_feedback import false_positive_rate

        now = timezone.now()
        self._event(self.stream_a, when=now - timedelta(minutes=5))

        rate = false_positive_rate(scope=self.scope_a,
                                   since=now - timedelta(hours=12), until=now)
        self.assertIsNone(rate.total.rate)
        self.assertFalse(rate.is_measurable)

    def test_the_app_does_not_compute_the_rate_itself(self) -> None:
        """★ **App 이 나눗셈을 하지 않는가.**

        집계 경로를 하나로 유지하는 것 자체가 DA-04 K6 의 요구다. App 이 한 줄이라도
        직접 나누면 F-14(월간 리포트)와 W1(요약 한 줄)이 다른 수를 내고, 갈린 수는
        고객 앞에서 못 쓴다.
        """
        import inspect

        from apps.dsm import api

        src = inspect.getsource(api.DsmAPI.events_summary)
        for smell in ("rejected /", "/ reviewed", "* 100"):
            self.assertNotIn(
                smell, src,
                f"요약 라우트가 오탐률을 직접 계산합니다({smell}) — 그 수는 "
                f"K6 `false_positive_rate` 가 내야 합니다.")


class W1RouteReachTest(DsmFixture):
    """★ **함수가 아니라 문이 사는가** (착시 ⑨).

    D-410 이 남긴 자리: `settings/{domain}` 이 쓰기 라우트 넷을 삼켰고, 단위 시험은
    서비스 함수를 불러 초록이었다. 새 라우트를 만들 때마다 **URL 로** 한 번 물어야
    한다 — 여기서 묻는 것은 「그 주소가 이 핸들러로 오는가」다.
    """

    def test_the_summary_route_is_registered_and_not_swallowed(self) -> None:
        """`/api/dsm/events/summary` 가 `/events/{int:event_id}` 에 안 먹히는가."""
        from django.urls import resolve

        from apps.dsm.api import DsmAPI

        match = resolve("/api/dsm/events/summary")
        view = getattr(match.func, "__self__", None) or match.func
        # ninja 의 PathView 는 등록된 operation 을 들고 있다. 이름으로 확인한다.
        operations = getattr(getattr(match.func, "__self__", None), "operations", None)
        names = []
        if operations:
            for op in operations:
                names.append(op.view_func.__name__)
        self.assertIn(
            "events_summary", names or [getattr(view, "__name__", "")],
            f"`/api/dsm/events/summary` 가 다른 핸들러로 갑니다 — 라우트 삼킴입니다. "
            f"닿은 것: {names or view}. (DsmAPI={DsmAPI.__name__})")
