# -*- coding: utf-8 -*-
"""FWS-F3-01~09 — 산림과 담당(F3) 상황판·설정·인력·확인·접수·통보·자원·단계
(turn AN · WO-17 · 차선 N2 · 세종 판정 P-397).

P-397 을 그대로 잇는다 — 새 표를 만들지 않는다(새 표 0)
--------------------------------------------------------
F3(산림과 담당)이 다루는 것은 F1(감시원)·F2(진화대)·F5(드론)·F6(연계)이 이미
같은 K1 이벤트·같은 감사 로그를 놓고 본 것을 **산림과 쪽 각도**에서 다시 보는
것이다(`patrol.py`·`missions.py`·`drone.py`·`integration.py` 머리말과 같은 판단):

    확인 요청 발송(F3-04)   `apps.dsm.services.notify_event`(F1/F6 문 재사용) +
                             이 파일의 감사 한 줄(10분 시계)
    오인 종결·산불 확정(F3-05) `apps.fws.verification.reply_verification`(F1-06)
                             **그대로** — 이 파일은 새 라우트를 열지 않는다(아래
                             참조). 이미 있는 문을 다시 짓는 것은 D-212 위반이다.
    자원 배정(F3-08)        `apps.dsm.services.field_reply` + `notify_event`
                             (F2 임무·F6 통보와 같은 재사용)
    산림청 번호(F3-07)      `apps.fws.contacts.FOREST_REPORT_NUMBER`(F1-08) 재사용
                             — 번호를 다시 적지 않는다
    헬기 요청 발송(F3-07)   기록만 이 파일이 더한다(요청 시각·기지·도착 예정) —
                             `apps.fws.integration.request_helicopter`(F6-05)와
                             **행위가 다르다**(그쪽은 산림항공본부로 나가는 요청
                             그 자체, 이쪽은 산림과 담당이 "통보했다"는 자기 기록)
                             이므로 그 함수를 고치지 않고 옆에 둔다(D-212 — 남의
                             계약을 넓히지 않는다).
    산불 대응단계 계산(F3-09) `apps.fws.constants.compute_fire_stage`(P-386) 재사용
                             — 문턱값을 다시 적지 않는다

새 표는 0 — 전부 `logger.AuditLogs` 감사 한 줄(`patrol.py`·`standby.py`·
`integration.py` 와 같은 관례: 일어난 일 한 줄을 남기고, 최신/전체 줄이 지금
상태를 답한다).

조직 전체를 보는 자리(F3-01·02·03) — `filter_users_by_group` 로 좁힌다
-----------------------------------------------------------------------
F1(감시원)·F2(진화대)의 모듈들은 전부 **자기 것만**(own rows) 본다 — 감사 표에
테넌트 칼럼이 없어서(그 파일들 머리말의 한계) 여러 사람의 기록을 모으는 문이
없었다. 그러나 F3(산림과 담당)은 태생적으로 "우리 팀 전체가 지금 어떤가"를
봐야 하는 역할이다 — 그 자리를 열려면 안전하게 **먼저** 사람 목록을 테넌트로
좁혀야 한다(`common.tenant_filters.filter_users_by_group` — `apps/dsm/
access_permission_service.py::person_permissions` 가 이미 쓰는 문). 이 파일은
그 좁혀진 `user_id` 목록으로만 `AuditLogs` 를 `user_id__in=` 질의한다 — 아이디
목록 자체가 이미 테넌트 경계 안이므로, 그 안에서 감사 표를 읽는 것은 새로운
누출 경로를 열지 않는다(경계는 여전히 `filter_users_by_group` 하나가 긋는다).

N+1 을 피한다 — 사람 수만큼 질의하지 않는다(`apps/dsm/services.py::
event_data_sources` 머리말의 같은 경고). `user_id__in=` 한 번의 질의로 모으고
파이썬에서 사람별 최신 한 줄만 접는다.

정직하게 남긴다 — 「가장 가까운 드론」은 값이 없다
-----------------------------------------------------
F3-04 의 기능 설명 괄호("가장 가까운 감시원/드론에 확인 요청")는 FF-2 §6 프로세스
표의 UX 힌트이고, §5.3 표의 **완결조건은 "요청 발송 · 10분 시계"**이다(제목 괄호가
아니라 완결조건이 승격의 조작적 기준 — F6-07 이 이미 같은 방식으로 "실제 앱
푸시"가 아니라 PRD 대안으로 닫힌 전례를 따른다). 그래도 이 파일은 "가장 가까운
감시원"은 실제로 값을 낸다(오늘 체크인한 사람의 위치와 사건 좌표의 하버사인
거리) — 그러나 "드론"은 **이 저장소에 드론이 0대**이고(P-387 머리말) 위치
텔레메트리가 아예 없어 빈 목록을 정직하게 낸다(D-284 — 없는 값을 지어내지
않는다).
"""
from __future__ import annotations

