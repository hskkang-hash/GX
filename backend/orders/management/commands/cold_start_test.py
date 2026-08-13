"""
COLD START Performance Test - Exact API Logic

This test:
1. Clears ALL caches before each run
2. Uses EXACT same logic as list_orders API
3. Passes QUERYSET (not list) to schema
4. Measures real cold-start performance
"""
import time
import gc
import os
import subprocess
import sys

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Subquery, OuterRef, Value, CharField, F, Case, When
from django.db.models.expressions import RawSQL
from django.db.models.functions import Concat, Coalesce
from django.db import connection, reset_queries, connections
from django.conf import settings
from django.core.cache import cache

from orders.models import Order, OrderHistory
from orders.schemas.schemas_djantic_out import OrderListOutSchema
from delivery.services.status_mapping_service import StatusMappingService
from core.middleware.refresh_token import thread_local, get_current_request
from core.common.search.dynamic_search import apply_dynamic_filters


def clear_all_caches():
    """Clear ALL caches to simulate cold start"""
    print("🧊 Clearing all caches...")
    
    # 1. Clear Django cache
    try:
        cache.clear()
        print("   ✓ Django cache cleared")
    except Exception as e:
        print(f"   ✗ Django cache: {e}")
    
    # 2. Close all DB connections
    try:
        for conn in connections.all():
            conn.close()
        print("   ✓ DB connections closed")
    except Exception as e:
        print(f"   ✗ DB connections: {e}")
    
    # 3. Clear request-level caches
    try:
        request = getattr(thread_local, 'request', None)
        if request:
            for attr in list(vars(request).keys()):
                if attr.startswith('_') and 'cache' in attr.lower():
                    delattr(request, attr)
        print("   ✓ Request caches cleared")
    except Exception as e:
        print(f"   ✗ Request caches: {e}")
    
    # 4. Force garbage collection
    gc.collect()
    print("   ✓ Garbage collected")
    
    print("🧊 Cache clearing complete\n")


def setup_request(username):
    """Setup mock request - same as real API"""
    User = get_user_model()
    
    # Simulate fresh user fetch (no cache)
    user = User.objects.select_related('language').get(username=username)
    
    class MockRequest:
        def __init__(self, user):
            self.user = user
            self.GET = {}
            self.META = {'REMOTE_ADDR': '127.0.0.1'}
            self.method = 'GET'
            # Note: NO pre-initialized caches - simulates cold start
    
    request_obj = MockRequest(user)
    thread_local.request = request_obj
    
    return request_obj, user


