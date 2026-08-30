#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""화면이 쓰는 라우트를 **실제 HTTP 로 때린다** — 단위 시험이 못 보는 층 (D-386).

    "캡처 첫 시도에서 `/api/dsm/events` 가 **500** 이었다.
     **단위 시험 530건이 전부 초록인 채로** 그 라우트는 운영에서 죽어 있었다."

단위 시험은 **함수를 부른다.** 브라우저는 **라우트를 때린다.** 그 사이에 URL 배선·
스키마 해석·직렬화·권한·미들웨어 순서가 다 들어 있고, 단위 시험은 그 전부를 건너뛴다.
그래서 이 판정기가 있다 — **단위가 전부 초록이어도 독립적으로 빨개질 수 있어야 한다.**
그것이 존재 이유다(D-386).

무엇을 때리나 — **우리가 정하지 않는다**
----------------------------------------
`scripts/capture_screens.py` 가 화면을 지나며 **브라우저가 실제로 부른 API** 를 적어 둔
`docs/agent/evidence/D-386/screen_routes.json` 을 읽는다. 목록을 손으로 적으면 화면이
새 API 를 부르기 시작한 날 이 판정기만 옛말을 하게 된다.

    python scripts/verify_route_alive.py --user gxprobe_e2e --password ****
    python scripts/verify_route_alive.py --self-test      # 판정 규칙 대조 (D-277 · D-310)

★ D-310 자기표본: **500 을 내던 그 라우트**(`/api/dsm/events`)를 자기시험에 박았다.
  목록에서 그 라우트가 사라지면 자기시험이 먼저 실패한다 — 눈이 감기는 것을 눈이 본다.

종료 코드
    0 전부 살아 있다 · 1 죽은 라우트가 있다 · 2 **판정 불가**(서버 미기동·자격증명 없음)
★ 2 는 실패가 아니고 **통과는 더더욱 아니다.** 때려 보지 못한 것을 초록으로 적지 않는다(D-301).
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

ROOT = Path(__file__).resolve().parent.parent
EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 증거가 어디에 있나. 컨테이너는 저장소가 `/repo`, 문서가 `/docs` 로 **따로** 붙는다 —
#: `/repo/docs` 는 없다. 한 자리로 못 박으면 컨테이너에서 「목록이 없다」로 죽는다 [실측].
def _routes_file() -> Path:
    tail = Path("agent") / "evidence" / "D-386" / "screen_routes.json"
    for base in (ROOT / "docs", Path("/docs")):
        if (base / tail).is_file():
            return base / tail
    return ROOT / "docs" / tail


#: ★ **출생 표본** (D-310) — 이 도구를 만들게 한 사례는 합성이 아니다:
#:   [실측 2026-09-12] 화면을 처음 띄운 순간 `GET /api/dsm/events` 가 **500** 이었다
#:   (pydantic `QueryParams is not fully defined` — 미래 임포트 + @tenant_scoped).
#:   **단위 시험 530건이 전부 초록인 채로** 그 라우트는 운영에서 죽어 있었다.
#:   아래 자기시험이 그 사례 그대로를 판정한다 — 합성 상태 코드가 아니라 그날의 세 값으로.
BIRTH_SAMPLE = ("GET", "/api/dsm/events", 500)

#: ★ 자기표본 (D-310). 이 라우트가 목록에 없으면 **판정기부터 의심한다** — 이번 국면에서
#:   실제로 500 을 내던 자리이고, 화면을 띄우기 전에는 아무도 몰랐다.
SELF_SAMPLE = "/api/dsm/events"

#: 값이 든 경로(`/api/dsm/events/4674`)는 그 순간의 씨앗을 가리킨다. 씨앗은 캡처가 끝나며
#: 지워지므로(D-347 ④) 지금 때리면 404 가 정상이다 — **때리지 않고, 몇 건인지 말한다**(D-301).
_HAS_ID = re.compile(r"/\d+(?:/|$)")


def judge(status: int) -> tuple[bool, str]:
    """상태 코드 하나를 판정한다. **규칙을 함수로 떼어 둔 이유는 시험하기 위해서다.**

    · 2xx      살아 있다
    · 401/403  **살아 있다.** 문지기가 선 것은 라우트가 죽은 것이 아니다(F-09 는 그것을 원한다)
    · 5xx      죽었다 — 이번 국면이 잡으려는 바로 그것
    · 그 밖    죽었다(404 포함) — 화면이 부르는데 없는 자리다
    """
    if 200 <= status < 300:
        return True, "산다"
    if status in (401, 403):
        return True, "문지기가 섰다(살아 있다)"
    if status >= 500:
        return False, "**서버 오류** — 화면이 부르는 자리가 죽었다"
    return False, "없거나 못 받는다"


