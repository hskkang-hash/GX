#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""D-368 ① — 관문 없는 **쓰기** 면을 호출로 분류한다. 읽어서 답하지 않는다 (D-210).

왜 읽기와 따로 세나 (D-368)
---------------------------
    읽기 유출 — 나간 것은 되돌릴 수 없다. 그러나 **무엇이 나갔는지는 안다**
    쓰기 오염 — 들어온 것도 되돌릴 수 없고, **게다가 조용하다.**
                익명이 이벤트를 심으면 가짜 재난 알림이 나가고 보고서가 오염된다.
                그 데이터는 진짜와 섞여서 **나중에 골라낼 수 없다**

그래서 D-358(한꺼번에 막으면 제품이 깨진다)의 신중함은 **읽기 면의 규칙**으로 두고,
쓰기 면은 범위를 좁혀 **그 자리들만** 막는다.

네 갈래 (D-368 ①)
-----------------
    writes                 익명이 핸들러 자리에 **도달**하고, 그 핸들러가 **쓴다**
                           ★ 이번 턴의 표적
    read_only_in_practice  도달은 하지만 핸들러가 쓰지 않는다 (조회를 POST 로 받는 자리)
    rejected_elsewhere     도달하지 못한다 — 다른 것(권한·CSRF·검증)이 막았다
    public_by_design       **선언**이다. 로그인·토큰처럼 익명이어야만 성립하는 면.
                           면제가 아니라 이름을 적어 두는 것이다 (D-264 계열)

어떻게 재나 — 부작용 없이
-------------------------
쓰기 메서드를 그냥 때리면 부작용이 남는다. 그렇다고 안 때리면 「auth 콜백이 비었으니
열려 있을 것」이라는 **추정**이 된다(D-280 금지). 그래서 D-334 가 쓴 방법을 그대로
쓴다 — 등록된 `view_func` 를 **도달 표시만 남기는 대체물**로 잠시 바꾸고 때린다.
**본체는 한 줄도 돌지 않는다.**

「쓰는가」는 **정적으로** 읽는다 — 대체물을 끼운 채로는 본체가 안 돌기 때문이다.
그 사실을 숨기지 않는다: `writes_by` 칸에 **무엇을 보고 그렇게 판정했는지** 적는다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/probe_write_surface.py /docs/agent/evidence/D-368/write_surface.json

