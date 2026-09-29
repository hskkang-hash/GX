# -*- coding: utf-8 -*-
"""P-392 · WO-17 §4 O — `scripts/verify_spec_title_parts.py` 의 짝(P-319·P-323).

이 게이트는 「제목이 부르는 것 ↔ 있는 것」 표의 **빈 칸**을 센다 — 표가 있는데
빈 칸/열린 행이 남으면 반쪽 승격이고, 반쪽은 닫힘이 아니다(P-376). `TheSelfTestCanFail`
은 그 판정식을 몸소 망가뜨려(반쪽을 통과시킨다 · 증거 없음을 통과시킨다) 자기시험이
정말 `1` 을 내는지 본다 — F6 게이트 짝(`test_verify_spec_fws_f6_gate_can_fail.py`)과
같은 절차(D-277 — 순수 함수를 판정, 몸통에서 참조만 바꾼다).

캐시 처리: 해당 없음 — 이 시험은 HTTP 를 안 두드리고 DB 도 안 쓴다(대장 YAML 과
`docs/agent/evidence/SPEC/*.json` 만 읽는 순수 함수를 그대로 부른다). `SimpleTestCase`.

gx-shell 에서 이 파일을 찾는 방식은 `test_p237_onboarding_probe_billing.py`·
`test_verify_spec_fws_f6_gate_can_fail.py` 가 이미 쓰는 자리 그대로다 —
컨테이너에는 `/repo` 가 저장소 뿌리로 마운트돼 있고, 호스트에서 돌 때는 이 파일
기준 상위 디렉터리를 되짚는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

from django.test import SimpleTestCase


def _gate():
    here = Path(__file__).resolve()
    for cand in ("/repo/scripts", str(here.parent.parent.parent / "scripts")):
        if Path(cand).is_dir() and cand not in sys.path:
            sys.path.insert(0, cand)
    import verify_spec_title_parts  # noqa: PLC0415

    return verify_spec_title_parts


# ═══════════════════════════════════════════════════════════════════════════
# TheSelfTestCanFail — 판정식을 몸소 망가뜨려 본다(P-319 · P-323)
# ═══════════════════════════════════════════════════════════════════════════
class TheSelfTestCanFail(SimpleTestCase):
    def test_self_test_passes_as_built(self) -> None:
        self.assertEqual(0, _gate().self_test())

    def test_self_test_fails_when_half_promotion_is_waved_through(self) -> None:
        """★★★ 이 게이트가 있는 이유 그 자체 — 표가 있고 빈 칸이 남았는데 그것을
        「깨끗함」으로 읽으면, 반쪽 승격이 대장에 초록으로 올라간다."""
        g = _gate()
        real = g.classify_payload

        def waves_half(clause_id, payload):
            r = real(clause_id, payload)
            if r["bucket"] == "half":
                r = dict(r, verdict="ok", bucket="clean",
                        detail="빈 칸이 있어도 통과시킨다(망가진 판정)")
            return r

        g.classify_payload = waves_half
        try:
            got = g.self_test()
        finally:
            g.classify_payload = real
        self.assertEqual(1, got,
                         "빈 칸/열린 행이 있는 표를 깨끗하다고 읽는 판정식을 "
                         "자기시험이 못 잡는다")

    def test_self_test_fails_when_missing_evidence_reads_as_clean(self) -> None:
        """★ 증거 파일이 없는데(못 쟀다) 그것을 「깨끗함」으로 읽으면 — 증거가
        하나도 없는 절이 표까지 다 갖춘 것으로 보인다."""
        g = _gate()
        real = g.classify_payload

        def waves_missing(clause_id, payload):
            if payload is None:
                return {"id": clause_id, "verdict": "ok", "bucket": "clean",
                        "detail": "증거가 없어도 통과시킨다(망가진 판정)"}
            return real(clause_id, payload)

        g.classify_payload = waves_missing
        try:
            got = g.self_test()
        finally:
            g.classify_payload = real
        self.assertEqual(1, got,
                         "증거 파일이 없는 것을 통과시키는 판정식을 자기시험이 못 잡는다")

    def test_self_test_fails_when_closed_status_check_is_removed(self) -> None:
        """★ status 가 무엇이든 「닫혔다」로 읽으면 — 열린 부분이 안 보인다."""
        g = _gate()
        real = g._is_closed

        g._is_closed = lambda status: True
        try:
            got = g.self_test()
        finally:
            g._is_closed = real
        self.assertEqual(1, got,
                         "열린 status 를 전부 닫힘으로 읽는 판정식을 자기시험이 못 잡는다")

    def test_self_test_fails_when_rule_doc_sync_check_is_waved_through(self) -> None:
        """★★★ [턴 AP · P-419] 눈금 문서 대조가 이 게이트에 있는 이유 그 자체 —
        문서 목록과 코드 상수가 갈려도(또는 문서가 없어도) 「같다」로 읽으면,
        사람마다 다른 눈금을 쓰는 것을 이 게이트가 못 잡는다."""
        g = _gate()
        real = g.check_rule_doc_sync

        g.check_rule_doc_sync = lambda items: {"verdict": "ok", "detail": "항상 같다고 우긴다(망가진 판정)"}
        try:
            got = g.self_test()
        finally:
            g.check_rule_doc_sync = real
        self.assertEqual(1, got,
                         "눈금 문서 목록이 코드 상수와 갈려도 통과시키는 판정식을 "
                         "자기시험이 못 잡는다")


# ═══════════════════════════════════════════════════════════════════════════
# [턴 AP · P-419 · 차선 N1] 눈금 문서(TITLE_PARTS_RULE.md) — 존재 + 목록 대조
# ═══════════════════════════════════════════════════════════════════════════
class RuleDocTest(SimpleTestCase):
    """`docs/agent/evidence/SPEC/TITLE_PARTS_RULE.md` — 이 게이트가 실제로
    읽는 문서. 문서가 없으면 회색 · 문서의 닫힘 status 앞머리 목록이 코드
    상수 `CLOSED_PREFIXES` 와 갈리면 빨강(사람마다 다른 눈금 0)."""

    def test_rule_doc_exists_and_matches_code_constant_today(self) -> None:
        g = _gate()
        items, why = g.load_rule_doc()
        if items is None:
            #: ★ [gx-shell] `/repo/docs` 는 `backend`·`scripts` 와 달리 살아
            #:   있는 마운트가 아니다(이 파일의 `RealRepoSnapshotTest` 와 같은
            #:   판단) — 「못 찾았다」를 실패로 읽지 않는다, skip 한다.
            self.skipTest("이 환경의 /repo/docs 가 눈금 문서를 안 들고 있다 — "
                         "%s (호스트에서 직접 돌리면 읽힌다)" % why)
        verdict = g.check_rule_doc_sync(items)
        self.assertEqual("ok", verdict["verdict"], verdict["detail"])

    def test_check_rule_doc_sync_is_grey_when_doc_missing(self) -> None:
        """순수 함수 표본 — items=None(문서 없음·모양 안 맞음)은 회색이다."""
        g = _gate()
        verdict = g.check_rule_doc_sync(None)
        self.assertEqual("grey", verdict["verdict"])

    def test_check_rule_doc_sync_is_red_when_list_diverges(self) -> None:
        """순수 함수 표본 — 목록이 코드 상수와 원소 하나라도 다르면 빨강."""
        g = _gate()
        verdict = g.check_rule_doc_sync(["measured", "present", "있음"])  # "구현" 빠짐
        self.assertEqual("red", verdict["verdict"])

    def test_parse_rule_doc_prefixes_reads_the_real_file_line(self) -> None:
        """실물 파일을 직접 열어 `CLOSED_PREFIXES = ...` 줄을 읽는다(문서가
        게이트가 읽는 모양 그대로인지 — 파싱이 아니라 문서 내용을 건다)."""
        g = _gate()
        if not g.RULE_DOC.is_file():
            self.skipTest("이 환경의 /repo/docs 가 눈금 문서를 안 들고 있다 "
                         "(호스트에서 직접 돌리면 읽힌다)")
        text = g.RULE_DOC.read_text(encoding="utf-8")
        items = g._parse_rule_doc_prefixes(text)
        self.assertEqual(list(g.CLOSED_PREFIXES), items)


# ═══════════════════════════════════════════════════════════════════════════
# 지금 이 저장소의 실물 — **대장·SPEC 폴더를 실제로 읽는다**(못 박은 표본이 아니다)
# ═══════════════════════════════════════════════════════════════════════════
class RealRepoSnapshotTest(SimpleTestCase):
    """2026-09-29 실측: 영역 7 의 DSM-/FWS-/O- 접두 절 39건 · 표 있음 0 ·
    빈 칸/열린 행 있는 반쪽(red) 0 · 옛 승격·표 없음(grey) 39. 숫자 39 를 못 박지
    않는다 — 다음 턴이 표를 채우면 legacy 는 줄고 ok 나 half 가 는다. 여기서
    거는 것은 **구조**(분모=반쪽+깨끗함+옛승격+증거없음+모양이상 · exit 0 ↔ 반쪽 0)뿐이다."""

    def test_measure_reads_the_real_ledger_and_evidence(self) -> None:
        g = _gate()
        rep = g.measure()
        if not rep.get("ok"):
            #: ★ [실측 2026-09-29 · gx-shell] `/repo/docs` 는 **`backend`·`scripts`
            #:   와 달리 살아 있는 마운트가 아니다** — `D-346/ga_readiness.yaml` 이
            #:   컨테이너 안에 없다(호스트에는 있다). 「못 찾았다」를 「0건」으로
            #:   읽지 않는다(D-301) — 회색(skip)으로 적는다, 초록으로 숨기지 않는다
            #:   (`test_p237_onboarding_probe_billing.py` 와 같은 판단).
            self.skipTest("이 환경(gx-shell)의 /repo/docs 가 대장을 안 들고 있다 — "
                         "%s (호스트에서 직접 돌리면 읽힌다)" % rep.get("why"))
        self.assertTrue(rep.get("ok"), rep.get("why"))
        self.assertGreater(rep["promoted_n"], 0,
                           "영역 7 에서 DSM-/FWS-/O- 접두 절을 하나도 못 읽었다")
        b = rep["buckets"]
        total = (len(b["ok"]) + len(b["half"]) + len(b["legacy_no_table"])
                + len(b["no_evidence"]) + len(b["malformed"]))
        self.assertEqual(total, rep["promoted_n"],
                         "다섯 칸의 합이 분모와 다르다 — 절 하나가 두 번 세어지거나 "
                         "빠졌다")

    def test_no_visible_half_promotion_today(self) -> None:
        """★ 2026-09-29 실측 — 지금 대장의 영역 7 승격 39건 중 **표를 가진 것은
        전부 빈 칸 0**이다(아직 아무도 표를 채우지 않았을 뿐 — 채운 표가 반쪽인
        경우는 0건). 이 시험이 빨강이 되면 **실제로 반쪽 승격이 생긴 것**이니
        `docs/agent/evidence/SPEC/O_promotions.md` 에 「소급 빨강」청구로 옮긴다."""
        g = _gate()
        rep = g.measure()
        if not rep.get("ok"):
            self.skipTest("이 환경(gx-shell)의 /repo/docs 가 대장을 안 들고 있다 — "
                         "%s (호스트에서 직접 돌리면 읽힌다)" % rep.get("why"))
        self.assertEqual(0, len(rep["buckets"]["half"]),
                         "반쪽 승격(표 있음 · 빈 칸/열린 행 1+) 이 나타났다: %s"
                         % [r["id"] for r in rep["buckets"]["half"]])
        self.assertEqual(g.EXIT_OK, g.report(rep))

    def test_no_area7_not_found_is_grey_not_zero(self) -> None:
        """D-301 — 「못 읽었다」와 「0건」은 다른 사실이다. 대장 구조가 바뀌어
        영역 7 이 사라지면 이 게이트는 회색(exit 2)이지, 승격 0건(exit 0)이 아니다."""
        g = _gate()
        broken = {"areas": [{"id": "2", "clauses": [{"id": "DSM-U1-01"}]}]}
        rep = {"ok": False,
              "why": "대장에서 영역 id==\"7\" 을 못 찾았다"} if not \
            g.promoted_area7_ids(broken)[2] else None
        self.assertIsNotNone(rep, "이 표본 대장에는 영역 7 이 없어야 한다")
        self.assertEqual(g.EXIT_GREY, g.report(rep))
