# -*- coding: utf-8 -*-
"""인증 표면 회귀 시험 — P-W0-18-2 (W0-14 · W0-18 연계).

이 파일이 못박는 것은 셋이다.

  1) **`auth=` 없이 `@path_permission` 만 붙은 라우트가 늘지 않는다.** 지금 24건이고,
     그 24건은 인증 관문을 거치지 않은 채 권한 판정까지 도달한다.
  2) **그 도달을 HTTP 로 재현한다.** Authorization 헤더가 아예 없어도 401 이 아니라
     권한 판정 결과가 나온다 — `auth=` 가 붙은 대조군은 같은 요청에 401 이다.
  3) **해독할 수 없는 Bearer 토큰은 모든 라우트에서 500 이다.** dj-core 의
     `TokenRefreshMiddleware` 가 복구 경로에서 다시 `jwt.decode` 를 부르고 그것을
     감싸지 않았다(§0.4 · 고칠 수 없다). 401 이어야 할 자리다.

★ 이 시험들은 **결함이 있다는 사실을 고정한다**(characterization). 결함이 고쳐지면
  여기가 빨개진다 — 그때가 이 파일을 고칠 때다. 같은 방식을 이미
  `test_api_contract.py::test_token_pair_issues_tokens_that_do_not_work` 이 쓴다.

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105 · D-224)
    skip·xfail·비활성화하지 말 것. 못 고친 것은 `KNOWN_GAPS` 에 사유와 함께 세어 둔다.

실행
    python manage.py test tests.test_auth_surface -v 2
"""

from __future__ import annotations

import jwt as pyjwt
from django.conf import settings
from django.test import Client, TestCase

from tests.no_cache import NO_CACHE

# ═══════════════════════════════════════════════════════════════════════════
# 등록부 — 못 고친 것을 숨기지 않고 센다 (D-224 방식)
# ═══════════════════════════════════════════════════════════════════════════

#: `auth=` 콜백이 없는데 `@path_permission` 은 붙은 라우트 수.
#: 실측 2026-08-25 — 652 라우트 중 auth 없음 143, 그중 @path_permission 부착 **24**.
#: terminals 9 · devices 6 · flight_log 4 · delivery 3 · operational_data 1 · orders 1.
#: 24건 중 공개 라우트로 볼 만한 것은 **0건**이다 (evidence/W0-18/auth_surface.md).
#: P-W0-18-5 판정 대기 — 붙이기로 하면 이 수는 0 이 되어야 한다.
KNOWN_GAPS = {
    "no_auth_with_path_permission": 24,
}

#: 대표 라우트 — 인증 관문이 **없는** 쪽과 **있는** 쪽. 둘을 같은 요청으로 때려 비교한다.
ROUTE_NO_AUTH_CALLBACK = "/api/devices/devices-management"
ROUTE_WITH_AUTH_CALLBACK = "/api/report-template/"


def _gap_routes() -> list[str]:
    """`auth=` 없이 `@path_permission` 만 붙은 라우트 목록.

    정적 grep 이 아니라 **런타임 ninja 레지스트리**를 읽는다 — 동적 등록을 놓치지 않기
    위해서다 (`common/api_contract.py::classify_permission_routes` 와 같은 이유).
    """
    from common.tenant_scope import _iter_ninja_apis, _join

    found: list[str] = []
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    view = getattr(op, "view_func", None)
                    if not getattr(view, "_path_override", None):
                        continue
                    if getattr(op, "auth_callbacks", None):
                        continue
                    methods = ",".join(str(m).upper() for m in (getattr(op, "methods", []) or []))
                    found.append(f"{methods} {_join(mount, prefix, op_path)}")
    return sorted(found)


class AuthSurfaceRegistryTest(TestCase):

    def test_gap_routes_have_not_grown(self):
        """인증 관문 없는 권한 라우트가 **늘지 않았는가.**

        늘었다면 새 라우트가 `@path_permission` 만 붙이고 `auth=` 를 빠뜨린 것이다.
        줄었다면 P-W0-18-5 가 적용된 것이고 `KNOWN_GAPS` 를 낮춰야 한다.
        """
        gap = _gap_routes()
        self.assertLessEqual(
            len(gap),
            KNOWN_GAPS["no_auth_with_path_permission"],
            "인증 콜백 없이 권한만 보는 라우트가 늘었다:\n  " + "\n  ".join(gap),
        )


