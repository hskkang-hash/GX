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
    # P-71 — 시험 DB 생성 경로에 OPS-03 우회층을 태운다 (아래 블록 참조).
    #   `django.setup()` 은 pytest-django 가 이미 끝냈다 — 그래서 여기가 첫 자리다.
    _install_migrate_bootstrap()


# ═══════════════════════════════════════════════════════════════════════════
# P-71 — **새 시험 DB 가 마이그레이션 잠금에서 죽는다** (2026-09-06 · 턴 G · 차선 S)
#
# 무엇이 막고 있었나 [실측 2026-09-06 · 새 이름 `test_gx_s_p71a` 로 재현]
# ---------------------------------------------------------------------
#     core/logger/migrations/0009_auditaccesstype_… .py:17
#         MultiLanguageContent = apps.get_model("multilanguage", "MultiLanguageContent")
#     E   LookupError: No installed app with label 'multilanguage'.
#
#   `logger/0009` 는 `multilanguage` 의존을 **선언하지 않는다.** 그래서 장고가 세운
#   기본 순서로 빈 DB 에 `migrate` 를 돌리면, 그 RunPython 이 아직 상태에 없는 앱을
#   찾다가 죽는다. 그 파일은 dj-core — **§0.4 금지구역이라 고칠 수 없다.**
#
#   OPS-03 은 이 잠금의 우회층을 이미 만들어 두었다: `manage.py migrate_bootstrap`
#   (`backend/common/management/commands/migrate_bootstrap.py`). 없던 것은 **그 층이
#   시험 DB 생성 경로에는 안 깔려 있었다**는 것뿐이다. 사람이 손으로 부르는 명령이라
#   pytest 가 만드는 DB 는 그 순서를 모른 채 태어났다.
#
#   ★ **순서를 아는 것은 도구여야 한다** (D-286). 「새 시험 DB 를 만들기 전에
#     migrate_bootstrap 을 부르세요」는 사람의 기억에 맡긴 절차이고, 기억에 맡긴 절차는
#     바쁜 날 빠진다. 그래서 여기서 **자동으로** 같은 순서를 태운다.
#
# 무엇을 고쳤나 — **순서만.** 스키마도 dj-core 도 한 글자 안 바꿨다
# ------------------------------------------------------------------
#   장고의 `BaseDatabaseCreation.create_test_db` 는 빈 DB 를 만든 뒤 `migrate` 를
#   **한 번** 부른다(django 5.1 `db/backends/base/creation.py`). 그 한 번 앞에
#   `migrate user` · `migrate multilanguage` 를 끼운다 — `migrate_bootstrap` 이 손으로
#   부를 때 밟는 것과 **같은 순서, 같은 목록**이다.
#
#   ★ 목록을 여기 베끼지 않는다. `BOOTSTRAP_ORDER` 를 **그 파일에서 읽어 온다** —
#     두 벌로 두면 한쪽만 고쳐지고, 어긋난 복사본 하나가 D-212 였다.
#   ★ 이미 선 DB(`keepdb`)에서는 그 걸음이 전부 「적용 완료」라 아무 일도 하지 않는다.
#   ★ **마이그레이션이 꺼진 실행이면 끼우지 않는다.** 그때는 잠금도 함께 사라진다 —
#     `--nomigrations` 로 돌리면 이 결함이 안 보이던 이유가 바로 그것이다.
#     ⚠ 꺼졌는지는 깃발 하나로 못 묻는다: `TEST['MIGRATE'] is False` **와**
#     pytest-django 의 `--nomigrations`(= `settings.MIGRATION_MODULES` 교체)가
#     서로 다른 자리를 건드린다. `migrations_are_disabled()` 참조 — 그 하나를
#     빠뜨려 786 passed 가 21 errors 가 됐다 [실측 2026-09-06].
# ═══════════════════════════════════════════════════════════════════════════
def migrations_are_disabled(app_labels) -> bool:
    """마이그레이션이 **꺼진 실행인가.** 깃발을 믿지 않고 장고에게 직접 묻는다.

    ★ 왜 술어가 둘이 되었나 [실측 2026-09-06 · 턴 G · 조율자]
    ------------------------------------------------------
    이 훅은 처음에 `TEST['MIGRATE'] is False` 하나로만 물었다. 그런데
    **pytest-django 의 `--nomigrations` 는 그 칸을 안 건드린다** — 대신
    `settings.MIGRATION_MODULES` 를 「무엇을 물어도 None」인 물건으로 갈아 끼운다.
    그래서 판별자가 「꺼지지 않았다」고 답했고, 훅이 `migrate user` 를 불렀고,
    문서에 적힌 빠른 경로가 통째로 죽었다:

        conftest.py:183 create_test_db → :176 call_command
        CommandError: App 'user' does not have migrations.     ← 786 passed 가 21 errors

    ★ **깃발은 두 벌인데 사실은 하나다.** 그럴 때는 깃발을 세지 말고 사실을 잰다 —
      「이 앱에 태울 마이그레이션이 있는가」를 장고 자신의 로더에게 묻는다.
      새 도구가 세 번째 방식으로 마이그레이션을 꺼도 이 술어는 그대로 맞는다.

    ⚠ `all()` 이다 — 목록의 앱이 **하나라도** 태울 것이 있으면 켜진 실행으로 본다.
      `any()` 로 쓰면 앱 하나만 마이그레이션이 없어도 우회층 전체가 조용히 꺼진다.
    """
    from django.db.migrations.loader import MigrationLoader

    labels = tuple(app_labels)
    if not labels:
        return False
    try:
        return all(MigrationLoader.migrations_module(a)[0] is None for a in labels)
    except Exception:            # 앱 등록부를 못 읽으면 **끄지 않는다** (안전한 쪽)
        return False


