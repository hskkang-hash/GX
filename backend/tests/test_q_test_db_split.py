# -*- coding: utf-8 -*-
"""QA-11 — 시험 DB 이름을 **실행이 정한다** (차선 Q · 2026-09-26 · D-390).

무엇을 재는가
-------------
`conftest.test_db_name` 은 순수 함수다. 이 시험은 그 함수에 **실행 인자를 그대로** 먹여
갈래를 확인한다 — 실제 DB 를 만들지 않는다. DB 를 정말 안 다투는지는 **동시에 돌려 본
기록**이 증거이고, 그것은 대장(GA `QA-11`)에 있다.

★ 왜 이 시험이 필요한가
    고친 것은 코드 한 줄이 아니라 **순서**였다(환경변수 → 픽스처). 순서는 로그에
    안 나오고, 되돌아가도 **조용하다** — 두 실행이 같은 이름을 쓰기 시작하면
    그 빨강은 「환경 충돌」의 모양으로 나타나 코드 결함처럼 읽힌다.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from django.test import TestCase


def _conftest():
    """루트 conftest 를 **파일 경로로** 읽는다.

    이름(`conftest`)으로 import 하면 pytest 가 이미 올려 둔 다른 conftest 를 집을 수 있다 —
    마운트가 셋인 이 컨테이너에서 그 착각은 실제로 일어난다.
    """
    path = Path(__file__).resolve().parent.parent / "conftest.py"
    spec = importlib.util.spec_from_file_location("gx_root_conftest", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestDbNameTest(TestCase):

    def setUp(self) -> None:
        self.name = _conftest().test_db_name

    def test_the_e2e_run_gets_its_own_name(self) -> None:
        self.assertEqual(
            self.name(["tests/e2e", "-q"], base="test_gx"), "test_gx_e2e")

    def test_a_single_e2e_file_also_gets_it(self) -> None:
        self.assertEqual(
            self.name(["tests/e2e/test_e2e_1_fire.py::E2E1FireTest", "-q"],
                      base="test_gx"), "test_gx_e2e")

    def test_the_unit_run_keeps_the_plain_name(self) -> None:
        self.assertEqual(self.name(["tests", "-q"], base="test_gx"), "test_gx")

    def test_ignore_is_not_a_target(self) -> None:
        """★ **`--ignore=tests/e2e` 는 겨누는 것이 아니라 빼는 것이다.**

        이 구별이 없으면 단위 실행이 E2E 이름을 쓰고, 그러면 갈라 놓은 보람이 없다 —
        둘이 다시 같은 DB 를 만들고 그 빨강은 코드 결함처럼 보인다.
        """
        self.assertEqual(
            self.name(["tests", "--ignore=tests/e2e"], base="test_gx"), "test_gx")

    def test_windows_paths_are_the_same_paths(self) -> None:
        self.assertEqual(
            self.name([r"tests\e2e"], base="test_gx"), "test_gx_e2e")

    def test_no_argument_run_is_the_unit_name(self) -> None:
        """인자 없이 부르면 `testpaths = tests` 다 — 그것은 단위다."""
        self.assertEqual(self.name([], base="test_gx"), "test_gx")


class RootConfigIsPinnedTest(TestCase):
    """★ 이 갈래를 살린 것은 코드가 아니라 **`pytest.ini` 의 존재**였다.

    ini 파일이 없으면 rootdir 이 인자들의 공통 조상(`tests/e2e`)이 되고,
    그러면 `backend/conftest.py` 는 그 **위**라 아예 안 읽힌다 —
    고친 코드가 조용히 안 도는 상태다. 파일이 사라지면 이 시험이 말한다.
    """

    def test_pytest_ini_exists_and_pins_testpaths(self) -> None:
        ini = Path(__file__).resolve().parent.parent / "pytest.ini"
        self.assertTrue(ini.is_file(), "pytest.ini 가 없으면 rootdir 이 인자를 따라 움직인다")
        text = ini.read_text(encoding="utf-8")
        self.assertIn("[pytest]", text)
        self.assertIn("testpaths", text)


class SplitWhenBusyTest(TestCase):
    """턴 X · 차선 S — **같은 이름을 든 실행 둘**을 다투는 순간에만 가른다.

    출생 표본 [실측 2026-09-20]: `DB_TEST_NAME=test_gx_s` 를 든 내 실행 둘.
    먼저 돈 쪽은 teardown 에서 `database "test_gx_s" is being accessed by other users`,
    나중에 온 쪽은 **22 errors** — 전부
    `duplicate key value violates unique constraint "auth_permission_…"` 였다.
    그 빨강에는 DB 이름이 한 글자도 안 나온다. 그래서 코드 결함으로 읽힌다.
    """

    def setUp(self) -> None:
        self.split = _conftest().split_when_busy

    def test_a_busy_name_is_split(self) -> None:
        self.assertEqual(
            self.split("test_gx_s", busy=True, pid=4242), "test_gx_s_p4242")

    def test_a_free_name_is_not_touched(self) -> None:
        """⚠ 늘 가르면 실행마다 새 DB 가 남고, 치우는 일이 사람의 기억으로 돌아온다."""
        self.assertEqual(
            self.split("test_gx_s", busy=False, pid=4242), "test_gx_s")

    def test_not_knowing_is_not_splitting(self) -> None:
        """**못 봤다(None)** 는 이름을 안 바꾼다 — 대신 부르는 쪽이 그 사실을 인쇄한다.

        「못 봤다」를 「다툰다」로 읽으면 평시 실행마다 DB 가 새로 생기고,
        「안 다툰다」로 읽으면 가드가 조용히 사라진다. 그래서 갈래가 셋이다.
        """
        self.assertEqual(
            self.split("test_gx_s", busy=None, pid=4242), "test_gx_s")

    def test_the_split_name_is_still_a_legal_db_name(self) -> None:
        """postgres 의 이름 한도는 63자다 — 가른 이름이 그 선을 넘으면 조용히 잘린다."""
        self.assertLess(len(self.split("test_gx_s", busy=True, pid=999999)), 63)
