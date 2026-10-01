# -*- coding: utf-8 -*-
"""P-471 / P-293 — **역할 밖 읽기 면** (턴 AS · 차선 S).

캐시 처리: **우회** — `X-No-Cache` (D-341 착시 ⑦). 관문을 재는 시험이 캐시를 재면
안 된다.

출생 표본 [실측 2026-10-01 · 8500 · GET 만]
-------------------------------------------
관제요원(U1)이 메뉴 밖 10 라우트를 열었다(P-293). 그 화면들이 부르는 API 를 U1
토큰으로 직접 불렀다. 4/10 이 아니라 **자료가 나가는 문이 있었다**:

    GET /api/v1/user/list                 U1 200 (count=54 · 44KB) · U2 200 · U4 200
    GET /api/v1/user/get-user-detail/115  U1 200 (남의 계정 전문 5KB) · U2 200 · U4 200
    GET /api/dsm/stats/by-reviewer        U1 200
    GET /api/dsm/cameras/address-gap      U1 200
    GET /api/dsm/webhook-subscriptions    U1 200
    GET /api/dsm/metering                 U1 200

이 파일이 못박는 것
-------------------
  1) 출생 표본 6 자리는 **운영 역할(U1)에게 403** 이다 — 본문에 자료 0자
  2) 사람 목록·남의 상세는 **관리자만**: U2 · U4 도 403
  3) **음성 대조** — 같은 자리를 허용 역할이 부르면 403 이 아니다
  4) **자기 상세는 열려 있다** — 프로필 화면(rj-core `profile`)이 부른다
  5) 모르는 역할(배송 등)이 섞인 계정은 이 규칙의 일이 아니다
  6) 쓰기 메서드는 이 규칙의 일이 아니다
  7) 되돌리기가 진짜로 되돌아간다 — `ROLE_SURFACE_GATE_ENABLED=False`

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import contextlib
import json

from django.apps import apps
from django.test import Client, SimpleTestCase, TestCase, override_settings

from common import role_gate
from tests.no_cache import NO_CACHE
from tests.test_api_contract import _bearer

PASSWORD = "p471-test-only-not-a-secret"

#: ★ 출생 표본 — (경로, 허용 종류). U1(operator)에게 열려 있던 자리들.
FORMERLY_OPEN_TO_OPERATOR = (
    ("/api/v1/user/list", {"admin"}),
    ("/api/v1/user/get-user-detail/115", {"admin"}),
    # [P-486 · 세종 표] 팀장은 통계·주소 둘만 · 지자체 0 · 웹훅·계량은 관리자만
    ("/api/dsm/stats/by-reviewer", {"admin", "manager"}),
    ("/api/dsm/cameras/address-gap", {"admin", "manager"}),
    ("/api/dsm/webhook-subscriptions", {"admin"}),
    ("/api/dsm/metering", {"admin"}),
)

#: 이미 403 이던 자리 — 이 규칙의 표에 **없어야** 한다(중복 문을 만들지 않는다).
ALREADY_CLOSED_ELSEWHERE = (
    "/api/dsm/reports/runs",
    "/api/dsm/system/storage",
    "/api/dsm/settings/notify-rules/list",
    "/api/roles/",
    "/api/devices/devices-management",
    "/api/report-template/",
)


def _forget_leftover_request() -> None:
    """스레드에 남은 요청을 지운다 — 뒤에 오는 시험을 위해서다."""
    with contextlib.suppress(Exception):
        from core.middleware.refresh_token import thread_local

        thread_local.request = None


class _CleanThreadLocal:
    @classmethod
    def setUpClass(cls):
        _forget_leftover_request()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        _forget_leftover_request()

    def setUp(self):
        _forget_leftover_request()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        _forget_leftover_request()


class SurfaceJudgeTest(SimpleTestCase):
    """`judge_surface()` 한 함수가 규칙 전부다."""

    def test_operator_is_denied_on_every_birth_sample(self):
        for path, _allowed in FORMERLY_OPEN_TO_OPERATOR:
            with self.subTest(path=path):
                self.assertEqual(
                    role_gate.judge_surface(method="GET", path=path,
                                            kinds={"operator"}, user_id=1),
                    role_gate.SURFACE_DENIAL_CODE)

    def test_allowed_kinds_pass_and_others_are_denied(self):
        """★ 음성 대조 + 양성 대조를 종류마다 — 표의 「허용 종류」가 그대로 나온다."""
        for path, allowed in FORMERLY_OPEN_TO_OPERATOR:
            for kind in ("admin", "manager", "executive", "operator"):
                with self.subTest(path=path, kind=kind):
                    got = role_gate.judge_surface(method="GET", path=path,
                                                  kinds={kind}, user_id=1)
                    if kind in allowed:
                        self.assertIsNone(got)
                    else:
                        self.assertEqual(got, role_gate.SURFACE_DENIAL_CODE)

    def test_people_list_is_admin_only(self):
        for kind in ("manager", "executive", "operator"):
            with self.subTest(kind=kind):
                self.assertEqual(
                    role_gate.judge_surface(method="GET", path="/api/v1/user/list",
                                            kinds={kind}, user_id=1),
                    role_gate.SURFACE_DENIAL_CODE)

    def test_own_detail_stays_open(self):
        self.assertIsNone(role_gate.judge_surface(
            method="GET", path="/api/v1/user/get-user-detail/42",
            kinds={"operator"}, user_id=42))
        self.assertEqual(role_gate.judge_surface(
            method="GET", path="/api/v1/user/get-user-detail/43",
            kinds={"operator"}, user_id=42), role_gate.SURFACE_DENIAL_CODE)

    def test_trailing_slash_is_the_same_door(self):
        self.assertEqual(role_gate.judge_surface(
            method="GET", path="/api/v1/user/list/", kinds={"operator"}),
            role_gate.SURFACE_DENIAL_CODE)

    def test_unknown_roles_and_role_zero_are_not_this_rules_business(self):
        for kinds in (set(), {"other"}, {"operator", "other"}):
            with self.subTest(kinds=kinds):
                self.assertIsNone(role_gate.judge_surface(
                    method="GET", path="/api/v1/user/list", kinds=kinds))

    def test_writes_are_not_touched(self):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                self.assertIsNone(role_gate.judge_surface(
                    method=method, path="/api/v1/user/list", kinds={"operator"}))

    def test_outside_the_api_surface_is_not_touched(self):
        for path in ("/admin/", "/static/x.js", "/"):
            self.assertIsNone(role_gate.judge_surface(
                method="GET", path=path, kinds={"operator"}))

    def test_doors_already_closed_elsewhere_are_not_duplicated(self):
        for path in ALREADY_CLOSED_ELSEWHERE:
            with self.subTest(path=path):
                self.assertIsNone(role_gate.match_surface_rule("GET", path))

    @override_settings(ROLE_SURFACE_GATE_ENABLED=False)
    def test_flag_off_denies_nothing(self):
        for path, _a in FORMERLY_OPEN_TO_OPERATOR:
            with self.subTest(path=path):
                self.assertIsNone(role_gate.judge_surface(
                    method="GET", path=path, kinds={"operator"}, user_id=1))

    def test_kinds_from_codes_uses_the_k3_table(self):
        from config import k3_roles as k3

        self.assertEqual(role_gate.kinds_from_codes(k3.K3_ROLE_OPERATORS),
                         frozenset({"operator"}))
        self.assertEqual(role_gate.kinds_from_codes(k3.K3_ROLE_MANAGERS),
                         frozenset({"manager"}))
        self.assertEqual(role_gate.kinds_from_codes(k3.K3_ROLE_EXECUTIVES),
                         frozenset({"executive"}))
        self.assertEqual(role_gate.kinds_from_codes(k3.K3_ROLE_SYSOPS),
                         frozenset({"admin"}))
        self.assertEqual(role_gate.kinds_from_codes(["order", "fire_user"]),
                         frozenset({"operator", "other"}))
        self.assertEqual(role_gate.kinds_from_codes([], is_admin_flag=True),
                         frozenset({"admin"}))


class SurfaceHttpTest(_CleanThreadLocal, TestCase):
    """실제 미들웨어 · 실제 사용자 · 실제 토큰."""

    @classmethod
    def setUpTestData(cls):
        _forget_leftover_request()
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")

        def _role(code):
            r, _ = Role.objects.get_or_create(code=code, defaults={"role_name": code})
            return r

        def _mk(name, *codes, **kw):
            u = CoreUser.objects.create_user(
                username=name, password=PASSWORD, is_active=True,
                email=f"{name}@test.invalid", **kw)
            for c in codes:
                u.roles.add(_role(c))
            return u

        cls.operator = _mk("p471_operator", "fire_user")
        cls.manager = _mk("p471_manager", "fire_admin")
        cls.executive = _mk("p471_exec", "view_only_-_anyang")
        cls.admin = _mk("p471_admin", "admin")
        cls.mixed = _mk("p471_mixed", "fire_user", "delivery_admin")

    def setUp(self):
        super().setUp()
        self.client = Client(**NO_CACHE)

    def _get(self, user, path):
        return self.client.get(path, **_bearer(user))

    def test_operator_gets_403_on_every_birth_sample_with_no_data(self):
        for path, _a in FORMERLY_OPEN_TO_OPERATOR:
            with self.subTest(path=path):
                resp = self._get(self.operator, path)
                self.assertEqual(resp.status_code, 403)
                body = json.loads(resp.content)
                self.assertEqual(body.get("code"), role_gate.SURFACE_DENIAL_CODE)
                self.assertIn("ko", body.get("message", {}))
                self.assertEqual(
                    sorted(body), ["code", "detail", "message", "status_code", "success"],
                    "본문에 자료가 한 칸도 없어야 한다")

    def test_manager_and_executive_cannot_list_people(self):
        for user in (self.manager, self.executive):
            with self.subTest(user=user.username):
                self.assertEqual(self._get(user, "/api/v1/user/list").status_code, 403)
                self.assertEqual(self._get(
                    user, f"/api/v1/user/get-user-detail/{self.operator.id}").status_code,
                    403)

    def test_negative_control_allowed_roles_are_not_403_by_this_gate(self):
        """★ 늘 막는 관문은 관문이 아니라 고장이다 (D-277)."""
        for path, allowed in FORMERLY_OPEN_TO_OPERATOR:
            users = {"admin": self.admin, "manager": self.manager,
                     "executive": self.executive}
            for kind in allowed:
                with self.subTest(path=path, kind=kind):
                    resp = self._get(users[kind], path)
                    body = b"" if resp.status_code != 403 else resp.content
                    self.assertNotIn(role_gate.SURFACE_DENIAL_CODE.encode(), body)

    def test_own_detail_is_not_denied_by_this_gate(self):
        resp = self._get(self.operator, f"/api/v1/user/get-user-detail/{self.operator.id}")
        self.assertNotIn(role_gate.SURFACE_DENIAL_CODE.encode(),
                         resp.content if resp.status_code == 403 else b"")

    def test_mixed_with_unknown_role_is_not_this_gates_business(self):
        resp = self._get(self.mixed, "/api/dsm/stats/by-reviewer")
        self.assertNotIn(role_gate.SURFACE_DENIAL_CODE.encode(),
                         resp.content if resp.status_code == 403 else b"")

    @override_settings(ROLE_SURFACE_GATE_ENABLED=False)
    def test_flag_off_really_reverts(self):
        resp = self._get(self.operator, "/api/dsm/stats/by-reviewer")
        self.assertNotIn(role_gate.SURFACE_DENIAL_CODE.encode(),
                         resp.content if resp.status_code == 403 else b"")

    @override_settings(ROLE_SURFACE_GATE_ENABLED=False)
    def test_other_gates_survive_this_flag(self):
        """스위치가 따로인 이유 — 역할 0 관문은 이 스위치와 무관하게 선다."""
        CoreUser = apps.get_model("user", "CoreUser")
        zero = CoreUser.objects.create_user(
            username="p471_zero", password=PASSWORD, is_active=True,
            email="p471_zero@test.invalid")
        resp = self._get(zero, "/api/dsm/events?limit=1")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(json.loads(resp.content).get("code"), role_gate.DENIAL_CODE)
