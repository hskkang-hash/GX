# -*- coding: utf-8 -*-
"""QA 10키 브라우저 실측 — WO-GRDX-20261007-01 T1 레인 D·S (규격 09 M2 「첫 화면」 · M4 「QA 바 스크린샷」).

키마다 새 브라우저 문맥에서 `http://127.0.0.1:8510/qa/as/<키>` 를 열고 `/qa/enter` 를 지나 도착한 주소,
QA 바(`role=region name=QA 도구`) 유무, 화면 캡처(PNG)를 남긴다. 키 하나에 탭 하나(동시 세션 1개 규칙).

    python scripts/qa/qa_walk_browser.py <캡처 폴더>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

import os

BASE = os.environ.get("GX_QA_BASE", "http://127.0.0.1:8510")  # gx-shell 안에서는 http://host.docker.internal:8510


def main(out: Path) -> int:
    import importlib.util
    keys_py = Path(os.environ.get("GX_QA_KEYS_PY", Path(__file__).resolve().parents[2] / "backend/apps/qa/keys.py"))
    spec = importlib.util.spec_from_file_location("k", keys_py)
    k = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(k)
    out.mkdir(parents=True, exist_ok=True)
    rows, ok = [], 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for key in k.QA_KEYS:
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            page.goto(f"{BASE}/qa/as/{key}", wait_until="domcontentloaded", timeout=60000)
            deadline = time.time() + 40
            while time.time() < deadline and "/qa/enter" in page.url:
                page.wait_for_timeout(500)
            page.wait_for_timeout(4000)
            bar = page.get_by_role("region", name="QA 도구").count() > 0
            bar_text = page.get_by_role("region", name="QA 도구").inner_text() if bar else ""
            path = page.url.replace(BASE, "")
            arrived = "/qa/enter" not in path and not path.startswith("/login")
            shot = out / f"{key}.png"
            page.screenshot(path=str(shot))
            row = {"account": key, "arrived": path, "ok": arrived, "qa_bar": bar, "bar_has_key": key in bar_text}
            ok += arrived and bar
            rows.append(row)
            print(("OK  " if arrived and bar else "BAD ") + json.dumps(row, ensure_ascii=False))
            ctx.close()
        browser.close()
    (out / "walk.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[QA-BROWSER] 첫 화면 도착 + QA 바 {ok}/{len(rows)}")
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(Path(sys.argv[1])))
