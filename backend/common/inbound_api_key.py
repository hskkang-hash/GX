# -*- coding: utf-8 -*-
"""**들어오는** API Key 의 문지기 — F-05 진입면 (D-335).

「같은 이름, 다른 것」 (D-337)
-----------------------------
    outbound (나가는) 키 = 우리가 남의 API 를 부를 때 쓴다. 표 ②(K5 자격증명 저장처)가 관리한다
    inbound  (들어오는) 키 = 남의 App 이 우리 이벤트 OpenAPI 를 부를 때 쓴다. **이 파일이 그것이다**

둘 다 "API Key" 라 불려서 한 번 오판했다(D-337). 그래서 이 모듈의 이름에 방향을 박는다.

★ 만들지 않았다 — 이미 열려 있었다 (D-335 · 2026-09-07 실측)
------------------------------------------------------------
착수하면서 알게 된 것: dj-core 의 `CustomJWTAuth` 는 **이미** inbound 키 헤더와
`Authorization` 의 inbound 스킴을 받는다(core/api/v1/auth.py:136·168). 즉 들어오는 키는
**만들 것이 아니라 이미 살아 있었고, 아무도 그 범위를 정하지 않았다.**

호출로 잰 것 [실측] — 키 하나로 F-05 진입면 7자리에 전부 닿았다:

    GET /api/dsm/events               도달      GET /api/dsm/events/{id}/clip         도달
    GET /api/dsm/deliveries           도달      GET /api/dsm/events/{id}/clip/stream  도달  ★ 원본 영상
    GET /api/dsm/dashboard/frame  200 도달      GET /api/dsm/reports/templates    200 도달
    GET /api/dsm/settings/{domain}    도달

    (만료된 키 401 · 비활성 키 401 · 가짜 키 401 — **인증 자체는 성했다.**
     성하지 않은 것은 **범위**다.)

`clip/stream` 이 계약 11조(영상 반출)의 자리다(D-306). 발급된 아무 키나 거기 닿는 상태는
「들어오는 키를 아직 안 만들었다」가 아니라 **「범위 없이 이미 열어 두었다」**이다.

이 파일이 하는 일 — **좁히기 하나**
-----------------------------------
라우트마다 **들어오는 키를 받을지**를 선언하게 한다. 선언하지 않은 라우트는 키를 거절한다.
JWT(사람 로그인) 경로는 건드리지 않는다 — 좁히는 것은 키 갈래뿐이다.

    @route.get("/events", auth=JwtOrInboundKey(inbound_key=True, reason="F-05 이벤트 조회"))
    @route.get("/events/{id}/clip/stream", auth=JwtOrInboundKey())   # 키 거절 — 기본값

★ **기본값이 거절이다.** 새 라우트가 아무 선언 없이 생기면 키가 닿지 않는다.
  이것이 D-300(부작위) 의 모양이다 — 「열어 준 것」이 아니라 **「안 열린 것」**이 기본이어야
  새 라우트가 조용히 표면을 넓히지 못한다.

규약 (D-335) 과 이 파일의 대응
------------------------------
  ① 키는 테넌트에 묶인다      → 키의 소유자를 request.user 로 세우고 `@tenant_scoped` 가 좁힌다
                                 (dj-core 가 이미 그렇게 한다. 우리는 그 사용자를 그대로 쓴다)
  ② HTTPS 강제                → `settings.INBOUND_API_KEY_REQUIRE_HTTPS` 가 참이면 평문 거절
  ③ 읽기 전용부터            → 쓰기 메서드에는 `inbound_key=True` 를 **줄 수 없다**(생성 시 거부)
  ④ 키 값을 저장하지 않는다   → 이 파일은 원문 키를 **어디에도 쓰지 않는다.**
                                 로그에도 남기지 않는다 — 거절 사유에 키를 넣지 않는다
  ⑤ 부작위                    → 원본 영상·타 테넌트 식별자에 닿는 경로가 0건임을 시험이 잰다
                                 (`backend/tests/test_f05_inbound_api_key.py`)

§0.4 — dj-core 는 **읽고 호출만** 한다 (D-207 · D-335)
    `CustomJWTAuth` 를 고치지 않는다. 감싼다. 금지구역 안으로 손을 넣지 않는다.
"""
from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest

from core.api.v1.auth import CustomJWTAuth

#: 들어오는 키가 실려 오는 자리. dj-core 가 보는 자리와 **같아야** 한다
#: (`core/api/v1/auth.py::get_api_key_from_request` · `CustomJWTAuth.__call__`).
#: 여기가 좁으면 우리가 못 본 갈래로 키가 들어오고, 그러면 이 문지기는 있으나 마나다.
INBOUND_KEY_HEADER = "X-API-Key"
INBOUND_AUTHORIZATION_SCHEMES = ("apikey",)

#: 쓰기 메서드. ③ 읽기 전용부터 — 여기에 키를 열어 주려면 절을 따로 세운다.
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def carries_inbound_key(request: HttpRequest) -> bool:
    """이 요청이 **들어오는 키**를 들고 왔는가. 값은 보지 않는다 — 유무만 본다.

    ★ 키 값을 읽어서 돌려주지 않는다(규약 ④). 이 함수가 값을 반환하면
      부르는 쪽이 그것을 로그에 넣게 되고, 그 순간 키가 평문으로 남는다.
    """
    if request.headers.get(INBOUND_KEY_HEADER):
        return True
    # 이름에 갈래를 박는다 (D-342): 여기서 보는 것은 **인증(authn)** 헤더다.
    # 「auth」 단독은 인가(authz)로도 읽힌다 — 그 혼동이 사고 ①을 만들었다.
    authn_header = request.headers.get("Authorization", "")
    scheme = authn_header.split(" ", 1)[0].lower() if authn_header else ""
    return scheme in INBOUND_AUTHORIZATION_SCHEMES


