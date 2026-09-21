# -*- coding: utf-8 -*-
"""P-202 회귀 — **가드가 무너지면 이 파일이 빨강이 된다** (2026-09-21 · 턴 Z · 차선 S).

캐시 처리: 해당 없음 — HTTP 를 한 번도 안 탄다. DB 도 안 탄다(전부 `SimpleTestCase`).

★ 이 파일이 재는 것은 `tests/test_law08_prod_writes.py` 와 **다르다.**
  저쪽은 *「가드가 지금 막는가」*를 누른다. 이쪽은 *「가드가 무너지면 우리가 그것을
  알아채는가」*를 누른다 — **음성 대조를 파일 안에 넣는다.**

  턴 Y 에 그 A/B 를 **손으로** 했다: 제품 코드를 일부러 고쳐 5 failed 를 확인하고 되돌렸다.
  손으로 한 A/B 는 그 자리에서 증발한다. 다음 사람이 `audit_db_isolated` 를 한 줄
  느슨하게 고쳐도 시험은 전부 초록일 수 있고, 아무도 그 사실을 모른다.
  그래서 **망가뜨리는 다섯 가지 방식**을 여기 박아 두고, 각각이 탐침에 **잡히는지** 본다.

⚠ **분모를 같이 둔다** (D-301). 「망가뜨리면 안 막는다」만 재면 가드를 `raise` 한 줄로
  바꿔도 이 파일이 초록이다. 그래서 ① 가드가 무장돼 있는가 ② 시험 DB 는 **안** 막는가
  ③ 문 다섯이 실제로 가드를 지나는가 를 **먼저** 누른다.

★ **턴 AA 에 넓혔다**(차선 S · P-219): U24 가 `apps/dsm/audit.py` 를 쥐는 턴이라
  **그 위쪽 모듈이 `audit_writer` 를 비켜 표에 직접 닿는 길**을 따로 잰다(②′ 두 벌).
  가드는 `audit_writer` 아래 **한 자리**에만 있으므로, 앱 모듈이 우회로를 한 줄 내면
  기존 열아홉 건은 **전부 초록인 채로** 그 길에서 가드가 사라진다.

⚠ **운영 표에 한 행도 안 쓴다.** 이 파일은 연결을 한 번도 안 연다 — 가리키는 DB 를
  바꾸는 대신 `evidence_chain.audit_db_name` **하나만** 갈아 끼운다. 가드의 입력은
  「이 alias 가 가리키는 이름」이고, 그 이름을 받고 내리는 **판단**이 이 시험의 과녁이다.
"""
from __future__ import annotations

import os

from django.test import SimpleTestCase

from common import audit_writer, evidence_chain

#: 운영 DB 처럼 생긴 이름. **실제 운영 이름을 적지 않는다** — 적으면 「그 이름만」 막는
#: 시험이 되고, 이름이 바뀌는 날 조용히 아무것도 안 잰다.
LOOKS_LIKE_PROD = "guardianx_live_2"

#: 시험 DB 처럼 생긴 이름 — 가드가 **통과시켜야** 하는 쪽(분모).
LOOKS_LIKE_TEST = "test_gx_s"

#: 탐침이 가드에 건네는 낱말. 예외문에 그대로 실린다.
DEED = "회귀탐침"


class _Named:
    """`audit_db_name` 이 이 이름을 내놓게 한다 — 그리고 되돌린다. **연결은 안 연다.**"""

    def __init__(self, name: str) -> None:
        self.name = name

    def __enter__(self):
        self.keep = evidence_chain.audit_db_name
        evidence_chain.audit_db_name = lambda alias="default": self.name
        return self

    def __exit__(self, *exc):
        evidence_chain.audit_db_name = self.keep
        return False


