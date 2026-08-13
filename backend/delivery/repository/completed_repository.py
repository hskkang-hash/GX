from orders.models import OrderItem
from delivery.models import (
    DeliveryStatus,
    DeliveryOperation,
    DeliveryOperationItem,
    DeliveryOperationHistory,
    DeliveryCancellation,
    DeliveryOperationApproval,
)
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
)
from django.db.models.functions import Concat, Coalesce
from delivery.services.status_mapping_service import StatusMappingService


class CompletedRepository:
    @staticmethod
    def get_completed_statuses() -> QuerySet:
        return DeliveryStatus.objects.filter(
            code__in=["arrived_order", "completed_order"]
        )

    @staticmethod
    def get_arrived_operations() -> QuerySet:
        order_items_count = (
            OrderItem.objects.filter(order=OuterRef("order"))
            .values("order")
            .annotate(count=Count("id"))
            .values("count")
        )

        # Latest cancellation for reason_for_rejection
        latest_cancellation = DeliveryCancellation.objects.filter(
            delivery_operation=OuterRef("pk")
        ).order_by("-cancelled_at")

        # Get mapping annotations from StatusMappingService
        mapping_annotations = StatusMappingService.build_annotate_with_mapping(
            context="delivery_operation"
        )

        return (
            DeliveryOperation.objects.filter(current_status__code="arrived_order")
            .select_related(
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
                order_identifier=F("another_info__anyang__itemOrgId"),
                receipt_number=F("another_info__etri__receipt_id"),
                handler=Concat(
                    Coalesce(
                        F("created_by__last_name"), Value(""), output_field=CharField()
                    ),
                    Value(" "),
                    Coalesce(
                        F("created_by__first_name"), Value(""), output_field=CharField()
                    ),
                    output_field=CharField(),
                ),
                tracking_number=F("another_info__etri__tracking_number"),
                reason_for_rejection=Coalesce(
                    Subquery(latest_cancellation.values("reason")[:1]),
                    F("order__cancel_reason"),
                ),
                # Use dynamic mapping annotations
                **mapping_annotations
            )
            .order_by("-id")
        )

    @staticmethod
    def get_completed_operations() -> QuerySet:
        order_items_count = (
            OrderItem.objects.filter(order=OuterRef("order"))
            .values("order")
            .annotate(count=Count("id"))
            .values("count")
        )

        # Latest cancellation for reason_for_rejection
        latest_cancellation = DeliveryCancellation.objects.filter(
            delivery_operation=OuterRef("pk")
        ).order_by("-id")

        # Get mapping annotations from StatusMappingService
        mapping_annotations = StatusMappingService.build_annotate_with_mapping(
            context="delivery_operation"
        )

        return (
            DeliveryOperation.objects.filter(current_status__code="completed_order")
            .select_related(
                'current_status',
                'order',
                'order__created_by',
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
                # Grid required fields - using double underscore format for grid compatibility
                order__id=F("order__id"),
                order__order_code=F("order__order_code"),
                order__created_on=F("order__created_on"),
                order__sender_name=F("order__sender_name"),
                order__recipient_name=F("order__recipient_name"),
                creator=Concat(
                    Coalesce(F("order__created_by__first_name"), Value(""), output_field=CharField()),
                    Value(" "),
                    Coalesce(F("order__created_by__last_name"), Value(""), output_field=CharField()),
                    output_field=CharField()
                ),
                # New columns
                order_identifier=F("another_info__anyang__itemOrgId"),
                receipt_number=F("another_info__etri__receipt_id"),
                handler=Concat(
                    Coalesce(
                        F("created_by__last_name"), Value(""), output_field=CharField()
                    ),
                    Value(" "),
                    Coalesce(
                        F("created_by__first_name"), Value(""), output_field=CharField()
                    ),
                    output_field=CharField(),
                ),
                tracking_number=F("another_info__etri__tracking_number"),
                reason_for_rejection=Coalesce(
                    Subquery(latest_cancellation.values("reason")[:1]),
                    F("order__cancel_reason"),
                ),
                # Use dynamic mapping annotations
                **mapping_annotations
            )
            .order_by("-id")
        )

    @staticmethod
    def get_items_by_completed(operation_id: int) -> QuerySet:
        return DeliveryOperationItem.objects.filter(delivery_operation_id=operation_id)

    @staticmethod
    def get_items_by_arrived(operation_id: int) -> QuerySet:
        return DeliveryOperationItem.objects.filter(delivery_operation_id=operation_id)

    @staticmethod
    def get_arrived_operation_by_id(operation_id: int) -> DeliveryOperation:
        """
        Check if the order is in the previous step,
        if it is in the previous step then return the result,
        otherwise return None
        """
        try:
            return DeliveryOperation.objects.get(
                id=operation_id, current_status__code="in_transit_processing"
            )
        except DeliveryOperation.DoesNotExist:
            return None

    @staticmethod
    def get_completed_operation_by_id(operation_id: int) -> DeliveryOperation:
        """
        Check if the order is in the previous step,
        if it is in the previous step then return the result,
        otherwise return None
        """
        try:
            return DeliveryOperation.objects.get(
                id=operation_id, current_status__code="arrived_order"
            )
        except DeliveryOperation.DoesNotExist:
            return None

    @staticmethod
    def get_completed_operations_by_ids(operation_ids: list) -> QuerySet:
        return DeliveryOperation.objects.filter(
            id__in=operation_ids, current_status__code="arrived_order"
        )

    @staticmethod
    def execute_complete_operation(operation: DeliveryOperation) -> DeliveryOperation:
        operation.current_status = DeliveryStatus.objects.get(code="completed_order")
        operation.save()
        return operation

    @staticmethod
    def execute_complete_operations(operations: QuerySet) -> None:
        status = DeliveryStatus.objects.get(code="completed_order")
        # Use individual saves instead of bulk update to trigger signals
        for operation in operations:
            operation.current_status = status
            operation.save()  # This will trigger pre_save and post_save signals
        CompletedRepository.bulk_create_operation_history(operations, status)

    @staticmethod
    def bulk_create_operation_history(
        operations: QuerySet, status: DeliveryStatus
    ) -> None:
        histories = [
            DeliveryOperationHistory(
                delivery_operation=op, status=status, changed_by=op.created_by
            )
            for op in operations
        ]
        DeliveryOperationHistory.objects.bulk_create(histories)

    @staticmethod
    def execute_arrived_operation(operation: DeliveryOperation) -> DeliveryOperation:
        operation.current_status = DeliveryStatus.objects.get(code="arrived_order")
        operation.save()
        return operation

    @staticmethod
    def download_report(operation_id: int, template_type="pdf"):
        """
        Get the download URL for an existing report that was auto-generated.
        If report doesn't exist, create it first.
        
        Args:
            operation_id: ID of the delivery operation
            template_type: Type of report (pdf or docx)
            
        Returns:
            dict: Dictionary containing file URL and success status
        """
        try:
            operation = DeliveryOperation.objects.get(id=operation_id)
            
            # Kiểm tra xem operation đã completed chưa
            if operation.current_status.code != "completed_order":
                return {
                    'success': False,
                    'message': f'Operation {operation_id} is not completed yet. Status: {operation.current_status.code}',
                    'operation_id': operation_id
                }
            
            # Tìm file report trên MinIO dựa trên naming convention
            # File được tạo bởi signal: report-{operation_id}-{timestamp}.pdf
            from core.file_management.models import UserMediaFile
            
            # Tìm file có tên chứa operation_id và đúng định dạng
            file_extension = 'pdf' if template_type == 'pdf' else 'docx'
            search_pattern = f"report-{operation_id}-"
            
            # Tìm file trong UserMediaFile với tên chứa pattern
            report_files = UserMediaFile._base_manager.filter(
                file_name__startswith=search_pattern,
                file_name__endswith=f'.{file_extension}'
            ).order_by('-created_on')
            
            if report_files.exists():
                latest_report = report_files.first()
                return {
                    'success': True,
                    'file_url': latest_report.file_url,
                    'file_name': latest_report.file_name,
                    'operation_id': operation_id,
                    'file_size': latest_report.file_size,
                    'created_on': latest_report.created_on
                }
            else:
                # Nếu không tìm thấy file, tạo report mới
                return CompletedRepository._create_report_for_operation(operation, template_type)
                
        except DeliveryOperation.DoesNotExist:
            return {
                'success': False,
                'message': f'Delivery operation with ID {operation_id} not found',
                'operation_id': operation_id
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving report: {str(e)}',
                'operation_id': operation_id
            }

    @staticmethod
    def _create_report_for_operation(operation: DeliveryOperation, template_type="pdf"):
        """
        Tạo report mới cho operation nếu chưa có
        
        Args:
            operation: DeliveryOperation instance
            template_type: Type of report (pdf or docx)
            
        Returns:
            dict: Dictionary containing file URL and success status
        """
        try:
            from report_template.models import ReportTemplate
            from report_template.utils import generate_report_template
            from print_format.services import PrintFormatService
            from django.http import HttpRequest
            from terminals.models import RouteTerminal
            from django.db.models import Prefetch
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Get the default report template
            try:
                report_template = ReportTemplate._base_manager.filter(is_default=True, is_enabled=True, group=operation.created_by.userprofilelink.group).first()
                if not report_template:
                    return {
                        'success': False,
                        'message': 'No default report template found',
                        'operation_id': operation.id
                    }
            except Exception as e:
                logger.error(f"Error getting report template: {str(e)}")
                return {
                    'success': False,
                    'message': f'Error getting report template: {str(e)}',
                    'operation_id': operation.id
                }
            
            # Get operation with proper relations for report generation
            try:
                operation_with_relations = DeliveryOperation._base_manager.select_related(
                    'order',
                    'current_status',
                    'route',
                    'created_by'
                ).prefetch_related(
                    Prefetch('items', queryset=DeliveryOperationItem._base_manager.select_related('drone', 'order_item')),
                    Prefetch('order__items'),
                    Prefetch('approvals', queryset=DeliveryOperationApproval._base_manager.select_related('drone')),
                    Prefetch('route__route_terminals', queryset=RouteTerminal._base_manager.select_related('terminal')),
                ).get(id=operation.id)
                
            except Exception as e:
                logger.error(f"Error getting operation with relations: {str(e)}")
                return {
                    'success': False,
                    'message': f'Error getting operation data: {str(e)}',
                    'operation_id': operation.id
                }
            
            # Prepare data for the report template
            order_data = PrintFormatService.get_report_template_data(
                report_template=report_template,
                instance=operation_with_relations,
                model_name="delivery.deliveryoperation",
                language=operation.created_by.language.code if operation.created_by.language else 'en'
            )
            
            # Update usage count
            report_template.usage_count += 1
            report_template.save()
            
            # Create a mock request for the report generation
            request = HttpRequest()
            request.user = operation.created_by
            
            # Generate report
            result = generate_report_template(
                request=request, 
                data=order_data, 
                template_type=template_type, 
                operation_id=operation.id,
                group_id = operation.created_by.userprofilelink.group.id if operation.created_by.userprofilelink.group else None
            )
            
            if result.get("success"):
                logger.info(f"✅ Report created successfully for operation {operation.id}: {result.get('file_url')}")
                
                # Tìm lại file vừa tạo để lấy thông tin đầy đủ
                from core.file_management.models import UserMediaFile
                file_extension = 'pdf' if template_type == 'pdf' else 'docx'
                search_pattern = f"report-{operation.id}-"
                
                report_files = UserMediaFile._base_manager.filter(
                    file_name__startswith=search_pattern,
                    file_name__endswith=f'.{file_extension}'
                ).order_by('-created_on')
                
                if report_files.exists():
                    latest_report = report_files.first()
                    return {
                        'success': True,
                        'file_url': latest_report.full_url,
                        'file_name': latest_report.file_name,
                        'operation_id': operation.id,
                        'file_size': latest_report.file_size,
                        'created_on': latest_report.created_on
                    }
                else:
                    # Fallback nếu không tìm thấy file trong database
                    return {
                        'success': True,
                        'file_url': result.get('file_url'),
                        'file_name': result.get('file_name', f'report-{operation.id}.{template_type}'),
                        'operation_id': operation.id,
                        'file_size': None,
                        'created_on': None
                    }
            else:
                logger.error(f"❌ Failed to create report for operation {operation.id}: {result.get('message')}")
                return {
                    'success': False,
                    'message': f'Failed to create report: {result.get("message")}',
                    'operation_id': operation.id
                }
                
        except Exception as e:
            logger.error(f"❌ Error in _create_report_for_operation for operation {operation.id}: {str(e)}")
            return {
                'success': False,
                'message': f'Error creating report: {str(e)}',
                'operation_id': operation.id
            }