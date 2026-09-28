# -*- coding: utf-8 -*-
"""FWS-F5-01·02·03·08·10 — 드론 운용자(F5) (턴 AM 차선 N2 · 세종 판정 P-387).

세종 판정 P-387 — 「요청·상태·결과」 세 축뿐이다, 드론은 0대다
------------------------------------------------------------------
이 저장소에는 실제 드론이 **0대** 있다(연동 카메라·스트림과 다르다 — 그런 하드웨어가
아예 없다). P-387 이 그은 선은 이렇다: 드론이 하는 일을 흉내 내지 않는다. 대신
사람이 드론을 **부리는 서류**의 세 축만 만든다:

    요청(request)  「이 사건에 드론 정찰을 띄운다」 — F5-01
    상태(state)    수락 → 이륙 → 귀환, 그 서류가 지금 어디 있는가 — F5-01
    결과(result)   산불 맞음/오인 + 참조(사진·열화상 경로 값) — F5-03

DJI 연동은 **어댑터 자리 하나**(`log_flight` 의 `source` 칸)로 잠근다 — 실제 DJI API
호출은 0건이다. 새 기체 제조사가 붙어도 이 칸에 문자열 값이 하나 늘 뿐, 코드는
안 바뀐다.

열점·화선(F5-02)·비행 기록(F5-08)은 **값**이다 — 지도·폴리라인을 그리지 않는다
------------------------------------------------------------------------------
§0.4 인접 금지구역(`MapForRoute*`·`FormRoute.tsx`)은 이 차선이 만지지 않는다. 열점
좌표 목록·화선 좌표 목록은 그 자체로 값(list[{lat,lng}])이고, 그리는 것은 화면의
몫이다(F1-05 `verification.get_verification` 머리말과 같은 판단).

「요청」은 K1 이벤트를 드론 쪽에서 본 것이다 — 새 표를 만들지 않는다
--------------------------------------------------------------------
F1 의 「확인 요청」·F2 의 「임무」와 같은 판단(P-357). 드론 정찰 요청도 **같은 K1
이벤트**를 겨눈다 — 반경(`radius_m`)은 K1 이벤트 스키마에 없는 칸이라 값으로만
오가고 저장하지 않는다(요청 감사 한 줄에는 남는다·재조회 가능·단 K1 이벤트 자체의
칸은 아니다, D-284 「지어내지 않는다」).

★ 다중 행위자 규칙 — **한 조종사의 상태 전이가 사건을 닫지 않는다**
------------------------------------------------------------------
`missions.py` 머리말(턴 AL 조율자 병합)이 잡은 것과 같은 함정이다: 이 파일의
`recon()`·`confirm_result()` 는 **`apps.dsm.services.advance_response` 를 한 번도
부르지 않는다.** 드론의 수락·이륙·귀환은 그 조종사 자신의 기록일 뿐 사건의
`response_state` 를 옮기지 않는다. `confirm_result()` 가 부르는 `review_event` 는
사건의 **판정**(verdict: confirmed/rejected)만 바꾼다 — 그것도 F1-06 이 이미 같은
문으로 하던 일이고(재사용), 대응 진행(response_state)과는 다른 축이다(D-399 판정
축·대응 축 분리).

★ 자기 서류의 한계 — **요청·수락이 다른 사람일 수 없다**
------------------------------------------------------------------
감사 표(`logger.AuditLogs`)에는 테넌트 칼럼이 없다(`patrol.py`·`missions.py` 머리말과
같은 한계). 그래서 "누구나 볼 수 있는 대기열"을 이 표로 만들면 남의 테넌트 요청이
섞일 위험이 있다 — 그래서 순서 검사(`accept` 는 `request` 뒤에만)는 **이 조종사
자신의 기록**으로 가른다(`missions.py::_require_own` 과 같은 판단). 현실에서는
지휘가 배차하고 다른 조종사가 수락하는 그림이 자연스럽지만, 그 배차(새 축·다른
테넌트 문지기)는 이번 차선 권한 밖이다 — 지어내지 않고 여기 적는다.

닫는 다섯 (F5-01·02·03·08·10) · 못 닫는 다섯 (F5-04·05·06·07·09)
------------------------------------------------------------------
못 닫은 다섯의 이유는 `scripts/verify_spec_fws.py` 의 `NOT_STARTED` 표에 있다 —
전부 **App 층 권한 밖의 새 축**(구역 예약·헬기 충돌 규칙·폴리곤 면적·스트림 공유)
이다.
"""
from __future__ import annotations