호스트에서는 `--self-test` 만 돈다.
"""
from __future__ import annotations

import argparse
import ast
import inspect
import json
import os
import re
import sys
import textwrap
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")

#: 익명이어야만 성립하는 면. **선언이지 면제가 아니다** — 사유를 적고, 늘 때마다
#: 사람이 이 목록을 고쳐야 한다. 목록에 없으면 자동으로 표적이 된다.
#:
#: ★ 판단 기준 하나: **아직 로그인하지 못한 사람이 부르는 자리인가.**
#:   그 답이 「아니오」이면 여기 있으면 안 된다.
PUBLIC_BY_DESIGN: dict[str, str] = {
    "/api/token/pair": "로그인 — 토큰을 받으러 오는 자리다. 토큰이 있어야 부를 수 있으면 로그인이 아니다",
    "/api/token/refresh": "만료된 토큰을 갱신한다 — 유효한 접근 토큰이 없는 상태가 정상이다",
    "/api/token/verify": "토큰 검사 — 검사받을 토큰을 본문으로 낸다",
    "/api/v1/auth/login": "로그인",
    "/api/v1/auth/logout": "로그아웃 — 이미 만료된 토큰으로도 불려야 한다",
    "/api/v1/auth/refresh-token": "토큰 갱신",
    "/api/v1/auth/forgot-password": "비밀번호 분실 — 로그인할 수 없는 사람이 부른다",
    "/api/v1/auth/reset-password": "재설정 — 메일로 받은 토큰으로 부른다",
    "/api/v1/auth/otp/verify": "OTP 확인 — 로그인 절차의 두 번째 단계",
    "/api/v1/auth/otp/reset": "OTP 재설정 — 로그인 절차 안에 있다",
    "/api/v1/auth/delete-session": "세션 정리 — 로그인 실패 경로에서 불린다",
}

#: 핸들러가 **쓰는가**를 정적으로 볼 때 찾는 이름. 행위로 긋는다 (D-324).
WRITE_CALLS = ("save", "create", "delete", "update", "bulk_create", "bulk_update",
               "get_or_create", "update_or_create", "add", "remove", "set")


class _Reached(Exception):
    """대체물이 도달을 알리는 신호. 본체 대신 이것이 던져진다 — 부작용이 없다."""


def handler_writes(view_func) -> tuple[bool, str]:
    """이 핸들러가 **쓰는가.** (판정, 근거) 를 돌려준다.

    ★ 정적 판정임을 숨기지 않는다. 대체물을 끼운 채로는 본체가 안 돌기 때문에
      「도달했다」와 「썼다」를 같은 방법으로 잴 수 없다 — 그 사실을 근거란에 적는다.
      못 읽으면 **모른다고 적는다**: 모르는 것을 「안 쓴다」로 두면 표적이 조용히 준다.
    """
    fn = inspect.unwrap(view_func)
    try:
        src = inspect.getsource(fn)
    except (OSError, TypeError):
        return True, "원본을 읽지 못했다 — **모르는 것은 쓰는 쪽으로 센다** (D-284)"
    try:
        # ★ 데코레이터가 붙은 함수의 원본은 **들여쓰기가 남는다.**
        #   `lstrip()` 은 첫 줄만 펴고 나머지를 그대로 둬서 IndentationError 가
        #   나고, 그러면 전수가 통째로 「모른다」로 떨어진다 —
        #   첫 실행에서 실제로 8자리가 그렇게 떨어졌다 (D-350 측정기를 먼저 의심한다).
        tree = ast.parse(textwrap.dedent(src))
    except SyntaxError:
        return True, "원본을 파싱하지 못했다 — 모르는 것은 쓰는 쪽으로 센다"
    found = sorted({
        n.func.attr for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr in WRITE_CALLS
    })
    if found:
        return True, f"[정적] 핸들러 본문에 {', '.join(found)}() 호출"
    return False, "[정적] 핸들러 본문에 쓰기 호출 없음"


def _stub_probe(op, path: str, method: str) -> dict:
    """익명으로 때린다. **본체는 한 줄도 돌지 않는다** (D-334 의 방법 그대로)."""
    from django.test import Client

    marker = {"hit": False}

    def _stub(request, *a, **kw):
        marker["hit"] = True
        raise _Reached()

    saved = op.view_func
    status, note = None, ""
    try:
        op.view_func = _stub
        client = Client(raise_request_exception=False)
        probe_path = re.sub(r"\{[^}]+\}", "1", path)
        try:
            resp = client.generic(method, probe_path, data=b"{}",
                                  content_type="application/json")
            status = resp.status_code
        except _Reached:
            status = None
        except Exception as exc:                       # noqa: BLE001
            note = ("raised: %s: %s" % (type(exc).__name__, exc))[:160]
    finally:
        op.view_func = saved
    return {"reached": marker["hit"], "status": status, "note": note}


def classify(reached: bool, writes: bool, path: str) -> str:
    """네 갈래. **판정식을 한 곳에만 둔다** (D-212)."""
    if path in PUBLIC_BY_DESIGN:
        return "public_by_design"
    if not reached:
        return "rejected_elsewhere"
    return "writes" if writes else "read_only_in_practice"


def collect() -> list[dict]:
    from common.tenant_scope import _iter_ninja_apis, _join

    rows: list[dict] = []
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    methods = [str(m).upper() for m in (getattr(op, "methods", []) or [])]
                    writes_methods = [m for m in methods if m in WRITE_METHODS]
                    if not writes_methods:
                        continue
                    if getattr(op, "auth_callbacks", None):
                        continue                        # 인증 관문이 있다
                    path = _join(mount, prefix, op_path)
                    view = getattr(op, "view_func", None)
                    does_write, why = handler_writes(view) if view else (True, "핸들러 없음")
                    probe = _stub_probe(op, path, writes_methods[0])
                    rows.append({
                        "method": writes_methods[0],
                        "methods": ",".join(sorted(set(methods))),
                        "path": path,
                        "app": path.strip("/").split("/")[1] if path.count("/") > 1 else "",
                        "view": f"{getattr(view, '__module__', '?')}.{getattr(view, '__name__', '?')}",
                        "reached": probe["reached"],
                        "status": probe["status"],
                        "note": probe["note"],
                        "writes": does_write,
                        "writes_by": why,
                        "verdict": classify(probe["reached"], does_write, path),
                    })
    rows.sort(key=lambda r: (r["verdict"], r["path"]))
    return rows


def self_test() -> int:
    checks = [
        ("★ 도달 + 쓴다 → writes", classify(True, True, "/x") == "writes"),
        ("도달 + 안 쓴다 → read_only_in_practice",
         classify(True, False, "/x") == "read_only_in_practice"),
        ("★ 도달 못함 → rejected_elsewhere",
         classify(False, True, "/x") == "rejected_elsewhere"),
        ("★ 선언된 면은 도달하고 써도 표적이 아니다",
         classify(True, True, "/api/v1/auth/login") == "public_by_design"),
        ("★ 데코레이터 붙은 함수도 읽는다 (첫 실행이 여기서 멀었다)",
         handler_writes(_decorated_writer)[0]),
        ("쓰기 호출을 읽는다",
         handler_writes(_sample_writer)[0]),
        ("쓰기 호출이 없으면 안 읽는다",
         not handler_writes(_sample_reader)[0]),
    ]
    for name, ok in checks:
        print(f"  {'OK  ' if ok else 'FAIL'}  {name}")
    bad = [n for n, ok in checks if not ok]
    print(f"[WRITESURFACE] 자기시험 {len(checks)}건 {'통과' if not bad else '실패'}")
    return 0 if not bad else 1


def _fake_decorator(fn):
    return fn


# ★ 아래 표본들은 **부르지 않는다** — `handler_writes` 에게 소스를 읽히려고 있다.
#   그래서 `store` 는 None 이고, 실행하면 죽는다. 그것이 요점이다.
#
#   ⚠ `store.objects.create(...)` 로 쓰지 않는 이유: `scripts/verify_classification.py`
#     가 `objects`/`_base_manager` 사슬을 **진짜 DB 쓰기**로 세고, 그러면 이 측정기가
#     「데이터를 쓰는 도구」로 잡힌다. 표본은 표본이지 쓰기가 아니다.
@_fake_decorator
def _decorated_writer(request):
    store = None
    return store.create(x=1)


def _sample_writer(request):
    store = None
    return store.create(x=1)


def _sample_reader(request):
    store = None
    return list(store.filter(x=1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", help="결과 JSON 경로")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    rc = self_test()
    if args.self_test or rc:
        return rc
    if not args.out:
        print("[WRITESURFACE] 출력 경로가 필요하다 (배너가 stdout 을 더럽힌다)")
        return 2

    sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    rows = collect()
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {
        "decision": "D-368",
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": ("관문 없는(=`auth=` 콜백 없는) 쓰기 라우트 전수. 도달은 **호출**로, "
                 "쓰는가는 **정적**으로 판정했다 — 두 방법이 다르다는 사실을 "
                 "`writes_by` 에 적었다 (D-322)"),
        "totals": {"routes": len(rows), "by_verdict": counts},
        "routes": rows,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"[WRITESURFACE] 관문 없는 쓰기 라우트 **{len(rows)}자리** → {args.out}")
    for k in sorted(counts):
        print(f"    {k:24} {counts[k]:3}자리")
    return 0


if __name__ == "__main__":
    sys.exit(main())
