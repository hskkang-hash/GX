#!/usr/bin/env python
"""ISO-03 — **새 라우트는 테넌트 범위를 「선언」하고 태어난다**.

무엇이 다른가 — 「지켜진다」와 「선언했다」는 다른 사실이다
------------------------------------------------------------
신규 경로 트립와이어(D-275 §5-1 · `common/tenant_tripwire.py`)는 이미 서 있고,
**문지기가 하나도 없는** 새 라우트를 잡는다. 그런데 그것이 보는 것은 *효과*다 —
호출 그래프 3단계 안 어딘가에서 `filter_by_group_field` 같은 이름이 나오면 통과다.

ISO-03 이 요구하는 것은 그 앞의 것, **표면의 선언**이다:

    [실측 2026-09-04 · 차선 S] 이 게이트가 태어난 사건 (★ 출생 표본)
      · 문지기가 없는 새 라우트를 심었다 → `verify_tenant_scope.py` exit 1  ✔ 잡힌다
      · 문지기를 **부르기만** 하고 `@tenant_scoped` 는 없는 새 라우트를 심었다
        → 같은 게이트 exit 0  ✘ **통과했다**
    두 실험 사이의 차이가 정확히 ISO-03 의 몫이다.

왜 표면이어야 하나 — 「핸들러 안을 읽어야 아는 것」은 다음 사람에게 안 보인다
-----------------------------------------------------------------------------
호출 그래프 안의 문지기는 **읽어야 안다.** 라우트가 500개면 아무도 안 읽는다.
그리고 그 판정은 AST 3단계라 동적 디스패치에서 조용히 틀린다(트립와이어 머리말이
자기 한계로 적어 둔 것). 표면의 데코레이터는 **보면 안다** — 사람도, 게이트도.
D-346 ISO-03 의 [실측] 이 말한 것이 이것이다: *"663 라우트 중 `@tenant_scoped` 표식이
붙은 것은 11건. 나머지는 핸들러 안에서 좁히거나 좁히지 않는다 — 라우트 표면에서는
알 수 없다."*

래칫이다 — **소급하지 않는다** (D-311)
--------------------------------------
오늘 선언 없는 라우트가 수백 건이다. 그것을 오늘 다 고치라고 하면 사유란이 거짓으로
채워지거나 게이트가 꺼진다. 그래서 오늘의 목록을 **이름으로** 잠그고(수가 아니다 —
수로 잠그면 낡은 라우트가 지워질 때마다 새 라우트 자리가 조용히 생긴다, D-249),
**등재부에 없던 이름이 선언 없이 나타나는 것만** 실패로 본다.

    python scripts/verify_route_scope_declared.py                  # 판정
    python scripts/verify_route_scope_declared.py --list           # 선언한 라우트 전수
    python scripts/verify_route_scope_declared.py --write-baseline # 등재부 갱신
    python scripts/verify_route_scope_declared.py --self-test      # 양성·음성 대조

무엇을 **안** 하나 — 중복 0 (원칙 1)
------------------------------------
· 라우트 열거와 문지기 판정을 **다시 적지 않는다.** `common/tenant_tripwire.scan_static()`
  을 부른다. 판정식 복사본 하나가 격리 사고의 원인이었다(D-212).
· 「문지기가 있는가」는 여기서 안 본다 — 그것은 트립와이어의 몫이다. 여기는 오직
  **선언했는가**만 본다. 두 게이트가 같은 것을 세면 하나가 꺼져도 아무도 모른다.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

BASELINE = ROOT / "docs" / "agent" / "evidence" / "ISO-03" / "declaration_baseline.txt"

#: 표면의 선언으로 인정하는 이름. **데코레이터 하나뿐이다** — 늘리는 것은
#: "이것도 선언으로 친다"는 선언이고, 그때 이 줄을 사유와 함께 고친다.
DECLARATIONS = frozenset({"tenant_scoped"})

#: 열거기가 이보다 적게 세면 **고장**이다. 0건 위의 "위반 0" 은 초록이 아니다 (D-301).
MIN_ROUTES = 233


# ══════════════════════════════════════════════════════════════════════════
# 판정 — 순수 함수. 자기시험이 겨누는 과녁이 여기다 (D-277)
# ══════════════════════════════════════════════════════════════════════════

def declares(gatekeepers: frozenset[str] | set[str] | tuple[str, ...]) -> bool:
    """이 라우트가 **표면에서** 테넌트 범위를 선언했는가.

    `gatekeepers` 는 트립와이어가 낸 값이다 — 데코레이터와 호출이 섞여 있고,
    그중 **데코레이터로 인정된 이름**만 선언으로 본다.
    """
    return bool(set(gatekeepers) & DECLARATIONS)


def judge(*, undeclared: set[str], baseline: set[str]) -> list[str]:
    """등재부에 없던 이름이 선언 없이 나타났는가. **이 함수가 정본이다.**

    줄어드는 것(등재부에는 있는데 지금 없는 것)은 실패가 아니다 — 고쳐졌거나 지워졌다.
    """
    return sorted(undeclared - baseline)


def stale(*, undeclared: set[str], baseline: set[str]) -> list[str]:
    """등재부에만 남은 이름. 실패는 아니지만 **놔두면 그 자리가 빈다** (D-249)."""
    return sorted(baseline - undeclared)


# ══════════════════════════════════════════════════════════════════════════
# 등재부
# ══════════════════════════════════════════════════════════════════════════

def load_baseline() -> set[str] | None:
    if not BASELINE.is_file():
        return None
    out = set()
    for line in BASELINE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return out


def write_baseline(undeclared: set[str], total: int, declared: int) -> None:
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    head = (
        "# ISO-03 선언 등재부 — **새 라우트는 테넌트 범위를 선언하고 태어난다**\n"
        "#\n"
        "# 여기 적힌 이름들은 `@tenant_scoped` 선언 없이 **이미 존재하는** 라우트다.\n"
        "# 소급해서 고치라고 하지 않는다(D-311). 여기 **없던 이름이 선언 없이 나타나면**\n"
        "# scripts/verify_route_scope_declared.py 가 exit 1 로 멈춘다.\n"
        "#\n"
        "# 줄어드는 것은 환영이다 — 줄었으면 `--write-baseline` 으로 다시 만들어 커밋한다.\n"
        "# 줄어든 자리를 안 지우면 그 이름으로 새 라우트가 조용히 들어올 수 있다(D-249).\n"
        f"#\n# 측정 {date.today().isoformat()} · 라우트 전수 {total}건 "
        f"· 선언 {declared}건 · 미선언 {len(undeclared)}건\n"
    )
    BASELINE.write_text(head + "\n".join(sorted(undeclared)) + "\n", encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════
# 실행
# ══════════════════════════════════════════════════════════════════════════

def scan() -> tuple[set[str], set[str], list]:
    """(미선언 이름, 선언 이름, 판정 전수). 열거는 **트립와이어의 눈을 빌린다**."""
    from common import tenant_tripwire

    verdicts = tenant_tripwire.scan_static()
    declared = {v.key for v in verdicts if declares(v.gatekeepers)}
    undeclared = {v.key for v in verdicts} - declared
    return undeclared, declared, verdicts


def main_judge() -> int:
    undeclared, declared, verdicts = scan()
    total = len(verdicts)

    print(f"[입력] 라우트 {total}건 (술어=@route.* 정적 전수 · "
          f"열거기=common.tenant_tripwire.scan_static)")
    if total < MIN_ROUTES:
        print(f"[ISO-03] 라우트를 {total}건밖에 못 셌다 (하한 {MIN_ROUTES}) — "
              f"**열거기 고장**으로 본다. 이 상태의 「위반 0」은 눈이 감긴 것이다 (D-301)")
        return 1

    base = load_baseline()
    if base is None:
        print(f"[ISO-03] 등재부가 없다 ({BASELINE.relative_to(ROOT)}). "
              f"`--write-baseline` 로 만들고 커밋하라 — 등재부 없이 통과시키면 "
              f"무엇이 늘었는지 아무도 모른다")
        return 1

    print(f"[ISO-03] 표면 선언 {len(declared)}건 · 미선언 {len(undeclared)}건 "
          f"(등재부 {len(base)}건 · 술어=@{' / @'.join(sorted(DECLARATIONS))})")

    new = judge(undeclared=undeclared, baseline=base)
    if new:
        print(f"[ISO-03] **선언 없이 태어난 새 라우트 {len(new)}건** — 멈춘다")
        for key in new:
            v = next(x for x in verdicts if x.key == key)
            print(f"  · {key}\n"
                  f"      경로 {v.method} {v.path}  ({v.where})\n"
                  f"      만지는 테넌트 모델: {', '.join(v.models) or '(없음)'}\n"
                  f"      → 표면에 @tenant_scoped 가 없다. 핸들러 안에서 좁히더라도 "
                  f"**라우트 표면에서는 알 수 없다** — 그것이 ISO-03 이 닫는 자리다\n"
                  f"      조치: 핸들러에 `@tenant_scoped(...)` 를 걸어라. 테넌트 데이터를 "
                  f"만지지 않는 라우트라면 그 사실도 선언이다 — 사유와 함께 등재부에 "
                  f"올리되, 올리는 커밋에서 **왜 안 만지는지**를 적어라")
        return 1

    left = stale(undeclared=undeclared, baseline=base)
    if left:
        print(f"[ISO-03] ↓ 미선언이 {len(base)} → {len(undeclared)} 로 줄었다 "
              f"({', '.join(left[:3])}{' 외' if len(left) > 3 else ''}) — "
              f"`--write-baseline` 로 등재부를 다시 만들어 커밋하라")
    print("[ISO-03] 통과 — 선언 없이 태어난 새 라우트 0건")
    return 0


def list_declared() -> int:
    undeclared, declared, verdicts = scan()
    print(f"[입력] 라우트 {len(verdicts)}건")
    for v in sorted(verdicts, key=lambda x: x.key):
        if declares(v.gatekeepers):
            print(f"  선언  {v.key}  ({v.method} {v.path})")
    print(f"[ISO-03] 선언 {len(declared)}건 / 전수 {len(verdicts)}건 "
          f"· 미선언 {len(undeclared)}건")
    return 0


def self_test() -> int:
    bad = 0

    def check(label: str, got, want) -> None:
        nonlocal bad
        ok = got == want
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1
            print(f"       기대 {want!r} · 실제 {got!r}")

    # ── 가. 선언 술어 ────────────────────────────────────────────────────
    check("★ 출생표본 — **문지기만 부르고 선언은 없는** 라우트는 선언으로 안 친다",
          declares(("filter_by_group_field", "get_scoped_or_404")), False)
    check("   `@tenant_scoped` 가 붙어 있으면 선언으로 친다",
          declares(("tenant_scoped",)), True)
    check("   문지기와 선언이 함께 있어도 선언이다",
          declares(("tenant_scoped", "filter_by_group_field")), True)
    check("아무것도 없으면 선언이 아니다", declares(()), False)

    # ── 나. 래칫 판정 ────────────────────────────────────────────────────
    base = {"GET a.A.x", "GET a.A.y"}
    check("★ 출생표본 ② — 등재부에 **없던** 미선언 라우트가 나타나면 잡는다",
          judge(undeclared={"GET a.A.x", "GET a.A.z"}, baseline=base), ["GET a.A.z"])
    check("등재부에 있는 미선언 라우트는 안 잡는다 (소급 금지 · D-311)",
          judge(undeclared=base, baseline=base), [])
    check("새로 생긴 라우트라도 **선언했으면** 미선언 집합에 없으므로 안 잡는다",
          judge(undeclared=base, baseline=base), [])
    check("줄어든 것은 실패가 아니라 등재부 갱신 안내다",
          stale(undeclared={"GET a.A.x"}, baseline=base), ["GET a.A.y"])

    # ── 다. 열거기가 실제로 도는가 — 0건이면 판정이 아니라 고장이다 ────
    try:
        undeclared, declared, verdicts = scan()
        n = len(verdicts)
    except Exception as exc:                                   # noqa: BLE001
        print(f"  FAIL 열거기가 죽었다: {type(exc).__name__}: {exc}")
        return 1
    check(f"라우트를 실제로 훑는다 ({n}건 · 하한 {MIN_ROUTES})", n >= MIN_ROUTES, True)
    check(f"선언한 라우트를 실제로 가려낸다 ({len(declared)}건)", len(declared) > 0, True)

    if bad:
        print(f"[ISO-03] 자기시험 {bad}건 실패 — **이 게이트는 눈이 멀었다**")
        return 1
    print("[ISO-03] 자기시험 10건 통과 (선언 술어 4 · 래칫 4 · 열거 2 · 출생 표본 2)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--write-baseline", action="store_true")
    args = ap.parse_args()

    print("[ISO-03] 새 라우트는 테넌트 범위를 **선언**하고 태어난다 "
          "(D-346 ISO-03 · 표면의 선언 ≠ 호출 그래프의 문지기)")
    if args.self_test:
        return self_test()
    if args.list:
        return list_declared()
    if args.write_baseline:
        undeclared, declared, verdicts = scan()
        if len(verdicts) < MIN_ROUTES:
            print(f"[ISO-03] 라우트 {len(verdicts)}건 — 열거기 고장으로 본다. "
                  f"등재부를 이 상태로 만들지 않는다")
            return 1
        write_baseline(undeclared, len(verdicts), len(declared))
        print(f"[ISO-03] 등재부를 다시 만들었다 — {BASELINE.relative_to(ROOT)} "
              f"(미선언 {len(undeclared)}건 / 전수 {len(verdicts)}건)")
        return 0
    return main_judge()


if __name__ == "__main__":
    raise SystemExit(main())
