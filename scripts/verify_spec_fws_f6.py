#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-356·357·358·392 — FWS-F6-01~10 별표 절 승격 게이트 (annex §5.1 · 턴 AM 차선
N3(구현) · 턴 AN 차선 N1(P-392 「반쪽 여섯 채우기」 — F6-07 웹푸시 훈련 채널)).

`scripts/verify_spec_fws.py`(F1·F2, 차선 N2 소유) 의 **판정식을 그대로 베낀다**
(D-212 를 어기지 않는다 — 그 파일은 F1·F2 만 게이트하고, 이 파일은 F6 만
게이트한다. 판정 함수의 모양이 같은 것은 같은 규칙(P-356)을 재는 것이므로
같은 것이고, 이름이 겹치는 두 파일이 서로를 안 부르는 것은 DA-04 §1-1(게이트는
게이트를 import 하지 않는다)과 같은 결이다).

무엇을 재는가 — 셋
--------------------
    ① **길목** — `backend/tests/test_fws_f6.py` 를 gx-shell 안에서 그대로 돌린다.
       판정 규칙은 그 시험이 이미 정했다(D-212) — 이 게이트가 다시 만들지 않는다.
       그 시험은 도는 김에 `docs/agent/evidence/SPEC/<id>.json` 을 **기계로** 새로
       찍는다.
    ② **증거 성립** — 방금 찍힌 증거 파일 8건이 「HTTP 로 실제로 두드렸다」는
       모양을 갖췄는가.
    ③ **title_parts 빈 칸 0**(P-392 · 있으면만) — 8건 중 F6-07 은 이 턴(AN)이
       「제목이 부르는 것 ↔ 있는 것」 표(`title_parts`)를 새로 더했다 — 있으면
       빈 칸 0 을 강제한다(`judge_title_parts`). 나머지 일곱(F6-01·02·03·05·06·
       08·10)은 **턴 AM 의 것을 이 턴이 다시 짓지 않았다** — title_parts 가
       없어도(레거시) 빨강으로 막지 않는다(그렇게 하면 이 차선이 손대지 않은
       절까지 이 차선 탓에 실패로 바뀐다 · `verify_spec_fws_f3b.py` 는 반대로
       "닫은 열 전부가 그 차선 소유"라 강제할 수 있었던 것과 다른 처지다).
    ④ **절 목록 전수** — FWS-F6-01~10 열 열 개를 전부 찍는다. 닫은 여덟은 ①②③로,
       못 닫은 둘(F6-04·09)은 **「무엇이 없는가」 한 줄**로(빈 칸으로 두지 않는다
       · D-274).

무엇을 하지 않는가
------------------
· 대장(`ga_readiness.yaml`) 이동은 이 게이트의 일이 아니다 — 제안만
  `docs/agent/evidence/SPEC/N3_promotions.md` 에 적고, 대장에 옮기는 것은
  조율자다.

종료 코드 (저장소 규약 · D-400)
    0 = 쟀고 통과(닫은 열 8/8)   1 = 쟀고 실패   2 = 못 쟀다 (회색)

    python scripts/verify_spec_fws_f6.py                  # 판정 (호스트 — docker 를 부른다)
    python scripts/verify_spec_fws_f6.py --self-test        # 판정 규칙만
    python scripts/verify_spec_fws_f6.py --no-run           # ②③만(pytest 를 다시 안 돌린다 · 빠르다)
    python scripts/verify_spec_fws_f6.py --shell gx-shell   # 컨테이너 이름을 바꿔 잰다

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
TESTS_REL = "tests/test_fws_f6.py"
TESTS = BACKEND / TESTS_REL
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"
SHELL_CONTAINER = "gx-shell"
TAG = "[SPEC-FWS-F6]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 닫은 열(P-356 넷을 갖췄다고 이 차선이 주장하는 것) — F6 여덟(annex 열 넷 중
#: F6-04·09 는 못 닫았다 · 아래 NOT_STARTED).
CLOSED_CLAUSES: tuple[str, ...] = (
    "FWS-F6-01", "FWS-F6-02", "FWS-F6-03", "FWS-F6-05",
    "FWS-F6-06", "FWS-F6-07", "FWS-F6-08", "FWS-F6-10",
)

