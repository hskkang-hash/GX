#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-356·392 — DSM-U3-01·U3-02·U6-01·U6-03 별표 절 승격 게이트 (턴 AO ·
WO-GX-20260930-18 §N4 · 차선 N4).

`scripts/verify_spec_u5_an.py` 의 **판정식을 그대로 베낀다**(그 파일 머리말과
같은 이유 — D-212 를 어기지 않는다: 같은 규칙(P-356)을 재는 두 게이트가 서로를
import 하지 않고 판정 함수 모양만 같은 것은 DA-04 §1-1 과 같은 결).

무엇을 재는가 — 셋
--------------------
    ① **길목** — `backend/tests/test_dsm_u36_an.py` 를 gx-shell 안에서 그대로
       돌린다. 증거 파일 넷을 기계로 새로 찍는다.
    ② **증거 성립** — 네 절 증거가 「HTTP 로 실제로 두드렸다」는 모양을 갖췄는가
       + `title_parts` 빈 칸 0(이 넷은 전부 이 턴의 것이므로 전부 강제한다).
    ③ **절 목록 전수** — 닫은 넷 + 「이 턴 배정에서 S 크기가 0 이었다」(DSM-U4
       잔여 넷)을 전부 찍는다.

종료 코드 (저장소 규약 · D-400)
    0 = 쟀고 통과(닫은 열 4/4)   1 = 쟀고 실패   2 = 못 쟀다 (회색)

    python scripts/verify_spec_dsm_u36.py                  # 판정(호스트 — docker 를 부른다)
    python scripts/verify_spec_dsm_u36.py --self-test        # 판정 규칙만
    python scripts/verify_spec_dsm_u36.py --no-run           # ②③만(pytest 를 다시 안 돌린다)
    python scripts/verify_spec_dsm_u36.py --shell gx-shell   # 컨테이너 이름을 바꿔 잰다

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
TESTS_REL: tuple[str, ...] = ("tests/test_dsm_u36_an.py",)
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"
SHELL_CONTAINER = "gx-shell"
TAG = "[SPEC-DSM-U36]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 닫은 넷 — P-356 넷(구현·증거·게이트·승격 제안)을 갖췄다고 이 차선이 주장하는 것.
CLOSED_CLAUSES: tuple[str, ...] = ("DSM-U3-01", "DSM-U3-02", "DSM-U6-01", "DSM-U6-03")

#: 명세 원문(90·91·123·125행) 제목 그대로. 판정에 안 쓴다 — 사람이 읽을 이름표일 뿐이다.
TITLES: dict[str, str] = {
    "DSM-U3-01": "역할별 M2 문안",
    "DSM-U3-02": "통제 실행 회신",
    "DSM-U6-01": "스마트시티 통합플랫폼 이벤트 연계(112·119·재난상황 긴급대응·CAP 1.2)",
    "DSM-U6-03": "사회적약자(실종) 요청 수신 → 객체 검색 사건 생성",
    "DSM-U4-02": "중간 보고 사이클",
    "DSM-U4-05": "일일상황보고 자동",
    "DSM-U4-08": "재난관리평가·감사 자료 묶음",
    "DSM-U4-09": "통계 축 추가 — 지역안전지수 6분야 유형 분류 열",
}

#: 못 닫은 넷 — **「무엇이 없는가」 한 줄**(P-358 형식). 빈 칸으로 두지 않는다(D-274).
#: 이 넷은 이 차선의 배정 조건("DSM-U4 잔여 중 S 크기") 자체가 **비어 있었다** —
#: 미포함표(`기능명세_미포함표_20260925.md` 98·103·106·107행) 실측: 넷 다 "M" 이지
#: "S" 가 아니다. 지어내지 않고 그대로 적는다.
NOT_STARTED: dict[str, str] = {
    "DSM-U4-02": "미포함표에서 크기 M 으로 판정돼 있다(S 아님) — 이 차선의 배정 조건"
                "(「DSM-U4-02·05·08·09 중 S 인 것」)에 해당하는 항목이 없다(실측: "
                "기능명세_미포함표_20260925.md 98행).",
    "DSM-U4-05": "위와 같음 — 크기 M(103행). 06:00 자동 배치·HWPX 출력이 필요한 M "
                "규모 절이라 이 차선의 「빠른 축」 범위 밖이다.",
    "DSM-U4-08": "위와 같음 — 크기 M(106행). K5 집계·ZIP 묶음이 필요한 M 규모 절.",
    "DSM-U4-09": "위와 같음 — 크기 M(107행). 지역안전지수 6분야 분류 매핑 표가 "
                "필요한 M 규모 절.",
}

