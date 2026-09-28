# -*- coding: utf-8 -*-
"""FWS App(L4) — F5(드론 운용자) 절 다섯 건의 **HTTP 실측**과
`docs/agent/evidence/SPEC/*.json` 생성 (WO-GX-20260925-15 §5 P-356·357·358·387 · 턴 AM
차선 N2).

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`X-No-Cache`) 헤더를 모든 요청에 싣는다
(`test_fws_app.py`·`test_fws_f2.py` 와 같은 규약). 이 파일은 새 캐시를 만들지
않는다 — 멱등 캐시는 `setUp` 에서 `cache.clear()` 로 비운다.

이 파일이 재는 것 — P-356 승격 규칙 넷 중 ①②(③·④는 게이트·제안 문서)
------------------------------------------------------------------------
    ① 실제 구현    `self.client` 가 `/api/fws/drone/...` 를 실제로 두드린다
    ② 실측 증거    각 시험이 요청·응답을 그대로 `docs/agent/evidence/SPEC/<id>.json`
                    에 적는다(`test_fws_app._write_evidence` 재사용 — 두 벌을
                    만들지 않는다, D-212).

세종 판정 P-387 — 드론 0대, 요청·상태·결과 세 축만
----------------------------------------------------
`apps/fws/drone.py` 머리말 그대로다. 이 시험이 반드시 잡아야 하는 것 하나:
드론의 상태 전이(수락·이륙·귀환)가 **사건의 `response_state` 를 옮기지 않는다**
(다중 행위자 규칙 — 작업지시 「per-drone actions must not close the shared
incident」). `test_recon_state_never_advances_shared_response_state` 가 그것만
잰다.
"""
from __future__ import annotations

from urllib.parse import urlencode

import json

from django.core.cache import cache
from django.test import Client

from tests.no_cache import NO_CACHE
from tests.test_fws_app import FwsHttpTest, _write_evidence

DRONE_RECON_MINE = "/api/fws/drone/missions/mine"
DRONE_FLIGHTS = "/api/fws/drone/flights"
DRONE_FLIGHTS_MINE = "/api/fws/drone/flights/mine"
DRONE_FLIGHTS_MINUTES = "/api/fws/drone/flights/minutes"


def _qs(path: str, **params) -> str:
    live = {k: v for k, v in params.items() if v is not None}
    return f"{path}?{urlencode(live)}" if live else path


def _recon_path(event_id) -> str:
    return f"/api/fws/drone/missions/{event_id}/recon"


def _hotspots_path(event_id) -> str:
    return f"/api/fws/drone/missions/{event_id}/hotspots"


def _hotspots_mine_path(event_id) -> str:
    return f"/api/fws/drone/missions/{event_id}/hotspots/mine"


def _drone_verify_path(event_id) -> str:
    return f"/api/fws/drone/verifications/{event_id}/reply"


