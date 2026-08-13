"""
Common app configuration with core performance optimizations
"""
from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'common'
    
    def ready(self):
        """
        Called when Django app is ready - apply optimizations and enable cache signals
        """
        try:
            print("🚀 [DJANGO_READY] Applying backend optimizations...")
            
            # Import universal optimization signals  
            from . import universal_optimization  # 🌍 Universal optimization for ALL models & views
            
            # ENSURE signals are registered (fix for signal registration issues)
            from django.db.models.signals import post_save, post_delete, m2m_changed
            from .universal_optimization import universal_cache_invalidation, universal_m2m_invalidation
            
            # Manual signal registration to ensure they work
            post_save.connect(universal_cache_invalidation, dispatch_uid="universal_cache_post_save")
            post_delete.connect(universal_cache_invalidation, dispatch_uid="universal_cache_post_delete") 
            m2m_changed.connect(universal_m2m_invalidation, dispatch_uid="universal_cache_m2m")
            
            print("🌍 [DJANGO_READY] Universal optimization system initialized for ALL models & views")
            print("🔗 [DJANGO_READY] Cache invalidation signals registered manually")

            # 🧵 Thread request/user context propagation:
            # Make any `threading.Thread` spawned during a request automatically inherit user context
            # so BaseModel/permission logic relying on get_current_request() keeps working.
            from .thread_context import install_thread_request_propagation
            install_thread_request_propagation()
            print("🧵 [DJANGO_READY] Thread request context propagation installed")
            
            # Schema logic preservation: No aggressive core optimizations needed
            # Universal optimization handles caching without affecting schema logic
                
        except Exception as e:
            print(f"❌ [DJANGO_READY] Failed to apply optimizations: {e}")
            import traceback
            traceback.print_exc()
