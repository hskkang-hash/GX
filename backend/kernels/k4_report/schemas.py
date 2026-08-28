# -*- coding: utf-8 -*-
"""K4 공개 면이 주고받는 모양 — **모델을 밖으로 내보내지 않는다** (DA-04 §1-4).

이 파일의 중심은 `ReportContext` 다. F-11 의 AC 가 *"템플릿 변수(이벤트·조치·캡처)
치환 및 PDF 출력"* 이고, DA-04 §2 K4 가 그 셋을 **반드시 포함**하라고 못박았다:

    치환 변수는 계약이 지정한 **3종을 반드시 포함**한다: 이벤트 · 조치 · 캡처(F-11 AC).
    "조치"는 K2 의 `DeliveryRecord` + I-4 의 SDN 처리 결과다.

그리고 U2 의 10분은 렌더 시간이 아니다:

    10분은 **사람의 작업 시간**이지 렌더 시간이 아니다. 줄이는 것은 `build_context` 의
    **자동 취합 범위**다 — 사람이 손으로 옮겨 적는 항목이 0 이면 10분이 된다.

그래서 이 컨텍스트는 **손으로 채워야 하는 칸을 스스로 센다**(`manual_fields`).
그 수가 0 이 아니면 U2 는 아직 달성되지 않았고, 그 사실이 숫자로 보인다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

#: F-11 이 지정한 치환 변수 3종. **이름으로 잠근다** (D-285 ②).
#: 늘리거나 줄이려면 계약 AC 와 이 튜플을 **같은 커밋에서** 고친다.
REQUIRED_VARIABLES: tuple[str, ...] = ("events", "actions", "captures")


@dataclass(frozen=True)
class TemplateView:
    """템플릿 한 장. App 이 `ReportTemplate` 모델을 만지지 않게 여기서 끊는다."""

    template_id: int
    name: str
    is_default: bool
    is_enabled: bool
    usage_count: int = 0


@dataclass(frozen=True)
class ActionRow:
    """조치 이력 한 줄 — **K2 의 `DeliveryRecord` 를 그대로 읽는다.**

    DA-04 §2 K2 이중 AC: *"발송 기록이 곧 보고서의 '조치 이력' 행이다 — K4 가 이
    레코드를 그대로 읽는다. **알림용·보고서용 두 벌로 적재하지 않는다.**"*

    그래서 이 dataclass 에는 K2 가 안 주는 필드가 없다. 하나라도 더 있으면 그 필드는
    어디선가 따로 만들어진 것이고, 따로 만든 순간 두 벌이 된다.
    """

    delivery_id: int
    event_id: int
    channel: str
    recipient_address: str
    occurred_at: datetime
    sent_at: datetime | None
    succeeded: bool
    failure_reason: str | None = None

    @property
    def latency_seconds(self) -> float | None:
        """실패면 `None` — **0 이 아니다.** 못 보낸 것은 빠른 것이 아니다."""
        if self.sent_at is None:
            return None
        return (self.sent_at - self.occurred_at).total_seconds()


@dataclass(frozen=True)
class CaptureRow:
    """캡처 한 장. 경로만 나른다 — 바이트는 렌더러가 필요할 때 가져간다."""

    event_id: int
    snapshot_path: str
    clip_path: str | None = None

    @property
    def has_image(self) -> bool:
        return bool(self.snapshot_path)


@dataclass(frozen=True)
class ReportContext:
    """치환 컨텍스트. **F-11 의 세 변수가 여기 다 있어야 한다.**

    ★ `sources_failed` 가 요점이다 — **"조치가 없었다"와 "조치를 못 가져왔다"는
      다른 사실**이다(D-290). 둘을 빈 목록 하나로 표현하면, 발송 조회가 실패한 보고서가
      "조치 없음"으로 인쇄되어 고객에게 나간다. 그 종이는 되돌릴 수 없다.
    """

    since: datetime
    until: datetime
    events: tuple[Any, ...] = field(default_factory=tuple)
    actions: tuple[ActionRow, ...] = field(default_factory=tuple)
    captures: tuple[CaptureRow, ...] = field(default_factory=tuple)
    #: 자동으로 못 채워 **사람이 손으로 적어야 하는** 칸. U2 의 10분이 이 수에 달려 있다.
    manual_fields: tuple[str, ...] = field(default_factory=tuple)
    #: 가져오다 **실패한** 출처. 비어 있는 것과 실패한 것을 가른다 (D-290).
    sources_failed: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_complete(self) -> bool:
        """이 컨텍스트로 보고서를 낼 수 있는가.

        손으로 채울 칸이 남았거나 출처가 실패했으면 **아직 아니다.**
        """
        return not self.manual_fields and not self.sources_failed

    @property
    def missing_variables(self) -> tuple[str, ...]:
        """F-11 의 세 변수 중 **자리 자체가 없는** 것.

        비어 있는 것(`()`)은 여기 해당하지 않는다 — 그 기간에 이벤트가 0건일 수 있다.
        여기서 잡는 것은 **필드가 아예 없는** 경우이고, 그것은 계약 위반이다.
        """
        return tuple(name for name in REQUIRED_VARIABLES if not hasattr(self, name))

    def as_template_vars(self) -> dict[str, Any]:
        """템플릿 엔진에 넘길 사전. **세 변수를 항상 넣는다.**

        0건이어도 키를 뺀 채로 넘기지 않는다 — 빼면 템플릿이 `{{ actions }}` 에서
        조용히 빈 문자열을 그리고, 그 종이는 "조치 없음"과 구별되지 않는다.
        """
        return {
            "since": self.since,
            "until": self.until,
            "events": list(self.events),
            "actions": list(self.actions),
            "captures": list(self.captures),
            # 보고서에 **불완전 사실을 함께 인쇄**한다. 숨기면 받는 사람이 완전한 줄 안다.
            "sources_failed": list(self.sources_failed),
            "manual_fields": list(self.manual_fields),
        }
