"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.http import Http404
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


# ─────────────────────────────────────────────────────────────────────────────
# ★ [D-411 · 판정 2 · 승인 세종 2026-09-19] `/api/token/pair` 를 **뺀다.**
#
#   그 문이 무엇이었나 — [실측 2026-09-18, 두 갈래]
#     · 웹 UI·모바일·게이트·시드 중 **아무도 부르지 않는다**(번들 21파일 정독 · 0건)
#     · 발급한 JWT 는 dj-core `core/auth.py:38` 이 `user.token` 없다고 거절한다
#     · 세션이 **없으면 401 · 남이 세워 두면 200** — 죽은 문이 아니라
#       **남의 세션에 기생하는 문**이다. 스스로는 아무것도 못 세운다
#   쓸모없는 토큰을 내주는 문은 기능이 아니라 **공격 면**이다. 그래서 닫는다.
#
#   ⚠ **dj-core 를 고치지 않는다** (D-207 · §0.4). 저 라우트는 `core.urls` 안에 있고
#     그 파일은 금지구역이다. 바깥에서 막는다: Django 는 **먼저 등록된 패턴**에서
#     멈추므로, `include("core.urls")` **앞**에 같은 경로를 놓으면 그 문에 못 닿는다.
#     이 줄을 아래로 옮기면 문이 다시 열린다 — 순서가 곧 판정이다.
#
#   ⚠ `token/refresh` · `token/verify` 는 **건드리지 않는다.** 이번에 잰 것은
#     `pair` 하나이고, 재지 않은 것을 함께 닫으면 그 순간 이 결정이 추측이 된다(D-301).
def _gone(request, *args, **kwargs):
    """닫힌 문. **404 다** — 401·403 이 아니다.

    401 을 내면 「자격증명이 모자란다」로 읽혀 연동 담당자가 계정을 고치려 든다.
    없는 것은 없다고 말한다(D-290 — 부재와 거절을 가른다).
    """
    raise Http404(
        "/api/token/pair 는 2026-09-19 에 제거됐다 (D-411). "
        "로그인은 POST /api/v1/auth/login 이다 — docs/agent/authn_paths.md"
    )

# URLs patterns main
urlpatterns = [
    path("admin/", admin.site.urls),
    # ★ D-411 — `core.urls` **보다 먼저.** 아래로 내리면 문이 다시 열린다.
    path("api/token/pair", _gone),
    # ★ [P-105 · 2026-09-07 턴 M · 차선 B] 역할 대기 화면의 문. **`core.urls` 보다 먼저.**
    #   `core.urls` 는 `api/` 전체를 include 하고 그 안에 `/v1/...` 라우터들이 산다.
    #   지금은 `core` 안에 `v1/access` 가 없으므로 뒤에 두어도 닿지만, **선언 순서가 곧
    #   라우팅**이다(D-411 이 같은 성질을 반대로 썼다 — 먼저 선언해 문을 닫았다).
    #   dj-core 가 언젠가 같은 이름을 들이면 우리 문이 조용히 삼켜지고, 그때 나타나는
    #   증상은 오류가 아니라 **404 하나**다. 앞에 둔다.
    path("api/v1/access/", include("apps.access.urls")),  # 역할 대기 (P-105)
    path("api/", include("core.urls")),  # APIs core
    path("api/devices/", include("devices.urls")),  # APIs devices
    path("api/delivery/", include("delivery.urls")),  # APIs delivery
    path("api/orders/", include("orders.urls")),  # APIs orders
    # path('api/geolocation/', include('geolocation.urls')),       # APIs geolocation
    # path('api/nominatim/', include('geoutils.urls')),      # APIs nominatim geocoding
    path("api/terminals/", include("terminals.urls")),  # APIs terminals
    path(
        "api/dronehw/", include("drone_communication.urls.dronehw_url")
    ),  # APIs dronehw
    # path('api/waybill/', include('waybill.urls')),      # APIs waybill
    path("api/print-format/", include("print_format.urls")),  # APIs print format
    path(
        "api/operation-settings/", include("operation_settings.urls")
    ),  # API Integration System
    path("api/dashboard/", include("dashboard.urls")),  # API Dashboard
    path(
        "api/report-template/", include("report_template.urls")
    ),  # API Report Template
    path("api/third-api/", include("third_api.urls")),  # APIs third party integration
    path(
        "api/stream-monitors/", include("stream_monitors.urls")
    ),  # APIs stream monitors,
    path(
        "api/checklist-setting/", include("checklist_setting.urls")
    ),  # APIs checklist setting
    path(
        "api/operational-data/", include("operational_data.urls")
    ),  # APIs operational data
    path("api/optimization/", include("optimization.urls")),  # 🚀 Background optimization APIs
    path("api/partner/", include("partner.urls")),  # 🚀 Background optimization APIs
    path("api/flight-log/", include("flight_log.urls")),  # 🚀 Background optimization APIs
    path("api/surveillance/", include("surveillance.urls")),  # 🚀 Surveillance & GCS APIs
    path("api/proxy/", include("proxy.urls")),  # Proxy for iframe content
    path("api/handover/", include("handover.urls")),  # Handover Management APIs
    path("api/task-status/", include("task_status.urls")),  # Task status tracking APIs
    path("api/media-data/", include("media_data.urls")),  # Media data (MinIO) management APIs
    # ★ L4 DSM App — F-09 대시보드 · F-10 알림 · F-11 보고서 · F-12 설정.
    #   Django 앱이 아니다(모델이 없다) — INSTALLED_APPS 를 건드리지 않고 라우트만 붙인다.
    #   신규 라우트는 트립와이어(D-275 §5-1)를 통과해야 한다: 문지기 없는 새 경로가
    #   하나 생기면 그 순간 다시 샌다.
    path("api/dsm/", include("apps.dsm.urls")),  # 재난안전 모니터링 App (F-09~F-12)
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
