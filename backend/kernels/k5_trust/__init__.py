# -*- coding: utf-8 -*-
"""K5 신뢰 커널 — **공개 면은 서비스 함수다** (DA-04 §1-4).

DA-04 가 정의한 K5 는 격리·감사·저하 운전이었고, 그 대부분은 `common/` 에 산다
(`tenant_roles` · `tenant_filters` · `api_contract`). 2026-09-06 에 **표 둘**이 붙었다:

    표 ①  임계값(Threshold)          — `thresholds.py` 정의 + DB 덮어쓰기·이력
    표 ②  자격증명 저장처(Credential) — `credentials.py` 선언 + DB 사실

왜 둘 다 K5 인가 (D-325 이행 판정)
----------------------------------
지시서는 표 ①을 "L3 커널" 이라고만 하고 번호를 주지 않았다. 계약 AC 대장이
F-12(수신자·위젯·구역·**임계값**·등급규칙·**API키**)의 커널을 **K5** 로 적고 있고,
표 ①·②가 갚는 절 넷 중 셋이 F-12·F-05 다. **새 커널 번호를 지어내지 않는다**(D-280).

★ 이중 AC — 한 번 개발해서 두 번 판다
-------------------------------------
    계약 (F)  F-02 지점별 기준선 설정 · F-05 API Key 발급·폐기 · F-12 임계값 · F-12 API키
    상품 (U)  U1~U4 상용판이 **같은 표를 쓴다.** 임계값도 자격증명도 재난안전 전용이 아니다.

`__all__` 이 곧 계약이다 — 여기 없는 이름을 App 이 가져오면
`scripts/verify_layers.py` 가 멈춘다. `models` 를 넣고 싶어지는 순간이 커널이 새는
순간이므로 넣지 않는다.
"""
from __future__ import annotations

from kernels.k5_trust.credentials import (  # noqa: F401
    ABSENT,
    PRESENT,
    ROTATED,
    TYPED,
    VERIFIED,
)
from kernels.k5_trust.exceptions import (  # noqa: F401
    CredentialNotDeclared,
    CredentialNotUsable,
    K5Error,
    ScopeNotAvailable,
    ThresholdIsContractFixed,
    ThresholdNotDefined,
    ThresholdNotSet,
)
from kernels.k5_trust.services import (  # noqa: F401
    credential_fact,
    list_credentials,
    list_thresholds,
    refresh_credential,
    resolve_threshold,
    secret_for,
    set_threshold,
    threshold_history,
)

__all__ = [
    # 표 ① 임계값
    "list_thresholds",
    "resolve_threshold",
    "set_threshold",
    "threshold_history",
    # 표 ② 자격증명
    "list_credentials",
    "credential_fact",
    "secret_for",
    "refresh_credential",
    # 상태 5값 (D-328)
    "ABSENT",
    "PRESENT",
    "TYPED",
    "VERIFIED",
    "ROTATED",
    # 거부들 — 없는 것은 없다고 말한다 (D-284)
    "K5Error",
    "ThresholdNotDefined",
    "ThresholdNotSet",
    "ThresholdIsContractFixed",
    "ScopeNotAvailable",
    "CredentialNotDeclared",
    "CredentialNotUsable",
]
