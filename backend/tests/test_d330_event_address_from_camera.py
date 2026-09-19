# -*- coding: utf-8 -*-
"""D-330 — **사건의 주소는 카메라가 안다** (턴 V · 차선 U3).

무엇이 이 시험을 만들었나 [실측 2026-09-18]
--------------------------------------------
온보딩 U3#2(「위치 확인 — 어디로 가나」)가 두 턴째 빨강이었고, 사유는 매번
「씨앗 사건에 주소가 없다」였다. 그런데 씨앗 카메라에는 설치 주소가 **있었다.**
비어 있던 것은 카메라가 아니라 **사건**이다.

뿌리는 배선의 빈칸이다:

    · `JUSO_REVERSE_SUPPORTED='no'` (D-329) — 좌표→도로명 어댑터는 영원히
      `disabled` 를 낸다. 그래서 배선이 커널에 넘기는 주소는 **언제나 비어 있다**
    · D-330 은 그 대체를 이미 판정해 두었다 — 「카메라는 고정 설치물이므로 설치
      주소를 적어 두면 이벤트 위치가 곧 그 카메라의 주소다」
    · 그런데 **그 판정을 코드로 옮긴 자리가 없었다.** 카메라 표에 주소가 가득
      차 있어도 현장에 가는 사람의 화면(M3 「어디로 가나」)은 빈칸이었다

그래서 이 시험이 지키는 것은 하나다:

    **씨앗이든 실제 탐지든, 사건을 만드는 길은 하나(K1)이고 그 길이 주소를 싣는다.**

씨앗이 제 손으로 주소를 적어 넣어 이 자리를 메우면 그것은 시드가 규칙을 흉내 내는
것이고(P-9), 그러면 규칙이 없어도 시드는 똑같이 보인다 — 시드로 찍은 화면에서
이 결함은 영영 안 드러난다.
"""
from __future__ import annotations

import contextlib

from django.apps import apps
from django.test import TestCase

CAMERA_ADDRESS = "경기도 안양시 만안구 안양천서로 100"


