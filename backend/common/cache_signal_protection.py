"""
🔐 Signal Protection - Prevent Recursive Loops & Rate Limiting
CRITICAL FIX để prevent server down
"""
import threading
import time
from functools import wraps
from django.core.cache import cache as django_cache


class SignalProtection:
    """
    🔐 Protection mechanisms for signal handlers
    - Recursion detection
    - Rate limiting
    - Debouncing
    """
    
    # Recursion guard (thread-local)
    _recursion_guard = threading.local()
    
    # Rate limiting (shared)
    _rate_limit_lock = threading.Lock()
    _rate_limit_counters = {}  # {model_name: [(timestamp1, timestamp2, ...)]}
    
    # Debouncing (shared)
    _debounce_lock = threading.Lock()
    _debounce_timers = {}  # {key: Timer}
    _debounce_pending = {}  # {key: data}
    
    @classmethod
    def check_recursion(cls, signal_key: str) -> bool:
        """
        🔐 Check if signal is already being processed (recursion detection)
        Returns: True if recursion detected, False otherwise
        """
        if not hasattr(cls._recursion_guard, 'active'):
            cls._recursion_guard.active = set()
        
        if signal_key in cls._recursion_guard.active:
            return True  # Recursion detected!
        
        return False
    
    @classmethod
    def mark_active(cls, signal_key: str):
        """Mark signal as active"""
        if not hasattr(cls._recursion_guard, 'active'):
            cls._recursion_guard.active = set()
        cls._recursion_guard.active.add(signal_key)
    
    @classmethod
    def mark_inactive(cls, signal_key: str):
        """Mark signal as inactive"""
        if hasattr(cls._recursion_guard, 'active'):
            cls._recursion_guard.active.discard(signal_key)
    
    @classmethod
    def check_rate_limit(cls, model_name: str, max_per_minute: int = 100) -> bool:
        """
        🚦 Check if rate limit exceeded
        Returns: True if rate limit exceeded, False otherwise
        """
        current_time = time.time()
        cutoff_time = current_time - 60  # 1 minute ago
        
        with cls._rate_limit_lock:
            # Get existing timestamps
            if model_name not in cls._rate_limit_counters:
                cls._rate_limit_counters[model_name] = []
            
            timestamps = cls._rate_limit_counters[model_name]
            
            # Remove old timestamps (> 1 minute ago)
            timestamps = [t for t in timestamps if t > cutoff_time]
            cls._rate_limit_counters[model_name] = timestamps
            
            # Check if limit exceeded
            if len(timestamps) >= max_per_minute:
                return True  # Rate limit exceeded!
            
            # Add current timestamp
            timestamps.append(current_time)
            
            return False
    
    @classmethod
    def cleanup_rate_limits(cls):
        """Cleanup old rate limit data (should run periodically)"""
        current_time = time.time()
        cutoff_time = current_time - 120  # Keep 2 minutes of data
        
        with cls._rate_limit_lock:
            for model_name in list(cls._rate_limit_counters.keys()):
                timestamps = cls._rate_limit_counters[model_name]
                timestamps = [t for t in timestamps if t > cutoff_time]
                
                if not timestamps:
                    del cls._rate_limit_counters[model_name]
                else:
                    cls._rate_limit_counters[model_name] = timestamps


def recursion_protected(func):
    """
    🔐 Decorator: Protect function from recursive calls
    
    Usage:
        @receiver(post_save)
        @recursion_protected
        def my_signal_handler(sender, instance, **kwargs):
            ...
    """
    @wraps(func)
    def wrapper(sender, instance, **kwargs):
        # Generate unique key
        instance_id = getattr(instance, 'id', getattr(instance, 'pk', 'unknown'))
        # Handle both model classes and instances
        if hasattr(sender, '__name__'):
            sender_name = sender.__name__
        elif hasattr(sender, '_meta') and hasattr(sender._meta, 'model_name'):
            sender_name = sender._meta.model_name
        else:
            sender_name = 'unknown'
        signal_key = f"{sender_name}_{instance_id}_{func.__name__}"
        
        # Check recursion
        if SignalProtection.check_recursion(signal_key):
            print(f"⚠️ Recursion detected: {signal_key} - skipping")
            return
        
        try:
            # Mark as active
            SignalProtection.mark_active(signal_key)
            
            # Execute function
            return func(sender, instance, **kwargs)
            
        finally:
            # Always mark as inactive
            SignalProtection.mark_inactive(signal_key)
    
    return wrapper


