# -*- coding: utf-8 -*-
"""FWS U5 기관 관리자(산불 설정) — 카메라·초소·마을·알림 규칙(FWS-U5-01~04).

턴 AN · WO-17 · 차선 N4 단독 소유 파일(조율자가 빈 컨트롤러로 세워 `urls.py` 에 등록해 둠).
`api.py` 는 이 턴에 아무 차선도 고치지 않는다 — 문은 전부 이 파일에 더한다.
★ `from __future__ import annotations` 를 쓰지 않는다(D-378 · `api.py` 머리말과 같은 까닭).

경로는 전부 `/admin/...` 아래에 둔다 — `apps/fws/api.py`·`api_office.py`·
`api_office2.py` 전수(grep 재확인)에 **첫 조각이 변수인 라우트가 0개**라 삼킴이
없다(메모리 「라우트 삼킴 함정」의 예방 조치와 같은 확인).

로직은 `apps/fws/admin_settings.py` 하나에 있다 — 이 파일은 그 함수를 HTTP 로
여는 얇은 문일 뿐이다(`AppStaysThinTest`, `test_fws_app.py`).
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


@api_controller("", tags=["FWS — 관리자 U5 (턴 AN · N4)"])
class FwsAdminAPI:
    # ═══════════════════════════════════════════════════════════════════
    # FWS-U5-01 — 산불 감시 카메라 등록(고지대·PTZ 프리셋·열화상 채널·감시 반경)
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/admin/cameras", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-01 카메라 목록 — 남의 테넌트 카메라·표식이 보이면 격리 실패다")
    def admin_cameras_list(self, request):
        from apps.fws import admin_settings

        try:
            return admin_settings.list_fire_cameras(scope=_scope(request))
        except admin_settings.AdminPermissionDenied as exc:
            raise HttpError(403, str(exc))

    @route.get("/admin/cameras/{int:camera_id}/fire-marker", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-01 표식 조회 — 남의 테넌트 카메라는 404(존재도 새지 않는다)")
    def admin_camera_marker_get(self, request, camera_id: int):
        from apps.fws import admin_settings

        try:
            return admin_settings.camera_fire_marker(scope=_scope(request), camera_id=camera_id)
        except admin_settings.AdminPermissionDenied as exc:
            raise HttpError(403, str(exc))
        except admin_settings.AdminNotFound:
            raise HttpError(404, "그런 카메라가 없습니다.")

    @route.post("/admin/cameras/{int:camera_id}/fire-marker", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-01 표식 저장 — 남의 테넌트 카메라의 표식을 바꿀 수 없다(쓰기 IDOR)")
    def admin_camera_marker_save(self, request, camera_id: int, is_highland: bool = False,
                                 thermal_channel: str = "", ptz_presets: str = "",
                                 radius_polygon_json: str = ""):
        from apps.fws import admin_settings

        try:
            return admin_settings.save_camera_fire_marker(
                scope=_scope(request), camera_id=camera_id, is_highland=is_highland,
                thermal_channel=thermal_channel, ptz_presets=ptz_presets,
                radius_polygon_json=radius_polygon_json)
        except admin_settings.AdminPermissionDenied as exc:
            raise HttpError(403, str(exc))
        except admin_settings.AdminNotFound:
            raise HttpError(404, "그런 카메라가 없습니다.")
        except admin_settings.AdminInputRejected as exc:
            raise HttpError(422, str(exc))

    # ═══════════════════════════════════════════════════════════════════
    # FWS-U5-02 — 초소·순찰함(NFC)·순찰 구역 등록
    # ═══════════════════════════════════════════════════════════════════
    @route.post("/admin/posts", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-02 초소 등록 — 관리자만. 등록은 감사 한 줄로 남는다")
    def admin_post_save(self, request, post_code: str, name: str, patrol_zone: str = "",
                        lat: float | None = None, lng: float | None = None,
                        nfc_boxes: str = ""):
        from apps.fws import admin_settings

        try:
            return admin_settings.save_post(
                scope=_scope(request), post_code=post_code, name=name,
                patrol_zone=patrol_zone, lat=lat, lng=lng, nfc_boxes=nfc_boxes)
        except admin_settings.AdminPermissionDenied as exc:
            raise HttpError(403, str(exc))
        except admin_settings.AdminInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/admin/posts", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-02 초소 목록 — 관리자만")
    def admin_posts_list(self, request):
        from apps.fws import admin_settings

        try:
            return admin_settings.my_posts(scope=_scope(request))
        except admin_settings.AdminPermissionDenied as exc:
            raise HttpError(403, str(exc))

    # ═══════════════════════════════════════════════════════════════════
    # FWS-U5-03 — 마을·대피소·요양시설 등록(대피 대상 자동 산출)
    # ═══════════════════════════════════════════════════════════════════
    @route.post("/admin/evac-targets", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-03 대피 대상 등록 — 관리자만")
    def admin_evac_entity_save(self, request, kind: str, name: str, headcount: int,
                               note: str = ""):
        from apps.fws import admin_settings

        try:
            return admin_settings.save_evac_entity(
                scope=_scope(request), kind=kind, name=name, headcount=headcount, note=note)
        except admin_settings.AdminPermissionDenied as exc:
            raise HttpError(403, str(exc))
        except admin_settings.AdminInputRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/admin/evac-targets", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-03 대피 대상 조회 — 관리자만")
    def admin_evac_targets_list(self, request):
        from apps.fws import admin_settings

        try:
            return admin_settings.evac_targets(scope=_scope(request))
        except admin_settings.AdminPermissionDenied as exc:
            raise HttpError(403, str(exc))

    # ═══════════════════════════════════════════════════════════════════
    # FWS-U5-04 — 산불 알림 규칙(등급별 수신) · 야간 5분대기조 채널
    # (`kernels.k2_notify.rule_admin` 재사용 — 새 저장처 없음)
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/admin/notify-rules", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-04 알림 규칙 조회 — 남의 테넌트가 누구에게 재난을 알리는지는 "
                         "남의 정보다")
    def admin_notify_rules_get(self, request):
        from apps.fws import admin_settings

        try:
            return admin_settings.notify_rules_overview(scope=_scope(request))
        except admin_settings.AdminPermissionDenied as exc:
            raise HttpError(403, str(exc))

    @route.post("/admin/notify-rules", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-04 알림 규칙 저장 — 남의 테넌트 규칙을 바꾸면 그쪽 당직자가 "
                         "재난을 못 듣는다(쓰기 IDOR)")
    def admin_notify_rules_save(self, request, severity: str, role_code: str,
                                channels: str, zone: str = "", is_active: bool = True,
                                rule_id: int = 0):
        from apps.fws import admin_settings
        from kernels.k2_notify import (CriticalWithoutRecipients,
                                       InvalidNotifyInput, NotifyPermissionDenied)

        try:
            return admin_settings.save_notify_rule(
                scope=_scope(request), severity=severity, role_code=role_code,
                channels=channels, zone=zone, is_active=is_active, rule_id=rule_id)
        except admin_settings.AdminPermissionDenied as exc:
            raise HttpError(403, str(exc))
        except CriticalWithoutRecipients as exc:
            raise HttpError(409, str(exc))
        except NotifyPermissionDenied as exc:
            raise HttpError(403, str(exc))
        except InvalidNotifyInput as exc:
            raise HttpError(400, str(exc))

    @route.post("/admin/notify-rules/test", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U5-04 시험 발송 — 남의 테넌트 수신자에게 발송을 일으킬 수 없다"
                         "(쓰기 IDOR)")
    def admin_notify_rules_test(self, request, severity: str = "critical"):
        from apps.fws import admin_settings
        from kernels.k2_notify import CriticalWithoutRecipients, InvalidNotifyInput

        try:
            return admin_settings.test_notify_rule(scope=_scope(request), severity=severity)
        except admin_settings.AdminPermissionDenied as exc:
            raise HttpError(403, str(exc))
        except CriticalWithoutRecipients as exc:
            raise HttpError(409, str(exc))
        except InvalidNotifyInput as exc:
            raise HttpError(400, str(exc))
