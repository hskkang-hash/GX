# -*- coding: utf-8 -*-
"""P-437 — 「누른 뒤」 U1#11 은 **탐침 포함 목록**에서 표본을 고른다 (턴 AQ · 차선 Q).

턴 AP 회차(2026-09-29 11:18Z): 씨앗 4건(575509~575512)이 전부 미판정인데 U1#11 은 「표본
25건 전부 판정됨」 회색이었다. 씨앗은 탐침 표식(`track_id=data_source=probe;…`)으로 심기고
`GET /api/dsm/events` 는 P-220 부터 **기본이 탐침 제외**다 — 술어가 본 갈래(고객 목록)와
씨앗이 들어간 자리(탐침 칸)가 달랐다. 판정기(`scripts/verify_click_completes.py`)는 이제
`include_probe=true` 목록을 `pick_unjudged` 로 고른다(측정은 V).

캐시 처리: 해당 없음 — HTTP 를 안 두드리고 DB 도 안 쓴다(순수 함수 · `SimpleTestCase`).
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

TAG = "gxprobe-D384-screen"


def _gate():
    here = Path(__file__).resolve()
    for cand in ("/repo/scripts", str(here.parent.parent.parent / "scripts")):
        if Path(cand, "verify_click_completes.py").is_file() and cand not in sys.path:
            sys.path.insert(0, cand)
    import verify_click_completes  # noqa: PLC0415
    return verify_click_completes


class PickFromProbeInclusiveList(SimpleTestCase):
    def test_this_run_seed_is_picked(self) -> None:
        g = _gate()
        rows = [{"event_id": 575509, "stream_monitor_name": TAG + " 캡처용 카메라", "verdict": None},
                {"event_id": 446155, "stream_monitor_name": "GX-SEED-DSM", "verdict": "confirmed"}]
        self.assertEqual([575509], g.pick_unjudged(rows, TAG, [575509]))

    def test_last_run_seed_is_not_picked(self) -> None:
        g = _gate()
        rows = [{"event_id": 561608, "stream_monitor_name": TAG + " 캡처용 카메라", "verdict": None}]
        self.assertEqual([], g.pick_unjudged(rows, TAG, [575509]))

    def test_non_probe_unjudged_still_counts(self) -> None:
        g = _gate()
        rows = [{"event_id": 7, "stream_monitor_name": "정문카메라", "verdict": ""}]
        self.assertEqual([7], g.pick_unjudged(rows, TAG, []))

    def test_driver_reads_the_probe_inclusive_list(self) -> None:
        g = _gate()
        self.assertIn("include_probe=true", g.U1_11_PICK_PATH)
        self.assertIn(g.U1_11_PICK_PATH, g.DRIVER)
        self.assertIn("def pick_unjudged", g._shared_driver_src())

    def test_self_test_fails_if_pick_ignores_keep(self) -> None:
        """자기시험 짝 — 지난 회 씨앗까지 집는 술어로 바꾸면 자기시험이 빨강이어야 한다."""
        g = _gate()

        def sloppy(rows, probe_tag, keep_ids):
            return [e.get("event_id") for e in rows or [] if not e.get("verdict")]

        with mock.patch.object(g, "pick_unjudged", sloppy), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertNotEqual(g.EXIT_OK, g.self_test())
