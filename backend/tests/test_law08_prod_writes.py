# -*- coding: utf-8 -*-
"""P-202 — **시험은 운영 감사표에 한 행도 안 쓴다** (2026-09-20 · 턴 Y · 차선 S).

캐시 처리: 해당 없음 — HTTP 를 한 번도 안 탄다. 감사표와 DB 설정만 만진다.

출생 표본 — 이 시험이 생긴 것은 **차선 S 의 사고 때문이다** [실측 2026-09-20 · 턴 X]
------------------------------------------------------------------------------
시험 DB 다툼 가드의 첫 판이 「이 DB 에 누가 붙어 있나」를 **장고 연결로 물었다.**
묻는 행위 자체가 그 뒤의 `create_test_db` 를 바꿨고, 시험 셋이 운영 DB 에 붙어
운영 감사표에 `guardianx.test.law08_race` **219행**을 남겼다. 그 무리 안에서 체인이
갈려 끊김 **#276795** 가 났고, 그 행들은 **지울 수도 고칠 수도 없다**(P-191 · 대표 결정).

    ★ 그래서 이 시험의 과녁은 둘이다. 「쓰기가 막히나」만 보면 **사고의 원인을 안 보는
      것**이다 — 원인은 묻는 행위였다. 「묻기도 막히나」가 같은 무게의 과녁이다.

⚠ **가드가 다 막으면 안 된다.** 「예외가 난다」만 재면 가드를 `raise` 한 줄로 바꿔도
  초록이다. 그래서 정상 실행(시험 DB)에서 쓰기가 **실제로 성공하는** 갈래를 같이 둔다 —
  분모 없는 초록은 초록이 아니다(D-301).
"""
from __future__ import annotations

import os

from django.apps import apps
from django.db import connections
from django.test import SimpleTestCase, TestCase

from common import audit_writer, evidence_chain, evidence_guard

#: 운영 DB 이름처럼 생긴 것. **실제 운영 이름을 여기 적지 않는다** — 적으면 이 시험이
#: 「그 이름」만 막는 시험이 되고, 이름이 바뀌는 날 조용히 아무것도 안 잰다.
LOOKS_LIKE_PROD = "guardianx-v2"


class AuditDbIsolatedTest(SimpleTestCase):
    """순수 술어 — DB 도 장고 연결도 없이 갈래를 전부 눌러 본다."""

    def test_an_empty_name_is_blocked(self) -> None:
        """★ **모르면 막는다.** 「못 읽었다」를 「괜찮다」로 접으면 가드가 사라진다."""
        self.assertFalse(evidence_chain.audit_db_isolated(""))
        self.assertFalse(evidence_chain.audit_db_isolated(None))  # type: ignore[arg-type]

    def test_the_prod_name_is_blocked(self) -> None:
        self.assertFalse(evidence_chain.audit_db_isolated(LOOKS_LIKE_PROD))

    def test_a_test_name_passes(self) -> None:
        self.assertTrue(evidence_chain.audit_db_isolated("test_guardianx-v2"))

    def test_the_lane_name_must_be_the_prefix(self) -> None:
        """`DB_TEST_NAME` 을 준 실행에서는 **그 접두**여야 한다 (P-18 차선별 이름)."""
        self.assertTrue(
            evidence_chain.audit_db_isolated("test_gx_s", want="test_gx_s"))
        self.assertFalse(
            evidence_chain.audit_db_isolated("test_gx_q", want="test_gx_s"))

    def test_the_suffixes_that_really_get_appended_still_pass(self) -> None:
        """xdist 의 `_gw0` 와 다툼 가드의 `_p<pid>` 는 **실제로 붙는다**(턴 X)."""
        for name in ("test_gx_s_gw0", "test_gx_s_p131482", "test_gx_s_e2e"):
            with self.subTest(name=name):
                self.assertTrue(
                    evidence_chain.audit_db_isolated(name, want="test_gx_s"))

    def test_the_env_var_cannot_open_the_floor(self) -> None:
        """★ **환경변수 하나로 가드를 끌 수 없다.**

        누가 `DB_TEST_NAME` 에 운영 DB 이름을 넣으면 접두 검사는 통과한다.
        바닥(`test_`)을 함께 보지 않으면 그 순간 가드가 통째로 열린다 —
        끌 수 있는 규칙은 결국 꺼진다(D-353).
        """
        self.assertFalse(
            evidence_chain.audit_db_isolated(LOOKS_LIKE_PROD, want=LOOKS_LIKE_PROD))


