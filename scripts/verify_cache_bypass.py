#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""D-341 착시 ⑦ — **캐시가 코드 수정보다 오래 산다.** 시험이 캐시를 재지 않게 한다.

무슨 일이 있었나 (출생 표본 · D-310)
------------------------------------
    [실측 2026-09-07 · D-334 INCIDENT §5]
    익명에게 열려 있던 15자리를 고쳤다. 고친 **뒤에** 다시 때렸는데 **2자리가 여전히 200**
    이었고, `cache.clear()` 뒤 0 이 됐다.

    [실측 2026-09-08 · 그 2자리를 술어로 되찾았다]
    `UniversalOptimizer.should_cache_request()` 에 세 자리를 넣어 보면
        /api/terminals/days-of-week      → True   ← 캐시된다
        /api/terminals/terminal-types    → True   ← 캐시된다
        /api/dronehw/.../online-drones   → False
    익명에게 200 을 내던 셋 중 **캐시되는 것이 정확히 둘**이다. 사고 기록의 「2자리」와 같다.

캐시가 없었다면 그 2자리는 **「고쳤다」로 보고됐을 것**이다. 그것이 이 게이트의 이유다.

    ⑦ 캐시 — 측정 대상과 측정 시점 사이에 낀 상태가 **결과를 대신 답한다.**
      응답 캐시만이 아니다: 모듈 임포트 캐시 · ORM 쿼리 캐시 · 브라우저 · CDN ·
      컨테이너 이미지 레이어 · `__pycache__` — 전부 같은 병이다.

규약 (D-341)
------------
    **모든 보안·회귀 시험은 캐시를 우회하거나 비우고 때린다.**
    · 우회가 가능하면 우회 (`X-No-Cache` 헤더 · 직접 호출)
    · 불가능하면 **명시적으로 비우고 시작** (`cache.clear()`)
    · 시험 파일에 **「캐시 처리: 우회 / 비움 / 해당 없음」을 한 줄로 남긴다.** 비면 게이트가 죽는다

무엇을 모수로 보나 (D-301)
--------------------------
`backend/tests/**/*.py` 중 **HTTP 를 때리는 시험** — `Client(` 또는 `self.client.<메서드>` 가
있는 파일이다. 스택을 통과하는 시험만이 캐시를 잴 수 있다. 순수 단위 시험은 대상이 아니고,
**대상이 아닌 것도 건수로 출력한다** — 「검사 못함」과 「해당 없음」은 다르다.

★ 래칫이다 (D-311) — 기존분은 소급 사유를 요구하지 않는다. **새 시험은 100% 의무.**

    python scripts/verify_cache_bypass.py            # 판정
    python scripts/verify_cache_bypass.py --list     # 파일별 상태
    python scripts/verify_cache_bypass.py --freeze   # 기준선 갱신
    python scripts/verify_cache_bypass.py --self-test

호스트에서 돈다 — Django 가 필요 없다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "backend" / "tests"
BASELINE = ROOT / "docs" / "agent" / "evidence" / "D-341" / "cache_bypass_baseline.txt"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

_HEADER = """\
# D-341 캐시 우회 기준선 — **오늘 캐시 처리 표기가 없는 시험 파일** (2026-09-08 실측)
#
# ★ `python scripts/verify_cache_bypass.py --freeze` 가 만든다. 손으로 고치지 말 것.
#
# 래칫이다(D-311). 여기 이름이 오른 파일은 오늘 면제된다. **새 파일은 면제가 없다.**
# 목록에서 이름이 빠지는 것(=표기를 채우는 것)은 환영이고, --freeze 로 내린다.
"""

#: 이 파일이 **스택을 통과하는 시험**인가. 통과하지 않으면 캐시를 잴 수 없다.
HTTP_CALL = re.compile(
    r"\bClient\s*\(|\bself\.client\.(get|post|put|patch|delete)\b|\bAPIClient\s*\(|"
    r"\brequests\.(get|post)\b")

