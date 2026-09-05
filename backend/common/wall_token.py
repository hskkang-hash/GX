# -*- coding: utf-8 -*-
"""UX-24a — **월(wall) 표시 토큰**. 세션이 아니다. 쓰기가 0 이다.

무엇이 문제였나 [실측 턴 E · `docs/agent/authn_paths.md` §8]
------------------------------------------------------------
이 제품은 **동시 접속이 1개**다. `user.token` 이 CharField **한 칸**이고 로그인이 그것을
덮어쓴다(`core/user/models.py:577` · `core/api/v1/auth.py:706`). 관제실은 월 대형화면 ·
자리 데스크톱 · 휴대전화를 **동시에** 켜는데, 월을 켜면 자리가 튕긴다.

그 한 칸은 §0.4(dj-core)라 우리가 못 고친다. 그것이 UX-24b 이고 **손 밖**이다.

★ 세종 판정 P-62 — **월 모드는 세션이 필요 없다**
-------------------------------------------------
그래서 문을 쪼갰다. 월은 **세션을 세우지 않는 다른 문**으로 들어온다:

    · 읽기 전용 (**쓰기 0**)
    · 유효 12시간
    · 화면 `/wall` 하나만 — 그 화면이 부르는 두 문만 열린다
    · `user.token` 을 **한 자도 만지지 않는다** → 자리 데스크톱 세션이 산다

★ 왜 JWT 로 만들지 않았나 — **영역을 갈랐다**
---------------------------------------------
JWT 를 발급하면 그것은 `Authorization: Bearer` 자리에 실린다. 그 자리는 dj-core 가 보고,
그러면 이 토큰은 **제품 전체의 문**이 된다 — 월 한 장을 위해 문 하나를 통째로 여는 것이다.
`/api/token/pair` 를 뺀 이유(D-411)가 정확히 그것이었다: **쓸모없는 토큰을 내주는 문은
기능이 아니라 공격 면이다.** 여기서 같은 모양을 새로 만들지 않는다.

    헤더   `X-GX-Wall-Token`                      — `Authorization` 이 아니다
    서명   HMAC(SECRET_KEY, "gx.ux24a.…v1")       — JWT 열쇠와 **같은 값이 될 수 없다**
    검증   이 파일                                 — dj-core 는 이 토큰을 아예 못 본다

즉 월 토큰을 `Authorization` 에 실어도 통하지 않고, JWT 를 `X-GX-Wall-Token` 에 실어도
통하지 않는다. 두 문은 **서로의 열쇠로 열리지 않는다.**

★ 「쓰기 0」을 두 겹으로 막는다
------------------------------
  ① `WallTokenMiddleware` — `AccessGateMiddleware` **위**. 쓰기 메서드와 목록 밖 경로를
     **403** 으로 끊는다. §0.4(delivery·orders·terminals)를 포함한 **모든** 라우트를 덮는다.
  ② `JwtOrWallToken(wall_token=True, …)` — **선언한 라우트만** 월 토큰을 받는다.
     선언 없는 라우트는 거절이 기본값이다(`JwtOrInboundKey` 와 같은 규약 · D-335 ③⑤).

한 겹이면 충분한가 — 아니다. ②만 있으면 §0.4 안에 새 라우트가 나는 날 그 자리가 선언 없이
열릴 수 있고, ①만 있으면 목록을 늘리는 손이 곧 개방이 된다. **둘을 함께 두면 어느 한쪽을
늘려도 다른 쪽이 남는다.**

발급과 회수 — `docs/agent/authn_paths.md` §9-3 이 대장이다
----------------------------------------------------------
    발급   python manage.py wall_token issue  --user <계정>      (U5 시스템 관리자 · 서버에서)
    회수   python manage.py wall_token revoke --jti <jti>        (캐시 · 12시간)
    전부   python manage.py wall_token revoke --all              (WALL_TOKEN_EPOCH 를 올린다)
    끄기   settings.WALL_TOKEN_ENABLED = False                   (되돌리기 한 줄)

★ 발급 문을 **HTTP 에 내지 않았다.** 월 토큰은 한 달에 몇 번 나가는 물건이고, 그런 것에
  상시 열린 문을 주지 않는다. 발급 문 자체가 새 공격면이다.

⚠ **회수 목록은 캐시다.** 재기동하면 비고 개별 회수가 사라진다 — 숨기지 않는다. 그래서
  급한 회수는 캐시가 아니라 설정값에 둔 `--all` 이 답이다.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
import secrets
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse

from common.inbound_api_key import JwtOrInboundKey

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# 규약 — 값 하나하나가 판정이다
# ═══════════════════════════════════════════════════════════════════════════

#: 이 토큰이 실려 오는 자리. **`Authorization` 이 아니다** — 그 자리는 dj-core 의 것이다.
WALL_TOKEN_HEADER = "X-GX-Wall-Token"

#: 토큰 머리말. 판을 이름에 박는다 — 규약이 바뀌면 옛 토큰이 **조용히** 통하지 않게.
WALL_TOKEN_PREFIX = "gxwall1"

#: 유효 12시간 (세종 판정 P-62). 한 교대(8h)를 넘기고 이틀은 못 넘긴다.
#: ★ 발급기만이 아니라 **검증기도** 이 값을 본다 — `exp - iat` 가 이보다 크면 서명이
#:   맞아도 거절한다. 발급기를 우회해 손으로 찍은 장수명 토큰을 막는 자리다.
WALL_TOKEN_TTL_SECONDS = 12 * 60 * 60

#: 읽기 메서드. **쓰기 0 은 여기서 시작한다.**
#: `OPTIONS` 는 CORS 예비 요청이라 넣는다 — 아무것도 안 내주고 아무것도 안 바꾼다.
WALL_TOKEN_READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

#: ★ **월 토큰이 닿아도 되는 자리 — 전부.** 이 tuple 이 곧 개방 선언이다.
#:
#: 손으로 고른 것이 아니라 **화면에서 읽었다** [실측 2026-09-05]:
#:     frontend/src/features/dsm/pages/Wall.tsx:177      dsmEndpoint.eventsQueue
#:     frontend/src/features/dsm/hooks/useCameraPulse.ts CAMERA_PULSE_PATH
#: 화면이 문을 하나 더 부르기 시작하면 그 문은 **여기에 손으로 올라와야** 한다.
#: 그 손이 「진입면을 넓힌다」는 선언이다(D-343 ② · `INBOUND_KEY_ALLOWED` 와 같은 규약).
WALL_TOKEN_PATHS: tuple[str, ...] = (
    "/api/dsm/events/queue",
    "/api/dsm/cameras/pulse",
)

#: 이 토큰이 여는 **화면**. 하나다 — 대장(`authn_paths.md` §9)이 그렇게 적혀 있다.
WALL_SCREEN_PATH = "/wall"

#: 서명 열쇠의 영역 문자열. **JWT 열쇠와 같은 값이 될 수 없게** 하는 자리다.
_KEY_PURPOSE = b"gx.ux24a.wall-display-token.v1"

#: 회수 목록의 캐시 열쇠.
_REVOKE_KEY = "gx:ux24a:wall:revoked:%s"


def wall_token_enabled() -> bool:
    """되돌리기는 이 한 줄이다 (`settings.WALL_TOKEN_ENABLED = False`)."""
    return bool(getattr(settings, "WALL_TOKEN_ENABLED", True))


def wall_token_epoch() -> int:
    """이 시각 **이전에 발급된 토큰은 전부 죽는다** (`--all` 회수).

    캐시가 아니라 설정값이다 — 재기동해도 살아 있어야 하는 판정이기 때문이다.
    """
    try:
        return int(getattr(settings, "WALL_TOKEN_EPOCH", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _signing_key() -> bytes:
    """서명 열쇠. **`SECRET_KEY` 를 그대로 쓰지 않는다.**

    그대로 쓰면 다른 목적의 서명과 같은 열쇠가 되고, 한쪽에서 새면 다른 쪽이 함께 열린다.
    목적 문자열로 한 겹 유도해서 **이 용도에서만 쓰이는 값**을 만든다(영역 분리).
    """
    secret = (settings.SECRET_KEY or "").encode("utf-8")
    return hmac.new(secret, _KEY_PURPOSE, hashlib.sha256).digest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


# ═══════════════════════════════════════════════════════════════════════════
# 발급 · 검증 — **순수하다**. 시각을 인자로 받는다(부르는 쪽이 재현할 수 있게)
# ═══════════════════════════════════════════════════════════════════════════

def issue(user_id: int, *, now: float | None = None, note: str = "") -> tuple[str, dict]:
    """월 표시 토큰 한 장. `(토큰, 주장)` 을 돌려준다.

    ★ 수명은 인자가 아니다. 12시간 **하나**다 — 부르는 쪽이 고를 수 있으면 언젠가
      누군가 30일을 고르고, 그 순간 이 절의 판정이 사라진다.
    """
    now = int(time.time() if now is None else now)
    claims = {
        "v": 1,
        "sub": int(user_id),
        "jti": secrets.token_hex(8),
        "iat": now,
        "exp": now + WALL_TOKEN_TTL_SECONDS,
        "scope": "wall",
        "screen": WALL_SCREEN_PATH,
    }
    if note:
        claims["note"] = note[:80]
    payload = _b64(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    body = f"{WALL_TOKEN_PREFIX}.{payload}"
    sig = hmac.new(_signing_key(), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64(sig)}", claims


def verify(token: str | None, *, now: float | None = None) -> tuple[dict | None, str]:
    """`(주장, 사유)`. 통과하면 사유는 빈 문자열이다.

    ★ 사유에 토큰을 **넣지 않는다** (D-335 규약 ④). 사유는 어휘 하나이고, 그 어휘가
      로그에 남는다 — 토큰이 로그에 남으면 그것은 더 이상 비밀이 아니다.
    """
    if not wall_token_enabled():
        return None, "disabled"
    if not token:
        return None, "no_token"
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != WALL_TOKEN_PREFIX:
        return None, "malformed"

    body = f"{parts[0]}.{parts[1]}"
    expected = hmac.new(_signing_key(), body.encode("ascii"), hashlib.sha256).digest()
    try:
        given = _unb64(parts[2])
    except (binascii.Error, ValueError):
        return None, "malformed"
    # ★ 상수 시간 비교. `==` 로 비교하면 서명을 한 바이트씩 맞춰 볼 수 있다.
    if not hmac.compare_digest(expected, given):
        return None, "bad_signature"

    try:
        claims = json.loads(_unb64(parts[1]).decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None, "malformed"
    if not isinstance(claims, dict):
        return None, "malformed"

    if claims.get("v") != 1 or claims.get("scope") != "wall":
        return None, "malformed"
    if not isinstance(claims.get("sub"), int) or not isinstance(claims.get("jti"), str):
        return None, "malformed"

    iat, exp = claims.get("iat"), claims.get("exp")
    if not isinstance(iat, int) or not isinstance(exp, int):
        return None, "malformed"
    # ★ 서명이 맞아도 수명이 규약보다 길면 거절한다 — 발급기를 우회한 장수명 토큰을 막는다.
    if exp - iat > WALL_TOKEN_TTL_SECONDS:
        return None, "ttl_too_long"
    now = int(time.time() if now is None else now)
    if now >= exp:
        return None, "expired"
    if iat < wall_token_epoch():
        return None, "epoch"          # `--all` 로 전부 끊었다
    if is_revoked(claims["jti"]):
        return None, "revoked"
    return claims, ""


def revoke(jti: str) -> None:
    """토큰 한 장을 끊는다. 회수 목록의 수명은 **토큰 수명과 같다** —
    이미 만료된 토큰의 회수 기록을 들고 있을 이유가 없다."""
    cache.set(_REVOKE_KEY % jti, "1", WALL_TOKEN_TTL_SECONDS)


def is_revoked(jti: str) -> bool:
    try:
        return cache.get(_REVOKE_KEY % jti) is not None
    except Exception:                                   # noqa: BLE001
        # ⚠ 캐시가 죽었을 때 「회수 안 됐다」로 읽는다. 그 사실을 적어 둔다 —
        #   회수의 최종 수단은 캐시가 아니라 `--all`(WALL_TOKEN_EPOCH)이다.
        logger.warning("[UX-24a] 회수 목록을 못 읽었다 — 회수는 --all 로 한다")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# 요청에서 읽기
# ═══════════════════════════════════════════════════════════════════════════

def token_of(request: HttpRequest) -> str | None:
    value = (request.headers.get(WALL_TOKEN_HEADER) or "").strip()
    return value or None


def carries_wall_token(request: HttpRequest) -> bool:
    """월 토큰을 **들고 왔는가.** 유효한지는 보지 않는다 — 그건 검증기의 일이다.

    `carries_inbound_key` 와 같은 규약이다: 값을 돌려주지 않는다(값을 돌려주면
    부르는 쪽이 그것을 로그에 넣는다 · D-335 ④).
    """
    return token_of(request) is not None


def _user_of(claims: dict):
    """주장의 주인. 못 찾으면 None — **없는 사용자로 통과시키지 않는다.**"""
    try:
        from django.contrib.auth import get_user_model

        return get_user_model().objects.filter(id=claims["sub"]).first()
    except Exception:                                   # noqa: BLE001
        return None


def _normalize(path: str) -> str:
    return path.rstrip("/") or "/"


def _denied(status: int, reason: str) -> JsonResponse:
    """거절은 **HTTP 상태로** 말한다 — 200 봉투에 담지 않는다 (D-349 착시 ⑧).

    401 과 403 을 가른다: 「누구인지 모른다」와 「알겠는데 그건 못 한다」는 다른 사실이고,
    둘을 뭉치면 월 화면이 「토큰이 죽었다」로 읽고 재발급을 부른다.
    """
    detail = "Unauthorized" if status == 401 else "Forbidden"
    return JsonResponse({"detail": detail, "reason": reason}, status=status)


# ═══════════════════════════════════════════════════════════════════════════
# ① 미들웨어 — **모든** 라우트를 덮는 겹
# ═══════════════════════════════════════════════════════════════════════════

class WallTokenMiddleware:
    """월 토큰을 들고 온 요청에만 손댄다. 그 밖의 요청은 **한 자도 안 만진다.**

    ★ 자리 — `AccessGateMiddleware` **바로 위**(즉 응답 캐시보다 바깥).
      두 이유가 있다:
        ① 캐시보다 안쪽에 두면, 캐시에 적중한 월 요청이 이 겹을 **지나지 않고** 나간다
           (D-341 착시 ⑦ — 관문을 캐시 안쪽에 두어 실제로 겪은 일이다).
        ② `request.user` 를 여기서 세워야 캐시 열쇠가 **그 사용자 것**이 된다
           (`generate_universal_cache_key` 가 `request.user` 로 서명을 만든다).
           안 세우면 월 응답이 익명 칸에 담기고, 그 칸은 남과 공유된다.

    ★ 순서가 곧 판정이다 — 메서드를 **경로보다 먼저** 본다. 목록에 있는 경로로 쓰기를
      때렸을 때 「경로가 아니다」가 아니라 **「쓰기다」**라고 말해야, 다음 사람이 목록을
      늘려도 쓰기가 열리지 않는다는 것을 읽는다.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._paths = frozenset(_normalize(p) for p in WALL_TOKEN_PATHS)

    def __call__(self, request):
        if not carries_wall_token(request):
            return self.get_response(request)

        verdict = self.judge(
            method=request.method,
            path=request.path,
            token=token_of(request),
            has_authorization=bool(request.META.get("HTTP_AUTHORIZATION")),
        )
        if verdict is not None:
            status, reason = verdict
            logger.info("[UX-24a] 월 토큰 거절 %s %s — %s", request.method, request.path, reason)
            return _denied(status, reason)

        claims, _ = verify(token_of(request))
        user = _user_of(claims or {})
        if user is None:
            return _denied(401, "unknown_user")
        # 캐시 열쇠와 테넌트 좁히기가 이 사용자로 서게 한다. **세션은 안 세운다** —
        # `user.token` 은 한 자도 안 만진다. 그것이 이 절의 전부다.
        request.user = user
        request.gx_wall_claims = claims
        return self.get_response(request)

    def judge(self, *, method: str, path: str, token: str | None,
              has_authorization: bool) -> tuple[int, str] | None:
        """거절이면 `(상태, 사유)`, 통과면 None. **순수하다** — 시험이 이것만으로 전부 잰다."""
        if not wall_token_enabled():
            return 401, "disabled"
        # 한 요청에 자격증명 둘. 어느 것으로 판정할지가 애매해지는 자리는 **닫는다** —
        # 낮은 권한 토큰이 높은 권한 헤더에 얹혀 가는 모양(혼동된 대리인)을 만들지 않는다.
        if has_authorization:
            return 401, "two_credentials"
        claims, reason = verify(token)
        if claims is None:
            return 401, reason
        if (method or "").upper() not in WALL_TOKEN_READ_METHODS:
            return 403, "read_only"                     # ★ 쓰기 0
        if _normalize(path) not in self._paths:
            return 403, "scope_path"
        return None


