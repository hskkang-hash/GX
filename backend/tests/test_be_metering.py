# -*- coding: utf-8 -*-
"""OPS-16 — **이번 달 사용량** (계량 · 2026-09-05 · 차선 E).

이 파일이 묻는 것 다섯
----------------------
① **다섯 칸이 다 있는가** — 카메라 대수 · 쓰는 사람 수 · 이벤트 수 · 보낸 알림 수 ·
   저장 용량. 하나라도 없으면 청구서에 빈 줄이 생긴다.
② **테넌트 격리** — A 의 사용량에 B 의 수가 섞이지 않는다. 남의 카메라 대수는
   남의 사업 규모다. 섞이면 그것은 틀린 청구서가 아니라 **유출**이다.
③ ★ **지운 카메라는 청구하지 않는다.** dj-core 의 소프트 삭제는 평범한 조회에서
   행을 남긴다 [실측 core/base.py:2082 · retention.py §3]. 그것을 그대로 세면
   고객은 지웠다고 알고 있는데 우리는 돈을 받는다.
④ ★ **수를 만들지 않는다** — 계량이 이벤트를 새로 만들면 그 수로 청구하게 된다.
   부르기 전후로 행 수가 **한 건도** 달라지지 않아야 한다.
⑤ **못 잰 칸은 0이 아니다** — 빈 칸으로 나가고, CSV 도 빈 칸으로 적는다.

낱말은 `docs/design/GX-COPY_v1.md` §5 가 정본이다 — 이 시험이 그 글자를 잰다.
"""
from datetime import timedelta

from django.apps import apps
from django.utils import timezone

from tests.test_dsm_app import DsmFixture

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "apps.dsm.metering · stream_monitors.StreamMonitor · "
    "stream_monitors.DetectionEvent · stream_monitors.DeliveryRecord · "
    "file_management.UserMediaFile · user.CoreUser — 저장소의 실제 모듈과 표"
)

#: GX-COPY §5 「2026-09-05 턴 E 추가」의 글자 그대로. **여기서 새 말을 만들지 않는다.**
COPY = ("이번 달 사용량", "카메라 대수", "쓰는 사람 수", "이벤트 수",
        "보낸 알림 수", "저장 용량")


class MeteringFixture(DsmFixture):
    def setUp(self):
        self.now = timezone.localtime()
        self.month = self.now.strftime("%Y-%m")


class TheFiveCellsExistTest(MeteringFixture):
    """① 다섯 칸이 다 있고, **화면의 말로** 있다."""

    def test_five_cells_with_the_agreed_words(self):
        from apps.dsm.metering import usage

        got = usage(scope=self.scope_a, month=self.month)
        self.assertEqual(got["title"], COPY[0])
        labels = [c["label"] for c in got["cells"]]
        self.assertEqual(labels, list(COPY[1:]),
                         "화면의 말이 GX-COPY §5 와 다르다 — 두 벌이 되면 화면과 "
                         "청구서가 다른 말을 한다")

    def test_every_cell_says_whether_it_was_measured(self):
        """**「못 쟀다」와 「0」을 화면이 가를 수 있어야 한다** (DA-03 §2-5)."""
        from apps.dsm.metering import usage

        for cell in usage(scope=self.scope_a, month=self.month)["cells"]:
            self.assertIn(cell["state"], ("ok", "unknown"))
            if cell["value"] is None:
                self.assertEqual(cell["state"], "unknown")

    def test_the_definitions_travel_with_the_numbers(self):
        """정의 없는 수는 **다시 셀 수 없고**, 다시 못 세는 수는 다툼이 된다."""
        from apps.dsm.metering import ORDER, usage

        got = usage(scope=self.scope_a, month=self.month)
        for key in ORDER:
            self.assertTrue(got["definitions"].get(key),
                            f"{key} 의 정의가 응답에 없다")


