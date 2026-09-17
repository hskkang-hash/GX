# -*- coding: utf-8 -*-
"""UX-45 M3 — 현장 회신의 **종류**(`kind`) (2026-09-16 · 턴 S · 차선 U3).

무엇을 재는가 — 넷
------------------
    ① **여섯 칸이 이름으로 서 있는가**   수가 아니라 이름이다(D-285 ②). 시트의
       여섯(도착·사진·한 줄·오탐 사유·지원 요청·조치 완료)이 그대로 있어야 한다.
    ② **접두가 사람의 자리에 새지 않는가**  저장은 `[FIELD:support] …` 이고, 라우트가
       내는 것은 `kind` 와 **깨끗한 본문**이다. 접두가 화면에 보이면 판정 실패다.
    ③ **과거 회신이 안 깨지는가**   접두 없는 옛 회신은 전부 `note` 로 읽힌다 —
       새 칸이 「과거가 비어 있다」로 태어나지 않는다.
    ④ **두 벌이 갈리지 않는가**   `field.KERNEL_REPLY_CHARS` 와 커널의
       `MAX_REPLY_CHARS`. 두 벌인 것은 알고 있다(F-05 때문에 App 이 K1 을 직접
       import 할 수 없다) — 그래서 **갈리는지는 이 시험이 본다**
       (`drill.DRILL_CHANNEL` 이 같은 처방을 쓴 자리와 같다).

★ 시험은 커널을 직접 import 해도 된다 — `test_f05_event_api::_py_files` 가
  `/tests/` 를 진입면 검사에서 빼기 때문이다. 제품 코드에서는 못 한다.
"""
from __future__ import annotations

import contextlib

from django.apps import apps
from django.test import RequestFactory, TestCase

from common.tenant_scope import TenantScope


class ReplyKindUnitTest(TestCase):
    """DB 없이 서는 절 — 접두를 만들고 되읽는 자리."""

    def test_rule1_the_six_cells_are_pinned_by_name(self) -> None:
        from apps.dsm import field

        self.assertEqual(
            ["arrived", "photo", "note", "false_positive", "support", "done"],
            list(field.REPLY_KINDS),
            "M3 시트의 여섯 칸이 달라졌습니다 — 이름으로 잠근 자리입니다(D-285 ②).")

    def test_rule4_the_kernel_cap_has_not_drifted(self) -> None:
        """★ 두 벌이 갈리는 날 이 시험이 멈춘다."""
        from kernels.k1_event.field_reply import MAX_REPLY_CHARS

        from apps.dsm import field

        self.assertEqual(
            MAX_REPLY_CHARS, field.KERNEL_REPLY_CHARS,
            "회신 상한이 커널과 App 에서 갈렸습니다 — 갈리면 라우트가 통과시킨 회신을 "
            "커널이 거절하거나(422 가 사용자에게 뜻 없이 뜬다) 그 반대가 됩니다.")

    def test_rule2_every_kind_round_trips_without_leaking_the_tag(self) -> None:
        from apps.dsm import field

        for kind in field.REPLY_KINDS:
            with self.subTest(kind=kind):
                stored, clean = field.compose_reply(kind=kind, text="현장 상황 한 줄")
                self.assertTrue(stored.startswith(f"[FIELD:{kind}]"))
                self.assertEqual("현장 상황 한 줄", clean)
                read_kind, read_text = field.split_reply(stored)
                self.assertEqual(kind, read_kind)
                self.assertEqual("현장 상황 한 줄", read_text)
                self.assertNotIn("[FIELD:", read_text)

    def test_rule3_untagged_past_replies_read_as_note(self) -> None:
        from apps.dsm import field

        kind, text = field.split_reply("도착. 실화재 아님 — 조리 연기.")
        self.assertEqual("note", kind)
        self.assertEqual("도착. 실화재 아님 — 조리 연기.", text)

    def test_an_unknown_kind_is_refused_not_folded_into_note(self) -> None:
        """★ 모르는 종류를 `note` 로 접으면 오타 하나가 「지원 요청」을 삼킨다."""
        from apps.dsm import field

        with self.assertRaises(field.UnknownReplyKind):
            field.compose_reply(kind="suport", text="인력 2명")

    def test_the_two_kinds_that_need_a_body_refuse_an_empty_one(self) -> None:
        from apps.dsm import field

        for kind in ("note", "false_positive"):
            with self.subTest(kind=kind):
                with self.assertRaises(field.UnknownReplyKind):
                    field.compose_reply(kind=kind, text="   ")

    def test_the_four_press_only_kinds_fill_their_own_sentence(self) -> None:
        """★ 누름 자체가 사실인 넷은 빈 본문으로도 선다 — 커널은 빈 회신을 거절한다."""
        from apps.dsm import field

        for kind in ("arrived", "photo", "support", "done"):
            with self.subTest(kind=kind):
                stored, clean = field.compose_reply(kind=kind, text="")
                self.assertTrue(clean, "누름만으로 남는 회신의 문구가 비었습니다.")
                self.assertLessEqual(len(stored), field.KERNEL_REPLY_CHARS)

    def test_an_oversized_body_is_refused_including_the_prefix(self) -> None:
        """**잘라 저장하지 않는다** — 잘린 회신은 뜻이 뒤집힐 수 있다(커널과 같은 규약)."""
        from apps.dsm import field

        with self.assertRaises(field.UnknownReplyKind):
            field.compose_reply(kind="note", text="가" * field.KERNEL_REPLY_CHARS)


