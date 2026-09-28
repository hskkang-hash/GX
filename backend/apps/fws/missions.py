# -*- coding: utf-8 -*-
"""FWS-F2-02·03·05·11·12 — 임무 수신·이동/도착·지원 요청·철수/복귀·내 임무 이력
(턴 AL 차선 N2).

「임무」는 새 표가 아니다 — K1 이벤트를 진화대 쪽에서 본 것
------------------------------------------------------------
F1(감시원)의 「확인 요청」이 K1 이벤트를 관제 쪽에서 본 것이었던 것과 같은 판단
(`apps/fws/verification.py` 머리말)이다. F2(진화대)의 「임무」도 **같은 K1 이벤트**를
진화대 쪽에서 본 것 — 새 이벤트·새 표를 만들지 않는다(P-357).

정직하게 남긴다 — 명세서 원문(발화점·접근로·화세·풍향·집결지·지휘자) 중 무엇이 없나
--------------------------------------------------------------------------------
K1 `EventView` 가 들고 있는 것은 좌표(발화점 근사)·주소·화세(severity)·시각·스냅샷
경로뿐이다. **접근로·풍향·집결지·지휘자는 K1 이벤트 스키마에 없다** — 그 넷을 채우려면
새 칸(커널 변경)이 필요하고, 그것은 이 차선(App 층)의 권한 밖이다(DA-04 §1-1 — App 은
커널을 소비만 한다). `mission_detail` 은 있는 것만 낸다 — 없는 것을 지어내지 않는다
(D-284). 이 한계는 F1-03(`risk.py` 머리말)이 이미 같은 형으로 적어 둔 관례를 따른다.

대응 진행(response_state)을 **그대로** 빌린다 — 「출동·도착·철수」를 3번째 상태기계로
만들지 않는다
------------------------------------------------------------------------------
K1 은 이미 사람이 어디까지 했는가를 4값으로 갖고 있다(`OCCURRED → ACKNOWLEDGED →
IN_PROGRESS → CLOSED`, `kernels/k1_event/response_flow.py`). 이 파일이 부르는
`apps.dsm.services.advance_response` 가 **그 표 하나**를 그대로 쓴다:

    F2-02 「출동」 1탭     OCCURRED    → ACKNOWLEDGED  (`dispatch` · 사건이 아직 그 앞일 때만)
    F2-03 「도착」 회신    ACKNOWLEDGED → IN_PROGRESS   (`arrived` · 사건이 아직 그 앞일 때만)
    F2-11 「철수·복귀」회신 사건 상태는 **안 옮긴다**   (`released` · 그 진화대의 기록만)

★ [턴 AL · 조율자 병합] **한 불에 진화대가 여럿 붙는다.** 차선 판은 철수 한 번이 사건 전체를
  `CLOSED` 로 옮겼다 — 다른 진화대가 아직 끄고 있는데 사건이 닫힌다. 그리고 전이표가 앞으로만
  가므로 **둘째 진화대의 출동이 409** 였다. 그래서: 사건 상태는 「아직 그 앞일 때만」 앞으로 밀고,
  순서 검사(출동 없이 도착 · 도착 없이 철수 → 409)는 **그 진화대 자신의 기록**으로 한다.
  사건을 닫는 것은 진화대가 아니라 지휘(U2·F4)의 일이다 — 이 문은 닫지 않는다.

전이표는 **앞으로만** 간다(건너뛰기 없음) — 그래서 순서를 어기면(예: 출동 탭 없이
도착 회신) 커널이 `ResponseTransitionForbidden` 을 던지고, 이 파일은 그것을 409 로
번역한다(`api.py`). 두 번째 전이표를 만들지 않는다(D-212) — 두 벌은 반드시 갈린다.

⚠ **한 이벤트에 진화대가 여럿 붙을 때의 한계.** `response_state` 는 이벤트 전체의
칸이다 — 한 사람의 「철수」가 이벤트를 CLOSED 로 옮기면, 아직 현장에 남은 다른
사람의 진행 상태도 함께 닫힌 것처럼 보인다. 이번 턴 범위(첫 고객·시군구 산림과
1곳 규모)에서는 사건당 진화대가 사실상 하나로 취급되고, 이 한계는 다중 대응팀
분리 배정(새 축)이 생기기 전까지 남는다 — 지어내지 않고 여기 적어 둔다.

내 임무 이력·투입 시간(F2-12)은 **이 파일이 자기 감사를 쓴다**
----------------------------------------------------------------
K1 감사(`guardianx.dsm.field_reply`·`guardianx.dsm.response`)에는 테넌트 칸이 없어
사람별로 전건을 뽑는 문지기가 없다(그 파일들 머리말의 같은 한계). `apps/fws/patrol.py`
가 이미 같은 이유로 자기 감사를 쓰고, 이 파일도 그 관례를 따른다 — `arrive`·`release`
가 성공할 때마다 **이 파일의** 감사 한 줄(`LOGGER_NAME` 아래)을 남기고, `mine()` 은
그 감사만 읽는다(K1 감사를 다시 훑지 않는다).
"""
from __future__ import annotations