def load_routes(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    pairs: set[tuple[str, str]] = set()
    skipped: list[str] = []
    for _screen, calls in data.get("screens", {}).items():
        for c in calls:
            if c.get("method", "GET").upper() != "GET":
                continue
            p = c["path"]
            #: id 판정은 **경로 부분만** 본다 — `?page_size=10000` 의 숫자는 씨앗이 아니다
            if _HAS_ID.search(p.split("?", 1)[0]):
                skipped.append(p)
                continue
            pairs.add((c.get("method", "GET").upper(), p))
    return sorted(pairs), sorted(set(skipped))


def login(api: str, user: str, password: str) -> str | None:
    """제품의 로그인으로 토큰을 받는다. **못 받으면 못 받았다고 말한다** — 익명으로 때려
    401 만 잔뜩 보고 「전부 살아 있다」로 적는 것이 이 판정기의 가장 나쁜 실패다."""
    for path in ("/api/token/pair", "/api/v1/user/login", "/api/login"):
        body = json.dumps({"username": user, "password": password}).encode()
        req = urllib.request.Request(api + path, data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (404, 405):
                continue
            print(f"[ALIVE] 로그인 {path} → HTTP {e.code}")
            continue
        except Exception as exc:                       # noqa: BLE001
            print(f"[ALIVE] 로그인 {path} → {type(exc).__name__} {exc}")
            continue
        for key in ("access", "access_token", "token"):
            tok = data.get(key) if isinstance(data, dict) else None
            if isinstance(tok, dict):
                tok = tok.get("access") or tok.get("token")
            if tok:
                print(f"[ALIVE] 로그인 성공: {path}")
                return tok
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            tok = data["data"].get("access") or data["data"].get("token")
            if tok:
                print(f"[ALIVE] 로그인 성공: {path}")
                return tok
    return None


def hit(api: str, method: str, path: str, token: str | None) -> int:
    req = urllib.request.Request(api + path, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as exc:                           # noqa: BLE001
        print(f"[ALIVE] {path} — 응답을 못 받았다: {type(exc).__name__} {exc}")
        return 0


def self_test() -> int:
    """판정 규칙과 자기표본을 함께 본다 (D-277 · D-310)."""
    bad = []
    for status, expect in ((200, True), (204, True), (401, True), (403, True),
                           (500, False), (502, False), (404, False), (0, False)):
        ok, _ = judge(status)
        if ok != expect:
            bad.append(f"judge({status}) = {ok} (기대 {expect})")
    # ★ 출생 표본 — 그날의 세 값(GET · /api/dsm/events · 500)을 그대로 판정한다
    _m, _p, _s = BIRTH_SAMPLE
    if judge(_s)[0]:
        bad.append(f"출생 표본 {_m} {_p} {_s} 를 「살아 있다」로 읽는다 — "
                   f"이 도구가 태어난 바로 그 사례를 놓친다 (D-310)")
    src = _routes_file()
    if not src.is_file():
        bad.append(f"라우트 목록이 없다: {src} — 무엇을 때릴지 모르는 채로 통과할 수 없다")
    else:
        pairs, _ = load_routes(src)
        #: 질의문자열은 그대로 두고 때리므로(위 사유) 자기표본은 **경로로** 맞춘다
        if not any(p.split("?", 1)[0] == SELF_SAMPLE for _, p in pairs):
            bad.append(f"자기표본 {SELF_SAMPLE} 이 목록에 없다 — 500 을 내던 그 자리다 (D-310)")
    if bad:
        print("[ALIVE] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print(f"    {b}")
        return EXIT_FAIL
    print(f"[ALIVE] 자기시험 통과 — 판정 규칙 8종 + 출생 표본 {BIRTH_SAMPLE[1]} 500 "
          f"+ 자기표본 {SELF_SAMPLE}")
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="화면이 쓰는 라우트가 살아 있나 (D-386)")
    ap.add_argument("--api", default=os.environ.get("GX_API", "http://localhost:8000"))
    ap.add_argument("--user", default=os.environ.get("GX_ROUTE_USER"))
    ap.add_argument("--password", default=os.environ.get("GX_ROUTE_PASSWORD"))
    ap.add_argument("--json", metavar="PATH")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    src = _routes_file()
    pairs, skipped = load_routes(src)
    print(f"[ALIVE] [입력] {len(pairs)}건 — 화면이 실제로 부른 GET 라우트 "
          f"(값이 든 경로 {len(skipped)}건은 씨앗이 지워져 때리지 않는다)")

    try:
        urllib.request.urlopen(args.api + "/api/docs", timeout=10)
    except urllib.error.HTTPError:
        pass
    except Exception as exc:                           # noqa: BLE001
        print(f"[ALIVE] API 에 닿지 못했다 ({args.api}): {type(exc).__name__} {exc}")
        print("[ALIVE] **판정 불가** — 때려 보지 못한 것을 초록으로 적지 않는다 (D-301)")
        return EXIT_UNDECIDABLE
    if not (args.user and args.password):
        print("[ALIVE] 자격증명이 없다 (--user/--password 또는 GX_ROUTE_USER/PASSWORD)")
        print("[ALIVE] **판정 불가** — 익명으로 때려 401 만 보고 통과로 적지 않는다 (D-301)")
        return EXIT_UNDECIDABLE
    token = login(args.api, args.user, args.password)
    if not token:
        print("[ALIVE] 토큰을 못 받았다 — **판정 불가**")
        return EXIT_UNDECIDABLE

    dead, rows = [], []
    for method, path in pairs:
        status = hit(args.api, method, path, token)
        ok, why = judge(status)
        rows.append({"method": method, "path": path, "status": status, "alive": ok})
        mark = "  " if ok else "✗ "
        print(f"[ALIVE] {mark}{status:3} {method:4} {path:52} {why}")
        if not ok:
            dead.append((method, path, status))

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"api": args.api, "checked": len(pairs),
                                   "skipped_with_id": skipped, "rows": rows,
                                   "dead": len(dead)}, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        print(f"[ALIVE] 증거 기록: {out}")

    if dead:
        print(f"[ALIVE] **죽은 라우트 {len(dead)}건** — 화면이 부르는데 응답이 없다:")
        for m, p, s in dead:
            print(f"          {s} {m} {p}")
        return EXIT_FAIL
    print(f"[ALIVE] 통과 — {len(pairs)}건 전부 살아 있다 (실제 HTTP 로 때렸다)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
