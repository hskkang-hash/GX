"""
🔧 Redis Connection Pool - CRITICAL FIX
Giải quyết vấn đề connection leak trong cache invalidation
"""
import redis
import threading
import time
import logging
from django.conf import settings


class RedisConnectionPool:
    """
    🚀 Singleton Redis Connection Pool
    Giải quyết vấn đề connection leak bằng cách share connection pool
    """
    _instance = None
    _lock = threading.RLock()
    _pool = None
    _client = None
    _connection_failed = False
    _failure_count = 0
    _last_failure_time = 0
    _did_log_init = False
    _did_log_failure = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_client(cls):
        """
        🔧 Get Redis client from shared connection pool
        Returns: Redis client or None if connection failed
        """
        # Circuit breaker: Stop trying if too many failures
        current_time = time.time()
        if (cls._connection_failed and 
            cls._failure_count >= 5 and 
            current_time - cls._last_failure_time < 300):  # 5 minutes cooldown
            return None
        
        # Thread-safe client creation
        with cls._lock:
            if cls._client is None:
                try:
                    logger = logging.getLogger("redis_pool")
                    # Get Redis config
                    redis_host = getattr(settings, 'REDIS_HOST', 'redis://localhost:6379')
                    redis_port = getattr(settings, 'REDIS_PORT', 6379)
                    redis_db = getattr(settings, 'REDIS_DB', 0)
                    
                    # Build Redis URL
                    if redis_host.startswith('redis://'):
                        redis_url = f"{redis_host}/{redis_db}"
                    else:
                        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
                    
                    # Create connection pool (shared across all requests)
                    cls._pool = redis.ConnectionPool.from_url(
                        redis_url,
                        max_connections=100,           # Pool size
                        socket_timeout=5,              # Read timeout
                        socket_connect_timeout=3,      # Connect timeout
                        socket_keepalive=True,         # Keep connections alive
                        retry_on_timeout=True,
                        health_check_interval=30,      # Check connection health
                    )
                    
                    # Create client using pool
                    cls._client = redis.Redis(connection_pool=cls._pool)
                    
                    # Test connection
                    cls._client.ping()
                    
                    # Reset failure state
                    cls._connection_failed = False
                    cls._failure_count = 0
                    cls._did_log_failure = False
                    
                    # Avoid noisy stdout prints (Celery redirects stdout into logs, which can trigger DB log recursion)
                    if not cls._did_log_init:
                        logger.info("✅ Redis connection pool initialized (max=%s)", cls._pool.max_connections)
                        cls._did_log_init = True
                    
                except Exception as e:
                    logger = logging.getLogger("redis_pool")
                    # Log failure once per cooldown window to prevent log storms
                    if not cls._did_log_failure:
                        logger.warning("⚠️ Redis connection failed: %s", str(e)[:200])
                        cls._did_log_failure = True
                    cls._connection_failed = True
                    cls._failure_count += 1
                    cls._last_failure_time = current_time
                    cls._client = None
                    cls._pool = None
        
        return cls._client
    
    @classmethod
    def get_stats(cls):
        """Get connection pool statistics"""
        if cls._pool is None:
            return {
                'status': 'disconnected',
                'max_connections': 0,
                'available': 0,
                'in_use': 0
            }
        
        try:
            # Get pool stats
            pool_stats = {
                'status': 'connected' if cls._client else 'error',
                'max_connections': cls._pool.max_connections,
                'available': cls._pool._available_connections,
                'in_use': cls._pool._created_connections - cls._pool._available_connections,
                'created': cls._pool._created_connections,
                'failure_count': cls._failure_count,
            }
            return pool_stats
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    @classmethod
    def reset(cls):
        """Reset connection pool (for testing or emergency)"""
        with cls._lock:
            if cls._client:
                cls._client.close()
            if cls._pool:
                cls._pool.disconnect()
            cls._client = None
            cls._pool = None
            cls._connection_failed = False
            cls._failure_count = 0
            cls._did_log_init = False
            cls._did_log_failure = False
            logging.getLogger("redis_pool").info("🔄 Redis connection pool reset")


# Singleton instance
redis_pool = RedisConnectionPool()


def get_redis_client():
    """
    🎯 Helper function: Get Redis client from shared pool
    Use this EVERYWHERE instead of redis.Redis.from_url()
    
    Example:
        redis_client = get_redis_client()
        if redis_client:
            keys = redis_client.keys('pattern*')
    """
    return RedisConnectionPool.get_client()

