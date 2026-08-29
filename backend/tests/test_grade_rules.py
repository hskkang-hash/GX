# -*- coding: utf-8 -*-
"""표 ③ 등급규칙 — F-12 「등급규칙」 · **F-04 「JSON 무재기동 반영」** (D-368).

이 파일의 중심 갈래는 하나다
----------------------------
    **바꾼 규칙이 재기동 없이 먹는가.**

그것이 계약 F-04 의 AC 문장이고, 코드에서 그 성질이 나오는 자리는 딱 한 줄이다 —
판정이 사전을 직접 읽지 않고 **매번 DB 를 보는가**. 사전은 import 시점에 한 번 읽히고,
그것만 있으면 규칙을 바꾸려면 재기동해야 한다. **재기동은 재난 상황 중에 하면 안 되는
일**이고, 규칙을 고치는 시점은 대개 경보가 쏟아지는 그 순간이다.

★ 그리고 이 표에서 가장 위험한 동작을 따로 잰다 — **하향**
----------------------------------------------------------
`fire → info` 로 내리면 화재가 **조용해진다.** 경보가 안 오는 것은 사고가 아니라
「아무 일도 없음」으로 보이고, 그래서 아무도 신고하지 않는다. 막지는 않되
**조용히 지나가지도 않게** 한다: 사유 · 이력 · `lowered` 표식 셋을 요구한다.

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105 · D-224)
    skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import contextlib

from django.apps import apps
from django.test import TestCase

from common.tenant_scope import TenantScope
from kernels.k5_trust import grade_rules


class GradeRuleFixture(TestCase):
    """테넌트 A/B · 각각 관리자. `DsmFixture` 규약을 따른다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        UserGroup = apps.get_model("user", "UserGroup")

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="grade-tenant-A")
        cls.group_b = UserGroup.objects.create(name="grade-tenant-B")
        UserGroup.objects.filter(
            pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.user_a = cls._user("grade_user_a", cls.group_a, admin=True)
        cls.user_b = cls._user("grade_user_b", cls.group_b, admin=True)
        cls.plain_a = cls._user("grade_plain_a", cls.group_a, admin=False)

        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)
        cls.plain_scope = TenantScope.of(cls.plain_a)

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
    def _user(cls, username, group, *, admin: bool):
        from common.tenant_roles import tenant_admin_role_code

        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": group})
        code = tenant_admin_role_code(group.pk) if admin else f"watch_{username}"
        user.roles.add(cls._own(Role.objects.create(role_name=code, code=code), group))
        user.refresh_from_db()
        return user