class _Env:
    """환경변수 한 칸을 세웠다 되돌린다 (`DB_TEST_NAME` 은 가드가 실제로 읽는다)."""

    def __init__(self, key: str, value: str) -> None:
        self.key, self.value = key, value

    def __enter__(self):
        self.keep = os.environ.get(self.key)
        if self.value:
            os.environ[self.key] = self.value
        else:
            os.environ.pop(self.key, None)
        return self

    def __exit__(self, *exc):
        if self.keep is None:
            os.environ.pop(self.key, None)
        else:
            os.environ[self.key] = self.keep
        return False


class _Sabotage:
    """가드를 **일부러 망가뜨린다** — 그리고 반드시 되돌린다.

    ⚠ 되돌리기가 `__exit__` 에 있어야 한다. 한 번이라도 새면 그 뒤의 모든 시험이
      가드 없이 도는 실행이 되고, 그 초록은 턴 X 사고를 그대로 다시 부른다.
      그래서 마지막에 「안 샜는가」를 따로 누른다(`SabotageNeverLeaksTest`).
    """

    def __init__(self, **attrs) -> None:
        self.attrs = attrs

    def __enter__(self):
        self.keep = {k: getattr(evidence_chain, k) for k in self.attrs}
        for k, v in self.attrs.items():
            setattr(evidence_chain, k, v)
        return self

    def __exit__(self, *exc):
        for k, v in self.keep.items():
            setattr(evidence_chain, k, v)
        return False


def guard_stops(name: str, *, want: str = "") -> bool:
    """**탐침** — 이 이름 앞에서 가드가 서는가. 부르는 것은 가드 하나뿐이다."""
    with _Named(name), _Env("DB_TEST_NAME", want):
        try:
            evidence_chain.guard_audit_db(doing=DEED)
        except evidence_chain.AuditDbNotIsolated:
            return True
    return False


# ══════════════════════════════════════════════════════════════════════════
# ① 분모 — 망가뜨리기 전에, 지금 서 있는가부터 본다
# ══════════════════════════════════════════════════════════════════════════

class TheGuardStandsTest(SimpleTestCase):

    def test_the_guard_is_armed_in_this_run(self) -> None:
        """★ 이것이 거짓이면 **이 파일 전체가 아무것도 안 재는 초록**이 된다."""
        self.assertTrue(
            evidence_chain.guard_is_armed(),
            "가드가 무장 안 된 실행이다 — 아래 시험들은 전부 헛것이다 "
            "(conftest.pytest_configure · evidence_guard.under_pytest 확인)")

    def test_a_prod_shaped_name_is_stopped(self) -> None:
        self.assertTrue(guard_stops(LOOKS_LIKE_PROD))

    def test_a_test_shaped_name_is_not_stopped(self) -> None:
        """★ 분모. 「다 막는 가드」는 `raise` 한 줄이고, 그것은 가드가 아니다."""
        self.assertFalse(guard_stops(LOOKS_LIKE_TEST, want=LOOKS_LIKE_TEST))

    def test_the_red_carries_the_deed_and_the_name(self) -> None:
        """빨강이 **스스로 설명해야** 다음 사람이 「쓰기만 막으면 되나」로 안 읽는다."""
        with _Named(LOOKS_LIKE_PROD):
            with self.assertRaises(evidence_chain.AuditDbNotIsolated) as caught:
                evidence_chain.guard_audit_db(doing=DEED)
        text = str(caught.exception)
        self.assertIn(DEED, text)
        self.assertIn(LOOKS_LIKE_PROD, text)


# ══════════════════════════════════════════════════════════════════════════
# ② 배선 — 문 다섯이 **정말로** 가드를 지나는가 (지나는 것을 세어서 본다)
# ══════════════════════════════════════════════════════════════════════════

class _Sentinel(Exception):
    """가드 자리에 세워 두는 표식. 이것이 안 올라오면 그 문은 가드를 안 지난 것이다."""


