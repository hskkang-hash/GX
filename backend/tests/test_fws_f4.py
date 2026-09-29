# -*- coding: utf-8 -*-
"""FWS App(L4) — F4 통합지휘본부장·상황실(F4-01~13·15)의 **HTTP 실측**과
`docs/agent/evidence/SPEC/*.json` 생성 (WO-GX-20260930-18 §5 P-414 · 턴 AO 차선 N2).

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`X-No-Cache`) 헤더를 모든 요청에 싣는다
(`test_fws_f3b.py` 와 같은 규약). 멱등 캐시는 `setUp` 에서 `cache.clear()` 로 비운다.

이 파일이 재는 것 — P-356 승격 규칙 넷 중 ①②(③·④는 게이트·제안 문서)
------------------------------------------------------------------------
    ① 실제 구현    `self.client` 가 `/api/fws/command/...` 를 실제로 두드린다.
    ② 실측 증거    각 시험이 요청·응답을 그대로 `docs/agent/evidence/SPEC/<id>.json`
                    에 적는다 — `title_parts`(「제목이 부르는 것 ↔ 있는 것」 표 ·
                    빈 칸 0) 를 더한다. `tests.test_fws_app._write_evidence` 는 그
                    칸을 모른다 — 공용 파일을 고치지 않고 같은 모양 + title_parts
                    를 쓰는 `_write_evidence2` 를 이 파일 안에 둔다(`test_fws_f3b.py`
                    와 같은 판단 · D-212).

F4-14(진화완료 후 드론 순회 감시 계획)는 이 파일이 닫지 않는다 — L 규모,
`scripts/verify_spec_fws_f4.py` 의 「무엇이 없는가」를 본다.
"""
from __future__ import annotations

import datetime as _dt
import json

from django.core.cache import cache
from django.test import Client

from apps.dsm import services as dsm_services
from common.evidence_guard import allow_evidence_writes
from tests.no_cache import NO_CACHE
from tests.test_fws_app import EVIDENCE_DIR, FwsHttpTest, _qs


def _write_evidence2(clause_id: str, *, title: str, title_parts: list, test_ref: str,
                     method: str, path: str, request_params: dict, response,
                     what: str) -> None:
    """`tests.test_fws_app._write_evidence` 와 같은 모양 + `title_parts`
    (P-392 — 「제목이 부르는 것 ↔ 있는 것」 표 · 빈 칸 0 · O 게이트가 센다).
    공용 파일(`test_fws_app.py`)을 고치지 않고 이 차선 파일 안에 둔다
    (`test_fws_f3b.py::_write_evidence2` 와 같은 판단)."""
    for part in title_parts:
        missing = [k for k in ("part", "where", "status") if not (part.get(k) or "").strip()]
        if missing:
            raise AssertionError(
                f"{clause_id} title_parts 에 빈 칸이 있다: {part!r} (칸: {missing})")

    with allow_evidence_writes(
            "P-356 ② · P-392 FWS-F4 별표 절 실측 증거 — pytest 가 방금 두드린 "
            "HTTP 왕복을 그대로 적는다(손으로 옮기지 않는다)"):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            body = json.loads((response.content or b"{}").decode("utf-8", "replace"))
        except (ValueError, TypeError):
            body = {"_raw": (response.content or b"").decode("utf-8", "replace")}
        payload = {
            "id": clause_id, "title": title, "title_parts": title_parts,
            "measured_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "measured_by": "django_test_client", "test": test_ref,
            "request": {"method": method, "path": path, "params": request_params},
            "response": {"status": response.status_code, "body": body},
            "what": what,
        }
        out = EVIDENCE_DIR / f"{clause_id}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# 경로
# ═══════════════════════════════════════════════════════════════════════════
def _stage_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/stage"


def _command_post_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/command-post"


def _aircraft_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/aircraft-request"


def _evac_approve_path(eid) -> str:
    return f"/api/fws/command/evacuations/{eid}/approve"


def _evac_release_path(eid) -> str:
    return f"/api/fws/command/evacuations/{eid}/release"


def _agency_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/agency-request"


def _main_out_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/main-fire-out"


def _extinguished_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/extinguished"


def _hourly_approve_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/hourly-report/approve"


def _contacts_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/contacts"


def _timeline_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/response-timeline"


def _sunset_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/sunset"


def _night_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/night-status"


def _meetings_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/meetings"


PRIORITY_PATH = "/api/fws/command/incidents"


def _post_report_summary_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/post-report/summary"


def _post_report_pdf_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/post-report.pdf"


def _command_screen_path(eid) -> str:
    return f"/api/fws/command/incidents/{eid}/command"


