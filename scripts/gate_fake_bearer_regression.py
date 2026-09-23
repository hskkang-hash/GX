#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-273 — **가짜 헤더로도 안 뚫린다는 것을 다음 사람이 깨면 빨강을 낸다** (턴 AF · 차선 S).

왜 이 게이트가 필요한가
------------------------
`scripts/probe_fake_bearer.py` 가 어제(턴 AE) 읽기 면 364자리를 가짜
`Authorization` 값으로 두드려 **0건**을 냈다고 보고됐다. 그런데 그 스크립트를
**문서에 적힌 그대로** 불러 보면 [실측 2026-09-23 · 턴 AF]:

    ModuleNotFoundError: No module named 'config'

즉 **한 번도 돌 수 없었다.** 원인이 둘 있었다(이 턴에 `probe_fake_bearer.py`
자체를 고쳤다 — 그 파일의 머리말에 실측을 남겼다):

    ① `sys.path` 에 `/app`(장고 프로젝트 루트)을 안 얹어서 `django.setup()`
       자체가 죽는다. `-w /app` 은 **현재 디렉터리**만 옮길 뿐이다.
    ② `P.measure(caller, method, url, principal, query)` 의 다섯째 자리는
       **질의값**이지 헤더가 아니다. `{"Authorization": FAKE}` 를 거기 넣으면
       그 글자는 `?Authorization=Bearer+...` 로 **URL 뒤에 질의 문자열로 붙을
       뿐**, 실제 `Authorization:` HTTP 헤더는 한 번도 실리지 않았다.

즉 「가짜 헤더 0/364」는 **원래 스크립트로는 나올 수 없었던 수**였다 — 둘 다
고친 뒤 다시 재니 **정말로 364 · 0건**이었다(§S.md 실측 로그 참조). 그러나
세종 판정 P-273 은 「0/364 는 분모·증거·**회귀 게이트**가 있어야 closed」라고
했다 — 한 번의 초록은 다음 턴에 누가 `auth=` 를 빼도 아무 말도 안 한다.
이 파일이 그 회귀 게이트다.

이 게이트가 답하는 질문
------------------------
    **다음에 누가 어떤 읽기 라우트의 `auth=`(또는 관문 뒤의 다른 보호)를
    빼면 — 그 라우트가 가짜 `Authorization` 으로 실제 자료를 내주는 순간을
    이 게이트가 빨강으로 잡는가.**

판정식을 베끼지 않는다 (D-212)
-------------------------------
빨강 술어(`has_data`) · 공개 선언(`PUBLIC_READ_BY_DESIGN`)은
`scripts/probe_read_surface.py` 에서 **import** 한다. 면제 목록을 새로 만들지
않는다 — 공개 선언이 필요하면 그 표를 그대로 쓴다. 이 파일이 새로 갖는 것은
① 로그인 없이 가짜 헤더를 **실제로** 싣는 수집기(`collect_rows`, Django
in-process 시험 클라이언트) ② facts → 빨강 목록을 가르는 순수 함수
(`judge_rows` — 분류만 한다. 「자료가 있는가」의 답은 여전히 `has_data`
것이다)뿐이다.

★ 실계정·실토큰 0 — 로그인하지 않는다
--------------------------------------
`django.test.Client` 를 쓴다 — 살아있는 gunicorn(8000)에 의존하지 않고, 이
제품이 계정당 세션 하나뿐이라는 사정과도 무관하다(로그인 자체를 안 한다).
싣는 값은 `probe_fake_bearer.FAKE` **그 글자 그대로**(두 벌로 안 적는다) —
「어디에도 없는 글자」다.

