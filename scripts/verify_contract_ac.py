#!/usr/bin/env python
"""계약 AC 전수 대장 판정 — **재지 않은 것을 '구현'으로 적지 못하게 한다** (D-309).

    · 대장 행 수 ≠ 14 이면 exit 1
    · '구현' 칸에 증명 시험이 비면 exit 1
    · 적힌 시험 **파일이 없거나 그 메서드 이름이 없으면** exit 1 (없는 시험은 문서다)
    · 검사 건수와 **미측정 건수**를 출력한다 (D-301)

왜 이 표인가 — **우리가 무엇을 모르는지 세는 표**
-------------------------------------------------
지금까지 F-09~F-12 만 이야기했다. 계약 기능은 14건이다. 나머지의 상태를 표로 갖고
있지 않으면, 검수에서 처음 세게 된다.

그리고 이 표의 값은 '구현' 칸이 아니라 **'미측정' 칸**에 있다. 구현했는지 안 했는지와
**재고 있는지**는 다른 질문이고, 후자를 세는 표가 이것 하나다.

    python scripts/verify_contract_ac.py            # 판정
    python scripts/verify_contract_ac.py --table    # 사람이 읽는 표 (대표 보고용)
    python scripts/verify_contract_ac.py --self-test

★ D-292 반성 — 문서를 읽어 표를 만들면 그 표는 문서의 사본이다. 그래서 이 스크립트는
  대장이 가리킨 **시험 파일과 메서드 이름의 실재**를 매번 다시 본다. 시험이 지워지면
  그 칸은 다음 실행에서 빨간불이 된다.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "agent" / "evidence" / "D-309" / "contract_ac_ledger.yaml"
BLOCKERS = ROOT / "docs" / "agent" / "evidence" / "DA-05" / "blockers.yaml"

EXPECTED_IDS = tuple(f"F-{n:02d}" for n in range(1, 15))
STATES = ("구현", "부분", "잠김", "미측정")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def parse(text: str) -> list[dict]:
    """대장을 읽는다. **PyYAML 을 요구하지 않는다** — 컨테이너에 없다(실측).

    파서를 요구하면 이 게이트는 환경에 따라 사라진다. 보는 것이 단순하므로 직접 읽는다.
    """
    rows: list[dict] = []
    cur: dict | None = None
    key: str | None = None
    for raw in text.split("\n"):
        if raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^  - id:\s*(\S+)", raw)
        if m:
            cur = {"id": m.group(1), "proof": []}
            rows.append(cur)
            key = None
            continue
        if cur is None:
            continue
        m = re.match(r'^      - "(.+)"\s*$', raw)
        if m and key == "proof":
            cur["proof"].append(m.group(1))
            continue
        m = re.match(r"^    ([a-z_]+):\s*(.*)$", raw)
        if m:
            key, value = m.group(1), m.group(2).strip()
            if key == "proof":
                cur["proof"] = []
                continue
            cur[key] = "" if value in ("|", ">", ">-", "|-", "[]") else value.strip('"')
            continue
        if key and key != "proof" and raw.startswith("      "):
            cur[key] = (cur.get(key, "") + " " + raw.strip()).strip()
    return rows


def blocker_ids() -> set[str]:
    if not BLOCKERS.is_file():
        return set()
    return set(re.findall(r"^  - id:\s*(\S+)", BLOCKERS.read_text(encoding="utf-8"), re.M))


def check(rows: list[dict], known_blockers: set[str],
          proof_exists=None) -> list[str]:
    """proof_exists(path, method) -> bool 을 주입받는다 — 자기시험이 파일 없이 돈다."""
    if proof_exists is None:
        def proof_exists(path: str, method: str) -> bool:
            f = ROOT / path
            return f.is_file() and f"def {method}(" in f.read_text(encoding="utf-8")

    problems: list[str] = []
    ids = [r["id"] for r in rows]
    if len(rows) != len(EXPECTED_IDS):
        problems.append(
            f"대장이 {len(rows)}행이다 — 계약 기능은 {len(EXPECTED_IDS)}건이다. "
            f"빠진 줄은 보이지 않는다(D-274)")
    missing = [f for f in EXPECTED_IDS if f not in ids]
    if missing:
        problems.append(f"대장에 없는 기능: {missing}")

    for row in rows:
        rid = row.get("id", "?")
        state = (row.get("state") or "").strip()
        if state not in STATES:
            problems.append(f"{rid}: state='{state}' 는 열거 밖이다 {STATES}")
        if not (row.get("ac") or "").strip():
            problems.append(f"{rid}: 계약 AC 원문이 비었다")

        proofs = row.get("proof") or []
        # ★ 핵심 규칙 — 증명 없는 '구현' 은 '구현' 이 아니라 '미측정' 이다.
        if state == "구현" and not proofs:
            problems.append(
                f"{rid}: '구현' 인데 증명 시험이 없다 — 그런 칸은 '부분' 이 아니라 "
                f"**'미측정'** 이다 (D-309)")
        if state in ("부분", "잠김", "미측정") and not (row.get("not_measured") or "").strip():
            problems.append(
                f"{rid}: state='{state}' 인데 **무엇을 못 재는지** 적혀 있지 않다. "
                f"못 재는 것을 안 적으면 '부분' 은 '거의 다 됨' 으로 읽힌다")
        for proof in proofs:
            if "::" not in proof:
                problems.append(f"{rid}: proof '{proof}' 형식이 아니다 (파일::메서드)")
                continue
            path, method = proof.split("::", 1)
            if not proof_exists(path, method):
                problems.append(
                    f"{rid}: 증명 시험이 실재하지 않는다 — {proof}. "
                    f"없는 시험을 적으면 그것도 문서다 (D-286)")
        unlock = (row.get("unlock_id") or "").strip()
        if state == "잠김" and not unlock:
            problems.append(f"{rid}: '잠김' 인데 unlock_id 가 없다 — 누가 푸는지 모른다 (D-307)")
        if unlock and known_blockers and unlock not in known_blockers:
            problems.append(
                f"{rid}: unlock_id='{unlock}' 가 잠금 대장에 없다 — 유령 참조다")
    return problems


def self_test() -> int:
    ok_row = {"id": "F-01", "ac": "a", "state": "구현",
              "proof": ["tests/x.py::test_a"], "unlock_id": ""}
    full = [dict(ok_row, id=f) for f in EXPECTED_IDS]

    def yes(path, method):
        return True

    def no(path, method):
        return False

    cases = (
        ("14행 · 증명 있는 '구현' 은 안 잡는다", full, yes, False),
        ("★ 행 수가 14 가 아니면 잡는다", full[:5], yes, True),
        ("★ 증명 없는 '구현' 을 잡는다",
         [dict(r, proof=[]) if r["id"] == "F-01" else r for r in full], yes, True),
        ("★ 없는 시험을 가리키면 잡는다", full, no, True),
        ("'부분' 인데 못 재는 것을 안 적으면 잡는다",
         [dict(r, state="부분") if r["id"] == "F-02" else r for r in full], yes, True),
        ("'잠김' 인데 unlock_id 가 없으면 잡는다",
         [dict(r, state="잠김", not_measured="x") if r["id"] == "F-06" else r
          for r in full], yes, True),
    )
    bad = 0
    for label, rows, pe, should_fail in cases:
        ok = bool(check(rows, set(), pe)) == should_fail
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1
    parsed = parse(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else []
    ok_parse = len(parsed) == len(EXPECTED_IDS) and all(r.get("proof") is not None
                                                        for r in parsed)
    print(f"  {'OK  ' if ok_parse else 'FAIL'} 파서가 대장을 읽는다 ({len(parsed)}행)")
    if not ok_parse:
        bad += 1
    if bad:
        print(f"[AC] 자기시험 {bad}건 실패 — 이 판정기는 눈이 멀었다")
        return 1
    print(f"[AC] 자기시험 {len(cases) + 1}건 통과 (양성 5 · 음성 2)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not LEDGER.is_file():
        print(f"[AC] 대장이 없다: {LEDGER} — 판정할 수 없으므로 멈춘다")
        return 1
    if self_test() != 0:
        return 1

    rows = parse(LEDGER.read_text(encoding="utf-8"))
    counts = Counter((r.get("state") or "?").strip() for r in rows)
    proofs = sum(len(r.get("proof") or []) for r in rows)

    print(f"[AC] 검사 {len(rows)}행 (모수=계약 기능 {len(EXPECTED_IDS)}건 · "
          f"술어=state 열거 + 증명 시험의 파일·메서드 실재) · 증명 시험 {proofs}건")
    print("[AC] 상태별: " + " · ".join(f"{s} {counts.get(s, 0)}" for s in STATES))
    # ★ 이 표의 진짜 값 — 우리가 무엇을 모르는가.
    print(f"[AC] ★ **미측정 {counts.get('미측정', 0)}건** — 구현 여부와 무관하게 "
          f"재는 시험이 없는 칸이다")

    if args.table:
        print()
        print(f"  {'기능':6} {'상태':6} {'커널':8} {'증명':4}  계약 AC")
        for row in rows:
            print(f"  {row['id']:6} {row.get('state', '?'):6} "
                  f"{row.get('kernel', '?'):8} {len(row.get('proof') or []):4}  "
                  f"{(row.get('ac') or '')[:56]}")

    problems = check(rows, blocker_ids())
    if problems:
        print("[AC] 위반 — 재지 않은 것이 '구현' 으로 적혀 있거나 증명이 사라졌다")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[AC] 통과 — 14건 전부 상태와 증명이 실재한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
