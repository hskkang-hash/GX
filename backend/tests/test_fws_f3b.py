# -*- coding: utf-8 -*-
"""FWS App(L4) — F3 잔여(대피·상황보고·통계·오탐률·단속·훈련·온보딩 · F3-11~20)의
**HTTP 실측**과 `docs/agent/evidence/SPEC/*.json` 생성
(WO-GX-20260929-17 §5 P-356·392·397 · 턴 AN 차선 N3).

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`X-No-Cache`) 헤더를 모든 요청에 싣는다
(`test_fws_f6.py` 와 같은 규약). 멱등 캐시는 `setUp` 에서 `cache.clear()` 로 비운다.

이 파일이 재는 것 — P-356 승격 규칙 넷 중 ①②(③·④는 게이트·제안 문서)
------------------------------------------------------------------------
    ① 실제 구현    `self.client` 가 `/api/fws/office2/...` 를 실제로 두드린다.
    ② 실측 증거    각 시험이 요청·응답을 그대로 `docs/agent/evidence/SPEC/<id>.json`
                    에 적는다 — 그러나 이 턴(P-392)은 증거에 **title_parts**
                    (「제목이 부르는 것 ↔ 있는 것」 표 · 빈 칸 0)를 더 요구한다.
                    `tests.test_fws_app._write_evidence` 는 그 칸을 모른다 —
                    두 벌을 만들지 않되(D-212), 이 파일이 그 함수를 감싸는 대신
                    **같은 모양 + title_parts** 를 쓰는 `_write_evidence2` 를
                    이 파일 안에 둔다(공용 파일을 고치지 않는다 · §0.4 인접).

F3-10(확산예측)·F3-15(조사반·드론 피해면적)는 이 파일이 닫지 않는다 — L 규모,
`scripts/verify_spec_fws_f3b.py`·`docs/agent/evidence/SPEC/N3_promotions_an.md`
의 「무엇이 없는가」를 본다.

★ [턴 AO 차선 O · WO-18 · 2026-09-29] F3-16 은 이 파일이 여전히 여덟 칸을 실측
  하지만(발생·면적·원인·시간대·구역·오인율·확인 시간 + 골든타임 근사), 「골든
  타임 준수율」 행이 대리 지표(확인 회신 30분 비율)라 이 턴의 더한 규약으로는
  **열린 행**이다 — 나머지 일곱이 실측이어도 절 전체를 닫지 않는다
  (`scripts/verify_spec_fws_f3b.py` 가 NOT_STARTED 로 옮겼다). F3-18(계도·단속
  통계·입산통제구역)은 이 턴이 곁표(`common.models.AuditScope`)로 "본인만" 한계를
  넘어 **같은 테넌트 전체**를 세도록 고쳤다 — 이제 반쪽이 아니다(CLOSED 유지).
"""
from __future__ import annotations

import datetime as _dt
import json

from django.core.cache import cache
from django.test import Client
from django.utils import timezone as dj_timezone

from apps.dsm import services as dsm_services
from common.evidence_guard import allow_evidence_writes
from tests.no_cache import NO_CACHE
from tests.test_fws_app import EVIDENCE_DIR, FwsHttpTest, _qs


def _write_evidence2(clause_id: str, *, title: str, title_parts: list, test_ref: str,
                     method: str, path: str, request_params: dict, response,
                     what: str, retro: str | None = None) -> None:
    """`tests.test_fws_app._write_evidence` 와 같은 모양 + `title_parts`
    (P-392 — 「제목이 부르는 것 ↔ 있는 것」 표 · 빈 칸 0 · O 게이트가 센다).
    공용 파일(`test_fws_app.py`)을 고치지 않고 이 차선 파일 안에 둔다.

    ★ [턴 AP · N2b · P-421 ⑤] 기존 파일에 `retro`(사람이 대조한 1줄 — 재판정·소급)
      가 있으면 그 `title_parts`·`retro` 를 **그대로 둔다** — 이 시험은 요청/응답만
      갱신한다(재판정이 연 행을 시험이 옛 표로 조용히 덮지 않게). 이 시험이 그
      절의 표를 **새로 채울 때만** `retro=` 를 넘기고, 그때는 새 표 + 그 한 줄로
      다시 붙인다."""
    for part in title_parts:
        missing = [k for k in ("part", "where", "status") if not (part.get(k) or "").strip()]
        if missing:
            raise AssertionError(
                f"{clause_id} title_parts 에 빈 칸이 있다: {part!r} (칸: {missing})")

    with allow_evidence_writes(
            "P-356 ② · P-392 FWS-F3(잔여) 별표 절 실측 증거 — pytest 가 방금 두드린 "
            "HTTP 왕복을 그대로 적는다(손으로 옮기지 않는다)"):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            body = json.loads((response.content or b"{}").decode("utf-8", "replace"))
        except (ValueError, TypeError):
            body = {"_raw": (response.content or b"").decode("utf-8", "replace")}
        payload = {
            #: [턴 AQ · P-431 · 차선 Q] title_parts·retro 는 json 에 안 쓴다(정본 <id>.retro.md).
            "id": clause_id, "title": title,
            "measured_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "measured_by": "django_test_client", "test": test_ref,
            "request": {"method": method, "path": path, "params": request_params},
            "response": {"status": response.status_code, "body": body},
            "what": what,
        }
        out = EVIDENCE_DIR / f"{clause_id}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")


