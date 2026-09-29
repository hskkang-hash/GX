# -*- coding: utf-8 -*-
"""FWS-F6-04 — 확산예측 결과 수신(업로드 경로) 실측 (턴 AP · WO-19 · 차선 N4).

명세 §5.6 F6: 「확산예측 결과 수신(API [미확인] 또는 업로드)」— 이 시험은
**업로드** 경로(`apps/fws/ap_f6.py`)를 두드린다. API 경로(산림과학원 실연동)는
이 턴 범위 밖이다(WO-19 외부 실연동 제외 · evidence `excluded_by: P-428`).
"""
from __future__ import annotations

from django.core.cache import cache
from django.test import Client

from tests.no_cache import NO_CACHE
from tests.test_fws_app import FwsHttpTest, _write_evidence

SPREAD = "/api/fws/ap/incidents/{}/spread-results"


class Fws6ApHttpTest(FwsHttpTest):
    def setUp(self) -> None:
        cache.clear()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def tearDown(self) -> None:
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        cache.clear()


class F6_04_SpreadUploadTest(Fws6ApHttpTest):
    def test_upload_then_list_reads_back_the_same_values(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)

        # ★ 스칼라 인자는 **질의**로만 받는다(django-ninja 규약 — 본문이 아니다).
        from urllib.parse import quote

        up = self.client.post(
            f"{SPREAD.format(event_id)}?image_ref={quote('minio://fws/spread-1.png', safe='')}"
            f"&arrival_note={quote('본촌리 08:00')}", **head)
        self.assertEqual(200, up.status_code, up.content)
        body = self._body(up)
        self.assertEqual("upload", body["source"])
        self.assertEqual("minio://fws/spread-1.png", body["image_ref"])

        listed = self.client.get(SPREAD.format(event_id), **head)
        self.assertEqual(200, listed.status_code, listed.content)
        rows = self._body(listed)
        self.assertEqual(1, rows["count"])
        self.assertEqual("minio://fws/spread-1.png", rows["results"][0]["image_ref"])
        self.assertEqual("본촌리 08:00", rows["results"][0]["arrival_note"])
        _write_evidence(
            "FWS-F6-04", title="확산예측 결과 수신(API [미확인] 또는 업로드)",
            test_ref="tests.test_ap_n4_f6_spread_upload.F6_04_SpreadUploadTest."
                    "test_upload_then_list_reads_back_the_same_values",
            method="GET", path=SPREAD.format(event_id), request_params={},
            response=listed,
            what="[턴 AP · 차선 N4] 확산예측 결과(이미지/좌표 참조 + 화선 도달 "
                "예상 메모)를 업로드 경로로 등록·재조회 — 실측(API 경로는 산림"
                "과학원 실연동이라 이 턴 범위 밖 · excluded_by P-428)")

    def test_empty_image_ref_is_422(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(f"{SPREAD.format(event_id)}?image_ref=", **head)
        self.assertEqual(422, resp.status_code, resp.content)

    def test_other_tenants_event_is_404(self) -> None:
        event_id = self._event(self.stream_b, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(f"{SPREAD.format(event_id)}?image_ref=x", **head)
        self.assertEqual(404, resp.status_code, resp.content)
