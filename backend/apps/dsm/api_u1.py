# -*- coding: utf-8 -*-
"""WO-GX-20260915-01 §4.2 — 차선 **U1(관제요원)** 라우터 모듈. 이 파일은 U1 차선만 고친다.

왜 따로 있나 — `api.py`(공용부 · 기존 라우트 전부)를 차선 넷이 같은 턴에 고치면 충돌하고,
충돌한 라우트는 **라우팅 침묵**으로 나타난다(`urls.py` 머리말). 그래서 새 라우트는 차선
파일에서만 태어난다. **기존 라우트는 옮기지 않는다** — 선언 순서가 곧 라우팅이라, 옮기는
순간 어느 경로가 어느 경로를 삼키는지가 바뀐다(턴 Q 조율자 판정 · 반경 좁은 쪽).

⚠ `urls.py` 는 이 컨트롤러를 `DsmAPI` · `DsmLawAPI` **뒤에** 붙인다.
  - 기존 경로와 **같은 경로에 다른 메서드**를 여기서 더하지 않는다 — 앞 컨트롤러의 URL
    패턴이 먼저 잡고 405 를 낸다(라우트 삼킴 · P-100 계열). 새 일은 새 경로로.
  - 새 경로는 태어날 때 ISO-03(테넌트 스코프) · SEC-04(인증 관문) · 계약 도달을 통과한다.
"""
from django.http import Http404
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.idempotency import idempotent
from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import TenantScope, tenant_scoped

from apps.dsm import services


def _scope(request) -> TenantScope:
    """요청자에서 스코프를 만든다. **없으면 401.** `api.py::_scope` 와 같은 규약 —

    파일마다 새 인증 경로를 만들지 않는다. 이 한 줄은 `TenantScope.of` 를 감쌀
    뿐이고, 두 파일이 갈릴 자리가 아니다(공용부 `api.py` 는 조율자 소유라 이번
    턴에 그 파일을 손대지 않는다 — 대신 같은 세 줄을 여기 그대로 둔다).
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


@api_controller("", tags=["DSM — U1 관제요원 (WO-01 차선 U1)"])
class DsmU1API:
    """U1 차선의 새 라우트가 태어나는 자리(턴 Q 조율자 분할 · 처음엔 비어 있다)."""

    # ── 큐 카드 키 1 — 판정 + 접수 한 트랜잭션 (WO-01 §5 · AC-2) ───────────
    @route.post("/events/{int:event_id}/review-and-acknowledge",
               auth=JwtOrInboundKey())
    @tenant_scoped(reason="판정+접수 한 트랜잭션 쓰기 — 남의 이벤트를 판정·접수할 "
                         "수 없다 (쓰기 IDOR)")
    @idempotent("dsm.events.review-and-acknowledge")
    def review_and_acknowledge(self, request, event_id: int, reason: str = ""):
        """큐 카드 키 **1** — 「이 탐지는 진짜다, 그리고 내가 접수한다」를 한 번에.

        ★ 기존 `/review`(판정) · `/response`(접수) 라우트를 **대신하지 않는다.**
          둘은 그대로 살아 있다(오탐 3택은 여전히 `/review` 를 쓴다). 이 라우트는
          **새 경로**이고, 화면의 키 1 만 이 문을 부른다 — 기존 경로에 메서드를
          더하면 앞 컨트롤러가 먼저 잡아 405 를 내므로(라우트 삼킴), 더하지 않고
          새로 열었다.

        ★ 재사용: 판정값 검증·전이표·문지기·감사는 전부 `services.review_event`·
          `services.advance_response`(그 뒤 K1)에 있다. 여기서 다시 만들지 않는다.

        거절을 4xx 로 나눈다 — 두 소비 함수가 던지는 것을 **그대로** 옮긴다:
          404  없는 이벤트 · 남의 테넌트 이벤트
          422  판정값이 계약 밖(여기서는 나지 않는다 — 판정값이 고정이라)
          403  요청자가 없다(시스템 스코프) · 또는 되돌림 전용 조작이 관제팀장이
               아닌 사람에게서 왔다(이 라우트는 앞으로만 가므로 정상 경로에서는
               나지 않는다 — 그래도 소비 함수의 계약을 좁히지 않는다)
          409  그 전이 자체가 없다(예: 이미 종결된 사건) — **판정도 함께 롤백된다**
          400  되돌림에 사유가 비었다(이 라우트에서는 나지 않는다 — 같은 이유)
        """
        from common.tenant_scope import SystemScopeCannotRead

        try:
            return services.review_and_acknowledge(
                scope=_scope(request), event_id=event_id, reason=reason)
        except Http404:
            raise HttpError(404, "그런 이벤트가 없습니다.")
        except SystemScopeCannotRead as exc:
            raise HttpError(403, str(exc))
        except services.InvalidEventInput as exc:
            raise HttpError(422, str(exc))
        except services.ResponseTransitionNeedsManager as exc:
            raise HttpError(403, str(exc))
        except services.ResponseTransitionNeedsReason as exc:
            raise HttpError(400, str(exc))
        except services.ResponseTransitionForbidden as exc:
            raise HttpError(409, str(exc))
