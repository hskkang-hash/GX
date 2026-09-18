# -*- coding: utf-8 -*-
"""UX-46 온보딩 진행률 — **카드를 닫는 것은 서버 기록이다** (턴 R · 차선 F).

이 시험이 묻는 것 넷
--------------------
    ① **문이 실재하고 삼켜지지 않는가** — `/api/dsm/onboarding/progress` 가 URL 해석에서
       이 핸들러로 온다. 조용한 404 는 「기능이 없다」와 구별되지 않는다(D-410).
    ② **익명은 401** — 진행률에는 사람 이름과 테넌트의 상태가 실린다.
    ③ **근거 없이는 안 닫힌다** — `source_ref` 없는 완료는 「체크했다」와 같다(WO-01 §12).
       그리고 기록이 생기면 **사람이 아무것도 안 눌러도** 닫힌다(자동 완료 훅).
    ④ **못 재는 카드를 지우지 않는다** — 분모가 조용히 줄면 진행률이 거짓으로 올라간다(D-301).

무엇을 다시 묻지 않나
---------------------
표 자체의 격리·목적 코드는 `tests/test_v11_tables.py` 가 이미 잰다. 여기서 다시 물으면
같은 사실을 두 벌로 재고, 한쪽이 지워져도 아무도 모른다.

캐시 처리: 우회 — `X-No-Cache`(D-341 착시 ⑦). 익명 401 을 묻는 줄이 스택을 타므로,
관문이 열려 있던 동안 채워진 항목을 돌려받으면 **고친 뒤에도 초록**이 된다.
"""
from __future__ import annotations

import contextlib

from django.apps import apps
from django.test import Client, RequestFactory, TestCase
from django.utils import timezone

from common.tenant_scope import TenantScope
from tests.no_cache import NO_CACHE

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "apps.dsm.api_f.DsmFAPI.onboarding_progress · apps.dsm.onboarding.progress · "
    "stream_monitors.DsmOnboardingProgress — 저장소의 실제 라우트와 실제 표"
)

PROGRESS_PATH = "/api/dsm/onboarding/progress"