★★ 음성 대조 (턴 AF 실측 · `--self-test`)
--------------------------------------------
`judge_rows()` 는 순수 함수라 **도커 없이** 시험된다(D-277, `ops_retention_
policy.judge` 와 같은 모양). 자기시험은 흉내 낸 facts 셋 셋을 먹인다:
① 관문이 선 자리(401 · data=False) → 안 걸림 ② 공개 선언 자리(data=True 지만
허용목록에 있음) → 안 걸림 ③ **`auth=` 가 없다고 흉내 낸 자리**(data=True ·
허용목록 밖) → **빨강**이어야 한다. ③이 안 잡히면 자기시험 자체가 실패
(EXIT 1)한다 — 「혼자 재면 통과」를 막는다(D-350).

    python scripts/gate_fake_bearer_regression.py --self-test      # 도커 없이 판정 규칙만
    docker exec -e DJANGO_SETTINGS_MODULE=config.settings -w /app gx-shell \\
        python /repo/scripts/gate_fake_bearer_regression.py \\
        docs/agent/evidence/P-270/fake_bearer_gate.json

부르는 방향: 이 파일에 `docker exec` 가 **없다** — HTTP·ORM 을 직접 쓰므로
**gx-shell 안** `-w /app` 에서 돈다(호스트에서는 `--self-test` 만 돈다).

종료 코드: 0 쟀고 0건 · 1 쟀고 자료가 나온 자리가 있다(**빨강**) · 2 못 쟀다
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2
TAG = "[P-273]"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: `common/access_gate.py::_has_credentials` 가 "들고 왔다"고만 보는 값과
#: **같은 값**이어야 한다 — `probe_fake_bearer.FAKE` 를 그대로 쓴다(두 벌로
#: 안 적는다). 자매 스크립트가 같은 디렉터리에 있으므로 스크립트 자신의
#: 경로만 얹으면 찾는다(파이썬이 자동으로 얹는 자리와 같다).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from probe_fake_bearer import FAKE  # noqa: E402  (경로 삽입 뒤에 와야 한다)
except ImportError:                                              # pragma: no cover
    # 최후 대비값 — 위 import 가 사는 한 이 줄은 안 쓰인다. 값은 반드시 같아야 한다.
    FAKE = "Bearer gx.nonexistent.probe.token.do-not-issue-this"

