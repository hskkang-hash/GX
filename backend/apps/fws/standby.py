# -*- coding: utf-8 -*-
"""FWS-F2-01 — 대기 상태 등록(주간·야간 5분대기조·위치) (턴 AL 차선 N2).

`apps/fws/patrol.py` 와 같은 판단 — 감사 한 줄이 정본
--------------------------------------------------------
「지금 대기 중인가·주간인가 야간인가·어디 있는가」는 **일어난 일 한 줄**이고
(patrol.py 머리말과 같은 뜻), 새 표 + 마이그레이션을 세우지 않는다. 「지금 상태」는
**최신 줄이 답한다**(`notify_prefs.py`·`drill.py` 와 같은 형).

「자원 배치판에 표시」(완결조건)
--------------------------------
턴 AQ 차선 W2C — 저장 줄에 테넌트 곁표를 붙이고(`audit_scope.record`), 배치판
읽기는 `resource_board.py`(GET /api/fws/resources/board)가 한다. 화면은 지휘
화면(`CommandHome.tsx` 자원 배치판 카드).
"""
from __future__ import annotations

from django.apps import apps
from django.utils import timezone

from apps.fws import audit_scope as fws_audit_scope

LOGGER_NAME = "guardianx.fws.standby"
TAG = "[FWS-STANDBY]"
ACTION_SAVE = "standby.save"

#: 대기 상태 3택 — 명세서 §5.2 FWS-F2-01(주간·야간 5분대기조 · 근무 외).
STATUS_STANDBY_DAY = "standby_day"
STATUS_STANDBY_NIGHT = "standby_night"
STATUS_OFF_DUTY = "off_duty"
STATUSES = (STATUS_STANDBY_DAY, STATUS_STANDBY_NIGHT, STATUS_OFF_DUTY)


class StandbyStatusRejected(Exception):
    """값이 계약 밖이다 — 422."""


def _model():
    return apps.get_model("logger", "AuditLogs")


def _latest_row(user_id: int):
    return (
        _model()._base_manager
        .filter(logger_name=LOGGER_NAME, user_id=user_id, api_name=ACTION_SAVE)
        .order_by("-id")
        .first()
    )


def set_status(*, scope, status: str, lat: float | None = None,
              lng: float | None = None) -> dict:
    """FWS-F2-01 — 대기 상태 등록. 위치는 좌표 값만 싣는다(§0.4 인접 — 지도 렌더는
    이 문의 몫이 아니다)."""
    if status not in STATUSES:
        raise StandbyStatusRejected(
            f"status={status!r} 는 대기 상태가 아니다. 허용: {STATUSES}")
    actor = scope.require_actor()
    now = timezone.now()
    location = {"lat": lat, "lng": lng} if (lat is not None and lng is not None) else None
    payload = {"status": status, "lat": lat, "lng": lng, "set_at": now.isoformat()}
    # 턴 AQ 차선 W2C — 테넌트 곁표(`audit_scope.record`)로 남긴다: 지휘 화면의 자원
    # 배치판(`resource_board.py`)이 「이 기관의 대기 인원」을 묻는 자리다.
    fws_audit_scope.record(
        scope=scope, logger_name=LOGGER_NAME, tag=TAG, action=ACTION_SAVE,
        payload=payload, kind=ACTION_SAVE,
        reason=f"대기 상태 {status}" + (f" · 위치 {lat},{lng}" if location else ""))
    return {"status": status, "location": location, "set_at": now.isoformat()}


def my_status(*, scope) -> dict:
    """지금 내 대기 상태 — 아직 등록한 적 없으면 정직하게 `None`(D-284)."""
    actor = scope.require_actor()
    row = _latest_row(actor.pk)
    if row is None:
        return {"status": None, "location": None, "set_at": None}
    payload = row.data_after if isinstance(row.data_after, dict) else {}
    lat, lng = payload.get("lat"), payload.get("lng")
    location = {"lat": lat, "lng": lng} if (lat is not None and lng is not None) else None
    return {"status": payload.get("status"), "location": location,
           "set_at": payload.get("set_at")}
