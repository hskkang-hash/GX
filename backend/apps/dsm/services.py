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
                  until: datetime | None = None,
                  event_type=None, severity=None, response_state=None,
                  reviewed_by_id: int | None = None,
                  limit: int = 50):
    """F-09 이벤트 목록. K1 을 그대로 부른다 — 필터도 커널이 건다.

    ★ NFR-09-1 — 외부 의존(스트리밍 서버)이 죽어도 이 목록은 산다.
      여기서 스트리밍을 부르지 않는 것이 그 성질의 전부다.

    ★ 2026-09-23 (차선 C · W1 프리셋 4종) — `until` 과 `reviewed_by_id` 가 더해졌다.
      **App 은 여기서 아무것도 거르지 않는다.** 인자를 커널로 넘기기만 한다 —
      App 이 한 줄이라도 거르기 시작하면 필터가 두 층에 생기고, 두 층은 어긋난다.
    """
    from kernels.k1_event import query_events

    return query_events(scope=scope, since=since, until=until,
                        event_type=event_type,
                        severity=severity, response_state=response_state,
                        reviewed_by_id=reviewed_by_id,
                        limit=limit)


def event_detail(*, scope: TenantScope, event_id: int):
    """이벤트 하나 (F-09 상세 화면 · D-371 ⑤).

    ★ 목록을 받아 화면에서 골라내지 않는다. 골라내면 **문지기가 목록에만 서고
      상세에는 안 서는** 모양이 되고, 그 자리가 IDOR 이 태어나는 자리다.
      좁히기는 커널의 `get_event` 가 한다 — App 은 소비만 한다.
    """
    from kernels.k1_event import get_event

    return get_event(event_id, scope=scope)


# ═══════════════════════════════════════════════════════════════════════════
# 스냅샷 바이트 — P-25 (2026-09-24)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 판정(지시서 §1 P-25): 프리사인드 URL 은 **무계정 링크**라 만들지 않는 것이 옳았다.
#   대신 **인증 필수 바이트 라우트 1개**를 낸다. 스냅샷은 11조가 말하는 원본 영상이
#   아니라 정지 이미지 1장이고(DA-01 FR-01-3), 화면이 이미 그리고 있는 것이다.
#
#   저장은 못 막는다. **그래서 출처를 남긴다** — 테넌트명과 열람 시각을 소인으로 찍는다.


class SnapshotUnavailable(RuntimeError):
    """스냅샷 바이트를 지금 줄 수 없다. **사유가 함께 온다** — 빈 응답을 만들지 않는다.

    Attributes:
        kind: `missing`(이 이벤트에 프레임이 없다) / `storage`(저장소가 죽었다) /
              `stamp`(소인을 못 찍었다 — 우리 결함). 라우트가 이 셋을 **다른 상태 코드**로
              번역한다: 404 · 503 · 500. 하나로 뭉치면 「없다」와 「지금 안 된다」가
              같은 답이 되고, 운영자는 어느 쪽을 고쳐야 하는지 모른다.
    """

    def __init__(self, kind: str, reason: str):
        super().__init__(reason)
        self.kind = kind
        self.reason = reason


def _watermark_text(*, actor, event_id: int, occurred_at) -> str:
    """소인 문구 — **테넌트명과 시각**. 둘 중 하나라도 없으면 소인의 뜻이 없다."""
    from django.utils import timezone

    from common.tenant_filters import get_user_group

    group = get_user_group(actor)
    tenant = (getattr(group, "name", "") or getattr(group, "code", "")
              or "(소속 미상)")
    viewed = timezone.localtime().strftime("%Y-%m-%d %H:%M")
    when = occurred_at.strftime("%Y-%m-%d %H:%M") if occurred_at else "시각 미상"
    return f"GuardianX · {tenant} · 이벤트 {event_id} ({when}) · 열람 {viewed}"


