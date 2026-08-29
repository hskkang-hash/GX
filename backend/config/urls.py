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
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# URLs patterns main
urlpatterns = [
    path("admin/", admin.site.urls),
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