def door_goes_through_the_guard(case, call, expected_deed: str) -> None:
    """이 호출이 **가드를 지나는가** — 예외 종류가 아니라 「가드가 불렸다」를 센다.

    표식이 가드 자리에서 올라오므로 그 뒤의 DB 작업은 한 줄도 안 돈다.
    `SimpleTestCase` 는 DB 를 건드리는 순간 죽으므로, 초록 자체가
    **「가드 앞에서는 아직 아무것도 안 했다」**는 증거다.
    """
    seen: list[str] = []

    def record(*, doing: str, alias: str = "default") -> None:
        seen.append(doing)
        raise _Sentinel(doing)

    with _Sabotage(guard_audit_db=record):
        with case.assertRaises(_Sentinel):
            call()
    case.assertEqual(seen[0], expected_deed)


class EveryDoorGoesThroughTheGuardTest(SimpleTestCase):
    """★ 「예외가 난다」가 아니라 **「가드가 불렸다」**를 센다.

    `AuditDbNotIsolated` 만 보면, 누가 그 문에서 가드 호출을 지우고 다른 자리에서 같은
    예외를 내도 초록이다. 표식을 세워 **그 문이 가드를 지났다는 사실 자체**를 잡는다.
    그리고 표식이 그 자리에서 올라오므로 그 뒤의 DB 작업은 한 줄도 안 돈다 —
    `SimpleTestCase` 는 DB 를 건드리는 순간 죽으므로, 초록 자체가
    **「가드 앞에서는 아직 아무것도 안 했다」**는 증거다.
    """

    def _door(self, call, expected_deed: str) -> None:
        door_goes_through_the_guard(self, call, expected_deed)

    def test_the_chain_query_door(self) -> None:
        self._door(evidence_chain._model, "묻기")

    def test_the_chain_verifier_door(self) -> None:
        self._door(evidence_chain.verify_chain, "묻기")

    def test_the_writer_query_door(self) -> None:
        self._door(audit_writer._model, "묻기")

    def test_the_writer_read_door(self) -> None:
        self._door(lambda: audit_writer.read(logger_name="guardianx.test.p202"), "묻기")

    def test_the_write_door_stops_before_the_transaction(self) -> None:
        """★★ **쓰기는 트랜잭션을 열기 전에** 가드를 지나야 fail-closed 가 글자 그대로다.

        표식이 올라온 뒤로 `transaction.atomic()` 도 advisory lock 도 INSERT 도 안 돈다.
        가드가 `atomic()` **안쪽**으로 밀려나는 순간 이 갈래가 다른 예외로 빨개진다.
        """
        self._door(
            lambda: audit_writer.write(
                logger_name="guardianx.test.p202", tag="[P-202]", actor=None,
                action="selftest", outcome=audit_writer.ALLOWED,
                reason="여기까지 오면 안 된다"),
            "쓰기")


# ══════════════════════════════════════════════════════════════════════════
# ②′ 감사 쓰기 경로가 **움직일 때** — `apps/dsm/audit.py` 의 문 넷 (턴 AA · P-219)
# ══════════════════════════════════════════════════════════════════════════
#
# ★ 턴 AA 에 U24 가 `apps/dsm/audit.py` 와 `incident_report.py` 를 쥔다(P-219).
#   위 ②는 `common/audit_writer` 의 문만 잰다 — 그 아래를 지나는 한 가드는 선다.
#   그런데 **위쪽 모듈이 `audit_writer` 를 비켜 표에 직접 닿으면** ② 는 초록인 채로
#   가드가 사라진다. 한 줄(`apps.get_model("logger", "AuditLogs")`)이면 그렇게 된다.
#   그래서 여기서 **앱 쪽 문 넷**과 **「비켜 가는 길이 없다」**를 따로 누른다.

def _writing_scope():
    """행위자 없는 스코프. **DB 를 안 탄다** — 쓰기 문은 `scope.actor` 만 읽는다."""
    from common.tenant_scope import TenantScope

    return TenantScope.system(reason="P-202 회귀탐침 — 여기서 서야 한다")


