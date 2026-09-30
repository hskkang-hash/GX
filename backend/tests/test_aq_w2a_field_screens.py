# -*- coding: utf-8 -*-
"""턴 AQ · 2물결 차선 W2A — 감시원(F1)·진화대(F2) 화면 배선의 **누른 뒤 재조회** 실측.

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`X-No-Cache`) 헤더를 모든 요청에 싣고(화면의
  `fwsGetFresh` 와 같은 규약), `setUp`·`tearDown` 에서 `cache.clear()` 로 멱등 캐시를 비운다.
  이 파일은 새 캐시를 만들지 않는다(D-341).

절마다 셋을 잰다 — ① 누른다(POST) → 새 GET 으로 재조회해 바뀐 값이 보인다 ② 테넌트
격리(남의 것은 404 · 남의 실적에 안 섞인다) ③ 화면 정적 대조(`data-gx` 이름과 부르는
경로가 **글자 그대로** 화면 파일에 있다).

★ 이 파일은 `docs/agent/evidence/SPEC/*.json`·`.retro.md` 를 쓰지 않는다(P-431 — 표는 손으로만).
"""
from __future__ import annotations

import contextlib
import csv
import io
from pathlib import Path
from unittest import mock
from urllib.parse import urlencode

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import timezone as dj_timezone

from tests.no_cache import NO_CACHE
from tests.test_fws_app import FwsHttpTest

PATROL_CHECKIN = "/api/fws/patrol/checkin"
PATROL_TRACK = "/api/fws/patrol/track"
PATROL_MINE = "/api/fws/patrol/mine"
MISSIONS_MINE = "/api/fws/missions/mine"
MISSIONS_EXPORT = "/api/fws/missions/mine/export"
UPLOAD_BYTES = "apps.dsm.field._upload_bytes"


def _qs(path: str, **params) -> str:
    live = {k: v for k, v in params.items() if v is not None}
    return f"{path}?{urlencode(live)}" if live else path


def _frontend_src() -> Path | None:
    for base in (Path("/repo/frontend/src"),
                 *(p / "frontend" / "src" for p in Path(__file__).resolve().parents)):
        if base.is_dir():
            return base
    return None


class W2aHttpTest(FwsHttpTest):
    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().setUpTestData()

    def setUp(self) -> None:
        cache.clear()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def tearDown(self) -> None:
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        cache.clear()

    def _screen(self, rel: str) -> str:
        src = _frontend_src()
        self.assertIsNotNone(src, "frontend/src 를 못 찾았다 — 판정 불가를 초록으로 두지 않는다")
        return (src / rel).read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F1-11 내 근무 기록·순찰 실적(일·주) — 화면 표
# ═══════════════════════════════════════════════════════════════════════════
class F1_11_PatrolMineScreenTest(W2aHttpTest):
    def test_checkin_then_refetch_shows_in_today_and_week_row(self) -> None:
        head = self._bearer(self.user_a)
        before = self._body(self.client.get(PATROL_MINE, **head))
        self.assertEqual(0, before["today"]["checkins"])

        r = self.client.post(_qs(PATROL_CHECKIN, post_code="P-1", method="gps"), **head)
        self.assertEqual(200, r.status_code, r.content)

        after = self.client.get(PATROL_MINE, **head)
        self.assertEqual(200, after.status_code)
        body = self._body(after)
        self.assertEqual(1, body["today"]["checkins"])
        self.assertEqual(1, body["week"]["checkins"])

    def test_other_tenant_record_does_not_enter_my_table(self) -> None:
        r = self.client.post(_qs(PATROL_CHECKIN, post_code="P-1", method="gps"),
                             **self._bearer(self.user_a))
        self.assertEqual(200, r.status_code, r.content)
        other = self._body(self.client.get(PATROL_MINE, **self._bearer(self.user_b)))
        self.assertEqual({"checkins": 0, "tracks": 0, "checkpoints": 0}, other["today"])

    def test_screen_draws_the_table_from_patrol_mine(self) -> None:
        cards = self._screen("features/fws/pages/PatrolW2aCards.tsx")
        home = self._screen("features/fws/pages/PatrolHome.tsx")
        self.assertIn('data-gx="fws-f1-11-table"', cards)
        self.assertIn('data-gx="fws-f1-11-refresh"', cards)
        self.assertIn("fwsGetFresh<PatrolMine>(fwsEndpoint.patrolMine)", cards)
        self.assertIn("<PatrolW2aCards refreshKey={mineKey} />", home)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F1-02 순찰 경로 기록 — 화면 버튼(GPS 트랙 · 순찰함 번호)
