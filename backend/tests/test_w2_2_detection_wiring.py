# -*- coding: utf-8 -*-
"""W2-2 배선 — **AI 검출이 실제로 이벤트가 되는가** (D-284).

★ 이 파일이 재는 것은 하나다: *검출이 버려지지 않는가.*
------------------------------------------------------
직전 턴의 실측은 이랬다 — `DetectionEvent` **정의 1건 · 사용 0건.**
AI 서버는 `Detection{x, y, width, height, label, confidence, color}` 를 **이미**
돌려주고 있었는데(`frame_detection.proto`), `grpc_client` 가 이미지만 디코딩하고
`detections` 를 통째로 버렸다. **검출이 없던 게 아니라 받아서 버리고 있었다.**

    D-284: *"추가 AI 개발 없이 배선만으로 탐지가 살아난다."*

그래서 여기서는 **AI 서버 없이** 판정한다. 필요한 것은 AI 가 아니라 배선이고,
배선은 proto 모양의 응답만 있으면 잴 수 있다. AI 서버를 띄워야만 도는 시험은
띄울 수 없는 날 **조용히 skip 되고**, skip 된 시험은 아무것도 지키지 않는다.

무엇을 **아직 못 재나** — 지우지 않고 적는다 (D-262)
----------------------------------------------------
**AI 서버가 실제로 어떤 라벨 문자열을 쓰는지 재지 못했다.** `AI_GRPC_URL` 이 이 PC 에서
닿지 않는다(`media-ai.invalid`). 그래서 `LABEL_TO_EVENT_TYPE` 에는 계약 열거값과 **글자가
같은 것만** 넣었고, 그 밖의 라벨은 **세어서 돌려준다**(`unmapped_labels`).
아래 `test_unknown_labels_are_counted_not_dropped` 가 그 약속을 고정한다 —
모르는 것을 아는 척하지도, 조용히 버리지도 않는다.
"""
from __future__ import annotations

import contextlib
from types import SimpleNamespace

from django.apps import apps
from django.test import TestCase


def _fake_detection(label, x=10, y=20, w=30, h=40, confidence=0.9, color="#ff0000"):
    """proto `Detection` 의 오리 타입. **필드 이름을 proto 실측 그대로** 쓴다.

    이름이 어긋나면 시험은 초록인데 실물은 깨진다 — 가짜를 쓸 때 가장 흔한 실패다.
    실측(frame_detection_pb2): x · y · width · height · label · confidence · color.
    """
    return SimpleNamespace(x=x, y=y, width=w, height=h,
                           label=label, confidence=confidence, color=color)


def _tiny_jpeg(width=8, height=8) -> bytes:
    """진짜 JPEG 바이트. **빈 바이트를 쓰지 않는다.**

    처음엔 `image_data=b""` 로 뒀는데 `cv2.imdecode` 가 거기서 죽었다 — 시험이
    배선이 아니라 **가짜의 결함**으로 빨개졌다. 가짜는 실물이 받는 것과 같은 모양이어야 한다.
    """
    import cv2
    import numpy as np

    ok, buf = cv2.imencode(".jpg", np.zeros((height, width, 3), dtype=np.uint8))
    assert ok, "시험용 JPEG 인코딩 실패"
    return buf.tobytes()


def _fake_frame_with_detections(detections, frame_w=640, frame_h=480):
    """proto `FrameWithDetections` 의 오리 타입 — `frame` + `detections`."""
    return SimpleNamespace(
        frame=SimpleNamespace(image_data=_tiny_jpeg(), width=frame_w, height=frame_h,
                              timestamp=0, format="jpeg"),
        detections=detections,
    )