#: 캐시 처리: 우회 — `backend/tests/no_cache.py::NO_CACHE` 와 **같은 값**이다.
#: 판정식이 아니라 WSGI 헤더 이름 하나라서 D-212 대상이 아니다(D-341 착시 ⑦ —
#: 관문을 재는 시험이 캐시를 재면 안 된다).
NO_CACHE = {"HTTP_X_NO_CACHE": "true"}


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — 순수 함수, 도커 없이 시험된다 (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge_rows(rows, public=None):
    """facts → **빨강 목록**.

    `rows` 의 `data` 는 이미 `probe_read_surface.has_data()` 로 잰 값이다 —
    여기서 다시 재지 않는다(D-212, 판정은 한 곳에). 이 함수가 하는 일은
    「자료가 있는 자리 중 공개로 선언 안 된 자리」를 **가르는 것**뿐이다.

    Args:
        rows: `{"method", "path", "status", "data", "why", ...}` 목록.
        public: 공개로 선언된 자리(`probe_read_surface.PUBLIC_READ_BY_DESIGN`
            의 키 — 경로 문자열, 또는 `(method, path)` 쌍). `None` 이면 빈
            집합 — **면제 목록을 스스로 만들지 않는다**(지시 규약 §1).

    Returns:
        `data=True` 인데 `public` 에 없는 행만. 빈 목록이면 초록이다.
    """
    pub = set(public or ())
    leaked = []
    for r in rows:
        if not r.get("data"):
            continue
        if r.get("path") in pub or (r.get("method"), r.get("path")) in pub:
            continue
        leaked.append(r)
    return leaked


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — 가짜 라우트 facts 를 먹여 **빨강이 실제로 나는지** 증명한다
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    """★★ 음성 대조 — `auth=` 가 없다고 흉내 낸 자리 하나를 판정기에 먹인다.

    이 함수가 실측하는 것은 **살아 있는 라우트가 아니라 판정 규칙 자체**다.
    실제 라우트를 흉내 내는 이유: 실제 레지스트리를 건드리면(§ 실측 로그 참조)
    ninja_extra 의 `Operation.auth_callbacks` 를 실행 중에 지워도 디스패치가
    그 자리를 다시 안 읽어서 **아무 일도 안 일어나는** 경우가 있었다(빈 결과가
    아니라 "안 바뀜"이었다 — `/api/article` 로 실측, §S.md). 판정 규칙은
    facts 를 신뢰하지 레지스트리 내부 구조를 신뢰하지 않으므로, facts 를
    직접 먹이는 쪽이 **더 확실한** 음성 대조다.
    """
    fake_rows = [
        {"method": "GET", "path": "/api/fake/protected", "status": 401,
         "data": False, "why": "401 — 관문이 섰다 [흉내]"},
        {"method": "GET", "path": "/api/fake/public-door", "status": 200,
         "data": True, "why": "공개 선언 자리라 data=True 여도 괜찮다 [흉내]"},
        #: ★★ 이 한 행이 **음성 대조**다 — `auth=` 를 뺀 라우트를 흉내 낸다.
        #:   판정기가 이 행을 못 잡으면 이 게이트는 아무것도 안 잰 게이트다.
        {"method": "GET", "path": "/api/fake/no-auth-oops", "status": 200,
         "data": True,
         "why": "★ auth= 가 없다고 흉내 낸 자리 — 이 행이 빨강으로 잡혀야 한다"},
    ]
    public = {"/api/fake/public-door"}
    leaked = judge_rows(fake_rows, public)
    leaked_paths = sorted(r["path"] for r in leaked)

    bad = []
    if leaked_paths != ["/api/fake/no-auth-oops"]:
        bad.append("음성 대조가 빨강을 내지 못했다 — 잡힌 자리: %r (기대: "
                    "['/api/fake/no-auth-oops'])" % leaked_paths)
    if judge_rows([], set()) != []:
        bad.append("빈 facts 에서 빨강이 났다")
    if judge_rows([{"method": "GET", "path": "/x", "status": 401,
                    "data": False}], set()):
        bad.append("401 · data=False 인 행이 빨강으로 잡혔다(정상 갈래가 안 초록이다)")

    print("%s [입력] 자기시험 facts %d개(흉내 · 실제 라우트 0개) — 도커·DB 없이 "
          "판정 규칙(judge_rows)만 잰다" % (TAG, len(fake_rows)))
    print("%s AS=**없는 토큰**(%s) · SOURCE=자기시험 흉내 facts(레지스트리 아님) · "
          "MEASURED=judge_rows() 순수 함수 하나" % (TAG, FAKE))
    if bad:
        print("%s 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):" % TAG)
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print("%s 자기시험 통과 — 정상 갈래 2(401 · 공개선언) · 음성 대조 1"
          "(★ auth= 없는 자리를 빨강으로 잡았다: %r)" % (TAG, leaked_paths))
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 실측 — Django in-process 로 읽기 면 전수를 두드린다 (gx-shell 안)
# ═══════════════════════════════════════════════════════════════════════════
def collect_rows(client, P, iter_ninja_apis, join_fn):
    """읽기 면 전수를 **가짜 `Authorization` 헤더로** 두드려 facts 를 낸다.

    ★ 분모는 살아 있는 라우터 전수다(P-99 그대로) — 손으로 추리지 않는다.
    ★ 로그인하지 않는다 — `django.test.Client` 는 세션이 없고, 이 값은
      어디에도 없는 글자라 남의 세션·잠금 계수기를 건드리지 않는다.

    Args:
        client: `django.test.Client` 인스턴스.
        P: `probe_read_surface` 모듈(READ_METHODS · fill_path · probe_url ·
            has_data 를 그대로 쓴다 — D-212).
        iter_ninja_apis / join_fn: `common.tenant_scope._iter_ninja_apis` /
            `_join` — probe 들과 **같은** 레지스트리 순회.
    """
    rows = []
    for mount, api in iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (
                    getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    methods = [str(m).upper()
                               for m in (getattr(op, "methods", []) or [])]
                    read_methods = [m for m in methods if m in P.READ_METHODS]
                    if not read_methods:
                        continue
                    path = join_fn(mount, prefix, op_path)
                    url = P.fill_path(P.probe_url(path, mount, prefix, op_path), {})
                    for method in read_methods:
                        call = client.get if method == "GET" else client.head
                        resp = call(url, follow=True, HTTP_AUTHORIZATION=FAKE,
                                    **NO_CACHE)
                        data, why, units, keys = P.has_data(
                            resp.status_code, resp.content or b"")
                        rows.append({
                            "method": method, "path": path,
                            "status": resp.status_code, "data": data,
                            "why": why, "units": units, "keys": keys[:6],
                        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", help="결과 JSON 경로(생략 가능)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    #: 판정 규칙이 살아 있는지 **먼저** 확인한다 — 규칙이 안 서면 실측도 못 믿는다.
    rc = self_test()
    if rc != EXIT_OK:
        print("%s **멈춘다** — 자기시험이 먼저 실패했다. 판정 규칙을 먼저 "
              "의심한다 (D-350)" % TAG)
        return rc

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    #: ★★ [턴 AF 실측] `config.settings` 는 `/app`(gx-shell 의 장고 프로젝트
    #:   루트)에 있다. 이 줄이 없으면 `django.setup()` 이
    #:   `ModuleNotFoundError: No module named 'config'` 로 **매번** 죽는다.
    sys.path.insert(0, "/app")
    try:
        import django
        django.setup()
        import probe_read_surface as P
        from common.tenant_scope import _iter_ninja_apis, _join
        from django.test import Client
    except Exception as exc:                                    # noqa: BLE001
        print("%s **못 쟀다** — 환경을 못 세웠다: %s: %s"
              % (TAG, type(exc).__name__, exc))
        print("%s gx-shell 안에서 DJANGO_SETTINGS_MODULE 을 주고 -w /app 으로 부른다"
              % TAG)
        return EXIT_UNDECIDABLE

    client = Client(raise_request_exception=False, **NO_CACHE)
    t0 = time.time()
    rows = collect_rows(client, P, _iter_ninja_apis, _join)
    public = set(getattr(P, "PUBLIC_READ_BY_DESIGN", ()) or ())
    leaked = judge_rows(rows, public)

    payload = {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total": len(rows), "elapsed_s": round(time.time() - t0, 1),
        "leaked": len(leaked), "rows_leaked": leaked[:40],
    }
    if args.out:
        out_dir = os.path.dirname(args.out)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)

    print("%s TARGET=Django in-process Client (gx-shell 안 · 로그인 0회 · "
          "localhost:8000 과 무관)" % TAG)
    print("%s AS=**없는 토큰**(%s) · 실계정·실토큰 0" % (TAG, FAKE))
    print("%s SOURCE=살아 있는 라우터 레지스트리(런타임 전수)" % TAG)
    print("%s MEASURED=읽기 면 전수를 가짜 헤더로 두드린다 — **분모 %d**(지금 "
          "셌다). 가짜 헤더로도 2xx + 자료가 나오면 그 자리의 `auth=`(또는 "
          "관문 뒤의 다른 보호)가 빠진 것이다" % (TAG, len(rows)))
    print("%s [입력] 읽기 자리 %d · %.1f초 · 자기시험 통과 뒤 실측"
          % (TAG, len(rows), payload["elapsed_s"]))
    print("%s 가짜 헤더로 **자료가 나온 자리 %d**" % (TAG, len(leaked)))
    for r in leaked[:12]:
        print("%s   · %-4s %-52s %s · %s"
              % (TAG, r["method"], r["path"][:52], r["status"], r["why"][:50]))
    if args.out:
        print("%s 기록 → %s" % (TAG, args.out))
    if leaked:
        print("%s **빨강** — 이 라우트들의 `auth=`(또는 관문 뒤의 다른 보호)가 "
              "빠졌다. 고칠 자리는 이 게이트가 아니라 그 라우트들이다" % TAG)
        return EXIT_FAIL
    print("%s 초록 — 가짜 자격증명으로 자료가 나오는 자리가 **0** 이다" % TAG)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