class UnauthenticatedReachTest(TestCase):
    """헤더가 아예 없을 때 무엇이 다른가 — 대조군과 나란히 본다."""

    def setUp(self):
        # 캐시 처리: 우회 — X-No-Cache (D-341).
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def test_auth_callback_route_rejects_anonymous(self):
        """`auth=` 가 붙은 라우트는 **401** 이다. 이것이 정상이다."""
        resp = self.client.get(ROUTE_WITH_AUTH_CALLBACK)
        self.assertEqual(resp.status_code, 401)

    def test_no_auth_callback_route_reaches_permission_check(self):
        """`auth=` 가 없는 라우트는 401 이 아니라 **권한 판정까지 간다.**

        인증을 한 번도 묻지 않았는데 "권한이 없습니다"가 나온다 — 관문이 라우트마다
        있거나 없다는 뜻이다. 이 단언이 깨지면(=401 이 나오면) 관문이 붙은 것이고,
        `KNOWN_GAPS` 와 evidence/W0-18/auth_surface.md 를 같이 고쳐야 한다.
        """
        resp = self.client.get(ROUTE_NO_AUTH_CALLBACK)
        self.assertNotEqual(
            resp.status_code, 401,
            "인증 관문이 생겼다 — 좋은 소식이다. KNOWN_GAPS 를 낮추고 이 시험을 고쳐라",
        )
        self.assertEqual(resp.status_code, 200, "권한 판정 결과가 200 본문으로 나온다")
        self.assertIs(resp.json().get("success"), False)


class MalformedBearerTest(TestCase):
    """해독 불가 토큰 = 500. 라우트가 아니라 **미들웨어**의 문제다.

    dj-core `core/middleware/refresh_token.py:204` — `except` 블록이 복구를 시도하며
    `jwt.decode` 를 **다시** 부르는데 그것을 감싸지 않았다. 첫 실패가 "해독 불가"면
    복구도 같은 자리에서 터지고 예외가 미들웨어 밖으로 나간다.
    §0.4 금지구역(dj-core)이라 그 파일은 고칠 수 없다 (D-207).

    ★ 왜 지금 중요한가: 서명키 교체(D-251 자격증명 회전) 뒤에는 **구 토큰을 든 모든
      클라이언트가 401 이 아니라 500 을 받는다.** 프론트의 재인증 경로는 401 을 본다.
    """

    def setUp(self):
        # 캐시 처리: 우회 — X-No-Cache (D-341).
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def _get(self, path: str, token: str):
        return self.client.get(path, HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_undecodable_token_yields_500_everywhere(self):
        """해독 자체가 안 되는 토큰 — 관문 유무와 **무관하게** 500."""
        for path in (ROUTE_NO_AUTH_CALLBACK, ROUTE_WITH_AUTH_CALLBACK):
            for label, token in (
                ("점이 없다", "not-a-token"),
                ("점만 있다", "aaa.bbb.ccc"),
                ("다른 키로 서명", self._foreign_signature()),
            ):
                with self.subTest(path=path, token=label):
                    self.assertEqual(
                        self._get(path, token).status_code, 500,
                        "500 이 아니게 됐다 — dj-core 가 고쳐졌거나 저장소 쪽에서 감쌌다. "
                        "그렇다면 이 시험과 evidence/W0-18/auth_surface.md 를 고쳐라",
                    )

    def test_correctly_signed_expired_token_is_handled(self):
        """대조 — **실키로 서명된** 만료 토큰은 500 이 아니다.

        즉 500 의 원인은 "만료"가 아니라 **"해독 실패"** 다. 이 구분이 없으면
        일상적인 만료까지 500 이라고 잘못 보고하게 된다.
        """
        token = self._sign({"exp": 1})
        self.assertEqual(self._get(ROUTE_WITH_AUTH_CALLBACK, token).status_code, 401)
        self.assertEqual(self._get(ROUTE_NO_AUTH_CALLBACK, token).status_code, 200)

    # ── 도구 ──────────────────────────────────────────────────────────────

    def _sign(self, extra: dict) -> str:
        payload = {"user_id": 1, "jti": "x", "session_id": "y", "token_type": "access"}
        payload.update(extra)
        return pyjwt.encode(
            payload,
            settings.NINJA_JWT["SIGNING_KEY"],
            algorithm=settings.NINJA_JWT.get("ALGORITHM", "HS256"),
        )

    def _foreign_signature(self) -> str:
        """형식은 완전히 정상이고 **서명만 다른 키**인 토큰 — 키 교체 후의 구 토큰이 이 모양이다."""
        return pyjwt.encode(
            {"user_id": 1, "jti": "x", "session_id": "y",
             "token_type": "access", "exp": 4102444800},
            "not-the-signing-key-only-for-this-test",
            algorithm="HS256",
        )
