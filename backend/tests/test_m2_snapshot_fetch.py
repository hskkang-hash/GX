# -*- coding: utf-8 -*-
"""P-162 U3#3 「상황 사진 1장 보기」 회귀 — **서버 쪽 두 점** (2026-09-17 · 턴 T · 차선 U3).

턴 S 빨강의 실측(`docs/agent/evidence/P-118/click_completes.json` U3#3):
    · 판정기가 고른 사건 204340 은 `capture_screens.py` 가 심은 **캡처용 씨앗**이고
      `snapshot_path=""` 였다(`scripts/capture_screens.py:543` — MinIO 부재라 비워 둔다).
    · 상세 응답 `snapshot_path` = `""`(before·after 둘 다) → 화면은
      「이 이벤트에는 스냅샷 참조가 없습니다」를 그렸고(`MobileEventDetail.tsx:618`
      `e.snapshot_path ? <EventSnapshot/> : …`) `GET …/snapshot` 은 **나가지 않는 것이
      옳다** — 참조 없는 사진을 부르면 404 를 부르는 것이다.
    · 그러므로 제품 결함이 아니라 **표본 선택**(판정기가 「판정 안 된 첫 사건」을 고르는데
      그것이 사진 없는 씨앗이었다)이다. 턴 R 초록은 고른 사건에 참조가 있었기 때문이다.

이 시험이 못박는 두 점 — 화면이 사진을 그릴 조건과 그 GET 이 200 인 것:
    ① 참조가 **있는** 사건: 상세 응답이 `snapshot_path` 를 내고, `GET /events/{id}/snapshot`
       이 `200 image/jpeg` 다(저장소는 mock — 바이트는 진짜 JPEG).
    ② 참조가 **없는** 사건: 상세 응답 `snapshot_path=""` · 그 GET 은 404 — 화면이
       GET 을 안 내는 것이 옳고, 냈다면 404 를 「불러오지 못했습니다」로 그리지 않는다.

캐시 처리: 우회 — 라우트 함수를 직접 부른다(D-341).
"""
from __future__ import annotations

from unittest import mock

from django.http import Http404
from django.test import RequestFactory

from tests.test_snapshot_route import FETCH, _SnapshotFixture, _a_jpeg


class M2SnapshotFetchTest(_SnapshotFixture):

    def _detail(self, event_id: int) -> dict:
        from apps.dsm.api import DsmAPI

        request = RequestFactory().get(f"/api/dsm/events/{event_id}")
        request.user = self.user_a
        return DsmAPI.event_detail(DsmAPI(), request, event_id)

    def test_an_event_with_a_reference_serves_its_photo_as_200_jpeg(self) -> None:
        """① 상세가 참조를 내고 → 그 GET 이 200 image/jpeg."""
        detail = self._detail(self.event_id)
        self.assertTrue(detail.get("snapshot_path"),
                        "상세 응답에 snapshot_path 가 비어 있습니다 — 화면은 이 값이 있어야 GET 을 냅니다.")
        with mock.patch(FETCH, return_value=(_a_jpeg(), "")):
            response = self._call(self.user_a)
        self.assertEqual(200, response.status_code)
        self.assertEqual("image/jpeg", response["Content-Type"])
        self.assertEqual(b"\xff\xd8", response.content[:2], "JPEG 바이트가 아닙니다.")

    def test_an_event_without_a_reference_says_so_and_the_photo_route_is_404(self) -> None:
        """② 참조 없음 = 화면이 GET 을 안 낸다. 냈더라도 404 이지 500 이 아니다."""
        from ninja.errors import HttpError

        detail = self._detail(self.event_no_frame)
        self.assertEqual("", detail.get("snapshot_path") or "",
                         "참조 없는 사건이 참조를 냈습니다 — 화면이 없는 사진을 부르게 됩니다.")
        with self.assertRaises((HttpError, Http404)) as caught:
            self._call(self.user_a, self.event_no_frame)
        status = getattr(caught.exception, "status_code", 404)
        self.assertEqual(404, status)

    def test_the_mobile_screen_gates_the_fetch_on_snapshot_path(self) -> None:
        """화면 쪽 조건을 **글자로** 못박는다 — `e.snapshot_path ? <EventSnapshot …> : …`.

        판정기가 사진 없는 씨앗을 고르면 이 조건 때문에 GET 이 안 나가는 것이 옳다.
        조건이 사라지면(무조건 GET) 참조 없는 사건마다 404 가 「불러오지 못했습니다」로 그려진다.
        """
        from pathlib import Path

        here = Path(__file__).resolve()
        candidates = [p / "frontend" / "src" / "features" / "mobile" / "pages" / "MobileEventDetail.tsx"
                      for p in here.parents[1:4]]
        source = next((c for c in candidates if c.is_file()), None)
        if source is None:
            self.skipTest("frontend 소스가 이 컨테이너에 마운트되지 않았다 — 회색(초록 아님)")
        text = source.read_text(encoding="utf-8")
        self.assertIn("e.snapshot_path ? (", text)
        self.assertIn('dataGx="snapshot"', text)
