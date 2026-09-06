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

#: 「잠김」·「미측정」이 어디에 속하는가 (2026-09-21 · 세종 §3 판정).
#:   design 은 **분모에서 뺀다** — 하지 않기로 한 것은 못 한 것이 아니다.
#:   out 은 분모에 남기고 따로 센다 — 조건이 열어 준다.
HANDS = ("design", "out", "in")


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

    #: ★ P-18 턴(2026-09-21) — **분류하지 않은 것은 분모에서 뺄 수 없다.**
    #:   「잠김」·「미측정」은 셋 중 하나여야 한다:
    #:     design  하지 않기로 한 것 — 기능이 아니라 규칙이다. 100%의 대상이 아니다
    #:     out     손 밖 — 상대방·기관·GPU·대표. 조건이 성립하면 열린다
    #:     in      손 안 — 우리가 닫을 수 있다. **이것이 남아 있는 한 100%가 아니다**
    #:   분류를 안 적으면 그 절은 조용히 「어쩔 수 없는 것」이 된다.
    if status in ("잠김", "미측정"):
        hand = (clause.get("hand") or "").strip()
        if hand not in HANDS:
            out.append("%s: '%s' 인데 hand 가 %r 다 — 허용: %s. **분류하지 않은 것은 "
                       "분모에서 뺄 수 없다**" % (cid, status, hand, ", ".join(HANDS)))
        elif len((clause.get("hand_why") or "").strip()) < 10:
            out.append("%s: hand=%s 인데 사유가 없다 — 「손 밖」은 선언이지 면제가 아니다"
                       % (cid, hand))

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


#: 계약 절 대장의 잠금 id → hand. 계약 절은 상태를 두 곳에 적지 않으므로(위 함수)
#: 분류도 **거기 있는 값**에서 파생한다.
CONTRACT_HAND = {
    #: 계약 11조 — 구간 추출은 **하지 않기로 한 것**이다. 기능이 아니라 규칙이므로
    #: 100%의 분모에서 뺀다. 「못 했다」로 세면 영원히 안 채워지는 칸이 생긴다.
    "CLIP_EXTRACTION": "design",
    #: 상대방(SDN) 명세가 오면 열린다 — 조건부다.
    "SDN_API_SPEC": "out",
}


def contract_clause_hands() -> dict[str, int]:
    """계약 절 중 잠김을 hand 별로 센다. 술어는 `unlock_id` 다."""
    text = CONTRACT.read_text(encoding="utf-8")
    out: dict[str, int] = {}
    for m in re.finditer(r"^\s*unlock_id:\s*(\S+)", text, re.MULTILINE):
        hand = CONTRACT_HAND.get(m.group(1).strip())
        if hand:
            out[hand] = out.get(hand, 0) + 1
    return out


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
        not problems({"id": "X", "status": "잠김", "blocker": "MIGRATE_ONE_LINER",
                      "hand": "in", "hand_why": "우회 경로를 우리 층에 둔다"})))
    #: ★ 2026-09-21 — **분류하지 않은 것은 분모에서 뺄 수 없다** (세종 §3).
    checks.append((
        "'잠김' 인데 hand 가 없으면 잡는다",
        any("분모에서 뺄 수 없다" in p
            for p in problems({"id": "X", "status": "잠김",
                               "blocker": "MIGRATE_ONE_LINER"}))))
    checks.append((
        "hand 는 있는데 사유가 없으면 잡는다 — 「손 밖」은 선언이지 면제가 아니다",
        any("선언이지 면제가" in p
            for p in problems({"id": "X", "status": "미측정", "why": "재는 중",
                               "hand": "out"}))))
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

