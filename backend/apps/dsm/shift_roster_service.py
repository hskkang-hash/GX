# -*- coding: utf-8 -*-
"""DSM-U5-05 — **교대 편성(4조 3교대) 근무표 업로드(CSV)** (`POST
/api/dsm/shifts/import` · `GET .../shifts`) · 차선 N4 · 턴 AM.

명세(§4.5)는 「CSV → `shifts` → 표 → 일지 근무자 = 편성표」다. 이 파일이 닫는
것은 **CSV 업로드 → 저장 → 조회 표**까지다 — 「인계 메모·일지의 근무자 자동
채움」은 **닫지 않는다**(N4_promotions.md 의 「무엇이 없는가」 참조: 관제일지
자체(DSM-U1-04)가 이 제품에 없고, `handover_service.py`(다른 턴 소유)를 이번
턴이 고치지 않기로 했다 — 그래서 부분 승격이다).

CSV 모양 — 헤더 고정 넷: `date,team,shift,members`
-----------------------------------------------------
  · `date`    YYYY-MM-DD
  · `team`    `apps/dsm/u4_regulations.SHIFT_TEAMS` 중 하나(1~4조)
  · `shift`   `apps/dsm/u4_regulations.SHIFT_KINDS` 중 하나(주간·야간·비번)
  · `members` 근무자 이름을 세미콜론(`;`)으로 이은 것

★ **한 줄이라도 계약을 벗어나면 전체를 저장하지 않는다**(전부 아니면 전무) —
  반만 들어간 근무표는 「이번 주 편성」을 아무도 못 믿는다.
★ **새 표를 만들지 않는다** — `(날짜,조)` 마다 감사 한 줄, 재업로드는 **새 줄이
  이긴다**(`alert_level_service` 의 「최근 줄이 정본」과 같은 규약).
"""
from __future__ import annotations

import csv
import io
from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_date

from common import audit_writer
from common.tenant_filters import get_user_group
from common.tenant_scope import TenantScope

from apps.dsm.u4_regulations import SHIFT_KINDS, SHIFT_TEAMS

LOGGER_NAME = "guardianx.u5.shift_roster"
TAG = "[U5-SHIFT]"
SCAN_CAP = 2000
CSV_HEADER = ("date", "team", "shift", "members")
#: 한 번 업로드로 받는 줄 수 상한 — 4조 × 하루 4행이면 1년(365일)도 1460행,
#: 여유를 둔다.
IMPORT_CAP = 2000


class ShiftRosterRejected(Exception):
    """저장할 수 없다 — 소속 조직이 없다."""


def _row_action(group_id: int, date_str: str, team: str) -> str:
    return f"shift_roster:{group_id}:{date_str}:{team}"


def _require_group(scope: TenantScope):
    actor = scope.require_actor()  # 시스템 스코프면 SystemScopeCannotRead
    group = get_user_group(actor)
    if group is None:
        raise ShiftRosterRejected("소속 조직이 없어 근무표를 저장할 수 없습니다.")
    return actor, group


def _parse_rows(csv_text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None or tuple(reader.fieldnames) != CSV_HEADER:
        raise ValueError(
            f"CSV 머리글이 {CSV_HEADER} 와 다릅니다 — {tuple(reader.fieldnames or ())}")
    rows = list(reader)
    if not rows:
        raise ValueError("CSV 에 근무표 줄이 없습니다.")
    if len(rows) > IMPORT_CAP:
        raise ValueError(f"한 번에 {IMPORT_CAP}줄을 넘을 수 없습니다 — {len(rows)}줄.")

    parsed: list[dict[str, str]] = []
    for i, row in enumerate(rows, start=2):  # 1행은 머리글이므로 데이터는 2행부터
        date_raw = (row.get("date") or "").strip()
        team = (row.get("team") or "").strip()
        shift = (row.get("shift") or "").strip()
        members = (row.get("members") or "").strip()
        date_val = parse_date(date_raw)
        if date_val is None:
            raise ValueError(f"{i}행 — 날짜를 읽을 수 없습니다: {date_raw!r}")
        if team not in SHIFT_TEAMS:
            raise ValueError(f"{i}행 — 조는 {SHIFT_TEAMS} 중 하나다: {team!r}")
        if shift not in SHIFT_KINDS:
            raise ValueError(f"{i}행 — 근무는 {SHIFT_KINDS} 중 하나다: {shift!r}")
        if not members:
            raise ValueError(f"{i}행 — 근무자 명단이 비어 있습니다.")
        parsed.append({"date": date_val.isoformat(), "team": team, "shift": shift,
                      "members": members})
    return parsed


def import_csv(*, scope: TenantScope, csv_text: str) -> dict[str, Any]:
    """`POST /shifts/import` — CSV 전체를 검증하고(전부 아니면 전무), 줄마다 감사 한
    줄로 남긴다.

    Raises:
        ValueError: 머리글이 다르다 · 줄이 없다 · 상한 초과 · 한 줄이라도 계약 밖이다.
        ShiftRosterRejected: 소속 조직이 없다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    rows = _parse_rows(csv_text)  # 전량 검증 — 하나라도 틀리면 여기서 예외, 아무것도 안 쓴다
    actor, group = _require_group(scope)

    saved = []
    for row in rows:
        entry = audit_writer.write(
            logger_name=LOGGER_NAME, tag=TAG, actor=actor,
            action=_row_action(group.pk, row["date"], row["team"]),
            outcome=audit_writer.ALLOWED,
            reason=(f"날짜={row['date']} · 조={row['team']} · 근무={row['shift']} · "
                   f"근무자={row['members']}"),
            api_method="POST",
        )
        saved.append(entry.audit_id)
    return {"imported": len(saved), "row_ids": saved}


def list_roster(*, scope: TenantScope, date: str | None = None,
                limit: int = 500) -> list[dict[str, Any]]:
    """`GET /shifts` — 근무표 표. `date` 로 좁힐 수 있다. 같은 (날짜,조)는 **가장
    나중에 올린 줄이 이긴다**(재업로드 정정을 반영한다).

    Raises:
        ValueError: `date` 를 못 읽는다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    if date is not None and parse_date(date) is None:
        raise ValueError(f"날짜를 읽을 수 없습니다: {date!r}")
    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        return []
    entries = audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP)
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    prefix = f"shift_roster:{group.pk}:"
    for e in entries:  # 최신 먼저 오므로(`read` 가 `-id`) 처음 본 것이 최신이다
        if not e.action.startswith(prefix):
            continue
        parts = e.action.split(":")
        if len(parts) != 4:
            continue
        _, _, row_date, team = parts
        if date is not None and row_date != date:
            continue
        key = (row_date, team)
        if key in latest:
            continue
        latest[key] = {"date": row_date, "team": team, "text": e.reason,
                       "row_id": e.audit_id}
    rows = sorted(latest.values(), key=lambda r: (r["date"], r["team"]), reverse=True)
    return rows[:limit]
