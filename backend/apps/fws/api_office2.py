# -*- coding: utf-8 -*-
"""FWS F3 산림과 담당 — 대피·보고·통계·오탐률·단속·훈련·온보딩(F3-11~20).

턴 AN · WO-17 · 차선 N3 단독 소유 파일(조율자가 빈 컨트롤러로 세워 `urls.py` 에 등록해 둠).
`api.py` 는 이 턴에 아무 차선도 고치지 않는다 — 문은 전부 이 파일에 더한다.
★ `from __future__ import annotations` 를 쓰지 않는다(D-378 · `api.py` 머리말과 같은 까닭).

경로는 전부 `/office2/...` 로 좁힌다 — 같은 턴 차선 N2 가 `api_office.py`(F3-01~09)
에서 `/fws/...` 최상위 가지를 쓰는 중이고, 그 파일 이름을 이 차선이 추측해 겹치지
않게 하기보다 **애초에 겹칠 수 없는 접두어**를 쓴다(P-VOID — 남의 차선 파일을
고치지 않는다 원칙의 연장).

값이 복합(목록)이면 JSON 문자열로 받는다 — `apps/fws/drone.py::submit_hotspots`
와 같은 규약(django-ninja 라우트는 원시 인자를 질의로만 받는다)이다.
"""
import json

from django.http import Http404
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.idempotency import idempotent
from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import SystemScopeCannotRead, TenantScope, tenant_scoped

from apps.fws import office2


def _scope(request) -> TenantScope:
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


def _parse_villages(raw: str) -> list:
    raw = (raw or "").strip()
    if not raw:
        raise office2.Office2InputRejected("villages_json 이 비었다")
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise office2.Office2InputRejected("villages_json 이 올바른 JSON 이 아니다") from exc
    if not isinstance(parsed, list):
        raise office2.Office2InputRejected("villages_json 은 배열이어야 한다")
    return parsed


