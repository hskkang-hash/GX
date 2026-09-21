# -*- coding: utf-8 -*-
"""LAW-08 증거 해시 체인 — **행 하나를 고치면 여기서 빨강이 난다**.

초록의 조건이 지시서에 못 박혀 있다: *"행 하나를 고치면 체인 검증이 exit 1"*.
그래서 이 파일의 중심은 「체인이 만들어진다」가 아니라 **「고친 것을 잡는다」**이다.
만들어지기만 하는 체인은 장식이고, 장식은 감사에서 아무 말도 하지 못한다.

잡아야 하는 세 가지 모양 — 셋이 서로 다른 사건이다
--------------------------------------------------
  ① **내용이 바뀌었다**  — 그 행의 `hash` 가 내용에서 다시 나오지 않는다
  ② **행이 사라졌다**    — 다음 행의 `prev_hash` 가 앞 행의 `hash` 와 어긋난다
  ③ **두 칸이 지워졌다** — 체인이 시작된 뒤인데 해시가 없다

  ★ ②·③ 을 안 재면 「값을 고치는 것」만 막고 **「지우는 것」은 열려 있다.** 감사 기록을
    지우는 쪽이 고치는 쪽보다 쉽고, 지운 자리는 원래 없었던 것과 모양이 같다 —
    이 저장소가 D-290 에서 배운 것과 같은 얼굴이다.

무엇을 시험하지 **않는가**
--------------------------
종이 앵커가 실제로 인쇄되는지는 여기서 못 잰다 — 그것은 보고서 렌더링이고 종이다.
여기서 재는 것은 **인쇄될 값이 하루의 마지막 해시와 같은가**까지다. 그 너머는
시험이 아니라 운영 절차이고, 시험이 그 척을 하면 안 된다.
"""
from __future__ import annotations

from datetime import date

from django.apps import apps
from django.test import SimpleTestCase, TestCase

from common import audit_writer, evidence_chain


class _Actor:
    """감사 한 줄에 쓸 **이름뿐인 행위자.** `audit_writer` 는 `pk` 와 `username` 만 본다."""

    def __init__(self, pk: int, username: str) -> None:
        self.pk = pk
        self.username = username


LOGGER = "guardianx.test.s_chain"


def _audit_rows():
    return apps.get_model("logger", "AuditLogs")._base_manager


