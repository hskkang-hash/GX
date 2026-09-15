# -*- coding: utf-8 -*-
"""P-120 / UX-27 — **종결된 사건에 화면으로 닿는가**를 브라우저에서 잰다 (차선 C1 · 턴 O).

무엇을 재는가
-------------
  ① 프리셋마다 **화면이 실제로 그린 행**을 세고, 그중 「종결」이 몇인가.
     API 로 세지 않는다 — 재는 것은 「서버가 줄 수 있는가」가 아니라
     **「사람이 화면에서 볼 수 있는가」**다. 표는 20건씩 접히므로 **쪽을 넘겨** 센다.
  ② 감사 질문 한 줄 → 그 사건 하나까지 **몇 초**인가.
     시계는 사람이 첫 손을 대는 순간(목록 화면이 뜬 뒤)부터 상세 화면의
     사건번호가 보이는 순간까지다.

    GX_SEED_ROLE_PASSWORD=... python walk_p120.py --tag after --target-hhmm 13:14
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

DESKTOP = {"width": 1440, "height": 900}
PRESETS = ["all", "unhandled", "recent", "mine", "system"]
CLOSED = "종결"


def sign_in(page, web, user, password):
    page.goto(web + "/login", wait_until="domcontentloaded", timeout=60000)
    # ★ 16MB 번들이다. `networkidle` 뒤 1.5초로는 **첫 그리기 전**에 재는 수가 있고,
    #   그 빈 화면은 「로그인 화면이 고장났다」와 구별되지 않는다 — 칸이 설 때까지 기다린다.
    try:
        page.wait_for_selector("input", timeout=45000)
    except Exception:                                       # noqa: BLE001
        return False, "입력칸이 45초 안에 안 섰다 — 본문 " + repr(page.inner_text("body")[:160])
    page.wait_for_timeout(1500)
    f = page.locator("input")
    if f.count() < 2:
        return False, "입력칸이 둘 미만 — 본문 " + repr(page.inner_text("body")[:160])
    f.nth(0).fill(user)
    f.nth(1).fill(password)
    page.get_by_role("button", name="Log In").click()
    page.wait_for_timeout(9000)
    if not page.url.rstrip("/").endswith("/login"):
        return True, "한 번에"
    for lab in ("Confirm", "확인", "End Session", "OK"):
        b = page.get_by_role("button", name=lab)
        try:
            if b.count() > 0 and b.first.is_visible():
                b.first.click()
                page.wait_for_timeout(9000)
                if not page.url.rstrip("/").endswith("/login"):
                    return True, "확인 창(%s)" % lab
        except Exception:                                   # noqa: BLE001
            continue
    return False, page.inner_text("body")[:160]


def read_rows(page):
    """표가 **지금 그린** 행을 읽는다. 쪽을 넘겨 가며 전부 모은다."""
    seen: dict = {}
    for _ in range(10):
        page.wait_for_timeout(900)
        rows = page.locator(".ant-table-tbody > tr.ant-table-row")
        for i in range(rows.count()):
            try:
                cells = rows.nth(i).locator("td")
                if cells.count() < 6:
                    continue
                key = "|".join(cells.nth(j).inner_text().strip()
                               for j in range(cells.count()))
                seen[key] = {
                    "camera": cells.nth(2).inner_text().strip(),
                    "state": cells.nth(3).inner_text().strip(),
                    "occurred": cells.nth(5).inner_text().strip(),
                }
            except Exception:                               # noqa: BLE001
                continue
        nxt = page.locator("li.ant-pagination-next")
        try:
            cls = nxt.first.get_attribute("class") or ""
            if "disabled" in cls or nxt.count() == 0:
                break
            nxt.first.click()
        except Exception:                                   # noqa: BLE001
            break
    return list(seen.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="http://localhost:3002")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--user", default="gxseed_u2_manager")
    #: 감사 질문의 시각. 이 저장소의 씨앗에는 **09-12 자료가 없다** — 있는 날짜로 묻는다.
    ap.add_argument("--target-date", default="2026-09-03")
    ap.add_argument("--target-hhmm", default="13:14")
    args = ap.parse_args()

    pwd = os.environ.get("GX_SEED_ROLE_PASSWORD", "").strip()
    if not pwd:
        print("[P-120] 판정 불가 — 비밀번호가 없다")
        return 2
    from playwright.sync_api import sync_playwright

    out = Path("/docs/agent/evidence/P-120")
    (out / "shots").mkdir(parents=True, exist_ok=True)
    rep = {"tag": args.tag, "at": datetime.now().isoformat(timespec="seconds"),
           "web": args.web, "user": args.user, "presets": {}, "walk": {}}

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        ctx = b.new_context(viewport=DESKTOP)
        page = ctx.new_page()
        ok, why = sign_in(page, args.web, args.user, pwd)
        print("[P-120] 로그인 — %s (%s)" % (ok, why))
        if not ok:
            return 2

        # ── ① 프리셋마다 화면이 그린 것 ────────────────────────────────
        reach_closed: set = set()
        for key in PRESETS:
            page.goto("%s/dsm/events?preset=%s" % (args.web, key),
                      wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3500)
            body = page.inner_text("body")
            if "전체 보기" not in body and key == "all":
                rep["presets"][key] = {"missing": True}
                print("[P-120] %-9s — 이 프리셋이 화면에 없다" % key)
                continue
            rows = read_rows(page)
            closed = [r for r in rows if r["state"] == CLOSED]
            for r in closed:
                reach_closed.add(r["occurred"] + "|" + r["camera"])
            rep["presets"][key] = {"rows": len(rows), "closed": len(closed)}
            print("[P-120] %-9s — 화면에 그려진 행 %2d · 그중 종결 %d"
                  % (key, len(rows), len(closed)))
            page.screenshot(path=str(out / "shots" / ("%s_preset_%s.png" % (args.tag, key))))
        rep["closed_reachable_distinct"] = len(reach_closed)

        # ── ② 감사 질문 한 줄 → 사건 하나 ──────────────────────────────
        #    사람이 하는 그대로: 목록 → 전체 → 기간 직접 입력 → 그 시각의 행 → 상세
        page.goto("%s/dsm/events" % args.web, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        t0 = time.time()
        steps = []

        def step(name):
            steps.append({"step": name, "t": round(time.time() - t0, 2)})

        page.get_by_role("button", name="전체 보기").first.click()
        page.wait_for_timeout(1200)
        step("전체 보기")

        # 기간 — **단추와 칸을 실제로 누른다.** 주소로 뛰어넘으면 그것은 사람이
        # 걸은 시간이 아니라 우리가 아는 지름길의 시간이다.
        page.get_by_text("직접 입력", exact=True).first.click()
        page.wait_for_timeout(900)
        hh, mm = int(args.target_hhmm[:2]), int(args.target_hhmm[3:5])
        lo = "%s %02d:%02d" % (args.target_date, hh, max(0, mm - 10))
        hi = "%s %02d:%02d" % (args.target_date, hh, min(59, mm + 10))
        boxes = page.locator(".ant-picker-range input")
        boxes.nth(0).click()
        boxes.nth(0).fill(lo)
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)
        boxes.nth(1).fill(hi)
        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)
        page.keyboard.press("Escape")
        page.wait_for_timeout(2500)
        step("기간 직접 입력 (%s ~ %s)" % (lo, hi))
        rep["walk"]["window_typed"] = {"since": lo, "until": hi}
        rep["walk"]["window_in_url"] = page.url

        # 그 시각의 행 — **쪽을 넘기지 않고** 지금 화면에서 찾는다. 창을 좁혔으니
        # 한 쪽 안에 있어야 하고, 없으면 그것이 곧 판정이다.
        page.wait_for_timeout(500)
        table_rows = page.locator(".ant-table-tbody > tr.ant-table-row")
        rep["walk"]["rows_in_window"] = table_rows.count()
        hit = table_rows.filter(has_text=args.target_hhmm)
        found = hit.count() > 0
        rep["walk"]["row_found"] = found
        rep["walk"]["rows_text"] = [
            " / ".join(table_rows.nth(i).inner_text().split("\n"))
            for i in range(min(6, table_rows.count()))]
        if found:
            hit.first.click()
            page.wait_for_timeout(3500)
            step("사건 하나를 열었다")
            body = page.inner_text("body")
            m = re.search(r"/dsm/events/(\d+)", page.url)
            rep["walk"]["event_id"] = m.group(1) if m else None
            rep["walk"]["detail_shows_time"] = args.target_hhmm in body
        rep["walk"]["seconds"] = round(time.time() - t0, 2)
        rep["walk"]["steps"] = steps
        page.screenshot(path=str(out / "shots" / ("%s_walk_detail.png" % args.tag)))
        print("[P-120] 걷기 — 창 안 %s행 · 그 시각의 행 %s · 사건 %s · **%.1f초**"
              % (rep["walk"].get("rows_in_window"), found,
                 rep["walk"].get("event_id"), rep["walk"]["seconds"]))
        b.close()

    f = out / ("p120_%s.json" % args.tag)
    f.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[P-120] 기록 → %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
