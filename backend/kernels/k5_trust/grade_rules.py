# -*- coding: utf-8 -*-
"""표 ③ 등급규칙 — F-12 「등급규칙」 · F-04 「JSON 무재기동 반영」 (D-368).

한 문장
-------
    `event_type` 을 어느 `severity` 로 읽을 것인가를 **운영이 재기동 없이** 바꾼다.

무엇이 여기 있고 무엇이 코드에 있나 — 표 ①과 **같은 모양**
----------------------------------------------------------
    정의(코드)  `detection_event_bridge.EVENT_TYPE_TO_SEVERITY`
                — 잠정 기본값과 **그 값을 고른 근거**. 커밋으로 바뀐다
    값(DB)      `GradeRule` · `GradeRuleChange`
                — 운영이 덮어쓴 값과 그 내력. 화면으로 바뀐다

같은 모양으로 두는 이유는 하나다 — 운영자가 설정 화면 두 곳에서 다른 규칙을 배우지
않아도 된다. 그리고 정의를 DB 로 옮기지 않는 이유도 표 ①과 같다: 정의가 DB 에 있으면
운영이 정의를 지울 수 있고, **지워진 정의는 코드가 부를 때 터진다.**

★ 「무재기동 반영」이 무엇을 요구하나 (계약 F-04 AC)
---------------------------------------------------
코드의 사전은 **import 시점에 한 번** 읽힌다. 그것만 있으면 규칙을 바꾸려면 재기동해야
하고, **재기동은 재난 상황 중에 하면 안 되는 일**이다 — 규칙을 고치는 시점은 대개
경보가 쏟아지는 그 순간이기 때문이다.

그래서 `resolve_severity()` 가 **부를 때마다 DB 를 본다.** 캐시를 두지 않는다:
캐시를 두는 순간 "바꿨는데 안 먹는다" 가 생기고, 그 상태는 화면에서 안 보인다.
판정 한 번에 인덱스 조회 한 번이 드는 것이 그 값이다.

★ 등급 **하향**이 이 표에서 가장 위험한 동작이다
------------------------------------------------
`fire → info` 로 내리면 화재가 **조용해진다.** 경보가 안 오는 것은 사고가 아니라
「아무 일도 없음」으로 보이고, 그래서 아무도 신고하지 않는다.
막지는 않는다 — 현장에 따라 필요한 변경일 수 있다. 대신 셋을 요구한다:
**사유** · **이력** · 그리고 아래 `escalation_only` 로 **하향임을 호출자에게 알린다.**

계약이 못박은 것은 여기 없다 (D-280)
------------------------------------
계약 [별첨1] 은 `severity` 열거와 `event_type` 열거를 각각 정의하되 **둘을 잇는 규칙은
적지 않았다.** 그래서 이 표의 어떤 행도 `contract_fixed` 가 아니다 — 표 ①의
F-04 「5분」·F-10 「30초」와 다른 자리다. 계약이 안 정한 것을 계약인 척하지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.apps import apps

from common.tenant_scope import TenantScope

#: 계약 [별첨1] 의 열거 그대로. **오름차순** — 하향인지 상향인지를 이 순서가 정한다.
SEVERITY_ORDER: tuple[str, ...] = ("info", "warning", "critical")


class GradeRuleNotDefined(Exception):
    """정의에 없는 `event_type`. **오타가 새 이벤트 타입이 되지 않게** (표 ①과 같은 규약)."""


class SeverityNotInContract(Exception):
    """계약 열거 밖의 `severity`. 새 등급을 설정 화면에서 만들 수 없다."""


@dataclass(frozen=True)
class GradeRuleView:
    """등급규칙 한 줄의 **사실**. 화면·보고서가 이것을 읽는다."""

    event_type: str
    #: 지금 적용되는 값 (덮어썼으면 그 값, 아니면 코드의 잠정 기본값)
    severity: str
    #: 코드가 정한 잠정 기본값. **언제나 함께 낸다** — 무엇에서 바꿨는지가 보여야 한다
    default_severity: str
    #: 덮어쓴 적이 있는가. `False` 면 아래 `reason` 은 빈 문자열이다
    overridden: bool
    reason: str
    #: ★ 기본값보다 **낮은가.** 참이면 그 이벤트는 조용해진 것이다
    lowered: bool


def _defaults() -> dict[str, str]:
    """코드의 잠정 기본값. **여기서 복사하지 않고 그때그때 읽는다.**

    복사해 두면 `detection_event_bridge` 가 바뀌는 날 이 모듈만 옛말이 되고,
    옛말이 된 사전은 옛말인 것이 안 보인다 (D-286).
    """
    from stream_monitors.services.detection_event_bridge import EVENT_TYPE_TO_SEVERITY

    return dict(EVENT_TYPE_TO_SEVERITY)


def _model(name: str):
    return apps.get_model("stream_monitors", name)


def _scoped(qs, scope: TenantScope):
    """표 ①·구역 판정과 **같은 좁히기.** 세 곳이 다른 방식을 쓰면 언젠가 갈린다(D-212).

    ★ 좁히기를 손으로 조립하지 않고 `common.tenant_filters` 의 **진짜 문지기**를 부른다.
      `verify_tenant_scope.py` 가 호출 그래프에서 그 이름을 찾는 것이 판정 기준이고,
      기준이 그런 이유는 하나다 — 표식이 아니라 **실제로 막는 것**만 인정하기 위해서다(P-K1-1).
    """
    from common.tenant_filters import filter_by_group_field, is_global_admin

    if scope.is_system:
        return qs
    if is_global_admin(scope.actor):
        return qs
    from common.tenant_filters import get_user_group

    if get_user_group(scope.actor) is None:
        return qs.none()
    return filter_by_group_field(qs, scope.actor)


def _rank(severity: str) -> int:
    try:
        return SEVERITY_ORDER.index(severity)
    except ValueError:
        raise SeverityNotInContract(
            f"severity={severity!r} 는 계약 열거 밖이다 {SEVERITY_ORDER} — "
            f"새 등급을 설정 화면에서 만들 수 없다. 열거를 늘리려면 계약 해석부터 받는다"
        ) from None


# ═══════════════════════════════════════════════════════════════════════════
# 판정 — **부를 때마다 DB 를 본다.** 그것이 「무재기동 반영」이다 (F-04)
# ═══════════════════════════════════════════════════════════════════════════
def _resolve_severity(event_type: str, *, group=None) -> str:
    """이 검출을 어느 등급으로 읽을 것인가. **캐시하지 않는다.**

    ★ 테넌트를 **요청자가 아니라 `group` 으로** 받는다 — 검출 파이프라인에는 요청자가
      없기 때문이다(D-281). 그 자리의 테넌트는 **그 카메라의 주인**이고, 그것을
      아는 것은 부르는 쪽(`detection_event_bridge`)이다.

      [실측 2026-09-10] 처음에는 `scope=None` 이면 좁히지 **않게** 짰다. 그러면
      스코프 없이 부른 판정이 **아무 테넌트의 규칙이나 집었고**, 시험이 그것을 잡았다
      (`test_the_pipeline_sees_only_global_rules`). 「좁히지 않는다」와 「전역만 본다」는
      다른 뜻이고, 그 둘을 한 값(None)에 둔 것이 잘못이었다.

      그래서 지금:
          group=None   **주인 없는(전역) 규칙만** 본다. 없으면 코드 기본값
          group=<그룹>  그 테넌트 규칙 → 없으면 전역 → 없으면 코드 기본값

    ★ 정의에 없는 타입은 **거부한다.** 조용히 `info` 로 떨어뜨리면 새 위험이
      가장 낮은 등급으로 조용히 들어온다 (D-284).
    """
    defaults = _defaults()
    if event_type not in defaults:
        raise GradeRuleNotDefined(
            f"event_type={event_type!r} 는 정의에 없다. 있는 것: "
            f"{', '.join(sorted(defaults))}. 새 타입은 "
            f"detection_event_bridge 의 정의를 먼저 올린다 — 정의 없는 타입은 "
            f"아무도 등급을 검토한 적이 없다")

    Rule = _model("GradeRule")
    base = Rule._base_manager.filter(event_type=event_type, is_active=True)
    lookup = _group_field(Rule)

    if group is not None:
        row = base.filter(**{lookup: group}).order_by("-id").first()
        if row is not None:
            return row.severity            # 좁은 것이 이긴다 (표 ①과 같은 규약)
    row = base.filter(**{f"{lookup}__isnull": True}).order_by("-id").first()
    return row.severity if row is not None else defaults[event_type]


def _group_field(model) -> str:
    """소유 칸의 이름. 하드코딩하지 않는다 — dj-core 가 주는 이름을 실측으로 읽는다."""
    names = {f.name for f in model._meta.get_fields()}
    return "groups" if "groups" in names else "group"


def _group_of_stream(stream_monitor_id: int):
    """그 카메라의 주인 테넌트. **판정의 테넌트는 요청자가 아니라 카메라의 주인이다.**

    파이프라인에는 요청자가 없으므로(D-281) 여기서 테넌트를 정한다. 못 정하면 `None` 이고,
    그러면 전역 규칙만 본다 — **추측하지 않는다.**
    """
    StreamMonitor = _model("StreamMonitor")
    row = StreamMonitor._base_manager.filter(pk=stream_monitor_id).first()
    if row is None:
        return None
    lookup = _group_field(StreamMonitor)
    if lookup == "groups":
        return row.groups.first()
    return getattr(row, "group", None)


def severity_for(*, scope: TenantScope, event_type: str,
                 stream_monitor_id: int | None = None) -> str:
    """★ **공개 판정 면** — 이 검출을 어느 등급으로 읽을 것인가 (F-04 무재기동 반영).

    D-281 이 요구하는 대로 **테넌트 없이는 부를 수 없다.** 다만 「테넌트」가 무엇인지가
    이 함수의 요점이다:

        stream_monitor_id 가 있으면  → **그 카메라의 주인**이 테넌트다.
                                       검출 파이프라인에는 요청자가 없으므로(D-281)
                                       요청자에게서 테넌트를 얻을 수 없다
        없고 사람이 부르면          → 부른 사람의 소속
        없고 시스템 스코프면        → **전역 규칙만.** 추측하지 않는다

    ★ `scope` 를 받되 그것으로 좁히지 **않는** 경우가 있다는 것이 이 함수의 정직한
      모양이다 — 파이프라인의 스코프는 「누가 부르는가」가 아니라 「왜 사람이 없는가」의
      사유를 들고 있고(D-281), 판정의 테넌트는 카메라에서 온다.
    """
    if stream_monitor_id is not None:
        return _resolve_severity(event_type, group=_group_of_stream(stream_monitor_id))
    if scope.is_system:
        return _resolve_severity(event_type)
    # ★ 사람이 부르면 **소속을 요구한다** — `get_user_group`(있으면 준다)이 아니라
    #   `require_user_group`(없으면 멈춘다)이다. 소속 없는 사람에게 전역 규칙으로
    #   조용히 답하면, 그 사람은 자기 테넌트의 규칙이 적용된 줄 안다.
    #   그리고 이것이 `common.tenant_filters` 의 진짜 문지기라 호출 그래프 추적이
    #   인정한다 — 표식이 아니라 실제로 막기 때문이다(P-K1-1).
    from common.tenant_filters import require_user_group

    return _resolve_severity(event_type, group=require_user_group(scope.actor))


def list_grade_rules(*, scope: TenantScope) -> list[GradeRuleView]:
    """설정 화면이 읽는 전체 표 — **정의 전건 + 덮어쓴 값.**

    덮어쓴 행만 내면 화면은 "규칙이 2개" 를 그리고, 운영자는 나머지 타입이
    **규칙 없이 돈다**고 읽는다. 정의 전건을 내고 어느 것이 덮였는지를 칸으로 낸다.
    """
    defaults = _defaults()
    Rule = _model("GradeRule")
    overrides = {}
    for row in _scoped(Rule._base_manager.filter(is_active=True),
                       scope).order_by("id"):
        overrides[row.event_type] = row

    views = []
    for event_type in sorted(defaults):
        default = defaults[event_type]
        row = overrides.get(event_type)
        severity = row.severity if row is not None else default
        views.append(GradeRuleView(
            event_type=event_type,
            severity=severity,
            default_severity=default,
            overridden=row is not None,
            reason=row.reason if row is not None else "",
            lowered=_rank(severity) < _rank(default),
        ))
    return views


def set_grade_rule(*, scope: TenantScope, event_type: str, severity: str,
                   reason: str) -> GradeRuleView:
    """등급규칙 하나를 덮어쓴다. **사유 없이는 못 바꾼다.**

    권한 판정은 여기서 하지 않는다 — F-12 문지기(`apps.dsm.services.guard_setting`)가
    한다. **판정식을 두 벌 두지 않는다**(D-212).

    ★ 하향이면 `lowered=True` 로 **돌려준다.** 막지는 않는다 — 현장에 따라 필요한
      변경일 수 있다. 다만 부르는 쪽이 그 사실을 모르고 지나갈 수는 없게 한다.
    """
    from django.db import transaction

    defaults = _defaults()
    if event_type not in defaults:
        raise GradeRuleNotDefined(
            f"event_type={event_type!r} 는 정의에 없다. 있는 것: "
            f"{', '.join(sorted(defaults))}")
    new_rank = _rank(severity)                      # 열거 밖이면 여기서 멈춘다
    if not (reason or "").strip():
        raise ValueError(
            "사유가 없다. 등급을 낮추는 변경은 **경보를 끄는 것**이고, 사유 없는 "
            "하향은 사후에 '왜 경보가 안 왔나' 에 아무도 답하지 못하게 만든다")

    actor = scope.require_actor()
    Rule, Change = _model("GradeRule"), _model("GradeRuleChange")

    with transaction.atomic():
        row = _scoped(Rule._base_manager.filter(event_type=event_type, is_active=True),
                      scope).order_by("-id").first()
        previous = row.severity if row is not None else None

        if row is None:
            row = Rule._base_manager.create(
                event_type=event_type, severity=severity, reason=reason.strip())
            _inherit_group(row, actor)
        else:
            row.severity = severity
            row.reason = reason.strip()
            row.save(update_fields=["severity", "reason"])

        change = Change._base_manager.create(
            event_type=event_type, old_severity=previous, new_severity=severity,
            reason=reason.strip(), changed_by=actor)
        _inherit_group(change, actor)

    return GradeRuleView(
        event_type=event_type, severity=severity,
        default_severity=defaults[event_type], overridden=True,
        reason=reason.strip(),
        lowered=new_rank < _rank(defaults[event_type]),
    )


def grade_rule_history(*, scope: TenantScope, limit: int = 20) -> list[dict]:
    """변경 내력. **무엇에서 무엇으로, 누가, 왜.**

    `updated_at` 한 칸으로는 "언제" 만 답한다 — 사고 뒤에 필요한 것은 나머지 셋이다.
    """
    Change = _model("GradeRuleChange")
    rows = _scoped(Change._base_manager.all(), scope)[:limit]
    return [{"event_type": r.event_type, "old_severity": r.old_severity,
             "new_severity": r.new_severity, "reason": r.reason,
             "changed_at": r.changed_at,
             "changed_by": getattr(r.changed_by, "username", None)}
            for r in rows]


def _inherit_group(row, actor) -> None:
    """소유를 박는다. 필드 이름을 하드코딩하지 않는다 — 실행 중인 dj-core 는
    `group` FK 를 준다(D-292 실측). 주인 없는 행은 §0.4 의 OR 절을 타고 모두에게 보인다."""
    from common.tenant_filters import get_user_group

    group = get_user_group(actor)
    if group is None:
        return
    names = {f.name for f in type(row)._meta.get_fields()}
    if "groups" in names:
        row.groups.set([group])
    elif "group" in names:
        row.group = group
        row.save(update_fields=["group"])


__all__ = [
    "SEVERITY_ORDER",
    "GradeRuleNotDefined",
    "SeverityNotInContract",
    "GradeRuleView",
    "severity_for",
    "list_grade_rules",
    "set_grade_rule",
    "grade_rule_history",
]
