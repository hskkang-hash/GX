# -*- coding: utf-8 -*-
"""LAW-07 — **열람·삭제 청구: 접수 → 마스킹본 조회 → 회신 기록** (차선 L · 2026-09-05).

대장이 적어 둔 것
-----------------
    [인용 · ga_readiness.yaml LAW-07] 고정형 영상정보처리기기는 정보주체의
    **열람·존재확인 청구**에 답할 법정 의무가 있다 (위반 과태료 3천만~5천만).
    ★ 원본 영상은 여전히 나가지 않는다 — 법이 요구하는 것은 열람·존재 확인이지
      **반출이 아니다**(계약 11조 유지).

그래서 이 파일의 불변은 하나다: **원본은 안 나간다.** 청구인에게 나가는 것은
마스킹본뿐이고, 원본 객체 경로는 응답의 어느 칸에도 실리지 않는다.

★ 왜 새 표를 만들지 않았나 — **실측하고 정했다**
------------------------------------------------
지시는 「모델이 필요하면 어디에 둘지 먼저 실측하고 사유를 적어라」였다. 실측:

  ① `apps/dsm` 은 **Django 앱이 아니다** [`apps/dsm/__init__.py` 머리말 · INSTALLED_APPS
     에 없다]. 여기에 모델을 두려면 설정을 고쳐야 하고, 그 앱 스스로가 「모델이 없기
     때문에 앱이 아니다」라고 적어 두었다.
  ② `stream_monitors` 에 표를 만들면 **함께 고쳐야 하는 공용 자리가 둘**이다:
     `tests/test_tenant_isolation.py` 의 `MODELS` 레지스트리(머지 게이트)와
     `tests/tenant_census.py`(정본 모수). 이번 턴에 차선 넷이 도는데 그 둘은 공용이다.
  ③ 그리고 **이 기록의 성질이 감사다.** 접수·조회·회신은 덧붙이기만 하는 이력이고,
     뒤에서 조용히 고쳐지면 안 되는 종류의 기록이다. `logger.AuditLogs` 에 쓰면
     LAW-08 해시 체인 위에 그대로 얹힌다 — 한 줄을 고치면 뒤가 어긋난다.
     「새 감사 표를 만들지 않는다」는 `apps/dsm/audit.py` 의 판단과 같은 판단이다.

  ⚠ **대가를 적는다 — 법률 검토 대기.** 감사 로그 보존기간 집행
    (`ops-audit-purge-daily` · 기본 90일)이 **이 청구 기록도 지운다.** 청구 대응
    기록을 며칠 보관해야 하는지는 법이 정하는 것이고 우리가 정할 값이 아니다.
    지금은 그 사실을 여기 적어 두는 것까지가 정직이다.

★ 마스킹은 **전면 마스킹**이다 — 얼굴만 고르지 않는다
-----------------------------------------------------
얼굴을 찾아 그 자리만 가리는 선택적 마스킹은 이 저장소에 없다
[실측 2026-09-05 · 얼굴 인식 특징값을 만들지 않는 것이 제품 사양이다 —
`legal_notice.PRODUCT_SPEC`]. 그래서 **이미지 전체**를 픽셀화하고 흐린다.
과하게 가리는 쪽으로 틀렸지 덜 가리는 쪽으로 틀리지 않는다 — 그 방향이 중요하다.
`SELECTIVE_MASKING_READY` 가 그 부재를 상수로 잠가 둔다(저장소 표준 · D-306 계열).

★ 청구인 개인정보 — **처리방침 초안에 없는 항목이 하나 생겼다**
--------------------------------------------------------------
접수에는 청구인의 이름과 연락처가 필요하다. 그런데 GX-LAW-03 초안 §1 수집 항목
표에는 그 항목이 **없다** [실측 2026-09-05]. 나가는 길은 마스킹하지만, 표에 없는
것을 모으기 시작한 사실 자체를 CPO 에게 보고해야 한다 — 처리방침이 조용히 낡는
자리가 정확히 이런 모양이다.
"""
from __future__ import annotations