import math
from datetime import timedelta

from django.apps import apps
from django.utils import timezone

from common import audit_writer
from common.tenant_filters import filter_users_by_group

#: ★ F-05 잠금 — K1 을 직접 부르지 않는다. `apps.dsm.services` 가 유일한 문이다.
from apps.dsm import services as dsm_services
from apps.dsm.services import InvalidEventInput
#: ★ D-278 — 커널의 공개 면(예외 클래스)만 가져온다. 발송 함수는 여전히
#:   `dsm_services.notify_event` 하나로 부른다(`integration.py` 와 같은 자리).
from kernels.k2_notify import NoRecipients

from apps.fws import constants as fws_constants
from apps.fws import contacts as fws_contacts
from apps.fws import patrol as fws_patrol
from apps.fws import standby as fws_standby

LOGGER_NAME = "guardianx.fws.office"
TAG = "[FWS-OFFICE]"

MAX_NOTE_CHARS = 300
MAX_CODE_CHARS = 40
MAX_NAME_CHARS = 80
MAX_ORG_CHARS = 80

#: 조직 전체를 좁힐 때의 상한 — 무제한 스캔 금지(`access_permission_service.py`
#: 의 `_PERSON_CAP` 과 같은 판단). 첫 고객 규모(시군구 산림과 1곳)에는 넉넉하다.
GROUP_SCAN_CAP = 300

#: F3-04 「10분 시계」— annex §5.3 원문 그대로. 이 차선의 모듈 상수(공용
#: `constants.py` 는 이 턴에 고치지 않는다).
VERIFICATION_TIMEOUT_MINUTES = 10

#: F3-06 「신고 시각 = 30분 시계 시작」— annex §5.3·FF-2 원문 그대로.
INTAKE_CLOCK_MINUTES = 30

#: F3-01 「초소 근무」 판단 창 — annex 가 시각을 정하지 않아 이 차선이 정한
#: 값이다(법정 규정값이 아니다 · 오늘 자정부터로 잡는다 — `patrol.mine()` 이
#: 이미 쓰는 "오늘" 경계와 같다).


class OfficeInputRejected(Exception):
    """값이 계약 밖이다 — 422."""


def _audit_model():
    return apps.get_model("logger", "AuditLogs")


def _write(actor, action: str, payload: dict, reason: str):
    return audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=action,
        outcome=audit_writer.ALLOWED, reason=reason, after=payload,
        api_name=action, api_method="POST")


def _now_iso() -> str:
    return timezone.now().isoformat()


def _check_note(note: str) -> str:
    note = (note or "").strip()
    if len(note) > MAX_NOTE_CHARS:
        raise OfficeInputRejected(f"note 가 {len(note)}자다. 상한은 {MAX_NOTE_CHARS}자")
    return note


def _rows_for_event(action: str, event_id: int):
    """이 사건에 달린 이 파일의 기록 전부 — **제출자를 가리지 않는다**
    (`integration.py::_rows_for_event` 와 같은 판단 — 산림과 담당 여럿이 같은
    사건에 남기는 공유 기록이다). 부르기 **전에** 호출자가
    `dsm_services.event_detail(event_id)` 로 그 사건에 닿을 자격을 이미
    확인받았다(남의 테넌트 사건이면 거기서 404) — 그 경계 밖에서 이 함수를
    부르지 않는다."""
    qs = _audit_model()._base_manager.filter(
        logger_name=LOGGER_NAME, api_name=action).order_by("id")
    out = []
    for row in qs:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        if payload.get("event_id") == event_id:
            out.append(row)
    return out


def _group_user_ids(actor, *, cap: int = GROUP_SCAN_CAP) -> list[int]:
    """이 사람의 테넌트(그룹) 전원의 id — 머리말 참조. 한 번만 계산해 재사용한다."""
    CoreUser = apps.get_model("user", "CoreUser")
    qs = (filter_users_by_group(CoreUser.objects.all(), actor)
         .order_by("id").values_list("id", flat=True)[:cap])
    return list(qs)


