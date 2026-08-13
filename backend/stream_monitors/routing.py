"""
WebSocket routing for stream monitors
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/drawing/session/(?P<session_id>\d+)/?$', consumers.DrawingConsumer.as_asgi()),
    re_path(r'^ws/drawing/session/all/?$', consumers.AllDrawingConsumer.as_asgi()),
    re_path(r'^ws/external-data-stream/?$', consumers.ExternalDataStreamConsumer.as_asgi()),
]