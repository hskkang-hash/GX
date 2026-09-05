# -*- coding: utf-8 -*-
"""LAW-06 — **다섯 의무의 자리표** (차선 L · 2026-09-05).

대장이 적어 둔 것 그대로
------------------------
    [인용 · ga_readiness.yaml LAW-06] 2026-01-22 시행 · 고영향 AI 11분야에 **공공안전**
    포함 · 계도기간 1년+. 다섯 중 넷은 제품 안에 조각이 이미 있다(월간 오탐률 ·
    규칙 판정 근거 표시 · 사람 확인 없는 외부 전파 0 · 알림 예산). **없는 것은 그것을
    다섯으로 묶어 적은 자리와 사전 고지 문구**다.

이 파일이 그 「묶어 적은 자리」다. 그리고 그 이상은 하지 않는다.

★ 이 파일이 **하지 않는 것** — 법을 해석하지 않는다
---------------------------------------------------
다섯 의무의 **이름**은 대장이 적은 그대로 쓴다(위험관리 · 설명가능성 · 이용자보호 ·
사람감독 · 문서화). 조문 번호도, 각 의무가 요구하는 상세도 여기서 지어내지 않는다 —
이 저장소는 LAW-02 · LAW-03 을 「법률 대조 대기」로 **미측정**에 두고 있고, 여기도 같다.
`legal_review_pending` 이 그 사실을 응답에 싣는다.

★ 이 파일이 **하는 것** — 「어디에 사는가」를 잰다
--------------------------------------------------
의무마다 제품 안의 **실제 자리**(모듈·함수·상수)를 이름으로 적고, 그 이름이
**진짜 있는지 import 로 확인한다.** 적어만 두면 그 표는 리팩터링 한 번에 조용히
낡고, 낡은 자리표는 「있다」고 말하면서 아무것도 안 가리킨다 — 그것이 이 저장소가
착시 ⑥(스키마의 착시)이라고 부르는 모양이다.

★ **빈칸과 「없음」은 다르다** (D-290 · D-301)
---------------------------------------------
다섯 칸은 **언제나 다섯 개다.** 아직 자리가 없는 의무는 칸을 지우는 것이 아니라
`present=False` + **왜 없는지**로 남는다. 칸을 지우면 「그 의무가 없다」와
「그 의무를 아직 안 했다」가 같은 그림이 된다.

★ 지금 실측으로 비어 있는 칸 하나 — **모델 기술문서**
------------------------------------------------------
문서화 의무의 자리 셋 중 둘(감사 전건 · 해시 체인)은 실재하고, 셋째인
**AI 모델 자체의 기술문서**(학습 데이터 · 성능 · 한계)는 이 저장소에 없다
[실측 2026-09-05 · `grep -rl "모델 카드" docs/ backend/` = 0건 — 나온 1건은 VLM
후보 조사 메모이지 우리 모델의 문서가 아니다]. 그 사실을 표가 그대로 말한다.
"""
from __future__ import annotations

import importlib
from typing import Any

from common.ai_act_notice import (
    NOTICE_BODY,
    NOTICE_SURFACES,
    NOTICE_TITLE,
    notice_line,
)

#: 다섯 의무의 **순서와 이름**. 대장(ga_readiness.yaml LAW-06 제목)이 적은 그대로다.
#: ⚠ 여기서 이름을 늘리거나 줄이지 않는다 — 다섯이 아닌 자리표는 자리표가 아니다.
DUTY_NAMES: tuple[str, ...] = (
    "위험관리", "설명가능성", "이용자보호", "사람감독", "문서화",
)

#: 대장이 인용한 사실. **우리가 조문을 읽고 적은 것이 아니다** — 대장에서 옮긴다.
LEDGER_QUOTE: str = (
    "2026-01-22 시행 · 고영향 AI 11분야에 공공안전 포함 · 계도기간 1년+"
)

#: ★ 법률 검토가 필요한 자리. 이 값이 참인 동안 이 표는 **배선**이지 준법 판정이 아니다.
LEGAL_REVIEW_PENDING: bool = True
LEGAL_REVIEW_NOTE: str = (
    "조문 대조 전이다. 이 표가 말하는 것은 「우리 제품의 어디가 이 의무에 닿는가」이고, "
    "「그 자리가 법이 요구하는 수준인가」는 법률대리인의 판정이다. "
    "LAW-02 · LAW-03 을 미측정에 둔 것과 같은 정직이다."
)


# ═══════════════════════════════════════════════════════════════════════════
# 자리 하나를 **실제로 찾아본다**
# ═══════════════════════════════════════════════════════════════════════════
def _resolve(target: str) -> dict[str, Any]:
    """`"module:attr"` 또는 `"module"` 이 실재하는가. **없으면 없다고 적는다.**

    import 로 확인한다 — 파일 존재로 묻지 않는 이유: 이름이 바뀌어도 파일은 남고,
    남은 파일은 「있다」로 읽힌다.
    """
    module_name, _, attr = target.partition(":")
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:                                   # noqa: BLE001
        return {"target": target, "present": False,
                "why_not": f"{module_name} 를 가져오지 못했다: "
                           f"{type(exc).__name__}: {exc}"[:200]}
    if attr and not hasattr(module, attr):
        return {"target": target, "present": False,
                "why_not": f"{module_name} 에 {attr} 가 없다"}
    return {"target": target, "present": True, "why_not": None}