def _latest_per_user(rows) -> dict:
    """`user_id` 별 최신 한 줄 — 행은 이미 `-id` 로 왔다고 가정한다."""
    latest: dict[int, object] = {}
    for row in rows:
        if row.user_id not in latest:
            latest[row.user_id] = row
    return latest


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-01 산불 상황판 — 위험지수·위기경보·초소 근무·카메라 정상·진행 사건·
# 자원 대기(띠 6수)
# ═══════════════════════════════════════════════════════════════════════════
_ACTIVE_RESPONSE_STATES = ("occurred", "acknowledged", "in_progress")


def dashboard(*, scope) -> dict:
    """F3-01 — 여섯 띠를 한 번에. **판정은 전부 재사용**한다:

        위험지수·위기경보   `apps.fws.risk.risk_today()`(F1-03)
        카메라 정상         `apps.dsm.services.camera_pulse()`(UX-23)
        진행 사건           `apps.dsm.services.recent_events()`(F-09) — 대응
                            진행이 종결 전 셋 중 하나인 것만 센다
        초소 근무·자원 대기 이 파일이 새로 연다(머리말 「조직 전체를 보는 자리」) —
                            `patrol.py`·`standby.py` 의 **같은 행위 이름**
                            (checkin·standby.save)을 그 모듈을 고치지 않고
                            그룹 전체로 넓혀 센다(그 모듈들의 상수만 가져온다).
    """
    from apps.fws import risk as fws_risk

    actor = scope.require_actor()
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    risk_today = fws_risk.risk_today()
    pulse = dsm_services.camera_pulse(scope=scope)

    events = dsm_services.recent_events(scope=scope, limit=200)
    ongoing = [e for e in events
              if (e.response_state or "occurred") in _ACTIVE_RESPONSE_STATES]

    user_ids = _group_user_ids(actor)
    AuditLogs = _audit_model()

    on_duty_count = 0
    if user_ids:
        checkin_user_ids = set(
            AuditLogs._base_manager.filter(
                logger_name=fws_patrol.LOGGER_NAME,
                api_name=fws_patrol.ACTION_CHECKIN,
                user_id__in=user_ids,
                create_datetime__gte=today_start,
            ).values_list("user_id", flat=True).distinct())
        on_duty_count = len(checkin_user_ids)

    standby_counts = {status: 0 for status in fws_standby.STATUSES}
    if user_ids:
        rows = (AuditLogs._base_manager.filter(
            logger_name=fws_standby.LOGGER_NAME,
            api_name=fws_standby.ACTION_SAVE,
            user_id__in=user_ids,
        ).order_by("user_id", "-id")[:5000])
        for row in _latest_per_user(rows).values():
            payload = row.data_after if isinstance(row.data_after, dict) else {}
            status = payload.get("status")
            if status in standby_counts:
                standby_counts[status] += 1

    return {
        "as_of": now.isoformat(),
        "risk_index": {"level": risk_today["level"], "season": risk_today["season"]},
        "fire_alert": {"active": risk_today["fire_alert"],
                      "mountain_entry_banned": risk_today["mountain_entry_banned"]},
        "post_duty": {"on_duty": on_duty_count, "total_officers": len(user_ids)},
        "camera_status": pulse["counts"],
        "ongoing_incidents": {
            "count": len(ongoing),
            "items": [{
                "event_id": e.event_id, "severity": e.severity,
                "response_state": e.response_state,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
            } for e in ongoing[:20]],
        },
        "resource_standby": standby_counts,
    }


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-02 조심기간·특별대책기간 설정 · 초소·순찰 구역 등록
# ═══════════════════════════════════════════════════════════════════════════
SEASON_KIND_DRY = "dry_season"            # 조심기간
SEASON_KIND_SPECIAL = "special_measures"  # 특별대책기간
SEASON_KINDS = (SEASON_KIND_DRY, SEASON_KIND_SPECIAL)

ACTION_SEASON_SET = "office.season.set"


