#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""[턴 AR · P-458 · 차선 Q] 브라우저 누름 22 행 — **Playwright 뼈대** (V 가 채워 돌린다).

`verify_click_completes.py` 의 `browser_clicked` 열을 채우는 도구다. 이 파일은 **뼈대뿐**이다:

  * 기본 실행(`--plan`)은 대상 표와 증거 스키마만 찍는다 — 브라우저도 서버도 안 건드린다.
  * `--run` 은 `GX_BROWSER_CLICK_OK=1` 이 환경에 있어야만 돈다(실수로 8500 을 누르지 않게).
    이번 턴(AR · Q)은 **한 번도 돌리지 않았다** — 8500 을 실제로 누르는 것은 V 몫이다.

증거 스키마(`docs/agent/evidence/P-118/click_completes_browser.json`):

    {"measured_at": "<ISO>", "spa": "<주소>", "observations": {
        "<data-gx 토큰>": {"verdict": "green|red", "clause": "FWS-F4-02",
                           "control_found": true, "clicked": true,
                           "call": {"method": "POST", "url": "...", "status": 200},
                           "after_get": {"url": "...", "status": 200, "reflected": true},
                           "why": "한 줄"}}}

판정기는 `verdict` 가 green/red 인 키만 `browser_clicked` 로 센다 — 없으면 회색이다.

역할 계정: `gx-smoke` 가 아니라 **역할 계정**(scripts/verify_click_completes.py 의 PERSONAS 와 같은
저장소 밖 .env.gates 자격)으로 로그인한다. 자격은 이 파일에 적지 않는다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_click_completes import BROWSER_OBSERVED, BROWSER_TARGETS  # noqa: E402


def plan() -> int:
    print("[BROWSER-22] 대상 %d행 (F4 · O) — 증거 파일: %s" % (len(BROWSER_TARGETS), BROWSER_OBSERVED))
    for clause, gx in BROWSER_TARGETS:
        print("   %-10s [data-gx=%s]" % (clause, gx))
    print("[BROWSER-22] 뼈대다 — 로그인 · 화면 이동 · 누름 · 재조회는 V 가 `click_one` 에 채운다")
    return 0


def click_one(page, clause: str, gx: str) -> dict:
    """한 대상을 누르고 관측 한 건을 돌려준다. TODO(V): 화면 경로 · 준비 단계 · 누른 뒤 재조회.

    못 채운 동안은 verdict 를 **주지 않는다**(= 회색). 지어낸 초록은 없다.
    """
    el = page.locator('[data-gx="%s"]' % gx)
    return {"clause": clause, "control_found": el.count() > 0, "clicked": False,
            "why": "뼈대 — 누름 로직 미구현(V 몫)"}


def run(spa: str) -> int:
    if os.environ.get("GX_BROWSER_CLICK_OK") != "1":
        print("[BROWSER-22] GX_BROWSER_CLICK_OK=1 이 없다 — 누르지 않는다(8500 보호)")
        return 2
    from playwright.sync_api import sync_playwright  # 지연 임포트 — 뼈대만 볼 때는 필요 없다
    from datetime import datetime
    obs: dict = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_context(locale="ko-KR").new_page()
        # TODO(V): 역할 계정 로그인(.env.gates) — 대상 화면마다 역할이 다르다(F4 지휘 · O 운영자)
        for clause, gx in BROWSER_TARGETS:
            obs[gx] = click_one(page, clause, gx)
        browser.close()
    doc = {"measured_at": datetime.now().isoformat(timespec="seconds"), "spa": spa, "observations": obs}
    BROWSER_OBSERVED.parent.mkdir(parents=True, exist_ok=True)
    BROWSER_OBSERVED.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print("[BROWSER-22] 증거를 썼다: %s" % BROWSER_OBSERVED)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="브라우저 누름 22 행 (뼈대)")
    ap.add_argument("--plan", action="store_true", help="대상 표만 찍는다(기본)")
    ap.add_argument("--run", action="store_true", help="실제로 누른다(GX_BROWSER_CLICK_OK=1 필요)")
    ap.add_argument("--spa", default="http://localhost:3002")
    a = ap.parse_args()
    return run(a.spa) if a.run else plan()


if __name__ == "__main__":
    sys.exit(main())