def bootstrap_steps(order, *, migrate_disabled: bool) -> tuple:
    """시험 DB 의 `migrate` **앞에** 밟을 걸음. **순수 함수다** — DB 없이 시험한다.

    마이그레이션이 꺼진 실행이면 빈 튜플이다. 꺼진 실행에 순서를 끼우면 **없는 일을
    한 척**하게 되고, 그 척은 다음 사람이 이 훅을 믿지 못하게 만든다.

    ⚠ `migrate_disabled` 를 **판단하는 것은 이 함수가 아니다**(순수하게 남기려고).
      그 판단은 `migrations_are_disabled()` 가 하고, 그 자리가 한 번 틀렸었다.
    """
    if migrate_disabled:
        return ()
    return tuple(order)


_BOOTSTRAP_INSTALLED = False


def _install_migrate_bootstrap() -> None:
    """`create_test_db` 안의 `migrate` 한 번 앞에 OPS-03 순서를 끼운다."""
    global _BOOTSTRAP_INSTALLED
    if _BOOTSTRAP_INSTALLED:
        return

    import django.core.management as _mgmt
    from django.db.backends.base.creation import BaseDatabaseCreation

    original_create = BaseDatabaseCreation.create_test_db

    def create_test_db(self, verbosity=1, autoclobber=False, keepdb=False,
                       serialize=True):
        # ⚠ 목록의 정본은 OPS-03 우회층이다. 여기서 **읽어 오고, 베끼지 않는다.**
        try:
            from common.management.commands.migrate_bootstrap import BOOTSTRAP_ORDER
        except ImportError:                      # 우회층이 없으면 아무것도 안 한다
            return original_create(self, verbosity, autoclobber, keepdb, serialize)

        alias = self.connection.alias
        disabled = (
            self.connection.settings_dict.get("TEST", {}).get("MIGRATE") is False
            or migrations_are_disabled(BOOTSTRAP_ORDER)
        )
        steps = bootstrap_steps(BOOTSTRAP_ORDER, migrate_disabled=disabled)
        original_call = _mgmt.call_command
        state = {"done": not steps}

        def call_command(name, *args, **kwargs):
            # 장고가 빈 DB 에 부르는 **그 한 번**의 `migrate` 앞에서만 끼운다.
            # (인자 없는 `migrate` = 전체 계획. 앱 이름이 붙은 것은 우리가 부른 것이다)
            if name == "migrate" and not args and not state["done"]:
                state["done"] = True
                for app in steps:
                    original_call("migrate", app,
                                  verbosity=max(int(kwargs.get("verbosity", 1)) - 1, 0),
                                  interactive=False, database=alias)
            return original_call(name, *args, **kwargs)

        _mgmt.call_command = call_command
        try:
            return original_create(self, verbosity, autoclobber, keepdb, serialize)
        finally:
            _mgmt.call_command = original_call

    BaseDatabaseCreation.create_test_db = create_test_db
    _BOOTSTRAP_INSTALLED = True
