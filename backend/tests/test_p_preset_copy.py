# -*- coding: utf-8 -*-
"""P-51 — 「프리셋」을 **「보기」**로 (차선 C · 2026-09-05 턴 E).

이 파일이 묻는 것
-----------------
① **사전에 있는 낱말만 쓰는가.** 조율자가 GX-COPY §5(턴 E)에 넉 자를 이미
   넣어 두었다 — 미처리 보기 · 지난 12시간 보기 · 내 담당 보기 · 시스템 보기.
   화면이 다른 말을 쓰면 그것은 「고쳤다」가 아니라 **사전을 두 벌로 만든 것**이다.
② **「프리셋」이 사용자에게 안 보이는가.** 「프리셋」은 우리 말이다. 주석에는
   남아도 좋다 — 남는 것이 옳다(왜 바꿨는지가 거기 있다). **렌더되는 자리**에만
   없으면 된다.
③ **계약은 안 움직였는가.** 이것이 이 파일의 진짜 이유다.
   표시 이름을 바꾸는 일은 쉬워 보여서 **질의 값까지 같이 바꾸기 쉽다**
   (`?preset=unhandled` → `?preset=미처리 보기`). 그 순간 검수 촬영과 시나리오
   주행이 **한꺼번에** 죽고, 죽은 이유가 「글자를 바꿨다」라는 것은 아무도
   그 자리에서 못 읽는다. 그래서 **값과 이름을 갈라서** 못 박는다.

무엇을 다시 묻지 않나
---------------------
「대장 언어가 화면에 새는가」는 `scripts/verify_ui_copy.py` 가 전수로 잰다.
여기서 다시 물으면 같은 사실을 두 벌로 재고, 기준선이 두 곳에서 늙는다.
"""
from __future__ import annotations

from pathlib import Path

from django.test import SimpleTestCase

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "docs/design/GX-COPY_v1.md(사전 정본) · "
    "frontend/src/features/dsm/pages/EventList.tsx(화면 실물) · "
    "scripts/capture_screens.py(질의 계약을 실제로 두드리는 자리) — 합성 더미 없음"
)

#: 사전이 정한 넉 자. **여기에 적는 것은 인용이지 판정이 아니다** — 낱말을 고르는
#: 것은 조율자의 일이고(GX-COPY §5 · 2026-09-05 턴 E), 이 시험은 화면이 그것을
#: 그대로 쓰는지만 본다.
VIEW_LABELS = ("미처리 보기", "지난 12시간 보기", "내 담당 보기", "시스템 보기")

#: 질의 값 — **계약**이다. 표시 이름과 **다른 것**이고, 다른 채로 있어야 한다.
PRESET_KEYS = ("unhandled", "recent", "mine", "system")

#: 우리 말. 렌더되는 자리에 있으면 안 된다.
OUR_WORD = "프리셋"


def _read(*bases_and_tail) -> str | None:
    """저장소 파일 원문. 못 읽으면 `None` — **회색은 초록이 아니다**(D-301)."""
    bases, tail = bases_and_tail[0], bases_and_tail[1]
    for base in bases:
        cand = Path(base).joinpath(*tail)
        if cand.is_file():
            return cand.read_text(encoding="utf-8")
    return None


def _here_parents():
    return list(Path(__file__).resolve().parents)


def _docs(*parts) -> str | None:
    """사전·설계 문서. 컨테이너는 `/docs`, 호스트는 `<저장소>/docs` 다."""
    bases = [Path("/docs")]
    bases += [p / "docs" for p in _here_parents() if (p / "docs").is_dir()]
    return _read(bases, parts)


def _scripts(*parts) -> str | None:
    """도구. 컨테이너는 `/repo/scripts`, 호스트는 `<저장소>/scripts` 다."""
    bases = [Path("/repo/scripts")]
    bases += [p / "scripts" for p in _here_parents() if (p / "scripts").is_dir()]
    return _read(bases, parts)


def _screen(*parts) -> str | None:
    """화면 파일. ⚠ gx-shell 에는 `frontend/` 가 **없다** [실측 2026-09-05] —
    backend·docs·scripts 만 마운트돼 있다. 못 읽으면 `None` 을 돌려주고 부르는
    쪽이 **「못 쟀다」로** 남긴다(통과시키지 않는다)."""
    tail = ("src", "features", "dsm", "pages") + parts
    bases = [Path("/repo/frontend"), Path("/frontend")]
    bases += [p / "frontend" for p in _here_parents() if (p / "frontend").is_dir()]
    return _read(bases, tail)


def _uncommented(source: str) -> list[tuple[int, str]]:
    """주석이 **아닌** 자리만 (줄번호, 남은 글자). 「프리셋」이 주석에 남는 것은
    옳다 — 왜 바꿨는지가 거기 있다. 이 시험이 잡을 것은 **렌더되는 자리**뿐이다.

    ★ 줄 머리로만 가르면 **안 된다** [실측 2026-09-05 · 이 시험이 그렇게 시작했다].
      이 저장소의 화면 주석은 `{/* … */}` 여러 줄짜리이고, 둘째 줄부터는 아무
      표시 없이 그냥 글자다. 그래서 `/* … */` 를 **상태로** 따라간다.
      완전한 파서는 아니다(문자열 안의 `/*` 는 안 가린다) — 그런 줄이 이 화면
      파일들에 없다는 것을 보고 멈춘다. 여기서 더 키우면 **이 시험이 시험할
      것보다 커진다.**
    """
    out, in_block = [], False
    for i, line in enumerate(source.splitlines(), start=1):
        rest, kept = line, ""
        while rest:
            if in_block:
                close = rest.find("*/")
                if close < 0:
                    rest = ""
                    break
                rest = rest[close + 2:]
                in_block = False
                continue
            opener = rest.find("/*")
            liner = rest.find("//")
            if liner >= 0 and (opener < 0 or liner < opener):
                kept += rest[:liner]
                rest = ""
                break
            if opener < 0:
                kept += rest
                rest = ""
                break
            kept += rest[:opener]
            rest = rest[opener + 2:]
            in_block = True
        if kept.strip():
            out.append((i, kept))
    return out


