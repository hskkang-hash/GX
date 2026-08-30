#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""㉠ 호출 없음 314건을 **가른다** — 「고칠 목록」이 아니라 「가를 목록」이다 (D-388).

D-377 이 센 세 술어 중 ㉠(호출 없음)은 **큰 수 하나**로 남아 있었다. 314 를 그대로 두면
그 수는 아무 일도 하지 않는다 — 켤 것과 지울 것과 원래 그런 것이 한 칸에 있기 때문이다.

    ㉮ 켜야 할 것   만들어졌고 쓸모가 있는데 배선이 없다.        **오늘의 자산**
    ㉯ 지워야 할 것 대체되었거나 아무도 안 쓰는 죽은 코드.        **오늘의 빚**
    ㉰ 정상         유틸·프레임워크 훅·CLI·문자열 배선.          잠든 것이 아니다
    ? 판정 불가     위 셋 중 어느 것이라고 **말할 근거가 없다**

★ 넷째 칸이 있는 이유 (D-290 3값 · D-301):
  「모르는 것」을 셋 중 하나에 밀어 넣으면 그 수는 **추측이 실측 행세**를 하게 된다.
  ㉮ 목록은 사람이 켤 순서를 정하는 데 쓰이고, ㉯ 목록은 언젠가 지우는 데 쓰인다 —
  둘 다 틀리면 값이 비싸다. 그래서 근거가 없으면 **모른다고 적는다.**

★ 이 도구는 **한 건도 지우지 않는다** (D-388). 가르기만 한다. 지우는 것은 되돌리기
  어렵고, 지우기 전에 **분류의 정확도를 먼저 봐야 한다.**

무엇을 근거로 가르나 — 규칙마다 이름이 있고, 출력이 그 이름을 말한다
--------------------------------------------------------------------
  ㉰ cli        `management/commands/` 아래이거나 `__main__` 가드가 있다 — CLI 가 부른다
  ㉰ server-hook `gunicorn.conf.py`·`wsgi.py` 처럼 **서버가 이름으로 부르는 파일**이다
  ㉰ test-file  `test.py`·`tests.py` — ㉠ 판정기의 시험 판별이 못 걸러 낸 시험 파일이다
  ㉰ method     **살아 있는 클래스의 메서드**다 (그 클래스를 운영 코드가 쓴다).
                메서드는 클래스의 표면이고, 안 불리는 표면이 있는 것은 정상이다
  ㉰ dynamic    이름이 **.py 밖**(yaml·json·cfg·compose)에 적혀 있다 — 문자열로 배선된다
  ㉯ deprecated 이름이나 바로 위 주석·독스트링이 **폐기를 말한다**
  ㉯ orphan     운영도 시험도 부르지 않고, **그 모듈을 아무도 import 하지 않는다**
  ㉮ live       모듈은 운영이 import 하는데 **그 함수만 아무도 안 부른다** — 자산이 잠들었다
  ?  test-only  **시험만 부른다.** 운영에서 죽은 것은 맞으나, 시험용 발판인지
                배선이 빠진 자산인지는 이 도구가 못 가른다 — 사람이 본다

    python scripts/classify_dormant.py                 # 네 칸 건수
    python scripts/classify_dormant.py --list ㉮       # 한 칸의 목록
    python scripts/classify_dormant.py --json PATH     # 증거 파일로
    python scripts/classify_dormant.py --self-test     # 양성·음성 대조 (D-277)

⚠ 이 도구는 `verify_dormant.py` 가 센 **그 목록**을 가른다. 두 벌로 세면 두 수가 갈라진다.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_dormant import (  # noqa: E402  — 같은 눈으로 센다 (D-286)
    BACKEND,
    FORBIDDEN_APPS,
    ROOT,
    _app_of_label,
    _is_test,
    _rel,
    audit_uncalled,
    iter_py,
    parse_all,
)

EXIT_OK, EXIT_FAIL = 0, 1

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

KEEP, DROP, NORMAL, UNKNOWN = "㉮켜야", "㉯지워야", "㉰정상", "?판정불가"

#: 폐기를 말하는 표. **이름과 글 둘 다 본다** — 이름만 보면 `handle_old_format` 처럼
#: 옛 형식을 다루는 살아 있는 함수를 지울 것으로 잘못 넣는다.
_DEPRECATED_NAME = re.compile(r"(_old|_v1|_bak|_backup|_legacy|_deprecated|_tmp|_temp)$", re.I)
_DEPRECATED_TEXT = re.compile(
    r"(deprecated|obsolete|no longer used|더\s*이상\s*(안|사용)|폐기|사용하지\s*않|"
    r"쓰지\s*않|대체됨|replaced by)", re.I)

