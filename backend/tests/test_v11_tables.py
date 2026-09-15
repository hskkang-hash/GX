# -*- coding: utf-8 -*-
"""DSM v1.1 신규 테이블 7 — **태어날 때 테넌트·목적·분류를 갖췄는가** (WO-01 §5 「데이터」).

무엇을 재나
-----------
  ① 격리 — 테넌트 A 의 행이 B 의 스코프 매니저(`objects` = dj-core `CustomManagerGroup`)에서
     **안 보인다.** 음성만 재면 「매니저가 통째로 비었다」와 구별되지 않으므로
     A 자신에게는 **보인다**(양성 대조)와 `_base_manager` 에는 **있다**(행 실재)를 함께 잰다
     — 스레드에 남은 요청이 `objects` 를 비우는 함정(D-253 배선)을 가르는 판별자다.
  ② `purpose_code` 필수 — 빼도 · 빈 문자열을 줘도 **DB 가 거절한다.** Django 의 `blank=False`
     는 폼 검증일 뿐이라 `create()` 는 빈 값을 넣는다. 그래서 CHECK 제약을 재지, 모델
     선언을 재지 않는다.
  ③ 분류 등록 — 새 표는 **격리 대상**(group FK)이고, 면제 등록부(`tenant_classification`)에
     **없고**, 인구조사(`tenant_census`)에 **사유와 함께 있다.**
     ⚠ ③의 인구조사 단언은 `scripts/gen_tenant_census.py::NEW_SINCE_CENSUS` 등재 +
       재생성 전까지 **빨강이 정상이다** — 표에 없는 모델을 초록으로 두면
       `test_census_matches_code` 와 두 말을 하게 된다(D-264).

라우트는 재지 않는다 — 이 턴의 라우트는 U1·U3·U24·U56 차선이 만든다(ISO-03 은 거기서).
"""
from __future__ import annotations

from datetime import time

from django.apps import apps
from django.db import IntegrityError, transaction
from django.utils import timezone

from tests.test_dsm_app import DsmFixture
from tests.test_tenant_isolation import acting_as, is_group_isolatable

#: 신규 테이블 6(+ `WebhookSubscription.filters`) — label → db_table.
V11_TABLES: dict[str, str] = {
    "stream_monitors.DsmHandover": "dsm_handover",
    "stream_monitors.DsmFieldPhoto": "dsm_field_photo",
    "stream_monitors.DsmNotifyPrefs": "dsm_notify_prefs",
    "stream_monitors.DsmOnboardingProgress": "dsm_onboarding_progress",
    "stream_monitors.DsmReportRun": "dsm_report_run",
    "stream_monitors.DsmUpperReportFlag": "dsm_upper_report_flag",
}


class V11TablesFixture(DsmFixture):
    """`DsmFixture` 의 테넌트 A/B · 스트림 · 사건을 그대로 쓴다 — 새 픽스처를 만들지 않는다."""

    def _required(self, label: str) -> dict:
        """label 의 행 하나를 만드는 데 **필요한 칸만** (purpose_code 제외). 소유는 A."""
        now = timezone.now()
        if label.endswith("DsmHandover"):
            return {"body": "미처리 1건 · 시스템 사건 0건 · 내가 처리한 2건",
                    "unresolved_count": 1, "system_event_count": 0, "handled_count": 2}
        if label.endswith("DsmFieldPhoto"):
            return {"event_id": self._event(self.stream_a), "object_key": "dsm/field/1.jpg",
                    "content_type": "image/jpeg", "size_bytes": 1024}
        if label.endswith("DsmNotifyPrefs"):
            return {"user": self.user_a}
        if label.endswith("DsmOnboardingProgress"):
            return {"user": self.user_a, "card_key": "u1.handover", "completed_at": now,
                    "source_ref": "handover#1"}
        if label.endswith("DsmReportRun"):
            return {"kind": "monthly", "trigger": "auto", "status": "succeeded"}
        if label.endswith("DsmUpperReportFlag"):
            return {"event_id": self._event(self.stream_a), "reported_at": now}
        raise AssertionError(f"{label} 의 필수 칸을 모릅니다 — V11_TABLES 와 어긋났습니다")

    def _make_a(self, label: str):
        """테넌트 A 소유 행. 소유는 **명시**하고, 저장 뒤 다시 읽어 확인한다."""
        model = apps.get_model(label)
        with acting_as(self.user_a):
            row = model._base_manager.create(
                purpose_code="dsm.monitor", group=self.group_a, created_by=self.user_a,
                **self._required(label))
        row = model._base_manager.get(pk=row.pk)
        self.assertEqual(self.group_a.pk, row.group_id,
                         f"{label}: 만든 행의 소유가 A 가 아닙니다 — 시험이 무엇을 재는지 모릅니다")
        return row


class V11TablesExistTest(V11TablesFixture):
    def test_the_seven_are_where_the_work_order_says(self) -> None:
        """표 이름 6 + 웹훅 필터 칸 1 — 지시서의 이름 그대로."""
        for label, table in V11_TABLES.items():
            self.assertEqual(table, apps.get_model(label)._meta.db_table, label)

        Sub = apps.get_model("stream_monitors", "WebhookSubscription")
        field = Sub._meta.get_field("filters")
        self.assertEqual({}, field.get_default(),
                         "빈 필터는 「거르지 않는다」여야 한다 — 기존 구독의 발송이 바뀌면 안 된다")


