# -*- coding: utf-8 -*-
"""DSM-U2-03 — **상황판단회의 기록** (`POST|GET /api/dsm/situation-meetings`) · 차선 N1 · 턴 AK.

명세(`DSM_재난안전관리App_명세서_v1.1_지침기반_20260915.md` §4.2)의 완결 조건은
「기록 표 · 감사」다. **새 표를 만들지 않는다** — `apps/dsm/event_note_service.py`
머리말과 같은 판단이다: `common/audit_writer.py` 가 이미 「누가·언제·무엇을 남겼나」를
쓰는 자리이고, 표를 하나 더 두면 이력이 두 곳에 쌓여 어느 쪽이 전부인지 아무도
모르게 된다. 한 회의 기록 = 감사 한 줄, 본문에 시각·참석·결정·근거 값을 사람이
읽을 문장으로 눌러 담는다.

★ **테넌트로 좁힌다 — `action` 칸에 그룹 id 를 싣는다.** `audit_writer.read()` 는
  머리말에 스스로 적어 두었듯 "테넌트로 좁히지 않는다 — 좁히는 판단은 부르는 쪽이
  한다." 이 파일이 그 부르는 쪽이다. `action=f"situation_meeting:{group_id}"` 로
  쓰고 같은 열쇠로만 읽으면, 다른 그룹의 회의 기록은 애초에 이 로거 전건을 스캔해도
  안 걸린다(질의 자체가 다른 이름이다) — `threshold_alert_service` 가 카메라 id 를
  action 에 싣는 것과 같은 결의 판단이다.
"""
from __future__ import annotations

from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.dsm import alert_level_service
from common import audit_writer
from common.tenant_filters import get_user_group
from common.tenant_scope import TenantScope

#: F-12 설정 감사(`apps/dsm/audit.py`)·K5 자격 접근 감사와 같은 표를 쓰되 이름으로 갈린다.
LOGGER_NAME = "guardianx.u2.situation_meeting"
TAG = "[U2-MEETING]"

#: 결정 문장 길이 상한 — 회의 기록 카드 한 장에 들어가는 길이다(`event_note_service`
#: 의 `MAX_LEN` 과 같은 자리, 다른 값 — 회의 기록은 여러 항목을 이어 적으므로 더 넓다).
MAX_LEN = 2000


class SituationMeetingRejected(Exception):
    """저장할 수 없다 — 소속 조직이 없다. `handover_service.HandoverRejected` 와 같은 모양."""


def _action(group_id: int) -> str:
    return f"situation_meeting:{group_id}"


def _fmt(*, occurred_at, attendees: str, decision: str, basis: str) -> str:
    stamp = timezone.localtime(occurred_at).strftime("%Y-%m-%d %H:%M")
    return (f"시각={stamp} · 참석={attendees or '(미기재)'} · "
            f"결정={decision} · 근거={basis or '(미기재)'}")


def record_meeting(*, scope: TenantScope, occurred_at: str | None = None,
                   attendees: str = "", decision: str = "",
                   basis: str = "", alert_level: str = "") -> dict[str, Any]:
    """회의 한 건을 감사 줄로 남긴다.

    ★ [턴 AQ · 차선 W2B] 완결 조건 「결정 → 테넌트 상태 축 변경」 — `alert_level`
      (비상 단계, `alert_level_service.LEVELS` 중 하나)를 함께 보내면 같은 요청에서
      **위기경보·비상 단계 축**(`alert_level_service.record_alert` · `latest_alert()` 가
      읽는 그 축)에 한 줄을 더한다. 새 상태 칸을 만들지 않는다 — 그 축이 이미 이
      테넌트의 「지금 단계」 정본이다(그 파일 머리말). 비우면 축은 그대로다
      (통제·대피만 정한 회의는 단계를 바꾸지 않는다).

    Raises:
        ValueError: `decision` 이 비었거나 상한을 넘었다 · `occurred_at` 이 있는데
            ISO 형식으로 못 읽는다.
        SituationMeetingRejected: 소속 조직이 없어 저장할 수 없다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    decision = (decision or "").strip()
    if not decision:
        raise ValueError("결정(통제·대피·비상 단계)이 비어 있습니다.")
    alert_level = (alert_level or "").strip()
    if alert_level and alert_level not in alert_level_service.LEVELS:
        raise ValueError(
            f"비상 단계는 {'·'.join(alert_level_service.LEVELS)} 중 하나입니다.")

    when = timezone.now()
    if occurred_at:
        parsed = parse_datetime(occurred_at)
        if parsed is None:
            raise ValueError(f"회의 시각을 읽을 수 없습니다: {occurred_at!r}")
        when = timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed

    text = _fmt(occurred_at=when, attendees=(attendees or "").strip(),
               decision=decision, basis=(basis or "").strip())
    if len(text) > MAX_LEN:
        raise ValueError(f"회의 기록은 {MAX_LEN}자를 넘을 수 없습니다.")

    actor = scope.require_actor()  # 시스템 스코프면 SystemScopeCannotRead
    group = get_user_group(actor)
    if group is None:
        raise SituationMeetingRejected(
            "소속 조직이 없어 상황판단회의 기록을 저장할 수 없습니다.")

    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_action(group.pk), outcome=audit_writer.ALLOWED,
        reason=text, api_method="POST",
    )
    applied = None
    if alert_level:
        # 같은 테넌트 · 같은 요청자 — 축의 문지기는 그 함수가 다시 선다.
        applied = alert_level_service.record_alert(
            scope=scope, level=alert_level, occurred_at=when.isoformat(),
            doc_no=f"상황판단회의 기록 #{entry.audit_id}")
    return {
        "meeting_id": entry.audit_id,
        "occurred_at": when,
        "attendees": (attendees or "").strip(),
        "decision": decision,
        "basis": (basis or "").strip(),
        "actor_id": entry.actor_id,
        #: 상태 축에 더한 한 줄 — 단계를 정하지 않은 회의면 None.
        "alert_level": applied,
    }


def list_meetings(*, scope: TenantScope, limit: int = 100) -> list[dict[str, Any]]:
    """최근 회의 기록 — 최신이 먼저 · **내 테넌트 것만**(`_action` 이 좁힌다).

    소속 조직이 없으면 빈 목록이다(0 은 「없다」이지 「못 읽었다」가 아니다 —
    쓰기가 애초에 같은 이유로 거절되므로 이 그룹은 회의 기록을 가질 수 없다).

    Raises:
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        return []
    entries = audit_writer.read(
        logger_name=LOGGER_NAME, action=_action(group.pk), limit=limit)
    return [
        {"meeting_id": e.audit_id, "text": e.reason, "actor_id": e.actor_id}
        for e in entries
    ]
