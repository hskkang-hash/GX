#!/usr/bin/env python
"""계약 AC 전수 대장 판정 — **절 단위** (D-309 · D-314 확장).

    · 대장 행 수 ≠ 14 이면 exit 1
    · **상태 '부분' 이 한 칸이라도 남아 있으면 exit 1**  ← D-314 의 핵심
    · '구현' 절에 증명 시험이 없으면 exit 1 (그런 절은 '미측정' 으로 적는다)
    · 적힌 시험 **파일이 없거나 그 메서드 이름이 없으면** exit 1 (없는 시험은 문서다)
    · 절에 AC 원문 인용(`quote`)이 없거나 **그 인용이 ac 의 부분 문자열이 아니면** exit 1
    · 출력: 절 총수 · 구현 · 미착수 · 잠김 · 미측정 (건수 출력 필수 · D-301)

왜 절인가 — **'부분' 은 상태가 아니라 아직 안 쪼갠 것의 이름이다**
------------------------------------------------------------------
'부분' 이 5건 남아 있는 한 잔여를 모른다. 5건이 95% 인지 20% 인지 표가 말하지 못한다 —
착시 ③(모수와 술어)의 대장 판이다. 계약 AC 는 문장이고, 문장은 절로 쪼갤 수 있다.
쪼개고 나면 **잔여가 숫자**가 된다.

    python scripts/verify_contract_ac.py            # 판정
    python scripts/verify_contract_ac.py --table    # 사람이 읽는 절 표 (대표 보고용)
    python scripts/verify_contract_ac.py --self-test

★ 자기표본 (D-310) — 이 도구를 태어나게 한 사례를 fixture 로 박는다
------------------------------------------------------------------
태어난 사유 둘:
  ① (D-309) *"재는 시험이 없는 칸이 '구현' 으로 적혀 있었다."*
  ② (D-314) *"'부분' 이라는 칸이 잔여를 숨겼다."*
그 둘이 자기시험의 첫 두 갈래다. 거기서 초록이 나오면 이 도구는 도구가 아니다.
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
CLAUSE_STATES = ("구현", "미착수", "잠김", "미측정")

#: ★ D-314 가 없앤 칸. 대장 어디에도 상태로 남아 있으면 안 된다.
BANNED_STATE = "부분"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def parse(text: str) -> list[dict]:
    """대장을 읽는다. **PyYAML 을 요구하지 않는다** — 컨테이너에 없다(실측).

    파서를 요구하면 이 게이트는 환경에 따라 사라지고, 사라진 게이트는 사라진 것이
    보이지 않는다. 보는 것이 단순하므로(기능 → 절 → 스칼라) 직접 읽는다.
    """
    features: list[dict] = []
    feature: dict | None = None
    clause: dict | None = None
    key: str | None = None
    in_proof = False

    for raw in text.split("\n"):
        stripped = raw.strip()
        if stripped.startswith("#"):
            continue

        m = re.match(r"^  - id:\s*(\S+)", raw)
        if m:
            feature = {"id": m.group(1), "clauses": []}
            features.append(feature)
            clause, key, in_proof = None, None, False
            continue
        if feature is None:
            continue

        m = re.match(r"^      - quote:\s*(.*)$", raw)
        if m:
            clause = {"quote": m.group(1).strip().strip('"'), "proof": []}
            feature["clauses"].append(clause)
            key, in_proof = "quote", False
            continue

        # 절 안의 스칼라 / proof 목록
        m = re.match(r"^        ([a-z_]+):\s*(.*)$", raw)
        if m and clause is not None:
            key, value = m.group(1), m.group(2).strip()
            in_proof = key == "proof"
            if in_proof:
                continue
            clause[key] = "" if value in ("|", ">", ">-", "|-", "[]") else value.strip('"')
            continue
        m = re.match(r'^          - "(.+)"\s*$', raw)
        if m and clause is not None and in_proof:
            clause["proof"].append(m.group(1))
            continue

        # 기능 수준 스칼라
        m = re.match(r"^    ([a-z_]+):\s*(.*)$", raw)
        if m:
            key, value = m.group(1), m.group(2).strip()
            clause, in_proof = None, False
            if key == "clauses":
                continue
            feature[key] = "" if value in ("|", ">", ">-", "|-") else value.strip('"')
            continue

        # 이어지는 블록 문자열
        if key and clause is not None and raw.startswith("          ") and not in_proof:
            clause[key] = (clause.get(key, "") + " " + stripped).strip()
        elif key and clause is None and feature is not None and raw.startswith("      "):
            feature[key] = (feature.get(key, "") + " " + stripped).strip()
    return features


def blocker_ids() -> set[str]:
    if not BLOCKERS.is_file():
        return set()
    return set(re.findall(r"^  - id:\s*(\S+)", BLOCKERS.read_text(encoding="utf-8"), re.M))


def check(features: list[dict], known_blockers: set[str], raw_text: str = "",
          proof_exists=None) -> list[str]:
    """proof_exists(path, method) -> bool 을 주입받는다 — 자기시험이 파일 없이 돈다."""
    if proof_exists is None:
        def proof_exists(path: str, method: str) -> bool:
            f = ROOT / path
            return f.is_file() and f"def {method}(" in f.read_text(encoding="utf-8")

    problems: list[str] = []

    # ★ D-314 — '부분' 이라는 칸 자체가 없어야 한다.
    if re.search(rf"^\s*state:\s*{BANNED_STATE}\s*$", raw_text, re.M):
        problems.append(
            f"대장에 상태 '{BANNED_STATE}' 가 남아 있다 — '{BANNED_STATE}' 은 상태가 아니라 "
            f"**아직 안 쪼갠 것의 이름**이다. 절로 쪼개면 잔여가 숫자가 된다 (D-314)")

    ids = [f["id"] for f in features]
    if len(features) != len(EXPECTED_IDS):
        problems.append(
            f"대장이 {len(features)}행이다 — 계약 기능은 {len(EXPECTED_IDS)}건이다. "
            f"빠진 줄은 보이지 않는다(D-274)")
    missing = [f for f in EXPECTED_IDS if f not in ids]
    if missing:
        problems.append(f"대장에 없는 기능: {missing}")

    for feature in features:
        fid = feature.get("id", "?")
        ac = (feature.get("ac") or "").strip()
        if not ac:
            problems.append(f"{fid}: 계약 AC 원문이 비었다")
        clauses = feature.get("clauses") or []
        if not clauses:
            problems.append(
                f"{fid}: 절이 하나도 없다 — 쪼개지 않으면 잔여를 모른다 (D-314)")

        for clause in clauses:
            quote = (clause.get("quote") or "").strip()
            state = (clause.get("state") or "").strip()
            label = f"{fid}[{quote[:20]}]"

            # 규칙 ③ — 원문 인용이 실제로 AC 안에 있는가
            if not quote:
                problems.append(f"{fid}: 인용 없는 절이 있다 — 그것은 우리가 만든 절이지 "
                                f"계약의 절이 아니다 (D-314 규칙 ③)")
            elif ac and quote not in ac:
                problems.append(
                    f"{label}: 인용이 AC 문장에 없다. 계약의 절이 아니라 우리가 만든 절이다 — "
                    f"AC 문장을 고쳐야 한다면 그것은 **원문 실측**의 일이다 (D-316)")

            # 규칙 ① — '부분' 은 절 단위에 존재할 수 없다
            if state not in CLAUSE_STATES:
                problems.append(f"{label}: state='{state}' 는 열거 밖이다 {CLAUSE_STATES}")

            # 규칙 ② — '구현' 절에는 증명 시험이 반드시 있다
            proofs = clause.get("proof") or []
            if state == "구현" and not proofs:
                problems.append(
                    f"{label}: '구현' 인데 증명 시험이 없다 — 그런 절은 **'미측정'** 이다. "
                    f"구현 주장은 시험이 하지 사람이 하지 않는다 (D-314 규칙 ②)")
            for proof in proofs:
                if "::" not in proof:
                    problems.append(f"{label}: proof '{proof}' 형식이 아니다 (파일::메서드)")
                    continue
                path, method = proof.split("::", 1)
                if not proof_exists(path, method):
                    problems.append(
                        f"{label}: 증명 시험이 실재하지 않는다 — {proof}. "
                        f"없는 시험을 적으면 그것도 문서다 (D-286)")

            unlock = (clause.get("unlock_id") or "").strip()
            if state == "잠김" and not unlock:
                problems.append(f"{label}: '잠김' 인데 unlock_id 가 없다 — 누가 푸는지 "
                                f"모른다 (D-307)")
            if unlock and known_blockers and unlock not in known_blockers:
                problems.append(f"{label}: unlock_id='{unlock}' 가 잠금 대장에 없다 — 유령 참조다")
            if state in ("미착수", "잠김") and not (clause.get("note") or "").strip():
                problems.append(
                    f"{label}: state='{state}' 인데 사유가 없다. 못 하는 것을 안 적으면 "
                    f"'거의 다 됨' 으로 읽힌다 (D-264)")
    return problems


def clause_counts(features: list[dict]) -> Counter:
    return Counter((c.get("state") or "?").strip()
                   for f in features for c in (f.get("clauses") or []))


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — ★ 첫 두 갈래가 **이 도구를 태어나게 한 표본**이다 (D-310)
# ═══════════════════════════════════════════════════════════════════════════
def _feature(fid: str, **kw) -> dict:
    base = {
        "id": fid, "ac": "가 나 다",
        "clauses": [{"quote": "가", "state": "구현",
                     "proof": ["tests/x.py::test_a"], "note": ""}],
    }
    base.update(kw)
    return base


def self_test() -> int:
    full = [_feature(f) for f in EXPECTED_IDS]

    def yes(path, method):
        return True

    def no(path, method):
        return False

    birth_309 = [dict(f, clauses=[{"quote": "가", "state": "구현", "proof": []}])
                 if f["id"] == "F-05" else f for f in full]
    birth_314 = full   # raw_text 로 '부분' 을 주입한다

    cases = (
        ("정상 대장은 안 잡는다", full, "", yes, False),
        ("★ 출생표본① 증명 없는 '구현' 을 잡는다 (D-309)", birth_309, "", yes, True),
        ("★ 출생표본② 상태 '부분' 이 남아 있으면 잡는다 (D-314)",
         birth_314, "    state: 부분\n", yes, True),
        ("행 수가 14 가 아니면 잡는다", full[:5], "", yes, True),
        ("없는 시험을 가리키면 잡는다", full, "", no, True),
        ("AC 에 없는 인용을 잡는다",
         [dict(f, clauses=[{"quote": "라", "state": "구현",
                            "proof": ["tests/x.py::test_a"]}])
          if f["id"] == "F-02" else f for f in full], "", yes, True),
        ("'잠김' 인데 unlock_id 가 없으면 잡는다",
         [dict(f, clauses=[{"quote": "가", "state": "잠김", "proof": [], "note": "사유"}])
          if f["id"] == "F-06" else f for f in full], "", yes, True),
        ("'미착수' 인데 사유가 없으면 잡는다",
         [dict(f, clauses=[{"quote": "가", "state": "미착수", "proof": []}])
          if f["id"] == "F-07" else f for f in full], "", yes, True),
    )
    bad = 0
    for label, feats, raw, pe, should_fail in cases:
        ok = bool(check(feats, set(), raw, pe)) == should_fail
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1
    parsed = parse(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else []
    n_clauses = sum(len(f.get("clauses") or []) for f in parsed)
    ok_parse = len(parsed) == len(EXPECTED_IDS) and n_clauses >= len(EXPECTED_IDS)
    print(f"  {'OK  ' if ok_parse else 'FAIL'} 파서가 대장을 읽는다 "
          f"({len(parsed)}행 · 절 {n_clauses})")
    if not ok_parse:
        bad += 1
    if bad:
        print(f"[AC] 자기시험 {bad}건 실패 — 이 판정기는 눈이 멀었다")
        return 1
    print(f"[AC] 자기시험 {len(cases) + 1}건 통과 (출생표본 2 포함)")
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

    raw = LEDGER.read_text(encoding="utf-8")
    features = parse(raw)
    counts = clause_counts(features)
    total = sum(counts.values())
    proofs = sum(len(c.get("proof") or [])
                 for f in features for c in (f.get("clauses") or []))

    print(f"[AC] 검사 {len(features)}행 · **절 {total}개** "
          f"(모수=계약 기능 {len(EXPECTED_IDS)}건을 절로 쪼갠 것 · "
          f"술어=절 상태 + 인용 대조 + 시험 실재) · 증명 시험 {proofs}건")
    if not total:
        print("[AC] 절이 0개다 — 파서가 눈이 멀었거나 대장이 안 쪼개졌다. "
              "0 을 통과로 읽지 않는다 (D-301)")
        return 1
    print("[AC] 절 상태: " + " · ".join(f"{s} {counts.get(s, 0)}" for s in CLAUSE_STATES))
    done = counts.get("구현", 0)
    print(f"[AC] ★ **잔여 {total - done}절 / 전체 {total}절** "
          f"(구현 {done} · {done * 100 // total}%) — 이제 잔여가 숫자다")

    if args.table:
        print()
        for f in features:
            print(f"  {f['id']}  ({f.get('kernel', '?')})  {(f.get('ac') or '')[:60]}")
            for c in f.get("clauses") or []:
                mark = {"구현": "OK  ", "미착수": "TODO", "잠김": "LOCK",
                        "미측정": "????"}.get(c.get("state", ""), "??  ")
                extra = f" → {c.get('unlock_id')}" if c.get("unlock_id") else ""
                print(f"      {mark} {(c.get('quote') or '')[:34]:36} "
                      f"증명 {len(c.get('proof') or [])}{extra}")

    problems = check(features, blocker_ids(), raw)
    if problems:
        print("[AC] 위반 — 재지 않은 것이 '구현' 으로 적혀 있거나 증명이 사라졌다")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[AC] 통과 — 14건이 절로 쪼개져 있고, 절마다 상태·인용·증명이 실재한다")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    _feats = parse(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else []
    _n_clause = sum(len(f.get("clauses") or []) for f in _feats)
    #: ★ [P-204 · 턴 Z · Q] **마지막 줄은 분모다.** 이 수는 **지금 센 것**이다 —
    #:   손으로 적은 수는 분모가 아니고, 분모를 안 말한 `exit 0` 은
    #:   「이 게이트가 통과」가 아니라 「이 호출이 끝났다」일 뿐이다.
    gate_header(__file__, measured=(
        "계약 기능을 **절로 쪼갠 것**마다 상태·인용 대조·증명 시험 실재를 본다 — "
        "**분모 %d절**(기능 %d건을 쪼갠 것 · 지금 읽었다)" % (_n_clause, len(_feats))))
    sys.exit(main())