def set_season(*, scope, kind: str, start_date: str, end_date: str,
              note: str = "") -> dict:
    if kind not in SEASON_KINDS:
        raise OfficeInputRejected(
            f"kind={kind!r} 는 기간 종류가 아니다. 허용: {SEASON_KINDS}")
    start_date = (start_date or "").strip()
    end_date = (end_date or "").strip()
    if not start_date or not end_date:
        raise OfficeInputRejected("start_date · end_date 는 비울 수 없다")
    note = _check_note(note)
    actor = scope.require_actor()
    payload = {"kind": kind, "start_date": start_date, "end_date": end_date,
              "note": note, "set_at": _now_iso(),
              "set_by": getattr(actor, "username", "")}
    entry = _write(actor, ACTION_SEASON_SET, payload,
                  f"{kind} 설정 {start_date}~{end_date}")
    return {"season_id": entry.audit_id, **payload}


def current_seasons(*, scope) -> dict:
    actor = scope.require_actor()
    user_ids = _group_user_ids(actor)
    seasons: dict[str, dict] = {}
    if user_ids:
        rows = (_audit_model()._base_manager.filter(
            logger_name=LOGGER_NAME, api_name=ACTION_SEASON_SET,
            user_id__in=user_ids).order_by("-id")[:500])
        for row in rows:
            payload = row.data_after if isinstance(row.data_after, dict) else {}
            kind = payload.get("kind")
            if kind and kind not in seasons:
                seasons[kind] = payload
    return {"seasons": seasons}


POST_KIND_WATCHPOST = "watchpost"       # 초소
POST_KIND_PATROL_ZONE = "patrol_zone"   # 순찰 구역
POST_KIND_CHECKPOINT = "checkpoint"     # 순찰함(전자순찰함 · F1-02 등록 목록)
POST_KINDS = (POST_KIND_WATCHPOST, POST_KIND_PATROL_ZONE, POST_KIND_CHECKPOINT)

ACTION_POST_REGISTER = "office.post.register"


def register_post(*, scope, kind: str, code: str, name: str = "",
                  lat: float | None = None, lng: float | None = None,
                  note: str = "") -> dict:
    if kind not in POST_KINDS:
        raise OfficeInputRejected(
            f"kind={kind!r} 는 초소·구역 종류가 아니다. 허용: {POST_KINDS}")
    code = (code or "").strip()
    if not code:
        raise OfficeInputRejected("code 가 비었다 — 어느 초소·구역인지 없이는 등록이 뜻을 갖지 못한다")
    if len(code) > MAX_CODE_CHARS:
        raise OfficeInputRejected(f"code 가 {len(code)}자다. 상한은 {MAX_CODE_CHARS}자")
    name = (name or "").strip()[:MAX_NAME_CHARS]
    note = _check_note(note)
    actor = scope.require_actor()
    location = {"lat": lat, "lng": lng} if (lat is not None and lng is not None) else None
    payload = {"kind": kind, "code": code, "name": name, "lat": lat, "lng": lng,
              "note": note, "registered_at": _now_iso()}
    entry = _write(actor, ACTION_POST_REGISTER, payload,
                  f"{kind} {code} 등록" + (f" · 위치 {location}" if location else ""))
    return {"post_id": entry.audit_id, **payload}


def registered_posts(*, scope, kind: str = "") -> dict:
    actor = scope.require_actor()
    user_ids = _group_user_ids(actor)
    by_code: dict[str, dict] = {}
    if user_ids:
        rows = (_audit_model()._base_manager.filter(
            logger_name=LOGGER_NAME, api_name=ACTION_POST_REGISTER,
            user_id__in=user_ids).order_by("id")[:5000])
        for row in rows:
            payload = row.data_after if isinstance(row.data_after, dict) else {}
            if kind and payload.get("kind") != kind:
                continue
            code = payload.get("code")
            if code:
                by_code[code] = payload  # 최신이 옛 등록을 덮는다(재등록 = 갱신)
    items = list(by_code.values())
    return {"posts": items, "count": len(items)}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-03 인력 배치 — 감시원·대응단 근무표(CSV) · 야간 5분대기조
# ═══════════════════════════════════════════════════════════════════════════
MAX_ROSTER_ROWS = 500
ROSTER_REQUIRED_COLUMNS = ("name", "role", "shift_date", "shift_type")
#: 야간 5분대기조 표시값 — CSV 의 `night_standby_5min` 칸에 이 문자열 중 하나가
#: 오면 참으로 읽는다(annex §5.3 FWS-F3-03 원문 "야간 5분대기조").
_TRUTHY = {"1", "true", "y", "yes", "on", "참"}

ACTION_ROSTER_UPLOAD = "office.roster.upload"


