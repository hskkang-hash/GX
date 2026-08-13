import time
from django.core.management.base import BaseCommand
from orders.models import OrderHistory, Order, OrderStatus

class Command(BaseCommand):
    help = 'Create order history'

    def handle(self, *args, **kwargs):
        order_ids = [65]
        step = "pending_confirmation"
        reason = ""

        for order_id in order_ids:
            order = Order.objects.get(id=order_id)

            print(f"Processing order {order_id}")
            # Create order history
            # if step is cancelled, create 3 histories records: paid, cancelled, refunded. update order status to cancelled
            if step == "cancelled":
                reason = "Customer requested cancellation"
                OrderHistory.objects.create(
                    order=order,
                    action='paid',
                    description=reason
                )
                # add delay 1 second
                time.sleep(1)
                OrderHistory.objects.create(
                    order=order,
                    action='cancelled',
                    description=reason
                )
                time.sleep(1)
                OrderHistory.objects.create(
                    order=order,
                    action='refunded',
                    description=reason
                )
                order.status = OrderStatus.objects.get(code='cancelled')
                order.save()
                
            # if step is pending_processing, create 2 histories records: paid, verified. update order status to pending_processing
            if step == "pending_processing":
                reason = "Order is being processed"
                OrderHistory.objects.create(
                    order=order,
                    action='paid',
                    description=reason
                )
                time.sleep(1)
                OrderHistory.objects.create(
                    order=order,
                    action='verified',
                    description=reason
                )
                order.status = OrderStatus.objects.get(code='pending_processing')
                order.save()

            # if step is returned, create 4 history record: paid, verified, arrived, returned. update order status to returned
            if step == "returned":
                reason = "Order is being returned"
                OrderHistory.objects.create(
                    order=order,
                    action='paid',
                    description=reason
                )
                time.sleep(1)
                OrderHistory.objects.create(
                    order=order,
                    action='verified',
                    description=reason
                )
                time.sleep(1)
                OrderHistory.objects.create(
                    order=order,
                    action='arrived',
                    description=reason
                )
                time.sleep(1)
                OrderHistory.objects.create(
                    order=order,
                    action='returned',
                    description=reason
                )
                order.status = OrderStatus.objects.get(code='returned')
                order.save()    

            # if step is awaiting_shipment, create 2 histories records: paid, verified. update order status to awaiting_shipment
            if step == "awaiting_shipment":
                reason = "Order is being shipped"
                OrderHistory.objects.create(
                    order=order,
                    action='paid',
                    description=reason
                )
                time.sleep(1)
                OrderHistory.objects.create(
                    order=order,
                    action='verified',
                    description=reason
                )
                order.status = OrderStatus.objects.get(code='awaiting_shipment')
                order.save()

            # if step is delivered, create 4 histories records: paid, verified, arrived, completed. update order status to delivered
            if step == "delivered":
                reason = "Order is being delivered"
                OrderHistory.objects.create(
                    order=order,
                    action='paid',
                    description=reason
                )
                time.sleep(1)
                OrderHistory.objects.create(
                    order=order,
                    action='verified',
                    description=reason
                )
                time.sleep(1)
                OrderHistory.objects.create(
                    order=order,
                    action='arrived',
                    description=reason
                )
                time.sleep(1)
                OrderHistory.objects.create(
                    order=order,
                    action='completed',
                    description=reason
                )
                order.status = OrderStatus.objects.get(code='delivered')
                order.save()

            # if step is pending_confirmation, create 1 history record: paid. update order status to pending_confirmation
            if step == "pending_confirmation":
                reason = "Order is being confirmed"
                OrderHistory.objects.create(
                    order=order,
                    action='paid',
                    description=reason
                )
                order.status = OrderStatus.objects.get(code='pending_confirmation')
                order.save()
