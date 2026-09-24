# -*- coding: utf-8 -*-
"""P-318 — ● 조건 셋째: **그 사용자의 언어** (차선 Q · 2026-09-26 ·
WO-GX-20260926-12 §12 P-318).

무엇을 재는가 — 판정 함수만, 계측기를 실제로 돌리지 않는다
------------------------------------------------------------
`scripts/measure_onboarding_t.py::third_condition_violations` 는 **순수 함수**다 —
문자열 하나(그 행이 실제로 보여 준 화면 글자)를 받아 위반 이름들을 돌려준다.
로그인도, 브라우저도, 서버도 필요 없다. 이 시험은 그 함수와, 그것이 `result()` 에
어떻게 **배선**됐는지만 확인한다 — 실제 계측(서버 로그인·화면 캡처)은 V 가
다음 회차에 한다(WO 지시 그대로: 「계측기를 실제로 돌리지는 마십시오」).

★★ **먼저 실패해 본다** — `GapBetweenScanLineAloneAndThirdConditionTest` 가 그 기록이다.
  `verify_ui_copy.scan_line` **하나만으로는** 순영문 라벨(`Status` · `In Use`)을
  못 잡는다 — 그 판정기 자신의 주석이 「순영문 라벨은 이 그물을 지나간다 …
  그 자리는 UX-21」이라 적어 두었다(UX-21 게이트는 아직 이 저장소에 없다).
  그래서 이 시험은 먼저 **그 구멍이 실제로 있다는 것**(scan_line 만으로는 안 잡힘)을
  오늘(2026-09-24) 턴 AH 네 번째 회차가 U4#11 에서 실제로 캡처한 화면 글자로
  확인하고, 그다음 `third_condition_violations` (ADMIN_HEADER 자기표지를 더한 것)가
  **같은 글자를 잡는다**는 것을 확인한다. 지어낸 문장이 아니라
  `docs/agent/evidence/ONB-T/turn_ah_4.json` 의 U4#11 `evidence` 문자열 그대로다.

두 벌 금지(D-479) 확인
-----------------------
사전이 두 벌이 아니라는 것을 **동일성**으로 확인한다 — `third_condition_violations` 가
GX-COPY 위반을 잡을 때, 그 결과가 `verify_ui_copy.scan_line` 을 **같은 문자열에 직접
불렀을 때와 정확히 같다**(자기표지 ADMIN_HEADER 한 줄만 얹었을 뿐, 사전 자체를
다시 적지 않았다는 뜻이다).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from django.test import SimpleTestCase

#: [P-318 · WO-12 §12] 오늘(2026-09-24) 턴 AH 네 번째 회차가 U4#11(`/device`)에서
#: 실제로 캡처한 본문 앞부분 — `docs/agent/evidence/ONB-T/turn_ah_4.json` 의
#: `rows[].evidence` 그대로 옮긴다(지어내지 않는다).
REAL_U4_11_BODY = (
    "무슨 일 있었나\n열람·삭제 청구\n드론·로봇 장비 등록 · 관리자 전용 화면입니다. "
    "아래 표기는 아직 영문입니다.\n\t\nStatus\n\t\nIn Use"
)

#: WO 지시문이 든 예시 모양 — 「그날 실제 모양 — 예: Personal Information 같은 영어
#: 본문」. `ADMIN_HEADER` 없이 영문 낱말만 있으면 이 판정기는 그 낱말 자체를 사전에
#: 넣지 않고는 못 잡는다(그러면 두 번째 사전이 된다 · D-479) — 그래서 이 형태는
#: **제품이 실제로 쓰는 자기표지**(관리자 화면이 스스로 「아직 영문입니다」라 미리
#: 알리는 문장)와 함께 나타난다고 본다. 오늘 실측(U4#11 · U5#2)도 정확히 그 모양이다.
WO_EXAMPLE_BODY = (
    "사람·역할 — 계정 만들기 · 비활성화 · 관리자 전용 화면입니다. "
    "아래 표기는 아직 영문입니다.\nPersonal Information\nRole\nStatus"
)

CLEAN_KOREAN_BODY = "지금 처리할 것\n무슨 일 있었나\n카메라 격자\n인계 메모\n처음이세요"


def _measure_onboarding_t():
    """`scripts/measure_onboarding_t.py` 를 **파일 경로로** 읽는다.

    gx-shell 은 `/repo/scripts` 에 이 저장소의 `scripts/` 를 마운트한다(MEMORY ·
    「GuardianX 시험 실행 명령」). 호스트에서 직접 돌릴 경우를 위해 저장소 상대
    경로도 함께 시도한다 — 정본을 못 읽으면 **회색으로 스킵**한다(지어내지 않는다).
    """
    candidates = [
        Path("/repo/scripts/measure_onboarding_t.py"),
        Path(__file__).resolve().parents[2] / "scripts" / "measure_onboarding_t.py",
        Path("/app/scripts/measure_onboarding_t.py"),
    ]
    for path in candidates:
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location(
            "gx_measure_onboarding_t_p318", str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    raise AssertionError(
        "scripts/measure_onboarding_t.py 를 못 읽었다 — 찾아본 자리: %s" % candidates)


def _verify_ui_copy():
    candidates = [
        Path("/repo/scripts/verify_ui_copy.py"),
        Path(__file__).resolve().parents[2] / "scripts" / "verify_ui_copy.py",
        Path("/app/scripts/verify_ui_copy.py"),
    ]
    for path in candidates:
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location(
            "gx_verify_ui_copy_p318", str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    raise AssertionError("scripts/verify_ui_copy.py 를 못 읽었다")


class GapBetweenScanLineAloneAndThirdConditionTest(SimpleTestCase):
    """★★ 먼저 실패해 본다 — `scan_line` 혼자로는 오늘의 실제 모양을 못 잡는다."""

    def setUp(self) -> None:
        self.copy = _verify_ui_copy()
        self.onb = _measure_onboarding_t()

    def test_scan_line_alone_misses_the_undeclared_english_columns(self) -> None:
        """`Status` · `In Use` 는 GX-COPY 금지 목록에 없다 — `scan_line` 은 그 두 낱말
        자체로는 안 걸린다(순영문 라벨은 UX-21 의 자리라고 그 판정기 스스로 적어
        두었다). 이 assert 가 실패하면 이 시험의 전제(구멍이 있다)가 깨진 것이다.
        """
        bare_english = "Status\nIn Use"
        self.assertEqual(self.copy.scan_line(bare_english), [])

    def test_third_condition_catches_the_same_real_row_via_self_declared_header(self) -> None:
        """같은 화면 글자(U4#11 실측 전체)를 셋째 조건에 넣으면 **잡힌다** —
        `ADMIN_HEADER` 자기표지가 함께 있기 때문이다. 새 사전을 만들지 않았다."""
        hits = self.onb.third_condition_violations(REAL_U4_11_BODY)
        self.assertTrue(hits, "오늘 실제로 캡처된 U4#11 화면이 셋째 조건에 안 걸렸다")
        self.assertIn("영문 메뉴(자기표지 ADMIN_HEADER)", hits)


class ThirdConditionViolationsTest(SimpleTestCase):

    def setUp(self) -> None:
        self.onb = _measure_onboarding_t()
        self.copy = _verify_ui_copy()

    def test_empty_text_is_not_measured_as_zero_violations_by_fabrication(self) -> None:
        """화면 글자를 아직 안 넘긴 행(빈 문자열)은 **위반 0건**이 아니라 **배선 전**이다
        — 그래도 함수는 빈 목록을 돌려준다(호출부가 그 뜻을 안다: 아직 안 쟀다)."""
        self.assertEqual(self.onb.third_condition_violations(""), [])

    def test_clean_korean_screen_is_not_flagged(self) -> None:
        self.assertEqual(self.onb.third_condition_violations(CLEAN_KOREAN_BODY), [])

    def test_gx_copy_dictionary_violation_is_caught(self) -> None:
        """GX-COPY 사전 밖 표현(백틱·절 ID) — `scan_line` 그대로가 잡는 갈래다."""
        text = "지금 상태는 `response_state=occurred` 입니다 (P-184)"
        hits = self.onb.third_condition_violations(text)
        self.assertTrue(hits)

    def test_wo_illustrative_example_shape_is_caught(self) -> None:
        """WO 지시문의 예시 모양(「Personal Information 같은 영어 본문」) — 오늘 제품이
        실제로 쓰는 자기표지와 함께 나타나는 형태로 재현해 확인한다."""
        hits = self.onb.third_condition_violations(WO_EXAMPLE_BODY)
        self.assertIn("영문 메뉴(자기표지 ADMIN_HEADER)", hits)

    def test_same_dictionary_same_function_no_second_copy(self) -> None:
        """D-479 — GX-COPY 갈래의 결과는 `verify_ui_copy.scan_line` 을 **같은 문자열에
        직접 불렀을 때와 정확히 같다.** 사전을 베껴 적지 않았다는 뜻이다."""
        text = "지금 상태는 `response_state=occurred` 입니다 (P-184)"
        direct = self.copy.scan_line(text)
        via_onb = [h for h in self.onb.third_condition_violations(text)
                   if h != "영문 메뉴(자기표지 ADMIN_HEADER)"]
        self.assertEqual(sorted(direct), sorted(via_onb))


class ResultWiringTest(SimpleTestCase):
    """`result()` 가 셋째 조건을 **◐ 상한**으로 실제로 반영하는가."""

    def setUp(self) -> None:
        self.onb = _measure_onboarding_t()

    def test_a_row_that_would_be_green_is_capped_to_half_by_third_condition(self) -> None:
        r = self.onb.result(
            "U4#11", "/device", phrase_seen=True, predicate=True,
            evidence="표 먼저 보기=True", cap_half=False, measured=True,
            screen_text=REAL_U4_11_BODY)
        self.assertEqual(r["verdict"], "half")
        self.assertEqual(r["score"], 0.5)
        self.assertTrue(r["cap_half"])
        self.assertIn("셋째 조건", r["evidence"])

    def test_a_clean_row_stays_green(self) -> None:
        r = self.onb.result(
            "U1#1", "/login", phrase_seen=True, predicate=True,
            evidence="문장=True", cap_half=False, measured=True,
            screen_text=CLEAN_KOREAN_BODY)
        self.assertEqual(r["verdict"], "green")
        self.assertEqual(r["score"], 1.0)
        self.assertFalse(r["cap_half"])

    def test_an_already_capped_row_is_unaffected(self) -> None:
        """정본이 이미 ◐ 상한이라 적은 행은 셋째 조건이 있든 없든 그대로 ◐다
        (내리지 않는다 — cap_half 는 **올릴 뿐**이다)."""
        r = self.onb.result(
            "U5#15", "/dsm/metering", phrase_seen=True, predicate=True,
            evidence="화면에 %=False", cap_half=True, measured=True,
            screen_text=CLEAN_KOREAN_BODY)
        self.assertEqual(r["verdict"], "half")
        self.assertNotIn("셋째 조건", r["evidence"])   # 깨끗한 글자면 사유를 더 안 붙인다

    def test_a_red_row_stays_red_even_with_violations(self) -> None:
        """술어가 안 서면(빨강) 셋째 조건은 점수를 더 깎지 않는다 — 이미 0 이다."""
        r = self.onb.result(
            "U1#11", "/dsm/queue", phrase_seen=False, predicate=False,
            evidence="단추 없음", cap_half=False, measured=True,
            screen_text=REAL_U4_11_BODY)
        self.assertEqual(r["verdict"], "red")
        self.assertEqual(r["score"], 0.0)

    def test_existing_callers_without_screen_text_are_unaffected(self) -> None:
        """★ 배선이지 소급 재측이 아니다 — 기존 ~40개 호출부는 `screen_text` 를
        아직 안 넘긴다. 그 호출부의 결과는 **한 글자도 안 바뀐다**(기본값 "")."""
        r = self.onb.result(
            "U1#9", "/dsm/events/:id", phrase_seen=True, predicate=True,
            evidence="배지=['심각']", cap_half=False, measured=True)
        self.assertEqual(r["verdict"], "green")
        self.assertEqual(r["score"], 1.0)
        self.assertEqual(r["evidence"], "배지=['심각']")

    def test_gray_rows_are_not_scored_by_third_condition(self) -> None:
        """못 잰 행(회색)은 셋째 조건이 끼어들 자리가 아니다 — `measured=False` 면
        `third_condition_violations` 를 아예 안 부른다."""
        r = self.onb.result(
            "U6#4", "webhook", phrase_seen=False, predicate=False,
            evidence="환경", cap_half=False, measured=False,
            gray_kind="env", screen_text=REAL_U4_11_BODY)
        self.assertEqual(r["verdict"], "gray")
        self.assertIsNone(r["score"])
