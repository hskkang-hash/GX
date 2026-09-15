#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""UX-20 — **화면이 우리 대장의 말로 말하는가.** 제품 언어 판정기 (P-29).

무엇이 이 판정기를 만들었나
---------------------------
화면 24장을 한 장씩 읽었더니 결함 31건이 나왔고 **11장의 뿌리가 하나**였다:

    「UX-17 훈련 모드」  「표시 7건(요청 상한 50건)」  「패널 상태 data 0/0 loading 0/0」
    「`response_state=occurred` 로 걸러 준 목록입니다」  「data_source = live」
    「종결(으)로」  「Network Error」

D-번호 · 절 ID · 백틱 · 마크다운 원문 · 영문 열거값 · 개발 계수기가 **사용자 본문**에 있었다.
뿌리는 「사유를 화면에 적어라」였다 — 시킨 쪽의 잘못이고, 정정은 사전과 이 판정기다.
사전은 `docs/design/GX-COPY_v1.md` 이고, 이 파일은 그 사전을 **강제하는 쪽**이다.

★ 래칫이다 (D-311). 오늘의 빚을 **이름으로** 잠그고 **새로 생기는 것만** 막는다.
  왜 처음부터 exit 1 이 아닌가: 오늘 31건이 걸린 채로 병합을 막으면 사람이 게이트를 끈다.
  꺼진 게이트는 없는 게이트보다 나쁘다. 그래서 **오늘 수를 적어 두고**, 그 수가 줄지 않으면
  줄지 않았다고 말하고, **새 것이 하나라도 생기면 exit 1** 이다.

    python scripts/verify_ui_copy.py            # 판정 (새 위반만 막는다 · 잔여 N 을 말한다)
    python scripts/verify_ui_copy.py --list     # 걸린 자리 전수
    python scripts/verify_ui_copy.py --strict   # 래칫 없이 — 잔여가 0 이어야 통과
    python scripts/verify_ui_copy.py --freeze   # 오늘의 빚을 기준선에 잠근다
    python scripts/verify_ui_copy.py --self-test

주석은 세지 않는다 — 금지된 것은 「사용자 본문」이지 「소스」가 아니다.
주석을 걷어 내는 일은 `verify_ui_secrets.strip_comments` 가 한다. **두 벌을 두지 않는다**
(D-369) — 두 벌은 반드시 어긋나고, 어긋나면 한쪽이 조용히 아무것도 안 본다.

호스트에서 돈다 — Django 가 필요 없다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from verify_ui_secrets import frontend_files, strip_comments  # noqa: E402

BASELINE = ROOT / "docs" / "agent" / "evidence" / "UX-20" / "copy_baseline.txt"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 대장 언어 — 사전 §4 「사용자 본문에 쓰지 않는 것」이 이름으로 적은 것들
# ═══════════════════════════════════════════════════════════════════════════
PATTERNS: tuple[tuple[str, str], ...] = (
    #: 결정 번호. 뒤에 숫자가 더 붙으면 장비 일련번호다 — 그것은 우리 대장이 아니다.
    ("결정 번호", r"D-\d{3}(?!\d)"),
    #: 절 ID. 화면 제목이 「UX-17 훈련 모드」였다 — 절 이름은 제목이 아니다.
    ("절 ID", r"\b(?:UX|SEC|OPS|QA|LAW|PERF|ISO|F|P|W|AC|FR|NFR|DA)-\d{1,2}\b"),
    #: 백틱과 마크다운 강조. **렌더되지 않고 그대로 보인다** — 화면에 별 두 개가 뜬다.
    ("백틱", r"`"),
    ("마크다운 강조", r"\*\*"),
    #: 영문 열거값이 그대로 뜨는 자리.
    ("출처 칩", r"data_source\s*="),
    ("영문 열거값", r"\b(?:occurred|acknowledged|in_progress|confirmed|rejected|"
                    r"response_state|event_type|severity)\b\s*[=:]"),
    #: 내부 경로 · 도구 이름. 「어디에 없는지」는 사용자에게 뜻이 없다.
    ("내부 경로", r"(?:scripts/|backend/|kernels\.|frontend/src)"),
)
COMPILED = tuple((name, re.compile(rx)) for name, rx in PATTERNS)