def _require_https() -> bool:
    """평문 요청을 거절할 것인가.

    기본값은 **`DEBUG` 가 아니면 참**이다 — 운영에서 켜져 있는 것이 기본이고,
    개발에서 끄는 것이 예외다. 그 반대로 두면 「운영에서 켜는 것을 잊는」 쪽이 기본이 된다.
    """
    return bool(getattr(settings, "INBOUND_API_KEY_REQUIRE_HTTPS", not settings.DEBUG))


class JwtOrInboundKey(CustomJWTAuth):
    """JWT 는 그대로, **들어오는 키는 선언한 라우트에서만** 통과시킨다.

    `CustomJWTAuth` 를 상속하되 **고치지 않는다** — 키 갈래일 때만 앞에서 끊고,
    나머지는 부모에게 그대로 넘긴다(§0.4 · D-207).

    · `inbound_key=False`(기본): 키를 들고 온 요청은 **여기서 끝난다.** 401
    · `inbound_key=True`: HTTPS 를 확인한 뒤 부모에게 넘긴다
    """

    def __init__(self, *, inbound_key: bool = False, reason: str = "", **kwargs):
        super().__init__(**kwargs)
        if inbound_key and not reason:
            # 사유 없는 개방은 다음 사람에게 "왜 열렸는지 모르는 문"이다 (D-264 계열).
            raise ValueError(
                "inbound_key=True 에는 reason 이 필요하다 — 어느 절이 이 개방을 부르는가"
            )
        self.inbound_key = inbound_key
        self.reason = reason

    def __call__(self, request: HttpRequest):
        if carries_inbound_key(request):
            if not self.inbound_key:
                # ③⑤ — 선언하지 않은 라우트에는 키가 닿지 않는다. **기본값이 거절이다.**
                return None
            if _require_https() and not request.is_secure():
                # ② 키가 평문으로 흐르면 키가 아니다. 사유에 키를 넣지 않는다(④).
                return None
            user = super().__call__(request)
            if user is None:
                return None                      # 인증이 안 됐다 — 401 이다
            _assert_request_key_scope(request, user)   # 범위 밖이면 **403**
            return user
        return super().__call__(request)


def inbound_key_id(request: HttpRequest) -> int | None:
    """이 요청이 들고 온 **들어오는 키의 id.** 못 찾으면 `None`.

    ★ 값을 돌려주지 않는다(규약 ④) — 돌려주는 것은 **정수 하나**다. 앞 8자
      (`prefix`)만으로 행을 찾는다. `prefix` 는 `InboundKeyView` 가 이미 사람에게
      보여 주는 칸이고, 그것만으로는 인증되지 않는다.
    ★ dj-core 표는 **읽기만** 한다 (§0.4 · D-207). `apps.get_model` 로 가져온다 —
      `kernels/k5_trust/inbound_keys.py` 와 같은 규약이다.
    """
    raw = request.headers.get(INBOUND_KEY_HEADER) or ""
    if not raw:
        authn_header = request.headers.get("Authorization", "") or ""
        head, _, rest = authn_header.partition(" ")
        if head.lower() in INBOUND_AUTHORIZATION_SCHEMES:
            raw = rest
    raw = raw.strip()
    if not raw:
        return None

    from django.apps import apps

    row = (apps.get_model("apikey_account", "APIKey").objects
           .filter(prefix=raw[:8], is_active=True)
           .values_list("pk", flat=True).first())
    return None if row is None else int(row)


def _assert_request_key_scope(request: HttpRequest, user) -> None:
    """이 키로 이 경로를 부를 수 있는가. 아니면 **403**.

    ★ **요청을 아는 자리는 여기 하나다** (D-335 · `key_scopes.py` 머리말). 커널은
      HTTP 를 모른다 — 그래서 경로와 키 id 를 **여기서** 꺼내 `assert_path_scope`
      에 넘긴다. 판정식은 커널 한 곳이고 이 함수는 옮기기만 한다(D-212).
    ★ 키를 못 찾으면 **막지 않는다.** 이 갈래에는 dj-core 의 파트너 키(`pk_…`)도
      들어오는데 그 키는 `apikey_account` 행이 아니다 — 여기서 거절하면 범위와
      무관한 갈래가 조용히 죽는다. 그 갈래의 좁히기는 `INBOUND_KEY_ALLOWED`
      (경로 자체를 연 목록)가 이미 한 겹 하고 있다.
    ★ 401 이 아니라 **403** 이다 — 인증은 성했고 권한이 없다(연계 명세 §4).
    """
    from ninja.errors import HttpError

    from common.tenant_scope import TenantScope
    from kernels.k5_trust import KeyScopeDenied, assert_path_scope

    key_id = inbound_key_id(request)
    if key_id is None:
        return
    try:
        assert_path_scope(scope=TenantScope.of(user), key_id=key_id,
                          path=request.path)
    except KeyScopeDenied as exc:
        raise HttpError(403, str(exc))


def inbound_key_routes(surface) -> list[tuple[str, str]]:
    """등록된 라우트 중 **들어오는 키를 받는** 것을 열거한다 — 부작위 시험의 눈이다.

    `surface` 는 `(method, path, auth_callbacks)` 를 내놓는 것이면 무엇이든 된다.
    시험이 런타임 레지스트리를 넘긴다 — 정적 grep 이 아니다.
    """
    out = []
    for method, path, callbacks in surface:
        for cb in callbacks or []:
            if isinstance(cb, JwtOrInboundKey) and cb.inbound_key:
                out.append((method, path))
                break
    return sorted(set(out))
