# -*- coding: utf-8 -*-
"""FWS-F6-04 — 확산예측 결과 수신(API [미확인] 또는 업로드) (턴 AP · WO-19 ·
차선 N4).

명세 §5.6 F6: 「확산예측 결과 수신(API [미확인] 또는 업로드)」— 둘 중 하나면
된다(「또는」). **API** 경로는 산림과학원 쪽 실제 연동이라 이 턴 범위 밖이다
(WO-19 「외부 실연동은 하지 않는다」→ 증거 JSON 에 `excluded_by: P-428`).
**업로드** 경로는 이 App 층 안에서 완결되는 값 한 걸음이라 여기서 짓는다.

★ 새 판정 문을 만들지 않는다 — 이 사건의 상태(`response_state`·`verdict`)는
  건드리지 않는다. 이 파일이 하는 일은 「그 사건에 확산예측 결과 참조가
  등록됐다」는 사실 한 줄을 남기고 재조회하는 것뿐이다(F3-07 「헬기 요청
  기록」·F5-08 「비행 기록」과 같은 결 — 서류 한 줄, 새 축 없음).
★ 새 표를 만들지 않는다 — `audit_writer` 감사 한 줄이 이 절의 표다.
"""
from django.apps import apps as django_apps
from django.utils import timezone

from common import audit_writer
from common.tenant_scope import TenantScope

from apps.dsm import services as dsm_services

LOGGER_NAME = "guardianx.ap.n4.f6_spread"
TAG = "[AP-N4-F6-SPREAD]"

#: 값 자리표 상한 — 사진·좌표 참조 문자열(F5-08 `airframe_code` 류와 같은 자리).
MAX_REF_CHARS = 500
MAX_NOTE_CHARS = 500

#: 업로드 소스 — 「API [미확인] 또는 업로드」 중 이 파일이 여는 쪽은 업로드뿐이다.
SOURCE_UPLOAD = "upload"


class SpreadResultRejected(Exception):
    """참조 값이 비었거나 너무 길다 — 422 로 번역된다."""


def _action(event_id: int) -> str:
    return f"f6_spread:{event_id}"


def _model():
    return django_apps.get_model("logger", "AuditLogs")


def record_spread_result(*, scope: TenantScope, event_id: int, image_ref: str,
                         arrival_note: str = "") -> dict:
    """`POST .../spread-results` — 확산예측 결과(이미지/좌표 참조 · 화선 도달
    예상 마을별 메모)를 **업로드 경로**로 등록한다.

    Raises:
        django.http.Http404: 그런 사건이 없다 · 남의 테넌트 사건이다.
        SpreadResultRejected: `image_ref` 가 비었거나 너무 길다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 문지기(404·격리)
    image_ref = (image_ref or "").strip()
    if not image_ref:
        raise SpreadResultRejected("image_ref 가 비어 있습니다 — 결과 이미지/좌표 "
                                   "참조 없이는 등록할 수 없습니다.")
    if len(image_ref) > MAX_REF_CHARS:
        raise SpreadResultRejected(f"image_ref 가 {len(image_ref)}자다. 상한은 "
                                   f"{MAX_REF_CHARS}자")
    arrival_note = (arrival_note or "").strip()
    if len(arrival_note) > MAX_NOTE_CHARS:
        raise SpreadResultRejected(f"arrival_note 가 {len(arrival_note)}자다. 상한은 "
                                   f"{MAX_NOTE_CHARS}자")

    actor = scope.require_actor()
    now = timezone.now()
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=_action(event_id),
        outcome=audit_writer.ALLOWED,
        reason=(f"확산예측 결과 업로드 · 사건#{event_id} · 참조={image_ref}"
               + (f" · 도달예상={arrival_note}" if arrival_note else "")),
        after={"event_id": event_id, "source": SOURCE_UPLOAD, "image_ref": image_ref,
              "arrival_note": arrival_note, "uploaded_at": now.isoformat()},
        api_name=_action(event_id), api_method="POST")
    return {"event_id": event_id, "spread_id": entry.audit_id, "source": SOURCE_UPLOAD,
           "image_ref": image_ref, "arrival_note": arrival_note, "uploaded_at": now}


def list_spread_results(*, scope: TenantScope, event_id: int) -> dict:
    """`GET .../spread-results` — 그 사건의 확산예측 결과 전건(최신 먼저).

    Raises:
        django.http.Http404: 그런 사건이 없다 · 남의 테넌트 사건이다.
        common.tenant_scope.SystemScopeCannotRead: 요청자가 없다(시스템 스코프).
    """
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 문지기
    rows = (
        _model()._base_manager
        .filter(logger_name=LOGGER_NAME, api_name=_action(event_id))
        .order_by("-id")[:200]
    )
    out = []
    for r in rows:
        payload = r.data_after if isinstance(r.data_after, dict) else {}
        out.append({"spread_id": r.pk, "source": payload.get("source"),
                   "image_ref": payload.get("image_ref"),
                   "arrival_note": payload.get("arrival_note"),
                   "uploaded_at": payload.get("uploaded_at")})
    return {"event_id": event_id, "results": out, "count": len(out)}