#: annex 원문(§5.1 Table A) 제목 — `docs/design/FWS_산불감시App_명세서_v1.0_…
#: 20260915.md` 표 그대로. 손으로 옮겨 적은 것이지만 **제목 문자열**일 뿐이고
#: 판정에 안 쓴다(판정은 evidence 파일이 한다) — 화면에 사람이 읽을 이름을 대는 용도다.
TITLES: dict[str, str] = {
    "FWS-F6-01": "산림청 산불상황관제시스템/산림재난정보시스템 입력 항목 "
                "내보내기(JSON/CSV · 항목 1:1)",
    "FWS-F6-02": "웹훅 — fws.fire.confirmed/stage_changed/evacuation_ordered/"
                "extinguished(CAP 1.2 · 필터)",
    "FWS-F6-03": "산불위험예보·위기경보 수신(산림과학원·산림청 API 또는 수동)",
    "FWS-F6-04": "확산예측 결과 수신(API [미확인] 또는 업로드)",
    "FWS-F6-05": "헬기 출동 요청·위치 수신(산림항공 · 수동 입력 대안)",
    "FWS-F6-06": "소방 119 출동 사건 연동(재난안전 App DSM 통해)",
    "FWS-F6-07": "스마트산림재난 앱 대피 푸시 연계(산림청) [미확인] · 대안 CBS 초안",
    "FWS-F6-08": "경찰 교통통제·입산통제 협조 기록",
    "FWS-F6-09": "스키마 버전·헬스·요청 한도(공통 API-02)",
    "FWS-F6-10": "국립공원·국유림관리소 관할 사건 이첩",
}

#: 못 닫은 둘 — **「무엇이 없는가」 한 줄** (P-358 형식). 빈 칸으로 두지 않는다(D-274).
NOT_STARTED: dict[str, str] = {
    "FWS-F6-04": "확산예측 — 풍향장·지형·연료(임상)를 쓰는 확산예측 모델이나 그 결과를 "
                "낼 외부 API 가 이 차선에 없다. annex 가 스스로 허락한 대안("
                "「업로드」)도 짓지 않았다 — 업로드 결과(폴리곤·GeoJSON)를 화면에 "
                "놓으려면 좌표 목록이 아니라 지도 오버레이가 필요한데, 그것은 §0.4 "
                "인접(MapForRoute·FormRoute 금지구역) 이라 이번 차선이 손대지 않는다. "
                "L 규모 · 지어내지 않고 범위 밖으로 남긴다.",
    "FWS-F6-09": "스키마 버전·헬스·요청 한도 — 셋 중 둘만 있다. 스키마 버전은 "
                "`common/schema_header.py` 전역 미들웨어가 이미 모든 응답에 "
                "X-GX-Schema 를 달고(재사용 · `test_fws_f6.py::F6_09_HealthReuseTest` "
                "가 확인), 헬스는 `GET /api/fws/health` 로 새로 열었다(DSM 과 같은 "
                "모양의 db·cache 검사 — 계층 게이트(D-278)가 App 간 직접 import 를 "
                "막아 `apps.fws.integration.fws_health` 가 다시 지었다). 그러나 "
                "**요청 한도(API-02)가 없다** — "
                "이 저장소의 율제한은 로그인(`POST /api/v1/auth/login`, SEC-21) "
                "하나뿐이고 그 미들웨어는 dj-core 소유(§0.4)다. 일반 API 라우트(이 "
                "앱 포함)에는 요청 한도가 어디에도 없다 — 새로 걸려면 공용 "
                "미들웨어를 고쳐야 하는데 그 미들웨어는 이번 턴 다른 차선도 쓰는 "
                "자리라 손대지 않는다. 제목이 부르는 셋 중 하나가 없으므로(P-376) "
                "닫힌 절로 제안하지 않는다.",
}

REQUIRED_EVIDENCE_KEYS = ("id", "measured_at", "measured_by", "test", "request",
                         "response", "what")