import json as _json

from django.apps import apps
from django.utils import timezone

from common import audit_writer

#: ★ F-05 잠금 — K1 을 직접 부르지 않는다. `apps.dsm.services` 가 유일한 문이다.
from apps.dsm import services as dsm_services
from apps.dsm.services import InvalidEventInput

from apps.fws import verification

LOGGER_NAME = "guardianx.fws.drone"
TAG = "[FWS-DRONE]"

MAX_NOTE_CHARS = 300

ACTION_RECON_REQUEST = "drone.recon.request"
ACTION_RECON_ACCEPT = "drone.recon.accept"
ACTION_RECON_AIRBORNE = "drone.recon.airborne"
ACTION_RECON_RETURN = "drone.recon.return"
ACTION_HOTSPOTS = "drone.hotspots.submit"
ACTION_FLIGHT_LOG = "drone.flight.log"

#: F5-01 정찰 요청의 상태 넷 — 요청·수락·이륙·귀환. **앞으로만** 간다(missions.py
#: 의 대응 진행표와 같은 규율 — 건너뛰기 없음).
RECON_REQUEST = "request"
RECON_ACCEPT = "accept"
RECON_AIRBORNE = "airborne"
RECON_RETURN = "return"
RECON_ACTIONS = (RECON_REQUEST, RECON_ACCEPT, RECON_AIRBORNE, RECON_RETURN)

_RECON_ACTION_LOG = {
    RECON_REQUEST: ACTION_RECON_REQUEST,
    RECON_ACCEPT: ACTION_RECON_ACCEPT,
    RECON_AIRBORNE: ACTION_RECON_AIRBORNE,
    RECON_RETURN: ACTION_RECON_RETURN,
}
#: 이 상태 바로 앞에 있어야 할 상태 — 없으면(제 기록에) 409.
_RECON_PREV = {
    RECON_ACCEPT: RECON_REQUEST,
    RECON_AIRBORNE: RECON_ACCEPT,
    RECON_RETURN: RECON_AIRBORNE,
}
_RECON_FIELD = {
    RECON_REQUEST: "requested_at",
    RECON_ACCEPT: "accepted_at",
    RECON_AIRBORNE: "airborne_at",
    RECON_RETURN: "returned_at",
}

#: F5-02 좌표 목록 상한 — 명세 값이 아니라 **이 차선이 정한 안전 상한**(남용 방지,
#: 규칙 9의 "규정 값"과는 출처가 다르다 — 그래도 시험 표본을 하나 둔다).
MAX_HOTSPOT_POINTS = 200
MAX_FIRELINE_POINTS = 200

#: F5-08 값의 상한·기본값. `source` 는 DJI 등 연동 어댑터의 **이름 값 자리**뿐이다
#: (머리말 참조) — 닫힌 목록으로 잠그지 않는다(다음 기체 제조사가 배포 없이 붙게).
DEFAULT_FLIGHT_SOURCE = "manual"
MAX_SOURCE_CHARS = 40
MAX_AIRFRAME_CHARS = 40
BATTERY_PCT_MIN = 0.0
BATTERY_PCT_MAX = 100.0


class DroneActionRejected(Exception):
    """값이 계약 밖이다 — 422."""


class DroneStateConflict(Exception):
    """순서가 맞지 않다(예: 수락 없이 이륙) — 409."""


def _model():
    return apps.get_model("logger", "AuditLogs")


def _own_rows(user_id: int, *, event_id: int | None = None,
             actions: tuple[str, ...] = ()):
    """`missions.py::_own_rows` 와 같은 세 줄 — 두 벌을 만들지 않으려 했으나 그
    모듈을 이 모듈이 import 하면 순환·결합이 생겨(둘 다 `apps.fws` 하위) 그대로
    옮겨 적는다(D-212 은 "판정식 복사"를 금하지 "같은 모양의 세 줄"까지 금하지
    않는다 — 판정은 없고 필터 조립뿐이다)."""
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


