#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""D-346 — 상용 오픈 기준 8영역을 **절 단위**로 판정하고 가중 합계를 낸다.

왜 이 표가 계약 표와 따로인가 (D-345)
-------------------------------------
    계약 39절을 100% 채워도 **상용 출시는 되지 않는다.** 계약에 없는 것이 상용에는 필수다.
    그래서 축을 둘로 나눠 잰다. **합쳐서 하나의 %로 내지 않는다** —
    합치는 순간 어느 쪽도 알 수 없게 된다.

보는 것 — 일곱
--------------
  ① 가중치 합이 100 인가 (모수가 흔들리면 아래 수는 전부 무의미하다)
  ② 상태가 넷 안에 있는가 — 구현 · 미착수 · 잠김 · 미측정
  ③ **「부분」류가 한 칸이라도 있으면 exit 1** (D-314) — 「부분」은 상태가 아니라
     **아직 안 쪼갠 것의 이름**이다
  ④ ★ **'구현' 에 증명이 있고 그 파일이 실재하는가** — 없으면 그 칸은 '미측정'이다 (D-346)
  ⑤ '잠김' 의 blocker id 가 `DA-05/blockers.yaml` 에 실재하는가
  ⑥ '미착수'·'미측정' 에 사유가 있는가 (사유 없는 빈칸은 잊은 것과 구별되지 않는다)
  ⑦ 영역 ①은 **계약 절 대장에서 파생**한다 — 절 상태를 두 곳에 적지 않는다

★ 출생 표본 (D-310)
-------------------
이 도구를 만들게 한 문장은 D-346 의 이것이다:

    **증명이 없는 칸은 '구현'으로 적을 수 없다. 그런 칸은 '미측정'이다.**

그래서 자기시험의 첫 갈래가 **「증명 없는 '구현'」과 「없는 파일을 가리키는 증명」**이다.
거기서 초록이 나오면 이 표는 스스로를 부풀린다 — 착시 ①(부착률을 완성으로)의 상용판이다.

    python scripts/verify_ga_readiness.py            # 판정 + 가중 합계
    python scripts/verify_ga_readiness.py --list     # 영역별 절 표
    python scripts/verify_ga_readiness.py --table    # 대표 보고용 표 (마크다운)
    python scripts/verify_ga_readiness.py --self-test

호스트에서 돈다 — Django 가 필요 없다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "agent" / "evidence" / "D-346" / "ga_readiness.yaml"
BLOCKERS = ROOT / "docs" / "agent" / "evidence" / "DA-05" / "blockers.yaml"
CONTRACT = ROOT / "docs" / "agent" / "evidence" / "D-309" / "contract_ac_ledger.yaml"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

DONE = "구현"
STATUSES = (DONE, "미착수", "잠김", "미측정")
BANNED = ("부분", "진행중", "일부", "대부분", "거의")
NEEDS_WHY = ("미착수", "미측정")


# ═══════════════════════════════════════════════════════════════════════════
# 술어 — 파일 없이 시험할 수 있게 순수 함수로 둔다
# ═══════════════════════════════════════════════════════════════════════════

def judge_clause(clause: dict, *, exists, blocker_ids: set[str]) -> list[str]:
    """절 하나를 판정한다. 어긋난 것들을 돌려준다 — **판정은 부르는 쪽이 한다.**"""
    cid = clause.get("id", "(id 없음)")
    status = (clause.get("status") or "").strip()
    out: list[str] = []

    if status in BANNED:
        out.append("%s: 상태 «%s» — 「부분」류는 상태가 아니다. 절로 쪼개라 (D-314)" % (cid, status))
        return out
    if status not in STATUSES:
        out.append("%s: 상태 «%s» 가 넷 밖이다 (%s)" % (cid, status, " · ".join(STATUSES)))
        return out

    if status == DONE:
        proof = (clause.get("proof") or "").strip()
        if not proof:
            out.append("%s: '구현' 인데 증명이 없다 — **그런 칸은 '미측정'이다** (D-346)" % cid)
        elif not exists(proof):
            out.append("%s: 증명이 가리킨 «%s» 가 없다 — 없는 증명은 문서다" % (cid, proof))

    if status == "잠김":
        blocker = (clause.get("blocker") or "").strip()
        if not blocker:
            out.append("%s: '잠김' 인데 blocker 가 없다 — 무엇이 막는지 말하지 않는다" % cid)
        elif blocker not in blocker_ids:
            out.append("%s: blocker «%s» 가 잠금 대장에 없다" % (cid, blocker))

    if status in NEEDS_WHY and not (clause.get("why") or "").strip():
        out.append("%s: '%s' 인데 사유가 없다 — 잊은 것과 구별되지 않는다" % (cid, status))

    # ★ '미착수'·'미측정' 인데 blocker 를 단 것은 허용한다(그 자리가 왜 안 되는지의 근거다).
    blocker = (clause.get("blocker") or "").strip()
    if blocker and blocker not in blocker_ids:
        out.append("%s: blocker «%s» 가 잠금 대장에 없다" % (cid, blocker))
    return out


