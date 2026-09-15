# -*- coding: utf-8 -*-
"""P-121 / UX-26 — **사진이 실제로 그려졌는가**를 브라우저에서 잰다 (차선 C1 · 턴 O).

무엇을 재는가
-------------
    ① 나간 XHR 의 상태와 **바이트 수** (`*/snapshot`)
    ② 그 뒤 화면에 `<img>` 가 서 있고 `naturalWidth > 0` 인가
       — 「img 태그가 있다」로 단언하지 않는다. src 가 깨져도 태그는 남는다.
    ③ 화면에 뜬 문장 — 「사진을 불러오지 못했습니다」가 **4xx/5xx 가 아닐 때**
       떠 있으면 그것은 거짓말이다
    ④ 「다시 시도」를 누르면 **요청이 실제로 나가는가** (누르기 전/후 요청 수)
    ⑤ 모바일의 「관제 화면에서 확인하십시오」가 아직 있는가

    GX_SEED_ROLE_PASSWORD=... python capture_p121.py --tag before
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

DESKTOP = {"width": 1440, "height": 900}
MOBILE = {"width": 390, "height": 844}
FALSE_INSTRUCTION = "관제 화면에서 확인하십시오"
FAIL_LINE = "사진을 불러오지 못했습니다"
NONE_LINE = "저장된 스냅샷 경로가 없습니다"


def sign_in(page, web, user, password):
    page.goto(web + "/login", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1500)
    fields = page.locator("input")
    if fields.count() < 2:
        return False, "로그인 화면에 입력칸이 둘 미만이다"
    fields.nth(0).fill(user)
    fields.nth(1).fill(password)
    page.get_by_role("button", name="Log In").click()
    page.wait_for_timeout(9000)
    if not page.url.rstrip("/").endswith("/login"):
        return True, "한 번에 들어갔다"
    for label in ("Confirm", "확인", "End Session", "OK"):
        btn = page.get_by_role("button", name=label)
        try:
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click()
                page.wait_for_timeout(9000)
                if not page.url.rstrip("/").endswith("/login"):
                    return True, "확인 창을 눌러 들어갔다 (%s)" % label
        except Exception:                                   # noqa: BLE001
            continue
    return False, "로그인 뒤에도 로그인 화면이다 — " + repr(page.inner_text("body")[:180])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="http://localhost:3002")
    ap.add_argument("--tag", required=True)            # before | after
    ap.add_argument("--user", default="gxseed_u2_manager")
    ap.add_argument("--event", default="4798")         # 스냅샷이 **있는** 사건
    ap.add_argument("--event-nosnap", default="4818")  # 스냅샷 경로가 **없는** 사건
    args = ap.parse_args()

    pw_ = os.environ.get("GX_SEED_ROLE_PASSWORD", "").strip()
    if not pw_:
        print("[P-121] 판정 불가 — GX_SEED_ROLE_PASSWORD 가 없다")
        return 2
    from playwright.sync_api import sync_playwright

    out = Path("/docs/agent/evidence/P-121")
    (out / "shots").mkdir(parents=True, exist_ok=True)
    rep = {"tag": args.tag, "at": datetime.now().isoformat(timespec="seconds"),
           "web": args.web, "screens": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        ctx = browser.new_context(viewport=DESKTOP)
        page = ctx.new_page()

        calls: list = []
        console: list = []

        def on_resp(r):
            if "/snapshot" in r.url:
                try:
                    n = len(r.body())
                except Exception:                           # noqa: BLE001
                    n = -1
                calls.append({"url": r.url.split("/api")[-1], "status": r.status,
                              "bytes": n})

        page.on("response", on_resp)
        #: ⚠ 콘솔은 카카오맵·웹소켓 잡음으로 가득 찬다. **찾는 말만** 남긴다 —
        #:   상한에 걸려 정작 그 줄이 밀려나면 그 침묵이 「없다」로 읽힌다.
        WANT = ("createObjectURL", "TypeError", "Failed to execute")
        page.on("console", lambda m: console.append(m.type + ": " + m.text[:240])
                if any(w in m.text for w in WANT) else None)
        page.on("pageerror", lambda e: console.append("pageerror: " + str(e)[:240]))

        ok, why = sign_in(page, args.web, args.user, pw_)
        print("[P-121] 로그인 — %s (%s)" % (ok, why))
        if not ok:
            print(json.dumps(rep, ensure_ascii=False))
            return 2

        def look(name, url, viewport=None, force=None, click_retry=False):
            nonlocal calls, console
            pg = page
            c = None
            if viewport:
                c = browser.new_context(viewport=viewport,
                                        storage_state=ctx.storage_state())
                pg = c.new_page()
                pg.on("response", on_resp)
                pg.on("pageerror", lambda e: console.append("pageerror: " + str(e)[:240]))
                pg.on("console", lambda m: console.append(m.type + ": " + m.text[:240])
                      if any(w in m.text for w in
                             ("createObjectURL", "TypeError", "Failed to execute")) else None)
            calls = []
            console = []
            if force:
                pg.route("**/api/dsm/events/*/snapshot*",
                         lambda route: route.fulfill(
                             status=force, content_type="application/json",
                             body='{"detail": "\uac15\uc81c \uc2e4\ud328"}'))
            pg.goto(args.web + url, wait_until="networkidle", timeout=60000)
            pg.wait_for_timeout(6000)
            body = pg.inner_text("body")
            imgs = pg.evaluate(
                "() => Array.from(document.images)"
                ".filter(i => (i.currentSrc||i.src||'').startsWith('blob:'))"
                ".map(i => ({w: i.naturalWidth, h: i.naturalHeight}))")
            row = {
                "screen": name, "url": url,
                "viewport": viewport or DESKTOP,
                "snapshot_calls": list(calls),
                "blob_imgs": imgs,
                "drawn": any(i["w"] > 0 for i in imgs),
                "shows_fail_line": FAIL_LINE in body,
                "shows_none_line": NONE_LINE in body,
                "shows_false_instruction": FALSE_INSTRUCTION in body,
                "console": list(console)[:6],
            }
            if click_retry:
                before_n = len(calls)
                clicked = False
                for sel in ("다시 시도",):
                    loc = pg.get_by_text(sel, exact=True)
                    try:
                        if loc.count() > 0 and loc.first.is_visible():
                            loc.first.click()
                            clicked = True
                            break
                    except Exception:                       # noqa: BLE001
                        pass
                pg.wait_for_timeout(4000)
                row["retry"] = {"found": clicked,
                                "calls_before": before_n,
                                "calls_after": len(calls),
                                "issued": len(calls) > before_n}
            shot = out / "shots" / ("%s_%s.png" % (args.tag, name))
            pg.screenshot(path=str(shot), full_page=False)
            row["shot"] = shot.name
            rep["screens"].append(row)
            print("[P-121] %-22s calls=%s drawn=%s fail_line=%s false_instr=%s %s"
                  % (name, row["snapshot_calls"], row["drawn"],
                     row["shows_fail_line"], row["shows_false_instruction"],
                     row.get("retry", "")))
            if c:
                c.close()

        look("desktop_detail", "/dsm/events/%s" % args.event, click_retry=True)
        look("desktop_queue", "/dsm/queue")
        look("mobile_detail", "/m/events/%s" % args.event, viewport=MOBILE,
             click_retry=True)
        look("desktop_nosnap", "/dsm/events/%s" % args.event_nosnap)
        look("desktop_forced500", "/dsm/events/%s" % args.event,
             force=500, click_retry=True)

        browser.close()

    f = out / ("p121_%s.json" % args.tag)
    f.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[P-121] 기록 → %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
