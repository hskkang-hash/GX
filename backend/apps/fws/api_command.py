# -*- coding: utf-8 -*-
"""FWS F4 통합지휘본부장 (FWS-F4-01~15 · 명세 제목이 정본).

턴 AO · WO-18 · 차선 N2 단독 소유 파일(조율자가 빈 컨트롤러로 세워 `urls.py` 에
등록해 둠). 경로는 전부 `/command/...` 로 좁힌다 — 같은 턴 다른 차선·앞선 턴의
`/office`·`/office2`·`/admin` 최상위 가지와 겹치지 않게(`api_office2.py` 머리말과
같은 판단 — 애초에 겹칠 수 없는 접두어).
★ `from __future__ import annotations` 를 쓰지 않는다(D-378).
"""
from django.http import Http404, HttpResponse
from ninja.errors import HttpError
from ninja_extra import api_controller, route  # noqa: F401

from common.idempotency import idempotent
from common.inbound_api_key import JwtOrInboundKey  # noqa: F401
from common.tenant_scope import SystemScopeCannotRead, TenantScope, tenant_scoped  # noqa: F401

from apps.dsm.services import IncidentReportUnavailable, SettingNotAvailable

from apps.fws import command


def _scope(request) -> TenantScope:
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


@api_controller("/command", tags=["FWS — 지휘 F4 (턴 AO · N2)"])
class FwsCommandAPI:
    # ── FWS-F4-02 대응단계 확정·상향 · 지휘권 이양 ──────────────────────
    @route.post("/incidents/{int:event_id}/stage", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 대응단계를 확정할 수 없다")
    @idempotent("fws.command.stage_confirm")
    def confirm_stage(self, request, event_id: int, stage: str, reason: str,
                      command_level: str = ""):
        try:
            return command.confirm_stage(
                scope=_scope(request), event_id=event_id, stage=stage,
                reason=reason, command_level=command_level)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except command.CommandInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/incidents/{int:event_id}/stage", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 단계 이력을 읽을 수 없다")
    def stage_history(self, request, event_id: int):
        try:
            return command.stage_history(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F4-03 통합지휘본부 설치 선언 ────────────────────────────────
    @route.post("/incidents/{int:event_id}/command-post", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 지휘본부를 설치 선언할 수 없다")
    @idempotent("fws.command.command_post")
    def declare_command_post(self, request, event_id: int, address: str,
                             org_composition: str = "",
                             situation_room_phone: str = "", note: str = ""):
        try:
            return command.declare_command_post(
                scope=_scope(request), event_id=event_id, address=address,
                org_composition=org_composition,
                situation_room_phone=situation_room_phone, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except command.CommandInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/incidents/{int:event_id}/command-post", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 지휘본부 선언을 읽을 수 없다")
    def command_post(self, request, event_id: int):
        try:
            return command.command_post(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F4-04 헬기 요청 승인·투하구역 지정 ───────────────────────────
    @route.post("/incidents/{int:event_id}/aircraft-request", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 헬기 요청을 승인할 수 없다")
    @idempotent("fws.command.aircraft_request")
    def approve_helicopter_request(self, request, event_id: int, requesting_org: str,
                                   drop_zone_lat: float, drop_zone_lng: float,
                                   base: str = "", eta: str = "", note: str = ""):
        try:
            return command.approve_helicopter_request(
                scope=_scope(request), event_id=event_id, requesting_org=requesting_org,
                drop_zone_lat=drop_zone_lat, drop_zone_lng=drop_zone_lng,
                base=base, eta=eta, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except command.CommandInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/incidents/{int:event_id}/aircraft-request", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 헬기 승인을 읽을 수 없다")
    def helicopter_status(self, request, event_id: int):
        try:
            return command.helicopter_status(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F4-05 대피 명령 승인(즉시/준비)·해제 ─────────────────────────
    @route.post("/evacuations/{int:event_id}/approve", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 대피 명령을 승인할 수 없다")
    @idempotent("fws.command.evac_approve")
    def approve_evacuation(self, request, event_id: int, urgency: str, note: str = ""):
        try:
            return command.approve_evacuation(
                scope=_scope(request), event_id=event_id, urgency=urgency, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except command.CommandInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.post("/evacuations/{int:event_id}/release", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 대피를 해제할 수 없다")
    @idempotent("fws.command.evac_release")
    def release_evacuation(self, request, event_id: int, reason: str):
        try:
            return command.release_evacuation(
                scope=_scope(request), event_id=event_id, reason=reason)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except command.CommandInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/evacuations/{int:event_id}/command-status", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 대피 승인 현황을 읽을 수 없다")
    def evacuation_command_status(self, request, event_id: int):
        try:
            return command.evacuation_command_status(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F4-06 소방·경찰·군 협조 요청 기록 ────────────────────────────
    @route.post("/incidents/{int:event_id}/agency-request", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 협조 요청을 남길 수 없다")
    @idempotent("fws.command.agency_request")
    def record_agency_coordination(self, request, event_id: int, agency: str,
                                   request_detail: str = "", note: str = ""):
        try:
            return command.record_agency_coordination(
                scope=_scope(request), event_id=event_id, agency=agency,
                request_detail=request_detail, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except command.CommandInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/incidents/{int:event_id}/agency-request", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 협조 요청 기록을 읽을 수 없다")
    def agency_coordination_records(self, request, event_id: int):
        try:
            return command.agency_coordination_records(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F4-07 주불 진화 선언 · 진화완료 선언 ─────────────────────────
    @route.post("/incidents/{int:event_id}/main-fire-out", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 주불 진화를 선언할 수 없다")
    @idempotent("fws.command.main_fire_out")
    def declare_main_fire_out(self, request, event_id: int, note: str = ""):
        try:
            return command.declare_main_fire_out(
                scope=_scope(request), event_id=event_id, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    @route.post("/incidents/{int:event_id}/extinguished", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 진화완료를 선언할 수 없다")
    @idempotent("fws.command.extinguished")
    def declare_extinguished(self, request, event_id: int, reason: str = ""):
        try:
            return command.declare_extinguished(
                scope=_scope(request), event_id=event_id, reason=reason)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except command.CommandInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/incidents/{int:event_id}/fire-declarations", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 진화 선언 기록을 읽을 수 없다")
    def fire_declarations(self, request, event_id: int):
        try:
            return command.fire_declarations(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F4-08 상황보고 승인(매시간) ──────────────────────────────────
    @route.post("/incidents/{int:event_id}/hourly-report/approve", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 상황보고를 승인할 수 없다")
    @idempotent("fws.command.hourly_approve")
    def approve_hourly_report(self, request, event_id: int, hour: str = "", note: str = ""):
        try:
            return command.approve_hourly_report(
                scope=_scope(request), event_id=event_id, hour=hour, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except command.CommandInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/incidents/{int:event_id}/hourly-report/approve", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 상황보고 승인 기록을 읽을 수 없다")
    def hourly_approvals(self, request, event_id: int):
        try:
            return command.hourly_approvals(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F4-09 산림청·시도 상황실 연락(1클릭) ─────────────────────────
    @route.get("/incidents/{int:event_id}/contacts", auth=JwtOrInboundKey())
    @tenant_scoped(reason="사건 문지기를 지나야 지휘소가 등록한 상황실 번호를 읽는다")
    def contact_directory(self, request, event_id: int):
        try:
            return command.contact_directory(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F4-10 대응 시계 ───────────────────────────────────────────────
    @route.get("/incidents/{int:event_id}/response-timeline", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 대응 시계를 읽을 수 없다")
    def response_timeline(self, request, event_id: int):
        try:
            return command.response_timeline(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except SettingNotAvailable as exc:
            raise HttpError(409, str(exc))

    @route.post("/incidents/{int:event_id}/golden-time-reason", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 골든타임 초과 사유를 남길 수 없다")
    @idempotent("fws.command.golden_time_reason")
    def record_golden_time_exceeded_reason(self, request, event_id: int, reason: str):
        try:
            return command.record_golden_time_exceeded_reason(
                scope=_scope(request), event_id=event_id, reason=reason)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except command.CommandInputRejected as exc:
            raise HttpError(422, str(exc))

    # ── FWS-F4-11 야간 전환(일몰) ─────────────────────────────────────────
    @route.post("/incidents/{int:event_id}/sunset", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 일몰 시각을 기록할 수 없다")
    @idempotent("fws.command.sunset")
    def set_sunset(self, request, event_id: int, sunset_at: str):
        try:
            return command.set_sunset(
                scope=_scope(request), event_id=event_id, sunset_at=sunset_at)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except command.CommandInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/incidents/{int:event_id}/night-status", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 야간 전환 상태를 읽을 수 없다")
    def night_status(self, request, event_id: int):
        try:
            return command.night_status(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F4-12 상황판단회의 기록(DSM-U2-03 재사용) ────────────────────
    @route.post("/incidents/{int:event_id}/meetings", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 회의 기록을 남길 수 없다")
    @idempotent("fws.command.meeting")
    def record_situation_meeting(self, request, event_id: int, decision: str,
                                 occurred_at: str = "", attendees: str = "",
                                 basis: str = ""):
        try:
            return command.record_situation_meeting(
                scope=_scope(request), event_id=event_id, occurred_at=occurred_at,
                attendees=attendees, decision=decision, basis=basis)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except command.CommandInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/incidents/{int:event_id}/meetings", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 회의 기록을 읽을 수 없다")
    def situation_meetings(self, request, event_id: int):
        try:
            return command.situation_meetings(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F4-13 동시 다발 사건 우선순위(위험도 정렬) ──────────────────
    @route.get("/incidents", auth=JwtOrInboundKey())
    @tenant_scoped(reason="우선순위 큐는 내 테넌트 사건만 모은다 — K1 이 이미 좁힌다")
    def priority_queue(self, request, sort: str = "risk", limit: int = 50):
        return command.priority_queue(scope=_scope(request), limit=limit)

    # ── FWS-F4-15 사후 보고서 1쪽 ─────────────────────────────────────────
    @route.get("/incidents/{int:event_id}/post-report.pdf", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 사건의 사후 보고서가 종이로 나가면 IDOR 이다")
    def post_incident_report_pdf(self, request, event_id: int):
        try:
            pdf = command.post_incident_report_pdf(scope=_scope(request), event_id=event_id)
        except Http404 as exc:
            raise HttpError(404, str(exc) or "그런 사건이 없습니다.")
        except (IncidentReportUnavailable, SettingNotAvailable) as exc:
            raise HttpError(409, f"지금은 보고서를 만들 수 없습니다 — {exc}")
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="guardianx-fws-command-{event_id}.pdf"')
        return response

    @route.get("/incidents/{int:event_id}/post-report/summary", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 사후 보고 요약을 읽을 수 없다")
    def post_incident_summary(self, request, event_id: int):
        try:
            return command.post_incident_summary(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except SettingNotAvailable as exc:
            raise HttpError(409, str(exc))

    # ── FWS-F4-01 지휘 화면 ──────────────────────────────────────────────
    @route.get("/incidents/{int:event_id}/command", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 지휘 화면을 읽을 수 없다")
    def command_screen(self, request, event_id: int):
        try:
            return command.command_screen(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except SettingNotAvailable as exc:
            raise HttpError(409, str(exc))
