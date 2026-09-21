#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""D-344 — **같은 수가 아니면 같은 술어가 아니다.** 수를 내는 도구를 두 번 돌려 대조한다.

무슨 일이 있었나 (출생 표본 · D-310)
------------------------------------
    임계값 전수가 [실측]610/127(직전 턴) → [실측]614/131(그 다음 턴) 로 바뀌었다.
    그 턴은 **자기 변경분 기여 0건**이라고 보고했고, 어느 쪽이 맞는지 모른다고 올렸다.

    [실측 2026-09-08 · 같은 술어를 여러 커밋에 얹어 재현했다]
      `probe_threshold_census.py`(25daaf5 에서 태어나 그 뒤 한 줄도 안 바뀌었다)를
      워크트리에 복사해 커밋마다 돌렸다:

          8dfa9fa · 6dcd965 · d601a79 · 030178c   →  610 / 127
          25daaf5 · d5cb454                        →  614 / 131

      같은 커밋에서 두 번 돌리면 **같은 수**가 나온다 — 술어는 결정적이다(D-344 ①).
      늘어난 4건은 **25daaf5 자신이 더한 것**이다:

          common/audit_writer.py        limit = 100
          kernels/k5_trust/audit.py     limit = 100
          kernels/k5_trust/credentials.py  len(value) <= 8
          kernels/k5_trust/services.py  limit = 50

    ★ 그러므로 「자기 변경분 기여 0건」은 **틀렸다.** 610 은 그 턴이 **자기 코드를 쓰기 전에**
      잰 수였고, 614 는 쓴 뒤에 잰 수다. 두 수는 다른 트리에서 나왔다 —
      **수가 아니라 측정 시점이 달랐다.**

원칙 (D-344)
------------
    수를 보고하는 도구는 **재현 가능해야 한다.** 같은 커밋에서 두 번 돌려 다른 수가 나오면
    그건 수를 **세는** 도구가 아니라 **추정하는** 도구다.

    그리고 이 사고가 가르친 두 번째: **수에는 커밋이 붙어야 한다.** 어느 트리에서 잰
    수인지 모르면 두 수를 비교할 수 없고, 비교할 수 없는 두 수를 비교하면 없는 원인을 찾는다.

무엇을 하나
-----------
  ① 등재된 측정 도구를 **두 번** 돌린다
  ② 날짜·시각·경과시간·경로처럼 **당연히 변하는 것**을 지운 뒤 출력을 대조한다
  ③ 다르면 어느 줄이 달랐는지 보이고 exit 1
  ④ 어느 커밋에서 쟀는지 **함께 출력한다** (수에 커밋을 붙인다)

    python scripts/verify_measure_repro.py            # 판정
    python scripts/verify_measure_repro.py --list     # 등재된 측정 도구
    python scripts/verify_measure_repro.py --self-test

호스트에서 돈다 — 등재는 **호스트에서 도는 도구만** 받는다. 컨테이너를 요구하는 측정은
환경이 죽으면 게이트가 **초록으로** 죽는다(D-301).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 등재된 측정 도구 — **수를 보고하는 것만** 넣는다.
#: 새 측정 도구를 만들면 여기 등재한다. 등재하지 않으면 재현성이 검사되지 않는다.
MEASURES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("threshold-census", ("scripts/probe_threshold_census.py",)),
    ("homonyms",         ("scripts/verify_homonyms.py", "--list")),
    ("cache-bypass",     ("scripts/verify_cache_bypass.py", "--list")),
    ("route-ledger",     ("scripts/verify_route_inventory.py", "--list")),
    ("ga-readiness",     ("scripts/verify_ga_readiness.py", "--list")),
    ("envelope",         ("scripts/verify_envelope.py", "--list")),
)

#: 당연히 변하는 것. 지우지 않으면 게이트가 **시계를 재고** 매번 빨개진다.
VOLATILE = (
    re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?"),   # 타임스탬프
    re.compile(r"\b\d+(\.\d+)?\s*(ms|s|초)\b"),                  # 경과 시간
    re.compile(r"0x[0-9a-fA-F]+"),                               # 객체 주소
    re.compile(r"[A-Za-z]:[\\/][^\s]*"),                         # 절대 경로(윈도)
    re.compile(r"/(?:home|tmp|repo|docs|app)/[^\s]*"),           # 절대 경로(POSIX)
)


