#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-356·392·419·428 — 턴 AP 차선 N4 별표 절 승격 게이트(FWS F3·F5·F6 잔여 ·
DSM U4 잔여 M · 세종 P-424).

`scripts/verify_spec_fws_f3b.py` 의 판정식을 그대로 베낀다(D-212 — 같은 규칙은
같은 판정 함수로 잰다). 이 파일이 다른 점은 절 아홉이 **두 App**(DSM·FWS)에
걸쳐 있다는 것뿐이라, 증거 경로 검사만 `/api/dsm/`·`/api/fws/` 둘 다 받는다.

무엇을 재는가 — 넷(F3b 게이트와 같음)
--------------------------------------
    ① **길목** — 이 차선이 새로 쓴 시험 여덟 파일을 gx-shell 안에서 돌린다
       (`--run` 일 때만 · 기본은 **--no-run**, 지금 있는 evidence 파일만 본다 —
       `verify_spec_fws_f6.py` 와 같은 기본값).
    ② **증거 성립** — `docs/agent/evidence/SPEC/<id>.json` 이 「HTTP 로 실제로
       두드렸다」는 모양을 갖췄는가.
    ③ **title_parts 빈 칸 0**(P-392) — 「제목이 부르는 것 ↔ 있는 것」 표에 빈
       칸이 있으면 반쪽이다.
    ④ **눈금은 하나다**(P-419) — `status` 가 `없음`·`부분`·`근사`·`대리`·
       `[미확인]` 로 시작하면 **열린 행**이다. 단 `excluded_by`(P-###|D-###
       형식) + `excluded_why` 가 함께 있으면 그 행은 **닫힘**으로 센다
       (WO-19 「운영 집행·외부 실연동 부분은 excluded_by: P-428」).

닫은 여덟 · 못 닫은 셋(NOT_STARTED — 「무엇이 없는가」)
--------------------------------------------------------
FWS-F5-01 · FWS-F5-02 · FWS-F5-03 · FWS-F5-08 · FWS-F6-04 · DSM-U4-02 ·
DSM-U4-08 · DSM-U4-09 는 닫혔다. FWS-F3-16(헬기 투하 시각 없음 — 다른 차선이
더 깊이 고친 뒤에도 남은 열린 행) · FWS-F5-10(공용 계량 커널(S-20) 연계 없음) ·
DSM-U4-05(기상특보 제외해도 피해 누계·동원·향후 계획 구조화 원천이 이 저장소에
없다)는 못 닫았다 — 아래 NOT_STARTED.

무엇을 하지 않는가
------------------
대장(`ga_readiness.yaml`) 이동은 이 게이트의 일이 아니다 — 제안만
`docs/agent/evidence/SPEC/N4_promotions_ap.md` 에 적는다.

종료 코드 (D-400): 0=통과 1=실패 2=못 쟀다(회색)

    python scripts/verify_spec_ap_n4.py                 # 판정(호스트 — 기본 --no-run)
    python scripts/verify_spec_ap_n4.py --self-test      # 판정 규칙만
    python scripts/verify_spec_ap_n4.py --run             # 시험을 다시 돌려 evidence 를 새로 찍는다
    python scripts/verify_spec_ap_n4.py --shell gx-shell
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
#: 이 차선이 새로 쓴 시험 여덟 — `--run` 일 때만 gx-shell 안에서 돈다.
TESTS_REL: tuple[str, ...] = (
    "tests/test_ap_n4_f5_recon_coords_thermal.py",
    "tests/test_ap_n4_f6_spread_upload.py",
    "tests/test_ap_n4_f5_10_monthly.py",
    "tests/test_ap_n4_u4_02_interim_batch.py",
    "tests/test_ap_n4_u4_05_daily_report.py",
    "tests/test_ap_n4_u4_08_bundle.py",
    "tests/test_ap_n4_u4_09_safety_index.py",
)
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"
SHELL_CONTAINER = "gx-shell"
DB_TEST_NAME = "test_gx_lane_n4"
TAG = "[SPEC-AP-N4]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: ★ [2026-09-29 · 재확인] FWS-F3-16 은 이 목록에서 뺐다 — 같은 절을 병행
#:   손대던 다른 차선(N2b, `office2.py` 소유)이 골든타임 행을 대응 시계
#:   실측(`arrived_at`)으로 더 깊이 고쳤고, 그 과정에서 이 차선이 붙였던
#:   `excluded_by: P-428` 판정이 **틀렸다**고 정정했다(「코드 결손이지 외부
#:   실연동이 아니다」) — 헬기 물 투하 시각 자체가 저장소에 없는 것은 맞지만
#:   그것은 운영 집행/외부 실연동이 아니라 값 자체가 없는 코드 결손이라
#:   `excluded_by` 로 못 막는다. 아래 NOT_STARTED 로 옮긴다(D-212, 남의 더
#:   나은 판정을 덮어쓰지 않는다).
CLOSED_CLAUSES: tuple[str, ...] = (
    "FWS-F5-01", "FWS-F5-02", "FWS-F5-03", "FWS-F5-08", "FWS-F6-04",
    "DSM-U4-02", "DSM-U4-08", "DSM-U4-09",
)

