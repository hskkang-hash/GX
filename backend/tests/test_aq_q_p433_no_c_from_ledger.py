# -*- coding: utf-8 -*-
"""P-433 — `scripts/onboarding_two_numbers.py` 에서 `--c-from-ledger` 를 **없앴다** (턴 AQ · 차선 Q).

턴 AP: 기본 호출을 막으니 명시 옵션 `--c-from-ledger` 가 107.8 이라는 새 거짓 초록을
냈다(V 가 `--c-rows` 로 막았다). 옵션 자체를 없앴다 — 부르면 argparse 가 오류(exit 2)를
내야 한다. c 의 출처는 `--c-rows` 하나다.

캐시 처리: 해당 없음 — HTTP 를 안 두드리고 DB 도 안 쓴다(순수 도구 · `unittest.TestCase`).
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import sys
import unittest
from pathlib import Path


def _tool_path() -> Path:
    for path in (Path("/repo/scripts/onboarding_two_numbers.py"),
                 Path(__file__).resolve().parents[2] / "scripts" / "onboarding_two_numbers.py"):
        if path.is_file():
            return path
    raise AssertionError("scripts/onboarding_two_numbers.py 를 못 찾았다")


def _load():
    spec = importlib.util.spec_from_file_location("gx_onb2n_p433", str(_tool_path()))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CFromLedgerIsGone(unittest.TestCase):
    def test_c_from_ledger_is_an_argparse_error(self) -> None:
        mod = _load()
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            mod.main(["--c-from-ledger"])
        self.assertEqual(2, cm.exception.code)
        self.assertIn("--c-from-ledger", err.getvalue())

    def test_subprocess_exit_code_is_2(self) -> None:
        r = subprocess.run([sys.executable, str(_tool_path()), "--c-from-ledger"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=30)
        self.assertEqual(2, r.returncode, (r.stdout + r.stderr)[-1000:])

    def test_resolve_has_no_ledger_branch(self) -> None:
        mod = _load()
        self.assertNotIn("c_from_ledger", mod.resolve_c_rows.__code__.co_varnames)
        self.assertFalse(hasattr(mod, "c_rows_from_markdown"),
                         "장부 표를 읽는 함수가 남아 있다 — 옵션만 지우고 길은 남겼다")

    def test_tool_self_test_passes(self) -> None:
        mod = _load()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, mod._self_test())
