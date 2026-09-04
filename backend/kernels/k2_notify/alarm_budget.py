# -*- coding: utf-8 -*-
"""알림 예산 시뮬레이션 — QA-12 (2026-09-04 · 차선 Q).

한 문장
-------
    규칙을 저장하기 전에 **최근 7일로 되돌려 돌려 보고**, 그 규칙이 관제요원 한 사람에게
    **시간당 몇 건**을 보낼지 수로 말한다.

왜 이 파일이 생겼나 — [시험]은 **판정만 보여 주고 건수를 안 보여 준다**
----------------------------------------------------------------------
[실측 등재 2026-09-24 · PRD v2.5 ⑤] 규칙 저장 전 [시험](DA-03 §3-3)은 「이 규칙은
누구에게 간다」까지만 답한다. 규칙 하나가 알림 폭주를 만들어도 **저장 전에 알 방법이
없다.** 폭주한 뒤에 알게 되는 것은 알림을 끄는 방식으로 해결되고, 한 번 꺼진 알림은
다시 안 켜진다 — 그것이 이 절이 막으려는 것이다.

★ 상한 6은 **우리가 지은 수가 아니다** [인용]
---------------------------------------------
EEMUA 191(Alarm Systems: A Guide to Design, Management and Procurement)이 권고하는
**운전원 1인당 시간당 평균 경보 6건**이다. 우리 판단이 아니라 인용이므로, 고객이
「왜 6이냐」고 물을 때 답이 있다. 그리고 **우리가 올릴 수 없는 수**이기도 하다 —
지어낸 수라면 불편할 때 올렸을 것이다.

★ 빨강이 아니라 **주황**이다 (ISA-101)
--------------------------------------
빨강은 `critical` 등급 전용이다(계약 문서: *"critical 만 빨강. 다른 용도로 빨강 금지"*).
예산 초과는 **저장을 막지 않는다** — 현장이 그 규칙을 정말 원할 수도 있다. 막는 것이
아니라 **보여 주는** 것이고, 그래서 색도 경고이지 금지가 아니다.

무엇을 세나 — **억제를 지난 뒤의 수**
-------------------------------------
이벤트 수를 그대로 세면 실제보다 크게 나온다. K2 의 5분 억제(`SUPPRESS_WINDOW`)가
같은 `(카메라, 유형)` 의 재발을 접기 때문이다. 크게 나온 수는 두 번 해롭다:
사람이 한 번 놀라고, 다음번에 그 수를 안 믿는다. 그래서 **억제를 흉내 내지 않고
같은 상수를 인용해** 접은 뒤의 수를 낸다.

★ 이것은 **시뮬레이션이지 예언이 아니다.** 최근 7일이 다음 7일과 같다는 보장은 없다 —
  장마철 규칙을 건기 표본으로 재면 낮게 나온다. 그 사실을 `AlarmBudgetView.caveat` 에
  값으로 들려 보낸다: 화면이 수만 그리고 단서를 지우면 그때 이 수는 예언이 된다.

무엇을 하지 않나
----------------
· **저장하지 않는다.** 읽기 전용이다 — 저장은 `save_notification_rule` 한 곳이다.
· 규칙 행을 만들지 않는다. 아직 없는 규칙을 재는 것이 이 함수의 목적이다.
· 발송을 하지 않는다. `DeliveryRecord` 행이 하나도 안 생긴다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.apps import apps
from django.utils import timezone

from common.tenant_scope import TenantScope
from kernels.k2_notify.exceptions import InvalidNotifyInput
from kernels.k2_notify.schemas import SUPPRESS_WINDOW
from kernels.k2_notify.services import _owner_for, resolve_recipients

# ═══════════════════════════════════════════════════════════════════════════
# 계약이 정한 수 — **한 곳에만 둔다** (D-212)
# ═══════════════════════════════════════════════════════════════════════════

#: ★ [인용] EEMUA 191 — 운전원 1인당 **시간당 평균 경보 6건**.
#:   우리가 지은 수가 아니다. 이름에 출처를 박아 둔 이유는, 이름이 `MAX_ALARMS` 였다면
#:   누군가 불편할 때 8로 고쳤을 것이기 때문이다.
EEMUA_191_ALARMS_PER_OPERATOR_HOUR: float = 6.0

#: 시뮬레이션이 되돌아보는 기간. 7일인 이유: 요일 주기(주말 통행량)가 한 번 돈다.
#: 하루면 그날의 사정이 전부가 되고, 한 달이면 계절이 섞인다.
BUDGET_WINDOW_DAYS: int = 7

#: 판정 두 값. **셋이 아니다** — 빨강을 만들면 ISA-101 이 깨진다.
BUDGET_OK = "ok"
BUDGET_ORANGE = "orange"


def _model(name: str):
    return apps.get_model("stream_monitors", name)


# ═══════════════════════════════════════════════════════════════════════════
# 나가는 값 — **모델이 아니라 값이다**
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class AlarmBudgetView:
    """[시험] 이 화면에 그릴 것. **수와 그 수의 내력을 함께 들고 다닌다.**

    ★ `matched_events` 와 `after_suppression` 을 둘 다 낸다. 하나만 내면 「7일에
      420건이었는데 왜 시간당 1건이냐」에 답할 수 없고, 답할 수 없는 수는 안 믿긴다.
    """

    #: 규칙 후보 그 자체 (되돌려 준다 — 화면이 무엇을 쟀는지 확인할 수 있게).
    severity: str
    zone: str | None

    #: 표본 기간.
    window_days: int
    window_hours: float
    since: datetime
    until: datetime

    #: 창 안에서 이 규칙에 걸린 이벤트 수 (억제 전).
    matched_events: int
    #: 5분 억제를 지난 뒤 실제로 나갔을 알림 수.
    after_suppression: int
    #: 관제요원 **1인당** 시간당 알림 수. 규칙이 고른 사람은 이 규칙의 알림을
    #: **전부** 받으므로, 1인당 부하는 수신자 수로 나뉘지 않는다.
    per_operator_hour: float

    #: 이 규칙이 지금 고르는 사람 수. 0 이면 예산은 0 이지만 **그것은 좋은 상태가 아니다.**
    recipients: int

    #: 인용된 상한과 그 출처.
    limit: float
    citation: str

    level: str
    headline: str
    caveat: str

    @property
    def over_budget(self) -> bool:
        return self.level == BUDGET_ORANGE


# ═══════════════════════════════════════════════════════════════════════════
# 판정 — **순수 함수.** DB 없이 잰다
# ═══════════════════════════════════════════════════════════════════════════
def _fold_by_suppression(keyed_times, window: timedelta = SUPPRESS_WINDOW) -> int:
    """5분 억제를 지난 뒤 **몇 건이 실제로 나갔을까**.

    `keyed_times` 는 `[(key, occurred_at), ...]` 이고 `key` 는 `(카메라, 유형)` 이다.
    같은 key 의 직전 발송에서 `window` 안이면 접힌다 — K2 의 `suppress` 가 발송 이력을
    보고 하는 판정과 **같은 모양**이고, 같은 상수를 인용한다.

    ★ 흉내가 아니라 인용이다. 여기서 `timedelta(minutes=5)` 를 적으면 두 벌이 되고,
      두 벌은 반드시 갈린다 (D-212).
    """
    last: dict = {}
    kept = 0
    for key, when in sorted(keyed_times, key=lambda r: r[1]):
        seen = last.get(key)
        if seen is not None and when - seen <= window:
            continue
        last[key] = when
        kept += 1
    return kept


def _judge(per_hour: float, limit: float = EEMUA_191_ALARMS_PER_OPERATOR_HOUR):
    """`(등급, 머리글)`. **초과해도 빨강이 아니다** — 주황이다 (ISA-101)."""
    if per_hour > limit:
        return (BUDGET_ORANGE,
                f"이 규칙은 시간당 {per_hour:.1f}건을 보냅니다 — "
                f"EEMUA 191 권고 상한 {limit:g}건")
    return (BUDGET_OK,
            f"이 규칙은 시간당 {per_hour:.1f}건을 보냅니다 "
            f"(EEMUA 191 권고 상한 {limit:g}건)")


# ═══════════════════════════════════════════════════════════════════════════
# 공개 면 — 읽기 전용
# ═══════════════════════════════════════════════════════════════════════════
def simulate_alarm_budget(
    *,
    scope: TenantScope,
    severity: str,
    zone: str | None = None,
    days: int = BUDGET_WINDOW_DAYS,
    now: datetime | None = None,
    group=None,
) -> AlarmBudgetView:
    """규칙 후보 하나를 **최근 7일 이벤트로 되돌려 돌려 본다.**

    아직 없는 규칙을 잰다 — 그것이 요점이다. 저장한 뒤에 재면 이미 늦었다.

    ★ `zone` 은 `NotificationRule.zone` 과 같은 **라벨**이다. 라벨이 `Zone` 이름과
      맞으면 그 구역의 카메라로 좁히고, 맞는 구역이 없으면 **좁히지 않고 그 사실을
      단서에 적는다** — 조용히 0건을 내면 「그 구역엔 아무 일도 없었다」로 읽힌다.
    """
    Event = _model("DetectionEvent")
    if severity not in Event.Severity.values:
        raise InvalidNotifyInput(
            f"severity={severity!r} 은 계약에 없다. 허용: {', '.join(Event.Severity.values)}")
    if days < 1:
        raise InvalidNotifyInput(
            f"days={days} — 되돌아볼 기간이 없다. 표본 0일의 시간당 건수는 나눗셈이 아니라 "
            f"만들어진 수다")

    # ★ `group=` 을 그대로 믿지 않는다 — 사람이 남의 테넌트를 가리키면 거절한다.
    #   그러지 않으면 남의 이벤트 수로 내 규칙의 예산을 재게 되고, 그 수는 **남의
    #   관제 현황**이다. 판단은 `services._owner_for` 한 곳이다 (D-212).
    owner = _owner_for(scope, group)
    if owner is None:
        raise InvalidNotifyInput(
            "예산을 잴 테넌트가 없다. 파이프라인 호출이면 `group=` 을 넘겨라 — 그것 없이 "
            "세면 **전 테넌트의 이벤트**를 세고, 그 수는 이 고객의 예산이 아니다 (D-281)")

    until = now or timezone.now()
    since = until - timedelta(days=days)
    window_hours = days * 24.0

    qs = _own_events(Event, owner).filter(
        severity=severity, occurred_at__gte=since, occurred_at__lte=until)

    zone_note = ""
    if zone:
        camera_ids = _zone_camera_ids(owner, zone)
        if camera_ids is None:
            zone_note = (f" · 구역 라벨 {zone!r} 과 이름이 같은 활성 카메라묶음 구역이 "
                         f"없다 — **좁히지 않고** 전 구역으로 쟀다")
        else:
            qs = qs.filter(stream_monitor_id__in=camera_ids)

    rows = list(qs.values_list("stream_monitor_id", "event_type", "occurred_at"))
    matched = len(rows)
    kept = _fold_by_suppression([((cid, etype), when) for (cid, etype, when) in rows])
    per_hour = kept / window_hours

    people = resolve_recipients(scope=scope, severity=severity, group=owner, zone=zone)
    level, headline = _judge(per_hour)

    caveat = (f"최근 {days}일 표본의 되돌림이지 예보가 아니다 — 장마철 규칙을 건기 "
              f"표본으로 재면 낮게 나온다. 5분 억제를 지난 뒤의 수다"
              f"(이벤트 {matched}건 → 알림 {kept}건){zone_note}")
    if not people:
        caveat += (" · ⚠ 이 규칙이 지금 고르는 사람이 **0명**이다 — 예산 0은 조용해서가 "
                   "아니라 **아무에게도 안 가서**다")

    return AlarmBudgetView(
        severity=severity, zone=zone,
        window_days=days, window_hours=window_hours, since=since, until=until,
        matched_events=matched, after_suppression=kept, per_operator_hour=per_hour,
        recipients=len(people),
        limit=EEMUA_191_ALARMS_PER_OPERATOR_HOUR,
        citation="EEMUA 191 — Alarm Systems: A Guide to Design, Management and Procurement",
        level=level, headline=headline, caveat=caveat,
    )


def _own_events(Event, owner):
    """그 테넌트의 이벤트만. `k1_event` 와 **같은 소유 판단**을 쓴다 (D-212)."""
    # ★ 소유 필드 판단은 **K2 자신의 자리**를 통해 쓴다 (`services._owner_field`).
    #   그 함수가 K1 의 판단기를 그대로 부른다 — 판단은 한 곳에서만(D-212).
    #   여기서 K1 을 직접 import 하지 않는 이유: 이 모듈이 **K1 소비자로 등재**
    #   되어야 하고(F-05 진입면 대장), 등재는 「이벤트를 쓴다」는 선언이다.
    #   이 두 모듈은 이벤트를 **세거나 요약할 뿐** 만들지 않는다.
    from kernels.k2_notify.services import _owner_field

    if _owner_field(Event) == "groups":
        return Event._base_manager.filter(groups=owner).distinct()
    return Event._base_manager.filter(group=owner)


def _zone_camera_ids(owner, zone_label: str):
    """구역 라벨 → 그 구역 카메라 id 들. 맞는 구역이 없으면 `None`(빈 목록이 아니다).

    ★ 빈 목록과 `None` 을 가른다. 빈 목록이면 「구역은 있는데 카메라가 없다」이고,
      `None` 이면 「그 이름의 구역이 없다」다 — 앞은 0건이 사실이고, 뒤는 **좁히면
      안 되는 상태**다 (D-290).
    """
    Zone = _model("Zone")
    # ★ 소유 필드 판단은 **K2 자신의 자리**를 통해 쓴다 (`services._owner_field`).
    #   그 함수가 K1 의 판단기를 그대로 부른다 — 판단은 한 곳에서만(D-212).
    #   여기서 K1 을 직접 import 하지 않는 이유: 이 모듈이 **K1 소비자로 등재**
    #   되어야 하고(F-05 진입면 대장), 등재는 「이벤트를 쓴다」는 선언이다.
    #   이 두 모듈은 이벤트를 **세거나 요약할 뿐** 만들지 않는다.
    from kernels.k2_notify.services import _owner_field

    qs = Zone._base_manager.filter(
        name=zone_label, kind=Zone.Kind.CAMERA_GROUP, is_active=True)
    qs = (qs.filter(groups=owner).distinct() if _owner_field(Zone) == "groups"
          else qs.filter(group=owner))
    found = list(qs)
    if not found:
        return None
    ids: list = []
    for row in found:
        ids.extend(row.cameras.values_list("pk", flat=True))
    return ids


__all__ = [
    "EEMUA_191_ALARMS_PER_OPERATOR_HOUR",
    "BUDGET_WINDOW_DAYS",
    "BUDGET_OK",
    "BUDGET_ORANGE",
    "AlarmBudgetView",
    "simulate_alarm_budget",
]
