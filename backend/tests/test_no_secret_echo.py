# -*- coding: utf-8 -*-
"""P-135 ④ — **값을 안 찍는 게이트가 스스로 눈이 멀지 않았는지** 회귀로 지킨다.

`scripts/verify_no_secret_echo.py` 는 저장소 밖 `.env`·`.env.gates` 를 읽어
`docs/agent/**`·`docs/review/**`·`--run` 출력에 값이 새면 exit 1 이 되는 게이트다.
그 판정 엔진(`self_test`)을 여기서도 불러 — **한 벌의 판정이 어긋나지 않게**
한다(D-369). 시험도 게이트 자신의 규칙을 따른다: **아래 어디에도 값을 담은
변수를 남기지 않는다.**

★ `.env`·`.env.gates` 는 `gx-shell` 에 **마운트되지 않는다**
  (`/repo` 아래에는 `backend`·`frontend`·`scripts` 만 붙는다 — `docker inspect
  gx-shell` [실측]). 그래서 컨테이너 안에서는 「저장소 루트 두 파일을 읽고 실제
  스캔한다」 갈래를 잴 수 없다 — 그 갈래는 호스트에서 `python
  scripts/verify_no_secret_echo.py` 로 잰다(회색을 초록으로 덮지 않는다 · D-301).
  이 시험이 컨테이너 안에서 재는 것은 **탐지 엔진 자체**(`self_test`)뿐이다 —
  DB 도 env 파일도 필요 없는 순수 판정이라 여기서도 의미가 있다.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path


def _scripts_dir() -> Path:
    """호스트에서는 `<repo>/scripts`, `gx-shell` 안에서는 `/repo/scripts` (D-369 계열
    — 자리를 한 곳으로 못 박지 않으면 한쪽에서 조용히 건너뛴다).
    """
    here = Path(__file__).resolve()
    for cand in [p / "scripts" for p in here.parents] + [Path("/repo/scripts")]:
        if (cand / "verify_no_secret_echo.py").is_file():
            return cand
    return Path("/repo/scripts")


class NoSecretEchoSelfTestRegressionTest(unittest.TestCase):
    """탐지 엔진이 여전히 심은 값을 잡는가 — **이 시험 자체가 게이트의 자기시험을
    부른다.** 두 번째 판정을 새로 짜지 않는다(두 벌은 반드시 어긋난다 · D-369).
    """

    def setUp(self) -> None:
        scripts = _scripts_dir()
        if not scripts.is_dir():
            self.skipTest(f"scripts/ 를 못 찾았다 — {scripts} (이 자리에서는 못 잰다)")
        sys.path.insert(0, str(scripts))

    def test_self_test_passes(self) -> None:
        from verify_no_secret_echo import EXIT_OK, self_test

        rc = self_test()
        self.assertEqual(
            rc, EXIT_OK,
            "verify_no_secret_echo 의 자기시험이 실패했다 — "
            "이 게이트는 값이 새도 못 잡을 수 있다(위 stdout 에 사유가 있다)",
        )

    def test_secret_name_pattern_excludes_url_and_username_style_keys(self) -> None:
        """제외 규칙(코드 머리말에 이름으로 적은 것)이 실제로 빠지는지 — 값이 아니라
        **이름의 생김새**로 가른다는 그 말이 거짓이 아닌지.
        """
        from verify_no_secret_echo import _SECRET_NAME

        for non_secret in ("GX_API", "GX_ROUTE_USER", "GX_ROUTE_CONTAINER",
                          "GX_PROBE_USER", "MINIO_ENDPOINT", "MINIO_BUCKET_NAME"):
            self.assertIsNone(
                _SECRET_NAME.search(non_secret),
                f"{non_secret} 가 대상 이름 패턴에 걸린다 — URL·사용자명·컨테이너·"
                "호스트·버킷 이름까지 대상이 된다",
            )
        for secret in ("GX_ROUTE_PASSWORD", "GX_ROUTE_PASSWORD_ROLE0",
                      "GX_SEED_ROLE_PASSWORD", "GX_PROBE_PASSWORD",
                      "MINIO_ROOT_PASSWORD"):
            self.assertIsNotNone(
                _SECRET_NAME.search(secret),
                f"{secret} 가 대상 이름 패턴을 놓친다 — 진짜 비밀이 안 잡힌다",
            )


class NoSecretEchoRealScanTest(unittest.TestCase):
    """`docs/agent`·`docs/review` 가 실제로 새지 않았는지 — **`.env`·`.env.gates`
    를 읽을 수 있는 자리에서만** 잰다. 못 읽으면 회색이지 초록이 아니다(D-301) —
    그래서 여기서는 스킵으로 적고, 진짜 판정은 호스트의
    `python scripts/verify_no_secret_echo.py` 가 낸다.
    """

    def test_docs_carry_no_env_secret(self) -> None:
        scripts = _scripts_dir()
        if not scripts.is_dir():
            self.skipTest(f"scripts/ 를 못 찾았다 — {scripts}")
        sys.path.insert(0, str(scripts))

        from verify_no_secret_echo import ROOT, SCAN_ROOTS, collect_secrets, scan_dir

        rows, read_files, problems = collect_secrets()
        if not read_files:
            self.skipTest(
                "이 자리에서는 .env·.env.gates 를 못 읽는다("
                + ", ".join(problems) + ") — gx-shell 은 저장소 루트를 "
                "마운트하지 않는다. 실제 스캔은 호스트에서 잰다(회색 ≠ 초록)"
            )
        all_hits: list[str] = []
        for base_name in SCAN_ROOTS:
            hits, _skipped = scan_dir(ROOT / base_name, rows)
            all_hits += hits
        self.assertEqual(
            all_hits, [],
            "값이 docs/agent 또는 docs/review 에 나타났다(위 목록 — 값 자체는 "
            "적지 않는다). 스크럽은 조율자 몫이고 이 시험은 회귀만 막는다",
        )
