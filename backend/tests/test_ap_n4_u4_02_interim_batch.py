# -*- coding: utf-8 -*-
"""DSM-U4-02 — 중간 보고 사이클(08시·17시 배치 + NDMS 내보내기) 실측
(턴 AP · WO-19 · 차선 N4).
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.cache import cache

from common.evidence_guard import allow_evidence_writes
from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

BATCH = "/api/dsm/situation-reports/interim-batch"
NDMS = "/api/dsm/situation-reports/ndms-export.csv"

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"


def _write_evidence(spec_id: str, *, test: str, method: str, path: str,
                    status: int, resp_body: dict, what: str,
                    title_parts: list[dict]) -> None:
    """`test_ap_n3_o10_o11_ops.py::_write_evidence` 와 같은 모양(D-212)."""
    from django.utils import timezone

    payload = {
        "id": spec_id, "measured_at": timezone.now().isoformat(),
        "measured_by": "django_test_client", "test": test,
        "request": {"method": method, "path": path, "params": {}},
        "response": {"status": status, "body": resp_body}, "what": what,
        "title_parts": title_parts,
    }
    with allow_evidence_writes("P-356 ② DSM-U4 별표 절 실측 증거 — pytest 가 "
                              "방금 두드린 HTTP 왕복을 그대로 적는다"):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        out = EVIDENCE_DIR / f"{spec_id}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                       encoding="utf-8")


class InterimBatchTest(DsmFixture):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()

    def test_batch_issues_interim_reports_for_open_events_and_dedupes_same_slot(self) -> None:
        eid = self._event(self.stream_a, event_type="fire")
        head = _bearer(self.user_a)

        first = self.client.post(BATCH, {}, content_type="application/json", **head)
        self.assertEqual(200, first.status_code, first.content[:300])
        body = first.json()
        issued_ids = [row["event_id"] for row in body["issued"]]
        self.assertIn(eid, issued_ids, "미종결 사건이 배치에서 채번되지 않았습니다.")

        second = self.client.post(BATCH, {}, content_type="application/json", **head)
        self.assertEqual(200, second.status_code, second.content[:300])
        body2 = second.json()
        self.assertIn(eid, body2["skipped"],
                     "같은 슬롯·같은 날 재호출인데 중복 채번됐습니다.")
        self.assertEqual(body["slot"], body2["slot"])
        _write_evidence(
            "DSM-U4-02", test="tests.test_ap_n4_u4_02_interim_batch.InterimBatchTest."
                              "test_batch_issues_interim_reports_for_open_events_and_dedupes_same_slot",
            method="POST", path=BATCH, status=200, resp_body=body2,
            what="[턴 AP · 차선 N4] 08시/17시 슬롯 배치가 미종결 사건에 중간 보고를 "
                "채번하고, 같은 슬롯·같은 날 재호출은 건너뛴다 — 실측",
            title_parts=[
                {"part": "08시·17시 기준 응급조치 보고 자동 초안(1일 2회)",
                 "where": "POST /api/dsm/situation-reports/interim-batch · "
                         "apps/dsm/u4_interim_report_service.py::issue_interim_batch()"
                         "(슬롯 판정 `_slot_for` · 기존 situation_report_ledger_"
                         "service.issue_report(kind=중간) 재사용)",
                 "status": "measured: 이 시험 — 미종결 사건이 배치로 채번됨(issued)"},
                {"part": "같은 슬롯·같은 날 중복 채번 방지",
                 "where": "u4_interim_report_service.py::_batch_marker_action() "
                         "감사 마커",
                 "status": "measured: 이 시험 — 재호출 시 같은 사건이 skipped 로 "
                         "빠짐(slot 값도 같음)"},
                {"part": "NDMS 입력용 표 내보내기(항목 1:1)",
                 "where": "GET /api/dsm/situation-reports/ndms-export.csv · "
                         "u4_interim_report_service.py::export_ndms_csv()",
                 "status": "measured: tests.test_ap_n4_u4_02_interim_batch."
                         "InterimBatchTest.test_ndms_export_csv_lists_issued_reports "
                         "— CSV 에 방금 채번된 사건번호·report_id 열이 실측됨"},
            ])

    def test_other_tenants_events_are_not_issued(self) -> None:
        eid_b = self._event(self.stream_b, event_type="fire")
        head_a = _bearer(self.user_a)
        resp = self.client.post(BATCH, {}, content_type="application/json", **head_a)
        self.assertEqual(200, resp.status_code)
        issued_ids = [row["event_id"] for row in resp.json()["issued"]]
        self.assertNotIn(eid_b, issued_ids, "B 테넌트 사건이 A 테넌트 배치에 섞였습니다 — 격리 실패.")

    def test_ndms_export_csv_lists_issued_reports(self) -> None:
        eid = self._event(self.stream_a, event_type="fire")
        head = _bearer(self.user_a)
        self.client.post(BATCH, {}, content_type="application/json", **head)

        resp = self.client.get(NDMS, **head)
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self.assertIn("text/csv", resp["Content-Type"])
        text = resp.content.decode("utf-8-sig")
        self.assertIn(str(eid), text, "NDMS CSV 에 방금 채번된 사건번호가 없습니다.")
        self.assertIn("report_id", text.splitlines()[0])