# ═══════════════════════════════════════════════════════════════════════════
# ② 라우트 선언 — **선언한 자리만** 월 토큰을 받는다
# ═══════════════════════════════════════════════════════════════════════════

class JwtOrWallToken(JwtOrInboundKey):
    """JWT·들어오는 키는 부모 그대로, **월 토큰은 선언한 라우트에서만** 통과시킨다.

    · `wall_token=False`(기본): 월 토큰을 들고 온 요청은 **여기서 끝난다** → 401
    · `wall_token=True`: 서명·수명·회수를 확인하고 그 사용자를 세운다. **읽기만.**

    ★ 기본값이 거절이다 — 새 라우트가 아무 선언 없이 생기면 월 토큰이 닿지 않는다.
      `JwtOrInboundKey` 가 들어오는 키에 세운 규약과 같다(D-335 ③⑤ · D-300 부작위).
    """

    def __init__(self, *, wall_token: bool = False, wall_reason: str = "", **kwargs):
        super().__init__(**kwargs)
        if wall_token and not wall_reason:
            # 사유 없는 개방은 다음 사람에게 「왜 열렸는지 모르는 문」이다.
            raise ValueError(
                "wall_token=True 에는 wall_reason 이 필요하다 — 월 화면의 어느 칸이 이 문을 부르는가"
            )
        self.wall_token = wall_token
        self.wall_reason = wall_reason

    def __call__(self, request: HttpRequest):
        if carries_wall_token(request):
            if not self.wall_token:
                return None                             # 선언하지 않은 라우트 — 거절이 기본값
            if (request.method or "").upper() not in WALL_TOKEN_READ_METHODS:
                return None                             # ★ 쓰기 0 — 미들웨어와 **같은 술어**
            claims, _reason = verify(token_of(request))
            if claims is None:
                return None
            user = _user_of(claims)
            if user is None:
                return None
            request.user = user
            request.gx_wall_claims = claims
            return user
        return super().__call__(request)


def wall_token_routes(surface) -> list[tuple[str, str]]:
    """등록된 라우트 중 **월 토큰을 받는** 것을 열거한다 — 부작위 시험의 눈이다.

    `surface` 는 `(method, path, auth_callbacks)` 를 내놓는 것이면 무엇이든 된다.
    시험이 런타임 레지스트리를 넘긴다 — 정적 grep 이 아니다
    (`inbound_key_routes` 와 같은 모양 · 같은 이유).
    """
    out = []
    for method, path, callbacks in surface:
        for cb in callbacks or []:
            if isinstance(cb, JwtOrWallToken) and cb.wall_token:
                out.append((method, path))
                break
    return sorted(set(out))


__all__ = [
    "JwtOrWallToken",
    "WALL_SCREEN_PATH",
    "WALL_TOKEN_HEADER",
    "WALL_TOKEN_PATHS",
    "WALL_TOKEN_PREFIX",
    "WALL_TOKEN_READ_METHODS",
    "WALL_TOKEN_TTL_SECONDS",
    "WallTokenMiddleware",
    "carries_wall_token",
    "is_revoked",
    "issue",
    "revoke",
    "token_of",
    "verify",
    "wall_token_enabled",
    "wall_token_epoch",
    "wall_token_routes",
]
