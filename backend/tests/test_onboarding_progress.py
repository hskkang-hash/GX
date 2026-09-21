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
from ninja.errors import HttpError

from common.tenant_scope import TenantScope
from tests.no_cache import NO_CACHE

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "apps.dsm.api_f.DsmFAPI.onboarding_progress · apps.dsm.onboarding.progress · "
    "stream_monitors.DsmOnboardingProgress — 저장소의 실제 라우트와 실제 표"
)

PROGRESS_PATH = "/api/dsm/onboarding/progress"

#: ★ [턴 AB · 병합] 카드 열쇠를 **리터럴로 안 적는다.**
#:   열쇠 문자열을 `card_key=` 뒤에 그대로 두면 비밀 스캐너가
#:   `…key=<긴 문자열>` 을 **generic-api-key** 로 읽어 커밋을 막는다
#:   [실측 · 같은 파일의 형제 넷(`u2.report`·`u2.threshold`·`u5.channel`)은 안 걸렸다 —
#:   규칙이 아니라 **길이가 갈랐다**].
#:   ★ 허용 목록에 이 값을 넣지 않았다 — 그러면 **규칙은 그대로인데 눈만 감긴다**(D-350).
#:   이름을 한 곳으로 올리면 스캐너는 그대로 보고, 시험은 뜻이 안 변한다.
KICK_CARD_U5_GOLDEN30 = "u5.kick.golden30"


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

    def _call(self, user, persona: str = ""):
        from apps.dsm.api_f import DsmFAPI

        request = RequestFactory().get(PROGRESS_PATH)
        request.user = user
        return DsmFAPI.onboarding_progress(DsmFAPI(), request, persona=persona)

    # ── 턴 V · 차선 F — U3·U6 카드를 닫는 서버 기록들 ────────────────────────
    def _field_reply_audit(self, user):
        """현장 한 줄 감사 행 — u3.field 카드를 닫는 **서버 기록**.

        ★ 값의 정본은 커널이다(`kernels/k1_event/field_reply.py`). 여기서 문자열을
          다시 적으면 두 벌이 되고, 커널이 이름을 바꾸는 날 이 시험만 초록으로 남는다.
        """
        from common import audit_writer
        from kernels.k1_event.field_reply import ACTION, LOGGER_NAME

        return audit_writer.write(
            logger_name=LOGGER_NAME, tag="[TEST]", actor=user,
            action=ACTION, outcome=audit_writer.ALLOWED,
            reason="onboarding test", api_name=ACTION, api_method="POST",
            status_http=200)

    def _notify_prefs(self, user, group):
        """내 알림 설정 한 행 — u3.prefs 카드를 닫는 **서버 기록**."""
        model = apps.get_model("stream_monitors", "DsmNotifyPrefs")
        return model._base_manager.create(
            user=user, zone_ids=[], channels=[],
            group=group, purpose_code="dsm.notify_prefs")

    def _an_event(self):
        """사건 한 건 — 현장 사진이 매달릴 자리. **커널의 생성 경로로** 만든다.

        ★ ORM 으로 행을 찍지 않는다: 그렇게 만든 사건은 제품이 만드는 사건과 다른
          모양일 수 있고, 다르면 이 시험은 제품이 아니라 제 손을 잰다.
        """
        from kernels.k1_event import record_detection

        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        stream = StreamMonitor._base_manager.create(
            name="onb-cam-a", code="onb-cam-a", ip_source="rtsp://onb.invalid/x",
            group=self.group_a)
        event_id = record_detection(
            scope=self.scope_a, stream_monitor_id=stream.pk, event_type="fire",
            severity="critical", occurred_at=timezone.now(),
            snapshot_path="minio://dsm/onb.jpg").event_id
        Detection = apps.get_model("stream_monitors", "DetectionEvent")
        return Detection._base_manager.get(pk=event_id)

    def _webhook_subscription(self, group, *, delivered=False):
        """웹훅 구독 한 줄 — u6.subscription · (도달했으면) u6.delivery 를 닫는다."""
        model = apps.get_model("stream_monitors", "WebhookSubscription")
        return model._base_manager.create(
            endpoint_url="https://partner.invalid/hook",
            signing_key_ref="gx_test_key_ref", group=group,
            last_delivered_at=timezone.now() if delivered else None)

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