#: 캐시 처리 세 갈래. **표기는 사람이 읽는 한 줄이고, 아래 표시는 기계가 읽는 근거다.**
BYPASS_MARKS = (
    "X_NO_CACHE", "X-No-Cache", "HTTP_X_NO_CACHE", "no_cache=true", "no_cache': 'true'",
)
CLEAR_MARKS = ("cache.clear()", "caches[", "clear_cache(")
#: 「해당 없음」은 **사유가 붙은 선언**이어야 한다. 낱말만으로는 인정하지 않는다 —
#: 사유 없는 면제는 UNREVIEWED 와 구별되지 않는다(`tenant_scope.ScopeSpec` 와 같은 규칙).
DECLARE = re.compile(r"캐시\s*처리\s*[:：]\s*(우회|비움|해당\s*없음)([^\n]*)")

STATE_BYPASS = "우회"
STATE_CLEAR = "비움"
STATE_NA = "해당 없음"
STATE_MISSING = "표기 없음"
STATE_NOT_TARGET = "대상 아님"


def classify_source(text: str) -> str:
    """이 시험 파일의 캐시 처리 상태. **선언이 우선한다** — 사람이 적은 것이 근거다.

    ★ 선언이 없어도 `X-No-Cache` 를 실제로 붙였으면 인정한다. 규약이 생기기 전에
      옳게 쓴 시험을 규약 위반으로 세면, 게이트가 **옳은 것을 벌한다.**
    """
    if not HTTP_CALL.search(text):
        return STATE_NOT_TARGET
    m = DECLARE.search(text)
    if m:
        head = m.group(1).replace(" ", "")
        if head == "해당없음" and not m.group(2).strip(" -—·:"):
            # 사유 없는 「해당 없음」은 면제가 아니다.
            return STATE_MISSING
        return {"우회": STATE_BYPASS, "비움": STATE_CLEAR}.get(head, STATE_NA)
    if any(mark in text for mark in BYPASS_MARKS):
        return STATE_BYPASS
    if any(mark in text for mark in CLEAR_MARKS):
        return STATE_CLEAR
    return STATE_MISSING


def walk() -> list[Path]:
    return sorted(p for p in TESTS.rglob("*.py")
                  if "__pycache__" not in p.parts and p.name != "__init__.py")


def scan() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in walk():
        text = path.read_text(encoding="utf-8", errors="replace")
        out[path.relative_to(ROOT).as_posix()] = classify_source(text)
    return out


def read_baseline() -> set[str]:
    if not BASELINE.exists():
        return set()
    return {line.strip() for line in BASELINE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")}


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310) — 출생 표본은 **그 2자리**다
# ═══════════════════════════════════════════════════════════════════════════

#: ★ 2026-09-07 수정 뒤에도 익명에게 200 을 내던 자리. 캐시가 대신 답한 그 둘이다.
#: (2026-09-08 `UniversalOptimizer.should_cache_request()` 로 되찾았다 — 위 머리말 참조.)
CACHE_SERVED_ROUTES = (
    "/api/terminals/days-of-week",
    "/api/terminals/terminal-types",
)

_SAMPLE_BAD = '''\
from django.test import Client, TestCase

class FormerlyOpenRoutesRejectAnonymousTest(TestCase):
    def setUp(self):
        self.client = Client(raise_request_exception=False)

    def test_anonymous_is_rejected(self):
        for path in ("/api/terminals/days-of-week", "/api/terminals/terminal-types"):
            self.assertEqual(self.client.get(path).status_code, 401)
'''

_SAMPLE_GOOD = _SAMPLE_BAD.replace(
    "Client(raise_request_exception=False)",
    "Client(raise_request_exception=False, HTTP_X_NO_CACHE='true')")

_SAMPLE_DECLARED = "# 캐시 처리: 비움 — 미들웨어를 못 끄는 자리라 setUp 에서 비운다\n" + \
    _SAMPLE_BAD.replace("def setUp", "def setUp")

