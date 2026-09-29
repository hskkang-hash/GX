# -*- coding: utf-8 -*-
"""DSM-U4 규정값 — **숫자·낱말을 이 한 파일에만 둔다** (턴 AM · 차선 N4).

법·지침이 정한 값을 흩어 두면 다음 사람이 어느 것이 정본인지 모른다(D-280 —
값을 지어내지 않는다 · 규정값은 출처 한 줄과 함께 한 곳에). 이 파일에 넣는 값은
전부 `docs/design/DSM_재난안전관리App_명세서_v1.1_지침기반_20260915.md` §4.4
(U4 표) 의 실측 인용이다 — 표에 없는 숫자는 여기 없다(지어내지 않는다).

이 값을 바꾸는 시험 표본 — `backend/tests/test_p356_u4_rest_spec_promotions.py`
의 `RegulationConstantsTest` 가 값 하나마다 「이 값을 고치면 시험이 빨개진다」를
표본으로 남긴다.
"""
from __future__ import annotations

#: 재난문자(CBS) 글자수 상한 — 「90자(안전안내)/157자(긴급·위급)」
#: 출처: 명세서 §4.4 DSM-U4-03 · §「재난문자(CBS)」행(파일 27행) · 행안부
#: 「재난문자방송 기준 및 운영규정」.
CBS_LEN_SAFETY = 90
CBS_LEN_URGENT = 157

#: 재난문자 유형 셋 — 명세서 §「재난문자(CBS)」행 그대로. 글자수는 유형이 정한다.
CBS_KIND_SAFETY = "안전안내"
CBS_KIND_URGENT = "긴급"
CBS_KIND_CRITICAL = "위급"
CBS_KINDS = (CBS_KIND_CRITICAL, CBS_KIND_URGENT, CBS_KIND_SAFETY)

#: 유형별 글자수 상한. 안전안내만 90 — 긴급·위급은 157(표에 두 유형이 157 하나로
#: 묶여 있다 · 지어내지 않는다).
CBS_LEN_LIMIT: dict[str, int] = {
    CBS_KIND_SAFETY: CBS_LEN_SAFETY,
    CBS_KIND_URGENT: CBS_LEN_URGENT,
    CBS_KIND_CRITICAL: CBS_LEN_URGENT,
}

#: 야간(21~06시) 안전안내 자제 — 명세서 §「재난문자(CBS)」행 「야간(21~06시) 안전안내
#: 자제」. **자제이지 금지가 아니다** — 그래서 저장을 막지 않고 경고 칸만 켠다.
CBS_NIGHT_START_HOUR = 21
CBS_NIGHT_END_HOUR = 6

#: 유형별 **표준 문안(자동 생성)** 틀 — 명세서 §4.4 DSM-U4-03 「유형·읍면동 선택 →
#: 표준 문안(자동 생성) → 글자 수 검사」. 턴 AM(N4)이 채우지 못한 반쪽(N4_promotions.md
#: 「표준 문안 자동 생성이 빠졌다」)을 이 턴(AN·N1)이 채운다.
#: `{region}` 자리표시자 하나만 받는다(D-280 — 지어낸 문장을 늘리지 않는다,
#: 정해진 틀에 실측 입력값 하나만 채운다). 사람이 `message` 를 직접 써서 보내면
#: 이 틀 대신 그 글이 그대로 쓰인다 — 이 틀은 **비었을 때의 자동값**이다.
CBS_STANDARD_TEMPLATE: dict[str, str] = {
    CBS_KIND_SAFETY: "[안전안내] {region} 지역 주민께서는 안전에 유의하시기 바랍니다.",
    CBS_KIND_URGENT: "[긴급재난문자] {region} 위험 상황이 발생했습니다. 안내에 따라 행동하시기 바랍니다.",
    CBS_KIND_CRITICAL: "[위급재난문자] {region} 지역은 즉시 대피하시기 바랍니다.",
}

#: 상황보고서(별지 제1호서식) 보고 구분 셋 — 명세서 §「상황보고」행(27행)
#: 「최초 보고 지체 없이 · 중간 보고 … · 최종 보고」.
REPORT_KIND_FIRST = "최초"
REPORT_KIND_INTERIM = "중간"
REPORT_KIND_FINAL = "최종"
REPORT_KINDS = (REPORT_KIND_FIRST, REPORT_KIND_INTERIM, REPORT_KIND_FINAL)

#: 통제·대피 현황판 4시각 — 명세서 §4.4 DSM-U4-04 「도달·결정·실행·해제 4시각」.
CONTROL_STAGE_REACHED = "도달"
CONTROL_STAGE_DECIDED = "결정"
CONTROL_STAGE_EXECUTED = "실행"
CONTROL_STAGE_RELEASED = "해제"
#: 순서가 곧 계약이다 — 뒤 단계는 앞 단계 없이 못 선다(도달 없이 결정 불가 등).
CONTROL_STAGE_ORDER = (CONTROL_STAGE_REACHED, CONTROL_STAGE_DECIDED,
                       CONTROL_STAGE_EXECUTED, CONTROL_STAGE_RELEASED)

#: 4조 3교대 — 명세서 §「관제 인력」행(31행) 「4조 3교대」· §3.1 U1 행(54행)
#: 「4조 3교대(주·야·비번)」.
SHIFT_TEAMS = ("1조", "2조", "3조", "4조")
SHIFT_KINDS = ("주간", "야간", "비번")

#: [턴 AP · 차선 N4] 지역안전지수 6분야 — 행정안전부가 매년 공표하는 지역안전지수
#: (재난 및 안전관리 기본법 §66의2)의 법정 여섯 분야. 명세서 §4.4 DSM-U4-09
#: 「지역안전지수 6분야(화재·범죄·생활안전 …)에 맞춘 유형 분류 열」의 「…」을
#: 채운다 — 공개된 법정 분야명 그대로다(D-280, 지어내지 않는다).
SAFETY_INDEX_FIELDS = ("화재", "교통사고", "범죄", "생활안전", "자살", "감염병")

#: 매핑에 없는 유형이 떨어지는 칸 — 「분류 못 함」을 아무 분야에나 얹지 않는다
#: (D-280, 지어낸 분류를 만들지 않는다).
SAFETY_INDEX_UNCLASSIFIED = "미분류"

#: 이 제품이 아는 `event_type`(카메라 탐지계) → 위 6분야 매핑.
#: ★ 이 제품은 소방·경찰 등록계가 아니라 **카메라 탐지계**라 여섯 분야 전부에
#:   관측 유형이 걸치지 않는다(예: 자살·감염병은 이 카메라들이 탐지하는 축이
#:   아니다 — 지어내지 않고 매핑에서 뺀다). 설비 자신의 신호(`camera_down`·
#:   `storage_high`)는 사람 안전이 아니라 **설비 안전**이라 생활안전에 잠정
#:   분류한다 — 정본 지침에 이 두 유형의 지정이 없어 이 저장소의 분류 판단임을
#:   여기 적는다(값이 아니라 분류이므로 D-280 「값을 지어내지 않는다」의 대상은
#:   아니다 · 분류 자체가 이 절의 완결 조건 「분류 매핑 표」다).
EVENT_TYPE_SAFETY_INDEX: dict[str, str] = {
    "fire": "화재",
    "smoke": "화재",
    "camera_cluster_down": "화재",
    "vehicle": "교통사고",
    "intrusion": "범죄",
    "sos": "범죄",
    "person": "생활안전",
    "flood": "생활안전",
    "camera_down": "생활안전",
    "storage_high": "생활안전",
}
