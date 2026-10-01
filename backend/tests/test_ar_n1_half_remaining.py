# -*- coding: utf-8 -*-
"""턴 AR · 차선 N1 — 반쪽 잔여를 세종 결정 번호(WO-21 §5)로 닫는다.

절마다 (a) 누르는 자리를 시험 클라이언트로 두드리고 (b) 같은 GET 을 다시 불러 새 값이
보이는지 잰다(이름은 `client_measured` — 브라우저를 누른 것이 아니다, P-458).

  FWS-F1-12 · F2-15  담당 초소 = 그날 편성표 배정 · 미배정 「대기」 (P-452)
  FWS-F1-02          순찰함 등록 목록 대조 (위조 코드 거절)
  FWS-F2-11          철수 회신 -> 자원 배치판 해제
  O-02               유령 시드 = 삭제가 아니라 표식 · 「표식됨 N」 (P-453)
  O-05               5xx 앞문 응답 카운터 (새 저장소 0)
  DSM-U3-03          사진 축소본(긴 변 <= 640) + 워터마크 (P-451)
  FWS-F4-01          지도 겹침 화면 배선 (P-448)

이 파일은 증거 json 도 사람 표(`.retro.md`)도 쓰지 않는다. 캐시 처리: 우회 —
`FwsHttpTest` 가 `X-No-Cache` 클라이언트를 쓰고 각 시험 `setUp` 에서 `cache.clear()`.
"""
from __future__ import annotations

import io
import zipfile
from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.utils import timezone

from tests.test_api_contract import _bearer
from tests.test_aq_n2_ops_boards import _Fixture as OpsFixture
from tests.test_aq_n3_screens import _src
from tests.test_aq_w2c_command_admin_drone import BOARD, STANDBY, W2cFixture
from tests.test_fws_app import _qs
from tests.test_ops_an import APPS_LIST, HEALTH
from tests.test_p356_u3u6_spec_promotions import (FIELD_PHOTO, SITUATION_DOCX,
                                                   UPLOAD_BYTES, U3AMFixture)

NOTIFY_PREFS = "/api/fws/notify-prefs"
ROSTER = "/api/fws/office/roster"
POSTS = "/api/fws/office/posts"
TRACK = "/api/fws/patrol/track"
NL = chr(10)


def _mission(eid) -> str:
    return f"/api/fws/missions/{eid}/response"


# ═══════════════════════════════════════════════════════════════════════════
# F1-12 · F2-15 담당 초소 = 그날 편성표
# ═══════════════════════════════════════════════════════════════════════════
class DutyPostFromRosterTest(W2cFixture):
    def _upload(self, rows: list[str], head=None) -> None:
        csv_text = NL.join(["name,role,shift_date,shift_type,post_code", *rows])
        r = self.client.post(_qs(ROSTER, csv_text=csv_text), **(head or self.head_a))
        self.assertEqual(200, r.status_code, r.content[:300])

    def test_unassigned_is_waiting_then_roster_assigns_then_refetch_shows_post(self) -> None:
        got = self.get_ok(NOTIFY_PREFS)["duty_post"]
        self.assertEqual("waiting", got["status"], "편성이 없는데 초소가 보인다(지어냄)")
        self.assertIsNone(got["post_code"])

        today = timezone.localtime(timezone.now()).date().isoformat()
        me = self.user_a.username
        # 이름은 있으나 초소 칸이 빈 편성 -> 여전히 대기
        self._upload([f"{me},fire_crew,{today},day,"])
        self.assertEqual("waiting", self.get_ok(NOTIFY_PREFS)["duty_post"]["status"])

        # 다른 날짜의 배정은 오늘의 담당이 아니다
        other_day = (timezone.localtime(timezone.now()) - timedelta(days=3)).date().isoformat()
        self._upload([f"{me},fire_crew,{other_day},day,초소-9"])
        self.assertEqual("waiting", self.get_ok(NOTIFY_PREFS)["duty_post"]["status"])

        # 오늘 배정 -> 재조회에 그 초소
        self._upload([f"{me},fire_crew,{today},day,초소-7"])
        got = self.get_ok(NOTIFY_PREFS)["duty_post"]
        self.assertEqual(("assigned", "초소-7"), (got["status"], got["post_code"]))

        # 다른 기관 사용자는 이 편성을 볼 수 없다
        other = self.get_ok(NOTIFY_PREFS, self._bearer(self.user_b))["duty_post"]
        self.assertEqual("waiting", other["status"])

    def test_screen_shows_waiting_badge_and_duty_post(self) -> None:
        card = _src("features/fws/pages/NotifyPrefsCard.tsx")
        for suffix in ("duty-post", "duty-post-code", "duty-waiting"):
            self.assertIn("gxOf(gxPrefix, '" + suffix + "')", card)
            for pre in ("fws-f1-12-quiet", "fws-f2-15-quiet"):
                self.assertIn("gx: '" + pre + "-" + suffix + "'", card)
        self.assertIn("duty_post", card)