@api_controller("/office2", tags=["FWS — 산림과 F3 잔여 (턴 AN · N3)"])
class FwsOffice2API:
    # ── FWS-F3-11 대피 초안 ──────────────────────────────────────────────
    @route.post("/evacuations/{int:event_id}/plan", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 대피 계획을 남길 수 없다")
    @idempotent("fws.office2.evac_plan")
    def draft_evacuation_plan(self, request, event_id: int, villages_json: str,
                             kind: str = "order", note: str = ""):
        try:
            villages = _parse_villages(villages_json)
            return office2.draft_evacuation_plan(
                scope=_scope(request), event_id=event_id, villages=villages,
                kind=kind, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except office2.Office2InputRejected as exc:
            raise HttpError(422, str(exc))

    # ── FWS-F3-12 대피 이행 확인 ─────────────────────────────────────────
    @route.post("/evacuations/{int:event_id}/progress", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 대피 이행을 기록할 수 없다")
    @idempotent("fws.office2.evac_progress")
    def record_evacuation_progress(self, request, event_id: int, village: str,
                                  completed: bool,
                                  remaining_residents: int = 0,
                                  care_facility_cleared: bool | None = None,
                                  note: str = ""):
        try:
            return office2.record_evacuation_progress(
                scope=_scope(request), event_id=event_id, village=village,
                completed=completed, remaining_residents=remaining_residents,
                care_facility_cleared=care_facility_cleared, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except office2.Office2InputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/evacuations/{int:event_id}/status", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 대피 이행 %를 읽을 수 없다")
    def evacuation_status(self, request, event_id: int):
        try:
            return office2.evacuation_status(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F3-13 매시간 상황보고 초안 ───────────────────────────────────
    @route.post("/reports/{int:event_id}/hourly", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 상황보고를 남길 수 없다")
    @idempotent("fws.office2.hourly_report")
    def draft_hourly_report(self, request, event_id: int,
                           personnel_count: int | None = None,
                           equipment_note: str = "",
                           casualties_count: int | None = None,
                           facility_note: str = "", weather_note: str = ""):
        try:
            return office2.draft_hourly_report(
                scope=_scope(request), event_id=event_id,
                personnel_count=personnel_count, equipment_note=equipment_note,
                casualties_count=casualties_count, facility_note=facility_note,
                weather_note=weather_note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except office2.Office2InputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/reports/{int:event_id}/hourly", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 상황보고를 읽을 수 없다")
    def hourly_reports(self, request, event_id: int):
        try:
            return office2.hourly_reports(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F3-14 진화완료 보고·산불 통계 항목 ──────────────────────────
    @route.post("/reports/{int:event_id}/final", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 진화완료 보고를 남길 수 없다")
    @idempotent("fws.office2.final_report")
    def record_final_report(self, request, event_id: int, cause: str,
                           area_ha: float, sms_sent: bool, sunrise: str = "",
                           sunset: str = "", fire_info_id: str = ""):
        try:
            return office2.record_final_report(
                scope=_scope(request), event_id=event_id, cause=cause,
                area_ha=area_ha, sms_sent=sms_sent, sunrise=sunrise,
                sunset=sunset, fire_info_id=fire_info_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except office2.Office2InputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/reports/{int:event_id}/final", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 진화완료 보고를 읽을 수 없다")
    def final_report(self, request, event_id: int):
        try:
            return office2.final_report(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F3-16 통계 ───────────────────────────────────────────────────
    @route.get("/stats/fires", auth=JwtOrInboundKey())
    @tenant_scoped(reason="통계는 내 테넌트 사건만 모은다 — K1 이 이미 좁힌다")
    def fire_stats(self, request, since: str = "", until: str = ""):
        return office2.fire_stats(scope=_scope(request), since=since, until=until)

    # ── FWS-F3-17 카메라별 오탐률·임계값 시험 ───────────────────────────
    @route.get("/stats/camera-false-alarms", auth=JwtOrInboundKey())
    @tenant_scoped(reason="카메라별 오탐률은 내 테넌트 카메라만 모은다")
    def camera_false_alarm_rates(self, request, since: str = "", until: str = ""):
        return office2.camera_false_alarm_rates(
            scope=_scope(request), since=since, until=until)

    @route.post("/stats/camera-false-alarms/threshold-test", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 카메라의 임계값을 시험할 수 없다 — 통계가 "
                        "테넌트로 이미 좁혀 있어 남의 카메라는 애초에 안 잡힌다")
    @idempotent("fws.office2.camera_threshold_test")
    def run_camera_threshold_test(self, request, stream_monitor_id: int,
                                 threshold_pct: float, since: str = "",
                                 until: str = ""):
        try:
            return office2.run_camera_threshold_test(
                scope=_scope(request), stream_monitor_id=stream_monitor_id,
                threshold_pct=threshold_pct, since=since, until=until)
        except office2.Office2InputRejected as exc:
            raise HttpError(422, str(exc))

    # ── FWS-F3-18 계도·단속 통계 · 입산통제구역 관리 ────────────────────
    @route.post("/patrol/enforcement", auth=JwtOrInboundKey())
    @tenant_scoped(reason="계도·단속 기록은 이 테넌트에 남긴다(곁표 audit_scope · P-411)")
    @idempotent("fws.office2.patrol_enforcement")
    def record_patrol_enforcement(self, request, kind: str, location: str = "",
                                 note: str = ""):
        try:
            return office2.record_patrol_enforcement(
                scope=_scope(request), kind=kind, location=location, note=note)
        except office2.Office2InputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/patrol/enforcement/mine", auth=JwtOrInboundKey())
    @tenant_scoped(reason="이 테넌트의 계도·단속 실적을 읽는다(곁표 audit_scope · 다른 테넌트 0 · 경로 이름 /mine 은 라우트 대장 때문에 그대로)")
    def patrol_enforcement_stats(self, request):
        return office2.patrol_enforcement_stats(scope=_scope(request))

    @route.post("/entry-control-zones", auth=JwtOrInboundKey())
    @tenant_scoped(reason="입산통제구역 설정은 이 테넌트에 남긴다(곁표 audit_scope · P-411)")
    @idempotent("fws.office2.entry_control_zone")
    def set_entry_control_zone(self, request, zone_name: str, status: str):
        try:
            return office2.set_entry_control_zone(
                scope=_scope(request), zone_name=zone_name, status=status)
        except office2.Office2InputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/entry-control-zones", auth=JwtOrInboundKey())
    @tenant_scoped(reason="이 테넌트가 설정한 구역을 읽는다(곁표 audit_scope · 다른 테넌트 0)")
    def entry_control_zones(self, request):
        return office2.entry_control_zones(scope=_scope(request))

    # ── FWS-F3-19 훈련 시나리오 실행 ─────────────────────────────────────
    @route.post("/drill/start", auth=JwtOrInboundKey())
    @tenant_scoped(reason="훈련 스위치는 이 테넌트 것만 켠다(DSM 훈련 스위치 재사용)")
    def start_drill_scenario(self, request, reason: str):
        try:
            return office2.start_drill_scenario(scope=_scope(request), reason=reason)
        except office2.Office2InputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/drill/status", auth=JwtOrInboundKey())
    @tenant_scoped(reason="훈련 상태는 이 테넌트 것만 읽는다")
    def drill_scenario_status(self, request):
        return office2.drill_scenario_status(scope=_scope(request))

    @route.post("/drill/end", auth=JwtOrInboundKey())
    @tenant_scoped(reason="훈련 종료·보고서는 이 테넌트 것만 낸다")
    def end_drill_scenario(self, request, reason: str = ""):
        return office2.end_drill_scenario(scope=_scope(request), reason=reason)

    # ── FWS-F3-20 온보딩 카드 7 ──────────────────────────────────────────
    @route.get("/onboarding/progress", auth=JwtOrInboundKey())
    @tenant_scoped(reason="내 온보딩 진행률만 읽는다")
    def f3_onboarding_progress(self, request):
        return office2.f3_onboarding_progress(scope=_scope(request))
