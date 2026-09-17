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


# ═══════════════════════════════════════════════════════════════════════════
# 턴 T (P-164 U24 ②·③) — 사건 행위 감사 채널 + **테넌트로 좁힌 읽기**
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 사건 행위(상급 보고 체크 · 해제)는 F-12 설정 감사와 **다른 `logger_name`** 에 쓴다.
#   `LOGGER_NAME` 은 「F-12 설정 감사 전건」을 세는 이름이다(D-285 ②) — 거기에 사건
#   행위를 섞으면 그 전건이 조용히 늘고, 검수가 세는 수가 바뀐다. 쓰는 손은 여전히
#   `common/audit_writer.write` 하나다(두 벌을 만들지 않는다).
EVENT_LOGGER_NAME = "guardianx.u24.events"
EVENT_TAG = "[U24-EVENT]"

#: 감사 읽기 라우트가 여는 채널. 여기 없는 이름은 그 라우트로 안 나간다 —
#: dj-core 가 같은 표에 쌓는 API 접근 로그 전체가 화면으로 새지 않게 하는 울타리다.
READABLE_LOGGER_NAMES = (LOGGER_NAME, EVENT_LOGGER_NAME)

#: 한 쪽의 상한. 화면 표 한 장이 감당하는 수 — 더 크면 「60초 안 도달」이 먼저 깨진다.
PAGE_SIZE_MAX = 200


def record_event_action(
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
    """사건 행위 감사 한 줄(`EVENT_LOGGER_NAME`). `record()` 와 같은 규약 — 실패는 올라간다."""
    entry = audit_writer.write(
        logger_name=EVENT_LOGGER_NAME, tag=EVENT_TAG, actor=scope.actor,
        action=action, outcome=outcome, reason=reason,
        before=before, after=after,
        api_name=api_name, api_method=api_method, status_http=status_http,
    )
    log.info("[U24-EVENT] %s %s actor=%s reason=%s",
             action, outcome, entry.actor_id, reason)
    return entry


def _tenant_actor_ids(actor) -> "list[int] | None":
    """요청자와 **같은 테넌트**의 사용자 pk 목록. 전역 관리자면 `None`(좁히지 않는다).

    감사 표(`logger.AuditLogs`)에는 group 칸이 없다 — 행의 테넌트는 **행위자의 소속**
    으로만 정해진다. 그래서 테넌트 좁히기는 `user_id ∈ 우리 테넌트 사용자` 다.
    행위자가 없는 행(`user_id` null · 시스템 행위)은 소속을 말할 수 없으므로 테넌트
    사용자에게는 **안 보인다** — 닫는 쪽이 기본값이다(`filter_users_by_group` 과 같은 규약).
    """
    from django.apps import apps

    from common.tenant_filters import filter_users_by_group
    from common.tenant_roles import is_global_admin

    if is_global_admin(actor):
        return None
    CoreUser = apps.get_model("user", "CoreUser")
    qs = filter_users_by_group(CoreUser._base_manager.all(), actor)
    return list(qs.values_list("pk", flat=True))


def read_page(
    *,
    scope: TenantScope,
    since=None,
    until=None,
    actor_id: int | None = None,
    action: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """감사 이력을 **요청자의 테넌트로 좁혀** 한 쪽 낸다 (P-164 U24 ③ · 필터 3 + 쪽).

    `entries()` 와 다른 점은 단 하나 — **여기서는 좁힌다.** `entries()` 는 검수가 「전건」을
    세는 자리라 좁히지 않았고, 그래서 라우트에 직접 노출하지 않았다. 이 함수는 화면에
    나가는 자리이므로 좁히는 판단을 **여기서** 한다(머리말 규약 그대로 — 판단은 라우트
    쪽 몫이고, 이 함수가 그 라우트의 뒷면이다).

    필터 셋: 기간(`since`·`until` — `create_datetime`) · 행위자(`actor_id` — `user_id`) ·
    행위 종류(`action` — `api_name` 앞머리 일치 · 대소문자 무시).
    """
    from common.tenant_filters import get_user_group

    actor = scope.require_actor()
    if page < 1:
        raise ValueError(f"page 는 1 이상이다 — page={page}")
    if not (1 <= page_size <= PAGE_SIZE_MAX):
        raise ValueError(f"page_size 는 1~{PAGE_SIZE_MAX} 다 — page_size={page_size}")

    Model = audit_writer._model()
    qs = Model._base_manager.filter(logger_name__in=READABLE_LOGGER_NAMES)

    allowed_ids = _tenant_actor_ids(actor)
    if allowed_ids is not None:
        if get_user_group(actor) is None:
            qs = qs.none()  # 소속 없는 계정 — 닫는 쪽이 기본값
        else:
            qs = qs.filter(user_id__in=allowed_ids)
    if since is not None:
        qs = qs.filter(create_datetime__gte=since)
    if until is not None:
        qs = qs.filter(create_datetime__lte=until)
    if actor_id is not None:
        qs = qs.filter(user_id=actor_id)
    if action:
        qs = qs.filter(api_name__istartswith=action)

    total = qs.count()
    start = (page - 1) * page_size
    rows = list(qs.order_by("-id")[start:start + page_size])
    items = [
        {
            "audit_id": r.pk,
            "at": r.create_datetime.isoformat() if r.create_datetime else None,
            "channel": r.logger_name,
            "outcome": ALLOWED if r.level_name == "INFO" else DENIED,
            "action": r.api_name or "",
            "method": r.api_method or "",
            "actor_id": r.user_id,
            "actor": r.username or "",
            "reason": r.note or "",
            "status_http": r.status_http,
        }
        for r in rows
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
        "channels": list(READABLE_LOGGER_NAMES),
    }
