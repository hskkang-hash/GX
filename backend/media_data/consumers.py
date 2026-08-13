"""
WebSocket consumers for real-time media download notifications
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class MediaDownloadConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time media download notifications.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = None
        self.room_groups = []
    
    async def connect(self):
        """Handle WebSocket connection"""
        from django.contrib.auth.models import AnonymousUser
        self.user = self.scope.get('user', AnonymousUser())
        
        if self.user.is_anonymous:
            logger.warning("Anonymous user attempted to connect to media download notifications")
            await self.close()
            return
        
        self.user_id = self.user.id
        
        # Join user-specific room for download notifications
        user_room = f'media_download_{self.user.username}'
        self.room_groups.append(user_room)
        await self.channel_layer.group_add(user_room, self.channel_name)
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Connected to media download notifications',
            'user': self.user.username,
            'subscribed_to': self.room_groups
        }))
        
        logger.info(f"User {self.user.username} connected to media download notifications")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave all room groups
        for room_group in self.room_groups:
            await self.channel_layer.group_discard(room_group, self.channel_name)
        
        logger.info(f"User {getattr(self.user, 'username', 'unknown')} disconnected from media download notifications")
    
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
    async def media_download_notification(self, event):
        """Send media download notification to WebSocket
        Format: {status, url, name_file, result_id, message}
        """
        await self.send(text_data=json.dumps({
            'type': 'media_download',
            'status': event.get('status', ''),  # 'PENDING', 'PROCESSING', 'DONE', 'FAILED'
            'url': event.get('url', ''),
            'name_file': event.get('name_file', ''),
            'result_id': event.get('result_id'),
            'message': event.get('message', ''),
            'task_id': event.get('task_id'),
            'timestamp': event.get('timestamp'),
            'progress': event.get('progress', 0),
        }))


class MediaDetectConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time media detection notifications.
    Supports both authenticated users and anonymous connections for testing.
    For anonymous users, use ?username=<username> query param to subscribe to a specific user's notifications.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = None
        self.room_groups = []
        self.username = None
        self.group_code = None
    async def connect(self):
        """Handle WebSocket connection"""
        from django.contrib.auth.models import AnonymousUser
        from urllib.parse import parse_qs
        self.user = self.scope.get('user', AnonymousUser())
        
        # Parse query string for username parameter (for testing)
        query_string = self.scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        
        if self.user.is_anonymous:
            # Allow anonymous users for testing - get username from query param
            query_username = query_params.get('username', [None])[0]
            if query_username:
                self.username = query_username
                logger.info(f"Anonymous user connecting with username param: {query_username}")
            else:
                # Default to 'test_user' for testing if no username provided
                self.username = 'test_user'
                logger.warning("Anonymous user connected to media detect notifications (using test_user)")
        else:
            self.user_id = self.user.id
            self.username = self.user.username
            self.group_code = await self.get_group_code()
        # Join user-specific room for detect notifications
        if self.group_code:
            user_room = f'media_detect_{self.group_code}'
            self.room_groups.append(user_room)
            await self.channel_layer.group_add(user_room, self.channel_name)
   
        
        # Also join a global room for broadcast notifications (admin only)
        if await self.user_has_admin_access():
            global_room = 'media_detect_global'
            self.room_groups.append(global_room)
            await self.channel_layer.group_add(global_room, self.channel_name)
        
        await self.accept()
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Connected to media detect notifications',
            'user': self.username,
            'group_code': self.group_code,
            'subscribed_to': self.room_groups
        }))
        
        logger.info(f"User {self.username} connected to media detect notifications")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave all room groups
        for room_group in self.room_groups:
            await self.channel_layer.group_discard(room_group, self.channel_name)
        
        logger.info(f"User {self.username or 'unknown'} disconnected from media detect notifications")
    
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
    async def media_detect_notification(self, event):
        """Send media detect notification to WebSocket
        Format: {msg, data}
        """
        await self.send(text_data=json.dumps({
            'type': 'media_detect',
            'msg': event.get('msg', ''),
            'data': event.get('data', []),
            'timestamp': event.get('timestamp'),
        }))


    @database_sync_to_async
    def get_group_code(self):
        if hasattr(self.user, 'userprofilelink') and self.user.userprofilelink and self.user.userprofilelink.group:
            return self.user.userprofilelink.group.code
        return None
    
    @database_sync_to_async
    def user_has_admin_access(self):
        """Only admins should subscribe to *_global rooms."""
        try:
            return bool(getattr(self.user, "is_superuser", False) or getattr(self.user, "is_staff", False))
        except Exception:
            return False




class MediaUploadDetectionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for upload-detection notifications (separate from detect callback).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = None
        self.room_groups = []
        self.username = None
        self.group_code = None

    async def connect(self):
        """Handle WebSocket connection"""
        from django.contrib.auth.models import AnonymousUser
        from urllib.parse import parse_qs
        self.user = self.scope.get('user', AnonymousUser())

        # Parse query string for username parameter (for testing)
        query_string = self.scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)

        if self.user.is_anonymous:
            query_username = query_params.get('username', [None])[0]
            if query_username:
                self.username = query_username
                logger.info(f"Anonymous user connecting with username param: {query_username}")
            else:
                self.username = 'test_user'
                logger.warning("Anonymous user connected to upload-detection notifications (using test_user)")
        else:
            self.user_id = self.user.id
            self.username = self.user.username
            self.group_code = await self.get_group_code()

        if self.group_code:
            user_room = f'media_upload_detection_{self.group_code}'
            self.room_groups.append(user_room)
            await self.channel_layer.group_add(user_room, self.channel_name)

        # Global broadcast room (admin only)
        if await self.user_has_admin_access():
            global_room = 'media_upload_detection_global'
            self.room_groups.append(global_room)
            await self.channel_layer.group_add(global_room, self.channel_name)

        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Connected to upload-detection notifications',
            'user': self.username,
            'group_code': self.group_code,
            'subscribed_to': self.room_groups
        }))

        logger.info(f"User {self.username} connected to upload-detection notifications")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        for room_group in self.room_groups:
            await self.channel_layer.group_discard(room_group, self.channel_name)

        logger.info(f"User {self.username or 'unknown'} disconnected from upload-detection notifications")

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

    async def media_upload_detection_notification(self, event):
        """Send upload-detection notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'media_upload_detection',
            'msg': event.get('msg', ''),
            'data': event.get('data', {}),
            'timestamp': event.get('timestamp'),
        }))

    @database_sync_to_async
    def get_group_code(self):
        if hasattr(self.user, 'userprofilelink') and self.user.userprofilelink and self.user.userprofilelink.group:
            return self.user.userprofilelink.group.code
        return None
    
    @database_sync_to_async
    def user_has_admin_access(self):
        """Only admins should subscribe to *_global rooms."""
        try:
            return bool(getattr(self.user, "is_superuser", False) or getattr(self.user, "is_staff", False))
        except Exception:
            return False