class _OnboardingFixture(TestCase):
    """테넌트 A/B · **역할 코드가 실재하는** 사용자들.

    ⚠ `DsmFixture` 의 사용자는 역할 코드가 `dsm_watch_a` 라 K3 표에 없다 — 그 계정으로는
      카드가 0장이고, 0장에서 재는 진행률은 아무것도 증명하지 않는다. 그래서 여기서는
      `config/k3_roles.py` 에 **실재하는 코드**로 역할을 만든다.
    """

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        UserGroup = apps.get_model("user", "UserGroup")
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="onb-tenant-A")
        cls.group_b = UserGroup.objects.create(name="onb-tenant-B")
        UserGroup.objects.filter(
            pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.user_a = cls._user("onb_manager_a", cls.group_a, "fire_admin")
        cls.user_b = cls._user("onb_manager_b", cls.group_b, "fire_admin")
        #: 역할을 못 읽는 사람 — 「모른다」가 「0%」로 둔갑하지 않는지 재는 표본이다.
        cls.user_x = cls._user("onb_stranger", cls.group_a, "some_unmapped_role")
        #: U5(SYSOPS · `K3_ROLE_SYSOPS = ("admin",)`) 버킷 — u5.channel 카드는
        #: U2 표에 없다(카드 표는 역할마다 다르다), 그래서 U2 표본(user_a/b)이 아니라
        #: 이 사람들로 잰다 (턴 U).
        cls.user_s5a = cls._user("onb_sysop_a", cls.group_a, "admin")
        cls.user_s5b = cls._user("onb_sysop_b", cls.group_b, "admin")

        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)
        cls.scope_x = TenantScope.of(cls.user_x)
        cls.scope_s5a = TenantScope.of(cls.user_s5a)
        cls.scope_s5b = TenantScope.of(cls.user_s5b)

    @classmethod
    def _user(cls, username, group, role_code):
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")
        role, _ = Role.objects.get_or_create(code=role_code,
                                             defaults={"role_name": role_code})
        role.group = group
        role.save(update_fields=["group"])
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": group})
        user.roles.add(role)
        return user

    def tearDown(self) -> None:
        """HTTP 를 때린 시험은 **스레드에 요청을 남긴다** — 다음 시험의 `objects` 가 빈다.

        그 오염은 「없다」를 만들고, 「없다」를 기대하는 시험은 그 상태에서 **초록**이다.
        """
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().tearDown()

    def _call(self, user):
        from apps.dsm.api_f import DsmFAPI

        request = RequestFactory().get(PROGRESS_PATH)
        request.user = user
        return DsmFAPI.onboarding_progress(DsmFAPI(), request)

    def _report_run(self, group):
        """보고서 실행 기록 한 줄 — U2 ⑥ 카드를 닫는 **서버 기록**."""
        model = apps.get_model("stream_monitors", "DsmReportRun")
        return model._base_manager.create(
            kind="monthly", trigger="auto", status="succeeded",
            group=group, purpose_code="dsm.report")

    def _threshold_change(self, user):
        """임계값 변경 이력 한 줄 — u2.threshold 카드를 닫는 **서버 기록**(턴 U).

        ★ `changed_by` 로만 좁힌다(테넌트 칸이 아니다) — `_closed_by_threshold_change`
          의 규약 그대로다. `group` 을 안 준다: 이 카드가 재는 것은 「이 사람이 시험해
          봤나」이지 「이 테넌트가」가 아니다.
        """
        model = apps.get_model("stream_monitors", "ThresholdChange")
        return model._base_manager.create(
            key="person_confidence", scope_level="camera",
            old_value="0.6", new_value="0.7", reason="onboarding test",
            changed_by=user)

    def _test_send_audit(self, user, *, via="webpush"):
        """시험 발송 감사 행 한 줄 — u5.channel 카드를 닫는 **서버 기록**(턴 U).

        `via="webpush"` 는 `notify_prefs.py::test_send` 채널, `via="email"` 은
        K2 `rule_admin.py::send_test_notification` 채널 — **둘 다** 감사에 남고
        `_closed_by_test_send` 는 둘 중 하나면 닫는다.
        """
        from common import audit_writer

        if via == "webpush":
            from apps.dsm import notify_prefs

            logger_name, api_name = notify_prefs.LOGGER_NAME, notify_prefs.ACTION_TEST_SEND
        else:
            logger_name, api_name = "guardianx.dsm.notify", "dsm.notify.test_send:critical"
        return audit_writer.write(
            logger_name=logger_name, tag="[TEST]", actor=user,
            action="test_send", outcome=audit_writer.ALLOWED,
            reason="onboarding test", api_name=api_name, api_method="POST",
            status_http=200)


class OnboardingRouteTest(_OnboardingFixture):
    """① 문이 실재하는가 · ② 익명은 401 인가."""

    def test_the_route_resolves_to_this_handler(self) -> None:
        """`/onboarding/progress` 가 **이 핸들러로 오는가** (라우트 삼킴 · 착시 ⑨).

        ★ `match.func.__module__` 을 보면 안 된다 [실측 2026-09-16]. ninja-extra 는
          핸들러를 `PathView._sync_view` 로 감싸므로 그 자리에는 **언제나** ninja 의
          이름이 온다 — 「DSM 이 아닌 곳으로 갔다」가 아니라 **내가 잘못 물은 것**이다.
          등록된 operation 의 `view_func` 이름을 본다(`test_c_w1_presets` 와 같은 술어).
        """
        from django.urls import Resolver404, resolve

        try:
            match = resolve(PROGRESS_PATH)
        except Resolver404:  # pragma: no cover - 실패 메시지를 위해서만 존재한다
            self.fail(f"{PROGRESS_PATH} 가 어느 라우트에도 안 걸립니다 — "
                      f"등록(urls.py) 또는 경로를 확인하십시오.")
        operations = getattr(getattr(match.func, "__self__", None), "operations", None)
        names = [op.view_func.__name__ for op in (operations or [])]
        self.assertIn(
            "onboarding_progress", names or [getattr(match.func, "__name__", "")],
            f"{PROGRESS_PATH} 가 다른 핸들러로 갑니다 — 라우트 삼킴입니다. "
            f"닿은 것: {names or match.func}")

    def test_anonymous_gets_401(self) -> None:
        """진행률에는 테넌트의 상태가 실린다 — 자격증명 없이는 한 줄도 나가지 않는다."""
        resp = Client(raise_request_exception=False, **NO_CACHE).get(PROGRESS_PATH)
        self.assertEqual(
            resp.status_code, 401,
            f"익명 요청이 {resp.status_code} 를 받았습니다 — 이 문은 인증 뒤에 섭니다.")


