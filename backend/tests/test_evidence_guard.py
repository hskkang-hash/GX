# -*- coding: utf-8 -*-
"""P-87 ④ — **시험은 운영 증거를 덮지 않는다.** 격리 가드가 실제로 도는가.

무엇을 지키는가 [실측 2026-09-06 · 턴 H · 차선 E]
------------------------------------------------
    시험 뒤 파일    : {"verdict": "SKIPPED_UNDECLARED",    "purged": 0}
    개발 DB 의 사실 : {"verdict": "SKIPPED_UNREVERSIBLE", "purged": 0}

시험이 `docs/agent/evidence/D-373/audit_purge_last.json` 을 **진짜로 고쳤다.**
그때 막은 자리는 한 곳뿐이었고, 한 자리만 막은 가드는 「막혀 있다」는 착시를 준다.

★ 이 파일이 재는 것은 **가드의 존재가 아니라 작동**이다. 「가드 코드가 있다」는
  시험은 아무것도 재지 않는다 — 실제로 쓰기를 던져 보고 막히는지를 본다.
"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from common import evidence_guard as G


class EvidencePathPredicateTest(unittest.TestCase):
    """`docs/agent/evidence/**` 를 **경로 조각으로** 가른다."""

    def test_positives(self) -> None:
        for p in ("/docs/agent/evidence/D-373/x.json",
                  "C:/GuardianX/guardianx-source/docs/agent/evidence/UX-20/a.txt",
                  "docs/agent/evidence/e2e/E2E-1/steps.md",
                  "/repo/docs/agent/evidence/W0-14/route_baseline.json"):
            self.assertTrue(G.is_evidence_path(p), p)

    def test_negatives(self) -> None:
        """문자열 `in` 으로 보면 걸리거나 빠지는 것들."""
        for p in ("/tmp/xdocs/agent/evidenceX/a.json",
                  "/docs/agent/a.json",
                  "/backup/20260906/dump.sql",
                  "/app/tests/test_x.py"):
            self.assertFalse(G.is_evidence_path(p), p)


class NetIsActuallyRunningTest(unittest.TestCase):
    """★ **그물이 이 실행에 실제로 걸려 있는가.** 안 걸렸으면 나머지는 다 무의미하다."""

    def test_net_installed(self) -> None:
        self.assertTrue(
            G.net_is_installed(),
            "증거 폴더 격리 그물이 안 걸렸다 — `backend/conftest.py` 의 "
            "`_install_evidence_net()` 이 안 불렸다. 가드가 없는데 "
            "「가드가 있다」고 읽히는 것이 가장 나쁜 자리다")

    def test_session_flag_is_set(self) -> None:
        """`PYTEST_CURRENT_TEST` 는 시험 하나가 도는 동안만 선다 —
        수집·픽스처에서 나는 쓰기까지 보려면 세션 깃발이 있어야 한다."""
        self.assertEqual(os.environ.get(G.SESSION_ENV), "1")
        self.assertTrue(G.under_pytest())


class NetBlocksWritesTest(unittest.TestCase):
    """쓰기 원시함수 넷에 던져 보고 **막히는지**를 본다."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.evi = Path(self._tmp.name) / "docs" / "agent" / "evidence" / "TI"
        self.evi.mkdir(parents=True, exist_ok=True)
        self.target = self.evi / "gate.json"
        self.plain = Path(self._tmp.name) / "plain.json"

    def tearDown(self) -> None:
        with G.allow_evidence_writes("이 시험이 만든 임시 증거 흉내를 치운다"):
            self._tmp.cleanup()

    def test_open_for_write_is_blocked(self) -> None:
        with self.assertRaises(G.EvidenceWriteBlocked):
            with open(self.target, "w", encoding="utf-8") as fh:
                fh.write("{}")
        self.assertFalse(self.target.exists(), "막혔다면서 파일이 생겼다")

    def test_path_write_text_is_blocked(self) -> None:
        with self.assertRaises(G.EvidenceWriteBlocked):
            self.target.write_text("{}", encoding="utf-8")
        self.assertFalse(self.target.exists())

    def test_append_is_blocked(self) -> None:
        """덮어쓰기만 막고 이어쓰기를 열어 두면 저널이 오염된다."""
        with self.assertRaises(G.EvidenceWriteBlocked):
            with open(self.target, "a", encoding="utf-8") as fh:
                fh.write("x")

    def test_rename_and_remove_are_blocked(self) -> None:
        """★ 「임시로 쓰고 갈아 끼우기」가 가장 흔한 덮어쓰기 모양이다."""
        src = Path(self._tmp.name) / "tmp.json"
        src.write_text("{}", encoding="utf-8")
        with self.assertRaises(G.EvidenceWriteBlocked):
            os.replace(str(src), str(self.target))
        with self.assertRaises(G.EvidenceWriteBlocked):
            os.rename(str(src), str(self.target))
        with self.assertRaises(G.EvidenceWriteBlocked):
            os.remove(str(self.target))

    def test_reading_evidence_is_not_blocked(self) -> None:
        """읽기는 막지 않는다 — 증거를 읽는 시험은 많고 그것은 정상이다."""
        with G.allow_evidence_writes("이 시험이 읽을 파일 하나를 만든다"):
            self.target.write_text('{"ok": 1}', encoding="utf-8")
        self.assertEqual(json.loads(self.target.read_text(encoding="utf-8")), {"ok": 1})

    def test_non_evidence_paths_are_untouched(self) -> None:
        """그물이 증거 폴더 밖까지 조이면 시험 전체가 못 돈다."""
        self.plain.write_text("{}", encoding="utf-8")
        self.assertTrue(self.plain.exists())

    def test_allow_context_closes_again(self) -> None:
        """예외는 **블록 동안만** 열린다 — 나가면서 닫히지 않으면 가드가 아니다."""
        with G.allow_evidence_writes("한 번만 연다"):
            self.target.write_text("1", encoding="utf-8")
        self.assertFalse(G.writes_allowed())
        with self.assertRaises(G.EvidenceWriteBlocked):
            self.target.write_text("2", encoding="utf-8")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "1")

    def test_allow_requires_a_reason(self) -> None:
        """이름 없는 예외는 다음 사람이 지울 수 없다."""
        with self.assertRaises(ValueError):
            with G.allow_evidence_writes("   "):
                pass


