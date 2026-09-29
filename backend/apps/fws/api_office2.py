# -*- coding: utf-8 -*-
"""FWS F3 산림과 담당 — 대피·보고·통계·오탐률·단속·훈련·온보딩(F3-11~20).

턴 AN · WO-17 · 차선 N3 단독 소유 파일(조율자가 빈 컨트롤러로 세워 `urls.py` 에 등록해 둠).
`api.py` 는 이 턴에 아무 차선도 고치지 않는다 — 문은 전부 이 파일에 더한다.
★ `from __future__ import annotations` 를 쓰지 않는다(D-378 · `api.py` 머리말과 같은 까닭).
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


@api_controller("", tags=["FWS — 산림과 F3 잔여 (턴 AN · N3)"])
class FwsOffice2API:
    pass
