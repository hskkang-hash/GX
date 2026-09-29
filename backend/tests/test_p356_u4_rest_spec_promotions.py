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
# [턴 AN · P-392 · 차선 N1] 반쪽 채움 ① — CBS 표준 문안 자동 생성
# ═══════════════════════════════════════════════════════════════════════════
class CbsDraftStandardTemplateTest(U4Fixture):
    def test_blank_message_autofills_the_standard_template(self) -> None:
        resp = self.client.post(
            CBS_DRAFTS, {"kind": "안전안내", "region": "정왕동", "message": ""},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()
        self.assertTrue(body["auto_generated"], "표준 문안 자동 생성 표식이 없습니다.")
        self.assertIn("정왕동", body["message"])
        self.assertLessEqual(len(body["message"]), 90)

    def test_hand_written_message_is_not_overwritten(self) -> None:
        resp = self.client.post(
            CBS_DRAFTS,
            {"kind": "안전안내", "region": "정왕동", "message": "직접 쓴 문안"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()
        self.assertFalse(body["auto_generated"])
        self.assertEqual("직접 쓴 문안", body["message"])


# ═══════════════════════════════════════════════════════════════════════════
# [턴 AN · P-392 · 차선 N1] 반쪽 채움 ② — 통제현황 일일보고 자동 반영
# ═══════════════════════════════════════════════════════════════════════════
class ControlBoardDailyReportTest(U4Fixture):
    def test_daily_report_reflects_current_stage_counts(self) -> None:
        created = self.client.post(
            CONTROL_POINTS, {"name": "일일보고시험지점"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, created.status_code, created.content[:300])
        point_id = created.json()["point_id"]

        cache.clear()
        resp = self.client.get(f"{CONTROL_POINTS}/daily-report", **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()
        self.assertIn("as_of", body)
        self.assertGreaterEqual(body["point_count"], 1)
        self.assertIn("도달", body["by_stage"])
        self.assertTrue(any(p["point_id"] == point_id for p in body["points"]))


# ═══════════════════════════════════════════════════════════════════════════
# [턴 AN · P-392 · 차선 N1] 반쪽 채움 ③ — 영상 제공 실제 마스킹 파이프라인 실행
# ═══════════════════════════════════════════════════════════════════════════
class VideoAccessMaskingTest(U4Fixture):
    @staticmethod
    def _sample_jpeg_b64() -> str:
        import base64
        import io

        from PIL import Image

        image = Image.new("RGB", (64, 64), color=(200, 30, 30))
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

    def test_provide_with_image_actually_masks_it(self) -> None:
        created = self.client.post(
            VIDEO_ACCESS,
            {"requester_org": "시흥경찰서", "doc_no": "형사과-2026-777",
             "purpose": "수사"},
            content_type="application/json", **_bearer(self.user_a))
        request_id = created.json()["request_id"]

        cache.clear()
        approved = self.client.post(
            f"{VIDEO_ACCESS}/{request_id}/approve", {},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, approved.status_code, approved.content[:300])

        cache.clear()
        resp = self.client.post(
            f"{VIDEO_ACCESS}/{request_id}/provide",
            {"method": "MinIO 링크", "image_b64": self._sample_jpeg_b64()},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        masking = resp.json()["masking"]
        self.assertTrue(masking["applied"], "마스킹이 실행되지 않았습니다.")
        self.assertGreater(masking["masked_bytes"], 0)
        self.assertTrue(masking["masked_sha12"])

    def test_provide_without_image_still_works_as_before(self) -> None:
        created = self.client.post(
            VIDEO_ACCESS,
            {"requester_org": "시흥경찰서", "doc_no": "형사과-2026-778",
             "purpose": "수사"},
            content_type="application/json", **_bearer(self.user_a))
        request_id = created.json()["request_id"]

        cache.clear()
        self.client.post(
            f"{VIDEO_ACCESS}/{request_id}/approve", {},
            content_type="application/json", **_bearer(self.user_a))

        cache.clear()
        resp = self.client.post(
            f"{VIDEO_ACCESS}/{request_id}/provide", {"method": "MinIO 링크"},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        self.assertFalse(resp.json()["masking"]["applied"])


# ═══════════════════════════════════════════════════════════════════════════
# [턴 AN · P-392 · 차선 N1] 반쪽 채움 ④ — 근무자 자동 조회
# ═══════════════════════════════════════════════════════════════════════════
class ShiftOnDutyTest(U4Fixture):
    def test_on_duty_parses_members_from_the_uploaded_roster(self) -> None:
        resp = self.client.post(
            SHIFTS_IMPORT, {"csv_text": ShiftRosterTest.GOOD_CSV},
            content_type="application/json", **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])

        cache.clear()
        on_duty = self.client.get(
            f"{SHIFTS}/on-duty", {"date": "2026-09-28"}, **_bearer(self.user_a))
        self.assertEqual(200, on_duty.status_code, on_duty.content[:300])
        body = on_duty.json()
        self.assertEqual("2026-09-28", body["date"])
        team1 = next(t for t in body["teams"] if t["team"] == "1조")
        self.assertEqual(["홍길동", "김철수"], team1["members"])
        self.assertEqual("주간", team1["shift"])

    def test_on_duty_defaults_to_today_and_stays_tenant_scoped(self) -> None:
        self.client.post(
            SHIFTS_IMPORT, {"csv_text": ShiftRosterTest.GOOD_CSV},
            content_type="application/json", **_bearer(self.user_b))

        cache.clear()
        mine = self.client.get(f"{SHIFTS}/on-duty", **_bearer(self.user_a))
        self.assertEqual(200, mine.status_code)
        self.assertEqual([], mine.json()["teams"])


# ═══════════════════════════════════════════════════════════════════════════
# P-356 ② — 증거 파일 기계 출력
# ═══════════════════════════════════════════════════════════════════════════
class EvidenceExportTest(U4Fixture):
    def _dump(self, spec_id: str, *, test: str, method: str, path: str,
             req_body, status: int, resp_body, what: str,
             title_parts: list[dict] | None = None,
             decision_note: str = "") -> None:
        payload = {
            "id": spec_id,
            "measured_at": timezone.now().isoformat(),
            "measured_by": "django_test_client",
            "test": test,
            "request": {"method": method, "path": path, "body": req_body},
            "response": {"status": status, "body": resp_body},
            "what": what,
        }
        #: [턴 AN · P-392] 「제목이 부르는 것 ↔ 있는 것」 표 — 빈 칸 0(협약 §끝낼 때).
        if title_parts is not None:
            payload["title_parts"] = title_parts
        #: [턴 AN · P-392 결정 ⑤] DSM-U4-01(HWPX) 처럼 **채우지 않기로 정한** 절은
        #: 전체 표 대신 사유 한 줄만 남긴다.
        if decision_note:
            payload["decision_note"] = decision_note
        with allow_evidence_writes(
                "P-356 ② DSM-U4 절 실측 증거(차선 N4·턴 AM) — pytest 가 방금 두드린 "
                "HTTP 왕복을 그대로 적는다(손으로 옮기지 않는다)"):
            EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
            out_path = EVIDENCE_DIR / f"{spec_id}.json"
            #: [턴 AO · P-407] `title_parts` 를 이 호출이 새로 안 준(`None`) 경우
            #: 에만 이전 표를 보존한다 — 준 경우는 이 호출이 정본을 갱신하는
            #: 것이므로 덮어쓴다. 안 그러면 전량 시험 순서에 따라 표가 지워져
            #: O 게이트가 옛 승격으로 오판한다(`test_fws_app.py::_write_evidence`
            #: 와 같은 판단).
            if title_parts is None and out_path.is_file():
                try:
                    prev = json.loads(out_path.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    prev = {}
                for keep in ("title_parts", "title_parts_note"):
                    if keep in prev:
                        payload[keep] = prev[keep]
            out_path.write_text(
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
                "elapsed_minutes 계산까지 응답에 실렸다. 손으로 지어낸 값 0.",
            decision_note="[턴 AN · P-392 · 결정 ⑤ 「안 산다」] HWPX 는 채우지 "
                         "않는다 — DOCX 가 정본(`api_u24.py::situation_"
                         "report_docx`)이고, HWPX 는 v1.2 옵션으로 미룬다. "
                         "출시 뒤 수요가 있으면 그때 표 후보로 다시 올린다.")

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
                "통과한 실측값이 그대로 응답에 있다.",
            title_parts=[
                {"part": "유형·구역 선택", "where": "create_draft(kind, region)",
                 "status": "있음"},
                {"part": "표준 문안(자동 생성)",
                 "where": "[턴 AN] u4_regulations.CBS_STANDARD_TEMPLATE · "
                         "message 를 비우면 create_draft 가 자동으로 채운다"
                         "(CbsDraftStandardTemplateTest)",
                 "status": "있음(신규)"},
                {"part": "글자 수 검사(90/157)",
                 "where": "u4_regulations.CBS_LEN_LIMIT", "status": "있음"},
                {"part": "승인권자 결재 요청",
                 "where": "POST /cbs-drafts/{id}/approve", "status": "있음"},
                {"part": "발송은 행안부 시스템(이 제품은 안 함)",
                 "where": "발송 버튼 없음 — 명세 그대로", "status": "있음(설계로 보장)"},
                {"part": "발송 기록", "where": "POST /cbs-drafts/{id}/sent",
                 "status": "있음"},
                {"part": "야간(21~06시) 안전안내 경고",
                 "where": "night_warning 플래그", "status": "있음"},
            ])

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
                "칸까지 같은 줄에 실렸다.",
            title_parts=[
                {"part": "통제 개소 등록", "where": "POST /control-points",
                 "status": "있음"},
                {"part": "도달·결정·실행·해제 4시각",
                 "where": "u4_regulations.CONTROL_STAGE_ORDER · advance()",
                 "status": "있음"},
                {"part": "대피 인원·장소",
                 "where": "evacuee_count · evacuation_site", "status": "있음"},
                {"part": "현황판(출력)", "where": "GET /control-points",
                 "status": "있음"},
                {"part": "일일보고 자동 반영",
                 "where": "[턴 AN] GET /control-points/daily-report · "
                         "control_board_service.daily_reflection"
                         "(ControlBoardDailyReportTest)",
                 "status": "있음(신규)"},
                {"part": "controls 모델(처리)",
                 "where": "감사 이력 대장(새 표 0 — AppStaysThinTest 와 같은 원칙)",
                 "status": "있음(다른 모양 — 완결조건과 무관)"},
            ])

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
            what="영상 제공 요청(공문번호·목적) 접수 한 건을 실제로 대장에 남겼다.",
            title_parts=[
                {"part": "수사기관 요청 접수(공문번호·목적·범위)",
                 "where": "POST /video-access-requests", "status": "있음"},
                {"part": "승인", "where": "POST .../approve", "status": "있음"},
                {"part": "마스킹본 제공(가림 처리)",
                 "where": "[턴 AN] provide(image_b64=...) → "
                         "apps.dsm.privacy_request.mask_jpeg 실제 실행 · "
                         "원본≠결과 해시로 확인(VideoAccessMaskingTest)",
                 "status": "있음(신규)"},
                {"part": "개인영상정보 관리대장 자동 기재",
                 "where": "GET /video-access-requests(요청→승인→제공 세 단계)",
                 "status": "있음"},
                {"part": "원본 반출 0",
                 "where": "함수 어디에도 원본 파일 경로 매개변수가 없다(구조로 보장)",
                 "status": "있음"},
                {"part": "연간 통계(출력)",
                 "where": "[턴 AO] GET /video-access-requests/annual-stats · "
                         "video_access_ledger_service.annual_stats — 같은 감사 "
                         "이력을 연도로 걸러 요청·승인·제공 건수·월별 요청 건수를 "
                         "낸다(새 표 0 · VideoAccessAnnualStatsTest)",
                 "status": "있음(신규)"},
            ])

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
                "imported=2 가 응답에 실렸다.",
            title_parts=[
                {"part": "CSV 업로드", "where": "POST /shifts/import",
                 "status": "있음"},
                {"part": "shifts 저장", "where": "감사 이력 대장(재업로드=최근 줄 승)",
                 "status": "있음"},
                {"part": "표(출력)", "where": "GET /shifts", "status": "있음"},
                {"part": "근무자 자동 조회(핵심 사실)",
                 "where": "[턴 AN] GET /shifts/on-duty · "
                         "shift_roster_service.current_workers(ShiftOnDutyTest)",
                 "status": "있음(신규)"},
                {"part": "인계 메모 근무자 자동",
                 "where": "[턴 AO] handover_service.build_draft() → "
                         "shift_roster_service.current_workers() — 인계 초안 본문 "
                         "5번째 줄과 on_duty 칸에 그대로 실린다(새 표 0 · "
                         "HandoverRosterConnectionTest)",
                 "status": "있음(신규)"},
                {"part": "일지 근무자 자동",
                 "where": "관제일지(DSM-U1-04) 자체가 이 저장소에 없다 — 이 턴도 "
                         "만들지 않았다(새 표 0 지시 · 별도 절)",
                 "status": "없음(범위 밖 — 별도 절)"},
                {"part": "완결조건 「일지 근무자 = 편성표」",
                 "where": "근무자는 자동으로 나와 인계 메모에 실리나(위) 명세가 "
                         "부르는 「일지」자체가 이 제품에 없다",
                 "status": "부분(인계 메모로 대신 — 일지 자체는 미착수)"},
            ])