TITLES: dict[str, str] = {
    "FWS-F3-16": "통계 — 발생·면적·원인·시간대·구역·오인율·확인 시간·골든타임 준수율",
    "FWS-F5-01": "정찰 임무 수신(발화 추정 좌표·반경) → 열화상 정찰",
    "FWS-F5-02": "열점·화선 표시(열화상 프레임 → 지도 폴리라인)",
    "FWS-F5-03": "확인 회신(산불 맞음/오인 · 사진·열화상)",
    "FWS-F5-08": "비행 기록·배터리·기체 상태",
    "FWS-F5-10": "계량(비행 분)",
    "FWS-F6-04": "확산예측 결과 수신(API [미확인] 또는 업로드)",
    "DSM-U4-02": "중간 보고 사이클 — 08시·17시 기준 응급조치 보고 자동 초안 · "
                "NDMS 입력용 표 내보내기",
    "DSM-U4-05": "일일상황보고 자동 — 기상특보·재난상황·통제 현황·피해 누계·"
                "대피·동원·향후 계획",
    "DSM-U4-08": "재난관리평가·감사 자료 묶음 — 상황보고·CBS·통제·회의·열람 "
                "대장·훈련·접속기록을 ZIP(PDF+CSV)",
    "DSM-U4-09": "통계 축 추가 — 지역안전지수 6분야에 맞춘 유형 분류 열",
}

#: 못 닫은 셋 — 「무엇이 없는가」 한 줄(D-274, 빈 칸으로 두지 않는다).
NOT_STARTED: dict[str, str] = {
    "FWS-F3-16": "헬기 물 투하 시각(신고 → 투하 30분) — 저장소에 그 시각 자체가 "
                "없다(F4-04 는 승인 시각만 적고, 대응 시계 네 시각에도 투하는 "
                "없다). ★ 이 절은 이 차선(N4)이 먼저 골든타임 행을 "
                "`excluded_by: P-428` 로 닫았으나, 같은 절을 병행 손대던 차선 "
                "N2b(`office2.py` 소유)가 대응 시계 실측(`arrived_at`)으로 더 "
                "깊이 고치면서 그 판정을 정정했다 — 「코드 결손이지 외부 "
                "실연동이 아니다」(TITLE_PARTS §3). 신고 접수 기준 골든타임은 "
                "N2b 가 실측으로 닫았지만, 헬기 투하 기준 하나가 남아 절 "
                "전체는 여전히 반쪽이다. 이 차선은 이 정정을 그대로 받아들이고 "
                "덮어쓰지 않는다(D-212).",
    "FWS-F5-10": "명세가 가리키는 커널/S-20 공용 계량 체계와의 연계 — "
                "`flight_minutes_total()`/`flight_minutes_monthly_table()` 은 "
                "F5-08 감사 로그를 자체 집계하는 드론 전용 로컬 카운터일 뿐, "
                "공용 계량 커널(`apps.dsm.metering` 류)에는 반영되지 않는다. "
                "공용 커널을 고치는 일은 여러 차선이 공유하는 자리라 이 턴 "
                "범위 밖이다(excluded_by 로 못 막는다 — 외부 실연동이 아니라 "
                "내부 공용 모듈 변경이 필요한 경우다). 나머지 넷(합계·건수·월별 "
                "필터·월 표)은 이 턴이 실측·신설로 닫았다.",
    "DSM-U4-05": "피해 누계·동원(자원 배치)·향후 계획 — 이 저장소에 그 값을 "
                "쥔 구조화 표가 없다(별지 제1호서식은 사람이 그때그때 채우는 "
                "자유 입력칸이지 재조회 가능한 표가 아니다, `incident_report.py` "
                "실측). 지어내지 않는다(D-280). 기상특보만 excluded_by: P-428 "
                "(외부 기관 API 실연동)로 닫혔고, 재난상황·통제 현황·대피 "
                "셋은 이 턴이 실측·신설로 닫았다 — 그러나 세 칸이 열려 있어 "
                "절 전체는 반쪽이다(P-419, 하나라도 열려 있으면 반쪽).",
}

