# -*- coding: utf-8 -*-
"""O-05 「5xx」 — **앞문 응답 카운터** (턴 AR · 차선 N1 · 새 저장소 0).

`MIDDLEWARE` 의 맨 위 겹이 응답마다 (시간 칸, 상태 등급) 두 수를 센다. 저장소는 **이미
있는 캐시**(Redis)의 정수 키뿐이다 — 표도 파일도 새로 만들지 않고, 48 시간 뒤 스스로 사라진다.

정직한 한계 (건강 보드가 그대로 밝힌다)
--------------------------------------
* 센 것은 **Django 가 만든 응답**이다. nginx 가 뒷단에 못 닿아 스스로 낸 502/504 는 여기까지
  오지 않는다 — 그것은 `scripts/verify_front_line_502.py` 의 접근로그 대조 몫이다.
* 카운터가 켜진 시각 이전은 모른다. `since` 를 함께 낸다 — 0 건과 「아직 안 쟀다」를 가른다.
* 캐시가 죽으면 세지 못하고 응답은 그대로 나간다(카운터가 앞문을 막지 않는다).
"""
from __future__ import annotations

import logging
import time

from django.conf import settings
from django.core.cache import cache

log = logging.getLogger("guardianx.front_door")

PREFIX = "gx:frontdoor:"
BUCKET_SEC = 3600
TTL_SEC = 48 * 3600
WINDOW_HOURS = 24
SINCE_KEY = PREFIX + "since"


def enabled() -> bool:
    return bool(getattr(settings, "FRONT_DOOR_COUNTER_ENABLED", True))


def _bucket(now: float | None = None) -> int:
    return int((now if now is not None else time.time()) // BUCKET_SEC)


def _key(bucket: int, kind: str) -> str:
    return f"{PREFIX}{bucket}:{kind}"


def _bump(key: str) -> None:
    if cache.add(key, 1, TTL_SEC):
        return
    try:
        cache.incr(key)
    except ValueError:                              # 사이에 만료됐다 — 다시 만든다
        cache.add(key, 1, TTL_SEC)


def record(status_code: int, now: float | None = None) -> None:
    b = _bucket(now)
    cache.add(SINCE_KEY, int(now if now is not None else time.time()), None)
    _bump(_key(b, "total"))
    if status_code >= 500:
        _bump(_key(b, "5xx"))


def snapshot(now: float | None = None, hours: int = WINDOW_HOURS) -> dict:
    """최근 `hours` 시간의 (전체, 5xx). 못 읽으면 `measured=False` — 0 으로 덮지 않는다."""
    try:
        b = _bucket(now)
        keys = [_key(b - i, k) for i in range(hours) for k in ("total", "5xx")]
        got = cache.get_many(keys)
        total = sum(v for k, v in got.items() if k.endswith(":total"))
        errs = sum(v for k, v in got.items() if k.endswith(":5xx"))
        since = cache.get(SINCE_KEY)
    except Exception:                               # noqa: BLE001
        return {"measured": False, "window_hours": hours}
    if not since or total == 0:
        return {"measured": False, "window_hours": hours, "total": total, "5xx": errs,
                "since": since}
    return {"measured": True, "window_hours": hours, "total": total, "5xx": errs,
            "rate_pct": round(100.0 * errs / total, 3), "since": since,
            "scope": "Django 가 낸 응답(nginx 자체 502/504 는 제외)"}


class FrontDoorCounterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if enabled():
            try:
                record(response.status_code)
            except Exception:                       # noqa: BLE001 — 카운터가 응답을 막지 않는다
                log.debug("front door counter failed", exc_info=True)
        return response


__all__ = ["FrontDoorCounterMiddleware", "record", "snapshot", "enabled"]
