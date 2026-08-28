# -*- coding: utf-8 -*-
"""E2E 만의 시험 DB 구성 — **실 마이그레이션으로 세운다** (D-291 규약 ①).

이 파일이 왜 필요한가 — 실측한 사실 하나
----------------------------------------
빈 DB 에 `manage.py migrate` 를 그냥 돌리면 **죽는다**:

    core/logger/migrations/0009_auditaccesstype_auditaction_auditcommand_and_more.py:17
        MultiLanguageContent = apps.get_model("multilanguage", "MultiLanguageContent")
    LookupError: No installed app with label 'multilanguage'.

`multilanguage` 는 `INSTALLED_APPS` 에 있다(`core.multilanguage`, label=`multilanguage`).
없는 것은 앱이 아니라 **그 시점의 마이그레이션 상태**다 — dj-core 의 `logger/0009` 가
`multilanguage` 에 대한 dependency 를 선언하지 않아서, 실행 계획에서 뒤에 오면
`RunPython` 이 받는 상태에 그 앱의 모델이 아직 없다.

즉 **이 저장소의 스키마는 지금까지 마이그레이션만으로 재현되지 않았다.**
도는 개발 DB 는 어쩌다 맞는 순서로 적용된 결과이고, 새 환경(에스비 인도 · CI · 이 E2E)
에서는 처음부터 못 세운다. 증거: `docs/agent/evidence/e2e/migration_from_scratch.md`.

무엇으로 고쳤나 — **순서 하나**
-------------------------------
`user` → `multilanguage` 를 먼저 적용하고 나머지를 돌리면 통과한다. 빈 DB 실측:

    manage.py migrate user               # 먼저 (아래 ※)
    manage.py migrate multilanguage      # 그 다음
    manage.py migrate                    # 나머지 전부  → migrate --check exit 0 (표 212)

그래서 시험 DB 를 만들 때 그 두 줄을 앞에 끼운다. 그것이 이 파일의 전부다.

  ※ `user` 가 먼저인 이유도 실측이다. `multilanguage` 만 먼저 돌리면 dj-core 의 시그널이
    씨앗 데이터 저장 중 `CoreUser.objects.…username='AnonymousUser'` 를 묻고,
    그때 `user_coreuser` 표가 아직 없어 `UndefinedTable` 로 죽는다.
    **두 줄 다 순서일 뿐 스키마를 바꾸지 않는다.**

왜 마이그레이션 파일로 고치지 않았나 (되돌린 시도를 남긴다)
----------------------------------------------------------
`run_before = [("logger", "0009…")]` 를 선언한 빈 마이그레이션을 만들어 봤고, **빈 DB 에서는
통과했다.** 그러나 **이미 `logger/0009` 가 적용된 DB**(지금의 개발 DB, 그리고 운영 DB)에서는
`migrate` 자체가 `InconsistentMigrationHistory` 로 죽는다 — `--fake` 로도 통과하지 못한다.
고치려던 것보다 **더 큰 것을 깨뜨리므로 되돌렸다.**

  ⚠ 근본 해결은 dj-core `logger/0009` 에 dependency 를 넣는 것이다. 그것은 사내 패키지
    수정(§0.4)이므로 **P-ENV-1 로 적재**했다. 이 파일은 그 전까지의 받침이고,
    받침이라는 사실을 숨기지 않는다.

이 파일의 범위 — `tests/e2e/` 뿐이다
------------------------------------
`tests/` 전체를 `--nomigrations` 로 돌리는 빠른 경로는 **그대로 둔다.**
속도용 보조 수단을 없애는 것이 D-282 의 요구가 아니다 — 요구는
**최소 하나의 시험 경로가 실물 위에서 도는 것**이고, 그 경로가 여기다.
"""
from __future__ import annotations

from unittest import mock

import pytest

#: 먼저 적용해야 하는 앱. **이름으로 적는다** — "몇 개를 먼저"가 아니라 "무엇을 먼저"다.
#: 늘어나면 여기에 이름이 늘고, 그 diff 가 곧 "왜 늘었는가"를 묻는 자리가 된다 (D-285 ②).
PRE_MIGRATED_APPS: tuple[str, ...] = ("user", "multilanguage")


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):  # noqa: PT004 - pytest-django 규약
    """기본 구성을 그대로 쓰되, **표가 실제로 섰는지 한 번 확인한다.**

    구성 자체는 아래 `_order_aware_create_test_db` 가 이미 고쳤다(세션 시작 시 패치).
    여기서 다시 확인하는 이유는 D-274 다 — **우연에 기대지 않는다.**
    패치가 어떤 이유로든 안 걸리면 여기서 멈추고, 그 사실이 보인다.
    """
    from django.db import connection

    with django_db_blocker.unblock():
        names = set(connection.introspection.table_names())
    missing = sorted({"stream_monitors_detectionevent",
                      "stream_monitors_notificationrule",
                      "stream_monitors_deliveryrecord"} - names)
    if missing:
        raise RuntimeError(
            f"E2E 시험 DB 에 표가 없습니다: {missing}. "
            "이 폴더는 `--nomigrations` 없이 돌아야 합니다 (D-291 규약 ①)."
        )
    return django_db_setup


def pytest_configure(config) -> None:
    """시험 DB 생성 순서를 고친다 — **DB 를 만들기 전에** 걸어야 한다.

    `create_test_db` 는 (1) 빈 DB 를 만들고 (2) `call_command("migrate", …)` 를 부른다.
    그 (2) 앞에 `migrate <app>` 을 끼우는 것이 전부다. 스키마를 바꾸지 않는다.
    """
    # `creation.py` 는 **메서드 안에서** `from django.core.management import call_command`
    # 을 한다(실측: creation.py:40). 그래서 모듈 속성을 갈아 끼우면 그 시점에 잡힌다.
    from django.core import management as management_module

    original_call_command = management_module.call_command

    def call_command(name, *args, **kwargs):
        # 전체 마이그레이션(인자 없는 `migrate`) 직전에만 끼어든다.
        # `migrate <app>` 형태(우리가 넣는 것 포함)에는 재귀하지 않는다.
        if name == "migrate" and not args:
            for app_label in PRE_MIGRATED_APPS:
                original_call_command(
                    "migrate", app_label,
                    verbosity=0, interactive=False,
                    database=kwargs.get("database", "default"),
                )
        return original_call_command(name, *args, **kwargs)

    patcher = mock.patch.object(management_module, "call_command", call_command)
    patcher.start()
    config.add_cleanup(patcher.stop)
