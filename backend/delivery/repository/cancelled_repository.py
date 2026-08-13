from orders.models import OrderHistory, OrderItem, OrderStatus, RefundOrder
from delivery.models import (
    DeliveryStatus, 
    DeliveryOperation, 
    DeliveryOperationItem, 
    DeliveryCancellation, 
    DeliveryCancellationType
)
from django.db.models import QuerySet
from django.db.models import Count
from core.middleware.refresh_token import get_current_request
from django.db.models import OuterRef, Subquery, Count, Max, F, Case, When, BooleanField, Exists, CharField, Sum, Value, Q
from django.db.models.functions import Concat, Coalesce
from delivery.services.status_mapping_service import StatusMappingService

class CancelledRepository:
    @staticmethod
    def get_cancelled_statuses() -> QuerySet:
        return DeliveryStatus.objects.filter(code="receipt_cancelled")

    @staticmethod
    def get_cancelled_operations() -> QuerySet:
        order_items_count = OrderItem.objects.filter(
            order=OuterRef('order')
        ).values('order').annotate(
            count=Count('id')
        ).values('count')

        order_cancellation_time = RefundOrder.objects.filter(
            order=OuterRef('order')
        ).values('created_on').order_by('-created_on')

        # Use Subquery for One-to-Many relationships
        latest_cancellation = DeliveryCancellation.objects.filter(
            delivery_operation=OuterRef('pk')
        ).order_by('-cancelled_at')

        # Get mapping annotations from StatusMappingService
        mapping_annotations = StatusMappingService.build_annotate_with_mapping(context='delivery_operation')

        data = DeliveryOperation.objects.filter(
            current_status__code__in=["receipt_cancelled", "cancelled"]
        ).select_related(
            'current_status',
            'order',
            'route',
            'created_by',
            'modified_by'
        ).prefetch_related(
            'items',
            'items__drone',
            'items__order_item',
            'returns',
            'cancellations'
        ).annotate(
            number_of_packages=Subquery(order_items_count),
            cancel_time=Subquery(latest_cancellation.values('cancelled_at')[:1]),
            cancel_reason=Coalesce(
                Subquery(latest_cancellation.values('reason')[:1]),
                F('order__cancel_reason')
            ),
            cancelled_by_first_name=Subquery(latest_cancellation.values('cancelled_by__first_name')[:1]),
            refunded_time=Subquery(
                OrderHistory.objects.filter(
                    order=OuterRef('order'),
                    action='refunded'
                ).values('created_on')[:1]
            ),
            order_cancellation_time=Subquery(order_cancellation_time[:1]),
            # New columns
            order_identifier=F('another_info__anyang__itemOrgId'),
            receipt_number=F('another_info__etri__receipt_id'),
            handler=Concat(
                Coalesce(F('created_by__last_name'), Value(''), output_field=CharField()),
                Value(' '),
                Coalesce(F('created_by__first_name'), Value(''), output_field=CharField()),
                output_field=CharField()
            ),
            tracking_number=F('another_info__etri__tracking_number'),
            
            # Use dynamic mapping annotations
            **mapping_annotations
        ).order_by('-id')
        
        return data
    
    @staticmethod
    def get_cancelled_operation_by_id(operation_id: int) -> DeliveryOperation:
        try:
            return DeliveryOperation.objects.get(id=operation_id, 
                                                 current_status__code="unverified_order",
                                                 another_info__isnull=True)
        except DeliveryOperation.DoesNotExist:
            return None
    
    @staticmethod
    def cancel_operation_order_by_user(operation: DeliveryOperation, reason_note: str) -> DeliveryOperation:
        operation.current_status = DeliveryStatus.objects.get(code="receipt_cancelled")
        operation.save()
        operation.order.cancel_reason = reason_note
        operation.order.status = OrderStatus.objects.filter(code="cancelled").first()
        operation.order.save()
        user = get_current_request().user
        DeliveryCancellation.objects.create(
            delivery_operation=operation,
            reason_type=DeliveryCancellationType.objects.get(code="user_cancelled"),
            reason=reason_note,
            cancelled_by=user
        )
        return operation
    
    @staticmethod
    def cancel_operation_order_by_system(operation: DeliveryOperation) -> DeliveryOperation:
        operation.current_status = DeliveryStatus.objects.get(code="receipt_cancelled")
        operation.save()
        reason_type = DeliveryCancellationType.objects.get(code="auto_cancelled")
        DeliveryCancellation.objects.create(
            delivery_operation=operation,
            reason_type=reason_type,
            reason=reason_type.reason_default
        )
        return operation
    
