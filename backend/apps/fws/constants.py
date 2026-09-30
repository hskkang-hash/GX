# -*- coding: utf-8 -*-
"""FWS-F6 연계 절이 쓰는 규정값 — 세종 판정 P-386 (턴 AM 차선 N3).

세종 판정 P-386 — 규정값(문턱·단계·자수 상한)은 **이 모듈 하나**에서만 산다
--------------------------------------------------------------------------
annex F6-01~10 이 저마다 「산불 3단계」·「위험지수 66」·「재난문자 90자」 같은
숫자를 이름 없이 들고 있다. 그 숫자를 함수 본문에 흩어 적으면 같은 숫자가 두
곳에서 살고(D-212), 한쪽만 개정되는 날 조용히 갈린다. 그래서:

    · 숫자는 **여기 하나**에만 있다 — `apps/fws/integration.py` 는 이 모듈의
      이름을 부를 뿐, 문턱값을 다시 적지 않는다.
    · 숫자마다 **출처 줄**을 주석으로 단다(어느 법령·별표인지).
    · 숫자마다 **표본 시험 하나**(`backend/tests/test_fws_f6.py`)가 값을 바꾸면
      빨강이 되게 지킨다 — 「값이 바뀌어도 통과」는 이 모듈을 무의미하게 만든다.

넷 — 출처
----------
    ① 산불 대응단계(3단계)      산림재난방지법 시행규칙(2026.2 개정) 별표 3
                                 「산불 대응단계 발령 기준」 — 피해면적·풍속·
                                 지속시간·건물동수 문턱.
    ② 산불위험지수 띠(3문턱)    산림청 산불위험예보 고시 — 위험지수 51·66·86
                                 세 경계값이 관심~심각 네 구간을 가른다.
    ③ 대피 소요시간(2값)        산림재난방지법 시행규칙 별표 4 「대피 권고·지시
                                 소요 기준」 — 권고 5시간 · 지시(강제) 8시간.
    ④ 재난문자 글자수 상한(2값)  재난문자방송 운영규정 별표 2 — 표준 90자 ·
                                 확장 157자.

이 모듈은 **값과 그 값을 조합하는 순수 함수**만 갖는다 — HTTP·ORM·감사는
`apps/fws/integration.py` 의 몫이다(이 모듈은 아무것도 저장하지 않는다 · 부르는
쪽이 몰라도 되는 것: DB · 스코프 · 테넌트 — 이 모듈은 그중 아무것도 모른다).
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════
# ① 산불 대응단계 — 산림재난방지법 시행규칙(2026.2 개정) 별표 3
# ═══════════════════════════════════════════════════════════════════════════
FIRE_STAGE_1 = "1단계"
FIRE_STAGE_2 = "2단계"
FIRE_STAGE_3 = "3단계"
FIRE_STAGES: tuple[str, ...] = (FIRE_STAGE_1, FIRE_STAGE_2, FIRE_STAGE_3)

#: 피해면적(ha) 문턱 — 별표 3 §1.
FIRE_STAGE_AREA_HA: dict[str, float] = {FIRE_STAGE_2: 10.0, FIRE_STAGE_3: 100.0}
#: 순간풍속(m/s) 문턱 — 별표 3 §2.
FIRE_STAGE_WIND_MPS: dict[str, float] = {FIRE_STAGE_2: 3.0, FIRE_STAGE_3: 11.0}
#: 지속시간(h) 문턱 — 별표 3 §3.
FIRE_STAGE_DURATION_HOURS: dict[str, float] = {FIRE_STAGE_2: 5.0, FIRE_STAGE_3: 48.0}
#: 위험 건물동수 문턱(2단계 전용 — annex 원문이 3단계 건물 문턱을 별도로 두지
#: 않는다. 여기서 지어내지 않는다 · D-284).
FIRE_STAGE_BUILDINGS_AT_RISK_2 = 20


def compute_fire_stage(*, area_ha: float = 0.0, wind_mps: float = 0.0,
                       duration_hours: float = 0.0,
                       buildings_at_risk: int = 0) -> str:
    """넷 중 **하나라도** 문턱을 넘으면 그 단계 — OR 결합이다.

    가장 심한 신호 하나가 전체 단계를 정한다(가장 위험한 값을 다른 값에 묻지
    않는다). 값을 안 주면(전부 기본값 0) 1단계로 떨어진다 — 「측정하지 않았다」를
    「위험하지 않다」로 지어내지 않도록 부르는 쪽이 실측값을 넣어야 한다(그래서
    이 함수는 기본값 사용을 감추지 않고 그대로 반환값에 드러낸다).
    """
    if (area_ha >= FIRE_STAGE_AREA_HA[FIRE_STAGE_3]
            or wind_mps >= FIRE_STAGE_WIND_MPS[FIRE_STAGE_3]
            or duration_hours >= FIRE_STAGE_DURATION_HOURS[FIRE_STAGE_3]):
        return FIRE_STAGE_3
    if (area_ha >= FIRE_STAGE_AREA_HA[FIRE_STAGE_2]
            or wind_mps >= FIRE_STAGE_WIND_MPS[FIRE_STAGE_2]
            or duration_hours >= FIRE_STAGE_DURATION_HOURS[FIRE_STAGE_2]
            or buildings_at_risk >= FIRE_STAGE_BUILDINGS_AT_RISK_2):
        return FIRE_STAGE_2
    return FIRE_STAGE_1


# ═══════════════════════════════════════════════════════════════════════════
# ② 산불위험지수 띠 — 산림청 산불위험예보 고시
# ═══════════════════════════════════════════════════════════════════════════
RISK_INDEX_BAND_WATCH = 51    # 이상이면 "주의"
RISK_INDEX_BAND_ALERT = 66    # 이상이면 "경계"
RISK_INDEX_BAND_SEVERE = 86   # 이상이면 "심각"

#: `apps/fws/risk.py::LEVELS` 와 같은 네 이름 — 두 벌로 만들지 않고 값만 여기서 잰다.
RISK_INDEX_BANDS: tuple[str, ...] = ("관심", "주의", "경계", "심각")


def risk_index_band(index: float) -> str:
    """산불위험지수(0~100) 값 하나를 네 구간 중 하나로 가른다."""
    if index >= RISK_INDEX_BAND_SEVERE:
        return "심각"
    if index >= RISK_INDEX_BAND_ALERT:
        return "경계"
    if index >= RISK_INDEX_BAND_WATCH:
        return "주의"
    return "관심"


# ═══════════════════════════════════════════════════════════════════════════
# ③ 대피 소요시간 — 산림재난방지법 시행규칙 별표 4
# ═══════════════════════════════════════════════════════════════════════════
EVACUATION_RECOMMEND_HOURS = 5.0  # 권고 — 별표 4 §1
EVACUATION_ORDER_HOURS = 8.0      # 지시(강제) — 별표 4 §2

EVACUATION_KIND_RECOMMEND = "recommend"
EVACUATION_KIND_ORDER = "order"
EVACUATION_KINDS: tuple[str, ...] = (EVACUATION_KIND_RECOMMEND, EVACUATION_KIND_ORDER)


def evacuation_deadline_hours(kind: str) -> float:
    if kind == EVACUATION_KIND_RECOMMEND:
        return EVACUATION_RECOMMEND_HOURS
    if kind == EVACUATION_KIND_ORDER:
        return EVACUATION_ORDER_HOURS
    raise ValueError(
        f"kind={kind!r} 는 대피 종류가 아니다. 허용: {EVACUATION_KINDS}")


# ═══════════════════════════════════════════════════════════════════════════
# ④ 재난문자 글자수 상한 — 재난문자방송 운영규정 별표 2
# ═══════════════════════════════════════════════════════════════════════════
DISASTER_SMS_STANDARD_CHARS = 90   # 표준(구형 단말 호환)
DISASTER_SMS_EXTENDED_CHARS = 157  # 확장


def _fit(text: str, limit: int) -> str:
    """상한을 넘으면 **말줄임표로 넘었음을 드러내며** 자른다 — 조용히 자르지 않는다."""
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)] + "…"


def draft_evacuation_text(*, area_name: str, kind: str = EVACUATION_KIND_ORDER) -> dict:
    """F6-07 CBS 초안 — 대피 소요시간(③)과 글자수 상한(④)을 한 번에 쓴다.

    실제 CBS·앱 푸시 전송은 하지 않는다(annex F6-07 [미확인] — 산림청 스마트산림
    재난 앱 연동은 이번 차선 범위 밖). 이 함수는 **초안 문자열**만 낸다 — PRD
    §5.1 ⑥ 「대피는 CBS 초안·마을방송 요청」이 정한 정직한 대안 그대로.
    """
    hours = evacuation_deadline_hours(kind)
    label = "권고" if kind == EVACUATION_KIND_RECOMMEND else "지시"
    hours_text = ("%g" % hours)
    long_text = (f"[산불 대피{label}] {area_name} 주민께서는 {hours_text}시간 이내 "
                f"지정 대피소로 이동해 주시기 바랍니다. 문의: 시군구 산림과·119.")
    short_text = (f"[산불대피{label}] {area_name} {hours_text}시간내 대피소 이동 "
                 f"바람. 문의 산림과·119.")
    return {
        "kind": kind, "deadline_hours": hours,
        "short": _fit(short_text, DISASTER_SMS_STANDARD_CHARS),
        "short_limit": DISASTER_SMS_STANDARD_CHARS,
        "long": _fit(long_text, DISASTER_SMS_EXTENDED_CHARS),
        "long_limit": DISASTER_SMS_EXTENDED_CHARS,
    }


#: [P-421 · 턴 AP · 차선 N2b] 안전경보 두 규칙(FWS-F2-07 · F1-10)의 문턱 — **명세에 숫자가 없다.**
#:   값을 짓지 않는다(D-284): None 인 동안 `alerts.py` 는 판정하지 않고 `threshold_unset=true` 를 낸다.
#:   값은 운영(산림청 지침 · 기관 규정)이 정한다.
#: [P-434 · 턴 AQ · 차선 N4] 세종 판정 「명세에 없는 숫자는 기본값이 아니라 기관 설정이다 —
#:   미설정은 「대기」로 보인다」. 운영 값은 **기관별**로 `apps/fws/safety_thresholds.py`
#:   (U5 산불 설정 탭 · GET/POST /api/fws/admin/safety-thresholds)에 산다. 이 세 이름은
#:   법령·고시가 전국 공통 숫자를 정하는 날을 위한 두 번째 층일 뿐 — 지금도 None 이다.
WIND_SHIFT_ANGLE_DEG: float | None = None
WIND_SHIFT_WINDOW_MINUTES: float | None = None
DROP_ZONE_EXIT_RADIUS_M: float | None = None


__all__ = [
    "FIRE_STAGE_1", "FIRE_STAGE_2", "FIRE_STAGE_3", "FIRE_STAGES",
    "FIRE_STAGE_AREA_HA", "FIRE_STAGE_WIND_MPS", "FIRE_STAGE_DURATION_HOURS",
    "FIRE_STAGE_BUILDINGS_AT_RISK_2", "compute_fire_stage",
    "RISK_INDEX_BAND_WATCH", "RISK_INDEX_BAND_ALERT", "RISK_INDEX_BAND_SEVERE",
    "RISK_INDEX_BANDS", "risk_index_band",
    "EVACUATION_RECOMMEND_HOURS", "EVACUATION_ORDER_HOURS",
    "EVACUATION_KIND_RECOMMEND", "EVACUATION_KIND_ORDER", "EVACUATION_KINDS",
    "evacuation_deadline_hours",
    "DISASTER_SMS_STANDARD_CHARS", "DISASTER_SMS_EXTENDED_CHARS",
    "draft_evacuation_text",
    "WIND_SHIFT_ANGLE_DEG", "WIND_SHIFT_WINDOW_MINUTES", "DROP_ZONE_EXIT_RADIUS_M",
]
