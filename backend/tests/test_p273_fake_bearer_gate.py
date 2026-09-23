# -*- coding: utf-8 -*-
"""P-273 — **가짜 `Authorization` 으로도 읽기 면이 안 뚫린다는 것을 회귀로 잠근다** (턴 AF · 차선 S).

캐시 처리: 우회 — `tests/no_cache.NO_CACHE`(`X-No-Cache`)를 실은 `Client` 로 읽기 면
364자리를 때린다(이 파일 `setUpClass`). **우회여야 하는 까닭**: 이 시험이 묻는 것은
「가짜 자격으로 자료가 나오는가」인데, 응답 캐시가 적중하면 **자격과 무관하게 지난
본문이 그대로** 돌아온다 — 그 200 은 관문을 잰 수가 아니다(D-341 착시 ⑦ ·
`guardianx-response-cache-masks-failures`).

[조율자 턴 AF 오판: 훅 `[CACHE-BYPASS]` 가 이 줄이 없다고 커밋을 물렀을 때, 조율자가
먼저 적은 문장은 **「이 파일은 HTTP 를 한 번도 안 때린다 — 해당 없음」** 이었다.
코드를 안 보고 머리말만 읽고 쓴 것이고, 178행이 `Client(..., **NO_CACHE)` 다.
훅이 옳았고 조율자가 틀렸다. **머리글은 늙고, 새로 쓴 머리글도 늙은 채로 태어난다.**]

무엇을 닫는가
--------------
`common/access_gate.py::_has_credentials` 는 자격증명을 **들고 왔는지만** 본다
(설계 — 유효성까지 보면 두 번째 인증기가 된다). 그러니 그 뒤의 진짜 보호는
라우트마다 제 `auth=`(또는 `common/access_gate.py::AUTHN_REQUIRED_PREFIXES`
같은 접두 차단)가 한다. `scripts/probe_fake_bearer.py` 가 읽기 면 364자리를
가짜 `Authorization` 값으로 두드려 **0건**을 쟀다(세종 판정 P-273 참조) —
이 파일은 그 0 을 **다음에 누가 어떤 라우트의 `auth=` 를 빼면 빨강이 나는
자리**로 만든다. `pytest tests -q` 정본 회차에 이 파일이 들어 있으므로,
평소 시험 회차 자체가 이 회귀를 잡는다.

★★ [턴 AF 실측] `scripts/probe_fake_bearer.py` 는 어제 「364 · 0건」을 냈다고
보고됐지만, **문서에 적힌 그대로는 한 번도 돌 수 없었다** — ①
`django.setup()` 전에 `/app` 을 `sys.path` 에 안 얹어 `ModuleNotFoundError:
No module named 'config'` 로 죽는다 ② 가짜 값을 `Authorization` **헤더**가
아니라 `measure()` 의 **질의값** 자리에 넣고 있어서 실제 헤더는 한 번도
실리지 않았다. 이 턴에 그 스크립트 자체를 고치고 나서 다시 재니 **정말로
364 · 0건**이었다(고친 스크립트의 머리말과 `docs/agent/checkpoints/
turn-af/조율자.inbox/S.md` 에 실측 로그를 남겼다). 이 시험은 **그 뒤에도
같은 사실이 유지되는가**를 잰다 — 한 번의 초록을 되풀이해서 믿지 않는다.

판정식을 베끼지 않는다 (D-212)
-------------------------------
이 시험은 `scripts/gate_fake_bearer_regression.py` 의 `judge_rows()` /
`collect_rows()` 를 **그대로** 부른다(계측기 소스를 import 해서 그 함수를
직접 부른다 — `test_p237_onboarding_probe_billing.py` 와 같은 자리, D-369).
빨강 술어(`has_data`)·공개 선언(`PUBLIC_READ_BY_DESIGN`)은 그 게이트를 거쳐
`probe_read_surface` 의 것을 그대로 쓴다 — 이 파일에는 판정식이 **없다.**

★ **실계정·실토큰 0.** `django.test.Client` 는 로그인하지 않는다 — 이
제품이 계정당 동시 세션 하나뿐이라는 사정과 무관하다.

★★ 음성 대조 (지시 규약 §1의 5 — 「혼자 재면 통과」를 「고쳤다」로 적지 않는다)
--------------------------------------------------------------------------
`GateJudgeRowsCatchesMissingAuthTest` 가 그 대조다: `judge_rows()` 에
**`auth=` 가 없다고 흉내 낸 facts 행**을 직접 먹여, 그 행이 정확히 빨강으로
잡히는지를 **이 시험 스위트 안에서 매 회차마다** 확인한다. 게이트 판정
규칙이 나중에 누가 「전부 초록」쪽으로 약하게 고치면(예: 조건을 뒤집거나
허용목록을 통째로 먹는 실수) 이 시험이 먼저 빨강을 낸다.

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105 · D-224)
    skip·xfail·비활성화하지 말 것. 게이트 모듈을 못 찾으면 **회색**(skip
    with reason)으로 적는다 — 초록으로 숨기지 않는다(D-301).
"""
from __future__ import annotations

