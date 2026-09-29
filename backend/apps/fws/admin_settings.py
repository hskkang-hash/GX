# -*- coding: utf-8 -*-
"""FWS-U5-01~04 — 기관 관리자(산불 설정) 로직 (annex §5.7 · 턴 AN · WO-17 · 차선 N4).

무엇을 새로 짓지 않았나 — `patrol.py`·`standby.py`·`integration.py` 와 같은 판단
--------------------------------------------------------------------------------
이 파일도 새 표 + 마이그레이션을 세우지 않는다. `apps/fws` 는 지금까지 `models.py` 를
한 번도 연 적이 없다(그 자체가 이 저장소가 굳힌 관례다) — 새로 여는 것은 이번 한 절의
값을 위해 이 App 전체의 마이그레이션 상태를 처음으로 만드는 일이고, 그 반경은 차선
하나가 짊어지기엔 너무 크다. 그래서 여기서도 **일어난 일 한 줄이 정본**이다
(`patrol.py` 머리말과 같은 뜻) — 최신 줄이 「지금 값」을 답한다.

★ 좁히기 — 무엇이 테넌트로 안전하고 무엇이 「내 것만」인가
-------------------------------------------------------------
    카메라 표식(U5-01)   `camera_id` 로 좁힌다 — `StreamMonitor.group` 이 이미
                        테넌트를 정하므로(`_camera()` 가 그 카메라가 **내 테넌트**
                        것인지 먼저 확인), 그 뒤에 `camera_id` 로 감사 행을 읽어도
                        새지 않는다(`integration.py::_rows_for_event` 와 같은 근거).
    초소·순찰함(U5-02)   `post_code` 는 자유 문자열이라 그 자체로는 테넌트를 정하지
                        못한다(두 지자체가 같은 코드 "P-12" 를 쓸 수 있다). 예전엔
                        그래서 **등록한 사람 자신의 최신 값만** 냈다(`standby.py`·
                        `liaison.my_latest_risk_forecast` 와 같은 한계 — 감사 표에
                        테넌트 칼럼이 없다, `patrol.py` 머리말). **턴 AO 차선 O ·
                        P-411 이 이 한계를 넘는다** — `apps/fws/audit_scope.py`
                        곁표(`common.models.AuditScope`)가 「그 감사 행이 어느
                        테넌트 것인가」를 따로 적어 두므로, 이제 **같은 테넌트의
                        관리자 전원**이 서로의 등록을 본다(post_code 가 같아도
                        테넌트가 다르면 섞이지 않는다 — 곁표가 그 둘을 가른다).
    마을·대피소(U5-03)   같은 한계·같은 고침.
    알림 규칙(U5-04)     새 저장을 짓지 않는다 — `kernels.k2_notify.rule_admin`
                        (S-16 화면의 서버 면, `NotificationRule` 실재 표)을 **그대로
                        재사용**한다. 그 표는 처음부터 테넌트 칼럼(`group`)이 있다 —
                        위 한계가 없다.

★ 관리자 판정 — `common.tenant_roles` 를 직접 부른다(D-212)
-------------------------------------------------------------
`apps.dsm.services.guard_setting` 과 같은 물음("전역 관리 역할인가 · 테넌트 운영
역할인가")을 이 파일도 묻는다. 그 판정식을 복사하지 않는다 — `is_global_admin`·
`is_tenant_admin`(둘 다 `common/tenant_roles.py` 의 유일한 정본)을 그대로 부른다.
`apps.dsm.services.guard_setting` 자체를 부르지 않는 이유는 그 함수가 DSM 의 감사
행(`apps.dsm.audit`)에 적기 때문이다 — 산불 앱의 관리자 판정이 DSM 감사 채널에
적히면 다음 사람이 "이게 왜 DSM 감사에 있지"를 다시 캐야 한다(§0.4 인접 — 두 앱의
감사는 각자의 `logger_name` 아래 남는다).
"""
from __future__ import annotations

import json as _json

from django.apps import apps
from django.utils import timezone

