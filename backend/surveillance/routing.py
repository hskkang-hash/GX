"""WebSocket routing for surveillance notifications."""

from django.urls import re_path

from surveillance.consumers import SurveillanceProfileNotificationConsumer


websocket_urlpatterns = [
    re_path(r"^ws/surveillance/profiles/$", SurveillanceProfileNotificationConsumer.as_asgi()),
]


