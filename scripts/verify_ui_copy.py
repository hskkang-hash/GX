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

#: 사용자 본문이 사는 곳. 여기 밖(설정·라우터·서비스)의 문자열은 화면에 뜨지 않는다.
#: ⚠ 좁게 잡는다 — 넓게 잡으면 첫 수가 수백이 되고, 수백은 아무도 안 고친다.
SCOPE = ("frontend/src/features/dsm/", "frontend/src/features/mobile/")


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

#: JSX 본문 — `>여기 한국어<`. 중괄호가 든 조각은 식이므로 제외한다.
JSX_TEXT = re.compile(r">([^<>{}]*[가-힣][^<>{}]*)<")


def user_texts(src: str) -> list[tuple[int, str]]:
    """주석을 걷어 낸 소스에서 **사용자가 읽는 글자**만 뽑는다.

    ① 따옴표 안의 문자열 리터럴(`'` `"` `` ` ``) 중 한글이 든 것
    ② JSX 본문 중 한글이 든 것

    줄 번호는 **여는 따옴표의 줄**이다 — 여러 줄 템플릿이면 시작 줄을 가리킨다.
    """
    out: list[tuple[int, str]] = []
    i, n = 0, len(src)
    line = 1
    while i < n:
        ch = src[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch in "'\"`":
            quote, start, start_line = ch, i + 1, line
            i += 1
            while i < n:
                if src[i] == "\\":
                    i += 2
                    continue
                if src[i] == "\n":
                    line += 1
                if src[i] == quote:
                    break
                i += 1
            body = src[start:i]
            #: ★ 한글만 골라내지 않는다 [실측 2026-09-26]. 그렇게 했더니 출생 표본
            #:   「data_source = live」 칩을 놓쳤다 — 대장 언어는 **한국어가 아닌 채로도**
            #:   화면에 뜬다. 대신 **문자열의 몸통만** 본다: 템플릿 리터럴의 백틱은
            #:   구분자이지 본문이 아니므로 `/m/events/${id}` 같은 코드는 지나간다.
            out.append((start_line, body))
            i += 1
            continue
        i += 1
    for m in JSX_TEXT.finditer(src):
        out.append((src.count("\n", 0, m.start()) + 1, m.group(1)))
    return out


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


def scan() -> tuple[int, list[tuple[str, int, str, str]]]:
    """`(본 파일 수, [(상대경로, 줄, 패턴, 발췌)])`."""
    findings: list[tuple[str, int, str, str]] = []
    files = [p for p in frontend_files() if in_scope(p)]
    for path in files:
        try:
            src = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        for lineno, text in user_texts(strip_comments(src)):
            for name in scan_line(text):
                findings.append((rel, lineno, name, norm(text)))
    return len(files), findings


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
    # 음성 ① — 주석은 소스의 자리다
    if scan_line(strip_comments("// UX-17 · D-421 · `kernels.k1_event`\n").strip()):
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
    if fails:
        print(f"[COPY] 자기시험 {fails}건 실패")
        return 1
    print(f"[COPY] 자기시험 통과 — 양성 {len(BIRTH_SAMPLES)} · 음성 6")
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

    seen, findings = scan()
    if seen == 0:
        print(f"[COPY] **판정 불가** — {' · '.join(SCOPE)} 에서 파일을 한 개도 못 읽었다 "
              "(0건 검사와 검사 못 함은 다르다 · D-301)")
        return 2
    print(f"[COPY] [입력] {seen}개 화면 파일 (주석 걷어낸 뒤) · 패턴 {len(COMPILED)}종")

    if args.freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# UX-20 제품 언어 — **오늘의 빚**. 줄이는 것만 허용한다 (래칫 · D-311).",
                 "# 열쇠: 파일<TAB>패턴<TAB>발췌(공백 정규화). 줄 번호는 쓰지 않는다.",
                 f"# 잠근 날: 2026-09-26 · {len(findings)}건",
                 ""]
        lines += sorted({key(f) for f in findings})
        BASELINE.write_text("\n".join(lines) + "\n", encoding="utf-8")
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

    if not baseline:
        print("[COPY] 기준선이 없다 — `--freeze` 로 오늘의 빚을 먼저 잠근다")
        return 2
    print("[COPY] 통과 — 새로 생긴 대장 언어 0건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
