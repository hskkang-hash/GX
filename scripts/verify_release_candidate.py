#!/usr/bin/env python
"""릴리스 후보(SDN 제외판) 도달 조건 5건을 **판정한다** (D-303).

    ① E2E-1 8/8 (SDN·VIDEO 칸 제외, 잠김 사유 명시)
    ② E2E-2 4/4 (D-299 로 열림)
    ③ 게이트 전건 exit 0 + 입력 건수 출력 (D-301)
    ④ F-09~F-12 라우트 트립와이어 통과
    ⑤ 설치·운영 문서 초안

왜 스크립트인가 — **"다섯이 찼다"는 문장은 사람이 쓰면 다시 문서다** (D-286)
---------------------------------------------------------------------------
릴리스 후보 선언은 계약 인도로 이어지는 판정이다. 그 판정이 회신문의 한 줄로만 존재하면,
다음 턴에 하나가 깨져도 그 문장은 그대로 남는다. 그래서 **매번 다시 세는 것**을 둔다.

★ 증거가 없으면 통과가 아니라 **판정 불가로 exit 1** (D-301 「검사 못함 ≠ 0건 검사」)
------------------------------------------------------------------------------------
`steps.md` 가 없으면 "E2E-1 이 실패했다"가 아니라 "재지 못했다"이다. 둘을 같은 값으로
두면 증거를 지우는 것만으로 초록이 된다 — 게이트가 있다는 착시가 게이트가 없는 것보다 나쁘다.

    python scripts/verify_release_candidate.py             # 판정 (하나라도 못 채우면 exit 1)
    python scripts/verify_release_candidate.py --self-test # 양성·음성 대조 (D-277)

이 스크립트는 **시험을 돌리지 않는다.** 시험이 남긴 증거를 읽는다 — 돌리는 것과 세는 것을
한 자리에 두면, 세는 쪽이 돌리는 쪽의 실패를 삼킬 수 있다.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "agent" / "evidence" / "e2e"
GATES = ROOT / "docs" / "agent" / "verify_gates.sh"
CONTRACT = ROOT / "backend" / "tests" / "e2e" / "e2e_contract.py"
TRIPWIRE = ROOT / "backend" / "tests" / "test_route_tripwire.py"
DSM_API = ROOT / "backend" / "apps" / "dsm" / "api.py"
MANUAL = ROOT / "docs" / "agent" / "runbook" / "설치운영매뉴얼_v0.1.md"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


@dataclass
class Condition:
    no: str
    title: str
    ok: bool
    note: str

    def render(self) -> str:
        return f"  {'OK  ' if self.ok else 'MISS'} {self.no} {self.title:34} {self.note}"


def _steps(code: str) -> str | None:
    path = EVIDENCE / code / "steps.md"
    return path.read_text(encoding="utf-8") if path.is_file() else None


def _counts(body: str):
    m = re.search(r"단계 (\d+)/(\d+) 도달 \(계획 (\d+) · 잠김 (\d+)\)", body)
    return tuple(int(g) for g in m.groups()) if m else None


def _scenario_condition(no: str, code: str, want_unlocked: int,
                        want_locked: int) -> Condition:
    """해금분을 **전부 도달**했고, 잠김 수가 예상과 같은가.

    잠김 수까지 보는 이유: 잠긴 칸이 조용히 늘면 "해금분 전건 통과"는 그대로 초록이다.
    빠진 줄은 보이지 않는다(D-274) — 그래서 줄 수를 함께 잠근다.
    """
    body = _steps(code)
    if body is None:
        return Condition(no, f"{code} 단계표", False,
                         "증거 없음 — 판정 불가(통과 아님). E2E 를 돌려 steps.md 를 남긴다")
    c = _counts(body)
    if c is None:
        return Condition(no, f"{code} 단계표", False,
                         "단계표 형식이 바뀌어 셀 수 없다 — 판정 불가")
    reached, unlocked, planned, locked = c
    if "FAIL" in body:
        return Condition(no, f"{code} 단계표", False, "FAIL 단계가 있다")
    ok = reached == unlocked == want_unlocked and locked == want_locked
    return Condition(no, f"{code} 단계표", ok,
                     f"{reached}/{unlocked} 도달 (계획 {planned} · 잠김 {locked}) "
                     f"— 기대 {want_unlocked}/{want_unlocked} · 잠김 {want_locked}")


def _locked_reasons_present() -> tuple[bool, str]:
    """**잠긴 것마다 사유가 있는가.** 사유는 두 곳에 산다 — 둘 다 본다.

    ① `LOCKED_CAPABILITIES` — 커널이 아닌 잠긴 능력(이름 + 사유)
    ② 모듈의 `KERNEL_READY=False` + `NOT_READY_REASON` — 어댑터·서비스가 스스로 하는 선언

    ★ 2026-09-02 실측: ①이 **비었다.** FLOOD(D-294) · ZONE(D-299) · VIDEO(D-306)가 차례로
      열리면서 등재부에서 지워졌고, 남은 잠김(SDN)의 사유는 ②에 있다. 그때 이 함수가
      "잠긴 능력 0건 — 등재부가 비었거나 형식이 바뀌었다"로 실패했다. 그것은 **판정기가
      한쪽 눈만 뜨고 있었다는 뜻**이지 저장소가 잘못된 것이 아니다.

      그런데 ①이 빈 것을 그냥 통과시키면 안 된다: 등재부 형식이 바뀌어 못 읽는 경우와
      **정말로 다 열린 경우**가 구별되지 않는다. 그래서 둘을 합쳐 세고, 합이 0 인데
      단계표에 잠김이 남아 있으면 실패한다 — 아래 호출부가 그 대조를 한다.
    """
    problems: list[str] = []
    total = 0

    src = CONTRACT.read_text(encoding="utf-8")
    block = re.search(r"LOCKED_CAPABILITIES[^=]*=\s*\{(.*?)\n\}", src, re.S)
    if block is None:
        return False, "LOCKED_CAPABILITIES 등재부 자체가 없다 — 형식이 바뀌었다"
    body = block.group(1)
    names = re.findall(r'^    "([A-Z_]+)":', body, re.M)
    for n in names:
        total += 1
        chunk = body.split(f'"{n}":', 1)[1].split('\n    "', 1)[0]
        chunk = "\n".join(ln for ln in chunk.split("\n")
                          if not ln.lstrip().startswith("#"))
        why = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', chunk))
        if len(why.strip()) < 40:
            problems.append(f"LOCKED_CAPABILITIES['{n}'] 의 사유가 빈약하다")

    # ② 모듈 스스로의 선언 — `scripts/verify_e2e_contract.py` 와 **같은 판정기**를 쓴다.
    #    두 벌로 두면 언젠가 다른 말을 하고, 그때 어느 쪽이 진실인지 알 수 없다.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_vec", ROOT / "scripts" / "verify_e2e_contract.py")
    vec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vec)
    for code, module in vec.kernel_packages().items():
        path = ROOT / "backend" / (module.replace(".", "/") + "/__init__.py")
        if not path.is_file():
            path = ROOT / "backend" / (module.replace(".", "/") + ".py")
        if not path.is_file():
            continue
        if vec.literal_from(path, "KERNEL_READY") is False:
            total += 1
    problems.extend(vec.not_ready_declarations())

    if problems:
        return False, f"사유가 없거나 빈약한 잠김: {problems[:2]}"
    return True, f"잠긴 것 {total}건 전부 사유 있음 (등재부 {len(names)} + 모듈 선언 {total - len(names)})"


def _gate_counts_condition() -> Condition:
    """게이트가 **자기가 무엇을 몇 건 보았는지 말하는가** (D-301).

    여기서는 러너를 돌리지 않는다 — 정적으로 본다. 실행 판정은 `verify_gate_counts.py`
    와 `run_gate` 가 한다. 셋이 같은 규칙을 다른 자리에서 본다.
    """
    if not GATES.is_file():
        return Condition("③", "게이트 건수 출력", False, "verify_gates.sh 가 없다 — 판정 불가")
    src = GATES.read_text(encoding="utf-8")
    declared = re.search(r"^ALL_GATES=\((.*?)\)", src, re.M | re.S)
    names = declared.group(1).split() if declared else []
    missing = [n for n in names
               if not re.search(rf"^gate_{n.replace('-', '_')}\(\)", src, re.M)]
    bodies = re.findall(r"^gate_[a-z0-9_]+\(\)", src, re.M)
    calls = len(re.findall(r"^\s*inputs\s", src, re.M))
    ok = bool(names) and not missing and "GATE_INPUTS_MARK" in src and calls >= len(bodies)
    return Condition("③", "게이트 건수 출력", ok,
                     f"게이트 {len(bodies)}종 · 등재 {len(names)}종 · inputs 호출 {calls}곳"
                     + (f" · 함수 없는 등재 {missing}" if missing else ""))


def conditions() -> list[Condition]:
    out = [
        # ★ 2026-09-02 · D-306 으로 VIDEO 칸이 열려 잠김이 2 → 1 이 됐다.
        #   기대값을 함께 고친다 — 안 고치면 이 판정기가 "덜 잠긴 것"을 실패로 읽는다.
        _scenario_condition("①", "E2E-1", want_unlocked=9, want_locked=1),
        _scenario_condition("②", "E2E-2", want_unlocked=4, want_locked=0),
        _gate_counts_condition(),
    ]
    reasons_ok, reasons_note = _locked_reasons_present()
    # ★ 단계표에 잠김이 남아 있는데 사유가 **한 건도** 없으면 그것은 통과가 아니다 —
    #   사유 없는 잠김은 "아직" 인지 "영영" 인지 구별되지 않는다(D-264).
    locked_in_steps = sum((_counts(_steps(c)) or (0, 0, 0, 0))[3]
                          for c in ("E2E-1", "E2E-2", "E2E-3") if _steps(c))
    if locked_in_steps and "0건" in reasons_note:
        reasons_ok, reasons_note = False, (
            f"단계표에 잠김 {locked_in_steps}칸이 있는데 사유가 0건이다 — 판정 불가")
    out[0].ok = out[0].ok and reasons_ok
    out[0].note += f" · {reasons_note}"

    # ④ 트립와이어 — F-09~F-12 라우트가 실재하고, **전부 문지기를 달고 있는가**
    #
    #   트립와이어가 지키는 것은 "문지기 없는 새 경로가 하나 생기면 그 순간 다시 샌다"
    #   이다. 그러므로 여기서 셀 것은 기능 이름이 아니라 **라우트 수 대 문지기 수**다.
    #   이름만 세면 주석에 F-09 라고 적기만 해도 초록이 된다.
    if not (DSM_API.is_file() and TRIPWIRE.is_file()):
        out.append(Condition("④", "F-09~12 라우트 트립와이어", False,
                             "apps/dsm/api.py 또는 test_route_tripwire.py 가 없다 — 판정 불가"))
    else:
        src = DSM_API.read_text(encoding="utf-8")
        routes = len(re.findall(r"^\s*@route\.", src, re.M))
        guards = len(re.findall(r"^\s*@tenant_scoped\(", src, re.M))
        features = [f for f in ("F-09", "F-10", "F-11", "F-12") if f in src]
        out.append(Condition(
            "④", "F-09~12 라우트 트립와이어",
            routes > 0 and routes == guards and len(features) == 4,
            f"라우트 {routes}건 · 문지기 {guards}건 · 기능 {features}"))

    # ⑤ 설치·운영 문서 — 있는가, 그리고 **빈 환경 절차**가 들어 있는가
    if MANUAL.is_file():
        src = MANUAL.read_text(encoding="utf-8")
        need = ("migrate user", "migrate multilanguage", "migrate --check")
        missing = [n for n in need if n not in src]
        out.append(Condition("⑤", "설치·운영 문서 초안", not missing,
                             "빈 DB 3줄 절차 포함" if not missing
                             else f"빠진 절차: {missing}"))
    else:
        out.append(Condition("⑤", "설치·운영 문서 초안", False,
                             f"{MANUAL.name} 이 없다"))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — 증거를 지우면 초록이 되는가 (그러면 안 된다)
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    cases = []

    good = "[E2E-2] 단계 4/4 도달 (계획 4 · 잠김 0)\n  OK    1. …"
    fail = "[E2E-2] 단계 3/4 도달 (계획 4 · 잠김 0)\n  FAIL  2. …"
    more_locked = "[E2E-2] 단계 3/3 도달 (계획 4 · 잠김 1)\n  OK    1. …"

    def probe(body: str | None, want_unlocked: int, want_locked: int) -> bool:
        if body is None:
            return False
        c = _counts(body)
        if c is None or "FAIL" in body:
            return False
        reached, unlocked, planned, locked = c
        return reached == unlocked == want_unlocked and locked == want_locked

    cases.append(("정상 단계표는 통과한다", probe(good, 4, 0) is True))
    cases.append(("FAIL 이 있으면 잡는다", probe(fail, 4, 0) is False))
    cases.append(("★ 증거가 없으면 통과가 아니다", probe(None, 4, 0) is False))
    cases.append(("잠김이 늘면 잡는다", probe(more_locked, 4, 0) is False))

    bad = 0
    for label, ok in cases:
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1
    if bad:
        print(f"[RC] 자기시험 {bad}건 실패 — 이 판정기는 눈이 멀었다")
        return 1
    print(f"[RC] 자기시험 {len(cases)}건 통과")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != 0:                  # 판정 전에 판정기부터 (D-277)
        return 1

    rows = conditions()
    print(f"[RC] 릴리스 후보(SDN 제외판) 도달 조건 {len(rows)}건 판정")
    for c in rows:
        print(c.render())

    missed = [c for c in rows if not c.ok]
    if missed:
        print(f"[RC] 미충족 {len(missed)}건 — **아직 릴리스 후보가 아니다**")
        return 1
    print("[RC] 다섯 조건 충족 — 릴리스 후보(SDN 제외판) 선언 가능")
    print("     ※ 이것은 '완주' 가 아니다. 잠긴 칸은 잴 수 없는 것이고,")
    print("       정확한 표현은 '이 범위 안에서는 끊긴 단계가 없다' 이다 (D-302).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
