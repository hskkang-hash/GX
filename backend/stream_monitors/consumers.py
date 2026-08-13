"""
WebSocket consumers for real-time drawing functionality and external data streams
"""
import asyncio
import json
import logging
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import DrawingSession, DrawingElement, DrawingParticipant, StreamMonitor


logger = logging.getLogger(__name__)
User = get_user_model()

class AllDrawingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for global real-time drawing collaboration.
    All users draw on the same shared canvas without session isolation.
    """
    
    # Throttle cursor updates: min interval in seconds between cursor broadcasts
    CURSOR_THROTTLE_INTERVAL = 0.05  # 50ms = max 20 updates/sec per user
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_group_name = 'global_drawing'
        self._last_cursor_broadcast = 0  # Timestamp of last cursor broadcast
        
    async def connect(self):
        """Handle WebSocket connection for global drawing"""
        from django.contrib.auth.models import AnonymousUser
        self.user = self.scope.get('user', AnonymousUser())
        
        # Join global drawing room
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Connected to global drawing canvas',
            'user': getattr(self.user, 'username', 'anonymous')
        }))
        
        logger.info(f"User connected to global drawing canvas")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"User disconnected from global drawing canvas")
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")
            
            # Priority messages are awaited directly for reliable delivery
            # Low-priority messages (cursor_position) are fire-and-forget
            if message_type in ('draw_element', 'clear_all'):
                await self.dispatch_message(data)
            else:
                asyncio.create_task(self.dispatch_message(data))
        except Exception as e:
            logger.exception(f"Receive error: {e}")

    async def dispatch_message(self, data):
        message_type = data.get("type")
        if message_type == "draw_element":
            await self.handle_draw_element(data)
        elif message_type == "clear_all":
            await self.handle_clear_all(data)
        elif message_type == "cursor_position":
            await self.handle_cursor_position(data)
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def handle_draw_element(self, data):
        """Handle new drawing element - broadcast directly"""
        element_data = data.get('element_data', {})
        element_type = data.get('element_type', 'line')
        
        # Broadcast drawing element directly to all users
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'element_added',
                'element': {
                    'type': element_type,
                    'data': element_data,
                    'created_by': getattr(self.user, 'username', 'anonymous'),
                }
            }
        )
    
    async def handle_clear_all(self, data):
        """Handle clearing all elements - broadcast directly"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'drawing_cleared',
                'cleared_by': getattr(self.user, 'username', 'anonymous'),
            }
        )
    
    async def handle_cursor_position(self, data):
        """Handle cursor position updates with throttling"""
        import time
        
        # Throttle cursor broadcasts to prevent message flooding
        current_time = time.time()
        if current_time - self._last_cursor_broadcast < self.CURSOR_THROTTLE_INTERVAL:
            return  # Skip this update, too soon after last one
        
        self._last_cursor_broadcast = current_time
        cursor_data = data.get('cursor_data', {})
        
        # Broadcast cursor position to other users
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'cursor_position_updated',
                'user': getattr(self.user, 'username', 'anonymous'),
                'cursor_data': cursor_data,
                'sender_channel': self.channel_name,
            }
        )
    
    # WebSocket message handlers
    async def element_added(self, event):
        """Send drawing element added event to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'element_added',
            'element': event['element']
        }))
    
    async def drawing_cleared(self, event):
        """Send drawing cleared event to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'drawing_cleared',
            'cleared_by': event['cleared_by']
        }))
    
    async def cursor_position_updated(self, event):
        """Send cursor position update to WebSocket (except sender)"""
        if event.get('sender_channel') != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'cursor_position',
                'user': event['user'],
                'cursor_data': event['cursor_data']
            }))

class DrawingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time drawing collaboration.
    
    This consumer provides real-time drawing without persistence:
    - Drawing elements are broadcast directly to all connected users
    - No database operations for drawing elements (performance optimized)
    - Elements only exist during the active session
    - New users joining see a clean canvas
    - Session and participant management still uses database
    """
    
    # Throttle cursor updates: min interval in seconds between cursor broadcasts
    CURSOR_THROTTLE_INTERVAL = 0.05  # 50ms = max 20 updates/sec per user
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handle_message_type = {
            'draw_element': self.handle_draw_element,
            'clear_all': self.handle_clear_all,
            'cursor_position': self.handle_cursor_position,
            'request_drawing': self.handle_request_drawing,
            'send_drawings': self.handle_send_drawings,
            'request_participants': self.handle_request_participants,
        }
        self._last_cursor_broadcast = 0  # Timestamp of last cursor broadcast
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Get session ID from URL
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'drawing_session_{self.session_id}'
        
        # Get user from AuthMiddlewareStack (session/cookie authentication)
        from django.contrib.auth.models import AnonymousUser
        self.user = self.scope.get('user', AnonymousUser())
        
        if self.user.is_anonymous:
            logger.warning("Anonymous user attempted to connect to drawing session")
            # For testing, you can allow anonymous users, or reject them:
            # await self.close()
            # return
            # For now, let's allow anonymous users for testing
            pass
        
        # Verify session exists
        session_exists = await self.verify_session_access()
        if not session_exists:
            logger.warning(f"Session {self.session_id} not found")
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept connection
        await self.accept()
        
        # Add user as participant
        await self.add_participant()
        
        # Send current drawing state to the new user
        await self.send_current_drawing_state()
        
        # Notify other users about new participant
        await self.notify_participant_joined()
        
        logger.info(f"User {self.user.username if hasattr(self.user, 'username') else 'anonymous'} connected to drawing session {self.session_id}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'room_group_name'):
            # Remove user from participants
            await self.remove_participant()
            
            # Notify other users about participant leaving
            await self.notify_participant_left()
            
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
            logger.info(f"User disconnected from drawing session {self.session_id}")
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            handler = self.handle_message_type.get(message_type)
            if handler:
                # Priority messages (draw_element, clear_all) are awaited directly
                # to ensure reliable delivery. Low-priority messages (cursor_position)
                # are fire-and-forget for better performance.
                if message_type in ('draw_element', 'clear_all', 'send_drawings'):
                    await self.safe_handler(handler, data)
                else:
                    asyncio.create_task(self.safe_handler(handler, data))
            else:
                logger.warning(f"Unknown message type: {message_type}")
        except Exception as e:
            logger.exception(f"Receive error: {e}")
            await self.send(json.dumps({'type': 'error', 'message': str(e)}))

    async def safe_handler(self, handler, data):
        try:
            await handler(data)
        except Exception as e:
            logger.exception(f"Error in handler {handler.__name__}: {e}")

    
    async def handle_draw_element(self, data):
        """Handle new drawing element - broadcast directly without saving"""
        element_data = data.get('element_data', {})
        element_type = data.get('element_type', 'line')
        
        # Broadcast drawing element directly to all users in the session
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'element_added',
                'element': {
                    'type': element_type,
                    'data': element_data,
                    'created_by': getattr(self.user, 'username', 'anonymous'),
                }
            }
        )
    
    async def handle_clear_all(self, data):
        """Handle clearing all elements - broadcast directly"""
        # Broadcast clear to all users
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'drawing_cleared',
                'cleared_by': getattr(self.user, 'username', 'anonymous'),
            }
        )
    
    async def handle_cursor_position(self, data):
        """Handle cursor position updates with throttling"""
        import time
        
        # Throttle cursor broadcasts to prevent message flooding
        current_time = time.time()
        if current_time - self._last_cursor_broadcast < self.CURSOR_THROTTLE_INTERVAL:
            return  # Skip this update, too soon after last one
        
        self._last_cursor_broadcast = current_time
        cursor_data = data.get('cursor_data', {})
        
        # Broadcast cursor position to other users (not self)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'cursor_position_updated',
                'user': getattr(self.user, 'username', 'anonymous'),
                'cursor_data': cursor_data,
                'sender_channel': self.channel_name,
            }
        )
    
    async def handle_request_drawing(self, data):
        """Handle request for current drawing state from a user"""
        # Broadcast to all users asking them to send their drawings
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'drawing_requested',
                'requested_by': getattr(self.user, 'username', 'anonymous'),
                'requester_channel': self.channel_name,
            }
        )
    
    async def handle_send_drawings(self, data):
        """Handle sending drawing elements to requesting user"""
        drawings = data.get('drawings', [])
        target_channel = data.get('target_channel')
        
        if target_channel:
            # Send drawings directly to the specific channel that requested them
            await self.channel_layer.send(
                target_channel,
                {
                    'type': 'drawings_received',
                    'drawings': drawings,
                    'sent_by': getattr(self.user, 'username', 'anonymous'),
                }
            )
    
    async def handle_request_participants(self, data):
        """Handle request for current participants list"""
        participants_data = await self.get_detailed_participants()
        
        # Send participants list back to the requesting user
        await self.send(text_data=json.dumps({
            'type': 'participants_list',
            'participants': participants_data
        }))
    
    # WebSocket message handlers
    async def element_added(self, event):
        """Send drawing element added event to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'element_added',
            'element': event['element']
        }))
    

    
    async def drawing_cleared(self, event):
        """Send drawing cleared event to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'drawing_cleared',
            'cleared_by': event['cleared_by']
        }))
    
    async def cursor_position_updated(self, event):
        """Send cursor position update to WebSocket (except sender)"""
        # Don't send to the sender
        if event['sender_channel'] != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'cursor_position',
                'user': event['user'],
                'cursor_data': event['cursor_data']
            }))
    
    async def participant_joined(self, event):
        """Send participant joined event to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'participant_joined',
            'user': event['user'],
            'participant': event.get('participant'),
            'participants': event['participants']
        }))
    
    async def participant_left(self, event):
        """Send participant left event to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'participant_left',
            'user': event['user'],
            'participants': event['participants']
        }))
    
    async def drawing_requested(self, event):
        """Send drawing request event to WebSocket (except requester)"""
        # Don't send to the requester
        if event['requester_channel'] != self.channel_name:
            await self.send(text_data=json.dumps({
                'type': 'drawing_request',
                'requested_by': event['requested_by'],
                'requester_channel': event['requester_channel']
            }))
    
    async def drawings_received(self, event):
        """Send received drawings to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'drawings_sync',
            'drawings': event['drawings'],
            'sent_by': event['sent_by']
        }))
    
    # Database operations
    
    @database_sync_to_async
    def verify_session_access(self):
        """Verify that the session exists"""
        try:
            session = DrawingSession.objects.get(id=self.session_id, is_active=True)
            return True
        except DrawingSession.DoesNotExist:
            return False
    
    @database_sync_to_async
    def add_participant(self):
        """Add user as participant in the session"""
        try:
            session = DrawingSession.objects.get(id=self.session_id)
            
            # Handle anonymous users
            if self.user.is_anonymous:
                # For anonymous users, we can skip participant tracking
                # or create a temporary participant record
                logger.info("Anonymous user connected - skipping participant tracking")
                return None
            
            participant, created = DrawingParticipant.objects.get_or_create(
                session=session,
                user=self.user,
                defaults={'is_online': True}
            )
            if not created:
                participant.is_online = True
                participant.save()
            return participant
        except Exception as e:
            logger.error(f"Error adding participant: {e}")
            return None
    
    @database_sync_to_async
    def remove_participant(self):
        """Remove user from participants or mark as offline"""
        try:
            if self.user.is_anonymous:
                return
                
            session = DrawingSession.objects.get(id=self.session_id)
            participant = DrawingParticipant.objects.get(session=session, user=self.user)
            participant.is_online = False
            participant.save()
        except Exception as e:
            logger.error(f"Error removing participant: {e}")
    

    
    async def send_current_drawing_state(self):
        """Send current drawing state to the newly connected user"""
        participants_data = await self.get_detailed_participants()
        
        await self.send(text_data=json.dumps({
            'type': 'initial_state',
            'elements': [],  # No persistent elements in real-time only mode
            'participants': participants_data
        }))
        
        # Also send a participants list message for consistency
        await self.send(text_data=json.dumps({
            'type': 'participants_list',
            'participants': participants_data
        }))
    

    
    @database_sync_to_async
    def get_session_participants(self):
        """Get all online participants in the session"""
        try:
            participants = DrawingParticipant.objects.filter(
                session_id=self.session_id,
                is_online=True
            ).select_related('user')
            
            return [getattr(participant.user, 'username', 'anonymous') for participant in participants]
        except Exception as e:
            logger.error(f"Error getting session participants: {e}")
            return []
    
    @database_sync_to_async
    def get_detailed_participants(self):
        """Get detailed participant information"""
        try:
            participants = DrawingParticipant.objects.filter(
                session_id=self.session_id,
                is_online=True
            ).select_related('user')
            
            participants_data = []
            for participant in participants:
                participants_data.append({
                    'user': getattr(participant.user, 'username', f'anonymous_{participant.id}'),
                    'joined_at': participant.joined_at.isoformat() if hasattr(participant, 'joined_at') and participant.joined_at else None,
                    'last_activity': participant.last_activity.isoformat() if hasattr(participant, 'last_activity') and participant.last_activity else None,
                    'is_online': participant.is_online
                })
            
            # If no participants found and we have anonymous users, add a dummy entry
            if not participants_data:
                participants_data = [{
                    'user': 'anonymous_user',
                    'joined_at': None,
                    'last_activity': None,
                    'is_online': True
                }]
            
            return participants_data
        except Exception as e:
            logger.error(f"Error getting detailed participants: {e}")
            # Return at least one anonymous participant as fallback
            return [{
                'user': 'anonymous_user',
                'joined_at': None,
                'last_activity': None,
                'is_online': True
            }]
    
    async def notify_participant_joined(self):
        """Notify other users about new participant"""
        participants_data = await self.get_detailed_participants()
        current_participant = await self.get_current_participant_data()
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'participant_joined',
                'user': getattr(self.user, 'username', 'anonymous'),
                'participant': current_participant,
                'participants': participants_data,
            }
        )
    
    async def notify_participant_left(self):
        """Notify other users about participant leaving"""
        participants_data = await self.get_detailed_participants()
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'participant_left',
                'user': getattr(self.user, 'username', 'anonymous'),
                'participants': participants_data,
            }
        )
    
    @database_sync_to_async
    def get_current_participant_data(self):
        """Get current user's participant data"""
        try:
            if self.user.is_anonymous:
                return {
                    'user': 'anonymous',
                    'joined_at': None,
                    'last_activity': None,
                    'is_online': True
                }
            
            participant = DrawingParticipant.objects.get(
                session_id=self.session_id,
                user=self.user
            )
            
            return {
                'user': getattr(participant.user, 'username', 'anonymous'),
                'joined_at': participant.joined_at.isoformat() if participant.joined_at else None,
                'last_activity': participant.last_activity.isoformat() if participant.last_activity else None,
                'is_online': participant.is_online
            }
        except Exception as e:
            logger.error(f"Error getting current participant data: {e}")
            return {
                'user': getattr(self.user, 'username', 'anonymous'),
                'joined_at': None,
                'last_activity': None,
                'is_online': True
            }


class ExternalDataStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for receiving external data streams
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = None
        self.room_groups = []
        
    async def connect(self):
        """Handle WebSocket connection for external data streams"""
        # Get user from AuthMiddlewareStack (session/cookie authentication)
        from django.contrib.auth.models import AnonymousUser
        self.user = self.scope.get('user', AnonymousUser())
        
        if self.user.is_anonymous:
            logger.warning("Anonymous user attempted to connect to external data stream")
            await self.close()
            return
        
        self.user_id = self.user.id
        
        # Check if user has permission to access external data streams
        has_permission = await self.user_has_stream_access()
        if not has_permission:
            logger.warning(f"User {self.user.username} denied access to external data stream")
            await self.close(code=4003)  # Custom code for permission denied
            return
        
        # Join user-specific room for their group's stream data
        user_group = await self.get_user_group()
        user_name = self.user.username
        
        if user_group:
            # Join group room (like orders: user_room = user_group)
            group_room = f'external_data_stream_{user_group}'
            self.room_groups.append(group_room)
            await self.channel_layer.group_add(group_room, self.channel_name)
            
            # Join user-specific room (like orders: f'{user_group}_{user_name}')
            user_specific_room = f'external_data_stream_{user_group}_{user_name}'
            self.room_groups.append(user_specific_room)
            await self.channel_layer.group_add(user_specific_room, self.channel_name)
        
        # If user has admin privileges, add them to global stream room
        has_admin = await self.user_has_admin_access()
        logger.info(f"🔍 [DEBUG] User {self.user.username} admin check: {has_admin}")
        logger.info(f"🔍 [DEBUG] is_superuser: {self.user.is_superuser}, is_staff: {self.user.is_staff}")
        
        if has_admin:
            admin_room = 'external_data_stream_global'
            self.room_groups.append(admin_room)
            await self.channel_layer.group_add(admin_room, self.channel_name)
            logger.info(f"✅ [DEBUG] Added {self.user.username} to global stream room")
        else:
            logger.info(f"❌ [DEBUG] {self.user.username} not added to global stream room")
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Connected to external data stream handler',
            'user': self.user.username,
            'subscribed_to': self.room_groups,
            'timestamp': datetime.now().isoformat()
        }))
        
        logger.info(f"User {self.user.username} connected to external data stream handler")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave all rooms
        for room_group in self.room_groups:
            await self.channel_layer.group_discard(room_group, self.channel_name)
        
        logger.info(f"User {getattr(self.user, 'username', 'unknown')} disconnected from external data stream notifications")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            logger.info(f"Received message type: {message_type}, data: {data}")
            
            if message_type == 'external_data':
                await self.handle_external_data(data)
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
    
    async def handle_external_data(self, data):
        """Handle external data messages"""
        logger.info(f"Processing external data: {data}")
        
        # Send acknowledgment back to client
        await self.send(text_data=json.dumps({
            'type': 'external_data_received',
            'message': 'External data received successfully',
            'timestamp': datetime.now().isoformat()
        }))
    
    # Helper methods
    @database_sync_to_async
    def get_user_group(self):
        """Get user's group ID with proper connection handling"""
        try:
            from django.db import connection
            
            # 🔐 FIX: Ensure fresh database connection
            if connection.connection and connection.connection.closed:
                connection.close()
            
            if hasattr(self.user, 'userprofilelink') and self.user.userprofilelink.group:
                return str(self.user.userprofilelink.group.id)
            return None
        except Exception as e:
            logger.error(f"Error getting user group: {e}")
            # 🔐 FIX: Close problematic connection
            try:
                from django.db import connection
                connection.close()
            except Exception:
                pass
            return None
    
    @database_sync_to_async
    def user_has_admin_access(self):
        """Check if user has admin access for global stream notifications with connection handling"""
        try:
            from django.db import connection
            
            # 🔐 FIX: Ensure fresh database connection
            if connection.connection and connection.connection.closed:
                connection.close()
            
            return (
                self.user.is_superuser or 
                any(role.code == 'superuser' for role in self.user.roles.all()) or
                self.user.is_staff or
                (hasattr(self.user, 'userprofilelink') and 
                 self.user.roles.all().values_list('role_name', flat=True) in ['superuser'])
            )
        except Exception as e:
            logger.error(f"Error checking admin access: {e}")
            # 🔐 FIX: Close problematic connection
            try:
                from django.db import connection
                connection.close()
            except Exception:
                pass
            return False
    
    @database_sync_to_async
    def user_has_stream_access(self):
        """Check if user has permission to access external data streams"""
        try:
            from django.db import connection
            
           
            if connection.connection and connection.connection.closed:
                connection.close()
            
            # Allow superuser/staff access
            if self.user.is_superuser or any(role.code == 'superuser' for role in self.user.roles.all()) or self.user.is_staff:
                return True
            
            # Check specific stream monitor permissions
            # You can customize this logic based on your permission system
            if hasattr(self.user, 'userprofilelink'):
                # Check if user has stream monitor role or permission
                user_roles = self.user.roles.all().values_list('role_name', flat=True)
                if any(role in ['stream_monitor', 'stream_admin', 'monitor_operator'] for role in user_roles):
                    return True
            
            # Default: deny access
            return False
        except Exception as e:
            logger.error(f"Error checking stream access: {e}")
            # 🔐 FIX: Close problematic connection
            try:
                from django.db import connection
                connection.close()
            except Exception:
                pass
            return False