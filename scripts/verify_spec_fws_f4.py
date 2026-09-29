#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-356·392·414 — FWS-F4-01~15 별표 절 승격 게이트(통합지휘본부장·상황실 ·
턴 AO 차선 N2).

`scripts/verify_spec_fws_f3b.py` 의 **판정식을 그대로 베낀다**(D-212 를 어기지
않는다 — 그 파일은 F3 잔여만, 이 파일은 F4 만 게이트한다. 판정 함수의 모양이
같은 것은 같은 규칙(P-356)을 재는 것이므로 같은 것이고, 이름이 겹치는 두 파일이
서로를 안 부르는 것은 DA-04 §1-1(게이트는 게이트를 import 하지 않는다)과 같은
결이다).

무엇을 재는가 — 넷(F3B 게이트의 셋 + title_parts)
--------------------------------------------------
    ① **길목** — `backend/tests/test_fws_f4.py` 를 gx-shell 안에서 그대로
       돌린다. 판정 규칙은 그 시험이 이미 정했다(D-212) — 이 게이트가 다시
       만들지 않는다. 그 시험은 도는 김에 `docs/agent/evidence/SPEC/<id>.json`
       을 **기계로** 새로 찍는다.
    ② **증거 성립** — 방금 찍힌 증거 파일이 「HTTP 로 실제로 두드렸다」는
       모양을 갖췄는가(`verify_spec_fws_f3b.py::judge_evidence` 와 같은 판정식).
    ③ **title_parts 빈 칸 0**(P-392) — 「제목이 부르는 것 ↔ 있는 것」 표에 빈
       칸이 있으면 반쪽이다 — 반쪽 승격은 이 게이트가 빨강으로 막는다.
    ④ **절 목록 전수** — FWS-F4-01~15 열 15개를 전부 찍는다. 닫은 열넷은
       ①②③으로, 못 닫은 하나(F4-14)는 **「무엇이 없는가」 한 줄**로(빈 칸으로
       두지 않는다 · D-274).

무엇을 하지 않는가
------------------
· 대장(`ga_readiness.yaml`) 이동은 이 게이트의 일이 아니다 — 제안만
  `docs/agent/evidence/SPEC/N2_promotions_ao.md` 에 적고, 대장에 옮기는 것은
  조율자다.

종료 코드 (저장소 규약 · D-400)
    0 = 쟀고 통과(닫은 열 14/14)   1 = 쟀고 실패   2 = 못 쟀다 (회색)

    python scripts/verify_spec_fws_f4.py                  # 판정 (호스트 — docker 를 부른다)
    python scripts/verify_spec_fws_f4.py --self-test        # 판정 규칙만
    python scripts/verify_spec_fws_f4.py --no-run           # ②③④만(pytest 를 다시 안 돌린다 · 빠르다)
    python scripts/verify_spec_fws_f4.py --shell gx-shell   # 컨테이너 이름을 바꿔 잰다

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
TESTS_REL = "tests/test_fws_f4.py"
TESTS = BACKEND / TESTS_REL
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"
SHELL_CONTAINER = "gx-shell"
TAG = "[SPEC-FWS-F4]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 닫은 열넷(P-356 넷을 갖췄다고 이 차선이 주장하는 것) — F4-01~15 열다섯 중
#: F4-14 는 못 닫았다 · 아래 NOT_STARTED.
CLOSED_CLAUSES: tuple[str, ...] = (
    "FWS-F4-01", "FWS-F4-02", "FWS-F4-03", "FWS-F4-04", "FWS-F4-05",
    "FWS-F4-06", "FWS-F4-07", "FWS-F4-08", "FWS-F4-09", "FWS-F4-10",
    "FWS-F4-11", "FWS-F4-12", "FWS-F4-13", "FWS-F4-15",
)

