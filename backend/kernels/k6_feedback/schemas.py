# -*- coding: utf-8 -*-
"""K6 공개 면이 주고받는 모양 — **모델을 밖으로 내보내지 않는다** (DA-04 §1-4).

계측 커널의 출력에는 규칙이 하나 더 붙는다: **비율만 내보내지 않는다.**
비율 하나는 "0.30" 이 3/10 인지 300/1000 인지 말해 주지 않고, 그 둘은 회의에서
전혀 다른 문장이다. DA-04 K6 표가 출력을 *"비율 + 분모·분자"* 로 적은 이유다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class RateWindow:
    """기간 하나의 오탐률.

    ★ `rate` 가 `None` 일 수 있다. **0.0 이 아니다.**
      분모가 0 이라는 것은 "오탐이 없었다"가 아니라 **"아직 아무도 판정하지 않았다"** 이다.
      그것을 0.0 으로 내보내면 U1 의 "오탐률 월 하락" 이 **판정을 안 하기만 해도** 달성된다
      — 지표가 지표를 죽이는 모양이다 (D-290: 없는 것과 실패한 것을 같은 값으로 두지 않는다).
    """

    since: datetime
    until: datetime
    #: 분자 — 사람이 **기각**한 이벤트 수.
    rejected: int
    #: 분모 — 사람이 **판정한** 이벤트 수 (확인 + 기각). 미판정(new)은 분모가 아니다.
    reviewed: int
    #: 아직 판정되지 않은 이벤트 수. 분모 밖이지만 **보이게 둔다** —
    #: 이 수가 크면 위의 비율은 표본이 얇다는 뜻이다.
    unreviewed: int = 0
    #: ★ 종료(closed)되며 판정이 지워진 이벤트 수. P-K6-1 이 열려 있는 동안 0 이 아니다.
    #:   숨기지 않는다 — 이 수만큼 분모가 실제보다 작다.
    verdict_lost_to_close: int = 0

    @property
    def rate(self) -> float | None:
        if self.reviewed <= 0:
            return None
        return self.rejected / self.reviewed


@dataclass(frozen=True)
class FalsePositiveRate:
    """`false_positive_rate` 의 결과 — F-14(월간 리포트)와 U1(추이)이 **같은 것을 본다**.

    DA-04 K6: *"같은 `status` 필드가 월간 리포트(F-14)와 추이 지표(U1)와 과금 근거(U4)를
    동시에 먹인다. **집계 경로를 하나로 유지하는 것 자체가 요구사항이다.**"*

    그래서 전체 창과 월별 칸을 **한 번의 집계**에서 함께 낸다. 두 번 세면 두 숫자가 나오고,
    갈린 숫자는 고객 앞에서 못 쓴다.
    """

    total: RateWindow
    #: 월별 칸 (`bucket="month"` 일 때만 채워진다). U1 의 "월 하락" 이 이것을 본다.
    buckets: tuple[RateWindow, ...] = field(default_factory=tuple)
    #: 어떤 필터로 잰 것인가 — 보고서에 그대로 실어 **모수를 함께 적게** 한다 (D-271).
    filters: dict = field(default_factory=dict)

    @property
    def is_measurable(self) -> bool:
        """이 수치를 보고에 쓸 수 있는가. 분모가 0 이면 **쓸 수 없다.**"""
        return self.total.reviewed > 0
