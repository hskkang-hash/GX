"""
Performance optimization utilities for reducing N+1 queries and permission checks
"""
import time
from contextlib import contextmanager
from django.db import transaction
from core.middleware.refresh_token import get_current_request


class PermissionOptimizer:
    """Utility class for optimizing permission checks during QuerySet evaluation"""
    
    @classmethod
    @contextmanager
    def optimized_evaluation(cls, description="QuerySet evaluation"):
        """
        Context manager that optimizes permission checks and object instantiation
        during QuerySet evaluation
        """
        request = get_current_request()
        start_time = time.time()
        
        # Initialize optimization flags
        original_bypass = getattr(request, '_permission_bypass_active', False)
        request._permission_bypass_active = True
        
        # Initialize comprehensive caches if not exists
        if not hasattr(request, '_permission_result_cache'):
            request._permission_result_cache = {}
        if not hasattr(request, '_group_users_cache'):
            request._group_users_cache = {}
        if not hasattr(request, '_user_group_cache'):
            request._user_group_cache = {}
            
        try:
            yield
        finally:
            # Restore original state
            request._permission_bypass_active = original_bypass
            
            end_time = time.time()
            duration = (end_time - start_time) * 1000
            
            # Log performance metrics if debug mode
            if hasattr(request, '_performance_metrics'):
                request._performance_metrics.append({
                    'operation': description,
                    'duration_ms': duration,
                    'cache_hits': len(getattr(request, '_permission_result_cache', {})),
                    'timestamp': end_time
                })
    
    @classmethod
    def enable_request_caching(cls, request):
        """Enable comprehensive request-level caching"""
        if not hasattr(request, '_permission_result_cache'):
            request._permission_result_cache = {}
        if not hasattr(request, '_group_users_cache'):
            request._group_users_cache = {}
        if not hasattr(request, '_user_group_cache'):
            request._user_group_cache = {}
        if not hasattr(request, '_performance_metrics'):
            request._performance_metrics = []
    
    @classmethod
    def get_performance_stats(cls, request):
        """Get performance statistics for the request"""
        if not hasattr(request, '_performance_metrics'):
            return {}
            
        metrics = request._performance_metrics
        if not metrics:
            return {}
            
        total_duration = sum(m['duration_ms'] for m in metrics)
        cache_efficiency = len(request._permission_result_cache) if hasattr(request, '_permission_result_cache') else 0
        
        return {
            'total_duration_ms': total_duration,
            'operations_count': len(metrics),
            'cache_entries': cache_efficiency,
            'operations': metrics
        }


@contextmanager
def optimized_queryset_evaluation():
    """
    Simple context manager for optimizing QuerySet evaluation performance
    """
    with PermissionOptimizer.optimized_evaluation("QuerySet to List conversion"):
        yield


@contextmanager 
def optimized_schema_processing():
    """
    Context manager for optimizing schema processing performance
    """
    with PermissionOptimizer.optimized_evaluation("Schema processing"):
        yield
