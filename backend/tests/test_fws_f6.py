# -*- coding: utf-8 -*-
"""FWS App(L4) — F6(산림청·지자체 산림과 연계) 별표 절 10건의 **HTTP 실측**과
`docs/agent/evidence/SPEC/*.json` 생성 (WO-GX-20260925-15 §5 P-356·357·358 · 턴 AM
차선 N3).

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`X-No-Cache`) 헤더를 모든 요청에 싣는다
(`test_fws_app.py`·`test_fws_f2.py` 와 같은 규약). 이 파일은 새 캐시를 만들지
않는다 — 멱등 캐시는 `setUp` 에서 `cache.clear()` 로 비운다.

이 파일이 재는 것 — P-356 승격 규칙 넷 중 ①②(③·④는 게이트·제안 문서)
------------------------------------------------------------------------
    ① 실제 구현    `self.client` 가 `/api/fws/...` 를 실제로 두드린다
    ② 실측 증거    각 시험이 요청·응답을 그대로 `docs/agent/evidence/SPEC/<id>.json`
                    에 적는다(`test_fws_app._write_evidence` 재사용 — 두 벌을
                    만들지 않는다, D-212).

F6-02(웹훅) 는 **진짜 네트워크를 때리지 않는다** — `common.webhook_outbox._post`
를 몽키패치해 상대를 흉내 낸다(`test_s_webhook_outbox.py` 와 같은 기법).

F6-04(확산예측)·F6-09(요청 한도)는 이 파일이 닫지 않는다 — `scripts/
verify_spec_fws_f6.py`·`docs/agent/evidence/SPEC/N3_promotions.md` 의 「무엇이
없는가」를 본다. F6-09 의 헬스·스키마 재사용만 `F6_09_HealthReuseTest`(증거 없이)
로 확인한다.
"""
from __future__ import annotations

from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone as dj_timezone

from tests.test_fws_app import FwsHttpTest, _qs, _write_evidence


def _kfs_export_path(event_id) -> str:
    return f"/api/fws/liaison/fire-events/{event_id}/kfs-export"


WEBHOOK_CATALOG = "/api/fws/liaison/webhook-events/catalog"


def _webhook_notify_path(event_id) -> str:
    return f"/api/fws/liaison/fire-events/{event_id}/webhook-notify"


RISK_FORECAST = "/api/fws/liaison/risk-forecast"
RISK_FORECAST_MINE = "/api/fws/liaison/risk-forecast/mine"


def _heli_requests_path(event_id) -> str:
    return f"/api/fws/liaison/fire-events/{event_id}/helicopter-requests"


def _fire_dept_link_path(event_id) -> str:
    return f"/api/fws/liaison/fire-events/{event_id}/fire-department-link"


def _evac_cbs_draft_path(event_id) -> str:
    return f"/api/fws/liaison/fire-events/{event_id}/evacuation-cbs-draft"


def _police_coord_path(event_id) -> str:
    return f"/api/fws/liaison/fire-events/{event_id}/police-coordination"


def _jurisdiction_transfer_path(event_id) -> str:
    return f"/api/fws/liaison/fire-events/{event_id}/jurisdiction-transfer"


HEALTH = "/api/fws/health"

#: 시험용 웹훅 서명키 — `test_s_webhook_outbox.py` 와 같은 형(진짜 키가 아니다 · D-204).
KEY_NAME = "fws-f6-test-partner"
KEY_VALUE = "not-a-real-key-only-for-this-test"
SIGNING = {"WEBHOOK_SIGNING_KEYS": {KEY_NAME: KEY_VALUE}, "CAP_SENDER": "guardianx.test"}


class F6HttpTest(FwsHttpTest):
    """`FwsHttpTest`(F1 시험의 픽스처·헬퍼)를 그대로 쓴다 — 같은 표를 두 벌로 만들지
    않는다."""

    def setUp(self) -> None:
        cache.clear()
        from django.test import Client

        from tests.no_cache import NO_CACHE

        self.client = Client(raise_request_exception=False, **NO_CACHE)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-01 산림청 시스템 입력 항목 내보내기(JSON/CSV · 항목 1:1)
