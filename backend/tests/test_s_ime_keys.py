# -*- coding: utf-8 -*-
"""P-58 — **한글 IME 상태 재현 시험.** 단축키가 물리 키인지 「글자로 고르는지」를 잰다.

세종 P-58: 단축키는 **물리 키(`event.code`)** 기준 · 한/영 무관 · 입력 칸에 초점이
있을 땐 무시. 게이트는 「**한글 IME 상태 재현 시험 1**」을 더 요구했다.

정적 판정기만으로는 왜 부족한가 — [실측으로 보였다]
---------------------------------------------------
`scripts/verify_wall_keys.py` 의 술어 ①은 「소스 어딘가에 `.code` 를 읽는 자리가
있는가」를 센다. 그것으로는 이 모양을 **못 잡는다**:

    const slot = ev.code;      // 읽기는 읽는다 → ①은 **초록**
    trace('key pressed', slot);
    switch (ev.key) { case 'j': ... }   // 그런데 **고르는 것은 글자**다 → 관제실에서 죽는다

이 파일의 `test_static_predicate_alone_would_pass_this` 가 그 두 답을 나란히 보여 준다.

무엇을 재고 무엇을 못 재는가 — **먼저 가른다**
----------------------------------------------
**잰 것**: 소스에서 뽑은 **배선**(switch 가 무엇을 받고 case 라벨이 무엇인가)에
한글 입력기 상태의 키 이벤트를 흘려 보내 **먹는지**를 본다. 브라우저 없이 된다.

**못 잰 것**: 브라우저가 정말 그 이벤트를 그 모양으로 올리는가. 이 환경은 화면
동시 접속이 하나뿐이고 이번 턴 그 자리는 QA/E2E 것이다 — 브라우저를 열지 않는다.
**그래서 이 파일은 「모형에 대한 재현」이라고 스스로 말한다.** 다음 사람이 브라우저에서
확인할 것 셋은 `verify_wall_keys.BROWSER_TODO` 에 있고, 아래 시험이 그 셋이 지워지지
않도록 지킨다. **못 재는 것을 잰 척하지 않는다.**

이 컨테이너에서 `frontend/` 를 못 읽는다 — 그것도 실측이다
----------------------------------------------------------
    [실측 2026-09-05] gx-shell 의 마운트는 넷이고 `frontend` 는 없다:
        C:/…/scripts -> /repo/scripts (ro) · C:/…/backend -> /app · /docs · /repo/backend (ro)

그래서 **제품 소스에 대한 판정은 호스트의 `verify_wall_keys.py` ⑦이 한다.**
이 파일은 ① 그 판정기의 술어가 옳은지(양성·음성)와 ② ⑦이 게이트에 실제로 실려 있는지를
잰다. 실려 있지 않으면 여기가 빨개진다 — **판정을 잃어버리는 것을 막는 자리다.**

캐시 처리: **해당 없음** — 파일과 순수 함수만 읽는다. HTTP 를 때리지 않는다.

절대 금지 (AGENT_LOOP 절대금지 #4·#5): skip·xfail 금지.

실행
    docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \\
      DB_TEST_NAME=test_gx_sec python -m pytest tests/test_s_ime_keys.py -q \\
      --nomigrations -p no:randomly --tb=short 2>/dev/null'
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

#: 판정기가 사는 자리. 컨테이너는 `/repo/scripts`(읽기 전용), 호스트는 저장소 안이다.
_CANDIDATES = (
    Path("/repo/scripts"),
    Path(__file__).resolve().parents[2] / "scripts",
)
for _c in _CANDIDATES:
    if (_c / "verify_wall_keys.py").exists():
        sys.path.insert(0, str(_c))
        JUDGE_DIR = _c
        break
else:  # pragma: no cover - 이 자리에 오면 시험이 아니라 환경이 깨진 것이다
    JUDGE_DIR = None

if JUDGE_DIR is not None:
    import verify_wall_keys as W


#: 제품 소스. **이 컨테이너에는 없다** — 없으면 「못 쟀다」로 적고 호스트 게이트를 가리킨다.
_SOURCE_CANDIDATES = tuple(
    p / "frontend/src/features/dsm/hooks/useQueueKeys.ts"
    for p in (Path("/repo"), Path(__file__).resolve().parents[2])
)


def _product_source() -> str | None:
    for path in _SOURCE_CANDIDATES:
        try:
            return W.strip_comments(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
    return None


class JudgeReachableTest(unittest.TestCase):
    """판정기를 못 읽으면 아래 시험들은 아무것도 재지 못한다 — 그것부터 말한다."""

    def test_judge_is_importable(self):
        self.assertIsNotNone(
            JUDGE_DIR,
            "verify_wall_keys.py 를 못 찾았다 — 이 파일은 아무것도 재지 못했다. "
            "gx-shell 은 /repo/scripts 를 읽기 전용으로 물고 있어야 한다",
        )


class ImeReplayPredicateTest(unittest.TestCase):
    """술어 ⑦이 옳은가 — **양성과 음성을 함께** 잰다. 한쪽만 재면 초록으로 죽는다."""

    def test_physical_key_wiring_survives_the_hangul_ime(self):
        """자리로 고르는 배선은 한글 입력기가 켜져도 여덟 자리가 다 먹는다."""
        self.assertEqual(W.check_ime_replay(W.GOOD_IME_KEYS), [])

    def test_birth_sample_dies_under_the_hangul_ime(self):
        """★ 출생 표본 — 차선 C1 이 처음 짠 `ev.key` 배선. 여기서 빨개져야 한다."""
        bad = W.check_ime_replay(W.BAD_KEYS_IME_ONLY_KEY)
        self.assertTrue(bad, "출생 표본을 초록으로 봤다 — 판정기가 죽었다")
        self.assertTrue(
            any("글자" in line for line in bad),
            "빨갛기는 한데 **사유가 글자/자리를 말하지 않는다** — 다음 사람이 원인을 못 읽는다",
        )

    def test_static_predicate_alone_would_pass_this(self):
        """★★ **이 시험 하나가 P-58 의 「시험 1」이 필요한 이유다.**

        `.code` 를 읽지만 **고르는 것은 글자**인 배선 — 술어 ①은 초록, ⑦은 빨강.
        「물리 키로 고쳤다」는 보고가 이 모양으로 남아 있으면 관제실에서는 여전히
        j·k·m·r 이 죽는다.
        """
        src = W.BAD_KEYS_READS_CODE_BUT_SWITCHES_ON_KEY
        self.assertEqual(
            W.check_keys(src), [],
            "①이 이것을 이미 잡는다면 ⑦은 없어도 된다 — 그러면 이 시험을 지워라",
        )
        self.assertTrue(W.check_ime_replay(src), "⑦이 ①의 사각을 못 봤다")

    def test_the_failure_is_partial_and_that_is_the_trap(self):
        """숫자·Enter 는 입력기가 안 바꾼다 — **넷은 죽고 넷은 산다.**

        고장이 부분적이라 사람은 「가끔 안 먹는다」라고만 보고한다. 이 시험은
        그 비대칭 자체를 못박는다 — 모형이 그것을 잃으면 재현이 재현이 아니다.
        """
        src = W.BAD_KEYS_READS_CODE_BUT_SWITCHES_ON_KEY
        dead = [c for c in ("KeyJ", "KeyK", "KeyM", "KeyR")
                if W.dispatch(src, W.ime_event(c)) is None]
        alive = [c for c in ("Enter", "Digit1", "Digit2", "Digit3")
                 if W.dispatch(src, W.ime_event(c)) is not None]
        self.assertEqual(dead, ["KeyJ", "KeyK", "KeyM", "KeyR"])
        self.assertEqual(alive, ["Enter", "Digit1", "Digit2", "Digit3"])

    def test_english_keyboard_always_works_which_is_why_nobody_reproduced_it(self):
        """대조군 — 같은 배선이 영문 자판에서는 **여덟 자리 전부** 먹는다."""
        src = W.BAD_KEYS_READS_CODE_BUT_SWITCHES_ON_KEY
        for code in ("KeyJ", "KeyK", "KeyM", "KeyR", "Enter", "Digit1", "Digit2", "Digit3"):
            with self.subTest(code=code):
                self.assertIsNotNone(W.dispatch(src, W.latin_event(code)))

    def test_typing_target_is_still_ignored_under_the_ime(self):
        """P-58 의 셋째 조건 — 입력 칸에 초점이 있으면 무시한다. 한/영 무관."""
        self.assertIsNone(W.dispatch(W.GOOD_IME_KEYS, W.ime_event("KeyJ", target="INPUT")))
        self.assertIsNone(W.dispatch(W.GOOD_IME_KEYS, W.latin_event("KeyJ", target="TEXTAREA")))

    def test_unresolvable_wiring_is_grey_not_green(self):
        """배선을 못 풀면 **판정 불가**다. 0건 검사와 검사 못 함은 다르다."""
        bad = W.check_ime_replay("const x = 1;")
        self.assertTrue(any("판정 불가" in line for line in bad))


class HonestyTest(unittest.TestCase):
    """못 잰 것을 잰 척하지 않는다 — 그 약속을 시험이 지킨다."""

    def test_predicate_is_wired_into_the_host_gate(self):
        """⑦이 게이트 목록에 실려 있는가. 안 실리면 제품 소스는 아무도 안 본다."""
        labels = [label for label, _key, _fn in W.CHECKS]
        self.assertTrue(
            any("IME" in label for label in labels),
            "⑦이 CHECKS 에서 빠졌다 — 술어는 있는데 게이트가 안 부른다",
        )

    def test_three_lines_for_the_next_person_are_kept(self):
        """브라우저에서만 답이 나는 것 셋. 지우면 「모형=사실」이 되어 버린다."""
        self.assertEqual(len(W.BROWSER_TODO), 3)
        self.assertTrue(any("isComposing" in line for line in W.BROWSER_TODO))

    def test_model_basis_is_written_down(self):
        """모형이 무엇에 기대는지 적혀 있는가 — 틀리면 이 술어도 틀린다."""
        self.assertGreaterEqual(len(W.IME_MODEL_BASIS), 3)


class ProductSourceTest(unittest.TestCase):
    """제품 소스를 **읽을 수 있으면** 그것도 잰다. 못 읽으면 그 사실을 말한다."""

    def test_product_source_or_say_where_it_is_measured(self):
        src = _product_source()
        if src is None:
            # ★ 초록으로 넘어가지만 **아무것도 안 재고 넘어가지 않는다** — 제품 판정이
            #   호스트 게이트에 실려 있다는 것을 확인하고서야 넘어간다.
            labels = [label for label, _k, _f in W.CHECKS]
            self.assertTrue(
                any("IME" in label for label in labels),
                "제품 소스도 못 읽고 호스트 게이트에도 ⑦이 없다 — **아무도 안 재고 있다**",
            )
            self.assertIn("keys", [key for _l, key, _f in W.CHECKS if "IME" in _l],
                          "⑦이 useQueueKeys.ts 를 보고 있지 않다")
            return
        self.assertEqual(
            W.check_ime_replay(src), [],
            "제품의 단축키 배선이 한글 입력기에서 죽는다",
        )
