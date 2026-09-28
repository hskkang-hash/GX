#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-356·357·358·387 — FWS-F1~F5 별표 절 승격 게이트 (WO-GX-20260925-15 §5 · 턴 AK/AL/AM 차선 N2).

무엇을 재는가 — 셋
--------------------
    ① **길목** — `backend/tests/test_fws_app.py`·`test_fws_f2.py`·`test_fws_f5.py`
       를 gx-shell 안에서 **그대로** 돌린다. 판정 규칙(응답 모양·상태 코드·격리)은
       그 시험들이 이미 정했다 — 이 게이트가 다시 만들지 않는다(D-212). 그 시험은
       도는 김에 `docs/agent/evidence/SPEC/<id>.json` 을 **기계로** 새로 찍는다.
    ② **증거 성립** — 방금 찍힌 증거 파일이 「HTTP 로 실제로 두드렸다」는 모양
       (요청·2xx 응답·무엇을 쟀는지)을 갖췄는가. **손으로 옮겨 적은 값이 아닌지**는
       여기서 못 잰다 — 그것은 ①(pytest 가 방금 이 파일을 새로 쓴 것)이 보장한다.
    ③ **절 목록 전수** — FWS-F1-01~15·F2-01~15·F5-01~10 을 전부 찍는다. 닫은 열은
       ①②로, 못 닫은 열은 **「무엇이 없는가」 한 줄**로. 못 닫은 칸을 빈 칸으로
       두지 않는다 — 빈 칸은 「모른다」와 「없다」가 구별되지 않는다(D-274).

    ★ [턴 AM · 차선 N2] F5(드론 운용자) 열 추가 — 세종 판정 P-387(요청·상태·결과
      세 축뿐, 드론 0대)에 따라 F5-01·02·03·08·10 다섯 건을 닫는다. `apps/fws/
      drone.py` 머리말 참조.

무엇을 하지 않는가
------------------
· 대장(`ga_readiness.yaml`) 이동은 이 게이트의 일이 아니다 — P-356 ④는
  `docs/agent/evidence/SPEC/N2_promotions.md` 에 **제안만** 적고, 대장에 실제로
  옮기는 것은 조율자다(대장은 손으로 고치지 않는다 — 세종 판정 그대로).

종료 코드 (저장소 규약 · D-400)
    0 = 쟀고 통과(닫은 열 10/10)   1 = 쟀고 실패   2 = 못 쟀다 (회색)

    python scripts/verify_spec_fws.py                  # 판정 (호스트 — docker 를 부른다)
    python scripts/verify_spec_fws.py --self-test        # 판정 규칙만
    python scripts/verify_spec_fws.py --no-run           # ②③만(pytest 를 다시 안 돌린다 · 빠르다)
    python scripts/verify_spec_fws.py --shell gx-shell   # 컨테이너 이름을 바꿔 잰다

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
#: [턴 AL·AM · 차선 N2] F2·F5 절 시험 파일이 더해졌다 — **세 파일을 한 pytest 호출로
#:   같이 돈다**(TESTS_REL 은 여전히 "길목"의 이름이지만 값은 이제 셋이다). 세 게이트로
#:   가르지 않는 이유: F1·F2·F5 는 같은 App(`apps.fws`)·같은 `AppStaysThinTest` 를
#:   공유하고, 게이트를 여러 개로 가르면 그 공유가 여러 벌로 다시 재진다(D-212).
TESTS_REL = "tests/test_fws_app.py"
TESTS_REL_F2 = "tests/test_fws_f2.py"
TESTS_REL_F5 = "tests/test_fws_f5.py"
TESTS = BACKEND / TESTS_REL
TESTS_F2 = BACKEND / TESTS_REL_F2
TESTS_F5 = BACKEND / TESTS_REL_F5
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"
SHELL_CONTAINER = "gx-shell"
TAG = "[SPEC-FWS]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 닫은 열(P-356 넷을 갖췄다고 이 차선이 주장하는 것) — F1 S 규모 10건 + F2 10건.
CLOSED_CLAUSES: tuple[str, ...] = (
    "FWS-F1-01", "FWS-F1-02", "FWS-F1-03", "FWS-F1-05", "FWS-F1-06",
    "FWS-F1-08", "FWS-F1-10", "FWS-F1-11", "FWS-F1-12", "FWS-F1-13",
    #: [턴 AL · 차선 N2] F2 산림재난대응단·진화대 — S 규모 2건(F2-13·14) +
    #:   K1 표(대응 진행·현장 회신)·K2(F1-10 재사용)·notify-prefs(F1-12 재사용)로
    #:   닫은 M 규모 8건. 새 상태기계·새 표는 세우지 않았다(missions.py 머리말).
    "FWS-F2-01", "FWS-F2-02", "FWS-F2-03", "FWS-F2-05", "FWS-F2-07",
    "FWS-F2-11", "FWS-F2-12", "FWS-F2-13", "FWS-F2-14", "FWS-F2-15",
    #: [턴 AM · 차선 N2] F5 드론 운용자 — 세종 판정 P-387(요청·상태·결과 세 축)로
    #:   닫은 다섯. S 규모 셋(F5-02·03·08) 우선 + 그 위에 자연히 붙는 둘
    #:   (F5-01 요청·상태 축 · F5-10 F5-08 값을 세는 계량). `apps/fws/drone.py`
    #:   머리말 참조 — 새 K1 축을 만들지 않았다(요청은 K1 이벤트를 드론 쪽에서
    #:   본 것, 결과는 F1-06 문 재사용).
    "FWS-F5-01", "FWS-F5-02", "FWS-F5-03", "FWS-F5-08", "FWS-F5-10",
)

