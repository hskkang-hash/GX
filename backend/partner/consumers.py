"""
WebSocket consumers for real-time partner callback notifications
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class PartnerCallbackNotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time partner callback notifications.
    Users can subscribe to:
    - All partner callbacks (admin/manager role)
    - Partner callbacks for their group
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
            logger.warning("Anonymous user attempted to connect to partner callback notifications")
            await self.close()
            return
        
        self.user_id = self.user.id
        
        # Join user-specific room for their group's partner callbacks
        user_group = await self.get_user_group()
        if user_group:
            group_room = f'partner_callbacks_{user_group}'
            self.room_groups.append(group_room)
            await self.channel_layer.group_add(group_room, self.channel_name)
        
        # If user has admin privileges, add them to global partner callbacks room
        has_admin = await self.user_has_admin_access()
        logger.info(f"🔍 [DEBUG] User {self.user.username} admin check: {has_admin}")
        logger.info(f"🔍 [DEBUG] is_superuser: {self.user.is_superuser}, is_staff: {self.user.is_staff}")
        
        if has_admin:
            admin_room = 'partner_callbacks_global'
            self.room_groups.append(admin_room)
            await self.channel_layer.group_add(admin_room, self.channel_name)
            logger.info(f"✅ [DEBUG] Added {self.user.username} to global room")
        else:
            logger.info(f"❌ [DEBUG] {self.user.username} not added to global room")
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Connected to partner callback notifications',
            'user': self.user.username,
            'subscribed_to': self.room_groups
        }))
        
        logger.info(f"User {self.user.username} connected to partner callback notifications")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave all room groups
        for room_group in self.room_groups:
            await self.channel_layer.group_discard(room_group, self.channel_name)
        
        logger.info(f"User {getattr(self.user, 'username', 'unknown')} disconnected from partner callback notifications")
    
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
    
    # WebSocket message handlers for different notification types
    async def delivery_status_callback(self, event):
        """Send delivery status callback notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'delivery_status_callback',
            'timestamp': event.get('timestamp'),
            'callback_type': 'DeliveryStatusCallback',
            'data': event['data'],
            'partner_info': event.get('partner_info', {}),
            'success': event.get('success', True),
            'message': event.get('message', 'Delivery status callback received')
        }))
    
    async def drone_base_station_callback(self, event):
        """Send drone base station callback notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'drone_base_station_callback',
            'timestamp': event.get('timestamp'),
            'callback_type': 'DroneBaseStation',
            'data': event['data'],
            'partner_info': event.get('partner_info', {}),
            'success': event.get('success', True),
            'message': event.get('message', 'Drone base station callback received')
        }))
    
    async def drone_user_notice_callback(self, event):
        """Send drone user notice callback notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'drone_user_notice_callback',
            'timestamp': event.get('timestamp'),
            'callback_type': 'DroneUserNotice',
            'data': event['data'],
            'partner_info': event.get('partner_info', {}),
            'success': event.get('success', True),
            'message': event.get('message', 'Drone user notice callback received')
        }))
    
    async def partner_callback_error(self, event):
        """Send partner callback error notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'partner_callback_error',
            'timestamp': event.get('timestamp'),
            'callback_type': event.get('callback_type', 'unknown'),
            'error': event.get('error', 'Unknown error'),
            'data': event.get('data', {}),
            'message': event.get('message', 'Partner callback error occurred')
        }))
    
    # Helper methods
    @database_sync_to_async
    def get_user_group(self):
        """Get user's group ID"""
        try:
            if hasattr(self.user, 'userprofilelink') and self.user.userprofilelink.group:
                return str(self.user.userprofilelink.group.id)
            return None
        except Exception as e:
            logger.error(f"Error getting user group: {e}")
            return None
    
    @database_sync_to_async
    def user_has_admin_access(self):
        """Check if user has admin access for global notifications"""
        try:
            return (
                self.user.is_superuser or 
                self.user.is_staff or
                (hasattr(self.user, 'userprofilelink') and 
                 self.user.roles.filter(id=1).exists())
            )
        except Exception as e:
            logger.error(f"Error checking admin access: {e}")
            return False