# ═══════════════════════════════════════════════════════════════════════════
# F1-02 순찰함 등록 목록
# ═══════════════════════════════════════════════════════════════════════════
class CheckpointRegistryTest(W2cFixture):
    def test_forged_code_rejected_when_registry_exists_and_registered_counts(self) -> None:
        # 등록이 없으면 대조할 것이 없다 — 막지 않고 empty 로 밝힌다
        r0 = self.post_ok(TRACK, post_code="P-1", checkpoint_code="CHK-ANY")
        self.assertEqual("empty", r0["checkpoint_registry"])

        self.post_ok(POSTS, kind="checkpoint", code="CHK-9", name="능선 순찰함")
        listed = self.get_ok(POSTS + "?kind=checkpoint")
        self.assertEqual(["CHK-9"], [p["code"] for p in listed["posts"]])

        ok = self.post_ok(TRACK, post_code="P-1", checkpoint_code="CHK-9")
        self.assertEqual("matched", ok["checkpoint_registry"])
        before = ok["checkpoint_count"]

        bad = self.client.post(_qs(TRACK, post_code="P-1", checkpoint_code="CHK-FAKE"),
                               **self.head_a)
        self.assertEqual(422, bad.status_code, bad.content[:300])
        cache.clear()
        again = self.client.post(_qs(TRACK, post_code="P-1", checkpoint_code="CHK-9"),
                                 **self.head_a)
        self.assertEqual(before + 1, self._body(again)["checkpoint_count"],
                         "위조 코드가 통과로 셈해졌다")

        # 다른 기관은 이 기관의 등록에 영향받지 않는다(등록 없음 -> empty)
        cache.clear()
        other = self.client.post(_qs(TRACK, post_code="P-1", checkpoint_code="CHK-FAKE"),
                                 **self._bearer(self.user_b))
        self.assertEqual(200, other.status_code, other.content[:300])
        self.assertEqual("empty", self._body(other)["checkpoint_registry"])

    def test_office_screen_offers_checkpoint_kind(self) -> None:
        self.assertIn("fws-f1-02-kind-checkpoint", _src("features/fws/pages/OfficeHome.tsx"))


# ═══════════════════════════════════════════════════════════════════════════
# F2-11 철수 -> 배치판 해제
# ═══════════════════════════════════════════════════════════════════════════
class ReleaseFreesBoardTest(W2cFixture):
    def test_dispatch_deploys_release_frees_and_refetch_shows_it(self) -> None:
        eid = self._event(self.stream_a, severity="critical", event_type="fire",
                          when=timezone.now() - timedelta(minutes=5))
        self.post_ok(STANDBY, status="standby_day", lat=36.4, lng=127.4)
        me = self.user_a.pk

        def person(board):
            return next(p for p in board["standby"]["people"] if p["user_id"] == me)

        b0 = self.get_ok(BOARD)
        self.assertEqual(1, b0["standby"]["on_standby"])
        self.assertIsNone(person(b0)["mission_state"])

        self.post_ok(_mission(eid), action="dispatch")
        self.post_ok(_mission(eid), action="arrived", lat=36.1, lng=127.2)
        b1 = self.get_ok(BOARD)
        self.assertEqual("deployed", person(b1)["mission_state"])
        self.assertEqual(0, b1["standby"]["on_standby"], "출동 중인데 대기 인원에 든다")
        self.assertEqual(1, b1["standby"]["deployed"])

        self.post_ok(_mission(eid), action="released", note="철수")
        b2 = self.get_ok(BOARD)
        p2 = person(b2)
        self.assertEqual("released", p2["mission_state"])
        self.assertIsNotNone(p2["released_at"])
        self.assertEqual(1, b2["standby"]["on_standby"], "철수했는데 배치판이 안 풀렸다")
        self.assertEqual(0, b2["standby"]["deployed"])

        # 사람이 스스로 대기를 다시 등록하면 옛 임무는 지난 일이다
        self.post_ok(STANDBY, status="standby_night")
        self.assertIsNone(person(self.get_ok(BOARD))["mission_state"])

    def test_screen_draws_deployed_and_released_tags(self) -> None:
        cards = _src("features/fws/pages/W2cCommandCards.tsx")
        self.assertIn('data-gx="fws-f2-11-deployed"', cards)
        self.assertIn('data-gx="fws-f2-11-released"', cards)


