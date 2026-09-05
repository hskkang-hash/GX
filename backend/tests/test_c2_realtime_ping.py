# -*- coding: utf-8 -*-
"""UX-08 — **꺼진 스위치가 그 전등의 스위치인가** (차선 C2 · 2026-09-05).

직전 턴이 남긴 미지
-------------------
    「잠자던 시그널은 `VideoAnalysis` 에 붙어 있고 화면은 `DetectionEvent` 를 읽는다 —
      꺼진 스위치가 그 전등의 스위치인지는 따로 확인해야 한다.」

재고 나온 것 [실측 2026-09-05]
------------------------------
    grep -rn "ping_detection" backend/ →
        common/live_ping.py:52                                  (정의)
        stream_monitors/services/detection_event_bridge.py:329  (부르는 곳 · **단 하나**)

두드림은 **AI gRPC 파이프라인 한 갈래에서만** 나가고 있었다. `record_detection` 을
부르는 다른 경로(맥박 군집 두절 · 검수 시드)로 태어난 이벤트는 화면을 한 번도
두드리지 않았다. 「코드는 있고 꺼져 있다」가 아니라 **「켜져 있는데 다른 전등이다」**였다.

무엇을 재는가 — 다섯
--------------------
    ① **받는 쪽이 먼저 서 있는가**   `consumers.py` 에 `detection_message` 핸들러가 있다
    ② **화면이 아는 말로 나가는가**  화면(`useDetectionPing`)이 알아듣는 `type` 하나뿐이다
    ③ **행이 태어나면 나가는가**     `DetectionEvent` 생성 → 그룹에 두드림이 **실제로** 온다
    ④ **갈래를 안 가리는가**         gRPC 배선을 지나지 않은 경로(맥박 군집 두절)도 두드린다
    ⑤ **부작위**                     새 탐지가 아닌 저장(판정·대응)은 두드리지 **않는다**

★ 어느 채널 레이어를 쟀는지 — **명시한다** (조율자 지시 · 2026-09-05)
---------------------------------------------------------------------
이 파일은 `InMemoryChannelLayer` 로 갈아 끼우지 **않는다.** `settings.CHANNEL_LAYERS`
가 가리키는 **운영 설정 그대로의 레이어**(`channels_redis.core.RedisChannelLayer`,
redis 컨테이너)에 붙어서 잰다. 갈아 끼우고 재면 「시험은 초록인데 운영 경로가
죽는다」가 되고, 그것이 D-378 에서 이 저장소가 이미 치른 값이다.

★ 다만 **커밋 시점**은 시험의 손으로 민다
-----------------------------------------
두드림은 `transaction.on_commit` 에 매달려 있다(그래야 화면이 목록을 다시 읽는 순간
그 행이 **이미 있다**). `TestCase` 는 트랜잭션을 커밋하지 않으므로 커밋 콜백이 돌지
않는다 — 그래서 `captureOnCommitCallbacks(execute=True)` 로 그 한 걸음만 민다.
**레이어는 진짜이고 커밋만 시험이 민다** — 두 사실을 섞어 적지 않는다.
"""
from __future__ import annotations

import asyncio
import contextlib
from datetime import timedelta
from pathlib import Path

from asgiref.sync import async_to_sync
from django.apps import apps
from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_save
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend"

#: 화면과 서버가 **같은 낱말**로 합의한 신호 이름. 한 곳에서만 적는다.
PING_TYPE = "detection_message"


def _receive(layer, channel, timeout: float = 3.0):
    """그 채널에 온 것 하나. 안 오면 `None` — **기다리다 죽지 않는다.**

    두드림이 안 나가는 것도 이 시험이 재야 하는 사실이므로(⑤), 못 받은 것이
    타임아웃 예외가 되면 「안 왔다」와 「시험이 깨졌다」가 같은 모양이 된다.
    """
    async def _go():
        try:
            return await asyncio.wait_for(layer.receive(channel), timeout)
        except (asyncio.TimeoutError, TimeoutError):
            return None

    try:
        return async_to_sync(_go)()
    except RuntimeError:
        # ⚠ [실측 2026-09-05] 한 번 **타임아웃으로 끊긴** receive 뒤에 같은 채널을
        #   다시 읽으면 `channels_redis` 의 연결이 닫힌 이벤트 루프에 묶여 있어
        #   RuntimeError 가 난다. 그 자리에서 재는 사실은 어느 쪽이든 하나다 —
        #   **두드림이 안 왔다.** 예외로 두면 「안 왔다」와 「시험이 깨졌다」가
        #   같은 모양이 되고, 그 둘을 못 가르면 이 시험은 뜻이 없어진다.
        return None


