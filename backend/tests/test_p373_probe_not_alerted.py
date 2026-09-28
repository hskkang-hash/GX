# -*- coding: utf-8 -*-
"""P-373 — 탐침 계정은 재난 경보를 받지 않는다 (턴 AM · 2026-09-28 · 세종 판정).

`gx-smoke`(스모크 전용 · 역할 `view_only_-_anyang`)가 K2 critical 규칙이 가리키는 역할을 든다 —
실 SMTP 가 붙는 날 경보가 그 주소로 가고 수신자 수를 거짓으로 늘린다. 규칙 표는 **안 고친다**.
계정 쪽 곁표(`BillingMark` probe)로 거른다 · 곁표를 지우면 다시 받는다(되돌리기 한 칸).

캐시 처리: 해당 없음 — HTTP 를 부르지 않고 커널 함수만 부른다.
절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

from common.billing_marks import mark_unbillable
from kernels.k2_notify.services import resolve_recipients
from tests.test_k2_notify_kernel import K2Fixture


class ProbeAccountIsNotARecipient(K2Fixture):
    def test_probe_marked_member_is_excluded_and_unmark_restores(self) -> None:
        probe = self._make_user("gx_smoke_like", self.group_a, self.role_a)
        before = {r.user_id for r in resolve_recipients(scope=self.scope_a, severity="critical")}
        self.assertIn(probe.pk, before, "표식 전에는 규칙대로 받는다 — 전제 확인")
        mark_unbillable(probe, "probe", reason="시험 — 스모크 전용 계정 모양")
        after = {r.user_id for r in resolve_recipients(scope=self.scope_a, severity="critical")}
        self.assertNotIn(probe.pk, after)
        self.assertIn(self.user_a.pk, after, "진짜 수신자는 그대로다 — 규칙 표를 안 건드렸다")
        from common.models import BillingMark
        BillingMark.objects.filter(object_id=str(probe.pk)).delete()
        back = {r.user_id for r in resolve_recipients(scope=self.scope_a, severity="critical")}
        self.assertIn(probe.pk, back, "곁표를 지우면 다시 받는다 — 되돌리기 한 칸")
