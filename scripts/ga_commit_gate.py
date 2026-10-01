# -*- coding: utf-8 -*-
"""P-468 — 커밋 게이트는 **이 커밋이 만든 빨강만** 막는다 (턴 AS · 조율자 E · 2026-10-01).

한 문장
-------
    `verify_ga_readiness.py` 의 FAIL 을 둘로 가른다 —
      ① **이 커밋의 빨강**: 그 절의 대장 블록이 이 커밋에서 바뀌었거나, 그 절의 게이트 파일이
         이 커밋에 들었다 → **막는다**(HEAD 에 없던 FAIL · 판정기·게이트를 고치며 생긴 색).
      ② **등재된 빨강**: 이 커밋이 손대지 않은 절의 FAIL(기계가 꺼져 있던 운영 사실 등)
         → **빨강으로 적고 통과**한다. GA 목록에는 빨강 그대로 남는다.

왜 이 파일이 생겼나 — 출생 표본
-------------------------------
10-01 09:05 PC 가 켜졌다. 05:00 정시 백업이 없어 OPS-19 가 빨강이 되었고, 그 빨강이
OPS-19 와 무관한 기능명세 승격 6 절의 커밋을 막았다(턴 AR). 「어제의 운영 사실이 오늘의
정직한 커밋을 막지 않는다」(WO-22 불변).

모르면 막는다
-------------
GA 가 rc 1 인데 FAIL 줄을 하나도 못 읽으면 가를 수 없다 → 막는다. 회색(rc 2)은 지금처럼
막지 않는다(P-70).

    python scripts/ga_commit_gate.py              # 훅이 부른다
    python scripts/ga_commit_gate.py --self-test
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "docs/agent/evidence/D-346/ga_readiness.yaml"
FAIL_RE = re.compile(r"^\[GA\] FAIL ([A-Za-z0-9][A-Za-z0-9_.-]*)\s*:", re.M)
ID_RE = re.compile(r"^(\s*)- id: (\S+)\s*$", re.M)
GATE_RE = re.compile(r"^\s+gate: (\S+)\s*$", re.M)


def fail_ids(ga_output: str) -> list:
    return sorted(set(FAIL_RE.findall(ga_output)))


def blocks(yaml_text: str) -> dict:
    """대장의 `- id:` 블록을 id → 글자로. 다음 같은-또는-얕은 들여쓰기 `- id:` 까지가 한 블록."""
    out = {}
    marks = list(ID_RE.finditer(yaml_text or ""))
    for i, m in enumerate(marks):
        end = len(yaml_text)
        for n in marks[i + 1:]:
            if len(n.group(1)) <= len(m.group(1)):
                end = n.start()
                break
        out[m.group(2)] = yaml_text[m.start():end]
    return out


def gate_of(block: str) -> str | None:
    m = GATE_RE.search(block or "")
    return m.group(1) if m else None


def classify(fails, head_yaml, staged_yaml, staged_files):
    """→ (이 커밋의 빨강, 등재된 빨강). 각 원소는 (id, 까닭)."""
    hb, sb = blocks(head_yaml), blocks(staged_yaml)
    staged = set(staged_files)
    mine, listed = [], []
    for fid in fails:
        if hb.get(fid) != sb.get(fid):
            mine.append((fid, "이 커밋이 대장 블록을 바꿨다"))
            continue
        g = gate_of(sb.get(fid) or hb.get(fid))
        if g and g in staged:
            mine.append((fid, f"이 커밋이 게이트 {g} 를 고쳤다"))
            continue
        listed.append((fid, "이 커밋이 손대지 않았다 — 등재된 빨강"))
    return mine, listed


def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8").stdout


def main() -> int:
    #: Windows 콘솔(cp949)은 GA 출력의 글자(↳ 등)를 못 쓴다 — 훅 안에서 죽으면 「모르면 막는다」가
    #: 아니라 「아무것도 못 말하고 막는다」가 된다. 자식과 자기 출력을 UTF-8 로 맞춘다.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    proc = subprocess.run([sys.executable, "scripts/verify_ga_readiness.py"], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 1:
        if proc.returncode != 0:
            print(f"[GA-COMMIT] 위는 회색(exit {proc.returncode})이다 — 막지 않는다(P-70). 초록이라는 뜻이 아니다.")
        return 0
    fails = fail_ids(proc.stdout)
    if not fails:
        print("[GA-COMMIT] GA 가 빨강인데 FAIL 줄을 못 읽었다 — 가를 수 없으니 막는다")
        return 1
    staged = [ln for ln in _git("diff", "--cached", "--name-only").splitlines() if ln]
    mine, listed = classify(fails, _git("show", f"HEAD:{LEDGER}"), _git("show", f":{LEDGER}"), staged)
    print(f"[GA-COMMIT] [입력] FAIL {len(fails)} · 이 커밋의 빨강 {len(mine)} · 등재된 빨강 {len(listed)} · 담긴 파일 {len(staged)}")
    for fid, why in listed:
        print(f"[GA-COMMIT] 빨강(등재) {fid} — {why} · GA 목록에 빨강 그대로 남는다")
    for fid, why in mine:
        print(f"[GA-COMMIT] 막음 {fid} — {why}")
    return 1 if mine else 0


def self_test() -> int:
    head = ("  - id: OPS-19\n    status: 구현\n    gate: scripts/verify_backup_autonomy.py\n"
            "  - id: FWS-F1-12\n    status: 미착수\n")
    staged_promote = head.replace("  - id: FWS-F1-12\n    status: 미착수\n",
                                  "  - id: FWS-F1-12\n    status: 구현\n")
    cases = []
    # 출생 표본 — 10-01: OPS-19 빨강 · 승격만 담은 커밋 → 통과
    m, l = classify(["OPS-19"], head, staged_promote, [LEDGER])
    cases.append(("출생 표본: OPS-19 빨강 + 무관한 승격 → 등재 · 통과", not m and len(l) == 1))
    # 이 커밋이 그 절의 블록을 바꿨다 → 막음
    flip = head.replace("    status: 구현\n    gate:", "    status: 구현됨\n    gate:")
    m, l = classify(["OPS-19"], head, flip, [LEDGER])
    cases.append(("그 절의 대장 블록을 바꾼 커밋 → 막음", len(m) == 1))
    # 이 커밋이 그 절의 게이트를 고쳤다 → 막음
    m, l = classify(["OPS-19"], head, head, ["scripts/verify_backup_autonomy.py"])
    cases.append(("그 절의 게이트를 고친 커밋 → 막음", len(m) == 1))
    # HEAD 에 없던 절이 새로 FAIL → 블록이 새로 생겼으니 막음
    newer = head + "  - id: NEW-01\n    status: 구현\n"
    m, l = classify(["NEW-01"], head, newer, [LEDGER])
    cases.append(("HEAD 에 없던 절의 FAIL → 막음", len(m) == 1))
    cases.append(("FAIL 줄 읽기", fail_ids("[GA] FAIL OPS-19: 대장은 …\n[GA] FAIL OPS-26: x") == ["OPS-19", "OPS-26"]))
    bad = sum(0 if ok else 1 for _, ok in cases)
    for label, ok in cases:
        print("  [%s] %s" % ("통과" if ok else "**실패**", label))
    print("[GA-COMMIT] 자기시험 %d건 중 %d건 실패" % (len(cases), bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
