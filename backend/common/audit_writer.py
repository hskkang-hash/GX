# -*- coding: utf-8 -*-
"""감사 한 줄을 쓰는 **자리 하나** — 판정식도 기록식도 복사하지 않는다 (D-212 계열).

왜 이 파일이 생겼나 (2026-09-06 · D-325 표 ②)
---------------------------------------------
F-12 설정 감사는 `apps/dsm/audit.py` 가 이미 쓰고 있었다. 그런데 K5 자격증명 표(D-325 ②)도
**접근 감사 로그**를 요구한다. 커널(L3)은 App(L4)을 import 할 수 없으므로(계층 역전 금지),
그대로 두면 **같은 표에 같은 모양으로 쓰는 코드가 두 벌**이 된다.

두 벌이 되면 무슨 일이 생기나 — 이 저장소가 이미 겪었다. 판정식 복사본 하나가
격리 사고의 원인이었고(D-212), 그래서 `common/tenant_roles.py` 한 곳만 부른다.
**기록식도 같다.** 한쪽이 `level_name` 규칙을 바꾸면 다른 쪽 집계가 조용히 갈린다.

그래서 쓰는 자리를 여기 하나로 두고, `apps/dsm/audit.py` 와 `kernels/k5_trust/audit.py` 는
**얇은 앞면**만 갖는다. 둘은 `logger_name` 이 다르다 — 그것이 "어느 전건인가" 를 가른다.

무엇을 하지 않나
----------------
· 분류 FK(action·service·command …)는 **비운다.** 그 열거가 무엇을 뜻하는지 모른다(D-280).
· `logger.AuditLogs` 는 dj-core 소유이고 §0.4 금지구역이다 — **모델을 고치지 않는다.**
  우리는 행을 쓸 뿐이다.
· 쓰기 실패를 **삼키지 않는다.** 감사에 남길 수 없으면 그 행위는 일어나지 않는 것이 옳다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.apps import apps

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


def write(
    *,
    logger_name: str,
    tag: str,
    actor,
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

    `tag` 는 메시지 머리에 붙는 표시(`[F-12]` · `[K5-CRED]`)다. 사람이 로그를 눈으로
    훑을 때 어느 계열인지 즉시 갈리게 한다 — 집계는 `logger_name` 이 한다.
    """
    if outcome not in (ALLOWED, DENIED):
        raise ValueError(
            f"outcome={outcome!r} 은 감사 판정이 아니다. 허용: {ALLOWED} · {DENIED}. "
            f"제3의 값을 만들면 '성공·실패 모두' 라는 집계가 갈린다")

    row = _model()._base_manager.create(
        logger_name=logger_name,
        level_name="INFO" if outcome == ALLOWED else "WARNING",
        msg=f"{tag} {action} — {outcome}: {reason}",
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
    return AuditEntry(audit_id=row.pk, outcome=outcome, action=action,
                      actor_id=getattr(actor, "pk", None), reason=reason)


def read(*, logger_name: str, action: str | None = None,
         limit: int = 100) -> tuple[AuditEntry, ...]:
    """감사 이력 조회. **검수에서 "전건" 을 세는 자리**다.

    ⚠ 테넌트로 좁히지 않는다 — 좁히는 판단은 부르는 쪽이 한다.
      여기서 좁히면 "전건" 이 조용히 부분집합이 된다.
    """
    qs = _model()._base_manager.filter(logger_name=logger_name)
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
