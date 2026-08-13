from print_format.models import PrintFormat
from delivery.models import (
    DeliveryStatus, 
    DeliveryOperation, 
    DeliveryOperationItem,
    DeliveryOperationHistory,
    DeliveryCancellation
)
from django.db.models import QuerySet
from orders.models import Order, OrderItem
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.db.models import OuterRef, Subquery, Count, Max, F, Case, When, BooleanField, Exists, CharField, Sum, Value, Q
from django.db.models.functions import Concat, Coalesce
from delivery.services.status_mapping_service import StatusMappingService

class VerificationRepository:
    @staticmethod
    def get_verification_statuses() -> QuerySet:
        return DeliveryStatus.objects.filter(code__in=["unverified_order", "verified_order"])

    @staticmethod
    def get_unverified_operations() -> QuerySet:
        order_items_count = OrderItem.objects.filter(
            order=OuterRef('order'),
        ).values('order').annotate(
            count=Count('id')
        ).values('count')
        
        # Latest cancellation for reason_for_rejection
        latest_cancellation = DeliveryCancellation.objects.filter(
            delivery_operation=OuterRef('pk')
        ).order_by('-cancelled_at')
        
        # Get mapping annotations from StatusMappingService
        mapping_annotations = StatusMappingService.build_annotate_with_mapping(context='delivery_operation')
        
        return DeliveryOperation.objects.filter(
            current_status__code="unverified_order"
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
            reason_for_rejection=Coalesce(
                Subquery(latest_cancellation.values('reason')[:1]),
                F('order__cancel_reason')
            ),
            # Use dynamic mapping annotations
            **mapping_annotations
        ).order_by('-id')
    
    @staticmethod
    def get_verified_operations() -> QuerySet:
        order_items_count = OrderItem.objects.filter(
            order=OuterRef('order'),
        ).values('order').annotate(
            count=Count('id')
        ).values('count')
        
        # Latest cancellation for reason_for_rejection
        latest_cancellation = DeliveryCancellation.objects.filter(
            delivery_operation=OuterRef('pk')
        ).order_by('-cancelled_at')
        
        # Get mapping annotations from StatusMappingService
        mapping_annotations = StatusMappingService.build_annotate_with_mapping(context='delivery_operation')
        
        return DeliveryOperation.objects.filter(
            current_status__code="verified_order"
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
            reason_for_rejection=Coalesce(
                Subquery(latest_cancellation.values('reason')[:1]),
                F('order__cancel_reason')
            ),
            # Use dynamic mapping annotations
            **mapping_annotations
        ).order_by('-id')
    
    @staticmethod
    def get_unverified_operation_by_id(operation_id: int) -> DeliveryOperation:
        try:
            order_items_count = OrderItem.objects.filter(
                order=OuterRef('order'),
            ).values('order').annotate(
                count=Count('id')
            ).values('count')
            
            # Latest cancellation for reason_for_rejection
            latest_cancellation = DeliveryCancellation.objects.filter(
                delivery_operation=OuterRef('pk')
            ).order_by('-cancelled_at')
            
            # Get mapping annotations from StatusMappingService
            mapping_annotations = StatusMappingService.build_annotate_with_mapping(context='delivery_operation')
            
            return DeliveryOperation.objects.filter(
                id=operation_id, 
                current_status__code="unverified_order"
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
                reason_for_rejection=Coalesce(
                    Subquery(latest_cancellation.values('reason')[:1]),
                    F('order__cancel_reason')
                ),
                # Use dynamic mapping annotations
                **mapping_annotations
            ).first()
        except DeliveryOperation.DoesNotExist:
            return None
    
    @staticmethod
    def get_verified_operation_by_id(operation_id: int) -> DeliveryOperation:
        try:
            package_count = OrderItem.objects.filter(
                order=OuterRef('order'),
            ).values('order').annotate(
                count=Count('package_id', distinct=True)
            ).values('count')
            
            # Latest cancellation for reason_for_rejection
            latest_cancellation = DeliveryCancellation.objects.filter(
                delivery_operation=OuterRef('pk')
            ).order_by('-cancelled_at')
            
            # Get mapping annotations from StatusMappingService
            mapping_annotations = StatusMappingService.build_annotate_with_mapping(context='delivery_operation')
            
            return DeliveryOperation.objects.filter(
                id=operation_id, 
                current_status__code="verified_order"
            ).annotate(
                number_of_packages=Subquery(package_count),
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
                reason_for_rejection=Coalesce(
                    Subquery(latest_cancellation.values('reason')[:1]),
                    F('order__cancel_reason')
                ),
                # Use dynamic mapping annotations
                **mapping_annotations
            ).first()
        except DeliveryOperation.DoesNotExist:
            return None
    
    @staticmethod
    def verify_operation(operation: DeliveryOperation) -> DeliveryOperation:
        operation.current_status = DeliveryStatus.objects.get(code="verified_order")
        operation.save()
        # create delivery operation items
        try:
            VerificationRepository.create_delivery_operation_items(operation.order.items.all())
        except Exception as e:
            return operation
        return operation
    
    @staticmethod
    def get_operations_by_operation_ids(operation_ids: list) -> QuerySet:
        return DeliveryOperation.objects.filter(
            id__in=operation_ids, 
            current_status__code="unverified_order"
        ).annotate(
            number_of_packages=Count('order__items__package_id', distinct=True)
        )

    @staticmethod
    def verify_operations(operations: QuerySet) -> QuerySet:
        with transaction.atomic():
            try:
                operations = VerificationRepository.bulk_verify_operations(operations)
                VerificationRepository.create_delivery_operations_items(operations)
            except ObjectDoesNotExist:
                raise ValueError("DeliveryStatus with code 'verified_order' not found")
        return operations

    
    @staticmethod
    def bulk_verify_operations(operations: QuerySet) -> None:
        status = DeliveryStatus.objects.get(code="verified_order")
        operation_ids = list(operations.values_list('id', flat=True))
        operations.update(current_status=status)
        updated_operations = DeliveryOperation.objects.filter(id__in=operation_ids).annotate(number_of_packages=Count('order__items__package_id', distinct=True))
        VerificationRepository.bulk_create_operation_history(updated_operations, status)
        return updated_operations
    
    @staticmethod
    def bulk_create_operation_history(operations: QuerySet, status: DeliveryStatus) -> None:
        histories = [
            DeliveryOperationHistory(
                delivery_operation=op,
                status=status,
                changed_by=op.created_by
            )
            for op in operations
        ]
        DeliveryOperationHistory.objects.bulk_create(histories)
        
    @staticmethod
    def execute_processing_order(operation_id: int, template_id: int) -> DeliveryOperation:
        operation = VerificationRepository.get_verified_operation_by_id(operation_id)
        if operation:
            operation.current_status = DeliveryStatus.objects.get(code="select_route_processing")
            operation.save()
            template = PrintFormat.objects.get(id=template_id)
            template.usage_count += 1
            template.save()
            return operation
        return None

    @staticmethod
    def create_delivery_operation_items(items: list) -> None:
        for item in items:
            delivery_operation = DeliveryOperation._base_manager.get(order=item.order)
            if delivery_operation:
                DeliveryOperationItem.objects.create(
                    delivery_operation=delivery_operation,
                    order_item=item
                )
    
    @staticmethod
    def create_delivery_operations_items(delivery_operations: QuerySet) -> None:
        for delivery_operation in delivery_operations:
            VerificationRepository.create_delivery_operation_items(delivery_operation.order.items.all())
