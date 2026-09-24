# -*- coding: utf-8 -*-
"""P-325 — **「보냈습니다」 길목.** 주소를 보기 전에 SMTP 도달성을 본다 (턴 S · 2026-09-24).

무엇이 문제였나 [실측 2026-09-24 · `backend/tests/test_s_password_reset_walk.py` 머릿글]
-----------------------------------------------------------------------------------
`core/api/v1/auth.py::forgot_password` 는 dj-core 안이다(§0.4 금지구역 — 읽기·호출만).
그 함수는 메일 발송을 `try/except Exception` 으로 감싸고, **실패해도 성공 응답을
그대로 돌려준다**:

    email_backend = SMTPEmailBackend()
    email_backend.send_notification(email_data)
    ...
    except Exception as e:
        logger.error(...)
        # 사용자에게는 오류를 알리지 않는다(주소 존재를 흘리지 않으려고)

의도는 좋다 — 「없는 주소도 같은 답」으로 계정 존재를 감춘다. 그런데 **그 의도가 고장까지
같이 숨긴다.** 지금 SMTP 는 컨테이너 생성값(`SMTP_SERVER=smtp.invalid`)이라 **항상 죽어
있고**, 화면은 매번 「메일을 보냈습니다」라고 말한다. 이것은 재설정을 요청한 사람 전원이
받는 **거짓말**이다.

★★ **이 겹이 고치는 것은 거짓말이지, 유출은 아니다** — 순서가 핵심이다
------------------------------------------------------------------------
발송 실패를 **있는 주소에서만** 보이게 고치면(예: 있는 주소는 "실패", 없는 주소는
"성공") 그 차이로 회원 명단을 셀 수 있다 — 유출 통로를 새로 여는 것과 같다. 그래서
이 길목은 **주소를 보기 전에** SMTP 도달성부터 본다:

    ① SMTP 가 죽어 있으면 → 주소를 조회하지도 않고 **모두에게 같은 실패 안내**
    ② SMTP 가 살아 있으면 → dj-core 로 그대로 넘긴다 (지금의 "같은 답" 규칙 그대로)

①의 순서를 뒤집으면(주소를 먼저 조회하고 그 결과에 따라 SMTP 를 본다) 있는 주소만
SMTP 검사를 타는 경로가 생길 수 있어, 마이크로타이밍이든 로그든 **계정 존재가 새는
길**이 다시 열린다. 그래서 이 파일의 유일한 판단 지점(`ResetMailGateMiddleware.__call__`)
은 **경로 문자열만** 보고 SMTP 를 확인하며, 요청 본문(주소)을 파싱하지 않는다.

무엇을 안 하는가
-----------------
- dj-core 를 고치지 않는다(§0.4). `core/api/v1/auth.py` 는 한 줄도 안 만진다.
- SMTP 로 실제 메일을 보내지 않는다 — 하는 일은 TCP 연결 1회뿐이다(EHLO 도 안 한다).
- 자격(SMTP_USERNAME/SMTP_PASSWORD)은 안 읽는다 — 이름만 읽는 것은 SMTP_SERVER ·
  SMTP_PORT 둘뿐이다(dj-core `SMTPEmailBackend` 이 `os.getenv` 로 읽는 것과 같은 이름).
- 값을 로그에 안 찍는다 — 서버 로그는 "SMTP 도달 불가" 한 줄뿐이다(호스트 이름도 안 낸다).

K2 경보 — **자리 없음** [실측 2026-09-24]
------------------------------------------
`kernels/k2_notify/services.py::send()` 와 `kernels/k2_notify/heartbeat.py` 의 발송
경로는 전부 **장치 경보 이벤트**(`event` · `TenantScope` · 규칙이 고르는 수신자)를
전제로 짜여 있다 — 인프라 SMTP 장애처럼 이벤트가 없는 상황을 위한 일반 경보 자리가
없다. 없는 자리를 억지로 채우려면 가짜 이벤트 행을 만들어야 하는데, 그것은 K2 의
전제(§ "발송 기록이 곧 조치 이력") 를 어기고 §0.4 인접 모델을 건드리는 위험이 더
크다. 그래서 이 겹은 **로그만** 남긴다(`_log_smtp_unreachable`) — 부를 K2 함수가
새로 생기면 그 자리에 한 줄을 더 넣으면 된다.

되돌리기
--------
`RESET_MAIL_GATE_ENABLED = False` 한 줄이다. 그 한 줄이면 이 겹은 통과만 한다.
"""
from __future__ import annotations

import logging
import os
import socket
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger(__name__)

#: 되돌리기 한 줄. 없으면 켜진 것으로 본다(새 겹은 켜져야 일을 한다) — jwt_guard.py 와 같은 관례.
SETTING_NAME = "RESET_MAIL_GATE_ENABLED"

