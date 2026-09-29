#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-356·358 — DSM 별표 절 승격 게이트 (WO-GX-20260925-15 §5 · 차선 N1 · 턴 AK 에 서고
턴 AL·AM 이 넓힌다).

무엇을 재는가 — 셋(`scripts/verify_spec_fws.py` 와 같은 그림 · 차선 N2 가 같은
승격 규칙으로 먼저 세운 짝이다 — 두 게이트가 다른 모양이면 다음 사람이 파일마다
다른 눈으로 읽어야 한다)
--------------------------------------------------------------------------------
    ① **길목** — `TESTS_RELS` 의 세 시험 파일(턴 AK 의 U2 셋 · 턴 AL 의 U4-06·U5-02
       둘 · 턴 AM 의 U3-04·U3-03 둘)을 gx-shell 안에서 **한 번에** 돌린다. 판정 규칙
       (응답 모양·상태 코드·격리)은 그 시험들이 이미 정했다 — 이 게이트가 다시 만들지
       않는다(D-212). 그 시험들은 도는 김에 `docs/agent/evidence/SPEC/<id>.json` 을
       **기계로** 새로 찍는다(각 파일의 `EvidenceExportTest`).
    ② **증거 성립** — 방금 찍힌 증거 파일들이 「HTTP 로 실제로 두드렸다」는 모양
       (요청·2xx 응답·무엇을 쟀는지)을 갖췄는가. **손으로 옮겨 적은 값이 아닌지**는
       여기서 못 잰다 — 그것은 ①(pytest 가 방금 그 파일을 새로 쓴 것)이 보장한다.
    ③ **절 목록 전수** — 이 차선에 배정된 DSM 절을 전부 찍는다(턴 AK 11 + 턴 AL 11 +
       턴 AM 7 = 29). 닫은 여덟(U2-03·U2-04·U2-05·U4-06·U5-02·U3-04·U3-03·
       U5-05[턴 AP])은 ①②로, 못 닫은 스물하나는 **「무엇이 없는가」 한 줄**로.
       못 닫은 칸을 빈 칸으로 두지 않는다 — 빈 칸은 「모른다」와 「없다」가
       구별되지 않는다(D-274).

무엇을 하지 않는가
------------------
· 대장(`ga_readiness.yaml`) 이동은 이 게이트의 일이 아니다 — P-356 ④는
  `docs/agent/evidence/SPEC/N1_promotions.md` 에 **제안만** 적고, 대장에 실제로
  옮기는 것은 조율자다(대장은 손으로 고치지 않는다 — 세종 판정 그대로).

