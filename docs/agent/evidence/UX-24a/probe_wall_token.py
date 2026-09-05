# -*- coding: utf-8 -*-
"""UX-24a 실측 탐침 — **월 토큰으로 열고, 자리 세션이 사는가**를 HTTP 로 잰다.

    docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
      python /docs/agent/evidence/UX-24a/probe_wall_token.py'

왜 시험 말고 이것도 하나 — **단위 시험은 함수를 부르고 브라우저는 라우트를 때린다**(D-386).
미들웨어 순서·응답 캐시·앞단 프록시는 시험 클라이언트에 안 보인다.

⚠ 캐시 처리: **우회** — 모든 요청에 `X-No-Cache: true`. 적중한 응답은 언제나 200 이라
  이 탐침이 캐시를 재면 전부 초록이 된다(실측된 함정).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

#: 이 파일은 `/docs` 에 산다 — 컨테이너에서 저장소는 `/app`(과 `/repo/backend`)이다.
#: 넣지 않으면 `config` 를 못 찾는다 [실측: ModuleNotFoundError: No module named 'config'].
for _base in ("/app", "/repo/backend"):
    if os.path.isdir(_base) and _base not in sys.path:
        sys.path.insert(0, _base)

API = os.environ.get("GX_API", "http://localhost:8000")
USER = os.environ.get("GX_ROUTE_USER")
PASSWORD = os.environ.get("GX_ROUTE_PASSWORD")

DESK_ROUTE = "/api/dsm/events?limit=1"
WALL_ROUTES = ("/api/dsm/events/queue?limit=5", "/api/dsm/cameras/pulse")

WRITE_PROBES = [
    ("POST", "/api/dsm/events/1/review"),
    ("POST", "/api/dsm/events/1/response"),
    ("POST", "/api/dsm/events/1/notify"),
    ("POST", "/api/dsm/events/1/field-reply"),
    ("POST", "/api/dsm/settings/thresholds"),
    ("POST", "/api/dsm/settings/zones"),
    ("POST", "/api/dsm/settings/api-keys"),
    ("POST", "/api/dsm/settings/grade-rules"),
    ("DELETE", "/api/dsm/settings/api-keys/1"),
    ("POST", "/api/dsm/settings/api-keys/1/rotate"),
    ("POST", "/api/dsm/drill"),
    ("POST", "/api/dsm/cameras/import"),
    ("POST", "/api/dsm/webhook-subscriptions"),
    ("POST", "/api/delivery/etri-mock/receive-delivery"),
    ("POST", "/api/orders/banks"),
    ("POST", "/api/terminals/terminals"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/logout"),
    ("POST", "/api/dsm/events/queue"),
    ("PUT", "/api/dsm/cameras/pulse"),
]

OUT_OF_SCOPE_READS = [
    "/api/dsm/events",
    "/api/dsm/events/1",
    "/api/dsm/events/1/clip/stream",
    "/api/dsm/settings/api_keys",
    "/api/dsm/metering",
    "/api/delivery/drone-monitoring/drone-status",
]


def hit(method, path, *, bearer=None, wall=None, body=None):
    req = urllib.request.Request(API + path, data=body, method=method)
    req.add_header("X-No-Cache", "true")
    if bearer:
        req.add_header("Authorization", "Bearer " + bearer)
    if wall:
        req.add_header("X-GX-Wall-Token", wall)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read()[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200]
    except Exception as e:                                # noqa: BLE001
        return 0, repr(e)[:200].encode()


def login():
    body = json.dumps({"username": USER, "password": PASSWORD,
                       "end_previous_session": True}).encode()
    req = urllib.request.Request(API + "/api/v1/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        payload = json.loads(r.read().decode("utf-8", "replace"))
    return ((payload.get("user") or {}).get("access_token"), payload.get("success"))


def stored_session(username):
    """`user.token` 을 DB 에서 그대로 읽는다 — 「안 만졌다」를 눈으로 본다."""
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    from django.contrib.auth import get_user_model

    u = get_user_model().objects.filter(username=username).only("id", "token").first()
    return (u.id if u else None), (u.token if u else None)


def main():
    if not (USER and PASSWORD):
        print("[UX-24a] 자격증명이 없다 — **판정 불가**")
        return 2

    uid, before = stored_session(USER)
    print(f"[UX-24a] 대상 계정 id={uid}")

    from common.wall_token import issue

    wall_token, claims = issue(uid, note="probe")
    print(f"[UX-24a] 월 토큰 발급 jti={claims['jti']} "
          f"수명={claims['exp'] - claims['iat']}초")

    access, ok = login()
    print(f"[UX-24a] ① 자리 로그인 success={ok} 토큰={'있다' if access else '없다'}")
    uid, before = stored_session(USER)

    st, _ = hit("GET", DESK_ROUTE, bearer=access)
    print(f"[UX-24a] ② 자리 화면 {DESK_ROUTE} → {st}")
    desk_first = st

    for path in WALL_ROUTES:
        st, body = hit("GET", path, wall=wall_token)
        print(f"[UX-24a] ③ 월 토큰으로 {path} → {st}  {body[:80]!r}")

    st, _ = hit("GET", DESK_ROUTE, bearer=access)
    print(f"[UX-24a] ④ **월을 켠 뒤** 자리 화면 → {st}  (①과 같아야 한다: {desk_first})")
    desk_after = st

    _uid, after = stored_session(USER)
    print(f"[UX-24a] ⑤ user.token 이 바뀌었나 → {'바뀌었다' if before != after else '그대로다'}")

    refused, opened = 0, []
    for method, path in WRITE_PROBES:
        st, body = hit(method, path, wall=wall_token, body=b"{}")
        if st in (401, 403):
            refused += 1
        else:
            opened.append((method, path, st, body[:60]))
    print(f"[UX-24a] ⑥ 쓰기 문 {len(WRITE_PROBES)}개 두드림 → **거부 {refused}** · 열림 {len(opened)}")
    for row in opened:
        print(f"[UX-24a]     ✗ 열렸다: {row}")

    r_refused, r_opened = 0, []
    for path in OUT_OF_SCOPE_READS:
        st, body = hit("GET", path, wall=wall_token)
        if st in (401, 403):
            r_refused += 1
        else:
            r_opened.append((path, st, body[:60]))
    print(f"[UX-24a] ⑦ 목록 밖 읽기 {len(OUT_OF_SCOPE_READS)}개 → **거부 {r_refused}** · 열림 {len(r_opened)}")
    for row in r_opened:
        print(f"[UX-24a]     ✗ 열렸다: {row}")

    bad = []
    if desk_after != desk_first:
        bad.append(f"자리 화면이 달라졌다 {desk_first} → {desk_after}")
    if before != after:
        bad.append("월이 user.token 을 건드렸다")
    if refused != len(WRITE_PROBES):
        bad.append("쓰기 문이 열렸다")
    if r_refused != len(OUT_OF_SCOPE_READS):
        bad.append("목록 밖 읽기가 열렸다")
    if bad:
        print("[UX-24a] ✗ 실패: " + " · ".join(bad))
        return 1
    print("[UX-24a] 통과 — 월이 열리고 자리가 살아 있고 쓰기가 0 이다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
