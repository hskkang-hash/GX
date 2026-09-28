# -*- coding: utf-8 -*-
"""FWS App(L4)의 유일한 문 — **얇다**: 여기서 하는 일은 스코프를 만들고, 아래
기능 모듈(`patrol` · `risk` · `verification` · `alerts` · `notify_prefs` · `contacts` ·
`standby` · `training` · `equipment` · `missions` · `drone`)을 부르고, 그 예외를
HTTP 상태로 옮기는 것뿐이다. 판정·저장은 전부 그 모듈들과 그 모듈들이 부르는
커널(K1·K2)에 있다 — `tests/test_fws_app.py::AppStaysThinTest` 가 이 파일이 모델을
직접 만지지 않는지를 잰다(턴 AL 이 더한 `standby`·`equipment`·`missions`, 턴 AM 이
더한 `drone` 도 같은 자리 — 감사 로그 전건을 직접 읽고 쓴다, `patrol`·
`notify_prefs` 와 같은 이유로 이 시험이 보지 않는다).

P-357 — FWS 는 새 앱이 아니다
------------------------------
프런트는 같은 SPA 의 `/fws/*` 라우트를 쓰고, 이 App 은 그 화면들의 서버 쪽 짝이다.
DSM 커널(K1 이벤트·K2 알림)을 공유한다 — 새 이벤트·발송 표를 만들지 않는다.


★ `from __future__ import annotations` 를 **쓰지 않는다** (D-378 · `apps/dsm/
law_api.py` 머리말과 같은 이유) — 미래 임포트가 켜지면 타입 주석이 문자열이
되고, `@tenant_scoped` 로 감싸인 핸들러의 `__globals__` 에서 그 문자열이 안
풀려 라우트가 500 으로 죽는다. 단위 시험은 그것을 못 잡는다.
"""

from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.idempotency import idempotent
from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import SystemScopeCannotRead, TenantScope, tenant_scoped

from apps.fws import (alerts, contacts, drone, equipment, integration,
                      missions, notify_prefs, patrol, risk, standby, training,
                      verification)


