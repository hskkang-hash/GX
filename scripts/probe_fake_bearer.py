#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SEC — **관문의 경계가 얼마나 넓은가.** 가짜 자격증명으로 읽기 면 전수를 두드린다.

왜 이것이 필요한가 [턴 AE · 차선 U56 이 물었고 조율자가 확인했다]
------------------------------------------------------------------
`common/access_gate.py::_has_credentials` 는 **자격증명을 들고 왔는지만** 본다.
유효한지는 안 본다 — 그리고 그것은 **설계다.** 소스가 그 이유를 적어 뒀다:

    「여기서 유효성까지 보면 이 미들웨어가 **두 번째 인증기**가 된다.
     인증기가 둘이면 언젠가 갈리고, 갈리면 어느 쪽이 맞는지 아무도 모른다.」

그러니 이 관문이 막는 것은 **아무것도 안 싣고 오는 요청**뿐이고, 진짜 인증은
라우트마다 제 `auth=` 가 한다. 여기까지는 문서에 있다.

★★ **없는 것은 그 경계가 얼마나 넓은가다.**
  턴 P 의 `probe_anon_read.py` 는 **익명**(헤더 0)으로 331자리를 쟀다.
  **가짜 헤더를 실은 회차는 한 번도 없었다.** 두 수는 다른 수다 —
  익명이 401 이라는 것은 관문이 섰다는 뜻이고, **가짜 헤더도 401 이라야**
  그 자리의 `auth=` 가 실제로 서 있다는 뜻이다.

  ⇒ 이 탐침이 답하는 질문은 하나다:
     **「`Authorization` 에 아무거나 실으면 자료가 나오는 자리가 몇인가.」**
     0 이면 경계는 설계대로 좁다. 0 이 아니면 **그 수가 빨강**이고,
     고칠 자리는 관문이 아니라 **그 라우트들의 `auth=`** 다.

★ 판정식을 베끼지 않는다 (D-212) — 빨강 술어(`has_data`)·칸 나누기(`classify`)·
  공개 선언(`PUBLIC_READ_BY_DESIGN`)은 `probe_read_surface` 에서 **import** 한다.

★ **실토큰을 쓰지 않는다.** 이 파일이 싣는 것은 **어디에도 없는 글자**다 —
  남의 세션을 빼앗지도, 잠금 계수기를 올리지도 않는다(로그인을 안 한다).

부르는 자리: **gx-shell 안**(HTTP 로 8000 을 때린다).

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings -w /app gx-shell \\
      python /repo/scripts/probe_fake_bearer.py /tmp/fake_bearer.json