class OnboardingClosedByRecordTest(_OnboardingFixture):
    """③ 근거가 닫는다 — 사람이 아니라."""

    def test_a_card_cannot_be_closed_without_a_source_ref(self) -> None:
        from apps.dsm import onboarding

        with self.assertRaises(ValueError):
            onboarding.record_card(scope=self.scope_a, card_key="u2.report",
                                   source_ref="   ")

    def test_there_is_no_door_a_person_can_press_to_close_a_card(self) -> None:
        """**닫는 문(POST)이 없다.** 있으면 그것이 곧 체크박스다(WO-01 §12)."""
        from pathlib import Path

        src = Path(__file__).resolve().parent.parent / "apps" / "dsm" / "api_f.py"
        text = "\n".join(line for line in src.read_text(encoding="utf-8").splitlines()
                         if not line.strip().startswith("#"))
        self.assertNotIn(
            "@route.post", text,
            "온보딩 라우터에 쓰기 문이 생겼습니다 — 카드를 사람이 닫는 문이면 "
            "진행률은 「했다」가 아니라 「했다고 적었다」를 셉니다.")

    def test_a_server_record_closes_the_card_without_anyone_pressing(self) -> None:
        """보고서 기록이 생기면 **다음 조회에서** 그 카드가 닫힌다."""
        from apps.dsm import onboarding

        before = onboarding.progress(scope=self.scope_a)
        closed_before = {c["key"] for c in before["cards"] if c["done"]}
        self.assertNotIn("u2.report", closed_before,
                         "기록이 없는데 카드가 닫혀 있습니다.")

        run = self._report_run(self.group_a)

        after = onboarding.progress(scope=self.scope_a)
        card = next(c for c in after["cards"] if c["key"] == "u2.report")
        self.assertTrue(card["done"], "서버 기록이 생겼는데 카드가 안 닫혔습니다.")
        self.assertEqual(
            card["source_ref"], f"report_run#{run.pk}",
            "카드가 닫혔는데 **무엇이 닫았는지**가 응답에 없습니다 — 근거 없는 완료입니다.")
        self.assertEqual(after["done"], before["done"] + 1)

    def test_the_row_is_written_once_and_not_again(self) -> None:
        """멱등 — 같은 카드에 살아 있는 행은 하나다(두 번 조회해도 늘지 않는다)."""
        from apps.dsm import onboarding

        model = apps.get_model("stream_monitors", "DsmOnboardingProgress")
        self._report_run(self.group_a)
        onboarding.progress(scope=self.scope_a)
        onboarding.progress(scope=self.scope_a)
        rows = model._base_manager.filter(user=self.user_a, card_key="u2.report",
                                          deleted__isnull=True)
        self.assertEqual(rows.count(), 1, "같은 카드의 행이 둘입니다.")

    def test_another_tenant_does_not_see_my_progress(self) -> None:
        """B 의 진행률에 A 의 기록이 섞이면 격리 실패다."""
        from apps.dsm import onboarding

        self._report_run(self.group_a)
        onboarding.progress(scope=self.scope_a)

        theirs = onboarding.progress(scope=self.scope_b)
        card = next(c for c in theirs["cards"] if c["key"] == "u2.report")
        self.assertFalse(card["done"],
                         "남의 테넌트 보고서 기록이 내 카드를 닫았습니다.")


