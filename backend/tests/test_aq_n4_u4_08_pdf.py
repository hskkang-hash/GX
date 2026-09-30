# -*- coding: utf-8 -*-
"""DSM-U4-08 — 재난관리평가·감사 자료 묶음 ZIP 에 **PDF 가 함께 실린다** (턴 AQ · 차선 N4 · P-436).

예전 증거 표의 `excluded_by: P-392` 는 번호 오용이었다(P-392 는 HWPX · F6-07 결정).
PDF 는 K4 공개 면(`kernels.k4_report.render_html`)으로 찍은 요약 한 장이다.

재는 것: GET /api/dsm/evaluation-bundle.zip → ZIP 안 `evaluation_bundle.pdf` 바이트가
`%PDF` 로 시작 · 쪽 ≥ 1 · manifest.json 의 pdf.status == "ok" · CSV 일곱은 그대로.
기존 `test_ap_n4_u4_08_bundle.py` 는 고치지 않는다(다른 차선 소유) — 새 파일이다.

캐시 처리: 우회 — 응답이 `Cache-Control: no-store` 인 파일 문이고, 각 시험 `setUp` 에서
`cache.clear()`.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
import zlib

from django.core.cache import cache

from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

BUNDLE = "/api/dsm/evaluation-bundle.zip"
CSV_NAMES = {
    "situation_reports.csv", "cbs_drafts.csv", "control_points.csv",
    "situation_meetings.csv", "video_access_requests.csv", "drill_report.csv",
    "access_log.csv",
}


def _page_count(data: bytes) -> int:
    """쪽 객체 수. pypdf 가 이 이미지에 없어(실측) 직접 센다 — 날 본문과, 압축된
    객체 스트림(FlateDecode)을 풀어낸 본문 양쪽에서 `/Type /Page`(`/Pages` 제외)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        pass
    else:
        return len(PdfReader(io.BytesIO(data)).pages)
    bodies = [data]
    eol = bytes([13, 10])  # CR LF (백슬래시 없이 적는다 — 도구가 벗긴다)
    for raw in re.findall(b"stream(.*?)endstream", data, re.S):
        try:
            bodies.append(zlib.decompress(raw.lstrip(eol)))
        except zlib.error:
            continue
    pattern = re.compile(b"/Type */Page(?![sA-Za-z0-9_])")
    return sum(len(pattern.findall(b)) for b in bodies)


class EvaluationBundlePdfTest(DsmFixture):
    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        from core.middleware.refresh_token import thread_local

        thread_local.request = None
        super().setUpTestData()

    def setUp(self) -> None:
        super().setUp()
        cache.clear()

    def test_bundle_zip_carries_a_real_pdf(self) -> None:
        resp = self.client.get(BUNDLE, **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = set(zf.namelist())
        self.assertTrue(CSV_NAMES.issubset(names), names)

        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        self.assertEqual("ok", manifest["pdf"]["status"], manifest["pdf"])
        self.assertIn(manifest["pdf"]["name"], names)

        pdf = zf.read(manifest["pdf"]["name"])
        self.assertTrue(pdf.startswith(b"%PDF"), pdf[:16])
        self.assertGreaterEqual(_page_count(pdf), 1)
