# -*- coding: utf-8 -*-
"""PERF-04 / P-198 — **설정 읽기를 요청 한 벌 안에서 한 번만 한다** (2026-09-20 · 턴 X · 차선 F).

무엇을 고치는가 — 「아무 일도 안 하는 자리가 22개 질의를 쓴다」
----------------------------------------------------------------
[실측 2026-09-20 · `scripts/perf_breakdown.py` · `docs/agent/evidence/PERF-04/`]

`GET /api/dsm/dashboard/link-state` 의 **서비스는 DB 를 한 번도 안 읽는다**
(`services.link_state()` 는 SDN 준비 여부만 본다). 그런데 요청 한 벌이 **22개 질의**를
쓰고 파이썬을 **45ms** 쓴다. 프로파일이 이름을 댔다:

    core/configuration/utils.py:163  _get_config_sync         요청당 **6회**
      └ `AdminConfig.objects.filter(...)` + `len(configs)`    ← 전 행 전 칸을 가져온다
      └ `configs.values(fieldname)[0]`                        ← **두 번째 질의**
      └ `logger.info('Get config (…)')`                       ← 부를 때마다 로그 한 줄
    core/common/security/encryption.py:18  _derive_key        위를 부르는 주된 자리
      └ 세션 토큰을 풀 때마다(`get_session_token_parts`) 다시 부른다

    6회 × 2질의 = **12질의** · 프로파일 누적 **18.5ms/요청** = 요청 전체의 **41%**

그리고 이 저장소의 8000 은 **초당 22건에서 포화**한다 [실측 · 동시 곡선 1·2·4·10 이
정확히 선형]. 포화한 서버에서 `p95 ≈ 동시 × 한 벌 값` 이므로, **한 벌 값을 줄이는 것이
p95 를 줄이는 유일한 손잡이**다. 문턱 안으로 돌아오는 길이 여기다.

왜 dj-core 를 안 고치나
-----------------------
`core/configuration/utils.py` 와 `core/common/security/encryption.py` 는 **§0.4 금지구역**
(dj-core)이다. 한 자도 안 고친다. 대신 **길목에서 같은 답을 두 번 묻지 않게** 한다
(D-348 과 같은 규약) — 답을 바꾸지 않고, 묻는 횟수만 줄인다.

무엇을 **안** 하는가 — 이것이 이 파일의 안전선이다
--------------------------------------------------
1. **요청 한 벌보다 오래 들고 있지 않는다.** TTL 캐시가 아니다. 요청이 끝나면 버린다.
   운영자가 설정을 바꾸면 **바로 다음 요청**이 새 값을 읽는다. 「껐는데 아직 켜져 있다」가
   생길 수 있는 창이 없다.
2. **읽기 요청에서만 기억한다.** `POST`·`PUT`·`PATCH`·`DELETE` 는 한 자도 안 만진다 —
   같은 요청 안에서 설정을 **쓰고 다시 읽는** 자리가 있을 수 있고, 그 자리에서 기억은
   거짓말이 된다. 재야 하는 세 자리는 전부 GET 이다.
3. **값을 고치지 않는다.** 원 함수가 낸 것을 그대로 돌려준다. 기본값(`default`)이 다른
   호출은 **다른 열쇠**다 — 같은 이름이라도 기본값이 다르면 다시 묻는다.
4. **스레드를 넘지 않는다.** `threading.local()` 이다. 비동기 갈래
   (`get_config_async` · `ThreadPoolExecutor`)는 다른 스레드라 기억이 없고,
   기억이 없으면 **원래대로** 매번 묻는다. 끄는 것이 기본값인 쪽이다.

되돌리기는 한 줄이다: `CONFIG_READ_CACHE_ENABLED = False`.
`settings.py` 가 그 이름을 **환경에서도** 받는다(`CONFIG_READ_CACHE_ENABLED=false`) —
되돌리기 때문이 아니라 **재기 위해서**다: 같은 코드·같은 데이터·같은 창에서 이 한 칸만
바꿔 두 벌을 재야 「좋아진 것이 코드 덕인가」를 말할 수 있다.
"""
from __future__ import annotations

import logging
import threading

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed

logger = logging.getLogger("console")

#: 기억은 **요청 한 벌**만 산다. 요청 밖에서는 `None` 이고, `None` 이면 안 기억한다.
_state = threading.local()

#: 기억에 없다는 것과 「`None` 을 기억했다」를 가른다. dj-core 는 `None` 을 돌려줄 수 있고,
#: 그것을 「없음」으로 읽으면 캐시가 아무 일도 안 하게 된다.
_MISS = object()

#: 기억을 켜는 메서드. **읽기뿐이다** (위 안전선 2).
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

_install_lock = threading.Lock()
_installed = False


