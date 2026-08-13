import redis
import json
import time
from typing import Dict, Optional, Any
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self.client = None
        self.available = False
        
        try:
            # Handle Redis URL format (redis://host:port) or separate host/port
            if settings.REDIS_HOST.startswith('redis://'):
                # Use URL format
                redis_url = f"{settings.REDIS_HOST}/{settings.REDIS_DB}"
                self.client = redis.from_url(redis_url, decode_responses=True)
            else:
                # Use separate host/port
                self.client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=int(settings.REDIS_PORT),
                    db=int(settings.REDIS_DB),
                    decode_responses=True
                )
            # Test connection
            self.client.ping()
            self.available = True
            logger.info("Redis client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            logger.warning("Redis functionality will be disabled")
    
    def set_recording_status(self, record_code: str, status: Dict[str, Any], expire_seconds: int = 3600):
        """
        Set recording status in Redis with expiration.
        
        Args:
            record_code: Unique identifier for the recording
            status: Status dictionary containing recording information
            expire_seconds: Time to live in seconds (default 1 hour)
        """
        if not self.available or not self.client:
            logger.warning("Redis is unavailable. Recording status will not be saved.")
            return False
            
        try:
            key = f"{settings.REDIS_RECORDING_STATUS_KEY}:{record_code}"
            self.client.setex(key, expire_seconds, json.dumps(status))
            logger.debug(f"Recording status saved for {record_code}: {status}")
            return True
        except Exception as e:
            logger.error(f"Error saving recording status to Redis: {e}")
            return False
    
    def get_recording_status(self, record_code: str) -> Optional[Dict[str, Any]]:
        """
        Get recording status from Redis.
        
        Args:
            record_code: Unique identifier for the recording
            
        Returns:
            Status dictionary or None if not found
        """
        if not self.available or not self.client:
            logger.warning("Redis is unavailable. Cannot retrieve recording status.")
            return None
            
        try:
            key = f"{settings.REDIS_RECORDING_STATUS_KEY}:{record_code}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving recording status from Redis: {e}")
            return None
    
    def update_recording_status(self, record_code: str, updates: Dict[str, Any], expire_seconds: int = 3600):
        """
        Update existing recording status with new information.
        
        Args:
            record_code: Unique identifier for the recording
            updates: Dictionary with fields to update
            expire_seconds: Time to live in seconds (default 1 hour)
        """
        if not self.available or not self.client:
            logger.warning("Redis is unavailable. Recording status will not be updated.")
            return False
            
        try:
            key = f"{settings.REDIS_RECORDING_STATUS_KEY}:{record_code}"
            current_status = self.get_recording_status(record_code) or {}
            current_status.update(updates)
            current_status['updated_at'] = time.time()
            
            self.client.setex(key, expire_seconds, json.dumps(current_status))
            logger.debug(f"Recording status updated for {record_code}: {updates}")
            return True
        except Exception as e:
            logger.error(f"Error updating recording status in Redis: {e}")
            return False
    
    def delete_recording_status(self, record_code: str):
        """
        Delete recording status from Redis.
        
        Args:
            record_code: Unique identifier for the recording
        """
        if not self.available or not self.client:
            logger.warning("Redis is unavailable. Cannot delete recording status.")
            return False
            
        try:
            key = f"{settings.REDIS_RECORDING_STATUS_KEY}:{record_code}"
            self.client.delete(key)
            logger.debug(f"Recording status deleted for {record_code}")
            return True
        except Exception as e:
            logger.error(f"Error deleting recording status from Redis: {e}")
            return False
    
    def list_recording_statuses(self, pattern: str = "recording_status:*") -> Dict[str, Dict[str, Any]]:
        """
        List all recording statuses matching a pattern.
        
        Args:
            pattern: Redis key pattern to match
            
        Returns:
            Dictionary of record_code -> status
        """
        if not self.available or not self.client:
            logger.warning("Redis is unavailable. Cannot list recording statuses.")
            return {}
            
        try:
            keys = self.client.keys(pattern)
            result = {}
            for key in keys:
                record_code = key.replace(settings.REDIS_RECORDING_STATUS_KEY + ":", "")
                status = self.get_recording_status(record_code)
                if status:
                    result[record_code] = status
            return result
        except Exception as e:
            logger.error(f"Error listing recording statuses from Redis: {e}")
            return {}

    def clear_webrtc_state(self):
        if not self.available or not self.client:
            logger.warning("Redis is unavailable. Cannot clear WebRTC state.")
            return False
        try:
            self.client.delete("webrtc:state")
            logger.debug("WebRTC state cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing WebRTC state from Redis: {e}")
            return False

# Singleton instance to be used throughout the application
redis_client = RedisClient()
