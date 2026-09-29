# -*- coding: utf-8 -*-
"""FWS-F2-07 · FWS-F1-10 — 풍향 급변 · 헬기 투하 구역 이탈 **판정 규칙**
(WO-GX-20261001-19 턴 AP · 차선 N2b · P-421 ②).

이 파일이 재는 것
------------------
    ① 풍향 급변 — 문턱 **아래**(= 문턱값 그대로)는 경보 없음 · 문턱 **위**는
       경보 발송 → 기존 안전경보 문(GET /api/fws/alerts)에 도달 → ack.
    ② 헬기 투하 구역 이탈 — F4-04 승인 좌표에서 반경 **안**(299m)은 경보 없음 ·
       반경 **밖**(301m)은 경보 발송 → 같은 문으로 도달.
    ③ 규정값이 없으면(명세에 숫자가 없다 — 이름만 있다) **판정하지 않는다** —
       `judged=False`·`threshold_unset=True` 로 말한다(「안 쐈다」와 「못 쟀다」를
       같은 모양으로 내지 않는다).

규정값은 `apps.fws.constants` 에서 이름으로 읽힌다(그 파일은 조율자 소유) — 시험은
`mock.patch.object(..., create=True)` 로 **시험용 문턱을 주입**한다. 주입한 값은
규정값이 아니다(증거 표의 「문턱 규정값」 행이 열린 채 남는 이유).

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`test_fws_app.py` 와 같은 규약).
"""
from __future__ import annotations

import math
from unittest import mock

from django.core.cache import cache
from django.test import Client

from apps.fws import constants as fws_constants
from tests.no_cache import NO_CACHE
from tests.test_ap_n2_fws_quiet_hours import _write_evidence_full
from tests.test_fws_app import ALERTS, FwsHttpTest, _qs

#: 시험용 문턱 — **규정값이 아니다**(명세에 숫자 없음). 경계를 재려고 주입할 뿐.
TEST_ANGLE_DEG = 45.0
TEST_WINDOW_MIN = 10.0
TEST_RADIUS_M = 300.0

CENTER = (36.35, 127.38)
_M_PER_DEG_LAT = 6_371_000.0 * math.pi / 180.0


def _wind_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/wind-reading"


def _drop_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/drop-zone-position"


def _aircraft_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/aircraft-request"


def _ack_path(delivery_id) -> str:
    return f"/api/fws/alerts/{delivery_id}/ack"


RETRO = ("P-421 채움 · 확인한 것 — 턴 AP 차선 N2b · 2026-09-29 · 판정 규칙 "
         "(apps/fws/alerts.py::report_wind_direction·report_drop_zone_position)을 HTTP 로 "
         "두드려 문턱 아래는 경보 0 · 문턱 위는 notify_event→K2 발송→GET /api/fws/alerts "
         "도달→ack 를 대조했다. 문턱 숫자는 명세에 없어 constants.py 에 이름만 요청했고 "
         "(값 None → judged=false), 시험은 주입값으로 경계를 쟀다 — 규정값 행은 열린 채 둔다.")


def _patch_thresholds(angle=TEST_ANGLE_DEG, window=TEST_WINDOW_MIN, radius=TEST_RADIUS_M):
    return [
        mock.patch.object(fws_constants, "WIND_SHIFT_ANGLE_DEG", angle, create=True),
        mock.patch.object(fws_constants, "WIND_SHIFT_WINDOW_MINUTES", window, create=True),
        mock.patch.object(fws_constants, "DROP_ZONE_EXIT_RADIUS_M", radius, create=True),
    ]


