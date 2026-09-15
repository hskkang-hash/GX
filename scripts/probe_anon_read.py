#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-133 — **익명 GET 전수**만 잰다. 로그인하지 않는다.

왜 따로 있나 (`probe_read_surface.py` 가 있는데)
------------------------------------------------
`probe_read_surface.py` 는 계정 **둘**(역할0 주인공 · admin 대조군)로 로그인한다.
이 제품은 계정당 동시 세션이 **하나**이고, 턴 P 는 차선이 여럿이다 — 그 탐침을
돌리면 옆 차선의 토큰을 빼앗고, 빼앗긴 쪽은 401 을 「관문이 섰다」로 세어
**거짓 초록**을 낸다 (D-350 · 턴 M 의 거짓 초록 151자리).

P-133 이 답해야 하는 질문은 **하나**다: 「자격증명 없이 부르면 자료가 나오는가.」
그 질문에는 로그인이 필요 없다. 그래서 이 탐침은 **익명 한 줄**만 잰다.

★ 판정식은 베끼지 않는다 (D-212)
--------------------------------
빨강 술어(`has_data`)·칸 나누기(`classify`)·공개 선언(`PUBLIC_READ_BY_DESIGN`)은
`probe_read_surface` 에서 **import 한다**. 복사하면 언젠가 갈리고, 갈린 날
어느 쪽이 제품의 답인지 아무도 모른다.

★ 대조군이 없으므로 못 가르는 것 (정직하게 회색)
------------------------------------------------
「200 인데 비었다」가 **관문이 비운 것**인지 **이 환경에 행이 없는 것**인지는
admin 대조 없이 못 가른다 → 회색이다. 빨강(자료가 나갔다)은 대조군 없이도
확정된다 — 본문에 자료가 **실제로 들어 있는가**만 보면 되기 때문이다.
경로 틀(`{id}`)은 실재 id 를 캐올 대조군이 없으므로 `1` 로 때린다. 404 면 회색이다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, "/app")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", help="결과 JSON 경로")
    ap.add_argument("--base", default=os.environ.get("GX_READ_BASE", "http://localhost:8000"))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()

    import probe_read_surface as P

    caller = P.Caller(args.base)
    from common.tenant_scope import _iter_ninja_apis, _join

    rows = []
    t0 = time.time()
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    methods = [str(m).upper() for m in (getattr(op, "methods", []) or [])]
                    read_methods = [m for m in methods if m in P.READ_METHODS]
                    if not read_methods:
                        continue
                    path = _join(mount, prefix, op_path)
                    url = P.probe_url(path, mount, prefix, op_path)
                    view = getattr(op, "view_func", None)
                    auth_names = []
                    for cb in (getattr(op, "auth_callbacks", None) or []):
                        for klass in type(cb).__mro__:
                            if klass is not object and klass.__name__ not in auth_names:
                                auth_names.append(klass.__name__)
                    params = re.findall(r"\{([^}]+)\}", url)
                    subj_url = P.fill_path(url, {})
                    for method in read_methods:
                        a = P.measure(caller, method, subj_url, None, {})
                        a_data, a_why, a_units, a_keys = P.has_data(a["status"], a["body"])
                        box, why = P.classify(
                            {"status": a["status"], "data": a_data, "why": a_why},
                            {"status": None, "data": False}, path, anon=True)
                        row = {
                            "method": method, "path": path, "measured_url": a["url"],
                            "view": "%s.%s" % (getattr(view, "__module__", "?"),
                                               getattr(view, "__name__", "?")),
                            "authn_chain": auth_names,
                            "path_params": params,
                            "anon_status": a["status"], "anon_bytes": len(a["body"]),
                            "anon_data": a_data, "anon_why": a_why,
                            "anon_units": a_units, "anon_keys": a_keys,
                            "anon_bucket": box, "anon_bucket_by": why,
                            "declared_public": path in P.PUBLIC_READ_BY_DESIGN,
                        }
                        row["anon_red"] = (box == P.BUCKET_RED)
                        if args.verbose:
                            print("  %-6s %-4s %-5s %s" % (box, method, a["status"], path))
                        rows.append(row)

    rows.sort(key=lambda r: (P.BUCKETS.index(r["anon_bucket"]), r["path"], r["method"]))
    boxes = {b: sum(1 for r in rows if r["anon_bucket"] == b) for b in P.BUCKETS}
    reds = [r for r in rows if r["anon_red"]]

    payload = {
        "decision": "P-133",
        "probe_mode": "live-router-anonymous-only-real-call (로그인 없음)",
        "server": {"base": args.base},
        "red_predicate": P.has_data.__doc__.strip().splitlines()[0],
        "public_read_by_design": dict(sorted(P.PUBLIC_READ_BY_DESIGN.items())),
        "anon_buckets": boxes,
        "anon_red": [{"method": r["method"], "path": r["path"], "view": r["view"],
                      "status": r["anon_status"], "bytes": r["anon_bytes"],
                      "units": r["anon_units"], "keys": r["anon_keys"],
                      "measured_url": r["measured_url"]} for r in reds],
        "totals": {"read_rows": len(rows), "anon_red": len(reds)},
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "elapsed_s": int(time.time() - t0),
        "routes": rows,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    print("[ANONREAD] 익명 읽기 전수 %d자리 → %s" % (len(rows), args.out))
    print("    빨강 %d · 초록 %d · 공개 %d · 회색 %d"
          % (boxes[P.BUCKET_RED], boxes[P.BUCKET_GREEN],
             boxes[P.BUCKET_PUBLIC], boxes[P.BUCKET_GREY]))
    for r in sorted(reds, key=lambda x: -x["anon_bytes"]):
        print("    ★빨강 %s %s — %d B · %d덩이 · %s"
              % (r["method"], r["path"], r["anon_bytes"], r["anon_units"],
                 ", ".join(r["anon_keys"][:6])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
