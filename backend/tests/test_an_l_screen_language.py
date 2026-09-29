# -*- coding: utf-8 -*-
"""P-396 · 턴 AN · 차선 L — 이번 턴에 고친 화면 문구 두 자리가 다시 새지 않는가.

이 파일은 `scripts/verify_ui_copy.py` 를 다시 만들지 않는다(D-479 — 두 벌은 반드시
어긋난다). 그 게이트는 "잔여 0건"을 이미 말하고 있다(2026-09-29 재실행) — 셋째 조건
(결정 번호 · 절 ID · 마크다운 강조 · 상태 코드 · 영문 열거값)의 dsm/mobile/login
스코프 위반은 이 턴이 시작하기 전에 이미 갚혀 있었다(직전 턴 「AM」 차선 L 의 몫).

이 턴에 차선 L 이 실제로 새로 고친 자리는 **둘**이다:
  ① `frontend/src/features/mobile/pages/MobileSettings.tsx` — 온보딩 U3#16.
     새로고침 뒤에도 남는 "저장 여부" 줄이 "저장된 설정이 있습니다"였다 — 저장
     **직후**에만 뜨는 상태 칸의 낱말("저장됨")과 달라서 셋째 조건 계측(문자열
     대조)이 "화면 「저장됨」=False"로 읽었다. 두 낱말을 하나로 모았다.
  ② `frontend/src/features/dsm/pages/EventDetail.tsx` — 온보딩 U3#1.
     "알림 보내기"의 결과가 토스트(`message.*`)뿐이었다 — 토스트는 사라지고,
     사라진 뒤에는 "결과 문장"이 화면에 없다(같은 화면의 다른 쓰기는 전부 상태
     칸을 이미 쓰고 있었다). 상태 칸(`notifyOutcome` → `data-gx="notify-outcome"`)을
     더했다.

소스 문자열 대조다 — HTTP 를 한 번도 때리지 않는다(P-371 자매 파일과 같은 성질).

절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

from pathlib import Path

from django.test import TestCase


def _frontend_src() -> Path | None:
    for base in (Path("/repo/frontend/src"),
                 *(p / "frontend" / "src" for p in Path(__file__).resolve().parents)):
        if (base / "App.tsx").is_file():
            return base
    return None


class MobileSettingsSavedStateCopyTests(TestCase):
    """온보딩 U3#16 — `/m/settings` 의 저장 여부 줄이 「저장됨」을 말하는가."""

    def setUp(self) -> None:
        self.src = _frontend_src()
        self.assertIsNotNone(self.src, "frontend/src 를 못 찾았다 — 판정 불가를 초록으로 두지 않는다")
        self.body = (
            self.src / "features/mobile/pages/MobileSettings.tsx"
        ).read_text(encoding="utf-8")

    def test_saved_state_line_says_saved(self) -> None:
        # ★ `data-gx="prefs-saved-state"` 가 서는 그 줄 — 새로고침 뒤에도 남는
        #   "지금 서버에 저장된 값이 있는가"의 유일한 자리다.
        self.assertIn('data-gx="prefs-saved-state"', self.body)
        self.assertIn("저장됨 — 이미 정한 값이 있습니다.", self.body,
                      "저장 여부 줄이 다시 「저장됨」이 아닌 다른 낱말로 돌아갔다")
        # 종전 문구가 되살아나면 실패한다 — 두 벌(저장 직후의 낱말과 새로고침
        # 뒤의 낱말)이 다시 어긋나는 것을 잡는다.
        self.assertNotIn("저장된 설정이 있습니다.", self.body,
                         "새로고침 뒤 줄이 다시 「저장됨」과 다른 낱말을 쓴다")

    def test_unsaved_state_line_unchanged(self) -> None:
        # ★ 저장 안 한 갈래는 이번 턴에 손대지 않았다 — 그대로인지도 함께 본다.
        self.assertIn("아직 정하지 않았습니다 — 규칙이 정한 대로 받습니다.", self.body)


class EventDetailNotifyOutcomeCellTests(TestCase):
    """온보딩 U3#1 — `/dsm/events/:id` 의 「알림 보내기」 결과가 토스트 말고도 남는가."""

    def setUp(self) -> None:
        self.src = _frontend_src()
        self.assertIsNotNone(self.src, "frontend/src 를 못 찾았다 — 판정 불가를 초록으로 두지 않는다")
        self.body = (
            self.src / "features/dsm/pages/EventDetail.tsx"
        ).read_text(encoding="utf-8")

    def test_notify_sets_a_persistent_outcome_state(self) -> None:
        self.assertIn("notifyOutcome", self.body)
        self.assertIn("setNotifyOutcome(", self.body)

    def test_notify_outcome_is_rendered_with_a_data_gx_marker(self) -> None:
        # ★ `data-gx="notify-outcome"` 이 검수·판정기가 찾는 자리다 — 토스트와
        #   달리 사라지지 않는다.
        self.assertIn('data-gx="notify-outcome"', self.body)

    def test_all_three_notify_branches_still_set_the_outcome(self) -> None:
        # ★ 세 갈래(0건 · 일부 실패 · 정상) + 오류 갈래 — 넷 다 `setNotifyOutcome`
        #   호출로 이어져야 한다. 하나라도 토스트만 남으면 그 갈래에서 다시
        #   "결과 문장=False"가 된다.
        self.assertGreaterEqual(
            self.body.count("setNotifyOutcome("), 2,
            "notify() 의 갈래 일부가 상태 칸을 안 채운다 — 토스트만 남은 자리가 있다",
        )
        # 오류 갈래도 상태 칸을 채우는지 — catch 블록 안에서 같은 이름이 불린다.
        catch_start = self.body.index("} catch (err) {\n      const line = userFacingError('EventDetail.notify'")
        catch_slice = self.body[catch_start:catch_start + 300]
        self.assertIn("setNotifyOutcome(", catch_slice,
                      "notify() 의 오류 갈래가 상태 칸을 채우지 않는다")