class EvidenceChainPureTest(TestCase):
    """① 순수 계산 — Django 없이도 성립하는 부분. **과녁이 여기다** (D-277)."""

    def _entry(self, i: int, prev: str, record: dict) -> dict:
        return {"id": i, "record": record, "prev_hash": prev,
                "hash": evidence_chain.digest(prev_hash=prev, record=record)}

    def _chain(self, n: int = 3) -> list[dict]:
        out: list[dict] = []
        prev = evidence_chain.GENESIS
        for i in range(1, n + 1):
            e = self._entry(i, prev, {"id": i, "msg": f"줄 {i}", "note": ""})
            out.append(e)
            prev = e["hash"]
        return out

    def test_intact_chain_has_no_breaks(self):
        self.assertEqual((), evidence_chain.verify_sequence(self._chain()))

    def test_changed_content_is_caught(self):
        """★ 출생 표본 — **한 글자를 고친다.**"""
        chain = self._chain()
        chain[1]["record"]["msg"] = "줄 2 (고침)"
        breaks = evidence_chain.verify_sequence(chain)
        self.assertTrue(breaks, "행 내용을 고쳤는데 체인이 조용하다 — 체인이 아니다")
        self.assertEqual(evidence_chain.HASH_MISMATCH, breaks[0].kind)
        self.assertEqual(2, breaks[0].audit_id)

    def test_removed_row_is_caught(self):
        chain = self._chain()
        del chain[1]
        breaks = evidence_chain.verify_sequence(chain)
        self.assertTrue(breaks, "가운데 행을 지웠는데 체인이 조용하다")
        self.assertEqual(evidence_chain.PREV_MISMATCH, breaks[0].kind)

    def test_stripped_columns_are_caught(self):
        chain = self._chain()
        chain[1]["hash"] = ""
        chain[1]["prev_hash"] = ""
        kinds = {b.kind for b in evidence_chain.verify_sequence(chain)}
        self.assertIn(evidence_chain.MISSING, kinds)

    def test_rows_before_the_chain_are_not_counted_as_breaks(self):
        """LAW-08 이전의 행은 두 칸이 없다. 그것을 빨강으로 세면 **빨강이 상시가 된다**."""
        chain = [{"id": 0, "record": {"id": 0}, "prev_hash": "", "hash": ""}]
        chain += self._chain()
        self.assertEqual((), evidence_chain.verify_sequence(chain))

    def test_the_two_columns_are_not_hashed_by_themselves(self):
        """해시가 자기 자신을 덮으면 저장하는 순간 값이 바뀌고 검증이 늘 빨강이다."""
        payload = {"text": "회신", evidence_chain.PREV_KEY: "a",
                   evidence_chain.HASH_KEY: "b"}
        self.assertEqual({"text": "회신"}, evidence_chain.strip_chain(payload))

    def test_a_row_that_had_no_payload_stays_empty_after_stripping(self):
        """두 칸만 있던 행은 **원래 비어 있던 행**이다 — `{}` 로 두면 해시가 갈린다."""
        only = {evidence_chain.PREV_KEY: "a", evidence_chain.HASH_KEY: "b"}
        self.assertIsNone(evidence_chain.strip_chain(only))

    def test_order_of_keys_does_not_change_the_hash(self):
        a = {"id": 1, "msg": "x", "note": "y"}
        b = {"note": "y", "msg": "x", "id": 1}
        self.assertEqual(evidence_chain.digest(prev_hash="p", record=a),
                         evidence_chain.digest(prev_hash="p", record=b))

    def test_a_purged_head_is_not_called_tampering_but_is_reported(self):
        """★ 보존기간이 앞에서부터 지운다. 그것을 「변조」로 세면 **판정이 영구 빨강**이다.

        앞머리는 초록으로 두되 **잘렸다는 사실을 값으로 낸다** — 그 자리의 증거는
        코드가 아니라 그날 인쇄된 앵커다. 「초록」과 「종이로만 확인 가능」을 같은
        말로 적으면 다음 사람이 종이를 안 찾는다.
        """
        chain = self._chain(4)[2:]                 # 앞 두 줄이 보존기간에 사라졌다
        self.assertEqual((), evidence_chain.verify_sequence(chain))
        self.assertNotEqual(evidence_chain.GENESIS, chain[0]["prev_hash"])

    def test_middle_deletion_is_still_caught_after_that_relaxation(self):
        """앞머리를 봐준 것이 **가운데를 열어 주면** 안 된다 (D-326: 좁힐 때마다 반대편이 열린다)."""
        chain = self._chain(5)
        del chain[2]
        kinds = {b.kind for b in evidence_chain.verify_sequence(chain)}
        self.assertIn(evidence_chain.PREV_MISMATCH, kinds)

    def test_previous_hash_actually_enters_the_digest(self):
        """앞의 값이 안 들어가면 그것은 체인이 아니라 **행별 해시**다 — 순서를 못 지킨다."""
        rec = {"id": 1, "msg": "x"}
        self.assertNotEqual(evidence_chain.digest(prev_hash="a", record=rec),
                            evidence_chain.digest(prev_hash="b", record=rec))


