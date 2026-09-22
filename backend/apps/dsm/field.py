# -*- coding: utf-8 -*-
"""M3 현장 회신 — **사진 한 장 올리기** (UX-45 `POST …/field-photo`).

이 파일의 이력 [2026-09-15 턴 Q · 차선 U3]
-------------------------------------------
착수 시점에는 `dsm_field_photo` 모델이 없어 검증(`validate_upload`)만 실재하고 저장은
`NotImplementedError` 였다. **이번 턴 안에 F-DB 차선이 모델을 세웠다**
(`stream_monitors/models.py::DsmFieldPhoto` · `stream_monitors/migrations/0029_v11_tables.py`
· 2026-09-15 실측). 그래서 `save_field_photo` 를 채우고 라우트를 `api_u3.py` 에 건다
— WO §5 「재사용」 규칙대로 **새 저장소 클라이언트를 만들지 않는다**: 스냅샷과 같은
`stream_monitors.utils.minio_client.minio_client` 를 그대로 쓴다.

규칙 넷 — 지시서가 명시한 것 (전부 시험이 있다 · `test_u3_field_photo_route.py`)
--------------------------------------------------------------------------------
    ① **테넌트 격리**   `get_event(event_id, scope=...)` 로 사건이 요청자의 테넌트
       것인지 먼저 확인한다 — 남의 사건이면 404(스냅샷·`field-reply` 와 같은 판정:
       403 이 아니다. 존재 여부도 누출이다).
    ② **크기 상한**   `MAX_BYTES`(8MB) 아래에서만 받는다.
    ③ **형식**   `ALLOWED_CONTENT_TYPES` 안에서만 받는다 — 확장자가 아니라 **선언된
       content-type** 을 본다.
    ④ **익명 401**   `field-reply`·스냅샷과 같은 문지기(`JwtOrInboundKey` + `@tenant_scoped`
       + `scope.require_actor()` — 시스템 스코프는 사진을 올릴 수 없다. 회신은
       계정이 남긴다).

객체 경로 규약 — 스냅샷과 **같은 모양, 다른 접두**
---------------------------------------------------
`snapshot_path`/`EventClip.object_key` 와 같은 `"{bucket}/{object}"` 모양으로 적는다
(`DsmFieldPhoto.object_key` 는 이 모양을 받는 칸이다 — `fetch_snapshot()` 이 그 모양을
읽는 것과 같은 규약이라 나중에 바이트 라우트를 걸 때 파서를 새로 안 만들어도 된다).
접두는 `field-photos/{event_id}/` 다 — 스냅샷은 스트림별(`detections/{stream_id}/…`)인데
이 사진은 **사건별**이다: 스냅샷은 파이프라인이 올려 임자가 스트림이지만, 이 사진은
**사람이 그 사건을 보고** 올리는 것이라 임자가 사건이다.

★ 바이트를 돌려주는 라우트(`GET …/field-photo/{id}`)는 **이번 턴에 걸지 않는다** —
  UX-45 가 요구한 것은 「사진 1장 올리기」이고, 업로드 확인 응답(`photo_id`·크기·형식)
  으로 화면은 「올라갔다」를 알 수 있다. 읽기 문은 M3 가 목록을 그릴 다음 파에서,
  스냅샷 라우트가 지킨 규약(소인 없이는 안 내보낸다 · `inline`)을 그대로 물려 걷는다
  — 지금 서둘러 걸면 그 규약 없이 바이트가 나가는 문이 하나 더 생긴다.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

#: 현장 사진 하나의 상한. LTE 업로드가 3G 예산(WO §5 「모바일」: 3G 에서 M2 ≤ 3초)을
#: 넘기지 않는 크기다 — 카메라 스냅샷(수백 KB급)보다 넉넉히 잡되, 원본 영상이
#: 섞여 들어올 상한은 아니다.
MAX_BYTES = 8 * 1024 * 1024  # 8MB

#: 현장 사람의 손에 있는 기기가 실제로 내는 형식만 받는다. HEIC 은 아직 안 받는다 —
#: 서버가 못 열면 「올렸는데 안 보인다」는 새 사진 실패가 하나 더 생긴다(P-121 의 교훈).
ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

#: 확장자 매핑 — 객체 키에 형식을 남긴다(디버깅 · 브라우저 힌트). 선언되지 않은
#: content-type 은 `validate_upload` 가 이미 막으므로 여기 없는 값은 오지 않는다.
_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}

#: 객체 경로 접두 — 스냅샷(`detections/`)과 다른 이름으로 겹치지 않게 가른다.
PREFIX = "field-photos"


class FieldPhotoRejected(Exception):
    """검증 실패(크기·형식). **사유를 사람의 말로** 담는다 — 호출자가 그대로 화면에 옮길 수 있게."""


class FieldPhotoStorageDown(Exception):
    """MinIO 에 닿지 못했다 — 우리 결함이 아니라 **저장소의 상태**다(스냅샷 라우트의 503 과 같은 판정)."""


def validate_upload(*, content_type: str, size_bytes: int) -> None:
    """규칙 ②·③ 을 확인한다. 통과하면 아무것도 반환하지 않고, 아니면 던진다."""
    if size_bytes <= 0:
        raise FieldPhotoRejected("사진이 비어 있습니다.")
    if size_bytes > MAX_BYTES:
        mb = MAX_BYTES // (1024 * 1024)
        raise FieldPhotoRejected(f"사진이 너무 큽니다 — {mb}MB 이하만 올릴 수 있습니다.")
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise FieldPhotoRejected(
            "이 형식은 올릴 수 없습니다 — JPEG·PNG·WEBP 만 받습니다.")


def _upload_bytes(*, event_id: int, content_type: str, data: bytes) -> str:
    """MinIO 에 올리고 `"{bucket}/{object}"` 를 돌려준다. 못 올리면 던진다.

    ★ `stream_monitors.services.detection_snapshot.upload_snapshot` 과 **같은
      클라이언트**를 쓴다(WO §5 「재사용」) — 연결·타임아웃·재시도 상한을 여기서
      다시 정하지 않는다. 두 벌을 두면 어긋나고 그 어긋남은 아무도 못 본다.
    """
    try:
        from stream_monitors.utils.minio_client import minio_client
    except Exception as exc:  # noqa: BLE001
        raise FieldPhotoStorageDown(
            f"MinIO 클라이언트를 가져오지 못했다: {type(exc).__name__}: {exc}") from exc

    if not getattr(minio_client, "available", False) or minio_client.client is None:
        raise FieldPhotoStorageDown("저장소 연결 안 됨 — MinIO 가 지금 사용 불가 상태다")

    now = datetime.now()
    ext = _EXT.get(content_type, "bin")
    object_name = (f"{PREFIX}/{event_id}/{now.strftime('%Y%m%d')}/"
                   f"{now.strftime('%H%M%S_%f')}_{uuid.uuid4().hex[:8]}.{ext}")
    bucket = minio_client.bucket_name

    import io

    try:
        minio_client.client.put_object(
            bucket, object_name, io.BytesIO(data), len(data), content_type=content_type)
    except Exception as exc:  # noqa: BLE001
        raise FieldPhotoStorageDown(f"업로드 실패: {type(exc).__name__}: {exc}") from exc

    return f"{bucket}/{object_name}"


def save_field_photo(
    *,
    scope: Any,  # TenantScope — 순환 import 를 피해 타입을 못 박지 않는다(D-281 은 지킨다).
    event_id: int,
    content_type: str,
    data: bytes,
) -> dict:
    """현장 사진 한 장을 저장한다. 화면이 그릴 수 있는 값만 돌려준다.

    거절은 넷으로 갈린다(라우트가 상태 코드로 번역한다):
        `Http404`(K1 이 올린다)                남의/없는 사건
        `SystemScopeCannotRead`               요청자 없음(시스템 스코프)
        `FieldPhotoRejected`                  크기·형식 위반
        `FieldPhotoStorageDown`               MinIO 불가
    """
    from django.apps import apps

    from common.tenant_filters import get_user_group
    from apps.dsm.services import event_detail

    # ① 남의 사건이면 여기서 Http404 가 난다 — field_reply 와 같은 문지기 순서.
    # ★ [턴 Q · 조율자] K1 을 **직접** 부르지 않고 `services.event_detail` 을 거친다 —
    #   F-05 의 App 쪽 K1 소비자는 `apps/dsm/services.py` 하나다(`test_f05_event_api.py`
    #   `K1_CONSUMERS` 「유일한 App 소비자」). 문지기는 같은 `get_event` 다.
    event = event_detail(scope=scope, event_id=event_id)

    # ④ 사람이어야 한다 — 시스템 스코프는 여기서 SystemScopeCannotRead 를 올린다.
    actor = scope.require_actor()

    # ②·③ 저장소에 바이트를 밀어 넣기 전에 거절한다.
    validate_upload(content_type=content_type, size_bytes=len(data))

    group = get_user_group(actor)
    if group is None:
        raise FieldPhotoRejected("소속 조직이 없어 사진을 올릴 수 없습니다.")

    object_key = _upload_bytes(event_id=event.event_id, content_type=content_type, data=data)

    DsmFieldPhoto = apps.get_model("stream_monitors", "DsmFieldPhoto")
    #: ★ [실측 2026-09-15] 이 모델의 테넌트 칸은 **`group`(FK)** 이다 — `groups`(M2M)
    #:   가 아니다(`DsmFieldPhoto._meta.get_fields()` 로 직접 확인. `kernels.k1_event`
    #:   가 `_owner_field()` 로 동적 판정하는 것과 같은 불확실성이 dj-core 전역에
    #:   있지만, **이 표는 F-DB 차선이 이번 턴에 새로 만든 것**이라 판정이 필요
    #:   없다 — 만든 쪽의 선언이 정본이다).
    photo = DsmFieldPhoto.objects.create(
        event_id=event.event_id,
        object_key=object_key,
        content_type=content_type,
        size_bytes=len(data),
        group=group,
        #: ISO-03 목적 선언 — 이 행이 왜 생겼는가. `dsm.field_photo` 는 이 파일에서만 쓴다.
        purpose_code="dsm.field_photo",
    )
    return {
        "photo_id": photo.pk,
        "event_id": event.event_id,
        "content_type": photo.content_type,
        "size_bytes": photo.size_bytes,
    }


# ═══════════════════════════════════════════════════════════════════════════
# M3 현장 회신의 **종류**(`kind`) — UX-45 여섯 칸 (2026-09-16 · 턴 S · 차선 U3)
# ═══════════════════════════════════════════════════════════════════════════
#
# 왜 새 표도, 새 칸도, 커널 수정도 아닌가 [판정 · 턴 S]
# -----------------------------------------------------
# 회신은 감사 한 줄이 정본이다(`kernels/k1_event/field_reply.py` 머리말 ③). 거기에
# `kind` 를 담는 길이 셋 있었다:
#
#     ① 커널 시그니처에 `kind` 를 더한다      가장 곧다. 그러나 그 파일은 K1 이고
#                                            이번 턴 U3 의 소유가 아니다 — 같은 턴에
#                                            두 차선이 한 파일을 고치면 충돌하고,
#                                            충돌한 라우트는 라우팅 침묵이 된다.
#     ② App 이 감사 행을 **직접** 쓴다        문지기(`get_event` 404)·길이 검증이
#                                            **두 벌**이 된다. 두 벌은 반드시 갈리고,
#                                            갈리는 쪽은 언제나 거절 경로다(D-212).
#     ③ 저장 문자열에 **정형 접두**를 붙인다  ← 이것으로 갔다.
#
# ③은 설계 1쪽(`U3_M3_시트_설계.md` §1 「지원 요청」)이 이미 후보로 적어 둔 길이다.
# 커널의 문지기·길이 검증·감사 규약을 **한 벌 그대로** 지나고, 저장된 과거 회신은
# 접두가 없으므로 `note` 로 읽힌다 — 새 칸이 「과거가 비어 있다」로 태어나는 문제가
# 없다(`event_timeline` 이 칸 셋을 안 만든 것과 같은 판단).
#
# ⚠ 그래서 **화면은 접두를 보지 않는다.** 라우트가 `kind` 와 깨끗한 `text` 로 갈라
#   내보낸다(`api.py::field_reply` · `field_replies`). 접두가 사람의 자리에 보이면
#   그것은 이 판정의 실패다.
class UnknownReplyKind(Exception):
    """계약 밖의 종류. **422 다** — 문법은 맞고 값이 계약 밖이다(D-290)."""


#: UX-45 M3 시트의 여섯 칸. **이름으로 잠근다**(D-285 ②) — 수가 아니라 이름이다.
#:
#: 각 칸: (사람이 읽는 이름, 본문이 비었을 때 대신 적는 말, 본문이 필수인가)
#:
#: ★ 본문이 필수인 둘(`note`·`false_positive`)에는 **기본 문구가 없다.** 「본 것을
#:   한 줄로」와 「가 보니 아무것도 없었다」는 사람이 적어야 뜻이 있고, 기본 문구를
#:   깔면 아무도 안 적은 회신이 **적은 것처럼** 쌓인다(D-284 의 조용한 판).
#: ★ 나머지 넷에는 기본 문구가 있다 — 그 넷은 **누름 자체가 사실**이다(도착했다 ·
#:   사진을 올렸다 · 지원이 필요하다 · 조치를 끝냈다). 빈 회신을 커널이 거절하므로
#:   (그 규약은 옳다) 누름의 사실을 문장으로 옮기는 것이 이 자리의 일이다.
REPLY_KINDS: dict[str, tuple[str, str, bool]] = {
    "arrived":        ("도착",      "현장에 도착했습니다.", False),
    "photo":          ("사진",      "현장 사진을 올렸습니다.", False),
    "note":           ("한 줄",     "", True),
    "false_positive": ("오탐 사유", "", True),
    "support":        ("지원 요청", "추가 지원을 요청합니다.", False),
    "done":           ("조치 완료", "현장 조치를 마쳤습니다.", False),
}

#: 기본값. 접두가 없는 **과거 회신 전부**가 이것으로 읽힌다 — 「한 줄」이 그 시절의
#: 유일한 종류였으므로 이 기본값은 추측이 아니라 사실이다.
DEFAULT_REPLY_KIND = "note"

#: 저장 문자열의 접두 모양. `[FIELD:support] 인력 2명` 처럼 앞에 붙는다.
_KIND_TAG = "[FIELD:%s]"
_KIND_TAG_RE = re.compile(r"^\[FIELD:([a-z_]{1,32})\]\s?(.*)$", re.DOTALL)

#: 커널이 받는 한 줄의 상한(`kernels/k1_event/field_reply.py::MAX_REPLY_CHARS`).
#:
#: ⚠ **두 벌이다.** 여기서 커널을 import 하지 않는 이유는 F-05 다: K1 의 App 소비자는
#:   `apps/dsm/services.py` **하나**여야 하고(`test_f05_event_api::K1_CONSUMERS`),
#:   이 파일이 커널을 직접 부르면 그 시험이 멈춘다. `drill.py::DRILL_CHANNEL` 이
#:   같은 이유로 `LogChannel.name` 을 두 벌 든 자리와 같은 모양이고, 같은 처방을
#:   쓴다 — **갈리는지는 시험이 본다**(`tests/test_u3_field_reply_kind.py`).
KERNEL_REPLY_CHARS = 500


def normalize_kind(kind: str | None) -> str:
    """종류 이름을 계약 안의 값으로 만든다. 계약 밖이면 **던진다.**

    ★ 모르는 값을 `note` 로 **접지 않는다.** 접으면 화면의 오타 하나가 「지원 요청」을
      조용히 「한 줄」로 바꾸고, 관제 큐의 지원 요청 배지가 영영 안 뜬다 — 그 고장은
      아무 데서도 안 보인다(착시 ⑧ 「조용한 성공」).
    """
    name = (kind or "").strip() or DEFAULT_REPLY_KIND
    if name not in REPLY_KINDS:
        raise UnknownReplyKind(
            f"현장 회신 종류 {name!r} 는 계약 밖입니다. "
            f"쓸 수 있는 것: {', '.join(REPLY_KINDS)}")
    return name


def kind_label(kind: str) -> str:
    """사람이 읽는 이름. 모르는 값은 **그 값 그대로** 돌려준다 — 읽기는 막지 않는다.

    ⚠ 쓰기(`normalize_kind`)와 읽기가 다른 엄격도를 갖는 것은 뜻이 있다: 계약 밖
      값이 저장돼 버린 과거가 있으면 그것을 **보여는 줘야** 고칠 수 있다.
    """
    row = REPLY_KINDS.get(kind)
    return row[0] if row else kind


def compose_reply(*, kind: str, text: str) -> tuple[str, str]:
    """(저장할 문자열, 깨끗한 본문). 커널에 넘기기 **직전**의 모양을 만든다.

    거절 둘 — 둘 다 `FieldReplyRejected` 가 아니라 부르는 쪽이 422 로 옮긴다:
        · 본문이 필수인 종류인데 비었다  → 기본 문구로 채우지 않는다(위 ★)
        · 접두까지 세어 커널 상한을 넘는다 → **잘라 저장하지 않는다**(커널과 같은 규약)
    """
    name = normalize_kind(kind)
    label, fallback, text_required = REPLY_KINDS[name]
    body = (text or "").strip()

    if not body:
        if text_required:
            raise UnknownReplyKind(
                f"「{label}」에는 본문이 필요합니다. 기본 문구로 채우지 않습니다 — "
                f"아무도 안 적은 회신이 적은 것처럼 쌓이기 때문입니다.")
        body = fallback

    prefix = _KIND_TAG % name
    room = KERNEL_REPLY_CHARS - len(prefix) - 1
    if len(body) > room:
        raise UnknownReplyKind(
            f"현장 회신이 {len(body)}자입니다. 「{label}」의 상한은 {room}자 — "
            f"잘라 저장하지 않습니다: 잘린 회신은 뜻이 뒤집힐 수 있습니다.")
    return f"{prefix} {body}", body


def split_reply(stored: str) -> tuple[str, str]:
    """저장된 문자열 → (종류, 사람이 읽는 본문).

    접두가 없으면 `note` 다 — **접두가 생기기 전의 회신 전부**가 그것이다.
    """
    raw = stored or ""
    matched = _KIND_TAG_RE.match(raw)
    if not matched:
        return DEFAULT_REPLY_KIND, raw
    name, body = matched.group(1), matched.group(2)
    if name not in REPLY_KINDS:
        #: 계약 밖 접두는 **본문을 통째로** 돌려준다 — 접두를 떼면 그 사실이 사라진다.
        return name, raw
    return name, body


# ═══════════════════════════════════════════════════════════════════════════
# M1 「처리함」 — 내가 회신한 사건 (턴 T · 차선 U3)
# ═══════════════════════════════════════════════════════════════════════════
#: 회신 감사 행의 이름 — `kernels/k1_event/field_reply.py::LOGGER_NAME · ACTION` 과 **글자가
#: 같아야 한다**(커널 비공개 모듈은 App 이 import 하지 못한다 · D-278).
#: `tests/test_u3_handled_events.py` 가 두 벌이 갈리는 것을 본다.
FIELD_REPLY_LOGGER = "guardianx.dsm.field_reply"
FIELD_REPLY_ACTION = "field_reply"


def handled_events(*, scope, limit: int = 50) -> list[dict]:
    """내가 현장 회신(`field_reply`)을 낸 사건들 — **최근 회신 순**, 사건마다 한 줄.

    회신의 정본은 감사 한 줄이다(`kernels/k1_event/field_reply.py`). 여기서는 **내**
    줄만 읽고(`user_id`), 사건은 커널 `get_event` 문지기를 지나 가져온다 — 남의 사건
    번호가 섞여 있어도(있을 수 없지만) 404 로 빠진다.
    """
    from django.apps import apps

    from apps.dsm import services as _services   # 커널은 services 한 곳만 부른다(F-05 「하나로만」)

    actor = scope.require_actor()
    AuditLogs = apps.get_model("logger", "AuditLogs")
    rows = (AuditLogs._base_manager
            .filter(logger_name=FIELD_REPLY_LOGGER, api_name=FIELD_REPLY_ACTION,
                    user_id=getattr(actor, "pk", None))
            .order_by("-id")[:2000])
    seen: dict[int, dict] = {}
    for row in rows:
        raw = getattr(row, "data_after", None)
        payload = raw if isinstance(raw, dict) else {}
        if isinstance(raw, (str, bytes)):
            try:
                import json

                payload = json.loads(raw) or {}
            except (ValueError, TypeError):
                payload = {}
        event_id = payload.get("event_id")
        if not isinstance(event_id, int) or event_id in seen:
            continue
        seen[event_id] = {
            "last_reply_at": getattr(row, "create_datetime", None)
                             or getattr(row, "created_on", None),
            "last_reply_text": split_reply(str(payload.get("text") or ""))[1][:120],
            "last_reply_kind": split_reply(str(payload.get("text") or ""))[0],
        }
        if len(seen) >= limit:
            break

    out: list[dict] = []
    for event_id, meta in seen.items():
        try:
            e = _services.event_detail(scope=scope, event_id=event_id)
        except Exception:      # noqa: BLE001 — 404(남의 것·지워진 것)는 목록에서 빠진다
            continue
        out.append({
            "event_id": e.event_id, "event_type": e.event_type,
            "severity": e.severity, "status": e.status, "verdict": e.verdict,
            "occurred_at": e.occurred_at, "last_seen_at": e.last_seen_at,
            "stream_monitor_id": e.stream_monitor_id,
            "stream_monitor_name": e.stream_monitor_name,
            "lat": e.lat, "lng": e.lng, "snapshot_path": e.snapshot_path,
            "response_state": e.response_state,
            #: ★ [턴 AC · 차선 U1 · P-220/221] 이 칸이 **빠져 있었다** [실측] —
            #:   「처리함」(내가 현장 회신을 낸 사건)에 훈련·씨앗 사건이 섞여도
            #:   배지 없이 실사건과 같은 카드로 떴다. `events()` 라우트
            #:   (`apps/dsm/api.py:301`)와 같은 함수를 부른다 — 낱말이 두 벌로
            #:   갈리지 않는다.
            "data_source": _services.event_data_source(view=e),
            **meta,
        })
    return out
