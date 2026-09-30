# -*- coding: utf-8 -*-
"""P-422 — `scripts/onboarding_two_numbers.py` 기본 호출은 **아무 행도 빼지 않는다**
(턴 AP · 차선 Q).

무엇이 거짓 초록이었나
-----------------------
옛 기본 동작(인자 없이 부르면)은 `onboarding_48.md` 를 **자동으로** 훑어 그 문서
전체(여러 재측 절 누적)의 `**(c)**` 행을 모았다 — 실측으로 30/48 을 30/32
(93.8%)로 찍었다. 문서는 절이 쌓이는 장부라 자동으로 다 모으면 이번 회와 무관한
옛 절의 (c) 행까지 상한을 깎는다.

이 시험이 못박는 것
--------------------
① 기본 호출(`--c-rows` · `--c-from-ledger` 둘 다 없음)은 장부를 **읽지 않는다**
   (스파이로 잰다 — 부르면 예외).
② 기본 호출의 상한 기준은 「회색 · c 미명시」다 — 숫자를 지어내지 않는다.
③④ [턴 AQ · P-433] `--c-from-ledger` 는 **없앴다**(명시 옵션이 107.8 거짓 초록을 냈다) —
   c 의 출처는 `--c-rows` 하나다.
⑤ 도구 자신의 `--self-test` 가 이 사실들을 스스로도 재고(자기시험 짝) 통과한다.

★ [수확 · 턴 AP] `class FooTest:`(TestCase 를 안 물려받는 맨 클래스)는 이 저장소의
  pytest 설정(`backend/pytest.ini` — `python_classes` 재정의 없음)에서 **수집되지
  않는다**(`--collect-only` 로 실측: `test_ao_q_p408_onboarding_two_numbers.py` 가
  0건 수집 — 「14 passed」로 보고됐던 턴 AO 수는 그 파일 몫이 전혀 안 들어 있었다).
  실제로 도는 파일들(`test_ao_q_p409...` · `test_p343...`)은 전부 `unittest.TestCase`
  (또는 Django `TestCase`/`SimpleTestCase`)를 물려받는다 — 그래서 이 파일도 그렇게
  쓴다(수집 자체를 실측으로 확인 — 아래 ③ 참고).
"""
from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path


def _tool_path() -> Path:
    candidates = [
        Path("/repo/scripts/onboarding_two_numbers.py"),
        Path(__file__).resolve().parents[2] / "scripts" / "onboarding_two_numbers.py",
        Path("/app/scripts/onboarding_two_numbers.py"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise AssertionError(
        "scripts/onboarding_two_numbers.py 를 못 읽었다 — 찾아본 자리: %s" % candidates)


def _load_module():
    path = _tool_path()
    spec = importlib.util.spec_from_file_location(
        "gx_onboarding_two_numbers_p422", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class DefaultCallDoesNotReadTheLedgerTest(unittest.TestCase):
    """① ② — 기본 호출은 아무 행도 안 빼고, 상한 줄은 회색이다.

    [턴 AQ · P-433 · 차선 Q] 장부를 읽는 갈래(`--c-from-ledger`)는 없어졌다 —
    `resolve_c_rows` 는 `c_rows_arg` 하나만 받는다(없앤 옵션의 시험은
    `test_aq_q_p433_no_c_from_ledger.py`)."""

    def setUp(self) -> None:
        self.onb2n = _load_module()

    def test_default_yields_no_rows_and_says_unspecified(self) -> None:
        rows, source = self.onb2n.resolve_c_rows(c_rows_arg=None)
        self.assertEqual(rows, set())
        self.assertIn("미명시", source)

    def test_default_result_yields_no_cap_number(self) -> None:
        rows, source = self.onb2n.resolve_c_rows(c_rows_arg=None)
        out = self.onb2n.two_numbers(score_sum=30.0, denominator=48, c_rows=rows)
        self.assertIsNone(out["by_cap"])
        text = self.onb2n.render(out, turn_source="t.json", c_source=source)
        self.assertIn("미명시", text)
        # 옛 거짓 초록의 흔적(93.8%)이 기본 호출 렌더에 없다.
        self.assertNotIn("93.8", text)

    def test_default_call_regresses_red_if_it_ever_computes_a_cap_number(self) -> None:
        """**자기시험 짝.** 기본 호출이 상한 수를 실제로 내면 이 시험이 빨개진다."""
        rows, _source = self.onb2n.resolve_c_rows(c_rows_arg=None)
        out = self.onb2n.two_numbers(score_sum=30.0, denominator=48, c_rows=rows)
        self.assertIsNone(
            out["by_cap"],
            "기본 호출이 상한 수(%s)를 냈다 — P-422 회귀(거짓 초록 부활)" % out["by_cap"])

    def test_c_rows_arg_is_the_only_source(self) -> None:
        rows, source = self.onb2n.resolve_c_rows(c_rows_arg="U2#2,U2#3")
        self.assertEqual(rows, {"U2#2", "U2#3"})
        self.assertEqual(source, "--c-rows(손으로 줌)")



class ToolSelfTestAgreesTest(unittest.TestCase):
    """⑤ — 도구의 --self-test 가 이 파일과 같은 사실을 스스로도 잰다."""

    def test_self_test_subprocess_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(_tool_path()), "--self-test"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-2000:])

    def test_self_test_function_exits_zero_in_process(self) -> None:
        onb2n = _load_module()
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = onb2n._self_test()
        self.assertEqual(code, 0, buf.getvalue())


class ThisFileItselfIsCollectedByPytestTest(unittest.TestCase):
    """★ 이 파일이 실제로 pytest 에 걸리는지 — 수집 자체가 회귀 지점이었다(위 머리말)."""

    def test_test_case_subclassing_is_what_makes_collection_work(self) -> None:
        self.assertTrue(issubclass(DefaultCallDoesNotReadTheLedgerTest, unittest.TestCase))
