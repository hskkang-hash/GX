# -*- coding: utf-8 -*-
"""OPS-03 — 마이그레이션이 **한 줄로 선다** (잠금 `MIGRATE_ONE_LINER` 우회층 · 턴 C).

무엇이 막고 있었나: dj-core `logger/0009` 가 `multilanguage` 의존을 선언하지 않는다.
그 파일은 §0.4 라 못 고치고, 순서 제약을 **우리 쪽에 선언**해 봤더니 이미 도는 환경이
전부 `InconsistentMigrationHistory` 로 죽었다(되돌렸다).

    [대장 OPS-03 · hand: in] dj-core 는 못 고치지만 **우회 경로를 우리 층에 둔다.**

그래서 `manage.py migrate_bootstrap` 이 있다 — **선언이 아니라 집행**이다.
스키마를 한 줄도 바꾸지 않으므로 이미 선 DB 를 깨뜨리지 않는다.

이 시험이 못박는 것 넷
----------------------
  ① 걸음의 **순서** — 이 순서가 이 절의 내용 전부다
  ② 명령이 **실재**한다 (등록되지 않은 명령은 문서 속 명령이다)
  ③ `--plan` 은 **DB 를 만지지 않는다** — 안 만지는 걸음이 있어야 사람이 먼저 본다
  ④ 이미 선 DB 에서는 **멈춘다** — 설치 도구가 운영 DB 에서 돌면 그건 사고다(D-283)
"""
from __future__ import annotations

from io import StringIO

from django.core.management import call_command, get_commands
from django.test import TestCase

from common.management.commands.migrate_bootstrap import (
    BOOTSTRAP_ORDER,
    applied_count,
    planned_steps,
    refuse_reason,
)


class BootstrapOrderIsTheContentTest(TestCase):
    """① 순서. ★ 이 순서를 바꾸려면 **빈 DB 에서 다시 재고** 증거를 남겨라."""

    def test_user_comes_before_multilanguage(self):
        self.assertEqual(BOOTSTRAP_ORDER, ("user", "multilanguage"))

    def test_the_last_step_checks_itself(self):
        """「돌았다」와 「맞다」는 다르다 — 마지막 걸음이 `--check` 다."""
        steps = planned_steps()
        self.assertEqual(steps[-1], "migrate --check")
        self.assertEqual(steps[-2], "migrate",
                         "전체 migrate 가 `--check` 앞에 없다 — 확인할 것이 없다")

    def test_the_plan_is_not_empty(self):
        """0걸음과 「걸음을 못 읽었다」를 가른다 (D-301)."""
        self.assertGreaterEqual(len(planned_steps()), 4)


class TheCommandActuallyExistsTest(TestCase):
    """② 등록되지 않은 명령은 **문서 속 명령**이다 — 설치일에 그것이 드러난다."""

    def test_registered(self):
        self.assertIn("migrate_bootstrap", get_commands())


class PlanTouchesNothingTest(TestCase):
    """③ `--plan` 은 DB 를 만지지 않는다."""

    def test_plan_prints_the_steps_and_leaves_the_db_alone(self):
        before = applied_count()
        out = StringIO()
        call_command("migrate_bootstrap", "--plan", stdout=out)
        text = out.getvalue()
        for step in planned_steps():
            self.assertIn(step, text, "걸음 %r 이 계획 출력에 없다" % step)
        self.assertIn("DB 를 만지지 않았다", text)
        self.assertEqual(applied_count(), before)


class RefusesOnAnAlreadyStandingDatabaseTest(TestCase):
    """④ ★ **이 시험이 D-283 이다.**

    2026-08-29 에 컨테이너 재기동 하나가 `entrypoint.sh` 의 무조건 `migrate` 를 태워
    마이그레이션 4건이 절차 없이 적용됐다. 설치용 도구가 이미 선 DB 에서 조용히
    돌 수 있으면, 그 도구는 설치 도구가 아니라 **같은 사고의 다음 판**이다.

    ★ 판정을 **순수 함수로** 뽑아 두고 여기서 시험한다 — 시험용 DB 는 언제나 비어
      있으므로, 판정이 `handle()` 안에만 있으면 이 갈래는 **아무도 안 재는 갈래**가
      된다. 그런 판정은 있으나 마나다.
    """

    def test_it_refuses_when_migrations_are_already_applied(self):
        reason = refuse_reason(438, force=False)
        self.assertIsNotNone(reason, "이미 선 DB 인데 그냥 진행한다")
        self.assertIn("멈춘다", reason)
        self.assertIn("--force", reason,
                      "멈추기만 하고 **넘는 길**을 안 알려 주면 사람은 도구를 우회한다")
        self.assertIn("D-283", reason)

    def test_empty_database_passes(self):
        """음성 대조 — 빈 DB 까지 막으면 그것은 설치 도구가 아니다."""
        self.assertIsNone(refuse_reason(0, force=False))

    def test_force_is_the_only_way_through(self):
        """`--force` 는 **손으로** 켜는 곁길이다 — 저절로 열리는 문이 아니다."""
        self.assertIsNone(refuse_reason(438, force=True))
