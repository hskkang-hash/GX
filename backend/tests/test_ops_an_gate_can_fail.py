# -*- coding: utf-8 -*-
"""`scripts/verify_spec_ops.py` 의 짝(턴 AO · 차선 N3 몫) — **이 턴이 더한 판정식**
(`judge_title_parts` · `/api/dsm/ops/` 경로 접두어)을 스스로 망가뜨려 실패를 본다.

`test_verify_spec_ops_gate_can_fail.py`(턴 AM 소유)와 겹치지 않는다 — 그 파일은
`judge_gate_tests`·`judge_evidence`(500 응답·빈 증거)를 망가뜨리고, 이 파일은
**이번 턴이 새로 얹은 문**(title_parts 표의 빈 칸 판정)만 겨눈다(D-212 — 같은
자리를 두 번 재지 않는다).
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


_GOOD = {
    "id": "O-01", "measured_at": "2026-09-30T00:00:00+00:00",
    "measured_by": "django_test_client", "test": "tests.test_ops_an.X.y",
    "request": {"method": "POST", "path": "/api/dsm/ops/tenants", "body": {}},
    "response": {"status": 200, "body": {}}, "what": "실측",
    "title_parts": [
        {"part": "테넌트 생성", "where": "tenant_code", "status": "measured"},
        {"part": "초기 관리자", "where": "admin_username", "status": "measured"},
    ],
}


class TheSelfTestCanFail(SimpleTestCase):
    def test_self_test_passes_as_built(self) -> None:
        self.assertEqual(0, _gate().self_test())

    def test_self_test_fails_when_an_open_title_part_is_waved_through(self) -> None:
        """★ title_parts 안에 「없음」으로 시작하는 열린 행이 있는데도 그 절을
        닫힘으로 읽으면 — 반쪽이 승격 표에 오른다. P-417 이 막으려는 바로 그 사고."""
        g = _gate()
        real = g.judge_title_parts

        def waves_open_rows(clause_id, payload):
            code, verdict = real(clause_id, payload)
            if code == g.EXIT_FAIL and "반쪽" in verdict:
                return g.EXIT_OK, "열린 행도 닫힘으로 본다(망가진 판정)"
            return code, verdict

        g.judge_title_parts = waves_open_rows
        try:
            broken = dict(_GOOD, title_parts=[
                {"part": "테넌트 생성", "where": "x", "status": "없음 — 아직"}])
            code, _verdict = g.judge_evidence("O-01", broken)
        finally:
            g.judge_title_parts = real
        self.assertEqual(g.EXIT_OK, code,
                         "이 시험은 판정식을 일부러 망가뜨려 그 망가짐이 통과로 "
                         "새는지 보인다 — 아래에서 원래 판정식으로 같은 입력을 "
                         "다시 재서 실패(FAIL)가 나오는지가 진짜 단언이다")
        code2, verdict2 = g.judge_evidence("O-01", broken)
        self.assertEqual(g.EXIT_FAIL, code2,
                         "열린 title_parts 행이 있는 증거를 원래 판정식이 통과시켰다")
        self.assertIn("반쪽", verdict2)

    def test_self_test_fails_when_title_parts_is_missing_entirely(self) -> None:
        """★ title_parts 표가 아예 없는 증거를 닫힘으로 읽으면 — "제목이 부르는 것
        ↔ 있는 것" 대조 자체가 없는 절이 승격 표에 오른다."""
        g = _gate()
        no_parts = {k: v for k, v in _GOOD.items() if k != "title_parts"}
        code, verdict = g.judge_evidence("O-01", no_parts)
        self.assertEqual(g.EXIT_FAIL, code, "title_parts 없는 증거가 통과했다")
        self.assertIn("title_parts", verdict)

    def test_self_test_fails_when_old_ops_prefix_is_accepted(self) -> None:
        """★ [턴 AM → AO] 경로 접두어를 실재(`/api/dsm/ops/`)로 고쳤다 — 옛 자리
        (`/api/ops/`, 그날 아직 없던 앱을 가정한 자리)를 다시 받아 주면 실재 라우트가
        아닌 문서를 잰 증거도 통과한다."""
        g = _gate()
        old_prefix = dict(_GOOD, request={"method": "POST", "path": "/api/ops/tenants", "body": {}})
        code, verdict = g.judge_evidence("O-01", old_prefix)
        self.assertEqual(g.EXIT_FAIL, code, "옛 접두어(/api/ops/)가 실재 경로처럼 통과했다")

    def test_closed_eight_have_no_open_title_part_rows(self) -> None:
        """★ N3 가 닫았다고 주장하는 여덟 — 실제 증거 파일을 읽어 title_parts 에
        열린 행이 0인지 재확인한다(자기시험이 아니라 실제 파일 대조)."""
        import json

        g = _gate()
        root = Path(__file__).resolve().parents[2]
        evidence_dir = root / "docs" / "agent" / "evidence" / "SPEC"
        for clause_id in g.CLOSED_CLAUSES:
            path = evidence_dir / ("%s.json" % clause_id)
            self.assertTrue(path.is_file(), f"{clause_id}: 증거 파일이 없다")
            payload = json.loads(path.read_text(encoding="utf-8"))
            code, verdict = g.judge_evidence(clause_id, payload)
            self.assertEqual(g.EXIT_OK, code, f"{clause_id}: {verdict}")
