#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-356·P-376 — OPS annex O-01·02·05~12 승격 게이트. 차선 O(턴 AM) 가 O-10·O-04
로 세웠고, 차선 N3(턴 AO · WO-18)가 **여덟을 더 얹었다**(O-01·02·06·07·08·09·11·12).
`scripts/verify_spec_fws.py` 의 구조를 그대로 베낀다(D-212 —
판정 모양은 한 곳에서 정한다. 분모가 다를 뿐 셋·짝·자기시험은 같다).

★ [턴 AO · 차선 N3] 경로 접두어를 고친다 — **`/api/ops/` 가 아니라 `/api/dsm/ops/`**
----------------------------------------------------------------------------------
턴 AM 은 "OPS 앱이 서는 날을 위한 자리"라며 `judge_evidence` 에 `/api/ops/` 를
박아 뒀다(그 날 아직 OPS 앱이 없어 `CLOSED_CLAUSES` 가 비어 있었다). 이번 턴
실측하니 파일 소유 규약이 이미 정해 둔 자리는 `backend/apps/dsm/api_ops_an.py`
— 즉 라우트는 `dsm_api`(`/api/dsm/` 로 mount) 아래 `/ops/...` 다. 새 OPS 전용
Django app 을 세우는 일은 이 턴의 몫이 아니었다(파일 소유가 이미 `apps/dsm` 을
가리켰다). 그래서 실제 경로는 `/api/dsm/ops/...` 이고, 판정식을 **실재에 맞춘다**
(지어낸 계획에 실재를 맞추지 않는다 — D-284 계열).

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
#: 턴 AM 의 길목(O-10·O-04 조사 기록 — 지금도 0건 통과라 CLOSED 가 없다).
TESTS_REL = "tests/test_p356_ops_spec_promotions.py"
TESTS = BACKEND / TESTS_REL
#: [턴 AO · 차선 N3] 여덟을 닫는 길목 — 실제 HTTP 왕복(django_test_client).
TESTS_REL_N3 = "tests/test_ops_an.py"
TESTS_N3 = BACKEND / TESTS_REL_N3
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"
SHELL_CONTAINER = "gx-shell"
TAG = "[SPEC-OPS]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 닫은 열 — 턴 AM 은 비웠다(O-10·O-04). 턴 AO · 차선 N3 가 **여덟을 얹는다.**
#: 새 DB 모델 0(감사 스냅샷 재사용) · dj-core 는 읽기·호출만(`backend/apps/dsm/
#: ops_an_service.py` 머리말 참조) — 각 절의 `docs/agent/evidence/SPEC/O-*.json`
#: 의 `title_parts` 가 "제목이 부르는 것 ↔ 있는 것" 표를 낸다.
CLOSED_CLAUSES: tuple[str, ...] = (
    "O-01", "O-02", "O-05", "O-06", "O-07", "O-08", "O-09", "O-12",
)

#: annex 원문(플랫폼 구조설계서 §7) 제목 — 판정에는 안 쓴다(사람이 읽을 이름표).
TITLES: dict[str, str] = {
    "O-01": "테넌트 발급 — 테넌트(시군구) 생성 · 계층 · 초기 관리자 1 · 도메인·인증서 · "
           "공개 URL",
    "O-02": "앱 설치·버전 — 테넌트에 앱 설치·업그레이드·비활성 · 시드 소유권 · 유령 "
           "시드 정리",
    "O-05": "건강 보드(전 테넌트) — 완결조건: 테넌트 수 = 보드 행 수 · 빨강 → "
           "인시던트 자동 생성",
    "O-06": "인시던트 — 접수(테넌트·앱·심각도) → 1차 대응(4영업시간) → 에스컬레이션"
           "(1영업일) → 종결·원인",
    "O-07": "백업·복구 — 테넌트별 덤프·회수증 · 복원 시험 · 다른 호스트 목적지",
    "O-08": "온보딩 관제 — 테넌트별 D-7~D+30 진행 · 역할별 진행률 6/6 · 48행 재측 "
           "결과 · 막힌 카드",
    "O-09": "감사(플랫폼) — 운영자 행위 전건 · 테넌트 감사 열람은 요청·승인 뒤",
    "O-10": "키·자격 회전 — API 키 · 서명키 · DB/MinIO 자격 · VAPID · 회전 주기 · "
           "재생성 창 runbook",
    "O-11": "릴리스·배포 — 릴리스 트레인 · 테넌트별 단계 배포(카나리 1 → 전체) · "
           "되돌리기 · 배포 창",
    "O-12": "시드·훈련 데이터 — 테넌트에 검수 시드 심기·숨기기 · 훈련 시나리오 배포",
    "O-04": "모델 레지스트리 — 모델 버전·앱 태그·테넌트 배포·롤백 · 카메라별 바인딩 "
           "현황 · 성능(오탐률)",
}

