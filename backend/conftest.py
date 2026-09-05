# -*- coding: utf-8 -*-
"""QA-11 — **단위 시험과 E2E 가 서로의 DB 를 다투지 않는다** (D-390 · 차선 Q).

무엇이 문제였나
---------------
둘 다 `test_<DB_NAME>` 하나를 만들려 했다. 동시에 돌리면 나중에 시작한 쪽이
`DuplicateDatabase` / `ObjectInUse: being accessed by other users` 로 죽는다.

    ★ **그 빨강은 코드 결함처럼 보이지만 환경 충돌이다.**
      실제로 한 번 「실패 1건」을 그렇게 오독할 뻔했다.

지금까지의 대응은 「순차로 돌린다」였고, 그것은 **회피이지 해결이 아니다**(D-390).
그리고 회피는 사람의 기억을 요구한다 — 기억을 요구하는 규칙은 바쁜 날 깨진다(D-286).

무엇을 고쳤나 — 이름 하나
-------------------------
`DB_TEST_NAME` 은 이미 있었다(P-18 · 차선마다 이름 가르기). 없던 것은 **기본값**이다.
아무도 아무것도 안 정했을 때 둘이 같은 이름을 쓴다는 것이 전부였다.

그래서 **실행 자체를 보고 이름을 정한다**: 이 실행이 `tests/e2e` 를 겨누면
`…_e2e` 를 쓴다. 사람이 기억할 것이 없다.

    pytest tests --ignore=tests/e2e   →  test_<DB>          (단위)
    pytest tests/e2e                  →  test_<DB>_e2e      (E2E)
    DB_TEST_NAME=test_gx_c pytest …   →  test_gx_c          (사람이 정하면 그것이 이긴다)

★ 왜 환경변수가 아니라 **`django_db_modify_db_settings`** 인가 [실측 2026-09-26]
    처음에는 conftest 최상단에서 `os.environ["DB_TEST_NAME"]` 을 세웠다. **안 먹었다** —
    pytest-django 는 `pytest_load_initial_conftests` 에서 **먼저** `django.setup()` 을
    부르고, 그 순간 `config/settings.py` 가 이미 `DB_TEST_NAME` 을 읽어 버린다.
    그래서 E2E 실행이 여전히 단위와 같은 이름을 만들려 했고 `DuplicateDatabase` 12건으로 죽었다.
    **판정기가 아니라 순서 문제였고, 그 순서는 로그 어디에도 안 나온다.**
    pytest-django 가 그 자리에 준 손잡이가 이 픽스처다 — DB 를 만들기 **직전**에 불린다.

★ 사람이 `DB_TEST_NAME` 을 준 실행에서는 그 값이 이긴다 —
  차선마다 이름을 가르는 P-18 의 길을 막지 않는다.
"""
from __future__ import annotations

import os

import pytest


def test_db_name(argv, *, base: str) -> str:
    """이 실행이 겨누는 시험 DB 이름. **순수 함수다** — 시험이 이것을 직접 먹인다.

    술어는 하나: 인자 중에 `tests/e2e` 를 가리키는 것이 있는가.
    `--ignore=tests/e2e` 는 **겨누는 것이 아니라 빼는 것**이므로 세지 않는다 —
    그 구별이 없으면 단위 실행이 E2E 이름을 쓰고, 그러면 갈라 놓은 보람이 없다.
    """
    for raw in argv or ():
        arg = str(raw).replace("\\", "/")
        if arg.startswith("-"):        # --ignore=tests/e2e · -k … 는 겨누는 것이 아니다
            continue
        if "tests/e2e" in arg.split("::", 1)[0]:
            return f"{base}_e2e"
    return base


@pytest.fixture(scope="session")
def django_db_modify_db_settings(django_db_modify_db_settings_xdist_suffix) -> None:
    """시험 DB 이름을 **만들기 직전에** 정한다 (QA-11).

    `django_db_modify_db_settings_xdist_suffix` 를 먼저 받는 이유: xdist 로 나눠 돌 때
    pytest-django 가 워커별 접미사를 붙인다. 그 일을 지우지 않고 **그 뒤에** 얹는다 —
    지우면 xdist 실행이 서로의 DB 를 다투고, 그것은 우리가 고치려던 바로 그 병이다.
    """
    from django.conf import settings

    db = settings.DATABASES["default"]
    test_conf = db.setdefault("TEST", {})
    if os.environ.get("DB_TEST_NAME"):
        return                       # 사람이 정한 이름이 이긴다 (P-18 차선별 이름)
    if test_conf.get("NAME") and "gw" in str(test_conf.get("NAME")):
        return                       # xdist 접미사가 붙은 이름은 건드리지 않는다
    base = "test_" + str(db.get("NAME") or "guardianx-v2")
    test_conf["NAME"] = test_db_name(_pytest_args, base=base)


#: 실행 인자. `pytest_cmdline_main` 이 아니라 훅에서 받아 둔다 — 픽스처는 세션 뒤에 불리고
#: 그때 `sys.argv` 는 이미 다른 것이 만졌을 수 있다.
_pytest_args: list[str] = []


def pytest_configure(config) -> None:
    global _pytest_args
    _pytest_args = [str(a) for a in (config.args or [])]
