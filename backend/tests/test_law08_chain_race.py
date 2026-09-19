# -*- coding: utf-8 -*-
"""LAW-08 P-191 — 감사 체인 **경합**. 같은 순간 두 손이 붙으면 줄이 갈라진다.

무엇을 재는가 — 「만들어진다」가 아니라 「같은 순간에도 하나의 줄인가」
--------------------------------------------------------------------
`tests/test_s_evidence_chain.py` 는 체인을 **한 손으로** 잇는다. 그래서 초록이어도
두 손이 동시에 붙는 순간에 대해서는 아무 말도 하지 않는다. 턴 V 의 실측이 그 침묵의
값을 말해 주었다 — 운영 DB 에서 `#257053` 이 **측정 중에 태어났고**, 이어서 아래 모양이
반복해서 나왔다 [실측 2026-09-19 · 운영 DB]::

    260977 06:58:32.856  prev=2be3b83e5efd  hash=92bb183271de
    260978 06:58:32.864  prev=2be3b83e5efd  hash=5bac3e95d978   ← 같은 앞 해시
    260979 06:58:32.867  prev=2be3b83e5efd  hash=50a0b2d099f9   ← 또 같은 앞 해시

  **세 행이 같은 「앞 해시」를 읽었다.** 12 밀리초 안에 태어난 세 행이다. 줄 하나에
  가지 셋이 달린 것이고, 그 순간 「지워진 행」과 「갈라진 행」이 같은 얼굴이 된다.

이 파일이 겨누는 과녁은 그 모양 하나다:
  ① 같은 순간에 붙은 행들 사이에 **어긋남이 0** 인가
  ② 어떤 두 행도 **같은 `prev_hash` 를 쓰지 않는가** (위 실측의 얼굴 그대로)

★ 왜 `TestCase` 가 아니라 `TransactionTestCase` 인가 — **여기를 틀리면 회색이 초록이 된다**
---------------------------------------------------------------------------------------
`TestCase` 는 시험 하나를 트랜잭션으로 감싸고 끝에 되돌린다. 그러면 **다른 스레드가
그 행들을 아예 못 본다** — 경합이 일어날 수 없고, 시험은 언제나 초록이다.
초록의 이유가 「고쳐서」가 아니라 「못 봐서」인 시험은 증거가 아니다.

★ sqlite 로는 이 시험이 뜻이 없다 — sqlite 는 쓰기를 통째로 직렬화한다.
  그래서 잠금이 없어도 초록이 난다. **postgres 로 돌려야 한다**(이 저장소의 시험 DB 가
  그렇다: `config/settings.py` DATABASES.default = postgresql).
"""
from __future__ import annotations

import threading

from django.apps import apps
from django.db import connection, connections, transaction
from django.test import TransactionTestCase

from common import audit_writer, evidence_chain

LOGGER = "guardianx.test.law08_race"

#: 같은 순간에 붙는 손의 수. 실측에서 한 번에 셋이 붙었으므로 그보다 넉넉히 둔다.
HANDS = 6
#: 겹치는 순간을 몇 번 만드는가. 경합은 확률이라 **한 번으로는 재현을 보증 못 한다** —
#: 「낮은 수도 재현돼야 수다」. 그래서 같은 순간을 여러 번 만든다.
ROUNDS = 6


class _Actor:
    """`audit_writer` 가 보는 것은 `pk` 와 `username` 뿐이다."""

    def __init__(self, pk: int, username: str) -> None:
        self.pk = pk
        self.username = username


def _audit_rows():
    return apps.get_model("logger", "AuditLogs")._base_manager


