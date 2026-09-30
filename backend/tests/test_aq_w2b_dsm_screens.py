# -*- coding: utf-8 -*-
"""턴 AQ · 차선 W2B — DSM 판단·인계 화면 배선(DSM-U2-03 · U2-04 · U2-05 · U4-06).

캐시 처리: 우회 — 매 시험·매 요청 사이 `cache.clear()`(멱등 창·응답 캐시가 누르기 전 값을
되살리지 않게) · 화면은 재조회에 `X-No-Cache` 를 싣는다(`aqScreensApi.aqFreshGet`).

이 파일이 잰다 — 화면이 부르는 그 순서 그대로 **누른 뒤 새 GET 으로 재조회**한다.
  U2-03  회의 폼 POST(`alert_level` 포함) → GET `/alert-level` 첫 행 단계가 바뀐다(상태 축) ·
         단계를 안 고른 회의는 축을 안 바꾼다 · 4단계 밖은 400 · 남의 테넌트 축은 그대로.
  U2-04  관측 도달 → GET `/thresholds/alerts` 에 「기준 도달 hh:mm · 통제 여부 결정 필요」 ·
         결정 POST → 같은 GET 이 결정됨 · 남의 테넌트 카드는 안 보인다.
  U2-05  GET `/handover/latest` 의 인계 창 08:00~09:00(명세 원문) · 확인 POST → 같은 GET 이 ✓ ·
         창 안/밖 판정(고정 시각) · 남의 테넌트 인계는 안 보인다.
  U4-06  접수 POST → GET `/alert-level?limit=1` 이 단계·문서번호·인원을 칸으로 낸다 · 격리.
  정적  화면 파일이 `data-gx` 를 **글자 그대로** 갖고, 홈이 그 줄을 끼운다.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from django.core.cache import cache
from django.test import SimpleTestCase

from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

MEETINGS = "/api/dsm/situation-meetings"
ALERT = "/api/dsm/alert-level"
OBSERVE = "/api/dsm/thresholds/observe"
ALERTS = "/api/dsm/thresholds/alerts"
LATEST = "/api/dsm/handover/latest"


def _clear_thread_request() -> None:
    import contextlib

    with contextlib.suppress(Exception):
        from core.middleware.refresh_token import thread_local

        thread_local.request = None


class W2BFixture(DsmFixture):
    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        from core.middleware.refresh_token import thread_local

        thread_local.request = None
        super().setUpTestData()
        cls.lead_a = cls._user(
            "w2b_lead_a", cls.group_a, cls._own(cls._role("w2b_u2_a"), cls.group_a))
        cls.lead_b = cls._user(
            "w2b_lead_b", cls.group_b, cls._own(cls._role("w2b_u2_b"), cls.group_b))

    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        _clear_thread_request()

    def tearDown(self) -> None:
        _clear_thread_request()
        super().tearDown()

    def _get(self, url, user, **params):
        cache.clear()
        resp = self.client.get(url, params, **_bearer(user))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        return resp.json()

    def _post(self, url, user, body=None, expect=200):
        cache.clear()
        resp = self.client.post(url, body or {}, content_type="application/json",
                                **_bearer(user))
        self.assertEqual(expect, resp.status_code, resp.content[:300])
        return resp.json()


# ═══════════════════════════════════════════════════════════════════════════
class SituationMeetingScreenTest(W2BFixture):
    def test_meeting_decision_moves_alert_level_axis_then_refetch(self) -> None:
        self.assertEqual([], self._get(ALERT, self.lead_a, limit=1))
        body = self._post(MEETINGS, self.lead_a, {
            "occurred_at": "2026-09-30T03:40:00+09:00",
            "attendees": "상황실장·팀장·U4", "decision": "통제 실시 · 비상 단계 경계",
            "basis": "수위 182cm · 강우 41mm", "alert_level": "경계"})
        self.assertIsNotNone(body["alert_level"])

        rows = self._get(ALERT, self.lead_a, limit=1)
        self.assertEqual("경계", rows[0]["level"])
        self.assertEqual(f"상황판단회의 기록 #{body['meeting_id']}", rows[0]["doc_no"])
        meetings = self._get(MEETINGS, self.lead_a)
        self.assertIn("통제 실시", meetings[0]["text"])

    def test_meeting_without_level_leaves_axis(self) -> None:
        self._post(ALERT, self.lead_a, {"level": "주의"})
        body = self._post(MEETINGS, self.lead_a, {"decision": "대피 권고만"})
        self.assertIsNone(body["alert_level"])
        self.assertEqual("주의", self._get(ALERT, self.lead_a, limit=1)[0]["level"])

    def test_unknown_level_is_400_and_nothing_written(self) -> None:
        self._post(MEETINGS, self.lead_a,
                   {"decision": "x", "alert_level": "2단계"}, expect=400)
        self.assertEqual([], self._get(MEETINGS, self.lead_a))
        self.assertEqual([], self._get(ALERT, self.lead_a))

    def test_other_tenant_axis_untouched(self) -> None:
        self._post(MEETINGS, self.lead_b, {"decision": "B 결정", "alert_level": "심각"})
        self.assertEqual([], self._get(ALERT, self.lead_a))
        self.assertEqual("심각", self._get(ALERT, self.lead_b, limit=1)[0]["level"])


# ═══════════════════════════════════════════════════════════════════════════
class ThresholdAlertScreenTest(W2BFixture):
    def _baseline(self, scope, stream):
        from kernels.k5_trust import set_threshold

        set_threshold(scope=scope, key="waterlevel.baseline", value=180,
                      reason="시험 기준선", scope_level="camera", scope_ref=stream.pk)

    def test_card_notice_then_decide_then_refetch(self) -> None:
        self._baseline(self.scope_a, self.stream_a)
        obs = self._post(OBSERVE, self.lead_a, {
            "camera_id": self.stream_a.pk, "key": "waterlevel.baseline", "value": 182})
        oid = obs["observation_id"]

        cards = self._get(ALERTS, self.lead_a)
        self.assertEqual([oid], [c["observation_id"] for c in cards])
        self.assertRegex(cards[0]["notice"], r"^기준 도달 \d\d:\d\d · 통제 여부 결정 필요$")
        self.assertFalse(cards[0]["decided"])

        self._post(f"{OBSERVE}/{oid}/decide", self.lead_a, {"decision": "통제 실시"})
        after = self._get(ALERTS, self.lead_a)
        self.assertTrue(after[0]["decided"])
        self.assertEqual("통제 실시", after[0]["decision"])
        self.assertIsNotNone(after[0]["decided_at"])

    def test_other_tenant_cards_hidden(self) -> None:
        self._baseline(self.scope_b, self.stream_b)
        self._post(OBSERVE, self.lead_b, {
            "camera_id": self.stream_b.pk, "key": "waterlevel.baseline", "value": 200})
        self.assertEqual([], self._get(ALERTS, self.lead_a))
        self.assertEqual(1, len(self._get(ALERTS, self.lead_b)))


# ═══════════════════════════════════════════════════════════════════════════
class HandoverAckScreenTest(W2BFixture):
    def _save(self, user) -> int:
        return self._post("/api/dsm/handover/draft", user,
                          {"hours": 24, "note": "특이사항 없음"})["id"]

    def test_ack_then_refetch_shows_check_and_window(self) -> None:
        hid = self._save(self.lead_a)
        before = self._get(LATEST, self.lead_a)
        self.assertFalse(before["acknowledged"])
        self.assertEqual({"start": "08:00", "end": "09:00"},
                         {k: before["handover_window"][k] for k in ("start", "end")})

        ack = self._post(f"/api/dsm/handover/{hid}/ack", self.lead_a)
        self.assertIn("in_window", ack)
        after = self._get(LATEST, self.lead_a)
        self.assertTrue(after["acknowledged"])
        self.assertRegex(after["acknowledgement"]["reason"],
                         r"인계 창 08:00~09:00 (안|밖)$")

    def test_window_bounds_are_the_spec_hours(self) -> None:
        from apps.dsm.handover_service import handover_window

        # [턴 AQ · 조율자] 한국 시각(Asia/Seoul)으로 잰다 — 앱 전역 TIME_ZONE(Ho_Chi_Minh · UTC+7)과
        # 무관해야 한다(P-260 규약). 그래서 같은 순간을 두 시간대로 다 대 본다.
        from zoneinfo import ZoneInfo

        kst = ZoneInfo("Asia/Seoul")
        self.assertTrue(handover_window(datetime(2026, 9, 30, 8, 30, tzinfo=kst))["open"])
        self.assertFalse(handover_window(datetime(2026, 9, 30, 9, 0, tzinfo=kst))["open"])
        self.assertFalse(handover_window(datetime(2026, 9, 30, 7, 59, tzinfo=kst))["open"])
        # 호찌민 08:30 = 한국 10:30 → 창 밖(전역 시간대로 재면 거짓으로 「안」이 된다)
        hcm = ZoneInfo("Asia/Ho_Chi_Minh")
        self.assertFalse(handover_window(datetime(2026, 9, 30, 8, 30, tzinfo=hcm))["open"])

    def test_other_tenant_handover_not_on_my_card(self) -> None:
        self._save(self.lead_b)
        self.assertFalse(self._get(LATEST, self.lead_a)["exists"])


# ═══════════════════════════════════════════════════════════════════════════
class AlertLevelScreenTest(W2BFixture):
    def test_record_then_band_refetch_reads_fields(self) -> None:
        self._post(ALERT, self.lead_a, {"level": "관심"})
        self._post(ALERT, self.lead_a, {
            "level": "경계", "doc_no": "제3호", "staffing": 24,
            "occurred_at": "2026-09-30T08:10"})
        row = self._get(ALERT, self.lead_a, limit=1)[0]
        self.assertEqual(("경계", "제3호", 24, "2026-09-30 08:10"),
                         (row["level"], row["doc_no"], row["staffing"], row["received_at"]))

    def test_isolation(self) -> None:
        self._post(ALERT, self.lead_b, {"level": "심각"})
        self.assertEqual([], self._get(ALERT, self.lead_a, limit=1))


# ═══════════════════════════════════════════════════════════════════════════
def _root() -> Path | None:
    for base in (Path("/repo"), *Path(__file__).resolve().parents):
        if (base / "frontend" / "src" / "App.tsx").is_file():
            return base
    return None


class ScreenStaticTest(SimpleTestCase):
    """화면 파일이 판정기가 찾는 `data-gx` 를 글자 그대로 갖고, 부르는 경로가 서버와 같다."""

    COMP = "frontend/src/features/dsm/components/"
    WANT = {
        "SituationMeetingCard.tsx": [
            "dsm-u2-03-occurred-at", "dsm-u2-03-attendees", "dsm-u2-03-decision",
            "dsm-u2-03-basis", "dsm-u2-03-alert-level", "dsm-u2-03-submit", "dsm-u2-03-list"],
        "ThresholdAlertCard.tsx": [
            "dsm-u2-04-card", "dsm-u2-04-notice", "dsm-u2-04-decision", "dsm-u2-04-decide",
            "dsm-u2-04-decided"],
        "HandoverAckCard.tsx": [
            "dsm-u2-05-card", "dsm-u2-05-window", "dsm-u2-05-ack", "dsm-u2-05-acked"],
        "AlertLevelBand.tsx": ["dsm-u4-06-band", "dsm-u4-06-band-level"],
        "AlertLevelCard.tsx": [
            "dsm-u4-06-card", "dsm-u4-06-level", "dsm-u4-06-doc-no", "dsm-u4-06-staffing",
            "dsm-u4-06-submit", "dsm-u4-06-current"],
    }

    def setUp(self) -> None:
        self.root = _root()
        self.assertIsNotNone(self.root, "저장소 뿌리를 못 찾았다 — 판정 불가를 초록으로 두지 않는다")

    def _read(self, rel: str) -> str:
        return (self.root / rel).read_text(encoding="utf-8")

    def test_data_gx_literal(self) -> None:
        for name, ids in self.WANT.items():
            body = self._read(self.COMP + name)
            for gx in ids:
                self.assertIn(f'data-gx="{gx}"', body, f"{name} :: {gx}")
            self.assertNotRegex(body, r"data-gx=\{`", name)

    def test_paths_match_server_routes(self) -> None:
        api = self._read(self.COMP + "w2bDecisionApi.ts")
        for path in (MEETINGS, ALERT, ALERTS, LATEST, "/api/dsm/thresholds/observe/",
                     "/api/dsm/handover/"):
            self.assertIn(path, api)

    def test_every_write_is_followed_by_refetch(self) -> None:
        for name in ("SituationMeetingCard.tsx", "ThresholdAlertCard.tsx",
                     "HandoverAckCard.tsx", "AlertLevelCard.tsx"):
            body = self._read(self.COMP + name)
            self.assertRegex(body, re.compile(r"dsmPostOnce\(.*?finally \{\s*await reload\(\)",
                                              re.S), name)

    def test_home_mounts_the_row(self) -> None:
        home = self._read("frontend/src/features/dsm/pages/Home.tsx")
        self.assertIn("<DecisionHandoverRow bucket={bucket} />", home)
