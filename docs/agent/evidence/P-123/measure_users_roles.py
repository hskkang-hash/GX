# -*- coding: utf-8 -*-
"""A/B — `/users` 를 **주소로** 여는 것과 **사이드바를 눌러** 여는 것이 다른가."""
import os, re
from playwright.sync_api import sync_playwright
WEB="http://localhost:3002"; PW=os.environ["GX_SEED_ROLE_PASSWORD"]; USER="gxseed_u5_sysop"
def snap(page, tag):
    body=page.inner_text("body")
    print("  [%s] url=%s bytes=%d rows=%d th=%d table=%d" % (
        tag, page.url.replace(WEB,""), len(body),
        page.locator("table tbody tr").count(),
        page.locator("table th").count(),
        page.locator("table").count()))
    print("       text=%r" % re.sub(r'\s+',' ',body)[:200])
with sync_playwright() as pw:
    b=pw.chromium.launch(args=["--no-sandbox"]); ctx=b.new_context(viewport={"width":1600,"height":1200}); page=ctx.new_page()
    calls=[]
    page.on("response", lambda r: calls.append((r.status, r.url)) if "/api/v1/user/list" in r.url or "/api/roles/" in r.url else None)
    page.goto(WEB+"/login", wait_until="networkidle", timeout=60000)
    page.wait_for_selector("input", state="visible", timeout=30000); page.wait_for_timeout(1500)
    f=page.locator("input"); f.nth(0).fill(USER); f.nth(1).fill(PW)
    page.get_by_role("button", name="Log In").click(); page.wait_for_timeout(9000)
    btn=page.get_by_role("button", name="Confirm")
    if btn.count() and btn.first.is_visible(): btn.first.click(); page.wait_for_timeout(9000)
    print("[A] 주소로 연다")
    calls.clear(); page.goto(WEB+"/users", wait_until="domcontentloaded", timeout=60000); page.wait_for_timeout(7000)
    snap(page,"A"); print("      목록 호출:", calls)
    print("[B] 사이드바 「사람」을 누른다")
    calls.clear()
    page.goto(WEB+"/dsm/queue", wait_until="domcontentloaded", timeout=60000); page.wait_for_timeout(4000)
    item = page.locator("nav.sidebar-nav .menu-item").filter(has_text="사람")
    print("      누를 줄:", item.count())
    item.first.click(); page.wait_for_timeout(8000)
    snap(page,"B"); print("      목록 호출:", calls)
    ctx.close(); b.close()
