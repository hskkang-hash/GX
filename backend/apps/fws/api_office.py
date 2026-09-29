# -*- coding: utf-8 -*-
"""FWS F3 산림과 담당 — 상황판·기간·인력·확인·접수·통보·자원·단계(F3-01~09).

턴 AN · WO-17 · 차선 N2 단독 소유 파일(조율자가 빈 컨트롤러로 세워 `urls.py` 에 등록해 둠).
`api.py` 는 이 턴에 아무 차선도 고치지 않는다 — 문은 전부 이 파일에 더한다.
★ `from __future__ import annotations` 를 쓰지 않는다(D-378 · `api.py` 머리말과 같은 까닭).

이 파일은 **얇다** — 스코프를 만들고 `apps/fws/office.py` 를 부르고, 그 예외를
HTTP 상태로 옮기는 것뿐이다(`apps/fws/api.py` 머리말과 같은 규율). F3-05(오인
종결·산불 확정)는 새 라우트가 없다 — `office.py` 머리말 참조(P-397 재사용,
기존 `/api/fws/verifications/{id}/reply` 를 그대로 쓴다).
"""
from django.http import Http404
from ninja.errors import HttpError
from ninja_extra import api_controller, route  # noqa: F401

from common.idempotency import idempotent
from common.inbound_api_key import JwtOrInboundKey  # noqa: F401
from common.tenant_scope import SystemScopeCannotRead, TenantScope, tenant_scoped  # noqa: F401

from apps.fws import office


def _scope(request) -> TenantScope:
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)