종료 코드: 0 쟀고 0건 · 1 쟀고 자료가 나온 자리가 있다 · 2 못 쟀다
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: ★ 어디에도 없는 글자. 실재 토큰의 모양만 흉내 내고 값은 아무 뜻이 없다.
#:   이 글자가 통과한다면 그것은 **값을 안 본다**는 뜻이고, 그것이 이 탐침의 답이다.
FAKE = "Bearer gx.nonexistent.probe.token.do-not-issue-this"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", help="결과 JSON 경로")
    ap.add_argument("--base", default=os.environ.get("GX_READ_BASE", "http://localhost:8000"))
    args = ap.parse_args()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import django
        django.setup()
        import probe_read_surface as P
        from common.tenant_scope import _iter_ninja_apis, _join
    except Exception as exc:                                    # noqa: BLE001
        print("[FAKE-BEARER] **못 쟀다** — 환경을 못 세웠다: %s: %s"
              % (type(exc).__name__, exc))
        print("[FAKE-BEARER] gx-shell 안에서 DJANGO_SETTINGS_MODULE 을 주고 -w /app 으로 부른다")
        return EXIT_UNDECIDABLE

    caller = P.Caller(args.base)
    rows, t0 = [], time.time()
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    methods = [str(m).upper() for m in (getattr(op, "methods", []) or [])]
                    read_methods = [m for m in methods if m in P.READ_METHODS]
                    if not read_methods:
                        continue
                    path = _join(mount, prefix, op_path)
                    url = P.fill_path(P.probe_url(path, mount, prefix, op_path), {})
                    for method in read_methods:
                        #: 같은 자리를 **두 번** 때린다 — 익명 한 번, 가짜 헤더 한 번.
                        #: 두 수를 나란히 둬야 「관문이 섰다」와 「값을 안 본다」가 갈린다.
                        anon = P.measure(caller, method, url, None, {})
                        fake = P.measure(caller, method, url, None,
                                         {"Authorization": FAKE})
                        a_data, a_why, _, _ = P.has_data(anon["status"], anon["body"])
                        f_data, f_why, f_units, f_keys = P.has_data(fake["status"], fake["body"])
                        rows.append({
                            "method": method, "path": path,
                            "anon_status": anon["status"], "anon_data": a_data,
                            "fake_status": fake["status"], "fake_data": f_data,
                            "fake_why": f_why, "fake_units": f_units,
                            "fake_keys": f_keys[:6],
                            "fake_bytes": len(fake["body"]),
                        })

    public = set(getattr(P, "PUBLIC_READ_BY_DESIGN", ()) or ())

    def is_public(r):
        return r["path"] in public or (r["method"], r["path"]) in public

    leaked = [r for r in rows if r["fake_data"] and not is_public(r)]
    #: ★ 「익명은 막혔는데 가짜 헤더는 통과」가 **이 탐침의 고유한 수**다.
    #:   익명도 자료가 나오는 자리는 턴 P 가 이미 세던 수이고, 여기서 다시 세면
    #:   같은 사실을 두 번 세는 것이 된다.
    only_fake = [r for r in leaked if not r["anon_data"]]

    payload = {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "base": args.base, "total": len(rows),
        "elapsed_s": round(time.time() - t0, 1),
        "leaked": len(leaked), "only_fake": len(only_fake),
        "rows_leaked": leaked[:40],
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print("[P-107] TARGET=%s (gx-shell 안에서 HTTP 로 때린다)" % args.base)
    print("[P-107] AS=**없는 토큰** — 로그인하지 않는다 · 실계정·실토큰 0")
    print("[P-107] SOURCE=살아 있는 라우터 레지스트리(런타임 전수)")
    print("[P-107] MEASURED=읽기 면 전수를 **두 번** 때린다(익명 · 가짜 헤더) — "
          "**분모 %d**(지금 셌다). 익명 401 은 관문이 선 것이고, "
          "가짜 헤더도 401 이라야 그 자리의 `auth=` 가 선 것이다" % len(rows))
    print("[FAKE-BEARER] [입력] 읽기 자리 %d · %.1f초" % (len(rows), payload["elapsed_s"]))
    print("[FAKE-BEARER] 가짜 헤더로 **자료가 나온 자리 %d**"
          " (그중 익명으로는 막히던 자리 **%d**)" % (len(leaked), len(only_fake)))
    for r in leaked[:12]:
        print("[FAKE-BEARER]   · %-4s %-52s 익명 %s → 가짜 %s · %dB · %s"
              % (r["method"], r["path"][:52], r["anon_status"], r["fake_status"],
                 r["fake_bytes"], ",".join(r["fake_keys"]) or r["fake_why"][:40]))
    print("[FAKE-BEARER] 기록 → %s" % args.out)
    if leaked:
        print("[FAKE-BEARER] **빨강** — 관문은 자격증명의 **있음**만 본다(설계). "
              "그러니 이 자리들은 제 `auth=` 로 서야 하는데 서지 않았다. "
              "고칠 자리는 관문이 아니라 **그 라우트들**이다")
        return EXIT_FAIL
    print("[FAKE-BEARER] 초록 — 가짜 자격증명으로 자료가 나오는 자리가 **0** 이다. "
          "관문의 경계가 넓어도 그 뒤가 서 있다")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
