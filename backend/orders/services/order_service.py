import json
from django.db.models.functions import Concat
from django.utils import timezone
from django.db import transaction
from terminals.models import RouteTerminal, Routes, Terminal
from terminals.services.terminal_service import get_function_names_annotation, get_linked_delivery_hubs_annotation, get_type_name_annotation
from delivery.models import DeliveryOperation, DeliveryStatus
from devices.services.packaging_service import PackagingSpecificationService
from devices.models import PackagingSpecification
from ninja.errors import ValidationError
from django.utils.translation import gettext as _
from typing import Any, Dict, List
from geopy.geocoders import Nominatim
from orders.models import Address, Bank, OrderHistory, Payment, RefundOrder, ReturnOrder, DeliveryOption, GuessUser, Order, OrderItem, OrderStatus, PaymentType
from core.common.search.dynamic_search import apply_dynamic_filters
from core.middleware.refresh_token import get_current_request
from common.pagination import OptimizedPaginator
from django.db.models import Q, Subquery, OuterRef, Count, Exists, Case, When, F, Value, CharField
from django.contrib.contenttypes.models import ContentType
from django.db import models
from orders.repository.order_repository import OrderRepository
from core.configuration.models import AdminConfig
from decimal import Decimal
from delivery.repository.verification_repository import VerificationRepository
from django.core.cache import cache
import hashlib
from common.utils import generate_order_code, generate_item_code, generate_unique_code

RETURNED_ORDER_TIMEOUT_NO_PICKUP_DEFAULT = 15

def get_operation_config():
    """Get operation configuration with fallback"""
    try:
        from core.configuration.models import AdminConfig
        config = AdminConfig.objects.get(name='Operation').settings
        return config
    except (ImportError, AdminConfig.DoesNotExist, Exception):
        # Fallback to default configuration
        return {
            'returned_order_timeout_no_pickup': RETURNED_ORDER_TIMEOUT_NO_PICKUP_DEFAULT
        }

