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
from urllib.parse import urlencode

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


# ═══════════════════════════════════════════════════════════════════════════
# ⑦ UX-36 카메라별 오탐률 — 부속서A U2 #10 「내림차순 · 상위 3 강조」 (턴 S)
# ═══════════════════════════════════════════════════════════════════════════
BY_CAMERA = "/api/dsm/stats/false-positive/by-camera"
SIMULATE = "/api/dsm/stats/thresholds/simulate"
CAMERA_THRESHOLD = "/api/dsm/stats/camera-threshold"
CAMERA_THRESHOLD_KEYS = "/api/dsm/stats/camera-thresholds"

#: 표 ①에서 **카메라별로 둘 수 있고 계약이 못박지 않은** 키. 이 시험이 이 키를 쓰는
#: 이유는 그것이 지금 표에 실제로 있는 유일한 그런 키이기 때문이다 — 없는 키를
#: 지어내면 시험이 저장소가 아니라 상상을 잰다(D-289).
CAMERA_KEY = "waterlevel.baseline"


class CameraFixture(StatsFixture):
    """같은 테넌트에 카메라 **셋**. 한 대만으로는 「내림차순」을 잴 수 없다.

    ★ 카메라를 `setUpTestData`(클래스 한 번)에서 만든다 — `setUp`(시험마다)이 아니다.
      [실측] `setUp` 에서 만들었더니 같은 테넌트의 사건을 판정하는 순간
      `DetectionEvent.DoesNotExist` 가 났다: 오탐 판정이 자동 종결 신호를 타고
      다시 사건을 **테넌트로 좁혀** 읽는데, 그 좁히기가 이 시점의 소유 관계를
      못 따라왔다. `DsmFixture` 가 `stream_a`·`stream_b` 를 만드는 자리와 **같은
      자리**에 두면 사라진다 — 픽스처가 저장소의 관례를 벗어난 것이 원인이었지
      제품 결함이 아니다.
    """

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        super().setUpTestData()
        cls.stream_a2 = cls._stream("dsm-stream-A2", cls.group_a)
        cls.stream_a3 = cls._stream("dsm-stream-A3", cls.group_a)

    def setUp(self) -> None:
        super().setUp()
        # ★★ **스레드에 남은 요청을 지운다 — 시험마다.** [실측 · 격리 A/B 8칸]
        #
        #   증상: 이 클래스의 시험 둘이 `_judge(...)` 첫 줄에서
        #   `DetectionEvent.DoesNotExist` 로 죽었다. 같은 한 줄을 격리해서 돌리면
        #   여덟 자리가 **전부 초록**이었다 — 카메라를 더한 것도, 판정 순서도,
        #   사건을 여러 건 만든 것도 범인이 아니었다(가설 셋 기각).
        #
        #   범인은 **앞 시험이 남긴 요청**이다. 한 클래스 안에서 `test_anonymous...`
        #   가 이름순으로 **먼저** 돌며 익명으로 HTTP 를 때리고, 그 요청이 스레드에
        #   남는다. 그 뒤 ORM 의 기본 관리자가 그 남은 요청으로 테넌트를 좁히므로
        #   **뒤따르는 시험에서 행이 통째로 안 보인다.** 오탐 판정은 자동 종결
        #   신호를 타고 사건을 다시 읽으므로 바로 그 자리에서 죽었다.
        #
        #   ⚠ 이것은 제품 결함이 아니라 **시험 위생**이다. 그리고 「HTTP 를 때린
        #     시험 뒤에 objects 가 빈다」는 이 저장소가 이미 아는 함정이다 —
        #     `DsmFixture.setUpTestData` 가 같은 줄을 클래스 머리에서 한 번 쓴다.
        #     한 번으로는 모자라다: 오염은 **시험마다** 새로 생긴다.
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

    def _event_with_confidence(self, stream, confidence, *, event_type="fire"):
        """확신도를 실은 사건 하나. `DsmFixture._event` 는 확신도를 안 싣는다.

        ★ `occurred_at` 을 60초씩 벌린다 — 기록 단계 중복 억제창(10초) 안에 같은
          카메라·같은 유형이 연달아 들어가면 **한 건으로 접히고**, 접힌 표본으로는
          「몇 건이 남나」를 못 잰다(`DsmFixture._event` 와 같은 이유).
        """
        from kernels.k1_event import record_detection

        self._nth = getattr(self, "_nth", 0) + 1
        when = timezone.now() - timedelta(seconds=60 * self._nth)
        return record_detection(
            scope=self.scope_pipe, stream_monitor_id=stream.pk,
            event_type=event_type, severity="critical", occurred_at=when,
            confidence=confidence,
            snapshot_path=f"minio://dsm/{self._nth}.jpg").event_id


