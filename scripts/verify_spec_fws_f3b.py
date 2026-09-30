#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-356·392·397 — FWS-F3-10~20 별표 절 승격 게이트(산림과 담당 잔여 · 턴 AN 차선 N3).

`scripts/verify_spec_fws_f6.py` 의 **판정식을 그대로 베낀다**(D-212 를 어기지
않는다 — 그 파일은 F6 만, 이 파일은 F3-10~20 만 게이트한다. 판정 함수의 모양이
같은 것은 같은 규칙(P-356)을 재는 것이므로 같은 것이고, 이름이 겹치는 두 파일이
서로를 안 부르는 것은 DA-04 §1-1(게이트는 게이트를 import 하지 않는다)과 같은
결이다).

무엇을 재는가 — 넷(F6 게이트의 셋 + title_parts)
--------------------------------------------------
    ① **길목** — `backend/tests/test_fws_f3b.py` 를 gx-shell 안에서 그대로
       돌린다. 판정 규칙은 그 시험이 이미 정했다(D-212) — 이 게이트가 다시
       만들지 않는다. 그 시험은 도는 김에 `docs/agent/evidence/SPEC/<id>.json`
       을 **기계로** 새로 찍는다.
    ② **증거 성립** — 방금 찍힌 증거 파일 8건이 「HTTP 로 실제로 두드렸다」는
       모양을 갖췄는가(`verify_spec_fws_f6.py::judge_evidence` 와 같은 판정식).
    ③ **title_parts 빈 칸 0**(P-392) — 「제목이 부르는 것 ↔ 있는 것」 표에 빈
       칸이 있으면 반쪽이다 — 반쪽 승격은 이 게이트가 빨강으로 막는다.
    ④ **절 목록 전수** — FWS-F3-10~20 열 11개를 전부 찍는다. 닫은 여덟은
       ①②③으로, 못 닫은 셋(F3-10·15·16)은 **「무엇이 없는가」 한 줄**로(빈
       칸으로 두지 않는다 · D-274).

    ★ [턴 AO 차선 O · WO-18 · 2026-09-29] **FWS-F3-16 을 CLOSED 에서 NOT_STARTED
      로 옮겼다.** 턴 AN(N3)은 이 절을 닫았다고 적었지만(`title_parts` 안 "골든
      타임 준수율" 행이 이미 "근사 실측"이라고 스스로 적어 두었다), 이 턴이
      더한 규약(`docs/agent/checkpoints/turn-ao/_규약.md` "턴 AO 에 더한 것")은
      상태가 `없음`·`부분`·`근사`·`대리`·`대안`·`[미확인]` 로 시작하는 행을
      **열린 행**으로 센다 — 여덟 칸이 실측이어도 한 칸이 열려 있으면 그 절은
      반쪽이다(반쪽은 닫힘이 아니다). 실제 헬기 투하·지상 도달 시각을 저장소에서
      다시 찾아봤다 — `stream_monitors/services/response_clock.py` 가 사건별
      `arrived_at`(현장 도착/조치 착수 전이)을 낸다는 것은 찾았지만, 그것도
      annex 가 부르는 "헬기 투하" 시각은 아니고(그 시각을 담는 자리 자체가 이
      저장소에 없다), office2.py 의 알고리즘을 바꾸는 것은 이 차선(O)의 일이
      아니다(파일 소유는 office2.py 지만 이번 일감은 곁표뿐) — 그래서 지어내지
      않고 열어 둔다. 아래 NOT_STARTED 참고.

무엇을 하지 않는가
------------------
· 대장(`ga_readiness.yaml`) 이동은 이 게이트의 일이 아니다 — 제안만
  `docs/agent/evidence/SPEC/N3_promotions_an.md` 에 적고, 대장에 옮기는 것은
  조율자다.

종료 코드 (저장소 규약 · D-400)
    0 = 쟀고 통과(닫은 열 9/9)   1 = 쟀고 실패   2 = 못 쟀다 (회색)

    python scripts/verify_spec_fws_f3b.py                  # 판정 (호스트 — docker 를 부른다)
    python scripts/verify_spec_fws_f3b.py --self-test        # 판정 규칙만
    python scripts/verify_spec_fws_f3b.py --no-run           # ②③④만(pytest 를 다시 안 돌린다 · 빠르다)
    python scripts/verify_spec_fws_f3b.py --shell gx-shell   # 컨테이너 이름을 바꿔 잰다

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
TESTS_REL = "tests/test_fws_f3b.py"
TESTS = BACKEND / TESTS_REL
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"
SHELL_CONTAINER = "gx-shell"
TAG = "[SPEC-FWS-F3B]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 닫은 여덟(P-356 넷을 갖췄다고 이 차선이 주장하는 것) — F3-10~20 열한 중
#: F3-10·15·16 은 못 닫았다 · 아래 NOT_STARTED(F3-16 은 턴 AO 차선 O 가
#: WO-18 규약으로 다시 갈랐다 — 위 머리말 ★ 참고).
CLOSED_CLAUSES: tuple[str, ...] = (
    "FWS-F3-11", "FWS-F3-12", "FWS-F3-13", "FWS-F3-14",
    "FWS-F3-17", "FWS-F3-18", "FWS-F3-19", "FWS-F3-20",
    #: [턴 AQ · 조율자 창 ② · P-435] 차선 N3 가 헬기 투하 시각 저장(POST/GET
    #: `…/command/incidents/{id}/helicopter-drop` · 지휘 화면 F4-04 자리)과 준수율
    #: (`fire_stats.heli_drop_compliance_pct` · 기관 통계 화면)을 배선 — 대리 지표가 걷혔다.
    #: 증거 `SPEC/FWS-F3-16.retro.md` 9/9 · 시험 `test_aq_n3_screens.FwsF3_16HeliDropScreenTest`.
    "FWS-F3-16",
)

#: annex 원문(§5.3 Table) 제목 — `docs/design/FWS_산불감시App_명세서_v1.0_…
#: 20260915.md` 표 그대로. 손으로 옮겨 적은 것이지만 **제목 문자열**일 뿐이고
#: 판정에 안 쓴다(판정은 evidence 파일이 한다) — 화면에 사람이 읽을 이름을 대는 용도다.
TITLES: dict[str, str] = {
    "FWS-F3-10": "확산예측 결과 등록(산림과학원 결과 이미지/좌표 업로드 또는 API) · "
                "화선 도달 예상 시각 마을별",
    "FWS-F3-11": "대피 초안 — 대상 마을·대피소·문안(CBS 90/157자·마을방송문·"
                "앱 푸시) 자동 → F4 승인 요청",
    "FWS-F3-12": "대피 이행 확인(마을별 완료·잔류자·요양시설)",
    "FWS-F3-13": "매시간 상황보고 초안(발생·위치·면적·진화 현황·인력/장비·인명·"
                "시설·기상) → 승인 → 산림청 입력 항목 내보내기",
    "FWS-F3-14": "진화완료 보고·산불 통계 항목(산불정보ID·원인·면적·문자전송 "
                "여부·일출몰)",
    "FWS-F3-15": "조사반 배정·조사 대장(원인·감식·경찰 합동·피해면적 드론 산출)",
    "FWS-F3-16": "통계 — 발생·면적·원인·시간대·구역·오인율·확인 시간·골든타임 "
                "준수율",
    "FWS-F3-17": "카메라별 오탐률(안개·소각 …)·임계값 시험(K6·QA-12)",
    "FWS-F3-18": "계도·단속 통계 · 입산통제구역 관리",
    "FWS-F3-19": "훈련 시나리오 실행(가상 사건 · 실채널 0)",
    "FWS-F3-20": "온보딩 카드 7(조심기간 전)",
}

#: 못 닫은 셋 — **「무엇이 없는가」 한 줄** (P-358 형식). 빈 칸으로 두지 않는다(D-274).
NOT_STARTED: dict[str, str] = {
    "FWS-F3-10": "확산예측 — 풍향장·지형·연료(임상)를 쓰는 확산예측 모델이나 그 "
                "결과를 낼 산림과학원 외부 API 가 이 차선에 없다. annex 가 스스로 "
                "허락한 대안(「업로드」)도 짓지 않았다 — 업로드 결과(폴리곤·좌표)를 "
                "화면에 놓으려면 좌표 목록이 아니라 지도 오버레이·마을별 화선 "
                "도달 예상 시각 계산이 필요한데, 지도 렌더는 §0.4 인접(MapForRoute·"
                "FormRoute 금지구역)이라 이번 차선이 손대지 않는다. L 규모 · "
                "지어내지 않고 범위 밖으로 남긴다(F6-04 확산예측 미착수와 같은 "
                "이유 — `verify_spec_fws_f6.py` 참고).",
    "FWS-F3-15": "조사반·드론 피해면적 — 조사반 배정(산림청·지자체·경찰 합동) "
                "기록 자체는 지을 수 있었으나, 완결조건이 요구하는 「대장 1」의 "
                "핵심인 **드론 정사영상 폴리곤 피해면적 산출**은 F5(드론 운용자) "
                "의 열점·화선 좌표 기록(`drone.py::submit_hotspots`)과는 다른 "
                "일이다 — 폴리곤 면적 계산은 좌표 목록을 받는 것이 아니라 "
                "그것으로부터 넓이를 셈하는 새 계산이고, 이 차선이 손에 넣은 "
                "산식·검증 표본이 없다(지어내면 D-284 위반). L 규모로 남긴다 — "
                "조율자 지시대로 「하지 않음」 후보.",
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
    if not (request.get("path") or "").startswith("/api/fws/office2/"):
        return (EXIT_FAIL,
                "%s — 요청 경로(%r)가 /api/fws/office2/ 가 아니다 — 다른 문을 잰 "
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
             "-e", "DB_TEST_NAME=test_gx_lane_n3",
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

    good_parts = [{"part": "대상 마을", "where": "응답 drafts[].village",
                  "status": "구현 — 실측"}]
    good = {
        "id": "FWS-F3-11", "measured_at": "2026-09-29T00:00:00+00:00",
        "measured_by": "django_test_client", "test": "tests.test_fws_f3b.X.y",
        "request": {"method": "POST", "path": "/api/fws/office2/evacuations/1/"
                                              "plan", "body": {}},
        "response": {"status": 200, "body": {}}, "what": "실측",
        "title_parts": good_parts,
    }
    code, _ = judge_evidence("FWS-F3-11", good)
    check("증거 성립 표본 → 초록", code == EXIT_OK)

    code, _ = judge_evidence("FWS-F3-11", None)
    check("증거 파일 없음 → 회색(못 쟀다)", code == EXIT_UNDECIDABLE)

    broken_status = dict(good, response={"status": 500, "body": {}})
    code, _ = judge_evidence("FWS-F3-11", broken_status)
    check("★★ 출생표본 — 응답 500 인 증거 → 빨강(성공을 가장한 실패를 못 잡으면 "
         "이 게이트는 없느니만 못하다)", code == EXIT_FAIL)

    broken_hand = dict(good, measured_by="hand")
    code, _ = judge_evidence("FWS-F3-11", broken_hand)
    check("★ measured_by=hand(손으로 적음) → 빨강", code == EXIT_FAIL)

    broken_path = dict(good, request={"method": "POST", "path": "/api/dsm/x", "body": {}})
    code, _ = judge_evidence("FWS-F3-11", broken_path)
    check("★ 다른 App 경로를 잰 증거 → 빨강", code == EXIT_FAIL)

    broken_id = dict(good, id="FWS-F3-99")
    code, _ = judge_evidence("FWS-F3-11", broken_id)
    check("파일 이름과 id 가 다르면 → 빨강", code == EXIT_FAIL)

    no_parts = dict(good, title_parts=[])
    code, _ = judge_evidence("FWS-F3-11", no_parts)
    check("★★ title_parts 비어 있으면 → 빨강(P-392 반쪽 승격을 막는다)",
         code == EXIT_FAIL)

    blank_cell = dict(good, title_parts=[{"part": "대상 마을", "where": "",
                                         "status": "구현"}])
    code, _ = judge_evidence("FWS-F3-11", blank_cell)
    check("★★ title_parts 안 빈 칸 하나 → 빨강", code == EXIT_FAIL)

    check("combine — 하나라도 빨강이면 빨강", combine([EXIT_OK, EXIT_FAIL]) == EXIT_FAIL)
    check("combine — 빨강 없고 회색 있으면 회색",
         combine([EXIT_OK, EXIT_UNDECIDABLE]) == EXIT_UNDECIDABLE)
    check("combine — 전부 초록이면 초록", combine([EXIT_OK, EXIT_OK]) == EXIT_OK)

    print("%s 자기시험 %d건 실패" % (TAG, fails))
    return EXIT_FAIL if fails else EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="FWS-F3-10~20 별표 절 승격 게이트")
    ap.add_argument("--self-test", action="store_true")
    #: ★ 기본은 다시 안 돌린다(`verify_spec_fws_f6.py` 와 같은 이유 — 시험이 증거
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
        target="gx-shell(%s) 안 backend/ · apps.fws.office2(신규) · F1/F2/F5/F6 문 "
              "재사용 · K1·K2 커널 재사용 · docs/agent/evidence/SPEC/*.json" % SHELL_CONTAINER,
        as_="pytest 는 자격증명 없이 --create-db 로 돈다 · HTTP 실측은 "
            "tests/test_fws_f3b.py 안에서 실제 JWT(RefreshToken.for_user)로",
        source="살아 있는 gx-shell 컨테이너(docker exec) · 그 실행이 방금 새로 쓴 "
              "evidence 파일 — 사진·손으로 옮긴 값이 아니라 이번 실행",
        measured="닫은 열 8건(FWS-F3-11·12·13·14·17·18·19·20) · 못 닫은 열 3건은 "
                "이유 1줄(F3-10·15·16 · F3-16 은 턴 AO 차선 O 가 WO-18 규약으로 "
                "옮김) · 분모 11",
    )
    raise SystemExit(main())
