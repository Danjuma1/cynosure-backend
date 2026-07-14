"""
WebSocket URL routing for Brief Connect chat.
"""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/brief-connect/chat/<uuid:engagement_id>/', consumers.BriefChatConsumer.as_asgi()),
]