class NoRestartTest(GradeRuleFixture):
    """★ **계약 F-04 「JSON 무재기동 반영」** — 이 파일의 중심."""

    def test_f04_no_restart_contract_ac(self) -> None:
        """★ 계약 AC — 바꾼 규칙이 **같은 프로세스 안에서** 즉시 먹는다.

        재기동하지 않았다는 것을 어떻게 재나: 시험 자체가 한 프로세스다.
        `set_grade_rule` 을 부른 **직후** `resolve_severity` 가 새 값을 내면,
        그 사이에 재기동이 없었다는 뜻이다.
        """
        before = grade_rules._resolve_severity("intrusion", group=self.group_a)
        self.assertEqual(before, "warning", "잠정 기본값이 바뀌었습니다 — "
                                            "이 시험의 출발점을 다시 잡으십시오.")

        grade_rules.set_grade_rule(
            scope=self.scope_a, event_type="intrusion", severity="critical",
            reason="야간 무단침입이 늘어 현장 요청으로 상향")

        after = grade_rules._resolve_severity("intrusion", group=self.group_a)
        self.assertEqual(
            after, "critical",
            "규칙을 바꿨는데 판정이 옛 값입니다 — 재기동이 필요한 상태이고, "
            "그것은 계약 F-04 「무재기동 반영」의 위반입니다.")

    def test_the_judgment_does_not_read_the_dict_directly(self) -> None:
        """★ **부작위** (D-300) — 배선이 사전을 직접 읽지 않는다.

        위 시험은 커널만 잰다. 실제 이벤트가 나는 경로(`detection_event_bridge`)가
        사전을 직접 읽고 있으면 **커널만 무재기동이고 제품은 아니다.**
        그 어긋남은 시험 하나로는 안 보이므로 소스를 본다.
        """
        import inspect

        from stream_monitors.services import detection_event_bridge as bridge

        src = inspect.getsource(bridge.publish_detections) \
            if hasattr(bridge, "publish_detections") else inspect.getsource(bridge)
        self.assertNotIn(
            "EVENT_TYPE_TO_SEVERITY[", src,
            "배선이 사전을 직접 읽습니다 — 사전은 import 시점에 한 번 읽히므로 "
            "규칙 변경이 재기동을 요구하게 됩니다 (계약 F-04 위반).")
        self.assertIn(
            "severity_for", src,
            "배선이 커널의 **공개** 판정 면을 부르지 않습니다 — 두 곳이 다른 등급을 "
            "낼 수 있습니다.")

    def test_the_dictionary_is_still_the_definition(self) -> None:
        """★ 사전을 **지우지 않았다.** 표는 덮어쓴 값이고 사전은 정의다.

        정의를 DB 로 옮기면 운영이 정의를 지울 수 있고, **지워진 정의는 코드가
        부를 때 터진다** — 표 ①이 같은 이유로 정의를 코드에 둔다(D-325).
        """
        from stream_monitors.services.detection_event_bridge import (
            EVENT_TYPE_TO_SEVERITY)

        self.assertTrue(EVENT_TYPE_TO_SEVERITY, "잠정 사전이 비었습니다.")
        rows = grade_rules.list_grade_rules(scope=self.scope_a)
        self.assertEqual(
            {r.event_type for r in rows}, set(EVENT_TYPE_TO_SEVERITY),
            "설정 화면이 정의 전건을 내지 않습니다 — 덮어쓴 것만 내면 화면은 "
            "'규칙 2개' 를 그리고 나머지가 규칙 없이 도는 것처럼 읽힙니다.")

    def test_no_row_is_the_normal_state(self) -> None:
        """★ **행이 없는 것이 정상이다.** 기본값을 복사해 넣지 않았다.

        복사해 두면 코드의 기본값이 바뀌는 날 **복사본만 옛말**이 되고,
        옛말이 된 행은 옛말인 것이 안 보인다 (D-290).
        """
        Rule = apps.get_model("stream_monitors", "GradeRule")
        self.assertEqual(
            0, Rule._base_manager.count(),
            "아무도 안 바꿨는데 등급규칙 행이 있습니다 — 기본값이 복사돼 있습니다.")
        self.assertEqual("critical",
                         grade_rules._resolve_severity("fire", group=self.group_a))


