# -*- coding: utf-8 -*-
"""턴 AQ · 차선 N1 — F4 지휘 화면(`/fws/command`) 버튼 배선의 **누른 뒤 재조회** 실측.

캐시 처리: 우회 — 모든 요청에 `tests.no_cache.NO_CACHE`(`X-No-Cache`)를 싣고
`setUp`·`tearDown` 에서 `cache.clear()` 한다(화면도 재조회를 `fwsGetFresh` 로
캐시 우회해 부른다 — 같은 조건). 적중 본문이 누르기 전 값을 200 으로 되살리는
거짓 초록(P-19)을 두 쪽 다 막는다.

무엇을 재는가 (절마다 한 시험 — FWS-F4-01·02·03·04·05·06·07·08·10·11·12·15)
    ① 화면 버튼이 부르는 **그 쓰기 문**을 실제 HTTP 로 부른다.
    ② 화면이 누른 뒤 다시 부르는 **그 조회 GET** 을 재호출해 바뀐 값을 확인한다.
    ③ 테넌트 격리 1 — 다른 테넌트(B)가 같은 쓰기 문을 부르면 404 이고, **주인(A)의
       재조회 값이 그대로다**(404 하나만 믿지 않는다 — 스레드에 남은 요청이 만드는
       거짓 초록을 주인 쪽 재조회로 한 번 더 막는다).
    ④ 정적 대조 1 — `CommandHome.tsx` 에 절별 `data-gx` 와 그 경로 호출이 실제로
       있고, `api.ts` 에 그 경로 문자열이 있다(프런트 파일을 읽어 문자열로 확인).

이 시험은 `docs/agent/evidence/SPEC/*.json`·`*.retro.md` 를 쓰지 않는다(P-431 —
사람 표는 손으로만, 기계 표는 기존 쓰개 몫).
"""
from __future__ import annotations

import contextlib
import datetime as _dt
import json
import re
from pathlib import Path

from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from apps.dsm import services as dsm_services
from tests.no_cache import NO_CACHE
from tests.test_fws_app import FwsHttpTest, _qs

BASE = "/api/fws/command"


def P(eid, tail: str) -> str:  # noqa: N802
    return f"{BASE}/incidents/{eid}/{tail}"


def EV(eid, tail: str) -> str:  # noqa: N802
    return f"{BASE}/evacuations/{eid}/{tail}"


OFFICE_INTAKE = lambda eid: f"/api/fws/office/fire-events/{eid}/intake"  # noqa: E731
OFFICE_RESOURCE = lambda eid: f"/api/fws/office/fire-events/{eid}/resource-assignment"  # noqa: E731
OFFICE2_EVAC_PLAN = lambda eid: f"/api/fws/office2/evacuations/{eid}/plan"  # noqa: E731
OFFICE2_HOURLY = lambda eid: f"/api/fws/office2/reports/{eid}/hourly"  # noqa: E731


class AqN1CommandWiringBase(FwsHttpTest):
    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().setUpTestData()

    def setUp(self) -> None:
        cache.clear()
        self.client = Client(raise_request_exception=False, **NO_CACHE)
        self.event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        self.head_a = self._bearer(self.user_a)
        self.head_b = self._bearer(self.user_b)

    # ── 도우미 ──────────────────────────────────────────────────────────
    def post_ok(self, url: str, **params):
        resp = self.client.post(_qs(url, **params), **self.head_a)
        self.assertEqual(200, resp.status_code, resp.content)
        return self._body(resp)

    def get_ok(self, url: str, head=None):
        resp = self.client.get(url, **(head or self.head_a))
        self.assertEqual(200, resp.status_code, resp.content)
        return self._body(resp)

    def assert_other_tenant_blocked(self, write_url: str, read_url: str, **params) -> None:
        """테넌트 B 의 쓰기는 404 · 주인 A 의 재조회 본문은 그대로."""
        before = self.get_ok(read_url)
        resp = self.client.post(_qs(write_url, **params), **self.head_b)
        self.assertEqual(404, resp.status_code, resp.content)
        cache.clear()
        after = self.get_ok(read_url)
        self.assertEqual(before, after, "다른 테넌트의 쓰기가 주인의 재조회 값을 바꿨다")

    def advance(self, to_state: str) -> None:
        dsm_services.advance_response(scope=self.scope_a, event_id=self.event_id,
                                      to_state=to_state)