REQUIRED_EVIDENCE_KEYS = ("id", "measured_at", "measured_by", "test", "request",
                         "response", "what")
REQUIRED_TITLE_PART_KEYS = ("part", "where", "status")
ALLOWED_PATH_PREFIXES = ("/api/dsm/",)


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
    """이 넷은 **전부 이 턴이 새로 붙였다** — `title_parts` 가 없으면(레거시 취급을
    안 한다) 그 자체가 빨강이다(F6 게이트와 다른 처지, U5-AN 게이트와 같은 처지)."""
    parts = payload.get("title_parts")
    if not isinstance(parts, list) or not parts:
        return EXIT_FAIL, "%s — title_parts 가 없거나 비었다(반쪽 승격)" % clause_id
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
    """이 절의 증거 한 건이 「HTTP 로 실제로 두드렸다」는 모양을 갖췄는가."""
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
    path = request.get("path") or ""
    if not any(path.startswith(p) for p in ALLOWED_PATH_PREFIXES):
        return (EXIT_FAIL,
                "%s — 요청 경로(%r)가 /api/dsm/ 가 아니다 — 다른 문을 잰 증거일 수 있다"
                % (clause_id, path))
    code, verdict = judge_title_parts(clause_id, payload)
    if code != EXIT_OK:
        return code, verdict
    return EXIT_OK, "%s — 증거 성립(2xx · %s %s · %s)" % (
        clause_id, request.get("method"), path, verdict)


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
             "-e", "DB_TEST_NAME=test_gx_verify_spec_dsm_u36",
             "-w", "/app", shell,
             "python", "-m", "pytest", *TESTS_REL,
             "-q", "--create-db", "-p", "no:randomly"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            #: ★ `guardianx-lane-count-ceilings` — 공유 gx-shell 은 다른 차선과
            #:   나뉜다. 10분 여유(`verify_spec_u5_an.py` 와 같은 값).
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

    code, _ = judge_gate_tests((14, 0, 0))
    check("① 전부 통과 → 초록", code == EXIT_OK)
    code, _ = judge_gate_tests((13, 1, 0))
    check("★ ① 1건 실패 → 빨강", code == EXIT_FAIL)
    code, _ = judge_gate_tests(None)
    check("① 요약을 못 읽으면 → 회색", code == EXIT_UNDECIDABLE)

    good = {
        "id": "DSM-U3-01", "measured_at": "2026-09-30T00:00:00+00:00",
        "measured_by": "django_test_client",
        "test": "tests.test_dsm_u36_an.X.y",
        "request": {"method": "GET", "path": "/api/dsm/events/1/m2-brief", "params": {}},
        "response": {"status": 200, "body": {}}, "what": "실측",
        "title_parts": [{"part": "역할×유형 문안 표", "where": "M2_PHRASE_TABLE",
                        "status": "measured"}],
    }
    code, _ = judge_evidence("DSM-U3-01", good)
    check("증거 성립 표본 → 초록", code == EXIT_OK)

    code, _ = judge_evidence("DSM-U3-01", None)
    check("증거 파일 없음 → 회색(못 쟀다)", code == EXIT_UNDECIDABLE)

    broken_status = dict(good, response={"status": 500, "body": {}})
    code, _ = judge_evidence("DSM-U3-01", broken_status)
    check("★★ 출생표본 — 응답 500 인 증거 → 빨강", code == EXIT_FAIL)

    broken_hand = dict(good, measured_by="hand")
    code, _ = judge_evidence("DSM-U3-01", broken_hand)
    check("★ measured_by=hand(손으로 적음) → 빨강", code == EXIT_FAIL)

    broken_path = dict(good, request={"method": "GET", "path": "/api/other/x",
                                      "params": {}})
    code, _ = judge_evidence("DSM-U3-01", broken_path)
    check("★ /api/dsm/ 가 아닌 경로 → 빨강", code == EXIT_FAIL)

    broken_id = dict(good, id="DSM-U3-99")
    code, _ = judge_evidence("DSM-U3-01", broken_id)
    check("파일 이름과 id 가 다르면 → 빨강", code == EXIT_FAIL)

    #: ★ 이 게이트는 F6 게이트와 달리 **title_parts 없음을 봐주지 않는다**(머리말).
    no_parts = {k: v for k, v in good.items() if k != "title_parts"}
    code, _ = judge_evidence("DSM-U3-01", no_parts)
    check("★★ title_parts 자체가 없으면(넷 다 새 것) → 빨강", code == EXIT_FAIL)

    empty_parts = dict(good, title_parts=[])
    code, _ = judge_evidence("DSM-U3-01", empty_parts)
    check("★★ title_parts 가 있는데 비었으면 → 빨강", code == EXIT_FAIL)

    blank_cell = dict(good, title_parts=[
        {"part": "역할×유형 문안 표", "where": "", "status": "measured"}])
    code, _ = judge_evidence("DSM-U3-01", blank_cell)
    check("★★ title_parts 안 빈 칸 하나 → 빨강", code == EXIT_FAIL)

    check("combine — 하나라도 빨강이면 빨강", combine([EXIT_OK, EXIT_FAIL]) == EXIT_FAIL)
    check("combine — 빨강 없고 회색 있으면 회색",
         combine([EXIT_OK, EXIT_UNDECIDABLE]) == EXIT_UNDECIDABLE)
    check("combine — 전부 초록이면 초록", combine([EXIT_OK, EXIT_OK]) == EXIT_OK)

    print("%s 자기시험 %d건 실패" % (TAG, fails))
    return EXIT_FAIL if fails else EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(
        description="DSM-U3-01·U3-02·U6-01·U6-03 별표 절 승격 게이트")
    ap.add_argument("--self-test", action="store_true")
    #: ★ 기본은 다시 안 돌린다(`verify_spec_u5_an.py` 와 같은 이유).
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
        missing_files = [t for t in TESTS_REL if not (BACKEND / t).exists()]
        if missing_files:
            print("%s **판정 불가 · 회색** — 길목 시험 파일이 없다: %s"
                 % (TAG, missing_files))
            return EXIT_UNDECIDABLE
        raw = run_gate_tests(args.shell)
        summary = parse_pytest_summary(raw) if raw is not None else None
        code1, verdict1 = judge_gate_tests(summary)
        codes.append(code1)
        print("%s [입력] 길목 시험 = %s (gx-shell=%s)" % (TAG, list(TESTS_REL), args.shell))
        if summary is not None:
            print("%s [입력] pytest 요약 — 통과 %d · 실패 %d · 에러 %d"
                 % (TAG, summary[0], summary[1], summary[2]))
        print("%s %s ① %s" % (TAG, "OK  " if code1 == EXIT_OK else
                              ("FAIL" if code1 == EXIT_FAIL else "GRAY"), verdict1))
        if code1 != EXIT_OK and raw:
            print("%s ── 길목 시험 원문 꼬리 ──\n%s" % (TAG, raw[-3000:]))

    # ② 절마다 증거 성립
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
             % (TAG, clause_id, TITLES.get(clause_id, clause_id), NOT_STARTED[clause_id]))

    final = combine(codes)
    ok_count = sum(1 for c in (codes[1:] if not args.no_run else codes) if c == EXIT_OK)
    print("%s ── 요약 — 닫은 열 %d/%d · 최종 %s ──"
         % (TAG, ok_count, len(CLOSED_CLAUSES),
            {EXIT_OK: "PASS", EXIT_FAIL: "FAIL", EXIT_UNDECIDABLE: "GRAY"}[final]))
    return final


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE

    gate_header(
        __file__,
        target="gx-shell 안 backend/ · apps.dsm.u36_an_service · apps.dsm.services · "
               "docs/agent/evidence/SPEC/*.json",
        as_="pytest 는 자격증명 없이 --create-db 로 돈다 · HTTP 실측은 "
            "tests/test_dsm_u36_an.py 안에서 실제 JWT 로 · 서명은 HMAC(웹훅 규약)",
        source="살아 있는 gx-shell 컨테이너(docker exec) · 그 실행이 새로 쓴 evidence 파일",
        measured="닫은 열 4건(DSM-U3-01·U3-02·U6-01·U6-03) · 못 닫은 열 4건은 이유 1줄"
                 "(DSM-U4-02·05·08·09 — 배정 조건인 S 크기가 이 넷 중 0건) · 분모 8",
    )
    sys.exit(main())
