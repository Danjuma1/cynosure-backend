"""
WebSocket consumers for real-time cause list updates.
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class CauseListConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time cause list updates.
    
    Clients can subscribe to:
    - All cause lists for a date
    - Cause lists for a specific court
    - Cause lists for a specific judge
    - A specific cause list
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope.get('user')
        self.subscribed_groups = set()
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to cause list updates'
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        for group in self.subscribed_groups:
            await self.channel_layer.group_discard(group, self.channel_name)
        
        logger.info(f"WebSocket disconnected: {close_code}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'subscribe':
                await self.handle_subscribe(data)
            elif action == 'unsubscribe':
                await self.handle_unsubscribe(data)
            elif action == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown action: {action}'
                }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def handle_subscribe(self, data):
        """Handle subscription requests."""
        subscription_type = data.get('subscription_type')
        subscription_id = data.get('id')
        
        group_name = None
        
        if subscription_type == 'date':
            group_name = f'cause_list_date_{subscription_id}'
        elif subscription_type == 'court':
            group_name = f'cause_list_court_{subscription_id}'
        elif subscription_type == 'judge':
            group_name = f'cause_list_judge_{subscription_id}'
        elif subscription_type == 'cause_list':
            group_name = f'cause_list_{subscription_id}'
        elif subscription_type == 'all':
            group_name = 'cause_list_all'
        
        if group_name:
            await self.channel_layer.group_add(group_name, self.channel_name)
            self.subscribed_groups.add(group_name)
            
            await self.send(text_data=json.dumps({
                'type': 'subscribed',
                'subscription_type': subscription_type,
                'id': subscription_id,
                'group': group_name
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Invalid subscription type: {subscription_type}'
            }))
    
    async def handle_unsubscribe(self, data):
        """Handle unsubscription requests."""
        subscription_type = data.get('subscription_type')
        subscription_id = data.get('id')
        
        group_name = None
        
        if subscription_type == 'date':
            group_name = f'cause_list_date_{subscription_id}'
        elif subscription_type == 'court':
            group_name = f'cause_list_court_{subscription_id}'
        elif subscription_type == 'judge':
            group_name = f'cause_list_judge_{subscription_id}'
        elif subscription_type == 'cause_list':
            group_name = f'cause_list_{subscription_id}'
        elif subscription_type == 'all':
            group_name = 'cause_list_all'
        
        if group_name and group_name in self.subscribed_groups:
            await self.channel_layer.group_discard(group_name, self.channel_name)
            self.subscribed_groups.remove(group_name)
            
            await self.send(text_data=json.dumps({
                'type': 'unsubscribed',
                'subscription_type': subscription_type,
                'id': subscription_id
            }))
    
    # Event handlers for group messages
    
    async def cause_list_created(self, event):
        """Handle new cause list creation."""
        await self.send(text_data=json.dumps({
            'type': 'cause_list_created',
            'cause_list': event['cause_list']
        }))
    
    async def cause_list_updated(self, event):
        """Handle cause list update."""
        await self.send(text_data=json.dumps({
            'type': 'cause_list_updated',
            'cause_list': event['cause_list'],
            'changes': event.get('changes', {})
        }))
    
    async def cause_list_status_changed(self, event):
        """Handle cause list status change."""
        await self.send(text_data=json.dumps({
            'type': 'cause_list_status_changed',
            'cause_list_id': event['cause_list_id'],
            'old_status': event['old_status'],
            'new_status': event['new_status']
        }))
    
    async def cause_list_entry_added(self, event):
        """Handle new entry added to cause list."""
        await self.send(text_data=json.dumps({
            'type': 'cause_list_entry_added',
            'cause_list_id': event['cause_list_id'],
            'entry': event['entry']
        }))
    
    async def cause_list_entry_updated(self, event):
        """Handle cause list entry update."""
        await self.send(text_data=json.dumps({
            'type': 'cause_list_entry_updated',
            'cause_list_id': event['cause_list_id'],
            'entry': event['entry']
        }))
    
    async def cause_list_adjournment(self, event):
        """Handle cause list adjournment."""
        await self.send(text_data=json.dumps({
            'type': 'cause_list_adjournment',
            'cause_list_id': event['cause_list_id'],
            'reason': event.get('reason', ''),
            'new_date': event.get('new_date')
        }))
    
    async def cause_list_not_sitting(self, event):
        """Handle not sitting notice."""
        await self.send(text_data=json.dumps({
            'type': 'cause_list_not_sitting',
            'cause_list_id': event['cause_list_id'],
            'judge_name': event.get('judge_name', ''),
            'reason': event.get('reason', '')
        }))
    
    async def cause_list_time_changed(self, event):
        """Handle time change notification."""
        await self.send(text_data=json.dumps({
            'type': 'cause_list_time_changed',
            'cause_list_id': event['cause_list_id'],
            'old_time': event.get('old_time'),
            'new_time': event.get('new_time')
        }))
    
    async def cause_list_courtroom_changed(self, event):
        """Handle courtroom change notification."""
        await self.send(text_data=json.dumps({
            'type': 'cause_list_courtroom_changed',
            'cause_list_id': event['cause_list_id'],
            'old_courtroom': event.get('old_courtroom'),
            'new_courtroom': event.get('new_courtroom')
        }))
