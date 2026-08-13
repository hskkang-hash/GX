"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""
# asgi.py
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from stream_monitors.routing import websocket_urlpatterns as stream_websocket_patterns
from orders.routing import websocket_urlpatterns as orders_websocket_patterns
from operational_data.routing import websocket_urlpatterns as operational_data_websocket_patterns
from partner.routing import websocket_urlpatterns as partner_websocket_patterns
from surveillance.routing import websocket_urlpatterns as surveillance_websocket_patterns
from handover.routing import websocket_urlpatterns as handover_websocket_patterns
from media_data.routing import websocket_urlpatterns as media_data_websocket_patterns

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

print("🚀 ASGI server started: ready for WebSockets")
django_asgi_app = get_asgi_application()

# Combine all WebSocket URL patterns
all_websocket_patterns = (
    stream_websocket_patterns
    + orders_websocket_patterns
    + operational_data_websocket_patterns
    + partner_websocket_patterns
    + surveillance_websocket_patterns
    + handover_websocket_patterns
    + media_data_websocket_patterns
)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(all_websocket_patterns)
    ),
})