class EvidenceChainOnAuditTableTest(TestCase):
    """② 진짜 감사표 위에서. **`audit_writer.write` 로 남긴 행이 스스로 이어진다.**"""

    def _write(self, n: int = 3) -> list[int]:
        ids = []
        for i in range(n):
            entry = audit_writer.write(
                logger_name=LOGGER, tag="[S-TEST]", actor=_Actor(1, "s_actor"),
                action=f"s_act_{i}", outcome=audit_writer.ALLOWED,
                reason=f"체인 시험 {i}", after={"seq": i})
            ids.append(entry.audit_id)
        return ids

    def test_every_written_row_gets_two_columns(self):
        ids = self._write()
        for pk in ids:
            payload = _audit_rows().filter(pk=pk).values_list("data_after", flat=True)[0]
            self.assertIn(evidence_chain.HASH_KEY, payload,
                          f"#{pk} 에 해시 칸이 없다 — 체인 밖에서 태어난 감사 행이다")
            self.assertIn(evidence_chain.PREV_KEY, payload)
            self.assertIn("seq", payload, "두 칸이 부르는 쪽의 payload 를 덮었다")

    def test_payload_written_by_the_caller_survives(self):
        """두 칸이 **부르는 쪽의 값을 덮지 않는다.** 덮으면 현장 회신 본문이 사라진다."""
        entry = audit_writer.write(
            logger_name=LOGGER, tag="[S-TEST]", actor=_Actor(1, "s_actor"),
            action="s_payload", outcome=audit_writer.ALLOWED, reason="본문 보존",
            after={"event_id": 7, "text": "현장 도착"})
        payload = _audit_rows().filter(pk=entry.audit_id).values_list(
            "data_after", flat=True)[0]
        self.assertEqual(7, payload["event_id"])
        self.assertEqual("현장 도착", payload["text"])

    def test_write_returns_the_position_in_the_chain(self):
        first, second = self._write(2)
        e2 = _audit_rows().filter(pk=second).values_list("data_after", flat=True)[0]
        e1 = _audit_rows().filter(pk=first).values_list("data_after", flat=True)[0]
        self.assertEqual(e1[evidence_chain.HASH_KEY], e2[evidence_chain.PREV_KEY],
                         "두 번째 행이 첫 행을 안 가리킨다 — 줄이 아니라 점 두 개다")

    def test_intact_chain_verifies(self):
        self._write()
        report = evidence_chain.verify_chain()
        self.assertTrue(report.ok, f"손대지 않았는데 깨졌다: {[str(b) for b in report.breaks]}")
        self.assertGreaterEqual(report.chained, 3)

    def test_tampering_one_row_breaks_verification(self):
        """★ **초록의 조건 그 자체** — 지시서가 못 박은 시연이다.

        한 행의 `msg` 한 글자를 바꾼다. 값을 바꾼 자가 두 칸은 안 만졌으므로,
        저장된 해시는 그대로다. 다시 계산하면 다른 값이 나온다 — 그것이 잡히는 자리다.
        """
        ids = self._write()
        _audit_rows().filter(pk=ids[1]).update(msg="[S-TEST] 조용히 고쳤다")

        report = evidence_chain.verify_chain()
        self.assertFalse(report.ok, "행을 고쳤는데 체인 검증이 초록이다 — 체인이 아니다")
        self.assertIn(ids[1], [b.audit_id for b in report.breaks])
        self.assertIn(evidence_chain.HASH_MISMATCH, {b.kind for b in report.breaks})

    def test_deleting_a_row_breaks_verification(self):
        ids = self._write()
        _audit_rows().filter(pk=ids[1]).delete()

        report = evidence_chain.verify_chain()
        self.assertFalse(report.ok, "가운데 감사 행을 지웠는데 체인이 조용하다")
        self.assertIn(evidence_chain.PREV_MISMATCH, {b.kind for b in report.breaks})

    def test_stripping_the_two_columns_breaks_verification(self):
        """두 칸만 지우고 내용은 그대로 두는 것 — **가장 그럴듯한 은폐**다."""
        ids = self._write()
        _audit_rows().filter(pk=ids[1]).update(data_after={"seq": 1})

        report = evidence_chain.verify_chain()
        self.assertFalse(report.ok, "두 칸을 지웠는데 체인이 조용하다")
        self.assertIn(evidence_chain.MISSING, {b.kind for b in report.breaks})

    def test_rewriting_the_whole_tail_is_still_caught_by_the_anchor(self):
        """★ 체인만으로 못 잡는 자리를 **적어 둔다.**

        고친 뒤 그 행부터 끝까지 해시를 다시 계산하면 체인은 초록이 된다. 여기서
        빨강을 만드는 것은 코드가 아니라 **어제 종이에 찍힌 40자**다. 이 시험은
        그 사실을 실행 가능한 모양으로 남긴다 — 앵커가 바뀌었음을 보인다.
        """
        ids = self._write()
        before = evidence_chain.daily_anchor(date.today())

        _audit_rows().filter(pk=ids[1]).update(msg="[S-TEST] 조용히 고쳤다")
        for pk in ids[1:]:                                   # 꼬리를 다시 계산한다
            evidence_chain.append_evidence_hash(audit_id=pk)

        self.assertTrue(evidence_chain.verify_chain().ok,
                        "꼬리를 다시 계산했으면 체인 자체는 초록이다 — 그것이 요점이다")
        after = evidence_chain.daily_anchor(date.today())
        self.assertNotEqual(before, after,
                            "표를 다시 썼는데 그날의 앵커가 그대로다 — 종이가 못 잡는다")

    def test_purging_the_oldest_rows_keeps_the_chain_green(self):
        """DB 위에서도 같다 — 보존기간 집행이 돌아도 판정은 초록이고, 잘린 사실을 낸다."""
        ids = self._write(4)
        _audit_rows().filter(pk__in=ids[:2]).delete()
        report = evidence_chain.verify_chain()
        self.assertTrue(report.ok,
                        f"보존기간 집행 모양인데 빨강이다: {[str(b) for b in report.breaks]}")
        self.assertFalse(report.starts_at_genesis,
                         "앞머리가 잘렸는데 보고서가 GENESIS 라고 말한다")

    def test_daily_anchor_is_the_last_hash_of_that_day(self):
        ids = self._write()
        last = _audit_rows().filter(pk=ids[-1]).values_list("data_after", flat=True)[0]
        anchor = evidence_chain.daily_anchor(date.today())
        self.assertEqual(last[evidence_chain.HASH_KEY], anchor)
        self.assertIn(anchor, evidence_chain.anchor_line(date.today(), anchor))

    def test_anchor_line_says_so_when_there_is_nothing(self):
        """행이 없는 날에 **빈 줄을 인쇄하지 않는다** — 빈 줄은 「검사 안 함」과 같은 모양이다."""
        line = evidence_chain.anchor_line(date(2000, 1, 1), "")
        self.assertIn("2000-01-01", line)
        self.assertIn("없음", line)