def _reading_scope():
    """`require_actor()` 만 통과시키는 가짜 행위자. 표식이 그 직후에 올라온다."""
    from common.tenant_scope import TenantScope

    return TenantScope.of(object())


class DsmAuditDoorsGoThroughTheGuardTest(SimpleTestCase):
    """`apps/dsm/audit.py` 의 문 넷이 **전부** 가드를 지나는가."""

    def _door(self, call, expected_deed: str) -> None:
        door_goes_through_the_guard(self, call, expected_deed)

    def test_the_f12_settings_write_door(self) -> None:
        from apps.dsm import audit as dsm_audit

        self._door(
            lambda: dsm_audit.record(
                scope=_writing_scope(), action="selftest",
                outcome=dsm_audit.ALLOWED, reason="여기까지 오면 안 된다"),
            "쓰기")

    def test_the_event_action_write_door(self) -> None:
        from apps.dsm import audit as dsm_audit

        self._door(
            lambda: dsm_audit.record_event_action(
                scope=_writing_scope(), action="selftest",
                outcome=dsm_audit.ALLOWED, reason="여기까지 오면 안 된다"),
            "쓰기")

    def test_the_f12_entries_read_door(self) -> None:
        from apps.dsm import audit as dsm_audit

        self._door(lambda: dsm_audit.entries(limit=1), "묻기")

    def test_the_tenant_scoped_page_read_door(self) -> None:
        """★ 화면(`AuditLog.tsx`)이 실제로 타는 문이다 — 이 턴에 U24 가 여는 자리."""
        from apps.dsm import audit as dsm_audit

        self._door(
            lambda: dsm_audit.read_page(scope=_reading_scope(), page=1, page_size=1),
            "묻기")


#: 감사 표가 사는 앱 라벨. 이 이름으로 모델을 직접 집으면 `audit_writer` 를 비켜 간다.
AUDIT_APP_LABEL = "logger"


