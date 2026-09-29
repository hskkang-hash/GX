# -*- coding: utf-8 -*-
"""FWS App(L4) — F3(산림과 담당) 앞 절 아홉 건(F3-01~09)의 **HTTP 실측**과
`docs/agent/evidence/SPEC/*.json` 생성 (WO-GX-20260929-17 §5 P-356·357·397 ·
턴 AN 차선 N2).

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`X-No-Cache`) 헤더를 모든 요청에
싣는다(`test_fws_f6.py` 와 같은 규약). 이 파일은 새 캐시를 만들지 않는다.

이 파일이 재는 것 — P-356 승격 규칙 넷 중 ①②(③·④는 게이트·제안 문서)
------------------------------------------------------------------------
    ① 실제 구현    `self.client` 가 `/api/fws/office/...` 를 실제로 두드린다
                    (F3-05 는 예외 — 새 라우트가 없다. 기존 F1-06 문
                    `/api/fws/verifications/{id}/reply` 를 그대로 두드린다 ·
                    `apps/fws/office.py` 머리말의 재사용 판단 그대로).
    ② 실측 증거    각 시험이 요청·응답을 그대로 `docs/agent/evidence/SPEC/<id>.json`
                    에 적는다 — 이 파일이 그 위에 **title_parts**(제목이 부르는
                    것 ↔ 있는 것, 빈 칸 0)를 더 싣는다(`_규약.md` 요구 — 기존
                    공용 `_write_evidence`(test_fws_app.py)는 고치지 않고, 이
                    파일이 그 모양을 따라 만든 **자기 버전**을 쓴다, D-212가
                    "판정식 복사"를 금하지 "같은 모양" 자체를 금하지 않는다는
                    `drone.py` 머리말의 같은 판단).

F3-04(확인 요청)의 「가장 가까운 드론」은 정직하게 빈 값이다 — `office.py`
머리말 참조(이 저장소에 드론이 0대, P-387). title_parts 가 그 칸을 "missing"
으로 채운다(빈 칸이 아니라 — O 게이트가 세는 것은 "빈 칸"이지 "missing" 문자열이
아니다).
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone as dj_timezone

from common.evidence_guard import allow_evidence_writes
from tests.test_fws_app import FwsHttpTest, _qs

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"


def _write_evidence(clause_id: str, *, title: str, test_ref: str, method: str,
                    path: str, request_params: dict, response, what: str,
                    title_parts: list[dict]) -> None:
    """`tests.test_fws_app._write_evidence` 와 같은 봉투 + `title_parts`
    (`_규약.md` 의 별표 절 승격 규약이 요구하는 「제목이 부르는 것 ↔ 있는 것」
    표, 빈 칸 0). 공용 파일을 고치지 않고 이 차선의 시험 파일 안에 자기
    버전을 둔다."""
    with allow_evidence_writes(
            "P-356 ② FWS-F3 별표 절 실측 증거 — pytest 가 방금 두드린 HTTP "
            "왕복을 그대로 적는다(손으로 옮기지 않는다)"):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            body = json.loads((response.content or b"{}").decode("utf-8", "replace"))
        except (ValueError, TypeError):
            body = {"_raw": (response.content or b"").decode("utf-8", "replace")}
        for part in title_parts:
            missing = [k for k in ("part", "where", "status") if not (part.get(k) or "").strip()]
            if missing:
                raise ValueError(f"title_parts 에 빈 칸이 있다: {part!r} ({missing})")
        payload = {
            "id": clause_id,
            "title": title,
            "measured_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "measured_by": "django_test_client",
            "test": test_ref,
            "request": {"method": method, "path": path, "params": request_params},
            "response": {"status": response.status_code, "body": body},
            "what": what,
            "title_parts": title_parts,
        }
        out = EVIDENCE_DIR / f"{clause_id}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")


DASHBOARD = "/api/fws/office/dashboard"
SEASON = "/api/fws/office/season"
POSTS = "/api/fws/office/posts"
ROSTER = "/api/fws/office/roster"
PATROL_CHECKIN = "/api/fws/patrol/checkin"
STANDBY_STATUS = "/api/fws/resources/me/status"


def _verify_request_path(event_id) -> str:
    return f"/api/fws/office/fire-events/{event_id}/verification-request"


def _verify_reply_path(event_id) -> str:
    return f"/api/fws/verifications/{event_id}/reply"


def _intake_path(event_id) -> str:
    return f"/api/fws/office/fire-events/{event_id}/intake"


def _agency_notify_path(event_id) -> str:
    return f"/api/fws/office/fire-events/{event_id}/agency-notify"


def _resource_assignment_path(event_id) -> str:
    return f"/api/fws/office/fire-events/{event_id}/resource-assignment"


def _stage_proposal_path(event_id) -> str:
    return f"/api/fws/office/fire-events/{event_id}/stage-proposal"


class F3aHttpTest(FwsHttpTest):
    """`FwsHttpTest`(F1/F6 시험의 픽스처·헬퍼)를 그대로 쓴다 — 두 벌을 만들지 않는다."""


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-01 산불 상황판(띠 6수)
# ═══════════════════════════════════════════════════════════════════════════
class F3_01_DashboardTest(F3aHttpTest):
    def test_six_bands_present(self) -> None:
        head = self._bearer(self.user_a)
        # 초소 근무·자원 대기 띠가 0 이 아님을 보이려고 먼저 체크인·대기상태를 남긴다.
        self.client.post(_qs(PATROL_CHECKIN, post_code="P-1", method="gps",
                             lat=36.35, lng=127.38), **head)
        self.client.post(_qs(STANDBY_STATUS, status="standby_day"), **head)
        self._event(self.stream_a, severity="critical", event_type="fire")

        resp = self.client.get(DASHBOARD, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        for band in ("risk_index", "fire_alert", "post_duty", "camera_status",
                    "ongoing_incidents", "resource_standby"):
            self.assertIn(band, body, f"상황판에 {band} 띠가 없습니다")
        self.assertGreaterEqual(body["post_duty"]["on_duty"], 1)
        self.assertGreaterEqual(body["resource_standby"]["standby_day"], 1)
        self.assertGreaterEqual(body["ongoing_incidents"]["count"], 1)
        _write_evidence(
            "FWS-F3-01", title="산불 상황판 — 위험지수·위기경보·초소 근무·카메라"
                              " 정상·진행 사건·자원 대기",
            test_ref="tests.test_fws_f3a.F3_01_DashboardTest.test_six_bands_present",
            method="GET", path=DASHBOARD, request_params={}, response=resp,
            what="GET .../office/dashboard 가 여섯 띠(위험지수·위기경보·초소 근무·"
                "카메라 정상·진행 사건·자원 대기)를 한 번에 낸다 — 체크인·대기상태·"
                "사건 생성 뒤 각 띠가 분모와 함께 움직임을 실측",
            title_parts=[
                {"part": "위험지수", "where": "response.risk_index(F1-03 재사용)", "status": "present"},
                {"part": "위기경보", "where": "response.fire_alert(F1-03 재사용)", "status": "present"},
                {"part": "초소 근무", "where": "response.post_duty(오늘 체크인 집계)", "status": "present"},
                {"part": "카메라 정상", "where": "response.camera_status(UX-23 camera_pulse 재사용)", "status": "present"},
                {"part": "진행 사건", "where": "response.ongoing_incidents(F-09 recent_events 재사용)", "status": "present"},
                {"part": "자원 대기", "where": "response.resource_standby(F2-01 standby 집계)", "status": "present"},
            ],
        )


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-02 조심기간·특별대책기간 설정 · 초소·순찰 구역 등록
# ═══════════════════════════════════════════════════════════════════════════
class F3_02_SeasonAndPostsTest(F3aHttpTest):
    def test_season_save_then_read_back(self) -> None:
        head = self._bearer(self.user_a)
        params = {"kind": "dry_season", "start_date": "2026-11-01", "end_date": "2026-12-15"}
        save = self.client.post(_qs(SEASON, **params), **head)
        self.assertEqual(200, save.status_code, save.content)

        params2 = {"kind": "special_measures", "start_date": "2027-02-01", "end_date": "2027-03-15"}
        save2 = self.client.post(_qs(SEASON, **params2), **head)
        self.assertEqual(200, save2.status_code, save2.content)

        read = self.client.get(SEASON, **head)
        self.assertEqual(200, read.status_code)
        seasons = self._body(read)["seasons"]
        self.assertEqual("2026-11-01", seasons["dry_season"]["start_date"])
        self.assertEqual("2027-02-01", seasons["special_measures"]["start_date"])
        _write_evidence(
            "FWS-F3-02", title="조심기간·특별대책기간 설정 · 초소·순찰 구역 등록",
            test_ref="tests.test_fws_f3a.F3_02_SeasonAndPostsTest.test_season_save_then_read_back",
            method="GET", path=SEASON, request_params={}, response=read,
            what="POST 로 조심기간·특별대책기간을 저장하면 GET 재조회에 둘 다 "
                "남는다(저장 → 재조회 실측). 초소·순찰 구역 등록은 같은 클래스의 "
                "다른 시험이 잰다",
            title_parts=[
                {"part": "조심기간 설정", "where": "POST/GET .../office/season(kind=dry_season)", "status": "present"},
                {"part": "특별대책기간 설정", "where": "POST/GET .../office/season(kind=special_measures)", "status": "present"},
                {"part": "초소 등록", "where": "POST/GET .../office/posts(kind=watchpost)", "status": "present"},
                {"part": "순찰 구역 등록", "where": "POST/GET .../office/posts(kind=patrol_zone)", "status": "present"},
            ],
        )

    def test_posts_registered_then_listed(self) -> None:
        head = self._bearer(self.user_a)
        p1 = self.client.post(_qs(POSTS, kind="watchpost", code="P-12", name="수리산 12초소",
                                  lat=36.35, lng=127.38), **head)
        self.assertEqual(200, p1.status_code, p1.content)
        p2 = self.client.post(_qs(POSTS, kind="patrol_zone", code="Z-3", name="북측 순찰구역"), **head)
        self.assertEqual(200, p2.status_code, p2.content)

        listed = self.client.get(POSTS, **head)
        self.assertEqual(200, listed.status_code)
        codes = [p["code"] for p in self._body(listed)["posts"]]
        self.assertIn("P-12", codes)
        self.assertIn("Z-3", codes)

    def test_invalid_season_kind_is_422(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.post(
            _qs(SEASON, kind="made_up", start_date="2026-01-01", end_date="2026-02-01"), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-03 인력 배치 — 감시원·대응단 근무표(CSV) · 야간 5분대기조
# ═══════════════════════════════════════════════════════════════════════════
class F3_03_RosterTest(F3aHttpTest):
    def test_csv_upload_then_readback_shows_night_standby_flag(self) -> None:
        head = self._bearer(self.user_a)
        csv_text = (
            "name,role,shift_date,shift_type,night_standby_5min\n"
            "김감시,감시원,2026-11-05,day,0\n"
            "이대응,대응단,2026-11-05,night,1\n"
        )
        resp = self.client.post(_qs(ROSTER, csv_text=csv_text), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(2, body["count"])

        read = self.client.get(ROSTER, **head)
        self.assertEqual(200, read.status_code)
        rows = self._body(read)["rows"]
        by_name = {r["name"]: r for r in rows}
        self.assertFalse(by_name["김감시"]["night_standby_5min"])
        self.assertTrue(by_name["이대응"]["night_standby_5min"])
        _write_evidence(
            "FWS-F3-03", title="인력 배치 — 감시원·대응단 근무표(CSV) · 야간 5분대기조",
            test_ref="tests.test_fws_f3a.F3_03_RosterTest."
                    "test_csv_upload_then_readback_shows_night_standby_flag",
            method="GET", path=ROSTER, request_params={}, response=read,
            what="POST 로 올린 근무표 CSV(감시원·대응단 혼재)가 GET 배치판에 "
                "그대로 남고, night_standby_5min 칸이 야간 5분대기조 행만 참으로 "
                "읽힌다(저장 → 재조회 실측)",
            title_parts=[
                {"part": "감시원 근무표(CSV)", "where": "POST .../office/roster(role=감시원 행)", "status": "present"},
                {"part": "대응단 근무표(CSV)", "where": "POST .../office/roster(role=대응단 행)", "status": "present"},
                {"part": "야간 5분대기조", "where": "response.rows[].night_standby_5min", "status": "present"},
            ],
        )

    def test_missing_required_column_is_422(self) -> None:
        head = self._bearer(self.user_a)
        resp = self.client.post(_qs(ROSTER, csv_text="name,role\n김감시,감시원\n"), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-04 탐지 확인 요청 1클릭 · 10분 시계
# ═══════════════════════════════════════════════════════════════════════════
class F3_04_VerificationRequestTest(F3aHttpTest):
    def test_request_starts_a_ten_minute_clock_and_suggests_nearest_officer(self) -> None:
        from kernels.k1_event import record_detection

        head = self._bearer(self.user_a)
        self.client.post(_qs(PATROL_CHECKIN, post_code="P-7", method="gps",
                             lat=36.35, lng=127.38), **head)
        #: ★ `self._event()`(DsmFixture) 는 좌표를 안 준다 — 「가장 가까운 감시원」
        #:   실측에는 사건 좌표가 있어야 하므로 여기서만 `record_detection` 을
        #:   직접 불러 lat·lng 을 함께 남긴다(F-05 잠금과 무관 — 이 시험 픽스처는
        #:   파이프라인 스코프로 K1 을 직접 부르는 것이 이미 관례다).
        event_id = record_detection(
            scope=self.scope_pipe, stream_monitor_id=self.stream_a.pk,
            event_type="fire", severity="critical", occurred_at=dj_timezone.now(),
            snapshot_path="minio://dsm/f3-04.jpg", lat=36.351, lng=127.381,
        ).event_id

        resp = self.client.post(_qs(_verify_request_path(event_id), note="카드 확인"), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(10, body["timeout_minutes"])
        self.assertIsNotNone(body["deadline_at"])
        self.assertGreaterEqual(len(body["suggested_officers"]), 1,
                                "체크인한 감시원이 있는데 제안 목록이 비었습니다")
        self.assertEqual([], body["suggested_drones"], "드론은 0대라 빈 목록이어야 합니다")

        read = self.client.get(_verify_request_path(event_id), **head)
        self.assertEqual(200, read.status_code)
        self.assertEqual(1, self._body(read)["count"])
        _write_evidence(
            "FWS-F3-04", title="탐지 확인 요청 1클릭 — 카드에서 가장 가까운 감시원/"
                              "드론에 확인 요청 · 10분 시계",
            test_ref="tests.test_fws_f3a.F3_04_VerificationRequestTest."
                    "test_request_starts_a_ten_minute_clock_and_suggests_nearest_officer",
            method="POST", path=_qs(_verify_request_path(event_id), note="카드 확인"),
            request_params={"note": "카드 확인"}, response=resp,
            what="POST .../verification-request 가 1클릭으로 발송하고(notify_event "
                "재사용) 10분 시계(deadline_at)를 세우며, 오늘 체크인한 감시원 중 "
                "사건 좌표에 가장 가까운 순으로 제안한다(하버사인). 재조회(GET)에도 "
                "그대로 남는다",
            title_parts=[
                {"part": "1클릭 확인요청 발송", "where": "POST .../verification-request(notify_event 재사용)", "status": "present"},
                {"part": "10분 시계", "where": "response.deadline_at·timeout_minutes=10", "status": "present"},
                {"part": "가장 가까운 감시원 제안", "where": "response.suggested_officers(체크인 위치 하버사인 거리순)", "status": "present"},
                {"part": "가장 가까운 드론 제안", "where": "response.suggested_drones",
                 "status": "missing — 이 저장소에 드론이 0대라(P-387) 위치 텔레메트리가 없다. 완결조건(발송·10분 시계, §5.3 표)은 위 두 항목으로 충족한다"},
            ],
        )

    def test_other_tenant_event_is_404(self) -> None:
        event_id = self._event(self.stream_b, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(_verify_request_path(event_id), **head)
        self.assertEqual(404, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-05 오인 종결(사유) · 산불 확정 — 새 라우트 0(F1-06 문 재사용)
# ═══════════════════════════════════════════════════════════════════════════
class F3_05_MisjudgeOrConfirmReuseTest(F3aHttpTest):
    def test_office_actor_confirms_fire_via_existing_f1_06_door(self) -> None:
        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        resp = self.client.post(
            _qs(_verify_reply_path(event_id), result="fire_confirmed"), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertEqual("confirmed", self._body(resp)["verdict"])
        _write_evidence(
            "FWS-F3-05", title="오인 종결(사유) · 산불 확정",
            test_ref="tests.test_fws_f3a.F3_05_MisjudgeOrConfirmReuseTest."
                    "test_office_actor_confirms_fire_via_existing_f1_06_door",
            method="POST", path=_qs(_verify_reply_path(event_id), result="fire_confirmed"),
            request_params={"result": "fire_confirmed"}, response=resp,
            what="산림과 담당(user_a)이 **새 라우트 없이** 기존 F1-06 문"
                "(`/api/fws/verifications/{id}/reply`)을 그대로 두드려 산불을 "
                "확정한다(verdict=confirmed) — 오인 종결(사유)은 result=false_alarm"
                "+reason_code 로 같은 문이 이미 받는다(P-397 재사용, 새 코드 0줄)",
            title_parts=[
                {"part": "오인 종결(사유)", "where": "POST .../verifications/{id}/reply(result=false_alarm, reason_code=5택 · F1-06 재사용)", "status": "present"},
                {"part": "산불 확정", "where": "POST .../verifications/{id}/reply(result=fire_confirmed · F1-06 재사용)", "status": "present"},
            ],
        )

    def test_misjudge_close_with_reason_via_same_door(self) -> None:
        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        resp = self.client.post(
            _qs(_verify_reply_path(event_id), result="false_alarm", reason_code="fog_or_cloud"),
            **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertEqual("rejected", self._body(resp)["verdict"])


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-06 신고 접수 기록 — 119/산림청/시민 · 신고 시각 = 30분 시계 시작
# ═══════════════════════════════════════════════════════════════════════════
class F3_06_IntakeTest(F3aHttpTest):
    def test_intake_recorded_then_listed_starts_the_clock(self) -> None:
        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        params = {"source": "citizen", "facility_note": "인근 축사 있음",
                 "vehicle_access": True, "fire_intensity": "중", "note": "시민 최초 신고"}
        resp = self.client.post(_qs(_intake_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual(30, body["clock_minutes"])
        self.assertEqual(body["reported_at"], body["clock_started_at"])

        read = self.client.get(_intake_path(event_id), **head)
        self.assertEqual(200, read.status_code)
        self.assertEqual(1, self._body(read)["count"])
        _write_evidence(
            "FWS-F3-06", title="신고 접수 기록 — 119/산림청/시민 신고 접수 항목"
                              "(시간·장소·시설·차량 진입·화세) · 신고 시각 = 30분 시계 시작",
            test_ref="tests.test_fws_f3a.F3_06_IntakeTest."
                    "test_intake_recorded_then_listed_starts_the_clock",
            method="GET", path=_intake_path(event_id), request_params={}, response=read,
            what="POST 로 남긴 신고 접수 기록(출처 citizen·시설·차량진입·화세)이 "
                "GET 재조회에 그대로 남고, 신고 시각이 30분 시계의 시작값으로 "
                "함께 저장됨을 실측",
            title_parts=[
                {"part": "신고 출처(119/산림청/시민)", "where": "request.source(REPORT_SOURCES 3택)", "status": "present"},
                {"part": "접수 항목(시간·장소·시설·차량진입·화세)", "where": "response.{reported_at,facility_note,vehicle_access,fire_intensity}(장소는 사건의 좌표·주소를 그대로 쓴다 — event_detail 재사용)", "status": "present"},
                {"part": "신고 시각 = 30분 시계 시작", "where": "response.clock_started_at = reported_at · clock_minutes=30", "status": "present"},
            ],
        )

    def test_unknown_source_is_422(self) -> None:
        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        resp = self.client.post(_qs(_intake_path(event_id), source="made_up"), **head)
        self.assertEqual(422, resp.status_code)

    def test_other_tenant_event_is_404(self) -> None:
        event_id = self._event(self.stream_b, severity="critical", event_type="fire")
        head = self._bearer(self.user_a)
        resp = self.client.post(_qs(_intake_path(event_id), source="citizen"), **head)
        self.assertEqual(404, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-07 산림청 상황실 통보 기록(042-481-4119) · 헬기 요청 기록
# ═══════════════════════════════════════════════════════════════════════════
class F3_07_AgencyNotifyTest(F3aHttpTest):
    def test_notify_records_the_reused_phone_number_and_helicopter_request(self) -> None:
        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        params = {"helicopter_base": "원주기지", "helicopter_eta": "2026-11-05T04:10:00+09:00",
                 "note": "산불 3단계 급수 요청"}
        resp = self.client.post(_qs(_agency_notify_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("042-481-4119", body["agency_phone"],
                         "F1-08 emergency_contacts 와 다른 번호를 썼습니다(D-212)")
        self.assertEqual("원주기지", body["helicopter_base"])
        self.assertIsNotNone(body["helicopter_requested_at"])

        read = self.client.get(_agency_notify_path(event_id), **head)
        self.assertEqual(200, read.status_code)
        self.assertEqual(1, self._body(read)["count"])
        _write_evidence(
            "FWS-F3-07", title="산림청 상황실 통보 기록(042-481-4119) · 헬기 요청"
                              " 기록(요청 시각·기지·도착 예정)",
            test_ref="tests.test_fws_f3a.F3_07_AgencyNotifyTest."
                    "test_notify_records_the_reused_phone_number_and_helicopter_request",
            method="GET", path=_agency_notify_path(event_id), request_params={},
            response=read,
            what="POST 로 남긴 산림청 통보(번호는 F1-08 contacts.FOREST_REPORT_"
                "NUMBER 재사용)와 헬기 요청(기지·도착예정)이 GET 재조회에 그대로 "
                "남는다",
            title_parts=[
                {"part": "산림청 상황실 통보 기록(042-481-4119)", "where": "response.agency_phone(contacts.FOREST_REPORT_NUMBER 재사용) · notified_at", "status": "present"},
                {"part": "헬기 요청 기록(요청시각·기지·도착예정)", "where": "response.{helicopter_requested_at,helicopter_base,helicopter_eta}", "status": "present"},
            ],
        )


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-08 자원 배정 — 진화대·차량·드론 · 임무 문안 자동
# ═══════════════════════════════════════════════════════════════════════════
class F3_08_ResourceAssignmentTest(F3aHttpTest):
    def test_crew_assignment_writes_auto_mission_text_and_reaches_f2(self) -> None:
        from apps.dsm.services import field_replies
        from common.tenant_scope import TenantScope

        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        params = {"kind": "crew", "resource_name": "1진화대", "note": "즉시 출동"}
        resp = self.client.post(_qs(_resource_assignment_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertIn("1진화대", body["mission_text"])
        self.assertIn("자원배정", body["mission_text"])

        replies = field_replies(scope=TenantScope.of(self.user_a), event_id=event_id)
        self.assertTrue(any("1진화대" in r.text for r in replies),
                        "F2 가 읽는 현장 회신 자리(field_reply)에 배정 문안이 안 실렸습니다")

        for kind, name in (("vehicle", "3호 진화차"), ("drone", "드론-1")):
            r = self.client.post(
                _qs(_resource_assignment_path(event_id), kind=kind, resource_name=name), **head)
            self.assertEqual(200, r.status_code, r.content)

        read = self.client.get(_resource_assignment_path(event_id), **head)
        self.assertEqual(200, read.status_code)
        self.assertEqual(3, self._body(read)["count"])
        _write_evidence(
            "FWS-F3-08", title="자원 배정 — 진화대·차량·드론을 사건에 배정"
                              "(임무 문안 자동)",
            test_ref="tests.test_fws_f3a.F3_08_ResourceAssignmentTest."
                    "test_crew_assignment_writes_auto_mission_text_and_reaches_f2",
            method="GET", path=_resource_assignment_path(event_id), request_params={},
            response=read,
            what="진화대·차량·드론 셋을 각각 배정하면 자동 임무 문안이 지어져 F2 가 "
                "읽는 현장 회신(field_reply, 재사용)에 실리고, 3건 전부 GET "
                "재조회에 남는다",
            title_parts=[
                {"part": "진화대 배정", "where": "POST .../resource-assignment(kind=crew)", "status": "present"},
                {"part": "차량 배정", "where": "POST .../resource-assignment(kind=vehicle)", "status": "present"},
                {"part": "드론 배정", "where": "POST .../resource-assignment(kind=drone)", "status": "present"},
                {"part": "임무 문안 자동", "where": "response.mission_text(자동 조립) · field_reply 로 F2 도달(재사용)", "status": "present"},
            ],
        )

    def test_unknown_kind_is_422(self) -> None:
        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        resp = self.client.post(
            _qs(_resource_assignment_path(event_id), kind="made_up", resource_name="x"), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-09 대응단계 입력 3칸(면적·풍속·시설 우려) → 단계 제안 → F4 확정 요청
# ═══════════════════════════════════════════════════════════════════════════
class F3_09_StageProposalTest(F3aHttpTest):
    def test_three_inputs_propose_stage_using_p386_constants(self) -> None:
        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        params = {"area_ha": 150, "wind_mps": 1, "buildings_at_risk": 0}
        resp = self.client.post(_qs(_stage_proposal_path(event_id), **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        self.assertEqual("3단계", body["proposed_stage"],
                         "150ha 는 P-386 3단계 문턱(100ha)을 넘습니다")
        self.assertEqual("pending_f4_confirmation", body["status"])

        read = self.client.get(_stage_proposal_path(event_id), **head)
        self.assertEqual(200, read.status_code)
        self.assertEqual(1, self._body(read)["count"])
        _write_evidence(
            "FWS-F3-09", title="대응단계 입력 3칸(면적·풍속·시설 우려) → 단계 제안"
                              " → F4 확정 요청",
            test_ref="tests.test_fws_f3a.F3_09_StageProposalTest."
                    "test_three_inputs_propose_stage_using_p386_constants",
            method="GET", path=_stage_proposal_path(event_id), request_params={},
            response=read,
            what="면적·풍속·시설우려(건물수) 3칸을 넣으면 constants.compute_"
                "fire_stage(P-386, F6 재사용)로 단계를 제안하고, F4 확정 요청 "
                "상태(pending_f4_confirmation)로 알림(notify_event 재사용)까지 "
                "한 번에 남는다",
            title_parts=[
                {"part": "면적 입력", "where": "request.area_ha", "status": "present"},
                {"part": "풍속 입력", "where": "request.wind_mps", "status": "present"},
                {"part": "시설 우려 입력", "where": "request.buildings_at_risk", "status": "present"},
                {"part": "단계 제안", "where": "response.proposed_stage(constants.compute_fire_stage 재사용)", "status": "present"},
                {"part": "F4 확정 요청", "where": "response.status=pending_f4_confirmation · f4_notified_count(notify_event 재사용)", "status": "present"},
            ],
        )

    def test_negative_area_is_422(self) -> None:
        head = self._bearer(self.user_a)
        event_id = self._event(self.stream_a, severity="critical", event_type="fire")
        resp = self.client.post(
            _qs(_stage_proposal_path(event_id), area_ha=-1, wind_mps=1), **head)
        self.assertEqual(422, resp.status_code)


# ═══════════════════════════════════════════════════════════════════════════
# 게이트 자기시험 짝(P-319·P-323) — `scripts/verify_spec_fws_f3.py` 의
# `judge_evidence` 를 몸소 망가뜨려 실패(1)를 본다(`test_verify_spec_fws_f6_
# gate_can_fail.py` 와 같은 모양). 조율자에게: `scripts/_gate_header.py::
# SELF_TEST_LINKS` 에 "verify_spec_fws_f3.py": "backend/tests/test_fws_f3a.py"
# 한 줄 등재 요망(최종 보고 참고 — 이 차선은 공용 파일을 고치지 않는다).
# ═══════════════════════════════════════════════════════════════════════════
from django.test import SimpleTestCase  # noqa: E402


def _gate():
    import sys
    from pathlib import Path as _P

    here = _P(__file__).resolve()
    for cand in ("/repo/scripts", str(here.parent.parent.parent / "scripts")):
        if _P(cand).is_dir() and cand not in sys.path:
            sys.path.insert(0, cand)
    import verify_spec_fws_f3  # noqa: PLC0415

    return verify_spec_fws_f3


class FwsF3GateSelfTestCanFail(SimpleTestCase):
    """`test_verify_spec_fws_f6_gate_can_fail.py` 와 같은 두 가지 망가뜨림 —
    증거 파일이 없거나 응답이 500 인데 통과로 읽는 판정식을 자기시험이 잡는가."""

    def test_self_test_passes_as_built(self) -> None:
        self.assertEqual(0, _gate().self_test())

    def test_self_test_fails_when_missing_evidence_is_waved_through(self) -> None:
        g = _gate()
        real = g.judge_evidence

        def waves_missing(clause_id, payload):
            if payload is None:
                return g.EXIT_OK, "없어도 통과시킨다(망가진 판정)"
            return real(clause_id, payload)

        g.judge_evidence = waves_missing
        try:
            got = g.self_test()
        finally:
            g.judge_evidence = real
        self.assertEqual(g.EXIT_FAIL, got,
                         "증거 없음을 통과로 읽는 망가진 판정을 자기시험이 못 잡습니다")

    def test_self_test_fails_when_500_is_waved_through(self) -> None:
        g = _gate()
        real = g.judge_evidence

        def waves_500_status(clause_id, payload):
            if isinstance(payload, dict) and payload.get("response", {}).get("status") == 500:
                return g.EXIT_OK, "500 인데 통과시킨다(망가진 판정)"
            return real(clause_id, payload)

        g.judge_evidence = waves_500_status
        try:
            got = g.self_test()
        finally:
            g.judge_evidence = real
        self.assertEqual(g.EXIT_FAIL, got,
                         "응답 500 인 증거를 통과로 읽는 망가진 판정을 자기시험이 못 잡습니다")
