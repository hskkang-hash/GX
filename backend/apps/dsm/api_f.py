# -*- coding: utf-8 -*-
"""WO-GX-20260915-01 §4.2 — 차선 **F(기반)** 라우터 모듈. 이 파일은 F 차선만 고친다.

규약은 `api_u1.py` 머리말과 같다: 기존 라우트는 옮기지 않는다 · `DsmAPI`·`DsmLawAPI` 뒤에
붙으므로 기존 경로에 다른 메서드를 더하지 않는다(405 삼킴) · 새 경로는 ISO-03·SEC-04·계약
도달을 태어날 때 통과한다.

★ `from __future__ import annotations` 를 **일부러 쓰지 않는다** (`api.py` D-378 과 같은 사유).

이 파일이 여는 것 — 온보딩 진행률 하나 (UX-46)
-----------------------------------------------
    GET /api/dsm/onboarding/progress

계산은 전부 `apps/dsm/onboarding.py` 에 있다. 여기는 그 결과를 HTTP 로 얇게 연다
(`api_u24.py` 가 `stats.py` 를 얇게 여는 것과 같은 모양).

★ **역할 홈의 띠 수를 내주는 새 라우트를 만들지 않았다.** 띠가 그리는 세 수(미처리 ·
  미판정 · 오탐률)의 자리는 이미 있다(`GET /events/summary`) — 같은 수를 내는 문을 하나
  더 열면 두 문이 갈리고, 갈린 수는 감사 앞에서 못 쓴다(`stats.py` 머리말 AC-5 와 같은
  이유). 홈은 그 문을 그대로 부르고, 그래서 **띠의 수 = 목록의 수**가 구조로 성립한다.
"""
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import TenantScope, tenant_scoped


def _scope(request) -> TenantScope:
    """요청자에서 스코프를 만든다. **없으면 401.** `api.py::_scope` 와 같은 규약 —

    파일마다 새 인증 경로를 만들지 않는다.
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


@api_controller("", tags=["DSM — 역할 홈·온보딩 (WO-01 차선 F)"])
class DsmFAPI:
    """F 차선의 새 라우트 — UX-46 온보딩 진행률."""

    # ── UX-46 온보딩 진행률 ──────────────────────────────────────────────
    #
    # ★ **라우트 삼킴을 먼저 본다** (D-410). `/onboarding/...` 은 기존 어느 컨트롤러의
    #   변수 조각 밑에도 없다 — `api.py` 의 변수 조각은 `/events/{int:event_id}` ·
    #   `/law/privacy-requests/{no}` 뿐이고 둘 다 다른 가지다. 그래서 이 경로는
    #   **삼킬 수 없는 자리**에 태어난다(순서를 외우는 것보다 안전하다).
    @route.get("/onboarding/progress", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-46 온보딩 진행률 — 남의 테넌트 카드·기록이 섞이면 격리 실패다")
    def onboarding_progress(self, request):
        """내 역할의 「처음 시작하기」 카드와 그 진행률.

        ★ **사람이 체크하는 문이 아니다.** 이 응답의 `done` 은 전부 서버 기록이 닫은 것이고,
          무엇이 닫았는지는 `source_ref` 가 말한다(`event#4812` · `handover#7` 처럼).
          닫는 문(POST)은 **열지 않았다** — 열면 그것이 체크박스다(WO-01 §12).

        ★ 못 재는 카드는 `blocked` 로 **이름과 사유와 함께** 나간다. 분모에서 지우지
          않는다 — 지우면 진행률이 조용히 올라가고 그 수는 거짓이다(D-301).

        ★ 역할을 못 읽으면 카드가 0장이고 `percent` 는 **`null`** 이다 — 0 도 100 도 아니다.
        """
        from apps.dsm import onboarding

        return onboarding.progress(scope=_scope(request))