def reaches_the_audit_table_directly(source: str) -> list[str]:
    """이 소스가 **`audit_writer` 를 비켜** 감사 표에 닿는 자리들. AST 로 본다.

    ⚠ 본문 문자열이 아니라 **구문**을 본다 — 이 파일들의 머리말에는 `logger.AuditLogs`
      가 설명으로 여러 번 나온다. 낱말을 세면 주석 한 줄에 빨개지고, 그런 시험은
      다음 사람이 주석을 고쳐서 초록으로 만든다.
    """
    import ast

    found: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name == "get_model":
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and \
                            str(arg.value).lower() == AUDIT_APP_LABEL:
                        found.append(f"get_model({arg.value!r}, …) @{node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            head = str(node.module or "").split(".")[0]
            if head == AUDIT_APP_LABEL:
                found.append(f"from {node.module} import … @{node.lineno}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if str(alias.name).split(".")[0] == AUDIT_APP_LABEL:
                    found.append(f"import {alias.name} @{node.lineno}")
    return found


class NoDoorBypassesTheWriterTest(SimpleTestCase):
    """★ 가드는 `audit_writer` 아래에 **한 자리**만 있다. 그래서 위쪽 모듈이
    표에 직접 닿는 길을 내면 가드는 그 길에서만 조용히 없다 — 초록인 채로.
    """

    def test_the_scanner_catches_a_bypass(self) -> None:
        """★ 분모. 스캐너가 실제로 무언가를 잡는다는 것을 먼저 고정한다."""
        bypass = (
            "from django.apps import apps\n"
            "def leak():\n"
            f"    return apps.get_model({AUDIT_APP_LABEL!r}, 'AuditLogs')\n")
        self.assertEqual(len(reaches_the_audit_table_directly(bypass)), 1)

    def test_an_innocent_module_is_not_flagged(self) -> None:
        """★ 분모의 반대쪽. 「다 잡는 스캐너」는 스캐너가 아니다."""
        clean = (
            "from django.apps import apps\n"
            "'logger.AuditLogs 는 설명으로만 나온다'\n"
            "def fine():\n"
            "    return apps.get_model('user', 'CoreUser')\n")
        self.assertEqual(reaches_the_audit_table_directly(clean), [])

    def _scan(self, module) -> list[str]:
        import inspect

        path = inspect.getsourcefile(module)
        self.assertTrue(path, f"{module.__name__} 의 소스를 못 찾았다")
        with open(path, encoding="utf-8") as fh:
            return reaches_the_audit_table_directly(fh.read())

    def test_the_dsm_audit_module_does_not_bypass_the_writer(self) -> None:
        from apps.dsm import audit as dsm_audit

        self.assertEqual(
            self._scan(dsm_audit), [],
            "apps/dsm/audit.py 가 감사 표를 직접 집는다 — 그 길에는 P-202 가드가 없다. "
            "감사 표에 닿는 길은 common/audit_writer 하나여야 한다(D-325 표 ②)")

    def test_the_incident_report_module_does_not_bypass_the_writer(self) -> None:
        from apps.dsm import incident_report

        self.assertEqual(
            self._scan(incident_report), [],
            "apps/dsm/incident_report.py 가 감사 표를 직접 집는다 — 같은 이유로 막힌다")


# ══════════════════════════════════════════════════════════════════════════
# ③ 음성 대조 — **일부러 망가뜨린다.** 탐침이 못 잡으면 이 파일이 빨강이다
# ══════════════════════════════════════════════════════════════════════════

def _permissive(name, *, want=""):
    """① 「시험이 자꾸 빨개져서」 술어를 통과로 바꾼 판."""
    return True


def _floor_dropped(name, *, want=""):
    """② `test_` 바닥을 빼고 `DB_TEST_NAME` 만 보는 판 — 끌 수 있는 규칙은 결국 꺼진다."""
    got = str(name or "")
    wanted = str(want or "")
    return got.startswith(wanted) if wanted else True


def _unknown_is_fine(name, *, want=""):
    """③ 「이름을 못 읽었다」를 「괜찮다」로 접은 판 — fail-open 의 고전."""
    got = str(name or "")
    if not got:
        return True                       # ← 여기가 망가진 한 줄
    return got.startswith(evidence_chain.TEST_DB_PREFIX)


def _warn_only(*, doing: str, alias: str = "default") -> None:
    """④ 예외를 경고로 강등한 판 — 「로그는 남으니 괜찮다」."""
    return None


def _never_armed() -> bool:
    """⑤ 무장 신호가 둘 다 죽은 판 — 가드는 있는데 아무 데서도 안 선다."""
    return False


class BreakingTheGuardIsCaughtTest(SimpleTestCase):
    """다섯 가지 망가짐이 **각각** 탐침에 잡히는가.

    ★ 잡힌다는 것은 곧 「그때 ①·② 의 시험들이 빨강이 된다」는 뜻이다.
      망가진 판에서도 탐침이 그대로 참이면, 그 시험들은 망가진 가드에도 초록을 낸다 —
      **「통과한다」만 증명하고 「무너지면 잡는다」는 증명하지 않는 시험**이 된다.
    """

    def test_the_probe_is_true_while_nothing_is_broken(self) -> None:
        """★ 분모. 아래 갈래들의 `False` 가 **망가뜨림 때문**임을 여기서 고정한다."""
        self.assertTrue(guard_stops(LOOKS_LIKE_PROD))

    def test_a_permissive_predicate_is_caught(self) -> None:
        with _Sabotage(audit_db_isolated=_permissive):
            self.assertFalse(
                guard_stops(LOOKS_LIKE_PROD),
                "술어를 통과로 바꿔도 탐침이 참이다 — 이 파일은 가드를 안 재고 있다")

    def test_dropping_the_test_prefix_floor_is_caught(self) -> None:
        with _Sabotage(audit_db_isolated=_floor_dropped):
            self.assertFalse(
                guard_stops(LOOKS_LIKE_PROD),
                "바닥이 사라졌는데 탐침이 참이다 — 환경변수 한 칸으로 가드가 열린다")

    def test_treating_an_unknown_name_as_fine_is_caught(self) -> None:
        with _Sabotage(audit_db_isolated=_unknown_is_fine):
            self.assertFalse(
                guard_stops(""),
                "이름을 모르는데 통과시킨다 — 「모르면 막는다」가 사라졌다")

    def test_downgrading_the_raise_to_a_warning_is_caught(self) -> None:
        with _Sabotage(guard_audit_db=_warn_only):
            self.assertFalse(
                guard_stops(LOOKS_LIKE_PROD),
                "예외가 경고로 내려갔는데 탐침이 참이다 — 그 경고는 아무도 안 본다")

    def test_a_guard_that_never_arms_is_caught(self) -> None:
        with _Sabotage(guard_is_armed=_never_armed):
            self.assertFalse(
                guard_stops(LOOKS_LIKE_PROD),
                "무장이 죽었는데 탐침이 참이다 — 가드가 어디서도 안 서는데 초록이다")

    def test_a_door_that_lost_its_guard_call_is_caught(self) -> None:
        """★ 배선이 빠지는 쪽도 같이 본다 — ②가 무엇을 재는지의 음성 대조다."""
        with _Named(LOOKS_LIKE_PROD):
            with self.assertRaises(evidence_chain.AuditDbNotIsolated):
                evidence_chain._model()                 # 가드가 있을 때: 선다
            with _Sabotage(guard_audit_db=_warn_only):
                evidence_chain._model()                 # 가드가 빠지면: 그냥 지나간다


class SabotageNeverLeaksTest(SimpleTestCase):
    """★ 망가뜨린 판이 한 번이라도 새면 **그 뒤의 모든 초록이 거짓**이다.

    이름이 `S` 로 시작해 위 세 벌보다 **뒤에 돈다**(`-p no:randomly` 기준).
    한 벌이라도 되돌리기를 빠뜨리면 여기서 잡힌다.
    """

    def test_the_real_predicate_is_back(self) -> None:
        self.assertEqual(evidence_chain.audit_db_isolated.__module__,
                         evidence_chain.__name__)
        self.assertFalse(evidence_chain.audit_db_isolated(LOOKS_LIKE_PROD))
        self.assertTrue(evidence_chain.audit_db_isolated(LOOKS_LIKE_TEST))

    def test_the_real_guard_is_back(self) -> None:
        self.assertTrue(guard_stops(LOOKS_LIKE_PROD))

    def test_the_real_name_reader_is_back(self) -> None:
        """`audit_db_name` 이 **진짜 설정**을 다시 읽는가 (내 가짜가 아니라).

        ★ [실측 2026-09-21 · 턴 Z] 처음엔 여기서 「그리고 그 이름은 시험 DB 다」까지
          주장했고 **빨개졌다** — 이 파일은 `SimpleTestCase` 뿐이라 시험 DB 가 **아예 서지
          않는다.** 그 실행에서 `default` 가 가리키는 이름은 아직 운영 이름
          (`database_guardianx`)이다. 고칠 것은 제품이 아니라 이 주장이었다.

        ⚠ 그리고 그 사실이 이 가드가 왜 있는지를 그대로 말한다: **시험 DB 가 서기 전의
          창에서 감사표를 건드리면 그것은 운영 표다.** 턴 X 의 219행이 샌 자리가 바로
          그 창(픽스처 안)이었다. 그래서 이 창에서 가드는 **서 있어야 맞다** —
          아래 `test_the_real_guard_is_back` 이 그 창에서 실제로 선다는 것을 누른다.
        """
        from django.db import connections

        live = str(connections["default"].settings_dict.get("NAME") or "")
        self.assertEqual(evidence_chain.audit_db_name("default"), live)
        self.assertNotEqual(evidence_chain.audit_db_name("default"), LOOKS_LIKE_PROD)