#: annex 원문(§5.1) 제목 — `docs/design/FWS_산불감시App_명세서_v1.0_…20260915.md`
#: 표 그대로. 손으로 옮겨 적은 것이지만 **제목 문자열**일 뿐이고 판정에 안 쓴다
#: (판정은 evidence 파일이 한다) — 화면에 사람이 읽을 이름을 대는 용도다.
TITLES: dict[str, str] = {
    "FWS-F1-01": "근무 시작·초소 체크인(NFC/GPS)",
    "FWS-F1-02": "순찰 경로 기록(GPS 트랙 · 전자순찰함 NFC)",
    "FWS-F1-03": "오늘 위험지수·위기경보·입산통제 확인",
    "FWS-F1-04": "계도·단속 기록(소각·흡연·입산 — 사진·위치)",
    "FWS-F1-05": "확인 요청 수신",
    "FWS-F1-06": "현장 확인 회신",
    "FWS-F1-07": "직접 신고(사진·GPS·화세·차량 진입 가능)",
    "FWS-F1-08": "119·산림청 신고 번호 버튼",
    "FWS-F1-09": "초동진화 참여 회신(도착·진화 중·철수)",
    "FWS-F1-10": "안전 알림 수신(풍향 급변·대피 지시·철수)",
    "FWS-F1-11": "내 근무 기록·순찰 실적(일·주)",
    "FWS-F1-12": "근무 외 알림 차단·담당 초소 설정",
    "FWS-F1-13": "오프라인 큐(산지 통신 불가 시 기록 저장 후 전송)",
    "FWS-F1-14": "카메라 사각 신고",
    "FWS-F1-15": "근무 종료·인계(특이사항 한 줄)",
    "FWS-F2-01": "대기 상태 등록(주간·야간 5분대기조·위치)",
    "FWS-F2-02": "임무 수신(출동 지시)",
    "FWS-F2-03": "이동·도착 회신(GPS)",
    "FWS-F2-04": "현장 상황 보고(화선 길이·방향·진화 가능 여부·사진)",
    "FWS-F2-05": "지원 요청(인력·물·헬기·중장비)",
    "FWS-F2-06": "진화선 구축·진화 진행 보고(구간 완료)",
    "FWS-F2-07": "안전 경보 수신(풍향 급변·헬기 투하 구역 이탈)",
    "FWS-F2-08": "주불 진화 보고",
    "FWS-F2-09": "잔불 정리 구역 배정·완료",
    "FWS-F2-10": "뒷불 감시 교대·발견 보고(열점 위치)",
    "FWS-F2-11": "철수·복귀 회신",
    "FWS-F2-12": "내 임무 이력·투입 시간(수당 근거)",
    "FWS-F2-13": "훈련 임무 수신(훈련 배지)",
    "FWS-F2-14": "장비 점검 체크(등짐펌프·진화차)",
    "FWS-F2-15": "근무 외 차단·담당 구역",
    "FWS-F5-01": "정찰 임무 수신(발화 추정 좌표·반경) → 열화상 정찰",
    "FWS-F5-02": "열점·화선 표시(열화상 프레임 → 지도 폴리라인)",
    "FWS-F5-03": "확인 회신(산불 맞음/오인 · 사진·열화상)",
    "FWS-F5-04": "잔불 순회 예약(구역·간격·야간)",
    "FWS-F5-05": "대피 안내 방송(스피커) 임무",
    "FWS-F5-06": "비행 제한(헬기 투입 중 드론 금지 구역 · 고도) 표시·차단",
    "FWS-F5-07": "피해면적 산출(정사영상 → 폴리곤 ha)",
    "FWS-F5-08": "비행 기록·배터리·기체 상태",
    "FWS-F5-09": "영상 스트림 관제 화면 공유",
    "FWS-F5-10": "계량(비행 분)",
}