class AqN1F4CommandWiringTest(AqN1CommandWiringBase):
    # ── FWS-F4-01 한 화면 ───────────────────────────────────────────────
    def test_f4_01_screen_rereads_stage_and_post_after_press(self) -> None:
        eid = self.event_id
        before = self.get_ok(P(eid, "command"))
        self.assertIsNone(before["stage"])
        self.assertIsNone(before["command_post"])
        self.post_ok(P(eid, "stage"), stage="2단계", reason="확산 우려")
        self.post_ok(P(eid, "command-post"), address="강원 OO군 OO면 OO리 1", org_composition="산림과")
        after = self.get_ok(P(eid, "command"))
        self.assertEqual("2단계", after["stage"]["stage"])
        self.assertEqual("강원 OO군 OO면 OO리 1", after["command_post"]["address"])
        for key in ("incident", "resources", "response_clock", "evacuation"):
            self.assertIn(key, after)
        resp = self.client.get(P(eid, "command"), **self.head_b)
        self.assertEqual(404, resp.status_code)

    # ── FWS-F4-02 대응단계 확정·상향 · 지휘권 이양 ─────────────────────────
    def test_f4_02_confirm_then_reread_stage(self) -> None:
        eid = self.event_id
        self.assertIsNone(self.get_ok(P(eid, "stage"))["current"])
        self.post_ok(P(eid, "stage"), stage="1단계", reason="최초 확정")
        self.post_ok(P(eid, "stage"), stage="2단계", reason="풍속 급증", command_level="시도")
        body = self.get_ok(P(eid, "stage"))
        self.assertEqual(2, body["count"])
        self.assertEqual("2단계", body["current"]["stage"])
        self.assertEqual("1단계", body["current"]["prior_stage"])
        self.assertEqual("시도", body["current"]["command_level"])
        self.assert_other_tenant_blocked(P(eid, "stage"), P(eid, "stage"),
                                         stage="3단계", reason="남의 사건")

    # ── FWS-F4-03 통합지휘본부 설치 선언 ─────────────────────────────────
    def test_f4_03_declare_then_reread_post(self) -> None:
        eid = self.event_id
        self.assertFalse(self.get_ok(P(eid, "command-post"))["declared"])
        self.post_ok(P(eid, "command-post"), address="OO면사무소", org_composition="산림과·소방서",
                     situation_room_phone="033-000-0000")
        body = self.get_ok(P(eid, "command-post"))
        self.assertTrue(body["declared"])
        self.assertEqual("OO면사무소", body["post"]["address"])
        self.assertEqual("산림과·소방서", body["post"]["org_composition"])
        self.assert_other_tenant_blocked(P(eid, "command-post"), P(eid, "command-post"),
                                         address="남의 주소")

    # ── FWS-F4-04 헬기 요청 승인 · 투하구역 ─────────────────────────────
    def test_f4_04_approve_then_reread_drop_zone_and_clock(self) -> None:
        eid = self.event_id
        self.assertEqual(0, self.get_ok(P(eid, "aircraft-request"))["count"])
        self.post_ok(P(eid, "aircraft-request"), requesting_org="OO군 산림과",
                     drop_zone_lat=37.5, drop_zone_lng=128.1)
        body = self.get_ok(P(eid, "aircraft-request"))
        self.assertEqual(1, body["count"])
        latest = body["approvals"][-1]
        self.assertEqual({"lat": 37.5, "lng": 128.1}, latest["drop_zone"])
        self.assertTrue(latest["deadline_at"])
        timeline = self.get_ok(P(eid, "response-timeline"))
        self.assertIsNotNone(timeline["timeline"]["helicopter_dropped_at"])
        self.assert_other_tenant_blocked(P(eid, "aircraft-request"), P(eid, "aircraft-request"),
                                         requesting_org="남", drop_zone_lat=1.0, drop_zone_lng=1.0)

    # ── FWS-F4-05 대피 명령 승인 · 해제 ─────────────────────────────────
    def test_f4_05_approve_release_then_reread_status(self) -> None:
        eid = self.event_id
        villages_json = json.dumps([{"village": "OO리", "shelter": "OO경로당"}], ensure_ascii=False)
        self.post_ok(OFFICE2_EVAC_PLAN(eid), villages_json=villages_json)
        self.assertIsNone(self.get_ok(EV(eid, "command-status"))["latest_approval"])
        self.post_ok(EV(eid, "approve"), urgency="immediate")
        body = self.get_ok(EV(eid, "command-status"))
        self.assertEqual("approved", body["latest_approval"]["status"])
        self.assertEqual(["OO리"], body["latest_approval"]["villages"])
        self.assertIsNone(body["latest_release"])
        self.post_ok(EV(eid, "release"), reason="주불 진화")
        body = self.get_ok(EV(eid, "command-status"))
        self.assertEqual("released", body["latest_release"]["status"])
        self.assert_other_tenant_blocked(EV(eid, "release"), EV(eid, "command-status"),
                                         reason="남의 사건")

    # ── FWS-F4-06 협조 요청 기록 ──────────────────────────────────────────
    def test_f4_06_record_then_reread_records(self) -> None:
        eid = self.event_id
        self.assertEqual(0, self.get_ok(P(eid, "agency-request"))["count"])
        for agency in ("fire_department", "police", "military"):
            self.post_ok(P(eid, "agency-request"), agency=agency, request_detail="인력 지원")
        body = self.get_ok(P(eid, "agency-request"))
        self.assertEqual(3, body["count"])
        self.assertEqual(["fire_department", "police", "military"],
                         [r["agency"] for r in body["records"]])
        self.assert_other_tenant_blocked(P(eid, "agency-request"), P(eid, "agency-request"),
                                         agency="police")

    # ── FWS-F4-07 주불 · 진화완료 선언 ───────────────────────────────────
    def test_f4_07_declare_then_reread_declarations_and_state(self) -> None:
        eid = self.event_id
        self.advance("acknowledged")
        self.advance("in_progress")
        before = self.get_ok(P(eid, "fire-declarations"))
        self.assertEqual([], before["main_fire_out"])
        self.post_ok(P(eid, "main-fire-out"), note="주불 확인")
        self.post_ok(P(eid, "extinguished"), reason="진화선 확인")
        body = self.get_ok(P(eid, "fire-declarations"))
        self.assertEqual(1, len(body["main_fire_out"]))
        self.assertEqual(1, len(body["extinguished"]))
        self.assertEqual("closed", body["extinguished"][0]["response_state"])
        screen = self.get_ok(P(eid, "command"))
        self.assertEqual("closed", screen["incident"]["response_state"])
        self.assert_other_tenant_blocked(P(eid, "main-fire-out"), P(eid, "fire-declarations"))

    # ── FWS-F4-08 상황보고 승인 ───────────────────────────────────────────
    def test_f4_08_approve_then_reread_approvals(self) -> None:
        eid = self.event_id
        draft = self.post_ok(OFFICE2_HOURLY(eid), personnel_count=5)
        self.assertEqual(0, self.get_ok(P(eid, "hourly-report/approve"))["count"])
        self.post_ok(P(eid, "hourly-report/approve"))
        body = self.get_ok(P(eid, "hourly-report/approve"))
        self.assertEqual(1, body["count"])
        self.assertEqual(draft["hour"], body["approvals"][-1]["hour"])
        self.assert_other_tenant_blocked(P(eid, "hourly-report/approve"),
                                         P(eid, "hourly-report/approve"))

    # ── FWS-F4-10 대응 시계 + 골든타임 초과 사유 ─────────────────────────
    def test_f4_10_reason_then_reread_timeline(self) -> None:
        eid = self.event_id
        old = (timezone.now() - _dt.timedelta(minutes=40)).isoformat()
        self.post_ok(OFFICE_INTAKE(eid), source="fire_119", reported_at=old)
        before = self.get_ok(P(eid, "response-timeline"))
        self.assertTrue(before["golden_time_exceeded"])
        self.assertIsNone(before["golden_time_exceeded_reason"])
        for key in ("reported_at", "acknowledged_at", "helicopter_dropped_at",
                    "main_fire_out_at", "extinguished_at"):
            self.assertIn(key, before["timeline"])
        self.post_ok(P(eid, "golden-time-reason"), reason="야간 헬기 불가")
        after = self.get_ok(P(eid, "response-timeline"))
        self.assertFalse(after["golden_time_exceeded"])
        self.assertEqual("야간 헬기 불가", after["golden_time_exceeded_reason"]["reason"])
        self.assert_other_tenant_blocked(P(eid, "golden-time-reason"), P(eid, "response-timeline"),
                                         reason="남의 사유")

    # ── FWS-F4-11 야간 전환 ───────────────────────────────────────────────
    def test_f4_11_sunset_then_reread_night_badge(self) -> None:
        eid = self.event_id
        self.post_ok(OFFICE_RESOURCE(eid), kind="crew", resource_name="1진화대")
        self.post_ok(OFFICE_RESOURCE(eid), kind="drone", resource_name="D-1")
        before = self.get_ok(P(eid, "night-status"))
        self.assertFalse(before["is_night"])
        self.assertIsNone(before["sunset_at"])
        past = (timezone.now() - _dt.timedelta(hours=1)).replace(microsecond=0)
        # 화면의 datetime-local 칸이 보내는 모양(초·시간대 없음)을 그대로 쓴다
        local = timezone.localtime(past).strftime("%Y-%m-%dT%H:%M")
        self.post_ok(P(eid, "sunset"), sunset_at=local)
        after = self.get_ok(P(eid, "night-status"))
        self.assertTrue(after["is_night"])
        self.assertEqual("헬기 불가", after["helicopter_badge"])
        avail = {r["resource_name"]: r["available_at_night"] for r in after["night_resources"]}
        self.assertEqual({"1진화대": True, "D-1": False}, avail)
        self.assert_other_tenant_blocked(P(eid, "sunset"), P(eid, "night-status"), sunset_at=local)

    # ── FWS-F4-12 상황판단회의 기록 ───────────────────────────────────────
    def test_f4_12_record_then_reread_meetings(self) -> None:
        eid = self.event_id
        self.assertEqual(0, self.get_ok(P(eid, "meetings"))["count"])
        self.post_ok(P(eid, "meetings"), decision="2단계 상향", attendees="본부장·산림과장",
                     basis="풍속 급증")
        body = self.get_ok(P(eid, "meetings"))
        self.assertEqual(1, body["count"])
        self.assertIn("2단계 상향", body["meetings"][0]["text"])
        self.assert_other_tenant_blocked(P(eid, "meetings"), P(eid, "meetings"),
                                         decision="남의 결정")

    # ── FWS-F4-15 사후 보고 1쪽 ───────────────────────────────────────────
    def test_f4_15_summary_and_pdf_reflect_written_resource(self) -> None:
        eid = self.event_id
        before = self.get_ok(P(eid, "post-report/summary"))
        self.assertEqual([], before["resources"])
        self.post_ok(OFFICE_RESOURCE(eid), kind="crew", resource_name="1진화대")
        after = self.get_ok(P(eid, "post-report/summary"))
        self.assertEqual(["1진화대"], [r["resource_name"] for r in after["resources"]])
        self.assertEqual("집계 전", after["damage"]["status"])
        pdf = self.client.get(P(eid, "post-report.pdf"), **self.head_a)
        self.assertEqual(200, pdf.status_code)
        self.assertEqual("application/pdf", pdf["Content-Type"])
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertEqual(404, self.client.get(P(eid, "post-report.pdf"), **self.head_b).status_code)
        self.assertEqual(404, self.client.get(P(eid, "post-report/summary"),
                                              **self.head_b).status_code)


