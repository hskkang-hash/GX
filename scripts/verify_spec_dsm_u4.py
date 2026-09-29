#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-356·358·392 — DSM U4 별표 절 승격 게이트 (WO-GX-20260925-15 §5 · 차선 N4 ·
턴 AM(구현) · 차선 N1 · 턴 AN(P-392 「반쪽 여섯 채우기」) · 차선 N1 · 턴 AO(P-407
「반쪽 잔여 셋」 — DSM-U4-07 「연간 통계(출력)」·`GET /video-access-requests/
annual-stats` 신설 · DSM-U5-05 「인계 메모 근무자 자동」·`handover_service.py`
연결. 둘 다 닫은 열 4건 안에 이미 있었다 — title_parts 행만 갱신했다).

`scripts/verify_spec_dsm.py`(차선 N1 소유 · 이 턴은 그 파일을 고치지 않는다)와
**같은 구조**로 복사해 세운 짝이다 — 두 게이트가 다른 모양이면 다음 사람이 파일
마다 다른 눈으로 읽어야 한다(D-212 계열). 이 게이트가 재는 것은 **N4 배정
(DSM-U4-01·02·03·04·05·07·08·09 · DSM-U5-05, 아홉)** 뿐이다 — N1 배정(턴 AK·AL·
AM 의 29절)은 `verify_spec_dsm.py` 가 계속 잰다. 대장에 옮길 때는 두 게이트의
「닫은 열」을 합쳐서 본다(조율자 몫).

무엇을 재는가 — 넷(P-392 · `verify_spec_fws_f3b.py` 와 같은 그림)
--------------------------------------------------------------------
    ① **길목** — `tests/test_p356_u4_rest_spec_promotions.py` 를 gx-shell 안에서
       돈다. 판정 규칙은 그 시험이 이미 정했다(D-212) — 도는 김에
       `docs/agent/evidence/SPEC/<id>.json` 을 기계로 새로 찍는다.
    ② **증거 성립** — 방금 찍힌 증거가 「HTTP 로 실제로 두드렸다」는 모양을
       갖췄는가.
    ③ **title_parts 빈 칸 0**(P-392) — 「제목이 부르는 것 ↔ 있는 것」 표에 빈
       칸이 있으면 반쪽이다 — 반쪽 승격은 이 게이트가 빨강으로 막는다. 닫은 열
       넷(U4-03·04·07·U5-05) 전부 이 턴(AN)이 title_parts 를 새로 채웠으므로
       **여기서는 필수**(F6 게이트와 달리 완화하지 않는다 — 이 게이트의 닫은
       열은 전부 이 파일이 소유한다).
    ④ **절 목록 전수** — N4 배정 아홉을 전부 찍는다. 닫은 넷(U4-03·04·07·
       U5-05 — 전부 **부분 승격**)은 ①②③으로, 못 닫은 다섯(U4-01·02·05·08·09)은
       **「무엇이 없는가」 한 줄**로.

    ★ [턴 AN · P-392 · 결정 ⑤] **DSM-U4-01(HWPX)은 이 턴부터 닫은 열에서 뺀다** —
      채번 대장(제N보·최초/중간/최종·발송기록)은 여전히 서 있고 증거 파일도
      그대로 남지만, 명세 제목이 부르는 HWPX 산출은 「안 산다」로 정했다(DOCX 가
      정본 · HWPX 는 v1.2 옵션 · 출시 뒤 표 후보). title_parts 없이 「부분
      승격」을 자칭하던 예전 판단을 거두고, 정직하게 NOT_STARTED 로 옮긴다.

종료 코드 (D-400)
    0 = 쟀고 통과   1 = 쟀고 실패   2 = 못 쟀다(회색)

    python scripts/verify_spec_dsm_u4.py                  # 판정(호스트 — docker 를 부른다)
    python scripts/verify_spec_dsm_u4.py --self-test        # 판정 규칙만
    python scripts/verify_spec_dsm_u4.py --no-run            # ②③만(기본값)
    python scripts/verify_spec_dsm_u4.py --run                # pytest 를 다시 돌려 증거를 새로 찍는다
    python scripts/verify_spec_dsm_u4.py --shell gx-shell     # 컨테이너 이름을 바꿔 잰다

