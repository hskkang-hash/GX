# -*- coding: utf-8 -*-
"""전역 접근 관문 — **우리 층에서 길목을 막는다** (D-348 · D-343 ③).

왜 미들웨어인가 — §0.4 가 금지한 것은 「파일 수정」이지 「길목 차단」이 아니다
------------------------------------------------------------------------------
사고 ③에서 익명에게 데이터를 돌려주던 11자리 중 **2자리를 못 닫았다.**
`backend/delivery/views/api.py` 가 §0.4 금지구역이라 라우트 선언에 손을 댈 수 없었고,
forbidden-zone 게이트가 STOP 으로 잡았다. **게이트는 제 일을 했다** — 파일을 고치려 했으니까.

    [판정 D-348] D-207 이 금지한 것은 **그 파일을 수정하는 것**이다.
    그 경로로 가는 요청을 **우리 층에서 막는 것**은 금지된 적이 없다.
    바꿀 것은 게이트가 아니라 **막는 자리**다.

이 미들웨어는 우리 코드다. dj-core 도, `backend/delivery/` 도 **한 줄도 건드리지 않는다.**

무엇을 하나 — 규칙 둘
---------------------
  ① **들어오는 키 기본값 거절** (D-343 ③) — inbound 키를 들고 온 요청은
     `INBOUND_KEY_ALLOWED` 에 이름이 오른 자리에만 닿는다. 나머지는 401.
     ★ 라우트 선언의 `JwtOrInboundKey` 와 **같은 규칙을 한 겹 밖에서** 건다.
       선언은 우리가 고칠 수 있는 라우트만 덮고, 이 미들웨어는 **전부**를 덮는다 —
       §0.4 경로를 포함해서.
  ② **익명 거절** (D-348) — `AUTHN_REQUIRED_PREFIXES` 에 오른 경로는 자격증명 없는
     요청을 401 로 끊는다. 인증 관문이 라우트에 없어도 여기서 끊긴다.

★ 자리 — **캐시보다 바깥이어야 한다** (D-341 착시 ⑦)
----------------------------------------------------
`UniversalCacheMiddleware` 는 캐시 적중 시 뷰를 부르지 않고 저장된 본문을 200 으로 돌려준다.
이 관문을 캐시 **안쪽**에 두면, 열려 있던 동안 익명 키로 채워진 항목이 관문을 지나지 않고
그대로 나간다 — 2026-09-07 에 실제로 있었던 일이다(2자리가 고친 뒤에도 200).
그래서 `MIDDLEWARE` 에서 `UniversalCacheMiddleware` **위**에 둔다.
`common.api_contract.ApiContractStatusMiddleware` 가 같은 이유로 그 자리에 있다.

★ 응답은 **HTTP 상태로 말한다** (D-349 착시 ⑧)
----------------------------------------------
거절을 HTTP 200 봉투 안에 담지 않는다. 401 은 401 로 나간다.
「봉투는 200, 내용은 403」이 이 저장소가 방금 겪은 착시이고, 그 면을 우리가 새로 만들지 않는다.

되돌림
------
`settings.MIDDLEWARE` 에서 이 한 줄을 지우면 종전 동작이다. 데이터도 스키마도 건드리지 않는다.
"""
from __future__ import annotations

import re

from django.http import JsonResponse

from common.inbound_api_key import carries_inbound_key

#: ★ **들어오는 키가 닿아도 되는 자리 — 전부.** 이 집합이 곧 개방 선언이다(D-343 ②).
#: 늘리는 일은 손으로 이 줄을 더하는 일이고, 그 손이 「진입면을 넓힌다」는 선언이다.
#: `scripts/verify_route_inventory.py` 가 이 집합과 라우트 대장의
#: `inbound_key_allowed` 가 **같은지** 검사한다 — 갈리면 exit 1.
INBOUND_KEY_ALLOWED: frozenset[tuple[str, str]] = frozenset({
    ("GET", "/api/dsm/events"),
})

