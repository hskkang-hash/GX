# -*- coding: utf-8 -*-
"""DSM-U5-01·U5-03 — 시스템 관리자(운영·관리 방침 · 연계 설정) 로직 (annex §4.5 ·
턴 AN · WO-17 · 차선 N4).

새 표를 짓지 않는다 — `apps/dsm` 도 지금까지 자기 `models.py` 를 연 적이 없다
-------------------------------------------------------------------------------
이 파일도 `apps/fws/admin_settings.py` 와 같은 판단을 따른다(그 파일 머리말 참고) —
**일어난 일 한 줄이 정본**이고, 최신 줄이 「지금 값」을 답한다. 등록한 사람 자신의
최신 값만 낸다는 한계도 같다(감사 표에 테넌트 칼럼이 없다 — `apps/fws/patrol.py`
머리말의 실측). DSM-U5 도 annex §3 이 "정보통신과 담당 또는 관제센터 운영 담당"
한 자리로 그린다 — 단일 운영자 가정과 맞는다.

DSM-U5-01 「보관 기간 = 파기 정책 값」을 **어긋날 수 없게** 만든 방법
----------------------------------------------------------------------
방침 문서의 "보관 기간" 칸은 **이 파일이 값을 받는 칸이 아니다.** 그 수는
`apps.dsm.retention.retention_days()`(LAW-02a · 파기가 **실제로 보는** 그 수)를
그대로 읽어서 싣는다. 관리자가 따로 입력할 칸을 두면 "방침엔 30일, 파기는 90일"
같은 갈림이 생기고, 그 갈림이 바로 annex 완결조건이 막으려는 사고다(D-212 —
같은 값을 두 벌로 묻지 않는다).

DSM-U5-03 「연결 시험」이 **실제로 밖에 나가지 않는 이유**
------------------------------------------------------------
WO-17 지시서가 못박은 경계: 이 절은 **설정 값(끝점 이름·상태)만** 다루고 외부
호출은 하지 않는다. 그래서 `test_integration_connection` 은 네트워크를 두드리지
않는다 — **설정이 갖춰졌는가**(끝점 이름 + 자격 참조명 둘 다 있는가)만 보고
"정상/대기/끊김" 한 단어를 낸다. 실제 연동 시험(진짜 핸드셰이크)은 이번 차선
범위 밖이다(대표 승인이 필요한 실외부 연동 — `apps/fws/integration.py` 머리말과
같은 판단).

★ 비밀 값은 어디에도 없다 — `outbound_api_key_ref` 는 **참조 이름**뿐이다
---------------------------------------------------------------------------
저장하는 것은 "그 자격증명이 어떤 이름으로 선언돼 있는가"(예: 환경변수 이름)
뿐이고, 실제 키 값은 이 파일 어디에도 들어오지 않는다(WO-17 지시서 원문 —
"키 값은 저장하지 않고 이름만"). 필드 이름에 `outbound_` 방향을 붙인 것은
`scripts/verify_homonyms.py` 의 동음이의 게이트(D-337 — 방향 없이 쓰면 안
되는 이름이 있다)를 그대로 따른 것이다.
"""
from __future__ import annotations

from django.apps import apps
from django.utils import timezone

from apps.dsm.retention import retention_days, retention_source
from common import audit_writer

LOGGER_NAME = "guardianx.dsm.admin_u5_an"
TAG = "[DSM-U5-AN]"


class U5AnInputRejected(Exception):
    """값이 계약 밖이다 — 422."""


class U5AnPermissionDenied(Exception):
    """관리자가 아니다 — 403."""


def _model():
    return apps.get_model("logger", "AuditLogs")


def require_admin(scope) -> None:
    """전역 관리 역할이거나 자기 테넌트의 운영 역할이어야 지난다 — `apps/fws/
    admin_settings.py::require_admin` 과 같은 판정식(`common.tenant_roles` 정본)."""
    from common.tenant_roles import is_global_admin, is_tenant_admin

    actor = scope.require_actor()
    if is_global_admin(actor) or is_tenant_admin(actor):
        return
    raise U5AnPermissionDenied(
        "이 설정은 관리자만 만질 수 있다 — 테넌트 운영 역할이나 전역 관리 역할이 필요하다")