호스트에서 돈다 — `guardianx-host-cannot-see-gate-servers`: 서버를 때리는 것은
gx-shell 안이고, 호스트는 docker exec 로 위임한다.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
TESTS_RELS: tuple[str, ...] = (
    "tests/test_p356_u4_rest_spec_promotions.py",   # 턴 AM — N4 배정 다섯 승격
)
TESTS: tuple[Path, ...] = tuple(BACKEND / rel for rel in TESTS_RELS)
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"
SHELL_CONTAINER = "gx-shell"
TAG = "[SPEC-DSM-U4]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 닫은 열 — 전부 **N4(WO-15 §5) 배정**, 이 턴(AN·N1)이 반쪽을 채웠다. 전부 부분
#: 승격이다(어느 항목이 빠졌는지는 `docs/agent/evidence/SPEC/N4_promotions.md`·
#: `N1_promotions_an.md` 의 「제목이 부르는 것 ↔ 있는 것」 표 · 각 서비스 파일
#: 머리말 · evidence JSON 의 `title_parts`).
CLOSED_CLAUSES: tuple[str, ...] = (
    "DSM-U4-03", "DSM-U4-04", "DSM-U4-07", "DSM-U5-05",
)

#: annex 원문(§4.4·§4.5) 제목 — 명세서 표 그대로. 판정에 안 쓴다(사람이 읽을
#: 이름표일 뿐 — 판정은 evidence 파일이 한다).
TITLES: dict[str, str] = {
    "DSM-U4-01": "재난상황보고서(별지 제1호서식) 작성 — 13항목·제N보·최초/중간/최종",
    "DSM-U4-02": "중간 보고 사이클",
    "DSM-U4-03": "재난문자(CBS) 초안",
    "DSM-U4-04": "통제·대피 현황판",
    "DSM-U4-05": "일일상황보고 자동",
    "DSM-U4-07": "영상 열람·제공(반출) 대장",
    "DSM-U4-08": "재난관리평가·감사 자료 묶음",
    "DSM-U4-09": "통계 축 추가 — 지역안전지수 6분야",
    "DSM-U5-05": "교대 편성 — 4조 3교대 근무표 업로드(CSV)",
}

#: N4 배정 아홉 중 못 닫은 다섯 — **「무엇이 없는가」 한 줄**(P-358 형식). 빈
#: 칸으로 두지 않는다(D-274).
NOT_STARTED: dict[str, str] = {
    "DSM-U4-01": "재난상황보고서 HWPX 산출물 — [턴 AN · P-392 · 결정 ⑤ 「안 "
                "산다」] 이 저장소의 정본 산출물은 DOCX(`api_u24.py::"
                "situation_report_docx`)뿐이다. HWPX(한글과컴퓨터 OWPML) 렌더러는 "
                "새 의존성이고, 이번 턴이 사지 않기로 했다 — v1.2 옵션으로 미루고 "
                "출시 뒤 수요가 있으면 그때 표 후보로 다시 올린다. 채번 대장 자체"
                "(제N보 채번·최초/중간/최종 구분·발송 기록·경과분 계산)는 이미 "
                "서 있다(`situation_report_ledger_service.py` · "
                "`docs/agent/evidence/SPEC/DSM-U4-01.json` 의 `decision_note` "
                "참조) — 이 절이 못 닫힌 이유는 HWPX 하나뿐이다.",
    "DSM-U4-02": "중간 보고 사이클 — 08·17시 기준 자동 초안 배치·NDMS 표 내보내기가 "
                "없다. M 규모(배치 스케줄 + 표 1:1 매핑)라 이번 차선(가장 싼 것 "
                "우선)의 시간 안에 못 붙였다 — DSM-U4-01 채번 대장은 이번 턴에 섰지만 "
                "「08·17시 자동」은 별도 배치가 필요하다.",
    "DSM-U4-05": "일일상황보고 자동 — 06:00 자동 배치가 없다. 기존 "
                "`monthly_report.py::KINDS` 는 세 종류로 잠겨 있고(그 파일은 N1 소유, "
                "이 턴이 고치지 않는다) 별도 경로를 새로 파는 것도 M 규모다 — 06:00 "
                "celery beat 등재는 `config/**`(조율자 소유)이고, 등재 없이 「자동」을 "
                "주장하면 거짓이다. 이번 배정에서 DSM-U4-04(통제현황판)가 먼저 서서 "
                "다음 턴에 이 절이 그 현황판 요약을 그대로 빌려 쓸 수 있다.",
    "DSM-U4-08": "재난관리평가·감사 자료 묶음 — 기간별 ZIP(PDF+CSV) 조립 배치가 없다. "
                "이번 턴 U4-01·03·04·07 넷이 새로 섰지만(각 부분 승격) **HWPX/PDF 로 "
                "찍어 내는 서식이 아니라 JSON 감사 이력**이다 — ZIP 에 넣을 PDF/CSV "
                "산출물 자체가 없다. U4-02·05 도 여전히 없어 「10분 내 생성」을 잴 재료가 "
                "부족하다.",
    "DSM-U4-09": "통계 축 추가 — `stats?by=safety_index`(지역안전지수 6분야 매핑)가 "
                "없다. 기존 `stats_axes`(턴 T 소유)는 5축(카메라·유형·심각도·판정·"
                "시간대)뿐이고, 그 표를 늘리는 것은 공유 파일(`apps/dsm/stats.py`)을 "
                "고치는 일이라 이번 차선의 새 파일 전용 범위 밖이다.",
}

