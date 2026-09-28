# -*- coding: utf-8 -*-
"""DSM-U5-02 앞 갈래 — **사람별 카메라·기능 권한** 라우터. 차선 O · 턴 AM.

이 파일 하나만 고친다 — 이 절의 뒤 갈래(접속기록)는 `api_u24.py`(차선 N1 소유)에
이미 있고, 이번 턴은 그 파일을 고치지 않는다(§0.4 차선 경계). 같은 턴에 두 차선이
한 라우트 파일을 고치면 충돌하고, 충돌한 라우트는 **라우팅 침묵**이 된다(메모리
「라우트 삼킴 함정」) — 그래서 새 컨트롤러를 새 파일에 연다.

경로는 `/access-log/permissions` 로 같은 절 아래 묶는다
--------------------------------------------------------
★ 삼킴 없음 [실측 확인]: `api_u24.py` 의 `/access-log`·`/access-log/export.csv` 는
  **둘 다 완전한 리터럴**이고 그 뒤에 변수 조각이 없다 — `/access-log/permissions`
  를 새 리터럴로 더해도 삼킬 것도 삼켜질 것도 없다. 저장소 전체(`api.py` ·
  `api_u1.py` · `api_u3.py` · `api_u24.py` · `api_u56.py` · `law_api.py`)에
  `/access-log` 로 시작하는 다른 등록이 없다(grep 재확인).

★ `from __future__ import annotations` 를 쓰지 않는다 — `api_u24.py` 머리말과
  같은 이유(D-378, `@tenant_scoped` 데코레이터가 주석을 그 모듈의 `__globals__`
  에서 푼다).

로직은 `apps/dsm/access_permission_service.py` 에 있다 — 이 파일은 그 함수
하나를 HTTP 로 여는 얇은 문일 뿐이다(`api_u24.py::access_log_read` 와 같은 모양).
"""
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import TenantScope, tenant_scoped

from apps.dsm import access_permission_service


def _scope(request) -> TenantScope:
    """`api_u24.py::_scope` 와 같은 세 줄 — 새 인증 경로를 만들지 않는다(파일마다
    이 셋을 그대로 두는 것이 규약이다, `api_u24.py::_scope` 주석 참조)."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


@api_controller("", tags=["DSM — U5 접근권한 매트릭스 (P-376 반쪽 메움 · 차선 O)"])
class DsmU5PermAPI:
    """DSM-U5-02 앞 갈래 — 사람별 카메라·기능 권한 표. 새 컨트롤러 하나, 라우트 하나."""

    @route.get("/access-log/permissions", auth=JwtOrInboundKey())
    @tenant_scoped(reason="권한 매트릭스 — 남의 테넌트 사람·카메라·기능 권한이 보이면 "
                         "격리 실패다")
    def access_permissions(self, request, limit: int = 200):
        """`GET /access-log/permissions` — DSM-U5-02 앞 갈래. 문지기는 접속기록과
        같다(시스템관리자·테넌트관리자·전역관리자만 — `access_log_service.py` 와
        같은 무게로 좁힌다)."""
        try:
            return access_permission_service.person_permissions(
                scope=_scope(request), limit=limit)
        except access_permission_service.AccessPermissionDenied as exc:
            raise HttpError(403, str(exc))
