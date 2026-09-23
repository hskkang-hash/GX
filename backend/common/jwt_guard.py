# -*- coding: utf-8 -*-
"""P-274 — **틀린 자격은 거절한다.** 못 푸는 `Bearer` 한 줄을 500 이 아니라 401 로 낸다.

무엇을 고치는가 — 그리고 **무엇을 안 고치는가**
------------------------------------------------
[실측 2026-09-23 · 턴 AF · 조율자] 읽기 면 364자리에 **아무 글자나** 실은
`Authorization: Bearer` 를 보내면 **364자리 전부가 HTTP 500** 이다.
자료는 안 샜다(유출 0/364) — 그러나 그 0 은 「거절해서」가 아니라 **「죽어서」**다.

뿌리는 dj-core 다(§0.4 금지구역 — 읽기·호출만):

    site-packages/core/middleware/refresh_token.py
        try:
            decoded = AccessToken(token)          # ← 쓰레기 글자면 여기서 터진다
            ...
        except Exception as e:
            payload = jwt.decode(token, ...)      # ← **잡는 자리에서 다시 터진다**
                                                  #    이 줄엔 try 가 없다

곧 `except` 가 예외를 **처리하는 게 아니라 새로 만든다.** 잡는 사람이 없으니 500 이고,
미들웨어라 **모든 요청**에 걸린다 — 그래서 364자리 전부다.

★★ **우리는 dj-core 를 한 줄도 안 고친다.** 저 파일보다 **바깥**에 이 겹을 세워, 저
   자리가 아예 그 글자를 못 보게 한다. 고치는 게 아니라 **앞에서 답하는 것**이다.

★★ **우리는 판단하지 않는다 — dj-core 가 터질지를 미리 물을 뿐이다**
--------------------------------------------------------------------
[조율자 턴 AG 오판 ①] 처음 판은 「구조적으로 못 푸는 글자」만 잡았다. 그러자 실측이
**절반만 고쳐졌다**:

    쓰레기 Bearer          → 401 ✅
    모양만 JWT · 서명 틀림 → **500 ❌ 그대로**

코드를 끝까지 읽고서야 까닭을 알았다. dj-core 의 `except` 갈래는 **서명을 검사하며**
다시 읽는다(`verify_signature=True` · `verify_exp=False`) — 그러니 터지는 집합은
「못 푸는 글자」가 아니라 **「서명이 안 맞는 글자」**다. 구조는 멀쩡하고 서명만 틀린
토큰은 첫 판을 그대로 지나가 dj-core 에서 터졌다.
⇒ **한 겹을 세우고 절반만 재고 초록이라 부르지 않는다.**

그래서 이 겹의 술어를 **dj-core 의 두 걸음을 그대로 흉내 내는 것**으로 바꿨다:

    ① `AccessToken(token)` 이 서면      → dj-core 의 `try` 가 산다 → **통과**
    ② 아니면 dj-core 가 하듯 서명을 검사하며 다시 읽는다
       · 서면  → dj-core 가 회복한다(만료 토큰이 이 자리다) → **통과**
       · 터진다 → dj-core 가 **바로 여기서 500 을 낸다** → **401**

  ⇒ 이 겹은 **아무것도 통과시키지 않는다.** 하는 일은 거절뿐이고, 거절하는 대상은
    **지금 500 이 나고 있는 바로 그 요청**이다. 그 밖은 한 건도 안 바뀐다.
  ⇒ 두 번째 인증기가 아닌 까닭이 여기 있다. 인증기는 **무엇을 받아들일지**를 정한다 —
    이 겹은 받아들이는 자리가 없다. `common/access_gate.py::_has_credentials` 의
    「인증기가 둘이면 언젠가 갈린다」는 경고는 **받아들이는 쪽**의 이야기다.

★★ **만료 토큰은 건드리지 않는다**
-----------------------------------
서명이 유효하고 `exp` 만 지난 토큰은 ② 에서 **선다** — dj-core 가 지금 하는 일
(그 사용자의 미만료 토큰을 블랙리스트에 넣는 부수 효과 포함)을 그대로 한다.
⇒ 만료 토큰이 고객에게 무엇으로 보이는지는 턴 AF 에 **못 쟀고 지금도 안 쟀다**
  (서명 비밀키로 표본을 만들어야 한다). 못 잰 것을 고친 척하지 않는다.

되돌리기
--------
`JWT_GUARD_ENABLED = False` **한 줄**이다. 그 한 줄이면 이 겹은 통과만 한다.

⚠ 파일 자리 [조율자 턴 AG]
--------------------------
지시서 WO-GX-20260925-10 §3 은 `backend/common/middleware/jwt_guard.py` 로 적었는데,
**이 저장소의 잰 관례는 `common/` 바로 아래 평면**이다 — `schema_header` ·
`config_read_cache` · `error_body` · `rate_limit_body` · `wall_token` · `access_gate` ·
`role_gate` · `session_limit` · `api_contract` 가 전부 그렇다 [실측: `common/middleware/`
디렉터리가 **없다**]. 같은 종류를 두 자리에 나누면 다음 사람이 겹을 찾을 때 **두 곳을
봐야 하고, 한 곳만 보면 못 찾는다.** 그래서 관례를 따랐고 이 줄로 알린다 — 세종이
디렉터리 쪽이 옳다고 판정하면 옮기는 것은 한 줄이다.
"""
from __future__ import annotations