import sys
from pathlib import Path

from django.test import Client, TestCase

from tests.no_cache import NO_CACHE

#: 저장소 뿌리 후보 — `test_p237_onboarding_probe_billing.py::_REPO_ROOT_CANDIDATES`
#: 와 같은 자리(D-369, 눈 하나). 컨테이너에는 `backend/` 만 `/app` 으로 들어오므로
#: 소스 트리를 되짚는 경로가 안 통한다. `docker-compose` 가 `/repo` 로 저장소
#: 뿌리 모양을 얹어 준다(`scripts/` 가 그 아래 바인드 마운트돼 있다).
_REPO_ROOT_CANDIDATES = ("/repo",)


def _find_scripts_dir():
    """`scripts/gate_fake_bearer_regression.py` 가 사는 디렉터리 실경로. 없으면 `None`."""
    here = Path(__file__).resolve()
    roots = [*(Path(c) for c in _REPO_ROOT_CANDIDATES), *here.parents[1:4]]
    for root in roots:
        candidate = root / "scripts" / "gate_fake_bearer_regression.py"
        if candidate.is_file():
            return candidate.parent
    return None


def _import_gate_module():
    """게이트 소스를 **부른다**(베끼지 않는다 · D-369). 못 찾으면 `None`."""
    scripts_dir = _find_scripts_dir()
    if scripts_dir is None:
        return None
    sys.path.insert(0, str(scripts_dir))
    import gate_fake_bearer_regression as gate  # noqa: PLC0415

    return gate