#: annex 원문(§5.4 Table) 제목 — `docs/design/FWS_산불감시App_명세서_v1.0_…
#: 20260915.md` 표 그대로. 판정에 안 쓴다(판정은 evidence 파일이 한다) —
#: 화면에 사람이 읽을 이름을 대는 용도다.
TITLES: dict[str, str] = {
    "FWS-F4-01": "지휘 화면 — 사건 1건 전체(지도·화선·자원·시계·대피·단계)",
    "FWS-F4-02": "대응단계 확정·상향(사유) · 지휘권 이양 기록(시군구→시도)",
    "FWS-F4-03": "통합지휘본부 설치 선언(위치·구성)",
    "FWS-F4-04": "헬기 요청 승인·투하 구역 지정",
    "FWS-F4-05": "대피 명령 승인(즉시/준비) · 해제",
    "FWS-F4-06": "소방·경찰·군 협조 요청 기록",
    "FWS-F4-07": "주불 진화 선언 · 진화완료 선언",
    "FWS-F4-08": "상황보고 승인(매시간)",
    "FWS-F4-09": "산림청·시도 상황실 화상/전화 연락 버튼",
    "FWS-F4-10": "대응 시계 — 신고·확인·헬기 투하·주불·진화완료 + 골든타임 초과 사유",
    "FWS-F4-11": "야간 전환(일몰) — 헬기 불가·야간 진화 자원 표시",
    "FWS-F4-12": "상황판단회의 기록",
    "FWS-F4-13": "동시 다발 사건 우선순위(위험도 정렬)",
    "FWS-F4-14": "진화완료 후 잔불·뒷불 감시 계획 승인(드론 순회)",
    "FWS-F4-15": "사후 보고서 1쪽(대응 시계·자원·대피·피해)",
}

