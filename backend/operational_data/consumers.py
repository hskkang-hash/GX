"""
WebSocket consumers for real-time operational data notifications
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

class OperationalDataNotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time operational data notifications.
    Users can subscribe to:
    - Video upload progress notifications
    - Log upload progress notifications
    - File processing status updates
    - Error notifications for operational data operations
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
            logger.warning("Anonymous user attempted to connect to operational data notifications")
            await self.close()
            return
        
        self.user_id = self.user.id
        
        # Join user-specific room for their operational data notifications
        user_room = f'operational_data_{self.user.username}'
        self.room_groups.append(user_room)
        await self.channel_layer.group_add(user_room, self.channel_name)
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Connected to operational data notifications',
            'user': self.user.username,
            'subscribed_to': self.room_groups
        }))
        
        logger.info(f"User {self.user.username} connected to operational data notifications")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave all room groups
        for room_group in self.room_groups:
            await self.channel_layer.group_discard(room_group, self.channel_name)
        
        logger.info(f"User {getattr(self.user, 'username', 'unknown')} disconnected from operational data notifications")
    
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
            elif message_type == 'subscribe_to_order_item':
                await self.handle_subscribe_to_order_item(data)
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
    
    async def handle_subscribe_to_order_item(self, data):
        """Handle subscription to specific order item notifications"""
        order_item_id = data.get('order_item_id')
        if not order_item_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'order_item_id is required'
            }))
            return
        
        # Check if user has access to this order item
        has_access = await self.user_has_order_item_access(order_item_id)
        if not has_access:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Access denied to this order item'
            }))
            return
        
        # Subscribe to order item specific notifications
        order_item_room = f'operational_data_order_item_{order_item_id}'
        if order_item_room not in self.room_groups:
            self.room_groups.append(order_item_room)
            await self.channel_layer.group_add(order_item_room, self.channel_name)
            
            await self.send(text_data=json.dumps({
                'type': 'subscribed',
                'message': f'Subscribed to order item {order_item_id} notifications',
                'order_item_id': order_item_id
            }))
    
    # WebSocket message handlers
    async def operational_video_upload_notification(self, event):
        """Send operational video upload notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'operational_video_upload',
            'notification_type': event['notification_type'],
            'order_item_id': event['order_item_id'],
            'device_type': event['device_type'],
            'status': event['status'],
            'message': event['message'],
            'timestamp': event['timestamp'],
            'task_id': event['task_id'],
            'data': event.get('data', {})
        }))
    
    async def operational_log_upload_notification(self, event):
        """Send operational log upload notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'operational_log_upload',
            'notification_type': event['notification_type'],
            'order_item_id': event['order_item_id'],
            'device_type': event['device_type'],
            'status': event['status'],
            'message': event['message'],
            'timestamp': event['timestamp'],
            'data': event.get('data', {})
        }))
    
    async def operational_data_processing_notification(self, event):
        """Send operational data processing notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'operational_data_processing',
            'notification_type': event['notification_type'],
            'order_item_id': event['order_item_id'],
            'operation_type': event['operation_type'],
            'status': event['status'],
            'message': event['message'],
            'timestamp': event['timestamp'],
            'data': event.get('data', {})
        }))
    
    async def operational_data_error_notification(self, event):
        """Send operational data error notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'operational_data_error',
            'notification_type': event['notification_type'],
            'order_item_id': event['order_item_id'],
            'error_type': event['error_type'],
            'message': event['message'],
            'timestamp': event['timestamp'],
            'data': event.get('data', {})
        }))
    
    async def operational_data_download_notification(self, event):
        """Send operational data download notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'operational_data_download',
            'notification_type': event['notification_type'],
            'order_item_ids': event['order_item_ids'],
            'status': event['status'],
            'message': event['message'],
            'timestamp': event['timestamp'],
            'data': event.get('data', {})
        }))
    
    async def operational_log_download_notification(self, event):
        """Send operational log download notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'operational_log_download',
            'notification_type': event['notification_type'],
            'order_item_id': event['order_item_id'],
            'device_type': event['device_type'],
            'status': event['status'],
            'message': event['message'],
            'timestamp': event['timestamp'],
            'data': event.get('data', {})
        }))
    
    @database_sync_to_async
    def user_has_admin_access(self):
        """Check if user has admin access to all operational data"""
        try:
            # Check if user is superuser or staff
            if self.user.is_superuser or self.user.is_staff:
                return True
            
            # Add custom permission checks here if needed
            # Example: check if user has specific group membership
            # return self.user.groups.filter(name__in=['admin', 'manager']).exists()
            
            return False
        except Exception as e:
            logger.error(f"Error checking admin access: {e}")
            return False
    
    @database_sync_to_async
    def user_has_order_item_access(self, order_item_id):
        """Check if user has access to specific order item"""
        try:
            from orders.models import OrderItem
            
            order_item = OrderItem.objects.select_related('order').get(id=order_item_id)
            
            # Admin users have access to all order items
            if self.user.is_superuser or self.user.is_staff:
                return True
            
            # Users can access order items for orders they created
            if order_item.order.created_by_id == self.user.id:
                return True
            
            # Add additional access logic here if needed
            # Example: users can access order items for their group/organization
            
            return False
        except Exception as e:
            logger.error(f"Error checking order item access: {e}")
            return False