def _write(actor, action: str, payload: dict, reason: str):
    return audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=action,
        outcome=audit_writer.ALLOWED, reason=reason, after=payload,
        api_name=action, api_method="POST")


def _now_iso() -> str:
    return timezone.now().isoformat()


def _latest_rows(*, action: str, user_id: int):
    return (_model()._base_manager
            .filter(logger_name=LOGGER_NAME, api_name=action, user_id=user_id)
            .order_by("-id"))


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U5-01 — 운영·관리 방침 항목 관리
# ═══════════════════════════════════════════════════════════════════════════
ACTION_POLICY_SAVE = "u5an.privacy_policy_save"

MAX_POLICY_FIELD_CHARS = 300

#: 관리자가 채우는 항목 — annex 원문 순서(설치 목적·위치·촬영 범위·관리책임자·
#: 접근권한자·촬영 시간·열람 절차). "대수"·"보관 기간"은 여기 없다 — 아래
#: `privacy_policy()` 가 **실측값**으로 채운다(손으로 적는 칸이 아니다).
POLICY_FIELDS: tuple[str, ...] = (
    "purpose", "install_locations", "filming_scope", "responsible_person",
    "access_grantees", "filming_hours", "viewing_procedure",
)

POLICY_FIELD_LABELS: dict[str, str] = {
    "purpose": "설치 목적", "install_locations": "설치 위치", "filming_scope": "촬영 범위",
    "responsible_person": "관리책임자", "access_grantees": "접근권한자",
    "filming_hours": "촬영 시간", "viewing_procedure": "열람 절차",
}


def _installed_camera_count(scope) -> int:
    """지금 이 테넌트에 실재하는 카메라 대수 — **손으로 적지 않는다**(D-330 계열).
    관리자가 "대수" 를 잘못 옮겨 적어 카메라 대수가 실물과 어긋나는 사고를
    원천에서 막는다."""
    from common.tenant_filters import get_user_group
    from common.tenant_roles import is_global_admin
    from stream_monitors.models import StreamMonitor

    actor = scope.require_actor()
    qs = StreamMonitor.objects.all()
    if not is_global_admin(actor):
        group = get_user_group(actor)
        group_id = getattr(group, "pk", None)
        if group_id is None:
            return 0
        qs = qs.filter(group_id=group_id)
    return qs.count()


def _policy_document_text(values: dict) -> str:
    """방침 문서 자동 생성 — **텍스트 한 장**(PDF 조판은 범위 밖, 아래 참고).

    ★ 정직하게 남긴다: annex 표는 "방침 PDF"를 출력으로 든다. 이 함수는 PDF 조판
      (`K4` 서식·글꼴·페이지 나누기)을 새로 짓지 않는다 — 같은 항목을 사람이 읽을
      수 있는 문서 텍스트로 조립하는 것까지가 이 차선의 범위다. 제목이 부르는
      "문서 자동 생성"의 알맹이(항목이 모여 한 장의 글이 된다)는 이 함수가 채우고,
      "PDF" 라는 파일 형식은 채우지 못한다 — `N4_promotions_an.md` 의 「무엇이
      없는가」에 같은 문장을 남긴다.
    """
    lines = ["GuardianX 재난안전관리 App — 영상정보 운영·관리 방침", ""]
    for field in POLICY_FIELDS:
        lines.append(f"· {POLICY_FIELD_LABELS[field]}: {values.get(field) or '(미입력)'}")
    lines.append(f"· 설치 대수: {values['installed_camera_count']}대(실측)")
    retention = values["retention_days"]
    lines.append(
        "· 보관 기간: "
        + (f"{retention}일(파기 정책과 같은 값)" if retention is not None else "미선언"))
    return "\n".join(lines)


