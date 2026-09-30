# -*- coding: utf-8 -*-
"""FWS-F1-05·06 — 확인 요청 수신·현장 확인 회신 (턴 AK 차선 N2).

DSM 커널을 그대로 쓴다 — 새 표를 만들지 않는다
------------------------------------------------
관제가 「이 연기 확인해 주세요」라고 보내는 것은 카메라가 이미 만든 **K1 이벤트**다.
FWS 의 "확인 요청"은 그 이벤트를 현장 사람 눈으로 보는 것이고, "현장 확인 회신"은
그 이벤트에 대한 사람의 판단이다 — 이것은 **K1 이 이미 갖고 있는 두 문**과 정확히
같은 모양이다:

    조회        `apps.dsm.services.event_detail` → K1 `get_event`     (남의 것이면 404)
    한 줄 회신   `apps.dsm.services.field_reply` → K1 `reply_from_field`  (누가·언제·무엇을)
    판정 확정    `apps.dsm.services.review_event` → K1 `review_event`  (confirmed/rejected)

이 파일이 새로 정하는 것은 **회신의 계약**(결과 3택 + 오인 사유 5택)뿐이다 — 판정과
저장은 전부 K1 에 위임한다(P-357 「DSM 커널을 공유한다」의 실측).
"""
from __future__ import annotations

#: ★ [턴 AK · 조율자 병합] K1 을 직접 부르지 않는다 — F-05 「진입면 하나」는 **K1 의 App 소비자가
#:   `apps/dsm/services.py` 하나뿐**이라는 뜻이고(`test_f05_event_api`), 새 App 이 이벤트를 쓰려면
#:   그 판정을 먼저 받아야 한다. 판정 없이 둘째 소비자가 되지 않고 **그 하나를 거친다**(같은 함수 · 같은 문지기).
from apps.dsm import services as dsm_services
from apps.dsm.services import InvalidEventInput

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
    event = dsm_services.event_detail(scope=scope, event_id=verification_id)
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
        # ★ [턴 AQ · 차선 W2A] 누른 뒤 재조회가 회신(결과·사진)을 보이게 — K1 현장 회신
        #   공개 면(`field_replies`)을 읽어 **이 파일이 쓴 모양**만 되짚는다(새 표 0).
        "replies": _parsed_replies(scope, event.event_id),
    }


#: 회신 한 줄 안의 사진 표식 — `reply_verification` 이 쓰고 `_parsed_replies` 가 읽는다.
PHOTO_MARK = "[사진:"


def _parsed_replies(scope, event_id: int) -> list[dict]:
    """이 확인 요청에 달린 회신 중 **결과 3택으로 시작하는 줄**만 — 최신순."""
    out = []
    for reply in dsm_services.field_replies(scope=scope, event_id=event_id, limit=50):
        text = reply.text or ""
        head = text.split(" ", 1)[0]
        if head not in RESULTS:
            continue
        photo_id = None
        if PHOTO_MARK in text:
            tail = text.split(PHOTO_MARK, 1)[1].split("]", 1)[0]
            photo_id = int(tail) if tail.isdigit() else None
        out.append({"reply_id": reply.reply_id, "result": head, "photo_id": photo_id})
    return out


def _require_photo_of(event_id: int, photo_id: int) -> None:
    """그 사진이 **이 사건에** 올라온 것인가. 사건 문지기(K1 `get_event`)는 호출자가
    먼저 지났다 — 그래서 사건 번호로 좁히면 곧 테넌트로 좁힌 것이다.

    사진 저장은 `POST /api/dsm/events/{id}/field-photo`(`apps/dsm/field.py`) 한 곳이다 —
    이 파일은 새 업로드 문을 만들지 않고 그 행의 번호만 회신에 묶는다(D-212).
    """
    from django.apps import apps

    photo_model = apps.get_model("stream_monitors", "DsmFieldPhoto")
    if not photo_model._base_manager.filter(pk=photo_id, event_id=event_id).exists():
        raise VerificationReplyRejected(
            f"photo_id={photo_id} 는 이 확인 요청에 올라온 사진이 아니다")


def reply_verification(*, scope, verification_id: int, result: str,
                       reason_code: str = "", note: str = "",
                       photo_id: int | None = None) -> dict:
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

    photo_label = ""
    if photo_id is not None:
        # 사건 문지기를 먼저 지난다(남의 사건이면 여기서 404) — 그 뒤에 사진을 본다.
        dsm_services.event_detail(scope=scope, event_id=verification_id)
        _require_photo_of(verification_id, photo_id)
        photo_label = f"{PHOTO_MARK}{photo_id}] "

    text = f"{result} {reason_label}{photo_label}{note}".strip()
    try:
        reply = dsm_services.field_reply(
            scope=scope, event_id=verification_id, text=text)
    except InvalidEventInput as exc:
        raise VerificationReplyRejected(str(exc)) from exc

    verdict = None
    if result == RESULT_FIRE_CONFIRMED:
        verdict = dsm_services.review_event(
            scope=scope, event_id=verification_id, verdict="confirmed", reason=text).verdict
    elif result == RESULT_FALSE_ALARM:
        verdict = dsm_services.review_event(
            scope=scope, event_id=verification_id, verdict="rejected", reason=text).verdict
    # cannot_access — 판정을 바꾸지 않는다(접근 불가는 「진위」에 대한 답이 아니다).

    return {
        "verification_id": reply.event_id,
        "reply_id": reply.reply_id,
        "result": result,
        "reason_code": reason_code or None,
        "verdict": verdict,
        "photo_id": photo_id,
    }
