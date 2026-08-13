"""
🔢 STRATEGY 1: PRE-COMPUTED AGGREGATIONS
Background pre-compute heavy calculations cho orders, devices, deliveries
Thay vì tính real-time → background calculate và cache
"""

from celery import shared_task
from django.core.cache import cache
from django.db.models import Count, Sum, Avg, Q, F, Case, When, IntegerField
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
        # Silently ignore if not running via Celery worker
        pass


@shared_task(bind=True)
def precompute_order_statistics(self):
    """🔢 Pre-compute order statistics for dashboard and list views"""
    try:
        start_time = time.time()
        
        # Update progress
        update_progress_safe(self, 10, 'Loading order data')
        
        from orders.models import Order, OrderStatus
        
        # Time ranges for statistics
        now = datetime.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        year_ago = today - timedelta(days=365)
        
        update_progress_safe(self, 25, 'Calculating basic counts')
        
        # 1. Basic Order Counts
        basic_stats = {
            'total_orders': Order.objects.count(),
            'orders_today': Order.objects.filter(created_on__date=today).count(),
            'orders_this_week': Order.objects.filter(created_on__date__gte=week_ago).count(),
            'orders_this_month': Order.objects.filter(created_on__date__gte=month_ago).count(),
            'orders_this_year': Order.objects.filter(created_on__date__gte=year_ago).count(),
        }
        
        update_progress_safe(self, 40, 'Calculating status distribution')
        
        # 2. Status Distribution
        status_distribution = {}
        status_counts = Order.objects.values('status__code', 'status__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        for status in status_counts:
            status_distribution[status['status__code']] = {
                'count': status['count'],
                'name': status['status__name'],
                'percentage': round((status['count'] / basic_stats['total_orders']) * 100, 2) if basic_stats['total_orders'] > 0 else 0
            }
        
        update_progress_safe(self, 55, 'Calculating revenue metrics')
        
        # 3. Revenue Calculations
        revenue_stats = Order.objects.exclude(total_amount__isnull=True).aggregate(
            total_revenue=Sum('total_amount'),
            avg_order_value=Avg('total_amount'),
            revenue_today=Sum('total_amount', filter=Q(created_on__date=today)),
            revenue_this_week=Sum('total_amount', filter=Q(created_on__date__gte=week_ago)),
            revenue_this_month=Sum('total_amount', filter=Q(created_on__date__gte=month_ago))
        )
        
        # Convert Decimal to float for JSON serialization
        for key, value in revenue_stats.items():
            if value is not None:
                revenue_stats[key] = float(value)
            else:
                revenue_stats[key] = 0.0
        
        update_progress_safe(self, 70, 'Calculating delivery metrics')
        
        # 4. Delivery-related Order Metrics
        delivery_stats = {}
        try:
            # Orders with delivery operations
            orders_with_delivery = Order.objects.filter(
                delivery_operation__isnull=False
            ).distinct().count()
            
            # Completed deliveries
            completed_orders = Order.objects.filter(
                status__code__in=['completed_order', 'delivered']
            ).count()
            
            delivery_stats = {
                'orders_with_delivery': orders_with_delivery,
                'completed_orders': completed_orders,
                'completion_rate': round((completed_orders / basic_stats['total_orders']) * 100, 2) if basic_stats['total_orders'] > 0 else 0
            }
        except Exception as delivery_error:
            logger.warning(f"Could not calculate delivery stats: {delivery_error}")
            delivery_stats = {
                'orders_with_delivery': 0,
                'completed_orders': 0,
                'completion_rate': 0
            }
        
        update_progress_safe(self, 85, 'Calculating trend data')
        
        # 5. Trend Data (last 7 days)
        trend_data = []
        for i in range(7):
            date = today - timedelta(days=i)
            daily_count = Order.objects.filter(created_on__date=date).count()
            daily_revenue = Order.objects.filter(
                created_on__date=date
            ).aggregate(revenue=Sum('total_amount'))['revenue'] or 0
            
            trend_data.append({
                'date': date.isoformat(),
                'orders': daily_count,
                'revenue': float(daily_revenue) if daily_revenue else 0.0
            })
        
        # Reverse to get chronological order
        trend_data.reverse()
        
        update_progress_safe(self, 95, 'Caching results')
        
        # 6. Combine all statistics
        all_stats = {
            'basic_stats': basic_stats,
            'status_distribution': status_distribution,
            'revenue_stats': revenue_stats,
            'delivery_stats': delivery_stats,
            'trend_data': trend_data,
            'last_updated': now.isoformat(),
            'calculation_time_ms': round((time.time() - start_time) * 1000, 2)
        }
        
        # Cache for 5 minutes
        cache.set('precomputed_order_statistics', all_stats, timeout=300)
        
        logger.info(f"✅ Order statistics pre-computed in {all_stats['calculation_time_ms']}ms")
        
        return {
            'status': 'success',
            'total_orders': basic_stats['total_orders'],
            'status_count': len(status_distribution),
            'calculation_time_ms': all_stats['calculation_time_ms']
        }
        
    except Exception as exc:
        logger.error(f"❌ Error precomputing order statistics: {exc}")
        try:
            if hasattr(self, 'request') and self.request.id:
                self.update_state(state='FAILURE', meta={'error': str(exc)})
        except:
            pass  # Ignore if not running via Celery
        raise exc


@shared_task(bind=True) 
def precompute_device_metrics(self):
    """🔢 Pre-compute device performance metrics"""
    try:
        start_time = time.time()
        
        update_progress_safe(self, 10, 'Loading device data')
        
        from devices.models import Device
        
        # Basic device counts
        update_progress_safe(self, 25, 'Calculating device counts')
        
        basic_device_stats = {
            'total_devices': Device.objects.count(),
            'active_devices': Device.objects.filter(active=True).count(),
            'inactive_devices': Device.objects.filter(active=False).count(),
        }
        
        # Status distribution
        update_progress_safe(self, 40, 'Calculating status distribution')
        
        status_distribution = {}
        device_status_counts = Device.objects.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        for status in device_status_counts:
            status_distribution[status['status']] = {
                'count': status['count'],
                'percentage': round((status['count'] / basic_device_stats['total_devices']) * 100, 2) if basic_device_stats['total_devices'] > 0 else 0
            }
        
        # Device type distribution
        update_progress_safe(self, 55, 'Calculating type distribution')
        
        type_distribution = {}
        try:
            device_type_counts = Device.objects.filter(main_type__isnull=False).values(
                'main_type__name'
            ).annotate(count=Count('id')).order_by('-count')
            
            for device_type in device_type_counts:
                type_name = device_type['main_type__name']
                type_distribution[type_name] = {
                    'count': device_type['count'],
                    'percentage': round((device_type['count'] / basic_device_stats['total_devices']) * 100, 2) if basic_device_stats['total_devices'] > 0 else 0
                }
        except Exception as type_error:
            logger.warning(f"Could not calculate device type distribution: {type_error}")
            type_distribution = {}
        
        # Device performance metrics (if delivery operations exist)
        update_progress_safe(self, 70, 'Calculating performance metrics')
        
        performance_metrics = {}
        try:
            from delivery.models import DeliveryOperation
            
            devices_with_deliveries = Device.objects.filter(
                
            ).distinct()
            
            for device in devices_with_deliveries[:20]:  # Top 20 devices with deliveries
                try:
                    operations = DeliveryOperation.objects.filter(items__drone=device)
                    total_operations = operations.count()
                    
                    if total_operations > 0:
                        successful_operations = operations.filter(
                            current_status__code__in=['completed', 'delivered']
                        ).count()
                        
                        success_rate = (successful_operations / total_operations) * 100
                        
                        # Average delivery time if field exists
                        avg_delivery_time = 0
                        try:
                            delivery_time_avg = operations.filter(
                                current_status__code__in=['completed', 'delivered']
                            ).aggregate(avg=Avg('delivery_time'))['avg']
                            avg_delivery_time = float(delivery_time_avg) if delivery_time_avg else 0
                        except:
                            avg_delivery_time = 0
                        
                        performance_metrics[device.id] = {
                            'device_name': device.name,
                            'total_operations': total_operations,
                            'successful_operations': successful_operations,
                            'success_rate': round(success_rate, 2),
                            'avg_delivery_time': avg_delivery_time
                        }
                except Exception as device_error:
                    logger.warning(f"Could not calculate metrics for device {device.id}: {device_error}")
                    continue
                    
        except Exception as perf_error:
            logger.warning(f"Could not calculate device performance metrics: {perf_error}")
            performance_metrics = {}
        
        update_progress_safe(self, 90, 'Finalizing results')
        
        # Combine all device metrics
        all_device_metrics = {
            'basic_stats': basic_device_stats,
            'status_distribution': status_distribution,
            'type_distribution': type_distribution,
            'performance_metrics': performance_metrics,
            'last_updated': datetime.now().isoformat(),
            'calculation_time_ms': round((time.time() - start_time) * 1000, 2)
        }
        
        # Cache for 10 minutes (devices change less frequently)
        cache.set('precomputed_device_metrics', all_device_metrics, timeout=600)
        
        logger.info(f"✅ Device metrics pre-computed in {all_device_metrics['calculation_time_ms']}ms")
        
        return {
            'status': 'success',
            'total_devices': basic_device_stats['total_devices'],
            'active_devices': basic_device_stats['active_devices'],
            'performance_devices': len(performance_metrics),
            'calculation_time_ms': all_device_metrics['calculation_time_ms']
        }
        
    except Exception as exc:
        logger.error(f"❌ Error precomputing device metrics: {exc}")
        try:
            if hasattr(self, 'request') and self.request.id:
                self.update_state(state='FAILURE', meta={'error': str(exc)})
        except:
            pass
        raise exc


@shared_task(bind=True)
def precompute_delivery_statistics(self):
    """🔢 Pre-compute delivery operation statistics"""
    try:
        start_time = time.time()
        
        update_progress_safe(self, 10, 'Loading delivery data')
        
        try:
            from delivery.models import DeliveryOperation
            
            # Time ranges
            now = datetime.now()
            today = now.date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            update_progress_safe(self, 30, 'Calculating delivery counts')
            
            # Basic delivery stats
            basic_delivery_stats = {
                'total_deliveries': DeliveryOperation.objects.count(),
                'deliveries_today': DeliveryOperation.objects.filter(created_on__date=today).count(),
                'deliveries_this_week': DeliveryOperation.objects.filter(created_on__date__gte=week_ago).count(),
                'deliveries_this_month': DeliveryOperation.objects.filter(created_on__date__gte=month_ago).count(),
            }
            
            update_progress_safe(self, 60, 'Calculating status distribution')
            
            # Delivery status distribution
            delivery_status_distribution = {}
            status_counts = DeliveryOperation.objects.values('current_status__code', 'current_status__name').annotate(
                count=Count('id')
            ).order_by('-count')
            
            for status in status_counts:
                delivery_status_distribution[status['current_status__code']] = {
                    'count': status['count'],
                    'name': status['current_status__name'],
                    'percentage': round((status['count'] / basic_delivery_stats['total_deliveries']) * 100, 2) if basic_delivery_stats['total_deliveries'] > 0 else 0
                }
            
            update_progress_safe(self, 90, 'Finalizing delivery stats')
            
            # Combine delivery statistics
            all_delivery_stats = {
                'basic_stats': basic_delivery_stats,
                'status_distribution': delivery_status_distribution,
                'last_updated': now.isoformat(),
                'calculation_time_ms': round((time.time() - start_time) * 1000, 2)
            }
            
            # Cache for 7 minutes
            cache.set('precomputed_delivery_statistics', all_delivery_stats, timeout=420)
            
            logger.info(f"✅ Delivery statistics pre-computed in {all_delivery_stats['calculation_time_ms']}ms")
            
            return {
                'status': 'success',
                'total_deliveries': basic_delivery_stats['total_deliveries'],
                'status_count': len(delivery_status_distribution),
                'calculation_time_ms': all_delivery_stats['calculation_time_ms']
            }
            
        except ImportError:
            # Delivery models don't exist, skip this task
            logger.info("📦 Delivery models not found, skipping delivery statistics")
            return {'status': 'skipped', 'reason': 'delivery_models_not_found'}
            
    except Exception as exc:
        logger.error(f"❌ Error precomputing delivery statistics: {exc}")
        try:
            if hasattr(self, 'request') and self.request.id:
                self.update_state(state='FAILURE', meta={'error': str(exc)})
        except:
            pass
        raise exc


# Helper function to get all precomputed stats at once
def get_all_precomputed_stats():
    """📊 Get all precomputed statistics from cache"""
    return {
        'order_stats': cache.get('precomputed_order_statistics', {}),
        'device_metrics': cache.get('precomputed_device_metrics', {}),
        'delivery_stats': cache.get('precomputed_delivery_statistics', {}),
        'cache_status': {
            'order_stats_cached': cache.get('precomputed_order_statistics') is not None,
            'device_metrics_cached': cache.get('precomputed_device_metrics') is not None,
            'delivery_stats_cached': cache.get('precomputed_delivery_statistics') is not None,
        }
    }