from datetime import datetime, timezone as _tz

from django.apps import apps

from common import audit_writer

#: ★ F-05 잠금 — K1 을 직접 부르지 않는다. `apps.dsm.services` 가 유일한 문이다.
from apps.dsm import services as dsm_services
from apps.dsm.services import (
    InvalidEventInput,
    ResponseTransitionForbidden,
    ResponseTransitionNeedsManager,
    ResponseTransitionNeedsReason,
)

LOGGER_NAME = "guardianx.fws.mission"
TAG = "[FWS-MISSION]"

ACTION_DISPATCH = "mission.dispatch"
ACTION_ARRIVED = "mission.arrived"
ACTION_RELEASED = "mission.released"
ACTION_SUPPORT = "mission.support_request"

MAX_NOTE_CHARS = 300

#: F2-05 지원 요청 4택 — 명세서 §5.2 FWS-F2-05 원문 그대로(인력·물·헬기·중장비).
SUPPORT_PERSONNEL = "personnel"
SUPPORT_WATER = "water"
SUPPORT_HELICOPTER = "helicopter"
SUPPORT_HEAVY_EQUIPMENT = "heavy_equipment"
SUPPORT_KINDS = (SUPPORT_PERSONNEL, SUPPORT_WATER, SUPPORT_HELICOPTER,
                SUPPORT_HEAVY_EQUIPMENT)

RESPONSE_ACTIONS = ("dispatch", "arrived", "released")


class MissionActionRejected(Exception):
    """값이 계약 밖이다 — 422."""


class MissionStateConflict(Exception):
    """순서가 맞지 않다(예: 출동 탭 없이 도착 회신) — 409. `apps.dsm.services` 가
    던진 대응 전이 거절을 그대로 옮겨 담는다."""


def _model():
    return apps.get_model("logger", "AuditLogs")


def _own_rows(user_id: int, *, event_id: int | None = None,
             actions: tuple[str, ...] = ()):
    qs = _model()._base_manager.filter(logger_name=LOGGER_NAME, user_id=user_id)
    if actions:
        qs = qs.filter(api_name__in=actions)
    rows = list(qs.order_by("id"))
    if event_id is None:
        return rows
    out = []
    for row in rows:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        if payload.get("event_id") == event_id:
            out.append(row)
    return out


def mission_detail(*, scope, event_id: int) -> dict:
    """FWS-F2-02 — 임무 수신. K1 이벤트를 **있는 칸만** 옮긴다(머리말 참조 — 접근로·
    풍향·집결지·지휘자는 K1 스키마에 없어 내지 않는다)."""
    event = dsm_services.event_detail(scope=scope, event_id=event_id)
    return {
        "mission_id": event.event_id,
        "fire_origin": {"lat": event.lat, "lng": event.lng},
        "address": event.address,
        "severity": event.severity,
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        "snapshot_path": event.snapshot_path,
        "response_state": event.response_state,
        "status": event.status,
        # ★ 정직하게 빈 값 — 지어내지 않는다(D-284, 위 머리말).
        "access_route": None,
        "wind_direction": None,
        "muster_point": None,
        "commander": None,
    }


#: 사건 대응 진행의 앞뒤 — 「아직 그 앞일 때만 민다」를 가르는 순서(K1 표와 같은 네 값).
_ORDER = ("occurred", "acknowledged", "in_progress", "closed")


