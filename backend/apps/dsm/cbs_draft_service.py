# -*- coding: utf-8 -*-
"""DSM-U4-03 — **재난문자(CBS) 초안** (`POST /api/dsm/cbs-drafts` ·
`.../cbs-drafts/{id}/approve` · `.../cbs-drafts/{id}/sent` · `GET .../cbs-drafts`) ·
차선 N4 · 턴 AM.

명세(§4.4)의 완결 조건은 「승인 시각·발송 기록 감사 · 야간 안전안내 경고」다 —
**발송 자체는 이 제품이 하지 않는다**(명세서 그대로 「발송은 행안부 시스템에서
(복사·붙여넣기)」). 그래서 이 파일이 여는 세 걸음은 초안 → 승인 요청 → **발송
기록**(행안부 시스템에서 실제로 보낸 뒤 사람이 남기는 확인)이고, 「발송」 버튼은
없다 — 있으면 그 자체가 명세를 벗어난 기능이 된다.

★ **새 표를 만들지 않는다** — `alert_level_service.py`·`situation_meeting_service.py`
와 같은 판단. 초안 한 건 = 감사 세 줄(초안·승인·발송)까지 쌓일 수 있는 이력이고,
`threshold_alert_service.decide` 가 쓰는 것과 같은 관용구(만들 때 받은 id로 뒷걸음
질의)로 세 단계를 잇는다 — 한 행을 고쳐 쓰지 않는다.

★ **글자수는 이 파일이 재지 않는다** — `apps/dsm/u4_regulations.py` 의
`CBS_LEN_LIMIT` 표 하나가 정본이다(D-280, 지어내지 않는다 · 명세서 §4.4 실측).
"""
from __future__ import annotations

from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from common import audit_writer
from common.tenant_filters import get_user_group
from common.tenant_scope import TenantScope

from apps.dsm.u4_regulations import (CBS_KIND_SAFETY, CBS_KINDS, CBS_LEN_LIMIT,
                                     CBS_NIGHT_END_HOUR, CBS_NIGHT_START_HOUR)

LOGGER_NAME = "guardianx.u4.cbs_draft"
TAG = "[U4-CBS]"

#: 조회 한 번이 훑는 감사 행 상한 — `threshold_alert_service.decide` 와 같은 자리
#: 다른 값(이 절은 초안·승인·발송 셋이 쌓이므로 조금 더 넓게 둔다).
SCAN_CAP = 1000


class CbsDraftRejected(Exception):
    """저장할 수 없다 — 소속 조직이 없다. `alert_level_service.AlertLevelRejected`
    와 같은 모양."""


class CbsDraftConflict(Exception):
    """상태 전이가 순서를 어겼다(초안 없이 승인 · 승인 없이 발송 · 이미 있는 단계를
    또) — 409 로 번역된다."""


def _draft_action(group_id: int) -> str:
    return f"cbs_draft:{group_id}"


def _approve_action(group_id: int, draft_id: int) -> str:
    return f"cbs_draft_approve:{group_id}:{draft_id}"


def _sent_action(group_id: int, draft_id: int) -> str:
    return f"cbs_draft_sent:{group_id}:{draft_id}"


def _is_night(when) -> bool:
    hour = timezone.localtime(when).hour
    return hour >= CBS_NIGHT_START_HOUR or hour < CBS_NIGHT_END_HOUR


def _parse_when(occurred_at: str | None):
    if not occurred_at:
        return timezone.now()
    parsed = parse_datetime(occurred_at)
    if parsed is None:
        raise ValueError(f"시각을 읽을 수 없습니다: {occurred_at!r}")
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


def _require_group(scope: TenantScope):
    actor = scope.require_actor()  # 시스템 스코프면 SystemScopeCannotRead
    group = get_user_group(actor)
    if group is None:
        raise CbsDraftRejected("소속 조직이 없어 재난문자 초안을 저장할 수 없습니다.")
    return actor, group


