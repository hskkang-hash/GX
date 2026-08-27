# -*- coding: utf-8 -*-
"""K1 공개 면이 주고받는 모양 — **Django 모델을 밖으로 내보내지 않는다**.

왜 dataclass 인가
-----------------
DA-04 §1-4: *"커널의 공개 면은 서비스 함수다. App 이 커널의 **모델을 직접 import 하지
않는다.** 모델을 직접 만지면 커널을 바꿀 때 App 이 깨지고, 그러면 '한 번 개발'이 거짓이 된다."*

모델 인스턴스를 그대로 돌려주면 import 를 안 해도 결과는 같다 — App 이
`event.stream_monitor.drone.name` 을 타고 들어가는 순간 커널의 스키마가 App 의 계약이 된다.
그래서 **여기서 끊는다.** 나가는 것은 값이고, 값의 모양은 이 파일이 정한다.

`stream_monitor_name` 같은 파생 필드를 미리 담아 두는 것도 같은 이유다 —
담아 두지 않으면 App 이 FK 를 타고 들어가고, 그러면 N+1 과 계층 누수가 함께 온다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class RecordResult:
    """`record_detection` 의 결과.

    ★ `created` 와 `should_notify` 는 **다른 것**이다. 이 둘을 하나로 합치면
      DA-04 가 나눠 둔 두 창(기록 10초 · 알림 5분)이 다시 붙고,
      그 순간 F-04(중복 알림 0건)를 지키려다 U1(오탐률 분모)이 거짓이 된다.
    """

    event_id: int
    #: 새 이벤트가 만들어졌는가. 거짓이면 기존 이벤트의 `last_seen_at` 만 갱신됐다 (10초 창).
    created: bool
    #: K2 가 알림을 보내야 하는가 (5분 창). **이벤트를 접는 것과 무관하다.**
    should_notify: bool
    #: 접힌 횟수를 세는 대신 그 사실만 남긴다 — 정확한 수는 이벤트 행들이 이미 갖고 있다.
    folded_into_existing: bool = False


@dataclass(frozen=True)
class EventView:
    """조회 결과 한 줄. App·화면이 보는 이벤트의 전부다."""

    event_id: int
    event_type: str
    severity: str
    status: str
    occurred_at: datetime
    last_seen_at: datetime | None
    stream_monitor_id: int
    #: 파생 필드 — App 이 FK 를 타고 들어가지 않게 미리 담는다.
    stream_monitor_name: str
    confidence: float | None = None
    bbox: dict[str, Any] | None = None
    snapshot_path: str = ""
    clip_path: str | None = None
    lat: float | None = None
    lng: float | None = None
    reviewed_by_id: int | None = None
    reviewed_at: datetime | None = None
    reject_reason: str | None = None