class _SafetyBase(FwsHttpTest):
    def setUp(self) -> None:
        cache.clear()
        self.client = Client(raise_request_exception=False, **NO_CACHE)
        self._patches = []

    def _with_thresholds(self, **kw) -> None:
        for p in _patch_thresholds(**kw):
            p.start()
            self._patches.append(p)
        self.addCleanup(lambda: [p.stop() for p in self._patches])

    def _post(self, path, head, **params):
        resp = self.client.post(_qs(path, **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        return resp

    def _my_alert_ids(self, head) -> set:
        resp = self.client.get(ALERTS, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        return {r["delivery_id"] for r in self._body(resp)["alerts"]}


class WindShiftRuleTest(_SafetyBase):
    def test_wind_shift_boundary_and_delivery(self) -> None:
        self._with_thresholds()
        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        before = self._my_alert_ids(head)

        first = self._body(self._post(_wind_path(event_id), head, direction_deg=10.0))
        self.assertFalse(first["alert_fired"])
        self.assertFalse(first["judged"], "직전 판독이 없으면 판정하지 않는다")

        #: 문턱값 **그대로**(45도 변화)는 아직 급변이 아니다(`>` 이지 `>=` 아니다).
        at_threshold = self._body(self._post(_wind_path(event_id), head, direction_deg=55.0))
        self.assertTrue(at_threshold["judged"])
        self.assertEqual(45.0, at_threshold["diff_deg"])
        self.assertFalse(at_threshold["alert_fired"])
        self.assertEqual(0, at_threshold["delivered_count"])
        self.assertEqual(before, self._my_alert_ids(head), "문턱 아래인데 알림이 왔다")

        #: 문턱 위(46도 변화) — 경보가 기존 안전경보 문으로 실제로 도달한다.
        above_resp = self._post(_wind_path(event_id), head, direction_deg=101.0)
        above = self._body(above_resp)
        self.assertTrue(above["alert_fired"], above)
        self.assertEqual(46.0, above["diff_deg"])
        self.assertGreaterEqual(above["delivered_count"], 1)
        new_ids = self._my_alert_ids(head) - before
        self.assertTrue(new_ids, "경보가 발송됐다는데 GET /api/fws/alerts 에 안 보인다")

        delivery_id = sorted(new_ids)[-1]
        ack = self.client.post(_ack_path(delivery_id), **head)
        self.assertEqual(200, ack.status_code, ack.content)
        self.assertTrue(self._body(ack)["acknowledged"])

        _write_wind_evidence(event_id, above_resp)

    def test_threshold_unset_means_not_judged(self) -> None:
        self._with_thresholds(angle=None, window=None, radius=None)
        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        self._post(_wind_path(event_id), head, direction_deg=0.0)
        body = self._body(self._post(_wind_path(event_id), head, direction_deg=180.0))
        self.assertTrue(body["threshold_unset"])
        self.assertFalse(body["judged"])
        self.assertFalse(body["alert_fired"], "규정값이 없는데 경보를 쐈다 — 값을 지어냈다")

    def test_out_of_range_direction_is_422(self) -> None:
        self._with_thresholds()
        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        resp = self.client.post(_qs(_wind_path(event_id), direction_deg=360.0), **head)
        self.assertEqual(422, resp.status_code, resp.content)


class DropZoneExitRuleTest(_SafetyBase):
    def test_drop_zone_boundary_and_delivery(self) -> None:
        self._with_thresholds()
        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")

        #: 중심이 없으면 판정할 수 없다 — 422.
        no_center = self.client.post(
            _qs(_drop_path(event_id), lat=CENTER[0], lng=CENTER[1]), **head)
        self.assertEqual(422, no_center.status_code, no_center.content)

        self._post(_aircraft_path(event_id), head, requesting_org="OO소방서",
                   drop_zone_lat=CENTER[0], drop_zone_lng=CENTER[1],
                   base="OO공항", eta="15분")
        before = self._my_alert_ids(head)

        inside = self._body(self._post(
            _drop_path(event_id), head,
            lat=CENTER[0] + 299.0 / _M_PER_DEG_LAT, lng=CENTER[1]))
        self.assertTrue(inside["judged"])
        self.assertLess(inside["distance_m"], TEST_RADIUS_M)
        self.assertFalse(inside["alert_fired"])
        self.assertEqual(before, self._my_alert_ids(head), "반경 안인데 알림이 왔다")

        outside_resp = self._post(
            _drop_path(event_id), head,
            lat=CENTER[0] + 301.0 / _M_PER_DEG_LAT, lng=CENTER[1])
        outside = self._body(outside_resp)
        self.assertGreater(outside["distance_m"], TEST_RADIUS_M)
        self.assertTrue(outside["alert_fired"], outside)
        self.assertGreaterEqual(outside["delivered_count"], 1)
        self.assertTrue(self._my_alert_ids(head) - before,
                        "이탈 경보가 발송됐다는데 GET /api/fws/alerts 에 안 보인다")

        _write_drop_evidence(event_id, outside_resp)


# ═══════════════════════════════════════════════════════════════════════════
# 증거 — F2-07 은 두 규칙이 다 있어야 하므로 풍향 시험·투하 시험이 각자 자기
# 응답을 남기되 표는 같은 한 벌(_f2_07_parts)이다.
# ═══════════════════════════════════════════════════════════════════════════
def _rule_rows() -> list:
    return [
        {"part": "문턱 규정값(선언 == 설정) — 풍향 급변 각도·시간창 · 투하 구역 반경",
         "where": "backend/apps/fws/alerts.py::_threshold 가 apps.fws.constants 의 "
                  "WIND_SHIFT_ANGLE_DEG·WIND_SHIFT_WINDOW_MINUTES·DROP_ZONE_EXIT_RADIUS_M "
                  "를 이름으로 읽는다 — 명세 §5.1 F1-10·F2-07 은 말만 있고 숫자가 없다",
         "status": "없음 — 명세·조사 메모에 숫자가 없어 값을 짓지 않았다(이름만 · 값 "
                   "None → 운영에서 judged=false). 세종 결정으로 값이 들어와야 운영 판정이 "
                   "돈다(시험은 주입값으로 경계만 쟀다)"},
        {"part": "풍향 실측원 — 기상 관측(기상청·산림청 AWS) 실연동",
         "where": "입력 문은 POST /api/fws/command/incidents/{id}/wind-reading "
                  "(수동·연계용) 하나뿐",
         "excluded_by": "P-428",
         "excluded_why": "외부 기관 실연동(기상 관측 API)은 이 턴이 채우지 않는다 — 판정 "
                         "규칙은 들어온 판독을 읽어 실제로 쏜다",
         "status": "excluded_by: P-428 — 외부 기상 관측 실연동 부분만 결정 제외"},
    ]


def _wind_row() -> dict:
    return {"part": "'풍향 급변' 판정 → 안전 경보 자동 발송",
            "where": "backend/apps/fws/alerts.py::report_wind_direction → "
                     "_fire_safety_alert → dsm_services.notify_event → K2 send · "
                     "POST /api/fws/command/incidents/{id}/wind-reading",
            "status": "measured: 문턱값 그대로(45도 변화)는 alert_fired=false·알림 0 · "
                      "46도 변화는 alert_fired=true·delivered_count>=1·GET /api/fws/alerts "
                      "에 새 행 · ack 200(시험 주입 문턱 — 규정값은 아래 열린 행)"}


def _drop_row() -> dict:
    return {"part": "'헬기 투하 구역 이탈' 판정 → 안전 경보 자동 발송",
            "where": "backend/apps/fws/alerts.py::report_drop_zone_position(F4-04 승인 "
                     "drop_zone 을 중심으로 재사용) · POST /api/fws/command/incidents/"
                     "{id}/drop-zone-position",
            "status": "measured: 중심에서 299m 는 alert_fired=false·알림 0 · 301m 는 "
                      "alert_fired=true·delivered_count>=1·GET /api/fws/alerts 에 새 행 · "
                      "승인 없으면 422(시험 주입 반경 — 규정값은 열린 행)"}


def _f2_07_parts() -> list:
    return [
        {"part": "안전 경보 도달(내게 온 알림 목록)",
         "where": "backend/apps/fws/alerts.py::my_alerts · GET /api/fws/alerts",
         "status": "measured: 경보 발송 뒤 GET /api/fws/alerts 에 새 delivery 가 잡힘"},
        {"part": "확인(ack) — 완결조건",
         "where": "backend/apps/fws/alerts.py::ack_alert · POST /api/fws/alerts/{id}/ack",
         "status": "measured: 풍향 급변 경보 delivery 를 ack → acknowledged=true"},
        _wind_row(),
        _drop_row(),
    ] + _rule_rows() + [
        {"part": "헬기 위치 실측원 — 항공기 위치(산림항공본부) 실연동",
         "where": "입력 문은 POST .../drop-zone-position(수동·연계용) 하나뿐",
         "excluded_by": "P-428",
         "excluded_why": "외부 기관 실연동(헬기 운항 위치)은 이 턴이 채우지 않는다 — 판정 "
                         "규칙은 들어온 위치를 읽어 실제로 쏜다",
         "status": "excluded_by: P-428 — 헬기 위치 실연동 부분만 결정 제외"},
        {"part": "화면 — 진화대 임무 화면(FM3)에서 안전 경보 수신·확인",
         "where": "frontend/src/features/fws/pages/FieldHome.tsx — /api/fws/alerts 를 "
                  "부르지 않는다(grep · 경보 목록·확인 버튼은 PatrolHome 에만 있다)",
         "status": "없음 — F2 진화대 화면에 안전 경보 칸·확인 버튼이 없다(명세 FM3 "
                   "「풍향 급변 경보 시 이 칸이 빨강」)"},
    ]


def _f1_10_parts() -> list:
    return [
        {"part": "K2 발송이 내 목록(GET /api/fws/alerts)에 '도달'로 나타난다",
         "where": "backend/apps/fws/alerts.py::my_alerts — GET /api/fws/alerts",
         "status": "measured: 풍향 급변 경보 발송 뒤 목록에 새 delivery"},
        {"part": "확인(ack) 처리",
         "where": "backend/apps/fws/alerts.py::ack_alert — POST /api/fws/alerts/{id}/ack",
         "status": "measured: 같은 시험 — ack 200 · acknowledged=true"},
        {"part": "화면에서 알림 목록 표시 + 확인 버튼",
         "where": "frontend/src/features/fws/pages/PatrolHome.tsx(List + ackButton · "
                  "handleAck 가 alertAck 엔드포인트를 부른다)",
         "status": "present: 턴 AO 소급이 코드로 확인한 행 그대로(이 차선은 화면을 "
                   "바꾸지 않았다)"},
        _wind_row(),
    ] + _rule_rows() + [
        {"part": "'대피 지시'·'철수' 전용 알림이 F1 감시원의 /alerts 목록에 뜨는가",
         "where": "backend/apps/fws/integration.py·office2.py(대피 문안 초안·웹푸시 "
                  "훈련은 F3/F6 쪽) — F1 /alerts 로 잇는 트리거·시험 없음",
         "status": "부분: 대피 문안·훈련 채널은 있으나 대피 지시·철수를 F1 안전 알림으로 "
                   "보내는 트리거는 미실측(이 차선 범위 밖 — 턴 AO 소급 행 그대로)"},
    ]


def _write_wind_evidence(event_id, resp) -> None:
    params = {"direction_deg": 101.0}
    for clause_id, title, parts in (
            ("FWS-F2-07", "안전 경보 수신(풍향 급변·헬기 투하 구역 이탈)", _f2_07_parts()),
            ("FWS-F1-10", "안전 알림 수신(풍향 급변·대피 지시·철수)", _f1_10_parts())):
        _write_evidence_full(
            clause_id, title=title, title_parts=parts,
            test_ref="tests.test_ap_n2_fws_safety_alerts.WindShiftRuleTest."
                     "test_wind_shift_boundary_and_delivery",
            method="POST", path=_qs(_wind_path(event_id), **params),
            request_params=params, response=resp,
            what="풍향 판독 10→55도(45도 = 문턱 그대로 · 경보 없음) → 101도(46도 · 경보 "
                 "발송) — 경보가 GET /api/fws/alerts 에 도달하고 ack 됨을 실측. 헬기 "
                 "투하 구역 이탈은 DropZoneExitRuleTest(299m 없음 · 301m 발송)가 같은 "
                 "파일에서 잰다. 문턱은 시험 주입값(명세에 숫자 없음)",
            retro=RETRO)


def _write_drop_evidence(event_id, resp) -> None:
    #: F2-07 은 두 규칙을 다 부른다 — 이 시험(파일 안 정의 순서로 풍향 시험 뒤에
    #: 돈다)이 같은 표로 자기 응답(투하 구역 이탈)을 남긴다. 풍향 응답은 F1-10
    #: 증거에 남는다.
    center = {"lat": CENTER[0], "lng": CENTER[1]}
    _write_evidence_full(
        "FWS-F2-07", title="안전 경보 수신(풍향 급변·헬기 투하 구역 이탈)",
        title_parts=_f2_07_parts(),
        test_ref="tests.test_ap_n2_fws_safety_alerts.DropZoneExitRuleTest."
                 "test_drop_zone_boundary_and_delivery",
        method="POST", path=_drop_path(event_id),
        request_params={"center": center, "offset_m": 301.0}, response=resp,
        what="F4-04 승인 투하 구역 중심에서 299m(경보 없음) → 301m(경보 발송 · GET "
             "/api/fws/alerts 도달) 실측. 풍향 급변(45도 그대로 없음 · 46도 발송 · ack)은 "
             "WindShiftRuleTest 가 같은 표로 잰다(F1-10 증거에 그 응답). 문턱은 시험 "
             "주입값(명세에 숫자 없음)",
        retro=RETRO)
