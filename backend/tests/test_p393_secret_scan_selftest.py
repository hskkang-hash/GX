# -*- coding: utf-8 -*-
"""P-393 (세종 판정 · P-203 예외) — SEC-05 비밀 스캔 게이트 자기시험의 표본을 고정한다.

턴 AM 에서 GA 판정기(`verify_ga_readiness.py`)가 SEC-05 를 FAIL 로 냈다:
`scripts/verify_secret_scan.py` 의 자기시험이 무작위로 심은 키를 부하(전량 시험과
병렬) 중에 두 번 못 잡았고, 단독으로 돌리면 통과했다. 세종 판정: 「부하 중 흔들리는
자기시험은 자기시험이 아니다 — 표본은 고정한다」.

`verify_secret_scan.py` 는 이제 무작위 32자 하나 대신 **형식별 고정 표본 5개**
(`FIXED_PLANT_SAMPLES`)를 심는다. 이 시험이 지키는 것 셋:
  ① 표본 5개가 전부 잡힌다.
  ② 같은 형식의 깨끗한(플레이스홀더) 표본은 안 잡힌다.
  ③ 부하 중(스레드 여러 개 동시)에도 결과가 매번 같다 — 이번 SEC-05 FAIL 의 재현 시험.

★ gitleaks 실행 파일(`tools/gitleaks.exe`)과 저장소 루트 `.gitleaks.toml` 은
  gx-shell 에 마운트되지 않는다 — `/repo` 아래에는 `backend`·`frontend`·`scripts`·
  `docs` 만 붙는다(`docker inspect gx-shell` [실측 2026-09-29]). 그래서 컨테이너
  안에서는 **실제 스캐너를 돌리는 시험**(①·②·부분적으로 ③)을 스킵하고 사유를
  남긴다 — 회색은 초록이 아니다(D-301). 그 갈래는 호스트의
  `python scripts/verify_secret_scan.py --self-test` 가 잰다.
  컨테이너 안에서도 실제로 잴 수 있는 것은 **표본 생성 자체가 결정적인가**다 —
  파이썬 값 비교뿐이라 스캐너가 없어도 잰다. 이번에 고친 것(무작위 → 고정)이
  바로 이 성질이라, 이 부분은 gx-shell 안에서도 진짜 초록을 낸다.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def _scripts_dir() -> Path:
    """호스트에서는 `<repo>/scripts`, `gx-shell` 안에서는 `/repo/scripts` (기존
    `test_no_secret_echo.py` · `test_p3xx` 계열이 쓰는 자리 찾기를 그대로 따른다).
    """
    here = Path(__file__).resolve()
    for cand in [p / "scripts" for p in here.parents] + [Path("/repo/scripts")]:
        if (cand / "verify_secret_scan.py").is_file():
            return cand
    return Path("/repo/scripts")


class FixedSampleDeterminismTest(unittest.TestCase):
    """P-393 핵심 — 표본 생성기가 **무작위가 아니라 고정**인가. 스캐너 없이도
    잴 수 있다(파이썬 값 비교뿐) — gx-shell 안에서도 실제 초록을 낸다.
    """

    def setUp(self) -> None:
        scripts = _scripts_dir()
        if not scripts.is_dir():
            self.skipTest(f"scripts/ 를 못 찾았다 — {scripts} (이 자리에서는 못 잰다)")
        sys.path.insert(0, str(scripts))

    def test_module_constant_has_five_distinct_formats(self) -> None:
        from verify_secret_scan import FIXED_PLANT_SAMPLES

        self.assertEqual(
            len(FIXED_PLANT_SAMPLES), 5,
            "고정 표본은 형식별로 5개여야 한다(P-393 지시)",
        )
        formats = {s["format"] for s in FIXED_PLANT_SAMPLES}
        self.assertEqual(
            len(formats), 5,
            "다섯 표본의 형식이 서로 겹친다 — 형식별 하나씩이어야 한다",
        )
        for s in FIXED_PLANT_SAMPLES:
            self.assertIn("content", s)
            self.assertIn("clean_content", s)
            self.assertNotEqual(
                s["content"], s["clean_content"],
                f"{s['format']} — 양성·음성 내용이 같다",
            )

    def test_generator_is_stable_across_reimport(self) -> None:
        """같은 함수를 다시 부르면 같은 값이 나오는가 — 무작위였다면 이 시험은
        사실상 항상 실패했을 것이다(62진 32자가 우연히 같을 확률은 무시할 만하다).
        """
        from verify_secret_scan import FIXED_PLANT_SAMPLES, _fixed_plant_samples

        first = _fixed_plant_samples()
        second = _fixed_plant_samples()
        self.assertEqual(
            first, second,
            "같은 함수를 두 번 불렀는데 표본이 달라졌다 — 아직 무작위 값이 섞여 있다",
        )
        self.assertEqual(
            FIXED_PLANT_SAMPLES, first,
            "모듈 상수(FIXED_PLANT_SAMPLES)가 함수의 산출과 어긋난다",
        )

    def test_generation_is_identical_under_concurrent_load(self) -> None:
        """부하 재현(스캐너 없이) — 스레드 8개가 동시에 표본을 만들어도 전부 같은
        값을 내는가. 턴 AM 의 SEC-05 FAIL 은 바로 이 자리(심는 값 자체)의 우연이
        부하 중 표면화된 것이라는 가설을 코드 수준에서 막는다.
        """
        from verify_secret_scan import _fixed_plant_samples

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _i: _fixed_plant_samples(), range(32)))

        baseline = results[0]
        for i, r in enumerate(results[1:], start=1):
            self.assertEqual(
                r, baseline,
                f"{i}번째 동시 호출이 기준과 다르다 — 부하 중 표본이 흔들린다",
            )


class SecretScanSelfTestGateTest(unittest.TestCase):
    """실제 스캐너로 표본이 잡히는지 — **스캐너와 설정이 있는 자리에서만** 잰다.
    gx-shell 은 `tools/gitleaks.exe`·`.gitleaks.toml` 을 마운트하지 않으므로
    여기서는 스킵하고, 실제 판정은 호스트의
    `python scripts/verify_secret_scan.py --self-test` 가 낸다(회색 ≠ 초록 · D-301).
    """

    def setUp(self) -> None:
        scripts = _scripts_dir()
        if not scripts.is_dir():
            self.skipTest(f"scripts/ 를 못 찾았다 — {scripts} (이 자리에서는 못 잰다)")
        sys.path.insert(0, str(scripts))

        from verify_secret_scan import CONFIG, find_scanner

        self.exe = find_scanner()
        self.config_ok = CONFIG.is_file()
        if self.exe is None or not self.config_ok:
            self.skipTest(
                "스캐너(tools/gitleaks(.exe)) 또는 .gitleaks.toml 을 이 자리에서 "
                "못 찾는다 — gx-shell 은 저장소 루트(tools/·.gitleaks.toml)를 "
                "마운트하지 않는다. 실제 판정은 호스트에서 잰다(회색 ≠ 초록 · D-301)"
            )

    def test_all_five_fixed_samples_are_caught(self) -> None:
        """자기시험 짝 ① — 표본 5개가 전부 잡힌다."""
        from verify_secret_scan import CONFIG, FIXED_PLANT_SAMPLES, run_scan

        box = Path(tempfile.mkdtemp(prefix="p393.pos."))
        try:
            shutil.copy(CONFIG, box / ".gitleaks.toml")
            for sample in FIXED_PLANT_SAMPLES:
                target = box / sample["path"]
                target.write_text(sample["content"], encoding="utf-8")
                hits = run_scan(self.exe, box, no_git=True)
                self.assertIsNotNone(
                    hits, f"{sample['format']} — 보고서를 못 읽었다(스캐너가 안 돌았다)"
                )
                self.assertTrue(hits, f"{sample['format']} — 고정 표본을 못 잡았다")
                target.unlink()
        finally:
            shutil.rmtree(box, ignore_errors=True)

    def test_clean_counterparts_are_not_caught(self) -> None:
        """자기시험 짝 ② — 깨끗한 표본(같은 형식의 플레이스홀더)은 안 잡힌다."""
        from verify_secret_scan import CONFIG, FIXED_PLANT_SAMPLES, run_scan

        box = Path(tempfile.mkdtemp(prefix="p393.neg."))
        try:
            shutil.copy(CONFIG, box / ".gitleaks.toml")
            for sample in FIXED_PLANT_SAMPLES:
                target = box / sample["path"]
                target.write_text(sample["clean_content"], encoding="utf-8")
                hits = run_scan(self.exe, box, no_git=True)
                self.assertIsNotNone(hits, f"{sample['format']} 음성 — 보고서를 못 읽었다")
                self.assertFalse(
                    hits, f"{sample['format']} 음성 — 플레이스홀더인데 잡혔다(오탐)"
                )
                target.unlink()
        finally:
            shutil.rmtree(box, ignore_errors=True)

    def test_self_test_passes(self) -> None:
        """게이트 자신의 self_test() 가 통과하는가 — 두 번째 판정을 새로 짜지 않고
        게이트의 자기시험을 그대로 부른다(D-369, `test_no_secret_echo.py` 와 같은 결).
        """
        from verify_secret_scan import EXIT_OK, self_test

        rc = self_test(self.exe)
        self.assertEqual(
            rc, EXIT_OK,
            "verify_secret_scan 의 자기시험이 실패했다 — 위 stdout 에 사유가 있다",
        )

    def test_self_test_is_stable_under_concurrent_load(self) -> None:
        """부하 중 재현 시험 — 같은 self_test() 를 동시에 여러 번(스레드 4개) 돌려도
        결과가 전부 같은가. 턴 AM 의 SEC-05 FAIL(부하 중 두 번 실패·단독 실행 통과)이
        되살아나지 않아야 한다.
        """
        from verify_secret_scan import self_test

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _i: self_test(self.exe), range(4)))

        self.assertEqual(
            len(set(results)), 1,
            f"동시 실행 결과가 갈렸다 — {results} (부하 중 흔들리는 자기시험이 되살아났다)",
        )


if __name__ == "__main__":
    unittest.main()
