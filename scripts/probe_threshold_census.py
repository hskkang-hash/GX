#!/usr/bin/env python
"""하드코딩 임계값 **전수** — 표를 만들기 전에 분모부터 (D-301 · D-325 ②).

왜 표보다 이것이 먼저인가
-------------------------
D-325 는 임계값 표를 최우선으로 지시하면서 **착수 전 필수**를 함께 못박았다:

    지금 코드에 하드코딩된 임계값을 전수로 세라. 분모를 먼저 내라(D-301).
    나는 그 수를 모른다 — [추정] 없이 **[실측]으로 답하라.**

분모 없이 표를 만들면 표는 **자기가 무엇을 대체했는지 모른다.** 그러면 다음 사람은
"임계값은 이제 표에 있다"고 읽고, 코드에 남은 것들을 보지 못한다 — D-301 이 말한
「검사 못함 ≠ 0건 검사」와 같은 얼굴이다.

    python scripts/probe_threshold_census.py            # 전수 + 요약
    python scripts/probe_threshold_census.py --list     # 건별 전부 출력
    python scripts/probe_threshold_census.py --names    # 이름만 (래칫 기준선 만들 때)
    python scripts/probe_threshold_census.py --self-test

모수 (D-301)
------------
`backend/**/*.py` 중 **시험·마이그레이션·__pycache__ 를 뺀 전부.**
시험을 빼는 이유: 시험 안의 숫자는 **판정 기준이 아니라 표본**이다. 표로 옮기면
시험이 자기가 재는 값을 스스로 고르게 된다.

술어 — 「숫자가 **판단을 가르는 자리**에 있는가」
-------------------------------------------------
숫자가 있다고 임계값이 아니다. 인덱스 `[0]`, 배열 크기, HTTP 상태 코드는 임계값이 아니다.
그래서 **자리**로 판정한다. 다음 넷 중 하나여야 한다:

  ① 비교식의 한쪽      `if score > 0.7`  · `if age_seconds >= 30`
  ② 임계값 이름의 대입  `DEDUP_WINDOW = 10` · `MAX_RETRY = 3`  (이름 패턴 아래 THRESHOLD_NAME)
  ③ 시간 생성자 인자    `timedelta(seconds=10)` · `sleep(5)` · `timeout=3`
  ④ 임계값 이름의 기본값 `def f(*, retry_limit: int = 3)`

그리고 **뺀다** — 「이것은 임계값이 아니다」가 명백한 것:
  · `0` `1` `-1` : 있음/없음·첫 항목·실패 표지다. 경계를 가르는 값이 아니다
  · HTTP 상태 코드 3자리(100~599)가 `status`·`code` 이름 옆에 있는 것
  · 연도로 보이는 값(1900~2100)

★ 술어를 좁힐 때마다 자기시험을 다시 돈다 (D-326)
-------------------------------------------------
`verify_external_sources` 에서 술어를 세 번 좁혔고 **세 번 다 반대편으로 넘어갔다.**
그래서 아래 자기시험은 좁힌 쪽(음성)과 남겨야 하는 쪽(양성)을 **함께** 잰다.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

SKIP_DIRS = {"__pycache__", "migrations", "node_modules", ".venv", "tests", "fonts"}

#: 계약 기능(F-01~F-14)이 실제로 사는 자리. 여기 것이 **표로 옮길 1순위**다.
#: 나머지(주문·운송장 등 이관 자산)는 세되 표의 대상이 아니다 — 세는 것과 옮기는 것은 다르다.
CONTRACT_SURFACE = ("kernels/", "apps/", "adapters/", "stream_monitors/", "common/")

#: ② ④ 의 이름 패턴. **이름이 경계를 말하는가**로 본다.
THRESHOLD_NAME = re.compile(
    r"(THRESHOLD|LIMIT|MAX|MIN|WINDOW|TIMEOUT|INTERVAL|RETRY|TTL|EXPIRE|EXPIRY"
    r"|DEADLINE|DURATION|PERIOD|SECONDS|MINUTES|HOURS|DAYS|SIZE|COUNT|RATE"
    r"|TOLERANCE|MARGIN|CUTOFF|CAPACITY|QUOTA|BATCH|CHUNK|DELAY|BACKOFF)",
    re.IGNORECASE)

#: ③ 시간·크기를 만드는 호출. 인자 이름이 아니라 **호출 이름**으로 잡는다.
TIME_CALLS = {"timedelta", "sleep", "Timer", "wait", "timeout"}
TIME_KWARGS = {"seconds", "minutes", "hours", "days", "milliseconds",
               "timeout", "interval", "ttl", "expires", "expiry", "delay"}

#: 「이것은 임계값이 아니다」 — 경계를 가르지 않는 값
TRIVIAL = {0, 1, -1}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


class Hit:
    __slots__ = ("path", "line", "kind", "name", "value", "snippet")

    def __init__(self, path: str, line: int, kind: str, name: str, value, snippet: str):
        self.path, self.line, self.kind = path, line, kind
        self.name, self.value, self.snippet = name, value, snippet

    @property
    def on_contract_surface(self) -> bool:
        return any(self.path.startswith(p) for p in CONTRACT_SURFACE)

    def render(self) -> str:
        mark = "*" if self.on_contract_surface else " "
        return (f"  {mark} {self.path}:{self.line}  [{self.kind}] "
                f"{self.name} = {self.value!r}   {self.snippet}")


def _num(node):
    """숫자 리터럴이면 값, 아니면 None. `-5` 처럼 단항 마이너스도 숫자다."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = _num(node.operand)
        return -inner if inner is not None else None
    return None


