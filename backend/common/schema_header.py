# -*- coding: utf-8 -*-
"""`X-GX-Schema: 1.1` — **모든 응답**에 스키마 버전 한 줄 (턴 T · 차선 U56 · P-164).

왜 헤더인가 — 본문은 라우트마다 다르고 실패 본문은 더 다르다. 외부 연계(U6)가 「이
서버가 어느 계약으로 말하는가」를 **응답 하나로** 알려면 본문 밖에 있어야 한다.
200 도 4xx 도 5xx 도 같은 헤더를 단다 — 실패 응답에 없으면 상대는 「옛 서버」와
「죽은 서버」를 못 가른다.

자리 — `MIDDLEWARE` 의 **맨 위**(SecurityMiddleware 위). 바깥일수록 안쪽 어느 겹이
응답을 만들든(캐시 적중 · 관문 401 · 5xx 표지) 전부 이 겹을 지난다. 헤더 하나를
붙일 뿐 본문·상태줄·다른 헤더를 읽지도 고치지도 않는다.

되돌리기는 `SCHEMA_HEADER_ENABLED = False` 한 줄이다(설정에 없으면 켜짐).
"""
from __future__ import annotations

from django.conf import settings

HEADER_NAME = "X-GX-Schema"
SCHEMA_VERSION = "1.1"


def enabled() -> bool:
    return bool(getattr(settings, "SCHEMA_HEADER_ENABLED", True))


class SchemaHeaderMiddleware:
    """응답마다 `X-GX-Schema` 를 단다. 이미 있으면(뷰가 직접 달았으면) 덮지 않는다."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if enabled() and not response.has_header(HEADER_NAME):
            response[HEADER_NAME] = SCHEMA_VERSION
        return response


__all__ = ["SchemaHeaderMiddleware", "HEADER_NAME", "SCHEMA_VERSION", "enabled"]
