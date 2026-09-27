#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-356·358 — DSM-U2-03·U2-04·U2-05 별표 절 승격 게이트 (WO-GX-20260925-15 §5 · 턴 AK 차선 N1).

무엇을 재는가 — 셋(`scripts/verify_spec_fws.py` 와 같은 그림 · 차선 N2 가 이번 턴
같은 승격 규칙으로 먼저 세운 짝이다 — 두 게이트가 다른 모양이면 다음 사람이 파일마다
다른 눈으로 읽어야 한다)
--------------------------------------------------------------------------------
    ① **길목** — `backend/tests/test_p356_u2_spec_promotions.py` 를 gx-shell 안에서
       **그대로** 돌린다. 판정 규칙(응답 모양·상태 코드·격리)은 그 시험이 이미 정했다 —
       이 게이트가 다시 만들지 않는다(D-212). 그 시험은 도는 김에
       `docs/agent/evidence/SPEC/<id>.json` 을 **기계로** 새로 찍는다
       (`EvidenceExportTest`).
    ② **증거 성립** — 방금 찍힌 증거 파일 3건이 「HTTP 로 실제로 두드렸다」는 모양
       (요청·2xx 응답·무엇을 쟀는지)을 갖췄는가. **손으로 옮겨 적은 값이 아닌지**는
       여기서 못 잰다 — 그것은 ①(pytest 가 방금 이 파일을 새로 쓴 것)이 보장한다.
    ③ **절 목록 전수** — 이 차선에 배정된 DSM U1·U2 11 절을 전부 찍는다. 닫은 셋
       (U2-03·U2-04·U2-05)은 ①②로, 못 닫은 여덟(U1-01~06 · U2-01·02)은
       **「무엇이 없는가」 한 줄**로. 못 닫은 칸을 빈 칸으로 두지 않는다 — 빈 칸은
       「모른다」와 「없다」가 구별되지 않는다(D-274).

무엇을 하지 않는가
------------------
· 대장(`ga_readiness.yaml`) 이동은 이 게이트의 일이 아니다 — P-356 ④는
  `docs/agent/evidence/SPEC/N1_promotions.md` 에 **제안만** 적고, 대장에 실제로
  옮기는 것은 조율자다(대장은 손으로 고치지 않는다 — 세종 판정 그대로).

종료 코드 (저장소 규약 · D-400)
    0 = 쟀고 통과(닫은 열 3/3)   1 = 쟀고 실패   2 = 못 쟀다 (회색)

    python scripts/verify_spec_dsm.py                  # 판정 (호스트 — docker 를 부른다)
    python scripts/verify_spec_dsm.py --self-test        # 판정 규칙만
    python scripts/verify_spec_dsm.py --no-run           # ②③만(pytest 를 다시 안 돌린다 · 빠르다)
    python scripts/verify_spec_dsm.py --shell gx-shell   # 컨테이너 이름을 바꿔 잰다

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
TESTS_REL = "tests/test_p356_u2_spec_promotions.py"
TESTS = BACKEND / TESTS_REL
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"
SHELL_CONTAINER = "gx-shell"
TAG = "[SPEC-DSM]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 닫은 열(P-356 넷을 갖췄다고 이 차선이 주장하는 것) — S 규모 3건, S 먼저(WO-15 §5 P-358).
CLOSED_CLAUSES: tuple[str, ...] = ("DSM-U2-03", "DSM-U2-04", "DSM-U2-05")

#: annex 원문(§4.2) 제목 — `docs/design/DSM_재난안전관리App_명세서_v1.1_지침기반_20260915.md`
#: 표 그대로. 손으로 옮겨 적은 것이지만 **제목 문자열**일 뿐이고 판정에 안 쓴다
#: (판정은 evidence 파일이 한다) — 화면에 사람이 읽을 이름을 대는 용도다.
TITLES: dict[str, str] = {
    "DSM-U1-01": "유형별 행동 카드",
    "DSM-U1-02": "112/119 통보 기록",
    "DSM-U1-03": "인근 카메라 전환·추적",
    "DSM-U1-04": "관제일지 자동",
    "DSM-U1-05": "비상벨·시민 신고 접수 카드",
    "DSM-U1-06": "선별관제 큐 정렬",
    "DSM-U2-01": "상황판단 카드",
    "DSM-U2-02": "상황보고 초안 승인",
    "DSM-U2-03": "상황판단회의 기록",
    "DSM-U2-04": "임계값 도달 알림",
    "DSM-U2-05": "교대 인수인계 합동 확인",
}

