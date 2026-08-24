"""외부 HTTP 호출 — 타임아웃 기본값과 저하 운전 (W0-17 · D-212).

무엇을 푸는가
    이 저장소는 외부 의존(스트리밍 서버·AI 분석·FlightBird·OpenSearch)에 `requests`
    로 직접 붙는다. 실측(evidence/W0-17/timeout_inventory.md)에서 **호출 75건 중 17건에
    타임아웃이 없었다.** 타임아웃 없는 호출 하나가 늦으면 워커가 잡히고, 잡힌 워커가
    쌓이면 서비스가 선다 — **부분 실패가 전면 정지가 되는 경로**다.

    더 나쁜 것은 그 다음이다. 목록 API 는 스트리밍 상태조회가 실패하면 예외가
    그대로 올라가 **통째로 HTTP 500** 이었다. 드론 목록은 스트리밍 서버와 무관하게
    보여야 하는 정보인데, 무관한 의존 하나가 화면 전체를 끈다.

두 가지만 제공한다
    `fetch_json(...)`  — 실패를 **예외가 아니라 값**으로 돌려준다: `(data, ok)`.
                          호출부는 `ok` 가 거짓이면 그 필드만 "일시 불가"로 표시하고
                          나머지는 200 으로 낸다.
    `request(...)`     — 타임아웃을 빠뜨릴 수 없는 `requests` 대체. 인자를 주지
                          않으면 설정값이 들어간다.

⚠ 타임아웃 숫자를 호출부에 적지 말 것 (D-212). 값은 `settings.EXTERNAL_HTTP_TIMEOUT`
  한 곳이고, 이 모듈이 그것을 읽는다. 흩어진 숫자는 바꿀 수 없는 숫자가 된다.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

import requests
from django.conf import settings

log = logging.getLogger(__name__)

#: 저하 운전 시 사용자에게 보일 표시. 화면 문구는 프런트가 i18n 으로 정한다.
UNAVAILABLE = "unavailable"
AVAILABLE = "ok"

#: 실패로 **간주하는** 예외. 여기 없는 예외는 버그이므로 삼키지 않는다.
#: (`ValueError` 는 JSON 파싱 실패 — 응답이 오긴 왔으나 형식이 다른 경우다.)
TRANSIENT_ERRORS: tuple[type[BaseException], ...] = (
    requests.exceptions.RequestException,
    ValueError,
)


#: 설정을 읽을 수 없는 실행 맥락(장고 밖 독립 스크립트)의 최후값.
#: 운영 경로는 항상 settings 를 읽는다 — 이 값은 "타임아웃 없음"으로 떨어지는 것을 막는 바닥이다.
_FALLBACK_TIMEOUT = (3.0, 5.0)
_FALLBACK_TIMEOUT_LONG = (3.0, 60.0)


def _setting(name: str, fallback: Any) -> Any:
    """settings 를 읽되, 장고가 구성되지 않은 맥락에서도 죽지 않는다.

    `getattr(settings, name, default)` 은 `ImproperlyConfigured` 를 삼키지 않는다 —
    독립 스크립트에서 이 모듈을 import 하면 그대로 터진다. 타임아웃을 넣으려다
    스크립트를 깨뜨리는 것은 목적에 반한다.
    """
    try:
        return getattr(settings, name, fallback)
    except Exception:  # ImproperlyConfigured 등 — 설정이 없는 실행 맥락
        return fallback


def default_timeout() -> Any:
    """설정된 (연결, 응답) 타임아웃. **이 함수만 값을 안다.**"""
    return _setting("EXTERNAL_HTTP_TIMEOUT", _FALLBACK_TIMEOUT)


def long_timeout() -> Any:
    """업로드·다운로드처럼 본래 오래 걸리는 호출용."""
    return _setting("EXTERNAL_HTTP_TIMEOUT_LONG", _FALLBACK_TIMEOUT_LONG)


def request(method: str, url: str, **kwargs: Any) -> requests.Response:
    """`requests.request` 와 같되 **타임아웃을 빠뜨릴 수 없다.**"""
    kwargs.setdefault("timeout", default_timeout())
    return requests.request(method, url, **kwargs)


def get(url: str, **kwargs: Any) -> requests.Response:
    return request("GET", url, **kwargs)


def post(url: str, **kwargs: Any) -> requests.Response:
    return request("POST", url, **kwargs)


def fetch_json(
    url: str,
    *,
    method: str = "GET",
    default: Any = None,
    on_error: Callable[[BaseException], None] | None = None,
    **kwargs: Any,
) -> tuple[Any, bool]:
    """JSON 을 가져오되 **실패를 값으로 돌려준다** — `(데이터, 성공여부)`.

    실패해도 예외를 올리지 않는다. 그것이 이 함수의 존재 이유다::

        streams, ok = fetch_json(f"{settings.STREAM_URL}/manage/v3/paths/list", default={})
        item["stream_status"] = AVAILABLE if ok else UNAVAILABLE

    ⚠ **인증·권한 실패를 이것으로 감추지 말 것.** 이 함수는 "이 정보가 없어도 화면이
      성립하는" 부수 정보에만 쓴다. 본체 데이터가 없으면 그것은 저하 운전이 아니라
      빈 화면이고, 사용자는 그것을 정상으로 오해한다.
    """
    kwargs.setdefault("timeout", default_timeout())
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json(), True
    except TRANSIENT_ERRORS as exc:
        if on_error is not None:
            on_error(exc)
        log.warning(
            "[DEGRADED] 외부 의존 실패 — %s %s (%s: %s). 저하 운전으로 계속한다.",
            method, url, type(exc).__name__, str(exc)[:200],
        )
        return default, False