class Fws5HttpTest(FwsHttpTest):
    """`FwsHttpTest`(F1 시험의 픽스처·헬퍼)를 그대로 쓴다 — 같은 표를 두 벌로 만들지
    않는다(`test_fws_f2.py::Fws2HttpTest` 와 같은 규약)."""

    def setUp(self) -> None:
        cache.clear()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def tearDown(self) -> None:
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        cache.clear()


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F5-01 정찰 임무 수신(요청·상태)
# ═══════════════════════════════════════════════════════════════════════════
class F5_01_ReconTest(Fws5HttpTest):
    def test_request_accept_airborne_return_and_mine_reflects_state(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)

        request_params = {"action": "request", "radius_m": 300}
        r = self.client.post(_qs(_recon_path(event_id), **request_params), **head)
        self.assertEqual(200, r.status_code, r.content)
        self.assertEqual("request", self._body(r)["action"])
        self.assertEqual(300, self._body(r)["radius_m"])

        for action in ("accept", "airborne", "return"):
            resp = self.client.post(_qs(_recon_path(event_id), action=action), **head)
            self.assertEqual(200, resp.status_code, resp.content)

        mine = self.client.get(DRONE_RECON_MINE, **head)
        self.assertEqual(200, mine.status_code, mine.content)
        body = self._body(mine)
        self.assertEqual(1, body["count"])
        row = body["requests"][0]
        self.assertEqual(event_id, row["event_id"])
        self.assertEqual(300, row["radius_m"])
        self.assertEqual("return", row["state"])
        self.assertIsNotNone(row["requested_at"])
        self.assertIsNotNone(row["returned_at"])
        _write_evidence(
            "FWS-F5-01", title="정찰 임무 수신(발화 추정 좌표·반경) → 열화상 정찰",
            test_ref="tests.test_fws_f5.F5_01_ReconTest."
                    "test_request_accept_airborne_return_and_mine_reflects_state",
            method="GET", path=DRONE_RECON_MINE, request_params={}, response=mine,
            what="정찰 요청(반경 값)→수락→이륙→귀환 상태 전이가 내 대기열(mine)에 "
                "그대로 남는다 — 요청·상태 두 축 실측(K1 이벤트를 드론 쪽에서 "
                "본 것 · 새 표 없음)")

    def test_recon_state_never_advances_shared_response_state(self) -> None:
        """★ 다중 행위자 규칙 — 드론의 상태 전이가 사건을 닫지/옮기지 않는다."""
        from apps.dsm.services import event_detail

        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        for action in ("request", "accept", "airborne", "return"):
            resp = self.client.post(_qs(_recon_path(event_id), action=action), **head)
            self.assertEqual(200, resp.status_code, resp.content)

        ev = event_detail(scope=self.scope_a, event_id=event_id)
        self.assertEqual(
            "occurred", ev.response_state,
            "드론의 정찰 상태 전이가 사건의 response_state 를 옮겼습니다 — "
            "per-drone 행위가 공유 사건을 닫으면 안 됩니다")

    def test_airborne_without_accept_is_409(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        self.client.post(_qs(_recon_path(event_id), action="request"), **head)
        resp = self.client.post(_qs(_recon_path(event_id), action="airborne"), **head)
        self.assertEqual(409, resp.status_code, resp.content)

    def test_unknown_action_is_422(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(_qs(_recon_path(event_id), action="hover"), **head)
        self.assertEqual(422, resp.status_code)

    def test_other_tenant_event_is_404(self) -> None:
        event_id = self._event(self.stream_b, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(_qs(_recon_path(event_id), action="request"), **head)
        self.assertEqual(404, resp.status_code, resp.content)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F5-02 열점·화선 표시(좌표 목록 값 — 지도 없음)
# ═══════════════════════════════════════════════════════════════════════════
class F5_02_HotspotsTest(Fws5HttpTest):
    def test_submit_points_and_fireline_then_read_back(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        points = [{"lat": 36.11, "lng": 127.21}, {"lat": 36.12, "lng": 127.22}]
        fireline = [{"lat": 36.10, "lng": 127.20}, {"lat": 36.13, "lng": 127.23}]
        params = {"points_json": json.dumps(points), "fireline_json": json.dumps(fireline)}
        resp = self.client.post(_qs(_hotspots_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(2, len(body["points"]))
        self.assertEqual(2, len(body["fireline"]))

        mine = self.client.get(_hotspots_mine_path(event_id), **head)
        self.assertEqual(200, mine.status_code, mine.content)
        mine_body = self._body(mine)
        self.assertEqual(1, mine_body["count"])
        self.assertEqual(points, mine_body["batches"][0]["points"])
        self.assertEqual(fireline, mine_body["batches"][0]["fireline"])
        _write_evidence(
            "FWS-F5-02", title="열점·화선 표시(열화상 프레임 → 지도 폴리라인)",
            test_ref="tests.test_fws_f5.F5_02_HotspotsTest."
                    "test_submit_points_and_fireline_then_read_back",
            method="GET", path=_hotspots_mine_path(event_id), request_params={},
            response=mine,
            what="열점 2점·화선 2점(좌표 목록 값)을 제출한 뒤 재조회에 그대로 "
                "보인다 — 값 실측(지도·폴리라인 렌더는 §0.4 인접 금지구역 밖이라 "
                "만들지 않았다)")

    def test_empty_points_and_fireline_is_422(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(_hotspots_path(event_id), **head)
        self.assertEqual(422, resp.status_code)

    def test_single_point_fireline_is_422(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"fireline_json": json.dumps([{"lat": 36.1, "lng": 127.1}])}
        resp = self.client.post(_qs(_hotspots_path(event_id), **params), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F5-03 확인 회신(산불 맞음/오인 · 참조) — F1-06 문 재사용
# ═══════════════════════════════════════════════════════════════════════════
class F5_03_ConfirmResultTest(Fws5HttpTest):
    def test_fire_confirmed_requires_attachment_ref(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)

        missing = self.client.post(
            _qs(_drone_verify_path(event_id), result="fire_confirmed"), **head)
        self.assertEqual(422, missing.status_code, missing.content)

        params = {"result": "fire_confirmed", "attachment_ref": "minio://drone/1.jpg"}
        resp = self.client.post(_qs(_drone_verify_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("fire_confirmed", body["result"])
        self.assertEqual("minio://drone/1.jpg", body["attachment_ref"])
        self.assertEqual("confirmed", body["verdict"])
        _write_evidence(
            "FWS-F5-03", title="확인 회신(산불 맞음/오인 · 사진·열화상)",
            test_ref="tests.test_fws_f5.F5_03_ConfirmResultTest."
                    "test_fire_confirmed_requires_attachment_ref",
            method="POST", path=_qs(_drone_verify_path(event_id), **params),
            request_params=params, response=resp,
            what="드론 확인 회신(산불 맞음 + 사진·열화상 참조)이 K1 사건의 verdict "
                "를 confirmed 로 바꾼다 — F1-06 문 재사용(P-357) + 참조 값 필수화 "
                "실측(참조 없이 fire_confirmed 는 422)")

    def test_false_alarm_does_not_require_attachment_ref(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"result": "false_alarm", "reason_code": "fog_or_cloud"}
        resp = self.client.post(_qs(_drone_verify_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertIsNone(self._body(resp)["attachment_ref"])


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F5-08 비행 기록·배터리·기체 상태
# ═══════════════════════════════════════════════════════════════════════════
class F5_08_FlightLogTest(Fws5HttpTest):
    def test_log_is_recorded_and_read_back(self) -> None:
        head = self._bearer(self.user_a)
        params = {"source": "dji", "airframe_code": "M30T-7", "battery_pct": 68.5,
                 "flight_minutes": 22}
        resp = self.client.post(_qs(DRONE_FLIGHTS, **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertEqual("dji", self._body(resp)["source"])

        mine = self.client.get(DRONE_FLIGHTS_MINE, **head)
        self.assertEqual(200, mine.status_code, mine.content)
        mine_body = self._body(mine)
        self.assertEqual(1, mine_body["count"])
        row = mine_body["flights"][0]
        self.assertEqual("M30T-7", row["airframe_code"])
        self.assertEqual(68.5, row["battery_pct"])
        self.assertEqual(22, row["flight_minutes"])
        _write_evidence(
            "FWS-F5-08", title="비행 기록·배터리·기체 상태",
            test_ref="tests.test_fws_f5.F5_08_FlightLogTest."
                    "test_log_is_recorded_and_read_back",
            method="GET", path=DRONE_FLIGHTS_MINE, request_params={}, response=mine,
            what="POST /drone/flights(dji · M30T-7 · 배터리 68.5 · 22분) 뒤 GET "
                "/drone/flights/mine 에 그 값이 그대로 보인다 — 비행 기록 실측 "
                "(source 는 DJI 등 연동 어댑터의 값 자리뿐, 실제 API 호출 0건)")

    def test_battery_out_of_range_is_422(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.post(_qs(DRONE_FLIGHTS, battery_pct=150), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F5-10 계량(비행 분) — F5-08 의 값을 센다
# ═══════════════════════════════════════════════════════════════════════════
class F5_10_FlightMinutesTest(Fws5HttpTest):
    def test_flight_minutes_are_summed(self) -> None:
        head = self._bearer(self.user_a)
        self.client.post(_qs(DRONE_FLIGHTS, flight_minutes=15), **head)
        self.client.post(_qs(DRONE_FLIGHTS, flight_minutes=27.5), **head)

        resp = self.client.get(DRONE_FLIGHTS_MINUTES, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(42.5, body["flight_minutes_total"])
        self.assertEqual(2, body["flight_count"])
        _write_evidence(
            "FWS-F5-10", title="계량(비행 분)",
            test_ref="tests.test_fws_f5.F5_10_FlightMinutesTest."
                    "test_flight_minutes_are_summed",
            method="GET", path=DRONE_FLIGHTS_MINUTES, request_params={},
            response=resp,
            what="비행 기록 두 건(15분·27.5분) 뒤 GET /drone/flights/minutes 의 "
                "flight_minutes_total 이 42.5 — F5-08 값을 세기만 한다(새 표 없음, "
                "계량 실측)")