REQUIRED_EVIDENCE_KEYS = ("id", "measured_at", "measured_by", "test", "request",
                         "response", "what", "title_parts")
REQUIRED_TITLE_PART_KEYS = ("part", "where", "status")


# ═══════════════════════════════════════════════════════════════════════════
# 판정 — **순수 함수** (자기시험이 docker 없이 이것을 잰다)
# ═══════════════════════════════════════════════════════════════════════════
def parse_pytest_summary(output: str) -> tuple[int, int, int] | None:
    """(passed, failed, errors). 못 읽으면 `None`."""
    tail = None
    for line in reversed(output.splitlines()):
        if " in " in line and ("passed" in line or "failed" in line or "error" in line):
            tail = line
            break
    if tail is None:
        return None
    passed = int(re.search(r"(\d+) passed", tail).group(1)) if "passed" in tail else 0
    failed = int(re.search(r"(\d+) failed", tail).group(1)) if "failed" in tail else 0
    errors = int(re.search(r"(\d+) error", tail).group(1)) if "error" in tail else 0
    return passed, failed, errors


def judge_gate_tests(summary: tuple[int, int, int] | None) -> tuple[int, str]:
    if summary is None:
        return EXIT_UNDECIDABLE, "길목 시험 출력에서 요약 줄을 못 읽었다 — 못 쟀다"
    passed, failed, errors = summary
    if failed or errors:
        return (EXIT_FAIL,
                "길목 시험 %d실패 · %d에러 (통과 %d)" % (failed, errors, passed))
    if passed == 0:
        return EXIT_UNDECIDABLE, "길목 시험이 0건 통과·0건 실패 — 수집조차 안 됐다(못 쟀다)"
    return EXIT_OK, "길목 시험 %d건 전부 통과" % passed


def judge_title_parts(clause_id: str, payload: dict) -> tuple[int, str]:
    """P-392 — 「제목이 부르는 것 ↔ 있는 것」 표에 빈 칸이 있으면 빨강
    (`verify_spec_fws_f3b.py::judge_title_parts` 와 같은 판정식 — D-212).

    ⚠ **자기시험이 이 함수를 몸소 망가뜨려 본다** — 「없으면 넘긴다」로 흐리면
      반쪽 승격을 이 게이트가 못 잡는다."""
    parts = payload.get("title_parts")
    if not isinstance(parts, list) or not parts:
        return EXIT_FAIL, "%s — title_parts 가 없거나 비었다(반쪽 승격 의심)" % clause_id
    for i, part in enumerate(parts):
        if not isinstance(part, dict):
            return EXIT_FAIL, "%s — title_parts[%d] 가 표 모양이 아니다" % (clause_id, i)
        missing = [k for k in REQUIRED_TITLE_PART_KEYS
                  if not (part.get(k) or "").strip()]
        if missing:
            return (EXIT_FAIL,
                    "%s — title_parts[%d] 에 빈 칸: %s" % (clause_id, i, missing))
    return EXIT_OK, "%s — title_parts %d행 전부 채워짐" % (clause_id, len(parts))