def event_snapshot(*, scope: TenantScope, event_id: int) -> bytes:
    """이벤트 스냅샷 1장의 **소인 찍힌** 바이트 (P-25).

    좁히기는 `event_detail` 이 부르는 커널이 한다 — 남의 테넌트 이벤트는 **404** 다.
    여기서 다시 필터를 짜지 않는다: 두 벌을 두면 어긋나고, 어긋난 쪽이 조용히 이긴다.

    Raises:
        SnapshotUnavailable: 프레임이 없거나(`missing`) · 저장소가 죽었거나(`storage`) ·
            소인을 못 찍었을 때(`stamp`).
    """
    from stream_monitors.services.detection_snapshot import fetch_snapshot

    from apps.dsm.watermark import stamp

    view = event_detail(scope=scope, event_id=event_id)
    path = (getattr(view, "snapshot_path", "") or "").strip()
    if not path:
        raise SnapshotUnavailable(
            "missing", "이 이벤트에는 저장된 스냅샷이 없습니다.")

    data, reason = fetch_snapshot(path)
    if not data:
        # ★ 「경로는 있는데 객체가 없다」는 **저장소 쪽 사실**이다. 우리 결함(500)으로
        #   올리지 않는다 — 고칠 자리가 다르다.
        kind = "missing" if "0바이트" in reason or "경로" in reason else "storage"
        raise SnapshotUnavailable(kind, reason)

    try:
        return stamp(data, _watermark_text(
            actor=scope.require_actor(), event_id=event_id,
            occurred_at=getattr(view, "occurred_at", None)))
    except Exception as exc:  # noqa: BLE001
        # 소인을 못 찍으면 **원본을 그대로 내보내지 않는다.** 소인 없는 바이트가
        # 나가는 순간 P-25 가 준 것은 라우트뿐이고 출처는 없다.
        raise SnapshotUnavailable(
            "stamp", f"소인을 찍지 못해 스냅샷을 내보내지 않습니다 — "
                     f"{type(exc).__name__}: {exc}") from exc


# ═══════════════════════════════════════════════════════════════════════════
# 대응 진행 축 (D-399)
# ═══════════════════════════════════════════════════════════════════════════
#: ★ 커널 예외를 **여기서 다시 내보낸다.** `api.py` 가 직접 `kernels.k1_event` 를
#:   쓰면 `test_f05_event_api` 가 멈춘다 — 「K1 의 App 소비자는 **하나뿐**」이 F-05
#:   「진입면 하나」의 실제 집행이고, 그 하나가 이 파일이다.
#:   ⚠ 클래스를 **다시 정의하지 않고 그대로 내보낸다.** 새로 정의하면 커널이 던진
#:     것과 App 이 잡는 것이 다른 클래스가 되어 `except` 가 조용히 안 걸린다.
from kernels.k1_event import (  # noqa: E402  (재수출 — 위 규약 때문에 여기 있다)
    InvalidEventInput,
    ResponseTransitionError,
    ResponseTransitionForbidden,
    ResponseTransitionNeedsManager,
    ResponseTransitionNeedsReason,
)

__all_response_errors__ = (
    "ResponseTransitionError", "ResponseTransitionForbidden",
    "ResponseTransitionNeedsManager", "ResponseTransitionNeedsReason",
    # ★ P-16 — 판정값이 아닌 값은 **422** 로 나간다. `api.py` 가 이 이름으로 잡는다.
    "InvalidEventInput",
)
def advance_response(*, scope: TenantScope, event_id: int, to_state: str,
                     reason: str = ""):
    """대응 진행을 한 칸 옮긴다 (D-399).

    ★ **App 은 규칙을 들지 않는다.** 전이표·되돌림 권한·감사는 전부 K1 에 있다 —
      1차판은 이것을 App 에 두었고 `AppStaysThinTest` 가 즉시 빨개졌다. 옳은 지적이다:
      `DetectionEvent` 의 수명주기는 K1 의 것이고 `review_event`·`close_event` 가
      이미 거기 산다. 흩어 두면 같은 표의 규칙이 두 층에 나뉜다.
    """
    from kernels.k1_event import advance_response as _advance

    return _advance(event_id, to_state=to_state, reason=reason, scope=scope)


def field_reply(*, scope: TenantScope, event_id: int, text: str):
    """현장이 돌려주는 한 줄 (U3 #9 · 차선 D).

    ★ **App 은 규칙을 들지 않는다.** 문지기(`get_event` 404)·길이 검증·감사 기록은
      전부 커널에 있다. 여기서 다시 하면 두 벌이 되고, 두 벌은 반드시 갈린다.
    """
    from kernels.k1_event import reply_from_field

    return reply_from_field(scope=scope, event_id=event_id, text=text)


