#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-105 ① — **역할 없는 계정이 무엇을 읽는가**를 호출로 분류한다. 읽어서 답하지 않는다 (D-210).

이 탐침을 만들게 한 것 (P-98 · 턴 L)
------------------------------------
`gxprobe_e2e` 는 **인증된 계정인데 역할이 하나도 없다** (`user.roles` M2M 이 빈
쿼리셋이다. 이 제품에는 `role` 이라는 **단수 필드가 없다** — `getattr(u,"role",None)`
이 조용히 None 을 돌려주었고, 그 None 이 인덱스의 `user_role` 칸에 `NO_ROLE` 로
적혔다. 채워져 있었지만 아무것도 재고 있지 않았다).

그 계정으로 찍은 33장을 **전부 눈으로 열어** 세었더니 [실측 2026-09-07 · 차선 C]:

    제대로 거부를 낸 화면            **2장**
    거부 안내 없이 **실제 자료**를 그린 화면  **15장**
      — 이벤트 목록 · 이벤트 상세 · 판정 칸 · 프리셋 넷 · 휴대전화 수신함 ·
        NOTAM 기록 · 본인 프로필. 카메라 이름과 발생 시각이 든 표가 그대로 그려졌다
    안내도 자료도 없이 빈 표만 낸 화면  **7장**

즉 **갓 만들어진 역할 0개 계정이 운영 자료를 읽는다.**

제품 판정 (CPO · 2026-09-07) — 다시 논하지 않는다
-------------------------------------------------
    역할이 없는 계정이 볼 수 있는 화면은 **정확히 하나**다:
        「역할이 아직 없습니다 · 관리자에게 역할 부여를 요청했습니다」
    **그 밖의 모든 화면과 모든 API 는 403 이다.**

이 탐침은 그 판정을 **재는 자**이지 거는 자가 아니다. 거는 것은 차선 B/DB 의 일이고
(`backend/**` 는 이 차선이 한 줄도 고치지 않는다), 이 탐침은 **지금 실제로 무엇이
나가는가**를 호출로 잰다.

★ 분모는 **살아 있는 라우터 전수**다 (P-99 를 읽기 면에 그대로 적용)
--------------------------------------------------------------------
쓰기 탐침이 턴 K 에 배운 것을 처음부터 지킨다: 손으로 고른 목록은 분모가 아니다.
django-ninja 레지스트리를 전수로 돌고(`_iter_ninja_apis` → `_routers` →
`path_operations` → `operations`), 거르는 것은 **읽기 메서드가 아닌 것 하나뿐**이다.
[실측 2026-09-07 · 라우터 705행 = 읽기 328행 + 쓰기 377행 · 서로 다른 경로 578]

★ 왜 대체물(stub)을 안 쓰나 — 쓰기 탐침과 **다른 점**
------------------------------------------------------
쓰기 탐침은 부작용을 피하려고 `view_func` 를 대체물로 바꿔 「도달」만 쟀다. 읽기는
그러면 안 된다. **여기서 답해야 하는 질문이 「도달했는가」가 아니라 「무엇이
나왔는가」**이기 때문이다. 도달만 재면 15장이 그린 그 표를 못 본다.
그래서 이 탐침은 **진짜로 부른다** — 진짜 서버(`http://localhost:8000`)에,
진짜 토큰으로, 진짜 응답 본문을 받아서 센다. 읽기는 되돌릴 것이 없다.

★★ 네 칸 — 게이트가 읽는 것은 이 넷이다
----------------------------------------
    빨강  red                200 **인데 본문에 자료가 들어 있다** (아래 술어)
    초록  green              403/401, 또는 **비었거나 거부인 봉투**
    공개  public_by_design   허용목록 + **한 줄 사유**. 목록에 없는데 익명이
                             읽히면 그것도 **빨강**이다
    회색  grey               **못 쟀다.** 초록이 아니다

★★ 빨강 술어 — **정확히 이것이다** (숨기지 않고 적는다)
--------------------------------------------------------
`has_data()` 가 참인 응답만 빨강이다:

  ① HTTP 상태가 2xx 다. (401/403/404/422/5xx 는 빨강이 될 수 없다)
  ② 본문이 JSON 이고, **거부 봉투가 아니다.**
     거부 봉투 = `success` 가 거짓이면서 상태칸(`status`·`status_code`)이 401/403
     이거나 메시지에 거부 문구("permission denied" · "권한이" · "unauthorized" 등)가
     든 것. ★ 이 제품은 **거부를 HTTP 200 봉투에 담는 자리가 있다**(D-349 착시 ⑧) —
     그것을 자료로 세면 없는 빨강이 무더기로 생긴다. 그래서 따로 가른다
  ③ 봉투(성공 표시·상태·메시지·쪽 나누기 칸)를 **걷어내고 남은 것**이 비어 있지 않다.
     남은 것이 리스트면 원소 ≥ 1, 딕트면 열쇠 ≥ 1, 홑값이면 None/""/0/False 가 아니다.
     `{"items": [], "total": 0}` 은 **자료가 아니다.**

  ★ 그리고 ③이 「비었다」로 나온 자리는 **그대로 초록으로 세지 않는다.** 이 환경의
    표가 비어 있어서 빈 것인지, 관문이 비운 것인지 가를 수 없기 때문이다
    (D-301 「검사 못함 ≠ 0건」). 그래서 **같은 순간 같은 주소를 역할 있는 계정
    (`gxseed_u5_sysop` · admin)으로 한 번 더 부른다**:
        대조군에 자료가 있다 → 관문이 비운 것이다 → **초록**
        대조군도 비었다     → 이 환경에 행이 없다 → **회색** (초록이 아니다)

★ 응답 캐시 (D-341 착시 ⑦ · 이 저장소의 상처)
----------------------------------------------
`UniversalCacheMiddleware` 는 적중 시 뷰를 부르지 않고 저장된 본문을 **200 으로**
돌려준다. 열쇠에 사용자 권한 서명이 들어가지만
(`_get_user_permission_signature`), **역할도 그룹도 언어도 없는 계정의 서명은 빈
문자열**이다 — 같은 처지의 다른 계정과 열쇠가 겹친다. 그래서 이 탐침은 자료가
나온 자리를 **`X-No-Cache: true` 로 한 번 더** 부르고 두 답을 나란히 적는다:
    둘 다 자료 → 핸들러가 낸 것이다 (권한 결함)
    캐시만 자료 → 캐시가 낸 것이다 (그것도 유출이다. 사람은 자료를 받았다)
둘 중 무엇이든 **빨강이다.** 어느 쪽인지를 `data_from` 칸에 적는다.