# ═══════════════════════════════════════════════════════════════════════════
# ① · ② 받는 쪽이 먼저 서 있는가 · 화면이 아는 말인가 — **DB 없이 잰다**
# ═══════════════════════════════════════════════════════════════════════════
class TheReceivingSideStandsFirstTest(SimpleTestCase):
    """★ 켜기의 순서 — **받는 쪽 없이 켜면 켜는 순간이 사고다.**

    `consumers.py` 에 해당 `type` 핸들러가 없는 채로 그룹에 쏘면 Channels 가
    `No handler for message type ...` 로 죽고, **그 그룹에 붙은 모든 관제 세션이
    끊긴다.** 새 두드림을 더하는 사람이 이 시험을 먼저 만나게 둔다.
    """

    def test_the_consumer_has_a_handler_for_the_ping(self) -> None:
        from surveillance.consumers import SurveillanceProfileNotificationConsumer

        self.assertTrue(
            callable(getattr(SurveillanceProfileNotificationConsumer, PING_TYPE, None)),
            f"consumer 에 {PING_TYPE!r} 핸들러가 없다 — 이대로 그룹에 쏘면 "
            f"그 그룹의 관제 세션이 **전부 끊긴다**")

    def test_every_type_we_send_has_a_handler(self) -> None:
        """★ 부작위 — 보내는 쪽이 쓰는 `type` 이 받는 쪽에 **전부** 있다.

        하나만 확인하면 다음에 더해지는 두 번째 두드림이 그대로 사고가 된다.
        """
        from surveillance.consumers import SurveillanceProfileNotificationConsumer

        sent = set()
        for path in ("common/live_ping.py", "surveillance/signals.py"):
            src = (BACKEND / path).read_text(encoding="utf-8", errors="replace")
            for line in src.splitlines():
                if '"type":' in line:
                    value = line.split('"type":', 1)[1].strip().strip(",").strip()
                    if value.startswith(('"', "'")):
                        sent.add(value.strip("\"'"))
        self.assertIn(PING_TYPE, sent, "보내는 쪽에서 그 두드림을 못 찾았다")
        missing = [t for t in sorted(sent)
                   if not callable(getattr(SurveillanceProfileNotificationConsumer,
                                           t, None))]
        self.assertEqual([], missing,
                         f"핸들러 없는 두드림: {missing} — 쏘는 순간 세션이 끊긴다")

    def test_the_screen_understands_exactly_this_word(self) -> None:
        """★ 화면과 서버가 같은 낱말을 쓰는가 — **한 글자가 다르면 아무 일도 안 난다.**

        틀리면 화면은 조용히 아무것도 안 한다(모르는 모양은 무시한다). 그 침묵은
        「사건이 없다」와 구별되지 않는다.
        """
        rel = "src/features/dsm/hooks/useDetectionPing.ts"
        hook = next((c for c in (FRONTEND / rel, BACKEND.parent.parent / "frontend" / rel)
                     if c.exists()), None)
        if hook is None:
            # ⚠ 시험 컨테이너(gx-shell)에는 `frontend/` 가 없다 [실측 2026-09-05:
            #   `/repo` = backend·docs·scripts]. 못 잰 것은 **판정 불가**이고,
            #   초록으로 세지 않는다. 호스트에서 같은 확인을 하고 증거에 적었다.
            self.skipTest("화면 훅이 이 트리에 없다 — 못 잰 것은 판정 불가다")
        src = hook.read_text(encoding="utf-8", errors="replace")
        self.assertIn(f"'{PING_TYPE}'", src,
                      "화면이 기다리는 낱말과 서버가 보내는 낱말이 다르다")

    def test_the_signal_is_actually_connected(self) -> None:
        """★ **잠자는 기능**을 다시 만들지 않는다 — 붙어 있는지 대장에 묻는다.

        데코레이터가 붙어 있어도 아무도 그 모듈을 import 하지 않으면 시그널은
        붙지 않는다. 코드에는 있고 돌지는 않는 상태 — 이 절의 출발점이 그것이었다.
        """
        DetectionEvent = apps.get_model("stream_monitors", "DetectionEvent")
        self.assertTrue(
            post_save.has_listeners(DetectionEvent),
            "DetectionEvent 의 post_save 에 아무도 안 붙어 있다 — "
            "SurveillanceConfig.ready() 가 signals 를 import 하는지 보라")

        # ⚠ 등재 줄의 **모양이 장고 판마다 다르다** (5.1 은 `(key, ref, is_async)`).
        #   모양을 하나로 단정하면 장고를 올리는 날 이 시험이 「기능이 죽었다」로
        #   빨개진다 — 그 빨강은 뜻이 틀린 빨강이다. 그래서 줄에서 **함수만** 캐낸다.
        names = set()
        for row in post_save.receivers:
            for item in row:
                func = item() if callable(item) and not hasattr(item, "__name__") else item
                name = getattr(func, "__name__", None)
                if name:
                    names.add(name)
        self.assertIn(
            "detection_event_post_save", names,
            "UX-08 두드림 수신기가 대장에 없다 — 모듈이 import 되지 않았다")


