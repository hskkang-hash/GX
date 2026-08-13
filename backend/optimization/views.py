"""
🚀 OPTIMIZATION API VIEWS
API endpoints để sử dụng precomputed data và test performance
"""

from ninja_extra import api_controller, route
from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from django.core.cache import cache
from django.http import JsonResponse
from celery.result import AsyncResult
import time
from optimization.tasks.aggregation_tasks import get_all_precomputed_stats


@api_controller('/optimization', tags=['Background Optimization'])
class OptimizationAPI:
    
    @route.get('/dashboard-stats', auth=CustomJWTAuth())
    def get_dashboard_stats(self, request):
        """📊 Get precomputed dashboard statistics (ultra fast)"""
        start_time = time.time()
        
        # Get all precomputed stats from cache
        stats = get_all_precomputed_stats()
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return BaseResponse(
            status_code=200,
            message="Dashboard statistics retrieved successfully",
            data={
                **stats,
                'api_response_time_ms': response_time,
                'performance_note': 'This data is pre-computed in background for ultra-fast response'
            }
        )
    
    @route.get('/order-statistics', auth=CustomJWTAuth())
    def get_order_statistics(self, request):
        """📈 Get precomputed order statistics"""
        start_time = time.time()
        
        order_stats = cache.get('precomputed_order_statistics', {})
        
        if not order_stats:
            return BaseResponse(
                status_code=202,
                message="Statistics are being computed in background, please try again in a moment",
                data={
                    'cache_status': 'empty',
                    'suggestion': 'Background task may still be running'
                }
            )
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return BaseResponse(
            status_code=200,
            message="Order statistics retrieved successfully",
            data={
                **order_stats,
                'api_response_time_ms': response_time
            }
        )
    
    @route.get('/device-metrics', auth=CustomJWTAuth())
    def get_device_metrics(self, request):
        """🔧 Get precomputed device metrics"""
        start_time = time.time()
        
        device_metrics = cache.get('precomputed_device_metrics', {})
        
        if not device_metrics:
            return BaseResponse(
                status_code=202,
                message="Device metrics are being computed in background",
                data={'cache_status': 'empty'}
            )
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return BaseResponse(
            status_code=200,
            message="Device metrics retrieved successfully",
            data={
                **device_metrics,
                'api_response_time_ms': response_time
            }
        )
    
    @route.post('/trigger-computation', auth=CustomJWTAuth())
    def trigger_manual_computation(self, request):
        """🔄 Manually trigger background computation tasks"""
        from optimization.tasks.aggregation_tasks import (
            precompute_order_statistics, 
            precompute_device_metrics,
            precompute_delivery_statistics
        )
        
        # Start all background tasks
        order_task = precompute_order_statistics.delay()
        device_task = precompute_device_metrics.delay()
        delivery_task = precompute_delivery_statistics.delay()
        
        return BaseResponse(
            status_code=200,
            message="Background computation tasks started",
            data={
                'task_ids': {
                    'order_stats': order_task.id,
                    'device_metrics': device_task.id,
                    'delivery_stats': delivery_task.id
                },
                'status_urls': {
                    'order_stats': f'/api/optimization/task-status/{order_task.id}/',
                    'device_metrics': f'/api/optimization/task-status/{device_task.id}/',
                    'delivery_stats': f'/api/optimization/task-status/{delivery_task.id}/'
                },
                'note': 'Use status URLs to check computation progress'
            }
        )
    
    @route.post('/trigger-cache-warming', auth=CustomJWTAuth())
    def trigger_cache_warming(self, request):
        """🔥 Manually trigger cache warming tasks"""
        from optimization.tasks.cache_warming_tasks import (
            warm_popular_data_cache,
            warm_dashboard_cache,
            warm_user_specific_cache
        )
        
        # Start cache warming tasks
        popular_data_task = warm_popular_data_cache.delay()
        dashboard_task = warm_dashboard_cache.delay()
        
        # Optionally warm current user's cache
        user_task = None
        if request.user and request.user.id:
            user_task = warm_user_specific_cache.delay(request.user.id)
        
        task_data = {
            'popular_data': popular_data_task.id,
            'dashboard': dashboard_task.id,
        }
        
        status_urls = {
            'popular_data': f'/api/optimization/task-status/{popular_data_task.id}/',
            'dashboard': f'/api/optimization/task-status/{dashboard_task.id}/',
        }
        
        if user_task:
            task_data['user_cache'] = user_task.id
            status_urls['user_cache'] = f'/api/optimization/task-status/{user_task.id}/'
        
        return BaseResponse(
            status_code=200,
            message="Cache warming tasks started",
            data={
                'task_ids': task_data,
                'status_urls': status_urls,
                'note': 'Use status URLs to check warming progress'
            }
        )
    
    @route.get('/warm-cache-status', auth=CustomJWTAuth())
    def get_warm_cache_status(self, request):
        """🔥 Get status of all warmed caches"""
        start_time = time.time()
        
        from optimization.tasks.cache_warming_tasks import get_all_warmed_cache_status
        
        cache_status = get_all_warmed_cache_status()
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return BaseResponse(
            status_code=200,
            message="Warm cache status retrieved successfully",
            data={
                **cache_status,
                'api_response_time_ms': response_time
            }
        )
    
    @route.get('/warm-data/{data_type}', auth=CustomJWTAuth())
    def get_warm_data(self, request, data_type: str):
        """🎯 Get specific warmed data from cache"""
        start_time = time.time()
        
        cache_key_map = {
            'orders': 'warm_orders_first_page',
            'devices': 'warm_active_devices',
            'status': 'warm_status_mappings',
            'deliveries': 'warm_delivery_operations',
            'dashboard': 'warm_dashboard_summary',
            'permissions': 'warm_permission_patterns'
        }
        
        cache_key = cache_key_map.get(data_type)
        if not cache_key:
            return BaseResponse(
                status_code=400,
                message="Invalid data type",
                data={
                    'available_types': list(cache_key_map.keys()),
                    'requested_type': data_type
                }
            )
        
        warmed_data = cache.get(cache_key)
        response_time = round((time.time() - start_time) * 1000, 2)
        
        if warmed_data:
            return BaseResponse(
                status_code=200,
                message=f"Warmed {data_type} data retrieved successfully",
                data={
                    'data': warmed_data,
                    'data_type': data_type,
                    'cache_key': cache_key,
                    'items_count': len(warmed_data) if isinstance(warmed_data, (list, dict)) else 1,
                    'api_response_time_ms': response_time,
                    'note': 'This data was pre-warmed in cache for fast access'
                }
            )
        else:
            return BaseResponse(
                status_code=404,
                message=f"No warmed data found for {data_type}",
                data={
                    'data_type': data_type,
                    'cache_key': cache_key,
                    'suggestion': 'Try triggering cache warming first',
                    'api_response_time_ms': response_time
                }
            )
    
    @route.get('/task-status/{task_id}', auth=CustomJWTAuth())
    def get_task_status(self, request, task_id: str):
        """📊 Get background task progress status"""
        try:
            result = AsyncResult(task_id)
            
            if result.state == 'PENDING':
                response_data = {
                    'state': 'PENDING',
                    'progress': 0,
                    'status': 'Task is waiting to be processed'
                }
            elif result.state == 'PROGRESS':
                response_data = {
                    'state': 'PROGRESS',
                    'progress': result.info.get('progress', 0),
                    'status': result.info.get('status', 'Processing...'),
                    **result.info
                }
            elif result.state == 'SUCCESS':
                response_data = {
                    'state': 'SUCCESS',
                    'progress': 100,
                    'status': 'Task completed successfully',
                    'result': result.result
                }
            else:  # FAILURE
                response_data = {
                    'state': 'FAILURE',
                    'progress': 0,
                    'status': 'Task failed',
                    'error': str(result.info)
                }
            
            return BaseResponse(
                status_code=200,
                message="Task status retrieved successfully",
                data=response_data
            )
            
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message="Error retrieving task status",
                data={'error': str(e)}
            )
    
    @route.get('/cache-status', auth=CustomJWTAuth())
    def get_cache_status(self, request):
        """💾 Check cache status of all precomputed data"""
        start_time = time.time()
        
        cache_status = {
            'order_statistics': {
                'cached': cache.get('precomputed_order_statistics') is not None,
                'last_updated': None,
                'size': 0
            },
            'device_metrics': {
                'cached': cache.get('precomputed_device_metrics') is not None,
                'last_updated': None,
                'size': 0
            },
            'delivery_statistics': {
                'cached': cache.get('precomputed_delivery_statistics') is not None,
                'last_updated': None,
                'size': 0
            }
        }
        
        # Get detailed info if cached
        order_stats = cache.get('precomputed_order_statistics')
        if order_stats:
            cache_status['order_statistics']['last_updated'] = order_stats.get('last_updated')
            cache_status['order_statistics']['size'] = len(str(order_stats))
        
        device_metrics = cache.get('precomputed_device_metrics')
        if device_metrics:
            cache_status['device_metrics']['last_updated'] = device_metrics.get('last_updated')
            cache_status['device_metrics']['size'] = len(str(device_metrics))
        
        delivery_stats = cache.get('precomputed_delivery_statistics')
        if delivery_stats:
            cache_status['delivery_statistics']['last_updated'] = delivery_stats.get('last_updated')
            cache_status['delivery_statistics']['size'] = len(str(delivery_stats))
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return BaseResponse(
            status_code=200,
            message="Cache status retrieved successfully",
            data={
                'cache_status': cache_status,
                'api_response_time_ms': response_time,
                'overall_cached_count': sum(1 for status in cache_status.values() if status['cached'])
            }
        )
    
    @route.get('/performance-comparison', auth=CustomJWTAuth())
    def performance_comparison(self, request):
        """⚡ Compare performance: precomputed vs real-time calculation"""
        
        # 1. Test precomputed data speed
        precomputed_start = time.time()
        precomputed_stats = get_all_precomputed_stats()
        precomputed_time = round((time.time() - precomputed_start) * 1000, 2)
        
        # 2. Test real-time calculation speed (simplified)
        realtime_start = time.time()
        try:
            from orders.models import Order
            from devices.models import Device
            
            realtime_stats = {
                'order_count': Order.objects.count(),
                'device_count': Device.objects.count(),
                'active_devices': Device.objects.filter(active=True).count()
            }
        except Exception as e:
            realtime_stats = {'error': str(e)}
        
        realtime_time = round((time.time() - realtime_start) * 1000, 2)
        
        # Calculate improvement
        improvement_factor = round(realtime_time / precomputed_time, 2) if precomputed_time > 0 else 0
        improvement_percentage = round(((realtime_time - precomputed_time) / realtime_time) * 100, 2) if realtime_time > 0 else 0
        
        return BaseResponse(
            status_code=200,
            message="Performance comparison completed",
            data={
                'precomputed': {
                    'time_ms': precomputed_time,
                    'data_available': bool(precomputed_stats['order_stats'] or precomputed_stats['device_metrics']),
                    'comprehensive': True
                },
                'realtime': {
                    'time_ms': realtime_time,
                    'data': realtime_stats,
                    'comprehensive': False
                },
                'performance_improvement': {
                    'factor': f"{improvement_factor}x faster",
                    'percentage': f"{improvement_percentage}% improvement",
                    'time_saved_ms': realtime_time - precomputed_time
                },
                'recommendation': 'Use precomputed data for dashboard and statistics'
            }
        )
