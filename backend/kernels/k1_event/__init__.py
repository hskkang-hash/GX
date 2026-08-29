# -*- coding: utf-8 -*-
"""K1 이벤트 커널 — **공개 면**.

App(L4)이 만질 수 있는 것은 여기 있는 이름뿐이다. `models` · 내부 헬퍼는 커널의 속이고,
직접 import 하면 `scripts/verify_layers.py` 가 exit 1 로 멈춘다 (D-278 · DA-04 §1-4).

    from kernels.k1_event import record_detection, query_events      # 이렇게 쓴다
    from kernels.k1_event.models import DetectionEvent               # 이러면 CI 가 막는다

목록은 **DA-04 §2 K1 표 그대로**다. 표를 바꾸려면 그 문서와 이 파일과
`tests/test_k1_event_kernel.KernelPublicSurfaceTest.SURFACE` 를 **같은 커밋에서** 함께 고친다 —
문서와 코드가 갈리면 어느 쪽이 계약인지 아무도 모른다 (D-227 이 만든 상황이 그것이었다).
"""
from kernels.k1_event.exceptions import (
    InvalidEventInput,
    K1Error,
    NotImplementedYet,
    ResponseTransitionError,
    ResponseTransitionForbidden,
    ResponseTransitionNeedsManager,
    ResponseTransitionNeedsReason,
)
from kernels.k1_event.field_reply import list_field_replies, reply_from_field
from kernels.k1_event.response_flow import (
    advance_response,
    close_as_false_positive,
    response_state,
)
from kernels.k1_event.schemas import EventView, RecordResult
from kernels.k1_event.services import (
    DEDUP_WINDOW,
    NOTIFY_WINDOW,
    close_event,
    get_event,
    query_events,
    record_detection,
    review_event,
    subscribe,
)

__all__ = [
    # DA-04 §2 K1 공개 면 6개
    "record_detection",
    "query_events",
    "get_event",
    "review_event",
    "close_event",
    "subscribe",
    # ★ D-399 대응 진행 축 — `status`(탐지 판정)와 **다른 축**이다. 섞지 않는다.
    #   DA-04 §2 K1 표에 두 줄을 더했다(같은 커밋 규약).
    "advance_response",
    "response_state",
    # ★ P-16 오탐 결합 — **소비자 한 곳만 부른다** (2026-09-20).
    #   공개 면에 두는 이유는 격리 대장(WRITE_PROBES)이 커널 `__all__` 을 훑기 때문이다:
    #   면에서 감추면 쓰기 면이 **대장 밖에서** 자란다(D-290 · D-301).
    "close_as_false_positive",
    # ★ 차선 D (2026-09-04) M3 현장 회신 — U3 #9. 공개 면에 두는 이유는
    #   격리 대장(WRITE_PROBES)이 커널 `__all__` 을 훑기 때문이다:
    #   면에서 감추면 쓰기 면이 **대장 밖에서** 자란다(D-290 · D-301).
    "reply_from_field",
    # ★ 읽기도 공개 면에 둔다 — App 이 서브모듈을 직접 가져오면 계층 검사가 멈춘다
    #   (D-278 · DA-04 §1-4). 실제로 그렇게 짰다가 5개 시험이 한꺼번에 빨개졌고,
    #   그 빨강이 옳다: 커널 로직이 App 으로 새는 첫 걸음이 서브모듈 import 다.
    "list_field_replies",
    # 나가는 값의 모양
    "EventView",
    "RecordResult",
    # 오류 계약 (4xx 로 번역된다 — 200+{"success":false} 를 만들지 않는다)
    "K1Error",
    "InvalidEventInput",
    "NotImplementedYet",
    "ResponseTransitionError",
    "ResponseTransitionForbidden",
    "ResponseTransitionNeedsManager",
    "ResponseTransitionNeedsReason",
    # 두 창. **같은 값으로 두지 말 것** — 합치면 F-04 와 U1 중 하나가 깨진다
    "DEDUP_WINDOW",
    "NOTIFY_WINDOW",
]