★ 경로 틀(`{id}`) — 없는 id 로 404 를 받고 「막혔다」로 세지 않는다
------------------------------------------------------------------
404 는 관문의 답이 아니라 **「그런 행이 없다」**의 답이다. 그래서 404 가 나오면
대조군(admin)으로 **부모 목록**을 불러 실재 id 를 얻고 다시 때린다. 얻지 못하면
그 자리는 **회색**이고, 그 사유(`id_source`)를 적는다. 읽기이므로 실재 id 로
때려도 되돌릴 것이 없다 — 쓰기 면에서는 하지 않는 일이다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
        -e GX_READ_SUBJECT_PW=… -e GX_READ_CONTROL_PW=… gx-shell \
        python /repo/scripts/probe_read_surface.py /docs/agent/evidence/P-105/read_surface.json

호스트에서는 ``--self-test`` 만 돈다.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlencode

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

READ_METHODS = ("GET", "HEAD")

#: 질의값을 몇 바퀴까지 맞춰 보는가. 다 쓰고도 422 면 **못 맞춘 것**이고 회색이다.
MAX_ROUNDS = 8

DENY_STATUSES = (401, 403)            # 관문 — 이것만 관문이다
VALIDATION_STATUSES = (400, 422)      # 도달·검증 실패 — 관문이 아니다
UNREACHABLE_STATUSES = (404, 405)     # 도달 실패 / 그런 행이 없다

#: 네 칸. 게이트가 읽는 것은 이 넷이다.
BUCKET_RED = "red"
BUCKET_GREEN = "green"
BUCKET_PUBLIC = "public_by_design"
BUCKET_GREY = "grey"
BUCKETS = (BUCKET_RED, BUCKET_GREEN, BUCKET_PUBLIC, BUCKET_GREY)

#: ★ **익명이 읽어도 되는 자리.** 선언이지 면제가 아니다 (D-264 계열).
#:   판단 기준 하나: **아직 로그인하지 못한 사람이 부르는 자리인가.**
#:   여기 없는데 익명이 자료를 읽으면 **빨강**이다.
PUBLIC_READ_BY_DESIGN: dict[str, str] = {
    "/api/v1/health": "생존 확인 — 로드밸런서·감시기가 자격증명 없이 부른다. 테넌트 자료가 아니다",
    "/api/dsm/health": "생존 확인 — 인증 없이 부른다 · 검사 이름과 상태 이름(ok/fail)뿐 · 테넌트 "
                       "자료·호스트명 없음 (턴 T U56 · tests/test_f05_event_api.py::PUBLIC_ENTRY_BY_DESIGN 과 한 쌍)",
    "/api/v1/auth/csrf-token": "CSRF 토큰 — **로그인하기 전에** 받아야 한다. 토큰이 있어야 "
                               "받을 수 있으면 로그인할 수 없다",
    # ★ [D-461 · 2026-09-15 턴 P] 로그인 화면(§0.4 rj-core)이 **로그인 전에** 부른다.
    #   익명에게는 원 응답(16,436 B · 보안 정책 포함)이 아니라 `common/access_gate.py::
    #   ANON_PUBLIC_PROJECTIONS` 가 **새로 만든** 두 칸(부제목 · 가입 허용)만 나간다 · 상한 1KB.
    "/api/config-management/list-optimized": "로그인 화면이 로그인 전에 읽는 부제목·가입 허용 두 칸 — "
                                             "우리 층이 그 둘만 새로 만들어 낸다(원 응답은 안 나감 · 1KB 상한)",
}

#: ★★ **역할 0개 계정이 읽어도 되는 자리 — 지금은 비어 있다.**
#:
#:   CPO 판정은 화면 **하나**를 말하고, 그 화면은 「역할이 아직 없습니다」를 알리는 것
#:   말고 아무것도 하지 않는다. 그래서 이 목록의 기본값은 **빈 목록**이다.
#:   ★ 이름을 더하는 것은 「역할 없는 사람에게 이것도 보인다」는 **사람의 선언**이고,
#:     탐침이 스스로 더하지 않는다. 모르는 쪽은 **닫힌 쪽**으로 기운다 (D-284).
#:
#:   ⚠ 사람이 판정해야 할 자리 둘 [실측 2026-09-07 · 턴 M] — 지금은 **빨강**으로 둔다:
#:       GET /api/v1/user/me         3,751 B  자기 자신 (테넌트 자료는 아니다)
#:       GET /api/v1/auth/profile      247 B  자기 자신
#:     그 한 화면이 사람의 이름을 그려야 한다면 둘 중 **하나만** 여기 오르면 된다.
#:     둘 다 열 이유는 없다.
#:
#:   ★ 2026-09-07 턴 M 병합 [영실 선언] — **하나 올린다.** CPO 판정이 말한 「그 화면
#:     하나」가 실제 문을 갖게 됐다(`backend/apps/access`). 문이 없으면 화면이 자기를
#:     못 채우고, 그러면 판정이 말한 화면이 서지 못한다. **판정이 연 문이지 우리가 연
#:     문이 아니다** — 그래서 사유를 여기 적고, 아래 자기시험이 이 목록을 **이 하나로
#:     못박는다**(「비어 있다」보다 강한 못이다: 다음 사람이 조용히 늘리면 잡힌다).
#:     `/api/v1/user/me` · `/api/v1/auth/profile` 은 **여전히 빨강** — 그 화면은 이 문
#:     하나로 자기를 채운다(`user`·`administrator` 덩이가 그 안에 있다).
ROLE0_ALLOWED: dict[str, str] = {
    "/api/v1/access/role-pending":
        "역할 대기 화면이 자기를 채우는 **유일한** 문 (CPO 판정 P-105 · 턴 M). "
        "자기 자신과 관리자 이름만 낸다 — 남의 테넌트 자료가 아니다. "
        "이 문이 없으면 「역할이 아직 없습니다」 화면이 서지 못한다",
}

#: MinIO 자격증명이 자리표시자라서 나는 503. **권한 결과가 아니다** — 이름을 적어 둔다.
MINIO_503_PREFIXES = ("/api/media-data", "/api/dsm/events/")

#: 거부를 뜻하는 문구 (D-349 — 봉투는 200 인데 내용이 403 인 자리가 있다).
DENIAL_WORDS = ("permission denied", "you don't have permission", "unauthorized",
                "forbidden", "권한이 없", "권한이 거부", "접근 권한", "no permission")

#: 봉투 칸 — 자료가 아니다. 걷어내고 남은 것이 자료다.
ENVELOPE_KEYS = frozenset({
    "success", "status", "status_code", "statuscode", "message", "messages", "detail",
    "details", "error", "errors", "code", "meta", "pagination", "timestamp", "time",
    "total", "total_item", "total_items", "total_page", "total_pages", "total_count",
    "total_records", "count", "page", "pages", "page_size", "per_page", "current_page",
    "next", "previous", "has_next", "has_prev", "has_previous", "links", "request_id",
})

