# -*- coding: utf-8 -*-
"""UX-45 현장 사진 — **검증 규칙만** 잰다 (`apps/dsm/field.py::validate_upload`).

왜 저장까지 안 재는가
----------------------
`dsm_field_photo` 모델이 아직 없다(F-DB 차선 · WO-01 §5 신규 테이블 7 · 2026-09-15
턴 Q 실측: `backend/apps/dsm/migrations/` 디렉터리 자체가 없다). 저장·테넌트 격리·
익명 401 은 그 모델과 라우트가 서야 잴 수 있는 것이고, 지금 시험이 있는 척 만들면
「모델도 없는데 격리를 통과했다」는 거짓 초록이 된다(D-327의 이웃).

지금 확정할 수 있는 것은 **바이트를 받기 전에 거절하는 규칙 둘**(크기·형식)뿐이다 —
그래서 이 파일은 그 둘만 잰다. 나머지 넷(테넌트 격리·익명 401 ·저장·라우트 도달)은
`field.py` 머리말의 설계에 이름으로 적혀 있고, 모델이 서면 이 파일 옆에
`test_rule1_anonymous_gets_401` 같은 이름으로(스냅샷 라우트 시험과 같은 형) 채운다.
"""
from __future__ import annotations

from django.test import SimpleTestCase

from apps.dsm.field import (
    ALLOWED_CONTENT_TYPES,
    MAX_BYTES,
    FieldPhotoRejected,
    validate_upload,
)


class FieldPhotoValidationTest(SimpleTestCase):

    def test_a_normal_jpeg_passes(self) -> None:
        """정상 크기의 JPEG 는 통과한다 — 던지지 않는다."""
        validate_upload(content_type="image/jpeg", size_bytes=200_000)

    def test_empty_bytes_are_rejected(self) -> None:
        """0 바이트는 「사진이 아니다」 — 조용히 통과시키지 않는다."""
        with self.assertRaises(FieldPhotoRejected) as caught:
            validate_upload(content_type="image/jpeg", size_bytes=0)
        self.assertIn("비어", str(caught.exception))

    def test_over_the_cap_is_rejected(self) -> None:
        """상한을 1바이트라도 넘으면 거절한다 — 「대략」이 아니라 정확히 상한이다."""
        with self.assertRaises(FieldPhotoRejected) as caught:
            validate_upload(content_type="image/jpeg", size_bytes=MAX_BYTES + 1)
        self.assertIn("MB", str(caught.exception))

    def test_exactly_the_cap_passes(self) -> None:
        """경계값 — 상한과 같으면 통과한다(초과만 거절한다)."""
        validate_upload(content_type="image/png", size_bytes=MAX_BYTES)

    def test_disallowed_content_type_is_rejected(self) -> None:
        """허용 목록 밖 형식(예: 원본 영상 컨테이너)은 확장자가 아니라 선언된
        content-type 으로 막는다 — 클라이언트가 확장자를 무엇으로 붙이든 통과 못 한다."""
        with self.assertRaises(FieldPhotoRejected) as caught:
            validate_upload(content_type="video/mp4", size_bytes=100)
        self.assertIn("JPEG", str(caught.exception))

    def test_heic_is_not_yet_allowed(self) -> None:
        """HEIC 은 아직 허용 목록에 없다 — 「서버가 못 열어 안 보이는 사진」을
        업로드 시점에 막는다(P-121 이 사진 렌더에서 겪은 것과 같은 실패 모양을
        업로드 쪽에서 먼저 막는다)."""
        self.assertNotIn("image/heic", ALLOWED_CONTENT_TYPES)
        with self.assertRaises(FieldPhotoRejected):
            validate_upload(content_type="image/heic", size_bytes=100)

    def test_allowed_types_are_exactly_three(self) -> None:
        """허용 목록을 **이름으로** 잠근다(D-285 ②) — 늘리는 것도 판단이다."""
        self.assertEqual(
            ALLOWED_CONTENT_TYPES,
            frozenset({"image/jpeg", "image/png", "image/webp"}))
