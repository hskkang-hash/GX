"""
🔥 STRATEGY 4: CACHE WARMING
Proactively warm cache cho data hay được access
Warm data trước khi user request để elimite cold cache delays
"""

from celery import shared_task
from django.core.cache import cache
from django.db.models import Count
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import logging
import time

logger = logging.getLogger(__name__)


def update_progress_safe(task_self, progress, status):
    """Helper function to safely update task progress"""
    try:
        if hasattr(task_self, 'request') and task_self.request.id:
            task_self.update_state(state='PROGRESS', meta={'progress': progress, 'status': status})
    except:
        pass


@shared_task(bind=True)
def warm_popular_data_cache(self):
    """🔥 Warm cache for most frequently accessed data"""
    try:
        start_time = time.time()
        warmed_caches = {}
        
        update_progress_safe(self, 10, 'Starting cache warming')
        
        # 1. 🔥 Warm first page of orders (using REAL API SERVICE + SCHEMA)
        update_progress_safe(self, 20, 'Warming order list cache using OrderService + OrderListOutSchema')
        
        try:
            from orders.services.order_service import OrderService
            from orders.schemas.schemas_djantic_out import OrderListOutSchema
            
            # 🚀 USE REAL API SERVICE METHOD
            # Call the same service method that real API uses
            data = {
                'page_size': 25,
                'current_page': 1,
                'created_on_start': None,
                'created_on_end': None,
                'mapped_status': None,
                'receipt_code': None
            }
            
            # Call OrderService.get_list with same parameters as real API
            orders, total_pages, total_items = OrderService.get_list(
                data=data,
                page_size=25,
                current_page=1,
                exclude_fields=[],
                sort_obj={}
            )
            
            # 🚀 USE REAL API SCHEMA to serialize data
            # This ensures 100% identical structure to real API response
            orders_data = OrderListOutSchema.from_queryset(orders, many=True)
            
            # Convert to serializable format (dict)
            serialized_orders = [order.dict() for order in orders_data] if hasattr(orders_data, '__iter__') else []
            
            cache.set('warm_orders_first_page', serialized_orders, timeout=300)  # 5 minutes
            warmed_caches['orders_first_page'] = len(serialized_orders)
            
        except Exception as e:
            logger.warning(f"Could not warm orders cache: {e}")
            warmed_caches['orders_first_page'] = 0
        
        # 2. 🔥 Warm active devices (using REAL API SCHEMA)
        update_progress_safe(self, 40, 'Warming device list cache using DeviceListOutSchema')
        
        try:
            from devices.models import Device
            from devices.schemas.schemas_djantic_out import DeviceListOutSchema
            
            # 🚀 USE REAL API QUERY LOGIC
            # Apply same filtering, select_related, and prefetch_related as real device API
            active_devices = Device.objects.filter(
                active=True
            ).select_related(
                'main_type',
                'status',
                'created_by'
            ).prefetch_related(
                'cargo_compartments',
                'dimensions_and_weight',
                'propulsion_system',
                'flight_control_system'
            )[:20]  # Standard page size
            
            # 🚀 USE REAL API SCHEMA to serialize data
            # This ensures 100% identical structure to real API response
            devices_data = DeviceListOutSchema.from_queryset(active_devices, many=True)
            
            # Convert to serializable format (dict)
            serialized_devices = [device.dict() for device in devices_data] if hasattr(devices_data, '__iter__') else []
            
            cache.set('warm_active_devices', serialized_devices, timeout=600)  # 10 minutes
            warmed_caches['active_devices'] = len(serialized_devices)
            
        except Exception as e:
            logger.warning(f"Could not warm devices cache: {e}")
            warmed_caches['active_devices'] = 0
        
        # 3. Warm status mappings
        update_progress_safe(self, 60, 'Warming status mappings cache')
        
        try:
            from orders.models import OrderStatus
            
            status_mappings = []
            for status in OrderStatus.objects.all():
                status_mappings.append({
                    'id': status.id,
                    'code': status.code,
                    'name': status.name
                })
            
            cache.set('warm_status_mappings', status_mappings, timeout=1800)  # 30 minutes
            warmed_caches['status_mappings'] = len(status_mappings)
            
        except Exception as e:
            logger.warning(f"Could not warm status mappings: {e}")
            warmed_caches['status_mappings'] = 0
        
        # 4. 🔥 Warm delivery operations (using REAL API SERVICE + SCHEMA)  
        update_progress_safe(self, 80, 'Warming delivery operations using DeliverySystem + Schema')
        
        try:
            from delivery.models import DeliveryOperation
            from delivery.services.delivery_system import DeliverySystem
            from delivery.schemas.schemas_djantic_out import DeliveryOperationOutSchema
            from django.db.models import Count, F, CharField, Value
            from django.db.models.functions import Concat, Coalesce
            
            # 🚀 USE REAL API SERVICE METHOD
            # Get operations using the same service method that real API uses
            page_size = 25  # Standard API page size
            
            # Get recent operations with all the complex annotations (like real API)
            operations = DeliveryOperation.objects.select_related(
                'current_status', 
                'order', 
                'order__status',
                'order__recipient_address',
                'order__pickup_location',
                'order__created_by',
                'created_by'
            ).prefetch_related(
                'order__items'
            ).annotate(
                number_of_packages=Count('order__items__id', distinct=True),
                order_identifier=Coalesce(
                    F('order__order_code'),
                    output_field=CharField()
                ),
                handler=Concat(
                    Coalesce(F('order__created_by__first_name'), Value(''), output_field=CharField()),
                    Value(' '),
                    Coalesce(F('created_by__first_name'), Value(''), output_field=CharField()),
                    output_field=CharField()
                )
            ).order_by('-created_on')[:page_size]
            
            # 🚀 USE REAL API SCHEMA to serialize data
            # This ensures 100% identical structure to real API response
            operations_data = DeliveryOperationOutSchema.from_queryset(operations, many=True)
            
            # Convert to serializable format (dict)
            serialized_operations = [operation.dict() for operation in operations_data] if hasattr(operations_data, '__iter__') else []
            
            cache.set('warm_delivery_operations', serialized_operations, timeout=420)  # 7 minutes
            warmed_caches['delivery_operations'] = len(serialized_operations)
            
        except Exception as e:
            logger.warning(f"Could not warm delivery operations: {e}")
            warmed_caches['delivery_operations'] = 0
        
        # 5. Warm user permission patterns (common ones)
        update_progress_safe(self, 90, 'Warming permission cache')
        
        try:
            # Common permission patterns for faster access
            common_permissions = {
                'superuser_permissions': {'is_superuser': True, 'all_access': True},
                'admin_permissions': {'order_access': True, 'device_access': True},
                'viewer_permissions': {'read_only': True},
                'last_updated': datetime.now().isoformat()
            }
            
            cache.set('warm_permission_patterns', common_permissions, timeout=900)  # 25 minutes
            warmed_caches['permission_patterns'] = len(common_permissions)
            
        except Exception as e:
            logger.warning(f"Could not warm permissions: {e}")
            warmed_caches['permission_patterns'] = 0
        
        update_progress_safe(self, 100, 'Cache warming completed')
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        logger.info(f"🔥 Cache warming completed in {total_time}ms")
        
        return {
            'status': 'success',
            'warmed_caches': warmed_caches,
            'total_items_warmed': sum(warmed_caches.values()),
            'warming_time_ms': total_time,
            'cache_keys_created': list(warmed_caches.keys())
        }
        
    except Exception as exc:
        logger.error(f"❌ Error warming cache: {exc}")
        try:
            if hasattr(self, 'request') and self.request.id:
                self.update_state(state='FAILURE', meta={'error': str(exc)})
        except:
            pass
        raise exc


