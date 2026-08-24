#!/usr/bin/env python
"""타임아웃 없는 외부 호출 실측 (W0-17 ②).

무엇을 세나
    `requests.{get,post,put,patch,delete,head,request}` 와 `requests.Session()` 객체의
    호출 중 **`timeout=` 인자가 없는 것**. 타임아웃 없는 호출 하나가 늦으면 워커가
    잡히고, 잡힌 워커가 쌓이면 서비스 전체가 선다 — 부분 실패가 전면 정지가 되는 경로다.

왜 grep 이 아니라 AST 인가
    grep 은 주석·문자열·여러 줄 호출을 잘못 세고, 무엇보다 **이름이 비슷한 것을 같이 센다**
    (redis `client.get` · Django 테스트 `client.get` · dict `.get`). 이 파일은 `ast` 로
    호출 노드를 보고 `requests` 계열만 고른다. **이 수가 정본이다.**

    지시서의 "49건"은 grep 추정치였다. 실측은 아래 출력이 말한다 (D-214 · 실측 우선).

사용:
    python scripts/scan_request_timeouts.py backend            # 표
    python scripts/scan_request_timeouts.py backend --json     # 기계 판독
    python scripts/scan_request_timeouts.py backend --check    # 미조치 있으면 exit 1 (게이트용)

제외: 마이그레이션·가상환경·캐시. 관리 커맨드·배치는 **포함**한다 — 배치가 매달리는 것도
      같은 사고다.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "request"}
SKIP_PARTS = {"migrations", "venv", "node_modules", "__pycache__", ".git"}

#: 사유와 함께 면제된 호출. `(파일 상대경로, 줄번호)` → 사유.
#: 여기에 넣는 것은 **"이 호출은 매달려도 된다"는 선언**이 아니라,
#: "정적으로 보이지 않을 뿐 타임아웃이 들어간다"는 선언이다. 추측으로 넣지 않는다.
#: 셋 다 `kwargs.setdefault("timeout", …)` 로 **직전 줄에서** 넣는 형태라 AST 가 못 본다.
EXEMPT: dict[tuple[str, int], str] = {
    ("backend/common/external_http.py", 77):
        "request() — 바로 위에서 kwargs.setdefault('timeout', default_timeout())",
    ("backend/common/external_http.py", 109):
        "fetch_json() — 바로 위에서 kwargs.setdefault('timeout', default_timeout())",
    ("backend/delivery/decorators.py", 381):
        "외부 연동 데코레이터 — request_kwargs.setdefault('timeout', default_timeout())",
}


def _session_names(tree: ast.AST) -> set[str]:
    """이 파일 안에서 `requests.Session()` 이 대입된 이름들."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        if isinstance(func, ast.Attribute) and func.attr == "Session":
            base = func.value
            if isinstance(base, ast.Name) and base.id == "requests":
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
                    elif isinstance(target, ast.Attribute):
                        names.add(target.attr)
    return names


def is_request_call(node: ast.Call, session_names: set[str]) -> str | None:
    """`requests.get(...)` 또는 Session 객체 호출이면 표기를 준다."""
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr not in HTTP_METHODS:
        return None
    base = func.value
    if isinstance(base, ast.Name):
        name = base.id
    elif isinstance(base, ast.Attribute):
        name = base.attr
    else:
        return None
    if name == "requests" or name in session_names:
        return f"{name}.{func.attr}"
    return None


def scan(root: Path) -> dict:
    missing: list[dict] = []
    with_timeout = 0
    for path in sorted(root.rglob("*.py")):
        if set(path.parts) & SKIP_PARTS:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "requests" not in text:
            continue
        try:
            tree = ast.parse(text, str(path))
        except SyntaxError:
            continue
        sessions = _session_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            call = is_request_call(node, sessions)
            if call is None:
                continue
            if any(k.arg == "timeout" for k in node.keywords):
                with_timeout += 1
                continue
            rel = path.as_posix()
            missing.append({
                "file": rel,
                "line": node.lineno,
                "call": call,
                "exempt_reason": EXEMPT.get((rel, node.lineno)),
            })
    return {"missing": missing, "with_timeout": with_timeout}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default="backend")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="면제되지 않은 미조치가 있으면 exit 1")
    args = ap.parse_args()

    result = scan(Path(args.root))
    missing = result["missing"]
    open_items = [f for f in missing if not f["exempt_reason"]]

    if args.json:
        print(json.dumps({
            "with_timeout": result["with_timeout"],
            "missing_total": len(missing),
            "open": len(open_items),
            "findings": missing,
        }, ensure_ascii=False, indent=2))
    else:
        by_file: dict[str, int] = {}
        for f in open_items:
            by_file[f["file"]] = by_file.get(f["file"], 0) + 1
        total = result["with_timeout"] + len(missing)
        print(f"[TIMEOUT] requests 호출 {total}건 중 타임아웃 없는 것 {len(open_items)}건 "
              f"/ {len(by_file)}파일 (면제 {len(missing) - len(open_items)}건 · "
              f"타임아웃 있음 {result['with_timeout']}건)")
        for name, count in sorted(by_file.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {count:3d}  {name}")

    if args.check and open_items:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
