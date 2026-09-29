#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-356·357·397 — FWS-F3-01~09 별표 절 승격 게이트(산림과 담당 앞 절 아홉 ·
annex §5.3 · 턴 AN 차선 N2).

`scripts/verify_spec_fws_f6.py` 의 **판정식을 그대로 베낀다**(D-212 를 어기지
않는다 — 그 파일은 F6 만 게이트하고, 이 파일은 F3-01~09 만 게이트한다. 판정
함수의 모양이 같은 것은 같은 규칙(P-356)을 재는 것이므로 같은 것이다).

무엇을 재는가 — 셋
--------------------
    ① **길목** — `backend/tests/test_fws_f3a.py` 를 gx-shell 안에서 그대로
       돌린다. 그 시험은 도는 김에 `docs/agent/evidence/SPEC/<id>.json` 을
       **기계로** 새로 찍는다.
    ② **증거 성립** — 방금 찍힌 증거 파일 9건이 「HTTP 로 실제로 두드렸다」는
       모양을 갖췄는가 — **더해 `title_parts`(빈 칸 0)** 까지 갖췄는가(`_규약.md`
       요구 · O 게이트가 이 칸을 다시 센다).
    ③ **절 목록 전수** — FWS-F3-01~09 아홉을 전부 찍는다(N2 몫 · F3-10~20 은
       차선 N3 의 `verify_spec_fws_f3b.py` — 이 파일이 아니다).

종료 코드 (저장소 규약 · D-400)
    0 = 쟀고 통과(닫은 아홉 9/9)   1 = 쟀고 실패   2 = 못 쟀다 (회색)

    python scripts/verify_spec_fws_f3.py                  # 판정 (호스트 — docker 를 부른다)
    python scripts/verify_spec_fws_f3.py --self-test        # 판정 규칙만
    python scripts/verify_spec_fws_f3.py --no-run           # ②③만(pytest 를 다시 안 돌린다 · 빠르다)
    python scripts/verify_spec_fws_f3.py --shell gx-shell   # 컨테이너 이름을 바꿔 잰다

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
TESTS_REL = "tests/test_fws_f3a.py"
TESTS = BACKEND / TESTS_REL
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"
SHELL_CONTAINER = "gx-shell"
TAG = "[SPEC-FWS-F3]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 닫은 아홉 — F3-01~09 전부(이 차선의 목표 ≥7 을 넘긴다). F3-10~20 은 차선 N3
#: 소유(`api_office2.py`·`office2.py`)라 이 파일이 재지 않는다.
CLOSED_CLAUSES: tuple[str, ...] = (
    "FWS-F3-01", "FWS-F3-02", "FWS-F3-03", "FWS-F3-04", "FWS-F3-05",
    "FWS-F3-06", "FWS-F3-07", "FWS-F3-08", "FWS-F3-09",
)

#: annex 원문(§5.3 표) 제목 — 판정에는 안 쓴다(판정은 evidence 파일이 한다) ·
#: 화면에 사람이 읽을 이름을 대는 용도다.
TITLES: dict[str, str] = {
    "FWS-F3-01": "산불 상황판 — 위험지수·위기경보·초소 근무·카메라 정상·진행 "
                "사건·자원 대기",
    "FWS-F3-02": "조심기간·특별대책기간 설정 · 초소·순찰 구역 등록",
    "FWS-F3-03": "인력 배치 — 감시원·대응단 근무표(CSV) · 야간 5분대기조",
    "FWS-F3-04": "탐지 확인 요청 1클릭 — 카드에서 가장 가까운 감시원/드론에 "
                "확인 요청 · 10분 시계",
    "FWS-F3-05": "오인 종결(사유) · 산불 확정",
    "FWS-F3-06": "신고 접수 기록 — 119/산림청/시민 신고 접수 항목(시간·장소·"
                "시설·차량 진입·화세) · 신고 시각 = 30분 시계 시작",
    "FWS-F3-07": "산림청 상황실 통보 기록(042-481-4119) · 헬기 요청 기록"
                "(요청 시각·기지·도착 예정)",
    "FWS-F3-08": "자원 배정 — 진화대·차량·드론을 사건에 배정(임무 문안 자동)",
    "FWS-F3-09": "대응단계 입력 3칸(면적·풍속·시설 우려) → 단계 제안 → "
                "F4 확정 요청",
}