class ItCountsTheRightRowsTest(MeteringFixture):
    """세는 것이 맞는가 — 이벤트 · 알림 · 카메라."""

    def test_events_are_counted_in_the_month_they_happened(self):
        from apps.dsm.metering import usage

        before = usage(scope=self.scope_a, month=self.month)
        n0 = next(c for c in before["cells"] if c["key"] == "events")["value"]
        self._event(self.stream_a)
        after = usage(scope=self.scope_a, month=self.month)
        n1 = next(c for c in after["cells"] if c["key"] == "events")["value"]
        self.assertEqual(n1, n0 + 1)

    def test_a_last_month_event_is_not_in_this_month(self):
        """★ 음성 대조 — 지난 달 이벤트가 이번 달 청구서에 오르면 안 된다."""
        from apps.dsm.metering import usage

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        event_id = self._event(self.stream_a)
        before = usage(scope=self.scope_a, month=self.month)
        n0 = next(c for c in before["cells"] if c["key"] == "events")["value"]
        Event._base_manager.filter(pk=event_id).update(
            occurred_at=timezone.now() - timedelta(days=45))
        after = usage(scope=self.scope_a, month=self.month)
        n1 = next(c for c in after["cells"] if c["key"] == "events")["value"]
        self.assertEqual(n1, n0 - 1,
                         "45일 전 이벤트가 아직 이번 달에 세어진다")

    def test_a_failed_notification_is_not_a_sent_notification(self):
        """★ 실패한 발송에 돈을 받지 않는다."""
        from apps.dsm.metering import usage

        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        event_id = self._event(self.stream_a)
        now = timezone.now()
        ok = Delivery._base_manager.create(
            event_id=event_id, channel="email", occurred_at=now,
            sent_at=now, succeeded=True, recipient_address="a@test.invalid")
        bad = Delivery._base_manager.create(
            event_id=event_id, channel="email", occurred_at=now,
            sent_at=None, succeeded=False, recipient_address="b@test.invalid")
        for row in (ok, bad):
            row.group = self.group_a
            row.save(update_fields=["group"])

        got = usage(scope=self.scope_a, month=self.month)
        sent = next(c for c in got["cells"]
                    if c["key"] == "notifications")["value"]
        self.assertEqual(sent, 1, "실패한 발송까지 「보낸 알림」으로 셌다")
        self.assertGreaterEqual(got["notifications_failed"], 1,
                                "실패 건수가 아예 안 보인다 — 조용한 실패다")

    def test_a_soft_deleted_camera_is_not_billed(self):
        """③ ★ **지운 카메라를 청구서에 올리지 않는다.**

        `delete()` 는 행을 남긴다(출생 표본 · test_be_purge 머리말). 그 사실을
        모르는 셈은 고객이 지운 카메라에 계속 값을 매긴다.
        """
        from apps.dsm.metering import usage

        Stream = apps.get_model("stream_monitors", "StreamMonitor")
        extra = Stream._base_manager.create(
            name="곧 지울 카메라", code="gone", ip_source="rtsp://x.invalid/1")
        extra.group = self.group_a
        extra.save(update_fields=["group"])

        before = usage(scope=self.scope_a, month=self.month)
        n0 = next(c for c in before["cells"] if c["key"] == "cameras")["value"]
        extra.delete()
        #: 소프트 삭제라 행은 남아 있다 — 그 사실을 먼저 확인한다.
        self.assertTrue(Stream._base_manager.filter(pk=extra.pk).exists())
        after = usage(scope=self.scope_a, month=self.month)
        n1 = next(c for c in after["cells"] if c["key"] == "cameras")["value"]
        self.assertEqual(n1, n0 - 1,
                         "★ 지운 카메라가 아직 청구서에 있다 — 고객은 지웠다고 "
                         "알고 있고 우리는 돈을 받는다")


class TenantIsolationTest(MeteringFixture):
    """② 남의 테넌트 수가 **섞이지 않는다.**"""

    def test_bs_events_do_not_appear_in_as_bill(self):
        from apps.dsm.metering import usage

        before = usage(scope=self.scope_a, month=self.month)
        n0 = next(c for c in before["cells"] if c["key"] == "events")["value"]
        self._event(self.stream_b)                      # ★ B 의 이벤트
        after = usage(scope=self.scope_a, month=self.month)
        n1 = next(c for c in after["cells"] if c["key"] == "events")["value"]
        self.assertEqual(n1, n0, "★ 남의 테넌트 이벤트가 내 청구서에 올랐다")

    def test_each_tenant_sees_its_own_name(self):
        from apps.dsm.metering import usage

        self.assertEqual(usage(scope=self.scope_a, month=self.month)["tenant_id"],
                         self.group_a.pk)
        self.assertEqual(usage(scope=self.scope_b, month=self.month)["tenant_id"],
                         self.group_b.pk)

    def test_a_system_scope_cannot_read_usage(self):
        """사람이 없는 호출은 **사용량을 못 읽는다** (D-281)."""
        from common.tenant_scope import SystemScopeCannotRead

        from apps.dsm.metering import usage

        with self.assertRaises(SystemScopeCannotRead):
            usage(scope=self.scope_pipe, month=self.month)