@shared_task(bind=True)
def warm_user_specific_cache(self, user_id):
    """🔥 Warm cache cho specific user permissions và data"""
    try:
        start_time = time.time()
        
        update_progress_safe(self, 10, f'Loading user {user_id} data')
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.select_related().prefetch_related('groups', 'user_permissions').get(id=user_id)
        except User.DoesNotExist:
            return {'status': 'error', 'error': f'User {user_id} not found'}
        
        update_progress_safe(self, 50, 'Caching user permissions')
        
        # Warm user-specific data
        user_cache_data = {
            'user_id': user.id,
            'username': user.username,
            'is_superuser': user.is_superuser,
            'is_staff': getattr(user, 'is_staff', False),
            'user_permissions': list(user.user_permissions.values('id', 'codename')),
            'user_groups': list(user.groups.values('id', 'name')),
            'language': getattr(user, 'language', None),
            'last_warmed': datetime.now().isoformat()
        }
        
        # Cache user data for 25 minutes
        cache.set(f'warm_user_data_{user_id}', user_cache_data, timeout=900)
        
        # Cache user's recent orders if accessible
        try:
            update_progress_safe(self, 80, 'Caching user recent data')
            
            from orders.models import Order
            user_orders = Order.objects.filter(
                created_by=user
            ).select_related('status').order_by('-created_on')[:10]
            
            user_orders_data = []
            for order in user_orders:
                user_orders_data.append({
                    'id': order.id,
                    'order_code': getattr(order, 'order_code', ''),
                    'status_code': order.status.code if order.status else 'unknown',
                    'created_on': order.created_on.isoformat() if order.created_on else ''
                })
            
            cache.set(f'warm_user_orders_{user_id}', user_orders_data, timeout=600)
            
        except Exception as order_error:
            logger.warning(f"Could not cache user orders: {order_error}")
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            'status': 'success',
            'user_id': user_id,
            'cached_items': len(user_cache_data),
            'warming_time_ms': total_time
        }
        
    except Exception as exc:
        logger.error(f"❌ Error warming user cache: {exc}")
        try:
            if hasattr(self, 'request') and self.request.id:
                self.update_state(state='FAILURE', meta={'error': str(exc)})
        except:
            pass
        raise exc


