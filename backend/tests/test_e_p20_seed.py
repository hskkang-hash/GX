# -*- coding: utf-8 -*-
"""P-20 시드 구멍 둘을 메운 **면들의 시험** (2026-09-22 · 차선 E2).

무엇을 재는가
-------------
    ① `k2_notify.save_notification_rule` — **새로 연 쓰기 면**. P-8 이 요구하는 탐침이
       여기 있다: 남의 테넌트 규칙을 만들거나 고칠 수 있는가
    ② `k2_notify.channels.LogChannel` — 사람이 아니라 로그에 도달하는 채널이
       **사람에게 갔다고 주장하지 않는가**
    ③ `seed_dsm_events.synthetic_frame` — 합성 표식 프레임이 **실제 장면을 흉내 내지
       않는가**, 그리고 같은 인자로 두 번 그리면 같은 그림인가(두 번 올리기의 전제)

★ 가장 중요한 시험은 ①의 **음성 갈래**다. 규칙은 「누구에게 무엇이 가는가」이므로,
  남의 규칙을 고칠 수 있으면 **남의 당직자가 알림을 못 받는다** — 화면 어디에도
  안 나타나는 사고다. 그래서 여기서는 초록보다 **거절이 실제로 일어나는가**를 잰다.

★ 픽스처를 새로 짓지 않고 `K2Fixture` 를 쓴다 (D-379 — 있는 것을 다시 만들지 않는다).
  두 벌로 지으면 두 픽스처가 갈리고, 갈린 픽스처 위의 두 시험은 다른 세상을 잰다.
"""
from __future__ import annotations

from django.apps import apps
from django.test import TestCase

from tests.test_k2_notify_kernel import K2Fixture