class ItDoesNotMakeNumbersTest(MeteringFixture):
    """④ ★ **수는 세는 것이지 만드는 것이 아니다.**"""

    def test_reading_usage_creates_no_rows(self):
        from apps.dsm.metering import usage, usage_csv

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        Stream = apps.get_model("stream_monitors", "StreamMonitor")
        AuditLogs = apps.get_model("logger", "AuditLogs")

        def snapshot():
            return tuple(m._base_manager.count()
                         for m in (Event, Delivery, Stream, AuditLogs))

        before = snapshot()
        usage(scope=self.scope_a, month=self.month)
        usage_csv(scope=self.scope_a, months=3)
        self.assertEqual(snapshot(), before,
                         "★ 계량이 행을 만들었다 — 그 수로 청구하게 된다")


class TheTableDownloadsTest(MeteringFixture):
    """⑤ **표 내려받기** — 머리글이 화면의 말이고, 못 잰 칸은 빈 칸이다."""

    def test_the_csv_header_uses_the_screen_words(self):
        from apps.dsm.metering import usage_csv

        text = usage_csv(scope=self.scope_a, months=2)
        header = text.splitlines()[0]
        for word in COPY[1:]:
            self.assertIn(word, header)

    def test_the_csv_has_one_row_per_month(self):
        from apps.dsm.metering import usage_csv

        lines = [ln for ln in usage_csv(scope=self.scope_a, months=3).splitlines()
                 if ln.strip()]
        self.assertEqual(len(lines), 4, "머리글 1 + 달 3 이 아니다")

    def test_an_unmeasured_cell_is_blank_not_zero(self):
        """못 잰 칸을 0으로 적으면 표계산기가 그것을 **0으로 더한다.**"""
        from unittest.mock import patch

        from apps.dsm import metering

        with patch.object(metering, "_storage",
                          return_value={"bytes": None, "files": None,
                                        "unsized": None, "why": "못 쟀다"}):
            got = metering.usage(scope=self.scope_a, month=self.month)
            cell = next(c for c in got["cells"] if c["key"] == "storage")
            self.assertIsNone(cell["value"])
            self.assertEqual(cell["state"], "unknown")

            text = metering.usage_csv(scope=self.scope_a, months=1)
        row = text.splitlines()[1]
        self.assertTrue(row.endswith(","),
                        "못 잰 저장 용량이 0 으로 적혔다 — 「안 썼다」가 됐다")


class TheMonthBoundaryTest(MeteringFixture):
    """달의 경계는 **한 곳에서만** 정한다."""

    def test_the_period_is_half_open(self):
        from apps.dsm.metering import month_bounds

        start, end = month_bounds("2026-01")
        self.assertEqual((start.year, start.month, start.day), (2026, 1, 1))
        self.assertEqual((end.year, end.month, end.day), (2026, 2, 1))

    def test_december_rolls_into_next_january(self):
        from apps.dsm.metering import month_bounds

        _, end = month_bounds("2026-12")
        self.assertEqual((end.year, end.month), (2027, 1))

    def test_a_broken_month_is_a_value_error_not_a_guess(self):
        from apps.dsm.metering import month_bounds

        for bad in ("2026-13", "올해", "2026-00"):
            with self.assertRaises(ValueError):
                month_bounds(bad)


