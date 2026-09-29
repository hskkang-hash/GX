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

★ [턴 AN · P-392 · 차선 N1] 「일일보고 자동 반영」 채움 — 턴 AM 은 이 칸을
  DSM-U4-05(일일상황보고 자동 · 06:00 배치)가 없다는 이유로 비워 뒀다. 그런데
  이 절(U4-04) 자신이 명세에서 부르는 것은 **06:00 자동 배치**가 아니라
  「일일보고 자동 반영」 — 즉 통제 현황이 사람이 다시 세지 않아도 일일상황보고에
  꽂을 수 있는 모양으로 **자동 산출**되는가다. `daily_reflection()` 이 그것을
  한다: 지금까지 쌓인 감사에서 지점마다 지금 단계를 다시 뽑아(=`list_board` 와
  같은 자료) 「기준 시각 · 단계별 집계 · 지점 목록」으로 접어 낸다. **U4-05 의
  06:00 자동 배치·HWPX 출력 자체는 여전히 이 파일의 범위 밖이다** — 이 함수가
  내는 것은 그 배치가 삼킬 수 있는 **자료**이지, 그 배치 자체가 아니다(경계는
  그대로 정직하게 남긴다).
"""
from __future__ import annotations

from typing import Any

from django.apps import apps as django_apps
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from common import audit_writer
from common.tenant_filters import get_user_group
from common.tenant_scope import TenantScope

from apps.dsm.u4_regulations import CONTROL_STAGE_ORDER

LOGGER_NAME = "guardianx.u4.control_board"
TAG = "[U4-CONTROL]"
SCAN_CAP = 1000


def _audit_model():
    return django_apps.get_model("logger", "AuditLogs")


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
        #: [턴 AP · 차선 N4 · U4-05 일일상황보고 「대피」 칸] 구조화 칸 — `reason`
        #: 문장을 다시 파싱하지 않고 `list_board`/`u4_daily_report_service` 가
        #: 그대로 읽는다. `list_board` 의 기존 소비자는 `text`·`stage` 만 쓰므로
        #: 이 칸을 더해도 안 깨진다(D-212).
        after={"name": name, "evacuee_count": evacuee_count,
              "evacuation_site": evacuation_site},
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
                "stage": CONTROL_STAGE_ORDER[0],
                #: [턴 AP · 차선 N4] 아래에서 구조화 칸으로 채운다 — 못 찾으면
                #: `None`(옛 행 · `after=` 없이 쓰인 행일 수 있다).
                "evacuee_count": None, "evacuation_site": None})
    if points:
        rows = (
            _audit_model()._base_manager
            .filter(logger_name=LOGGER_NAME, api_name=_create_action(group.pk),
                    pk__in=points.keys())
        )
        for r in rows:
            payload = r.data_after if isinstance(r.data_after, dict) else {}
            row = points.get(r.pk)
            if row is not None:
                row["evacuee_count"] = payload.get("evacuee_count")
                row["evacuation_site"] = payload.get("evacuation_site")
    for point_id, row in points.items():
        for stage in CONTROL_STAGE_ORDER[1:]:
            if _reached_stage(group.pk, point_id, stage):
                row["stage"] = stage
    rows = sorted(points.values(), key=lambda r: r["point_id"], reverse=True)
    return rows[:limit]


def daily_reflection(*, scope: TenantScope, as_of: str | None = None) -> dict[str, Any]:
    """`GET /control-points/daily-report` — DSM-U4-04 「일일보고 자동 반영」.

    통제 현황판을 사람이 다시 세지 않고 **일일상황보고의 통제현황 칸**이 그대로
    삼킬 수 있는 모양으로 접어 낸다 — 기준 시각 · 단계별 집계 · 지점 목록.
    이 함수가 감사에서 다시 세는 것은 `list_board` 와 **같은 자료**다(두 번째
    집계를 새로 만들지 않는다 — 두 집계는 반드시 어긋난다, `handover_service.py`
    머리말 「셈은 여기서 하지 않는다」와 같은 판단).

    Raises:
        ValueError: `as_of` 를 못 읽는다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    when = _parse_when(as_of)
    board = list_board(scope=scope, limit=SCAN_CAP)
    by_stage: dict[str, int] = {}
    for row in board:
        by_stage[row["stage"]] = by_stage.get(row["stage"], 0) + 1
    return {
        "as_of": when,
        "reference": "통제현황",
        "point_count": len(board),
        "by_stage": by_stage,
        "points": board,
    }
