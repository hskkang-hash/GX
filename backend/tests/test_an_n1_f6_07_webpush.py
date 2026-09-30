# -*- coding: utf-8 -*-
"""FWS-F6-07 반쪽 채움 — 웹푸시 **훈련** 채널 연계 (턴 AN · WO-GX-20260929-17 ·
P-392 「반쪽 여섯 채우기」 · 차선 N1).

이 절이 「제목의 「앱 푸시 연계」가 없었다」로 반쪽이었던 이유(WO-GX-20260928-16
보고 §2)를 채운다 — 세종 판정: 산림청 스마트산림재난 앱 실제 푸시는 여전히
[미확인]이라 열지 않는다. 대신 **웹푸시 훈련 채널**(`kernels.k2_notify.
send_webpush`)로 잇는다(실발송 아님 · 제목은 언제나 `[훈련]`로 시작한다).
문자 초안(`F6_07_EvacuationCbsDraftTest`, `test_fws_f6.py`)은 그대로 둔다 —
이 파일은 그 옆에 새로 여는 자리를 잰다.

새 라우트(`apps/fws/api_n1.py::FwsN1API`)는 **아직 `apps/fws/urls.py` 에 등록되지
않았다** — 그 파일은 공용 파일(§0.4 인접)이라 이 차선이 고치지 않는다(최종
보고에 조율자에게 넘길 줄을 적는다). 그래서 이 시험은 프로젝트의 실제
URLconf 대신 **이 파일 스스로가 마운트하는 임시 URLconf**로 잰다
(`django.test.override_settings(ROOT_URLCONF=__name__)`) — Django 의 실제
`Client`·미들웨어·인증·`@tenant_scoped`·`@idempotent` 전부가 실제로 돈다(가짜
Mock 요청이 아니다). 등록 뒤에는 이 우회가 필요 없어진다.

캐시 처리: 우회 — `FwsHttpTest.setUp` 이 매 시험 앞에 `cache.clear()` 를 부른다
(`test_fws_f6.py` 와 같은 규약).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

from django.apps import apps
from django.test import override_settings
from django.urls import path
from ninja_extra import NinjaExtraAPI

from tests.test_fws_app import FwsHttpTest

from apps.fws.api_n1 import FwsN1API

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"

#: 임시 URLconf — `apps/fws/urls.py`(공용 파일)는 고치지 않는다. 컨트롤러는
#: 이 차선이 진짜로 소유한 `api_n1.py` 것 그대로다(가짜 라우트가 아니다).
_test_api = NinjaExtraAPI(urls_namespace="fws_n1_an_test")
_test_api.register_controllers(FwsN1API)

urlpatterns = [
    path("api/fws/", _test_api.urls),
]

#: 시험용 VAPID 값 — `test_u3_webpush_send.py::FAKE_ENV` 와 같은 형(진짜 키가
#: 아니다 · D-204). `pywebpush.webpush` 자체를 몽키패치하므로 값은 외부로
#: 한 바이트도 안 나간다.
FAKE_ENV = {
    "GX_VAPID_PUBLIC_KEY": "fake-public-for-tests",
    "GX_VAPID_PRIVATE_KEY": "fake-private-for-tests",
    "GX_VAPID_SUBJECT": "mailto:test@test.invalid",
}
FAKE_SUBSCRIPTION = {
    "endpoint": "https://push.invalid/send/an-n1-f6-07-fake-endpoint",
    "keys": {"p256dh": "BFakeP256dhKeyForTestsOnly_not_a_real_key",
            "auth": "FakeAuthSecretForTests"},
}


def _drill_path(event_id) -> str:
    return f"/api/fws/liaison/fire-events/{event_id}/evacuation-webpush-drill"


def _merge_title_parts(clause_id: str, title_parts: list) -> None:
    """`title_parts`(제목이 부르는 것 ↔ 있는 것 표)를 **기존 실측 증거 위에** 더한다
    — `request`·`response`·`test`(F6_07_EvacuationCbsDraftTest 의 실측)는 그대로
    두고 표만 더한다(협약 §별표 절 승격 ②).

    [턴 AQ · P-431 · 차선 Q] 사람 표는 이제 `SPEC/<id>.retro.md`(손으로만)다 — 이
    쓰개는 json 에 `title_parts` 를 **쓰지 않는다**. 표 모양(빈 칸 0)만 여기서 본다."""
    for part in title_parts:
        missing = [k for k in ("part", "where", "status") if not (part.get(k) or "").strip()]
        assert not missing, f"{clause_id} title_parts 에 빈 칸: {part!r} ({missing})"


@override_settings(ROOT_URLCONF=__name__)
class F6_07_WebpushDrillTest(FwsHttpTest):
    """`FwsHttpTest`(F1·F6 시험의 픽스처·헬퍼)를 그대로 쓴다 — 같은 표를 두 벌로
    만들지 않는다."""

    def test_drill_send_is_training_marked_and_never_a_real_push(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        body = {"area_name": "OO면 OO리 6구", "kind": "order",
               "subscription": FAKE_SUBSCRIPTION}
        with mock.patch.dict(os.environ, FAKE_ENV), \
                mock.patch("pywebpush.webpush", return_value=None) as sender:
            resp = self.client.post(
                _drill_path(event_id), data=json.dumps(body),
                content_type="application/json", **head)
        self.assertEqual(200, resp.status_code, resp.content)
        out = self._body(resp)
        self.assertTrue(out["title"].startswith("[훈련]"),
                       "웹푸시 훈련 제목이 [훈련] 으로 시작하지 않습니다 — 실발송으로 "
                       "오해될 수 있습니다.")
        self.assertEqual("webpush", out["channel"])
        self.assertTrue(out["succeeded"], out.get("failure_reason"))
        self.assertEqual(1, sender.call_count, "발송기가 한 번 불려야 합니다.")

        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        row = Delivery._base_manager.get(pk=out["delivery_id"])
        self.assertTrue(
            row.recipient_address.startswith("drill:webpush:"),
            "훈련 표식(drill:)이 없습니다 — 5분 억제·통계에 실발송처럼 잡힐 "
            "수 있습니다.")
        self.assertNotIn(FAKE_SUBSCRIPTION["endpoint"], row.recipient_address)

        _merge_title_parts(
            "FWS-F6-07",
            [
                {"part": "대피 소요시간(P-386)",
                 "where": "constants.evacuation_deadline_hours",
                 "status": "있음"},
                {"part": "CBS 초안(재난문자 글자수 상한)",
                 "where": "draft_evacuation_text — 표준 90자·확장 157자",
                 "status": "있음"},
                {"part": "대피 지시 기록",
                 "where": "liaison.evacuation_cbs_draft 감사", "status": "있음"},
                {"part": "산림청 스마트산림재난 앱 실제 푸시 발송",
                 "where": "annex 원문 그대로 [미확인] — 열지 않는다",
                 "status": "없음(세종 판정 · 결정 사항)",
                 #: [턴 AO · P-406 · 차선 N1] 결정으로 뺀 행 — 산림청
                 #: 스마트산림재난 앱은 이 제품이 발송 권한도 연동 계약도 갖지
                 #: 않은 제3자 앱이라, 실제 앱 푸시는 이 절의 범위 밖으로 정했다
                 #: (세종 판정 · WO-GX-20260929-17 §2 두 번 물은 것 ①). 웹푸시
                 #: 훈련 채널(위 행)이 이 절이 실제로 여는 앱 푸시 연계다.
                 "excluded_by": "P-392",
                 "excluded_why": "산림청 스마트산림재난 앱 실제 발송은 세종 "
                                 "판정으로 F6-07 범위 밖 — 웹푸시 훈련 채널이 "
                                 "이 절의 앱 푸시 연계다"},
                {"part": "앱 푸시 연계(제목이 부르는 것)",
                 "where": "[턴 AN] POST .../evacuation-webpush-drill · "
                         "kernels.k2_notify.send_webpush · 제목 [훈련] 고정 · "
                         "drill: 표식(F6_07_WebpushDrillTest)",
                 "status": "있음(대체 — 웹푸시 훈련 채널 · 실발송 아님)"},
            ])

    def test_missing_area_name_is_422(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        body = {"area_name": "", "kind": "order", "subscription": FAKE_SUBSCRIPTION}
        with mock.patch.dict(os.environ, FAKE_ENV):
            resp = self.client.post(
                _drill_path(event_id), data=json.dumps(body),
                content_type="application/json", **head)
        self.assertEqual(422, resp.status_code, resp.content)

    def test_no_such_event_is_404(self) -> None:
        head = self._bearer(self.user_a)
        body = {"area_name": "OO면 OO리 6구", "kind": "order",
               "subscription": FAKE_SUBSCRIPTION}
        with mock.patch.dict(os.environ, FAKE_ENV):
            resp = self.client.post(
                _drill_path(999_999_999), data=json.dumps(body),
                content_type="application/json", **head)
        self.assertEqual(404, resp.status_code, resp.content)