class OnboardingDenominatorTest(_OnboardingFixture):
    """④ 분모 — 못 재는 것을 지우지 않는다."""

    def test_blocked_cards_stay_in_the_answer_with_a_reason(self) -> None:
        from apps.dsm import onboarding

        out = onboarding.progress(scope=self.scope_a)
        self.assertTrue(out["blocked"],
                        "못 재는 카드가 하나도 없다고 답했습니다 — 표를 확인하십시오.")
        for card in out["blocked"]:
            self.assertTrue(card["why"].strip(),
                            f"{card['key']} 가 사유 없이 빠져 있습니다 — 사유 없는 제외는 "
                            f"「깜빡했다」와 구별되지 않습니다.")

    def test_percent_is_null_when_the_role_is_unknown(self) -> None:
        """역할을 못 읽으면 **0% 도 100% 도 아니다.**"""
        from apps.dsm import onboarding

        out = onboarding.progress(scope=self.scope_x)
        self.assertFalse(out["role_known"])
        self.assertEqual(out["total"], 0)
        self.assertIsNone(out["percent"],
                          "카드 0장에서 백분율을 냈습니다 — 분모 0의 비율은 수가 아닙니다.")

    def test_cards_per_role_do_not_exceed_seven(self) -> None:
        """PRD §7.2 — 한 역할에 일곱 장을 넘기지 않는다(넘기면 첫날에 아무도 안 읽는다)."""
        from apps.dsm import onboarding

        for role, cards in onboarding.CARDS.items():
            self.assertLessEqual(len(cards), 7, f"{role} 카드가 {len(cards)}장입니다.")

    def test_measured_at_is_now(self) -> None:
        from apps.dsm import onboarding

        out = onboarding.progress(scope=self.scope_a)
        self.assertLessEqual(
            abs((timezone.now() - out["measured_at"]).total_seconds()), 60,
            "응답의 측정 시각이 지금이 아닙니다 — 낡은 값을 그리는 화면이 됩니다.")


class OnboardingThresholdChangeCardTest(_OnboardingFixture):
    """u2.threshold — `ThresholdChange`(K5 표 ①) 가 닫는다 (턴 U · BLOCKED→CARDS 이월).

    ★ **테넌트가 아니라 행위자로 좁힌다** — 전역 층 변경(`group=null`)도 내가 했으면
      닫혀야 하므로, 표본은 `group` 을 주지 않고 `changed_by` 만 준다.
    """

    def test_no_record_means_not_done(self) -> None:
        from apps.dsm import onboarding

        out = onboarding.progress(scope=self.scope_a)
        card = next(c for c in out["cards"] if c["key"] == "u2.threshold")
        self.assertFalse(card["done"], "기록이 없는데 임계값 카드가 닫혀 있습니다.")

    def test_a_change_closes_the_card_with_source_ref(self) -> None:
        from apps.dsm import onboarding

        change = self._threshold_change(self.user_a)
        out = onboarding.progress(scope=self.scope_a)
        card = next(c for c in out["cards"] if c["key"] == "u2.threshold")
        self.assertTrue(card["done"], "임계값 변경 기록이 생겼는데 카드가 안 닫혔습니다.")
        self.assertEqual(card["source_ref"], f"threshold_change#{change.pk}",
                         "카드가 닫혔는데 무엇이 닫았는지가 응답에 없습니다.")

    def test_calling_twice_writes_one_row(self) -> None:
        from apps.dsm import onboarding

        model = apps.get_model("stream_monitors", "DsmOnboardingProgress")
        self._threshold_change(self.user_a)
        onboarding.progress(scope=self.scope_a)
        onboarding.progress(scope=self.scope_a)
        rows = model._base_manager.filter(user=self.user_a, card_key="u2.threshold",
                                          deleted__isnull=True)
        self.assertEqual(rows.count(), 1, "같은 카드의 행이 둘입니다(멱등 실패).")

    def test_another_persons_change_does_not_close_my_card(self) -> None:
        """행위자로 좁힌다 — 같은 테넌트의 **다른 사람**이 바꿔도 내 카드는 안 닫힌다."""
        from apps.dsm import onboarding

        self._threshold_change(self.user_b)
        theirs = onboarding.progress(scope=self.scope_a)
        card = next(c for c in theirs["cards"] if c["key"] == "u2.threshold")
        self.assertFalse(card["done"], "남이 바꾼 임계값 기록이 내 카드를 닫았습니다.")