class OrderService:
    @classmethod
    @transaction.atomic
    def create(cls, data: Dict[str, Any], request) -> Order:
        # Validate required fields
        if not data.get('recipient_name'):
            raise ValidationError(_("Recipient name is required"))
        if not data.get('recipient_phone'):
            raise ValidationError(_("Recipient phone is required"))
        if not data.get('pickup_location_id'):
            raise ValidationError(_("Pickup location is required"))

        # Create recipient address if provided (for Delivery to Door option)
        recipient_address = None
        sender_address = None
        if data.get('recipient_address'):
            recipient_address = Address.objects.create(**data.get('recipient_address'))
            # if recipient_address.city is empty
            if not recipient_address.city:
                try:
                    geolocator = Nominatim(user_agent="delivery_dashboard")
                    location = geolocator.geocode(recipient_address.full_address)
                    if location:
                        recipient_address.city = location.raw['display_name'].split(",")[-3].strip()
                        recipient_address.save()
                except Exception as e:
                    print("error get city from address: ", e)

        if data.get('sender_address'):
            sender_address = Address.objects.create(**data.get('sender_address'))

        # Get delivery option
        delivery_option = DeliveryOption.objects.get(code=data.get('delivery_option_code'))

        # Get payment method
        payment_method = PaymentType.objects.get(code=data.get('payment_method_code'))

        # Generate order code
        order_code = str(Order._base_manager.order_by('-id').first().id + 1).zfill(8)

        # get pending order status
        pending_order_status = OrderStatus.objects.get(code='awaiting_payment')

        # Process financial data from input - Use Decimal directly for EnhancedMoneyField
        delivery_fee = None
        if data.get('delivery_fee'):
            delivery_fee = Decimal(str(data.get('delivery_fee', {}).get('value', 0)))
        
        tax_amount = None
        if data.get('tax_amount'):
            tax_amount = Decimal(str(data.get('tax_amount', {}).get('value', 0)))
        
        discount_amount = None
        if data.get('discount_amount'):
            discount_amount = Decimal(str(data.get('discount_amount', {}).get('value', 0)))

        # Create order
        order = Order.objects.create(
            order_code=order_code,
            sender_name=data.get('sender_name'),
            sender_phone=data.get('sender_phone'),
            sender_address=sender_address,
            recipient_name=data.get('recipient_name'),
            recipient_phone=data.get('recipient_phone'),
            recipient_address=recipient_address,
            pickup_location_id=data.get('pickup_location_id'),
            delivery_option=delivery_option,
            delivery_terminal_id=data.get('delivery_terminal_id'),
            created_by_id=request.user.id,
            sender_note=data.get('sender_note'),
            recipient_note=data.get('recipient_note'),
            created_on=timezone.now(),
            status=pending_order_status,
            another_info={}
        )

        # Only create the DeliveryOperation, not the items
        receipt_code = f"{timezone.now().strftime('%y%m%d')}{str(order.id).zfill(6)}"
        another_info = {}
        order_org = data.get('order_org', None)
        if order_org == "etri":
            another_info = {
                "etri": {
                    "receipt_id": receipt_code
            }
        }
        DeliveryOperation.objects.create(
            order=order,
            current_status=DeliveryStatus.objects.get(code="unverified_order"),
            another_info=another_info
        )
        
        # Set money fields directly in __dict__ to bypass Money descriptor
        order.__dict__['delivery_fee'] = delivery_fee
        order.__dict__['tax_amount'] = tax_amount  
        order.__dict__['discount_amount'] = discount_amount
        # Also set subtotal and total_amount to None to avoid Money objects
        order.__dict__['subtotal'] = None
        order.__dict__['total_amount'] = None
        order.save()

        # Gen a receipt code with format "YYMMDDXXXXXX" where XXXXXX is base on order id
        user = get_current_request().user
        group_code = user.userprofilelink.group.code if user.userprofilelink.group else None
        tracking_number = f"ms_{group_code}_{str(order.id).zfill(6)}"
        receipt_code = f"{timezone.now().strftime('%y%m%d')}{str(order.id).zfill(6)}"
        order.another_info = {
            "etri": {
                "receipt_id": receipt_code,
                "tracking_number": ""
            }
        }
        order.save()

        # Create order items (packages)
        total_amount = Decimal('0')
        for item in data.get('items', []):
            # Get the selected package specification
            package_specification = PackagingSpecification.objects.get(id=item.get('package_id')) if item.get('package_id') else None
            
            # Generate item code with pattern PK00000X
            # Get count of existing items and add 1 for the new item
            item_count = OrderItem._base_manager.order_by('-id').first().id + 1
            item_code = f"PK{str(item_count).zfill(6)}"
            
            # Process item amount - Use Decimal directly for EnhancedMoneyField
            item_amount = None
            if item.get('amount'):
                item_amount = Decimal(str(item.get('amount').get('value', 10000)))
            else:
                item_amount = Decimal('10000')  # Default amount
            
            # Create the order item
            OrderItem.objects.create(
                order=order,
                name="",
                code=item_code,
                weight={"value": item.get('weight').get('value'), "unit": item.get('weight').get('unit')},
                dimension_l={"value": item.get('dimension_l').get('value'), "unit": item.get('dimension_l').get('unit')},
                dimension_w={"value": item.get('dimension_w').get('value'), "unit": item.get('dimension_w').get('unit')},
                dimension_h={"value": item.get('dimension_h').get('value'), "unit": item.get('dimension_h').get('unit')},
                is_waterproof=item.get('is_waterproof', False),
                is_fragile=item.get('is_fragile', False),
                item_type_id=item.get('item_type_id'),
                package_id=package_specification,
                amount=item_amount,  # Use Decimal directly for EnhancedMoneyField
                note=item.get('note', '')
            )
            
            # Add to total amount
            total_amount += item_amount

        # Create payment record using Decimal directly for EnhancedMoneyField
        Payment.objects.create(
            order=order,
            amount=total_amount,  # Use Decimal directly
            payment_type=payment_method,
            status='completed' if data.get('payment_method_code') != 'cash' else 'pending',
            payer_phone=data.get('sender_phone')
        )
        
        OrderService.create_order_history(order.id, request.user.username if request.user else "", "created")

        # Change order status to pending confirmation
        if data.get('payment_method_code') != 'cash':
            OrderService.update_order_status(order.id, "pending_confirmation")
            OrderService.create_order_history(order.id, request.user.username if request.user else "", "paid")

        return order

    @classmethod
    @transaction.atomic
    def get_list(cls, data: Dict[str, Any], page_size: int, current_page: int, exclude_fields: List[str] = [], sort_obj: Dict[str, Any] = {}) -> Order:
        # Make a full select to ensure we get all fields
        orders = Order.objects.select_related(
            'recipient_address',
            'status'
        ).annotate(
            item_count=models.Count('items')
        ).order_by('-created_on')

        # filter order by number of items
        item_count = data.get('item_count')
        if item_count is not None:
            try:
                item_count = item_count
                orders = orders.filter(item_count=item_count)
            except ValueError:
                pass
        
        # filter order by order time
        if data.get('created_on_start'):
            orders = orders.filter(created_on__gte=data.get('created_on_start'))
        if data.get('created_on_end'):
            orders = orders.filter(created_on__lte=data.get('created_on_end'))
        
        orders = apply_dynamic_filters(orders, data, exclude_fields, sort_obj)
        # sort in case sort_obj contains {"key":"item_count","value":"desc"}
        if sort_obj:
            sort_obj = json.loads(sort_obj)
            for sort_item in sort_obj:
                key = sort_item['key']
                value = sort_item['value']
                if key == 'item_count' and value == 'desc':
                    orders = orders.order_by('-item_count')
                elif key == 'item_count' and value == 'asc':
                    orders = orders.order_by('item_count')
        
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(orders, page_size)
        
        # Handle pagination properly
        try:
            orders = paginator.page(current_page)
        except:
            # Default to first page if there's an issue
            orders = paginator.page(1)
            
        total_pages = paginator.num_pages
        total_items = paginator.count
        return orders.object_list, total_pages, total_items
    
    @classmethod
    @transaction.atomic
    def get_order_by_id(cls, id: int) -> Order:
        return Order.objects.select_related(
            'recipient_address', 
            'pickup_location',
            'delivery_option',
            'delivery_terminal',
            'delivery_operation',
            'delivery_operation__current_status'
        ).prefetch_related(
            'items__package_id__measurements',
            'items__assignments__events',
            'payments',
            'histories'
        ).get(id=id)
    
    @classmethod
    @transaction.atomic
    def cancel_order(cls, id: int, reason: str, request) -> Order:
        order = Order.objects.get(id=id)
        is_refund = False
        return_method = None
        # Check if order exists
        if not order:
            raise ValidationError(f"Order with ID {id} not found")
            
        # Check if order status
        order_status = order.status.code
        if order_status == 'cancelled':
            raise ValidationError(f"Order with ID {id} is already cancelled")
        if order_status == 'pending_confirmation':
            try:
                payment = Payment.objects.get(order=order)
                if payment:
                    if payment.status == 'completed':
                        is_refund = True
                    if payment.payment_type.code == 'cash':
                        return_method = 'cash'
                    else:
                        return_method = 'bank'
            except Payment.DoesNotExist:
                # If no payment exists, proceed with normal cancellation
                pass
        
        if is_refund is False:
            # Create order history
            OrderService.create_order_history(order.id, request.user.username if request.user else "", "cancelled")

            # Update the order status
            cancelled_status = OrderStatus.objects.get(code='cancelled')
            order.status = cancelled_status
            order.cancel_reason = reason
            order.save()

            # update order delivery operation status
            order_delivery_operation = DeliveryOperation.objects.get(order=order)
            order_delivery_operation.current_status = DeliveryStatus.objects.get(code='receipt_cancelled')
            order_delivery_operation.save()
            if hasattr(order_delivery_operation, 'deliveryoperationitem'):
                order_delivery_operation.deliveryoperationitem.update(is_drone_approved=False)
                order_delivery_operation.deliveryoperationitem.update(is_arrived=False)
                order_delivery_operation.deliveryoperationitem.update(is_delivered=False)
                order_delivery_operation.deliveryoperationitem.update(drone_arrived_at=None)
                order_delivery_operation.deliveryoperationitem.update(arrived_at=None)
                order_delivery_operation.deliveryoperationitem.update(delivered_at=None)
                order_delivery_operation.deliveryoperationitem.update(drone=None)
                order_delivery_operation.save()
        # Return order id, is_refund, return_method
        return order.id, is_refund, return_method
    
    @classmethod
    @transaction.atomic
    def return_order(cls, id: int) -> Order:
        order = Order.objects.get(id=id)
        # Check if order exists
        if not order:
            raise ValidationError(f"Order with ID {id} not found")
        # Make a return order
        ReturnOrder.objects.create(
            order=order,
            return_terminal=order.pickup_location,
            return_time_period="from Monday to Friday, between 8:00 AM and 5:00 PM",
            return_days=7
        )

        # Create order history
        OrderHistory.objects.create(
            order=order,
            action='returned',
            description="Order returned to terminal " + order.pickup_location.name
        )
        return order
    
    @classmethod
    @transaction.atomic
    def get_package_list(cls, weight: float, dimension_l: float, dimension_w: float, dimension_h: float, waterproof: bool, fragile: bool) -> List[PackagingSpecification]:
        """
        Find suitable packaging specifications based on item dimensions, weight, and other requirements.
        Returns a list of packaging specifications that can accommodate the item.
        
        Logic: Package dimensions >= Item dimensions AND Package weight >= Item weight
        """
        # Get the content type for PackagingSpecification
        content_type = ContentType.objects.get_for_model(PackagingSpecification)
        
        # Base query - filter by basic properties with prefetch_related
        packages_query = PackagingSpecification.objects.filter(
            active=True
        ).prefetch_related('measurements')
        
        # Apply waterproof and fragile filters only if required
        if waterproof:
            packages_query = packages_query.filter(water_proof__isnull=False)
        if fragile:
            packages_query = packages_query.filter(fragile=True)
        
        # Use JOIN instead of Subquery for better performance
        packages_query = packages_query.filter(
            # Dimensions filter
            measurements__content_type=content_type,
            measurements__measurement_type='dimensions',
            measurements__data__type='dimensions',
            measurements__data__length__gte=dimension_l,
            measurements__data__width__gte=dimension_w,
            measurements__data__height__gte=dimension_h
        ).filter(
            # Weight filter
            measurements__content_type=content_type,
            measurements__measurement_type='max_weight',
            measurements__data__type='simple',
            measurements__data__value__gte=weight
        ).distinct()
        
        return packages_query

    @classmethod
    def get_package_list_cached(cls, weight: float, dimension_l: float, dimension_w: float, dimension_h: float, waterproof: bool, fragile: bool, name_search: str = None) -> List[PackagingSpecification]:
        """
        Get package list with caching for better performance
        """
        # Create cache key based on all parameters
        cache_params = {
            'weight': weight,
            'dimension_l': dimension_l,
            'dimension_w': dimension_w,
            'dimension_h': dimension_h,
            'waterproof': waterproof,
            'fragile': fragile,
            'name_search': name_search
        }
        
        # Create hash for cache key
        cache_key = f"package_list_{hashlib.md5(json.dumps(cache_params, sort_keys=True).encode()).hexdigest()}"
        
        # Try to get from cache first
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # If not in cache, get from database
        package_list = cls.get_package_list(weight, dimension_l, dimension_w, dimension_h, waterproof, fragile)
        
        # Apply name filter if provided
        if name_search:
            package_list = package_list.filter(name__icontains=name_search)
        
        # Cache the result for 5 minutes
        cache.set(cache_key, package_list, 300)
        
        return package_list

    @classmethod
    @transaction.atomic
    def payment_order(cls, id: int) -> Order:
        order = Order.objects.get(id=id)
        if not order:
            raise ValidationError(f"Order with ID {id} not found")
        # Update the order status to paid
        paid_status = OrderStatus.objects.get(code='pending_confirmation')
        order.status = paid_status
        order.save()

        # Create order history
        OrderHistory.objects.create(
            order=order,
            action='paid',
            description="Order paid, waiting for confirmation"
        )
        # update payment status
        payment = Payment.objects.get(order=order)
        payment.status = 'completed'
        payment.save()
        
        return order  

    @classmethod
    @transaction.atomic
    def refund_order(cls, id: int, data: Dict[str, Any]) -> tuple:
        order = Order.objects.get(id=id)
        if not order:
            raise ValidationError(f"Order with ID {id} not found")
        
        # Calculate refund amount (could be from payment or manual input)
        refund_amount = None
        processing_fee = None
        
        if data.get('refund_amount'):
            refund_amount = Decimal(str(data.get('refund_amount').get('value')))
        else:
            # Default to payment amount
            payment = order.payments.first()
            if payment and payment.amount and not payment.amount.is_null:
                refund_amount = payment.amount.raw_amount
        
        if data.get('processing_fee'):
            processing_fee = Decimal(str(data.get('processing_fee').get('value')))
        
        refund_order = None
        # Create order refund record with money fields
        if data.get('refund_method') == 'cash':
            refund_order = RefundOrder.objects.create(
                order=order,
                refund_type='cash',
                refund_amount=refund_amount,
                processing_fee=processing_fee,
                refund_status='pending'
            )
        elif data.get('refund_method') == 'bank':
            bank = Bank.objects.get(code=data.get('bank_code'))
            refund_order = RefundOrder.objects.create(
                order=order,
                refund_type='bank',
                bank=bank,
                account_number=data.get('account_number'),
                account_holder_name=data.get('account_holder_name'),
                refund_amount=refund_amount,
                processing_fee=processing_fee,
                refund_status='pending'
            )
        else:
            raise ValidationError(f"Invalid refund method: {data.get('refund_method')}")
        
        # Create order history
        OrderHistory.objects.create(
            order=order,
            action='cancelled',
            description="Order cancelled"
        )

        # Update the order status
        cancelled_status = OrderStatus.objects.get(code='cancelled')
        order.status = cancelled_status
        order.cancel_reason = data.get('reason')
        order.save()

        OrderHistory.objects.create(
            order=order,
            action='refunded',
            description="Order refunded"
        )
        
        return order, refund_order

    @classmethod
    @transaction.atomic
    def create_order_history(cls, order_id: int, username: str, action: str) -> None:
        if action == "created":
            OrderRepository.create_order_create_history(order_id, username)
        elif action == "paid":
            OrderRepository.create_order_paid_history(order_id, username)
        elif action == "cancelled":
            OrderRepository.create_order_cancelled_history(order_id, username)
        elif action == "refunded":
            OrderRepository.create_order_refunded_history(order_id, username)
        elif action == "verified":
            OrderRepository.create_order_verified_history(order_id, "")
        elif action == "returned":
            OrderRepository.create_order_returned_history(order_id, username)
        elif action == "delivered":
            OrderRepository.create_order_delivered_history(order_id, username)
        elif action == "receipt_cancelled":
            OrderRepository.create_order_receipt_cancelled_history(order_id, username)
        else:
            raise ValidationError(f"Invalid action: {action}")
        
    @classmethod
    @transaction.atomic
    def create_orders_history(cls, order_ids: list, username: str, action: str) -> None:
        if action == "verified":
            OrderRepository.create_orders_verified_history(order_ids, username)
        else:
            raise ValidationError(f"Invalid action: {action}")

    @classmethod
    @transaction.atomic
    def update_order_status(cls, order_id: int, status_code: str) -> None:
        OrderRepository.update_order_status(order_id, status_code)

    @classmethod
    @transaction.atomic
    def update_orders_status(cls, order_ids: list, status_code: str) -> None:
        OrderRepository.update_orders_status(order_ids, status_code)

    @staticmethod
    def get_returned_order_timeout_no_pickup() -> int:
        operation_config = get_operation_config()
        order_timeout = operation_config.get('order_returned_timeout_no_pickup', RETURNED_ORDER_TIMEOUT_NO_PICKUP_DEFAULT)
        return order_timeout
        
        
    @classmethod
    @transaction.atomic
    def change_status_order(cls, id: int) -> Order:
        # Optimize: Use select_related to reduce queries
        order = Order.objects.select_related('status').get(id=id)
        
        # Optimize: Get delivery operation with select_related in one query
        order_delivery_operation = DeliveryOperation.objects.select_related(
            'current_status', 'order'
        ).filter(order=order).first()
        
        if not order_delivery_operation:
            raise ValidationError("Delivery operation not found for this order")
        
        # Optimize: Cache status objects to avoid repeated queries
        # These statuses are likely used frequently, consider caching at application level
        awaiting_shipment_status = OrderStatus.objects.filter(code='awaiting_shipment').first()
        select_route_status = DeliveryStatus.objects.filter(code='select_route_processing').first()
        
        if not awaiting_shipment_status or not select_route_status:
            raise ValidationError("Required status not found")
        
        # Optimize: Only verify if operation is not already verified
        if order_delivery_operation.current_status.code != 'verified_order':
            # Optimize: Pass single operation instead of queryset
            VerificationRepository.verify_operations(
                DeliveryOperation.objects.filter(id=order_delivery_operation.id)
            )
        
        # Optimize: Update both objects in memory first, then save once
        order.status = awaiting_shipment_status
        order_delivery_operation.current_status = select_route_status
        
        # Optimize: Use bulk_update for better performance if multiple operations
        order.save()
        order_delivery_operation.save()
        
        return order
    
    @classmethod
    @transaction.atomic
    def get_delivery_inquiry_refresh_config(cls) -> tuple:
        try:
            config = AdminConfig.objects.get(name='Delivery inquiry refresh')
            dashboard_refresh_interval = config.settings.get('delivery_inquiry_refresh_interval')
            dashboard_auto_refresh = config.settings.get('delivery_inquiry_auto_refresh')
        except Exception as e:
            dashboard_refresh_interval = 0
            dashboard_auto_refresh = False
            print("error get delivery inquiry refresh config: ", e)
        return dashboard_refresh_interval, dashboard_auto_refresh
    
    def get_terminals_by_route( pickup_location_id: int = None):
        """
        Get all terminals that are in at least one active route
        Only terminals that have at least one active route will be returned
        
        Args:
            pickup_location_id: Optional terminal ID. If provided, only return terminals
                                that are in the same active routes as this terminal
        """
        # Check if terminal has at least one active route
        active_routes = RouteTerminal.objects.filter(
            terminal=OuterRef('pk'),
            route__is_active=True
        )
        
        terminals = Terminal.objects.prefetch_related(
            'terminal_types', 'functions', 'location_type'
        ).filter(
            Exists(active_routes),
            terminal_types__code__in=['DOCKING_STATION','DELIVERY_HUB'],
            active=True
        )
        
        # If pickup_location_id is provided, filter to only terminals in same routes
        if pickup_location_id:
            # Get all active routes that contain the pickup_location terminal
            pickup_routes_subquery = Routes.objects.filter(
                route_terminals__terminal_id=pickup_location_id,
                is_active=True
            ).values_list('id', flat=True).distinct()
            
            # Only return terminals that are in at least one of these routes
            terminals_in_same_routes = RouteTerminal.objects.filter(
                terminal=OuterRef('pk'),
                route_id__in=Subquery(pickup_routes_subquery),
                route__is_active=True
            )
            
            terminals = terminals.filter(
                Exists(terminals_in_same_routes)
            )
        
        terminals = terminals.annotate(
            full_address=Case(
                When(
                    city_province__isnull=False,
                    city_county_district__isnull=False,
                    ward_town_township__isnull=False,
                    street_address__isnull=False,
                    then=Concat(
                        F('city_province'),
                        Value(' '),
                        F('city_county_district'),
                        Value(' '),
                        F('ward_town_township'),
                        Value(' '),
                        F('street_address'),
                        output_field=CharField()
                    )
                ),
                When(
                    city_province__isnull=False,
                    city_county_district__isnull=False,
                    street_address__isnull=False,
                    then=Concat(
                        F('city_province'),
                        Value(' '),
                        F('city_county_district'),
                        Value(' '),
                        F('street_address'),
                        output_field=CharField()
                    )
                ),
                When(
                    city_province__isnull=False,
                    city_county_district__isnull=False,
                    then=Concat(
                        F('city_province'),
                        Value(' '),
                        F('city_county_district'),
                        output_field=CharField()
                    )
                ),
                When(
                    city_province__isnull=False,
                    then=F('city_province')
                ),
                default=Value(''),
                output_field=CharField()
            ),
            organization=F('created_by__userprofilelink__group__code'),
            related_routes_count=Count('route_terminals__route', distinct=True),
            type_name=get_type_name_annotation(),
            function=get_function_names_annotation(),
            linked_terminal=get_linked_delivery_hubs_annotation()
        ).distinct()
        
        # Exclude pickup_location_id if provided (after all filters and annotations)
        if pickup_location_id:
            terminals = terminals.exclude(id=pickup_location_id)
        
        terminals = terminals.order_by('-id')
        
        return terminals