class LoweringIsLoudTest(GradeRuleFixture):
    """★ 등급 **하향**은 이 표에서 가장 위험한 동작이다 — 조용히 지나가지 않게."""

    def test_lowering_is_reported_as_lowered(self) -> None:
        """`fire → info` 는 화재를 **조용하게 만드는** 변경이다. 그 사실이 값으로 나온다."""
        view = grade_rules.set_grade_rule(
            scope=self.scope_a, event_type="fire", severity="info",
            reason="시험 환경 — 실제 운영에서 이러면 화재 경보가 사라진다")
        self.assertTrue(
            view.lowered,
            "★ 하향인데 lowered 가 거짓입니다 — 경보를 끈 변경이 화면에서 "
            "다른 변경과 같아 보입니다.")
        self.assertEqual(view.default_severity, "critical",
                         "무엇에서 낮췄는지가 안 나옵니다.")

    def test_raising_is_not_reported_as_lowered(self) -> None:
        """★ **음성 대조** — 전부 `lowered=True` 면 그 표식은 아무것도 안 알린다(D-289)."""
        view = grade_rules.set_grade_rule(
            scope=self.scope_a, event_type="person", severity="warning",
            reason="공사 구역 무단출입 감시 강화")
        self.assertFalse(view.lowered)

    def test_a_change_without_a_reason_is_refused(self) -> None:
        """사유 없이는 못 바꾼다 — 사후에 '왜 경보가 안 왔나' 에 답할 자리가 없어진다."""
        with self.assertRaises(ValueError):
            grade_rules.set_grade_rule(scope=self.scope_a, event_type="fire",
                                       severity="info", reason="   ")

    def test_the_history_keeps_what_it_was_and_why(self) -> None:
        """★ 이력이 **무엇에서 무엇으로, 누가, 왜** 를 남긴다.

        `updated_at` 한 칸은 "언제" 만 답한다. 사고 뒤에 필요한 것은 나머지 셋이다.
        """
        grade_rules.set_grade_rule(scope=self.scope_a, event_type="smoke",
                                   severity="warning", reason="연기 오탐이 많아 하향")
        history = grade_rules.grade_rule_history(scope=self.scope_a)
        self.assertTrue(history, "이력이 안 남았습니다.")
        row = history[0]
        self.assertEqual(row["event_type"], "smoke")
        self.assertIsNone(row["old_severity"],
                          "덮어쓴 적이 없던 상태가 null 이 아닙니다 — "
                          "'기본값이었다' 와 '어떤 값이었다' 가 섞입니다.")
        self.assertEqual(row["new_severity"], "warning")
        self.assertIn("오탐", row["reason"])
        self.assertEqual(row["changed_by"], self.user_a.username)

    def test_the_setting_page_counts_the_lowered_ones(self) -> None:
        """★ **낮춘 것의 수를 따로 낸다** (D-301). 목록에 섞이면 눈에 안 띈다."""
        from apps.dsm import services

        grade_rules.set_grade_rule(scope=self.scope_a, event_type="fire",
                                   severity="warning", reason="시험 표본")
        out = services.setting_overview(scope=self.scope_a, domain="grade_rules")
        self.assertEqual(out["lowered_count"], 1,
                         "낮춘 규칙의 수가 따로 안 나옵니다.")


class RefusesWhatIsNotDefinedTest(GradeRuleFixture):
    """★ 없는 것은 없다고 말한다 — 조용히 가장 낮은 등급으로 떨어뜨리지 않는다 (D-284)."""

    def test_an_unknown_event_type_is_refused(self) -> None:
        """조용히 `info` 로 떨어뜨리면 **새 위험이 가장 낮은 등급으로 들어온다.**"""
        with self.assertRaises(grade_rules.GradeRuleNotDefined):
            grade_rules._resolve_severity("earthquake", group=self.group_a)
        with self.assertRaises(grade_rules.GradeRuleNotDefined):
            grade_rules.set_grade_rule(scope=self.scope_a, event_type="earthquake",
                                       severity="critical", reason="새 타입")

    def test_a_severity_outside_the_contract_enum_is_refused(self) -> None:
        """계약 열거 밖의 등급을 **설정 화면에서 만들 수 없다.**

        만들 수 있으면 화면·알림·보고서가 모르는 값이 DB 에 들어가고,
        그 값을 받은 쪽은 각자 다르게 처리한다.
        """
        with self.assertRaises(grade_rules.SeverityNotInContract):
            grade_rules.set_grade_rule(scope=self.scope_a, event_type="fire",
                                       severity="emergency", reason="새 등급")

    def test_nothing_here_claims_to_be_contract_fixed(self) -> None:
        """★ 계약이 **안 정한 것을 계약인 척하지 않는다** (D-280).

        계약 [별첨1] 은 두 열거를 각각 정의하되 **둘을 잇는 규칙은 적지 않았다.**
        표 ①의 F-04 「5분」·F-10 「30초」와 다른 자리다.

        ★ 소스 문자열이 아니라 **모델의 칸과 판정 결과**를 본다. 문자열로 재면
          "왜 여기엔 계약 고정이 없나" 를 설명한 주석까지 위반으로 잡힌다 —
          **설명을 못 쓰게 만드는 시험**은 다음 사람에게서 사유를 빼앗는다.
        """
        Rule = apps.get_model("stream_monitors", "GradeRule")
        fields = {f.name for f in Rule._meta.get_fields()}
        self.assertNotIn(
            "contract_fixed", fields,
            "등급규칙 표에 계약 고정 칸이 생겼습니다 — 계약이 정하지 않은 것을 "
            "계약으로 만들고 있습니다(D-280).")

        # 그리고 실제로 **어느 타입도 잠겨 있지 않다** — 전건이 바뀔 수 있어야 한다
        for view in grade_rules.list_grade_rules(scope=self.scope_a):
            grade_rules.set_grade_rule(
                scope=self.scope_a, event_type=view.event_type,
                severity=view.severity, reason="계약 고정이 없음을 확인하는 재기입")


