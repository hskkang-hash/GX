# -*- coding: utf-8 -*-
"""곁표(`common.models.AuditScope`) 시험 — 쓰기 · 같은 테넌트 읽기 · 다른 테넌트 0
(턴 AO 차선 O · P-411 · `docs/agent/checkpoints/turn-ao/O.md`).

배경
----
`logger.AuditLogs`(dj-core 소유 · §0.4 금지구역)에는 테넌트(group) 칸이 없다.
`apps/fws/office2.py`(F3-18)·`admin_settings.py`(U5-02·U5-03)는 새 표 없이 그
감사 로그 한 줄로 기록하는데, 그래서 지금까지 통계·목록이 "이 감사 행을 쓴
사람 자신의 것만"으로 좁아 있었다. `apps/fws/audit_scope.py` 가 곁표
(`common.models.AuditScope`)로 그 한계를 넘는다 — 이 파일이 그 도우미 자체의
계약 셋을 잰다.

이 파일이 재는 것 — `apps/fws/audit_scope.py` 자체의 계약 셋
-----------------------------------------------------------------
    ① **곁표 쓰기** — `record(...)` 가 감사 행과 함께 `AuditScope` 행을 남긴다
       (`audit_id`·`tenant_group_id` 가 실제 group 과 맞는가).
    ② **같은 테넌트 읽기** — `tenant_audit_ids(...)` 가 **한 테넌트의 여러
       사람**이 쓴 행을 전부 돌려준다(한 사람 것만이 아니다).
    ③ **다른 테넌트는 0** — 격리. 다른 group 의 요청자는 이 테넌트의 감사 행을
       하나도 못 본다.

②③은 HTTP 로도 한 번 더 확인한다(F3-18 계도·단속 — 손으로 부른 함수가 아니라
실제 라우트가 이 도우미를 거치는지).

캐시 처리: `FwsHttpTest`(`test_fws_app.py`)를 그대로 쓴다 — `setUp` 이 이미
`cache.clear()` 와 `NO_CACHE` 헤더를 갖춘 `Client` 를 만든다(`test_fws_f3b.py`
와 같은 규약).
"""
from __future__ import annotations

from django.apps import apps

from common.tenant_scope import TenantScope
from tests.test_fws_app import FwsHttpTest, _qs

PATROL_ENFORCEMENT = "/api/fws/office2/patrol/enforcement"
PATROL_ENFORCEMENT_MINE = "/api/fws/office2/patrol/enforcement/mine"


def _audit_scope_model():
    return apps.get_model("common", "AuditScope")


def _make_second_tenant_a_user(group, suffix: str, *, role=None):
    """`group` 소속 두 번째 사람. `role` 을 주면 그 역할을 붙인다 — 역할 0 계정은
    `common/role_gate.py`(P-105)가 **쓰기 라우트를 통째로 막는다**(역할 판정보다
    앞선 관문이다). HTTP 로 실제 라우트를 두드리는 시험은 역할이 있어야 한다."""
    CoreUser = apps.get_model("user", "CoreUser")
    user = CoreUser.objects.create_user(
        username=f"ao_o_{suffix}", password="test-only-not-a-secret",
        is_active=True, email=f"ao_o_{suffix}@test.invalid")
    link_field = CoreUser._meta.get_field("userprofilelink")
    link_field.related_model.objects.create(
        **{link_field.remote_field.name: user, "group": group})
    if role is not None:
        user.roles.add(role)
    return user


