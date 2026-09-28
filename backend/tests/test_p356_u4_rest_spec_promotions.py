# -*- coding: utf-8 -*-
"""P-356/P-358 · WO-GX-20260925-15 §5 — **DSM-U4-01(부분)·U4-03·U4-04(부분)·
U4-07(부분)·U5-05(부분) 승격 시험** · 차선 N4 · 턴 AM.

캐시 처리: 우회/비움/해당 없음 — `test_p356_u4_spec_promotions.py`(차선 N1)와 같은
이유로 매 요청 뒤 `cache.clear()` 를 부른다(`common/idempotency.py` 가 Redis 에
성공 응답을 잠깐 기억해, 창을 안 비우면 같은 시험 안에서 두 번째 요청이 새 자원
대신 옛 응답을 받는다).

이 파일이 잰다
--------------
  DSM-U4-01 `POST /api/dsm/situation-reports` · `.../sent` — 사건마다 제N보가
    1부터 순서대로 채번된다 · 보고 구분 밖 값 400 · 남의 테넌트 사건 404 ·
    발송 전 재발송 409.
  DSM-U4-03 `POST /api/dsm/cbs-drafts[...]` — 글자수 초과 400(안전안내 90 · 긴급
    157) · 승인 전 발송 409 · 야간 안전안내 경고 플래그.
  DSM-U4-04 `POST /api/dsm/control-points[...]` — 4단계 순서(도달→결정→실행→해제)
    를 어기면 409 · 현황판이 지금 단계를 보여준다.
  DSM-U4-07 `POST /api/dsm/video-access-requests[...]` — 승인 전 제공 409 ·
    제공 기록에 원본 미반출 문구가 항상 붙는다.
  DSM-U5-05 `POST /api/dsm/shifts/import` — 계약 밖 CSV 는 **전부 저장하지 않는다**
    (전부 아니면 전무) · 재업로드는 최근 줄이 이긴다.

이 다섯이 「부분」인 이유는 각 서비스 파일 머리말과
`docs/agent/evidence/SPEC/N4_promotions.md` 가 적는다 — 이 시험은 **실제로
갖춘 부분**만 잰다(P-356 「셋 중 하나라도 없으면 승격하지 않는다」의 반대편 —
갖춘 것은 실측으로 보인다).
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.cache import cache
from django.utils import timezone

from common.evidence_guard import allow_evidence_writes
from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

SITUATION_REPORTS = "/api/dsm/situation-reports"
CBS_DRAFTS = "/api/dsm/cbs-drafts"
CONTROL_POINTS = "/api/dsm/control-points"
VIDEO_ACCESS = "/api/dsm/video-access-requests"
SHIFTS_IMPORT = "/api/dsm/shifts/import"
SHIFTS = "/api/dsm/shifts"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


#: P-356 ② — 증거 파일이 사는 자리. **손으로 만들지 않는다** — 아래
#: `EvidenceExportTest` 가 실제로 때린 응답으로 채운다.
EVIDENCE_DIR = _repo_root() / "docs" / "agent" / "evidence" / "SPEC"


class U4Fixture(DsmFixture):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self._clear_thread_request()

    def tearDown(self) -> None:
        #: HTTP 를 때린 시험 뒤 스레드에 요청이 남으면 다음 시험의 `objects` 가 빈다
        #: (메모리 「스레드에 남은 요청이 거짓 초록을 만든다」).
        self._clear_thread_request()
        super().tearDown()

    @staticmethod
    def _clear_thread_request() -> None:
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U4-01 재난상황보고서 제N보 채번 대장
# ═══════════════════════════════════════════════════════════════════════════
class SituationReportLedgerTest(U4Fixture):
    def test_out_of_range_kind_is_400(self) -> None:
        event_id = self._event(self.stream_a)
        resp = self.client.post(
            SITUATION_REPORTS, {"event_id": event_id, "kind": "넷째보"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(400, resp.status_code, resp.content[:300])

    def test_report_numbers_increment_per_event(self) -> None:
        event_id = self._event(self.stream_a)
        first = self.client.post(
            SITUATION_REPORTS, {"event_id": event_id, "kind": "최초"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, first.status_code, first.content[:300])
        self.assertEqual(1, first.json()["report_no"])
        self.assertIn("elapsed_minutes", first.json())

        cache.clear()
        second = self.client.post(
            SITUATION_REPORTS, {"event_id": event_id, "kind": "중간"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, second.status_code, second.content[:300])
        self.assertEqual(2, second.json()["report_no"])

        cache.clear()
        listing = self.client.get(
            SITUATION_REPORTS, {"event_id": event_id}, **_bearer(self.user_a))
        self.assertEqual(200, listing.status_code)
        self.assertEqual(2, len(listing.json()))

    def test_other_tenant_event_is_404(self) -> None:
        event_id = self._event(self.stream_b)
        resp = self.client.post(
            SITUATION_REPORTS, {"event_id": event_id, "kind": "최초"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(404, resp.status_code, resp.content[:300])

    def test_sent_before_conflict_is_409_on_resend(self) -> None:
        event_id = self._event(self.stream_a)
        issued = self.client.post(
            SITUATION_REPORTS, {"event_id": event_id, "kind": "최초"},
            content_type="application/json", **_bearer(self.user_a))
        report_id = issued.json()["report_id"]

        cache.clear()
        sent = self.client.post(
            f"{SITUATION_REPORTS}/{report_id}/sent", {"recipient": "중대본"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, sent.status_code, sent.content[:300])

        cache.clear()
        again = self.client.post(
            f"{SITUATION_REPORTS}/{report_id}/sent", {"recipient": "중대본"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(409, again.status_code, again.content[:300])


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U4-03 재난문자(CBS) 초안
# ═══════════════════════════════════════════════════════════════════════════
class CbsDraftTest(U4Fixture):
    def test_message_over_limit_is_400(self) -> None:
        resp = self.client.post(
            CBS_DRAFTS,
            {"kind": "안전안내", "region": "정왕동", "message": "가" * 91},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(400, resp.status_code, resp.content[:300])

    def test_urgent_allows_157_but_not_158(self) -> None:
        ok = self.client.post(
            CBS_DRAFTS,
            {"kind": "긴급", "region": "정왕동", "message": "가" * 157},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, ok.status_code, ok.content[:300])

        cache.clear()
        over = self.client.post(
            CBS_DRAFTS,
            {"kind": "긴급", "region": "정왕동", "message": "가" * 158},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(400, over.status_code, over.content[:300])

    def test_night_safety_message_is_flagged(self) -> None:
        from datetime import datetime

        import zoneinfo

        night = datetime(2026, 9, 28, 23, 0, tzinfo=zoneinfo.ZoneInfo("Asia/Seoul"))
        resp = self.client.post(
            CBS_DRAFTS,
            {"kind": "안전안내", "region": "정왕동", "message": "대피 안내",
             "occurred_at": night.isoformat()},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self.assertTrue(resp.json()["night_warning"])

    def test_sent_before_approve_is_409(self) -> None:
        created = self.client.post(
            CBS_DRAFTS, {"kind": "위급", "region": "정왕동", "message": "대피"},
            content_type="application/json", **_bearer(self.user_a))
        draft_id = created.json()["draft_id"]

        cache.clear()
        sent = self.client.post(
            f"{CBS_DRAFTS}/{draft_id}/sent", {},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(409, sent.status_code, sent.content[:300])

        cache.clear()
        approved = self.client.post(
            f"{CBS_DRAFTS}/{draft_id}/approve", {},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, approved.status_code, approved.content[:300])

        cache.clear()
        sent_now = self.client.post(
            f"{CBS_DRAFTS}/{draft_id}/sent", {},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, sent_now.status_code, sent_now.content[:300])

    def test_other_tenant_draft_is_404(self) -> None:
        created = self.client.post(
            CBS_DRAFTS, {"kind": "위급", "region": "정왕동", "message": "대피"},
            content_type="application/json", **_bearer(self.user_b))
        draft_id = created.json()["draft_id"]

        cache.clear()
        resp = self.client.post(
            f"{CBS_DRAFTS}/{draft_id}/approve", {},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(404, resp.status_code, resp.content[:300])


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U4-04 통제·대피 현황판
# ═══════════════════════════════════════════════════════════════════════════
class ControlBoardTest(U4Fixture):
    def test_execute_before_decide_is_409(self) -> None:
        created = self.client.post(
            CONTROL_POINTS, {"name": "정왕지하차도", "evacuee_count": 12},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, created.status_code, created.content[:300])
        point_id = created.json()["point_id"]

        cache.clear()
        resp = self.client.post(
            f"{CONTROL_POINTS}/{point_id}/advance", {"stage": "실행"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(409, resp.status_code, resp.content[:300])

    def test_full_sequence_then_board_shows_released(self) -> None:
        created = self.client.post(
            CONTROL_POINTS, {"name": "둔치주차장"},
            content_type="application/json", **_bearer(self.user_a))
        point_id = created.json()["point_id"]

        for stage in ("결정", "실행", "해제"):
            cache.clear()
            resp = self.client.post(
                f"{CONTROL_POINTS}/{point_id}/advance", {"stage": stage},
                content_type="application/json", **_bearer(self.user_a))
            self.assertEqual(200, resp.status_code, f"{stage}: {resp.content[:300]}")

        cache.clear()
        # ★ 이미 거친 단계를 또 부르면 순서 위반이다(중복 실행 금지).
        again = self.client.post(
            f"{CONTROL_POINTS}/{point_id}/advance", {"stage": "해제"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(409, again.status_code, again.content[:300])

        cache.clear()
        board = self.client.get(CONTROL_POINTS, **_bearer(self.user_a))
        self.assertEqual(200, board.status_code, board.content[:300])
        row = next(r for r in board.json() if r["point_id"] == point_id)
        self.assertEqual("해제", row["stage"])

    def test_other_tenant_point_is_404(self) -> None:
        created = self.client.post(
            CONTROL_POINTS, {"name": "타테넌트지점"},
            content_type="application/json", **_bearer(self.user_b))
        point_id = created.json()["point_id"]

        cache.clear()
        resp = self.client.post(
            f"{CONTROL_POINTS}/{point_id}/advance", {"stage": "결정"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(404, resp.status_code, resp.content[:300])


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U4-07 영상 열람·제공(반출) 대장
# ═══════════════════════════════════════════════════════════════════════════
class VideoAccessLedgerTest(U4Fixture):
    def test_missing_doc_no_is_400(self) -> None:
        resp = self.client.post(
            VIDEO_ACCESS,
            {"requester_org": "시흥경찰서", "doc_no": "", "purpose": "수사"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(400, resp.status_code, resp.content[:300])

    def test_provide_before_approve_is_409_then_ok_with_original_not_released(self) -> None:
        created = self.client.post(
            VIDEO_ACCESS,
            {"requester_org": "시흥경찰서", "doc_no": "형사과-2026-118",
             "purpose": "수사", "scope_desc": "9/27 03~04시"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, created.status_code, created.content[:300])
        request_id = created.json()["request_id"]

        cache.clear()
        early = self.client.post(
            f"{VIDEO_ACCESS}/{request_id}/provide", {},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(409, early.status_code, early.content[:300])

        cache.clear()
        approved = self.client.post(
            f"{VIDEO_ACCESS}/{request_id}/approve", {},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, approved.status_code, approved.content[:300])

        cache.clear()
        provided = self.client.post(
            f"{VIDEO_ACCESS}/{request_id}/provide", {"method": "MinIO 링크"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, provided.status_code, provided.content[:300])
        self.assertIn("원본 미반출", provided.json()["note"])

        cache.clear()
        ledger = self.client.get(VIDEO_ACCESS, **_bearer(self.user_a))
        row = next(r for r in ledger.json() if r["request_id"] == request_id)
        self.assertEqual("제공", row["status"])

    def test_other_tenant_request_is_404(self) -> None:
        created = self.client.post(
            VIDEO_ACCESS,
            {"requester_org": "타서", "doc_no": "X-1", "purpose": "수사"},
            content_type="application/json", **_bearer(self.user_b))
        request_id = created.json()["request_id"]

        cache.clear()
        resp = self.client.post(
            f"{VIDEO_ACCESS}/{request_id}/approve", {},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(404, resp.status_code, resp.content[:300])


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U5-05 교대 편성(4조 3교대) CSV
# ═══════════════════════════════════════════════════════════════════════════
class ShiftRosterTest(U4Fixture):
    GOOD_CSV = ("date,team,shift,members\n"
               "2026-09-28,1조,주간,홍길동;김철수\n"
               "2026-09-28,2조,야간,이영희\n")

    def test_all_or_nothing_on_bad_row(self) -> None:
        bad_csv = self.GOOD_CSV + "2026-09-28,5조,주간,나쁜조\n"
        resp = self.client.post(
            SHIFTS_IMPORT, {"csv_text": bad_csv},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(400, resp.status_code, resp.content[:300])

        cache.clear()
        listing = self.client.get(SHIFTS, **_bearer(self.user_a))
        self.assertEqual(200, listing.status_code)
        self.assertEqual(
            [], listing.json(),
            "계약을 어긴 CSV 인데 일부 줄이 저장됐다 — 전부 아니면 전무가 깨졌다.")

    def test_good_csv_round_trips_and_reupload_wins(self) -> None:
        resp = self.client.post(
            SHIFTS_IMPORT, {"csv_text": self.GOOD_CSV},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self.assertEqual(2, resp.json()["imported"])

        cache.clear()
        listing = self.client.get(
            SHIFTS, {"date": "2026-09-28"}, **_bearer(self.user_a))
        self.assertEqual(200, listing.status_code)
        rows = listing.json()
        self.assertEqual(2, len(rows))
        self.assertIn("홍길동", next(r["text"] for r in rows if r["team"] == "1조"))

        # ★ 재업로드 — 1조의 근무자를 바꾸면 **최근 줄이 이긴다.**
        cache.clear()
        reupload = ("date,team,shift,members\n"
                   "2026-09-28,1조,비번,박정정\n")
        resp2 = self.client.post(
            SHIFTS_IMPORT, {"csv_text": reupload},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, resp2.status_code, resp2.content[:300])

        cache.clear()
        listing2 = self.client.get(
            SHIFTS, {"date": "2026-09-28"}, **_bearer(self.user_a))
        team1 = next(r for r in listing2.json() if r["team"] == "1조")
        self.assertIn("박정정", team1["text"])
        self.assertIn("비번", team1["text"])

    def test_other_tenant_roster_is_not_visible(self) -> None:
        self.client.post(
            SHIFTS_IMPORT, {"csv_text": self.GOOD_CSV},
            content_type="application/json", **_bearer(self.user_b))

        cache.clear()
        mine = self.client.get(
            SHIFTS, {"date": "2026-09-28"}, **_bearer(self.user_a))
        self.assertEqual(200, mine.status_code)
        self.assertEqual([], mine.json())


# ═══════════════════════════════════════════════════════════════════════════
# 규정값 표본 — 이 값을 고치면 시험이 빨개진다 (D-280)
# ═══════════════════════════════════════════════════════════════════════════
class RegulationConstantsTest(U4Fixture):
    def test_cbs_length_limits_match_the_regulation(self) -> None:
        from apps.dsm.u4_regulations import CBS_LEN_LIMIT

        #: 출처: DSM 명세서 §4.4 「재난문자(CBS)」행 — 「90자(안전안내)/157자(긴급·위급)」.
        self.assertEqual(90, CBS_LEN_LIMIT["안전안내"])
        self.assertEqual(157, CBS_LEN_LIMIT["긴급"])
        self.assertEqual(157, CBS_LEN_LIMIT["위급"])

    def test_shift_teams_are_four_for_4jo_3gyodae(self) -> None:
        from apps.dsm.u4_regulations import SHIFT_KINDS, SHIFT_TEAMS

        #: 출처: 명세서 §3.1 U1 행 「4조 3교대(주·야·비번)」.
        self.assertEqual(4, len(SHIFT_TEAMS))
        self.assertEqual(("주간", "야간", "비번"), SHIFT_KINDS)

    def test_control_stage_order_is_the_four_named_by_the_clause(self) -> None:
        from apps.dsm.u4_regulations import CONTROL_STAGE_ORDER

        #: 출처: 명세서 §4.4 DSM-U4-04 「도달·결정·실행·해제 4시각」.
        self.assertEqual(("도달", "결정", "실행", "해제"), CONTROL_STAGE_ORDER)


# ═══════════════════════════════════════════════════════════════════════════
# P-356 ② — 증거 파일 기계 출력
# ═══════════════════════════════════════════════════════════════════════════
class EvidenceExportTest(U4Fixture):
    def _dump(self, spec_id: str, *, test: str, method: str, path: str,
             req_body, status: int, resp_body, what: str) -> None:
        payload = {
            "id": spec_id,
            "measured_at": timezone.now().isoformat(),
            "measured_by": "django_test_client",
            "test": test,
            "request": {"method": method, "path": path, "body": req_body},
            "response": {"status": status, "body": resp_body},
            "what": what,
        }
        with allow_evidence_writes(
                "P-356 ② DSM-U4 절 실측 증거(차선 N4·턴 AM) — pytest 가 방금 두드린 "
                "HTTP 왕복을 그대로 적는다(손으로 옮기지 않는다)"):
            EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
            (EVIDENCE_DIR / f"{spec_id}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8")

    def test_dump_dsm_u4_01_evidence(self) -> None:
        event_id = self._event(self.stream_a)
        resp = self.client.post(
            SITUATION_REPORTS, {"event_id": event_id, "kind": "최초"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self._dump(
            "DSM-U4-01",
            test="tests.test_p356_u4_rest_spec_promotions.EvidenceExportTest"
                ".test_dump_dsm_u4_01_evidence",
            method="POST", path=SITUATION_REPORTS,
            req_body={"event_id": event_id, "kind": "최초"},
            status=resp.status_code, resp_body=resp.json(),
            what="사건 하나에 제1보(최초)를 실제로 채번했다 — report_no=1 · "
                "elapsed_minutes 계산까지 응답에 실렸다. 손으로 지어낸 값 0.")

    def test_dump_dsm_u4_03_evidence(self) -> None:
        resp = self.client.post(
            CBS_DRAFTS, {"kind": "긴급", "region": "정왕동", "message": "즉시 대피"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self._dump(
            "DSM-U4-03",
            test="tests.test_p356_u4_rest_spec_promotions.EvidenceExportTest"
                ".test_dump_dsm_u4_03_evidence",
            method="POST", path=CBS_DRAFTS,
            req_body={"kind": "긴급", "region": "정왕동", "message": "즉시 대피"},
            status=resp.status_code, resp_body=resp.json(),
            what="재난문자 초안 한 건을 실제로 만들었다 — 글자수(4/157) 검사를 "
                "통과한 실측값이 그대로 응답에 있다.")

    def test_dump_dsm_u4_04_evidence(self) -> None:
        resp = self.client.post(
            CONTROL_POINTS, {"name": "하천산책로", "evacuee_count": 5},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self._dump(
            "DSM-U4-04",
            test="tests.test_p356_u4_rest_spec_promotions.EvidenceExportTest"
                ".test_dump_dsm_u4_04_evidence",
            method="POST", path=CONTROL_POINTS,
            req_body={"name": "하천산책로", "evacuee_count": 5},
            status=resp.status_code, resp_body=resp.json(),
            what="통제 개소 등록(=도달 시각) 한 건을 실제로 남겼다 — 대피 인원 "
                "칸까지 같은 줄에 실렸다.")

    def test_dump_dsm_u4_07_evidence(self) -> None:
        resp = self.client.post(
            VIDEO_ACCESS,
            {"requester_org": "시흥경찰서", "doc_no": "형사과-2026-200",
             "purpose": "수사"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self._dump(
            "DSM-U4-07",
            test="tests.test_p356_u4_rest_spec_promotions.EvidenceExportTest"
                ".test_dump_dsm_u4_07_evidence",
            method="POST", path=VIDEO_ACCESS,
            req_body={"requester_org": "시흥경찰서", "doc_no": "형사과-2026-200",
                     "purpose": "수사"},
            status=resp.status_code, resp_body=resp.json(),
            what="영상 제공 요청(공문번호·목적) 접수 한 건을 실제로 대장에 남겼다.")

    def test_dump_dsm_u5_05_evidence(self) -> None:
        resp = self.client.post(
            SHIFTS_IMPORT, {"csv_text": ShiftRosterTest.GOOD_CSV},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self._dump(
            "DSM-U5-05",
            test="tests.test_p356_u4_rest_spec_promotions.EvidenceExportTest"
                ".test_dump_dsm_u5_05_evidence",
            method="POST", path=SHIFTS_IMPORT,
            req_body={"csv_text": ShiftRosterTest.GOOD_CSV},
            status=resp.status_code, resp_body=resp.json(),
            what="4조 3교대 근무표 CSV 2줄을 실제로 업로드해 저장했다 — "
                "imported=2 가 응답에 실렸다.")
