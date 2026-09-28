#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-356·P-376 — OPS annex O-10(키·자격 회전)·O-04(모델 레지스트리) 승격 게이트.
차선 O · 턴 AM. `scripts/verify_spec_fws.py` 의 구조를 그대로 베낀다(D-212 —
판정 모양은 한 곳에서 정한다. 분모가 다를 뿐 셋·짝·자기시험은 같다).

무엇을 재는가 — 셋 (FWS 게이트와 같다)
----------------------------------------
    ① **길목** — `backend/tests/test_p356_ops_spec_promotions.py` 를 gx-shell
       안에서 그대로 돈다. `--run` 일 때만(기본은 안 돈다 — 아래 참조).
    ② **증거 성립** — `docs/agent/evidence/SPEC/<id>.json` 이 「HTTP 로 실제로
       두드렸다」는 모양을 갖췄는가.
    ③ **절 목록 전수** — O-10·O-04 둘을 전부 찍는다.

★ 이번 턴의 실측 — **닫은 열 0 / 2** (P-376 이 요구하는 정직한 결론)
----------------------------------------------------------------------
`CLOSED_CLAUSES` 가 비어 있다. O-10·O-04 는 조사 결과 둘 다 annex 가 이름 대는
것 중 **실제 HTTP 엔드포인트로 여는 부분이 없다**(O-04 는 저장처 자체가 없고,
O-10 은 조각(API 키 회전·웹훅 서명키·DB 공유 비밀번호 회전)은 있지만 완결 조건의
AND 절반(「게이트 계정 로그인 4/4」)이 **이 환경에서 구조적으로 재현 불가** —
라이브 서버 로그인은 이 저장소 차선 공통 규칙이 금지한다). `NOT_STARTED` 의 각 줄이
「무엇이 없는가」를 적는다 — 빈 칸으로 두지 않는다(D-274).

CLOSED_CLAUSES 가 비어도 이 게이트가 **PASS(0)를 낼 수 있다** — 그 뜻은 "annex
전체가 됐다"가 아니라 "이 차선이 닫았다고 주장하는 것(0건)은 전부 정직하게
증명됐다"이다(FWS 게이트가 25/40 을 PASS 로 내는 것과 같은 셈법). 아래 「요약」
줄이 분모(2)와 분자(0)를 함께 낸다 — 착시를 막는다(D-271).

무엇을 하지 않는가
------------------
대장(`ga_readiness.yaml`) 이동은 이 게이트의 일이 아니다 — 조율자가 한다.

종료 코드 (저장소 규약 · D-400)
    0 = 쟀고 통과(닫은 열 0/2 — 전부 정직하게 「없다」로 찍혔다)   1 = 쟀고 실패
    2 = 못 쟀다 (회색)

    python scripts/verify_spec_ops.py                  # 판정 (기본 — pytest 재실행 없음)
    python scripts/verify_spec_ops.py --self-test        # 판정 규칙만
    python scripts/verify_spec_ops.py --run               # 길목 시험을 다시 돌린다(손으로만)
    python scripts/verify_spec_ops.py --shell gx-shell   # 컨테이너 이름을 바꿔 잰다

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
TESTS_REL = "tests/test_p356_ops_spec_promotions.py"
TESTS = BACKEND / TESTS_REL
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"
SHELL_CONTAINER = "gx-shell"
TAG = "[SPEC-OPS]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 닫은 열 — **이번 턴은 비어 있다.** O-10·O-04 둘 다 P-356 넷(실제 엔드포인트 ·
#: 증거 · 게이트 · 승격 제안)을 갖추지 못했다(`docs/agent/evidence/SPEC/O_promotions.md`
#: 참조). 앞으로 누가 정말 닫으면 그 절 id 를 여기 올리고 `NOT_STARTED` 에서 뺀다.
CLOSED_CLAUSES: tuple[str, ...] = ()

#: annex 원문(플랫폼 구조설계서 §7) 제목 — 판정에는 안 쓴다(사람이 읽을 이름표).
TITLES: dict[str, str] = {
    "O-10": "키·자격 회전 — API 키 · 서명키 · DB/MinIO 자격 · VAPID · 회전 주기 · "
           "재생성 창 runbook",
    "O-04": "모델 레지스트리 — 모델 버전·앱 태그·테넌트 배포·롤백 · 카메라별 바인딩 "
           "현황 · 성능(오탐률)",
}