def load() -> tuple[list[dict], dict[str, dict[str, int]], list[str], dict[str, int],
                    dict[str, int], dict[str, int]]:
    data = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    areas = data["areas"]
    ids = blocker_ids()
    counts: dict[str, dict[str, int]] = {}
    hands: dict[str, int] = dict(contract_clause_hands())   # 계약 절 몫을 먼저 담는다
    #: ★ 2026-09-24 (P-26) — hand 는 이제 '미착수' 에도 붙는다(PRD v2.5 15절이 전부 `hand: in`).
    #:   그래서 「잠김·미측정 중 손 안」을 따로 센다 — 안 가르면 아래 한 줄이
    #:   34 + 22 = 56 처럼 읽혀 **남은 40절과 어긋난다.** 분모는 그대로다(design·out 만 뺀다).
    hands_lock: dict[str, int] = dict(contract_clause_hands())
    #: ★ [2026-09-26] **'미착수' 도 손 밖일 수 있다** — P-30 이 OPS-12 를 쪼개며
    #:   「다른 호스트」 갈래를 미착수·손 밖으로 냈다. 계약 절(영역 ①)의 몫은 여기
    #:   담지 않는다: 그쪽 미착수는 잠금 대장이 아니라 계약 대장이 세고, 그 수는
    #:   `contract_clause_hands()` 가 이미 hands 에 넣었다.
    hands_todo: dict[str, int] = {}
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
                hand = (clause.get("hand") or "").strip()
                if hand in HANDS:
                    hands[hand] = hands.get(hand, 0) + 1
                    if status in ("잠김", "미측정"):
                        hands_lock[hand] = hands_lock.get(hand, 0) + 1
                    elif status == "미착수":
                        hands_todo[hand] = hands_todo.get(hand, 0) + 1
                elif status == "미착수":
                    #: hand 칸이 없는 미착수. **손 밖이라 적힌 적이 없으므로 손 안이다** —
                    #: 다만 「손 안이라고 적은 것」과 구별해 센다. 둘을 뭉치면
                    #: 분류를 잊은 절과 분류한 절이 같은 칸에 선다(D-301).
                    hands_todo["none"] = hands_todo.get("none", 0) + 1
        counts[area["id"]] = c

    # ── P-81 · 대장 id 는 **유일하다** (2026-09-06 · 턴 H) ──────────────────
    #   ★ **출생 표본**: 턴 G 에 새 절을 `SEC-14` 로 등재했는데 그 id 는 이미
    #     「익명 반출 0건」이 쓰고 있었다. YAML 은 같은 id 를 **두 항목으로 그냥 싣고**,
    #     이 판정기는 절을 세기만 했으므로 **아무 색도 안 났다** — 대장이 조용히 겹쳤다.
    #     세종·영실 둘 다 못 봤다. 사람이 두 번 놓친 자리는 사람을 한 번 더 세우는 것이
    #     아니라 **게이트를 세우는 자리**다(D-286).
    #   ⚠ 겹친 id 는 「어느 쪽이 진짜인가」를 아무도 못 답하게 만든다. 증명·상태·손이
    #     둘로 갈리고, 절 수는 그대로라 **수가 안 움직인다**. 조용한 것이 가장 나쁘다.
    seen: dict[str, str] = {}
    for area in areas:
        for clause in (area.get("clauses") or []):
            cid = (clause.get("id") or "").strip()
            if not cid:
                continue
            if cid in seen:
                problems.append(
                    "대장 id 가 겹친다: %s — 영역 %s 와 영역 %s 에 둘 다 있다. "
                    "겹친 id 는 「어느 쪽이 진짜인가」를 아무도 못 답하게 만든다"
                    % (cid, seen[cid], area["id"]))
            else:
                seen[cid] = area["id"]

    weights = sum(a["weight"] for a in areas)
    if weights != 100:
        problems.insert(0, "가중치 합이 %d 다 — 100 이 아니면 아래 수는 전부 무의미하다" % weights)
    return areas, counts, problems, hands, hands_lock, hands_todo


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

    areas, counts, problems, hands, hands_lock, hands_todo = load()
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

    # ── 손 안 도달율 (2026-09-21 · 세종 §3) ────────────────────────────────
    # **우리가 닫을 수 있는 100%** 를 따로 낸다. 두 수를 함께 적는 이유:
    #   가중 합계만 적으면 「상대방이 안 주는 것」과 「우리가 안 한 것」이 같은 칸에서
    #   같은 무게로 눌러 앉는다. 그러면 아무리 일해도 수가 안 오르는 것처럼 보이고,
    #   반대로 손 안에 남은 것이 몇인지도 안 보인다.
    design, out_of_hand, in_hand = (hands.get(k, 0) for k in HANDS)
    denom = all_clauses - design - out_of_hand
    print("[GA] [입력] 분류 %d건 — 설계 잠금 %d(분모에서 뺀다) · 손 밖 %d · 손 안 %d"
          % (design + out_of_hand + in_hand, design, out_of_hand, in_hand))
    if denom > 0:
        print("[GA] ★ **손 안 도달율 %.1f%%** = 구현 %d / (%d − 설계 잠금 %d − 손 밖 %d = %d)"
              % (done / denom * 100, done, all_clauses, design, out_of_hand, denom))
        #: 미착수도 **손 안 것만** 센다 — 손 밖 미착수를 우리 잔여에 넣으면
        #: 갚을 수 없는 절이 진척률을 눌러 앉는다(D-311 이 잠자는 빚에서 한 것과 같다).
        #: 계약 절(영역 ①)의 미착수는 hand 칸이 없으므로 아래 「그 밖」이 받는다.
        marked = hands_todo.get("in", 0)
        unmarked = hands_todo.get("none", 0)
        in_lock = hands_lock.get("in", 0)
        contract_rest = (denom - done) - marked - unmarked - in_lock
        print("[GA]   손 안에 남은 %d절 = 미착수 %d(손 안이라 적힘) + 미착수 %d(hand 미기재) "
              "+ 잠김·미측정 중 손 안 %d + 계약 절 %d — "
              "이 %d절이 **우리가 닫을 수 있는 100%%** 까지의 거리다"
              % (denom - done, marked, unmarked, in_lock, contract_rest, denom - done))
        not_started = marked + unmarked + contract_rest
        if not_started + in_lock != denom - done:
            print("[GA]   ⚠ 두 몫의 합 %d 이 남은 %d 과 다르다 — 분류가 어긋났다"
                  % (not_started + in_lock, denom - done))
    else:
        print("[GA] 손 안 도달율 **판정 불가** — 분모가 0 이하다 (분류가 어긋났다)")

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
