# -*- coding: utf-8 -*-
"""FWS-F1-05·06 — 확인 요청 수신·현장 확인 회신 (턴 AK 차선 N2).

DSM 커널을 그대로 쓴다 — 새 표를 만들지 않는다
------------------------------------------------
관제가 「이 연기 확인해 주세요」라고 보내는 것은 카메라가 이미 만든 **K1 이벤트**다.
FWS 의 "확인 요청"은 그 이벤트를 현장 사람 눈으로 보는 것이고, "현장 확인 회신"은
그 이벤트에 대한 사람의 판단이다 — 이것은 **K1 이 이미 갖고 있는 두 문**과 정확히
같은 모양이다:

    조회        `kernels.k1_event.services.get_event`     (남의 것이면 404)
    한 줄 회신   `kernels.k1_event.field_reply.reply_from_field`  (누가·언제·무엇을)
    판정 확정    `kernels.k1_event.services.review_event`  (confirmed/rejected)

이 파일이 새로 정하는 것은 **회신의 계약**(결과 3택 + 오인 사유 5택)뿐이다 — 판정과
저장은 전부 K1 에 위임한다(P-357 「DSM 커널을 공유한다」의 실측).
"""
from __future__ import annotations

from kernels.k1_event import reply_from_field  # 커널 공개 면(__init__) — 비공개 모듈 직접 import 금지(D-278)
from kernels.k1_event.exceptions import InvalidEventInput
from kernels.k1_event.services import get_event, review_event

#: 회신 결과 3택 — 명세서 §5.1 FWS-F1-06.
RESULT_FIRE_CONFIRMED = "fire_confirmed"
RESULT_FALSE_ALARM = "false_alarm"
RESULT_CANNOT_ACCESS = "cannot_access"
RESULTS = (RESULT_FIRE_CONFIRMED, RESULT_FALSE_ALARM, RESULT_CANNOT_ACCESS)

#: 「소각·오인」 사유 5택 — 명세서 §5.1 FWS-F1-06 원문 그대로. 여기가 정본이다.
REASON_BURNING = "agri_burning"          # 농산 부산물 소각
REASON_SMOKING = "smoking"               # 흡연
REASON_FOG = "fog_or_cloud"              # 안개·연무·구름
REASON_DUST = "dust_or_steam"            # 공사장 분진·수증기
REASON_OTHER = "other"                   # 기타(직접 기재)
FALSE_ALARM_REASONS = (
    REASON_BURNING, REASON_SMOKING, REASON_FOG, REASON_DUST, REASON_OTHER)


class VerificationReplyRejected(Exception):
    """회신 값이 계약 밖이다 — 422."""


def get_verification(*, scope, verification_id: int) -> dict:
    """FWS-F1-05 — 확인 요청 한 건. **화면 자리에 지도를 두지 않는다**(§0.4 금지구역
    `MapForRoute`/`FormRoute` 밖 — 여기서 나가는 것은 좌표 값뿐이고, 그리는 것은
    화면의 몫이다)."""
    event = get_event(verification_id, scope=scope)
    return {
        "verification_id": event.event_id,
        "requested_action": "이 연기, 확인해 주세요",
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        "snapshot_path": event.snapshot_path,
        "lat": event.lat,
        "lng": event.lng,
        "address": event.address,
        "severity": event.severity,
        "status": event.status,
        "verdict": event.verdict,
    }


def reply_verification(*, scope, verification_id: int, result: str,
                       reason_code: str = "", note: str = "") -> dict:
    """FWS-F1-06 — 현장 확인 회신. 결과가 사건의 판정을 바꾼다(「사건 확정/오인」)."""
    if result not in RESULTS:
        raise VerificationReplyRejected(
            f"result={result!r} 은 회신 결과가 아니다. 허용: {RESULTS}")

    reason_label = ""
    if result == RESULT_FALSE_ALARM:
        if reason_code not in FALSE_ALARM_REASONS:
            raise VerificationReplyRejected(
                f"reason_code={reason_code!r} 는 오인 사유 5택 밖이다. "
                f"허용: {FALSE_ALARM_REASONS}")
        reason_label = f"[{reason_code}] "

    text = f"{result} {reason_label}{note}".strip()
    try:
        reply = reply_from_field(
            scope=scope, event_id=verification_id, text=text)
    except InvalidEventInput as exc:
        raise VerificationReplyRejected(str(exc)) from exc

    verdict = None
    if result == RESULT_FIRE_CONFIRMED:
        verdict = review_event(
            verification_id, verdict="confirmed", reason=text, scope=scope).verdict
    elif result == RESULT_FALSE_ALARM:
        verdict = review_event(
            verification_id, verdict="rejected", reason=text, scope=scope).verdict
    # cannot_access — 판정을 바꾸지 않는다(접근 불가는 「진위」에 대한 답이 아니다).

    return {
        "verification_id": reply.event_id,
        "reply_id": reply.reply_id,
        "result": result,
        "reason_code": reason_code or None,
        "verdict": verdict,
    }
