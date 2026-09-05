# -*- coding: utf-8 -*-
"""API 계약 회귀 시험 — W0-18 (D-248 · D-212).

이 파일이 못박는 것은 셋이다.

  1) **권한거부의 상태코드**  플래그 ON 이면 실제 4xx 로 나가고, OFF 이면 기존 200 이
     한 글자도 바뀌지 않는다(하위호환). 되돌림이 실제로 되는지를 시험이 증명한다.
  2) **`/api/token/pair`**    200 으로 토큰을 주지만 그 토큰은 `CustomJWTAuth` 라우트에서
     401 이다. "발급 성공 → 다음 호출 401" 이 실제 동작이고, 연동 문서는 그것을 적어야 한다.
  3) **`/api/v1/auth/delete-session`**  body·query 어느 형태로도 호출할 수 없다(전부 422).

절대 금지 (AGENT_LOOP 절대금지 #4 · D-105 · D-224)
    이 파일의 시험을 skip·xfail·비활성화하지 말 것. 아직 못 고친 결함은
    `KNOWN_GAPS` 등록부에 **사유와 함께** 적고 증가금지 시험으로 묶는다.
    조용히 건너뛰면 초록불이 실제 커버리지보다 커 보인다.

실행
    python manage.py test tests.test_api_contract -v 2
"""

from __future__ import annotations

import json

from django.apps import apps
from django.http import JsonResponse
from django.test import (
    Client, RequestFactory, TestCase, override_settings,
)

from tests.no_cache import NO_CACHE

from common.api_contract import (
    KIND_PROMOTABLE,
    KIND_RAISES,
    KIND_SWALLOWED,
    classify_permission_routes,
    denial_status,
)

# ═══════════════════════════════════════════════════════════════════════════
# 대표 라우트 — 세 부류에서 하나씩
# ═══════════════════════════════════════════════════════════════════════════

#: A — `response=` 선언이 없다. 거부가 200 + 본문으로 나간다.
ROUTE_NO_SCHEMA = "/api/devices/devices-management"

#: B — `response=List[…]`. 거부 dict 를 pydantic 이 거절해 예외가 된다.
ROUTE_LIST_SCHEMA = "/api/report-template/"

#: C 였던 것 — `response=<단일 스키마>` 선언 때문에 거부가 `{}` 로 소멸하던 라우트.
#: P-W0-18-1 A 안 적용으로 선언을 뗐고, 이제 A 부류로서 승격된다. 부류는 0 이 됐다.
ROUTE_FORMERLY_SWALLOWED = "/api/report-template/1"


# ═══════════════════════════════════════════════════════════════════════════
# 등록부 — 아직 못 고친 것을 숨기지 않고 센다 (D-224 방식)
# ═══════════════════════════════════════════════════════════════════════════

#: 거부가 `{}` 로 소멸하는 라우트 수. 응답 계층에서 복원할 수 없는 부류다.
#: 2026-08-25 · P-W0-18-1 A 안 적용 — report_template 4 · checklist_setting 4 의
#: `response=<단일 스키마>` 선언을 뗐다. **8 → 0.** 등록부는 지우지 않고 0 으로 남긴다:
#: 이 수가 다시 오르면 새 라우트가 같은 함정에 빠진 것이고, 아래 증가금지 시험이 잡는다.
KNOWN_GAPS = {
    KIND_SWALLOWED: 0,
}

#: 실측 분포 (evidence/W0-18/backward_compat_impact.md §1-1). 라우트가 늘거나 선언이
#: 바뀌면 이 수가 움직인다 — 움직이면 증거 문서도 같이 고쳐야 한다는 신호다.
EXPECTED_DISTRIBUTION = {
    KIND_PROMOTABLE: 289,   # 281 + P-W0-18-1 로 넘어온 8
    KIND_RAISES: 7,
    KIND_SWALLOWED: 0,      # 8 → 0
}


