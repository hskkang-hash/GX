# -*- coding: utf-8 -*-
"""FWS-F5-01·F5-03 반쪽 채움 (턴 AP · WO-19 · 차선 N4 단독 소유).

`apps/fws/drone.py`(N2 소유 · 이 턴은 **읽기만**)가 이미 F5-01·02·03·08·10 을
「서류상」 닫았다고 적었지만(그 파일 머리말), P-419 눈금으로 다시 대조하니
둘이 반쪽이었다(`docs/agent/evidence/SPEC/FWS-F5-01.json`·`FWS-F5-03.json` 옛
title_parts):

    F5-01 — 「발화 추정 좌표」가 정찰 임무 응답에 안 실린다(사건 참조뿐 · 간접)
    F5-03 — 「사진·열화상」 둘을 구분하는 칸이 없다(`attachment_ref` 하나뿐)

이 파일은 **`drone.py` 를 고치지 않고** 그 위에 얇게 두 문을 더한다(P-357 —
판정 문을 새로 만들지 않는다, 이미 있는 값을 합치거나 곁에 남긴다뿐):

    recon_coords()      K1 이벤트의 lat/lng(`apps.dsm.services.event_detail`,
                         공용 공개 면) 과 드론의 반경 기록(`drone.recon_mine`,
                         읽기만)을 **합쳐서** 낸다 — 새 축이 아니라 합치는 줄.
    attach_thermal()     열화상 전용 참조 한 칸 — 사진(`attachment_ref`, F1-06/
                         F5-03 이 이미 쓴다)과 **다른 칸**에 남긴다. 판정(verdict)
                         은 여전히 `drone.confirm_result()` 가 한다 — 이 문은
                         판정에 관여하지 않는다.

★ 새 표를 만들지 않는다 — `cbs_draft_service.py`·`control_board_service.py` 와
  같은 판단(감사 한 줄 = 증빙 한 걸음). `audit_writer` 를 직접 쓴다.
"""
from django.apps import apps as django_apps

from common import audit_writer
from common.tenant_scope import TenantScope

from apps.dsm import services as dsm_services
from apps.fws import drone

LOGGER_NAME = "guardianx.ap.n4.f5"
TAG = "[AP-N4-F5]"

#: 열화상 증빙 참조 상한 — 사진 참조(`attachment_ref`, `drone.py::confirm_result`)
#: 와 같은 자리표(값 하나, 형식 검증은 하지 않는다 — D-284, 지어내지 않는다).
MAX_THERMAL_REF_CHARS = 500


class ThermalAttachmentRejected(Exception):
    """열화상 참조가 비었다 — 422 로 번역된다."""


def _thermal_action(event_id: int) -> str:
    return f"f5_thermal:{event_id}"


def _audit_model():
    return django_apps.get_model("logger", "AuditLogs")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F5-01 반쪽 채움 — 발화 추정 좌표를 반경과 한 응답으로