@api_controller("", tags=["FWS — 산림과 F3 (턴 AN · N2)"])
class FwsOfficeAPI:
    # ── FWS-F3-01 산불 상황판(위험지수·위기경보·초소 근무·카메라 정상·진행
    #    사건·자원 대기 — 띠 6수) ──────────────────────────────────────────
    @route.get("/office/dashboard", auth=JwtOrInboundKey())
    @tenant_scoped(reason="상황판은 이 테넌트 자원·사건만 본다")
    def office_dashboard(self, request):
        return office.dashboard(scope=_scope(request))

    # ── FWS-F3-02 조심기간·특별대책기간 설정 ────────────────────────────
    @route.post("/office/season", auth=JwtOrInboundKey())
    @tenant_scoped(reason="기간 설정은 이 테넌트의 산림과 담당만 한다")
    @idempotent("fws.office.season.set")
    def office_set_season(self, request, kind: str, start_date: str,
                          end_date: str, note: str = ""):
        try:
            return office.set_season(scope=_scope(request), kind=kind,
                                     start_date=start_date, end_date=end_date,
                                     note=note)
        except office.OfficeInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/office/season", auth=JwtOrInboundKey())
    @tenant_scoped(reason="지금 설정된 기간을 본다 — 이 테넌트 것만")
    def office_current_seasons(self, request):
        return office.current_seasons(scope=_scope(request))

    # ── FWS-F3-02 초소·순찰 구역 등록 ────────────────────────────────────
    @route.post("/office/posts", auth=JwtOrInboundKey())
    @tenant_scoped(reason="초소·구역 등록은 이 테넌트의 산림과 담당만 한다")
    @idempotent("fws.office.posts.register")
    def office_register_post(self, request, kind: str, code: str, name: str = "",
                             lat: float | None = None, lng: float | None = None,
                             note: str = ""):
        try:
            return office.register_post(scope=_scope(request), kind=kind, code=code,
                                        name=name, lat=lat, lng=lng, note=note)
        except office.OfficeInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/office/posts", auth=JwtOrInboundKey())
    @tenant_scoped(reason="등록된 초소·구역을 본다 — 이 테넌트 것만")
    def office_registered_posts(self, request, kind: str = ""):
        return office.registered_posts(scope=_scope(request), kind=kind)

    # ── FWS-F3-03 인력 배치 — 근무표(CSV) · 야간 5분대기조 ──────────────
    @route.post("/office/roster", auth=JwtOrInboundKey())
    @tenant_scoped(reason="근무표 업로드는 이 테넌트의 산림과 담당만 한다")
    @idempotent("fws.office.roster.upload")
    def office_upload_roster(self, request, csv_text: str):
        try:
            return office.upload_roster(scope=_scope(request), csv_text=csv_text)
        except office.OfficeInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/office/roster", auth=JwtOrInboundKey())
    @tenant_scoped(reason="배치판 — 이 테넌트 근무표만 본다")
    def office_current_roster(self, request):
        return office.current_roster(scope=_scope(request))

    # ── FWS-F3-04 탐지 확인 요청 1클릭 · 10분 시계 ──────────────────────
    @route.post("/office/fire-events/{int:event_id}/verification-request",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 확인 요청을 낼 수 없다")
    @idempotent("fws.office.verification_request")
    def office_request_verification(self, request, event_id: int, note: str = ""):
        try:
            return office.request_verification(
                scope=_scope(request), event_id=event_id, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except office.OfficeInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/office/fire-events/{int:event_id}/verification-request",
              auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 확인 요청 기록을 읽을 수 없다")
    def office_verification_requests(self, request, event_id: int):
        try:
            return office.verification_requests(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F3-06 신고 접수 기록(119/산림청/시민 · 30분 시계 시작) ──────
    @route.post("/office/fire-events/{int:event_id}/intake", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 신고 접수를 남길 수 없다")
    @idempotent("fws.office.intake")
    def office_record_intake(self, request, event_id: int, source: str,
                             reported_at: str = "", facility_note: str = "",
                             vehicle_access: bool | None = None,
                             fire_intensity: str = "", note: str = ""):
        try:
            return office.record_intake(
                scope=_scope(request), event_id=event_id, source=source,
                reported_at=reported_at, facility_note=facility_note,
                vehicle_access=vehicle_access, fire_intensity=fire_intensity,
                note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except office.OfficeInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/office/fire-events/{int:event_id}/intake", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 신고 접수 기록을 읽을 수 없다")
    def office_intake_records(self, request, event_id: int):
        try:
            return office.intake_records(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F3-07 산림청 상황실 통보(042-481-4119) · 헬기 요청 기록 ─────
    @route.post("/office/fire-events/{int:event_id}/agency-notify",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건으로 산림청 통보를 남길 수 없다")
    @idempotent("fws.office.agency_notify")
    def office_notify_forest_agency(self, request, event_id: int,
                                    helicopter_base: str = "",
                                    helicopter_eta: str = "", note: str = ""):
        try:
            return office.notify_forest_agency(
                scope=_scope(request), event_id=event_id,
                helicopter_base=helicopter_base, helicopter_eta=helicopter_eta,
                note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except office.OfficeInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/office/fire-events/{int:event_id}/agency-notify",
              auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 통보 기록을 읽을 수 없다")
    def office_agency_notifications(self, request, event_id: int):
        try:
            return office.agency_notifications(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F3-08 자원 배정(진화대·차량·드론 · 임무 문안 자동) ──────────
    @route.post("/office/fire-events/{int:event_id}/resource-assignment",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 자원을 배정할 수 없다")
    @idempotent("fws.office.resource_assignment")
    def office_assign_resource(self, request, event_id: int, kind: str,
                               resource_name: str, note: str = ""):
        try:
            return office.assign_resource(
                scope=_scope(request), event_id=event_id, kind=kind,
                resource_name=resource_name, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except office.OfficeInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/office/fire-events/{int:event_id}/resource-assignment",
              auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 자원 배정을 읽을 수 없다")
    def office_resource_assignments(self, request, event_id: int):
        try:
            return office.resource_assignments(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F3-09 대응단계 입력 3칸 → 단계 제안 → F4 확정 요청 ──────────
    @route.post("/office/fire-events/{int:event_id}/stage-proposal",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 단계 제안을 낼 수 없다")
    @idempotent("fws.office.stage_proposal")
    def office_propose_stage(self, request, event_id: int, area_ha: float,
                             wind_mps: float, buildings_at_risk: int = 0,
                             note: str = ""):
        try:
            return office.propose_stage(
                scope=_scope(request), event_id=event_id, area_ha=area_ha,
                wind_mps=wind_mps, buildings_at_risk=buildings_at_risk, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except office.OfficeInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/office/fire-events/{int:event_id}/stage-proposal",
              auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 단계 제안을 읽을 수 없다")
    def office_stage_proposals(self, request, event_id: int):
        try:
            return office.stage_proposals(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
