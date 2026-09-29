# -*- coding: utf-8 -*-
"""FWS-F1-10 — 안전 알림 수신(풍향 급변·대피 지시·철수) — 도달·확인 (턴 AK 차선 N2).

K2 를 그대로 쓴다
------------------
「나에게 무엇이 왔는가」는 이미 K2 의 발송 대장(`list_deliveries`)이 갖고 있는 사실이다
— 채널·수신자·성공 여부·시각까지. 이 파일이 새로 하는 일은 **「내 것만」**으로
좁히는 것과, **확인(ack)** 이라는 사람의 행위를 감사 한 줄로 남기는 것 둘뿐이다.
발송(K2 send)은 관제 쪽 화면의 일이라 이 절의 범위가 아니다 — 여기서 만드는 것은
「받는 사람이 받았다고 누르는 것」이다.
"""
from __future__ import annotations

import math

from django.apps import apps
from django.utils import timezone

from common import audit_writer
from kernels.k2_notify import NoRecipients
from kernels.k2_notify.services import list_deliveries

#: ★ F-05 잠금 — K1 을 직접 부르지 않는다. `apps.dsm.services` 가 유일한 문이다.
from apps.dsm import services as dsm_services

LOGGER_NAME = "guardianx.fws.alert_ack"
TAG = "[FWS-ALERT]"
ACTION_ACK = "alert.ack"


class AlertNotFound(Exception):
    """그런 알림이 없다 — 404. 남의 알림일 때도 이것이다(존재 여부도 새면 누출)."""


class AlertInputRejected(Exception):
    """값이 계약 밖이다 — 422."""


def my_alerts(*, scope, limit: int = 50) -> list[dict]:
    """FWS-F1-10 「도달」 — 나에게 실제로 간(성공한) 발송만."""
    actor = scope.require_actor()
    deliveries = list_deliveries(
        scope=scope, recipient_id=actor.pk, succeeded=True, limit=limit)
    acked = _acked_ids(actor.pk)
    return [
        {
            "delivery_id": d.delivery_id,
            "event_id": d.event_id,
            "channel": d.channel,
            "occurred_at": d.occurred_at.isoformat() if d.occurred_at else None,
            "sent_at": d.sent_at.isoformat() if d.sent_at else None,
            "acknowledged": d.delivery_id in acked,
        }
        for d in deliveries
    ]


def _model():
    return apps.get_model("logger", "AuditLogs")


def _acked_ids(user_id: int) -> set[int]:
    rows = (
        _model()._base_manager
        .filter(logger_name=LOGGER_NAME, user_id=user_id, api_name=ACTION_ACK)
        .order_by("-id")[:2000]
    )
    out: set[int] = set()
    for row in rows:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        delivery_id = payload.get("delivery_id")
        if isinstance(delivery_id, int):
            out.add(delivery_id)
    return out


def ack_alert(*, scope, delivery_id: int) -> dict:
    """FWS-F1-10 「확인」 — 이 사람이 이 알림을 봤다고 남긴다.

    ★ 남의 배달 번호로 확인을 남길 수 없다 — `my_alerts` 로 자기 목록에 있는 것만
      먼저 확인하고 그 번호로 부른다(문지기는 부르는 쪽이 목록을 좁혀 준 것에 기댄다
      — `field_reply.list_field_replies` 와 같은 얕은 좁히기이지만, 발송 이력은
      이미 `list_deliveries` 가 테넌트로 좁혀 두어서 남의 테넌트 배달 번호는애초에
      이 사람 목록에 없다).
    """
    actor = scope.require_actor()
    own = {d["delivery_id"] for d in my_alerts(scope=scope, limit=2000)}
    if delivery_id not in own:
        raise AlertNotFound(f"delivery_id={delivery_id} 가 없다")
    audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=ACTION_ACK,
        outcome=audit_writer.ALLOWED, reason=f"알림 {delivery_id} 확인",
        after={"delivery_id": delivery_id}, api_name=ACTION_ACK, api_method="POST")
    return {"delivery_id": delivery_id, "acknowledged": True}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F2-07 · FWS-F1-10 — 풍향 급변 · 헬기 투하 구역 이탈 경보 규칙
