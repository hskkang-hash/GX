# -*- coding: utf-8 -*-
"""D-338 ① — `install_address` 에 **쓰기 지점이 있는가.**

이 파일이 막는 것 하나
----------------------
`install_address` 는 2026-09-06 까지 **정의 있음 · 읽기 있음 · 쓰기 0곳**이었다.
D-304 착시 ⑥(스키마의 착시)의 정확한 형태다 — `clip_path` 가 그랬다.

계측기가 「39/39 미입력」을 출력하니 숨지는 않았다. 그러나
**숨지 않는 것과 살아 있는 것은 다르다.** 채울 수단이 없으면 그 수는 영원히 39 다.

그래서 이 시험은 **필드가 아니라 경로**를 본다: 관리 커맨드로 값이 실제로 들어가는가.
읽는 쪽(알림 위치줄)은 `test_f10_camera_address.py` 가 이미 본다 —
쓰기와 읽기를 **다른 파일이 나눠 맡는다.** 한 파일이 둘 다 보면, 한쪽이 죽어도
다른 쪽 단언이 초록을 만들어 준다.

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105)
    skip·xfail 하지 말 것.
"""

from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from stream_monitors.models import StreamMonitor

ADDRESS = "경기도 안양시 만안구 안양로 123"


class CameraAddressWritePathTest(TestCase):
    """쓰기 지점이 실재하는가 — 커맨드를 **실제로 부른다.**"""

    def setUp(self):
        self.cam = StreamMonitor.objects.create(
            name="anyang-front", code="anyang-front",
            ip_source="rtsp://test.invalid/1")

    def _run(self, *args, **kwargs):
        out = StringIO()
        call_command("set_camera_address", *args, stdout=out, stderr=out, **kwargs)
        return out.getvalue()

    def test_the_command_writes_the_address(self):
        """★ 출생 표본 — 쓰기 0곳이던 자리에 값이 들어간다."""
        self._run("--name", "anyang-front", "--address", ADDRESS, "--detail", "정문")
        self.cam.refresh_from_db()
        self.assertEqual(ADDRESS, self.cam.install_address)
        self.assertEqual("정문", self.cam.install_address_detail)
        self.assertEqual(StreamMonitor.AddressSource.MANUAL, self.cam.address_source)

    def test_dry_run_writes_nothing(self):
        """모의 실행이 진짜로 쓰지 않는가. **기본이 쓰기라는 점**이 여기서 갈린다."""
        self._run("--name", "anyang-front", "--address", ADDRESS, "--dry-run")
        self.cam.refresh_from_db()
        self.assertIsNone(self.cam.install_address)
        self.assertEqual(StreamMonitor.AddressSource.UNSET, self.cam.address_source)

    def test_clear_returns_to_unset_not_to_empty_string(self):
        """「안 적음」과 「빈 주소」는 다른 사실이다 (D-290)."""
        self._run("--name", "anyang-front", "--address", ADDRESS)
        self._run("--name", "anyang-front", "--clear")
        self.cam.refresh_from_db()
        self.assertIsNone(self.cam.install_address)
        self.assertEqual(StreamMonitor.AddressSource.UNSET, self.cam.address_source)

    def test_a_missing_camera_is_counted_not_swallowed(self):
        """없는 이름을 조용히 넘기면 「39대 다 넣었다」가 3대만 넣은 상태와 같아진다 (D-301)."""
        with self.assertRaises(CommandError):
            self._run("--name", "없는카메라", "--address", ADDRESS)

    def test_an_empty_address_is_not_written_as_a_blank(self):
        """빈 문자열을 주소로 넣지 않는다 — 넣으면 「적었는데 비었다」가 만들어진다."""
        with self.assertRaises(CommandError):
            self._run("--name", "anyang-front", "--address", "   ")
        self.cam.refresh_from_db()
        self.assertEqual(StreamMonitor.AddressSource.UNSET, self.cam.address_source)

    def test_a_duplicate_name_writes_nothing(self):
        """어느 카메라인지 모르는 채로 쓰면 **엉뚱한 카메라의 주소가 알림에 나간다.**"""
        StreamMonitor.objects.create(name="anyang-front", code="dup",
                                     ip_source="rtsp://test.invalid/2")
        with self.assertRaises(CommandError):
            self._run("--name", "anyang-front", "--address", ADDRESS)
        for cam in StreamMonitor._base_manager.filter(name="anyang-front"):
            self.assertEqual(StreamMonitor.AddressSource.UNSET, cam.address_source)

    def test_csv_fills_many(self):
        """대표께 부탁드린 세 칸 그대로 들어가는가 (이름 / 도로명주소 / 현장 표현)."""
        import tempfile
        from pathlib import Path

        StreamMonitor.objects.create(name="anyang-3f", code="anyang-3f",
                                     ip_source="rtsp://test.invalid/3")
        with tempfile.TemporaryDirectory() as d:
            csv_path = Path(d) / "cameras.csv"
            csv_path.write_text(
                "name,address,detail\n"
                f"anyang-front,{ADDRESS},정문\n"
                f"anyang-3f,{ADDRESS},3층 복도\n",
                encoding="utf-8")
            self._run("--csv", str(csv_path))

        # ★ `objects` 가 아니라 `_base_manager` 로 읽는다.
        #   dj-core 의 `CustomManagerGroup._request` 는 **클래스 속성**이라
        #   앞선 시험이 남긴 요청이 이 조회까지 걸러낸다(core/base.py:219).
        #   전수 실행에서 이 단언이 `2 != 0` 으로 죽어 드러난 자리다 [실측 2026-09-07].
        written = StreamMonitor._base_manager.filter(
            address_source=StreamMonitor.AddressSource.MANUAL)
        self.assertEqual(2, written.count())
        self.assertEqual(
            {"정문", "3층 복도"},
            {c.install_address_detail for c in written})


class CameraAddressIsNotADeadFieldTest(TestCase):
    """쓰기 지점이 **코드에 실재하는가** — 시험이 부르는 것과 별개로 파일이 있는가.

    이 단언이 있는 이유: 시험이 커맨드를 부르는 것만으로는 「시험용으로만 존재하는
    쓰기 지점」과 구별되지 않는다. 운영자가 쓸 수 있는 자리인지를 따로 못박는다.
    """

    def test_the_management_command_is_discoverable(self):
        from django.core.management import get_commands
        self.assertIn(
            "set_camera_address", get_commands(),
            "관리 커맨드가 등록되지 않았다 — 운영자가 부를 수 없는 쓰기 지점은 "
            "쓰기 지점이 아니다 (D-338 ①)")
