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
    RuleView,
)
from kernels.k2_notify.renotify import (
    DEFAULT_RENOTIFY_AFTER,
    MAX_RENOTIFY_AFTER,
    MIN_RENOTIFY_AFTER,
    RenotifyResult,
    renotify,
)
from kernels.k2_notify.services import (
    list_deliveries,
    notice_false_positive,
    resolve_recipients,
    save_notification_rule,
    send,
    suppress,
)

__all__ = [
    # DA-04 §2 K2 공개 면 4개
    "resolve_recipients",
    "send",
    "suppress",
    "list_deliveries",
    # ★ P-16 오탐 ③ — 알림이 나간 이벤트가 오탐이 되면 원 수신자에게 **1회** (2026-09-20).
    #   발송이 아니라 **뒷정리**라 `DeliveryRecord` 행을 만들지 않는다 — 그 표는
    #   F-10 의 30초와 5분 억제를 재는 자리다(함수 머리말 ★★).
    "notice_false_positive",
    # ★ P-20 ① 알림 규칙 쓰기 면 — **개발 DB 규칙 0건**이 이 이름을 만들었다 (2026-09-22).
    #   격리 대장(`tests/test_tenant_isolation.WRITE_NO_PROBE`)에 **선등재된 이름**이고,
    #   면이 실제로 열렸으므로 그 줄은 probe 로 옮겨져야 한다(P-8).
    "save_notification_rule",
    # ★ 차선 D (2026-09-04) 재알림 N분 — **U3 「내가 놓친 알림」의 자리**.
    #   격리 대장(`tests/test_tenant_isolation.WRITE_NO_PROBE`)에 **선등재된 이름**이고,
    #   면이 실제로 열렸으므로 그 줄은 probe 로 옮겨져야 한다(P-8).
    #   ⚠ 5분 억제는 **같은 이벤트의 재발송을 접지 않는다** — 문턱은 이 모듈이 따로 잰다.
    "renotify",
    # 나가는 값의 모양
    "Recipient",
    "DeliveryView",
    "RuleView",
    "RenotifyResult",
    # 오류 계약
    "K2Error",
    "EventNotFound",
    "InvalidNotifyInput",
    "NoRecipients",
    "NotImplementedYet",
    # 계약이 정한 숫자 — 화면·시험·보고서가 **같은 값**을 본다 (D-212)
    "F10_MAX_LATENCY",
    "SUPPRESS_WINDOW",
    # 재알림 창의 기본·상한·하한. 화면이 자기 숫자를 들지 않는다 (D-212).
    "DEFAULT_RENOTIFY_AFTER",
    "MAX_RENOTIFY_AFTER",
    "MIN_RENOTIFY_AFTER",
]
