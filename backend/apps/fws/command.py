# -*- coding: utf-8 -*-
"""FWS-F4-01~15 — 통합지휘본부장·상황실(F4) (턴 AO · WO-18 §5 P-414 · 차선 N2).

세종 판정 P-414 — F4 는 DSM 을 재사용한다(두 번째 상태기계·표를 짓지 않는다)
--------------------------------------------------------------------------
    F4-10 대응 시계    `apps.dsm.services.response_clock`(UX-14) 그대로 +
                        이 파일이 얹는 두 칸(헬기 투하·주불 — K1 에 없는 칸)
    F4-12 회의 기록    `apps.dsm.situation_meeting_service`(DSM-U2-03) 그대로 —
                        사건과 묶는 자리만 결정문 앞 `[사건N]` 표로 더한다
                        (새 칸이 아니라 그 모듈의 `decision` 문자열 자리를 쓴다)
    F4-07 진화완료     `apps.dsm.services.advance_response`(K1 종결 축, `closed`)
                        그대로 — "주불"은 K1 에 없는 칸이라 감사 한 줄로 남긴다
    F4-02 지휘권 이양   새 표 0 — `command_level` 칸은 이 파일의 감사 한 줄
                        (office.py 의 감사-한-줄 관례와 같다)

이 파일이 F3(`office.py`·`office2.py`)·F6(`integration.py`) 문을 재사용하는 곳
-----------------------------------------------------------------------------
    F4-04 헬기 요청 승인    `integration.request_helicopter`(F6-05) 그대로 부른다
                            — 이 파일이 더하는 것은 지휘부 승인 + 30분 시계뿐
                            (`office2.GOLDEN_TIME_THRESHOLD_SEC` 재사용 — 30분을
                            다시 적지 않는다)
    F4-05 대피 명령 승인    `office2.draft_evacuation_plan`(F3-11)이 이미 지은
                            CBS 초안을 승인 상태로 확정한다 — 문안을 다시 안 짓는다
    F4-08 상황보고 승인     `office2.hourly_reports`(F3-13)의 초안을 승인한다 —
                            초안 계산을 다시 안 한다
    F4-09 연락(1클릭)       `apps.fws.contacts`(F1-08) 그대로 — 산림청 번호를
                            다시 적지 않는다
    F4-15 사후 보고서 PDF   `apps.dsm.services.incident_report`(UX-30) 그대로 —
                            PDF 렌더를 두 벌로 짓지 않는다

정직하게 좁힌 자리 — D-284(지어내지 않는다)
--------------------------------------------
· **F4-01 지휘 화면·F4-09 연락**의 "지도·화선"·"화상"은 이 파일이 짓지 않는다.
  화선(확산 경계) 데이터 자체가 이 저장소에 없고(F3-10 확산예측 미착수와 같은
  이유), 화상회의 인프라도 이 저장소 전체에 없다(공통 한계). 지도 렌더는 §0.4
  인접 금지구역(MapForRoute*·FormRoute.tsx) 밖이라 애초에 손대지 않는다.
  그래서 이 두 절의 계약을 **완결조건(§5.4 표 마지막 열)으로 좁힌다** — F4-01
  은 "한 화면"(사건개요·단계·자원·시계·대피를 한 응답으로), F4-09 는 "1클릭"
  (전화 — 산림청 소스값 + 시도 상황실은 F4-03 에 실제로 등록된 값이 있을 때만,
  없으면 정직하게 null).
· **F4-11 야간 전환**은 일몰 시각 계산기를 갖지 않는다(office2.py F3-14 의
  sunrise/sunset 과 같은 한계) — 실측 일몰 시각을 입력으로 받는다.
· **F4-14(진화완료 후 드론 순회 감시 계획)는 이 파일이 짓지 않는다** — L 규모,
  `scripts/verify_spec_fws_f4.py` 의 「무엇이 없는가」를 본다.

새 표는 0 — 전부 `logger.AuditLogs` 감사 한 줄(office.py·office2.py 와 같은 관례).
"""
from __future__ import annotations

from datetime import timedelta

from django.apps import apps
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from common import audit_writer

#: ★ F-05 잠금 — K1 을 직접 부르지 않는다. `apps.dsm.services` 가 유일한 문이다.
from apps.dsm import services as dsm_services
from apps.dsm.services import (
    ResponseTransitionForbidden,
    ResponseTransitionNeedsManager,
    ResponseTransitionNeedsReason,
)
#: ★ D-278 — 커널의 공개 면(예외 클래스)만 가져온다. `office.py` 와 같은 자리.
from kernels.k2_notify import NoRecipients

#: ★ P-414 — DSM-U2-03(상황판단회의)을 그대로 재사용한다(F4-12). D-278 ④ — DSM 내부 모듈이 아니라
#:   `apps.dsm.services` 의 경유 문으로 부른다(턴 AO 조율자 병합).
from apps.dsm import services as dsm_meeting_gate

