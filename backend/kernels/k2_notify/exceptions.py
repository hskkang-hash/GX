# -*- coding: utf-8 -*-
"""K2 오류 계약. K1·K6 과 같은 형을 쓴다 — App 이 커널마다 다른 계보를 외우지 않게."""
from __future__ import annotations

from django.core.exceptions import PermissionDenied


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


class NotifyPermissionDenied(InvalidNotifyInput, PermissionDenied):
    """남의 테넌트를 `group=` 으로 가리켰다 — **입력 오류가 아니라 권한 판정**이다.

    ★ [2026-09-24 · 조율자 병합] 차선 Q 가 세운 문지기(`services._owner_for`)는 옳았는데
      던지는 이름이 `InvalidNotifyInput` 이었다. 그 이름은 **「모르는 채널」·「기간이 계약
      밖」 같은 평범한 입력 오류도** 쓴다. 격리 러너(`tests/test_tenant_isolation`)의
      「거절로 세는 예외」 목록에 그 넓은 이름을 넣으면, 문지기에 **닿지도 못하고** 입력
      오류로 죽은 호출이 「막혔다」로 세어진다 — D-366 이 이름 붙인 거짓 초록 그대로다.

    ★ `EventNotFound` 와 같은 형이다: **넓은 그물은 그대로 두고 좁은 그물을 더한다.**
      이미 `except InvalidNotifyInput` 으로 잡던 자리는 한 곳도 안 바뀐다(차선 Q 의
      시험 셋이 그 넓은 이름으로 잡고 있고, 그대로 통과한다).
      동시에 `PermissionDenied` 이므로 격리 러너가 **권한 거절로만** 세고,
      HTTP 로 번역될 일이 생기면 400 이 아니라 403 이다.
    """


class NoRecipients(K2Error):
    """수신자가 0명이다 — **조용한 무력화를 막는다** (DA-03 §3-2).

    ★ 빈 목록을 돌려주지 않는 이유: 그러면 "보냈는데 대상이 없었다"가 성공으로 보인다.
      규칙이 비었거나 역할에 사람이 없는 상태는 **알림 체계가 꺼져 있는 것**이고,
      그것은 재난 시스템에서 가장 조용한 고장이다. 없는 것과 실패한 것을 같은 값으로
      표현하지 않는다 (D-290).
    """


class CriticalWithoutRecipients(K2Error):
    """이 저장은 **심각 등급을 0명으로 만든다** — 거절한다 (UX-43 AC · 턴 S · 차선 U56).

    ★ `NoRecipients` 와 **다른 사실이다.** 그쪽은 「보내려는데 받을 사람이 없다」(발송
      시점)이고, 이쪽은 「**저장하면** 받을 사람이 없어진다」(설정 시점)다. 앞엣것은
      이미 꺼진 상태를 알리고 뒤엣것은 **꺼지는 것을 막는다** — 둘을 한 이름으로 두면
      화면이 「지금 안 간다」와 「저장을 거절했다」를 같은 말로 그린다(D-290).

    ★ 값이 아니라 예외인 이유: `{"saved": false}` 를 200 으로 돌려주면 화면이 그것을
      성공으로 그리는 날이 오고(W0-18 이 이 저장소에서 실제로 만난 모양), 그러면
      「저장했다」는 글자 뒤에서 심각 경보가 꺼진다. HTTP 409 로 번역한다 — 요청이
      틀린 게 아니라(400) **지금 상태에서 할 수 없는 일**이다.
    """


class NotImplementedYet(K2Error):
    """공개 면에 이름은 있는데 구현이 없는 것 (D-284)."""
