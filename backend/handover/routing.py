"""
WebSocket routing for handover notifications
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/handover/notifications/$', consumers.HandoverNotificationConsumer.as_asgi()),
]