#: 못 닫은 것들 — **「무엇이 없는가」**(P-358·P-376 형식). 빈 칸으로 두지 않는다(D-274).
NOT_STARTED: dict[str, str] = {
    "O-11": "완결 조건은 3항 AND 다(「deploy.sh exit 0 · 걷기 초록 · 되돌리기 1회 "
           "시험」). 앞 둘은 이미 있는 장부(`docs/agent/evidence/OPS-27/"
           "deploys.jsonl`)를 그대로 읽어 실측한다(`GET /api/dsm/ops/releases` · "
           "`tests/test_ops_an.py::O11_ReleaseBoardSmokeTest`). **되돌리기 1회 "
           "시험만 없다** — 실제 배포 되돌리기(파일 스왑·컨테이너 재시작)는 HTTP "
           "라운드트립 시험이 아니라 운영 집행이고, `deploys.jsonl` 에도 되돌리기 "
           "항목이 0건이라(grep 0) 이미 있는 장부를 읽는 방식으로도 못 잰다. 반쪽"
           "(3항 중 2항)이라 승격하지 않는다(P-417).",
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
           "이 흩어짐과 구조적 한계를 실측으로 고정한다. [턴 AO · 차선 N3 덧붙임] "
           "콘솔 문은 이번 턴 하나 열었다 — `GET /api/dsm/ops/keys`(회전 대상 보드"
           " · `docs/agent/evidence/D-373/key_rotation_last.json` 읽기) · "
           "`POST /api/dsm/ops/keys/rotate`(`kernels.k5_trust.inbound_keys."
           "rotate_key` 그대로 재사용). 그러나 앞 반(라이브 로그인 재검증)은 여전히 "
           "이 저장소 규칙이 막아 결론은 바뀌지 않는다 — `tests/test_ops_an.py::"
           "O10_KeyRotationSmokeTest` 가 그 자백(`gray_why`)이 응답에 실제로 실려 "
           "있는지만 스모크로 확인한다(승격은 안 한다).",
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


#: [턴 AO §0.4 규약 · P-417] 닫힘으로 세는 `status` 접두어 — 이 밖의 값은 **열린
#: 행**이다(반쪽). `excluded_by`(결정 번호) + `excluded_why` 가 있으면 그 행은
#: 예외로 닫힘(P-406).
_CLOSING_STATUS_PREFIXES = ("measured", "present", "있음", "구현 — ", "구현—")
_OPEN_STATUS_PREFIXES = ("없음", "부분", "missing", "[미확인]", "대안", "근사", "대리")


def _title_part_closed(part: dict) -> tuple[bool, str]:
    if part.get("excluded_by") and (part.get("excluded_why") or "").strip():
        return True, "excluded_by=%s" % part["excluded_by"]
    status = (part.get("status") or "").strip()
    if not status:
        return False, "status 칸이 비었다"
    if any(status.startswith(p) for p in _OPEN_STATUS_PREFIXES):
        return False, "status=%r 는 열린 행이다" % status
    if any(status.startswith(p) for p in _CLOSING_STATUS_PREFIXES):
        return True, "status=%r" % status
    #: 그 밖의 값(예: "measured — 대체 경로") — `measured` 로 시작하면 위에서 이미
    #: 잡혔으므로 여기는 분류 밖 문자열이다. 안전하게 **연 것으로** 본다(D-274 —
    #: 모르면 닫힘이라 말하지 않는다).
    return False, "status=%r 를 분류 못 했다 — 열린 행으로 본다" % status


def judge_title_parts(clause_id: str, payload: dict | None) -> tuple[int, str]:
    """★ P-356 ② — 「제목이 부르는 것 ↔ 있는 것」 표가 **빈 칸 없이** 다 닫혔는가.

    턴 AO §0.4 규약: "증거 안에 title_parts 표가 있어야 한다 — O 게이트가 빈 칸을
    센다." 이 함수가 그 셈이다. 열린 행이 하나라도 있으면 그 절은 반쪽이다.
    """
    if payload is None:
        return EXIT_UNDECIDABLE, "%s — 증거 파일이 없다(못 쟀다)" % clause_id
    parts = payload.get("title_parts")
    if not parts:
        return EXIT_FAIL, "%s — title_parts 표가 없다(P-356 ② 위반)" % clause_id
    open_rows = []
    for part in parts:
        ok, why = _title_part_closed(part)
        if not ok:
            open_rows.append("%s(%s)" % (part.get("part", "?"), why))
    if open_rows:
        return EXIT_FAIL, "%s — 반쪽(열린 행 %d): %s" % (clause_id, len(open_rows), "; ".join(open_rows))
    return EXIT_OK, "%s — title_parts %d행 전부 닫힘" % (clause_id, len(parts))


def judge_evidence(clause_id: str, payload: dict | None) -> tuple[int, str]:
    """이 절의 증거 한 건이 「HTTP 로 실제로 두드렸다」는 모양을 갖췄는가.

    ★ `verify_spec_fws.py::judge_evidence` 와 판정식이 같다. [턴 AO · 차선 N3]
      경로 접두어를 실재에 맞춰 `/api/dsm/ops/` 로 고쳤다(머리말 참조 — 턴 AM 이
      박아 둔 `/api/ops/` 는 그 날 아직 없던 앱을 가정한 자리였다).
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
    if not (request.get("path") or "").startswith("/api/dsm/ops/"):
        return (EXIT_FAIL,
                "%s — 요청 경로(%r)가 /api/dsm/ops/ 가 아니다 — 다른 문을 잰 증거일 수 있다"
                % (clause_id, request.get("path")))
    tp_code, tp_verdict = judge_title_parts(clause_id, payload)
    if tp_code != EXIT_OK:
        return tp_code, tp_verdict
    return EXIT_OK, "%s — 증거 성립(2xx · %s %s · %s)" % (
        clause_id, request.get("method"), request.get("path"), tp_verdict)


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
             #: [턴 AO · 차선 N3] 둘 다 돈다 — 턴 AM 의 길목(O-10·O-04, 여전히 0
             #: 통과) + 이 턴의 길목(여덟을 닫는 실제 HTTP 왕복).
             "python", "-m", "pytest", TESTS_REL, TESTS_REL_N3,
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
        "request": {"method": "POST", "path": "/api/dsm/ops/keys/rotate", "body": {}},
        "response": {"status": 200, "body": {}}, "what": "실측",
        "title_parts": [{"part": "회전", "where": "keys/rotate", "status": "measured"}],
    }
    code, _ = judge_evidence("O-10", good)
    check("증거 성립 표본 → 초록", code == EXIT_OK)

    code, _ = judge_title_parts("O-10", good)
    check("title_parts 전부 닫힘 → 초록", code == EXIT_OK)
    code, _ = judge_title_parts("O-10", dict(good, title_parts=[
        {"part": "회전", "where": "x", "status": "없음 — 아직"}]))
    check("★ title_parts 에 열린 행 하나 → 빨강(반쪽을 닫힘으로 안 올린다)", code == EXIT_FAIL)
    code, _ = judge_title_parts("O-10", dict(good, title_parts=[
        {"part": "회전", "where": "x", "status": "없음", "excluded_by": "P-999",
         "excluded_why": "결정으로 뺐다"}]))
    check("excluded_by + excluded_why 있으면 열린 행이어도 닫힘(P-406)", code == EXIT_OK)
    code, _ = judge_title_parts("O-10", dict(good, title_parts=[]))
    check("title_parts 빈 목록 → 빨강", code == EXIT_FAIL)
    code, _ = judge_title_parts("O-10", None)
    check("title_parts 판정 — 증거 자체가 없으면 회색", code == EXIT_UNDECIDABLE)

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
    ap = argparse.ArgumentParser(
        description="OPS O-01·02·05~12(N3)·O-10·O-04(O) 별표 절 승격 게이트")
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
             "파일만 본다)" % TAG)
    else:
        missing_tests = [str(p) for p in (TESTS, TESTS_N3) if not p.exists()]
        if missing_tests:
            print("%s **판정 불가 · 회색** — 길목 시험 파일이 없다: %s"
                 % (TAG, ", ".join(missing_tests)))
            return EXIT_UNDECIDABLE
        raw = run_gate_tests(args.shell)
        summary = parse_pytest_summary(raw) if raw is not None else None
        code1, verdict1 = judge_gate_tests(summary)
        codes.append(code1)
        print("%s [입력] 길목 시험 = %s · %s (gx-shell=%s)"
             % (TAG, TESTS_REL, TESTS_REL_N3, args.shell))
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
    print("%s ── 요약 — 닫은 열 %d/%d(분모 = annex 배정 %d건) · 최종 %s ──"
         % (TAG, closed_n, len(CLOSED_CLAUSES) + len(NOT_STARTED),
            len(CLOSED_CLAUSES) + len(NOT_STARTED),
            {EXIT_OK: "PASS", EXIT_FAIL: "FAIL", EXIT_UNDECIDABLE: "GRAY"}[final]))
    return final


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE

    gate_header(
        __file__,
        target="gx-shell(%s) 안 backend/tests/test_p356_ops_spec_promotions.py · "
               "backend/tests/test_ops_an.py · apps.dsm.ops_an_service · "
               "kernels.k5_trust(inbound_keys·webhook_signing_keys·credentials) · "
               "scripts/rotate_shared_passwords.py · docs/agent/evidence/SPEC/*.json"
               % SHELL_CONTAINER,
        as_="pytest 는 자격증명 없이 --create-db 로 돈다 · 라이브 서버 로그인은 이번 "
            "게이트가 하지 않는다(차선 공통 규칙 금지) — O-10·O-11 완결 조건의 "
            "라이브 절반이 바로 이 이유로 못 닫힌다",
        source="살아 있는 gx-shell 컨테이너(docker exec, `--run` 일 때만) · 정적으로는 "
              "저장소의 kernels·scripts 소스 그 자체(전수 grep — 사진·손으로 옮긴 값 "
              "아님)",
        measured="닫은 열 %d건(O-01·02·05·06·07·08·09·12) · 못 닫은 열 %d건"
                "(O-10·O-11·O-04) — 분모 %d, `docs/agent/evidence/SPEC/"
                "N3_promotions_ao.md` 의 「무엇이 없는가」 표와 일치"
                % (len(CLOSED_CLAUSES), len(NOT_STARTED),
                   len(CLOSED_CLAUSES) + len(NOT_STARTED)),
    )
    raise SystemExit(main())