#: 장고·셀러리가 **이름으로** 찾는 모듈. 아무도 import 하지 않아도 살아 있다.
_MAGIC_MODULES = {
    "urls", "apps", "models", "admin", "tasks", "signals", "settings", "serializers",
    "schemas", "api", "views", "forms", "filters", "permissions", "middleware",
    "wsgi", "asgi", "celery", "__init__", "conftest", "routing", "consumers",
}

#: **서버·러너가 이름으로 부르는 파일.** 아무도 import 하지 않아도 그 안의 함수는 불린다.
#: ★ 1차판은 `gunicorn.conf.py` 의 훅 아홉(`post_fork`·`worker_exit`…)을 **「지워야 할 것」**
#:   으로 넣었다. 지웠으면 워커 수명주기 훅이 통째로 사라진다 — 이 도구가 낼 수 있는
#:   가장 비싼 오답이라, 규칙을 하나 더 두고 자기시험에 표본으로 박았다 (D-310 · D-350).
_SERVER_HOOK_FILES = ("gunicorn.conf.py", "wsgi.py", "asgi.py", "manage.py", "conftest.py")
#: `verify_dormant._is_test` 는 `tests/` 와 `test_*.py` 만 시험으로 본다 — `test.py`·`tests.py`
#: 는 안 걸린다 [실측]. 그 틈을 **여기서 메우되 래칫은 건드리지 않는다**(기준선은 줄기만 한다).
_TEST_FILENAMES = ("test.py", "tests.py")

#: 이름을 문자열로 들고 있을 수 있는 **배선 자리**. 여기 적혀 있으면 문자열로 이어진 것이다.
#: ★ 1차판은 저장소 전체의 `*.md`·`*.json` 을 읽었고, 그래서 **우리 증거 파일이 적어 둔
#:   함수 이름**(dormant.json·decisions.yaml)이 「배선」으로 잡혔다 — 80건이 통째로
#:   가짜였다. 문서가 이름을 적은 것은 배선이 아니다. 판정기를 먼저 의심한 자리다(D-350).
_WIRING_ROOTS = ("backend", "nginx", ".")
_NONPY_GLOBS = ("*.yaml", "*.yml", "*.json", "*.cfg", "*.ini", "*.toml", "*.env*")
#: 배선이 아니라 **우리가 그 이름을 적은 자리**. 여기서 읽으면 자기가 쓴 것을 근거로 삼는다.
_NOT_WIRING = ("docs", "node_modules", ".git", "__pycache__", "dist", "build",
               "tests", "migrations")


# ---------------------------------------------------------------------------
# 정의 자리의 성질 — 메서드인가 · CLI 인가 · 폐기라고 적혀 있나
# ---------------------------------------------------------------------------
def collect_facts(trees: dict[Path, ast.Module]) -> dict:
    """라벨(`파일::이름`)마다 **가르는 데 필요한 사실만** 모은다."""
    facts: dict[str, dict] = {}
    class_of: dict[str, str] = {}
    module_defs: dict[str, set[str]] = defaultdict(set)

    for path, tree in trees.items():
        if _is_test(path):
            continue
        rel = _rel(path)
        src = path.read_text(encoding="utf-8", errors="replace")
        module_doc = ast.get_docstring(tree) or ""
        has_main = "__main__" in src
        is_command = "management/commands/" in rel
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        class_of[f"{rel}::{sub.name}"] = node.name
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            label = f"{rel}::{node.name}"
            own_doc = ast.get_docstring(node) or ""
            facts[label] = {
                "file": rel,
                "name": node.name,
                "module": Path(rel).stem,
                "is_command": is_command,
                "has_main": has_main,
                "deprecated": bool(
                    _DEPRECATED_NAME.search(node.name)
                    or _DEPRECATED_TEXT.search(own_doc)
                    or (_DEPRECATED_TEXT.search(module_doc) and not own_doc)),
            }
            module_defs[rel].add(node.name)

    for label, cls in class_of.items():
        if label in facts:
            facts[label]["class"] = cls
    return facts


def module_import_index(trees: dict[Path, ast.Module]) -> set[str]:
    """운영 코드가 **import 하는 모듈 이름**(마지막 마디)의 집합.

    점 경로를 통째로 맞추지 않고 마지막 마디로 본다 — `from common import ops_tasks` 와
    `import backend.common.ops_tasks` 를 같은 것으로 세기 위해서다. **놓치는 쪽으로**
    틀린다(같은 이름의 다른 모듈을 살아 있다고 볼 수 있다) — 죽었다고 잘못 말하는 것보다
    낫다. 여기서 잘못 「죽었다」고 말하면 사람이 멀쩡한 코드를 지운다.
    """
    seen: set[str] = set()
    for path, tree in trees.items():
        if _is_test(path):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    seen.update(a.name.split("."))
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    seen.add(a.name)
                if node.module:
                    seen.update(node.module.split("."))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "." in node.value or "/" in node.value:
                    seen.update(re.split(r"[./]", node.value))
    return seen


