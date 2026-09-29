# -*- coding: utf-8 -*-
"""FWS-F5-10 반쪽 채움 실측 (턴 AP · WO-19 · P-419 · 차선 N4).

`docs/agent/evidence/SPEC/FWS-F5-10.json` 의 옛 title_parts 가 연 두 행을 닫는다:
    「월별 필터(month) 검증 안 됨」 — `drone.py` 는 고치지 않는다. 이미 있는
      `GET /drone/flights/minutes?month=` 를 실제로 다른 달 값 둘로 두드려
      **검증**한다(테스트만 · 코드 변경 없음).
    「월 표(완결 조건) 없음」 — `apps/fws/ap_f5.py::flight_minutes_monthly_table`
      (새 door)이 채운다.

세 번째 열린 행(공용 계량 커널(S-20)과의 연계)은 이 시험이 닫지 않는다 —
공용 커널을 고치는 일은 이 턴 범위 밖이다(정직하게 열어 둔다).
"""
from __future__ import annotations

from django.core.cache import cache
from django.test import Client

from tests.no_cache import NO_CACHE
from tests.test_fws_app import FwsHttpTest, _write_evidence

FLIGHTS = "/api/fws/drone/flights"
FLIGHTS_MINUTES = "/api/fws/drone/flights/minutes"
MONTHLY_TABLE = "/api/fws/ap/drone/flights/minutes/monthly-table"


class Fws5_10ApHttpTest(FwsHttpTest):
    def setUp(self) -> None:
        cache.clear()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def tearDown(self) -> None:
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        cache.clear()

    def _log(self, head, *, minutes, logged_month_hint=""):
        resp = self.client.post(
            f"{FLIGHTS}?flight_minutes={minutes}&source=dji&airframe_code=M30T",
            **head)
        self.assertEqual(200, resp.status_code, resp.content)
        return self._body(resp)


class F5_10_MonthFilterTest(Fws5_10ApHttpTest):
    def test_month_param_actually_filters_by_real_month(self) -> None:
        head = self._bearer(self.user_a)
        self._log(head, minutes=10)

        this_month = self._body(
            self.client.get(FLIGHTS_MINUTES, **head))["month"]
        self.assertIsNone(this_month, "month 를 안 줬는데 응답에 값이 있습니다.")

        # 실제 이번 달로 좁히면 방금 기록이 잡혀야 한다.
        from django.utils import timezone

        real_month = timezone.localtime(timezone.now()).strftime("%Y-%m")
        this = self.client.get(f"{FLIGHTS_MINUTES}?month={real_month}", **head)
        self.assertEqual(200, this.status_code, this.content)
        this_body = self._body(this)
        self.assertEqual(real_month, this_body["month"])
        self.assertGreaterEqual(this_body["flight_count"], 1,
                                "실제 이번 달로 좁혔는데 방금 기록이 안 잡힙니다.")

        # 있을 수 없는 먼 과거 달로 좁히면 0 이어야 한다 — 필터가 실제로 걸린다.
        past = self.client.get(f"{FLIGHTS_MINUTES}?month=1999-01", **head)
        self.assertEqual(200, past.status_code, past.content)
        past_body = self._body(past)
        self.assertEqual(0, past_body["flight_count"],
                         "1999-01 로 좁혔는데 방금 기록이 잡힙니다 — month 필터가 "
                         "실제로 걸리지 않습니다.")
        _write_evidence(
            "FWS-F5-10", title="계량(비행 분)",
            test_ref="tests.test_ap_n4_f5_10_monthly.F5_10_MonthFilterTest."
                    "test_month_param_actually_filters_by_real_month",
            method="GET", path=f"{FLIGHTS_MINUTES}?month={real_month}",
            request_params={"month": real_month}, response=this,
            what="[턴 AP · 차선 N4] month 파라미터가 실제로 걸린다 — 이번 달로 "
                "좁히면 방금 기록이 잡히고, 1999-01 로 좁히면 0건이다(drone.py "
                "는 고치지 않았다 · 검증만 새로 했다)")


class F5_10_MonthlyTableTest(Fws5_10ApHttpTest):
    def test_monthly_table_groups_flights_by_month(self) -> None:
        head = self._bearer(self.user_a)
        self._log(head, minutes=15)
        self._log(head, minutes=27.5)

        resp = self.client.get(MONTHLY_TABLE, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(1, body["count"], "같은 달에 두 번 기록했는데 행이 갈렸습니다.")
        row = body["rows"][0]
        self.assertEqual(42.5, row["flight_minutes_total"])
        self.assertEqual(2, row["flight_count"])
        _write_evidence(
            "FWS-F5-10", title="계량(비행 분)",
            test_ref="tests.test_ap_n4_f5_10_monthly.F5_10_MonthlyTableTest."
                    "test_monthly_table_groups_flights_by_month",
            method="GET", path=MONTHLY_TABLE, request_params={}, response=resp,
            what="[턴 AP · 차선 N4] 명세 완결 조건 「월 표」— 비행 분·건수를 월별로 "
                "접은 표(새 door `ap_f5.flight_minutes_monthly_table`, drone.py "
                "는 고치지 않았다)")
