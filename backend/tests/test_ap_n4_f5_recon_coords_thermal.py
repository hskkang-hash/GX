# -*- coding: utf-8 -*-
"""FWS-F5-01·F5-03 반쪽 채움 실측 (턴 AP · WO-19 · P-419 · 차선 N4).

`docs/agent/evidence/SPEC/FWS-F5-01.json`·`FWS-F5-03.json` 의 옛 title_parts가
연 두 열린 행 — 「좌표가 응답에 안 실린다(간접뿐)」·「사진·열화상을 구분하는
칸이 없다」 — 를 `apps/fws/ap_f5.py`(새 파일 · `drone.py` 는 고치지 않는다)가
닫는다. 이 시험이 실측한다.
"""
from __future__ import annotations

from django.core.cache import cache
from django.test import Client

from tests.no_cache import NO_CACHE
from tests.test_fws_app import FwsHttpTest, _write_evidence

RECON_COORDS = "/api/fws/ap/drone/missions/{}/recon-coords"
THERMAL = "/api/fws/ap/drone/verifications/{}/thermal-attachment"
RECON = "/api/fws/drone/missions/{}/recon"
VERIFY_REPLY = "/api/fws/drone/verifications/{}/reply"


class Fws5ApHttpTest(FwsHttpTest):
    def setUp(self) -> None:
        cache.clear()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def tearDown(self) -> None:
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        cache.clear()


class F5_01_ReconCoordsTest(Fws5ApHttpTest):
    @staticmethod
    def _set_latlng(event_id: int, lat: float, lng: float) -> None:
        from django.apps import apps

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        Event._base_manager.filter(pk=event_id).update(lat=lat, lng=lng)

    def test_recon_coords_carries_the_events_lat_lng_and_radius(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        self._set_latlng(event_id, 36.11, 127.21)  # 발화 추정 좌표(K1 이벤트 값)
        head = self._bearer(self.user_a)

        req = self.client.post(
            f"{RECON.format(event_id)}?action=request&radius_m=300", **head)
        self.assertEqual(200, req.status_code, req.content)

        resp = self.client.get(RECON_COORDS.format(event_id), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(event_id, body["event_id"])
        self.assertEqual(300, body["radius_m"])
        self.assertIsNotNone(body["lat"], "발화 추정 좌표(lat)가 응답에 없습니다.")
        self.assertIsNotNone(body["lng"], "발화 추정 좌표(lng)가 응답에 없습니다.")
        _write_evidence(
            "FWS-F5-01", title="정찰 임무 수신(발화 추정 좌표·반경) → 열화상 정찰",
            test_ref="tests.test_ap_n4_f5_recon_coords_thermal.F5_01_ReconCoordsTest."
                    "test_recon_coords_carries_the_events_lat_lng_and_radius",
            method="GET", path=RECON_COORDS.format(event_id), request_params={},
            response=resp,
            what="[턴 AP · 차선 N4] 반쪽 채움 — 정찰 임무의 발화 추정 좌표(K1 "
                "이벤트 lat/lng)가 반경과 한 응답에 실린다(drone.py 는 고치지 "
                "않고 그 위에 새 door 하나를 더했다)")

    def test_other_tenants_event_is_404(self) -> None:
        event_id = self._event(self.stream_b, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.get(RECON_COORDS.format(event_id), **head)
        self.assertEqual(404, resp.status_code, resp.content)


class F5_03_ThermalAttachmentTest(Fws5ApHttpTest):
    def test_thermal_ref_is_a_separate_slot_from_photo_attachment_ref(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)

        # 사진 참조 — 기존 F5-03 문(F1-06 재사용)으로 판정
        verify = self.client.post(
            f"{VERIFY_REPLY.format(event_id)}?result=fire_confirmed"
            "&attachment_ref=minio://drone/photo.jpg", **head)
        self.assertEqual(200, verify.status_code, verify.content)

        # 열화상 참조 — 새 door, 다른 칸. ★ 이 라우트는 스칼라 인자를 **질의**로만
        # 받는다(django-ninja 규약 — 본문이 아니라 querystring, `drone.py::recon()`
        # 와 같은 자리).
        thermal = self.client.post(
            f"{THERMAL.format(event_id)}?thermal_ref="
            "minio%3A%2F%2Fdrone%2Fthermal.tiff", **head)
        self.assertEqual(200, thermal.status_code, thermal.content)
        thermal_body = self._body(thermal)
        self.assertEqual("minio://drone/thermal.tiff", thermal_body["thermal_ref"])

        listed = self.client.get(THERMAL.format(event_id), **head)
        self.assertEqual(200, listed.status_code, listed.content)
        rows = self._body(listed)
        self.assertEqual(1, rows["count"])
        self.assertEqual("minio://drone/thermal.tiff", rows["attachments"][0]["thermal_ref"])
        _write_evidence(
            "FWS-F5-03", title="확인 회신(산불 맞음/오인 · 사진·열화상)",
            test_ref="tests.test_ap_n4_f5_recon_coords_thermal."
                    "F5_03_ThermalAttachmentTest."
                    "test_thermal_ref_is_a_separate_slot_from_photo_attachment_ref",
            method="GET", path=THERMAL.format(event_id), request_params={},
            response=listed,
            what="[턴 AP · 차선 N4] 반쪽 채움 — 사진 참조(attachment_ref, F1-06 "
                "재사용)와 열화상 참조(thermal_ref, 새 door)가 서로 다른 칸에 "
                "남는다. 판정은 여전히 F1-06/confirm_result 문 하나가 한다 "
                "(P-357, 두 번째 판정 문을 만들지 않았다)")

    def test_empty_thermal_ref_is_422(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(f"{THERMAL.format(event_id)}?thermal_ref=", **head)
        self.assertEqual(422, resp.status_code, resp.content)

    def test_other_tenants_event_is_404(self) -> None:
        event_id = self._event(self.stream_b, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(f"{THERMAL.format(event_id)}?thermal_ref=x", **head)
        self.assertEqual(404, resp.status_code, resp.content)
