# -*- coding: utf-8 -*-
"""P-408 · 턴 AO · 차선 L — (a) 재갈래 뒤 이번 턴에 고친 화면 자리들이 다시 새지 않는가.

이 파일도 `scripts/verify_ui_copy.py` 를 다시 만들지 않는다(D-479 — 두 벌은 반드시
어긋난다). 그 게이트가 이미 "잔여 0건"을 말하는 채로 `turn_an_7.json`(일곱째 회차)의
실제 화면 스캔이 U1#9 · U2#3 · U4#16 · U5#14 넷에서 「절 ID · 마크다운 강조 ·
상태 코드」를 여전히 잡았다 — 정적 검사는 **소스 문자열만** 본다. 서버가 채우고
화면이 `dataIndex` 원문으로 그대로 옮기는 자유 문장(판정 사유 · 발송 실패 사유 ·
감사 사유 · 재시작 사유)은 그 그물 밖이다. 이번 턴이 고친 것은 그 네 자리를 감싸는
`safeFreeText()`(우리 대장 표기만 지우고 문장은 버리지 않는다)와, U3#1 의 결과 문장이
「일부 실패」 갈래에서 다른 낱말로 갈라지던 자리다.

이 파일이 검증하는 것은 셋:
  ① `frontend/src/features/dsm/copy.ts::safeFreeText` — 결정 번호·절 ID·백틱·
     마크다운 강조·상태 열거값을 지우고, 사람이 쓴 나머지 문장은 그대로 둔다.
  ② `EventDetail.tsx`(판정 사유 · 실패 사유) · `AuditLog.tsx`(사유 열) ·
     `SystemSettings.tsx`(재시작 사유 열) 넷 다 그 함수로 렌더한다 — 원문
     `dataIndex` 그대로 찍는 자리가 되살아나지 않는가.
  ③ `EventDetail.tsx::notify()` 의 세 갈래(0건 · 일부 실패 · 정상) 전부가
     `measure_onboarding_t.py::rows_u3` 의 결과 문장 술어("발송을 요청했습니다" in
     본문)를 만족하는 문구를 낸다 — 「일부 실패」 갈래가 다시 다른 낱말로 갈라지면
     deliveries 는 늘어도 U3#1 은 다시 빨개진다(2026-09-29 · turn_an_7.json 실측).

소스 문자열 대조다 — HTTP 를 한 번도 때리지 않는다(직전 턴 AN 자매 파일과 같은 성질).
TypeScript 정규식의 실제 동작(자바스크립트 런타임)은 이 파일이 재현하지 않는다 —
그것은 프런트엔드 유닛시험의 몫이고, 여기는 **소스가 그 자리를 실제로 쓰는가**만 본다.

절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

from pathlib import Path

from django.test import TestCase


def _frontend_src() -> Path | None:
    for base in (Path("/repo/frontend/src"),
                 *(p / "frontend" / "src" for p in Path(__file__).resolve().parents)):
        if (base / "App.tsx").is_file():
            return base
    return None


class SafeFreeTextHelperTests(TestCase):
    """`copy.ts::safeFreeText` 가 서 있고, 이 턴이 기댄 네 그물을 다 두는가."""

    def setUp(self) -> None:
        self.src = _frontend_src()
        self.assertIsNotNone(self.src, "frontend/src 를 못 찾았다 — 판정 불가를 초록으로 두지 않는다")
        self.body = (self.src / "features/dsm/copy.ts").read_text(encoding="utf-8")

    def test_safe_free_text_is_exported(self) -> None:
        self.assertIn("export function safeFreeText(", self.body)

    def test_safe_free_text_strips_decision_number_and_section_id(self) -> None:
        # 결정 번호(D-\d{3}) · 절 ID(UX/SEC/OPS/QA/LAW/PERF/ISO/F/P/W/AC/FR/NFR/DA-\d{1,3})
        self.assertIn("FREE_TEXT_DECISION_NUMBER", self.body)
        self.assertIn("FREE_TEXT_SECTION_ID", self.body)
        self.assertIn(r"D-\d{3}", self.body)

    def test_safe_free_text_strips_markdown_and_backtick(self) -> None:
        self.assertIn("FREE_TEXT_BACKTICK", self.body)
        self.assertIn("FREE_TEXT_MARKDOWN_EMPHASIS", self.body)

    def test_safe_free_text_strips_bare_status_words(self) -> None:
        # verify_ui_copy.py::AA_STATUS_CODES 와 같은 낱말 무리다(두 벌이라는 것을
        # 안다 — 이 파일은 번들이고 그 파일은 스크립트라 import 로 합칠 수 없다).
        for word in ("occurred", "acknowledged", "in_progress", "confirmed",
                     "rejected", "resolved", "pending"):
            self.assertIn(word, self.body,
                          f"상태 열거값 {word} 가 safeFreeText 의 그물에서 빠졌다")

    def test_safe_free_text_does_not_discard_the_whole_sentence(self) -> None:
        # ★ 문장 자체는 버리지 않는다 — 머리말의 불변. 빈 문자열로 뭉개는 구현이
        #   되살아나면(예: `return ''` 로 항상 비우기) 이 시험은 못 잡지만, 적어도
        #   trim 만 하고 통째로 지우지는 않는다는 것을 소스 모양으로 본다.
        self.assertNotIn("return '';\n}", self.body.split("export function safeFreeText")[-1][:400])


class RawReasonColumnsUseSafeFreeTextTests(TestCase):
    """네 화면의 사유·실패 사유 칸이 `safeFreeText` 를 거치는가(원문 직접 찍기 재발 방지)."""

    def setUp(self) -> None:
        self.src = _frontend_src()
        self.assertIsNotNone(self.src, "frontend/src 를 못 찾았다 — 판정 불가를 초록으로 두지 않는다")

    def _read(self, rel: str) -> str:
        return (self.src / rel).read_text(encoding="utf-8")

    def test_event_detail_imports_safe_free_text(self) -> None:
        body = self._read("features/dsm/pages/EventDetail.tsx")
        self.assertIn("safeFreeText", body)
        self.assertIn("safeFreeText(e.reject_reason)", body,
                      "「판정 사유」 칸이 다시 e.reject_reason 원문을 직접 찍는다")

    def test_event_detail_failure_reason_column_no_longer_renders_raw(self) -> None:
        body = self._read("features/dsm/pages/EventDetail.tsx")
        self.assertIn("title: '실패 사유'", body)
        # 종전 결함 모양 — 되살아나면 실패한다.
        self.assertNotIn("render: (v?: string) => v || '',", body,
                         "「실패 사유」 칸이 다시 원문을 그대로(가공 없이) 찍는다")
        # dataIndex 'failure_reason' 바로 다음 render 가 safeFreeText 를 부르는지
        idx = body.index("dataIndex: 'failure_reason'")
        near = body[idx:idx + 200]
        self.assertIn("safeFreeText(", near,
                      "「실패 사유」 칸의 render 가 safeFreeText 를 거치지 않는다")

    def test_audit_log_reason_column_uses_safe_free_text(self) -> None:
        body = self._read("features/dsm/pages/AuditLog.tsx")
        self.assertIn("safeFreeText", body)
        idx = body.index("title: '사유'")
        near = body[idx:idx + 200]
        self.assertIn("safeFreeText(", near,
                      "감사 기록의 「사유」 칸이 safeFreeText 를 거치지 않는다")

    def test_system_settings_reason_column_uses_safe_free_text(self) -> None:
        body = self._read("features/dsm/pages/SystemSettings.tsx")
        self.assertIn("safeFreeText", body)
        idx = body.index("title: '사유'")
        near = body[idx:idx + 200]
        self.assertIn("safeFreeText(", near,
                      "재시작 요청의 「사유」 칸이 safeFreeText 를 거치지 않는다")


class NotifyOutcomeAllBranchesSayRequestedTests(TestCase):
    """U3#1 — notify() 의 세 갈래 모두 「발송을 요청했습니다」를 말하는가.

    `scripts/measure_onboarding_t.py::rows_u3` 의 결과 문장 술어는 정확히 이
    부분 문자열이 화면 본문에 있는가다(`msg = "발송을 요청했습니다" in b`).
    """

    def setUp(self) -> None:
        self.src = _frontend_src()
        self.assertIsNotNone(self.src, "frontend/src 를 못 찾았다 — 판정 불가를 초록으로 두지 않는다")
        self.body = (self.src / "features/dsm/pages/EventDetail.tsx").read_text(encoding="utf-8")

    def _notify_body(self) -> str:
        start = self.body.index("const notify = useCallback(")
        # 다음 useCallback 정의(등급 재판정)가 시작하기 전까지를 notify() 몸통으로 본다.
        end = self.body.index("const regrade = useCallback(", start)
        return self.body[start:end]

    def test_zero_total_branch_mentions_requested(self) -> None:
        chunk = self._notify_body()
        self.assertIn("total === 0", chunk)
        zero_branch = chunk[chunk.index("if (total === 0)"):chunk.index("} else if (total !== null && failed > 0)")]
        self.assertIn("발송을 요청했습니다", zero_branch,
                      "0건 갈래 문구에 「발송을 요청했습니다」가 없다 — U3#1 결과 문장 술어가 False 로 돌아간다")

    def test_partial_failure_branch_mentions_requested(self) -> None:
        chunk = self._notify_body()
        self.assertIn("failed > 0", chunk)
        start = chunk.index("} else if (total !== null && failed > 0)")
        end = chunk.index("} else {", start)
        failed_branch = chunk[start:end]
        self.assertIn("발송을 요청했습니다", failed_branch,
                      "일부 실패 갈래 문구에 「발송을 요청했습니다」가 없다 — "
                      "deliveries 는 늘어도(88→101 처럼) U3#1 결과 문장 술어가 False 가 된다")

    def test_success_branch_mentions_requested(self) -> None:
        chunk = self._notify_body()
        self.assertIn("발송을 요청했습니다", chunk[chunk.index("} else {"):])

    def test_error_branch_still_sets_outcome(self) -> None:
        # 오류 갈래는 이 턴에서 손대지 않았다 — 턴 AN 이 세운 상태 칸 배선이
        # 그대로인지만 다시 본다(회귀 방지).
        self.assertIn("setNotifyOutcome(", self.body)
        catch_idx = self.body.index("} catch (err) {\n      const line = userFacingError('EventDetail.notify'")
        self.assertIn("setNotifyOutcome(", self.body[catch_idx:catch_idx + 300])
