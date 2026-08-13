from celery import shared_task
from django.conf import settings
import django
from django.db import connection

# Ensure Django is properly set up
if not settings.configured:
    django.setup()

from orders.models import Order, OrderItemType, OrderStatus, OrderHistory
from delivery.models import DeliveryOperation, DeliveryStatus
from delivery.services.returned_service import ReturnedService
from core.user.models import CoreUser

@shared_task
def check_order_statuses():
    """
    Daily task to check and update order statuses based on various conditions
    """
    
    try:
        user = CoreUser.objects.get(username="admin")
        # Get delivery operations that are in arrived_order status
        # Use _base_manager to bypass group filtering since there's no user context in Celery
        arrived_status = DeliveryStatus.objects.get(code='arrived_order')
        pending_return_status = DeliveryStatus.objects.get(code='order_pending_returned')
        arrived_delivery_operations = DeliveryOperation._base_manager.filter(current_status=arrived_status)
        pending_return_delivery_operations = DeliveryOperation._base_manager.filter(current_status=pending_return_status)

        for delivery_operation in arrived_delivery_operations:
            # Check delivery operation status
            try:
                is_returned = ReturnedService.check_arrived_order_timeout_no_pickup(delivery_operation.id)
                if is_returned:
                    # change order status to returned
                    order = delivery_operation.order
                    order.status = OrderStatus.objects.get(code='returned')
                    order.save()

                    # create history entry
                    OrderHistory.objects.create(
                        created_by=user,
                        modified_by=user,
                        order=order,
                        action='returned',
                        description="Order due for return"
                    )
            
            except Exception as e:
                print(f"Error processing delivery operation {delivery_operation.id}: {e}")
                continue

        for delivery_operation in pending_return_delivery_operations:
            # Check delivery operation status
            try:
                is_returned = ReturnedService.check_pending_order_timeout_no_pickup(delivery_operation.id)
                order = delivery_operation.order
                if is_returned:
                    # create history entry
                    OrderHistory.objects.create(
                        created_by=user,
                        modified_by=user,
                        order=order,
                        action='overdue',
                        description="Order overdue"
                    )
            except Exception as e:
                print(f"Error processing delivery operation {delivery_operation.id}: {e}")
                continue
        
    except Exception as e:
        print(f"Error in check_order_statuses: {e}")