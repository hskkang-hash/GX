# -*- coding: utf-8 -*-
"""DSM U5 시스템 관리자 — 운영·관리 방침 항목(DSM-U5-01) · 연계 설정(DSM-U5-03).

턴 AN · WO-17 · 차선 N4 단독 소유 파일(조율자가 빈 컨트롤러로 세워 `urls.py` 에 등록해 둠).
★ `from __future__ import annotations` 를 쓰지 않는다(D-378).
★ 새 `/api/dsm/` 라우트는 `tests/test_f05_event_api.py::EVENT_ENTRY_SURFACE` 에 올라야 한다 —
  그 파일은 조율자 몫이니 차선은 보고에 줄을 적는다.

경로는 전부 `/u5an/...` 아래에 둔다 — `apps/dsm/api.py` 의 유일한 변수 조각
`/settings/{domain}`(GET·2조각)을 피하려고 아예 다른 리터럴을 쓴다(같은 함정을
`api_u56.py` 머리말이 이미 세 번 적어 두었다 — 그 뒤를 따르지 않고 처음부터
겹칠 수 없는 이름을 고른다).

로직은 `apps/dsm/u5_an_service.py` 하나에 있다 — 이 파일은 그 함수를 HTTP 로
여는 얇은 문일 뿐이다.
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


@api_controller("", tags=["DSM — U5 방침·연계 (턴 AN · N4)"])
class DsmU5AnAPI:
    # ═══════════════════════════════════════════════════════════════════
    # DSM-U5-01 — 운영·관리 방침 항목 관리
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/u5an/privacy-policy", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-01 방침 조회 — 남의 테넌트 방침·카메라 대수는 남의 정보다")
    def u5an_privacy_policy_get(self, request):
        from apps.dsm import u5_an_service

        try:
            return u5_an_service.privacy_policy(scope=_scope(request))
        except u5_an_service.U5AnPermissionDenied as exc:
            raise HttpError(403, str(exc))

    @route.post("/u5an/privacy-policy", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-01 방침 저장 — 관리자만. 남의 테넌트 방침을 바꿀 수 없다")
    def u5an_privacy_policy_save(self, request, purpose: str = "",
                                 install_locations: str = "", filming_scope: str = "",
                                 responsible_person: str = "", access_grantees: str = "",
                                 filming_hours: str = "", viewing_procedure: str = ""):
        from apps.dsm import u5_an_service

        try:
            return u5_an_service.save_privacy_policy(
                scope=_scope(request), purpose=purpose, install_locations=install_locations,
                filming_scope=filming_scope, responsible_person=responsible_person,
                access_grantees=access_grantees, filming_hours=filming_hours,
                viewing_procedure=viewing_procedure)
        except u5_an_service.U5AnPermissionDenied as exc:
            raise HttpError(403, str(exc))
        except u5_an_service.U5AnInputRejected as exc:
            raise HttpError(422, str(exc))

    # ═══════════════════════════════════════════════════════════════════
    # DSM-U5-03 — 연계 설정(스마트시티 통합플랫폼·112·119·NDMS)
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/u5an/integrations", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-03 연계 설정 조회 — 남의 테넌트 연계 상태는 남의 정보다")
    def u5an_integrations_list(self, request):
        from apps.dsm import u5_an_service

        try:
            return u5_an_service.list_integrations(scope=_scope(request))
        except u5_an_service.U5AnPermissionDenied as exc:
            raise HttpError(403, str(exc))

    @route.post("/u5an/integrations", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-03 연계 설정 저장 — 관리자만. 값(비밀)은 어디에도 싣지 않는다")
    def u5an_integration_save(self, request, service: str, endpoint_name: str = "",
                              outbound_api_key_ref: str = ""):
        from apps.dsm import u5_an_service

        try:
            return u5_an_service.save_integration_endpoint(
                scope=_scope(request), service=service, endpoint_name=endpoint_name,
                outbound_api_key_ref=outbound_api_key_ref)
        except u5_an_service.U5AnPermissionDenied as exc:
            raise HttpError(403, str(exc))
        except u5_an_service.U5AnInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.post("/u5an/integrations/test", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-03 연결 시험 — 관리자만. 설정 완결성만 보고 외부로 나가지 않는다")
    def u5an_integration_test(self, request, service: str):
        from apps.dsm import u5_an_service

        try:
            return u5_an_service.test_integration_connection(
                scope=_scope(request), service=service)
        except u5_an_service.U5AnPermissionDenied as exc:
            raise HttpError(403, str(exc))
        except u5_an_service.U5AnInputRejected as exc:
            raise HttpError(422, str(exc))