from apps.fws import constants as fws_constants
from apps.fws import contacts as fws_contacts
from apps.fws import integration as fws_integration
from apps.fws import office as fws_office
from apps.fws import office2 as fws_office2

LOGGER_NAME = "guardianx.fws.command"
TAG = "[FWS-F4]"

MAX_NOTE_CHARS = 300
MAX_TEXT_CHARS = 200
MAX_PHONE_CHARS = 40

#: 회의 기록(F4-12)을 사건과 묶는 표 — U2-03 의 `decision` 문자열 앞에 붙인다.
_EVENT_TAG_FMT = "[사건{event_id}]"

#: 진행 중으로 보는 대응 상태 — `office.py::_ACTIVE_RESPONSE_STATES` 와 같은
#: 값(K1 `STATES` 중 `closed` 를 뺀 셋)이다. 그 모듈의 "_" 이름을 이 파일이
#: 끌어다 쓰지 않고(다른 차선 파일의 사적 이름에 기대지 않는다) 같은 값을
#: 여기 다시 이름 짓는다 — 값의 출처는 K1 `response_flow.STATES` 하나다.
_ONGOING_RESPONSE_STATES = ("occurred", "acknowledged", "in_progress")


class CommandInputRejected(Exception):
    """값이 계약 밖이다 — 422."""


def _model():
    return apps.get_model("logger", "AuditLogs")


def _write(actor, action: str, payload: dict, reason: str):
    return audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=action,
        outcome=audit_writer.ALLOWED, reason=reason, after=payload,
        api_name=action, api_method="POST")


def _now():
    return timezone.now()


def _now_iso() -> str:
    return _now().isoformat()


