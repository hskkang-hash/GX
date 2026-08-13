from ninja_extra import NinjaExtraAPI
from django.urls import path
from stream_monitors.views import StreamMonitorsAPI
from stream_monitors.views.drawing_views import DrawingAPI
from stream_monitors.views.auth_views import csrf_token_view, auth_status_view

stream_monitors_api = NinjaExtraAPI(urls_namespace='stream_monitors')

stream_monitors_api.register_controllers(
    StreamMonitorsAPI,
    DrawingAPI
)

urlpatterns = [
    path('', stream_monitors_api.urls),
    path('auth/csrf-token/', csrf_token_view, name='stream_monitors_csrf_token'),
    path('auth/status/', auth_status_view, name='stream_monitors_auth_status'),
] 
