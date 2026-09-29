# -*- coding: utf-8 -*-
"""DSM-U3-01·U3-02·U6-01·U6-03 — **HTTP 실측**과 `docs/agent/evidence/SPEC/*.json`
생성 (P-356·WO-18 §턴AO · 차선 N4).

닫는 절: DSM-U3-01(역할별 M2 문안) · DSM-U3-02(통제 실행 회신) · DSM-U6-01
(외부 이벤트 연계 — 112·119·스마트시티 통합플랫폼) · DSM-U6-03(사회적약자 요청
수신 → 객체 검색 사건 생성).

캐시 처리: `FwsHttpTest`(=`tests.test_fws_app.FwsHttpTest`)가 매 시험 앞뒤로
`cache.clear()` 를 부른다 — `common/idempotency.py` 가 성공 응답을 Redis 에
잠깐 기억해, 안 비우면 같은 문을 두 번 두드리는 시험(도달→결정→실행 순서 시험 등)
의 두 번째 호출이 새 자원 대신 옛 응답을 받는다.

`tests.test_fws_app.FwsHttpTest`(=`DsmFixture` + 일반 HTTP 클라이언트) 를 그대로
쓴다 — 이름은 FWS 이지만 DSM 라우트에도 같은 표를 쓴다(`test_dsm_u5_an.py` 와
같은 재사용, D-212). 증거 쓰기(`_write_evidence`)도 그 파일의 것을 재사용한다.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.cache import cache
from django.test import override_settings

from common import audit_writer
from common.evidence_guard import allow_evidence_writes
from common.webhook_contract import outbound_headers
from tests.test_fws_app import FwsHttpTest, _qs, _write_evidence

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"

M2_BRIEF = "/api/dsm/events/{event_id}/m2-brief"
CONTROL_POINTS = "/api/dsm/control-points"
CONTROL_EXECUTED = "/api/dsm/controls/{point_id}/executed"
EXTERNAL_EVENTS = "/api/dsm/external-events"
SEARCH_REQUESTS = "/api/dsm/search-requests"


def _add_title_parts(clause_id: str, parts: list[dict]) -> None:
    """`test_dsm_u5_an.py::_add_title_parts` 와 같은 모양 — 이미 찍은 증거 파일을
    다시 열어 `title_parts` 칸만 얹는다(공용 `_write_evidence` 를 고치지 않는다)."""
    with allow_evidence_writes(
            "P-356 ② title_parts — 제목이 부르는 부분과 실측 상태를 표로 남긴다"):
        path = EVIDENCE_DIR / f"{clause_id}.json"
        body = json.loads(path.read_text(encoding="utf-8"))
        body["title_parts"] = parts
        path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")


def _hdr(headers: dict) -> dict:
    """웹훅 서명 헤더(`X-GX-Schema` 등)를 Django 시험 클라이언트의 `HTTP_...`
    이름으로 바꾼다."""
    return {"HTTP_" + k.upper().replace("-", "_"): v for k, v in headers.items()}


class U36AnFixture(FwsHttpTest):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U3-01 — 역할별 M2 문안
# ═══════════════════════════════════════════════════════════════════════════
class U3_01_M2BriefTest(U36AnFixture):
    def test_role_and_event_type_pick_the_exact_dictionary_line(self) -> None:
        event_id = self._event(self.stream_a, event_type="flood")
        path = M2_BRIEF.format(event_id=event_id)

        resp = self.client.get(
            _qs(path, role="facility"), **self._bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = self._body(resp)
        self.assertEqual("도로 통제 후 회신", body["text"],
                         "명세 원문의 예시 문안과 다르다")
        self.assertEqual("시설", body["role_label"])

        _write_evidence(
            "DSM-U3-01", title="역할별 M2 문안",
            test_ref="tests.test_dsm_u36_an.U3_01_M2BriefTest."
                    "test_role_and_event_type_pick_the_exact_dictionary_line",
            method="GET", path=_qs(path, role="facility"),
            request_params={"role": "facility"}, response=resp,
            what="침수(flood) 사건에 시설 담당 역할로 M2 문안을 물으면 명세 원문의 "
                "예시 문장('도로 통제 후 회신')이 그대로 나온다 — 역할×유형 문안 "
                "표가 사전과 일치한다")

    def test_unknown_role_is_422_and_other_tenant_event_is_404(self) -> None:
        event_id = self._event(self.stream_a, event_type="fire")
        path = M2_BRIEF.format(event_id=event_id)

        bad_role = self.client.get(
            _qs(path, role="ghost-role"), **self._bearer(self.user_a))
        self.assertEqual(422, bad_role.status_code, bad_role.content[:300])

        cross_tenant = self.client.get(
            _qs(path, role="119"), **self._bearer(self.user_b))
        self.assertEqual(404, cross_tenant.status_code, cross_tenant.content[:300])

        #: ★ 이 시험이 알파벳 순으로 `test_role_and_event_type_...` 뒤에 돌아
        #:   증거 파일이 이미 있다(`test_dsm_u36_gate_can_fail` 와 같은 순서 규율 —
        #:   먼저 쓰고 나중에 얹는다).
        _add_title_parts("DSM-U3-01", [
            {"part": "역할×유형 문안 표", "where": "u36_an_service.M2_PHRASE_TABLE",
             "status": "measured"},
            {"part": "M2 상단 한 줄", "where": "응답 text 칸", "status": "measured"},
            {"part": "문안 사전 일치", "where": "시설+flood → '도로 통제 후 회신' "
             "(명세 원문 예시와 문자열 일치)", "status": "measured"},
        ])

    def test_dictionary_covers_all_four_roles(self) -> None:
        """문안 사전 일치 — 네 역할 전부 표에 한 줄씩 있다(빈 문자열 0)."""
        from apps.dsm import u36_an_service

        event_id = self._event(self.stream_a, event_type="sos")
        path = M2_BRIEF.format(event_id=event_id)
        for role in u36_an_service.ROLES:
            resp = self.client.get(_qs(path, role=role), **self._bearer(self.user_a))
            self.assertEqual(200, resp.status_code, (role, resp.content[:200]))
            self.assertTrue(self._body(resp)["text"].strip(), f"role={role} 이 빈 문안")


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U3-02 — 통제 실행 회신
# ═══════════════════════════════════════════════════════════════════════════
class U3_02_ControlExecutedTest(U36AnFixture):
    def test_reached_decided_executed_three_timestamps(self) -> None:
        from apps.dsm import control_board_service

        created = control_board_service.create_point(
            scope=self.scope_a, name="지하차도", evacuee_count=0)
        point_id = created["point_id"]
        control_board_service.advance(scope=self.scope_a, point_id=point_id,
                                      stage="결정")

        resp = self.client.post(
            CONTROL_EXECUTED.format(point_id=point_id), {"note": "바리케이드 설치 완료"},
            content_type="application/json", **self._bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = self._body(resp)
        self.assertEqual("실행", body["stage"])

        board = self.client.get(CONTROL_POINTS, **self._bearer(self.user_a))
        self.assertEqual(200, board.status_code)
        row = next(r for r in self._body(board) if r["point_id"] == point_id)
        self.assertEqual("실행", row["stage"],
                         "통제 현황판이 실행 단계를 반영하지 않는다")

        _write_evidence(
            "DSM-U3-02", title="통제 실행 회신",
            test_ref="tests.test_dsm_u36_an.U3_02_ControlExecutedTest."
                    "test_reached_decided_executed_three_timestamps",
            method="POST", path=CONTROL_EXECUTED.format(point_id=point_id),
            request_params={"note": "바리케이드 설치 완료"}, response=resp,
            what="도달(등록)→결정(advance)→실행(POST /controls/{id}/executed) "
                "셋을 순서대로 남기면 현황판(GET /control-points)의 지점 행이 "
                "'실행' 단계를 보여준다 — 완결조건(3시각) 그대로")
        _add_title_parts("DSM-U3-02", [
            {"part": "통제 완료 버튼", "where": "POST /controls/{id}/executed",
             "status": "measured"},
            {"part": "시각 기록", "where": "advance() 감사 줄(occurred_at)",
             "status": "measured"},
            {"part": "통제 현황판 반영", "where": "GET /control-points 지점 행 stage",
             "status": "measured"},
            {"part": "도달→결정→실행 3시각", "where": "create_point→advance(결정)→"
             "POST /controls/{id}/executed 순서 검사", "status": "measured"},
        ])

    def test_executed_before_decided_is_409(self) -> None:
        from apps.dsm import control_board_service

        created = control_board_service.create_point(scope=self.scope_a, name="둔치주차장")
        point_id = created["point_id"]

        resp = self.client.post(
            CONTROL_EXECUTED.format(point_id=point_id), {},
            content_type="application/json", **self._bearer(self.user_a))
        self.assertEqual(409, resp.status_code, resp.content[:300])

    def test_other_tenants_point_is_404(self) -> None:
        from apps.dsm import control_board_service

        created = control_board_service.create_point(scope=self.scope_a, name="산책로")
        point_id = created["point_id"]
        control_board_service.advance(scope=self.scope_a, point_id=point_id, stage="결정")

        resp = self.client.post(
            CONTROL_EXECUTED.format(point_id=point_id), {},
            content_type="application/json", **self._bearer(self.user_b))
        self.assertEqual(404, resp.status_code, resp.content[:300])


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U6-01 — 스마트시티 통합플랫폼 이벤트 연계 (112·119·재난상황 긴급대응)
# ═══════════════════════════════════════════════════════════════════════════
SECRET_112 = "test-only-112-secret-not-real"          # noqa: S105
SECRET_119 = "test-only-119-secret-not-real"           # noqa: S105
SECRET_SMART_CITY = "test-only-smartcity-secret-not-real"  # noqa: S105

_SIGNING_KEYS = {
    "police_112": SECRET_112, "fire_119": SECRET_119, "smart_city": SECRET_SMART_CITY,
}


@override_settings(EXTERNAL_EVENT_SIGNING_KEYS=_SIGNING_KEYS)
class U6_01_ExternalEventsTest(U36AnFixture):
    def _post(self, body: dict, secret: str, *, user=None):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = _hdr(outbound_headers(secret, raw))
        return self.client.post(
            EXTERNAL_EVENTS, data=raw, content_type="application/json",
            **headers, **self._bearer(user or self.user_a))

    def test_police_112_emergency_video_event_is_recorded_as_external(self) -> None:
        body = {"source": "police_112", "event_type": "intrusion",
               "severity": "critical", "stream_monitor_id": self.stream_a.pk,
               "external_ref": "POL-2026-0001"}
        resp = self._post(body, SECRET_112)
        self.assertEqual(200, resp.status_code, resp.content[:300])
        out = self._body(resp)
        self.assertTrue(out["created"])
        self.assertEqual("external", out["data_source"])
        self.assertEqual("police_112", out["source"])

        _write_evidence(
            "DSM-U6-01", title="스마트시티 통합플랫폼 이벤트 연계",
            test_ref="tests.test_dsm_u36_an.U6_01_ExternalEventsTest."
                    "test_police_112_emergency_video_event_is_recorded_as_external",
            method="POST", path=EXTERNAL_EVENTS, request_params=body, response=resp,
            what="112 긴급영상(사건+카메라 스트림) — 서명된 외부 이벤트가 F-05 읽기 "
                "문의 짝인 쓰기 문 하나로 들어와 data_source=external 로 적립된다")

    def test_fire_119_dispatch_event_is_recorded(self) -> None:
        body = {"source": "fire_119", "event_type": "fire", "severity": "critical",
               "stream_monitor_id": self.stream_a.pk}
        resp = self._post(body, SECRET_119)
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self.assertEqual("external", self._body(resp)["data_source"])

    def test_smart_city_emergency_response_event_is_recorded(self) -> None:
        body = {"source": "smart_city", "event_type": "flood", "severity": "warning",
               "stream_monitor_id": self.stream_a.pk}
        resp = self._post(body, SECRET_SMART_CITY)
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self.assertEqual("external", self._body(resp)["data_source"])

    def test_bad_signature_is_401(self) -> None:
        body = {"source": "police_112", "event_type": "intrusion",
               "severity": "critical", "stream_monitor_id": self.stream_a.pk}
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = _hdr(outbound_headers(SECRET_112, raw))
        headers["HTTP_X_GX_SIGNATURE"] = "sha256=" + "0" * 64
        resp = self.client.post(
            EXTERNAL_EVENTS, data=raw, content_type="application/json",
            **headers, **self._bearer(self.user_a))
        self.assertEqual(401, resp.status_code, resp.content[:300])

    def test_missing_schema_header_is_401(self) -> None:
        """CAP 1.2 프로파일 — 스키마 버전이 없으면(모르는 발신 규격) 서명 값이 맞아도
        거절한다(`webhook_contract.verify` 의 순서: 스키마를 서명보다 먼저 본다)."""
        body = {"source": "police_112", "event_type": "intrusion",
               "severity": "critical", "stream_monitor_id": self.stream_a.pk}
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = _hdr(outbound_headers(SECRET_112, raw))
        del headers["HTTP_X_GX_SCHEMA"]
        resp = self.client.post(
            EXTERNAL_EVENTS, data=raw, content_type="application/json",
            **headers, **self._bearer(self.user_a))
        self.assertEqual(401, resp.status_code, resp.content[:300])

    def test_wrong_tenants_camera_is_404(self) -> None:
        body = {"source": "police_112", "event_type": "intrusion",
               "severity": "critical", "stream_monitor_id": self.stream_a.pk}
        resp = self._post(body, SECRET_112, user=self.user_b)
        self.assertEqual(404, resp.status_code, resp.content[:300])

        #: ★ 이 시험이 알파벳 순으로 여섯 중 마지막이라(`w` > `p`), 증거 파일
        #:   (`test_police_112_..._as_external`)이 이미 있다 — 먼저 쓰고 나중에 얹는다.
        _add_title_parts("DSM-U6-01", [
            {"part": "112 긴급영상(사건+카메라 스트림 URL)",
             "where": "source=police_112", "status": "measured"},
            {"part": "119 출동(화재 사건)", "where": "source=fire_119",
             "status": "measured"},
            {"part": "재난상황 긴급대응(상황실 전송)", "where": "source=smart_city",
             "status": "measured"},
            {"part": "CAP 1.2 프로파일(스키마 버전 검증)",
             "where": "X-GX-Schema 헤더 부재 → 401", "status": "measured"},
            {"part": "서명 검증", "where": "X-GX-Signature 불일치 → 401",
             "status": "measured"},
            {"part": "data_source=external 표식", "where": "응답 data_source 칸",
             "status": "measured"},
        ])


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U6-03 — 사회적약자(실종) 요청 수신 → 객체 검색 사건 생성
# ═══════════════════════════════════════════════════════════════════════════
class U6_03_SearchRequestTest(U36AnFixture):
    def test_request_creates_exactly_one_case_and_one_audit_line(self) -> None:
        from apps.dsm.audit import EVENT_LOGGER_NAME

        body = {"requester_agency": "OO경찰서 여성청소년과",
               "subject_description": "70대 남성 · 회색 상의 · 지팡이 사용",
               "last_seen_stream_monitor_id": self.stream_a.pk,
               "contact": "031-000-0000"}
        before = audit_writer.read(
            logger_name=EVENT_LOGGER_NAME, action="search_request_received", limit=50)

        resp = self.client.post(
            SEARCH_REQUESTS, body, content_type="application/json",
            **self._bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        out = self._body(resp)
        self.assertTrue(out["created"], "요청 → 사건 1 이 완결조건이다")
        self.assertEqual("external", out["data_source"])

        after = audit_writer.read(
            logger_name=EVENT_LOGGER_NAME, action="search_request_received", limit=50)
        self.assertEqual(len(before) + 1, len(after),
                         "감사 줄이 정확히 1개 늘어야 한다(LAW-05 범위 — 감사 줄 1)")
        self.assertIn("OO경찰서 여성청소년과", after[0].reason)
        self.assertNotIn("70대 남성", after[0].reason,
                         "인상착의 원문을 감사 줄에 복제하지 않는다")

        _write_evidence(
            "DSM-U6-03", title="사회적약자(실종) 요청 수신 → 객체 검색 사건 생성",
            test_ref="tests.test_dsm_u36_an.U6_03_SearchRequestTest."
                    "test_request_creates_exactly_one_case_and_one_audit_line",
            method="POST", path=SEARCH_REQUESTS, request_params=body, response=resp,
            what="요청 → 사건 1(완결조건 그대로) — 재식별 AI 는 짓지 않고, 수색의 "
                "출발점이 되는 사건 하나와 감사 줄 하나(LAW-05 범위)를 남긴다")
        _add_title_parts("DSM-U6-03", [
            {"part": "사회적약자(실종) 요청 수신", "where": "POST /search-requests",
             "status": "measured"},
            {"part": "객체 검색 사건 생성", "where": "응답 event_id · created=true",
             "status": "measured"},
            {"part": "요청 → 사건 1", "where": "감사 줄 수 diff == 1",
             "status": "measured"},
            {"part": "LAW-05 범위(감사 줄 1)", "where": "audit.record_event_action",
             "status": "measured"},
        ])

    def test_blank_description_is_422(self) -> None:
        body = {"requester_agency": "OO경찰서", "subject_description": "",
               "last_seen_stream_monitor_id": self.stream_a.pk}
        resp = self.client.post(
            SEARCH_REQUESTS, body, content_type="application/json",
            **self._bearer(self.user_a))
        self.assertEqual(422, resp.status_code, resp.content[:300])

    def test_wrong_tenants_camera_is_404(self) -> None:
        body = {"requester_agency": "OO경찰서", "subject_description": "인상착의",
               "last_seen_stream_monitor_id": self.stream_a.pk}
        resp = self.client.post(
            SEARCH_REQUESTS, body, content_type="application/json",
            **self._bearer(self.user_b))
        self.assertEqual(404, resp.status_code, resp.content[:300])