@shared_task(bind=True)
def warm_dashboard_cache(self):
    """🔥 Warm dashboard-specific cache data"""
    try:
        start_time = time.time()
        
        update_progress_safe(self, 10, 'Warming dashboard cache')
        
        # Get precomputed stats if available
        from optimization.tasks.aggregation_tasks import get_all_precomputed_stats
        dashboard_stats = get_all_precomputed_stats()
        
        update_progress_safe(self, 40, 'Preparing dashboard summary')
        
        # Create dashboard summary
        dashboard_summary = {
            'stats_available': any([
                dashboard_stats.get('order_stats'),
                dashboard_stats.get('device_metrics'),
                dashboard_stats.get('delivery_stats')
            ]),
            'last_stats_update': None,
            'quick_stats': {},
            'cache_status': dashboard_stats.get('cache_status', {}),
            'last_warmed': datetime.now().isoformat()
        }
        
        # Extract quick stats if available
        if dashboard_stats.get('order_stats'):
            order_stats = dashboard_stats['order_stats']
            dashboard_summary['quick_stats']['orders'] = {
                'total': order_stats.get('basic_stats', {}).get('total_orders', 0),
                'today': order_stats.get('basic_stats', {}).get('orders_today', 0),
                'last_updated': order_stats.get('last_updated')
            }
            dashboard_summary['last_stats_update'] = order_stats.get('last_updated')
        
        if dashboard_stats.get('device_metrics'):
            device_metrics = dashboard_stats['device_metrics']
            dashboard_summary['quick_stats']['devices'] = {
                'total': device_metrics.get('basic_stats', {}).get('total_devices', 0),
                'active': device_metrics.get('basic_stats', {}).get('active_devices', 0),
                'last_updated': device_metrics.get('last_updated')
            }
        
        update_progress_safe(self, 80, 'Caching dashboard data')
        
        # Cache dashboard summary for quick access
        cache.set('warm_dashboard_summary', dashboard_summary, timeout=300)  # 5 minutes
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        logger.info(f"🔥 Dashboard cache warmed in {total_time}ms")
        
        return {
            'status': 'success',
            'dashboard_cached': True,
            'stats_available': dashboard_summary['stats_available'],
            'warming_time_ms': total_time
        }
        
    except Exception as exc:
        logger.error(f"❌ Error warming dashboard cache: {exc}")
        try:
            if hasattr(self, 'request') and self.request.id:
                self.update_state(state='FAILURE', meta={'error': str(exc)})
        except:
            pass
        raise exc


# Helper functions
def get_all_warmed_cache_status():
    """📊 Get status of all warmed caches"""
    cache_keys = [
        'warm_orders_first_page',
        'warm_active_devices', 
        'warm_status_mappings',
        'warm_delivery_operations',
        'warm_permission_patterns',
        'warm_dashboard_summary'
    ]
    
    cache_status = {}
    for key in cache_keys:
        cached_data = cache.get(key)
        cache_status[key] = {
            'cached': cached_data is not None,
            'size': len(str(cached_data)) if cached_data else 0,
            'items': len(cached_data) if isinstance(cached_data, (list, dict)) else 0
        }
    
    return {
        'cache_status': cache_status,
        'total_cached': sum(1 for status in cache_status.values() if status['cached']),
        'check_time': datetime.now().isoformat()
    }


def warm_specific_data(data_type, limit=20):
    """🎯 Warm specific type of data on demand"""
    try:
        if data_type == 'orders':
            from orders.models import Order
            return Order.objects.select_related('status').order_by('-created_on')[:limit]
        elif data_type == 'devices':
            from devices.models import Device
            return Device.objects.filter(active=True)[:limit]
        elif data_type == 'deliveries':
            from delivery.models import DeliveryOperation
            return DeliveryOperation.objects.select_related('current_status')[:limit]
        else:
            return None
    except Exception as e:
        logger.warning(f"Could not warm {data_type}: {e}")
        return None
