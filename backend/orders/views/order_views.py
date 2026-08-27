from datetime import timezone
import json

from django.db.models.fields import DateTimeField
from orders.services.order_service import OrderService
from terminals.schemas.schemas_djantic_out import TerminalOutSchema
from devices.utils import sort_terminal_by_address
from terminals.services import terminal_service
from delivery.models import DeliveryCancellation, DeliveryOperation, DeliveryReturn
from orders.utils import get_order_message, is_date_outdated
from devices.models import PackagingSpecification
from orders.models import Bank, DeliveryOption, Order, OrderHistory, OrderItem, Payment
from devices.services.packaging_service import PackagingSpecificationService
from ninja_extra import api_controller, route
from core.role.permission import permission_required, path_permission
from ninja.errors import ValidationError
from common.pagination import OptimizedPaginator
from django.db.models.expressions import RawSQL
from core.common.base_response import BaseResponse
from common.tenant_filters import assert_scoped
from django.db.models import (
    QuerySet,
    Count,
    OuterRef,
    Subquery,
    F,
    CharField,
    Value,
    Q,
    Case,
    When,
    Prefetch,
)
from orders.schemas.schemas_djantic_in import OrderCreateSchema, OrderCancelSchema, OrderRefundSchema
from orders.schemas.schemas_djantic_out import OrderDetailOutSchema, OrderHistoryOutSchema, OrderItemOutSchema, OrderListOutSchema, DeliveryOptionOutSchema, BankOutSchema, RefundOrderOutSchema
from common.constant import MESSAGE_ENUM, get_message
from core.middleware.refresh_token import get_current_request
from django.db.models.functions import Concat, Coalesce
from core.common.search.dynamic_search import apply_dynamic_filters
from core.api.v1.auth import CustomJWTAuth
from delivery.services.status_mapping_service import StatusMappingService
from core.user.services.usergroup_service import UserGroupService

# Status color mapping dictionary
STATUS_COLOR_MAPPING = {
    'unverified_order': '#9C9D9D',
    'verified_order': '#1D9BE2',
    'select_route_processing': '#1E90FF',
    'select_drone_processing': '#4682B4',
    'in_transit_processing': '#6495ED',
    'arrived_order': '#EB7509',
    'completed_order': '#0CBA47',
    'order_due_for_returned': '#414DAD',
    'order_pending_returned': '#F0C418',
    'overdue_order': '#683DE2',
    'returned_order': '#1D9BE2',
    'processed_order': '#9C9D9D',
    'cancelled': '#EE533D',

}