def normalize(text: str) -> str:
    for pattern in VOLATILE:
        text = pattern.sub("<volatile>", text)
    return text.replace("\r\n", "\n").strip()


#: ★ [실측 2026-09-07 · 턴 J] **재현성을 재는 일이 재는 대상을 바꾸고 있었다.**
#:   여기서 부르는 판정기 여럿이 도는 김에 `docs/agent/evidence/**` 에 제 산출을 쓴다.
#:   이 파일은 그 판정기를 **두 번씩** 부르므로, 커밋 훅으로 돌 때마다 증거 파일이
#:   흔들렸고 pre-commit 은 「files were modified by this hook」으로 커밋을 막았다.
#:   턴 J 에 그 고리에 여섯 번 걸렸다.
#:   ⚠ 더 나쁜 것은 **판정 자체가 오염된다**는 것이다: 1회차가 쓴 증거를 2회차가 읽으면
#:     「두 번 같은 수」는 재현성이 아니라 **자기가 방금 쓴 것을 다시 읽은 것**이다.
#:   → 부르기 전에 **깨끗하던 증거 파일**을 적어 두고, 부른 뒤 그중 더러워진 것만
#:     되돌린다. 이미 더러웠던 파일은 **건드리지 않는다** — 그것은 남의 작업본이다.
EVIDENCE_DIR = "docs/agent/evidence"


