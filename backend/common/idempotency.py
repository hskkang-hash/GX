# -*- coding: utf-8 -*-
"""멱등 키 — **같은 의도는 한 번만 자원을 만든다** (P-87 · 2026-09-06 턴 I · 차선 C)

무엇이 문제였나 — **화면만 막고 있었다** [실측 · 턴 H · `features/dsm/api.ts`]
-----------------------------------------------------------------------------
턴 H 가 `Idempotency-Key` 를 화면에서 싣기 시작했고, 그 파일은 스스로 이렇게 적어
두었다: 「⚠ **서버 신호 대기.** 이 저장소의 어느 라우트도 이 이름을 아직 읽지 않는다
[실측 · 저장소 전수 검색 0건]. 그러므로 이 헤더는 지금 **서버에서 아무 일도 하지
않는다.**」 — 그 문장이 참이었다. 브라우저 안의 약속 재사용이 전부였고, 그것은
**한 브라우저 안**에서만 산다. 새로고침·두 탭·모바일과 자리 화면·재시도는 못 막는다.

★ 이 모듈이 그 문장을 거짓으로 만든다. **서버가 키를 본다.**

무엇을 하는가 — 세 줄
---------------------
  ① 헤더가 **없으면 아무 일도 하지 않는다.** 이 모듈이 붙기 전과 한 글자도 다르지 않다.
  ② 같은 (사람 · 문 · 키) 로 **성공했던** 요청이 창 안에 있으면, 손을 대지 않고
     **그때 준 답을 그대로 돌려준다** — 새 자원이 생기지 않는다.
  ③ 같은 키가 **지금 날아가는 중**이면 409 다. 두 번째 요청이 첫 번째를 앞질러
     자원을 하나 더 만드는 자리가 정확히 거기다.

★ **실패는 기억하지 않는다.** 500·409·422 로 끝난 요청의 키를 창에 넣어 두면
  「고친 뒤 같은 키로 다시 시도」가 영원히 옛 실패를 받는다. 재시도할 수 없는 멱등은
  멱등이 아니라 고장이다. 그래서 **성공한 답만** 기억한다.

★ **키는 사람에 매인다.** 저장 키에 요청자 신원을 넣는다 — 안 넣으면 남이 고른 UUID
  하나로 **남의 답을 받아 갈 수 있다**(우연이 아니라 공격으로). 테넌트 격리를 라우트
  마다 세워 놓고 이 자리에서 새면 그 전부가 무의미하다.

⚠ **저장소는 Redis 캐시다 — 영구 저장이 아니다.** 캐시가 비면 창도 비고, 같은 키의
  두 번째 요청은 새 요청이 된다. 그것이 이 구현이 **못 하는 일**이고 여기 적어 둔다.
  DB 표로 올리는 것은 이관(migration)이 필요한 일이라 이 턴의 자리가 아니다.
  지금 막는 것은 「사람이 두 번 누른다 · 화면이 두 번 보낸다」이고, 그 창은 초 단위다.
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging

from django.core.cache import cache
from ninja.errors import HttpError

logger = logging.getLogger(__name__)

#: 화면과 **같은 이름**이다 (`frontend/src/features/dsm/api.ts` 의 `IDEMPOTENCY_HEADER`).
#: 이름을 두 벌로 적으면 언젠가 한 벌만 바뀐다.
IDEMPOTENCY_HEADER = "Idempotency-Key"

#: 답을 들고 있는 창. 사람의 두 번 누름은 초 단위이고, 화면의 재시도는 분 단위다.
IDEMPOTENCY_WINDOW_SEC = 600

#: 날아가는 중 표시의 수명. 이보다 오래 걸리는 요청은 이 자리의 문제가 아니다.
INFLIGHT_TTL_SEC = 60

#: 키 길이 상한 — 캐시 키를 사람이 정하는 자리다. 해시로 접지만 상한도 둔다.
MAX_KEY_LEN = 200

_STORE_PREFIX = "gx:idem:v1:"


def _requester(request) -> str:
    """이 키가 **누구의 것인가.** 못 알아내면 그 사실을 값으로 낸다 — 익명끼리
    답을 나눠 갖지 않도록 원격 주소까지 섞는다."""
    user = getattr(request, "user", None)
    uid = getattr(user, "id", None) if user is not None else None
    if uid:
        return "u%s" % uid
    key_id = getattr(request, "inbound_api_key_id", None)
    if key_id:
        return "k%s" % key_id
    meta = getattr(request, "META", {}) or {}
    return "anon:%s" % meta.get("REMOTE_ADDR", "?")


def _store_key(door: str, request, key: str) -> str:
    raw = "|".join([door, request.method or "", request.path or "",
                    _requester(request), key])
    return _STORE_PREFIX + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def idempotent(door: str):
    """이 문에 멱등 키를 **읽게** 한다.

    쓰는 법 — `@route.post(...)` · `@tenant_scoped(...)` **아래**에 붙인다.
    그래야 테넌트 문지기를 먼저 지나고(남의 자원인지 먼저 가른다), 그 뒤에
    「같은 의도인가」를 묻는다. 순서를 뒤집으면 **남의 문 앞에서 답을 캐시**한다.
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(self, request, *args, **kwargs):
            key = (request.headers.get(IDEMPOTENCY_HEADER) or "").strip()
            #: ① 헤더가 없으면 **이 모듈은 없는 것과 같다**
            if not key or len(key) > MAX_KEY_LEN:
                return fn(self, request, *args, **kwargs)

            sk = _store_key(door, request, key)
            cached = cache.get(sk)
            if cached is not None:
                #: ② 같은 의도의 **성공했던 답**. 손을 대지 않는다 — 새 자원이 없다.
                logger.info("idempotent replay door=%s", door)
                try:
                    return json.loads(cached)
                except Exception:      # 저장이 깨졌으면 **막지 않는다**
                    cache.delete(sk)

            lock = sk + ":inflight"
            if not cache.add(lock, "1", INFLIGHT_TTL_SEC):
                again = cache.get(sk)
                if again is not None:
                    try:
                        return json.loads(again)
                    except Exception:
                        pass
                #: ③ 앞의 것이 아직 날아간다. **여기서 하나 더 만들지 않는다.**
                raise HttpError(409, "같은 요청이 이미 처리 중입니다. 잠시 뒤 결과를 확인해 주십시오.")

            try:
                result = fn(self, request, *args, **kwargs)
            except Exception:
                #: **실패는 기억하지 않는다** — 고쳐 다시 보낼 수 있어야 한다
                cache.delete(lock)
                raise

            try:
                cache.set(sk, json.dumps(result, default=str), IDEMPOTENCY_WINDOW_SEC)
            except Exception:          # 기억하지 못해도 **이 요청은 성공했다**
                logger.warning("idempotent store failed door=%s", door)
            cache.delete(lock)
            return result

        wrapper.__gx_idempotent_door__ = door
        return wrapper
    return deco
