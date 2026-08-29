# -*- coding: utf-8 -*-
"""카메라 설치 주소 — **밖에서 사 오려던 것을 우리는 이미 알고 있었다** (D-330).

무엇이 바뀌었나
---------------
종전 설계는 이벤트 좌표 → 외부 역지오코딩 API → 주소 였다. 외부 의존 · 타임아웃 ·
저하 운전 · 실패 상태 4값 · 비용, 그리고 **자원이 없어서 잠김**(FX-5).

그런데 **카메라는 고정 설치물이다.** 설치할 때 주소를 안다 — 적어 두지 않았을 뿐이다.

이 시험이 묻는 것 셋
--------------------
    ① **주소가 있으면 알림에 주소가 나가는가**  「정문 (서울시 …로 12)」
    ② **없으면 종전대로 나가는가**              좌표 1줄. D-308 이 그은 경계를 넓히지 않는다
    ③ **주소가 발송을 지연시키지 않는가**       주소는 보조 정보이지 발송 조건이 아니다

③이 이 변경 고유의 위험이다. 주소를 채우려고 발송을 기다리면, 그 순간
**보조 정보가 계약 AC(F-10 30초)를 인질로 잡는다.**
"""
from __future__ import annotations

from django.test import TestCase

from tests.test_dsm_app import DsmFixture


class CameraAddressFieldTest(TestCase):
    """모델의 계약 — 「아직 안 적음」과 「없음」을 같은 값에 두지 않는다 (D-290)."""

    def test_the_source_column_separates_unset_from_written(self) -> None:
        from django.apps import apps

        Model = apps.get_model("stream_monitors", "StreamMonitor")
        values = {c[0] for c in Model._meta.get_field("address_source").choices}
        self.assertEqual({"unset", "manual"}, values)
        self.assertEqual("unset", Model._meta.get_field("address_source").default)

    def test_there_is_a_place_for_what_the_road_address_cannot_say(self) -> None:
        """「정문」·「3층 복도」 — 현장 사람이 쓰는 표현. 도로명주소가 답하지 못한다."""
        from django.apps import apps

        names = {f.name for f in
                 apps.get_model("stream_monitors", "StreamMonitor")._meta.get_fields()}
        self.assertIn("install_address", names)
        self.assertIn("install_address_detail", names)


class NotificationLocationLineTest(DsmFixture):
    """알림 본문의 위치 한 줄 — F-10 취지."""

    def _line(self, stream) -> str:
        from django.apps import apps

        from kernels.k2_notify.services import _location_line

        event_id = self._event(stream)
        event = apps.get_model("stream_monitors", "DetectionEvent")             ._base_manager.select_related("stream_monitor").get(pk=event_id)
        return _location_line(event)

    def test_the_camera_address_is_used_when_it_is_written(self) -> None:
        """★ 「정문 (서울시 …로 12)」 — 역지오코딩보다 결과가 좋다."""
        self.stream_a.install_address = "서울특별시 중구 세종대로 110"
        self.stream_a.install_address_detail = "정문"
        self.stream_a.address_source = "manual"
        self.stream_a.save(update_fields=["install_address", "install_address_detail",
                                          "address_source"])
        line = self._line(self.stream_a)
        self.assertIn("정문", line)
        self.assertIn("세종대로 110", line)

    def test_the_road_address_alone_is_enough(self) -> None:
        self.stream_a.install_address = "서울특별시 중구 세종대로 110"
        self.stream_a.address_source = "manual"
        self.stream_a.save(update_fields=["install_address", "address_source"])
        self.assertEqual("위치 서울특별시 중구 세종대로 110", self._line(self.stream_a))

    def test_unset_falls_back_to_the_old_line_unchanged(self) -> None:
        """★ D-308 경계를 넓히지 않는다 — 없으면 **종전 그대로** 나간다."""
        line = self._line(self.stream_b)
        self.assertNotIn("(", line)
        self.assertTrue(line.startswith("위치"))

    def test_an_address_written_without_source_is_not_used(self) -> None:
        """출처가 `unset` 인데 주소만 있는 행은 **믿지 않는다.**

        두 칸이 한 사실을 다르게 말하는 상태이고, 그 상태를 조용히 채택하면
        어긋남이 영영 안 보인다 (`verify_camera_address.py` 가 그 수를 센다).
        """
        self.stream_a.install_address = "서울특별시 중구 세종대로 110"
        self.stream_a.address_source = "unset"
        self.stream_a.save(update_fields=["install_address", "address_source"])
        self.assertNotIn("세종대로", self._line(self.stream_a))

    def test_the_address_does_not_delay_sending(self) -> None:
        """★ 주소는 보조 정보이지 **발송 조건이 아니다** (D-330).

        주소가 없는 카메라의 이벤트도 F-10 의 상한 안에 발송 기록이 남는다 —
        보조 정보가 계약 AC 를 인질로 잡지 않는다.
        """
        from kernels.k2_notify import send

        from django.utils import timezone

        # 지금 난 사건이어야 F-10 의 30초를 실제로 잰다 — 픽스처 기본은 과거 시각이다.
        event_id = self._event(self.stream_a, when=timezone.now())  # 주소 미입력 그대로
        rows = send(scope=self.scope_a, event_id=event_id)
        self.assertTrue(rows, "주소가 없다고 발송 기록이 사라지면 F-10 이 깨집니다.")
        self.assertTrue(all(r.meets_f10 for r in rows),
                        "주소가 없는 카메라의 이벤트가 F-10 상한을 넘었습니다 — "
                        "보조 정보가 계약 AC 를 인질로 잡고 있습니다.")


class CameraAddressGateTest(TestCase):
    """세는 도구가 실재하는가 — **수가 보여야 채워진다** (D-301 · D-286)."""

    def test_the_counting_tool_exists_and_does_not_block(self) -> None:
        from tests.test_k5_threshold_table import _gate

        gate = _gate("verify_camera_address.py")
        self.assertIsNotNone(gate, "세는 도구가 없으면 아무도 채우지 않습니다.")
        src = gate.read_text(encoding="utf-8")
        self.assertIn("EXIT_OK", src,
                      "이건 판정이 아니라 계측입니다 — 운영자가 채우는 값을 개발이 막지 않습니다.")