def field_replies(*, scope: TenantScope, event_id: int, limit: int = 50):
    """한 이벤트의 현장 회신들.

    ★ 좁히기는 커널이 한다 — 감사 표에는 테넌트 칸이 없어서 `list_field_replies` 가
      **이벤트 문지기를 먼저 지난 뒤** 번호로 뽑는다. 순서가 뜻이다.
    """
    from kernels.k1_event import list_field_replies

    return list_field_replies(scope=scope, event_id=event_id, limit=limit)


def response_state(*, scope: TenantScope, event_id: int):
    """지금 어디까지 왔나 + 갈 수 있는 곳 (D-399). 상세 화면이 부른다."""
    from kernels.k1_event import response_state as _state

    return _state(event_id, scope=scope)


# ═══════════════════════════════════════════════════════════════════════════
# 판정 축 — 오탐/정탐 (P-16 · 오탐 ②)
# ═══════════════════════════════════════════════════════════════════════════
def review_event(*, scope: TenantScope, event_id: int, verdict: str,
                 reason: str = ""):
    """이 탐지가 진짜인가를 사람이 판정한다 (F-14 오탐률의 입력).

    ★ 이 함수는 **2026-08 부터 커널에 있었고 문이 없었다.** 화면의 「오탐」 버튼이
      부를 자리가 없어 U1 의 오탐률은 시드로만 채워졌다 — 착시 ⑨(함수는 문이 아니다).
      P-16 에서 문을 세운다.

    ★ **App 은 규칙을 들지 않는다.** 판정값 검증·감사·오탐 결합은 전부 커널에 있다.
      결합(→ 대응 축 종결)은 이 호출의 **부작용이 아니라 소비자의 일**이다 —
      `stream_monitors/services/` 의 오탐 결합 소비자 한 곳에만 산다.
      (그 모듈 이름을 여기 적지 않는다: `AppStaysThinTest` 가 이 파일에서 오탐 관련
       영문 낱말을 **App 이 오탐률을 다시 세는 냄새**로 읽는다. 그 판정이 옳다 —
       이름을 적고 싶어 시험을 넓히는 것이 시험을 고쳐 초록을 만드는 일이다 · D-327)
    """
    from kernels.k1_event import review_event as _review

    return _review(event_id, verdict=verdict, reason=reason, scope=scope)


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
                     succeeded: bool | None = None, mine: bool = False,
                     limit: int = 100, offset: int = 0):
    """F-10 발송 기록 조회 (FR-10-2: 대상·시각·채널·성공여부).

    이 목록이 곧 F-11 보고서의 "조치 이력" 이다 — 보고서용을 따로 만들지 않는다
    (DA-04 K2 이중 AC).

    ★ `mine` — **「내게 온 것」을 서버가 거른다** (차선 D · 2026-09-04).
      직전까지 커널에는 `recipient_id` 가 있는데 이 함수가 안 넘겨서, 모바일 M1 이
      「내게 온 이벤트」를 **서버에게 물어볼 수 없었다.** 화면이 대신 거르면
      **페이지 밖 발송이 없는 것**이 된다 — W1 프리셋에서 이미 같은 이유로 서버 필터를
      골랐다(P-13).

    ★ 그리고 **좁히는 값은 서버가 정한다.** 요청은 「나」라고만 말한다 —
      `recipient_id=<숫자>` 를 질의로 받으면 남의 사번으로 「그 사람에게 무엇이 갔나」를
      물을 수 있고, 이 라우트의 사유(「수신자 주소가 새면 안 된다」)가 그것을 이미
      금지하고 있다. `/events` 의 `mine` 과 같은 규약이다.
    """
    from kernels.k2_notify import list_deliveries

    recipient_id = getattr(scope.require_actor(), "pk", None) if mine else None
    return list_deliveries(scope=scope, event_id=event_id, since=since, until=until,
                           recipient_id=recipient_id, succeeded=succeeded,
                           limit=limit, offset=offset)


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
    # ★ 2026-09-10 열렸다 — D-366. 「저장할 표가 없다」가 아니게 됐다.
    #   막고 있던 것은 표가 아니라 **체계**였다: 행정구역인지 카메라 묶음인지 폴리곤인지.
    #   D-365 가 그 셋 중 둘(카메라 묶음·폴리곤)을 고르고 좌표계까지 못박았으므로
    #   이 사유는 해소됐다. 남은 하나(행정구역)는 **안 만든다** — 계약 F-03 이
    #   부르는 것은 "지정 위험구역" 이고 행정구역 경계는 그 질문이 아니다(D-280).
    "zones": "",
    # ★ 2026-09-06 열렸다 — K5 표 ① (D-325). 「저장할 표가 없다」가 아니게 됐다.
    #   임의값을 두지 않은 것이 요점이다: F-02 의 지점별 수위 기준선은 여전히 **값이 없고**,
    #   없으면 `ThresholdNotSet` 으로 멈춘다. 표가 생겼다고 숫자가 생긴 것이 아니다(D-280).
    "thresholds": "",
    # ★ 2026-09-10 열렸다 — 표 ③ (D-368). 「저장할 표가 없다」가 아니게 됐다.
    #   잠정 사전은 그대로 남는다 — 그것이 **정의**이고 표는 **덮어쓴 값**이다.
    #   표 ①이 임계값에 쓴 그 구조를 그대로 쓴다: 정의는 개발이, 값은 운영이 정한다.
    "grade_rules": "",
    # ★ 2026-09-06 열렸다 — K5 표 ② (D-325 · D-328). 저장처가 생겼다.
    #   **값은 여전히 저장소 밖이다**(D-204 · D-319) — 표가 갖는 것은 값이 아니라
    #   「있는가 · 무엇인가」의 사실이고, 조회는 언제나 마스킹된다.
    "api_keys": "",
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


