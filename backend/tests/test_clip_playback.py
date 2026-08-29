# -*- coding: utf-8 -*-
"""D-306 영상 재생 **규약 넷** — 계약 11조(원본 영상 무반출)가 여기서 걸린다.

    ① 테넌트 범위 — 남의 event_id 는 404 (403 아님. 존재도 알리지 않는다 · D-269)
    ② 만료 서명 URL — 무기한 링크 금지
    ③ 구간 한정 — 요청 구간 밖 바이트가 나가지 않는다
    ④ **다운로드 아님** — 원본 전체를 주는 경로가 생기지 않았음을 부작위 시험으로 (D-300)

★ 규약을 **이름으로** 잠근다 (D-285 ② · D-291 규약)
---------------------------------------------------
넷을 주석에 적는 것과 그 이름의 시험이 실제로 도는 것은 다르다. 그래서
`test_the_four_rules_are_all_present` 가 네 이름의 실재를 판정한다 — 하나가 지워지면
그 시험이 먼저 멈춘다. 지워진 시험은 지워진 것이 보이지 않는다.

★ 그리고 잠금 — 바이트는 아직 나가지 않는다
-------------------------------------------
`CLIP_EXTRACTION_READY = False` 인 동안 전송 경로는 501 로 멈춘다. 이 시험들이 재는 것은
**"어디를 보라"를 안전하게 말하는 능력**이지 재생 자체가 아니고, 그 구별을 표에도 적는다.
"""
from __future__ import annotations

import contextlib
from datetime import timedelta
from pathlib import Path

from django.apps import apps
from django.http import Http404
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from common.tenant_scope import TenantScope
from stream_monitors.services import clips

#: 규약 넷의 시험 이름. **여기가 정본이다** — 아래 판정이 이 집합을 본다.
REQUIRED_RULES: dict[str, str] = {
    "①": "test_rule1_another_tenant_gets_404",
    "②": "test_rule2_url_expires",
    "③": "test_rule3_only_the_requested_window",
    "④": "test_rule4_no_full_download_route_exists",
}