#: 봉투 안에서 **자료가 담기는** 이름. 있으면 그 값만 본다.
PAYLOAD_KEYS = ("data", "items", "results", "records", "list", "rows", "content",
                "payload", "objects")


# ─────────────────────────────────────────────────────────────────────────────
# 술어 — 요청 객체 없이 시험할 수 있게 **순수 함수**로 둔다 (D-212: 판정은 한 곳)
# ─────────────────────────────────────────────────────────────────────────────
def is_denial_envelope(obj) -> bool:
    """★ 「봉투는 200, 내용은 403」인가 (D-349 착시 ⑧).

    이것을 자료로 세면 없는 빨강이 무더기로 생긴다. 이 제품에는 그 자리가 실제로 있다.
    """
    if not isinstance(obj, dict):
        return False
    ok = obj.get("success")
    st = obj.get("status_code", obj.get("status"))
    if ok is False and st in DENY_STATUSES:
        return True
    blob = json.dumps({k: obj.get(k) for k in ("message", "detail", "error", "messages")},
                      ensure_ascii=False).lower()
    if any(w in blob for w in DENIAL_WORDS):
        return True
    return False


def strip_envelope(obj):
    """봉투를 걷어내고 **남은 것**을 돌려준다. 봉투 자체는 자료가 아니다."""
    if not isinstance(obj, dict):
        return obj
    for k in PAYLOAD_KEYS:
        if k in obj:
            return obj[k]
    rest = {k: v for k, v in obj.items() if k.lower() not in ENVELOPE_KEYS}
    return rest


def is_empty_payload(payload) -> bool:
    """걷어내고 남은 것이 **비었는가.** `{"items": [], "total": 0}` 은 비었다."""
    if payload is None:
        return True
    if isinstance(payload, (list, tuple, set)):
        return len(payload) == 0
    if isinstance(payload, dict):
        return len(payload) == 0
    if isinstance(payload, str):
        return payload.strip() == ""
    if isinstance(payload, bool):
        return payload is False
    if isinstance(payload, (int, float)):
        return payload == 0
    return False


def data_units(payload) -> int:
    """자료가 **몇 덩이**인가. 보고에 쓰는 수이지 판정에 쓰는 수가 아니다."""
    if isinstance(payload, (list, tuple)):
        return len(payload)
    if isinstance(payload, dict):
        return len(payload)
    return 0 if is_empty_payload(payload) else 1


def sample_keys(payload) -> list:
    """**열쇠 이름만** 뽑는다. 값은 적지 않는다 — 증거에 테넌트 자료를 옮기지 않는다."""
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            return sorted(first.keys())[:20]
        return [type(first).__name__]
    if isinstance(payload, dict):
        return sorted(payload.keys())[:20]
    return []


def has_data(status, body: bytes):
    """★★ **빨강 술어.** (참/거짓, 사유, 덩이수, 열쇠들) 을 돌려준다.

    ①2xx · ②거부 봉투가 아니다 · ③봉투를 걷어내고 남은 것이 있다 — 셋 다여야 참이다.
    """
    if status is None or not (200 <= int(status) < 300):
        return False, "2xx 가 아니다 (상태 %s)" % status, 0, []
    if not body:
        return False, "본문이 비었다", 0, []
    try:
        obj = json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        # JSON 이 아니다 — 문서·HTML·바이너리. 길이로만 말한다(추정하지 않는다).
        return False, "JSON 이 아니다 (%d B) — 자료 여부를 이 술어로는 못 가른다" % len(body), 0, []
    if is_denial_envelope(obj):
        return False, "★ 거부 봉투다 — 200 안에 든 403 (D-349 착시 ⑧)", 0, []
    payload = strip_envelope(obj)
    if is_empty_payload(payload):
        return False, "봉투를 걷어내니 **비었다**", 0, []
    return (True, "봉투를 걷어내고도 자료가 남는다", data_units(payload),
            sample_keys(payload))


def minio_503(path: str, status) -> bool:
    """알려진 환경 사실 — MinIO 자격증명이 자리표시자라 503 이다. **권한 결과가 아니다.**"""
    return status == 503 and any(path.startswith(p) for p in MINIO_503_PREFIXES)


def classify(subject: dict, control: dict, path: str, *, anon: bool = False,
             public=None, role0=None):
    """★★ 네 칸을 정한다. **판정식은 여기 한 곳에만 둔다** (D-212).

    subject/control 은 `{"status": int|None, "data": bool, "why": str}` 모양이다.
    """
    pub = PUBLIC_READ_BY_DESIGN if public is None else public
    r0 = ROLE0_ALLOWED if role0 is None else role0
    allow = dict(pub) if anon else dict(pub, **r0)
    st = subject.get("status")

    if subject.get("data"):
        if path in allow:
            return BUCKET_PUBLIC, "선언된 공개 읽기 면 — %s" % allow[path]
        return BUCKET_RED, "★ 200 인데 본문에 자료가 있다 — %s" % subject.get("why", "")

    if st in DENY_STATUSES:
        # ★★ [출생 표본 · 턴 M] **admin 도 같은 401 을 받았다면 그것은 관문이 아니다.**
        #   관문이 admin 을 막을 리가 없다 — 탐침의 토큰이 죽은 것이다(동시 세션 1개).
        #   첫 실행이 이 모양으로 **거짓 초록 151** 을 냈다. 부름꾼이 401 을 되살리게
        #   고쳤지만, 되살리기가 실패하는 날을 위해 **판정에도 한 겹 둔다** (D-350).
        if st == 401 and control.get("status") == 401 and not anon:
            return BUCKET_GREY, ("401 인데 **대조군(admin)도 401** 이다 — 관문이 admin 을 "
                                 "막을 리 없다. 탐침의 토큰이 죽은 것으로 본다. "
                                 "**초록이 아니다** (턴 M 거짓 초록 151자리)")
        return BUCKET_GREEN, "%s — 관문이 섰다 [실측]" % st
    if st is None:
        return BUCKET_GREY, "부르지 못했다 (%s)" % (subject.get("why") or "전송 실패")
    if minio_503(path, st):
        return BUCKET_GREY, ("503 — MinIO 자격증명이 자리표시자다(알려진 환경 사실). "
                             "**권한 결과가 아니다**")
    if 200 <= int(st) < 300:
        if "거부 봉투" in (subject.get("why") or ""):
            return BUCKET_GREEN, ("거부를 200 봉투에 담아 돌려줬다 — 자료는 안 나갔다. "
                                  "★ 봉투 자체는 따로 등재된 결함이다 (D-349)")
        # 비었다 — **그대로 초록으로 세지 않는다.** 대조군이 가른다
        if control.get("data"):
            return BUCKET_GREEN, ("비었다 · 같은 주소를 admin 으로 부르면 자료가 나온다 "
                                  "→ **관문이 비운 것이다** [대조 실측]")
        return BUCKET_GREY, ("비었는데 **admin 으로도 비었다** — 이 환경에 행이 없어서인지 "
                             "관문 때문인지 못 가른다 (D-301 「검사 못함 ≠ 0건」)")
    if int(st) in VALIDATION_STATUSES:
        return BUCKET_GREY, "%s — 질의값을 못 맞췄다. 그 뒤에 관문이 있는지 못 쟀다" % st
    if int(st) in UNREACHABLE_STATUSES:
        return BUCKET_GREY, "%s — 그런 행/메서드가 없다. 관문은 못 쟀다" % st
    return BUCKET_GREY, "%s — 그 밖의 상태. 관문은 못 쟀다" % st


