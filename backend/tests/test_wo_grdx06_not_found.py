# -*- coding: utf-8 -*-
"""WO-GRDX-20261002-06 AC-2·AC-3 — 없는 주소와 서버 오류가 내부를 보이지 않는다.

출생 표본 [실측 2026-10-02 20:3x · 8500 · DJANGO_DEBUG=True]
    GET /start · /no-such-page · /api/x  ->  404 · 「Django tried these URL patterns」 · 「DEBUG = True」
이 시험은 DEBUG=False 판(운영 모양)에서 장고가 우리 처리기를 부르는지, 본문에 주소 규칙 ·
디버그 문장 · 역추적이 0 인지 잰다.

캐시 처리: 해당 없음 — 응답 캐시를 타지 않는 404·500 처리기만 부른다.
"""
import json

import pytest
from django.test import Client, RequestFactory, override_settings

from common import not_found
from config import urls as root_urls

LEAKS = ("Django tried", "DEBUG = True", "Traceback", "urlpatterns", "File \"")


def _no_leak(body: str):
    for word in LEAKS:
        assert word not in body, word


def test_handlers_are_wired_on_root_urlconf():
    assert root_urls.handler404 == "common.not_found.page_not_found"
    assert root_urls.handler500 == "common.not_found.server_error"


@pytest.mark.django_db
@override_settings(DEBUG=False)
@pytest.mark.parametrize("path", ["/no-such-page", "/start-x/deeper", "/admin-x"])
def test_unknown_screen_path_gets_korean_404_page(path):
    res = Client().get(path)
    assert res.status_code == 404
    body = res.content.decode("utf-8")
    assert "없는 화면입니다" in body
    assert 'href="/login"' in body and "로그인으로" in body
    assert "/logoguax.svg" in body
    assert res["Content-Type"].startswith("text/html")
    _no_leak(body)


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_unknown_api_path_gets_json_404():
    res = Client().get("/api/x-no-such-route/")
    assert res.status_code == 404
    assert res["Content-Type"].startswith("application/json")
    assert json.loads(res.content) == {"detail": "Not Found"}
    _no_leak(res.content.decode("utf-8"))


def test_server_error_bodies_carry_nothing_internal():
    rf = RequestFactory()
    page = not_found.server_error(rf.get("/dsm/home"))
    assert page.status_code == 500
    assert "잠시 뒤 다시 시도해 주세요" in page.content.decode("utf-8")
    _no_leak(page.content.decode("utf-8"))
    api = not_found.server_error(rf.get("/api/dsm/anything"))
    assert api.status_code == 500
    assert json.loads(api.content) == {"detail": "Internal Server Error"}


# ── AC-1 · AC-6 — 프런트 시험 실행기가 없어 소스를 읽는다(test_p342 와 같은 관례) ──
from pathlib import Path  # noqa: E402


def _frontend_src():
    for base in (Path("/repo/frontend/src"), *(p / "frontend" / "src" for p in Path(__file__).resolve().parents)):
        if (base / "App.tsx").exists():
            return base
    return None


def _read(rel):
    src = _frontend_src()
    assert src is not None, "frontend/src 를 못 찾았다 — 판정 불가를 초록으로 두지 않는다"
    return (src / rel).read_text(encoding="utf-8")


def test_onboarding_does_not_call_server_when_anonymous():
    # 출생 표본: 익명 /start → onboarding/progress 401 → 전역 401 처리기가 /login 으로 보냈다.
    body = _read("features/dsm/pages/Onboarding.tsx")
    assert "enabled: !kick && signedIn" in body
    assert "Boolean(useUserInfo())" in body


def test_login_screens_read_return_path_and_say_why():
    helper = _read("features/login/returnTo.ts")
    assert "export const LOGIN_REQUIRED = '로그인이 필요합니다';" in helper
    assert "startsWith('//')" in helper
    for rel in ("features/login/LoginDesktop.tsx", "features/LoginMobile/LoginMobile.tsx"):
        body = _read(rel)
        assert "returnPathFrom(location.state)" in body, rel
        assert "{LOGIN_REQUIRED}" in body, rel
        assert "navigate(back, { replace: true })" in body, rel
