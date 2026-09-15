# -*- coding: utf-8 -*-
"""역할 관문 — **역할이 하나도 없는 계정은 아무것도 보지 않는다** (P-105 · 2026-09-07 차선 B).

무엇이 이 파일을 만들게 했나 — **출생 표본**
--------------------------------------------
[실측 2026-09-07 · `gxprobe_e2e`(`user.roles` == []) 로 8000 을 두드림 · 53자리]

    GET /api/dsm/events?limit=200                    -> 200 ·  8,963B  카메라명·시각·판정
    GET /api/dsm/events/queue?limit=200              -> 200 ·  3,945B
    GET /api/dsm/deliveries?limit=50                 -> 200 ·  8,035B
    GET /api/v1/user/get-user-detail/115             -> 200 ·  5,487B  **남의 계정 전문**
    GET /api/user-groups/?page_size=10000            -> 200 ·    823B
    GET /api/config-management/list-optimized        -> 200 · 16,436B
    …  53자리 중 **21자리가 200 + 실자료**

같은 순간 같은 53자리를 역할 보유 계정으로도 쟀다. `fire_user` 22 · `fire_admin` 22 ·
`view_only_-_anyang` 22 · `admin` 28. 즉 **역할 0 계정은 운영자와 거의 같은 것을 봤다.**
「인증됐다」가 곧 「봐도 된다」였고, 그 사이에 아무것도 서 있지 않았다.

무엇이 이것을 숨겼나 — **이 제품에는 단수 `role` 필드가 없다**
--------------------------------------------------------------
역할은 M2M `user.roles` 다. `getattr(u, "role", None)` 은 **언제나 None** 을 낸다.
그 None 을 「역할을 못 쟀다」가 아니라 **측정값**으로 읽은 코드가 세 턴 동안 서 있었다.
그래서 이 파일의 판정은 `roles` 만 본다.

왜 접두를 하나씩 올리지 않고 **전역 규칙**인가
----------------------------------------------
CPO 가 정책을 정했다: 「역할 0 은 화면 하나 · 나머지 전부 403」. 정책이 전역이면
구현도 전역이어야 한다. 접두를 하나씩 올리는 방식은 **올리지 않은 접두가 곧 구멍**이고,
이 저장소는 그 모양으로 세 번 샜다(D-343 ③ · D-348 · P-83). 반경은 쟀다 —
`enumerate_operations()` 로 **705 오퍼레이션 / 578 경로**, `get_resolver()` 재귀로
**876 URL 패턴**. 그 전부가 이 한 겹을 지난다.

★ 자리 — `AccessGateMiddleware` **바로 아래**(= 응답 캐시보다 바깥)
-------------------------------------------------------------------
  ① 캐시(`UniversalCacheMiddleware`)보다 **바깥**이어야 한다. 안쪽에 두면 역할이
     있던 동안 채워진 항목이 이 관문을 지나지 않고 그대로 나간다 — D-341 착시 ⑦,
     이 저장소가 2026-09-07 에 실제로 겪은 일이다.
  ② `AccessGateMiddleware` **다음**이어야 한다. 익명은 401(누구인지 모른다),
     역할 0 은 403(누구인지는 아는데 안 된다). 순서가 두 문장을 가른다(D-290).
  ③ `JWTUserRestoreMiddleware`(dj-core · 미들웨어 목록 위쪽)보다 **아래**여야
     `request.user` 가 이미 세워져 있다. 이 관문은 **두 번째 인증기가 되지 않는다** —
     토큰을 스스로 풀지 않고, 앞 겹이 세워 준 사용자만 본다(`access_gate` 와 같은 규율).

★ 거절은 **HTTP 403 으로** 나간다 — 200 봉투에 담지 않는다 (D-349 착시 ⑧)
-------------------------------------------------------------------------
그리고 본문에 **테넌트 자료가 한 자도 없다.** `message` 는 다국어 객체로 보낸다 —
앞단의 기존 전역 거절 처리기(`permissionDenied.ts::messageOfDenial`)가 `message.ko` 를
그대로 읽으므로 **앞단을 한 줄도 안 고쳐도** 띠가 뜬다.

되돌리기 (D-212)
----------------
    settings.ROLE_GATE_ENABLED = False   # 또는 환경변수 ROLE_GATE_ENABLED=false

False 면 이 미들웨어는 경로에 있어도 **한 요청도 안 막는다.** 역할 대기 문은 남는다 —
막는 것만 되돌린다.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

#: 되돌리기 한 줄의 이름. 시험도 운영도 이 이름만 본다 (D-212).
FLAG = "ROLE_GATE_ENABLED"

#: 이 관문이 보는 면. API 밖(로그인 화면·정적·관리자)은 종전대로 둔다.
API_PREFIX = "/api/"

#: ★ **유일하게 열린 문.** 역할 대기 화면이 부르는 그 하나.
ROLE_PENDING_PATH = "/api/v1/access/role-pending"

#: ★★ **역할 0 에게도 열려 있는 자리 — 손으로 적은 목록.**
#:
#: 로그인 절차 자체를 막으면 관문이 문을 잠그고 열쇠를 삼킨다. 그래서 「들어오는 길」과
#: 「나가는 길」과 「자기 자신에 대한 최소 조작」만 비켜 준다.
#:
#: ⚠ 여기 **없는 것**을 적어 둔다 — 지금 실제로 자료가 나가던 자리들이다:
#:     /api/v1/auth/profile · /api/v1/auth/data-for-profile · /api/v1/auth/account
#:     /api/v1/auth/groups  · /api/v1/auth/departments      · /api/v1/auth/teams
#:   `access_gate.AUTHN_SURFACE` 같은 **넓은 규칙**은 이것들을 통째로 덮는다. 그 아래
#:   좁은 사고가 숨는 것을 P-83 에서 한 번 겪었다(익명이 남의 비밀번호를 바꾸던 자리).
#:   그래서 여기서는 규칙이 아니라 **이름**을 적는다. 이름을 적는 손이 곧 개방 선언이다.
ROLE_ZERO_ALLOWED: frozenset = frozenset({
    # 들어오는 길
    "/api/v1/auth/login",
    "/api/v1/auth/csrf-token",
    "/api/v1/auth/refresh-token",
    "/api/token/refresh",
    "/api/token/verify",
    # 2단계 인증 — 이것을 막으면 OTP 계정은 로그인을 **끝낼 수 없다**
    "/api/v1/auth/otp/verify",
    "/api/v1/auth/otp/generate-qr",
    "/api/v1/auth/otp/reset",
    # 나가는 길 · 세션 정리 (동시 접속 1개 제약 때문에 반드시 필요하다)
    "/api/v1/auth/logout",
    "/api/v1/auth/end-session",
    "/api/v1/auth/delete-session",
    # 자기 비밀번호. **옛 비밀번호를 아는 사람만** 바꾼다 —
    # 남의 것을 바꾸는 `/api/v1/auth/reset-password-for-user` 는 여기 없다.
    "/api/v1/auth/change-password",
    # ★ 그 하나의 문
    ROLE_PENDING_PATH,
})

#: 밖으로 나가는 본문. **고정이다** — 요청에서 가져온 글자를 한 자도 안 싣는다.
DENIAL_CODE = "role_required"
MESSAGE_KO = "역할이 아직 없습니다 — 관리자에게 역할 부여를 요청했습니다."
MESSAGE_EN = "This account has no role yet. An administrator has been notified."


# ═══════════════════════════════════════════════════════════════════════════
# ★★ P-119 / SEC-20 [2026-09-10 턴 O · 차선 S] — **읽기 전용 역할이 썼다**
# ═══════════════════════════════════════════════════════════════════════════
#
# 무엇이 있었나 [실측 2026-09-10 · 사용자 관점 점검]
#   계정 `gxseed_u4_official` · 역할 코드가 **글자 그대로** `view_only_-_anyang`.
#   그 계정으로 사건 화면의 「조치 시작」을 눌렀다:
#
#       POST /api/dsm/events/4803/response?to_state=in_progress
#         -> **200 · 사건 상태가 실제로 바뀌었다 · 감사 #197207** · 확인 대화상자 없음
#
#   [실측 2026-09-10 · TARGET=8500 · 같은 계정 · 실재하지 않는 id 로 다시]
#       POST /api/dsm/events/999999999/response?to_state=in_progress
#         -> **404** {"detail":"그런 이벤트가 없습니다."}
#            <- 관문이 아니다. **핸들러가 돌아서 조회까지 갔다**(P-83 눈금).
#       ⚠ 실재 사건 id 로는 다시 두드리지 않았다 — 그 한 번이 곧 두 번째 오염이다.
#
#   ★★ 남은 오염 한 줄 — **되돌리지 않았다.** 사건 **4803** 의 상태는 읽기 전용 계정
#      `gxseed_u4_official` 이 바꾼 그대로 남아 있고, 그 사실을 남긴 감사 행 **#197207**
#      도 그대로 있다. 지우지도 되돌리지도 않은 이유는 하나다 — **되돌림은 경영진의
#      결정**이고, 감사 행은 그 일이 있었다는 유일한 증거다. 지우면 사고가 사라진다.
#      [실측 2026-09-10 후] #197207 여전히 존재 (logger_name=guardianx.dsm.response ·
#      username=gxseed_u4_official · api_name=dsm.events.response · status_http=200).
#
#   전수 [실측 2026-09-10 · `scripts/probe_role_write_surface.py` · 살아 있는 라우터
#   전수 377자리(경로x메서드)] — `gxseed_u4_official` 로 **막힌 자리 0 / 377**.
#   같은 순간 `fire_user` 0/377 · `fire_admin` 0/377 · `admin` 0/377.
#   즉 **읽기 전용 계정과 관리자의 쓰기 반경이 완전히 같았다.**
#
# 왜 접두를 하나씩 올리지 않고 **전역 규칙**인가 — 위 P-105 와 같은 이유다.
#   반경은 쟀다: 살아 있는 라우터의 쓰기 메서드 **377자리 전수**가 이 한 겹을 지난다.
#   접두를 하나씩 올리는 방식은 **올리지 않은 접두가 곧 구멍**이고, 이 저장소는
#   그 모양으로 이미 세 번 샜다(D-343 ③ · D-348 · P-83).
#
# 왜 `role_gate` 인가 (`access_gate` 가 아니라)
#   `access_gate` 가 답하는 질문은 **하나뿐**이다 — 「아무것도 안 들고 왔는가」.
#   그 파일 머리말이 스스로 그렇게 못박아 두었다("이 관문이 답하는 질문은 하나다").
#   거기에 역할 판정을 넣으면 그 규율이 깨지고, 인증기와 권한기가 한 파일에서 섞인다.
#   여기는 **역할 관문**이고, 이 겹은 이미 `user.roles` 를 본다 — 질의 한 벌로 끝난다.
#   자리(미들웨어 순서)는 완전히 같다: 캐시보다 바깥 · `access_gate` 바로 아래.
#   되돌리기 스위치는 **따로** 둔다 — 역할 0 관문을 끄는 일과 이 규칙을 끄는 일은
#   다른 결정이고, 한 스위치에 둘을 묶으면 하나를 끄려다 둘이 꺼진다.
#
# ⚠ 앞단 버튼 숨김은 **이 다음 일**이고 차선 F 의 몫이다. 화면이 먼저 서면
#   「서버는 열려 있는데 버튼만 없는」 상태가 되고, 그건 관문이 아니다.

#: 되돌리기 한 줄의 이름. **`FLAG` 와 따로다** (위 사유).
READONLY_FLAG = "READONLY_ROLE_GATE_ENABLED"

#: 이 규칙이 보는 메서드. 읽기(GET/HEAD/OPTIONS)는 한 자도 안 만진다.
WRITE_METHODS: frozenset = frozenset({"POST", "PUT", "PATCH", "DELETE"})

#: ★ **읽기 전용 역할의 표식.** 역할 `code` 가 이 접두로 시작하면 읽기 전용이다.
#: [실측 2026-09-10 · Role 전수 15건] 이 접두에 걸리는 역할은 하나뿐이다:
#:     id=9 `view_only_-_anyang` ("View Only - Anyang") · 보유 계정 **3**
#:     (`anyang_sv`(55) · `gongju_sv01`(100) · `gxseed_u4_official`(109))
#: 셋 다 역할이 **그 하나뿐**이고 셋 다 `is_staff`·`is_superuser` 가 아니다.
#: 그러므로 이 규칙의 반경은 **계정 3개**이고, 나머지 12역할·110계정은 안 건드린다.
READONLY_ROLE_PREFIX = "view_only"

#: ★ 읽기 전용 계정도 **반드시 부를 수 있어야 하는 쓰기 자리.**
#:   `ROLE_ZERO_ALLOWED` 를 그대로 쓴다 — 「들어오는 길 · 나가는 길 · 자기 자신에 대한
#:   최소 조작」이라는 판단 기준이 여기서도 **글자 그대로** 같기 때문이다.
#:   목록을 새로 베끼면 언젠가 한쪽만 고쳐지고, 그날 로그아웃이 403 이 된다(D-212).
#: ⚠ 이 목록에 없는 것을 확인해 둔다: 로그아웃(POST)·세션정리(POST)·토큰갱신(POST)·
#:   자기 비밀번호 변경(POST)은 **있다.** 남의 것을 바꾸는 자리는 **없다.**
READONLY_WRITE_ALLOWED: frozenset = ROLE_ZERO_ALLOWED

#: 밖으로 나가는 본문. **고정이다** — 요청에서 가져온 글자를 한 자도 안 싣는다.
READONLY_DENIAL_CODE = "read_only_role"
READONLY_MESSAGE_KO = "읽기 전용 계정입니다 — 이 작업은 수행할 수 없습니다."
READONLY_MESSAGE_EN = "This account is read-only and cannot perform this action."


def enabled() -> bool:
    """이 겹이 켜져 있는가. 기본은 **켜짐**(닫힌 쪽이 기본이다)."""
    return bool(getattr(settings, FLAG, True))


def has_no_role(user) -> bool:
    """**역할 0 인가.** 이 질문의 답은 여기서만 낸다 (D-212).

    넷을 모두 만족해야 참이다:
      ① 인증됐다      ② `roles` 가 비었다
      ③ `is_superuser` 가 아니다   ④ `is_staff` 가 아니다

    ③④ 는 **잠금 방지**다. DB 플래그 관리자와 관리자 화면 운영자는 역할 표에 줄이
    없을 수 있고, 그들을 잠그면 역할을 부여할 사람이 사라진다 — 관문이 스스로를 가둔다.

    ⚠ `getattr(user, "role", None)` 을 쓰지 않는다. 이 제품에 그 필드는 **없고**,
      없는 것을 읽으면 언제나 None 이 나온다. None 을 측정으로 읽은 것이 P-105 다.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return False
    roles = getattr(user, "roles", None)
    if roles is None:
        # 역할 관계 자체가 없는 사용자 객체다. **모르는 것을 0 으로 세지 않는다**
        # (D-301 「검사 못함 != 0건」) — 막지 않고 넘긴다.
        return False
    try:
        return not roles.exists()
    except Exception:  # pragma: no cover - 이상한 사용자 객체 방어
        logger.warning("[ROLE_GATE] roles 를 읽지 못했다 — 막지 않고 넘긴다")
        return False


