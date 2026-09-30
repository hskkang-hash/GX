# -*- coding: utf-8 -*-
"""FWS-F2-07 · FWS-F1-10 안전경보 문턱 = **기관(테넌트) 설정값** (턴 AQ · 차선 N4 · P-434).

세종 판정 원문(P-434): 「명세에 없는 숫자는 기본값이 아니라 기관 설정이다 — 미설정은
「대기」로 보인다」.

무엇을 담나
-----------
풍향 급변 각(도) · 풍향 급변 시간창(분) · 투하구역 이탈 반경(m) 셋. 명세(§5.1 F1-10 ·
F2-07)는 말만 있고 숫자가 없다 — 그래서 이 파일은 **기본값·권장값을 하나도 갖지
않는다**(D-284). 기관이 저장하기 전까지 값은 `None` 이고, 규칙(`alerts.py`)은 판정하지
않은 채 「대기」를 낸다.

어디에 저장하나 — 새 표를 짓지 않는다
---------------------------------------
`admin_settings.py`(U5-02·U5-03)와 같은 저장처 — 감사 한 줄(`logger.AuditLogs`) +
테넌트 곁표(`apps/fws/audit_scope.py` · `common.models.AuditScope`). 이 테넌트 곁표로
좁힌 **최신 한 줄이 「지금 값」**이다. 그 한 줄이 곧 감사 줄이다(누가 · 언제 · 전 → 후
— `before`·`after` 두 칸에 세 값 전부를 싣는다).

범위 검증 — 물리적으로 말이 되는 범위만
----------------------------------------
    각     0 < x ≤ 180   (두 방위각의 최단 차는 180 을 넘을 수 없다)
    시간창 x > 0
    반경   x > 0
빈 값(None)은 「미설정으로 되돌림」이다 — 기관이 값을 거둘 수 있어야 한다.
"""
from __future__ import annotations

import math

from django.apps import apps
from django.utils import timezone

from common.evidence_chain import strip_chain

from apps.fws import audit_scope as fws_audit_scope
from apps.fws.admin_settings import (AdminInputRejected, AdminPermissionDenied,
                                     require_admin)

LOGGER_NAME = "guardianx.fws.admin_u5"
TAG = "[FWS-U5]"
ACTION_SAVE = "admin.safety_thresholds"

WIND_SHIFT_ANGLE = "wind_shift_angle_deg"
WIND_SHIFT_WINDOW = "wind_shift_window_minutes"
DROP_ZONE_EXIT_RADIUS = "drop_zone_exit_radius_m"
NAMES: tuple[str, ...] = (WIND_SHIFT_ANGLE, WIND_SHIFT_WINDOW, DROP_ZONE_EXIT_RADIUS)

#: 칸 이름 → (단위, 하한 초과, 상한 이하 or None). 권장값이 아니라 **물리적 범위**다.
RANGES: dict[str, tuple[str, float, float | None]] = {
    WIND_SHIFT_ANGLE: ("도", 0.0, 180.0),
    WIND_SHIFT_WINDOW: ("분", 0.0, None),
    DROP_ZONE_EXIT_RADIUS: ("m", 0.0, None),
}

STATUS_WAITING = "대기"
STATUS_SET = "설정됨"


class NoTenant(AdminInputRejected):
    """소속 기관이 없는 계정 — 기관 설정을 앉힐 자리가 없다(422)."""


def _model():
    return apps.get_model("logger", "AuditLogs")


def _empty() -> dict:
    return {name: None for name in NAMES}


def _latest_payload(scope) -> dict | None:
    ids = fws_audit_scope.tenant_audit_ids(scope=scope, kind=ACTION_SAVE)
    if not ids:
        return None
    row = (_model()._base_manager
           .filter(logger_name=LOGGER_NAME, api_name=ACTION_SAVE, id__in=ids)
           .order_by("-id").first())
    if row is None or not isinstance(row.data_after, dict):
        return None
    return strip_chain(row.data_after)