def _scope(request) -> TenantScope:
    """`apps/dsm/api_u1.py::_scope` 와 같은 세 줄 — 공용부(조율자 소유)를 이 턴에
    건드리지 않기 위해 그대로 옮겨 둔다."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


@api_controller("", tags=["FWS — 산불감시 (WO-15 §5 P-357 · 차선 N2)"])
class FwsAPI:
    # ── FWS-F1-01 근무 시작·초소 체크인 ─────────────────────────────────
    @route.post("/patrol/checkin", auth=JwtOrInboundKey())
    @tenant_scoped(reason="체크인은 이 사람의 근무 기록이다 — 남의 초소 상태를 "
                         "대신 켤 수 없다")
    @idempotent("fws.patrol.checkin")
    def patrol_checkin(self, request, post_code: str, method: str = "gps",
                      lat: float | None = None, lng: float | None = None):
        try:
            return patrol.checkin(scope=_scope(request), post_code=post_code,
                                  method=method, lat=lat, lng=lng)
        except patrol.PatrolInputRejected as exc:
            raise HttpError(422, str(exc))

    # ── FWS-F1-02 순찰 경로 기록 ─────────────────────────────────────────
    @route.post("/patrol/track", auth=JwtOrInboundKey())
    @tenant_scoped(reason="트랙은 이 사람의 순찰 기록이다")
    @idempotent("fws.patrol.track")
    def patrol_track(self, request, post_code: str, lat: float | None = None,
                     lng: float | None = None, checkpoint_code: str = ""):
        try:
            return patrol.track(scope=_scope(request), post_code=post_code,
                                lat=lat, lng=lng, checkpoint_code=checkpoint_code)
        except patrol.PatrolInputRejected as exc:
            raise HttpError(422, str(exc))

    # ── FWS-F1-11 내 근무 기록·순찰 실적 ─────────────────────────────────
    @route.get("/patrol/mine", auth=JwtOrInboundKey())
    @tenant_scoped(reason="내 실적 — 본인 것만")
    def patrol_mine(self, request):
        return patrol.mine(scope=_scope(request))

    # ── FWS-F1-03 오늘 위험지수·위기경보·입산통제 ────────────────────────
    @route.get("/risk/today", auth=JwtOrInboundKey())
    @tenant_scoped(reason="오늘 위험지수는 테넌트 자료가 아니다(전국 공개 지수) — 만지는 테넌트 모델 0 · 선언만(ISO-03)")
    def risk(self, request):
        _scope(request)  # 인증만 확인 — 값은 테넌트 무관 공용 정보다
        return risk.risk_today()

    # ── FWS-F1-08 119·산림청 신고 번호 ──────────────────────────────────
    @route.get("/emergency-contacts", auth=JwtOrInboundKey())
    @tenant_scoped(reason="신고 번호는 테넌트 자료가 아니다(119 · 산림청) — 만지는 테넌트 모델 0 · 선언만(ISO-03)")
    def emergency_contacts(self, request):
        # ★ [턴 AK · 조율자 병합] 차선은 익명으로 열었다(번호는 비밀이 아니다). 그러나 익명 표면은
        #   래칫(open_anonymous 73)이 지키는 자리이고 넓히는 것은 판정이 필요한 일이다 — 기본값은
        #   닫힌 쪽. 이 번호를 쓰는 화면(`/fws/home`)은 로그인 뒤에만 열리므로 닫아도 1탭은 그대로다.
        #   익명 공개가 필요하면(예: 로그인 전 화면) 세종 판정 뒤 `auth=None` 한 줄 + 래칫 기준선 +1.
        return contacts.emergency_contacts()

    # ── FWS-F1-05 확인 요청 수신 ─────────────────────────────────────────
    @route.get("/verifications/{int:verification_id}", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 이벤트를 확인 요청으로 읽을 수 없다")
    def get_verification(self, request, verification_id: int):
        from django.http import Http404
        try:
            return verification.get_verification(
                scope=_scope(request), verification_id=verification_id)
        except Http404:
            raise HttpError(404, "그런 확인 요청이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F1-06 현장 확인 회신 ─────────────────────────────────────────
    @route.post("/verifications/{int:verification_id}/reply", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 이벤트에 회신·판정을 쓸 수 없다")
    @idempotent("fws.verifications.reply")
    def reply_verification(self, request, verification_id: int, result: str,
                           reason_code: str = "", note: str = ""):
        from django.http import Http404
        try:
            return verification.reply_verification(
                scope=_scope(request), verification_id=verification_id,
                result=result, reason_code=reason_code, note=note)
        except Http404:
            raise HttpError(404, "그런 확인 요청이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except verification.VerificationReplyRejected as exc:
            raise HttpError(422, str(exc))

    # ── FWS-F1-10 안전 알림 수신(도달·확인) ──────────────────────────────
    @route.get("/alerts", auth=JwtOrInboundKey())
    @tenant_scoped(reason="내 앞으로 온 발송만")
    def my_alerts(self, request):
        return {"alerts": alerts.my_alerts(scope=_scope(request))}

    @route.post("/alerts/{int:delivery_id}/ack", auth=JwtOrInboundKey())
    @tenant_scoped(reason="내 목록에 있는 알림만 확인할 수 있다")
    @idempotent("fws.alerts.ack")
    def ack_alert(self, request, delivery_id: int):
        try:
            return alerts.ack_alert(scope=_scope(request), delivery_id=delivery_id)
        except alerts.AlertNotFound as exc:
            raise HttpError(404, str(exc))

    # ── FWS-F1-12 근무 외 알림 차단·담당 초소 설정 ───────────────────────
    @route.get("/notify-prefs", auth=JwtOrInboundKey())
    @tenant_scoped(reason="본인 설정만 읽는다")
    def get_notify_prefs(self, request):
        return notify_prefs.get_prefs(scope=_scope(request))

    @route.post("/notify-prefs", auth=JwtOrInboundKey())
    @tenant_scoped(reason="본인 설정만 쓴다")
    def save_notify_prefs(self, request, quiet_hours_start: str = "",
                          quiet_hours_end: str = "", assigned_post_code: str = ""):
        try:
            return notify_prefs.save_prefs(
                scope=_scope(request), quiet_hours_start=quiet_hours_start,
                quiet_hours_end=quiet_hours_end,
                assigned_post_code=assigned_post_code)
        except notify_prefs.NotifyPrefsRejected as exc:
            raise HttpError(422, str(exc))

    # ── FWS-F2-01 대기 상태 등록(주간·야간 5분대기조·위치) ───────────────
    @route.post("/resources/me/status", auth=JwtOrInboundKey())
    @tenant_scoped(reason="대기 상태는 이 사람의 것이다 — 남의 대기 상태를 대신 켤 수 없다")
    @idempotent("fws.resources.status")
    def set_standby_status(self, request, status: str,
                           lat: float | None = None, lng: float | None = None):
        try:
            return standby.set_status(scope=_scope(request), status=status,
                                      lat=lat, lng=lng)
        except standby.StandbyStatusRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/resources/me/status", auth=JwtOrInboundKey())
    @tenant_scoped(reason="본인 대기 상태만 읽는다")
    def get_standby_status(self, request):
        return standby.my_status(scope=_scope(request))

    # ── FWS-F2-13 훈련 임무 수신(훈련 배지) ───────────────────────────────
    @route.get("/training/mission", auth=JwtOrInboundKey())
    @tenant_scoped(reason="훈련 배지는 이 사람 테넌트의 훈련 상태를 본다 — DSM 훈련 "
                         "스위치 공개 면(apps.dsm.services)만 부른다")
    def training_mission(self, request):
        return training.training_mission_badge(scope=_scope(request))

    # ── FWS-F2-14 장비 점검 체크(등짐펌프·진화차) ─────────────────────────
    @route.post("/equipment/checks", auth=JwtOrInboundKey())
    @tenant_scoped(reason="점검 기록은 이 사람이 한 것이다")
    @idempotent("fws.equipment.check")
    def check_equipment(self, request, equipment_type: str,
                        equipment_code: str = "", result: str = "", note: str = ""):
        try:
            return equipment.check(scope=_scope(request), equipment_type=equipment_type,
                                   equipment_code=equipment_code, result=result,
                                   note=note)
        except equipment.EquipmentCheckRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/equipment/checks/mine", auth=JwtOrInboundKey())
    @tenant_scoped(reason="본인이 남긴 점검만 읽는다")
    def my_equipment_checks(self, request):
        return equipment.mine(scope=_scope(request))

    # ── FWS-F2-02 임무 수신 ────────────────────────────────────────────────
    @route.get("/missions/mine", auth=JwtOrInboundKey())
    @tenant_scoped(reason="본인 임무 이력만 읽는다")
    def my_missions(self, request):
        return missions.mine(scope=_scope(request))

    @route.get("/missions/{int:event_id}", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건을 임무로 읽을 수 없다")
    def mission_detail(self, request, event_id: int):
        from django.http import Http404
        try:
            return missions.mission_detail(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 임무가 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F2-02(출동 탭)·F2-03(도착 회신)·F2-11(철수·복귀 회신) ─────────
    @route.post("/missions/{int:event_id}/response", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 임무에 회신을 쓸 수 없다")
    @idempotent("fws.missions.response")
    def mission_response(self, request, event_id: int, action: str,
                         lat: float | None = None, lng: float | None = None,
                         note: str = ""):
        from django.http import Http404
        try:
            return missions.respond(scope=_scope(request), event_id=event_id,
                                    action=action, lat=lat, lng=lng, note=note)
        except Http404:
            raise HttpError(404, "그런 임무가 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except missions.MissionActionRejected as exc:
            raise HttpError(422, str(exc))
        except missions.MissionStateConflict as exc:
            raise HttpError(409, str(exc))

    # ── FWS-F2-05 지원 요청(인력·물·헬기·중장비) ─────────────────────────
    @route.post("/missions/{int:event_id}/field-reply", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 임무에 지원 요청을 남길 수 없다")
    @idempotent("fws.missions.field_reply")
    def mission_support_request(self, request, event_id: int, kind: str,
                                amount: str = "", note: str = ""):
        from django.http import Http404
        try:
            return missions.request_support(scope=_scope(request), event_id=event_id,
                                            kind=kind, amount=amount, note=note)
        except Http404:
            raise HttpError(404, "그런 임무가 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except missions.MissionActionRejected as exc:
            raise HttpError(422, str(exc))

    # ── FWS-F5-01 정찰 임무 수신(요청·상태) ────────────────────────────────
    @route.get("/drone/missions/mine", auth=JwtOrInboundKey())
    @tenant_scoped(reason="본인 정찰 요청 대기열만 읽는다")
    def drone_recon_mine(self, request):
        return drone.recon_mine(scope=_scope(request))

    @route.post("/drone/missions/{int:event_id}/recon", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 정찰 요청·상태를 쓸 수 없다")
    @idempotent("fws.drone.recon")
    def drone_recon(self, request, event_id: int, action: str,
                    radius_m: float | None = None, note: str = ""):
        from django.http import Http404
        try:
            return drone.recon(scope=_scope(request), event_id=event_id,
                               action=action, radius_m=radius_m, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except drone.DroneActionRejected as exc:
            raise HttpError(422, str(exc))
        except drone.DroneStateConflict as exc:
            raise HttpError(409, str(exc))

    # ── FWS-F5-02 열점·화선 표시(좌표 목록 값) ──────────────────────────────
    @route.post("/drone/missions/{int:event_id}/hotspots", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 열점·화선을 남길 수 없다")
    @idempotent("fws.drone.hotspots")
    def drone_hotspots(self, request, event_id: int, points_json: str = "",
                       fireline_json: str = "", note: str = ""):
        from django.http import Http404
        try:
            return drone.submit_hotspots(
                scope=_scope(request), event_id=event_id, points_json=points_json,
                fireline_json=fireline_json, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except drone.DroneActionRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/drone/missions/{int:event_id}/hotspots/mine", auth=JwtOrInboundKey())
    @tenant_scoped(reason="본인이 그 사건에 남긴 열점·화선만 읽는다")
    def drone_hotspots_mine(self, request, event_id: int):
        from django.http import Http404
        try:
            return drone.hotspots_mine(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F5-03 확인 회신(산불 맞음/오인 · 참조) — F1-06 문 재사용 ──────────
    @route.post("/drone/verifications/{int:event_id}/reply", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 확인 회신을 쓸 수 없다")
    @idempotent("fws.drone.verify")
    def drone_confirm_result(self, request, event_id: int, result: str,
                             reason_code: str = "", attachment_ref: str = "",
                             note: str = ""):
        from django.http import Http404
        try:
            return drone.confirm_result(
                scope=_scope(request), event_id=event_id, result=result,
                reason_code=reason_code, attachment_ref=attachment_ref, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except verification.VerificationReplyRejected as exc:
            raise HttpError(422, str(exc))

    # ── FWS-F5-08 비행 기록·배터리·기체 상태 ────────────────────────────────
    @route.post("/drone/flights", auth=JwtOrInboundKey())
    @tenant_scoped(reason="비행 기록은 이 조종사가 남긴 것이다")
    @idempotent("fws.drone.flight")
    def drone_log_flight(self, request, event_id: int | None = None,
                         source: str = "manual", airframe_code: str = "",
                         battery_pct: float | None = None,
                         flight_minutes: float | None = None, note: str = ""):
        from django.http import Http404
        try:
            return drone.log_flight(
                scope=_scope(request), event_id=event_id, source=source,
                airframe_code=airframe_code, battery_pct=battery_pct,
                flight_minutes=flight_minutes, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except drone.DroneActionRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/drone/flights/mine", auth=JwtOrInboundKey())
    @tenant_scoped(reason="본인이 남긴 비행 기록만 읽는다")
    def drone_flights_mine(self, request):
        return drone.flights_mine(scope=_scope(request))

    # ── FWS-F5-10 계량(비행 분) ──────────────────────────────────────────────
    @route.get("/drone/flights/minutes", auth=JwtOrInboundKey())
    @tenant_scoped(reason="본인 비행 분 합계만 읽는다 — 계량은 셈이지 청구가 아니다")
    def drone_flight_minutes(self, request, month: str = ""):
        return drone.flight_minutes_total(scope=_scope(request), month=month)

    # ═════════════════════════════════════════════════════════════════════
    # FWS-F6-01~10 산림청·지자체 산림과 연계 (annex §5.1 · 턴 AM 차선 N3)
    # `apps.fws.integration` 하나만 부른다 — 새 표는 여기서도 만들지 않는다.
    # ═════════════════════════════════════════════════════════════════════

    # ── FWS-F6-01 산림청 시스템 입력 항목 내보내기(JSON/CSV · 항목 1:1) ────
    @route.get("/liaison/fire-events/{int:event_id}/kfs-export", auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건을 산림청 내보내기로 읽을 수 없다")
    def liaison_kfs_export(self, request, event_id: int, fmt: str = "json",
                           area_ha: float | None = None, wind_mps: float | None = None,
                           duration_hours: float | None = None,
                           buildings_at_risk: int | None = None):
        from django.http import Http404, HttpResponse
        try:
            out = integration.export_kfs_feed(
                scope=_scope(request), event_id=event_id, fmt=fmt, area_ha=area_ha,
                wind_mps=wind_mps, duration_hours=duration_hours,
                buildings_at_risk=buildings_at_risk)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except integration.LiaisonInputRejected as exc:
            raise HttpError(422, str(exc))
        if out["format"] == "csv":
            return HttpResponse(out["text"], content_type="text/csv; charset=utf-8")
        return out

    # ── FWS-F6-02 웹훅 이벤트 종류(fws.fire.confirmed/stage_changed/
    #    evacuation_ordered/extinguished) — UX-19 웹훅 기계 재사용 ──────────
    @route.get("/liaison/webhook-events/catalog", auth=JwtOrInboundKey())
    @tenant_scoped(reason="이 앱이 낼 수 있는 웹훅 이벤트 종류 — 테넌트 자료가 아니다 "
                         "(선언만 · ISO-03)")
    def liaison_webhook_event_catalog(self, request):
        _scope(request)  # 인증만 확인
        return integration.webhook_event_catalog()

    @route.post("/liaison/fire-events/{int:event_id}/webhook-notify",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건으로 웹훅을 쏠 수 없다")
    @idempotent("fws.liaison.webhook_notify")
    def liaison_webhook_notify(self, request, event_id: int, kind: str, note: str = ""):
        from django.http import Http404
        try:
            return integration.notify_fws_event(
                scope=_scope(request), event_id=event_id, kind=kind, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except integration.LiaisonInputRejected as exc:
            raise HttpError(422, str(exc))
        except integration.LiaisonNoSubscribers as exc:
            raise HttpError(409, str(exc))

    # ── FWS-F6-03 산불위험예보·위기경보 수신(수동 입력) ────────────────────
    @route.post("/liaison/risk-forecast", auth=JwtOrInboundKey())
    @tenant_scoped(reason="위험예보 수동 입력은 이 사람이 남긴 기록이다")
    @idempotent("fws.liaison.risk_forecast")
    def liaison_record_risk_forecast(self, request, risk_index: float,
                                     source: str = "manual", note: str = ""):
        try:
            return integration.record_risk_forecast(
                scope=_scope(request), risk_index=risk_index, source=source, note=note)
        except integration.LiaisonInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/liaison/risk-forecast/mine", auth=JwtOrInboundKey())
    @tenant_scoped(reason="본인이 입력한 최신 예보만 읽는다")
    def liaison_my_risk_forecast(self, request):
        return integration.my_latest_risk_forecast(scope=_scope(request))

    # ── FWS-F6-05 헬기 출동 요청·위치 수신(수동 입력 대안) ─────────────────
    @route.post("/liaison/fire-events/{int:event_id}/helicopter-requests",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 헬기 요청을 남길 수 없다")
    @idempotent("fws.liaison.helicopter_request")
    def liaison_request_helicopter(self, request, event_id: int, requesting_org: str,
                                   lat: float | None = None, lng: float | None = None,
                                   note: str = ""):
        from django.http import Http404
        try:
            return integration.request_helicopter(
                scope=_scope(request), event_id=event_id, requesting_org=requesting_org,
                lat=lat, lng=lng, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except integration.LiaisonInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/liaison/fire-events/{int:event_id}/helicopter-requests",
              auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 헬기 요청을 읽을 수 없다")
    def liaison_helicopter_requests(self, request, event_id: int):
        from django.http import Http404
        try:
            return integration.helicopter_requests(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F6-06 소방 119 출동 사건 연동(DSM 통해 · K1 현장 회신 재사용) ──
    @route.post("/liaison/fire-events/{int:event_id}/fire-department-link",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 119 연동 기록을 남길 수 없다")
    @idempotent("fws.liaison.fire_department_link")
    def liaison_link_fire_department(self, request, event_id: int,
                                     dispatch_no: str = "", note: str = ""):
        from django.http import Http404
        try:
            return integration.link_fire_department(
                scope=_scope(request), event_id=event_id, dispatch_no=dispatch_no,
                note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except integration.LiaisonInputRejected as exc:
            raise HttpError(422, str(exc))

    # ── FWS-F6-07 대피 푸시 연계 [미확인] · 대안 CBS 초안 ───────────────────
    @route.post("/liaison/fire-events/{int:event_id}/evacuation-cbs-draft",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건으로 대피 문자 초안을 만들 수 없다")
    @idempotent("fws.liaison.evacuation_cbs_draft")
    def liaison_draft_evacuation(self, request, event_id: int, area_name: str,
                                 kind: str = "order", note: str = ""):
        from django.http import Http404
        try:
            return integration.draft_evacuation_notice(
                scope=_scope(request), event_id=event_id, area_name=area_name,
                kind=kind, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except integration.LiaisonInputRejected as exc:
            raise HttpError(422, str(exc))

    # ── FWS-F6-08 경찰 교통통제·입산통제 협조 기록 ──────────────────────────
    @route.post("/liaison/fire-events/{int:event_id}/police-coordination",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건에 경찰 협조 기록을 남길 수 없다")
    @idempotent("fws.liaison.police_coordination")
    def liaison_record_police_coordination(self, request, event_id: int, kind: str,
                                           note: str = ""):
        from django.http import Http404
        try:
            return integration.record_police_coordination(
                scope=_scope(request), event_id=event_id, kind=kind, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except integration.LiaisonInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/liaison/fire-events/{int:event_id}/police-coordination",
              auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 경찰 협조 기록을 읽을 수 없다")
    def liaison_police_coordination_records(self, request, event_id: int):
        from django.http import Http404
        try:
            return integration.police_coordination_records(
                scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── FWS-F6-09 스키마 버전·헬스·요청 한도(공통 API-02) — 헬스만 채운다 ──
    # ★ 스키마 버전은 `common/schema_header.py` 전역 미들웨어가 이미 모든 응답에
    #   붙인다(재사용 · 새로 안 만든다). 요청 한도는 없다(이 파일 위쪽 import
    #   블록 주석·`apps/fws/integration.py::fws_health` 머리말 참고 — F6-09 는
    #   그래서 닫힌 절로 제안하지 않는다).
    # ★ **익명이 아니다** — DSM `/api/dsm/health` 와 다른 점. 새 익명 표면을 열려면
    #   래칫 기준선(`scripts/probe_read_surface.py::PUBLIC_READ_BY_DESIGN`)을
    #   같은 커밋에서 올려야 하는데 그 파일은 이 차선 소유가 아니다 — 필요하면
    #   닫지 말고 좁힌다(정직한 기본값): 인증은 요구하되 테넌트 자료는 안 본다.
    @route.get("/health", auth=JwtOrInboundKey())
    @tenant_scoped(required=False,
                   reason="생존 확인 — 테넌트 자료가 아니다. db·cache 검사(DSM 과 "
                         "같은 모양이지만 계층 게이트 때문에 App 내부를 직접 "
                         "import 하지 않고 이 App 이 다시 짓는다 · integration.py "
                         "머리말 참고) · 인증은 요구한다(익명 래칫 밖)")
    def fws_health(self, request):
        from django.http import JsonResponse

        body = integration.fws_health()
        status = 200 if body["status"] == "ok" else 503
        resp = JsonResponse(body, status=status)
        resp["Cache-Control"] = "no-store"
        return resp

    # ── FWS-F6-10 국립공원·국유림관리소 관할 사건 이첩 ──────────────────────
    @route.post("/liaison/fire-events/{int:event_id}/jurisdiction-transfer",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건을 이첩할 수 없다")
    @idempotent("fws.liaison.jurisdiction_transfer")
    def liaison_transfer_jurisdiction(self, request, event_id: int, org_type: str,
                                      target_org: str, note: str = ""):
        from django.http import Http404
        try:
            return integration.transfer_jurisdiction(
                scope=_scope(request), event_id=event_id, org_type=org_type,
                target_org=target_org, note=note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except integration.LiaisonInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/liaison/fire-events/{int:event_id}/jurisdiction-transfer",
              auth=JwtOrInboundKey())
    @tenant_scoped(reason="남의 테넌트 사건의 이첩 기록을 읽을 수 없다")
    def liaison_jurisdiction_transfers(self, request, event_id: int):
        from django.http import Http404
        try:
            return integration.jurisdiction_transfers(
                scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