@api_controller('/order', tags=['Order'])
class OrderAPI:
    @route.get('/map-status', url_name='map_status', auth=CustomJWTAuth())
    @path_permission("read", path_override=['/order', '/etri-order'])
    def map_status(self, request):
        """
        Map status
        """
        language = get_current_request().user.language.code if get_current_request().user.language else 'en'
        STATUS_MAPPING = [
            'Receipt Completed' if language == 'en' else '접수완료' if language == 'ko' else 'ใบเสร็จสมบูรณ์',
            'Delivery Cancelled' if language == 'en' else '배송취소' if language == 'ko' else 'การจัดส่งถูกยกเลิก',
            'Waiting for Delivery' if language == 'en' else '배송대기' if language == 'ko' else 'รอการจัดส่ง',
            'In Delivery' if language == 'en' else '배송중' if language == 'ko' else 'กำลังจัดส่ง',
            'Delivery Completed' if language == 'en' else '배송완료' if language == 'ko' else 'การจัดส่งเสร็จสมบูรณ์',
            'Receipt Cancelled' if language == 'en' else '접수취소' if language == 'ko' else 'การรับถูกยกเลิก',
        ]
        return BaseResponse(
            status_code=200,
            message="Status mapped successfully",
            data=STATUS_MAPPING
        )

    @route.get('/etri-order', url_name='etri_order', auth=CustomJWTAuth())
    @path_permission("read", path_override=['/order', '/etri-order','/delivery-operation'])
    def list_etri_orders(
        self,
        request,
        page_size: int = 10,
        current_page: int = 1,
        sort_obj: object = None,
        item_count: int = None,
        created_on_start: str = None,
        created_on_end: str = None,
        mapped_status: str = None,
        receipt_code: str = None
    ):
        """
        Get paginated list of orders with optional filtering and sorting

        Parameters:
        - page_size: Number of items per page
        - current_page: Current page number
        - sort_obj: JSON string for sorting (e.g. {"field": "created_on", "order": "desc"})
        - search: Search term for filtering orders
        - order_status: Filter by order status code
        - start_date: Filter orders created after this date (YYYY-MM-DD)
        - end_date: Filter orders created before this date (YYYY-MM-DD)
        """
        status_codes = ['delivered', 'pending_confirmation', 'awaiting_shipment', 'cancelled', 'pending_processing', 'awaiting_payment', 'returned']
        if request.GET.get('status_codes'):
            status_codes = [status_code for status_code in status_codes if status_code in request.GET.get('status_codes')]

        # Convert string parameters if provided
        page_size = int(request.GET.get('page_size', page_size))
        current_page = int(request.GET.get('current_page', current_page))
        exclude_fields = []
        sort_obj = request.GET.get('sort_obj', sort_obj)

        language = get_current_request().user.language.code if get_current_request().user.language else 'en'
        STATUS_MAPPING = {
            'unverified_order': 'Receipt Completed' if language == 'en' else '접수완료' if language == 'ko' else 'ใบเสร็จสมบูรณ์',
            'cancelled': 'Delivery Cancelled' if language == 'en' else '배송취소' if language == 'ko' else 'การจัดส่งถูกยกเลิก',
            'overdue_order': 'Delivery Cancelled' if language == 'en' else '배송취소' if language == 'ko' else 'การจัดส่งถูกยกเลิก',
            'returned_order': 'Delivery Cancelled' if language == 'en' else '배송취소' if language == 'ko' else 'การจัดส่งถูกยกเลิก',
            'processed_order': 'Delivery Cancelled' if language == 'en' else '배송취소' if language == 'ko' else 'การจัดส่งถูกยกเลิก',
            'order_pending_returned': 'Delivery Cancelled' if language == 'en' else '배송취소' if language == 'ko' else 'การจัดส่งถูกยกเลิก',
            'order_due_for_returned': 'Delivery Cancelled' if language == 'en' else '배송취소' if language == 'ko' else 'การจัดส่งถูกยกเลิก',
            'select_route_processing': 'Waiting for Delivery' if language == 'en' else '배송대기' if language == 'ko' else 'รอการจัดส่ง',
            'select_drone_processing': 'Waiting for Delivery' if language == 'en' else '배송대기' if language == 'ko' else 'รอการจัดส่ง',
            'in_transit_processing': 'In Delivery' if language == 'en' else '배송중' if language == 'ko' else 'กำลังจัดส่ง',
            'completed_order': 'Delivery Completed' if language == 'en' else '배송완료' if language == 'ko' else 'การจัดส่งเสร็จสมบูรณ์',
            'arrived_order': 'Delivery Completed' if language == 'en' else '배송 완료' if language == 'ko' else 'การจัดส่งเสร็จสมบูรณ์',  # Also map arrived to shipped
            'verified_order': 'Receipt Completed' if language == 'en' else '접수완료' if language == 'ko' else 'ใบเสร็จสมบูรณ์',  # Map verified to received as well
            'receipt_cancelled': 'Receipt Cancelled' if language == 'en' else '접수취소' if language == 'ko' else 'การรับถูกยกเลิก',
        }

        STATUS_MAPPING_COLOR = {
            'unverified_order': '#9C9D9D',
            'cancelled': '#EE533D',
            'overdue_order': '#EE533D',
            'returned_order': '#EE533D',
            'processed_order': '#EE533D',
            'order_pending_returned': '#EE533D',
            'order_due_for_returned': '#EE533D',
            'select_route_processing': '#1E90FF',
            'select_drone_processing': '#1E90FF',
            'in_transit_processing': '#6495ED',
            'completed_order': '#0CBA47',
            'arrived_order': '#EB7509',
        }

        # Get base queryset with annotations
        orders_queryset = Order.objects.annotate(

            item_count=Count('items', distinct=True),

            # Cancel information using subqueries
            cancel_time=Subquery(
                OrderHistory.objects.filter(
                    order=OuterRef('pk'),
                    action='cancelled'
                ).values('created_on')[:1]
            ),

            cancelled_by_first_name=Subquery(
                OrderHistory.objects.filter(
                    order=OuterRef('pk'),
                    action='cancelled'
                ).values('created_by__first_name')[:1]
            ),

            # Refund information using subquery
            refunded_time=Subquery(
                OrderHistory.objects.filter(
                    order=OuterRef('pk'),
                    action='refunded'
                ).values('created_on')[:1]
            ),
            delivered_time = Subquery(
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
            # add receipt code if order.another_info.etri.receipt_id is exist
            receipt_code=RawSQL("(orders_order.another_info -> 'etri' ->> 'receipt_id')", []),

            # add mapped_status
            mapped_status=Case(
                *[When(
                    delivery_operation__current_status__code=code,
                    then=Value(mapped_status)
                ) for code, mapped_status in STATUS_MAPPING.items()],
                default=Value('Unknown'),
                output_field=CharField()
            ),

            # add mapped_status_color
            mapped_status_color=Case(
                *[When(
                    delivery_operation__current_status__code=code,
                    then=Value(STATUS_MAPPING_COLOR[code])
                ) for code in STATUS_MAPPING_COLOR.keys()],
                default=Value('#9C9D9D'),
                output_field=CharField()
            ),
            sender_address__full_address = F('sender_address__full_address'),
            recipient_address__full_address = F('recipient_address__full_address'),


        ).select_related(
            'status',
            'created_by'
        ).prefetch_related(
            'items',
            'histories'
        ).order_by('-modified_on')
        orders_queryset = orders_queryset.filter(status__code__in=status_codes, delivery_operation__another_info__etri__isnull=False)

        if request.GET.get('mapped_status'):
            orders_queryset = orders_queryset.filter(mapped_status=request.GET.get('mapped_status'))

        if request.GET.get('receipt_code'):
            orders_queryset = orders_queryset.filter(receipt_code__icontains=request.GET.get('receipt_code'))

        orders_queryset = apply_dynamic_filters(orders_queryset, request, exclude_fields, request.GET.get('sort_obj', None))
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(orders_queryset, page_size)
        pages = paginator.page(current_page)

        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_ORDER_SUCCESS),
            data=OrderListOutSchema.from_queryset(pages.object_list, many=True) ,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page,
        )


    @route.get('/etri-order-detail', url_name='etri_order_detail', auth=CustomJWTAuth())
    @path_permission("read", path_override=['/order', '/etri-order','/delivery-operation','/etri-tracking'])
    def get_etri_order(self, request, id: int):
        """
        Get detailed information about a specific order

        Parameters:
        - id: The order ID to retrieve
        """
        language = get_current_request().user.language.code if get_current_request().user.language else 'en'

        STATUS_MAPPING = {
            # Primary status mappings using existing codes
            'delivered': 'Delivery Completed' if language == 'en' else '배송완료' if language == 'ko' else 'การจัดส่งเสร็จสมบูรณ์',  # Status 0
            'cancelled': 'Delivery Cancelled' if language == 'en' else '배송취소' if language == 'ko' else 'การจัดส่งถูกยกเลิก',  # Status 1
            'in_transit_processing': 'In Delivery' if language == 'en' else '배송중' if language == 'ko' else 'กำลังจัดส่ง',  # Status 2
            'awaiting_shipment': 'Waiting for Delivery' if language == 'en' else '배송대기' if language == 'ko' else 'รอการจัดส่ง',  # Status 3
            'pending_confirmation': 'Receipt Completed' if language == 'en' else '접수완료' if language == 'ko' else 'ใบเสร็จสมบูรณ์',  # Status 4
            'receipt_cancelled': 'Receipt Cancelled' if language == 'en' else '접수취소' if language == 'ko' else 'การรับถูกยกเลิก',  # Status 5

            # Legacy mappings for backward compatibility
            'unverified_order': 'Received' if language == 'en' else '접수완료' if language == 'ko' else 'ใบเสร็จสมบูรณ์',  # Maps to Status 4
            'verified_order': 'Waiting for Delivery' if language == 'en' else '배송대기' if language == 'ko' else 'รอการจัดส่ง',  # Maps to Status 3
            'select_route_processing': 'Waiting for Delivery' if language == 'en' else '배송대기' if language == 'ko' else 'รอการจัดส่ง',  # Maps to Status 3
            'select_drone_processing': 'Waiting for Delivery' if language == 'en' else '배송대기' if language == 'ko' else 'รอการจัดส่ง',  # Maps to Status 3
            'completed_order': 'Delivery Completed' if language == 'en' else '배송완료' if language == 'ko' else 'การจัดส่งเสร็จสมบูรณ์',  # Maps to Status 0
            'arrived_order': 'Delivery Completed' if language == 'en' else '배송완료' if language == 'ko' else 'การจัดส่งเสร็จสมบูรณ์',  # Maps to Status 0
            'returned': 'Delivery Cancelled' if language == 'en' else '배송취소' if language == 'ko' else 'การจัดส่งถูกยกเลิก',
        }

        # Build comprehensive query with all needed data
        order = Order.objects.annotate(
            # Payment status
            payment_status=Case(
                When(
                    payments__isnull=False,
                    then=Subquery(
                        Payment.objects.filter(order=OuterRef('pk')).values('status')[:1]
                    )
                ),
                default=Value('failed'),
                output_field=CharField()
            ),

            # Various timestamps
            verified_time=Subquery(
                OrderHistory._base_manager.filter(
                    order=OuterRef('pk'),
                    action='verified'
                ).values('created_on')[:1]
            ),
            cancel_time=Subquery(
                OrderHistory._base_manager.filter(
                    order=OuterRef('pk'),
                    action='cancelled'
                ).values('created_on')[:1]
            ),
            arrived_time=Subquery(
                OrderHistory._base_manager.filter(
                    order=OuterRef('pk'),
                    action='arrived'
                ).values('created_on')[:1]
            ),
            refunded_time=Subquery(
                OrderHistory._base_manager.filter(
                    order=OuterRef('pk'),
                    action='refunded'
                ).values('created_on')[:1]
            ),
            returned_time=Subquery(
                OrderHistory._base_manager.filter(
                    order=OuterRef('pk'),
                    action='returned'
                ).values('created_on')[:1]
            ),
            paid_time=Subquery(
                OrderHistory._base_manager.filter(
                    order=OuterRef('pk'),
                    action='paid'
                ).values('created_on')[:1]
            ),
            completed_time=Subquery(
                OrderHistory._base_manager.filter(
                    order=OuterRef('pk'),
                    action='completed'
                ).values('created_on')[:1]
            ),
            delivered_time=Subquery(
                OrderHistory._base_manager.filter(
                    order=OuterRef('pk'),
                    action='delivered'
                ).values('created_on')[:1]
            ),
            return_received_time=Subquery(
                DeliveryOperation.objects.filter(
                    order=OuterRef('pk')
                ).values('status_history__changed_at')[:1]
            ),

            # Address info with ORM formatting
            recipient_address_full=F('recipient_address__full_address'),

            # Pickup location formatted address
            pickup_location_formatted=Case(
                When(
                    pickup_location__isnull=False,
                    then=Concat(
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
                    )
                ),
                default=Value(None),
                output_field=CharField()
            ),

            # Delivery address based on option
            delivery_address_formatted=Case(
                When(
                    delivery_option__code='collect_at_location',
                    then=Case(
                        When(
                            delivery_terminal__isnull=False,
                                                    then=Concat(
                            F('delivery_terminal__name'),
                            Value(' ('),
                            F('delivery_terminal__street_address'),
                            Value(', '),
                            F('delivery_terminal__ward_town_township'),
                            Value(', '),
                            F('delivery_terminal__city_county_district'),
                            Value(', '),
                            F('delivery_terminal__city_province'),
                            Value(')'),
                            output_field=CharField()
                        )
                        ),
                        default=Value(None),
                        output_field=CharField()
                    )
                ),
                When(
                    delivery_option__code='delivery_to_door',
                    then=F('recipient_address__full_address')
                ),
                default=Value(None),
                output_field=CharField()
            ),

            # Transferred terminal formatted address
            transferred_terminal_formatted=Subquery(
                DeliveryReturn.objects.filter(
                    delivery_operation__order=OuterRef('pk'),
                    return_terminal__isnull=False
                ).annotate(
                    formatted_address=Concat(
                        F('return_terminal__name'),
                        Value(' ('),
                        F('return_terminal__street_address'),
                        Value(', '),
                        F('return_terminal__ward_town_township'),
                        Value(', '),
                        F('return_terminal__city_county_district'),
                        Value(', '),
                        F('return_terminal__city_province'),
                        Value(')'),
                        output_field=CharField()
                    )
                ).values('formatted_address')[:1]
            ),

            # Route ID
            route=Subquery(
                DeliveryOperation.objects.filter(
                    order=OuterRef('pk')
                ).values('route_id')[:1]
            ),

            # Mapped status based on delivery operation
            mapped_status_code=Subquery(
                DeliveryOperation.objects.filter(
                    order=OuterRef('pk')
                ).values('current_status__code')[:1]
            )

        ).select_related(
            'status',
            'created_by',
            'recipient_address',
            'pickup_location',
            'delivery_terminal',
            'delivery_option',
            'delivery_operation',
            'delivery_operation__current_status',
            'delivery_operation__route'
        ).prefetch_related(
            'items',
            'items__item_type',
            'items__assignments',
            'items__assignments__events',
            'items__assignments__events__terminal_stop',
            'histories',
            'payments',
            'payments__payment_type',
            'delivery_operation__status_history',
            'delivery_operation__status_history__status'
        ).get(id=id)

        # Get order data using schema
        order_data = OrderDetailOutSchema.from_queryset(order, many=False)

        # Add items using schema
        items_data = []
        for item in order.items.all():
            item_data = OrderItemOutSchema.from_queryset(item, many=False)
            items_data.append(item_data)
        order_data['items'] = items_data

        # All fields including history and delivery_events are handled by schema and ORM

        # Financial summary is handled by DynamicSchema automatically

        # Add complex business logic fields that require custom processing

        # Add mapped_status using ORM data
        if hasattr(order, 'delivery_operation') and order.delivery_operation and order.delivery_operation.current_status:
            mapped_status = order.delivery_operation.current_status
            order_data['mapped_status'] = {
                'id': mapped_status.id,
                'name': STATUS_MAPPING.get(mapped_status.code, 'Unknown'),
                'code': mapped_status.code,
                'description': mapped_status.get_translation('description', language),
                'color_code': STATUS_COLOR_MAPPING.get(mapped_status.code, '#9C9D9D')
            }
        else:
            order_data['mapped_status'] = None

        # Add delivery_status using ORM data
        if hasattr(order, 'delivery_operation') and order.delivery_operation and order.delivery_operation.current_status:
            order_data['delivery_status'] = {
                'id': order.delivery_operation.current_status.id,
                'name': order.delivery_operation.current_status.get_translation('name', language),
                'code': order.delivery_operation.current_status.code,
                'description': order.delivery_operation.current_status.get_translation('description', language),
                'color_code': order.delivery_operation.current_status.color_code
            }
        else:
            order_data['delivery_status'] = {
                'id': None,
                'name': None,
                'code': None,
                'description': None,
                'color_code': None
            }

        # Add payment_details using prefetched data
        payment = order.payments.first() if order.payments.exists() else None
        if payment:
            order_data['payment_details'] = {
                'id': payment.id,
                'payment_method': payment.payment_type.get_translation('name', language),
                'payment_method_code': payment.payment_type.code,
                'amount': str(payment.amount) if payment.amount else None,
                'currency': payment.amount.currency_symbol if payment.amount else None
            }
        else:
            order_data['payment_details'] = {
                'id': None,
                'payment_method': None,
                'payment_method_code': None,
                'amount': None,
                'currency': None
            }

        # Add history using prefetched data
        order_data['history'] = [
            {
                'id': history.id,
                'action': history.action,
                'description': history.get_translation('description', language),
                'created_on': history.created_on
            }
            for history in order.histories.all().order_by('id')
        ]

        # Add delivery_events using prefetched data
        delivery_events = []
        for item in order.items.all():
            for assignment in item.assignments.all():
                for event in assignment.events.all():
                    if event.terminal_stop:
                        delivery_events.append({
                            'package_id': item.id,
                            'id': event.id,
                            'event_type': event.event_type,
                            'description': event.description,
                            'lat': event.lat,
                            'lng': event.lng,
                            'terminal_stop': event.terminal_stop.name,
                            'created_on': event.created_on
                        })
        order_data['delivery_events'] = sorted(delivery_events, key=lambda x: x['created_on'])

        # Add financial_summary using ORM money fields
        order_data['financial_summary'] = {
            'subtotal': {
                'value': float(order.subtotal.raw_amount) if order.subtotal and not order.subtotal.is_null else 0,
                'formatted': str(order.subtotal) if order.subtotal and not order.subtotal.is_null else None,
                'currency_code': order.subtotal.currency_code if order.subtotal else None,
                'currency_symbol': order.subtotal.currency_symbol if order.subtotal else None
            },
            'delivery_fee': {
                'value': float(order.delivery_fee.raw_amount) if order.delivery_fee and not order.delivery_fee.is_null else 0,
                'formatted': str(order.delivery_fee) if order.delivery_fee and not order.delivery_fee.is_null else None,
                'currency_code': order.delivery_fee.currency_code if order.delivery_fee else None,
                'currency_symbol': order.delivery_fee.currency_symbol if order.delivery_fee else None
            },
            'tax_amount': {
                'value': float(order.tax_amount.raw_amount) if order.tax_amount and not order.tax_amount.is_null else 0,
                'formatted': str(order.tax_amount) if order.tax_amount and not order.tax_amount.is_null else None,
                'currency_code': order.tax_amount.currency_code if order.tax_amount else None,
                'currency_symbol': order.tax_amount.currency_symbol if order.tax_amount else None
            },
            'discount_amount': {
                'value': float(order.discount_amount.raw_amount) if order.discount_amount and not order.discount_amount.is_null else 0,
                'formatted': str(order.discount_amount) if order.discount_amount and not order.discount_amount.is_null else None,
                'currency_code': order.discount_amount.currency_code if order.discount_amount else None,
                'currency_symbol': order.discount_amount.currency_symbol if order.discount_amount else None
            },
            'total_amount': {
                'value': float(order.total_amount.raw_amount) if order.total_amount and not order.total_amount.is_null else 0,
                'formatted': str(order.total_amount) if order.total_amount and not order.total_amount.is_null else None,
                'currency_code': order.total_amount.currency_code if order.total_amount else None,
                'currency_symbol': order.total_amount.currency_symbol if order.total_amount else None
            }
        }

        # Add message logic for returned orders
        order_data['message'] = None
        order_data['message_type'] = None
        if order.status.code == 'returned':
            timeout = OrderService.get_returned_order_timeout_no_pickup()
            returned_time = order.returned_time
            if returned_time and is_date_outdated(returned_time, timeout, language):
                order_data['message'] = get_order_message(order.delivery_address_formatted or '', 'en', timeout, True)
                order_data['message_type'] = 'error'
            else:
                order_data['message'] = get_order_message(order.delivery_address_formatted or '', 'en', timeout, False)
                order_data['message_type'] = 'warning'

        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_ORDER_SUCCESS, "Order retrieved successfully"),
            data=order_data
        )
    @route.get('/', url_name='list_orders', auth=CustomJWTAuth())
    @path_permission("read", path_override=['/order', '/etri-order', '/delivery-inquiry'])
    def list_orders(
        self,
        request,
        page_size: int = 10,
        current_page: int = 1,
        sort_obj: object = None,
        item_count: int = None,
        created_on_start: str = None,
        created_on_end: str = None,
        mapped_status: str = None,
        receipt_code: str = None
    ):
        """
        Get paginated list of orders with optional filtering and sorting

        Parameters:
        - page_size: Number of items per page
        - current_page: Current page number
        - sort_obj: JSON string for sorting (e.g. {"field": "created_on", "order": "desc"})
        - search: Search term for filtering orders
        - order_status: Filter by order status code
        - start_date: Filter orders created after this date (YYYY-MM-DD)
        - end_date: Filter orders created before this date (YYYY-MM-DD)
        """
        mapping_annotations = StatusMappingService.build_annotate_with_mapping(context='order')
        exclude_fields = []
        language = request.user.language.code if request.user.language else 'en'
        status_codes = ['delivered', 'pending_confirmation', 'awaiting_shipment', 'cancelled', 'pending_processing', 'awaiting_payment', 'returned']
        if request.GET.get('status_codes'):
            status_codes = [status_code for status_code in status_codes if status_code in request.GET.get('status_codes')]

        # Convert string parameters if provided
        page_size = int(request.GET.get('page_size', page_size))
        current_page = int(request.GET.get('current_page', current_page))
        exclude_fields = []
        sort_obj = request.GET.get('sort_obj', sort_obj)

        language = get_current_request().user.language.code if get_current_request().user.language else 'en'

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

         delivered_time = Subquery(
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
            # 🚀 COMPLETE PREFETCH: All possible related objects to eliminate ALL lazy loading
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
            # Permission system optimization
            'created_by__userprofilelink__group'
        ).order_by('-modified_on')

        orders_queryset = orders_queryset.filter(status__code__in=status_codes, delivery_operation__another_info__etri__isnull=True)

        if request.GET.get('mapped_status'):
            orders_queryset = orders_queryset.filter(mapped_status=request.GET.get('mapped_status'))

        if request.GET.get('receipt_code'):
            orders_queryset = orders_queryset.filter(receipt_code__icontains=request.GET.get('receipt_code'))

        orders_queryset = apply_dynamic_filters(orders_queryset, request, exclude_fields, request.GET.get('sort_obj', None))

        paginator = OptimizedPaginator(orders_queryset, page_size)
        pages = paginator.page(current_page)

        # 🚀 OPTIMIZATION: Extract PKs using values_list to avoid materializing objects
        try:
            if hasattr(pages, 'object_list') and hasattr(pages.object_list, 'values_list'):
                page_pks = list(pages.object_list.values_list('pk', flat=True))
            elif hasattr(pages, 'object_list') and hasattr(pages.object_list, '_result_cache') and pages.object_list._result_cache is not None:
                page_pks = [obj.pk for obj in pages.object_list._result_cache]
            else:
                page_pks = [obj.pk for obj in pages.object_list]
        except Exception:
            page_pks = [obj.pk for obj in pages.object_list]

        schema_data = OrderListOutSchema.from_queryset(
            orders_queryset.filter(pk__in=page_pks),
            many=True,
            request_path='/order',
            query_fields=None,
            page_size=page_size,
            current_page=current_page
        )

        dashboard_refresh_interval, dashboard_auto_refresh = OrderService.get_delivery_inquiry_refresh_config()
        allow_order_in_bad_weather = UserGroupService.get_user_group_settings(request.user.userprofilelink.group.id, 'allow_order_in_bad_weather')

        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=schema_data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page,
            dashboard_refresh_interval=dashboard_refresh_interval,
            dashboard_auto_refresh=dashboard_auto_refresh,
            allow_order_in_bad_weather=allow_order_in_bad_weather['active']
        )

    @route.get('/{id}', url_name='get_order_detail', auth=CustomJWTAuth())
    @path_permission("read", path_override=['/order', '/etri-order', '/etri-tracking', '/delivery-operation', '/delivery-inquiry'])
    def get_order(self, request, id: int):
        """
        Get detailed information about a specific order

        Parameters:
        - id: The order ID to retrieve
        """
        # ★ W0-14c 문지기 (2026-08-28). 이 핸들러에는 try/except 가 없어
        #   `Order.DoesNotExist` 가 그대로 미들웨어까지 올라가 **HTTP 500** 이 된다.
        #   실측: 남의 주문 pk 에 500 — 막힌 것이지만 그 500 은 "막혔다"를 말하지 않는다.
        #   그리고 이 경로는 OrderHistory·Payment·DeliveryOperation 의 **부모 경로**이기도 해서
        #   (D-272 via_parent) 자식 3종의 판정이 전부 이 500 에 걸려 있었다.
        assert_scoped(Order, id, request.user)


        # Get mapping annotations for delivery operation context (used with delivery_operation__ prefix)
        mapping_annotations = StatusMappingService.build_annotate_with_mapping(context='order')

        language = request.user.language.code if request.user.language else 'en'
        latest_cancellation = DeliveryCancellation.objects.filter(
                        delivery_operation__order_id=OuterRef('pk')
                    ).order_by('-id')
        # Get order with mapping annotations through delivery operation
        order = Order.objects.annotate(
            # Origin (pickup_location) with null handling
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

            # Delivery terminal formatted address
            delivery_terminal_formatted=Concat(
                F('delivery_terminal__name'),
                Value(' ('),
                F('delivery_terminal__street_address'),
                Value(', '),
                F('delivery_terminal__ward_town_township'),
                Value(', '),
                F('delivery_terminal__city_county_district'),
                Value(', '),
                F('delivery_terminal__city_province'),
                Value(')'),
                output_field=CharField()
            ),

            # Transferred terminal formatted address
            transferred_terminal_formatted=Subquery(
                DeliveryReturn.objects.filter(
                    delivery_operation__order=OuterRef('pk'),
                    return_terminal__isnull=False
                ).annotate(
                    formatted_address=Concat(
                        F('return_terminal__name'),
                        Value(' ('),
                        F('return_terminal__street_address'),
                        Value(', '),
                        F('return_terminal__ward_town_township'),
                        Value(', '),
                        F('return_terminal__city_county_district'),
                        Value(', '),
                        F('return_terminal__city_province'),
                        Value(')'),
                        output_field=CharField()
                    )
                ).values('formatted_address')[:1]
            ),

            # Route ID
            route=Subquery(
                DeliveryOperation.objects.filter(
                    order=OuterRef('pk')
                ).values('route_id')[:1]
            ),
            returned_time=Subquery(
                OrderHistory.objects.filter(
                    order=OuterRef('pk'),
                    action='returned'
                ).values('created_on')[:1]
            ),
            verified_time=Subquery(
                OrderHistory.objects.filter(
                    order=OuterRef('pk'),
                    action='verified'
                ).values('created_on')[:1]
            ),
            cancel_time=Coalesce(
                    # Lấy từ OrderHistory action 'cancelled' trước
                    Subquery(
                        OrderHistory.objects.filter(
                            order=OuterRef('pk'),
                            action='cancelled'
                        ).values('created_on')[:1]
                    ),
                    # Nếu không có thì lấy từ action 'receipt_cancelled'
                    Subquery(
                        OrderHistory.objects.filter(
                            order=OuterRef('pk'),
                            action='receipt_cancelled'
                        ).values('created_on')[:1]
                    ),
                    # Cuối cùng lấy từ DeliveryCancellation
                    Subquery(latest_cancellation.values('cancelled_at')[:1]),
                    output_field=DateTimeField()
                ),
            arrived_time=Subquery(
                OrderHistory.objects.filter(
                    order=OuterRef('pk'),
                    action='arrived'
                ).values('created_on')[:1]
            ),
            refunded_time=Subquery(
                OrderHistory.objects.filter(
                    order=OuterRef('pk'),
                    action='refunded'
                ).values('created_on')[:1]
            ),
            paid_time=Subquery(
                OrderHistory.objects.filter(
                    order=OuterRef('pk'),
                    action='paid'
                ).values('created_on')[:1]
            ),
            completed_time=Subquery(
                OrderHistory.objects.filter(
                    order=OuterRef('pk'),
                    action='completed'
                ).values('created_on')[:1]
            ),
            delivered_time=Subquery(
                OrderHistory.objects.filter(
                    order=OuterRef('pk'),
                    action='delivered'
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
                Subquery(latest_cancellation.values('cancelled_by__first_name')[:1]),
                # Cuối cùng là None
                Value(None),
                output_field=CharField()
            ),
            # Apply mapping annotations
            **mapping_annotations

        ).select_related(
            'status',
            'created_by',
            'recipient_address',
            'pickup_location',
            'delivery_terminal',
            'delivery_option',
            'delivery_operation',
            'delivery_operation__current_status',
            'delivery_operation__route'
        ).prefetch_related(
            'items',
            'items__item_type',
            'items__assignments',
            'items__assignments__events',
            'items__assignments__events__terminal_stop',
            'histories',
            'payments',
            'payments__payment_type'
        ).get(id=id)

        # Use DynamicSchema to get basic data structure
        order_data = OrderDetailOutSchema.from_queryset(order, many=False)

        # Financial summary is handled by DynamicSchema automatically

        # Add complex business logic fields that require custom processing

        # Add mapped_status using the new mapping system
        if hasattr(order, 'mapped_status') and order.mapped_status:
            order_data['mapped_status'] = {
                'name': order.mapped_status,
                'code': order.mapped_status_code,
                'color_code': order.mapped_status_background_color or order.mapped_status_text_color,
                'external_status_code': getattr(order, 'external_status_code', None),
                'external_status_name': getattr(order, 'external_status_name', None),
            }
        elif hasattr(order, 'delivery_operation') and order.delivery_operation and order.delivery_operation.current_status:
            # Fallback to delivery status if no mapping
            mapped_status = order.delivery_operation.current_status
            order_data['mapped_status'] = {
                'name': mapped_status.get_translation('name', language),
                'code': mapped_status.code,
                'color_code': mapped_status.color_code,
                'external_status_code': None,
                'external_status_name': None
            }
        else:
            order_data['mapped_status'] = None

        # Add delivery_status using ORM data
        if hasattr(order, 'delivery_operation') and order.delivery_operation and order.delivery_operation.current_status:
            order_data['delivery_status'] = {
                'id': order.delivery_operation.current_status.id,
                'name': order.delivery_operation.current_status.get_translation('name', language),
                'code': order.delivery_operation.current_status.code,
                'description': order.delivery_operation.current_status.get_translation('description', language),
                'color_code': order.delivery_operation.current_status.color_code
            }
        else:
            order_data['delivery_status'] = {
                'id': None,
                'name': None,
                'code': None,
                'description': None,
                'color_code': None
            }



        # Add payment_details using prefetched data
        payment = order.payments.first() if order.payments.exists() else None
        if payment:
            order_data['payment_details'] = {
                'id': payment.id,
                'payment_method': payment.payment_type.get_translation('name', language),
                'payment_method_code': payment.payment_type.code,
                'amount': str(payment.amount) if payment.amount else None,
                'currency': payment.amount.currency_symbol if payment.amount else None
            }
        else:
            order_data['payment_details'] = {
                'id': None,
                'payment_method': None,
                'payment_method_code': None,
                'amount': None,
                'currency': None
            }

        # Add history using prefetched data, filter out duplicate descriptions
        seen_descriptions = set()
        unique_history = []
        for history in order.histories.all():
            history_data = OrderHistoryOutSchema.from_queryset(history, many=False)
            description = history_data.get('description') if isinstance(history_data, dict) else getattr(history_data, 'description', None)
            if description not in seen_descriptions:
                seen_descriptions.add(description)
                unique_history.append(history_data)
        order_data['history'] = unique_history
        # # get verified time, cancel time, arrived time
        # order_data['verified_time'] = None
        # order_data['cancel_time'] = None
        # order_data['arrived_time'] = None
        # order_data['refunded_time'] = None
        # order_data['returned_time'] = None
        # order_data['paid_time'] = None
        # order_data['completed_time'] = None
        # verified_time = order.histories.filter(action='verified').first()
        # if verified_time:
        #     order_data['verified_time'] = verified_time.created_on
        # cancel_time = order.histories.filter(action='cancelled').first()
        # if cancel_time:
        #     order_data['cancel_time'] = cancel_time.created_on
        # arrived_time = order.histories.filter(action='arrived').first()
        # if arrived_time:
        #     order_data['arrived_time'] = arrived_time.created_on
        # refunded_time = order.histories.filter(action='refunded').first()
        # if refunded_time:
        #     order_data['refunded_time'] = refunded_time.created_on
        # returned_time = order.histories.filter(action='returned').first()
        # if returned_time:
        #     order_data['returned_time'] = returned_time.created_on
        # paid_time = order.histories.filter(action='paid').first()
        # if paid_time:
        #     order_data['paid_time'] = paid_time.created_on
        # completed_time = order.histories.filter(action='completed').first()
        # if completed_time:
        #     order_data['completed_time'] = completed_time.created_on
        # delivered_time = order.histories.filter(action='delivered').first()
        # if delivered_time:
        #     order_data['delivered_time'] = delivered_time.created_on
        # Add delivery_events using prefetched data
        delivery_events = []
        # ⚠️ CRITICAL: Với many=False cho order, serialize từng item với many=False để có đầy đủ nested fields
        items_data = []
        for item in order.items.all():
            item_data = OrderItemOutSchema.from_queryset(item, many=False)
            items_data.append(item_data)
        order_data['items'] = items_data
        for item in order.items.all():
            # print("item", item.assignments.all())  # DISABLED for performance
            for assignment in item.assignments.all():
                for event in assignment.events.all():
                    if event.terminal_stop:
                        delivery_events.append({
                            'package_id': item.id,
                            'id': event.id,
                            'event_type': event.event_type,
                            'description': event.description,
                            'lat': event.lat,
                            'lng': event.lng,
                            'terminal_stop': event.terminal_stop.name,
                            'created_on': event.created_on
                        })
        order_data['delivery_events'] = sorted(delivery_events, key=lambda x: x['created_on'])

        # Add financial_summary using ORM money fields
        order_data['financial_summary'] = {
            'subtotal': {
                'value': float(order.subtotal.raw_amount) if order.subtotal and not order.subtotal.is_null else 0,
                'formatted': str(order.subtotal) if order.subtotal and not order.subtotal.is_null else None,
                'currency_code': order.subtotal.currency_code if order.subtotal else None,
                'currency_symbol': order.subtotal.currency_symbol if order.subtotal else None
            },
            'delivery_fee': {
                'value': float(order.delivery_fee.raw_amount) if order.delivery_fee and not order.delivery_fee.is_null else 0,
                'formatted': str(order.delivery_fee) if order.delivery_fee and not order.delivery_fee.is_null else None,
                'currency_code': order.delivery_fee.currency_code if order.delivery_fee else None,
                'currency_symbol': order.delivery_fee.currency_symbol if order.delivery_fee else None
            },
            'tax_amount': {
                'value': float(order.tax_amount.raw_amount) if order.tax_amount and not order.tax_amount.is_null else 0,
                'formatted': str(order.tax_amount) if order.tax_amount and not order.tax_amount.is_null else None,
                'currency_code': order.tax_amount.currency_code if order.tax_amount else None,
                'currency_symbol': order.tax_amount.currency_symbol if order.tax_amount else None
            },
            'discount_amount': {
                'value': float(order.discount_amount.raw_amount) if order.discount_amount and not order.discount_amount.is_null else 0,
                'formatted': str(order.discount_amount) if order.discount_amount and not order.discount_amount.is_null else None,
                'currency_code': order.discount_amount.currency_code if order.discount_amount else None,
                'currency_symbol': order.discount_amount.currency_symbol if order.discount_amount else None
            },
            'total_amount': {
                'value': float(order.total_amount.raw_amount) if order.total_amount and not order.total_amount.is_null else 0,
                'formatted': str(order.total_amount) if order.total_amount and not order.total_amount.is_null else None,
                'currency_code': order.total_amount.currency_code if order.total_amount else None,
                'currency_symbol': order.total_amount.currency_symbol if order.total_amount else None
            }
        }

        # Add message logic for returned orders
        order_data['message'] = None
        order_data['message_type'] = None
        if order.status.code == 'returned':
            timeout = OrderService.get_returned_order_timeout_no_pickup()
            returned_time = order.histories.filter(action='returned').first()
            if returned_time and is_date_outdated(returned_time.created_on, timeout, language):
                order_data['message'] = get_order_message(order.delivery_address_formatted or '', 'en', timeout, True)
                order_data['message_type'] = 'error'
            else:
                order_data['message'] = get_order_message(order.delivery_address_formatted or '', 'en', timeout, False)
                order_data['message_type'] = 'warning'

        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_ORDER_SUCCESS, "Order retrieved successfully"),
            data=order_data
        )

    @route.post('/', auth=CustomJWTAuth())
    @path_permission("create", path_override=['/order', '/etri-order','/delivery-operation', '/delivery-inquiry'])
    def create_order(self, request, data: OrderCreateSchema):
        """
        sample data:
        {
            "sender_name": "Alice",
            "sender_phone": "0987654322",
            "sender_note": "Please handle with care",
            "recipient_name": "John Doe",
            "recipient_phone": "0987654321",
            "recipient_note": "Call before delivery",
            "pickup_location_id": 30,
            "delivery_option_code": "collect_at_location",
            "delivery_terminal_id": 28,
            "payment_method_code": "cash",
            "recipient_address": {
                "city": "Ho Chi Minh City",
                "district": "Tan Binh",
                "ward": "Ward 2",
                "street": "34B Bach Dang",
                "full_address": "34B Bach Dang, Ward 2, Tan Binh, Ho Chi Minh City",
                "lat": 10.773502,
                "lng": 106.704056
            },
            "items": [
                {
                "name": "Electronics Package",
                "weight": {"value": 2.5, "unit": "kg"},
                "dimension_l": {"value": 300, "unit": "mm"},
                "dimension_w": {"value": 200, "unit": "mm"},
                "dimension_h": {"value": 150, "unit": "mm"},
                "is_waterproof": true,
                "is_fragile": true,
                "item_type_id": 1,
                "package_id": 37,
                "note": "Contains a laptop"
                },
                {
                "name": "Documents",
                "weight": {"value": 0.5, "unit": "kg"},
                "dimension_l": {"value": 320, "unit": "mm"},
                "dimension_w": {"value": 230, "unit": "mm"},
                "dimension_h": {"value": 10, "unit": "mm"},
                "is_waterproof": false,
                "is_fragile": false,
                "item_type_id": 2,
                "package_id": 36,
                "note": "Important documents"
                }
            ]
        }
        """
        try:
            # In a real implementation, this would call a service in the order module
            order = OrderService.create(data.dict(), request)

            # Calculate order totals after creation
            order.calculate_totals()
            order.save()

            # Convert order to schema for JSON serialization - keep original format
            order_data = {}
            order_data['order_code'] = order.order_code
            order_data['order_id'] = order.id
            order_data['status_name'] = order.status.name
            order_data['status_code'] = order.status.code

            # Add new financial_summary field only
            order_data['financial_summary'] = {
                'total_amount': {
                    'value': float(order.total_amount.raw_amount) if order.total_amount and not order.total_amount.is_null else 0,
                    'formatted': str(order.total_amount) if order.total_amount and not order.total_amount.is_null else None,
                    'currency_code': order.total_amount.currency_code if order.total_amount else None,
                    'currency_symbol': order.total_amount.currency_symbol if order.total_amount else None
                }
            }

            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_ORDER_SUCCESS, "Order created successfully"),
                data=order_data
            )

        except ValidationError as e:
            return {
                "status": "error",
                "status_code": 400,
                "message": str(e),
                "data": {}
            }
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=400,
                message=str(e)
            )

    @route.post('/{id}/cancel-order', auth=CustomJWTAuth())
    @path_permission("update", path_override=['/order', '/etri-order', '/delivery-inquiry','/etri-tracking'])
    def cancel_order(self, request, data: OrderCancelSchema, id: int):
        """
        Cancel an order
        """
        try:
            # The data parameter already contains the parsed request body thanks to ninja
            order_id, is_refund, return_method = OrderService.cancel_order(id, data.reason, request)
            order_data = {}
            order_data['order_id'] = order_id
            order_data['is_refund'] = is_refund
            order_data['return_method'] = return_method
            order_data['cancel_reason'] = data.reason
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CANCEL_ORDER_SUCCESS, "Order cancelled successfully"),
                data=order_data
            )
        except ValidationError as e:
            return BaseResponse(
                success=False,
                status_code=400,
                errors=e.errors
            )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=400,
                message=str(e)
            )

    @route.post('/{id}/return-order', auth=CustomJWTAuth())
    @path_permission("update", path_override=['/order', '/etri-order', '/delivery-inquiry'])
    def return_order(self, request, id: int):
        """
        Return an order
        """
        try:
            order = OrderService.return_order(id)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.RETURN_ORDER_SUCCESS, "Order returned successfully"),
                data=order.id
            )
        except ValidationError as e:
            return BaseResponse(
                success=False,
                status_code=400,
                errors=e.errors
            )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=400,
                message=str(e)
            )

    @route.post('/{id}/payment')
    @path_permission("update", path_override=['/order', '/etri-order', '/delivery-inquiry'])
    def payment_order(self, request, id: int):
        """
        Payment an order
        """
        try:
            order = OrderService.payment_order(id)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.PAYMENT_ORDER_SUCCESS, "Order paid successfully"),
                data=order.id
            )
        except ValidationError as e:
            return BaseResponse(
                success=False,
                status_code=400,
                errors=e.errors
            )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=400,
                message=str(e)
            )

    @route.post('/{id}/refund', auth=CustomJWTAuth())
    @path_permission("update", path_override=['/order', '/etri-order', '/delivery-inquiry'])
    def refund_order(self, request, data: OrderRefundSchema, id: int):
        """
        Refund an order
        """
        try:
            order, refund_order = OrderService.refund_order(id, data.dict())

            # Use DynamicSchema for refund info
            refund_info = None
            if refund_order:
                refund_info = RefundOrderOutSchema.from_queryset(refund_order)

            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.REFUND_ORDER_SUCCESS, "Order refunded successfully"),
                data={'order_id': order.id, 'refund_info': refund_info},
                success=True
            )
        except ValidationError as e:
            return BaseResponse(
                success=False,
                status_code=400,
                errors=e.errors
            )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=400,
                message=str(e)
            )

    @route.post('/{id}/change-status', auth=CustomJWTAuth())
    @path_permission("update", path_override=['/order', '/etri-order', '/delivery-inquiry'])
    def change_status_order(self, request, id: int):
        """
        Change status of an order
        """
        try:
            order = OrderService.change_status_order(id)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CHANGE_STATUS_ORDER_SUCCESS, "Order status changed successfully"),
                data=order.id
            )
        except ValidationError as e:
            return BaseResponse(
                success=False,
                status_code=400,
                errors=e.errors
            )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=400,
                message=str(e)
            )


    @route.put('/settings/allow-order-in-bad-weather', url_name='allow_order_in_bad_weather', auth=CustomJWTAuth())
    def allow_order_in_bad_weather(self, request):
        """
        Check if order is allowed in bad weather
        """
        try:
            allow_order_in_bad_weather = UserGroupService.get_user_group_settings(request.user.userprofilelink.group.id, 'allow_order_in_bad_weather')
            allow_order_in_bad_weather_active = allow_order_in_bad_weather['active']
            print(f"allow_order_in_bad_weather: {allow_order_in_bad_weather_active}")
            # update allow_order_in_bad_weather_active to the database
            UserGroupService.update_user_group_settings(request.user.userprofilelink.group.id, 'allow_order_in_bad_weather', {'active': not allow_order_in_bad_weather_active})
            if allow_order_in_bad_weather_active:
                message = MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_ALLOW_ORDER_IN_BAD_WEATHER_UPDATED)
            else:
                message = MESSAGE_ENUM.get(MESSAGE_ENUM.ALLOW_ORDER_IN_BAD_WEATHER_UPDATED)
            return BaseResponse(
                success=True,
                status_code=200,
                message=message
            )
        except Exception as e:
            return BaseResponse(
                success=False,
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UNEXPECTED_ERROR)
            )