def _advance_if_behind(*, scope, event_id: int, to_state: str, reason: str) -> dict:
    """사건이 `to_state` 보다 **앞**이면 민다 · 이미 그 자리거나 지났으면 그대로 둔다(둘째 진화대)."""
    event = dsm_services.event_detail(scope=scope, event_id=event_id)
    now_state = (event.response_state or "occurred")
    if now_state in _ORDER and _ORDER.index(now_state) >= _ORDER.index(to_state):
        return {"to": now_state, "event_advanced": False}
    try:
        out = dsm_services.advance_response(
            scope=scope, event_id=event_id, to_state=to_state, reason=reason)
    except (ResponseTransitionForbidden, ResponseTransitionNeedsReason,
           ResponseTransitionNeedsManager) as exc:
        raise MissionStateConflict(str(exc)) from exc
    return {**out, "event_advanced": True}


def _require_own(actor, event_id: int, action: str, why: str) -> None:
    """이 진화대가 앞 단계를 했는가 — 순서는 **제 기록**으로 가른다(남의 출동으로 내 도착이 서지 않는다)."""
    if not _own_rows(actor.pk, event_id=event_id, actions=(action,)):
        raise MissionStateConflict(why)


def _write_own(actor, action: str, event_id: int, extra: dict, reason: str) -> int:
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=action,
        outcome=audit_writer.ALLOWED, reason=reason,
        after={"event_id": event_id, **extra}, api_name=action, api_method="POST")
    return entry.audit_id


def respond(*, scope, event_id: int, action: str,
           lat: float | None = None, lng: float | None = None,
           note: str = "") -> dict:
    """F2-02 「출동」탭 · F2-03 도착 회신 · F2-11 철수·복귀 회신 — 한 문.

    `action` 이 무엇을 옮기는지는 머리말의 표 그대로다. 순서가 맞지 않으면
    `MissionStateConflict`(409) — 새 상태기계를 만들지 않고 K1 의 표가 거절한다.
    """
    if action not in RESPONSE_ACTIONS:
        raise MissionActionRejected(
            f"action={action!r} 은 임무 회신이 아니다. 허용: {RESPONSE_ACTIONS}")
    note = (note or "").strip()
    if len(note) > MAX_NOTE_CHARS:
        raise MissionActionRejected(
            f"note 가 {len(note)}자다. 상한은 {MAX_NOTE_CHARS}자")
    actor = scope.require_actor()
    now = datetime.now(_tz.utc)

    if action == "dispatch":
        result = _advance_if_behind(scope=scope, event_id=event_id, to_state="acknowledged",
                                    reason=note or "출동 확인(F2-02)")
        _write_own(actor, ACTION_DISPATCH, event_id, {"at": now.isoformat()},
                  "임무 출동 탭")
        return {"mission_id": event_id, "action": action, **result}

    if action == "arrived":
        #: ★ **순서가 뜻이다.** 전이 문지기(`_advance`)를 먼저 지나고 나서야 회신·
        #:   자기 감사를 쓴다 — 반대로 하면 순서가 틀린 요청(출동 탭 없이 도착)이
        #:   409 로 거절되고도 K1 현장 회신엔 흔적이 남는 반쪽짜리 쓰기가 생긴다.
        event = dsm_services.event_detail(scope=scope, event_id=event_id)
        _require_own(actor, event_id, ACTION_DISPATCH, "출동 탭 없이 도착할 수 없다(이 진화대의 출동 기록이 없다)")
        result = _advance_if_behind(scope=scope, event_id=event_id, to_state="in_progress",
                                    reason=note or "현장 도착(F2-03)")
        text = f"[도착] GPS lat={lat} lng={lng}" + (f" · {note}" if note else "")
        try:
            dsm_services.field_reply(scope=scope, event_id=event_id, text=text)
        except InvalidEventInput as exc:
            raise MissionActionRejected(str(exc)) from exc
        _write_own(actor, ACTION_ARRIVED, event_id,
                  {"lat": lat, "lng": lng, "at": now.isoformat()}, "현장 도착 회신")
        elapsed_minutes = None
        within_30_min = None
        if event.occurred_at is not None:
            elapsed_minutes = round((now - event.occurred_at).total_seconds() / 60, 1)
            within_30_min = elapsed_minutes <= 30
        return {"mission_id": event_id, "action": action,
               "arrived_at": now.isoformat(),
               "elapsed_minutes": elapsed_minutes, "within_30_min": within_30_min,
               **result}

    # action == "released" — **사건을 닫지 않는다**(머리말 ★). 순서는 이 진화대의 도착 기록으로 가른다.
    _require_own(actor, event_id, ACTION_ARRIVED, "도착 회신 없이 철수할 수 없다(이 진화대의 도착 기록이 없다)")
    event = dsm_services.event_detail(scope=scope, event_id=event_id)
    result = {"to": event.response_state or "occurred", "event_advanced": False}
    text = "[철수] 복귀" + (f" · {note}" if note else "")
    try:
        dsm_services.field_reply(scope=scope, event_id=event_id, text=text)
    except InvalidEventInput as exc:
        raise MissionActionRejected(str(exc)) from exc
    arrived_rows = _own_rows(actor.pk, event_id=event_id, actions=(ACTION_ARRIVED,))
    duration_minutes = None
    if arrived_rows:
        payload = arrived_rows[-1].data_after or {}
        arrived_at = payload.get("at")
        if arrived_at:
            try:
                started = datetime.fromisoformat(arrived_at)
                duration_minutes = round((now - started).total_seconds() / 60, 1)
            except ValueError:
                duration_minutes = None
    _write_own(actor, ACTION_RELEASED, event_id,
              {"at": now.isoformat(), "duration_minutes": duration_minutes},
              "철수·복귀 회신")
    return {"mission_id": event_id, "action": action, "released_at": now.isoformat(),
           "duration_minutes": duration_minutes, **result}