#: 못 닫은 둘 — **「무엇이 없는가」**(P-358·P-376 형식). 빈 칸으로 두지 않는다(D-274).
NOT_STARTED: dict[str, str] = {
    "O-10": "완결 조건은 AND 다(「회전 뒤 게이트 계정 로그인 4/4 · 옛 키 401」). "
           "뒤 반(옛 키 401)은 이미 있는 door(`kernels.k5_trust.inbound_keys."
           "rotate_key` · 들어오는 키(inbound_api_key) 회전 문)로 "
           "Django test client 실측이 가능하지만, 앞 반(게이트 계정이 회전 뒤에도 "
           "로그인된다)은 **이 환경에서 구조적으로 못 잰다** — "
           "`scripts/rotate_shared_passwords.py` 는 게이트 계정을 일부러 회전하지 "
           "않고(`NEVER_TOUCH`), 게이트 계정 자신의 자격을 바꾸고 실제 서버에 "
           "로그인해 보는 것은 이 저장소 차선 공통 규칙이 금지한 행위다(라이브 "
           "서버 로그인 금지). 조각(API 키 회전·웹훅 서명키 생성 "
           "`webhook_signing_keys.py`·DB 공유 비밀번호 회전·표 ②"
           "(`credentials.py`, 나가는 API 키 셋만))은 있지만 **하나의 O-10 "
           "콘솔/엔드포인트로 통합된 곳이 없고**, VAPID·DB/MinIO 자격은 표 ②에 "
           "아예 없다(`apps/dsm/notify_prefs.py` 에 따로 있다). "
           "`tests/test_p356_ops_spec_promotions.py::KeyRotationCoverageTest` 가 "
           "이 흩어짐과 구조적 한계를 실측으로 고정한다.",
    "O-04": "모델 버전·테넌트 배포·롤백·카메라별 바인딩을 담을 저장처가 전혀 없다"
           "(전수 grep 0건 — `ModelVersion`·`ModelRegistry`·`ModelDeployment`·"
           "`ModelBinding` 류 이름 0). 가장 가까운 기존 값(`kernels.k6_feedback."
           "false_positive_rate`)은 판정자·카메라별 오탐률일 뿐 AI 모델 버전과 "
           "엮이지 않는다 — 「배포 → 테넌트 오탐률 추세」를 이을 축이 없다. "
           "L~XL 규모(새 저장처 + 배포/롤백 상태기계 + 카메라 바인딩 + 추세 집계) "
           "라 이번 차선(P-376 이 요구하는 정직성 · 시간 상자 2.5h) 안에 못 붙였다. "
           "`tests/test_p356_ops_spec_promotions.py::ModelRegistryAbsenceTest` 가 "
           "이 부재를 실측으로 고정한다.",
}

REQUIRED_EVIDENCE_KEYS = ("id", "measured_at", "measured_by", "test", "request",
                         "response", "what")


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


