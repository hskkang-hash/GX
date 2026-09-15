# -*- coding: utf-8 -*-
"""P-105 — **역할 없는 계정은 아무것도 보지 않는다.**

캐시 처리: **우회** — `X-No-Cache` (D-341 착시 ⑦). 관문을 재는 시험이 캐시를 재면 안 된다.
캐시 안쪽에서 답이 나오면 관문이 없어도 초록이 뜬다 — 이 저장소가 실제로 겪은 일이다.

무엇이 있었나 — **출생 표본** [실측 2026-09-07 · `gxprobe_e2e` · `user.roles` == []]
--------------------------------------------------------------------------------------
화면이 실제로 부르는 53자리를 다섯 계정으로 같이 쟀다:

    gxprobe_e2e         roles=[]                  200:35  **그중 21자리가 실자료**
    gxseed_u1_operator  fire_user                 200:35  22
    gxseed_u2_manager   fire_admin                200:35  22
    gxseed_u4_official  view_only_-_anyang        200:35  22
    gxseed_u5_sysop     admin                     200:37  28

**역할 0 이 운영자와 거의 같은 것을 봤다.** 나간 것 중에는 사건 목록(카메라명·시각·판정)·
배송·사용자 그룹, 그리고 **남의 계정 전문**(`/api/v1/user/get-user-detail/115` · 5,487B)이
있었다. 「인증됐다」와 「봐도 된다」 사이에 아무것도 서 있지 않았다.

이 파일이 못박는 것 여섯
------------------------
  1) **양성 대조** — 역할 0 이 임의 API 를 부르면 **403**, 본문에 자료가 **0자**다
  2) **음성 대조** — 역할을 **하나 가진** 사용자는 같은 문에서 관문에 안 걸린다
     (늘 빨간불인 관문은 관문이 아니다 · D-277)
  3) 그 하나의 문(`/api/v1/access/role-pending`)은 역할 0 에게도 **열려 있다**
  4) 관리자 알림은 **1건**이다 — 두 번 불러도 1건 (계약: 「알림 1건」)
  5) 잠금 방지 — `is_superuser`·`is_staff` 는 역할 표가 비어도 **안 막힌다**
  6) 되돌리기가 **진짜로 되돌아간다** — `ROLE_GATE_ENABLED=False` 면 한 요청도 안 막는다

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105 · D-224)
    skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import contextlib
import json

from django.apps import apps
from django.contrib.auth.models import AnonymousUser
from django.test import Client, SimpleTestCase, TestCase, override_settings

from common import role_gate, role_request
from tests.no_cache import NO_CACHE
#: ★ **JWT 머리글을 여기서 다시 만들지 않는다** (D-212). dj-core 는 토큰의 `jti` 를
#:   사용자에 저장된 세션값과 대조하고, 그 세 단계는 `tests/test_api_contract.py` 가
#:   이미 한 곳에 적어 두었다. 복사본을 만들면 한쪽이 고쳐지는 날 다른 쪽이 조용히
#:   401 을 내고, 그 401 은 「관문이 일했다」로 오독된다.
from tests.test_api_contract import _bearer

#: ★ **출생 표본** — 그날 역할 0 에게 200 + 실자료로 나간 자리와 바이트.
#:   이 시험이 태어난 이유이고, 각 줄이 실제로 잰 값이다.
FORMERLY_OPEN_TO_ROLE_ZERO = (
    ("/api/dsm/events", 8963),
    ("/api/dsm/events/queue", 3945),
    ("/api/dsm/deliveries", 8035),
    ("/api/v1/user/get-user-detail/115", 5487),
    ("/api/user-groups/", 823),
    ("/api/config-management/list-optimized", 16436),
    ("/api/stream-monitors/stream-monitors", 2057),
    ("/api/advanced-table/grid-management/50/detail", 24999),
)

PASSWORD = "test-only-not-a-secret"


def _forget_leftover_request() -> None:
    """스레드에 남은 요청을 지운다. **뒤에 오는 시험을 위해서다.**

    ★ [실측 2026-09-07 · 이 파일이 실제로 남의 시험을 죽였다] 이 파일의 HTTP 시험이
      지나간 뒤 `tests/test_s_evidence_chain.py` 가 **10건 빨개졌다**:

          psycopg2.errors.ForeignKeyViolation:
            insert or update on table "logger_auditlogs" violates foreign key
            constraint "..._created_by_id_..._fk_user_coreuser_id"
            DETAIL:  Key (created_by_id)=(9) is not present in table "user_coreuser".

      dj-core 의 `BaseModel` 은 저장할 때 **스레드 지역에 남은 요청**의 사용자를
      `created_by` 로 채운다. 우리 HTTP 시험이 만든 사용자는 롤백으로 사라지는데
      그 요청 객체는 스레드에 남고, 다음 파일이 감사 행을 쓸 때 없는 id 를 참조한다.

      **그 빨강은 그 파일의 결함처럼 보이지만 우리가 남긴 상태다.** 파일 단독으로는
      22건 전부 초록이었고 전수에서만 빨갰다 — 순서가 바뀌면 범인이 바뀐다.
      그러므로 치우는 것은 **더럽힌 쪽의 일**이다. 앞뒤로 모두 지운다.
    """
    with contextlib.suppress(Exception):
        from core.middleware.refresh_token import thread_local

        thread_local.request = None


class _CleanThreadLocal:
    """앞뒤로 스레드 지역을 비우는 혼합. 이 파일의 모든 `TestCase` 가 든다."""

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

class RoleGateJudgeTest(SimpleTestCase):
    """`judge()` 한 함수가 규칙 전부다. 여기서 갈리면 미들웨어도 갈린다."""

    def test_role_zero_is_denied_on_api_surface(self):
        for path, _bytes in FORMERLY_OPEN_TO_ROLE_ZERO:
            with self.subTest(path=path):
                self.assertEqual(role_gate.judge(path=path, no_role=True),
                                 role_gate.DENIAL_CODE)

    def test_role_holder_is_not_touched(self):
        """★ **음성 대조.** 늘 막는 관문은 관문이 아니라 고장이다."""
        for path, _bytes in FORMERLY_OPEN_TO_ROLE_ZERO:
            with self.subTest(path=path):
                self.assertIsNone(role_gate.judge(path=path, no_role=False))

    def test_login_surface_stays_open(self):
        """관문이 문을 잠그고 열쇠를 삼키면 아무도 못 들어온다."""
        for path in ("/api/v1/auth/login", "/api/v1/auth/csrf-token",
                     "/api/v1/auth/logout", "/api/v1/auth/otp/verify",
                     "/api/token/refresh", role_gate.ROLE_PENDING_PATH):
            with self.subTest(path=path):
                self.assertIsNone(role_gate.judge(path=path, no_role=True))

    def test_profile_surface_is_not_open(self):
        """★ 넓은 규칙(`AUTHN_SURFACE`)이 덮던 자리는 **여기서는 안 열린다.**

        `access_gate` 가 P-83 에서 겪은 것과 같은 모양이다 — 넓은 면제 아래에
        좁은 사고가 숨는다. 이 넷은 전부 실제 자료를 내는 자리다.
        """
        for path in ("/api/v1/auth/profile", "/api/v1/auth/data-for-profile",
                     "/api/v1/auth/groups", "/api/v1/auth/departments",
                     "/api/v1/auth/teams", "/api/v1/auth/account"):
            with self.subTest(path=path):
                self.assertEqual(role_gate.judge(path=path, no_role=True),
                                 role_gate.DENIAL_CODE)

    def test_non_api_surface_is_not_touched(self):
        """API 밖까지 막으면 로그인 화면과 정적 파일이 함께 막힌다."""
        for path in ("/", "/login", "/admin/", "/static/app.js"):
            with self.subTest(path=path):
                self.assertIsNone(role_gate.judge(path=path, no_role=True))

    @override_settings(ROLE_GATE_ENABLED=False)
    def test_revert_switch_actually_reverts(self):
        """되돌리기 한 줄이 **진짜로 되돌아간다** (D-212)."""
        for path, _bytes in FORMERLY_OPEN_TO_ROLE_ZERO:
            with self.subTest(path=path):
                self.assertIsNone(role_gate.judge(path=path, no_role=True))

    def test_denial_body_carries_no_data(self):
        """거절 본문에 **테넌트 자료가 한 자도 없다.**

        표지를 손으로 세지 않는다 — 본문 전체를 글자로 만들어, 그날 새 나간 값의
        조각이 하나라도 있으면 잡는다.
        """
        text = json.dumps(role_gate.denial_payload(), ensure_ascii=False)
        for leaked in ("camera", "event_id", "verdict", "username",
                       "get-user-detail", "gxprobe", "group_id"):
            with self.subTest(leaked=leaked):
                self.assertNotIn(leaked, text)
        self.assertEqual(role_gate.denial_payload()["status_code"], 403)
        self.assertEqual(role_gate.denial_payload()["code"], "role_required")

    def test_denial_message_is_readable_by_the_existing_frontend_handler(self):
        """앞단의 기존 전역 거절 처리기가 읽는 자리는 `message.ko` 다.

        `frontend/src/features/session/permissionDenied.ts::messageOfDenial` 이
        `message` 를 다국어 객체로도 받는다 — 그래서 앞단을 한 줄도 안 고쳐도 띠가 뜬다.
        모양이 갈리면 사람이 보는 것은 사전의 기본 문장이 되고, 그것은 이 절의 문장이 아니다.
        """
        message = role_gate.denial_payload()["message"]
        self.assertIsInstance(message, dict)
        self.assertIn("역할", message["ko"])
        self.assertTrue(message["en"])


# ═══════════════════════════════════════════════════════════════════════════
# 2) 역할 0 판정 — **`role` 이 아니라 `roles` 로 잰다**
# ═══════════════════════════════════════════════════════════════════════════

class HasNoRoleTest(_CleanThreadLocal, TestCase):
    """이 판정이 틀리면 나머지 전부가 틀린다. 그래서 실제 사용자로 잰다."""

    @classmethod
    def setUpTestData(cls):
        _forget_leftover_request()
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")
        cls.role_zero = CoreUser.objects.create_user(
            username="p105_role_zero", password=PASSWORD, is_active=True,
            email="p105_role_zero@test.invalid")
        cls.role_one = CoreUser.objects.create_user(
            username="p105_role_one", password=PASSWORD, is_active=True,
            email="p105_role_one@test.invalid")
        cls.role_one.roles.add(Role.objects.create(role_name="p105_op", code="p105_op"))
        cls.flag_admin = CoreUser.objects.create_user(
            username="p105_flag_admin", password=PASSWORD, is_active=True,
            email="p105_flag_admin@test.invalid", is_superuser=True)
        cls.staff = CoreUser.objects.create_user(
            username="p105_staff", password=PASSWORD, is_active=True,
            email="p105_staff@test.invalid", is_staff=True)

    def test_role_zero_is_role_zero(self):
        self.assertTrue(role_gate.has_no_role(self.role_zero))

    def test_one_role_is_enough(self):
        """★ **음성 대조** — 역할 하나면 이 관문에 안 걸린다."""
        self.assertFalse(role_gate.has_no_role(self.role_one))

    def test_anonymous_is_not_role_zero(self):
        """익명은 이 겹의 일이 아니다 — 401 은 `access_gate` 와 라우트 관문의 몫이다."""
        self.assertFalse(role_gate.has_no_role(AnonymousUser()))
        self.assertFalse(role_gate.has_no_role(None))

    def test_superuser_and_staff_are_never_locked_out(self):
        """★ **잠금 방지.** 이들을 막으면 역할을 부여할 사람이 사라진다."""
        self.assertFalse(role_gate.has_no_role(self.flag_admin))
        self.assertFalse(role_gate.has_no_role(self.staff))

    def test_singular_role_attribute_does_not_exist(self):
        """★ 이 사고를 세 턴 동안 덮은 것이 바로 이 사실이다.

        `getattr(u, "role", None)` 은 **언제나 None** 이고, 그 None 을 측정으로 읽으면
        「역할이 없다」와 「역할을 못 쟀다」가 같은 값이 된다. 못박아 둔다 — 이 필드가
        생기는 날 이 시험이 빨개지고, 그때 판정을 다시 정하라는 뜻이다.
        """
        self.assertIsNone(getattr(self.role_one, "role", None))
        self.assertEqual(list(self.role_one.roles.values_list("code", flat=True)),
                         ["p105_op"])


# ═══════════════════════════════════════════════════════════════════════════
# 3) 호출로 확인한다 (D-210) — **함수가 아니라 문을 두드린다**
# ═══════════════════════════════════════════════════════════════════════════

class RoleGateOverHttpTest(_CleanThreadLocal, TestCase):
    """캐시 처리: **우회** (`X-No-Cache`) — 관문을 재는 시험이 캐시를 재면 안 된다."""

    @classmethod
    def setUpTestData(cls):
        _forget_leftover_request()
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")
        cls.role_zero = CoreUser.objects.create_user(
            username="p105_http_zero", password=PASSWORD, is_active=True,
            email="p105_http_zero@test.invalid")
        cls.role_one = CoreUser.objects.create_user(
            username="p105_http_one", password=PASSWORD, is_active=True,
            email="p105_http_one@test.invalid")
        cls.role_one.roles.add(Role.objects.create(role_name="p105_h", code="p105_h"))

    def setUp(self):
        self.client = Client(**NO_CACHE)

    def test_positive_control_role_zero_gets_403_with_no_data(self):
        """★ **양성 대조** — 그날 자료가 나가던 자리에서 403 이 나오고 본문이 비었다.

        ★ 세션 로그인이 아니라 **Bearer 로 때린다.** 운영에서 이 관문이 보는
          `request.user` 는 dj-core `JWTUserRestoreMiddleware` 가 토큰에서 세워 준
          것이고, 세션으로 재면 그 겹을 건너뛴 판을 재게 된다 — 재지 않은 것을 잰
          것으로 읽는 자리다(D-301).
        """
        authn_headers = _bearer(self.role_zero)
        for path, _bytes in FORMERLY_OPEN_TO_ROLE_ZERO:
            with self.subTest(path=path):
                response = self.client.get(path, **authn_headers)
                self.assertEqual(response.status_code, 403)
                body = json.loads(response.content.decode("utf-8"))
                self.assertEqual(body["code"], "role_required")
                # 본문은 **고정 문자열**이다. 요청에서 가져온 글자가 한 자도 없다.
                self.assertEqual(body, role_gate.denial_payload())

    def test_negative_control_role_holder_is_not_stopped_by_this_gate(self):
        """★ **음성 대조** — 역할을 가진 사용자는 이 관문에 **안 걸린다.**

        그 뒤에 무엇이 오는가(`@path_permission` 의 403 · 404 · 200)는 이 절의 일이
        아니다. 이 시험이 못박는 것은 하나다: **이 관문의 거절이 아니다.**
        늘 막는 관문은 관문이 아니라 고장이고, 그 고장은 역할 보유자의 화면을 죽인다.
        """
        authn_headers = _bearer(self.role_one)
        for path, _bytes in FORMERLY_OPEN_TO_ROLE_ZERO:
            with self.subTest(path=path):
                response = self.client.get(path, **authn_headers)
                if response.status_code != 403:
                    continue
                body = json.loads(response.content.decode("utf-8"))
                self.assertNotEqual(
                    body.get("code"), role_gate.DENIAL_CODE,
                    f"{path}: 역할 보유자가 **역할 0 관문**에 걸렸다 — 회귀다")

    def test_the_one_open_door_is_open_to_role_zero(self):
        response = self.client.get(role_gate.ROLE_PENDING_PATH,
                                   **_bearer(self.role_zero))
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content.decode("utf-8"))
        self.assertEqual(body["state"], "pending")
        self.assertEqual(body["roles"], [])
        self.assertIn("역할", body["message"])

    def test_role_holder_also_gets_200_on_that_door(self):
        """역할이 **있다**는 답도 답이다. 여기서 403 을 내면 앞단이 문장을 못 그린다."""
        response = self.client.get(role_gate.ROLE_PENDING_PATH,
                                   **_bearer(self.role_one))
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content.decode("utf-8"))
        self.assertEqual(body["state"], "has_roles")
        self.assertEqual(body["roles"], ["p105_h"])

    def test_anonymous_gets_401_not_403_on_that_door(self):
        """「누구인지 모른다」와 「누구인지는 아는데 안 된다」는 다른 문장이다 (D-290)."""
        response = self.client.get(role_gate.ROLE_PENDING_PATH)
        self.assertEqual(response.status_code, 401)

    @override_settings(ROLE_GATE_ENABLED=False)
    def test_revert_switch_reopens_over_http(self):
        """되돌리기가 **호출 수준에서도** 되돌아간다 — 설정만 보고 믿지 않는다."""
        response = self.client.get("/api/dsm/events", **_bearer(self.role_zero))
        if response.status_code == 403:
            body = json.loads(response.content.decode("utf-8"))
            self.assertNotEqual(body.get("code"), role_gate.DENIAL_CODE)


# ═══════════════════════════════════════════════════════════════════════════
# 4) 관리자 알림 — **1건이 계약이다**
# ═══════════════════════════════════════════════════════════════════════════

class RoleRequestNotificationTest(_CleanThreadLocal, TestCase):
    """새로고침마다 1건이면 관리자의 대장이 곧 못 쓰게 된다."""

    @classmethod
    def setUpTestData(cls):
        _forget_leftover_request()
        CoreUser = apps.get_model("user", "CoreUser")
        cls.role_zero = CoreUser.objects.create_user(
            username="p105_notify_zero", password=PASSWORD, is_active=True,
            email="p105_notify_zero@test.invalid")
        cls.admin = CoreUser.objects.create_user(
            username="p105_notify_admin", password=PASSWORD, is_active=True,
            email="p105_notify_admin@test.invalid", is_superuser=True)

    def test_first_call_notifies_and_second_does_not(self):
        first = role_request.notify_admin(self.role_zero)
        self.assertTrue(first["sent"])
        self.assertFalse(first["already_sent"])

        second = role_request.notify_admin(self.role_zero)
        self.assertFalse(second["sent"])
        self.assertTrue(second["already_sent"])

        rows = [r for r in role_request.pending_requests()
                if r.actor_id == self.role_zero.pk]
        self.assertEqual(len(rows), 1, "「알림 1건」이 계약이다")

    def test_administrator_is_named_or_declared_absent(self):
        """관리자를 못 찾으면 **없다고 낸다.** 아무 이름이나 지어 넣지 않는다."""
        admin = role_request.administrator_for(self.role_zero)
        self.assertIn(admin["source"],
                      {"tenant_admin", "global_admin", "settings_fallback", "none"})
        if admin["source"] == "none":
            self.assertEqual(admin["name"], "")
        else:
            self.assertTrue(admin["name"])

    def test_administrator_contact_is_not_shipped(self):
        """★ 관리자의 **주소를 싣지 않는다.**

        [실측 2026-09-07] 처음 만들 때는 실었고 `admin@guardianx.com` 이 역할 0
        계정에게 그대로 나갔다. 쓸 일 없는 남의 연락처를 권한 0 계정에게 내주는 것은
        이 절이 막으려는 바로 그 부류다.
        """
        admin = role_request.administrator_for(self.role_zero)
        self.assertNotIn("email", admin)
        text = json.dumps(admin, ensure_ascii=False)
        self.assertNotIn("@", text)

    def test_the_admin_ledger_has_a_door_and_it_is_admin_only(self):
        """★ **함수는 문이 아니다** (D-377 · `verify_dormant.py` 가 실제로 잡았다).

        알림을 대장에 쓰기만 하고 읽을 자리를 안 만들면 `pending_requests()` 는
        아무도 안 부르는 함수가 된다. 그래서 문을 세웠고, 그 문은 **관리자만** 연다.
        """
        client = Client(**NO_CACHE)
        role_request.notify_admin(self.role_zero)

        denied = client.get("/api/v1/access/role-requests", **_bearer(self.role_zero))
        self.assertEqual(denied.status_code, 403)

        allowed = client.get("/api/v1/access/role-requests", **_bearer(self.admin))
        self.assertEqual(allowed.status_code, 200)
        body = json.loads(allowed.content.decode("utf-8"))
        self.assertGreaterEqual(body["count"], 1)
        self.assertIn(self.role_zero.pk, [r["user_id"] for r in body["requests"]])

    def test_message_names_the_administrator(self):
        """화면의 「관리자(이름)」 자리를 **서버가 채운다** (GX-COPY 규칙 1)."""
        named = role_request.message_for({"name": "홍길동"}, has_roles=False)
        self.assertIn("관리자(홍길동)", named)
        unnamed = role_request.message_for({"name": ""}, has_roles=False)
        self.assertIn("관리자에게", unnamed)
        self.assertNotIn("()", unnamed)


# ═══════════════════════════════════════════════════════════════════════════
# 5) 자리 — **캐시보다 바깥, 접근 관문보다 안쪽**
# ═══════════════════════════════════════════════════════════════════════════

class MiddlewareOrderTest(SimpleTestCase):
    """자리를 틀리면 관문이 있어도 캐시가 대신 답한다 (D-341 착시 ⑦)."""

    ROLE_GATE = "common.role_gate.RoleGateMiddleware"
    ACCESS_GATE = "common.access_gate.AccessGateMiddleware"
    CACHE = "common.universal_optimization.UniversalCacheMiddleware"
    JWT_RESTORE = "core.middleware.jwt_user_restore.JWTUserRestoreMiddleware"

    def _order(self):
        from django.conf import settings

        return list(settings.MIDDLEWARE)

    def test_role_gate_is_installed(self):
        self.assertIn(self.ROLE_GATE, self._order())

    def test_role_gate_is_outside_the_response_cache(self):
        order = self._order()
        self.assertLess(order.index(self.ROLE_GATE), order.index(self.CACHE))

    def test_role_gate_is_after_the_access_gate(self):
        """익명은 401, 역할 0 은 403. 순서가 두 문장을 가른다 (D-290)."""
        order = self._order()
        self.assertGreater(order.index(self.ROLE_GATE), order.index(self.ACCESS_GATE))

    def test_role_gate_is_after_the_user_is_restored(self):
        """`request.user` 를 세우는 겹보다 아래여야 한다 — 이 관문은 토큰을 안 푼다."""
        order = self._order()
        self.assertGreater(order.index(self.ROLE_GATE), order.index(self.JWT_RESTORE))