def request_support(*, scope, event_id: int, kind: str, amount: str = "",
                    note: str = "") -> dict:
    """FWS-F2-05 — 지원 요청(인력·물·헬기·중장비). K1 현장 회신에 실어 지휘 화면이
    읽는 자리(`GET /events/{id}` 의 field replies)에 그대로 도달한다 — 새 배지
    위젯은 이 차선(App 서버 쪽)의 범위 밖이라 만들지 않는다(§0.4 인접 — DSM 화면은
    lane L 소유)."""
    if kind not in SUPPORT_KINDS:
        raise MissionActionRejected(
            f"kind={kind!r} 는 지원 요청 항목이 아니다. 허용: {SUPPORT_KINDS}")
    note = (note or "").strip()
    amount = (amount or "").strip()
    text = f"[지원요청] {kind} {amount}".strip() + (f" · {note}" if note else "")
    try:
        reply = dsm_services.field_reply(scope=scope, event_id=event_id, text=text)
    except InvalidEventInput as exc:
        raise MissionActionRejected(str(exc)) from exc
    actor = scope.require_actor()
    _write_own(actor, ACTION_SUPPORT, event_id,
              {"kind": kind, "amount": amount, "note": note}, "지원 요청")
    return {"mission_id": event_id, "reply_id": reply.reply_id, "kind": kind,
           "amount": amount or None}


def mine(*, scope) -> dict:
    """FWS-F2-12 — 내 임무 이력·투입 시간(수당 근거). **이 파일의 자기 감사만**
    읽는다(머리말 참조) — K1 감사를 다시 훑지 않는다."""
    actor = scope.require_actor()
    rows = _own_rows(actor.pk, actions=(ACTION_DISPATCH, ACTION_ARRIVED,
                                       ACTION_RELEASED))
    by_event: dict[int, dict] = {}
    for row in rows:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        event_id = payload.get("event_id")
        if event_id is None:
            continue
        entry = by_event.setdefault(event_id, {
            "mission_id": event_id, "dispatched_at": None,
            "arrived_at": None, "released_at": None, "duration_minutes": None})
        if row.api_name == ACTION_DISPATCH:
            entry["dispatched_at"] = payload.get("at")
        elif row.api_name == ACTION_ARRIVED:
            entry["arrived_at"] = payload.get("at")
        elif row.api_name == ACTION_RELEASED:
            entry["released_at"] = payload.get("at")
            entry["duration_minutes"] = payload.get("duration_minutes")

    missions = sorted(by_event.values(),
                      key=lambda m: m["dispatched_at"] or m["arrived_at"] or "",
                      reverse=True)
    total_minutes = sum(m["duration_minutes"] for m in missions
                        if isinstance(m["duration_minutes"], (int, float)))
    return {"missions": missions, "count": len(missions),
           "total_minutes": round(total_minutes, 1) if missions else 0}
