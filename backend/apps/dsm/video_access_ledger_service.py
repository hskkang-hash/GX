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

★ **원본은 여전히 밖으로 안 나간다** — 이 파일의 어느 함수도 원본 파일 **경로**를
받거나 돌려주는 매개변수가 없다. 「제공했다」는 사실과 시각은 감사에 남는다.

★ [턴 AN · P-392 · 차선 N1] **실제 마스킹 파이프라인 실행** 채움 — 턴 AM 은
  「제공했다」는 사실만 남기고 픽셀 처리는 하지 않았다(N4_promotions.md 「실제
  마스킹 파이프라인 실행은 없다」). 이제 `provide()` 가 이미지(base64)를
  같이 받으면 `apps.dsm.privacy_request.mask_jpeg`(LAW-07 이 이미 쓰는 **순수
  함수** — 전면 픽셀화+흐림, `privacy_request.py` 를 고치지 않고 그 함수 하나만
  가져다 쓴다)를 그대로 돌려 **실제로** 마스킹한다. 청구인(LAW-07·정보주체
  본인)과 이 절(수사기관 등 제3자)은 여전히 **다른 대장**이다 — 같은 표를 나눠
  쓰지 않는다는 원래 판단은 그대로 두고, 마스킹 **함수**만 재사용한다(두 벌로
  다시 짜지 않는다 · D-212).
  ★ **결과 바이트·원본 바이트는 응답에도 감사에도 남지 않는다** — 마스킹
  전/후 해시(sha256 앞 12자)와 크기만 남는다(값 자체를 남기면 원본 반출과
  같은 결이 된다). 이미지를 안 보내면 이전과 같다(마스킹 없음 — 문서만).

★ **새 표를 만들지 않는다** — 요청·승인·제공 셋을 감사 세 걸음으로 잇는다
(`cbs_draft_service.py` 와 같은 모양 — 초안·승인·발송 → 요청·승인·제공).

★ [턴 AO · P-407 · 차선 N1] **연간 통계(출력)** 채움 — 턴 AM 은 목록 조회(`list_
  requests`)까지만 열었고, 명세 제목이 부르는 「연간 통계」 산출은 없었다
  (`DSM-U4-07.json` 옛 title_parts 「목록 조회만 있고 연간 집계 배치는 없다」).
  `annual_stats()` 가 **새 표 없이**(`GET /video-access-requests` 와 같은
  감사 이력을 다시 읽는다) 한 해의 요청·승인·제공 건수와 월별 요청 건수를
  집계해 낸다. **저장 시각 칸이 없는 감사 모델**(`audit_writer.read` 가 돌려주는
  `AuditEntry` 에는 시각 칸이 없다 — 머리말 「분류 FK 는 비운다」와 같은 결의
  판단)이라, `create_request`·`approve_request`·`provide` 가 이미 문장에 적어
  둔 `접수=`·`시각=` 스탬프(`YYYY-MM-DD HH:MM`)를 되읽는다
  (`shift_roster_service._parse_reason` 과 같은 방식 — 표를 새로 쪼개지 않고
  이미 있는 감사 문장에서 뽑는다).
