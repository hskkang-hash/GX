# -*- coding: utf-8 -*-
"""UX-23 카메라 격자의 서버 문 — **「조용함」과 「죽음」은 다른 사실이다** (차선 C2 · 2026-09-05).

캐시 처리: 우회 — `X-No-Cache`(`tests.no_cache.NO_CACHE`). 맥박은 **지금 살아 있는가**를
묻는 질문이고, 적중 본문을 되살리는 캐시는 **죽은 카메라를 살아 있다고 답한다**(P-19 · D-341).

무엇을 재는가 — 다섯
--------------------
    ① **문지기가 실재하는가**   익명이 두드리면 열리지 않는다 (호출로 확인 · D-210)
    ② **격리**                  남의 테넌트 카메라가 목록에 없다
    ③ **셋을 접지 않는가**      살아 있음 · 응답 없음 · 한 번도 안 옴이 **다른 값**이다
    ④ **부작위**                한 대만 끊기면 군집 두절 **0건** (양성 1건과 함께 잰다)
    ⑤ **판정이 한 벌인가**      이 문의 `alive` 합이 `pulse_counts().alive` 와 같다

왜 ④를 양성과 **함께** 재나
---------------------------
`camera_pulse.py` 머리말이 그 이유를 이미 적었다: 이 규칙의 값은 무엇을 만드는가가
아니라 **무엇을 안 만드는가**에 있다. 한쪽만 재는 판정기는 이 저장소에서 초록으로
죽는다 — 아무것도 안 하는 문도, 모든 것에 발동하는 문도 「양성 1건」만으로는 통과한다.

왜 ⑤가 필요한가 — **두 벌이 되는 자리는 여기다**
------------------------------------------------
맥박 판정은 `stream_monitors/services/camera_pulse.py` 한 곳에 있고, 이 App 의 문은
그것을 **인용**한다. 그런데 카메라별 목록은 그 파일의 공개 면에 없어서 App 이
`PULSE_TIMEOUT` 을 인용해 한 줄을 스스로 만든다 — 그 한 줄이 언젠가 갈릴 수 있는
유일한 자리다. ⑤가 그 자리를 잠근다: 갈리는 날 이 시험이 빨개진다.

★ 재지 못한 것 — 정직하게 남긴다
--------------------------------
이 파일은 **화면을 재지 않는다.** `CameraGrid.tsx` 가 이 값을 어떻게 그리는지는
브라우저에서만 재어지고, 이 턴에 브라우저는 조율자의 것이다(동시접속 1개).
그 사실은 `docs/agent/evidence/UX-23/README.md` 에 적었다.
"""
from __future__ import annotations

import contextlib
import json
from datetime import timedelta

from django.apps import apps
from django.test import Client, TestCase
from django.utils import timezone

from tests.no_cache import NO_CACHE

#: 이 문의 주소. 한 곳에서만 적는다 — 두 곳에 적으면 한 곳만 고치는 날이 온다.
PULSE_PATH = "/api/dsm/cameras/pulse"


