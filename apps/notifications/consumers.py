"""
WebSocket consumer for real-time notifications.
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user notifications.
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope.get('user')
        
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        # Join user-specific group
        self.group_name = f'notifications_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to notification stream'
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
    
    async def receive(self, text_data):
        """Handle incoming messages."""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            elif action == 'mark_read':
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_read(notification_id)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    async def mark_notification_read(self, notification_id):
        """Mark a notification as read."""
        from channels.db import database_sync_to_async
        from .models import Notification
        
        @database_sync_to_async
        def mark_read():
            try:
                notif = Notification.objects.get(id=notification_id, user=self.user)
                notif.mark_read()
                return True
            except Notification.DoesNotExist:
                return False
        
        success = await mark_read()
        await self.send(text_data=json.dumps({
            'type': 'notification_marked_read',
            'notification_id': notification_id,
            'success': success
        }))
    
    # Event handlers
    
    async def new_notification(self, event):
        """Handle new notification event."""
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification']
        }))
    
    async def notification_count_update(self, event):
        """Handle notification count update."""
        await self.send(text_data=json.dumps({
            'type': 'count_update',
            'unread_count': event['unread_count']
        }))
