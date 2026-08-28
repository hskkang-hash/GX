# -*- coding: utf-8 -*-
"""K6 피드백·계측 커널 — **공개 면**.

App(L4)이 만질 수 있는 것은 여기 있는 이름뿐이다. `scripts/verify_layers.py` 가
그 밖의 import 를 exit 1 로 막는다 (D-278 · DA-04 §1-4).

    from kernels.k6_feedback import false_positive_rate      # 이렇게 쓴다

목록은 **DA-04 §2 K6 표 그대로**다. 표를 바꾸려면 그 문서와 이 파일과
`tests/test_k6_feedback_kernel.KernelPublicSurfaceTest.SURFACE` 를 **같은 커밋에서**
함께 고친다.

★ 이 패키지에 `models.py` 가 없는 것은 **누락이 아니라 설계**다.
  DA-04 K6: *"오탐률의 분모·분자는 `DetectionEvent.status` 하나에서 나온다.
  별도 집계 테이블을 만들지 않는다 — 두 벌로 세면 숫자가 갈리고, 갈린 숫자는
  고객 앞에서 못 쓴다."*
"""
from kernels.k6_feedback.exceptions import (
    InvalidMetricInput,
    K6Error,
    NotImplementedYet,
)
from kernels.k6_feedback.schemas import FalsePositiveRate, RateWindow
from kernels.k6_feedback.services import (
    BUCKETS,
    REVIEWED_STATUSES,
    false_positive_rate,
    kpi_series,
    record_feedback,
    usage_snapshot,
)

__all__ = [
    # DA-04 §2 K6 공개 면 4개
    "record_feedback",
    "false_positive_rate",
    "usage_snapshot",
    "kpi_series",
    # 나가는 값의 모양
    "FalsePositiveRate",
    "RateWindow",
    # 오류 계약
    "K6Error",
    "InvalidMetricInput",
    "NotImplementedYet",
    # 분모의 정의 — **밖에서도 읽을 수 있게 둔다.**
    # 오탐률을 다시 세려는 코드가 생기면 최소한 같은 분모를 쓰게 한다.
    "REVIEWED_STATUSES",
    "BUCKETS",
]