def _normalize(path: str) -> str:
    return (str(path or "").rstrip("/")) or "/"


#: 목록을 **한 번만** 정규화해 둔다. 요청마다 다시 만들면 그 비용이 705 라우트에 곱해진다.
_ALLOWED_NORMALIZED: frozenset = frozenset(_normalize(p) for p in ROLE_ZERO_ALLOWED)


def is_allowed_path(path: str) -> bool:
    """역할 0 이 닿아도 되는 자리인가. **순수 함수다** — 시험이 이것만으로 전부 잰다."""
    return _normalize(path) in _ALLOWED_NORMALIZED


def judge(*, path: str, no_role: bool):
    """거절 사유를 돌려준다. 통과면 None. **요청 객체 없이 시험할 수 있다.**

    순서가 규칙이다:
      ① 끄면 아무것도 안 막는다 (되돌리기가 진짜로 되돌아간다)
      ② API 면 밖은 안 본다 — 넓히면 로그인 화면·정적 파일까지 막힌다
      ③ 손으로 적은 자리는 통과 — 이름이 규칙보다 세다
      ④ 역할 0 이면 거절
    """
    if not enabled():
        return None
    if not str(path or "").startswith(API_PREFIX):
        return None
    if is_allowed_path(path):
        return None
    if not no_role:
        return None
    return DENIAL_CODE


