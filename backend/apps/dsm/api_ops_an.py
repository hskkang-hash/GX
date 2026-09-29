# -*- coding: utf-8 -*-
"""플랫폼 운영자 U0 (O-01·02·05~12 · 명세 제목이 정본) — U0 만 · 고객 메뉴 0.

턴 AO · WO-18 · 차선 N3 단독 소유 파일(조율자가 빈 컨트롤러로 세워 `urls.py` 에 등록해 둠).
★ `from __future__ import annotations` 를 쓰지 않는다(D-378).
★ 새 `/api/dsm/` 라우트는 `tests/test_f05_event_api.py::EVENT_ENTRY_SURFACE` 에 올라야
  한다 — 그 파일은 조율자 몫이니 차선은 보고에 줄을 적는다.

경로는 전부 `/ops/...` 아래에 둔다(P-415 — `/ops/*` 한 갈래 · U0 만) — 기존
`/system/...`(F 차선 소유)와 안 겹친다. 로직은 전부 `apps/dsm/ops_an_service.py` 에
있다 — 이 파일은 그 함수를 HTTP 로 여는 얇은 문일 뿐이다(u5_an_service 와 같은 결).

Ninja 라우트는 원시 인자를 **질의(query)** 로 받는다(이 저장소 관례 — `law_api.py`
머리말 ④ · `u5_an_service` 증거가 그 모양). 여기도 같은 관례를 따른다.
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


def _actor(request):
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return user


def _translate(exc: Exception):
    from apps.dsm import ops_an_service as svc

    if isinstance(exc, svc.OpsAnPermissionDenied):
        return HttpError(403, str(exc))
    if isinstance(exc, svc.OpsAnInputRejected):
        return HttpError(422, str(exc))
    if isinstance(exc, svc.OpsAnNotFound):
        return HttpError(404, str(exc))
    raise exc


@api_controller("", tags=["OPS — 플랫폼 운영자 (턴 AO · N3)"])
class DsmOpsAnAPI:
    # ═══════════════════════════════════════════════════════════════════
    # O-01 — 테넌트 발급
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/ops/tenants", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-01 테넌트 목록 — U0 전용 전 테넌트 조회")
    def ops_tenants_list(self, request):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.list_tenants(actor=_actor(request))
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    @route.post("/ops/tenants", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-01 테넌트 발급 — U0 전용")
    def ops_tenants_issue(self, request, code: str, name: str, admin_username: str,
                          admin_email: str, admin_password: str, region: str = "",
                          public_url: str = "", domain: str = ""):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.issue_tenant(
                actor=_actor(request), code=code, name=name, admin_username=admin_username,
                admin_email=admin_email, admin_password=admin_password, region=region,
                public_url=public_url, domain=domain,
                auth_header=request.META.get("HTTP_AUTHORIZATION", ""))
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    @route.get("/ops/tenants/{tenant_code}/members", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-09 승인 뒤 테넌트 구성원 열람 — 승인 없이는 0")
    def ops_tenant_members(self, request, tenant_code: str):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.view_tenant_members(actor=_actor(request), tenant_code=tenant_code)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    # ═══════════════════════════════════════════════════════════════════
    # O-02 — 앱 설치·버전
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/ops/apps", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-02 설치 목록 — U0 전용")
    def ops_apps_list(self, request, tenant_code: str = ""):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.list_app_installs(actor=_actor(request), tenant_code=tenant_code or None)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    @route.post("/ops/apps/install", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-02 앱 설치 — U0 전용")
    def ops_apps_install(self, request, tenant_code: str, app_code: str, version: str):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.install_app(actor=_actor(request), tenant_code=tenant_code,
                                   app_code=app_code, version=version)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    @route.post("/ops/apps/status", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-02 앱 활성·비활성 — U0 전용")
    def ops_apps_status(self, request, tenant_code: str, app_code: str, status: str):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.set_app_status(actor=_actor(request), tenant_code=tenant_code,
                                      app_code=app_code, status=status)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    # ═══════════════════════════════════════════════════════════════════
    # O-05 — 건강 보드(전 테넌트)
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/ops/health", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-05 건강 보드 — 전 테넌트 · U0 전용")
    def ops_health_board(self, request):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.health_board(actor=_actor(request))
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    # ═══════════════════════════════════════════════════════════════════
    # O-06 — 인시던트
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/ops/incidents", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-06 인시던트 목록 — U0 전용")
    def ops_incidents_list(self, request, tenant_code: str = "", status: str = ""):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.list_incidents(actor=_actor(request), tenant_code=tenant_code or None,
                                      status=status or None)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    @route.post("/ops/incidents", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-06 인시던트 접수 — U0 전용")
    def ops_incidents_open(self, request, tenant_code: str, app_code: str, severity: str,
                           summary: str = ""):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.open_incident(actor=_actor(request), tenant_code=tenant_code,
                                     app_code=app_code, severity=severity, summary=summary)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    @route.post("/ops/incidents/{incident_id}/respond", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-06 1차 대응 — U0 전용")
    def ops_incidents_respond(self, request, incident_id: str, note: str = ""):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.respond_incident(actor=_actor(request), incident_id=incident_id, note=note)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    @route.post("/ops/incidents/{incident_id}/escalate", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-06 에스컬레이션 — U0 전용")
    def ops_incidents_escalate(self, request, incident_id: str, note: str = ""):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.escalate_incident(actor=_actor(request), incident_id=incident_id, note=note)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    @route.post("/ops/incidents/{incident_id}/close", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-06 종결 — U0 전용")
    def ops_incidents_close(self, request, incident_id: str, cause: str, prevention: str = ""):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.close_incident(actor=_actor(request), incident_id=incident_id,
                                      cause=cause, prevention=prevention)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    # ═══════════════════════════════════════════════════════════════════
    # O-07 — 백업·복구
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/ops/backups", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-07 백업 회수증·복원 시험 보드 — U0 전용")
    def ops_backups_board(self, request):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.backup_board(actor=_actor(request))
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    # ═══════════════════════════════════════════════════════════════════
    # O-08 — 온보딩 관제
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/ops/onboarding", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-08 온보딩 관제 — U0 전용")
    def ops_onboarding_board(self, request):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.onboarding_board(actor=_actor(request))
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    # ═══════════════════════════════════════════════════════════════════
    # O-09 — 감사(플랫폼)
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/ops/audit", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-09 운영자 행위 전건 — U0 전용")
    def ops_audit_log(self, request, limit: int = 200):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.platform_audit_log(actor=_actor(request), limit=limit)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    @route.post("/ops/audit/access-requests", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-09 테넌트 열람 요청 — U0 전용")
    def ops_audit_request_access(self, request, tenant_code: str, reason: str):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.request_tenant_access(actor=_actor(request), tenant_code=tenant_code,
                                             reason=reason)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    @route.post("/ops/audit/access-requests/{request_id}/approve", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-09 테넌트 열람 승인 — U0 전용")
    def ops_audit_approve_access(self, request, request_id: str):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.approve_tenant_access(actor=_actor(request), request_id=request_id)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    # ═══════════════════════════════════════════════════════════════════
    # O-10 — 키·자격 회전 (k5_trust 재사용 · 라이브 로그인 반쪽은 회색)
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/ops/keys", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-10 키 회전 보드 — U0 전용")
    def ops_keys_board(self, request):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.key_rotation_board(actor=_actor(request))
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    @route.post("/ops/keys/rotate", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-10 키 회전 — k5_trust.inbound_keys.rotate_key 재사용")
    def ops_keys_rotate(self, request, tenant_code: str, key_id: int):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.rotate_api_key(actor=_actor(request), tenant_code=tenant_code,
                                      key_id=key_id)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    # ═══════════════════════════════════════════════════════════════════
    # O-11 — 릴리스·배포
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/ops/releases", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-11 배포 보드 — U0 전용")
    def ops_releases_board(self, request):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.release_board(actor=_actor(request))
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    # ═══════════════════════════════════════════════════════════════════
    # O-12 — 시드·훈련 데이터
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/ops/seed", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-12 시드 보드 — U0 전용")
    def ops_seed_board(self, request):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.seed_board(actor=_actor(request))
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)

    @route.post("/ops/seed/toggle", auth=JwtOrInboundKey())
    @tenant_scoped(reason="O-12 시드 심기·숨기기·시나리오 배포 — U0 전용")
    def ops_seed_toggle(self, request, tenant_code: str, action: str, scenario_code: str = "",
                        note: str = ""):
        from apps.dsm import ops_an_service as svc

        try:
            return svc.toggle_seed(actor=_actor(request), tenant_code=tenant_code, action=action,
                                   scenario_code=scenario_code, note=note)
        except Exception as exc:  # noqa: BLE001
            raise _translate(exc)
