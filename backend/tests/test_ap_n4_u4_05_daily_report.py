# -*- coding: utf-8 -*-
"""DSM-U4-05 — 일일상황보고 자동(재난상황·통제 현황·대피) 실측 (턴 AP · WO-19 ·
차선 N4). 기상특보·피해 누계·동원·향후 계획은 이 시험이 닫지 않는다 —
`u4_daily_report_service.py` 머리말이 이유를 적는다(정직하게 열어 둔다)."""
from __future__ import annotations

import json
from pathlib import Path

from django.core.cache import cache

from common.evidence_guard import allow_evidence_writes
from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

DAILY = "/api/dsm/daily-report"
CONTROL_POINTS = "/api/dsm/control-points"

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
        "title_parts": title_parts,
    }
    with allow_evidence_writes("P-356 ② DSM-U4 별표 절 실측 증거"):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        out = EVIDENCE_DIR / f"{spec_id}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                       encoding="utf-8")


class DailyReportTest(DsmFixture):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()

    def test_disaster_status_counts_todays_events_and_control_status_reuses_u4_04(self) -> None:
        self._event(self.stream_a, event_type="fire", severity="critical")
        head = _bearer(self.user_a)

        created = self.client.post(
            CONTROL_POINTS, {"name": "만안 지하차도", "evacuee_count": 3,
                            "evacuation_site": "만안체육관"},
            content_type="application/json", **head)
        self.assertEqual(200, created.status_code, created.content[:300])

        resp = self.client.get(DAILY, **head)
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()
        self.assertGreaterEqual(body["disaster_status"]["occurrence_count"], 1)
        self.assertEqual("json", body["format"])
        self.assertEqual(1, body["control_status"]["point_count"],
                         "통제 현황이 daily_reflection() 값을 그대로 안 씁니다.")
        self.assertEqual(3, body["evacuation"]["evacuee_count_total"])
        self.assertIn("만안체육관", body["evacuation"]["evacuation_sites"])
        # 값을 지어내지 않는다 — 구조화 원천이 없는 셋은 정직하게 비어 있다.
        self.assertIsNone(body["weather_advisory"])
        self.assertIsNone(body["damage_cumulative"])
        _write_evidence(
            "DSM-U4-05",
            test="tests.test_ap_n4_u4_05_daily_report.DailyReportTest."
                "test_disaster_status_counts_todays_events_and_control_status_reuses_u4_04",
            method="GET", path=DAILY, status=200, resp_body=body,
            what="[턴 AP · 차선 N4] 반쪽 채움 — 재난상황·통제 현황·대피 셋은 "
                "기존 공개 면을 재사용해 실측으로 닫았다. 기상특보는 외부 "
                "실연동이라 제외, 피해 누계·동원·향후 계획 셋은 구조화 원천이 "
                "없어 정직하게 열어 둔다 — 절 전체는 반쪽이다(P-419)",
            title_parts=[
                {"part": "재난상황(오늘 발생·등급별·미종결)",
                 "where": "GET /api/dsm/daily-report · "
                         "apps/dsm/u4_daily_report_service.py::daily_report()"
                         "(apps.dsm.services.recent_events 재사용, 새 질의 없음)",
                 "status": "measured: 이 시험 — occurrence_count>=1 실측"},
                {"part": "통제 현황",
                 "where": "u4_daily_report_service.py::daily_report() → "
                         "control_board_service.daily_reflection() 재사용(턴 AN)",
                 "status": "measured: 이 시험 — point_count=1 실측(daily_reflection "
                         "값 그대로)"},
                {"part": "대피(인원·장소)",
                 "where": "u4_daily_report_service.py::daily_report() — 통제 "
                         "지점의 evacuee_count/evacuation_site 합산(control_board_"
                         "service.py 에 이 턴 구조화 칸(after=)을 더했다)",
                 "status": "measured: 이 시험 — evacuee_count_total=3 · "
                         "evacuation_sites=['만안체육관'] 실측"},
                {"part": "기상특보",
                 "where": "u4_daily_report_service.py::daily_report() — "
                         "weather_advisory 필드는 항상 None",
                 "status": "없음 — 기상청/산림청 특보 수신 API 실연동이 이 "
                         "저장소에 없다",
                 "excluded_by": "P-428",
                 "excluded_why": "기상특보 수신은 외부 기관(기상청) API 실연동이다 "
                                "(WO-19 「외부 실연동은 하지 않는다」)."},
                {"part": "피해 누계",
                 "where": "u4_daily_report_service.py::daily_report() — "
                         "damage_cumulative 필드는 항상 None",
                 "status": "없음 — 이 저장소에 피해(인명·재산) 값을 쥔 구조화 "
                         "표가 없다(별지 제1호서식은 자유 입력칸, 재조회 가능한 "
                         "표가 아니다 · incident_report.py 실측). 지어내지 "
                         "않는다(D-280) — 외부 실연동이 아니라 내부 구조화 "
                         "표가 없는 코드 결손이라 excluded_by 로 못 막는다."},
                {"part": "동원(자원 배치)",
                 "where": "u4_daily_report_service.py::daily_report() — "
                         "mobilization 필드는 항상 None",
                 "status": "없음 — 동원 인력·장비를 쥔 구조화 표가 이 저장소에 "
                         "없다. 지어내지 않는다(D-280)."},
                {"part": "향후 계획",
                 "where": "u4_daily_report_service.py::daily_report() — "
                         "future_plan 필드는 항상 None",
                 "status": "없음 — 자유 서술 계획을 쥘 표가 이 저장소에 없다. "
                         "지어내지 않는다(D-280)."},
            ])

    def test_other_tenants_events_are_not_counted(self) -> None:
        self._event(self.stream_b, event_type="fire")
        head_a = _bearer(self.user_a)
        resp = self.client.get(DAILY, **head_a)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(0, resp.json()["disaster_status"]["occurrence_count"],
                         "B 테넌트 사건이 A 테넌트 일일보고에 섞였습니다 — 격리 실패.")