def rate_limited(max_per_minute: int = 100):
    """
    🚦 Decorator: Rate limit function calls
    
    Usage:
        @receiver(post_save)
        @rate_limited(max_per_minute=50)
        def my_signal_handler(sender, instance, **kwargs):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(sender, instance, **kwargs):
            # Handle both model classes and instances
            if hasattr(sender, '_meta'):
                model_name = sender._meta.model_name
            else:
                model_name = getattr(sender, '__name__', 'unknown')
            
            # Check rate limit
            if SignalProtection.check_rate_limit(model_name, max_per_minute):
                print(f"⚠️ Rate limit exceeded for {model_name} ({max_per_minute}/min) - skipping")
                return
            
            # Execute function
            return func(sender, instance, **kwargs)
        
        return wrapper
    return decorator


def debounced(wait_seconds: float = 1.0):
    """
    ⏱️ Decorator: Debounce function calls (group rapid calls into one)
    
    Usage:
        @receiver(m2m_changed)
        @debounced(wait_seconds=1.0)
        def my_m2m_handler(sender, instance, action, **kwargs):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(sender, instance, action=None, **kwargs):
            # Generate unique key
            instance_id = getattr(instance, 'id', getattr(instance, 'pk', 'unknown'))
            # Handle both model classes and instances
            if hasattr(sender, '__name__'):
                sender_name = sender.__name__
            elif hasattr(sender, '_meta') and hasattr(sender._meta, 'model_name'):
                sender_name = sender._meta.model_name
            else:
                sender_name = 'unknown'
            debounce_key = f"{sender_name}_{instance_id}_{func.__name__}"
            
            with SignalProtection._debounce_lock:
                # Cancel previous timer
                if debounce_key in SignalProtection._debounce_timers:
                    SignalProtection._debounce_timers[debounce_key].cancel()
                
                # Store pending data
                SignalProtection._debounce_pending[debounce_key] = {
                    'sender': sender,
                    'instance': instance,
                    'action': action,
                    'kwargs': kwargs
                }
                
                # Create new timer
                def execute_function():
                    with SignalProtection._debounce_lock:
                        if debounce_key in SignalProtection._debounce_pending:
                            data = SignalProtection._debounce_pending.pop(debounce_key)
                            SignalProtection._debounce_timers.pop(debounce_key, None)
                            
                            # Execute function with pending data
                            func(data['sender'], data['instance'], 
                                 action=data['action'], **data['kwargs'])
                
                timer = threading.Timer(wait_seconds, execute_function)
                SignalProtection._debounce_timers[debounce_key] = timer
                timer.start()
        
        return wrapper
    return decorator


def protected_signal(max_per_minute: int = 100, debounce_seconds: float = 0):
    """
    🔐 Decorator: Full protection (recursion + rate limit + optional debounce)
    
    Usage:
        @receiver(post_save)
        @protected_signal(max_per_minute=50, debounce_seconds=1.0)
        def my_signal_handler(sender, instance, **kwargs):
            ...
    """
    def decorator(func):
        # Apply protections in order
        protected_func = recursion_protected(func)
        protected_func = rate_limited(max_per_minute)(protected_func)
        
        if debounce_seconds > 0:
            protected_func = debounced(debounce_seconds)(protected_func)
        
        return protected_func
    
    return decorator