from common import audit_writer
from common.evidence_chain import strip_chain
from common.tenant_roles import is_global_admin, is_tenant_admin

from apps.fws import audit_scope as fws_audit_scope

LOGGER_NAME = "guardianx.fws.admin_u5"
TAG = "[FWS-U5]"


class AdminInputRejected(Exception):
    """값이 계약 밖이다 — 422."""


class AdminPermissionDenied(Exception):
    """관리자가 아니다 — 403."""


class AdminNotFound(Exception):
    """그런 대상이 없다(남의 테넌트 카메라 포함) — 404. 존재 여부도 새지 않는다(D-269)."""


def _model():
    return apps.get_model("logger", "AuditLogs")


def require_admin(scope) -> None:
    """전역 관리 역할이거나 **자기 테넌트의** 운영 역할이어야 지난다."""
    actor = scope.require_actor()
    if is_global_admin(actor) or is_tenant_admin(actor):
        return
    raise AdminPermissionDenied(
        "산불 설정은 관리자만 만질 수 있다 — 테넌트 운영 역할이나 전역 관리 역할이 필요하다")


def _write(actor, action: str, payload: dict, reason: str):
    return audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=action,
        outcome=audit_writer.ALLOWED, reason=reason, after=payload,
        api_name=action, api_method="POST")


def _now_iso() -> str:
    return timezone.now().isoformat()


def _latest_rows(*, action: str, user_id: int | None = None):
    qs = _model()._base_manager.filter(logger_name=LOGGER_NAME, api_name=action)
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    return qs.order_by("-id")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-U5-01 — 산불 감시 카메라 등록(고지대·PTZ 프리셋·열화상 채널·감시 반경)
# ═══════════════════════════════════════════════════════════════════════════
#
# 카메라 자체(이름·주소·스트림)는 **기존 문**(DSM 의 카메라 등록 — `stream_monitors.
# StreamMonitor` · `apps/dsm/api.py POST /cameras/import`)이 만든다. 이 파일은 그
# 문을 다시 열지 않는다 — 여기서 더하는 것은 annex 가 요구하는 **산불 표식**
# (고지대 여부·PTZ 프리셋 이름·열화상 채널·감시 반경) 뿐이다. `stream_monitors` 는
# `backend/apps/` 밖(레거시 공용 App)이라 D-278 층 게이트가 막지 않는다 — `apps/dsm/
# api_u56.py::set_camera_address` 가 이미 같은 모델을 같은 방식으로 만진다(전례).
ACTION_CAMERA_MARKER = "admin.camera_fire_marker"


def _camera(scope, camera_id: int):
    """내 테넌트의 그 카메라. 남의 것이면 `None`(→ 404, D-269) — `api_u56.py::
    _one_camera` 와 같은 판단(전역 관리자는 전체, 그 밖은 자기 group 으로 좁힌다)."""
    from common.tenant_filters import get_user_group
    from stream_monitors.models import StreamMonitor

    actor = scope.require_actor()
    qs = StreamMonitor.objects.all()
    if not is_global_admin(actor):
        group = get_user_group(actor)
        group_id = getattr(group, "pk", None)
        if group_id is None:
            return None
        qs = qs.filter(group_id=group_id)
    return qs.filter(pk=camera_id).first()


def _default_marker(camera_id: int) -> dict:
    return {"camera_id": camera_id, "is_highland": False, "thermal_channel": "",
           "ptz_presets": [], "radius_polygon": [], "saved_at": None}


