#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-119 / SEC-20 — **역할별** 쓰기 면 전수 측정. 읽어서 답하지 않는다 (D-210).

무엇을 재나
-----------
살아 있는 라우터의 **쓰기 메서드 전수**(경로×메서드)를 **로그인한 사람으로** 때린다.
`probe_write_surface.py` 가 「익명이 어디까지 가나」를 재는 동안, 이것은
「**이 역할이 어디까지 쓰나**」를 잰다. 분모는 같은 열거를 쓴다 — 갈리면 안 된다.

부작용 없음 (D-334 대체물)
--------------------------
등록된 ``view_func`` 를 **도달 표시만 남기는 대체물**로 잠시 바꾸고 때린다.
본체는 한 줄도 돌지 않는다. 그러므로 이벤트 상태도, 감사 줄도 만들지 않는다.
★ 관문(미들웨어)은 대체물과 무관하게 **그대로 돈다** — 그것이 이 탐침이 재는 것이다.

판정 — 두 칸뿐이다
------------------
    blocked   관문이 **403** 을 냈다. 본체 자리에 **닿지 못했다**
    allowed   관문을 지났다 (도달했든, 422/404 로 떨어졌든 — **관문은 없었다**)

422·404·405 를 관문으로 세지 않는다 (P-83). 관문은 403 뿐이다.
빈 본문 하나면 충분하다: 이 탐침이 재는 것은 **스키마가 아니라 관문**이고,
관문은 본문 검증보다 **바깥**에 있다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/probe_role_write_surface.py \
            --user gxseed_u4_official --user gxseed_u1_operator \
            /repo/docs/agent/evidence/P-119/after_u4.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")


class _Reached(Exception):
    """대체물이 불렸다는 표시. 본체는 안 돈다."""


def enumerate_writes():
    """분모 — **살아 있는 라우터 전수**. `probe_write_surface.collect()` 와 같은 열거."""
    from common.tenant_scope import _iter_ninja_apis, _join
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
    from probe_write_surface import probe_url

    out = []
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    methods = [str(m).upper() for m in (getattr(op, "methods", []) or [])]
                    writes = [m for m in methods if m in WRITE_METHODS]
                    if not writes:
                        continue
                    path = _join(mount, prefix, op_path)
                    url = probe_url(path, mount, prefix, op_path)
                    for method in writes:
                        out.append((op, path, url, method))
    return out


def _concrete(url: str) -> str:
    """경로 틀(`{id}`)을 값으로 채운다. **1 은 실재 id 가 아니다** — 대체물이 막고 있으므로
    본체는 어차피 안 돈다. 그래도 쓰기 면을 실재 id 로 때리지 않는 규율은 지킨다."""
    return re.sub(r"\{[^}]+\}", "999999999", url)


def probe_one(client, op, url: str, method: str) -> dict:
    marker = {"hit": False}

    def _stub(request, *a, **kw):
        marker["hit"] = True
        raise _Reached()

    saved = op.view_func
    try:
        op.view_func = _stub
        try:
            resp = client.generic(method, _concrete(url), data=b"{}",
                                  content_type="application/json")
            status = resp.status_code
            body = resp.content[:600].decode("utf-8", "replace")
        except _Reached:
            status, body = None, ""
        except Exception as exc:                          # noqa: BLE001
            status, body = -1, "%s: %s" % (type(exc).__name__, exc)
    finally:
        op.view_func = saved

    code = ""
    if body:
        try:
            code = str((json.loads(body) or {}).get("code") or "")
        except Exception:                                  # noqa: BLE001
            code = ""
    blocked = (status == 403 and not marker["hit"])
    return {"status": status, "reached": marker["hit"], "code": code,
            "verdict": "blocked" if blocked else "allowed",
            "body": body[:200] if blocked else ""}


def run_for_user(username: str, rows) -> dict:
    from django.contrib.auth import get_user_model
    from django.test import Client

    user = get_user_model().objects.get(username=username)
    client = Client(raise_request_exception=False)
    client.force_login(user)

    measured = []
    for op, path, url, method in rows:
        r = probe_one(client, op, url, method)
        r.update({"method": method, "path": path})
        measured.append(r)
    measured.sort(key=lambda r: (r["path"], r["method"]))
    blocked = [r for r in measured if r["verdict"] == "blocked"]
    return {
        "user": username,
        "user_id": user.id,
        "roles": sorted(x.code for x in user.roles.all()),
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "totals": {"routes": len(measured), "blocked": len(blocked),
                   "allowed": len(measured) - len(blocked)},
        "blocked_codes": {c: sum(1 for r in blocked if r["code"] == c)
                          for c in sorted({r["code"] for r in blocked})},
        "routes": measured,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--user", action="append", required=True)
    args = ap.parse_args()

    sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()

    rows = enumerate_writes()
    payload = {
        "decision": "P-119 · SEC-20",
        "probe_mode": "live-router-authenticated-stub",
        "denominator": {"source": "live-router", "write_method_rows": len(rows),
                        "write_methods": list(WRITE_METHODS)},
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "users": [],
    }
    for name in args.user:
        res = run_for_user(name, rows)
        payload["users"].append(res)
        print("[ROLEWRITE] %-22s 역할=%s  전수 %d자리 · **막힘 %d** · 통과 %d %s"
              % (name, ",".join(res["roles"]) or "(없음)", res["totals"]["routes"],
                 res["totals"]["blocked"], res["totals"]["allowed"],
                 res["blocked_codes"] or ""))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print("[ROLEWRITE] → %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