OFFICE_INTAKE = lambda eid: f"/api/fws/office/fire-events/{eid}/intake"  # noqa: E731
OFFICE_RESOURCE = lambda eid: f"/api/fws/office/fire-events/{eid}/resource-assignment"  # noqa: E731
OFFICE2_EVAC_PLAN = lambda eid: f"/api/fws/office2/evacuations/{eid}/plan"  # noqa: E731
OFFICE2_HOURLY = lambda eid: f"/api/fws/office2/reports/{eid}/hourly"  # noqa: E731


class F4HttpTest(FwsHttpTest):
    """`FwsHttpTest`(F1 시험의 픽스처·헬퍼)를 그대로 쓴다 — 같은 표를 두 벌로
    만들지 않는다(`test_fws_f3b.py` 와 같은 재사용)."""

    def setUp(self) -> None:
        cache.clear()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def _advance(self, event_id: int, to_state: str) -> None:
        """K1 종결 축을 한 칸 옮긴다(시험 준비용 — 순수 파이썬 호출, HTTP 아님.
        `dsm_services.advance_response` 자체는 D-399 소유 커널 절이지 이 파일이
        재는 F4 절이 아니다 — `test_dsm_app.py::DsmFixture` 가 이미 `scope_a`
        를 이런 준비에 쓰는 것과 같은 자리)."""
        dsm_services.advance_response(scope=self.scope_a, event_id=event_id, to_state=to_state)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-02 대응단계 확정·상향(사유) · 지휘권 이양 기록(시군구→시도)
