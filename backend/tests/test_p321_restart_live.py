# -*- coding: utf-8 -*-
"""P-321 · P-315 — **재적재는 restart 이고, 재시작 뒤에는 서버를 잰다** (턴 AI 전).

이 시험이 무엇을 메우나
-----------------------
`scripts/restart_live.py` 는 「오늘 다시 세웠고 섰다」를, `scripts/smoke_live.py` 는
「서버가 받는다」를 잰다. 이 파일은 **그렇게 판정하도록 배선돼 있다**를 잰다 — 서버를
건드리지 않는다(docker 도 HTTP 도 부르지 않는다).

만든 사고 [실측 2026-09-24 · 턴 AH · OPS-26]
--------------------------------------------
`backend/` 를 고치고 gunicorn 을 안 세웠다 → 반쪽 서버가 `/api/dsm/cameras/pulse` 500.
그 서버는 **건강 200 · events 200** 이었다. 세종이 처음 허용한 `kill -HUP 1` 은
`preload_app = True` 에서 코드를 다시 안 읽는다 — 대표 결정 「HUP 는 restart」(09-24).
그래서 재시작 판정은 건강·스모크가 초록이어도 **옛 코드면 빨강**이어야 한다.

절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from django.test import SimpleTestCase


def _scripts() -> Path:
    here = Path(__file__).resolve()
    for cand in ("/repo/scripts", str(here.parent.parent.parent / "scripts")):
        if Path(cand).is_dir():
            if cand not in sys.path:
                sys.path.insert(0, cand)
            return Path(cand)
    raise AssertionError("scripts/ 를 못 찾았다 — 재는 자리가 틀렸다")


def _restart():
    _scripts()
    import restart_live  # noqa: PLC0415

    return restart_live


def _smoke():
    _scripts()
    import smoke_live  # noqa: PLC0415

    return smoke_live


def _all_ok(r) -> dict:
    return {c: True for c in r.CONTAINERS}


class TheIncidentIsRed(SimpleTestCase):
    """★ 출생 표본 — 그날의 모양. 이것이 초록이면 이 도구는 사고를 절차로 굳힌다."""

    def test_old_code_is_red_even_when_health_and_smoke_are_green(self) -> None:
        r = _restart()
        code, why = r.judge(restarted=_all_ok(r), health_ok=True, celery_ready=True,
                            live_code=r.EXIT_FAIL, smoke=r.EXIT_OK)
        self.assertEqual(r.EXIT_FAIL, code, why)
        self.assertIn("옛 코드", why)

    def test_login_200_without_token_is_red(self) -> None:
        """[실측 2026-09-17·18] 제품은 「다른 세션이 있다」를 200 + success:false 로 낸다."""
        s = _smoke()
        code, _ = s.judge([s.step("건강", 200), s.step("로그인", 200, False, "토큰 없음"),
                           s.step("읽기", None, why="토큰 없음")], 1.0)
        self.assertEqual(s.EXIT_FAIL, code)

    def test_dead_server_is_red_not_gray(self) -> None:
        s = _smoke()
        code, _ = s.judge([s.step("건강", 0), s.step("로그인", None, why="x"),
                           s.step("읽기", None, why="x")], 1.0)
        self.assertEqual(s.EXIT_FAIL, code)


class GrayIsNotGreen(SimpleTestCase):
    def test_v_lock_skips_login_and_is_gray(self) -> None:
        s = _smoke()
        code, _ = s.judge([s.step("건강", 200), s.step("로그인", None, why="V"),
                           s.step("읽기", None, why="V")], 1.0)
        self.assertEqual(s.EXIT_UNDECIDABLE, code)

    def test_gray_smoke_makes_the_restart_gray(self) -> None:
        r = _restart()
        code, _ = r.judge(restarted=_all_ok(r), health_ok=True, celery_ready=True,
                          live_code=r.EXIT_OK, smoke=r.EXIT_UNDECIDABLE)
        self.assertEqual(r.EXIT_UNDECIDABLE, code)

    def test_no_reason_restarts_nothing(self) -> None:
        """사유 없는 재시작은 수로 못 센다 — docker 를 부르기 **전에** 회색으로 끝난다."""
        r = _restart()
        called = []
        real = r._run
        r._run = lambda *a, **k: called.append(a) or real(*a, **k)
        try:
            self.assertEqual(r.EXIT_UNDECIDABLE, r.main(["--reason", "  "]))
        finally:
            r._run = real
        self.assertEqual([], called)


class OnlyTheTwoContainersThePolicyNames(SimpleTestCase):
    """도구가 다시 세우는 통 == 헤드리스 허용 목록의 두 줄(D-479 짝) · 그 밖은 없다."""

    def test_containers_are_exactly_the_policy_pair(self) -> None:
        r = _restart()
        self.assertEqual(("gx-gunicorn-e", "gx-celery-e"), r.CONTAINERS)

    def test_headless_allow_list_carries_each_restart_line(self) -> None:
        r = _restart()
        conf = _scripts() / "loop" / "headless.settings.json"
        perms = json.loads(conf.read_text(encoding="utf-8"))["permissions"]
        for c in r.CONTAINERS:
            self.assertIn(f"Bash(docker restart {c})", perms["allow"])
        self.assertNotIn("Bash(docker restart*)", perms["deny"],
                         "일반 거부가 남아 있으면 허용 두 줄이 헤드리스에서 막힌다")


class TheLineCarriesNoSecret(SimpleTestCase):
    def test_line_is_json_and_has_no_value_fields(self) -> None:
        r = _restart()
        line = r.make_line(at="2026-09-24T21:36:55+09:00", reason="P-321", commit="32e6ca5",
                           dirty_backend=0, restarted=_all_ok(r), health_ok=True,
                           celery_ready=True, live_code=0, smoke=0, code=0, verdict="초록")
        text = json.dumps(line, ensure_ascii=False)
        for word in ("password", "token", "PASSWORD", "SECRET", "env"):
            self.assertNotIn(word, text)
        self.assertTrue(line["planned"])

    def test_smoke_account_needs_both_halves(self) -> None:
        s = _smoke()
        env = {"GX_SMOKE_USER": "u", "GX_ROUTE_USER": "r", "GX_ROUTE_PASSWORD": "p"}
        self.assertEqual("r", s.pick_account(env)[0], "반쪽 짝(비밀번호 없음)은 안 쓴다")
        env["GX_SMOKE_PASSWORD"] = "q"
        self.assertEqual("u", s.pick_account(env)[0])


class TheSelfTestCanFail(SimpleTestCase):
    """★★ P-319 · P-323 — 자기시험은 **그날 실제로 일어난 모양으로** 먼저 실패해 본다."""

    def test_both_self_tests_pass_as_built(self) -> None:
        self.assertEqual(0, _restart().self_test())
        self.assertEqual(0, _smoke().self_test())

    def test_restart_self_test_fails_when_judge_trusts_health(self) -> None:
        """망가뜨림 = 「건강 200 이면 섰다」 — 그날 HUP 을 믿었다면 쓰였을 눈."""
        r = _restart()
        real = r.judge

        def trusts_health(*, restarted, health_ok, celery_ready, live_code, smoke):
            return (r.EXIT_OK, "섰다") if health_ok else (r.EXIT_FAIL, "안 섰다")

        r.judge = trusts_health
        try:
            got = r.self_test()
        finally:
            r.judge = real
        self.assertEqual(1, got, "건강만 보는 판정을 자기시험이 못 잡는다")

    def test_smoke_self_test_fails_when_judge_reads_only_status(self) -> None:
        """망가뜨림 = 「200 이면 로그인 성공」 — 09-17 에 게이트가 실제로 그렇게 읽었다."""
        s = _smoke()
        real = s.judge

        def status_only(steps, elapsed, deadline=s.DEADLINE_S):
            if any(x["status"] not in (None, 200) for x in steps):
                return s.EXIT_FAIL, "빨강"
            if any(x["status"] is None for x in steps):
                return s.EXIT_UNDECIDABLE, "회색"
            return s.EXIT_OK, "초록"

        s.judge = status_only
        try:
            got = s.self_test()
        finally:
            s.judge = real
        self.assertEqual(1, got, "토큰 없는 200 을 자기시험이 못 잡는다")
