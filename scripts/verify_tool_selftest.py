#!/usr/bin/env python
"""D-310 — **도구는 자기가 태어난 표본을 시험에 넣는다.**

    죽은 필드 판정기가 자기가 태어난 이유(clip_path)를 "살아 있다"고 답했다.
    착시 ⑥을 잡으려는 도구가 착시 ⑥의 표본을 못 본 것이다.

왜 무서운가
-----------
도구는 만들어진 순간 **"이제 이 착시는 잡힌다"는 안심**을 준다. 그리고 그 안심은
도구가 실제로 그 표본을 잡는지와 **무관하게** 생긴다. 안심만 남고 검사는 없는 상태 —
D-301(검사 못함 ≠ 0건 검사)의 형제이고, 이 저장소가 계속 만나는 같은 얼굴이다.

그래서 게이트·검증기를 만들 때 **그 도구를 만들게 한 바로 그 사례**를 fixture 로 박는다.
그 표본에서 초록이 나오면 도구가 아니다.

    python scripts/verify_tool_selftest.py           # 판정
    python scripts/verify_tool_selftest.py --list    # 도구별 보유 현황
    python scripts/verify_tool_selftest.py --self-test

무엇을 보는가 — 둘
------------------
  ① **자기시험이 있는가**  `--self-test` 또는 `def self_test` (셸 게이트는 「탐지기 자기시험」)
  ② **출생 표본이 있는가**  아래 `BIRTH_MARKERS` 중 하나가 소스에 있는가

  ★ ②는 ①보다 강한 요구다. 자기시험이 있어도 **합성 예제만** 보면 그 도구는 자기가
    태어난 이유를 못 본다 — `verify_dead_fields.py` 가 정확히 그 상태였다.

★ 이 도구 자신의 출생 표본
--------------------------
태어난 사유: *"자기시험이 있는데도 출생 사유를 못 잡은 도구가 있었다(verify_dead_fields)."*
그래서 자기시험의 첫 갈래가 **「자기시험은 있는데 출생 표본이 없는 도구」**다.
거기서 초록이 나오면 이 도구도 같은 병에 걸린 것이다.

★ 래칫이다 — 소급 사유를 요구하지 않는다 (D-311)
------------------------------------------------
오늘 없는 것에 사후 사유를 달게 하면 사유란이 거짓으로 채워진다. 그래서 오늘의 보유
현황을 **기준선으로 잠그고**, 새 도구가 표본 없이 태어나는 것만 막는다.
줄어드는(=채워지는) 것은 환영이고, 채워지면 기준선에서 빠진다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
GATES = ROOT / "docs" / "agent" / "verify_gates.sh"
BASELINE = ROOT / "docs" / "agent" / "evidence" / "D-310" / "selftest_baseline.txt"

#: 자기시험이 있다고 볼 표시.
SELFTEST_MARKERS = ("--self-test", "def self_test", "탐지기 자기시험", "self_test()")

#: **출생 표본**이 있다고 볼 표시. 도구를 만들게 한 사례를 fixture 로 박았다는 선언이다.
#: 표시를 이름으로 고정하는 이유: "표본을 넣었다"는 보고는 문서이고, 이 낱말이 소스에
#: 있는 것은 사실이다. 다음 사람이 검색으로 찾을 수 있어야 한다.
BIRTH_MARKERS = ("출생 표본", "출생표본", "BIRTH_SAMPLE", "birth-sample", "birth sample")

#: 판정 대상에서 뺀다 — 게이트·검증기가 아니라 **측정기·생성기**다.
#: 이름을 적어 두는 이유는 빠진 줄이 보이게 하기 위해서다(면제가 아니라 등재).
NOT_A_GATE: dict[str, str] = {
    "gen_tenant_census.py": "생성기 — 판정하지 않는다. 판정은 test_tenant_isolation 이 한다",
    "gen_manifest.py": "생성기",
    "gen_integration_test_report.py": "생성기 — 증거에서 문서를 만든다",
    "probe_juso_direction.py": "측정기 — 실호출 1회. 판정 대상이 아니라 판정의 입력이다",
    "probe_public_data_schema.py": "측정기",
    "probe_census_gap.py": "측정기",
    "probe_dashboard_list.py": "측정기",
    "probe_flightlog_lookup.py": "측정기",
    "probe_isolatable_census.py": "측정기",
    "probe_openapi_response_decl.py": "측정기",
    "probe_p0_targets.py": "측정기",
    "probe_tenant_isolation.py": "측정기",
    "probe_public_data_schema.py ": "측정기",
    "scan_auth_surface.py": "측정기 — 훑어서 표를 낸다",
    "scan_dump_created_by.py": "측정기",
    "scan_frontend_success_contract.py": "측정기",
    "scan_request_timeouts.py": "판정 엔진 — 게이트 진입점은 verify_timeout.py 다(중복 0)",
    "scan_silent_success.py": "측정기",
    "map_routes_to_models.py": "측정기",
    "build_leak_targets.py": "측정기",
    "draft_isolation_targets.py": "측정기",
    "gen_tenant_census.py ": "생성기",
    "backfill_owner_apply.py": "일회성 마이그레이션 도구",
    "backfill_owner_dryrun.py": "일회성 마이그레이션 도구",
    "backfill_owner_rollback.py": "일회성 마이그레이션 도구",
    "role_split_local.py": "일회성 도구",
    "check_demo_isolation.py": "게이트다 — 아래 판정 대상",
    "check_key_divergence.py": "게이트다 — 아래 판정 대상",
    "dump_openapi_routes.py": "측정기",
}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def shell_gates() -> list[tuple[str, str]]:
    """(이름, 본문) — `verify_gates.sh` 의 게이트 함수 전수."""
    if not GATES.is_file():
        return []
    src = GATES.read_text(encoding="utf-8")
    starts = [(m.group(1), m.start())
              for m in re.finditer(r"^gate_([a-z0-9_]+)\(\)\s*\{", src, re.M)]
    tops = [m.start() for m in re.finditer(r"^\w[\w./-]*\(\)\s*\{", src, re.M)]
    out = []
    for name, pos in starts:
        after = [t for t in tops if t > pos]
        out.append((f"GATE {name}", src[pos:min(after) if after else len(src)]))
    return out


def python_tools() -> list[tuple[str, str]]:
    """(이름, 소스) — `scripts/verify_*.py` · `scripts/check_*.py` 전수."""
    out = []
    for path in sorted(SCRIPTS.glob("*.py")):
        if path.name in NOT_A_GATE:
            continue
        if not (path.name.startswith("verify_") or path.name.startswith("check_")):
            continue
        out.append((path.name, path.read_text(encoding="utf-8", errors="replace")))
    return out


def audit() -> list[tuple[str, bool, bool]]:
    """[(도구, 자기시험 있음, 출생 표본 있음)]."""
    rows = []
    for name, src in shell_gates() + python_tools():
        has_self = any(m in src for m in SELFTEST_MARKERS)
        has_birth = any(m in src for m in BIRTH_MARKERS)
        rows.append((name, has_self, has_birth))
    return rows


def load_baseline() -> set[str]:
    if not BASELINE.is_file():
        return set()
    return {ln.strip() for ln in BASELINE.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")}


_HEADER = """\
# D-310 자기표본 기준선 — **오늘 출생 표본이 없는 도구** (2026-09-04 실측)
#
# ★ `python scripts/verify_tool_selftest.py --freeze` 가 만든다. 손으로 고치지 말 것.
#
# 래칫이다 — 소급 사유를 요구하지 않는다(D-311). 오늘 없는 것에 사후 사유를 달게 하면
# 사유란이 거짓으로 채워지고, 그 거짓이 다음 판정의 근거가 된다.
# 여기 이름을 **새로** 올리는 일(=표본 없는 새 도구)만 exit 1 이다.
# 이름이 사라지는 것은 채워졌다는 뜻이고, 그것은 환영이다.
"""


def self_test() -> int:
    """★ 첫 갈래가 이 도구의 **출생 표본**이다 — 자기시험은 있는데 표본이 없는 도구."""
    birth = ("def self_test():\n    pass\n", True, False)      # verify_dead_fields 의 그 상태
    good = ("def self_test():\n    # 출생 표본\n    pass\n", True, True)
    naked = ("def main():\n    pass\n", False, False)

    def probe(src: str) -> tuple[bool, bool]:
        return (any(m in src for m in SELFTEST_MARKERS),
                any(m in src for m in BIRTH_MARKERS))

    cases = (
        ("★ 출생 표본 — 자기시험은 있는데 출생 표본이 없다", birth),
        ("자기시험 + 출생 표본이 다 있는 도구", good),
        ("둘 다 없는 도구", naked),
    )
    bad = 0
    for label, (src, want_self, want_birth) in cases:
        got = probe(src)
        ok = got == (want_self, want_birth)
        print(f"  {'OK  ' if ok else 'FAIL'} {label}  → 자기시험={got[0]} 출생표본={got[1]}")
        if not ok:
            bad += 1
    if bad:
        print(f"[TOOLSELF] 자기시험 {bad}건 실패 — 이 판정기는 눈이 멀었다")
        return 1
    print(f"[TOOLSELF] 자기시험 {len(cases)}건 통과 (출생 표본 포함)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != 0:
        return 1

    rows = audit()
    total = len(rows)
    with_self = [n for n, s, _ in rows if s]
    with_birth = [n for n, _, b in rows if b]
    without_birth = sorted(n for n, _, b in rows if not b)

    # ★ D-301 — 분모와 함께. 0건은 통과가 아니라 열거기 고장이다.
    print(f"[TOOLSELF] 검사 **{total}종** (모수=verify_gates.sh 의 게이트 함수 + "
          f"scripts/verify_*·check_*.py · 측정기·생성기 {len(NOT_A_GATE)}종 제외)")
    if not rows:
        print("[TOOLSELF] 도구를 한 건도 못 찾았다 — 열거기가 눈이 멀었다 (D-301)")
        return 1
    print(f"[TOOLSELF] 자기시험 보유 **{len(with_self)}/{total}** · "
          f"출생 표본 보유 **{len(with_birth)}/{total}**")

    if args.freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(_HEADER + "\n" + "\n".join(without_birth) + "\n",
                            encoding="utf-8")
        print(f"[TOOLSELF] 기준선 {len(without_birth)}종 기록 — "
              f"{BASELINE.relative_to(ROOT)}")
        return 0

    if args.list:
        for name, s, b in rows:
            print(f"  {'자기시험 O' if s else '자기시험 X'} "
                  f"{'출생표본 O' if b else '출생표본 X'}  {name}")

    baseline = load_baseline()
    if not baseline:
        print("[TOOLSELF] 기준선 파일이 없다 — `--freeze` 로 오늘의 현황을 먼저 잠근다. "
              "기준선 없이 내는 초록은 아무것도 재지 않은 것이다 (D-301)")
        return 1

    fresh = [n for n in without_birth if n not in baseline]
    healed = sorted(baseline - set(without_birth))
    print(f"[TOOLSELF] 기준선 {len(baseline)}종 · **새로 표본 없이 태어난 도구 "
          f"{len(fresh)}종** · 채워진 것 {len(healed)}종")
    if healed:
        print(f"[TOOLSELF] 채워졌다: {healed[:6]}" + (" …" if len(healed) > 6 else ""))
        print("[TOOLSELF] `--freeze` 로 기준선을 줄인다 — 줄어드는 것이 보여야 갚는 맛이 난다")

    if fresh:
        print("[TOOLSELF] 위반 — **도구는 자기가 태어난 표본을 시험에 넣는다** (D-310)")
        for n in fresh:
            print(f"  · {n}: 출생 표본이 없다. 이 도구를 만들게 한 **바로 그 사례**를 "
                  f"fixture 로 박고, 주석에 「출생 표본」이라고 적는다")
        return 1
    print("[TOOLSELF] 통과 — 표본 없이 태어난 새 도구가 없다")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(__file__)
    sys.exit(main())
