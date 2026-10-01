#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-454 [N4] 게이트 — 빌드 산출물(dist)에 `localhost:8000` 이 0 건인가.

운영 모양의 번들은 API·웹소켓 주소를 **화면이 온 곳**(location.host)에서 얻는다.
`localhost:8000` 이 남아 있으면 대표 PC 밖의 브라우저에게는 자기 컴퓨터를 가리키는
죽은 주소다.

    python scripts/verify_bundle_origin.py [dist 폴더 ...]   # 기본: backend/_fe_dist_ar_n4
    python scripts/verify_bundle_origin.py --self-test

종료 코드: 0 초록 · 1 빨강 · 2 못 쟀다(폴더 없음/파일 0)
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIST = ROOT / "backend" / "_fe_dist_ar_n4"
NEEDLE = "localhost:8000"
EXTS = {".js", ".mjs", ".css", ".html", ".json", ".map"}


def scan(dist: Path):
    """(검사한 파일 수, {파일: 건수})"""
    files, hits = 0, {}
    for p in sorted(dist.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in EXTS or p.suffix.lower() == ".map":
            continue
        files += 1
        n = p.read_bytes().decode("utf-8", "ignore").count(NEEDLE)
        if n:
            hits[str(p.relative_to(dist))] = n
    return files, hits


def judge(dist: Path) -> int:
    if not dist.is_dir():
        print("[BUNDLE_ORIGIN] 회색 — 못 쟀다: %s 폴더가 없다" % dist)
        return 2
    files, hits = scan(dist)
    total = sum(hits.values())
    print("[BUNDLE_ORIGIN] [입력] %s · 검사한 파일 %d개 · `%s` %d건" % (dist, files, NEEDLE, total))
    if files == 0:
        print("[BUNDLE_ORIGIN] 회색 — 못 쟀다: 검사할 파일이 0개")
        return 2
    if total:
        for f, n in hits.items():
            print("[BUNDLE_ORIGIN]   %s : %d" % (f, n))
        print("[BUNDLE_ORIGIN] 빨강 — 번들에 localhost:8000 이 남았다")
        return 1
    print("[BUNDLE_ORIGIN] 초록 — localhost:8000 0건")
    return 0


def self_test() -> int:
    ok = True
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "a.js").write_text('var u="ws://localhost:8000/ws/x";', encoding="utf-8")
        f, h = scan(d)
        pos = (f == 1 and sum(h.values()) == 1)
        #: 출생 표본 — 턴 AQ P-444 에서 대표가 본 번들: 주문 화면 소켓이
        #: `${VITE_STREAMING_WS}/ws/orders/notifications/` 를 기본값 ws://localhost:8000 으로 구웠다.
        (d / "a.js").write_text('const s={socketUrl:"ws://localhost:8000/ws/orders/notifications/"};', encoding="utf-8")
        f, h = scan(d)
        pos = pos and (f == 1 and sum(h.values()) == 1)
        (d / "a.js").write_text('var u=location.host;', encoding="utf-8")
        f, h = scan(d)
        neg = (f == 1 and sum(h.values()) == 0)
    print("[BUNDLE_ORIGIN] 자기시험 양성표본(잡아야 함): %s · 음성표본(안 잡아야 함): %s"
          % ("통과" if pos else "실패", "통과" if neg else "실패"))
    ok = pos and neg
    return 0 if ok else 1


def main(argv) -> int:
    if "--self-test" in argv:
        return self_test()
    dirs = [Path(a) for a in argv if not a.startswith("--")] or [DEFAULT_DIST]
    rc = 0
    for d in dirs:
        rc = max(rc, judge(d))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