# ═══════════════════════════════════════════════════════════════════════════
# 정적 대조 — 화면 소스에 data-gx 와 경로 호출이 실제로 있는가
# ═══════════════════════════════════════════════════════════════════════════
def _frontend_src() -> Path | None:
    for base in (Path("/repo/frontend/src"),
                 *(p / "frontend" / "src" for p in Path(__file__).resolve().parents)):
        if (base / "features" / "fws" / "pages" / "CommandHome.tsx").is_file():
            return base
    return None


#: 절 → (쓰기/누름 data-gx, 재조회 data-gx, api.ts 경로 키, 그 경로 꼬리)
WIRING = {
    "FWS-F4-01": ("fws-f4-01-load", "fws-f4-01-screen", ["screen"], ["/command`"]),
    "FWS-F4-02": ("fws-f4-02-confirm", "fws-f4-02-current", ["stage"], ["/stage`"]),
    "FWS-F4-03": ("fws-f4-03-declare", "fws-f4-03-current", ["commandPost"], ["/command-post`"]),
    "FWS-F4-04": ("fws-f4-04-approve", "fws-f4-04-latest", ["aircraft"], ["/aircraft-request`"]),
    "FWS-F4-05": ("fws-f4-05-approve", "fws-f4-05-status", ["evacApprove", "evacRelease",
                                                             "evacStatus"],
                  ["/approve`", "/release`", "/command-status`"]),
    "FWS-F4-06": ("fws-f4-06-record", "fws-f4-06-records", ["agency"], ["/agency-request`"]),
    "FWS-F4-07": ("fws-f4-07-extinguished", "fws-f4-07-declarations",
                  ["mainFireOut", "extinguished", "fireDeclarations"],
                  ["/main-fire-out`", "/extinguished`", "/fire-declarations`"]),
    "FWS-F4-08": ("fws-f4-08-approve", "fws-f4-08-approvals", ["hourlyApprove"],
                  ["/hourly-report/approve`"]),
    "FWS-F4-10": ("fws-f4-10-golden-reason", "fws-f4-10-timeline",
                  ["timeline", "goldenTimeReason"],
                  ["/response-timeline`", "/golden-time-reason`"]),
    "FWS-F4-11": ("fws-f4-11-sunset", "fws-f4-11-badge", ["sunset", "nightStatus"],
                  ["/sunset`", "/night-status`"]),
    "FWS-F4-12": ("fws-f4-12-record", "fws-f4-12-meetings", ["meetings"], ["/meetings`"]),
    "FWS-F4-15": ("fws-f4-15-pdf", "fws-f4-15-summary-view",
                  ["postReportSummary", "postReportPdf"],
                  ["/post-report/summary`", "/post-report.pdf`"]),
}