class TheDictionaryStillHasTheFourWordsTest(SimpleTestCase):
    """① 사전이 정본이다 — 화면이 아니라 **사전**을 먼저 본다."""

    def test_the_four_words_are_in_the_dictionary(self) -> None:
        copy = _docs("design", "GX-COPY_v1.md")
        self.assertIsNotNone(copy, "사전(GX-COPY_v1.md)을 못 읽었다")
        for word in VIEW_LABELS:
            self.assertIn(word, copy,
                          "「%s」가 사전에 없다 — 사전에 없는 말을 화면에 쓰면 "
                          "그것은 새 낱말을 만든 것이다" % word)


class TheScreenUsesOnlyDictionaryWordsTest(SimpleTestCase):
    """② 화면이 **그 넉 자 그대로** 쓰는가."""

    def _source(self) -> str:
        src = _screen("EventList.tsx")
        if src is None:
            #: ★ **회색은 초록이 아니다.** 통과시키지 않고 「못 쟀다」로 남긴다.
            #:   마운트가 생기면 이 자리는 저절로 재기 시작한다 — 고칠 것이 없다.
            self.skipTest("frontend 가 이 컨테이너에 마운트되지 않았다 — "
                          "gx-shell 에 읽기전용 마운트가 필요하다(조율자 배선). "
                          "호스트에서는 같은 대조가 초록이고 명령·출력은 보고에 있다")
        return src

    def test_every_button_carries_the_dictionary_word(self) -> None:
        src = self._source()
        body = "\n".join(line for _, line in _uncommented(src))
        for word in VIEW_LABELS:
            # 「지난 12시간 보기」는 템플릿 문자열로 만들어진다(`${RECENT_HOURS}`) —
            # 그러므로 원문에서는 낱말의 **양 끝**으로 찾는다.
            if word.startswith("지난 "):
                self.assertIn("시간 보기", body,
                              "「지난 N시간 보기」가 화면에 없다")
                continue
            self.assertIn(word, body, "「%s」가 화면에 없다" % word)

    def test_our_word_is_not_rendered_anywhere(self) -> None:
        src = self._source()
        leaks = [(n, ln.strip()) for n, ln in _uncommented(src) if OUR_WORD in ln]
        self.assertEqual(leaks, [],
                         "「%s」가 렌더되는 자리에 남아 있다: %r — 주석에는 남겨도 "
                         "좋지만 화면에는 안 된다" % (OUR_WORD, leaks))

    def test_the_neighbouring_screens_are_clean_too(self) -> None:
        """전수다 — 한 화면만 고치면 두 화면이 같은 것을 다르게 부른다."""
        for name in ("ControlDashboard.tsx", "Onboarding.tsx"):
            src = _screen(name)
            if src is None:
                self.skipTest("frontend 가 이 컨테이너에 마운트되지 않았다")
            leaks = [(n, ln.strip()) for n, ln in _uncommented(src) if OUR_WORD in ln]
            self.assertEqual(leaks, [],
                             "%s 의 렌더되는 자리에 「%s」가 있다: %r"
                             % (name, OUR_WORD, leaks))


class TheQueryContractDidNotMoveTest(SimpleTestCase):
    """③ ★ **값은 그대로다.** 이름을 바꾸다 값을 바꾸면 계약이 바뀐다.

    이 대조는 화면 마운트가 없어도 **잰다** — 계약을 실제로 두드리는 자리가
    `scripts/capture_screens.py` 이고 그것은 컨테이너에 마운트돼 있다.
    """

    def test_the_capture_tool_still_knocks_the_four_english_keys(self) -> None:
        tool = _scripts("capture_screens.py")
        self.assertIsNotNone(tool, "capture_screens.py 를 못 읽었다")
        for key in PRESET_KEYS:
            self.assertIn("preset=%s" % key, tool,
                          "검수 촬영이 `?preset=%s` 를 더 이상 두드리지 않는다 — "
                          "표시 이름을 바꾸면서 **질의 값까지** 바꾼 것이다" % key)

    def test_the_screen_still_writes_the_english_keys_into_the_address(self) -> None:
        src = _screen("EventList.tsx")
        if src is None:
            self.skipTest("frontend 가 이 컨테이너에 마운트되지 않았다")
        body = "\n".join(line for _, line in _uncommented(src))
        self.assertIn("setParam('preset'", body,
                      "주소에 `preset` 을 쓰는 자리가 사라졌다 — 프리셋이 주소에 "
                      "살지 않으면 검수 촬영이 그 화면에 못 간다")
        for key in PRESET_KEYS:
            self.assertIn("'%s'" % key, body,
                          "질의 값 `%s` 가 화면에서 사라졌다" % key)

    def test_the_label_and_the_key_are_not_the_same_string(self) -> None:
        """★ 표시 이름과 질의 값이 **같아지면** 계약이 표시에 끌려간다."""
        for label in VIEW_LABELS:
            self.assertNotIn(label, PRESET_KEYS,
                             "표시 이름이 질의 값이 됐다: %s" % label)
