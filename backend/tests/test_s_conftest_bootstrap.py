# -*- coding: utf-8 -*-
"""P-71 — **시험 DB 생성 경로에 OPS-03 우회층이 깔려 있는가** (2026-09-06 · 턴 G · 차선 S).

무엇을 막는가 — **새 이름의 시험 DB 가 태어나지 못했다**
--------------------------------------------------------
[실측 2026-09-06 · `DB_TEST_NAME=test_gx_s_p71a`]

    core/logger/migrations/0009_auditaccesstype_… .py:17
        MultiLanguageContent = apps.get_model("multilanguage", "MultiLanguageContent")
    E   LookupError: No installed app with label 'multilanguage'.
    …
    13 errors in 157.84s

`logger/0009` 이 `multilanguage` 의존을 선언하지 않는다. 그 파일은 dj-core —
**§0.4 금지구역이라 고칠 수 없다.** OPS-03 이 만든 우회층(`migrate_bootstrap`)이
아는 순서를 시험 DB 생성 경로에도 태우자 **12 passed** 가 됐다(남은 1건은 차선 E 의
보존 선언 작업 중인 `DEFAULT_RETENTION_DAYS` — 이 훅과 무관하다).

★ 이 시험이 지키는 것은 **DB 가 아니라 순서다.** 순서는 DB 없이 잴 수 있고
  (D-277), DB 로만 잴 수 있는 규칙은 결국 아무도 안 재는 규칙이 된다.

⚠ **`--nomigrations` 로 돌리면 이 잠금이 안 보인다.** 그때는 마이그레이션 자체가
  꺼져 있어서 `logger/0009` 이 아예 안 돈다. 그래서 아래 ㉢ 갈래가 있다 —
  꺼진 실행에 순서를 끼우면 **없는 일을 한 척**이 된다.
"""
from __future__ import annotations

import conftest
from common.management.commands.migrate_bootstrap import BOOTSTRAP_ORDER


class TestDbIsBornWithTheBootstrapOrder:
    """시험 DB 의 `migrate` **앞에** 무엇을 밟는가."""

    def test_the_order_comes_from_the_ops03_layer_not_a_copy(self):
        """★ 목록의 정본은 하나다.

        conftest 가 목록을 **베껴** 들고 있으면 한쪽만 고쳐지고, 어긋난 판정식
        복사본 하나가 D-212 였다. 그래서 `BOOTSTRAP_ORDER` 를 그대로 먹인 결과가
        그 목록과 같아야 한다.
        """
        steps = conftest.bootstrap_steps(BOOTSTRAP_ORDER, migrate_disabled=False)
        assert steps == tuple(BOOTSTRAP_ORDER)

    def test_multilanguage_is_stood_up_before_the_rest(self):
        """★ **출생 표본** — 죽은 자리가 `multilanguage` 였다.

        목록이 「무엇이든」이면 이 훅은 있으나 마나다. 그날 못 찾은 그 앱이
        전체 `migrate` 앞에 서 있어야 한다.
        """
        steps = conftest.bootstrap_steps(BOOTSTRAP_ORDER, migrate_disabled=False)
        assert "multilanguage" in steps, (
            "logger/0009 이 찾다가 죽은 앱이 앞 걸음에 없다 — "
            "LookupError: No installed app with label 'multilanguage'"
        )

    def test_nomigrations_run_gets_no_extra_steps(self):
        """㉢ 마이그레이션이 꺼진 실행에는 **끼우지 않는다.**

        마이그레이션이 꺼진 실행에 걸음을 끼우면
        아무 일도 안 하면서 「우회층을 태웠다」고 말하게 되고, 그 척은 다음 사람이
        이 훅을 믿지 못하게 만든다.
        """
        assert conftest.bootstrap_steps(BOOTSTRAP_ORDER, migrate_disabled=True) == ()

    def test_the_hook_is_actually_installed(self):
        """★ **선언이 아니라 적용을 본다.**

        `bootstrap_steps` 가 옳아도 아무도 안 부르면 시험 DB 는 그대로 죽는다.
        `pytest_configure` 가 실제로 설치했는지를 묻는다 — 이 시험이 도는 지금
        이미 불렸어야 한다.
        """
        assert conftest._BOOTSTRAP_INSTALLED is True, (
            "pytest_configure 가 _install_migrate_bootstrap() 을 안 불렀다 — "
            "훅이 있어도 깔리지 않으면 새 시험 DB 는 여전히 logger/0009 에서 죽는다"
        )


