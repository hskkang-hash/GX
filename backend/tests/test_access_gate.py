# -*- coding: utf-8 -*-
"""D-348 · D-343 ③ — 전역 접근 관문. **§0.4 를 고치지 않고 길목을 막았다.**

캐시 처리: 우회 — `X-No-Cache` (D-341 착시 ⑦). 관문을 재는 시험이 캐시를 재면 안 된다.

무엇이 있었나
-------------
사고 ③에서 익명에게 데이터를 돌려주던 11자리 중 **2자리를 못 닫았다**
(`backend/delivery/` 가 §0.4 금지구역이라 라우트 선언에 손댈 수 없었다).

    [판정 D-348] D-207 이 금지한 것은 **그 파일을 수정하는 것**이다.
    그 경로로 가는 요청을 **우리 층에서 막는 것**은 금지된 적이 없다.

그래서 미들웨어 한 겹을 우리 층에 올렸다. `backend/delivery/` 도 dj-core 도 한 줄 안 바뀌었다.

이 파일이 못박는 것 다섯
------------------------
  1) 선언된 경로에 익명이 닿으면 **401** — 호출로 확인한다 (D-210)
  2) 그 401 이 **HTTP 상태로** 나간다 — 200 봉투 안의 401 이 아니다 (D-349 착시 ⑧)
  3) 들어오는 키는 **선언한 자리에만** 닿는다 — 나머지는 401 (D-343 ③ 전역 기본값 거절)
  4) 관문이 **캐시보다 바깥**에 있다 — 안쪽이면 캐시가 관문 대신 답한다 (D-341)
  5) 인증 면(로그인·토큰)은 막지 않는다 — 막으면 **아무도 들어올 수 없다**

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105 · D-224)
    skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import json

from django.conf import settings
from django.test import Client, TestCase

from common.access_gate import (
    AUTHN_REQUIRED_PATHS,
    INBOUND_KEY_ALLOWED,
    AccessGateMiddleware,
)
from tests.no_cache import NO_CACHE

#: ★ **출생 표본** — 2026-09-08 익명에게 데이터가 나갔고 §0.4 라 못 닫았던 자리.
#: `(경로, 그날 익명이 받은 바이트)`. 이 둘이 이 미들웨어가 태어난 이유다.
FORMERLY_OPEN_IN_FORBIDDEN_ZONE = (
    ("/api/delivery/drone-monitoring/drone-status", 17416),
    ("/api/delivery/etri-mock/test-scenarios", 1976),
)

#: 캐시 미들웨어. 관문은 **이것보다 바깥**이어야 한다.
CACHE_MIDDLEWARE = "common.universal_optimization.UniversalCacheMiddleware"
GATE_MIDDLEWARE = "common.access_gate.AccessGateMiddleware"


class GateJudgesWithoutRequestTest(TestCase):
    """술어를 요청 객체 없이 시험한다 — 판정이 프레임워크에 매이지 않게."""

    def setUp(self):
        self.gate = AccessGateMiddleware(lambda request: None)

    def _judge(self, **kwargs):
        base = dict(method="GET", path="/api/x", has_inbound_key=False, has_credentials=True)
        base.update(kwargs)
        return self.gate.judge(**base)

    def test_inbound_key_is_denied_by_default(self):
        """★ 기본값이 거절이다 (D-343 ③). 선언하지 않은 자리에는 키가 닿지 않는다."""
        self.assertIsNotNone(self._judge(has_inbound_key=True, path="/api/terminals/terminals"))

    def test_declared_route_accepts_inbound_key(self):
        """음성 대조 — 전부 거절이면 그건 「좁혔다」가 아니라 「다 막았다」이다."""
        method, path = sorted(INBOUND_KEY_ALLOWED)[0]
        self.assertIsNone(self._judge(has_inbound_key=True, method=method, path=path))

    def test_anonymous_is_denied_on_declared_paths(self):
        for path, _bytes in FORMERLY_OPEN_IN_FORBIDDEN_ZONE:
            self.assertIsNotNone(
                self._judge(has_credentials=False, path=path),
                "%s 가 익명에게 다시 열렸다" % path,
            )

    def test_authn_surface_is_never_blocked(self):
        """★ 로그인·토큰 면을 막으면 관문이 문을 잠그고 열쇠를 삼킨다."""
        for path in ("/api/v1/auth/login", "/api/token/refresh", "/api/auth/logout"):
            self.assertIsNone(self._judge(has_credentials=False, has_inbound_key=True, path=path),
                              "%s 가 막혔다 — 아무도 들어올 수 없다" % path)

    def test_non_api_paths_are_untouched(self):
        self.assertIsNone(self._judge(has_credentials=False, path="/admin/login/"))
        self.assertIsNone(self._judge(has_inbound_key=True, path="/static/app.js"))

    def test_trailing_slash_does_not_open_a_hole(self):
        """`/path` 를 막고 `/path/` 를 열어 두면 막은 것이 아니다."""
        path = FORMERLY_OPEN_IN_FORBIDDEN_ZONE[0][0]
        self.assertIsNotNone(self._judge(has_credentials=False, path=path + "/"))


class ForbiddenZoneRoutesRejectAnonymousTest(TestCase):
    """① 호출로 확인한다 (D-210) — 읽어서 답하지 않는다."""

    def setUp(self):
        # 캐시 처리: 우회 — 관문을 재는 시험이 캐시를 재면 안 된다 (D-341).
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def test_anonymous_gets_401(self):
        wrong = []
        for path, _bytes in FORMERLY_OPEN_IN_FORBIDDEN_ZONE:
            resp = self.client.get(path)
            if resp.status_code != 401:
                wrong.append("%s -> %s" % (path, resp.status_code))
        self.assertEqual(wrong, [], "★ 익명이 §0.4 자리에 다시 닿는다:\n  " + "\n  ".join(wrong))

    def test_rejection_speaks_in_http_status_not_in_an_envelope(self):
        """② 착시 ⑧ 을 우리가 새로 만들지 않는다 (D-349).

        거절을 HTTP 200 안에 담으면 게이트웨이·모니터링·클라이언트가 **성공으로 읽는다.**
        우리가 첫 피해자였다 — 판정기가 봉투만 읽고 18건을 반출로 셌다.
        """
        for path, _bytes in FORMERLY_OPEN_IN_FORBIDDEN_ZONE:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 401)
            body = json.loads((resp.content or b"{}").decode("utf-8", "replace"))
            self.assertNotIn(
                "status_code", body,
                "%s 의 거절이 본문에 상태를 담았다 — 봉투와 내용이 갈린다(D-349)" % path,
            )

    def test_no_payload_leaks_in_the_rejection(self):
        """거절 본문에 원래 데이터가 섞여 나가지 않는다 — 그날 17KB 가 나가던 자리다."""
        for path, was in FORMERLY_OPEN_IN_FORBIDDEN_ZONE:
            resp = self.client.get(path)
            self.assertLess(
                len(resp.content or b""), 512,
                "%s 의 401 본문이 %d바이트다 (그날 %d바이트가 나갔다)"
                % (path, len(resp.content or b""), was),
            )


class InboundKeyIsDeniedEverywhereButTheDeclaredRouteTest(TestCase):
    """③ 전역 기본값 거절 (D-343 ③) — 선언 목록 밖에서는 키가 통하지 않는다."""

    def setUp(self):
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def test_key_bearing_request_is_denied_off_the_allowlist(self):
        """가짜 키여도 **거절 자리**가 관문이어야 한다 — 핸들러에 닿기 전에 끊는다."""
        for path in ("/api/terminals/terminals",
                     "/api/dsm/events/1/clip/stream",
                     "/api/delivery/drone-monitoring/drone-status"):
            resp = self.client.get(path, HTTP_X_API_KEY="not-a-real-key-000000")
            self.assertEqual(resp.status_code, 401, "%s 에 키가 닿았다" % path)

    def test_allowlist_matches_the_route_ledger(self):
        """④ 부작위 — 미들웨어의 목록과 라우트 대장이 갈리면 대장이 거짓말한다.

        코드가 선언한 자리(`JwtOrInboundKey(inbound_key=True)`)와 이 미들웨어의
        허용 목록이 **같아야** 한다. 갈리면 한쪽이 열고 다른 쪽이 막는다.
        """
        from common.inbound_api_key import JwtOrInboundKey
        from common.tenant_scope import _iter_ninja_apis, _join

        declared = set()
        for mount, api in _iter_ninja_apis():
            for prefix, router in getattr(api, "_routers", []) or []:
                for op_path, pv in (getattr(router, "path_operations", {}) or {}).items():
                    for op in getattr(pv, "operations", []) or []:
                        path = _join(mount, prefix, op_path)
                        for cb in getattr(op, "auth_callbacks", None) or []:
                            if isinstance(cb, JwtOrInboundKey) and cb.inbound_key:
                                for m in getattr(op, "methods", []) or []:
                                    declared.add((str(m).upper(), path))
        self.assertEqual(
            declared, set(INBOUND_KEY_ALLOWED),
            "라우트 선언과 미들웨어 허용 목록이 갈렸다:\n"
            "  라우트만: %s\n  미들웨어만: %s"
            % (sorted(declared - set(INBOUND_KEY_ALLOWED)),
               sorted(set(INBOUND_KEY_ALLOWED) - declared)),
        )


class GateIsOutsideTheCacheTest(TestCase):
    """④ **캐시보다 바깥**이어야 한다 (D-341 착시 ⑦).

    캐시 안쪽에 두면, 열려 있던 동안 익명으로 채워진 항목이 관문을 지나지 않고 그대로 나간다.
    2026-09-07 에 실제로 있었던 일이다 — 고친 뒤에도 2자리가 200 이었다.
    """

    def test_gate_precedes_cache_middleware(self):
        stack = list(settings.MIDDLEWARE)
        self.assertIn(GATE_MIDDLEWARE, stack, "관문이 미들웨어 목록에서 사라졌다")
        self.assertIn(CACHE_MIDDLEWARE, stack)
        self.assertLess(
            stack.index(GATE_MIDDLEWARE), stack.index(CACHE_MIDDLEWARE),
            "★ 관문이 캐시 안쪽으로 들어갔다 — 캐시가 관문 대신 답한다(D-341)",
        )


class DeclaredPathsStayNonEmptyTest(TestCase):
    """0건 검사와 검사 못함을 가른다 (D-301)."""

    def test_lists_are_not_empty(self):
        self.assertGreater(len(AUTHN_REQUIRED_PATHS), 0,
                           "익명 거절 목록이 비었다 — 관문이 아무것도 안 본다")
        self.assertGreater(len(INBOUND_KEY_ALLOWED), 0,
                           "허용 목록이 비면 그건 「좁혔다」가 아니라 「다 막았다」이다")
