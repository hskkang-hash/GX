# -*- coding: utf-8 -*-
"""턴 AQ · 차선 N3 — DSM·FWS 잔여 화면 배선(P-435 화면 축).

절마다 세 가지를 잰다:
  ① **누름/칸 변경 → 재조회** — 화면이 누르는 그 쓰기 문을 HTTP 로 부르고, 화면이
     다시 부르는 그 조회 GET 에서 바뀐 값을 확인한다.
  ② **테넌트 격리** — 다른 테넌트 사람이 같은 문을 부르면 404/빈 값.
  ③ **화면 소스 정적 대조** — 화면 파일에 그 `data-gx` 와 그 API 경로가 실제로 있다
     (`/repo/frontend/src` — 소스 문자열만 본다, 판정기를 대신하지 않는다).

대상: DSM-U3-01 · U3-02 · U4-07 · U4-08(묶음 내려받기) · FWS-F1-12 · F2-15 ·
F2-07(진화대 경보 칸) · F3-16(헬기 투하 시각) · F3-18(기관 통계 기간 칸) ·
F4-09(tel: 연락) · F4-13(위험도 목록).

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`FwsHttpTest` 픽스처 그대로 · 재조회 GET 은
화면도 `X-No-Cache` 로 부른다).
증거: 이 파일은 `SPEC/<id>.json`·`.retro.md` 어느 쪽도 쓰지 않는다(P-431 — 사람 표는
손으로만 · 기계 실측 json 은 원래 쓰개 시험이 쓴다).
"""
from __future__ import annotations

import io
import zipfile
from datetime import timedelta
from pathlib import Path

from django.core.cache import cache
from django.utils import timezone

from tests.test_fws_app import NOTIFY_PREFS, FwsHttpTest, _qs


def _frontend_src() -> Path:
    for base in (Path("/repo/frontend/src"),
                 *(p / "frontend" / "src" for p in Path(__file__).resolve().parents)):
        if (base / "App.tsx").is_file():
            return base
    raise AssertionError("frontend/src 를 찾지 못했다 — 정적 대조를 할 수 없다")


def _src(rel: str) -> str:
    return (_frontend_src() / rel).read_text(encoding="utf-8")