class GridFixture(TestCase):
    """테넌트 A(카메라 4대 · 구역 하나) · 테넌트 B(카메라 1대).

    `tests/test_q_camera_pulse.PulseFixture` 의 모양을 따른다 — 같은 표를 두 벌로
    만들지 않기 위해서다. 다른 것은 **App 의 문을 지난다**는 것뿐이다.
    """

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        UserGroup = apps.get_model("user", "UserGroup")

        # 스레드에 남은 요청이 `objects` 를 조용히 비운다 — 픽스처는 그 앞에서 선다.
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="c2-grid-A")
        cls.group_b = UserGroup.objects.create(name="c2-grid-B")
        UserGroup.objects.filter(
            pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.user_a = cls._user("c2_grid_user_a", cls.group_a)
        cls.user_b = cls._user("c2_grid_user_b", cls.group_b)

        # 구역 A — 군집 규칙이 보는 최소 대수(3대)를 채운다.
        cls.cams_a = [cls._camera(f"c2-a-{i}", cls.group_a) for i in range(3)]
        #: 맥박이 **한 번도 안 온** 카메라. 구역 밖에 둔다 — 구역 판정과 섞지 않는다.
        cls.cam_never = cls._camera("c2-a-never", cls.group_a)
        cls.cam_b = cls._camera("c2-b-0", cls.group_b)

        cls.zone_a = cls._zone("c2-zone-A", cls.group_a, cls.cams_a)

        from common.tenant_scope import TenantScope

        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)
        cls.scope_pipe = TenantScope.system(
            reason="UX-23 시험 픽스처 — 프레임 수집에는 요청자가 없다 (D-281)")

    # ── 도우미 ───────────────────────────────────────────────────────────
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
    def _camera(cls, name, group):
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        cam = StreamMonitor.objects.create(name=name, code=name,
                                           ip_source="rtsp://test.invalid/x")
        return cls._own(cam, group)

    @classmethod
    def _zone(cls, name, group, cameras):
        Zone = apps.get_model("stream_monitors", "Zone")
        zone = Zone.objects.create(name=name, kind=Zone.Kind.CAMERA_GROUP,
                                   is_active=True)
        cls._own(zone, group)
        zone.cameras.set(cameras)
        return zone

    def _beat(self, cameras, *, ago: timedelta, now=None):
        """이 카메라들의 마지막 프레임을 `ago` 전으로 둔다 (= 그만큼 조용하다)."""
        from stream_monitors.services.camera_pulse import record_frame

        now = now or timezone.now()
        for cam in cameras:
            record_frame(scope=self.scope_pipe, stream_monitor_id=cam.pk,
                         at=now - ago)

    def _pulse(self, scope=None, now=None):
        from apps.dsm import services

        return services.camera_pulse(scope=scope or self.scope_a, now=now)

    @staticmethod
    def _by_id(payload):
        return {row["id"]: row for row in payload["cameras"]}


# ═══════════════════════════════════════════════════════════════════════════
# ① 문지기 — **호출로 확인한다** (D-210). 읽어서 답하지 않는다
# ═══════════════════════════════════════════════════════════════════════════
class PulseDoorIsGuardedTest(TestCase):
    """문지기 없는 새 경로를 만들지 않는다 (D-275 §5-1)."""

    def setUp(self) -> None:
        # 캐시가 장애를 덮는다(P-19) — 문지기를 재는 시험이 캐시를 재면 안 된다.
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def test_anonymous_does_not_get_the_pulse(self) -> None:
        """★ 익명에게는 **200 이 아니다.** 그리고 그 거절이 봉투 안에 숨지 않는다.

        거절을 200 안에 담으면 게이트웨이·모니터링·화면이 **성공으로 읽는다**
        (D-349 착시 ⑧). 이 문은 그 전철을 밟지 않는다.
        """
        resp = self.client.get(PULSE_PATH)
        self.assertEqual(
            401, resp.status_code,
            f"익명이 카메라 맥박을 {resp.status_code} 로 받았다 — "
            f"어느 구역이 통째로 끊겼는지는 재난 정보다")
        body = json.loads((resp.content or b"{}").decode("utf-8", "replace"))
        self.assertNotIn("cameras", body, "거절 본문에 카메라 목록이 섞여 나갔다")

    def test_the_route_is_registered_with_both_guards(self) -> None:
        """★ 대장에 이름으로 남긴다 — 인증과 테넌트 문지기 **둘 다**.

        401 하나만 재면 「인증은 있는데 테넌트 문지기가 없는」 문을 통과시킨다.
        그 문은 로그인만 하면 남의 카메라를 준다.
        """
        from common.tenant_scope import enumerate_operations

        rows = [r for r in enumerate_operations()
                if r.path == PULSE_PATH and r.method == "GET"]
        self.assertEqual(1, len(rows),
                         f"{PULSE_PATH} 가 라우트 대장에 {len(rows)}건이다")
        self.assertTrue(rows[0].has_auth, "인증 없는 진입면이다")
        self.assertIsNotNone(rows[0].scope, "테넌트 문지기가 없는 진입면이다")