class GuardIsArmedTest(SimpleTestCase):
    """**켜지는 신호가 둘**이다 — 하나에만 걸어 두면 안 도는 실행이 생긴다."""

    #: 「지금 시험이 도는가」의 **정본 술어**가 보는 깃발들. 이름을 여기서 베끼지 않는다 —
    #: 술어가 한 자리에 있다는 것이 D-369 의 요점이고, 그 자리가 이름도 들고 있다.
    FLAGS = ("PYTEST_CURRENT_" + "TEST", evidence_guard.SESSION_ENV)

    def test_the_shared_predicate_alone_arms_it(self) -> None:
        """★ `backend/conftest.py` 가 **안 읽히는** 실행에서도 가드가 돈다.

        rootdir 이 어긋나면 그 conftest 는 아예 안 읽힌다(시험 명령 메모의 ⚠).
        무장을 거기 하나에만 걸어 두면 가드가 조용히 없는 실행이 생기고,
        그 실행이 바로 턴 X 의 사고다.
        """
        evidence_chain.arm_audit_db_guard(armed=False)
        try:
            self.assertTrue(evidence_guard.under_pytest())
            self.assertTrue(evidence_chain.guard_is_armed())
        finally:
            evidence_chain.arm_audit_db_guard()

    def test_a_run_with_neither_signal_is_not_guarded(self) -> None:
        """운영 프로세스에는 신호가 하나도 없다 — 거기서는 **한 글자도 안 바뀐다**."""
        evidence_chain.arm_audit_db_guard(armed=False)
        keep = {f: os.environ.pop(f, None) for f in self.FLAGS}
        try:
            self.assertFalse(evidence_chain.guard_is_armed())
            # 무장 안 된 실행에서는 운영 이름이어도 안 선다 (막는 자리가 아니다)
            evidence_chain.guard_audit_db(doing="쓰기")
        finally:
            for flag, value in keep.items():
                if value is not None:
                    os.environ[flag] = value
            evidence_chain.arm_audit_db_guard()


class _PointsAtProd:
    """`default` alias 가 **운영 DB 를 가리키는 것처럼** 만든다 — 그리고 되돌린다.

    ⚠ 진짜로 운영 DB 에 붙이지 않는다. 바꾸는 것은 `settings_dict["NAME"]` 한 칸이고,
      그 칸은 **다음 연결을 열 때** 읽힌다. 가드가 서므로 그 연결은 열리지 않는다 —
      즉 이 시험은 운영 DB 에 한 번도 안 닿는다.
    """

    def __init__(self, name: str = LOOKS_LIKE_PROD, alias: str = "default") -> None:
        self.name, self.alias = name, alias

    def __enter__(self):
        self.keep = connections[self.alias].settings_dict.get("NAME")
        connections[self.alias].settings_dict["NAME"] = self.name
        return self

    def __exit__(self, *exc):
        connections[self.alias].settings_dict["NAME"] = self.keep
        return False