# ═══════════════════════════════════════════════════════════════════════════
# ① save_notification_rule — 쓰기 면
# ═══════════════════════════════════════════════════════════════════════════
class SaveNotificationRuleTest(K2Fixture):
    """규칙을 만드는 자리. **검사 넷**(등급·역할·채널·소속)이 실제로 막는가."""

    def test_creates_rule_that_actually_selects_a_recipient(self) -> None:
        """★ 양성 대조 — 만든 규칙이 **실제로 사람을 고르는가** (D-282 ④).

        행이 생겼다는 것과 그 규칙이 수신자를 고른다는 것은 다른 사실이다. 행만 세면
        「규칙 N건」이 초록인 채로 M1 이 빈 화면일 수 있다.
        """
        from kernels.k2_notify import resolve_recipients, save_notification_rule

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        Rule._base_manager.all().delete()          # 픽스처 규칙을 치우고 이것만 본다

        view = save_notification_rule(
            scope=self.scope_a, severity="critical",
            role_code=self.role_a.code, channels=["log"])
        self.assertEqual("critical", view.severity)
        self.assertEqual(self.role_a.code, view.role_code)
        self.assertEqual(("log",), view.channels)

        people = resolve_recipients(scope=self.scope_a, severity="critical")
        self.assertEqual(
            [self.user_a.pk], [p.user_id for p in people],
            "규칙은 생겼는데 아무도 안 고른다 — 「규칙 N건」이 초록인 채로 M1 이 "
            "빈 화면이 되는 자리다")
        self.assertEqual(view.rule_id, people[0].rule_id,
                         "어느 규칙이 이 사람을 골랐는지 되짚을 수 없다 — 감사에서 "
                         "「왜 이 사람에게 갔나」에 답하지 못한다")

    def test_rule_is_owned_by_the_actors_tenant(self) -> None:
        """소유 없는 규칙은 §0.4 의 `created_by__isnull` 을 타고 **모두에게 보인다**."""
        from kernels.k1_event.services import _owner_field
        from kernels.k2_notify import save_notification_rule

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        view = save_notification_rule(
            scope=self.scope_a, severity="warning",
            role_code=self.role_a.code, channels=["log"])
        row = Rule._base_manager.get(pk=view.rule_id)
        if _owner_field(Rule) == "groups":
            self.assertIn(self.group_a.pk, list(row.groups.values_list("pk", flat=True)))
        else:
            self.assertEqual(self.group_a.pk, row.group_id)

    def test_rejects_what_would_become_a_rule_nobody_can_use(self) -> None:
        """등급·역할·채널·빈 채널 — **넷 다 막는가**. 하나라도 새면 그 규칙은
        화면에는 규칙으로 보이면서 발송에서 아무도 못 고른다."""
        from kernels.k2_notify import save_notification_rule
        from kernels.k2_notify.exceptions import InvalidNotifyInput

        cases = {
            "계약에 없는 등급": dict(severity="urgent", role_code=self.role_a.code,
                                     channels=["log"]),
            "없는 역할": dict(severity="critical", role_code="gx_no_such_role",
                              channels=["log"]),
            "모르는 채널": dict(severity="critical", role_code=self.role_a.code,
                                channels=["carrier-pigeon"]),
            "빈 채널": dict(severity="critical", role_code=self.role_a.code,
                            channels=[]),
        }
        for label, kwargs in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(InvalidNotifyInput, msg=f"{label} 을 통과시킨다"):
                    save_notification_rule(scope=self.scope_a, **kwargs)

    def test_unimplemented_channel_is_allowed_but_unknown_one_is_not(self) -> None:
        """★ **미구현과 모름은 다른 사실이다** (D-290).

        `sms` 는 업체 미정으로 자리만 있는 채널이다(D4-1). 그 이름의 규칙은 만들 수 있어야
        한다 — 못 만들면 업체가 정해지는 날 규칙부터 새로 세워야 한다. 반면 오타는 막는다.
        """
        from kernels.k2_notify import save_notification_rule

        view = save_notification_rule(
            scope=self.scope_a, severity="info",
            role_code=self.role_a.code, channels=["sms"])
        self.assertEqual(("sms",), view.channels)

    def test_system_scope_without_group_is_refused(self) -> None:
        """소속 없이 만들면 **소유 없는 규칙**이 된다 — 그것이 곧 전 테넌트 노출이다."""
        from common.tenant_scope import TenantScope
        from kernels.k2_notify import save_notification_rule
        from kernels.k2_notify.exceptions import InvalidNotifyInput

        scope = TenantScope.system(reason="시험 — 파이프라인에는 요청자가 없다")
        with self.assertRaises(InvalidNotifyInput):
            save_notification_rule(scope=scope, severity="critical",
                                   role_code=self.role_a.code, channels=["log"])