def _parse_polygon(raw: str | None) -> list:
    """`radius_polygon_json` — 감시 반경 폴리곤. **값만** 오간다(`apps/fws/drone.py::
    _parse_points_json` 과 같은 규약 — django-ninja 원시 인자는 질의뿐이라 좌표
    목록은 JSON 문자열로 받는다). 판정(폴리곤 안/밖)은 짓지 않는다 — 여기서
    내는 것은 저장·재조회뿐이다."""
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        parsed = _json.loads(raw)
    except ValueError as exc:
        raise AdminInputRejected("radius_polygon_json 이 올바른 JSON 이 아니다") from exc
    if not isinstance(parsed, list):
        raise AdminInputRejected("radius_polygon_json 은 좌표 배열이어야 한다")
    out = []
    for i, p in enumerate(parsed):
        if not isinstance(p, dict) or "lat" not in p or "lng" not in p:
            raise AdminInputRejected(f"radius_polygon_json[{i}] 에 lat/lng 가 없다")
        try:
            out.append({"lat": float(p["lat"]), "lng": float(p["lng"])})
        except (TypeError, ValueError) as exc:
            raise AdminInputRejected(f"radius_polygon_json[{i}] 의 좌표가 숫자가 아니다") from exc
    return out


def save_camera_fire_marker(*, scope, camera_id: int, is_highland: bool = False,
                            thermal_channel: str = "", ptz_presets: str = "",
                            radius_polygon_json: str = "") -> dict:
    """산불 표식 한 대 저장. `ptz_presets` 는 쉼표 문자열(이 저장소의 `event_types`
    관용과 같다 — `apps/dsm/api_u56.py::issue_webhook_subscription` 참고).
    `radius_polygon_json` 은 좌표 배열 JSON 문자열이다(annex "감시 반경 폴리곤")."""
    require_admin(scope)
    cam = _camera(scope, camera_id)
    if cam is None:
        raise AdminNotFound(f"camera_id={camera_id} 가 없다")
    polygon = _parse_polygon(radius_polygon_json)
    presets = [p.strip() for p in (ptz_presets or "").split(",") if p.strip()]
    actor = scope.require_actor()
    payload = {
        "camera_id": camera_id, "is_highland": bool(is_highland),
        "thermal_channel": (thermal_channel or "").strip(),
        "ptz_presets": presets, "radius_polygon": polygon,
        "saved_at": _now_iso(),
    }
    _write(actor, ACTION_CAMERA_MARKER, payload,
          f"카메라 {camera_id} 산불 표식 저장(고지대={bool(is_highland)})")
    return payload


def camera_fire_marker(*, scope, camera_id: int) -> dict:
    """지금 표식. 저장한 적 없으면 정직한 기본값(D-284).

    ★ `strip_chain` — `common/audit_writer.py::write` 가 저장 뒤 `data_after` 에
      LAW-08 해시 체인 예약 칸(`__hash__`·`__prev_hash__`·`__seq__`)을 덧붙인다.
      `patrol.py`·`standby.py` 는 특정 키만 `.get()` 으로 골라 그 칸이 안 보였을
      뿐 — 이 함수처럼 **저장한 값 그대로**를 응답으로 낼 때는 그 세 칸을 먼저
      떼어야 재조회 값이 저장한 값과 정확히 같아진다.
    """
    require_admin(scope)
    cam = _camera(scope, camera_id)
    if cam is None:
        raise AdminNotFound(f"camera_id={camera_id} 가 없다")
    for row in _latest_rows(action=ACTION_CAMERA_MARKER):
        payload = strip_chain(row.data_after) if isinstance(row.data_after, dict) else {}
        if isinstance(payload, dict) and payload.get("camera_id") == camera_id:
            return payload
    return _default_marker(camera_id)


def list_fire_cameras(*, scope) -> dict:
    """내 테넌트 카메라 전부 + 각 대의 산불 표식(없으면 기본값)."""
    require_admin(scope)
    from common.tenant_filters import get_user_group
    from stream_monitors.models import StreamMonitor

    actor = scope.require_actor()
    qs = StreamMonitor.objects.all()
    if not is_global_admin(actor):
        group = get_user_group(actor)
        group_id = getattr(group, "pk", None)
        qs = qs.filter(group_id=group_id) if group_id is not None else qs.none()
    cams = list(qs.order_by("id")[:500])

    markers: dict[int, dict] = {}
    for row in _latest_rows(action=ACTION_CAMERA_MARKER):
        payload = strip_chain(row.data_after) if isinstance(row.data_after, dict) else {}
        cid = payload.get("camera_id") if isinstance(payload, dict) else None
        if isinstance(cid, int) and cid not in markers:
            markers[cid] = payload

    return {
        "cameras": [
            {"camera_id": c.pk, "name": c.name,
             **(markers.get(c.pk) or _default_marker(c.pk))}
            for c in cams
        ],
        "count": len(cams),
    }


