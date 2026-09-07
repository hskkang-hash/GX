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
    AUTHN_REQUIRED_PREFIXES,
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

#: ★ **두 번째 출생 표본** — 2026-09-10 (D-364). 위 둘과 성격이 다르므로 따로 둔다.
#:
#: 위 둘은 「보였는데 못 닫은 자리」였다. 이 넷은 **「안 보이던 자리」**다 —
#: 측정기가 리다이렉트를 따라가지 않아 **301 로 찍혔고**, 301 은 「본문 없음」 칸에
#: 들어가 관문이 있는 것처럼 보였다. 따라가자 200 이 나왔다.
#:
#:     GET /api/orders/banks            200 ·  87 B
#:     GET /api/orders/delivery-option  200 ·  96 B
#:     GET /api/orders/payment-methods  200 ·  97 B
#:     GET /api/orders/item-types       500        (핸들러가 터져 데이터는 안 나갔다)
#:
#: ★ 그날 본문이 `data: []` 였던 것은 **이 환경의 그 표가 비어서**이지 관문이 있어서가
#:   아니다. 그래서 아래 바이트 수는 「그날 나간 양」이 아니라 **「그날 나간 봉투의 크기」**다 —
#:   행이 있는 환경에서는 목록이 통째로 나간다 (D-301 「검사 못함 ≠ 0건 검사」).
#: `backend/orders/` 는 §0.4 다. 라우트가 아니라 **길목**을 막았다 (D-357).
FORMERLY_HIDDEN_BY_REDIRECT = (
    ("/api/orders/banks", 87),
    ("/api/orders/delivery-option", 96),
    ("/api/orders/payment-methods", 97),
    ("/api/orders/item-types", 0),
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


class RedirectHiddenRoutesRejectAnonymousTest(TestCase):
    """★ D-364 — **리다이렉트 뒤에 숨어 있던 넷.** 따라가서 재고, 막고, 다시 잰다.

    이 시험이 못박는 것은 관문 하나가 아니라 **측정 방식**이다:
    `follow=True` 없이 재면 301 이 나오고, 301 은 「막혔다」로도 「닿았다」로도 읽힌다.
    두 뜻을 갖는 응답은 판정에 쓸 수 없다 — 그래서 여기서는 언제나 따라간다.
    """

    def setUp(self):
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def test_anonymous_gets_401_when_the_redirect_is_followed(self):
        """① 따라간 끝에서 401 이다. **중간의 301 을 답으로 읽지 않는다.**"""
        wrong = []
        for path, _bytes in FORMERLY_HIDDEN_BY_REDIRECT:
            resp = self.client.get(path, follow=True)
            if resp.status_code != 401:
                wrong.append("%s -> %s" % (path, resp.status_code))
        self.assertEqual(
            wrong, [],
            "★ 익명이 리다이렉트 끝에서 다시 닿는다:\n  " + "\n  ".join(wrong))

    def test_the_gate_answers_before_the_redirect(self):
        """② **관문이 리다이렉트보다 앞이다.** 막은 자리는 301 조차 내주지 않는다.

        착시가 생기던 구조는 이렇다: `APPEND_SLASH` 가 301 을 먼저 내고, 재는 쪽이
        따라가지 않으면 그 301 이 답으로 남는다. 301 은 「막혔다」로도 「닿았다」로도
        읽히고, **두 뜻을 갖는 응답은 판정에 쓸 수 없다.**

        고친 뒤에는 따라가든 안 따라가든 401 이다 — 착시가 이 넷에서 **구조로 사라졌다**
        (D-357 「그 자리에 못 생기게 하는 것이 생긴 것을 잡는 것보다 낫다」).
        """
        for path, _bytes in FORMERLY_HIDDEN_BY_REDIRECT:
            self.assertEqual(
                self.client.get(path).status_code, 401,
                "%s 가 관문보다 먼저 301 을 냈다 — 착시가 돌아왔다" % path)

    def test_the_illusion_still_exists_where_we_did_not_gate(self):
        """③ **음성 대조** — 착시 자체가 사라진 것은 아니라는 사실을 시험이 기억한다.

        ②만 있으면 「이제 301 은 안 나온다」로 읽힌다. 그러면 다음 사람이 다른 경로를
        따라가지 않고 재고, 같은 착시를 다시 겪는다. 그래서 **막지 않은 자리**에서
        301 이 여전히 나온다는 것을 여기서 못박는다.

        [실측 2026-09-10] `GET /api/flight-log/flight-log`
            따라가지 않으면 **301** · 따라가면 200 봉투 안의 403 (D-349 착시 ⑧과 겹친다)
        """
        ungated = "/api/flight-log/flight-log"
        self.assertEqual(
            self.client.get(ungated).status_code, 301,
            "%s 가 301 이 아니다 — 착시의 구조가 바뀌었으면 이 대조를 다시 골라라" % ungated)
        self.assertNotEqual(
            self.client.get(ungated, follow=True).status_code, 301,
            "따라갔는데도 301 이다 — 리다이렉트가 자기 자신을 가리킨다")

    def test_no_payload_leaks_in_the_rejection(self):
        """③ 거절 본문에 원래 목록이 섞여 나가지 않는다."""
        for path, _bytes in FORMERLY_HIDDEN_BY_REDIRECT:
            resp = self.client.get(path, follow=True)
            self.assertLess(
                len(resp.content or b""), 512,
                "%s 의 401 본문이 %d바이트다" % (path, len(resp.content or b"")))

    def test_every_hidden_path_is_actually_declared(self):
        """④ 시험이 아는 넷이 **선언 목록에 실재**한다 — 시험만 알고 코드는 모르는 상태를 막는다."""
        missing = [p for p, _ in FORMERLY_HIDDEN_BY_REDIRECT
                   if p not in AUTHN_REQUIRED_PATHS]
        self.assertEqual(missing, [],
                         "시험은 아는데 관문은 모르는 경로가 있다: %r" % missing)


class FrontLineIsTheSecondDefenseTest(TestCase):
    """★ OPS-13 · D-361 — **관문을 앞단까지 넓힌다.**

        **단일 방어선은 방어선이 아니다.**
        미들웨어는 코드이고, 코드는 리팩터링 중에 순서가 바뀐다 — 앞단은 그때 남는다.

    위의 `GateIsOutsideTheCacheTest` 는 미들웨어의 **순서**를 못박는다. 그런데 못박는
    것과 **막는 것**은 다르다: 순서가 바뀐 그 순간부터 시험이 빨개질 때까지 요청은
    계속 지나간다. 그래서 같은 규칙을 앞단(nginx)에 한 벌 더 걸고, **두 벌이 아직
    같은지**를 여기서 본다.

    ⚠ 이 시험이 보는 것은 **설정을 만드는 규칙**이지 떠 있는 nginx 가 아니다
      (`gx-shell` 에 저장소의 `nginx/` 가 붙지 않는다 — backend·scripts·docs 만 붙는다).
      떠 있는 앞단은 `scripts/ops_front_line.py --probe` 가 **호출로** 잰다(D-210).
      [실측 2026-09-05 · 턴 C] 그 실측은 18갈래 exit 0 이었다.
    """

    def setUp(self):
        from common import front_line

        self.front = front_line
        self.conf = front_line.render_locations()

    def test_front_line_covers_every_path_the_middleware_covers(self):
        """① 앞단이 미들웨어와 **같은 자리**를 막는다 — 슬래시 변형까지."""
        want = set()
        for path in AUTHN_REQUIRED_PATHS:
            want.add(path.rstrip("/"))
            want.add(path.rstrip("/") + "/")
        got = self.front.parse_gated_paths(self.conf)
        self.assertEqual(
            got, want,
            "앞단과 미들웨어가 갈렸다:\n  앞단만: %s\n  미들웨어만: %s"
            % (sorted(got - want), sorted(want - got)))

    def test_front_line_covers_every_prefix_the_middleware_covers(self):
        """①-b ★ [P-83] **접두도 두 벌이다.**

        경로 틀(inbound 키: `/api/apikey/keys/{user_id}`)은 이름으로 못 막는다. 미들웨어가 접두로
        막았는데 앞단이 이름으로만 막으면, 미들웨어가 빠지는 날 그 자리는 **앞단이
        모르는 자리**가 된다 — 두 방어선이 아니라 하나가 된다.
        """
        want = {p if p.endswith("/") else p + "/" for p in AUTHN_REQUIRED_PREFIXES}
        got = self.front.parse_gated_prefixes(self.conf)
        self.assertEqual(
            got, want,
            "앞단과 미들웨어의 **접두**가 갈렸다 — 앞단만: %s / 미들웨어만: %s"
            % (sorted(got - want), sorted(want - got)))

    def test_front_line_key_allowlist_matches_the_middleware(self):
        """② 들어오는 키의 허용 목록도 한 벌이다 (D-343 ③)."""
        want = {(m.upper(), p.rstrip("/") or "/") for m, p in INBOUND_KEY_ALLOWED}
        self.assertEqual(self.front.parse_key_allowed(self.conf), want)

    def test_front_line_is_not_a_wall(self):
        """③ **음성 대조** — 막지 않은 자리는 앞단도 막지 않는다.

        전부 401 을 내는 앞단은 방어선이 아니라 벽이고, 벽은 첫날 치워진다.
        치워진 앞단은 없는 앞단이다.
        """
        self.assertNotIn("/api/flight-log/flight-log",
                         self.front.parse_gated_paths(self.conf))

    def test_front_line_does_not_depend_on_the_middleware_order(self):
        """④ ★ **이것이 이 절의 요점이다.**

        관문을 `MIDDLEWARE` 에서 통째로 빼도 앞단의 설정은 그대로다. 두 방어선이
        **같은 사고로 함께 무너지지 않는다**는 뜻이고, 그것이 「단일 방어선은 방어선이
        아니다」의 집행이다.
        """
        stripped = [m for m in settings.MIDDLEWARE if m != GATE_MIDDLEWARE]
        with self.settings(MIDDLEWARE=stripped):
            self.assertNotIn(GATE_MIDDLEWARE, settings.MIDDLEWARE)
            still = self.front.parse_gated_paths(self.front.render_locations())
        self.assertEqual(
            still, self.front.parse_gated_paths(self.conf),
            "미들웨어를 빼자 앞단도 함께 사라졌다 — 그러면 방어선은 여전히 하나다")

    def test_front_line_rejection_keeps_the_same_contract(self):
        """⑤ 앞단의 거절도 **HTTP 상태로 말하고** 본문이 짧다 (D-349 · 반출 0).

        그리고 **앞단의 답임을 밝힌다** — 밝히지 않으면 뒷단이 낸 401 과 구별할 수
        없고, 구별 못 하는 증거로는 「앞단이 막았다」를 말할 수 없다.
        """
        rejections = [ln for ln in self.conf.splitlines() if "return 401" in ln]
        self.assertGreaterEqual(len(rejections), len(AUTHN_REQUIRED_PATHS))
        for line in rejections:
            body = line.split("return 401", 1)[1]
            self.assertLess(len(body.encode("utf-8")), 512)
            self.assertNotIn("status_code", body)
        self.assertIn("(front line)", self.conf)


#: ★★ **세 번째 출생 표본** — 2026-09-06 턴 I (P-83). 앞의 둘과 성격이 또 다르다.
#:
#:   첫째 표본  보였는데 §0.4 라 못 닫은 자리 (읽기)
#:   둘째 표본  301 뒤에 숨어 안 보이던 자리 (읽기)
#:   ★셋째 표본 **422 뒤에 숨어 있던 자리 — 그리고 이것은 쓰기다**
#:
#: `probe_write_surface.py` 는 턴 H 까지 빈 본문 `{}` 하나를 던지고 「도달 못 하면
#: 관문이 섰다」로 셌다. 그 17자리 중 **13자리의 실제 답이 422**였다. 422 는
#: 「인증 없이도 여기까지 왔고 본문 형식에서 떨어졌다」는 뜻이지 관문이 아니다 —
#: **401·403 과 422 는 다른 칸이다**(P-83). 스키마를 통과하는 최소 본문을 만들어
#: 다시 던지자 다섯 자리에서 익명이 핸들러까지 닿았다.
#:
#: `(경로, 메서드, 익명이 그 자리에서 할 수 있던 일)`
FORMERLY_HIDDEN_BY_SCHEMA_ERROR = (
    ("/api/v1/auth/reset-password-for-user", "POST",
     "아무 사용자의 비밀번호를 바꾼다 — 핸들러에 권한 검사가 한 줄도 없다"),
    ("/api/v1/user/create-user", "POST",
     "계정을 만든다 — 문서엔 admin 필요, 코드엔 그 검사가 없다"),
    ("/api/v1/auth/register", "POST", "계정을 만든다 — 자가 가입 면이 아니다"),
    ("/api/source/save-html", "POST", "템플릿 디렉터리에 파일을 쓰고 기존 파일을 지운다"),
    ("/api/advanced-table/column-order", "PUT", "남의 그리드 설정을 바꾼다"),
)


class WriteSurfaceHiddenBySchemaErrorTest(TestCase):
    """★★ P-83 — **422 를 관문으로 세지 않는다.** 그 착각이 게이트를 거짓 초록으로 만들었다.

    이 시험이 못박는 것은 관문 다섯이 아니라 **판정의 칸**이다:

        401 · 403  관문           — 막았다
        422        도달·검증 실패 — **막지 않았다.** 본문만 맞추면 그대로 들어간다
        404 · 405  도달 실패      — 그 자리에 그 메서드가 없다

    셋을 한 칸에 넣으면 「관문 17」 같은 수가 나오고, 그 수를 보는 사람은
    **열일곱 자리가 지켜지고 있다**고 읽는다. 실제로 그랬던 것은 둘이었다.
    """

    def setUp(self):
        # 캐시 처리: 우회 — 관문을 재는 시험이 캐시를 재면 안 된다 (D-341).
        self.client = Client(raise_request_exception=False, **NO_CACHE)
        self.gate = AccessGateMiddleware(lambda request: None)

    def test_every_hidden_write_path_is_actually_declared(self):
        """① 시험이 아는 다섯이 **선언 목록에 실재**한다 (시험만 알고 코드는 모르는 상태를 막는다)."""
        missing = [p for p, _m, _w in FORMERLY_HIDDEN_BY_SCHEMA_ERROR
                   if p not in AUTHN_REQUIRED_PATHS]
        self.assertEqual(missing, [],
                         "시험은 아는데 관문은 모르는 쓰기 경로가 있다: %r" % missing)

    def test_anonymous_write_gets_401_with_a_schema_passing_body(self):
        """② ★ **스키마를 통과하는 본문으로** 때린다 — 빈 본문으로 재면 422 가 나오고,
        422 를 관문으로 읽는 것이 바로 이번에 잡은 거짓 초록이다.

        본문에 실제 값을 담아 보내도 **401** 이어야 한다. 핸들러는 한 줄도 안 돈다.
        """
        bodies = {
            "/api/v1/auth/reset-password-for-user": {"id": 1, "new_password": "GxProbe!2026"},
            "/api/v1/user/create-user": {"username": "gxprobe_gate", "email":
                                         "gxprobe@example.invalid", "password": "GxProbe!2026"},
            "/api/v1/auth/register": {"username": "gxprobe_gate2", "email":
                                      "gxprobe2@example.invalid", "password": "GxProbe!2026"},
            "/api/advanced-table/column-order": [],
        }
        wrong = []
        for path, method, what in FORMERLY_HIDDEN_BY_SCHEMA_ERROR:
            if path == "/api/source/save-html":
                resp = self.client.post(path, data={"menu_id": "1", "url": "https://x.invalid/"})
            else:
                url = path
                if path == "/api/advanced-table/column-order":
                    url = path + "?grid_id=1&user_id=1"
                resp = self.client.generic(
                    method, url, data=json.dumps(bodies[path]).encode(),
                    content_type="application/json", **NO_CACHE)
            if resp.status_code != 401:
                wrong.append("%s %s -> %s (익명이 %s)" % (method, path, resp.status_code, what))
        self.assertEqual(
            wrong, [], "★ 익명이 쓰기 면에 다시 닿는다:\n  " + "\n  ".join(wrong))

    def test_the_gate_beats_the_authn_surface_exemption(self):
        """③ ★★ **넓은 면제 아래 좁은 사고가 숨어 있었다.**

        `AUTHN_SURFACE` 는 「`/api/v1/auth/...` 는 비켜 준다」는 규칙이다. 그 규칙이
        `reset-password-for-user` 를 함께 비켜 주고 있었다 — 익명이 `{id, new_password}`
        만 보내면 아무 계정의 비밀번호가 바뀌는 자리를.

        **이름을 적은 것이 규칙보다 세다.** 순서가 그 집행이다.
        """
        for path in ("/api/v1/auth/reset-password-for-user", "/api/v1/auth/register"):
            self.assertIsNotNone(
                self.gate.judge(method="POST", path=path,
                                has_inbound_key=False, has_credentials=False),
                "%s 가 인증 면 면제에 묻혔다 — 이름이 규칙보다 세야 한다" % path)

    def test_login_still_works_after_the_reordering(self):
        """④ **음성 대조** — 순서를 바꾸면서 로그인 길을 막지 않았다.

        관문이 문을 잠그고 열쇠를 삼키면 이 시스템에는 아무도 들어올 수 없다.
        ③만 있으면 그 사고를 못 잡는다.
        """
        for path in ("/api/v1/auth/login", "/api/v1/auth/logout",
                     "/api/v1/auth/forgot-password", "/api/v1/auth/reset-password",
                     "/api/token/pair", "/api/token/refresh"):
            self.assertIsNone(
                self.gate.judge(method="POST", path=path,
                                has_inbound_key=False, has_credentials=False),
                "%s 가 막혔다 — 아무도 들어올 수 없다" % path)

    def test_credentialed_requests_are_not_touched(self):
        """⑤ **음성 대조** — 자격증명을 들고 온 요청은 이 관문이 한 자도 안 만진다.

        전부 401 을 내는 관문은 관문이 아니라 벽이고, 벽은 첫날 치워진다.
        """
        for path, method, _w in FORMERLY_HIDDEN_BY_SCHEMA_ERROR:
            self.assertIsNone(
                self.gate.judge(method=method, path=path,
                                has_inbound_key=False, has_credentials=True),
                "%s 가 인증된 요청까지 막았다" % path)

    def test_trailing_slash_does_not_open_a_hole(self):
        """⑥ `/path` 를 막고 `/path/` 를 열어 두면 막은 것이 아니다."""
        for path, method, _w in FORMERLY_HIDDEN_BY_SCHEMA_ERROR:
            self.assertIsNotNone(
                self.gate.judge(method=method, path=path + "/",
                                has_inbound_key=False, has_credentials=False),
                "%s/ 가 열려 있다" % path)
