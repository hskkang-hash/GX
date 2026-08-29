# -*- coding: utf-8 -*-
"""D-293 강제 도구 — **같은 코호트는 두 시점에 같은 값이어야 한다.**

D-293 이 금지한 것 한 줄
------------------------
    종료된 판정을 지우면 오탐률이 시간이 갈수록 **저절로 좋아진다.**
    개선된 것이 아니라 나쁜 데이터가 사라진 것이다 — 착시의 새 얼굴이다.

그래서 판정은 보존하고(물리 삭제 금지), 오탐률은 **발생 코호트 기준**으로 센다:
*이번 달 발생분의 오탐률은 다음 달에도 같은 값이어야 한다.*

왜 "회귀 시험"인가 — 한 시점의 값은 아무것도 증명하지 않는다
-------------------------------------------------------------
"오탐률 0.33" 은 옳을 수도 있고, 분모가 조용히 깎인 뒤의 수일 수도 있다.
한 번 재서는 그 둘을 구별할 수 없다. **두 번 재서 비교해야** 구별된다 —
그 사이에 시간이 흐르고(이벤트가 종료되고), 값이 움직이면 그것이 자가개선이다.

이 파일은 그래서 늘 **두 번 잰다**: 코호트를 정하고 → 값을 적고 → 세상을 늙히고
(종료·재조회·새 이벤트 유입) → 다시 재서 **첫 값과 대조**한다.

무엇을 못 잡나 — 경계를 적는다 (D-277)
--------------------------------------
· 이 시험은 **소프트 삭제·아카이브**로 행이 사라지는 경우를 직접 만들지 않는다.
  `_base_manager` 로 세는 K6 은 soft-delete 된 행도 본다 — 그 성질이 바뀌면
  `test_soft_deleted_events_stay_in_the_cohort` 가 먼저 멈춘다.
· 시간 이동은 **논리 시계**다. 실시간으로 한 달을 기다리지 않는다 (D-291 규약 ⑤).
"""
from __future__ import annotations

from datetime import timedelta

from django.apps import apps
from django.utils import timezone

from tests.test_k6_feedback_kernel import K6Fixture

#: ★ D-289 — 양성 대조의 표본은 저장소 실물에서 뽑는다.
REAL_SAMPLE = (
    "kernels.k6_feedback.false_positive_rate · kernels.k1_event.close_event — "
    "저장소의 실제 커널 공개 면. 합성 더미를 부르지 않는다"
)