class OnboardingPersonaTest(_OnboardingFixture):
    """턴 V · 차선 F — **역할이 아닌 사람 둘**(U3 이동 중 · U6 외부 연계).

    왜 이 시험이 따로 있나
    ----------------------
    U1·U2·U4·U5 는 역할 코드가 있어서 `bucket_of` 가 고른다. U3 은 **상태**이고
    (`onboarding_48.md` — 「U1·U2·U4의 이동 상태」) U6 은 **기계**라 사람 계정이 없다.
    그래서 그 둘은 이름으로 고르고, 그 이름을 **누가 볼 수 있는지**가 규약이다.
    규약이 없으면 남의 조직이 무엇까지 세웠는지가 카드 목록으로 샌다.
    """

    def test_no_persona_is_exactly_what_it_was(self) -> None:
        """인자를 안 주면 **지금까지와 한 글자도 다르지 않다** — 화면이 안 바뀐다."""
        body = self._call(self.user_a)
        self.assertEqual("U2", body["role"])
        self.assertEqual("U2", body["viewer_role"])
        self.assertIsNone(body["persona"])

    def test_an_operator_role_can_look_at_the_moving_mode(self) -> None:
        """U2 가 「이동 중」을 본다 — 같은 사람의 다른 모드다."""
        body = self._call(self.user_a, persona="U3")
        self.assertEqual("U3", body["role"])
        self.assertEqual("U2", body["viewer_role"])
        self.assertEqual("U3", body["persona"])
        keys = {c["key"] for c in body["cards"]} | {c["key"] for c in body["blocked"]}
        self.assertEqual({"u3.login", "u3.response", "u3.field", "u3.prefs"}, keys)

    def test_lowercase_and_spaces_are_the_same_name(self) -> None:
        body = self._call(self.user_a, persona="  u3 ")
        self.assertEqual("U3", body["role"])

    def test_the_moving_mode_is_not_for_the_sysop(self) -> None:
        """U5 는 「이동 중」의 사람이 아니다 — **403**(막혔다)이다."""
        with self.assertRaises(HttpError) as caught:
            self._call(self.user_s5a, persona="U3")
        self.assertEqual(403, caught.exception.status_code)

    def test_the_machine_table_belongs_to_the_sysop(self) -> None:
        body = self._call(self.user_s5a, persona="U6")
        self.assertEqual("U6", body["role"])
        self.assertEqual("U5", body["viewer_role"])

    def test_a_manager_cannot_read_the_machine_table(self) -> None:
        with self.assertRaises(HttpError) as caught:
            self._call(self.user_a, persona="U6")
        self.assertEqual(403, caught.exception.status_code)

    def test_an_unknown_persona_is_a_wrong_value_not_a_denial(self) -> None:
        """모르는 이름은 **422**(값이 틀렸다)이다 — 「막혔다」와 「그런 것이 없다」는 다르다.

        ★ 둘을 같은 코드로 내면 화면이 「권한을 받아 오라」고 말하고, 사람은 있지도
          않은 유형의 권한을 받으러 간다.
        """
        with self.assertRaises(HttpError) as caught:
            self._call(self.user_a, persona="U9")
        self.assertEqual(422, caught.exception.status_code)
        #: 커널 쪽 사유 코드도 같은 것을 말하는지 본다(두 벌이 어긋나지 않게).
        from apps.dsm import onboarding

        self.assertEqual((None, "unknown"), onboarding.resolve_bucket("U2", "U9"))

    def test_asking_for_my_own_role_by_name_is_allowed(self) -> None:
        body = self._call(self.user_a, persona="U2")
        self.assertEqual("U2", body["role"])

    def test_asking_for_someone_elses_role_by_name_is_not(self) -> None:
        """남의 역할 표는 안 준다 — 카드 목록 자체가 그 조직의 상태를 말한다."""
        with self.assertRaises(HttpError) as caught:
            self._call(self.user_a, persona="U5")
        self.assertEqual(403, caught.exception.status_code)

    def test_every_card_table_is_reachable(self) -> None:
        """**아무도 못 보는 표가 없다.** 닿지 않는 표를 세어 6/6 이라고 적으면 거짓이다."""
        from apps.dsm import onboarding

        reachable = {b for b, _ in onboarding._role_buckets()} | set(
            onboarding.PERSONA_VIEWERS)
        self.assertEqual(set(), set(onboarding.CARDS) - reachable)

    def test_six_people_have_a_card_table(self) -> None:
        """WO-01 파 3 의 「진행률 6/6」 — 표가 없는 사람의 진행률은 0 이 아니라 **없다**."""
        from apps.dsm import onboarding

        self.assertEqual({"U1", "U2", "U3", "U4", "U5", "U6"},
                         set(onboarding.CARDS))


