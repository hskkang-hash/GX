# -*- coding: utf-8 -*-
"""P-431 — 증거 표 분리: 사람 표 `<id>.retro.md` · 기계 표 `<id>.json` (턴 AQ · 차선 Q).

못박는 것
① 게이트(`verify_spec_title_parts.py`)와 공용 읽개(`_retro_table.py`)는 표를 **`.retro.md`
   에서만** 읽는다 — json 에 `title_parts`·`retro*` 가 남아 있어도 버린다. `.retro.md` 가
   없으면 「표 없음 → 회색」(옛 json 표로 떨어지지 않는다).
② 게이트 1행 「사람 표 diff 0」 — 정적(소스의 `.retro` 쓰기)·런타임(가드) 짝이 자기시험에
   있고, 그 판정식을 망가뜨리면 자기시험이 빨강이 된다.
③ `common.evidence_guard` 는 `allow_evidence_writes` 안에서도 `.retro.md` 쓰기를 거절한다.
④ 지금 `backend/tests`·`scripts` 소스에 `.retro` 쓰기 호출이 0곳이다.

이 시험은 `.retro.md` 를 **쓰지 않는다**(파일 없이 순수 함수 · 가짜 읽개로 잰다).

캐시 처리: 해당 없음 — HTTP 를 안 두드리고 DB 도 안 쓴다(`SimpleTestCase`).
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase


def _scripts_dir() -> Path:
    here = Path(__file__).resolve()
    for cand in (Path("/repo/scripts"), here.parent.parent.parent / "scripts"):
        if (cand / "_retro_table.py").is_file():
            return cand
    raise AssertionError("scripts/_retro_table.py 를 못 찾았다")


def _mods():
    d = str(_scripts_dir())
    if d not in sys.path:
        sys.path.insert(0, d)
    import _retro_table  # noqa: PLC0415
    import verify_spec_title_parts  # noqa: PLC0415
    return _retro_table, verify_spec_title_parts


_TABLE = {"id": "X-01", "title_parts": [
    {"part": "a", "where": "screen::x · GET /api/x", "status": "measured"}],
    "retro": "사람 확인"}
_JSON = {"id": "X-01", "request": {}, "response": {}, "what": "w",
         "title_parts": [{"part": "쓰개", "where": "", "status": "없음"}],
         "retro": "쓰개가 덮은 값", "retro_ap": "x", "title_parts_note": "n"}


class ReaderReadsOnlyRetro(SimpleTestCase):
    def test_json_human_keys_are_dropped_and_retro_wins(self) -> None:
        rt, _g = _mods()
        with mock.patch.object(rt, "load_retro", return_value=_TABLE):
            out = rt.overlay(dict(_JSON), "X-01")
        self.assertEqual(_TABLE["title_parts"], out["title_parts"])
        self.assertEqual("사람 확인", out["retro"])
        self.assertNotIn("retro_ap", out)
        self.assertEqual("w", out["what"])

    def test_missing_retro_means_no_table_not_old_json(self) -> None:
        rt, g = _mods()
        with mock.patch.object(rt, "load_retro", return_value=None):
            out = rt.overlay(dict(_JSON), "X-01")
        self.assertNotIn("title_parts", out)
        rep = g.classify_payload("X-01", out)
        self.assertEqual(("grey", "legacy_no_table"), (rep["verdict"], rep["bucket"]))

    def test_open_row_in_retro_is_red_even_if_json_was_clean(self) -> None:
        rt, g = _mods()
        clean_json = dict(_JSON, title_parts=[{"part": "a", "where": "b", "status": "measured"}])
        half = {"id": "X-01", "title_parts": [{"part": "a", "where": "b", "status": "부분(화면 없음)"}]}
        with mock.patch.object(rt, "load_retro", return_value=half):
            out = rt.overlay(clean_json, "X-01")
        self.assertEqual("red", g.classify_payload("X-01", out)["verdict"])

    def test_parse_requires_exactly_one_block_and_matching_id(self) -> None:
        rt, _g = _mods()
        fence = "`" * 3
        body = "머리말" + chr(10) + fence + "json" + chr(10) + '{"id": "X-01", "title_parts": []}' \
            + chr(10) + fence + chr(10)
        self.assertIsNotNone(rt.parse_retro_md(body, "X-01")[0])
        self.assertIsNone(rt.parse_retro_md(body, "X-02")[0])
        self.assertIsNone(rt.parse_retro_md(body + body, "X-01")[0])


class HumanTableDiffZeroRow(SimpleTestCase):
    def test_self_test_passes_as_built(self) -> None:
        _rt, g = _mods()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, g.self_test())

    def test_self_test_fails_when_static_scan_sees_nothing(self) -> None:
        _rt, g = _mods()
        with mock.patch.object(g, "scan_retro_writes", return_value=[]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, g.self_test(), "정적 짝이 눈을 감아도 자기시험이 초록이다")

    def test_self_test_fails_when_runtime_probe_always_ok(self) -> None:
        _rt, g = _mods()
        with mock.patch.object(g, "probe_guard", return_value={"verdict": "ok", "detail": "x"}), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, g.self_test(), "런타임 짝이 늘 ok 여도 자기시험이 초록이다")

    def test_self_test_fails_when_screen_citation_always_ok(self) -> None:
        """[턴 AQ] 「화면 인용 = 화면 실재」 짝 — 없는 토큰을 적어도 ok 로 읽으면 빨강."""
        _rt, g = _mods()
        fake = {"verdict": "ok", "n_cited": 0, "n_found": 0, "missing": [], "uncited": [],
                "detail": "x"}
        with mock.patch.object(g, "judge_screen_citations", return_value=fake), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, g.self_test(), "화면에 없는 인용을 통과시켜도 자기시험이 초록이다")

    def test_real_guard_refuses_retro_even_when_allowed(self) -> None:
        _rt, g = _mods()
        from common import evidence_guard

        self.assertEqual("ok", g.probe_guard(evidence_guard)["verdict"])
        with evidence_guard.allow_evidence_writes("P-431 시험 — json 은 열리는지 대조"):
            self.assertIsNone(evidence_guard.blocked_reason("docs/agent/evidence/SPEC/X-01.json"))

    def test_real_sources_have_zero_retro_writes(self) -> None:
        _rt, g = _mods()
        sources = g.collect_scan_sources()
        if not sources:
            self.skipTest("이 환경에서 backend/tests·scripts 소스를 못 읽었다")
        self.assertEqual([], g.scan_retro_writes(sources))