class BboxNormalizationTest(TestCase):
    """[계약] bbox 는 **정규화 좌표(0.0~1.0)** 다 — 픽셀을 그대로 넣지 않는다.

    `docs/contracts/detection-event.md`:
        *"정규화 좌표(0.0~1.0)를 쓴다. 해상도가 바뀌어도 값이 유효하다.
          원본 픽셀 좌표를 쓰지 않는다 — 파이프라인 교체 시 입력 해상도가 달라진다."*

    proto 는 픽셀 정수를 준다. 받는 자리에서 나누지 않으면 픽셀값이 DB 에 쌓이고,
    입력 해상도가 바뀌는 날 **이미 쌓인 bbox 가 전부 뜻을 잃는다.** 되돌릴 수 없다.
    """

    def test_pixels_become_normalized_coordinates(self) -> None:
        from stream_monitors.services.grpc_client import _detections_to_dicts

        fwd = _fake_frame_with_detections(
            [_fake_detection("person", x=64, y=48, w=128, h=96)],
            frame_w=640, frame_h=480)

        out = _detections_to_dicts(fwd)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["bbox"], {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2})
        # 원본 픽셀도 **버리지 않는다** — 정규화가 틀렸을 때 되짚을 근거가 남아야 한다.
        self.assertEqual(out[0]["pixel"], {"x": 64, "y": 48, "w": 128, "h": 96})

    def test_unknown_frame_size_gives_none_not_zero(self) -> None:
        """프레임 크기를 모르면 bbox 는 **None** — 0 으로 채우지 않는다.

        0 은 "왼쪽 위 모서리의 점"이라는 **뜻이 있는 값**이다. 모르는 것을 0 으로 채우면
        그것은 모른다는 사실을 지우고 아는 척하는 것이다.
        """
        from stream_monitors.services.grpc_client import _detections_to_dicts

        fwd = _fake_frame_with_detections([_fake_detection("fire")], frame_w=0, frame_h=0)
        out = _detections_to_dicts(fwd)

        self.assertIsNone(out[0]["bbox"])
        self.assertIn("프레임 크기를 알 수 없다", out[0]["bbox_unavailable_reason"])
        # ★ 사유가 남는가. None 만 보면 "검출이 없다"와 구별되지 않는다.
        self.assertIsNotNone(out[0]["bbox_unavailable_reason"])


class DetectionsSurviveTheClientTest(TestCase):
    """[D-284 (1)] `process_frame_batch` 가 검출을 **버리지 않는가.**

    이것이 이 파일의 과녁이다. 다른 시험이 전부 초록이어도 이 하나가 빨가면
    검출은 여전히 사라진다.
    """

    def _run_batch(self, response):
        """`FrameDetectionClient.process_frame_batch` 를 **AI 서버 없이** 돌린다."""
        import numpy as np

        from stream_monitors.services import grpc_client as gc

        client = gc.FrameDetectionClient.__new__(gc.FrameDetectionClient)
        client.connected = True
        client.stub = SimpleNamespace(ProcessFrames=lambda request: response)

        frames = [np.zeros((480, 640, 3), dtype=np.uint8)]
        return client.process_frame_batch(frames)

    def test_detections_reach_metadata(self) -> None:
        response = SimpleNamespace(
            batch_id="b1", processing_time_ms=12, timestamp=0,
            processed_frames=[
                _fake_frame_with_detections([
                    _fake_detection("person", x=64, y=48, w=128, h=96),
                    _fake_detection("fire", x=0, y=0, w=640, h=480),
                ]),
            ],
        )
        _frames, metadata = self._run_batch(response)

        self.assertIn("detections", metadata,
                      "metadata 에 detections 가 없다 — 클라이언트가 다시 버리고 있다 (D-284 회귀)")
        self.assertEqual(metadata["detection_count"], 2)
        self.assertEqual([d["label"] for d in metadata["detections"][0]],
                         ["person", "fire"])

    def test_zero_detections_is_not_the_same_as_no_wiring(self) -> None:
        """★ **검출 0건**과 **배선 없음**을 가른다.

        전에는 둘 다 "metadata 에 아무것도 없음"이었다. 그러면 "AI 가 아무것도 못 찾았다"와
        "우리가 받아서 버렸다"가 같은 모양이 되고, 그 둘이 구별되지 않는 한
        누구도 배선이 끊긴 것을 알아챌 수 없다.
        """
        response = SimpleNamespace(
            batch_id="b2", processing_time_ms=3, timestamp=0,
            processed_frames=[_fake_frame_with_detections([])],
        )
        _frames, metadata = self._run_batch(response)

        self.assertEqual(metadata["detection_count"], 0)
        self.assertEqual(metadata["detections"], [[]])   # 키는 **있다**. 값이 빈 것뿐이다.


