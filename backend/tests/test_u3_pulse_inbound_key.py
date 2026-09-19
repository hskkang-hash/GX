# -*- coding: utf-8 -*-
"""`GET /api/dsm/cameras/pulse` 를 **들어오는 키**에게 연다 (2026-09-19 · 턴 W · U3).

두 턴을 떠다니던 자리다. 조율자가 세 번째로 넘겼고, 이 턴에 **답을 낸다: 연다.**

왜 여는가 — 「상속했으니 열렸겠거니」가 아니다
---------------------------------------------
`JwtOrWallToken` 이 `JwtOrInboundKey` 를 상속해도 `inbound_key` 는 기본 거짓이다.
그 **기본값이 거절**인 규약은 옳으므로 **안 바꿨다**(D-335 ③⑤ · D-300 부작위).
바꾼 것은 이 라우트의 선언 한 줄이다.

여는 사유는 **범위가 이미 이 경로를 가리키고 있었다**는 것이다 [실측 2026-09-19]:

    kernels/k5_trust/key_scopes.py
      · SCOPE_PULSE_READ = "pulse:read" 가 ALLOWED_SCOPES 에 있다
        → 운영자가 키에 **줄 수 있다** (발급 문이 422 를 안 낸다)
      · PATH_SCOPES 에 ("/api/dsm/cameras/pulse", SCOPE_PULSE_READ) 가 있다

그런데 라우트가 선언을 안 해서 키는 **범위 판정에 닿기도 전에 401** 이었다.
즉 「줄 수는 있는데 아무 데도 못 쓰는 범위」였다 — 줄 수 있다고 적어 놓고 쓰면
막는 것은 없는 기능에 손잡이를 그린 것과 같다(D-284). 여는 쪽이 **이미 내려진
판정을 집행하는 것**이고, 안 여는 쪽이 새 판정이다.

⚠ **여는 것이 넓히는 것이 아니다** — 이 시험의 중심이 그것이다.
  기본 범위는 `DEFAULT_SCOPES = ("events:read",)` 이므로 **이미 나간 키는 그대로
  403** 이다. 늘어나는 것은 「운영자가 `pulse:read` 를 **일부러** 준 키」 하나뿐이다.
  `test_a_default_scoped_key_is_still_denied` 가 그 문장을 지킨다 — 이 시험이
  빨개지는 날은 우리가 모든 키에게 재난 정보를 연 날이다.

★ **분모를 함께 둔다** (`TurnVKeyScopeOverHttpTest` 와 같은 규율): 막는 것만 재면
  그 초록은 「막았다」가 아니라 「문이 죽었다」일 수 있다. 그래서 200·403·401 을
  **같은 문에서** 나란히 잰다.

캐시 처리: 우회 — `NO_CACHE` (`X-No-Cache` · D-341 착시 ⑦).
같은 경로를 **자격만 바꿔** 잇달아 두드린다(`pulse:read` 키 200 · `events:read` 키
403 · 키 없음 401 · 평문 401). **적중 본문은 언제나 200 이므로**(D-412) 캐시를 타면
**403 이어야 할 자리가 200 으로 보인다** — 이 시험은 문이 열린 폭을 재는 것이라
그 착시가 바로 재려던 값을 지운다.
"""
from __future__ import annotations

from django.test import Client, override_settings

from tests.test_u56_turn_u_admin_surfaces import DsmFixture

PULSE = "/api/dsm/cameras/pulse"
NO_CACHE = {"HTTP_CACHE_CONTROL": "no-store"}


