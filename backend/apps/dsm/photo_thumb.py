# -*- coding: utf-8 -*-
"""DSM-U3-03 · P-451 — 현장 사진 **축소본 + 워터마크** (턴 AR · 차선 N1).

계약 11조는 **원본** 무반출이다. 문서(상황보고서 ⑨ 첨부)에는 다음만 싣는다.

  * 긴 변 <= 640 px 로 줄인 JPEG 축소본(원본 픽셀을 그대로 옮기지 않는다)
  * 워터마크 한 줄: 기관명 · 사건번호 · 시각 (그림 아래쪽 띠 — 줄여 놓은 그림 **위에** 얹는다)
  * 원본으로 가는 링크 · 객체 키 · 해시는 **0**. EXIF 도 새 이미지라 딸려 오지 않는다.

원본은 서버(MinIO)에만 있다. 이 파일은 저장하지 않는다 — 바이트를 읽어 줄여 돌려줄 뿐이다.
"""
from __future__ import annotations

import base64
import io
import logging

log = logging.getLogger("guardianx.dsm.photo_thumb")

#: P-451 — 축소본 긴 변 상한.
MAX_LONG_SIDE = 640
#: 한 문서에 싣는 축소본 수 — 종이가 사진으로 터지지 않게.
MAX_THUMBS = 4

_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
    "C:/Windows/Fonts/malgun.ttf",
)


def _font(size: int):
    from PIL import ImageFont

    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()          # 한글 글리프가 없을 수 있다 — 환경 문제로 남긴다


def watermark_text(*, org: str, case_no, at) -> str:
    """워터마크 문구 — 기관명 · 사건번호 · 시각. 셋 다 비면 안 된다(빈 워터마크는 표식이 아니다)."""
    stamp = at.strftime("%Y-%m-%d %H:%M") if hasattr(at, "strftime") else str(at)
    return f"{org} · 사건 {case_no} · {stamp}"


def make_thumbnail(data: bytes, *, org: str, case_no, at, max_side: int = MAX_LONG_SIDE) -> bytes:
    """원본 바이트 -> 워터마크가 얹힌 축소 JPEG 바이트. 못 읽으면 예외(호출자가 건너뛴다)."""
    from PIL import Image, ImageDraw

    with Image.open(io.BytesIO(data)) as src:
        img = src.convert("RGB")
    img.thumbnail((max_side, max_side))       # 긴 변 <= max_side · 종횡비 유지 · 키우지 않는다
    text = watermark_text(org=org, case_no=case_no, at=at)
    font = _font(max(12, img.width // 40))
    draw = ImageDraw.Draw(img, "RGBA")
    box = draw.textbbox((0, 0), text, font=font)
    th = box[3] - box[1]
    band_h = th + 10
    draw.rectangle([(0, img.height - band_h), (img.width, img.height)], fill=(0, 0, 0, 150))
    draw.text((6, img.height - band_h + 4), text, font=font, fill=(255, 255, 255, 255))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=80)   # exif 인자 없음 -> 메타데이터 0
    return out.getvalue()


def _read_original(object_key: str) -> bytes | None:
    """`bucket/object` -> 바이트. 저장소가 안 열리면 None(못 쟀다 — 지어내지 않는다)."""
    try:
        from stream_monitors.utils.minio_client import minio_client

        if not getattr(minio_client, "available", False) or minio_client.client is None:
            return None
        bucket, _, name = object_key.partition("/")
        resp = minio_client.client.get_object(bucket, name)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()
    except Exception:                          # noqa: BLE001
        log.warning("photo original read failed", exc_info=True)
        return None


def thumbnails_for_event(event_id: int, *, org: str, at, limit: int = MAX_THUMBS) -> list[str]:
    """이 사건의 현장 사진 축소본을 `data:image/jpeg;base64,...` 로 (최신순 `limit` 장).

    ★ 링크·해시를 만들지 않는다. 읽지 못한 사진은 건너뛴다 — 그 몫은 「N장 중 M장」으로
      종이가 스스로 밝힌다(`incident_report`).
    """
    from django.apps import apps

    Photo = apps.get_model("stream_monitors", "DsmFieldPhoto")
    rows = list(Photo.objects.filter(event_id=event_id).order_by("-id")[:limit])
    out: list[str] = []
    for row in rows:
        raw = _read_original(row.object_key)
        if not raw:
            continue
        try:
            jpg = make_thumbnail(raw, org=org, case_no=event_id, at=at)
        except Exception:                      # noqa: BLE001
            log.warning("thumbnail failed", exc_info=True)
            continue
        out.append("data:image/jpeg;base64," + base64.b64encode(jpg).decode("ascii"))
    return out