import io
import logging
import uuid
from datetime import timedelta
from typing import Any

from django.apps import apps
from django.utils import timezone

from common import audit_writer
from common.tenant_filters import require_user_group
from common.tenant_scope import TenantScope

log = logging.getLogger("guardianx.law07.privacy_request")

#: 감사 행의 logger_name. **이 문자열 하나로 청구 대장 전건을 뽑는다.**
LOGGER_NAME = "guardianx.law07.privacy_request"
TAG = "[LAW-07]"

#: 접수 번호의 머리. 사람이 전화로 불러 줄 수 있어야 하므로 짧고 대문자다.
RECEIPT_PREFIX = "GX-PR"

#: 청구의 종류. **우리 말로 적는다** — 화면에 그대로 나가는 값이다.
KIND_ACCESS = "열람"
KIND_DELETE = "삭제"
KINDS = (KIND_ACCESS, KIND_DELETE)

#: 청구의 상태. 「접수」와 「회신 완료」 둘뿐이다 — 세 번째를 만들면 어느 것이
#: 「아직 답 안 한 것」인지 세는 식이 갈린다.
STATUS_ACCEPTED = "접수"
STATUS_REPLIED = "회신 완료"

#: 감사 payload 안에서 이 계열을 가르는 예약 키.
PAYLOAD_KEY = "law07"

#: 행위 이름 셋. 한 청구가 이 셋으로 이어진다.
ACTION_ACCEPT = "law07:accept"
ACTION_VIEW = "law07:masked_view"
ACTION_REPLY = "law07:reply"

#: ★ 선택적(얼굴만) 마스킹 잠금. 거짓인 동안 **전면 마스킹**만 나간다.
SELECTIVE_MASKING_READY: bool = False
SELECTIVE_MASKING_NOT_READY_REASON: str = (
    "얼굴 위치를 찾는 기능이 제품에 없다. 제품 사양이 얼굴 인식 특징값을 만들지 "
    "않기로 못박았기 때문이다. 그래서 이미지 전체를 가린다 — 덜 가리는 쪽으로 "
    "틀리지 않는 것이 이 자리의 규약이다."
)

#: 마스킹본의 최대 가로 폭. 원본 해상도를 그대로 내보내면 「가렸다」의 뜻이 얇아진다.
MASKED_MAX_WIDTH = 320

#: 한 번의 조회가 만드는 마스킹본 상한. 상한 없이 만들면 한 번의 청구가 서버를 문다.
MASKED_ITEM_CAP = 20

#: 청구 조회의 기본 기간(일). 기간을 안 적은 청구를 「전 기간」으로 읽지 않는다 —
#: 전 기간 조회는 청구가 아니라 열람 그 자체가 된다.
DEFAULT_WINDOW_DAYS = 30


