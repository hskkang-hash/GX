# -*- coding: utf-8 -*-
"""WO-GX-20260925-15 §5 (P-356·P-358) — 차선 **N4**(재난안전과 담당 공무원, U4)
라우터 모듈 · 턴 AM.

이 파일이 여는 다섯 — DSM-U4-01(부분)·U4-03·U4-04(부분)·U4-07(부분)·U5-05(부분)
-------------------------------------------------------------------------------
전부 신설 서비스(`apps/dsm/situation_report_ledger_service.py` ·
`cbs_draft_service.py` · `control_board_service.py` · `video_access_ledger_service.py` ·
`shift_roster_service.py`)를 얇게 여는 자리다 — 값 판정·감사 규약은 그 서비스들이
갖고 있고, 이 파일은 스키마 검증 + 예외 → HTTP 상태 번역만 한다
(`api_u24.py` 와 같은 규약).

★ `api_u24.py`·`api_u1.py`·`api_u3.py`·`api_u56.py`(N1·기존 차선 소유)는
**손대지 않는다** — 새 경로는 이 파일 하나에 산다. `backend/apps/dsm/urls.py` 에
컨트롤러 등록 한 줄만 더한다(다른 컨트롤러 **뒤**에 — 선언 순서가 곧 라우팅).

★ `from __future__ import annotations` 를 **일부러 쓰지 않는다** — `api_u24.py`
머리말과 같은 사유(D-378, `@tenant_scoped` 로 감싼 핸들러의 주석이 그 데코레이터
모듈의 `__globals__` 에서 풀린다).

★ 경로 겹침 없음 [실측] — 이 파일의 리터럴(`situation-reports` · `cbs-drafts` ·
  `control-points` · `video-access-requests` · `shifts`·`shifts/import`)은
  `api.py`·`api_u1.py`·`api_u3.py`·`api_u24.py`·`api_u56.py`·`law_api.py`·
  `api_f.py`·`api_f_ops.py` 어디에도 없다(grep 전수).
"""
from ninja import Schema
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.idempotency import idempotent
from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import SystemScopeCannotRead, TenantScope, tenant_scoped

from apps.dsm import (cbs_draft_service, control_board_service, shift_roster_service,
                     situation_report_ledger_service, video_access_ledger_service)