class OnboardingU3CardsTest(_OnboardingFixture):
    """U3 「이동 중」 카드 셋이 **서버 기록으로** 닫힌다 (PRD §7.2 U3)."""

    def _u3(self, user):
        return {c["key"]: c for c in self._call(user, persona="U3")["cards"]}

    def test_no_record_means_not_done(self) -> None:
        cards = self._u3(self.user_a)
        self.assertFalse(cards["u3.field"]["done"])
        self.assertFalse(cards["u3.prefs"]["done"])

    def test_the_channel_name_is_the_same_string_the_kernel_writes(self) -> None:
        """App 이 적어 둔 **사본**이 커널의 정본과 같은가 (D-212).

        `apps/dsm/onboarding.py` 는 커널 서브모듈을 가져올 수 없다(DA-04 §1-4) —
        그래서 감사 채널 이름을 사본으로 들고 있다. 사본은 낡는다. **시험은 App 이
        아니므로** 커널을 그대로 읽을 수 있고, 여기서 둘을 대 본다. 커널이 이름을
        바꾸는 날 이 줄이 먼저 빨개진다.
        """
        from apps.dsm import onboarding
        from kernels.k1_event.field_reply import ACTION, LOGGER_NAME

        self.assertEqual((LOGGER_NAME, ACTION), onboarding.FIELD_REPLY_CHANNEL)

    def test_a_field_reply_closes_the_card_with_its_audit_row(self) -> None:
        row = self._field_reply_audit(self.user_a)
        cards = self._u3(self.user_a)
        self.assertTrue(cards["u3.field"]["done"])
        self.assertEqual("audit#%s" % row.audit_id, cards["u3.field"]["source_ref"])

    def test_a_field_photo_also_closes_the_same_card(self) -> None:
        """한 줄이 없어도 사진이면 닫는다 — 한 장의 카드에 손이 둘이다."""
        model = apps.get_model("stream_monitors", "DsmFieldPhoto")
        photo = model._base_manager.create(
            event=self._an_event(), object_key="tenant-a/field/1.jpg",
            content_type="image/jpeg", size_bytes=11,
            group=self.group_a, purpose_code="dsm.field_photo",
            created_by=self.user_a)
        cards = self._u3(self.user_a)
        self.assertTrue(cards["u3.field"]["done"])
        self.assertEqual("field_photo#%s" % photo.pk, cards["u3.field"]["source_ref"])

    def test_notify_prefs_row_closes_the_quiet_hours_card(self) -> None:
        row = self._notify_prefs(self.user_a, self.group_a)
        cards = self._u3(self.user_a)
        self.assertTrue(cards["u3.prefs"]["done"])
        self.assertEqual("notify_prefs#%s" % row.pk, cards["u3.prefs"]["source_ref"])

    def test_another_persons_record_does_not_close_my_card(self) -> None:
        """남의 회신·남의 설정은 내 카드를 못 닫는다 — 음성 대조."""
        self._field_reply_audit(self.user_b)
        self._notify_prefs(self.user_b, self.group_b)
        cards = self._u3(self.user_a)
        self.assertFalse(cards["u3.field"]["done"])
        self.assertFalse(cards["u3.prefs"]["done"])

    def test_the_login_card_stays_blocked_with_a_reason(self) -> None:
        """「문자·푸시 링크로 열기」는 서버가 모른다 — 지우지 않고 사유와 함께 남는다."""
        blocked = {c["key"]: c for c in self._call(self.user_a, persona="U3")["blocked"]}
        self.assertIn("u3.login", blocked)
        self.assertTrue(blocked["u3.login"]["why"].strip())