class _GateModuleFixture(TestCase):
    """게이트 소스를 찾아 두고 못 찾으면 **회색(skip)** 으로 적는다 — 초록으로 숨기지 않는다."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gate = _import_gate_module()

    def setUp(self):
        super().setUp()
        if self.gate is None:
            self.skipTest(
                "scripts/gate_fake_bearer_regression.py 를 못 찾았다 — 컨테이너라면 "
                "docker-compose 의 `./scripts:/repo/scripts:ro` 마운트가 빠진 것이다. "
                "못 잰 것은 초록이 아니다 (D-301)")


# ═══════════════════════════════════════════════════════════════════════════
# ① ★★ 음성 대조 — 판정 규칙이 `auth=` 없는 자리를 실제로 빨강으로 잡는가
#    (지시 규약 §1의 5. 이 시험 스위트 안에 **영구히** 남는 대조다.)
# ═══════════════════════════════════════════════════════════════════════════
class GateJudgeRowsCatchesMissingAuthTest(_GateModuleFixture):
    """`judge_rows()` 는 순수 함수다(D-277) — 살아 있는 라우트를 안 건드리고
    facts 만으로 판정 규칙 자체를 시험한다."""

    def test_a_route_without_auth_is_flagged_red(self):
        """★★ 이 시험이 이 파일 전체의 근거다 — 못 잡으면 이 게이트는 아무것도
        안 잰 게이트다."""
        fake_rows = [
            {"method": "GET", "path": "/api/fake/protected", "status": 401,
             "data": False, "why": "401 [흉내]"},
            {"method": "GET", "path": "/api/fake/no-auth-oops", "status": 200,
             "data": True, "why": "★ auth= 가 없다고 흉내 낸 자리"},
        ]
        leaked = self.gate.judge_rows(fake_rows, public=set())
        self.assertEqual(
            [r["path"] for r in leaked], ["/api/fake/no-auth-oops"],
            "auth= 가 없다고 흉내 낸 자리를 게이트가 못 잡았다 — 판정 규칙이 죽었다")

    def test_a_gated_route_is_not_flagged(self):
        """정상 갈래 — 401 을 낸 자리는 빨강이 아니다."""
        fake_rows = [{"method": "GET", "path": "/api/fake/protected",
                     "status": 401, "data": False, "why": "401 [흉내]"}]
        self.assertEqual(self.gate.judge_rows(fake_rows, public=set()), [])

    def test_declared_public_route_is_not_flagged_even_with_data(self):
        """공개 선언은 **면제 목록이 아니라** 판단 기준(D-264 계열)이지만, 판정
        규칙이 그 표를 실제로 보는지는 확인한다."""
        fake_rows = [{"method": "GET", "path": "/api/fake/public-door",
                     "status": 200, "data": True, "why": "공개 선언 [흉내]"}]
        leaked = self.gate.judge_rows(fake_rows, public={"/api/fake/public-door"})
        self.assertEqual(leaked, [])

    def test_empty_facts_are_not_a_leak(self):
        self.assertEqual(self.gate.judge_rows([], set()), [])

    def test_fake_value_matches_the_probe_this_gate_regresses(self):
        """게이트와 탐침이 **같은** 「어디에도 없는 글자」를 쓰는지 — 두 벌로
        적으면 언젠가 갈린다(D-212)."""
        import probe_fake_bearer

        self.assertEqual(self.gate.FAKE, probe_fake_bearer.FAKE)
        self.assertNotIn(
            "real", self.gate.FAKE.lower(),
            "가짜 값이 실토큰처럼 보인다 — 실계정·실토큰 0 규약을 어긴다")


# ═══════════════════════════════════════════════════════════════════════════
# ② ★ 실측 — 읽기 면 전수를 가짜 헤더로 두드린다 (Django in-process, 로그인 0회)
# ═══════════════════════════════════════════════════════════════════════════
class FakeBearerReadSurfaceStaysClosedTest(_GateModuleFixture):
    """`collect_rows()` 로 **살아 있는 라우터 전수**를 두드리고, 그 결과를
    `judge_rows()` 로 가른다. 다음에 누가 `auth=` 를 빼면 여기서 빨강이 난다."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.gate is None:
            cls._rows = None
            return
        import logging

        import probe_read_surface as P
        from common.tenant_scope import _iter_ninja_apis, _join

        client = Client(raise_request_exception=False, **NO_CACHE)
        #: ★ 이 값(`gate.FAKE`)은 JWT 모양이 아니라서 `CustomJWTAuth` 가 매
        #:   요청마다 디코드 예외를 잡아 **긴 traceback 을 통째로 로그에** 찍는다
        #:   (§0.4 dj-core — 우리가 못 고친다). 판정과는 무관한 소음이고, 364건
        #:   전부에서 반복돼 시험을 몇 분씩 느리게 만든다. **판정 자체는 안 줄인다**
        #:   — 로거만 이 구간에서 잠깐 죽이고 끝나면 되살린다(finally).
        logging.disable(logging.CRITICAL)
        try:
            cls._rows = cls.gate.collect_rows(client, P, _iter_ninja_apis, _join)
        finally:
            logging.disable(logging.NOTSET)
        cls._public = set(getattr(P, "PUBLIC_READ_BY_DESIGN", ()) or ())

    def test_denominator_is_not_suspiciously_small(self):
        """★ 부작위 방지 — `collect_rows()` 가 빈 목록을 내면 아래 시험이
        **거짓으로 초록**이 된다(레지스트리를 못 찾았는데 「0 개 누출」로 읽힌다).
        분모 자체가 죽어 있지 않은지 먼저 본다(D-301 「검사 못함 ≠ 0건」)."""
        self.assertIsNotNone(self._rows)
        self.assertGreater(
            len(self._rows), 100,
            "읽기 라우트가 %d개뿐이다 — 레지스트리 순회가 깨졌을 수 있다. "
            "이 숫자가 작으면 아래 0건은 의미가 없다" % len(self._rows))

    def test_no_read_route_leaks_data_to_a_fake_bearer(self):
        """★★ 이 파일의 중심 시험 — 다음에 누가 `auth=` 를 빼면 여기서 빨강이 난다."""
        leaked = self.gate.judge_rows(self._rows, self._public)
        self.assertEqual(
            leaked, [],
            "★ 가짜 Authorization 으로 자료가 나온 자리가 있다 — 이 라우트들의 "
            "`auth=`(또는 관문 뒤의 다른 보호)가 빠졌다:\n  "
            + "\n  ".join("%s %s (%s · %s)" % (r["method"], r["path"], r["status"],
                                                r["why"]) for r in leaked))

    def test_every_row_was_actually_measured_not_skipped(self):
        """★ 모든 행이 `has_data()` 로 실제로 판정됐다 — `data` 칸이 누락된 행이
        섞이면 그 행은 아무 판정도 안 받은 채 통과한다."""
        for r in self._rows:
            self.assertIn("data", r, "%s %s 행에 data 칸이 없다" % (r.get("method"), r.get("path")))
            self.assertIsInstance(r["data"], bool)