def _scope(request) -> TenantScope:
    """요청자에서 스코프를 만든다. **없으면 401.** `api_u24.py::_scope` 와 같은 규약."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


# ═══════════════════════════════════════════════════════════════════════════
# 입력 스키마 — 전부 JSON 본문(사람이 쓴 글·목록형 값이 있어 질의 문자열로 받지 않는다,
# `api_u24.py::ReportRunIn` 머리말과 같은 이유).
# ═══════════════════════════════════════════════════════════════════════════
class SituationReportIssueIn(Schema):
    event_id: int
    kind: str


class SituationReportSentIn(Schema):
    recipient: str = ""
    sent_at: str | None = None


class CbsDraftIn(Schema):
    kind: str
    region: str
    #: [턴 AN · P-392] 비우면(기본값) 표준 문안이 자동으로 채워진다
    #: (`u4_regulations.CBS_STANDARD_TEMPLATE` · `cbs_draft_service.create_draft`).
    message: str = ""
    occurred_at: str | None = None


class CbsDraftApproveIn(Schema):
    note: str = ""


class CbsDraftSentIn(Schema):
    sent_at: str | None = None
    channel_ref: str = ""


class ControlPointIn(Schema):
    name: str
    reached_at: str | None = None
    evacuee_count: int | None = None
    evacuation_site: str = ""


class ControlAdvanceIn(Schema):
    stage: str
    when: str | None = None
    note: str = ""


class VideoAccessRequestIn(Schema):
    requester_org: str
    doc_no: str
    purpose: str
    scope_desc: str = ""
    camera_id: int | None = None
    event_id: int | None = None


class VideoAccessApproveIn(Schema):
    note: str = ""


class VideoAccessProvideIn(Schema):
    method: str = ""
    #: [턴 AN · P-392] 비우면 이전과 같다(마스킹 없음). 채우면 실제로 마스킹
    #: 파이프라인을 돌린다(`video_access_ledger_service.provide`).
    image_b64: str = ""


class ShiftImportIn(Schema):
    csv_text: str


@api_controller("", tags=["DSM — U4 재난안전과 담당 (WO-15 §5 차선 N4 · 턴 AM)"])
class DsmU4API:
    """N4 차선의 새 라우트 — DSM-U4-01(부분)·U4-03·U4-04(부분)·U4-07(부분)·
    U5-05(부분). 무엇이 부분인지는 각 서비스 파일 머리말 · N4_promotions.md."""

    # ══════════════════════════════════════════════════════════════════════
    # DSM-U4-01 재난상황보고서 제N보 채번 대장
    # ══════════════════════════════════════════════════════════════════════
    @route.post("/situation-reports", auth=JwtOrInboundKey())
    @tenant_scoped(reason="상황보고서 채번 — 남의 테넌트 감사에 남으면 격리 실패다")
    @idempotent("dsm.u4.situation_reports.issue")
    def issue_situation_report(self, request, payload: SituationReportIssueIn):
        """`POST /situation-reports` — 사건의 제N보를 하나 채번한다(최초/중간/최종)."""
        from django.http import Http404

        try:
            return situation_report_ledger_service.issue_report(
                scope=_scope(request), event_id=payload.event_id, kind=payload.kind)
        except ValueError as exc:
            raise HttpError(400, str(exc))
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except situation_report_ledger_service.SituationReportRejected as exc:
            raise HttpError(422, str(exc))

    @route.post("/situation-reports/{int:report_id}/sent", auth=JwtOrInboundKey())
    @tenant_scoped(reason="상황보고서 발송 기록 — 남의 테넌트 채번을 건드릴 수 없다")
    @idempotent("dsm.u4.situation_reports.sent")
    def situation_report_sent(self, request, report_id: int,
                              payload: SituationReportSentIn):
        """`POST /situation-reports/{id}/sent` — 발송 시각·수신처 기록."""
        from django.http import Http404

        try:
            return situation_report_ledger_service.mark_sent(
                scope=_scope(request), report_id=report_id,
                recipient=payload.recipient, sent_at=payload.sent_at)
        except ValueError as exc:
            raise HttpError(400, str(exc))
        except Http404:
            raise HttpError(404, "그런 상황보고서 채번 기록이 없습니다.")
        except situation_report_ledger_service.SituationReportConflict as exc:
            raise HttpError(409, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    @route.get("/situation-reports", auth=JwtOrInboundKey())
    @tenant_scoped(reason="상황보고서 채번 열람 — 남의 테넌트 감사가 보이면 격리 실패다")
    def list_situation_reports(self, request, event_id: int | None = None,
                               limit: int = 100):
        """`GET /situation-reports` — 채번 이력(최신 먼저)."""
        try:
            return situation_report_ledger_service.list_reports(
                scope=_scope(request), event_id=event_id, limit=limit)
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ══════════════════════════════════════════════════════════════════════
    # DSM-U4-03 재난문자(CBS) 초안
    # ══════════════════════════════════════════════════════════════════════
    @route.post("/cbs-drafts", auth=JwtOrInboundKey())
    @tenant_scoped(reason="CBS 초안 — 남의 테넌트 감사에 남으면 격리 실패다")
    @idempotent("dsm.u4.cbs_drafts.create")
    def create_cbs_draft(self, request, payload: CbsDraftIn):
        """`POST /cbs-drafts` — 유형·구역·문안 → 글자수 검사(90/157) → 초안."""
        try:
            return cbs_draft_service.create_draft(
                scope=_scope(request), kind=payload.kind, region=payload.region,
                message=payload.message, occurred_at=payload.occurred_at)
        except ValueError as exc:
            raise HttpError(400, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except cbs_draft_service.CbsDraftRejected as exc:
            raise HttpError(422, str(exc))

    @route.post("/cbs-drafts/{int:draft_id}/approve", auth=JwtOrInboundKey())
    @tenant_scoped(reason="CBS 초안 승인 — 남의 테넌트 초안을 승인할 수 없다")
    @idempotent("dsm.u4.cbs_drafts.approve")
    def approve_cbs_draft(self, request, draft_id: int, payload: CbsDraftApproveIn):
        """`POST /cbs-drafts/{id}/approve` — 승인권자 결재."""
        from django.http import Http404

        try:
            return cbs_draft_service.approve_draft(
                scope=_scope(request), draft_id=draft_id, note=payload.note)
        except Http404:
            raise HttpError(404, "그런 재난문자 초안이 없습니다.")
        except cbs_draft_service.CbsDraftConflict as exc:
            raise HttpError(409, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    @route.post("/cbs-drafts/{int:draft_id}/sent", auth=JwtOrInboundKey())
    @tenant_scoped(reason="CBS 발송 기록 — 남의 테넌트 초안을 건드릴 수 없다")
    @idempotent("dsm.u4.cbs_drafts.sent")
    def cbs_draft_sent(self, request, draft_id: int, payload: CbsDraftSentIn):
        """`POST /cbs-drafts/{id}/sent` — 행안부 시스템에서 실제로 보낸 뒤의 발송 기록
        (이 제품이 발송하지 않는다 — 명세 그대로)."""
        from django.http import Http404

        try:
            return cbs_draft_service.mark_sent(
                scope=_scope(request), draft_id=draft_id, sent_at=payload.sent_at,
                channel_ref=payload.channel_ref)
        except ValueError as exc:
            raise HttpError(400, str(exc))
        except Http404:
            raise HttpError(404, "그런 재난문자 초안이 없습니다.")
        except cbs_draft_service.CbsDraftConflict as exc:
            raise HttpError(409, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    @route.get("/cbs-drafts", auth=JwtOrInboundKey())
    @tenant_scoped(reason="CBS 초안 열람 — 남의 테넌트 감사가 보이면 격리 실패다")
    def list_cbs_drafts(self, request, limit: int = 100):
        """`GET /cbs-drafts` — 초안마다 지금 상태(초안/승인/발송)."""
        try:
            return cbs_draft_service.list_drafts(scope=_scope(request), limit=limit)
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ══════════════════════════════════════════════════════════════════════
    # DSM-U4-04 통제·대피 현황판
    # ══════════════════════════════════════════════════════════════════════
    @route.post("/control-points", auth=JwtOrInboundKey())
    @tenant_scoped(reason="통제 지점 등록 — 남의 테넌트 감사에 남으면 격리 실패다")
    @idempotent("dsm.u4.control_points.create")
    def create_control_point(self, request, payload: ControlPointIn):
        """`POST /control-points` — 통제 개소 등록(=도달 시각)."""
        try:
            return control_board_service.create_point(
                scope=_scope(request), name=payload.name,
                reached_at=payload.reached_at, evacuee_count=payload.evacuee_count,
                evacuation_site=payload.evacuation_site)
        except ValueError as exc:
            raise HttpError(400, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except control_board_service.ControlPointRejected as exc:
            raise HttpError(422, str(exc))

    @route.post("/control-points/{int:point_id}/advance", auth=JwtOrInboundKey())
    @tenant_scoped(reason="통제 단계 전진 — 남의 테넌트 지점을 건드릴 수 없다")
    @idempotent("dsm.u4.control_points.advance")
    def advance_control_point(self, request, point_id: int,
                              payload: ControlAdvanceIn):
        """`POST /control-points/{id}/advance` — 결정/실행/해제 시각을 순서대로 남긴다."""
        from django.http import Http404

        try:
            return control_board_service.advance(
                scope=_scope(request), point_id=point_id, stage=payload.stage,
                when=payload.when, note=payload.note)
        except ValueError as exc:
            raise HttpError(400, str(exc))
        except Http404:
            raise HttpError(404, "그런 통제 지점이 없습니다.")
        except control_board_service.ControlPointOutOfOrder as exc:
            raise HttpError(409, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    @route.get("/control-points", auth=JwtOrInboundKey())
    @tenant_scoped(reason="통제·대피 현황판 — 남의 테넌트 지점이 보이면 격리 실패다")
    def list_control_points(self, request, limit: int = 200):
        """`GET /control-points` — 현황판: 지점마다 지금 단계."""
        try:
            return control_board_service.list_board(scope=_scope(request), limit=limit)
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── [턴 AN · P-392] DSM-U4-04 「일일보고 자동 반영」 반쪽 채움 ──────────
    @route.get("/control-points/daily-report", auth=JwtOrInboundKey())
    @tenant_scoped(reason="일일보고 반영 자료 — 남의 테넌트 통제 현황이 보이면 "
                          "격리 실패다")
    def control_points_daily_report(self, request, as_of: str | None = None):
        """`GET /control-points/daily-report` — 통제 현황을 일일상황보고가 그대로
        삼킬 수 있는 모양(기준 시각·단계별 집계·지점 목록)으로 자동 반영한다."""
        try:
            return control_board_service.daily_reflection(
                scope=_scope(request), as_of=as_of)
        except ValueError as exc:
            raise HttpError(400, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ══════════════════════════════════════════════════════════════════════
    # DSM-U4-07 영상 열람·제공(반출) 대장
    # ══════════════════════════════════════════════════════════════════════
    @route.post("/video-access-requests", auth=JwtOrInboundKey())
    @tenant_scoped(reason="영상 제공 요청 접수 — 남의 테넌트 감사에 남으면 격리 실패다")
    @idempotent("dsm.u4.video_access.create")
    def create_video_access_request(self, request, payload: VideoAccessRequestIn):
        """`POST /video-access-requests` — 수사기관 등 요청(공문번호·목적·범위) 접수."""
        try:
            return video_access_ledger_service.create_request(
                scope=_scope(request), requester_org=payload.requester_org,
                doc_no=payload.doc_no, purpose=payload.purpose,
                scope_desc=payload.scope_desc, camera_id=payload.camera_id,
                event_id=payload.event_id)
        except ValueError as exc:
            raise HttpError(400, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except video_access_ledger_service.VideoAccessRejected as exc:
            raise HttpError(422, str(exc))

    @route.post("/video-access-requests/{int:request_id}/approve",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="영상 제공 승인 — 남의 테넌트 요청을 승인할 수 없다")
    @idempotent("dsm.u4.video_access.approve")
    def approve_video_access_request(self, request, request_id: int,
                                     payload: VideoAccessApproveIn):
        """`POST /video-access-requests/{id}/approve` — 승인."""
        from django.http import Http404

        try:
            return video_access_ledger_service.approve_request(
                scope=_scope(request), request_id=request_id, note=payload.note)
        except Http404:
            raise HttpError(404, "그런 영상 제공 요청이 없습니다.")
        except video_access_ledger_service.VideoAccessConflict as exc:
            raise HttpError(409, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    @route.post("/video-access-requests/{int:request_id}/provide",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="영상 마스킹본 제공 기록 — 남의 테넌트 요청을 건드릴 수 없다")
    @idempotent("dsm.u4.video_access.provide")
    def provide_video_access(self, request, request_id: int,
                             payload: VideoAccessProvideIn):
        """`POST /video-access-requests/{id}/provide` — 마스킹본 제공 기록(원본 미반출)."""
        from django.http import Http404

        try:
            return video_access_ledger_service.provide(
                scope=_scope(request), request_id=request_id, method=payload.method,
                image_b64=payload.image_b64)
        except Http404:
            raise HttpError(404, "그런 영상 제공 요청이 없습니다.")
        except video_access_ledger_service.VideoAccessConflict as exc:
            raise HttpError(409, str(exc))
        except ValueError as exc:
            raise HttpError(400, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    @route.get("/video-access-requests", auth=JwtOrInboundKey())
    @tenant_scoped(reason="영상 제공 대장 열람 — 남의 테넌트 대장이 보이면 격리 실패다")
    def list_video_access_requests(self, request, limit: int = 200):
        """`GET /video-access-requests` — 대장 전체, 요청마다 지금 상태."""
        try:
            return video_access_ledger_service.list_requests(
                scope=_scope(request), limit=limit)
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── [턴 AO · P-407] DSM-U4-07 「연간 통계(출력)」 반쪽 채움 ──────────────
    @route.get("/video-access-requests/annual-stats", auth=JwtOrInboundKey())
    @tenant_scoped(reason="영상 제공 연간 통계 — 남의 테넌트 대장이 집계에 "
                          "섞이면 격리 실패다")
    def video_access_annual_stats(self, request, year: int | None = None):
        """`GET /video-access-requests/annual-stats` — 한 해의 요청·승인·제공
        건수와 월별 요청 건수(생략하면 올해)."""
        try:
            return video_access_ledger_service.annual_stats(
                scope=_scope(request), year=year)
        except ValueError as exc:
            raise HttpError(400, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ══════════════════════════════════════════════════════════════════════
    # DSM-U5-05 교대 편성(4조 3교대) CSV
    # ══════════════════════════════════════════════════════════════════════
    @route.post("/shifts/import", auth=JwtOrInboundKey())
    @tenant_scoped(reason="근무표 CSV 업로드 — 남의 테넌트 감사에 남으면 격리 실패다")
    @idempotent("dsm.u5.shifts.import")
    def import_shifts(self, request, payload: ShiftImportIn):
        """`POST /shifts/import` — 4조 3교대 근무표 CSV(`date,team,shift,members`)."""
        try:
            return shift_roster_service.import_csv(
                scope=_scope(request), csv_text=payload.csv_text)
        except ValueError as exc:
            raise HttpError(400, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except shift_roster_service.ShiftRosterRejected as exc:
            raise HttpError(422, str(exc))

    @route.get("/shifts", auth=JwtOrInboundKey())
    @tenant_scoped(reason="근무표 열람 — 남의 테넌트 근무표가 보이면 격리 실패다")
    def list_shifts(self, request, date: str | None = None, limit: int = 500):
        """`GET /shifts` — 근무표 표. `date`(YYYY-MM-DD)로 좁힐 수 있다."""
        try:
            return shift_roster_service.list_roster(
                scope=_scope(request), date=date, limit=limit)
        except ValueError as exc:
            raise HttpError(400, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ── [턴 AN · P-392] DSM-U5-05 「인계 메모·일지의 근무자 자동」 반쪽 채움 ──
    @route.get("/shifts/on-duty", auth=JwtOrInboundKey())
    @tenant_scoped(reason="근무자 자동 조회 — 남의 테넌트 근무표가 보이면 격리 "
                          "실패다")
    def shifts_on_duty(self, request, date: str | None = None):
        """`GET /shifts/on-duty` — 이 날짜(생략하면 오늘)의 조별 근무자를
        편성표에서 그대로 구조화해 낸다(인계 메모·관제일지가 삼킬 자료)."""
        try:
            return shift_roster_service.current_workers(
                scope=_scope(request), date=date)
        except ValueError as exc:
            raise HttpError(400, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