# ═══════════════════════════════════════════════════════════════════════════
# ①②③ — `audit_scope.py` 를 직접 부른다(HTTP 없이) · 도우미 자체의 계약
# ═══════════════════════════════════════════════════════════════════════════
class AuditScopeUnitTest(FwsHttpTest):
    def test_record_writes_a_sidecar_row_with_the_actors_tenant(self) -> None:
        """① 곁표 쓰기 — audit_id·tenant_group_id 가 실제 group 과 맞는다."""
        from apps.fws import audit_scope

        entry = audit_scope.record(
            scope=self.scope_a, logger_name="guardianx.fws.office2", tag="[TEST]",
            action="test.ao_o.record", payload={"x": 1}, reason="시험",
            kind="test.ao_o.record")
        row = _audit_scope_model()._base_manager.get(audit_id=entry.audit_id)
        self.assertEqual(self.group_a.pk, row.tenant_group_id)
        self.assertEqual("test.ao_o.record", row.kind)

    def test_tenant_audit_ids_covers_every_person_in_the_tenant(self) -> None:
        """② 같은 테넌트 읽기 — 한 사람 것만이 아니라 그 테넌트 전원의 것."""
        from apps.fws import audit_scope

        second = _make_second_tenant_a_user(self.group_a, "unit_second")
        scope_a2 = TenantScope.of(second)

        e1 = audit_scope.record(
            scope=self.scope_a, logger_name="guardianx.fws.office2", tag="[TEST]",
            action="test.ao_o.multi", payload={"who": "a"}, reason="시험",
            kind="test.ao_o.multi")
        e2 = audit_scope.record(
            scope=scope_a2, logger_name="guardianx.fws.office2", tag="[TEST]",
            action="test.ao_o.multi", payload={"who": "a2"}, reason="시험",
            kind="test.ao_o.multi")

        ids = audit_scope.tenant_audit_ids(scope=self.scope_a, kind="test.ao_o.multi")
        self.assertEqual({e1.audit_id, e2.audit_id}, ids,
                         "같은 테넌트 두 사람의 감사 행 id 가 합쳐지지 않았다")

    def test_other_tenant_sees_zero(self) -> None:
        """③ 다른 테넌트는 0 — 격리."""
        from apps.fws import audit_scope

        audit_scope.record(
            scope=self.scope_a, logger_name="guardianx.fws.office2", tag="[TEST]",
            action="test.ao_o.isolate", payload={}, reason="시험",
            kind="test.ao_o.isolate")

        ids_b = audit_scope.tenant_audit_ids(scope=self.scope_b, kind="test.ao_o.isolate")
        self.assertEqual(set(), ids_b)

    def test_actor_without_group_skips_the_sidecar_without_raising(self) -> None:
        """소속 group 이 없는 행위자(시스템 스코프는 애초에 못 쓴다 — `require_
        actor` 가 던진다)라도 감사 행 쓰기 자체는 실패하면 안 된다. group 을
        떼어낸 사용자로 이를 확인한다(전역 관리자와 같은 모양의 극단값)."""
        from apps.fws import audit_scope

        CoreUser = apps.get_model("user", "CoreUser")
        groupless = CoreUser.objects.create_user(
            username="ao_o_groupless", password="test-only-not-a-secret",
            is_active=True, email="ao_o_groupless@test.invalid")
        scope_groupless = TenantScope.of(groupless)

        entry = audit_scope.record(
            scope=scope_groupless, logger_name="guardianx.fws.office2", tag="[TEST]",
            action="test.ao_o.groupless", payload={}, reason="시험",
            kind="test.ao_o.groupless")
        self.assertFalse(
            _audit_scope_model()._base_manager.filter(audit_id=entry.audit_id).exists(),
            "group 없는 행위자는 곁표를 안 남긴다(좁힐 테넌트가 없다)")


# ═══════════════════════════════════════════════════════════════════════════
# ②③ HTTP 로 한 번 더 — F3-18 계도·단속(실제 라우트가 이 도우미를 거치는가)
# ═══════════════════════════════════════════════════════════════════════════
class AuditScopeHttpTest(FwsHttpTest):
    def test_two_people_same_tenant_see_each_others_patrol_records(self) -> None:
        second = _make_second_tenant_a_user(self.group_a, "http_second", role=self.role_a)
        head_a = self._bearer(self.user_a)
        head_a2 = self._bearer(second)

        r1 = self.client.post(
            _qs(PATROL_ENFORCEMENT, kind="guidance", location="입구 A"), **head_a)
        self.assertEqual(200, r1.status_code, r1.content)
        r2 = self.client.post(
            _qs(PATROL_ENFORCEMENT, kind="enforcement", location="입구 B"), **head_a2)
        self.assertEqual(200, r2.status_code, r2.content)

        stats = self.client.get(PATROL_ENFORCEMENT_MINE, **head_a2)
        self.assertEqual(200, stats.status_code, stats.content)
        body = self._body(stats)
        self.assertEqual(2, body["total"], "같은 테넌트 두 사람의 기록이 합쳐지지 않았다")
        self.assertEqual(1, body["by_kind"]["guidance"])
        self.assertEqual(1, body["by_kind"]["enforcement"])
        self.assertEqual("tenant", body["scope"])

    def test_other_tenant_gets_zero_patrol_stats(self) -> None:
        head_a = self._bearer(self.user_a)
        resp = self.client.post(_qs(PATROL_ENFORCEMENT, kind="guidance"), **head_a)
        self.assertEqual(200, resp.status_code, resp.content)

        head_b = self._bearer(self.user_b)
        stats = self.client.get(PATROL_ENFORCEMENT_MINE, **head_b)
        self.assertEqual(200, stats.status_code, stats.content)
        body = self._body(stats)
        self.assertEqual(0, body["total"])
        self.assertEqual({}, body["by_kind"])