# ═══════════════════════════════════════════════════════════════════════════
# ② 격리 — 남의 카메라는 **없다**
# ═══════════════════════════════════════════════════════════════════════════
class PulseIsolationTest(GridFixture):

    def test_another_tenants_camera_is_not_in_the_list(self) -> None:
        now = timezone.now()
        self._beat(self.cams_a + [self.cam_b], ago=timedelta(seconds=5), now=now)

        mine = self._pulse(self.scope_a, now=now)
        ids = set(self._by_id(mine))
        self.assertNotIn(self.cam_b.pk, ids,
                         "남의 테넌트 카메라가 내 격자에 떴다 — 격리 실패")
        self.assertTrue({c.pk for c in self.cams_a} <= ids,
                        "내 카메라가 안 보인다 — 격리가 아니라 눈이 먼 것이다")

    def test_the_other_side_sees_only_its_own(self) -> None:
        """★ 한쪽만 재면 「아무것도 안 보이는 문」이 격리로 통과한다 (D-301)."""
        now = timezone.now()
        self._beat(self.cams_a + [self.cam_b], ago=timedelta(seconds=5), now=now)

        theirs = self._pulse(self.scope_b, now=now)
        ids = set(self._by_id(theirs))
        self.assertEqual({self.cam_b.pk}, ids,
                         "B 가 보는 목록이 자기 것 한 대가 아니다")
        self.assertEqual(1, theirs["counts"]["total"], "분모까지 격리돼야 한다")

    def test_the_zone_verdicts_are_scoped_too(self) -> None:
        """구역 판정도 좁혀진다 — 목록만 좁히고 집계를 안 좁히면 수로 샌다."""
        now = timezone.now()
        self._beat(self.cams_a, ago=timedelta(seconds=5), now=now)
        theirs = self._pulse(self.scope_b, now=now)
        self.assertEqual(
            [], [z["zone_id"] for z in theirs["cluster"]["zones"]],
            "남의 구역 판정이 B 에게 나갔다")


# ═══════════════════════════════════════════════════════════════════════════
# ③ 「조용함」 · 「죽음」 · 「아직 안 옴」 — **셋은 다른 사실이다**
# ═══════════════════════════════════════════════════════════════════════════
class QuietIsNotDeadTest(GridFixture):
    """`camera_pulse.py` 머리말이 이 파일을 낳은 문장이다.

    프레임은 사건이 없어도 온다. 그래서 「이벤트가 안 온 카메라」와 「케이블이 끊긴
    카메라」는 **다른 값으로** 나와야 한다 — 같은 값이면 관제요원이 멀쩡한 카메라를
    보러 가고, 진짜 끊긴 카메라는 그 사이에 묻힌다.
    """

    def test_a_quiet_camera_and_a_dead_camera_differ(self) -> None:
        from stream_monitors.services.camera_pulse import PULSE_TIMEOUT

        now = timezone.now()
        quiet, dead = self.cams_a[0], self.cams_a[1]
        # 조용한 카메라 — 프레임은 방금 왔고 **탐지 이벤트는 한 건도 없다.**
        self._beat([quiet], ago=timedelta(seconds=5), now=now)
        self._beat([dead], ago=PULSE_TIMEOUT + timedelta(minutes=1), now=now)
        self._beat(self.cams_a[2:], ago=timedelta(seconds=5), now=now)

        rows = self._by_id(self._pulse(now=now))
        self.assertTrue(rows[quiet.pk]["alive"],
                        "사건이 없는 카메라가 죽은 것으로 나왔다 — "
                        "「조용함」과 「죽음」이 같은 값이 됐다")
        self.assertFalse(rows[dead.pk]["alive"],
                         "프레임이 끊긴 카메라가 살아 있는 것으로 나왔다")
        self.assertNotEqual(rows[quiet.pk]["alive"], rows[dead.pk]["alive"])

    def test_never_seen_is_not_the_same_as_dead(self) -> None:
        """★ `null` 은 「아직 한 장도 안 왔다」이지 「죽었다」가 아니다 (D-290).

        둘 다 화면에서는 「응답 없음」이지만, 아래 한 줄(「마지막 응답 N분 전」)이
        갈린다 — 한 번도 안 온 카메라에는 그 줄이 **없다.** 없는 것을 0분으로 그리면
        방금 등록한 카메라가 방금 끊긴 카메라로 보인다.
        """
        from stream_monitors.services.camera_pulse import PULSE_TIMEOUT

        now = timezone.now()
        dead = self.cams_a[0]
        self._beat([dead], ago=PULSE_TIMEOUT + timedelta(minutes=1), now=now)
        self._beat(self.cams_a[1:], ago=timedelta(seconds=5), now=now)

        rows = self._by_id(self._pulse(now=now))
        never = rows[self.cam_never.pk]
        self.assertFalse(never["alive"])
        self.assertIsNone(never["last_seen_at"],
                          "한 번도 안 온 카메라에 마지막 응답 시각이 생겼다")
        self.assertIsNone(never["silent_seconds"],
                          "「없다」가 0초로 접혔다 — 0은 「즉시」이지 「없음」이 아니다")
        self.assertIsNotNone(rows[dead.pk]["last_seen_at"],
                             "끊긴 카메라의 마지막 응답 시각이 사라졌다")
        self.assertGreater(rows[dead.pk]["silent_seconds"],
                           PULSE_TIMEOUT.total_seconds())
        # 셋이 실제로 세 모양인가 — 값으로 확인한다.
        alive_row = rows[self.cams_a[1].pk]
        shapes = {
            (alive_row["alive"], alive_row["last_seen_at"] is None),
            (rows[dead.pk]["alive"], rows[dead.pk]["last_seen_at"] is None),
            (never["alive"], never["last_seen_at"] is None),
        }
        self.assertEqual(3, len(shapes),
                         "세 사실이 세 모양으로 안 나온다 — 어딘가에서 접혔다")

    def test_the_response_carries_no_reason_prose(self) -> None:
        """★ 사유 문장을 화면 쪽으로 내보내지 않는다 (P-27).

        `ClusterVerdict.reason` 은 우리 말이다. 앞판이 사유를 그대로 실었다가
        상대사명·계약번호가 관제요원 화면에 떴다 — 막는 곳은 화면이 아니라 서버다.
        """
        now = timezone.now()
        self._beat(self.cams_a, ago=timedelta(seconds=5), now=now)
        payload = self._pulse(now=now)
        flat = json.dumps(payload, default=str, ensure_ascii=False)
        self.assertNotIn("reason", flat,
                         "사유 문장이 응답에 실렸다 — 화면이 그것을 그대로 그린다")
        for zone in payload["cluster"]["zones"]:
            # 사유가 하던 일(「안 봤다」와 「안 걸렸다」를 가르기)은 값이 한다.
            self.assertIn("judged", zone)
            self.assertIn("fires", zone)