def class_alive_index(trees: dict[Path, ast.Module]) -> set[str]:
    """운영 코드가 **자기 파일 밖에서** 쓰는 클래스 이름.

    ★ 자기 파일 안의 등장까지 세면 「정의했으니 살아 있다」가 되어 규칙이 아무것도
      가르지 못한다. 밖에서 쓰이는 것만 세는 쪽이 **놓치는 방향**이다 — 살아 있는
      클래스를 죽었다고 보는 일이 생기지만, 그 결과는 「판정 불가」이지 삭제가 아니다.
    """
    defined: dict[str, str] = {}
    used: set[str] = set()
    for path, tree in trees.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                defined[node.name] = _rel(path)
    for path, tree in trees.items():
        if _is_test(path):
            continue
        here = _rel(path)
        defined_here = {k for k, v in defined.items() if v == here}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in defined and node.id not in defined_here:
                used.add(node.id)
            elif isinstance(node, ast.Attribute) and node.attr in defined and node.attr not in defined_here:
                used.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                tail = node.value.rsplit(".", 1)[-1]
                if tail in defined and tail not in defined_here:
                    used.add(tail)
    return used


def nonpy_names(root: Path) -> set[str]:
    """`.py` 밖의 **배선 파일**에 적힌 낱말. 문서는 읽지 않는다 (위 주석의 사유)."""
    words: set[str] = set()
    for pattern in _NONPY_GLOBS:
        for p in root.rglob(pattern):
            if set(p.parts) & set(_NOT_WIRING):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            words.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", text))
    return words


# ---------------------------------------------------------------------------
# 가르기 — 규칙은 **차례가 있다.** 앞의 규칙이 먼저 잡는다
# ---------------------------------------------------------------------------
def classify(label: str, facts: dict, *, imported: set[str], classes: set[str],
             wired_by_string: set[str], test_refs: int) -> tuple[str, str]:
    f = facts.get(label)
    if f is None:
        return UNKNOWN, "no-facts"                 # 목록에는 있는데 사실을 못 모았다
    if f["deprecated"]:
        return DROP, "deprecated"          # ★ 폐기가 먼저다 — 폐기된 메서드는 빚이지 정상이 아니다
    if f["is_command"] or f["has_main"]:
        return NORMAL, "cli"
    if f["file"].endswith(_SERVER_HOOK_FILES):
        return NORMAL, "server-hook"
    if f["file"].endswith(_TEST_FILENAMES):
        return NORMAL, "test-file"
    cls = f.get("class")
    if cls and cls in classes:
        return NORMAL, "method"
    if f["name"] in wired_by_string:
        return NORMAL, "dynamic"
    module_live = f["module"] in imported or f["module"] in _MAGIC_MODULES
    if test_refs > 0:
        return UNKNOWN, "test-only"
    if not module_live:
        return DROP, "orphan"
    return KEEP, "live"