def exact_list_orders_logic(request, page_size=25, current_page=1):
    """
    EXACT COPY of list_orders API logic
    
    This is copied directly from order_views.py lines 606-858
    to ensure we're testing the same code path.
    """
    timing = {}
    
    t0 = time.perf_counter()
    print("[ORDER] ---- start list_orders (COLD) ----")
    
    # Get mapping annotations for Order context
    mapping_annotations = StatusMappingService.build_annotate_with_mapping(context='order')
    exclude_fields = []
    language = request.user.language.code if request.user.language else 'en'
    status_codes = ['delivered', 'pending_confirmation', 'awaiting_shipment', 'cancelled', 'pending_processing', 'awaiting_payment', 'returned']
    
    t1 = time.perf_counter()
    timing['preprocess'] = (t1 - t0) * 1000
    print(f"[ORDER] preprocess params:          {timing['preprocess']:.4f}ms")
    
    # Get base queryset with annotations - EXACT COPY
    orders_queryset = Order.objects.annotate(
        item_count=Count('items', distinct=True),
        # Cancel information using subqueries
        cancel_time=Subquery(
            OrderHistory.objects.filter(
                order=OuterRef('pk'),
                action='cancelled'
            ).values('created_on')[:1]
        ),
       
        cancelled_by__name=Coalesce(
            # Lấy từ action 'cancelled' trước
            Subquery(
                OrderHistory.objects.filter(
                    order=OuterRef('pk'),
                    action='cancelled'
                ).values('created_by__first_name')[:1]
            ),
            # Nếu không có thì lấy từ action 'receipt_cancelled'
            Subquery(
                OrderHistory.objects.filter(
                    order=OuterRef('pk'),
                    action='receipt_cancelled'
                ).values('created_by__first_name')[:1]
            ),
            # Cuối cùng là None
            Value(None),
            output_field=CharField()
        ),
        
        delivered_time=Subquery(
            OrderHistory.objects.filter(
                order=OuterRef('pk'),
                action='delivered'
            ).values('created_on')[:1]
        ), 
        returned_time = Subquery(
            OrderHistory.objects.filter(
                order=OuterRef('pk'),
                action='returned'
            ).values('created_on')[:1]
        ),
        refunded_on=Subquery(
            OrderHistory.objects.filter(
                order=OuterRef('pk'),
                action='refunded'
            ).values('created_on')[:1]
        ), 
        origin=Concat( 
            Coalesce(F('pickup_location__name'), Value(''), output_field=CharField()),
            Value(' ('),
            Coalesce(F('pickup_location__street_address'), Value(''), output_field=CharField()),
            Case(
                When(pickup_location__street_address__isnull=False, then=Value(', ')),
                default=Value(''),
                output_field=CharField()
            ),
            Coalesce(F('pickup_location__ward_town_township'), Value(''), output_field=CharField()),
            Case(
                When(pickup_location__ward_town_township__isnull=False, then=Value(', ')),
                default=Value(''),
                output_field=CharField()
            ),
            Coalesce(F('pickup_location__city_county_district'), Value(''), output_field=CharField()),
            Case(
                When(pickup_location__city_county_district__isnull=False, then=Value(', ')),
                default=Value(''),
                output_field=CharField()
            ),
            Coalesce(F('pickup_location__city_province'), Value(''), output_field=CharField()),
            Value(')'),
            output_field=CharField()
        ),
        
        # Destination (recipient_address or delivery_terminal) with null handling
        destination=Case(
            When(
                delivery_option__code="delivery_to_door",
                then=Coalesce(F('recipient_address__full_address'), Value(''), output_field=CharField())
            ),
            When(
                delivery_option__code="collect_at_location",
                then=Concat(
                    Coalesce(F('delivery_terminal__name'), Value(''), output_field=CharField()),
                    Value(' ('),
                    Coalesce(F('delivery_terminal__street_address'), Value(''), output_field=CharField()),
                    Case(
                        When(delivery_terminal__street_address__isnull=False, then=Value(', ')),
                        default=Value(''),
                        output_field=CharField()
                    ),
                    Coalesce(F('delivery_terminal__ward_town_township'), Value(''), output_field=CharField()),
                    Case(
                        When(delivery_terminal__ward_town_township__isnull=False, then=Value(', ')),
                        default=Value(''),
                        output_field=CharField()
                    ),
                    Coalesce(F('delivery_terminal__city_county_district'), Value(''), output_field=CharField()),
                    Case(
                        When(delivery_terminal__city_county_district__isnull=False, then=Value(', ')),
                        default=Value(''),
                        output_field=CharField()
                    ),
                    Coalesce(F('delivery_terminal__city_province'), Value(''), output_field=CharField()),
                    Value(')'),
                    output_field=CharField()
                )
            ),
            default=Value('N/A'), 
            output_field=CharField()
        ),
        
        # Delivery address formatted 
        delivery_address_formatted=Concat(
            F('recipient_address__full_address'),
            Value(' ('),
            F('delivery_terminal__name'),
            Value(')'),
            output_field=CharField()
        ),
        
        # Pickup location formatted 
        pickup_location_formatted=Concat(
            F('pickup_location__name'),
            Value(' ('),
            F('pickup_location__street_address'),
            Value(', '),
            F('pickup_location__ward_town_township'),
            Value(', '),
            F('pickup_location__city_county_district'),
            Value(', '),
            F('pickup_location__city_province'),
            Value(')'),
            output_field=CharField()
        ),
        # add receipt code if order.another_info.etri.receipt_id is exist
        receipt_code=RawSQL("(orders_order.another_info -> 'etri' ->> 'receipt_id')", []),

        # Use dynamic mapping annotations for Order context
        **mapping_annotations
    ).select_related(
        'status',
        'created_by',
        'delivery_operation',
        'delivery_operation__current_status'
    ).prefetch_related(
        'items',
        'items__item_type',
        'items__products',
        'items__assignments',
        'items__assignments__device',
        'histories',
        'histories__created_by',
        'payments',
        'payments__payment_type',
        'comments',
        'created_by__userprofilelink__group'
    ).order_by('-modified_on')
    
    t2 = time.perf_counter()
    timing['build_queryset'] = (t2 - t1) * 1000
    print(f"[ORDER] build base queryset:        {timing['build_queryset']:.4f}ms")
    
    orders_queryset = orders_queryset.filter(
        status__code__in=status_codes, 
        delivery_operation__another_info__etri__isnull=True
    )
    
    t3 = time.perf_counter()
    timing['base_filters'] = (t3 - t2) * 1000
    print(f"[ORDER] apply base filters:         {timing['base_filters']:.4f}ms")

    t3a = time.perf_counter()
    orders_queryset = apply_dynamic_filters(orders_queryset, request, exclude_fields, request.GET.get('sort_obj', None))
    t4 = time.perf_counter()
    timing['dynamic_filters'] = (t4 - t3a) * 1000
    print(f"[ORDER] apply_dynamic_filters:      {timing['dynamic_filters']:.4f}ms")
    
    # Track queries for pagination
    reset_queries()
    
    paginator = Paginator(orders_queryset, page_size)
    pages = paginator.page(current_page)
    
    t5 = time.perf_counter()
    timing['pagination'] = (t5 - t4) * 1000
    pagination_queries = len(connection.queries)
    print(f"[ORDER] pagination (COUNT+SELECT):  {timing['pagination']:.4f}ms ({pagination_queries} queries)")
    
    # Show pagination queries
    if pagination_queries > 0:
        print("        Pagination queries:")
        for i, q in enumerate(connection.queries):
            sql = q['sql'][:100] + '...' if len(q['sql']) > 100 else q['sql']
            print(f"          Q{i+1} ({q['time']}s): {sql}")
    
    # KEY: Pass pages.object_list (QUERYSET) to schema, NOT list
    reset_queries()
    
    # This is the exact call from the API
    orders_data = OrderListOutSchema.from_queryset(pages.object_list, many=True)
    
    t6 = time.perf_counter()
    timing['schema'] = (t6 - t5) * 1000
    schema_queries = len(connection.queries)
    print(f"[ORDER] schema.from_queryset:       {timing['schema']:.4f}ms ({schema_queries} queries)")
    
    # Show schema queries if any
    if schema_queries > 0:
        print("        Schema queries:")
        for i, q in enumerate(connection.queries[:20]):
            sql = q['sql'][:100] + '...' if len(q['sql']) > 100 else q['sql']
            print(f"          Q{i+1} ({q['time']}s): {sql}")
        if schema_queries > 20:
            print(f"          ... and {schema_queries - 20} more queries")
    
    t7 = time.perf_counter()
    timing['total'] = (t7 - t0) * 1000
    print(f"[ORDER] total (before return):      {timing['total']:.4f}ms")
    print("[ORDER] ---- end list_orders ----")
    
    return {
        'timing': timing,
        'total_items': paginator.count,
        'page_items': len(orders_data) if isinstance(orders_data, list) else 'N/A',
        'queries': {
            'pagination': pagination_queries,
            'schema': schema_queries,
        },
        'data': orders_data
    }


