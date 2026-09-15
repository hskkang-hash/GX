# -*- coding: utf-8 -*-
"""U24 — `stats.py` + `/api/dsm/stats/*` 세 라우트 (UX-35·UX-36·UX-39 · WO-01 §4.2).

이 파일이 잰다 — 여섯
----------------------
  ① 익명 401
  ② 읽기 전용 역할(`view_only_-*`)도 **읽기는 200**
  ③ 다른 테넌트 행 0 — 격리
  ④ AC-5 「합계 = 목록 수」 — `/stats/summary` 의 `total` == `/events` 목록 수
  ⑤ AC-4 「요원 ≥ 2행」 — `/stats/by-reviewer` 가 두 요원을 가르고, 각 행의 수가
    커널 조회(`services.recent_events(reviewed_by_id=...)`)와 일치
  ⑥ 오탐률 분모 0 — `ZeroDivisionError` 없이 `false_positive_rate: null`

무엇을 다시 묻지 않나
---------------------
오탐률 계산(K6) · 판정 전이(K1) 은 각자의 커널 시험이 이미 잰다(`test_k6_feedback_kernel.py`
· `test_k1_event_kernel.py`). 여기서 다시 물으면 같은 사실을 두 벌로 재고, 커널이 바뀔
때 두 곳에서 깨진다(`test_dsm_app.py` 규약과 같은 이유) — 이 파일은 **App 층이 그 결과를
잃지 않고 옮기는가** 만 묻는다.

캐시 처리: 시험마다 `cache.clear()` 로 비우고 시작한다(P-119 시험과 같은 이유) —
캐시 안쪽에서 답이 나오면 위 ①~⑥이 캐시를 재는 것이 되고, 대상을 안 재게 된다
(QA-05 · `guardianx-response-cache-masks-failures` 메모와 같은 함정).
"""
from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

STATS_SUMMARY = "/api/dsm/stats/summary"
STATS_BY_REVIEWER = "/api/dsm/stats/by-reviewer"
STATS_FALSE_POSITIVE = "/api/dsm/stats/false-positive"
ALL_STATS_ROUTES = (STATS_SUMMARY, STATS_BY_REVIEWER, STATS_FALSE_POSITIVE)

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "apps.dsm.api_u24.DsmU24API / apps.dsm.stats · apps.dsm.services.recent_events · "
    "kernels.k6_feedback.false_positive_rate — 저장소의 실제 라우트와 실제 커널. "
    "합성 더미를 부르지 않는다"
)


class StatsFixture(DsmFixture):
    """`DsmFixture`(tenant A/B · 스트림 · 이벤트 생성기)에 **요원 둘째**(tenant A)를 더한다.

    AC-4 「요원 ≥ 2행」을 재려면 **같은 테넌트** 안에 판정자가 둘 있어야 한다 —
    `DsmFixture` 는 테넌트마다 한 사람(`user_a`/`user_b`)뿐이라 그대로는 못 잰다.
    """

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        super().setUpTestData()

        from common.tenant_scope import TenantScope

        cls.role_a2 = cls._own(cls._role("dsm_watch_a2"), cls.group_a)
        cls.user_a2 = cls._user("dsm_user_a2", cls.group_a, cls.role_a2)
        cls.scope_a2 = TenantScope.of(cls.user_a2)

    def setUp(self) -> None:
        super().setUp()
        cache.clear()  # 캐시 60초 — 시험끼리 섞이지 않게 비우고 시작한다

    def _judge(self, event_id: int, verdict: str, *, scope):
        from kernels.k6_feedback import record_feedback

        return record_feedback(event_id, verdict=verdict, reason="u24-stats-test",
                               scope=scope)


# ═══════════════════════════════════════════════════════════════════════════
# ① 익명 401 · ② 읽기 전용 역할도 읽기는 200
# ═══════════════════════════════════════════════════════════════════════════
class AuthGateTest(StatsFixture):
    def test_anonymous_gets_401_on_all_three_routes(self) -> None:
        for path in ALL_STATS_ROUTES:
            with self.subTest(path=path):
                resp = self.client.get(path)
                self.assertEqual(401, resp.status_code, resp.content)

    def test_read_only_role_can_still_read(self) -> None:
        """`view_only_-*` 역할 **뿐인** 계정도 읽기는 막히지 않는다 (P-119 규칙 3)."""
        view_only_role = self._own(self._role("view_only_-_u24stats"), self.group_a)
        viewer = self._user("dsm_view_only_u24", self.group_a, view_only_role)
        for path in ALL_STATS_ROUTES:
            with self.subTest(path=path):
                resp = self.client.get(path, **_bearer(viewer))
                self.assertEqual(200, resp.status_code, resp.content)


