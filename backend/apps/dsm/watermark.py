# -*- coding: utf-8 -*-
"""스냅샷 소인 — **저장은 못 막지만 출처는 남긴다** (P-25 · 2026-09-24).

왜 이것이 있나
--------------
계약 11조는 **원본 영상**의 반출을 금지한다. 스냅샷은 원본 영상이 아니라 정지 이미지
1장이고(DA-01 FR-01-3), 화면이 이미 그리고 있는 것이다. 그래서 바이트 라우트를 낸다
— 그러나 브라우저에 뜬 이미지는 누구나 저장할 수 있다.

    막을 수 없는 것을 막는 척하지 않는다. **대신 나간 자리를 남긴다.**

소인은 「누구의 테넌트에서 · 언제 열람한 1장인가」다. 저장된 사진이 나중에 어디서
나오더라도 그 두 가지가 함께 나온다.

★ 글꼴이 없으면 **소인 없이 내보내지 않는다**
---------------------------------------------
한글 글꼴이 없으면 PIL 기본 글꼴은 한글 자리를 **빈칸으로** 그린다. 그러면 소인은
있는데 테넌트명이 없는 이미지가 나가고, 그것은 소인이 아니라 **소인의 모양**이다.
그 자리에서 조용히 통과시키면 「찍혔다」는 거짓말이 남는다(D-284 조용한 성공).
그래서 글꼴을 못 찾으면 예외를 올린다 — 라우트가 500 으로 번역하고, 사유가 함께 나간다.
고치는 법은 한 줄이다: 컨테이너에 `fonts-nanum` (또는 아래 후보 중 하나)를 깐다.
`scripts/verify_snapshot_route.py` 가 이 글꼴의 실재를 함께 잰다 — 3시에 알지 않도록.
"""
from __future__ import annotations

import io
from pathlib import Path

#: 한글을 그릴 수 있는 글꼴 후보. 먼저 찾은 것을 쓴다.
#: ★ 경로를 하나로 못 박지 않는다 — 컨테이너·개발기·운영기의 글꼴 자리가 다르고,
#:   못 박으면 그중 한 곳에서만 소인이 찍힌다.
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/malgun.ttf",
)


class WatermarkFontMissing(RuntimeError):
    """한글 글꼴이 없다 — **배포 결함이다.** 소인 없는 이미지를 내보내는 대신 여기서 멈춘다."""


def find_font_path() -> str:
    """쓸 수 있는 글꼴 경로. 없으면 빈 문자열 — **판정은 부르는 쪽이 한다.**"""
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return ""


def stamp(jpeg_bytes: bytes, text: str) -> bytes:
    """JPEG 아래쪽에 반투명 띠와 소인 한 줄을 그린다.

    Args:
        jpeg_bytes: 저장소에서 읽은 원본 스냅샷.
        text: 소인 문구. 테넌트명과 열람 시각이 들어 있어야 한다 — 그것이 이 함수의 이유다.

    Raises:
        WatermarkFontMissing: 한글 글꼴이 없다.
        OSError / ValueError: 이미지가 아니거나 깨졌다. **원본을 그대로 돌려주지 않는다.**
    """
    from PIL import Image, ImageDraw, ImageFont

    font_path = find_font_path()
    if not font_path:
        raise WatermarkFontMissing(
            "한글 글꼴을 찾지 못해 소인을 찍을 수 없습니다. 소인 없는 스냅샷은 "
            "내보내지 않습니다(P-25). 후보: " + " · ".join(FONT_CANDIDATES))

    image = Image.open(io.BytesIO(jpeg_bytes))
    image.load()                      # 깨진 파일은 **여기서** 터진다 — 그리다가가 아니라
    image = image.convert("RGB")
    width, height = image.size

    # 글자 크기는 폭에 비례한다 — 640px 에서 14px, 1920px 에서 42px.
    size = max(12, int(width * 0.022))
    font = ImageFont.truetype(font_path, size)

    band = min(height, int(size * 1.9))
    top = height - band

    # ★ 원본 위에 **겹친다** — 새 이미지를 만들어 붙이면 그 자리의 그림이 사라지고,
    #   그것은 소인이 아니라 검은 띠다. 잘라 내어 합성한 뒤 그 자리에 되돌린다.
    overlay = Image.new("RGBA", (width, band), (0, 0, 0, 140))
    draw = ImageDraw.Draw(overlay)
    draw.text((int(size * 0.5), int(size * 0.42)), text,
              font=font, fill=(255, 255, 255, 235))
    region = image.crop((0, top, width, height)).convert("RGBA")
    image.paste(Image.alpha_composite(region, overlay).convert("RGB"), (0, top))

    out = io.BytesIO()
    image.save(out, format="JPEG", quality=88)
    return out.getvalue()