def _evac_plan_path(event_id) -> str:
    return f"/api/fws/office2/evacuations/{event_id}/plan"


def _evac_progress_path(event_id) -> str:
    return f"/api/fws/office2/evacuations/{event_id}/progress"


def _evac_status_path(event_id) -> str:
    return f"/api/fws/office2/evacuations/{event_id}/status"


def _hourly_path(event_id) -> str:
    return f"/api/fws/office2/reports/{event_id}/hourly"


def _final_path(event_id) -> str:
    return f"/api/fws/office2/reports/{event_id}/final"


STATS_FIRES = "/api/fws/office2/stats/fires"
STATS_CAMERA = "/api/fws/office2/stats/camera-false-alarms"
CAMERA_THRESHOLD_TEST = "/api/fws/office2/stats/camera-false-alarms/threshold-test"
PATROL_ENFORCEMENT = "/api/fws/office2/patrol/enforcement"
PATROL_ENFORCEMENT_MINE = "/api/fws/office2/patrol/enforcement/mine"
ENTRY_ZONES = "/api/fws/office2/entry-control-zones"
DRILL_START = "/api/fws/office2/drill/start"
DRILL_STATUS = "/api/fws/office2/drill/status"
DRILL_END = "/api/fws/office2/drill/end"
ONBOARDING = "/api/fws/office2/onboarding/progress"


class F3BHttpTest(FwsHttpTest):
    """`FwsHttpTest`(F1 시험의 픽스처·헬퍼)를 그대로 쓴다 — 같은 표를 두 벌로 만들지
    않는다(`test_fws_f6.py` 와 같은 재사용)."""

    def setUp(self) -> None:
        cache.clear()
        self.client = Client(raise_request_exception=False, **NO_CACHE)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-11 대피 초안(대상 마을·대피소·문안 자동 → F4 승인 요청)