# (턴 AP · WO-19 · 차선 N2 · P-421 ②)
#
# 턴 AO 소급(`N1_promotions_ao.md` §2-2)이 잡은 결손: 두 절 다 배달·확인(ack)은
# 이미 닫혀 있었지만(위 `my_alerts`/`ack_alert`), 「풍향 급변」·「헬기 투하 구역
# 이탈」을 **판정해 실제로 경보를 쏘는 규칙**이 `kernels/k2_notify` 어디에도
# 없었다(grep 결과 0건). 이 절이 그 규칙 하나를 세운다 — 경보 발송은 새 채널을
# 열지 않고 F1-10·F2-07 이 이미 연 문(`dsm_services.notify_event` → K2 send →
# GET /api/fws/alerts 도달·POST .../ack 확인)을 그대로 탄다(D-212).
#
# ★ 규정값 — 명세 원문(FWS_산불감시App_명세서_v1.0 §5.1 표 FWS-F1-10 「안전 알림
#   수신(풍향 급변·대피 지시·철수)」·FWS-F2-07 「안전 경보 수신(풍향 급변·헬기
#   투하 구역 이탈)」)은 **말만** 두고 각도·시간창·반경 숫자를 주지 않는다(명세·
#   조사 메모·미포함표 grep 무일치). 그래서 **값을 짓지 않고 이름만 세운다**
#   (턴 AP 지시 「모르는 값은 짓지 않고 이름만」 · D-284). 값은 규정값 모듈
#   `apps.fws.constants` 에 산다(P-386 「규정값은 그 모듈 하나」) — 그 파일은 공용
#   (조율자 소유)이라 이 차선이 고치지 않고 아래 세 이름을 **그 모듈에서 읽는다**.
#   이름이 없거나 값이 `None` 이면 판정하지 않는다(`judged=False` ·
#   `threshold_unset=True` 를 응답에 그대로 낸다 — 「안 쐈다」와 「못 쟀다」를
#   같은 모양으로 내지 않는다 · D-290).
WIND_SHIFT_ANGLE_NAME = "WIND_SHIFT_ANGLE_DEG"
WIND_SHIFT_WINDOW_NAME = "WIND_SHIFT_WINDOW_MINUTES"
DROP_ZONE_EXIT_RADIUS_NAME = "DROP_ZONE_EXIT_RADIUS_M"


def _threshold(name: str):
    """규정값 모듈에서 문턱 하나를 **부를 때마다** 읽는다(모듈 적재 때 굳히지
    않는다 — 세종 결정으로 값이 들어오는 날 이 파일은 안 바뀐다)."""
    from apps.fws import constants as fws_constants

    value = getattr(fws_constants, name, None)
    return None if value is None else float(value)


_SAFETY_LOGGER = "guardianx.fws.safety_alert"
_SAFETY_TAG = "[FWS-SAFETY]"
ACTION_WIND_READING = "safety.wind_reading"
ACTION_DROP_ZONE_POSITION = "safety.drop_zone_position"
ACTION_SAFETY_ALERT_FIRED = "safety.alert_fired"

KIND_WIND_SHIFT = "wind_shift"
KIND_DROP_ZONE_EXIT = "drop_zone_exit"


def _safety_rows_for_event(action: str, event_id: int):
    qs = (_model()._base_manager
          .filter(logger_name=_SAFETY_LOGGER, api_name=action).order_by("id"))
    out = []
    for row in qs:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        if payload.get("event_id") == event_id:
            out.append(payload)
    return out


def _latest_wind_reading(event_id: int) -> dict | None:
    items = _safety_rows_for_event(ACTION_WIND_READING, event_id)
    return items[-1] if items else None


