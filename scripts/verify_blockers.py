#!/usr/bin/env python
"""잠금 대장 판정 — **막힌 것의 종류를 정확히 말하게 한다** (D-307).

    unlock_type  : 'DEV' | 'CONTRACT' | 'ADMIN'
    unlock_owner : 누가 푸는가

왜 유형이 필요한가
------------------
지금까지 잠김은 전부 "막혔다" 한 단어였다. 셋은 성격이 전혀 다르다 —
**DEV 는 일정 문제, CONTRACT 는 책임 문제, ADMIN 은 하루면 풀리는데 안 한 것**이다.
섞어 두면 하루짜리가 계약 리스크 뒤에 숨는다. 대표께 올라가는 표에서 그 셋이 갈려 있어야
"오늘 무엇을 하면 몇 개가 풀리는가"를 즉시 읽는다.

    python scripts/verify_blockers.py            # 판정
    python scripts/verify_blockers.py --summary  # 유형별 건수만 (릴리스 후보 표지용)
    python scripts/verify_blockers.py --self-test

무엇을 보는가
-------------
  ① 두 칸이 **있는가** — 비면 exit 1
  ② `unlock_type` 이 열거 안인가 — 오타는 새 유형이 아니다
  ③ 사유(`why`)와 해소 절차(`unlock_step`)가 있는가 — 없으면 그 등재는 "막혔다" 한 단어다
  ④ `state_in_code` 가 가리킨 파일이 **실재하는가** — 없는 자리를 적으면 그것도 문서다

★ 대장이 0건이면 통과가 아니라 **판정 불가**다 (D-301 「검사 못함 ≠ 0건 검사」).
  잠김이 정말 없어서 0건인 것과 파일을 못 읽어 0건인 것을 구별할 수 없기 때문이다.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "agent" / "evidence" / "DA-05" / "blockers.yaml"

VALID_TYPES = ("DEV", "CONTRACT", "ADMIN")
REQUIRED = ("title", "unlock_type", "unlock_owner", "why", "unlock_step", "state_in_code")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def parse(text: str) -> list[dict]:
    """대장을 읽는다. **PyYAML 을 요구하지 않는다** — 컨테이너에 없다(실측).

    파서를 요구하면 이 게이트는 환경에 따라 사라지고, 사라진 게이트는 사라진 것이
    보이지 않는다. 보는 것이 단순하므로(항목마다 몇 개의 스칼라) 직접 읽는다.
    """
    rows: list[dict] = []
    current: dict | None = None
    key: str | None = None
    for raw in text.split("\n"):
        if raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^  - id:\s*(\S+)", raw)
        if m:
            current = {"id": m.group(1)}
            rows.append(current)
            key = None
            continue
        if current is None:
            continue
        m = re.match(r"^    ([a-z_]+):\s*(.*)$", raw)
        if m:
            key, value = m.group(1), m.group(2).strip()
            current[key] = "" if value in ("|", ">", ">-", "|-") else value.strip('"')
            continue
        if key and raw.startswith("      "):
            current[key] = (current.get(key, "") + " " + raw.strip()).strip()
    return rows


def check(rows: list[dict]) -> list[str]:
    problems: list[str] = []
    for row in rows:
        rid = row.get("id", "?")
        for field in REQUIRED:
            if not (row.get(field) or "").strip():
                problems.append(
                    f"{rid}: `{field}` 가 비었다 — "
                    + ("막힌 것의 종류를 말하지 않으면 하루짜리가 계약 리스크 뒤에 숨는다"
                       if field.startswith("unlock") else "등재는 면제가 아니라 선언이다"))
        t = (row.get("unlock_type") or "").strip()
        if t and t not in VALID_TYPES:
            problems.append(
                f"{rid}: unlock_type='{t}' 은 열거 밖이다 {VALID_TYPES} — "
                f"오타는 새 유형이 아니다")
        where = (row.get("state_in_code") or "").split(" —")[0].strip()
        if where and not (ROOT / where).exists():
            problems.append(
                f"{rid}: state_in_code 가 가리킨 '{where}' 가 없다 — "
                f"없는 자리를 적으면 그것도 문서다 (D-286)")
    return problems


def summary(rows: list[dict]) -> Counter:
    return Counter((r.get("unlock_type") or "?").strip() for r in rows)


def self_test() -> int:
    good = [{"id": "A", "title": "t", "unlock_type": "DEV", "unlock_owner": "Code",
             "why": "w", "unlock_step": "s", "state_in_code": "scripts"}]
    cases = (
        ("정상 항목은 안 잡는다", good, False),
        ("★ unlock_type 이 비면 잡는다",
         [{**good[0], "unlock_type": ""}], True),
        ("★ unlock_owner 가 비면 잡는다",
         [{**good[0], "unlock_owner": ""}], True),
        ("열거 밖 유형을 잡는다", [{**good[0], "unlock_type": "TODO"}], True),
        ("없는 파일을 가리키면 잡는다",
         [{**good[0], "state_in_code": "없는/자리.py"}], True),
        ("해소 절차가 없으면 잡는다", [{**good[0], "unlock_step": ""}], True),
    )
    bad = 0
    for label, rows, should_fail in cases:
        ok = bool(check(rows)) == should_fail
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1
    # 파서도 시험한다 — 판정만 맞고 못 읽으면 대장은 늘 0건이다
    parsed = parse(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else []
    ok_parse = len(parsed) > 0 and all("unlock_type" in r for r in parsed)
    print(f"  {'OK  ' if ok_parse else 'FAIL'} 파서가 대장을 읽는다 ({len(parsed)}건)")
    if not ok_parse:
        bad += 1
    if bad:
        print(f"[BLOCKER] 자기시험 {bad}건 실패 — 이 판정기는 눈이 멀었다")
        return 1
    print(f"[BLOCKER] 자기시험 {len(cases) + 1}건 통과 (양성 5 · 음성 2)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not LEDGER.is_file():
        print(f"[BLOCKER] 잠금 대장이 없다: {LEDGER} — 판정할 수 없으므로 멈춘다")
        return 1
    if self_test() != 0:
        return 1

    rows = parse(LEDGER.read_text(encoding="utf-8"))
    counts = summary(rows)

    print(f"[BLOCKER] 검사 {len(rows)}건 (대상=DA-05 잠금 대장 전수 · "
          f"술어=unlock_type·unlock_owner·사유·해소절차·코드 자리)")
    # ★ 0건은 통과가 아니다 (D-301)
    if not rows:
        print("[BLOCKER] 대장이 0건이다 — 정말 잠김이 없는 것인지 못 읽은 것인지 "
              "구별할 수 없다. 판정 불가이지 통과가 아니다")
        return 1

    print("[BLOCKER] 유형별: " + " · ".join(
        f"{t} {counts.get(t, 0)}" for t in VALID_TYPES)
        + (f" · 미분류 {counts.get('?', 0)}" if counts.get("?") else ""))
    if args.summary:
        for row in rows:
            print(f"  {row.get('unlock_type', '?'):9} {row['id']:22} "
                  f"→ {row.get('unlock_owner', '?')}")

    problems = check(rows)
    if problems:
        print("[BLOCKER] 위반 — 막힌 것의 종류가 말해지지 않았다")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[BLOCKER] 통과 — 잠김마다 유형·주인·사유·해소 절차가 있다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
