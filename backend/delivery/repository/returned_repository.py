
from orders.models import OrderItem, OrderStatus
from delivery.models import (
    DeliveryStatus, 
    DeliveryOperation, 
    DeliveryOperationItem, 
    DeliveryReturn,
    DeliveryOperationHistory,
    DeliveryCancellation
)
from django.db.models import OuterRef, Subquery, Count, Max, F, Case, When, BooleanField, Exists, CharField, Sum, Q
from django.db.models import QuerySet
from django.db.models import Count
from django.db.models.functions import Concat, Coalesce
from django.db.models import Value
from delivery.services.status_mapping_service import StatusMappingService

class ReturnedRepository:
    @staticmethod
    def get_operation_by_id(operation_id: int) -> DeliveryOperation:
        return DeliveryOperation._base_manager.get(id=operation_id)
    
    @staticmethod
    def get_returned_statuses() -> QuerySet:
        return DeliveryStatus.objects.filter(code__in=[
            "order_due_for_returned", 
            "order_pending_returned", 
            "overdue_order", 
            "returned_order", 
            "processed_order"
        ])

    @staticmethod
    def _get_base_annotations():
        order_items_count = OrderItem.objects.filter(
            order=OuterRef('order')
        ).values('order').annotate(
            count=Count('id')
        ).values('count')

        arrival_time = DeliveryOperationHistory.objects.filter(
            delivery_operation=OuterRef('id'),
            status__code='arrived_order'
        ).values('changed_at').order_by('-changed_at')

        return_time = DeliveryOperationHistory.objects.filter(
            delivery_operation=OuterRef('id'),
            status__code='order_pending_returned'
        ).values('changed_at').order_by('-changed_at')

        return_received_time = DeliveryOperationHistory.objects.filter(
            delivery_operation=OuterRef('id'),
            status__code='returned_order'
        ).values('changed_at').order_by('-changed_at')

        processing_confirmation_time = DeliveryOperationHistory.objects.filter(
            delivery_operation=OuterRef('id'),
            status__code='processed_order'
        ).values('changed_at').order_by('-changed_at')

        # Latest cancellation for reason_for_rejection
        latest_cancellation = DeliveryCancellation.objects.filter(
            delivery_operation=OuterRef('pk')
        ).order_by('-cancelled_at')

        # Get mapping annotations from StatusMappingService
        mapping_annotations = StatusMappingService.build_annotate_with_mapping(context='delivery_operation')

        base_annotations = {
            'number_of_packages': Subquery(order_items_count),
            'arrival_time': Subquery(arrival_time[:1]),
            'return_time': Subquery(return_time[:1]),
            'return_received_time': Subquery(return_received_time[:1]),
            'processing_confirmation_time': Subquery(processing_confirmation_time[:1]),
            # New columns
            'order_identifier': F('another_info__anyang__itemOrgId'),
            'receipt_number': F('another_info__etri__receipt_id'),
            'handler': Concat(
                Coalesce(F('created_by__last_name'), Value(''), output_field=CharField()),
                Value(' '),
                Coalesce(F('created_by__first_name'), Value(''), output_field=CharField()),
                output_field=CharField()
            ),
            'tracking_number': F('another_info__etri__tracking_number'),
            'reason_for_rejection': Coalesce(
                Subquery(latest_cancellation.values('reason')[:1]),
                F('order__cancel_reason')
            ),
        }

        # Add mapping annotations
        base_annotations.update(mapping_annotations)

        return base_annotations

    @staticmethod
    def get_due_for_return_operations() -> QuerySet:
        annotations = ReturnedRepository._get_base_annotations()
        return DeliveryOperation.objects.filter(
            current_status__code="order_due_for_returned"
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
        ).annotate(**annotations).order_by('-id', '-created_on').distinct('id')
        
    @staticmethod
    def get_pending_return_operations() -> QuerySet:
        annotations = ReturnedRepository._get_base_annotations()
        return DeliveryOperation.objects.filter(
            current_status__code="order_pending_returned"
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
        ).annotate(**annotations).order_by('-id', '-created_on').distinct('id')
        
    @staticmethod
    def get_overdue_operations() -> QuerySet:
        annotations = ReturnedRepository._get_base_annotations()
        return DeliveryOperation.objects.filter(
            current_status__code="overdue_order"
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
        ).annotate(**annotations).order_by('-id', '-created_on').distinct('id')
        
    @staticmethod
    def get_returned_operations() -> QuerySet:
        annotations = ReturnedRepository._get_base_annotations()
        return DeliveryOperation.objects.filter(
            current_status__code="returned_order"
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
        ).annotate(**annotations).order_by('-id', '-created_on').distinct('id')
        
    @staticmethod
    def get_processed_return_operations() -> QuerySet:
        annotations = ReturnedRepository._get_base_annotations()
        return DeliveryOperation.objects.filter(
            current_status__code="processed_order"
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
        ).annotate(**annotations).order_by('-id', '-created_on').distinct('id')

    @staticmethod
    def execute_order_due_for_return(operation_id: int):
        from orders.services.order_service import OrderService
        operation = DeliveryOperation._base_manager.get(id=operation_id)
        status_return = DeliveryStatus.objects.get(code="order_due_for_returned")
        operation.current_status = status_return
        operation.save()
        operation.order.status = OrderStatus.objects.get(code="returned")
        operation.order.save()
        # create order history
        OrderService.create_order_history(operation.order.id, "", "returned")
        DeliveryReturn.objects.create(
            delivery_operation=operation,
            status_return=status_return
        )
    
    @staticmethod
    def execute_multi_order_pending_return(operation_ids: list, terminal_id: int):
        from orders.services.order_service import OrderService
        operations = DeliveryOperation.objects.filter(id__in=operation_ids)
        status_return = DeliveryStatus.objects.get(code="order_pending_returned")
        operations.update(current_status=status_return)
        DeliveryReturn.objects.bulk_create([
            DeliveryReturn(
                delivery_operation=operation,
                status_return=status_return,
                return_terminal_id=terminal_id
            )
            for operation in operations
        ])
        for operation in operations:
            operation.order.status = OrderStatus.objects.get(code="returned")
            operation.order.save()
            # create order history
            OrderService.create_order_history(operation.order.id, "", "returned")
        ReturnedRepository.bulk_create_operation_history(operation_ids, status_return)
    
    @staticmethod
    def execute_overdue_order(operation_id: int):
        from orders.services.order_service import OrderService
        operation = DeliveryOperation._base_manager.get(id=operation_id)
        status_return = DeliveryStatus.objects.get(code="overdue_order")
        operation.current_status = status_return
        operation.save()
        operation.order.status = OrderStatus.objects.get(code="returned")
        operation.order.save()
        # create order history
        OrderService.create_order_history(operation.order.id, "", "returned")
        DeliveryReturn.objects.create(
            delivery_operation=operation,
            status_return=status_return
        )
    
    @staticmethod
    def execute_multi_returned_order(operation_ids: list):
        from orders.services.order_service import OrderService
        operations = DeliveryOperation.objects.filter(id__in=operation_ids)
        status_return = DeliveryStatus.objects.get(code="returned_order")
        operations.update(current_status=status_return)
        DeliveryReturn.objects.bulk_create([
            DeliveryReturn(
                delivery_operation=operation,
                status_return=status_return
            )
            for operation in operations
        ])
        # update order status to returned
        for operation in operations:
            operation.order.status = OrderStatus.objects.get(code="returned")
            operation.order.save()
            # create order history
            OrderService.create_order_history(operation.order.id, "", "returned")
        ReturnedRepository.bulk_create_operation_history(operation_ids, status_return)
    
    @staticmethod
    def execute_multi_processed_order(operation_ids: list):
        from orders.services.order_service import OrderService
        operations = DeliveryOperation.objects.filter(id__in=operation_ids)
        status_return = DeliveryStatus.objects.get(code="processed_order")
        operations.update(current_status=status_return)
        DeliveryReturn.objects.bulk_create([
            DeliveryReturn(
                delivery_operation=operation,
                status_return=status_return
            )
            for operation in operations
        ])
        ReturnedRepository.bulk_create_operation_history(operation_ids, status_return)
    
    @staticmethod
    def bulk_create_operation_history(operation_ids: list, status: DeliveryStatus) -> None:
        operations = DeliveryOperation.objects.filter(id__in=operation_ids)
        histories = [
            DeliveryOperationHistory(
                delivery_operation=op,
                status=status,
                changed_by=op.created_by
            )
            for op in operations
        ]
        DeliveryOperationHistory.objects.bulk_create(histories)