def set_threshold_value(*, scope: TenantScope, key: str, value: float, reason: str,
                        scope_level: str = "global",
                        scope_ref: int | None = None) -> dict[str, Any]:
    """F-12 「임계값」 쓰기 — **F-02 「지점별 기준선 설정」이 실제로 설정되는 자리**.

    App 은 문지기 노릇만 한다. 값 판정(계약 고정인가 · 범위가 맞는가)과 내력 기록은
    **커널이** 한다 — 여기서 다시 판정하면 두 벌이 되고, 두 벌은 반드시 어긋난다(D-212).
    """
    from kernels.k5_trust import set_threshold

    access = guard_setting(scope=scope, action=f"write:thresholds:{key}",
                           api_method="POST")
    if not access.allowed:
        raise PermissionDeniedForSetting(access.reason, audit_id=access.audit_id)
    return set_threshold(scope=scope, key=key, value=value, reason=reason,
                         scope_level=scope_level, scope_ref=scope_ref)


def save_zone_setting(*, scope: TenantScope, name: str, kind: str,
                      zone_id: int | None = None, geometry=None,
                      camera_ids: list[int] | None = None,
                      is_active: bool = True) -> dict[str, Any]:
    """F-12 「구역」 쓰기 — **위험구역이 실제로 지정되는 자리** (D-366).

    App 은 문지기 노릇만 한다. 도형 검증·소유 상속·테넌트 좁히기는 **L3 이** 한다 —
    여기서 다시 하면 두 벌이 되고, 두 벌은 반드시 어긋난다(D-212).

    ★ 무권한 차단도 **성공도** 감사에 남는다(AC-12). 구역 지정은 "어디를 위험하다고
      볼 것인가" 를 바꾸는 일이라, 누가 언제 바꿨는지가 사고 뒤에 반드시 필요하다.
    """
    from stream_monitors.services.zones import save_zone

    action = f"write:zones:{zone_id if zone_id is not None else 'new'}"
    access = guard_setting(scope=scope, action=action, api_method="POST")
    if not access.allowed:
        raise PermissionDeniedForSetting(access.reason, audit_id=access.audit_id)

    zone = save_zone(scope=scope, zone_id=zone_id, name=name, kind=kind,
                     geometry=geometry, camera_ids=camera_ids, is_active=is_active)
    return {"zone_id": zone.pk, "name": zone.name, "kind": zone.kind,
            "geometry_status": zone.geometry_status, "is_active": zone.is_active,
            "audit_id": access.audit_id}