def tenant_values(scope) -> dict:
    """이 기관의 세 값(없으면 None). 규칙(`alerts.py`)이 부르는 자리 — 권한 검사 없이
    **요청자 테넌트로만** 좁힌다(현장 대원의 판독도 자기 기관 값으로 판정된다)."""
    payload = _latest_payload(scope) or {}
    out = _empty()
    for name in NAMES:
        value = payload.get(name)
        out[name] = None if value is None else float(value)
    return out


def _view(values: dict, payload: dict | None) -> dict:
    fields = []
    for name in NAMES:
        unit, low, high = RANGES[name]
        value = values.get(name)
        fields.append({
            "name": name, "value": value, "unit": unit,
            "min_exclusive": low, "max_inclusive": high,
            "status": STATUS_WAITING if value is None else STATUS_SET,
        })
    return {
        "fields": fields,
        "all_set": all(values.get(n) is not None for n in NAMES),
        "saved_at": (payload or {}).get("saved_at"),
        "saved_by": (payload or {}).get("saved_by"),
    }


def read_thresholds(*, scope) -> dict:
    """GET — 이 기관 사용자면 누구나 읽는다(값이 없으면 칸마다 「대기」)."""
    scope.require_actor()
    payload = _latest_payload(scope)
    return _view(tenant_values(scope), payload)


def _validate(name: str, raw) -> float | None:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise AdminInputRejected(f"{name} 는 숫자여야 한다") from exc
    if not math.isfinite(value):
        raise AdminInputRejected(f"{name} 는 유한한 숫자여야 한다")
    unit, low, high = RANGES[name]
    if value <= low:
        raise AdminInputRejected(f"{name} 는 {low:g}{unit}보다 커야 한다")
    if high is not None and value > high:
        raise AdminInputRejected(f"{name} 는 {high:g}{unit} 이하여야 한다")
    return value


def save_thresholds(*, scope, wind_shift_angle_deg=None, wind_shift_window_minutes=None,
                    drop_zone_exit_radius_m=None) -> dict:
    """POST — U5(기관 관리자)만. 세 값 전부를 한 벌로 저장한다(빈 칸 = 미설정)."""
    require_admin(scope)
    actor = scope.require_actor()
    from common.tenant_filters import get_user_group

    if getattr(get_user_group(actor), "pk", None) is None:
        raise NoTenant("소속 기관이 없는 계정은 기관 문턱을 저장할 수 없다")
    after = {
        WIND_SHIFT_ANGLE: _validate(WIND_SHIFT_ANGLE, wind_shift_angle_deg),
        WIND_SHIFT_WINDOW: _validate(WIND_SHIFT_WINDOW, wind_shift_window_minutes),
        DROP_ZONE_EXIT_RADIUS: _validate(DROP_ZONE_EXIT_RADIUS, drop_zone_exit_radius_m),
    }
    before = tenant_values(scope)
    payload = {**after, "before": before, "saved_at": timezone.now().isoformat(),
               "saved_by": getattr(actor, "pk", None)}
    changes = ", ".join(f"{n}: {before[n]} → {after[n]}" for n in NAMES)
    fws_audit_scope.record(
        scope=scope, logger_name=LOGGER_NAME, tag=TAG, action=ACTION_SAVE,
        payload=payload, reason=f"안전경보 문턱 저장 ({changes})", kind=ACTION_SAVE)
    return read_thresholds(scope=scope)


__all__ = [
    "ACTION_SAVE", "NAMES", "RANGES", "STATUS_WAITING", "STATUS_SET",
    "WIND_SHIFT_ANGLE", "WIND_SHIFT_WINDOW", "DROP_ZONE_EXIT_RADIUS",
    "AdminInputRejected", "AdminPermissionDenied", "NoTenant",
    "tenant_values", "read_thresholds", "save_thresholds",
]
