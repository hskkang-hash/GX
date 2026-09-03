# -*- coding: utf-8 -*-
"""K2 오류 계약. K1·K6 과 같은 형을 쓴다 — App 이 커널마다 다른 계보를 외우지 않게."""
from __future__ import annotations


class K2Error(Exception):
    """K2 가 내는 모든 오류의 뿌리."""


class InvalidNotifyInput(K2Error):
    """등급·채널·기간이 계약을 벗어난 입력. HTTP 400 으로 번역한다."""


class EventNotFound(InvalidNotifyInput):
    """지목한 이벤트가 **없다.** HTTP 404 로 번역한다.

    ★ [D-410 · 2026-09-19] `InvalidNotifyInput` 의 좁은 갈래로 새로 판다. 왜 나누나 —
      「없는 이벤트」와 「등급이 계약 밖」은 **부르는 쪽이 해야 할 일이 다르다.**
      앞엣것은 id 를 고쳐야 하고 뒤엣것은 요청을 고쳐야 한다. 한 예외로 뭉치면 App 은
      문구를 뜯어 보는 수밖에 없고, 문구를 뜯어 보는 코드는 번역문이 바뀌는 날 조용히
      틀린다 (D-290 — 부재와 오류를 가른다).

    ★ **`InvalidNotifyInput` 을 상속한다** — 이미 `except InvalidNotifyInput` 으로
      잡고 있던 자리는 하나도 안 바뀐다. 넓은 그물은 그대로 두고 좁은 그물을 더한다.

    ⚠ 이 갈래가 생긴 사유: 계약 라우트 도달 판정기가
      `POST /api/dsm/events/{id}/notify` 를 없는 id 로 두드렸더니 **500** 이었다.
      「그런 이벤트가 없다」를 **서버 결함**으로 내고 있었다 — U6 은 자기 잘못인지
      우리 잘못인지 알 수 없었다.
    """


class NoRecipients(K2Error):
    """수신자가 0명이다 — **조용한 무력화를 막는다** (DA-03 §3-2).

    ★ 빈 목록을 돌려주지 않는 이유: 그러면 "보냈는데 대상이 없었다"가 성공으로 보인다.
      규칙이 비었거나 역할에 사람이 없는 상태는 **알림 체계가 꺼져 있는 것**이고,
      그것은 재난 시스템에서 가장 조용한 고장이다. 없는 것과 실패한 것을 같은 값으로
      표현하지 않는다 (D-290).
    """


class NotImplementedYet(K2Error):
    """공개 면에 이름은 있는데 구현이 없는 것 (D-284)."""
