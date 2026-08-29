# -*- coding: utf-8 -*-
"""DSM App 의 HTTP 면 — **신규 라우트는 트립와이어를 통과해야 한다** (D-275 §5-1).

이 파일이 지키는 셋
-------------------
① **문지기 없는 새 경로를 만들지 않는다.** WP-2 EXIT 가 남긴 미지는
   *"지금 닫혀 있는 이유는 라우트마다 문지기를 손으로 달았기 때문이고, 문지기 없는
   새 경로가 하나 생기면 그 순간 다시 샌다"* 였다. 그래서 모든 라우트가
   `@tenant_scoped()` 를 달고, **실제 좁히기는 커널이** `TenantScope` 로 한다
   (시그니처가 1차 · 문지기가 2차 — D-281).

② **오류는 HTTP 상태로 낸다.** `200 + {"success": false}` 를 만들지 않는다(W0-18).
   이 저장소는 권한 거부를 200 으로 내보내 **거부 사실이 소멸**한 라우트를 8건 갖고
   있었다. 신규 라우트는 그 전철을 밟지 않는다.

③ **`response=<단일 스키마>` 를 선언하지 않는다.** W0-18 실측: 그 선언이 붙은 8건에서
   거부 dict 가 스키마를 통과해 `200 + {}` 가 됐고, 거부 사실이 사라졌다.
   그 8건은 P-W0-18-1 A 안으로 전부 뗐다 — 새로 만들지 않는다.

왜 `BaseResponse` 를 쓰지 않나
------------------------------
기존 컨트롤러들은 `BaseResponse(status_code=..., ...)` 로 dict 를 돌려주고, 그 값은
**언제나 HTTP 200 으로 나간다.** 그것이 ②가 금지한 모양 그 자체다.
신규 App 은 성공이면 값을, 실패면 `HttpError` 를 던진다.
"""
from __future__ import annotations

from datetime import datetime

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import TenantScope, tenant_scoped
from core.api.v1.auth import CustomJWTAuth

from apps.dsm import services
from apps.dsm.exceptions import PermissionDeniedForSetting, SettingNotAvailable