class _Fixture(TestCase):
    """카메라 둘 — 주소가 **있는** 것과 **없는** 것. 둘을 갈라야 이 규칙이 보인다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        UserGroup = apps.get_model("user", "UserGroup")
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")

        # 스레드 로컬에 남은 앞 시험의 요청을 지운다 (D-253 · test_k1_event_kernel 와 같다).
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group = UserGroup.objects.create(name="d330-tenant")
        UserGroup.objects.filter(pk=cls.group.pk).update(created_by=None)

        cls.with_address = cls._make_stream(
            "d330-cam-addr", install_address=CAMERA_ADDRESS, address_source="manual")
        cls.no_address = cls._make_stream(
            "d330-cam-blank", install_address="", address_source="unset")
        #: 주소는 적혀 있는데 **출처가 선언되지 않은** 카메라 — 두 칸이 어긋난 행이다.
        cls.undeclared = cls._make_stream(
            "d330-cam-undeclared", install_address=CAMERA_ADDRESS, address_source="unset")

        from common.tenant_scope import TenantScope

        cls.scope_pipe = TenantScope.system(
            reason="D-330 시험 — 검출 파이프라인에는 요청자가 없다 (D-281)")

    @classmethod
    def _make_stream(cls, name: str, *, install_address: str, address_source: str):
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        sm = StreamMonitor.objects.create(
            name=name, code=name, ip_source="rtsp://test.invalid/x",
            install_address=install_address, address_source=address_source,
        )
        # 소유 필드는 환경에 따라 `groups`(M2M) 또는 `group`(FK) 이다 — 커널이 쓰는
        # 판단기를 그대로 쓴다(픽스처가 한쪽을 박으면 다른 환경에서 조용히 판정 불가다).
        from kernels.k1_event.services import _owner_field

        if _owner_field(StreamMonitor) == "groups":
            sm.groups.set([cls.group])
        else:
            sm.group = cls.group
            sm.save(update_fields=["group"])
        return sm

    def _record(self, stream, **kwargs):
        from kernels.k1_event import services as k1

        return k1.record_detection(
            scope=self.scope_pipe, stream_monitor_id=stream.pk,
            event_type="fire", severity="critical", snapshot_path="", **kwargs)

    def _row(self, event_id: int):
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        return Event._base_manager.get(pk=event_id)


class EventInheritsCameraAddressTest(_Fixture):
    """주소를 **안 받았을 때** 카메라의 설치 주소가 사건에 실리는가."""

    def test_event_gets_the_camera_install_address(self) -> None:
        """★ U3#2 가 빨갛던 그 자리다 — 사건의 `address` 를 화면이 읽는다."""
        result = self._record(self.with_address)
        row = self._row(result.event_id)
        self.assertEqual(CAMERA_ADDRESS, row.address)

    def test_inherited_address_is_not_left_as_disabled(self) -> None:
        """★ 배선은 어댑터가 낸 `disabled` 를 넘긴다. 물려받았으면 그것을 바로잡는다 —
        주소가 있는데 「조회 대상 아님」이면 화면은 그 행을 「주소 없음」으로 그린다."""
        result = self._record(self.with_address, address_status="disabled")
        row = self._row(result.event_id)
        self.assertEqual(CAMERA_ADDRESS, row.address)
        self.assertEqual("resolved", row.address_status)

    def test_a_given_address_always_wins(self) -> None:
        """★ 물려받기는 **빈칸을 채우는 일**이다 — 덮어쓰지 않는다.
        역지오코딩이 열리는 날 그 값이 카메라 설치 주소보다 정확하다."""
        given = "서울특별시 종로구 세종대로 1"
        result = self._record(self.with_address, address=given)
        row = self._row(result.event_id)
        self.assertEqual(given, row.address)

    def test_a_camera_without_an_address_stays_empty(self) -> None:
        """★ 없는 것은 없는 채로 둔다 — 짐작한 주소는 현장 사람을 엉뚱한 데로 보낸다."""
        result = self._record(self.no_address)
        row = self._row(result.event_id)
        self.assertFalse(row.address)
        self.assertEqual("disabled", row.address_status)

    def test_an_address_without_a_declared_source_is_not_inherited(self) -> None:
        """★ 두 칸이 한 사실을 다르게 말하는 행은 **믿지 않는다.**
        이 문턱은 알림 쪽이 이미 세워 둔 것이고, 여기서 다르게 정하면
        「알림에는 안 나가는 주소가 화면에는 나가는」 상태가 된다."""
        result = self._record(self.undeclared)
        row = self._row(result.event_id)
        self.assertFalse(row.address)

    def test_the_two_kernels_agree_on_the_same_camera(self) -> None:
        """★ 사건의 주소(K1)와 알림의 위치 한 줄(K2)이 **같은 카메라에서 갈리지 않는가.**
        규칙을 두 벌로 두면 한쪽만 고쳐지는 날 두 화면이 다른 말을 한다(D-369)."""
        from kernels.k2_notify.services import _location_line

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        for stream in (self.with_address, self.undeclared, self.no_address):
            with self.subTest(camera=stream.code):
                result = self._record(stream)
                row = Event._base_manager.select_related("stream_monitor").get(
                    pk=result.event_id)
                line = _location_line(row)
                self.assertEqual(
                    bool(row.address), CAMERA_ADDRESS in line,
                    "사건에 실린 주소와 알림에 나가는 주소가 갈렸습니다.")

    def test_the_kernel_did_not_learn_about_the_outside(self) -> None:
        """★ 이것은 **조회가 아니다.** 커널이 주소 어댑터를 부르면 계층 역전이다
        (`verify_layers` 금지 ⑤) — 부르지 않는다는 것을 소스로 못박는다."""
        import re
        from pathlib import Path

        import kernels.k1_event.services as k1

        # 머리말·주석은 어댑터를 **말로** 가리킨다(그래야 다음 사람이 안다).
        # 금지된 것은 말이 아니라 **부름**이므로 import 문만 센다.
        source = Path(k1.__file__).read_text(encoding="utf-8")
        imports = [
            line.strip() for line in source.splitlines()
            if re.match(r"\s*(from|import)\s+adapters", line)
        ]
        self.assertEqual([], imports, "커널이 어댑터를 부릅니다 — 계층 역전입니다.")
