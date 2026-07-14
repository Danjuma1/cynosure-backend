"""
WebSocket consumer for real-time Brief Connect chat.
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class BriefChatConsumer(AsyncWebsocketConsumer):
    """
    One consumer per engagement chat. Only the engagement's two parties may
    connect. Messages themselves are created via the REST endpoint (so
    multipart file uploads work normally); this socket relays the resulting
    `chat_message` event plus lightweight `typing`/`read_receipt` signals.
    """

    async def connect(self):
        self.user = self.scope.get('user')
        self.engagement_id = self.scope['url_route']['kwargs']['engagement_id']

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        if not await self.is_participant():
            await self.close()
            return

        self.group_name = f'brief_chat_{self.engagement_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to Brief Connect chat',
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Invalid JSON'}))
            return

        action = data.get('action')
        if action == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
        elif action == 'typing':
            await self.channel_layer.group_send(self.group_name, {
                'type': 'typing_event',
                'user_id': str(self.user.id),
            })
        elif action == 'mark_read':
            await self.mark_read()
            await self.channel_layer.group_send(self.group_name, {
                'type': 'read_receipt',
                'user_id': str(self.user.id),
            })

    @database_sync_to_async
    def is_participant(self):
        from apps.brief_connect.models import BriefEngagement
        try:
            engagement = BriefEngagement.objects.get(id=self.engagement_id)
        except (BriefEngagement.DoesNotExist, ValueError):
            return False
        return self.user in (engagement.requester, engagement.holding_lawyer)

    @database_sync_to_async
    def mark_read(self):
        from django.utils import timezone
        from .models import Message
        Message.objects.filter(
            engagement_id=self.engagement_id, is_read=False,
        ).exclude(sender=self.user).update(is_read=True, read_at=timezone.now())

    # ── Group event handlers ────────────────────────────────────────────────

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'type': 'chat_message', 'message': event['message']}))

    async def typing_event(self, event):
        if event['user_id'] == str(self.user.id):
            return
        await self.send(text_data=json.dumps({'type': 'typing', 'user_id': event['user_id']}))

    async def read_receipt(self, event):
        if event['user_id'] == str(self.user.id):
            return
        await self.send(text_data=json.dumps({'type': 'read_receipt', 'user_id': event['user_id']}))
