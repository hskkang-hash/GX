# -*- coding: utf-8 -*-
"""K2 공개 면이 주고받는 모양 — **모델을 밖으로 내보내지 않는다** (DA-04 §1-4)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

#: ★ [F-10 계약 AC] **심각 등급 발생 후 30초 내 발송 기록.**
#:   숫자를 여기 한 곳에 둔다 — 시험과 화면과 보고서가 같은 값을 본다 (D-212).
F10_MAX_LATENCY = timedelta(seconds=30)

#: ★ **알림** 중복 억제 창 (DA-04 K2: *"5분 중복 억제 판정은 여기다 — K1 이 아니다"*).
#:   K1 의 `NOTIFY_WINDOW` 와 **같은 값이지만 다른 자리에서 판정한다.**
#:   K1 은 "이 검출이 알릴 만한가"를, K2 는 "실제로 이미 보냈는가"를 본다.
#:   K1 의 판정은 이벤트 행을 보고, K2 의 판정은 **발송 이력**을 본다 —
#:   보내지 못한 알림(발송 실패)은 억제 대상이 아니기 때문이다.
SUPPRESS_WINDOW = timedelta(minutes=5)


@dataclass(frozen=True)
class Recipient:
    """수신자 한 명. **모델이 아니라 값이다.**

    `address` 를 미리 담아 두는 이유는 K1 의 `stream_monitor_name` 과 같다 —
    담아 두지 않으면 부르는 쪽이 사용자 객체를 타고 들어가고, 그러면 커널의 스키마가
    App 의 계약이 된다.
    """

    user_id: int
    display_name: str
    address: str
    channel: str
    #: 어느 규칙이 이 사람을 골랐는가. 감사에서 "왜 이 사람에게 갔나"에 답하는 값이다.
    rule_id: int
    role_code: str = ""


@dataclass(frozen=True)
class RuleView:
    """알림 규칙 한 줄. **모델이 아니라 값이다** (`Recipient` 와 같은 이유).

    ★ `role_code` 를 함께 담는 이유: 부르는 쪽이 `rule.role.code` 를 타고 들어가면
      역할 모델이 App 의 계약이 된다. 규칙을 만든 화면이 되돌려 받는 것은 **번호가
      아니라 이름**이어야 사람이 확인할 수 있다 — 「누가 받는가」가 이 값의 전부다.

    ★ `channels` 는 튜플이다. 리스트로 내면 부르는 쪽이 고칠 수 있고, 고쳐도 DB 는
      안 바뀐다 — 「바꿨는데 안 바뀌는」 자리를 만들지 않는다.
    """

    rule_id: int
    severity: str
    role_id: int
    role_code: str
    zone: str | None
    channels: tuple[str, ...]
    is_active: bool


@dataclass(frozen=True)
class DeliveryView:
    """발송 이력 한 줄. **F-10 을 재는 두 점이 한 줄에 있다** (DA-04 K2)."""

    delivery_id: int
    event_id: int
    recipient_id: int | None
    recipient_address: str
    channel: str
    occurred_at: datetime
    sent_at: datetime | None
    succeeded: bool
    failure_reason: str | None = None
    retry_count: int = 0

    @property
    def latency_seconds(self) -> float | None:
        """`occurred_at → sent_at`. 실패면 `None` — **0 이 아니다.**

        실패를 0초로 세면 평균 지연이 좋아진다. 못 보낸 것은 빠른 것이 아니다.
        """
        if self.sent_at is None:
            return None
        return (self.sent_at - self.occurred_at).total_seconds()

    @property
    def meets_f10(self) -> bool:
        """[F-10] 30초 안에 **발송 기록이 남았는가.**

        실패한 발송은 아무리 빨라도 이 판정을 통과하지 못한다 — F-10 이 요구하는 것은
        "빨리 시도했다"가 아니라 **"보냈다"** 이다.
        """
        if not self.succeeded or self.sent_at is None:
            return False
        return (self.sent_at - self.occurred_at) <= F10_MAX_LATENCY