def upload_roster(*, scope, csv_text: str) -> dict:
    import csv
    import io

    csv_text = (csv_text or "").strip()
    if not csv_text:
        raise OfficeInputRejected("csv_text 가 비었다")
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        raise OfficeInputRejected("CSV 머리글을 읽지 못했다")
    missing_cols = [c for c in ROSTER_REQUIRED_COLUMNS if c not in reader.fieldnames]
    if missing_cols:
        raise OfficeInputRejected(f"CSV 머리글에 칸이 없다: {missing_cols}")

    rows = list(reader)
    if len(rows) > MAX_ROSTER_ROWS:
        raise OfficeInputRejected(f"근무표가 {len(rows)}행이다. 상한은 {MAX_ROSTER_ROWS}행")

    entries = []
    for i, row in enumerate(rows):
        name = (row.get("name") or "").strip()
        role = (row.get("role") or "").strip()
        shift_date = (row.get("shift_date") or "").strip()
        shift_type = (row.get("shift_type") or "").strip()
        if not name or not role or not shift_date:
            raise OfficeInputRejected(f"근무표 {i+1}행에 name·role·shift_date 가 없다")
        night_flag = (row.get("night_standby_5min") or "").strip().lower() in _TRUTHY
        #: P-452 — 담당 초소는 **그날 편성표의 배정**이다. 선택 칸 `post_code`(초소 코드)를
        #: 그대로 싣는다. 비어 있으면 「미배정」이다 — 지어내지 않는다.
        post_code = (row.get("post_code") or "").strip()[:MAX_CODE_CHARS]
        entries.append({
            "name": name, "role": role, "shift_date": shift_date,
            "shift_type": shift_type, "night_standby_5min": night_flag,
            "post_code": post_code,
        })

    actor = scope.require_actor()
    payload = {"rows": entries, "count": len(entries), "uploaded_at": _now_iso(),
              "uploaded_by": getattr(actor, "username", "")}
    entry = _write(actor, ACTION_ROSTER_UPLOAD, payload,
                  f"근무표 업로드 {len(entries)}행")
    return {"roster_id": entry.audit_id, **payload}


def current_roster(*, scope) -> dict:
    actor = scope.require_actor()
    user_ids = _group_user_ids(actor)
    if not user_ids:
        return {"rows": [], "count": 0, "uploaded_at": None}
    row = (_audit_model()._base_manager.filter(
        logger_name=LOGGER_NAME, api_name=ACTION_ROSTER_UPLOAD,
        user_id__in=user_ids).order_by("-id").first())
    if row is None:
        return {"rows": [], "count": 0, "uploaded_at": None}
    payload = row.data_after if isinstance(row.data_after, dict) else {}
    return {"rows": payload.get("rows", []), "count": payload.get("count", 0),
           "uploaded_at": payload.get("uploaded_at")}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-04 탐지 확인 요청 1클릭 · 10분 시계 (완결조건: 요청 발송 · 10분 시계 —
# annex §5.3 표. 「가장 가까운」은 §6 FF-2 의 UX 힌트 — 감시원은 값을 내고,
# 드론은 정직하게 빈 값(머리말 참조))
# ═══════════════════════════════════════════════════════════════════════════
ACTION_VERIFICATION_REQUEST = "office.verification.request"


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2)
    return 2 * r_km * math.asin(min(1.0, math.sqrt(a)))


def _nearest_officers(*, user_ids: list[int], event_lat, event_lng,
                      limit: int = 5) -> list[dict]:
    """오늘 체크인한 사람 중 사건 좌표에 가장 가까운 순 — 좌표가 하나라도
    없으면(사건 또는 사람) 빈 목록(D-284 — 지어내지 않는다)."""
    if event_lat is None or event_lng is None or not user_ids:
        return []
    rows = (_audit_model()._base_manager.filter(
        logger_name=fws_patrol.LOGGER_NAME, api_name=fws_patrol.ACTION_CHECKIN,
        user_id__in=user_ids).order_by("user_id", "-id")[:5000])
    out = []
    for row in _latest_per_user(rows).values():
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        lat, lng = payload.get("lat"), payload.get("lng")
        if lat is None or lng is None:
            continue
        dist = _haversine_km(event_lat, event_lng, lat, lng)
        out.append({"user_id": row.user_id, "post_code": payload.get("post_code"),
                   "distance_km": round(dist, 2)})
    out.sort(key=lambda o: o["distance_km"])
    return out[:limit]


