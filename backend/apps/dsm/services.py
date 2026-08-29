# -*- coding: utf-8 -*-
"""DSM App (L4) — **F-09·F-10·F-11·F-12 의 조립부**.

이 파일이 하는 일과 안 하는 일
------------------------------
    한다   커널 공개 면을 부른다 · 그 결과를 화면·HTTP 가 쓸 모양으로 옮긴다
    안 한다 판정 · 집계 · 중복 억제 · 소유 상속 · 오탐률 계산 — **전부 커널이 한다**

DA-04 §1-1: *"App(L4)·어댑터(L2)는 커널 API 를 **소비만** 한다."*
그래서 이 파일은 얇다. 얇은 것이 게으름이 아니라 계약 8조3항의 경계다.

기능별로 어느 커널을 소비하나
-----------------------------
    F-09 재난 대시보드   K3(프레임·5상태) + K1(이벤트) + adapters.sdn(연계 상태 3표시)
    F-10 알림 발송       K2(수신자·발송·이력)
    F-11 상황 보고서     K4(컨텍스트·렌더) — 조치 이력은 K4 가 K2 에서 가져온다
    F-12 관리자 설정     K3(위젯 가시성) + K2(수신자 확인) + 감사(audit.py)

없는 것을 있다고 하지 않는다 (D-284 · D-280)
--------------------------------------------
F-12 가 계약상 관리해야 하는 다섯 가지 중 **셋은 저장할 표가 없다** —
위험구역·임계값·등급규칙. 실측이다(`grep -rn "class .*Zone\\|Threshold" backend/` → 0건).
그 셋은 조용히 빈 목록을 돌려주지 않고 `SettingNotAvailable` 로 멈춘다.
빈 목록을 돌려주면 화면은 "설정이 없습니다" 를 그리고, 사용자는 **설정 기능이 있는데
비어 있다**고 읽는다. 없는 것과 비어 있는 것은 다르다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from common.tenant_roles import is_global_admin, is_tenant_admin
from common.tenant_scope import TenantScope

import adapters.sdn as sdn
from apps.dsm import audit
from apps.dsm.exceptions import PermissionDeniedForSetting, SettingNotAvailable

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# F-09 재난 대시보드
# ═══════════════════════════════════════════════════════════════════════════
class LinkStatus(str, Enum):
    """FR-09-4 — **연계 상태 3표시.** 계획서 §2.2 설계원칙 2(장애 격리)가 요구한 자리다.

    *"일방 장애 시 타방 단독 동작"* 을 **사람이 눈으로 확인하는 자리**가 이것이다.
    빼면 F-08 의 가치가 화면에서 사라진다.
    """

    #: 연계가 살아 있다. 어댑터가 붙었고 인증이 통한다.
    NORMAL = "normal"
    #: **대기.** 연계할 수 없는 상태이되 우리 잘못이 아니다 — 지금은 명세 미수령이 그것이다.
    WAITING = "waiting"
    #: 붙어 있었는데 지금 끊겼다. 이것이 F-08 이 이벤트로 만드는 상태다.
    DOWN = "down"


@dataclass(frozen=True)
class LinkStateView:
    """연계 상태 한 칸. **왜 그 상태인지를 함께 낸다.**

    "대기" 만 보여 주면 화면 앞의 사람은 기다려야 하는지 신고해야 하는지 모른다.
    DA-03 §2-5 규칙 1이 오류와 빈 상태를 가른 것과 같은 이유다.
    """

    status: LinkStatus
    reason: str


def link_state() -> LinkStateView:
    """SDN 연계 상태 (FR-09-4).

    ★ **어댑터가 없어도 이 칸은 지금 정확하다.** SDN 연결 표준(`adapters.sdn`)이
      "왜 못 붙는지" 를 값으로 들고 있기 때문이다 — 명세 미수령은 장애가 아니라
      **대기**이고, 화면은 그 둘을 다른 색으로 그려야 한다.

      스코프를 받지 않는다: 연계 상태는 테넌트별 사실이 아니라 **설비의 사실**이다.
    """
    if not sdn.is_ready():
        return LinkStateView(status=LinkStatus.WAITING,
                             reason=sdn.NOT_READY_REASON)
    try:
        alive = sdn.current().check_auth()
    except sdn.SdnUnavailable as exc:
        return LinkStateView(status=LinkStatus.DOWN, reason=str(exc))
    if not alive:
        return LinkStateView(status=LinkStatus.DOWN,
                             reason="SDN 인증이 통하지 않는다 (I-5)")
    return LinkStateView(status=LinkStatus.NORMAL, reason="")


@dataclass(frozen=True)
class DashboardFrame:
    """F-09 한 화면분. **AC-09 ①이 요구하는 것을 값으로 낸다.**

    AC-09 ①: *"화면 5상태(기본/로딩/빈/오류/권한없음)가 **전 위젯에 대해** 정의·구현된다."*

    ★ 검수에서 "5상태 100%" 를 물으면 **세지 않고 보여 준다** — `five_states` 가
      프레임이 정의한 다섯의 이름이고, `panels[].state` 가 각 칸의 실제 상태다.
      위젯마다 다시 세면 그 수는 언제나 100% 가 나온다 (D-249 부착률 착시).
    """

    preset: str
    preset_matched: bool
    panels: tuple[Any, ...]
    five_states: tuple[str, ...]
    link: LinkStateView
    #: 각 상태가 몇 칸인가. **분모를 함께 낸다** (D-271) — "정상 3칸" 만 보면
    #: 전체가 3칸인지 30칸인지 모른다.
    state_counts: dict[str, int] = field(default_factory=dict)


def dashboard_frame(*, scope: TenantScope, dashboard_code: str | None = None,
                    panel_source=None) -> DashboardFrame:
    """F-09 대시보드 프레임. **K3 가 만든 것을 옮길 뿐이다.**

    상태 판정(권한없음→오류→빈→기본)은 커널이 한다. 여기서 다시 하지 않는다 —
    두 벌을 두면 화면과 시험이 다른 말을 한다.
    """
    from kernels.k3_dashboard import FIVE_STATES, get_preset, resolve_layout

    preset = get_preset(scope=scope)
    panels = resolve_layout(scope=scope, preset=preset.preset,
                            dashboard_code=dashboard_code,
                            panel_source=panel_source)
    counts = {state: 0 for state in FIVE_STATES}
    for panel in panels:
        counts[panel.state.value] = counts.get(panel.state.value, 0) + 1
    return DashboardFrame(
        preset=preset.preset,
        preset_matched=preset.matched,
        panels=panels,
        five_states=FIVE_STATES,
        link=link_state(),
        state_counts=counts,
    )


def recent_events(*, scope: TenantScope, since: datetime | None = None,
                  event_type=None, severity=None, limit: int = 50):
    """F-09 이벤트 목록. K1 을 그대로 부른다 — 필터도 커널이 건다.

    ★ NFR-09-1 — 외부 의존(스트리밍 서버)이 죽어도 이 목록은 산다.
      여기서 스트리밍을 부르지 않는 것이 그 성질의 전부다.
    """
    from kernels.k1_event import query_events

    return query_events(scope=scope, since=since, event_type=event_type,
                        severity=severity, limit=limit)


# ═══════════════════════════════════════════════════════════════════════════
# F-10 알림 발송
# ═══════════════════════════════════════════════════════════════════════════
def notify_event(*, scope: TenantScope, event_id: int, channels=None):
    """이벤트 하나를 규칙대로 보낸다 (F-10).

    ★ **실패해도 예외를 올리지 않는다** — K2 가 그렇게 만들어져 있고(저하 운전),
      실패는 행으로 보인다(`succeeded=False` + `failure_reason`).
      App 이 여기서 예외로 바꾸면 "보낸 적 없음" 과 "보내려다 실패" 가 다시 뭉개진다.

    ★ 중복 억제(F-04 5분)도 K2 가 한다. `respect_suppression` 를 끄지 않는다 —
      끄는 것은 운영 판단이지 App 의 기본값이 아니다.
    """
    from kernels.k2_notify import send

    return send(scope=scope, event_id=event_id, channels=channels)


def delivery_history(*, scope: TenantScope, event_id: int | None = None,
                     since: datetime | None = None, until: datetime | None = None,
                     succeeded: bool | None = None, limit: int = 100, offset: int = 0):
    """F-10 발송 기록 조회 (FR-10-2: 대상·시각·채널·성공여부).

    이 목록이 곧 F-11 보고서의 "조치 이력" 이다 — 보고서용을 따로 만들지 않는다
    (DA-04 K2 이중 AC).
    """
    from kernels.k2_notify import list_deliveries

    return list_deliveries(scope=scope, event_id=event_id, since=since, until=until,
                           succeeded=succeeded, limit=limit, offset=offset)


# ═══════════════════════════════════════════════════════════════════════════
# F-11 상황 보고서
# ═══════════════════════════════════════════════════════════════════════════
def report_templates(*, scope: TenantScope):
    """F-11 템플릿 목록. K4 를 그대로 부른다."""
    from kernels.k4_report import list_templates

    return list_templates(scope=scope)


def build_report(*, scope: TenantScope, template_id: int,
                 event_id: int | None = None, mission_id: int | None = None,
                 since: datetime | None = None, until: datetime | None = None,
                 allow_incomplete: bool = False) -> bytes:
    """F-11 PDF 바이트 (AC-11: 기재 항목이 원본 이벤트와 일치).

    ★ `allow_incomplete` 의 기본값을 **바꾸지 않는다.** 출처가 실패했는데 그대로 찍으면
      "조치 없음" 보고서가 고객에게 나가고, 종이는 되돌릴 수 없다 (K4 가 정한 규칙).
      App 이 편의로 True 를 기본에 두면 그 규칙이 App 한 줄로 무력해진다.
    """
    from kernels.k4_report import build_context, render

    context = build_context(scope=scope, event_id=event_id, mission_id=mission_id,
                            since=since, until=until)
    return render(scope=scope, template_id=template_id, context=context,
                  allow_incomplete=allow_incomplete)


# ═══════════════════════════════════════════════════════════════════════════
# F-12 관리자 설정 — **무권한 차단 + 감사로그 전건** (AC-12)
# ═══════════════════════════════════════════════════════════════════════════
#: F-12 가 계약상 한 곳에서 관리해야 하는 다섯 (FR-12-1).
#: 값은 "지금 이것을 다룰 수 있는가" 다. **셋은 표가 없다** — 실측이고, 추측으로
#: 만들지 않는다(D-280). 여기 이름을 적어 두는 이유는 빠진 줄이 보이게 하기 위해서다.
SETTING_DOMAINS: dict[str, str] = {
    "recipients": "",   # 다룰 수 있다 — NotificationRule 실재, K2 가 읽는다
    "widgets": "",      # 다룰 수 있다 — K3 widget_permission
    "zones": "위험구역을 저장할 표가 없다. `NotificationRule.zone` 은 체계가 아니라 "
             "**라벨**이고, 행정구역인지 카메라 묶음인지 폴리곤인지가 미정이다 "
             "(P-K2-2). 체계를 여기서 정하면 그 추측이 곧 계약이 된다",
    "thresholds": "지점별 수위·임계값을 저장할 표가 없다(FR-02-2 가 요구하는 것). "
                  "지금 임의값을 두면 그 값이 곧 F-02 의 AC 판정 근거가 된다",
    "grade_rules": "등급규칙(F-04 JSON 규칙엔진)을 저장할 표가 없다. "
                   "`detection_event_bridge.EVENT_TYPE_TO_SEVERITY` 는 배선의 "
                   "**잠정 사전**이지 사용자가 고치는 설정이 아니다 (P-W2-2-1)",
    "api_keys": "API Key 발급·폐기(FR-05-3)의 저장처가 없다. 키 값은 저장소 밖이고"
                "(D-204), 발급 이력을 어디에 두는가는 W4 계측 모델과 함께 정해진다",
}


@dataclass(frozen=True)
class SettingAccess:
    """설정 접근 판정 하나. **감사 행 번호를 함께 낸다** — 남았다는 증거다."""

    allowed: bool
    reason: str
    audit_id: int


def _decide(actor) -> tuple[bool, str]:
    """설정을 만질 수 있는가. **판정식을 복사하지 않는다** (FR-12-3 · D-212).

    `common/tenant_roles.py` 한 곳만 부른다. 판정식 복사본 하나가 우회 지점 하나이고,
    실제로 그 복사본이 이 저장소 격리 사고의 원인이었다.
    """
    if is_global_admin(actor):
        return True, "전역 관리 역할"
    if is_tenant_admin(actor):
        return True, "테넌트 운영 역할"
    return False, "설정 변경 권한이 없는 계정"


def guard_setting(*, scope: TenantScope, action: str,
                  api_method: str = "") -> SettingAccess:
    """F-12 문지기. **막든 통과시키든 감사에 남긴다** (AC-12).

    순서가 중요하다 — **감사를 먼저 남기고 그 결과를 돌려준다.** 통과시킨 뒤에
    남기면 그 사이에 죽은 요청이 감사에서 사라지고, 사라진 것은 감사가 아니다.

    감사 쓰기가 실패하면 예외가 그대로 올라간다 — **삼키지 않는다.**
    감사에 남길 수 없으면 그 설정 변경은 일어나지 않는 것이 옳다.
    """
    actor = scope.require_actor()
    allowed, why = _decide(actor)
    entry = audit.record(
        scope=scope, action=action,
        outcome=audit.ALLOWED if allowed else audit.DENIED,
        reason=why, api_name=action, api_method=api_method,
        status_http=200 if allowed else 403,
    )
    return SettingAccess(allowed=allowed, reason=why, audit_id=entry.audit_id)


def setting_overview(*, scope: TenantScope, domain: str) -> dict[str, Any]:
    """F-12 설정 한 영역을 읽는다. **무권한이면 차단되고 그 사실이 남는다.**

    다룰 수 없는 영역은 `SettingNotAvailable` 로 멈춘다 — 빈 목록을 돌려주면
    화면이 "설정이 없습니다" 를 그리고, 사용자는 **기능이 있는데 비어 있다**고 읽는다.
    """
    if domain not in SETTING_DOMAINS:
        raise SettingNotAvailable(
            f"domain={domain!r} 은 F-12 의 설정 영역이 아니다. "
            f"허용: {', '.join(SETTING_DOMAINS)}")

    access = guard_setting(scope=scope, action=f"read:{domain}", api_method="GET")
    if not access.allowed:
        raise PermissionDeniedForSetting(access.reason, audit_id=access.audit_id)

    blocker = SETTING_DOMAINS[domain]
    if blocker:
        raise SettingNotAvailable(
            f"F-12 의 '{domain}' 설정은 아직 다룰 수 없다 — {blocker}. "
            f"빈 목록을 돌려주지 않는다: 없는 것과 비어 있는 것은 다르다 (D-284 · D-290)")

    if domain == "widgets":
        from kernels.k3_dashboard import SETTING_WIDGETS, widget_permission

        return {"widgets": {w: widget_permission(w, scope=scope).name
                            for w in SETTING_WIDGETS}}

    # domain == "recipients"
    from kernels.k2_notify import resolve_recipients

    severities = ("info", "warning", "critical")
    return {"recipients": {
        s: [r.user_id for r in resolve_recipients(scope=scope, severity=s)]
        for s in severities}}
