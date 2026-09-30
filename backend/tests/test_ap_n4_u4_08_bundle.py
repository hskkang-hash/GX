# -*- coding: utf-8 -*-
"""DSM-U4-08 — 재난관리평가·감사 자료 묶음(ZIP) 실측 (턴 AP · WO-19 · 차선 N4).
[턴 AQ · P-436] PDF 는 차선 N4 가 구현했다 — manifest 의 `pdf.status` 가 "ok" 인지
본다(옛 「PDF 안 만듦」 결정 인용은 번호 오용이라 걷었다). CSV 일곱 + manifest 가 실제로 담기는지 잰다."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from django.core.cache import cache

from common.evidence_guard import allow_evidence_writes
from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

BUNDLE = "/api/dsm/evaluation-bundle.zip"
CBS_DRAFTS = "/api/dsm/cbs-drafts"

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


class EvaluationBundleTest(DsmFixture):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()

    def test_bundle_zip_contains_seven_csv_sources_and_a_manifest(self) -> None:
        head = _bearer(self.user_a)
        created = self.client.post(
            CBS_DRAFTS, {"kind": "안전안내", "region": "만안구", "message": "테스트 문안"},
            content_type="application/json", **head)
        self.assertEqual(200, created.status_code, created.content[:300])

        resp = self.client.get(BUNDLE, **head)
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self.assertEqual("application/zip", resp["Content-Type"])

        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = set(zf.namelist())
        expected = {
            "situation_reports.csv", "cbs_drafts.csv", "control_points.csv",
            "situation_meetings.csv", "video_access_requests.csv",
            "drill_report.csv", "access_log.csv", "manifest.json",
        }
        self.assertTrue(expected.issubset(names), names)

        cbs_csv = zf.read("cbs_drafts.csv").decode("utf-8")
        self.assertIn("만안구", cbs_csv, "CBS 초안 CSV 에 방금 만든 초안이 없습니다.")

        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        self.assertIn("pdf", manifest)
        self.assertEqual("ok", manifest["pdf"]["status"])

        _write_evidence(
            "DSM-U4-08",
            test="tests.test_ap_n4_u4_08_bundle.EvaluationBundleTest."
                "test_bundle_zip_contains_seven_csv_sources_and_a_manifest",
            method="GET", path=BUNDLE, status=200,
            resp_body={"zip_entries": sorted(names), "manifest": manifest},
            what="[턴 AP · 차선 N4] 일곱 CSV 원천 + manifest.json 이 ZIP 하나에 "
                "담긴다 — CBS 초안 CSV 에 방금 만든 초안 값이 실려 있음을 실측. "
                "[턴 AQ] manifest.pdf.status == ok 실측",
            title_parts=[
                {"part": "상황보고 발송 이력",
                 "where": "situation_reports.csv · apps/dsm/u4_evaluation_bundle_"
                         "service.py::build_bundle_zip() → situation_report_"
                         "ledger_service.list_reports() 재사용",
                 "status": "measured: 이 시험 — ZIP 안 situation_reports.csv 존재 실측"},
                {"part": "CBS 승인 기록",
                 "where": "cbs_drafts.csv → cbs_draft_service.list_drafts() 재사용",
                 "status": "measured: 이 시험 — 방금 만든 초안(만안구)이 CSV 에 그대로 실측"},
                {"part": "통제 4시각",
                 "where": "control_points.csv → control_board_service.list_board() 재사용",
                 "status": "measured: 이 시험 — ZIP 안 control_points.csv 존재 실측"},
                {"part": "상황판단회의",
                 "where": "situation_meetings.csv → situation_meeting_service."
                         "list_meetings() 재사용",
                 "status": "measured: 이 시험 — ZIP 안 situation_meetings.csv 존재 실측"},
                {"part": "열람 대장",
                 "where": "video_access_requests.csv → video_access_ledger_"
                         "service.list_requests() 재사용",
                 "status": "measured: 이 시험 — ZIP 안 video_access_requests.csv 존재 실측"},
                {"part": "훈련 실적",
                 "where": "drill_report.csv → apps.dsm.services.drill_report() 재사용",
                 "status": "measured: 이 시험 — ZIP 안 drill_report.csv 존재 실측"},
                {"part": "접속기록 요약",
                 "where": "access_log.csv → access_log_service.read_csv() 재사용 "
                         "(권한 없으면 그 파일 자리에 오류 메시지만 담고 나머지는 "
                         "계속 담는다 — 부분 실패가 전체를 막지 않는다)",
                 "status": "measured: 이 시험 — ZIP 안 access_log.csv 존재 실측"},
                {"part": "ZIP(PDF+CSV) — CSV 부분",
                 "where": "build_bundle_zip() — zipfile.ZipFile 로 위 일곱 + "
                         "manifest.json 을 하나로 묶는다",
                 "status": "measured: 이 시험 — ZIP 1건에 여덟 항목 실측(완결 조건 "
                         "「ZIP 1」)"},
                {"part": "ZIP(PDF+CSV) — PDF 부분",
                 "where": "manifest.json 의 pdf{name,status} — 차선 N4(턴 AQ) 구현",
                 "status": "measured: 이 시험 — manifest.pdf.status == ok 실측"},
            ])
