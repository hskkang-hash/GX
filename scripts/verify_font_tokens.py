#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-454 [N4] 게이트 — 화면 인라인 글씨 12 px 검출 (전역 토큰: 기본 14 · 보조 13).

`frontend/src` 의 .ts/.tsx 에서 `fontSize: 12` · `fontSize: '12px'` · `fontSize={12}` ·
`font-size: 12px` 를 센다(주석 줄 제외). 토큰은 `src/configs/fontTokens.ts`.

    python scripts/verify_font_tokens.py
    python scripts/verify_font_tokens.py --self-test

종료 코드: 0 초록 · 1 빨강 · 2 못 쟀다
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "src"
PAT = re.compile(
    r"fontSize:\s*12(?![\d.])"
    r"|fontSize:\s*(['\"])12px\1"
    r"|fontSize=\{12\}"
    r"|(?<![/\w-])font-size:\s*12px"
)
SKIP = ("configs/fontTokens.ts",)


def count_text(text: str) -> list:
    out = []
    for i, ln in enumerate(text.split("\n"), 1):
        if ln.lstrip().startswith(("//", "*", "/*")):
            continue
        if PAT.search(ln):
            out.append(i)
    return out


def main(argv) -> int:
    if "--self-test" in argv:
        pos = count_text("<div style={{ fontSize: 12 }} />\nx={{fontSize: '12px'}}\n<Text fontSize={12}/>\ncss `font-size: 12px;`")
        neg = count_text("// fontSize: 12\nstyle={{ fontSize: FONT_SM }}\nfontSize: 120\nfontSize: 14\nfontSize: '112px'")
        #: 출생 표본 — 턴 AQ P-295 「화면별 인라인 12 px」의 실제 줄(옮기기 전 원문 그대로).
        birth = count_text("              <div style={{ fontSize: '12px', color: '#8c8c8c' }}>")
        ok = len(pos) == 4 and len(neg) == 0 and len(birth) == 1
        print("[FONT_TOKENS] 자기시험 양성표본 %d/4 · 음성표본 오탐 %d/0 : %s"
              % (len(pos), len(neg), "통과" if ok else "실패"))
        return 0 if ok else 1
    if not SRC.is_dir():
        print("[FONT_TOKENS] 회색 — 못 쟀다: %s 없음" % SRC)
        return 2
    files, hits = 0, {}
    for p in sorted(SRC.rglob("*")):
        if p.suffix not in (".ts", ".tsx") or p.as_posix().endswith(SKIP):
            continue
        files += 1
        h = count_text(p.read_text(encoding="utf-8", errors="ignore"))
        if h:
            hits[p.relative_to(ROOT).as_posix()] = h
    total = sum(len(v) for v in hits.values())
    print("[FONT_TOKENS] [입력] 검사한 파일 %d개 · 인라인 12 px %d건 (%d파일)" % (files, total, len(hits)))
    if total:
        for f, h in list(hits.items())[:40]:
            print("[FONT_TOKENS]   %s : %s" % (f, h))
        print("[FONT_TOKENS] 빨강 — FONT_SM/FONT_BASE 토큰으로 옮겨라")
        return 1
    print("[FONT_TOKENS] 초록 — 인라인 12 px 0건")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
