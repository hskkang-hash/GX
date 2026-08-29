# -*- coding: utf-8 -*-
"""K2 **재알림 N분** — 보냈는데 아무도 받지 않은 알림을 다시 보낸다 (차선 D · U3).

무엇을 재는가
-------------
「N분」의 기준점을 **발생 시각이 아니라 마지막 성공 발송 시각**으로 잡는다.

    발생 → (K2.send) 발송 성공 ──── N분 ────→ 아직 아무도 접수 안 함 → 재알림

발생 시각에서 재면, 발송이 3분 늦게 나간 사건은 사람에게 N−3분만 주고 다시 울린다.
그것은 사람의 게으름이 아니라 **우리 지연**이고, 우리 지연으로 사람을 재촉하는 것은
알림 피로를 만든다. 「보낸 뒤로 N분」이 사람이 실제로 받은 시각에서 재는 유일한 값이다.

왜 `send(respect_suppression=True)` 하나로는 안 되는가 [실측 2026-09-04]
------------------------------------------------------------------------
`suppress` 는 **다른 이벤트**의 중복을 접는 장치다. 판정식이

    occurred_at__lt=event.occurred_at  AND  occurred_at >= event.occurred_at - 5분

이라서, 같은 이벤트의 재발송은 `occurred_at` 이 **같으므로** `__lt` 에 걸리지 않는다.
즉 5분 억제는 재알림을 접지 않는다 — 접어 줄 것이라고 믿고 이 문을 열면 버튼 한 번에
같은 사람에게 알림이 무한히 간다. 그래서 **이 모듈이 자기 문턱을 따로 잰다.**

무엇을 하지 않는가
------------------
· **수신자를 새로 고르지 않는다.** 규칙(`resolve_recipients`)이 고른 그 사람들에게
  다시 간다. 「원 수신자 목록」을 발송 이력에서 되짚어 만들면 그 사이 인사이동으로
  바뀐 규칙을 무시하게 되고, 퇴사자에게 재난 알림이 다시 간다.
· **행을 직접 만들지 않는다.** 실제 발송과 이력 적재는 `send` 가 한다 — 두 벌로
  적재하면 알림과 보고서가 다른 말을 한다(DA-04 K2 이중 AC).
· **조용한 빈 성공을 만들지 않는다.** 안 보낸 경우 `skipped_reason` 이 왜인지 말한다
  (D-290 — 부재와 실패를 가른다).

한계 [실측 · 이번 턴에 못 고친 것]
-----------------------------------
재알림으로 생긴 `DeliveryRecord` 행의 `retry_count` 는 **0 이다.** 그 칸을 올리려면
`send` 가 인자를 하나 더 받아야 하고, `send` 는 F-10 판정의 정본이라 이번 턴에
건드리지 않았다. 지금 재알림 행과 최초 발송 행을 가르는 것은 **시각**뿐이다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.apps import apps
from django.utils import timezone

from common.tenant_filters import assert_scoped
from common.tenant_scope import TenantScope
from kernels.k2_notify.exceptions import EventNotFound, InvalidNotifyInput
from kernels.k2_notify.schemas import DeliveryView

#: 기본 재알림 창. **기본값이 있는 것과 없는 것을 가른다** — 부르는 쪽이 안 주면
#: 이 값이고, 이 값은 5분 억제창보다 길다(그보다 짧으면 재알림이 억제와 겹쳐 뜻이 흐려진다).
DEFAULT_RENOTIFY_AFTER = timedelta(minutes=10)

#: 재알림 창의 상한. 하루가 넘는 「재알림」은 재알림이 아니라 새 사건이다.
MAX_RENOTIFY_AFTER = timedelta(hours=24)

#: 재알림 창의 하한. 이보다 짧으면 사람이 화면을 여는 시간보다 알림이 빠르다.
MIN_RENOTIFY_AFTER = timedelta(minutes=1)

#: 아직 사람이 손대지 않은 대응 상태. 이 값일 때만 재알림이 뜻을 가진다.
_UNTOUCHED_RESPONSE_STATE = "occurred"


@dataclass(frozen=True)
class RenotifyResult:
    """재알림 한 번의 결과. **왜 안 보냈는지가 값 안에 있다.**

    빈 튜플만 돌려주면 「보낼 사람이 없었다」와 「아직 이르다」와 「이미 접수됐다」가
    화면에서 같은 그림이 된다 — 셋은 부르는 쪽이 할 일이 전혀 다르다.
    """

    event_id: int
    #: 실제로 보냈는가. 거짓이면 `skipped_reason` 이 비어 있지 않다.
    sent: bool
    #: 안 보낸 사유. 보냈으면 빈 문자열이다.
    skipped_reason: str
    #: 마지막 성공 발송 이후 흐른 시간(초). 그런 발송이 없으면 `None` — **0 이 아니다.**
    elapsed_seconds: float | None
    #: 이번 판정에 쓴 창(초).
    after_seconds: float
    #: 판정 시점의 대응 진행 상태.
    response_state: str
    #: 이번 재알림이 만든 발송 이력. 안 보냈으면 빈 튜플이다.
    deliveries: tuple[DeliveryView, ...] = ()


def _model(name: str):
    return apps.get_model("stream_monitors", name)


def _coerce_after(after_minutes: float | None) -> timedelta:
    """N분을 창으로 바꾼다. **범위 밖은 거절이다** — 잘라 맞추지 않는다.

    조용히 잘라 맞추면 부르는 쪽은 자기가 준 값이 쓰인 줄 안다. 0분을 주고 10분이
    돌아가는 자리가 「설정했는데 안 바뀌는」 자리다.
    """
    if after_minutes is None:
        return DEFAULT_RENOTIFY_AFTER
    try:
        minutes = float(after_minutes)
    except (TypeError, ValueError):
        raise InvalidNotifyInput(
            f"after_minutes={after_minutes!r} 은 수가 아니다.")
    window = timedelta(minutes=minutes)
    if window < MIN_RENOTIFY_AFTER or window > MAX_RENOTIFY_AFTER:
        raise InvalidNotifyInput(
            f"after_minutes={minutes} 는 범위 밖이다. 허용: "
            f"{MIN_RENOTIFY_AFTER.total_seconds() / 60:.0f}분 ~ "
            f"{MAX_RENOTIFY_AFTER.total_seconds() / 3600:.0f}시간")
    return window


def renotify(
    *,
    scope: TenantScope,
    event_id: int,
    after_minutes: float | None = None,
    now: datetime | None = None,
) -> RenotifyResult:
    """보낸 지 N분이 지나도 **아무도 손대지 않은** 이벤트를 다시 알린다.

    문턱 넷을 순서대로 지난다. 순서가 뜻이다 — 앞의 것이 뒤의 것보다 싸고,
    앞에서 걸리면 뒤를 물어볼 필요가 없다.

        ① 그 이벤트가 있는가                     없으면 `EventNotFound`
        ② **내 테넌트의 것인가**                 아니면 404 (쓰기 IDOR · D-290)
        ③ 원 발송이 있는가                       없으면 재알림이 아니라 최초 발송이다
        ④ N분이 지났고 아직 손대지 않았는가       아니면 안 보낸다 + 사유

    ★ ②가 이 함수의 전부다. 이 문턱이 없으면 **남의 테넌트 사건으로 남의 수신자에게
      우리가 알림을 일으킬 수 있다.** 읽기 격리가 온전해도 그것은 격리가 아니다.
      문지기를 새로 만들지 않고 `assert_scoped` 를 그대로 쓴다 — 두 벌은 갈린다(D-212).

    ★ 시스템 스코프(파이프라인·크론)는 ②를 지나지 않는다. 그것이 `TenantScope.system`
      이 사유를 요구하는 이유다.
    """
    from kernels.k1_event.response_flow import response_state as k1_response_state
    from kernels.k2_notify.services import send

    Event = _model("DetectionEvent")
    Delivery = _model("DeliveryRecord")

    window = _coerce_after(after_minutes)
    at = now or timezone.now()

    # ① 있는가
    event = Event._base_manager.filter(pk=event_id).first()
    if event is None:
        raise EventNotFound(f"event_id={event_id} 가 없다")

    # ② 내 것인가 — **쓰기 IDOR 문턱**
    if not scope.is_system:
        assert_scoped(Event, event_id, scope.actor)

    # ③ 원 발송이 있는가. 성공한 것만 센다 — 실패한 발송은 「보낸 적」이 아니다
    #    (`suppress` 가 성공 위에서만 접는 것과 같은 이유).
    last_sent = (
        Delivery._base_manager
        .filter(event_id=event_id, succeeded=True, sent_at__isnull=False)
        .order_by("-sent_at")
        .values_list("sent_at", flat=True)
        .first()
    )
    current_state = getattr(event, "response_state", "") or ""

    if last_sent is None:
        return RenotifyResult(
            event_id=event_id, sent=False,
            skipped_reason=(
                "원 발송이 없다 — 이것은 재알림이 아니라 최초 발송이다. "
                "`kernels.k2_notify.send` 를 부른다. "
                "(발송 실패 행만 있는 경우도 여기다: 실패는 「보낸 적」이 아니다)"),
            elapsed_seconds=None, after_seconds=window.total_seconds(),
            response_state=current_state)

    elapsed = (at - last_sent).total_seconds()

    # ④-a 아직 이르다
    if elapsed < window.total_seconds():
        return RenotifyResult(
            event_id=event_id, sent=False,
            skipped_reason=(
                f"아직 이르다 — 마지막 발송 뒤 {elapsed:.0f}초 지났고 "
                f"창은 {window.total_seconds():.0f}초다"),
            elapsed_seconds=elapsed, after_seconds=window.total_seconds(),
            response_state=current_state)

    # ④-b 이미 사람이 손댔다. **재알림의 목적은 무응답을 깨우는 것**이므로
    #     접수된 사건을 다시 울리는 것은 알림 피로일 뿐이다.
    #     ⚠ 상태는 K1 이 답한다 — 여기서 전이표를 다시 적지 않는다(D-212).
    if not scope.is_system:
        current_state = k1_response_state(event_id, scope=scope)["response_state"]
    if current_state != _UNTOUCHED_RESPONSE_STATE:
        return RenotifyResult(
            event_id=event_id, sent=False,
            skipped_reason=(
                f"이미 손댔다 — 대응 진행이 `{current_state}` 다. "
                "재알림은 **무응답**을 깨우는 것이지 진행 중인 사람을 재촉하는 것이 아니다"),
            elapsed_seconds=elapsed, after_seconds=window.total_seconds(),
            response_state=current_state)

    # ⑤ 보낸다. **행을 직접 만들지 않는다** — `send` 가 정본이다.
    #    `respect_suppression=False` 인 이유: 5분 억제는 같은 이벤트의 재발송을 애초에
    #    접지 않는다(위 머리말 [실측]). 켜 두면 「접어 줄 것」이라는 잘못된 믿음이
    #    코드에 남고, 실제 문턱은 위 ④뿐이라는 사실이 가려진다.
    deliveries = send(scope=scope, event_id=event_id, respect_suppression=False)
    return RenotifyResult(
        event_id=event_id, sent=True, skipped_reason="",
        elapsed_seconds=elapsed, after_seconds=window.total_seconds(),
        response_state=current_state, deliveries=tuple(deliveries))