class FalsePositiveByCameraTest(CameraFixture):
    def test_cameras_are_ordered_by_rate_with_unmeasurable_last(self) -> None:
        """내림차순 · 판정 0건인 카메라는 **맨 뒤** · 상위 N 은 잴 수 있는 행에만."""
        noisy = [self._event(self.stream_a) for _ in range(3)]
        self._judge(noisy[0], "rejected", scope=self.scope_a)
        self._judge(noisy[1], "rejected", scope=self.scope_a)
        self._judge(noisy[2], "confirmed", scope=self.scope_a)

        quiet = [self._event(self.stream_a2) for _ in range(2)]
        self._judge(quiet[0], "confirmed", scope=self.scope_a)

        self._event(self.stream_a3)          # 미판정만 — 잴 수 없는 카메라

        resp = self.client.get(BY_CAMERA, {"days": 7, "top_n": 1},
                               **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content)
        body = resp.json()
        cams = body["cameras"]
        self.assertEqual(3, len(cams), f"카메라 3대가 나와야 합니다: {cams}")

        by_id = {c["stream_monitor_id"]: c for c in cams}
        self.assertAlmostEqual(2 / 3, by_id[self.stream_a.pk]["false_positive_rate"])
        self.assertEqual(0.0, by_id[self.stream_a2.pk]["false_positive_rate"])
        self.assertIsNone(
            by_id[self.stream_a3.pk]["false_positive_rate"],
            "판정 0건인 카메라의 오탐률이 0.0 으로 나왔습니다 — 「오탐이 없다」와 "
            "「아직 잴 수 없다」가 같은 값이 됐습니다(D-290)")

        self.assertEqual(self.stream_a.pk, cams[0]["stream_monitor_id"],
                         f"오탐률이 높은 카메라가 맨 위가 아닙니다: {cams}")
        self.assertEqual(self.stream_a3.pk, cams[-1]["stream_monitor_id"],
                         "판정 0건인 카메라가 맨 뒤가 아닙니다 — 조용한 카메라로 "
                         "보입니다")

        self.assertTrue(cams[0]["top"])
        self.assertEqual(
            1, sum(1 for c in cams if c["top"]),
            "top_n=1 인데 상위 표시가 여럿입니다 — 화면이 서버의 순위를 못 믿게 됩니다")
        self.assertFalse(by_id[self.stream_a3.pk]["top"],
                         "잴 수 없는 카메라에 순위를 줬습니다 — 판정을 안 한 것이 "
                         "상이 됩니다")

    def test_numerator_and_denominator_come_with_the_rate(self) -> None:
        """비율만 내지 않는다 — 분자·분모를 함께 낸다."""
        ids = [self._event(self.stream_a) for _ in range(2)]
        self._judge(ids[0], "rejected", scope=self.scope_a)

        resp = self.client.get(BY_CAMERA, {"days": 7}, **_bearer(self.user_a))
        row = next(c for c in resp.json()["cameras"]
                   if c["stream_monitor_id"] == self.stream_a.pk)
        self.assertEqual(1, row["false_positive"])
        self.assertEqual(1, row["reviewed"])
        self.assertEqual(1, row["unreviewed"])

    def test_other_tenants_cameras_do_not_appear(self) -> None:
        for _ in range(2):
            self._event(self.stream_b)
        self._event(self.stream_a)

        resp = self.client.get(BY_CAMERA, {"days": 7}, **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content)
        ids = {c["stream_monitor_id"] for c in resp.json()["cameras"]}
        self.assertNotIn(self.stream_b.pk, ids,
                         "테넌트 B 의 카메라가 테넌트 A 의 표에 나왔습니다")

    def test_anonymous_is_401(self) -> None:
        self.assertEqual(401, self.client.get(BY_CAMERA).status_code)