# ═══════════════════════════════════════════════════════════════════════════
# O-02 표식됨 N · O-05 5xx
# ═══════════════════════════════════════════════════════════════════════════
class MarkedSeedBoardTest(OpsFixture):
    def test_marking_a_row_raises_count_and_never_deletes_it(self) -> None:
        from common.billing_marks import mark_unbillable

        before = self._get(APPS_LIST)
        self.assertIsNotNone(before["marked"], "곁표를 못 읽었다")
        target = self.user_b
        mark_unbillable(target, "probe", reason="AR N1 시험 — 유령 시드 표식")
        after = self._get(APPS_LIST)
        self.assertEqual(before["marked_probe"] + 1, after["marked_probe"])
        self.assertEqual(before["marked"] + 1, after["marked"])
        # 표식은 행을 지우지 않는다 — 가리키는 행은 그대로다
        type(target).objects.get(pk=target.pk)

        mark_unbillable(self.user_a, "seed", reason="AR N1 시험 — 씨앗 표식")
        seeded = self._get(APPS_LIST)
        self.assertEqual(after["marked_seed"] + 1, seeded["marked_seed"])

    def test_screen_shows_marked_count(self) -> None:
        board = _src("features/ops/components/AppsBoard.tsx")
        self.assertIn('data-gx="o-02-marked"', board)
        self.assertIn("board.data?.marked", board)


class FrontDoorFiveXxTest(OpsFixture):
    def test_counter_counts_5xx_and_health_board_reports_it(self) -> None:
        from common import front_door_counter as fd

        base = fd.snapshot()
        fd.record(200)
        fd.record(500)
        fd.record(503)
        now = fd.snapshot()
        self.assertTrue(now["measured"])
        self.assertEqual((base.get("total") or 0) + 3, now["total"])
        self.assertEqual((base.get("5xx") or 0) + 2, now["5xx"])

        body = self._get(HEALTH)
        self.assertIn("front_door", body)
        self.assertTrue(body["front_door"]["measured"])
        self.assertNotIn("5xx", body["not_measured"], "5xx 를 재는데 아직 못 잰다고 적는다")
        self.assertIn("gate_16_colors", body["not_measured"],
                      "16색은 아직 못 쟀다 — 지어내지 않는다")

    def test_middleware_is_registered_outermost_and_screen_draws_it(self) -> None:
        from django.conf import settings

        self.assertEqual("common.front_door_counter.FrontDoorCounterMiddleware",
                         settings.MIDDLEWARE[0])
        board = _src("features/ops/components/HealthBoard.tsx")
        self.assertIn('data-gx="o-05-5xx"', board)
        self.assertIn('data-gx="o-05-5xx-unmeasured"', board)