# ═══════════════════════════════════════════════════════════════════════════
# 0. 마스킹 — **되돌릴 수 없게 가린다**
# ═══════════════════════════════════════════════════════════════════════════
def mask_jpeg(jpeg_bytes: bytes) -> bytes:
    """이미지 하나를 **전면 마스킹**한다. 순수 함수 — 시험이 이것을 직접 먹인다.

    순서가 요점이다: **먼저 픽셀화하고 그 다음 흐린다.** 흐리기만 하면 되돌리는
    방법이 알려져 있고(디컨볼루션), 픽셀화는 정보를 실제로 버린다.
    마지막으로 폭을 줄여 저장한다 — 버린 정보가 다시 커지지 않게.
    """
    from PIL import Image, ImageFilter

    image = Image.open(io.BytesIO(jpeg_bytes))
    image.load()                       # 깨진 파일은 **여기서** 터진다
    image = image.convert("RGB")
    width, height = image.size

    block = max(8, min(width, height) // 12)
    small = image.resize((max(4, width // block), max(4, height // block)),
                         Image.BILINEAR)
    image = small.resize((width, height), Image.NEAREST)
    image = image.filter(ImageFilter.GaussianBlur(max(4, block // 2)))

    if width > MASKED_MAX_WIDTH:
        ratio = MASKED_MAX_WIDTH / float(width)
        image = image.resize((MASKED_MAX_WIDTH, max(1, int(height * ratio))),
                             Image.BILINEAR)

    out = io.BytesIO()
    image.save(out, format="JPEG", quality=60)
    return out.getvalue()


# ═══════════════════════════════════════════════════════════════════════════
# 1. 대장 — 감사 표 위에 선다
# ═══════════════════════════════════════════════════════════════════════════
def _audit_model():
    return apps.get_model("logger", "AuditLogs")


def _tenant_id(scope: TenantScope) -> int:
    """청구를 접수한 테넌트. **없으면 만들지 않는다** (W0-12).

    소속을 모르는 채로 접수하면 그 청구는 아무의 것도 아니게 되고, 남의 화면에서
    보이거나 아무 화면에서도 안 보인다 — 둘 다 사고다.
    """
    group = require_user_group(scope.require_actor())
    return int(group.pk)


def _new_receipt() -> str:
    """접수 번호. 날짜 + 짧은 무작위. **행 번호를 쓰지 않는다** — 접수 번호로
    남의 청구 번호를 세어 볼 수 있으면 그 번호 자체가 정보다."""
    stamp = timezone.localtime().strftime("%Y%m%d")
    return f"{RECEIPT_PREFIX}-{stamp}-{uuid.uuid4().hex[:6].upper()}"


def _mask_contact(contact: str) -> str:
    """연락처를 **가려서** 낸다. 대장에는 원문이 있고 화면에는 가린 것이 간다."""
    contact = (contact or "").strip()
    if len(contact) <= 4:
        return "*" * len(contact)
    return contact[:3] + "*" * (len(contact) - 6 if len(contact) > 6 else 1) + contact[-3:]


def _rows(*, tenant_id: int | None = None, receipt_no: str = "",
          action: str = "", limit: int = 500) -> list:
    """대장에서 줄을 읽는다. **`_base_manager` 로 읽는다.**

    ⚠ 기본 매니저를 쓰면 요청 스레드에 남은 상태가 결과를 갈아 치운다 —
      이 저장소에서 실제로 「HTTP 를 때린 시험 뒤 objects 가 빈다」가 있었다.
    ⚠ 테넌트로 좁히는 것은 **여기서** 한다. 부르는 쪽이 잊으면 남의 청구가 보인다.
    """
    qs = _audit_model()._base_manager.filter(logger_name=LOGGER_NAME)
    if action:
        qs = qs.filter(api_name=action)
    out = []
    for row in qs.order_by("-id")[:limit]:
        payload = (row.data_after or {}).get(PAYLOAD_KEY) if isinstance(
            row.data_after, dict) else None
        if not isinstance(payload, dict):
            continue
        if tenant_id is not None and payload.get("tenant_id") != tenant_id:
            continue
        if receipt_no and payload.get("receipt_no") != receipt_no:
            continue
        out.append({"audit_id": row.pk, "at": row.created_on, **payload})
    return out


def _write(*, scope: TenantScope, action: str, reason: str, payload: dict) -> int:
    """대장 한 줄. 실패하면 예외가 올라간다 — 남길 수 없으면 그 행위는 없던 것이다."""
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=scope.actor,
        action=action, outcome=audit_writer.ALLOWED, reason=reason[:400],
        before=None, after={PAYLOAD_KEY: payload},
    )
    return entry.audit_id


# ═══════════════════════════════════════════════════════════════════════════
# 2. 접수
# ═══════════════════════════════════════════════════════════════════════════
def accept(*, scope: TenantScope, subject_name: str, contact: str,
           kind: str = KIND_ACCESS, camera_id: int | None = None,
           since=None, until=None, note: str = "") -> dict:
    """청구를 **접수한다.** 접수 번호가 그 자리에서 나온다.

    Raises:
        ValueError: 청구인·연락처·종류가 없다. **빈 접수를 만들지 않는다** —
            연락처 없는 청구는 회신할 수 없고, 회신 못 할 접수는 접수가 아니다.
    """
    subject_name = (subject_name or "").strip()
    contact = (contact or "").strip()
    if not subject_name or not contact:
        raise ValueError("청구인과 연락처가 있어야 접수합니다. "
                         "회신할 수 없는 접수는 접수가 아닙니다.")
    if kind not in KINDS:
        raise ValueError(f"청구 종류는 {' · '.join(KINDS)} 중 하나입니다.")

    tenant_id = _tenant_id(scope)
    now = timezone.now()
    until = until or now
    since = since or (until - timedelta(days=DEFAULT_WINDOW_DAYS))
    receipt_no = _new_receipt()

    payload = {
        "receipt_no": receipt_no,
        "tenant_id": tenant_id,
        "kind": kind,
        "status": STATUS_ACCEPTED,
        "subject_name": subject_name,
        "contact": contact,
        "camera_id": int(camera_id) if camera_id else None,
        "since": since.isoformat(),
        "until": until.isoformat(),
        "note": (note or "").strip()[:500],
        "accepted_at": now.isoformat(),
    }
    audit_id = _write(scope=scope, action=ACTION_ACCEPT,
                      reason=f"열람·삭제 청구 접수 {receipt_no}", payload=payload)
    log.info("[LAW-07] 접수 %s (감사 %s)", receipt_no, audit_id)
    return {**_public(payload), "audit_id": audit_id}


def _public(payload: dict) -> dict:
    """청구 한 건을 **화면이 읽는 모양**으로. 연락처는 가려서 나간다."""
    return {
        "receipt_no": payload.get("receipt_no", ""),
        "kind": payload.get("kind", ""),
        "status": payload.get("status", STATUS_ACCEPTED),
        "subject_name": payload.get("subject_name", ""),
        "contact_masked": _mask_contact(payload.get("contact", "")),
        "camera_id": payload.get("camera_id"),
        "since": payload.get("since"),
        "until": payload.get("until"),
        "note": payload.get("note", ""),
        "accepted_at": payload.get("accepted_at"),
    }


def list_requests(*, scope: TenantScope, limit: int = 100) -> dict:
    """내 테넌트의 청구 목록. **남의 테넌트 청구는 여기 없다.**"""
    tenant_id = _tenant_id(scope)
    accepted = _rows(tenant_id=tenant_id, action=ACTION_ACCEPT, limit=limit)
    replied = {r.get("receipt_no") for r in
               _rows(tenant_id=tenant_id, action=ACTION_REPLY, limit=limit * 4)}
    items = []
    for row in accepted:
        view = _public(row)
        if view["receipt_no"] in replied:
            view["status"] = STATUS_REPLIED
        items.append(view)
    return {
        "items": items,
        "total": len(items),
        #: 아직 회신하지 않은 것. **0건과 「안 셌다」를 가른다** — 화면이 이 수를 쓴다.
        "unanswered": len([i for i in items if i["status"] != STATUS_REPLIED]),
        "kinds": list(KINDS),
    }


def _find(*, scope: TenantScope, receipt_no: str) -> dict:
    """접수 한 건. 없으면 `LookupError` — **남의 것도 「없다」로 답한다.**

    남의 테넌트 청구를 「권한 없음」으로 답하면 그 번호가 **존재한다는 사실**이
    새어 나간다. 없는 것과 남의 것은 밖에서 같은 답이어야 한다.
    """
    tenant_id = _tenant_id(scope)
    rows = _rows(tenant_id=tenant_id, receipt_no=receipt_no,
                 action=ACTION_ACCEPT, limit=500)
    if not rows:
        raise LookupError(f"접수 번호 {receipt_no} 를 찾지 못했습니다.")
    return rows[0]


def replies(*, scope: TenantScope, receipt_no: str) -> list:
    """회신 기록. **덧붙이기만 한다** — 고친 회신은 회신이 아니다."""
    tenant_id = _tenant_id(scope)
    rows = _rows(tenant_id=tenant_id, receipt_no=receipt_no,
                 action=ACTION_REPLY, limit=200)
    return [{"audit_id": r["audit_id"], "at": r.get("replied_at"),
             "text": r.get("text", ""), "outcome": r.get("outcome", "")}
            for r in reversed(rows)]


def detail(*, scope: TenantScope, receipt_no: str) -> dict:
    """청구 한 건 + 회신 기록. 화면의 상세가 이것 하나로 그려진다."""
    row = _find(scope=scope, receipt_no=receipt_no)
    log_rows = replies(scope=scope, receipt_no=receipt_no)
    view = _public(row)
    view["status"] = STATUS_REPLIED if log_rows else STATUS_ACCEPTED
    return {
        "request": view,
        "replies": log_rows,
        #: ★ 화면이 「원본 영상은 제공되지 않습니다」를 **누르기 전에** 그리도록
        #:   서버도 같은 사실을 낸다. 두 곳이 같은 말을 해야 그 말이 규약이 된다.
        "original_video_released": False,
        "masking": {
            "selective_ready": SELECTIVE_MASKING_READY,
            "why_not": "" if SELECTIVE_MASKING_READY
                       else SELECTIVE_MASKING_NOT_READY_REASON,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# 3. 마스킹본 조회 — **원본은 안 나간다**
# ═══════════════════════════════════════════════════════════════════════════
def _events_for(row: dict, *, scope: TenantScope):
    """청구 범위 안의 이벤트. **문지기를 거쳐 좁힌다.**"""
    from django.utils.dateparse import parse_datetime

    from common.tenant_filters import filter_by_group_field

    Event = apps.get_model("stream_monitors", "DetectionEvent")
    qs = filter_by_group_field(Event._base_manager.all(), scope.require_actor())
    since = parse_datetime(row.get("since") or "")
    until = parse_datetime(row.get("until") or "")
    if since:
        qs = qs.filter(occurred_at__gte=since)
    if until:
        qs = qs.filter(occurred_at__lte=until)
    if row.get("camera_id"):
        qs = qs.filter(stream_monitor_id=row["camera_id"])
    return qs.order_by("-occurred_at")


def masked_view(*, scope: TenantScope, receipt_no: str) -> dict:
    """청구인에게 보이는 **마스킹본 목록.**

    ★ 이 응답에는 객체 경로가 **한 칸도 없다.** 그것이 이 함수의 계약이고,
      `test_l_privacy_request.py` 가 응답 전체를 훑어 0건인지 잰다(부작위 시험).
    ★ 소인을 못 찍으면 **이미지를 내보내지 않는다** — 소인 없는 바이트가 나가는
      순간 남는 것은 그림이고 출처는 없다(P-25 의 규약을 그대로 따른다).
    """
    row = _find(scope=scope, receipt_no=receipt_no)
    qs = _events_for(row, scope=scope)
    total = qs.count()

    items = []
    for event in qs[:MASKED_ITEM_CAP]:
        item = {
            "event_id": event.pk,
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            "camera": getattr(getattr(event, "stream_monitor", None), "name", "") or "",
            "masked": True,
            "image": None,
            "why_not": "",
        }
        path = (getattr(event, "snapshot_path", "") or "").strip()
        if not path:
            item["why_not"] = "이 사건에는 저장된 이미지가 없습니다."
            items.append(item)
            continue
        try:
            item["image"] = _masked_data_uri(path, scope=scope, event=event)
        except Exception as exc:                               # noqa: BLE001
            #: 못 만든 것을 **빈 그림으로 그리지 않는다** — 「없다」와 「못 만들었다」는
            #: 다른 사실이고, 청구인에게는 그 차이가 곧 답변의 내용이다.
            item["why_not"] = f"마스킹본을 만들지 못했습니다: {type(exc).__name__}"
        items.append(item)

    _write(scope=scope, action=ACTION_VIEW,
           reason=f"마스킹본 조회 {receipt_no} — {len(items)}건",
           payload={"receipt_no": receipt_no,
                    "tenant_id": row.get("tenant_id"),
                    "viewed": len(items), "matched": total,
                    "viewed_at": timezone.now().isoformat()})

    return {
        "receipt_no": receipt_no,
        "items": items,
        #: 존재 확인의 답. **분모와 함께 낸다** — 「0건」만으로는 「없었다」인지
        #: 「못 봤다」인지 청구인이 구별할 수 없다.
        "matched": total,
        "shown": len(items),
        "capped": total > MASKED_ITEM_CAP,
        "original_video_released": False,
        "masking": {
            "kind": "전면 마스킹",
            "selective_ready": SELECTIVE_MASKING_READY,
            "why_not": "" if SELECTIVE_MASKING_READY
                       else SELECTIVE_MASKING_NOT_READY_REASON,
        },
    }


def _masked_data_uri(path: str, *, scope: TenantScope, event) -> str:
    """원본 1장을 읽어 **마스킹하고 소인을 찍어** 데이터 URI 로 만든다.

    바이트 라우트를 따로 내지 않는 이유: 이미지 주소가 생기면 그 주소가 화면 밖으로
    복사되고, 복사된 주소는 우리 문지기 밖에서 열린다. 값으로 실어 보내면 이 응답을
    받을 수 있는 사람만 볼 수 있다.
    """
    import base64

    from stream_monitors.services.detection_snapshot import fetch_snapshot

    from apps.dsm.watermark import stamp

    data, reason = fetch_snapshot(path)
    if not data:
        raise RuntimeError(reason or "원본을 읽지 못했다")
    masked = mask_jpeg(data)
    text = (f"GuardianX · 마스킹본 · 사건 {event.pk} · "
            f"열람 {timezone.localtime().strftime('%Y-%m-%d %H:%M')}")
    stamped = stamp(masked, text)
    return "data:image/jpeg;base64," + base64.b64encode(stamped).decode("ascii")


# ═══════════════════════════════════════════════════════════════════════════
# 4. 회신 기록
# ═══════════════════════════════════════════════════════════════════════════
def reply(*, scope: TenantScope, receipt_no: str, text: str,
          outcome: str = "") -> dict:
    """회신을 **기록한다.** 보내지는 않는다 — 보내는 자리는 이 제품 밖이다.

    ★ 기록만 하는 것이 정직하다: 우편·전화로 답한 것을 「보냈다」로 적으면 제품이
      하지 않은 일을 했다고 말하게 된다. 여기 남는 것은 **누가 언제 무엇이라고
      답했는가**이고, 그것이 법정 대응에서 요구되는 사실이다.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("회신 내용이 비어 있습니다. 빈 회신은 기록하지 않습니다.")
    row = _find(scope=scope, receipt_no=receipt_no)

    payload = {
        "receipt_no": receipt_no,
        "tenant_id": row.get("tenant_id"),
        "text": text[:2000],
        "outcome": (outcome or "").strip()[:100],
        "replied_at": timezone.now().isoformat(),
    }
    audit_id = _write(scope=scope, action=ACTION_REPLY,
                      reason=f"회신 기록 {receipt_no}", payload=payload)
    log.info("[LAW-07] 회신 %s (감사 %s)", receipt_no, audit_id)
    return {"receipt_no": receipt_no, "audit_id": audit_id,
            "status": STATUS_REPLIED,
            "replies": replies(scope=scope, receipt_no=receipt_no)}