class BridgeToKernelTest(TestCase):
    """[D-284 (1)] 검출 → K1 이벤트. **중복 억제는 커널이 한다** (여기서 다시 하지 않는다)."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        CoreUser = apps.get_model("user", "CoreUser")
        UserGroup = apps.get_model("user", "UserGroup")
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group = UserGroup.objects.create(name="w22-tenant")
        UserGroup.objects.filter(pk=cls.group.pk).update(created_by=None)
        cls.user = CoreUser.objects.create_user(
            username="w22_user", password="test-only-not-a-secret", is_active=True,
            email="w22@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: cls.user, "group": cls.group})

        sm = StreamMonitor.objects.create(
            name="w22-stream", code="w22-stream", ip_source="rtsp://test.invalid/x")
        from kernels.k1_event.services import _owner_field

        if _owner_field(StreamMonitor) == "groups":
            sm.groups.set([cls.group])
        else:
            sm.group = cls.group
            sm.save(update_fields=["group"])
        cls.stream = sm

    def _publish(self, detections_per_frame):
        from stream_monitors.services.detection_event_bridge import publish_detections

        return publish_detections(
            stream_monitor_id=self.stream.id,
            detections_per_frame=detections_per_frame,
            reason="시험 — 파이프라인에는 요청자가 없다",
        )

    def test_known_labels_become_events(self) -> None:
        """★ 과녁 — 검출이 **행으로 남는가.** 이 시험 전까지 사용처는 0건이었다."""
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        before = Event._base_manager.count()

        result = self._publish([[{"label": "fire", "confidence": 0.93, "bbox": None}]])

        self.assertEqual(result.created, 1)
        self.assertEqual(Event._base_manager.count(), before + 1)
        row = Event._base_manager.order_by("-id").first()
        self.assertEqual(row.event_type, "fire")
        self.assertEqual(row.severity, "critical")   # P-W2-2-1 잠정표

    def test_event_inherits_tenant_from_stream(self) -> None:
        """소유는 **스트림이 정한다.** 주인 없는 행은 §0.4 OR 절을 타고 모두에게 보인다.

        W0-13 백필 25,296행이 되돌린 것이 정확히 그 상태다 — 배선이 그것을 다시 만들면 안 된다.
        """
        from common.tenant_scope import TenantScope
        from kernels.k1_event import query_events

        self._publish([[{"label": "person", "confidence": 0.7, "bbox": None}]])

        mine = query_events(scope=TenantScope.of(self.user))
        self.assertTrue(mine, "배선이 만든 이벤트가 소유자에게 안 보인다 — 소유가 비었다")
        self.assertEqual(mine[0].event_type, "person")

    def test_unknown_labels_are_counted_not_dropped(self) -> None:
        """★ 모르는 라벨을 **버리지 않고 센다.**

        버리면 "검출이 없었다"와 "옮길 줄 몰랐다"가 구별되지 않는다. 그 구별이 사라지는 것이
        이 배선이 고치려는 바로 그 병이다. 이 목록이 곧 표를 늘릴 근거다 (D-273).
        """
        result = self._publish([[
            {"label": "dog", "confidence": 0.8, "bbox": None},
            {"label": "car", "confidence": 0.8, "bbox": None},
            {"label": "dog", "confidence": 0.6, "bbox": None},
        ]])

        self.assertEqual(result.created, 0)
        self.assertEqual(result.unmapped_labels, {"dog": 2, "car": 1})
        # 분모가 맞는가 — 본 것이 3건이다 (D-271: 분모 없는 초록은 보고가 아니다).
        self.assertEqual(result.total_seen, 3)

    def test_dedup_is_the_kernels_job_not_the_bridges(self) -> None:
        """[F-04 × U1] 배선은 중복 억제를 **하지 않는다** — 커널이 이미 한다.

        두 벌을 두면 어긋나고, 그 어긋남은 아무도 못 본다. 여기서는 커널의 두 창이
        배선을 통해서도 그대로 살아 있는지만 본다: 같은 것 3연발 → **이벤트 1 · 알림 1.**
        """
        result = self._publish([[
            {"label": "smoke", "confidence": 0.5, "bbox": None},
            {"label": "smoke", "confidence": 0.9, "bbox": None},
            {"label": "smoke", "confidence": 0.7, "bbox": None},
        ]])

        self.assertEqual(result.total_seen, 3)
        self.assertEqual(result.created, 1, "10초 창이 안 먹었다 — 커널의 중복 억제가 새고 있다")
        self.assertEqual(result.folded, 2)
        self.assertEqual(result.to_notify, 1, "5분 창이 안 먹었다 — F-04 가 깨진다")
        # ★ confidence 는 **높은 쪽**이 남는다 (커널 규약) — 접힌 관측 중 가장 확실한 것이
        #   증거로서 값이 있다. 마지막 값(0.7)으로 덮이면 안 된다.
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        self.assertAlmostEqual(
            Event._base_manager.order_by("-id").first().confidence, 0.9, places=5)

    def test_bridge_uses_a_system_scope_with_a_reason(self) -> None:
        """[D-281] 배선은 **사유 있는 시스템 스코프**로 커널을 부른다.

        사유 없는 시스템 스코프는 만들어지지 않는다 — 면제가 아니라 등재이기 때문이다.
        """
        from stream_monitors.services.detection_event_bridge import publish_detections

        with self.assertRaises(ValueError):
            publish_detections(stream_monitor_id=self.stream.id,
                               detections_per_frame=[], reason="")


class SnapshotTest(BridgeToKernelTest):
    """[W2-2 spec] **스냅샷 1장을 MinIO 에** — 그리고 못 올렸을 때 무엇을 남기나.

        W2-2 spec: *"스냅샷 1장을 MinIO 에 저장하고 snapshot_path 에 기록한다."*
        계약 불변규칙 4: *"스냅샷은 MinIO 에 1장. 원본 프레임을 DB 에 넣지 않는다."*

    ★ 이 시험의 절반은 **실패 경로**다. 이 PC 에서 MinIO 는 닿지 않고(`minio.invalid`),
      운영에서도 저장소는 언제든 죽는다. 그때 무엇이 남는지가 "저장했다"는 거짓말과
      "증거가 없다"는 사실을 가른다 (D-284).
    """

    def _frame(self):
        import numpy as np

        return np.zeros((480, 640, 3), dtype=np.uint8)

    def test_snapshot_path_is_recorded_when_upload_succeeds(self) -> None:
        from unittest.mock import patch

        from stream_monitors.services.detection_event_bridge import publish_detections

        with patch("stream_monitors.services.detection_snapshot.upload_snapshot",
                   return_value=("gx-bucket/detections/1/20260829/120000_000000.jpg", "")):
            result = publish_detections(
                stream_monitor_id=self.stream.id,
                detections_per_frame=[[{"label": "fire", "confidence": 0.9, "bbox": None}]],
                frames=[self._frame()],
                reason="시험")

        self.assertEqual(result.snapshots_uploaded, 1)
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        row = Event._base_manager.order_by("-id").first()
        self.assertTrue(row.snapshot_path.endswith(".jpg"))

    def test_failed_upload_leaves_an_empty_path_not_a_fake_one(self) -> None:
        """★ 못 올리면 **빈 문자열**이다. 있지도 않은 객체를 가리키지 않는다.

        가짜 경로는 화면이 믿고 깨진 이미지를 띄우게 만든다 — D-284 가 이름 붙인
        조용한 성공이다. **그리고 이벤트는 그래도 기록된다** — 스냅샷이 없다고
        검출을 버리는 것이 더 나쁘다.
        """
        from unittest.mock import patch

        from stream_monitors.services.detection_event_bridge import publish_detections

        with patch("stream_monitors.services.detection_snapshot.upload_snapshot",
                   return_value=("", "MinIO 가 사용 불가 상태다(초기화 실패)")):
            result = publish_detections(
                stream_monitor_id=self.stream.id,
                detections_per_frame=[[{"label": "smoke", "confidence": 0.8, "bbox": None}]],
                frames=[self._frame()],
                reason="시험")

        self.assertEqual(result.snapshots_uploaded, 0)
        self.assertEqual(sum(result.snapshot_failures.values()), 1)
        # ★ 사유가 남는가. 빈 경로만 보면 "안 올림"과 "못 올림"이 구별되지 않는다.
        self.assertTrue(any("MinIO" in why for why in result.snapshot_failures))

        # ★ 그래도 이벤트는 있다.
        self.assertEqual(result.created, 1)
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        self.assertEqual(Event._base_manager.order_by("-id").first().snapshot_path, "")

    def test_one_snapshot_per_event_type_not_per_detection(self) -> None:
        """계약이 "1장"이라 적었다 — 검출마다 올리면 배치 하나가 저장소를 수십 번 두드린다."""
        from unittest.mock import patch

        from stream_monitors.services.detection_event_bridge import publish_detections

        with patch("stream_monitors.services.detection_snapshot.upload_snapshot",
                   return_value=("b/o.jpg", "")) as up:
            result = publish_detections(
                stream_monitor_id=self.stream.id,
                detections_per_frame=[[
                    {"label": "person", "confidence": 0.9, "bbox": None},
                    {"label": "person", "confidence": 0.8, "bbox": None},
                    {"label": "fire", "confidence": 0.7, "bbox": None},
                ]],
                frames=[self._frame()],
                reason="시험")

        self.assertEqual(up.call_count, 2, "종류당 1장이어야 한다 (person · fire)")
        # 접혀서 쓰이지 않은 장수를 **숨기지 않고 센다.**
        self.assertEqual(result.snapshots_uploaded, 2)
        self.assertEqual(result.snapshots_discarded, 0)

    def test_no_frames_means_no_upload_attempt(self) -> None:
        """양성 대조 — 프레임을 안 주면 **올리려 들지 않는다.**

        전부 올리려 드는 배선은 저장소가 없을 때 배치마다 실패 로그를 쏟는다.
        """
        from unittest.mock import patch

        from stream_monitors.services.detection_event_bridge import publish_detections

        with patch("stream_monitors.services.detection_snapshot.upload_snapshot") as up:
            publish_detections(
                stream_monitor_id=self.stream.id,
                detections_per_frame=[[{"label": "fire", "confidence": 0.9, "bbox": None}]],
                reason="시험")
        up.assert_not_called()

    def test_upload_refuses_empty_bytes_with_a_reason(self) -> None:
        """빈 바이트는 **사유와 함께** 거절한다 — 조용히 성공하지 않는다."""
        from stream_monitors.services.detection_snapshot import encode_frame, upload_snapshot

        path, why = upload_snapshot(stream_monitor_id=1, jpeg_bytes=b"")
        self.assertEqual(path, "")
        self.assertTrue(why, "빈 경로에 사유가 없으면 '안 올림'과 '못 올림'이 구별되지 않는다")

        # 인코딩 실패도 예외가 아니라 빈 바이트다 — 스트림이 죽으면 안 된다.
        self.assertEqual(encode_frame(None), b"")


class LiveCallSiteTest(TestCase):
    """[D-284 (1)] **실호출 경로**가 배선을 부르는가.

    ★ 왜 이것을 따로 재나 — 함수가 있는 것과 **불리는 것**은 다르다.
      `detection_event_bridge` 만 시험하면 "만들어는 뒀다"까지만 증명된다.
      직전 턴에 `DetectionEvent` 가 **정의 1건 · 사용 0건**이었던 것이 정확히 그 상태다.
    """

    def test_wiring_helper_is_called_from_the_stream_loop(self) -> None:
        """gRPC 배치 처리 뒤에 `_publish_detection_events` 호출이 **소스에 있는가**."""
        import ast
        import inspect

        from stream_monitors.services import grpc_dual_stream_service as svc

        src = inspect.getsource(svc)
        tree = ast.parse(src)
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertIn(
            "_publish_detection_events", called,
            "실호출 경로가 배선을 부르지 않는다 — 배선은 있는데 아무도 안 쓴다 (D-284 회귀)")

    def test_missing_detections_key_is_reported_not_ignored(self) -> None:
        """metadata 에 `detections` 키가 아예 없으면 **에러 로그가 난다.**

        키가 없다는 것은 `grpc_client` 가 검출을 다시 버리기 시작했다는 뜻이다.
        조용히 지나가면 그 회귀를 아무도 못 본다.
        """
        from stream_monitors.services.grpc_dual_stream_service import (
            _publish_detection_events,
        )

        with self.assertLogs("stream_monitors.services.grpc_dual_stream_service",
                             level="ERROR") as logs:
            _publish_detection_events(self.__class__.__name__, {"batch_id": "x"})
        self.assertTrue(any("detections" in line for line in logs.output))

    def test_zero_detections_does_not_log_an_error(self) -> None:
        """양성 대조 — **검출 0건은 정상이다.** 전부 에러를 내는 탐지기는 탐지기가 아니다."""
        import logging

        from stream_monitors.services.grpc_dual_stream_service import (
            _publish_detection_events,
        )

        logger_name = "stream_monitors.services.grpc_dual_stream_service"
        with self.assertNoLogs(logger_name, level=logging.ERROR):
            _publish_detection_events(1, {"detections": [[]], "detection_count": 0})


class SilentSuccessSurveyTest(TestCase):
    """[D-284 (3)] 조용한 성공 조사기가 **자기 시험을 통과하는가.**

    조사 결과(39건)는 사람이 읽을 목록이지 판정이 아니다. 여기서 고정하는 것은
    **조사기 자신**이다 — 조사기가 눈이 멀면 그 목록은 "결함 없음"의 다른 이름이 된다.

    ★ 이 조사기는 처음에 **실제 과녁을 놓쳤다.** 고치기 전 `detect_and_save`
      (`return True, results`)를 0건으로 셌다. 합성 대조 7건은 전부 통과하는데
      진짜 하나를 못 잡은 것 — 착시 ④(D-277)를 그대로 재현한 셈이다.
      그래서 그 모양을 대조에 넣었고(`unconditional_ok`), 아래에서 다시 고정한다.
    """

    def _script(self):
        from pathlib import Path

        for root in ("/repo", *Path(__file__).resolve().parents[1:4]):
            p = Path(root) / "scripts" / "scan_silent_success.py"
            if p.is_file():
                return p
        return None

    def test_survey_self_test_passes(self) -> None:
        import subprocess
        import sys

        script = self._script()
        self.assertIsNotNone(script, "scan_silent_success.py 를 찾지 못했습니다 (D-284 (3))")
        out = subprocess.run([sys.executable, str(script), "--self-test"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_the_original_target_is_caught(self) -> None:
        """★ 진짜 과녁 — `return True, <데이터>` 모양을 잡는가.

        합성 대조가 아니라 **이 조사를 하게 만든 실제 코드 모양**이다.
        """
        import importlib.util
        import tempfile
        from pathlib import Path

        script = self._script()
        self.assertIsNotNone(script)
        spec = importlib.util.spec_from_file_location("scan_silent_success", script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "target.py"
            f.write_text(
                'def detect_and_save(d):\n'
                '    """Detect media files and save results to VideoAnalysis."""\n'
                '    results = detect_media(d)\n'
                '    created_records = []\n'
                '    return True, results\n',
                encoding="utf-8")
            rows = mod.scan_file(f)

        self.assertTrue(rows, "조사기가 실제 과녁을 놓쳤습니다 — 합성 대조만 통과하는 탐지기다 (D-277)")
        self.assertEqual(rows[0]["grade"], "high")
