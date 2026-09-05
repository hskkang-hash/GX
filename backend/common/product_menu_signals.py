# -*- coding: utf-8 -*-
"""**테넌트가 생기면 제품 메뉴가 함께 선다** — UX-25 의 닫는 조건 (세종 P-61 §4).

지시서 §4 가 적은 함정이 이것이다:

    시드는 테넌트 생성 경로에 붙는다 — 개발 테넌트에만 한 번 넣고 끝내면
    **새 테넌트에서 다시 0 이 된다.**

★ 그런데 우리 행은 소속이 없다 — 그러면 신호는 왜 필요한가
----------------------------------------------------------
`common/product_menus.py` 머리말 ②가 적은 대로, 이 DB 에서 메뉴 정본은
**소속 없는 한 벌**이어야 한다(`RoleMenu` 가 (메뉴,역할) 유일 · `list_menus` 가
소속을 안 가린다). 그래서 새 테넌트는 만들어지는 순간 이미 그 한 벌을 본다.

그렇다면 신호가 메우는 자리는 **다른 둘**이다. 둘 다 실제로 일어난다:

  ① **표가 늘었는데 아무도 시드를 다시 안 돌린 채 테넌트가 생기는 날.**
     그날 새 테넌트는 옛 표를 본다. 「배포에 시드 한 줄을 넣기로 했다」는 규약이지
     기계가 아니다 — 규약은 잊히고, 잊힌 것은 화면에서 안 보인다.
  ② **새 테넌트가 자기 역할을 새로 만드는 날.**
     이 DB 의 `role_role` 은 소속을 갖는다 [실측 2026-09-05 — `fire_user` 소속 6 ·
     `surveillance_order` 소속 5 · `admin` 소속 없음]. 같은 코드의 역할이 소속마다
     따로 생기면 **그 역할에는 연결이 하나도 없다.** 사람은 역할이 있는데 사이드바가
     빈다 — UX-25 가 태어난 그 모양 그대로다.

그래서 두 자리에 건다: `UserGroup` 이 생길 때(테넌트) · `Role` 이 생길 때(역할).

★ 무엇을 안 하나
----------------
  · **지우지 않는다.** 신호는 「빠진 것을 메운다」뿐이다.
  · **막지 않는다.** 메뉴를 못 세워도 테넌트 생성은 성공해야 한다 — 사이드바 한 줄
    때문에 테넌트가 안 만들어지는 것은 고치려던 것보다 나쁜 고장이다. 그래서
    `try/except` 로 감싸고 **로그에 남긴다**(조용히 삼키지 않는다).
  · **dj-core 를 안 고친다**(§0.4). 신호는 바깥에서 듣는 것이고, 듣는 것은 고치는 것이
    아니다. `core.user.api.create_group` 도 `core.menu.models` 도 그대로다.
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

#: 신호가 실제로 무엇을 했는지 세는 자리. 시험이 읽는다 —
#: 「신호를 걸었다」와 「신호가 돌았다」는 다른 사실이다(D-301).
LAST_RUN: dict = {"tenant": None, "role": None}


def _ensure(where: str) -> None:
    from common.product_menus import ensure_product_menus

    try:
        result = ensure_product_menus()
    except Exception as exc:  # noqa: BLE001 — 테넌트 생성을 막지 않는다
        logger.error("[UX-25] %s 에서 제품 메뉴를 못 세웠다: %s: %s",
                     where, type(exc).__name__, exc)
        LAST_RUN[where] = {"error": "%s: %s" % (type(exc).__name__, exc)}
        return
    LAST_RUN[where] = result
    if result["menu_created"] or result["link_created"] or result["link_updated"]:
        logger.info(
            "[UX-25] %s — 제품 메뉴 %d행 새로 · 연결 %d개 새로 · %d개 켬",
            where, result["menu_created"], result["link_created"], result["link_updated"])


@receiver(post_save, sender="user.UserGroup", dispatch_uid="ux25_product_menus_on_tenant")
def on_tenant_created(sender, instance, created, **kwargs):
    """테넌트가 생기면 제품 메뉴가 함께 선다. **생성일 때만** 돈다."""
    if created:
        _ensure("tenant")


@receiver(post_save, sender="role.Role", dispatch_uid="ux25_product_menus_on_role")
def on_role_created(sender, instance, created, **kwargs):
    """역할이 생기면 그 역할의 연결이 함께 선다.

    ★ 코드가 우리 묶음에 없으면 `ensure_product_menus` 가 알아서 아무것도 안 한다 —
      여기서 코드를 다시 걸러 내지 않는다. 거르개를 두 벌 두면 반드시 어긋난다(D-369).
    """
    if created:
        _ensure("role")