def save_privacy_policy(*, scope, purpose: str = "", install_locations: str = "",
                        filming_scope: str = "", responsible_person: str = "",
                        access_grantees: str = "", filming_hours: str = "",
                        viewing_procedure: str = "") -> dict:
    require_admin(scope)
    values = {
        "purpose": purpose, "install_locations": install_locations,
        "filming_scope": filming_scope, "responsible_person": responsible_person,
        "access_grantees": access_grantees, "filming_hours": filming_hours,
        "viewing_procedure": viewing_procedure,
    }
    for field, value in values.items():
        if len(value or "") > MAX_POLICY_FIELD_CHARS:
            raise U5AnInputRejected(
                f"{POLICY_FIELD_LABELS[field]} 이 {len(value)}자다. "
                f"상한은 {MAX_POLICY_FIELD_CHARS}자")
    actor = scope.require_actor()
    payload = {**values, "saved_at": _now_iso()}
    _write(actor, ACTION_POLICY_SAVE, payload, "영상정보 운영·관리 방침 저장")
    return privacy_policy(scope=scope)


def privacy_policy(*, scope) -> dict:
    """지금 방침 — 관리자가 적은 항목 + **실측 대수** + **실측 보관 기간**(파기
    정책과 같은 값) + 자동 생성 문서 텍스트."""
    require_admin(scope)
    actor = scope.require_actor()
    row = _latest_rows(action=ACTION_POLICY_SAVE, user_id=actor.pk).first()
    values = {field: "" for field in POLICY_FIELDS}
    saved_at = None
    if row is not None and isinstance(row.data_after, dict):
        for field in POLICY_FIELDS:
            values[field] = row.data_after.get(field, "")
        saved_at = row.data_after.get("saved_at")

    values["installed_camera_count"] = _installed_camera_count(scope)
    values["retention_days"] = retention_days()
    values["retention_source"] = retention_source()
    values["saved_at"] = saved_at
    values["document_text"] = _policy_document_text(values)
    return values


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U5-03 — 연계 설정(스마트시티 통합플랫폼·112·119·NDMS)
# ═══════════════════════════════════════════════════════════════════════════
SERVICE_SMART_CITY = "smart_city"
SERVICE_POLICE_112 = "police_112"
SERVICE_FIRE_119 = "fire_119"
SERVICE_NDMS = "ndms"
SERVICES: tuple[str, ...] = (SERVICE_SMART_CITY, SERVICE_POLICE_112, SERVICE_FIRE_119,
                            SERVICE_NDMS)

SERVICE_LABELS: dict[str, str] = {
    SERVICE_SMART_CITY: "스마트시티 통합플랫폼", SERVICE_POLICE_112: "112 종합상황실",
    SERVICE_FIRE_119: "119 상황실", SERVICE_NDMS: "NDMS(재난관리시스템)",
}

#: 상태 한 단어 — annex 원문 "정상/대기/끊김" 그대로.
STATUS_OK = "정상"
STATUS_WAITING = "대기"
STATUS_DISCONNECTED = "끊김"

ACTION_INTEGRATION_SAVE = "u5an.integration_save"
ACTION_INTEGRATION_TEST = "u5an.integration_test"

MAX_ENDPOINT_NAME_CHARS = 120
MAX_KEY_REF_CHARS = 120


def _latest_service_row(actor, service: str):
    for row in _latest_rows(action=ACTION_INTEGRATION_SAVE, user_id=actor.pk):
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        if payload.get("service") == service:
            return payload
    return None


def _latest_test_row(actor, service: str):
    for row in _latest_rows(action=ACTION_INTEGRATION_TEST, user_id=actor.pk):
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        if payload.get("service") == service:
            return payload
    return None


def _status_word(endpoint_name: str, outbound_api_key_ref: str, tested_ok: bool | None) -> str:
    if not endpoint_name and not outbound_api_key_ref:
        return STATUS_DISCONNECTED
    if not endpoint_name or not outbound_api_key_ref:
        return STATUS_WAITING
    if tested_ok:
        return STATUS_OK
    return STATUS_WAITING