# ═══════════════════════════════════════════════════════════════════════════
class F6_01_KfsExportTest(F6HttpTest):
    def test_json_export_carries_labeled_fields_one_to_one(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire",
                               when=dj_timezone.now())
        head = self._bearer(self.user_a)
        resp = self.client.get(_kfs_export_path(event_id), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("json", body["format"])
        labels = [f["label"] for f in body["fields"]]
        self.assertIn("신고일시", labels)
        self.assertIn("발생위치_위도", labels)
        self.assertIn("산불대응단계", labels)
        self.assertEqual(len(labels), len(set(labels)), "항목 이름이 중복됩니다")
        _write_evidence(
            "FWS-F6-01", title="산림청 시스템 입력 항목 내보내기(JSON/CSV · 항목 1:1)",
            test_ref="tests.test_fws_f6.F6_01_KfsExportTest."
                    "test_json_export_carries_labeled_fields_one_to_one",
            method="GET", path=_kfs_export_path(event_id), request_params={},
            response=resp,
            what="GET .../kfs-export 가 K1 이벤트 항목을 산림청 한글 항목명과 1:1로 "
                "묶어 낸다(신고일시·위도·경도·산불대응단계 등) — 내보내기 1 실측")

    def test_csv_export_has_a_header_row_and_a_value_row(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.get(_qs(_kfs_export_path(event_id), fmt="csv"), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertIn("text/csv", resp["Content-Type"])
        lines = resp.content.decode("utf-8").strip().splitlines()
        self.assertEqual(2, len(lines), "CSV 는 머리글 한 줄 + 값 한 줄이어야 합니다")

    def test_stage_is_null_when_no_measurement_is_given(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.get(_kfs_export_path(event_id), **head)
        row = {f["key"]: f["value"] for f in self._body(resp)["fields"]}
        self.assertIsNone(row["fire_stage"], "측정값을 안 줬는데 단계를 지어냈습니다(D-284 위반)")

    def test_stage_uses_p386_constants_when_measurements_given(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"area_ha": 150, "wind_mps": 1, "duration_hours": 1}
        resp = self.client.get(_qs(_kfs_export_path(event_id), **params), **head)
        row = {f["key"]: f["value"] for f in self._body(resp)["fields"]}
        self.assertEqual("3단계", row["fire_stage"],
                         "150ha 는 P-386 3단계 문턱(100ha)을 넘습니다")

    def test_unknown_format_is_422(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.get(_qs(_kfs_export_path(event_id), fmt="xml"), **head)
        self.assertEqual(422, resp.status_code)

    def test_other_tenant_event_is_404(self) -> None:
        event_id = self._event(self.stream_b, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.get(_kfs_export_path(event_id), **head)
        self.assertEqual(404, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-02 웹훅 이벤트 종류(fws.fire.confirmed/stage_changed/evacuation_
# ordered/extinguished)
# ═══════════════════════════════════════════════════════════════════════════
class F6_02_WebhookEventsTest(F6HttpTest):
    def test_catalog_lists_the_four_annex_kinds(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.get(WEBHOOK_CATALOG, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        types = self._body(resp)["event_types"]
        for kind in ("fws.fire.confirmed", "fws.fire.stage_changed",
                    "fws.fire.evacuation_ordered", "fws.fire.extinguished"):
            self.assertIn(kind, types)
        _write_evidence(
            "FWS-F6-02", title="웹훅 이벤트 종류(fws.fire.confirmed/stage_changed/"
                              "evacuation_ordered/extinguished)",
            test_ref="tests.test_fws_f6.F6_02_WebhookEventsTest."
                    "test_catalog_lists_the_four_annex_kinds",
            method="GET", path=WEBHOOK_CATALOG, request_params={}, response=resp,
            what="GET .../webhook-events/catalog 가 annex 원문 그대로 네 종류를 낸다 "
                "— 카탈로그 실측(발송 실측은 같은 클래스의 다른 시험이 잰다)")

    @override_settings(**SIGNING)
    def test_notify_reaches_a_subscribed_situation_room_with_200(self) -> None:
        from apps.dsm.services import register_webhook_subscription
        from common.tenant_scope import TenantScope

        register_webhook_subscription(
            scope=TenantScope.of(self.user_a),
            endpoint_url="https://situation-room.test.invalid/hook",
            signing_key_ref=KEY_NAME, event_types=(), min_severity="")

        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"kind": "fws.fire.confirmed", "note": "현장 확인 완료"}
        with mock.patch("common.webhook_outbox._post", return_value=(200, "")):
            resp = self.client.post(_qs(_webhook_notify_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("fws.fire.confirmed", body["kind"])
        self.assertGreaterEqual(body["webhook_deliveries"], 1,
                                "구독 기관으로 나간 웹훅이 0건입니다")
        self.assertEqual(body["webhook_deliveries"], body["webhook_succeeded"],
                         "완결조건(소방·시도 상황실 수신 200)이 깨졌습니다")
        _write_evidence(
            "FWS-F6-02", title="웹훅 이벤트 종류(fws.fire.confirmed/stage_changed/"
                              "evacuation_ordered/extinguished)",
            test_ref="tests.test_fws_f6.F6_02_WebhookEventsTest."
                    "test_notify_reaches_a_subscribed_situation_room_with_200",
            method="POST", path=_qs(_webhook_notify_path(event_id), **params),
            request_params=params, response=resp,
            what="kind=fws.fire.confirmed 로 POST 하면 구독한 상황실 주소로 실제 "
                "CAP 1.2 웹훅이 나가고 200 을 받는다(기존 UX-19 dispatch_event 재사용, "
                "_post 만 몽키패치) — 완결조건(수신 200) 실측")

    def test_unknown_kind_is_422(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(
            _qs(_webhook_notify_path(event_id), kind="fws.fire.made_up"), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-03 산불위험예보·위기경보 수신(수동 입력)
# ═══════════════════════════════════════════════════════════════════════════
class F6_03_RiskForecastTest(F6HttpTest):
    def test_record_then_read_back_band_from_p386_thresholds(self) -> None:
        head = self._bearer(self.user_a)
        params = {"risk_index": 70, "source": "manual", "note": "산림과학원 고시 대체 입력"}
        save = self.client.post(_qs(RISK_FORECAST, **params), **head)
        self.assertEqual(200, save.status_code, save.content)
        self.assertEqual("경계", self._body(save)["band"], "70 은 P-386 경계 문턱(66)을 넘습니다")

        read = self.client.get(RISK_FORECAST_MINE, **head)
        self.assertEqual(200, read.status_code)
        body = self._body(read)
        self.assertEqual(70, body["risk_index"])
        self.assertEqual("경계", body["band"])
        _write_evidence(
            "FWS-F6-03", title="산불위험예보·위기경보 수신(산림과학원·산림청 API 또는 수동)",
            test_ref="tests.test_fws_f6.F6_03_RiskForecastTest."
                    "test_record_then_read_back_band_from_p386_thresholds",
            method="GET", path=RISK_FORECAST_MINE, request_params={}, response=read,
            what="POST 로 수동 입력한 위험지수(70)가 P-386 문턱으로 '경계' 띠를 받고 "
                "GET 재조회에 그대로 남는다 — 수동 입력 경로 실측(외부 API 는 미검증이라 "
                "열지 않는다)")

    def test_out_of_range_index_is_422(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.post(_qs(RISK_FORECAST, risk_index=150), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-05 헬기 출동 요청·위치 수신(수동 입력 대안)
# ═══════════════════════════════════════════════════════════════════════════
class F6_05_HelicopterRequestTest(F6HttpTest):
    def test_request_then_list_by_event(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"requesting_org": "산림항공본부 원주기지", "lat": 37.3, "lng": 127.9,
                 "note": "산불 3단계 급수 요청"}
        resp = self.client.post(_qs(_heli_requests_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertIn("request_id", self._body(resp))

        listed = self.client.get(_heli_requests_path(event_id), **head)
        self.assertEqual(200, listed.status_code)
        body = self._body(listed)
        self.assertEqual(1, body["count"])
        self.assertEqual("산림항공본부 원주기지", body["requests"][0]["requesting_org"])
        _write_evidence(
            "FWS-F6-05", title="헬기 출동 요청·위치 수신(산림항공 · 수동 입력 대안)",
            test_ref="tests.test_fws_f6.F6_05_HelicopterRequestTest."
                    "test_request_then_list_by_event",
            method="GET", path=_heli_requests_path(event_id), request_params={},
            response=listed,
            what="POST 로 남긴 헬기 요청(기지·좌표값)이 GET 재조회에 1건으로 남는다 "
                "— 수동 입력 대안 실측(좌표는 값만, 지도는 그리지 않는다)")

    def test_blank_org_is_422(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(_qs(_heli_requests_path(event_id), requesting_org=""), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-06 소방 119 출동 사건 연동(DSM 통해)
# ═══════════════════════════════════════════════════════════════════════════
class F6_06_FireDepartmentLinkTest(F6HttpTest):
    def test_link_reaches_dsm_field_replies(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"dispatch_no": "119-2026-0091", "note": "관할 소방서 출동"}
        resp = self.client.post(_qs(_fire_dept_link_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertIn("reply_id", self._body(resp))

        from apps.dsm.services import field_replies
        from common.tenant_scope import TenantScope

        replies = field_replies(scope=TenantScope.of(self.user_a), event_id=event_id)
        self.assertTrue(
            any("119-2026-0091" in r.text for r in replies),
            "119 연동 기록이 DSM 이 읽는 현장 회신(카드 자리)에 도달하지 않았습니다")
        _write_evidence(
            "FWS-F6-06", title="소방 119 출동 사건 연동(재난안전 App DSM 통해)",
            test_ref="tests.test_fws_f6.F6_06_FireDepartmentLinkTest."
                    "test_link_reaches_dsm_field_replies",
            method="POST", path=_qs(_fire_dept_link_path(event_id), **params),
            request_params=params, response=resp,
            what="출동번호 기록이 K1 현장 회신(DSM 카드가 읽는 자리)에 그대로 도달한다 "
                "— 새 표 없이 DSM 재사용 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-07 대피 푸시 연계 [미확인] · 대안 CBS 초안
# ═══════════════════════════════════════════════════════════════════════════
class F6_07_EvacuationCbsDraftTest(F6HttpTest):
    def test_draft_respects_p386_deadline_and_char_limits(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"area_name": "OO면 OO리 1~5구", "kind": "order"}
        resp = self.client.post(_qs(_evac_cbs_draft_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(8.0, body["deadline_hours"], "지시 대피는 P-386 8시간이어야 합니다")
        self.assertLessEqual(len(body["short"]), 90, "표준 재난문자 90자 상한을 넘었습니다")
        self.assertLessEqual(len(body["long"]), 157, "확장 재난문자 157자 상한을 넘었습니다")
        _write_evidence(
            "FWS-F6-07", title="스마트산림재난 앱 대피 푸시 연계(산림청) [미확인] · "
                              "대안 CBS 초안",
            test_ref="tests.test_fws_f6.F6_07_EvacuationCbsDraftTest."
                    "test_draft_respects_p386_deadline_and_char_limits",
            method="POST", path=_qs(_evac_cbs_draft_path(event_id), **params),
            request_params=params, response=resp,
            what="산림청 앱 푸시는 [미확인]이라 열지 않고, PRD 대안(CBS 초안)만 "
                "짓는다 — P-386 대피 8시간·재난문자 90/157자 상한 실측(대안 기록)")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-08 경찰 교통통제·입산통제 협조 기록
# ═══════════════════════════════════════════════════════════════════════════
class F6_08_PoliceCoordinationTest(F6HttpTest):
    def test_record_then_list_by_event(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"kind": "traffic_control", "note": "OO로 3km 구간 전면 통제"}
        resp = self.client.post(_qs(_police_coord_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertIn("record_id", self._body(resp))

        listed = self.client.get(_police_coord_path(event_id), **head)
        self.assertEqual(200, listed.status_code)
        body = self._body(listed)
        self.assertEqual(1, body["count"])
        self.assertEqual("traffic_control", body["records"][0]["kind"])
        _write_evidence(
            "FWS-F6-08", title="경찰 교통통제·입산통제 협조 기록",
            test_ref="tests.test_fws_f6.F6_08_PoliceCoordinationTest."
                    "test_record_then_list_by_event",
            method="GET", path=_police_coord_path(event_id), request_params={},
            response=listed,
            what="POST 로 남긴 경찰 협조 기록(교통통제)이 GET 재조회에 1건으로 남는다 "
                "— 협조 기록 실측")

    def test_unknown_kind_is_422(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(
            _qs(_police_coord_path(event_id), kind="curfew"), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-10 국립공원·국유림관리소 관할 사건 이첩
# ═══════════════════════════════════════════════════════════════════════════
class F6_10_JurisdictionTransferTest(F6HttpTest):
    def test_transfer_then_list_by_event(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"org_type": "national_park", "target_org": "OO국립공원사무소",
                 "note": "발화지점 국립공원 경계 내"}
        resp = self.client.post(_qs(_jurisdiction_transfer_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertIn("transfer_id", self._body(resp))

        listed = self.client.get(_jurisdiction_transfer_path(event_id), **head)
        self.assertEqual(200, listed.status_code)
        body = self._body(listed)
        self.assertEqual(1, body["count"])
        self.assertEqual("OO국립공원사무소", body["transfers"][0]["target_org"])
        _write_evidence(
            "FWS-F6-10", title="국립공원·국유림관리소 관할 사건 이첩",
            test_ref="tests.test_fws_f6.F6_10_JurisdictionTransferTest."
                    "test_transfer_then_list_by_event",
            method="GET", path=_jurisdiction_transfer_path(event_id), request_params={},
            response=listed,
            what="POST 로 남긴 관할 이첩 기록이 GET 재조회에 1건으로 남는다 — 이첩 "
                "기록 실측")

    def test_unknown_org_type_is_422(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(
            _qs(_jurisdiction_transfer_path(event_id), org_type="city_hall",
               target_org="x"), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-09 스키마 버전·헬스·요청 한도 — **증거를 안 쓴다**(닫힌 절이 아니다).
# 재사용 확인만 한다: 스키마 헤더는 이미 있고, 헬스는 새로 열었다.
# ═══════════════════════════════════════════════════════════════════════════
class F6_09_HealthReuseTest(F6HttpTest):
    def test_schema_header_already_rides_on_every_fws_response(self) -> None:
        """★ 새로 만들지 않았다 — `common/schema_header.py` 전역 미들웨어가 FWS
        응답에도 이미 X-GX-Schema 를 달고 있음을 확인한다(재사용, D-212)."""
        head = self._bearer(self.user_a)
        resp = self.client.get(RISK_FORECAST_MINE, **head)
        self.assertIn("X-GX-Schema", resp)

    def test_health_reuses_dsm_checks_and_reports_ok(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.get(HEALTH, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("ok", body["status"])
        self.assertIn("db", body["checks"])

    def test_health_requires_auth_because_it_is_not_registered_anonymous(self) -> None:
        """★ 정직한 좁힘 — DSM `/api/dsm/health` 와 달리 익명이 아니다(머리말·
        `api.py` 주석 참고 — 익명 래칫 기준선은 이 차선 소유가 아니다)."""
        resp = self.client.get(HEALTH)
        self.assertEqual(401, resp.status_code)