class GradeRulesAreTenantScopedTest(GradeRuleFixture):
    """★ 규칙은 테넌트별로 다르다 — 하천 지자체와 산업단지가 같을 이유가 없다."""

    def test_another_tenants_rule_does_not_change_my_judgment(self) -> None:
        grade_rules.set_grade_rule(scope=self.scope_b, event_type="fire",
                                   severity="info", reason="남의 테넌트 사정")
        self.assertEqual(
            "critical", grade_rules._resolve_severity("fire", group=self.group_a),
            "★ 남의 테넌트 규칙이 내 판정을 바꿨습니다 — 남이 우리 화재 경보를 껐습니다.")

    def test_another_tenants_rule_is_not_in_my_list(self) -> None:
        grade_rules.set_grade_rule(scope=self.scope_b, event_type="fire",
                                   severity="info", reason="남의 테넌트 사정")
        mine = {r.event_type: r for r in grade_rules.list_grade_rules(scope=self.scope_a)}
        self.assertFalse(mine["fire"].overridden,
                         "남의 덮어쓰기가 내 목록에 보입니다.")

    def test_the_pipeline_sees_only_global_rules(self) -> None:
        """★ **테넌트 없이 부른 판정은 전역 규칙만 본다** (D-281 · D-368).

        [이 시험이 실제로 잡은 것 · 2026-09-10]
            처음 구현은 `group` 이 없으면 **좁히지 않았고**, 그래서 스코프 없이 부른
            판정이 **아무 테넌트의 규칙이나 집었다.** 「좁히지 않는다」와 「전역만
            본다」를 한 값(None)에 둔 것이 원인이었다. 구현이 바뀐 뒤 이 시험이 초록이다.
        """
        grade_rules.set_grade_rule(scope=self.scope_b, event_type="vehicle",
                                   severity="critical", reason="남의 테넌트 사정")
        self.assertEqual(
            "info", grade_rules._resolve_severity("vehicle"),
            "테넌트 없이 부른 판정이 남의 테넌트 규칙을 집었습니다.")

    def test_the_pipeline_resolves_the_tenant_from_the_camera(self) -> None:
        """★ 파이프라인의 테넌트는 **그 카메라의 주인**이다 — 요청자가 아니다.

        위 시험만 있으면 「전역만 본다」로 끝나고, 그러면 **테넌트 규칙이 실제
        검출에는 영원히 안 먹는다.** 설정 화면만 도는 기능이 되는 것이다.
        """
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        mine = self._own(StreamMonitor.objects.create(
            name="grade-cam-a", code="grade-cam-a",
            ip_source="rtsp://grade.invalid/x"), self.group_a)

        grade_rules.set_grade_rule(scope=self.scope_a, event_type="vehicle",
                                   severity="warning", reason="공사구역 차량 통제")

        group = grade_rules._group_of_stream(mine.pk)
        self.assertIsNotNone(group, "카메라에서 주인을 못 찾았습니다.")
        self.assertEqual(
            "warning", grade_rules._resolve_severity("vehicle", group=group),
            "내 테넌트 규칙이 내 카메라의 검출에 안 먹습니다 — 설정 화면에서만 "
            "도는 기능이 됐습니다.")

    def test_a_missing_camera_falls_back_to_global_not_to_a_guess(self) -> None:
        """없는 카메라면 `None` 이고, 그러면 전역만 본다 — **추측하지 않는다.**"""
        self.assertIsNone(grade_rules._group_of_stream(9_999_999))

    # ── 공개 면 — 위 갈래들은 비공개 본체를 재고, 여기는 **밖에서 부르는 문**을 잰다 ──
    def test_the_public_surface_demands_a_scope(self) -> None:
        """★ D-281 — 커널 공개 면은 **테넌트 없이는 부를 수 없다.**

        비공개 본체(`_resolve_severity`)만 재면 그 규약이 지켜지는지 알 수 없다.
        시그니처가 무너지는 것은 **호출이 되기 시작하는 것**으로 나타난다.
        """
        with self.assertRaises(TypeError):
            grade_rules.severity_for(event_type="fire")      # scope 없이

    def test_the_public_surface_resolves_the_tenant_from_the_camera(self) -> None:
        """★ 공개 면이 **카메라의 주인**으로 판정한다 — 파이프라인이 부르는 그 길이다."""
        from common.tenant_scope import TenantScope

        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        mine = self._own(StreamMonitor.objects.create(
            name="grade-pub-a", code="grade-pub-a",
            ip_source="rtsp://grade.invalid/x"), self.group_a)
        grade_rules.set_grade_rule(scope=self.scope_a, event_type="vehicle",
                                   severity="warning", reason="공사구역 차량 통제")

        pipe = TenantScope.system(reason="등급규칙 시험 — 파이프라인에는 요청자가 없다")
        self.assertEqual(
            "warning",
            grade_rules.severity_for(scope=pipe, event_type="vehicle",
                                     stream_monitor_id=mine.pk),
            "공개 면이 카메라의 주인 규칙을 안 집습니다 — 설정 화면에서만 도는 "
            "기능이 됩니다.")
        self.assertEqual(
            "info", grade_rules.severity_for(scope=pipe, event_type="vehicle"),
            "카메라를 안 주면 전역만 봐야 합니다 — 추측하면 남의 규칙이 섞입니다.")

    def test_a_human_without_a_group_is_refused_not_answered_globally(self) -> None:
        """★ 소속 없는 사람에게 **전역 규칙으로 조용히 답하지 않는다.**

        답해 주면 그 사람은 자기 테넌트의 규칙이 적용된 줄 압니다.
        `require_user_group` 이 그 자리에서 멈춥니다.
        """
        from common.tenant_filters import NoTenantGroupError
        from common.tenant_scope import TenantScope

        CoreUser = apps.get_model("user", "CoreUser")
        stray = CoreUser.objects.create_user(
            username="grade_no_group", password="test-only-not-a-secret",
            is_active=True, email="grade_no_group@test.invalid")
        with self.assertRaises(NoTenantGroupError):
            grade_rules.severity_for(scope=TenantScope.of(stray), event_type="fire")

    def test_a_non_admin_cannot_change_a_grade_rule(self) -> None:
        """★ AC-12 「무권한은 차단하며」 — 등급규칙도 그 차단 안이다.

        아무나 등급을 낮출 수 있으면 **아무나 경보를 끌 수 있다.**
        """
        from apps.dsm import services
        from apps.dsm.exceptions import PermissionDeniedForSetting

        Rule = apps.get_model("stream_monitors", "GradeRule")
        before = Rule._base_manager.count()

        with self.assertRaises(PermissionDeniedForSetting) as caught:
            services.set_grade_rule_value(
                scope=self.plain_scope, event_type="fire", severity="info",
                reason="몰래 끄기")
        self.assertTrue(caught.exception.audit_id,
                        "차단이 감사에 안 남았습니다 (AC-12).")
        self.assertEqual(before, Rule._base_manager.count(),
                         "차단했는데 규칙이 바뀌었습니다.")
