# -*- coding: utf-8 -*-
"""P-25 스냅샷 바이트 라우트 — **규약 넷** (2026-09-24).

    ① 익명은 401 — 인증 없이 프레임 1장도 나가지 않는다
    ② 남의 테넌트는 404 — 403 이 아니다. 존재 여부가 새는 것도 누출이다 (D-269)
    ③ 나가는 바이트에는 **소인**이 있다 — 테넌트명과 시각. 저장은 못 막고 출처는 남긴다
    ④ `inline` 이지 `attachment` 가 아니다 — 후자는 「파일로 받으라」이고 반출의 모양이다

왜 이 라우트를 냈나 (지시서 §1 P-25)
------------------------------------
화면은 스냅샷을 **이미 그리고 있다.** 없던 것은 그 그림의 바이트를 인증 뒤에서
내려 줄 문 하나였고, 그 자리를 무계정 링크(서명 URL)로 메우지 않았다 —
계정 없이 열리는 링크는 한 번 새면 회수할 수 없다.

★ 규약을 **이름으로** 잠근다 (D-285 ② · test_clip_playback 과 같은 형)
넷 중 하나가 지워지면 `test_the_four_rules_are_all_present` 가 먼저 멈춘다.
지워진 시험은 지워진 것이 보이지 않는다.
"""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
from unittest import mock

from django.apps import apps
from django.http import Http404
from django.test import Client, RequestFactory, TestCase

from common.tenant_scope import TenantScope

#: 규약 넷의 시험 이름. **여기가 정본이다.**
REQUIRED_RULES: dict[str, str] = {
    "①": "test_rule1_anonymous_gets_401",
    "②": "test_rule2_another_tenant_gets_404",
    "③": "test_rule3_bytes_carry_a_stamp",
    "④": "test_rule4_inline_not_attachment",
}

SNAPSHOT_PATH = "guardianx/detections/1/20260924/120000_000000.jpg"

#: 소인 실패를 흉내 낼 때 이 이름을 판다 — 서비스가 **모듈에서** 이름을 끌어오므로
#: 여기서도 같은 자리를 patch 한다.
FETCH = "stream_monitors.services.detection_snapshot.fetch_snapshot"


def _a_jpeg(width: int = 320, height: int = 240) -> bytes:
    """소인을 찍을 대상. **가짜 바이트가 아니라 진짜 JPEG 이어야 한다** —
    소인은 이미지를 열어서 그리므로, 아무 바이트나 주면 재는 것이 달라진다."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (width, height), (40, 60, 90)).save(buf, format="JPEG")
    return buf.getvalue()


class _SnapshotFixture(TestCase):
    """테넌트 A/B · A 의 스트림에 스냅샷 참조를 가진 이벤트 하나."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        UserGroup = apps.get_model("user", "UserGroup")
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="snap-tenant-A")
        cls.group_b = UserGroup.objects.create(name="snap-tenant-B")
        UserGroup.objects.filter(
            pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.user_a = cls._user("snap_user_a", cls.group_a)
        cls.user_b = cls._user("snap_user_b", cls.group_b)
        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)

        cls.stream = cls._stream("snap-cam-A", cls.group_a)
        cls.event_id = cls._event(cls.stream, SNAPSHOT_PATH)
        #: 프레임이 **없는** 이벤트 — 「없다」와 「지금 못 준다」를 가르는 표본이다.
        #: ⚠ **다른 스트림**에 세운다. 같은 스트림·같은 종류로 5분 안에 두 번 부르면
        #:   F-04 중복 억제가 앞의 이벤트로 접어 버려 두 표본이 **같은 행**이 된다 —
        #:   그러면 「프레임 없음」을 잰다고 믿으면서 실은 있는 프레임을 잰다.
        cls.stream_no_frame = cls._stream("snap-cam-A-noframe", cls.group_a)
        cls.event_no_frame = cls._event(cls.stream_no_frame, "")
        assert cls.event_no_frame != cls.event_id, "두 표본이 같은 이벤트로 접혔다"

    @staticmethod
    def _own(obj, group):
        from kernels.k1_event.services import _owner_field

        if _owner_field(type(obj)) == "groups":
            obj.groups.set([group])
        else:
            obj.group = group
            obj.save(update_fields=["group"])
        return obj

    @classmethod
    def _user(cls, username, group):
        CoreUser = apps.get_model("user", "CoreUser")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": group})
        return user

    @classmethod
    def _stream(cls, name, group):
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        return cls._own(StreamMonitor.objects.create(
            name=name, code=name, ip_source="rtsp://snap.invalid/x"), group)

    @classmethod
    def _event(cls, stream, snapshot_path: str) -> int:
        from kernels.k1_event import record_detection

        return record_detection(
            scope=TenantScope.system(reason="스냅샷 시험 — 파이프라인에 요청자가 없다"),
            stream_monitor_id=stream.pk, event_type="fire", severity="critical",
            snapshot_path=snapshot_path).event_id

    def tearDown(self) -> None:
        """★ HTTP 를 한 번이라도 때린 시험은 **스레드에 요청을 남긴다.**

        dj-core 의 `CustomManagerGroup.get_queryset()` 은 `get_current_request()` 를 보고
        그 요청자의 group 으로 **모든 조회를 좁힌다.** 익명 요청 하나가 남아 있으면
        그다음 시험의 `Event.objects` 가 통째로 비고, 그 빈 결과는 404 로 나온다 —
        [실측 2026-09-24] 이 자리에서 실제로 그랬다. 더 나쁜 것은 **404 를 기대하던
        시험(규약 ②)이 그 상태에서 초록이었다는 것**이다. 격리가 아니라 오염이 낸 초록이다.
        """
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().tearDown()

    def _request(self, user):
        request = RequestFactory().get(f"/api/dsm/events/{self.event_id}/snapshot")
        request.user = user
        return request

    def _call(self, user, event_id=None):
        from apps.dsm.api import DsmAPI

        return DsmAPI.event_snapshot(
            DsmAPI(), self._request(user), event_id or self.event_id)


