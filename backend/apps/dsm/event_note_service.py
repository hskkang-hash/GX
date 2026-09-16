# -*- coding: utf-8 -*-
"""부속서A U1 #15 「사건에 메모 남기기」(`POST|GET /events/{id}/note`) · 차선 U1 · 턴 R.

새 표를 만들지 않는다 — `common/audit_writer.py` 가 이미 「누가·언제·무엇을 남겼나」를
쓰는 자리다(F-12 설정 감사·K5 자격 접근 감사가 이미 같은 표를 쓴다. `apps/dsm/audit.py`
머리말과 같은 판단). 메모도 그 모양이다: 표를 하나 더 두면 이력이 두 곳에 쌓이고
어느 쪽이 전부인지 아무도 모른다.

행 하나 = 사건 하나의 메모 하나. `action` 칸을 사건별로 가른다(`event_note:{id}`).
★ **테넌트로 다시 거르지 않는다 — 거를 필요가 없다.** 그 사건이 요청자의 테넌트
  것인지는 `services.event_detail`(K1)이 이미 확인했다(아니면 `Http404`). 그 관문을
  통과한 `event_id` 로만 `action` 을 채우므로, 남의 사건 id 를 넣어 봐야 이 함수
  앞에서 이미 막힌다 — 여기서 다시 `group` 을 비교하면 같은 문지기가 두 벌이 되고
  두 벌은 언젠가 어긋난다.
"""
from __future__ import annotations

from common import audit_writer
from common.tenant_scope import TenantScope

from apps.dsm.services import event_detail

#: 이 계열의 감사 전건을 가르는 이름 — F-12(`guardianx.f12.settings`)와 같은 표를
#: 쓰되 이름으로 갈린다(D-325 표 ②와 같은 모양).
LOGGER_NAME = "guardianx.u1.event_note"
TAG = "[U1-NOTE]"

#: 메모 한 줄의 길이 상한 — 타임라인 카드 한 장에 들어가는 길이다.
MAX_LEN = 1000


def _action(event_id: int) -> str:
    return f"event_note:{event_id}"


def add_note(*, scope: TenantScope, event_id: int, text: str) -> dict:
    """메모 한 줄을 남긴다.

    Raises:
        django.http.Http404: 없는 이벤트 · 남의 테넌트 이벤트(K1 이 올린다).
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
        ValueError: 메모가 비었거나 상한(1000자)을 넘었다.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("메모가 비어 있습니다.")
    if len(text) > MAX_LEN:
        raise ValueError(f"메모는 {MAX_LEN}자를 넘을 수 없습니다.")

    event = event_detail(scope=scope, event_id=event_id)  # 남의 사건이면 여기서 404
    actor = scope.require_actor()  # 시스템 스코프면 SystemScopeCannotRead

    #: ★ [실측 2026-09-16 · 스모크 시험] `api_name` 을 여기서 채우면 안 된다 —
    #:   `audit_writer.write()` 는 `api_name or action` 으로 저장 칸을 고르는데,
    #:   `api_name` 을 넘기면 그것이 이기고 **사건별 이름(`event_note:{id}`)이
    #:   묻힌다.** `read()` 는 그 이름으로 거르므로, 방금 쓴 메모를 스스로 못 찾는
    #:   조용한 버그였다 — 넘기지 않아야 `action` 이 저장 칸에 들어간다.
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_action(event.event_id), outcome=audit_writer.ALLOWED,
        reason=text, api_method="POST",
    )
    return {
        "note_id": entry.audit_id,
        "event_id": event.event_id,
        "text": text,
        "actor_id": entry.actor_id,
    }


def list_notes(*, scope: TenantScope, event_id: int, limit: int = 100) -> list[dict]:
    """사건 하나의 메모 전부 — 최신이 먼저(화면이 타임라인으로 뒤집어 그린다).

    Raises:
        django.http.Http404: 없는 이벤트 · 남의 테넌트 이벤트.
    """
    event = event_detail(scope=scope, event_id=event_id)  # 남의 사건이면 여기서 404

    entries = audit_writer.read(
        logger_name=LOGGER_NAME, action=_action(event.event_id), limit=limit)
    return [
        {"note_id": e.audit_id, "event_id": event.event_id,
         "text": e.reason, "actor_id": e.actor_id}
        for e in entries
    ]
