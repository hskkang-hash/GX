# -*- coding: utf-8 -*-
"""K2 알림 커널 — **공개 면**.

App(L4)이 만질 수 있는 것은 여기 있는 이름뿐이다. `scripts/verify_layers.py` 가
그 밖의 import 를 exit 1 로 막는다 (D-278 · DA-04 §1-4).

    from kernels.k2_notify import send, resolve_recipients      # 이렇게 쓴다
    from stream_monitors.models import DeliveryRecord           # 이러면 CI 가 막는다

목록은 **DA-04 §2 K2 표 그대로**다. 표를 바꾸려면 그 문서와 이 파일과
`tests/test_k2_notify_kernel.KernelPublicSurfaceTest.SURFACE` 를 **같은 커밋에서** 고친다.

★ 표는 저장소를 하나만 쓴다 — `DeliveryRecord` 가 알림 이력이자 **K4 의 조치 이력**이다.
  두 벌로 적재하면 알림과 보고서가 다른 말을 한다 (DA-04 K2 이중 AC).
"""
from kernels.k2_notify.exceptions import (
    EventNotFound,
    InvalidNotifyInput,
    K2Error,
    NoRecipients,
    NotImplementedYet,
)
from kernels.k2_notify.schemas import (
    F10_MAX_LATENCY,
    SUPPRESS_WINDOW,
    DeliveryView,
    Recipient,
)
from kernels.k2_notify.services import (
    list_deliveries,
    resolve_recipients,
    send,
    suppress,
)

__all__ = [
    # DA-04 §2 K2 공개 면 4개
    "resolve_recipients",
    "send",
    "suppress",
    "list_deliveries",
    # 나가는 값의 모양
    "Recipient",
    "DeliveryView",
    # 오류 계약
    "K2Error",
    "EventNotFound",
    "InvalidNotifyInput",
    "NoRecipients",
    "NotImplementedYet",
    # 계약이 정한 숫자 — 화면·시험·보고서가 **같은 값**을 본다 (D-212)
    "F10_MAX_LATENCY",
    "SUPPRESS_WINDOW",
]