def _bearer(user) -> dict[str, str]:
    """이 사용자로 인증된 요청 헤더.

    dj-core 는 토큰의 `jti` 를 사용자에 저장된 세션값과 대조한다. 그래서 로그인 경로가
    하는 것과 같은 세 단계를 그대로 한다 (tests/test_tenant_isolation.py 와 같은 이유).
    """
    import uuid

    import jwt
    from django.conf import settings
    from ninja_jwt.tokens import RefreshToken

    session_id = str(uuid.uuid4())
    refresh = RefreshToken.for_user(user)
    refresh["session_id"] = session_id
    access = str(refresh.access_token)
    decoded = jwt.decode(
        access,
        settings.NINJA_JWT["SIGNING_KEY"],
        algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")],
    )
    setter = getattr(user, "set_encrypted_session_token", None)
    if setter is not None:
        setter(session_id, decoded.get("jti"))
        user.save()
    return {"HTTP_AUTHORIZATION": f"Bearer {access}"}


class _DeniedUserMixin:
    """권한이 **없는** 사용자 하나.

    역할은 주되 `RoleMenu`/`RoleTab` 을 주지 않는다 — `_check_path_permission` 이
    바로 그 조합에서 False 를 낸다. 역할을 아예 주지 않아도 False 지만, 그러면
    "역할이 없어서"와 "권한이 없어서"가 구별되지 않는다. 이 시험이 묻는 것은 후자다.
    """

    PASSWORD = "test-only-not-a-secret"

    @classmethod
    def _make_denied_user(cls, username: str):
        CoreUser = apps.get_model("user", "CoreUser")
        UserGroup = apps.get_model("user", "UserGroup")
        Role = apps.get_model("role", "Role")

        group = UserGroup.objects.create(name=f"contract-{username}")
        user = CoreUser.objects.create_user(
            username=username,
            password=cls.PASSWORD,
            is_active=True,
            email=f"{username}@test.invalid",
        )
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": group}
        )
        role = Role.objects.create(role_name=f"contract-{username}", code=f"c_{username}")
        user.roles.set([role])
        return user


# ═══════════════════════════════════════════════════════════════════════════
# 1) 판정 함수 — 무엇을 승격하고 무엇을 건드리지 않는가
# ═══════════════════════════════════════════════════════════════════════════

class DenialDiscriminatorTest(TestCase):
    """판정을 좁게 잡았다는 것을 못박는다. 넓히면 배송·주문 본문이 걸린다."""

    def test_permission_denial_shape_is_promoted(self):
        payload = {"success": False, "message": {"en": "Permission denied."}, "status_code": 403}
        self.assertEqual(denial_status(payload), 403)

    def test_domain_status_code_is_not_promoted(self):
        """배송 진행단계(0~5) · 도메인 상태문자열은 HTTP 상태가 아니다."""
        for code in (0, 1, 5, 200, 201, "success", "error", None):
            with self.subTest(code=code):
                self.assertIsNone(denial_status({"success": False, "status_code": code}))

    def test_success_true_is_not_promoted(self):
        self.assertIsNone(denial_status({"success": True, "status_code": 403}))

    def test_missing_success_key_is_not_promoted(self):
        """`orders/views/order_views.py:1394` 처럼 `status: "error"` 만 쓰는 본문."""
        self.assertIsNone(denial_status({"status": "error", "status_code": 400}))

    def test_true_does_not_pass_as_status_one(self):
        """bool 은 int 의 서브클래스다. True 가 새어들어오면 안 된다."""
        self.assertIsNone(denial_status({"success": False, "status_code": True}))

    def test_non_dict_is_not_promoted(self):
        for payload in (None, [], "403", 403):
            with self.subTest(payload=payload):
                self.assertIsNone(denial_status(payload))


# ═══════════════════════════════════════════════════════════════════════════
# 2) 권한거부의 상태코드 — 플래그 ON / OFF
# ═══════════════════════════════════════════════════════════════════════════

