# -*- coding: utf-8 -*-
"""FWS 잔여 새 절(턴 AP · WO-19 · 차선 N4 단독 소유 · F3·F5·F6 잔여 · 명세 제목이 정본).

조율자가 빈 컨트롤러로 세워 `urls.py` 에 등록해 둠. `api.py`·다른 차선 파일은 고치지 않는다.
★ `from __future__ import annotations` 를 쓰지 않는다(D-378).

이 파일이 여는 것 — F5-01·F5-03 반쪽 채움(`apps/fws/ap_f5.py`)
-------------------------------------------------------------------------------
값 판정·감사 규약은 `ap_f5.py` 가 갖고 있고, 이 파일은 스키마 검증 + 예외 →
HTTP 상태 번역만 한다(`api_u4.py` 와 같은 규약). `apps/fws/drone.py`(N2 소유)는
읽기만 하고 고치지 않는다.

★ 경로 겹침 없음 [실측] — 이 파일의 리터럴(`drone/missions/{id}/recon-coords` ·
  `drone/verifications/{id}/thermal-attachment`)은 `api.py`·`api_office.py`·
  `api_office2.py`·`api_admin.py`·`api_n1.py`·`api_command.py` 어디에도 없다
  (grep 전수 — `recon-coords`·`thermal-attachment` 리터럴은 이 파일에만 있다).
"""
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import SystemScopeCannotRead, TenantScope, tenant_scoped

from apps.fws import ap_f5, ap_f6


def _scope(request) -> TenantScope:
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


@api_controller("ap", tags=["FWS — 잔여 새 절 (턴 AP · N4)"])
class FwsApAPI:
    # ══════════════════════════════════════════════════════════════════════
    # FWS-F5-01 반쪽 채움 — 발화 추정 좌표 + 반경 한 응답
    # ══════════════════════════════════════════════════════════════════════
    @route.get("/drone/missions/{int:event_id}/recon-coords", auth=JwtOrInboundKey())
    @tenant_scoped(reason="정찰 임무 좌표 조회 — 남의 테넌트 사건 좌표가 보이면 "
                          "격리 실패다")
    def recon_coords(self, request, event_id: int):
        """`GET /drone/missions/{id}/recon-coords` — 그 사건의 발화 추정
        좌표(lat/lng)를 정찰 반경(radius_m)과 함께 낸다."""
        from django.http import Http404

        try:
            return ap_f5.recon_coords(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ══════════════════════════════════════════════════════════════════════
    # FWS-F5-03 반쪽 채움 — 열화상 전용 증빙 칸(사진 참조와 구분)
    # ══════════════════════════════════════════════════════════════════════
    @route.post("/drone/verifications/{int:event_id}/thermal-attachment",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="열화상 증빙 첨부 — 남의 테넌트 사건에 남으면 격리 실패다")
    def attach_thermal(self, request, event_id: int, thermal_ref: str):
        """`POST /drone/verifications/{id}/thermal-attachment` — 열화상 증빙
        참조를 사진(`attachment_ref`)과 다른 칸에 남긴다. 판정에는 관여하지
        않는다(F1-06/F5-03 문이 그대로 판정한다)."""
        from django.http import Http404

        try:
            return ap_f5.attach_thermal(
                scope=_scope(request), event_id=event_id, thermal_ref=thermal_ref)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except ap_f5.ThermalAttachmentRejected as exc:
            raise HttpError(422, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    @route.get("/drone/verifications/{int:event_id}/thermal-attachment",
              auth=JwtOrInboundKey())
    @tenant_scoped(reason="열화상 증빙 열람 — 남의 테넌트 사건이 보이면 격리 실패다")
    def thermal_attachments(self, request, event_id: int):
        """`GET /drone/verifications/{id}/thermal-attachment` — 그 사건의
        열화상 증빙 전건(최신 먼저)."""
        from django.http import Http404

        try:
            return ap_f5.thermal_attachments(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ══════════════════════════════════════════════════════════════════════
    # FWS-F5-10 반쪽 채움 — 월 표
    # ══════════════════════════════════════════════════════════════════════
    @route.get("/drone/flights/minutes/monthly-table", auth=JwtOrInboundKey())
    @tenant_scoped(reason="비행 분 월 표 — 남의 조종사 기록이 섞이면 격리 실패다")
    def flight_minutes_monthly_table(self, request, limit: int = 500):
        """`GET /drone/flights/minutes/monthly-table` — 비행 분·건수를 월별로
        접은 표(명세 완결 조건 「월 표」)."""
        try:
            return ap_f5.flight_minutes_monthly_table(scope=_scope(request), limit=limit)
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ══════════════════════════════════════════════════════════════════════
    # FWS-F6-04 확산예측 결과 수신 — 업로드 경로(API 는 excluded_by P-428)
    # ══════════════════════════════════════════════════════════════════════
    @route.post("/incidents/{int:event_id}/spread-results", auth=JwtOrInboundKey())
    @tenant_scoped(reason="확산예측 결과 업로드 — 남의 테넌트 사건에 남으면 격리 실패다")
    def upload_spread_result(self, request, event_id: int, image_ref: str,
                             arrival_note: str = ""):
        """`POST /incidents/{id}/spread-results` — 확산예측 결과(이미지/좌표
        참조)를 업로드 경로로 등록한다."""
        from django.http import Http404

        try:
            return ap_f6.record_spread_result(
                scope=_scope(request), event_id=event_id, image_ref=image_ref,
                arrival_note=arrival_note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except ap_f6.SpreadResultRejected as exc:
            raise HttpError(422, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    @route.get("/incidents/{int:event_id}/spread-results", auth=JwtOrInboundKey())
    @tenant_scoped(reason="확산예측 결과 열람 — 남의 테넌트 사건이 보이면 격리 실패다")
    def list_spread_results(self, request, event_id: int):
        """`GET /incidents/{id}/spread-results` — 그 사건의 확산예측 결과 전건."""
        from django.http import Http404

        try:
            return ap_f6.list_spread_results(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