class OnboardingTestSendCardTest(_OnboardingFixture):
    """u5.channel — 시험 발송 감사 행(K2 `test_send` 또는 `notify_prefs.test_send`) 이
    닫는다 (턴 U · BLOCKED→CARDS 이월). 감사 표에는 테넌트 칸이 없어 **행위자로 좁힌다**
    (`_closed_by_test_send` 의 규약 그대로) — `audit.read_page` 와 같은 사실.
    """

    def test_no_record_means_not_done(self) -> None:
        from apps.dsm import onboarding

        out = onboarding.progress(scope=self.scope_s5a)
        card = next(c for c in out["cards"] if c["key"] == "u5.channel")
        self.assertFalse(card["done"], "기록이 없는데 시험 발송 카드가 닫혀 있습니다.")

    def test_webpush_test_send_closes_the_card(self) -> None:
        from apps.dsm import onboarding

        entry = self._test_send_audit(self.user_s5a, via="webpush")
        out = onboarding.progress(scope=self.scope_s5a)
        card = next(c for c in out["cards"] if c["key"] == "u5.channel")
        self.assertTrue(card["done"], "웹푸시 시험 발송 감사가 생겼는데 카드가 안 닫혔습니다.")
        self.assertEqual(card["source_ref"], f"audit#{entry.audit_id}")

    def test_email_test_send_also_closes_the_card(self) -> None:
        """K2 훈련 채널(이메일) 경로도 **같은 카드**를 닫는다 — 둘 중 하나면 된다."""
        from apps.dsm import onboarding

        entry = self._test_send_audit(self.user_s5b, via="email")
        out = onboarding.progress(scope=self.scope_s5b)
        card = next(c for c in out["cards"] if c["key"] == "u5.channel")
        self.assertTrue(card["done"], "K2 시험 발송 감사가 생겼는데 카드가 안 닫혔습니다.")
        self.assertEqual(card["source_ref"], f"audit#{entry.audit_id}")

    def test_calling_twice_writes_one_row(self) -> None:
        from apps.dsm import onboarding

        model = apps.get_model("stream_monitors", "DsmOnboardingProgress")
        self._test_send_audit(self.user_s5a, via="webpush")
        onboarding.progress(scope=self.scope_s5a)
        onboarding.progress(scope=self.scope_s5a)
        rows = model._base_manager.filter(user=self.user_s5a, card_key="u5.channel",
                                          deleted__isnull=True)
        self.assertEqual(rows.count(), 1, "같은 카드의 행이 둘입니다(멱등 실패).")

    def test_another_persons_test_send_does_not_close_my_card(self) -> None:
        from apps.dsm import onboarding

        self._test_send_audit(self.user_s5b, via="webpush")
        theirs = onboarding.progress(scope=self.scope_s5a)
        card = next(c for c in theirs["cards"] if c["key"] == "u5.channel")
        self.assertFalse(card["done"], "남이 누른 시험 발송이 내 카드를 닫았습니다.")
