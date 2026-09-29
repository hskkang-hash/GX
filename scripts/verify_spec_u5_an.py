#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-356·358·392 — FWS-U5-01~04·DSM-U5-01·03 별표 절 승격 게이트 (annex §5.7·§4.5 ·
턴 AN · WO-GX-20260929-17 · 차선 N4).

`scripts/verify_spec_fws_f6.py` 의 **판정식을 그대로 베낀다**(그 파일 머리말과
같은 이유 — D-212 를 어기지 않는다: 같은 규칙(P-356)을 재는 두 게이트가 서로를
import 하지 않고 판정 함수 모양만 같은 것은 DA-04 §1-1 과 같은 결). 다른 점은
길목 시험이 **둘**(FWS 하나·DSM 하나)이고, 증거 경로가 `/api/fws/` 뿐 아니라
`/api/dsm/` 도 허용해야 한다는 것뿐이다.

무엇을 재는가 — 셋
--------------------
    ① **길목** — `backend/tests/test_fws_u5.py`·`test_dsm_u5_an.py` 를 gx-shell
       안에서 그대로 돌린다. 둘 다 증거 파일을 기계로 새로 찍는다.
    ② **증거 성립** — 여섯 절 증거가 「HTTP 로 실제로 두드렸다」는 모양을 갖췄는가
       + `title_parts` 빈 칸 0(이 턴이 전건에 새로 붙였으므로 **여섯 다 강제**한다
       — F6 게이트가 레거시라 봐준 것과 다른 처지, 이 여섯은 전부 이 턴의 것이다).
    ③ **절 목록 전수** — 여섯(닫음) + 셋(못 닫음: FWS-U5-05·DSM-U5-04·O-03)을
       전부 찍는다.

종료 코드 (저장소 규약 · D-400)
    0 = 쟀고 통과(닫은 열 6/6)   1 = 쟀고 실패   2 = 못 쟀다 (회색)

    python scripts/verify_spec_u5_an.py                  # 판정(호스트 — docker 를 부른다)
    python scripts/verify_spec_u5_an.py --self-test        # 판정 규칙만
    python scripts/verify_spec_u5_an.py --no-run           # ②③만(pytest 를 다시 안 돌린다 · 빠르다)
    python scripts/verify_spec_u5_an.py --shell gx-shell   # 컨테이너 이름을 바꿔 잰다

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
TESTS_REL: tuple[str, ...] = ("tests/test_fws_u5.py", "tests/test_dsm_u5_an.py")
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"
SHELL_CONTAINER = "gx-shell"
TAG = "[SPEC-U5-AN]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 닫은 여섯 — P-356 넷(구현·증거·게이트·승격 제안)을 갖췄다고 이 차선이 주장하는 것.
CLOSED_CLAUSES: tuple[str, ...] = (
    "FWS-U5-01", "FWS-U5-02", "FWS-U5-03", "FWS-U5-04",
    "DSM-U5-01", "DSM-U5-03",
)

#: annex 원문(§5.7·§4.5) 제목 그대로. 판정에 안 쓴다 — 사람이 읽을 이름표일 뿐이다.
TITLES: dict[str, str] = {
    "FWS-U5-01": "산불 감시 카메라 등록(고지대·PTZ 프리셋·열화상 채널·감시 반경 폴리곤)",
    "FWS-U5-02": "초소·순찰함(NFC)·순찰 구역",
    "FWS-U5-03": "마을·대피소·요양시설 등록(대피 대상 자동 산출)",
    "FWS-U5-04": "산불 알림 규칙(등급별 수신: 진화대·산림과·지휘·산림청) · 야간 "
                "5분대기조 채널",
    "DSM-U5-01": "운영·관리 방침 항목 관리",
    "DSM-U5-03": "연계 설정 — 스마트시티 통합플랫폼·112·119·NDMS",
    "DSM-U5-04": "임계값 소스 등록 — 하천 수위계·강우량계(API/수동) · 통제 기준값(지점별)",
    "FWS-U5-05": "오탐 필터 모델 활성(안개·소각 시간대·계절)",
    "O-03": "라이선스·계량·청구",
}

#: 못 닫은 셋 — **「무엇이 없는가」 한 줄**(P-358 형식). 빈 칸으로 두지 않는다(D-274).
NOT_STARTED: dict[str, str] = {
    "FWS-U5-05": "오탐 필터 모델 활성(안개·소각 시간대·계절) — AI 판별 모델이 이 "
                "저장소 어디에도 없다(모델 학습·추론 파이프라인은 L 규모 · 대표 "
                "승인이 필요한 별도 사업). 이번 차선이 지을 수 있는 것은 설정 값을 "
                "받는 빈 칸뿐이고, 그 값을 실제로 걸러내는 판정기가 없는 빈 칸은 "
                "「저장은 되는데 아무 일도 안 하는 스위치」라 annex 완결조건을 "
                "충족하지 못한다 — 지어내지 않고 범위 밖으로 남긴다.",
    "DSM-U5-04": "임계값 소스 등록(하천 수위계·강우량계) — 이 절은 차선 배정표에 "
                "없다(WO-17 지시서가 이 차선에 맡긴 것은 U5-01·U5-03 둘뿐이다). "
                "임계값 소스는 `kernels.k5_trust` 의 기존 표(K5 표 ①)와 맞물린 "
                "차선 배정 밖 절이라 이번 차선이 손대지 않는다.",
    "O-03": "라이선스·계량·청구 — 청구 체계(단가·정산 주기·인보이스)는 사업 "
           "결정(가격 정책)이 먼저 서야 하는 L 규모 절이고, 이 차선의 두 앱(U5-01·"
           "U5-03) 범위와 무관하다 — 지어내지 않고 범위 밖으로 남긴다.",
}

