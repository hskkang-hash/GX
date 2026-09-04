# -*- coding: utf-8 -*-
"""OPS-15 카메라 맥박 군집 두절 — **초록의 절반은 0건이다** (2026-09-04 · 차선 Q).

무엇을 재는가
-------------
    ① **양성** 구역 A 카메라 3대 중 2대의 프레임이 5분 안에 함께 멈추면 → 이벤트 **1건**
    ② **음성(부작위)** 1대만 멈추면 → **0건** ← 지시서 §3-3 이 요구하는 절반
    ③ **음성(동시성)** 2대가 죽어 있지만 **함께 죽지 않았으면** → 0건
    ④ 맥박이 한 번도 안 온 카메라(`last_frame_at=null`)는 **두절로 세지 않는다**
    ⑤ 만들어진 이벤트는 `camera_cluster_down` 이고 `camera_down` 과 **다른 유형**이다
    ⑥ 남의 카메라 맥박을 갱신할 수 없다 (쓰기 격리)
    ⑦ 두 번 훑어도 이벤트는 1건이다 (억제)

왜 ②가 가장 중요한가
--------------------
이 규칙의 값은 무엇을 만드는가가 아니라 **무엇을 안 만드는가**에 있다. 카메라 한 대가
끊길 때마다 재난 징후를 내면 관제 화면은 카메라 고장 목록이 되고, 그러면 진짜 군집
두절이 왔을 때 그 줄은 다른 줄들 사이에 묻힌다. 양성만 재는 시험은 그 상태를 초록으로
통과시킨다 — 그것이 지시서가 「부작위」라고 부르는 것이다.

★ **시험을 고쳐 초록을 만들지 않는다** (D-327). 아래 수(3대·2대·5분)는
  `camera_pulse` 의 상수를 **인용**한다 — 여기에 숫자를 적으면 규칙이 바뀌는 날
  시험만 옛말이 되고, 옛말이 된 시험은 초록이다.
"""
from __future__ import annotations

import contextlib
from datetime import timedelta

from django.apps import apps
from django.test import TestCase
from django.utils import timezone


