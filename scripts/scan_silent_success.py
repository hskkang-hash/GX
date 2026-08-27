#!/usr/bin/env python
"""**조용한 성공** 전수 조사 — 본문 없이 True/None 을 내는 공개 함수 (D-284 (3)).

무엇을 찾나
-----------
    D-284: *"구현이 없는 함수는 성공을 반환하지 않는다. 빈 본문은 NotImplementedError 를
    던진다. **조용한 성공이 가장 나쁘다** — 부르는 쪽이 '저장됐다'고 믿고 다음을 쌓는다."*

발단은 `media_data/services/media_data_detect_service.py:detect_and_save` 였다.
독스트링은 "저장한다"이고 본문은 `created_records = []` 한 줄뿐이었으며 `return True` 로
끝났다. 부르는 쪽(뷰)은 그 `True` 를 보고 200 "Detection completed successfully" 를 냈다.

이 스크립트는 **1회 조사**다 (D-284 (3) 이 요구한 목록). 게이트가 아니다 —
    · 이 저장소에는 이미 빚이 있고, 게이트로 만들면 래칫밖에 못 건다.
    · 무엇이 "빈 본문"인지는 사람이 봐야 갈린다. 기계는 후보를 좁힐 뿐이다.
그래서 **판정하지 않고 목록을 낸다.** 위험도로 줄을 세워, 사람이 읽을 순서를 정해 준다.

무엇을 "조용한 성공"으로 세나 — 술어를 먼저 적는다 (D-271)
---------------------------------------------------------
**두 가지 모양**을 센다. 처음에는 ①만 셌고, 그 술어로는 **이 조사를 하게 만든 바로 그
함수를 못 잡았다** — 착시 ④(D-277)를 제 손으로 재현한 것이라 여기 남긴다.

  ① 빈 본문      본문에서 실질 작업 문장을 걷어냈을 때 남는 것이
                 `return True` / `return None` / 암묵 None 인 것.

                     실질 작업 문장 = 대입·호출·제어흐름·예외·with·assert
                     걷어내는 것    = 독스트링 · `pass` · 주석 · **쓰이지 않는 대입**

                 "쓰이지 않는 대입"을 걷어내는 것이 핵심이다. `created_records = []` 는
                 문장이 하나 있으니 빈 본문이 아닌 것처럼 보이지만 그 변수는 **아무 데서도
                 읽히지 않는다.** 의도의 잔해를 구현으로 세면 아무것도 못 찾는다.

  ② 무조건 성공  함수의 **모든** return 이 성공을 뜻하는 상수를 낸다 —
                 `return True` 또는 `return True, <무엇이든>`.
                 즉 **실패를 낼 길이 없다.** 그러면 부르는 쪽의 실패 갈래는 죽은 코드다.

                 `detect_and_save` 가 정확히 이 모양이었다: `return True, results`.
                 뷰는 `if not success: return 400` 을 갖고 있었지만 **그 400 에는 닿을 수
                 없었다.** ①만 보면 이 함수는 "실질 작업이 있다"로 통과한다 —
                 `results = detect_media(...)` 가 있고 그 값이 읽히기 때문이다.

등급
----
    high    독스트링 **또는 이름**이 부작용을 약속하는데(저장/생성/전송/갱신/삭제…)
            본문이 비었거나 무조건 성공한다 → 부르는 쪽이 그 약속을 믿는다.
    medium  약속하는 말은 없지만 무조건 True 를 낸다
    low     본문이 비었고 None 을 낸다 (성공을 주장하지는 않는다)

    ※ 이름도 보는 이유: `save_log_file_to_minio(log_file_data): pass` 는 독스트링이
      없다. 독스트링만 보면 low 로 떨어지지만, **이름이 이미 약속이다.**

    ※ `raise NotImplementedError` / `NotImplementedYet` 로 끝나는 함수는 **세지 않는다.**
      그것이 D-284 가 요구한 **바른 모양**이다. 바른 것을 결함으로 세면 목록이 거짓이 된다.

사용법
------
    python scripts/scan_silent_success.py              # 등급순 목록
    python scripts/scan_silent_success.py --json       # 기계가 읽을 형태
    python scripts/scan_silent_success.py --self-test  # ★ 탐지기가 실제로 탐지하는지 (D-277)

종료 코드는 **언제나 0** 이다 — 조사이지 판정이 아니다. `--self-test` 만 실패 시 1.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 독스트링이 이 말을 하면 **부작용을 약속한 것**이다. 약속과 빈 본문이 만나면 high.
PROMISE_WORDS = (
    "save", "saves", "saving", "저장", "create", "creates", "생성", "insert",
    "update", "updates", "갱신", "delete", "deletes", "삭제", "send", "sends",
    "전송", "발송", "upload", "업로드", "write", "writes", "기록", "publish",
    "발행", "register", "등록", "sync", "동기화", "apply", "적용",
)

#: 훑지 않는 곳. **사유를 함께 적는다** — 조용히 빼면 모수가 거짓이 된다.
SKIP_DIRS = {
    "migrations": "마이그레이션은 Django 가 만든다 — 우리 코드가 아니다",
    "__pycache__": "산출물",
    "tests": "시험은 부작용을 약속하지 않는다",
    ".venv": "의존성",
    "node_modules": "의존성",
}


def _is_noop_return(node: ast.AST) -> str | None:
    """`return True` · `return None` · 암묵 None 인가. 아니면 None."""
    if isinstance(node, ast.Return):
        if node.value is None:
            return "None(명시)"
        if isinstance(node.value, ast.Constant):
            if node.value.value is True:
                return "True"
            if node.value.value is None:
                return "None(명시)"
    return None


def _assigned_names(stmt: ast.AST) -> set[str]:
    out: set[str] = set()
    if isinstance(stmt, ast.Assign):
        for t in stmt.targets:
            if isinstance(t, ast.Name):
                out.add(t.id)
    elif isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
        if isinstance(stmt.target, ast.Name):
            out.add(stmt.target.id)
    return out


def _read_names(fn: ast.AST, skip: ast.AST) -> set[str]:
    """`skip` 문장을 뺀 나머지에서 **읽히는** 이름."""
    out: set[str] = set()
    for node in ast.walk(fn):
        if node is skip:
            continue
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            out.add(node.id)
    return out


def _substantive(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt]:
    """실질 작업 문장만 남긴다 — 독스트링 · pass · **쓰이지 않는 대입**을 걷어낸다."""
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]                                   # 독스트링

    out: list[ast.stmt] = []
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            names = _assigned_names(stmt)
            # 대입된 이름이 함수 안 **어디서도 읽히지 않으면** 그것은 의도의 잔해다.
            if names and not (names & _read_names(fn, stmt)):
                continue
        if isinstance(stmt, ast.Return) and _is_noop_return(stmt):
            continue                                       # 반환은 따로 본다
        out.append(stmt)
    return out


def _raises_not_implemented(fn) -> bool:
    """D-284 가 요구한 **바른 모양**인가 — 그렇다면 결함으로 세지 않는다."""
    for node in ast.walk(fn):
        if isinstance(node, ast.Raise) and node.exc is not None:
            name = node.exc
            if isinstance(name, ast.Call):
                name = name.func
            text = getattr(name, "id", "") or getattr(name, "attr", "")
            if "NotImplemented" in text:
                return True
    return False


def _success_constant(node: ast.Return) -> bool:
    """이 return 이 **성공을 뜻하는 상수**를 내는가 — `True` 또는 `(True, …)`."""
    v = node.value
    if isinstance(v, ast.Constant) and v.value is True:
        return True
    if isinstance(v, ast.Tuple) and v.elts:
        first = v.elts[0]
        return isinstance(first, ast.Constant) and first.value is True
    return False


def _own_returns(fn) -> list[ast.Return]:
    """이 함수 **자신의** return 만. 안에 정의된 함수의 return 은 그 함수의 것이다."""
    out: list[ast.Return] = []

    def walk(node, top: bool):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
                                  ast.ClassDef)) and not top:
                continue
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
                                  ast.ClassDef)):
                continue
            if isinstance(child, ast.Return):
                out.append(child)
            walk(child, False)

    walk(fn, True)
    return out


def _unconditional_success(fn) -> bool:
    """실패를 낼 길이 **없는가** (② 모양).

    return 이 하나 이상 있고 그 **전부**가 성공 상수를 낸다면, 부르는 쪽의 실패 갈래는
    닿을 수 없는 죽은 코드다. `raise` 로 나가는 길은 예외이지 "실패 반환"이 아니다 —
    그것은 부르는 쪽이 `if not ok:` 로 잡는 것이 아니라 try 로 잡는 것이다.
    """
    returns = _own_returns(fn)
    return bool(returns) and all(_success_constant(r) for r in returns)


def _promise_words(fn) -> list[str]:
    """부작용을 약속하는 말 — **독스트링과 이름 양쪽**에서 찾는다.

    이름도 보는 이유: `save_log_file_to_minio(...): pass` 는 독스트링이 없다.
    독스트링만 보면 "약속한 적 없다"가 되지만, 부르는 사람이 읽는 것은 **이름**이다.
    """
    doc = (ast.get_docstring(fn) or "").lower()
    name = fn.name.lower()
    hits = [w for w in PROMISE_WORDS if w in doc]
    hits += [f"이름:{w}" for w in PROMISE_WORDS
             if w in name.split("_") or name.startswith(w + "_")]
    return hits


def _rel(path: Path) -> str:
    """저장소 기준 경로. 밖에 있으면 있는 그대로 — **예외로 죽지 않는다.**

    `--self-test` 는 임시 디렉터리에 가짜 파일을 만들어 먹인다. 그것은 ROOT 밖이고,
    `relative_to` 는 거기서 ValueError 를 던진다. 처음 이 함수 없이 짰다가
    self-test 3건이 **사유도 없이** 실패했다 — 탐지기가 아니라 대조가 죽은 것이었다.
    """
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def scan_file(path: Path) -> list[dict]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError) as exc:
        # 못 읽은 것을 "결함 0건"으로 세지 않는다 — 목록에 사실대로 넣는다.
        return [{"file": _rel(path), "func": "(파일 전체)",
                 "line": 0, "grade": "unread", "returns": "-",
                 "why": f"파싱 실패: {type(exc).__name__} — 판정하지 못했다"}]

    found: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue                                       # 비공개는 밖에서 안 부른다
        if _raises_not_implemented(node):
            continue                                       # 바른 모양

        empty_body = not _substantive(node)
        always_ok = _unconditional_success(node)
        if not empty_body and not always_ok:
            continue                                       # 두 모양 어느 쪽도 아니다

        if empty_body:
            returns = {r for r in (_is_noop_return(s) for s in _own_returns(node)) if r}
            ret = "/".join(sorted(returns)) if returns else "None(암묵)"
            shape = "빈 본문"
        else:
            ret = "True(무조건)"
            shape = "무조건 성공"

        promises = _promise_words(node)
        if promises:
            grade = "high"
            why = f"{shape} — 약속한다: {', '.join(promises[:4])}"
        elif always_ok or "True" in ret:
            grade = "medium"
            why = f"{shape} — 실패를 낼 길이 없다. 부르는 쪽의 실패 갈래는 죽은 코드다"
        else:
            grade = "low"
            why = f"{shape} — None 을 낸다 (성공을 주장하지는 않는다)"

        found.append({
            "file": _rel(path), "func": node.name, "line": node.lineno,
            "grade": grade, "returns": ret, "shape": shape, "why": why,
        })
    return found


def walk() -> list[dict]:
    out: list[dict] = []
    n_files = 0
    for path in sorted(BACKEND.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        n_files += 1
        out += scan_file(path)
    print(f"[SILENT] 훑은 파일 {n_files}개 (모수=backend/**/*.py 전수, "
          f"제외={', '.join(SKIP_DIRS)})")
    return out


def self_test() -> int:
    """★ 탐지기가 실제로 탐지하는가 (D-277).

    잡아야 할 것과 **잡으면 안 되는 것**을 함께 먹인다. 잡기만 하는 탐지기는
    전부 잡는 탐지기와 구별되지 않는다.
    """
    import tempfile

    cases = [
        ("saves_but_empty", 'def save_it():\n    """Save the thing."""\n    rows = []\n    return True\n',
         True, "독스트링이 저장을 약속하는데 본문이 잔해뿐"),
        ("true_no_promise", 'def go():\n    return True\n', True, "빈 본문 + True"),
        ("implicit_none", 'def go2():\n    """도움말."""\n', True, "빈 본문 + 암묵 None"),
        # ★ 이 대조는 처음에 `return True` 로 적었다가 ② 를 더하면서 **잡혔다.**
        #   그때 고쳐야 할 것은 탐지기가 아니라 대조였다 — 일을 하더라도 실패를 낼
        #   길이 없으면 그것이 바로 ② 다. 그래서 "일을 하고 결과로 답하는" 모양으로 바꿨다.
        ("real_work",
         'def go3():\n    """Save it."""\n    x = 1\n    print(x)\n    return bool(x)\n',
         False, "실질 작업이 있고 결과로 답한다 — 잡으면 안 된다"),
        ("used_assign", 'def go4():\n    """Save."""\n    rows = []\n    return bool(rows)\n',
         False, "대입이 읽힌다 — 잔해가 아니다"),
        ("correct_shape", 'def go5():\n    """Save it."""\n    raise NotImplementedError("아직")\n',
         False, "D-284 가 요구한 바른 모양 — 결함으로 세면 안 된다"),
        ("private", 'def _hidden():\n    return True\n', False, "비공개는 밖에서 안 부른다"),
        # ★ ② 무조건 성공 — **이 조사를 하게 만든 실제 모양이다.**
        #   처음엔 이 대조가 없었고, 그래서 탐지기가 과녁을 놓친 것을 못 봤다 (D-277).
        ("unconditional_ok",
         'def detect_and_save(d):\n    """Save results."""\n'
         '    results = detect(d)\n    return True, results\n',
         True, "실질 작업은 있지만 실패를 낼 길이 없다 — detect_and_save 의 실제 모양"),
        ("can_fail",
         'def go6(d):\n    """Save."""\n    r = detect(d)\n'
         '    if not r:\n        return False, []\n    return True, r\n',
         False, "실패를 낼 길이 있다 — 잡으면 안 된다"),
        ("named_save_pass",
         'def save_log_file_to_minio(data):\n    pass\n',
         True, "독스트링은 없지만 **이름이 약속한다**"),
    ]

    failed = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, src, want, why in cases:
            f = Path(tmp) / f"{name}.py"
            f.write_text(src, encoding="utf-8")
            try:
                got = bool(scan_file(f))
            except Exception as exc:  # noqa: BLE001
                failed.append((name, f"예외: {exc}", why))
                continue
            mark = "OK " if got == want else "실패"
            print(f"  {mark} {name:20s} 기대={'잡힘' if want else '통과'} "
                  f"실제={'잡힘' if got else '통과'}  — {why}")
            if got != want:
                failed.append((name, f"기대={want} 실제={got}", why))

    if failed:
        print(f"\n[SILENT] self-test **실패** {len(failed)}/{len(cases)} — "
              f"이 탐지기가 낸 목록은 신뢰할 수 없다 (D-277)")
        # ★ 사유를 반드시 낸다. 처음엔 이 줄이 없어서 "3건 실패"만 보이고
        #   **무엇이 왜 실패했는지 알 수 없었다** — 실패가 뒤를 가린 그 모양이다 (D-274).
        for name, detail, why in failed:
            print(f"    · {name}: {detail}  ({why})")
        return 1
    print(f"\n[SILENT] self-test 통과 {len(cases)}/{len(cases)} — "
          f"잡을 것은 잡고 안 잡을 것은 안 잡는다")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="조용한 성공 전수 조사 (D-284 (3))")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    # 조사 결과를 내기 전에 **탐지기부터 시험한다.** 순서가 반대면 목록을 먼저 믿게 된다.
    if self_test() != 0:
        return 1
    print()

    rows = walk()
    order = {"high": 0, "medium": 1, "low": 2, "unread": 3}
    rows.sort(key=lambda r: (order.get(r["grade"], 9), r["file"], r["line"]))

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    counts = {g: sum(1 for r in rows if r["grade"] == g) for g in order}
    print(f"[SILENT] 후보 {len(rows)}건 — "
          f"high {counts['high']} · medium {counts['medium']} · low {counts['low']} · "
          f"판정불가 {counts['unread']}")
    print("[SILENT] ※ 이것은 **판정이 아니라 목록**이다. 사람이 읽을 순서를 정해 준다 (D-284 (3))\n")

    current = None
    for r in rows:
        if r["grade"] != current:
            current = r["grade"]
            print(f"── {current} ──")
        print(f"  {r['file']}:{r['line']}  {r['func']}()  →  {r['returns']}")
        print(f"      {r['why']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
