# -*- coding: utf-8 -*-
"""P-123 ① — 발송 기록의 실제 모양 + 휴대전화 화면이 그것을 뭐라고 적는가."""
import json, os, re, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
BASE="http://gx-nginx-e:8500"; WEB="http://localhost:3002"
USER=os.environ.get("U","gxseed_u1_operator"); PW=os.environ["GX_SEED_ROLE_PASSWORD"]
def req(m,p,tok=None,body=None):
    d=json.dumps(body).encode() if body is not None else None
    r=urllib.request.Request(BASE+p,data=d,method=m,
      headers={"Content-Type":"application/json",**({"Authorization":"Bearer "+tok} if tok else {})})
    try:
        x=urllib.request.urlopen(r,timeout=30); return x.status, x.read().decode()
    except urllib.error.HTTPError as e: return e.code, e.read().decode()
st,b=req("POST","/api/v1/auth/login",body={"username":USER,"password":PW,"end_previous_session":True})
tok=json.loads(b).get("user",{}).get("access_token")
st,b=req("GET","/api/dsm/deliveries?limit=200",tok)
j=json.loads(b); rows=(j.get("data") or j).get("deliveries") if isinstance(j.get("data"),dict) else j.get("deliveries")
rows = rows or (j.get("data") if isinstance(j.get("data"),list) else [])
print("GET /api/dsm/deliveries ->", st, "rows:", len(rows))
from collections import Counter
print("  channel:", Counter(r.get("channel") for r in rows))
print("  succeeded:", Counter(r.get("succeeded") for r in rows))
print("  recipient 빈칸:", sum(1 for r in rows if not str(r.get("recipient") or "").strip()), "/", len(rows))
print("  recipient_id null:", sum(1 for r in rows if r.get("recipient_id") is None))
print("  sample:", json.dumps(rows[0], ensure_ascii=False) if rows else "-")
# 메일함
try:
    x=urllib.request.urlopen("http://mailpit:8025/api/v1/messages?limit=1", timeout=10)
    print("mailpit:", json.loads(x.read().decode()).get("messages_count"))
except Exception as e:
    print("mailpit: 못 읽었다", type(e).__name__, e)
# 휴대전화 화면
with sync_playwright() as pw:
    b2=pw.chromium.launch(args=["--no-sandbox"]); ctx=b2.new_context(viewport={"width":390,"height":844}); page=ctx.new_page()
    page.goto(WEB+"/login", wait_until="networkidle", timeout=60000)
    page.wait_for_selector("input", state="visible", timeout=30000); page.wait_for_timeout(1500)
    f=page.locator("input"); f.nth(0).fill(USER); f.nth(1).fill(PW)
    try: page.get_by_role("button", name="Log In").click()
    except Exception: page.locator("button").last.click()
    page.wait_for_timeout(9000)
    btn=page.get_by_role("button", name="Confirm")
    if btn.count() and btn.first.is_visible(): btn.first.click(); page.wait_for_timeout(9000)
    page.goto(WEB+"/m/inbox", wait_until="domcontentloaded", timeout=60000); page.wait_for_timeout(7000)
    t=re.sub(r'\s+',' ',page.inner_text("body"))
    print("MobileInbox bytes=%d" % len(t))
    print("  「로그에 기록됨(사람에게 안 감)」:", t.count("로그에 기록됨(사람에게 안 감)"))
    print("  「· 발송 」(옛 문구):", len(re.findall(r'· 발송 \d', t)))
    print("  text:", t[:420])
    ctx.close(); b2.close()
