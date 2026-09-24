# -*- coding: utf-8 -*-
"""P-325 · P-326 게이트(`scripts/verify_password_reset.py`)의 짝 — **자기시험은 먼저 실패해 본다**.

`scripts/_gate_header.py` 의 `SELF_TEST_LINKS` 가 이 파일을 가리킨다(P-319 · P-323 · D-479).
턴 AI 조율자가 병합하며 지었다 — 차선 S 가 게이트를 짓던 때 차선 F 가 「새 게이트는 짝이
있어야 한다」를 같은 턴에 세웠고, 검사기가 이 게이트를 첫 「짝 없음」으로 잡았다.

망가뜨림은 **그날 실제로 일어났던 모양**이다:
① [실측 2026-09-24] `frontendUrl` 칸이 **없어** 메일 링크가 dj-core 기본값
   `http://localhost:3001`(아무도 안 듣는 포트)로 나갔다 — 「칸이 없으면 모른다」로
   넘기는 눈이면 그날이 초록이다.
② 「pytest 가 뭔가 통과했으면 초록」 — 1건 실패가 섞인 요약을 통과로 읽는 눈.

절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import sys
from pathlib import Path

from django.test import SimpleTestCase


def _gate():
    here = Path(__file__).resolve()
    for cand in ("/repo/scripts", str(here.parent.parent.parent / "scripts")):
        if Path(cand).is_dir() and cand not in sys.path:
            sys.path.insert(0, cand)
    import verify_password_reset  # noqa: PLC0415

    return verify_password_reset


class TheSelfTestCanFail(SimpleTestCase):
    def test_self_test_passes_as_built(self) -> None:
        self.assertEqual(0, _gate().self_test())

    def test_self_test_fails_when_missing_cell_is_waved_through(self) -> None:
        g = _gate()
        real = g.judge_link_host

        def waves_missing_cell(frontend_cell, link_body):
            if not frontend_cell:
                return g.EXIT_OK, "칸이 없다 — 모른다고 넘긴다"
            return real(frontend_cell, link_body)

        g.judge_link_host = waves_missing_cell
        try:
            got = g.self_test()
        finally:
            g.judge_link_host = real
        self.assertEqual(1, got, "칸 없음 + 3001 링크(그날)를 자기시험이 못 잡는다")

    def test_self_test_fails_when_any_pass_is_green(self) -> None:
        g = _gate()
        real = g.judge_gate_tests

        def any_pass_is_green(summary):
            if summary and summary[0] > 0:
                return g.EXIT_OK, "하나라도 통과"
            return real(summary)

        g.judge_gate_tests = any_pass_is_green
        try:
            got = g.self_test()
        finally:
            g.judge_gate_tests = real
        self.assertEqual(1, got, "1건 실패가 섞인 길목 시험을 자기시험이 못 잡는다")
