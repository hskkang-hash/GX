# -*- coding: utf-8 -*-
"""K5 신뢰 커널 — **공개 면은 서비스 함수다** (DA-04 §1-4).

DA-04 가 정의한 K5 는 격리·감사·저하 운전이었고, 그 대부분은 `common/` 에 산다
(`tenant_roles` · `tenant_filters` · `api_contract`). 2026-09-06 에 **표 둘**이 붙었다:

    표 ①  임계값(Threshold)          — `thresholds.py` 정의 + DB 덮어쓰기·이력
    표 ②  자격증명 저장처(Credential) — `credentials.py` 선언 + DB 사실
    표 ③  등급규칙(GradeRule)         — `grade_rules.py`. 정의는 배선에, 값은 DB
                                       (2026-09-10 · D-368 · F-04 무재기동 반영)
    (2026-09-10 추가 · D-367)
    들어오는 키(InboundKey)          — `inbound_keys.py` 발급·폐기·회전·목록.
                                       **표가 아니다** — dj-core 의 표를 감싼 면이다

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
from kernels.k5_trust.grade_rules import (  # noqa: F401
    SEVERITY_ORDER,
    GradeRuleNotDefined,
    GradeRuleView,
    SeverityNotInContract,
    grade_rule_history,
    list_grade_rules,
    set_grade_rule,
    severity_for,
)
from kernels.k5_trust.inbound_keys import (  # noqa: F401
    DEFAULT_EXPIRES_DAYS,
    INBOUND_API_TYPE,
    inbound_key_facts,
    InboundKeyNotFound,
    InboundKeyView,
    IssuedKey,
    issue_key,
    list_keys,
    revoke_key,
    rotate_key,
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
    # ★ 표 ③ 등급규칙 — F-12 「등급규칙」 · F-04 「무재기동 반영」 (D-368)
    "severity_for",
    "list_grade_rules",
    "set_grade_rule",
    "grade_rule_history",
    "SEVERITY_ORDER",
    "GradeRuleView",
    "GradeRuleNotDefined",
    "SeverityNotInContract",
    # ★ 들어오는 키 — 발급·폐기·회전·목록 (D-367 · 계약 F-05 · F-12)
    #   표 ②(나가는 키)와 **같은 어휘, 다른 방향**이다. 한 표에 두지 않는 이유는
    #   inbound_keys.py 머리에 있다 (D-337).
    "issue_key",
    "revoke_key",
    "rotate_key",
    "list_keys",
    "INBOUND_API_TYPE",
    "DEFAULT_EXPIRES_DAYS",
    "inbound_key_facts",
    "InboundKeyView",
    "IssuedKey",
    "InboundKeyNotFound",
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