@api_controller('/package', tags=['Package'])
class PackageAPI:
    @route.get('/package-list', url_name='get_package_list', auth=CustomJWTAuth())
    def get_package_list(
        self,
        request,
        weight: float = None,
        dimension_l: float = None,
        dimension_w: float = None,
        dimension_h: float = None,
        is_waterproof: bool = None,
        is_fragile: bool = None
    ):
        """
        Get list of packaging specifications with optional filtering

        Parameters:
        - is_waterproof: Filter by waterproof capability
        - is_fragile: Filter by fragile support
        - package_type_id: Filter by package type ID
        """
        # Get name filter from query params
        name_search = request.GET.get('name', None)

        # Get package list from the service with caching
        package_list = OrderService.get_package_list_cached(
            weight, dimension_l, dimension_w, dimension_h,
            is_waterproof, is_fragile, name_search
        )

        # Use PackagingSpecificationService to process the package list
        serialized_packages = PackagingSpecificationService.get_list_specification_data(package_list)

        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_PACKAGE_LIST_SUCCESS, "Package list retrieved successfully"),
            data=serialized_packages
        )

@api_controller('/delivery-option', tags=['Delivery Option'])
class DeliveryOptionAPI:
    @route.get('/', url_name='get_delivery_options')
    def get_delivery_options(
        self,
        request,
    ):
        """
        Get list of available delivery options
        """
        query = DeliveryOption.objects.all()

        # Convert QuerySet to serializable data using the schema
        serialized_options = DeliveryOptionOutSchema.from_queryset(query, many=True)
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_DELIVERY_OPTIONS_SUCCESS, "Delivery options retrieved successfully"),
            data=serialized_options
        )