class OldCodeRowIsStillTheTailTest(TestCase):
    """★ 턴 X — **자리표 없이 태어난 행도 줄의 끝이다.**

    [실측 2026-09-20 · 운영 DB · 이 차선이 직접 밟았다]
    잠금·자리표가 선 뒤에도 **재기동 안 한 컨테이너 하나**가 옛 코드로 감사를 썼다::

        #275841  2026-09-20 01:00:04Z  guardianx.k2.heartbeat  자리표 없음  hash=c9d02a45…

    그 행은 두 칸이 제대로 있는 **정상 행**이다. 그런데 `_hashed_head()` 가 자리표 있는
    행만 보고 줄 끝을 골랐기 때문에, 그 뒤에 온 쓰기가 **그 행을 못 보고** 한 칸 앞
    (#275818 · `2d4e4980…`)에 붙었다 — 줄이 갈라졌고, 게이트가 **새 끊김 1건**을 냈다.

    ⚠ 같은 자리를 `_order_key` 는 **제대로** 읽는다(자리표가 없으면 번호가 자리다).
      즉 **줄의 순서를 정하는 규칙이 두 벌**이었고, 두 벌의 어긋남이 이 갈라짐이다 —
      이 저장소가 D-212 에서 배운 바로 그 병이다.
    """

    def test_a_row_without_a_place_marker_is_seen_as_the_tail(self):
        first = audit_writer.write(
            logger_name=LOGGER, tag="[S-TEST]", actor=_Actor(1, "s_actor"),
            action="before_old_code", outcome=audit_writer.ALLOWED, reason="앞 행")

        # 옛 코드가 쓴 행을 **그 모양 그대로** 만든다: 두 칸은 있고 자리표만 없다.
        old = audit_writer.write(
            logger_name=LOGGER, tag="[S-TEST]", actor=_Actor(1, "s_actor"),
            action="old_code_row", outcome=audit_writer.ALLOWED, reason="옛 코드 행")
        row = _audit_rows().get(pk=old.audit_id)
        payload = dict(row.data_after or {})
        payload.pop(evidence_chain.SEQ_KEY, None)
        _audit_rows().filter(pk=old.audit_id).update(data_after=payload)

        head_id, head_hash, head_seq = evidence_chain._hashed_head()
        self.assertEqual(
            old.audit_id, head_id,
            f"자리표 없는 행 #{old.audit_id} 을 줄 끝으로 안 봤다 — "
            f"#{head_id} 를 끝이라 했다(#{first.audit_id} 가 그 앞 행이다). "
            f"다음 쓰기가 그 앞에 붙어 줄이 갈라진다")
        self.assertEqual(old.row_hash, head_hash)
        self.assertEqual(old.audit_id, head_seq, "자리표가 없으면 **번호가 곧 자리**다")

    def test_the_next_write_lands_behind_that_row(self):
        """그 다음 한 줄이 **정말로** 그 뒤에 붙는가 — 끊김 0 으로 확인한다."""
        audit_writer.write(logger_name=LOGGER, tag="[S-TEST]",
                           actor=_Actor(1, "s_actor"), action="a",
                           outcome=audit_writer.ALLOWED, reason="가")
        old = audit_writer.write(logger_name=LOGGER, tag="[S-TEST]",
                                 actor=_Actor(1, "s_actor"), action="b",
                                 outcome=audit_writer.ALLOWED, reason="나")
        row = _audit_rows().get(pk=old.audit_id)
        payload = dict(row.data_after or {})
        payload.pop(evidence_chain.SEQ_KEY, None)
        _audit_rows().filter(pk=old.audit_id).update(data_after=payload)

        audit_writer.write(logger_name=LOGGER, tag="[S-TEST]",
                           actor=_Actor(1, "s_actor"), action="c",
                           outcome=audit_writer.ALLOWED, reason="다")
        breaks = evidence_chain.verify_sequence(evidence_chain.chain_entries())
        self.assertEqual((), breaks,
                         "옛 코드 행 하나가 줄을 갈랐다: "
                         + " · ".join(str(b) for b in breaks[:5]))