REQUIRED_EVIDENCE_KEYS = ("id", "measured_at", "measured_by", "test", "request",
                         "response", "what", "title_parts")
REQUIRED_TITLE_PART_KEYS = ("part", "where", "status")
#: 결정 제외 번호 형식 — `docs/agent/evidence/SPEC/N1_promotions_ao.md` §1 의
#: `EXCLUDED_BY_RE`·`PROXY_PREFIXES` 와 같은 규칙(P-406).
EXCLUDED_BY_RE = re.compile(r"^(?:P|D)-\d{3}$")
OPEN_PREFIXES = ("없음", "부분", "근사", "대리", "대안", "[미확인]", "missing")
VALID_PATH_PREFIXES = ("/api/dsm/", "/api/fws/")


# ═══════════════════════════════════════════════════════════════════════════
# 판정 — 순수 함수
# ═══════════════════════════════════════════════════════════════════════════
def parse_pytest_summary(output: str) -> tuple[int, int, int] | None:
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


def _is_open_status(status: str) -> bool:
    s = (status or "").strip()
    return any(s.startswith(p) for p in OPEN_PREFIXES)


def _is_excluded_closed(part: dict) -> bool:
    by = part.get("excluded_by")
    why = part.get("excluded_why")
    return (isinstance(by, str) and bool(EXCLUDED_BY_RE.match(by.strip()))
            and isinstance(why, str) and bool(why.strip()))


def judge_title_parts(clause_id: str, payload: dict) -> tuple[int, str]:
    """P-392 빈 칸 0 + P-419 눈금 하나(열린 상태 접두 · excluded_by 예외).

    ⚠ 자기시험이 이 함수를 몸소 망가뜨려 본다."""
    parts = payload.get("title_parts")
    if not isinstance(parts, list) or not parts:
        return EXIT_FAIL, "%s — title_parts 가 없거나 비었다(반쪽 승격 의심)" % clause_id
    open_rows = []
    for i, part in enumerate(parts):
        if not isinstance(part, dict):
            return EXIT_FAIL, "%s — title_parts[%d] 가 표 모양이 아니다" % (clause_id, i)
        missing = [k for k in REQUIRED_TITLE_PART_KEYS
                  if not (part.get(k) or "").strip()]
        if missing:
            return (EXIT_FAIL,
                    "%s — title_parts[%d] 에 빈 칸: %s" % (clause_id, i, missing))
        if _is_open_status(part.get("status", "")) and not _is_excluded_closed(part):
            open_rows.append(part.get("part"))
    if open_rows:
        return (EXIT_FAIL,
                "%s — 열린 행 %d개(대리/없음/부분 · excluded_by 없음): %s"
                % (clause_id, len(open_rows), open_rows))
    return EXIT_OK, "%s — title_parts %d행 전부 닫힘(빈 칸 0 · 열린 행 0)" % (
        clause_id, len(parts))


