# -*- coding: utf-8 -*-
"""K6 오류 계약.

K1 과 같은 형을 쓴다 — App 은 커널마다 다른 예외 계보를 외우지 않아도 된다.

  · 남의 테넌트 것 → `Http404` (`common.tenant_filters` 가 던진다)
  · 입력이 계약을 벗어남 → `InvalidMetricInput` (4xx 로 번역된다)
  · 아직 안 만든 공개 면 → `NotImplementedYet`
"""
from __future__ import annotations


class K6Error(Exception):
    """K6 이 내는 모든 오류의 뿌리."""


class InvalidMetricInput(K6Error):
    """기간·지표 이름이 계약을 벗어난 입력. HTTP 400 으로 번역한다."""


class NotImplementedYet(K6Error):
    """공개 면에 **이름은 있는데 구현이 없는** 것.

    ★ 빈 목록이나 `0.0` 을 돌려주지 않는다. 계측 커널에서 그것은 특히 위험하다 —
      "측정했는데 0 이다"와 "측정하지 않았다"가 같은 화면에 같은 숫자로 나오면,
      **아무도 재지 않은 지표가 좋은 지표로 보고된다.** D-290 이 이름 붙인
      "없는 것과 실패한 것을 같은 값으로 표현하지 않는다"의 계측판이다.
    """