종료 코드 (저장소 규약 · D-400)
    0 = 쟀고 통과(닫은 열 8/8)   1 = 쟀고 실패   2 = 못 쟀다 (회색)

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
#: ★ 턴 AL — **둘로 늘었다.** 한 파일이 아니라 파일마다 다른 턴·다른 절이 붙으므로
#:   튜플로 둔다 — `run_gate_tests` 가 한 pytest 호출에 둘 다 넘긴다(요약 줄은 합산).
TESTS_RELS: tuple[str, ...] = (
    "tests/test_p356_u2_spec_promotions.py",     # 턴 AK — DSM-U2-03·04·05
    "tests/test_p356_u4_spec_promotions.py",     # 턴 AL — DSM-U4-06 · DSM-U5-02
    "tests/test_p356_u3u6_spec_promotions.py",   # 턴 AM — DSM-U3-04 · DSM-U3-03
    "tests/test_ap_n3_u5_02_retention.py",       # 턴 AP · N3 — DSM-U5-02 반쪽 채움(P-421 ④)
    "tests/test_ap_n3_u5_05_control_log.py",     # 턴 AP · N3 — DSM-U5-05 반쪽 채움(P-421 ②)
)
TESTS: tuple[Path, ...] = tuple(BACKEND / rel for rel in TESTS_RELS)
EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "SPEC"
SHELL_CONTAINER = "gx-shell"
TAG = "[SPEC-DSM]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 닫은 열(P-356 넷을 갖췄다고 이 차선이 주장하는 것) — 턴 AK 의 S 셋 + 턴 AL 의
#: S 하나(U5-02, 부분 — 아래 TITLES 옆 주석) · M 하나(U4-06, 완결 조건이 "변경 감사"
#: 뿐이라 이번 배정 중 가장 싸다) + 턴 AM 의 S 하나(U3-04) · M 하나(U3-03, 이미 서
#: 있던 사진 업로드·상황보고 조립을 잇기만 해서 가장 싸다 — 지시(WO-15 §5) 「S 먼저,
#: 그다음 가장 싼 M」 순서 그대로).
CLOSED_CLAUSES: tuple[str, ...] = (
    "DSM-U2-03", "DSM-U2-04", "DSM-U2-05", "DSM-U4-06", "DSM-U5-02",
    "DSM-U3-04", "DSM-U3-03",
    #: [턴 AP · 차선 N3 · P-421 ②] DSM-U5-05 — 관제일지 = 인계 메모 + 사건
    #: 타임라인 합본(새 표 0). 남은 두 행("일지 근무자 자동"·"완결조건 일지
    #: 근무자=편성표")을 `handover_service.control_log()` 로 닫았다 — 7/7.
    "DSM-U5-05",
)

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
    # ── 턴 AL 배정(U4 아홉 · U5 둘 = 11) ─────────────────────────────────
    "DSM-U4-01": "재난상황보고서(별지 제1호서식) 작성",
    "DSM-U4-02": "중간 보고 사이클",
    "DSM-U4-03": "재난문자(CBS) 초안",
    "DSM-U4-04": "통제·대피 현황판",
    "DSM-U4-05": "일일상황보고 자동",
    "DSM-U4-06": "위기경보·비상 단계 접수 입력",
    "DSM-U4-07": "영상 열람·제공(반출) 대장",
    "DSM-U4-08": "재난관리평가·감사 자료 묶음",
    "DSM-U4-09": "통계 축 추가 — 지역안전지수 6분야 유형 분류",
    "DSM-U5-02": "접근권한·접속기록",
    "DSM-U5-05": "교대 편성 — 4조 3교대 근무표 업로드(CSV)",
    # ── 턴 AM 배정(U3 넷 · U6 셋 = 7) ─────────────────────────────────────
    "DSM-U3-01": "역할별 M2 문안",
    "DSM-U3-02": "통제 실행 회신",
    "DSM-U3-03": "현장 사진 → 보고서 증빙 자동 첨부",
    "DSM-U3-04": "PS-LTE 그룹통화 번호 · 상황실 번호 버튼",
    "DSM-U6-01": "스마트시티 통합플랫폼 이벤트 연계",
    "DSM-U6-02": "NDMS 입력용 내보내기 API",
    "DSM-U6-03": "사회적약자(실종) 요청 수신 → 객체 검색 사건 생성",
}

#: 이 차선(N1)에 턴 AK 에 배정된 열한 절 중 그 턴에 못 닫은 여덟 — **「무엇이 없는가」
#: 한 줄**(P-358 형식). 빈 칸으로 두지 않는다(D-274). 턴 AL 은 이 여덟을 다시 안
#: 건드렸다(이번 배정 밖) — 그대로 옮겨 둔다.
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

