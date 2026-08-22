#!/usr/bin/env python
r"""pg_dump(COPY 형식)에서 `created_by IS NULL` 행을 **DB 없이** 집계한다 — W0-13 ①.

왜 DB 를 띄우지 않는가
----------------------
RUNBOOK 의 §F 는 `django.setup()` → `apps.get_models()` → `_base_manager.count()` 로
세도록 되어 있고, 그러려면 dj-core + Postgres + 컨테이너가 전부 있어야 한다.
그 셋이 없어서 이 집계는 열두 스프린트 동안 한 번도 돌지 못했다.

그런데 **덤프 파일 자체가 답을 갖고 있다.** pg_dump 의 COPY 형식은

    COPY public.<table> (col1, col2, ...) FROM stdin;
    val1\tval2\t...
    \.

이고 NULL 은 `\N` 이다. 컬럼 목록에서 `created_by` 의 위치를 찾아 그 열이 `\N` 인
행을 세면 된다. ORM 도 DB 도 필요 없다.

★ 이 방식이 오히려 정확하다
---------------------------
`objects` 로 세면 세는 행위 자체가 `CustomManagerGroup` 필터를 지나 **결함이 결함을
숨긴다.** 그래서 원 스크립트도 `_base_manager` 를 쓰라고 못박았다.
덤프는 매니저를 아예 통과하지 않으므로 그 함정이 원천적으로 없다.

사용법
------
    python scripts/scan_dump_created_by.py <dump.sql>
    python scripts/scan_dump_created_by.py <dump.sql> --all   # 테넌트성 아닌 표도 전부
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

COPY_RE = re.compile(r"^COPY\s+(?:[\w.]+\.)?\"?(?P<table>[\w]+)\"?\s*\((?P<cols>[^)]*)\)\s+FROM\s+stdin;", re.I)

# 테넌트 소유를 나타내는 컬럼. 이 중 하나라도 있으면 '테넌트성 테이블'로 본다.
GROUP_COLS = {"group_id", "groups_id", "group", "groups"}


def scan(path: Path):
    rows = []
    cur = None
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if cur is None:
                m = COPY_RE.match(line)
                if not m:
                    continue
                cols = [c.strip().strip('"') for c in m.group("cols").split(",")]
                cur = {
                    "table": m.group("table"),
                    "cols": cols,
                    "cb_idx": cols.index("created_by_id") if "created_by_id" in cols
                    else (cols.index("created_by") if "created_by" in cols else None),
                    "tenant": bool(GROUP_COLS & set(cols)),
                    "total": 0,
                    "nulls": 0,
                }
                continue

            if line.startswith("\\."):
                rows.append(cur)
                cur = None
                continue

            cur["total"] += 1
            i = cur["cb_idx"]
            if i is not None:
                fields = line.rstrip("\n").split("\t")
                if i < len(fields) and fields[i] == r"\N":
                    cur["nulls"] += 1
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--all", action="store_true", help="created_by 없는 표까지 전부 출력")
    args = ap.parse_args()

    rows = scan(Path(args.dump))
    has_cb = [r for r in rows if r["cb_idx"] is not None]
    tenant = [r for r in has_cb if r["tenant"]]

    print(f"# COPY 블록 {len(rows)}개 · created_by 보유 {len(has_cb)}개 · 그중 테넌트성 {len(tenant)}개\n")

    target = rows if args.all else sorted(has_cb, key=lambda r: (-r["nulls"], -r["total"]))
    print(f"{'table':44} {'tenant':>6} {'total':>9} {'null_cb':>9} {'pct':>7}")
    print("-" * 80)
    for r in target:
        if not args.all and r["total"] == 0 and r["nulls"] == 0:
            continue
        pct = (100.0 * r["nulls"] / r["total"]) if r["total"] else 0.0
        mark = "  Y" if r["tenant"] else "  ."
        print(f"{r['table']:44} {mark:>6} {r['total']:9d} {r['nulls']:9d} {pct:6.1f}%")

    t_total = sum(r["total"] for r in tenant)
    t_nulls = sum(r["nulls"] for r in tenant)
    a_total = sum(r["total"] for r in has_cb)
    a_nulls = sum(r["nulls"] for r in has_cb)
    print("-" * 80)
    print(f"테넌트성 표 합계 : NULL {t_nulls} / {t_total} "
          f"({100.0 * t_nulls / t_total if t_total else 0:.1f}%)   ← 실제 노출 후보")
    print(f"created_by 보유 전체: NULL {a_nulls} / {a_total} "
          f"({100.0 * a_nulls / a_total if a_total else 0:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
