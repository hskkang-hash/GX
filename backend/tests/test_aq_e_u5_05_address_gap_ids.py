# -*- coding: utf-8 -*-
"""턴 AQ · 조율자 — 온보딩 「누른 뒤」 U5#5: 주소 없는 카메라의 **id** 를 배지와 함께 낸다.

턴 AP 의 U5#5 빨강(차선 Q 원인 한 줄): `/dsm/cameras/address` 표가 켜진 카메라 전부를
싣고 현재 주소를 안 보여 줘서, 「이 한 대 채우기」 첫 행이 이미 주소 있는 카메라였다 →
덮어쓰기 · `without_address` 5 → 5. 이제 `address_gap()` 이 `without_address_ids` 를 내고
화면(`CameraAddress.tsx::missingFirst`)이 그 행을 위로 올려 「주소 없음」 표식을 단다.

캐시 처리: 해당 없음 — 서비스 함수를 직접 부른다(HTTP 0 · 응답 캐시를 지나지 않는다).
"""
from __future__ import annotations

from pathlib import Path

from tests.test_dsm_app import DsmFixture


class AddressGapIdsTest(DsmFixture):
    def test_ids_match_the_count_and_only_name_blank_cameras(self) -> None:
        from stream_monitors.models import StreamMonitor
        from stream_monitors.services import bulk_register

        gap = bulk_register.address_gap(scope=self.scope_a)
        ids = gap["without_address_ids"]
        self.assertEqual(gap["without_address"], len(ids))
        for cam in StreamMonitor.objects.filter(pk__in=ids):
            self.assertIn(cam.install_address or "", ("",))

    def test_filling_one_removes_its_id(self) -> None:
        from stream_monitors.models import StreamMonitor
        from stream_monitors.services import bulk_register

        ids = bulk_register.address_gap(scope=self.scope_a)["without_address_ids"]
        self.assertTrue(ids, "픽스처 A 테넌트에 주소 없는 카메라가 있어야 한다")
        StreamMonitor.objects.filter(pk=ids[0]).update(install_address="경기도 안양시 만안구 안양로 1")
        after = bulk_register.address_gap(scope=self.scope_a)["without_address_ids"]
        self.assertNotIn(ids[0], after)
        self.assertEqual(len(ids) - 1, len(after))

    def test_other_tenants_ids_do_not_leak(self) -> None:
        from stream_monitors.models import StreamMonitor
        from stream_monitors.services import bulk_register

        ids = bulk_register.address_gap(scope=self.scope_a)["without_address_ids"]
        foreign = set(StreamMonitor.objects.filter(group_id=self.group_b.pk)
                      .values_list("pk", flat=True))
        self.assertFalse(set(ids) & foreign, "남의 테넌트 카메라 id 가 배지에 섞였다")

    def test_screen_sorts_missing_rows_first(self) -> None:
        root = Path(__file__).resolve().parents[2]
        candidates = [root / "frontend/src/features/dsm/pages/CameraAddress.tsx",
                      Path("/repo/frontend/src/features/dsm/pages/CameraAddress.tsx")]
        src = next((p for p in candidates if p.is_file()), None)
        if src is None:
            self.skipTest("프런트 소스가 이 자리에 없다")
        text = src.read_text(encoding="utf-8")
        self.assertIn("missingFirst(cameras.data?.cameras", text)
        self.assertIn('data-gx="camera-address-row-missing"', text)
