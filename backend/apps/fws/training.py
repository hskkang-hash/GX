# -*- coding: utf-8 -*-
"""FWS-F2-13 — 훈련 임무 수신(훈련 배지) (턴 AL 차선 N2).

DSM 의 훈련 스위치를 그대로 쓴다 — 새 스위치를 만들지 않는다
----------------------------------------------------------------
「지금 훈련 중인가」는 이미 `stream_monitors/services/drill.py` 가 감사로 정본을
쥐고 있고, `apps.dsm.services.drill_state`·`drill_report` 가 그 공개 면이다(F-05 와
같은 결의 판단 — 커널·다른 App 의 상태를 **다시 재지 않는다**, D-212). 이 파일이
더하는 것은 **진화대 쪽 배지 모양**뿐이다.

명세서 완결조건 「실채널 0」을 이 문이 그대로 낸다
----------------------------------------------------
`drill_report()` 가 이미 그 증거(`real_channel_sends`)를 갖고 있다 — 훈련 창 안에
실채널(로그가 아닌 채널)로 나간 발송이 있으면 그것은 훈련의 성공이 아니라 사고다
(그 파일 머리말 「첫 증거는 실채널 발송 0」). 이 배지는 그 값을 사람이 읽을 진화대
언어로 옮길 뿐, 다시 세지 않는다.
"""
from __future__ import annotations

from apps.dsm import services as dsm_services

BADGE_TRAINING = "훈련"


def training_mission_badge(*, scope) -> dict:
    """지금 훈련 임무가 떠 있는가(훈련 배지). 훈련 모드가 꺼져 있으면 정직하게
    `badge=None`(D-284) — 배지를 억지로 그리지 않는다."""
    state = dsm_services.drill_state(scope=scope)
    if not state.get("drill_mode"):
        return {"badge": None, "drill_mode": False,
               "message": "지금 훈련 임무가 없습니다"}

    report = dsm_services.drill_report(scope=scope)
    return {
        "badge": BADGE_TRAINING,
        "drill_mode": True,
        "channel_while_drilling": state.get("channel_while_drilling"),
        "since": state.get("since").isoformat() if state.get("since") else None,
        #: ★ 완결조건 「실채널 0」— 이 값이 실제로 0인지는 `drill_report` 가 잰다.
        #:   여기서 다시 세지 않는다.
        "real_channel_sends": report.get("real_channel_sends") if report.get(
            "measurable") else None,
        "measurable": report.get("measurable", False),
    }
