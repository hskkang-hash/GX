# -*- coding: utf-8 -*-
"""P-119 / SEC-20 — **읽기 전용 역할은 쓰지 못한다.**

캐시 처리: **우회** — `X-No-Cache` (D-341 착시 ⑦). 관문을 재는 시험이 캐시를 재면
안 된다. 캐시 안쪽에서 답이 나오면 관문이 없어도 초록이 뜬다.

무엇이 있었나 — **출생 표본** [실측 2026-09-10 · 사용자 관점 점검]
------------------------------------------------------------------
계정 `gxseed_u4_official` · 역할 코드가 **글자 그대로** `view_only_-_anyang`.
그 계정으로 사건 화면의 「조치 시작」을 눌렀다:

    POST /api/dsm/events/4803/response?to_state=in_progress
      -> **200 · 사건 상태가 실제로 바뀌었다 · 감사 #197207** · 확인 대화상자 없음

전수 [실측 2026-09-10 · `scripts/probe_role_write_surface.py` · 살아 있는 라우터
전수 **377자리**(경로x메서드)]:

    전  gxseed_u4_official (view_only)  막힘 **0** / 377
        gxseed_u1_operator (fire_user)  막힘   0 / 377
        gxseed_u2_manager  (fire_admin) 막힘   0 / 377
        gxseed_u5_sysop    (admin)      막힘   0 / 377
    후  gxseed_u4_official              막힘 **367** / 377   (통과 10 = 손으로 적은 자리)
        나머지 셋                        막힘   0 / 377      (**한 자리도 안 바뀌었다**)

이 파일이 못박는 것 여덟
------------------------
  1) **양성 대조** — 읽기 전용 계정의 쓰기는 **403**, 본문에 자료가 **0자**다
  2) **음성 대조** — 같은 자리를 다른 역할이 부르면 안 걸린다 (D-277)
  3) **읽기는 한 자도 안 만진다** — GET/HEAD/OPTIONS 는 종전 그대로
  4) 로그아웃·세션정리·자기 비밀번호는 **쓰기여도 열려 있다** — 관문이 열쇠를 삼키지 않는다
  5) 잠금 방지 — `is_superuser`·`is_staff` 는 `view_only` 를 달고 있어도 안 막힌다
  6) **역할이 섞인 계정은 읽기 전용이 아니다** — 넓게 세면 내가 남을 잠근다
  7) 역할 0 은 이 규칙의 일이 아니다 — 그쪽은 `has_no_role`(P-105) 이 답한다
  8) 되돌리기가 **진짜로 되돌아간다** — `READONLY_ROLE_GATE_ENABLED=False` 면 안 막고,
     그때도 **역할 0 관문은 그대로 선다**(스위치가 둘인 이유)

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105 · D-224)
    skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import contextlib
import json

from django.apps import apps
from django.contrib.auth.models import AnonymousUser
from django.test import Client, SimpleTestCase, TestCase, override_settings

from common import role_gate
from tests.no_cache import NO_CACHE
from tests.test_api_contract import _bearer

PASSWORD = "p119-test-only-not-a-secret"

#: ★ **출생 표본** — 그날 읽기 전용 계정이 실제로 눌러서 상태를 바꾼 자리, 그리고
#:   같은 계통의 이웃 자리들. 각 줄이 「쓰기인데 열려 있었다」의 증거다.
FORMERLY_OPEN_TO_READ_ONLY = (
    ("POST", "/api/dsm/events/4803/response"),
    ("POST", "/api/dsm/events/4803/reply"),
    ("PUT", "/api/dsm/events/4803"),
    ("DELETE", "/api/dsm/events/4803"),
    ("PATCH", "/api/v1/user/update-user/115"),
    ("POST", "/api/config-management/create"),
)

#: 읽기 전용도 **반드시** 부를 수 있어야 하는 쓰기 자리 (들어오는 길·나가는 길·자기 자신).
MUST_STAY_OPEN = (
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/api/v1/auth/end-session",
    "/api/v1/auth/delete-session",
    "/api/v1/auth/refresh-token",
    "/api/token/refresh",
    "/api/v1/auth/change-password",
)


def _forget_leftover_request() -> None:
    """스레드에 남은 요청을 지운다 — **뒤에 오는 시험을 위해서다** (test_role_gate 와 같은 사유)."""
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


# ═══════════════════════════════════════════════════════════════════════════
# 1) 판정 함수 — 요청 객체 없이 잰다 (D-277 순수 술어)
# ═══════════════════════════════════════════════════════════════════════════

class ReadOnlyJudgeTest(SimpleTestCase):
    """`judge_readonly()` 한 함수가 규칙 전부다. 여기서 갈리면 미들웨어도 갈린다."""

    def test_write_by_read_only_is_denied(self):
        for method, path in FORMERLY_OPEN_TO_READ_ONLY:
            with self.subTest(method=method, path=path):
                self.assertEqual(
                    role_gate.judge_readonly(method=method, path=path, read_only=True),
                    role_gate.READONLY_DENIAL_CODE)

    def test_other_roles_are_not_touched(self):
        """★ **음성 대조.** 늘 막는 관문은 관문이 아니라 고장이다 (D-277)."""
        for method, path in FORMERLY_OPEN_TO_READ_ONLY:
            with self.subTest(method=method, path=path):
                self.assertIsNone(role_gate.judge_readonly(
                    method=method, path=path, read_only=False))

    def test_reads_are_never_touched(self):
        """★ 이 규칙은 **쓰기 규칙**이다. 읽기를 막으면 읽기 전용이 아니라 무용 계정이다."""
        for method in ("GET", "HEAD", "OPTIONS"):
            for _m, path in FORMERLY_OPEN_TO_READ_ONLY:
                with self.subTest(method=method, path=path):
                    self.assertIsNone(role_gate.judge_readonly(
                        method=method, path=path, read_only=True))

    def test_way_in_and_way_out_stay_open(self):
        """관문이 문을 잠그고 열쇠를 삼키면 읽기 전용 계정은 로그아웃도 못 한다."""
        for path in MUST_STAY_OPEN:
            with self.subTest(path=path):
                self.assertIsNone(role_gate.judge_readonly(
                    method="POST", path=path, read_only=True))

    def test_outside_the_api_surface_is_not_touched(self):
        for path in ("/admin/", "/static/x.js", "/", "/health"):
            with self.subTest(path=path):
                self.assertIsNone(role_gate.judge_readonly(
                    method="POST", path=path, read_only=True))

    def test_write_methods_are_exactly_four(self):
        self.assertEqual(role_gate.WRITE_METHODS,
                         frozenset({"POST", "PUT", "PATCH", "DELETE"}))
        for m in ("POST", "put", "Patch", "DELETE"):
            self.assertTrue(role_gate.is_write_method(m))
        for m in ("GET", "HEAD", "OPTIONS", "TRACE", ""):
            self.assertFalse(role_gate.is_write_method(m))

    @override_settings(READONLY_ROLE_GATE_ENABLED=False)
    def test_flag_off_denies_nothing(self):
        for method, path in FORMERLY_OPEN_TO_READ_ONLY:
            with self.subTest(method=method, path=path):
                self.assertIsNone(role_gate.judge_readonly(
                    method=method, path=path, read_only=True))


# ═══════════════════════════════════════════════════════════════════════════
# 2) 「읽기 전용인가」 — 실제 사용자로 잰다
# ═══════════════════════════════════════════════════════════════════════════

class IsReadOnlyTest(_CleanThreadLocal, TestCase):
    """이 판정이 틀리면 나머지 전부가 틀린다. 그래서 실제 사용자로 잰다."""

    @classmethod
    def setUpTestData(cls):
        _forget_leftover_request()
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")
        cls.view_only_role = Role.objects.create(role_name="View Only - Test",
                                                 code="view_only_-_test")
        cls.other_role = Role.objects.create(role_name="p119_op", code="p119_op")

        def _mk(name, **kw):
            return CoreUser.objects.create_user(
                username=name, password=PASSWORD, is_active=True,
                email=f"{name}@test.invalid", **kw)

        cls.reader = _mk("p119_reader")
        cls.reader.roles.add(cls.view_only_role)
        cls.writer = _mk("p119_writer")
        cls.writer.roles.add(cls.other_role)
        cls.mixed = _mk("p119_mixed")
        cls.mixed.roles.add(cls.view_only_role, cls.other_role)
        cls.role_zero = _mk("p119_role_zero")
        cls.flag_admin = _mk("p119_flag_admin", is_superuser=True)
        cls.flag_admin.roles.add(cls.view_only_role)
        cls.staff = _mk("p119_staff", is_staff=True)
        cls.staff.roles.add(cls.view_only_role)

    def test_view_only_role_is_read_only(self):
        self.assertTrue(role_gate.is_read_only(self.reader))

    def test_another_role_is_not(self):
        """★ **음성 대조** — 이 관문에 걸리지 않는 역할이 실제로 있어야 한다."""
        self.assertFalse(role_gate.is_read_only(self.writer))

    def test_mixed_roles_are_not_read_only(self):
        """★ `view_only` **와 함께** 다른 역할을 가진 계정은 관리자다 — 잠그지 않는다.

        「하나라도 view_only 면 막는다」로 세면 그런 계정의 쓰기가 전부 막히고,
        그것은 내가 만든 회귀다. [실측 2026-09-10] 지금 DB 에 그런 계정은 0개다 —
        그래도 **좁은 쪽**을 못박는다. 넓은 쪽은 나중에 조용히 남을 잠근다.
        """
        self.assertFalse(role_gate.is_read_only(self.mixed))

    def test_role_zero_is_not_this_rule(self):
        """역할 0 은 P-105 의 일이다. 두 규칙이 겹치면 사유가 섞인다."""
        self.assertFalse(role_gate.is_read_only(self.role_zero))
        self.assertTrue(role_gate.has_no_role(self.role_zero))

    def test_anonymous_is_not_read_only(self):
        """익명은 이 겹의 일이 아니다 — 401 은 `access_gate` 의 몫이다."""
        self.assertFalse(role_gate.is_read_only(AnonymousUser()))
        self.assertFalse(role_gate.is_read_only(None))

    def test_superuser_and_staff_are_never_locked_out(self):
        """★ **잠금 방지.** DB 플래그 관리자를 역할표 한 줄로 잠그지 않는다."""
        self.assertFalse(role_gate.is_read_only(self.flag_admin))
        self.assertFalse(role_gate.is_read_only(self.staff))

    def test_the_prefix_is_what_the_live_role_code_starts_with(self):
        """★ 출생 표본의 역할 코드가 실제로 이 접두에 걸리는지 못박는다."""
        self.assertTrue("view_only_-_anyang".startswith(role_gate.READONLY_ROLE_PREFIX))
        self.assertFalse("fire_admin".startswith(role_gate.READONLY_ROLE_PREFIX))
        self.assertFalse("admin".startswith(role_gate.READONLY_ROLE_PREFIX))


# ═══════════════════════════════════════════════════════════════════════════
# 3) 호출로 확인한다 (D-210) — **함수가 아니라 문을 두드린다**
# ═══════════════════════════════════════════════════════════════════════════

class ReadOnlyOverHttpTest(_CleanThreadLocal, TestCase):
    """캐시 처리: **우회** (`X-No-Cache`)."""

    @classmethod
    def setUpTestData(cls):
        _forget_leftover_request()
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")
        view_only = Role.objects.create(role_name="View Only - Http",
                                        code="view_only_-_http")
        other = Role.objects.create(role_name="p119_http_op", code="p119_http_op")
        cls.reader = CoreUser.objects.create_user(
            username="p119_http_reader", password=PASSWORD, is_active=True,
            email="p119_http_reader@test.invalid")
        cls.reader.roles.add(view_only)
        cls.writer = CoreUser.objects.create_user(
            username="p119_http_writer", password=PASSWORD, is_active=True,
            email="p119_http_writer@test.invalid")
        cls.writer.roles.add(other)

    def setUp(self):
        super().setUp()
        self.client = Client(**NO_CACHE)

    def _write(self, user, method="POST",
               path="/api/dsm/events/999999999/response"):
        """★ **실재하지 않는 id 로 두드린다.** 실재 id 로 쓰기 면을 때리는 것이 곧 사고다."""
        return self.client.generic(method, path, data=b"{}",
                                   content_type="application/json",
                                   **_bearer(user))

    def test_read_only_write_is_403_with_no_tenant_data(self):
        resp = self._write(self.reader)
        self.assertEqual(resp.status_code, 403)
        body = json.loads(resp.content)
        self.assertEqual(body.get("code"), role_gate.READONLY_DENIAL_CODE)
        self.assertEqual(body.get("status_code"), 403)
        self.assertIn("ko", body.get("message", {}))
        self.assertNotIn("role_pending_url", body,
                         "역할을 기다리는 것이 아니라 역할이 그런 것이다 — 사유를 섞지 않는다")

    def test_the_same_door_is_not_403_for_another_role(self):
        """★ **음성 대조** — 관문이 늘 빨간불이면 그것은 관문이 아니다."""
        resp = self._write(self.writer)
        self.assertNotEqual(resp.status_code, 403)

    def test_all_four_write_methods_are_closed(self):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                self.assertEqual(self._write(self.reader, method).status_code, 403)

    def test_reads_still_work(self):
        """읽기 전용은 **읽을 수 있어야** 한다."""
        resp = self.client.get("/api/dsm/events?limit=1", **_bearer(self.reader))
        self.assertNotEqual(resp.status_code, 403)

    def test_logout_still_works(self):
        """★ 로그아웃(POST)이 막히면 관문이 열쇠를 삼킨 것이다."""
        resp = self.client.post("/api/v1/auth/logout", data=b"{}",
                                content_type="application/json",
                                **_bearer(self.reader))
        self.assertNotEqual(resp.status_code, 403)

    # ── 되돌리기 (D-212) ────────────────────────────────────────────────────
    @override_settings(READONLY_ROLE_GATE_ENABLED=False)
    def test_flag_off_really_reverts(self):
        self.assertNotEqual(self._write(self.reader).status_code, 403)

    @override_settings(READONLY_ROLE_GATE_ENABLED=False)
    def test_role_zero_gate_survives_this_flag(self):
        """★ 스위치가 **둘인 이유** — 하나를 끄려다 둘이 꺼지면 그날 구멍이 하나 열린다."""
        CoreUser = apps.get_model("user", "CoreUser")
        zero = CoreUser.objects.create_user(
            username="p119_flag_zero", password=PASSWORD, is_active=True,
            email="p119_flag_zero@test.invalid")
        resp = self.client.get("/api/dsm/events?limit=1", **_bearer(zero))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(json.loads(resp.content).get("code"), role_gate.DENIAL_CODE)