import logging
from typing import Any

import jwt
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

#: 되돌리기 한 줄. 없으면 켜진 것으로 본다(새 겹은 켜져야 일을 한다).
SETTING_NAME = "JWT_GUARD_ENABLED"

#: 답 본문의 기계 낱말. 화면은 이 낱말이 아니라 `message` 를 읽는다.
UNDECODABLE_CODE = "credential_undecodable"

#: 고객 말. dj-core 의 답 모양(`success`/`status`/`message` 4개 국어)과 같은 틀이다
#: — 앞단이 이미 그 틀을 읽는다(`frontend/src/features/dsm/api.ts`).
MESSAGE = {
    "ko": "자격 증명을 읽을 수 없습니다. 다시 로그인해 주십시오.",
    "en": "The credential could not be read. Please sign in again.",
    "vi": "Không thể đọc thông tin xác thực. Vui lòng đăng nhập lại.",
    "th": "ไม่สามารถอ่านข้อมูลรับรองได้ กรุณาเข้าสู่ระบบอีกครั้ง",
}

#: dj-core 가 읽는 자리 **둘 다** 본다 [실측: refresh_token.py 가
#: `HTTP_AUTHORIZATION` 과 `Authorization` 를 차례로 본다]. 한 자리만 보면
#: 다른 자리로 온 글자가 이 겹을 지나쳐 그대로 500 이 된다.
HEADER_KEYS = ("HTTP_AUTHORIZATION", "Authorization")

PREFIX = "Bearer "


def enabled() -> bool:
    return bool(getattr(settings, SETTING_NAME, True))


def bearer_token(request: Any) -> str | None:
    """`Bearer ` 뒤의 글자. 없거나 빈 값이면 `None`.

    ★ 빈 값(`"Bearer "` 한 줄)은 **이 겹의 일이 아니다** — 실측상 그것은 이미 401 이다
      (관문이 「자격증명 없음」으로 읽는다). 여기서 또 401 을 내면 같은 사실을 두 겹이
      말하게 되고, 나중에 한 겹을 고칠 때 다른 겹이 그 변화를 덮는다.
    """
    meta = getattr(request, "META", None) or {}
    for key in HEADER_KEYS:
        raw = meta.get(key)
        if not raw or not str(raw).startswith(PREFIX):
            continue
        token = str(raw)[len(PREFIX):].strip()
        if token:
            return token
    return None


def would_djcore_raise(token: str) -> bool:
    """**dj-core 가 이 글자로 터지는가.** 우리가 정책을 만들지 않고 그쪽을 흉내 낸다.

    흉내 내는 원본 [실측 2026-09-23 · site-packages/core/middleware/refresh_token.py]:

        try:
            decoded = AccessToken(token)        # ① 서면 여기서 끝
        except Exception as e:
            payload = jwt.decode(token, SIGNING_KEY, verify_signature=True,
                                 verify_exp=False, leeway=60)   # ② try 가 **없다**
            ... 미만료 토큰 블랙리스트 ...

    ② 가 터지면 잡는 사람이 없어 **500** 이다. 그 경우에만 참을 낸다.

    ★ 비밀은 **넘기기만** 한다 — 이 함수는 키를 찍지도 돌려주지도 않는다(D-204).
    ★ 두 번 읽는 값은 dj-core 가 읽는 것과 **같은 설정 자리**다. 우리 쪽에 상수를
      새로 두면 언젠가 두 값이 갈리고, 갈리면 이 겹이 조용히 다른 문을 지킨다.
    """
    try:
        from ninja_jwt.tokens import AccessToken
        AccessToken(token)
        return False                                  # ① dj-core 의 try 가 산다
    except Exception:                                 # noqa: BLE001
        pass
    conf = getattr(settings, "NINJA_JWT", None) or {}
    try:
        jwt.decode(
            token,
            conf.get("SIGNING_KEY") or getattr(settings, "SECRET_KEY", ""),
            algorithms=[conf.get("ALGORITHM", "HS256")],
            options={"verify_exp": False, "verify_signature": True},
            leeway=60,
        )
    except Exception:                                 # noqa: BLE001
        return True                                   # ② dj-core 가 여기서 500 을 낸다
    return False                                      # ② 가 서면 dj-core 가 회복한다


def undecodable_response() -> JsonResponse:
    resp = JsonResponse(
        {"success": False, "status": 401, "code": UNDECODABLE_CODE, "message": MESSAGE},
        status=401, json_dumps_params={"ensure_ascii": False})
    resp["Cache-Control"] = "no-store"
    #: 401 의 규약 헤더. 없으면 고객 쪽이 「무엇으로 다시 오라는 것인지」를 모른다.
    resp["WWW-Authenticate"] = 'Bearer error="invalid_token"'
    return resp


class JwtGuardMiddleware:
    """못 푸는 `Bearer` 하나만 401 로 옮긴다. 그 밖의 요청은 한 자도 안 만진다."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not enabled():
            return self.get_response(request)
        token = bearer_token(request)
        if token is not None and would_djcore_raise(token):
            logger.info("[JWT_GUARD] %s %s — dj-core 가 터질 Bearer → 401 (500 이 아니다)",
                        getattr(request, "method", "?"), getattr(request, "path", "?"))
            return undecodable_response()
        return self.get_response(request)
