#!/usr/bin/env python
"""표 ② 자격증명 게이트 — **무엇인지 모르는 키를 기능 코드가 쓰지 못하게 한다** (D-328).

왜 이 게이트가 태어났나 — 2026-09-05~06 juso 사건
--------------------------------------------------
대표께서 승인키 2건을 발급하셨다. 우리는 「키가 있는가/없는가」만 물었고
**「어떤 키인가」는 묻지 않았다.** 받은 것은 **도로명주소 팝업 API** 키 —
브라우저에 주소검색 창을 띄우는 UI 위젯이고 서버끼리 쓰는 조회 API 조차 아니다.
그 사실을 하루 뒤에 알았다. 그 하루가 `present`(파일에 있다)와
`typed`(무슨 API 인지 안다) 사이다.

    absent → present → **typed** → verified → rotated

그래서 술어는 「있는가」가 아니라 **「무엇인지 아는가」**다:

    capability 가 비었거나 상태가 typed 미만인 이름을 **기능 코드가 참조하면 exit 1.**

probe·scan 은 예외다 — **그것들이 typed 로 올리는 일을 한다.** 조사하는 코드까지 막으면
상태를 올릴 방법이 없어지고, 그러면 게이트가 자기가 요구하는 것을 불가능하게 만든다.

    python scripts/verify_credential_store.py          # 판정
    python scripts/verify_credential_store.py --list   # 표 ② 를 사람이 읽는 모양으로
    python scripts/verify_credential_store.py --self-test

★ 출생 표본 (D-310)
-------------------
자기시험 첫 갈래가 **「팝업 키를 기능 코드가 읽는다」**이다. 그것이 이 게이트가
막으려던 바로 그 사건이고, 거기서 초록이 나오면 이 도구는 아무것도 아니다.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
SCRIPTS = ROOT / "scripts"
TABLE = BACKEND / "kernels" / "k5_trust" / "credentials.py"

STATUS_ORDER = ("absent", "present", "typed", "verified", "rotated")
MIN_USABLE = "typed"

SKIP_DIRS = {"__pycache__", "migrations", "node_modules", ".venv", "tests", "fonts"}

#: **표 자신**은 이름을 적는 자리다 — 여기서 잡으면 선언을 할 수 없다.
DECLARING_FILES = {
    "backend/kernels/k5_trust/credentials.py",
    "backend/kernels/k5_trust/services.py",
    "backend/kernels/k5_trust/__init__.py",
}

#: 조사·측정 코드는 예외다 — **그것들이 상태를 올리는 일을 한다.**
PROBE_PREFIXES = ("probe_", "scan_", "verify_", "check_", "dump_", "gen_")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def table() -> dict[str, dict]:
    """표 ②를 **import 하지 않고** AST 로 읽는다 — 이 게이트는 Django 없이 돈다.

    ⚠ `declared_status=TYPED` 처럼 **모듈 상수로 적힌 값**이 있다. 리터럴만 읽으면
      그 항목이 통째로 사라지고, 사라진 항목은 게이트가 못 본다 —
      「검사 못함 ≠ 0건 검사」(D-301). 그래서 모듈 최상위 문자열 상수를 먼저 모은다.
    """
    src = TABLE.read_text(encoding="utf-8")
    tree = ast.parse(src)

    consts: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    consts[t.id] = node.value.value

    def value(node):
        if isinstance(node, ast.Name):
            if node.id not in consts:
                raise ValueError(f"모듈 상수 {node.id} 를 못 읽었다")
            return consts[node.id]
        return ast.literal_eval(node)

    out: dict[str, dict] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "id", "") != "CredentialDef":
            continue
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        try:
            name = value(kw["name"])
            out[name] = {
                "env_var": value(kw["env_var"]),
                "api_type": value(kw["api_type"]),
                "capability": value(kw["capability"]),
                "is_secret": value(kw["is_secret"]),
                "declared_status": value(kw["declared_status"]),
                "intended_use": value(kw["intended_use"]),
            }
        except (KeyError, ValueError):
            continue
    return out


def at_least(status: str, floor: str) -> bool:
    order = {s: i for i, s in enumerate(STATUS_ORDER)}
    if status == "rotated":
        status = "verified"
    return order.get(status, -1) >= order.get(floor, 99)


def usable(spec: dict) -> bool:
    """이 이름을 기능 코드가 써도 되는가. **두 조건 모두**여야 참이다."""
    return (at_least(spec["declared_status"], MIN_USABLE)
            and bool((spec["capability"] or "").strip()))


def judge_file(rel: str, src: str, defs: dict[str, dict]) -> list[str]:
    """파일 하나. **순수 함수다** — 자기시험이 겨누는 과녁이 여기다 (D-277).

    술어를 좁힌 자리를 적어 둔다 (D-326: 좁힐 때마다 반대편이 열린다):
      · 주석·독스트링 안의 언급은 참조가 아니다 — **적어 두는 것**이 곧 표를 만드는 일이다
      · 표 자신과 조사 코드는 예외
    """
    if rel in DECLARING_FILES:
        return []
    base = rel.rsplit("/", 1)[-1]
    if rel.startswith("scripts/") and base.startswith(PROBE_PREFIXES):
        return []

    # 주석·독스트링을 지운다 — 남는 것이 **코드가 실제로 만지는 이름**이다.
    try:
        tree = ast.parse(src)
        stripped = _without_strings_and_comments(src, tree)
    except SyntaxError:
        stripped = re.sub(r"#.*", "", src)

    problems = []
    for name, spec in defs.items():
        if usable(spec):
            continue
        for token in {name, spec["env_var"]}:
            if re.search(rf"\b{re.escape(token)}\b", stripped):
                problems.append(
                    f"{rel}: {token} 를 읽는다 — 상태 '{spec['declared_status']}' · "
                    f"capability {'비어 있음' if not spec['capability'].strip() else '기재됨'}. "
                    f"「있다」와 「무엇인지 안다」는 다른 사실이다(D-328). "
                    f"표 ②의 상태를 typed 이상으로 올리고 capability 를 적은 뒤에 붙여라")
                break
    return problems


def _without_strings_and_comments(src: str, tree: ast.Module) -> str:
    """문자열 리터럴과 주석을 지운 소스. **문자열을 통째로 지우지 않는다** —

    `os.environ["JUSO_POPUP_KEY_1"]` 은 문자열이지만 **읽는 행위**다.
    지우는 것은 독스트링(문(statement)으로 홀로 선 문자열)뿐이다.
    ★ D-326 — `verify_external_sources` 에서 이 술어를 세 번 좁혔고 세 번 다
      반대편으로 넘어갔다. 그래서 자기시험이 양쪽을 함께 잰다.
    """
    lines = src.split("\n")
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for i in range(node.lineno - 1, min(node.end_lineno, len(lines))):
                lines[i] = ""
    return re.sub(r"#.*", "", "\n".join(lines))


def targets():
    """(상대경로, 소스) — 기능 코드 전수. 시험은 뺀다(표본이지 사용이 아니다)."""
    out = []
    for root, prefix in ((BACKEND, "backend"), (SCRIPTS, "scripts")):
        for path in sorted(root.rglob("*.py")):
            parts = path.relative_to(root).parts
            if any(p in SKIP_DIRS for p in parts):
                continue
            out.append((f"{prefix}/" + "/".join(parts),
                        path.read_text(encoding="utf-8", errors="replace")))
    return out


def self_test() -> int:
    """★ 출생 표본 — 팝업 키를 기능 코드가 읽는다."""
    unusable = {"JUSO_POPUP_KEY_1": {
        "env_var": "JUSO_POPUP_KEY_1", "capability": "", "declared_status": "present",
        "api_type": "도로명주소 팝업 API", "is_secret": False, "intended_use": ""}}
    usable_defs = {"JUSO_POPUP_KEY_1": {
        "env_var": "JUSO_POPUP_KEY_1", "capability": "브라우저 주소검색 UI",
        "declared_status": "typed", "api_type": "도로명주소 팝업 API",
        "is_secret": False, "intended_use": ""}}

    cases = (
        ("★ 출생표본 capability 빈 키를 기능 코드가 읽으면 잡는다",
         "backend/apps/x.py", 'key = os.environ["JUSO_POPUP_KEY_1"]\n', unusable, True),
        ("상태가 present 여도 capability 만으로는 못 지나간다",
         "backend/apps/x.py", "k = JUSO_POPUP_KEY_1\n",
         {"JUSO_POPUP_KEY_1": {**unusable["JUSO_POPUP_KEY_1"],
                               "capability": "브라우저 UI"}}, True),
        ("typed + capability 면 안 잡는다",
         "backend/apps/x.py", 'key = os.environ["JUSO_POPUP_KEY_1"]\n',
         usable_defs, False),
        # ─ 좁힌 쪽 (음성)
        ("독스트링 안의 언급은 참조가 아니다",
         "backend/apps/x.py", '"""JUSO_POPUP_KEY_1 은 팝업 키다."""\n', unusable, False),
        ("주석 안의 언급도 참조가 아니다",
         "backend/apps/x.py", "# JUSO_POPUP_KEY_1 은 팝업 키다\n", unusable, False),
        ("표 자신은 예외다",
         "backend/kernels/k5_trust/credentials.py",
         'name="JUSO_POPUP_KEY_1"\n', unusable, False),
        ("probe 는 예외다 — 그것이 typed 로 올리는 일을 한다",
         "scripts/probe_juso_direction.py",
         'os.environ["JUSO_POPUP_KEY_1"]\n', unusable, False),
        # ─ 좁히면서 놓치면 안 되는 쪽 (양성) — D-326
        ("★ 문자열 안이어도 **읽는 행위**면 잡는다",
         "backend/apps/x.py", 'v = config.get("JUSO_POPUP_KEY_1")\n', unusable, True),
        ("이름이 부분 문자열로 겹치는 것은 안 잡는다",
         "backend/apps/x.py", "MY_JUSO_POPUP_KEY_1_BACKUP = 1\n", unusable, False),
    )
    bad = 0
    for label, rel, src, defs, should_fail in cases:
        got = bool(judge_file(rel, src, defs))
        ok = got == should_fail
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1
    # 표를 실제로 읽는가 — 판정만 맞고 표를 못 읽으면 대상은 늘 0건이다
    parsed = table() if TABLE.is_file() else {}
    ok_parse = len(parsed) > 0
    print(f"  {'OK  ' if ok_parse else 'FAIL'} 표 ②를 읽는다 ({len(parsed)}건)")
    if not ok_parse:
        bad += 1
    if bad:
        print(f"[CRED] 자기시험 {bad}건 실패 — 이 게이트는 눈이 멀었다")
        return 1
    print(f"[CRED] 자기시험 {len(cases) + 1}건 통과 (양성 3 · 음성 6 · 출생 표본 포함)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != 0:
        return 1
    if not TABLE.is_file():
        print(f"[CRED] 표 ②가 없다: {TABLE.relative_to(ROOT)} — 판정 불가")
        return 1

    defs = table()
    files = targets()
    blocked = [n for n, s in defs.items() if not usable(s)]

    print(f"[CRED] 표 ② **{len(defs)}건** · 기능 코드가 쓸 수 없는 이름 **{len(blocked)}건** "
          f"(모수={len(files)}파일 · 술어=capability 기재 + 상태 typed 이상)")
    if not defs:
        print("[CRED] 표가 0건이다 — 못 읽은 것인지 빈 것인지 구별할 수 없다 (D-301)")
        return 1

    if args.list:
        for name, s in sorted(defs.items()):
            mark = "쓸 수 있음" if usable(s) else "**차단**  "
            print(f"    {mark}  {name:26} {s['declared_status']:9} "
                  f"{'공개키' if not s['is_secret'] else '비밀키'}  {s['api_type']}")

    problems: list[str] = []
    for rel, src in files:
        problems += judge_file(rel, src, defs)

    if problems:
        print("[CRED] 위반 — 무엇인지 모르는 키를 기능 코드가 만진다")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[CRED] 통과 — capability 없는 키를 만지는 기능 코드가 없다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
