# -*- coding: utf-8 -*-
"""검출 스냅샷 1장을 MinIO 에 올린다 (W2-2 spec · 계약 불변규칙 4).

    W2-2 spec: *"스냅샷 1장을 MinIO 에 저장하고 snapshot_path 에 기록한다."*
    detection-event.md 불변규칙 4: *"스냅샷은 MinIO 에 1장. 원본 프레임을 DB 에 넣지 않는다."*

왜 `minio_client.save_image` 를 쓰지 않나 — **파이프라인에는 요청자가 없다**
--------------------------------------------------------------------------
`MinioClient.save_image` 는 `get_current_request()` 로 요청자를 캐내어
`user_media_file.created_by = request.user` 를 쓴다. gRPC 콜백에는 요청자가 없으므로
그 줄에서 `None.userprofilelink` 로 죽는다. 요청자가 없는 자리에서 요청자를 요구하는
함수를 억지로 부르면, 그 결과는 **가짜 요청자를 만들어 넣는 것**밖에 없다 —
그것이 W0-12 가 고친 "group 없으면 아무 group" 폴백과 같은 병이다.

그래서 **같은 클라이언트를 쓰되 요청자를 요구하지 않는 경로**를 따로 둔다.
연결·타임아웃·재시도 상한은 `MinioClient` 가 이미 정해 둔 것을 그대로 탄다 (C-3.3).

★ 못 올렸으면 **빈 문자열이다. 가짜 경로를 만들지 않는다**
---------------------------------------------------------
있지도 않은 객체를 가리키는 `snapshot_path` 는 "저장했다"는 거짓말이고,
화면은 그 경로를 믿고 깨진 이미지를 띄운다. D-284 가 이름 붙인 **조용한 성공**이다.
못 올리면 `("", 사유)` 를 돌려주고, 사유는 로그와 호출자 양쪽에 남는다.
**이벤트는 그래도 기록된다** — 스냅샷이 없다고 검출을 버리는 것이 더 나쁘다.
"""
from __future__ import annotations

import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

#: 객체 경로 접두. 요청자별(`{group}/{user}/images/…`)이 아니라 **스트림별**로 쌓는다 —
#: 파이프라인에는 사용자가 없고, 이 스냅샷의 임자는 사람이 아니라 스트림이기 때문이다.
PREFIX = "detections"


def upload_snapshot(*, stream_monitor_id: int, jpeg_bytes: bytes,
                    occurred_at: datetime | None = None) -> tuple[str, str]:
    """스냅샷 1장을 올린다.

    Returns:
        `(snapshot_path, reason)` — 성공하면 `("bucket/object", "")`,
        실패하면 `("", 못 올린 사유)`. **둘 중 하나는 반드시 비어 있다.**
        빈 경로에 사유가 없으면 그것은 "안 올렸다"와 "못 올렸다"가 구별되지 않는 상태다.
    """
    if not jpeg_bytes:
        return "", "프레임 바이트가 비었다 — 올릴 것이 없다"

    try:
        from stream_monitors.utils.minio_client import minio_client
    except Exception as exc:  # noqa: BLE001
        return "", f"MinIO 클라이언트를 가져오지 못했다: {type(exc).__name__}: {exc}"

    if not getattr(minio_client, "available", False) or minio_client.client is None:
        # 저장소가 안 뜬 것은 **사실**이다. 그 사실을 경로로 위장하지 않는다.
        return "", ("MinIO 가 사용 불가 상태다(초기화 실패). 스냅샷 없이 이벤트만 기록한다 — "
                    "가짜 경로를 만들지 않는다")

    stamp = (occurred_at or datetime.now())
    object_name = (f"{PREFIX}/{stream_monitor_id}/"
                   f"{stamp.strftime('%Y%m%d')}/{stamp.strftime('%H%M%S_%f')}.jpg")
    bucket = minio_client.bucket_name

    try:
        buf = io.BytesIO(jpeg_bytes)
        # C-3.3 — 타임아웃·재시도 상한은 MinioClient 가 http_client 에 이미 걸어 뒀다.
        # 여기서 다시 정하지 않는다. 두 벌을 두면 어긋나고 그 어긋남은 아무도 못 본다.
        minio_client.client.put_object(
            bucket, object_name, buf, len(jpeg_bytes), content_type="image/jpeg")
    except Exception as exc:  # noqa: BLE001 — 저장소 실패가 검출을 버리게 두지 않는다
        return "", f"업로드 실패: {type(exc).__name__}: {exc}"

    return f"{bucket}/{object_name}", ""