class CohortStabilityTest(K6Fixture):
    """★ 코호트 회귀 — **두 시점의 값이 같은가.** 다르면 exit 1."""

    def _cohort(self, *, since, until, **kw):
        from kernels.k6_feedback import false_positive_rate

        window = false_positive_rate(scope=self.scope_a, since=since, until=until,
                                     **kw).total
        return (window.reviewed, window.rejected, window.rate)

    def test_closing_events_does_not_move_the_cohort(self) -> None:
        """세상을 늙힌다 — 코호트의 이벤트를 **전부 종료**하고 다시 잰다.

        이것이 실제로 일어나는 일이다: 지난달 이벤트는 이번 달이면 대개 닫혀 있다.
        닫힘이 값을 움직이면 지난달 보고서와 이번 달 보고서가 **다른 지난달**을 말한다.
        """
        from kernels.k1_event import close_event

        since = timezone.now() - timedelta(days=2)
        until = timezone.now() + timedelta(seconds=1)

        ids = [self._event(self.stream_a) for _ in range(4)]
        for event_id, verdict in zip(ids, ("rejected", "rejected", "confirmed",
                                           "confirmed")):
            self._judge(event_id, verdict)

        first = self._cohort(since=since, until=until)
        self.assertEqual((4, 2, 0.5), first,
                         "픽스처가 의도한 코호트를 만들지 못했습니다 — 이 시험의 전제가 깨졌습니다.")

        for event_id in ids:
            close_event(event_id, scope=self.scope_a)

        second = self._cohort(since=since, until=until)
        self.assertEqual(
            first, second,
            f"같은 코호트가 두 시점에 다른 값을 냈습니다: {first} → {second}. "
            "종료가 판정을 지우고 있습니다 — 오탐률이 시간이 갈수록 저절로 좋아지는 "
            "구조입니다 (D-293).")

    def test_later_events_do_not_change_an_earlier_cohort(self) -> None:
        """★ 코호트의 정의 자체 — **발생 시점**으로 가른다.

        나중에 들어온 이벤트가 지난달 값을 바꾸면 그것은 코호트가 아니라 누적이고,
        누적은 "지난달 오탐률" 이라는 문장을 만들 수 없다.
        """
        now = timezone.now()
        old_since = now - timedelta(days=40)
        old_until = now - timedelta(days=20)

        # 시각을 벌린다 — 같은 스트림·같은 타입이 10초 창 안에 겹치면 커널이 접고,
        # 접히면 두 건이 아니라 한 건이 된다 (DEDUP_WINDOW).
        for offset, verdict in enumerate(("rejected", "confirmed")):
            event_id = self._event(
                self.stream_a, when=now - timedelta(days=30, minutes=offset))
            self._judge(event_id, verdict)

        first = self._cohort(since=old_since, until=old_until)
        self.assertEqual((2, 1, 0.5), first)

        # 오늘 새 이벤트가 다섯 건 들어오고 전부 기각된다 — 오늘 오탐률은 1.0 이다.
        for offset in range(5):
            self._judge(
                self._event(self.stream_a, when=now - timedelta(minutes=offset)),
                "rejected")

        self.assertEqual(
            first, self._cohort(since=old_since, until=old_until),
            "새 이벤트가 지난 코호트의 값을 바꿨습니다 — 발생 시점이 아니라 판정 시점으로 "
            "세고 있습니다.")

    def test_soft_deleted_events_stay_in_the_cohort(self) -> None:
        """★ **물리 삭제 금지**의 시험판 — 지워도 분모가 줄지 않는가.

        D-293 은 종료 판정의 **보존**을 요구했다. 이 저장소의 삭제는 soft-delete 이고,
        K6 은 `_base_manager` 로 세므로 soft-delete 된 행도 분모에 남는다.
        그 성질이 바뀌면 여기서 멈춘다 — "지우면 지표가 좋아지는" 경로가 다시 열리기 때문이다.
        """
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        since = timezone.now() - timedelta(days=2)
        until = timezone.now() + timedelta(seconds=1)

        ids = [self._event(self.stream_a) for _ in range(2)]
        self._judge(ids[0], "rejected")
        self._judge(ids[1], "confirmed")
        first = self._cohort(since=since, until=until)

        row = Event._base_manager.get(pk=ids[0])
        row.delete()          # dj-core 의 soft-delete

        self.assertEqual(
            first, self._cohort(since=since, until=until),
            "삭제가 분모를 깎았습니다 — 나쁜 데이터를 지우면 지표가 좋아지는 구조입니다 "
            "(D-293: 물리 삭제 금지 · 종료 판정도 보존).")

    def test_positive_control_the_regression_can_actually_fail(self) -> None:
        """★ 양성 대조 (D-277 · D-289) — **재는 기계가 작동하는가.**

        위 세 시험은 전부 "값이 같다"를 단언한다. 값이 언제나 같은 술어라면
        그 초록은 아무것도 재지 않은 것이다. 그래서 여기서는 **판정을 실제로 지워**
        값이 움직이는지 본다. 움직이지 않으면 이 파일 전체가 눈이 먼 것이다.
        """
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        since = timezone.now() - timedelta(days=2)
        until = timezone.now() + timedelta(seconds=1)

        event_id = self._event(self.stream_a)
        self._judge(event_id, "rejected")
        before = self._cohort(since=since, until=until)
        self.assertEqual((1, 1, 1.0), before)

        # 이것이 D-293 이 금지한 동작이다 — 커널 밖에서 손으로 재현한다.
        Event._base_manager.filter(pk=event_id).update(verdict=None)

        self.assertNotEqual(
            before, self._cohort(since=since, until=until),
            "판정을 지웠는데 코호트 값이 그대로입니다 — 이 회귀 시험은 아무것도 "
            "재고 있지 않습니다 (착시 ④).")


class CohortRegressionEnvironmentTest(K6Fixture):
    """규약 ⑤(환경) — 세는 칸이 **DB 에 실재하는가** (D-282 ②눈).

    `--nomigrations` 로 도는 빠른 경로는 모델 선언만으로 표를 만든다. `verdict` 열이
    마이그레이션에 없어도 그 경로는 초록이고, 실 DB 에서만 죽는다.
    """

    def test_verdict_column_exists_in_the_database(self) -> None:
        from django.db import connection

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        with connection.cursor() as cursor:
            columns = {c.name for c in connection.introspection.get_table_description(
                cursor, Event._meta.db_table)}
        self.assertIn(
            "verdict", columns,
            "DetectionEvent 에 verdict 열이 없습니다 — 마이그레이션 0018 이 빠졌습니다. "
            "모델 선언만으로 초록이 되는 경로가 있으니 이 시험이 그 자리를 지킵니다.")