# ═══════════════════════════════════════════════════════════════════════════
# ③ 다른 테넌트 행 0 — 격리
# ═══════════════════════════════════════════════════════════════════════════
class TenantIsolationTest(StatsFixture):
    def test_other_tenants_events_do_not_leak_into_any_of_the_three(self) -> None:
        since = timezone.now() - timedelta(days=1)

        ids_a = [self._event(self.stream_a) for _ in range(2)]
        ids_b = [self._event(self.stream_b) for _ in range(3)]
        for eid in ids_b:
            self._judge(eid, "rejected", scope=self.scope_b)

        params = {"since": since.isoformat()}

        summary = self.client.get(STATS_SUMMARY, params, **_bearer(self.user_a))
        self.assertEqual(200, summary.status_code, summary.content)
        self.assertEqual(2, summary.json()["total"],
                         "테넌트 B 의 이벤트 3건이 테넌트 A 의 요약에 섞였습니다")

        fp = self.client.get(STATS_FALSE_POSITIVE, params, **_bearer(self.user_a))
        self.assertEqual(200, fp.status_code, fp.content)
        fp_body = fp.json()
        self.assertEqual(0, fp_body["reviewed"],
                         "테넌트 A 는 아무도 판정하지 않았는데 분모가 0 이 아닙니다 — "
                         "테넌트 B 의 판정(3건 기각)이 섞였습니다")
        self.assertEqual(0, fp_body["false_positive"])

        by_rev = self.client.get(STATS_BY_REVIEWER, params, **_bearer(self.user_a))
        self.assertEqual(200, by_rev.status_code, by_rev.content)
        reviewer_ids = {r["reviewer_id"] for r in by_rev.json()["reviewers"]}
        self.assertNotIn(self.user_b.pk, reviewer_ids,
                         "테넌트 B 의 판정자(user_b)가 테넌트 A 의 요원별 표에 나왔습니다")

        # ids_a 는 모두 미판정 — 요원별 표 자체가 비어 있어야 한다.
        self.assertEqual([], by_rev.json()["reviewers"])
        del ids_a  # 참조만 — 판정하지 않은 채로 둔다(대조를 위해 만든 것)


# ═══════════════════════════════════════════════════════════════════════════
# ④ AC-5 「합계 = 목록 수」
# ═══════════════════════════════════════════════════════════════════════════
class SummaryMatchesEventsListTest(StatsFixture):
    def test_summary_total_equals_events_list_count(self) -> None:
        since = timezone.now() - timedelta(days=1)
        for _ in range(5):
            self._event(self.stream_a)

        params = {"since": since.isoformat()}
        events_resp = self.client.get("/api/dsm/events",
                                      {**params, "limit": 100}, **_bearer(self.user_a))
        self.assertEqual(200, events_resp.status_code, events_resp.content)
        events_total = events_resp.json()["total"]

        stats_resp = self.client.get(STATS_SUMMARY, params, **_bearer(self.user_a))
        self.assertEqual(200, stats_resp.status_code, stats_resp.content)
        stats_body = stats_resp.json()

        self.assertEqual(
            events_total, stats_body["total"],
            f"/events 목록 수({events_total})와 /stats/summary 합계"
            f"({stats_body['total']})가 다릅니다 — AC-5 위반")
        self.assertEqual(
            stats_body["total"], sum(stats_body["by_event_type"].values()),
            "유형별 합이 전체와 다릅니다 — 어느 행이 어느 칸에도 안 세어졌습니다")

    def test_by_reviewer_total_reviewed_equals_kernel_count(self) -> None:
        """/events 는 `reviewed_by_id` 를 임의로 질의하지 못하게 막아 두었다(D-… 「나」만
        허용). 그래서 AC-5 의 같은 뜻을 **커널 직접 조회**로 대조한다 — `mine=true` 가
        내부에서 쓰는 바로 그 함수다.
        """
        from apps.dsm import services

        since = timezone.now() - timedelta(days=1)
        ids = [self._event(self.stream_a) for _ in range(3)]
        self._judge(ids[0], "confirmed", scope=self.scope_a)
        self._judge(ids[1], "rejected", scope=self.scope_a)
        # ids[2] 는 미판정으로 남긴다.

        resp = self.client.get(STATS_BY_REVIEWER, {"since": since.isoformat()},
                               **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content)
        by_id = {r["reviewer_id"]: r for r in resp.json()["reviewers"]}

        detail_rows = services.recent_events(scope=self.scope_a, since=since,
                                             reviewed_by_id=self.user_a.pk, limit=100)
        self.assertEqual(
            len(detail_rows), by_id[self.user_a.pk]["reviewed_total"],
            "요원별 표의 판정 건수가 사건 상세(커널 조회)와 다릅니다 — AC-5 위반")