def encode_frame(frame) -> bytes:
    """프레임(ndarray)을 JPEG 바이트로. 실패하면 **빈 바이트** — 예외를 올리지 않는다.

    인코딩 실패로 스트림이 죽으면 안 된다. 빈 바이트는 위에서 "올릴 것이 없다"로 걸린다.
    """
    if frame is None:
        return b""
    try:
        import cv2

        ok, buf = cv2.imencode(".jpg", frame)
        return buf.tobytes() if ok else b""
    except Exception as exc:  # noqa: BLE001
        logger.warning("스냅샷 JPEG 인코딩 실패: %s", exc)
        return b""


# ═══════════════════════════════════════════════════════════════════════════
# 읽는 쪽 — P-25 (2026-09-24)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 왜 여기에 두나. 올린 자리와 읽는 자리가 갈리면 **경로 규약이 둘이 된다** —
#   위 `upload_snapshot` 이 `f"{bucket}/{object_name}"` 로 쓰고, 읽는 쪽이 그 모양을
#   다르게 가정하는 순간 조용히 404 가 난다. 같은 파일에 두어 규약을 한 곳에 묶는다.
#
# ★ 프리사인드 URL 을 만들지 않는다 (11조 · 불변 제약 「무계정 링크 금지」).
#   프리사인드는 **계정 없는 링크**이고, 한 번 새면 우리가 회수할 수 없다.
#   바이트는 우리 라우트를 통해서만 나가고, 그 라우트는 인증과 테넌트를 본다.

def fetch_snapshot(snapshot_path: str) -> tuple[bytes, str]:
    """스냅샷 객체의 바이트를 읽는다.

    Args:
        snapshot_path: `upload_snapshot` 이 기록한 `"{bucket}/{object}"`.

    Returns:
        `(jpeg_bytes, reason)` — 성공하면 `(bytes, "")`, 실패하면 `(b"", 사유)`.
        **둘 중 하나는 반드시 비어 있다** — 위 규약과 같다. 빈 바이트에 사유가 없으면
        「없는 것」과 「못 읽은 것」이 구별되지 않고, 그 둘은 다른 HTTP 상태다.
    """
    path = (snapshot_path or "").strip().lstrip("/")
    if not path:
        return b"", "스냅샷 경로가 비었다 — 이 이벤트에는 저장된 프레임이 없다"
    if "/" not in path:
        return b"", f"스냅샷 경로 «{path}» 에 버킷이 없다 — «버킷/객체» 모양이어야 한다"
    bucket, _, object_name = path.partition("/")

    try:
        from stream_monitors.utils.minio_client import minio_client
    except Exception as exc:  # noqa: BLE001
        return b"", f"MinIO 클라이언트를 가져오지 못했다: {type(exc).__name__}: {exc}"

    # ★ `available` 은 맥박이다(D-412) — 사진이 아니다. 여기서 묻는 값은 **지금**의 값이고,
    #   저장소가 죽어 있으면 그 사실이 그대로 위로 올라가 503 이 된다. 200 을 만들지 않는다.
    if not getattr(minio_client, "available", False) or minio_client.client is None:
        return b"", "저장소 연결 안 됨 — MinIO 가 지금 사용 불가 상태다"

    response = None
    try:
        response = minio_client.client.get_object(bucket, object_name)
        data = response.read()
    except Exception as exc:  # noqa: BLE001
        return b"", f"스냅샷을 읽지 못했다: {type(exc).__name__}: {exc}"
    finally:
        if response is not None:
            try:
                response.close()
                response.release_conn()
            except Exception:  # noqa: BLE001 — 반납 실패가 읽은 바이트를 무르지 않는다
                pass

    if not data:
        return b"", "스냅샷 객체가 0바이트다 — 올라간 적이 없거나 지워졌다"
    return data, ""