def _name_of(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _name_of(node.func)
    return ""


def _is_status_code(name: str, value) -> bool:
    """HTTP 상태 코드는 임계값이 아니다 — 프로토콜이 정한 상수다."""
    return (isinstance(value, int) and 100 <= value <= 599
            and re.search(r"status|http|code", name, re.IGNORECASE) is not None)


def _is_year(value) -> bool:
    return isinstance(value, int) and 1900 <= value <= 2100


def scan_source(src: str, rel: str) -> list:
    """한 파일. **순수 함수다** — 자기시험이 겨누는 과녁이 여기다 (D-277)."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    lines = src.split("\n")

    def snip(lineno: int) -> str:
        return lines[lineno - 1].strip()[:70] if 0 < lineno <= len(lines) else ""

    hits: list = []
    seen: set = set()   # (line, col) — 한 리터럴을 두 번 세지 않는다

    def add(node, kind: str, name: str, value) -> None:
        key = (getattr(node, "lineno", 0), getattr(node, "col_offset", 0))
        if key in seen:
            return
        if value in TRIVIAL or _is_status_code(name, value) or _is_year(value):
            return
        seen.add(key)
        hits.append(Hit(rel, key[0], kind, name or "(익명)", value, snip(key[0])))

    for node in ast.walk(tree):
        # (1) 비교식 — `if score > 0.7`
        if isinstance(node, ast.Compare):
            if not any(isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)) for op in node.ops):
                continue
            operands = [node.left] + list(node.comparators)
            names = [_name_of(o) for o in operands if _num(o) is None]
            label = next((n for n in names if n), "")
            for o in operands:
                v = _num(o)
                if v is not None:
                    add(o, "비교", label, v)
            continue

        # (3) 시간 생성자 — `timedelta(seconds=10)` · `sleep(5)` · `f(timeout=3)`
        if isinstance(node, ast.Call):
            fname = _name_of(node.func)
            for kw in node.keywords:
                if kw.arg and kw.arg.lower() in TIME_KWARGS:
                    v = _num(kw.value)
                    if v is not None:
                        add(kw.value, "시간인자", f"{fname}({kw.arg}=)", v)
            if fname in TIME_CALLS:
                for a in node.args:
                    v = _num(a)
                    if v is not None:
                        add(a, "시간인자", f"{fname}()", v)
            continue

        # (2) 이름 있는 대입 — `DEDUP_WINDOW = 10`
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            label = next((_name_of(t) for t in targets if _name_of(t)), "")
            v = _num(node.value) if node.value is not None else None
            if v is not None and label and THRESHOLD_NAME.search(label):
                add(node.value, "이름대입", label, v)
            continue

        # (4) 이름 있는 기본값 — `def f(*, retry_limit: int = 3)`
        if isinstance(node, ast.arguments):
            pairs = []
            if node.defaults:
                pairs += list(zip(node.args[-len(node.defaults):], node.defaults))
            pairs += [(a, d) for a, d in zip(node.kwonlyargs, node.kw_defaults) if d]
            for arg, default in pairs:
                v = _num(default)
                if v is not None and THRESHOLD_NAME.search(arg.arg):
                    add(default, "기본값", arg.arg, v)
    return hits


def walk():
    hits: list = []
    files = 0
    for path in sorted(BACKEND.rglob("*.py")):
        rel_parts = path.relative_to(BACKEND).parts
        if any(p in SKIP_DIRS for p in rel_parts):
            continue
        files += 1
        hits += scan_source(path.read_text(encoding="utf-8", errors="replace"),
                            "/".join(rel_parts))
    return hits, files


def self_test() -> int:
    """★ 출생 표본 — 이 도구를 만들게 한 사례.

    D-325 가 "분모를 먼저 내라"고 한 이유는 `k1_event/services.py` 의
    `DEDUP_WINDOW = timedelta(seconds=10)` 같은 값들이 **코드에만 있고 표에 없기 때문**이다.
    그 한 줄을 못 잡으면 이 전수는 0건을 내고, 0건은 "임계값이 없다"로 읽힌다.
    """
    cases = [
        # 출생 표본 — F-04 중복 억제창. 이 값이 표에 없다는 것이 D-325 의 출발점이다
        ("★ 출생표본 DEDUP_WINDOW = timedelta(seconds=10) 을 잡는다",
         "from datetime import timedelta\nDEDUP_WINDOW = timedelta(seconds=10)\n", 1),
        ("비교식의 상수를 잡는다", "if score > 0.7:\n    pass\n", 1),
        ("이름 없는 대입은 안 잡는다", "x = 42\n", 0),
        ("이름이 경계를 말하면 잡는다", "MAX_RETRY = 3\n", 1),
        ("기본값도 이름이 말하면 잡는다",
         "def f(*, retry_limit: int = 3):\n    return retry_limit\n", 1),
        ("기본값이라도 이름이 안 말하면 안 잡는다",
         "def f(*, mode: int = 3):\n    return mode\n", 0),
        # 좁힌 쪽 (음성) — 술어를 좁힐 때마다 반대편이 열린다 (D-326)
        ("인덱스 0·1 은 안 잡는다", "if len(rows) > 0:\n    pass\n", 0),
        ("HTTP 상태 코드는 안 잡는다", "if status_code >= 400:\n    pass\n", 0),
        ("연도는 안 잡는다", "if year > 2026:\n    pass\n", 0),
        # 그런데 좁히면서 놓치면 안 되는 쪽 (양성)
        ("★ 상태 코드처럼 생겼어도 이름이 다르면 잡는다",
         "if wait_seconds >= 400:\n    pass\n", 1),
        ("한 리터럴을 두 번 세지 않는다", "TIMEOUT_SECONDS = 30\n", 1),
        ("timeout= 키워드는 잡는다", "requests.get(url, timeout=5)\n", 1),
    ]
    bad = 0
    for label, src, expect in cases:
        got = len(scan_source(src, "t.py"))
        ok = got == expect
        print(f"  {'OK  ' if ok else 'FAIL'} {label}  (기대 {expect} · 실측 {got})")
        if not ok:
            bad += 1
    if bad:
        print(f"[THRESHOLD-CENSUS] 자기시험 {bad}건 실패 — 이 전수는 눈이 멀었다")
        return 1
    print(f"[THRESHOLD-CENSUS] 자기시험 {len(cases)}건 통과 "
          f"(양성 7 · 음성 5 · 출생 표본 포함)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--names", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != 0:
        return 1

    hits, files = walk()
    surface = [h for h in hits if h.on_contract_surface]

    if args.names:
        for h in sorted(hits, key=lambda h: (h.path, h.line)):
            print(f"{h.path}:{h.line}:{h.name}")
        return 0

    print(f"[THRESHOLD-CENSUS] 모수 = backend/**/*.py {files}개 "
          f"(시험·마이그레이션 제외) · 술어 = 숫자가 판단을 가르는 자리에 있는가")
    print(f"[THRESHOLD-CENSUS] **하드코딩 임계값 {len(hits)}건** "
          f"— 그중 계약 기능 면(kernels·apps·adapters·stream_monitors·common) "
          f"**{len(surface)}건**")

    by_kind = Counter(h.kind for h in hits)
    print("[THRESHOLD-CENSUS] 자리별: "
          + " · ".join(f"{k} {v}" for k, v in by_kind.most_common()))
    by_file = Counter(h.path for h in surface)
    print("[THRESHOLD-CENSUS] 계약 면 상위 파일:")
    for path, n in by_file.most_common(12):
        print(f"    {n:3}  {path}")

    if args.list:
        print("[THRESHOLD-CENSUS] 전건 (* = 계약 기능 면):")
        for h in sorted(hits, key=lambda h: (not h.on_contract_surface, h.path, h.line)):
            print(h.render())
    else:
        print("[THRESHOLD-CENSUS] 건별은 --list")
    return 0


if __name__ == "__main__":
    sys.exit(main())