def score(areas: list[dict], counts: dict[str, dict[str, int]]) -> tuple[float, list[tuple]]:
    """가중 합계. 영역 점수 = 구현 절 / 전체 절."""
    rows = []
    total = 0.0
    for area in areas:
        c = counts[area["id"]]
        n = sum(c.values())
        ratio = (c.get(DONE, 0) / n) if n else 0.0
        weighted = area["weight"] * ratio
        total += weighted
        rows.append((area["id"], area["name"], area["weight"], c.get(DONE, 0), n,
                     ratio, weighted))
    return total, rows


# ═══════════════════════════════════════════════════════════════════════════
# 읽기
# ═══════════════════════════════════════════════════════════════════════════

def contract_clause_counts() -> dict[str, int]:
    """영역 ①은 계약 절 대장에서 **파생한다** — 절 상태를 두 곳에 적지 않는다.

    두 곳에 적으면 반드시 갈리고, 갈리는 순간 하나는 거짓말이다(D-227 이 만든 상태).
    """
    text = CONTRACT.read_text(encoding="utf-8")
    counts: dict[str, int] = {}
    # 계약 절 대장은 칸 이름이 `state` 다 (`status` 가 아니다) —
    # 두 대장이 같은 낱말을 안 쓰는 것도 「같은 이름, 다른 것」의 이웃이다(D-337).
    for m in re.finditer(r"^\s*(?:-\s*)?state:\s*(\S+)", text, re.MULTILINE):
        value = m.group(1).strip().strip('"').strip("'")
        if value in STATUSES:
            counts[value] = counts.get(value, 0) + 1
    return counts


def blocker_ids() -> set[str]:
    if not BLOCKERS.exists():
        return set()
    return set(re.findall(r"^\s*-\s*id:\s*(\S+)", BLOCKERS.read_text(encoding="utf-8"),
                          re.MULTILINE))


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310)
# ═══════════════════════════════════════════════════════════════════════════

def self_test() -> int:
    ok_exists = {"backend/tests/x.py"}.__contains__
    ids = {"MIGRATE_ONE_LINER"}
    checks: list[tuple[str, bool]] = []

    def problems(clause):
        return judge_clause(clause, exists=ok_exists, blocker_ids=ids)

    checks.append((
        "★ 출생표본 — 증명 없는 '구현' 을 잡는다 (D-346)",
        any("'미측정'이다" in p for p in problems({"id": "X", "status": "구현"}))))
    checks.append((
        "★ 출생표본 — 없는 파일을 가리킨 증명을 잡는다",
        any("없는 증명은 문서다" in p
            for p in problems({"id": "X", "status": "구현", "proof": "backend/없다.py"}))))
    checks.append((
        "★ 「부분」은 상태가 아니다 (D-314)",
        any("절로 쪼개라" in p for p in problems({"id": "X", "status": "부분"}))))
    checks.append((
        "증명이 실재하는 '구현' 은 통과한다",
        not problems({"id": "X", "status": "구현", "proof": "backend/tests/x.py"})))
    checks.append((
        "'잠김' 인데 blocker 가 없으면 잡는다",
        any("무엇이 막는지" in p for p in problems({"id": "X", "status": "잠김"}))))
    checks.append((
        "잠금 대장에 없는 blocker 를 잡는다",
        any("잠금 대장에 없다" in p
            for p in problems({"id": "X", "status": "잠김", "blocker": "없는것"}))))
    checks.append((
        "대장에 있는 blocker 는 통과한다",
        not problems({"id": "X", "status": "잠김", "blocker": "MIGRATE_ONE_LINER"})))
    checks.append((
        "사유 없는 '미착수' 를 잡는다",
        any("사유가 없다" in p for p in problems({"id": "X", "status": "미착수"}))))
    checks.append((
        "넷 밖의 상태를 잡는다",
        any("넷 밖이다" in p for p in problems({"id": "X", "status": "검토중"}))))

    # 가중 합계 계산 — 손으로 검산할 수 있는 표본
    total, _ = score(
        [{"id": "a", "name": "A", "weight": 20}, {"id": "b", "name": "B", "weight": 80}],
        {"a": {DONE: 1, "미착수": 1}, "b": {DONE: 0, "미착수": 4}})
    checks.append(("가중 합계가 절 비율로 계산된다 (20×½ + 80×0 = 10)", abs(total - 10.0) < 1e-9))
    total, _ = score([{"id": "a", "name": "A", "weight": 100}], {"a": {DONE: 3}})
    checks.append(("전부 구현이면 100 이다", abs(total - 100.0) < 1e-9))
    total, _ = score([{"id": "a", "name": "A", "weight": 100}], {"a": {}})
    checks.append(("절이 0개인 영역은 0 이다 (1 이 아니다)", abs(total) < 1e-9))

    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[GA] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return 1 if bad else 0


