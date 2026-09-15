# -*- coding: utf-8 -*-
"""5xx 응답이 **본문에 내부를 싣지 않게 한다** — P-100 (2026-09-07 · 차선 B).

무엇이 이 파일을 만들게 했나 — **출생 표본**
--------------------------------------------
[실측 2026-09-07 · `gxseed_u4_official`(view_only) 로 8000 을 두드림]

    GET /api/report-template/   ->  HTTP **500** · text/plain 951바이트
        Traceback (most recent call last):
          File "/usr/local/lib/python3.11/site-packages/ninja_extra/operation.py", line 216, in run
          File "/usr/local/lib/python3.11/site-packages/ninja/operation.py", line 280, in _result_to_response
          ...
          pydantic_core._pydantic_core.ValidationError: ...

권한 거절 하나가 **역추적 전문**을 되돌려 줬다. 그 본문에는 셋이 들어 있었다:
설치 경로(`/usr/local/lib/python3.11/site-packages/...`) · 쓰고 있는 라이브러리
(`ninja_extra` · `pydantic`) · 우리 코드의 파일명과 줄번호. 거절 하나에 대고
**공격자에게 지도를 그려 준 것**이고, 게다가 그 답은 403 이어야 했다(`401·403 != 5xx`).

왜 미들웨어 한 겹으로는 안 되나 — **django-ninja 가 예외를 먼저 삼킨다**
------------------------------------------------------------------------
`ninja/errors.py:_default_exception` 은 이렇게 생겼다 [실측 · 설치본 확인]:

    def _default_exception(request, exc, api):
        if not settings.DEBUG:
            raise exc                       # <- 여기서만 Django 로 넘어간다
        logger.exception(exc)
        tb = traceback.format_exc()
        return HttpResponse(tb, status=500, content_type="text/plain")

즉 **DEBUG 가 켜진 판에서는 예외가 뷰 밖으로 나오지 않는다.** 나오지 않으므로
Django 의 `process_exception` 도 불리지 않고, `common.api_contract` 의 승격 경로
(B 부류 복원)가 **통째로 죽는다.** 시험은 DEBUG=False 로 돌아서 초록이었고
운영 서버(개발 프로필 · DEBUG=True)만 500 이었다 — 착시 (9) 의 또 한 사례다.

그래서 이 파일은 **두 겹**이다. 한 겹이 지워져도 다른 한 겹이 남는다:

  (1) `install_safe_ninja_handlers()`  ninja API 들의 `Exception` 처리기를 우리 것으로
      바꾼다. DEBUG 와 **무관하게** 역추적을 본문에 싣지 않는다. 여기서 먼저
      `api_contract` 의 거부 dict 복원을 시도하므로 **거절은 403 으로 되살아난다.**
  (2) `SafeErrorBodyMiddleware`        응답 단계 그물. ninja 를 안 타는 라우트
      (Django 뷰 · 관리자 · 오류 화면)에서 나온 5xx 본문에 표지가 남아 있으면
      **본문만 갈아 끼운다.** 상태줄과 헤더는 그대로 둔다.

역추적은 **사라지지 않는다. 자리를 옮긴다** — `logger.exception` 으로 서버 로그에
전문이 남는다. 개발자가 잃는 것은 없고, 바깥으로 나가는 것만 없어진다.

되돌리기 (D-212)
----------------
    settings.SAFE_ERROR_BODY = False   # 또는 환경변수 SAFE_ERROR_BODY=false
False 면 (1)은 원래 예외를 그대로 다시 던지고 (2)는 본문을 한 자도 안 만진다.

**개발 편의를 어디까지 지키나** — `scrub_applies()` 한 곳에서 정한다
--------------------------------------------------------------------
  · DEBUG=False (운영)  : **모든 경로**. 운영에서 내부가 새는 자리는 없어야 한다.
  · DEBUG=True  (개발)  : `/api/` 로 시작하는 경로만. 관리자·템플릿 화면의 Django
                          기술 500 쪽은 개발자 손에 그대로 남긴다. API 면은 개발에서도
                          닫는다 — **우리를 문 자리가 바로 그 면**이었다.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from django.conf import settings
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404, HttpResponse, JsonResponse
from django.http.multipartparser import MultiPartParserError

logger = logging.getLogger(__name__)

#: 되돌리기 한 줄의 이름. 시험도 운영도 이 이름만 본다 (D-212).
FLAG = "SAFE_ERROR_BODY"

#: 본문에서 발견되면 **내부가 샜다**고 판정하는 표지.
#: P-100 이 이름으로 못박은 넷 중 셋이 문자열이고, 넷째(내부 파일경로)는 아래 정규식이다.
LEAK_MARKERS: tuple = (
    "Traceback",
    "pydantic",
    'File "',
)

#: 넷째 표지 — **내부 파일시스템 경로**. 컨테이너의 posix 경로와 개발자 PC 의 윈도우
#: 경로를 같이 본다. `site-packages` 는 조각만 나와도 설치 위치를 말해 준다.
_INTERNAL_PATH = re.compile(
    r"(site-packages|dist-packages"
    r"|/(?:app|repo|usr|home|root|opt|srv|var)/[A-Za-z0-9_.\-/]+"
    r"|[A-Za-z]:\\[A-Za-z0-9_.\-\\]+)"
)

#: 밖으로 나가는 본문. **고정 문자열이다** — 예외에서 가져온 글자를 한 자도 안 싣는다.
SAFE_MESSAGE = "서버가 요청을 처리하지 못했습니다. 관리자에게 문의하세요."


def enabled() -> bool:
    """이 겹이 켜져 있는가. 기본은 **켜짐**(닫힌 쪽이 기본이다)."""
    return bool(getattr(settings, FLAG, True))


def leak_markers(text: Any) -> list:
    """본문에서 찾은 표지들. **순수 함수다** (D-277) — 시험이 이것만 보고 판정한다.

    돌려주는 것은 이름의 목록이다. 빈 목록이면 「이 본문에는 내부가 없다」.
    """
    if isinstance(text, (bytes, bytearray)):
        text = bytes(text).decode("utf-8", "replace")
    if not isinstance(text, str):
        return []
    found = [m for m in LEAK_MARKERS if m in text]
    if _INTERNAL_PATH.search(text):
        found.append("internal_path")
    return found


def scrub_applies(path: str, debug: bool) -> bool:
    """이 경로의 5xx 본문을 갈아 끼우는가. **순수 함수다.**

    운영(DEBUG=False)에서는 어디서나. 개발에서는 API 면만 — 사유는 모듈 설명 참조.
    """
    if not enabled():
        return False
    if not debug:
        return True
    return str(path or "").startswith("/api/")


def safe_payload(status: int = 500) -> dict:
    """밖으로 나가는 본문 한 벌. 기존 클라이언트가 읽던 봉투 모양을 그대로 쓴다."""
    return {"success": False, "status_code": int(status), "message": SAFE_MESSAGE,
            "detail": "Internal server error"}


def safe_response(status: int = 500) -> JsonResponse:
    """무해한 5xx 응답 하나."""
    return JsonResponse(safe_payload(status), status=status)


# =============================================================================
# (1) ninja 처리기 — **DEBUG 와 무관하게** 역추적을 본문에 안 싣는다
# =============================================================================
_installed = False


def _safe_api_exception(request, exc, api):
    """모든 ninja API 의 `Exception` 처리기.

    순서가 요점이다:
      (ㄱ) **먼저 거절을 되살린다.** `@path_permission` 의 거부 dict 가 응답 스키마
           검증에서 터진 것이면(B 부류) 그 dict 를 되찾아 403 으로 낸다. 이 자리를
           `process_exception` 에만 두면 DEBUG 켜진 판에서는 영영 안 불린다.
      (ㄴ) 그다음에야 500 이다. 그리고 그 500 은 **고정 본문**이다.
      (ㄷ) 꺼져 있으면(`SAFE_ERROR_BODY=False`) 원래 예외를 그대로 던진다 —
           이 겹이 진짜 결함을 삼키지 않는다는 것을 되돌리기로도 보인다.
    """
    from common.api_contract import (
        _denial_from_exception, denial_status, promotion_enabled_for,
    )

    # Django 에게 흐름 제어인 예외는 **우리가 채 가지 않는다** — 미들웨어 쪽과 같은 사유다.
    if isinstance(exc, SafeErrorBodyMiddleware.PASSTHROUGH):
        raise exc

    payload = _denial_from_exception(exc)
    if payload is not None and promotion_enabled_for(request.path):
        code = denial_status(payload)
        logger.info("[SAFE_ERROR_BODY] 거절 복원 %s %s: 500 -> %s",
                    request.method, request.path, code)
        return JsonResponse(payload, status=code)

    # 전문은 **로그로** 간다. 본문으로는 안 간다.
    logger.exception("[SAFE_ERROR_BODY] %s %s 처리 중 예외", request.method, request.path)
    if not scrub_applies(request.path, bool(getattr(settings, "DEBUG", False))):
        raise exc
    return api.create_response(request, safe_payload(500), status=500)


def install_safe_ninja_handlers() -> int:
    """등록된 모든 ninja API 의 `Exception` 처리기를 갈아 끼운다. 바꾼 API 수를 낸다.

    ★ **라우트를 정적으로 세지 않는다** — `common.tenant_scope._iter_ninja_apis()` 를
      쓴다. 라우트 열거기가 이미 쓰는 그 자리고, 새 API 가 생겨도 같이 덮인다.
    """
    global _installed
    from functools import partial

    from common.tenant_scope import _iter_ninja_apis

    count = 0
    for _mount, api in _iter_ninja_apis():
        try:
            api.add_exception_handler(Exception, partial(_safe_api_exception, api=api))
            count += 1
        except Exception:  # pragma: no cover - 이상한 API 객체 방어
            logger.warning("[SAFE_ERROR_BODY] 처리기를 못 달았다: %r", api)
    _installed = True
    logger.info("[SAFE_ERROR_BODY] ninja API %d개에 안전 예외 처리기를 달았다", count)
    return count


def ensure_installed() -> None:
    """한 번만 단다. URL 설정을 아직 못 읽는 시점이면 **다음 요청에 다시 시도한다.**"""
    if _installed:
        return
    try:
        install_safe_ninja_handlers()
    except Exception as exc:  # pragma: no cover - 기동 순서 방어
        logger.warning("[SAFE_ERROR_BODY] 처리기 설치 지연 — %s", exc)


# =============================================================================
# (2) 응답 단계 그물 — ninja 를 안 타는 5xx 까지 덮는다
# =============================================================================
class SafeErrorBodyMiddleware:
    """5xx 본문에 표지가 남아 있으면 **본문만** 갈아 끼운다.

    ★ 자리 — `GZipMiddleware` **바로 아래**(= 안쪽). 두 조건이다:
      (1) GZip 보다 안쪽이어야 압축 전 본문을 읽을 수 있다.
      (2) 5xx 를 만드는 어떤 겹보다도 바깥이어야 그 본문을 볼 수 있다 — 그래서
          GZip 바로 다음, 나머지 전부보다 위다.

    ★ **상태줄은 안 고친다.** 500 을 200 으로 만들지 않는다. 이 겹이 하는 것은
      「무엇이 샜나」뿐이고, 「무엇이었나」는 `api_contract` 의 몫이다.
    """

    #: Django 에게 **오류가 아니라 흐름 제어**인 예외들. 손대지 않는다 —
    #: `django/core/handlers/exception.py:response_for_exception` 이 각각
    #: 404 · 403 · 400 으로 옮긴다. 우리가 채 가면 그 번역이 500 이 된다.
    PASSTHROUGH = (Http404, PermissionDenied, SuspiciousOperation, MultiPartParserError)

    def __init__(self, get_response):
        self.get_response = get_response
        ensure_installed()

    def __call__(self, request):
        ensure_installed()
        response = self.get_response(request)
        return self._scrub(request, response)

    def _scrub(self, request, response: HttpResponse) -> HttpResponse:
        if getattr(response, "status_code", 200) < 500:
            return response
        if not scrub_applies(getattr(request, "path", ""),
                             bool(getattr(settings, "DEBUG", False))):
            return response
        if getattr(response, "streaming", False):
            return response
        if response.has_header("Content-Encoding"):
            return response
        try:
            text = response.content.decode(response.charset or "utf-8", "replace")
        except Exception:  # pragma: no cover - 본문을 못 읽으면 손대지 않는다
            return response
        found = leak_markers(text)
        if not found:
            return response
        logger.error("[SAFE_ERROR_BODY] %s %s 의 %s 본문에서 내부를 걷어냈다: %s",
                     request.method, request.path, response.status_code, found)
        response.content = json.dumps(
            safe_payload(response.status_code), ensure_ascii=False).encode("utf-8")
        response["Content-Type"] = "application/json"
        if response.has_header("Content-Length"):
            response["Content-Length"] = str(len(response.content))
        return response

    def process_exception(self, request, exception):
        """뷰 밖으로 나온 예외 — 여기서 무해한 5xx 로 끝낸다.

        ★ 이 겹은 `ApiContractStatusMiddleware` **보다 바깥**이다. Django 는
          `process_exception` 을 안쪽부터 부르므로 **승격이 먼저 시도되고**,
          그것이 None 을 낸 것만 여기 온다 — 거절을 500 으로 뭉개지 않는다.

        ★ [실측 2026-09-07 · 이 겹을 처음 달자마자 났다] `PASSTHROUGH` 를 빼면
          `tests/test_api_contract.py::test_token_pair_is_gone` 이 빨개진다:
          `config/urls.py:_gone` 이 던지는 **`Http404` 를 500 으로 뭉갰다.**
          Django 에게 이 예외들은 오류가 아니라 **흐름 제어**이고
          (`django/core/handlers/exception.py:response_for_exception` 이 각각
          404·403·400 으로 옮긴다), 우리가 먼저 채 가면 그 번역이 사라진다.
          `401·403 != 5xx` 를 지키자고 만든 겹이 404 를 500 으로 만들면 안 된다.
        """
        if isinstance(exception, self.PASSTHROUGH):
            return None
        if not scrub_applies(getattr(request, "path", ""),
                             bool(getattr(settings, "DEBUG", False))):
            return None
        logger.exception("[SAFE_ERROR_BODY] %s %s 에서 예외가 뷰 밖으로 나왔다",
                         request.method, request.path)
        return safe_response(500)