#: ★ 턴 AL — 이번 턴 배정 11(U4-01~09 · U5-02 · U5-05) 중 못 닫은 아홉. U4-06 ·
#: U5-02(부분)는 `CLOSED_CLAUSES` 로 옮겼다. 「가장 싼 것부터」(WO-15 §5) 순서를
#: 그대로 따랐다 — 나머지 아홉은 전부 다단계 워크플로우이거나 새 저장처가 필요한 M
#: 규모다.
NOT_STARTED_AL: dict[str, str] = {
    "DSM-U4-01": "재난상황보고서(별지 1호) — 제N보 채번 · 최초/중간/최종 구분 · "
                "최초 「지체 없이」 타이머가 없다. 기존 `situation_report_docx`(턴 AB) "
                "는 사건 한 건을 지금 그려 내는 **단건 스냅숏**일 뿐 차수·타이머·발송 "
                "이력이 없다 — 다른 절이다.",
    "DSM-U4-02": "중간 보고 사이클 — 08·17시 기준 자동 초안 배치 · NDMS 표 내보내기가 "
                "없다. M 규모(배치 스케줄 + 표 매핑)라 범위 밖.",
    "DSM-U4-03": "재난문자(CBS) 초안 — `POST /cbs-drafts` 자체가 없다(글자수 검사 "
                "90/157 · 승인권자 결재 요청 · 발송 기록 3단계 흐름). M 규모(다단계 "
                "워크플로우)라 이번 차선(가장 싼 것 우선)의 시간 안에 못 붙였다.",
    "DSM-U4-04": "통제·대피 현황판 — 통제 지점 4시각(도달·결정·실행·해제) 저장처가 "
                "없다. M 규모(새 모델 + 일일상황보고 반영 배선)라 범위 밖.",
    "DSM-U4-05": "일일상황보고 자동 — 06:00 자동 배치가 없다. 기존 `monthly_report.py` "
                "의 `KINDS` 는 세 종류로 잠겨 있어(그 파일 머리말) 넷째(daily)를 더하려면 "
                "그 표 자체를 확장해야 한다 — 남의 파일(다른 턴 소유)을 건드리는 변경.",
    "DSM-U4-07": "영상 열람·제공(반출) 대장 — `privacy_request.py` 안에 「제공」· "
                "「반출」·「수사기관」·「공문」 관련 코드가 0건이다(GX-LAW-09 §4 실측 "
                "그대로, 이 문서가 이미 「코드 0줄」로 갈라 뒀다).",
    "DSM-U4-08": "재난관리평가·감사 자료 묶음 — 기간별 ZIP(PDF+CSV) 조립 배치가 없다. "
                "U4-01·02·03·04·07 각 자료가 먼저 갖춰져야 조립할 수 있다(선행 절 의존 "
                "— 그 절들이 이번 배정에도 못 닫혔다).",
    "DSM-U4-09": "통계 축 추가 — `stats?by=safety_index`(지역안전지수 6분야 매핑)가 "
                "없다. 기존 `stats_axes`(턴 T)는 5축(카메라·유형·심각도·판정·시간대)뿐 "
                "이고 6분야 매핑표가 새로 필요하다.",
    #: [턴 AP · 차선 N3] DSM-U5-05 는 이제 CLOSED_CLAUSES 에 있다 — 이 자리에서
    #: 뺐다(스테일 텍스트를 안 남긴다). 근무표 업로드·shifts 저장처는 턴 AO 부터
    #: 이미 있었다(이 문구가 그 뒤로도 낡은 채 남아 있었다 — 실측 없이 옮겨 적힌
    #: 흔적).
}

