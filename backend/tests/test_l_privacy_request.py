# -*- coding: utf-8 -*-
"""LAW-07 — **접수 → 마스킹본 조회 → 회신 기록**, 그리고 원본은 안 나간다 (차선 L).

이 파일이 묻는 것 넷
--------------------
① **한 줄로 이어지는가.** 접수해서 번호가 나오고, 그 번호로 조회하고, 그 번호에
   회신이 남는가. 셋 중 하나라도 끊기면 청구인에게 답할 수 없다.
② ★ **원본 경로가 응답에 0건인가** — 부작위 시험이고, 이것이 초록의 절반이다.
   법이 요구하는 것은 열람·존재 확인이지 **반출이 아니다**(계약 11조 유지).
   응답 어딘가에 객체 경로가 한 줄 실리면 그 순간 무반출 규약이 깨진다.
③ **남의 테넌트 청구가 안 보이는가.** 청구에는 사람 이름과 연락처가 들어 있다.
④ **마스킹이 실제로 정보를 버리는가.** 「가렸다」는 말이 아니라 바이트로 재야 한다.

★ 이 파일이 묻지 **않는** 것 — 회신 기한(10일 등)이 지켜지는가.
  법정 기한은 대조 전이다(GX-LAW-03 초안이 「[확인 — 법정 기한 대조]」로 남겼다).
  없는 기한을 시험이 강제하면 그 수가 곧 계약처럼 읽힌다.
"""
from __future__ import annotations

from django.apps import apps

from tests.test_dsm_app import DsmFixture

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "apps.dsm.privacy_request · apps.dsm.watermark · logger.AuditLogs · "
    "stream_monitors.DetectionEvent — 저장소의 실제 모듈과 표"
)

#: 응답 어디에도 있으면 안 되는 것. **경로를 가리키는 이름과 값 둘 다** 본다.
FORBIDDEN_KEYS = ("snapshot_path", "object_key", "object_path", "clip_path",
                  "bucket", "presigned", "url")
FORBIDDEN_VALUES = ("minio://", "/dsm/", "s3://", ".mp4")


