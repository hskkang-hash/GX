from django.core.management.base import BaseCommand
from django.db import transaction
from orders.models import OrderStatus

class Command(BaseCommand):
    help = 'Creates default order status values'

    @transaction.atomic
    def handle(self, *args, **options):
        statuses = [
            {
                "code": "delivered",
                "name": "Delivered",
                "description": "Order has been delivered to the recipient"
            },
            {
                "code": "pending_confirmation",
                "name": "Pending Confirmation",
                "description": "Order is waiting for seller confirmation"
            },
            {
                "code": "awaiting_shipment",
                "name": "Awaiting Shipment",
                "description": "Order is confirmed and waiting to be shipped"
            },
            {
                "code": "cancelled",
                "name": "Cancelled",
                "description": "Order has been cancelled"
            },
            {
                "code": "pending_processing",
                "name": "Pending Processing",
                "description": "Order is being processed by the system"
            },
            {
                "code": "awaiting_payment",
                "name": "Awaiting Payment",
                "description": "Order is waiting for payment completion"
            },
            {
                "code": "returned",
                "name": "Returned",
                "description": "Order has been returned by the recipient"
            },
            {
                "code": "receipt_cancelled",
                "name": "Receipt Cancelled",
                "description": "Order has been cancelled by the recipient"
            }
        ]
        
        created_count = 0
        for status_data in statuses:
            # Check if status already exists
            status, created = OrderStatus.objects.get_or_create(
                code=status_data["code"],
                defaults=status_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created OrderStatus: {status.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"OrderStatus '{status.name}' already exists."))
        
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} new OrderStatus records."))
    
    def _create_order_status_constants(self):
        """Create constants in a file if no OrderStatus model exists"""
        from orders.models import Order
        
        # Check if Order model has a STATUSES attribute or choices for status field
        status_field = Order._meta.get_field('status')
        if hasattr(status_field, 'choices') and status_field.choices:
            self.stdout.write(self.style.WARNING("Order.status already has choices defined. No action needed."))
            return
            
        # Create constants file
        constants_file_path = 'orders/constants.py'
        
        # Define the statuses
        statuses = [
            ('DELIVERED', 'delivered', 'Delivered'),
            ('PENDING_CONFIRMATION', 'pending_confirmation', 'Pending Confirmation'),
            ('AWAITING_SHIPMENT', 'awaiting_shipment', 'Awaiting Shipment'),
            ('CANCELLED', 'cancelled', 'Cancelled'),
            ('PENDING_PROCESSING', 'pending_processing', 'Pending Processing'),
            ('AWAITING_PAYMENT', 'awaiting_payment', 'Awaiting Payment'),
            ('PAYMENT_FAILED', 'payment_failed', 'Payment Failed'),
            ('RETURNED', 'returned', 'Returned')
        ]
        
        # Generate the file content
        content = """# Order Status Constants
class OrderStatus:
"""
        
        for const_name, code, display_name in statuses:
            content += f"    {const_name} = '{code}'  # {display_name}\n"
            
        content += "\n\n# Order Status Choices for models\n"
        content += "ORDER_STATUS_CHOICES = [\n"
        for _, code, display_name in statuses:
            content += f"    ('{code}', '{display_name}'),\n"
        content += "]\n"
        
        # Write to file
        import os
        if not os.path.exists(constants_file_path):
            with open(constants_file_path, 'w') as f:
                f.write(content)
            self.stdout.write(self.style.SUCCESS(f"Created {constants_file_path} with status constants"))
        else:
            # Append to existing file
            with open(constants_file_path, 'a') as f:
                f.write("\n\n" + content)
            self.stdout.write(self.style.SUCCESS(f"Appended status constants to {constants_file_path}"))
            
        self.stdout.write(self.style.SUCCESS("Created order status constants. You will need to update your Order model to use these constants.")) 