def judge_evidence(clause_id: str, payload: dict | None) -> tuple[int, str]:
    """이 절의 증거 한 건이 「HTTP 로 실제로 두드렸다」는 모양을 갖췄는가.

    ★ `verify_spec_fws.py::judge_evidence` 와 판정식이 같다 — 경로 접두어만
      `/api/ops/` 로 바꿨다(OPS 앱이 서는 날을 위한 자리 — 아직 아무 절도 이
      경로를 쓰지 않는다, `CLOSED_CLAUSES` 가 비어 있는 것이 그 증거다).
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
    if not (request.get("path") or "").startswith("/api/ops/"):
        return (EXIT_FAIL,
                "%s — 요청 경로(%r)가 /api/ops/ 가 아니다 — 다른 문을 잰 증거일 수 있다"
                % (clause_id, request.get("path")))
    return EXIT_OK, "%s — 증거 성립(2xx · %s %s)" % (
        clause_id, request.get("method"), request.get("path"))


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
             "-e", "DB_TEST_NAME=test_gx_verify_spec_ops",
             "-w", "/app", shell,
             "python", "-m", "pytest", TESTS_REL,
             "-q", "--create-db", "-p", "no:randomly"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            #: ★ `guardianx-lane-count-ceilings` — 공유 gx-shell 은 다른 차선과
            #:   나뉜다. 10분 여유(`verify_spec_fws.py` 와 같은 값).
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

    code, _ = judge_gate_tests((6, 0, 0))
    check("① 전부 통과 → 초록", code == EXIT_OK)
    code, _ = judge_gate_tests((5, 1, 0))
    check("★ ① 1건 실패 → 빨강", code == EXIT_FAIL)
    code, _ = judge_gate_tests(None)
    check("① 요약을 못 읽으면 → 회색", code == EXIT_UNDECIDABLE)

    good = {
        "id": "O-10", "measured_at": "2026-09-28T00:00:00+00:00",
        "measured_by": "django_test_client", "test": "tests.test_p356_ops_spec_promotions.X.y",
        "request": {"method": "POST", "path": "/api/ops/keys/rotate", "body": {}},
        "response": {"status": 200, "body": {}}, "what": "실측",
    }
    code, _ = judge_evidence("O-10", good)
    check("증거 성립 표본 → 초록", code == EXIT_OK)

    code, _ = judge_evidence("O-10", None)
    check("증거 파일 없음 → 회색(못 쟀다)", code == EXIT_UNDECIDABLE)

    broken_status = dict(good, response={"status": 500, "body": {}})
    code, _ = judge_evidence("O-10", broken_status)
    check("★★ 출생표본 — 응답 500 인 증거 → 빨강(성공을 가장한 실패를 못 잡으면 "
         "이 게이트는 없느니만 못하다)", code == EXIT_FAIL)

    broken_hand = dict(good, measured_by="hand")
    code, _ = judge_evidence("O-10", broken_hand)
    check("★ measured_by=hand(손으로 적음) → 빨강", code == EXIT_FAIL)

    broken_path = dict(good, request={"method": "POST", "path": "/api/dsm/x", "body": {}})
    code, _ = judge_evidence("O-10", broken_path)
    check("★ 다른 App 경로를 잰 증거 → 빨강", code == EXIT_FAIL)

    broken_id = dict(good, id="O-99")
    code, _ = judge_evidence("O-10", broken_id)
    check("파일 이름과 id 가 다르면 → 빨강", code == EXIT_FAIL)

    check("combine — 하나라도 빨강이면 빨강", combine([EXIT_OK, EXIT_FAIL]) == EXIT_FAIL)
    check("combine — 빨강 없고 회색 있으면 회색",
         combine([EXIT_OK, EXIT_UNDECIDABLE]) == EXIT_UNDECIDABLE)
    check("combine — 전부 초록이면 초록", combine([EXIT_OK, EXIT_OK]) == EXIT_OK)
    check("★ combine — 빈 목록(닫은 열 0건)도 초록 — 「아무것도 없다」와 「거짓말을 "
         "안 했다」는 다르다", combine([]) == EXIT_OK)

    print("%s 자기시험 %d건 실패" % (TAG, fails))
    return EXIT_FAIL if fails else EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="OPS O-10·O-04 별표 절 승격 게이트")
    ap.add_argument("--self-test", action="store_true")
    #: [P-376 · 차선 O] **기본은 다시 안 돌린다** — `verify_spec_fws.py` 와 같은 이유
    #:   (증거 시각이 매번 바뀌면 측정 재현성이 깨진다). `--run` 이 pytest 를 다시 돌린다.
    ap.add_argument("--run", action="store_true",
                   help="pytest 를 다시 돌려 evidence 를 새로 찍는다(손으로만)")
    ap.add_argument("--no-run", action="store_true",
                   help="pytest 를 다시 안 돌린다 — 지금 있는 evidence 파일만 본다(기본)")
    ap.add_argument("--shell", default=SHELL_CONTAINER)
    args = ap.parse_args()
    args.no_run = args.no_run or not args.run

    if args.self_test:
        return self_test()

    codes: list[int] = []

    if args.no_run:
        print("%s [입력] --no-run(기본) — pytest 를 다시 안 돌린다(지금 있는 evidence "
             "파일만 · 이번 턴은 닫은 열 0건이라 볼 파일도 없다)" % TAG)
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

    # ② 절마다 증거 성립 (닫은 열이 있을 때만 — 지금은 0)
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
    closed_n = sum(1 for c in codes if c == EXIT_OK) if args.no_run else \
        sum(1 for c in codes[1:] if c == EXIT_OK)
    print("%s ── 요약 — 닫은 열 %d/%d(분모 = annex 배정 2건) · 최종 %s ──"
         % (TAG, closed_n, len(CLOSED_CLAUSES) + len(NOT_STARTED),
            {EXIT_OK: "PASS", EXIT_FAIL: "FAIL", EXIT_UNDECIDABLE: "GRAY"}[final]))
    return final


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE

    gate_header(
        __file__,
        target="gx-shell(%s) 안 backend/tests/test_p356_ops_spec_promotions.py · "
               "kernels.k5_trust(inbound_keys·webhook_signing_keys·credentials) · "
               "scripts/rotate_shared_passwords.py · docs/agent/evidence/SPEC/*.json"
               % SHELL_CONTAINER,
        as_="pytest 는 자격증명 없이 --create-db 로 돈다 · 라이브 서버 로그인은 이번 "
            "게이트가 하지 않는다(차선 공통 규칙 금지) — O-10 완결 조건의 그 반쪽이 "
            "바로 이 이유로 못 닫힌다",
        source="살아 있는 gx-shell 컨테이너(docker exec, `--run` 일 때만) · 정적으로는 "
              "저장소의 kernels·scripts 소스 그 자체(전수 grep — 사진·손으로 옮긴 값 "
              "아님)",
        measured="닫은 열 0건 · 못 닫은 열 2건(O-10·O-04) — 분모 2, "
                "`docs/agent/evidence/SPEC/O_promotions.md` 의 「무엇이 없는가」 표와 "
                "일치",
    )
    raise SystemExit(main())