# ─────────────────────────────────────────────────────────────────────────────
# 질의값 맞추기 — **서버가 불러 주는 대로 받아쓴다**
#   `probe_write_surface.py` 의 같은 이름 함수를 **베껴 왔다.** 판정식(D-212)이 아니라
#   보조 함수이고, 두 탐침이 서로를 import 하면 한쪽이 죽을 때 다른 쪽도 죽는다.
# ─────────────────────────────────────────────────────────────────────────────
_EMAILISH = ("email", "mail")
_URLISH = ("url", "uri", "endpoint", "callback", "link")


def by_name(k: str):
    k = k.lower()
    if any(w in k for w in _EMAILISH):
        return "gxprobe@example.invalid"
    if any(w in k for w in _URLISH):
        return "https://example.invalid/probe"
    if k.endswith("_ids") or k == "ids":
        return "1"
    return "1"


def guess_value(err: dict, key: str):
    t = str(err.get("type") or "")
    ctx = err.get("ctx") or {}
    k = str(key).lower()
    if t in ("int_type", "int_parsing", "int_from_float"):
        return 1
    if t in ("float_type", "float_parsing", "decimal_type", "decimal_parsing"):
        return 1.0
    if t in ("bool_type", "bool_parsing"):
        return "false"
    if t.startswith("datetime"):
        return "2026-01-01T00:00:00+00:00"
    if t.startswith("date"):
        return "2026-01-01"
    if t.startswith("time"):
        return "00:00:00"
    if t.startswith("uuid"):
        return "00000000-0000-4000-8000-000000000000"
    if t in ("list_type", "tuple_type", "set_type", "iterable_type"):
        return "1"
    if t == "enum":
        expected = str(ctx.get("expected") or "")
        quoted = re.findall(r"'([^']*)'", expected)
        if quoted:
            return quoted[0]
        nums = re.findall(r"-?\d+", expected)
        return int(nums[0]) if nums else "1"
    if t in ("greater_than", "greater_than_equal"):
        base = ctx.get("gt", ctx.get("ge", 0))
        try:
            return int(base) + 1
        except (TypeError, ValueError):
            return 1
    if t in ("too_short", "string_too_short"):
        n = int(ctx.get("min_length") or 1)
        return "x" * max(n, 1)
    return by_name(k)


def probe_url(canonical: str, mount: str, prefix: str, op_path: str) -> str:
    """**때리는 주소.** `_join` 이 지운 끝 빗금을 되살린다 (D-350).

    끝 빗금을 지우고 때리면 `APPEND_SLASH` 가 끼어들고, 301 을 안 따라가면 그 자리가
    「관문이 있는 것처럼」 보인다 — D-364 가 그렇게 넷을 놓쳤다.
    """
    raw = re.sub(r"/{2,}", "/", "/" + "".join(x or "" for x in (mount, prefix, op_path)))
    if raw.endswith("/") and canonical != "/":
        return canonical + "/"
    return canonical


def fill_path(url: str, values: dict) -> str:
    for name in re.findall(r"\{([^}]+)\}", url):
        url = url.replace("{%s}" % name, str(values.get(name, "1")))
    return url


# ─────────────────────────────────────────────────────────────────────────────
# 부르는 쪽 — **진짜 서버에 진짜 토큰으로** 부른다 (대체물 없음)
# ─────────────────────────────────────────────────────────────────────────────
class Caller:
    """★★ **토큰은 도중에 죽는다** — 2026-09-07 턴 M 첫 실행에서 실제로 그랬다 (D-350).

    첫 실행은 328자리 중 **151자리에서 401** 을 받았고, 그 401 을 「관문이 섰다」로 세어
    **거짓 초록 151** 을 냈다. 그런데 같은 151자리에서 **대조군(admin)도 401** 이었다 —
    관문이 admin 을 막을 리가 없다. 손으로 새 토큰을 받아 같은 주소를 다시 부르니
    `/api/dashboard/dashboard` 는 **200 · 426 B**, `/api/checklist-setting` 은 **403**
    이었다. 즉 그 401 은 제품의 답이 아니라 **탐침의 토큰이 죽은 것**이다.

    (이 제품은 계정당 동시 세션이 하나다. 옆 차선이 같은 계정으로 로그인하면 내 토큰이
     그 순간 무효가 된다. 턴 M 은 차선이 여럿이다.)

    그래서 이 부름꾼은 **401 을 받으면 한 번 다시 로그인하고 한 번 더 부른다.**
    다시 부른 답이 또 401 이면 그때는 **진짜 401** 이다. 다시 로그인한 횟수는
    `relogins` 에 남는다 — 「몇 번 죽었는지」를 증거에 적는다.
    """

    def __init__(self, base: str, timeout: float = 20.0):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.creds: dict = {}          # principal → (username, password)
        self.tokens: dict = {}         # principal → access token
        self.last_login: dict = {}     # principal → time.time()
        self.relogins: dict = {}       # principal → 다시 로그인한 횟수

    def add_principal(self, name: str, username: str, password: str):
        self.creds[name] = (username, password)
        self.tokens[name] = self.login(username, password)
        self.last_login[name] = time.time()
        self.relogins[name] = 0

    def authed(self, principal, method: str, url: str, no_cache=False):
        """★ 401 이면 **한 번 되살리고 한 번 더 부른다.** 그래도 401 이면 진짜다."""
        token = self.tokens.get(principal) if principal else None
        r = self.call(method, url, token, no_cache=no_cache)
        if r["status"] != 401 or principal not in self.creds:
            return r
        # 3초 안에 이미 되살렸으면 또 로그인하지 않는다 (로그인 폭풍을 막는다).
        if time.time() - self.last_login[principal] > 3:
            self.tokens[principal] = self.login(*self.creds[principal])
            self.last_login[principal] = time.time()
            self.relogins[principal] += 1
        r2 = self.call(method, url, self.tokens[principal], no_cache=no_cache)
        r2["retried_after_401"] = True
        return r2

    def call(self, method: str, url: str, token=None, body=None, no_cache=False):
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if no_cache:
            headers["X-No-Cache"] = "true"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + url, data=data, headers=headers,
                                     method=method)
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return {"status": resp.status, "body": resp.read(),
                        "ms": int((time.time() - t0) * 1000), "err": ""}
        except urllib.error.HTTPError as exc:
            return {"status": exc.code, "body": exc.read(),
                    "ms": int((time.time() - t0) * 1000), "err": ""}
        except Exception as exc:                                   # noqa: BLE001
            return {"status": None, "body": b"",
                    "ms": int((time.time() - t0) * 1000),
                    "err": "%s: %s" % (type(exc).__name__, exc)}

    def login(self, username: str, password: str) -> str:
        #: P-170 ① — V 단독 잠금이면 로그인하지 않는다(회색으로 끝낸다 · 초록 아님).
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from v_lock import is_locked as _v_locked, GRAY_NOTE as _V_NOTE  # noqa: PLC0415
        except ImportError:                                            # pragma: no cover
            _v_locked, _V_NOTE = (lambda: False), ""
        if _v_locked():
            raise SystemExit("[READSURFACE] 회색 — 로그인 건너뜀 · " + _V_NOTE)
        r = self.call("POST", "/api/v1/auth/login",
                      body={"username": username, "password": password,
                            "end_previous_session": True})
        if r["status"] != 200:
            raise SystemExit("[READSURFACE] 로그인 실패 %s %s — 계정/비밀번호를 "
                             "확인한다 (값은 적지 않는다)"
                             % (username, r["status"]))
        d = json.loads(r["body"].decode("utf-8", "replace"))
        tok = (d.get("user") or {}).get("access_token") or d.get("access_token")
        if not tok:
            raise SystemExit("[READSURFACE] 로그인은 200 인데 토큰이 없다 — 응답 모양이 바뀌었다")
        return tok


