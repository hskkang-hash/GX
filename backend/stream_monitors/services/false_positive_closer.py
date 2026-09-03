# -*- coding: utf-8 -*-
"""오탐 결합 규칙 — **결합이 사는 단 한 곳** (P-16 · 2026-09-20).

무엇을 하는가
-------------
「판정이 `rejected` 로 바뀌었다」는 신호를 받아 **대응 축을 종결로 닫는다.**
그리고 그 이벤트로 이미 알림이 나갔다면 **원 수신자에게 한 번** 「오탐이었다」를 알린다.

왜 여기인가 — 두 축은 서로를 모른다
-----------------------------------
D-399 가 판정 축(`status`/`verdict`)과 대응 축(`response_state`)을 갈랐다. 사용자에게
「오탐」과 「종결」이 한 번의 행동인 것은 맞지만(P-1 화면 규칙), **코드에서 두 축이
맞물리면** 다음 사람이 판정을 고치려다 대응을 깨뜨린다.

    · `review_event` 는 `response_state` 를 **모른다** — 신호만 보낸다
    · `close_as_false_positive` 는 `verdict` 를 **모른다** — 대응 축만 만진다
    · 둘을 아는 코드는 **이 파일 하나**다

역방향은 없다
-------------
`rejected` 가 나중에 `confirmed` 로 재판정되어도 **대응 축은 그대로 `closed`** 다.
자동으로 다시 열지 않는다 — 되돌림은 사람이 한다(U2 · `closed → in_progress` ·
사유 필수 · 감사에 남는다). 자동 되돌림을 넣으면 두 축이 서로를 끌어당기고, 그 순간
「지금 어디까지 왔나」를 말하는 축이 판정의 그림자가 된다.

★ 알림은 **저하 운전**이다 (K2 가 하는 것과 같다). 종결은 반드시 일어나야 하지만,
  통지가 실패했다고 판정이 실패하면 안 된다 — 「메일이 죽어도 화재 판정은 산다」.
  그래서 종결은 예외를 올리고, 통지는 로그로 떨어진다.

★ 이 파일은 `tests/test_f05_event_api.K1_CONSUMERS` 에 **사유와 함께 등재**돼 있다.
  HTTP 진입면이 아니다 — 밖에서 부를 수 있는 주소가 없고, 신호를 받는 자리다.
"""
from __future__ import annotations

import logging

from django.dispatch import receiver

from kernels.k1_event import close_as_false_positive
from kernels.k1_event.verdict_events import verdict_changed

logger = logging.getLogger(__name__)

#: 어떤 판정이 이 규칙을 켜는가. **글자로 적는다** — `DetectionEvent.Status` 를 여기서
#: 부르면 모듈 import 시각에 앱이 아직 안 서 있다(response_flow 머리말과 같은 사유).
#: 두 벌이 갈리는 것은 `tests/test_false_positive_coupling` 이 모델 값과 대조해 막는다.
REJECTED = "rejected"


@receiver(verdict_changed, dispatch_uid="gx.false_positive_closer")
def close_when_rejected(sender, *, event_id: int, verdict: str,
                        previous: str = "", scope=None, **kwargs) -> None:
    """`rejected` 로 바뀌면 대응 축을 닫는다. 그 밖의 판정에는 **아무 일도 하지 않는다.**

    ★ `dispatch_uid` 를 주는 이유: 모듈이 두 번 import 되면(테스트·리로드) 수신자가
      둘이 되고, 그러면 같은 판정에 종결이 두 번 시도된다. 두 번째는 이미 `closed` 라
      조용히 지나가겠지만 — **조용히 지나가는 중복은 다음에 조용하지 않다.**
    """
    if verdict != REJECTED:
        return                      # 역방향 없음 — 대응 축은 verdict 를 읽지 않는다
    if previous == REJECTED:
        return                      # 같은 값 재판정은 전이가 아니다

    #: ★ 문지기는 **판정자의 스코프**로 지난다. 남의 테넌트 이벤트면 여기서 404 가 나고,
    #:   그 예외는 그대로 올라가 판정 자체를 되돌린다(같은 트랜잭션) — 옳다.
    #:   격리 실패를 삼키면 그것이 격리의 부재다.
    close_as_false_positive(event_id, scope=scope)

    #: ── 곁가지: 오탐 종결 통지 (오탐 ③) ─────────────────────────────────
    #: 저하 운전. 통지가 실패해도 종결은 이미 일어났고, 그 사실이 더 중요하다.
    try:
        from kernels.k2_notify import notice_false_positive

        notice_false_positive(scope=scope, event_id=event_id)
    except Exception as exc:                                   # noqa: BLE001
        #: 삼키되 **보이게** 삼킨다. 조용한 실패는 없는 일이 된다(D-290).
        logger.warning(
            "[FP-NOTICE] event_id=%s 오탐 종결 통지 실패 — %s: %s "
            "(종결 자체는 일어났다)", event_id, type(exc).__name__, exc)
