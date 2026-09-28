# -*- coding: utf-8 -*-
"""DSM-U4-07 — **영상 열람·제공(반출) 대장** (`POST /api/dsm/video-access-requests` ·
`.../video-access-requests/{id}/approve` · `.../video-access-requests/{id}/provide` ·
`GET .../video-access-requests`) · 차선 N4 · 턴 AM.

명세(§4.4)의 완결 조건은 「대장 항목 100% · 원본 0」이다. 이 절은 개인정보
보호법 §18·§25 가 요구하는 **제3자 제공(수사기관 등) 대장**이고, `LAW-07`
(`apps/dsm/privacy_request.py` — 정보주체 본인의 열람·삭제 청구)과는 **다른
청구인·다른 절차**다(요청자가 수사기관이고 목적·범위·공문번호가 다른 칸이다).
그 파일을 고치지 않는다 — 같은 표를 두 절이 나눠 쓰면 어느 쪽이 전건인지 갈린다
(D-212). 새 `logger_name` 으로 완전히 별도 대장을 연다.

★ **원본 0 은 스키마가 보장한다** — 이 파일의 어느 함수도 영상 파일 경로·바이트를
받는 매개변수가 없다. 「제공했다」는 사실과 시각만 감사에 남는다. **실제 마스킹
파이프라인 실행은 이 절의 범위 밖이다**(N4_promotions.md 의 「무엇이 없는가」
참조 — 이 파일은 대장(who·when·why)을 채우지, 영상 픽셀을 처리하지 않는다).

★ **새 표를 만들지 않는다** — 요청·승인·제공 셋을 감사 세 걸음으로 잇는다
(`cbs_draft_service.py` 와 같은 모양 — 초안·승인·발송 → 요청·승인·제공).
"""
from __future__ import annotations

from typing import Any

from django.utils import timezone

from common import audit_writer
from common.tenant_filters import get_user_group
from common.tenant_scope import TenantScope

LOGGER_NAME = "guardianx.u4.video_access_ledger"
TAG = "[U4-VIDEO-LEDGER]"
SCAN_CAP = 1000

#: **불변 문구** — 어느 제공 기록에도 이 말이 붙는다. 원본 파일 경로를 받는 매개변수
#: 자체가 없으므로(구조로 막는다), 이 문구는 광고가 아니라 사실의 기록이다.
ORIGINAL_NOT_RELEASED = "원본 미반출(마스킹본 제공)"


class VideoAccessRejected(Exception):
    """저장할 수 없다 — 소속 조직이 없다."""


class VideoAccessConflict(Exception):
    """승인 전 제공 · 이미 제공됨 — 409 로 번역된다."""


def _request_action(group_id: int) -> str:
    return f"video_access_request:{group_id}"


def _approve_action(group_id: int, request_id: int) -> str:
    return f"video_access_approve:{group_id}:{request_id}"


def _provide_action(group_id: int, request_id: int) -> str:
    return f"video_access_provide:{group_id}:{request_id}"


def _require_group(scope: TenantScope):
    actor = scope.require_actor()  # 시스템 스코프면 SystemScopeCannotRead
    group = get_user_group(actor)
    if group is None:
        raise VideoAccessRejected(
            "소속 조직이 없어 영상 제공 요청을 저장할 수 없습니다.")
    return actor, group