#: 못 닫은 것 — 지금은 없다(9/9). 그래도 자리를 비워 두지 않는다(D-274 형식
#: 유지 — F6 게이트와 같은 모양).
NOT_STARTED: dict[str, str] = {}

REQUIRED_EVIDENCE_KEYS = ("id", "measured_at", "measured_by", "test", "request",
                         "response", "what", "title_parts")


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


def _judge_title_parts(clause_id: str, parts) -> str | None:
    """`title_parts` 가 「빈 칸 0」인가 — 배열이 없거나·비었거나·칸이 비면 사유를
    낸다(없으면 `None`)."""
    if not isinstance(parts, list) or not parts:
        return "title_parts 가 없거나 비었다"
    for i, part in enumerate(parts):
        if not isinstance(part, dict):
            return f"title_parts[{i}] 가 객체가 아니다"
        blanks = [k for k in ("part", "where", "status") if not (part.get(k) or "").strip()]
        if blanks:
            return f"title_parts[{i}] 에 빈 칸: {blanks}"
    return None


def judge_evidence(clause_id: str, payload: dict | None) -> tuple[int, str]:
    """이 절의 증거 한 건이 「HTTP 로 실제로 두드렸다 · title_parts 빈 칸 0」
    이라는 모양을 갖췄는가.

    ⚠ **자기시험이 이 함수를 몸소 망가뜨려 본다** — 「없으면 넘긴다」로 흐리면
      머리글 규약(P-319)이 요구하는 짝이 성립하지 않는다.
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
    if not (request.get("path") or "").startswith("/api/fws/"):
        return (EXIT_FAIL,
                "%s — 요청 경로(%r)가 /api/fws/ 가 아니다 — 다른 문을 잰 증거일 수 있다"
                % (clause_id, request.get("path")))
    parts_problem = _judge_title_parts(clause_id, payload.get("title_parts"))
    if parts_problem:
        return EXIT_FAIL, "%s — %s" % (clause_id, parts_problem)
    return EXIT_OK, "%s — 증거 성립(2xx · %s %s · title_parts %d칸)" % (
        clause_id, request.get("method"), request.get("path"),
        len(payload.get("title_parts") or []))


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
             "-e", "DB_TEST_NAME=test_gx_verify_spec_fws_f3",
             "-w", "/app", shell,
             "python", "-m", "pytest", TESTS_REL,
             "-q", "--create-db", "-p", "no:randomly"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            #: ★ `guardianx-lane-count-ceilings` — 공유 gx-shell 은 다른 차선과
            #:   나뉜다. 10분 여유(`verify_spec_fws_f6.py` 와 같은 값).
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

    code, _ = judge_gate_tests((22, 0, 0))
    check("① 전부 통과 → 초록", code == EXIT_OK)
    code, _ = judge_gate_tests((21, 1, 0))
    check("★ ① 1건 실패 → 빨강", code == EXIT_FAIL)
    code, _ = judge_gate_tests(None)
    check("① 요약을 못 읽으면 → 회색", code == EXIT_UNDECIDABLE)

    good = {
        "id": "FWS-F3-01", "measured_at": "2026-09-29T00:00:00+00:00",
        "measured_by": "django_test_client", "test": "tests.test_fws_f3a.X.y",
        "request": {"method": "GET", "path": "/api/fws/office/dashboard", "params": {}},
        "response": {"status": 200, "body": {}}, "what": "실측",
        "title_parts": [{"part": "위험지수", "where": "response.risk_index", "status": "present"}],
    }
    code, _ = judge_evidence("FWS-F3-01", good)
    check("증거 성립 표본 → 초록", code == EXIT_OK)

    code, _ = judge_evidence("FWS-F3-01", None)
    check("증거 파일 없음 → 회색(못 쟀다)", code == EXIT_UNDECIDABLE)

    broken_status = dict(good, response={"status": 500, "body": {}})
    code, _ = judge_evidence("FWS-F3-01", broken_status)
    check("★★ 출생표본 — 응답 500 인 증거 → 빨강(성공을 가장한 실패를 못 잡으면 "
         "이 게이트는 없느니만 못하다)", code == EXIT_FAIL)

    broken_hand = dict(good, measured_by="hand")
    code, _ = judge_evidence("FWS-F3-01", broken_hand)
    check("★ measured_by=hand(손으로 적음) → 빨강", code == EXIT_FAIL)

    broken_path = dict(good, request={"method": "GET", "path": "/api/dsm/x", "params": {}})
    code, _ = judge_evidence("FWS-F3-01", broken_path)
    check("★ 다른 App 경로를 잰 증거 → 빨강", code == EXIT_FAIL)

    broken_id = dict(good, id="FWS-F3-99")
    code, _ = judge_evidence("FWS-F3-01", broken_id)
    check("파일 이름과 id 가 다르면 → 빨강", code == EXIT_FAIL)

    broken_no_parts = dict(good, title_parts=[])
    code, _ = judge_evidence("FWS-F3-01", broken_no_parts)
    check("★ title_parts 가 비어 있으면 → 빨강(빈 칸 0 위반)", code == EXIT_FAIL)

    broken_blank_part = dict(good, title_parts=[{"part": "위험지수", "where": "", "status": "present"}])
    code, _ = judge_evidence("FWS-F3-01", broken_blank_part)
    check("★ title_parts 안에 빈 칸이 있으면 → 빨강", code == EXIT_FAIL)

    check("combine — 하나라도 빨강이면 빨강", combine([EXIT_OK, EXIT_FAIL]) == EXIT_FAIL)
    check("combine — 빨강 없고 회색 있으면 회색",
         combine([EXIT_OK, EXIT_UNDECIDABLE]) == EXIT_UNDECIDABLE)
    check("combine — 전부 초록이면 초록", combine([EXIT_OK, EXIT_OK]) == EXIT_OK)

    print("%s 자기시험 %d건 실패" % (TAG, fails))
    return EXIT_FAIL if fails else EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="FWS-F3-01~09 별표 절 승격 게이트")
    ap.add_argument("--self-test", action="store_true")
    #: ★ 기본은 다시 안 돌린다(`verify_spec_fws_f6.py` 와 같은 이유 — 시험이
    #:   증거 파일을 새 시각으로 덮어써서 측정 재현성이 깨진다). 시험을 다시
    #:   돌려 증거를 새로 찍는 것은 `--run`(손 · 창 ③)이다.
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
        if not TESTS.exists():
            print("%s **판정 불가 · 회색** — 길목 시험 파일이 없다: %s" % (TAG, TESTS_REL))
            return EXIT_UNDECIDABLE
        raw = run_gate_tests(args.shell)
        summary = parse_pytest_summary(raw) if raw is not None else None
        code1, verdict1 = judge_gate_tests(summary)
        codes.append(code1)
        print("%s [입력] 길목 시험 = %s (gx-shell=%s)" % (TAG, TESTS_REL, args.shell))
        if summary is not None:
            print("%s [입력] pytest 요약 — 통과 %d · 실패 %d · 에러 %d"
                 % (TAG, summary[0], summary[1], summary[2]))
        print("%s %s ① %s" % (TAG, "OK  " if code1 == EXIT_OK else
                              ("FAIL" if code1 == EXIT_FAIL else "GRAY"), verdict1))
        if code1 != EXIT_OK and raw:
            print("%s ── 길목 시험 원문 꼬리 ──\n%s" % (TAG, raw[-3000:]))

    # ② 절마다 증거 성립
    print("%s ── 절별 판정 (닫은 아홉 %d · 못 닫은 것 %d) ──"
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
    print("%s ── 요약 — 닫은 열 %d/%d · 최종 %s ──"
         % (TAG, sum(1 for c in codes[1:] if c == EXIT_OK) if not args.no_run
            else sum(1 for c in codes if c == EXIT_OK),
            len(CLOSED_CLAUSES),
            {EXIT_OK: "PASS", EXIT_FAIL: "FAIL", EXIT_UNDECIDABLE: "GRAY"}[final]))
    return final


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE

    gate_header(
        __file__,
        target="gx-shell(%s) 안 backend/ · apps.fws.{office,api_office}(신규) · "
              "K1·K2 커널 재사용 · docs/agent/evidence/SPEC/*.json" % SHELL_CONTAINER,
        as_="pytest 는 자격증명 없이 --create-db 로 돈다 · HTTP 실측은 "
            "tests/test_fws_f3a.py 안에서 실제 JWT(RefreshToken.for_user)로",
        source="살아 있는 gx-shell 컨테이너(docker exec) · 그 실행이 방금 새로 쓴 "
              "evidence 파일 — 사진·손으로 옮긴 값이 아니라 이번 실행",
        measured="닫은 아홉 건(FWS-F3-01~09) · 못 닫은 것 0건 · 분모 9",
    )
    raise SystemExit(main())
