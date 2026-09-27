# -*- coding: utf-8 -*-
"""P-344 — 재시작 도구의 빨강은 두 문구다 · P-341 배포 도구 · P-339 익명 대조 (턴 AJ · 2026-09-25).

턴 AI 23:11 의 빨강(`restarts.jsonl` 2줄째)은 **재는 서버(gx-shell runserver)** 가 옛 코드였는데
도구는 「재시작했는데도 옛 코드」라고 적었다 — 다른 사고 · 다른 손. 각 모양으로 강제 실패시켜
문구가 갈리는지 본다(P-323 · 먼저 실패해 본다).

절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from django.test import SimpleTestCase


def _scripts() -> None:
    here = Path(__file__).resolve()
    for cand in ("/repo/scripts", str(here.parent.parent.parent / "scripts")):
        if Path(cand).is_dir():
            if cand not in sys.path:
                sys.path.insert(0, cand)
            return
    raise AssertionError("scripts/ 를 못 찾았다 — 재는 자리가 틀렸다")


#: `verify_live_code` 출력 모양 그대로(턴 AI 23:11 실측의 줄 머리).
def _live_out(product: str, shell: str) -> str:
    return "\n".join([
        "[LIVE] [입력] 가장 늦게 고친 backend 파일: x.py",
        "[LIVE] ── ① 제품 서버 gx-gunicorn-e ──",
        f"[LIVE] {product} 마스터 판정",
        "[LIVE] ── ② 재는 서버 gx-shell (runserver) ──",
        f"[LIVE] {shell} runserver 판정",
    ])


class RestartRedTwo(SimpleTestCase):
    def setUp(self) -> None:
        _scripts()
        import restart_live  # noqa: PLC0415
        self.r = restart_live
        self.base = dict(restarted={"gx-gunicorn-e": True, "gx-celery-e": True},
                         health_ok=True, celery_ready=True, smoke=0)

    def test_shell_stale_says_runserver_not_restart(self) -> None:
        stale = self.r.stale_parts(_live_out("OK  ", "FAIL"))
        self.assertEqual(stale, {"shell"})
        code, line = self.r.judge(**self.base, live_code=1, stale=stale)
        self.assertEqual(code, self.r.EXIT_FAIL)
        self.assertEqual(line, self.r.RED_SHELL)

    def test_product_stale_says_restart_did_not_take(self) -> None:
        stale = self.r.stale_parts(_live_out("FAIL", "OK  "))
        self.assertEqual(stale, {"product"})
        code, line = self.r.judge(**self.base, live_code=1, stale=stale)
        self.assertEqual(code, self.r.EXIT_FAIL)
        self.assertTrue(line.startswith(self.r.RED_PRODUCT))
        self.assertNotEqual(self.r.RED_PRODUCT, self.r.RED_SHELL)


class FrontRowRed(SimpleTestCase):
    """P-359 — ③ 프런트 배포본 빨강은 제 문구(재시작 대상이 아니다)."""

    def test_front_only_stale_says_redeploy(self) -> None:
        _scripts()
        import restart_live as r  # noqa: PLC0415
        out = "\n".join([_live_out("OK  ", "OK  "),
                         "[LIVE] ── ③ 프런트 배포본 C:/GuardianX/gx-spa ──",
                         "[LIVE] FAIL 옛 빌드"])
        stale = r.stale_parts(out)
        self.assertEqual(stale, {"front"})
        code, line = r.judge(restarted={"gx-gunicorn-e": True, "gx-celery-e": True},
                             health_ok=True, celery_ready=True, smoke=0, live_code=1, stale=stale)
        self.assertEqual((code, line), (r.EXIT_FAIL, r.RED_FRONT))

    def test_live_code_self_test_has_front_samples(self) -> None:
        _scripts()
        import verify_live_code as v  # noqa: PLC0415
        self.assertEqual(v.self_test(), v.EXIT_OK)
        self.assertEqual(v.judge_front(None, "x", 0)[0], v.EXIT_FAIL)


class DeploySelfTest(SimpleTestCase):
    """P-341 — 배포 도구의 판정 규칙과 복원 경로(임시 폴더 · 8500 은 안 건드린다)."""

    def test_self_test_passes(self) -> None:
        _scripts()
        import deploy_spa_8500  # noqa: PLC0415
        self.assertEqual(deploy_spa_8500.self_test(), deploy_spa_8500.EXIT_OK)

    def test_drill_catches_a_bad_backup(self) -> None:
        _scripts()
        import deploy_spa_8500 as d  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as tmp:
            live = Path(tmp) / "live"
            (live / "assets").mkdir(parents=True)
            (live / "index.html").write_text("a", encoding="utf-8")
            (live / "assets" / "index-X.js").write_text("b", encoding="utf-8")
            backup = Path(tmp) / "bk"
            d.replace_contents(live, backup)
            self.assertTrue(d.drill(backup, d.tree(live)))
            (backup / "assets" / "index-X.js").unlink()     # 백업이 한 파일 모자란다
            self.assertFalse(d.drill(backup, d.tree(live)))


class SmokeAnonymous(SimpleTestCase):
    """P-339 ④ — 읽기 문이 익명에 열리면 빨강."""

    def test_open_read_door_is_red(self) -> None:
        _scripts()
        import smoke_live as s  # noqa: PLC0415
        ok3 = [s.step("건강", 200), s.step("로그인", 200), s.step("읽기", 200)]
        self.assertEqual(s.judge(ok3 + [s.step("익명", 200, expect=s.ANON_EXPECT)], 1.0)[0],
                         s.EXIT_FAIL)
        self.assertEqual(s.judge(ok3 + [s.step("익명", 401, expect=s.ANON_EXPECT)], 1.0)[0],
                         s.EXIT_OK)

    def test_smoke_names_read_from_file_not_overriding_env(self) -> None:
        _scripts()
        import smoke_live as s  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / ".env.gates"
            f.write_text("GX_SMOKE_USER=u\nGX_SMOKE_PASSWORD=p!\n", encoding="utf-8")
            env = {"GX_SMOKE_USER": "already"}
            took = s.load_smoke_names(env, f)
        self.assertEqual(took, ["GX_SMOKE_PASSWORD"])
        self.assertEqual(env["GX_SMOKE_USER"], "already")
