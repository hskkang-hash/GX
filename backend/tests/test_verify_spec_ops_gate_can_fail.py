# -*- coding: utf-8 -*-
"""P-356/P-376 게이트(`scripts/verify_spec_ops.py`)의 짝 — **자기시험은 먼저
실패해 본다**. `scripts/_gate_header.py` 의 `SELF_TEST_LINKS` 가 이 파일을
가리킨다(P-319 · P-323).

캐시 처리: 해당 없음 — 이 시험은 HTTP 를 안 두드린다. 게이트의 순수 판정 함수
(`judge_evidence`)를 파이썬에서 직접 부를 뿐이라 캐시가 낄 자리가 없다.

망가뜨림은 **이 게이트가 실제로 막으려는 모양**이다: 증거 파일이 없거나(존재
확인을 빼먹은 눈) 응답이 500 인데(성공을 가장한 실패) 그것을 통과로 읽는 판정식
(`verify_spec_fws.py`·`verify_spec_dsm.py` 의 짝과 같은 망가뜨림 — D-212, 판정
모양이 하나면 망가뜨리는 모양도 하나다).
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
    import verify_spec_ops  # noqa: PLC0415

    return verify_spec_ops


_GOOD_EVIDENCE = {
    "id": "O-10", "measured_at": "2026-09-28T00:00:00+00:00",
    "measured_by": "django_test_client", "test": "tests.test_p356_ops_spec_promotions.X.y",
    "request": {"method": "POST", "path": "/api/ops/keys/rotate", "body": {}},
    "response": {"status": 200, "body": {}}, "what": "실측",
}


class TheSelfTestCanFail(SimpleTestCase):
    def test_self_test_passes_as_built(self) -> None:
        self.assertEqual(0, _gate().self_test())

    def test_self_test_fails_when_missing_evidence_is_waved_through(self) -> None:
        """★ 증거 파일이 없는데(못 쟀다가 아니라) 통과로 읽으면 — 안 닫힌 절이
        닫힌 것으로 대장에 올라간다. 이 게이트가 있는 이유 그 자체다."""
        g = _gate()
        real = g.judge_evidence

        def waves_missing(clause_id, payload):
            if payload is None:
                return g.EXIT_OK, "없어도 통과시킨다(망가진 판정)"
            return real(clause_id, payload)

        g.judge_evidence = waves_missing
        try:
            got = g.self_test()
        finally:
            g.judge_evidence = real
        self.assertEqual(1, got, "증거 파일 없음을 통과시키는 판정식을 자기시험이 "
                                "못 잡는다")

    def test_self_test_fails_when_a_failed_response_is_waved_through(self) -> None:
        """★ 응답 500(성공을 가장한 실패)을 2xx 로 읽으면 — HTTP 를 안 두드린
        증거와 구별이 안 된다."""
        g = _gate()
        real = g.judge_evidence

        def any_status_is_green(clause_id, payload):
            if payload is not None and payload.get("response", {}).get("status") == 500:
                return g.EXIT_OK, "500 도 통과시킨다(망가진 판정)"
            return real(clause_id, payload)

        g.judge_evidence = any_status_is_green
        try:
            got = g.self_test()
        finally:
            g.judge_evidence = real
        self.assertEqual(1, got, "500 응답을 통과시키는 판정식을 자기시험이 못 잡는다")

    def test_closed_clauses_is_honestly_empty_this_turn(self) -> None:
        """★ 이 게이트만의 표식 — `CLOSED_CLAUSES` 가 비어 있어야 한다(P-376).
        누가 실제로 O-10·O-04 를 닫으면 이 시험이 실패해서 「이제 채워야 한다」고
        말한다 — 그때는 이 시험을 지우는 것이 아니라 값을 고치는 것이 맞다."""
        g = _gate()
        self.assertEqual((), g.CLOSED_CLAUSES)
        self.assertEqual({"O-10", "O-04"}, set(g.NOT_STARTED))
        for clause_id, why in g.NOT_STARTED.items():
            self.assertTrue(why.strip(), f"{clause_id}: 「무엇이 없는가」가 비었다.")