def run(*, want_json: str | None, want_list: str | None) -> int:
    trees = parse_all(iter_py(BACKEND))
    if not trees:
        print("[CLASSIFY] backend 에서 .py 를 한 건도 못 읽었다 — 0건을 통과로 읽지 않는다 (D-301)")
        return EXIT_FAIL

    _, dormant, counts = audit_uncalled(trees)
    facts = collect_facts(trees)
    imported = module_import_index(trees)
    classes = class_alive_index(trees)
    wired = nonpy_names(ROOT)

    buckets: dict[str, list[tuple[str, str]]] = defaultdict(list)
    forb: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for label in dormant:
        _, t = counts.get(label, (0, 0))
        bucket, rule = classify(label, facts, imported=imported, classes=classes,
                                wired_by_string=wired, test_refs=t)
        target = forb if _app_of_label(label) in FORBIDDEN_APPS else buckets
        target[bucket].append((label, rule))

    total = sum(len(v) for v in buckets.values()) + sum(len(v) for v in forb.values())
    print(f"[CLASSIFY] [입력] ㉠ 호출 없음 {total}건 — `verify_dormant.py` 가 센 그 목록을 가른다")
    print(f"[CLASSIFY] 우리 관할 {sum(len(v) for v in buckets.values())}건 · "
          f"§0.4 금지구역 {sum(len(v) for v in forb.values())}건(가르되 **우리가 못 고친다**)")
    for name in (KEEP, DROP, NORMAL, UNKNOWN):
        rules = defaultdict(int)
        for _, rule in buckets[name]:
            rules[rule] += 1
        detail = " · ".join(f"{r} {n}" for r, n in sorted(rules.items()))
        print(f"[CLASSIFY]   {name:8} **{len(buckets[name]):3}건**   {detail}")
    print(f"[CLASSIFY] ★ 이 도구는 **한 건도 지우지 않는다** — 가르기만 한다 (D-388)")

    if want_list:
        for name in buckets:
            if want_list in name:
                print(f"\n-- {name} ({len(buckets[name])}건)")
                for label, rule in sorted(buckets[name]):
                    print(f"  {rule:10} {label}")

    if want_json:
        out = Path(want_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "source": "scripts/verify_dormant.py :: 호출 없음(㉠)",
            "total": total,
            "ours": {k: [{"label": lb, "rule": r} for lb, r in sorted(v)]
                     for k, v in buckets.items()},
            "forbidden_zone": {k: [lb for lb, _ in sorted(v)] for k, v in forb.items()},
            "note": "한 건도 지우지 않았다 (D-388). 가르기만 한 결과다.",
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[CLASSIFY] 증거 기록: {out}")
    return EXIT_OK


# ---------------------------------------------------------------------------
# 자기시험 — **양성과 음성 둘 다** (D-277). 규칙마다 표본을 하나씩 박는다 (D-310)
# ---------------------------------------------------------------------------
_FIXTURES = {
    # 규칙 이름 -> (라벨, 사실, 시험참조수, 기대 칸)
    "cli":        ({"file": "backend/x/management/commands/y.py", "name": "handle",
                    "module": "y", "is_command": True, "has_main": False,
                    "deprecated": False}, 0, NORMAL),
    "method":     ({"file": "backend/x/s.py", "name": "run", "module": "s",
                    "is_command": False, "has_main": False, "deprecated": False,
                    "class": "LiveClass"}, 0, NORMAL),
    "dynamic":    ({"file": "backend/x/s.py", "name": "wired_by_yaml", "module": "s",
                    "is_command": False, "has_main": False, "deprecated": False}, 0, NORMAL),
    "deprecated": ({"file": "backend/x/s.py", "name": "handler_old", "module": "s",
                    "is_command": False, "has_main": False, "deprecated": True}, 0, DROP),
    "server-hook": ({"file": "backend/gunicorn.conf.py", "name": "post_fork",
                     "module": "gunicorn.conf", "is_command": False, "has_main": False,
                     "deprecated": False}, 0, NORMAL),
    "test-file":  ({"file": "backend/devices/tests.py", "name": "setUp",
                    "module": "tests", "is_command": False, "has_main": False,
                    "deprecated": False}, 0, NORMAL),
    "orphan":     ({"file": "backend/x/nobody.py", "name": "gone", "module": "nobody",
                    "is_command": False, "has_main": False, "deprecated": False}, 0, DROP),
    "live":       ({"file": "backend/x/s.py", "name": "asset", "module": "s",
                    "is_command": False, "has_main": False, "deprecated": False}, 0, KEEP),
    "test-only":  ({"file": "backend/x/s.py", "name": "only_tests", "module": "s",
                    "is_command": False, "has_main": False, "deprecated": False}, 3, UNKNOWN),
}


def self_test() -> int:
    """규칙 일곱에 표본 일곱. **하나라도 어긋나면 판정을 시작하지 않는다** (D-350)."""
    bad = []
    for rule, (fact, trefs, expect) in _FIXTURES.items():
        label = f"{fact['file']}::{fact['name']}"
        got, got_rule = classify(label, {label: fact},
                                 imported={"s"}, classes={"LiveClass"},
                                 wired_by_string={"wired_by_yaml"}, test_refs=trefs)
        if got != expect or got_rule != rule:
            bad.append(f"{rule}: {got}/{got_rule} (기대 {expect}/{rule})")
    # 음성 갈래 — **사실이 없으면 모른다고 말해야 한다.** 조용히 한 칸에 넣으면 안 된다
    got, got_rule = classify("backend/x/s.py::ghost", {}, imported=set(), classes=set(),
                             wired_by_string=set(), test_refs=0)
    if (got, got_rule) != (UNKNOWN, "no-facts"):
        bad.append(f"사실 없음: {got}/{got_rule} (기대 {UNKNOWN}/no-facts)")
    if bad:
        print("[CLASSIFY] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print(f"    {b}")
        return EXIT_FAIL
    print(f"[CLASSIFY] 자기시험 통과 — 규칙 {len(_FIXTURES)}종 양성 + 음성 1종")
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="㉠ 호출 없음 가르기 (D-388)")
    ap.add_argument("--list", metavar="칸", help="㉮ / ㉯ / ㉰ / ? 중 하나")
    ap.add_argument("--json", metavar="PATH")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:            # 판정 전에 판정기부터 (D-277 · D-350)
        return EXIT_FAIL
    return run(want_json=args.json, want_list=args.list)


if __name__ == "__main__":
    sys.exit(main())
