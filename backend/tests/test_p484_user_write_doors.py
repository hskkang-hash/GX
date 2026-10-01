# -*- coding: utf-8 -*-
"""P-484 — dj-core 사람 쓰기 문(`update-user` · `delete-user` …)은 **관리자만** (턴 AS).

출생 표본 [실측 2026-10-01 · 시험 DB · 이 파일의 첫 판(실측만)]
------------------------------------------------------------------
    역할 · 문 · 상태 · 대상이 바뀌었나      (CSRF 검사 켬/끔 둘 다 같음)
    U1 관제요원 update-user(남) 200 · 바뀜 · delete-user(남) 200 · 지워짐
    U2 팀장     update-user(남) 200 · 바뀜 · delete-user(남) 200 · 지워짐
    U4 지자체   403 · 403 (② 읽기 전용 규칙)
  dj-core 는 주석에 「관리자 권한 확인」이라 적고 `is_authenticated` 만 본다 → 권한 상승 결함.
  고침 = `common/role_gate.py` 규칙 ④ (dj-core 0줄 · P-274 결).

캐시 처리: **우회** — `X-No-Cache`(NO_CACHE) · 관문을 재는 시험이 캐시를 재면 안 된다(D-341).
라이브 0 · 대상은 이 시험이 만든 탐침 계정뿐.
절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import contextlib
import json

from django.apps import apps
from django.db import transaction
from django.test import Client, TestCase, override_settings

from common import role_gate
from tests.no_cache import NO_CACHE
from tests.test_api_contract import _bearer

PASSWORD = "p484-test-only-not-a-secret"


def _forget_leftover_request() -> None:
    with contextlib.suppress(Exception):
        from core.middleware.refresh_token import thread_local
        thread_local.request = None


class UserWriteDoorsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        _forget_leftover_request()
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")

        def _mk(name, *codes):
            u = CoreUser.objects.create_user(username=name, password=PASSWORD, is_active=True,
                                             email=f"{name}@test.invalid",
                                             first_name="me", last_name="probe")
            for c in codes:
                u.roles.add(Role.objects.get_or_create(code=c, defaults={"role_name": c})[0])
            return u

        cls.callers = {"U1": _mk("p484_operator", "fire_user"),
                       "U2": _mk("p484_manager", "fire_admin"),
                       "U4": _mk("p484_exec", "view_only_-_anyang")}
        cls.admin = _mk("p484_admin", "admin")
        cls.CoreUser = CoreUser

    def tearDown(self):
        _forget_leftover_request()

    def _target(self, tag):
        return self.CoreUser.objects.create_user(
            username=f"gxprobe_p484_{tag}", password=PASSWORD, is_active=True,
            email=f"gxprobe_p484_{tag}@test.invalid", first_name="before", last_name="probe")

    def _call(self, caller, door, target_id, *, profile="false", csrf=False):
        c = Client(enforce_csrf_checks=csrf, raise_request_exception=False, **NO_CACHE)
        sp = transaction.savepoint()
        if door == "update":
            r = c.post(f"/api/v1/user/update-user/{target_id}/{profile}",
                       {"data": json.dumps({"first_name": "after", "last_name": "probe",
                                            "email": f"x{target_id}@test.invalid",
                                            "username": f"gxprobe_p484_x{target_id}"})},
                       **_bearer(caller))
        else:
            r = c.delete(f"/api/v1/user/delete-user/{target_id}", **_bearer(caller))
        _forget_leftover_request()
        (transaction.savepoint_rollback if r.status_code >= 500 else transaction.savepoint_commit)(sp)
        return r

    def _unchanged(self, t):
        row = self.CoreUser._base_manager.filter(pk=t.pk).values().first()
        return (row is not None and row.get("first_name") == "before"
                and not row.get("deleted") and row.get("is_active") is not False)

    def test_birth_sample_non_admins_cannot_change_others(self):
        for csrf in (False, True):
            for role, caller in self.callers.items():
                for door in ("update", "delete"):
                    with self.subTest(role=role, door=door, csrf=csrf):
                        t = self._target(f"{role}_{door}_{int(csrf)}".lower())
                        r = self._call(caller, door, t.id, csrf=csrf)
                        self.assertEqual(403, r.status_code)
                        self.assertTrue(self._unchanged(t), "대상이 바뀌면 안 된다")

    def test_negative_control_admin_is_not_blocked_by_this_rule(self):
        """★ 늘 막는 관문은 관문이 아니라 고장이다 (D-277)."""
        for door in ("update", "delete"):
            with self.subTest(door=door):
                t = self._target(f"admin_{door}")
                r = self._call(self.admin, door, t.id)
                body = r.content.decode("utf-8", "replace")
                self.assertNotIn(role_gate.PEOPLE_WRITE_DENIAL_CODE, body)
                self.assertFalse(self._unchanged(t), "관리자는 실제로 바꿀 수 있어야 한다")

    def test_own_profile_open_but_own_admin_form_closed(self):
        me = self.callers["U1"]
        self.assertIsNone(role_gate.judge_people_write(
            method="POST", path=f"/api/v1/user/update-user/{me.id}/true",
            kinds={"operator"}, user_id=me.id))
        self.assertEqual(role_gate.PEOPLE_WRITE_DENIAL_CODE, role_gate.judge_people_write(
            method="POST", path=f"/api/v1/user/update-user/{me.id}/false",
            kinds={"operator"}, user_id=me.id), "자기라도 관리자 양식은 역할 칸을 바꿀 수 있다")

    def test_unknown_kind_is_blocked_for_writes(self):
        for kinds in (set(), {"other"}, {"operator", "other"}):
            with self.subTest(kinds=kinds):
                self.assertEqual(role_gate.PEOPLE_WRITE_DENIAL_CODE, role_gate.judge_people_write(
                    method="DELETE", path="/api/v1/user/delete-user/9", kinds=kinds, user_id=1))

    def test_other_admin_doors_and_reads_are_classified(self):
        for path in ("/api/v1/user/reject-user", "/api/v1/user/activate-user",
                     "/api/v1/user/deactivate-user", "/api/v1/user/delete-user/3,4"):
            self.assertTrue(role_gate.is_people_write("POST", path), path)
        self.assertFalse(role_gate.is_people_write("GET", "/api/v1/user/update-user/3/false"))
        self.assertFalse(role_gate.is_people_write("POST", "/api/v1/user/settings/update"))

    def test_switch_off_restores_old_behaviour(self):
        with override_settings(ROLE_PEOPLE_WRITE_GATE_ENABLED=False):
            self.assertIsNone(role_gate.judge_people_write(
                method="DELETE", path="/api/v1/user/delete-user/9", kinds={"operator"}, user_id=1))

    def test_measure_anonymous_create_user_door(self):
        """인증 없는 `create-user` — 역할 규칙의 일이 아니다. 재서 찍기만 한다(P-484 보고)."""
        c = Client(raise_request_exception=False, **NO_CACHE)
        sp = transaction.savepoint()
        r = c.post("/api/v1/user/create-user", {"data": "{}"})
        _forget_leftover_request()
        transaction.savepoint_rollback(sp)
        print("\n[P-484] 익명 POST /api/v1/user/create-user → %s · %s"
              % (r.status_code, r.content[:100].decode("utf-8", "replace")))