#: ★ 턴 AM — 이번 턴 배정 7(U3-01·02·03·04 · U6-01·02·03) 중 못 닫은 다섯. U3-04 ·
#: U3-03 은 `CLOSED_CLAUSES` 로 옮겼다. 「S 먼저, 그다음 가장 싼 M」(WO-15 §5) 순서를
#: 그대로 따랐다 — 나머지 다섯은 이 저장소에 **아직 없는 저장처·아예 없는 능력**에
#: 걸려 있어 이번 차선(정직하게 · 지어내지 않고) 시간 안에 못 붙였다.
NOT_STARTED_AM: dict[str, str] = {
    "DSM-U3-01": "역할별 M2 문안 — 「상주 경찰관·119·시설·당직」을 가르는 역할 분류가 "
                "제품에 없다. `role.Role` 은 임의 문자열 코드일 뿐 이 네 갈래를 못박은 "
                "표가 아니다(grep 재확인 · 0건) — 새 분류 칸이 필요해 호스트라인(전화 "
                "번호 둘짜리 U3-04)보다 비싸다. M 규모라 범위 밖.",
    "DSM-U3-02": "통제 실행 회신 — `POST /controls/{id}/executed` 가 받을 「통제 지점」 "
                "자체가 없다. 완결 조건(「도달→결정→실행 3시각」)의 앞 두 시각을 쥔 "
                "DSM-U4-04(통제·대피 현황판)가 이번 배정(N4 소유)에도 아직 미착수라 "
                "— 실행 시각만 먼저 받을 저장처가 없다(선행 절 의존). M 규모.",
    "DSM-U6-01": "스마트시티 통합플랫폼 이벤트 연계 — 외부에서 사건을 **만드는** 문 "
                "자체가 이 저장소에 없다(`POST /events` 수동 생성, DSM-U1-05 와 같은 "
                "벽 — 그 절도 턴 AK 부터 미착수로 남아 있다). CAP 1.2 프로파일 해석은 "
                "그 문이 선 다음의 일이다. M 규모(카메라 연동)지만 선행 절 의존.",
    "DSM-U6-02": "NDMS 입력용 내보내기 API — 별지 1호 13항목 1:1 매핑 JSON/CSV. "
                "L 규모(Table A 실측)로 이번 배정 중 가장 비싸다 — 지시(WO-15 §5) "
                "「S 먼저, 그다음 가장 싼 M」이 이 절을 이번 차선 순서 맨 뒤로 둔다.",
    "DSM-U6-03": "사회적약자(실종) 요청 수신 → 객체 검색 사건 생성 — 「객체 검색」"
                "(용모 기반 재식별 · appearance re-id) 능력이 제품 어디에도 없다"
                "(grep 「객체 검색」·`object_search`·재식별 0건). AI 모델 연동이 선행돼야 "
                "하는 M 규모 절이라 이번 차선 시간 안에 못 붙였다.",
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


#: DSM-U5-02 ④ (P-421 · 턴 AP 차선 N3) — 「값은 선언이 아니라 설정에서 읽는다」.
#: gx-shell 안에서 실제로 두 함수를 불러 대조한다(pytest 를 또 안 돌린다 — settings
#: 만 읽으면 되는 가벼운 확인이라 `docker exec python -c` 하나로 충분하다).
RETENTION_PROBE = (
    "import django, os, json\n"
    "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')\n"
    "django.setup()\n"
    "from common import log_retention_policy as pol\n"
    "from common import ops_tasks as ot\n"
    "declared = pol.enforced_declared_days('audit')\n"
    "seeded = ot.audit_retention_declared_days()\n"
    "print('GX_U5_02_RETENTION ' + json.dumps({'declared': declared, 'seeded': seeded}))\n"
)
RETENTION_MARK = "GX_U5_02_RETENTION "


def run_retention_probe(shell: str) -> dict | None:
    try:
        r = subprocess.run(
            ["docker", "exec", "-e", "DJANGO_SETTINGS_MODULE=config.settings",
             shell, "python", "-c", RETENTION_PROBE],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("%s [입력] 보관기간 탐침을 못 불렀다 — %s" % (TAG, exc))
        return None
    text = (r.stdout or "") + (r.stderr or "")
    for line in text.splitlines():
        if line.startswith(RETENTION_MARK):
            try:
                return json.loads(line[len(RETENTION_MARK):])
            except ValueError:
                return None
    return None


def judge_retention_alignment(facts: dict | None) -> tuple[int, str]:
    """DSM-U5-02 ④ 「선언 == 설정」 1행.

    ⚠ **자기시험이 이 함수를 몸소 망가뜨려 본다**(아래 `self_test`) — 「없으면
      넘긴다」로 흐리면 P-421 ④가 요구하는 게이트 행이 성립하지 않는다.
    """
    if facts is None:
        return EXIT_UNDECIDABLE, "DSM-U5-02 ④ 선언==설정 — 못 쟀다(탐침이 값을 안 냈다)"
    declared, seeded = facts.get("declared"), facts.get("seeded")
    if seeded is None:
        return (EXIT_UNDECIDABLE,
                "DSM-U5-02 ④ 선언==설정 — 이 DB 는 미선언(AdminConfig 빈 칸) — "
                "못 쟀다(선언은 법정 목표 %s일로 안전하게 대체됐다)" % declared)
    if declared == seeded:
        return (EXIT_OK,
                "DSM-U5-02 ④ 선언==설정 — %s일 == %s일(같은 함수가 같은 자리를 "
                "읽는다 — 값은 선언이 아니라 설정에서 읽는다)" % (declared, seeded))
    return (EXIT_FAIL,
            "DSM-U5-02 ④ 선언==설정 — **갈렸다**: 선언 %s일 ≠ 설정 %s일"
            % (declared, seeded))


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
             "python", "-m", "pytest", *TESTS_RELS,
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

    code, _ = judge_retention_alignment({"declared": 365, "seeded": 365})
    check("DSM-U5-02 ④ 선언==설정 — 같으면 초록", code == EXIT_OK)
    code, _ = judge_retention_alignment({"declared": 730, "seeded": 365})
    check("★ DSM-U5-02 ④ 갈리면 빨강(같은 함수를 읽게 고쳐도 이 표본은 갈린 값을 "
         "그대로 줄 수 있어야 한다 — 항등을 시험이 아니라 판정식이 보장하면 "
         "안 된다)", code == EXIT_FAIL)
    code, _ = judge_retention_alignment({"declared": 730, "seeded": None})
    check("DSM-U5-02 ④ 미선언 → 회색", code == EXIT_UNDECIDABLE)
    code, _ = judge_retention_alignment(None)
    check("DSM-U5-02 ④ 탐침 실패 → 회색", code == EXIT_UNDECIDABLE)

    check("combine — 하나라도 빨강이면 빨강", combine([EXIT_OK, EXIT_FAIL]) == EXIT_FAIL)
    check("combine — 빨강 없고 회색 있으면 회색",
         combine([EXIT_OK, EXIT_UNDECIDABLE]) == EXIT_UNDECIDABLE)
    check("combine — 전부 초록이면 초록", combine([EXIT_OK, EXIT_OK]) == EXIT_OK)

    print("%s 자기시험 %d건 실패" % (TAG, fails))
    return EXIT_FAIL if fails else EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="DSM 별표 절 승격 게이트(턴 AK · AL)")
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
        missing = [rel for rel, path in zip(TESTS_RELS, TESTS) if not path.exists()]
        if missing:
            print("%s **판정 불가 · 회색** — 길목 시험 파일이 없다: %s"
                 % (TAG, missing))
            return EXIT_UNDECIDABLE
        raw = run_gate_tests(args.shell)
        summary = parse_pytest_summary(raw) if raw is not None else None
        code1, verdict1 = judge_gate_tests(summary)
        codes.append(code1)
        print("%s [입력] 길목 시험 = %s (gx-shell=%s)" % (TAG, list(TESTS_RELS), args.shell))
        if summary is not None:
            print("%s [입력] pytest 요약 — 통과 %d · 실패 %d · 에러 %d"
                 % (TAG, summary[0], summary[1], summary[2]))
        print("%s %s ① %s" % (TAG, "OK  " if code1 == EXIT_OK else
                              ("FAIL" if code1 == EXIT_FAIL else "GRAY"), verdict1))
        if code1 != EXIT_OK and raw:
            print("%s ── 길목 시험 원문 꼬리 ──\n%s" % (TAG, raw[-3000:]))

        # ④ DSM-U5-02 「선언 == 설정」 1행 (P-421 ④ · 턴 AP N3)
        facts = run_retention_probe(args.shell)
        code4, verdict4 = judge_retention_alignment(facts)
        codes.append(code4)
        print("%s %s %s" % (TAG, "OK  " if code4 == EXIT_OK else
                            ("FAIL" if code4 == EXIT_FAIL else "GRAY"), verdict4))

    # ② 절마다 증거 성립
    all_not_started = {**NOT_STARTED, **NOT_STARTED_AL, **NOT_STARTED_AM}
    print("%s ── 절별 판정 (닫은 열 %d · 못 닫은 열 %d) ──"
         % (TAG, len(CLOSED_CLAUSES), len(all_not_started)))
    for clause_id in CLOSED_CLAUSES:
        payload = _load_evidence(clause_id)
        code, verdict = judge_evidence(clause_id, payload)
        codes.append(code)
        mark = "OK  " if code == EXIT_OK else ("FAIL" if code == EXIT_FAIL else "GRAY")
        print("%s %s [%s] %s — %s" % (TAG, mark, clause_id, TITLES[clause_id], verdict))

    for clause_id in sorted(all_not_started):
        print("%s MISS [%s] %s — 무엇이 없는가: %s"
             % (TAG, clause_id, TITLES[clause_id], all_not_started[clause_id]))

    final = combine(codes)
    denom = len(CLOSED_CLAUSES) + len(all_not_started)  # 29 = 턴 AK 11 + 턴 AL 11 + 턴 AM 7
    print("%s ── 요약 — 닫은 열 %d/%d(분모는 이 차선 배정 %d = 턴 AK 11 + 턴 AL 11 + "
         "턴 AM 7) · 최종 %s ──"
         % (TAG, sum(1 for c in codes[1:] if c == EXIT_OK) if not args.no_run
            else sum(1 for c in codes if c == EXIT_OK),
            len(CLOSED_CLAUSES), denom,
            {EXIT_OK: "PASS", EXIT_FAIL: "FAIL", EXIT_UNDECIDABLE: "GRAY"}[final]))
    return final


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE

    gate_header(
        __file__,
        target="gx-shell(%s) 안 backend/ · apps.dsm.situation_meeting_service · "
              "apps.dsm.threshold_alert_service · apps.dsm.handover_service · "
              "apps.dsm.alert_level_service · apps.dsm.access_log_service · "
              "apps.dsm.audit(access_log_*) · apps.dsm.hotline_service · "
              "apps.dsm.incident_report(_field_photo_count · build_situation_report) · "
              "kernels.k5_trust · docs/agent/evidence/SPEC/*.json" % SHELL_CONTAINER,
        as_="pytest 는 자격증명 없이 --create-db 로 돈다 · HTTP 실측은 "
            "tests/test_p356_u2_spec_promotions.py · "
            "tests/test_p356_u4_spec_promotions.py · "
            "tests/test_p356_u3u6_spec_promotions.py · "
            "tests/test_ap_n3_u5_02_retention.py · "
            "tests/test_ap_n3_u5_05_control_log.py 안에서 실제 JWT"
            "(RefreshToken.for_user)로",
        source="살아 있는 gx-shell 컨테이너(docker exec) · 그 실행이 방금 새로 쓴 "
              "evidence 파일 — 사진·손으로 옮긴 값이 아니라 이번 실행",
        measured="닫은 열 8건(DSM-U2-03·04·05 턴 AK · DSM-U4-06·U5-02 턴 AL · "
                "DSM-U3-04·U3-03 턴 AM · U5-05 턴 AP) · 못 닫은 열 21건은 이유 1줄 "
                "(턴 AK 8 · 턴 AL 8 · 턴 AM 5) · 분모 29(이 차선 N1 배정 턴 AK 11 + "
                "턴 AL 11 + 턴 AM 7)",
    )
    raise SystemExit(main())