# ═══════════════════════════════════════════════════════════════════════════
class F1_02_TrackScreenTest(W2aHttpTest):
    def test_gps_and_checkpoint_press_then_refetch_mine(self) -> None:
        head = self._bearer(self.user_a)
        r1 = self.client.post(_qs(PATROL_TRACK, post_code="P-1", lat=36.1, lng=127.1), **head)
        self.assertEqual(200, r1.status_code, r1.content)
        r2 = self.client.post(_qs(PATROL_TRACK, post_code="P-1", checkpoint_code="CHK-1"),
                              **head)
        self.assertEqual(200, r2.status_code, r2.content)
        today = self._body(self.client.get(PATROL_MINE, **head))["today"]
        self.assertEqual(1, today["tracks"])
        self.assertEqual(1, today["checkpoints"])
        other = self._body(self.client.get(PATROL_MINE, **self._bearer(self.user_b)))["today"]
        self.assertEqual(0, other["tracks"])

    def test_screen_sends_track_and_refetches(self) -> None:
        cards = self._screen("features/fws/pages/PatrolW2aCards.tsx")
        for gx in ('data-gx="fws-f1-02-gps"', 'data-gx="fws-f1-02-checkpoint"',
                   'data-gx="fws-f1-02-checkpoint-code"', 'data-gx="fws-f1-02-post"'):
            self.assertIn(gx, cards)
        self.assertIn("fwsEndpoint.patrolTrack", cards)
        self.assertIn("await onSaved();", cards)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F1-06 현장 확인 회신 — 「접근 불가」 · 사진 1장
