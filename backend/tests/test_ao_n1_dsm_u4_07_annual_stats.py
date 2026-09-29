# -*- coding: utf-8 -*-
"""DSM-U4-07 「연간 통계(출력)」 채움 (턴 AO · P-407 · 차선 N1).

턴 AM 은 요청·승인·제공·목록(`GET /video-access-requests`)까지 열었지만, 명세
제목이 부르는 **연간 통계**(`docs/agent/evidence/SPEC/DSM-U4-07.json` 옛
title_parts 「목록 조회만 있고 연간 집계 배치는 없다」)는 없었다. 이 시험은
`GET /video-access-requests/annual-stats` 가 실제로 그 해의 요청·승인·제공
건수를 세는지 — **새 표 없이**(같은 감사 이력을 다시 읽어) 묻는다.
"""
from __future__ import annotations

from django.core.cache import cache
from django.utils import timezone

from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

VIDEO_ACCESS = "/api/dsm/video-access-requests"


def _annual_stats_path(year: int | None = None) -> str:
    return (f"{VIDEO_ACCESS}/annual-stats?year={year}" if year is not None
           else f"{VIDEO_ACCESS}/annual-stats")


class VideoAccessAnnualStatsTest(DsmFixture):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()

    def _create_approve_provide(self, *, org: str) -> int:
        head = _bearer(self.user_a)
        created = self.client.post(
            VIDEO_ACCESS, {"requester_org": org, "doc_no": f"공문-{org}",
                          "purpose": "수사"},
            content_type="application/json", **head)
        self.assertEqual(200, created.status_code, created.content[:300])
        request_id = created.json()["request_id"]
        cache.clear()

        approved = self.client.post(
            f"{VIDEO_ACCESS}/{request_id}/approve", {},
            content_type="application/json", **head)
        self.assertEqual(200, approved.status_code, approved.content[:300])
        cache.clear()

        provided = self.client.post(
            f"{VIDEO_ACCESS}/{request_id}/provide", {"method": "직접 전달"},
            content_type="application/json", **head)
        self.assertEqual(200, provided.status_code, provided.content[:300])
        cache.clear()
        return request_id

    def test_this_years_requests_approvals_and_provisions_are_counted(self) -> None:
        this_year = timezone.localtime(timezone.now()).year
        self._create_approve_provide(org="시흥경찰서")
        self._create_approve_provide(org="안산소방서")

        resp = self.client.get(_annual_stats_path(), **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()
        self.assertEqual(this_year, body["year"])
        self.assertEqual(2, body["requested"])
        self.assertEqual(2, body["approved"])
        self.assertEqual(2, body["provided"])
        month_key = f"{timezone.localtime(timezone.now()).month:02d}"
        self.assertEqual(2, body["by_month"][month_key],
                         "월별 요청 건수 집계가 안 맞습니다.")

    def test_a_year_with_no_requests_is_all_zero_not_fabricated(self) -> None:
        self._create_approve_provide(org="시흥경찰서")

        resp = self.client.get(_annual_stats_path(1999), **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()
        self.assertEqual(1999, body["year"])
        self.assertEqual(0, body["requested"])
        self.assertEqual(0, body["approved"])
        self.assertEqual(0, body["provided"])
        self.assertEqual(0, sum(body["by_month"].values()))

    def test_bad_year_is_400(self) -> None:
        resp = self.client.get(
            f"{VIDEO_ACCESS}/annual-stats?year=99999", **_bearer(self.user_a))
        self.assertEqual(400, resp.status_code, resp.content[:300])

    def test_other_tenants_requests_are_not_counted(self) -> None:
        """B 테넌트의 제3자 제공 요청이 A 테넌트 연간 통계에 안 섞인다(격리)."""
        head_b = _bearer(self.user_b)
        created = self.client.post(
            VIDEO_ACCESS, {"requester_org": "남의경찰서", "doc_no": "공문-B",
                          "purpose": "수사"},
            content_type="application/json", **head_b)
        self.assertEqual(200, created.status_code, created.content[:300])
        cache.clear()

        resp = self.client.get(_annual_stats_path(), **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()
        self.assertEqual(0, body["requested"],
                         "B 테넌트 요청이 A 테넌트 연간 통계에 섞였습니다 — 격리 실패.")