class CommonPredicateTest(unittest.TestCase):
    """공통 술어 — 부르는 쪽은 **안 썼다**를 사유와 함께 받는다."""

    def test_blocked_reason_names_the_path(self) -> None:
        why = G.blocked_reason("/docs/agent/evidence/D-373/x.json")
        self.assertIsNotNone(why)
        self.assertIn("D-373", why)

    def test_write_text_guarded_returns_none_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "docs" / "agent" / "evidence" / "TI" / "a.json"
            self.assertIsNone(G.write_text_guarded(target, "{}", who="시험"))
            self.assertFalse(target.exists())

    def test_non_evidence_write_goes_through(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sub" / "a.json"
            self.assertIsNotNone(G.write_text_guarded(target, "{}", who="시험"))
            self.assertEqual(target.read_text(encoding="utf-8"), "{}")


class OpsTasksDoesNotOverwriteRealEvidenceTest(unittest.TestCase):
    """★ **출생 표본** — 그날 덮인 그 파일을 그대로 던져 본다."""

    def test_write_evidence_is_blocked_and_file_unchanged(self) -> None:
        from common import ops_tasks

        real = Path(ops_tasks.EVIDENCE_DIR) / "audit_purge_last.json"
        before = real.read_bytes() if real.is_file() else None
        self.assertIsNone(
            ops_tasks._write_evidence("audit_purge_last",
                                      {"verdict": "TEST_MUST_NOT_LAND"}),
            "시험 중인데 증거를 썼다 — 그날 그대로다")
        after = real.read_bytes() if real.is_file() else None
        self.assertEqual(before, after, f"{real} 가 시험 중에 바뀌었다")


class GuardLivesInOnePlaceTest(unittest.TestCase):
    """두 벌을 두지 않는다 (D-369) — 어긋난 복사본 하나가 D-212 였다."""

    def test_no_inline_pytest_flag_checks_outside_the_guard(self) -> None:
        root = Path(__file__).resolve().parents[1]
        offenders = []
        for path in root.rglob("*.py"):
            rel = path.relative_to(root).as_posix()
            if rel == "common/evidence_guard.py" or rel.startswith("tests/"):
                continue
            try:
                body = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "PYTEST_CURRENT_TEST" in body:
                offenders.append(rel)
        self.assertEqual(
            offenders, [],
            "「시험 중인가」를 자기 자리에서 따로 묻는 곳이 있다 — 술어는 "
            "`common.evidence_guard` 한 자리에 둔다. 두 벌은 반드시 어긋나고, "
            f"어긋나면 한쪽이 조용히 아무것도 안 본다: {offenders}")


class SyntheticRunLeakTest(unittest.TestCase):
    """★ **출생 표본 2** — 판정기가 자기 증거를 덮은 그 한 줄 (P-87 4 · 턴 I).

    [실측 2026-09-06 · 턴 I · 차선 E 가 잡음]

        scripts/verify_retention_declared.py:371
            with override_settings(OPS_BACKUP_SCHEDULE_ENABLED=True, OPS_BACKUP_DIR=""):
                out = ops_tasks.ops_backup_beat()

    그 호출이 `docs/agent/evidence/D-373/backup_last.json` 을 이렇게 덮었다:

        {"verdict": "SKIPPED_UNDECLARED", "reason": "백업 목적지가 선언되지 않았다"}

    같은 순간 이 환경의 사실은 `OPS_BACKUP_DIR='/backup'` · `ENABLED=True` 였다 [실측].
    파일을 읽은 사람은 **환경이 미선언이라 백업을 건너뛰었다**고 읽는다. 아니다 —
    판정기가 잠깐 비워 놓고 물어본 것이다.

    ★ 그리고 이것은 `PYTEST_CURRENT_TEST` 가드를 **그냥 지나갔다.** 판정기는 시험이
      아니기 때문이다. 그래서 이 시험은 **깃발 둘을 지우고** 그날의 자리를 그대로
      만든다 — 재현되지 않는 가드는 가드가 아니다.
    """

    @contextlib.contextmanager
    def _no_pytest_flags(self):
        """그날의 자리 — 시험도 아니고 세션 깃발도 없다."""
        saved = {k: os.environ.pop(k, None)
                 for k in ("PYTEST_CURRENT_TEST", G.SESSION_ENV)}
        try:
            yield
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def _call_beat(self, evidence_dir: Path):
        """그날의 자리를 그대로 만든다 — 판정기는 **개발 DB** 를 물고 돈다.

        ★ `_db_name` 을 `database_guardianx` 로 세우는 것이 핵심이다.
          이 시험은 pytest 안에서 도니 시험 DB(`test_…`)를 물고 있고, 그러면
          **다른 가드**(시험 DB 술어)가 먼저 막아 버려 그날의 자리가 재현되지 않는다.
          재현이 안 되면 이 시험은 아무것도 지키지 않는다 — 그래서 판정기가 실제로
          있던 자리(개발 DB)를 그대로 세운다.
        """
        from django.test.utils import override_settings

        from common import ops_tasks

        with mock.patch.object(ops_tasks, "EVIDENCE_DIR", str(evidence_dir)),                 mock.patch.object(ops_tasks, "_db_name",
                                  lambda: "database_guardianx"):
            with override_settings(OPS_BACKUP_SCHEDULE_ENABLED=True,
                                   OPS_BACKUP_DIR=""):
                return ops_tasks.ops_backup_beat()

    def test_the_leak_reproduces_without_the_new_guard(self) -> None:
        """가드가 없으면 **실제로 샌다** — 이것을 못 보이면 고친 것이 아니다."""
        with tempfile.TemporaryDirectory() as tmp:
            evi = Path(tmp) / "docs" / "agent" / "evidence" / "D-373"
            target = evi / "backup_last.json"
            with self._no_pytest_flags():
                out = self._call_beat(evi)
            self.assertEqual(out.get("verdict"), "SKIPPED_UNDECLARED")
            self.assertTrue(
                target.is_file(),
                "그날의 자리를 만들었는데 안 샜다 — 재현이 안 되면 이 시험은 "
                "아무것도 지키지 않는다")
            body = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(body.get("verdict"), "SKIPPED_UNDECLARED")
            with G.allow_evidence_writes("이 시험이 만든 임시 파일을 치운다"):
                target.unlink()

    def test_synthetic_run_stops_it(self) -> None:
        """같은 호출을 `synthetic_run` 안에서 하면 **한 글자도 안 쓴다.**"""
        with tempfile.TemporaryDirectory() as tmp:
            evi = Path(tmp) / "docs" / "agent" / "evidence" / "D-373"
            target = evi / "backup_last.json"
            with self._no_pytest_flags():
                with G.synthetic_run("판정기가 OPS_BACKUP_DIR 을 비워 놓고 물어본다"):
                    out = self._call_beat(evi)
            self.assertEqual(out.get("verdict"), "SKIPPED_UNDECLARED",
                             "가드는 **판정을 바꾸지 않는다** — 안 쓸 뿐이다")
            self.assertFalse(target.exists(), "지어낸 상태인데 증거가 떨어졌다")

    def test_synthetic_beats_allow(self) -> None:
        """지어낸 상태 안에서는 **이름을 대도** 못 쓴다 —
        지어낸 수에 이름을 붙이면 그것이 가장 그럴듯한 거짓 증거다."""
        with G.synthetic_run("지어낸 상태"):
            with G.allow_evidence_writes("이름은 댔다"):
                self.assertIsNotNone(
                    G.blocked_reason("/docs/agent/evidence/D-373/backup_last.json"))

    def test_test_db_is_refused_even_outside_pytest(self) -> None:
        """★ **프로세스를 안 묻는다 — 수의 출처를 묻는다.**
        celery 워커든 관리 명령이든, 시험 DB 를 물고 있으면 증거를 못 쓴다."""
        with self._no_pytest_flags():
            self.assertIsNotNone(
                G.blocked_reason("/docs/agent/evidence/D-373/backup_last.json",
                                 db_name="test_gx_q"))
            self.assertIsNone(
                G.blocked_reason("/docs/agent/evidence/D-373/backup_last.json",
                                 db_name="database_guardianx"))

    def test_real_backup_evidence_is_untouched(self) -> None:
        """그날 덮인 그 파일 — 이 시험이 도는 동안 **한 바이트도 안 바뀐다.**"""
        from common import ops_tasks

        real = Path(ops_tasks.EVIDENCE_DIR) / "backup_last.json"
        before = real.read_bytes() if real.is_file() else None
        with G.synthetic_run("출생 표본 재현"):
            ops_tasks._write_evidence("backup_last", {"verdict": "TEST_MUST_NOT_LAND"})
        after = real.read_bytes() if real.is_file() else None
        self.assertEqual(before, after)


class JudgesThatCallOpsBeatsMustDeclareSyntheticTest(unittest.TestCase):
    """★ **다음에 또 다른 경로로 새지 않게.** 한 자리를 막는 것으로는 모자란다.

    `scripts/` 의 판정기가 `ops_tasks.*_beat()` 를 부르면서 설정을 갈아 끼우면
    그 호출은 **운영 증거를 덮는다.** 그런 파일은 `evidence_guard.synthetic_run` 을
    반드시 통과해야 한다 — 이 시험이 그 규칙을 지킨다.
    """

    def test_every_such_script_declares_synthetic_run(self) -> None:
        #: 컨테이너는 `/repo/scripts`, 호스트는 `<repo>/scripts` 다. 한 자리로 못 박으면
        #: 한쪽에서 조용히 건너뛰고, 건너뛴 시험은 아무것도 안 지킨다 (D-369 계열).
        here = Path(__file__).resolve()
        cands = [Path("/repo/scripts")]
        cands += [parent / "scripts" for parent in here.parents]
        root = None
        for cand in cands:
            if (cand / "verify_retention_declared.py").is_file():
                root = cand
                break
        if root is None:
            self.skipTest("scripts/verify_retention_declared.py 를 못 찾았다 — "
                          "이 자리에서는 못 잰다(회색이지 통과가 아니다)")
        offenders = []
        checked = 0
        for path in sorted(root.glob("*.py")):
            try:
                body = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "_beat()" not in body or "override_settings" not in body:
                continue
            checked += 1
            if "synthetic_run" not in body:
                offenders.append(path.name)
        self.assertGreater(checked, 0,
                           "검사 대상이 0건이다 — 0건 검사와 검사 못 함은 다르다 (D-301)")
        self.assertEqual(
            offenders, [],
            "설정을 갈아 끼운 채 운영 주기(`*_beat()`)를 부르면서 "
            "`evidence_guard.synthetic_run` 을 안 쓴 판정기가 있다 — "
            f"그 호출은 운영 증거를 덮는다: {offenders}")