class SaveNotificationRuleIsolationTest(K2Fixture):
    """★ **P-8 탐침** — 남의 테넌트 규칙을 고칠 수 있는가.

    이 시험이 `tests/test_tenant_isolation.WRITE_NO_PROBE` 의
    `kernels.k2_notify.save_notification_rule` 줄을 대신한다. 그 파일은 조율자만 고치므로
    (공용 등록부), 면을 연 차선은 **같은 시나리오를 여기서 먼저 세우고** 옮길 조각을
    보고한다 — 「면이 먼저 서고 잣대가 뒤따르는」 사이를 만들지 않기 위해서다.
    """

    def _is_refusal(self, exc) -> bool:
        from django.core.exceptions import PermissionDenied
        from django.http import Http404

        return isinstance(exc, (Http404, PermissionDenied)) or \
            type(exc).__name__ in {"NoTenantGroupError", "InvalidNotifyInput"}

    def test_cannot_edit_another_tenants_rule(self) -> None:
        from kernels.k2_notify import save_notification_rule

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        before = Rule._base_manager.get(pk=self.rule_b.pk)

        with self.assertRaises(Exception) as caught:
            save_notification_rule(
                scope=self.scope_a,                 # A 가
                severity="info", role_code=self.role_a.code,
                channels=["log"], rule_id=self.rule_b.pk)   # B 의 규칙을 고친다
        self.assertTrue(
            self._is_refusal(caught.exception),
            f"거절의 모양이 아니다: {type(caught.exception).__name__}: {caught.exception} — "
            f"200 + 조용한 성공은 거절이 아니다 (D-284)")

        after = Rule._base_manager.get(pk=self.rule_b.pk)
        self.assertEqual(
            (before.severity, before.role_id, list(before.channels)),
            (after.severity, after.role_id, list(after.channels)),
            "★ 남의 규칙이 **실제로 바뀌었다.** 그 테넌트의 당직자는 이제 알림을 "
            "못 받고, 그 사실은 어느 화면에도 안 나타난다")

    def test_positive_control_owner_can_edit_own_rule(self) -> None:
        """★ 양성 대조 — 모든 것을 막으면 위 시험도 쓸모가 없다 (⑪ 거절≠도달)."""
        from kernels.k2_notify import save_notification_rule

        view = save_notification_rule(
            scope=self.scope_a, severity="info", role_code=self.role_a.code,
            channels=["log"], rule_id=self.rule_a.pk)
        self.assertEqual(self.rule_a.pk, view.rule_id)
        self.assertEqual("info", view.severity)


# ═══════════════════════════════════════════════════════════════════════════
# ② LogChannel — **사람이 아니라 로그에 도달한다**
# ═══════════════════════════════════════════════════════════════════════════
class LogChannelTest(K2Fixture):

    def test_delivery_row_says_the_channel_was_log(self) -> None:
        """★ 로그로 간 발송이 **메일로 간 것처럼 보이지 않는가.**

        이 채널이 성공을 돌려주는 것은 사실이다(로그에는 닿았다). 위험한 것은 그 사실이
        **어디에도 안 남는 경우**다. 발송 이력의 `channel` 칸이 그 자리다.
        """
        from kernels.k2_notify import save_notification_rule, send

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        Rule._base_manager.all().delete()
        save_notification_rule(scope=self.scope_a, severity="critical",
                               role_code=self.role_a.code, channels=["log"])

        #: ★ **지금 일어난 이벤트로 잰다.** `K2Fixture._event` 의 기본값은 이벤트를
        #:   10분씩 과거로 미는데(중복 억제를 피하려고), 그러면 F-10 의 두 점
        #:   (`occurred_at → sent_at`)이 언제나 30초를 넘는다 [실측 2026-09-22:
        #:   600초]. 그것은 코드의 사실이 아니라 **픽스처의 사실**이다.
        from django.utils import timezone

        event_id = self._event(self.stream_a, when=timezone.now())
        views = send(scope=self.scope_a, event_id=event_id)
        self.assertEqual(1, len(views))
        self.assertEqual("log", views[0].channel,
                         "채널 이름이 안 남으면 「사람에게 갔다」와 구별되지 않는다")
        self.assertTrue(views[0].succeeded)
        self.assertIsNotNone(views[0].sent_at)
        self.assertTrue(views[0].meets_f10,
                        "발송 기록이 F-10 의 30초를 못 넘긴다 — 로그 채널은 외부 호출이 "
                        "없으므로 이 판정이 빨간 것은 코드의 문제다")

    def test_log_channel_is_marked_as_non_human(self) -> None:
        """운영 규칙에 이 채널을 넣으면 당직자가 아무것도 못 받는다. 그 사실을
        **판정식 복제 없이** 물어볼 수 있어야 한다 (D-212)."""
        from kernels.k2_notify import channels

        self.assertIn("log", channels.NON_HUMAN)
        self.assertNotIn("email", channels.NON_HUMAN)

    def test_empty_address_is_not_a_success(self) -> None:
        """주소 없는 수신자는 로그로도 도달하지 않는다 — 여기서 참을 내면
        「받을 사람이 없음」이 「보냈음」으로 둔갑한다 (D-284)."""
        from kernels.k2_notify import channels

        outcome = channels.get("log").send(address="", subject="s", body="b")
        self.assertFalse(outcome.ok)
        self.assertTrue(outcome.reason)


