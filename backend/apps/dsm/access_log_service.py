# -*- coding: utf-8 -*-
"""DSM-U5-02 — **접속기록 전용 조회·CSV** (`GET /api/dsm/access-log[/export.csv]`) ·
차선 N1 · 턴 AL (P-356 ⑤).

설계는 이미 서 있다 — 이 파일은 그 설계를 코드로 옮길 뿐이다
--------------------------------------------------------------
`docs/design/GX-LAW-09_접속기록_설계_v1.0.md` §4~5(턴 AE · 차선 S)가 실측으로 갈라
둔 것을 그대로 잇는다:

  · 대표 결정 ⑤(턴 Z)는 접속 로그(`db`·`jwt`·`application`·`security`·`user_update`)를
    **일반 감사 화면**(`apps/dsm/api_u24.py::audit_read`)에서 뺐다 — 계정+IP 평문이
    98% 의 요청 로그 밑에 묻히고 누출도 됐기 때문이다. **그 결정은 안 건드린다**
    (`apps.dsm.audit.READABLE_LOGGER_NAMES` 는 그대로다).
  · GX-LAW-09 §5-2 가 못박은 다음 손: 「권한을 좁힌 전용 화면(U5 시스템관리자만,
    계정+IP 마스킹 없이 원문 그대로, 그러나 그 화면 접근 자체도 감사)」— **이 파일이
    그 화면의 뒷면**이다. 일반 감사 화면과 이 화면은 **다른 문**이고, 여는 사람도
    다르다(`apps.dsm.audit.access_log_denial` — 팀장·읽기전용은 여기 못 들어온다).

★ **새 표를 만들지 않는다** — `logger.AuditLogs` 는 이미 다섯 채널을 쌓고 있다
  (§1 실측). 이 파일이 여는 것은 **읽는 좁은 문**이지 새 수집기가 아니다.

★ **ORM 은 여기 없다** — 질의는 `apps/dsm/audit.py`(감사 표 전담 · AppStaysThinTest
  가 이름으로 예외를 둔 파일)에 두고, 이 파일은 ①문지기(권한) ②「그 화면 접근 자체를
  감사」 둘만 한다. 두 번째가 GX-LAW-09 §5-2 의 핵심 조건이다 — 조회 자체가 기록이
  안 되면 「누가 접속기록을 봤는가」를 다시 아무도 답 못 한다(이 표의 존재 이유
  그 자체를 이 화면이 스스로 어기는 모순).
"""
from __future__ import annotations

from typing import Any

from apps.dsm import audit
from common import audit_writer
from common.tenant_scope import TenantScope

#: 이 화면 접근 자체를 남기는 감사 채널. **일반 감사 화면에 안 뜬다**
#: (`apps.dsm.audit.READABLE_LOGGER_NAMES` 에 없는 이름) — 이 화면을 보는 사람 수가
#: 원래도 적어야 한다는 GX-LAW-09 §3② 판단과 같은 결을 따른다. 필요하면 나중에
#: 그 목록에 이름으로 추가한다(지금은 추가하지 않는다 — 대표 결정 ⑤ 재검토는
#: 이 턴의 몫이 아니다).
LOGGER_NAME = "guardianx.u5.access_log_read"
TAG = "[U5-ACCESS-LOG]"


class AccessLogDenied(Exception):
    """이 계정은 접속기록을 볼 수 없다 — 사람의 말로 담는다."""


def read(*, scope: TenantScope, since=None, until=None, actor_id: int | None = None,
         page: int = 1, page_size: int = 50) -> dict[str, Any]:
    """DSM-U5-02 조회 — 권한이 없으면 `AccessLogDenied`.

    Raises:
        AccessLogDenied: 시스템관리자·테넌트관리자·전역관리자가 아니다.
        ValueError: `page`·`page_size` 계약 밖(`audit.read_access_log_page` 가 던진다).
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    actor = scope.require_actor()
    denial = audit.access_log_denial(actor)
    if denial:
        raise AccessLogDenied(denial)
    payload = audit.read_access_log_page(
        scope=scope, since=since, until=until, actor_id=actor_id,
        page=page, page_size=page_size)
    audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action="access_log:read", outcome=audit_writer.ALLOWED,
        reason=f"접속기록 조회 — {payload['total']}건 중 {len(payload['items'])}건 열람",
        api_method="GET",
    )
    return payload


def read_csv(*, scope: TenantScope, since=None, until=None,
            actor_id: int | None = None, limit: int = 1000) -> str:
    """DSM-U5-02 CSV — 같은 문지기 · 같은 질의 함수(화면과 파일이 다른 질의를 안 탄다).

    Raises:
        AccessLogDenied: 시스템관리자·테넌트관리자·전역관리자가 아니다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    actor = scope.require_actor()
    denial = audit.access_log_denial(actor)
    if denial:
        raise AccessLogDenied(denial)
    text = audit.access_log_csv(
        scope=scope, since=since, until=until, actor_id=actor_id, limit=limit)
    audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action="access_log:export_csv", outcome=audit_writer.ALLOWED,
        reason="접속기록 CSV 내보내기", api_method="GET",
    )
    return text