REQUIRED_EVIDENCE_KEYS = ("id", "measured_at", "measured_by", "test", "request",
                         "response", "what")
REQUIRED_TITLE_PART_KEYS = ("part", "where", "status")
#: 이 여섯은 `/api/fws/` 아니면 `/api/dsm/` 아래에서만 실측된다.
ALLOWED_PATH_PREFIXES = ("/api/fws/", "/api/dsm/")


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
    """이 여섯은 **전부 이 턴이 새로 붙였다** — `title_parts` 가 없으면(레거시
    취급을 안 한다) 그 자체가 빨강이다(F6 게이트와 다른 처지 · 머리말 참고)."""
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
                "%s — 요청 경로(%r)가 /api/fws/ 도 /api/dsm/ 도 아니다 — 다른 문을 "
                "잰 증거일 수 있다" % (clause_id, path))
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
             "-e", "DB_TEST_NAME=test_gx_verify_spec_u5_an",
             "-w", "/app", shell,
             "python", "-m", "pytest", *TESTS_REL,
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

    good_fws = {
        "id": "FWS-U5-02", "measured_at": "2026-09-29T00:00:00+00:00",
        "measured_by": "django_test_client", "test": "tests.test_fws_u5.X.y",
        "request": {"method": "POST", "path": "/api/fws/admin/posts", "params": {}},
        "response": {"status": 200, "body": {}}, "what": "실측",
        "title_parts": [{"part": "초소", "where": "post_code", "status": "measured"}],
    }
    code, _ = judge_evidence("FWS-U5-02", good_fws)
    check("증거 성립 표본(FWS 경로) → 초록", code == EXIT_OK)

    good_dsm = dict(good_fws, id="DSM-U5-03",
                    request={"method": "GET", "path": "/api/dsm/u5an/integrations",
                            "params": {}})
    code, _ = judge_evidence("DSM-U5-03", good_dsm)
    check("증거 성립 표본(DSM 경로) → 초록", code == EXIT_OK)

    code, _ = judge_evidence("FWS-U5-02", None)
    check("증거 파일 없음 → 회색(못 쟀다)", code == EXIT_UNDECIDABLE)

    broken_status = dict(good_fws, response={"status": 500, "body": {}})
    code, _ = judge_evidence("FWS-U5-02", broken_status)
    check("★★ 출생표본 — 응답 500 인 증거 → 빨강", code == EXIT_FAIL)

    broken_hand = dict(good_fws, measured_by="hand")
    code, _ = judge_evidence("FWS-U5-02", broken_hand)
    check("★ measured_by=hand(손으로 적음) → 빨강", code == EXIT_FAIL)

    broken_path = dict(good_fws, request={"method": "POST", "path": "/api/other/x",
                                          "params": {}})
    code, _ = judge_evidence("FWS-U5-02", broken_path)
    check("★ /api/fws/ 도 /api/dsm/ 도 아닌 경로 → 빨강", code == EXIT_FAIL)

    broken_id = dict(good_fws, id="FWS-U5-99")
    code, _ = judge_evidence("FWS-U5-02", broken_id)
    check("파일 이름과 id 가 다르면 → 빨강", code == EXIT_FAIL)

    #: ★ 이 게이트는 F6 게이트와 달리 **title_parts 없음을 봐주지 않는다**(머리말).
    no_parts = {k: v for k, v in good_fws.items() if k != "title_parts"}
    code, _ = judge_evidence("FWS-U5-02", no_parts)
    check("★★ title_parts 자체가 없으면(이 여섯은 전부 새 것) → 빨강", code == EXIT_FAIL)

    empty_parts = dict(good_fws, title_parts=[])
    code, _ = judge_evidence("FWS-U5-02", empty_parts)
    check("★★ title_parts 가 있는데 비었으면 → 빨강", code == EXIT_FAIL)

    blank_cell = dict(good_fws, title_parts=[
        {"part": "초소", "where": "", "status": "measured"}])
    code, _ = judge_evidence("FWS-U5-02", blank_cell)
    check("★★ title_parts 안 빈 칸 하나 → 빨강", code == EXIT_FAIL)

    check("combine — 하나라도 빨강이면 빨강", combine([EXIT_OK, EXIT_FAIL]) == EXIT_FAIL)
    check("combine — 빨강 없고 회색 있으면 회색",
         combine([EXIT_OK, EXIT_UNDECIDABLE]) == EXIT_UNDECIDABLE)
    check("combine — 전부 초록이면 초록", combine([EXIT_OK, EXIT_OK]) == EXIT_OK)

    print("%s 자기시험 %d건 실패" % (TAG, fails))
    return EXIT_FAIL if fails else EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="FWS-U5-01~04·DSM-U5-01·03 별표 절 승격 게이트")
    ap.add_argument("--self-test", action="store_true")
    #: ★ 기본은 다시 안 돌린다(`verify_spec_fws_f6.py` 와 같은 이유).
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
        target="gx-shell 안 backend/ · apps.fws.admin_settings · apps.dsm.u5_an_service · "
               "docs/agent/evidence/SPEC/*.json",
        as_="pytest 는 자격증명 없이 --create-db 로 돈다 · HTTP 실측은 tests/test_fws_u5.py · "
            "tests/test_dsm_u5_an.py 안에서 실제 JWT 로",
        source="살아 있는 gx-shell 컨테이너(docker exec) · 그 실행이 새로 쓴 evidence 파일",
        measured="닫은 열 6건(FWS-U5-01~04 · DSM-U5-01·03) · 못 닫은 열 3건은 이유 1줄"
                 "(FWS-U5-05 · DSM-U5-04 · O-03) · 분모 9",
    )
    sys.exit(main())
