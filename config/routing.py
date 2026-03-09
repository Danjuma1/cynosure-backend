"""
Main WebSocket URL routing for the application.
Combines all app-specific WebSocket routes.
"""
from django.urls import path

from apps.cause_lists.consumers import CauseListConsumer
from apps.notifications.consumers import NotificationConsumer

websocket_urlpatterns = [
    path('ws/cause-lists/', CauseListConsumer.as_asgi()),
    path('ws/notifications/', NotificationConsumer.as_asgi()),
]
