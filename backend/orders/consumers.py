"""
WebSocket consumers for real-time order notifications
"""
import json
import logging
from terminals.models import Terminal
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Order, OrderStatus

logger = logging.getLogger(__name__)
User = get_user_model()

class OrderNotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time order status notifications.
    Users can subscribe to:
    - All orders (admin/manager role)
    - Orders they created
    - Orders for specific users/groups
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
            logger.warning("Anonymous user attempted to connect to order notifications")
            await self.close()
            return
        
        self.user_id = self.user.id
        
        # Join user-specific room for their orders
        user_group = await self.get_user_group()
        user_name = self.user.username
            
        user_room = user_group
        self.room_groups.append(user_room)
        await self.channel_layer.group_add(user_room, self.channel_name)
        await self.channel_layer.group_add(f'{user_group}_{user_name}', self.channel_name)
        
        # If user has admin privileges, add them to global orders room
        if await self.user_has_admin_access():
            admin_room = 'order_global'
            self.room_groups.append(admin_room)
            await self.channel_layer.group_add(admin_room, self.channel_name)
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Connected to order notifications',
            'user': self.user.username,
            'subscribed_to': self.room_groups
        }))
        
        logger.info(f"User {self.user.username} connected to order notifications")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave all room groups
        for room_group in self.room_groups:
            await self.channel_layer.group_discard(room_group, self.channel_name)
        
        logger.info(f"User {getattr(self.user, 'username', 'unknown')} disconnected from order notifications")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'request_order_status':
                await self.handle_request_order_status(data)
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
    
    async def handle_request_order_status(self, data):
        """Handle request for current order status"""
        order_id = data.get('order_id')
        if not order_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'order_id is required'
            }))
            return
        
        # Check if user has access to this order
        has_access = await self.user_has_order_access(order_id)
        if not has_access:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Access denied to this order'
            }))
            return
        
        # Get order details
        order_data = await self.get_order_details(order_id)
        if order_data:
            await self.send(text_data=json.dumps({
                'type': 'order_status',
                'order': order_data
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Order not found'
            }))
    
    # WebSocket message handlers
    async def order_status_changed(self, event):
        """Send order status change notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'order_status_changed',
            'order': event['order'],
            'old_status': event.get('old_status'),
            'new_status': event['new_status'],
            'timestamp': event['timestamp'],
            'changed_by': event.get('changed_by')
        }))
    
    async def order_created(self, event):
        """Send order creation notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'order_created',
            'order': event['order'],
            'timestamp': event['timestamp'],
            'created_by': event.get('created_by')
        }))
    
    async def order_updated(self, event):
        """Send order update notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'order_updated',
            'order': event['order'],
            'changes': event.get('changes', {}),
            'timestamp': event['timestamp'],
            'updated_by': event.get('updated_by')
        }))
    
    # Database operations
    @database_sync_to_async
    def get_user_group(self):
        """Get user's group code safely"""
        try:
            if hasattr(self.user, 'userprofilelink') and self.user.userprofilelink and self.user.userprofilelink.group:
                return self.user.userprofilelink.group.code
            return 'default'
        except Exception as e:
            logger.error(f"Error getting user group: {e}")
            return 'default'
    
    @database_sync_to_async
    def user_has_admin_access(self):
        """Check if user has admin access to all orders"""
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
    def user_has_order_access(self, order_id):
        """Check if user has access to specific order"""
        try:
            order = Order.objects.get(id=order_id)
            
            # Admin users have access to all orders
            if self.user.is_superuser or self.user.is_staff:
                return True
            
            # Users can access orders they created
            if order.created_by_id == self.user.id:
                return True
            
            # Add additional access logic here if needed
            # Example: users can access orders for their group/organization
            
            return False
        except Order.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error checking order access: {e}")
            return False
    
    @database_sync_to_async
    def get_order_details(self, order_id):
        """Get order details for notification"""
        try:
            order = Order.objects.select_related(
                'status', 'created_by', 'delivery_option', 'pickup_location', 'delivery_terminal', 'recipient_address'
            ).get(id=order_id)

            pickup_location = Terminal._base_manager.get(id=order.pickup_location_id)
            
            return {
                'status.name': order.status.name if order.status else None,
                'pickup_location.city_county_district': pickup_location.city_county_district,
                'recipient_address.city': order.recipient_address.city if order.recipient_address.city else order.recipient_address.full_address,
                'modified_on': order.modified_on.isoformat(),
                'order_code': order.order_code,
                'recipient_name': order.recipient_name,
            }
        except Order.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting order details: {e}")
            return None
        
class OrderTrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for public order tracking.
    Allows tracking orders by order_code without authentication.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_code = None
        self.room_group_name = None
    
    async def connect(self):
        """Handle WebSocket connection for order tracking"""
        # Get order_code from URL
        self.order_code = self.scope['url_route']['kwargs']['order_code']
        self.room_group_name = f'track_order_{self.order_code}'
        
        # Verify order exists
        order_exists = await self.verify_order_exists()
        if not order_exists:
            logger.warning(f"Order tracking requested for non-existent order: {self.order_code}")
            await self.close()
            return
        
        # Join order tracking room
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        # Send current order status
        await self.send_current_order_status()
        
        logger.info(f"Order tracking started for order: {self.order_code}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if self.room_group_name:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        
        logger.info(f"Order tracking disconnected for order: {self.order_code}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            print(f"🔍 [MANAGER_DEBUG] Message type: {message_type}")
            if message_type == 'request_status':
                await self.send_current_order_status()
            else:
                logger.warning(f"Unknown message type in order tracking: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received in order tracking")
        except Exception as e:
            logger.error(f"Error handling order tracking message: {e}")
    
    async def send_current_order_status(self):
        """Send current order status to client"""
        order_data = await self.get_public_order_details()
        if order_data:
            await self.send(text_data=json.dumps({
                'type': 'order_status',
                'order': order_data
            }))
    
    # WebSocket message handlers
    async def order_status_changed(self, event):
        """Send order status change notification for tracking"""
        await self.send(text_data=json.dumps({
            'type': 'order_status_changed',
            'order': event['order'],
            'old_status': event.get('old_status'),
            'new_status': event['new_status'],
            'timestamp': event['timestamp']
        }))
    
    # Database operations
    @database_sync_to_async
    def verify_order_exists(self):
        """Verify that the order exists"""
        try:
            Order.objects.get(order_code=self.order_code)
            return True
        except Order.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error verifying order exists: {e}")
            return False
    
    @database_sync_to_async
    def get_public_order_details(self):
        """Get public order details for tracking (limited information)"""
        try:
            order = Order.objects.select_related('status', 'pickup_location', 'recipient_address').get(order_code=self.order_code)
            pickup_location = Terminal._base_manager.get(id=order.pickup_location_id)
            return {
                'status.name': order.status.name if order.status else None,
                'pickup_location.city_county_district': pickup_location.city_county_district,
                'recipient_address.city': order.recipient_address.city if order.recipient_address.city else order.recipient_address.full_address,
                'modified_on': order.modified_on.isoformat(),
                'order_code': order.order_code,
                'recipient_name': order.recipient_name,
                # Note: Limited information for public tracking
            }
        except Order.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting public order details: {e}")
            return None
    