def save_integration_endpoint(*, scope, service: str, endpoint_name: str = "",
                              outbound_api_key_ref: str = "") -> dict:
    """끝점 이름 · 자격 **참조명**만 저장한다 — 값(비밀)은 어디에도 싣지 않는다."""
    require_admin(scope)
    if service not in SERVICES:
        raise U5AnInputRejected(f"service={service!r} 는 연계서비스가 아니다. 허용: {SERVICES}")
    if len(endpoint_name or "") > MAX_ENDPOINT_NAME_CHARS:
        raise U5AnInputRejected(f"endpoint_name 이 {len(endpoint_name)}자다. "
                                f"상한은 {MAX_ENDPOINT_NAME_CHARS}자")
    if len(outbound_api_key_ref or "") > MAX_KEY_REF_CHARS:
        raise U5AnInputRejected(f"outbound_api_key_ref 가 {len(outbound_api_key_ref)}자다. "
                                f"상한은 {MAX_KEY_REF_CHARS}자")
    actor = scope.require_actor()
    payload = {
        "service": service, "endpoint_name": (endpoint_name or "").strip(),
        "outbound_api_key_ref": (outbound_api_key_ref or "").strip(),
        "saved_at": _now_iso(),
    }
    _write(actor, ACTION_INTEGRATION_SAVE, payload,
          f"연계 설정 저장 service={service}")
    return integration_endpoint(scope=scope, service=service)


def integration_endpoint(*, scope, service: str) -> dict:
    require_admin(scope)
    if service not in SERVICES:
        raise U5AnInputRejected(f"service={service!r} 는 연계서비스가 아니다. 허용: {SERVICES}")
    actor = scope.require_actor()
    config = _latest_service_row(actor, service) or {
        "service": service, "endpoint_name": "", "outbound_api_key_ref": "", "saved_at": None}
    test = _latest_test_row(actor, service)
    tested_ok = test.get("tested_ok") if test else None
    tested_at = test.get("tested_at") if test else None
    status = _status_word(config.get("endpoint_name", ""),
                          config.get("outbound_api_key_ref", ""), tested_ok)
    return {"service": service, "label": SERVICE_LABELS[service],
           "endpoint_name": config.get("endpoint_name", ""),
           "outbound_api_key_ref": config.get("outbound_api_key_ref", ""),
           "saved_at": config.get("saved_at"), "status": status,
           "tested_at": tested_at}


def list_integrations(*, scope) -> dict:
    require_admin(scope)
    return {"integrations": [integration_endpoint(scope=scope, service=s) for s in SERVICES]}


def test_integration_connection(*, scope, service: str) -> dict:
    """연결 시험 — **외부로 나가지 않는다**(머리말 참고). 설정이 갖춰졌는가만 본다."""
    require_admin(scope)
    if service not in SERVICES:
        raise U5AnInputRejected(f"service={service!r} 는 연계서비스가 아니다. 허용: {SERVICES}")
    actor = scope.require_actor()
    config = _latest_service_row(actor, service) or {"endpoint_name": "", "outbound_api_key_ref": ""}
    tested_ok = bool(config.get("endpoint_name")) and bool(config.get("outbound_api_key_ref"))
    payload = {"service": service, "tested_ok": tested_ok, "tested_at": _now_iso()}
    _write(actor, ACTION_INTEGRATION_TEST, payload,
          f"연계 설정 연결 시험 service={service} tested_ok={tested_ok}")
    return integration_endpoint(scope=scope, service=service)


__all__ = [
    "U5AnInputRejected", "U5AnPermissionDenied", "require_admin",
    "POLICY_FIELDS", "POLICY_FIELD_LABELS",
    "save_privacy_policy", "privacy_policy",
    "SERVICES", "SERVICE_LABELS", "STATUS_OK", "STATUS_WAITING", "STATUS_DISCONNECTED",
    "save_integration_endpoint", "integration_endpoint", "list_integrations",
    "test_integration_connection",
]
