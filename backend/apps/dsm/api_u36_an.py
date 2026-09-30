# -*- coding: utf-8 -*-
"""DSM U3-01·U3-02·U6-01·U6-03 (+U4 잔여 S) · 명세 제목이 정본.

턴 AO · WO-18 · 차선 N4 단독 소유 파일(조율자가 빈 컨트롤러로 세워 `urls.py` 에 등록해 둠).
★ `from __future__ import annotations` 를 쓰지 않는다(D-378 — `api_u4.py` 머리말과 같은
  사유, `@tenant_scoped` 로 감싼 핸들러의 주석이 그 데코레이터 모듈의 `__globals__` 에서
  풀린다).

이 파일이 여는 넷 — DSM-U3-01·U3-02·U6-01·U6-03
-------------------------------------------------
    U3-01  GET  /events/{id}/m2-brief         역할별 M2 문안(`u36_an_service.m2_brief`)
    U3-02  POST /controls/{id}/executed       통제 실행 회신 — **로직은 이 파일에 없다**,
                                              `control_board_service.advance(stage="실행")`
                                              를 새 리터럴로 여는 것뿐이다(두 번째 판정식을
                                              짓지 않는다 · U4-04 가 이미 4단계를 판정한다).
    U6-01  POST /external-events               스마트시티 통합플랫폼·112·119 이벤트 연계
    U6-03  POST /search-requests                사회적약자(실종) 요청 수신 → 사건 1

★ 경로 겹침 없음 [실측 — grep 전수] `/events/{int:event_id}/m2-brief`·
  `/controls/{int:point_id}/executed`·`/external-events`·`/search-requests` 넷 다
  `api.py`·`api_f.py`·`api_f_ops.py`·`api_u1.py`·`api_u3.py`·`api_u4.py`·`api_u24.py`·
  `api_u56.py`·`api_u5_perm.py`·`api_u5_an.py`·`api_ops_an.py`·`law_api.py` 리터럴 전수
  밖이다 — `m2-brief`·`executed`는 기존 어느 라우트의 마지막 조각과도 안 겹치는 새
  리터럴이고, `/external-events`·`/search-requests`는 최상위 새 리터럴이라 기존
  `{int:...}` 변수 조각이 삼킬 자리가 아니다.

★ 새 `/api/dsm/` 라우트는 `tests/test_f05_event_api.py::EVENT_ENTRY_SURFACE` 에 아직
  없다 — 그 파일은 조율자 몫이라 이 파일이 고치지 않는다(최종 보고에 (METHOD, path)
  넷을 옮겨 적는다).
"""
from ninja import Schema
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.idempotency import idempotent
from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import SystemScopeCannotRead, TenantScope, tenant_scoped

from apps.dsm import control_board_service, services, u36_an_service
from apps.dsm.u4_regulations import CONTROL_STAGE_EXECUTED


def _scope(request) -> TenantScope:
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


class ControlExecutedIn(Schema):
    when: str | None = None
    note: str = ""


class SearchRequestIn(Schema):
    requester_agency: str
    subject_description: str
    last_seen_stream_monitor_id: int
    last_seen_at: str | None = None
    contact: str = ""


