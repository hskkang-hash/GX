# -*- coding: utf-8 -*-
"""DSM-U4-09 — 통계 축 추가(지역안전지수 6분야) 실측 (턴 AP · WO-19 · 차선 N4).
새 질의를 짜지 않는다 — `stats.stats_axes()` 의 event_type 축을 다시 접는다."""
from __future__ import annotations

import json
from pathlib import Path

from django.core.cache import cache

from common.evidence_guard import allow_evidence_writes
from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

SAFETY = "/api/dsm/stats/safety-index"

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"


def _write_evidence(spec_id: str, *, test: str, method: str, path: str,
                    status: int, resp_body: dict, what: str,
                    title_parts: list[dict]) -> None:
    from django.utils import timezone

    payload = {
        "id": spec_id, "measured_at": timezone.now().isoformat(),
        "measured_by": "django_test_client", "test": test,
        "request": {"method": method, "path": path, "params": {}},
        "response": {"status": status, "body": resp_body}, "what": what,
        #: [턴 AQ · P-431 · 차선 Q] title_parts 는 json 에 안 쓴다 — 사람 표는 `<id>.retro.md`.
    }
    with allow_evidence_writes("P-356 ② DSM-U4 별표 절 실측 증거"):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        out = EVIDENCE_DIR / f"{spec_id}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                       encoding="utf-8")


class SafetyIndexAxisTest(DsmFixture):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()

    def test_fire_events_land_in_the_fire_field_and_mapping_table_is_returned(self) -> None:
        self._event(self.stream_a, event_type="fire")
        self._event(self.stream_a, event_type="vehicle")
        head = _bearer(self.user_a)

        resp = self.client.get(SAFETY, **head)
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()
        self.assertEqual("safety_index", body["by"])
        rows = {r["key"]: r["count"] for r in body["safety_index"]}
        self.assertGreaterEqual(rows.get("화재", 0), 1)
        self.assertGreaterEqual(rows.get("교통사고", 0), 1)
        self.assertIn("fire", body["mapping"])
        self.assertEqual("화재", body["mapping"]["fire"])
        self.assertEqual(6, len(body["fields"]), "지역안전지수 6분야가 아닙니다.")
        _write_evidence(
            "DSM-U4-09",
            test="tests.test_ap_n4_u4_09_safety_index.SafetyIndexAxisTest."
                "test_fire_events_land_in_the_fire_field_and_mapping_table_is_returned",
            method="GET", path=SAFETY, status=200, resp_body=body,
            what="[턴 AP · 차선 N4] fire→화재 · vehicle→교통사고 로 실제로 갈리고, "
                "event_type→분야 매핑 표(완결 조건)가 응답에 그대로 실린다 — "
                "실측(새 질의 없음, stats.stats_axes() 재사용)",
            title_parts=[
                {"part": "지역안전지수 6분야에 맞춘 유형 분류 열",
                 "where": "GET /api/dsm/stats/safety-index · "
                         "apps/dsm/u4_safety_index_stats.py::safety_index_axis()"
                         "(stats.stats_axes() 의 event_type 축을 재접음, 새 질의 없음)",
                 "status": "measured: 이 시험 — fire 2건→화재, vehicle 1건→교통"
                         "사고로 실제로 갈림"},
                {"part": "분류 매핑 표",
                 "where": "apps/dsm/u4_regulations.py::EVENT_TYPE_SAFETY_INDEX · "
                         "응답 mapping 칸",
                 "status": "measured: 이 시험 — mapping[\"fire\"]==\"화재\" 실측, "
                         "fields 6개(지역안전지수 6분야) 실측"},
            ])

    def test_other_tenants_events_are_not_counted(self) -> None:
        self._event(self.stream_b, event_type="fire")
        head_a = _bearer(self.user_a)
        resp = self.client.get(SAFETY, **head_a)
        self.assertEqual(200, resp.status_code)
        rows = {r["key"]: r["count"] for r in resp.json()["safety_index"]}
        self.assertEqual(0, rows.get("화재", 0),
                         "B 테넌트 사건이 A 테넌트 지역안전지수 집계에 섞였습니다 — 격리 실패.")