"""
from __future__ import annotations

import base64
import hashlib
import re
from typing import Any

from django.utils import timezone

from common import audit_writer
from common.tenant_filters import get_user_group
from common.tenant_scope import TenantScope

#: [턴 AN · P-392] LAW-07 의 마스킹 **함수만** 가져다 쓴다(전면 픽셀화+흐림 —
#: `privacy_request.py` 는 고치지 않는다. 그 파일의 청구 대장·모델은 이 절과
#: 여전히 다른 대장이다 — 재사용은 순수 함수 하나뿐이다).
from apps.dsm.privacy_request import mask_jpeg

LOGGER_NAME = "guardianx.u4.video_access_ledger"
TAG = "[U4-VIDEO-LEDGER]"
SCAN_CAP = 1000

#: **불변 문구** — 어느 제공 기록에도 이 말이 붙는다. 원본 파일 경로를 받는 매개변수
#: 자체가 없으므로(구조로 막는다), 이 문구는 광고가 아니라 사실의 기록이다.
ORIGINAL_NOT_RELEASED = "원본 미반출(마스킹본 제공)"

#: [턴 AO · P-407] `create_request`·`approve_request`·`provide` 가 이미 적어 둔
#: `접수=YYYY-MM-DD HH:MM` · `시각=YYYY-MM-DD HH:MM` 스탬프를 되읽는다.
_STAMP_RE = re.compile(r"(?:접수|시각)=(\d{4})-(\d{2})-\d{2}")


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


def provide(*, scope: TenantScope, request_id: int, method: str = "",
           image_b64: str = "") -> dict[str, Any]:
    """`POST /video-access-requests/{id}/provide` — 마스킹본 제공 기록.
    **원본 파일 경로는 받지도 내보내지도 않는다**(그런 매개변수 자체가 없다).

    ★ [턴 AN · P-392] `image_b64` 를 함께 보내면 **실제로 마스킹 파이프라인을
      돌린다**(`mask_jpeg` — 전면 픽셀화+흐림). 결과·원본 바이트는 어디에도
      남기지 않고, 해시(sha256 앞 12자)와 크기만 감사·응답에 남는다 — 「가렸다」는
      주장이 아니라 「가린 결과가 원본과 다르다」는 실측이다. 비우면 이전과
      같다(마스킹 없음 — 대장 문서만).

    Raises:
        django.http.Http404: 그런 요청이 없다 · 남의 테넌트다.
        VideoAccessConflict: 승인 전이다 · 이미 제공 기록이 있다.
        ValueError: `image_b64` 를 못 읽는다 · 이미지가 아니다 · 마스킹 결과가
            원본과 같다(파이프라인이 실행되지 않은 것과 같은 신호).
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

    masking_applied = False
    masked_sha12 = ""
    masked_bytes = 0
    if image_b64:
        try:
            raw = base64.b64decode(image_b64, validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"image_b64 를 읽을 수 없습니다: {exc}") from exc
        original_sha12 = hashlib.sha256(raw).hexdigest()[:12]
        try:
            masked = mask_jpeg(raw)
        except Exception as exc:  # noqa: BLE001 — 깨진 이미지도 사람의 말로 담는다
            raise ValueError(f"이미지를 마스킹하지 못했습니다: {type(exc).__name__}"
                            ) from exc
        masked_sha12 = hashlib.sha256(masked).hexdigest()[:12]
        if masked_sha12 == original_sha12:
            raise ValueError(
                "마스킹 결과가 원본과 같습니다 — 파이프라인이 실행되지 않았습니다.")
        masking_applied = True
        masked_bytes = len(masked)

    stamp = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M")
    masking_text = (f"마스킹 실행(결과≠원본 · {masked_bytes}B)" if masking_applied
                    else "마스킹 없음(문서만)")
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=_provide_action(group.pk, request_id), outcome=audit_writer.ALLOWED,
        reason=(f"요청#{request_id} 제공 — 경로={method or '(미기재)'} · 시각={stamp} · "
               f"{ORIGINAL_NOT_RELEASED} · {masking_text}"),
        api_method="POST",
    )
    return {"request_id": request_id, "provide_id": entry.audit_id, "status": "제공",
            "note": ORIGINAL_NOT_RELEASED,
            "masking": {"applied": masking_applied, "masked_sha12": masked_sha12,
                       "masked_bytes": masked_bytes}}


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


def annual_stats(*, scope: TenantScope, year: int | None = None) -> dict[str, Any]:
    """DSM-U4-07 「연간 통계(출력)」 — `GET /video-access-requests/annual-stats`.

    제목이 부르는 것은 「제공 실적을 연 단위로 낸다」다. **새 표를 만들지 않고**
    같은 감사 이력(`LOGGER_NAME`)을 연도(`year`, 생략하면 올해)로 걸러 요청·승인·
    제공 건수와 월별 요청 건수를 낸다.

    Raises:
        ValueError: `year` 가 네 자리 연도가 아니다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    actor = scope.require_actor()
    group = get_user_group(actor)
    year_val = int(year) if year is not None else timezone.localtime(
        timezone.now()).year
    if not (1000 <= year_val <= 9999):
        raise ValueError(f"year 는 네 자리 연도여야 합니다: {year_val!r}")

    by_month = {f"{m:02d}": 0 for m in range(1, 13)}
    if group is None:
        return {"year": year_val, "requested": 0, "approved": 0, "provided": 0,
                "by_month": by_month}

    entries = audit_writer.read(logger_name=LOGGER_NAME, limit=SCAN_CAP)
    req_action = _request_action(group.pk)
    appr_prefix = f"video_access_approve:{group.pk}:"
    prov_prefix = f"video_access_provide:{group.pk}:"
    requested = approved = provided = 0
    for e in entries:
        m = _STAMP_RE.search(e.reason or "")
        if not m or int(m.group(1)) != year_val:
            continue
        month = m.group(2)
        if e.action == req_action:
            requested += 1
            by_month[month] = by_month.get(month, 0) + 1
        elif e.action.startswith(appr_prefix):
            approved += 1
        elif e.action.startswith(prov_prefix):
            provided += 1
    return {"year": year_val, "requested": requested, "approved": approved,
            "provided": provided, "by_month": by_month}
