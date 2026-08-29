# -*- coding: utf-8 -*-
"""K5 접근 감사 — **쓰는 손은 하나다** (`common/audit_writer.py`).

`apps/dsm/audit.py`(F-12)와 같은 표에 쓴다. 커널(L3)은 App(L4)을 import 할 수 없으므로
공용 기록기를 L1(`common`)에 두고 둘이 그것을 부른다. 판정식 복사본 하나가 격리 사고의
원인이었고(D-212), **기록식도 같다** — 한쪽이 규칙을 바꾸면 다른 쪽 집계가 조용히 갈린다.

`logger_name` 이 다른 것이 요점이다. 그것이 "어느 전건인가" 를 가른다.
"""
from __future__ import annotations

import logging

from common import audit_writer
from common.audit_writer import ALLOWED, DENIED, AuditEntry  # noqa: F401  (재수출)

log = logging.getLogger("guardianx.audit.k5")

#: ★ 이 모듈의 함수는 **밑줄로 시작한다** — 커널의 공개 면이 아니기 때문이다.
#:   `scripts/verify_tenant_scope.py` 는 커널 모듈 최상위의 공개 함수마다
#:   `*, scope: TenantScope` 를 요구한다(D-281). 감사 기록기는 **커널 안쪽 부품**이고
#:   부르는 쪽(services)이 이미 scope 를 받아 판정을 마친 뒤에 부른다 —
#:   여기서 scope 를 또 받으면 **판정하는 척하는 인자**가 하나 늘 뿐이다(착시 ①).

#: **이 문자열로 K5 자격증명 접근 전건을 뽑는다.** 이름이 하나여야 "전건" 이 성립한다.
LOGGER_NAME = "guardianx.k5.credentials"

#: 임계값 변경은 F-12 설정 변경이면서 K5 소관이다. 계열을 나눠 둔다 —
#: 섞으면 "자격증명 접근 전건" 을 셀 때 임계값 변경이 딸려 들어온다.
THRESHOLD_LOGGER_NAME = "guardianx.k5.thresholds"


def _credential_access(*, actor, name: str, outcome: str, reason: str) -> AuditEntry:
    """자격증명 **조회 한 번**을 남긴다. 값은 남지 않는다 — 이름과 판정만 남는다."""
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag="[K5-CRED]", actor=actor,
        action=f"read:{name}", outcome=outcome, reason=reason,
    )
    log.info("[K5-CRED] read:%s %s reason=%s", name, outcome, reason)
    return entry


def _threshold_change(*, actor, key: str, outcome: str, reason: str,
                     before=None, after=None) -> AuditEntry:
    """임계값 변경 한 번. `before`/`after` 는 **값**이다 — 자격증명과 달리 비밀이 아니다."""
    entry = audit_writer.write(
        logger_name=THRESHOLD_LOGGER_NAME, tag="[K5-THRESH]", actor=actor,
        action=f"set:{key}", outcome=outcome, reason=reason,
        before=before, after=after,
    )
    log.info("[K5-THRESH] set:%s %s reason=%s", key, outcome, reason)
    return entry


def _entries(*, logger_name: str = LOGGER_NAME, action: str | None = None,
            limit: int = 100) -> tuple[AuditEntry, ...]:
    return audit_writer.read(logger_name=logger_name, action=action, limit=limit)