@api_controller('/banks', tags=['Banks'])
class BankAPI:
    @route.get('/', url_name='get_banks')
    def get_banks(self, request):
        """
        Get list of available banks
        """
        query = Bank.objects.all()
        serialized_banks = BankOutSchema.from_queryset(query, many=True)
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_BANKS_SUCCESS, "Banks retrieved successfully"),
            data=serialized_banks
        )

@api_controller('/pickup-locations', tags=['Pickup Locations'])
class PickupLocationAPI:
    @route.get('/', url_name='get_pickup_locations', auth=CustomJWTAuth())
    def get_pickup_locations(
        self,
        request,
        address: str = None,
        page_size: int = 25,
        current_page: int = 1,
        pickup_location_id: int = None,
        name: str = None
    ):
        """
        Get list of pickup locations
        """
        terminals = OrderService.get_terminals_by_route(pickup_location_id=pickup_location_id)

        terminals = apply_dynamic_filters(terminals, request.GET, [], request.GET.get('sort_obj'))

        terminals = sort_terminal_by_address(terminals, address)

        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(terminals, page_size)
        pages = paginator.page(current_page)
        data = []
        for terminal in pages.object_list:
            measurement = terminal.measurements.filter(measurement_type='time_stops').first()
            t = TerminalOutSchema.from_queryset(terminal)
            if measurement:
                t['time_stops'] = measurement.get_formatted_value(None)
            else:
                t['time_stops'] = None
            # t['full_address'] = terminal.name + '(' + terminal.street_address + ', ' + terminal.ward_town_township + ', ' + terminal.city_county_district + ', ' + terminal.city_province + ')'
            data.append(t)

        return BaseResponse(
            status_code=200,
            message="Pickup locations retrieved successfully",
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get('/etri-terminals', url_name='get_pickup_locations_etri', auth=CustomJWTAuth())
    def get_pickup_locations_etri(
        self,
        request,
        address: str = None,
        page_size: int = 25,
        current_page: int = 1,
        name: str = None
    ):
        """
        Get list of pickup locations
        """
        terminals = terminal_service.get_terminals_by_route_etri()
        if name:
            terminals = terminals.filter(full_address__icontains=name)
        terminals = sort_terminal_by_address(terminals, address)

        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(terminals, page_size)
        pages = paginator.page(current_page)
        data = []
        for terminal in pages.object_list:
            measurement = terminal.measurements.filter(measurement_type='time_stops').first()
            t = TerminalOutSchema.from_queryset(terminal)
            if measurement:
                t['time_stops'] = measurement.get_formatted_value(None)
            else:
                t['time_stops'] = None
            # t['full_address'] = terminal.name + '(' + terminal.street_address + ', ' + terminal.ward_town_township + ', ' + terminal.city_county_district + ', ' + terminal.city_province + ')'
            data.append(t)

        return BaseResponse(
            status_code=200,
            message="Pickup locations retrieved successfully",
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )
