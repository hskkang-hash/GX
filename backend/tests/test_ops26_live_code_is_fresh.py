# -*- coding: utf-8 -*-
"""OPS-26 — **요청을 받는 코드가 저장소의 코드와 같은 시점인가** (턴 AH · P-314 ②).

이 시험이 무엇을 메우나
-----------------------
게이트(`scripts/verify_live_code.py`)는 **「오늘 그랬다」**를 잰다 — 지금 도는 서버가
신선한가. 이 시험은 **「그렇게 판정하도록 배선돼 있다」**를 잰다 — 기준 시각을
**마스터**로 잡는가. 게이트만 있으면 내일 누가 기준을 워커로 바꿔도 그 게이트는
**초록**을 낸다(HUP 뒤 워커는 늘 새것이다) — 그리고 그 초록은 거짓이다.

만든 사고 [실측 2026-09-24]
---------------------------
`backend/` 를 고치고 gunicorn 을 안 세웠다 → `/api/dsm/cameras/pulse` 500 ·
`ImportError: cannot import name 'exclude_not_counted'`. 전량 2,182건은 전부 초록이었다.
**시험은 매번 새로 import 하므로 이 고장을 구조적으로 못 잡는다** — 그래서 이 파일은
서버를 재지 않고 **판정 규칙**을 잰다. 서버는 게이트가 잰다.

★★ `preload_app = True` [실측 · `/app/gunicorn.conf.py:101`]
  앱이 마스터에 올라가고 워커는 복제다. `kill -HUP 1` 은 워커만 새로 띄운다 —
  **코드는 다시 안 읽는다.** 그래서 기준은 마스터다.

절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import sys
from pathlib import Path

from django.test import SimpleTestCase


def _gate():
    """게이트 모듈. 마운트가 여럿이라 경로 후보를 둘 둔다(`test_authn_gap_closed` 선례)."""
    here = Path(__file__).resolve()
    for cand in ("/repo/scripts", str(here.parent.parent.parent / "scripts")):
        if cand not in sys.path and Path(cand).is_dir():
            sys.path.insert(0, cand)
    import verify_live_code  # noqa: PLC0415

    return verify_live_code


T0 = 1_790_000_000.0


class TheIncidentIsRed(SimpleTestCase):
    """★ 출생 표본 — 그날의 모양. 이것이 초록이면 이 절 전체가 무효다."""

    def test_old_master_with_fresh_workers_is_old_code(self) -> None:
        g = _gate()
        code, verdict, ref = g.judge(newest=T0 + 50, master=T0,
                                     workers=[T0 + 100, T0 + 120], preload=True)
        self.assertEqual(
            g.EXIT_FAIL, code,
            "preload 서버에서 워커가 새것이라고 신선하다고 읽었다 — HUP 뒤의 거짓 초록. "
            "판정문: %s · 기준: %s" % (verdict, ref))
        self.assertIn("마스터", ref, "기준이 마스터가 아니다")

    def test_unknown_preload_is_judged_strictly(self) -> None:
        """모르면 **엄한 쪽**. 틀려도 빨강 쪽으로 틀린다."""
        g = _gate()
        code, _v, _r = g.judge(newest=T0 + 50, master=T0, workers=[T0 + 100],
                               preload=None)
        self.assertEqual(g.EXIT_FAIL, code)


class TheForgottenMeasuringServerIsRed(SimpleTestCase):
    """★ 출생 표본 ② — **같은 사고가 두 번째 서버에서 났다** [실측 2026-09-24].

    조율자가 gx-shell 안에 `runserver 0.0.0.0:8000 --noreload` 를 띄우고 잊었다. 3시간 57분
    동안 한 번도 다시 안 읽었고, 게이트들이 기본으로 두드리는 곳(`GX_API`)이 그 서버라
    `verify_contract_route_reach` 가 pulse 500 을 받아 **GA FAIL 1** 이 났다. 이 게이트를
    처음 지었을 때는 gunicorn 만 봤다 — **재는 서버가 옛 코드면 잰 수가 거짓이다.**
    """

    def test_noreload_runserver_older_than_the_code_is_red(self) -> None:
        g = _gate()
        code, verdict = g.judge_runserver(
            T0 + 5_500, [[40989, 40983, T0,
                          "python manage.py runserver 0.0.0.0:8000 --noreload"]])
        self.assertEqual(g.EXIT_FAIL, code, "잊힌 재는 서버를 신선하다고 읽었다: " + verdict)
        self.assertIn("--noreload", verdict, "왜 스스로 안 고쳐지는지를 말하지 않는다")

    def test_no_runserver_is_green_not_gray(self) -> None:
        """없으면 옛 코드일 것도 없다 — 회색은 재려던 것을 **못 잰** 때만이다."""
        g = _gate()
        code, _v = g.judge_runserver(T0, [])
        self.assertEqual(g.EXIT_OK, code)

    def test_autoreload_new_child_is_the_reference(self) -> None:
        g = _gate()
        code, _v = g.judge_runserver(
            T0 + 50, [[10, 1, T0, "python manage.py runserver"],
                      [11, 10, T0 + 60, "python manage.py runserver"]])
        self.assertEqual(g.EXIT_OK, code, "자동 재적재의 새 자식을 안 보고 옛 부모로 판정했다")


class TheGateIsNotAFalseRedMachine(SimpleTestCase):
    """음성 대조 — 빨강만 내는 게이트는 사람이 끈다. 꺼진 게이트는 없는 게이트보다 나쁘다."""

    def test_a_restarted_server_is_fresh(self) -> None:
        g = _gate()
        code, _v, _r = g.judge(newest=T0 + 50, master=T0 + 60, workers=[T0 + 61],
                               preload=True)
        self.assertEqual(g.EXIT_OK, code)

    def test_confirmed_non_preload_trusts_the_workers(self) -> None:
        """preload 가 **아니라고 확인되면** HUP 이 정말 코드를 다시 읽는다 — 워커가 기준."""
        g = _gate()
        code, _v, ref = g.judge(newest=T0 + 50, master=T0, workers=[T0 + 100],
                                preload=False)
        self.assertEqual(g.EXIT_OK, code, "비-preload 에서 HUP 을 믿지 않았다 — 거짓 빨강")
        self.assertIn("워커", ref)

    def test_no_master_is_gray_not_green(self) -> None:
        g = _gate()
        code, _v, _r = g.judge(newest=T0, master=None, workers=[], preload=True)
        self.assertEqual(g.EXIT_UNDECIDABLE, code, "못 잰 것을 신선하다고 적었다")


class TheRunningConfigIsReadable(SimpleTestCase):
    """게이트가 **지금 저장소의** gunicorn 설정을 읽어 낼 수 있는가.

    ⚠ `True` 를 못박지 않는다. 누가 일부러 preload 를 끄는 날 이 시험이 빨개지면
      안 된다 — 그날은 HUP 이 정말 듣게 되는 날이고, 게이트는 그걸 읽어 워커를
      기준으로 삼는다. 여기서 재는 것은 「읽을 수 있다」(None 이 아니다)뿐이다.
    """

    def test_repo_gunicorn_conf_states_preload(self) -> None:
        g = _gate()
        here = Path(__file__).resolve()
        cands = [Path("/app/gunicorn.conf.py"), here.parent.parent / "gunicorn.conf.py"]
        conf = next((p for p in cands if p.is_file()), None)
        self.assertIsNotNone(conf, "gunicorn.conf.py 를 못 찾았다 — 게이트가 기준을 못 정한다")
        got = g.preload_from(conf.read_text(encoding="utf-8"), "")
        self.assertIsNotNone(
            got, "게이트가 gunicorn.conf.py 에서 preload 여부를 못 읽는다 — 그러면 언제나 "
                 "엄한 쪽(마스터)으로 판정해 비-preload 에서 거짓 빨강이 난다")


class TheSelfTestCanFail(SimpleTestCase):
    """★★ P-319 — **자기시험은 먼저 실패해 본다.** 말이 아니라 시험으로 못박는다.

    이 저장소의 다른 게이트(`verify_ui_copy`)에서 `ok = False` 일곱 개가 **초기화도
    읽는 데도 없어** 자기시험이 언제나 「통과」였다(턴 AH). 실패할 수 없는 자기시험은
    자기시험이 아니다 — 그래서 **판정을 그날의 함정 그대로 망가뜨려** 자기시험이
    정말 1 을 돌려주는지 본다.

    ⚠ 망가뜨림은 **실제로 일어났던 모양**이어야 한다. 아무렇게나 망가뜨리면 「표본이
      약하다」와 「망가뜨림이 엉뚱하다」를 못 가른다(P-320 표본을 만들다 첫 망가뜨림이
      통과해서 배웠다). 여기의 망가뜨림은 「preload 를 안 묻고 워커와 견준다」 —
      그날 HUP 을 믿었다면 쓰였을 눈이다.
    """

    def test_self_test_passes_as_built(self) -> None:
        self.assertEqual(0, _gate().self_test())

    def test_self_test_fails_when_judge_trusts_workers(self) -> None:
        g = _gate()
        real = g.judge

        def trusts_workers(newest, master, workers, preload):
            if master is None:
                return real(newest, master, workers, preload)
            ref = min(workers) if workers else master
            if newest - ref > g.TOLERANCE_S:
                return g.EXIT_FAIL, "옛 코드", "워커"
            return g.EXIT_OK, "신선", "워커"

        g.judge = trusts_workers
        try:
            got = g.self_test()
        finally:
            g.judge = real
        self.assertEqual(
            1, got, "판정을 워커 기준으로 망가뜨렸는데 자기시험이 통과했다 — "
                    "실패할 수 없는 자기시험이다")