def issue_inbound_key(*, scope: TenantScope, name: str,
                      expires_days: int | None = None) -> dict[str, Any]:
    """F-05 「API Key 발급」 · F-12 「API키」 — **키가 실제로 발급되는 자리** (D-367).

    ★ 응답에 `secret` 이 실리는 **유일한 자리**다. 저장소는 원문을 갖지 않으므로
      이 응답을 놓치면 되찾을 수 없고 회전만 가능하다. 그것이 옳은 성질이다.
    ★ 감사에는 **키 값을 적지 않는다** — `audit_id` 와 이름·prefix 만 남는다(D-335 규약 ④).
    """
    # ★ **공개 면에서만** 가져온다 (DA-04 §1-4). 비공개 모듈을 직접 가져오면
    #   `verify_layers.py` 가 멈춘다 — 커널 로직이 App 으로 새는 것이
    #   계약 8조3항 경계의 소멸이기 때문이다.
    from kernels.k5_trust import DEFAULT_EXPIRES_DAYS, issue_key

    access = guard_setting(scope=scope, action=f"write:inbound_api_key:issue:{name}",
                           api_method="POST")
    if not access.allowed:
        raise PermissionDeniedForSetting(access.reason, audit_id=access.audit_id)

    issued = issue_key(scope=scope, name=name,
                       expires_days=DEFAULT_EXPIRES_DAYS if expires_days is None
                       else expires_days)
    return {**_key_payload(issued.view), "secret": issued.secret,
            "audit_id": access.audit_id}


def revoke_inbound_key(*, scope: TenantScope, key_id: int) -> dict[str, Any]:
    """F-05 「API Key 폐기」 — 행을 지우지 않고 **꺼진 상태로 남긴다**.

    지우면 "그 키가 언제까지 살아 있었나" 가 사라진다. 사고 조사에 필요한 것은
    "지금 없다" 가 아니라 **"언제부터 없었나"** 다.
    """
    from kernels.k5_trust import revoke_key

    access = guard_setting(scope=scope, action=f"write:inbound_api_key:revoke:{key_id}",
                           api_method="POST")
    if not access.allowed:
        raise PermissionDeniedForSetting(access.reason, audit_id=access.audit_id)
    return {**_key_payload(revoke_key(scope=scope, key_id=key_id)),
            "audit_id": access.audit_id}


def rotate_inbound_key(*, scope: TenantScope, key_id: int) -> dict[str, Any]:
    """폐기 + 발급을 **한 동작으로.** 둘로 나누면 한쪽을 잊는다."""
    from kernels.k5_trust import rotate_key

    access = guard_setting(scope=scope, action=f"write:inbound_api_key:rotate:{key_id}",
                           api_method="POST")
    if not access.allowed:
        raise PermissionDeniedForSetting(access.reason, audit_id=access.audit_id)
    issued = rotate_key(scope=scope, key_id=key_id)
    return {**_key_payload(issued.view), "secret": issued.secret,
            "rotated_from": key_id, "audit_id": access.audit_id}


def _key_payload(view) -> dict[str, Any]:
    """키 하나의 응답 모양. **값 칸이 없다** — 여기에 칸을 만들면 언젠가 채워진다."""
    return {"key_id": view.key_id, "name": view.name, "prefix": view.prefix,
            "api_type": view.api_type, "capability": view.capability,
            "status": view.status, "is_active": view.is_active,
            "expires_at": view.expires_at}