def enabled() -> bool:
    """되돌리기 한 줄. 이름이 없으면 **켜져 있다** — 이 파일은 답을 바꾸지 않기 때문이다."""
    return bool(getattr(settings, "CONFIG_READ_CACHE_ENABLED", True))


def begin() -> None:
    """이 요청의 기억을 연다."""
    _state.memo = {}


def end() -> None:
    """이 요청의 기억을 **버린다**. 안 버리면 다음 요청이 남의 답을 읽는다.

    ★ 스레드에 남은 것이 거짓 초록을 만든 일이 이 저장소에 이미 있었다 —
      그래서 `finally` 에서 부르고, 열 때도 **새 사전으로** 덮는다(둘 다 한다).
    """
    _state.memo = None


def install() -> bool:
    """dj-core 의 `_get_config_sync` 를 **한 번만** 감싼다. 감쌌으면 참.

    ★ 가장 안쪽을 감싼다. `get_config` · `get_config_value_by_path` 는 이 함수를
      **모듈 전역으로** 부르므로, 여기 하나를 감싸면 세 이름이 전부 덮인다.
      바깥 이름을 감싸면 `from … import get_config_value_by_path` 로 **이미 묶인**
      이름(`encryption.py` 가 그렇다)이 안 덮인다 — 그쪽이 가장 비싼 부르는 자리다.
    """
    global _installed
    with _install_lock:
        if _installed:
            return True
        try:
            from core.configuration import utils as cfg_utils
        except ImportError:                                   # pragma: no cover
            logger.warning("[CONFIG-CACHE] core.configuration.utils 가 없다 — 감싸지 않는다")
            return False
        original = getattr(cfg_utils, "_get_config_sync", None)
        if original is None:                                  # pragma: no cover
            logger.warning("[CONFIG-CACHE] _get_config_sync 가 없다 — dj-core 가 바뀌었다")
            return False
        if getattr(original, "_gx_config_cache", False):
            _installed = True
            return True

        def cached(name, fieldpath=None, default=None):
            memo = getattr(_state, "memo", None)
            if memo is None or not enabled():
                return original(name, fieldpath, default)
            #: 기본값이 다르면 **다른 물음**이다. 사전에 못 넣는 값이 올 수 있어 `repr`.
            key = (name, fieldpath, repr(default))
            got = memo.get(key, _MISS)
            if got is _MISS:
                got = original(name, fieldpath, default)
                memo[key] = got
            return got

        cached._gx_config_cache = True
        cached._gx_original = original
        cfg_utils._get_config_sync = cached
        _installed = True
        return True


#: ★ [D-377 · 2026-09-20] **관찰용·되돌리기용 도우미를 여기 두지 않는다.**
#:   `cached_reads()`(기억 항목 수)와 `uninstall()`(감싸개 벗기기)을 처음엔 여기 뒀는데,
#:   부르는 곳이 **시험뿐**이었다. 운영이 안 부르는 함수를 제품에 두면 다음 사람에게
#:   「있는 줄 알고 안 만드는 함정」이 된다 — `dormant` 게이트가 그 자리에서 빨개졌고,
#:   옳은 빨강이었다. 답은 **등재가 아니라 이사**다: 둘 다
#:   `backend/tests/test_f_config_read_cache.py` 로 옮겼다.
#:   ⚠ 되돌리기는 이 둘이 없어도 온전하다 — `CONFIG_READ_CACHE_ENABLED = False` 면
#:     겹은 `MiddlewareNotUsed` 로 **경로에서 빠지고**, 이미 감싼 뒤에 꺼도 `cached()` 가
#:     매번 `enabled()` 를 보고 원 함수로 그냥 지나간다. 벗길 필요가 없다.
#:   ⚠ `cached._gx_original` 은 **남겨 둔다** — 시험이 그것으로 벗기고, 그 이름이
#:     「여기 감싸개가 있다」를 코드에 적어 두는 자리다.


class ConfigReadCacheMiddleware:
    """요청 한 벌 동안만 설정 읽기를 기억한다. **응답은 한 자도 안 만진다.**

    자리: 설정을 읽는 어느 겹보다도 **바깥**이어야 한다. 안쪽에 두면 그 위의 겹들
    (인증·관문·로그)이 쓰는 읽기가 기억 밖에 남고, 그 읽기가 바로 제일 많은 쪽이다.
    """

    def __init__(self, get_response):
        if not enabled():
            #: 꺼져 있으면 **경로에서 빠진다** — 통과만 하는 겹을 남기지 않는다.
            raise MiddlewareNotUsed("CONFIG_READ_CACHE_ENABLED=False")
        self.get_response = get_response
        install()

    def __call__(self, request):
        if request.method not in SAFE_METHODS:
            #: 쓰기 요청은 한 자도 안 만진다. 기억이 없으면 원래대로 매번 묻는다.
            return self.get_response(request)
        begin()
        try:
            return self.get_response(request)
        finally:
            end()