# ═══════════════════════════════════════════════════════════════════════════
# ③ · ④ · ⑤ 두드림이 **실제로** 나가는가 — 운영 설정의 채널 레이어에 붙어서 잰다
# ═══════════════════════════════════════════════════════════════════════════
class PingFixture(TestCase):
    """테넌트 하나 · 카메라 셋 · 구역 하나."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        UserGroup = apps.get_model("user", "UserGroup")

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group = UserGroup.objects.create(name="c2-ping")
        UserGroup.objects.filter(pk=cls.group.pk).update(created_by=None)
        cls.cams = [cls._camera(f"c2-ping-{i}", cls.group) for i in range(3)]
        cls.zone = cls._zone("c2-ping-zone", cls.group, cls.cams)

        from common.tenant_scope import TenantScope

        cls.scope_pipe = TenantScope.system(
            reason="UX-08 시험 — 검출 파이프라인에는 요청자가 없다 (D-281)")

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
    def _camera(cls, name, group):
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        return cls._own(StreamMonitor.objects.create(
            name=name, code=name, ip_source="rtsp://test.invalid/x"), group)

    @classmethod
    def _zone(cls, name, group, cameras):
        Zone = apps.get_model("stream_monitors", "Zone")
        zone = Zone.objects.create(name=name, kind=Zone.Kind.CAMERA_GROUP,
                                   is_active=True)
        cls._own(zone, group)
        zone.cameras.set(cameras)
        return zone

    # ── 채널 레이어 — **갈아 끼우지 않는다** ─────────────────────────────
    def setUp(self) -> None:
        from channels.layers import get_channel_layer
        from common.live_ping import _room_for
        from stream_monitors.services.detection_event_bridge import _tenant_code_of

        self.layer = get_channel_layer()
        if self.layer is None:
            self.skipTest("채널 레이어가 없다 — 못 잰 것은 판정 불가다")
        #: 두드림이 실제로 가는 방. **보내는 쪽의 판단을 그대로 쓴다** —
        #: 시험이 방을 따로 계산하면 방이 갈려도 이 시험은 초록이다.
        self.room = _room_for(_tenant_code_of(self.cams[0].pk))
        self.channel = async_to_sync(self.layer.new_channel)()
        async_to_sync(self.layer.group_add)(self.room, self.channel)
        self.addCleanup(
            lambda: async_to_sync(self.layer.group_discard)(self.room, self.channel))
        self._uncoalesce()

    def _uncoalesce(self) -> None:
        """합치기 창(3초)을 비운다 — 앞 시험의 두드림이 뒤 시험을 삼키지 않게.

        ⚠ 이 창은 **억제가 아니라 합치기**다(live_ping 머리말). 지우는 것은
          규칙을 끄는 것이 아니라 **시험 사이의 시간을 지우는 것**이다.
        """
        with contextlib.suppress(Exception):
            cache.delete(f"gx:ux08:ping:{self.room}")

    def _record(self, cam, *, event_type="fire", when=None):
        from kernels.k1_event import record_detection

        return record_detection(
            scope=self.scope_pipe, stream_monitor_id=cam.pk,
            event_type=event_type, severity="critical",
            occurred_at=when or timezone.now())


class TheKnockGoesOutWhenTheRowIsBornTest(PingFixture):
    """③ — **화면이 읽는 표가 늘면 화면이 두드려진다.**"""

    def test_recording_a_detection_knocks_the_room(self) -> None:
        with self.captureOnCommitCallbacks(execute=True):
            self._record(self.cams[0])
        got = _receive(self.layer, self.channel)
        self.assertIsNotNone(
            got,
            f"DetectionEvent 가 났는데 방 {self.room!r} 에 두드림이 안 왔다 — "
            f"화면은 주기 갱신(15초)까지 아무것도 모른다")
        self.assertEqual(PING_TYPE, got.get("type"),
                         "화면이 알아듣지 못하는 낱말로 나갔다")
        self.assertNotIn("event_id", got,
                         "두드림에 카드가 실렸다 — 목록이 두 벌이 된다. "
                         "무엇이 한 장인지는 목록 문 한 곳이 정한다")

    def test_a_folded_observation_also_knocks(self) -> None:
        """★ **접힌 것도 두드린다.** 접힘은 카드의 배지를 올리므로 화면이 바뀐다.

        새로 만들어진 것만 두드리면 「7건이 났는데 화면은 그대로」가 된다.
        """
        now = timezone.now()
        with self.captureOnCommitCallbacks(execute=True):
            first = self._record(self.cams[0], when=now)
        self.assertTrue(first.created)
        _receive(self.layer, self.channel)
        self._uncoalesce()

        with self.captureOnCommitCallbacks(execute=True):
            second = self._record(self.cams[0], when=now + timedelta(seconds=2))
        self.assertTrue(second.folded_into_existing,
                        "10초 창 안의 재발이 안 접혔다 — 시험이 그 갈래를 못 지났다")
        self.assertIsNotNone(_receive(self.layer, self.channel),
                             "접힌 관측이 화면을 안 두드렸다 — 배지가 안 오른다")

    def test_a_rolled_back_event_does_not_knock(self) -> None:
        """★ 부작위 — **커밋되지 않은 이벤트로 두드리지 않는다.**

        커밋 전에 두드리면 화면이 목록을 다시 읽는 순간 그 행이 아직 없고, 화면은
        다음 주기까지 아무것도 못 본다 — 두드림이 있으나 마나가 된다.
        """
        class _Rollback(Exception):
            pass

        with self.captureOnCommitCallbacks(execute=True):
            with contextlib.suppress(_Rollback):
                with transaction.atomic():
                    self._record(self.cams[0])
                    raise _Rollback
        self.assertIsNone(
            _receive(self.layer, self.channel, timeout=1.0),
            "롤백된 이벤트가 화면을 두드렸다 — 화면은 없는 것을 보러 간다")


class TheKnockDoesNotCareWhichPipelineTest(PingFixture):
    """④ — **갈래를 안 가린다.** 이것이 이 절의 실제 결함이었다.

    두드림이 gRPC 배선 한 곳에만 붙어 있으면, 그 배선을 지나지 않는 이벤트는
    화면을 영원히 안 두드린다. 맥박 군집 두절(OPS-15)이 정확히 그 경우였다 —
    **재난 징후인데 화면이 조용하다.**
    """

    def test_a_cluster_outage_event_also_knocks(self) -> None:
        from stream_monitors.services.camera_pulse import (PULSE_TIMEOUT,
                                                           record_frame,
                                                           scan_clusters)

        now = timezone.now()
        for cam in self.cams[:2]:
            record_frame(scope=self.scope_pipe, stream_monitor_id=cam.pk,
                         at=now - (PULSE_TIMEOUT + timedelta(minutes=1)))
        record_frame(scope=self.scope_pipe, stream_monitor_id=self.cams[2].pk,
                     at=now - timedelta(seconds=5))
        self._uncoalesce()

        with self.captureOnCommitCallbacks(execute=True):
            result = scan_clusters(scope=self.scope_pipe, now=now)
        self.assertEqual(1, result.created,
                         f"군집 두절이 안 났다 — 시험이 그 갈래를 못 지났다. "
                         f"판정: {[(n, v.fires) for (_z, n, v) in result.verdicts]}")
        self.assertIsNotNone(
            _receive(self.layer, self.channel),
            "군집 두절 이벤트가 화면을 안 두드렸다 — gRPC 배선 밖의 갈래가 "
            "화면에 영영 안 붙는다. 이 빨강이 이 절의 출발점이었다")

    def test_the_knock_is_not_wired_per_pipeline(self) -> None:
        """★ 부작위 — **갈래마다 손으로 부르는 배선이 아니다.**

        갈래마다 `ping_detection` 을 손으로 부르면 갈래가 하나 늘 때마다 조용히
        빠진다. 그것이 이 절의 병이었다: 부르는 곳이 **단 하나**였고, 나머지
        경로로 태어난 이벤트는 화면을 한 번도 두드리지 않았다.
        """
        src = (BACKEND / "surveillance/signals.py").read_text(
            encoding="utf-8", errors="replace")
        self.assertIn("post_save, sender=DetectionEvent", src,
                      "두드림이 행의 탄생이 아니라 어느 갈래에 매달려 있다")


class OnlyANewDetectionKnocksTest(PingFixture):
    """⑤ 부작위 — 판정·대응 저장은 **새 탐지가 아니다.**

    이 표는 판정(오탐)·대응 진행·종결로도 저장된다. 그때마다 두드리면 관제실
    화면 여럿이 아무것도 안 바뀐 목록을 밤새 다시 읽는다 — 두드림이 소음이 되고,
    소음이 된 신호는 다음 사람이 끈다.
    """

    def test_a_status_only_save_does_not_knock(self) -> None:
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        with self.captureOnCommitCallbacks(execute=True):
            recorded = self._record(self.cams[0])
        _receive(self.layer, self.channel)
        self._uncoalesce()

        row = Event._base_manager.get(pk=recorded.event_id)
        with self.captureOnCommitCallbacks(execute=True):
            row.save(update_fields=["severity"])
        self.assertIsNone(
            _receive(self.layer, self.channel, timeout=1.0),
            "새 탐지가 아닌 저장이 화면을 두드렸다 — 목록이 안 바뀌는데 다시 읽는다")