# ═══════════════════════════════════════════════════════════════════════════
def recon_coords(*, scope: TenantScope, event_id: int) -> dict:
    """그 사건(정찰 임무가 겨눈 K1 이벤트)의 **발화 추정 좌표**(lat/lng, K1
    공개 면 재사용)와 **반경**(`drone.py::recon()` 이 이미 받는 radius_m)을
    한 응답으로 합친다.

    좌표 자체는 새로 만들지 않는다 — K1 이벤트가 이미 갖고 있다
    (`apps.dsm.services.event_detail`). 반경은 드론의 정찰 요청 기록에서 읽는다
    (`drone.recon_mine`, 읽기 전용 — 이 함수는 `drone.py` 의 어떤 것도 고치지
    않는다).

    Raises:
        django.http.Http404: 그런 사건이 없다 · 남의 테넌트 사건이다
            (`event_detail` 의 문지기 그대로 — 여기서 다시 만들지 않는다).
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    ev = dsm_services.event_detail(scope=scope, event_id=event_id)  # 문지기(404·격리)
    mine = drone.recon_mine(scope=scope)
    row = next((r for r in mine["requests"] if r.get("event_id") == event_id), None)
    return {
        "event_id": event_id,
        "lat": ev.lat, "lng": ev.lng,
        "radius_m": row["radius_m"] if row else None,
        "state": row["state"] if row else None,
        "requested_at": row["requested_at"] if row else None,
    }


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F5-03 반쪽 채움 — 열화상 전용 증빙 칸(사진 참조와 구분)
# ═══════════════════════════════════════════════════════════════════════════
def attach_thermal(*, scope: TenantScope, event_id: int, thermal_ref: str) -> dict:
    """`POST .../thermal-attachment` — 열화상 증빙 참조를 **사진과 다른 칸**에
    남긴다. 판정에는 관여하지 않는다 — 판정은 `drone.confirm_result()`
    (F1-06 재사용)가 그대로 한다(P-357, 두 번째 판정 문을 만들지 않는다).

    Raises:
        django.http.Http404: 그런 사건이 없다 · 남의 테넌트 사건이다.
        ThermalAttachmentRejected: `thermal_ref` 가 비었다 · 너무 길다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 문지기
    thermal_ref = (thermal_ref or "").strip()
    if not thermal_ref:
        raise ThermalAttachmentRejected("thermal_ref 가 비어 있습니다 — 열화상 "
                                        "참조 없이는 증빙이 되지 않습니다.")
    if len(thermal_ref) > MAX_THERMAL_REF_CHARS:
        raise ThermalAttachmentRejected(
            f"thermal_ref 가 {len(thermal_ref)}자다. 상한은 {MAX_THERMAL_REF_CHARS}자")

    actor = scope.require_actor()
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_thermal_action(event_id), outcome=audit_writer.ALLOWED,
        reason=f"열화상 증빙 참조={thermal_ref}",
        after={"event_id": event_id, "thermal_ref": thermal_ref},
        api_name=_thermal_action(event_id), api_method="POST")
    return {"event_id": event_id, "thermal_id": entry.audit_id,
           "thermal_ref": thermal_ref}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F5-10 반쪽 채움 — 「월 표」(완결 조건이 부르는 월별 표시)
# ═══════════════════════════════════════════════════════════════════════════
def flight_minutes_monthly_table(*, scope: TenantScope, limit: int = 500) -> dict:
    """그 조종사의 비행 기록(`drone.flights_mine`, 읽기만)을 월별로 접는다.
    새 질의를 짜지 않는다 — `drone.py::flight_minutes_total` 이 이미 하는 합산을
    달마다 반복해 부르지 않고, 값 목록 하나를 한 번에 받아 이 함수가 접는다.
    """
    data = drone.flights_mine(scope=scope, limit=limit)
    by_month: dict[str, dict] = {}
    for f in data["flights"]:
        logged_at = f.get("logged_at") or ""
        month = logged_at[:7] if len(logged_at) >= 7 else "미상"
        row = by_month.setdefault(
            month, {"month": month, "flight_minutes_total": 0.0, "flight_count": 0})
        minutes = f.get("flight_minutes")
        if isinstance(minutes, (int, float)):
            row["flight_minutes_total"] += minutes
        row["flight_count"] += 1
    rows = sorted(by_month.values(), key=lambda r: r["month"], reverse=True)
    for r in rows:
        r["flight_minutes_total"] = round(r["flight_minutes_total"], 1)
    return {"rows": rows, "count": len(rows)}


def thermal_attachments(*, scope: TenantScope, event_id: int) -> dict:
    """`GET .../thermal-attachment` — 그 사건에 남긴 열화상 증빙 전건(최신 먼저).

    Raises:
        django.http.Http404: 그런 사건이 없다 · 남의 테넌트 사건이다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 문지기
    rows = (
        _audit_model()._base_manager
        .filter(logger_name=LOGGER_NAME, api_name=_thermal_action(event_id))
        .order_by("-id")[:200]
    )
    out = []
    for r in rows:
        payload = r.data_after if isinstance(r.data_after, dict) else {}
        out.append({"thermal_id": r.pk, "thermal_ref": payload.get("thermal_ref")})
    return {"event_id": event_id, "attachments": out, "count": len(out)}
