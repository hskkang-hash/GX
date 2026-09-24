# -*- coding: utf-8 -*-
"""P-311 — **카드 진행률 걷기는 「재기」가 아니라 「짓기」다** (턴 AI · 차선 F).

이 시험이 무엇을 메우나
-----------------------
게이트(`scripts/verify_onboarding_walk.py`)는 **「6 버킷의 진행률이 얼마인가」**를
잰다. 이 시험은 **「그렇게 판정하도록 배선돼 있다」**를 잰다 — 서버도 네트워크도
건드리지 않는다(순수 함수만 부른다 · D-277). 서버를 실제로 걷는 것은 이 턴이 아니라
V 의 첫 실측이다(P-311 · 「지은 뒤의 첫 수가 첫 수다」) — 이 시험은 그 전에 **판정
규칙이 옳은지**를 먼저 확인해 둔다.

만든 사고 [WO-12 §10 P-311 · 실측 2026-09-24]
----------------------------------------------
`verify_onboarding_walk --api` 는 로그인도 안 하고 `/api/dsm` 을 **인증 없이** 한 번
읽었다 — 「재면 나오는 수」가 아니라 **아직 안 지은 것**이었다. 그 자리에서 가장
위험한 다음 실수는 「못 잰 것을 0 으로 적는 것」이다: 로그인 200 인데 토큰이 없는
자리, 진행률 문이 아직 없는 자리, 분모를 못 셌는데 0/0 으로 접히는 자리 — 셋 다
**회색**이어야 하는데, 한 곳이라도 0 으로 접히면 「역할 하나 진행률 0%」라는 거짓
빨강(또는 거짓 초록)이 보고서에 실린다.

절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import sys
from pathlib import Path

from django.test import SimpleTestCase


def _scripts() -> Path:
    """게이트 모듈. 마운트가 여럿이라 경로 후보를 둘 둔다(`test_ops26_*` 선례)."""
    here = Path(__file__).resolve()
    for cand in ("/repo/scripts", str(here.parent.parent.parent / "scripts")):
        if Path(cand).is_dir():
            if cand not in sys.path:
                sys.path.insert(0, cand)
            return Path(cand)
    raise AssertionError("scripts/ 를 못 찾았다 — 재는 자리가 틀렸다")


def _gate():
    _scripts()
    import verify_onboarding_walk as m  # noqa: PLC0415

    return m


# ═══════════════════════════════════════════════════════════════════════════
# 0/N 과 회색을 가른다 — **못 잰 것을 0 으로 적지 않는다** (D-301)
# ═══════════════════════════════════════════════════════════════════════════
class ZeroIsNotTheSameAsGray(SimpleTestCase):
    """★ 출생 표본 — 이 구분이 없으면 「역할 하나 진행률 0%」가 거짓으로 보고된다."""

    def test_measured_zero_of_seven_is_ok_not_gray(self) -> None:
        g = _gate()
        code, why = g.judge_progress_response(200, {"total": 7, "done": 0})
        self.assertEqual(g.EXIT_OK, code, "쟀는데(분모 7·완료 0) 회색으로 읽었다")
        self.assertEqual("0/7", why)

    def test_missing_total_is_gray_not_zero_of_zero(self) -> None:
        """★ 그날의 다음 실수가 될 뻔한 자리 — `total` 이 없으면 0/0 으로 접지 않는다."""
        g = _gate()
        code, why = g.judge_progress_response(200, {})
        self.assertEqual(g.EXIT_UNDECIDABLE, code,
                         "분모를 못 셌는데 0/0 으로 접어 쟀다고 읽었다: " + why)

    def test_zero_of_seven_and_gray_are_different_codes(self) -> None:
        g = _gate()
        measured = g.judge_progress_response(200, {"total": 7, "done": 0})[0]
        gray = g.judge_progress_response(200, {})[0]
        self.assertNotEqual(measured, gray, "0/7 과 회색이 같은 판정으로 접혔다")

    def test_progress_door_missing_is_gray_not_a_failure(self) -> None:
        """P-311 — 「진행률 문 없으면 없다를 실측으로」. 있었다(api_f.py 실측) — 그래도
        사라지는 날(리팩터)엔 실패가 아니라 **회색**으로 말해야 한다."""
        g = _gate()
        code, why = g.judge_progress_response(404, {})
        self.assertEqual(g.EXIT_UNDECIDABLE, code, "문이 없는 것을 실패로 읽었다: " + why)


class LoginTwoHundredWithoutATokenIsGray(SimpleTestCase):
    """★ 출생 표본 — 「로그인 200 인데 토큰 없음」은 회색이지 빨강도 0 도 아니다.

    제품은 「다른 곳에 활성 세션이 있다」를 **200 + success:false** 로 낸다
    (`verify_route_alive._extract_token` 머리말 · 실측 2026-09-17·18). `login()` 이
    이미 그 갈래를 걸러 `None` 하나로 묶어 준다 — `walk_all_roles` 는 `None` 을
    받으면 그 계정이 덮는 버킷 전부를 **회색**으로 적어야 한다(0 으로 적지 않는다).
    """

    def test_no_token_marks_every_bucket_of_that_account_as_gray(self) -> None:
        g = _gate()
        real_login = g.login

        def login_returns_none(_api, _user, _password):
            # 제품이 200 을 냈어도(다른 세션 있음 등) login() 은 토큰을 못 뽑으면 None.
            return None

        g.login = login_returns_none
        try:
            results = g.walk_all_roles(
                "http://x", {"U1": ("gxseed_u1_operator", ""),
                            "U3": ("gxseed_u1_operator", "U3")})
        finally:
            g.login = real_login

        for bucket in ("U1", "U3"):
            self.assertEqual(g.EXIT_UNDECIDABLE, results[bucket]["code"],
                             "%s: 토큰 없는 로그인을 회색이 아니게 읽었다" % bucket)
            self.assertIsNone(results[bucket]["total"], "못 잰 total 을 값으로 채웠다")
            self.assertIsNone(results[bucket]["done"], "못 잰 done 을 값으로 채웠다")

    def test_missing_password_is_gray_and_never_calls_login(self) -> None:
        """비밀번호가 없으면 **로그인을 시도조차 하지 않는다** — 빈 문자열로 때리지 않는다."""
        g = _gate()
        real_login = g.login
        called = []
        g.login = lambda *a, **k: called.append(a) or None
        try:
            results = g.walk_all_roles("http://x", {"U1": ("gxseed_u1_operator", "")})
        finally:
            g.login = real_login
        self.assertEqual([], called, "비밀번호 없이 로그인을 시도했다")
        self.assertEqual(g.EXIT_UNDECIDABLE, results["U1"]["code"])


# ═══════════════════════════════════════════════════════════════════════════
# 로그인 계획 — 6 버킷을 실재 계정으로 덮는다 (역할 4 + 페르소나 2)
# ═══════════════════════════════════════════════════════════════════════════
class RoleWalkPlanCoversSixBucketsWithRealAccounts(SimpleTestCase):
    def test_plan_covers_all_six_expected_buckets(self) -> None:
        g = _gate()
        src = g.ONBOARDING.read_text(encoding="utf-8")
        plan = g.role_walk_plan(src, g.CONFIRMED_ROLE_ACCOUNTS,
                                reserve=("U5", g.U5_RESERVE_ACCOUNT))
        missing = [b for b in g.EXPECTED_BUCKETS if b not in plan]
        self.assertEqual([], missing, "계획이 6 버킷을 다 못 덮는다: %s" % missing)

    def test_u6_uses_the_reserve_account_not_u5s_own(self) -> None:
        """U6(외부 연계)을 U5 본계정으로 열면 U5 자신의 온보딩 실측과 섞인다."""
        g = _gate()
        src = g.ONBOARDING.read_text(encoding="utf-8")
        plan = g.role_walk_plan(src, g.CONFIRMED_ROLE_ACCOUNTS,
                                reserve=("U5", g.U5_RESERVE_ACCOUNT))
        user, persona = plan["U6"]
        self.assertEqual(g.U5_RESERVE_ACCOUNT, user)
        self.assertNotEqual(plan["U5"][0], user,
                            "U5 본계정과 U6 페르소나 계정이 같다 — 실측이 섞인다")
        self.assertEqual("U6", persona)


class TheSelfTestCanFail(SimpleTestCase):
    """★★ P-319 · P-323 — 자기시험은 **그날 실제로 일어난 모양으로** 먼저 실패해 본다.

    망가뜨림 = 「분모를 못 세면 0/0 으로 접는다」— P-311 이 막으려던 바로 그 실수다
    (WO-12 §10: 「그 전엔 회색 유지 · 0 이라 적지 않는다」).
    """

    def test_self_test_passes_as_built(self) -> None:
        self.assertEqual(0, _gate().self_test())

    def test_self_test_fails_when_missing_denominator_is_folded_into_zero(self) -> None:
        g = _gate()
        real = g.judge_progress_response

        def folds_missing_total_into_zero(status, body):
            if status == 200:
                total = body.get("total") if isinstance(body, dict) else None
                done = body.get("done") if isinstance(body, dict) else None
                if not isinstance(total, int):
                    total = 0
                if not isinstance(done, int):
                    done = 0
                return g.EXIT_OK, "%d/%d" % (done, total)
            return real(status, body)

        g.judge_progress_response = folds_missing_total_into_zero
        try:
            got = g.self_test()
        finally:
            g.judge_progress_response = real
        self.assertEqual(
            1, got, "분모를 못 세면 0/0 으로 접는 판정을 자기시험이 못 잡는다 — "
                    "「못 잰 것을 0 으로 적지 않는다」(D-301)가 안 지켜진다")

    def test_self_test_fails_when_five_of_six_measured_reads_as_ok(self) -> None:
        """망가뜨림 = 「접기(combine_role_codes)가 회색 하나를 무시하고 초록을 낸다」 —
        P-311 이 못박은 그 문장 그대로다: 「여섯을 다 재야 첫 수다 · 0 이라 적지 않는다」."""
        g = _gate()
        real = g.combine_role_codes

        def ignores_a_single_gray(results):
            codes = [r.get("code") for r in results.values()]
            if any(c == g.EXIT_FAIL for c in codes):
                return real(results)
            return g.EXIT_OK, "무시하고 초록"

        g.combine_role_codes = ignores_a_single_gray
        try:
            got = g.self_test()
        finally:
            g.combine_role_codes = real
        self.assertEqual(
            1, got, "다섯만 재고 하나가 회색인데 접기가 초록을 내는 것을 "
                    "자기시험이 못 잡는다")
