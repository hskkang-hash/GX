# -*- coding: utf-8 -*-
"""DSM-U5-02 앞 갈래 — **사람별 카메라·기능 권한** (`GET /api/dsm/access-log/permissions`).
차선 O · 턴 AM (P-376 「반쪽은 닫힘이 아니다」— 반쪽 메움).

이 파일이 왜 생겼나
--------------------
annex 제목 「접근권한·접속기록」의 앞 갈래(접근 권한 매트릭스)는 턴 AL(차선 N1)이
「부분 승격」으로 남겨 뒀다(`docs/agent/evidence/SPEC/N1_promotions.md` §AL) — 뒤
갈래(접속기록 조회·CSV, `access_log_service.py`)만 닫혔고, **사람마다 어느
카메라·어느 기능에 접근 가능한지** 보여주는 자리는 없었다(grep 재확인 —
`CameraPermission`·`권한관리` 류 이름이 0건 — N1 의 메모 그대로).

새 저장처·새 판정을 만들지 않는다 — 이미 있는 셋을 그대로 잇는다 (D-212)
------------------------------------------------------------------------
    기능 권한   `kernels.k3_dashboard` 의 역할→위젯 매트릭스(DA-03 §3-4, 이미 있다) ·
                `get_preset`(로그인 직후 화면) · `widget_permission`(위젯별 HIDDEN·
                VISIBLE·EDITABLE) 을 **사람마다 다시 부른다** — 판정식은 그 커널
                하나다.
    소속 사람   `common.tenant_filters.filter_users_by_group`(이미 있다).
    카메라 목록 `stream_monitors.services.camera_pulse.pulse_rows`(이미 있다 —
                `apps/dsm/services.py::camera_pulse`(UX-23)가 쓰는 바로 그 함수).
                **여기서 새로 짜지 않는다** — `StreamMonitor` 는
                `BaseModelWithGroup`(M2M `groups`)이라 `.objects.filter(group=...)`
                를 손으로 짜면 필드 이름부터 틀린다. `pulse_rows` 는 그 문지기
                (`_guess_group_lookup` · `_base_manager` · `is_active=True`)를
                이미 갖고 있다 — 저장소의 카메라 스코프 판단은 **이 함수 하나**다.

★ **카메라 권한의 실제 결(grain)을 있는 그대로 보고한다.** 이 제품에 사람별
  카메라 ACL 은 없다 — 카메라 접근은 **테넌트(그룹) 단위**다(F-05 의 IDOR 차단도
  전부 이 단위로 짠다, `kernels.k5_trust.services.resolve_threshold` 의
  `assert_scoped` 도 마찬가지). 그래서 이 표의 「카메라」 칸은 **그 사람의 그룹에
  속한 카메라 전체**이고, 같은 그룹의 두 사람은 카메라 칸이 같다 — 다른 것처럼
  보이면 그것이 거짓말이다(D-280). 「기능」 칸은 사람마다 다르다(역할이 다르면
  위젯 매트릭스가 다른 값을 낸다).

★ 문지기 — `access_log_service.py` 와 **같은 좁은 문**을 그대로 부른다
  (`apps.dsm.audit.access_log_denial`). 이 표는 「누가 무엇에 접근 가능한가」를
  통째로 보여주므로 접속기록과 같은 무게로 좁힌다 — **새 문지기를 만들지 않는다**
  (판정식은 `apps.dsm.audit` 한 곳).

★ **ORM은 여기 있다** — `handover_service.py`·`situation_meeting_service.py` 와
  같은 무게의 파일이다(`AppStaysThinTest` 는 `apps/dsm/services.py`·`api.py` 두
  파일만 본다, `tests/test_dsm_app.py::AppStaysThinTest.test_the_app_does_not_
  touch_django_models` 실측). `core.user.models.CoreUser` 를 직접 읽는 것도
  `operation_settings/services/menu_integration_service.py` 가 이미 쓰는 관용구다
  (dj-core 는 **읽기·호출만** — §0.4).
"""
from __future__ import annotations

from typing import Any

from apps.dsm import audit
from common import audit_writer
from common.tenant_filters import filter_users_by_group
from common.tenant_scope import TenantScope
from kernels.k3_dashboard import SETTING_WIDGETS, get_preset, widget_permission

LOGGER_NAME = "guardianx.u5.access_permission_read"
TAG = "[U5-ACCESS-PERM]"

