"""
WebSocket URL routing for cause lists.
"""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/cause-lists/', consumers.CauseListConsumer.as_asgi()),
]
