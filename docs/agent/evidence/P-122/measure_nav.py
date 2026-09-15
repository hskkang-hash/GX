# -*- coding: utf-8 -*-
"""P-122 · 사이드바 메뉴 줄을 **브라우저에서** 센다. 실제 로그인 · 실제 번들.

마디(자식 있는 줄)는 `span.menu-text` 뒤에 **꺾쇠 svg** 가 하나 더 붙는다 —
그것만 눌러서 편다. 잎을 누르면 화면이 옮겨 가므로 누르지 않는다.
"""
import json, os, re, sys
from playwright.sync_api import sync_playwright

WEB = os.environ.get("GX_WEB", "http://localhost:3002")
PW = os.environ["GX_SEED_ROLE_PASSWORD"]
PERSONAS = [("U1", "gxseed_u1_operator"), ("U2", "gxseed_u2_manager"),
            ("U4", "gxseed_u4_official"), ("U5", "gxseed_u5_sysop")]
HAN = re.compile(u'[\uac00-\ud7a3]')
LAT = re.compile(r'[A-Za-z]')
TAG = sys.argv[1] if len(sys.argv) > 1 else "before"
ONLY = [x for x in sys.argv[2:]] or None

SCAN = r"""() => {
  const nav = document.querySelector('nav.sidebar-nav');
  if (!nav) return {found:false, rows:[]};
  const rows = [];
  nav.querySelectorAll('.menu-item').forEach(el => {
    const t = el.querySelector('.menu-text');
    if (!t) return;
    rows.push({text:(t.textContent||'').trim(),
               expandable: el.querySelectorAll(':scope > svg').length > 0});
  });
  return {found:true, rows};
}"""

EXPAND = r"""() => {
  const nav = document.querySelector('nav.sidebar-nav');
  if (!nav) return 0;
  let n = 0;
  nav.querySelectorAll('.menu-item').forEach(el => {
    if (el.querySelectorAll(':scope > svg').length > 0 && !el.dataset.gxOpened) {
      el.dataset.gxOpened = '1'; el.click(); n++;
    }
  });
  return n;
}"""


def one(pw, bucket, user):
    b = pw.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 1600, "height": 1200})
    page = ctx.new_page()
    res = {"bucket": bucket, "user": user}
    try:
        page.goto(WEB + "/login", wait_until="networkidle", timeout=60000)
        page.wait_for_selector("input", state="visible", timeout=30000)
        page.wait_for_timeout(1500)
        f = page.locator("input")
        f.nth(0).fill(user); f.nth(1).fill(PW)
        page.get_by_role("button", name="Log In").click()
        page.wait_for_timeout(9000)
        try:
            btn = page.get_by_role("button", name="Confirm")
            if btn.count() and btn.first.is_visible():
                btn.first.click(); page.wait_for_timeout(9000)
                res["end_session_dialog"] = True
        except Exception:
            pass
        res["url_after_login"] = page.url
        if page.url.rstrip("/").endswith("/login"):
            res["error"] = "로그인 뒤에도 /login — %r" % page.inner_text("body")[:200]
            return res
        page.wait_for_selector("nav.sidebar-nav", timeout=30000)
        page.wait_for_timeout(2500)
        res["top_level"] = len([r for r in page.evaluate(SCAN)["rows"]])
        for _ in range(6):
            n = page.evaluate(EXPAND)
            page.wait_for_timeout(900)
            if not n:
                break
        d = page.evaluate(SCAN)
        rows = [r for r in d["rows"] if r["text"]]
        res["rows"] = rows
        res["total"] = len(rows)
        res["ko"] = sum(1 for r in rows if HAN.search(r["text"]))
        res["en"] = sum(1 for r in rows if not HAN.search(r["text"]) and LAT.search(r["text"]))
        res["en_labels"] = [r["text"] for r in rows
                            if not HAN.search(r["text"]) and LAT.search(r["text"])]
        res["bundle"] = page.evaluate(
            "() => Array.from(document.querySelectorAll('script[src]')).map(s=>s.getAttribute('src')).join(',')")
    except Exception as exc:
        res["error"] = "%s %s" % (type(exc).__name__, exc)
    finally:
        try:
            ctx.close(); b.close()
        except Exception:
            pass
    return res


out = []
with sync_playwright() as pw:
    for bucket, user in PERSONAS:
        if ONLY and bucket not in ONLY:
            continue
        r = one(pw, bucket, user)
        out.append(r)
        print("[NAV] %s %-22s top=%s total=%s ko=%s en=%s %s" % (
            bucket, user, r.get("top_level"), r.get("total"), r.get("ko"), r.get("en"),
            r.get("error", "")), flush=True)
        if r.get("en_labels"):
            print("      영문: %s" % ", ".join(r["en_labels"]), flush=True)
path = "/tmp/gx_nav_%s.json" % TAG
with open(path, "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print("[NAV] ->", path)
