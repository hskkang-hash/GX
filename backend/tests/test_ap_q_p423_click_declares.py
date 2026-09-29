# -*- coding: utf-8 -*-
"""P-423 — `verify_click_completes.py` 의 「누를 자리 미선언」 9행 중, 차선 L 이
`data-gx` 를 새로 단 5행(U5#1 · U5#4 · U5#5 · U3#16 · U5#10)에 **누를 자리·술어를
더한다** (턴 AP · 차선 Q). 선언할 자리가 없는 나머지 4행(U1#4 · U3#14 · U4#9 ·
U6#14 — 결정 잠금)은 그대로 둔다.

L 의 표(`docs/agent/checkpoints/turn-ap/L.md` §1-A)가 단 이름:
    U5#1  `people-create-submit`(+ `people-create-outcome`)
    U5#4  `camera-import-dryrun` / `camera-import-apply`
    U5#5  `camera-address-row-start` / `camera-address-row-submit`
    U3#16 `prefs-save-submit`
    U5#10 `notify-rule-channel` (+ `data-gx-channel` 속성 — 클릭 자리는 U5#9 재사용)

이 시험이 못박는 것
--------------------
① 5행 전부 `control` 이 더 이상 `None` 이 아니고, L 이 단 정확한 `gx` 이름을 쓴다.
② 4행(U1#4·U3#14·U4#9·U6#14)은 그대로 `control=None` 이다(회귀 방지 — 건드리지
   않았다).
③ `btn(name, gx=...)` 이 `gx` 를 담고, `find_control()` 이 **`gx` 선택자를 먼저**
   본다(텍스트만으로 같은 글자 단추 둘을 못 가르는 문제의 그 고침).
④ `gx` 없는 기존 컨트롤(`find_control` 의 텍스트 갈래)은 이 변경으로 안 갈린다.
⑤ `prepare_steps()` 의 새 갈래 `button_prepare`(=`press()`)와 `fill_label()` 이
   실제로 단추를 누르고 라벨로 글상자를 채운다.
⑥ 상태를 바꾸는 클릭(POST/PUT)인 5행 전부 `revert` 가 선언돼 있다 — 이 파일
   자신의 `--self-test` 가 그 빠짐을 잡는 자기시험이고, 그 시험이 통과한다
   (되돌림 선언 없음 자기시험 회귀 방지 — 이 5행을 추가하며 처음 걸렸던 자리).
"""
from __future__ import annotations

import ast
import importlib.util
import re
import subprocess
import sys
import unittest
from pathlib import Path