# ═══════════════════════════════════════════════════════════════════════════
# ④ 부작위 — **1대만 끊기면 0건.** 양성 1건과 함께 잰다
# ═══════════════════════════════════════════════════════════════════════════
class ClusterOmissionTest(GridFixture):
    """초록의 절반은 0건이다 (지시서 §3-3 · `camera_pulse.py` 머리말)."""

    def _outage(self, *, down, now):
        from stream_monitors.services.camera_pulse import PULSE_TIMEOUT

        self._beat(self.cams_a[:down], ago=PULSE_TIMEOUT + timedelta(minutes=1),
                   now=now)
        self._beat(self.cams_a[down:], ago=timedelta(seconds=5), now=now)
        return self._pulse(now=now)

    def test_two_cameras_lost_together_is_one_outage(self) -> None:
        """★ 양성 — 3대 중 2대가 함께 끊기면 **1건**."""
        payload = self._outage(down=2, now=timezone.now())
        self.assertEqual(1, payload["cluster"]["outage_count"],
                         "함께 끊긴 2대가 군집 두절로 안 나왔다")
        fired = [z for z in payload["cluster"]["zones"] if z["fires"]]
        self.assertEqual(1, len(fired))
        self.assertEqual(2, len(fired[0]["cluster_camera_ids"]))

    def test_only_one_camera_lost_is_zero_outages(self) -> None:
        """★★ **부작위** — 1대만 끊기면 **0건**이고, 그 0은 「안 봤다」가 아니다.

        한 대가 끊길 때마다 재난 징후를 내면 관제 화면은 카메라 고장 목록이 되고,
        진짜 군집 두절이 왔을 때 그 줄은 다른 줄들 사이에 묻힌다.
        """
        payload = self._outage(down=1, now=timezone.now())
        self.assertEqual(
            0, payload["cluster"]["outage_count"],
            f"1대만 끊겼는데 군집 두절이 나왔다 — 부작위 실패. "
            f"구역: {payload['cluster']['zones']}")
        self.assertGreater(payload["cluster"]["zones_seen"], 0,
                           "0건이 「구역을 하나도 안 봤다」여서는 안 된다 (D-301)")
        seen = [z for z in payload["cluster"]["zones"] if z["judged"]]
        self.assertTrue(seen, "본 구역이 하나도 없다 — 판정기가 눈이 멀었다")
        self.assertEqual(1, len(seen[0]["silent_camera_ids"]),
                         "끊긴 한 대가 목록에도 안 나온다 — 0건과 「아무 일 없음」이 "
                         "같은 그림이 됐다")

    def test_a_small_zone_is_not_judged_at_all(self) -> None:
        """「안 봤다」와 「봤는데 안 걸렸다」가 값으로 갈린다."""
        from stream_monitors.services.camera_pulse import (CLUSTER_MIN_CAMERAS,
                                                           PULSE_TIMEOUT)

        now = timezone.now()
        small = self._zone("c2-zone-small", self.group_a, self.cams_a[:2])
        self._beat(self.cams_a[:2], ago=PULSE_TIMEOUT + timedelta(minutes=1), now=now)
        self._beat(self.cams_a[2:], ago=timedelta(seconds=5), now=now)

        payload = self._pulse(now=now)
        row = next(z for z in payload["cluster"]["zones"] if z["zone_id"] == small.pk)
        self.assertLess(row["total"], CLUSTER_MIN_CAMERAS)
        self.assertFalse(row["judged"], "작은 구역을 봤다고 말한다")
        self.assertFalse(row["fires"])

    def test_looking_at_the_grid_creates_nothing(self) -> None:
        """★ **보는 행위가 보는 대상을 바꾸지 않는다.**

        이 문이 `create_events=True` 로 부르면 화면을 열 때마다 이벤트가 나고,
        그러면 관제 화면이 자기 목록을 스스로 채운다.
        """
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        before = Event._base_manager.count()
        self._outage(down=2, now=timezone.now())
        self.assertEqual(before, Event._base_manager.count(),
                         "맥박 문이 이벤트를 만들었다 — 읽기 면이 쓰기를 했다")


