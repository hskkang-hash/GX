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
