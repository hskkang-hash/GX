#!/usr/bin/env python
"""D-334 — **주석 처리된 권한 데코레이터**를 게이트로 막는다.

    권한 검사는 없는 것보다 **주석 처리된 것이 더 위험하다.**
    없으면 「아직 안 붙였다」로 읽히지만, 주석은 **「한때 붙어 있었다」**는 뜻이다.
    그리고 코드를 읽는 사람에게는 **붙어 있는 것처럼 보인다.**

무엇을 막는가 — 둘. **성격이 다르므로 규칙도 다르다** (D-290 · 한 칸에 두지 않는다)

  ① 열린 문 — **래칫 대상이 아니다. 오늘 빨개진다.**
     주석 처리된 권한이 있는데 그 라우트에 `auth=` 도 없으면 exit 1.
     이건 「권한이 느슨하다」가 아니라 **「인증 관문이 아예 없다」**이고,
     D-334 ③ 의 「열려 있으면 즉시 잠근다」가 가리키는 자리다.
     ★ 소급 유예가 없다. 새로 생기든 예전부터 있었든 **열린 문은 열린 문이다.**

  ② 늘어남 — **래칫이다** (D-311)
     주석 처리된 권한이 **기준선에 없던 자리에 새로** 생기면 exit 1.
     오늘 있는 39 자리에 소급 사유를 요구하지 않는다 — 사후 사유는 거짓으로 채워지고,
     그 거짓이 다음 판정의 근거가 된다. 사라지는 것은 환영이고 기준선에서 빠진다.

왜 `auth=` 를 같이 보는가 — 「같은 이름, 다른 것」 (D-337)
--------------------------------------------------------
`@path_permission` 은 **권한**이고 `auth=` 는 **인증**이다. 이름이 비슷해서 한 칸에 놓기
쉽지만 둘은 다른 관문이다. 주석 처리된 권한 + 살아 있는 인증 = 인증된 아무 역할이나 통과.
주석 처리된 권한 + 없는 인증 = **익명 통과.** 게이트가 ①과 ②를 가르는 이유가 이것이다.

★ 이 도구의 **출생 표본** (D-310 — 도구는 자기가 태어난 표본을 시험에 넣는다)
-----------------------------------------------------------------------------
태어난 사유: 2026-09-07 실측 — `drone_views.py:29` 에서

    @route.get('/online-drones')            ← auth= 가 없다
    # @path_permission("read")              ← 권한은 주석 처리되어 있다

이 라우트는 **익명 GET 에 200 과 데이터를 돌려주고 있었다.** 같은 모양이 15자리 있었다.
그래서 자기시험의 첫 갈래가 **바로 이 두 줄**이다. 여기서 초록이 나오면 이 도구가 아니다.

    python scripts/verify_commented_guards.py             # 판정
    python scripts/verify_commented_guards.py --list      # 자리 목록
    python scripts/verify_commented_guards.py --freeze    # 기준선 갱신
    python scripts/verify_commented_guards.py --self-test

호스트에서 돈다 — Django 가 필요 없다. 정적 판정만 하기 때문이다.
「지금 실제로 열려 있는가」는 이 게이트가 아니라 `probe_commented_guards.py` 가 **호출로** 답한다.
게이트가 정적인 이유: 게이트는 커밋마다 돌아야 하고, 커밋 훅에서 앱을 띄울 수는 없다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from probe_commented_guards import (           # noqa: E402 — 술어를 한 곳에만 둔다 (DA-01)
    GUARD_DECORATORS,
    RE_ACTIVE,
    RE_COMMENTED,
    _enclosing_class,
    _handler_after,
    _route_decorator_near,
    static_census,
)

ROOT = Path(__file__).resolve().parent.parent

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass
BACKEND = ROOT / "backend"
BASELINE = ROOT / "docs" / "agent" / "evidence" / "D-334" / "commented_guards_baseline.txt"

_HEADER = """\
# D-334 주석 처리된 권한 데코레이터 기준선 — **오늘 주석 상태인 자리** (2026-09-07 실측)
#
# ★ `python scripts/verify_commented_guards.py --freeze` 가 만든다. 손으로 고치지 말 것.
#
# 래칫이다 — 소급 사유를 요구하지 않는다(D-311). 여기 이름을 **새로** 올리는 일만 exit 1 이다.
# 이름이 사라지는 것은 권한이 복구됐다는 뜻이고, 그것은 환영이다.
#
# ★ 단, **`auth=` 가 없는 자리는 기준선에 있어도 exit 1 이다.** 그건 느슨한 권한이 아니라
#   열린 문이고, 열린 문에는 유예가 없다 (D-334 ③).
"""


def _key(row: dict) -> str:
    """기준선에 적을 이름. **줄 번호를 넣지 않는다** — 위아래가 밀리면 전부 새것이 된다."""
    return "{file}::{cls}::{handler}::{dec}".format(
        file=row["file"], cls=row.get("class") or "-",
        handler=row.get("handler") or "-", dec=row["decorator"])


def _load_baseline() -> set[str]:
    if not BASELINE.is_file():
        return set()
    return {ln.strip() for ln in BASELINE.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")}


def _census(root: Path) -> list[dict]:
    return static_census(str(root))["commented_rows"]


def judge(rows: list[dict], baseline: set[str]) -> tuple[list[dict], list[dict]]:
    """(열린 문, 새로 생긴 주석) 을 돌려준다."""
    open_doors = [r for r in rows if not r["auth_kwarg_in_source"]]
    newly = [r for r in rows if _key(r) not in baseline]
    return open_doors, newly


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — 출생 표본이 첫 갈래다 (D-310)
# ═══════════════════════════════════════════════════════════════════════════

#: ★ 출생 표본. 2026-09-07 `drone_views.py:29` 에 실제로 있던 두 줄 그대로다.
BIRTH_SAMPLE = """\
@api_controller('/drone-communication-management')
class DroneCommunicationAPI:
    @route.get('/online-drones')
    # @path_permission("read")
    def get_online_drones(self, page: int = 1):
        return []
