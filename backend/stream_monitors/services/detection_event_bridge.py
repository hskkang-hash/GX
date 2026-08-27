# -*- coding: utf-8 -*-
"""AI 검출 → K1 이벤트 배선 (W2-2 · D-284 (1)).

무엇이 없었나 — **검출이 없던 게 아니라 버려지고 있었다**
----------------------------------------------------------
AI 서버는 `Detection{x, y, width, height, label, confidence, color}` 를 **이미**
돌려주고 있었다(`frame_detection.proto` 실측). 그런데 `grpc_client.process_frame_batch`
가 이미지만 디코딩하고 `detections` 를 통째로 버렸고, `DetectionEvent` 는
**정의 1건 · 사용 0건**이었다. 즉 **추가 AI 개발 없이 배선만으로 탐지가 살아난다** (D-284).

이 파일이 그 배선이다. 하는 일은 셋뿐이다:

    1. AI 라벨 → 계약 열거값(`event_type`) 으로 옮긴다
    2. 옮기지 못한 라벨을 **버리지 않고 센다**
    3. K1 커널의 `record_detection` 을 부른다 (중복 억제는 커널이 한다)

★ 커널의 **공개 면만** 부른다 (DA-04 §1-4 · D-278)
--------------------------------------------------
    from kernels.k1_event import record_detection        # 이렇게 부른다
    from kernels.k1_event.models import DetectionEvent   # 이러면 CI 가 막는다

모델을 직접 만지면 커널을 바꿀 때 App 이 깨지고, 그러면 "한 번 개발"이 거짓이 된다.
중복 억제(10초)·알림 판정(5분)·소유 상속도 **전부 커널이 한다** — 여기서 다시 하지 않는다.
두 벌을 두면 어긋나고, 그 어긋남은 아무도 못 본다.

★ 스코프 — 파이프라인에는 요청자가 없다 (D-281)
-----------------------------------------------
gRPC 콜백에는 사람이 없다. 그래서 `TenantScope.system(reason=...)` 을 쓴다.
**사유가 필수**이고, 그 스코프로는 **읽지 못한다**. 이벤트의 소유는 요청자가 아니라
**스트림이 정한다** — 커널의 `_inherit_owner` 가 그것을 한다.

★ 모르는 라벨을 아는 척하지 않는다
----------------------------------
AI 서버가 실제로 어떤 라벨 문자열을 쓰는지는 **아직 재지 못했다** — `AI_GRPC_URL` 이
이 PC 에서 닿지 않는다(`media-ai.invalid`). 그래서 아래 표에는 **계약 열거값과 글자가
같은 것만** 넣었다. 그것은 추정이 아니다: AI 가 `"fire"` 를 주면 그것은 화재다.

    그 밖의 라벨은 `unmapped` 로 **세어서 돌려준다.** 조용히 버리지 않는다 —
    버리면 "검출이 없었다"와 "옮길 줄 몰랐다"가 구별되지 않고, 그것이 이 파일이
    고치려는 바로 그 상태다.

실제 라벨 목록이 측정되면 아래 표를 늘리되, **측정 근거를 함께 적는다** (D-273 초안 검증 원칙).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable

from common.tenant_scope import TenantScope
from kernels.k1_event import InvalidEventInput, record_detection

log = logging.getLogger(__name__)

#: AI 라벨 → 계약 `event_type` (docs/contracts/detection-event.md).
#:
#: ⚠ **글자가 같은 것만 넣었다.** 추정으로 늘리지 않는다 (D-280).
#:   예컨대 `"car"` → `vehicle` 은 그럴듯하지만, AI 가 `"car"` 를 주는지 `"vehicle"` 을
#:   주는지 **재지 않았다.** 재지 않은 것을 표에 적으면 그 표가 근거처럼 읽힌다.
#:   측정되면 늘리고, 그때 이 주석에 측정 경로를 적는다.
LABEL_TO_EVENT_TYPE: dict[str, str] = {
    "person": "person",
    "vehicle": "vehicle",
    "fire": "fire",
    "smoke": "smoke",
    "intrusion": "intrusion",
    "sos": "sos",
}

#: `event_type` → `severity` (계약 열거: info | warning | critical).
#:
#: ⚠ 이 표는 **계약 문서에 없다.** `detection-event.md` 는 두 열거값을 각각 정의하지만
#:   둘을 잇는 규칙은 적지 않았다. 그래서 임의로 정하지 않고 `decisions_pending` 의
#:   **P-W2-2-1** 로 올렸고, 그 판정 전까지 아래를 **잠정값**으로 쓴다 (D-213 — STOP 대신
#:   적재하고 전진). 되돌리는 비용은 이 사전 하나다.
#:
#:   잠정값의 근거: ISA-101 은 빨강(critical)을 **즉시 개입이 필요한 것** 전용으로 쓴다
#:   (계약 문서: "critical 만 빨강. 다른 용도로 빨강 금지"). 화재·연기·구조요청은
#:   사람이 지금 움직여야 하는 것이고, 사람·차량의 존재 자체는 그렇지 않다.
EVENT_TYPE_TO_SEVERITY: dict[str, str] = {
    "fire": "critical",
    "smoke": "critical",
    "sos": "critical",
    "intrusion": "warning",
    "person": "info",
    "vehicle": "info",
}

#: 이 값 아래의 검출은 이벤트로 만들지 않는다.
#:
#: ⚠ 0.0 이다 — **거르지 않는다.** 문턱값은 U1 의 오탐률 분모를 직접 깎으므로
#:   숫자를 고르는 것 자체가 판정이고, 그 판정의 근거가 될 실데이터가 아직 없다.
#:   "일단 0.5" 가 들어오는 순간 오탐률은 **문턱값이 만든 수**가 된다.
#:   문턱은 K6(피드백·계측)이 실측 분포를 갖고 정한다.
MIN_CONFIDENCE = 0.0


@dataclass
class PublishResult:
    """배선 한 번의 결과. **버린 것도 센다.**

    `unmapped_labels` 가 비어 있지 않다는 것은 "AI 가 우리가 모르는 말을 했다"는 뜻이고,
    그것은 오류가 아니라 **측정 결과**다. 지워서는 안 된다 — 이 목록이 곧
    `LABEL_TO_EVENT_TYPE` 를 늘릴 때 쓸 근거다 (D-273 초안 검증 원칙).
    """

    #: 만들어진 이벤트 id (접힌 것 포함 — 접힘도 그 이벤트를 가리킨다).
    event_ids: list[int] = field(default_factory=list)
    #: 새로 만들어진 이벤트 수 (10초 창을 넘긴 것).
    created: int = 0
    #: 기존 이벤트로 접힌 수 (10초 창 안).
    folded: int = 0
    #: K2 가 알림을 보내야 하는 수 (5분 창). **created 와 다른 수다** (DA-04).
    to_notify: int = 0
    #: 옮기지 못한 라벨 → 그 수. **버리지 않고 센다.**
    unmapped_labels: dict[str, int] = field(default_factory=dict)
    #: 문턱값 미달로 거른 수. MIN_CONFIDENCE=0.0 인 지금은 0 이다.
    below_confidence: int = 0
    #: 커널이 반려한 것 (계약 밖 열거값 등). 사유를 그대로 남긴다.
    rejected: list[str] = field(default_factory=list)

    @property
    def total_seen(self) -> int:
        """받은 검출 전수. **분모다** (D-271 — 분모 없는 초록은 보고가 아니다)."""
        return (self.created + self.folded + self.below_confidence
                + sum(self.unmapped_labels.values()) + len(self.rejected))


def publish_detections(
    *,
    stream_monitor_id: int,
    detections_per_frame: Iterable[Iterable[dict[str, Any]]],
    reason: str,
    snapshot_path: str = "",
    mission_id: int | None = None,
) -> PublishResult:
    """검출 묶음을 K1 이벤트로 넘긴다.

    Args:
        stream_monitor_id: 어느 스트림의 검출인가. **이벤트의 소유가 여기서 정해진다.**
        detections_per_frame: `grpc_client` 의 `metadata['detections']` 그대로.
        reason: 이 호출에 사람이 없는 이유 (D-281 — 사유 없는 시스템 스코프는 만들 수 없다).
        snapshot_path: MinIO 객체 경로. 없으면 빈 문자열 — **가짜 경로를 만들지 않는다.**
        mission_id: 임무 중이라면 그 id.

    Returns:
        `PublishResult` — 만든 것과 **버린 것을 함께** 센다.

    ※ 예외를 삼키지 않는다. 커널이 계약 위반으로 반려하면 그 사유를 `rejected` 에 담아
      **돌려준다**(호출처가 스트림을 죽이지 않도록). 그 밖의 예외는 그대로 올린다 —
      DB 가 죽은 것을 "검출 0건"으로 보고하는 것이 이 파일이 고치려는 바로 그 병이다.
    """
    scope = TenantScope.system(reason=reason)
    result = PublishResult()

    for frame_detections in detections_per_frame:
        for det in frame_detections or ():
            label = (det.get("label") or "").strip()
            confidence = det.get("confidence")

            event_type = LABEL_TO_EVENT_TYPE.get(label.lower())
            if event_type is None:
                # ★ 버리지 않는다. 센다.
                result.unmapped_labels[label] = result.unmapped_labels.get(label, 0) + 1
                continue

            if confidence is not None and confidence < MIN_CONFIDENCE:
                result.below_confidence += 1
                continue

            try:
                recorded = record_detection(
                    scope=scope,
                    stream_monitor_id=stream_monitor_id,
                    event_type=event_type,
                    severity=EVENT_TYPE_TO_SEVERITY[event_type],
                    confidence=confidence,
                    bbox=det.get("bbox"),
                    snapshot_path=snapshot_path,
                    mission_id=mission_id,
                )
            except InvalidEventInput as exc:
                # 계약 위반은 **이 배치만** 실패시킨다. 스트림 전체를 죽이지 않는다.
                result.rejected.append(f"label={label!r}: {exc}")
                continue

            result.event_ids.append(recorded.event_id)
            if recorded.created:
                result.created += 1
            else:
                result.folded += 1
            if recorded.should_notify:
                result.to_notify += 1

    if result.unmapped_labels:
        # 목록을 **글자 그대로** 남긴다. 요약하면 표를 늘릴 때 쓸 수 없다.
        log.warning(
            "[K1][UNMAPPED] stream=%s 옮기지 못한 AI 라벨 %s — "
            "LABEL_TO_EVENT_TYPE 에 없다. 이 목록이 그 표를 늘릴 근거다 (D-273)",
            stream_monitor_id, result.unmapped_labels,
        )
    return result