def judge_evidence(clause_id: str, payload: dict | None) -> tuple[int, str]:
    """이 절의 증거 한 건이 「HTTP 로 실제로 두드렸다」는 모양을 갖췄는가.

    ⚠ **자기시험이 이 함수를 몸소 망가뜨려 본다** — `verify_spec_dsm.py::judge_evidence`
      와 같은 판정식(짝을 두 벌로 재면 어긋난다 · D-212).
    """
    if payload is None:
        return EXIT_UNDECIDABLE, "%s — 증거 파일이 없다(못 쟀다)" % clause_id
    missing = [k for k in REQUIRED_EVIDENCE_KEYS if k not in payload]
    if missing:
        return EXIT_FAIL, "%s — 증거에 칸이 없다: %s" % (clause_id, missing)
    if payload.get("id") != clause_id:
        return (EXIT_FAIL,
                "%s — 증거 파일의 id(%r)가 파일 이름과 다르다" % (clause_id, payload.get("id")))
    if payload.get("measured_by") != "django_test_client":
        return (EXIT_FAIL,
                "%s — measured_by=%r 는 손으로 쟀다는 뜻이다(pytest 실측이 아니다)"
                % (clause_id, payload.get("measured_by")))
    if not (payload.get("test") or "").strip():
        return EXIT_FAIL, "%s — 어느 시험이 쟀는지(test)가 비었다" % clause_id
    if not (payload.get("what") or "").strip():
        return EXIT_FAIL, "%s — 무엇을 쟀는지(what)가 비었다" % clause_id
    response = payload.get("response") or {}
    status = response.get("status")
    if not isinstance(status, int) or not (200 <= status <= 299):
        return EXIT_FAIL, "%s — 응답 상태가 2xx 가 아니다(status=%r)" % (clause_id, status)
    request = payload.get("request") or {}
    if not (request.get("path") or "").startswith("/api/dsm/"):
        return (EXIT_FAIL,
                "%s — 요청 경로(%r)가 /api/dsm/ 가 아니다 — 다른 문을 잰 증거일 수 있다"
                % (clause_id, request.get("path")))
    code, verdict = judge_title_parts(clause_id, payload)
    if code != EXIT_OK:
        return code, verdict
    return EXIT_OK, "%s — 증거 성립(2xx · %s %s · %s)" % (
        clause_id, request.get("method"), request.get("path"), verdict)