def _write_own(actor, action: str, event_id: int | None, extra: dict,
              reason: str) -> int:
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=action,
        outcome=audit_writer.ALLOWED, reason=reason,
        after={"event_id": event_id, **extra}, api_name=action, api_method="POST")
    return entry.audit_id


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F5-01 정찰 임무 수신(요청·상태) — K1 이벤트를 드론 쪽에서 본 것
# ═══════════════════════════════════════════════════════════════════════════
def recon(*, scope, event_id: int, action: str, radius_m: float | None = None,
         note: str = "") -> dict:
    """F5-01 — 정찰 요청(action=request) · 상태 전이(accept·airborne·return) 한 문.

    `radius_m` 은 요청 때만 뜻이 있다(발화 추정 반경) — K1 이벤트 스키마에 없는
    칸이라 이 파일의 감사 한 줄에만 남는다(머리말 참조).
    """
    if action not in RECON_ACTIONS:
        raise DroneActionRejected(
            f"action={action!r} 은 정찰 상태가 아니다. 허용: {RECON_ACTIONS}")
    note = (note or "").strip()
    if len(note) > MAX_NOTE_CHARS:
        raise DroneActionRejected(f"note 가 {len(note)}자다. 상한은 {MAX_NOTE_CHARS}자")
    if radius_m is not None and radius_m <= 0:
        raise DroneActionRejected(f"radius_m={radius_m!r} 은 0보다 커야 한다")

    #: 테넌트 문지기 — 남의 사건에 정찰 서류를 쓸 수 없다(Http404 는 api.py 가 옮긴다).
    dsm_services.event_detail(scope=scope, event_id=event_id)

    prev_action = _RECON_PREV.get(action)
    if prev_action is not None and not _own_rows(
            scope.require_actor().pk, event_id=event_id,
            actions=(_RECON_ACTION_LOG[prev_action],)):
        raise DroneStateConflict(
            f"{action} 이전 단계({prev_action})가 이 조종사의 기록에 없다")

    actor = scope.require_actor()
    now = timezone.now()

    if action == RECON_REQUEST:
        text = f"[드론정찰요청] radius_m={radius_m}" + (f" · {note}" if note else "")
        try:
            dsm_services.field_reply(scope=scope, event_id=event_id, text=text)
        except InvalidEventInput as exc:
            raise DroneActionRejected(str(exc)) from exc

    record_id = _write_own(
        actor, _RECON_ACTION_LOG[action], event_id,
        {"action": action, "radius_m": radius_m, "at": now.isoformat()},
        note or f"드론 정찰 {action}")
    return {"event_id": event_id, "action": action, "radius_m": radius_m,
           "recorded_at": now.isoformat(), "record_id": record_id}


def recon_mine(*, scope) -> dict:
    """F5-01 — 이 조종사의 정찰 요청 대기열(사건별 상태)."""
    actor = scope.require_actor()
    rows = _own_rows(actor.pk, actions=tuple(_RECON_ACTION_LOG.values()))
    by_event: dict[int, dict] = {}
    for row in rows:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        event_id = payload.get("event_id")
        if event_id is None:
            continue
        entry = by_event.setdefault(event_id, {
            "event_id": event_id, "state": None, "radius_m": None,
            "requested_at": None, "accepted_at": None, "airborne_at": None,
            "returned_at": None})
        action = payload.get("action")
        field = _RECON_FIELD.get(action)
        if field:
            entry[field] = payload.get("at")
            entry["state"] = action
        if action == RECON_REQUEST:
            entry["radius_m"] = payload.get("radius_m")

    requests = sorted(by_event.values(),
                      key=lambda r: r["requested_at"] or "", reverse=True)
    return {"requests": requests, "count": len(requests)}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F5-02 열점·화선 표시 — 좌표 목록을 **값**으로 (지도 없음)
# ═══════════════════════════════════════════════════════════════════════════
def _validate_points(points, *, label: str, cap: int, min_count: int = 1) -> list:
    if points is None:
        return []
    if not isinstance(points, list):
        raise DroneActionRejected(f"{label} 은 좌표 목록이어야 한다")
    if len(points) > cap:
        raise DroneActionRejected(f"{label} 이 {len(points)}점이다. 상한은 {cap}점")
    out = []
    for i, p in enumerate(points):
        if not isinstance(p, dict) or "lat" not in p or "lng" not in p:
            raise DroneActionRejected(f"{label}[{i}] 에 lat·lng 이 없다")
        try:
            lat = float(p["lat"])
            lng = float(p["lng"])
        except (TypeError, ValueError) as exc:
            raise DroneActionRejected(f"{label}[{i}] 의 좌표가 숫자가 아니다") from exc
        out.append({"lat": lat, "lng": lng})
    if 0 < len(out) < min_count:
        raise DroneActionRejected(f"{label} 은 최소 {min_count}점이 필요하다")
    return out


