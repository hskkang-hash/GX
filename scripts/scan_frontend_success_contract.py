#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W0-18 ① 하위호환 영향조사 — 프론트에서 200-body-403 계약에 의존하는 지점 전수.

배경: dj-core core/role/permission.py:512 는 권한거부를 HTTP 200 + {"success": false,
"status_code": 403} 으로 돌려준다(§0.4 금지구역). W0-18 은 저장소 쪽 후처리로 이것을
실제 HTTP 403 으로 승격한다. 승격하면 axios 가 reject 하므로, **200 을 기대하고
res.success 를 읽던 지점**은 then 분기에 도달하지 못한다.

이 스크립트가 세는 것:
  · API 호출 지점 (await API.<m>( / API.<m>(...).then )
  · 각 호출이 try/catch 또는 .catch() 로 감싸였는가  → guarded / unguarded
  · 호출 결과에서 .success 를 읽는가                → 계약 의존
  · unguarded × 계약의존  = **승격 시 무증상 실패(스피너 고착)** 후보

읽기 전용. 소스를 수정하지 않는다.
"""
import json
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "frontend" / "src"

CALL_RE = re.compile(r"\bAPI\s*\.\s*(get|post|put|patch|delete|del|request)\s*\(")
SUCCESS_RE = re.compile(r"\.success\b")
STATUS_CODE_RE = re.compile(r"\.status_code\b")


def find_enclosing_function(lines, idx):
    """호출 라인에서 위로 올라가며 함수 시작 추정. 들여쓰기 기준."""
    call_indent = len(lines[idx]) - len(lines[idx].lstrip())
    for j in range(idx, -1, -1):
        line = lines[j]
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if indent < call_indent and re.search(
            r"(=>\s*\{|function\s|async\s|\)\s*\{)", line
        ):
            return j
    return max(0, idx - 40)


def brace_scan_try(lines, start, call_idx):
    """start~call_idx 사이에 열린 채로 남아 있는 try 블록이 있는가."""
    depth = 0
    try_depths = []
    for j in range(start, call_idx + 1):
        line = lines[j]
        code = re.sub(r"//.*$", "", line)
        for ch in code:
            if ch == "{":
                depth += 1
            elif ch == "}":
                if try_depths and try_depths[-1] == depth:
                    try_depths.pop()
                depth -= 1
        if re.search(r"\btry\s*\{", code):
            try_depths.append(depth)
    return bool(try_depths)


def scan_file(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    out = []
    for i, line in enumerate(lines):
        if not CALL_RE.search(line):
            continue
        if line.lstrip().startswith(("//", "*", "/*")):
            continue
        fn_start = find_enclosing_function(lines, i)
        in_try = brace_scan_try(lines, fn_start, i)
        # .catch( 는 호출 직후 5줄 안
        window = "\n".join(lines[i : min(len(lines), i + 6)])
        has_catch = ".catch(" in window
        # 결과에서 .success / .status_code 를 읽는가 — 호출 이후 25줄 안
        after = "\n".join(lines[i : min(len(lines), i + 25)])
        reads_success = bool(SUCCESS_RE.search(after))
        reads_status_code = bool(STATUS_CODE_RE.search(after))
        out.append(
            {
                "file": str(path.relative_to(SRC.parent.parent)).replace("\\", "/"),
                "line": i + 1,
                "snippet": line.strip()[:120],
                "guarded": bool(in_try or has_catch),
                "guard": "try" if in_try else (".catch" if has_catch else None),
                "reads_success": reads_success,
                "reads_status_code": reads_status_code,
            }
        )
    return out


def main():
    if not SRC.is_dir():
        print(f"[ERR] frontend/src 없음: {SRC}", file=sys.stderr)
        return 2
    sites = []
    for p in sorted(SRC.rglob("*")):
        if p.suffix in (".ts", ".tsx") and p.is_file():
            sites.extend(scan_file(p))

    total = len(sites)
    unguarded = [s for s in sites if not s["guarded"]]
    contract = [s for s in sites if s["reads_success"]]
    at_risk = [s for s in sites if not s["guarded"] and s["reads_success"]]

    print(f"[SCAN] API 호출 지점            {total}")
    print(f"[SCAN]   try/catch·.catch 보호   {total - len(unguarded)}")
    print(f"[SCAN]   보호 없음               {len(unguarded)}")
    print(f"[SCAN] res.success 를 읽는 지점  {len(contract)}")
    print(f"[SCAN] ★ 보호없음 × 계약의존     {len(at_risk)}   <- 승격 시 무증상 실패 후보")

    by_file = {}
    for s in at_risk:
        by_file.setdefault(s["file"], []).append(s["line"])
    print(f"[SCAN] 위험 파일 {len(by_file)}개")
    for f, ls in sorted(by_file.items(), key=lambda kv: -len(kv[1]))[:25]:
        print(f"    {len(ls):3}  {f}")

    outp = (
        Path(__file__).resolve().parent.parent
        / "docs/agent/evidence/W0-18/frontend_success_sites.json"
    )
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(
        json.dumps(
            {
                "total_call_sites": total,
                "unguarded": len(unguarded),
                "reads_success": len(contract),
                "at_risk": len(at_risk),
                "at_risk_files": len(by_file),
                "sites": sites,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[SCAN] 기록: {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
