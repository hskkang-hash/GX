# -*- coding: utf-8 -*-
"""P-342 — 비밀번호 찾기 화면이 묻는 문 (턴 AJ · 2026-09-25).

rj-core 데스크톱 화면은 503 을 `console.log` 로만 삼킨다(§0.4 · 못 고친다). 우리 감싸개
(`frontend/src/features/passwordReset/ResetMailNotice.tsx`)가
`GET /api/v1/auth/forgot-password/availability` 로 묻고 제 띠를 그린다.

재는 것 셋
    ① SMTP 죽음 → `available: false` + 고객 말(ko) · 캐시 안 됨
    ② SMTP 살아 있음 → `available: true` · 고객 말 없음
    ③ 이 문은 주소를 받지 않는다 — 쿼리에 주소를 실어도 답이 바이트까지 같다

절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

from unittest import mock

from django.test import Client, TestCase

from common import reset_mail_gate
from tests.no_cache import NO_CACHE

URL = reset_mail_gate.AVAILABILITY_PATH


class AvailabilityTests(TestCase):
    def setUp(self) -> None:
        self.client = Client(**NO_CACHE)  # 캐시 처리: 우회 — 60초 SMTP 판정 캐시는 smtp_reachable patch 로 비켜 간다

    def test_dead_smtp_says_unavailable_with_copy(self) -> None:
        with mock.patch("common.reset_mail_gate.smtp_reachable", return_value=False):
            resp = self.client.get(URL)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIs(body["available"], False)
        self.assertEqual(body["code"], reset_mail_gate.UNREACHABLE_CODE)
        self.assertEqual(body["message"]["ko"], reset_mail_gate.MESSAGE["ko"])
        self.assertEqual(resp["Cache-Control"], "no-store")

    def test_live_smtp_says_available_without_copy(self) -> None:
        with mock.patch("common.reset_mail_gate.smtp_reachable", return_value=True):
            resp = self.client.get(URL)
        self.assertEqual(resp.json(), {"available": True})

    def test_address_in_query_changes_nothing(self) -> None:
        with mock.patch("common.reset_mail_gate.smtp_reachable", return_value=False):
            plain = self.client.get(URL).content
            with_addr = self.client.get(URL, {"email": "someone@test.invalid"}).content
        self.assertEqual(plain, with_addr)


# ── 화면 쪽 배선(정적) — 프런트 시험 실행기가 없어 소스를 읽는다 ─────────────────
from pathlib import Path  # noqa: E402


def _frontend_src() -> Path | None:
    for base in (Path("/repo/frontend/src"), *(p / "frontend" / "src" for p in Path(__file__).resolve().parents)):
        if (base / "App.tsx").is_file():
            return base
    return None


class ScreenWiringTests(TestCase):
    """띠가 두 화면(데스크톱 rj-core · 모바일 우리 것)을 **다** 감싸고, 서버와 같은 문을 묻는다."""

    def setUp(self) -> None:
        self.src = _frontend_src()
        self.assertIsNotNone(self.src, "frontend/src 를 못 찾았다 — 판정 불가를 초록으로 두지 않는다")

    def test_wrapper_wraps_both_screens(self) -> None:
        app = (self.src / "App.tsx").read_text(encoding="utf-8")
        start = app.index("const ForgotPassword = () =>")
        body = app[start:app.index("};", start)]
        self.assertIn("<ResetMailNotice>", body)
        self.assertIn("<ForgotPasswordMobile />", body)
        self.assertIn("<ForgotPasswordPage", body)
        # 감싸개 밖으로 새는 갈래(예: isMobile 이면 먼저 return)가 없어야 한다
        self.assertEqual(body.count("return"), 1)

    def test_notice_asks_the_same_door_as_the_server(self) -> None:
        notice = (self.src / "features/passwordReset/ResetMailNotice.tsx").read_text(encoding="utf-8")
        self.assertIn(f"'{reset_mail_gate.AVAILABILITY_PATH}'", notice)
        self.assertIn("RETRY_LABEL", notice)
        self.assertIn('role="alert"', notice)