# ═══════════════════════════════════════════════════════════════════════════
# FWS-U5-02 — 초소·순찰함(NFC)·순찰 구역 등록
# ═══════════════════════════════════════════════════════════════════════════
#
# `patrol.py` 의 `checkin`/`track` 은 **어떤 `post_code` 든** 받는다(그 파일 머리말이
# 이미 그렇게 설계했다 — 표를 세우지 않고 감사 한 줄로 충분하다는 판단). 이 절이
# 더하는 것은 그 초소에 **이름·좌표·순찰 구역·순찰함(NFC) 코드 목록**을 등록하는
# 자리다 — 등록이 없어도 체크인은 여전히 되지만(하위호환), 등록이 있으면 관리자
# 화면이 「이 초소가 무엇인지」를 사람의 말로 보여준다.
ACTION_POST_SAVE = "admin.post_register"

MAX_POST_NAME_CHARS = 80


def save_post(*, scope, post_code: str, name: str, patrol_zone: str = "",
              lat: float | None = None, lng: float | None = None,
              nfc_boxes: str = "") -> dict:
    """초소 하나를 등록/갱신한다. `nfc_boxes` 는 쉼표 문자열(순찰함 코드 목록)."""
    require_admin(scope)
    code = (post_code or "").strip()
    if not code:
        raise AdminInputRejected("post_code 가 비었다 — 어느 초소인지 없이는 등록이 아니다")
    label = (name or "").strip()
    if not label:
        raise AdminInputRejected("name 이 비었다")
    if len(label) > MAX_POST_NAME_CHARS:
        raise AdminInputRejected(f"name 이 {len(label)}자다. 상한은 {MAX_POST_NAME_CHARS}자")
    boxes = [b.strip() for b in (nfc_boxes or "").split(",") if b.strip()]
    payload = {
        "post_code": code, "name": label, "patrol_zone": (patrol_zone or "").strip(),
        "lat": lat, "lng": lng, "nfc_boxes": boxes, "saved_at": _now_iso(),
    }
    fws_audit_scope.record(
        scope=scope, logger_name=LOGGER_NAME, tag=TAG, action=ACTION_POST_SAVE,
        payload=payload, reason=f"초소 {code} 등록/갱신", kind=ACTION_POST_SAVE)
    return payload


def _tenant_rows(scope, action: str):
    """이 **테넌트**의 감사 전건 — 곁표(`audit_scope.py`)로 좁힌 `AuditLogs` 행
    (`_latest_rows` 의 테넌트 판 · 턴 AO 차선 O · P-411)."""
    ids = fws_audit_scope.tenant_audit_ids(scope=scope, kind=action)
    if not ids:
        return _model()._base_manager.none()
    return _model()._base_manager.filter(
        logger_name=LOGGER_NAME, api_name=action, id__in=ids).order_by("-id")


def my_posts(*, scope) -> dict:
    """이 **테넌트**의 관리자 전원이 등록한 초소 전부 — 최신 코드당 한 줄(턴 AO
    차선 O · P-411, 예전엔 "등록한 사람 자신만" 이었다 · 머리말 참고)."""
    require_admin(scope)
    seen: dict[str, dict] = {}
    for row in _tenant_rows(scope, ACTION_POST_SAVE):
        payload = strip_chain(row.data_after) if isinstance(row.data_after, dict) else {}
        code = payload.get("post_code") if isinstance(payload, dict) else None
        if isinstance(code, str) and code not in seen:
            seen[code] = payload
    return {"posts": list(seen.values()), "count": len(seen)}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-U5-03 — 마을·대피소·요양시설 등록(대피 대상 자동 산출)