def _tool_path() -> Path:
    candidates = [
        Path("/repo/scripts/verify_click_completes.py"),
        Path(__file__).resolve().parents[2] / "scripts" / "verify_click_completes.py",
        Path("/app/scripts/verify_click_completes.py"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise AssertionError(
        "scripts/verify_click_completes.py 를 못 읽었다 — 찾아본 자리: %s" % candidates)


def _load_module():
    path = _tool_path()
    #: probe_marks 를 같은 폴더에서 임포트하므로 sys.path 에 scripts/ 를 넣어 둔다.
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("gx_verify_click_completes_p423", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _flows_by_key(mod):
    return {f["key"]: f for f in mod.FLOWS}


def _driver_functions(*names):
    """`find_control()`/`prepare_steps()` 는 **바깥 모듈의 top-level 함수가 아니다.**

    `verify_click_completes.py` 의 머리말대로 그 둘은 `DRIVER`(gx-shell 안에서
    **딴 프로세스**로 도는 문자열 소스, `verify_click_completes.py:2275` 부근)
    안에만 있다(`ast.parse` 로 실측: 바깥 모듈에 `find_control`/`prepare_steps`
    가 top-level 함수로 없다 — `FLOWS`/`F`/`btn`/`press`/`fill_label` 은 있다).
    실제로 눌러야 뜻이 있는 브라우저 부트스트랩(`sync_playwright` 실행 등)까지
    통째로 실행하지 않도록, `DRIVER` 문자열을 AST 로 파싱해 원하는 함수 정의만
    뽑아 **격리된 이름공간**에 실행한다.
    """
    mod = _load_module()
    src = mod.DRIVER
    tree = ast.parse(src)
    ns = {"re": re}
    wanted = set(names)
    found = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            segment = ast.get_source_segment(src, node)
            exec(compile(segment, "<driver:%s>" % node.name, "exec"), ns)  # noqa: S102
            found.add(node.name)
    missing = wanted - found
    if missing:
        raise AssertionError(
            "DRIVER 문자열 안에서 못 찾은 함수: %s — 드라이버 구조가 바뀌었을 수 있다"
            % missing)
    return ns


class DeclaredRowsGetARealControlTest(unittest.TestCase):
    """① — L 이 단 5행이 control=None 을 벗어나고 정확한 gx 이름을 쓴다."""

    EXPECTED_GX = {
        "U5#1": "people-create-submit",
        "U5#4": "camera-import-apply",
        "U5#5": "camera-address-row-submit",
        "U3#16": "prefs-save-submit",
    }

    def setUp(self) -> None:
        self.flows = _flows_by_key(_load_module())

    def test_five_rows_have_a_control(self) -> None:
        for key in ("U5#1", "U5#4", "U5#5", "U3#16", "U5#10"):
            with self.subTest(key=key):
                self.assertIsNotNone(self.flows[key]["control"], "%s 의 control 이 여전히 None" % key)

    def test_control_gx_matches_lanes_l_table(self) -> None:
        for key, gx in self.EXPECTED_GX.items():
            with self.subTest(key=key):
                self.assertEqual(self.flows[key]["control"].get("gx"), gx)

    def test_u5_10_reuses_u5_9_toggle_and_checks_the_channel_attribute(self) -> None:
        u5_9 = self.flows["U5#9"]
        u5_10 = self.flows["U5#10"]
        self.assertEqual(u5_10["control"]["name"], u5_9["control"]["name"])
        self.assertEqual(u5_10["attr_check"], '[data-gx="notify-rule-channel"]')

    def test_five_rows_declare_a_screen_route(self) -> None:
        for key in ("U5#1", "U5#4", "U5#5", "U3#16", "U5#10"):
            with self.subTest(key=key):
                self.assertIsNotNone(self.flows[key]["screen"])


class UndeclaredRowsAreUntouchedTest(unittest.TestCase):
    """② — 결정 잠금 4행은 손대지 않았다(회귀 방지).

    U1#4·U3#14·U4#9 는 화면 자체가 없어(`control=None`) 그대로다. U6#14 는 기계
    행이라 `control=api()` 를 이미 갖고 있었다(화면이 없어 `data-gx` 를 못 단다는
    것이지 컨트롤이 없다는 뜻이 아니다 — L.md §1-B) — 이 행은 **콜·상태가 종전과
    같은지**로 손대지 않았음을 확인한다.
    """

    def setUp(self) -> None:
        self.flows = _flows_by_key(_load_module())

    def test_three_screenless_rows_still_have_no_control(self) -> None:
        for key in ("U1#4", "U3#14", "U4#9"):
            with self.subTest(key=key):
                self.assertIsNone(self.flows[key]["control"], "%s 가 손댄 흔적이 있다" % key)

    def test_u6_14_machine_row_unchanged(self) -> None:
        u6_14 = self.flows["U6#14"]
        self.assertEqual(u6_14["control"], {"kind": "api"})
        self.assertEqual(u6_14["call"], ("GET", r"/api/dsm/health"))


class FindControlPrefersGxSelectorTest(unittest.TestCase):
    """③ ④ — gx 가 있으면 먼저 보고, 없으면 종전 텍스트 갈래로 그대로 간다.

    `find_control` 은 DRIVER 문자열 안에 있다 — `_driver_functions()` 로 뽑아 잰다.
    """

    def setUp(self) -> None:
        self.ns = _driver_functions("find_control")
        self.find_control = self.ns["find_control"]

    def test_gx_selector_is_tried_first_and_wins(self) -> None:
        page = _FakePage()
        target = _FakeElement(name="row-submit-button")
        decoy = _FakeElement(name="text-matched-decoy")
        page.buttons.append(("채우기", decoy))          # 텍스트로도 찾힐 만한 미끼
        page.gx_map["camera-address-row-submit"] = [target]
        el = self.find_control(page, {"name": "채우기", "gx": "camera-address-row-submit"})
        self.assertIs(el, target)  # 텍스트 미끼가 아니라 gx 선택자가 이긴다

    def test_falls_back_to_text_when_gx_not_found(self) -> None:
        page = _FakePage()
        target = _FakeElement(name="text-found")
        page.buttons.append(("확인", target))
        el = self.find_control(page, {"name": "확인", "gx": "no-such-gx"})
        self.assertIs(el, target)

    def test_rows_without_gx_are_unaffected(self) -> None:
        """gx 를 안 주는 기존 40여 행과 같은 모양 — None 이어도 그대로 텍스트로 찾는다."""
        page = _FakePage()
        target = _FakeElement(name="legacy")
        page.buttons.append(("저장", target))          # 화면의 실제 글자
        el = self.find_control(page, {"name": "^저장$", "gx": None})  # 컨트롤의 정규식
        self.assertIs(el, target)


class PrepareStepsNewKindsTest(unittest.TestCase):
    """⑤ — button_prepare(press()) 와 fill_label() 이 실제로 동작한다.

    `prepare_steps` 도 `find_control` 처럼 DRIVER 문자열 안에 있다(내부에서
    `find_control` 을 부르므로 **같은 이름공간에** 함께 뽑아 넣는다).
    """

    def setUp(self) -> None:
        self.ns = _driver_functions("find_control", "prepare_steps")
        self.prepare_steps = self.ns["prepare_steps"]
        self.mod = _load_module()  # press()/fill_label()/FLOWS 는 바깥 모듈의 진짜 top-level

    def test_button_prepare_clicks_by_gx(self) -> None:
        page = _FakePage()
        el = _FakeElement(name="dryrun-button")
        page.gx_map["camera-import-dryrun"] = [el]
        ok, done, restore, why = self.prepare_steps(
            page, [self.mod.press("표 먼저 보기", gx="camera-import-dryrun", wait_ms=10)])
        self.assertTrue(ok, why)
        self.assertEqual(el.clicked, 1)
        self.assertEqual(done[0]["kind"], "button_prepare")

    def test_button_prepare_missing_control_is_a_clean_failure(self) -> None:
        page = _FakePage()
        ok, done, restore, why = self.prepare_steps(
            page, [self.mod.press("없는 단추", gx="nope")])
        self.assertFalse(ok)
        self.assertIn("nope", why)  # gx 가 있으면 이름표는 gx 쪽을 쓴다(prepare_steps 규칙)

    def test_fill_label_writes_into_the_labelled_input(self) -> None:
        page = _FakePage()
        box = _FakeInput(value="")
        page.form_items["아이디"] = _FakeFormItem(box)
        ok, done, restore, why = self.prepare_steps(
            page, [self.mod.fill_label("아이디", "gxprobe-test-1")])
        self.assertTrue(ok, why)
        self.assertEqual(box.filled_with, "gxprobe-test-1")
        self.assertEqual(done[0]["kind"], "fill_label")

    def test_fill_label_missing_form_item_is_a_clean_failure(self) -> None:
        page = _FakePage()
        ok, done, restore, why = self.prepare_steps(
            page, [self.mod.fill_label("없는 라벨", "x")])
        self.assertFalse(ok)
        self.assertIn("없는 라벨", why)

    def test_u5_4_prepare_sequence_runs_both_button_presses_in_order(self) -> None:
        page = _FakePage()
        sample_btn = _FakeElement(name="sample")
        dryrun_btn = _FakeElement(name="dryrun")
        page.buttons.append(("예시 채우기", sample_btn))
        page.gx_map["camera-import-dryrun"] = [dryrun_btn]
        flows = _flows_by_key(self.mod)
        ok, done, restore, why = self.prepare_steps(page, flows["U5#4"]["prepare"])
        self.assertTrue(ok, why)
        self.assertEqual(sample_btn.clicked, 1)
        self.assertEqual(dryrun_btn.clicked, 1)
        self.assertEqual([d["kind"] for d in done], ["button_prepare", "button_prepare"])

    def test_u5_1_prepare_sequence_fills_all_four_labels(self) -> None:
        page = _FakePage()
        boxes = {label: _FakeInput("") for label in
                 ("아이디", "이메일", "비밀번호", "소속(테넌트) ID")}
        for label, box in boxes.items():
            page.form_items[label] = _FakeFormItem(box)
        flows = _flows_by_key(self.mod)
        ok, done, restore, why = self.prepare_steps(page, flows["U5#1"]["prepare"])
        self.assertTrue(ok, why)
        for label, box in boxes.items():
            with self.subTest(label=label):
                self.assertIsNotNone(box.filled_with, "%s 를 못 채웠다" % label)

    def test_u3_16_prepare_sequence_fills_both_times(self) -> None:
        page = _FakePage()
        start = _FakeInput("")
        end = _FakeInput("")
        page.placeholder_map["22:00"] = [start]
        page.placeholder_map["07:00"] = [end]
        flows = _flows_by_key(self.mod)
        ok, done, restore, why = self.prepare_steps(page, flows["U3#16"]["prepare"])
        self.assertTrue(ok, why)
        self.assertEqual(start.filled_with, "21:47")
        self.assertEqual(end.filled_with, "06:13")


class SelfTestCatchesMissingRevertTest(unittest.TestCase):
    """⑥ — 이 파일 자신의 --self-test 가 "되돌림 선언 없음"을 잡는다(회귀 방지).

    U5#1·U5#4·U5#5·U3#16 에 실제 POST/PUT 컨트롤을 달면서 revert 선언을 빠뜨리면
    이 도구의 자기시험이 스스로 걸린다 — 실제로 한 번 그렇게 걸렸다(구현 중 실측).
    여기서는 그 자기시험이 **여전히 통과 상태**인지 서브프로세스로 확인한다.
    """

    def test_self_test_subprocess_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(_tool_path()), "--self-test"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-3000:])
        self.assertIn("자기시험 통과", result.stdout)

    def test_five_rows_all_declare_revert(self) -> None:
        flows = _flows_by_key(_load_module())
        for key in ("U5#1", "U5#4", "U5#5", "U3#16", "U5#10"):
            with self.subTest(key=key):
                self.assertIsNotNone(flows[key]["revert"], "%s 에 revert 선언이 없다" % key)

    def test_flow_count_is_still_48(self) -> None:
        mod = _load_module()
        self.assertEqual(len(mod.FLOWS), 48)


# ═══════════════════════════════════════════════════════════════════════════
# Playwright `page` 의 가벼운 가짜 — find_control()/prepare_steps() 가 쓰는
# 부분집합만 흉내 낸다(.locator · .get_by_role · .get_by_text · .count · .first ·
# .nth · .is_visible · .click · .fill · .input_value).
# ═══════════════════════════════════════════════════════════════════════════

_GX_SELECTOR_RE = re.compile(r'\[data-gx="([^"]+)"\]')


class _FakeElement:
    def __init__(self, *, name="el", visible=True):
        self.name = name
        self.visible = visible
        self.clicked = 0

    def is_visible(self):
        return self.visible

    def click(self, timeout=None):
        self.clicked += 1


class _FakeInput:
    def __init__(self, value=""):
        self._value = value
        self.filled_with = None

    def input_value(self):
        return self._value

    def fill(self, text):
        self.filled_with = text
        self._value = text


class _FakeFormItem:
    """`.ant-form-item` 하나 — `.locator("input")` 만 지원한다(fill_label 이 쓰는 전부)."""

    def __init__(self, input_el: _FakeInput):
        self._input_el = input_el

    def locator(self, selector):
        assert selector == "input"
        return _FakeLocator([self._input_el])


class _FakeLocator:
    def __init__(self, elements):
        self._elements = list(elements)

    def count(self):
        return len(self._elements)

    def nth(self, i):
        return self._elements[i]

    @property
    def first(self):
        return self._elements[0]


class _FakePage:
    """`find_control()`/`prepare_steps()` 가 부르는 자리만 흉내 낸다."""

    def __init__(self):
        self.buttons: list[tuple[str, _FakeElement]] = []
        self.gx_map: dict[str, list[_FakeElement]] = {}
        self.form_items: dict[str, _FakeFormItem] = {}
        self.placeholder_map: dict[str, list[_FakeInput]] = {}
        self.wait_calls: list[int] = []

    def locator(self, selector, has=None):
        m = _GX_SELECTOR_RE.match(selector)
        if m:
            return _FakeLocator(self.gx_map.get(m.group(1), []))
        if selector == ".ant-form-item":
            # `has` 는 이 가짜에서 `get_by_text()` 가 돌려준 라벨 문자열 그대로다.
            item = self.form_items.get(has)
            return _FakeLocator([item] if item is not None else [])
        return _FakeLocator([])

    def get_by_role(self, role, name=None):
        if role == "button" and name is not None:
            return _FakeLocator([el for text, el in self.buttons if name.search(text)])
        return _FakeLocator([])

    def get_by_text(self, pattern, exact=False):
        if isinstance(pattern, str):
            return pattern  # `.locator(".ant-form-item", has=...)` 가 그대로 받는 표식
        return _FakeLocator([el for text, el in self.buttons if pattern.search(text)])

    def get_by_placeholder(self, placeholder):
        return _FakeLocator(self.placeholder_map.get(placeholder, []))

    def wait_for_timeout(self, ms):
        self.wait_calls.append(ms)
