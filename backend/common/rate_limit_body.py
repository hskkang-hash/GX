# -*- coding: utf-8 -*-
"""SEC-21 — 율제한 초과 응답을 **JSON · 한국어 · 남은 초**로 낸다 (턴 T · 차선 F).

무엇이 문제였나 [실측 2026-09-17 · Django 테스트 클라이언트 · `tests/test_sec21_login_ratelimit.py`]
--------------------------------------------------------------------------------------
`POST /api/v1/auth/login` 은 dj-core 가 `@ratelimit(key='ip', rate='5/m', block=True)`
로 막는다(`core/api/v1/auth.py:348`). 여섯 번째 부름의 답은 이랬다:

    403 · text/html · "<h1>403 Forbidden</h1>" · Retry-After 없음

`django_ratelimit.exceptions.Ratelimited` 는 `PermissionDenied` 의 자식이라 Django 가
**영문 HTML 403** 으로 옮긴다. 화면은 그것을 「이 계정에는 접근 권한이 없습니다」
(403 갈래)로 읽었다 — 사람이 할 일은 **기다림**인데 화면은 **관리자 문의**를 말했다.
PRD v2.7 SEC-21 의 정의: 「율제한 응답은 JSON · 한국어 · 화면 카운트다운」.

무엇을 하나 — **파일이 아니라 길목을 막는다** (D-348)
--------------------------------------------------
dj-core 의 데코레이터는 §0.4 금지구역이라 못 고친다. 이 겹은 뷰 밖으로 나온
`Ratelimited` 를 `process_exception` 에서 받아 다음으로 바꾼다:

    429 · application/json · Retry-After: <초>
    {"success": false, "status": 429, "code": "rate_limited",
     "retry_after_seconds": <초>,
     "message": "요청이 너무 잦습니다. <초>초 뒤 다시 시도해 주십시오."}

★ 남은 초는 **지어내지 않는다.** `django_ratelimit.core.get_usage(increment=False)` 가
  같은 창(window)의 `time_left` 를 낸다. 그 호출에 필요한 (group · key · rate · method)
  는 데코레이터가 닫아 둔 변수(`inspect.getclosurevars`)에서 **읽는다** — 숫자를 여기
  다시 적으면 두 벌이 되고 두 벌은 어긋난다(D-212). 못 읽으면 `retry_after_seconds`
  는 **`RATELIMIT_FALLBACK_SECONDS`**(기본 60) 로 떨어지고 `retry_after_source`
  가 `"fallback"` 이라 말한다 — 「측정」과 「짐작」을 같은 칸에 두지 않는다(D-290).

★ 이 겹은 `Ratelimited` **만** 본다. 다른 `PermissionDenied` 는 한 자도 안 만진다 —
  `SafeErrorBodyMiddleware.PASSTHROUGH` 가 Django 에게 넘기는 흐름 제어 그대로다.

되돌리기: `settings.MIDDLEWARE` 에서 이 줄 하나를 뺀다(영문 HTML 403 으로 돌아간다).
"""
from __future__ import annotations

import inspect
import logging
from typing import Any

from django.conf import settings
from django.http import JsonResponse

try:  # django_ratelimit 이 없는 환경에서도 임포트가 죽지 않게 — 그런 환경엔 율제한도 없다
    from django_ratelimit.exceptions import Ratelimited
except Exception:  # pragma: no cover
    class Ratelimited(Exception):  # type: ignore[no-redef]
        pass

logger = logging.getLogger(__name__)

#: 남은 초를 못 읽었을 때 화면에 줄 수. **측정이 아니라 짐작**이고, 본문의
#: `retry_after_source="fallback"` 이 그 사실을 말한다.
DEFAULT_FALLBACK_SECONDS = 60

RATE_LIMITED_CODE = "rate_limited"


def rate_limited_message(seconds: int) -> str:
    """율제한 문장 한 줄. 사전 GX-COPY_v1 §5 「율제한」 항목과 같은 글자다."""
    return f"요청이 너무 잦습니다. {int(seconds)}초 뒤 다시 시도해 주십시오."


def _closure_of(fn: Any) -> dict[str, Any]:
    try:
        return dict(inspect.getclosurevars(fn).nonlocals)
    except (TypeError, ValueError):
        return {}


def _ratelimit_params(view: Any) -> dict[str, Any] | None:
    """`@ratelimit` 이 닫아 둔 (group · fn · key · rate · method) 를 찾는다.

    ninja 경로: `resolver_match.func` 는 `PathView._sync_view`(바운드) → 그 `__self__` 의
    `_find_operation` 이 준 `Operation.view_func` 가 데코레이터의 `_wrapped` 다.
    장고 일반 뷰: `resolver_match.func` 자체가 `_wrapped` 다.
    """
    candidates = [view]
    owner = getattr(view, "__self__", None)
    if owner is not None and hasattr(owner, "operations"):
        for op in getattr(owner, "operations", []) or []:
            candidates.append(getattr(op, "view_func", None))
    for cand in candidates:
        cur = cand
        for _ in range(6):  # 데코레이터 겹을 따라 내려간다 — 무한히는 아니다
            if cur is None:
                break
            vars_ = _closure_of(cur)
            if "rate" in vars_ and "fn" in vars_ and "key" in vars_:
                return vars_
            cur = getattr(cur, "__wrapped__", None)
    return None


def seconds_left(request: Any) -> tuple[int, str]:
    """(남은 초, 출처). 출처는 `"measured"` 또는 `"fallback"`."""
    fallback = int(getattr(settings, "RATELIMIT_FALLBACK_SECONDS", DEFAULT_FALLBACK_SECONDS))
    match = getattr(request, "resolver_match", None)
    view = getattr(match, "func", None)
    params = _ratelimit_params(view) if view is not None else None
    if not params:
        return fallback, "fallback"
    try:
        from django_ratelimit import ALL
        from django_ratelimit.core import get_usage

        usage = get_usage(
            request,
            group=params.get("group"),
            fn=params.get("fn"),
            key=params.get("key"),
            rate=params.get("rate"),
            method=params["method"] if "method" in params else ALL,
            increment=False,
        )
    except Exception as exc:  # noqa: BLE001 — 측정 실패는 짐작으로, 그리고 표지를 남긴다
        logger.warning("[RATE_LIMIT_BODY] 남은 초를 못 읽었다 — %s", exc)
        return fallback, "fallback"
    left = int((usage or {}).get("time_left", -1) or -1)
    if left <= 0:
        return fallback, "fallback"
    return left, "measured"


def rate_limited_response(request: Any) -> JsonResponse:
    left, source = seconds_left(request)
    body = {
        "success": False,
        "status": 429,
        "code": RATE_LIMITED_CODE,
        "retry_after_seconds": left,
        "retry_after_source": source,
        "message": rate_limited_message(left),
    }
    resp = JsonResponse(body, status=429, json_dumps_params={"ensure_ascii": False})
    resp["Retry-After"] = str(left)
    resp["Cache-Control"] = "no-store"
    return resp


class RateLimitBodyMiddleware:
    """`Ratelimited` 하나만 429 JSON 으로 옮긴다. 그 밖의 예외는 한 자도 안 만진다."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, Ratelimited):
            return None
        logger.info("[RATE_LIMIT_BODY] %s %s 율제한 → 429", request.method, request.path)
        return rate_limited_response(request)