def _clean_evidence_files() -> set[str]:
    """지금 git 이 「깨끗하다」고 보는 증거 파일들. 되돌려도 되는 자리다."""
    ls = subprocess.run(["git", "ls-files", EVIDENCE_DIR], cwd=ROOT,
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if ls.returncode != 0:
        return set()
    tracked = {l.strip() for l in ls.stdout.splitlines() if l.strip()}
    st = subprocess.run(["git", "status", "--porcelain", "--", EVIDENCE_DIR], cwd=ROOT,
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    dirty = {l[3:].strip().strip('"') for l in st.stdout.splitlines() if l[3:].strip()}
    return tracked - dirty


def _restore(paths: set[str]) -> int:
    """그중 지금 더러운 것만 되돌린다. 되돌린 건수를 돌려준다."""
    st = subprocess.run(["git", "status", "--porcelain", "--", EVIDENCE_DIR], cwd=ROOT,
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    now_dirty = {l[3:].strip().strip('"') for l in st.stdout.splitlines() if l[3:].strip()}
    touched = sorted(paths & now_dirty)
    if not touched:
        return 0
    subprocess.run(["git", "checkout", "--", *touched], cwd=ROOT,
                   capture_output=True, text=True)
    return len(touched)


def run(argv: tuple[str, ...]) -> str:
    before = _clean_evidence_files()
    proc = subprocess.run(
        [sys.executable, *argv], cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    n = _restore(before)
    if n:
        print("[MEASURE-REPRO]   (%s 가 증거 %d개를 고쳤다 — 되돌렸다. "
              "재는 일이 대상을 바꾸면 그것은 측정이 아니다)" % (argv[-1].rsplit("/", 1)[-1], n))
    return proc.stdout + proc.stderr


def diff_lines(a: str, b: str, limit: int = 6) -> list[str]:
    """어느 줄이 달랐나. **다르다고만 말하는 게이트는 고칠 곳을 안 알려준다.**"""
    left, right = a.splitlines(), b.splitlines()
    out: list[str] = []
    for i in range(max(len(left), len(right))):
        x = left[i] if i < len(left) else "(없음)"
        y = right[i] if i < len(right) else "(없음)"
        if x != y:
            out.append("      %d회차: %s" % (1, x))
            out.append("      %d회차: %s" % (2, y))
            if len(out) >= limit * 2:
                break
    return out


def current_commit() -> str:
    """수에 커밋을 붙인다 — 어느 트리에서 잰 수인지 모르면 두 수를 비교할 수 없다."""
    try:
        proc = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True)
        head = proc.stdout.strip()
    except OSError:
        return "(git 없음)"
    if not head:
        return "(git 없음)"
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    return head + ("+작업본" if dirty else "")


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310)
# ═══════════════════════════════════════════════════════════════════════════

def self_test() -> int:
    """★ 출생 표본: **두 번 돌려 다른 수를 내는 도구**를 잡는가.

    610/127 과 614/131 이 그 모양이었다. 잡히지 않으면 이 게이트는
    「추정하는 도구」를 「세는 도구」로 통과시킨다.
    """
    checks: list[tuple[str, bool]] = []

    a = "[X] 하드코딩 임계값 610건 — 계약 면 127건"
    b = "[X] 하드코딩 임계값 614건 — 계약 면 131건"
    checks.append(("★ 출생표본 — 610/127 과 614/131 을 다르다고 본다",
                   normalize(a) != normalize(b)))
    checks.append(("★ 출생표본 — 어느 줄이 달랐는지 보여 준다",
                   len(diff_lines(a, b)) == 2))
    checks.append(("같은 출력은 같다고 본다", normalize(a) == normalize(a + "\n")))
    checks.append(("시각이 다른 것은 차이로 세지 않는다",
                   normalize("잰 때 2026-09-08 11:20") == normalize("잰 때 2026-09-08 11:21")))
    checks.append(("경과 시간은 차이로 세지 않는다",
                   normalize("0.05s 걸림") == normalize("0.07s 걸림")))
    checks.append(("경로는 차이로 세지 않는다",
                   normalize("→ /docs/a.json") == normalize("→ /repo/b.json")))
    checks.append(("★ 그러나 **수**가 다르면 반드시 잡는다",
                   normalize("건수 3") != normalize("건수 4")))
    checks.append(("등재가 비면 판정이 아니다", len(MEASURES) > 0))

    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[MEASURE-REPRO] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--only", default=None, help="이름 하나만 돌린다")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if args.list:
        print("[MEASURE-REPRO] [입력] 등재된 측정 도구 %d건" % len(MEASURES))
        for name, argv in MEASURES:
            print("  %-18s %s" % (name, " ".join(argv)))
        return 0

    targets = [m for m in MEASURES if args.only in (None, m[0])]
    if not targets:
        print("[MEASURE-REPRO] 대상 0건 — 이름이 틀렸거나 등재가 비었다 (D-301)")
        return 1

    print("[MEASURE-REPRO] [입력] 측정 도구 %d건을 **두 번씩** 돌린다 · 커밋 %s"
          % (len(targets), current_commit()))
    bad = 0
    for name, argv in targets:
        missing = [a for a in argv if a.endswith(".py") and not (ROOT / a).exists()]
        if missing:
            print("  FAIL  %-18s 등재된 도구가 없다: %s" % (name, ", ".join(missing)))
            bad += 1
            continue
        first, second = normalize(run(argv)), normalize(run(argv))
        if first == second:
            print("  OK    %-18s 두 번 같은 수" % name)
            continue
        bad += 1
        print("  FAIL  %-18s **두 번 다른 수** — 세는 도구가 아니라 추정하는 도구다" % name)
        for line in diff_lines(first, second):
            print(line)

    if bad:
        print("[MEASURE-REPRO] FAIL 재현되지 않는 측정 %d건. "
              "원인은 파일 순회 순서 · 캐시(D-341 ⑦) · 병렬 · 정규식 백트래킹 중 하나다" % bad)
        return 1
    print("[MEASURE-REPRO] 측정 %d건 전부 재현됐다" % len(targets))
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        measured=("등재된 측정 도구를 **두 번씩** 돌려 같은 수가 나오는가 — **분모 %d건**. "
               "등재하지 않은 도구는 재현성이 **검사되지 않는다** — 그 0 은 초록이 아니다"
               % len(MEASURES)),
    )
    raise SystemExit(main())
