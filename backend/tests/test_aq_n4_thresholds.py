# -*- coding: utf-8 -*-
"""FWS-F2-07 · FWS-F1-10 안전경보 문턱 = 기관(테넌트) 설정값 (턴 AQ · 차선 N4 · P-434).

세종 판정 원문: 「명세에 없는 숫자는 기본값이 아니라 기관 설정이다 — 미설정은 「대기」로
보인다」.

이 파일이 재는 것
------------------
    ① 미설정 — GET 이 세 칸 모두 「대기」 · 풍향 0→180 도 판독에도 발화 0 ·
       응답 `threshold_status="대기"`(거짓 초록 아님).
    ② U5 저장 → **새 GET 재조회**에 값·「설정됨」 → 넘으면 발화 · 안 넘으면 0
       (풍향 급변 · 투하구역 이탈 둘 다). 감사 줄 1(누가·전→후).
    ③ 다른 기관 격리 — A 기관 값이 B 기관 조회·판정에 새지 않는다.
    ④ 비U5 쓰기 403 · 범위 밖 422 (읽기는 같은 기관 누구나 200).

시험에서 넣는 숫자(45도·10분·300m)는 **기관이 넣었다고 치는 시험 입력**일 뿐 기본값·
권장값이 아니다 — 서버 코드에는 그런 숫자가 없다.

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`FwsHttpTest` 가 Client 에 싣는다) + 각 시험
`setUp` 에서 `cache.clear()`.
"""
from __future__ import annotations

import math

from django.apps import apps
from django.core.cache import cache

from tests.test_fws_app import ALERTS, FwsHttpTest, _qs

THRESHOLDS = "/api/fws/admin/safety-thresholds"
CENTER = (36.35, 127.38)
_M_PER_DEG_LAT = 6_371_000.0 * math.pi / 180.0

#: 시험 입력(기관이 저장했다고 치는 값) — 기본값이 아니다(머리말).
SET_ANGLE, SET_WINDOW, SET_RADIUS = 45.0, 10.0, 300.0


def _wind_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/wind-reading"


def _drop_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/drop-zone-position"


def _aircraft_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/aircraft-request"


