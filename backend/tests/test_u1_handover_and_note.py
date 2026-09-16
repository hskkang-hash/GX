# -*- coding: utf-8 -*-
"""WO-01 §5 · 차선 U1 · 턴 R — **UX-34 인계 자동 초안** · **사건 메모**.

이 파일이 묻는 것
------------------
  ① 초안 본문이 **실제 그 시간대 사건에서 나왔는가** — 미처리 사건 id 가 본문에
     찍히는가(닫는 조건: RESUME_NEXT 턴 R · U1 「사건 id 가 본문에 반영」)
  ② `GET /handover/draft` 는 **저장하지 않는다** — 미리보기는 행을 안 만든다
  ③ `POST /handover/draft` 는 `DsmHandover` 한 행을 남기고, `latest()` 가 그것을 읽는다
  ④ 남의 테넌트 인계 메모는 안 보인다(격리)
  ⑤ 사건 메모 — 남기고 **다시 읽는다**(왕복). 처음 구현에서 `audit_writer.write()` 에
     `api_name` 을 채워 넘겨 저장 칸이 `event_note:{id}` 대신 고정 문자열이 되고,
     그래서 방금 쓴 메모를 스스로 못 찾는 조용한 버그가 있었다 — 이 시험이 그것을 잡는다.
  ⑥ 남의 테넌트 사건에는 메모를 남길 수 없다(404 · IDOR) — 존재 여부도 새지 않는다.

★ **재조회로 잰다** — 함수가 돌려준 dict 를 믿지 않고 별도 조회(`latest`·`list_notes`)로
  다시 읽는다(QA-05 · `test_review_and_acknowledge.py` 와 같은 규약).
"""
from __future__ import annotations

from django.http import Http404

from tests.test_dsm_app import DsmFixture


class HandoverDraftTest(DsmFixture):
    def test_preview_reflects_the_real_unresolved_event_id(self) -> None:
        """★ 닫는 조건 그 자체 — 미처리 사건 id 가 본문에 찍힌다."""
        from apps.dsm import handover_service

        eid = self._event(self.stream_a)  # response_state 기본값 = occurred(미처리)

        draft = handover_service.preview(scope=self.scope_a, hours=24)

        self.assertGreaterEqual(
            len(draft["body"].splitlines()), 4,
            "자동 초안 본문이 4줄이 안 됩니다.")
        self.assertIn(eid, draft["unresolved_event_ids"])
        self.assertIn(f"#{eid}", draft["body"],
                      "본문에 사건 id 가 안 찍혔습니다 — 수만 있고 근거가 없습니다.")
        self.assertEqual(1, draft["unresolved_count"])

    def test_preview_does_not_write_a_row(self) -> None:
        """GET — **저장하지 않는다.**"""
        from django.apps import apps

        from apps.dsm import handover_service

        self._event(self.stream_a)
        DsmHandover = apps.get_model("stream_monitors", "DsmHandover")
        before = DsmHandover.objects.filter(group=self.group_a).count()

        handover_service.preview(scope=self.scope_a, hours=24)

        self.assertEqual(
            before, DsmHandover.objects.filter(group=self.group_a).count(),
            "미리보기(GET)가 행을 만들었습니다 — 저장하지 않아야 합니다.")

    def test_save_persists_a_row_and_latest_reads_it_back(self) -> None:
        """POST 저장 → `latest()` 재조회. **재조회로 잰다** — 반환값을 믿지 않는다."""
        from apps.dsm import handover_service

        eid = self._event(self.stream_a)

        saved = handover_service.save(scope=self.scope_a, hours=24, note="특이사항 없음")
        self.assertIsNotNone(saved["id"])

        fresh = handover_service.latest(scope=self.scope_a)
        self.assertTrue(fresh["exists"])
        self.assertEqual(saved["id"], fresh["id"])
        self.assertEqual("특이사항 없음", fresh["note"])
        self.assertIn(eid, fresh["unresolved_event_ids"])
        self.assertGreaterEqual(len(fresh["body"].splitlines()), 4)

    def test_another_tenants_draft_is_not_visible(self) -> None:
        """★ 격리 — B 테넌트가 저장한 인계 메모는 A 테넌트의 `latest()` 에 안 보인다."""
        from apps.dsm import handover_service

        self._event(self.stream_b)
        handover_service.save(scope=self.scope_b, hours=24)

        seen_by_a = handover_service.latest(scope=self.scope_a)
        self.assertFalse(
            seen_by_a["exists"],
            "A 테넌트가 B 테넌트의 인계 메모를 봤습니다 — 격리 실패입니다.")

    def test_hours_out_of_contract_is_rejected(self) -> None:
        from apps.dsm import handover_service

        with self.assertRaises(ValueError):
            handover_service.preview(scope=self.scope_a, hours=0)
        with self.assertRaises(ValueError):
            handover_service.preview(scope=self.scope_a, hours=24 * 32)


class EventNoteTest(DsmFixture):
    def test_a_note_left_can_be_read_back(self) -> None:
        """★ 왕복 — 남기고 다시 읽는다. 처음 구현의 `api_name` 버그를 이 한 줄이 잡는다."""
        from apps.dsm import event_note_service

        eid = self._event(self.stream_a)

        added = event_note_service.add_note(
            scope=self.scope_a, event_id=eid, text="야간 근무 특이사항 없음")
        self.assertIsNotNone(added["note_id"])

        notes = event_note_service.list_notes(scope=self.scope_a, event_id=eid)
        self.assertEqual(
            1, len(notes),
            "방금 남긴 메모를 다시 읽지 못했습니다 — 저장 칸과 조회 칸이 어긋났습니다.")
        self.assertEqual("야간 근무 특이사항 없음", notes[0]["text"])

    def test_notes_do_not_leak_across_events(self) -> None:
        from apps.dsm import event_note_service

        e1 = self._event(self.stream_a)
        e2 = self._event(self.stream_a)
        event_note_service.add_note(scope=self.scope_a, event_id=e1, text="사건 1의 메모")

        notes_e2 = event_note_service.list_notes(scope=self.scope_a, event_id=e2)
        self.assertEqual(
            0, len(notes_e2),
            "다른 사건의 메모가 섞여 보입니다 — 사건별 이름 가르기가 깨졌습니다.")

    def test_another_tenants_event_is_404_not_leaked(self) -> None:
        """남의 사건에는 메모를 남길 수도, 읽을 수도 없다 — **404**(존재 여부도 누출이다)."""
        from apps.dsm import event_note_service

        eid = self._event(self.stream_a)

        with self.assertRaises(Http404):
            event_note_service.add_note(scope=self.scope_b, event_id=eid, text="남의 사건")
        with self.assertRaises(Http404):
            event_note_service.list_notes(scope=self.scope_b, event_id=eid)

    def test_empty_note_is_rejected(self) -> None:
        from apps.dsm import event_note_service

        eid = self._event(self.stream_a)
        with self.assertRaises(ValueError):
            event_note_service.add_note(scope=self.scope_a, event_id=eid, text="   ")
