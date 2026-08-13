"""
WebSocket routing for media notifications
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/media/download/$', consumers.MediaDownloadConsumer.as_asgi()),
    re_path(r'ws/media/detect/$', consumers.MediaDetectConsumer.as_asgi()),
    re_path(r'ws/media/upload-detection/$', consumers.MediaUploadDetectionConsumer.as_asgi()),
]

