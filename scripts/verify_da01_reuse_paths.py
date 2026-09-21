#!/usr/bin/env python
"""DA-01 요구사항정의서가 인용한 **재사용 근거 경로가 실재하는지** 판정한다.

왜 이 스크립트가 필요한가
---------------------------
DA-01 의 가치는 "무엇이 이미 있는가"를 말하는 데 있다. 그 주장이 틀리면
문서는 위험해진다 — 없는 것을 있다고 적으면 일정 산정이 통째로 어긋난다.
그런데 경로는 리팩터링·이동으로 조용히 죽는다. 사람이 눈으로 세지 않는다.

무엇을 검사하나
---------------
문서 본문의 인라인 코드(`...`) 중 저장소 경로처럼 보이는 것만 골라
실재 여부를 본다. 경로처럼 보이지 않는 것(식별자·필드명·설정값)은 건너뛴다.

    python scripts/verify_da01_reuse_paths.py            # 판정 (불일치 시 exit 1)
    python scripts/verify_da01_reuse_paths.py --list     # 뽑아낸 경로 전부 출력
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "design" / "DA-01_요구사항정의서_v1.0.md"

try:  # cp949 콘솔에서 한글 출력이 죽지 않게
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 저장소 최상위 디렉터리 — 이 중 하나로 시작해야 "경로 주장"으로 본다.
ROOTS = ("backend/", "frontend/", "docs/", "scripts/", "nginx/")

#: 인라인 코드 안에서 경로를 뽑는다. `path:123` 의 줄번호는 떼어낸다.
INLINE = re.compile(r"`([^`\n]+)`")
LINE_SUFFIX = re.compile(r":\d+$")


def extract(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for raw in INLINE.findall(text):
        cand = LINE_SUFFIX.sub("", raw.strip().rstrip("/"))
        if not cand.startswith(ROOTS):
            continue
        if " " in cand:  # 문장이 통째로 코드로 감싸인 경우
            continue
        seen.setdefault(cand, None)
    return list(seen)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="뽑아낸 경로를 전부 출력")
    args = ap.parse_args()

    if not DOC.exists():
        print(f"[DA-01] 문서가 없다: {DOC.relative_to(ROOT)}")
        return 1

    paths = extract(DOC.read_text(encoding="utf-8"))
    if not paths:
        print("[DA-01] 경로 주장을 하나도 찾지 못했다 — 추출 규칙을 의심하라")
        return 1

    missing = [p for p in paths if not (ROOT / p).exists()]

    if args.list:
        for p in paths:
            print(f"  {'OK ' if (ROOT / p).exists() else 'MISS'}  {p}")

    print(f"[DA-01] 인용 경로 {len(paths)}건 · 실재 {len(paths) - len(missing)}건")
    if missing:
        print("[DA-01] 불일치 — 문서가 없는 것을 있다고 말한다")
        for p in missing:
            print(f"  · {p}")
        return 1
    print("[DA-01] 대조 통과")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        measured=("DA-01 이 「이미 있다」고 적은 **경로 주장**이 실재하는가 — 최상위 갈래 "
               "**분모 %d**(%s)로 시작하는 주장 전수를 문서에서 뽑아 하나씩 연다. "
               "없는 것을 있다고 적으면 일정 산정이 통째로 어긋난다"
               % (len(ROOTS), " · ".join(ROOTS))),
    )
    sys.exit(main())