class PermissionDeniedStatusTest(_DeniedUserMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = cls._make_denied_user("contract_denied")

    def setUp(self):
        # 캐시 처리: 우회 — X-No-Cache (D-341 착시 ⑦).
        # 관문·계약을 재는 시험이 캐시를 재면 안 된다.
        self.client = Client(**NO_CACHE)
        self.headers = _bearer(self.user)

    # ── 플래그 OFF — 기존 동작이 한 글자도 바뀌지 않는다 (하위호환) ──────────

    @override_settings(API_CONTRACT_PROMOTE_ERROR_STATUS=False)
    def test_flag_off_keeps_legacy_200(self):
        resp = self.client.get(ROUTE_NO_SCHEMA, **self.headers)
        self.assertEqual(resp.status_code, 200, "플래그 OFF 에서 상태가 바뀌면 되돌림이 불가능하다")
        body = json.loads(resp.content)
        self.assertIs(body.get("success"), False)
        self.assertEqual(body.get("status_code"), 403)

    # ── 플래그 ON — A 부류: 200 → 403 ──────────────────────────────────────

    @override_settings(API_CONTRACT_PROMOTE_ERROR_STATUS=True)
    def test_flag_on_promotes_no_schema_route(self):
        resp = self.client.get(ROUTE_NO_SCHEMA, **self.headers)
        self.assertEqual(resp.status_code, 403)

    @override_settings(API_CONTRACT_PROMOTE_ERROR_STATUS=True)
    def test_promotion_preserves_body(self):
        """상태줄만 고친다. 기존 클라이언트가 읽던 `success`·`message` 는 그대로 있어야 한다."""
        resp = self.client.get(ROUTE_NO_SCHEMA, **self.headers)
        body = json.loads(resp.content)
        self.assertIs(body.get("success"), False)
        self.assertEqual(body.get("status_code"), 403)
        self.assertIn("message", body)

    # ── 플래그 ON — B 부류: 500(예외) → 403 ────────────────────────────────

    @override_settings(API_CONTRACT_PROMOTE_ERROR_STATUS=True)
    def test_flag_on_promotes_list_schema_route(self):
        """`response=List[…]` 라우트는 거부 dict 로 **예외가 난다.**

        `process_exception` 이 그 예외의 `input` 에서 거부 dict 를 되찾는다.
        이 경로가 없으면 delivery 5건은 §0.4 라 손댈 방법이 없다.
        """
        resp = self.client.get(ROUTE_LIST_SCHEMA, **self.headers)
        self.assertEqual(resp.status_code, 403)
        self.assertIs(json.loads(resp.content).get("success"), False)

    @override_settings(API_CONTRACT_PROMOTE_ERROR_STATUS=False)
    def test_flag_off_list_schema_route_still_raises(self):
        """OFF 에서는 아무것도 하지 않는다 — 예외가 그대로 흐른다.

        `raise_request_exception=False` 로 Django 가 500 을 만들게 둔다.
        """
        client = Client(raise_request_exception=False, **NO_CACHE)
        resp = client.get(ROUTE_LIST_SCHEMA, **self.headers)
        self.assertEqual(resp.status_code, 500)

    # ── 플래그 ON — C 였던 부류: `{}` 소멸 → 403 (P-W0-18-1) ──────────────

    @override_settings(API_CONTRACT_PROMOTE_ERROR_STATUS=True)
    def test_flag_on_promotes_formerly_swallowed_route(self):
        """선언을 뗀 뒤 **거부가 실제로 보이는가.**

        수를 세는 시험(`test_swallowed_routes_have_not_grown`)만으로는 부족하다 —
        분류가 맞아도 응답이 틀릴 수 있다. 여기서는 HTTP 를 실제로 때린다.
        선언이 남아 있던 동안 이 라우트는 **200 + `{}`** 를 돌려줬다.
        """
        resp = self.client.get(ROUTE_FORMERLY_SWALLOWED, **self.headers)
        self.assertEqual(resp.status_code, 403)
        body = json.loads(resp.content)
        self.assertIs(body.get("success"), False, "거부 본문이 다시 소멸했다")
        self.assertEqual(body.get("status_code"), 403)

    @override_settings(API_CONTRACT_PROMOTE_ERROR_STATUS=False)
    def test_flag_off_formerly_swallowed_route_keeps_200(self):
        """OFF 되돌림도 그대로 성립하는가.

        선언 제거는 되돌림 경로를 건드리지 않아야 한다 — 플래그 하나로 전부 원복된다는
        하위호환 약속이 이 라우트에서도 유효하다는 뜻이다.
        단, 본문은 **더 이상 `{}` 가 아니다.** 거부 dict 가 그대로 실려 나간다 —
        선언을 떼서 얻은 것이 바로 이것이고, 플래그로 되돌아가지 않는 유일한 변화다.
        """
        resp = self.client.get(ROUTE_FORMERLY_SWALLOWED, **self.headers)
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content)
        self.assertIs(body.get("success"), False)
        self.assertEqual(body.get("status_code"), 403)

    # ── 정상 응답은 건드리지 않는다 ───────────────────────────────────────

    @override_settings(API_CONTRACT_PROMOTE_ERROR_STATUS=True)
    def test_unauthenticated_401_is_untouched(self):
        resp = self.client.get(ROUTE_FORMERLY_SWALLOWED)
        self.assertEqual(resp.status_code, 401)


