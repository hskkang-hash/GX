# -*- coding: utf-8 -*-
"""턴 AN 새 P-356 게이트 셋의 짝 — **자기시험은 먼저 실패해 본다** (P-319 · P-323).

`scripts/_gate_header.py::SELF_TEST_LINKS` 가 이 파일을 가리킨다:
`verify_spec_fws_f3.py`(N2) · `verify_spec_fws_f3b.py`(N3) · `verify_spec_u5_an.py`(N4).

캐시 처리: 해당 없음 — HTTP 를 안 두드린다. 게이트의 순수 판정 함수(`judge_evidence`)를
파이썬에서 직접 부른다. 망가뜨림은 `test_verify_spec_fws_f6_gate_can_fail.py` 와 같은
두 가지다(세 게이트가 그 판정식을 베꼈으니 같은 자리에서 깨져야 한다):
증거 없음을 통과시키는 판정 · 응답 500 을 통과시키는 판정.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

from django.test import SimpleTestCase

GATES = ("verify_spec_fws_f3", "verify_spec_fws_f3b", "verify_spec_u5_an")


def _gate(name):
    here = Path(__file__).resolve()
    for cand in ("/repo/scripts", str(here.parent.parent.parent / "scripts")):
        if Path(cand).is_dir() and cand not in sys.path:
            sys.path.insert(0, cand)
    return importlib.import_module(name)


def _run_broken(name, broken_factory) -> int:
    g = _gate(name)
    real = g.judge_evidence
    g.judge_evidence = broken_factory(g, real)
    try:
        return g.self_test()
    finally:
        g.judge_evidence = real


class TheSelfTestCanFail(SimpleTestCase):
    def test_self_test_passes_as_built(self) -> None:
        for name in GATES:
            with self.subTest(gate=name):
                self.assertEqual(0, _gate(name).self_test())

    def test_self_test_fails_when_missing_evidence_is_waved_through(self) -> None:
        def factory(g, real):
            def waves_missing(clause_id, payload):
                if payload is None:
                    return g.EXIT_OK, "없어도 통과시킨다(망가진 판정)"
                return real(clause_id, payload)
            return waves_missing

        for name in GATES:
            with self.subTest(gate=name):
                self.assertEqual(1, _run_broken(name, factory),
                                 "증거 없음을 통과시키는 판정식을 자기시험이 못 잡는다")

    def test_self_test_fails_when_a_failed_response_is_waved_through(self) -> None:
        def factory(g, real):
            def any_status_is_green(clause_id, payload):
                if payload is not None and (payload.get("response") or {}).get("status") == 500:
                    return g.EXIT_OK, "500 도 통과시킨다(망가진 판정)"
                return real(clause_id, payload)
            return any_status_is_green

        for name in GATES:
            with self.subTest(gate=name):
                self.assertEqual(1, _run_broken(name, factory),
                                 "응답 500 을 통과시키는 판정식을 자기시험이 못 잡는다")
