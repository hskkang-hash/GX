# -*- coding: utf-8 -*-
"""FX-5 주소 자동 변환 — **저하 운전이 첫 요구사항이다** (D-298 · D-290 · D-300).

넷으로 나뉜다:

    AddressStatusTest        네 상태가 **서로 다른 사실**을 말하는가 (D-290)
    DegradedOperationTest    주소가 죽어도 **이벤트는 나는가** (C-3.3 · W0-17)
    AlertBodyTest            상태에 따라 알림 문장이 갈리는가
    NothingWasGuessedTest    응답 필드를 **추측하지 않았는가** (D-300 · D-280)

한 문장
-------
    주소는 보조 정보다. **주소가 이벤트를 끌고 내려가면 그것이 장애다.**
"""
from __future__ import annotations

import contextlib
from pathlib import Path

from django.apps import apps
from django.core import mail
from django.test import SimpleTestCase, TestCase, override_settings

from adapters import juso
from common.tenant_scope import TenantScope

#: 컨테이너에서는 backend 가 `/app`, 저장소 문서는 `/repo` 에 따로 마운트된다.
#: `test_k1_event_kernel.py` · `test_zone_judgment.py` 와 **같은 방식**으로 찾는다.
REPO_ROOT_CANDIDATES = ("/repo",)


def _find_repo_file(relative: str):
    """저장소 파일의 실경로. 없으면 `None` — **추측하지 않는다.**"""
    here = Path(__file__).resolve()
    for root in (*(Path(c) for c in REPO_ROOT_CANDIDATES), *here.parents[1:4]):
        candidate = root / relative
        if candidate.is_file():
            return candidate
    return None


class _DeadAddressPort(juso.AddressPort):
    """부르면 죽는 포트 — 저하 변형용 (규약 ④)."""

    def lookup(self, *, lat, lng, timeout):
        raise ConnectionError("FX-5 저하 변형 — 주소 API 가 죽었다")


class _SlowAddressPort(juso.AddressPort):
    """타임아웃을 **받았는지** 보는 포트. 값을 그대로 기록한다."""

    seen: float | None = None

    def lookup(self, *, lat, lng, timeout):
        type(self).seen = timeout
        raise TimeoutError("느리다")


class _WorkingAddressPort(juso.AddressPort):
    """도로명 주소를 돌려주는 포트. **합성이지만 인터페이스는 실물이다.**"""

    def lookup(self, *, lat, lng, timeout):
        return "경기도 안양시 만안구 안양천서로 100"


class _EmptyAddressPort(juso.AddressPort):
    """부르면 되는데 그 좌표에 도로명이 없는 경우 — 하천·산지에서 실제로 난다."""

    def lookup(self, *, lat, lng, timeout):
        return None


class AddressStatusTest(SimpleTestCase):
    """★ 네 상태가 **서로 다른 사실**을 말하는가 (D-290).

    'pending'(아직 안 함)과 'failed'(했는데 실패)를 같은 값으로 두면 재시도 대상
    목록이 만들어지지 않는다 — 실패한 것이 영원히 pending 인 척하거나, 아직 안 한
    것이 실패로 세어진다. 둘 다 조용한 유실이다.
    """

    def test_no_coordinates_is_disabled_not_pending(self) -> None:
        """★ 좌표가 없으면 **재시도 대상이 아니다.** pending 으로 두면 영원히 못 푼다."""
        result = juso.resolve(lat=None, lng=None)
        self.assertEqual("disabled", result.status)
        self.assertTrue(result.reason)

    def test_no_port_is_disabled_with_a_reason(self) -> None:
        self.assertIsNone(juso.current(), "시험 시작 전에 포트가 꽂혀 있습니다.")
        result = juso.resolve(lat=37.40, lng=126.92)
        self.assertEqual("disabled", result.status)
        self.assertIn("실측", result.reason)

    def test_a_dead_port_is_failed_not_disabled(self) -> None:
        """★ **꽂혀 있는데 죽은 것**과 **안 꽂힌 것**은 다른 사실이다."""
        self.addCleanup(juso.register(_DeadAddressPort()))
        result = juso.resolve(lat=37.40, lng=126.92)
        self.assertEqual("failed", result.status)
        self.assertIn("좌표", result.reason)

    def test_a_working_port_resolves(self) -> None:
        self.addCleanup(juso.register(_WorkingAddressPort()))
        result = juso.resolve(lat=37.40, lng=126.92)
        self.assertEqual("resolved", result.status)
        self.assertIn("안양천서로", result.address)

    def test_no_road_name_is_failed_not_resolved(self) -> None:
        """빈 답을 'resolved' 로 읽지 않는다 — 빈 주소는 주소가 아니다."""
        self.addCleanup(juso.register(_EmptyAddressPort()))
        result = juso.resolve(lat=37.40, lng=126.92)
        self.assertEqual("failed", result.status)
        self.assertIsNone(result.address)

    def test_timeout_is_passed_down(self) -> None:
        """★ C-3.3 — 타임아웃은 **인자로 내려간다.** 구현체 기본값에 맡기지 않는다."""
        self.addCleanup(juso.register(_SlowAddressPort()))
        juso.resolve(lat=37.40, lng=126.92)
        self.assertEqual(juso.TIMEOUT_SECONDS, _SlowAddressPort.seen)
        self.assertIsNotNone(_SlowAddressPort.seen, "타임아웃 없이 외부를 불렀습니다.")

    def test_register_refuses_something_that_is_not_the_port(self) -> None:
        class NotAPort:
            def lookup(self, **kwargs):
                return "x"

        with self.assertRaises(TypeError):
            juso.register(NotAPort())

    def test_the_model_enum_and_the_adapter_agree(self) -> None:
        """★ 열거를 두 벌로 두면 갈린다 — 어댑터의 상태 문자열은 모델의 것과 같아야 한다."""
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        model_values = {v for v, _ in Event.AddressStatus.choices}
        self.assertEqual({"pending", "resolved", "failed", "disabled"}, model_values)
        for status in ("disabled", "failed", "resolved"):
            self.assertIn(status, model_values,
                          f"어댑터가 내는 '{status}' 를 모델이 모릅니다.")


