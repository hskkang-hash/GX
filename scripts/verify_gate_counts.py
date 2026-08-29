#!/usr/bin/env python
"""D-301 을 **도구로** 강제한다 — 「검사 못함 ≠ 0건 검사」.

    게이트는 "0건 검사했음"과 "검사하지 못했음"을 구분해야 한다.
    건수 출력이 없는 게이트는 게이트로 인정하지 않는다.

왜 이 스크립트가 따로 필요한가 — 러너의 판정은 **돌 때만** 산다
---------------------------------------------------------------
`verify_gates.sh` 의 `run_gate` 가 이미 실행 시점에 판정한다: 게이트 출력에 `[입력]`
표시가 없으면 그 게이트를 실패시킨다. 그것으로 충분해 보이지만 아니다 —

  · 러너를 **부르지 않으면** 그 판정은 일어나지 않는다. 새 게이트를 추가하고
    자기 게이트만 `--gate` 로 돌려 본 사람은 그 판정을 지나칠 수 있다.
  · 러너 자신이 고쳐질 수 있다. `run_gate` 에서 그 세 줄을 지우면 규칙이 사라지는데,
    **사라진 것을 아무도 못 본다.** 이 저장소가 반복해 만난 실패 모양이다
    (WP-0 EXIT §6-1 `tickets.sha256` · `verify_e2e_contract.py` 가 같은 이유로 있다).

그래서 저장소 밖에서 한 번 더 잠근다. Django 도 bash 도 필요 없다 — 파일을 읽는다.

    python scripts/verify_gate_counts.py            # 판정 (어긋나면 exit 1)
    python scripts/verify_gate_counts.py --list     # 게이트별 건수 출력 지점
    python scripts/verify_gate_counts.py --self-test  # 양성·음성 대조 (D-277 · D-289)

무엇을 보는가 — 넷이다
----------------------
  ① `ALL_GATES` 의 이름마다 `gate_<이름>` 함수가 실재하는가.
     (이름만 등재하고 함수가 없으면 러너가 `exit 2` 로 죽는다 — 게이트 목록이
      곧 거짓말이 된다.)
  ② 각 게이트 함수 본문이 `inputs ` 를 **최소 1회** 부르는가.
  ③ `inputs` 헬퍼 자신이 살아 있는가 — 0건일 때 사유를 요구하고 실패시키는가.
  ④ 러너의 `[입력]` 표시 판정(`GATE_INPUTS_MARK` 대조)이 `run_gate` 에 남아 있는가.

★ 자기시험 의무 (D-277 · D-300)
--------------------------------
이 판정기 역시 "전부 통과" 를 **아무것도 안 보고** 말할 수 있다. 그래서 `--self-test`
가 (가) 건수를 안 내는 가짜 게이트를 심어 잡히는지, (나) 제대로 내는 게이트는 안 잡는지
둘 다 본다. `main()` 은 대상이 0건이면 판정이 아니라 **열거기 고장**으로 보고 exit 1 한다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATES = ROOT / "docs" / "agent" / "verify_gates.sh"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 건수를 내는 호출. 헬퍼 이름을 바꾸면 여기도 같은 커밋에서 고친다 — 갈리면 멈춘다.
CALL = re.compile(r"^\s*inputs\s", re.M)

#: 게이트 함수 선언. `gate_secrets() {` 형태만 게이트로 본다.
DECL = re.compile(r"^gate_([a-z0-9_]+)\(\)\s*\{", re.M)


def gate_bodies(src: str) -> dict[str, str]:
    """`gate_*` 함수 이름 → 본문. 다음 최상위 선언 전까지를 본문으로 본다.

    중괄호를 세지 않는다 — 이 파일은 최상위 함수만 쓰고, 여는 중괄호가 줄 첫 칸에
    오는 자리는 함수 선언뿐이다. 중괄호 계수기는 heredoc 안의 `{` 에 속는다.
    """
    starts = [(m.group(1), m.start()) for m in DECL.finditer(src)]
    # 최상위 경계: 다음 게이트 선언, 또는 줄 첫 칸에서 시작하는 다른 최상위 선언
    tops = [m.start() for m in re.finditer(r"^\w[\w./-]*\(\)\s*\{", src, re.M)]
    out: dict[str, str] = {}
    for name, pos in starts:
        after = [t for t in tops if t > pos]
        end = min(after) if after else len(src)
        out[name] = src[pos:end]
    return out


def declared_gates(src: str) -> list[str]:
    """`ALL_GATES=(...)` 에 등재된 이름. 러너가 실제로 도는 목록이 이것이다."""
    m = re.search(r"^ALL_GATES=\((.*?)\)", src, re.M | re.S)
    return m.group(1).split() if m else []


def check(src: str) -> tuple[list[str], list[tuple[str, int]]]:
    """(문제 목록, [(게이트, inputs 호출 수)])."""
    problems: list[str] = []
    bodies = gate_bodies(src)
    rows: list[tuple[str, int]] = []

    # ① 등재된 이름마다 함수가 있는가 — `--gate` 이름과 `gate_` 이름은 하이픈/밑줄이 다르다
    for name in declared_gates(src):
        fn = name.replace("-", "_")
        if fn not in bodies:
            problems.append(
                f"ALL_GATES 에 '{name}' 이 있는데 gate_{fn}() 함수가 없다 — "
                f"러너는 이 이름에서 exit 2 로 죽는다. 목록이 곧 거짓말이다")

    # ② 게이트마다 건수를 내는가
    for name, body in sorted(bodies.items()):
        n = len(CALL.findall(body))
        rows.append((name, n))
        if n == 0:
            problems.append(
                f"gate_{name}() 이 입력 건수를 내지 않는다 ← D-301. "
                f"`inputs <건수> <무엇을> [0건 사유]` 를 판정 **전에** 부른다 — "
                f"무엇을 보고 한 말인지 모르는 초록은 초록이 아니다")

    # ③ 헬퍼가 살아 있는가 — 0건에 사유가 없으면 실패시키는가
    helper = re.search(r"^inputs\(\)\s*\{(.*?)^\}", src, re.M | re.S)
    if not helper:
        problems.append("inputs() 헬퍼가 사라졌다 — 건수 규약의 구현체가 없다")
    else:
        h = helper.group(1)
        if "fail" not in h or "-eq 0" not in h:
            problems.append(
                "inputs() 가 0건+무사유를 실패시키지 않는다 — 그러면 0건이 "
                "'볼 것이 없었다'인지 '보지 못했다'인지 영영 구별되지 않는다 (D-301)")

    # ④ 러너의 판정이 남아 있는가
    runner = re.search(r"^run_gate\(\)\s*\{(.*?)^\}", src, re.M | re.S)
    if not runner:
        problems.append("run_gate() 가 없다 — 실행 시점 판정이 사라졌다")
    elif "GATE_INPUTS_MARK" not in runner.group(1):
        problems.append(
            "run_gate() 가 [입력] 표시를 대조하지 않는다 — 건수 규약의 실행 시점 "
            "판정이 지워졌다. 지워진 게이트는 지워진 것이 보이지 않는다")

    return problems, rows


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — 심은 위반을 잡는가, 멀쩡한 것은 안 잡는가 (D-277 · D-289)
# ═══════════════════════════════════════════════════════════════════════════
_GOOD = """\
GATE_INPUTS_MARK='[입력]'
inputs() {
  local n="$1"
  if [ "$n" -eq 0 ]; then fail "사유 없음"; return 1; fi
}
gate_alpha() {
  inputs 3 "무엇인가"
  pass "ok"
}
run_gate() {
  grep -qF "$GATE_INPUTS_MARK" "$log" || fail "건수 없음"
}
ALL_GATES=(alpha)
"""

_BAD_NO_COUNT = _GOOD.replace('  inputs 3 "무엇인가"\n', "")
_BAD_NO_RUNNER = _GOOD.replace('  grep -qF "$GATE_INPUTS_MARK" "$log" || fail "건수 없음"\n',
                               '  true\n')
_BAD_MISSING_FN = _GOOD.replace("ALL_GATES=(alpha)", "ALL_GATES=(alpha beta)")


def self_test() -> int:
    cases = (
        ("건수를 내는 게이트는 안 잡는다", _GOOD, False),
        ("건수를 안 내는 게이트를 잡는다", _BAD_NO_COUNT, True),
        ("러너의 [입력] 대조가 지워진 것을 잡는다", _BAD_NO_RUNNER, True),
        ("등재만 되고 함수가 없는 게이트를 잡는다", _BAD_MISSING_FN, True),
    )
    bad = 0
    for label, src, should_fail in cases:
        problems, _ = check(src)
        caught = bool(problems)
        ok = caught == should_fail
        print(f"  {'OK  ' if ok else 'FAIL'} {label}"
              + (f"  ← {problems[0][:60]}" if caught and ok and should_fail else ""))
        if not ok:
            bad += 1
    if bad:
        print(f"[GATECOUNT] 자기시험 {bad}건 실패 — 이 판정기는 눈이 멀었다")
        return 1
    print(f"[GATECOUNT] 자기시험 {len(cases)}건 통과 (양성 3 · 음성 1)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not GATES.is_file():
        print(f"[GATECOUNT] 게이트 러너가 없다: {GATES} — 판정할 수 없으므로 멈춘다")
        return 1

    # 판정 전에 판정기부터 시험한다 (D-277). 여기서 죽으면 아래 초록은 뜻이 없다.
    if self_test() != 0:
        return 1

    src = GATES.read_text(encoding="utf-8")
    problems, rows = check(src)

    # ★ 대상 0건은 통과가 아니라 **열거기 고장**이다 (D-271 ② · D-301).
    if not rows:
        print("[GATECOUNT] 게이트 함수를 한 건도 못 찾았다 — 정규식이 눈이 멀었거나 "
              "러너가 통째로 바뀌었다. 0건을 통과로 읽지 않는다")
        return 1

    if args.list:
        for name, n in rows:
            print(f"  gate_{name:20} inputs 호출 {n}회")

    total = sum(n for _, n in rows)
    print(f"[GATECOUNT] 게이트 {len(rows)}종 · 건수 출력 지점 {total}곳 "
          f"(등재 {len(declared_gates(src))}종)")

    if problems:
        print("[GATECOUNT] D-301 위반 — 건수 출력이 없는 게이트는 게이트가 아니다")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[GATECOUNT] 전 게이트가 자기가 무엇을 몇 건 보았는지 말한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