def combine(codes: list[int]) -> int:
    if EXIT_FAIL in codes:
        return EXIT_FAIL
    if EXIT_UNDECIDABLE in codes:
        return EXIT_UNDECIDABLE
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 재기 — gx-shell 안에 위임
# ═══════════════════════════════════════════════════════════════════════════
def run_gate_tests(shell: str) -> str | None:
    try:
        r = subprocess.run(
            ["docker", "exec",
             "-e", "DJANGO_SETTINGS_MODULE=config.settings",
             "-e", "DB_TEST_NAME=test_gx_verify_spec_dsm_u4",
             "-w", "/app", shell,
             "python", "-m", "pytest", *TESTS_RELS,
             "-q", "--create-db", "-p", "no:randomly"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            #: `guardianx-lane-count-ceilings` — 공유 gx-shell 은 다른 차선과 나뉜다.
            timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("%s [입력] docker exec pytest 를 못 불렀다 — %s" % (TAG, exc))
        return None
    return (r.stdout or "") + (r.stderr or "")


def _load_evidence(clause_id: str) -> dict | None:
    path = EVIDENCE_DIR / ("%s.json" % clause_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310·P-319) — **판정식을 몸소 망가뜨려 실패(1)를 본다**
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    fails = 0

    def check(label: str, ok: bool) -> None:
        nonlocal fails
        fails += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))

    p, f, e = parse_pytest_summary("....                                    [100%]\n"
                                   "4 passed in 1.20s\n")
    check("pytest 요약 — 4 passed 를 읽는다", (p, f, e) == (4, 0, 0))
    p, f, e = parse_pytest_summary("F.F                                     [100%]\n"
                                   "1 passed, 2 failed in 0.55s\n")
    check("pytest 요약 — 실패 섞인 줄도 읽는다", (p, f, e) == (1, 2, 0))
    check("요약 줄이 없으면 None(못 쟀다)", parse_pytest_summary("collected 0 items\n") is None)

    code, _ = judge_gate_tests((10, 0, 0))
    check("① 전부 통과 → 초록", code == EXIT_OK)
    code, _ = judge_gate_tests((9, 1, 0))
    check("★ ① 1건 실패 → 빨강", code == EXIT_FAIL)
    code, _ = judge_gate_tests(None)
    check("① 요약을 못 읽으면 → 회색", code == EXIT_UNDECIDABLE)

    good_parts = [{"part": "유형·구역 선택", "where": "create_draft(kind, region)",
                  "status": "있음"}]
    good = {
        "id": "DSM-U4-03", "measured_at": "2026-09-28T00:00:00+00:00",
        "measured_by": "django_test_client",
        "test": "tests.test_p356_u4_rest_spec_promotions.X.y",
        "request": {"method": "POST", "path": "/api/dsm/cbs-drafts", "body": {}},
        "response": {"status": 200, "body": {}}, "what": "실측",
        "title_parts": good_parts,
    }
    code, _ = judge_evidence("DSM-U4-03", good)
    check("증거 성립 표본 → 초록", code == EXIT_OK)

    no_parts = dict(good, title_parts=[])
    code, _ = judge_evidence("DSM-U4-03", no_parts)
    check("★★ title_parts 비어 있으면 → 빨강(P-392 반쪽 승격을 막는다)",
         code == EXIT_FAIL)

    blank_cell = dict(good, title_parts=[{"part": "유형·구역 선택", "where": "",
                                         "status": "있음"}])
    code, _ = judge_evidence("DSM-U4-03", blank_cell)
    check("★★ title_parts 안 빈 칸 하나 → 빨강", code == EXIT_FAIL)

    code, _ = judge_evidence("DSM-U4-03", None)
    check("증거 파일 없음 → 회색(못 쟀다)", code == EXIT_UNDECIDABLE)

    broken_status = dict(good, response={"status": 500, "body": {}})
    code, _ = judge_evidence("DSM-U4-03", broken_status)
    check("★★ 출생표본 — 응답 500 인 증거 → 빨강(성공을 가장한 실패를 못 잡으면 "
         "이 게이트는 없느니만 못하다)", code == EXIT_FAIL)

    broken_hand = dict(good, measured_by="hand")
    code, _ = judge_evidence("DSM-U4-03", broken_hand)
    check("★ measured_by=hand(손으로 적음) → 빨강", code == EXIT_FAIL)

    broken_path = dict(good, request={"method": "POST", "path": "/api/fws/x", "body": {}})
    code, _ = judge_evidence("DSM-U4-03", broken_path)
    check("★ 다른 App 경로를 잰 증거 → 빨강", code == EXIT_FAIL)

    broken_id = dict(good, id="DSM-U4-99")
    code, _ = judge_evidence("DSM-U4-03", broken_id)
    check("파일 이름과 id 가 다르면 → 빨강", code == EXIT_FAIL)

    check("combine — 하나라도 빨강이면 빨강", combine([EXIT_OK, EXIT_FAIL]) == EXIT_FAIL)
    check("combine — 빨강 없고 회색 있으면 회색",
         combine([EXIT_OK, EXIT_UNDECIDABLE]) == EXIT_UNDECIDABLE)
    check("combine — 전부 초록이면 초록", combine([EXIT_OK, EXIT_OK]) == EXIT_OK)

    print("%s 자기시험 %d건 실패" % (TAG, fails))
    return EXIT_FAIL if fails else EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="DSM-U4 별표 절 승격 게이트(턴 AM · 차선 N4)")
    ap.add_argument("--self-test", action="store_true")
    #: 기본은 다시 안 돌린다 — `verify_spec_dsm.py` 와 같은 판단(추적 파일이 매번
    #:   바뀌면 측정 재현성(D-344)이 깨진다). 다시 돌려 증거를 새로 찍는 것은 `--run`.
    ap.add_argument("--run", action="store_true",
                   help="pytest 를 다시 돌려 evidence 를 새로 찍는다(손으로만)")
    ap.add_argument("--no-run", action="store_true",
                   help="pytest 를 다시 안 돌린다 — 지금 있는 evidence 파일만 본다")
    ap.add_argument("--shell", default=SHELL_CONTAINER)
    args = ap.parse_args()
    args.no_run = args.no_run or not args.run

    if args.self_test:
        return self_test()

    codes: list[int] = []

    if args.no_run:
        print("%s [입력] --no-run — pytest 를 다시 안 돌린다(지금 있는 evidence 파일만)"
             % TAG)
    else:
        missing = [rel for rel, path in zip(TESTS_RELS, TESTS) if not path.exists()]
        if missing:
            print("%s **판정 불가 · 회색** — 길목 시험 파일이 없다: %s"
                 % (TAG, missing))
            return EXIT_UNDECIDABLE
        output = run_gate_tests(args.shell)
        if output is None:
            return EXIT_UNDECIDABLE
        print(output)
        summary = parse_pytest_summary(output)
        code, verdict = judge_gate_tests(summary)
        codes.append(code)
        print("%s ① 길목 — %s" % (TAG, verdict))
        if code == EXIT_FAIL:
            print("%s **판정 불가하지 않다 · 빨강** — 길목 시험이 실패했다. evidence 를 "
                 "다시 찍지 않고 지금 있는 파일로 ②③을 마저 본다." % TAG)

    print("%s ── 절별 판정 (닫은 열 %d · 못 닫은 열 %d) ──"
         % (TAG, len(CLOSED_CLAUSES), len(NOT_STARTED)))
    for clause_id in CLOSED_CLAUSES:
        payload = _load_evidence(clause_id)
        code, verdict = judge_evidence(clause_id, payload)
        codes.append(code)
        mark = "OK  " if code == EXIT_OK else ("FAIL" if code == EXIT_FAIL else "GRAY")
        print("%s %s [%s] %s — %s" % (TAG, mark, clause_id, TITLES[clause_id], verdict))

    for clause_id in sorted(NOT_STARTED):
        print("%s MISS [%s] %s — 무엇이 없는가: %s"
             % (TAG, clause_id, TITLES[clause_id], NOT_STARTED[clause_id]))

    final = combine(codes)
    denom = len(CLOSED_CLAUSES) + len(NOT_STARTED)  # 9 = N4 배정(U4-01~09 · U5-05)
    print("%s ── 요약 — 닫은 열 %d/%d(분모는 이 차선 배정 %d) · 최종 %s ──"
         % (TAG, sum(1 for c in codes[1:] if c == EXIT_OK) if not args.no_run
            else sum(1 for c in codes if c == EXIT_OK),
            len(CLOSED_CLAUSES), denom,
            {EXIT_OK: "PASS", EXIT_FAIL: "FAIL", EXIT_UNDECIDABLE: "GRAY"}[final]))
    return final


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE

    gate_header(
        __file__,
        target="gx-shell(%s) 안 backend/ · apps.dsm.situation_report_ledger_service · "
              "apps.dsm.cbs_draft_service · apps.dsm.control_board_service · "
              "apps.dsm.video_access_ledger_service · apps.dsm.shift_roster_service · "
              "apps.dsm.api_u4 · docs/agent/evidence/SPEC/*.json" % SHELL_CONTAINER,
        as_="pytest 는 자격증명 없이 --create-db 로 돈다 · HTTP 실측은 "
            "tests/test_p356_u4_rest_spec_promotions.py 안에서 실제 JWT"
            "(RefreshToken.for_user)로",
        source="살아 있는 gx-shell 컨테이너(docker exec) · 그 실행이 방금 새로 쓴 "
              "evidence 파일 — 사진·손으로 옮긴 값이 아니라 이번 실행",
        measured="닫은 열 4건(DSM-U4-03·04·07 · U5-05 — 전부 부분 승격 · 턴 AM 구현 "
                "차선 N4 · 턴 AN title_parts 반쪽 채움 차선 N1) · 못 닫은 열 5건은 "
                "이유 1줄(U4-01 결정 ⑤ · U4-02·05·08·09) · 분모 9(이 차선 N4 배정 "
                "U4-01~09 · U5-05)",
    )
    raise SystemExit(main())