def create_draft(*, scope: TenantScope, kind: str, region: str, message: str,
                 occurred_at: str | None = None) -> dict[str, Any]:
    """`POST /cbs-drafts` — 유형·구역·문안을 받아 글자수를 검사하고 초안 한 줄을 남긴다.

    Raises:
        ValueError: `kind` 가 셋 밖 · `region`·`message` 가 비었다 · 글자수 초과 ·
            `occurred_at` 을 못 읽는다.
        CbsDraftRejected: 소속 조직이 없다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    kind = (kind or "").strip()
    if kind not in CBS_KINDS:
        raise ValueError(f"재난문자 유형은 {CBS_KINDS} 중 하나다 — kind={kind!r}")
    region = (region or "").strip()
    if not region:
        raise ValueError("구역(읍면동)이 비어 있습니다.")
    message = (message or "").strip()
    if not message:
        raise ValueError("문안이 비어 있습니다.")
    limit = CBS_LEN_LIMIT[kind]
    if len(message) > limit:
        raise ValueError(f"{kind} 문안은 {limit}자를 넘을 수 없습니다 — "
                        f"지금 {len(message)}자.")

    when = _parse_when(occurred_at)
    night_warning = kind == CBS_KIND_SAFETY and _is_night(when)

    actor, group = _require_group(scope)
    stamp = timezone.localtime(when).strftime("%Y-%m-%d %H:%M")
    reason = (f"유형={kind} · 구역={region} · 글자수={len(message)}/{limit} · "
             f"시각={stamp}" + (" · 야간 안전안내 경고" if night_warning else ""))
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_draft_action(group.pk), outcome=audit_writer.ALLOWED,
        reason=reason, api_method="POST",
    )
    return {
        "draft_id": entry.audit_id, "kind": kind, "region": region,
        "message": message, "length": len(message), "limit": limit,
        "night_warning": night_warning, "status": "초안",
        "occurred_at": when, "actor_id": entry.actor_id,
    }


def _find(*, action: str):
    """`action` 은 group·draft_id 를 이미 품고 있다(`_approve_action`·`_sent_action`
    이 만든 문자열) — 그 행 자신의 `audit_id`(=이 감사 줄 고유 번호, `draft_id` 와는
    다른 값이다)로 다시 좁히면 **항상 못 찾는다**(승인·발송은 매번 새 행이다).
    action 문자열 자체가 이미 유일하므로 그것만으로 찾는다."""
    for e in audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP):
        if e.action == action:
            return e
    return None


def _draft_row(group_id: int, draft_id: int):
    for e in audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP):
        if e.audit_id == draft_id and e.action == _draft_action(group_id):
            return e
    return None


def approve_draft(*, scope: TenantScope, draft_id: int, note: str = "") -> dict[str, Any]:
    """`POST /cbs-drafts/{id}/approve` — 승인권자 결재.

    Raises:
        django.http.Http404: 그런 초안이 없다 · 남의 테넌트 초안이다.
        CbsDraftConflict: 이미 승인됐다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    from django.http import Http404

    actor, group = _require_group(scope)
    if _draft_row(group.pk, draft_id) is None:
        raise Http404("그런 재난문자 초안이 없습니다.")
    already = _find(action=_approve_action(group.pk, draft_id))
    if already is not None:
        raise CbsDraftConflict(f"초안#{draft_id}은 이미 승인됐습니다.")

    stamp = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M")
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_approve_action(group.pk, draft_id), outcome=audit_writer.ALLOWED,
        reason=f"초안#{draft_id} 승인 — 시각={stamp}" + (f" · {note}" if note else ""),
        api_method="POST",
    )
    return {"draft_id": draft_id, "approve_id": entry.audit_id, "status": "승인"}


def mark_sent(*, scope: TenantScope, draft_id: int, sent_at: str | None = None,
             channel_ref: str = "") -> dict[str, Any]:
    """`POST /cbs-drafts/{id}/sent` — 행안부 시스템에서 실제로 보낸 뒤의 **발송 기록**.

    Raises:
        django.http.Http404: 그런 초안이 없다 · 남의 테넌트 초안이다.
        CbsDraftConflict: 승인 전이다 · 이미 발송 기록이 있다.
        ValueError: `sent_at` 을 못 읽는다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    from django.http import Http404

    actor, group = _require_group(scope)
    if _draft_row(group.pk, draft_id) is None:
        raise Http404("그런 재난문자 초안이 없습니다.")
    approved = _find(action=_approve_action(group.pk, draft_id))
    if approved is None:
        raise CbsDraftConflict(f"초안#{draft_id}은 아직 승인되지 않았습니다 — "
                              "승인 전에는 발송 기록을 남길 수 없습니다.")
    already_sent = _find(action=_sent_action(group.pk, draft_id))
    if already_sent is not None:
        raise CbsDraftConflict(f"초안#{draft_id}은 이미 발송 기록이 있습니다.")

    when = _parse_when(sent_at)
    stamp = timezone.localtime(when).strftime("%Y-%m-%d %H:%M")
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_sent_action(group.pk, draft_id), outcome=audit_writer.ALLOWED,
        reason=(f"초안#{draft_id} 발송 기록 — 시각={stamp} · "
               f"경로={channel_ref or '(미기재)'}"),
        api_method="POST",
    )
    return {"draft_id": draft_id, "sent_id": entry.audit_id, "status": "발송",
            "sent_at": when}


def list_drafts(*, scope: TenantScope, limit: int = 100) -> list[dict[str, Any]]:
    """`GET /cbs-drafts` — 초안마다 지금 상태(초안/승인/발송)를 합쳐 최신 먼저.

    Raises:
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        return []
    entries = audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP)
    drafts: dict[int, dict[str, Any]] = {}
    for e in entries:
        if e.action == _draft_action(group.pk):
            drafts.setdefault(e.audit_id, {
                "draft_id": e.audit_id, "text": e.reason, "status": "초안"})
    for draft_id, row in drafts.items():
        for e in entries:
            if e.action == _sent_action(group.pk, draft_id):
                row["status"] = "발송"
                break
            if e.action == _approve_action(group.pk, draft_id):
                row["status"] = "승인"
    rows = sorted(drafts.values(), key=lambda r: r["draft_id"], reverse=True)
    return rows[:limit]