@api_controller("", tags=["DSM — U3·U6 (턴 AO · N4)"])
class DsmU36AnAPI:
    # ═══════════════════════════════════════════════════════════════════
    # DSM-U3-01 — 역할별 M2 문안
    # ═══════════════════════════════════════════════════════════════════
    @route.get("/events/{int:event_id}/m2-brief", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U3-01 M2 문안 — 남의 테넌트 이벤트의 유형이 보이면 격리 실패다")
    def m2_brief(self, request, event_id: int, role: str):
        """`GET /events/{id}/m2-brief?role=<role>` — M2 상단 한 줄."""
        try:
            return u36_an_service.m2_brief(
                scope=_scope(request), event_id=event_id, role=role)
        except u36_an_service.M2RoleUnknown as exc:
            raise HttpError(422, str(exc))

    # ═══════════════════════════════════════════════════════════════════
    # DSM-U3-02 — 통제 실행 회신 (U4-04 통제 지점 표의 「실행」 단계를 새 리터럴로 연다)
    # ═══════════════════════════════════════════════════════════════════
    @route.post("/controls/{int:point_id}/executed", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U3-02 통제 실행 회신 — 남의 테넌트 통제 지점에 실행 시각을 "
                          "남기면 격리 실패다")
    @idempotent("dsm.u36.controls.executed")
    def control_executed(self, request, point_id: int, payload: ControlExecutedIn):
        """`POST /controls/{id}/executed` — 「통제 완료」 버튼. **도달·결정을 먼저**
        거친 지점에만 실행 시각을 남길 수 있다(`control_board_service.advance` 의
        기존 순서 검사 그대로 — 새 문지기를 짓지 않는다)."""
        from django.http import Http404

        try:
            return control_board_service.advance(
                scope=_scope(request), point_id=point_id,
                stage=CONTROL_STAGE_EXECUTED, when=payload.when, note=payload.note)
        except ValueError as exc:
            raise HttpError(422, str(exc))
        except Http404:
            raise HttpError(404, "그런 통제 지점이 없습니다.")
        except control_board_service.ControlPointOutOfOrder as exc:
            raise HttpError(409, str(exc))
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))

    # ═══════════════════════════════════════════════════════════════════
    # DSM-U6-01 — 스마트시티 통합플랫폼 이벤트 연계 (F-05 읽기 문의 짝 · 쓰기 1)
    # ═══════════════════════════════════════════════════════════════════
    #: ★ [P-427 · 턴 AO→AP · 세종 판정 · 조율자 E] 인증 = **들어오는 키 + HMAC**.
    #:   외부 기관 시스템에는 사람 로그인이 없다 — JWT 로 받으면 사람 세션을 흉내 내야 한다.
    #:   쓰기 문에 들어오는 키를 여는 것은 D-335 ③ 래칫의 **결정 번호 붙은 예외 하나**다
    #:   (`tests/test_f05_inbound_api_key.py::DECIDED_INBOUND_WRITES`) — 계약 절(DSM-U6-01)이
    #:   외부의 쓰기를 부르기 때문이다. 키가 테넌트를 정하고, 서명(웹훅 서명키 `agency`
    #:   재사용 · 새 자격 0)이 위조를, 시각 창 5분(`webhook_contract.TIMESTAMP_TOLERANCE_SECONDS`)이
    #:   재생을 막는다. JWT 로 온 요청은 받지 않는다(아래 첫 줄).
    @route.post("/external-events", auth=JwtOrInboundKey(
        inbound_key=True, reason="P-427 DSM-U6-01 외부 이벤트 연계 — 계약이 부르는 쓰기 1"))
    @tenant_scoped(reason="U6-01 외부 이벤트 연계 — 들어오는 키의 테넌트로만 적립한다. "
                          "서명 검증(HMAC)이 위조를, 테넌트 스코프가 남의 카메라로의 "
                          "쓰기 IDOR 을 막는다")
    @idempotent("dsm.u36.external_events")
    def external_event_intake(self, request):
        """`POST /external-events` — 112 긴급영상·119 출동·재난상황 긴급대응
        (CAP 1.2). 본문은 JSON — 서명이 **그 원문 바이트**를 덮으므로 ninja 스키마로
        먼저 파싱하지 않는다(`request.body` 그대로 `u36_an_service` 에 넘긴다)."""
        from django.http import Http404

        from common.inbound_api_key import (
            carries_inbound_key, verify_signed_with_request_key,
        )

        if not carries_inbound_key(request):
            raise HttpError(401, "외부 이벤트 연계는 들어오는 키로만 받습니다(P-427).")
        try:
            return u36_an_service.intake_external_event(
                scope=_scope(request), headers=request.headers,
                raw_body=request.body,
                # [P-432] 서명 비밀 = 이 요청의 들어오는 키 — 값은 HTTP 층 밖으로 안 나간다
                verify_signature=lambda body, hdrs: verify_signed_with_request_key(
                    request, body, hdrs))
        except u36_an_service.ExternalEventRejected as exc:
            raise HttpError(401, str(exc))
        except u36_an_service.ExternalEventInvalid as exc:
            raise HttpError(422, str(exc))
        except services.InvalidEventInput as exc:
            raise HttpError(422, str(exc))
        except Http404:
            raise HttpError(404, "그런 카메라(stream_monitor_id)가 없습니다.")

    # ═══════════════════════════════════════════════════════════════════
    # DSM-U6-03 — 사회적약자(실종) 요청 수신 → 객체 검색 사건 생성
    # ═══════════════════════════════════════════════════════════════════
    @route.post("/search-requests", auth=JwtOrInboundKey())
    @tenant_scoped(reason="U6-03 실종 수색 요청 — 남의 테넌트로 사건이 적립되면 격리 "
                          "실패다. 카메라도 요청자 테넌트 것이어야 한다")
    @idempotent("dsm.u36.search_requests")
    def search_request_intake(self, request, payload: SearchRequestIn):
        """`POST /search-requests` — 완결조건 "요청 → 사건 1". **재식별(용모 기반
        객체 검색) AI 는 짓지 않는다** — 이 문이 남기는 것은 수색의 출발점이 되는
        사건 하나와 감사 줄 하나다(왜: `u36_an_service` 머리말 · 최종 보고 참고)."""
        from django.http import Http404

        try:
            return u36_an_service.intake_search_request(
                scope=_scope(request), requester_agency=payload.requester_agency,
                subject_description=payload.subject_description,
                last_seen_stream_monitor_id=payload.last_seen_stream_monitor_id,
                last_seen_at=payload.last_seen_at, contact=payload.contact)
        except u36_an_service.SearchRequestInvalid as exc:
            raise HttpError(422, str(exc))
        except services.InvalidEventInput as exc:
            raise HttpError(422, str(exc))
        except Http404:
            raise HttpError(404, "그런 카메라(stream_monitor_id)가 없습니다.")