# ═══════════════════════════════════════════════════════════════════════════
# 문 — **문지기 없는 새 경로를 만들지 않는다** (D-275 §5-1)
#
# 캐시 처리: 우회 — `X-No-Cache`(`tests.no_cache.NO_CACHE`). 사용량은 **지금의 수**여야
# 하고, 적중한 본문은 언제나 200 이다(P-19). 캐시를 재면 문지기를 안 재게 된다.
# ═══════════════════════════════════════════════════════════════════════════
class MeteringDoorIsGuardedTest(DsmFixture):
    """★ 이 시험이 **화면이 처음 뜨는 순간**을 대신 잰다 (D-378).

    단위 시험은 `usage()` 를 직접 부른다. 라우트가 질의 인자를 만드는 순간에
    죽는 결함(미래 임포트 · 스키마)은 그 길로는 절대 안 잡힌다 — 화면을 띄운
    그날에 나온다. 그래서 여기서 **문을 두드린다.**
    """

    PATHS = ("/api/dsm/metering", "/api/dsm/metering/series",
             "/api/dsm/metering/csv")

    def setUp(self):
        from django.test import Client

        from tests.no_cache import NO_CACHE

        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def test_anonymous_gets_no_usage(self):
        """익명에게는 **200 이 아니다.** 남의 사용량은 남의 사업 규모다."""
        for path in self.PATHS:
            resp = self.client.get(path)
            self.assertEqual(
                401, resp.status_code,
                f"익명이 {path} 를 {resp.status_code} 로 받았다")

    def test_every_metering_door_is_in_the_route_ledger_with_both_guards(self):
        """대장에 이름으로 남는다 — 인증과 테넌트 문지기 **둘 다.**"""
        from common.tenant_scope import enumerate_operations

        ledger = {(r.path, r.method): r for r in enumerate_operations()}
        for path in self.PATHS:
            row = ledger.get((path, "GET"))
            self.assertIsNotNone(row, f"{path} 가 라우트 대장에 없다")
            self.assertTrue(row.has_auth, f"{path} 는 인증 없는 진입면이다")
            self.assertIsNotNone(row.scope,
                                 f"{path} 에 테넌트 문지기가 없다")

    def _bearer(self, user):
        """이 사용자의 접근 토큰 하나. **세션까지 묶는다.**

        ★ `force_login` 은 이 문에 안 통한다 [실측 2026-09-05 · 401]. 이 라우트의
          문지기는 `JwtOrInboundKey` 이고 세션 쿠키를 안 본다. 그리고 dj-core 는
          `user.token` 을 보므로 **세션을 안 묶으면 토큰이 있어도 401** 이다
          (`tests/test_s_session_limit._session_token` 과 같은 모양 · 게이트 메모).
        """
        import jwt as pyjwt
        from django.conf import settings
        from ninja_jwt.tokens import RefreshToken

        session_id = "gx-ops16-test"
        refresh = RefreshToken.for_user(user)
        refresh["session_id"] = session_id
        access = str(refresh.access_token)
        decoded = pyjwt.decode(
            access, settings.NINJA_JWT["SIGNING_KEY"],
            algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")])
        user.set_encrypted_session_token(session_id, decoded.get("jti"))
        user.save()
        return f"Bearer {access}"

    def test_the_signed_in_admin_gets_the_five_cells_over_http(self):
        """★ **문으로 들어온 응답**에 다섯 칸이 있다. 500 이면 여기서 빨개진다."""
        import json

        resp = self.client.get(
            "/api/dsm/metering",
            HTTP_AUTHORIZATION=self._bearer(self.user_a),
            **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(200, resp.status_code,
                         (resp.content or b"")[:400].decode("utf-8", "replace"))
        body = json.loads(resp.content.decode("utf-8"))
        self.assertEqual([c["label"] for c in body["cells"]], list(COPY[1:]))

    def test_the_table_download_is_a_csv_with_a_bom(self):
        """엑셀이 한글 머리글을 안 깨뜨리게 **BOM 이 앞에 있다.**"""
        resp = self.client.get(
            "/api/dsm/metering/csv",
            HTTP_AUTHORIZATION=self._bearer(self.user_a),
            **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(200, resp.status_code,
                         (resp.content or b"")[:400].decode("utf-8", "replace"))
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertTrue(resp.content.startswith("\ufeff".encode("utf-8")),
                        "BOM 이 없다 — 엑셀이 한글 머리글을 깨뜨려 연다")