@override_settings(INBOUND_API_KEY_REQUIRE_HTTPS=False)
class PulseInboundKeyTest(DsmFixture):
    """세 갈래를 **같은 문**에서 잰다: 200(범위 있음) · 403(범위 없음) · 401(키 아님)."""

    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)
        self._clear_thread_request()

    def tearDown(self):
        self._clear_thread_request()
        super().tearDown()

    def _clear_thread_request(self):
        """스레드에 남은 요청을 비운다 — 남아 있으면 `objects` 가 그 요청의 group 으로
        조용히 좁혀지고, 그러면 이 시험이 **우리 문지기가 아니라 오염**으로 초록이 된다.
        """
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

    def _key(self, name: str, scopes: str):
        """키를 하나 발급하고 범위를 준다. **비밀은 돌려받는 그 한 번뿐이다.**"""
        from kernels.k5_trust import issue_key, set_key_scopes

        issued = issue_key(scope=self.scope_a, name=name)
        set_key_scopes(scope=self.scope_a, key_id=issued.view.key_id, scopes=scopes)
        return issued

    def _get(self, secret: str | None):
        headers = {} if secret is None else {"HTTP_X_API_KEY": secret}
        return self.client.get(PULSE, **{**NO_CACHE, **headers})

    # ── ① 범위를 **일부러 받은** 키는 지나간다 ──────────────────────────
    def test_a_key_with_pulse_read_gets_200(self):
        issued = self._key("u3-pulse-yes", "pulse:read")
        resp = self._get(issued.secret)
        self.assertEqual(200, resp.status_code,
                         "pulse:read 를 가진 키가 못 들어왔다 — 문이 죽었다: %r"
                         % resp.content[:200])
        #: 문이 **살아 있다**는 것까지 본다. 200 만으로는 빈 껍데기와 구별이 안 된다.
        body = resp.json()
        self.assertIn("counts", body)
        self.assertIn("cameras", body)

    # ── ② 기본 범위만 가진 키는 **그대로 막힌다** (넓히지 않았다) ───────
    def test_a_default_scoped_key_is_still_denied(self):
        """★★ 이 시험이 빨개지는 날은 **모든 키에게 재난 정보를 연 날**이다.

        `DEFAULT_SCOPES` 가 `("events:read",)` 이므로 이미 나간 키는 전부 이 모양이다.
        401 이 아니라 **403** 이어야 한다 — 인증은 성했고 권한이 없다(다른 사실이다).
        """
        issued = self._key("u3-pulse-no", "events:read")
        resp = self._get(issued.secret)
        self.assertEqual(403, resp.status_code,
                         "기본 범위 키가 카메라 맥박을 읽었다 — 개방이 새어 나갔다: %s"
                         % resp.status_code)

    # ── ③ 키가 아예 없으면 401 (문이 열린 것이 아니다) ─────────────────
    def test_no_credentials_is_401(self):
        resp = self._get(None)
        self.assertEqual(401, resp.status_code)

    def test_a_wrong_secret_is_401(self):
        resp = self._get("gxk-아무거나-틀린-비밀")
        self.assertEqual(401, resp.status_code)

    # ── ④ 선언이 **이 라우트 하나**에만 붙었다 ─────────────────────────
    def test_sibling_routes_did_not_open(self):
        """⚠ 한 줄을 고치면서 옆 문까지 열지 않았는가.

        `stats/*` 는 이 턴에 **안 열었다**(U24 자리다). 키에게 그대로 401 이어야 한다 —
        여기서 403 이나 200 이 나오면 개방이 의도보다 넓게 퍼진 것이다.
        """
        issued = self._key("u3-pulse-sibling", "stats:read")
        resp = self.client.get("/api/dsm/stats/summary",
                               **{**NO_CACHE, "HTTP_X_API_KEY": issued.secret})
        self.assertEqual(401, resp.status_code,
                         "stats 까지 같이 열렸다 — 이 턴에 열기로 한 문이 아니다")

    # ── ⑤ 평문이면 거절한다 — 키가 평문으로 흐르면 키가 아니다 ────────
    @override_settings(INBOUND_API_KEY_REQUIRE_HTTPS=True)
    def test_plaintext_is_refused_even_with_the_right_scope(self):
        issued = self._key("u3-pulse-http", "pulse:read")
        resp = self._get(issued.secret)
        self.assertEqual(401, resp.status_code,
                         "HTTPS 를 요구하는데 평문 키가 지나갔다")

    # ── ⑥ 월 토큰 갈래를 **안 건드렸다** ───────────────────────────────
    def _auth_callbacks(self, want_path: str, want_method: str = "GET"):
        """살아 있는 레지스트리에서 그 라우트의 문지기들을 꺼낸다.

        ★ 정적 grep 이 아니라 **런타임 레지스트리**를 본다 — `wall_token_routes` 와
          `test_access_gate` 의 부작위 시험이 쓰는 바로 그 걸음이다. 소스에 글자가
          있는 것과 그 문지기가 실제로 라우트에 걸린 것은 다른 사실이다.
        """
        from common.tenant_scope import _iter_ninja_apis, _join

        for mount, api in _iter_ninja_apis():
            for prefix, router in getattr(api, "_routers", []) or []:
                for op_path, pv in (getattr(router, "path_operations", {}) or {}).items():
                    for op in getattr(pv, "operations", []) or []:
                        path = _join(mount, prefix, op_path)
                        methods = [str(m).upper() for m in getattr(op, "methods", []) or []]
                        if path == want_path and want_method in methods:
                            return list(getattr(op, "auth_callbacks", None) or [])
        return []

    def test_wall_token_declaration_survived(self):
        """`wall_token=True` 는 그대로다 — 키를 열면서 **월 화면을 끄지 않았다.**

        한 문지기에 선언이 둘(`wall_token` · `inbound_key`)이라, 하나를 더하면서
        다른 하나를 덮어쓰기 쉬운 자리다. 월 표시가 조용히 죽으면 아무도 모른다.
        """
        callbacks = self._auth_callbacks(PULSE)
        self.assertTrue(callbacks, "라우트를 레지스트리에서 못 찾았다")
        walls = [c for c in callbacks if getattr(c, "wall_token", False)]
        keys = [c for c in callbacks if getattr(c, "inbound_key", False)]
        self.assertTrue(walls, "월 토큰 선언이 사라졌다 — 월 화면이 조용히 죽는다")
        self.assertTrue(keys, "들어오는 키 선언이 안 붙었다")
        #: 사유 없는 개방은 「왜 열렸는지 모르는 문」이다 — 둘 다 사유를 들고 있어야 한다.
        self.assertTrue(getattr(walls[0], "wall_reason", ""))
        self.assertTrue(getattr(keys[0], "reason", ""))
