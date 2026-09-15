# -*- coding: utf-8 -*-
"""P-113 — **익명이 남의 2단계 인증을 끄던 자리**를 못박는다.

캐시 처리: **우회** — `X-No-Cache` (D-341 착시 ⑦). 관문을 재는 시험이 캐시를 재면
안 된다. 캐시 안쪽에서 답이 나오면 관문이 없어도 초록이 뜬다.

무엇이 있었나 — **출생 표본** [실측 2026-09-10 · TARGET=8500 · 인증 없음]
--------------------------------------------------------------------------
    POST /api/v1/auth/otp/reset   본문 {"username": "gx_nonexistent_probe_zzz"}
      전 -> HTTP **404** {"success":false,...,"ko":"사용자를 찾을 수 없습니다"}
      후 -> HTTP **401** {"detail":"Unauthorized","reason":"authentication required"}

404 는 관문의 답이 아니다. **핸들러가 실제로 돌아 조회까지 갔다**는 뜻이다(P-83 눈금).
실재 사용자명으로는 **일부러 두드리지 않았다** — 그 한 번이 곧 사고다. 「쓴다」의 근거는
dj-core `core/api/v1/auth.py:1990 reset_otp` 의 호출 그래프이고(`opt_mandatory=False` ·
`otp_is_verified=False` · `pyotp.random_base32()` 재발급), 「이 입력으로는 안 썼다」의
근거는 없는 이름으로 잰 404 다. 둘을 섞지 않는다 (D-322).

이 파일이 못박는 것 일곱
------------------------
  1) **익명 → 401.** `access_gate` 의 이름 목록에서 끊긴다 (reset-password-for-user 와 같은 자리)
  2) 로그인만 한 **본인**이 증거 없이 부르면 **401** — 세션 하나로 2FA 가 무너지지 않는다
  3) 본인 + **현재 비밀번호**가 맞으면 통과 (늘 빨간불인 관문은 관문이 아니다 · D-277)
  4) 본인 + **현재 OTP 코드**가 맞아도 통과 — 두 증거 중 하나면 된다
  5) 비관리자가 **남의 계정**을 건드리면 **403** (401 이 아니다 — D-290)
  6) 관리자가 남의 계정을 건드리면 통과하고 **감사 한 줄이 남는다**
  7) 되돌리기가 **진짜로 되돌아간다** — `OTP_RESET_GUARD_ENABLED=False` 면 안 막는다
     (익명 401 은 `access_gate` 의 별개 줄이므로 그때도 남는다 — 그 사실도 못박는다)

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105 · D-224)
    skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import contextlib
import json

from django.apps import apps
from django.contrib.auth.models import AnonymousUser
from django.test import Client, SimpleTestCase, TestCase, override_settings

from common import access_gate, otp_reset_guard
from tests.no_cache import NO_CACHE
from tests.test_api_contract import _bearer

PATH = "/api/v1/auth/otp/reset"
PASSWORD = "p113-test-only-not-a-secret"
OTHER_PASSWORD = "p113-other-only-not-a-secret"


def _forget_leftover_request() -> None:
    """스레드에 남은 요청을 지운다 — **뒤에 오는 시험을 위해서다.**

    dj-core `BaseModel` 이 저장할 때 스레드 지역의 요청 사용자를 `created_by` 로
    채운다. HTTP 시험이 만든 사용자는 롤백으로 사라지는데 요청 객체는 남는다.
    (`tests/test_role_gate.py` 가 실제로 남의 시험 10건을 죽인 그 자리다.)
    """
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

class OtpResetGuardPredicateTest(SimpleTestCase):
    """`is_guarded()` 한 함수가 「이 관문의 일인가」의 전부다."""

    def test_only_post_on_the_named_path(self):
        self.assertTrue(otp_reset_guard.is_guarded(method="POST", path=PATH))
        self.assertTrue(otp_reset_guard.is_guarded(method="post", path=PATH + "/"))

    def test_other_methods_and_paths_are_not_this_gate(self):
        """★ **음성 대조.** 옆자리를 함께 막으면 그것은 관문이 아니라 고장이다."""
        for method, path in (("GET", PATH), ("POST", "/api/v1/auth/otp/verify"),
                             ("POST", "/api/v1/auth/login"),
                             ("POST", "/api/v1/auth/otp/reset-other"),
                             ("PUT", PATH)):
            with self.subTest(method=method, path=path):
                self.assertFalse(otp_reset_guard.is_guarded(method=method, path=path))

    def test_anonymous_is_401_before_anything_else(self):
        verdict = otp_reset_guard.judge(user=AnonymousUser(), body={"username": "x"})
        self.assertEqual(verdict[0], 401)
        self.assertEqual(verdict[1], otp_reset_guard.REASON_ANONYMOUS)
        self.assertEqual(otp_reset_guard.judge(user=None, body={})[0], 401)

    def test_name_is_on_the_access_gate_list(self):
        """★ 익명 401 은 `reset-password-for-user` 와 **같은 목록**에서 나온다."""
        self.assertIn(PATH, access_gate.AUTHN_REQUIRED_PATHS)
        self.assertIn("/api/v1/auth/reset-password-for-user",
                      access_gate.AUTHN_REQUIRED_PATHS)


# ═══════════════════════════════════════════════════════════════════════════
# 2) 실제 사용자로 잰다 — 재인증 증거와 관리자 판정
# ═══════════════════════════════════════════════════════════════════════════

class OtpResetGuardJudgeWithUsersTest(_CleanThreadLocal, TestCase):

    @classmethod
    def setUpTestData(cls):
        _forget_leftover_request()
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")
        cls.plain = CoreUser.objects.create_user(
            username="p113_plain", password=PASSWORD, is_active=True,
            email="p113_plain@test.invalid")
        cls.plain.roles.add(Role.objects.create(role_name="p113_op", code="p113_op"))
        cls.victim = CoreUser.objects.create_user(
            username="p113_victim", password=OTHER_PASSWORD, is_active=True,
            email="p113_victim@test.invalid")
        cls.admin = CoreUser.objects.create_user(
            username="p113_admin", password=PASSWORD, is_active=True,
            email="p113_admin@test.invalid")
        cls.admin.roles.add(Role.objects.create(role_name="p113_admin_role",
                                                code="admin"))
        cls.flag_admin = CoreUser.objects.create_user(
            username="p113_flag_admin", password=PASSWORD, is_active=True,
            email="p113_flag_admin@test.invalid", is_superuser=True)

    # ── 본인 ────────────────────────────────────────────────────────────────
    def test_self_without_proof_is_401(self):
        verdict = otp_reset_guard.judge(
            user=self.plain, body={"username": "p113_plain"})
        self.assertEqual(verdict[0], 401)
        self.assertEqual(verdict[1], otp_reset_guard.REASON_REAUTH)

    def test_empty_username_is_read_as_self(self):
        """대상이 비면 **가장 좁은 해석**을 택한다 — 본인 요청."""
        self.assertEqual(otp_reset_guard.judge(user=self.plain, body={})[0], 401)

    def test_self_with_current_password_passes(self):
        """★ **음성 대조** — 증거가 맞으면 통과한다. 늘 막으면 관문이 아니다."""
        self.assertIsNone(otp_reset_guard.judge(
            user=self.plain,
            body={"username": "p113_plain",
                  otp_reset_guard.REAUTH_PASSWORD_FIELD: PASSWORD}))

    def test_self_with_wrong_password_is_401(self):
        self.assertEqual(otp_reset_guard.judge(
            user=self.plain,
            body={"username": "p113_plain",
                  otp_reset_guard.REAUTH_PASSWORD_FIELD: "wrong"})[0], 401)

    def test_self_with_current_otp_code_passes(self):
        """두 증거 중 **하나**면 된다 — 인증기를 아직 들고 있는 사람의 길."""
        import pyotp

        Profile = apps.get_model("user", "Profile")
        secret = pyotp.random_base32()
        Profile.objects.update_or_create(user=self.plain,
                                         defaults={"otp_secret": secret})
        code = pyotp.TOTP(secret).now()
        self.assertIsNone(otp_reset_guard.judge(
            user=self.plain,
            body={"username": "p113_plain",
                  otp_reset_guard.REAUTH_OTP_FIELD: code}))
        self.assertEqual(otp_reset_guard.judge(
            user=self.plain,
            body={"username": "p113_plain",
                  otp_reset_guard.REAUTH_OTP_FIELD: "000000"})[0], 401)

    # ── 남의 계정 ───────────────────────────────────────────────────────────
    def test_other_account_by_non_admin_is_403(self):
        """★ 401 이 아니라 403 이다 — 누구인지는 아는데 안 된다 (D-290)."""
        verdict = otp_reset_guard.judge(
            user=self.plain, body={"username": "p113_victim"})
        self.assertEqual(verdict[0], 403)
        self.assertEqual(verdict[1], otp_reset_guard.REASON_NOT_ADMIN)

    def test_other_account_by_admin_needs_audit(self):
        status, _reason, needs_audit = otp_reset_guard.judge(
            user=self.admin, body={"username": "p113_victim"})
        self.assertIsNone(status)
        self.assertTrue(needs_audit, "관리자 통과는 **감사 한 줄이 조건**이다")

    def test_administrator_predicate_covers_three_branches(self):
        self.assertTrue(otp_reset_guard.is_administrator(self.admin))
        self.assertTrue(otp_reset_guard.is_administrator(self.flag_admin))
        self.assertFalse(otp_reset_guard.is_administrator(self.plain))
        self.assertFalse(otp_reset_guard.is_administrator(AnonymousUser()))

    def test_audit_row_is_actually_written(self):
        """감사에 남길 수 없으면 그 행위는 일어나지 않는다 — 그러니 남는지 잰다."""
        entry = otp_reset_guard.write_audit(
            actor=self.admin, target="p113_victim", allowed=True,
            reason="test", status=200)
        self.assertGreater(entry.audit_id, 0)
        AuditLogs = apps.get_model("logger", "AuditLogs")
        row = AuditLogs._base_manager.get(pk=entry.audit_id)
        self.assertEqual(row.logger_name, otp_reset_guard.AUDIT_LOGGER_NAME)
        self.assertTrue(row.logger_name.startswith("guardianx."),
                        "체인 접두가 아니면 LAW-08 체인 잇기가 터진다 [실측 #199137]")
        self.assertEqual(row.username, "p113_admin")


# ═══════════════════════════════════════════════════════════════════════════
# 3) 호출로 확인한다 (D-210) — **함수가 아니라 문을 두드린다**
# ═══════════════════════════════════════════════════════════════════════════

class OtpResetOverHttpTest(_CleanThreadLocal, TestCase):
    """캐시 처리: **우회** (`X-No-Cache`)."""

    @classmethod
    def setUpTestData(cls):
        _forget_leftover_request()
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")
        cls.user = CoreUser.objects.create_user(
            username="p113_http_user", password=PASSWORD, is_active=True,
            email="p113_http_user@test.invalid")
        cls.user.roles.add(Role.objects.create(role_name="p113_h", code="p113_h"))
        cls.victim = CoreUser.objects.create_user(
            username="p113_http_victim", password=OTHER_PASSWORD, is_active=True,
            email="p113_http_victim@test.invalid")

    def setUp(self):
        super().setUp()
        self.client = Client(**NO_CACHE)

    def _post(self, body, headers=None):
        return self.client.post(PATH, data=json.dumps(body),
                                content_type="application/json",
                                **(headers or {}))

    def test_anonymous_is_401_and_body_carries_no_data(self):
        """★ **출생 표본이 닫혔다** — 전 404(핸들러 도달) → 후 401."""
        resp = self._post({"username": "p113_http_victim"})
        self.assertEqual(resp.status_code, 401)
        body = json.loads(resp.content)
        self.assertEqual(body.get("detail"), "Unauthorized")
        self.assertNotIn("p113_http_victim", resp.content.decode("utf-8", "replace"),
                         "거절 본문에 대상 이름을 실으면 그것이 계정 열거 창구다")

    def test_authenticated_self_without_proof_is_401(self):
        resp = self._post({"username": "p113_http_user"}, _bearer(self.user))
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(json.loads(resp.content).get("reason"),
                         otp_reset_guard.REASON_REAUTH)

    def test_authenticated_non_admin_on_other_account_is_403(self):
        resp = self._post({"username": "p113_http_victim"}, _bearer(self.user))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(json.loads(resp.content).get("detail"), "Forbidden")

    def test_self_with_password_reaches_the_handler(self):
        """★ **음성 대조** — 증거가 맞으면 관문을 지나 본체가 돈다.

        본체가 돌았다는 근거: 응답이 관문의 401/403 이 **아니고**, dj-core 핸들러가
        제 봉투(`success`)로 답한다. 이 시험 사용자의 OTP 를 실제로 초기화하는
        것이므로 대상은 **이 시험이 만든 사용자**뿐이다 — 남을 건드리지 않는다.
        """
        resp = self._post({"username": "p113_http_user",
                           otp_reset_guard.REAUTH_PASSWORD_FIELD: PASSWORD},
                          _bearer(self.user))
        self.assertNotIn(resp.status_code, (401, 403),
                         "증거가 맞는데도 막으면 관문이 아니라 고장이다 (D-277)")
        self.assertIn("success", resp.content.decode("utf-8", "replace"))

    # ── 되돌리기 (D-212) ────────────────────────────────────────────────────
    @override_settings(OTP_RESET_GUARD_ENABLED=False)
    def test_flag_off_stops_guarding_but_anonymous_stays_401(self):
        """★ 되돌리기가 **진짜로 되돌아간다** — 그리고 익명은 그때도 막힌다.

        두 줄은 별개다: 재인증 규칙은 `OTP_RESET_GUARD_ENABLED`,
        익명 401 은 `access_gate.AUTHN_REQUIRED_PATHS` 의 이름 한 줄이다.
        """
        self.assertEqual(self._post({"username": "p113_http_victim"}).status_code, 401)
        resp = self._post({"username": "p113_http_victim"}, _bearer(self.user))
        self.assertNotIn(resp.status_code, (401, 403),
                         "플래그를 껐는데도 막히면 되돌림이 되돌리지 못한 것이다")