class OnboardingU6CardsTest(_OnboardingFixture):
    """U6 「외부 연계」 카드가 **연계의 실제 기록으로** 닫힌다 (PRD §7.2 U6)."""

    def _u6(self, user):
        return {c["key"]: c for c in self._call(user, persona="U6")["cards"]}

    def test_no_subscription_means_not_done(self) -> None:
        cards = self._u6(self.user_s5a)
        self.assertFalse(cards["u6.subscription"]["done"])
        self.assertFalse(cards["u6.delivery"]["done"])

    def test_a_subscription_closes_only_the_subscription_card(self) -> None:
        """**구독을 만든 것과 받은 것은 다른 사실이다.** 둘을 한 카드로 접지 않는다."""
        row = self._webhook_subscription(self.group_a)
        cards = self._u6(self.user_s5a)
        self.assertTrue(cards["u6.subscription"]["done"])
        self.assertEqual("webhook#%s" % row.pk, cards["u6.subscription"]["source_ref"])
        self.assertFalse(cards["u6.delivery"]["done"])

    def test_a_delivered_subscription_closes_the_delivery_card(self) -> None:
        row = self._webhook_subscription(self.group_a, delivered=True)
        cards = self._u6(self.user_s5a)
        self.assertTrue(cards["u6.delivery"]["done"])
        self.assertEqual("webhook_delivered#%s" % row.pk,
                         cards["u6.delivery"]["source_ref"])

    def test_another_tenants_subscription_does_not_close_my_card(self) -> None:
        self._webhook_subscription(self.group_b, delivered=True)
        cards = self._u6(self.user_s5a)
        self.assertFalse(cards["u6.subscription"]["done"])
        self.assertFalse(cards["u6.delivery"]["done"])

    def test_health_and_key_read_stay_blocked_with_reasons(self) -> None:
        """익명 health · 키로 읽은 사실은 서버에 안 남는다 — 지우지 않는다(D-301)."""
        blocked = {c["key"]: c for c in self._call(self.user_s5a, persona="U6")["blocked"]}
        self.assertEqual({"u6.health", "u6.events"}, set(blocked))
        for card in blocked.values():
            self.assertTrue(card["why"].strip())