def _angle_diff(a: float, b: float) -> float:
    """두 방위각(0~360, 도) 사이 최단 각도차(0~180)."""
    d = abs(a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d


def _fire_safety_alert(*, scope, event_id: int, actor, kind: str, reason: str,
                       detail: dict) -> int:
    """판정이 문턱을 넘었을 때 **기존 안전경보 경로**(F1-10/F2-07 문)로 실제로
    쏜다 — `dsm_services.notify_event` → K2 `send()`. 새 채널을 열지 않는다."""
    try:
        records = dsm_services.notify_event(scope=scope, event_id=event_id)
    except NoRecipients:
        records = ()
    payload = {"event_id": event_id, "kind": kind, "delivered": len(records),
              **detail, "fired_at": timezone.now().isoformat()}
    audit_writer.write(
        logger_name=_SAFETY_LOGGER, tag=_SAFETY_TAG, actor=actor,
        action=ACTION_SAFETY_ALERT_FIRED, outcome=audit_writer.ALLOWED,
        reason=reason, after=payload, api_name=ACTION_SAFETY_ALERT_FIRED,
        api_method="POST")
    return len(records)


def report_wind_direction(*, scope, event_id: int, direction_deg: float) -> dict:
    """FWS-F2-07 · F1-10 판정 규칙 ① — **풍향 급변**.

    직전 판독(규정값 `WIND_SHIFT_WINDOW_MINUTES` 이내)과 견줘 `WIND_SHIFT_ANGLE_DEG`
    를 **초과**(`>`, `>=` 아니다 — 문턱값 자체는 아직 급변이 아니다)하면 경보를
    쏜다. 직전 판독이 없거나 창 밖이면 판정하지 않는다(판독 하나로는 「변화」를
    말할 수 없다)."""
    if not (0.0 <= direction_deg < 360.0):
        raise AlertInputRejected(
            f"direction_deg={direction_deg!r} 는 0~360 방위각이 아니다")
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트(테넌트)
    actor = scope.require_actor()
    now = timezone.now()

    angle = _threshold(WIND_SHIFT_ANGLE_NAME)
    window = _threshold(WIND_SHIFT_WINDOW_NAME)
    threshold_unset = angle is None or window is None
    prior = _latest_wind_reading(event_id)
    diff_deg = None
    within_window = False
    alert_fired = False
    if prior is not None and not threshold_unset:
        from django.utils.dateparse import parse_datetime

        prior_at = parse_datetime(prior.get("at") or "")
        if prior_at is not None:
            elapsed_min = (now - prior_at).total_seconds() / 60.0
            within_window = 0 <= elapsed_min <= window
        if within_window:
            diff_deg = _angle_diff(direction_deg, float(prior["direction_deg"]))
            alert_fired = diff_deg > angle

    audit_writer.write(
        logger_name=_SAFETY_LOGGER, tag=_SAFETY_TAG, actor=actor,
        action=ACTION_WIND_READING, outcome=audit_writer.ALLOWED,
        reason=f"풍향 판독 {direction_deg}도", api_name=ACTION_WIND_READING,
        api_method="POST",
        after={"event_id": event_id, "direction_deg": direction_deg,
              "at": now.isoformat()})

    delivered = 0
    alert_reason = None
    if alert_fired:
        alert_reason = (f"풍향 급변 — {diff_deg:.1f}도 변화"
                        f"({window:g}분 이내, 문턱 {angle:g}도 초과)")
        delivered = _fire_safety_alert(
            scope=scope, event_id=event_id, actor=actor, kind=KIND_WIND_SHIFT,
            reason=alert_reason,
            detail={"diff_deg": diff_deg, "threshold_deg": angle,
                    "window_minutes": window})
    return {
        "event_id": event_id, "direction_deg": direction_deg,
        "diff_deg": diff_deg, "within_window": within_window,
        "threshold_deg": angle, "window_minutes": window,
        "threshold_unset": threshold_unset,
        "judged": (not threshold_unset) and within_window,
        "alert_fired": alert_fired,
        "alert_reason": alert_reason, "delivered_count": delivered,
    }


def _drop_zone_center(event_id: int) -> dict | None:
    """F4-04 승인 좌표(`command.py::ACTION_HELI_APPROVE`)를 중심으로 재사용한다
    — 새 표를 만들지 않는다(D-212). 승인이 없으면 판정할 중심이 없다."""
    from apps.fws import command as fws_command

    items = fws_command._items_for_event(fws_command.ACTION_HELI_APPROVE, event_id)
    if not items:
        return None
    return items[-1].get("drop_zone")


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2)
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def report_drop_zone_position(*, scope, event_id: int, lat: float, lng: float) -> dict:
    """FWS-F2-07 · F1-10 판정 규칙 ② — **헬기 투하 구역 이탈**.

    F4-04 승인 좌표를 중심으로 규정값 `DROP_ZONE_EXIT_RADIUS_M` 을 **초과**하면 경보를
    쏜다. 이 사건에 등록된 승인이 없으면 판정할 중심이 없다 — 422."""
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트(테넌트)
    center = _drop_zone_center(event_id)
    if center is None:
        raise AlertInputRejected(
            "이 사건에 등록된 헬기 투하 구역(F4-04 승인)이 없다 — 판정할 중심이 없다")
    distance_m = _haversine_m(center["lat"], center["lng"], lat, lng)
    radius = _threshold(DROP_ZONE_EXIT_RADIUS_NAME)
    threshold_unset = radius is None
    alert_fired = (not threshold_unset) and distance_m > radius
    actor = scope.require_actor()
    now = timezone.now()

    audit_writer.write(
        logger_name=_SAFETY_LOGGER, tag=_SAFETY_TAG, actor=actor,
        action=ACTION_DROP_ZONE_POSITION, outcome=audit_writer.ALLOWED,
        reason=f"투하 위치 판독 · 중심 거리 {distance_m:.0f}m",
        api_name=ACTION_DROP_ZONE_POSITION, api_method="POST",
        after={"event_id": event_id, "lat": lat, "lng": lng,
              "distance_m": round(distance_m, 1), "at": now.isoformat()})

    delivered = 0
    alert_reason = None
    if alert_fired:
        alert_reason = (f"헬기 투하 구역 이탈 — {distance_m:.0f}m(문턱 "
                        f"{radius:.0f}m 초과)")
        delivered = _fire_safety_alert(
            scope=scope, event_id=event_id, actor=actor,
            kind=KIND_DROP_ZONE_EXIT, reason=alert_reason,
            detail={"distance_m": round(distance_m, 1),
                    "radius_m": radius})
    return {
        "event_id": event_id, "distance_m": round(distance_m, 1),
        "radius_m": radius, "threshold_unset": threshold_unset,
        "judged": not threshold_unset, "alert_fired": alert_fired,
        "alert_reason": alert_reason, "delivered_count": delivered,
    }
