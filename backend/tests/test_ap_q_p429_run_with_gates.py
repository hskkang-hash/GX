# -*- coding: utf-8 -*-
"""P-429 — 새 실행기 `scripts/run_with_gates.py` (턴 AP · 차선 Q).

`.env.gates` 를 이 프로세스에만 싣고 `verify_route_alive.expand_env_refs` 로
`${...}` 를 펼친 뒤 인자로 받은 판정기를 그대로 부른다. 값은 화면에도 argv 에도
안 찍는다.

이 시험이 못박는 것
--------------------
① `${A}` 처럼 **같은 파일 안의 앞줄**을 가리키는 참조가 펼쳐진다(셸 소싱과 같은 순서).
② 못 찾는 참조는 지어내지 않고 `${...}` 그대로 남는다.
③ **자기시험 짝** — 펼친 뒤에도 `${` 가 남으면 `unresolved_names()` 가 잡는다
   (이것이 `main()` 을 빨강으로 세우는 그 잣대다).
④ `main()` 을 실제로 끝까지 돌려서: (a) 다 펼쳐지면 자식이 펼쳐진 값을 **환경으로**
   받고 자식의 종료 코드가 그대로 나온다, (b) 못 펼친 이름이 남으면 자식을 **부르지
   않고** 1 을 내며 찍는 줄에 값이 없다(이름만 있다).
⑤ 도구 자신의 `--self-test` 가 통과한다.
"""
from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path


def _tool_path(name: str) -> Path:
    candidates = [
        Path("/repo/scripts/%s" % name),
        Path(__file__).resolve().parents[2] / "scripts" / name,
        Path("/app/scripts/%s" % name),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise AssertionError("scripts/%s 를 못 읽었다 — 찾아본 자리: %s" % (name, candidates))


def _load_module():
    path = _tool_path("run_with_gates.py")
    spec = importlib.util.spec_from_file_location("gx_run_with_gates_p429", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ExpansionOrderAndMissingRefsTest(unittest.TestCase):
    """① ② — 앞줄이 뒷줄을 채우고, 못 찾는 참조는 지어내지 않는다."""

    def setUp(self) -> None:
        self.rwg = _load_module()

    def test_earlier_line_fills_a_later_reference(self) -> None:
        env = self.rwg.parse_env_text(
            "GX_SEED_ROLE_PASSWORD=literal-secret\n"
            "GX_ROUTE_PASSWORD=${GX_SEED_ROLE_PASSWORD}\n")
        self.assertEqual(env["GX_ROUTE_PASSWORD"], "literal-secret")

    def test_missing_reference_is_left_as_is_not_fabricated(self) -> None:
        env = self.rwg.parse_env_text("B=${GX_NOT_DEFINED_ANYWHERE_P429}\n")
        self.assertEqual(env["B"], "${GX_NOT_DEFINED_ANYWHERE_P429}")

    def test_hash_inside_a_value_is_not_truncated(self) -> None:
        env = self.rwg.parse_env_text("PW=abc#def\n")
        self.assertEqual(env["PW"], "abc#def")


class SelfTestPairIfExpansionLeavesDollarBraceRedTest(unittest.TestCase):
    """③ — 자기시험 짝: 펼친 뒤 ${ 가 남으면 unresolved_names() 가 빨강 조건을 낸다."""

    def setUp(self) -> None:
        self.rwg = _load_module()

    def test_unresolved_braces_are_detected(self) -> None:
        env = self.rwg.parse_env_text("B=${GX_NOT_DEFINED_ANYWHERE_P429}\n")
        self.assertEqual(self.rwg.unresolved_names(env), ["B"])

    def test_fully_resolved_env_has_no_unresolved_names(self) -> None:
        env = self.rwg.parse_env_text("A=1\nB=${A}-2\n")
        self.assertEqual(self.rwg.unresolved_names(env), [])

    def test_unresolved_names_never_returns_the_value_itself(self) -> None:
        env = self.rwg.parse_env_text("B=${GX_NOT_DEFINED_ANYWHERE_P429}\n")
        names = self.rwg.unresolved_names(env)
        self.assertEqual(names, ["B"])
        self.assertNotIn("${GX_NOT_DEFINED_ANYWHERE_P429}", names)


class MainRunsTheGivenGateWithExpandedEnvTest(unittest.TestCase):
    """④ — main() 을 실제로 끝까지 돌린다: 성공 경로와 빨강 경로 둘 다."""

    def setUp(self) -> None:
        self.rwg = _load_module()

    def _write_env(self, tmp_path: Path, text: str) -> None:
        (tmp_path / ".env.gates").write_text(text, encoding="utf-8")

    def test_child_receives_expanded_value_via_environment_and_exit_code_passes_through(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._write_env(
                tmp, "GX_SEED_ROLE_PASSWORD=literal-secret-xyz\n"
                    "GX_ROUTE_PASSWORD=${GX_SEED_ROLE_PASSWORD}\n")
            child = tmp / "child.py"
            child.write_text(
                "import os, sys\n"
                "v = os.environ.get('GX_ROUTE_PASSWORD')\n"
                "v = '<missing>' if v is None else v\n"
                "sys.stdout.write('SAW=' + v + '\\n')\n"
                "sys.exit(7)\n",
                encoding="utf-8")
            orig_root = self.rwg.ROOT
            orig_env = dict(__import__("os").environ)
            try:
                self.rwg.ROOT = tmp
                import os
                for k in ("GX_SEED_ROLE_PASSWORD", "GX_ROUTE_PASSWORD"):
                    os.environ.pop(k, None)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = self.rwg.main(["--", sys.executable, str(child)])
                self.assertEqual(rc, 7)  # 자식의 종료 코드가 그대로 나온다
                printed = buf.getvalue()
                self.assertNotIn("literal-secret-xyz", printed)  # 값이 이 실행기 출력에 없다
            finally:
                self.rwg.ROOT = orig_root
                import os
                os.environ.clear()
                os.environ.update(orig_env)

    def test_unresolved_reference_stops_before_calling_the_child(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._write_env(tmp, "B=${GX_NOT_DEFINED_ANYWHERE_P429}\n")
            marker = tmp / "should_not_run.txt"
            child = tmp / "child.py"
            child.write_text(
                "from pathlib import Path\n"
                "Path(%r).write_text('ran')\n" % str(marker),
                encoding="utf-8")
            orig_root = self.rwg.ROOT
            orig_env = dict(__import__("os").environ)
            try:
                self.rwg.ROOT = tmp
                import os
                os.environ.pop("B", None)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = self.rwg.main(["--", sys.executable, str(child)])
                self.assertEqual(rc, 1)
                self.assertFalse(marker.exists(), "펼치지 못한 채로 자식을 불렀다")
                printed = buf.getvalue()
                self.assertIn("B", printed)  # 이름은 찍는다
                self.assertNotIn("${GX_NOT_DEFINED_ANYWHERE_P429}", printed)  # 값 형태는 안 찍는다
            finally:
                self.rwg.ROOT = orig_root
                import os
                os.environ.clear()
                os.environ.update(orig_env)


class ToolSelfTestPassesTest(unittest.TestCase):
    """⑤ — 도구 자신의 --self-test."""

    def test_self_test_subprocess_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(_tool_path("run_with_gates.py")), "--self-test"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-2000:])

    def test_self_test_function_exits_zero_in_process(self) -> None:
        rwg = _load_module()
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = rwg._self_test()
        self.assertEqual(code, 0, buf.getvalue())