def set_grade_rule_value(*, scope: TenantScope, event_type: str, severity: str,
                         reason: str) -> dict[str, Any]:
    """F-12 「등급규칙」 쓰기 — **F-04 「JSON 무재기동 반영」이 실제로 반영되는 자리** (D-368).

    App 은 문지기 노릇만 한다. 열거 검사·이력 기록은 **커널이** 한다 —
    여기서 다시 판정하면 두 벌이 되고, 두 벌은 반드시 어긋난다(D-212).

    ★ 하향이면 `lowered=True` 가 응답에 실린다. 막지 않되 **조용히 지나가지도 않는다** —
      `fire → info` 는 화재를 조용하게 만드는 변경이고, 경보가 안 오는 것은
      「아무 일도 없음」으로 보인다.
    """
    from kernels.k5_trust import set_grade_rule

    access = guard_setting(scope=scope, action=f"write:grade_rules:{event_type}",
                           api_method="POST")
    if not access.allowed:
        raise PermissionDeniedForSetting(access.reason, audit_id=access.audit_id)

    view = set_grade_rule(scope=scope, event_type=event_type, severity=severity,
                          reason=reason)
    return {"event_type": view.event_type, "severity": view.severity,
            "default_severity": view.default_severity, "lowered": view.lowered,
            "reason": view.reason, "audit_id": access.audit_id}


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

    if domain == "thresholds":
        # ★ K5 표 ①. **커널 서비스 함수만 부른다** — 모델을 직접 만지지 않는다(DA-04 §1-4).
        from kernels.k5_trust import list_thresholds, threshold_history

        return {"thresholds": list(list_thresholds(scope=scope)),
                "history": list(threshold_history(scope=scope, limit=20))}

    if domain == "api_keys":
        # ★ **두 방향을 나란히 낸다** (D-367). 한 칸에 뭉치면 D-337 이 잡은 혼동이
        #   화면 안으로 들어온다 — 「우리가 남을 부를 때 쓰는 키」와 「남이 우리를
        #   부를 때 쓰는 키」는 관리 주체도 폐기 절차도 다르다.
        #   값은 어느 쪽도 나오지 않는다 — 마스킹된 **사실**만 나온다(D-204 · D-319).
        from kernels.k5_trust import inbound_key_facts, list_credentials

        _facts = inbound_key_facts(scope=scope)
        return {
            #: 나가는 키 — 표 ②(환경변수 선언). 우리가 남의 API 를 부를 때 쓴다
            "outbound": list(list_credentials(scope=scope)),
            #: 들어오는 키 — 남의 App 이 우리 이벤트 OpenAPI 를 부를 때 쓴다
            "inbound": [
                {"key_id": k.key_id, "name": k.name, "prefix": k.prefix,
                 "status": k.status, "is_active": k.is_active,
                 "created_at": k.created_at, "last_used": k.last_used,
                 "expires_at": k.expires_at}
                for k in _facts["keys"]],
            "inbound_api_type": _facts["api_type"],
            "inbound_capability": _facts["capability"],
            #: ★ 옛 키(단일 목록)를 쓰던 화면을 위해 남긴다. **표 ②만 들어 있다** —
            #:   두 방향을 여기에 합치면 옛 화면이 들어오는 키를 나가는 키로 읽는다.
            "api_keys": list(list_credentials(scope=scope)),
        }

    if domain == "grade_rules":
        # ★ 표 ③. 정의 전건 + 덮어쓴 값. **덮어쓴 것만 내지 않는다** —
        #   그러면 화면이 "규칙 2개" 를 그리고 나머지가 규칙 없이 도는 것처럼 읽힌다.
        from kernels.k5_trust import grade_rule_history, list_grade_rules

        rules = list_grade_rules(scope=scope)
        return {
            "grade_rules": [
                {"event_type": r.event_type, "severity": r.severity,
                 "default_severity": r.default_severity, "overridden": r.overridden,
                 "reason": r.reason, "lowered": r.lowered}
                for r in rules],
            #: ★ **낮춘 것의 수를 따로 낸다.** 낮춘 규칙은 경보를 끈 것이고,
            #:   목록 안에 섞여 있으면 화면에서 눈에 안 띈다 (D-301 건수 출력).
            "lowered_count": sum(1 for r in rules if r.lowered),
            "history": list(grade_rule_history(scope=scope, limit=20)),
        }

    if domain == "zones":
        # ★ L3 의 구역 서비스만 부른다 — Zone 모델을 App 이 직접 만지지 않는다(DA-04 §1-4).
        from stream_monitors.services.zones import ZONE_CRS, list_zones

        return {"zones": list_zones(scope=scope), "crs": ZONE_CRS}

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
