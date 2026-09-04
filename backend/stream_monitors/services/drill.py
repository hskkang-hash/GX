# -*- coding: utf-8 -*-
"""훈련 모드 스위치 — **끄는 스위치다** (UX-17 · 차선 C · 2026-09-24).

한 문장
-------
    켜면 그 테넌트의 알림이 **사람에게 가지 않는다.** 그러므로 이 스위치는
    다른 어떤 쓰기보다 조용하게 사고를 만든다 — 남이 켜면 남의 진짜 경보가
    로그로 흘러 아무에게도 안 간다.

왜 표를 만들지 않았나 — **스위치는 사건이지 상태가 아니다**
-----------------------------------------------------------
`drill_mode` 를 `Group` 이나 새 표의 boolean 한 칸으로 두면 다음 질문에 아무도 못 답한다:
**언제부터 언제까지 훈련이었나 · 누가 켰나 · 왜 켰나.** 그 넷이 없으면 훈련 종료
보고서를 쓸 수 없고, 사후에 「그 시각의 미발송은 훈련 때문이었나 장애였나」를 가를 수도
없다. 그 구별이 이 기능의 값 전부다.

그래서 **감사 한 줄이 정본이다** — `logger.AuditLogs`, `logger_name` 은 아래 `LOGGER_NAME`.
`common/audit_writer.py` 하나로 쓴다. 새 표를 만들지 않는다(D-333) · 새 쓰는 손을
만들지 않는다(D-325 표 ②). 지금 켜져 있는가는 **그 테넌트의 마지막 줄**이 답한다.

그래서 훈련 이벤트는 어떻게 표시되나 — **창(window)이 표시다**
--------------------------------------------------------------
지시서는 「이벤트는 `data_source=drill`」이라 적었다. 착수 전 실측 [2026-09-24]:

    `DetectionEvent` 에 `data_source` 칸은 **없다.** 이 저장소에서 `data_source` 는
    **화면 메타**다 — `scripts/verify_screens.py :: META_FIELDS` 의 다섯째 칸이고
    (D-347), 시드는 그것을 화면에 글자로 찍는다(`seed_dsm_events.py:403`).

칸을 새로 만들지 않는 이유는 위와 같다: 새 칸은 태어나는 순간 **과거가 비어 있고**,
빈 과거는 「전부 실사건이었다」로 읽힌다. 대신 **훈련 창에 속하는가**로 판정한다
(`is_drill_event(occurred_at, group_id)`). 창은 감사에 있고 과거도 함께 온다.
화면과 보고서는 그 판정을 받아 `data_source=drill` 이라 적는다 — 판정은 여기 한 곳.

⚠ 이 파일이 하지 않는 것 — **채널을 바꾸지 않는다**
---------------------------------------------------
실제 채널 우회는 `kernels/k2_notify/` 안에서 일어나야 한다(발송 경로는 하나다).
그 파일은 **조율자의 것**이고 이 차선은 만지지 않는다. 이 파일은 K2 가 물어볼
질문 하나(`is_drill_mode`)를 답할 수 있게 세워 두고 멈춘다.
필요한 배선은 보고서에 정확히 적었다 — `k2_notify/services.py` 의 `_deliver` 안,
`channel_registry.get(recipient.channel)` **앞** 한 자리다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.apps import apps
from django.core.exceptions import PermissionDenied

from common import audit_writer
from common.tenant_filters import get_user_group
from common.tenant_roles import is_global_admin
from common.tenant_scope import TenantScope

log = logging.getLogger(__name__)

#: 훈련 스위치 감사의 `logger_name`. **이 이름으로 전건을 뽑는다** (D-285 ②).
LOGGER_NAME = "guardianx.dsm.drill"
TAG = "[DRILL]"

#: 켜고 끄는 두 행위. 값이 둘뿐인 것이 요점이다 — 「일시정지」 같은 셋째를 만들면
#: 「지금 훈련인가」가 두 값으로 답할 수 없게 된다.
ON = "drill.on"
OFF = "drill.off"

#: 훈련 중에 알림이 가는 곳. `kernels/k2_notify/channels.LogChannel.name` 과 **같은 글자**다.
#: 두 벌인 것은 알고 있다 — 갈라지는 것은 `tests/test_c_drill_mode.py` 가 본다.
#: (import 하지 않는 이유: 이 파일이 커널을 끌어오면 스위치가 발송 경로에 얽힌다.
#:  스위치는 발송을 **모른 채** 서 있어야 하고, 아는 쪽은 K2 여야 한다.)
DRILL_CHANNEL = "log"

#: 화면·보고서가 적는 출처 이름 (D-347 `verify_screens` 다섯째 칸).
DATA_SOURCE = "drill"


@dataclass(frozen=True)
class DrillState:
    """지금 훈련인가 — 그리고 **언제부터 · 누가 · 왜.**

    `enabled=False` 일 때 `since` 가 있는 것은 「마지막 훈련이 끝난 시각」이 아니라
    **켠 적이 없다는 것과 껐다는 것을 가르기 위한 값**이다(D-290). `last_action` 이
    비어 있으면 이 테넌트는 훈련 모드를 **한 번도 켜 본 적이 없다.**
    """

    group_id: int | None
    enabled: bool
    since: datetime | None = None
    by: str = ""
    reason: str = ""
    last_action: str = ""

    def as_dict(self) -> dict:
        return {
            "group_id": self.group_id,
            "drill_mode": self.enabled,
            "since": self.since,
            "by": self.by,
            "reason": self.reason,
            "last_action": self.last_action,
            "channel_while_drilling": DRILL_CHANNEL,
            "data_source": DATA_SOURCE if self.enabled else "live",
        }


def _audit_model():
    return apps.get_model("logger", "AuditLogs")


def _as_mapping(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        import json
        try:
            parsed = json.loads(value)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _target_group(scope: TenantScope, group_id: int | None):
    """**문지기.** 남의 테넌트를 훈련 모드로 바꿀 수 없다.

    ★ 이 함수가 P-8 탐침이 재는 자리다. 여기가 열려 있으면 남의 진짜 경보가
      로그로 흘러 **아무에게도 안 간다** — 읽기 격리가 온전해도 이것은 격리 실패다.

    ★ 시스템 스코프를 **거절한다.** 훈련을 켜는 것은 사람이 하는 일이고, 사람이 없는
      호출이 켤 수 있으면 「누가 켰나」가 영원히 비어 있다 (D-281 · P-16 과 같은 판단).
    """
    actor = scope.require_actor()
    own = get_user_group(actor)
    if own is None and not is_global_admin(actor):
        raise PermissionDenied(
            "소속 테넌트가 없는 요청자는 훈련 모드를 켤 수 없습니다 — 어느 테넌트의 "
            "알림을 끄는지 정할 수 없기 때문입니다 (W0-12).")
    own_id = getattr(own, "pk", None)
    if group_id is None or group_id == own_id:
        return own_id
    if is_global_admin(actor):
        return group_id
    raise PermissionDenied(
        f"group={group_id} 는 요청자의 테넌트가 아닙니다. 훈련 모드는 **끄는 스위치**라 "
        f"남의 테넌트에 켜면 그쪽 진짜 경보가 아무에게도 가지 않습니다.")


def set_drill_mode(*, scope: TenantScope, enabled: bool, reason: str,
                   group_id: int | None = None) -> dict:
    """훈련 모드를 켜거나 끈다. **사유 필수.**

    왜 사유가 필수인가: 이 스위치는 알림을 끈다. 사후에 「그 시각에 왜 안 갔나」를 묻는
    사람이 반드시 생기고, 그때 답이 없으면 그것은 장애와 구별되지 않는다.

    ★ **감사가 먼저다.** 감사에 남길 수 없으면 스위치는 안 움직이는 것이 옳다 —
      스위치의 정본이 감사이므로, 여기서는 그것이 곧 「안 움직인다」이기도 하다.

    ★ **두 번 켜도 한 번만 적힌다.** 같은 사실을 두 줄로 적으면 「언제부터 훈련인가」가
      마지막 줄로 밀려 훈련 창이 조용히 짧아진다.
    """
    if not (reason or "").strip():
        raise ValueError(
            "훈련 모드 전환에는 사유가 필요합니다. 사유 없는 전환은 「알림이 왜 안 갔나」에 "
            "답하지 못하고, 답하지 못하는 미발송은 장애와 구별되지 않습니다.")

    target = _target_group(scope, group_id)
    current = drill_state(scope=scope, group_id=target)
    if current.enabled == bool(enabled):
        return {**current.as_dict(), "changed": False, "audit_id": None}

    action = ON if enabled else OFF
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=scope.actor,
        action=action, outcome=audit_writer.ALLOWED, reason=reason.strip(),
        before={"group_id": target, "drill_mode": current.enabled},
        after={"group_id": target, "drill_mode": bool(enabled),
               "channel": DRILL_CHANNEL, "data_source": DATA_SOURCE},
        api_name="dsm.drill", api_method="POST", status_http=200,
    )
    log.info("%s group=%s → %s (%s)", TAG, target,
             "ON" if enabled else "OFF", reason.strip())
    state = drill_state(scope=scope, group_id=target)
    return {**state.as_dict(), "changed": True, "audit_id": entry.audit_id}


def drill_state(*, scope: TenantScope, group_id: int | None = None) -> DrillState:
    """지금 훈련인가. **문지기를 그대로 지난다** — 남의 테넌트 상태도 못 읽는다."""
    target = _target_group(scope, group_id)
    return _state_of(target)


def is_drill_mode(*, group_id: int | None) -> bool:
    """**K2 가 물어볼 한 줄.** 스코프를 받지 않는다 — 발송 경로에는 요청자가 없다.

    ⚠ 이 함수는 **판정만 한다.** 채널을 바꾸는 것은 K2 의 일이다(위 파일 주석).
    ⚠ `group_id` 가 `None` 이면 **거짓이다.** 「모르니까 훈련일 수도」로 참을 내면
      테넌트를 못 읽은 순간 진짜 경보가 통째로 로그로 간다 — 안전한 기본값은 실발송이다.
    """
    if group_id is None:
        return False
    return _state_of(group_id).enabled


def is_drill_event_for_stream(*, occurred_at: datetime,
                              stream_monitor_id: int | None) -> bool:
    """스트림 하나로 묻는 갈래 — **App 층이 모델을 만지지 않게 한다** (DA-04 §1-1).

    이벤트의 소유는 스트림이 정한다(K1 `_inherit_owner`). 화면·API 가 드는 것은
    `stream_monitor_id` 뿐이므로 소속을 되짚는 한 줄이 필요한데, 그 한 줄을
    `apps/dsm/services.py` 에 두면 App 이 ORM 을 만지게 되고
    `test_dsm_app` 이 그것을 잡는다 — **잡는 것이 옳다.** 그래서 여기 둔다.
    """
    if stream_monitor_id is None:
        return False
    group_id = (apps.get_model("stream_monitors", "StreamMonitor")
                ._base_manager.filter(pk=stream_monitor_id)
                .values_list("group_id", flat=True).first())
    return is_drill_event(occurred_at=occurred_at, group_id=group_id)


def is_drill_event(*, occurred_at: datetime, group_id: int | None) -> bool:
    """이 시각의 이벤트가 **훈련 중에 난 것인가.**

    칸이 아니라 창으로 판정하는 이유는 이 파일 머리에 적었다. 판정은 여기 한 곳이고,
    화면·보고서는 이 답을 받아 `data_source=drill` 이라 적는다.
    """
    if group_id is None or occurred_at is None:
        return False
    for row in _rows_of(group_id):
        at = row["at"]
        if at is None or at > occurred_at:
            continue
        return row["enabled"]          # 이 시각 **직전**의 마지막 전환이 답이다
    return False


def _rows_of(group_id: int) -> list[dict]:
    """이 테넌트의 전환 전건, **최신순.** 없으면 빈 목록 — 켠 적이 없다는 뜻이다."""
    rows = (
        _audit_model()
        ._base_manager.filter(logger_name=LOGGER_NAME)
        .order_by("-create_datetime", "-id")
        .values("id", "create_datetime", "created_on", "username",
                "note", "api_name", "data_after")[:2000]
    )
    out: list[dict] = []
    for row in rows:
        after = _as_mapping(row.get("data_after"))
        if after.get("group_id") != group_id:
            continue
        out.append({
            "at": row.get("create_datetime") or row.get("created_on"),
            "enabled": bool(after.get("drill_mode")),
            "by": (row.get("username") or "").strip(),
            "reason": (row.get("note") or "").strip(),
            "action": ON if after.get("drill_mode") else OFF,
        })
    return out


def _state_of(group_id: int | None) -> DrillState:
    if group_id is None:
        return DrillState(group_id=None, enabled=False)
    rows = _rows_of(group_id)
    if not rows:
        return DrillState(group_id=group_id, enabled=False)
    last = rows[0]
    return DrillState(group_id=group_id, enabled=last["enabled"], since=last["at"],
                      by=last["by"], reason=last["reason"], last_action=last["action"])


# ═══════════════════════════════════════════════════════════════════════════
# 훈련 종료 보고서 — **첫 증거는 「실채널 발송 0」이다**
# ═══════════════════════════════════════════════════════════════════════════
def drill_report(*, scope: TenantScope, group_id: int | None = None) -> dict:
    """마지막(또는 진행 중인) 훈련 한 판의 보고서 1장.

    ★ 이 보고서가 **먼저 답해야 하는 것 하나**: 훈련 창 안에서 **사람에게 나간 발송이
      몇 건인가.** 0 이 아니면 훈련이 진짜 경보를 흉내 낸 것이 아니라 **진짜로 보냈다**는
      뜻이고, 그것은 훈련 실패가 아니라 **사고**다.

    ★ 0 을 「없음」으로 적지 않는다. **모수와 함께** 적는다(D-301) — 창 안 발송 전건이
      몇이고 그중 실채널이 몇인지. 분모 없는 0 은 「발송 자체가 없었다」와 구별되지 않고,
      그러면 스위치가 안 걸린 채 아무 일도 안 일어난 밤이 「훈련 성공」이 된다.
    """
    target = _target_group(scope, group_id)
    rows = _rows_of(target)
    if not rows:
        return {"group_id": target, "measurable": False,
                "reason": "이 테넌트는 훈련 모드를 한 번도 켠 적이 없습니다.",
                "started_at": None, "ended_at": None}

    #: 마지막 창을 집는다: 최신순 목록에서 처음 만나는 ON 이 시작이고,
    #: 그보다 뒤(=목록에서 앞)의 OFF 가 끝이다. 진행 중이면 끝이 `None` 이다.
    ended_at: datetime | None = None
    started_at: datetime | None = None
    for row in rows:
        if row["enabled"]:
            started_at = row["at"]
            break
        ended_at = row["at"]
    if started_at is None:
        return {"group_id": target, "measurable": False,
                "reason": "켠 기록 없이 끈 기록만 있습니다 — 감사가 잘렸을 수 있습니다.",
                "started_at": None, "ended_at": ended_at}

    Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
    Event = apps.get_model("stream_monitors", "DetectionEvent")

    sends = Delivery._base_manager.filter(group_id=target,
                                          occurred_at__gte=started_at)
    events = Event._base_manager.filter(stream_monitor__group_id=target,
                                        occurred_at__gte=started_at)
    if ended_at is not None:
        sends = sends.filter(occurred_at__lte=ended_at)
        events = events.filter(occurred_at__lte=ended_at)

    by_channel: dict[str, int] = {}
    for channel in sends.values_list("channel", flat=True):
        key = str(channel or "")
        by_channel[key] = by_channel.get(key, 0) + 1
    real = {c: n for c, n in by_channel.items() if c != DRILL_CHANNEL}

    by_type: dict[str, int] = {}
    for event_type in events.values_list("event_type", flat=True):
        by_type[str(event_type)] = by_type.get(str(event_type), 0) + 1

    return {
        "group_id": target,
        "measurable": True,
        "started_at": started_at,
        "ended_at": ended_at,
        "in_progress": ended_at is None,
        "data_source": DATA_SOURCE,
        #: ★ 첫 증거. **0 이어야 한다.**
        "real_channel_sends": sum(real.values()),
        "real_channel_breakdown": real,
        #: 분모 — 창 안 발송 전건. 이것이 0 이면 위의 0 은 아무것도 증명하지 않는다.
        "sends_total": sum(by_channel.values()),
        "sends_by_channel": by_channel,
        "events_total": sum(by_type.values()),
        "events_by_type": by_type,
        "switch_by": rows[0]["by"],
        "switch_reason": rows[0]["reason"],
    }