def _iso(value):
    """datetime(-like) 값만 ISO 문자열로 — `response_clock` 의 `as_dict()` 는
    시각 옆에 `event_id`(int)·`acknowledge_seconds`(float)·`transitions`(list)
    같은 non-datetime 칸도 함께 낸다(P-125 실측 — 값을 가리지 않고 그대로
    옮긴다, D-284). `isoformat` 이 없는 값은 그대로 돌려준다."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _aware(parsed):
    if parsed is not None and timezone.is_naive(parsed):
        return timezone.make_aware(parsed)
    return parsed


def _rows_for_event(action: str, event_id: int):
    """이 사건에 달린 이 파일의 기록 전부 — `office.py::_rows_for_event` 와 같은
    문지기(부르는 쪽이 **먼저** `dsm_services.event_detail` 로 자격을 확인받는다)."""
    qs = _model()._base_manager.filter(
        logger_name=LOGGER_NAME, api_name=action).order_by("id")
    out = []
    for row in qs:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        if payload.get("event_id") == event_id:
            out.append(row)
    return out


def _items_for_event(action: str, event_id: int) -> list:
    return [r.data_after for r in _rows_for_event(action, event_id)
           if isinstance(r.data_after, dict)]


def _latest_for_event(action: str, event_id: int):
    items = _items_for_event(action, event_id)
    return items[-1] if items else None


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-02 대응단계 확정·상향(사유) · 지휘권 이양 기록(시군구→시도)
# ═══════════════════════════════════════════════════════════════════════════
ACTION_STAGE_CONFIRM = "command.stage.confirm"

COMMAND_LEVEL_MUNICIPAL = "시군구"
COMMAND_LEVEL_PROVINCIAL = "시도"
COMMAND_LEVELS = (COMMAND_LEVEL_MUNICIPAL, COMMAND_LEVEL_PROVINCIAL)


def confirm_stage(*, scope, event_id: int, stage: str, reason: str,
                  command_level: str = "") -> dict:
    """F4-02 — 단계 값은 `fws_constants.FIRE_STAGES`(F3-09 가 이미 쓰는 표)를
    그대로 쓴다(D-212). 지휘권 이양은 새 표를 두지 않는다(P-414) — 이 함수의
    감사 한 줄 `command_level` 칸이 그 기록이다."""
    if stage not in fws_constants.FIRE_STAGES:
        raise CommandInputRejected(
            f"stage={stage!r} 는 대응단계가 아니다. 허용: {fws_constants.FIRE_STAGES}")
    reason = (reason or "").strip()
    if not reason:
        raise CommandInputRejected(
            "reason(사유)이 비었다 — 단계 확정·상향은 사유 없이 남길 수 없다")
    if len(reason) > MAX_NOTE_CHARS:
        raise CommandInputRejected(f"reason 이 {len(reason)}자다. 상한은 {MAX_NOTE_CHARS}자")
    if command_level and command_level not in COMMAND_LEVELS:
        raise CommandInputRejected(
            f"command_level={command_level!r} 은 지휘 수준이 아니다. 허용: {COMMAND_LEVELS}")

    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    actor = scope.require_actor()
    prior = _latest_for_event(ACTION_STAGE_CONFIRM, event_id)
    prior_stage = prior.get("stage") if prior else None

    payload = {
        "event_id": event_id, "stage": stage, "prior_stage": prior_stage,
        "reason": reason, "command_level": command_level or None,
        "confirmed_at": _now_iso(), "confirmed_by": getattr(actor, "username", ""),
    }
    entry = _write(actor, ACTION_STAGE_CONFIRM, payload,
                  f"대응단계 확정 {prior_stage or '(없음)'}→{stage}"
                  + (f" · 지휘권 이양 {command_level}" if command_level else ""))
    return {"confirmation_id": entry.audit_id, **payload}


def stage_history(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    items = _items_for_event(ACTION_STAGE_CONFIRM, event_id)
    return {"event_id": event_id, "count": len(items), "history": items,
           "current": items[-1] if items else None}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-03 통합지휘본부 설치 선언(위치·구성)
# ═══════════════════════════════════════════════════════════════════════════
ACTION_COMMAND_POST = "command.post.declare"
MAX_ADDRESS_CHARS = 200


def declare_command_post(*, scope, event_id: int, address: str,
                         org_composition: str = "",
                         situation_room_phone: str = "", note: str = "") -> dict:
    """F4-03 — 위치는 **주소 문자열**로만 받는다. 지도 렌더는 §0.4 인접
    금지구역(MapForRoute*·FormRoute.tsx) 밖이라 이 파일이 짓지 않는다 —
    좌표가 아니라 사람이 읽는 주소 한 줄이 계약이다."""
    address = (address or "").strip()
    if not address:
        raise CommandInputRejected(
            "address(위치)가 비었다 — 어디에 설치했는지 없이는 선언이 뜻을 갖지 못한다")
    if len(address) > MAX_ADDRESS_CHARS:
        raise CommandInputRejected(f"address 가 {len(address)}자다. 상한은 {MAX_ADDRESS_CHARS}자")
    org_composition = (org_composition or "").strip()[:MAX_TEXT_CHARS]
    situation_room_phone = (situation_room_phone or "").strip()[:MAX_PHONE_CHARS]
    note = (note or "").strip()[:MAX_NOTE_CHARS]

    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    actor = scope.require_actor()
    payload = {
        "event_id": event_id, "address": address, "org_composition": org_composition,
        "situation_room_phone": situation_room_phone or None, "note": note,
        "declared_at": _now_iso(), "declared_by": getattr(actor, "username", ""),
    }
    entry = _write(actor, ACTION_COMMAND_POST, payload,
                  f"통합지휘본부 설치 선언 · {address}")
    return {"post_id": entry.audit_id, **payload}


def command_post(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    latest = _latest_for_event(ACTION_COMMAND_POST, event_id)
    return {"event_id": event_id, "declared": latest is not None, "post": latest}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-04 헬기 요청 승인·투하 구역 지정 (30분 시계)
# ═══════════════════════════════════════════════════════════════════════════
ACTION_HELI_APPROVE = "command.helicopter.approve"


def approve_helicopter_request(*, scope, event_id: int, requesting_org: str,
                               drop_zone_lat: float, drop_zone_lng: float,
                               base: str = "", eta: str = "", note: str = "") -> dict:
    """F4-04 — 실제 발송은 F6-05 문(`integration.request_helicopter`)을 그대로
    부른다(D-212, 두 번째 발송 경로를 열지 않는다). 이 함수가 더하는 것은
    지휘부의 **승인**과 **30분 골든타임 시계**뿐(`office2.
    GOLDEN_TIME_THRESHOLD_SEC` 재사용 — 30분을 다시 적지 않는다)."""
    try:
        request = fws_integration.request_helicopter(
            scope=scope, event_id=event_id, requesting_org=requesting_org,
            lat=drop_zone_lat, lng=drop_zone_lng, note=note)
    except fws_integration.LiaisonInputRejected as exc:
        raise CommandInputRejected(str(exc)) from exc

    actor = scope.require_actor()
    now = _now()
    deadline = now + timedelta(seconds=fws_office2.GOLDEN_TIME_THRESHOLD_SEC)
    payload = {
        "event_id": event_id, "request_id": request["request_id"],
        "requesting_org": requesting_org,
        "drop_zone": {"lat": drop_zone_lat, "lng": drop_zone_lng},
        "base": (base or "").strip()[:MAX_TEXT_CHARS], "eta": (eta or "").strip(),
        "approved_at": now.isoformat(), "deadline_at": deadline.isoformat(),
        "timeout_minutes": fws_office2.GOLDEN_TIME_THRESHOLD_SEC // 60,
    }
    entry = _write(actor, ACTION_HELI_APPROVE, payload,
                  f"헬기 요청 승인 · 투하구역({drop_zone_lat},{drop_zone_lng})")
    return {"approval_id": entry.audit_id, **payload}


def helicopter_status(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    items = _items_for_event(ACTION_HELI_APPROVE, event_id)
    return {"event_id": event_id, "count": len(items), "approvals": items}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-05 대피 명령 승인(즉시/준비) · 해제
# ═══════════════════════════════════════════════════════════════════════════
ACTION_EVAC_APPROVE = "command.evacuation.approve"
ACTION_EVAC_RELEASE = "command.evacuation.release"

EVAC_URGENCY_IMMEDIATE = "immediate"
EVAC_URGENCY_PREPARE = "prepare"
EVAC_URGENCIES = (EVAC_URGENCY_IMMEDIATE, EVAC_URGENCY_PREPARE)

_URGENCY_TO_KIND = {
    EVAC_URGENCY_IMMEDIATE: fws_constants.EVACUATION_KIND_ORDER,
    EVAC_URGENCY_PREPARE: fws_constants.EVACUATION_KIND_RECOMMEND,
}


def approve_evacuation(*, scope, event_id: int, urgency: str, note: str = "") -> dict:
    """F4-05 — F3-11(`office2.draft_evacuation_plan`)이 이미 지은 초안을
    **승인 상태로 확정**한다 — CBS 문안을 다시 짓지 않는다(D-212). 발송은
    `notify_event`(F1/F6 문 재사용)."""
    if urgency not in EVAC_URGENCIES:
        raise CommandInputRejected(
            f"urgency={urgency!r} 는 대피 긴급도가 아니다. 허용: {EVAC_URGENCIES}")
    note = (note or "").strip()[:MAX_NOTE_CHARS]

    status = fws_office2.evacuation_status(scope=scope, event_id=event_id)  # 404 게이트 겸함
    if not status["villages"]:
        raise CommandInputRejected("이 사건에 대피 초안(F3-11)이 없다 — 승인할 대상이 없다")

    kind = _URGENCY_TO_KIND[urgency]
    deadline_hours = fws_constants.evacuation_deadline_hours(kind)

    try:
        records = dsm_services.notify_event(scope=scope, event_id=event_id)
    except NoRecipients:
        records = ()

    actor = scope.require_actor()
    villages = [v["village"] for v in status["villages"]]
    payload = {
        "event_id": event_id, "urgency": urgency, "deadline_hours": deadline_hours,
        "villages": villages, "note": note, "approved_at": _now_iso(),
        "notified_count": len(records), "status": "approved",
    }
    entry = _write(actor, ACTION_EVAC_APPROVE, payload,
                  f"대피 명령 승인({urgency}) · {deadline_hours}시간 · 마을 {len(villages)}곳")
    return {"approval_id": entry.audit_id, **payload}


def release_evacuation(*, scope, event_id: int, reason: str) -> dict:
    reason = (reason or "").strip()
    if not reason:
        raise CommandInputRejected("reason(해제 사유)이 비었다")
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    actor = scope.require_actor()
    payload = {"event_id": event_id, "reason": reason, "released_at": _now_iso(),
              "status": "released"}
    entry = _write(actor, ACTION_EVAC_RELEASE, payload, f"대피 해제 · {reason}")
    return {"release_id": entry.audit_id, **payload}


def evacuation_command_status(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    approvals = _items_for_event(ACTION_EVAC_APPROVE, event_id)
    releases = _items_for_event(ACTION_EVAC_RELEASE, event_id)
    return {"event_id": event_id, "approvals": approvals, "releases": releases,
           "latest_approval": approvals[-1] if approvals else None,
           "latest_release": releases[-1] if releases else None}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-06 소방·경찰·군 협조 요청 기록
# ═══════════════════════════════════════════════════════════════════════════
ACTION_AGENCY_COORDINATION = "command.agency_coordination.record"

COORDINATION_AGENCY_FIRE = "fire_department"
COORDINATION_AGENCY_POLICE = "police"
COORDINATION_AGENCY_MILITARY = "military"
COORDINATION_AGENCIES = (COORDINATION_AGENCY_FIRE, COORDINATION_AGENCY_POLICE,
                        COORDINATION_AGENCY_MILITARY)


def record_agency_coordination(*, scope, event_id: int, agency: str,
                               request_detail: str = "", note: str = "") -> dict:
    """F4-06 — 산림청 통보(F3-07)·경찰 협조(F6-08)와는 **행위자가 다르다**(그쪽은
    각자의 각도 — 이 함수는 지휘부가 「요청했다」는 자기 기록, `office.py`
    F3-07 머리말과 같은 판단으로 옆에 둔다 — 새 문을 겹치지 않는다)."""
    if agency not in COORDINATION_AGENCIES:
        raise CommandInputRejected(
            f"agency={agency!r} 는 협조 기관이 아니다. 허용: {COORDINATION_AGENCIES}")
    request_detail = (request_detail or "").strip()[:MAX_NOTE_CHARS]
    note = (note or "").strip()[:MAX_NOTE_CHARS]
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    actor = scope.require_actor()
    payload = {
        "event_id": event_id, "agency": agency, "request_detail": request_detail,
        "note": note, "requested_at": _now_iso(),
        "requested_by": getattr(actor, "username", ""),
    }
    entry = _write(actor, ACTION_AGENCY_COORDINATION, payload, f"협조 요청 기록 · {agency}")
    return {"record_id": entry.audit_id, **payload}


def agency_coordination_records(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    items = _items_for_event(ACTION_AGENCY_COORDINATION, event_id)
    return {"event_id": event_id, "count": len(items), "records": items}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-07 주불 진화 선언 · 진화완료 선언
# ═══════════════════════════════════════════════════════════════════════════
ACTION_MAIN_FIRE_OUT = "command.fire.main_out_declare"
ACTION_EXTINGUISHED = "command.fire.extinguished_declare"


def declare_main_fire_out(*, scope, event_id: int, note: str = "") -> dict:
    """F4-07 전반 — 주불 진화 선언. K1 의 대응 축(`occurred→acknowledged→
    in_progress→closed`, `kernels.k1_event.response_flow.STATES`)에는 「주불」
    칸이 없다 — 그래서 이 선언은 **감사 한 줄**로 남긴다(K1 상태를 억지로
    하나 더 만들지 않는다, D-284). 다음 선언(진화완료)이 실제 종결 축을 옮긴다."""
    note = (note or "").strip()[:MAX_NOTE_CHARS]
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    actor = scope.require_actor()
    payload = {"event_id": event_id, "note": note, "declared_at": _now_iso(),
              "declared_by": getattr(actor, "username", "")}
    entry = _write(actor, ACTION_MAIN_FIRE_OUT, payload, "주불 진화 선언")
    return {"declaration_id": entry.audit_id, **payload}


def declare_extinguished(*, scope, event_id: int, reason: str = "") -> dict:
    """F4-07 후반 — 진화완료 선언 = **종결 축**(K1 `closed`)을 실제로 옮긴다
    (`dsm_services.advance_response` 재사용 — 두 번째 상태기계를 짓지 않는다)."""
    try:
        advanced = dsm_services.advance_response(
            scope=scope, event_id=event_id, to_state="closed", reason=reason or "")
    except (ResponseTransitionForbidden, ResponseTransitionNeedsReason,
           ResponseTransitionNeedsManager) as exc:
        raise CommandInputRejected(str(exc)) from exc

    actor = scope.require_actor()
    #: ★ K1 `advance_response` 의 반환 칸은 `to`다(`response_state` 가 아니다 —
    #:   `kernels.k1_event.response_flow.advance_response` 실측, 2026-09-30).
    payload = {"event_id": event_id, "reason": (reason or "").strip(),
              "declared_at": _now_iso(), "declared_by": getattr(actor, "username", ""),
              "response_state": advanced.get("to")}
    entry = _write(actor, ACTION_EXTINGUISHED, payload, "진화완료 선언")
    return {"declaration_id": entry.audit_id, **payload}


def fire_declarations(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    return {"event_id": event_id,
           "main_fire_out": _items_for_event(ACTION_MAIN_FIRE_OUT, event_id),
           "extinguished": _items_for_event(ACTION_EXTINGUISHED, event_id)}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-08 상황보고 승인(매시간)
# ═══════════════════════════════════════════════════════════════════════════
ACTION_HOURLY_APPROVE = "command.hourly_report.approve"


def approve_hourly_report(*, scope, event_id: int, hour: str = "", note: str = "") -> dict:
    """F4-08 — 초안은 F3-13 문(`office2.hourly_reports`)을 그대로 읽는다(D-212,
    두 번째 초안 계산을 짓지 않는다). F4-03 지휘소 선언이 있으면 그 값을
    승인 본문에 실어 **상황보고에 반영**한다(F4-03 완결조건 "상황보고 반영")."""
    drafts = fws_office2.hourly_reports(scope=scope, event_id=event_id)  # 404 게이트 겸함
    items = drafts["reports"]
    if not items:
        raise CommandInputRejected("승인할 매시간 상황보고 초안(F3-13)이 없다")
    if hour:
        target = next((d for d in items if d.get("hour") == hour), None)
        if target is None:
            raise CommandInputRejected(f"hour={hour!r} 초안이 없다")
    else:
        target = items[-1]

    post = _latest_for_event(ACTION_COMMAND_POST, event_id)

    try:
        records = dsm_services.notify_event(scope=scope, event_id=event_id)
    except NoRecipients:
        records = ()

    actor = scope.require_actor()
    payload = {
        "event_id": event_id, "hour": target["hour"], "approved_at": _now_iso(),
        "approved_by": getattr(actor, "username", ""),
        "note": (note or "").strip()[:MAX_NOTE_CHARS], "notified_count": len(records),
        "command_post_reflected": post,
    }
    entry = _write(actor, ACTION_HOURLY_APPROVE, payload,
                  f"상황보고 승인(매시간) · {target['hour']}")
    return {"approval_id": entry.audit_id, **payload}


def hourly_approvals(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    items = _items_for_event(ACTION_HOURLY_APPROVE, event_id)
    return {"event_id": event_id, "count": len(items), "approvals": items}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-09 산림청·시도 상황실 연락(1클릭)
# ═══════════════════════════════════════════════════════════════════════════
def contact_directory(*, scope, event_id: int) -> dict:
    """F4-09 — 완결조건(§5.4 표)은 "1클릭"이다. 산림청 번호는
    `apps.fws.contacts`(F1-08 문)를 그대로 재사용한다(다시 적지 않는다). 시도
    상황실 번호는 이 저장소가 임의로 짓지 않는다(D-284) — F4-03 지휘소
    선언에 실제로 입력된 값이 있을 때만 낸다(없으면 정직하게 null — 화상
    회의 인프라는 이 저장소 전체에 없고, 이 절은 전화 1클릭으로 계약을
    좁힌다)."""
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    forest = fws_contacts.emergency_contacts()["forest_report"]
    post = _latest_for_event(ACTION_COMMAND_POST, event_id)
    provincial = post.get("situation_room_phone") if post else None
    return {
        "event_id": event_id,
        "forest_service": {"phone": forest},
        "provincial_situation_room": {"phone": provincial},
    }


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-10 대응 시계 — 신고·확인·헬기 투하·주불·진화완료 + 골든타임 초과 사유
# ═══════════════════════════════════════════════════════════════════════════
ACTION_GOLDEN_TIME_REASON = "command.golden_time.exceeded_reason"


def response_timeline(*, scope, event_id: int) -> dict:
    """F4-10 — 기본 네 시각은 **DSM 대응 시계를 그대로 재사용**한다
    (`dsm_services.response_clock` — 세종 판정 P-414, 두 번째 시계를 짓지
    않는다): 신고=`occurred_at`(신고 접수 기록(F3-06)이 있으면 그 값으로
    바꿔 얹는다) · 확인=`acknowledged_at` · 진화완료=`closed_at`. 「헬기
    투하」·「주불」은 K1 에 없는 칸이라 이 App 층의 두 선언(F4-04·F4-07)에서
    얹는다."""
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    clock = dsm_services.response_clock(scope=scope, event_id=event_id)

    intake_items = fws_office.intake_records(scope=scope, event_id=event_id)["intakes"]
    reported_raw = intake_items[0]["clock_started_at"] if intake_items else clock.get("occurred_at")

    heli_items = _items_for_event(ACTION_HELI_APPROVE, event_id)
    heli_at = heli_items[0]["approved_at"] if heli_items else None

    main_out_items = _items_for_event(ACTION_MAIN_FIRE_OUT, event_id)
    main_out_at = main_out_items[0]["declared_at"] if main_out_items else None

    #: 골든타임(30분) 초과 여부 — `reported_raw` 를 aware datetime 으로 맞춘다.
    if isinstance(reported_raw, str):
        reported_dt = _aware(parse_datetime(reported_raw))
    else:
        reported_dt = reported_raw
    golden_seconds = fws_office2.GOLDEN_TIME_THRESHOLD_SEC
    over_golden_time = bool(
        reported_dt is not None and heli_at is None
        and (_now() - reported_dt).total_seconds() > golden_seconds)
    exceeded_reason = _latest_for_event(ACTION_GOLDEN_TIME_REASON, event_id)

    return {
        "event_id": event_id,
        "response_state": clock.get("response_state"),
        "timeline": {
            "reported_at": _iso(reported_raw),
            "acknowledged_at": _iso(clock.get("acknowledged_at")),
            "helicopter_dropped_at": heli_at,
            "main_fire_out_at": main_out_at,
            "extinguished_at": _iso(clock.get("closed_at")),
        },
        "golden_time_seconds": golden_seconds,
        "golden_time_exceeded": over_golden_time and exceeded_reason is None,
        "golden_time_exceeded_reason": exceeded_reason,
    }


def record_golden_time_exceeded_reason(*, scope, event_id: int, reason: str) -> dict:
    reason = (reason or "").strip()
    if not reason:
        raise CommandInputRejected("reason(골든타임 초과 사유)이 비었다")
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    actor = scope.require_actor()
    payload = {"event_id": event_id, "reason": reason, "recorded_at": _now_iso()}
    entry = _write(actor, ACTION_GOLDEN_TIME_REASON, payload, f"골든타임 초과 사유 · {reason}")
    return {"record_id": entry.audit_id, **payload}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-11 야간 전환(일몰) — 헬기 불가·야간 진화 자원 표시
# ═══════════════════════════════════════════════════════════════════════════
ACTION_SUNSET_SET = "command.night.sunset_set"

#: 야간 비행 제한(항공 규정 통상 관행) — 드론은 배정 종류에 있으므로 여기서
#: 가른다. 헬기는 별도 트랙(F4-04)이라 `night_status` 가 따로 표시한다.
NIGHT_UNAVAILABLE_RESOURCE_KINDS = (fws_office.RESOURCE_KIND_DRONE,)


def set_sunset(*, scope, event_id: int, sunset_at: str) -> dict:
    """F4-11 — 이 저장소는 일출몰 계산기를 갖지 않는다(office2.py F3-14 의
    sunrise/sunset 과 같은 한계) — 실측 일몰 시각을 **입력**으로 받는다
    (기상청 등 외부 출처, 지어내지 않는다 · D-284)."""
    sunset_at = (sunset_at or "").strip()
    if not sunset_at:
        raise CommandInputRejected("sunset_at 이 비었다")
    if parse_datetime(sunset_at) is None:
        raise CommandInputRejected(f"sunset_at 을 ISO 시각으로 읽지 못했다: {sunset_at!r}")
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    actor = scope.require_actor()
    payload = {"event_id": event_id, "sunset_at": sunset_at, "set_at": _now_iso()}
    entry = _write(actor, ACTION_SUNSET_SET, payload, f"일몰 시각 기록 · {sunset_at}")
    return {"record_id": entry.audit_id, **payload}


def night_status(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    latest = _latest_for_event(ACTION_SUNSET_SET, event_id)
    is_night = False
    sunset_at = None
    if latest:
        sunset_at = latest["sunset_at"]
        parsed = _aware(parse_datetime(sunset_at))
        if parsed is not None:
            is_night = _now() >= parsed

    assignments = fws_office.resource_assignments(scope=scope, event_id=event_id)["assignments"]
    night_resources = [{
        "resource_name": a.get("resource_name"), "kind": a.get("kind"),
        "available_at_night": a.get("kind") not in NIGHT_UNAVAILABLE_RESOURCE_KINDS,
    } for a in assignments]

    return {
        "event_id": event_id, "sunset_at": sunset_at, "is_night": is_night,
        "helicopter_badge": "헬기 불가" if is_night else "헬기 가능",
        "night_resources": night_resources,
    }


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-12 상황판단회의 기록 — DSM-U2-03 재사용 (P-414)
# ═══════════════════════════════════════════════════════════════════════════
def record_situation_meeting(*, scope, event_id: int, occurred_at: str = "",
                             attendees: str = "", decision: str = "",
                             basis: str = "") -> dict:
    """F4-12 — DSM-U2-03(`situation_meeting_service.record_meeting`)을 그대로
    재사용한다(세종 판정 P-414 — 두 번째 회의 기록 표를 짓지 않는다). U2-03
    은 회의를 **테넌트 단위**로 남긴다(사건과 안 묶는다) — 사건과 묶는 자리는
    결정문 앞에 `[사건N]` 표를 붙여 더한다(새 칸이 아니라 U2-03 의 `decision`
    문자열 자리를 쓴다 — 새 표 0)."""
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    decision = (decision or "").strip()
    if not decision:
        raise CommandInputRejected("decision(결정)이 비었다")
    tagged = f"{_EVENT_TAG_FMT.format(event_id=event_id)} {decision}"
    try:
        result = dsm_meeting_gate.record_situation_meeting(
            scope=scope, occurred_at=occurred_at or None, attendees=attendees,
            decision=tagged, basis=basis)
    except ValueError as exc:
        raise CommandInputRejected(str(exc)) from exc
    except dsm_meeting_gate.SituationMeetingRejected as exc:
        raise CommandInputRejected(str(exc)) from exc
    return {**result, "event_id": event_id, "decision": decision}


def situation_meetings(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    tag = _EVENT_TAG_FMT.format(event_id=event_id)
    items = []
    for row in dsm_meeting_gate.list_situation_meetings(scope=scope, limit=500):
        text = row.get("text") or ""
        if tag in text:
            items.append({**row, "text": text.replace(tag, "").strip()})
    return {"event_id": event_id, "count": len(items), "meetings": items}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-13 동시 다발 사건 우선순위(위험도 정렬)
# ═══════════════════════════════════════════════════════════════════════════
#: 위험도 정렬 — 이 App 은 사건별 위험도 점수 표를 따로 갖지 않는다(F3-01
#: 대시보드와 같은 한계) — 이미 있는 `severity`(경보 등급)로 정렬한다.
SEVERITY_RANK = {"critical": 3, "warning": 2, "info": 1}


def priority_queue(*, scope, limit: int = 50) -> dict:
    """F4-13 — annex 서버경로는 `GET /fws/incidents?sort=risk`. 진행 중(종결
    아님) 사건만 위험도(등급) 내림차순, 같은 등급이면 오래된 순으로 정렬한다."""
    events = dsm_services.recent_events(scope=scope, limit=max(limit, 200))
    ongoing = [e for e in events
              if (e.response_state or "occurred") in _ONGOING_RESPONSE_STATES]
    ranked = sorted(
        ongoing,
        key=lambda e: (-SEVERITY_RANK.get(e.severity, 0), e.occurred_at or _now()))
    items = [{
        "event_id": e.event_id, "severity": e.severity,
        "response_state": e.response_state,
        "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
        "address": e.address,
    } for e in ranked[:limit]]
    return {"count": len(items), "items": items}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-15 사후 보고서 1쪽(대응 시계·자원·대피·피해)
# ═══════════════════════════════════════════════════════════════════════════
def post_incident_report_pdf(*, scope, event_id: int) -> bytes:
    """F4-15 — **`dsm_services.incident_report`(UX-30)를 그대로 재사용**한다
    — 이미 사건 1건의 1쪽 PDF(사건개요·대응시계·판정·조치이력·피해현황)를
    낸다(D-212, PDF 렌더를 두 벌로 짓지 않는다)."""
    return dsm_services.incident_report(scope=scope, event_id=event_id)


def post_incident_summary(*, scope, event_id: int) -> dict:
    """F4-15 짝 — PDF 옆에 자원·대피 데이터를 더하는 JSON 요약. 피해 칸은
    `apps/dsm/incident_report.py::_damage_block` 과 같은 정직함을 지킨다 —
    이 저장소는 인명·재산 피해 집계 칸을 두지 않으므로 0 으로 지어내지 않고
    "집계 전"이라고 그대로 적는다."""
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    resources = fws_office.resource_assignments(scope=scope, event_id=event_id)
    evac = fws_office2.evacuation_status(scope=scope, event_id=event_id)
    clock = dsm_services.response_clock(scope=scope, event_id=event_id)
    return {
        "event_id": event_id,
        "response_clock": {k: _iso(v) for k, v in clock.items() if k != "response_state"},
        "response_state": clock.get("response_state"),
        "resources": resources["assignments"],
        "evacuation": {"total_villages": evac["total_villages"],
                      "percent_complete": evac["percent_complete"]},
        "damage": {"status": "집계 전",
                  "note": "이 저장소는 인명·재산 피해 집계 칸을 두지 않는다 — "
                          "현장 집계로 채운다(0 으로 지어내지 않는다)"},
    }


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-01 지휘 화면 — 사건 1건 전체를 한 화면으로
# ═══════════════════════════════════════════════════════════════════════════
def command_screen(*, scope, event_id: int) -> dict:
    """F4-01 — 완결조건(§5.4 표)은 "한 화면" — 이 함수가 그 한 응답이다.
    지도·화선 오버레이는 렌더하지 않는다(§0.4 인접 금지구역 MapForRoute*·
    FormRoute.tsx 밖) — 위치는 F4-03 과 같이 주소 문자열로, 화선(확산 경계)
    자체는 이 저장소에 데이터가 없다(F3-10 확산예측 미착수와 같은 이유) —
    그래서 이 함수의 계약은 그 둘을 그리지 않고, 나머지(사건 개요·단계·
    자원·시계·대피·지휘소)를 한 응답에 담는 것으로 좁힌다."""
    event = dsm_services.event_detail(scope=scope, event_id=event_id)
    stage = stage_history(scope=scope, event_id=event_id)
    resources = fws_office.resource_assignments(scope=scope, event_id=event_id)
    timeline = response_timeline(scope=scope, event_id=event_id)
    evac = fws_office2.evacuation_status(scope=scope, event_id=event_id)
    post = command_post(scope=scope, event_id=event_id)

    return {
        "event_id": event_id,
        "incident": {
            "address": event.address, "severity": event.severity,
            "response_state": event.response_state,
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        },
        "stage": stage["current"],
        "resources": resources["assignments"],
        "response_clock": timeline["timeline"],
        "evacuation": {"percent_complete": evac["percent_complete"],
                      "total_villages": evac["total_villages"]},
        "command_post": post["post"],
    }


__all__ = [
    "CommandInputRejected",
    "COMMAND_LEVELS", "COMMAND_LEVEL_MUNICIPAL", "COMMAND_LEVEL_PROVINCIAL",
    "confirm_stage", "stage_history",
    "declare_command_post", "command_post",
    "approve_helicopter_request", "helicopter_status",
    "EVAC_URGENCIES", "approve_evacuation", "release_evacuation",
    "evacuation_command_status",
    "COORDINATION_AGENCIES", "record_agency_coordination",
    "agency_coordination_records",
    "declare_main_fire_out", "declare_extinguished", "fire_declarations",
    "approve_hourly_report", "hourly_approvals",
    "contact_directory",
    "response_timeline", "record_golden_time_exceeded_reason",
    "set_sunset", "night_status",
    "record_situation_meeting", "situation_meetings",
    "priority_queue",
    "post_incident_report_pdf", "post_incident_summary",
    "command_screen",
]
