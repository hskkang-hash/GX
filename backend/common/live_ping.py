# -*- coding: utf-8 -*-
"""UX-08 — **관제 화면을 새로고침 없이 살리는 신호 하나.**

무엇을 보내나 — 카드가 아니라 **신호**다
----------------------------------------
새 탐지가 저장되면 화면에 「무엇인가 늘었다」만 알린다. 화면은 그 신호를 받고
**자기 목록 문을 다시 부른다.** 카드 내용을 신호에 실어 보내지 않는다:

    무엇이 한 장인가는 목록 문 한 곳이 정한다 —
    5분 이어붙이는 창의 묶음도, F-04 5분 알림 억제도 거기서 이미 판정된다.

카드를 신호에 실으면 화면이 그리는 목록과 서버가 정하는 목록이 **두 벌**이 되고,
두 벌은 반드시 어긋난다. 어긋나는 순간 하나는 거짓말이다.

★ 그래서 이 파일은 F-04 와 **부딪히지 않는다.** 억제는 발송(K2)이 정하고, 묶음은
  큐(화면 목록)가 정한다. 여기서 하는 일은 **문을 두드리는 것**뿐이다.

폭주를 어떻게 막나 — 억제가 아니라 **합치기**
---------------------------------------------
재난 때 탐지는 초 단위로 쏟아진다. 저장마다 채널 레이어를 때리면 그 자체가
장애가 된다. 그래서 테넌트마다 `PING_COALESCE_SECONDS` 창 안의 두드림을
**한 번으로 합친다**(Redis 캐시의 원자적 `add`).

⚠ 이것은 **억제가 아니다.** 합쳐도 다음 창에서 다시 두드리고, 화면은 두드림을
  받을 때마다 목록 전체를 다시 읽으므로 **합쳐진 사이에 늘어난 것도 함께 온다.**
  억제였다면 그 사이의 이벤트가 화면에서 사라졌을 것이다 — 둘은 다른 일이다.
⚠ 창을 5분으로 두지 않는다. 5분은 **알림**의 창이지 **화면**의 창이 아니다.
  화면에서 5분을 기다리면 당직자에게는 「안 뜬다」로 보인다.
"""

from __future__ import annotations

import logging

from django.core.cache import cache
from django.utils import timezone

log = logging.getLogger(__name__)

#: 같은 테넌트의 두드림을 이 초 안에서 한 번으로 합친다.
#: 짧게 잡는다 — 이것은 폭주 방지이지 억제가 아니다.
PING_COALESCE_SECONDS = 3

#: 전역 방과 테넌트 방. 받는 쪽(consumer)이 이미 두 방에 다 들어가 있다.
GLOBAL_ROOM = "surveillance_profiles_global"


def _room_for(tenant_code) -> str:
    return GLOBAL_ROOM if tenant_code in (None, "") else f"surveillance_profiles_{tenant_code}"


def ping_detection(*, tenant_code=None, reason: str = "detection") -> bool:
    """관제 화면에 「목록을 다시 읽어라」를 보낸다. 실제로 보냈으면 True.

    ★ **한 건도 실패로 위로 던지지 않는다.** 화면 갱신 신호가 못 나갔다고
      탐지 기록이 실패해서는 안 된다 — 알림과 기록의 순서를 뒤집는 것이 된다.
      다만 **조용히 삼키지도 않는다**: 못 보낸 것은 경고로 남는다.
    """
    room = _room_for(tenant_code)
    key = f"gx:ux08:ping:{room}"
    try:
        # 원자적이다. 여러 워커가 동시에 와도 창마다 한 번만 참이 된다.
        if not cache.add(key, 1, timeout=PING_COALESCE_SECONDS):
            return False
    except Exception as exc:  # 캐시가 죽어도 화면 갱신은 계속 시도한다
        log.warning("[UX-08] 두드림 합치기를 못 했다(%s) — 그대로 보낸다", exc)

    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        layer = get_channel_layer()
        if layer is None:
            log.warning("[UX-08] 채널 레이어가 없다 — 화면은 주기 갱신으로만 산다")
            return False
        async_to_sync(layer.group_send)(room, {
            "type": "detection_message",
            "timestamp": timezone.now().isoformat(),
            # ★ 카드가 아니다. 「무엇인가 늘었다」와 **왜 두드렸는지**뿐이다.
            "message": {"reason": reason},
        })
        return True
    except Exception as exc:
        log.warning("[UX-08] 화면 두드림 실패(%s) — 목록은 주기 갱신으로 계속 산다", exc)
        return False
