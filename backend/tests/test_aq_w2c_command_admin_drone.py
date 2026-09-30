# -*- coding: utf-8 -*-
"""턴 AQ · 2물결 차선 W2C — 지휘·관리·드론 화면 배선 (서버 왕복 + 화면 정적 대조).

닫는 절과 이 파일이 재는 것
----------------------------
* FWS-F2-01 「자원 배치판에 표시」 — 대원이 대기 상태를 등록(POST /resources/me/status)
  하면 지휘 화면이 읽는 **새 GET** `/api/fws/resources/board` 에 그 사람·상태·위치가
  보인다. 다른 기관 대원은 섞이지 않는다.
* FWS-F2-05 「지휘 화면 배지」 — 지원 요청(POST /missions/{id}/field-reply) 뒤 같은
  GET(`?event_id=`)의 종류별 배지 수가 오른다. 남의 기관은 404.
* FWS-F1-10 「대피 지시·철수」 — F4-05 대피 승인이 받는 사람의 GET /api/fws/alerts 에
  새 알림으로 도달한다(이미 있던 연결을 잰다) · 철수 지시(POST .../withdrawal-order)도
  같은 알림 경로로 도달하고, GET .../withdrawal-order 재조회에 남는다.
* FWS-U5-04 — 야간 5분대기조 규칙 저장 → 새 GET 재조회에 zone 이 보이고, 화면의 등급
  선택지가 쓰는 서버 등급 값으로 저장이 통과한다(예전 화면의 high/medium/low 는 서버
  등급이 아니어서 422 였다 — 그 값이 화면에 다시 들어가지 않는지도 잰다).
* FWS-F5-08 — 비행 기록 저장 → 새 GET(/drone/flights/mine)에 배터리·기체 값.
* 정적 대조 — 각 화면 파일에 `data-gx` 가 **글자 그대로** 있고, 누른 뒤 재조회 함수를
  부른다.

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`FwsHttpTest` 가 Client 에 싣는다) + 각 시험
`setUp` 에서 `cache.clear()`, 재조회 직전에도 `cache.clear()`.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.apps import apps
from django.core.cache import cache

from tests.test_fws_app import ALERTS, FwsHttpTest, _qs

BOARD = "/api/fws/resources/board"
STANDBY = "/api/fws/resources/me/status"
NOTIFY_RULES = "/api/fws/admin/notify-rules"
FLIGHTS = "/api/fws/drone/flights"
FLIGHTS_MINE = "/api/fws/drone/flights/mine"


def _support(eid) -> str:
    return f"/api/fws/missions/{eid}/field-reply"


def _withdrawal(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/withdrawal-order"


def _evac_plan(eid) -> str:
    return f"/api/fws/office2/evacuations/{eid}/plan"


def _evac_approve(eid) -> str:
    return f"/api/fws/command/evacuations/{eid}/approve"


def _frontend_src() -> Path:
    for base in (Path("/repo/frontend/src"),
                 *(p / "frontend" / "src" for p in Path(__file__).resolve().parents)):
        if (base / "App.tsx").is_file():
            return base
    raise AssertionError("frontend/src 를 찾지 못했다 — 정적 대조를 할 수 없다")


def _src(rel: str) -> str:
    return (_frontend_src() / rel).read_text(encoding="utf-8")


class W2cFixture(FwsHttpTest):
    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        from core.middleware.refresh_token import thread_local

        thread_local.request = None
        super().setUpTestData()
        Role = apps.get_model("role", "Role")
        admin_role, _ = Role.objects.get_or_create(
            code="admin", defaults={"role_name": "admin"})
        cls.user_a.roles.add(admin_role)
        fws_role, _ = Role.objects.get_or_create(
            code="fws_response_team", defaults={"role_name": "fws_response_team"})
        cls.user_a.roles.add(fws_role)
        #: 같은 기관 A 의 두 번째 대원 — 배치판에 둘 다 보이는지 잰다.
        cls.user_a2 = cls._user("aq_w2c_crew_a2", cls.group_a, cls.role_a)

    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.head_a = self._bearer(self.user_a)

    def post_ok(self, path, head=None, **params) -> dict:
        resp = self.client.post(_qs(path, **params), **(head or self.head_a))
        self.assertEqual(200, resp.status_code, resp.content)
        return self._body(resp)

    def get_ok(self, path, head=None) -> dict:
        cache.clear()
        resp = self.client.get(path, **(head or self.head_a))
        self.assertEqual(200, resp.status_code, resp.content)
        return self._body(resp)

    def alert_ids(self) -> set:
        return {r["delivery_id"] for r in self.get_ok(ALERTS)["alerts"]}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F2-01 자원 배치판 · FWS-F2-05 지휘 화면 배지
# ═══════════════════════════════════════════════════════════════════════════
class W2cResourceBoardTest(W2cFixture):
    def test_f2_01_standby_then_board_rereads_people_and_counts(self) -> None:
        before = self.get_ok(BOARD)
        self.assertEqual(0, before["standby"]["on_standby"])
        self.assertIsNone(before["support"])

        self.post_ok(STANDBY, status="standby_night", lat=36.4, lng=127.4)
        self.post_ok(STANDBY, self._bearer(self.user_a2), status="standby_day")
        # 다른 기관 대원 — A 의 배치판에 섞이면 안 된다.
        self.post_ok(STANDBY, self._bearer(self.user_b), status="standby_day")

        board = self.get_ok(BOARD)["standby"]
        self.assertEqual(2, board["on_standby"])
        self.assertEqual(1, board["counts"]["standby_night"])
        self.assertEqual(1, board["counts"]["standby_day"])
        by_user = {p["user_id"]: p for p in board["people"]}
        self.assertEqual({self.user_a.pk, self.user_a2.pk}, set(by_user))
        self.assertEqual("standby_night", by_user[self.user_a.pk]["status"])
        self.assertEqual({"lat": 36.4, "lng": 127.4}, by_user[self.user_a.pk]["location"])
        self.assertTrue(by_user[self.user_a2.pk]["name"])

        # 최신 한 줄이 이긴다 — 근무 외로 바꾸면 대기 인원이 준다.
        self.post_ok(STANDBY, status="off_duty")
        board = self.get_ok(BOARD)["standby"]
        self.assertEqual(1, board["on_standby"])
        self.assertEqual(1, board["counts"]["off_duty"])

        other = self.get_ok(BOARD, self._bearer(self.user_b))["standby"]
        self.assertEqual({self.user_b.pk}, {p["user_id"] for p in other["people"]})

    def test_f2_05_support_request_then_board_badges_rise(self) -> None:
        eid = self._event(self.stream_a, severity="critical", event_type="fire")
        before = self.get_ok(f"{BOARD}?event_id={eid}")["support"]
        self.assertEqual(0, before["count"])
        self.assertEqual({"personnel": 0, "water": 0, "helicopter": 0, "heavy_equipment": 0},
                         before["badges"])

        self.post_ok(_support(eid), kind="helicopter", amount="1대")
        self.post_ok(_support(eid), kind="water", amount="5톤")
        self.post_ok(_support(eid), kind="personnel", amount="10명")
        self.post_ok(_support(eid), kind="heavy_equipment")

        after = self.get_ok(f"{BOARD}?event_id={eid}")["support"]
        self.assertEqual(4, after["count"])
        self.assertEqual({"personnel": 1, "water": 1, "helicopter": 1, "heavy_equipment": 1},
                         after["badges"])
        self.assertIn("1대", {r["amount"] for r in after["requests"]})

        # 다른 사건의 요청은 이 사건 배지에 안 섞인다.
        other_eid = self._event(self.stream_a, severity="critical", event_type="fire")
        self.assertEqual(0, self.get_ok(f"{BOARD}?event_id={other_eid}")["support"]["count"])

        # 남의 기관 사건 — 404.
        resp = self.client.get(f"{BOARD}?event_id={eid}", **self._bearer(self.user_b))
        self.assertEqual(404, resp.status_code, resp.content)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F1-10 대피 지시 · 철수 → 현장 안전 알림(GET /api/fws/alerts)
# ═══════════════════════════════════════════════════════════════════════════
class W2cFieldSafetyAlertTest(W2cFixture):
    def test_f1_10_evac_approval_reaches_field_alerts(self) -> None:
        eid = self._event(self.stream_a, severity="critical", event_type="fire")
        villages = json.dumps([{"village": "OO리", "shelter": "OO경로당"}], ensure_ascii=False)
        self.post_ok(_evac_plan(eid), villages_json=villages)
        before = self.alert_ids()
        body = self.post_ok(_evac_approve(eid), urgency="immediate")
        self.assertGreaterEqual(body["notified_count"], 1)
        new_ids = self.alert_ids() - before
        self.assertTrue(new_ids, "대피 승인이 현장 알림 목록(GET /api/fws/alerts)에 안 닿았다")
        # 확인(ack)까지 — F1-10 「도달·확인」.
        ack = self.post_ok(f"{ALERTS}/{sorted(new_ids)[0]}/ack")
        self.assertTrue(ack["acknowledged"])

    def test_f1_10_withdrawal_order_reaches_alerts_and_rereads(self) -> None:
        eid = self._event(self.stream_a, severity="critical", event_type="fire")
        self.assertEqual(0, self.get_ok(_withdrawal(eid))["count"])
        before = self.alert_ids()

        body = self.post_ok(_withdrawal(eid), reason="풍향 급변 — 능선 뒤로 철수")
        self.assertEqual("withdrawal", body["kind"])
        self.assertGreaterEqual(body["delivered_count"], 1)
        self.assertTrue(self.alert_ids() - before,
                        "철수 지시가 현장 알림 목록(GET /api/fws/alerts)에 안 닿았다")

        reread = self.get_ok(_withdrawal(eid))
        self.assertEqual(1, reread["count"])
        self.assertEqual("풍향 급변 — 능선 뒤로 철수", reread["latest"]["reason"])
        self.assertGreaterEqual(reread["latest"]["delivered"], 1)

    def test_f1_10_withdrawal_guards(self) -> None:
        eid = self._event(self.stream_a, severity="critical", event_type="fire")
        resp = self.client.post(_qs(_withdrawal(eid), reason="  "), **self.head_a)
        self.assertEqual(422, resp.status_code, resp.content)
        resp = self.client.post(_qs(_withdrawal(eid), reason="남의 사건"),
                                **self._bearer(self.user_b))
        self.assertEqual(404, resp.status_code, resp.content)
        self.assertEqual(0, self.get_ok(_withdrawal(eid))["count"])


# ═══════════════════════════════════════════════════════════════════════════
# FWS-U5-04 등급별 수신 · 야간 5분대기조 · FWS-F5-08 비행 기록
# ═══════════════════════════════════════════════════════════════════════════
class W2cAdminDroneTest(W2cFixture):
    def test_u5_04_screen_severity_values_save_and_night_zone_rereads(self) -> None:
        overview = self.get_ok(NOTIFY_RULES)
        severities = [s["severity"] for s in overview["severities"]]
        self.assertTrue(severities)
        zone = overview["night_standby_zone"]
        # 화면은 서버가 준 등급 값만 고른다 — 그 값 하나하나로 저장이 통과해야 한다.
        for sev in severities:
            saved = self.post_ok(NOTIFY_RULES, severity=sev, role_code="fws_response_team",
                                 channels="email", zone=zone)
            self.assertEqual(zone, saved["zone"])
        reread = self.get_ok(NOTIFY_RULES)
        night = {r["severity"] for r in reread["rules"] if r["zone"] == zone}
        self.assertEqual(set(severities), night)
        by_sev = {s["severity"]: s for s in reread["severities"]}
        for sev in severities:
            self.assertIn("recipient_count", by_sev[sev])
            self.assertIn("reaches_people", by_sev[sev])
        # 예전 화면의 등급 값(high)은 서버 등급이 아니다 — 화면에서 뺐다(정적 대조 아래).
        resp = self.client.post(_qs(NOTIFY_RULES, severity="high", role_code="fws_response_team",
                                    channels="email"), **self.head_a)
        self.assertNotEqual(200, resp.status_code)

    def test_f5_08_flight_log_then_mine_rereads_battery_and_airframe(self) -> None:
        self.assertEqual(0, self.get_ok(FLIGHTS_MINE)["count"])
        self.post_ok(FLIGHTS, source="manual", airframe_code="M30T-7", battery_pct=68.5,
                     flight_minutes=22)
        mine = self.get_ok(FLIGHTS_MINE)
        self.assertEqual(1, mine["count"])
        row = mine["flights"][0]
        self.assertEqual(68.5, row["battery_pct"])
        self.assertEqual("M30T-7", row["airframe_code"])
        self.assertEqual(22, row["flight_minutes"])


# ═══════════════════════════════════════════════════════════════════════════
# 정적 대조 — data-gx 글자 그대로 · 누른 뒤 재조회
# ═══════════════════════════════════════════════════════════════════════════
class W2cScreenStaticTest(W2cFixture):
    def _assert_gx(self, text: str, names: list[str], where: str) -> None:
        missing = [n for n in names if f'data-gx="{n}"' not in text]
        self.assertEqual([], missing, f"{where} 에 data-gx 글자가 없다")

    def test_command_board_and_withdrawal_are_wired(self) -> None:
        cards = _src("features/fws/pages/W2cCommandCards.tsx")
        home = _src("features/fws/pages/CommandHome.tsx")
        api = _src("features/fws/api_w2c.ts")
        self._assert_gx(cards, [
            "fws-f2-01-board", "fws-f2-01-board-refresh", "fws-f2-01-standby-counts",
            "fws-f2-01-count-day", "fws-f2-01-count-night", "fws-f2-01-standby-list",
            "fws-f2-05-support-badges", "fws-f2-05-badge-personnel", "fws-f2-05-badge-water",
            "fws-f2-05-badge-helicopter", "fws-f2-05-badge-heavy-equipment",
            "fws-f1-10-card", "fws-f1-10-evac-notified", "fws-f1-10-withdrawal-reason",
            "fws-f1-10-withdrawal-order", "fws-f1-10-withdrawal-list",
        ], "W2cCommandCards.tsx")
        refresh_body = home.split("async function refreshAll", 1)[1].split("async function", 1)[0]
        self.assertIn("fetchResourceBoard(id)", refresh_body)
        self.assertIn("fetchWithdrawalOrders(id)", refresh_body)
        self.assertIn("act(fwsW2cEndpoint.withdrawalOrder", home)
        self.assertIn("<ResourceBoardCard", home)
        self.assertIn("<FieldSafetyAlertCard", home)
        self.assertIn("/api/fws/resources/board?event_id=", api)
        self.assertIn("/withdrawal-order", api)
        self.assertIn("fwsGetFresh", api)

    def test_admin_notify_card_is_wired(self) -> None:
        admin = _src("features/fws/pages/AdminHome.tsx")
        self._assert_gx(admin, [
            "fws-u5-04-card", "fws-u5-04-severity", "fws-u5-04-role", "fws-u5-04-channels",
            "fws-u5-04-night-standby", "fws-u5-04-save", "fws-u5-04-test", "fws-u5-04-reach",
            "fws-u5-04-rules",
        ], "AdminHome.tsx")
        notify = admin.split("function NotifyCard(", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("fwsGetFresh<NotifyOverview>(NOTIFY_RULES)", notify)
        self.assertIn("await reload();", notify.split("async function handleSave", 1)[1])
        self.assertNotIn("'high', 'medium', 'low'", notify, "서버 등급이 아닌 값이 화면에 다시 들어왔다")
        self.assertIn("overview?.severities", notify)

    def test_drone_flight_card_is_wired(self) -> None:
        drone = _src("features/fws/pages/DroneHome.tsx")
        self._assert_gx(drone, [
            "fws-f5-08-card", "fws-f5-08-source", "fws-f5-08-airframe", "fws-f5-08-battery",
            "fws-f5-08-minutes", "fws-f5-08-save", "fws-f5-08-minutes-total", "fws-f5-08-flights",
        ], "DroneHome.tsx")
        save = drone.split("async function handleSave", 1)[1].split("\n  }\n", 1)[0]
        self.assertIn("await reloadFlights();", save)
        self.assertIn("fetchMyFlights()", drone)
