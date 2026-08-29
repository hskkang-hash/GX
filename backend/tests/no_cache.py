# -*- coding: utf-8 -*-
"""캐시 우회 한 자리 — **관문을 재는 시험이 캐시를 재면 안 된다** (D-341 착시 ⑦).

왜 상수를 한 곳에 두나
----------------------
[실측 2026-09-07 · D-334 INCIDENT §5] 익명에게 열려 있던 자리를 고친 **뒤에** 다시 때렸는데
**2자리가 여전히 200** 이었다. `UniversalCacheMiddleware` 가 열려 있던 동안 익명 키로 채운
항목을 코드 수정 뒤에도 그대로 돌려준 것이다. 캐시가 없었다면 그 2자리는 **「고쳤다」로
보고됐을 것**이다.

그 헤더 이름이 **미들웨어가 보는 자리와 한 글자라도 다르면** 우회는 일어나지 않고,
시험은 조용히 캐시를 잰다 — 그리고 초록이다. 그래서 이름을 한 곳에 둔다.

    · 미들웨어가 보는 자리: `common/universal_optimization.py::UniversalOptimizer
      .should_cache_request()` — `request.headers.get('X-No-Cache') == 'true'`
    · Django 테스트 클라이언트는 WSGI 환경 이름을 받는다 → `HTTP_X_NO_CACHE`

    from tests.no_cache import NO_CACHE
    client = Client(**NO_CACHE)          # 캐시 처리: 우회

우회가 불가능한 자리는 **비우고 시작한다**(`django.core.cache.cache.clear()`), 그리고
어느 쪽이든 **「캐시 처리: 우회 / 비움 / 해당 없음 — 사유」 한 줄**을 남긴다.
`scripts/verify_cache_bypass.py` 가 그 한 줄을 센다.
"""
from __future__ import annotations

#: 캐시를 우회하는 헤더 (WSGI 환경 이름).
NO_CACHE = {"HTTP_X_NO_CACHE": "true"}