def create_request(*, scope: TenantScope, requester_org: str, doc_no: str,
                   purpose: str, scope_desc: str,
                   camera_id: int | None = None,
                   event_id: int | None = None) -> dict[str, Any]:
    """`POST /video-access-requests` — 수사기관 등 요청(공문번호·목적·범위) 접수.

    Raises:
        ValueError: `requester_org`·`doc_no`·`purpose` 중 하나라도 비었다.
        VideoAccessRejected: 소속 조직이 없다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    requester_org = (requester_org or "").strip()
    doc_no = (doc_no or "").strip()
    purpose = (purpose or "").strip()
    scope_desc = (scope_desc or "").strip()
    if not requester_org:
        raise ValueError("요청 기관이 비어 있습니다.")
    if not doc_no:
        raise ValueError("공문번호가 비어 있습니다.")
    if not purpose:
        raise ValueError("제공 목적이 비어 있습니다.")

    actor, group = _require_group(scope)
    stamp = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M")
    reason = (f"요청기관={requester_org} · 공문={doc_no} · 목적={purpose} · "
             f"범위={scope_desc or '(미기재)'} · 카메라={camera_id or '(미기재)'} · "
             f"사건={event_id or '(미기재)'} · 접수={stamp}")
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_request_action(group.pk), outcome=audit_writer.ALLOWED,
        reason=reason, api_method="POST",
    )
    return {"request_id": entry.audit_id, "requester_org": requester_org,
            "doc_no": doc_no, "purpose": purpose, "scope_desc": scope_desc,
            "status": "요청"}


def _request_row(group_id: int, request_id: int):
    for e in audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP):
        if e.audit_id == request_id and e.action == _request_action(group_id):
            return e
    return None


def approve_request(*, scope: TenantScope, request_id: int,
                    note: str = "") -> dict[str, Any]:
    """`POST /video-access-requests/{id}/approve` — 승인.

    Raises:
        django.http.Http404: 그런 요청이 없다 · 남의 테넌트다.
        VideoAccessConflict: 이미 승인됐다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    from django.http import Http404

    actor, group = _require_group(scope)
    if _request_row(group.pk, request_id) is None:
        raise Http404("그런 영상 제공 요청이 없습니다.")
    entries = audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP)
    if any(e.action == _approve_action(group.pk, request_id) for e in entries):
        raise VideoAccessConflict(f"요청#{request_id}은 이미 승인됐습니다.")

    stamp = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M")
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_approve_action(group.pk, request_id), outcome=audit_writer.ALLOWED,
        reason=f"요청#{request_id} 승인 — 시각={stamp}" + (f" · {note}" if note else ""),
        api_method="POST",
    )
    return {"request_id": request_id, "approve_id": entry.audit_id, "status": "승인"}


def provide(*, scope: TenantScope, request_id: int,
           method: str = "") -> dict[str, Any]:
    """`POST /video-access-requests/{id}/provide` — 마스킹본 제공 기록.
    **원본 파일을 받지도 내보내지도 않는다**(매개변수 자체가 없다).

    Raises:
        django.http.Http404: 그런 요청이 없다 · 남의 테넌트다.
        VideoAccessConflict: 승인 전이다 · 이미 제공 기록이 있다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    from django.http import Http404

    actor, group = _require_group(scope)
    if _request_row(group.pk, request_id) is None:
        raise Http404("그런 영상 제공 요청이 없습니다.")
    entries = audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP)
    if not any(e.action == _approve_action(group.pk, request_id) for e in entries):
        raise VideoAccessConflict(
            f"요청#{request_id}은 아직 승인되지 않았습니다 — 승인 전에는 제공 기록을 "
            "남길 수 없습니다.")
    if any(e.action == _provide_action(group.pk, request_id) for e in entries):
        raise VideoAccessConflict(f"요청#{request_id}은 이미 제공 기록이 있습니다.")

    stamp = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M")
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_provide_action(group.pk, request_id), outcome=audit_writer.ALLOWED,
        reason=(f"요청#{request_id} 제공 — 경로={method or '(미기재)'} · 시각={stamp} · "
               f"{ORIGINAL_NOT_RELEASED}"),
        api_method="POST",
    )
    return {"request_id": request_id, "provide_id": entry.audit_id, "status": "제공",
            "note": ORIGINAL_NOT_RELEASED}


def list_requests(*, scope: TenantScope, limit: int = 200) -> list[dict[str, Any]]:
    """`GET /video-access-requests` — 대장 전체(최신 먼저), 요청마다 지금 상태.

    Raises:
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        return []
    entries = audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP)
    rows: dict[int, dict[str, Any]] = {}
    for e in entries:
        if e.action == _request_action(group.pk):
            rows.setdefault(e.audit_id, {
                "request_id": e.audit_id, "text": e.reason, "status": "요청"})
    for request_id, row in rows.items():
        if any(e.action == _provide_action(group.pk, request_id) for e in entries):
            row["status"] = "제공"
        elif any(e.action == _approve_action(group.pk, request_id) for e in entries):
            row["status"] = "승인"
    out = sorted(rows.values(), key=lambda r: r["request_id"], reverse=True)
    return out[:limit]