#: 이 길목이 보는 유일한 경로. dj-core 의 라우트 이름과 같다
#: (`backend/tests/test_s_password_reset_walk.py::FORGOT`).
TARGET_PATH = "/api/v1/auth/forgot-password"
TARGET_METHOD = "POST"

#: SMTP 도달성 판정 캐시 — 60초. 요청마다 TCP 를 새로 열지 않는다.
CACHE_KEY = "reset_mail_gate:smtp_reachable"
CACHE_TTL_SECONDS = 60

#: 「짧은 timeout」— 죽은 SMTP 로 요청 전체가 그만큼 묶이지 않게 한다.
CONNECT_TIMEOUT_SECONDS = 2.0

#: 답 본문의 기계 낱말.
UNREACHABLE_CODE = "reset_mail_unavailable"

#: 고객 말 — 「보냈습니다」가 아니라 **정직한 실패 안내**다. dj-core 의 4개 국어 틀과 같다.
MESSAGE = {
    #: ★ 조율자 병합(09-24) — 처음 문구는 「관리자에게 **알렸습니다**」였다. 그러나 K2 경보
    #:   자리가 없어 이 겹은 **로그만** 남긴다(아래 「K2 경보 — 자리 없음」). 「보냈습니다」
    #:   거짓말을 고치며 「알렸습니다」 거짓말을 새로 만들 수는 없다 — 한 일만 말한다.
    #:   K2 자리가 생겨 실제로 알리는 날 이 문구를 되돌린다.
    "ko": "지금은 메일을 보낼 수 없습니다 — 관리자에게 문의하십시오.",
    "en": "Mail cannot be sent right now — please contact your administrator.",
    "vi": "Hiện không thể gửi email lúc này — vui lòng liên hệ quản trị viên.",
    "th": "ขณะนี้ไม่สามารถส่งอีเมลได้ — โปรดติดต่อผู้ดูแลระบบ",
}


def enabled() -> bool:
    return bool(getattr(settings, SETTING_NAME, True))


def _tcp_probe() -> bool:
    """SMTP_SERVER:SMTP_PORT 로 TCP 연결 1회. **이름만** 읽는다 — dj-core
    `core/notifications/backends/smtp_email_backend.py::SMTPEmailBackend` 이
    `os.getenv` 로 읽는 것과 같은 두 이름(SMTP_SERVER · SMTP_PORT)이다.

    값은 반환하지 않고, 로그에도 안 찍는다 — 이 함수는 참/거짓만 낸다.
    """
    host = os.getenv("SMTP_SERVER")
    port_raw = os.getenv("SMTP_PORT")
    if not host or not port_raw:
        return False
    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        return False
    try:
        with socket.create_connection((host, port), timeout=CONNECT_TIMEOUT_SECONDS):
            return True
    except OSError:
        return False


def smtp_reachable() -> bool:
    """60초 캐시를 두른 판정. **함수를 나누는 이유는 시험이 이 이름을 patch 하기
    위해서다**(jwt_guard.py::would_djcore_raise 와 같은 자리 — 시험은 네트워크를
    실제로 열지 않는다).
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return bool(cached)
    result = _tcp_probe()
    cache.set(CACHE_KEY, result, CACHE_TTL_SECONDS)
    return result


def _log_smtp_unreachable() -> None:
    """서버 로그 1줄. 값도 host 이름도 안 낸다 — "SMTP 도달 불가" 뿐이다."""
    logger.error("[RESET_MAIL_GATE] SMTP 도달 불가")
    #: K2 경보 — 부를 함수가 없다(위 독스트링 참고). 이 로그가 지금의 유일한 표지다.


def unreachable_response() -> JsonResponse:
    resp = JsonResponse(
        {"success": False, "status": 503, "code": UNREACHABLE_CODE, "message": MESSAGE},
        status=503, json_dumps_params={"ensure_ascii": False})
    resp["Cache-Control"] = "no-store"
    return resp


class ResetMailGateMiddleware:
    """비밀번호 찾기 문을 **주소를 보기 전에** SMTP 로 가른다.

    ★ `__call__` 은 `request.path` 와 `request.method` 만 본다 — 본문(이메일 주소)은
      **절대 파싱하지 않는다.** 파싱해서 주소 유무로 무언가를 갈라 버리면 이 겹 자체가
      유출 통로가 된다(위 모듈 독스트링의 "순서가 핵심이다" 참고).
    """

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: Any):
        if not enabled():
            return self.get_response(request)
        if (getattr(request, "method", None) == TARGET_METHOD
                and getattr(request, "path", None) == TARGET_PATH):
            if not smtp_reachable():
                _log_smtp_unreachable()
                return unreachable_response()
        return self.get_response(request)
