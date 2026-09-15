# -*- coding: utf-8 -*-
"""역할 대기 화면의 문 — **역할 0 계정이 닿는 유일한 자리** (P-105 · 2026-09-07 차선 B).

계약은 `docs/agent/evidence/P-105/backend/CONTRACT.md` 에 **코드보다 먼저** 적었다.
앞단(차선 F)이 같은 턴에 화면을 만들고 있고, 계약을 말로 주고받으면 갈린다.

이 문이 지키는 셋
-----------------
① **자족한다.** 역할 0 계정에게는 `/api/menu/menus` · `/api/config-management/*` ·
   `/api/user-groups/gen-schema` 가 전부 403 이다. 그러므로 역할 대기 화면이 그릴 것은
   **이 응답 하나에 다 있어야 한다** — 사람 이름 · 관리자 이름 · 알림 상태 · 문장.
② **자료를 안 싣는다.** 테넌트 자료는 한 자도 없다. 실리는 남의 이름은 「연락할
   관리자」 하나뿐이고, 그것이 이 화면의 존재 이유다.
③ **문장을 서버가 짓는다** (GX-COPY 규칙 1). 앞단은 `message` 를 그대로 그린다.

★ 역할이 **있는** 사람이 불러도 200 이다
----------------------------------------
`state: "has_roles"` 를 낸다. 403 이 아니다 — 이 문은 「역할이 있는가」를 묻는 문이고,
있다는 답도 답이다. 여기서 403 을 내면 앞단이 「이 문마저 막혔다」로 읽고, 그때 사람은
아무 문장도 못 본다.

★ `response=` 를 선언하지 않는다 (W0-18 · apps/dsm/api.py 와 같은 규율)
-----------------------------------------------------------------------
단일 스키마를 선언하면 거부 dict 가 그 스키마로 검증되며 **`200 + {}` 로 소멸**한다.
이 저장소가 8건에서 겪은 일이고, 새 라우트가 그 전철을 밟지 않는다.
"""
# ★ `from __future__ import annotations` 를 **일부러 쓰지 않는다** (D-378).
#   미래 임포트가 켜지면 ninja 가 주석을 문자열로 받아 `__globals__` 에서 푸는데,
#   데코레이터로 감싼 핸들러에서는 그 이름이 영영 안 풀린다 — `/api/dsm/events` 가
#   그 모양으로 운영에서만 500 이었다.
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common import role_request
from common.role_gate import has_no_role
from common.tenant_scope import tenant_scoped
from core.api.v1.auth import CustomJWTAuth


