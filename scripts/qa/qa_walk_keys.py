# -*- coding: utf-8 -*-
"""QA 10키 진입 실측 — WO-GRDX-20261007-01 T1 레인 S · 규격 09 M2 + 역할 격리 1회.

호스트에서 `http://127.0.0.1:8510` 을 때린다(QA 판만 · 8500 에는 `/qa/*` 가 없다).
키마다: `GET /qa/as/<키>` → 302 `/qa/enter?h=…` → `POST /qa/handoff` → 토큰으로 `GET /api/v1/auth/profile`.
격리: 관제요원 키(`operator_basic_01`)의 토큰으로 사람 목록 `GET /api/v1/user/list` → 403/404 여야 한다.
토큰·인계표 값은 찍지 않는다(길이·상태코드만).

    python scripts/qa/qa_walk_keys.py            # 표 출력 · exit 0 = 10/10 + 격리 통과
"""
from __future__ import annotations

import http.cookiejar
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8510"
ISOLATION_KEY = "operator_basic_01"
PEOPLE_LIST = "/api/v1/user/list"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _opener():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(_NoRedirect, urllib.request.HTTPCookieProcessor(jar))


def _call(op, method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        r = op.open(req, timeout=60)
        return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def enter(key: str):
    op = _opener()
    st, hd, _ = _call(op, "GET", f"/qa/as/{key}")
    loc = hd.get("Location", "")
    row = {"account": key, "as": st, "to_enter": loc.startswith("/qa/enter?h=")}
    if st != 302 or not row["to_enter"]:
        return row, None
    h = loc.split("h=", 1)[1]
    st2, _, b2 = _call(op, "POST", "/qa/handoff", {"h": h})
    row["handoff"] = st2
    if st2 != 200:
        return row, None
    data = json.loads(b2)
    token = data["user"]["access_token"]
    row["first_path"] = data.get("first_path")
    st3, _, b3 = _call(op, "GET", "/api/v1/auth/profile", token=token)
    row["profile"] = st3
    row["role_required"] = st3 == 403 and b"role_required" in b3  # 역할 0 키는 이것이 정답(역할 관문 설계)
    try:
        prof = json.loads(b3)
        row["username"] = (prof.get("data") or prof).get("username") if isinstance(prof, dict) else None
    except ValueError:
        row["username"] = None
    st4, _, _ = _call(op, "POST", "/qa/handoff", {"h": h})
    row["handoff_again"] = st4
    return row, token


def main() -> int:
    from apps_keys import QA_KEYS  # noqa: E402  (아래 _load 가 넣는다)
    ok = 0
    tokens = {}
    for key in QA_KEYS:
        row, token = enter(key)
        tokens[key] = token
        expect_pending = QA_KEYS[key].get("owner") is None
        profile_ok = row.get("role_required") if expect_pending else row.get("profile") == 200
        good = row.get("as") == 302 and row.get("handoff") == 200 and bool(profile_ok) and row.get("handoff_again") == 404
        ok += good
        print(("OK  " if good else "BAD ") + json.dumps(row, ensure_ascii=False))
    # 격리 — 같은 키로 다시 들어가 새 토큰(동시 세션 1개: 위 토큰은 다른 키 진입과 무관하지만, 확실히 새로)
    _, token = enter(ISOLATION_KEY)
    st, _, _ = _call(_opener(), "GET", PEOPLE_LIST, token=token)
    iso = st in (403, 404)
    print(f"{'OK  ' if iso else 'BAD '}isolation {ISOLATION_KEY} GET {PEOPLE_LIST} -> {st}")
    print(f"[QA-WALK] 진입 {ok}/{len(QA_KEYS)} · 격리 {'통과' if iso else '실패'}")
    return 0 if ok == len(QA_KEYS) and iso else 1


def _load():
    import importlib.util
    import pathlib
    p = pathlib.Path(__file__).resolve().parents[2] / "backend" / "apps" / "qa" / "keys.py"
    spec = importlib.util.spec_from_file_location("apps_keys", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules["apps_keys"] = mod


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    _load()
    sys.exit(main())