# ═══════════════════════════════════════════════════════════════════════════

def load() -> tuple[list[dict], dict[str, dict[str, int]], list[str]]:
    data = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    areas = data["areas"]
    ids = blocker_ids()
    counts: dict[str, dict[str, int]] = {}
    problems: list[str] = []

    for area in areas:
        c: dict[str, int] = {}
        if area.get("derived_from"):
            derived = contract_clause_counts()
            if not derived:
                problems.append("영역 %s: %s 에서 절을 읽지 못했다 — 판정이 아니라 열거기 고장이다"
                                % (area["id"], area["derived_from"]))
            c = derived
        else:
            clauses = area.get("clauses") or []
            if not clauses:
                problems.append("영역 %s(%s): 절이 0개다 — 쪼개지 않은 영역은 잴 수 없다"
                                % (area["id"], area["name"]))
            for clause in clauses:
                problems += ["영역 %s · %s" % (area["id"], p) for p in judge_clause(
                    clause, exists=lambda rel: (ROOT / rel).exists(), blocker_ids=ids)]
                status = (clause.get("status") or "").strip()
                c[status] = c.get(status, 0) + 1
        counts[area["id"]] = c

    weights = sum(a["weight"] for a in areas)
    if weights != 100:
        problems.insert(0, "가중치 합이 %d 다 — 100 이 아니면 아래 수는 전부 무의미하다" % weights)
    return areas, counts, problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not LEDGER.exists():
        print("[GA] 대장이 없다: %s" % LEDGER)
        return 1

    areas, counts, problems = load()
    total, rows = score(areas, counts)
    all_clauses = sum(sum(c.values()) for c in counts.values())
    done = sum(c.get(DONE, 0) for c in counts.values())

    print("[GA] [입력] 영역 %d · 절 %d개 (구현 %d · 미착수 %d · 잠김 %d · 미측정 %d)"
          % (len(areas), all_clauses, done,
             sum(c.get("미착수", 0) for c in counts.values()),
             sum(c.get("잠김", 0) for c in counts.values()),
             sum(c.get("미측정", 0) for c in counts.values())))

    for aid, name, weight, d, n, ratio, weighted in rows:
        print("  %-2s %-22s 가중 %2d%%  절 %2d/%-2d = %3.0f%%  →  %5.2f"
              % (aid, name, weight, d, n, ratio * 100, weighted))
    print("[GA] ★ 상용 오픈 가중 합계 **%.1f%%** [실측]" % total)
    print("[GA] (계약 축과 합치지 않는다 — D-345. 계약 절은 영역 ①이 그대로 인용한다)")

    if args.list or args.table:
        _print_table(areas, counts, rows, total, markdown=args.table)

    if problems:
        for p in problems:
            print("[GA] FAIL %s" % p)
        return 1
    print("[GA] 통과 — 절마다 상태·증명·사유가 실재한다")
    return 0


def _print_table(areas, counts, rows, total, *, markdown: bool) -> None:
    if markdown:
        print()
        print("| 영역 | 가중 | 절 구현/전체 | 영역 달성 | 가중 기여 |")
        print("|---|---:|---:|---:|---:|")
        for aid, name, weight, d, n, ratio, weighted in rows:
            print("| %s %s | %d%% | %d/%d | %.0f%% | %.2f |"
                  % (aid, name, weight, d, n, ratio * 100, weighted))
        print("| **합계** | **100%%** | | | **%.1f%%** |" % total)
        print()
    for area in areas:
        if area.get("derived_from"):
            print("\n[%s] %s — %s 에서 파생: %s"
                  % (area["id"], area["name"], area["derived_from"],
                     " · ".join("%s %d" % kv for kv in sorted(counts[area["id"]].items()))))
            continue
        print("\n[%s] %s" % (area["id"], area["name"]))
        for clause in area.get("clauses") or []:
            mark = clause.get("proof") or clause.get("blocker") or ""
            print("   %-8s %-8s %-58s %s"
                  % (clause.get("id", "?"), clause.get("status", "?"),
                     clause.get("title", "")[:58], mark))


if __name__ == "__main__":
    raise SystemExit(main())
