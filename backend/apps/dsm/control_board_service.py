# -*- coding: utf-8 -*-
"""DSM-U4-04 — **통제·대피 현황판** (`POST /api/dsm/control-points` ·
`.../control-points/{id}/advance` · `GET .../control-points`) · 차선 N4 · 턴 AM.

명세(§4.4)의 완결 조건은 「4시각 전부 기록」— 통제 개소(지하차도·둔치주차장·
하천 산책로·도로) 하나가 **도달 → 결정 → 실행 → 해제** 넷을 순서대로 거치는가다
(`apps/dsm/u4_regulations.py::CONTROL_STAGE_ORDER`). 「대피 인원·장소」도 같은
표의 칸이다(등록 때 함께 받는다 — 통제 개소와 대피가 다른 표로 갈리면 「현황판
한 화면」이 두 화면이 된다).

★ **새 표를 만들지 않는다** — `threshold_alert_service.py`(관측→결정 두 걸음)와
같은 판단을 넷으로 늘렸을 뿐이다. 지점 하나 = 감사 최대 넷(도달·결정·실행·해제),
**단계를 건너뛸 수 없다**(순서 검사는 이 파일이 한다 — 지어낸 문지기가 아니라
`CONTROL_STAGE_ORDER` 표 하나로 판정한다).

★ 「일일보고 자동 반영」(명세서 §4.4 출력 칸)은 **이번 턴 범위 밖**이다 —
DSM-U4-05(일일상황보고 자동)가 이번 배정에서도 미착수라 반영할 문서가 없다
(promotions.md 의 「무엇이 없는가」 참조).
"""
from __future__ import annotations

from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from common import audit_writer
from common.tenant_filters import get_user_group
from common.tenant_scope import TenantScope

from apps.dsm.u4_regulations import CONTROL_STAGE_ORDER

LOGGER_NAME = "guardianx.u4.control_board"
TAG = "[U4-CONTROL]"
SCAN_CAP = 1000


class ControlPointRejected(Exception):
    """저장할 수 없다 — 소속 조직이 없다."""


class ControlPointOutOfOrder(Exception):
    """단계 순서를 어겼다(도달 없이 결정 등) — 409 로 번역된다."""


def _create_action(group_id: int) -> str:
    return f"control_point_create:{group_id}"


def _stage_action(group_id: int, point_id: int, stage: str) -> str:
    return f"control_point_stage:{group_id}:{point_id}:{stage}"


def _parse_when(when: str | None):
    if not when:
        return timezone.now()
    parsed = parse_datetime(when)
    if parsed is None:
        raise ValueError(f"시각을 읽을 수 없습니다: {when!r}")
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


def _require_group(scope: TenantScope):
    actor = scope.require_actor()  # 시스템 스코프면 SystemScopeCannotRead
    group = get_user_group(actor)
    if group is None:
        raise ControlPointRejected("소속 조직이 없어 통제 지점을 저장할 수 없습니다.")
    return actor, group


def create_point(*, scope: TenantScope, name: str, reached_at: str | None = None,
                 evacuee_count: int | None = None,
                 evacuation_site: str = "") -> dict[str, Any]:
    """`POST /control-points` — 통제 개소 등록 = **도달** 시각(1/4)을 남긴다.

    Raises:
        ValueError: `name` 이 비었다 · `evacuee_count` 가 음수다 · `reached_at`
            을 못 읽는다.
        ControlPointRejected: 소속 조직이 없다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("통제 개소 이름이 비어 있습니다.")
    if evacuee_count is not None and evacuee_count < 0:
        raise ValueError(f"대피 인원은 0 이상이다 — evacuee_count={evacuee_count!r}")
    when = _parse_when(reached_at)

    actor, group = _require_group(scope)
    stamp = timezone.localtime(when).strftime("%Y-%m-%d %H:%M")
    evac_text = (f"{evacuee_count}명" if evacuee_count is not None else "(미기재)")
    reason = (f"개소={name} · 도달={stamp} · 대피인원={evac_text} · "
             f"대피장소={evacuation_site or '(미기재)'}")
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_create_action(group.pk), outcome=audit_writer.ALLOWED,
        reason=reason, api_method="POST",
    )
    return {"point_id": entry.audit_id, "name": name, "reached_at": when,
            "evacuee_count": evacuee_count, "evacuation_site": evacuation_site,
            "stage": CONTROL_STAGE_ORDER[0]}


def _point_row(group_id: int, point_id: int):
    for e in audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP):
        if e.audit_id == point_id and e.action == _create_action(group_id):
            return e
    return None


def _reached_stage(group_id: int, point_id: int, stage: str) -> bool:
    action = _stage_action(group_id, point_id, stage)
    for e in audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP):
        if e.action == action:
            return True
    return False


def advance(*, scope: TenantScope, point_id: int, stage: str,
           when: str | None = None, note: str = "") -> dict[str, Any]:
    """`POST /control-points/{id}/advance` — 다음 단계(결정→실행→해제) 시각을 남긴다.

    Raises:
        ValueError: `stage` 가 「결정·실행·해제」 밖이다 · `when` 을 못 읽는다.
        django.http.Http404: 그런 통제 지점이 없다 · 남의 테넌트다.
        ControlPointOutOfOrder: 앞 단계 없이 이 단계를 부르거나, 이미 이 단계를 거쳤다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    from django.http import Http404

    if stage not in CONTROL_STAGE_ORDER[1:]:
        raise ValueError(f"stage 는 {CONTROL_STAGE_ORDER[1:]} 중 하나다 — stage={stage!r}")
    at = _parse_when(when)

    actor, group = _require_group(scope)
    if _point_row(group.pk, point_id) is None:
        raise Http404("그런 통제 지점이 없습니다.")

    idx = CONTROL_STAGE_ORDER.index(stage)
    prior = CONTROL_STAGE_ORDER[idx - 1]
    if prior != CONTROL_STAGE_ORDER[0] and not _reached_stage(group.pk, point_id, prior):
        raise ControlPointOutOfOrder(
            f"지점#{point_id}은 아직 「{prior}」 단계가 없습니다 — "
            f"「{stage}」를 먼저 남길 수 없습니다.")
    if _reached_stage(group.pk, point_id, stage):
        raise ControlPointOutOfOrder(f"지점#{point_id}은 이미 「{stage}」 시각이 있습니다.")

    stamp = timezone.localtime(at).strftime("%Y-%m-%d %H:%M")
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_stage_action(group.pk, point_id, stage), outcome=audit_writer.ALLOWED,
        reason=f"지점#{point_id} {stage}={stamp}" + (f" · {note}" if note else ""),
        api_method="POST",
    )
    return {"point_id": point_id, "stage": stage, "stage_id": entry.audit_id,
            "occurred_at": at}


def list_board(*, scope: TenantScope, limit: int = 200) -> list[dict[str, Any]]:
    """`GET /control-points` — 현황판: 지점마다 지금까지 거친 단계와 각 시각.

    Raises:
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        return []
    entries = audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP)
    points: dict[int, dict[str, Any]] = {}
    for e in entries:
        if e.action == _create_action(group.pk):
            points.setdefault(e.audit_id, {
                "point_id": e.audit_id, "text": e.reason,
                "stage": CONTROL_STAGE_ORDER[0]})
    for point_id, row in points.items():
        for stage in CONTROL_STAGE_ORDER[1:]:
            if _reached_stage(group.pk, point_id, stage):
                row["stage"] = stage
    rows = sorted(points.values(), key=lambda r: r["point_id"], reverse=True)
    return rows[:limit]