class _ClipFixture(TestCase):
    """테넌트 A/B · A 의 스트림에 녹화 하나 · 그 시각의 이벤트 하나."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        UserGroup = apps.get_model("user", "UserGroup")
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="clip-tenant-A")
        cls.group_b = UserGroup.objects.create(name="clip-tenant-B")
        UserGroup.objects.filter(
            pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.user_a = cls._user("clip_user_a", cls.group_a)
        cls.user_b = cls._user("clip_user_b", cls.group_b)
        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)
        cls.scope_pipe = TenantScope.system(
            reason="영상 참조 시험 — 파이프라인에는 요청자가 없다 (D-281)")

        cls.stream = cls._stream("clip-cam-A", cls.group_a)
        cls.stream_norec = cls._stream("clip-cam-A-norec", cls.group_a)

        Record = apps.get_model("stream_monitors", "StreamMonitorRecord")
        cls.record = Record.objects.create(
            stream_id=cls.stream.code, code="rec-1", status="running",
            object_path="minio://records/clip-cam-A/2026-09-02.mp4")
        # created_at 은 auto_now_add 다 — 이벤트보다 앞서게 뒤로 민다.
        Record.objects.filter(pk=cls.record.pk).update(
            created_at=timezone.now() - timedelta(minutes=10))
        cls.record.refresh_from_db()

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
            name=name, code=name, ip_source="rtsp://clip.invalid/x"), group)

    def _event(self, stream=None, **kwargs):
        from kernels.k1_event import record_detection

        result = record_detection(
            scope=self.scope_pipe, stream_monitor_id=(stream or self.stream).pk,
            event_type=kwargs.pop("event_type", "fire"),
            severity=kwargs.pop("severity", "critical"),
            snapshot_path="minio://clip/1.jpg", **kwargs)
        return result.event_id


class ClipReferenceTest(_ClipFixture):
    """★ 섰는가 — **이벤트가 나면 참조도 함께 난다** (쓰기 1곳 · D-306)."""

    def test_a_reference_is_written_in_the_event_path(self) -> None:
        """★ 밖에서 채우는 배치가 아니라 **이벤트 생성 경로 안**에서 난다.

        이것이 `clip_path` 가 죽은 필드가 된 경로를 되풀이하지 않는 방법이다(D-304 착시 ⑥).
        """
        Clip = apps.get_model("stream_monitors", "EventClip")
        event_id = self._event()

        clip = Clip._base_manager.get(event_id=event_id)
        self.assertEqual("referenced", clip.clip_status)
        self.assertEqual(self.record.object_path, clip.object_key)
        self.assertEqual(clips.PRE_ROLL_SECONDS + clips.POST_ROLL_SECONDS, clip.duration)
        self.assertGreaterEqual(clip.start_offset, 0.0)

    def test_no_recording_is_unavailable_with_a_reason(self) -> None:
        """★ 녹화가 없으면 **행이 없는 것이 아니라** unavailable + 사유다 (D-290)."""
        Clip = apps.get_model("stream_monitors", "EventClip")
        event_id = self._event(stream=self.stream_norec)

        clip = Clip._base_manager.get(event_id=event_id)
        self.assertEqual("unavailable", clip.clip_status)
        self.assertTrue(clip.unavailable_reason,
                        "사유 없는 부재는 '없다' 인지 '못 찾았다' 인지 구별되지 않습니다.")
        self.assertEqual("", clip.object_key)

    def test_the_clip_inherits_the_tenant_from_the_event(self) -> None:
        """소유가 빈 행은 §0.4 의 OR 절을 타고 모두에게 보인다 — W0-13 이 되돌린 상태다."""
        Clip = apps.get_model("stream_monitors", "EventClip")
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        event_id = self._event()

        clip = Clip._base_manager.get(event_id=event_id)
        event = Event._base_manager.get(pk=event_id)
        self.assertIsNotNone(getattr(clip, "group_id", None) or
                             (clip.groups.first() if hasattr(clip, "groups") else None))
        if hasattr(clip, "group_id"):
            self.assertEqual(event.group_id, clip.group_id)

    def test_a_failure_does_not_take_the_event_down(self) -> None:
        """★ 영상 참조는 **보조**다. 여기서 죽으면 탐지 기록이 통째로 사라진다 (C-3.3)."""
        import stream_monitors.services.clips as clips_module

        original = clips_module.reference_for_event

        def _explode(event):
            raise RuntimeError("참조 실패 — 저하 변형")

        clips_module.reference_for_event = _explode
        self.addCleanup(setattr, clips_module, "reference_for_event", original)

        event_id = self._event()           # 예외가 나가면 이 줄에서 실패한다
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        self.assertTrue(Event._base_manager.filter(pk=event_id).exists())


class ClipPlaybackRulesTest(_ClipFixture):
    """★ 규약 넷 — 계약 11조가 걸리는 자리."""

    # ── 규약 ① ───────────────────────────────────────────────────────────
    def test_rule1_another_tenant_gets_404(self) -> None:
        """남의 event_id 는 **404**. 403 이면 그 id 가 존재한다는 사실이 샌다 (D-269)."""
        event_id = self._event()

        with self.assertRaises(Http404):
            clips.issue_ticket(scope=self.scope_b, event_id=event_id)

        # 양성 대조 — 우리 스코프로는 나온다. 안 나오면 위 초록은 뜻이 없다.
        self.assertIsNotNone(clips.issue_ticket(scope=self.scope_a, event_id=event_id))

    def test_rule1_system_scope_cannot_issue(self) -> None:
        """시스템 스코프로 티켓을 발급하지 않는다 — 요청자 없는 재생은 전역 조회다(D-281)."""
        event_id = self._event()
        with self.assertRaises(Http404):
            clips.issue_ticket(scope=self.scope_pipe, event_id=event_id)

    # ── 규약 ② ───────────────────────────────────────────────────────────
    def test_rule2_url_expires(self) -> None:
        """무기한 링크 금지. **만료 시각이 있고, 지나면 거절된다.**"""
        event_id = self._event()
        ticket = clips.issue_ticket(scope=self.scope_a, event_id=event_id)

        self.assertGreater(ticket.expires_at, timezone.now())
        self.assertLessEqual(ticket.expires_at,
                             timezone.now() + clips.TICKET_TTL + timedelta(seconds=5))

        # 살아 있는 티켓은 통과한다 (양성 대조)
        clips.verify_ticket(token=ticket.token, event_id=ticket.event_id,
                            object_key=ticket.object_key,
                            start_offset=ticket.start_offset, duration=ticket.duration)

        # 이미 만료된 티켓은 거절된다 — **논리 시계로** 잰다 (규약 ⑤ 계열, sleep 금지)
        expired = clips.issue_ticket(scope=self.scope_a, event_id=event_id,
                                     ttl=timedelta(seconds=-1))
        with self.assertRaises(Http404):
            clips.verify_ticket(token=expired.token, event_id=expired.event_id,
                                object_key=expired.object_key,
                                start_offset=expired.start_offset,
                                duration=expired.duration)

    # ── 규약 ③ ───────────────────────────────────────────────────────────
    def test_rule3_only_the_requested_window(self) -> None:
        """★ 구간이 **서명에 묶여 있다** — 다른 구간을 요구할 수조차 없다."""
        event_id = self._event()
        ticket = clips.issue_ticket(scope=self.scope_a, event_id=event_id)

        for label, kwargs in (
            ("시작점을 앞으로", {"start_offset": 0.0}),
            ("길이를 늘려", {"duration": ticket.duration + 3600}),
            ("다른 객체로", {"object_key": "minio://records/someone-else.mp4"}),
        ):
            payload = {
                "token": ticket.token, "event_id": ticket.event_id,
                "object_key": ticket.object_key,
                "start_offset": ticket.start_offset, "duration": ticket.duration,
            }
            payload.update(kwargs)
            with self.assertRaises(Http404, msg=f"{label} 바꿨는데 서명이 통과했습니다."):
                clips.verify_ticket(**payload)

    def test_rule3_no_bytes_leave_while_extraction_is_locked(self) -> None:
        """잠긴 동안 **어떤 바이트도 나가지 않는다.** 그리고 검증이 먼저 돈다."""
        event_id = self._event()
        ticket = clips.issue_ticket(scope=self.scope_a, event_id=event_id)

        # 위조 티켓은 잠금이 아니라 **검증**에서 걸린다 — 순서가 이렇지 않으면
        # 잠금이 풀린 날 검증이 도는지 아무도 모른다.
        with self.assertRaises(Http404):
            clips.stream_window(token="9999999999.deadbeef", event_id=ticket.event_id,
                                object_key=ticket.object_key,
                                start_offset=ticket.start_offset,
                                duration=ticket.duration)

        # 정상 티켓은 검증을 지나 **잠금에서** 멈춘다
        with self.assertRaises(NotImplementedError) as caught:
            clips.stream_window(token=ticket.token, event_id=ticket.event_id,
                                object_key=ticket.object_key,
                                start_offset=ticket.start_offset,
                                duration=ticket.duration)
        self.assertIn("F-09", str(caught.exception))

    # ── 규약 ④ — 부작위 시험 (D-300) ─────────────────────────────────────
    def test_rule4_no_full_download_route_exists(self) -> None:
        """★ **원본 전체를 주는 경로가 없다.** 만든 것이 아니라 **안 만든 것**을 잰다.

        계약 11조(원본 영상 무반출)를 어기는 가장 쉬운 길은 프리사인드 URL 한 줄이다.
        그 한 줄이 들어오면 이 시험이 멈춘다.
        """
        api_src = (Path(clips.__file__).resolve().parents[2]
                   / "apps" / "dsm" / "api.py").read_text(encoding="utf-8")
        clips_src = Path(clips.__file__).read_text(encoding="utf-8")

        for token in ("presigned", "presigned_get_object", "get_presigned_url",
                      "FileResponse", "StreamingHttpResponse", "X-Accel-Redirect"):
            self.assertNotIn(
                token, api_src,
                f"원본을 통째로 흘릴 수 있는 자리({token})가 라우트에 들어왔습니다 — "
                f"계약 11조 위반 경로입니다.")
            self.assertNotIn(token, clips_src,
                             f"구간 서비스에 {token} 이 들어왔습니다.")

        # 티켓 응답에 객체 URL 이 실리지 않는다 — 실리면 그것이 곧 다운로드 링크다.
        event_id = self._event()
        ticket = clips.issue_ticket(scope=self.scope_a, event_id=event_id)
        self.assertFalse(
            [f for f in ("http://", "https://") if f in ticket.token],
            "티켓 토큰이 URL 입니다 — 토큰은 서명이지 링크가 아닙니다.")

        # `attachment` 로 내려보내는 자리가 영상 라우트에 없다 (보고서 PDF 는 별개다)
        clip_block = api_src[api_src.index("F-09 영상 재생"):api_src.index("F-12 관리자 설정")]
        self.assertNotIn("attachment", clip_block,
                         "영상 라우트가 파일 다운로드로 내려갑니다.")

    # ── 규약이 **넷 다 있는가** ──────────────────────────────────────────
    def test_the_four_rules_are_all_present(self) -> None:
        """★ 하나라도 지워지면 여기서 멈춘다. 지워진 시험은 지워진 것이 보이지 않는다."""
        for no, name in REQUIRED_RULES.items():
            self.assertTrue(
                hasattr(type(self), name),
                f"규약 {no} 의 시험 `{name}` 이 없습니다 — 넷 중 하나라도 없으면 "
                f"이 라우트를 내지 않는다는 것이 D-306 의 판정입니다.")


class ExtractionStillLockedTest(SimpleTestCase):
    """★ 잠겨 있는가 — 그리고 그 잠금이 **값싼 선언이 아닌가**."""

    def test_extraction_is_locked(self) -> None:
        self.assertFalse(clips.CLIP_EXTRACTION_READY)
        self.assertFalse(clips.is_extraction_ready())

    def test_the_lock_carries_a_reason(self) -> None:
        reason = clips.CLIP_EXTRACTION_NOT_READY_REASON.strip()
        self.assertGreater(len(reason), 80)
        self.assertIn("F-09", reason)
        self.assertIn("11조", reason, "계약 11조와의 관계가 사유에 없습니다.")

    @staticmethod
    def _code_only(path) -> str:
        """모듈 독스트링을 뺀 소스. **"무엇을 안 만들었다"고 적은 문장이 그 자체로
        위반으로 잡히는 것**을 막는다 — 실제로 잡혔다(독스트링의 'ffmpeg 호출' 이라는
        부작위 선언이 구현으로 읽혔다). 부작위 시험은 코드를 보아야지 설명을 보면 안 된다.
        """
        import ast

        src = Path(path).read_text(encoding="utf-8")
        tree = ast.parse(src)
        doc = ast.get_docstring(tree, clean=False)
        return src.replace(f'"""{doc}"""', "", 1) if doc else src

    def test_no_extraction_implementation_exists(self) -> None:
        """부작위 (D-300) — 상수만 잠그고 구현이 몰래 들어오는 것을 막는다."""
        src = self._code_only(clips.__file__)
        self.assertNotIn("def _extract_window", src,
                         "추출 구현이 생겼습니다 — 그렇다면 상수를 올리고 무결성 시험을 "
                         "붙이십시오. 구현만 있고 잠금이 그대로인 상태가 가장 나쁩니다.")
        for token in ("ffmpeg", "subprocess"):
            self.assertNotIn(token, src, f"{token} 이 들어왔습니다 — 추출은 잠겨 있습니다.")

    def test_video_kernel_is_present_but_extraction_is_not(self) -> None:
        """두 잠금이 **다른 것을 잠근다** — 참조가 열렸다고 추출까지 열리지 않는다."""
        from tests.e2e.e2e_contract import kernel_present

        self.assertTrue(kernel_present("VIDEO"), "E2E-1 9단계가 다시 잠겼습니다.")
        self.assertFalse(clips.CLIP_EXTRACTION_READY,
                         "참조가 열렸다고 추출까지 열렸습니다 — 두 잠금이 붙었습니다.")

    def test_the_static_gate_agrees(self) -> None:
        """`scripts/verify_clip_extraction.py` 와 **같은 말을 하는가.**"""
        import subprocess
        import sys

        from tests.test_zone_judgment import _find_script

        script = _find_script("verify_clip_extraction.py")
        self.assertIsNotNone(
            script,
            "verify_clip_extraction.py 를 찾지 못했습니다. 컨테이너라면 "
            "`./scripts:/repo/scripts:ro` 마운트가 빠진 것입니다 (D-285 (4)).")
        proc = subprocess.run([sys.executable, str(script)], capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
        self.assertEqual(0, proc.returncode,
                         f"정적 게이트가 실패했습니다:\n{proc.stdout}\n{proc.stderr}")


class ExtractedRowsNeedTheFlagTest(_ClipFixture):
    """★ **데이터가 상수를 앞지르는 것**을 잡는다 — 정적 게이트가 못 보는 쪽 (D-306)."""

    def test_no_extracted_clip_without_the_flag(self) -> None:
        Clip = apps.get_model("stream_monitors", "EventClip")
        extracted = Clip._base_manager.filter(clip_status="extracted")
        if not clips.CLIP_EXTRACTION_READY:
            self.assertEqual(
                [], list(extracted.values_list("pk", flat=True)),
                "구간 추출이 잠겨 있는데 clip_status='extracted' 인 행이 있습니다 — "
                "데이터가 코드를 앞질렀습니다.")

    def test_positive_control_the_check_can_fail(self) -> None:
        """★ 위 시험이 **실패할 수 있는가.** 실패할 수 없는 시험은 시험이 아니다 (D-277)."""
        Clip = apps.get_model("stream_monitors", "EventClip")
        event_id = self._event()
        Clip._base_manager.filter(event_id=event_id).update(clip_status="extracted")
        with self.assertRaises(AssertionError):
            self.test_no_extracted_clip_without_the_flag()
