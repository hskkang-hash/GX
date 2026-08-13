"""
WebSocket routing for orders
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Order notifications for authenticated users
    re_path(r'^ws/orders/notifications/?$', consumers.OrderNotificationConsumer.as_asgi()),
    
    # Public order tracking by order code
    re_path(r'^ws/orders/track/(?P<order_code>[^/]+)/?$', consumers.OrderTrackingConsumer.as_asgi()),
]