"""

#: 대조군 — 인증은 살아 있고 권한만 꺼진 자리. 열린 문이 **아니다.**
AUTHN_ONLY_SAMPLE = """\
@api_controller('/api-key-management')
class ThirdPartyAPIKeyController:
    @route.get("/keys", response=List[APIKeySchema], auth=CustomJWTAuth())
    # @path_permission("read", path_override='/api-key-management')
    def list_api_keys(self, request):
        return []
"""

#: 대조군 — 권한 계열이 **아닌** 것. 주석 처리되면 접근이 좁아진다 (D-324 술어).
NOT_A_GUARD_SAMPLE = """\
@api_controller('/x')
class X:
    @route.get('/y')
    # @csrf_exempt
    # @require_http_methods(["GET"])
    def y(self, request):
        return []
"""


def _census_text(text: str) -> list[dict]:
    """파일 대신 문자열을 센다 — 자기시험이 저장소를 건드리지 않게."""
    lines = text.splitlines(keepends=True)
    rows = []
    for i, line in enumerate(lines):
        if RE_ACTIVE.match(line):
            continue
        m = RE_COMMENTED.match(line)
        if not m:
            continue
        route = _route_decorator_near(lines, i)
        rows.append({
            "file": "<self-test>", "line": i + 1, "decorator": m.group(1),
            "source": line.strip(), "class": _enclosing_class(lines, i),
            "handler": _handler_after(lines, i), "route_decorator": route,
            "auth_kwarg_in_source": bool(route and "auth=" in route),
        })
    return rows


def self_test() -> int:
    """★ 출생 표본이 첫 갈래다. 여기서 초록이 나오면 이 도구가 아니다."""
    failures = []

    # ① 출생 표본 — 반드시 「열린 문」으로 잡혀야 한다
    rows = _census_text(BIRTH_SAMPLE)
    if len(rows) != 1:
        failures.append("출생 표본에서 주석 권한을 %d건 셌다 (1건이어야 한다)" % len(rows))
    else:
        open_doors, _ = judge(rows, baseline=set())
        if not open_doors:
            failures.append("★ 출생 표본을 「열린 문」으로 잡지 못했다 — 이 도구가 태어난 이유다")
        if rows[0]["handler"] != "get_online_drones":
            failures.append("출생 표본의 핸들러를 잘못 짚었다: %r" % rows[0]["handler"])

    # ② 대조군 — 인증이 살아 있으면 열린 문이 아니다
    rows = _census_text(AUTHN_ONLY_SAMPLE)
    if len(rows) != 1:
        failures.append("authn_only 표본에서 주석 권한을 %d건 셌다 (1건이어야 한다)" % len(rows))
    else:
        open_doors, _ = judge(rows, baseline=set())
        if open_doors:
            failures.append("auth= 가 있는 자리를 「열린 문」으로 잘못 잡았다 — 권한과 인증을 한 칸에 뒀다")

    # ③ 대조군 — 권한 계열이 아닌 것은 세지 않는다
    rows = _census_text(NOT_A_GUARD_SAMPLE)
    if rows:
        failures.append("권한 계열이 아닌 데코레이터를 셌다: %s" % [r["decorator"] for r in rows])

    # ④ 래칫 — 기준선에 없는 자리는 새것이다
    rows = _census_text(AUTHN_ONLY_SAMPLE)
    _, newly = judge(rows, baseline=set())
    if len(newly) != 1:
        failures.append("래칫이 새 자리를 잡지 못했다")
    _, newly = judge(rows, baseline={_key(rows[0])})
    if newly:
        failures.append("래칫이 기준선에 있는 자리를 새것으로 잘못 잡았다")

    # ⑤ 술어가 한 곳에만 있는가 — probe 와 게이트가 같은 목록을 본다
    if "path_permission" not in GUARD_DECORATORS:
        failures.append("권한 계열 목록이 비었다")

    for f in failures:
        print("  [자기시험 실패] %s" % f)
    print("[SELFTEST] verify_commented_guards: %s" % ("FAIL" if failures else "OK"))
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="주석 처리된 권한 데코레이터 게이트 (D-334)")
    ap.add_argument("--list", action="store_true", help="자리 목록을 찍는다")
    ap.add_argument("--freeze", action="store_true", help="기준선을 오늘로 갱신한다")
    ap.add_argument("--self-test", action="store_true", help="자기시험만 돌린다")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not BACKEND.is_dir():
        print("[GUARDS] backend/ 가 없다 — 저장소 루트에서 돌려라")
        return 2

    rows = _census(BACKEND)
    baseline = _load_baseline()
    open_doors, newly = judge(rows, baseline)

    if args.list:
        for r in sorted(rows, key=lambda r: (r["file"], r["line"])):
            print("  %-6s %s:%s  %s" % (
                "OPEN" if not r["auth_kwarg_in_source"] else "authn",
                r["file"], r["line"], r.get("handler")))
        print("[GUARDS] 주석 %d건 · 열린 문 %d건 · 기준선 %d건" % (
            len(rows), len(open_doors), len(baseline)))
        return 0

    if args.freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(_HEADER + "\n" + "\n".join(sorted(_key(r) for r in rows)) + "\n",
                            encoding="utf-8")
        print("[GUARDS] 기준선 %d건 -> %s" % (len(rows), BASELINE.relative_to(ROOT)))
        return 0

    # 자기시험을 판정 앞에 둔다 — 도구가 성한지 먼저 본다 (D-310)
    if self_test() != 0:
        print("[GUARDS] 자기시험이 실패했다 — 판정을 신뢰할 수 없다")
        return 1

    rc = 0
    if open_doors:
        print("\n[GUARDS] ★ 열린 문 %d건 — 주석 처리된 권한 + `auth=` 없음. **래칫 대상이 아니다**"
              % len(open_doors))
        for r in sorted(open_doors, key=lambda r: (r["file"], r["line"])):
            print("    %s:%s  %s" % (r["file"], r["line"], r.get("handler")))
            print("        route: %s" % r["route_decorator"])
        print("    → 인증 관문을 붙여라: `auth=CustomJWTAuth()`."
              " 지금 실제로 열려 있는지는 `probe_commented_guards.py` 가 호출로 답한다.")
        rc = 1

    if newly:
        print("\n[GUARDS] 새로 생긴 주석 권한 %d건 (기준선 %d건에 없다)" % (len(newly), len(baseline)))
        for r in sorted(newly, key=lambda r: (r["file"], r["line"])):
            print("    %s:%s  %s  %s" % (r["file"], r["line"], r.get("handler"), r["source"]))
        print("    → 권한을 되살리거나, 정당한 사유가 있으면 --freeze 로 기준선에 올려라.")
        rc = 1

    print("[GUARDS] 주석 %d건 · 열린 문 %d건 · 새로 생긴 것 %d건 · 기준선 %d건 -> %s" % (
        len(rows), len(open_doors), len(newly), len(baseline), "FAIL" if rc else "OK"))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