class _EventFixture(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        UserGroup = apps.get_model("user", "UserGroup")
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group = UserGroup.objects.create(name="fx5-tenant")
        UserGroup.objects.filter(pk=cls.group.pk).update(created_by=None)
        cls.stream = cls._stream("fx5-cam", cls.group)
        cls.scope_pipe = TenantScope.system(
            reason="FX-5 시험 — 파이프라인에는 요청자가 없다 (D-281)")
        #: 읽기에는 사람이 필요하다 — 시스템 스코프로 읽으면 그것이 전역 조회이고,
        #: 전역 조회는 격리가 아니라 격리의 부재다 (D-281 `require_actor`).
        cls.reader = cls._reader("fx5_reader", cls.group)
        cls.scope_read = TenantScope.of(cls.reader)

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
    def _stream(cls, name, group):
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        return cls._own(StreamMonitor.objects.create(
            name=name, code=name, ip_source="rtsp://fx5.invalid/x"), group)

    @classmethod
    def _reader(cls, username, group):
        CoreUser = apps.get_model("user", "CoreUser")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": group})
        return user


class DegradedOperationTest(_EventFixture):
    """★ **주소가 죽어도 이벤트는 난다** (C-3.3 · W0-17 · 저하 운전)."""

    def _publish(self, **kwargs):
        from stream_monitors.services.detection_event_bridge import publish_detections

        return publish_detections(
            stream_monitor_id=self.stream.pk,
            detections_per_frame=[[{"label": "fire", "confidence": 0.9}]],
            reason="FX-5 저하 시험 — AI 파이프라인 배선에는 요청자가 없다",
            **kwargs)

    def test_event_is_created_when_the_address_api_is_dead(self) -> None:
        self.addCleanup(juso.register(_DeadAddressPort()))
        result = self._publish(lat=37.40, lng=126.92)

        self.assertEqual(1, result.created, "주소 장애가 이벤트 생성을 끌고 내려갔습니다.")
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        row = Event._base_manager.get(pk=result.event_ids[0])
        self.assertEqual("failed", row.address_status)
        self.assertIsNone(row.address)
        # 좌표는 남는다 — 주소를 못 얻었을 때 사람이 볼 유일한 위치다.
        self.assertEqual(37.40, row.lat)

    def test_event_is_created_when_no_port_is_plugged(self) -> None:
        result = self._publish(lat=37.40, lng=126.92)
        self.assertEqual(1, result.created)
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        self.assertEqual("disabled",
                         Event._base_manager.get(pk=result.event_ids[0]).address_status)

    def test_without_coordinates_it_is_disabled_not_pending(self) -> None:
        """★ 좌표 없는 이벤트가 **재시도 목록에 쌓이지 않는다.**"""
        self.addCleanup(juso.register(_WorkingAddressPort()))
        result = self._publish()
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        row = Event._base_manager.get(pk=result.event_ids[0])
        self.assertEqual("disabled", row.address_status)
        self.assertIsNone(row.address)

    def test_positive_control_a_working_port_puts_the_address_on_the_event(self) -> None:
        """★ 양성 대조 — 위 셋이 초록인 이유가 '아무것도 안 해서'가 아님을 잰다 (D-289)."""
        self.addCleanup(juso.register(_WorkingAddressPort()))
        result = self._publish(lat=37.40, lng=126.92)
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        row = Event._base_manager.get(pk=result.event_ids[0])
        self.assertEqual("resolved", row.address_status)
        self.assertIn("안양천서로", row.address)

    def test_the_address_api_is_called_once_per_batch(self) -> None:
        """검출마다 부르지 않는다 — 같은 좌표에 같은 답이 오고, 외부를 열 번 두드린다."""
        calls: list[tuple] = []

        class _Counting(juso.AddressPort):
            def lookup(self, *, lat, lng, timeout):
                calls.append((lat, lng))
                return "경기도 안양시 만안구 안양천서로 100"

        self.addCleanup(juso.register(_Counting()))
        from stream_monitors.services.detection_event_bridge import publish_detections

        publish_detections(
            stream_monitor_id=self.stream.pk,
            detections_per_frame=[[{"label": "fire", "confidence": 0.9},
                                   {"label": "person", "confidence": 0.8},
                                   {"label": "smoke", "confidence": 0.7}]],
            reason="FX-5 호출 횟수 시험",
            lat=37.40, lng=126.92)
        self.assertEqual(1, len(calls), f"배치 하나에 주소를 {len(calls)}번 불렀습니다.")

    def test_kernel_view_carries_the_address(self) -> None:
        """App 이 모델을 타고 들어가지 않게 커널 값이 주소를 담는다 (DA-04 §1-4)."""
        from kernels.k1_event import get_event, record_detection

        self.addCleanup(juso.register(_WorkingAddressPort()))
        located = juso.resolve(lat=37.40, lng=126.92)
        recorded = record_detection(
            scope=self.scope_pipe, stream_monitor_id=self.stream.pk,
            event_type="fire", severity="critical", snapshot_path="minio://fx5/1.jpg",
            lat=37.40, lng=126.92,
            address=located.address, address_status=located.status)
        view = get_event(recorded.event_id, scope=self.scope_read)
        self.assertEqual("resolved", view.address_status)
        self.assertIn("안양천서로", view.address)


#: ★ P-41 (2026-09-05) — **실발송 허용 도메인이 채널보다 앞에 선다.**
#:   `EmailChannel` 은 목록 밖 도메인을 `send_mail` 앞에서 **로그 어댑터로**
#:   떨어뜨린다. 그래서 「메일이 실제로 나갔다」를 재는 시험은 **어느 도메인을
#:   허용했는지 스스로 밝혀야** 한다. 밝히지 않고 초록이 서면 그 초록은
#:   운영에서 재현되지 않는다 — 운영의 목록은 비어 있기 때문이다.
#:   강제: `scripts/verify_send_allowlist.py`
@override_settings(K2_SEND_ALLOWED_DOMAINS=["test.invalid"])
class AlertBodyTest(_EventFixture):
    """상태에 따라 **알림 문장이 갈리는가** — 갈리지 않으면 받는 사람은 구별할 수 없다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        super().setUpTestData()
        Role = apps.get_model("role", "Role")
        CoreUser = apps.get_model("user", "CoreUser")
        Rule = apps.get_model("stream_monitors", "NotificationRule")

        cls.role = cls._own(Role.objects.create(role_name="fx5_chief", code="fx5_chief"),
                            cls.group)
        user = CoreUser.objects.create_user(
            username="fx5_chief_user", password="test-only-not-a-secret",
            is_active=True, email="fx5@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": cls.group})
        user.roles.add(cls.role)
        cls.user = user
        cls._own(Rule.objects.create(severity="critical", role=cls.role,
                                     channels=["email"], is_active=True), cls.group)
        cls.scope = TenantScope.of(user)

    def _send_with(self, *, address, address_status, lat=37.40, lng=126.92):
        from kernels.k1_event import record_detection
        from kernels.k2_notify import send

        recorded = record_detection(
            scope=self.scope_pipe, stream_monitor_id=self.stream.pk,
            event_type="fire", severity="critical", snapshot_path="minio://fx5/1.jpg",
            lat=lat, lng=lng, address=address, address_status=address_status)
        mail.outbox.clear()
        send(scope=self.scope, event_id=recorded.event_id)
        return mail.outbox[0].body

    def test_resolved_shows_the_address_and_not_the_coordinates(self) -> None:
        body = self._send_with(address="경기도 안양시 만안구 안양천서로 100",
                               address_status="resolved")
        self.assertIn("안양천서로", body)
        self.assertNotIn("126.92", body,
                         "주소를 얻었는데 좌표까지 실렸습니다 — 유출 표면을 넓힐 이유가 없습니다.")

    def test_failed_shows_the_coordinates_so_a_person_can_open_a_map(self) -> None:
        """D-298 이 명시적으로 요구한 문장 — '주소 확인 불가(좌표: …)'."""
        body = self._send_with(address=None, address_status="failed")
        self.assertIn("주소 확인 불가", body)
        self.assertIn("126.92", body)

    def test_disabled_says_the_location_is_unknown(self) -> None:
        body = self._send_with(address=None, address_status="disabled",
                               lat=None, lng=None)
        self.assertIn("미상", body)
        self.assertNotIn("주소 확인 불가", body,
                         "조회 대상이 아닌 것과 조회 실패가 같은 문장으로 나갔습니다.")


class NothingWasGuessedTest(SimpleTestCase):
    """★ **그 이상을 만들지 않았는가** — 부작위 시험 (D-300 · D-280 · D-298).

    juso.go.kr 의 **응답 스키마를 실측하지 않았다.** 추측한 필드명 위의 파서는 첫
    실호출에서 전부 재작업이 되고, 그때는 그것이 추측이었다는 사실조차 남지 않는다.
    """

    def _src(self) -> str:
        return Path(juso.__file__).read_text(encoding="utf-8")

    def test_no_http_implementation_exists(self) -> None:
        src = self._src()
        for token in ("requests.", "urllib.request", "httpx.", "http.client"):
            self.assertNotIn(
                token, src,
                f"HTTP 구현({token})이 들어왔습니다 — 응답 스키마가 미실측인 채로 "
                f"파서를 쓰면 첫 실호출에서 전부 재작업입니다 (D-280 · D-298).")

    def test_no_response_field_names_are_written_down(self) -> None:
        """저쪽 필드 이름을 한 개도 적지 않았다 — 적는 순간 그것이 계약이 된다."""
        body = "\n".join(line for line in self._src().split("\n")
                         if not line.lstrip().startswith("#"))
        for token in ("roadAddr", "jibunAddr", "admCd", "rnMgtSn", "results"):
            self.assertNotIn(
                token, body,
                f"juso 응답 필드명({token})이 코드에 들어왔습니다 — 실측 전입니다.")

    def test_not_ready_carries_a_reason_that_says_what_is_missing(self) -> None:
        self.assertFalse(juso.KERNEL_READY)
        reason = juso.NOT_READY_REASON.strip()
        self.assertGreater(len(reason), 80)
        self.assertIn("실측", reason)
        self.assertIn("probe_public_data_schema", reason,
                      "해소 절차가 사유에 없습니다 — 사유는 다음 사람이 무엇을 하면 "
                      "되는지까지 말해야 합니다 (D-264).")

    def test_resolve_never_raises(self) -> None:
        """★ 이 함수가 예외를 던지면 부르는 쪽이 감싸야 하고, 언젠가 한 곳이 빠진다."""
        class _Exploding(juso.AddressPort):
            def lookup(self, *, lat, lng, timeout):
                raise RuntimeError("무엇이든")

        self.addCleanup(juso.register(_Exploding()))
        result = juso.resolve(lat=1.0, lng=1.0)     # 예외가 나가면 이 줄에서 실패한다
        self.assertEqual("failed", result.status)

    def test_the_source_is_registered_as_unmeasured(self) -> None:
        """DA-05 등록부가 이 원천을 **미실측으로** 알고 있는가 (D-280)."""
        path = _find_repo_file("docs/agent/evidence/DA-05/sources.yaml")
        if path is None:
            # ★ **판정 불가는 통과가 아니다** (D-301 「검사 못함 ≠ 0건 검사」의 시험 판).
            #   초록으로 넘기지 않고 사유를 적은 skip 을 낸다 — 사유 없는 초록은
            #   "봤는데 문제없다"로 읽히고, 여기서는 아무것도 보지 못했다.
            self.skipTest(
                "판정 불가 — DA-05 등록부에 닿지 못했습니다. 컨테이너에 docs 가 "
                "마운트되지 않은 상태입니다(docker-compose.yml 의 `./docs:/repo/docs:ro`). "
                "2026-09-01 에 그 줄을 넣었으므로, 컨테이너를 다시 세우면 이 skip 은 "
                "사라집니다. 호스트에서는 언제나 돕니다.")
        # ★ PyYAML 로 읽지 않는다 — 컨테이너에 없다(실측). 파서를 요구하면 이 시험은
        #   환경에 따라 사라지고, **사라진 시험은 사라진 것이 보이지 않는다.**
        #   보는 것이 단순하므로(항목이 있는가 · verified 가 거짓인가) 블록을 직접 읽는다.
        text = path.read_text(encoding="utf-8")
        marker = "- id: juso_coord2addr"
        self.assertIn(marker, text,
                      "FX-5 의 원천이 DA-05 등록부에 없습니다 — 실측 대상이 아닌 것으로 "
                      "읽히고, 그러면 아무도 실측하지 않습니다.")
        block = text.split(marker, 1)[1].split("\n  - id:", 1)[0]
        self.assertIn("verified: false", block,
                      "verified=true 인데 어댑터 구현이 없습니다 — 둘이 갈렸습니다.")