def request_verification(*, scope, event_id: int, note: str = "") -> dict:
    """F3-04 — 1클릭 확인 요청. 발송은 `notify_event`(F1/F6 문 재사용) · 시계는
    이 파일이 더한다(10분)."""
    event = dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    note = _check_note(note)
    actor = scope.require_actor()
    now = timezone.now()
    deadline = now + timedelta(minutes=VERIFICATION_TIMEOUT_MINUTES)

    try:
        records = dsm_services.notify_event(scope=scope, event_id=event_id)
    except NoRecipients:
        records = ()

    user_ids = _group_user_ids(actor)
    suggested_officers = _nearest_officers(
        user_ids=user_ids, event_lat=event.lat, event_lng=event.lng)
    #: 드론 — 이 저장소에 실제 드론이 0대라 위치가 없다(머리말 · P-387). 빈
    #: 목록을 정직하게 낸다 — 지어내지 않는다.
    suggested_drones: list[dict] = []

    payload = {
        "event_id": event_id, "requested_at": now.isoformat(),
        "deadline_at": deadline.isoformat(),
        "timeout_minutes": VERIFICATION_TIMEOUT_MINUTES,
        "notified_count": len(records), "note": note,
        "suggested_officers": suggested_officers,
        "suggested_drones": suggested_drones,
    }
    entry = _write(actor, ACTION_VERIFICATION_REQUEST, payload,
                  f"탐지 확인 요청(1클릭) event_id={event_id}")
    return {"request_id": entry.audit_id, **payload}