# ═══════════════════════════════════════════════════════════════════════════
class F4_02_StageConfirmTest(F4HttpTest):
    def test_confirm_stage_records_badge_and_command_level_transfer(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"stage": "2단계", "reason": "풍속 급증", "command_level": "시도"}
        resp = self.client.post(_qs(_stage_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("2단계", body["stage"])
        self.assertEqual("시도", body["command_level"])
        self.assertIsNone(body["prior_stage"])

        history = self.client.get(_stage_path(event_id), **head)
        self.assertEqual(200, history.status_code)
        hbody = self._body(history)
        self.assertEqual(1, hbody["count"])
        self.assertEqual("2단계", hbody["current"]["stage"])

        _write_evidence2(
            "FWS-F4-02",
            title="대응단계 확정·상향(사유) · 지휘권 이양 기록(시군구→시도)",
            title_parts=[
                {"part": "대응단계 확정·상향", "where": "요청 stage → 응답 stage",
                "status": "구현 — 1단계 미설정 상태에서 2단계 확정 실측"},
                {"part": "사유", "where": "요청 reason → 응답 reason",
                "status": "구현 — 감사 사유로 남음(재조회 history 로 확인)"},
                {"part": "지휘권 이양 기록(시군구→시도)",
                "where": "요청 command_level → 응답 command_level(감사 한 줄 — "
                         "세종 판정 P-414, 새 표 0)",
                "status": "구현 — command_level=시도 실측"},
                {"part": "배지·감사(완결조건)", "where": "GET .../stage → history.current",
                "status": "구현 — 재조회로 남는 배지값 실측"},
            ],
            test_ref="tests.test_fws_f4.F4_02_StageConfirmTest."
                    "test_confirm_stage_records_badge_and_command_level_transfer",
            method="POST", path=_qs(_stage_path(event_id), **params),
            request_params=params, response=resp,
            what="POST .../stage 뒤 대응단계 2단계 확정 · 지휘권 시도 이양이 감사 "
                "한 줄로 남고, GET 재조회에 그대로 남는다 — 실측")

    def test_other_tenant_event_is_404(self) -> None:
        event_id = self._event(self.stream_b, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"stage": "1단계", "reason": "x"}
        resp = self.client.post(_qs(_stage_path(event_id), **params), **head)
        self.assertEqual(404, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-03 통합지휘본부 설치 선언(위치·구성)
# ═══════════════════════════════════════════════════════════════════════════
class F4_03_CommandPostTest(F4HttpTest):
    def test_declare_then_hourly_approval_reflects_it(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"address": "OO군 OO면 산불대응센터", "org_composition": "산림과·소방서·경찰서",
                  "situation_room_phone": "033-123-4567"}
        resp = self.client.post(_qs(_command_post_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(params["address"], body["address"])

        get_resp = self.client.get(_command_post_path(event_id), **head)
        self.assertEqual(200, get_resp.status_code)
        self.assertTrue(self._body(get_resp)["declared"])

        # 상황보고 초안(F3-13)을 지어 F4-08 승인이 지휘소 선언을 반영하는지 실측
        hourly = self.client.post(_qs(OFFICE2_HOURLY(event_id), personnel_count=5), **head)
        self.assertEqual(200, hourly.status_code, hourly.content)
        approve = self.client.post(_hourly_approve_path(event_id), **head)
        self.assertEqual(200, approve.status_code, approve.content)
        reflected = self._body(approve)["command_post_reflected"]
        self.assertIsNotNone(reflected)
        self.assertEqual(params["address"], reflected["address"])

        _write_evidence2(
            "FWS-F4-03",
            title="통합지휘본부 설치 선언(위치·구성)",
            title_parts=[
                {"part": "위치", "where": "요청 address(주소 문자열) → 응답 address "
                                        "— 지도 렌더는 §0.4 금지구역 밖이라 주소 "
                                        "문자열로 좁힌다",
                "status": "구현 — 실측"},
                {"part": "구성", "where": "요청 org_composition → 응답 org_composition",
                "status": "구현 — 실측(산림과·소방서·경찰서)"},
                {"part": "상황보고 반영(완결조건)",
                "where": "F4-08 approve_hourly_report 응답 command_post_reflected",
                "status": "구현 — 지휘소 선언 뒤 매시간 상황보고 승인에 그대로 반영됨을 실측"},
            ],
            test_ref="tests.test_fws_f4.F4_03_CommandPostTest."
                    "test_declare_then_hourly_approval_reflects_it",
            method="POST", path=_qs(_command_post_path(event_id), **params),
            request_params=params, response=resp,
            what="POST .../command-post 로 위치·구성을 선언한 뒤, F4-08 상황보고 "
                "승인 응답의 command_post_reflected 에 그 값이 그대로 실린다 — 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-04 헬기 요청 승인·투하 구역 지정
# ═══════════════════════════════════════════════════════════════════════════
class F4_04_HelicopterApprovalTest(F4HttpTest):
    def test_approve_sets_drop_zone_and_thirty_minute_clock(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"requesting_org": "OO소방서", "drop_zone_lat": 36.35, "drop_zone_lng": 127.38,
                  "base": "OO공항", "eta": "15분"}
        resp = self.client.post(_qs(_aircraft_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual({"lat": 36.35, "lng": 127.38}, body["drop_zone"])
        self.assertEqual(30, body["timeout_minutes"])
        self.assertIn("deadline_at", body)

        status = self.client.get(_aircraft_path(event_id), **head)
        self.assertEqual(200, status.status_code)
        self.assertEqual(1, self._body(status)["count"])

        _write_evidence2(
            "FWS-F4-04",
            title="헬기 요청 승인·투하 구역 지정",
            title_parts=[
                {"part": "헬기 요청 승인", "where": "POST .../aircraft-request(F6-05 "
                                                "integration.request_helicopter 재사용) "
                                                "→ 응답 request_id",
                "status": "구현 — 실측"},
                {"part": "투하 구역 지정", "where": "요청 drop_zone_lat/lng → 응답 drop_zone",
                "status": "구현 — 좌표 실측"},
                {"part": "30분 시계(완결조건)", "where": "응답 deadline_at·timeout_minutes=30",
                "status": "구현 — office2.GOLDEN_TIME_THRESHOLD_SEC 재사용 실측"},
            ],
            test_ref="tests.test_fws_f4.F4_04_HelicopterApprovalTest."
                    "test_approve_sets_drop_zone_and_thirty_minute_clock",
            method="POST", path=_qs(_aircraft_path(event_id), **params),
            request_params=params, response=resp,
            what="POST .../aircraft-request 가 F6-05 문으로 실제 요청을 내고, "
                "투하구역 좌표와 30분 시계를 얹는다 — 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-05 대피 명령 승인(즉시/준비) · 해제
# ═══════════════════════════════════════════════════════════════════════════
class F4_05_EvacuationApprovalTest(F4HttpTest):
    def test_approve_immediate_then_release(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        villages_json = json.dumps([{"village": "OO리", "shelter": "OO경로당"}],
                                  ensure_ascii=False)
        plan = self.client.post(_qs(OFFICE2_EVAC_PLAN(event_id), villages_json=villages_json),
                                **head)
        self.assertEqual(200, plan.status_code, plan.content)

        params = {"urgency": "immediate"}
        resp = self.client.post(_qs(_evac_approve_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("approved", body["status"])
        self.assertEqual(8.0, body["deadline_hours"])
        self.assertEqual(["OO리"], body["villages"])

        release = self.client.post(
            _qs(_evac_release_path(event_id), reason="산불 진화로 해제"), **head)
        self.assertEqual(200, release.status_code, release.content)
        self.assertEqual("released", self._body(release)["status"])

        _write_evidence2(
            "FWS-F4-05",
            title="대피 명령 승인(즉시/준비) · 해제",
            title_parts=[
                {"part": "승인(즉시/준비)", "where": "요청 urgency=immediate → 응답 status=approved",
                "status": "구현 — 즉시 승인 실측"},
                {"part": "CBS 초안 확정(완결조건)", "where": "F3-11 초안(villages) → 응답 villages",
                "status": "구현 — F3-11 문안을 다시 안 짓고 승인만 확정(D-212)"},
                {"part": "푸시(완결조건)", "where": "응답 notified_count(notify_event 재사용)",
                "status": "구현 — 실측"},
                {"part": "해제", "where": "POST .../release → 응답 status=released",
                "status": "구현 — 실측"},
            ],
            test_ref="tests.test_fws_f4.F4_05_EvacuationApprovalTest."
                    "test_approve_immediate_then_release",
            method="POST", path=_qs(_evac_approve_path(event_id), **params),
            request_params=params, response=resp,
            what="F3-11 초안 뒤 POST .../approve(즉시) 가 8시간 지시 대피로 확정하고 "
                "발송하며, POST .../release 가 해제한다 — 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-06 소방·경찰·군 협조 요청 기록
# ═══════════════════════════════════════════════════════════════════════════
class F4_06_AgencyCoordinationTest(F4HttpTest):
    def test_record_three_agencies(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = None
        for agency in ("fire_department", "police", "military"):
            params = {"agency": agency, "request_detail": f"{agency} 협조 요청"}
            resp = self.client.post(_qs(_agency_path(event_id), **params), **head)
            self.assertEqual(200, resp.status_code, resp.content)

        listed = self.client.get(_agency_path(event_id), **head)
        self.assertEqual(200, listed.status_code)
        self.assertEqual(3, self._body(listed)["count"])

        _write_evidence2(
            "FWS-F4-06",
            title="소방·경찰·군 협조 요청 기록",
            title_parts=[
                {"part": "소방 협조 요청 기록", "where": "agency=fire_department 실측",
                "status": "구현 — 실측"},
                {"part": "경찰 협조 요청 기록", "where": "agency=police 실측",
                "status": "구현 — 실측"},
                {"part": "군 협조 요청 기록", "where": "agency=military 실측",
                "status": "구현 — 실측"},
                {"part": "기록(완결조건)", "where": "GET .../agency-request → count=3",
                "status": "구현 — 재조회로 3건 확인"},
            ],
            test_ref="tests.test_fws_f4.F4_06_AgencyCoordinationTest.test_record_three_agencies",
            method="POST", path=_qs(_agency_path(event_id), agency="military",
                                   request_detail="military 협조 요청"),
            request_params={"agency": "military"}, response=resp,
            what="소방·경찰·군 세 기관 협조 요청을 각각 POST 로 기록하고 GET 재조회로 "
                "3건을 확인한다 — 실측")

    def test_unknown_agency_is_422(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(_qs(_agency_path(event_id), agency="navy"), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-07 주불 진화 선언 · 진화완료 선언
# ═══════════════════════════════════════════════════════════════════════════
class F4_07_FireDeclarationTest(F4HttpTest):
    def test_main_out_then_extinguished_closes_response_axis(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        self._advance(event_id, "acknowledged")
        self._advance(event_id, "in_progress")

        main_out = self.client.post(_qs(_main_out_path(event_id), note="주불 진화 확인"), **head)
        self.assertEqual(200, main_out.status_code, main_out.content)

        resp = self.client.post(_qs(_extinguished_path(event_id), reason="진화선 확인·기상 안정"),
                                **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("closed", body["response_state"])

        declarations = self.client.get(f"/api/fws/command/incidents/{event_id}/fire-declarations",
                                       **head)
        self.assertEqual(200, declarations.status_code)
        dbody = self._body(declarations)
        self.assertEqual(1, len(dbody["main_fire_out"]))
        self.assertEqual(1, len(dbody["extinguished"]))

        _write_evidence2(
            "FWS-F4-07",
            title="주불 진화 선언 · 진화완료 선언",
            title_parts=[
                {"part": "주불 진화 선언", "where": "POST .../main-fire-out → 감사 한 줄"
                                              "(K1 에 없는 칸이라 App 층 선언, D-284)",
                "status": "구현 — 실측"},
                {"part": "진화완료 선언", "where": "POST .../extinguished → 응답 response_state",
                "status": "구현 — 실측"},
                {"part": "종결 축(완결조건)", "where": "dsm_services.advance_response(K1 "
                                                  "closed) 재사용 — 응답 response_state=closed",
                "status": "구현 — K1 종결 축을 실제로 옮긴 것을 실측"},
            ],
            test_ref="tests.test_fws_f4.F4_07_FireDeclarationTest."
                    "test_main_out_then_extinguished_closes_response_axis",
            method="POST", path=_qs(_extinguished_path(event_id), reason="진화선 확인·기상 안정"),
            request_params={"reason": "진화선 확인·기상 안정"}, response=resp,
            what="주불 진화 선언(감사) 뒤 진화완료 선언이 K1 종결 축(closed)을 실제로 "
                "옮긴다 — 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-08 상황보고 승인(매시간)
# ═══════════════════════════════════════════════════════════════════════════
class F4_08_HourlyReportApprovalTest(F4HttpTest):
    def test_approve_latest_draft_and_sends(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        draft = self.client.post(_qs(OFFICE2_HOURLY(event_id), personnel_count=8), **head)
        self.assertEqual(200, draft.status_code, draft.content)
        hour = self._body(draft)["hour"]

        resp = self.client.post(_hourly_approve_path(event_id), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(hour, body["hour"])

        approvals = self.client.get(_hourly_approve_path(event_id), **head)
        self.assertEqual(200, approvals.status_code)
        self.assertEqual(1, self._body(approvals)["count"])

        _write_evidence2(
            "FWS-F4-08",
            title="상황보고 승인(매시간)",
            title_parts=[
                {"part": "상황보고 승인", "where": "POST .../hourly-report/approve → 응답 hour",
                "status": "구현 — F3-13 초안(office2.hourly_reports)을 그대로 읽어 승인 실측"},
                {"part": "발송(완결조건)", "where": "응답 notified_count(notify_event 재사용)",
                "status": "구현 — 실측"},
            ],
            test_ref="tests.test_fws_f4.F4_08_HourlyReportApprovalTest."
                    "test_approve_latest_draft_and_sends",
            method="POST", path=_hourly_approve_path(event_id), request_params={},
            response=resp,
            what="F3-13 매시간 초안 뒤 POST .../hourly-report/approve 가 그 초안을 "
                "승인·발송한다 — 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-09 산림청·시도 상황실 연락(1클릭)
# ═══════════════════════════════════════════════════════════════════════════
class F4_09_ContactDirectoryTest(F4HttpTest):
    def test_forest_number_always_present_provincial_from_command_post(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        before = self.client.get(_contacts_path(event_id), **head)
        self.assertEqual(200, before.status_code)
        bbody = self._body(before)
        self.assertEqual("042-481-4119", bbody["forest_service"]["phone"])
        self.assertIsNone(bbody["provincial_situation_room"]["phone"])

        post_params = {"address": "OO지휘소", "situation_room_phone": "033-999-0000"}
        post = self.client.post(_qs(_command_post_path(event_id), **post_params), **head)
        self.assertEqual(200, post.status_code, post.content)

        resp = self.client.get(_contacts_path(event_id), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("033-999-0000", body["provincial_situation_room"]["phone"])

        _write_evidence2(
            "FWS-F4-09",
            title="산림청·시도 상황실 화상/전화 연락 버튼",
            title_parts=[
                {"part": "산림청 상황실 1클릭(전화)", "where": "응답 forest_service.phone"
                                                          "(apps.fws.contacts F1-08 재사용)",
                "status": "구현 — 042-481-4119 실측"},
                {"part": "시도 상황실 1클릭(전화)", "where": "F4-03 지휘소 선언 "
                                                        "situation_room_phone → 응답 "
                                                        "provincial_situation_room.phone",
                "status": "구현 — 033-999-0000 등록 뒤 실측(미등록 시 null — 지어내지 "
                          "않는다, D-284)"},
            ],
            test_ref="tests.test_fws_f4.F4_09_ContactDirectoryTest."
                    "test_forest_number_always_present_provincial_from_command_post",
            method="GET", path=_contacts_path(event_id), request_params={}, response=resp,
            what="산림청 번호는 항상 있고, 시도 상황실 번호는 F4-03 지휘소 선언에 "
                "실제로 등록된 값만 낸다(완결조건 '1클릭') — 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-10 대응 시계 — 신고·확인·헬기 투하·주불·진화완료 + 골든타임 초과 사유
# ═══════════════════════════════════════════════════════════════════════════
class F4_10_ResponseTimelineTest(F4HttpTest):
    def test_timeline_layers_fws_milestones_on_dsm_clock(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        intake = self.client.post(
            _qs(OFFICE_INTAKE(event_id), source="fire_119"), **head)
        self.assertEqual(200, intake.status_code, intake.content)

        heli_params = {"requesting_org": "OO소방서", "drop_zone_lat": 36.0, "drop_zone_lng": 127.0}
        heli = self.client.post(_qs(_aircraft_path(event_id), **heli_params), **head)
        self.assertEqual(200, heli.status_code, heli.content)

        self._advance(event_id, "acknowledged")
        self._advance(event_id, "in_progress")
        main_out = self.client.post(_qs(_main_out_path(event_id)), **head)
        self.assertEqual(200, main_out.status_code, main_out.content)

        resp = self.client.get(_timeline_path(event_id), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        timeline = body["timeline"]
        self.assertIsNotNone(timeline["reported_at"])
        self.assertIsNotNone(timeline["helicopter_dropped_at"])
        self.assertIsNotNone(timeline["main_fire_out_at"])
        self.assertIsNone(timeline["extinguished_at"])
        self.assertEqual(1800, body["golden_time_seconds"])
        self.assertFalse(body["golden_time_exceeded"])  # 헬기 투하가 이미 있다

        _write_evidence2(
            "FWS-F4-10",
            title="대응 시계 — 신고·확인·헬기 투하·주불·진화완료 + 골든타임 초과 사유",
            title_parts=[
                {"part": "신고", "where": "F3-06 intake(office.record_intake) → 응답 "
                                        "timeline.reported_at",
                "status": "구현 — 실측"},
                {"part": "확인", "where": "dsm_services.response_clock(DSM 대응 시계 재사용, "
                                        "P-414) → timeline.acknowledged_at",
                "status": "구현 — K1 acknowledged_at 재사용"},
                {"part": "헬기 투하", "where": "F4-04 승인 기록 → timeline.helicopter_dropped_at",
                "status": "구현 — 실측"},
                {"part": "주불", "where": "F4-07 선언 → timeline.main_fire_out_at",
                "status": "구현 — 실측"},
                {"part": "진화완료", "where": "K1 closed_at → timeline.extinguished_at",
                "status": "구현 — 아직 미선언이라 null(정직 — D-284), 다른 시험(F4-07)이 "
                          "closed 값을 실측한다"},
                {"part": "골든타임(30분) 초과 사유", "where": "응답 golden_time_seconds=1800 · "
                                                        "golden_time_exceeded",
                "status": "구현 — office2.GOLDEN_TIME_THRESHOLD_SEC 재사용, 헬기 투하로 "
                          "false 실측"},
            ],
            test_ref="tests.test_fws_f4.F4_10_ResponseTimelineTest."
                    "test_timeline_layers_fws_milestones_on_dsm_clock",
            method="GET", path=_timeline_path(event_id), request_params={}, response=resp,
            what="DSM 대응 시계(재사용) 위에 신고·헬기 투하·주불 세 칸을 얹은 대응 "
                "시계를 GET 으로 실측한다")

    def test_golden_time_exceeded_reason_clears_the_flag(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        # 신고(intake)를 골든타임 밖 시각으로 기록해 초과를 만든다
        old = (__import__("django.utils.timezone", fromlist=["now"]).now()
              - __import__("datetime").timedelta(minutes=40)).isoformat()
        self.client.post(_qs(OFFICE_INTAKE(event_id), source="fire_119", reported_at=old),
                        **head)
        exceeded_before = self.client.get(_timeline_path(event_id), **head)
        self.assertTrue(self._body(exceeded_before)["golden_time_exceeded"])

        resp = self.client.post(
            _qs(f"/api/fws/command/incidents/{event_id}/golden-time-reason",
               reason="산불 다발로 헬기 배정 지연"), **head)
        self.assertEqual(200, resp.status_code, resp.content)

        after = self.client.get(_timeline_path(event_id), **head)
        self.assertFalse(self._body(after)["golden_time_exceeded"])
        self.assertIsNotNone(self._body(after)["golden_time_exceeded_reason"])


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-11 야간 전환(일몰) — 헬기 불가·야간 진화 자원 표시
# ═══════════════════════════════════════════════════════════════════════════
class F4_11_NightTransitionTest(F4HttpTest):
    def test_sunset_in_the_past_marks_night_and_helicopter_unavailable(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        self.client.post(_qs(OFFICE_RESOURCE(event_id), kind="crew", resource_name="1진화대"),
                        **head)
        self.client.post(_qs(OFFICE_RESOURCE(event_id), kind="drone", resource_name="D-1"),
                        **head)

        past = (__import__("django.utils.timezone", fromlist=["now"]).now()
               - __import__("datetime").timedelta(hours=1)).isoformat()
        set_resp = self.client.post(_qs(_sunset_path(event_id), sunset_at=past), **head)
        self.assertEqual(200, set_resp.status_code, set_resp.content)

        resp = self.client.get(_night_path(event_id), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertTrue(body["is_night"])
        self.assertEqual("헬기 불가", body["helicopter_badge"])
        by_kind = {r["kind"]: r["available_at_night"] for r in body["night_resources"]}
        self.assertTrue(by_kind["crew"])
        self.assertFalse(by_kind["drone"])

        _write_evidence2(
            "FWS-F4-11",
            title="야간 전환(일몰) — 헬기 불가·야간 진화 자원 표시",
            title_parts=[
                {"part": "야간 전환(일몰)", "where": "요청 sunset_at → 응답 is_night",
                "status": "구현 — 과거 일몰 시각으로 야간 전환 실측"},
                {"part": "헬기 불가", "where": "응답 helicopter_badge",
                "status": "구현 — '헬기 불가' 배지 실측"},
                {"part": "야간 진화 자원 표시(완결조건 '배지')",
                "where": "응답 night_resources[].available_at_night(F3-08 자원배정 재사용)",
                "status": "구현 — 진화대 가능·드론 불가 실측"},
            ],
            test_ref="tests.test_fws_f4.F4_11_NightTransitionTest."
                    "test_sunset_in_the_past_marks_night_and_helicopter_unavailable",
            method="GET", path=_night_path(event_id), request_params={}, response=resp,
            what="일몰 시각을 과거로 기록하면 야간 전환·헬기 불가 배지·자원별 야간 "
                "가동 가능 여부가 실측된다")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-12 상황판단회의 기록 — DSM-U2-03 재사용
# ═══════════════════════════════════════════════════════════════════════════
class F4_12_SituationMeetingTest(F4HttpTest):
    def test_record_then_list_is_scoped_to_this_event(self) -> None:
        event_a = self._event(self.stream_a, severity="critical", event_type="fire")
        event_a2 = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"attendees": "산림과장·소방서장", "decision": "2단계 유지", "basis": "풍속 4m/s"}
        resp = self.client.post(_qs(_meetings_path(event_a), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("2단계 유지", body["decision"])  # 사건 표가 벗겨져 나온다

        # 다른 사건의 회의는 섞이지 않는다
        self.client.post(_qs(_meetings_path(event_a2), decision="별개 회의"), **head)

        listed = self.client.get(_meetings_path(event_a), **head)
        self.assertEqual(200, listed.status_code)
        lbody = self._body(listed)
        self.assertEqual(1, lbody["count"])
        self.assertIn("2단계 유지", lbody["meetings"][0]["text"])
        self.assertNotIn("[사건", lbody["meetings"][0]["text"])  # 표가 벗겨졌다

        _write_evidence2(
            "FWS-F4-12",
            title="상황판단회의 기록",
            title_parts=[
                {"part": "회의 기록", "where": "POST .../meetings(DSM-U2-03 "
                                            "situation_meeting_service.record_meeting "
                                            "재사용, 세종 판정 P-414) → 응답 decision",
                "status": "구현 — 실측"},
                {"part": "사건별 구분(완결조건 '기록')",
                "where": "GET .../meetings → count=1(다른 사건 회의와 안 섞임)",
                "status": "구현 — 두 사건 각각 기록 뒤 섞이지 않음을 실측"},
            ],
            test_ref="tests.test_fws_f4.F4_12_SituationMeetingTest."
                    "test_record_then_list_is_scoped_to_this_event",
            method="POST", path=_qs(_meetings_path(event_a), **params),
            request_params=params, response=resp,
            what="DSM-U2-03 회의 기록 문을 그대로 재사용하고, 사건별 표를 얹어 두 "
                "사건의 회의가 섞이지 않음을 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-13 동시 다발 사건 우선순위(위험도 정렬)
# ═══════════════════════════════════════════════════════════════════════════
class F4_13_PriorityQueueTest(F4HttpTest):
    def test_critical_ranks_above_warning(self) -> None:
        head = self._bearer(self.user_a)
        low = self._event(self.stream_a, severity="info", event_type="fire")
        high = self._event(self.stream_a, severity="critical", event_type="fire")

        resp = self.client.get(_qs(PRIORITY_PATH, sort="risk"), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        ids = [item["event_id"] for item in body["items"]]
        self.assertIn(high, ids)
        self.assertIn(low, ids)
        self.assertLess(ids.index(high), ids.index(low))

        _write_evidence2(
            "FWS-F4-13",
            title="동시 다발 사건 우선순위(위험도 정렬)",
            title_parts=[
                {"part": "동시 다발 사건 목록", "where": "GET /command/incidents?sort=risk "
                                                    "→ 응답 items(dsm_services.recent_events "
                                                    "재사용)",
                "status": "구현 — 실측"},
                {"part": "위험도 정렬(완결조건)", "where": "응답 items 순서 "
                                                    "(severity=critical 이 info 보다 앞)",
                "status": "구현 — critical 사건이 info 사건보다 앞섬을 실측"},
            ],
            test_ref="tests.test_fws_f4.F4_13_PriorityQueueTest.test_critical_ranks_above_warning",
            method="GET", path=_qs(PRIORITY_PATH, sort="risk"), request_params={"sort": "risk"},
            response=resp,
            what="critical·info 두 사건을 만들고 GET .../incidents?sort=risk 가 critical "
                "을 앞에 두는 것을 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-15 사후 보고서 1쪽(대응 시계·자원·대피·피해)
# ═══════════════════════════════════════════════════════════════════════════
class F4_15_PostIncidentReportTest(F4HttpTest):
    def test_pdf_and_summary_cover_clock_resources_and_evacuation(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        self.client.post(_qs(OFFICE_RESOURCE(event_id), kind="crew", resource_name="1진화대"),
                        **head)
        villages_json = json.dumps([{"village": "OO리", "shelter": "OO경로당"}],
                                  ensure_ascii=False)
        self.client.post(_qs(OFFICE2_EVAC_PLAN(event_id), villages_json=villages_json), **head)

        pdf_resp = self.client.get(_post_report_pdf_path(event_id), **head)
        self.assertEqual(200, pdf_resp.status_code)
        self.assertEqual("application/pdf", pdf_resp["Content-Type"])
        self.assertGreater(len(pdf_resp.content), 100)

        resp = self.client.get(_post_report_summary_path(event_id), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(1, len(body["resources"]))
        self.assertEqual(1, body["evacuation"]["total_villages"])
        self.assertEqual("집계 전", body["damage"]["status"])

        _write_evidence2(
            "FWS-F4-15",
            title="사후 보고서 1쪽(대응 시계·자원·대피·피해)",
            title_parts=[
                {"part": "PDF(완결조건)", "where": "GET .../post-report.pdf(dsm_services."
                                              "incident_report — UX-30 재사용) → "
                                              "Content-Type application/pdf",
                "status": "구현 — PDF 바이트 실측(대응시계·판정·피해현황 포함)"},
                {"part": "자원", "where": "GET .../post-report/summary → resources",
                "status": "구현 — F3-08 자원배정 재사용 실측"},
                {"part": "대피", "where": "GET .../post-report/summary → evacuation",
                "status": "구현 — F3-11 대피현황 재사용 실측"},
                {"part": "피해", "where": "GET .../post-report/summary → damage.status",
                "status": "구현 — '집계 전'을 정직하게 낸다(이 저장소에 피해집계 칸이 "
                          "없다, incident_report.py::_damage_block 과 같은 정직함 — "
                          "0 으로 지어내지 않는다)"},
            ],
            test_ref="tests.test_fws_f4.F4_15_PostIncidentReportTest."
                    "test_pdf_and_summary_cover_clock_resources_and_evacuation",
            method="GET", path=_post_report_summary_path(event_id), request_params={},
            response=resp,
            what="UX-30 PDF(대응시계 포함) 재사용 옆에 자원·대피 요약을 더하고, "
                "피해는 정직하게 '집계 전'으로 낸다 — 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F4-01 지휘 화면 — 사건 1건 전체를 한 화면으로
# ═══════════════════════════════════════════════════════════════════════════
class F4_01_CommandScreenTest(F4HttpTest):
    def test_one_screen_bundles_stage_resources_clock_evacuation_post(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        self.client.post(_qs(_stage_path(event_id), stage="2단계", reason="확산 우려"), **head)
        self.client.post(_qs(OFFICE_RESOURCE(event_id), kind="crew", resource_name="1진화대"),
                        **head)
        villages_json = json.dumps([{"village": "OO리", "shelter": "OO경로당"}],
                                  ensure_ascii=False)
        self.client.post(_qs(OFFICE2_EVAC_PLAN(event_id), villages_json=villages_json), **head)
        post_params = {"address": "OO지휘소", "org_composition": "산림과·소방서"}
        self.client.post(_qs(_command_post_path(event_id), **post_params), **head)

        resp = self.client.get(_command_screen_path(event_id), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("2단계", body["stage"]["stage"])
        self.assertEqual(1, len(body["resources"]))
        self.assertEqual(1, body["evacuation"]["total_villages"])
        self.assertEqual("OO지휘소", body["command_post"]["address"])
        self.assertIn("reported_at", body["response_clock"])

        _write_evidence2(
            "FWS-F4-01",
            title="지휘 화면 — 사건 1건 전체(지도·화선·자원·시계·대피·단계)",
            title_parts=[
                {"part": "사건 1건", "where": "GET .../command → 응답 event_id·incident",
                "status": "구현 — 실측"},
                {"part": "단계", "where": "응답 stage(F4-02 재사용)",
                "status": "구현 — 2단계 실측"},
                {"part": "자원", "where": "응답 resources(F3-08 재사용)",
                "status": "구현 — 1건 실측"},
                {"part": "시계", "where": "응답 response_clock(F4-10 재사용)",
                "status": "구현 — 실측"},
                {"part": "대피", "where": "응답 evacuation(F3-11 재사용)",
                "status": "구현 — 1개 마을 실측"},
                {"part": "한 화면(완결조건)", "where": "GET /command/incidents/{id}/command "
                                              "응답 하나에 위 다섯이 함께 실린다",
                "status": "구현 — 단일 응답으로 실측(지도·화선 렌더는 §0.4 금지구역 밖 "
                          "— 위치는 F4-03 주소 문자열로 대신하고, 화선 데이터 자체가 "
                          "이 저장소에 없어(F3-10 확산예측 미착수) 이 절의 계약에서 뺐다)"},
            ],
            test_ref="tests.test_fws_f4.F4_01_CommandScreenTest."
                    "test_one_screen_bundles_stage_resources_clock_evacuation_post",
            method="GET", path=_command_screen_path(event_id), request_params={}, response=resp,
            what="단계·자원·대응시계·대피·지휘소를 한 GET 응답으로 묶어 지휘 화면 "
                "완결조건('한 화면')을 실측")