class ProdAuditIsFailClosedTest(TestCase):
    """**눌러서 본다** — 운영 alias 를 가리키게 해 놓고 실제로 쓰고·묻는다."""

    LOGGER = "guardianx.test.p202"

    def _rows(self):
        return apps.get_model("logger", "AuditLogs")._base_manager.filter(
            logger_name=self.LOGGER)

    def test_the_normal_write_still_works(self) -> None:
        """★ 분모. 가드가 **다 막는 물건이 아니라는 것**을 먼저 본다.

        이 갈래가 없으면 `guard_audit_db` 를 `raise` 한 줄로 바꿔도 아래 시험들이
        전부 초록이다 — 그 초록은 아무것도 안 재는 초록이다.
        """
        before = self._rows().count()
        entry = audit_writer.write(
            logger_name=self.LOGGER, tag="[P-202]", actor=None,
            action="selftest", outcome=audit_writer.ALLOWED,
            reason="시험 DB 에서는 쓰기가 성립한다")
        self.assertTrue(entry.row_hash)
        self.assertEqual(self._rows().count(), before + 1)

    def test_writing_to_the_prod_alias_raises_before_the_write(self) -> None:
        """**쓰기 전에** 선다 — 행 수가 한 줄도 안 움직인다 (fail-closed)."""
        before = self._rows().count()
        with _PointsAtProd():
            with self.assertRaises(evidence_chain.AuditDbNotIsolated) as caught:
                audit_writer.write(
                    logger_name=self.LOGGER, tag="[P-202]", actor=None,
                    action="leak", outcome=audit_writer.ALLOWED,
                    reason="여기까지 오면 안 된다")
        self.assertIn("쓰기", str(caught.exception))
        self.assertEqual(self._rows().count(), before)

    def test_reading_the_prod_alias_also_raises(self) -> None:
        """★★ **「묻는 행위」도 막힌다** — 턴 X 사고의 원인이 묻는 행위였다."""
        with _PointsAtProd():
            with self.assertRaises(evidence_chain.AuditDbNotIsolated) as caught:
                audit_writer.read(logger_name=self.LOGGER)
        self.assertIn("묻기", str(caught.exception))

    def test_the_chain_verifier_is_blocked_too(self) -> None:
        """체인 검증도 감사표를 **묻는다.** 이 문도 같이 닫혀 있어야 한다."""
        with _PointsAtProd():
            with self.assertRaises(evidence_chain.AuditDbNotIsolated):
                evidence_chain.verify_chain()

    def test_the_message_says_which_db_and_why(self) -> None:
        """빨강이 **스스로 설명해야 한다.** 턴 X 의 빨강에는 DB 이름이 없었다."""
        with _PointsAtProd():
            with self.assertRaises(evidence_chain.AuditDbNotIsolated) as caught:
                audit_writer.read(logger_name=self.LOGGER)
        text = str(caught.exception)
        self.assertIn(LOOKS_LIKE_PROD, text)
        self.assertIn("P-202", text)
        self.assertIn("276795", text)


class TheGuardDoesNotAskTheDatabaseTest(TestCase):
    """★★ **가드가 자기가 막으려는 사고를 내면 안 된다** — 묻지 않고 설정을 읽는다.

    턴 X 의 사고는 「누가 붙어 있나」를 **장고 연결로 물어서** 났다. 이 가드가 같은
    짓을 하면 가드를 다는 것이 곧 사고다. 그래서 커서를 못 열게 막아 놓고 부른다 —
    열려고 하면 그 자리에서 죽는다.
    """

    def test_it_never_opens_a_cursor(self) -> None:
        conn = connections["default"]
        original = conn.cursor

        def explode(*a, **kw):
            raise AssertionError(
                "가드가 DB 에 물었다 — 묻는 행위가 다음 걸음을 바꾼다(턴 X 사고)")

        conn.cursor = explode          # type: ignore[method-assign]
        try:
            self.assertTrue(evidence_chain.audit_db_name("default"))
            evidence_chain.guard_audit_db(doing="묻기")       # 시험 DB → 안 선다
            with _PointsAtProd():
                with self.assertRaises(evidence_chain.AuditDbNotIsolated):
                    evidence_chain.guard_audit_db(doing="묻기")
        finally:
            conn.cursor = original     # type: ignore[method-assign]