def measure(caller: Caller, method: str, url: str, principal, query: dict):
    """한 자리를 **질의값을 맞춰 가며** 부른다. 422 는 서버가 불러 주는 대로 채운다."""
    rounds, log = 0, []
    q = dict(query)
    r = None
    while True:
        rounds += 1
        full = url + ("?" + urlencode(q, doseq=True) if q else "")
        r = caller.authed(principal, method, full)
        log.append({"round": rounds, "status": r["status"], "query": dict(q)})
        if rounds >= MAX_ROUNDS or r["status"] not in VALIDATION_STATUSES:
            break
        try:
            errs = json.loads(r["body"].decode("utf-8", "replace")).get("detail")
        except (ValueError, AttributeError):
            errs = None
        if not isinstance(errs, list) or not errs:
            break
        progressed = False
        for err in errs:
            loc = list(err.get("loc") or [])
            if len(loc) < 2 or loc[0] != "query":
                continue
            key = str(loc[-1])
            val = guess_value(err, key)
            if q.get(key) != val:
                q[key] = val
                progressed = True
        if not progressed:
            break
    r["query"] = q
    r["rounds"] = rounds
    r["rounds_log"] = log
    r["url"] = url + ("?" + urlencode(q, doseq=True) if q else "")
    return r


def harvest_id(caller: Caller, url: str, principal):
    """부모 목록을 **대조군(admin)으로** 불러 실재 id 를 얻는다. 못 얻으면 None.

    ★ 읽기이므로 실재 id 로 때려도 되돌릴 것이 없다. 쓰기 면에서는 하지 않는 일이다.
    """
    parent = re.sub(r"/\{[^}]+\}[^/]*$", "", url)
    if not parent or parent == url:
        return None, "부모 목록 주소를 못 만들었다"
    r = caller.authed(principal, "GET", parent)
    if r["status"] is None or not (200 <= r["status"] < 300):
        return None, "부모 목록이 %s 를 냈다" % r["status"]
    try:
        payload = strip_envelope(json.loads(r["body"].decode("utf-8", "replace")))
    except ValueError:
        return None, "부모 목록이 JSON 이 아니다"
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list) or not payload:
        return None, "부모 목록이 비었다 (이 환경에 행이 없다)"
    first = payload[0]
    if not isinstance(first, dict):
        return None, "부모 목록의 원소가 객체가 아니다"
    for k in ("id", "pk", "uuid", "code"):
        if first.get(k) not in (None, ""):
            return first[k], "대조군(admin) 부모 목록 %s 의 첫 행 %s" % (parent, k)
    return None, "부모 목록의 첫 행에 id 가 없다"


def collect(caller: Caller, verbose=False):
    """★ 분모는 **살아 있는 라우터 전수**다. 손으로 추리지 않는다 (P-99)."""
    from common.tenant_scope import _iter_ninja_apis, _join

    rows = []
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    methods = [str(m).upper() for m in (getattr(op, "methods", []) or [])]
                    read_methods = [m for m in methods if m in READ_METHODS]
                    if not read_methods:
                        continue
                    path = _join(mount, prefix, op_path)
                    url = probe_url(path, mount, prefix, op_path)
                    view = getattr(op, "view_func", None)
                    auth_names = []
                    for cb in (getattr(op, "auth_callbacks", None) or []):
                        for klass in type(cb).__mro__:
                            if klass is not object and klass.__name__ not in auth_names:
                                auth_names.append(klass.__name__)
                    has_authz = bool(getattr(view, "_path_override", None))
                    for method in read_methods:
                        rows.append(probe_one(caller, method, path, url,
                                              view, auth_names, has_authz, verbose))
    rows.sort(key=lambda r: (BUCKETS.index(r["bucket"]), r["path"], r["method"]))
    return rows


