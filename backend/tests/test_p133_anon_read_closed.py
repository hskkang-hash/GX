# -*- coding: utf-8 -*-
"""P-133 — **익명이 자료를 200 으로 받던 마지막 다섯 자리**를 못박는다.

캐시 처리: 우회 — `X-No-Cache` (D-341 착시 ⑦). 관문을 재는 시험이 캐시를 재면 안 된다.

무엇이 있었나 [실측 2026-09-11 · `scripts/probe_anon_read.py`]
--------------------------------------------------------------
라우터 전수 **읽기 331자리**를 자격증명 없이 불렀다(로그인하지 않는 익명 전용 탐침 —
이 제품은 계정당 동시 세션이 하나여서, 로그인하는 탐침은 옆 차선의 토큰을 빼앗고
빼앗긴 쪽의 401 이 「관문이 섰다」로 세어져 **거짓 초록**이 된다 · D-350).

빨강 술어(`probe_read_surface.has_data`: 2xx · 거부 봉투 아님 · 봉투를 걷어내고도
남는 것이 있음)로 센 결과 **빨강 5 · 초록 310 · 공개 2 · 회색 14**:

    GET /api/v1/auth/timezones                 200 · 109,309 B · 598덩이
    GET /api/config-management/list-optimized  200 ·  16,436 B ·  12덩이
    GET /api/v1/auth/groups                    200 ·   1,685 B ·  10덩이
    GET /api/v1/auth/languages                 200 ·     466 B ·   3덩이
    GET /api/register-settings                 200 ·     182 B ·   1덩이

다섯 다 **dj-core**(site-packages `core/`) 안이다 — §0.4 금지구역이라 라우트 선언에
`auth=` 를 못 붙인다. D-348 그대로 **우리 층 미들웨어(`common/access_gate.py`)에서
길목을 막았다.** dj-core 도 `backend/delivery/` 도 한 줄 안 바뀌었다.

★ **옆자리 셋을 함께 닫았다** — `/api/v1/auth/{departments,positions,teams}`.
  빨강 술어는 이 셋을 회색으로 놓았다(200 인데 `{"data": []}`). 비어 있던 이유는
  관문이 아니라 **이 환경의 그 표에 행이 없어서**다 — 바로 옆 `/api/v1/auth/groups` 가
  같은 컨트롤러·같은 모양인데 행이 10개라 빨강이었다. 「검사 못함 ≠ 0건 검사」(D-301).

★ 앞의 셋이 `AUTHN_SURFACE`(「인증 면은 비켜 준다」)라는 **넓은 규칙** 아래 숨어 있었다 —
  `reset-password-for-user`(P-83) · `otp/reset`(P-113) 과 같은 모양이다.
  **손으로 이름을 적은 것이 규칙보다 세다**는 그 순서를 여기서 다시 못박는다.

이 파일이 못박는 것 여섯
------------------------
  1) 여덟 자리(빨강 5 + 옆자리 3)가 익명에게 **401** 이다 — 호출로 확인한다 (D-210)
  2) 그 401 본문에 **원래 자료가 섞여 나가지 않는다** — 109KB 가 나가던 자리다
  3) 거절이 **HTTP 상태로** 말한다 — 200 봉투 안의 401 이 아니다 (D-349 착시 ⑧)
  4) **음성 대조** — 공개가 설계인 문(로그인·health·csrf)은 여전히 열려 있다.
     전부 막는 관문은 방어선이 아니라 벽이고, 벽이면 아무도 못 들어온다
  5) 자격증명을 **들고 온** 요청에는 이 관문이 한마디도 하지 않는다
     — 인증 사용자 회귀 0 의 근거다 (관문은 `_has_credentials` 가 거짓일 때만 말한다)
  6) 시험이 아는 여덟을 **코드도 안다** — 시험만 아는 상태를 막는다 (D-301)

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105 · D-224)
    skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import json

from django.test import Client, TestCase

from common.access_gate import (
    ANON_PROJECTION_MAX_BYTES,
    ANON_PUBLIC_PROJECTIONS,
    AUTHN_REQUIRED_PATHS,
    AccessGateMiddleware,
)
from tests.no_cache import NO_CACHE

#: ★ **출생 표본** — `(경로, 그날 익명이 받은 바이트)`. 이 다섯이 P-133 이 태어난 이유다.
#: 바이트는 「그날 실제로 나간 양」이다(빈 봉투가 아니라 자료가 든 본문의 크기).
ANON_READ_LEAKS = (
    ("/api/v1/auth/timezones", 109309),
    ("/api/config-management/list-optimized", 16436),
    ("/api/v1/auth/groups", 1685),
    ("/api/v1/auth/languages", 466),
    ("/api/register-settings", 182),
)

#: ★ **옆자리 셋** — 빨강 술어는 이들을 **회색**으로 놓았다(봉투를 걷어내니 비었다).
#: 그러나 비어 있던 이유는 관문이 아니라 **이 환경의 그 표에 행이 없어서**다 —
#: 바로 옆의 `/api/v1/auth/groups` 가 같은 컨트롤러·같은 모양인데 행이 10개라 빨강이었다.
#: 「검사 못함 ≠ 0건 검사」(D-301) + 「한 자리를 막고 옆자리를 열면 사고는 그대로다」.
#: [실측 2026-09-11 · 익명] departments 200·87B `{"data": []}` · positions 200·85B ·
#: teams 200·81B — 부서·직위·팀 이름은 조직도이고, 조직도는 테넌트 자료다.
EMPTY_ONLY_BY_ACCIDENT = (
    ("/api/v1/auth/departments", 87),
    ("/api/v1/auth/positions", 85),
    ("/api/v1/auth/teams", 81),
)

#: ★ [D-461 · 2026-09-15 턴 P] 다섯 중 하나는 **닫지 않고 좁혔다.** 로그인 화면(§0.4 rj-core)이
#:   로그인 전에 부르는 자리라, 닫자 로그인 부제목이 사라지고 배치의 걷기가 되돌렸다.
#:   원 응답 16,436 B 는 여전히 안 나간다 — 공개 두 칸만 새로 만든 응답이 나간다(아래 ⑦).
PROJECTED_NOT_CLOSED = ("/api/config-management/list-optimized",)

#: 이 파일이 익명에게 401 을 요구하는 자리 전부.
ALL_CLOSED = tuple(x for x in ANON_READ_LEAKS if x[0] not in PROJECTED_NOT_CLOSED)     + EMPTY_ONLY_BY_ACCIDENT

#: ★ **음성 대조** — 공개가 설계인 문. 아직 로그인하지 못한 사람이 부르는 자리다.
#: (`scripts/probe_read_surface.py::PUBLIC_READ_BY_DESIGN` 과 같은 판단 기준.)
PUBLIC_BY_DESIGN = (
    "/api/v1/auth/login",       # 이 문이 막히면 아무도 들어올 수 없다
    "/api/v1/auth/csrf-token",  # 토큰이 있어야 토큰을 받을 수 있으면 로그인할 수 없다
    "/api/v1/health",           # 로드밸런서·감시기가 자격증명 없이 부른다
)

#: 관문이 낸 거절임을 알리는 사유 문구 (`common/access_gate.py::_denied`).
#: **누가 답했는가**를 가르는 표식이다 — 뒷단 인증기의 401 과 구별하는 데 쓴다.
GATE_REASON = "authentication required"


class AnonymousReadLeaksAreClosedTest(TestCase):
    """① 호출로 확인한다 (D-210) — 읽어서 답하지 않는다."""

    def setUp(self):
        # 캐시 처리: 우회 — 관문을 재는 시험이 캐시를 재면 안 된다 (D-341).
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def test_anonymous_gets_401(self):
        wrong = []
        for path, _bytes in ALL_CLOSED:
            resp = self.client.get(path, follow=True)
            if resp.status_code != 401:
                wrong.append("%s -> %s" % (path, resp.status_code))
        self.assertEqual(wrong, [],
                         "★ 익명이 다시 자료를 받는다:\n  " + "\n  ".join(wrong))

    def test_the_gate_answers_before_the_redirect(self):
        """★ 리다이렉트를 따라가지 않아도 401 이다 (D-364).

        `APPEND_SLASH` 가 301 을 먼저 내면 그 301 은 「막혔다」로도 「닿았다」로도
        읽힌다 — 두 뜻을 갖는 응답은 판정에 쓸 수 없다. `/api/register-settings` 가
        실제로 끝 빗금이 붙는 자리다.
        """
        for path, _bytes in ALL_CLOSED:
            self.assertEqual(
                self.client.get(path).status_code, 401,
                "%s 가 관문보다 먼저 301 을 냈다 — 착시가 돌아왔다" % path)

    def test_no_payload_leaks_in_the_rejection(self):
        """② 거절 본문에 원래 자료가 섞여 나가지 않는다 — 109KB 가 나가던 자리다."""
        for path, was in ALL_CLOSED:
            resp = self.client.get(path, follow=True)
            body = resp.content or b""
            self.assertLess(
                len(body), 512,
                "%s 의 401 본문이 %d바이트다 (그날 %d바이트가 나갔다)"
                % (path, len(body), was))

    def test_rejection_speaks_in_http_status_not_in_an_envelope(self):
        """③ 착시 ⑧ 을 우리가 새로 만들지 않는다 (D-349)."""
        for path, _bytes in ALL_CLOSED:
            resp = self.client.get(path, follow=True)
            self.assertEqual(resp.status_code, 401)
            body = json.loads((resp.content or b"{}").decode("utf-8", "replace"))
            self.assertNotIn(
                "status_code", body,
                "%s 의 거절이 본문에 상태를 담았다 — 봉투와 내용이 갈린다(D-349)" % path)

    def test_trailing_slash_does_not_open_a_hole(self):
        """`/p` 를 막고 `/p/` 를 열어 두면 막은 것이 아니다."""
        for path, _bytes in ALL_CLOSED:
            self.assertEqual(
                self.client.get(path.rstrip("/") + "/", follow=True).status_code, 401,
                "%s/ 가 열려 있다" % path)


class PublicDoorsStayOpenTest(TestCase):
    """④ **음성 대조** — 전부 401 을 내는 관문은 방어선이 아니라 벽이다.

    이 절이 없으면 「다 막았다」도 위의 시험을 전부 통과한다. 그리고 벽은 첫날
    치워지고, 치워진 관문은 없는 관문이다.
    """

    def setUp(self):
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def test_login_and_health_are_not_gated_by_the_middleware(self):
        gate = AccessGateMiddleware(lambda request: None)
        for path in PUBLIC_BY_DESIGN:
            self.assertIsNone(
                gate.judge(method="GET", path=path, has_inbound_key=False,
                           has_credentials=False),
                "%s 가 막혔다 — 아무도 들어올 수 없다" % path)

    def test_public_doors_do_not_answer_with_the_gate_rejection(self):
        """호출로도 본다 — 관문의 거절 사유가 이 문들에서 나오면 안 된다."""
        for path in PUBLIC_BY_DESIGN:
            resp = self.client.get(path, follow=True)
            body = (resp.content or b"").decode("utf-8", "replace")
            self.assertNotIn(
                GATE_REASON, body,
                "%s 에서 관문의 거절이 나왔다 — 로그인 길이 막혔다" % path)


class GateIsSilentForCredentialBearingRequestsTest(TestCase):
    """⑤ ★ **인증 사용자 회귀 0 의 근거.**

    이 관문이 답하는 질문은 하나다: 「아무것도 안 들고 들어왔는가」
    (`common/access_gate.py::_has_credentials` — 유효성은 보지 않는다. 보면 이 미들웨어가
     두 번째 인증기가 되고, 인증기가 둘이면 언젠가 갈린다).
    그러므로 자격증명을 **들고 온** 요청에 대해 이 관문은 한마디도 하지 않는다 —
    이 자리들을 막은 것이 인증 사용자의 200 을 건드릴 수 없는 이유가 이것이다.
    """

    def setUp(self):
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def test_judge_is_none_when_credentials_are_present(self):
        gate = AccessGateMiddleware(lambda request: None)
        for path, _bytes in ALL_CLOSED:
            self.assertIsNone(
                gate.judge(method="GET", path=path, has_inbound_key=False,
                           has_credentials=True),
                "%s 에서 관문이 **자격증명을 들고 온** 요청까지 막았다" % path)

    def test_credential_bearing_request_is_not_stopped_by_this_gate(self):
        """호출로도 본다 — 답이 무엇이든 **이 관문의 사유**는 아니어야 한다.

        (헤더가 가짜이므로 뒷단의 인증기가 401 을 낼 수 있다. 그것은 제품의 답이고,
         여기서 가르는 것은 **누가 답했는가**다. 관문의 401 만 `reason` 을 달고 나간다.)
        """
        for path, _bytes in ALL_CLOSED:
            resp = self.client.get(path, follow=True,
                                   HTTP_AUTHORIZATION="Bearer not-a-real-token-000000")
            body = (resp.content or b"").decode("utf-8", "replace")
            self.assertNotIn(
                GATE_REASON, body,
                "%s 에서 관문이 자격증명을 들고 온 요청을 끊었다" % path)


class DeclaredPathsMatchThisTestTest(TestCase):
    """⑥ 부작위 — **시험만 알고 코드는 모르는 상태**를 막는다 (D-301)."""

    def test_every_leak_is_actually_declared(self):
        missing = [p for p, _ in ALL_CLOSED if p not in AUTHN_REQUIRED_PATHS]
        self.assertEqual(missing, [],
                         "시험은 아는데 관문은 모르는 경로가 있다: %r" % missing)

    def test_the_front_line_covers_them_too(self):
        """★ 앞단(두 번째 방어선)도 같은 다섯을 덮는다 (OPS-13 · D-361).

        미들웨어는 코드이고, 코드는 리팩터링 중에 순서가 바뀐다 — 앞단은 그때 남는다.
        """
        from common import front_line

        gated = front_line.parse_gated_paths(front_line.render_locations())
        for path, _bytes in ALL_CLOSED:
            self.assertIn(path, gated, "앞단이 %s 를 모른다" % path)
            self.assertIn(path + "/", gated, "앞단이 %s/ 를 모른다" % path)


class LoginConfigIsProjectedNotLeakedTest(TestCase):
    """⑦ [D-461] 로그인 화면이 로그인 전에 읽는 **두 칸만** 나간다 — 원 응답의 보안 정책은 안 나간다.

    출생 표본: 원 응답 16,436 B 의 `System` 묶음에는 `cidr`·`security`·`otp`·`validation`·`domain`
    이 함께 들어 있었다. 투영은 원 응답을 **거르지 않고 새로 만든다** — 그래서 아래 표에 없는
    칸은 이름조차 본문에 나올 수 없어야 한다.
    """

    PATH = PROJECTED_NOT_CLOSED[0]
    #: 원 응답에 실제로 있던 보안 칸들 — 투영 본문에 **글자로도** 나오면 안 된다.
    FORBIDDEN = ("cidr", "security", "otp", "validation", "domain", "refresh_time", "Operation")

    def setUp(self):
        from core.configuration.models import AdminConfig
        self.client = Client(raise_request_exception=False, **NO_CACHE)
        AdminConfig.objects.create(
            name="System", is_active=True, is_sensitive=False, description="t",
            settings={"subtitle": {"ko": "AI기반 드론.로봇 통합 운영 서비스", "en": "AI-based"},
                      "cidr": ["10.0.0.0/8"], "security": {"lock": 5}, "otp": {"on": True},
                      "validation": {"min": 8}, "domain": "x.invalid", "refresh_time": 60})
        # ★ 이 환경의 실제 행처럼 **비활성**으로 둔다 — 원 뷰는 이것도 실었고 로그인 화면은 읽었다.
        AdminConfig.objects.create(
            name="system_register", is_active=False, is_sensitive=False, description="t",
            settings={"is_allow_register": {"value": False, "description": "Allow register"}})
        AdminConfig.objects.create(
            name="Operation", is_active=True, is_sensitive=False, description="t",
            settings={"secret_ops": {"value": "do-not-leak"}})

    def _get(self, path=None, **kw):
        resp = self.client.get(path or self.PATH, follow=True, **kw)
        return resp, json.loads((resp.content or b"{}").decode("utf-8", "replace"))

    def test_anonymous_gets_only_the_two_public_cells(self):
        resp, body = self._get()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get("X-GX-Public-Projection"), "login-config")
        folded = {r["name"]: r["settings"] for r in body["data"]}   # rj-core `bM` 과 같은 접기
        self.assertEqual(set(folded), {"System", "system_register"})
        self.assertEqual(set(folded["System"]), {"subtitle"})
        self.assertEqual(set(folded["system_register"]), {"is_allow_register"})
        self.assertEqual(folded["System"]["subtitle"]["ko"], "AI기반 드론.로봇 통합 운영 서비스")

    def test_security_policy_never_appears_even_as_a_word(self):
        resp, _ = self._get()
        text = resp.content.decode("utf-8", "replace")
        for word in self.FORBIDDEN + ("do-not-leak", "10.0.0.0"):
            self.assertNotIn(word, text, "투영 본문에 %r 가 나왔다 — 거름이 아니라 누출이다" % word)
        self.assertLess(len(resp.content), ANON_PROJECTION_MAX_BYTES)

    def test_name_parameter_is_honoured_and_cannot_widen(self):
        _, one = self._get(self.PATH + "?name=System")
        self.assertEqual([r["name"] for r in one["data"]], ["System"])
        _, other = self._get(self.PATH + "?name=Operation")
        self.assertEqual(other["data"], [], "허용 목록 밖의 이름을 달라고 하면 빈 목록이어야 한다")

    def test_trailing_slash_is_the_same_projection(self):
        resp, _ = self._get(self.PATH + "/")
        self.assertEqual(resp.get("X-GX-Public-Projection"), "login-config")

    def test_sensitive_group_is_withheld_even_if_named(self):
        from core.configuration.models import AdminConfig
        AdminConfig.objects.filter(name="System").update(is_sensitive=True)
        _, body = self._get()
        self.assertNotIn("System", [r["name"] for r in body["data"]])

    def test_credential_bearing_request_is_not_projected(self):
        resp = self.client.get(self.PATH, follow=True,
                               HTTP_AUTHORIZATION="Bearer not-a-real-token-000000")
        self.assertIsNone(resp.get("X-GX-Public-Projection"),
                          "자격증명을 들고 온 요청까지 투영했다 — 인증 사용자의 화면이 줄어든다")

    def test_projection_is_declared_and_not_double_gated(self):
        """선언은 한 자리 — 401 목록에도 있으면 투영보다 거절이 먼저 나갈 수 있다. 앞단도 막으면 운영 모양(8500)에서 로그인 부제목이 다시 빈다."""
        from common import front_line
        self.assertIn(self.PATH, ANON_PUBLIC_PROJECTIONS)
        self.assertNotIn(self.PATH, AUTHN_REQUIRED_PATHS)
        gated = front_line.parse_gated_paths(front_line.render_locations())
        self.assertNotIn(self.PATH, gated, "앞단이 투영 자리를 401 로 막는다")
