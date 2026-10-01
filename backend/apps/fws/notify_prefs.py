# -*- coding: utf-8 -*-
"""FWS-F1-12 — 근무 외 알림 차단(방해 금지 시간대)·담당 초소 설정 (턴 AK 차선 N2).

`apps/dsm/notify_prefs.py` 와 같은 판단, 다른 표
--------------------------------------------------
그 파일의 머리말이 이미 적어 둔 판단(감사 한 줄이 정본 · 새 표를 세우지 않는다)을
그대로 따른다. 다만 그 파일의 `DsmNotifyPrefs` 모델은 **DSM 차선(N1)의 것**이라
같은 턴에 두 차선이 같은 표를 쓰면 그 표의 소유가 흐려진다 — 그래서 FWS 는
감사 로그를 직접 쓴다(이 파일이 만드는 것은 표가 아니라 **읽고 쓰는 문**뿐이다).

「지금 설정」은 **최신 줄이 답한다**(drill.py 와 같은 형 — 마지막 줄이 현재다).
"""
from __future__ import annotations

from django.apps import apps

from common import audit_writer

LOGGER_NAME = "guardianx.fws.notify_prefs"
TAG = "[FWS-PREFS]"
ACTION_SAVE = "notify_prefs.save"

MAX_POST_CODE_CHARS = 40


class NotifyPrefsRejected(Exception):
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


def _defaults() -> dict:
    return {"quiet_hours_start": "", "quiet_hours_end": "", "assigned_post_code": ""}


DUTY_ASSIGNED = "assigned"
DUTY_WAITING = "waiting"


def duty_post(*, scope) -> dict:
    """P-452 — 담당 초소 = **그날 편성표(근무표)의 배정.**

    저장한 `assigned_post_code` 는 본인이 적은 메모일 뿐 담당이 아니다. 담당은 기관이
    올린 근무표(`office.upload_roster`)에서 **오늘 날짜 + 내 이름**의 줄이 들고 있는
    `post_code` 다. 편성 줄이 없거나 초소 칸이 비면 차단하지 않고 `waiting`(「대기」
    배지)을 낸다 — 초소를 지어내지 않는다.
    """
    from apps.fws import office
    from django.utils import timezone

    actor = scope.require_actor()
    today = timezone.localtime(timezone.now()).date().isoformat()
    names = {n.strip().lower() for n in (
        getattr(actor, "username", "") or "",
        (actor.get_full_name() or "") if hasattr(actor, "get_full_name") else "")
        if n and n.strip()}
    rows = office.current_roster(scope=scope).get("rows", [])
    mine = [r for r in rows
            if (r.get("shift_date") or "").strip() == today
            and (r.get("name") or "").strip().lower() in names]
    for r in mine:
        code = (r.get("post_code") or "").strip()
        if code:
            return {"status": DUTY_ASSIGNED, "post_code": code, "shift_date": today,
                    "shift_type": r.get("shift_type") or "", "source": "roster"}
    return {"status": DUTY_WAITING, "post_code": None, "shift_date": today,
            "shift_type": (mine[0].get("shift_type") if mine else "") or "",
            "source": "roster"}


def get_prefs(*, scope) -> dict:
    """FWS-F1-12 읽기 — 아직 아무 것도 저장한 적 없으면 **빈 기본값**(회색이 아니라
    「아직 안 정했다」는 뜻 있는 값이다). `duty_post` 는 그날 편성표의 배정(P-452)."""
    actor = scope.require_actor()
    row = _latest_row(actor.pk)
    out = _defaults()
    if row is not None:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        out.update({k: payload.get(k, "") for k in out})
    out["duty_post"] = duty_post(scope=scope)
    return out


def _hhmm(value: str, field: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    parts = value.split(":")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise NotifyPrefsRejected(f"{field}={value!r} 는 HH:MM 이 아니다")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise NotifyPrefsRejected(f"{field}={value!r} 는 하루 안의 시각이 아니다")
    return f"{hour:02d}:{minute:02d}"


def save_prefs(*, scope, quiet_hours_start: str = "", quiet_hours_end: str = "",
              assigned_post_code: str = "") -> dict:
    """FWS-F1-12 쓰기 — 근무 외 시간대(방해 금지)와 담당 초소를 한 번에 저장한다."""
    actor = scope.require_actor()
    start = _hhmm(quiet_hours_start, "quiet_hours_start")
    end = _hhmm(quiet_hours_end, "quiet_hours_end")
    post_code = (assigned_post_code or "").strip()
    if len(post_code) > MAX_POST_CODE_CHARS:
        raise NotifyPrefsRejected(
            f"assigned_post_code 가 {len(post_code)}자다. 상한은 {MAX_POST_CODE_CHARS}자")

    payload = {"quiet_hours_start": start, "quiet_hours_end": end,
              "assigned_post_code": post_code}
    audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=ACTION_SAVE,
        outcome=audit_writer.ALLOWED,
        reason=f"근무 외 알림 차단 {start or '없음'}~{end or '없음'} · "
               f"담당 초소 {post_code or '없음'}",
        after=payload, api_name=ACTION_SAVE, api_method="POST")
    return dict(payload)