#: 의무 → 그 의무가 사는 자리들. **이름으로 적고 위에서 실제로 찾는다.**
#:
#: ⚠ 여기에 이름을 더하는 것은 「이 코드가 그 의무를 감당한다」는 선언이다.
#:   감당하지 않는 것을 적으면 이 표가 곧 거짓 고지가 된다 — 조심해서 더하라.
DUTY_ANCHORS: dict[str, tuple[dict[str, str], ...]] = {
    "위험관리": (
        {"what": "알림 예산 — 사람이 감당할 수 있는 시간당 경보 수를 재고 넘으면 말한다",
         "target": "kernels.k2_notify.alarm_budget:simulate_alarm_budget"},
        {"what": "월간 오탐률 — 판정이 얼마나 틀렸는지를 분모와 함께 센다",
         "target": "kernels.k6_feedback:false_positive_rate"},
        {"what": "임계값 — 위험 기준을 값 없이 추측하지 않는다(없으면 멈춘다)",
         "target": "kernels.k5_trust:resolve_threshold"},
    ),
    "설명가능성": (
        {"what": "등급 판정 규칙 — 이 사건이 왜 이 등급인가",
         "target": "kernels.k5_trust:severity_for"},
        {"what": "규칙 표 — 사람이 읽을 수 있는 판정 근거 목록",
         "target": "kernels.k5_trust:list_grade_rules"},
    ),
    "이용자보호": (
        {"what": "원본 영상 무반출 잠금 — 바이트가 나가는 길이 잠겨 있다",
         "target": "stream_monitors.services.clips:CLIP_EXTRACTION_READY"},
        {"what": "스냅샷 소인 — 나간 1장에 누가 언제 열람했는지가 남는다",
         "target": "apps.dsm.watermark:stamp"},
        {"what": "열람·삭제 청구 접수 — 정보주체가 물을 자리",
         "target": "apps.dsm.privacy_request:accept"},
    ),
    "사람감독": (
        {"what": "진위 판정 — 자동 판정 후보를 사람이 확정한다",
         "target": "apps.dsm.services:review_event"},
        {"what": "대응 단계 — 사람이 올린다(자동으로 올라가지 않는다)",
         "target": "apps.dsm.services:advance_response"},
        {"what": "사전 고지 문구 — 사람이 최종 확인한다는 사실을 읽는 자리에서 말한다",
         "target": "common.ai_act_notice:NOTICE_BODY"},
    ),
    "문서화": (
        {"what": "설정 변경 전건 감사 — 성공도 실패도 남는다",
         "target": "apps.dsm.audit:record"},
        {"what": "증거 해시 체인 — 남은 기록을 뒤에서 조용히 못 고친다",
         "target": "common.evidence_chain:daily_anchor"},
        #: ★ 이 자리는 **없다.** 지우지 않고 남겨 「없음」으로 말하게 한다.
        {"what": "AI 모델 기술문서 — 학습 자료 · 성능 · 한계를 적은 자리",
         "target": "apps.dsm.model_card:MODEL_CARD"},
    ),
}


def duty_table() -> dict[str, Any]:
    """다섯 의무 자리표. **다섯 칸이 언제나 다섯 칸이다.**

    각 칸은 「어디에 사는가」를 이름으로 가리키고, 그 이름이 실재하는지 잰다.
    한 자리도 못 찾은 의무는 `present=False` 이고 `gap` 에 사유가 찬다.
    """
    duties = []
    for name in DUTY_NAMES:
        anchors = [
            {**anchor, **_resolve(anchor["target"])}
            for anchor in DUTY_ANCHORS.get(name, ())
        ]
        found = [a for a in anchors if a["present"]]
        missing = [a for a in anchors if not a["present"]]
        duties.append({
            "duty": name,
            "anchors": anchors,
            #: 한 자리라도 실재하면 「닿는 자리가 있다」이다. **전부 있다는 뜻이 아니다** —
            #: 그래서 `missing` 을 함께 낸다. 세지 않은 것을 초록으로 적지 않는다.
            "present": bool(found),
            "anchor_count": len(anchors),
            "found_count": len(found),
            "gap": None if not missing else
                   " · ".join(f"{a['what']}: {a['why_not']}" for a in missing),
        })

    empty = [d["duty"] for d in duties if not d["present"]]
    partial = [d["duty"] for d in duties if d["present"] and d["gap"]]
    return {
        "duties": duties,
        "duty_count": len(duties),
        #: ★ 자리가 **하나도 없는** 의무. 0건이 아니면 이 표는 「닿는다」고 말할 수 없다.
        "duties_without_any_anchor": empty,
        #: 자리가 일부만 있는 의무. **빈칸이 아니라 「일부 없음」이다.**
        "duties_with_gaps": partial,
        "notice": {
            "title": NOTICE_TITLE,
            "body": NOTICE_BODY,
            "line": notice_line(),
            "surfaces": list(NOTICE_SURFACES),
        },
        "ledger_quote": LEDGER_QUOTE,
        "legal_review_pending": LEGAL_REVIEW_PENDING,
        "legal_review_note": LEGAL_REVIEW_NOTE,
        "status": "배선 — 법률 검토 전 (대장 상태는 조율자가 정한다)",
    }