class V11TenantIsolationTest(V11TablesFixture):
    """① A 의 행은 B 의 스코프 매니저에서 안 보인다."""

    def test_another_tenant_cannot_see_the_row(self) -> None:
        for label in V11_TABLES:
            with self.subTest(label=label):
                model = apps.get_model(label)
                row = self._make_a(label)

                self.assertTrue(model._base_manager.filter(pk=row.pk).exists(),
                                f"{label}: 행이 실재하지 않습니다 — 음성 단언이 무의미합니다")
                with acting_as(self.user_a):
                    self.assertTrue(model.objects.filter(pk=row.pk).exists(),
                                    f"{label}: 주인에게도 안 보입니다 — 매니저가 통째로 빈 것입니다")
                with acting_as(self.user_b):
                    self.assertFalse(model.objects.filter(pk=row.pk).exists(),
                                     f"{label}: 테넌트 B 가 A 의 행을 봅니다")


class V11PurposeCodeRequiredTest(V11TablesFixture):
    """② purpose_code 없이는 행이 태어나지 못한다 — DB 가 거절한다."""

    def test_missing_or_empty_purpose_code_is_refused_by_the_database(self) -> None:
        for label in V11_TABLES:
            model = apps.get_model(label)
            for how, extra in (("빠짐", {}), ("빈 문자열", {"purpose_code": ""})):
                with self.subTest(label=label, how=how):
                    with self.assertRaises(IntegrityError,
                                           msg=f"{label}: purpose_code {how} 인데 저장됐습니다"):
                        with transaction.atomic(), acting_as(self.user_a):
                            model._base_manager.create(
                                group=self.group_a, **extra, **self._required(label))

    def test_the_constraint_is_a_check_not_a_default(self) -> None:
        """기본값이 있으면 「필수」가 아니다 — 누가 넣었는지 모르는 값이 채워진다."""
        for label in V11_TABLES:
            field = apps.get_model(label)._meta.get_field("purpose_code")
            self.assertFalse(field.has_default(), f"{label}.purpose_code 에 기본값이 있습니다")
            self.assertFalse(field.null, f"{label}.purpose_code 가 NULL 을 받습니다")


class V11ServerRecordClosesCardTest(V11TablesFixture):
    """WO-01 §12 「온보딩 카드의 완료는 서버 기록이 닫는다」 — 근거 없는 완료는 거절된다."""

    def test_a_card_without_source_ref_is_refused(self) -> None:
        model = apps.get_model("stream_monitors", "DsmOnboardingProgress")
        kwargs = self._required("stream_monitors.DsmOnboardingProgress") | {"source_ref": ""}
        with self.assertRaises(IntegrityError):
            with transaction.atomic(), acting_as(self.user_a):
                model._base_manager.create(purpose_code="dsm.monitor", group=self.group_a, **kwargs)

    def test_quiet_window_cannot_be_half_set(self) -> None:
        """차단 시간대는 둘 다 있거나 둘 다 없다 — 하나만 있으면 「언제까지」를 모른다."""
        model = apps.get_model("stream_monitors", "DsmNotifyPrefs")
        with self.assertRaises(IntegrityError):
            with transaction.atomic(), acting_as(self.user_a):
                model._base_manager.create(purpose_code="dsm.monitor", group=self.group_a,
                                           user=self.user_a, quiet_start=time(22, 0))


class V11ClassificationTest(V11TablesFixture):
    """③ 분류 등록 — 격리 대상이고 · 면제가 아니고 · 인구조사에 사유와 함께 있다."""

    def test_every_v11_table_is_group_isolatable(self) -> None:
        for label in V11_TABLES:
            self.assertTrue(is_group_isolatable(apps.get_model(label)),
                            f"{label}: group FK 가 없습니다 — TenantModel 을 상속하지 않았습니다")

    def test_no_v11_table_is_declared_exempt(self) -> None:
        """새 표는 공용 마스터도 · 주인 없음도 · 보류도 아니다 — 첫 행부터 주인이 있다."""
        from tests import tenant_classification as tc

        declared = tc.all_declared() & set(V11_TABLES)
        self.assertEqual(set(), declared,
                         f"면제 등록부에 신규 표가 있습니다: {sorted(declared)} — 면제를 늘리는 일입니다")

    def test_every_v11_table_is_in_the_census_with_a_reason(self) -> None:
        """⚠ `NEW_SINCE_CENSUS` 등재 + `gen_tenant_census.py` 재생성 전까지 빨강이 정상이다."""
        from tests.tenant_census import CENSUS

        missing = sorted(label for label in V11_TABLES
                         if not (CENSUS.get(label, (None,) * 5)[4] or "").strip())
        self.assertEqual(
            [], missing,
            f"인구조사에 없거나 사유가 빈 신규 표: {missing}\n"
            "scripts/gen_tenant_census.py 의 NEW_SINCE_CENSUS 에 사유를 적고 표를 다시 만드십시오.")
