# -*- coding: utf-8 -*-
"""플랫폼 운영자 U0 (O-01·02·05~12 · 명세 제목이 정본) — U0 만 · 고객 메뉴 0.

턴 AO · WO-18 · 차선 N3 단독 소유 파일(조율자가 빈 컨트롤러로 세워 `urls.py` 에 등록해 둠).
★ `from __future__ import annotations` 를 쓰지 않는다(D-378).
"""
from ninja.errors import HttpError
from ninja_extra import api_controller, route  # noqa: F401

from common.inbound_api_key import JwtOrInboundKey  # noqa: F401
from common.tenant_scope import TenantScope, tenant_scoped  # noqa: F401


def _scope(request) -> TenantScope:
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


@api_controller("", tags=["OPS — 플랫폼 운영자 (턴 AO · N3)"])
class DsmOpsAnAPI:
    pass
