# -*- coding: utf-8 -*-
"""판정이 바뀌었다는 **사실만** 알리는 자리 (P-16 · 2026-09-20).

왜 이 파일이 생겼나 — **사용자에게 같은 일이 코드에서도 같은 일이면 안 된다**
------------------------------------------------------------------------------
U1 이 「오탐」을 누르고 나서 「종결」을 또 눌러야 하면, 사용자는 **두 종류의 종결**을
보게 된다 — P-1 화면 규칙이 막으려던 바로 그 모양이다. 그래서 결합은 붙인다.

그런데 D-399 는 두 축을 일부러 갈랐다:

    DetectionEvent.status/verdict  「이 탐지가 진짜인가」   ← 판정 축
    DetectionEvent.response_state  「사람이 어디까지 했나」 ← 대응 축

`review_event` 가 `response_state` 를 **직접 쓰면** 그 둘이 코드에서 다시 맞물린다.
한 번 맞물리면 다음 사람은 판정을 고치려다 대응을 깨뜨리고, 그 반대도 마찬가지다.

그래서 이렇게 한다 (세종 09-18 §1 판정):

    · 판정 축은 **일어난 일을 말할 뿐**이다 — 이 신호를 보낸다
    · 대응 축은 **판정을 절대 읽지 않는다** (역방향 없음)
    · 결합은 **소비자 한 곳**에만 산다 — `stream_monitors/services/false_positive_closer.py`

★ 왜 django 신호인가. 이 저장소에 이미 있는 배선이고(`django.dispatch`), 소비자를
  **이름으로 등재**하는 대장이 이미 있다(`tests/test_f05_event_api.K1_CONSUMERS`).
  새 발행 기구를 만들면 그 대장이 안 보는 두 번째 배선이 생긴다.

★ 신호를 **트랜잭션 안에서** 보낸다. 판정이 커밋되고 대응 종결이 안 되는 창을 만들지
  않기 위해서다. 그 창이 곧 「오탐이라 눌렀는데 대응이 열려 있는 이벤트」이고,
  그것은 결합을 붙이지 않은 것보다 나쁘다 — **반만 일어난 규칙은 규칙이 아니다.**
  대신 알림 같은 곁가지는 소비자 안에서 **저하 운전**으로 감싼다(K2 가 하는 것과 같다).
"""
from __future__ import annotations

from django.dispatch import Signal

#: 판정이 **바뀌었다**. 같은 값으로 다시 판정한 것은 전이가 아니므로 보내지 않는다.
#:
#: 보내는 쪽: `kernels.k1_event.services.review_event`
#: 받는 쪽:   `stream_monitors.services.false_positive_closer` (K1_CONSUMERS 등재)
#:
#: kwargs
#:   event_id : int          어느 이벤트인가
#:   verdict  : str          바뀐 뒤의 판정 (`confirmed` / `rejected`)
#:   previous : str          바뀌기 전의 판정 (빈 문자열이면 첫 판정)
#:   scope    : TenantScope  **판정한 사람의 스코프.** 소비자는 이것으로 문지기를 지난다 —
#:                           행위자가 시스템이라고 해서 테넌트가 없어지는 것이 아니다
verdict_changed = Signal()