_SAMPLE_UNIT = '''\
from kernels.k1_event.services import score

def test_score():
    assert score(0.9) > 0.5
'''


def self_test() -> int:
    """★ 출생 표본: **그 2자리를 때리면서 캐시를 우회하지 않는 시험**이 잡히는가.

    잡히지 않으면 이 게이트는 2026-09-07 의 그 상태를 초록으로 통과시킨다 —
    「고쳤다」로 보고되고 문은 열린 채 남는다.
    """
    checks = [
        ("★ 출생표본 — 그 2자리를 캐시 우회 없이 때리는 시험을 잡는다",
         classify_source(_SAMPLE_BAD) == STATE_MISSING),
        ("★ 출생표본 — 같은 시험이 X-No-Cache 를 붙이면 통과한다",
         classify_source(_SAMPLE_GOOD) == STATE_BYPASS),
        ("「캐시 처리: 비움」 선언을 인정한다",
         classify_source(_SAMPLE_DECLARED) == STATE_CLEAR),
        ("HTTP 를 안 때리는 단위 시험은 대상이 아니다",
         classify_source(_SAMPLE_UNIT) == STATE_NOT_TARGET),
        ("사유 없는 「해당 없음」은 면제가 아니다",
         classify_source("# 캐시 처리: 해당 없음\n" + _SAMPLE_BAD) == STATE_MISSING),
        ("사유 붙은 「해당 없음」은 인정한다",
         classify_source("# 캐시 처리: 해당 없음 — 캐시를 타지 않는 경로다\n"
                         + _SAMPLE_BAD) == STATE_NA),
        ("★ 출생표본의 두 경로가 이 파일에 박혀 있다 (D-310)",
         all(r in _SAMPLE_BAD for r in CACHE_SERVED_ROUTES)),
    ]
    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[CACHE-BYPASS] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not TESTS.exists():
        print("[CACHE-BYPASS] 시험 디렉터리가 없다: %s — 판정이 아니라 열거기 고장이다" % TESTS)
        return 1

    states = scan()
    targets = {k: v for k, v in states.items() if v != STATE_NOT_TARGET}
    missing = sorted(k for k, v in targets.items() if v == STATE_MISSING)

    if args.freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(_HEADER + "".join(m + "\n" for m in missing), encoding="utf-8")
        print("[CACHE-BYPASS] 기준선 %d건으로 잠갔다" % len(missing))
        return 0

    baseline = read_baseline()
    if not targets:
        print("[CACHE-BYPASS] 대상 0건 — 스택을 때리는 시험이 하나도 없다. 열거기 고장이다")
        return 1

    counts: dict[str, int] = {}
    for v in states.values():
        counts[v] = counts.get(v, 0) + 1
    print("[CACHE-BYPASS] [입력] 시험 파일 %d건 · 그중 스택을 때리는 것 %d건"
          % (len(states), len(targets)))
    print("[CACHE-BYPASS] 캐시 처리: " + " · ".join(
        "%s %d" % (k, v) for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))))

    if args.list:
        for name, state in sorted(states.items()):
            if state == STATE_NOT_TARGET:
                continue
            mark = "면제" if name in baseline and state == STATE_MISSING else ""
            print("  %-12s %s %s" % (state, name, mark))

    new_violations = [m for m in missing if m not in baseline]
    healed = sorted(baseline - set(missing))
    if healed:
        print("[CACHE-BYPASS] 기준선이 낡았다 — 채워진 파일 %d건. --freeze 로 내려라: %s"
              % (len(healed), ", ".join(healed[:5])))
    if new_violations:
        print("[CACHE-BYPASS] FAIL 캐시 처리 표기 없는 **새** 시험 %d건 "
              "(「캐시 처리: 우회/비움/해당 없음 — 사유」 한 줄을 적어라):" % len(new_violations))
        for name in new_violations:
            print("    %s" % name)
        return 1
    print("[CACHE-BYPASS] 새 위반 0건 (기존 면제 %d건 · 래칫 D-311)" % len(baseline))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