def _parse_points_json(raw: str | None, *, label: str) -> list | None:
    """`issue_api_key(scopes: str)` 와 같은 규약 — django-ninja 라우트는 원시 인자를
    질의(query)로만 받으므로(`law_api.py` 머리말 ④), 좌표 목록 같은 복합 값은
    **JSON 문자열**로 들어온다. 빈 문자열은 "안 보냄"이다."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        parsed = _json.loads(raw)
    except ValueError as exc:
        raise DroneActionRejected(f"{label} 이 올바른 JSON 이 아니다") from exc
    return parsed


def submit_hotspots(*, scope, event_id: int, points_json: str = "",
                    fireline_json: str = "", note: str = "") -> dict:
    """F5-02 — 열점(`points_json`)·화선(`fireline_json`) 좌표 목록 제출(JSON 문자열
    — `[{"lat":..,"lng":..}, ...]`). **값만** 오간다 — 화면이 지도를 그리든 안
    그리든 이 함수는 모른다(§0.4 인접 금지구역 밖)."""
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 테넌트 문지기
    note = (note or "").strip()
    if len(note) > MAX_NOTE_CHARS:
        raise DroneActionRejected(f"note 가 {len(note)}자다. 상한은 {MAX_NOTE_CHARS}자")
    points = _parse_points_json(points_json, label="points")
    fireline = _parse_points_json(fireline_json, label="fireline")
    hot_points = _validate_points(points, label="points", cap=MAX_HOTSPOT_POINTS)
    line_points = _validate_points(
        fireline, label="fireline", cap=MAX_FIRELINE_POINTS, min_count=2)
    if not hot_points and not line_points:
        raise DroneActionRejected(
            "points 도 fireline 도 없다 — 무엇을 표시했는지 없이는 값이 안 된다")

    actor = scope.require_actor()
    now = timezone.now()
    text = (f"[드론열점] 열점 {len(hot_points)}점 · 화선 {len(line_points)}점"
           + (f" · {note}" if note else ""))
    try:
        dsm_services.field_reply(scope=scope, event_id=event_id, text=text)
    except InvalidEventInput as exc:
        raise DroneActionRejected(str(exc)) from exc

    batch_id = _write_own(
        actor, ACTION_HOTSPOTS, event_id,
        {"points": hot_points, "fireline": line_points, "at": now.isoformat()},
        note or "열점·화선 제출")
    return {"event_id": event_id, "batch_id": batch_id, "points": hot_points,
           "fireline": line_points, "submitted_at": now.isoformat()}


def hotspots_mine(*, scope, event_id: int) -> dict:
    """F5-02 — 이 조종사가 그 사건에 제출한 열점·화선 배치 전건(값 재조회)."""
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 테넌트 문지기
    actor = scope.require_actor()
    rows = _own_rows(actor.pk, event_id=event_id, actions=(ACTION_HOTSPOTS,))
    batches = []
    for row in rows:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        batches.append({
            "batch_id": row.pk, "points": payload.get("points", []),
            "fireline": payload.get("fireline", []),
            "submitted_at": payload.get("at")})
    return {"event_id": event_id, "batches": batches, "count": len(batches)}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F5-03 확인 회신(산불 맞음/오인 · 참조) — F1-06 의 문을 그대로 쓴다
# ═══════════════════════════════════════════════════════════════════════════
def confirm_result(*, scope, event_id: int, result: str, reason_code: str = "",
                   attachment_ref: str = "", note: str = "") -> dict:
    """F5-03 — 결과 첨부. `verification.reply_verification`(F1-06) 을 **그대로**
    부른다 — 두 번째 판정 문을 만들지 않는다(P-357, D-212).

    이 함수가 더하는 것은 **참조 값**(`attachment_ref` — 사진·열화상 파일의
    경로/URL. 실제 업로드 저장소는 이번 차선 범위 밖) 하나뿐이다. 「산불 맞음」
    이라고 답하면서 참조가 없으면 명세서 원문(「사진·열화상」)을 어기므로 422 다.
    """
    attachment_ref = (attachment_ref or "").strip()
    if result == verification.RESULT_FIRE_CONFIRMED and not attachment_ref:
        raise verification.VerificationReplyRejected(
            "산불 맞음 확인에는 사진·열화상 참조(attachment_ref)가 있어야 한다 "
            "(F5-03 명세 원문 — 사진·열화상)")
    note = (note or "").strip()
    tagged_note = (f"[드론 확인 첨부:{attachment_ref}] {note}".strip()
                  if attachment_ref else note)
    reply = verification.reply_verification(
        scope=scope, verification_id=event_id, result=result,
        reason_code=reason_code, note=tagged_note)
    return {**reply, "attachment_ref": attachment_ref or None}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F5-08 비행 기록·배터리·기체 상태 — 값 한 줄
# ═══════════════════════════════════════════════════════════════════════════
def log_flight(*, scope, event_id: int | None = None,
               source: str = DEFAULT_FLIGHT_SOURCE, airframe_code: str = "",
               battery_pct: float | None = None,
               flight_minutes: float | None = None, note: str = "") -> dict:
    """F5-08 — 비행 기록 한 줄(비행 분·배터리·기체). `source` 는 DJI 등 연동
    어댑터의 **이름 값 자리**뿐이다(머리말 참조 — 실제 호출 0건)."""
    if event_id is not None:
        dsm_services.event_detail(scope=scope, event_id=event_id)  # 테넌트 문지기
    source = (source or DEFAULT_FLIGHT_SOURCE).strip() or DEFAULT_FLIGHT_SOURCE
    if len(source) > MAX_SOURCE_CHARS:
        raise DroneActionRejected(f"source 가 {len(source)}자다. 상한은 {MAX_SOURCE_CHARS}자")
    airframe_code = (airframe_code or "").strip()
    if len(airframe_code) > MAX_AIRFRAME_CHARS:
        raise DroneActionRejected(
            f"airframe_code 가 {len(airframe_code)}자다. 상한은 {MAX_AIRFRAME_CHARS}자")
    if battery_pct is not None and not (BATTERY_PCT_MIN <= battery_pct <= BATTERY_PCT_MAX):
        raise DroneActionRejected(
            f"battery_pct={battery_pct!r} 는 {BATTERY_PCT_MIN}~{BATTERY_PCT_MAX} 밖이다")
    if flight_minutes is not None and flight_minutes < 0:
        raise DroneActionRejected(f"flight_minutes={flight_minutes!r} 는 음수일 수 없다")
    note = (note or "").strip()
    if len(note) > MAX_NOTE_CHARS:
        raise DroneActionRejected(f"note 가 {len(note)}자다. 상한은 {MAX_NOTE_CHARS}자")

    actor = scope.require_actor()
    now = timezone.now()
    payload = {"event_id": event_id, "source": source, "airframe_code": airframe_code,
              "battery_pct": battery_pct, "flight_minutes": flight_minutes,
              "note": note, "logged_at": now.isoformat()}
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=ACTION_FLIGHT_LOG,
        outcome=audit_writer.ALLOWED,
        reason=(f"비행 기록 {source} 배터리{battery_pct} 기체{airframe_code}".strip()),
        after=payload, api_name=ACTION_FLIGHT_LOG, api_method="POST")
    return {"flight_id": entry.audit_id, **payload}


def flights_mine(*, scope, limit: int = 50) -> dict:
    """F5-08 — 내가 남긴 비행 기록 전건, 최신순(저장 → 재조회 실측)."""
    actor = scope.require_actor()
    rows = (
        _model()._base_manager
        .filter(logger_name=LOGGER_NAME, user_id=actor.pk, api_name=ACTION_FLIGHT_LOG)
        .order_by("-id")[: max(1, min(limit, 500))]
    )
    flights = []
    for row in rows:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        flights.append({"flight_id": row.pk, **payload})
    return {"flights": flights, "count": len(flights)}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F5-10 계량(비행 분) — F5-08 의 값을 **센다**, 새 표를 만들지 않는다
# ═══════════════════════════════════════════════════════════════════════════
def flight_minutes_total(*, scope, month: str = "") -> dict:
    """F5-10 — 이번 달(또는 지정한 달) 비행 분 합계. `log_flight` 이 이미 남긴
    값을 세기만 한다 — 커널도 새 표도 부르지 않는다(F5-08 감사 한 줄이 정본)."""
    actor = scope.require_actor()
    month = (month or "").strip()
    rows = (
        _model()._base_manager
        .filter(logger_name=LOGGER_NAME, user_id=actor.pk, api_name=ACTION_FLIGHT_LOG)
        .order_by("-id")[:5000]
    )
    total = 0.0
    count = 0
    for row in rows:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        logged_at = payload.get("logged_at") or ""
        if month and not logged_at.startswith(month):
            continue
        minutes = payload.get("flight_minutes")
        if isinstance(minutes, (int, float)):
            total += minutes
            count += 1
    return {"month": month or None, "flight_minutes_total": round(total, 1),
           "flight_count": count}