class SnapshotRouteRulesTest(_SnapshotFixture):

    # ── ① 익명 401 ───────────────────────────────────────────────────────
    def test_rule1_anonymous_gets_401(self) -> None:
        """자격증명 없이는 프레임 1장도 나가지 않는다."""
        client = Client(raise_request_exception=False, HTTP_X_NO_CACHE="true")
        resp = client.get(f"/api/dsm/events/{self.event_id}/snapshot")
        self.assertEqual(
            resp.status_code, 401,
            f"익명 요청이 {resp.status_code} 를 받았습니다 — 스냅샷 문은 인증 뒤에 섭니다.")
        self.assertNotEqual(resp.content[:2], b"\xff\xd8",
                            "거절 응답에 JPEG 바이트가 실렸습니다.")

    # ── ② 남의 테넌트 404 ────────────────────────────────────────────────
    def test_rule2_another_tenant_gets_404(self) -> None:
        """403 이 아니다 — 「그 id 는 있지만 네 것이 아니다」도 누출이다 (D-269)."""
        from ninja.errors import HttpError

        from apps.dsm import services

        with self.assertRaises(Http404):
            services.event_snapshot(scope=self.scope_b, event_id=self.event_id)

        # 라우트도 같은 답을 낸다 — 서비스만 막고 라우트가 새면 막은 것이 아니다.
        with self.assertRaises(HttpError) as caught:
            self._call(self.user_b)
        self.assertEqual(caught.exception.status_code, 404)

    # ── ③ 소인 ───────────────────────────────────────────────────────────
    def test_rule3_bytes_carry_a_stamp(self) -> None:
        """나간 바이트는 원본이 아니다 — 테넌트명과 시각이 그림에 찍혀 있다."""
        from PIL import Image

        from apps.dsm import services

        original = _a_jpeg()
        with mock.patch(FETCH, return_value=(original, "")):
            stamped = services.event_snapshot(
                scope=self.scope_a, event_id=self.event_id)

        self.assertNotEqual(stamped, original,
                            "원본 바이트가 그대로 나갔습니다 — 소인이 없습니다.")
        self.assertEqual(stamped[:2], b"\xff\xd8", "JPEG 이 아닙니다.")

        # 소인이 **정말 그려졌는가** — 아래 띠의 픽셀이 원본과 달라야 한다.
        before = Image.open(io.BytesIO(original)).convert("L")
        after = Image.open(io.BytesIO(stamped)).convert("L")
        self.assertEqual(before.size, after.size, "소인이 이미지 크기를 바꿨습니다.")
        box = (0, int(before.height * 0.9), before.width, before.height)
        self.assertNotEqual(
            list(before.crop(box).getdata()), list(after.crop(box).getdata()),
            "아래쪽 띠가 원본과 같습니다 — 소인이 찍히지 않았습니다.")

    def test_a_missing_frame_is_404_not_500(self) -> None:
        """「이 이벤트에 프레임이 없다」는 서버 결함이 아니다."""
        from ninja.errors import HttpError

        with self.assertRaises(HttpError) as caught:
            self._call(self.user_a, event_id=self.event_no_frame)
        self.assertEqual(caught.exception.status_code, 404)

    def test_a_dead_store_is_503_not_500(self) -> None:
        """저장소가 죽은 것은 우리 결함이 아니다 — 그 사실을 상태로 낸다 (UX-10 과 같은 형)."""
        from ninja.errors import HttpError

        with mock.patch(FETCH, return_value=(
                b"", "저장소 연결 안 됨 — MinIO 가 지금 사용 불가 상태다")):
            with self.assertRaises(HttpError) as caught:
                self._call(self.user_a)
        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn("저장소 연결 안 됨", str(caught.exception))

    def test_a_stamp_failure_does_not_leak_unstamped_bytes(self) -> None:
        """소인을 못 찍으면 **안 내보낸다.** 원본으로 되돌아가지 않는다."""
        from ninja.errors import HttpError

        from apps.dsm.watermark import WatermarkFontMissing

        with mock.patch(FETCH, return_value=(_a_jpeg(), "")), \
             mock.patch("apps.dsm.watermark.stamp",
                        side_effect=WatermarkFontMissing("글꼴 없음")):
            with self.assertRaises(HttpError) as caught:
                self._call(self.user_a)
        self.assertEqual(caught.exception.status_code, 500)

    # ── ④ inline (다운로드 아님) ─────────────────────────────────────────
    def test_rule4_inline_not_attachment(self) -> None:
        """`attachment` 는 「파일로 받으라」다 — 그 헤더가 붙는 순간 반출의 모양이 된다."""
        with mock.patch(FETCH, return_value=(_a_jpeg(), "")):
            response = self._call(self.user_a)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        disposition = response["Content-Disposition"]
        self.assertIn("inline", disposition)
        self.assertNotIn("attachment", disposition,
                         "스냅샷이 파일 다운로드로 내려갑니다.")
        # 캐시 금지 (P-19) — 남의 소인이 찍힌 그림이 중간 캐시에 남으면 안 된다.
        self.assertIn("no-store", response["Cache-Control"])

    def test_the_route_source_declares_no_attachment(self) -> None:
        """부작위 — 라우트 원문에 `attachment` 가 들어오면 여기서 멈춘다 (D-300)."""
        api_src = (Path(__file__).resolve().parents[1]
                   / "apps" / "dsm" / "api.py").read_text(encoding="utf-8")
        block = api_src[api_src.index("스냅샷 바이트 (P-25"):
                        api_src.index("F-11 상황 보고서")]
        # ★ 주석은 뺀다. 이 라우트의 주석은 **왜 `attachment` 를 안 쓰는지**를 적고 있고,
        #   그 설명을 지워야 초록이 나는 시험은 설명을 지우게 만든다 (D-327 의 이웃).
        code = "\n".join(line for line in block.splitlines()
                         if not line.strip().startswith("#"))
        self.assertNotIn("attachment", code)
        self.assertIn('"inline"', code)

    # ── 규약이 **넷 다 있는가** ──────────────────────────────────────────
    def test_the_four_rules_are_all_present(self) -> None:
        for no, name in REQUIRED_RULES.items():
            self.assertTrue(
                hasattr(type(self), name),
                f"규약 {no} 의 시험 `{name}` 이 없습니다 — 넷 중 하나라도 없으면 "
                f"이 라우트를 내지 않는다는 것이 P-25 의 판정입니다.")
