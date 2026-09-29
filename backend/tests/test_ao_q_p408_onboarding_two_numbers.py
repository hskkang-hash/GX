# -*- coding: utf-8 -*-
"""P-408 — `scripts/onboarding_two_numbers.py` 짝 시험 (턴 AO · 차선 Q).

순수 시험(`test_p343_third_condition_wiring.py` 와 같은 모양) — Django 도 DB 도
필요 없다. 이 도구의 핵심 함수 셋(`c_rows_from_markdown` · `parse_c_rows_arg` ·
`two_numbers`)을 직접 부른다.

이 시험이 못박는 것
--------------------
① `onboarding_48.md` 의 `**(c)**` 표에서 행 id 를 뽑는다 — 갈래 칸이 아니면(비고에
   "(c)" 라는 낱말이 있어도) 안 센다. 같은 행이 여러 절에 반복돼도 한 번만 센다.
② 두 수의 **분자는 하나다** — 48 기준이든 상한 기준이든 N 이 갈리지 않는다.
   (c 를 바꿔 상한만 낮아지고 점수가 따라 오르는 착시를 만들지 않는다.)
③ c=0(상한 표를 못 찾음)이면 ②(상한 기준)를 **지어내지 않는다** — `by_cap`
   이 `None` 이고 사유 문장이 남는다.
④ 회차 JSON 의 48행에 없는 c 행 이름(오타·지난 회차 잔재)은 상한 계산에서
   빠지고 따로 보고된다 — 조용히 상한을 깎지 않는다.
⑤ `--self-test` 가 이 파일과 **같은 사실**을 잰다(도구 자신의 자기 시험도 통과).
"""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
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
        "gx_onboarding_two_numbers_p408", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CRowsFromMarkdownTest:
    """① — 표 갈래 칸만 센다."""

    def setup_method(self) -> None:
        self.onb2n = _load_module()

    def test_only_the_gallae_column_counts(self) -> None:
        md = (
            "| U1#4 `/x` | 증거 | **(c)** | 비고 |\n"
            "| U1#9 `/y` | 증거 | **(a)** | (c) 라는 낱말이 비고에 있어도 갈래 칸이 아니면 "
            "안 센다 |\n"
        )
        assert self.onb2n.c_rows_from_markdown(md) == {"U1#4"}

    def test_repeated_row_across_sections_counts_once(self) -> None:
        md = (
            "| U1#4 `/x` | 첫 절 | **(c)** | 비고 |\n"
            "| U1#4 `/x` | 재측 절에도 또 나온다 | **(c)** | 비고 |\n"
            "| U2#3 `/z` | 증거 | **(c)** | 비고 |\n"
        )
        assert self.onb2n.c_rows_from_markdown(md) == {"U1#4", "U2#3"}

    def test_no_c_rows_is_empty_set_not_an_error(self) -> None:
        md = "| U1#4 `/x` | 증거 | **(a)** | 비고 |\n"
        assert self.onb2n.c_rows_from_markdown(md) == set()


class ParseCRowsArgTest:
    def setup_method(self) -> None:
        self.onb2n = _load_module()

    def test_splits_and_trims_commas(self) -> None:
        assert (self.onb2n.parse_c_rows_arg(" U1#2, U2#3 ,, U3#9")
               == {"U1#2", "U2#3", "U3#9"})

    def test_empty_string_is_empty_set(self) -> None:
        assert self.onb2n.parse_c_rows_arg("") == set()


class TwoNumbersTest:
    """② ③ ④ — 분자는 하나 · 상한을 지어내지 않는다 · 모르는 행은 뺀다."""

    def setup_method(self) -> None:
        self.onb2n = _load_module()

    def test_numerator_is_the_same_for_both_numbers(self) -> None:
        out = self.onb2n.two_numbers(
            score_sum=30.0, denominator=48,
            c_rows={"U1#4", "U1#8", "U1#11"},
            canon_rows={"U1#4", "U1#8", "U1#11", "U1#2"})
        assert out["n"] == 30.0
        assert out["by_48"] == "30/48"
        assert out["cap_denominator"] == 48 - 3
        assert out["by_cap"] == "30/45"

    def test_c_zero_does_not_fabricate_the_capped_number(self) -> None:
        out = self.onb2n.two_numbers(score_sum=10.0, denominator=48, c_rows=set())
        assert out["by_cap"] is None
        assert "못 찾았다" in out["cap_undefined_why"]

    def test_unknown_c_row_names_are_excluded_and_reported(self) -> None:
        out = self.onb2n.two_numbers(
            score_sum=30.0, denominator=48,
            c_rows={"U1#4", "U9#99"}, canon_rows={"U1#4", "U1#8"})
        assert out["c"] == 1
        assert out["c_rows_unknown"] == ["U9#99"]

    def test_denominator_collapsing_to_zero_does_not_fabricate(self) -> None:
        rows = {"A#1", "A#2", "A#3", "A#4", "A#5", "A#6"}
        out = self.onb2n.two_numbers(score_sum=5.0, denominator=6, c_rows=rows,
                                     canon_rows=rows)
        assert out["by_cap"] is None


class SelfTestAgreesWithThisFileTest:
    """⑤ — 도구의 `--self-test` 가 통과한다(같은 사실을 자기 스스로도 잰다)."""

    def test_self_test_subprocess_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(_tool_path()), "--self-test"],
            capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, (result.stdout + result.stderr)[-2000:]

    def test_self_test_function_exits_zero_in_process(self) -> None:
        onb2n = _load_module()
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = onb2n._self_test()
        assert code == 0, buf.getvalue()


class RendersHumanReadableLinesTest:
    """찍는 문장에 둘 다 들어 있는가(한쪽만 찍는 경로가 없다는 것의 문자열 판)."""

    def test_render_includes_both_numbers_when_c_is_known(self) -> None:
        onb2n = _load_module()
        out = onb2n.two_numbers(score_sum=30.0, denominator=48,
                                c_rows={"U1#4"}, canon_rows={"U1#4", "U1#8"})
        text = onb2n.render(out, turn_source="t.json", c_source="onboarding_48.md")
        assert "48 기준" in text and "30/48" in text
        assert "상한 기준" in text and "30/47" in text