def probe_one(caller, method, path, url, view, auth_names, has_authz, verbose):
    params = re.findall(r"\{([^}]+)\}", url)
    path_values = {}
    subj_url = fill_path(url, path_values)

    # ① 역할 0개 계정 — 이 탐침의 주인공
    s = measure(caller, method, subj_url, "subject", {})
    id_source = "경로 틀 없음" if not params else "자리표시자 1"

    # ★ 404 는 관문의 답이 아니다 — 실재 id 로 다시 때린다
    if params and s["status"] in UNREACHABLE_STATUSES:
        real, why = harvest_id(caller, url, "control")
        if real is not None:
            path_values = {p: real for p in params}
            subj_url = fill_path(url, path_values)
            s = measure(caller, method, subj_url, "subject", {})
            id_source = why
        else:
            id_source = "실재 id 를 못 얻었다 — %s" % why

    s_data, s_why, s_units, s_keys = has_data(s["status"], s["body"])

    # ★ 캐시가 낸 것인가 핸들러가 낸 것인가 (D-341 착시 ⑦)
    data_from = ""
    nc_status = None
    if s_data:
        nc = caller.authed("subject", method, s["url"], no_cache=True)
        nc_status = nc["status"]
        nc_data, _, _, _ = has_data(nc["status"], nc["body"])
        data_from = ("핸들러 (캐시 우회에서도 자료가 나왔다)" if nc_data
                     else "캐시 (캐시를 우회하면 자료가 안 나온다 — 그래도 사람은 받았다)")

    # ② 대조군 — 역할 있는 계정(admin). **「비었다」를 가르는 자다**
    c = measure(caller, method, subj_url, "control", s.get("query") or {})
    c_data, c_why, c_units, _ = has_data(c["status"], c["body"])

    # ③ 익명 — 「공개로 읽히는가」
    a = measure(caller, method, subj_url, None, s.get("query") or {})
    a_data, a_why, a_units, _ = has_data(a["status"], a["body"])

    box, why = classify({"status": s["status"], "data": s_data, "why": s_why},
                        {"status": c["status"], "data": c_data}, path)
    anon_box, anon_why = classify({"status": a["status"], "data": a_data, "why": a_why},
                                  {"status": c["status"], "data": c_data}, path, anon=True)

    row = {
        "method": method, "path": path, "probe_url": url, "measured_url": s["url"],
        "app": path.strip("/").split("/")[1] if path.count("/") > 1 else "",
        "view": "%s.%s" % (getattr(view, "__module__", "?"),
                           getattr(view, "__name__", "?")),
        "authn": auth_names[0] if auth_names else "",
        "authn_chain": auth_names,
        "authz_path_permission": has_authz,
        "path_params": params,
        "id_source": id_source,
        # 역할 0개 계정 [주인공]
        "subject_status": s["status"], "subject_bytes": len(s["body"]),
        "subject_data": s_data, "subject_why": s_why,
        "subject_units": s_units, "subject_keys": s_keys,
        "subject_body_sha12": hashlib.sha256(s["body"]).hexdigest()[:12],
        "subject_err": s["err"], "rounds": s["rounds"], "query": s.get("query") or {},
        "subject_retried_after_401": bool(s.get("retried_after_401")),
        "data_from": data_from, "no_cache_status": nc_status,
        # 대조군 (admin)
        "control_status": c["status"], "control_bytes": len(c["body"]),
        "control_data": c_data, "control_units": c_units,
        # 익명
        "anon_status": a["status"], "anon_bytes": len(a["body"]),
        "anon_data": a_data, "anon_units": a_units,
        "anon_bucket": anon_box, "anon_bucket_by": anon_why,
        "declared_public": path in PUBLIC_READ_BY_DESIGN,
        "declared_role0": path in ROLE0_ALLOWED,
        "bucket": box, "bucket_by": why,
    }
    row["red"] = (box == BUCKET_RED)
    row["anon_red"] = (anon_box == BUCKET_RED)
    if verbose:
        print("  %-5s %-4s %-6s %s" % (box, method, s["status"], path))
    return row


