import time
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Q, Subquery, OuterRef
from orders.models import Order, OrderHistory
from orders.schemas.schemas_djantic_out import OrderListOutSchema
from delivery.services.status_mapping_service import StatusMappingService
from core.middleware.refresh_token import thread_local
from common.performance_optimizer import optimized_queryset_evaluation, optimized_schema_processing, PermissionOptimizer


class Command(BaseCommand):
    help = 'Ultra simple performance test'

    def test_user(self, username):
        """Test performance for a user"""
        User = get_user_model()
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None

        # Set thread local and enable optimization
        request_obj = type('Request', (), {
            'user': user,
            'GET': {},
            'META': {},
            'method': 'GET'
        })()
        thread_local.request = request_obj
        PermissionOptimizer.enable_request_caching(request_obj)
        
        start_time = time.time()
        
        # Build queryset (simplified)
        mapping_annotations = StatusMappingService.build_annotate_with_mapping(context='order')
        
        orders_queryset = Order.objects.annotate(
            item_count=Count('items', distinct=True),
            **mapping_annotations
        ).select_related(
            'status', 'created_by', 'delivery_operation'
        ).prefetch_related(
            'items', 'histories'
        ).order_by('-modified_on')
        
        # Apply filter
        status_codes = ['delivered', 'pending_confirmation', 'awaiting_shipment', 'cancelled', 'pending_processing', 'awaiting_payment', 'returned']
        orders_queryset = orders_queryset.filter(status__code__in=status_codes)
        
        # 🚀 FINAL TEST: Apply dynamic filters (confirmed not the bottleneck)
        from core.common.search.dynamic_search import apply_dynamic_filters
        apply_filters_start = time.time()
        exclude_fields = []
        orders_queryset = apply_dynamic_filters(orders_queryset, request_obj, exclude_fields, request_obj.GET.get('sort_obj', None))
        apply_filters_time = time.time() - apply_filters_start
        print(f"⚡ apply_dynamic_filters time: {apply_filters_time * 1000:.2f}ms")
        
        # Pagination
        paginator = Paginator(orders_queryset, 25)
        pages = paginator.get_page(1)
        
        # Convert to list with optimization
        list_start = time.time()
        
        # 🚀 PERFORMANCE OPTIMIZED: Clean evaluation with minimal logging
        print(f"🔍 Converting QuerySet to List for {username}...")
        
        # OPTION 1: Complete silence (best performance)
        # from django.db.models.query import QuerySet
        # original_repr = QuerySet.__repr__
        # QuerySet.__repr__ = lambda self: f"<Silent: {self.model.__name__}>"
        
        with optimized_queryset_evaluation():
            orders_list = list(pages.object_list)
        
        # OPTION 2: Show first few items only (for verification)
        if orders_list:
            print(f"📋 Sample data - First order: {orders_list[0]}")
            if hasattr(orders_list[0], 'items') and orders_list[0].items.exists():
                print(f"📦 Sample item: {orders_list[0].items.first()}")
            
        print(f"✅ List conversion complete - {len(orders_list)} records")
            
        list_time = time.time() - list_start
        
        # Schema processing with optimization
        schema_start = time.time()
        with optimized_schema_processing():
            data = OrderListOutSchema.from_queryset(orders_list, many=True)
        schema_time = time.time() - schema_start
        
        total_time = time.time() - start_time
        
        # Get performance stats
        perf_stats = PermissionOptimizer.get_performance_stats(request_obj)
        
        # Debug cache status
        cache_debug = {
            'permission_cache': len(getattr(request_obj, '_permission_result_cache', {})),
            'group_cache': len(getattr(request_obj, '_group_users_cache', {})),
            'user_cache': len(getattr(request_obj, '_user_group_cache', {})),
            'has_permission_cache': hasattr(request_obj, '_permission_result_cache'),
            'has_group_cache': hasattr(request_obj, '_group_users_cache'),
            'has_user_cache': hasattr(request_obj, '_user_group_cache')
        }
        
        return {
            'username': username,
            'total_time': total_time * 1000,
            'list_time': list_time * 1000,
            'schema_time': schema_time * 1000,
            'record_count': len(orders_list),
            'cache_entries': perf_stats.get('cache_entries', 0),
            'operations_count': perf_stats.get('operations_count', 0),
            'cache_debug': cache_debug
        }

    def handle(self, *args, **options):
        print("=" * 50)
        print("🚀 ULTRA SIMPLE PERFORMANCE TEST")
        print("=" * 50)
        
        # Test both users
        son_result = self.test_user('son')
        anyang_result = self.test_user('anyang03')
        
        if son_result and anyang_result:
            print(f"\n👑 SUPERUSER (son): {son_result['total_time']:.1f}ms")
            print(f"   List: {son_result['list_time']:.1f}ms")
            print(f"   Schema: {son_result['schema_time']:.1f}ms")
            print(f"   Records: {son_result['record_count']}")
            print(f"   Cache entries: {son_result['cache_entries']}")
            print(f"   Cache debug: {son_result['cache_debug']}")
            
            print(f"\n👤 NORMAL USER (anyang03): {anyang_result['total_time']:.1f}ms")
            print(f"   List: {anyang_result['list_time']:.1f}ms")
            print(f"   Schema: {anyang_result['schema_time']:.1f}ms")
            print(f"   Records: {anyang_result['record_count']}")
            print(f"   Cache entries: {anyang_result['cache_entries']}")
            print(f"   Cache debug: {anyang_result['cache_debug']}")
            
            ratio = anyang_result['total_time'] / son_result['total_time']
            list_ratio = anyang_result['list_time'] / son_result['list_time']
            schema_ratio = anyang_result['schema_time'] / son_result['schema_time']
            
            print(f"\n📊 PERFORMANCE RATIO:")
            print(f"   Total: {ratio:.2f}x slower")
            print(f"   List: {list_ratio:.2f}x slower")
            print(f"   Schema: {schema_ratio:.2f}x slower")
            
            if list_ratio > schema_ratio:
                print(f"\n🚨 MAIN BOTTLENECK: QuerySet to List conversion")
            else:
                print(f"\n🚨 MAIN BOTTLENECK: Schema processing")
                
        print("\n" + "=" * 50)