def judge_evidence(clause_id: str, payload: dict | None) -> tuple[int, str]:
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
    if not any(path.startswith(p) for p in VALID_PATH_PREFIXES):
        return (EXIT_FAIL,
                "%s — 요청 경로(%r)가 /api/dsm/ 도 /api/fws/ 도 아니다 — 다른 문을 "
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
             "-e", "DB_TEST_NAME=%s" % DB_TEST_NAME,
             "-w", "/app", shell,
             "python", "-m", "pytest", *TESTS_REL,
             "-q", "-p", "no:randomly"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
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
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    #: [턴 AQ · P-431 · 차선 Q] 제목 부분 표(title_parts·retro*)는 사람 파일
    #: `<id>.retro.md` 에서만 온다 — json 에 남은 그 키는 버린다(판정식은 그대로).
    _here = str(Path(__file__).resolve().parent)
    if _here not in sys.path:
        sys.path.insert(0, _here)
    from _retro_table import overlay  # noqa: PLC0415
    return overlay(payload, clause_id, EVIDENCE_DIR)


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310·P-319) — 판정식을 몸소 망가뜨려 실패(1)를 본다
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

    good_parts = [{"part": "대상", "where": "응답 x", "status": "구현 — 실측"}]
    good = {
        "id": "DSM-U4-09", "measured_at": "2026-09-29T00:00:00+00:00",
        "measured_by": "django_test_client", "test": "tests.test_ap_n4_x.X.y",
        "request": {"method": "GET", "path": "/api/dsm/stats/safety-index", "params": {}},
        "response": {"status": 200, "body": {}}, "what": "실측",
        "title_parts": good_parts,
    }
    code, _ = judge_evidence("DSM-U4-09", good)
    check("증거 성립 표본(DSM 경로) → 초록", code == EXIT_OK)

    good_fws = dict(good, id="FWS-F5-02",
                    request={"method": "GET", "path": "/api/fws/drone/x", "params": {}})
    code, _ = judge_evidence("FWS-F5-02", good_fws)
    check("증거 성립 표본(FWS 경로) → 초록", code == EXIT_OK)

    code, _ = judge_evidence("DSM-U4-09", None)
    check("증거 파일 없음 → 회색(못 쟀다)", code == EXIT_UNDECIDABLE)

    broken_status = dict(good, response={"status": 500, "body": {}})
    code, _ = judge_evidence("DSM-U4-09", broken_status)
    check("★★ 출생표본 — 응답 500 인 증거 → 빨강", code == EXIT_FAIL)

    broken_hand = dict(good, measured_by="hand")
    code, _ = judge_evidence("DSM-U4-09", broken_hand)
    check("★ measured_by=hand → 빨강", code == EXIT_FAIL)

    broken_path = dict(good, request={"method": "GET", "path": "/api/orders/x", "params": {}})
    code, _ = judge_evidence("DSM-U4-09", broken_path)
    check("★ 금지구역/다른 App 경로를 잰 증거 → 빨강", code == EXIT_FAIL)

    broken_id = dict(good, id="DSM-U4-99")
    code, _ = judge_evidence("DSM-U4-09", broken_id)
    check("파일 이름과 id 가 다르면 → 빨강", code == EXIT_FAIL)

    no_parts = dict(good, title_parts=[])
    code, _ = judge_evidence("DSM-U4-09", no_parts)
    check("★★ title_parts 비어 있으면 → 빨강", code == EXIT_FAIL)

    blank_cell = dict(good, title_parts=[{"part": "대상", "where": "", "status": "구현"}])
    code, _ = judge_evidence("DSM-U4-09", blank_cell)
    check("★★ title_parts 안 빈 칸 하나 → 빨강", code == EXIT_FAIL)

    open_row = dict(good, title_parts=[{"part": "대상", "where": "응답 x", "status": "없음"}])
    code, _ = judge_evidence("DSM-U4-09", open_row)
    check("★★ [P-419] 「없음」 으로 시작하는 열린 행 → 빨강(대리 지표를 못 잡으면 "
         "반쪽 승격이 새어 나간다)", code == EXIT_FAIL)

    proxy_row = dict(good, title_parts=[{"part": "대상", "where": "응답 x", "status": "근사 실측"}])
    code, _ = judge_evidence("DSM-U4-09", proxy_row)
    check("★ 「근사」 접두(대리 지표) → 빨강", code == EXIT_FAIL)

    excluded_row = dict(good, title_parts=[
        {"part": "대상", "where": "응답 x", "status": "없음 — 외부 실연동",
         "excluded_by": "P-428", "excluded_why": "산림청 실연동 — 이 턴 범위 밖"}])
    code, _ = judge_evidence("DSM-U4-09", excluded_row)
    check("★ excluded_by(P-###)+excluded_why 가 있으면 「없음」도 닫힘",
         code == EXIT_OK)

    excluded_no_number = dict(good, title_parts=[
        {"part": "대상", "where": "응답 x", "status": "없음",
         "excluded_why": "번호 없이 사유만"}])
    code, _ = judge_evidence("DSM-U4-09", excluded_no_number)
    check("★★ 번호 없는 「없음」(excluded_by 없음) → 여전히 빨강(P-406 그대로)",
         code == EXIT_FAIL)

    check("combine — 하나라도 빨강이면 빨강", combine([EXIT_OK, EXIT_FAIL]) == EXIT_FAIL)
    check("combine — 빨강 없고 회색 있으면 회색",
         combine([EXIT_OK, EXIT_UNDECIDABLE]) == EXIT_UNDECIDABLE)
    check("combine — 전부 초록이면 초록", combine([EXIT_OK, EXIT_OK]) == EXIT_OK)

    print("%s 자기시험 %d건 실패" % (TAG, fails))
    return EXIT_FAIL if fails else EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="턴 AP 차선 N4 별표 절 승격 게이트")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true",
                   help="pytest 를 다시 돌려 evidence 를 새로 찍는다(손으로만)")
    ap.add_argument("--no-run", action="store_true",
                   help="pytest 를 다시 안 돌린다 — 지금 있는 evidence 파일만 본다(기본값)")
    ap.add_argument("--shell", default=SHELL_CONTAINER)
    args = ap.parse_args()
    args.no_run = args.no_run or not args.run

    if args.self_test:
        return self_test()

    codes: list[int] = []

    if args.no_run:
        print("%s [입력] --no-run(기본값) — pytest 를 다시 안 돌린다(지금 있는 "
             "evidence 파일만)" % TAG)
    else:
        raw = run_gate_tests(args.shell)
        summary = parse_pytest_summary(raw) if raw is not None else None
        code1, verdict1 = judge_gate_tests(summary)
        codes.append(code1)
        print("%s [입력] 길목 시험 = %s개 파일 (gx-shell=%s)"
             % (TAG, len(TESTS_REL), args.shell))
        if summary is not None:
            print("%s [입력] pytest 요약 — 통과 %d · 실패 %d · 에러 %d"
                 % (TAG, summary[0], summary[1], summary[2]))
        print("%s %s ① %s" % (TAG, "OK  " if code1 == EXIT_OK else
                              ("FAIL" if code1 == EXIT_FAIL else "GRAY"), verdict1))
        if code1 != EXIT_OK and raw:
            print("%s ── 길목 시험 원문 꼬리 ──\n%s" % (TAG, raw[-3000:]))

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
    n_ok = sum(1 for c in (codes[1:] if not args.no_run else codes) if c == EXIT_OK)
    print("%s ── 요약 — 닫은 열 %d/%d · 최종 %s ──"
         % (TAG, n_ok, len(CLOSED_CLAUSES),
            {EXIT_OK: "PASS", EXIT_FAIL: "FAIL", EXIT_UNDECIDABLE: "GRAY"}[final]))
    return final


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE

    gate_header(
        __file__,
        target="gx-shell(%s) 안 backend/ · apps.dsm.api_u4(신규 넷) · "
              "apps.fws.api_ap(신규 · ap_f5·ap_f6) · docs/agent/evidence/SPEC/*.json"
              % SHELL_CONTAINER,
        as_="pytest 는 자격증명 없이 --create-db 로 돈다 · HTTP 실측은 이 차선의 "
            "새 시험 파일들 안에서 실제 JWT(RefreshToken.for_user)로",
        source="살아 있는 gx-shell 컨테이너(docker exec) · --run 이면 그 실행이 "
              "방금 새로 쓴 evidence 파일 · 기본(--no-run)은 지금 있는 파일",
        measured="닫은 열 8건(FWS-F5-01·F5-02·F5-03·F5-08·F6-04 · "
                "DSM-U4-02·U4-08·U4-09) · 못 닫은 열 3건은 이유 1줄(FWS-F3-16 · "
                "FWS-F5-10 · DSM-U4-05) · 분모 11",
    )
    raise SystemExit(main())