# ─────────────────────────────────────────────────────────────────────────────
def self_test() -> int:
    D = {"success": False, "status_code": 403, "message": "Permission denied."}
    D2 = {"success": False, "message": {"ko": "권한이 없습니다.", "en": "Permission denied."}}
    EMPTY = {"items": [], "total_item": 0, "total_page": 0, "current_page": 1}
    ROWS = {"success": True, "status": 200, "total_pages": 1,
            "data": [{"id": 1, "camera_name": "CAM-1", "occurred_at": "2026-09-07"}]}
    SCALAR = {"success": True, "data": 0}

    def b(o):
        return json.dumps(o).encode()

    checks = [
        # ═══ 빨강 술어 — **이 셋이 전부다** ═══
        ("★★ 200 + 봉투를 걷어내고 남은 행 → **자료다**", has_data(200, b(ROWS))[0]),
        ("★★ 200 + 빈 봉투(`items: []`)는 **자료가 아니다**", not has_data(200, b(EMPTY))[0]),
        ("★★ 200 인데 내용이 403 인 **거부 봉투**는 자료가 아니다 (D-349 착시 ⑧)",
         not has_data(200, b(D))[0]),
        ("★★ 거부 문구가 다국어 딕트 안에 있어도 읽는다 (이 제품의 실제 모양)",
         not has_data(200, b(D2))[0]),
        ("★ 403 은 술어에 걸리기 전에 떨어진다", not has_data(403, b(ROWS))[0]),
        ("★ 404 도 떨어진다", not has_data(404, b(ROWS))[0]),
        ("★ 본문이 비면 자료가 아니다", not has_data(200, b"")[0]),
        ("★ JSON 이 아니면 **모른다고 적는다** (자료로도 아님으로도 단정하지 않는다)",
         (lambda r: (not r[0]) and "JSON 이 아니다" in r[1])(has_data(200, b"<html>x</html>"))),
        ("★ 0 은 자료가 아니다 (홑값 봉투)", not has_data(200, b(SCALAR))[0]),
        ("★ 자료 덩이 수를 센다", has_data(200, b(ROWS))[2] == 1),
        ("★★ 증거에는 **열쇠 이름만** 남는다 — 값을 옮기지 않는다",
         has_data(200, b(ROWS))[3] == ["camera_name", "id", "occurred_at"]),

        # ═══ 봉투 걷어내기 ═══
        ("data 칸이 있으면 그 값만 본다", strip_envelope(ROWS) == ROWS["data"]),
        ("items 칸도 자료 자리다", strip_envelope(EMPTY) == []),
        ("자료 칸이 없으면 봉투 열쇠를 걷어낸 나머지다",
         strip_envelope({"success": True, "total": 3, "camera": "CAM-1"})
         == {"camera": "CAM-1"}),
        ("봉투뿐이면 남는 것이 없다",
         strip_envelope({"success": True, "status": 200, "message": "ok"}) == {}),
        ("리스트 본문은 그대로 자료다", strip_envelope([{"id": 1}]) == [{"id": 1}]),
        ("★ 빈 리스트 본문은 비었다", is_empty_payload(strip_envelope([]))),

        # ═══ 네 칸 (판정식은 한 곳에만) ═══
        ("★★ 자료가 나오면 **빨강**",
         classify({"status": 200, "data": True, "why": ""}, {}, "/api/x")[0] == BUCKET_RED),
        ("★★ 401 인데 **admin 도 401** 이면 회색이다 — 턴 M 의 거짓 초록 151자리",
         classify({"status": 401, "data": False}, {"status": 401},
                  "/api/x")[0] == BUCKET_GREY),
        ("★ admin 이 200 을 받는데 나만 401 이면 그것은 **관문**이다 (음성 대조)",
         classify({"status": 401, "data": False}, {"status": 200},
                  "/api/x")[0] == BUCKET_GREEN),
        ("★ 익명이 401 을 받는 것은 언제나 관문이다 (익명에는 대조군 규칙을 안 건다)",
         classify({"status": 401, "data": False}, {"status": 401}, "/api/x",
                  anon=True)[0] == BUCKET_GREEN),
        ("★★ 403 은 초록",
         classify({"status": 403, "data": False}, {}, "/api/x")[0] == BUCKET_GREEN),
        ("★ 401 도 초록",
         classify({"status": 401, "data": False}, {}, "/api/x")[0] == BUCKET_GREEN),
        ("★★ 거부 봉투(200)는 초록 — 자료는 안 나갔다",
         classify({"status": 200, "data": False, "why": "★ 거부 봉투다 — 200 안에 든 403"},
                  {}, "/api/x")[0] == BUCKET_GREEN),
        ("★★ 비었는데 **admin 은 자료를 받는다** → 관문이 비운 것 → 초록",
         classify({"status": 200, "data": False, "why": "비었다"},
                  {"status": 200, "data": True}, "/api/x")[0] == BUCKET_GREEN),
        ("★★ 비었는데 **admin 도 비었다** → **회색** (초록으로 세지 않는다)",
         classify({"status": 200, "data": False, "why": "비었다"},
                  {"status": 200, "data": False}, "/api/x")[0] == BUCKET_GREY),
        ("★★ 404 는 회색이다 — 관문의 답이 아니다",
         classify({"status": 404, "data": False}, {}, "/api/x")[0] == BUCKET_GREY),
        ("★ 422 도 회색이다",
         classify({"status": 422, "data": False}, {}, "/api/x")[0] == BUCKET_GREY),
        ("★ 500 도 회색이다 (관문으로 세지 않는다)",
         classify({"status": 500, "data": False}, {}, "/api/x")[0] == BUCKET_GREY),
        ("★★ MinIO 503 은 이름을 붙인 회색이다 — 권한 결과가 아니다",
         (lambda r: r[0] == BUCKET_GREY and "MinIO" in r[1])(
             classify({"status": 503, "data": False}, {}, "/api/media-data"))),
        ("★ 부르지 못한 자리도 회색이다",
         classify({"status": None, "data": False, "why": "timeout"}, {}, "/api/x")[0]
         == BUCKET_GREY),
        ("★ 네 칸 말고는 나오지 않는다",
         all(classify({"status": s, "data": False}, {}, "/api/x")[0] in BUCKETS
             for s in (200, 401, 403, 404, 422, 500, 503, None))),
        ("★ 칸마다 **근거 한 줄**이 붙는다",
         all(classify({"status": s, "data": False}, {}, "/api/x")[1]
             for s in (200, 401, 403, 404, 422, 500, None))),

        # ═══ 선언 목록 ═══
        ("★★ 역할 0개 허용목록에 있으면 자료가 나와도 빨강이 아니다",
         classify({"status": 200, "data": True, "why": ""}, {}, "/api/me",
                  role0={"/api/me": "사유"})[0] == BUCKET_PUBLIC),
        ("★★ 익명 판정에는 **역할 0개 허용목록이 안 먹는다** — 익명은 로그인도 안 했다",
         classify({"status": 200, "data": True, "why": ""}, {}, "/api/me", anon=True,
                  role0={"/api/me": "사유"})[0] == BUCKET_RED),
        ("★ 공개 선언은 익명에게도 먹는다",
         classify({"status": 200, "data": True, "why": ""}, {}, "/api/v1/health",
                  anon=True)[0] == BUCKET_PUBLIC),
        # ★ 「비어 있다」에서 「이 하나뿐이다」로 못을 옮겼다 (턴 M 병합).
        #   빈 목록은 늘어나는 것을 못 잡는다 — 이름을 박아 두면 잡는다.
        ("★★ 역할 0개 허용목록은 **CPO 판정이 연 문 하나뿐이다** — 늘어나면 잡는다. "
         "이름을 더하는 것은 사람의 선언이지 탐침의 판단이 아니다 (D-284)",
         set(ROLE0_ALLOWED) == {"/api/v1/access/role-pending"}),
        ("★★ 자기 자신을 읽는 자리도 **기본값은 빨강**이다 (닫힌 쪽으로 기운다)",
         classify({"status": 200, "data": True, "why": ""}, {},
                  "/api/v1/user/me")[0] == BUCKET_RED),
        ("★★ 선언 목록의 **모든** 이름에 사유 한 줄이 붙어 있다",
         all(isinstance(v, str) and v.strip()
             for v in list(PUBLIC_READ_BY_DESIGN.values()) + list(ROLE0_ALLOWED.values()))),
        ("★★ 역할 0개 허용목록은 **작아야 한다** — CPO 판정은 화면 하나다",
         len(ROLE0_ALLOWED) <= 2),

        # ═══ 측정기의 병 ═══
        ("★★ `/api/roles/` 의 끝 빗금을 살린다 (D-350)",
         probe_url("/api/roles", "/api/", "/roles", "/") == "/api/roles/"),
        ("★ 빗금이 없던 자리는 그대로 둔다 (음성 대조)",
         probe_url("/api/health", "/api/", "", "/health") == "/api/health"),
        ("★ 경로 틀을 채운다", fill_path("/api/x/{id}", {"id": 7}) == "/api/x/7"),
        ("★ 값이 없으면 자리표시자 1 을 쓴다", fill_path("/api/x/{id}", {}) == "/api/x/1"),
        ("★ 질의값은 서버가 불러 주는 대로 채운다",
         guess_value({"type": "int_parsing"}, "id") == 1),
        ("enum 은 기대 목록의 첫 값으로 채운다",
         guess_value({"type": "enum", "ctx": {"expected": "'a' or 'b'"}}, "k") == "a"),
    ]
    for name, ok in checks:
        print("  %s  %s" % ("OK  " if ok else "FAIL", name))
    bad = [n for n, ok in checks if not ok]
    neg = sum(1 for n, _ in checks if "음성 대조" in n)
    pos = len(checks) - neg
    print("[READSURFACE] 자기시험 %d건 %s (양성 %d · 음성 %d)"
          % (len(checks), "통과" if not bad else "실패", pos, neg))
    return 0 if not bad else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", help="결과 JSON 경로")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--base", default=os.environ.get("GX_READ_BASE",
                                                     "http://localhost:8000"))
    ap.add_argument("--subject", default=os.environ.get("GX_READ_SUBJECT", "gxprobe_e2e"))
    ap.add_argument("--control", default=os.environ.get("GX_READ_CONTROL",
                                                        "gxseed_u5_sysop"))
    args = ap.parse_args()

    rc = self_test()
    if args.self_test or rc:
        return rc
    if not args.out:
        print("[READSURFACE] 출력 경로가 필요하다 (배너가 stdout 을 더럽힌다)")
        return 2

    sub_pw = os.environ.get("GX_READ_SUBJECT_PW")
    ctl_pw = os.environ.get("GX_READ_CONTROL_PW")
    if not sub_pw or not ctl_pw:
        print("[READSURFACE] GX_READ_SUBJECT_PW · GX_READ_CONTROL_PW 가 필요하다 "
              "(저장소 밖 `.env.gates` 에서 온다 — 값은 어디에도 적지 않는다)")
        return 2

    sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    caller = Caller(args.base)
    caller.add_principal("subject", args.subject, sub_pw)
    caller.add_principal("control", args.control, ctl_pw)

    # ★ 주인공이 정말 **역할 0개**인지 먼저 확인한다. 여기가 틀리면 아래 전부가 무효다.
    from django.contrib.auth import get_user_model
    subj = get_user_model().objects.filter(username=args.subject).first()
    subj_roles = list(subj.roles.values_list("id", "role_name")) if subj else None
    if subj_roles:
        print("[READSURFACE] ★ 주인공 %s 의 역할이 **비어 있지 않다**: %s — 이 탐침은 "
              "역할 0개 계정을 재는 자다. 멈춘다" % (args.subject, subj_roles))
        return 2

    t0 = time.time()
    rows = collect(caller, verbose=args.verbose)
    elapsed = int(time.time() - t0)

    boxes = {b: sum(1 for r in rows if r["bucket"] == b) for b in BUCKETS}
    anon_boxes = {b: sum(1 for r in rows if r["anon_bucket"] == b) for b in BUCKETS}
    reds = [r for r in rows if r["red"]]
    anon_reds = [r for r in rows if r["anon_red"]]

    router_rows = 0
    from common.tenant_scope import _iter_ninja_apis
    for _m, _api in _iter_ninja_apis():
        for _p, _r in getattr(_api, "_routers", []) or []:
            for _op_path, _pv in (getattr(_r, "path_operations", {}) or {}).items():
                for _op in getattr(_pv, "operations", []) or []:
                    router_rows += len(getattr(_op, "methods", []) or [])

    # ★ **선언한 이름이 라우터에 실재하는가.** 첫 실행에서 `/api/v1/auth/me` 를 선언했는데
    #   그 자리는 **없었다** — 없는 자리를 향한 선언은 아무것도 면제하지 않으면서
    #   「우리는 이것을 열어 뒀다」고 읽힌다. 증거에 적어 게이트가 잡게 한다.
    live_paths = {r["path"] for r in rows}
    declared_ghosts = sorted(set(PUBLIC_READ_BY_DESIGN) | set(ROLE0_ALLOWED) - live_paths)
    declared_ghosts = [x for x in declared_ghosts if x not in live_paths]

    payload = {
        "decision": "P-105",
        "declared_not_in_router": declared_ghosts,
        "relogins": dict(caller.relogins),
        "server": {"base": args.base,
                   "note": "runserver --noreload — 이 측정 뒤에 바뀐 코드는 반영되지 않는다"},
        "probe_mode": "live-router-authenticated-role0-real-call",
        "subject": {"username": args.subject, "user_id": getattr(subj, "id", None),
                    "roles": subj_roles or [],
                    "note": "이 제품에는 단수 `role` 필드가 없다 — 역할은 `user.roles` M2M 이다"},
        "control": {"username": args.control, "note": "역할 있는 계정 — 「비었다」를 가르는 대조군"},
        "denominator": {
            "source": "live-router",
            "how": ("django-ninja 레지스트리 전수(`_iter_ninja_apis` → `_routers` → "
                    "`path_operations` → `operations`). 거른 것은 **읽기 메서드가 "
                    "아닌 것 하나뿐**이다 — `auth_callbacks` 유무로는 거르지 않는다"),
            "router_method_rows": router_rows,
            "read_method_rows": len(rows),
            "read_methods": list(READ_METHODS),
            "by_method": {m: sum(1 for r in rows if r["method"] == m)
                          for m in READ_METHODS},
        },
        "red_predicate": ("2xx · 거부 봉투가 아님 · 봉투(성공표시·상태·메시지·쪽나누기)를 "
                          "걷어내고 남은 것이 비어 있지 않음 — 셋 다여야 빨강이다. "
                          "빈 봉투는 자료가 아니고, 「비었다」는 **admin 대조**로 "
                          "관문이 비운 것인지 이 환경에 행이 없는 것인지 가른다"),
        "buckets": boxes,
        "anon_buckets": anon_boxes,
        "public_read_by_design": dict(sorted(PUBLIC_READ_BY_DESIGN.items())),
        "role0_allowed": dict(sorted(ROLE0_ALLOWED.items())),
        "red": [{"method": r["method"], "path": r["path"], "view": r["view"],
                 "status": r["subject_status"], "bytes": r["subject_bytes"],
                 "units": r["subject_units"], "keys": r["subject_keys"],
                 "data_from": r["data_from"], "id_source": r["id_source"]}
                for r in reds],
        "anon_red": [{"method": r["method"], "path": r["path"],
                      "status": r["anon_status"], "bytes": r["anon_bytes"],
                      "units": r["anon_units"]} for r in anon_reds],
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "elapsed_s": elapsed,
        "totals": {"routes": len(rows), "by_bucket": boxes, "red": len(reds),
                   "anon_red": len(anon_reds)},
        "routes": rows,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    if declared_ghosts:
        print("[READSURFACE] ★ 선언했는데 라우터에 **없는** 이름: %s" % ", ".join(declared_ghosts))
    print("[READSURFACE] 되살린 토큰: %s (0 이 아니면 도중에 세션을 빼앗겼다는 뜻이다)"
          % dict(caller.relogins))
    print("[READSURFACE] 읽기 면 **전수 %d자리** (라우터 %d행 중 · 분모=살아 있는 라우터) "
          "→ %s" % (len(rows), router_rows, args.out))
    print("    ★ 역할 0개 계정: 빨강 %d · 초록 %d · 공개 %d · 회색 %d"
          % (boxes[BUCKET_RED], boxes[BUCKET_GREEN], boxes[BUCKET_PUBLIC],
             boxes[BUCKET_GREY]))
    print("      익명        : 빨강 %d · 초록 %d · 공개 %d · 회색 %d"
          % (anon_boxes[BUCKET_RED], anon_boxes[BUCKET_GREEN],
             anon_boxes[BUCKET_PUBLIC], anon_boxes[BUCKET_GREY]))
    for r in sorted(reds, key=lambda x: -x["subject_bytes"])[:40]:
        print("    ★빨강 %s %s — %d B · %d덩이 · %s"
              % (r["method"], r["path"], r["subject_bytes"], r["subject_units"],
                 ", ".join(r["subject_keys"][:6])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