# ═══════════════════════════════════════════════════════════════════════════
# ③ 합성 표식 프레임 — **실제 장면이 아니다**
# ═══════════════════════════════════════════════════════════════════════════
class SyntheticFrameTest(TestCase):
    """P-20 ② · 불변 제약: *"시드 이미지는 합성 표식 프레임, 실제 장면 흉내 금지"*."""

    @staticmethod
    def _frame(**kw):
        from stream_monitors.management.commands.seed_dsm_events import Command

        base = dict(tenant="t-시험", event_id=1234,
                    when=__import__("datetime").datetime(2026, 9, 22, 3, 4, 5), seq=7)
        base.update(kw)
        return Command.synthetic_frame(**base)

    def test_is_a_real_jpeg_of_the_declared_size(self) -> None:
        from io import BytesIO

        from PIL import Image

        from stream_monitors.management.commands.seed_dsm_events import FRAME_SIZE

        data = self._frame()
        self.assertTrue(data.startswith(b"\xff\xd8"), "JPEG 가 아니다")
        img = Image.open(BytesIO(data))
        self.assertEqual("JPEG", img.format)
        self.assertEqual(FRAME_SIZE, img.size)

    def test_same_arguments_draw_the_same_picture(self) -> None:
        """★ 두 번 올리기의 전제. 시드는 같은 객체 이름에 **덮어쓴다** — 첫 번째는
        K1 이 참조를 만들게 하고, 두 번째는 그 객체에 `event_id` 를 적는다.
        그림이 인자 말고 다른 것(시각·난수)에 따라 달라지면 그 절차가 무의미해진다."""
        self.assertEqual(self._frame(), self._frame())

    def test_stamping_the_event_id_actually_changes_the_picture(self) -> None:
        """★ 음성 갈래 — 번호를 적었는데 그림이 그대로면 **두 번째 올리기는 하는 일이
        없다.** 그러면 객체 안의 `event_id` 는 영원히 「미부여」로 남는다."""
        self.assertNotEqual(self._frame(event_id=None), self._frame(event_id=1234))

    def test_frame_is_flat_colour_not_a_photograph(self) -> None:
        """★ **사진처럼 보이지 않는가.** 검수 자리에서 시드 화면이 현장 화면으로 읽히면
        착시가 아니라 거짓말이다(D-284 · P-9).

        ★ 재는 방법을 **한 번 고쳤다** (D-350 — 실측이 도구를 고친다).
          첫 판은 「색의 가짓수 < 3000」이었고, 재어 보니 **3888** 이었다. JPEG 압축이
          글자 가장자리에 만드는 색 때문이다. 그 수는 「사진인가」와 관계가 없고,
          문턱을 3888 위로 올리는 것은 **재고 나서 답을 고치는 일**이다.

          그래서 술어를 바꿨다: **가장 흔한 색 하나가 화면의 절반을 넘는가.**
          단색 바탕은 넘고, 사진은 결코 넘지 않는다 — 압축 잡음과 무관하다.
          [실측 2026-09-22] 이 프레임의 바닥색 비율은 0.9 대다.
        """
        from collections import Counter
        from io import BytesIO

        from PIL import Image

        img = Image.open(BytesIO(self._frame())).convert("RGB")
        pixels = list(img.getdata())
        top, count = Counter(pixels).most_common(1)[0]
        share = count / len(pixels)
        self.assertGreater(
            share, 0.5,
            f"가장 흔한 색 {top} 이 화면의 {share:.1%} 밖에 안 된다 — 사진에 가깝다. "
            f"시드 이미지는 실제 장면을 흉내 내지 않는다(P-20 ②)")