class DanglingEventRefTest(SimpleTestCase):
    """P-184/P-208 — **사라진 사건을 가리키는 체인 행**의 등재를 지킨다 (턴 Y · 차선 S).

    ★ 여기서 재는 것은 **등재의 모양**이지 그 수가 아니다. 수는 사건을 지울 때마다 늘고,
      그 늘어남은 결함이 아니라 대표 결정의 그림자다 — 수를 시험에 박으면 그 시험이
      「지우지 마라」는 규칙이 되어 버리고, 그것은 이 장부가 하려는 말이 아니다.
    """

    def test_it_reads_the_event_id_from_either_side(self) -> None:
        self.assertEqual(
            evidence_chain.event_ref_of({"data_after": {"event_id": 7}}), 7)
        self.assertEqual(
            evidence_chain.event_ref_of({"data_before": {"event_id": 9}}), 9)

    def test_after_wins_when_both_sides_carry_one(self) -> None:
        """상태 전이 행은 두 칸을 다 든다. **뒤의 값**이 그 행이 남긴 사실이다."""
        self.assertEqual(evidence_chain.event_ref_of(
            {"data_before": {"event_id": 1}, "data_after": {"event_id": 2}}), 2)

    def test_a_row_without_one_is_none_not_zero(self) -> None:
        """★ 0 은 사건 번호다. 「없다」를 0 으로 접으면 0번 사건을 가리킨 것이 된다."""
        self.assertIsNone(evidence_chain.event_ref_of({"data_after": {}}))
        self.assertIsNone(evidence_chain.event_ref_of({}))
        self.assertIsNone(evidence_chain.event_ref_of({"data_after": None}))
        self.assertIsNone(
            evidence_chain.event_ref_of({"data_after": {"event_id": "없음"}}))

    def test_every_recorded_note_carries_its_method_and_reason(self) -> None:
        """★ **수만 적힌 등재는 등재가 아니다.**

        턴 X 의 줄이 그 얼굴이다 — 29·43 이라는 수는 남았는데 **세는 식이 안 남아**
        다음 사람이 재현할 수 없다. 그 줄은 그 사실을 스스로 적고 있고, 이 시험은
        앞으로 들어올 줄이 같은 구멍을 갖지 않게 한다.
        """
        self.assertTrue(evidence_chain.RECORDED_DANGLING)
        for note in evidence_chain.RECORDED_DANGLING:
            with self.subTest(when=note.when):
                self.assertTrue(note.when.strip())
                self.assertTrue(note.method.strip())
                self.assertTrue(note.why.strip())
                self.assertGreaterEqual(note.table_rows, note.chain_rows)
