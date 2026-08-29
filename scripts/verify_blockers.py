#!/usr/bin/env python
"""잠금 대장 판정 — **막힌 것의 종류를 정확히 말하게 한다** (D-307).

    unlock_type  : 'DEV' | 'CONTRACT' | 'ADMIN' | 'OPS'
    unlock_owner : 누가 푸는가

왜 유형이 필요한가
------------------
지금까지 잠김은 전부 "막혔다" 한 단어였다. 셋은 성격이 전혀 다르다 —
**DEV 는 일정 문제, CONTRACT 는 책임 문제, ADMIN 은 하루면 풀리는데 안 한 것**이다.
그리고 **OPS 는 우리가 만들 수 없는 값**이다 — 현장을 아는 쪽이 채운다(D-338 ③).
OPS 를 DEV 로 적으면 개발이 못 끝낸 일처럼 보이고, 실제로는 아무도 안 채운다.
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

VALID_TYPES = ("DEV", "CONTRACT", "ADMIN", "OPS")
REQUIRED = ("title", "unlock_type", "unlock_owner", "why", "unlock_step", "state_in_code")

#: ★ D-323 — 술어는 「끝났는가」가 아니라 **「지금 막혀 있는가」**다.
#:   그리고 **"완료했다"는 진술이 아니라 확인 행위가 잠금을 내린다** — 두 칸이 그 증거다.
BLOCKED_NOW_VALUES = ("true", "false")
VERIFICATION = ("blocked_now", "verified_at", "verified_by")

#: ★ D-333 — 밖에 기대는 잠금(CONTRACT·ADMIN)은 **먼저 안을 뒤졌는지**를 적는다.
#:   DEV 는 우리가 하는 일이므로 대상이 아니다 — 외부 의존을 만들지 않는 것이 요점이다.
INTERNAL_FIRST = ("internal_alternative_considered", "why_not")
INTERNAL_FIRST_TYPES = ("CONTRACT", "ADMIN")

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
            if value in ("|", ">", ">-", "|-"):
                current[key] = ""
            else:
                # 줄 끝 주석은 값이 아니다 — `sent_at: "2026-09-04"  # 발송 완료` 에서
                # 날짜만 남긴다. 안 자르면 date.fromisoformat 이 그 자리에서 죽는다(실측).
                current[key] = value.split(" #", 1)[0].strip().strip('"')
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
        # ★ D-323 — 확인 행위가 잠금을 내린다. 세 칸이 비면 이 등재는 진술일 뿐이다.
        for field in VERIFICATION:
            if not (row.get(field) or "").strip():
                problems.append(
                    f"{rid}: `{field}` 가 비었다 — **'완료했다'는 진술이 아니라 확인 "
                    f"행위가 잠금을 내린다**(D-323). 발급 완료 · 전달 완료 · 환경 존재는 "
                    f"세 개의 다른 사실이고, 한 칸에 두면 이 대장이 하는 일이 없어진다")
        bn = (row.get("blocked_now") or "").strip().lower()
        if bn and bn not in BLOCKED_NOW_VALUES:
            problems.append(
                f"{rid}: blocked_now='{bn}' 은 true/false 가 아니다 — "
                f"오타는 새 값이 아니다")
        # ★ D-333 — 밖에 기대는 잠금은 **먼저 안을 뒤졌는지**를 적는다.
        if t in INTERNAL_FIRST_TYPES:
            for field in INTERNAL_FIRST:
                if not (row.get(field) or "").strip():
                    problems.append(
                        f"{rid}: {t} 인데 `{field}` 가 비었다 — 밖에 기대기 전에 "
                        f"「우리가 이미 아는 것으로 되는가」를 먼저 적는다(D-333). "
                        f"검토한 게 없으면 \"없음\" 이라고 적어라. **묻지 않고 가는 것만 "
                        f"금지한다** — 만들지 않은 외부 의존은 고장 나지 않는다")
        # ★ D-320 — CONTRACT 는 **시각을 갖는다.** 잠김이 조용히 늙지 않게 한다.
        if t == "CONTRACT":
            for field in ("sent_at", "due_by"):
                if not (row.get(field) or "").strip():
                    problems.append(
                        f"{rid}: CONTRACT 인데 `{field}` 가 없다 — 발송·기한이 없으면 "
                        f"지연이 **얼마나** 되었는지 아무도 못 세고, 세지 못하는 지연은 "
                        f"협상 카드가 되지 않는다 (D-320 · 계약 6조3항 기산)")
    return problems


def elapsed_lines(rows: list[dict]) -> list[str]:
    """CONTRACT 항목의 경과 일수. **매 실행마다 계산한다** — 문서에 적지 않는다(D-320).

    적어 두면 그 숫자는 적은 날에 멈춘다. 시간이 지나는 것이 화면에 보여야 협상 카드가 된다.
    """
    from datetime import date

    out: list[str] = []
    today = date.today()
    for row in rows:
        if (row.get("unlock_type") or "").strip() != "CONTRACT":
            continue
        sent = (row.get("sent_at") or "").strip().strip('"')
        due = (row.get("due_by") or "").strip().strip('"')
        try:
            sent_d = date.fromisoformat(sent)
            due_d = date.fromisoformat(due)
        except ValueError:
            out.append(f"  {row['id']}: 날짜 형식이 아니다 (sent_at={sent!r} due_by={due!r})")
            continue
        waited = (today - sent_d).days
        if today > due_d:
            out.append(f"  ★ {row['id']}: **회신 지연 {(today - due_d).days}일** "
                       f"(발송 {sent} · 기한 {due} · 대기 {waited}일) — "
                       f"계약 6조3항 이행기한 연장 사유가 누적 중이다")
        else:
            out.append(f"  {row['id']}: 발송 {sent} · 기한 {due} · 대기 {waited}일 "
                       f"(기한까지 {(due_d - today).days}일)")
    return out


def summary(rows: list[dict]) -> Counter:
    return Counter((r.get("unlock_type") or "?").strip() for r in rows)


def self_test() -> int:
    good = [{"id": "A", "title": "t", "unlock_type": "DEV", "unlock_owner": "Code",
             "why": "w", "unlock_step": "s", "state_in_code": "scripts",
             "blocked_now": "true", "verified_at": "2026-09-06",
             "verified_by": "파일에서 확인"}]
    ext = {**good[0], "unlock_type": "ADMIN", "unlock_owner": "대표",
           "internal_alternative_considered": "카메라 설치 주소", "why_not": "내부가 이겼다"}
    cases = (
        ("정상 항목은 안 잡는다", good, False),
        # ★ **출생 표본** (D-310) — 이 도구를 만들게 한 바로 그 사례.
        #   잠김이 전부 "막혔다" 한 단어였다. 유형이 비면 **하루짜리(ADMIN)가
        #   계약 리스크(CONTRACT) 뒤에 숨는다** — 아래 갈래가 그것을 잡는다.
        ("★ unlock_type 이 비면 잡는다",
         [{**good[0], "unlock_type": ""}], True),
        ("★ unlock_owner 가 비면 잡는다",
         [{**good[0], "unlock_owner": ""}], True),
        ("열거 밖 유형을 잡는다", [{**good[0], "unlock_type": "TODO"}], True),
        ("없는 파일을 가리키면 잡는다",
         [{**good[0], "state_in_code": "없는/자리.py"}], True),
        ("해소 절차가 없으면 잡는다", [{**good[0], "unlock_step": ""}], True),
        # ★ D-320 — CONTRACT 인데 발송·기한이 없으면 지연을 셀 수 없다.
        ("CONTRACT 인데 sent_at 이 없으면 잡는다",
         [{**good[0], "unlock_type": "CONTRACT", "unlock_owner": "상대방"}], True),
        ("CONTRACT + 발송·기한이 있으면 안 잡는다",
         [{**good[0], "unlock_type": "CONTRACT", "unlock_owner": "상대방",
           "sent_at": "2026-09-04", "due_by": "2026-09-19",
           "internal_alternative_considered": "없음", "why_not": "상대방 사실이다"}], False),
        # ★ D-323 출생 표본 — 「ADMIN 0건」. 발급은 됐고 전달은 안 됐는데
        #   그 셋을 한 칸에 두어서 0 이 되는 쪽으로 적혔다. 확인 칸이 없어서 가능했다.
        ("★ 출생표본 verified_by 가 비면 잡는다 — 진술은 확인이 아니다",
         [{**good[0], "verified_by": ""}], True),
        ("blocked_now 가 비면 잡는다", [{**good[0], "blocked_now": ""}], True),
        ("blocked_now 오타를 잡는다", [{**good[0], "blocked_now": "maybe"}], True),
        ("blocked_now: false 는 그 자체로 위반이 아니다",
         [{**good[0], "blocked_now": "false"}], False),
        # ★ D-333 — 밖에 기대는 잠금만 두 칸을 요구한다
        ("★ ADMIN 인데 내부 대안 칸이 비면 잡는다",
         [{**good[0], "unlock_type": "ADMIN", "unlock_owner": "대표"}], True),
        ("ADMIN + 두 칸이 있으면 안 잡는다", [ext], False),
        ("DEV 는 내부 대안 칸을 요구하지 않는다", [good[0]], False),
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
    print(f"[BLOCKER] 자기시험 {len(cases) + 1}건 통과 (양성 9 · 음성 5 · 출생 표본 포함)")
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

    for line in elapsed_lines(rows):
        print("[BLOCKER]" + line)
    # ★ D-323 — 잠김 총수와 **지금 막고 있는 수**는 다른 수다. 한 칸에 두지 않는다.
    now = [r for r in rows if (r.get("blocked_now") or "").strip().lower() == "true"]
    parked = [r for r in rows if (r.get("blocked_now") or "").strip().lower() == "false"]
    print(f"[BLOCKER] ★ **지금 막고 있는 것 {len(now)}건** · 남겨 두었으나 "
          f"막고 있지 않은 것 {len(parked)}건 (총 {len(rows)}건)")
    for r in parked:
        print(f"[BLOCKER]   (미룸) {r['id']} — 없앤 것과 미룬 것은 다르다. 지우지 않는다")
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