#: ★ **출생 표본** (D-310) — 그날 화면에 실제로 떠 있던 제목과 문단이다.
BIRTH_SAMPLES = (
    "UX-17 훈련 모드 — 이 화면은 **로그 어댑터로만** 보냅니다",
    "`response_state=occurred` 로 걸러 준 목록입니다",
    "data_source = live",
)

#: ★ **출생 표본 ②** (P-77 · 2026-09-06) — 앞선 정규식 파서가 **통째로 못 보던** 두 자리.
#:   둘 다 JSX 본문에 `{…}` 보간이 끼어 있고, 그래서 `>…<` 정규식이 배제했다.
#:   화면에는 떠 있었고 게이트는 「잔여 0 · 통과」를 냈다.
BIRTH_JSX: tuple[tuple[str, str], ...] = (
    ("<Tag>data_source = {current.data_source}</Tag>", "출처 칩"),
    ("""<Paragraph>같은 카메라·같은 유형이{' '}
     {Math.round(w / 60)}분 창 안에 연속으로 나면
     카드 한 장에 묶입니다. F-14 통계는 왼쪽 수를 봅니다.</Paragraph>""", "절 ID"),
)

#: 본 비율의 바닥. **이보다 낮으면 판정하지 않는다**(회색 · exit 2) —
#: 커버리지를 모르는 게이트는 판정한 것이 아니다.
COVERAGE_FLOOR = 0.90

#: 사용자 본문이 사는 곳. 여기 밖(설정·라우터·서비스)의 문자열은 화면에 뜨지 않는다.
#: ⚠ 좁게 잡는다 — 넓게 잡으면 첫 수가 수백이 되고, 수백은 아무도 안 고친다.
#: ★ [P-78 · 2026-09-06 턴 H] **로그인 화면을 범위에 넣었다.**
#:   직전 턴 실측에서 그 화면의 빈 값 문구가 영문(`This field is required.`)이었고,
#:   다섯 갈래는 아무 말도 안 했다. 그 자리를 우리 층으로 가져오면서 **판정기의 눈도
#:   함께 옮긴다** — 안 보는 자리에 새 문구를 쌓으면 사전이 그 화면을 못 따라간다.
#:   ⚠ 범위를 넓히면 잔여가 늘 수 있다. 늘면 늘었다고 적는다(래칫이 그 일을 한다).
SCOPE = ("frontend/src/features/dsm/", "frontend/src/features/mobile/",
         "frontend/src/features/login/", "frontend/src/features/LoginMobile/")