class ReplyKindRouteTest(TestCase):
    """라우트가 실제로 `kind` 를 갈라 내보내는가 — **문이 하는 일을 문에서 잰다.**"""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        UserGroup = apps.get_model("user", "UserGroup")
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group = UserGroup.objects.create(name="replykind-tenant-A")
        UserGroup.objects.filter(pk=cls.group.pk).update(created_by=None)
        cls.user = cls._user("replykind_user_a", cls.group)
        cls.stream = cls._stream("replykind-cam", cls.group)
        cls.event_id = cls._event(cls.stream)

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
            name=name, code=name, ip_source="rtsp://replykind.invalid/x"), group)

    @classmethod
    def _event(cls, stream) -> int:
        from kernels.k1_event import record_detection

        return record_detection(
            scope=TenantScope.system(reason="회신 종류 시험 — 파이프라인에 요청자 없음"),
            stream_monitor_id=stream.pk, event_type="fire", severity="critical").event_id

    def tearDown(self) -> None:
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().tearDown()

    def _request(self, path="/api/dsm/x"):
        request = RequestFactory().post(path)
        request.user = self.user
        return request

    def _post(self, **kwargs):
        from apps.dsm.api import DsmAPI

        return DsmAPI.field_reply(DsmAPI(), self._request(), self.event_id, **kwargs)

    def _list(self):
        from apps.dsm.api import DsmAPI

        request = RequestFactory().get("/api/dsm/x")
        request.user = self.user
        return DsmAPI.field_replies(DsmAPI(), request, self.event_id)

    def test_a_support_request_comes_back_as_support_with_a_clean_body(self) -> None:
        saved = self._post(kind="support", text="인력 2명이 더 필요합니다")
        self.assertEqual("support", saved["kind"])
        self.assertEqual("지원 요청", saved["kind_label"])
        self.assertEqual("인력 2명이 더 필요합니다", saved["text"])
        self.assertNotIn("[FIELD:", saved["text"])

    def test_the_default_kind_is_note_so_the_old_call_shape_still_works(self) -> None:
        """★ 앞판의 호출(`text` 만)이 그대로 산다 — 화면 배포 순서에 기대지 않는다."""
        saved = self._post(text="본 것을 한 줄로")
        self.assertEqual("note", saved["kind"])
        self.assertEqual("본 것을 한 줄로", saved["text"])

    def test_an_unknown_kind_is_422_and_nothing_is_written(self) -> None:
        from ninja.errors import HttpError

        before = self._list()["total"]
        with self.assertRaises(HttpError) as caught:
            self._post(kind="지원요청", text="한글 종류 이름")
        self.assertEqual(422, caught.exception.status_code)
        self.assertEqual(before, self._list()["total"],
                         "거절했는데 회신이 남았습니다.")

    def test_the_list_counts_by_kind_with_its_denominator(self) -> None:
        """★ `by_kind` 는 **이 페이지의 수**다 — 모수(`total`)와 함께 읽는다(D-301)."""
        self._post(kind="arrived")
        self._post(kind="support", text="헬기 지원")
        self._post(kind="done")

        listed = self._list()
        self.assertEqual(3, listed["total"])
        self.assertEqual({"arrived": 1, "support": 1, "done": 1}, listed["by_kind"])
        for row in listed["replies"]:
            self.assertNotIn("[FIELD:", row["text"])
            self.assertIn(row["kind"], listed["by_kind"])

    def test_a_reply_written_before_kinds_existed_lists_as_note(self) -> None:
        """★ 과거는 커널 경로로 그대로 만든다 — 합성이 아니다(D-289)."""
        from apps.dsm import services

        services.field_reply(scope=TenantScope.of(self.user),
                             event_id=self.event_id, text="접두 없는 옛 회신")
        rows = [r for r in self._list()["replies"] if r["text"] == "접두 없는 옛 회신"]
        self.assertEqual(1, len(rows))
        self.assertEqual("note", rows[0]["kind"])
