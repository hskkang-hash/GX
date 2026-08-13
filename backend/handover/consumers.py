"""
WebSocket consumers for real-time handover notifications
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class HandoverNotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time handover notifications.
    Users can subscribe to:
    - Handover management download notifications
    - Handover notice download notifications
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = None
        self.room_groups = []
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Get user from AuthMiddlewareStack (session/cookie authentication)
        from django.contrib.auth.models import AnonymousUser
        self.user = self.scope.get('user', AnonymousUser())
        
        if self.user.is_anonymous:
            logger.warning("Anonymous user attempted to connect to handover notifications")
            await self.close()
            return
        
        self.user_id = self.user.id
        
        # Join user-specific room for their handover notifications
        user_room = f'handover_{self.user.username}'
        self.room_groups.append(user_room)
        await self.channel_layer.group_add(user_room, self.channel_name)
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Connected to handover notifications',
            'user': self.user.username,
            'subscribed_to': self.room_groups
        }))
        
        logger.info(f"User {self.user.username} connected to handover notifications")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave all room groups
        for room_group in self.room_groups:
            await self.channel_layer.group_discard(room_group, self.channel_name)
        
        logger.info(f"User {getattr(self.user, 'username', 'unknown')} disconnected from handover notifications")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'message': 'Connection alive'
                }))
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))
    
    # WebSocket message handlers
    async def handover_download_notification(self, event):
        """Send handover download notification to WebSocket
        Format giống logic cũ: {status, url, name_file, result_id, page}
        """
        # Format theo logic cũ
        response_data = {
            'status': event.get('status', ''),
            'url': event.get('url', ''),
            'name_file': event.get('name_file', ''),
            'result_id': event.get('result_id'),
            'page': event.get('page', '')
        }
        
        # Thêm các field khác để backward compatibility
        await self.send(text_data=json.dumps({
            **response_data,  # Format cũ
            'type': 'handover_download',
            'notification_type': event.get('notification_type'),
            'download_type': event.get('download_type'),
            'message': event.get('message'),
            'timestamp': event.get('timestamp'),
            'task_id': event.get('task_id'),
        }))

