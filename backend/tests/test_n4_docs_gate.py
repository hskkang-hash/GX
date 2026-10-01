# -*- coding: utf-8 -*-
"""P-454 [N4] — API 문서 문: 익명 404 · U0 로그인 200 · 켜면 기존 그대로."""
from types import SimpleNamespace

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from common.docs_gate import DocsGateMiddleware, ENV_NAME

RF = RequestFactory()


def _mw():
    return DocsGateMiddleware(lambda request: HttpResponse("doc", status=200))


def _get(path, user):
    req = RF.get(path)
    req.user = user
    return _mw()(req)


ANON = SimpleNamespace(is_authenticated=False)
U0 = SimpleNamespace(is_authenticated=True, is_superuser=True, is_staff=False)
STAFF = SimpleNamespace(is_authenticated=True, is_superuser=False, is_staff=True)
PLAIN = SimpleNamespace(is_authenticated=True, is_superuser=False, is_staff=False)
PATHS = ["/api/docs", "/api/docs/", "/api/openapi.json",
         # [턴 AR] 앱별 문서 문(실측 48개 중 표본) — 두 줄만 막으면 이것들이 익명 200 이었다
         "/api/dsm/docs", "/api/dsm/openapi.json", "/api/handover/docs/",
         "/api/v1/access/openapi.json"]


@pytest.mark.parametrize("path", PATHS)
def test_off_anonymous_is_404(monkeypatch, path):
    monkeypatch.delenv(ENV_NAME, raising=False)
    assert _get(path, ANON).status_code == 404
    assert _get(path, PLAIN).status_code == 404


@pytest.mark.parametrize("path", PATHS)
def test_off_u0_is_200(monkeypatch, path):
    monkeypatch.delenv(ENV_NAME, raising=False)
    assert _get(path, U0).status_code == 200
    assert _get(path, STAFF).status_code == 200


@pytest.mark.parametrize("path", PATHS)
def test_on_anonymous_unchanged(monkeypatch, path):
    monkeypatch.setenv(ENV_NAME, "1")
    assert _get(path, ANON).status_code == 200


def test_other_paths_untouched(monkeypatch):
    monkeypatch.delenv(ENV_NAME, raising=False)
    assert _get("/api/v1/auth/login", ANON).status_code == 200
    assert _get("/api/docsx", ANON).status_code == 200
    assert _get("/api/dsm/events", ANON).status_code == 200
    assert _get("/docs", ANON).status_code == 200            # /api 밖은 이 문의 일이 아니다


def test_middleware_registered_after_role_gate():
    from django.conf import settings
    mw = settings.MIDDLEWARE
    assert mw.index("common.docs_gate.DocsGateMiddleware") > mw.index("common.role_gate.RoleGateMiddleware")
