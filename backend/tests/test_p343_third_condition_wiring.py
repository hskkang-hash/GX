# -*- coding: utf-8 -*-
"""P-343 — 「셋째 조건」(그 사용자의 언어)을 온보딩 계측기 전체에 배선한다
(차선 Q · WO-GX-20260925 후속).

무엇이 문제였나
---------------
P-318(턴 AI · 커밋 5b2429a)이 `third_condition_violations` 와 `result()` 의
`screen_text` 매개변수를 이미 넣어 두었다 — 그런데 이 파일의 실제 호출부(약 57곳)
**0곳**이 그것을 부르고 있었다. 함수는 있고 문은 있는데 아무도 두드리지 않은
꼴이다: 화면 글자를 한 번도 안 넘기니 `third_condition_violations("")` 는
매번 빈 목록을 돌려주고, 셋째 조건은 **한 번도 위반으로 걸리지 않은 채** 조용히
통과해 왔다.

이 시험이 확인하는 것 — **셋만**(계측기를 실제로 돌리지 않는다 · P-318 과 같은 결)
--------------------------------------------------------------------------
① 정본 소스의 `result(` 호출부 **전부**가 이제 `screen_text=` 를 넘긴다(N/N).
② 화면이 없는 행(U6 · 기계 호출)은 **회색**이다 — 초록으로 지어내지 않는다.
③ 화면에 사전 밖 낱말(외국어/영문 메뉴)이 있으면 **위반으로 걸린다**(◐ 상한).

②·③ 은 `result()` 를 직접 부르는 순수 함수 시험이다(로그인·브라우저·서버가
필요 없다 — P-318 의 `ResultWiringTest` 와 같은 모양).
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

from django.test import SimpleTestCase


def _measure_onboarding_t_path() -> Path:
    """`scripts/measure_onboarding_t.py` 를 찾는다 — gx-shell 마운트 자리부터 본다
    (MEMORY · 「GuardianX 시험 실행 명령」과 test_p318_third_condition.py 와 같은 순서)."""
    candidates = [
        Path("/repo/scripts/measure_onboarding_t.py"),
        Path(__file__).resolve().parents[2] / "scripts" / "measure_onboarding_t.py",
        Path("/app/scripts/measure_onboarding_t.py"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise AssertionError(
        "scripts/measure_onboarding_t.py 를 못 읽었다 — 찾아본 자리: %s" % candidates)


def _measure_onboarding_t():
    path = _measure_onboarding_t_path()
    spec = importlib.util.spec_from_file_location(
        "gx_measure_onboarding_t_p343", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _result_call_sites(src: str) -> list[ast.Call]:
    """소스에서 `result(...)` **호출부**를 전부 찾는다 — `def result(...)` 정의나
    주석·문자열 속 언급(`` `result("U6#…")` `` 같은)은 여기 안 걸린다(AST 라서
    글자 흉내가 아니라 **실제 호출 노드**만 본다)."""
    tree = ast.parse(src)
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "result"]


def _call_has_screen_text_kw(call: ast.Call) -> bool:
    return any(kw.arg == "screen_text" for kw in call.keywords)


class EveryResultCallSitePassesScreenTextTest(SimpleTestCase):
    """정적 대조 — **브라우저 없이** 소스만 읽는다(P-180 의 `--check` 와 같은 결).

    ★ 이 시험이 세는 것은 「이 파일이 부르는 행 수」(`implemented_rows()`, 48행 ·
    U 별 중복 제거)가 아니라 **`result(` 호출부 수 그 자체**다 — 같은 행이 두
    갈래(성공/실패)로 갈려 두 번 부르는 자리(예: U2#3·U2#4·U3#3·U5#10)가 있고,
    그 갈래 하나하나가 전부 배선됐는지를 보는 것이 이 시험의 몫이다.
    """

    def test_wiring_count_is_n_of_n(self) -> None:
        path = _measure_onboarding_t_path()
        src = path.read_text(encoding="utf-8")
        calls = _result_call_sites(src)
        total = len(calls)
        wired = [c for c in calls if _call_has_screen_text_kw(c)]
        unwired = [c.lineno for c in calls if not _call_has_screen_text_kw(c)]
        self.assertGreater(total, 0, "result( 호출부를 하나도 못 찾았다 — 시험 전제가 깨졌다")
        self.assertEqual(
            len(wired), total,
            "screen_text 배선 %d/%d — 안 걸린 줄: %s" % (len(wired), total, unwired))
        print("[P-343] result( 호출부 screen_text 배선 %d/%d" % (len(wired), total))

    def test_no_call_site_regressed_to_the_bare_default(self) -> None:
        """[P-343 배경] 고침 전에는 **0**곳이 `screen_text` 를 불렀다 — 이 시험은
        그 수가 되돌아가지 않았는지를 이름으로 확인한다(회귀 방지)."""
        path = _measure_onboarding_t_path()
        src = path.read_text(encoding="utf-8")
        calls = _result_call_sites(src)
        wired = sum(1 for c in calls if _call_has_screen_text_kw(c))
        self.assertGreater(wired, 0, "0/N 로 되돌아갔다 — P-343 이전 상태다")


class NoScreenIsGrayNotGreenTest(SimpleTestCase):
    """②의 짝 — 화면이 없는 행(U6 · 기계)은 **회색**이다. `result()` 를 직접
    불러 확인한다(계측기를 실제로 돌리지 않는다 · P-318 과 같은 결).
    """

    def setUp(self) -> None:
        self.onb = _measure_onboarding_t()

    def test_machine_row_with_no_screen_is_gray_not_green(self) -> None:
        """문구도 술어도 다 서는(200 · total/events 칸 다 있는) U6 행이라도,
        `screen_text=None`(=화면 자체가 없다)이면 **회색**이어야 한다 — 초록이면
        「화면 없이도 그 사용자의 언어를 쟀다」는 거짓말이 된다."""
        r = self.onb.result(
            "U6#2", "GET /api/dsm/events", phrase_seen=True, predicate=True,
            evidence="status=200 · total 칸=True · events 배열=True",
            cap_half=False, measured=True, screen_text=None)
        self.assertEqual(r["verdict"], "gray")
        self.assertIsNone(r["score"])
        self.assertEqual(r["gray_kind"], "nopred")
        self.assertIn("화면이 없다", r["evidence"])

    def test_collect_screen_text_returns_none_with_no_page_and_no_text(self) -> None:
        """기계 호출 자리(U6)가 실제로 부르는 모양 그대로: `page` 도 `text` 도
        없으면 **`None`**(빈 문자열이 아니다)."""
        self.assertIsNone(self.onb.collect_screen_text())

    def test_collect_screen_text_prefers_already_captured_text(self) -> None:
        """이미 캡처해 둔 글자(예: 로그인 화면 · U1#1)가 있으면 그것을 그대로
        쓴다 — `page` 를 다시 읽지 않는다(재읽기는 다른 화면을 잴 위험이 있다)."""
        self.assertEqual(self.onb.collect_screen_text(text="이미 읽은 글자"), "이미 읽은 글자")

    def test_bare_default_screen_text_still_means_not_wired_yet(self) -> None:
        """★ `""`(빈 문자열)과 `None` 은 다른 뜻이다 — 이 구별이 무너지면 P-318 의
        기존 규약(빈 문자열 = 아직 배선 안 됨)이 깨진다. `screen_text=""` 는
        여전히 **초록/빨강을 그대로 두고** 셋째 조건만 「0건」이지, 행 전체를
        회색으로 만들지 않는다(회귀 방지 — `no_screen` 은 오직 `None` 에만 선다)."""
        r = self.onb.result(
            "U1#9", "/dsm/events/:id", phrase_seen=True, predicate=True,
            evidence="배지=['심각']", cap_half=False, measured=True, screen_text="")
        self.assertEqual(r["verdict"], "green")
        self.assertNotEqual(r["gray_kind"], "nopred")


class ForeignLanguageViolationCapsToHalfTest(SimpleTestCase):
    """③의 짝 — 사전 밖 낱말(외국어/영문 메뉴)이 실제 화면에 있으면 초록이 되지
    않는다(◐ 상한). U4#11·U5#2 가 실측으로 겪은 그 모양(자기표지 ADMIN_HEADER +
    `Status`/`Add New Role` 같은 순영문 라벨)을 그대로 쓴다."""

    def setUp(self) -> None:
        self.onb = _measure_onboarding_t()

    def test_admin_screen_with_undeclared_english_labels_is_capped(self) -> None:
        screen = ("역할 관리 · 관리자 전용 화면입니다. 아래 표기는 아직 영문입니다.\n"
                  "Add New Role\nStatus")
        r = self.onb.result(
            "U5#2", "/roles", phrase_seen=True, predicate=True,
            evidence="표 행 3 · Add New Role=True", cap_half=False, measured=True,
            screen_text=screen)
        self.assertEqual(r["verdict"], "half")
        self.assertEqual(r["score"], 0.5)
        self.assertIn("셋째 조건", r["evidence"])
        self.assertNotEqual(r["gray_kind"], "nopred")     # 회색이 아니라 ◐다 — 다른 결

    def test_clean_korean_screen_is_not_capped_by_wiring_alone(self) -> None:
        """배선 자체가 억지로 반을 만들지 않는다 — 깨끗한 화면은 그대로 초록이다."""
        r = self.onb.result(
            "U1#1", "/login", phrase_seen=True, predicate=True,
            evidence="문장=True · 처음이세요?=True", cap_half=False, measured=True,
            screen_text="GuardianX는 대응 시간을 잽니다.\n처음이세요?")
        self.assertEqual(r["verdict"], "green")
        self.assertEqual(r["score"], 1.0)