class ChainRaceTest(TransactionTestCase):
    """P-191 — **같은 순간 여러 손**이 붙어도 줄은 하나여야 한다."""

    def _hand(self, barrier: threading.Barrier, round_no: int, hand_no: int,
              errors: list[str]) -> None:
        """손 하나. 관문에서 **같이 출발한다** — 출발을 안 맞추면 겹치지 않는다."""
        try:
            barrier.wait(timeout=30)
            audit_writer.write(
                logger_name=LOGGER, tag="[P-191]", actor=_Actor(1, "race_actor"),
                action=f"race_{round_no}_{hand_no}", outcome=audit_writer.ALLOWED,
                reason=f"경합 {round_no}-{hand_no}", after={"round": round_no,
                                                          "hand": hand_no})
        except Exception as exc:                      # noqa: BLE001 — 스레드의 예외는
            errors.append(f"{round_no}-{hand_no}: {type(exc).__name__}: {exc}")
        finally:
            # 스레드마다 제 연결을 연다. 안 닫으면 postgres 연결이 쌓인 채 남는다.
            connections.close_all()

    def _race_once(self, round_no: int, errors: list[str]) -> None:
        barrier = threading.Barrier(HANDS)
        threads = [threading.Thread(target=self._hand,
                                    args=(barrier, round_no, h, errors))
                   for h in range(HANDS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=120)
        for t in threads:
            self.assertFalse(t.is_alive(), "손 하나가 안 끝났다 — 잠금이 물렸을 수 있다")

    def _entries(self) -> list[dict]:
        """★ `verify_chain()` 이 아니라 **날 판정**을 쓴다.

        `verify_chain()` 은 「기록된 끊김」(`RECORDED_BREAKS`)을 빼고 돌려준다. 그 장부를
        통과시키면 이 시험은 **장부에 적기만 해도 초록**이 될 수 있다 — 그것은 경합을
        잡은 증거가 아니다. 그래서 여기서는 장부를 안 거치는 자리를 직접 부른다.
        """
        return evidence_chain.chain_entries()

    def test_hands_at_the_same_moment_do_not_split_the_chain(self):
        """★ 이 파일의 중심. 같은 순간 여러 손 → **어긋남 0**."""
        errors: list[str] = []
        for r in range(ROUNDS):
            self._race_once(r, errors)
        self.assertEqual([], errors, f"감사 쓰기 자체가 실패했다: {errors}")

        entries = self._entries()
        self.assertEqual(HANDS * ROUNDS, len(entries),
                         "쓴 행 수와 체인에 든 행 수가 다르다")
        breaks = evidence_chain.verify_sequence(entries)
        self.assertEqual((), breaks,
                         "같은 순간에 붙은 행들이 줄을 갈랐다 — 경합이다: "
                         + " · ".join(str(b) for b in breaks[:8]))

    def test_no_two_rows_share_the_same_previous_hash(self):
        """★ 실측의 얼굴 그대로 — **두 행이 같은 앞 해시를 읽으면** 그것이 갈라짐이다.

        어긋남 0 만 보면 놓칠 수 있다: 앞머리가 잘린 구간 등에서는 판정이 느슨해진다.
        「같은 앞 해시가 둘」은 느슨해질 자리가 없는 술어라 따로 둔다.
        """
        errors: list[str] = []
        for r in range(ROUNDS):
            self._race_once(r, errors)
        self.assertEqual([], errors, f"감사 쓰기 자체가 실패했다: {errors}")

        seen: dict[str, list[int]] = {}
        for e in self._entries():
            seen.setdefault(e["prev_hash"], []).append(e["id"])
        shared = {p: ids for p, ids in seen.items() if len(ids) > 1}
        self.assertEqual({}, shared,
                         "여러 행이 **같은 앞 해시**를 읽었다 — 줄 하나에 가지가 여럿이다: "
                         + " · ".join(f"{p[:12]}…→{ids}" for p, ids in
                                      list(shared.items())[:5]))


class ChainLockContractTest(TransactionTestCase):
    """잠금이 **정말 잠그고 있는가**. 「조용히 아무것도 안 잠그는」 모양을 겨눈다."""

    def test_the_lock_refuses_to_run_outside_a_transaction(self):
        """★ 트랜잭션 밖의 잠금은 **거는 순간 풀린다** — 그것은 잠금이 아니라 장식이다.

        `pg_advisory_xact_lock` 도 `SELECT … FOR UPDATE` 도 autocommit 에서는 그 문장이
        끝나는 순간 끝난다. 그래서 이 자리는 조용히 지나가면 안 되고 **서야** 한다.
        """
        self.assertFalse(connection.in_atomic_block,
                         "이 시험은 트랜잭션 밖에서 불려야 뜻이 있다")
        with self.assertRaises(RuntimeError):
            evidence_chain.lock_chain()

    def test_the_lock_is_taken_inside_a_transaction(self):
        """트랜잭션 안에서는 **선다** — 두 번 걸어도 (같은 트랜잭션이면) 통과한다."""
        with transaction.atomic():
            evidence_chain.lock_chain()
            evidence_chain.lock_chain()

    def test_append_runs_inside_a_transaction(self):
        """`append_evidence_hash` 가 스스로 트랜잭션을 연다 — 밖에서 불려도 잠금이 산다."""
        self.assertFalse(connection.in_atomic_block)
        entry = audit_writer.write(
            logger_name=LOGGER, tag="[P-191]", actor=_Actor(1, "race_actor"),
            action="lock_smoke", outcome=audit_writer.ALLOWED, reason="잠금 연기시험")
        payload = _audit_rows().filter(pk=entry.audit_id).values_list(
            "data_after", flat=True)[0]
        self.assertIn(evidence_chain.HASH_KEY, payload)

    def test_the_lock_key_is_a_single_chain(self):
        """체인이 하나이므로 **열쇠도 하나**다 — 가르면 두 손이 같은 줄에 동시에 붙는다."""
        self.assertIsInstance(evidence_chain.CHAIN_LOCK_KEY, int)


class RecordedBreakTest(TransactionTestCase):
    """「끊김 기록」이 **가림막이 되지 않는가**. 장부는 이 시험 없이는 위험한 물건이다."""

    def _break(self, **kw) -> evidence_chain.Break:
        base = dict(audit_id=1, kind=evidence_chain.PREV_MISMATCH,
                    detail="", got="a" * 64, want="b" * 64)
        base.update(kw)
        return evidence_chain.Break(**base)

    def test_a_recorded_break_moves_out_of_breaks_but_is_still_counted(self):
        rec = evidence_chain.RecordedBreak(1, evidence_chain.PREV_MISMATCH,
                                           "a" * 64, "b" * 64, "2026-09-19", "시험")
        one = self._break()
        self.assertEqual(one.key, rec.key)

    def test_the_same_row_with_different_values_is_a_new_break(self):
        """★ 가장 중요한 줄 — **같은 자리에 새로 생긴 끊김은 기록 뒤에 못 숨는다.**

        기록의 열쇠가 id 하나였다면 그 행에서 무슨 일이 나도 영원히 조용해진다.
        64자 두 개가 열쇠에 들어 있는 이유가 이것이다.
        """
        known = evidence_chain.recorded_keys()
        for rec in evidence_chain.RECORDED_BREAKS:
            same_id_other_value = self._break(audit_id=rec.audit_id, kind=rec.kind,
                                              got=rec.got, want="c" * 64)
            self.assertNotIn(same_id_other_value.key, known,
                             f"#{rec.audit_id} 에 새로 생긴 끊김이 옛 기록 뒤에 숨는다")
            other_kind = self._break(audit_id=rec.audit_id,
                                     kind=evidence_chain.HASH_MISMATCH,
                                     got=rec.got, want=rec.want)
            self.assertNotIn(other_kind.key, known,
                             f"#{rec.audit_id} 의 **다른 종류**의 끊김이 기록 뒤에 숨는다")

    def test_split_keeps_every_break_somewhere(self):
        """가른 뒤에도 **사라지는 끊김이 없다** — 합이 맞아야 「적었다」가 「지웠다」가 아니다."""
        made = [self._break(audit_id=i) for i in range(1, 4)]
        fresh, kept = evidence_chain.split_recorded(made)
        self.assertEqual(len(made), len(fresh) + len(kept))

    def test_every_recorded_line_says_when_and_why(self):
        """사유 없는 기록은 **면제**다. 등재는 사유를 든다 (D-261 c)."""
        for rec in evidence_chain.RECORDED_BREAKS:
            self.assertTrue(rec.when, f"#{rec.audit_id} 에 적은 날이 없다")
            self.assertTrue(rec.why, f"#{rec.audit_id} 에 사유가 없다")
            self.assertEqual(64, len(rec.got) or 64,
                             f"#{rec.audit_id} 의 값이 64자가 아니다 — 짧은 열쇠는 위험하다")
            self.assertEqual(64, len(rec.want),
                             f"#{rec.audit_id} 의 값이 64자가 아니다")
