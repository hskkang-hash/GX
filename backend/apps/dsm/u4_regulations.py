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