#: 못 닫은 다섯 — **「무엇이 없는가」 한 줄** (P-358 형식). 이 턴(N2)의 범위 밖인
#: 이유를 각자 적는다. 빈 칸으로 두지 않는다(D-274).
NOT_STARTED: dict[str, str] = {
    "FWS-F1-04": "위치·지도 화면이 필요하다 — §0.4 인접 금지구역(MapForRoute*·"
                "FormRoute.tsx) 밖에서 좌표만 다루는 이번 차선 범위 밖으로 작업지시가 "
                "명시적으로 넘겼다(M 규모 · 04는 위치).",
    "FWS-F1-07": "직접 신고(사진·GPS·화세·차량 진입 가능) — 사진 업로드 저장 경로가 "
                "없다. M 규모라 이번 차선(S 10건 우선)의 시간 안에 못 붙였다.",
    "FWS-F1-09": "초동진화 참여 회신(도착/진화 중/철수 3시각) — F1-06 과 다른 상태기계가 "
                "필요한데 아직 없다. M 규모라 이번 차선 범위 밖.",
    "FWS-F1-14": "카메라 사각 신고 — 신고를 받는 관리자 카드 소비 화면이 없다. "
                "M 규모라 이번 차선 범위 밖.",
    "FWS-F1-15": "근무 종료·인계(특이사항 한 줄) — DSM `handover_service` 재사용 "
                "여지는 확인했으나 실제 엔드포인트를 아직 안 열었다. M 규모라 범위 밖.",
    #: [턴 AL · 차선 N2] 못 닫은 F2 다섯 — 전부 M 규모, 전부 「구간·구역·승인」처럼
    #:   K1 의 4값 대응 진행 표(occurred→acknowledged→in_progress→closed)로는
    #:   담을 수 없는 **새 축**(구간별 진행률·구역 배정·타 역할 승인)이 필요하다.
    #:   그 축은 커널 변경(L3)이라 이 차선(App 층) 권한 밖이다(DA-04 §1-1).
    "FWS-F2-04": "현장 상황 보고(화선 길이·방향·사진) — 사진 업로드 저장 경로가 "
                "없다(F1-07 과 같은 한계). M 규모라 범위 밖.",
    "FWS-F2-06": "진화선 구축·구간 완료 보고 — '구간'은 K1 에 없는 축(진화선을 "
                "여러 구간으로 나눠 각각의 진행을 추적)이라 새 표가 필요하다. "
                "M 규모라 범위 밖.",
    "FWS-F2-08": "주불 진화 보고 — 완결조건이 'F4 승인'(다른 역할의 승인 절차)이고, "
                "그 승인 축은 K1 4값 대응 진행표에 없다. M 규모라 범위 밖.",
    "FWS-F2-09": "잔불 정리 구역 배정·완료 — '구역'별 배정·완료(N/N)를 담을 표가 "
                "없다(F2-06 과 같은 한계 — 구간·구역 축). M 규모라 범위 밖.",
    "FWS-F2-10": "뒷불 감시 교대·발견 보고(열점 위치) — 발견 보고가 '재발화 사건 "
                "연결'을 요구해 새 이벤트 생성 경로가 필요하고, 위치·지도 인접 "
                "주의(F1-04와 같은 한계)도 겹친다. M 규모라 범위 밖.",
    #: [턴 AM · 차선 N2] 못 닫은 F5 다섯 — 전부 App 층 권한 밖의 **새 축**이거나
    #:   (구역·간격 예약·헬기 충돌 규칙·폴리곤 면적·실시간 스트림), 다른 App(DSM ·
    #:   lane N1) 소유 화면을 침범해야 하는 것들이다.
    "FWS-F5-04": "잔불 순회 예약(구역·간격·야간) — '구역'·'간격'(반복 일정)은 K1 "
                "에 없는 축이다(F2-09 와 같은 한계 — 구역 배정). 예약 자체도 미래 "
                "반복 일정을 담을 표가 새로 필요하다. M 규모라 범위 밖.",
    "FWS-F5-05": "대피 안내 방송(스피커) 임무 — 방송 대상 '구역'을 지정하는 축이 "
                "F5-04 와 같은 이유로 없고, 방송 음성·문구 콘텐츠를 담을 저장 "
                "경로도 없다(F1-07 사진 업로드와 같은 한계). M 규모라 범위 밖.",
    "FWS-F5-06": "비행 제한(헬기 투입 중 드론 금지 구역 · 고도) 표시·차단 — "
                "'헬기 투입 중' 상태를 아는 축이 없다(F2-05 지원 요청은 텍스트 "
                "로그일 뿐 실제 헬기 배치 플래그가 아니다). 고도·금지구역 판정도 "
                "새 축이 필요하다. L 규모라 범위 밖.",
    "FWS-F5-07": "피해면적 산출(정사영상 → 폴리곤 ha) — F-03 폴리곤 문(`stream_"
                "monitors.services.zones.save_zone`)은 F-12 관리자 위험구역 지정 "
                "전용이고 면적 계산이 없다(그 모듈 머리말 '없다' 표 — GIS 의존 "
                "없음). 정찰용 피해면적 폴리곤을 받는 새 입력 문이 없다 — F-03 "
                "폴리곤 잠금이 이 용도를 허락하지 않는다(D-299·D-365). M 규모라 "
                "범위 밖.",
    "FWS-F5-09": "영상 스트림 관제 화면 공유 — 실시간 스트림 공유 인프라가 이 "
                "App 층에 없다. DSM 의 클립 스트림(`GET /api/dsm/events/{id}/clip/"
                "stream`)은 다른 App(lane N1) 소유라 이 차선이 새 공유 화면으로 "
                "재사용하지 않았다. M 규모라 범위 밖.",
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
    if not (request.get("path") or "").startswith("/api/fws/"):
        return (EXIT_FAIL,
                "%s — 요청 경로(%r)가 /api/fws/ 가 아니다 — 다른 문을 잰 증거일 수 있다"
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
             "-e", "DB_TEST_NAME=test_gx_verify_spec_fws",
             "-w", "/app", shell,
             "python", "-m", "pytest", TESTS_REL, TESTS_REL_F2, TESTS_REL_F5,
             "-q", "--create-db", "-p", "no:randomly"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            #: ★ `guardianx-lane-count-ceilings` — 공유 gx-shell 은 다른 차선과
            #:   나뉜다. 10분 여유(`verify_password_reset.py` 와 같은 값).
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
        "id": "FWS-F1-01", "measured_at": "2026-09-27T00:00:00+00:00",
        "measured_by": "django_test_client", "test": "tests.test_fws_app.X.y",
        "request": {"method": "POST", "path": "/api/fws/patrol/checkin", "body": {}},
        "response": {"status": 200, "body": {}}, "what": "실측",
    }
    code, _ = judge_evidence("FWS-F1-01", good)
    check("증거 성립 표본 → 초록", code == EXIT_OK)

    code, _ = judge_evidence("FWS-F1-01", None)
    check("증거 파일 없음 → 회색(못 쟀다)", code == EXIT_UNDECIDABLE)

    broken_status = dict(good, response={"status": 500, "body": {}})
    code, _ = judge_evidence("FWS-F1-01", broken_status)
    check("★★ 출생표본 — 응답 500 인 증거 → 빨강(성공을 가장한 실패를 못 잡으면 "
         "이 게이트는 없느니만 못하다)", code == EXIT_FAIL)

    broken_hand = dict(good, measured_by="hand")
    code, _ = judge_evidence("FWS-F1-01", broken_hand)
    check("★ measured_by=hand(손으로 적음) → 빨강", code == EXIT_FAIL)

    broken_path = dict(good, request={"method": "POST", "path": "/api/dsm/x", "body": {}})
    code, _ = judge_evidence("FWS-F1-01", broken_path)
    check("★ 다른 App 경로를 잰 증거 → 빨강", code == EXIT_FAIL)

    broken_id = dict(good, id="FWS-F1-99")
    code, _ = judge_evidence("FWS-F1-01", broken_id)
    check("파일 이름과 id 가 다르면 → 빨강", code == EXIT_FAIL)

    check("combine — 하나라도 빨강이면 빨강", combine([EXIT_OK, EXIT_FAIL]) == EXIT_FAIL)
    check("combine — 빨강 없고 회색 있으면 회색",
         combine([EXIT_OK, EXIT_UNDECIDABLE]) == EXIT_UNDECIDABLE)
    check("combine — 전부 초록이면 초록", combine([EXIT_OK, EXIT_OK]) == EXIT_OK)

    print("%s 자기시험 %d건 실패" % (TAG, fails))
    return EXIT_FAIL if fails else EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="FWS-F1-01~15 별표 절 승격 게이트")
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
        if not TESTS.exists() or not TESTS_F2.exists() or not TESTS_F5.exists():
            print("%s **판정 불가 · 회색** — 길목 시험 파일이 없다: %s · %s · %s"
                 % (TAG, TESTS_REL, TESTS_REL_F2, TESTS_REL_F5))
            return EXIT_UNDECIDABLE
        raw = run_gate_tests(args.shell)
        summary = parse_pytest_summary(raw) if raw is not None else None
        code1, verdict1 = judge_gate_tests(summary)
        codes.append(code1)
        print("%s [입력] 길목 시험 = %s · %s · %s (gx-shell=%s)"
             % (TAG, TESTS_REL, TESTS_REL_F2, TESTS_REL_F5, args.shell))
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
        target="gx-shell(%s) 안 backend/ · apps.fws(신규, `drone` 포함) · K1·K2 커널 · "
               "docs/agent/evidence/SPEC/*.json" % SHELL_CONTAINER,
        as_="pytest 는 자격증명 없이 --create-db 로 돈다 · HTTP 실측은 "
            "tests/test_fws_app.py · tests/test_fws_f2.py · tests/test_fws_f5.py "
            "안에서 실제 JWT(RefreshToken.for_user)로",
        source="살아 있는 gx-shell 컨테이너(docker exec) · 그 실행이 방금 새로 쓴 "
              "evidence 파일 — 사진·손으로 옮긴 값이 아니라 이번 실행",
        measured="닫은 열 25건(F1 10건 FWS-F1-01·02·03·05·06·08·10·11·12·13 + "
                "F2 10건 FWS-F2-01·02·03·05·07·11·12·13·14·15 + F5 5건 "
                "FWS-F5-01·02·03·08·10) · 못 닫은 열 15건은 이유 1줄(F1-04·07·09·"
                "14·15 + F2-04·06·08·09·10 + F5-04·05·06·07·09) · 분모 40",
    )
    raise SystemExit(main())
