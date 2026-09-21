#!/usr/bin/env python
"""juso 방향 3값 잠금을 **저장소 밖에서** 잠근다 (D-318 · D-290).

    JUSO_REVERSE_SUPPORTED = 'unknown' | 'yes' | 'no'
      · 'unknown' 인데 사유가 비면                    → exit 1
      · 'unknown' 인데 **HTTP 구현체가 존재하면**      → exit 1
      · 'yes'  인데 응답 스키마 스냅샷 시험이 없으면    → exit 1
      · 'no'   인데 사유(어느 응답을 보고 그렇게 판정했나)가 비면 → exit 1

왜 3값인가 — **"안 준다" 와 "안 물어봤다" 는 다른 사실이다**
------------------------------------------------------------
둘을 합치면 대체 자원을 찾아야 하는지 아직 물어보면 되는지 모른다. D-290 이
pending/failed 를 가른 것과 같은 이유이고, 여기서는 그 구별이 **자원 선택의 판정**을 가른다.

★ 'unknown' 인데 어댑터가 있으면 왜 멈추나
------------------------------------------
방향도 모르는 채로 파서를 쓰면 그 파서는 첫 실호출에서 전부 재작업이 된다(D-280).
다만 **포트·저하 운전은 어댑터가 아니다** — 명세 없이도 확정할 수 있는 것이고(DA-02 §3),
SDN 에서 이미 그 경계를 그었다. 그래서 이 게이트가 금지하는 것은 **HTTP 호출 코드**다:
`requests` · `urllib.request` · `httpx` · `http.client`.

    python scripts/verify_juso_direction.py             # 판정
    python scripts/verify_juso_direction.py --self-test # 양성·음성 대조 (D-277)

★ 자기표본 (D-310) — 이 도구를 태어나게 한 사례를 fixture 로 박는다
------------------------------------------------------------------
태어난 사유: *"juso 가 역방향을 주는지 모르는 채로 어댑터를 만들 뻔했다."*
그 표본(=unknown + HTTP 구현)이 자기시험에 있고, 거기서 초록이 나오면 이 도구는 도구가 아니다.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JUSO = ROOT / "backend" / "adapters" / "juso" / "__init__.py"
TESTS = ROOT / "backend" / "tests" / "test_fx5_address.py"

VALID = ("unknown", "yes", "no")

#: 'yes' 로 올리는 순간 **의무가 되는** 시험 — 실측한 응답 모양을 박는 자리다.
SCHEMA_SNAPSHOT_TEST = "test_juso_response_schema_snapshot"

#: 'unknown' 인 동안 있어서는 안 되는 것 — HTTP 호출 코드.
HTTP_TOKENS = ("requests.", "urllib.request", "httpx.", "http.client")

MIN_REASON = 60

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def literal(src: str, name: str):
    for node in ast.parse(src).body:
        targets = getattr(node, "targets", []) or (
            [node.target] if hasattr(node, "target") else [])
        for t in targets:
            if isinstance(t, ast.Name) and t.id == name:
                try:
                    return ast.literal_eval(node.value)
                except ValueError:
                    return None
    return None


def _code_only(src: str) -> str:
    """모듈 독스트링을 뺀 소스. **"안 만들었다"고 적은 문장이 위반으로 잡히는 것**을 막는다 —
    test_clip_playback.py 에서 실제로 그렇게 잡혔다(D-310 의 이웃 사례)."""
    tree = ast.parse(src)
    doc = ast.get_docstring(tree, clean=False)
    q = chr(34) * 3
    return src.replace(q + doc + q, "", 1) if doc else src


def check(juso_src: str, tests_src: str) -> list[str]:
    problems: list[str] = []
    value = literal(juso_src, "JUSO_REVERSE_SUPPORTED")
    if value is None:
        return ["JUSO_REVERSE_SUPPORTED 상수가 없다 — 방향 잠금이 통째로 사라졌다 (D-318)"]
    if value not in VALID:
        problems.append(f"JUSO_REVERSE_SUPPORTED='{value}' 는 열거 밖이다 {VALID} — "
                        f"오타는 새 값이 아니다")
    reason = literal(juso_src, "JUSO_REVERSE_UNKNOWN_REASON")
    body = _code_only(juso_src)

    if value == "unknown":
        if not (isinstance(reason, str) and len(reason.strip()) >= MIN_REASON):
            problems.append(
                "'unknown' 인데 사유가 없거나 빈약하다 — 왜 아직 못 물어봤는지 적는다. "
                "사유 없는 unknown 은 '아직' 인지 '영영' 인지 구별되지 않는다 (D-264)")
        found = [t for t in HTTP_TOKENS if t in body]
        if found:
            problems.append(
                f"'unknown' 인데 HTTP 구현이 있다: {found}. 방향도 모르는 채로 파서를 쓰면 "
                f"첫 실호출에서 전부 재작업이다 (D-280 · D-318)")
    elif value == "yes":
        if f"def {SCHEMA_SNAPSHOT_TEST}" not in tests_src:
            problems.append(
                f"'yes' 인데 {SCHEMA_SNAPSHOT_TEST} 가 없다 — '준다'는 말은 시험을 부른다. "
                f"실측한 응답 모양을 박지 않으면 다음에 바뀌어도 아무도 모른다 (D-315 판 고정)")
    elif value == "no":
        if not (isinstance(reason, str) and len(reason.strip()) >= MIN_REASON):
            problems.append(
                "'no' 인데 사유가 비었다 — **어느 응답을 보고 그렇게 판정했는지**를 적는다. "
                "자원을 버리는 판정이므로 근거가 남아야 한다 (D-316)")
    return problems


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — ★ 첫 fixture 가 **이 도구를 태어나게 한 표본**이다 (D-310)
# ═══════════════════════════════════════════════════════════════════════════
_REASON = ("승인키가 이 환경에 없어 실호출을 못 했다. 문서로 안 것을 계정에서 본 것으로 "
           "등재하지 않는다(D-316). 해소는 키를 환경변수에 넣고 프로브 1회.")
_UNKNOWN_OK = ('JUSO_REVERSE_SUPPORTED = "unknown"' + chr(10)
               + f'JUSO_REVERSE_UNKNOWN_REASON = "{_REASON}"' + chr(10))
#: ★ 출생 표본 — "방향도 모르는데 어댑터를 만들 뻔한" 바로 그 모양.
_BIRTH_SAMPLE = _UNKNOWN_OK + "import requests" + chr(10) + "def lookup(x):" + chr(10) + "    return requests.get(x)" + chr(10)
_UNKNOWN_NO_REASON = 'JUSO_REVERSE_SUPPORTED = "unknown"' + chr(10)
_YES = 'JUSO_REVERSE_SUPPORTED = "yes"' + chr(10)
_NO_OK = ('JUSO_REVERSE_SUPPORTED = "no"' + chr(10)
           + f'JUSO_REVERSE_UNKNOWN_REASON = "{_REASON}"' + chr(10))
_BAD_VALUE = 'JUSO_REVERSE_SUPPORTED = "maybe"' + chr(10)
_TESTS_OK = f"def {SCHEMA_SNAPSHOT_TEST}(self):" + chr(10) + "    pass" + chr(10)
_TESTS_NONE = "def test_other(self):" + chr(10) + "    pass" + chr(10)


def self_test() -> int:
    cases = (
        ("★ 출생 표본 — unknown 인데 HTTP 구현이 있다", _BIRTH_SAMPLE, _TESTS_NONE, True),
        ("사유 있는 unknown 은 안 잡는다", _UNKNOWN_OK, _TESTS_NONE, False),
        ("사유 없는 unknown 을 잡는다", _UNKNOWN_NO_REASON, _TESTS_NONE, True),
        ("yes 인데 스냅샷 시험이 없으면 잡는다", _YES, _TESTS_NONE, True),
        ("yes + 스냅샷 시험이면 안 잡는다", _YES, _TESTS_OK, False),
        ("사유 있는 no 는 안 잡는다", _NO_OK, _TESTS_NONE, False),
        ("열거 밖 값을 잡는다", _BAD_VALUE, _TESTS_OK, True),
    )
    bad = 0
    for label, jsrc, tsrc, should_fail in cases:
        problems = check(jsrc, tsrc)
        ok = bool(problems) == should_fail
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1
            print(f"        실제: {problems}")
    if bad:
        print(f"[JUSODIR] 자기시험 {bad}건 실패 — 이 판정기는 눈이 멀었다")
        return 1
    print(f"[JUSODIR] 자기시험 {len(cases)}건 통과 (양성 4 · 음성 3 · 출생 표본 포함)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not JUSO.is_file():
        print(f"[JUSODIR] juso 어댑터가 없다: {JUSO} — 판정할 수 없으므로 멈춘다")
        return 1
    if self_test() != 0:
        return 1

    juso_src = JUSO.read_text(encoding="utf-8")
    tests_src = TESTS.read_text(encoding="utf-8") if TESTS.is_file() else ""
    problems = check(juso_src, tests_src)
    value = literal(juso_src, "JUSO_REVERSE_SUPPORTED")
    print(f"[JUSODIR] 검사 1건 · JUSO_REVERSE_SUPPORTED={value!r} "
          f"(열거 {VALID} · 술어=사유 실재 + HTTP 구현 부재 + 스냅샷 시험 실재)")
    if problems:
        print("[JUSODIR] D-318 위반")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[JUSODIR] 통과 — 방향을 모르는 채로 어댑터를 만들지 않았다")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        measured=("주소 역변환을 **할 수 있다고 적은 것**과 구현이 갈리는가 — 선언값 **분모 %d종**"
               "(%s) · HTTP 구현 표지 %d종을 소스 전수에 건다"
               % (len(VALID), " | ".join(sorted(VALID)), len(HTTP_TOKENS))),
    )
    sys.exit(main())