# ═══════════════════════════════════════════════════════════════════════════
# ⑧ UX-36 시뮬 「시간당 N건」 — 부속서A U2 #11 · BF-3 4단계 (턴 S)
# ═══════════════════════════════════════════════════════════════════════════
class SimulateThresholdTest(CameraFixture):
    def _simulate(self, user, **params):
        return self.client.post(f"{SIMULATE}?{urlencode(params)}", **_bearer(user))

    def test_threshold_keeps_only_events_at_or_above_it(self) -> None:
        for c in (0.9, 0.8, 0.3):
            self._event_with_confidence(self.stream_a, c)

        resp = self._simulate(self.user_a, camera_id=self.stream_a.pk,
                              confidence_min=0.5, days=7)
        self.assertEqual(200, resp.status_code, resp.content)
        body = resp.json()

        self.assertTrue(body["measurable"])
        self.assertEqual(3, body["graded_total"])
        self.assertEqual(0, body["unknown_confidence"])
        self.assertEqual(2, body["kept"])
        self.assertEqual(1, body["dropped"])
        #: 「시간당 N건」 — 화면이 이 수를 만들지 않는다. 서버가 낸 수를 그대로 쓴다.
        self.assertAlmostEqual(2 / body["window_hours"], body["events_per_hour"])
        self.assertAlmostEqual(3 / body["window_hours"], body["current_per_hour"])
        #: 「많다」의 문턱도 서버가 낸다 — 화면이 6 을 들고 있으면 두 곳이 갈린다.
        self.assertEqual(6.0, body["noisy_per_hour"])
        self.assertFalse(body["noisy"])

    def test_events_without_confidence_are_not_counted_as_kept(self) -> None:
        """확신도가 없는 사건만 있으면 **잴 수 없다** — 시간당 0건이 아니다."""
        for _ in range(3):
            self._event(self.stream_a)          # confidence 를 안 싣는다

        body = self._simulate(self.user_a, camera_id=self.stream_a.pk,
                              confidence_min=0.5, days=7).json()
        self.assertEqual(3, body["events_total"])
        self.assertEqual(0, body["graded_total"])
        self.assertEqual(3, body["unknown_confidence"])
        self.assertFalse(body["measurable"])
        self.assertIsNone(
            body["events_per_hour"],
            "가를 수 있는 사건이 0건인데 시간당 0.0건이라고 답했습니다 — "
            "「문턱을 올렸더니 알림이 사라졌다」는 거짓 안심이 됩니다(D-290)")

    def test_simulation_writes_nothing(self) -> None:
        """시뮬은 **아무것도 바꾸지 않는다** — 누르는 것과 바뀌는 것을 가른다."""
        from kernels.k5_trust import ThresholdNotSet, resolve_threshold

        self._event_with_confidence(self.stream_a, 0.9)
        self._simulate(self.user_a, camera_id=self.stream_a.pk,
                       confidence_min=0.5, days=7)
        with self.assertRaises(ThresholdNotSet):
            resolve_threshold(CAMERA_KEY, scope=self.scope_a,
                              camera_id=self.stream_a.pk)

    def test_confidence_outside_zero_to_one_is_400(self) -> None:
        for bad in (-0.1, 1.5):
            with self.subTest(confidence_min=bad):
                resp = self._simulate(self.user_a, camera_id=self.stream_a.pk,
                                      confidence_min=bad, days=7)
                self.assertEqual(400, resp.status_code, resp.content)

    def test_other_tenants_camera_yields_zero_not_a_leak(self) -> None:
        """남의 카메라 id 를 넣어도 **0건**이다 — 이름도 존재 여부도 안 나간다."""
        self._event_with_confidence(self.stream_b, 0.9)

        body = self._simulate(self.user_a, camera_id=self.stream_b.pk,
                              confidence_min=0.5, days=7).json()
        self.assertEqual(0, body["events_total"])
        self.assertNotIn("stream_monitor_name", body)

    def test_anonymous_is_401(self) -> None:
        resp = self.client.post(
            f"{SIMULATE}?{urlencode({'camera_id': 1, 'confidence_min': 0.5})}")
        self.assertEqual(401, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# ⑨ 「저장(사유) → 재조회」 — 부속서A U2 #11 완결 조건 (턴 S)
# ═══════════════════════════════════════════════════════════════════════════
THRESHOLD_WRITE = "/api/dsm/settings/thresholds"


class SaveThenReadBackTest(CameraFixture):
    """★ 이 시험이 이 화면의 **완결 조건**이다 — 저장한 값이 실제로 되돌아오는가.

    쓰는 문은 F-12 의 임계값 문 하나(이미 있던 것)이고, 읽는 문만 이번에 열었다.
    둘이 같은 값을 말하지 않으면 화면의 「저장했습니다」는 아무것도 증명하지 않는다.
    """

    def setUp(self) -> None:
        super().setUp()
        from common.tenant_roles import tenant_admin_role_code

        #: 임계값을 바꾸는 것은 관리 역할의 일이다(F-12 문지기). 그 역할 없이 재면
        #: 이 시험은 403 을 재게 되고, 그것은 이 절이 묻는 것이 아니다.
        self.user_a.roles.add(
            self._own(self._role(tenant_admin_role_code(self.group_a.pk)),
                      self.group_a))
        self.user_a.refresh_from_db()

    def _save(self, *, value, reason, user=None, camera=None):
        params = urlencode({
            "key": CAMERA_KEY, "value": value, "reason": reason,
            "scope_level": "camera",
            "scope_ref": (camera or self.stream_a).pk,
        })
        return self.client.post(f"{THRESHOLD_WRITE}?{params}",
                                **_bearer(user or self.user_a))

    def _read_back(self, *, user=None, camera=None):
        return self.client.get(
            CAMERA_THRESHOLD,
            {"camera_id": (camera or self.stream_a).pk, "key": CAMERA_KEY},
            **_bearer(user or self.user_a))

    def test_unset_reads_back_as_null_not_zero(self) -> None:
        resp = self._read_back()
        self.assertEqual(200, resp.status_code, resp.content)
        body = resp.json()
        self.assertFalse(body["set"])
        self.assertIsNone(
            body["value"],
            "값이 없는데 0 이라고 답했습니다 — 「기준선이 0」으로 읽히면 모든 신호가 "
            "초과가 됩니다")

    def test_save_then_read_back_returns_the_saved_value(self) -> None:
        saved = self._save(value=42.5, reason="장마철 상향 — 야간 오탐 다수")
        self.assertEqual(200, saved.status_code, saved.content)

        resp = self._read_back()
        self.assertEqual(200, resp.status_code, resp.content)
        body = resp.json()
        self.assertTrue(body["set"])
        self.assertEqual(
            42.5, body["value"],
            "저장한 값이 되돌아오지 않았습니다 — 화면의 「저장했습니다」가 "
            "아무것도 증명하지 못합니다")

    def test_second_save_wins_and_is_visible_immediately(self) -> None:
        """재조회는 **캐시를 타지 않는다** — 캐시가 있으면 방금 바꾼 값이 안 보인다."""
        self._save(value=10, reason="첫 값")
        self._save(value=20, reason="다시 올림 — 여전히 시끄러움")
        self.assertEqual(20, self._read_back().json()["value"],
                         "두 번째 저장이 안 보입니다 — 응답 캐시가 변경을 덮고 "
                         "있습니다(QA-05)")

    def test_empty_reason_is_rejected(self) -> None:
        """**사유 없이는 못 바꾼다.** 무엇에서 무엇으로는 표가 알고 왜는 여기뿐이다."""
        resp = self._save(value=7, reason="   ")
        self.assertEqual(400, resp.status_code, resp.content)
        self.assertFalse(self._read_back().json()["set"],
                         "사유가 비었는데 값이 저장됐습니다")

    def test_key_list_offers_only_per_camera_editable_keys(self) -> None:
        resp = self.client.get(CAMERA_THRESHOLD_KEYS, **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content)
        keys = resp.json()["keys"]
        self.assertIn(CAMERA_KEY, {k["key"] for k in keys})
        for k in keys:
            self.assertEqual(
                "camera", k["applies_to"],
                f"카메라별로 둘 수 없는 항목이 화면 목록에 있습니다: {k}")
        #: 계약이 못박은 값은 목록에 없다 — 옮길 수 있는 것처럼 그려 놓고 저장에서
        #: 거절하는 것이 거짓말이기 때문이다.
        self.assertNotIn("notify.suppress_window", {k["key"] for k in keys})
        self.assertNotIn("notify.max_latency", {k["key"] for k in keys})

    def test_unknown_key_is_400(self) -> None:
        resp = self.client.get(
            CAMERA_THRESHOLD,
            {"camera_id": self.stream_a.pk, "key": "no.such.key"},
            **_bearer(self.user_a))
        self.assertEqual(400, resp.status_code, resp.content)

    def test_other_tenants_camera_is_refused(self) -> None:
        resp = self._read_back(camera=self.stream_b)
        self.assertIn(resp.status_code, (403, 404),
                      f"남의 카메라 기준선을 읽었습니다: {resp.status_code} {resp.content}")