def in_scope(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(rel.startswith(prefix) for prefix in SCOPE)


#: 한글이 한 자라도 있는가. **이것이 「사용자 본문」의 술어다.**
#:
#:   왜 이 술어인가 [실측 2026-09-26]: 처음에는 줄 전체를 보았고 127건이 나왔는데
#:   그중 대부분이 코드였다 — `` `/m/events/${id}` `` 같은 템플릿 경로, `event.severity`
#:   같은 식별자. 그 수를 그대로 빚으로 잠그면 **기준선이 코드로 채워지고**, 진짜 빚
#:   서른한 건이 그 안에 묻힌다. 사용자가 읽는 것은 **한국어 문장**이다.
#:
#:   ⚠ 놓치는 쪽으로 틀린다. 순수 영문 라벨(`Add New Device`)은 이 술어를 지나간다 —
#:     그것은 UX-21(역할별 메뉴·영문 CRUD)의 자리이고, 이 판정기의 자리가 아니다.
HANGUL = re.compile(r"[가-힣]")

# ═══════════════════════════════════════════════════════════════════════════
# JSX 전수 파서 — **보간과 붙은 본문을 놓치지 않는다** (P-77 · 2026-09-06 · 차선 Q)
# ═══════════════════════════════════════════════════════════════════════════
#: ★ **출생 표본 ②** — 이 파서를 만들게 한 바로 그 두 자리다 [실측 2026-09-06 · 턴 H].
#:
#:   앞선 술어는 이랬다:
#:
#:       JSX_TEXT = re.compile(r">([^<>{}]*[가-힣][^<>{}]*)<")
#:
#:   `{}` 를 배제했기 때문에 **보간이 한 번이라도 끼면 그 본문 전체가 안 보였다.**
#:   그래서 `DrillMode.tsx` 의 <Tag>data_source = {current.data_source}</Tag> 가
#:   화면에 떠 있는데 게이트는 「잔여 0 · 통과」를 냈고, D-433 이 그 수를 근거로
#:   UX-20 을 닫았다. `FocusQueue.tsx` 의 「… F-14 통계는 왼쪽 수를 봅니다」도
#:   같은 사각이었다. **못 본 조각이 본 조각의 41%였다.**
#:
#:   그래서 이제 **JSX 로 읽는다** — 텍스트 노드 · 문자열 리터럴 · 템플릿 리터럴 조각 ·
#:   속성값(placeholder·title·aria-label·alt …) 전수.

_IDENT = re.compile(r"[A-Za-z0-9_$]")

#: JSX 도 정규식도 **식이 올 자리에서만** 시작한다. 앞 토큰이 식별자거나 닫는 괄호면
#: 그 `<` 는 `a < b` 이거나 `Array<T>` 다. 이 술어가 없으면 파서가 코드에서 샌다.
_EXPR_WORDS = frozenset(("return", "yield", "await", "typeof", "case", "in", "of",
                         "default", "else", "do", "void", "new", "delete"))


class Frag(NamedTuple):
    """사용자가 읽는 조각 하나. `start`·`end` 는 **소스 안의 자리**다 — 본 비율은
    이 자리들로 잰다(파서에게 「다 봤느냐」를 묻지 않기 위해서다)."""

    start: int
    end: int
    line: int
    kind: str
    text: str


def jsx_fragments(src: str) -> list[Frag]:
    """주석을 걷어 낸 소스를 **JSX 로 읽어** 사용자가 읽는 조각 전수를 뽑는다.

    되돌아가지 않는 한 벌 훑기다. 다섯 자리를 본다:

      ``문자열``    `'…'` · `"…"` 의 몸통
      ``템플릿``    백틱 문자열의 몸통 — **보간으로 잘라서** 조각마다 낸다
                    (사용자가 보는 것은 보간된 결과이지 그 안의 코드가 아니다)
      ``JSX본문``   태그 사이의 텍스트 노드 — **중괄호로 잘라서** 조각마다 낸다.
                    ★ 여기가 41%가 숨어 있던 자리다
      ``속성:이름`` placeholder="…" 처럼 속성에 박힌 문자열 (이름을 함께 남긴다)
      그리고 위 넷 안의 중괄호는 다시 코드로 읽는다 — 중첩은 깊이 제한 없이 돈다
    """
    frags: list[Frag] = []
    n = len(src)
    i = 0
    line = 1

    def adv(k: int = 1) -> None:
        nonlocal i, line
        for _ in range(k):
            if i < n and src[i] == "\n":
                line += 1
            i += 1

    def expr_position() -> bool:
        """지금 자리에 **식이 올 수 있는가.** `<` 와 `/` 의 뜻을 이것이 가른다."""
        j = i - 1
        while j >= 0 and src[j] in " \t\r\n":
            j -= 1
        if j < 0:
            return True
        if _IDENT.match(src[j]):
            k = j
            while k >= 0 and _IDENT.match(src[k]):
                k -= 1
            return src[k + 1:j + 1] in _EXPR_WORDS
        return src[j] not in ")]"

    def take_string() -> None:
        quote, start_line = src[i], line
        adv()
        start = i
        while i < n and src[i] != quote:
            if src[i] == "\\":
                adv(2)
                continue
            adv()
        frags.append(Frag(start, i, start_line, "문자열", src[start:i]))
        adv()

    def take_template() -> None:
        adv()                                   # 여는 백틱
        start, start_line = i, line
        while i < n and src[i] != "`":
            if src[i] == "\\":
                adv(2)
                continue
            if src[i] == "$" and i + 1 < n and src[i + 1] == "{":
                frags.append(Frag(start, i, start_line, "템플릿", src[start:i]))
                adv(2)
                take_code(closing_brace=True)
                start, start_line = i, line
                continue
            adv()
        frags.append(Frag(start, i, start_line, "템플릿", src[start:i]))
        adv()

    def take_regex() -> None:
        """정규식 리터럴을 통째로 넘긴다. **넘기지 않으면 따옴표가 든 정규식 하나가
        파서를 문자열 안으로 끌고 들어가고, 그 뒤 파일 전체가 안 보인다.**"""
        adv()
        in_class = False
        while i < n:
            ch = src[i]
            if ch == "\\":
                adv(2)
                continue
            if ch == "\n":
                return                          # 줄을 넘는 정규식은 없다 — 나눗셈이었다
            if ch == "[":
                in_class = True
            elif ch == "]":
                in_class = False
            elif ch == "/" and not in_class:
                adv()
                return
            adv()

    def take_code(closing_brace: bool = False) -> None:
        depth = 0
        while i < n:
            ch = src[i]
            if ch in "'\"":
                take_string()
                continue
            if ch == "`":
                take_template()
                continue
            if ch == "/" and i + 1 < n and src[i + 1] not in "/*" and expr_position():
                take_regex()
                continue
            if ch == "{":
                depth += 1
                adv()
                continue
            if ch == "}":
                if closing_brace and depth == 0:
                    adv()
                    return
                depth = max(0, depth - 1)
                adv()
                continue
            if ch == "<" and expr_position() and take_element():
                continue
            adv()

    def take_element() -> bool:
        """`<` 자리에서 부른다. **JSX 가 아니면 한 글자도 안 먹고 `False`.**"""
        nonlocal i, line
        snap = (i, line)
        adv()
        if i < n and src[i] == ">":             # 조각 태그
            adv()
            take_children()
            return True
        if i >= n or not (src[i].isalpha() or src[i] in "_$"):
            i, line = snap
            return False
        while i < n and (src[i].isalnum() or src[i] in "_$.:-"):
            adv()
        if take_attrs():
            return True                         # 자기 닫음 — 자식이 없다
        take_children()
        return True

    def take_attrs() -> bool:
        """속성부를 읽는다. 자기 닫음으로 끝나면 `True`, 자식이 이어지면 `False`."""
        while i < n:
            ch = src[i]
            if ch == "/" and i + 1 < n and src[i + 1] == ">":
                adv(2)
                return True
            if ch == ">":
                adv()
                return False
            if ch.isalpha() or ch in "_$":
                at = i
                while i < n and (src[i].isalnum() or src[i] in "_$-:."):
                    adv()
                name = src[at:i]
                while i < n and src[i] in " \t\r\n":
                    adv()
                if i < n and src[i] == "=":
                    adv()
                    while i < n and src[i] in " \t\r\n":
                        adv()
                    if i < n and src[i] in "'\"":
                        quote, start_line = src[i], line
                        adv()
                        start = i
                        while i < n and src[i] != quote:
                            if src[i] == "\\":
                                adv(2)
                                continue
                            adv()
                        frags.append(Frag(start, i, start_line,
                                          f"속성:{name}", src[start:i]))
                        adv()
                    elif i < n and src[i] == "{":
                        adv()
                        take_code(closing_brace=True)
                continue
            if ch == "{":                       # 펼침 속성
                adv()
                take_code(closing_brace=True)
                continue
            if ch in "'\"":
                take_string()
                continue
            adv()
        return True

    def take_children() -> None:
        nonlocal i, line
        start, start_line = i, line

        def flush() -> None:
            nonlocal start, start_line
            body = src[start:i]
            if body.strip():
                frags.append(Frag(start, i, start_line, "JSX본문", body))
            start, start_line = i, line

        while i < n:
            ch = src[i]
            if ch == "{":
                flush()
                adv()
                take_code(closing_brace=True)
                start, start_line = i, line
                continue
            if ch == "<":
                flush()
                if i + 1 < n and src[i + 1] == "/":
                    adv(2)
                    while i < n and src[i] != ">":
                        adv()
                    adv()
                    return
                snap = (i, line)
                if not take_element():
                    i, line = snap
                    adv()
                start, start_line = i, line
                continue
            adv()
        flush()

    take_code()
    return frags


def user_texts(src: str) -> list[tuple[int, str]]:
    """주석을 걷어 낸 소스에서 **사용자가 읽는 글자** 전수 — `(줄, 조각)`.

    줄 번호는 조각이 **시작하는 줄**이다 — 여러 줄 본문이면 첫 줄을 가리킨다.
    """
    return [(f.line, f.text) for f in jsx_fragments(src)]


def hangul_coverage(src: str, frags: list[Frag]) -> tuple[int, int]:
    """`(조각이 덮은 한글 글자 수, 소스의 한글 글자 수)` — **본 비율**의 분자와 분모.

    ★ **왜 파서 밖의 잣대인가.** 바뀐 파서에게 「다 봤느냐」를 물으면 언제나 100%다.
      그 대답은 아무것도 재지 않는다 — 41%를 못 보던 그날의 파서도 자기 기준으로는
      100%였다. 그래서 파서가 만들지 않은 수를 분모로 쓴다: **주석을 걷어 낸 화면
      소스에 남은 한글**은 사실상 전부 사용자 본문이고, 그 글자가 어느 조각에도
      안 담기면 그만큼을 **못 본 것**이다. 파서가 어디선가 새면 이 수가 떨어진다.

    ⚠ 이 잣대가 못 세는 것: 순영문 본문(data_source = live)에는 한글이 없다.
      그 자리는 패턴이 본다 — 본 비율은 **파서가 샜는지**를 재는 수이지
      「빠짐없이 걸렀는가」를 재는 수가 아니다.
    """
    total = len(HANGUL.findall(src))
    if total == 0:
        return 0, 0
    seen = bytearray(len(src))
    for f in frags:
        for pos in range(f.start, min(f.end, len(src))):
            seen[pos] = 1
    covered = sum(1 for pos, ch in enumerate(src) if seen[pos] and HANGUL.match(ch))
    return covered, total


def scan_line(line: str) -> list[str]:
    """한 조각(문자열 몸통 · JSX 본문)에서 걸린 패턴 이름들."""
    return [name for name, rx in COMPILED if rx.search(line)]


def norm(snippet: str) -> str:
    """기준선 열쇠에 쓸 모양. **줄 번호를 쓰지 않는다** — 줄은 늘 밀리고,
    밀린 줄로 잠그면 다음 커밋에서 빚 전부가 「새 위반」으로 되살아난다."""
    #: ★ 자르고 나서 다시 `strip()` 한다 [실측 2026-09-26]. 100자에서 잘린 자리가
    #:   공백이면 열쇠 끝에 공백이 남고, **pre-commit 의 trailing-whitespace 훅이 그것을
    #:   지운다.** 그러면 어제 잠근 빚 한 줄이 오늘 「새 위반」으로 되살아난다 —
    #:   게이트가 자기 기준선을 스스로 깨뜨리는 모양이다.
    return " ".join(snippet.split())[:100].strip()


def scan() -> tuple[int, list[tuple[str, int, str, str]], int, int]:
    """`(본 파일 수, [(상대경로, 줄, 패턴, 발췌)], 덮은 한글, 전체 한글)`."""
    findings: list[tuple[str, int, str, str]] = []
    files = [p for p in frontend_files() if in_scope(p)]
    covered = total = 0
    for path in files:
        try:
            src = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        body = strip_comments(src)
        frags = jsx_fragments(body)
        c, t = hangul_coverage(body, frags)
        covered += c
        total += t
        for f in frags:
            for name in scan_line(f.text):
                findings.append((rel, f.line, name, norm(f.text)))
    return len(files), findings, covered, total


def key(f: tuple[str, int, str, str]) -> str:
    rel, _lineno, name, snippet = f
    return f"{rel}\t{name}\t{snippet}"


def load_baseline() -> set[str]:
    if not BASELINE.exists():
        return set()
    return {ln for ln in BASELINE.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")}


def self_test() -> int:
    fails = 0
    for sample in BIRTH_SAMPLES:
        if not scan_line(sample):
            print(f"[COPY] 자기시험 FAIL 출생 표본을 못 잡았다: {sample}")
            fails += 1
    #: ★ **출생 표본 ②** (P-77) — 파서가 통째로 못 보던 두 자리. 조각 뽑기까지
    #:   끝까지 돌린다. `scan_line` 만 시험하면 **파서가 눈이 멀어도 초록**이다 —
    #:   그것이 2026-09-06 까지 이 게이트가 있던 상태다.
    for src, want in BIRTH_JSX:
        hits = {name for _line, text in user_texts(src) for name in scan_line(text)}
        if want not in hits:
            print(f"[COPY] 자기시험 FAIL 출생 표본 ②를 못 잡았다 ({want}): "
                  f"{norm(src)[:60]}")
            fails += 1
        covered, total = hangul_coverage(src, jsx_fragments(src))
        if total and covered != total:
            print(f"[COPY] 자기시험 FAIL 출생 표본 ②의 한글 {total}자 중 "
                  f"{covered}자만 조각에 담겼다 — 파서가 샌다")
            fails += 1
    # 음성 ① — 주석은 소스의 자리다
    if scan_line(strip_comments("// UX-17 · D-421 · `kernels.k1_event`" + chr(10)).strip()):
        print("[COPY] 자기시험 FAIL 주석을 잡았다 — 소스가 아니라 화면을 본다")
        fails += 1
    # 음성 ② — 사전대로 고친 문장은 잡히면 안 된다
    for good in ("'훈련 모드'", "'미처리'", "'연계 대기'", "'사진을 불러오지 못했습니다'"):
        if scan_line(good):
            print(f"[COPY] 자기시험 FAIL 사전대로 고친 문장을 잡았다: {good}")
            fails += 1
    # 음성 ③ — 열쇠가 줄 번호를 타면 안 된다 (한 줄 밀면 빚이 되살아난다)
    a = key(("x.tsx", 10, "백틱", norm("  const a = `b`;")))
    b = key(("x.tsx", 99, "백틱", norm("const a = `b`;")))
    if a != b:
        print("[COPY] 자기시험 FAIL 줄 번호·들여쓰기가 열쇠를 바꾼다 — 빚이 되살아난다")
        fails += 1
    # 음성 ④ — **부등호는 태그가 아니다.** 이 술어가 없으면 파서가 코드로 새고,
    #          샌 파서는 조용히 파일 하나를 통째로 안 본다.
    for code in ("if (a < b && c > d) { doIt(); }",
                 "const m: Array<string> = useMemo<Foo>(() => [], []);"):
        if [t for _l, t in user_texts(code) if HANGUL.search(t)]:
            print(f"[COPY] 자기시험 FAIL 부등호·제네릭을 JSX 로 읽었다: {code}")
            fails += 1
    # 음성 ⑤ — 따옴표가 든 정규식 하나가 파서를 끌고 가면 안 된다
    derail = "const rx = /['\"]/; const msg = '사진을 불러오지 못했습니다';"
    if "사진을 불러오지 못했습니다" not in [t for _l, t in user_texts(derail)]:
        print("[COPY] 자기시험 FAIL 정규식 뒤의 본문을 못 봤다 — 파서가 새고 있다")
        fails += 1
    if fails:
        print(f"[COPY] 자기시험 {fails}건 실패")
        return 1
    print(f"[COPY] 자기시험 통과 — 양성 {len(BIRTH_SAMPLES)}(문구) + "
          f"{len(BIRTH_JSX)}(JSX 파서) · 음성 8")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="UX-20 제품 언어 판정기")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--strict", action="store_true", help="래칫 없이 — 잔여 0 이어야 통과")
    ap.add_argument("--freeze", action="store_true", help="오늘의 빚을 기준선에 잠근다")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    seen, findings, covered, total = scan()
    if seen == 0:
        print(f"[COPY] **판정 불가** — {' · '.join(SCOPE)} 에서 파일을 한 개도 못 읽었다 "
              "(0건 검사와 검사 못 함은 다르다 · D-301)")
        return 2

    #: ★ **첫 줄이 본 비율이다** (P-77). 커버리지를 모르는 게이트는 판정한 것이 아니다 —
    #:   41%를 못 보던 그날의 게이트도 「잔여 0 · 통과」라고 적었다.
    ratio = (covered / total) if total else 0.0
    print(f"[COPY] **본 비율 {ratio:.0%}** — 화면 소스의 한글 {total:,}자 중 "
          f"{covered:,}자가 조각에 담겼다 (기준 {COVERAGE_FLOOR:.0%})")
    print(f"[COPY] [입력] {seen}개 화면 파일 (주석 걷어낸 뒤) · 패턴 {len(COMPILED)}종")

    if total and ratio < COVERAGE_FLOOR:
        print(f"[COPY] **판정 불가** — 본 비율 {ratio:.0%} 가 기준 {COVERAGE_FLOOR:.0%} "
              "아래다. 파서가 화면 글자의 일부를 못 보고 있고, **못 본 자리에서 나온 "
              "「잔여 0」은 사실이 아니다** (D-301). 회색으로 둔다")
        return 2

    if args.freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# UX-20 제품 언어 — **오늘의 빚**. 줄이는 것만 허용한다 (래칫 · D-311).",
                 "# 열쇠: 파일<TAB>패턴<TAB>발췌(공백 정규화). 줄 번호는 쓰지 않는다.",
                 f"# 잠근 날: 2026-09-06(턴 I) · "
                 f"{len(set(map(key, findings)))}건 · 본 비율 {ratio:.0%}",
                 ""]
        lines += sorted({key(f) for f in findings})
        BASELINE.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
        print(f"[COPY] 기준선에 {len(set(map(key, findings)))}건을 잠갔다 → "
              f"{BASELINE.relative_to(ROOT).as_posix()}")
        return 0

    baseline = load_baseline()
    fresh = [f for f in findings if key(f) not in baseline]
    seen_keys = {key(f) for f in findings}
    paid = sorted(baseline - seen_keys)

    if args.list:
        for rel, lineno, name, snippet in findings:
            mark = "NEW " if key((rel, lineno, name, snippet)) not in baseline else "빚  "
            print(f"          {mark}{rel}:{lineno}  [{name}]  {snippet}")

    print(f"[COPY] 잔여 {len(seen_keys)}건 (기준선 {len(baseline)}건 · 갚은 것 {len(paid)}건)")

    if args.strict and seen_keys:
        print(f"[COPY] FAIL --strict — 잔여 {len(seen_keys)}건")
        return 1

    if fresh:
        for rel, lineno, name, snippet in fresh:
            print(f"[COPY] FAIL 새 위반 {rel}:{lineno}  [{name}]  {snippet}")
        print(f"[COPY] FAIL 새로 생긴 대장 언어 {len(fresh)}건 — "
              "사전에 없는 문구는 만들지 않는다 (docs/design/GX-COPY_v1.md)")
        return 1

    #: ★ [P-87 · 2026-09-06 턴 I] **「파일이 없다」와 「빚이 0이다」는 다른 칸이다.**
    #:   여기가 `if not baseline:` 이었다 — 빚을 전부 갚고 기준선을 0건으로 잠그면
    #:   그 순간 게이트가 「기준선이 없다 · 회색」을 냈다. 다 갚은 것이 못 잰 것과
    #:   같은 칸에 들어간 것이다. 「없다」는 **파일의 부재**로만 판정한다.
    if not BASELINE.exists():
        print("[COPY] **판정 불가** — 기준선 파일이 없다 "
              "(`--freeze` 로 오늘의 빚을 먼저 잠근다)")
        return 2
    print("[COPY] 통과 — 새로 생긴 대장 언어 0건")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(__file__)
    raise SystemExit(main())
