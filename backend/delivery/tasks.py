from celery import shared_task
from delivery.services.drone_state_service import DroneStateAnalyzer
from delivery.models import DeliveryOperation, DeliveryOperationItem, DeliveryOperationApproval
import logging

logger = logging.getLogger(__name__)

@shared_task
def check_all_drones_state():
    """
    Celery task to check and update the state of all drones.
    This task is scheduled to run every minute via Celery Beat.
    """
    try:
        logger.info("🔄 Starting scheduled drone state check...")
        analyzer = DroneStateAnalyzer()
        results = analyzer.check_all_drones_state()
        
        logger.info(f"✅ Drone state check completed. Results: {results}")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error in scheduled drone state check: {str(e)}")
        return {"error": str(e)}


@shared_task
def send_anyang_status_callback_task(delivery_operation_id, old_status_code):
    """
    Shared task to send status change callback to Anyang delivery app
    """
    try:
        # Import here to avoid circular imports
        from third_api.services.anyang_services import AnyangCallbackService
        from delivery.models import DeliveryOperation

        # Get delivery operation instance
        delivery_operation = DeliveryOperation._base_manager.get(id=delivery_operation_id)

        success = AnyangCallbackService.send_status_callback(
            delivery_operation=delivery_operation, old_status_code=old_status_code
        )

        if success:
            logger.info(
                f"✅ [ANYANG CALLBACK] Successfully sent for operation {delivery_operation_id}"
            )
        else:
            logger.warning(
                f"⚠️  [ANYANG CALLBACK] Failed to send for operation {delivery_operation_id}"
            )

    except Exception as e:
        logger.error(
            f"❌ [ANYANG CALLBACK] Error sending callback for operation {delivery_operation_id}: {str(e)}"
        )


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def create_report_task(self, operation_id: int, order_code: str):
    """
    Celery task to create report asynchronously with retry mechanism
    """
    try:
        logger.info(f"🔄 Starting report creation for operation {operation_id} (order: {order_code}) - Task ID: {self.request.id}")
        
        # Clear the cache flag since we're now processing the task
        from django.core.cache import cache
        cache_key = f"report_task_scheduled_{operation_id}"
        cache.delete(cache_key)
        
        # Import here to avoid circular imports
        from report_template.models import ReportTemplate
        from report_template.utils import generate_report_template
        from print_format.services import PrintFormatService
        from django.http import HttpRequest
        from terminals.models import RouteTerminal
        
        
        
        # Get operation with proper transaction management for connection pooling
        try:
            logger.info(f"🔄 Getting operation {operation_id} with completed status")
            from django.db import transaction
            from django.db.models import Prefetch
            
            # Use transaction.atomic with a fresh connection to ensure latest data
            # This works better with connection pooling
            with transaction.atomic():
                # Force a new transaction to see the latest committed data
                operation = DeliveryOperation._base_manager.select_related(
                    'order',
                    'current_status',
                    'route',
                    'created_by'
                ).prefetch_related(
                    Prefetch('items', queryset=DeliveryOperationItem._base_manager.select_related('drone', 'order_item')),
                    Prefetch('order__items'),
                    Prefetch('approvals', queryset=DeliveryOperationApproval._base_manager.select_related('drone')),
                    Prefetch('route__route_terminals', queryset=RouteTerminal._base_manager.select_related('terminal')),
                ).get(id=operation_id)
            # Get the default report template
            try:
                report_template = ReportTemplate._base_manager.filter(is_default=True, is_enabled=True, group=operation.created_by.userprofilelink.group).first()
                if not report_template:
                    logger.warning("No default report template found")
                    return
            except Exception as e:
                logger.error(f"Error getting report template: {str(e)}")
                return
            # Verify operation is completed
            if operation.current_status.code != "completed_order":
                logger.warning(f"Operation {operation_id} is not completed (status: {operation.current_status.code})")
                # Check retry count to prevent infinite retries
                if self.request.retries >= 2:  # Max 3 attempts total
                    logger.error(f"❌ Operation {operation_id} not completed after {self.request.retries + 1} attempts. Giving up.")
                    return
                # Retry the task to wait for status update
                raise self.retry(
                    exc=Exception(f"Operation {operation_id} not completed. Current status: {operation.current_status.code}"),
                    countdown=5
                )
            
            logger.info(f"✅ Successfully got operation {operation_id} with completed status")
            
        except DeliveryOperation.DoesNotExist:
            logger.error(f"❌ Operation {operation_id} not found")
            # Check retry count to prevent infinite retries
            if self.request.retries >= 2:  # Max 3 attempts total
                logger.error(f"❌ Operation {operation_id} not found after {self.request.retries + 1} attempts. Giving up.")
                return
            # Retry the task to wait for transaction to commit
            raise self.retry(
                exc=Exception(f"Operation {operation_id} not found"),
                countdown=5
            )
        except Exception as e:
            logger.error(f"Error getting operation {operation_id}: {str(e)}")
            # Check retry count to prevent infinite retries
            if self.request.retries >= 2:  # Max 3 attempts total
                logger.error(f"❌ Error getting operation {operation_id} after {self.request.retries + 1} attempts. Giving up.")
                return
            raise self.retry(exc=e, countdown=5)
        
        # Prepare data for the report template
        order_data = PrintFormatService.get_report_template_data(
            report_template=report_template,
            instance=operation,
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
            template_type="pdf", 
            operation_id=operation.id,
            group_id = operation.created_by.userprofilelink.group.id if operation.created_by.userprofilelink.group else None
        )
        
        if result.get("success"):
            logger.info(
                "✅ Report created successfully for order %s: %s",
                order_code,
                result.get("file_url"),
            )
        else:
            logger.error(
                "❌ Failed to create report for order %s: %s",
                order_code,
                result.get("message"),
            )
            # Retry if failed
            raise self.retry(exc=Exception(f"Report generation failed: {result.get('message')}"))
            
    except Exception as e:
        logger.error(f"❌ Error in create_report_task for operation {operation_id}: {str(e)}")
        # Retry the task
        raise self.retry(exc=e)
    finally:
        # No cleanup needed when using transaction.atomic()
        pass


@shared_task
def send_anyang_terminal_callback_task(terminal_id, event_data):
    """
    Shared task to send terminal callback to Anyang endpoint
    """
    try:
        # Import here to avoid circular imports
        from third_api.signals import send_anyang_callback
        
        success = send_anyang_callback('/Callback', event_data)
        
        if success:
            logger.info(f"✅ [ANYANG TERMINAL CALLBACK] Successfully sent for terminal {terminal_id}")
        else:
            logger.warning(f"⚠️ [ANYANG TERMINAL CALLBACK] Failed to send for terminal {terminal_id}")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ [ANYANG TERMINAL CALLBACK] Error sending callback for terminal {terminal_id}: {str(e)}")
        return False


@shared_task
def send_anyang_notification_callback_task(notice_id, event_data):
    """
    Shared task to send notification callback to Anyang endpoint
    """
    try:
        # Import here to avoid circular imports
        from third_api.signals import send_anyang_callback
        
        success = send_anyang_callback('/Callback', event_data)
        
        if success:
            logger.info(f"✅ [ANYANG NOTIFICATION CALLBACK] Successfully sent for notice {notice_id}")
        else:
            logger.warning(f"⚠️ [ANYANG NOTIFICATION CALLBACK] Failed to send for notice {notice_id}")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ [ANYANG NOTIFICATION CALLBACK] Error sending callback for notice {notice_id}: {str(e)}")
        return False