class TestTheDisabledRunIsMeasuredNotAssumed:
    """★ **출생 표본** — 이 술어가 한 번 틀려서 빠른 경로가 통째로 죽었다.

    [실측 2026-09-06 · 턴 G · 조율자]

        docker exec gx-shell python -m pytest tests -q --nomigrations
        conftest.py:183 create_test_db → :176 call_command
        CommandError: App 'user' does not have migrations.      ← 21 errors

    뿌리: 훅이 꺼짐을 `TEST['MIGRATE'] is False` **하나로만** 물었는데,
    pytest-django 의 `--nomigrations` 는 그 칸을 안 건드리고
    `settings.MIGRATION_MODULES` 를 「무엇을 물어도 None」인 물건으로 갈아 끼운다.
    깃발이 둘인데 하나만 봤다.
    """

    def test_pytest_django_style_disabling_is_seen(self):
        """pytest-django 가 끄는 **그 방식**을 세워 놓고 묻는다.

        `TEST['MIGRATE']` 는 건드리지 않는다 — 그것이 이 회귀의 조건이었다.
        """
        from django.conf import settings

        class _DisableMigrations:                 # pytest-django 가 끼우는 것과 같은 모양
            def __contains__(self, item): return True
            def __getitem__(self, item): return None

        original = settings.MIGRATION_MODULES
        settings.MIGRATION_MODULES = _DisableMigrations()
        try:
            assert conftest.migrations_are_disabled(BOOTSTRAP_ORDER) is True, (
                "pytest-django 방식으로 껐는데 술어가 「켜져 있다」고 답한다 — "
                "이 상태에서 훅이 `migrate user` 를 부르면 CommandError 가 난다"
            )
        finally:
            settings.MIGRATION_MODULES = original

    def test_a_live_run_is_not_mistaken_for_a_disabled_one(self):
        """★ **음성 대조군.** 언제나 True 를 내는 술어는 우회층을 조용히 끈다.

        마이그레이션이 실재하는 앱을 하나 먹여, 그것을 「꺼졌다」로 읽지 않는지 본다.
        (`all()` 이므로 실재하는 것이 하나만 있어도 False 여야 한다.)

        ⚠ **이 시험 자신이 한 번 틀렸다** [실측 2026-09-06 · 전 시험 1141 중 1건].
          처음에는 `MIGRATION_MODULES` 를 그대로 두고 물었다 — 그러면
          `--nomigrations` 실행에서는 `contenttypes` 도 꺼져 있으므로 True 가 나온다.
          **음성 대조군이 실행 모드에 따라 뒤집혔다** — 그것은 이 술어가 앓던 병과
          똑같은 병이다(깃발을 안 보고 재는 척했다). 그래서 여기서는 「꺼지지 않은
          상태」를 **직접 세워 놓고** 묻는다: 평범한 dict 를 끼우면 장고는 앱의 실제
          마이그레이션 모듈 이름을 돌려준다.
        """
        from django.conf import settings

        original = settings.MIGRATION_MODULES
        settings.MIGRATION_MODULES = {}          # 아무것도 끄지 않은 상태 = 평범한 dict
        try:
            assert conftest.migrations_are_disabled(["contenttypes"]) is False, (
                "마이그레이션이 실재하는 앱을 「꺼졌다」로 읽는다 — "
                "이 술어는 우회층을 언제나 조용히 끄게 된다"
            )
        finally:
            settings.MIGRATION_MODULES = original

    def test_an_empty_list_is_not_a_disabled_run(self):
        """빈 목록에 `all()` 은 True 다 — 그 파이썬 규칙이 우회층을 끄면 안 된다."""
        assert conftest.migrations_are_disabled([]) is False