#: 이 차선(N1)에 배정된 열한 절 중 이번 턴에 못 닫은 여덟 — **「무엇이 없는가」 한 줄**
#: (P-358 형식). 빈 칸으로 두지 않는다(D-274). S 셋을 먼저 닫으라는 지시(WO-15 §5)를
#: 그대로 따랐고, 시간표 안에서 M 여덟은 다음 턴 자리다.
NOT_STARTED: dict[str, str] = {
    "DSM-U1-01": "유형별 행동 카드 — `playbooks.yaml` 유형별 3단계 정의가 없다. "
                "M 규모(사건 유형별 체크리스트 + 감사 배선)라 이번 차선(S 3건 우선)의 "
                "시간 안에 못 붙였다.",
    "DSM-U1-02": "112/119 통보 기록 — `POST /events/{id}/notify-agency` 엔드포인트가 "
                "없다(기존 `/events/{id}/notify` 는 F-10 발송이지 통보 시각·통보자 "
                "기록이 아니다). S 규모지만 이번 차선은 U2 를 먼저 닫았다.",
    "DSM-U1-03": "인근 카메라 전환·추적 — `GET /cameras/nearby?event=` 반경 조회가 "
                "없다. M 규모(카메라 반경 계산 + PTZ 프리셋)라 범위 밖.",
    "DSM-U1-04": "관제일지 자동 — `handover_service` 확장 여지는 확인했으나(U1-04 는 "
                "일지, U2-05 는 확인 — 다른 절이다) 일지 표·PDF 출력은 아직 없다. "
                "M 규모라 범위 밖.",
    "DSM-U1-05": "비상벨·시민 신고 접수 카드 — `POST /events`(manual, source=manual) "
                "엔드포인트가 없다. M 규모(사건 생성 커널 진입점 신설)라 범위 밖.",
    "DSM-U1-06": "선별관제 큐 정렬 — 정렬 규칙(심각+미처리 → 통보 미완 → 경과 순)이 "
                "기존 `events/queue` 에 없다. M 규모(정렬식 + 800대 규모 검증)라 범위 밖.",
    "DSM-U2-01": "상황판단 카드 — 즉시 보고 대상 판정(사망 3/화재 5·14종) 규칙표가 "
                "없고, 확정 시 U4 상황보고 초안 자동 생성까지 걸린 사슬이다. M 규모라 "
                "이번 차선(S 3건 우선)의 시간 안에 못 붙였다.",
    "DSM-U2-02": "상황보고 초안 승인 — `POST /reports/{id}/approve` 엔드포인트가 "
                "없다(기존 `/reports/runs` 는 생성·다운로드뿐, 승인/반려 상태 전이가 "
                "없다). M 규모(보고서 상태기계 확장)라 범위 밖.",
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
    if not (request.get("path") or "").startswith("/api/dsm/"):
        return (EXIT_FAIL,
                "%s — 요청 경로(%r)가 /api/dsm/ 가 아니다 — 다른 문을 잰 증거일 수 있다"
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
             "-e", "DB_TEST_NAME=test_gx_verify_spec_dsm",
             "-w", "/app", shell,
             "python", "-m", "pytest", TESTS_REL,
             "-q", "--create-db", "-p", "no:randomly"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            #: ★ `guardianx-lane-count-ceilings` — 공유 gx-shell 은 다른 차선과
            #:   나뉜다. 10분 여유(`verify_password_reset.py` · `verify_spec_fws.py` 와
            #:   같은 값).
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

    good = {
        "id": "DSM-U2-03", "measured_at": "2026-09-27T00:00:00+00:00",
        "measured_by": "django_test_client",
        "test": "tests.test_p356_u2_spec_promotions.X.y",
        "request": {"method": "POST", "path": "/api/dsm/situation-meetings", "body": {}},
        "response": {"status": 200, "body": {}}, "what": "실측",
    }
    code, _ = judge_evidence("DSM-U2-03", good)
    check("증거 성립 표본 → 초록", code == EXIT_OK)

    code, _ = judge_evidence("DSM-U2-03", None)
    check("증거 파일 없음 → 회색(못 쟀다)", code == EXIT_UNDECIDABLE)

    broken_status = dict(good, response={"status": 500, "body": {}})
    code, _ = judge_evidence("DSM-U2-03", broken_status)
    check("★★ 출생표본 — 응답 500 인 증거 → 빨강(성공을 가장한 실패를 못 잡으면 "
         "이 게이트는 없느니만 못하다)", code == EXIT_FAIL)

    broken_hand = dict(good, measured_by="hand")
    code, _ = judge_evidence("DSM-U2-03", broken_hand)
    check("★ measured_by=hand(손으로 적음) → 빨강", code == EXIT_FAIL)

    broken_path = dict(good, request={"method": "POST", "path": "/api/fws/x", "body": {}})
    code, _ = judge_evidence("DSM-U2-03", broken_path)
    check("★ 다른 App 경로를 잰 증거 → 빨강", code == EXIT_FAIL)

    broken_id = dict(good, id="DSM-U2-99")
    code, _ = judge_evidence("DSM-U2-03", broken_id)
    check("파일 이름과 id 가 다르면 → 빨강", code == EXIT_FAIL)

    check("combine — 하나라도 빨강이면 빨강", combine([EXIT_OK, EXIT_FAIL]) == EXIT_FAIL)
    check("combine — 빨강 없고 회색 있으면 회색",
         combine([EXIT_OK, EXIT_UNDECIDABLE]) == EXIT_UNDECIDABLE)
    check("combine — 전부 초록이면 초록", combine([EXIT_OK, EXIT_OK]) == EXIT_OK)

    print("%s 자기시험 %d건 실패" % (TAG, fails))
    return EXIT_FAIL if fails else EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="DSM-U2-03·U2-04·U2-05 별표 절 승격 게이트")
    ap.add_argument("--self-test", action="store_true")
    #: [턴 AK · 조율자 병합] **기본은 다시 안 돌린다.** 시험이 증거 파일을 새 시각으로 덮어써서, GA 판정기가
    #:   이 게이트를 부를 때마다 추적 파일이 바뀌고 측정 재현성(D-344)이 깨졌다 — 게이트는 추적 파일을 쓰지 않는다.
    #:   시험을 다시 돌려 증거를 새로 찍는 것은 `--run`(손 · 창 ③)이다.
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
            print("%s **판정 불가 · 회색** — 길목 시험 파일이 없다: %s"
                 % (TAG, TESTS_REL))
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
    print("%s ── 요약 — 닫은 열 %d/%d(분모는 이 차선 배정 11) · 최종 %s ──"
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
        target="gx-shell(%s) 안 backend/ · apps.dsm.situation_meeting_service · "
              "apps.dsm.threshold_alert_service · apps.dsm.handover_service · "
              "kernels.k5_trust · docs/agent/evidence/SPEC/*.json" % SHELL_CONTAINER,
        as_="pytest 는 자격증명 없이 --create-db 로 돈다 · HTTP 실측은 "
            "tests/test_p356_u2_spec_promotions.py 안에서 실제 JWT(RefreshToken.for_user)로",
        source="살아 있는 gx-shell 컨테이너(docker exec) · 그 실행이 방금 새로 쓴 "
              "evidence 파일 — 사진·손으로 옮긴 값이 아니라 이번 실행",
        measured="닫은 열 3건(DSM-U2-03·04·05 · S 규모) · 못 닫은 열 8건은 이유 1줄 "
                "(U1-01~06 · U2-01·02 · M 규모) · 분모 11(이 차선 N1 배정)",
    )
    raise SystemExit(main())
