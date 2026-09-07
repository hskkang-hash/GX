# -*- coding: utf-8 -*-
"""차선 C ① — /device 권한 거절 실측. 같은 서버(8000)에 **번들 둘**을 나란히 건다."""
import json
import os
import sys

from playwright.sync_api import sync_playwright

WEB = sys.argv[1]
USER = os.environ["GX_U"]
PW = os.environ["GX_P"]
LABEL = sys.argv[2]
ROUTE = sys.argv[3] if len(sys.argv) > 3 else "/device"

out = {"web": WEB, "label": LABEL, "route": ROUTE}
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    page = b.new_page(viewport={"width": 1440, "height": 900})
    console = []
    page.on("console", lambda m: console.append({"type": m.type, "text": m.text[:300]}))
    page.on("pageerror", lambda e: console.append({"type": "pageerror", "text": str(e)[:300]}))
    calls = []
    page.on("response", lambda r: calls.append((r.request.method, r.url, r.status)))
    reqs = []
    page.on("request", lambda r: reqs.append((r.method, r.url)))

    page.goto(WEB + "/login", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1500)
    fields = page.locator("input")
    out["login_inputs"] = fields.count()
    fields.nth(0).fill(USER)
    fields.nth(1).fill(PW)
    page.get_by_role("button", name="Log In").click()
    page.wait_for_timeout(4000)
    # ★ 동시 접속 1개 — 다른 자리에 세션이 남아 있으면 여기서 「End Session」이 뜬다.
    #   조율자가 「폼 선택자 추정 실패」로 본 벽은 실은 **이 확인 대화상자**였다:
    #   폼은 맞았고, 로그인이 한 걸음 더 필요했다.
    out["end_session_dialog"] = "End Session" in page.inner_text("body")
    if out["end_session_dialog"]:
        # 대화상자의 단추 이름은 「End Session」이 아니라 **「Confirm」**이다
        # (머리줄이 End Session · 단추는 Confirm/Cancel · bootstrap modal).
        page.get_by_role("button", name="Confirm").click()
        page.wait_for_timeout(9000)
    else:
        page.wait_for_timeout(5000)
    out["url_after_login"] = page.url
    if page.url.rstrip("/").endswith("/login"):
        out["error"] = "로그인 뒤에도 /login — 본문: " + page.inner_text("body")[:200]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        b.close()
        sys.exit(3)

    calls.clear()
    console.clear()
    reqs.clear()
    page.goto(WEB + ROUTE, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(20000)
    out["url"] = page.url
    body = page.inner_text("body")
    out["body_len"] = len(body)
    out["body_head"] = body[:600]
    out["notice_present"] = page.locator('[data-testid="gx-permission-denied"]').count()
    out["copy_present"] = ("볼 권한이 없습니다" in body) or ("권한" in body and "없" in body)
    out["copy_exact"] = "볼 권한이 없습니다" in body

    # 스피너 — 넓게 훑는다. 있으면 있다고, 없으면 없다고 적는다.
    spin = page.evaluate("""() => {
      // ⚠ `[class*=loading]` 는 **레이아웃 칸**(`content-container loading-container`)까지
      //   잡는다 — 그 칸은 늘 있다. 그것을 스피너로 세면 「언제나 스피너가 남아 있다」는
      //   거짓이 나온다. 실제 스피너는 bootstrap 의 `spinner-border`(role=status)다.
      const sel = '[role=progressbar], [role=status], .spinner-border, .MuiCircularProgress-root, [class*=spinner i], [class*=loader i]';
      const found = [];
      document.querySelectorAll(sel).forEach(el => {
        const cs = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        if (cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0 && r.height > 0)
          found.push((el.tagName + '.' + (el.className.baseVal || el.className || '')).slice(0,120));
      });
      return found;
    }""")
    out["spinner_visible"] = spin
    out["req_all"] = sorted({u.split("localhost:8000")[-1] for m, u in reqs if "/api/" in u})
    out["api_all"] = [[m, u.split("localhost:8000")[-1], s] for m, u, s in calls if "/api/" in u]
    out["api_403"] = [[m, u, s] for m, u, s in calls if s == 403 and "/api/" in u]
    out["api_devices"] = [[m, u.split("localhost:8000")[-1], s] for m, u, s in calls if "devices-management" in u]
    out["console_errors"] = [c for c in console if c["type"] in ("error", "pageerror")]
    out["console_all_n"] = len(console)
    page.screenshot(path="/tmp/device_%s.png" % LABEL, full_page=True)
    b.close()

print(json.dumps(out, ensure_ascii=False, indent=2))