# ═══════════════════════════════════════════════════════════════════════════
class F3_11_EvacuationPlanTest(F3BHttpTest):
    def test_plan_drafts_cbs_text_per_village_and_waits_for_f4_approval(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        villages_json = json.dumps([
            {"village": "OO면 OO리", "shelter": "OO경로당"},
            {"village": "OO면 XX리", "shelter": "XX마을회관"},
        ], ensure_ascii=False)
        params = {"villages_json": villages_json, "kind": "order"}
        resp = self.client.post(_qs(_evac_plan_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("pending_f4_approval", body["status"])
        self.assertEqual(2, len(body["drafts"]))
        for draft in body["drafts"]:
            self.assertLessEqual(len(draft["short"]), 90)
            self.assertLessEqual(len(draft["long"]), 157)
            self.assertEqual(8.0, draft["deadline_hours"])
            self.assertIn("shelter", draft)
        _write_evidence2(
            "FWS-F3-11",
            title="대피 초안 — 대상 마을·대피소·문안(CBS 90/157자·마을방송문·"
                 "앱 푸시) 자동 → F4 승인 요청",
            title_parts=[
                {"part": "대상 마을", "where": "요청 villages_json 목록 → 응답 "
                                            "drafts[].village",
                "status": "구현 — 실측 2건"},
                {"part": "대피소", "where": "요청 villages_json.shelter → 응답 "
                                          "drafts[].shelter",
                "status": "구현 — 실측 2건"},
                {"part": "문안(CBS 90/157자)", "where": "응답 drafts[].short/long "
                                                      "(F6-07 integration.draft_"
                                                      "evacuation_notice 재사용)",
                "status": "구현 — 90/157자 상한 실측"},
                {"part": "마을방송문", "where": "drafts[].long — annex 가 CBS 문안과 "
                                             "마을방송문을 같은 문안으로 대안(§5.1 "
                                             "F6-07 대안)",
                "status": "F6-07 대안 그대로 — 별도 필드 없음(문안 공용)"},
                {"part": "앱 푸시", "where": "해당 없음",
                "status": "[미확인] — 산림청 스마트산림재난 앱 연동은 F6-07 이 이미 "
                          "범위 밖으로 남겼다(외부 자격증명 필요) · 이 절도 같은 "
                          "한계를 물려받는다"},
                {"part": "F4 승인 요청", "where": "응답 status=pending_f4_approval",
                "status": "구현 — 승인 대기 상태로 남는다(F4 확정은 F4 담당 몫)"},
            ],
            test_ref="tests.test_fws_f3b.F3_11_EvacuationPlanTest."
                    "test_plan_drafts_cbs_text_per_village_and_waits_for_f4_approval",
            method="POST", path=_qs(_evac_plan_path(event_id), **params),
            request_params=params, response=resp,
            what="POST .../plan 뒤 마을 2곳 각각의 CBS 문안(90/157자 상한 · 8시간 "
                "지시 대피)이 생기고 status=pending_f4_approval 로 F4 승인을 "
                "기다린다 — 실측")

    def test_other_tenant_event_is_404(self) -> None:
        event_id = self._event(self.stream_b, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"villages_json": json.dumps([{"village": "x", "shelter": "y"}])}
        resp = self.client.post(_qs(_evac_plan_path(event_id), **params), **head)
        self.assertEqual(404, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-12 대피 이행 확인(마을별 완료·잔류자·요양시설)
# ═══════════════════════════════════════════════════════════════════════════
class F3_12_EvacuationProgressTest(F3BHttpTest):
    def test_progress_then_status_shows_percent_and_remaining(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        villages_json = json.dumps([
            {"village": "동리", "shelter": "동리회관"},
            {"village": "서리", "shelter": "서리경로당"},
        ], ensure_ascii=False)
        plan = self.client.post(
            _qs(_evac_plan_path(event_id), villages_json=villages_json), **head)
        self.assertEqual(200, plan.status_code, plan.content)

        p1 = {"village": "동리", "completed": True, "remaining_residents": 0,
             "care_facility_cleared": True}
        r1 = self.client.post(_qs(_evac_progress_path(event_id), **p1), **head)
        self.assertEqual(200, r1.status_code, r1.content)

        p2 = {"village": "서리", "completed": False, "remaining_residents": 3,
             "care_facility_cleared": False, "note": "요양시설 이송 차량 대기 중"}
        r2 = self.client.post(_qs(_evac_progress_path(event_id), **p2), **head)
        self.assertEqual(200, r2.status_code, r2.content)

        resp = self.client.get(_evac_status_path(event_id), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(2, body["total_villages"])
        self.assertEqual(1, body["completed_villages"])
        self.assertEqual(50.0, body["percent_complete"])
        self.assertEqual(3, body["remaining_residents_total"])
        self.assertEqual(1, body["care_facilities_open"])
        _write_evidence2(
            "FWS-F3-12", title="대피 이행 확인(마을별 완료·잔류자·요양시설)",
            title_parts=[
                {"part": "마을별 완료", "where": "요청 completed → 응답 "
                                              "villages[].completed",
                "status": "구현 — 동리 완료 · 서리 미완료 실측"},
                {"part": "잔류자", "where": "요청 remaining_residents → 응답 "
                                          "remaining_residents_total",
                "status": "구현 — 3명 실측"},
                {"part": "요양시설", "where": "요청 care_facility_cleared → 응답 "
                                            "care_facilities_open",
                "status": "구현 — 미해제 1건 실측"},
                {"part": "이행 %(완결조건)", "where": "응답 percent_complete",
                "status": "구현 — 50.0 실측(2곳 중 1곳 완료)"},
            ],
            test_ref="tests.test_fws_f3b.F3_12_EvacuationProgressTest."
                    "test_progress_then_status_shows_percent_and_remaining",
            method="GET", path=_evac_status_path(event_id), request_params={},
            response=resp,
            what="대피 이행 기록 2건(완료 1 · 미완료 1) 뒤 GET status 가 이행 "
                "50.0% · 잔류자 3 · 요양시설 미해제 1건을 그대로 낸다 — 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-13 매시간 상황보고 초안 → 산림청 입력 항목 내보내기
# ═══════════════════════════════════════════════════════════════════════════
class F3_13_HourlyReportTest(F3BHttpTest):
    def test_draft_then_export_and_list(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"personnel_count": 12, "equipment_note": "진화차 2대 · 등짐펌프 8",
                 "casualties_count": 0, "facility_note": "인근 민가 3동 위험",
                 "weather_note": "풍속 4m/s 남서풍"}
        resp = self.client.post(_qs(_hourly_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(12, body["personnel_count"])
        self.assertIn("fields", body["kfs_export"])
        labels = [f["label"] for f in body["kfs_export"]["fields"]]
        self.assertIn("신고일시", labels)

        listed = self.client.get(_hourly_path(event_id), **head)
        self.assertEqual(200, listed.status_code)
        self.assertEqual(1, self._body(listed)["count"])
        _write_evidence2(
            "FWS-F3-13",
            title="매시간 상황보고 초안(발생·위치·면적·진화 현황·인력/장비·인명·"
                 "시설·기상) → 승인 → 산림청 입력 항목 내보내기",
            title_parts=[
                {"part": "발생·위치", "where": "응답 occurred_at·lat·lng·address",
                "status": "구현 — K1 이벤트에서 그대로"},
                {"part": "면적", "where": "해당 없음",
                "status": "정직하게 비움[None] — 진행 중 사건의 면적은 F3-14 최종 "
                          "실측 전까지 측정값이 없다(D-284, 지어내지 않는다)"},
                {"part": "진화 현황", "where": "응답 response_state·severity",
                "status": "구현 — K1 대응 진행 축 재사용"},
                {"part": "인력/장비", "where": "요청 personnel_count·equipment_note "
                                             "→ 응답 그대로",
                "status": "구현 — 실측 12명 · 장비 메모"},
                {"part": "인명", "where": "요청 casualties_count → 응답 그대로",
                "status": "구현 — 실측 0"},
                {"part": "시설", "where": "요청 facility_note → 응답 그대로",
                "status": "구현 — 실측"},
                {"part": "기상", "where": "요청 weather_note → 응답 그대로",
                "status": "구현 — 실측"},
                {"part": "매시간 초안(완결조건)", "where": "GET 목록 count",
                "status": "구현 — 1건 누적 실측"},
                {"part": "산림청 입력 항목 내보내기(완결조건)",
                "where": "응답 kfs_export.fields(F6-01 export_kfs_feed 재사용)",
                "status": "구현 — 신고일시 등 라벨 실측"},
            ],
            test_ref="tests.test_fws_f3b.F3_13_HourlyReportTest.test_draft_then_export_and_list",
            method="POST", path=_qs(_hourly_path(event_id), **params),
            request_params=params, response=resp,
            what="POST .../hourly 뒤 초안 항목(인력·장비·인명·시설·기상)과 F6-01 "
                "내보내기(kfs_export.fields)가 한 응답에 실린다 — 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-14 진화완료 보고·산불 통계 항목(산불정보ID·원인·면적·문자전송 여부·
# 일출몰) — 항목 1:1
# ═══════════════════════════════════════════════════════════════════════════
class F3_14_FinalReportTest(F3BHttpTest):
    def test_record_final_report_maps_items_one_to_one(self) -> None:
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        params = {"cause": "소각", "area_ha": 12.3, "sms_sent": True,
                 "sunrise": "06:32", "sunset": "18:07"}
        resp = self.client.post(_qs(_final_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        keys = {item["key"] for item in body["items"]}
        self.assertEqual(
            {"fire_info_id", "cause", "area_ha", "sms_sent", "sunrise", "sunset"}, keys)
        by_key = {item["key"]: item["value"] for item in body["items"]}
        self.assertEqual("소각", by_key["cause"])
        self.assertEqual(12.3, by_key["area_ha"])
        self.assertTrue(by_key["sms_sent"])
        self.assertEqual(f"FWS-{event_id}", by_key["fire_info_id"])

        again = self.client.get(_final_path(event_id), **head)
        self.assertEqual(200, again.status_code)
        self.assertTrue(self._body(again)["recorded"])
        _write_evidence2(
            "FWS-F3-14",
            title="진화완료 보고·산불 통계 항목(산불정보ID·원인·면적·문자전송 "
                 "여부·일출몰) — 항목 1:1",
            title_parts=[
                {"part": "산불정보ID", "where": "응답 items[key=fire_info_id]",
                "status": "구현 — 미기재 시 FWS-{event_id} 자동 부여 실측"},
                {"part": "원인", "where": "요청 cause(5택: 입산자실화·소각·담뱃불·"
                                        "건축물화재·기타 · annex FF-7) → 응답 그대로",
                "status": "구현 — '소각' 실측"},
                {"part": "면적", "where": "요청 area_ha → 응답 그대로",
                "status": "구현 — 12.3ha 실측"},
                {"part": "문자전송 여부", "where": "요청 sms_sent → 응답 그대로",
                "status": "구현 — true 실측"},
                {"part": "일출몰", "where": "요청 sunrise·sunset → 응답 그대로",
                "status": "구현 — 06:32/18:07 실측(수동 입력 — 천문 계산 API 미연동)"},
                {"part": "항목 1:1(완결조건)", "where": "응답 items 6칸",
                "status": "구현 — KFS_EXPORT_FIELDS 와 같은 형으로 6항목 1:1 실측"},
            ],
            test_ref="tests.test_fws_f3b.F3_14_FinalReportTest."
                    "test_record_final_report_maps_items_one_to_one",
            method="POST", path=_qs(_final_path(event_id), **params),
            request_params=params, response=resp,
            what="POST .../final 뒤 6항목(산불정보ID·원인·면적·문자전송 여부·"
                "일출·일몰)이 1:1로 실리고, GET 재조회에서도 그대로 남는다 — 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-16 통계 — 발생·면적·원인·시간대·구역·오인율·확인 시간·골든타임 준수율
# ═══════════════════════════════════════════════════════════════════════════
class F3_16_FireStatsTest(F3BHttpTest):
    def test_stats_covers_all_eight_parts(self) -> None:
        head = self._bearer(self.user_a)
        now = dj_timezone.now()

        confirmed_id = self._event(self.stream_a, severity="critical",
                                   event_type="fire", when=now - _dt.timedelta(minutes=40))
        dsm_services.review_event(scope=self.scope_a, event_id=confirmed_id,
                                  verdict="confirmed", reason="현장 확인 — 산불 맞음")
        final_params = {"cause": "입산자실화", "area_ha": 5.5, "sms_sent": True}
        final_resp = self.client.post(
            _qs(_final_path(confirmed_id), **final_params), **head)
        self.assertEqual(200, final_resp.status_code, final_resp.content)

        rejected_id = self._event(self.stream_a, severity="warning",
                                  event_type="fire", when=now - _dt.timedelta(minutes=10))
        dsm_services.review_event(scope=self.scope_a, event_id=rejected_id,
                                  verdict="rejected", reason="false_alarm [fog_or_cloud] 안개")

        #: ── 골든타임(대응 시계 실측) — 발생·신고·도착 셋을 엇갈리게 심는다 ──────
        #:   late : 발생 45분 전 → 지금 도착(45분 · 초과)
        #:   ok   : 발생 5분 전 → 지금 도착(5분 · 준수)
        #:   intake: 발생 50분 전이지만 **신고 접수** 10분 전 → 지금 도착 —
        #:           신고 기준이면 10분(준수), 발생 기준이면 50분(초과).
        from apps.fws import office as fws_office

        g_late = self._event(self.stream_a, severity="critical", event_type="fire",
                             when=now - _dt.timedelta(minutes=45))
        g_ok = self._event(self.stream_a, severity="critical", event_type="fire",
                           when=now - _dt.timedelta(minutes=5))
        g_intake = self._event(self.stream_a, severity="critical", event_type="fire",
                               when=now - _dt.timedelta(minutes=50))
        intake = self.client.post(_qs(
            f"/api/fws/office/fire-events/{g_intake}/intake",
            source=fws_office.REPORT_SOURCE_119,
            reported_at=(now - _dt.timedelta(minutes=10)).isoformat()), **head)
        self.assertEqual(200, intake.status_code, intake.content)
        for eid in (g_late, g_ok, g_intake):
            dsm_services.advance_response(scope=self.scope_a, event_id=eid,
                                          to_state="acknowledged")
            dsm_services.advance_response(scope=self.scope_a, event_id=eid,
                                          to_state="in_progress")

        resp = self.client.get(STATS_FIRES, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(3, body["golden_time_measured_n"], body)
        self.assertEqual(2, body["golden_time_compliant_n"], body)
        self.assertEqual(66.7, body["golden_time_compliance_pct"])
        self.assertIn("arrived_at", body["golden_time_basis"])
        self.assertGreaterEqual(body["occurrence_count"], 2)
        self.assertIn(self.stream_a.name, body["by_zone"])
        self.assertEqual(5.5, body["area_ha_total"])
        self.assertEqual({"입산자실화": 1}, body["cause_breakdown"])
        self.assertIsNotNone(body["false_alarm_rate_pct"])
        self.assertIsNotNone(body["verification_seconds_avg"])
        self.assertIn("golden_time_compliance_pct", body)
        self.assertIn("golden_time_note", body)
        self.assertTrue(any(v for v in body["by_hour"].values()))
        _write_evidence2(
            "FWS-F3-16",
            title="통계 — 발생·면적·원인·시간대·구역·오인율·확인 시간·골든타임 준수율",
            title_parts=[
                {"part": "발생", "where": "응답 occurrence_count",
                "status": "구현 — 2건 이상 실측"},
                {"part": "면적", "where": "응답 area_ha_total(F3-14 최종보고 되짚기)",
                "status": "구현 — 5.5ha 실측"},
                {"part": "원인", "where": "응답 cause_breakdown",
                "status": "구현 — 입산자실화 1건 실측"},
                {"part": "시간대", "where": "응답 by_hour",
                "status": "구현 — 시각별 집계 실측"},
                {"part": "구역", "where": "응답 by_zone",
                "status": "구현 — 카메라 이름별 집계 실측"},
                {"part": "오인율", "where": "응답 false_alarm_rate_pct",
                "status": "구현 — 판정된 2건 중 오인 1건 실측"},
                {"part": "확인 시간", "where": "응답 verification_seconds_avg",
                "status": "구현 — occurred_at→reviewed_at 평균 실측"},
                {"part": "골든타임 준수율 — 대응 시계 실측(신고 접수 → 현장 도착 30분)",
                "where": "office2.py::_golden_time_from_response_clock → "
                         "stream_monitors/services/response_clock.py::stamps_for "
                         "(arrived_at) + F3-06 신고 접수 clock_started_at · 응답 "
                         "golden_time_compliance_pct·golden_time_measured_n·"
                         "golden_time_compliant_n",
                "status": "measured: 세 사건(45분 초과 · 5분 준수 · 발생 50분 전이나 "
                         "신고 10분 전 → 준수)에서 3건 중 2건 = 66.7% — 신고 기준이 "
                         "실제로 읽힘(발생 기준이면 33.3%)"},
                {"part": "골든타임 준수율 — 헬기 물 투하 시각(신고 → 투하 30분)",
                "where": "저장소에 투하 시각 자체가 없다 — F4-04 는 승인 시각"
                         "(approved_at)만 적고, 대응 시계 네 시각에도 투하는 없다",
                "status": "없음 — 명세 §4.3 이 부르는 「헬기 투하」 시각이 저장소에 "
                         "없어 그 기준의 준수율은 재지 못한다(응답 golden_time_note 에 "
                         "명시 · 지어내지 않는다)"},
            ],
            test_ref="tests.test_fws_f3b.F3_16_FireStatsTest.test_stats_covers_all_eight_parts",
            method="GET", path=STATS_FIRES, request_params={}, response=resp,
            what="사건 2건(확정 1 · 오인 1)과 골든타임 사건 3건 뒤 GET stats/fires 가 "
                "발생·면적·원인·시간대·구역·오인율·확인 시간을 내고, 골든타임 준수율을 "
                "대응 시계(신고→도착) 실측으로 낸다 — 헬기 투하 기준은 시각이 없어 열린 행",
            retro="P-421 채움 · 확인한 것 — 턴 AP 차선 N2b · 2026-09-29 · 골든타임을 "
                  "「확인 회신 30분」 근사에서 대응 시계 arrived_at 실측으로 바꾸고, 신고 "
                  "접수 기준이 실제로 읽히는지(66.7% vs 발생 기준 33.3%) 대조했다. 헬기 "
                  "투하 시각은 저장소에 없어 열린 행으로 남긴다 — 앞 판의 excluded_by "
                  "P-428 은 뺐다(코드 결손이지 외부 실연동이 아니다 · TITLE_PARTS §3).")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-17 카메라별 오탐률(안개·소각 …)·임계값 시험(K6·QA-12)
# ═══════════════════════════════════════════════════════════════════════════
class F3_17_CameraFalseAlarmTest(F3BHttpTest):
    def test_rate_and_threshold_test(self) -> None:
        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="warning", event_type="fire")
        dsm_services.review_event(scope=self.scope_a, event_id=event_id,
                                  verdict="rejected", reason="false_alarm [fog_or_cloud] 안개")

        rates = self.client.get(STATS_CAMERA, **head)
        self.assertEqual(200, rates.status_code, rates.content)
        cams = self._body(rates)["cameras"]
        cam = next(c for c in cams if c["stream_monitor_id"] == self.stream_a.pk)
        self.assertEqual(100.0, cam["false_alarm_rate_pct"])
        self.assertEqual({"fog_or_cloud": 1}, cam["reason_breakdown"])

        params = {"stream_monitor_id": self.stream_a.pk, "threshold_pct": 50}
        resp = self.client.post(_qs(CAMERA_THRESHOLD_TEST, **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("fail", body["result"])
        self.assertEqual(100.0, body["computed_false_alarm_rate_pct"])
        _write_evidence2(
            "FWS-F3-17", title="카메라별 오탐률(안개·소각 …)·임계값 시험(K6·QA-12)",
            title_parts=[
                {"part": "카메라별 오탐률", "where": "응답 cameras[].false_alarm_rate_pct",
                "status": "구현 — 100.0 실측(오인 1/판정 1)"},
                {"part": "안개·소각 등 사유", "where": "응답 cameras[].reason_breakdown"
                                              "(verification.FALSE_ALARM_REASONS 재사용)",
                "status": "구현 — fog_or_cloud 1건 실측"},
                {"part": "임계값 시험(완결조건: 저장)", "where": "응답 result·"
                                                           "computed_false_alarm_rate_pct"
                                                           "(감사에 저장)",
                "status": "구현 — 임계값 50 대비 결과 fail 저장 실측"},
            ],
            test_ref="tests.test_fws_f3b.F3_17_CameraFalseAlarmTest.test_rate_and_threshold_test",
            method="POST", path=_qs(CAMERA_THRESHOLD_TEST, **params),
            request_params=params, response=resp,
            what="오인 판정 1건 뒤 카메라별 오탐률 100%·사유(안개) 집계, 임계값 "
                "50% 시험이 fail 로 저장된다 — 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-18 계도·단속 통계 · 입산통제구역 관리
# ═══════════════════════════════════════════════════════════════════════════
class F3_18_PatrolEnforcementTest(F3BHttpTest):
    def _second_tenant_a_user(self):
        """`self.group_a` 소속 두 번째 사람 — 테넌트 전체 집계(곁표 · 턴 AO 차선 O ·
        P-411)를 재려면 "한 사람" 이 아니라 "같은 테넌트 두 사람" 이 있어야 한다.
        `self.role_a`(DsmFixture 가 이미 group_a 에 물린 역할)를 붙인다 — 역할 0
        계정은 `common/role_gate.py`(P-105)가 쓰기 라우트를 통째로 막는다."""
        from django.apps import apps as _apps

        CoreUser = _apps.get_model("user", "CoreUser")
        user = CoreUser.objects.create_user(
            username="f3_18_second", password="test-only-not-a-secret",
            is_active=True, email="f3_18_second@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": self.group_a})
        user.roles.add(self.role_a)
        return user

    def test_record_stats_and_zone_management(self) -> None:
        head = self._bearer(self.user_a)
        head2 = self._bearer(self._second_tenant_a_user())
        params = {"kind": "guidance", "location": "OO등산로 입구",
                 "note": "입산 자제 안내"}
        resp = self.client.post(_qs(PATROL_ENFORCEMENT, **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertIn("record_id", self._body(resp))

        # ★ 턴 AO 차선 O · P-411 — 같은 테넌트의 **다른 사람**이 남긴 기록도
        #   집계에 잡혀야 한다(곁표가 넘어선 "본인만" 한계). 종류를 달리 남겨
        #   "합쳐졌다"를 두 kind 로 함께 실측한다.
        params2 = {"kind": "enforcement", "location": "XX등산로 입구"}
        resp2 = self.client.post(_qs(PATROL_ENFORCEMENT, **params2), **head2)
        self.assertEqual(200, resp2.status_code, resp2.content)

        stats = self.client.get(PATROL_ENFORCEMENT_MINE, **head)
        self.assertEqual(200, stats.status_code)
        stats_body = self._body(stats)
        self.assertEqual(1, stats_body["by_kind"]["guidance"])
        self.assertEqual(1, stats_body["by_kind"]["enforcement"])
        self.assertEqual(2, stats_body["total"],
                         "같은 테넌트 두 사람의 계도·단속 기록이 합쳐지지 않았다")
        self.assertEqual("tenant", stats_body["scope"])

        zone_params = {"zone_name": "OO봉 일대", "status": "active"}
        zone_resp = self.client.post(_qs(ENTRY_ZONES, **zone_params), **head)
        self.assertEqual(200, zone_resp.status_code, zone_resp.content)
        # ★ 다른 사람(head2)이 설정한 구역도 같은 테넌트면 함께 보여야 한다.
        zone_params2 = {"zone_name": "XX능선", "status": "active"}
        zone_resp2 = self.client.post(_qs(ENTRY_ZONES, **zone_params2), **head2)
        self.assertEqual(200, zone_resp2.status_code, zone_resp2.content)

        zones = self.client.get(ENTRY_ZONES, **head)
        self.assertEqual(200, zones.status_code)
        zones_body = self._body(zones)
        self.assertEqual(2, len(zones_body["zones"]),
                         "같은 테넌트 두 사람의 입산통제구역이 합쳐지지 않았다")
        names = {z["zone_name"] for z in zones_body["zones"]}
        self.assertEqual({"OO봉 일대", "XX능선"}, names)
        self.assertTrue(all(z["status"] == "active" for z in zones_body["zones"]))

        # ★ 격리 — 다른 테넌트(user_b)는 이 테넌트의 기록을 하나도 못 본다.
        head_b = self._bearer(self.user_b)
        stats_b = self.client.get(PATROL_ENFORCEMENT_MINE, **head_b)
        self.assertEqual(200, stats_b.status_code)
        self.assertEqual(0, self._body(stats_b)["total"])
        zones_b = self.client.get(ENTRY_ZONES, **head_b)
        self.assertEqual(200, zones_b.status_code)
        self.assertEqual([], self._body(zones_b)["zones"])

        _write_evidence2(
            "FWS-F3-18", title="계도·단속 통계 · 입산통제구역 관리",
            title_parts=[
                {"part": "계도·단속 통계", "where": "응답 by_kind·total"
                                               "(patrol_enforcement_stats)",
                "status": "구현 — guidance 1건 · enforcement 1건(같은 테넌트 "
                         "두 사람) → total=2 실측(곁표 common.models.AuditScope "
                         "가 감사 표의 테넌트 칸 없음을 넘어선다 · 턴 AO 차선 O · "
                         "P-411 · 다른 테넌트는 0건 실측)"},
                {"part": "입산통제구역 관리", "where": "응답 zones[](set_entry_control_"
                                                 "zone·entry_control_zones)",
                "status": "구현 — 같은 테넌트 두 사람이 설정한 구역 2건 모두 조회 "
                         "실측(다른 테넌트는 0건 실측)"},
            ],
            test_ref="tests.test_fws_f3b.F3_18_PatrolEnforcementTest."
                    "test_record_stats_and_zone_management",
            method="GET", path=ENTRY_ZONES, request_params={}, response=zones,
            what="같은 테넌트 두 사람이 계도 1건·단속 1건 · 입산통제구역 2곳을 "
                "나눠 남긴 뒤 GET 이 둘을 합쳐 낸다(total=2 · zones 2건) — 다른 "
                "테넌트는 같은 GET 에서 0건을 받는다(격리) — 실측")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-19 훈련 시나리오 실행(가상 사건 · 실채널 0)
# ═══════════════════════════════════════════════════════════════════════════
class F3_19_DrillScenarioTest(F3BHttpTest):
    def test_start_status_end_real_channel_zero(self) -> None:
        head = self._bearer(self.user_a)
        start = self.client.post(_qs(DRILL_START, reason="분기 정기 훈련"), **head)
        self.assertEqual(200, start.status_code, start.content)
        self.assertTrue(self._body(start)["drill_mode"])

        status = self.client.get(DRILL_STATUS, **head)
        self.assertEqual(200, status.status_code)
        self.assertTrue(self._body(status)["drill_mode"])

        resp = self.client.post(_qs(DRILL_END, reason="훈련 종료"), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertTrue(body["measurable"])
        self.assertEqual(0, body["real_channel_sends"])
        _write_evidence2(
            "FWS-F3-19", title="훈련 시나리오 실행(가상 사건 · 실채널 0)",
            title_parts=[
                {"part": "가상 사건", "where": "요청·응답 drill_mode(DSM 훈련 스위치 "
                                            "재사용 · training.py 와 같은 판단)",
                "status": "구현 — 시작·상태 실측"},
                {"part": "실채널 0(완결조건 · 첫 증거)", "where": "응답 "
                                                          "real_channel_sends",
                "status": "구현 — 0 실측(drill_report 가 잰다)"},
                {"part": "보고서", "where": "응답 전체(drill_report)",
                "status": "구현 — 종료 보고서 실측"},
            ],
            test_ref="tests.test_fws_f3b.F3_19_DrillScenarioTest."
                    "test_start_status_end_real_channel_zero",
            method="POST", path=_qs(DRILL_END, reason="훈련 종료"),
            request_params={"reason": "훈련 종료"}, response=resp,
            what="훈련 시작→상태 확인→종료 보고서에서 real_channel_sends=0 이 "
                "실측된다(훈련이 진짜 발송을 내지 않았다는 증거)")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-20 온보딩 카드 7(조심기간 전)
# ═══════════════════════════════════════════════════════════════════════════
class F3_20_OnboardingCardsTest(F3BHttpTest):
    def test_seven_cards_close_to_100_percent(self) -> None:
        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="warning", event_type="fire")

        self.client.post(_qs(_evac_plan_path(event_id), villages_json=json.dumps(
            [{"village": "동리", "shelter": "동리회관"}], ensure_ascii=False)), **head)
        self.client.post(_qs(_evac_progress_path(event_id), village="동리",
                            completed=True, remaining_residents=0), **head)
        self.client.post(_qs(_hourly_path(event_id), personnel_count=6), **head)
        self.client.post(_qs(_final_path(event_id), cause="기타", area_ha=1.0,
                            sms_sent=False), **head)
        dsm_services.review_event(scope=self.scope_a, event_id=event_id,
                                  verdict="rejected", reason="false_alarm [other] 오인")
        self.client.post(_qs(CAMERA_THRESHOLD_TEST, stream_monitor_id=self.stream_a.pk,
                            threshold_pct=10), **head)
        self.client.post(_qs(PATROL_ENFORCEMENT, kind="guidance"), **head)
        self.client.post(_qs(DRILL_START, reason="온보딩 훈련"), **head)
        self.client.post(_qs(DRILL_END, reason="종료"), **head)

        resp = self.client.get(ONBOARDING, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(7, body["total"])
        self.assertEqual(7, body["done"])
        self.assertEqual(100.0, body["percent"])
        _write_evidence2(
            "FWS-F3-20", title="온보딩 카드 7(조심기간 전)",
            title_parts=[
                {"part": "카드 7", "where": "응답 cards(길이 7 · F3_CARD_KEYS)",
                "status": "구현 — 7장 실측(대피 초안·이행 확인·상황보고·최종보고·"
                         "카메라 임계값·계도단속·훈련)"},
                {"part": "진행률 100(완결조건)", "where": "응답 percent",
                "status": "구현 — 7장 전부 두드린 뒤 100.0 실측"},
            ],
            test_ref="tests.test_fws_f3b.F3_20_OnboardingCardsTest."
                    "test_seven_cards_close_to_100_percent",
            method="GET", path=ONBOARDING, request_params={}, response=resp,
            what="F3 카드 7개에 해당하는 문을 전부 두드린 뒤 GET onboarding/progress "
                "가 done=7·percent=100.0 을 낸다 — 실측")