def _scope(request) -> TenantScope:
    """요청자에서 스코프를 만든다. **없으면 401** — 여기까지 오면 안 되는 상태다.

    `TenantScope.of(None)` 이 던지는 것을 그대로 500 으로 내보내지 않는다:
    인증이 없는 것은 서버 결함이 아니라 요청의 상태이고, 둘은 다른 상태 코드다.
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


def _panel_payload(panel) -> dict:
    """K3 `PanelView` → 화면이 읽는 dict. **상태를 반드시 싣는다.**

    상태를 빼면 화면이 "값이 없으니 빈 칸" 으로 그리고, 그 순간 오류와 빈 칸이
    같은 그림이 된다 — DA-03 §2-5 규칙 1이 금지한 자리다.
    """
    return {
        "panel_id": panel.panel_id,
        "dashboard_id": panel.dashboard_id,
        "title": panel.title,
        "panel_type": panel.panel_type,
        "state": panel.state.value,
        "reason": panel.reason,
        "config": panel.config,
    }


# ★ 접두어를 비운다. `config/urls.py` 가 이미 `api/dsm/` 로 마운트하므로 여기서 다시
#   "/dsm" 을 붙이면 **`/api/dsm/dsm/...` 가 된다** — 기존 앱들이 실제로 그 모양이다
#   (`/api/stream-monitors/stream-monitors/...`). 새로 만드는 것까지 그럴 이유는 없다.
@api_controller("", tags=["DSM — 재난안전 모니터링 (F-09~F-12)"])
class DsmAPI:
    """F-09~F-12 의 라우트. **커널을 소비만 한다** (DA-04 §1-1)."""

    # ── F-09 재난 대시보드 ───────────────────────────────────────────────
    @route.get("/dashboard/frame", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-09 대시보드 프레임 — 남의 테넌트 패널이 섞이면 안 된다")
    def dashboard_frame(self, request, dashboard_code: str | None = None):
        """F-09 프레임. **AC-09 ①의 5상태를 값으로 낸다.**

        검수에서 "5상태 100%" 를 물으면 세지 않고 이 응답을 보여 준다:
        `five_states` 가 정의된 다섯이고 `state_counts` 가 각 상태의 칸 수다.
        **분모를 함께 낸다** — "정상 3칸" 만 보면 전체가 3인지 30인지 모른다.
        """
        frame = services.dashboard_frame(scope=_scope(request),
                                         dashboard_code=dashboard_code)
        return {
            "preset": frame.preset,
            "preset_matched": frame.preset_matched,
            "five_states": list(frame.five_states),
            "state_counts": frame.state_counts,
            "panel_total": len(frame.panels),
            "panels": [_panel_payload(p) for p in frame.panels],
            "link": {"status": frame.link.status.value, "reason": frame.link.reason},
        }

    @route.get("/dashboard/link-state", auth=JwtOrInboundKey())
    @tenant_scoped(required=False,
                   reason="연계 상태는 테넌트별 사실이 아니라 **설비의 사실**이다 — "
                          "테넌트 모델을 만지지 않으므로 group 을 요구하지 않는다. "
                          "그래도 표식은 단다: 표식이 없는 라우트는 '분류를 잊은 것' 과 "
                          "'분류가 필요 없는 것' 이 구별되지 않는다 (D-272)")
    def link_state(self, request):
        """FR-09-4 — 연계 정상 / 대기 / 끊김.

        ★ 인증은 필요하고 테넌트 좁히기는 필요 없다. 그 둘은 다른 질문이고,
          `required=False` 가 그 답을 코드에 남긴다. PUBLIC_ROUTES 에 넣지 않는 이유도
          같다 — 그 목록은 **인증 불요**를 뜻하고, 이 라우트는 인증이 필요하다.
        """
        state = services.link_state()
        return {"status": state.status.value, "reason": state.reason}

    @route.get("/events", auth=JwtOrInboundKey(
        inbound_key=True,
        reason="F-05 「외부 App 이 이벤트 OpenAPI 하나로만 들어온다」 — 읽기 전용 조회"))
    @tenant_scoped(reason="F-09 이벤트 목록 — 남의 테넌트 이벤트가 보이면 격리 실패다")
    def events(self, request, since: datetime | None = None,
               event_type: str | None = None, severity: str | None = None,
               limit: int = 50):
        """F-09 이벤트 목록.

        ★ NFR-09-1 — 스트리밍 서버가 죽어도 이 목록은 200 이다.
          여기서 스트리밍을 부르지 않는 것이 그 성질의 전부다.
        """
        rows = services.recent_events(scope=_scope(request), since=since,
                                      event_type=event_type, severity=severity,
                                      limit=limit)
        return {"total": len(rows), "events": [
            {"event_id": e.event_id, "event_type": e.event_type,
             "severity": e.severity, "status": e.status, "verdict": e.verdict,
             "occurred_at": e.occurred_at, "last_seen_at": e.last_seen_at,
             "stream_monitor_id": e.stream_monitor_id,
             "stream_monitor_name": e.stream_monitor_name,
             "lat": e.lat, "lng": e.lng, "snapshot_path": e.snapshot_path}
            for e in rows]}

    # ── F-10 알림 발송 ───────────────────────────────────────────────────
    @route.post("/events/{int:event_id}/notify", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-10 발송 — 남의 이벤트로 발송을 일으킬 수 없다 (쓰기 IDOR)")
    def notify(self, request, event_id: int):
        """F-10 발송. **실패도 200 이고, 실패는 행으로 보인다.**

        발송 실패는 이 라우트의 실패가 아니다 — 저하 운전(DA2-21 (4))이 요구하는 대로
        업체가 죽어도 이벤트 처리는 200 을 유지한다. 대신 각 행의 `succeeded` 가 갈린다.
        `404` 는 **남의 테넌트 이벤트**일 때만 난다.
        """
        try:
            records = services.notify_event(scope=_scope(request), event_id=event_id)
        except Http404:
            raise HttpError(404, "그런 이벤트가 없습니다.")
        return {"total": len(records), "deliveries": [
            {"delivery_id": r.delivery_id, "event_id": r.event_id,
             "recipient_id": r.recipient_id, "channel": r.channel,
             "succeeded": r.succeeded, "failure_reason": r.failure_reason,
             "sent_at": r.sent_at}
            for r in records]}

    @route.get("/deliveries", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-10 발송 이력 — 수신자 주소가 새면 안 된다")
    def deliveries(self, request, event_id: int | None = None,
                   since: datetime | None = None, until: datetime | None = None,
                   succeeded: bool | None = None, limit: int = 100, offset: int = 0):
        """FR-10-2 — 대상·시각·채널·성공여부가 남는가."""
        rows = services.delivery_history(
            scope=_scope(request), event_id=event_id, since=since, until=until,
            succeeded=succeeded, limit=limit, offset=offset)
        return {"total": len(rows), "deliveries": [
            {"delivery_id": r.delivery_id, "event_id": r.event_id,
             "recipient_id": r.recipient_id, "channel": r.channel,
             "succeeded": r.succeeded, "failure_reason": r.failure_reason,
             "sent_at": r.sent_at}
            for r in rows]}

    # ── F-11 상황 보고서 ─────────────────────────────────────────────────
    @route.get("/reports/templates", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-11 템플릿 목록 — 남의 테넌트 템플릿이 보이면 안 된다")
    def report_templates(self, request):
        rows = services.report_templates(scope=_scope(request))
        return {"total": len(rows), "templates": [
            {"template_id": t.template_id, "name": t.name,
             "renderer": t.renderer} for t in rows]}

    @route.get("/reports/{int:template_id}.pdf", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-11 보고서 — 남의 이벤트가 보고서에 실리면 안 된다")
    def report_pdf(self, request, template_id: int, event_id: int | None = None,
                   mission_id: int | None = None):
        """AC-11 — 템플릿 치환 PDF.

        ★ 불완전한 컨텍스트로 찍지 않는다. 출처가 실패했으면 K4 가 예외를 올리고,
          여기서는 **409** 로 번역한다 — 서버 결함(500)이 아니라 **지금 찍을 수 없는
          상태**이기 때문이다. 200 으로 빈 PDF 를 내보내지 않는다 (D-284).
        """
        from kernels.k4_report import InvalidReportInput, RenderFailed

        try:
            pdf = services.build_report(scope=_scope(request), template_id=template_id,
                                        event_id=event_id, mission_id=mission_id)
        except Http404:
            raise HttpError(404, "그런 템플릿이 없습니다.")
        except InvalidReportInput as exc:
            raise HttpError(400, str(exc))
        except RenderFailed as exc:
            raise HttpError(409, f"지금은 보고서를 찍을 수 없습니다 — {exc}")
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="guardianx-report-{template_id}.pdf"')
        return response

    # ── F-09 영상 재생 — 계약 11조(원본 영상 무반출)가 여기서 걸린다 (D-306) ──
    #
    # ★ 이 두 라우트가 이번 턴에서 가장 위험한 자리다. 영상은 우리 산출물 중 반출 위험이
    #   가장 크고, 계약 11조는 그것을 정면으로 금지한다. 규약 넷을 **시험으로** 걸었고
    #   (backend/tests/test_clip_playback.py), 넷 중 하나라도 없으면 라우트를 내지 않는다.
    #
    #     ① 테넌트 범위 — 남의 event_id 는 404. 403 이 아니다(존재도 알리지 않는다 · D-269)
    #     ② 만료 서명 URL — 무기한 링크 금지
    #     ③ 구간 한정 — 구간이 서명에 묶여 있어 **다른 구간을 요구할 수조차 없다**
    #     ④ 다운로드 아님 — 원본 전체를 주는 경로가 **없다**(부작위 시험이 잰다 · D-300)
    @route.get("/events/{int:event_id}/clip", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-09 영상 구간 참조 — 남의 이벤트 영상에 닿으면 계약 11조 위반이다")
    def event_clip(self, request, event_id: int):
        """AC-09 — 이벤트 클릭 → **어디를 보라**.

        돌려주는 것은 구간에 묶인 만료 티켓이고, **객체를 통째로 받을 수 있는 URL 이
        아니다.** 프리사인드 URL 을 내면 요청한 30초를 주려다 두 시간짜리 원본을 준다.
        """
        from stream_monitors.services import clips

        try:
            ticket = clips.issue_ticket(scope=_scope(request), event_id=event_id)
        except Http404 as exc:
            raise HttpError(404, str(exc) or "그런 이벤트가 없습니다.")
        return {
            "event_id": ticket.event_id,
            "start_offset": ticket.start_offset,
            "duration": ticket.duration,
            "expires_at": ticket.expires_at.isoformat(),
            "token": ticket.token,
            # ★ 지금 바이트를 받을 수 있는가. 거짓이면 **사유가 함께 나간다** —
            #   조용히 빈 응답을 주면 화면은 "영상이 없다" 로 읽는다 (D-284 · D-290).
            "playable": ticket.playable,
            "reason": ticket.reason,
        }

    @route.get("/events/{int:event_id}/clip/stream", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-09 영상 구간 전송 — 구간 밖 바이트가 나가면 계약 11조 위반이다")
    def event_clip_stream(self, request, event_id: int, token: str,
                          start_offset: float, duration: float):
        """구간의 바이트. **지금은 아무 바이트도 나가지 않는다** (CLIP_EXTRACTION_READY=False).

        티켓을 **먼저** 검증하고 그다음 잠금에서 멈춘다. 순서가 반대면 "티켓이 틀렸다" 와
        "아직 못 준다" 가 같은 응답이 되고, 잠금이 풀린 날 검증이 도는지 아무도 모른다.
        """
        from stream_monitors.services import clips

        try:
            clip_ticket = clips.issue_ticket(scope=_scope(request), event_id=event_id)
        except Http404 as exc:
            raise HttpError(404, str(exc) or "그런 이벤트가 없습니다.")
        try:
            clips.stream_window(
                token=token, event_id=event_id, object_key=clip_ticket.object_key,
                start_offset=start_offset, duration=duration)
        except Http404 as exc:
            raise HttpError(404, str(exc))
        except NotImplementedError as exc:
            # 501 — **아직 구현하지 않았다.** 404(없는 주소)도 500(결함)도 아니다.
            raise HttpError(501, str(exc))
        raise HttpError(500, "도달할 수 없는 자리")   # stream_window 는 언제나 멈춘다

    # ── F-12 관리자 설정 ─────────────────────────────────────────────────
    @route.get("/settings/{domain}", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-12 설정 — 남의 테넌트 설정이 보이면 안 된다")
    def settings_domain(self, request, domain: str):
        """AC-12 — 무권한 차단 + **성공·실패 모두 감사로그**.

        `403` 응답의 `audit_id` 는 **차단이 기록에 남았다는 증거**다.
        차단만 하고 안 남기면 "시도가 없었다" 와 "시도가 막혔다" 가 같은 상태가 된다.
        """
        try:
            return services.setting_overview(scope=_scope(request), domain=domain)
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, f"{exc.reason} (감사 #{exc.audit_id})")
        except SettingNotAvailable as exc:
            # 501 — 서버가 그 기능을 **아직 구현하지 않았다.** 404(없는 주소)도
            # 400(잘못된 요청)도 아니다. 셋을 뭉치면 "언젠가 생길 것" 과
            # "영영 없는 것" 이 클라이언트에서 구별되지 않는다.
            raise HttpError(501, str(exc))

    @route.post("/settings/thresholds", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-12 임계값 쓰기 — 남의 테넌트 임계값을 못 바꾼다")
    def set_threshold(self, request, key: str, value: float, reason: str,
                      scope_level: str = "global", scope_ref: int | None = None):
        """F-12 「임계값」 · F-02 「**지점별** 기준선 설정」 — 값을 바꾸는 유일한 문.

        **사유 없이는 못 바꾼다.** 무엇에서 무엇으로는 표가 알지만 **왜** 는
        여기서만 들어온다 — 그 칸이 비면 400 이다.

        계약이 못박은 값(F-04 5분 · F-10 30초)은 **409** 다. 400(잘못된 요청)이 아니라
        409(상태 충돌)인 이유: 요청이 틀린 게 아니라 **그 값이 계약이라서** 안 되는 것이다.
        """
        from kernels.k5_trust import (
            ScopeNotAvailable,
            ThresholdIsContractFixed,
            ThresholdNotDefined,
        )

        try:
            return services.set_threshold_value(
                scope=_scope(request), key=key, value=value, reason=reason,
                scope_level=scope_level, scope_ref=scope_ref)
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, f"{exc.reason} (감사 #{exc.audit_id})")
        except ThresholdIsContractFixed as exc:
            raise HttpError(409, str(exc))
        except (ThresholdNotDefined, ScopeNotAvailable, ValueError) as exc:
            raise HttpError(400, str(exc))

    @route.post("/settings/zones", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-12 구역 쓰기 — 남의 테넌트 위험구역을 못 만든다")
    def save_zone(self, request, name: str, kind: str, zone_id: int | None = None,
                  geometry: dict | None = None, camera_ids: list[int] | None = None,
                  is_active: bool = True):
        """F-12 「구역」 · F-03 「지정 위험구역(폴리곤)」 — 구역을 **지정하는 유일한 문**.

        오류를 셋으로 가른다. 뭉치면 화면 앞의 사람이 무엇을 해야 할지 모른다:

            403  권한이 없다        — 감사 번호와 함께 나간다
            400  도형이 잘못됐다    — `InvalidPolygon`. **다시 그려야 한다**
            403  남의 카메라를 붙였다 — 조용히 빼지 않는다(D-284)

        ★ 남의 `zone_id` 는 **404** 다 — 403 은 그 구역이 있다는 사실을 알린다(D-269).
        """
        from stream_monitors.services.zones import InvalidPolygon

        try:
            return services.save_zone_setting(
                scope=_scope(request), zone_id=zone_id, name=name, kind=kind,
                geometry=geometry, camera_ids=camera_ids, is_active=is_active)
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, f"{exc.reason} (감사 #{exc.audit_id})")
        except Http404 as exc:
            raise HttpError(404, str(exc) or "그런 구역이 없습니다.")
        except PermissionDenied as exc:
            # L3 이 낸 거부. **이 저장소가 쓰는 거부의 형태**이고,
            # `test_tenant_isolation._is_refusal` 이 아는 형태이기도 하다 —
            # 새 예외 형을 만들면 격리 시험이 그것을 「부서진 것」으로 읽는다.
            raise HttpError(403, str(exc))
        except InvalidPolygon as exc:
            # 400 — **요청이 틀렸다.** 구역을 다시 그려야 한다. 500(결함)이 아니다.
            raise HttpError(400, str(exc))
        except ValueError as exc:
            raise HttpError(400, str(exc))

    # ── F-05 「API Key 발급·폐기」 · F-12 「API키」 ─────────────────────────
    #
    # ★ 이 셋이 계약 F-05 의 마지막 절을 갚는 자리다 (D-367). 세 번 미뤄졌던 절이고,
    #   미룬 이유가 세 번 다 달랐다 — 방향 오판(D-337) · 범위 문제(D-335) · 그리고
    #   남은 하나가 이것, **발급·폐기의 면**이다.
    #
    # ★ `inbound_key=True` 를 여기에 **주지 않는다.** 들어오는 키로 들어오는 키를
    #   발급받을 수 있으면 키 하나가 영원히 자기를 갱신한다 — 폐기가 폐기가 아니게 된다.
    #   이 셋은 사람(JWT)만 부른다.
    @route.post("/settings/api-keys", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-05 키 발급 — 남의 테넌트 이름으로 키를 만들 수 없다")
    def issue_api_key(self, request, name: str, expires_days: int | None = None):
        """F-05 「API Key 발급」. **`secret` 이 사람에게 보이는 유일한 응답이다.**

        저장소는 원문을 갖지 않는다(sha256 해시만). 이 응답을 놓치면 되찾을 수 없고
        회전만 가능하다 — 되찾을 수 있다면 그것은 어딘가에 저장돼 있다는 뜻이다.
        """
        try:
            return services.issue_inbound_key(
                scope=_scope(request), name=name, expires_days=expires_days)
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, f"{exc.reason} (감사 #{exc.audit_id})")
        except PermissionDenied as exc:
            raise HttpError(403, str(exc))
        except ValueError as exc:
            raise HttpError(400, str(exc))

    @route.delete("/settings/api-keys/{int:key_id}", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-05 키 폐기 — 남의 테넌트 키를 끌 수 없다")
    def revoke_api_key(self, request, key_id: int):
        """F-05 「API Key 폐기」. 행은 남고 **꺼진다.**

        남의 키는 **404** 다 — 403 은 "있는데 못 만진다" 를 알려 주고, 그것만으로
        남의 테넌트에 그 id 가 있다는 사실이 샌다 (D-269).
        """
        from kernels.k5_trust import InboundKeyNotFound

        try:
            return services.revoke_inbound_key(scope=_scope(request), key_id=key_id)
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, f"{exc.reason} (감사 #{exc.audit_id})")
        except InboundKeyNotFound:
            raise HttpError(404, "그런 키가 없습니다.")
        except PermissionDenied as exc:
            raise HttpError(403, str(exc))

    @route.post("/settings/api-keys/{int:key_id}/rotate", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-05 키 회전 — 남의 테넌트 키를 돌릴 수 없다")
    def rotate_api_key(self, request, key_id: int):
        """회전 — 폐기와 발급을 **한 번에.** 둘로 나누면 한쪽을 잊는다.

        옛 키는 지워지지 않고 `rotated` 로 남는다 — "폐기됐다" 와 "새것으로 바뀌었다"
        는 다른 사실이고, 뒤엣것은 **후속 키가 있다**는 뜻이다.
        """
        from kernels.k5_trust import InboundKeyNotFound

        try:
            return services.rotate_inbound_key(scope=_scope(request), key_id=key_id)
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, f"{exc.reason} (감사 #{exc.audit_id})")
        except InboundKeyNotFound:
            raise HttpError(404, "그런 키가 없습니다.")
        except PermissionDenied as exc:
            raise HttpError(403, str(exc))

    @route.post("/settings/grade-rules", auth=JwtOrInboundKey())
    @tenant_scoped(reason="F-12 등급규칙 쓰기 — 남의 테넌트 등급규칙을 못 바꾼다")
    def set_grade_rule(self, request, event_type: str, severity: str, reason: str):
        """F-12 「등급규칙」 · F-04 「JSON **무재기동** 반영」 — 규칙을 바꾸는 유일한 문.

        **사유 없이는 못 바꾼다.** 무엇에서 무엇으로는 표가 알지만 **왜** 는
        여기서만 들어온다 — 그 칸이 비면 400 이다.

        ★ 응답의 `lowered` 를 화면이 반드시 보여 줘야 한다. 참이면 그 이벤트는
          **조용해진 것**이고, 경보가 안 오는 것은 「아무 일도 없음」으로 보인다.
        """
        from kernels.k5_trust import GradeRuleNotDefined, SeverityNotInContract

        try:
            return services.set_grade_rule_value(
                scope=_scope(request), event_type=event_type,
                severity=severity, reason=reason)
        except PermissionDeniedForSetting as exc:
            raise HttpError(403, f"{exc.reason} (감사 #{exc.audit_id})")
        except (GradeRuleNotDefined, SeverityNotInContract, ValueError) as exc:
            raise HttpError(400, str(exc))
