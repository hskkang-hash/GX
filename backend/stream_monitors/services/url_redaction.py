# -*- coding: utf-8 -*-
"""카메라 주소에서 **자격을 지운다** — 로그로 가기 전에 (P-200 · 턴 X · 차선 U3).

왜 한 곳에 있나
---------------
턴 W(P-192)에 `capture_service.py` 안에서만 `_redact` 를 만들어 썼다. 그 사이
**옆 파일에서 같은 줄이 멀쩡히 살아 있었다** — `stream_monitor_services.py` 의
`logger.info(f"… RTSP URL: {rtsp_url}")` 일곱 줄이 `StreamMonitor.ip_source` 를
그대로 찍고 있었다 [실측 2026-09-20]. 한 파일 안에 숨은 `_redact` 는 옆 파일이
못 쓴다. 그래서 **부를 수 있는 한 곳**으로 옮겼다.

지키는 판정기는 `scripts/verify_camera_secret_logs.py` (게이트 `camera-secret-logs`)다.
여기 함수 이름을 바꾸면 그 판정기의 `SANITIZERS` 도 같이 고쳐야 한다 — 안 고치면
씻고 있는데도 빨강이 난다(조용히 갈리지 않는다).
"""
from __future__ import annotations

import re
import urllib.parse

#: **통째로 주소인 문자열**만 손댄다.
#:
#: ⚠ 「`://` 가 들어 있으면 주소」로 보면 안 된다. `redact_payload` 는 응답 본문도
#:   지나가는데(`result['api_response']` 는 남의 서버가 준 HTML 일 수 있다),
#:   그 안에 주소 한 조각이 섞였다고 **본문 전체를 주소로 바꿔 버리면** 로그에서
#:   고장 원인이 사라진다. 막는 것과 눈을 가리는 것은 다르다.
_WHOLE_URL_RE = re.compile(r"^[a-z][a-z0-9+.\-]*://", re.IGNORECASE)

#: 씻은 자리에 남기는 표. 로그를 보는 사람이 「지워진 것」과 「원래 없던 것」을 가른다.
REDACTED_MARK = "***"


def redact_url(url):
    """`rtsp://아이디:비밀번호@호스트:554/길` → `rtsp://***@호스트:554/길`.

    ★ 자격이 **없으면 아무것도 안 바꾼다** — 내부 미디어 서버 주소
      (`settings.RTSP_URL/stream/…`)는 그대로 읽혀야 사람이 쓸모를 얻는다.
    ★ 질의 문자열은 통째로 버린다 — 자격이 `?user=…&pass=…` 로 오는 카메라가 있다.
    """
    if not isinstance(url, str) or not _WHOLE_URL_RE.match(url):
        return url
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return "(주소 해석 실패)"
    if not parts.hostname:
        return url
    host = parts.hostname
    if parts.port:
        host = "%s:%d" % (host, parts.port)
    if parts.username or parts.password:
        host = "%s@%s" % (REDACTED_MARK, host)
    return urllib.parse.urlunsplit((parts.scheme, host, parts.path, "", ""))


def redact_payload(data):
    """dict·list 안의 주소 값을 씻은 **사본**을 낸다. 원본은 한 글자도 안 건드린다.

    ⚠ 이것이 필요한 이유 — **자격은 한 겹 건너서 샌다.**
      `body = {'rtsp_url': rtsp_url}` 를 만들어 두고
      `logger.info(f"body: {json.dumps(body)}")` 로 찍으면, 주소 변수를 로그 줄에
      직접 안 썼는데도 자격이 그대로 나간다. 실제로 그렇게 새고 있었다
      (`stream_monitor_services.py:688` · `:744` · `:1254`).
    """
    if isinstance(data, dict):
        return {k: redact_payload(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return type(data)(redact_payload(v) for v in data)
    if isinstance(data, str):
        return redact_url(data)
    return data
