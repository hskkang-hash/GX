#!/usr/bin/env python
"""DA-04 의 커널 매핑표와 tickets.yaml 의 `kernel:` 필드가 일치하는지 판정한다.

왜 필요한가
-----------
문서와 정본이 갈리는 것은 시간 문제다. DA-04 §4 의 표는 사람이 읽고,
`tickets.yaml` 의 `kernel:` 은 기계가 읽는다. **둘이 어긋나면 어느 쪽이 진실인지
아무도 모르게 된다** — 그 상태가 D-227(manifest 유실)이 만든 상황이었다.

그래서 표를 손으로 대조하지 않는다. 이 스크립트가 대조한다.

    python scripts/verify_kernel_map.py           # 판정 (불일치 시 exit 1)
    python scripts/verify_kernel_map.py --list    # 커널별 티켓 목록 출력
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TICKETS = ROOT / "docs" / "agent" / "tickets.yaml"
DOC = ROOT / "docs" / "design" / "DA-04_공유커널_API스펙_v1.0.md"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: DA-04 가 정의한 커널. **이 목록에 없는 커널 코드는 실패다** (아래 §미지 커널 검사).
#:
#: 왜 화이트리스트인가 (2026-08-27 · D-258)
#:     지시서 v2.2 가 K7(컨텍스트 커널)을 예고했고 DA-05 가 그 스펙을 쓴다. 그때
#:     tickets.yaml 에 `kernel: [K7]` 만 먼저 달리면, 이 스크립트는 K1~K6 만 돌므로
#:     **K7 을 아예 보지 않는다** — 문서에 없는 매핑이 조용히 정본에 남는다.
#:     그것이 이 스크립트가 막으려던 바로 그 상태다(D-227 manifest 유실과 같은 모양).
#:     그래서 모르는 커널을 만나면 **통과시키지 않고 실패**한다.
#:     K7 을 추가할 때는 여기와 DA-04 §4 표를 **같은 커밋에서** 함께 고친다.
KERNELS = ["K1", "K2", "K3", "K4", "K5", "K6"]

#: DA-04 §4 의 표 행 — `| K1 | W2-1 · W2-2 · W2-3 |`
ROW = re.compile(r"^\|\s*(K[1-6])\s*\|\s*(.+?)\s*\|\s*$", re.MULTILINE)
TICKET_ID = re.compile(r"\b([A-Z]+\d*-\d+[a-z]?)\b")


def from_registry() -> dict[str, set[str]]:
    doc = yaml.safe_load(TICKETS.read_text(encoding="utf-8"))
    out: dict[str, set[str]] = defaultdict(set)
    for t in doc.get("tickets") or []:
        for k in t.get("kernel") or []:
            out[k].add(t["id"])
    # DA-04 자신은 커널 정의 티켓이라 매핑표의 대상이 아니다
    for k in list(out):
        out[k].discard("DA-04")
    return out


def from_doc() -> dict[str, set[str]]:
    text = DOC.read_text(encoding="utf-8")
    # §4 이후만 본다 — 앞쪽 본문의 표에도 K 가 나온다
    marker = "## 4. `kernel:` 필드"
    idx = text.find(marker)
    if idx < 0:
        raise SystemExit("[KERNEL] DA-04 에서 §4 매핑표를 찾지 못했다")
    out: dict[str, set[str]] = defaultdict(set)
    for k, cell in ROW.findall(text[idx:]):
        out[k] = set(TICKET_ID.findall(cell))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if not DOC.exists():
        print(f"[KERNEL] 문서가 없다: {DOC.relative_to(ROOT)}")
        return 1

    reg, doc = from_registry(), from_doc()
    problems: list[str] = []

    # 미지 커널 검사 — 화이트리스트 밖의 코드는 문서와 대조된 적이 없다는 뜻이다.
    unknown = sorted(set(reg) - set(KERNELS))
    if unknown:
        problems.append(
            f"정본에 미지의 커널 코드가 있다 {unknown} — DA-04 매핑표와 이 스크립트의 "
            f"KERNELS 에 함께 등재하라 (커널을 늘리면서 검증을 늘리지 않으면 그 커널은 무검증이다)"
        )

    for k in KERNELS:
        r, d = reg.get(k, set()), doc.get(k, set())
        if args.list:
            print(f"  {k}  정본={sorted(r) or '(없음)'}  문서={sorted(d) or '(없음)'}")
        if r != d:
            if d - r:
                problems.append(f"{k}: 문서에만 있는 티켓 {sorted(d - r)}")
            if r - d:
                problems.append(f"{k}: 정본에만 있는 티켓 {sorted(r - d)}")

    total = sum(len(v) for v in reg.values())
    print(f"[KERNEL] 정본 kernel 필드 {total}건 · 커널 {len([k for k in KERNELS if reg.get(k)])}/6 에 티켓 배정")
    if not reg.get("K2"):
        print("[KERNEL] 알림: K2 는 대응 티켓이 없다 — DA-01 OPEN-07 로 등재된 GAP 이다 (실패 아님)")

    if problems:
        print("[KERNEL] 불일치 — 문서와 정본이 갈렸다")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[KERNEL] 대조 통과")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(__file__)
    sys.exit(main())