#: ★ **익명이 닿으면 안 되는 경로.** 라우트에 인증 관문이 없어도 여기서 끊는다.
#:
#: 지금 오른 넷은 §0.4(`backend/delivery/`)라 라우트 선언을 고칠 수 없는 자리다.
#: [실측 2026-09-08] 앞의 둘에서 익명에게 데이터가 나갔다:
#:     GET  /api/delivery/drone-monitoring/drone-status   17,416 B  드론 텔레메트리
#:     GET  /api/delivery/etri-mock/test-scenarios         1,976 B  시험 시나리오
#: 뒤의 둘은 같은 컨트롤러의 쓰기 면이다 — 한 자리를 막고 옆자리를 열면 사고는 그대로다.
#:
#: ★ 2026-09-10 넷이 더 올랐다 (D-364) — **측정기가 안 보여 주던 자리다.**
#: [실측] `probe_gap_route_settlement.py` 가 리다이렉트를 **따라가자** 드러났다:
#:     GET /api/orders/banks             200 · 87 B   익명 도달
#:     GET /api/orders/delivery-option   200 · 96 B   익명 도달
#:     GET /api/orders/payment-methods   200 · 97 B   익명 도달
#:     GET /api/orders/item-types        500          익명 도달(핸들러가 터졌다)
#: 직전 측정에서 이 넷은 **301** 로 찍혀 「본문 없음」 칸에 들어갔다. 301 은 관문의 답이
#: 아니라 `APPEND_SLASH` 의 답이었고, 따라가지 않았기 때문에 **관문이 있는 것처럼 보였다**
#: (D-350 — 측정기를 먼저 의심한다. 이번이 두 번째 적용이다).
#:
#: ★ 지금 `data: []` 가 나온다고 안전한 것이 아니다 — 그 표가 이 환경에서 비어 있을 뿐이다.
#:   행이 있는 환경에서는 같은 호출이 목록을 통째로 내놓는다 (D-301 「검사 못함 ≠ 0건」).
#: ★ `item-types` 는 터지므로 데이터가 안 나가지만 **함께 올린다.** 한 자리를 막고
#:   옆자리를 열면 사고는 그대로이고, 터지던 것이 고쳐지는 날 그 자리가 열린 채로 남는다.
#: `backend/orders/` 는 §0.4 다 — 라우트를 고치지 않고 **우리 층에서 막는다**(D-357).
AUTHN_REQUIRED_PATHS: tuple[str, ...] = (
    "/api/delivery/drone-monitoring/drone-status",
    "/api/delivery/etri-mock/test-scenarios",
    "/api/delivery/etri-mock/receive-delivery",
    "/api/orders/banks",
    "/api/orders/delivery-option",
    "/api/orders/payment-methods",
    "/api/orders/item-types",
)

#: 이 관문이 보는 면. API 밖(관리자·정적·문서)은 종전대로 둔다 — 넓히면 로그인 화면까지 막는다.
API_PREFIX = "/api/"

#: 인증 면 자체. 여기까지 막으면 **아무도 키를 받을 수 없다** — 관문이 문을 잠그고 열쇠를 삼킨다.
AUTHN_SURFACE = re.compile(r"^/api/(v1/)?(auth|token|login|logout|refresh|register)(/|$)")


def _has_credentials(request) -> bool:
    """자격증명을 **들고 왔는가**. 유효한지는 보지 않는다 — 그건 인증의 일이다.

    ★ 여기서 유효성까지 보면 이 미들웨어가 **두 번째 인증기**가 된다.
      인증기가 둘이면 언젠가 갈리고, 갈리면 어느 쪽이 맞는지 아무도 모른다(D-337 계열).
      이 관문이 답하는 질문은 하나다: **아무것도 없이 들어왔는가.**
    """
    if request.headers.get("Authorization") or carries_inbound_key(request):
        return True
    user = getattr(request, "user", None)
    return bool(user is not None and getattr(user, "is_authenticated", False))


def _denied(reason: str) -> JsonResponse:
    """거절은 **401 로** 나간다 — 200 봉투에 담지 않는다 (D-349).

    사유에 키·토큰·경로 파라미터를 넣지 않는다(D-335 규약 ④).
    """
    return JsonResponse({"detail": "Unauthorized", "reason": reason}, status=401)


def _normalize(path: str) -> str:
    return path.rstrip("/") or "/"


class AccessGateMiddleware:
    """규칙 둘을 한 자리에서 건다. **기본값은 거절이다.**"""

    def __init__(self, get_response):
        self.get_response = get_response
        self._allowed = {(m.upper(), _normalize(p)) for m, p in INBOUND_KEY_ALLOWED}
        self._authn_required = tuple(_normalize(p) for p in AUTHN_REQUIRED_PATHS)

    def __call__(self, request):
        verdict = self.judge(
            method=request.method,
            path=request.path,
            has_inbound_key=carries_inbound_key(request),
            has_credentials=_has_credentials(request),
        )
        if verdict is not None:
            return _denied(verdict)
        return self.get_response(request)

    # ── 술어 — 요청 객체 없이 시험할 수 있게 순수 함수로 둔다 ──────────────────
    def judge(self, *, method: str, path: str, has_inbound_key: bool,
              has_credentials: bool) -> str | None:
        """거절 사유를 돌려준다. 통과면 None.

        ★ 순서가 규칙이다. 인증 면을 **먼저** 비켜 준다 — 그러지 않으면
          키를 발급받는 길까지 막혀 아무도 이 시스템에 들어올 수 없다.
        """
        if not path.startswith(API_PREFIX):
            return None
        if AUTHN_SURFACE.match(path):
            return None

        key = (method.upper(), _normalize(path))

        # ① 들어오는 키 기본값 거절 (D-343 ③) — 선언한 자리에만 닿는다.
        if has_inbound_key and key not in self._allowed:
            return "inbound key is not allowed on this route"

        # ② 익명 거절 (D-348) — 라우트에 관문이 없어도 여기서 끊는다.
        if not has_credentials and _normalize(path) in self._authn_required:
            return "authentication required"

        return None
