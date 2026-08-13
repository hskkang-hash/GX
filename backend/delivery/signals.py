import logging
import json

from django.db.models.signals import post_save, pre_save
from django.db import transaction
from django.dispatch import receiver
from django.http import HttpRequest
from delivery.models import (
    DeliveryOperation,
    DeliveryOperationItem,
    DeliveryStatus,
    DeliveryOperationHistory,
    DeliveryOperationApproval,
)

from orders.models import Order, OrderItem
from print_format.services import PrintFormatService
from delivery.tasks import send_anyang_status_callback_task, create_report_task

logger = logging.getLogger(__name__)


# @receiver(post_save, sender=Order)
# def post_save_delivery_operation(sender, instance, created, **kwargs):
#     if created:
#         # Only create the DeliveryOperation, not the items
#         receipt_code = f"{timezone.now().strftime('%y%m%d')}{str(instance.id).zfill(6)}"
#         another_info = {
#             "etri": {
#                 "receipt_id": receipt_code
#             }
#         }
#         DeliveryOperation.objects.create(
#             order=instance,
#             current_status=DeliveryStatus.objects.get(code="unverified_order"),
#             another_info=another_info
#         )


@receiver(post_save, sender=DeliveryOperation)
def track_delivery_operation_status_change(sender, instance, created, **kwargs):
    if created:
        DeliveryOperationHistory.objects.create(
            delivery_operation=instance,
            status=instance.current_status,
            changed_by=instance.created_by,
        )
    else:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            old_instance = None

        if old_instance and old_instance.current_status != instance.current_status:
            DeliveryOperationHistory.objects.create(
                delivery_operation=instance,
                status=instance.current_status,
                changed_by=instance.created_by,
            )


# Store old status before save for Anyang callback
@receiver(pre_save, sender=DeliveryOperation)
def store_old_delivery_status(sender, instance, **kwargs):
    """Store old status before save to compare in post_save signal"""
    try:
        if instance.pk:
            old_instance = sender._base_manager.get(pk=instance.pk)
            instance._old_status_code = (
                old_instance.current_status.code
                if old_instance.current_status
                else None
            )
        else:
            instance._old_status_code = None
    except sender.DoesNotExist:
        instance._old_status_code = None







# Create Report Template when order status changes to delivered
@receiver(post_save, sender=DeliveryOperation)
def create_report_on_delivered(sender, instance, created, **kwargs):
    """Create a report template when order status changes to delivered."""

    # Skip for newly created orders
    if created:
        return

    new_status_code = instance.current_status.code if instance.current_status else None
    old_status_code = getattr(instance, "_old_status_code", None)

    # Check if status changed to 'completed_order'
    # Only create report if status actually changed to completed_order
    if new_status_code == "completed_order" and old_status_code != "completed_order":
        try:
            # Store operation ID for async processing
            operation_id = instance.id
            order_code = instance.order.order_code
            
            logger.info(
                "📋 Creating report for delivered order: %s (operation: %s, status: %s -> %s)",
                order_code,
                operation_id,
                old_status_code,
                new_status_code,
            )

            # Check if report task is already scheduled for this operation
            # Use Redis cache to prevent duplicate tasks
            from django.core.cache import cache
            cache_key = f"report_task_scheduled_{operation_id}"
            
            if cache.get(cache_key):
                logger.warning(
                    "⚠️ Report task already scheduled for operation %s (order: %s), skipping",
                    operation_id,
                    order_code,
                )
                return
            
            # Set cache flag to prevent duplicate tasks (expires in 5 minutes)
            cache.set(cache_key, True, timeout=300)
            
            # Schedule report creation as Celery task with delay to ensure transaction is committed
            # Use apply_async with countdown instead of transaction.on_commit
            create_report_task.apply_async(
                args=[operation_id, order_code],
                countdown=3  # Wait 3 seconds for transaction to commit
            )
            
            logger.info(
                "✅ Report task scheduled for operation %s (order: %s)",
                operation_id,
                order_code,
            )

        except Exception as e:
            logger.error(
                "❌ Error scheduling report creation for order %s: %s",
                instance.order.order_code,
                str(e),
            )



