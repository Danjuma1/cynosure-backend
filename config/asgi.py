"""
ASGI config for Cynosure project.
Configures Django Channels for WebSocket support.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from apps.common.middleware import JWTAuthMiddleware
from apps.notifications.routing import websocket_urlpatterns as notification_ws_patterns
from apps.cause_lists.routing import websocket_urlpatterns as cause_list_ws_patterns

# Combine all WebSocket URL patterns
websocket_urlpatterns = notification_ws_patterns + cause_list_ws_patterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