class AqN1F4ScreenSourceTest(AqN1CommandWiringBase):
    def setUp(self) -> None:  # DB·HTTP 가 필요 없다
        pass

    def test_screen_declares_data_gx_and_calls_each_path(self) -> None:
        src = _frontend_src()
        self.assertIsNotNone(src, "frontend/src 를 못 찾았다 — 판정 불가를 초록으로 두지 않는다")
        page = (src / "features" / "fws" / "pages" / "CommandHome.tsx").read_text(encoding="utf-8")
        api = (src / "features" / "fws" / "api.ts").read_text(encoding="utf-8")
        self.assertIn("fwsGetFresh", page, "누른 뒤 재조회는 캐시 우회 GET 이어야 한다")
        self.assertIn("await refreshAll(activeId)", page, "누른 뒤 조회 GET 재호출이 없다")
        refresh_body = page.split("async function refreshAll", 1)[1].split("async function", 1)[0]
        missing = []
        for clause, (press, view, keys, tails) in WIRING.items():
            for gx in (press, view):
                if f'data-gx="{gx}"' not in page:
                    missing.append(f"{clause}: data-gx={gx}")
            for key in keys:
                if not re.search(rf"\b(E|fwsCommandEndpoint)\.{key}\b", page):
                    missing.append(f"{clause}: 화면이 경로 {key} 를 부르지 않는다")
                if not re.search(rf"^\s*{key}: \(id", api, re.M):
                    missing.append(f"{clause}: api.ts 에 경로 키 {key} 가 없다")
            for tail in tails:
                if f"/api/fws/command/" not in api or tail not in api:
                    missing.append(f"{clause}: api.ts 에 경로 {tail} 가 없다")
        # 조회 GET 경로는 refreshAll 안에서 다시 불린다(요약·PDF 는 누를 때 부르는 GET)
        for key in ("screen", "stage", "commandPost", "aircraft", "evacStatus", "agency",
                    "fireDeclarations", "hourlyApprove", "timeline", "nightStatus", "meetings"):
            if f"E.{key}(id)" not in refresh_body:
                missing.append(f"refreshAll 이 {key} 를 재조회하지 않는다")
        self.assertEqual([], missing)