# ═══════════════════════════════════════════════════════════════════════════
# U3-03 사진 축소본 + 워터마크
# ═══════════════════════════════════════════════════════════════════════════
def _rels(data: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return b"".join(zf.read(n) for n in zf.namelist() if n.endswith(".rels"))


class PhotoThumbnailTest(U3AMFixture):
    @staticmethod
    def _jpeg():
        from django.core.files.uploadedfile import SimpleUploadedFile

        head = bytes([0xFF, 0xD8, 0xFF, 0xE0])
        return SimpleUploadedFile("scene.jpg", head + b"not-a-real-jpeg-but-bytes",
                                  content_type="image/jpeg")

    @staticmethod
    def _big_jpeg() -> bytes:
        from PIL import Image

        img = Image.new("RGB", (2400, 1500), (30, 120, 60))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=92)
        return out.getvalue()

    def test_thumbnail_long_side_and_watermark_are_applied(self) -> None:
        from PIL import Image

        from apps.dsm import photo_thumb

        raw = self._big_jpeg()
        at = timezone.now()
        jpg = photo_thumb.make_thumbnail(raw, org="테스트기관", case_no=4321, at=at)
        img = Image.open(io.BytesIO(jpg))
        self.assertLessEqual(max(img.size), 640)
        self.assertEqual((640, 400), img.size)
        # 워터마크 띠: 아래쪽 띠가 위쪽 본문보다 어둡다(반투명 검정 + 글자)
        top = img.getpixel((img.width // 2, 20))
        band = img.getpixel((img.width - 4, img.height - 4))
        self.assertLess(sum(band), sum(top))
        self.assertNotIn(b"Exif", jpg[:64], "메타데이터가 딸려 왔다")
        text = photo_thumb.watermark_text(org="테스트기관", case_no=4321, at=at)
        for part in ("테스트기관", "4321", at.strftime("%Y-%m-%d %H:%M")):
            self.assertIn(part, text)

    def test_report_embeds_thumbnail_without_original_link_or_hash(self) -> None:
        from PIL import Image

        from apps.dsm import photo_thumb

        event_id = self._event(self.stream_a)
        with mock.patch(UPLOAD_BYTES, return_value="dsm-bucket/field-photos/ar-n1.jpg"):
            up = self.client.post(FIELD_PHOTO.format(event_id), {"photo": self._jpeg()},
                                  **_bearer(self.user_a))
        self.assertEqual(200, up.status_code, up.content[:300])
        cache.clear()
        with mock.patch.object(photo_thumb, "_read_original", return_value=self._big_jpeg()):
            resp = self.client.get(SITUATION_DOCX.format(event_id),
                                   **_bearer(self.manager_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            doc = zf.read("word/document.xml").decode("utf-8", "replace")
            media = [n for n in zf.namelist() if n.startswith("word/media/")]
            self.assertEqual(1, len(media), "축소본 그림이 문서에 없다")
            pic = Image.open(io.BytesIO(zf.read(media[0])))
            everything = b"".join(zf.read(n) for n in zf.namelist())
        self.assertLessEqual(max(pic.size), 640)
        self.assertIn("1장 중 1장의 축소본을 실었습니다", doc)
        self.assertNotIn(b"field-photos", everything, "원본 객체 키가 문서에 샜다")
        self.assertNotIn(b"ar-n1.jpg", everything)
        self.assertNotIn(b"sha256", everything)
        self.assertNotIn(b"External", _rels(resp.content), "원본으로 가는 바깥 링크가 있다")
        self.assertNotIn(b"hyperlink", _rels(resp.content))

    def test_without_storage_the_paper_keeps_count_only(self) -> None:
        from apps.dsm import photo_thumb

        event_id = self._event(self.stream_a)
        with mock.patch(UPLOAD_BYTES, return_value="dsm-bucket/field-photos/ar-n1b.jpg"):
            self.client.post(FIELD_PHOTO.format(event_id), {"photo": self._jpeg()},
                             **_bearer(self.user_a))
        cache.clear()
        with mock.patch.object(photo_thumb, "_read_original", return_value=None):
            resp = self.client.get(SITUATION_DOCX.format(event_id),
                                   **_bearer(self.manager_a))
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            doc = zf.read("word/document.xml").decode("utf-8", "replace")
            self.assertEqual([], [n for n in zf.namelist() if n.startswith("word/media/")])
        self.assertIn("1장이 이 사건에 자동 첨부되었습니다", doc)


# ═══════════════════════════════════════════════════════════════════════════
# F4-01 지도 겹침 — 화면 배선 (정적 대조) + 뒷받침 문
# ═══════════════════════════════════════════════════════════════════════════
class MapOverlayWiringTest(W2cFixture):
    def test_card_uses_existing_map_and_rereads_both_sources(self) -> None:
        card = _src("features/fws/pages/IncidentMapOverlayCard.tsx")
        self.assertIn("from '../../../components/maps'", card)
        for gx in ("fws-f4-01-map", "fws-f4-01-map-refresh", "fws-f4-01-map-recon",
                   "fws-f4-01-map-spread", "fws-f4-01-map-evac"):
            self.assertIn(f'data-gx="{gx}"', card)
        self.assertIn("/api/fws/ap/drone/missions/", card)
        self.assertIn("/api/fws/ap/incidents/", card)
        self.assertIn("<IncidentMapOverlayCard", _src("features/fws/pages/CommandHome.tsx"))

    def test_backing_endpoints_answer_for_the_card(self) -> None:
        eid = self._event(self.stream_a, severity="critical", event_type="fire")
        rc = self.get_ok(f"/api/fws/ap/drone/missions/{eid}/recon-coords")
        self.assertEqual(eid, rc["event_id"])
        sp = self.get_ok(f"/api/fws/ap/incidents/{eid}/spread-results")
        self.assertIn("results", sp)
