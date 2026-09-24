# -*- coding: utf-8 -*-
"""P-329 — **가른 이름만 지운다** (차선 Q · 2026-09-26 · WO-GX-20260924-13 §5 P-329).

무엇이 문제였나
---------------
QA-11 다툼 가드(`conftest.split_when_busy`)는 두 실행이 같은 시험 DB 이름을 쥐면
`_p<pid>` 로 갈라 제 DB 를 따로 갖는다. 정상 종료하면 pytest-django 자신의 teardown 이
그 DB 를 지우지만, **끝까지 못 간 실행**(죽거나 teardown 도중 다른 예외를 만난 실행)은
그 DB 를 남긴다 — 지금 찌꺼기 5개가 그 증거다.

무엇을 재는가 — 순수 판정만
---------------------------
`conftest.split_cleanup_target(original, final)` 은 **지울지 말지를 정하는 순수
함수**다(실제 DROP·연결은 `_drop_leftover_split_db` 가 하고, 그것은 DB 가 필요해
여기서 재지 않는다 — 그 부분은 실제 DB 통합 시험의 몫이지 이 파일의 몫이 아니다).

    가르지 않은 이름 (final == original)  →  None            — 지울 것이 없다
    가른 이름         (final != original)  →  final 그 이름 하나 — **그것만** 지운다
    다른 `_p<pid>` 이름                    →  이 함수가 애초에 볼 일이 없다
                                               (호출하는 쪽이 **제 이름**만 넘긴다)

★ 왜 이것이 순수 함수로 충분한가 — `django_db_modify_db_settings` 픽스처가 실제로
  하는 일은 「`split_cleanup_target(원래 이름, 정해진 이름)` 의 결과가 있으면 그
  이름 하나만 `request.addfinalizer` 에 건다」이다. 그 판정 논리를 이 함수 하나로
  뽑아 두었기 때문에, DB 도 pytest-django 도 없이 갈래를 확인할 수 있다.

⚠ 죽은(kill) 실행은 이 finalizer 자체가 못 돈다 — pytest 가 finalizer 를 부를 기회가
  없기 때문이다. 이 시험도, `conftest.py` 의 finalizer 도 그 자리는 못 채운다(정직하게
  적어 둔다 · `_drop_leftover_split_db` 의 docstring 참조).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from django.test import SimpleTestCase


def _conftest():
    """루트 conftest 를 **파일 경로로** 읽는다 (test_q_test_db_split.py 와 같은 관용구).

    이름(`conftest`)으로 import 하면 pytest 가 이미 올려 둔 다른 conftest 를 집을 수
    있다 — 마운트가 셋인 이 컨테이너에서 그 착각은 실제로 일어난다.
    """
    path = Path(__file__).resolve().parent.parent / "conftest.py"
    spec = importlib.util.spec_from_file_location("gx_root_conftest_p329", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SplitCleanupTargetTest(SimpleTestCase):
    """가른 이름만 지운다 — 가르지 않은 이름은, 남의 이름은 절대 아니다."""

    def setUp(self) -> None:
        self.target = _conftest().split_cleanup_target

    def test_an_unsplit_name_is_not_cleaned(self) -> None:
        """다투지 않은 평시 실행 — `original == final` 이면 지울 것이 없다."""
        self.assertIsNone(self.target("test_gx_q", "test_gx_q"))

    def test_a_split_name_is_the_one_target(self) -> None:
        """다퉈서 갈린 실행 — **갈린 그 이름 하나만** 돌려준다."""
        self.assertEqual(
            self.target("test_gx_q", "test_gx_q_p4242"), "test_gx_q_p4242")

    def test_the_original_name_is_never_the_target(self) -> None:
        """갈렸어도 돌려주는 것은 **갈린 이름**이지 원래 이름이 아니다.

        원래 이름은 「다투고 있는 다른 실행」이 쥔 이름이다 — 그것을 지우면
        남의 DB 를 지우는 것이고, 이 finalizer 의 헌법(P-329)이 금지하는 바로 그 일이다.
        """
        got = self.target("test_gx_shared", "test_gx_shared_p777")
        self.assertNotEqual(got, "test_gx_shared")
        self.assertEqual(got, "test_gx_shared_p777")

    def test_a_different_processs_split_name_is_not_manufactured(self) -> None:
        """이 함수는 **넘겨받은 두 이름 말고는 아무것도 모른다.**

        다른 프로세스가 갈라 둔 `_p<다른pid>` 이름은 이 함수의 인자로 들어오지
        않는 한 존재조차 하지 않는다 — 그래서 「남의 `_p<pid>` 이름은 안 지운다」는
        이 함수가 지키는 규칙이 아니라, 이 함수가 **그런 이름을 만들어 낼 방법이
        없다**는 사실이다. 그 사실을 코드로 확인해 둔다: 이 함수가 낸 결과는
        언제나 두 입력 중 하나(`final`)이거나 `None` 이지, 제3의 이름이 아니다.
        """
        other_pid_name = "test_gx_shared_p999999"
        result = self.target("test_gx_shared", "test_gx_shared_p777")
        self.assertNotEqual(result, other_pid_name)
        self.assertIn(result, ("test_gx_shared", "test_gx_shared_p777", None))

    def test_pure_no_side_effects_hint(self) -> None:
        """순수 함수라 **몇 번을 불러도** 같은 입력에 같은 답 — DB 를 열지 않는다.

        (DB 접속이 있었다면 이 시험 파일은 실제 psycopg2/postgres 연결 없이는
        여기서 이미 실패했을 것이다 — 통과 자체가 「부작용이 없다」는 증거다.)
        """
        target = self.target
        first = target("test_gx_k", "test_gx_k_p1")
        second = target("test_gx_k", "test_gx_k_p1")
        self.assertEqual(first, second)


class DropLeftoverIsOptedInOnlyTest(SimpleTestCase):
    """`_drop_leftover_split_db` 는 **이름을 받아야만** 움직인다 — 스스로 이름을 고르지 않는다."""

    def test_the_function_exists_and_takes_exactly_a_name(self) -> None:
        import inspect

        fn = _conftest()._drop_leftover_split_db
        params = list(inspect.signature(fn).parameters)
        self.assertEqual(params, ["name"], "이 함수가 이름 말고 다른 것을 더 받으면 "
                          "「무엇을 지울지」를 스스로 정할 길이 생긴다 — 그것은 대표 결정이다")
