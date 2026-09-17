"""P-160 ④ — the PRODUCT path: host Chrome (390px) logs in, M4 「알림 받기」 subscribes via the app,
「시험 알림 보내기 (훈련)」 sends through test-send → deliveries channel=webpush; the browser's SW shows it.
Evidence: screenshots + JSON with only names/ids/lengths (no secrets)."""
import hashlib, json, os, sys, time
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("GX_PUSH_OUT", HERE)
SPA = "http://localhost:3002"
USER = os.environ["GX_PUSH_USER"]
PW = os.environ["GX_PUSH_PW"]
ev = {"measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "spa": SPA, "user": USER, "calls": []}

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        os.path.join(HERE, "profile_product"), channel="chrome", headless=False,
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    ctx.grant_permissions(["notifications"], origin=SPA)
    page = ctx.new_page()

    def on_resp(r):
        u = r.url
        if "/api/" in u and ("push-subscriptions" in u or "deliveries" in u or "auth/login" in u):
            ev["calls"].append({"method": r.request.method, "url": u.split("localhost:8000")[-1], "status": r.status})
    page.on("response", on_resp)

    page.goto(SPA + "/login", wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2500)
    page.fill("input[name=username]", USER)
    page.fill("input[name=password]", PW)
    page.click("button.login-button")
    # settle_login (verify_click_completes 와 같은 방식): 「Confirm/확인」(앞 세션 끊기) 이 뜨면 누른다
    import re
    end = time.time() + 30
    while time.time() < end and "/login" in page.url:
        try:
            b = page.get_by_role("button", name=re.compile("Confirm|확인"))
            if b.count() and b.first.is_visible():
                b.first.click()
        except Exception:
            pass
        page.wait_for_timeout(1000)
    page.wait_for_timeout(2500)
    ev["after_login_url"] = page.url
    if "/login" in page.url:
        page.screenshot(path=os.path.join(OUT, "login_stuck.png"))
        ev["login"] = "stuck"

    page.goto(SPA + "/m/settings", wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(3500)
    page.screenshot(path=os.path.join(OUT, "m4_before.png"))
    btn = page.get_by_role("button", name="알림 받기")
    ev["subscribe_button_found"] = btn.count() > 0
    if btn.count():
        btn.first.click()
        page.wait_for_timeout(6000)
    page.screenshot(path=os.path.join(OUT, "m4_subscribed.png"))
    sub = page.evaluate("() => Promise.race([navigator.serviceWorker.getRegistration('/field-push-sw.js').then(r => r && r.pushManager.getSubscription()).then(s => s ? s.endpoint : null), new Promise(res => setTimeout(() => res(null), 8000))])")
    ev["browser_subscription"] = {"present": bool(sub), "endpoint_host": (sub.split('/')[2] if sub else None),
                                  "endpoint_sha12": hashlib.sha256(sub.encode()).hexdigest()[:12] if sub else None}

    tbtn = page.get_by_role("button", name="시험 알림 보내기 (훈련)")
    ev["test_button_found"] = tbtn.count() > 0
    if tbtn.count():
        tbtn.first.click()
        page.wait_for_timeout(8000)
    outcome = page.locator("[data-gx=push-test-outcome]")
    ev["push_test_outcome_text"] = outcome.first.inner_text() if outcome.count() else None
    n = page.evaluate("() => Promise.race([navigator.serviceWorker.ready.then(r => r.getNotifications()).then(l => l.map(x => ({title: x.title, body: x.body}))), new Promise(res => setTimeout(() => res('sw-not-ready'), 8000))])")
    ev["notifications_shown"] = n
    page.screenshot(path=os.path.join(OUT, "m4_after_test_send.png"))
    ctx.close()

with open(os.path.join(OUT, "webpush_arrival.json"), "w", encoding="utf-8") as f:
    json.dump(ev, f, ensure_ascii=False, indent=2)
print(json.dumps({k: ev[k] for k in ("after_login_url", "subscribe_button_found", "browser_subscription", "test_button_found",
                                      "push_test_outcome_text", "notifications_shown")}, ensure_ascii=False))
print("calls", [(c["method"], c["url"][:60], c["status"]) for c in ev["calls"]])