def verification_requests(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    now_iso = _now_iso()
    rows = _rows_for_event(ACTION_VERIFICATION_REQUEST, event_id)
    items = []
    for row in rows:
        payload = dict(row.data_after) if isinstance(row.data_after, dict) else {}
        payload["expired"] = bool(payload.get("deadline_at")
                                  and now_iso > payload["deadline_at"])
        items.append(payload)
    return {"event_id": event_id, "count": len(items), "requests": items}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-05 오인 종결(사유) · 산불 확정 — **새 라우트 0** (P-397 재사용)
# ═══════════════════════════════════════════════════════════════════════════
#
# 이 절은 `apps.fws.verification.reply_verification`(F1-06)과 **완전히 같은
# 계약**이다 — 결과 3택(`fire_confirmed`/`false_alarm`/`cannot_access`) + 오인
# 사유 5택. 산림과 담당도 같은 테넌트 스코프로 같은 문(`POST /api/fws/
# verifications/{id}/reply`)을 그대로 두드린다 — 이 파일은 새 함수도 새 라우트도
# 열지 않는다(두 번째 판정 문을 세우면 D-212 위반 · P-397 이 금하는 것 그대로).
# `backend/tests/test_fws_f3a.py` 가 산림과 담당 역할로 그 문을 두드려 실측한다.


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-06 신고 접수 기록 — 119/산림청/시민 · 신고 시각 = 30분 시계 시작
# ═══════════════════════════════════════════════════════════════════════════
REPORT_SOURCE_119 = "fire_119"
REPORT_SOURCE_FOREST = "forest_service"
REPORT_SOURCE_CITIZEN = "citizen"
REPORT_SOURCES = (REPORT_SOURCE_119, REPORT_SOURCE_FOREST, REPORT_SOURCE_CITIZEN)

ACTION_INTAKE = "office.incident.intake"


def record_intake(*, scope, event_id: int, source: str,
                  reported_at: str = "", facility_note: str = "",
                  vehicle_access: bool | None = None, fire_intensity: str = "",
                  note: str = "") -> dict:
    """F3-06 — 신고 접수 기록. 이 사건은 **이미 K1 이벤트로 있어야 한다**
    (P-357 — 새 이벤트 표를 만들지 않는다). 카메라가 먼저 잡지 못한 「시민
    단독 신고」(카메라 관측 밖의 최초 신고)는 이 저장소가 이벤트를 짓는 문을
    이 App 층에 열어 두지 않아 담지 못한다 — 정직하게 범위 밖으로 남긴다
    (F-05 잠금 · P-357 이 만드는 한계 그대로, 지어내지 않는다)."""
    if source not in REPORT_SOURCES:
        raise OfficeInputRejected(
            f"source={source!r} 는 신고 출처가 아니다. 허용: {REPORT_SOURCES}")
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    note = _check_note(note)
    facility_note = (facility_note or "").strip()[:MAX_NOTE_CHARS]
    fire_intensity = (fire_intensity or "").strip()[:40]
    actor = scope.require_actor()
    reported_at = (reported_at or "").strip() or _now_iso()
    payload = {
        "event_id": event_id, "source": source, "reported_at": reported_at,
        "facility_note": facility_note, "vehicle_access": vehicle_access,
        "fire_intensity": fire_intensity, "note": note,
        "clock_started_at": reported_at,
        "clock_minutes": INTAKE_CLOCK_MINUTES,
    }
    entry = _write(actor, ACTION_INTAKE, payload, f"신고 접수 기록 source={source}")
    return {"intake_id": entry.audit_id, **payload}


def intake_records(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    rows = _rows_for_event(ACTION_INTAKE, event_id)
    items = [r.data_after for r in rows if isinstance(r.data_after, dict)]
    return {"event_id": event_id, "count": len(items), "intakes": items}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-07 산림청 상황실 통보 기록(042-481-4119) · 헬기 요청 기록(요청 시각·
# 기지·도착 예정)
# ═══════════════════════════════════════════════════════════════════════════
ACTION_AGENCY_NOTIFY = "office.agency_notify"


def notify_forest_agency(*, scope, event_id: int, helicopter_base: str = "",
                         helicopter_eta: str = "", note: str = "") -> dict:
    """F3-07 — 산림청 상황실 통보 + 헬기 요청 기록 한 문. 번호는
    `apps.fws.contacts.FOREST_REPORT_NUMBER`(F1-08)를 **그대로 읽는다** — 다시
    적지 않는다(머리말)."""
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    helicopter_base = (helicopter_base or "").strip()[:MAX_ORG_CHARS]
    helicopter_eta = (helicopter_eta or "").strip()
    note = _check_note(note)
    actor = scope.require_actor()
    now_iso = _now_iso()
    payload = {
        "event_id": event_id,
        "agency_phone": fws_contacts.FOREST_REPORT_NUMBER,
        "notified_at": now_iso,
        "helicopter_requested_at": now_iso if helicopter_base or helicopter_eta else None,
        "helicopter_base": helicopter_base or None,
        "helicopter_eta": helicopter_eta or None,
        "note": note,
    }
    entry = _write(actor, ACTION_AGENCY_NOTIFY, payload,
                  "산림청 상황실 통보 + 헬기 요청 기록")
    return {"notify_id": entry.audit_id, **payload}


def agency_notifications(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    rows = _rows_for_event(ACTION_AGENCY_NOTIFY, event_id)
    items = [r.data_after for r in rows if isinstance(r.data_after, dict)]
    return {"event_id": event_id, "count": len(items), "notifications": items}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-08 자원 배정 — 진화대·차량·드론을 사건에 배정(임무 문안 자동)
# ═══════════════════════════════════════════════════════════════════════════
RESOURCE_KIND_CREW = "crew"
RESOURCE_KIND_VEHICLE = "vehicle"
RESOURCE_KIND_DRONE = "drone"
RESOURCE_KINDS = (RESOURCE_KIND_CREW, RESOURCE_KIND_VEHICLE, RESOURCE_KIND_DRONE)

ACTION_RESOURCE_ASSIGN = "office.resource.assign"

_RESOURCE_LABEL = {
    RESOURCE_KIND_CREW: "진화대", RESOURCE_KIND_VEHICLE: "진화차",
    RESOURCE_KIND_DRONE: "드론",
}


def assign_resource(*, scope, event_id: int, kind: str, resource_name: str,
                    note: str = "") -> dict:
    """F3-08 — 자원 배정. 임무 문안은 **이 함수가 자동으로 짓는다**(완결조건
    "임무 문안 자동") — 저장·발송은 `field_reply`·`notify_event`(F2 임무·F6
    통보와 같은 재사용, 새 발송 경로를 만들지 않는다)."""
    if kind not in RESOURCE_KINDS:
        raise OfficeInputRejected(
            f"kind={kind!r} 는 자원 종류가 아니다. 허용: {RESOURCE_KINDS}")
    resource_name = (resource_name or "").strip()
    if not resource_name:
        raise OfficeInputRejected("resource_name 이 비었다 — 무엇을 배정했는지 없이는 배정이 아니다")
    if len(resource_name) > MAX_NAME_CHARS:
        raise OfficeInputRejected(f"resource_name 이 {len(resource_name)}자다. 상한은 {MAX_NAME_CHARS}자")
    note = _check_note(note)
    event = dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트

    label = _RESOURCE_LABEL[kind]
    mission_text = (f"[자원배정] {label} '{resource_name}' 배정 — 사건 #{event_id}"
                    f"({event.address or '주소 미상'}) 대응 바랍니다."
                    + (f" {note}" if note else ""))
    try:
        reply = dsm_services.field_reply(scope=scope, event_id=event_id, text=mission_text)
    except InvalidEventInput as exc:
        raise OfficeInputRejected(str(exc)) from exc

    try:
        records = dsm_services.notify_event(scope=scope, event_id=event_id)
    except NoRecipients:
        records = ()

    actor = scope.require_actor()
    payload = {
        "event_id": event_id, "kind": kind, "resource_name": resource_name,
        "note": note, "assigned_at": _now_iso(), "mission_text": mission_text,
        "reply_id": reply.reply_id, "notified_count": len(records),
    }
    entry = _write(actor, ACTION_RESOURCE_ASSIGN, payload,
                  f"자원배정 {kind}={resource_name}")
    return {"assignment_id": entry.audit_id, **payload}


def resource_assignments(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    rows = _rows_for_event(ACTION_RESOURCE_ASSIGN, event_id)
    items = [r.data_after for r in rows if isinstance(r.data_after, dict)]
    return {"event_id": event_id, "count": len(items), "assignments": items}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-09 대응단계 입력 3칸(면적·풍속·시설 우려) → 단계 제안 → F4 확정 요청
# ═══════════════════════════════════════════════════════════════════════════
ACTION_STAGE_PROPOSAL = "office.stage.proposal"


def propose_stage(*, scope, event_id: int, area_ha: float, wind_mps: float,
                  buildings_at_risk: int = 0, note: str = "") -> dict:
    """F3-09 — 3칸(면적·풍속·시설 우려) → `constants.compute_fire_stage`(P-386)
    로 단계 제안 → `notify_event` 로 F4(지휘)에 확정 요청(재사용 — 새 발송
    경로를 만들지 않는다)."""
    if area_ha < 0 or wind_mps < 0 or buildings_at_risk < 0:
        raise OfficeInputRejected("면적·풍속·시설 우려(건물수)는 음수일 수 없다")
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    note = _check_note(note)
    stage = fws_constants.compute_fire_stage(
        area_ha=area_ha, wind_mps=wind_mps, duration_hours=0.0,
        buildings_at_risk=buildings_at_risk)

    try:
        records = dsm_services.notify_event(scope=scope, event_id=event_id)
    except NoRecipients:
        records = ()

    actor = scope.require_actor()
    payload = {
        "event_id": event_id, "area_ha": area_ha, "wind_mps": wind_mps,
        "buildings_at_risk": buildings_at_risk, "proposed_stage": stage,
        "note": note, "proposed_at": _now_iso(),
        "status": "pending_f4_confirmation", "f4_notified_count": len(records),
    }
    entry = _write(actor, ACTION_STAGE_PROPOSAL, payload,
                  f"대응단계 제안 {stage}(면적{area_ha}ha·풍속{wind_mps}m/s)")
    return {"proposal_id": entry.audit_id, **payload}


def stage_proposals(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    rows = _rows_for_event(ACTION_STAGE_PROPOSAL, event_id)
    items = [r.data_after for r in rows if isinstance(r.data_after, dict)]
    return {"event_id": event_id, "count": len(items), "proposals": items}


__all__ = [
    "OfficeInputRejected",
    "dashboard",
    "SEASON_KINDS", "SEASON_KIND_DRY", "SEASON_KIND_SPECIAL",
    "set_season", "current_seasons",
    "POST_KINDS", "POST_KIND_WATCHPOST", "POST_KIND_PATROL_ZONE",
    "register_post", "registered_posts",
    "upload_roster", "current_roster", "ROSTER_REQUIRED_COLUMNS",
    "VERIFICATION_TIMEOUT_MINUTES", "request_verification", "verification_requests",
    "REPORT_SOURCES", "record_intake", "intake_records", "INTAKE_CLOCK_MINUTES",
    "notify_forest_agency", "agency_notifications",
    "RESOURCE_KINDS", "assign_resource", "resource_assignments",
    "propose_stage", "stage_proposals",
]
