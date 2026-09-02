#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""인증 경로 대장 판정 — **면마다 어느 문으로 들어가는가** (P-15).

    "게이트는 다른 길로 들어갔다. 그러면 실제 클라이언트는 어느 길로 들어가나?
     모바일 M1~M3 는 로그인이 첫 화면이다. **죽은 인증 길 위에 화면을 세우지 않는다.**"

이 저장소에는 「토큰」이라 불리는 것이 셋 있고 셋은 서로 다른 것이다:

    JWT(pair)     `/api/token/pair` 가 주는 것. **남이 세운 세션에 기생한다** —
                  세션이 없으면 401, 있으면 200. 스스로는 세션을 못 세운다 [실측]
    user.token    `/api/v1/auth/login` 이 DB 에 심는 세션 표식. dj-core 가 이것을 본다
    inbound_api_key  외부 App 이 **들고 오는** 것(`X-API-Key`). 선언한 라우트에서만 통한다
                     — 방향을 이름에 붙인다(D-337): 나가는 키와 다른 것이다

한 이름으로 부르면 「토큰을 받았다」가 「들어갈 수 있다」로 읽힌다. 2026-09-17 에
게이트가 정확히 그 착각으로 초록을 냈다 — 26건 중 24건이 401 인 채로.

★ 그리고 그 사실은 **이미 저장소에 있었다.** `tests/test_api_contract.py` 의
  `test_token_pair_issues_tokens_that_do_not_work` 가 그 계약을 못박아 두고 있었다.
  **저장소가 아는 것과 도구가 아는 것은 다른 것이다** — 그래서 이 판정기가 있다.

    python scripts/verify_authn_paths.py            # 판정
    python scripts/verify_authn_paths.py --self-test

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 **못 쟀다**(서버·자격증명 없음)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_route_alive import (  # noqa: E402  — **같은 눈으로 읽는다** (D-369)
    LOGIN_PATHS,
    delegate_to_container,
    load_local_env,
    login,
)

ROOT = Path(__file__).resolve().parent.parent
#: 대장이 어디에 있나. 컨테이너는 저장소가 `/repo`, 문서가 `/docs` 로 **따로** 붙는다 —
#: `/repo/docs` 는 없다. 한 자리로 못 박으면 컨테이너 안에서 「대장이 없다」로 죽는다
#: [실측 2026-09-18]. `verify_route_alive._routes_file()` 이 같은 이유로 같은 모양이다.
def _ledger() -> Path:
    tail = Path("agent") / "authn_paths.md"
    for base in (ROOT / "docs", Path("/docs")):
        if (base / tail).is_file():
            return base / tail
    return ROOT / "docs" / tail


LEDGER = _ledger()
EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 제품이 실제로 세션을 세우는 문. 번들에서 실측한 값이다 — 우리가 고른 것이 아니다.
PRODUCT_LOGIN = "/api/v1/auth/login"
#: 토큰은 주지만 **세션을 못 세우는** 문. 세션이 이미 있으면 그 토큰도 통한다 —
#: 그래서 「죽었다」가 아니라 **「기생한다」**가 정확한 말이다 [실측 2026-09-18].
DEAD_LOGIN = "/api/token/pair"
#: 로그인이 통했는지 보는 자리. 출생 표본이기도 하다(500 을 내던 그 라우트).
GATED_ROUTE = "/api/dsm/events?limit=1"

#: ★ **출생 표본** (D-310) — 이 판정기를 만들게 한 그날의 두 수.
#:   [실측 2026-09-17] `/api/token/pair` 로 받은 토큰으로 26건을 때려 **24건이 401**.
BIRTH_SAMPLE_WRONG_DOOR = (26, 24)

#: ★ 도달 불가 쓰기 면 — **래칫** (D-311). [실측 2026-09-18]
#:   `GET /api/dsm/settings/{domain}` 이 같은 자리를 먼저 먹어, 아래 넷은 **405** 다.
#:   단위 시험은 서비스 함수를 직접 부르므로 **전부 초록**이었다 — D-386 이 이름 붙인 층이다.
#:   ⚠ 이 목록은 「괜찮다」가 아니라 「오늘 이만큼이고 늘면 빨개진다」는 뜻이다.
SHADOWED_WRITE_ROUTES = (
    ("POST", "/api/dsm/settings/api-keys"),      # F-05 API Key 발급
    ("POST", "/api/dsm/settings/thresholds"),    # F-12 임계값
    ("POST", "/api/dsm/settings/zones"),         # F-12 구역
    ("POST", "/api/dsm/settings/grade-rules"),   # F-12 등급규칙
)

