#!/usr/bin/env python
"""커밋 내력을 **도구에 건다** — D-305.

    · 커밋 본문의 D-번호가 결정 레지스트리에 없으면 exit 1 (오타·유령 번호 차단)
    · 결정문을 고친 커밋에 D-번호가 하나도 없으면 exit 1

왜 필요한가 — **내력은 사람의 성실성에 맡길 것이 아니다**
---------------------------------------------------------
결정 번호를 커밋에 적는 규약은 지켜지는 동안에만 값이 있다. 한 번 빠지면 그 커밋은
"왜 이렇게 했나"를 영영 잃고, 잃었다는 사실조차 안 남는다. 그리고 유령 번호(D-1299 같은
오타)는 더 나쁘다 — 있는 것처럼 보이는데 열면 없다.

    python scripts/verify_commit_trace.py            # 판정
    python scripts/verify_commit_trace.py --list     # 커밋별 결정 번호
    python scripts/verify_commit_trace.py --self-test

★ 소급하지 않는다 (verify_decision_tools.py 와 같은 이유)
---------------------------------------------------------
D-305 이전 커밋에 지금 번호를 달면 그것은 **사후 정당화**다. 없던 내력을 있다고 적게 되고,
그것이 이 저장소가 반복해 만난 실패 모양이다(D-249 부착률 착시).
경계는 아래 `FIRST_TRACED` 하나이고, 그 커밋부터 규칙이 산다.

★ 검사 건수를 낸다 (D-301)
--------------------------
대상 커밋이 0건이면 통과가 아니라 **판정 불가**다. git 이 없거나 얕은 클론이면
"위반 0건"은 아무것도 안 본 결과이고, 그 초록은 게이트가 없는 것보다 나쁘다.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECISIONS = ROOT / "docs" / "agent" / "decisions.yaml"

#: 규칙이 사는 경계 — D-305 를 받은 첫 커밋. 이 커밋과 그 이후만 판정한다.
#: 값은 **커밋 제목**이다. 해시는 리베이스로 바뀌지만 제목은 사람이 읽고 고칠 수 있다.
FIRST_TRACED_SUBJECT = "feat(sdn,dsm,k6): 연계 표준 · F-09~12 App · 판정 칸 분리 · 부작위 시험"

#: 본문에서 결정 번호를 찾는 모양. 제목이 아니라 **본문**에서 찾는다(D-305 규약).
D_NUMBER = re.compile(r"\bD-(\d{3})\b")

#: 이 파일이 바뀌면 커밋에 결정 번호가 있어야 한다.
DECISION_FILES = ("docs/agent/decisions.yaml",)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def known_decisions() -> set[str]:
    """레지스트리에 실재하는 번호. yaml 파서 없이 읽는다 — 어디서든 돌아야 한다."""
    if not DECISIONS.is_file():
        return set()
    return set(re.findall(r"^- id: (D-\d{3})\s*$",
                          DECISIONS.read_text(encoding="utf-8"), re.M))


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout


def commits() -> list[tuple[str, str, str, list[str]]]:
    """[(해시, 제목, 본문, 바뀐 파일)] — 경계 커밋부터 HEAD 까지, 오래된 것부터.

    ★ 레코드 구분자를 **앞에** 둔다(`%x1e` 를 형식 맨 앞). 뒤에 두면 마지막 필드인
      본문과 그 뒤의 파일 목록이 한 덩어리로 붙어 필드 수가 흔들린다 — 첫 판이
      그래서 해시 자리에 파일 이름이 들어왔다. 구분자가 앞이면 레코드 경계가 명확하다.
    """
    raw = _git("log", "--reverse", "--format=%x1e%H%x1f%s%x1f%b%x1f", "--name-only")
    out: list[tuple[str, str, str, list[str]]] = []
    started = False
    for record in raw.split("\x1e"):
        if not record.strip():
            continue
        parts = record.split("\x1f")
        if len(parts) < 4:
            continue
        sha, subject, body, files_blob = parts[0], parts[1], parts[2], parts[3]
        files = [ln.strip() for ln in files_blob.split("\n") if ln.strip()]
        if not started:
            if subject.strip() != FIRST_TRACED_SUBJECT:
                continue
            started = True
        out.append((sha.strip()[:7], subject.strip(), body, files))
    return out


def check(rows, known: set[str]) -> list[str]:
    problems: list[str] = []
    for sha, subject, body, files in rows:
        numbers = {f"D-{n}" for n in D_NUMBER.findall(body)}
        ghosts = sorted(n for n in numbers if n not in known)
        if ghosts:
            problems.append(
                f"{sha} {subject[:40]} — 레지스트리에 없는 결정 번호 {ghosts}. "
                f"오타이거나 유령 번호다: 있는 것처럼 보이는데 열면 없다")
        touched = [f for f in files if f in DECISION_FILES]
        if touched and not numbers:
            problems.append(
                f"{sha} {subject[:40]} — 결정문을 고쳤는데({touched}) 본문에 결정 번호가 "
                f"하나도 없다. 무엇을 정했는지 커밋에서 못 읽는다 (D-305)")
    return problems


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-277 · D-289)
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    known = {"D-299", "D-305"}
    cases = (
        ("정상 커밋은 안 잡는다",
         [("aaa", "feat: x", "D-299 D-305", ["backend/x.py"])], False),
        ("★ 유령 번호를 잡는다",
         [("bbb", "feat: y", "D-999", ["backend/x.py"])], True),
        ("★ 결정문을 고쳤는데 번호가 없으면 잡는다",
         [("ccc", "docs: z", "본문에 번호 없음", ["docs/agent/decisions.yaml"])], True),
        ("결정문을 안 고친 커밋은 번호가 없어도 된다",
         [("ddd", "chore: w", "정리", ["backend/x.py"])], False),
    )
    bad = 0
    for label, rows, should_fail in cases:
        got = bool(check(rows, known))
        ok = got == should_fail
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1
    if bad:
        print(f"[TRACE] 자기시험 {bad}건 실패 — 이 판정기는 눈이 멀었다")
        return 1
    print(f"[TRACE] 자기시험 {len(cases)}건 통과 (양성 2 · 음성 2)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != 0:                   # 판정 전에 판정기부터 (D-277)
        return 1

    known = known_decisions()
    if not known:
        print(f"[TRACE] 결정 레지스트리를 못 읽었다: {DECISIONS} — 유령 번호를 "
              f"가릴 수 없으므로 멈춘다 (D-301)")
        return 1

    rows = commits()
    print(f"[TRACE] 검사 {len(rows)}건 (대상=경계 커밋 이후 전수 · "
          f"레지스트리 {len(known)}건 · 술어=본문의 D-번호)")
    # ★ 0건은 통과가 아니다 — 경계 커밋을 못 찾았거나 얕은 클론이다 (D-301).
    if not rows:
        print(f"[TRACE] 대상 커밋 0건 — 경계 커밋('{FIRST_TRACED_SUBJECT[:30]}…')을 "
              f"찾지 못했다. 판정 불가이지 통과가 아니다")
        return 1

    if args.list:
        for sha, subject, body, _ in rows:
            nums = sorted({f"D-{n}" for n in D_NUMBER.findall(body)})
            print(f"  {sha}  {subject[:52]:54} {nums or '—'}")

    problems = check(rows, known)
    if problems:
        print("[TRACE] 위반 — 내력이 끊겼다")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[TRACE] 통과 — 모든 커밋의 결정 번호가 레지스트리에 실재한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
