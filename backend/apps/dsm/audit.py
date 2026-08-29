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
from dataclasses import dataclass
from typing import Any

from django.apps import apps

from common.tenant_scope import TenantScope

log = logging.getLogger("guardianx.audit.settings")

#: 감사 행의 `logger_name`. **이 문자열로 F-12 감사 전건을 뽑는다** —
#: 이름이 하나여야 "전건" 이라는 말이 성립한다 (D-285 ②).
LOGGER_NAME = "guardianx.f12.settings"

#: 감사에 남는 판정 두 가지. 값이 둘뿐인 것이 요점이다 —
#: "시도했다" 만 남기면 막혔는지 통과했는지가 안 남는다.
ALLOWED = "allowed"
DENIED = "denied"


@dataclass(frozen=True)
class AuditEntry:
    """남긴 감사 한 줄. 부르는 쪽이 응답에 실어 보낼 수 있게 값으로 돌려준다."""

    audit_id: int
    outcome: str
    action: str
    actor_id: int | None
    reason: str


def _model():
    return apps.get_model("logger", "AuditLogs")


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
    if outcome not in (ALLOWED, DENIED):
        raise ValueError(
            f"outcome={outcome!r} 은 감사 판정이 아니다. 허용: {ALLOWED} · {DENIED}. "
            f"제3의 값을 만들면 '성공·실패 모두' 라는 AC-12 의 집계가 갈린다")

    actor = scope.actor
    row = _model()._base_manager.create(
        logger_name=LOGGER_NAME,
        level_name="INFO" if outcome == ALLOWED else "WARNING",
        msg=f"[F-12] {action} — {outcome}: {reason}",
        note=reason,
        api_name=api_name or action,
        api_method=api_method,
        status_http=status_http,
        user_id=getattr(actor, "pk", None),
        username=getattr(actor, "username", "") or "",
        # ★ 분류 FK 는 비운다 — 그 열거가 무엇을 뜻하는지 우리가 모른다 (D-280).
        data_before=before,
        data_after=after,
    )
    log.info("[F-12] %s %s actor=%s reason=%s",
             action, outcome, getattr(actor, "pk", None), reason)
    return AuditEntry(audit_id=row.pk, outcome=outcome, action=action,
                      actor_id=getattr(actor, "pk", None), reason=reason)


def entries(*, action: str | None = None, limit: int = 100) -> tuple[AuditEntry, ...]:
    """F-12 감사 이력 조회. **검수에서 "전건" 을 세는 자리**다.

    ⚠ 테넌트로 좁히지 않는다 — 감사 이력은 운영자가 보는 것이고, 좁히는 판단은
      이 함수를 부르는 라우트가 한다. 여기서 좁히면 "전건" 이 조용히 부분집합이 된다.
      이 함수를 라우트에 직접 노출하지 않는 이유이기도 하다.
    """
    qs = _model()._base_manager.filter(logger_name=LOGGER_NAME)
    if action:
        qs = qs.filter(api_name=action)
    return tuple(
        AuditEntry(audit_id=r.pk,
                   outcome=ALLOWED if r.level_name == "INFO" else DENIED,
                   action=r.api_name or "",
                   actor_id=r.user_id,
                   reason=r.note or "")
        for r in qs.order_by("-id")[:limit]
    )