# ═══════════════════════════════════════════════════════════════════════════
# 3) 엔드포인트 계약 — 문서가 적어야 할 실제 동작
# ═══════════════════════════════════════════════════════════════════════════

class AuthEndpointContractTest(_DeniedUserMixin, TestCase):
    """연동 문서의 기재를 시험으로 못박는다 (W0-18 dod ③④).

    문서와 동작이 갈라지면 여기가 먼저 빨개진다.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = cls._make_denied_user("contract_auth")

    def setUp(self):
        self.client = Client()

    def test_token_pair_is_gone(self):
        """`/api/token/pair` 는 **없다.** 404 여야 한다 (D-411 · 승인 세종 2026-09-19).

        ★ **이것은 시험을 고쳐 초록을 만든 것이 아니다.** 앞판의 단언
          (「200 으로 발급하고 그 토큰은 401 이다」)은 **그날의 사실이었고 옳았다.**
          바뀐 것은 시험이 아니라 **계약**이다: 세종이 그 문의 제거를 승인했고,
          결정 대장에 사유와 함께 남았다(D-411). 계약이 바뀌면 시험도 바뀐다 —
          바뀌지 않는 것은 **계약을 시험이 정하지 않는다**는 것이다(D-327 · D-300).

        ★ 왜 **부작위**를 시험하나 — 없앤 것은 다시 생긴다. 특히 이 문은
          `core.urls`(dj-core · 금지구역) 안에 그대로 살아 있고, 우리는 `config/urls.py`
          에서 **순서로** 가리고 있을 뿐이다. 그 줄이 아래로 한 칸만 내려가면
          문은 소리 없이 다시 열린다. 그 순간을 사람이 아니라 이 시험이 본다.

        ★ **401 이 아니라 404 여야 한다.** 401 이면 연동 담당자가 「자격증명이
          모자라다」로 읽고 계정을 고치려 든다 — 없는 것은 없다고 말한다(D-290).
        """
        resp = self.client.post(
            "/api/token/pair",
            data=json.dumps({"username": self.user.username, "password": self.PASSWORD}),
            content_type="application/json",
        )
        self.assertEqual(
            resp.status_code, 404,
            "token/pair 가 다시 열렸다 — config/urls.py 의 차단 줄이 "
            "core.urls include 아래로 내려갔는지 보라 (D-411)")

        self.user.refresh_from_db()
        self.assertFalse(self.user.token, "닫힌 문이 세션을 세웠다 — 가려진 것이 아니다")

    def test_login_is_the_working_credential_endpoint(self):
        """실경로는 `/api/v1/auth/login` 이다. 라우트가 살아 있는지만 못박는다."""
        resp = self.client.post(
            "/api/v1/auth/login",
            data=json.dumps({"username": self.user.username, "password": self.PASSWORD}),
            content_type="application/json",
        )
        self.assertNotEqual(resp.status_code, 404, "실경로가 사라졌다 — 연동 문서를 고쳐라")
        self.assertEqual(resp.status_code, 200)

    def test_delete_session_is_not_callable_in_any_shape(self):
        """`data: dict` 를 ninja 가 **쿼리 파라미터**로 잡는다. 그래서 부를 방법이 없다.

        핸들러는 §0.4 안이라 고칠 수 없다. 문서에 "현재 호출 불가"라고 적어야 하고,
        이 시험이 그 기재의 근거다. 고쳐지면 여기가 빨개지고 문서도 같이 고친다.
        """
        headers = _bearer(self.user)
        shapes = [
            ("body", {"data": json.dumps({"data": "x"}), "path": "/api/v1/auth/delete-session"}),
            ("query 문자열", {"data": None, "path": "/api/v1/auth/delete-session?data=x"}),
            (
                "query JSON",
                {
                    "data": None,
                    "path": "/api/v1/auth/delete-session?data=%7B%22session_id%22%3A%22x%22%7D",
                },
            ),
            ("query 평면", {"data": None, "path": "/api/v1/auth/delete-session?session_id=x"}),
        ]
        for label, shape in shapes:
            with self.subTest(shape=label):
                resp = self.client.post(
                    shape["path"],
                    data=shape["data"],
                    content_type="application/json",
                    **headers,
                )
                self.assertEqual(
                    resp.status_code, 422,
                    f"{label} 로 호출이 통했다 — 연동 문서를 고쳐라",
                )


# ═══════════════════════════════════════════════════════════════════════════
# 4) 커버리지 등록부 — 못 고친 것을 숨기지 않는다
# ═══════════════════════════════════════════════════════════════════════════

class MiddlewareOrderTest(TestCase):
    """배치가 곧 기능이다. 순서가 바뀌면 승격이 **조용히** 죽는다.

    `UniversalCacheMiddleware` 는 캐시 적중 시 저장된 본문으로 `JsonResponse(...)` 를
    새로 만든다 — **상태코드를 버리고 늘 200** 이다(`universal_optimization.py:872`).
    승격 미들웨어가 그보다 안쪽에 있으면 적중한 요청에서는 호출조차 되지 않는다.
    그리고 그때 시험은 전부 초록이다(캐시가 비어 있으므로) — 운영에서만 틀린다.
    """

    CONTRACT = "common.api_contract.ApiContractStatusMiddleware"
    GZIP = "django.middleware.gzip.GZipMiddleware"
    CACHE = "common.universal_optimization.UniversalCacheMiddleware"

    def test_contract_middleware_is_installed(self):
        from django.conf import settings

        self.assertIn(self.CONTRACT, settings.MIDDLEWARE)

    def test_contract_middleware_sits_between_gzip_and_cache(self):
        from django.conf import settings

        order = list(settings.MIDDLEWARE)
        contract, gzip_at, cache_at = (order.index(m) for m in (self.CONTRACT, self.GZIP, self.CACHE))
        self.assertGreater(
            contract, gzip_at,
            "GZip 보다 바깥이면 압축된 본문을 JSON 으로 읽을 수 없다",
        )
        self.assertLess(
            contract, cache_at,
            "UniversalCache 보다 안쪽이면 캐시 적중한 요청에서 승격이 통째로 사라진다",
        )


class ContractCoverageTest(TestCase):

    def test_distribution_matches_evidence(self):
        """증거 문서의 수와 실제 레지스트리의 수가 같은가.

        라우트가 늘거나 `response=` 선언이 바뀌면 여기가 먼저 빨개진다 —
        그때 `evidence/W0-18/backward_compat_impact.md` §1-1 도 같이 고친다.
        """
        actual = {k: len(v) for k, v in classify_permission_routes().items()}
        self.assertEqual(actual, EXPECTED_DISTRIBUTION)

    def test_swallowed_routes_have_not_grown(self):
        """거부가 `{}` 로 소멸하는 라우트가 **늘지 않았는가.**

        P-W0-18-1 적용으로 지금은 **0** 이다. 늘었다면 새 라우트가 단일 스키마를
        선언하면서 같은 함정에 다시 빠진 것이다 — 그 라우트 이름이 실패 메시지에 찍힌다.
        """
        swallowed = classify_permission_routes()[KIND_SWALLOWED]
        self.assertLessEqual(
            len(swallowed),
            KNOWN_GAPS[KIND_SWALLOWED],
            "권한거부가 조용히 사라지는 라우트가 늘었다:\n  " + "\n  ".join(swallowed),
        )


class ScopedPromotionForContractSurfaceTest(TestCase):
    """D-349 ③ — **F-05 진입면은 래칫에서 제외한다.** 전역 플래그가 꺼져 있어도 승격한다.

    캐시 처리: 해당 없음 — 미들웨어를 직접 호출한다 (스택을 타지 않는다).

    왜 경로로 좁혔나
        전역 승격은 무증상 실패 후보 21곳(대부분 delivery 화면)을 건드린다(W0-18 §2-2).
        한 번에 뒤집으면 **무엇이 깨졌는지 모르는 채로 초록이 된다.**
        그러나 계약 상대가 읽는 면은 다르다 — 거기서 200 봉투에 담긴 실패는
        **에스비 App 이 성공으로 읽는다. 계약 사고다.**

    ★ 출생 표본 (D-310): 2026-09-08 에 18 을 11 로 만든 그 본문 그대로.
    """

    #: 그날 익명 호출이 받은 본문. HTTP 는 200 이었다.
    DENIAL_BODY = {"success": False, "message": {"ko": "권한이 거부되었습니다."},
                   "status_code": 403}

    def _promote(self, path):
        from common.api_contract import ApiContractStatusMiddleware

        def get_response(request):
            return JsonResponse(self.DENIAL_BODY, status=200)

        middleware = ApiContractStatusMiddleware(get_response)
        request = RequestFactory().get(path)
        return middleware(request)

    def test_flag_is_off_by_default(self):
        """전역 플래그를 켜서 통과하는 시험이 되면 이 시험은 아무것도 증명하지 않는다."""
        from common.api_contract import promotion_enabled

        self.assertFalse(promotion_enabled(), "전역 승격이 켜져 있다 — 이 시험의 전제가 깨졌다")

    def test_contract_surface_is_promoted_without_the_global_flag(self):
        resp = self._promote("/api/dsm/events")
        self.assertEqual(
            resp.status_code, 403,
            "★ F-05 진입면이 200 봉투에 403 을 담아 보낸다 — 에스비 App 이 성공으로 읽는다",
        )

    def test_other_surfaces_stay_on_the_ratchet(self):
        """음성 대조 — 전부 승격되면 그건 「좁혔다」가 아니라 「전역을 켰다」이다."""
        resp = self._promote("/api/terminals/terminals")
        self.assertEqual(resp.status_code, 200,
                         "래칫 밖의 면까지 승격됐다 — 범위 판정 없이 넓힌 것이다")

    def test_body_is_not_rewritten(self):
        """상태줄만 고친다. 기존 클라이언트가 읽던 success·message 가 사라지면 안 된다."""
        resp = self._promote("/api/dsm/events")
        body = json.loads(resp.content.decode("utf-8"))
        self.assertIs(body.get("success"), False)
        self.assertIn("message", body)

    # ── SEC-11a · 부르는 자리 접두 셋 (2026-09-05 · 차선 S) ──────────────────
    #   화면 캡처 24장이 실제로 부른 접두 ∩ 봉투가 갈리는 자리(authz_envelope).
    #   화면이 열리는 순간 이 셋이 다 불린다 — 여기서 거부가 200 으로 나가면
    #   **모든 화면이 그 거부를 삼킨다.**
    #   ★ [2026-09-05 TC] 접두 둘을 더했다 — **남은 마지막 7건**이 이 아래 있다.
    #     flight-log 4 · departments 3. 켜면 부르는 자리의 `authz_envelope` 가 0 이다.
    CALLED_PREFIX_SAMPLES = (
        ("/api/advanced-table/select-data", "화면 24장 전부가 부르는 테마·표 데이터"),
        ("/api/config-management/list-optimized", "화면 24장 전부가 부르는 설정"),
        ("/api/user-groups/gen-schema", "권한 스키마 — 화면 호출 51건"),
        ("/api/flight-log/flight-log", "비행로그 목록 — 화면이 부르는 4건 중 하나"),
        ("/api/flight-log/detail/1", "비행로그 상세"),
        ("/api/departments/1", "부서 수정 — 뷰는 dj-core(§0.4)이고 밖에서 승격한다"),
    )

    def test_called_surfaces_are_promoted(self):
        for path, why in self.CALLED_PREFIX_SAMPLES:
            with self.subTest(path=path):
                self.assertEqual(
                    self._promote(path).status_code, 403,
                    "부르는 자리가 200 봉투에 403 을 담는다 (%s)" % why,
                )

    def test_collection_route_without_trailing_slash_is_promoted(self):
        """★ 출생 표본 [실측 2026-09-05] — 접두 셋을 켰는데 **한 건이 남았다.**

        기대 24건 중 갚힌 것은 23건이었고, 남은 하나가 `POST /api/user-groups` —
        접두 `/api/user-groups/` 로는 `startswith` 가 걸리지 않는 **모음 라우트**다.
        목록·생성처럼 가장 많이 불리는 자리가 정확히 그 모양이라, 이 한 줄이 없으면
        접두를 넣을 때마다 그 자리가 조용히 빠진다.
        """
        self.assertEqual(
            self._promote("/api/user-groups").status_code, 403,
            "모음 라우트(끝의 / 없음)가 승격에서 빠졌다 — 접두마다 이 자리가 샌다",
        )
        # ★ [2026-09-05 TC] 같은 모양이 이번 접두에도 있다 — `POST /api/departments`.
        #   정본 7건 중 하나이고, 이 줄이 없으면 접두를 켜고도 그 한 건이 남는다.
        self.assertEqual(
            self._promote("/api/departments").status_code, 403,
            "`POST /api/departments`(모음 라우트)가 승격에서 빠졌다 — 정본이 이름으로 "
            "적어 둔 7건 중 하나다",
        )

    def test_a_different_prefix_that_only_looks_like_departments_is_not_promoted(self):
        """음성 대조 [2026-09-05 TC] — `/api/v1/auth/departments` 는 **다른 문**이다.

        접두 `/api/departments/` 는 `startswith` 로도 모음 규칙으로도 저 경로에
        걸리지 않는다. 걸린다면 그것은 우리가 재지 않은 자리까지 상태줄을 바꾼 것이고,
        그 자리는 로그인 직후 화면이 부르는 자리다.
        """
        self.assertEqual(
            self._promote("/api/v1/auth/departments").status_code, 200,
            "부서 접두가 인증 면의 다른 경로까지 끌고 왔다",
        )

    def test_lookalike_prefix_is_not_promoted(self):
        """음성 대조 — 이름이 겹쳐 보이는 다른 접두까지 끌려오면 좁힌 것이 아니다."""
        self.assertEqual(
            self._promote("/api/user-groups-archive").status_code, 200,
            "접두가 아닌 자리까지 승격됐다",
        )

    def test_forbidden_zone_prefixes_stay_out(self):
        """§0.4 · SEC-11b — 손 밖의 자리는 우리가 승격하지 않는다.

        delivery·terminals·orders 는 금지구역이고 devices·handover 는 화면이
        한 번도 부르지 않는다. 승격은 **인수자 판단**이다(P-35).
        """
        for path in ("/api/delivery/orders", "/api/terminals/terminals",
                     "/api/orders/list", "/api/devices/list", "/api/handover/list"):
            with self.subTest(path=path):
                self.assertEqual(
                    self._promote(path).status_code, 200,
                    "손 밖(SEC-11b)의 자리를 우리가 승격했다 — 인수 자산의 계약 동작이 바뀐다",
                )

    def test_scope_is_declared_not_guessed(self):
        from django.conf import settings

        from common.api_contract import promotion_scope

        self.assertEqual(tuple(settings.API_CONTRACT_PROMOTE_PATHS), promotion_scope())
        self.assertGreater(len(promotion_scope()), 0,
                           "승격 경로가 비었다 — 계약 면이 래칫으로 되돌아갔다")