# ═══════════════════════════════════════════════════════════════════════════
class F1_06_ReplyScreenTest(W2aHttpTest):
    def _upload(self, head, event_id) -> int:
        photo = SimpleUploadedFile("p.jpg", b"\xff\xd8\xff" + b"0" * 64,
                                   content_type="image/jpeg")
        with mock.patch(UPLOAD_BYTES, return_value="bucket/field-photos/x.jpg"):
            resp = self.client.post(f"/api/dsm/events/{event_id}/field-photo",
                                    {"photo": photo}, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        body = self._body(resp)
        return (body.get("data") or body)["photo_id"]

    def test_cannot_access_with_photo_then_refetch_shows_reply(self) -> None:
        event_id = self._event(self.stream_a)
        head = self._bearer(self.user_a)
        photo_id = self._upload(head, event_id)

        path = f"/api/fws/verifications/{event_id}/reply"
        resp = self.client.post(_qs(path, result="cannot_access", photo_id=photo_id), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertIsNone(self._body(resp)["verdict"], "접근 불가가 판정을 바꿨다")
        self.assertEqual(photo_id, self._body(resp)["photo_id"])

        again = self.client.get(f"/api/fws/verifications/{event_id}", **head)
        self.assertEqual(200, again.status_code, again.content)
        body = self._body(again)
        self.assertIsNone(body["verdict"])
        self.assertEqual("cannot_access", body["replies"][0]["result"])
        self.assertEqual(photo_id, body["replies"][0]["photo_id"])

    def test_photo_of_another_event_is_422(self) -> None:
        e1 = self._event(self.stream_a)
        e2 = self._event(self.stream_a)
        head = self._bearer(self.user_a)
        photo_id = self._upload(head, e2)
        resp = self.client.post(
            _qs(f"/api/fws/verifications/{e1}/reply", result="cannot_access",
                photo_id=photo_id), **head)
        self.assertEqual(422, resp.status_code, resp.content)

    def test_other_tenant_cannot_read_or_reply(self) -> None:
        event_id = self._event(self.stream_a)
        head_b = self._bearer(self.user_b)
        self.assertEqual(404, self.client.get(
            f"/api/fws/verifications/{event_id}", **head_b).status_code)
        self.assertEqual(404, self.client.post(
            _qs(f"/api/fws/verifications/{event_id}/reply", result="cannot_access"),
            **head_b).status_code)

    def test_screen_offers_cannot_access_and_photo(self) -> None:
        cards = self._screen("features/fws/pages/PatrolW2aCards.tsx")
        for gx in ('data-gx="fws-f1-06-cannot-access"', 'data-gx="fws-f1-06-photo"',
                   'data-gx="fws-f1-06-replies"', 'data-gx="fws-f1-06-verdict"'):
            self.assertIn(gx, cards)
        self.assertIn("reply('cannot_access')", cards)
        self.assertIn("uploadFieldPhoto(item.verification_id, photo)", cards)
        self.assertIn("await load(String(item.verification_id));", cards)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F2-03 이동 중 회신
# ═══════════════════════════════════════════════════════════════════════════
class F2_03_EnRouteScreenTest(W2aHttpTest):
    def test_dispatch_en_route_then_refetch_shows_my_progress(self) -> None:
        event_id = self._event(self.stream_a)
        head = self._bearer(self.user_a)
        path = f"/api/fws/missions/{event_id}/response"
        self.assertEqual(200, self.client.post(_qs(path, action="dispatch"), **head).status_code)
        resp = self.client.post(_qs(path, action="en_route", lat=36.2, lng=127.3), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertFalse(self._body(resp)["event_advanced"])

        detail = self._body(self.client.get(f"/api/fws/missions/{event_id}", **head))
        self.assertEqual("en_route", detail["my_progress"])
        self.assertEqual("acknowledged", detail["response_state"],
                         "이동 회신이 사건 상태를 옮겼다(K1 에 이동 칸은 없다)")
        mine = self._body(self.client.get(MISSIONS_MINE, **head))
        self.assertIsNotNone(mine["missions"][0]["en_route_at"])

    def test_en_route_without_dispatch_is_409(self) -> None:
        event_id = self._event(self.stream_a)
        resp = self.client.post(
            _qs(f"/api/fws/missions/{event_id}/response", action="en_route"),
            **self._bearer(self.user_a))
        self.assertEqual(409, resp.status_code, resp.content)

    def test_other_tenant_en_route_is_404(self) -> None:
        event_id = self._event(self.stream_a)
        resp = self.client.post(
            _qs(f"/api/fws/missions/{event_id}/response", action="en_route"),
            **self._bearer(self.user_b))
        self.assertEqual(404, resp.status_code, resp.content)

    def test_screen_has_en_route_button_and_progress(self) -> None:
        home = self._screen("features/fws/pages/FieldHome.tsx")
        self.assertIn('data-gx="fws-f2-03-en-route"', home)
        self.assertIn('data-gx="fws-f2-03-progress"', home)
        self.assertIn("handleMissionAction('en_route')", home)
        self.assertIn("fwsGetFresh<MissionDetail>(fwsEndpoint.mission(missionId))", home)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F2-12 내 임무 이력 · 투입 시간 CSV
# ═══════════════════════════════════════════════════════════════════════════
class F2_12_CsvScreenTest(W2aHttpTest):
    def _full_chain(self, user, event_id) -> None:
        head = self._bearer(user)
        path = f"/api/fws/missions/{event_id}/response"
        for action in ("dispatch", "arrived", "released"):
            r = self.client.post(_qs(path, action=action), **head)
            self.assertEqual(200, r.status_code, r.content)

    def test_export_matches_mine_after_release(self) -> None:
        event_id = self._event(self.stream_a)
        self._full_chain(self.user_a, event_id)
        head = self._bearer(self.user_a)
        resp = self.client.get(MISSIONS_EXPORT, **head)
        self.assertEqual(200, resp.status_code, resp.content)
        self.assertIn("text/csv", resp["Content-Type"])
        rows = list(csv.reader(io.StringIO(resp.content.decode("utf-8"))))
        self.assertEqual(["mission_id", "dispatched_at", "en_route_at", "arrived_at",
                          "released_at", "duration_minutes"], rows[0])
        self.assertEqual(str(event_id), rows[1][0])
        mine = self._body(self.client.get(MISSIONS_MINE, **head))
        self.assertEqual(1, mine["count"])
        self.assertEqual(["total", "", "", "", "", str(mine["total_minutes"])], rows[-1])

    def test_other_tenant_export_has_no_rows_of_mine(self) -> None:
        event_id = self._event(self.stream_a)
        self._full_chain(self.user_a, event_id)
        resp = self.client.get(MISSIONS_EXPORT, **self._bearer(self.user_b))
        self.assertEqual(200, resp.status_code, resp.content)
        rows = list(csv.reader(io.StringIO(resp.content.decode("utf-8"))))
        self.assertEqual(2, len(rows), "남의 임무가 내 CSV 에 섞였다")

    def test_screen_has_csv_button(self) -> None:
        home = self._screen("features/fws/pages/FieldHome.tsx")
        api = self._screen("features/fws/api_w2a.ts")
        self.assertIn('data-gx="fws-f2-12-csv"', home)
        self.assertIn('data-gx="fws-f2-12-table"', home)
        self.assertIn("await downloadMyMissionsCsv();\n      await reload();", home)
        self.assertIn("'/api/fws/missions/mine/export'", api)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F2-13 훈련 임무 수신 — 임무 화면에 훈련 배지
# ═══════════════════════════════════════════════════════════════════════════
class F2_13_TrainingMissionScreenTest(W2aHttpTest):
    def test_event_inside_drill_window_carries_training_badge(self) -> None:
        from apps.dsm.services import set_drill_mode

        live_id = self._event(self.stream_a)
        set_drill_mode(scope=self.scope_a, enabled=True, reason="시험 훈련 창")
        drill_id = self._event(self.stream_a, when=dj_timezone.now())
        head = self._bearer(self.user_a)

        drill = self._body(self.client.get(f"/api/fws/missions/{drill_id}", **head))
        self.assertEqual("drill", drill["data_source"])
        self.assertEqual("훈련", drill["training_badge"])
        live = self._body(self.client.get(f"/api/fws/missions/{live_id}", **head))
        self.assertIsNone(live["training_badge"], "훈련 전 사건에 훈련 배지가 붙었다")

        badge = self._body(self.client.get("/api/fws/training/mission", **head))
        self.assertEqual(0, badge["real_channel_sends"])

    def test_other_tenant_training_mission_is_404(self) -> None:
        from apps.dsm.services import set_drill_mode

        set_drill_mode(scope=self.scope_a, enabled=True, reason="시험 훈련 창")
        drill_id = self._event(self.stream_a, when=dj_timezone.now())
        resp = self.client.get(f"/api/fws/missions/{drill_id}", **self._bearer(self.user_b))
        self.assertEqual(404, resp.status_code)

    def test_screen_draws_badge_on_mission_card(self) -> None:
        home = self._screen("features/fws/pages/FieldHome.tsx")
        self.assertIn('data-gx="fws-f2-13-mission-badge"', home)
        self.assertIn("mission.training_badge &&", home)
