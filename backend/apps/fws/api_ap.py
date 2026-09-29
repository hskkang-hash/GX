# -*- coding: utf-8 -*-
"""FWS 잔여 새 절(턴 AP · WO-19 · 차선 N4 단독 소유 · F3·F5·F6 잔여 · 명세 제목이 정본).

조율자가 빈 컨트롤러로 세워 `urls.py` 에 등록해 둠. `api.py`·다른 차선 파일은 고치지 않는다.
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


@api_controller("", tags=["FWS — 잔여 새 절 (턴 AP · N4)"])
class FwsApAPI:
    pass
