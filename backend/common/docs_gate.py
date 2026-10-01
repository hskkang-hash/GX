# -*- coding: utf-8 -*-
"""P-454 [N4] — `/api/docs` · `/api/openapi.json` 은 환경 이름 `GX_API_DOCS` 로 감싼다.

운영 모양(8500)에서 API 문서는 익명에게 200 이었다. 기본은 **꺼짐**:

    GX_API_DOCS 꺼짐(기본) : 익명 → 404 (없는 것은 없다고 말한다 · D-290)
                             로그인한 U0(시스템 관리자: is_superuser 또는 is_staff) → 200 그대로
    GX_API_DOCS 켜짐(1/true/yes/on) : 기존 그대로(익명 200)

U0 판정은 `request.user` 만 본다 — 토큰을 또 풀지 않는다(JWTUserRestore 가 세운 사용자).
그래서 자리는 `RoleGateMiddleware` 다음이다. 되돌리기는 환경 이름 하나를 켜는 것이다.
"""
from __future__ import annotations

import os

from django.http import HttpResponseNotFound

ENV_NAME = "GX_API_DOCS"
GUARDED_PREFIXES: tuple[str, ...] = ("/api/docs", "/api/openapi.json")


def docs_enabled() -> bool:
    return os.getenv(ENV_NAME, "").strip().lower() in ("1", "true", "yes", "on")


#: [턴 AR · 조율자] 앱마다 NinjaAPI 가 제 문서 문을 둔다(`/api/<app>/docs` · `/api/<app>/openapi.json`
#: · `/api/v1/access/…` — 실측 48개). 두 줄만 막으면 나머지 46 이 익명 200 이다. 그래서 **마지막
#: 칸 이름**으로 가른다: `/api/` 아래에서 마지막 칸이 `docs` 또는 `openapi.json` 이면 문서 문이다.
DOC_SEGMENTS: frozenset[str] = frozenset({"docs", "openapi.json"})


def is_docs_path(path: str) -> bool:
    if any(path == p or path.startswith(p + "/") for p in GUARDED_PREFIXES):
        return True
    segs = [s for s in path.split("/") if s]
    return len(segs) >= 2 and segs[0] == "api" and segs[-1] in DOC_SEGMENTS


def is_u0(user) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return bool(getattr(user, "is_superuser", False) or getattr(user, "is_staff", False))


class DocsGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if is_docs_path(request.path) and not docs_enabled():
            if not is_u0(getattr(request, "user", None)):
                return HttpResponseNotFound("Not Found")
        return self.get_response(request)