def run_in_new_process(username, page_size, current_page):
    """Run test in a completely fresh Python process"""
    script = f'''
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from orders.management.commands.cold_start_test import setup_request, exact_list_orders_logic, clear_all_caches

clear_all_caches()
request, user = setup_request("{username}")
result = exact_list_orders_logic(request, page_size={page_size}, current_page={current_page})
print(f"\\n=== RESULT ===")
print(f"Total: {{result['timing']['total']:.2f}}ms")
'''
    
    result = subprocess.run(
        [sys.executable, '-c', script],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[:500])


class Command(BaseCommand):
    help = 'Cold start performance test with exact API logic'

    def add_arguments(self, parser):
        parser.add_argument('--page-size', type=int, default=25)
        parser.add_argument('--page', type=int, default=1)
        parser.add_argument('--username', type=str, default='son')
        parser.add_argument('--fresh-process', action='store_true',
                          help='Run in a completely fresh Python process')
        parser.add_argument('--iterations', type=int, default=1)

    def handle(self, *args, **options):
        page_size = options['page_size']
        current_page = options['page']
        username = options['username']
        fresh_process = options['fresh_process']
        iterations = options['iterations']
        
        old_debug = settings.DEBUG
        settings.DEBUG = True
        
        print("=" * 70)
        print("🧊 COLD START PERFORMANCE TEST - Exact API Logic")
        print("=" * 70)
        print(f"   User: {username}")
        print(f"   Page size: {page_size}")
        print(f"   Page: {current_page}")
        print(f"   Fresh process: {fresh_process}")
        print(f"   Iterations: {iterations}")
        print("=" * 70)
        
        if fresh_process:
            print("\n🚀 Running in fresh Python process...")
            run_in_new_process(username, page_size, current_page)
        else:
            all_results = []
            
            for i in range(iterations):
                print(f"\n{'='*60}")
                print(f"📍 ITERATION {i+1}/{iterations}")
                print(f"{'='*60}")
                
                # Clear caches before each iteration
                clear_all_caches()
                
                # Setup request
                request, user = setup_request(username)
                print(f"✅ User: {user.username} (superuser={user.is_superuser})")
                
                # Run test
                result = exact_list_orders_logic(
                    request,
                    page_size=page_size,
                    current_page=current_page
                )
                
                all_results.append(result)
                
                print(f"\n📊 Items: {result['page_items']}/{result['total_items']}")
            
            # Summary
            if len(all_results) > 1:
                print("\n" + "=" * 70)
                print("📈 COLD START SUMMARY")
                print("=" * 70)
                
                totals = [r['timing']['total'] for r in all_results]
                print(f"   Run 1 (coldest): {totals[0]:.2f}ms")
                if len(totals) > 1:
                    print(f"   Run 2:           {totals[1]:.2f}ms")
                if len(totals) > 2:
                    print(f"   Run 3+:          {sum(totals[2:])/len(totals[2:]):.2f}ms (avg)")
                
                print(f"\n   Cold vs Warm delta: {totals[0] - totals[-1]:.2f}ms")
            else:
                print("\n" + "=" * 70)
                print(f"🧊 COLD START RESULT: {all_results[0]['timing']['total']:.2f}ms")
                print("=" * 70)
                
                # Breakdown
                t = all_results[0]['timing']
                print("\n📊 Breakdown:")
                for key, value in t.items():
                    if key != 'total':
                        pct = value / t['total'] * 100
                        bar = '█' * int(pct / 2)
                        print(f"   {key:20s}: {value:8.2f}ms ({pct:5.1f}%) {bar}")
                
                print(f"\n   {'TOTAL':20s}: {t['total']:8.2f}ms")
        
        settings.DEBUG = old_debug
        
        print("\n" + "=" * 70)
        print("✅ Cold start test completed!")
        print("=" * 70)