# ═══════════════════════════════════════════════════════════════════════════
EVAC_KIND_VILLAGE = "village"
EVAC_KIND_SHELTER = "shelter"
EVAC_KIND_CARE_FACILITY = "care_facility"
EVAC_KINDS: tuple[str, ...] = (EVAC_KIND_VILLAGE, EVAC_KIND_SHELTER, EVAC_KIND_CARE_FACILITY)

ACTION_EVAC_ENTITY_SAVE = "admin.evac_entity_register"

MAX_EVAC_NAME_CHARS = 80


def save_evac_entity(*, scope, kind: str, name: str, headcount: int,
                     note: str = "") -> dict:
    """마을(주민 수)·대피소(수용 인원)·요양시설(입소자 수) 한 곳을 등록/갱신한다.

    `headcount` 의 뜻은 `kind` 로 갈린다 — 마을·요양시설은 **대피 대상 인원**,
    대피소는 **수용 인원**이다. 한 칸에 뜻을 둘 섞지 않는다(D-301 과 같은 결).
    """
    require_admin(scope)
    if kind not in EVAC_KINDS:
        raise AdminInputRejected(f"kind={kind!r} 는 대피 대상 종류가 아니다. 허용: {EVAC_KINDS}")
    label = (name or "").strip()
    if not label:
        raise AdminInputRejected("name 이 비었다")
    if len(label) > MAX_EVAC_NAME_CHARS:
        raise AdminInputRejected(f"name 이 {len(label)}자다. 상한은 {MAX_EVAC_NAME_CHARS}자")
    if headcount < 0:
        raise AdminInputRejected("headcount 는 음수일 수 없다")
    payload = {
        "kind": kind, "name": label, "headcount": int(headcount),
        "note": note, "saved_at": _now_iso(),
    }
    fws_audit_scope.record(
        scope=scope, logger_name=LOGGER_NAME, tag=TAG, action=ACTION_EVAC_ENTITY_SAVE,
        payload=payload, reason=f"대피 대상 등록/갱신 kind={kind} name={label}",
        kind=ACTION_EVAC_ENTITY_SAVE)
    return payload


def evac_targets(*, scope) -> dict:
    """이 **테넌트**의 관리자 전원이 등록한 마을·대피소·요양시설 전부 +
    **자동 산출한** 대피 대상 총원(턴 AO 차선 O · P-411, 예전엔 "등록한 사람
    자신만" 이었다 · 머리말 참고).

    "자동 산출"은 관리자가 총원을 손으로 입력하는 칸을 **아예 두지 않고**, 등록된
    마을·요양시설의 `headcount` 를 이 함수가 더해서 낸다는 뜻이다(annex 완결조건
    "대피 대상 자동 산출") — 합계 칸이 없으므로 등록 값과 어긋날 길이 없다(D-212).
    """
    require_admin(scope)
    seen: dict[tuple[str, str], dict] = {}
    for row in _tenant_rows(scope, ACTION_EVAC_ENTITY_SAVE):
        payload = strip_chain(row.data_after) if isinstance(row.data_after, dict) else {}
        key = (payload.get("kind"), payload.get("name")) if isinstance(payload, dict) else (None, None)
        if key[0] and key[1] and key not in seen:
            seen[key] = payload

    entities = list(seen.values())
    evacuee_target_total = sum(
        e["headcount"] for e in entities
        if e.get("kind") in (EVAC_KIND_VILLAGE, EVAC_KIND_CARE_FACILITY))
    shelter_capacity_total = sum(
        e["headcount"] for e in entities if e.get("kind") == EVAC_KIND_SHELTER)
    return {
        "entities": entities,
        "count": len(entities),
        "evacuee_target_total": evacuee_target_total,
        "shelter_capacity_total": shelter_capacity_total,
        "shelter_covers_target": shelter_capacity_total >= evacuee_target_total,
    }


# ═══════════════════════════════════════════════════════════════════════════
# FWS-U5-04 — 산불 알림 규칙(등급별 수신: 진화대·산림과·지휘·산림청) · 야간
# 5분대기조 채널 — **새 저장처를 짓지 않는다.** `kernels.k2_notify.rule_admin`
# (S-16 「알림 받는 사람·채널」의 서버 면 · 실재 `NotificationRule` 표)을 그대로
# 재사용한다. 이 절이 더하는 것은 **산불 화면이 고를 역할 이름 제안**과 **야간
# 5분대기조를 가리키는 구역(zone) 이름 하나**뿐이다 — 저장·판정·「심각 0명 금지」
# 문턱은 전부 K2 커널의 것이다(재사용 확인은 `test_fws_u5.py` 가 실측한다).
# ═══════════════════════════════════════════════════════════════════════════
#: 화면이 고를 수 있는 **역할 제안** — annex 원문 "진화대·산림과·지휘·산림청" 순서
#: 그대로다. `role_code` 자체는 자유 문자열이라(그 역할이 그 테넌트에 실재해야
#: 저장이 통과한다 · `kernels.k2_notify.services.save_notification_rule`) 이
#: 목록은 강제가 아니라 **제안**이다.
FWS_NOTIFY_ROLE_SUGGESTIONS: tuple[dict, ...] = (
    {"role_code": "fws_response_team", "label": "진화대"},
    {"role_code": "fws_forestry_dept", "label": "산림과"},
    {"role_code": "fws_command", "label": "지휘"},
    {"role_code": "fws_kfs_liaison", "label": "산림청"},
)

#: 야간 5분대기조 규칙을 가리키는 구역(zone) 이름. `save_rule(..., zone=...)` 에
#: 그대로 실어 저장하면 그 규칙이 "야간 채널" 임을 표시한다 — 같은 역할이라도
#: 주간 규칙과 야간 규칙을 다른 채널로 가를 수 있게 하는 것이 annex 의 요구다.
NIGHT_STANDBY_ZONE = "fws_night_standby"


def notify_rules_overview(*, scope) -> dict:
    """S-16 화면 그대로 — 등급별 도달·규칙 목록·채널·심각 막힘 여부 + 산불 제안."""
    require_admin(scope)
    from kernels.k2_notify import notify_rule_overview

    body = notify_rule_overview(scope=scope)
    return {**body, "role_suggestions": list(FWS_NOTIFY_ROLE_SUGGESTIONS),
           "night_standby_zone": NIGHT_STANDBY_ZONE}


def save_notify_rule(*, scope, severity: str, role_code: str, channels: str,
                     zone: str = "", is_active: bool = True,
                     rule_id: int = 0) -> dict:
    """규칙 하나를 저장한다 — 그대로 `kernels.k2_notify.save_rule` 에 위임한다."""
    require_admin(scope)
    from kernels.k2_notify import save_rule

    names = [c.strip() for c in (channels or "").split(",") if c.strip()]
    view = save_rule(
        scope=scope, severity=severity, role_code=role_code, channels=names,
        zone=(zone or "").strip() or None, is_active=is_active,
        rule_id=rule_id or None)
    return {"rule_id": view.rule_id, "severity": view.severity,
           "role_code": view.role_code, "zone": view.zone,
           "channels": list(view.channels), "is_active": view.is_active}


def test_notify_rule(*, scope, severity: str = "critical") -> dict:
    """시험 발송 — 그대로 `kernels.k2_notify.send_test_notification` 에 위임한다."""
    require_admin(scope)
    from kernels.k2_notify import send_test_notification

    return send_test_notification(scope=scope, severity=severity)


__all__ = [
    "AdminInputRejected", "AdminPermissionDenied", "AdminNotFound", "require_admin",
    "save_camera_fire_marker", "camera_fire_marker", "list_fire_cameras",
    "save_post", "my_posts",
    "EVAC_KINDS", "save_evac_entity", "evac_targets",
    "FWS_NOTIFY_ROLE_SUGGESTIONS", "NIGHT_STANDBY_ZONE",
    "notify_rules_overview", "save_notify_rule", "test_notify_rule",
]
