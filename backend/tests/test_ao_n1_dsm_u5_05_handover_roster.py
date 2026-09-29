# -*- coding: utf-8 -*-
"""DSM-U5-05 「인계 메모 근무자 자동」 연결 (턴 AO · P-407 · 차선 N1).

턴 AN 이 세운 `shift_roster_service.current_workers()`는 그 날짜의 조별
근무자를 사람 손 없이 구조화해 냈지만, `handover_service.py`(다른 차선 소유)에
잇는 한 줄이 없었다(`docs/agent/evidence/SPEC/DSM-U5-05.json` 옛 title_parts
「인계 메모 근무자 자동」 행 — 「자동 조회 함수는 섰으나 … 잇는 한 줄이 아직
없다」). 이 턴이 그 한 줄을 이었다 — `build_draft()` 가 근무표를 다시 읽어
본문 5번째 줄(`근무 편성 …`)과 구조 응답 칸(`on_duty`)에 낸다. **새 표 0**
(`DsmHandover` 에 칸을 더하지 않는다 — 본문 텍스트에 실린다).

★ 이 시험이 닫지 않는 것을 정직하게 남긴다 — 관제일지(DSM-U1-04) 자체가 이
  저장소에 없다. 그래서 「일지 근무자 자동」·완결조건 「일지 근무자 = 편성표」는
  여전히 열린 행이다(이 절은 이 턴에도 반쪽으로 남는다 — 조율자에게 보고).
"""
from __future__ import annotations

from django.utils import timezone

from tests.test_dsm_app import DsmFixture


def _today() -> str:
    return timezone.localtime(timezone.now()).date().isoformat()


class HandoverRosterConnectionTest(DsmFixture):
    def test_preview_includes_on_duty_roster_from_shift_import(self) -> None:
        """근무표를 올리면 인계 초안 본문·구조 응답에 근무자가 그대로 실린다."""
        from apps.dsm import handover_service, shift_roster_service

        csv_text = ("date,team,shift,members\n"
                   f"{_today()},1조,주간,홍길동;김철수\n")
        shift_roster_service.import_csv(scope=self.scope_a, csv_text=csv_text)

        draft = handover_service.preview(scope=self.scope_a, hours=24)

        self.assertIn("근무 편성 1개 조", draft["body"],
                      "인계 초안 본문에 근무 편성 줄이 없습니다.")
        self.assertIn("홍길동", draft["body"])
        self.assertIn("김철수", draft["body"])
        self.assertEqual(1, draft["on_duty"]["team_count"])
        self.assertEqual(["홍길동", "김철수"],
                         draft["on_duty"]["teams"][0]["members"])
        self.assertEqual("1조", draft["on_duty"]["teams"][0]["team"])
        self.assertEqual("주간", draft["on_duty"]["teams"][0]["shift"])

    def test_no_roster_uploaded_is_honestly_labeled(self) -> None:
        """근무표가 없으면 지어내지 않고 「근무 편성 없음」을 그대로 적는다."""
        from apps.dsm import handover_service

        draft = handover_service.preview(scope=self.scope_a, hours=24)

        self.assertIn("근무 편성 없음", draft["body"])
        self.assertEqual(0, draft["on_duty"]["team_count"])
        self.assertEqual([], draft["on_duty"]["teams"])

    def test_saved_handover_row_body_persists_roster_line(self) -> None:
        """POST 저장 → `latest()` 재조회에도 근무자 줄이 그대로 남는다(왕복)."""
        from apps.dsm import handover_service, shift_roster_service

        csv_text = ("date,team,shift,members\n"
                   f"{_today()},2조,야간,이영희\n")
        shift_roster_service.import_csv(scope=self.scope_a, csv_text=csv_text)

        saved = handover_service.save(scope=self.scope_a, hours=24)
        self.assertIn("이영희", saved["body"])

        fresh = handover_service.latest(scope=self.scope_a)
        self.assertTrue(fresh["exists"])
        self.assertIn("이영희", fresh["body"],
                      "저장된 인계 메모를 다시 읽었더니 근무자 줄이 사라졌습니다.")

    def test_roster_is_tenant_scoped(self) -> None:
        """B 테넌트가 올린 근무표는 A 테넌트의 인계 초안에 안 섞인다(격리)."""
        from apps.dsm import handover_service, shift_roster_service

        csv_text = ("date,team,shift,members\n"
                   f"{_today()},3조,비번,남의동네직원\n")
        shift_roster_service.import_csv(scope=self.scope_b, csv_text=csv_text)

        draft = handover_service.preview(scope=self.scope_a, hours=24)

        self.assertNotIn("남의동네직원", draft["body"],
                         "B 테넌트 근무자가 A 테넌트 인계 초안에 섞였습니다 — "
                         "격리 실패입니다.")
        self.assertEqual(0, draft["on_duty"]["team_count"])