#: 못 닫은 하나 — **「무엇이 없는가」 한 줄** (P-358 형식). 빈 칸으로 두지 않는다(D-274).
NOT_STARTED: dict[str, str] = {
    "FWS-F4-14": "드론 순회 감시 계획 승인 — annex 서버경로는 `POST …/ember-plan`"
                "(예약). 이 저장소에 드론 임무 예약 자체는 있으나(`apps/fws/"
                "drone.py`), 「진화완료 후 잔불·뒷불 감시」라는 **후속 국면(P5) "
                "전용 예약 계획**과 그 계획을 지휘부가 승인하는 문은 이 차선이 "
                "새로 짓지 않았다 — L 규모, 조율자 지시대로 이 턴에서 손대지 "
                "않는다(`기능명세_미포함표_20260925.md` 의 250행 규모 표기와 "
                "같은 판단).",
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
    """P-392 — 「제목이 부르는 것 ↔ 있는 것」 표에 빈 칸이 있으면 빨강.

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
    if not (request.get("path") or "").startswith("/api/fws/command/"):
        return (EXIT_FAIL,
                "%s — 요청 경로(%r)가 /api/fws/command/ 가 아니다 — 다른 문을 잰 "
                "증거일 수 있다" % (clause_id, request.get("path")))
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
             "-e", "DB_TEST_NAME=test_gx_lane_n2",
             "-w", "/app", shell,
             "python", "-m", "pytest", TESTS_REL,
             "-q", "--create-db", "-p", "no:randomly"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            #: ★ `guardianx-lane-count-ceilings` — 공유 gx-shell 은 다른 차선과
            #:   나뉜다. 10분 여유(`verify_spec_fws_f3b.py` 와 같은 값).
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

    good_parts = [{"part": "단계", "where": "응답 stage", "status": "구현 — 실측"}]
    good = {
        "id": "FWS-F4-02", "measured_at": "2026-09-30T00:00:00+00:00",
        "measured_by": "django_test_client", "test": "tests.test_fws_f4.X.y",
        "request": {"method": "POST", "path": "/api/fws/command/incidents/1/stage",
                   "body": {}},
        "response": {"status": 200, "body": {}}, "what": "실측",
        "title_parts": good_parts,
    }
    code, _ = judge_evidence("FWS-F4-02", good)
    check("증거 성립 표본 → 초록", code == EXIT_OK)

    code, _ = judge_evidence("FWS-F4-02", None)
    check("증거 파일 없음 → 회색(못 쟀다)", code == EXIT_UNDECIDABLE)

    broken_status = dict(good, response={"status": 500, "body": {}})
    code, _ = judge_evidence("FWS-F4-02", broken_status)
    check("★★ 출생표본 — 응답 500 인 증거 → 빨강(성공을 가장한 실패를 못 잡으면 "
         "이 게이트는 없느니만 못하다)", code == EXIT_FAIL)

    broken_hand = dict(good, measured_by="hand")
    code, _ = judge_evidence("FWS-F4-02", broken_hand)
    check("★ measured_by=hand(손으로 적음) → 빨강", code == EXIT_FAIL)

    broken_path = dict(good, request={"method": "POST", "path": "/api/dsm/x", "body": {}})
    code, _ = judge_evidence("FWS-F4-02", broken_path)
    check("★ 다른 App 경로를 잰 증거 → 빨강", code == EXIT_FAIL)

    broken_id = dict(good, id="FWS-F4-99")
    code, _ = judge_evidence("FWS-F4-02", broken_id)
    check("파일 이름과 id 가 다르면 → 빨강", code == EXIT_FAIL)

    no_parts = dict(good, title_parts=[])
    code, _ = judge_evidence("FWS-F4-02", no_parts)
    check("★★ title_parts 비어 있으면 → 빨강(P-392 반쪽 승격을 막는다)",
         code == EXIT_FAIL)

    blank_cell = dict(good, title_parts=[{"part": "단계", "where": "", "status": "구현"}])
    code, _ = judge_evidence("FWS-F4-02", blank_cell)
    check("★★ title_parts 안 빈 칸 하나 → 빨강", code == EXIT_FAIL)

    open_row = dict(good, title_parts=[{"part": "화상", "where": "없음",
                                       "status": "없음 — 인프라 없음"}])
    code, _ = judge_evidence("FWS-F4-02", open_row)
    check("★★ status 가 '없음' 으로 시작하는 열린 행 → 성립하되(빈 칸은 아니다) "
         "닫힘 주장에는 못 쓴다(이 게이트는 빈 칸만 본다 — 열린 행 낱말 판정은 "
         "O 게이트(verify_spec_title_parts.py)의 몫)", code == EXIT_OK)

    check("combine — 하나라도 빨강이면 빨강", combine([EXIT_OK, EXIT_FAIL]) == EXIT_FAIL)
    check("combine — 빨강 없고 회색 있으면 회색",
         combine([EXIT_OK, EXIT_UNDECIDABLE]) == EXIT_UNDECIDABLE)
    check("combine — 전부 초록이면 초록", combine([EXIT_OK, EXIT_OK]) == EXIT_OK)

    print("%s 자기시험 %d건 실패" % (TAG, fails))
    return EXIT_FAIL if fails else EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="FWS-F4-01~15 별표 절 승격 게이트")
    ap.add_argument("--self-test", action="store_true")
    #: ★ 기본은 다시 안 돌린다(`verify_spec_fws_f3b.py` 와 같은 이유 — 시험이 증거
    #:   파일을 새 시각으로 덮어써서 측정 재현성이 깨진다). 시험을 다시 돌려 증거를
    #:   새로 찍는 것은 `--run`(손 · 창 ③)이다.
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

    # ② 절마다 증거 성립 + ③ title_parts 빈 칸 0
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
        target="gx-shell(%s) 안 backend/ · apps.fws.command(신규) · F3/F6 문 재사용 · "
              "DSM 대응 시계·U2-03 회의·K1 종결 축 재사용(P-414) · "
              "docs/agent/evidence/SPEC/*.json" % SHELL_CONTAINER,
        as_="pytest 는 자격증명 없이 --create-db 로 돈다 · HTTP 실측은 "
            "tests/test_fws_f4.py 안에서 실제 JWT(RefreshToken.for_user)로",
        source="살아 있는 gx-shell 컨테이너(docker exec) · 그 실행이 방금 새로 쓴 "
              "evidence 파일 — 사진·손으로 옮긴 값이 아니라 이번 실행",
        measured="닫은 열 14건(FWS-F4-01~13·15) · 못 닫은 열 1건은 이유 1줄(F4-14) · "
                "분모 15",
    )
    raise SystemExit(main())