class AqN3Fixture(FwsHttpTest):
    @classmethod
    def setUpTestData(cls) -> None:
        from core.middleware.refresh_token import thread_local

        thread_local.request = None
        super().setUpTestData()

    def setUp(self) -> None:
        super().setUp()
        cache.clear()


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U3-01 — M2 상단 한 줄(역할 분류 축)
# ═══════════════════════════════════════════════════════════════════════════
class DsmU3_01ScreenTest(AqN3Fixture):
    def test_role_axis_change_refetches_a_different_line(self) -> None:
        eid = self._event(self.stream_a, event_type="flood")
        head = self._bearer(self.user_a)
        path = f"/api/dsm/events/{eid}/m2-brief"
        facility = self.client.get(_qs(path, role="facility"), **head)
        duty = self.client.get(_qs(path, role="duty"), **head)
        self.assertEqual((200, 200), (facility.status_code, duty.status_code))
        self.assertEqual("도로 통제 후 회신", self._body(facility)["text"])
        self.assertNotEqual(self._body(facility)["text"], self._body(duty)["text"],
                            "역할 축을 바꿨는데 같은 줄이다")
        other = self.client.get(_qs(path, role="facility"), **self._bearer(self.user_b))
        self.assertEqual(404, other.status_code)

    def test_screen_wires_role_axis_and_line(self) -> None:
        comp = _src("features/dsm/components/M2BriefLine.tsx")
        api = _src("features/dsm/components/aqScreensApi.ts")
        m2 = _src("features/mobile/pages/MobileEventDetail.tsx")
        for gx in ("dsm-u3-01-role", "dsm-u3-01-line"):
            self.assertIn(f'data-gx="{gx}"', comp)
        self.assertIn("/m2-brief", api)
        self.assertIn("[eventId, role]", comp, "역할을 바꾸면 다시 불러야 한다")
        self.assertIn("<M2BriefLine eventId=", m2, "M2 화면에 한 줄이 안 붙었다")


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U3-02 — 통제 지점 표(도달 → 결정 → 통제 완료 → 해제)
# ═══════════════════════════════════════════════════════════════════════════
class DsmU3_02ScreenTest(AqN3Fixture):
    def test_each_press_then_board_refetch_shows_new_stage(self) -> None:
        head = self._bearer(self.user_a)
        created = self.client.post("/api/dsm/control-points",
                                   {"name": "둔치주차장", "evacuee_count": 3,
                                    "evacuation_site": "주민센터"},
                                   content_type="application/json", **head)
        self.assertEqual(200, created.status_code, created.content[:300])
        pid = self._body(created)["point_id"]

        def stage() -> str:
            board = self.client.get("/api/dsm/control-points", **head)
            self.assertEqual(200, board.status_code)
            return next(r for r in self._body(board) if r["point_id"] == pid)["stage"]

        self.assertEqual("도달", stage())
        early = self.client.post(f"/api/dsm/controls/{pid}/executed", {},
                                 content_type="application/json", **head)
        self.assertEqual(409, early.status_code, "결정 전에 통제 완료가 먹혔다")
        r = self.client.post(f"/api/dsm/control-points/{pid}/advance", {"stage": "결정"},
                             content_type="application/json", **head)
        self.assertEqual(200, r.status_code, r.content[:300])
        self.assertEqual("결정", stage())
        r = self.client.post(f"/api/dsm/controls/{pid}/executed", {},
                             content_type="application/json", **head)
        self.assertEqual(200, r.status_code, r.content[:300])
        self.assertEqual("실행", stage())
        r = self.client.post(f"/api/dsm/control-points/{pid}/advance", {"stage": "해제"},
                             content_type="application/json", **head)
        self.assertEqual(200, r.status_code, r.content[:300])
        self.assertEqual("해제", stage())

        head_b = self._bearer(self.user_b)
        board_b = self.client.get("/api/dsm/control-points", **head_b)
        self.assertNotIn(pid, [row["point_id"] for row in self._body(board_b)])
        cross = self.client.post(f"/api/dsm/controls/{pid}/executed", {},
                                 content_type="application/json", **head_b)
        self.assertEqual(404, cross.status_code)

    def test_screen_wires_buttons_and_refetch(self) -> None:
        comp = _src("features/dsm/components/ControlPointsBoard.tsx")
        api = _src("features/dsm/components/aqScreensApi.ts")
        dash = _src("features/dsm/pages/ControlDashboard.tsx")
        for gx in ("dsm-u3-02-create", "dsm-u3-02-decide", "dsm-u3-02-executed",
                   "dsm-u3-02-release", "dsm-u3-02-board"):
            self.assertIn(f'data-gx="{gx}"', comp)
        self.assertIn("'/api/dsm/control-points'", api)
        self.assertIn("/api/dsm/controls/${pointId}/executed", api)
        self.assertIn("await reload()", comp, "누른 뒤 현황판 재조회가 없다")
        self.assertIn("<ControlPointsBoard />", dash)


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U4-07 — 대장 표 · 연간 통계 / DSM-U4-08 — 기간 선택 → 묶음 내려받기
# ═══════════════════════════════════════════════════════════════════════════
class DsmU4_07_08ScreenTest(AqN3Fixture):
    def test_ledger_presses_then_ledger_and_stats_refetch(self) -> None:
        head = self._bearer(self.user_a)
        year = timezone.localtime().year
        before = self._body(self.client.get(
            _qs("/api/dsm/video-access-requests/annual-stats", year=year), **head))
        created = self.client.post(
            "/api/dsm/video-access-requests",
            {"requester_org": "○○경찰서", "doc_no": "수사-2026-1", "purpose": "수사",
             "scope_desc": "카메라 1 · 10분"},
            content_type="application/json", **head)
        self.assertEqual(200, created.status_code, created.content[:300])
        rid = self._body(created)["request_id"]

        def status_of() -> str:
            rows = self._body(self.client.get("/api/dsm/video-access-requests", **head))
            return next(r for r in rows if r["request_id"] == rid)["status"]

        self.assertEqual("요청", status_of())
        r = self.client.post(f"/api/dsm/video-access-requests/{rid}/approve", {},
                             content_type="application/json", **head)
        self.assertEqual(200, r.status_code, r.content[:300])
        self.assertEqual("승인", status_of())
        r = self.client.post(f"/api/dsm/video-access-requests/{rid}/provide",
                             {"method": "마스킹본"}, content_type="application/json", **head)
        self.assertEqual(200, r.status_code, r.content[:300])
        self.assertEqual("제공", status_of())

        after = self._body(self.client.get(
            _qs("/api/dsm/video-access-requests/annual-stats", year=year), **head))
        for k in ("requested", "approved", "provided"):
            self.assertEqual(before[k] + 1, after[k], f"연간 통계 {k} 가 안 늘었다")
        other_year = self._body(self.client.get(
            _qs("/api/dsm/video-access-requests/annual-stats", year=year - 1), **head))
        self.assertEqual(0, other_year["requested"], "연도 칸을 바꿔도 같은 수다")

        stats_b = self._body(self.client.get(
            _qs("/api/dsm/video-access-requests/annual-stats", year=year),
            **self._bearer(self.user_b)))
        self.assertEqual(0, stats_b["requested"], "다른 테넌트 통계에 섞였다")
        ledger_b = self._body(self.client.get("/api/dsm/video-access-requests",
                                              **self._bearer(self.user_b)))
        self.assertNotIn(rid, [x["request_id"] for x in ledger_b])

    def test_bundle_download_is_a_zip_for_the_chosen_period(self) -> None:
        today = timezone.localdate().isoformat()
        resp = self.client.get(
            _qs("/api/dsm/evaluation-bundle.zip", since=today, until=today),
            **self._bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self.assertEqual("application/zip", resp["Content-Type"])
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            self.assertTrue(zf.namelist(), "빈 ZIP 이다")

    def test_screen_wires_ledger_stats_and_bundle(self) -> None:
        comp = _src("features/dsm/components/VideoAccessLedgerPanel.tsx")
        api = _src("features/dsm/components/aqScreensApi.ts")
        reports = _src("features/dsm/pages/Reports.tsx")
        for gx in ("dsm-u4-07-year", "dsm-u4-07-stats", "dsm-u4-07-ledger",
                   "dsm-u4-07-create", "dsm-u4-07-approve", "dsm-u4-07-provide",
                   "dsm-u4-08-since", "dsm-u4-08-until", "dsm-u4-08-download"):
            self.assertIn(f'data-gx="{gx}"', comp)
        for path in ("/api/dsm/video-access-requests/annual-stats",
                     "'/api/dsm/video-access-requests'", "/api/dsm/evaluation-bundle.zip"):
            self.assertIn(path, api)
        self.assertIn("[year, loadStats]", comp, "연도 칸을 바꾸면 다시 불러야 한다")
        self.assertIn("Promise.all([loadLedger(), loadStats(year)])", comp)
        self.assertIn("<VideoAccessLedgerPanel />", reports)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F1-12 · F2-15 — M4 근무 외 알림 차단 칸
# ═══════════════════════════════════════════════════════════════════════════
class FwsQuietHoursScreenTest(AqN3Fixture):
    def test_save_then_refetch_shows_saved_window_and_other_user_unchanged(self) -> None:
        head = self._bearer(self.user_a)
        r = self.client.post(_qs(NOTIFY_PREFS, quiet_hours_start="22:00",
                                 quiet_hours_end="06:00", assigned_post_code="초소-3"), **head)
        self.assertEqual(200, r.status_code, r.content[:300])
        got = self._body(self.client.get(NOTIFY_PREFS, **head))
        self.assertEqual(("22:00", "06:00", "초소-3"),
                         (got["quiet_hours_start"], got["quiet_hours_end"],
                          got["assigned_post_code"]))
        r = self.client.post(_qs(NOTIFY_PREFS, quiet_hours_start="23:30",
                                 quiet_hours_end="05:00", assigned_post_code="초소-3"), **head)
        self.assertEqual(200, r.status_code)
        self.assertEqual("23:30", self._body(self.client.get(NOTIFY_PREFS, **head))[
            "quiet_hours_start"], "바꾼 값이 재조회에 안 보인다")
        other = self._body(self.client.get(NOTIFY_PREFS, **self._bearer(self.user_b)))
        self.assertEqual("", other["quiet_hours_start"], "남의 설정이 보인다")

    def test_screen_wires_card_on_patrol_and_field(self) -> None:
        card = _src("features/fws/pages/NotifyPrefsCard.tsx")
        for suffix in ("start", "end", "post", "save", "saved"):
            #: [턴 AR · N1] 이름은 `gxOf(gxPrefix, '<부분>')` 로 단다 — 목록(GX_NAMES)에 글자 그대로
            #: 적혀 있어 화면 인용 판정이 찾는다.
            self.assertIn(f"gxOf(gxPrefix, '{suffix}')", card)
            for pre in ("fws-f1-12-quiet", "fws-f2-15-quiet"):
                self.assertIn(f"gx: '{pre}-{suffix}'", card)
        self.assertIn("fwsEndpoint.notifyPrefs", card)
        self.assertIn("fwsGetFresh<NotifyPrefs>", card)
        self.assertIn("await reload()", card)
        self.assertIn('<NotifyPrefsCard gxPrefix="fws-f1-12-quiet" />',
                      _src("features/fws/pages/PatrolHome.tsx"))
        self.assertIn('<NotifyPrefsCard gxPrefix="fws-f2-15-quiet" />',
                      _src("features/fws/pages/FieldHome.tsx"))


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F2-07 — 진화대(FM3) 안전 경보 칸 · 기준 미설정 「대기」
# ═══════════════════════════════════════════════════════════════════════════
class FwsF2_07FieldAlertsScreenTest(AqN3Fixture):
    def test_field_user_reads_waiting_rules_and_alert_list(self) -> None:
        head = self._bearer(self.user_a)
        rules = self.client.get("/api/fws/admin/safety-thresholds", **head)
        self.assertEqual(200, rules.status_code, rules.content[:300])
        fields = self._body(rules)["fields"]
        self.assertTrue(fields)
        self.assertTrue(all(f["status"] == "대기" and f["value"] is None for f in fields),
                        "미설정 기관인데 숫자가 보인다(지어낸 값)")
        alerts = self.client.get("/api/fws/alerts", **head)
        self.assertEqual(200, alerts.status_code)
        self.assertIn("alerts", self._body(alerts))

    def test_screen_wires_waiting_badge_list_and_ack(self) -> None:
        card = _src("features/fws/pages/SafetyAlertsCard.tsx")
        for gx in ("fws-f2-07-card", "fws-f2-07-rules", "fws-f2-07-list", "fws-f2-07-ack"):
            self.assertIn(f'data-gx="{gx}"', card)
        self.assertIn("'fws-f2-07-waiting'", card)
        self.assertIn("fwsAqEndpoint.safetyThresholds", card)
        self.assertIn("fwsEndpoint.alertAck", card)
        self.assertIn("await reload()", card)
        self.assertIn("<SafetyAlertsCard />", _src("features/fws/pages/FieldHome.tsx"))
        self.assertIn("'/api/fws/admin/safety-thresholds'", _src("features/fws/api.ts"))


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-16 — 헬기 물 투하 시각 저장 칸 → 준수율
# ═══════════════════════════════════════════════════════════════════════════
class FwsF3_16HeliDropScreenTest(AqN3Fixture):
    def test_save_drop_time_then_refetch_and_stats_read_it(self) -> None:
        head = self._bearer(self.user_a)
        now = timezone.localtime()
        fast = self._event(self.stream_a, event_type="fire", when=now - timedelta(minutes=20))
        slow = self._event(self.stream_a, event_type="fire", when=now - timedelta(hours=2))
        self._event(self.stream_a, event_type="fire")  # 투하 기록 없음 → 분모 밖

        path_fast = f"/api/fws/command/incidents/{fast}/helicopter-drop"
        empty = self._body(self.client.get(path_fast, **head))
        self.assertEqual((0, None), (empty["count"], empty["first_dropped_at"]))
        r = self.client.post(_qs(path_fast, dropped_at=(now - timedelta(minutes=5))
                                 .strftime("%Y-%m-%dT%H:%M")), **head)
        self.assertEqual(200, r.status_code, r.content[:300])
        got = self._body(self.client.get(path_fast, **head))
        self.assertEqual(1, got["count"])
        self.assertIsNotNone(got["first_dropped_at"])

        r = self.client.post(_qs(f"/api/fws/command/incidents/{slow}/helicopter-drop",
                                 dropped_at=(now - timedelta(minutes=10))
                                 .strftime("%Y-%m-%dT%H:%M")), **head)
        self.assertEqual(200, r.status_code, r.content[:300])

        future = self.client.post(_qs(path_fast, dropped_at=(now + timedelta(hours=1))
                                      .strftime("%Y-%m-%dT%H:%M")), **head)
        self.assertEqual(422, future.status_code, "미래 투하 시각이 먹혔다")

        stats = self._body(self.client.get("/api/fws/office2/stats/fires", **head))
        self.assertEqual((2, 1, 50.0), (stats["heli_drop_measured_n"],
                                        stats["heli_drop_compliant_n"],
                                        stats["heli_drop_compliance_pct"]),
                         "신고(발생) → 첫 투하 30분 준수율이 저장값을 안 읽는다")

        head_b = self._bearer(self.user_b)
        self.assertEqual(404, self.client.get(path_fast, **head_b).status_code)
        self.assertEqual(404, self.client.post(_qs(path_fast), **head_b).status_code)
        stats_b = self._body(self.client.get("/api/fws/office2/stats/fires", **head_b))
        self.assertEqual(0, stats_b["heli_drop_measured_n"])

    def test_screen_wires_drop_field_in_f4_04_card(self) -> None:
        cmd = _src("features/fws/pages/CommandHome.tsx")
        for gx in ("fws-f3-16-dropped-at", "fws-f3-16-drop-save", "fws-f3-16-drops"):
            self.assertIn(f'data-gx="{gx}"', cmd)
        self.assertIn("act(E.helicopterDrop", cmd)
        self.assertIn("fwsGetFresh<HeliDropBody>(E.helicopterDrop(id))", cmd,
                      "누른 뒤 refreshAll 이 투하 기록을 다시 안 부른다")
        self.assertIn("/helicopter-drop`", _src("features/fws/api.ts"))
        self.assertIn('data-gx="fws-f3-16-heli-drop-pct"',
                      _src("features/fws/pages/OfficeReport.tsx"))


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-18 — 기관 통계(계도·단속) 기간 칸
# ═══════════════════════════════════════════════════════════════════════════
class FwsF3_18StatsScreenTest(AqN3Fixture):
    STATS = "/api/fws/office2/patrol/enforcement/mine"

    def test_record_then_period_refetch_counts_and_isolation(self) -> None:
        head = self._bearer(self.user_a)
        for kind in ("guidance", "enforcement"):
            r = self.client.post(_qs("/api/fws/office2/patrol/enforcement", kind=kind,
                                     location="등산로 입구"), **head)
            self.assertEqual(200, r.status_code, r.content[:300])
        today = timezone.localdate()
        inside = self._body(self.client.get(
            _qs(self.STATS, since=today.isoformat(),
                until=f"{today.isoformat()}T23:59:59"), **head))
        self.assertEqual((2, 1, 1), (inside["total"], inside["by_kind"].get("guidance"),
                                     inside["by_kind"].get("enforcement")))
        later = self._body(self.client.get(
            _qs(self.STATS, since=(today + timedelta(days=1)).isoformat()), **head))
        self.assertEqual(0, later["total"], "기간 칸을 바꿔도 같은 수다")
        whole = self._body(self.client.get(self.STATS, **head))
        self.assertEqual(2, whole["total"])
        bad = self.client.get(_qs(self.STATS, since="어제"), **head)
        self.assertEqual(422, bad.status_code)
        other = self._body(self.client.get(self.STATS, **self._bearer(self.user_b)))
        self.assertEqual(0, other["total"], "다른 테넌트 기록이 섞였다")

    def test_screen_wires_period_fields_and_refetch(self) -> None:
        office = _src("features/fws/pages/OfficeReport.tsx")
        for gx in ("fws-f3-18-since", "fws-f3-18-until", "fws-f3-18-stats", "fws-f3-18-record"):
            self.assertIn(f'data-gx="{gx}"', office)
        self.assertIn("office2.patrolEnforcementMine", office.split("function PatrolCard")[1],
                      "통계 GET 이 아직 죽은 상수다")
        self.assertIn("[since, until]", office, "기간 칸을 바꾸면 다시 불러야 한다")
        self.assertIn("await reloadStats()", office, "기록한 뒤 재조회가 없다")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-09 — 연락 전화 버튼(tel:) · FWS-F4-13 — 위험도 목록
# ═══════════════════════════════════════════════════════════════════════════
class FwsF4_09_13ScreenTest(AqN3Fixture):
    def test_contacts_refetch_after_command_post_phone_registered(self) -> None:
        head = self._bearer(self.user_a)
        eid = self._event(self.stream_a, event_type="fire")
        path = f"/api/fws/command/incidents/{eid}/contacts"
        before = self._body(self.client.get(path, **head))
        self.assertTrue(before["forest_service"]["phone"])
        self.assertIsNone(before["provincial_situation_room"]["phone"])
        r = self.client.post(_qs(f"/api/fws/command/incidents/{eid}/command-post",
                                 address="○○군 산림과", org_composition="산림·소방",
                                 situation_room_phone="033-000-0000"), **head)
        self.assertEqual(200, r.status_code, r.content[:300])
        after = self._body(self.client.get(path, **head))
        self.assertEqual("033-000-0000", after["provincial_situation_room"]["phone"])
        self.assertEqual(404, self.client.get(path, **self._bearer(self.user_b)).status_code)

    def test_risk_record_then_list_refetch_reorders(self) -> None:
        head = self._bearer(self.user_a)
        low = self._event(self.stream_a, event_type="fire")
        high = self._event(self.stream_a, event_type="fire")
        for eid, value in ((low, 51), (high, 86)):
            r = self.client.post(_qs(f"/api/fws/command/incidents/{eid}/risk-index",
                                     risk_index=value), **head)
            self.assertEqual(200, r.status_code, r.content[:300])
        items = self._body(self.client.get(
            _qs("/api/fws/command/incidents", sort="risk"), **head))["items"]
        order = [i["event_id"] for i in items if i["event_id"] in (low, high)]
        self.assertEqual([high, low], order)
        r = self.client.post(_qs(f"/api/fws/command/incidents/{low}/risk-index",
                                 risk_index=90), **head)
        self.assertEqual(200, r.status_code)
        items = self._body(self.client.get(
            _qs("/api/fws/command/incidents", sort="risk"), **head))["items"]
        order = [i["event_id"] for i in items if i["event_id"] in (low, high)]
        self.assertEqual([low, high], order, "지수를 바꾼 뒤 재조회 정렬이 그대로다")
        items_b = self._body(self.client.get(
            _qs("/api/fws/command/incidents", sort="risk"), **self._bearer(self.user_b)))["items"]
        self.assertFalse({low, high} & {i["event_id"] for i in items_b})

    def test_screen_wires_tel_buttons_and_risk_list(self) -> None:
        cmd = _src("features/fws/pages/CommandHome.tsx")
        api = _src("features/fws/api.ts")
        self.assertIn("href={`tel:", cmd)
        self.assertIn("gx: 'fws-f4-09-call-forest'", cmd)
        self.assertIn("gx: 'fws-f4-09-call-provincial'", cmd)
        self.assertIn("data-gx={c.gx}", cmd)
        self.assertIn("fwsGetFresh<ContactsBody>(E.contacts(id))", cmd)
        self.assertIn("/contacts`", api)
        for gx in ("fws-f4-13-list", "fws-f4-13-risk-input", "fws-f4-13-record",
                   "fws-f4-13-refresh"):
            self.assertIn(f'data-gx="{gx}"', cmd)
        self.assertIn("'/api/fws/command/incidents?sort=risk'", api)
        self.assertIn("/risk-index`", api)
        self.assertIn("await refreshPriority()", cmd, "지수 기록 뒤 목록 재조회가 없다")
        # N1 이 넣은 전량 재조회·표식을 깨지 않았다.
        self.assertIn("async function refreshAll(id: string)", cmd)
        self.assertIn('data-gx="fws-f4-04-approve"', cmd)