#: [턴 AN · P-392] `title_parts` 는 **있으면** 이 모양이어야 한다 — 없어도
#: (레거시 F6-01·02·03·05·06·08·10) 빨강으로 막지 않는다(위 머리말 ③).
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
    """P-392 — **있으면** 빈 칸 0 을 강제한다(`verify_spec_fws_f3b.py::
    judge_title_parts` 와 같은 판정식). `title_parts` 키 자체가 없는 레거시
    증거(F6-01·02·03·05·06·08·10 — 이 턴이 손대지 않았다)는 **초록으로 넘긴다**
    — 있는데 부실한 것과 아예 없는 것은 다르다(전자만 「반쪽을 숨겼다」로 본다).
    """
    if "title_parts" not in payload:
        return EXIT_OK, "%s — title_parts 없음(레거시 · 강제하지 않는다)" % clause_id
    parts = payload.get("title_parts")
    if not isinstance(parts, list) or not parts:
        return EXIT_FAIL, "%s — title_parts 가 있는데 비었다(반쪽 승격 의심)" % clause_id
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
             "-e", "DB_TEST_NAME=test_gx_verify_spec_fws_f6",
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
        "id": "FWS-F6-08", "measured_at": "2026-09-28T00:00:00+00:00",
        "measured_by": "django_test_client", "test": "tests.test_fws_f6.X.y",
        "request": {"method": "POST", "path": "/api/fws/liaison/fire-events/1/"
                                              "police-coordination", "body": {}},
        "response": {"status": 200, "body": {}}, "what": "실측",
    }
    code, _ = judge_evidence("FWS-F6-08", good)
    check("증거 성립 표본 → 초록", code == EXIT_OK)

    code, _ = judge_evidence("FWS-F6-08", None)
    check("증거 파일 없음 → 회색(못 쟀다)", code == EXIT_UNDECIDABLE)

    broken_status = dict(good, response={"status": 500, "body": {}})
    code, _ = judge_evidence("FWS-F6-08", broken_status)
    check("★★ 출생표본 — 응답 500 인 증거 → 빨강(성공을 가장한 실패를 못 잡으면 "
         "이 게이트는 없느니만 못하다)", code == EXIT_FAIL)

    broken_hand = dict(good, measured_by="hand")
    code, _ = judge_evidence("FWS-F6-08", broken_hand)
    check("★ measured_by=hand(손으로 적음) → 빨강", code == EXIT_FAIL)

    broken_path = dict(good, request={"method": "POST", "path": "/api/dsm/x", "body": {}})
    code, _ = judge_evidence("FWS-F6-08", broken_path)
    check("★ 다른 App 경로를 잰 증거 → 빨강", code == EXIT_FAIL)

    broken_id = dict(good, id="FWS-F6-99")
    code, _ = judge_evidence("FWS-F6-08", broken_id)
    check("파일 이름과 id 가 다르면 → 빨강", code == EXIT_FAIL)

    #: [턴 AN · P-392] title_parts — **있으면** 강제, **없으면**(레거시) 넘긴다.
    code, _ = judge_evidence("FWS-F6-08", good)
    check("title_parts 키 자체가 없으면(레거시) → 그래도 초록", code == EXIT_OK)

    with_parts = dict(good, title_parts=[
        {"part": "대피 소요시간", "where": "constants.evacuation_deadline_hours",
         "status": "있음"}])
    code, _ = judge_evidence("FWS-F6-08", with_parts)
    check("title_parts 가 있고 다 채워짐 → 초록", code == EXIT_OK)

    empty_parts = dict(good, title_parts=[])
    code, _ = judge_evidence("FWS-F6-08", empty_parts)
    check("★★ title_parts 키가 있는데 비어 있으면 → 빨강(반쪽을 숨겼다)",
         code == EXIT_FAIL)

    blank_cell = dict(good, title_parts=[
        {"part": "대피 소요시간", "where": "", "status": "있음"}])
    code, _ = judge_evidence("FWS-F6-08", blank_cell)
    check("★★ title_parts 안 빈 칸 하나 → 빨강", code == EXIT_FAIL)

    check("combine — 하나라도 빨강이면 빨강", combine([EXIT_OK, EXIT_FAIL]) == EXIT_FAIL)
    check("combine — 빨강 없고 회색 있으면 회색",
         combine([EXIT_OK, EXIT_UNDECIDABLE]) == EXIT_UNDECIDABLE)
    check("combine — 전부 초록이면 초록", combine([EXIT_OK, EXIT_OK]) == EXIT_OK)

    print("%s 자기시험 %d건 실패" % (TAG, fails))
    return EXIT_FAIL if fails else EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="FWS-F6-01~10 별표 절 승격 게이트")
    ap.add_argument("--self-test", action="store_true")
    #: ★ 기본은 다시 안 돌린다(`verify_spec_fws.py` 와 같은 이유 — 시험이 증거
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
        target="gx-shell(%s) 안 backend/ · apps.fws.integration(신규) · K1·K2 커널 "
              "재사용 · docs/agent/evidence/SPEC/*.json" % SHELL_CONTAINER,
        as_="pytest 는 자격증명 없이 --create-db 로 돈다 · HTTP 실측은 "
            "tests/test_fws_f6.py 안에서 실제 JWT(RefreshToken.for_user)로",
        source="살아 있는 gx-shell 컨테이너(docker exec) · 그 실행이 방금 새로 쓴 "
              "evidence 파일 — 사진·손으로 옮긴 값이 아니라 이번 실행",
        measured="닫은 열 8건(FWS-F6-01·02·03·05·06·07·08·10) · 못 닫은 열 2건은 "
                "이유 1줄(F6-04·09) · 분모 10 · [턴 AN · P-392] F6-07 은 웹푸시 훈련 "
                "채널 반쪽을 채우고 title_parts 를 더했다(있으면 강제 · 나머지 "
                "일곱은 레거시라 강제하지 않는다)",
    )
    raise SystemExit(main())