@api_controller("", tags=["Access — 역할 대기 (P-105)"])
class AccessAPI:
    """역할 부여 대기 상태를 말하는 문 하나."""

    @route.get("/role-pending", auth=CustomJWTAuth())
    # ★ `required=False` 는 형식이 아니라 **필요조건**이다 (D-275 §5-1 트립와이어).
    #
    #   ① 이 응답에는 테넌트 자료가 없다 — 부른 사람 자신의 신원과 관리자 이름뿐이다.
    #      좁힐 것이 없으므로 「검토했고 불필요하다」가 정확한 선언이다.
    #   ② 그리고 `required=True` 로 두면 **이 문이 스스로를 잠근다**: 역할 0 계정은
    #      소속(group)이 없는 경우가 흔하고([실측] `gxprobe_e2e`.group is None),
    #      차단 모드에서 `NoTenantGroupError` 가 난다. 그러면 역할 0 이 닿을 수 있는
    #      **유일한 문**이 역할 0 에게만 막히는 모양이 된다.
    #
    #   선언을 아예 빼면 `tests/test_route_tenant_scope.py` 의 래칫이 빨개진다
    #   (미분류 648 → 649). 그 래칫이 옳다 — 새 라우트는 자기 스코프를 말해야 한다.
    @tenant_scoped(required=False,
                   reason="P-105 역할 대기 — 응답에 테넌트 자료가 없다(부른 사람의 "
                          "신원과 관리자 이름뿐). 그리고 역할 0 계정은 소속이 없을 수 "
                          "있어 group 을 요구하면 이 유일한 문이 스스로를 잠근다")
    def role_pending(self, request):
        """이 계정에 역할이 있는가. 없으면 **관리자에게 알림 1건**을 남기고 알려 준다.

        ★ 인증이 없으면 **401 이다** — 403 이 아니다. 「누구인지 모른다」와
          「누구인지는 아는데 안 된다」는 다른 문장이다(D-290).
        """
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            raise HttpError(401, "인증이 필요합니다.")

        no_role = has_no_role(user)
        administrator = role_request.administrator_for(user)

        # ★ 알림은 **역할이 없을 때만** 나간다. 있는 사람이 이 문을 눌렀다고
        #   관리자 대장에 줄이 생기면 그 대장이 곧 못 쓰게 된다.
        if no_role:
            notification = role_request.notify_admin(user, administrator)
        else:
            notification = {"sent": False, "already_sent": False,
                            "channel": role_request.CHANNEL,
                            "requested_at": None, "error": None}

        try:
            roles = sorted(c for c in user.roles.values_list("code", flat=True) if c)
        except Exception:  # pragma: no cover - 역할 관계를 못 읽는 사용자 방어
            roles = []

        return {
            "state": "pending" if no_role else "has_roles",
            "message": role_request.message_for(administrator, has_roles=not no_role),
            "user": {
                "username": getattr(user, "username", "") or "",
                # ★ 자기 이름이다. 남의 것이 아니다 — 이 화면이 실어도 되는 유일한 신원.
                "display_name": role_request._display_name(user),
            },
            "roles": roles,
            "administrator": administrator,
            "notification": notification,
        }

    @route.get("/role-requests", auth=CustomJWTAuth())
    # ★ 관리자만 본다. `required=False` 인 이유는 위와 같다 — 이 목록은 테넌트 자료가
    #   아니라 **관리 대장**이고, 좁히기는 아래 `is_global_admin` 판정이 든다.
    @tenant_scoped(required=False,
                   reason="P-105 역할 요청 대장 — 관리 면이다. 테넌트 행이 아니라 "
                          "감사 대장을 읽고, 접근 판정은 tenant_roles 가 낸다")
    def role_requests(self, request):
        """**알림을 받는 쪽의 문** — 누가 역할을 기다리고 있는가.

        ★ 이 문이 왜 있나: 알림을 감사 대장에 쓰기만 하고 읽을 자리를 안 만들면
          `pending_requests()` 는 **아무도 부르지 않는 함수**가 된다. 이 저장소는 그것을
          「잠들어 태어났다」고 부르고(D-377), `scripts/verify_dormant.py` 가 실제로
          이 함수를 그렇게 잡았다 [실측 2026-09-07]. **함수는 문이 아니다** —
          `apps/dsm/services.py::review_event` 가 같은 이유로 두 달 동안 죽어 있었다.

        ★ 권한 판정을 여기서 **다시 세지 않는다**(D-212). 전역 관리자인지의 답은
          `common.tenant_roles.is_global_admin` 하나가 낸다.
        """
        from common.tenant_roles import is_global_admin, is_tenant_admin

        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            raise HttpError(401, "인증이 필요합니다.")
        if not (is_global_admin(user) or is_tenant_admin(user)):
            # 관리 대장이다. 관리자가 아닌 사람에게는 **없는 문**이 아니라 막힌 문이다.
            raise HttpError(403, "역할 요청 대장은 관리자만 봅니다.")

        rows = role_request.pending_requests()
        return {
            "count": len(rows),
            "requests": [
                {"audit_id": row.audit_id, "user_id": row.actor_id,
                 "reason": row.reason}
                for row in rows
            ],
        }