class PulseFixture(TestCase):
    """구역 A(카메라 3대) · 구역 B(카메라 3대, 남의 테넌트) · 작은 구역(2대)."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        UserGroup = apps.get_model("user", "UserGroup")
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="q-pulse-A")
        cls.group_b = UserGroup.objects.create(name="q-pulse-B")
        UserGroup.objects.filter(
            pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.cams_a = [cls._camera(f"q-pulse-a-{i}", cls.group_a) for i in range(3)]
        cls.cams_b = [cls._camera(f"q-pulse-b-{i}", cls.group_b) for i in range(3)]
        cls.cams_small = [cls._camera(f"q-pulse-s-{i}", cls.group_a) for i in range(2)]

        cls.zone_a = cls._zone("q-zone-A", cls.group_a, cls.cams_a)
        cls.zone_b = cls._zone("q-zone-B", cls.group_b, cls.cams_b)
        cls.zone_small = cls._zone("q-zone-small", cls.group_a, cls.cams_small)

        from common.tenant_scope import TenantScope

        cls.scope_pipe = TenantScope.system(
            reason="OPS-15 맥박 검사 — 프레임 수집에는 요청자가 없다 (D-281)")

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
    def _camera(cls, name: str, group):
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        cam = StreamMonitor.objects.create(name=name, code=name,
                                           ip_source="rtsp://test.invalid/x")
        return cls._own(cam, group)

    @classmethod
    def _zone(cls, name: str, group, cameras):
        Zone = apps.get_model("stream_monitors", "Zone")
        zone = Zone.objects.create(name=name, kind=Zone.Kind.CAMERA_GROUP, is_active=True)
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

    def _cluster_events(self):
        from stream_monitors.services.camera_pulse import CLUSTER_EVENT_TYPE

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        return list(Event._base_manager.filter(event_type=CLUSTER_EVENT_TYPE))


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — **DB 없이** 잰다 (순수 함수)
# ═══════════════════════════════════════════════════════════════════════════
class ClusterJudgeTest(TestCase):
    """`judge_cluster` 의 세 갈래. 경계를 DB 없이 잰다 — 그래서 많이 잰다."""

    def setUp(self) -> None:
        from stream_monitors.services import camera_pulse as cp

        self.cp = cp
        self.now = timezone.now()

    def _rows(self, *ago_minutes):
        """`(카메라 id, 마지막 프레임 시각)` — `None` 은 「한 번도 안 왔다」."""
        return [
            (i + 1, None if m is None else self.now - timedelta(minutes=m))
            for i, m in enumerate(ago_minutes)
        ]

    def test_two_of_three_lost_together_fires(self) -> None:
        """★ 양성 — 3대 중 2대가 창 안에서 함께 잃었다."""
        verdict = self.cp.judge_cluster(self._rows(6, 7, 0), self.now)
        self.assertTrue(verdict.fires, verdict.reason)
        self.assertEqual(2, len(verdict.cluster))
        self.assertEqual(3, verdict.total)

    def test_only_one_lost_does_not_fire(self) -> None:
        """★★ **부작위 — 이 시험이 초록의 절반이다** (지시서 §3-3).

        1대만 끊긴 것은 시스템 이벤트(`camera_down`)의 일이지 재난 징후가 아니다.
        """
        verdict = self.cp.judge_cluster(self._rows(6, 0, 0), self.now)
        self.assertFalse(
            verdict.fires,
            f"1대만 끊겼는데 군집 두절을 냈다 — 관제 화면이 카메라 고장 목록이 된다. "
            f"사유: {verdict.reason}")
        self.assertIn("1대", verdict.reason)

    def test_two_dead_but_not_together_does_not_fire(self) -> None:
        """★ 동시성 — 한 달 전에 죽은 카메라 옆에서 오늘 한 대가 끊긴 경우.

        대수만 세는 규칙은 이것을 재난 징후라고 말한다. 그리고 그 말은 틀렸다.
        """
        verdict = self.cp.judge_cluster(self._rows(60 * 24 * 30, 6, 0), self.now)
        self.assertFalse(verdict.fires, verdict.reason)
        self.assertEqual(2, len(verdict.silent), "두 대가 조용한 것은 사실이다")
        self.assertIn("함께 잃지 않았다", verdict.reason)

    def test_never_seen_is_not_counted_as_down(self) -> None:
        """★ `null` 은 「아직 안 왔다」이지 「죽었다」가 아니다 (D-290).

        여기서 두절로 세면 시드 직후의 새 카메라가 전부 군집 두절이 되고,
        그러면 이 신호는 태어나자마자 소음이 된다.
        """
        verdict = self.cp.judge_cluster(self._rows(None, None, 0), self.now)
        self.assertFalse(verdict.fires, verdict.reason)
        self.assertEqual(2, verdict.never_seen)
        self.assertEqual((), verdict.silent)

    def test_small_zone_is_not_judged_at_all(self) -> None:
        """N 미만 구역은 **아예 안 본다** — 그리고 그 사실이 사유에 남는다."""
        verdict = self.cp.judge_cluster(self._rows(60, 60), self.now)
        self.assertFalse(verdict.fires)
        self.assertIn(str(self.cp.CLUSTER_MIN_CAMERAS), verdict.reason)

    def test_reason_is_never_empty(self) -> None:
        """0건이 **왜** 0건인지 말하지 않는 판정은 「검사 못함」과 구별되지 않는다 (D-301)."""
        for rows in (self._rows(0, 0, 0), self._rows(6, 0, 0), self._rows(6, 7, 8)):
            verdict = self.cp.judge_cluster(rows, self.now)
            self.assertTrue(verdict.reason.strip(), f"사유가 비었다: {verdict}")


# ═══════════════════════════════════════════════════════════════════════════
# 배선 — 맥박에서 이벤트까지 (DB)
# ═══════════════════════════════════════════════════════════════════════════
class ClusterWiringTest(PulseFixture):
    """`record_frame` → `scan_clusters` → K1 이벤트. **1건과 0건을 함께 잰다.**"""

    def test_two_cameras_silent_together_make_exactly_one_event(self) -> None:
        """★ 양성 — 구역 A 3대 중 2대를 멈추면 이벤트 **1건**."""
        from stream_monitors.services.camera_pulse import (
            CLUSTER_EVENT_TYPE, CLUSTER_SEVERITY, PULSE_TIMEOUT, scan_clusters)

        now = timezone.now()
        self._beat(self.cams_a[:2], ago=PULSE_TIMEOUT + timedelta(minutes=1), now=now)
        self._beat(self.cams_a[2:], ago=timedelta(seconds=5), now=now)
        self._beat(self.cams_b, ago=timedelta(seconds=5), now=now)
        self._beat(self.cams_small, ago=timedelta(seconds=5), now=now)

        result = scan_clusters(scope=self.scope_pipe, now=now)
        rows = self._cluster_events()
        self.assertEqual(
            1, len(rows),
            f"구역 3대 중 2대가 함께 끊겼는데 이벤트가 {len(rows)}건이다. "
            f"판정: {[(z, n, v.reason) for (z, n, v) in result.verdicts]}")
        self.assertEqual(CLUSTER_EVENT_TYPE, rows[0].event_type)
        self.assertEqual(CLUSTER_SEVERITY, rows[0].severity,
                         "등급은 경계다 — 빨강은 critical 전용이다 (ISA-101)")
        self.assertIn(rows[0].stream_monitor_id, [c.pk for c in self.cams_a])

    def test_only_one_camera_silent_makes_zero_events(self) -> None:
        """★★ **부작위 — 배선에서도 0건이다.**

        판정 함수가 옳아도 배선이 다르게 부르면 소용없다. 그래서 같은 사실을
        순수 함수(위)와 배선(여기) **두 곳에서** 잰다.
        """
        from stream_monitors.services.camera_pulse import PULSE_TIMEOUT, scan_clusters

        now = timezone.now()
        self._beat(self.cams_a[:1], ago=PULSE_TIMEOUT + timedelta(minutes=1), now=now)
        self._beat(self.cams_a[1:], ago=timedelta(seconds=5), now=now)
        self._beat(self.cams_b, ago=timedelta(seconds=5), now=now)
        self._beat(self.cams_small, ago=timedelta(seconds=5), now=now)

        result = scan_clusters(scope=self.scope_pipe, now=now)
        self.assertEqual(
            [], self._cluster_events(),
            f"1대만 끊겼는데 군집 두절이 나왔다 — **부작위 실패**. "
            f"판정: {[(n, v.reason) for (_z, n, v) in result.verdicts]}")
        self.assertGreater(result.zones_seen, 0,
                           "0건이 「안 봤다」여서는 안 된다 (D-301)")

    def test_scanning_twice_does_not_make_two_events(self) -> None:
        """★ 같은 사건은 한 줄이다. 1분마다 도는 검사가 5분에 5줄을 만들면 안 된다."""
        from stream_monitors.services.camera_pulse import PULSE_TIMEOUT, scan_clusters

        now = timezone.now()
        self._beat(self.cams_a[:2], ago=PULSE_TIMEOUT + timedelta(minutes=1), now=now)
        self._beat(self.cams_a[2:] + self.cams_b + self.cams_small,
                   ago=timedelta(seconds=5), now=now)

        scan_clusters(scope=self.scope_pipe, now=now)
        again = scan_clusters(scope=self.scope_pipe, now=now + timedelta(minutes=1))
        self.assertEqual(1, len(self._cluster_events()))
        self.assertTrue(again.suppressed_zone_ids,
                        "두 번째 훑기가 억제됐다는 사실이 결과에 안 남는다 — "
                        "억제와 「판정이 안 걸림」이 같은 모양이 된다")

    def test_dry_run_creates_nothing(self) -> None:
        """`create_events=False` 는 **아무것도 만들지 않는다.**

        부작위를 재려고 진짜 이벤트를 만들어야 한다면, 재는 행위가 재는 대상을 바꾼다.
        """
        from stream_monitors.services.camera_pulse import PULSE_TIMEOUT, scan_clusters

        now = timezone.now()
        self._beat(self.cams_a[:2], ago=PULSE_TIMEOUT + timedelta(minutes=1), now=now)
        self._beat(self.cams_a[2:] + self.cams_b + self.cams_small,
                   ago=timedelta(seconds=5), now=now)

        result = scan_clusters(scope=self.scope_pipe, now=now, create_events=False)
        self.assertEqual([], self._cluster_events())
        self.assertTrue(any(v.fires for (_z, _n, v) in result.verdicts),
                        "판정은 걸렸어야 한다 — 안 만든 것과 안 걸린 것은 다르다")

    def test_cluster_type_is_not_the_single_camera_type(self) -> None:
        """★ 둘은 **다른 화면에 간다** — 한 유형으로 뭉치면 그 구별이 사라진다."""
        from stream_monitors.services.camera_pulse import CLUSTER_EVENT_TYPE

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        self.assertIn(CLUSTER_EVENT_TYPE, Event.EventType.values,
                      "열거에 없는 유형은 `record_detection` 이 거절한다")
        self.assertNotEqual(CLUSTER_EVENT_TYPE, Event.EventType.CAMERA_DOWN)

    def test_ai_labels_do_not_produce_cluster_events(self) -> None:
        """★ 부작위 — AI 가 「구역이 통째로 끊겼다」를 **검출했다고 말할 수 없다.**

        이 유형이 `LABEL_TO_EVENT_TYPE` 에 들어가면 모델 출력이 네트워크 사실을
        주장하게 되고, 그 순간 이 신호의 근거가 장비에서 추론으로 바뀐다.
        """
        from stream_monitors.services.camera_pulse import CLUSTER_EVENT_TYPE
        from stream_monitors.services.detection_event_bridge import LABEL_TO_EVENT_TYPE

        self.assertNotIn(CLUSTER_EVENT_TYPE, set(LABEL_TO_EVENT_TYPE.values()))


class PulseWriteIsolationTest(PulseFixture):
    """★ 쓰기 격리 — **남의 카메라 맥박을 덮을 수 있는가** (D-290).

    심은 행은 보이지만 **덮인 두절은 아무 흔적도 남기지 않는다.** 남의 맥박을 갱신할 수
    있으면 남의 구역 두절을 조용히 지울 수 있고, 그것은 데이터를 심는 것보다 나쁘다.
    """

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        super().setUpTestData()
        from common.tenant_scope import TenantScope

        CoreUser = apps.get_model("user", "CoreUser")
        cls.user_a = CoreUser.objects.create_user(
            username="q_pulse_user_a", password="test-only-not-a-secret",
            is_active=True, email="q_pulse_user_a@test.invalid")
        link = CoreUser._meta.get_field("userprofilelink")
        link.related_model.objects.create(
            **{link.remote_field.name: cls.user_a, "group": cls.group_a})
        cls.scope_a = TenantScope.of(cls.user_a)

    def test_cannot_touch_another_tenants_pulse(self) -> None:
        from django.core.exceptions import PermissionDenied
        from django.http import Http404

        from stream_monitors.services.camera_pulse import record_frame

        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        victim = self.cams_b[0]
        before = StreamMonitor._base_manager.get(pk=victim.pk).last_frame_at

        with self.assertRaises((Http404, PermissionDenied)):
            record_frame(scope=self.scope_a, stream_monitor_id=victim.pk)

        after = StreamMonitor._base_manager.get(pk=victim.pk).last_frame_at
        self.assertEqual(before, after,
                         "거절했다면서 값이 바뀌었다 — 거절이 아니라 지연이다")

    def test_own_tenant_pulse_succeeds(self) -> None:
        """★ 양성 대조 — 거절만 재면 「전부 막힌 것」도 초록이다 (D-282 ④)."""
        from stream_monitors.services.camera_pulse import record_frame

        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        when = record_frame(scope=self.scope_a, stream_monitor_id=self.cams_a[0].pk)
        self.assertEqual(
            when, StreamMonitor._base_manager.get(pk=self.cams_a[0].pk).last_frame_at)

    def test_scan_of_one_tenant_does_not_see_the_other(self) -> None:
        """구역 훑기가 남의 구역까지 보면 **남의 두절이 내 화면에** 뜬다."""
        from stream_monitors.services.camera_pulse import scan_clusters

        result = scan_clusters(scope=self.scope_a, now=timezone.now(),
                               create_events=False)
        seen = {name for (_z, name, _v) in result.verdicts}
        self.assertNotIn(self.zone_b.name, seen)
        self.assertIn(self.zone_a.name, seen)


class PulseCountsTest(PulseFixture):
    """「카메라 맥박 N/N」 — OPS-14 본문이 인용하는 두 수 + 셋째 수."""

    def test_counts_split_alive_silent_and_never_seen(self) -> None:
        from stream_monitors.services.camera_pulse import PULSE_TIMEOUT, pulse_counts

        now = timezone.now()
        self._beat(self.cams_a[:1], ago=timedelta(seconds=5), now=now)
        self._beat(self.cams_a[1:2], ago=PULSE_TIMEOUT + timedelta(minutes=1), now=now)
        # cams_a[2] 와 cams_small 은 맥박이 한 번도 안 왔다

        counts = pulse_counts(scope=self.scope_pipe, now=now, group=self.group_a)
        self.assertEqual(1, counts.alive)
        self.assertEqual(5, counts.total, "구역 A 3대 + 작은 구역 2대")
        self.assertEqual(3, counts.never_seen)
        self.assertIn("맥박 미수신", counts.as_line(),
                      "한 번도 안 온 카메라가 분모에 조용히 섞이면 매일 아침 같은 "
                      "낮은 수가 나오고, 같은 수는 배경으로 읽힌다")


class PulseIsFedByThePipelineTest(PulseFixture):
    """★ **맥박을 채우는 자리가 실제로 있는가** (2026-09-24 · 조율자 병합에서 잡힌 것).

    차선 Q 는 칸과 규칙과 판정기를 세웠고, 그것을 **채우는 호출은 어디에도 없었다** —
    `record_frame` 을 부르는 곳이 시험 말고 0곳이었다. 그 상태에서도 모든 시험이
    초록이었다: 시험이 스스로 맥박을 심기 때문이다.

    운영에서는 `last_frame_at` 이 영원히 `None` 이고, 규칙은 그것을 **두절로 세지
    않으므로**(「아직 안 왔다」≠「죽었다」) OPS-15 는 조용히 0건만 낸다 —
    켜 놓고 안 도는 기능이다(D-377 잠자는 기능 · 착시 ⑨ 함수는 문이 아니다).

    ⚠ 이 시험이 빨개지면 **배선이 지워진 것**이다. 규칙을 고치지 말고 배선을 찾아라.
    """

    def test_a_callback_with_no_detections_still_writes_the_pulse(self) -> None:
        """★ **검출 0건인 콜백도 맥박이다.** 여기가 「조용함」과 「죽음」을 가르는 자리다.

        검출이 있을 때만 적으면 D-415 가 이미 겪은 상태로 되돌아간다 — 조용한 밤의
        정상 카메라와 케이블이 끊긴 카메라가 같은 값을 낸다.
        """
        from stream_monitors.services.grpc_dual_stream_service import (
            _publish_detection_events,
        )

        cam = self.cams_a[0]
        Stream = type(cam)
        Stream._base_manager.filter(pk=cam.pk).update(last_frame_at=None)

        _publish_detection_events(cam.pk, {"detections": []})

        after = Stream._base_manager.get(pk=cam.pk).last_frame_at
        self.assertIsNotNone(
            after,
            "검출 0건인 콜백에서 맥박이 안 적혔습니다 — 그러면 `last_frame_at` 은 "
            "운영에서 영원히 None 이고 군집 두절 판정은 눈을 감고 있는 것입니다.")

    def test_the_pulse_write_never_kills_the_stream(self) -> None:
        """★ 맥박 하나가 영상을 세우지 않는다. **영상은 계속 흘러야 한다.**"""
        from unittest import mock

        from stream_monitors.services.grpc_dual_stream_service import (
            _publish_detection_events,
        )

        with mock.patch(
                "stream_monitors.services.camera_pulse.record_frame",
                side_effect=RuntimeError("맥박 표가 죽었다")):
            # 예외가 밖으로 나오면 이 호출이 터진다 — 터지지 않는 것이 이 시험이다.
            _publish_detection_events(self.cams_a[0].pk, {"detections": []})