class ThresholdFixture(FwsHttpTest):
    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        from core.middleware.refresh_token import thread_local

        thread_local.request = None
        super().setUpTestData()
        Role = apps.get_model("role", "Role")
        admin_role, _ = Role.objects.get_or_create(
            code="admin", defaults={"role_name": "admin"})
        cls.user_a.roles.add(admin_role)
        cls.user_b.roles.add(admin_role)
        #: 같은 기관 A 의 비관리자(현장 대원) — 쓰기 403 · 읽기 200 을 잰다.
        cls.user_a_field = cls._user("aq_n4_field_a", cls.group_a, cls.role_a)

    def setUp(self) -> None:
        super().setUp()
        cache.clear()

    def _get(self, head) -> dict:
        resp = self.client.get(THRESHOLDS, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        return self._body(resp)

    def _save(self, head, **values):
        return self.client.post(_qs(THRESHOLDS, **values), **head)

    def _post_ok(self, path, head, **params) -> dict:
        resp = self.client.post(_qs(path, **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        return self._body(resp)

    def _alert_ids(self, head) -> set:
        resp = self.client.get(ALERTS, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        return {r["delivery_id"] for r in self._body(resp)["alerts"]}

    @staticmethod
    def _by_name(body) -> dict:
        return {f["name"]: f for f in body["fields"]}


class UnsetMeansWaitingTest(ThresholdFixture):
    def test_unset_is_waiting_and_fires_nothing(self) -> None:
        head = self._bearer(self.user_a)
        body = self._get(head)
        self.assertFalse(body["all_set"])
        for field in body["fields"]:
            self.assertIsNone(field["value"], field)
            self.assertEqual("대기", field["status"], field)

        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        before = self._alert_ids(head)
        self._post_ok(_wind_path(event_id), head, direction_deg=0.0)
        wind = self._post_ok(_wind_path(event_id), head, direction_deg=180.0)
        self.assertTrue(wind["threshold_unset"])
        self.assertEqual("대기", wind["threshold_status"])
        self.assertFalse(wind["judged"])
        self.assertFalse(wind["alert_fired"], "기관 값이 없는데 경보를 쐈다 — 값을 지어냈다")
        self.assertEqual(before, self._alert_ids(head))


class SetThenJudgeTest(ThresholdFixture):
    def test_saved_value_is_reread_and_drives_both_rules(self) -> None:
        head = self._bearer(self.user_a)
        saved = self._save(head, wind_shift_angle_deg=SET_ANGLE,
                           wind_shift_window_minutes=SET_WINDOW,
                           drop_zone_exit_radius_m=SET_RADIUS)
        self.assertEqual(200, saved.status_code, saved.content)

        cache.clear()
        reread = self._by_name(self._get(head))  # 새 GET 재조회
        self.assertEqual(SET_ANGLE, reread["wind_shift_angle_deg"]["value"])
        self.assertEqual(SET_WINDOW, reread["wind_shift_window_minutes"]["value"])
        self.assertEqual(SET_RADIUS, reread["drop_zone_exit_radius_m"]["value"])
        for field in reread.values():
            self.assertEqual("설정됨", field["status"])

        # 감사 줄 — 누가 · 전 → 후.
        AuditLogs = apps.get_model("logger", "AuditLogs")
        row = (AuditLogs._base_manager
               .filter(logger_name="guardianx.fws.admin_u5",
                       api_name="admin.safety_thresholds")
               .order_by("-id").first())
        self.assertIsNotNone(row)
        self.assertEqual(self.user_a.pk, row.user_id)
        self.assertIsNone(row.data_after["before"]["wind_shift_angle_deg"])
        self.assertEqual(SET_ANGLE, row.data_after["wind_shift_angle_deg"])

        # ① 풍향 급변 — 문턱 그대로(45도)는 0, 넘으면(46도) 발화.
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        before = self._alert_ids(head)
        self._post_ok(_wind_path(event_id), head, direction_deg=10.0)
        at = self._post_ok(_wind_path(event_id), head, direction_deg=55.0)
        self.assertTrue(at["judged"])
        self.assertEqual("설정됨", at["threshold_status"])
        self.assertFalse(at["alert_fired"])
        self.assertEqual(before, self._alert_ids(head))
        above = self._post_ok(_wind_path(event_id), head, direction_deg=101.0)
        self.assertTrue(above["alert_fired"], above)
        self.assertEqual(SET_ANGLE, above["threshold_deg"])
        self.assertTrue(self._alert_ids(head) - before)

        # ② 투하구역 이탈 — 반경 안 0 · 밖 발화.
        self._post_ok(_aircraft_path(event_id), head, requesting_org="OO소방서",
                      drop_zone_lat=CENTER[0], drop_zone_lng=CENTER[1],
                      base="OO공항", eta="15분")
        inside = self._post_ok(_drop_path(event_id), head,
                               lat=CENTER[0] + 299.0 / _M_PER_DEG_LAT, lng=CENTER[1])
        self.assertTrue(inside["judged"])
        self.assertFalse(inside["alert_fired"])
        outside = self._post_ok(_drop_path(event_id), head,
                                lat=CENTER[0] + 301.0 / _M_PER_DEG_LAT, lng=CENTER[1])
        self.assertTrue(outside["alert_fired"], outside)
        self.assertEqual(SET_RADIUS, outside["radius_m"])


class OtherTenantDoesNotLeakTest(ThresholdFixture):
    def test_tenant_a_value_is_invisible_to_tenant_b(self) -> None:
        head_a = self._bearer(self.user_a)
        resp = self._save(head_a, wind_shift_angle_deg=SET_ANGLE,
                          wind_shift_window_minutes=SET_WINDOW,
                          drop_zone_exit_radius_m=SET_RADIUS)
        self.assertEqual(200, resp.status_code, resp.content)

        head_b = self._bearer(self.user_b)
        body_b = self._get(head_b)
        for field in body_b["fields"]:
            self.assertIsNone(field["value"], "A 기관 값이 B 기관 조회에 샜다")
            self.assertEqual("대기", field["status"])

        event_b = self._event(self.stream_b, severity="critical", event_type="fire")
        self._post_ok(_wind_path(event_b), head_b, direction_deg=0.0)
        wind_b = self._post_ok(_wind_path(event_b), head_b, direction_deg=180.0)
        self.assertEqual("대기", wind_b["threshold_status"])
        self.assertFalse(wind_b["alert_fired"], "A 기관 문턱이 B 기관 판정에 샜다")


class WriteGuardTest(ThresholdFixture):
    def test_non_u5_write_is_403_and_read_is_200(self) -> None:
        head = self._bearer(self.user_a_field)
        resp = self._save(head, wind_shift_angle_deg=SET_ANGLE)
        self.assertEqual(403, resp.status_code, resp.content)
        self.assertEqual("대기", self._by_name(self._get(head))["wind_shift_angle_deg"]["status"])

    def test_out_of_physical_range_is_422(self) -> None:
        head = self._bearer(self.user_a)
        for bad in ({"wind_shift_angle_deg": 0}, {"wind_shift_angle_deg": 181},
                    {"wind_shift_window_minutes": -1}, {"drop_zone_exit_radius_m": 0}):
            resp = self._save(head, **bad)
            self.assertEqual(422, resp.status_code, (bad, resp.content))
