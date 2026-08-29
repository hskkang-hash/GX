# -*- coding: utf-8 -*-
"""F-12 설정 감사로그 — **성공도 실패도 남는다** (AC-12).

계약 AC-12 원문: *"무권한 계정의 설정 변경 시도가 차단되고, **성공·실패 모두**
감사로그에 남는다."*

실패를 남기지 않으면 무슨 일이 생기나
-------------------------------------
차단은 조용하다. 막힌 요청은 아무 흔적을 남기지 않고, 그러면
**"시도가 없었다" 와 "시도가 막혔다" 가 같은 상태(행 없음)** 가 된다.
그 둘이 같아지면 감사에서 답할 수 있는 질문이 하나 줄어든다 —
"누가 우리 설정을 만지려 했는가". D-290 이 이름 붙인 실패 모양 그대로다.

어디에 남기나 — 새 표를 만들지 않는다
-------------------------------------
`logger.AuditLogs` 가 이미 있다(dj-core). 새 감사 표를 만들면 감사 이력이 두 곳에
쌓이고, 두 곳에 쌓인 이력은 어느 쪽이 전부인지 아무도 모른다.

★ 2026-09-06 — **쓰는 자리는 `common/audit_writer.py` 하나다** (D-325 표 ②).
  K5 자격증명 표도 같은 표에 접근 감사를 남긴다. 커널(L3)은 App(L4)을 import 할 수
  없으므로, 그대로 두면 같은 모양으로 쓰는 코드가 두 벌이 된다. 판정식 복사본 하나가
  격리 사고의 원인이었고(D-212), **기록식도 같다.** 이 파일은 이제 F-12 의 앞면이다 —
  `LOGGER_NAME` 만 다르고 쓰는 손은 하나다.

  ⚠ dj-core 는 §0.4 금지구역(D-207)이다 — **모델을 고치지 않는다.** 우리는 행을
    쓸 뿐이고, FK 분류 열(action·service·command …)은 **비워 둔다.** 그 분류값이
    무엇을 뜻하는지 우리가 모르기 때문이다. 모르는 칸을 그럴듯하게 채우면 그 값이
    나중에 근거처럼 읽힌다 (D-280).

쓰기가 실패하면 — **삼키지 않는다**
-----------------------------------
감사 쓰기가 조용히 실패하면 그때부터 "감사로그 전건" 은 거짓이 되고, 아무도 모른다.
그래서 `record()` 는 예외를 올린다. 부르는 쪽(`guard`)은 그 예외를 잡지 않는다 —
**감사에 남길 수 없으면 그 설정 변경은 일어나지 않는다.**

  이것은 저하 운전(규약 ④)의 예외다. 화재 판정은 메일이 죽어도 살아야 하지만,
  설정 변경은 감사가 죽으면 **하지 않는 것이 옳다.** 둘은 다른 성질의 행위다.
"""
from __future__ import annotations

import logging
from typing import Any

from common import audit_writer
from common.audit_writer import AuditEntry
from common.tenant_scope import TenantScope

log = logging.getLogger("guardianx.audit.settings")

#: 감사 행의 `logger_name`. **이 문자열로 F-12 감사 전건을 뽑는다** —
#: 이름이 하나여야 "전건" 이라는 말이 성립한다 (D-285 ②).
LOGGER_NAME = "guardianx.f12.settings"

#: 감사에 남는 판정 두 가지. `common/audit_writer` 가 정본이고 여기서 이름만 다시 낸다 —
#: 값을 여기서 새로 적으면 두 벌이 되고, 두 벌은 반드시 어긋난다.
ALLOWED = audit_writer.ALLOWED
DENIED = audit_writer.DENIED

#: 메시지 머리 표시. 집계는 `LOGGER_NAME` 이 하고, 이것은 사람이 눈으로 가르는 표시다.
TAG = "[F-12]"


def record(
    *,
    scope: TenantScope,
    action: str,
    outcome: str,
    reason: str,
    before: Any = None,
    after: Any = None,
    api_name: str = "",
    api_method: str = "",
    status_http: int | None = None,
) -> AuditEntry:
    """감사 한 줄을 **실제로 저장한다.** 실패하면 예외가 올라간다.

    `outcome` 은 `ALLOWED` / `DENIED` 둘뿐이다. 자유 문자열을 받으면 다음 사람이
    "attempted" 같은 제3의 값을 넣고, 그러면 전건 집계가 갈린다.
    """
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=scope.actor,
        action=action, outcome=outcome, reason=reason,
        before=before, after=after,
        api_name=api_name, api_method=api_method, status_http=status_http,
    )
    log.info("[F-12] %s %s actor=%s reason=%s",
             action, outcome, entry.actor_id, reason)
    return entry


def entries(*, action: str | None = None, limit: int = 100) -> tuple[AuditEntry, ...]:
    """F-12 감사 이력 조회. **검수에서 "전건" 을 세는 자리**다.

    ⚠ 테넌트로 좁히지 않는다 — 감사 이력은 운영자가 보는 것이고, 좁히는 판단은
      이 함수를 부르는 라우트가 한다. 여기서 좁히면 "전건" 이 조용히 부분집합이 된다.
      이 함수를 라우트에 직접 노출하지 않는 이유이기도 하다.
    """
    return audit_writer.read(logger_name=LOGGER_NAME, action=action, limit=limit)
