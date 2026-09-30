# -*- coding: utf-8 -*-
"""P-356/P-358/P-376 · WO-GX-20260925-15 §5 — **DSM-U3-04·U3-03 승격 시험** ·
차선 N1 · 턴 AM.

캐시 처리: 우회/비움/해당 없음 — Django 테스트 클라이언트가 매 시험 새 프로세스로
`cache.clear()` 를 부른다(`test_p356_u4_spec_promotions.py` 와 같은 이유 —
`common/idempotency.py` 가 Redis 캐시에 성공 응답을 잠깐 기억하는데, 창을 안 비우면
같은 시험 파일 안에서 두 번째 요청이 **새 자원 대신 옛 응답**을 받는다).

이 파일이 잰다
--------------
  DSM-U3-04 `POST|GET /api/dsm/hotline` — 상황실 번호·PS-LTE 그룹통화 번호 접수 ·
    가장 최근 접수가 지금 번호 · 다이얼 문자 밖 값은 400 · 둘 다 비면 400 ·
    남의 테넌트 번호는 안 보인다 · 설정 전에는 `configured:false`.
  DSM-U3-03 현장 사진 → 상황보고 **자동** 첨부 — `POST …/field-photo` 로 사진을
    올린 뒤 `GET …/situation-report.docx` 를 받으면 완성된 DOCX 본문에 「현장 사진」
    첨부 줄과 올린 수가 실제로 찍힌다(사람이 옮겨 적지 않는다). MinIO 는 이
    컨테이너에서 안 닿으므로 `apps.dsm.field._upload_bytes` 를 patch 한다
    (`test_u3_field_photo_route.py` 와 같은 이유 — 저장소 가용성이 아니라 우리
    코드의 판단을 잰다).

무엇을 다시 묻지 않나
---------------------
별지 1호 10칸이 전부 있는가는 `test_u24_situation_report.py` 가 이미 잰다 — 여기서는
**⑨ 첨부의 현장 사진 줄이 사진 수를 따라 바뀌는가**만 새로 묻는다.
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from unittest import mock

from django.core.cache import cache
from django.utils import timezone

from common.evidence_guard import allow_evidence_writes
from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

HOTLINE = "/api/dsm/hotline"
FIELD_PHOTO = "/api/dsm/events/{}/field-photo"
SITUATION_DOCX = "/api/dsm/events/{}/situation-report.docx"

UPLOAD_BYTES = "apps.dsm.field._upload_bytes"


def _repo_root() -> Path:
    """`parents[2]` 로 기어오른다 — `test_p356_u4_spec_promotions.py::_repo_root` 와
    같은 계산이다(같은 디렉터리에 쓰는 시험 파일들이 다른 길을 걷지 않는다)."""
    return Path(__file__).resolve().parents[2]


#: P-356 ② — 증거 파일이 사는 자리. **손으로 만들지 않는다** — 아래
#: `EvidenceExportTest` 가 실제로 때린 응답으로 채운다.
EVIDENCE_DIR = _repo_root() / "docs" / "agent" / "evidence" / "SPEC"


class U3AMFixture(DsmFixture):
    """`DsmFixture` + 팀장 계정 하나.

    ★ 상황실 번호 접수·사진 업로드는 `DsmFixture` 의 일반 역할(`dsm_watch_*`)로
      충분하다 — `hotline_service`·`field.py` 어느 쪽도 역할을 가르지 않는다
      (annex §4.2 「현장 대응자」는 세부 직제를 안 못박았다 — 지어내지 않는다).
    ★ 그런데 **완성된 상황보고를 읽는 문**(`GET …/situation-report.docx`)은 다른
      문이다 — `api_u24.py::_report_reader_denial` 이 「관제팀장·지자체 담당관·
      운영자만」으로 좁힌다(감사 읽기와 같은 표, `config.k3_roles.K3_ROLE_MANAGERS`).
      그래서 그 문을 두드리는 시험은 `manager_a`/`manager_b`(role code
      `fire_admin` — `K3_ROLE_MANAGERS` 의 실제 값)를 쓴다.
    """

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        super().setUpTestData()
        from django.apps import apps

        Role = apps.get_model("role", "Role")
        manager_role, _ = Role.objects.get_or_create(
            code="fire_admin", defaults={"role_name": "fire_admin"})
        cls.manager_a = cls._user("u3am_manager_a", cls.group_a, manager_role)
        cls.manager_b = cls._user("u3am_manager_b", cls.group_b, manager_role)

    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self._clear_thread_local()

    def tearDown(self) -> None:
        #: HTTP 를 때린 시험 뒤 스레드에 요청이 남으면 다음 시험의 `objects` 가 빈다
        #: (메모리 「스레드에 남은 요청이 거짓 초록을 만든다」).
        self._clear_thread_local()
        super().tearDown()

    @staticmethod
    def _clear_thread_local() -> None:
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U3-04 PS-LTE 그룹통화 번호 · 상황실 번호
# ═══════════════════════════════════════════════════════════════════════════
class HotlineTest(U3AMFixture):
    def test_both_blank_is_400(self) -> None:
        resp = self.client.post(
            HOTLINE, {"situation_room_phone": "", "pslte_group_call": ""},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(400, resp.status_code, resp.content[:300])

    def test_letters_are_rejected(self) -> None:
        resp = self.client.post(
            HOTLINE, {"situation_room_phone": "상황실입니다"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(400, resp.status_code, resp.content[:300])

    def test_unconfigured_tenant_says_so(self) -> None:
        resp = self.client.get(HOTLINE, **_bearer(self.user_b))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self.assertEqual({"configured": False}, resp.json())

    def test_record_then_get_round_trips_latest(self) -> None:
        first = self.client.post(
            HOTLINE, {"situation_room_phone": "031-120-0000"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, first.status_code, first.content[:300])

        cache.clear()
        second = self.client.post(
            HOTLINE, {"situation_room_phone": "031-120-1111",
                     "pslte_group_call": "*100"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, second.status_code, second.content[:300])

        cache.clear()
        got = self.client.get(HOTLINE, **_bearer(self.user_a))
        self.assertEqual(200, got.status_code, got.content[:300])
        body = got.json()
        self.assertTrue(body["configured"])
        #: ★ 가장 최근 접수가 지금 번호다.
        self.assertEqual("031-120-1111", body["situation_room_phone"])
        self.assertEqual("0311201111", body["situation_room_tel"])
        self.assertEqual("*100", body["pslte_group_call"])

    def test_other_tenant_hotline_is_not_visible(self) -> None:
        self.client.post(
            HOTLINE, {"situation_room_phone": "02-120-9999"},
            content_type="application/json", **_bearer(self.user_a))

        cache.clear()
        theirs = self.client.get(HOTLINE, **_bearer(self.user_b))
        self.assertEqual(200, theirs.status_code)
        self.assertEqual({"configured": False}, theirs.json())


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U3-03 현장 사진 → 보고서 증빙 자동 첨부
# ═══════════════════════════════════════════════════════════════════════════
class FieldPhotoAttachmentTest(U3AMFixture):
    @staticmethod
    def _jpeg() -> bytes:
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile(
            "scene.jpg", b"\xff\xd8\xff\xe0not-a-real-jpeg-but-bytes",
            content_type="image/jpeg")

    def _docx_text(self, resp) -> str:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            return zf.read("word/document.xml").decode("utf-8", "replace")

    def test_report_says_no_photos_before_any_upload(self) -> None:
        event_id = self._event(self.stream_a)
        resp = self.client.get(
            SITUATION_DOCX.format(event_id), **_bearer(self.manager_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        text = self._docx_text(resp)
        self.assertIn("현장 사진", text)
        self.assertIn("올라온 현장 사진이 없습니다", text)

    def test_uploaded_photo_is_automatically_counted_on_the_report(self) -> None:
        #: ★ 업로드는 일반 계정(`user_a`)이 한다 — 사진을 올리는 사람과 완성된
        #:   보고서를 읽는 사람이 **다른 역할**인 것이 현실이다(현장 대응자가 올리고
        #:   팀장이 읽는다). 두 역할을 한 계정으로 합치면 그 갈림이 시험에서 안 보인다.
        event_id = self._event(self.stream_a)

        with mock.patch(UPLOAD_BYTES, return_value="dsm-bucket/field-photos/probe.jpg"):
            up = self.client.post(
                FIELD_PHOTO.format(event_id), {"photo": self._jpeg()},
                **_bearer(self.user_a))
        self.assertEqual(200, up.status_code, up.content[:300])

        cache.clear()
        resp = self.client.get(
            SITUATION_DOCX.format(event_id), **_bearer(self.manager_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        text = self._docx_text(resp)
        self.assertIn("현장 사진", text)
        self.assertIn("1장이 이 사건에 자동 첨부되었습니다", text)
        #: ★ 원본은 안 붙는다 — 그림 0장(계약 11조·`docx_export` 머리말의 약속).
        self.assertNotIn("<w:drawing", text)

    def test_someone_elses_photo_does_not_inflate_my_report(self) -> None:
        """★ 격리 — B 테넌트 사진이 A 테넌트 사건 보고서에 섞이면 안 된다.

        `DsmFieldPhoto` 는 `event_id` 로만 세므로, 이 시험은 **다른 사건**(같은
        테넌트 A, 사진 없음)의 보고서가 A 사건의 사진 수에 영향받지 않는가를 잰다
        (같은 그룹 안에서도 사건별로 갈리는지 — 테넌트 경계 자체는 K1 `get_event`
        가 이미 지킨다, `test_u3_field_photo_route.py` ②).
        """
        photographed = self._event(self.stream_a)
        bare = self._event(self.stream_a)

        with mock.patch(UPLOAD_BYTES, return_value="dsm-bucket/field-photos/probe2.jpg"):
            up = self.client.post(
                FIELD_PHOTO.format(photographed), {"photo": self._jpeg()},
                **_bearer(self.user_a))
        self.assertEqual(200, up.status_code, up.content[:300])

        cache.clear()
        resp = self.client.get(SITUATION_DOCX.format(bare), **_bearer(self.manager_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        text = self._docx_text(resp)
        self.assertIn("올라온 현장 사진이 없습니다", text)


# ═══════════════════════════════════════════════════════════════════════════
# P-356 ② 증거 — `docs/agent/evidence/SPEC/<id>.json` 둘. **손으로 안 적는다** —
# 이 시험이 실제로 때린 응답을 그대로 담는다(Django TestCase · test client · test DB).
# `scripts/verify_spec_dsm.py` 가 이 파일들의 실재·모양을 잰다.
# ═══════════════════════════════════════════════════════════════════════════
class EvidenceExportTest(U3AMFixture):
    def _dump(self, spec_id: str, *, test: str, method: str, path: str,
             req_body, status: int, resp_body, what: str) -> None:
        payload = {
            "id": spec_id,
            "measured_at": timezone.now().isoformat(),
            "measured_by": "django_test_client",
            "test": test,
            "request": {"method": method, "path": path, "body": req_body},
            "response": {"status": status, "body": resp_body},
            "what": what,
        }
        #: ★ `docs/agent/evidence/**` 쓰기는 시험 중 기본으로 막혀 있다
        #:   (`common.evidence_guard`). 이 자리는 **일부러 쓰는 자리**다.
        with allow_evidence_writes(
                "P-356 ② DSM 별표 절 실측 증거 — pytest 가 방금 두드린 HTTP "
                "왕복을 그대로 적는다(손으로 옮기지 않는다)"):
            EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
            out_path = EVIDENCE_DIR / f"{spec_id}.json"
            #: [턴 AO · P-407] 다른 시험(소급 표 채움)이 이 증거 위에 더한
            #: 「제목이 부르는 것 ↔ 있는 것」 표(`title_parts`)는 **보존한다** —
            #: 이 시험은 HTTP 왕복만 다시 적는다. 안 그러면 전량 시험 순서에 따라
            #: 표가 지워져 O 게이트가 옛 승격으로 오판한다(`test_fws_app.py::
            #: _write_evidence` 와 같은 판단).
            if out_path.is_file():
                try:
                    prev = json.loads(out_path.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    prev = {}
                for keep in ():  #: [턴 AQ · P-431 · 차선 Q] 사람 표 키는 json 에 옮기지 않는다 — 정본은 <id>.retro.md
                    if keep in prev:
                        payload[keep] = prev[keep]
            out_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8")

    def test_dump_dsm_u3_04_evidence(self) -> None:
        body = {"situation_room_phone": "031-120-2222", "pslte_group_call": "*911"}
        resp = self.client.post(HOTLINE, body, content_type="application/json",
                                **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self._dump(
            "DSM-U3-04",
            test="tests.test_p356_u3u6_spec_promotions.EvidenceExportTest"
                ".test_dump_dsm_u3_04_evidence",
            method="POST", path=HOTLINE, req_body=body,
            status=resp.status_code, resp_body=resp.json(),
            what="상황실 번호·PS-LTE 그룹통화 번호 접수 1건을 실제로 남겼다 — "
                "완결 조건(「1탭」)은 M2 화면이 이 값을 `tel:` 링크로 그리는 것이고, "
                "번호 자체가 실제로 저장·조회되는 것을 이 왕복이 실측한다. "
                "손으로 지어낸 값 0.")

    def test_dump_dsm_u3_03_evidence(self) -> None:
        from django.core.files.uploadedfile import SimpleUploadedFile

        event_id = self._event(self.stream_a)
        photo = SimpleUploadedFile(
            "scene.jpg", b"\xff\xd8\xff\xe0not-a-real-jpeg-but-bytes",
            content_type="image/jpeg")
        with mock.patch(UPLOAD_BYTES, return_value="dsm-bucket/field-photos/evi.jpg"):
            up = self.client.post(
                FIELD_PHOTO.format(event_id), {"photo": photo}, **_bearer(self.user_a))
        self.assertEqual(200, up.status_code, up.content[:300])

        cache.clear()
        path = SITUATION_DOCX.format(event_id)
        resp = self.client.get(path, **_bearer(self.manager_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            text = zf.read("word/document.xml").decode("utf-8", "replace")
        self.assertIn("1장이 이 사건에 자동 첨부되었습니다", text)

        self._dump(
            "DSM-U3-03",
            test="tests.test_p356_u3u6_spec_promotions.EvidenceExportTest"
                ".test_dump_dsm_u3_03_evidence",
            method="GET", path=path, req_body={},
            status=resp.status_code,
            resp_body={"content_type": resp.get("Content-Type", ""),
                      "byte_length": len(resp.content),
                      "docx_attachment_line_contains_photo_count": True},
            what="현장 사진 한 장을 실제로 올린 뒤(`POST …/field-photo`) 완성된 "
                "상황보고 DOCX(`GET …/situation-report.docx`)의 ⑨ 첨부 칸에 그 수가 "
                "자동으로 찍히는 것을 실측했다(zip 안 word/document.xml 을 직접 "
                "읽었다 — 손으로 옮긴 값이 아니다). 원본 바이트는 응답에 실린 그대로다 "
                "(evidence 파일에는 요약만 담는다 — DOCX 바이너리는 JSON 이 아니다).")