def _walk(node, path="응답"):
    """응답을 **전부** 훑는다. 한 겹만 보면 중첩된 자리에서 새는 것을 못 본다."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield f"{path}.{key}", key, value
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, (list, tuple)):
        for i, value in enumerate(node):
            yield f"{path}[{i}]", "", value
            yield from _walk(value, f"{path}[{i}]")


class OneRequestGoesAllTheWayTest(DsmFixture):
    """① 접수 → 조회 → 회신이 **한 줄로 이어진다.**"""

    def _accept(self):
        from apps.dsm.privacy_request import accept

        return accept(scope=self.scope_a, subject_name="김민수",
                      contact="010-1234-5678", kind="열람",
                      note="정문 앞에서 찍힌 영상")

    def test_accept_returns_a_receipt_number(self):
        got = self._accept()
        self.assertTrue(got["receipt_no"].startswith("GX-PR-"),
                        "접수 번호가 없으면 청구인이 되물을 수 없다")
        self.assertEqual(got["status"], "접수")

    def test_the_contact_is_masked_on_the_way_out(self):
        """연락처 원문은 대장에만 있고 화면에는 가려서 간다."""
        got = self._accept()
        self.assertNotIn("010-1234-5678", str(got))
        self.assertIn("*", got["contact_masked"])

    def test_an_accept_without_a_contact_is_refused(self):
        """★ 회신할 수 없는 접수는 접수가 아니다."""
        from apps.dsm.privacy_request import accept

        with self.assertRaises(ValueError):
            accept(scope=self.scope_a, subject_name="김민수", contact="")

    def test_detail_then_masked_then_reply(self):
        from apps.dsm.privacy_request import detail, masked_view, reply

        receipt_no = self._accept()["receipt_no"]

        first = detail(scope=self.scope_a, receipt_no=receipt_no)
        self.assertEqual(first["request"]["status"], "접수")
        self.assertEqual(first["replies"], [])

        view = masked_view(scope=self.scope_a, receipt_no=receipt_no)
        self.assertEqual(view["receipt_no"], receipt_no)
        #: 존재 확인의 답은 **분모와 함께** 온다 — 0건만으로는 「없었다」인지
        #: 「못 봤다」인지 청구인이 구별할 수 없다.
        self.assertIn("matched", view)

        reply(scope=self.scope_a, receipt_no=receipt_no,
              text="해당 기간 영상 2건을 마스킹본으로 확인해 드렸습니다.")
        after = detail(scope=self.scope_a, receipt_no=receipt_no)
        self.assertEqual(after["request"]["status"], "회신 완료")
        self.assertEqual(len(after["replies"]), 1)

    def test_replies_only_append(self):
        """회신은 **덧붙기만 한다.** 고친 회신은 회신이 아니다."""
        from apps.dsm.privacy_request import detail, reply

        receipt_no = self._accept()["receipt_no"]
        reply(scope=self.scope_a, receipt_no=receipt_no, text="1차 회신")
        reply(scope=self.scope_a, receipt_no=receipt_no, text="2차 회신")
        rows = detail(scope=self.scope_a, receipt_no=receipt_no)["replies"]
        self.assertEqual([r["text"] for r in rows], ["1차 회신", "2차 회신"])

    def test_an_empty_reply_is_not_recorded(self):
        from apps.dsm.privacy_request import reply

        receipt_no = self._accept()["receipt_no"]
        with self.assertRaises(ValueError):
            reply(scope=self.scope_a, receipt_no=receipt_no, text="   ")

    def test_the_whole_trail_is_in_the_audit_log(self):
        """접수·조회·회신 셋이 **감사 표 위에** 남는다 — 뒤에서 못 고친다."""
        from apps.dsm.privacy_request import (
            ACTION_ACCEPT, ACTION_REPLY, ACTION_VIEW, LOGGER_NAME,
            masked_view, reply,
        )

        AuditLogs = apps.get_model("logger", "AuditLogs")
        receipt_no = self._accept()["receipt_no"]
        masked_view(scope=self.scope_a, receipt_no=receipt_no)
        reply(scope=self.scope_a, receipt_no=receipt_no, text="회신했습니다.")

        rows = AuditLogs._base_manager.filter(logger_name=LOGGER_NAME)
        for action in (ACTION_ACCEPT, ACTION_VIEW, ACTION_REPLY):
            self.assertTrue(rows.filter(api_name=action).exists(),
                            f"{action} 가 감사에 안 남았다")


class TheOriginalNeverLeavesTest(DsmFixture):
    """② ★ **원본 경로가 응답에 0건.** 부작위 시험 — 이것이 초록의 절반이다."""

    def setUp(self):
        from apps.dsm.privacy_request import accept

        #: 이 픽스처의 이벤트는 `snapshot_path` 가 실제로 채워져 있다
        #: (`minio://dsm/N.jpg`) — **셀 것이 있는 상태**에서 0건을 잰다.
        #: 채워져 있지 않으면 이 시험은 「안 샜다」가 아니라 「샐 것이 없었다」가 된다.
        self.event_id = self._event(self.stream_a)
        self.receipt_no = accept(
            scope=self.scope_a, subject_name="이서연", contact="010-2222-3333",
            kind="열람")["receipt_no"]

    def test_the_source_row_really_has_a_path(self):
        """★ 양성 대조 — **셀 것이 있는가.** 없으면 아래 0건은 아무 뜻이 없다."""
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        row = Event._base_manager.get(pk=self.event_id)
        self.assertTrue(row.snapshot_path,
                        "원본 경로가 애초에 비어 있다 — 이 시험은 아무것도 안 잰다")

    def test_no_object_path_appears_anywhere_in_the_masked_view(self):
        from apps.dsm.privacy_request import masked_view

        view = masked_view(scope=self.scope_a, receipt_no=self.receipt_no)
        leaks = []
        for where, key, value in _walk(view):
            if key in FORBIDDEN_KEYS:
                leaks.append(f"{where} (칸 이름)")
            if isinstance(value, str) and not value.startswith("data:image/"):
                for bad in FORBIDDEN_VALUES:
                    if bad in value:
                        leaks.append(f"{where} = {value[:60]}")
        self.assertEqual(leaks, [],
                         "원본을 가리키는 것이 응답에 실렸다 — 무반출 규약이 깨졌다:\n  "
                         + "\n  ".join(leaks))

    def test_the_detail_says_the_original_is_not_released(self):
        """서버가 **먼저** 말한다 — 화면이 「원본 영상은 제공되지 않습니다」를
        누르기 전에 그릴 수 있도록."""
        from apps.dsm.privacy_request import detail

        got = detail(scope=self.scope_a, receipt_no=self.receipt_no)
        self.assertFalse(got["original_video_released"])

    def test_selective_masking_is_declared_missing_not_hidden(self):
        """★ 없는 것을 **없다고 적는다.** 「마스킹본」이라는 말이 얼굴만 가린다는
        뜻으로 읽히면 안 된다 — 지금은 전면 마스킹이다."""
        from apps.dsm.privacy_request import (
            SELECTIVE_MASKING_NOT_READY_REASON, SELECTIVE_MASKING_READY,
            masked_view,
        )

        view = masked_view(scope=self.scope_a, receipt_no=self.receipt_no)
        self.assertEqual(view["masking"]["selective_ready"], SELECTIVE_MASKING_READY)
        if not SELECTIVE_MASKING_READY:
            self.assertTrue(SELECTIVE_MASKING_NOT_READY_REASON,
                            "잠긴 기능의 사유가 비면 그것은 잠금이 아니라 침묵이다")


class MaskingActuallyThrowsInformationAwayTest(DsmFixture):
    """④ **바이트로 잰다.** 「가렸다」는 말은 증거가 아니다."""

    @staticmethod
    def _jpeg(size=(160, 120)):
        """가로줄 무늬 한 장. **무늬가 있어야** 사라진 것을 볼 수 있다."""
        import io as _io

        from PIL import Image

        image = Image.new("RGB", size, (255, 255, 255))
        for y in range(0, size[1], 4):
            for x in range(size[0]):
                image.putpixel((x, y), (0, 0, 0))
        buf = _io.BytesIO()
        image.save(buf, format="JPEG", quality=95)
        return buf.getvalue()

    def test_the_masked_image_is_not_the_original(self):
        from apps.dsm.privacy_request import mask_jpeg

        source = self._jpeg()
        masked = mask_jpeg(source)
        self.assertNotEqual(masked, source)

    def test_the_stripes_are_gone(self):
        """★ 이것이 진짜 판정이다 — 무늬(고주파)가 **실제로 사라졌는가.**"""
        import io as _io

        from PIL import Image

        from apps.dsm.privacy_request import mask_jpeg

        def contrast(data):
            image = Image.open(_io.BytesIO(data)).convert("L")
            pixels = list(image.getdata())
            return max(pixels) - min(pixels)

        source = self._jpeg()
        self.assertGreater(contrast(source), 150, "원본에 무늬가 없다 — 잴 것이 없다")
        self.assertLess(contrast(mask_jpeg(source)), 120,
                        "마스킹 뒤에도 무늬가 그대로다 — 가린 것이 아니다")

    def test_the_masked_image_is_smaller(self):
        """폭을 줄인다 — 버린 정보가 다시 커지지 않게."""
        import io as _io

        from PIL import Image

        from apps.dsm.privacy_request import MASKED_MAX_WIDTH, mask_jpeg

        masked = Image.open(_io.BytesIO(mask_jpeg(self._jpeg((1280, 720)))))
        self.assertLessEqual(masked.size[0], MASKED_MAX_WIDTH)


class OtherTenantsRequestsAreInvisibleTest(DsmFixture):
    """③ **남의 청구는 없는 것으로 답한다.**"""

    def setUp(self):
        from apps.dsm.privacy_request import accept

        self.receipt_no = accept(
            scope=self.scope_a, subject_name="박지훈", contact="010-9999-0000",
            kind="삭제")["receipt_no"]

    def test_another_tenant_does_not_see_it_in_the_list(self):
        from apps.dsm.privacy_request import list_requests

        mine = list_requests(scope=self.scope_a)
        theirs = list_requests(scope=self.scope_b)
        self.assertEqual(mine["total"], 1)
        self.assertEqual(theirs["total"], 0,
                         "남의 테넌트 청구가 목록에 보인다 — 그 안에는 사람 이름이 있다")

    def test_another_tenant_gets_not_found_not_forbidden(self):
        """★ **없는 것과 남의 것이 밖에서 같은 답이어야 한다.**

        「권한 없음」으로 답하면 그 접수 번호가 **존재한다는 사실**이 새어 나간다.
        """
        from apps.dsm.privacy_request import detail

        with self.assertRaises(LookupError):
            detail(scope=self.scope_b, receipt_no=self.receipt_no)

    def test_the_owner_can_still_read_it(self):
        """★ 양성도 함께 본다 — 전부 거절하는 문지기는 문지기가 아니다."""
        from apps.dsm.privacy_request import detail

        got = detail(scope=self.scope_a, receipt_no=self.receipt_no)
        self.assertEqual(got["request"]["receipt_no"], self.receipt_no)

    def test_a_pipeline_call_cannot_accept_a_request(self):
        """사람 없는 호출은 청구를 접수할 수 없다 — 접수는 사람의 행위다."""
        from apps.dsm.privacy_request import accept

        with self.assertRaises(Exception) as caught:
            accept(scope=self.scope_pipe, subject_name="아무개", contact="010")
        self.assertNotIsInstance(caught.exception, AssertionError)


class TheRouteIsRegisteredTest(DsmFixture):
    """★ 라우트가 **열거기에 보이는가.** 안 보이면 트립와이어의 눈 밖이다."""

    @staticmethod
    def _paths():
        from common.tenant_scope import _iter_ninja_apis

        found = []
        for _mount, api in _iter_ninja_apis():
            for _prefix, router in getattr(api, "_routers", []) or []:
                for op_path in (getattr(router, "path_operations", {}) or {}):
                    found.append(str(op_path))
        return found

    def test_the_law_routes_are_declared(self):
        paths = self._paths()
        for expected in ("/law/privacy-requests",
                         "/law/privacy-requests/{receipt_no}",
                         "/law/privacy-requests/{receipt_no}/masked",
                         "/law/retention", "/law/retention/sweep",
                         "/law/ai-act/duties"):
            self.assertIn(expected, paths, f"{expected} 라우트가 선언되지 않았다")

    def test_the_literal_list_route_precedes_the_variable_one(self):
        """D-410 — 변수 조각이 리터럴을 삼키면 있는 기능이 없어 보인다."""
        paths = self._paths()
        self.assertLess(paths.index("/law/privacy-requests"),
                        paths.index("/law/privacy-requests/{receipt_no}"))
