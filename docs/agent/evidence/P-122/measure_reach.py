# -*- coding: utf-8 -*-
"""P-122 닫는 조건 ② — **가린 뒤에도 각 역할이 자기 화면에 닿는가.**
   그리고 P-123 ②③ — /handover 빈 상태 · 없는 사건의 404 문구."""
import json, os, re, sys
from playwright.sync_api import sync_playwright

WEB = "http://localhost:3002"
PW = os.environ["GX_SEED_ROLE_PASSWORD"]
ALLOW = {
    "U1": ["/dsm/queue", "/dsm/events", "/dsm/cameras/grid", "/handover", "/start"],
    "U2": ["/dsm/queue", "/dsm/events", "/dsm/cameras/grid", "/handover", "/start",
           "/dsm/dashboard", "/dsm/drill"],
    "U4": ["/dsm/events", "/dsm/privacy-requests"],
    "U5": ["/dsm/queue", "/dsm/events", "/dsm/cameras/grid", "/handover", "/start",
           "/users", "/dsm/cameras/import", "/dsm/system", "/dsm/metering"],
}
USERS = {"U1": "gxseed_u1_operator", "U2": "gxseed_u2_manager",
         "U4": "gxseed_u4_official", "U5": "gxseed_u5_sysop"}
DENIED = ['권한이 없습니다', '역할이 아직 없습니다', '로그인']
ONLY = sys.argv[1:] or list(ALLOW)

out = []
with sync_playwright() as pw:
    for bucket in ONLY:
        user = USERS[bucket]
        b = pw.chromium.launch(args=["--no-sandbox"])
        ctx = b.new_context(viewport={"width": 1600, "height": 1200})
        page = ctx.new_page()
        calls = []
        page.on("response", lambda r: calls.append((r.url, r.status))
                if "/api/" in r.url else None)
        rec = {"bucket": bucket, "user": user, "paths": []}
        try:
            page.goto(WEB + "/login", wait_until="networkidle", timeout=60000)
            page.wait_for_selector("input", state="visible", timeout=30000)
            page.wait_for_timeout(1500)
            f = page.locator("input"); f.nth(0).fill(user); f.nth(1).fill(PW)
            page.get_by_role("button", name="Log In").click(); page.wait_for_timeout(9000)
            btn = page.get_by_role("button", name="Confirm")
            if btn.count() and btn.first.is_visible():
                btn.first.click(); page.wait_for_timeout(9000)
            if page.url.rstrip("/").endswith("/login"):
                rec["error"] = "로그인 실패"; out.append(rec); ctx.close(); b.close(); continue

            for p in ALLOW[bucket]:
                calls.clear()
                page.goto(WEB + p, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)
                body = page.inner_text("body")
                main = re.sub(r'\s+', ' ', body).strip()
                api = [(u.split("/api/")[-1][:48], s) for u, s in calls]
                bad = [x for x in api if x[1] >= 400]
                rec["paths"].append({
                    "path": p, "url": page.url, "bytes": len(body),
                    "api_calls": len(api), "api_bad": bad[:5],
                    "denied": [d for d in DENIED if d in body],
                    "head": main[:110],
                })
            # ── P-123 ② /handover 빈 상태 ──────────────────────────────
            page.goto(WEB + "/handover", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            hb = page.inner_text("body")
            rec["handover"] = {
                "bytes": len(hb),
                "빈상태": "아직 인계 메모가 없습니다" in hb,
                "쓰기단추": page.get_by_role("button", name="인계 메모 쓰기").count(),
                "초안": "교대 인계 초안" in hb,
                "미처리줄": bool(re.search(r'미처리: ', hb)),
                "sample": re.sub(r'\s+', ' ', hb)[:300],
            }
            # ── P-123 ③ 없는 사건 ──────────────────────────────────────
            calls.clear()
            page.goto(WEB + "/dsm/events/999999999", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(6000)
            eb = page.inner_text("body")
            st = [s for u, s in calls if "/api/dsm/events/999999999" in u]
            rec["missing_event"] = {
                "status": st,
                "없는항목": "없는 항목입니다" in eb,
                "옛문구": "불러오지 못했습니다" in eb,
                "다시시도": "다시 시도" in eb,
                "알림보내기": page.get_by_role("button", name="알림 보내기").count(),
                "sample": re.sub(r'\s+', ' ', eb)[:300],
            }
        except Exception as exc:
            rec["error"] = "%s %s" % (type(exc).__name__, exc)
        finally:
            try: ctx.close(); b.close()
            except Exception: pass
        out.append(rec)
        print("[REACH] %s %s" % (bucket, rec.get("error", "ok")), flush=True)
        for x in rec["paths"]:
            print("   %-24s %s bytes=%-6s api=%-3s bad=%s denied=%s" % (
                x["path"], x["url"].replace(WEB, ""), x["bytes"], x["api_calls"],
                x["api_bad"], x["denied"]), flush=True)
        if "handover" in rec:
            print("   handover:", json.dumps(rec["handover"], ensure_ascii=False)[:400], flush=True)
        if "missing_event" in rec:
            print("   404event:", json.dumps(rec["missing_event"], ensure_ascii=False)[:400], flush=True)
with open("/tmp/gx_reach.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print("[REACH] -> /tmp/gx_reach.json")
