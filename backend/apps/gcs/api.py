# -*- coding: utf-8 -*-
"""GCS(드론 비행 제어) 경유 — 화면이 GCS 키를 들지 않게 한다 (WO-GRDX-20261002-10 AC-2 · S1 GRDX-FIRST-010).

출생 표본 [실측 2026-10-02 · `-06` AC-5]
    배포 번들 `index-D7n8w_2e.js` 에 GCS bearer 키 원문 4벌 — `VITE_CGS_APIKEY` 가 빌드 때 박혔다.
    뒷단 `GCS_APIKEY` 와 **같은 값**이고, 로그인 없이 `/login` 만 열어도 받는다.

그래서 화면 → `/api/gcs/<GCS 경로>`(우리 로그인 토큰) → 여기서 사람·역할을 확인한 뒤 → 서버가
`GCS_APIKEY` 로 `FLIGHTBRID_URL` 을 부른다. 키는 서버 환경에만 있고 응답·로그에 싣지 않는다.

닫힌 쪽이 기본이다.
  · 로그인 없음 → 401 (`CustomJWTAuth`)
  · 역할 0 · 읽기 전용 역할의 쓰기 → 403 (`common.role_gate` 미들웨어 — `/api/` 전부에 걸린다)
  · GCS 경로는 **화면 라이브러리(@gaion/gcs-fe `config/api.ts`)가 실제로 부르는 첫 마디만** 연다.
    GCS 의 자기 로그인(`auth/*`)은 열지 않는다 — 키 갈래에서는 쓰지 않는다.
  · 쿼리로 오는 토큰(`access_key=`)은 받지 않는다 — 주소에 실린 자격은 로그에 남는다.
    텔레메트리 스트림(EventSource · 머리말을 못 단다)은 그래서 이 경유에 없다 — 보고서 「멈춤」.
되돌리기: `config/urls.py` 의 `api/gcs/` 한 줄.
"""
from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from ninja_extra import api_controller, route

from core.api.v1.auth import CustomJWTAuth

logger = logging.getLogger(__name__)

#: 화면 라이브러리가 부르는 첫 마디 [실측 · gx-fe-build:/app/node_modules/@gaion/gcs-fe/src 전수].
ALLOWED_FIRST = frozenset({
    "formations", "drones", "missions", "connections", "api", "streams",
    "survey", "gotohere", "joystick", "health",
})
#: `api/` 아래는 둘만(`api/drone/*` · `api/v1/groups`).
ALLOWED_API_SECOND = frozenset({"drone", "v1"})
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]
TIMEOUT_S = 15
#: 쿼리에 실려 오면 버리는 이름 — 경유는 우리 토큰만 믿는다(라이브러리의 텔레메트리 갈래가 `access_key=` 를 단다).
DROP_QUERY = frozenset({"access_key", "accessKey", "token"})


def allowed_path(path: str) -> bool:
    parts = [p for p in path.split("/") if p]
    if not parts or any(p in (".", "..") for p in parts):
        return False
    if parts[0] not in ALLOWED_FIRST:
        return False
    if parts[0] == "api":
        return len(parts) >= 2 and parts[1] in ALLOWED_API_SECOND
    return True


def _upstream_headers(request) -> dict:
    headers = {"Accept": request.headers.get("Accept", "application/json")}
    ctype = request.headers.get("Content-Type")
    if ctype:
        headers["Content-Type"] = ctype
    key = getattr(settings, "GCS_APIKEY", "") or ""
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


@api_controller("", tags=["GCS 경유"])
class GcsProxyAPI:
    @route.generic("/{path:path}", methods=METHODS, auth=CustomJWTAuth(), url_name="gcs_proxy")
    def proxy(self, request, path: str):
        if not allowed_path(path):
            return JsonResponse({"detail": "Not Found"}, status=404)
        base = (getattr(settings, "FLIGHTBRID_URL", "") or "").rstrip("/")
        if not base:
            return JsonResponse({"detail": "GCS is not configured"}, status=503)
        params = [(k, v) for k, v in request.GET.items() if k not in DROP_QUERY]
        try:
            up = requests.request(
                request.method,
                f"{base}/{path}",
                params=params,
                data=request.body or None,
                headers=_upstream_headers(request),
                timeout=TIMEOUT_S,
            )
        except requests.RequestException as exc:
            # 예외 문장에는 주소가 실린다 — 화면에는 갈래만, 로그에는 종류만.
            logger.warning("gcs proxy upstream unreachable: %s", type(exc).__name__)
            return JsonResponse({"detail": "GCS unreachable"}, status=502)
        return HttpResponse(
            up.content,
            status=up.status_code,
            content_type=up.headers.get("Content-Type", "application/json"),
        )
