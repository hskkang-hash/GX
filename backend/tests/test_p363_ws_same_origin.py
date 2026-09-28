# -*- coding: utf-8 -*-
"""P-363 — 웹소켓 주소는 화면이 온 곳을 따른다 (턴 AK·AL · 2026-09-28).

`ws://localhost:8000` 은 대표 PC 밖의 브라우저에게 **자기 컴퓨터**다 — 바깥 사용자에게는 언제나 죽은
소켓이다. 소켓 주소는 `services/wsBase.ts::wsBase()` 한 곳에서만 짓는다. 이 시험은 프런트 소스에
`localhost:8000` 과 `${VITE_STREAMING_WS}/ws/…` 조립이 **다시 생기면** 멈춘다.

남겨 둔 자리 둘(이름으로): `wsBase.ts` 자신(환경값 되돌림) · `features/delivery/**`(§0.4 — 읽기만).

캐시 처리: 해당 없음 — HTTP 를 부르지 않고 소스 파일만 읽는다.
절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import re
from pathlib import Path

from django.test import SimpleTestCase

ALLOWED = ("services/wsBase.ts",)
FORBIDDEN_ZONE = ("features/delivery/",)
PATTERNS = (re.compile(r"['\"`]ws://localhost:8000"),
            re.compile(r"\$\{import\.meta\.env\.VITE_STREAMING_WS\}/ws/"))


def _src() -> Path | None:
    for base in (Path("/repo/frontend/src"),
                 *(p / "frontend" / "src" for p in Path(__file__).resolve().parents)):
        if (base / "services" / "wsBase.ts").is_file():
            return base
    return None


class SocketAddressComesFromOnePlace(SimpleTestCase):
    def test_no_hardcoded_socket_origin_outside_wsbase(self) -> None:
        src = _src()
        self.assertIsNotNone(src, "frontend/src 를 못 찾았다 — 판정 불가를 초록으로 두지 않는다")
        hits = []
        for p in src.rglob("*.ts*"):
            rel = p.relative_to(src).as_posix()
            if rel in ALLOWED or rel.startswith(FORBIDDEN_ZONE):
                continue
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                code = line.split("//", 1)[0]
                if any(rx.search(code) for rx in PATTERNS):
                    hits.append(f"{rel}:{i}")
        self.assertEqual([], hits, "소켓 주소를 wsBase() 밖에서 지었다")

    def test_the_rule_can_fail(self) -> None:
        """짝 — 옛 모양 두 줄이 실제로 걸린다(P-323)."""
        self.assertTrue(PATTERNS[0].search("socketUrl = 'ws://localhost:8000/ws/drawing/session/1/',"))
        self.assertTrue(PATTERNS[1].search("socketUrl: `${import.meta.env.VITE_STREAMING_WS}/ws/x/`,"))
