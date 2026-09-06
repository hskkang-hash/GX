# -*- coding: utf-8 -*-
"""P-74 — **브라우저가 실제로 지나간 것만 남긴다** (차선 C · 2026-09-06 턴 G).

무엇을 재는가 — 그리고 **무엇을 재지 않는가**
---------------------------------------------
    잰다   : ① 월 표시 토큰이 있는 브라우저가 `/wall` 을 **연다**
             ② 토큰이 없는 브라우저는 **못 연다** (관문이 그대로 산다)
             ③ 그때 실제로 나간 요청에 머리글자가 실렸고 **로그인 문을 안 불렀다**
             ④ 역할 넷의 사이드바가 각자의 제품 줄을 그린다
             ⑤ U5 시스템 화면에 **미선언 배지**가 뜬다
    안 잰다: 화면을 예쁘게 만들어 찍는 일. 단언이 깨지면 **찍지 않고 그 사실을 적는다.**

★ 「화면이 떴다」로 단언하지 않는다. 각 화면에만 있는 글자를 찾는다 — 로그인 화면으로
  튕긴 뒤에 찍은 PNG 도 **파일은 생긴다.**

★ 월 갈래의 단언은 **글자 하나로는 부족하다.** 월 화면은 로그인 세션으로도 똑같이
  뜨기 때문이다. 그래서 셋을 함께 본다: 화면의 글자 · 나간 요청의 **머리글자** ·
  로그인 문을 **안 불렀다**는 사실. 셋 중 하나라도 빠지면 그 초록은 거짓이다.

    GX_WALL_TOKEN=... GX_SEED_ROLE_PASSWORD=... python capture_p74.py \
        --web http://127.0.0.1:3402 --api http://localhost:8000

⚠ `--api` 는 **번들이 부르는 주소와 글자까지 같아야 한다.** 다르면 접두 대조가 한 건도
  안 맞고, 그 빈 기록이 게이트를 「때릴 것이 없어 통과」로 만든다.
⚠ 토큰은 인자로 받지 않는다(명령줄은 프로세스 목록에 남는다) — 환경변수로만 받는다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

WALL_HEADER = "x-gx-wall-token"
WALL_PATHS = ("/api/dsm/events/queue", "/api/dsm/cameras/pulse")
LOGIN_PATH = "/api/v1/auth/login"

#: 관제실 대형 화면의 크기. 데스크톱(1440×900)으로 찍으면 그것은 월 화면이 아니다.
WALL_VIEWPORT = {"width": 1920, "height": 1080}
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}


def _shots_dir() -> Path:
    for base in (Path("/docs"), Path(__file__).resolve().parents[3] / "docs"):
        if (base / "agent" / "evidence").is_dir():
            return base / "agent" / "evidence"
    raise SystemExit("증거 자리를 못 찾았다")


#: 역할 넷 — 사이드바에 **무엇이 보여야 하는가**. 표는 `common/product_menus.py` 다.
#: 여기 적은 것은 그 표에서 **한 줄씩 고른 대표**이고, 전수는 `verify_sidebar.py` 가 센다.
ROLES = (
    {"key": "U1", "user": "gxseed_u1_operator", "route": "/dsm/queue",
     "must_see": ("지금 처리할 것", "카메라 격자", "인계 메모"),
     "why": "관제요원 — 다섯 줄 전부가 우리 제품이다"},
    {"key": "U2", "user": "gxseed_u2_manager", "route": "/dsm/queue",
     "must_see": ("관제 현황", "훈련 모드", "지금 처리할 것"),
     "why": "관제팀장 — 제품 일곱 줄"},
    {"key": "U4", "user": "gxseed_u4_official", "route": "/dsm/events",
     "must_see": ("무슨 일 있었나", "열람·삭제 청구"),
     "why": "재난안전과 — 제품 두 줄"},
    {"key": "U5", "user": "gxseed_u5_sysop", "route": "/dsm/system",
     "must_see": ("보존·백업 설정", "이번 달 사용량", "카메라 일괄 등록"),
     "why": "관리자 — 제품 네 줄. 이 사람은 이번 턴에 처음 생겼다"},
)


def _clear_session(api: str, user: str, password: str) -> str:
    """이 사람의 **남은 세션을 끊는다.** 브라우저가 로그인하기 전에.

    ★ 왜 필요한가 [실측 2026-09-06]: 이 제품은 동시 접속이 1개이고, 그 자리는
      `user.token` **칸 하나**다. 바로 앞에서 판정기(`verify_sidebar`)가 같은 계정으로
      HTTP 로그인을 했으면 그 칸이 차 있고, 그 상태에서 브라우저가 로그인하면 서버는
      200 안에 이렇게 답한다:

          {"success": false, "message": "You have an active session in another
           location...", "auth_status": {"existing_session": true}}

      화면은 **로그인 화면에 머무르며 확인 창을 띄운다.** 그러면 캡처는 「로그인 뒤에도
      로그인 화면이다」로 기록되고, 그 기록은 **화면의 결함처럼 보인다** — 실제로 없던
      것은 화면이 아니라 빈 세션 칸이다. 그래서 **찍기 전에 비운다.**

    ⚠ 비우고도 확인 창이 뜰 수 있다(다른 차선이 그 사이에 들어오면). 그래서 아래
      브라우저 갈래에 **확인 단추를 누르는 길**을 함께 둔다 — 둘 중 하나가 아니라 둘 다다.
    """
    import urllib.error
    import urllib.request

    def post(path, payload, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(api + path, method="POST",
                                     data=json.dumps(payload).encode("utf-8"),
                                     headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception as e:                              # noqa: BLE001
            return 0, str(e)

    st, body = post("/api/v1/auth/login",
                    {"username": user, "password": password,
                     "end_previous_session": True})
    token = ""
    if isinstance(body, dict):
        token = (body.get("user") or {}).get("access_token") or ""
    if not token:
        return "로그인으로 세션을 못 잡았다 (%s)" % st
    st2, _ = post("/api/v1/auth/logout", {}, token)
    return "세션 비움 (로그인 %s → 로그아웃 %s)" % (st, st2)


def _sign_in(page, web, user, password, wait_ms=9000):
    """로그인 화면에서 사람이 하는 그대로. **확인 창이 뜨면 확인을 누른다.**

    돌려주는 것은 `(들어갔나, 무슨 일이 있었나)`.
    """
    page.goto(web + "/login", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1500)
    fields = page.locator("input")
    if fields.count() < 2:
        return False, "로그인 화면에 입력칸이 둘 미만이다"
    fields.nth(0).fill(user)
    fields.nth(1).fill(password)
    page.get_by_role("button", name="Log In").click()
    page.wait_for_timeout(wait_ms)
    if not page.url.rstrip("/").endswith("/login"):
        return True, "한 번에 들어갔다"

    # 확인 창 — 「이 계정이 다른 기기에서 켜져 있습니다」
    for label in ("Confirm", "확인"):
        btn = page.get_by_role("button", name=label)
        try:
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click()
                page.wait_for_timeout(wait_ms)
                if not page.url.rstrip("/").endswith("/login"):
                    return True, "확인 창을 눌러서 들어갔다 (앞선 세션을 끊었다)"
        except Exception:                                   # noqa: BLE001
            continue
    return False, "로그인 뒤에도 로그인 화면이다 — 본문 " + repr(
        page.inner_text("body")[:180])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="http://127.0.0.1:3402")
    ap.add_argument("--api", default="http://localhost:8000")
    args = ap.parse_args()

    token = os.environ.get("GX_WALL_TOKEN", "").strip()
    password = os.environ.get("GX_SEED_ROLE_PASSWORD", "").strip()
    if not token or not password:
        print("[P-74] 판정 불가 — GX_WALL_TOKEN / GX_SEED_ROLE_PASSWORD 가 없다")
        return EXIT_UNDECIDABLE

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[P-74] 판정 불가 — playwright 가 없다")
        return EXIT_UNDECIDABLE

    ev = _shots_dir()
    wall_dir = ev / "P-74" / "shots"
    side_dir = ev / "UX-25" / "shots"
    for d in (wall_dir, side_dir):
        d.mkdir(parents=True, exist_ok=True)

    report: dict = {"captured_at": datetime.now().isoformat(timespec="seconds"),
                    "web": args.web, "api": args.api, "shots": [], "misses": []}
    fails = 0

    def note(ok, what, detail, path=None):
        nonlocal fails
        mark = "OK  " if ok else "FAIL"
        print("[P-74] %s %s — %s" % (mark, what, detail))
        if ok:
            report["shots"].append({"what": what, "detail": detail,
                                    "file": str(path) if path else None})
        else:
            fails += 1
            report["misses"].append({"what": what, "why": detail})

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])

        # ═══════════════════════════════════════════════════════════════
        # ① 토큰 **없이** — 관문이 그대로 사는가
        #    ★ 이것을 먼저 찍는다. 뒤에 찍으면 앞선 갈래가 저장소에 남긴 토큰이
        #      이쪽으로 새어 「토큰 없이도 열린다」는 거짓 초록이 난다.
        # ═══════════════════════════════════════════════════════════════
        ctx = browser.new_context(viewport=WALL_VIEWPORT)
        page = ctx.new_page()
        page.goto(args.web + "/wall", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)
        body = page.inner_text("body")
        landed = page.url
        bounced = landed.rstrip("/").endswith("/login")
        shot = wall_dir / "wall_without_token.png"
        page.screenshot(path=str(shot))
        note(bounced and "월 모드" not in body,
             "토큰 없이 /wall",
             "도착 %s · 월 화면 글자 %s%s" % (
                 landed,
                 "없다" if "월 모드" not in body else "있다",
                 "" if bounced else " · **관문을 안 지났다**"),
             shot)
        ctx.close()

        # ═══════════════════════════════════════════════════════════════
        # ② 토큰을 **들고** — 열리는가. 그리고 무엇을 부르는가
        # ═══════════════════════════════════════════════════════════════
        ctx = browser.new_context(viewport=WALL_VIEWPORT)
        page = ctx.new_page()
        seen = []
        page.on("response", lambda r: seen.append(
            (r.request.method, r.url, r.status,
             WALL_HEADER in set(k.lower() for k in r.request.headers),
             "authorization" in set(k.lower() for k in r.request.headers))))
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))

        page.goto(args.web + "/wall?token=" + token, wait_until="networkidle",
                  timeout=60000)
        page.wait_for_timeout(8000)
        body = page.inner_text("body")
        landed = page.url

        ours = [(m, u[len(args.api):], st, h, a) for m, u, st, h, a in seen
                if u.startswith(args.api + "/api/")]
        wall_calls = [c for c in ours
                      if any(c[1].split("?")[0] == w for w in WALL_PATHS)]
        with_header = [c for c in wall_calls if c[3]]
        got_200 = [c for c in with_header if c[2] == 200]
        login_calls = [c for c in ours if LOGIN_PATH in c[1]]
        both_creds = [c for c in wall_calls if c[3] and c[4]]

        shot = wall_dir / "wall_with_token.png"
        opened = "월 모드" in body and "월 표시 토큰으로 열림" in body
        if opened:
            page.screenshot(path=str(shot))
        report["wall_calls"] = [{"method": m, "path": u, "status": st,
                                 "wall_header": h, "authorization": a}
                                for m, u, st, h, a in ours]
        note(opened, "토큰으로 /wall — 화면",
             "도착 %s · 「월 표시 토큰으로 열림」 %s%s" % (
                 landed,
                 "있다" if "월 표시 토큰으로 열림" in body else "없다",
                 "" if opened else " · 본문 " + repr(body[:160])),
             shot if opened else None)
        note(bool(got_200), "토큰으로 /wall — 요청",
             ("머리글자를 실은 문 %d건 · 200 %d건 (%s)" % (
                 len(with_header), len(got_200),
                 [c[1].split("?")[0] for c in got_200]))
             if got_200 else
             ("머리글자를 실은 200 이 **0건**이다. 우리 API 기록 %d건: %s" % (
                 len(ours), [(c[1].split("?")[0], c[2], c[3]) for c in ours][:6])))
        note(not login_calls, "토큰으로 /wall — 세션",
             "로그인 문을 **한 번도 안 불렀다** (세션을 안 세운다)"
             if not login_calls else
             "로그인 문을 %d번 불렀다 — 세션을 세우고 있다" % len(login_calls))
        note(not both_creds, "토큰으로 /wall — 자격증명 하나",
             "머리글자와 로그인 자리를 함께 실은 요청 0건"
             if not both_creds else
             "둘을 함께 실은 요청 %d건 — 서버가 거절할 모양이다" % len(both_creds))
        if errors:
            print("[P-74] [실측] 화면 오류 %d건: %s" % (len(errors), errors[:2]))
        report["wall_page_errors"] = errors
        ctx.close()

        # ═══════════════════════════════════════════════════════════════
        # ③ 역할 넷의 사이드바 · ④ U5 미선언 배지
        #    ★ 역할마다 **새 컨텍스트**다. 한 컨텍스트로 갈아타면 앞사람의 저장소가
        #      남아 다음 사람의 화면이 앞사람 것으로 뜬다.
        # ═══════════════════════════════════════════════════════════════
        for role in ROLES:
            ctx = browser.new_context(viewport=DESKTOP_VIEWPORT)
            page = ctx.new_page()
            calls = []
            page.on("response", lambda r, c=calls: c.append(
                (r.request.method, r.url, r.status)))
            try:
                cleared = _clear_session(args.api, role["user"], password)
                print("[P-74] [준비] %s %s — %s" % (role["key"], role["user"], cleared))
                entered, how = _sign_in(page, args.web, role["user"], password)
                if not entered:
                    note(False, role["key"] + " 사이드바", how)
                    continue
                print("[P-74] [준비] %s 로그인 — %s" % (role["key"], how))

                page.goto(args.web + role["route"], wait_until="networkidle",
                          timeout=60000)
                page.wait_for_timeout(6000)
                body = page.inner_text("body")
                missing = [w for w in role["must_see"] if w not in body]
                shot = side_dir / ("sidebar_%s_%s.png" % (role["key"], role["user"]))
                if not missing:
                    page.screenshot(path=str(shot))
                note(not missing, role["key"] + " 사이드바",
                     ("%s · 기다린 줄 %d개 전부 있다"
                      % (role["route"], len(role["must_see"])))
                     if not missing else
                     ("사이드바에 없는 줄: %s — 본문 %s"
                      % (missing, repr(body[:160]))),
                     shot if not missing else None)

                # ④ U5 만: 미선언 배지
                if role["key"] == "U5":
                    ours = [(m, u[len(args.api):], st) for m, u, st in calls
                            if u.startswith(args.api + "/api/")]
                    retention_called = [c for c in ours
                                        if "/api/dsm/law/retention" in c[1]]
                    badge = "미선언" in body
                    signal = "서버 신호 대기" in body
                    shot5 = wall_dir / "u5_system_undeclared.png"
                    page.screenshot(path=str(shot5))
                    note(badge or signal, "U5 시스템 — 미선언 배지",
                         "「미선언」 %s · 「서버 신호 대기」 %s · 보존 선언 문을 %d번 "
                         "불렀다 %s" % (
                             "있다" if badge else "없다",
                             "있다" if signal else "없다",
                             len(retention_called), retention_called[:2]),
                         shot5)
                    report["u5_calls"] = [{"method": m, "path": u, "status": st}
                                          for m, u, st in ours]
                    report["u5_declared_here"] = not badge

                    # ── ⑥ 빨강 배지 자체를 **찍는다** — 응답을 주입해서 ──────
                    #
                    #  왜 주입하나: 이 환경은 **선언된 환경**이다(개발·스테이징 선언 ·
                    #  P-67). 그래서 화면에 「미선언」이 안 뜬다 — 그것이 옳다.
                    #  그런데 그 상태로는 **빨강 배지가 실제로 그려지는지** 아무도
                    #  못 본다. 「코드에 있다」와 「화면에 뜬다」는 다른 사실이다.
                    #
                    #  ⚠ 이 장은 **주입한 응답으로 그린 화면**이다. 「이 환경이
                    #    미선언이다」의 증거가 **아니다.** 두 사실을 한 장으로 적으면
                    #    그 장이 거짓말이 된다 — 그래서 파일 이름과 기록에 둘 다 적는다.
                    #  ⚠ [실측 2026-09-06] 1차판은 본문만 주입했고 **아무 일도 안
                    #    일어났다.** 이 요청은 다른 출처로 나가고 로그인 자리를 실으므로
                    #    브라우저가 먼저 **예비 요청(OPTIONS)** 을 보낸다. 그 예비
                    #    요청까지 답해 주지 않으면 진짜 요청은 아예 나가지 않는다 —
                    #    바로 위 월 토큰이 걸렸던 것과 **같은 자리**다(허용 머리글자).
                    #    그리고 `*` 로는 안 된다: 자격증명이 실린 요청에는 출처를
                    #    글자 그대로 돌려줘야 한다.
                    _cors = {
                        "Access-Control-Allow-Origin": args.web,
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Allow-Methods": "GET,OPTIONS",
                    }

                    def _undeclared(route, request):
                        if request.method == "OPTIONS":
                            route.fulfill(status=204, headers=_cors)
                            return
                        route.fulfill(
                            status=200,
                            content_type="application/json",
                            headers=_cors,
                            body=json.dumps({
                                "retention_days": None,
                                "declared": False,
                                "source": "미선언",
                                "enforced": False,
                            }, ensure_ascii=False))

                    page.route("**/api/dsm/law/retention*", _undeclared)
                    page.goto(args.web + role["route"],
                              wait_until="networkidle", timeout=60000)
                    page.wait_for_timeout(5000)
                    body2 = page.inner_text("body")
                    report["u5_injected_body"] = body2[:600]
                    shot6 = wall_dir / "u5_system_undeclared_injected.png"
                    page.screenshot(path=str(shot6))
                    page.unroute("**/api/dsm/law/retention*")
                    note("미선언" in body2, "U5 시스템 — 빨강 배지 (응답 주입)",
                         "주입한 미선언 응답으로 「미선언」 %s · "
                         "「보관 기간이 선언되지 않았습니다.」 %s "
                         "— **이 환경이 미선언이라는 뜻이 아니다**" % (
                             "떴다" if "미선언" in body2 else "안 떴다",
                             "떴다" if "보관 기간이 선언되지 않았습니다."
                             in body2 else "안 떴다"),
                         shot6)
            finally:
                ctx.close()

        browser.close()

    out = ev / "P-74" / "capture_p74_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[P-74] 기록 → %s" % out)
    print("[P-74] 찍은 것 %d장 · 못 찍은 것 %d건"
          % (len(report["shots"]), len(report["misses"])))
    return EXIT_OK if fails == 0 else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
