# -*- coding: utf-8 -*-
"""FWS-F2-01 「자원 배치판에 표시」 · FWS-F2-05 「지휘 화면 배지」 — 읽기 한 자리
(턴 AQ · 2물결 차선 W2C).

새 표 0 — 두 절이 이미 남기는 감사 줄을 **읽기만** 한다.

* 대기 인원(F2-01) — `standby.set_status` 가 테넌트 곁표(`audit_scope`)를 붙여 남긴
  줄 중 **사람마다 최신 한 줄**. 곁표가 없는(이 턴 전에 쓴) 줄은 어느 기관 것인지
  모르므로 세지 않는다(넓히지 않고 좁힌다 — `audit_scope.tenant_audit_ids` 와 같은
  판단).
* 지원 요청 배지(F2-05) — `missions.request_support` 가 남긴 줄을 사건 번호로
  좁힌다. 사건 문지기는 `dsm_services.event_detail`(남의 테넌트 사건은 404).
  `missions.py` 는 다른 차선 소유라 **상수만 읽는다**.
"""
from __future__ import annotations

from django.apps import apps
from django.contrib.auth import get_user_model

from apps.dsm import services as dsm_services
from apps.fws import audit_scope as fws_audit_scope
from apps.fws import missions, standby

#: 한 번에 훑는 지원 요청 줄의 상한 — 화면 배지용 셈(감사표 전건을 끌지 않는다).
_SUPPORT_SCAN_LIMIT = 2000


def _model():
    return apps.get_model("logger", "AuditLogs")


def _row_time(row) -> str | None:
    """감사 행이 찍힌 시각(dj-core 칸 `create_datetime`) — 없으면 None."""
    at = getattr(row, "create_datetime", None)
    return at.isoformat() if at is not None else None


def standby_roster(*, scope) -> dict:
    """이 기관의 대기 인원 — 사람마다 최신 상태 한 줄 + 상태별 수."""
    ids = fws_audit_scope.tenant_audit_ids(scope=scope, kind=standby.ACTION_SAVE)
    rows = (_model()._base_manager
            .filter(logger_name=standby.LOGGER_NAME, api_name=standby.ACTION_SAVE,
                    id__in=ids)
            .order_by("-id")) if ids else []
    latest: dict[int, dict] = {}
    standby_row_id: dict[int, int] = {}
    for row in rows:
        if row.user_id in latest:
            continue
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        lat, lng = payload.get("lat"), payload.get("lng")
        standby_row_id[row.user_id] = row.id
        latest[row.user_id] = {
            "user_id": row.user_id,
            "status": payload.get("status"),
            "location": ({"lat": lat, "lng": lng}
                         if lat is not None and lng is not None else None),
            "set_at": payload.get("set_at"),
        }
    users = {u.pk: u for u in get_user_model()._base_manager.filter(pk__in=list(latest))}
    mission_state = _mission_state(list(latest), standby_row_id)
    people = []
    for uid, item in latest.items():
        user = users.get(uid)
        name = ""
        if user is not None:
            name = (user.get_full_name() or "").strip() or user.username
        ms = mission_state.get(uid, {})
        people.append({**item, "name": name,
                       "mission_state": ms.get("state"),
                       "mission_event_id": ms.get("event_id"),
                       "released_at": ms.get("released_at")})
    counts = {s: sum(1 for p in people if p["status"] == s) for s in standby.STATUSES}
    deployed = sum(1 for p in people if p["mission_state"] == MISSION_DEPLOYED)
    released = sum(1 for p in people if p["mission_state"] == MISSION_RELEASED)
    #: ★ 출동 중인 사람은 「대기 인원」에서 빠진다 — 철수·복귀(F2-11)를 회신하면
    #:   그 사람의 최신 임무 줄이 `released` 가 되어 다시 대기 인원에 든다(배치판 해제).
    on_standby = sum(
        1 for p in people
        if p["status"] in (standby.STATUS_STANDBY_DAY, standby.STATUS_STANDBY_NIGHT)
        and p["mission_state"] != MISSION_DEPLOYED)
    return {"people": people, "counts": counts, "on_standby": on_standby,
           "deployed": deployed, "released": released}


#: F2-11 「자원 배치판 해제」 — 사람의 **최신 임무 줄**이 출동이면 배치 중, 철수면 해제.
MISSION_DEPLOYED = "deployed"
MISSION_RELEASED = "released"


def _mission_state(user_ids: list[int], standby_row_id: dict[int, int]) -> dict[int, dict]:
    """사람마다 대기 상태를 **저장한 뒤**의 최신 임무 줄(출동 · 철수).

    `missions.py` 는 손대지 않고 **상수와 감사 줄만 읽는다.** 대기 상태를 다시 저장한
    줄(id)이 더 나중이면 그 임무는 이미 지난 일이라 무시한다 — 사람이 스스로 배치판에
    새로 섰다는 뜻이다.
    """
    if not user_ids:
        return {}
    rows = (_model()._base_manager
            .filter(logger_name=missions.LOGGER_NAME, user_id__in=user_ids,
                    api_name__in=(missions.ACTION_DISPATCH, missions.ACTION_RELEASED))
            .order_by("-id")[:_SUPPORT_SCAN_LIMIT])
    out: dict[int, dict] = {}
    for row in rows:
        if row.user_id in out:
            continue
        if row.id < standby_row_id.get(row.user_id, 0):
            out[row.user_id] = {}
            continue
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        if row.api_name == missions.ACTION_RELEASED:
            out[row.user_id] = {"state": MISSION_RELEASED,
                                "event_id": payload.get("event_id"),
                                "released_at": payload.get("at") or _row_time(row)}
        else:
            out[row.user_id] = {"state": MISSION_DEPLOYED,
                                "event_id": payload.get("event_id"), "released_at": None}
    return out


def support_requests(*, scope, event_id: int) -> dict:
    """이 사건에 들어온 지원 요청 — 종류별 수(배지) + 최신순 목록."""
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트(테넌트)
    rows = (_model()._base_manager
            .filter(logger_name=missions.LOGGER_NAME, api_name=missions.ACTION_SUPPORT)
            .order_by("-id")[:_SUPPORT_SCAN_LIMIT])
    items = []
    for row in rows:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        if payload.get("event_id") != event_id:
            continue
        items.append({"kind": payload.get("kind"), "amount": payload.get("amount") or None,
                      "note": payload.get("note") or None,
                      "requested_at": _row_time(row)})
    badges = {k: sum(1 for i in items if i["kind"] == k) for k in missions.SUPPORT_KINDS}
    return {"event_id": event_id, "count": len(items), "badges": badges,
           "requests": items}


def board(*, scope, event_id: int | None = None) -> dict:
    """자원 배치판 — 대기 인원 + (사건을 주면) 그 사건의 지원 요청 배지."""
    out = {"standby": standby_roster(scope=scope), "support": None}
    if event_id is not None:
        out["support"] = support_requests(scope=scope, event_id=event_id)
    return out