#: 사람 상한 — `apps/dsm/stats.py` 의 상한과 같은 발상(무제한 스캔 금지).
_PERSON_CAP = 500


class AccessPermissionDenied(Exception):
    """이 계정은 권한 매트릭스를 볼 수 없다 — 사람의 말로 담는다."""


def _role_bucket(codes: tuple[str, ...]) -> str:
    """K3 표 그대로 매핑한다 — 판정식을 새로 쓰지 않는다(`config.k3_roles` 한 곳).

    ★ `api_u24.py::_audit_reader_denial` 과 같은 버킷을 쓰되, 여기는 「읽어도
      되는가」가 아니라 「어느 버킷인가」를 답한다 — 다른 질문이라 함수를 공유하지
      않는다(공유하면 반환형이 `str | None` 과 `str` 로 갈려 호출부가 매번 갈래를
      가려야 한다).
    """
    from config.k3_roles import (K3_ROLE_EXECUTIVES, K3_ROLE_MANAGERS,
                                 K3_ROLE_OPERATORS, K3_ROLE_SYSOPS)

    codeset = set(codes)
    if codeset & set(K3_ROLE_SYSOPS):
        return "sysop"
    if codeset & set(K3_ROLE_MANAGERS):
        return "manager"
    if codeset & set(K3_ROLE_EXECUTIVES):
        return "executive"
    if codeset & set(K3_ROLE_OPERATORS):
        return "operator"
    return "unmapped"


def _cameras_for_group(*, scope: TenantScope, group) -> list[dict[str, Any]]:
    """그 그룹(테넌트)의 카메라 전체 — **그룹 단위가 곧 접근 단위다**(머리말 참조).

    `pulse_rows` 를 그대로 부른다 — 맥박(`alive`)은 이 표의 관심사가 아니므로
    id·name 만 옮긴다. 판정을 다시 하지 않는다(D-212).
    """
    from stream_monitors.services.camera_pulse import pulse_rows

    rows = pulse_rows(scope=scope, group=group)
    return [{"camera_id": row.id, "name": row.name} for row in rows]


def _widgets_for(person_scope: TenantScope) -> dict[str, str]:
    return {w: widget_permission(w, scope=person_scope).value for w in SETTING_WIDGETS}


def person_permissions(*, scope: TenantScope, limit: int = 200) -> dict[str, Any]:
    """DSM-U5-02 앞 갈래 — 사람별 카메라·기능 권한.

    Raises:
        AccessPermissionDenied: 시스템관리자·테넌트관리자·전역관리자가 아니다
            (`access_log_service.py` 와 같은 문).
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    from core.user.models import CoreUser

    actor = scope.require_actor()
    denial = audit.access_log_denial(actor)
    if denial:
        raise AccessPermissionDenied(denial)

    limit = max(0, min(limit, _PERSON_CAP))
    people = list(
        filter_users_by_group(CoreUser.objects.all(), actor)
        .select_related("userprofilelink__group")
        .order_by("id")[: limit + 1])
    capped = len(people) > limit
    people = people[:limit]

    #: 그룹은 사람마다 잘 안 바뀐다 — 같은 그룹을 두 번 세지 않는다(질의 재사용).
    camera_cache: dict[int, list[dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    for person in people:
        person_scope = TenantScope.of(person)
        preset = get_preset(scope=person_scope)
        profile = getattr(person, "userprofilelink", None)
        group = getattr(profile, "group", None) if profile else None

        cameras: list[dict[str, Any]] = []
        if group is not None:
            if group.id not in camera_cache:
                camera_cache[group.id] = _cameras_for_group(scope=scope, group=group)
            cameras = camera_cache[group.id]

        rows.append({
            "person_id": person.id,
            "username": getattr(person, "username", "") or "",
            "group_id": group.id if group is not None else None,
            "group_name": getattr(group, "name", "") if group is not None else "",
            "role_codes": list(preset.role_codes),
            "role_bucket": _role_bucket(preset.role_codes),
            "preset": preset.preset,
            "cameras": cameras,
            "camera_count": len(cameras),
            "features": _widgets_for(person_scope),
        })

    audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action="access_permission:read", outcome=audit_writer.ALLOWED,
        reason=f"권한 매트릭스 조회 — {len(rows)}명", api_method="GET",
    )
    return {"items": rows, "total": len(rows), "capped": capped,
            "widgets": list(SETTING_WIDGETS)}