# ═══════════════════════════════════════════════════════════════════════════
# ⑤ AC-4 「요원 ≥ 2행」
# ═══════════════════════════════════════════════════════════════════════════
class ByReviewerTest(StatsFixture):
    def test_two_reviewers_produce_two_rows_with_correct_counts(self) -> None:
        from kernels.k1_event import close_event

        since = timezone.now() - timedelta(days=1)
        ids = [self._event(self.stream_a) for _ in range(4)]
        self._judge(ids[0], "confirmed", scope=self.scope_a)
        self._judge(ids[1], "rejected", scope=self.scope_a)
        self._judge(ids[2], "rejected", scope=self.scope_a)
        self._judge(ids[3], "confirmed", scope=self.scope_a2)
        close_event(ids[0], scope=self.scope_a)  # user_a 의 판정 하나를 종결까지 보낸다

        resp = self.client.get(STATS_BY_REVIEWER, {"since": since.isoformat()},
                               **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content)
        body = resp.json()

        self.assertGreaterEqual(len(body["reviewers"]), 2,
                                "요원 ≥ 2행이어야 합니다(AC-4) — "
                                f"실제 {len(body['reviewers'])}행: {body['reviewers']}")

        by_id = {r["reviewer_id"]: r for r in body["reviewers"]}
        self.assertIn(self.user_a.pk, by_id)
        self.assertIn(self.user_a2.pk, by_id)

        row_a = by_id[self.user_a.pk]
        self.assertEqual(3, row_a["reviewed_total"])
        self.assertEqual(2, row_a["false_positive_total"])
        self.assertEqual(1, row_a["closed_total"])
        self.assertIsNotNone(row_a["avg_response_seconds"])

        row_a2 = by_id[self.user_a2.pk]
        self.assertEqual(1, row_a2["reviewed_total"])
        self.assertEqual(0, row_a2["false_positive_total"])

        self.assertEqual(body["total_reviewed"],
                         sum(r["reviewed_total"] for r in body["reviewers"]))


# ═══════════════════════════════════════════════════════════════════════════
# ⑥ 오탐률 분모 0 — 0 나누기 없이
# ═══════════════════════════════════════════════════════════════════════════
class FalsePositiveDenominatorTest(StatsFixture):
    def test_zero_reviewed_gives_null_rate_not_an_error(self) -> None:
        since = timezone.now() - timedelta(days=1)
        for _ in range(3):
            self._event(self.stream_a)  # 전부 미판정

        resp = self.client.get(STATS_FALSE_POSITIVE, {"since": since.isoformat()},
                               **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content)
        body = resp.json()
        self.assertEqual(0, body["reviewed"])
        self.assertIsNone(body["false_positive_rate"],
                         "분모 0 인데 0.0 이 나왔습니다 — 판정을 미루기만 해도 "
                         "오탐률이 좋아지는 지표가 됩니다(D-290)")
        self.assertFalse(body["measurable"])


# ═══════════════════════════════════════════════════════════════════════════
# 기간 상한 — WO-01 §5 성능(p95 800ms · 배치 테이블 없음 · 가정)
# ═══════════════════════════════════════════════════════════════════════════
class WindowGuardTest(StatsFixture):
    def test_reversed_window_is_400(self) -> None:
        now = timezone.now()
        resp = self.client.get(
            STATS_SUMMARY,
            {"since": now.isoformat(), "until": (now - timedelta(days=1)).isoformat()},
            **_bearer(self.user_a))
        self.assertEqual(400, resp.status_code, resp.content)

    def test_window_over_366_days_is_400(self) -> None:
        since = timezone.now() - timedelta(days=400)
        resp = self.client.get(STATS_BY_REVIEWER, {"since": since.isoformat()},
                               **_bearer(self.user_a))
        self.assertEqual(400, resp.status_code, resp.content)


# ═══════════════════════════════════════════════════════════════════════════
# 캐시 — 60초 · 키에 테넌트가 들어가는가 (WO-01 §5 · 가정)
# ═══════════════════════════════════════════════════════════════════════════
class CacheTest(StatsFixture):
    def test_cache_key_differs_by_tenant(self) -> None:
        from apps.dsm import stats

        key_a = stats._cache_key("summary", self.user_a, since=None, until=None)
        key_b = stats._cache_key("summary", self.user_b, since=None, until=None)
        self.assertNotEqual(key_a, key_b,
                            "테넌트가 다른데 캐시 키가 같습니다 — 캐시가 격리를 "
                            "뚫는 자리가 됩니다")

    def test_second_call_within_ttl_is_served_from_cache(self) -> None:
        """60초 안의 재호출은 **새 이벤트를 반영하지 않는다** — 그것이 캐시가 실제로
        도는 증거다. 반영되면 캐시가 아니라 매번 다시 센 것이다.
        """
        from apps.dsm import stats

        since = timezone.now() - timedelta(days=1)
        self._event(self.stream_a)
        first = stats.stats_summary(scope=self.scope_a, since=since)
        self.assertEqual(1, first["total"])

        self._event(self.stream_a)
        second = stats.stats_summary(scope=self.scope_a, since=since)
        self.assertEqual(first, second,
                         "같은 파라미터의 재호출이 캐시를 안 탔습니다 — 60초 캐시가 "
                         "깨졌거나 파라미터가 캐시 키에 안정적으로 안 실립니다")

        cache.clear()
        third = stats.stats_summary(scope=self.scope_a, since=since)
        self.assertEqual(2, third["total"],
                         "캐시를 비운 뒤에도 새 이벤트가 안 잡힙니다 — 집계 자체가 고장입니다")