#: 화면 번들에서 **실제로 나가는 주소**를 읽는다. 손으로 적으면 곧 옛말이 된다.
BUNDLE_GLOBS = ("backend/_fe_dist/assets/*.js", "frontend/dist/assets/*.js")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def bundle_login_paths() -> tuple[set[str], int]:
    """빌드된 화면이 부르는 로그인·토큰 주소. (찾은 주소들, 훑은 파일 수)"""
    found: set[str] = set()
    files = 0
    pat = re.compile(r"/api/[A-Za-z0-9/_-]*(?:login|token[A-Za-z0-9/_-]*)")
    for glob in BUNDLE_GLOBS:
        base, _, tail = glob.partition("/assets/")
        for path in (ROOT / base).glob("assets/" + tail):
            files += 1
            try:
                found.update(pat.findall(path.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                continue
    return found, files


def request(api: str, method: str, path: str, *, token: str | None = None,
            body: bytes | None = None) -> int:
    req = urllib.request.Request(api + path, data=body, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:                                   # noqa: BLE001
        return 0


def issue_pair_token(api: str, user: str, password: str) -> str | None:
    body = json.dumps({"username": user, "password": password}).encode()
    req = urllib.request.Request(api + DEAD_LOGIN, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8", "replace")).get("access")
    except Exception:                                   # noqa: BLE001
        return None


def self_test() -> int:
    """판정 규칙과 출생 표본 (D-277 · D-310)."""
    bad: list[str] = []
    n, gated = BIRTH_SAMPLE_WRONG_DOOR
    if gated >= n:
        bad.append("출생 표본 — 401 이던 수가 때린 수보다 크거나 같다")
    if gated == 0:
        bad.append("출생 표본 — 그날 401 은 24건이었다. 0 이면 이 도구가 태어난 이유가 사라진다")
    if LOGIN_PATHS[0] != PRODUCT_LOGIN:
        bad.append(f"판정기의 로그인 첫 경로가 {LOGIN_PATHS[0]} 다 — 제품의 문은 {PRODUCT_LOGIN}")
    if DEAD_LOGIN in LOGIN_PATHS[:1]:
        bad.append(f"{DEAD_LOGIN} 를 **먼저** 묻는다 — 세션 없는 JWT 를 받아 전부 401 이 된다")
    if not LEDGER.is_file():
        bad.append(f"대장이 없다: {LEDGER.relative_to(ROOT)} — 판정만 있고 기록이 없으면 "
                   f"다음 사람은 같은 자리에서 다시 헤맨다 (P-15)")
    if len(SHADOWED_WRITE_ROUTES) == 0:
        bad.append("도달 불가 기준선이 비었다 — 0 이면 래칫이 아무것도 안 지킨다")
    #: 음성 갈래 — 기준선 항목은 **전부 쓰기 메서드**여야 한다. 읽기가 섞이면
    #: 「쓰기 면이 막혔다」는 이 목록의 뜻이 흐려진다.
    for method, path in SHADOWED_WRITE_ROUTES:
        if method not in ("POST", "PUT", "PATCH", "DELETE"):
            bad.append(f"기준선에 읽기 메서드가 있다: {method} {path}")
    if bad:
        print("[AUTHN] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print(f"[AUTHN] 자기시험 통과 — 출생 표본({gated}/{n} 401) · 로그인 첫 경로 · "
          f"대장 실재 · 도달불가 기준선 {len(SHADOWED_WRITE_ROUTES)}건(전부 쓰기)")
    return EXIT_OK


def main() -> int:
    _env_files = load_local_env()
    ap = argparse.ArgumentParser(description="인증 경로 대장 판정 (P-15)")
    ap.add_argument("--api", default=os.environ.get("GX_API", "http://localhost:8000"))
    ap.add_argument("--user", default=os.environ.get("GX_ROUTE_USER"))
    ap.add_argument("--password", default=os.environ.get("GX_ROUTE_PASSWORD"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    rc = EXIT_OK

    # ── 면 ① 웹 UI — **번들이 실제로 부르는 주소** (서버 없이 잰다) ──────────
    paths, files = bundle_login_paths()
    print(f"[AUTHN] [입력] {files}건 — 훑은 화면 번들 파일")
    if files == 0:
        print("[AUTHN]   · 번들이 없다 — 화면 면은 **판정 불가**(빌드 후 다시 잰다)")
    else:
        has_product = any(p.endswith("/auth/login") for p in paths)
        has_dead = any(p == DEAD_LOGIN for p in paths)
        print(f"[AUTHN]   웹 UI 가 부르는 로그인·토큰 주소: {sorted(paths) or '없음'}")
        if not has_product:
            print(f"[AUTHN] ✗ 화면이 {PRODUCT_LOGIN} 를 부르지 않는다 — 대장이 옛말이다")
            rc = EXIT_FAIL
        if has_dead:
            print(f"[AUTHN] ✗ 화면이 {DEAD_LOGIN} 를 부른다 — **죽은 문 위에 화면이 서 있다**")
            rc = EXIT_FAIL

    container = os.environ.get("GX_ROUTE_CONTAINER", "").strip()
    if container and not os.environ.get("GX_ROUTE_IN_CONTAINER"):
        os.environ.setdefault("GX_API", "http://localhost:8000")
        if args.user:
            os.environ["GX_ROUTE_USER"] = args.user
        if args.password:
            os.environ["GX_ROUTE_PASSWORD"] = args.password
        return delegate_to_container(container, None, script="verify_authn_paths.py")

    if not (args.user and args.password):
        print(f"[AUTHN] 자격증명이 없다 ({' / '.join(('GX_ROUTE_USER', 'GX_ROUTE_PASSWORD'))})")
        print("[AUTHN] **판정 불가** — 때려 보지 못한 것을 초록으로 적지 않는다 (D-301)")
        return EXIT_UNDECIDABLE

    # ── 면 ② 제품 로그인 — 받은 토큰이 **실제로 문을 여는가** ────────────────
    token = login(args.api, args.user, args.password)
    if not token:
        print("[AUTHN] 제품 로그인에서 토큰을 못 받았다 — **판정 불가**")
        return EXIT_UNDECIDABLE
    st = request(args.api, "GET", GATED_ROUTE, token=token)
    print(f"[AUTHN] [입력] 1건 — {PRODUCT_LOGIN} 토큰으로 {GATED_ROUTE} → {st}")
    if not 200 <= st < 300:
        print("[AUTHN] ✗ 제품의 문으로 들어갔는데 막힌다 — 이 대장이 통째로 옛말이다")
        rc = EXIT_FAIL

    # ── 면 ③ `/api/token/pair` — **기생한다**는 성질을 두 갈래로 잰다 ────────
    #
    #   ★ [실측 2026-09-18] 이 판정기가 **제 대장을 반박했다.** 처음엔 「pair 토큰은
    #     어디서도 401」이라 적었는데, 재어 보니 **200** 이었다. 직전에 로그인이
    #     세션을 세워 두었기 때문이다. **한 갈래만 재면 어느 쪽이든 그럴듯하다.**
    #
    #       세션(`user.token`) 없음 → 401        세션 있음 → 200
    #
    #   즉 이 문은 죽은 것이 아니라 **남이 세운 세션에 기생한다.** 스스로는 못 세운다.
    #   `tests/test_api_contract.py` 의 계약 시험이 참인 것도 그 setUp 이 로그인을
    #   하지 않기 때문이다 — **시험은 옳고, 문장이 너무 넓었다.**
    #   ⚠ 이 갈래를 만들려면 탐침 계정을 **로그아웃시켜야 한다.** 탐침 계정만 건드리고
    #     끝나면 다시 로그인해 되돌린다.
    pair_no_session = pair_with_session = None
    pair = issue_pair_token(args.api, args.user, args.password)
    if pair:
        request(args.api, "POST", "/api/v1/auth/logout", token=pair, body=b"{}")
        fresh = issue_pair_token(args.api, args.user, args.password)
        if fresh:
            pair_no_session = request(args.api, "GET", GATED_ROUTE, token=fresh)
        token = login(args.api, args.user, args.password) or token
        again = issue_pair_token(args.api, args.user, args.password)
        if again:
            pair_with_session = request(args.api, "GET", GATED_ROUTE, token=again)
    print(f"[AUTHN] [입력] 2건 — {DEAD_LOGIN} 토큰을 두 갈래로 때렸다: "
          f"세션 없을 때 {pair_no_session} · 세션 있을 때 {pair_with_session}")
    if pair_no_session != 401:
        print(f"[AUTHN] ✗ 세션 없이 발급한 {DEAD_LOGIN} 토큰이 {pair_no_session} 다 — "
              f"이 문이 **스스로 세션을 세우게 되었다.** 연동 문서와 계약 시험을 고쳐라")
        rc = EXIT_FAIL
    if pair_with_session is not None and not 200 <= pair_with_session < 300:
        print(f"[AUTHN] ✗ 세션이 있는데도 {pair_with_session} 다 — 대장의 「기생한다」가 "
              f"옛말이 되었다. 다시 재고 대장을 고쳐라")
        rc = EXIT_FAIL

    # ── 면 ④ 외부 App 의 키 면 — **발급 문 자체가 도달 불가다** ──────────────
    dead = []
    for method, path in SHADOWED_WRITE_ROUTES:
        st = request(args.api, method, path, token=token, body=b"{}")
        if st == 405:
            dead.append((method, path))
    print(f"[AUTHN] [입력] {len(SHADOWED_WRITE_ROUTES)}건 — 선언된 쓰기 라우트 도달성 "
          f"(405 = 도달 불가)")
    for method, path in dead:
        print(f"[AUTHN]   · 도달 불가 {method:6} {path} "
              f"— `GET /api/dsm/settings/{{domain}}` 이 같은 자리를 먼저 먹는다")
    if len(dead) > len(SHADOWED_WRITE_ROUTES):
        print("[AUTHN] ✗ 도달 불가가 기준선보다 늘었다 — 래칫 D-311")
        rc = EXIT_FAIL
    elif len(dead) < len(SHADOWED_WRITE_ROUTES):
        print(f"[AUTHN]   ★ 도달 불가가 {len(SHADOWED_WRITE_ROUTES)} → {len(dead)} 로 줄었다 — "
              f"기준선을 함께 내려라")

    if rc == EXIT_OK:
        print(f"[AUTHN] 통과 — 제품의 문 하나({PRODUCT_LOGIN})가 세션을 세우고, "
              f"{DEAD_LOGIN} 는 **스스로 못 세우며**(세션 없이 401), "
              f"화면은 그 문 위에 서 있지 않다")
    return rc


if __name__ == "__main__":
    sys.exit(main())
