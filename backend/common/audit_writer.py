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
from django.db import transaction

from common import evidence_chain

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
    #: ★ LAW-08 — 이 행이 체인의 어느 자리에 붙었나. 부르는 쪽이 응답·영수증에 실을 수
    #:   있게 값으로 돌려준다. 읽기(`read`)에서는 비어 있다 — 읽을 때 다시 계산하면
    #:   "저장된 값" 과 "계산한 값" 이 같은 이름으로 섞이고, 그 둘이 섞이면 검증이
    #:   자기 자신을 증명하게 된다.
    prev_hash: str = ""
    row_hash: str = ""


def _model():
    # ★ P-202 — 시험 실행이 **운영** 감사표를 가리키면 여기서 선다.
    #   `write` 도 `read` 도 이 문을 지나므로 **묻는 행위까지** 같이 막힌다 —
    #   턴 X 사고의 원인은 「쓰기」가 아니라 「묻기」였다(`evidence_chain` P-202 머리말).
    evidence_chain.guard_audit_db(doing="묻기")
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

    # ★ P-202 — **트랜잭션을 열기 전에** 선다. 아래 `_model()` 에도 같은 그물이
    #   있지만 그것은 이미 잠금 구간 안이다. 여기서 먼저 서야
    #   「쓰기 전에 예외」(fail-closed)가 **글자 그대로** 성립한다 — 운영 DB 에
    #   트랜잭션도 안 열고, advisory lock 도 안 걸고, INSERT 도 안 한다.
    evidence_chain.guard_audit_db(doing="쓰기")

    with transaction.atomic():
        # ★ P-191 / 턴 X — **INSERT 를 잠금 구간 안으로 들인다.** 두 가지가 같이 고쳐진다:
        #
        #   ① **못 이었으면 그 행도 없다.** 전에는 `create` 가 제 트랜잭션에서 먼저
        #      커밋되고 잇기는 그 뒤였다. 그 사이에 실패하면 예외는 제대로 올라가는데도
        #      **두 칸 없는 감사 행 하나가 표에 남았다** — 체인이 시작된 뒤의 행이라
        #      `missing` 으로 잡히고, 한 번의 실패가 **상시 빨강**이 된다. 그리고 그 행은
        #      고칠 수도 없다(과거 행을 손대는 것이 이 체인이 잡으려는 행위 그 자체다).
        #      [실측 2026-09-20 · `tests/test_law08_chain_race.py::WriteIsAllOrNothingTest`
        #       — 고치기 전 `AssertionError: 0 != 1`]
        #
        #   ② **번호와 줄의 순서가 다시 같아진다.** 행 번호는 INSERT 가 시작될 때 나온다.
        #      INSERT 가 잠금 밖이면 6번이 먼저 붙고 2번이 나중에 붙는 일이 흔했고,
        #      그 뒤집힘을 자리표(`__seq__`)가 받아 냈다. 이제 INSERT 도 줄 순서대로
        #      일어나므로 **자리표는 예비가 된다**(지우지 않는다 — 아래 ⚠).
        #
        #   ⚠ 자리표를 **안 지운다.** 자리표 없이 태어난 옛 행이 표에 그대로 있고,
        #     검증은 그 두 세계를 한 줄로 읽어야 한다(`evidence_chain._order_key`).
        #     예비가 된 것과 필요 없어진 것은 다르다.
        #
        #   ⚠ 잠금은 **밖에서 트랜잭션을 열어 준 경우 그 트랜잭션이 끝날 때** 풀린다.
        #     그것은 이 고침이 만든 일이 아니다 — 잇기가 이미 그 자리에서 잠갔다.
        #     여기서 달라진 것은 잠그는 시점이 INSERT **앞**으로 왔다는 것뿐이다.
        evidence_chain.lock_chain()
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
        # ★ LAW-08 — 저장된 그 행을 **곧바로 체인에 잇는다**. 실패는 삼키지 않는다:
        #   이을 수 없으면 예외가 올라가고 이 감사 쓰기 자체가 실패한다(머리말 규약).
        #   체인 없는 감사 행 하나는 나중에 "그때는 원래 없었다" 로 읽히고, 그 변명이 한 번
        #   통하면 체인 전체의 값이 사라진다.
        prev_hash, row_hash = evidence_chain.append_evidence_hash(audit_id=row.pk)

    return AuditEntry(audit_id=row.pk, outcome=outcome, action=action,
                      actor_id=getattr(actor, "pk", None), reason=reason,
                      prev_hash=prev_hash, row_hash=row_hash)


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
