# -*- coding: utf-8 -*-
"""OPS-03 — 마이그레이션이 **한 줄로 선다** (잠금 `MIGRATE_ONE_LINER` 의 우회층).

무엇이 막고 있었나
------------------
dj-core 의 `logger/0009` 가 `multilanguage` 의존을 **선언하지 않는다.** 그래서 빈 DB 에
`manage.py migrate` 를 그냥 돌리면 죽는다. 그 파일은 §0.4 금지구역이라 이 저장소가
고칠 수 없고, 순서 제약을 우리 쪽에 선언해 봤더니 **이미 도는 환경 전부가**
`InconsistentMigrationHistory` 로 죽었다 (docs/agent/evidence/e2e/migration_from_scratch.md).

    [대장 OPS-03 · hand: in] dj-core 는 못 고치지만 **우회 경로를 우리 층에 둔다.**

그래서 이 명령이 있다. **스키마를 한 줄도 바꾸지 않는다** — 순서만 정한다.

    python manage.py migrate_bootstrap --plan     # 무엇을 할지만 보인다 (DB 를 안 만진다)
    python manage.py migrate_bootstrap            # 빈 DB 에 순서대로 세운다

★ 왜 「세 줄을 문서에 적기」로 끝내지 않았나 (D-286)
---------------------------------------------------
설치 절차의 여러 줄은 **사람의 기억에 맡긴 절차**이고, 사람의 기억에 맡긴 절차는
바쁜 날 한 줄이 빠진다. 빠진 그날 설치는 죽고, 죽은 자리를 보면 dj-core 의 의존
선언이 아니라 「이 제품은 설치가 안 된다」로 읽힌다. **순서를 아는 것은 도구여야 한다.**

★ 그런데 이것이 D-283 의 자동 migrate 가 되면 안 된다
-----------------------------------------------------
2026-08-29 에 컨테이너 재기동 하나가 `entrypoint.sh` 의 무조건 `migrate` 를 태워
마이그레이션 4건이 절차 없이 적용됐다. 그래서 이 명령은:

  ① **사람이 손으로 부르는 명령**이다 — 어떤 entrypoint 에도 걸지 않는다
  ② **이미 마이그레이션이 적용된 DB 에서는 그 자리에서 멈춘다** (`--force` 로만 넘는다).
     설치용 도구가 운영 DB 에서 돌 수 있으면, 그것은 설치 도구가 아니라 사고다
  ③ 끝나고 `migrate --check` 로 **정합을 스스로 확인한다** — 「돌았다」와 「맞다」는 다르다

종료 코드: 0 세웠다 · 1 실패 · 2 못 한다(이미 선 DB — 회색이지 통과가 아니다).
"""
from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

#: ★ **순서가 곧 이 파일의 내용이다** (실측 근거: migration_from_scratch.md §4).
#:   `logger/0009` 가 선언하지 않은 의존을 여기서 **집행**한다 — 선언을 고치는 것이
#:   아니라 **먼저 세우는 것**이므로 이미 도는 DB 를 깨뜨리지 않는다.
#:   ⚠ 이 순서를 바꾸려면 빈 DB 에서 다시 재고 그 기록을 증거에 남겨라.
BOOTSTRAP_ORDER: tuple[str, ...] = ("user", "multilanguage")

#: 위 앱들을 세운 뒤 나머지 전부. 이름이 아니라 **빈 인자**다(장고가 계획을 세운다).
FINAL_STEP = "(전체)"


def planned_steps() -> tuple[str, ...]:
    """이 명령이 밟을 걸음. **순수 함수다** — DB 없이 시험할 수 있다 (D-277)."""
    return tuple(f"migrate {app}" for app in BOOTSTRAP_ORDER) + (
        "migrate", "migrate --check")


def refuse_reason(applied: int, *, force: bool) -> str | None:
    """진행하면 안 되는 이유. 통과면 `None`. **순수 함수다** — DB 없이 시험한다(D-277).

    ★ 판정을 `handle()` 안에 두면 이 갈래는 **빈 DB 에서만** 시험할 수 있고, 시험용
      DB 는 언제나 비어 있으므로 결국 **아무도 안 재는 갈래**가 된다. 그러면 그 판정은
      있으나 마나다.
    """
    if applied and not force:
        return ("[OPS-03] **멈춘다** — 이 DB 에는 이미 마이그레이션 %d건이 적용돼 있다. "
                "이 명령은 **빈 DB 설치용**이다. 이미 선 DB 에 스키마를 대는 일은 "
                "D-283 절차(① sqlmigrate ② 역방향 ③ 스냅샷 ④ migrate ⑤ verify)를 "
                "밟은 사람이 한다. 그래도 진행하려면 `--force`." % applied)
    return None


def applied_count() -> int:
    """이 DB 에 이미 적용된 마이그레이션 수. **0 이면 빈 DB 다.**"""
    try:
        return MigrationRecorder(connection).migration_qs.count()
    except Exception:                                        # noqa: BLE001
        # 표 자체가 없으면 빈 DB 다 — 예외를 「많다」로 읽지 않는다.
        return 0


class Command(BaseCommand):
    help = "빈 DB 를 한 줄로 세운다 (OPS-03 · 잠금 MIGRATE_ONE_LINER 우회층)"

    def add_arguments(self, parser):
        parser.add_argument("--plan", action="store_true",
                            help="무엇을 할지만 보인다. **DB 를 만지지 않는다**")
        parser.add_argument("--force", action="store_true",
                            help="이미 마이그레이션이 적용된 DB 에서도 진행한다 "
                                 "(D-283 절차를 밟은 사람만 쓴다)")

    def handle(self, *args, **options):
        steps = planned_steps()
        self.stdout.write("[OPS-03] 걸음 %d개: %s" % (len(steps), " → ".join(steps)))
        self.stdout.write(
            "[OPS-03] 왜 이 순서인가: dj-core `logger/0009` 가 `multilanguage` 의존을 "
            "선언하지 않는다. 그 파일은 §0.4 라 못 고치고, 순서 제약을 우리 쪽에 "
            "선언하면 **이미 도는 DB 가 전부 죽는다**(실측). 그래서 선언이 아니라 "
            "**집행**한다.")

        if options["plan"]:
            self.stdout.write("[OPS-03] `--plan` 이라 DB 를 만지지 않았다.")
            return

        refusal = refuse_reason(applied_count(), force=options["force"])
        if refusal:
            raise CommandError(refusal)

        for app in BOOTSTRAP_ORDER:
            self.stdout.write("[OPS-03] migrate %s" % app)
            call_command("migrate", app, verbosity=options.get("verbosity", 1))
        self.stdout.write("[OPS-03] migrate (전체)")
        call_command("migrate", verbosity=options.get("verbosity", 1))

        # ★ 「돌았다」와 「맞다」는 다르다. 스스로 확인한다.
        self.stdout.write("[OPS-03] migrate --check")
        call_command("migrate", check_unapplied=True, verbosity=0)
        self.stdout.write(
            "[OPS-03] 세웠다 — 적용 %d건 · 정합 확인 통과. **한 줄이다.**"
            % applied_count())
