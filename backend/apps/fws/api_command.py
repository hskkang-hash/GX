# -*- coding: utf-8 -*-
"""FWS F4 통합지휘본부장 (FWS-F4-01~15 · 명세 제목이 정본).

턴 AO · WO-18 · 차선 N2 단독 소유 파일(조율자가 빈 컨트롤러로 세워 `urls.py` 에 등록해 둠).
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


@api_controller("", tags=["FWS — 지휘 F4 (턴 AO · N2)"])
class FwsCommandAPI:
    pass