# ═══════════════════════════════════════════════════════════════════════════
# ⑤ 판정이 한 벌인가 — **갈리는 날 여기가 빨개진다**
# ═══════════════════════════════════════════════════════════════════════════
class OneJudgementNotTwoTest(GridFixture):

    def test_alive_count_matches_the_pulse_service(self) -> None:
        """이 문의 카메라별 `alive` 합 == `camera_pulse.pulse_counts().alive`.

        두 수가 갈리면 화면의 「응답 없음 N대」와 생존 알림의 「맥박 N/N」이 다른
        수를 말하게 되고, 그 어긋남은 아무도 못 본다.
        """
        from stream_monitors.services.camera_pulse import PULSE_TIMEOUT, pulse_counts

        now = timezone.now()
        self._beat(self.cams_a[:1], ago=PULSE_TIMEOUT + timedelta(minutes=1), now=now)
        self._beat(self.cams_a[1:], ago=timedelta(seconds=5), now=now)

        payload = self._pulse(now=now)
        listed_alive = sum(1 for row in payload["cameras"] if row["alive"])
        counted = pulse_counts(scope=self.scope_a, now=now)
        self.assertEqual(
            counted.alive, listed_alive,
            f"목록이 센 생존 {listed_alive}대와 맥박 서비스가 센 {counted.alive}대가 "
            f"다르다 — 판정이 두 벌이 됐다 (D-212)")
        self.assertEqual(counted.total, len(payload["cameras"]),
                         "분모가 다르다 — 목록과 집계가 다른 카메라를 보고 있다")
        self.assertEqual(counted.never_seen, payload["counts"]["never_seen"])

    def test_the_rules_come_from_the_pulse_module(self) -> None:
        """★ 문턱을 화면에 내려보내되 **그 수를 여기서 만들지 않는다.**

        화면이 자기 문턱을 들면 규칙이 바뀌는 날 화면만 옛말이 된다. 그래서 서버가
        문턱을 말하고, 서버의 그 수는 `camera_pulse` 의 상수 그대로여야 한다.
        """
        from stream_monitors.services import camera_pulse as cp

        rules = self._pulse(now=timezone.now())["rules"]
        self.assertEqual(int(cp.PULSE_TIMEOUT.total_seconds()),
                         rules["pulse_timeout_seconds"])
        self.assertEqual(int(cp.CLUSTER_WINDOW.total_seconds()),
                         rules["cluster_window_seconds"])
        self.assertEqual(cp.CLUSTER_MIN_CAMERAS, rules["cluster_min_cameras"])
        self.assertEqual(cp.CLUSTER_MIN_DOWN, rules["cluster_min_down"])

    def test_a_system_scope_cannot_read_the_grid(self) -> None:
        """읽기는 사람이 한다 (D-281). 요청자 없는 스코프로 열면 전역 조회가 된다."""
        with self.assertRaises(Exception):
            self._pulse(self.scope_pipe, now=timezone.now())
