# -*- coding: utf-8 -*-
"""P-421 ② · WO-GX-20261001-19 §4(N3) · §5(P-421) — **DSM-U5-05 반쪽 채움**
(턴 AP · 차선 N3).

이 파일이 닫는 것
------------------
`docs/agent/evidence/SPEC/DSM-U5-05.json` 의 title_parts 두 열린 행:

  ① 「일지 근무자 자동」 — 관제일지(DSM-U1-04)라는 새 저장처를 만들지 않고
     (지시서 「새 표 0」), 이미 공개된 두 면을 한 응답으로 묶는다:
     `handover_service.build_draft()`(인계 메모)와 `apps.dsm.services
     .recent_events`/`response_clock`(사건 타임라인, UX-14 가 이미 연 면).
     새 함수는 `handover_service.control_log()` 하나, 새 문은
     `GET /api/dsm/u5an/control-log` 하나뿐이다.
  ② 「완결조건 일지 근무자 = 편성표」 — `control_log()['on_duty']` 는
     `build_draft().on_duty` 를 그대로 옮긴 것이고, 그것은
     `shift_roster_service.current_workers()` 를 그대로 옮긴 것이다 — 이
     시험은 **세 자리가 같은 값**임을 실제로 HTTP 로 대조한다(대리 지표 0).

이 파일이 안 하는 것
--------------------
`docs/agent/evidence/SPEC/DSM-U5-05.json` 의 **기본 봉투**(id·measured_at·
test·request·response·what)는 `tests/test_p356_u4_rest_spec_promotions.py`
(남의 시험 파일 · CSV 업로드 증거)가 쓴 것을 그대로 둔다 — 이 파일은
`title_parts` 의 두 행만 고친다(P-358 소급 보존 규약).

캐시 처리: 우회 — `setUp` 에서 `cache.clear()` 뒤 `NO_CACHE`(`X-No-Cache`) 클라이언트로 부른다(턴 AP 병합 · D-341).
"""
from __future__ import annotations

import json

from django.utils import timezone

from common.evidence_guard import allow_evidence_writes
from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

CONTROL_LOG = "/api/dsm/u5an/control-log"
EVIDENCE_DIR = "docs/agent/evidence/SPEC"


def _repo_root():
    from pathlib import Path

    return Path(__file__).resolve().parents[2]


EVIDENCE_PATH = _repo_root() / EVIDENCE_DIR / "DSM-U5-05.json"

ROW_LOG_AUTO = "일지 근무자 자동"
ROW_COMPLETION = "완결조건 「일지 근무자 = 편성표」"


def _today() -> str:
    return timezone.localtime(timezone.now()).date().isoformat()


def _merge_title_parts(updates: dict[str, dict[str, str]]) -> None:
    with allow_evidence_writes(
            "P-421 ② DSM-U5-05 title_parts 갱신 — 코드로 다시 실측한 행만 고친다"):
        payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        rows = payload.get("title_parts") or []
        touched = set()
        for row in rows:
            part = row.get("part")
            if part in updates:
                row["status"] = updates[part]["status"]
                if "where" in updates[part]:
                    row["where"] = updates[part]["where"]
                touched.add(part)
        missing = set(updates) - touched
        if missing:
            raise AssertionError(
                "DSM-U5-05.json 에 이 part 가 없다(오타 대조): %s" % missing)
        payload["title_parts"] = rows
        EVIDENCE_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8")


class ControlLogTest(DsmFixture):
    def setUp(self) -> None:
        super().setUp()
        from django.core.cache import cache
        from django.test import Client

        from tests.no_cache import NO_CACHE

        cache.clear()
        self.client = Client(**NO_CACHE)

    def test_control_log_combines_handover_and_incident_timeline(self) -> None:
        from apps.dsm import shift_roster_service

        csv_text = ("date,team,shift,members\n"
                   f"{_today()},1조,주간,홍길동;김철수\n")
        shift_roster_service.import_csv(scope=self.scope_a, csv_text=csv_text)
        event_id = self._event(self.stream_a)

        resp = self.client.get(CONTROL_LOG, **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()

        # ① 사건 타임라인 — 방금 심은 사건이 실제로 보인다(각 카드에 네 시각 시계).
        ids_in_timeline = {row["event_id"] for row in body["incident_timeline"]}
        self.assertIn(event_id, ids_in_timeline,
                      "관제일지의 사건 타임라인에 방금 심은 사건이 없다")
        card = next(r for r in body["incident_timeline"] if r["event_id"] == event_id)
        self.assertIsNotNone(card["clock"], "사건 타임라인 행에 시계(네 시각)가 없다")
        self.assertIn("occurred_at", card["clock"])

        # ① 인계 메모 — 같은 응답 안에 그대로 실린다.
        self.assertIn("근무 편성 1개 조", body["handover"]["body"])
        self.assertIn("홍길동", body["handover"]["body"])

        # ② 완결조건 「일지 근무자 = 편성표」 — 세 자리를 나란히 대조한다.
        roster = shift_roster_service.current_workers(scope=self.scope_a, date=_today())
        self.assertEqual(roster, body["on_duty"],
                         "일지의 근무자가 편성표와 다르다 — 완결조건 미달")
        self.assertEqual(body["handover"]["on_duty"], body["on_duty"],
                         "일지 on_duty 와 인계 메모 on_duty 가 갈렸다 — 두 벌로 셌다")

        _merge_title_parts({
            ROW_LOG_AUTO: {
                "status": (
                    "measured — 관제일지 = 인계 메모 + 사건 타임라인 합본(새 표 0 · "
                    "P-421 ② · 턴 AP N3): handover_service.control_log() 가 "
                    "build_draft()(인계 메모)와 services.recent_events/"
                    "response_clock(사건 타임라인, UX-14 공개 면 재사용)을 한 응답에 "
                    "묶는다. 문: GET /api/dsm/u5an/control-log. 시험: "
                    "tests.test_ap_n3_u5_05_control_log.ControlLogTest."
                    "test_control_log_combines_handover_and_incident_timeline"),
                "where": (
                    "backend/apps/dsm/handover_service.py::control_log · "
                    "backend/apps/dsm/api_u5_an.py::u5an_control_log"),
            },
            ROW_COMPLETION: {
                "status": (
                    "measured — 일지 근무자(control_log().on_duty) == 편성표"
                    "(shift_roster_service.current_workers()) 를 HTTP 응답에서 "
                    "실측 대조(항등 — 같은 호출 하나를 옮겨 쓸 뿐 다른 값을 낼 길이 "
                    "없다). 인계 메모의 on_duty 와도 일치(두 벌로 안 센다). 시험: "
                    "tests.test_ap_n3_u5_05_control_log.ControlLogTest."
                    "test_control_log_combines_handover_and_incident_timeline"),
                "where": "backend/apps/dsm/handover_service.py::control_log",
            },
        })

    def test_other_tenant_incidents_and_roster_do_not_leak(self) -> None:
        from apps.dsm import shift_roster_service

        shift_roster_service.import_csv(
            scope=self.scope_a,
            csv_text=f"date,team,shift,members\n{_today()},1조,주간,홍길동\n")
        event_a = self._event(self.stream_a)
        event_b = self._event(self.stream_b)

        resp = self.client.get(CONTROL_LOG, **_bearer(self.user_b))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()

        ids = {row["event_id"] for row in body["incident_timeline"]}
        self.assertIn(event_b, ids)
        self.assertNotIn(event_a, ids, "남의 테넌트 사건이 관제일지에 샜다")
        self.assertEqual(0, body["on_duty"]["team_count"],
                         "남의 테넌트 근무표가 이쪽 일지에 샜다")