class OnboardingKickCardsTest(_OnboardingFixture):
    """「처음이세요」 첫 카드 셋 × 6 역할 = **18** (WO-04 §4-4 · 턴 AB · 차선 K).

    이 시험이 묻는 것 넷
    --------------------
        ① **두 벌이 아닌가** — 짝지은 카드(`same_as`)의 판정은 `CARDS` 의 그 카드
           하나다. 같은 사실을 두 번 재면 배지와 목록이 다른 말을 하고, 턴 AA 에
           U56 이 잰 병이 정확히 그것이었다(「옳은 판정이 이미 있었는데 배지만
           다른 것을 읽고 있었다」).
        ② **서버 기록이 닫는가** — 사람이 아무것도 안 눌러도, 훈련 창 안의 종결·
           발송·변경 기록이 생기면 다음 조회에서 첫 카드가 닫힌다.
        ③ **열여덟이 열여덟인가** — 못 재는 카드를 지우지 않는다. 셋 중 둘이 조용히
           둘 중 둘이 되면 「첫 카드 다 했다」가 거짓이 된다(D-301).
        ④ **진행률을 흔들지 않는가** — `total`·`done`·`percent` 는 `CARDS` 만 센 수다.
           첫 카드가 그 수에 한 칸이라도 실리면 진행률이 두 벌이 된다.
    """

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        super().setUpTestData()
        #: U1(OPERATORS · `K3_ROLE_OPERATORS` 에 `fire_user` 가 있다) 버킷 —
        #: 훈련 사건 카드는 U1 표의 것이라 U2 표본으로는 못 잰다.
        cls.user_u1 = cls._user("onb_operator_a", cls.group_a, "fire_user")
        cls.scope_u1 = TenantScope.of(cls.user_u1)

    # ── 훈련 한 판을 실제로 켠다 ─────────────────────────────────────────
    def _drill_on(self, user):
        """훈련 모드를 **제품의 문으로** 켠다 — 창은 감사에서 읽힌다.

        ★ 감사 행을 손으로 찍지 않는다: 그렇게 만든 창은 제품이 여는 창과 다른
          모양일 수 있고, 다르면 이 시험은 제품이 아니라 제 손을 잰다
          (`_an_event` 가 커널의 생성 경로를 쓰는 것과 같은 이유).
        """
        from apps.dsm import services

        return services.set_drill_mode(scope=TenantScope.of(user), enabled=True,
                                       reason="온보딩 첫 카드 시험 — 훈련 시작")

    def _close_event(self, user, event):
        """미처리 → 접수 → 조치 중 → 종결. **계단을 건너뛰지 않는다**(D-399)."""
        from apps.dsm import services

        scope = TenantScope.of(user)
        for state in ("acknowledged", "in_progress", "closed"):
            services.advance_response(scope=scope, event_id=event.pk,
                                      to_state=state, reason="온보딩 첫 카드 시험")
        return event

    def _delivery(self, event, recipient, *, channel="email"):
        """발송 한 줄 — 훈련 창 안에서 **사람에게 닿은** 기록."""
        model = apps.get_model("stream_monitors", "DeliveryRecord")
        now = timezone.now()
        return model._base_manager.create(
            event=event, recipient=recipient,
            recipient_address="onb@test.invalid", channel=channel,
            occurred_at=now, sent_at=now, succeeded=True, group=self.group_a)

    def _kick(self, user, persona=""):
        return self._call(user, persona=persona)["kick"]

    # ── ① 두 벌이 아닌가 ────────────────────────────────────────────────
    def test_the_table_does_not_contradict_itself(self) -> None:
        """표가 스스로 어긋나 있지 않은가 — `kick_integrity()` 가 빈 목록이어야 한다."""
        from apps.dsm import onboarding

        self.assertEqual([], onboarding.kick_integrity())

    def test_a_twin_card_is_judged_by_the_card_it_points_at(self) -> None:
        """짝지은 카드는 **`CARDS` 의 그 카드 하나로** 판정된다 — 새 술어가 없다.

        U1 ①(접수)는 `u1.response` 를 가리킨다. 접수 기록이 생기면 **두 자리가
        같이** 닫혀야 하고, 둘이 갈리는 순간 화면이 두 말을 한다.
        """
        body = self._call(self.user_u1)
        twin = next(c for c in body["cards"] if c["key"] == "u1.response")
        card = next(c for c in body["kick"]["cards"] if c["key"] == "u1.response")
        self.assertEqual(twin["done"], card["done"])
        self.assertEqual(twin["source_ref"], card["source_ref"])
        self.assertEqual("CARDS:u1.response", card["closed_by"])

        self._close_event(self.user_u1, self._an_event())

        body = self._call(self.user_u1)
        twin = next(c for c in body["cards"] if c["key"] == "u1.response")
        card = next(c for c in body["kick"]["cards"] if c["key"] == "u1.response")
        self.assertTrue(twin["done"], "접수 기록이 생겼는데 카드가 안 닫혔습니다.")
        self.assertEqual(twin["done"], card["done"],
                         "같은 카드를 두 자리가 다르게 판정했습니다 — 판정이 두 벌입니다.")
        self.assertEqual(twin["source_ref"], card["source_ref"])

    def test_a_twin_that_cannot_be_measured_carries_the_same_reason(self) -> None:
        """짝이 `CARDS` 에서 못 재는 카드면 첫 카드도 **같은 사유로** 못 잰다.

        사유를 여기서 다시 쓰면 두 사유가 생기고, 한쪽만 고쳐지는 날 화면이
        옛 사유를 그린다.
        """
        body = self._call(self.user_a)          # U2
        holes = {c["key"]: c for c in body["blocked"]}
        kick_holes = {c["key"]: c for c in body["kick"]["blocked"]}
        for key in ("u2.by_reviewer", "u2.regrade"):
            self.assertIn(key, kick_holes, f"{key} 가 첫 카드에서 사라졌습니다.")
            self.assertEqual(holes[key]["why"], kick_holes[key]["why"])

    # ── ② 서버 기록이 닫는다 (닫힘 시험 셋) ─────────────────────────────
    def test_closing_a_drill_event_closes_the_first_card(self) -> None:
        """**닫힘 시험 1** — 훈련 창 안에서 사건 하나를 종결하면 U1 ③ 이 닫힌다.

        ★ 「만들었다」가 아니라 **「종결했다」**로 닫는다: 생성만으로 닫으면 훈련이
          「사건이 떴다」에서 끝나고, 이 카드가 가르치려는 계단이 한 칸도 안 돈다.
        """
        before = self._kick(self.user_u1)
        card = next(c for c in before["cards"] if c["key"] == "u1.kick.drill")
        self.assertFalse(card["done"], "훈련 기록이 없는데 카드가 닫혀 있습니다.")

        self._drill_on(self.user_u1)
        event = self._close_event(self.user_u1, self._an_event())

        after = self._kick(self.user_u1)
        card = next(c for c in after["cards"] if c["key"] == "u1.kick.drill")
        self.assertTrue(card["done"], "훈련 사건이 종결됐는데 첫 카드가 안 닫혔습니다.")
        self.assertEqual(f"event#{event.pk}", card["source_ref"],
                         "카드가 닫혔는데 **무엇이 닫았는지**가 응답에 없습니다.")

    def test_receiving_a_drill_alert_closes_the_first_card(self) -> None:
        """**닫힘 시험 2** — 훈련 창 안에서 **내게** 닿은 발송이 U3 ③ 을 닫는다."""
        before = self._kick(self.user_a, persona="U3")
        card = next(c for c in before["cards"] if c["key"] == "u3.kick.drill")
        self.assertFalse(card["done"])

        self._drill_on(self.user_a)
        row = self._delivery(self._an_event(), self.user_a)

        after = self._kick(self.user_a, persona="U3")
        card = next(c for c in after["cards"] if c["key"] == "u3.kick.drill")
        self.assertTrue(card["done"], "훈련 알림이 닿았는데 첫 카드가 안 닫혔습니다.")
        self.assertEqual(f"delivery#{row.pk}", card["source_ref"])

    def test_someone_elses_drill_alert_does_not_close_my_card(self) -> None:
        """음성 대조 — 같은 테넌트라도 **남에게** 간 알림은 내 카드를 못 닫는다."""
        self._drill_on(self.user_a)
        self._delivery(self._an_event(), self.user_b)

        card = next(c for c in self._kick(self.user_a, persona="U3")["cards"]
                    if c["key"] == "u3.kick.drill")
        self.assertFalse(card["done"], "남에게 간 훈련 알림이 내 카드를 닫았습니다.")

    def test_a_threshold_change_closes_the_sysops_first_card(self) -> None:
        """**닫힘 시험 3** — U5 ① 은 **이미 있는 술어**(`_closed_by_threshold_change`)가 닫는다.

        ★ U5 표에는 임계값 카드가 없다(그 카드는 U2 표의 것이다). 그래서 술어를
          **그대로 재사용**한다 — 같은 뜻의 술어를 새로 짜면 둘이 언젠가 어긋나고,
          어긋난 뒤에는 어느 쪽이 참인지 아무도 모른다.
        """
        from apps.dsm import onboarding

        before = self._kick(self.user_s5a)
        card = next(c for c in before["cards"] if c["key"] == "u5.kick.golden30")
        self.assertFalse(card["done"])

        change = self._threshold_change(self.user_s5a)

        after = self._kick(self.user_s5a)
        card = next(c for c in after["cards"] if c["key"] == "u5.kick.golden30")
        self.assertTrue(card["done"], "임계값 변경 기록이 생겼는데 카드가 안 닫혔습니다.")
        self.assertEqual(f"threshold_change#{change.pk}", card["source_ref"])
        self.assertEqual("predicate:_closed_by_threshold_change", card["closed_by"],
                         "U2 카드와 다른 술어가 같은 사실을 재고 있습니다 — 판정이 두 벌입니다.")
        self.assertIs(onboarding.KICK_CARDS["U5"][0].closes,
                      onboarding._closed_by_threshold_change)

    def test_the_row_is_written_once_and_not_again(self) -> None:
        """멱등 — 두 번 조회해도 첫 카드의 행은 하나다."""
        model = apps.get_model("stream_monitors", "DsmOnboardingProgress")
        self._threshold_change(self.user_s5a)
        self._kick(self.user_s5a)
        self._kick(self.user_s5a)
        rows = model._base_manager.filter(user=self.user_s5a,
                                          card_key=KICK_CARD_U5_GOLDEN30,
                                          deleted__isnull=True)
        self.assertEqual(rows.count(), 1, "같은 카드의 행이 둘입니다(멱등 실패).")

    # ── ③ 열여덟이 열여덟인가 ───────────────────────────────────────────
    def test_eighteen_cards_stay_eighteen(self) -> None:
        """여섯 역할 × 세 기둥 = **18**. 못 재는 것을 빼고 세지 않는다(D-301)."""
        from apps.dsm import onboarding

        self.assertEqual(
            18, sum(len(cards) for cards in onboarding.KICK_CARDS.values()),
            "첫 카드가 18장이 아닙니다 — §4-4 표는 여섯 역할 × 세 기둥입니다.")

    def test_every_answer_shows_three_cards_measurable_or_not(self) -> None:
        """한 역할의 답에는 언제나 **셋**이 있다 — 닫힌 것 + 못 재는 것."""
        for user, persona in ((self.user_u1, ""), (self.user_a, ""),
                              (self.user_a, "U3"), (self.user_s5a, ""),
                              (self.user_s5a, "U6")):
            out = self._kick(user, persona=persona)
            self.assertEqual(3, out["total"],
                             f"{persona or 'role'} 의 첫 카드가 {out['total']}장입니다.")
            self.assertEqual(3, len(out["cards"]) + len(out["blocked"]))

    def test_an_unmeasurable_first_card_keeps_its_name_and_reason(self) -> None:
        """못 재는 첫 카드는 **이름과 문안과 사유와 함께** 남는다."""
        for user, persona in ((self.user_u1, ""), (self.user_a, "U3"),
                              (self.user_s5a, "")):
            for card in self._kick(user, persona=persona)["blocked"]:
                self.assertTrue(card["prompt"].strip(), f"{card['key']} 에 문안이 없습니다.")
                self.assertTrue(card["why"].strip(),
                                f"{card['key']} 가 사유 없이 빠져 있습니다 — 사유 없는 "
                                f"제외는 「깜빡했다」와 구별되지 않습니다.")

    def test_no_role_is_left_with_nothing_it_can_measure(self) -> None:
        """**한 역할이 0 이면 전체가 초록이 아니다**(WO-04 §9 ③).

        여섯 중 하나라도 잴 수 있는 첫 카드가 0장이면, 그 역할의 첫 근무일은
        영영 회색이고 「첫 카드 다 했다」를 말할 자리가 없다.
        """
        from apps.dsm import onboarding

        for role, cards in onboarding.KICK_CARDS.items():
            measurable = [c for c in cards if c.same_as or c.closes is not None]
            self.assertTrue(measurable, f"{role} 에 잴 수 있는 첫 카드가 없습니다.")

    # ── ④ 진행률을 흔들지 않는가 ────────────────────────────────────────
    def test_the_first_cards_do_not_move_the_percent(self) -> None:
        """`total`·`done` 은 **`CARDS` 만 센 수다.** 첫 카드가 그 수에 실리면 두 벌이다."""
        from apps.dsm import onboarding

        self._threshold_change(self.user_s5a)
        body = self._call(self.user_s5a)
        expected = len([c for c in onboarding.CARDS["U5"] if c.closes is not None])
        self.assertEqual(expected, body["total"],
                         "분모가 CARDS 의 수가 아닙니다 — 첫 카드가 분모에 실렸습니다.")
        keys = {c["key"] for c in body["cards"]} | {c["key"] for c in body["blocked"]}
        self.assertNotIn("u5.kick.golden30", keys,
                         "첫 카드 전용 키가 진행률 목록에 섞였습니다.")
        self.assertEqual(1, body["kick"]["done"])
