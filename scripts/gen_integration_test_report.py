#!/usr/bin/env python
"""통합시험 결과서 초안을 **생성한다** — 계약 제7조 3단계 인도물 ① (D-303).

한 문장
-------
    **본문은 생성물이지 작성물이 아니다.** 손으로 쓰면 그 순간 실측과 갈리고,
    갈린 뒤에는 어느 쪽이 사실인지 아무도 모른다 (D-227 이 만든 상태).

무엇에서 만드나
---------------
`docs/agent/evidence/e2e/<시나리오>/steps.md` — E2E 가 돌 때마다 스스로 남기는 단계표다
(D-291 규약 ⑥). 시나리오·단계·OK/FAIL/잠김이 이미 표로 있으므로, 이 스크립트가 할 일은
**표지와 요약 한 장을 얹는 것** 뿐이다.

    python scripts/gen_integration_test_report.py          # 생성
    python scripts/gen_integration_test_report.py --check  # 최신인지만 본다 (게이트용)

★ 증거가 없으면 **빈 결과서를 만들지 않는다** (D-301 「검사 못함 ≠ 0건 검사」)
------------------------------------------------------------------------------
`steps.md` 가 하나도 없으면 exit 1 이다. "시나리오 0건 · 전건 통과" 라고 적힌 결과서는
아무것도 안 잰 것이고, 그런 문서는 없는 것보다 나쁘다 — 인수측이 그것을 근거로 읽는다.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "agent" / "evidence" / "e2e"
OUT = EVIDENCE / "통합시험결과서_초안.md"
CONTRACT = ROOT / "backend" / "tests" / "e2e" / "e2e_contract.py"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def scenarios() -> list[tuple[str, str]]:
    """(코드, 단계표 본문). 파일이 있는 것만 — **없는 것을 지어내지 않는다.**"""
    out: list[tuple[str, str]] = []
    for d in sorted(EVIDENCE.iterdir()):
        steps = d / "steps.md" if d.is_dir() else None
        if steps and steps.is_file():
            out.append((d.name, steps.read_text(encoding="utf-8")))
    return out


def counts(body: str) -> tuple[int, int, int, int]:
    """(도달, 해금, 계획, 잠김). 단계표 첫 줄의 실측값을 그대로 읽는다."""
    m = re.search(r"단계 (\d+)/(\d+) 도달 \(계획 (\d+) · 잠김 (\d+)\)", body)
    return tuple(int(g) for g in m.groups()) if m else (0, 0, 0, 0)


def locked_reasons() -> dict[str, str]:
    """`LOCKED_CAPABILITIES` 의 사유. 결과서의 '왜 못 쟀나' 가 여기서 온다.

    import 하지 않는다 — Django 없이 돌아야 한다. 블록을 문자열로 읽는다.
    """
    src = CONTRACT.read_text(encoding="utf-8")
    block = re.search(r"LOCKED_CAPABILITIES[^=]*=\s*\{(.*?)\n\}", src, re.S)
    if not block:
        return {}
    out: dict[str, str] = {}
    body = block.group(1)
    # 항목 하나 = `"NAME":` 부터 다음 `"NAME":` (또는 끝) 까지. 그 안의 문자열을 잇는다.
    # 줄 단위 정규식으로 자르면 여러 줄로 이어 붙인 사유의 **뒷줄이 잘린다** — 실제로 잘렸다.
    starts = [(m.group(1), m.start()) for m in re.finditer(r'^    "([A-Z_]+)":', body, re.M)]
    for i, (name, pos) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(body)
        chunk = body[pos:end]
        chunk = chunk[chunk.index(":") + 1:]
        # ★ 주석 줄을 먼저 버린다. 등재부에는 **지운 이름의 내력**이 주석으로 남아 있고
        #   (예: FLOOD_EVENT_TYPE · ZONE 이 왜 지워졌는가), 그 주석 안의 따옴표까지
        #   사유로 이어 붙으면 결과서가 앞뒤가 안 맞는 문장을 낸다 — 실제로 그랬다.
        chunk = "\n".join(ln for ln in chunk.split("\n")
                          if not ln.lstrip().startswith("#"))
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"', chunk)
        out[name] = "".join(parts).strip()
    return out


def render() -> str:
    rows = scenarios()
    locked = locked_reasons()
    total_reached = sum(counts(b)[0] for _, b in rows)
    total_planned = sum(counts(b)[2] for _, b in rows)
    total_locked = sum(counts(b)[3] for _, b in rows)

    lines = [
        "# GuardianX 통합시험 결과서 (초안)",
        "",
        f"**생성** {date.today().isoformat()} · **근거** 계약 제7조 3단계 인도물 ① · "
        f"**범위** 릴리스 후보(SDN 제외판)",
        "",
        "> ★ **이 문서의 본문은 생성물이다.** `docs/agent/evidence/e2e/*/steps.md` 를 그대로",
        "> 옮긴 것이고, 그 파일들은 E2E 가 돌 때마다 스스로 남긴다(D-291 규약 ⑥).",
        "> 손으로 고치지 말 것 — 고치면 실측과 갈리고, 갈린 뒤에는 어느 쪽이 사실인지 모른다.",
        "",
        "---",
        "",
        "## 1. 요약",
        "",
        "| 시나리오 | 도달 | 해금 | 계획 | 잠김 |",
        "|---|---:|---:|---:|---:|",
    ]
    for code, body in rows:
        reached, unlocked, planned, lock = counts(body)
        lines.append(f"| {code} | {reached} | {unlocked} | {planned} | {lock} |")
    lines += [
        f"| **합계** | **{total_reached}** | | **{total_planned}** | **{total_locked}** |",
        "",
        "★ **잠김은 실패가 아니고 통과도 아니다 — 잴 수 없는 것이다** (D-302).",
        "  그래서 '완주' 라고 적지 않는다. 정확한 표현은",
        "  *\"릴리스 후보(SDN 제외판)의 범위 안에서는 끊긴 단계가 없다\"* 이다.",
        "",
        "---",
        "",
        "## 2. 왜 못 쟀나 — 잠긴 능력의 사유",
        "",
    ]
    if locked:
        for name, why in sorted(locked.items()):
            lines += [f"### {name}", "", why, ""]
    else:
        lines += ["잠긴 능력이 없다.", ""]

    lines += ["---", "", "## 3. 시나리오별 단계표 (실측 원문)", ""]
    for code, body in rows:
        lines += [body.strip(), ""]

    lines += [
        "---",
        "",
        "## 4. 이 결과서가 말하지 않는 것",
        "",
        "· **DoD 재현은 사람이 한다.** 이 표는 자동 시험의 결과이지 인수 판정이 아니다.",
        "· 잠긴 단계는 **한 번도 실행되지 않았다.** 통과로 세지 말 것.",
        "· 설치 절차·저하 운전은 `docs/agent/runbook/설치운영매뉴얼_v0.1.md` 에 있다.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not EVIDENCE.is_dir():
        print(f"[REPORT] 증거 폴더가 없다: {EVIDENCE} — 판정할 수 없으므로 멈춘다")
        return 1

    rows = scenarios()
    # ★ 증거 0건은 "전건 통과" 가 아니라 **아무것도 안 잰 것**이다 (D-301).
    if not rows:
        print("[REPORT] steps.md 가 한 건도 없다 — E2E 를 한 번도 돌리지 않았거나 "
              "증거가 지워졌다. 빈 결과서를 만들지 않는다")
        return 1

    body = render()
    if args.check:
        if not OUT.is_file():
            print(f"[REPORT] {OUT.relative_to(ROOT)} 가 없다 — 생성해야 한다")
            return 1
        if OUT.read_text(encoding="utf-8") != body:
            print(f"[REPORT] {OUT.relative_to(ROOT)} 가 증거보다 낡았다 — "
                  f"다시 생성한다: python scripts/gen_integration_test_report.py")
            return 1
        print(f"[REPORT] 최신 — 시나리오 {len(rows)}건")
        return 0

    OUT.write_text(body, encoding="utf-8")
    print(f"[REPORT] {OUT.relative_to(ROOT)} 생성 — 시나리오 {len(rows)}건 · "
          f"단계 {sum(counts(b)[2] for _, b in rows)}칸 "
          f"(잠김 {sum(counts(b)[3] for _, b in rows)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