#: 목록을 **한 번만** 정규화해 둔다 (위 `_ALLOWED_NORMALIZED` 와 같은 이유).
_READONLY_ALLOWED_NORMALIZED: frozenset = frozenset(
    _normalize(p) for p in READONLY_WRITE_ALLOWED)


def readonly_enabled() -> bool:
    """P-119 규칙이 켜져 있는가. 기본은 **켜짐**(닫힌 쪽이 기본이다)."""
    return bool(getattr(settings, READONLY_FLAG, True))


def is_readonly_allowed_path(path: str) -> bool:
    """읽기 전용 계정이 **써도 되는** 자리인가. **순수 함수다.**"""
    return _normalize(path) in _READONLY_ALLOWED_NORMALIZED


def is_write_method(method: str) -> bool:
    """상태를 바꾸는 메서드인가. **순수 함수다.**"""
    return str(method or "").upper() in WRITE_METHODS


def is_read_only(user) -> bool:
    """**읽기 전용 계정인가.** 이 질문의 답은 여기서만 낸다 (D-212).

    다섯을 모두 만족해야 참이다:
      ① 인증됐다                      ② `is_superuser` 가 아니다
      ③ `is_staff` 가 아니다          ④ 역할이 **하나 이상** 있다
      ⑤ 가진 역할이 **전부** `view_only*` 다

    ⑤ 가 "하나라도" 가 아니라 "전부" 인 이유 — `view_only` 와 `fire_admin` 을 함께
    가진 계정은 **관리자**이지 읽기 전용이 아니다. 하나라도로 세면 그런 계정의
    쓰기가 전부 막히고, 그것은 내가 만든 회귀다. [실측 2026-09-10] 지금 이 DB 에
    그런 계정은 **0개**이므로 두 해석의 결과는 같다 — 그래도 **좁은 쪽**을 적어 둔다.
    넓은 쪽은 나중에 조용히 남을 잠근다.

    ②③ 는 `has_no_role` 과 같은 **잠금 방지**다. DB 플래그 관리자를 잠그지 않는다.
    ④ 는 `has_no_role`(역할 0) 과 이 규칙을 **겹치지 않게** 한다 — 역할 0 은 그쪽 일이다.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return False
    roles = getattr(user, "roles", None)
    if roles is None:
        # 역할 관계 자체가 없는 사용자 객체다. **모르는 것을 읽기 전용으로 세지 않는다**
        # (D-301 「검사 못함 != 0건」) — 막지 않고 넘긴다.
        return False
    try:
        codes = [str(c or "") for c in roles.values_list("code", flat=True)]
    except Exception:                                     # pragma: no cover
        logger.warning("[ROLE_GATE] roles 를 못 읽었다 — 막지 않고 넘긴다")
        return False
    if not codes:
        return False           # 역할 0 — `has_no_role` 의 일이다
    return all(c.startswith(READONLY_ROLE_PREFIX) for c in codes)


def judge_readonly(*, method: str, path: str, read_only: bool):
    """거절 사유를 돌려준다. 통과면 None. **요청 객체 없이 시험할 수 있다.**

    순서가 규칙이다:
      ① 끄면 아무것도 안 막는다 (되돌리기가 진짜로 되돌아간다)
      ② API 면 밖은 안 본다
      ③ 읽기 메서드는 안 본다 — 이 규칙은 **쓰기**에만 건다
      ④ 손으로 적은 자리는 통과 (로그아웃·세션정리·자기 비밀번호)
      ⑤ 읽기 전용이면 거절
    """
    if not readonly_enabled():
        return None
    if not str(path or "").startswith(API_PREFIX):
        return None
    if not is_write_method(method):
        return None
    if is_readonly_allowed_path(path):
        return None
    if not read_only:
        return None
    return READONLY_DENIAL_CODE


def readonly_denial_payload() -> dict:
    """밖으로 나가는 본문 한 벌. **테넌트 자료가 한 자도 없다.**

    `role_pending_url` 은 싣지 않는다 — 이 계정은 역할을 기다리는 것이 아니라
    **역할이 그런 것**이다. 두 사유를 같은 본문으로 내보내면 앞단이 못 가린다.
    """
    return {
        "success": False,
        "status_code": 403,
        "code": READONLY_DENIAL_CODE,
        "detail": "Forbidden",
        "message": {"ko": READONLY_MESSAGE_KO, "en": READONLY_MESSAGE_EN},
    }


def readonly_denial_response() -> JsonResponse:
    """거절 하나. **403 으로 나간다** — 200 봉투에 담지 않는다 (D-349 착시 ⑧)."""
    return JsonResponse(readonly_denial_payload(), status=403)


def denial_payload() -> dict:
    """밖으로 나가는 본문 한 벌. **테넌트 자료가 한 자도 없다.**

    `message` 를 다국어 객체로 보내는 이유는 앞단이다 —
    `permissionDenied.ts::messageOfDenial` 이 `message.ko` 를 그대로 읽고,
    그래서 앞단을 한 줄도 안 고쳐도 사람이 읽는 문장이 뜬다(GX-COPY 규칙 1:
    문장은 서버가 짓는다).
    """
    return {
        "success": False,
        "status_code": 403,
        "code": DENIAL_CODE,
        "detail": "Forbidden",
        "message": {"ko": MESSAGE_KO, "en": MESSAGE_EN},
        "role_pending_url": ROLE_PENDING_PATH,
    }


def denial_response() -> JsonResponse:
    """거절 하나. **403 으로 나간다** — 200 봉투에 담지 않는다 (D-349 착시 ⑧)."""
    return JsonResponse(denial_payload(), status=403)


class RoleGateMiddleware:
    """역할로 끊는 **규칙 둘**을 한 자리에서 건다. **기본값은 거절이다.**

      ① 역할 0 계정 -> 403 (P-105) — 스위치 `ROLE_GATE_ENABLED`
      ② 읽기 전용 역할의 **쓰기** -> 403 (P-119) — 스위치 `READONLY_ROLE_GATE_ENABLED`

    두 스위치는 **따로다.** 하나를 끄려다 둘이 꺼지면 그날 구멍이 하나 열린다.

    ★ 이 겹은 **인증을 하지 않는다.** `request.user` 를 세우는 것은 앞 겹의 일이고
      (dj-core `JWTUserRestoreMiddleware`), 여기서 토큰을 또 풀면 인증기가 둘이 된다.
      인증기가 둘이면 언젠가 갈리고, 갈리면 어느 쪽이 맞는지 아무도 모른다(D-337 계열).
      앞 겹이 사용자를 못 세운 요청은 익명으로 보이고, 익명은 이 겹의 일이 아니다 —
      라우트의 인증 관문이 401 로 끊는다.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = getattr(request, "path", "") or ""
        method = getattr(request, "method", "") or ""

        # ★ 값싼 것부터 본다. `user.roles` 질의는 하나다 — API 면 밖에서는
        #   그 질의를 아예 만들지 않는다(정적 파일마다 DB 를 때리지 않는다).
        if not path.startswith(API_PREFIX):
            return self.get_response(request)

        user = getattr(request, "user", None)

        # ① 역할 0 (P-105)
        if enabled() and not is_allowed_path(path):
            verdict = judge(path=path, no_role=has_no_role(user))
            if verdict is not None:
                logger.info("[ROLE_GATE] 역할 0 거절 %s %s — %s", method, path, verdict)
                return denial_response()

        # ② 읽기 전용 역할 (P-119 / SEC-20). **쓰기 메서드에만 걸린다.**
        #   ★ 두 규칙을 한 겹에서 본다 — 미들웨어를 하나 더 얹으면 요청마다 겹이
        #     하나 늘고, 역할 질의도 두 벌이 된다. 판정식은 각자 제 함수에 있다(D-212).
        if readonly_enabled() and is_write_method(method) \
                and not is_readonly_allowed_path(path):
            verdict = judge_readonly(method=method, path=path,
                                     read_only=is_read_only(user))
            if verdict is not None:
                logger.info("[ROLE_GATE] 읽기 전용 거절 %s %s — %s",
                            method, path, verdict)
                return readonly_denial_response()

        return self.get_response(request)
