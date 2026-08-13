"""
WebSocket routing configuration for partner notifications
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/partner-callbacks/$', consumers.PartnerCallbackNotificationConsumer.as_asgi()),
]
