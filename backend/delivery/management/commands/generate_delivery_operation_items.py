import random
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from delivery.models import DeliveryOperation, DeliveryOperationItem
from devices.models import PackagingSpecification, Device
from orders.models import OrderItem
from core.user.models import CoreUser


class Command(BaseCommand):
    help = 'Generate DeliveryOperationItem instances for a given DeliveryOperation ID'

    def handle(self, *args, **kwargs):
        operation_id = 101
        count = None
        assign_drones = True

        try:
            # Get the delivery operation
            delivery_operation = DeliveryOperation._base_manager.get(id=operation_id)
            self.stdout.write(
                self.style.SUCCESS(f'Found DeliveryOperation: {delivery_operation}')
            )

            # Get order items if not using random packages
            order_items = []
            order_items = list(delivery_operation.order.items.all())
            if not order_items:
                self.stdout.write(
                    self.style.WARNING('No order items found. Using random packages.')
                )

            # Determine count
            if count is None:
                count = len(order_items)

            # Get available packages
            available_packages = list(PackagingSpecification.objects.filter(active=True))
            if not available_packages:
                raise CommandError('No active PackagingSpecification found. Please create some packages first.')

            # Get available drones if assigning drones
            available_drones = []
            if assign_drones:
                available_drones = list(Device.objects.filter(
                    main_type__name__icontains='Drone',
                    active=True
                ))
                if not available_drones:
                    self.stdout.write(
                        self.style.WARNING('No active drones found. Items will be created without drone assignment.')
                    )
                    assign_drones = False

            # Generate items
            created_items = []
            with transaction.atomic():
                for i in range(count):
                    # Determine package
                    if i >= len(order_items):
                        package = random.choice(available_packages)
                    else:
                        # Try to use the package from order item
                        order_item = order_items[i]
                        if hasattr(order_item, 'package') and order_item.package:
                            package = order_item.package
                        else:
                            package = random.choice(available_packages)

                    # Create delivery operation item
                    item_data = {
                        'delivery_operation': delivery_operation,
                        'package': package,
                        'timestamp': timezone.now(),
                        'is_arrived': False,
                        'is_delivered': False
                    }

                    # Set arrived_at if is_arrived is True
                    if item_data['is_arrived']:
                        item_data['arrived_at'] = timezone.now() - timezone.timedelta(
                            hours=random.randint(1, 24)
                        )

                    # Assign drone if requested
                    if assign_drones and available_drones:
                        drone = random.choice(available_drones)
                        item_data['drone'] = drone
                        item_data['is_delivered_by_drone'] = random.choice([True, False])
                        
                        if item_data['is_delivered_by_drone']:
                            item_data['drone_arrived_at'] = timezone.now() - timezone.timedelta(
                                hours=random.randint(1, 12)
                            )

                    # Create the item
                    delivery_item = DeliveryOperationItem.objects.create(**item_data)
                    created_items.append(delivery_item)

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created DeliveryOperationItem {delivery_item.id} with package: {package.name}'
                        )
                    )

            # Summary
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully created {len(created_items)} DeliveryOperationItem(s) '
                    f'for DeliveryOperation {operation_id}'
                )
            )

            # Display summary information
            self.stdout.write('\n' + '='*50)
            self.stdout.write('SUMMARY:')
            self.stdout.write('='*50)
            self.stdout.write(f'DeliveryOperation ID: {delivery_operation.id}')
            self.stdout.write(f'Order: {delivery_operation.order.order_code}')
            self.stdout.write(f'Current Status: {delivery_operation.current_status.name}')
            self.stdout.write(f'Items Created: {len(created_items)}')
            
            arrived_count = sum(1 for item in created_items if item.is_arrived)
            drone_delivered_count = sum(1 for item in created_items if item.is_delivered_by_drone)
            
            self.stdout.write(f'Items Arrived: {arrived_count}')
            self.stdout.write(f'Items Delivered by Drone: {drone_delivered_count}')
            
            if assign_drones:
                assigned_drones = set(item.drone.name for item in created_items if item.drone)
                self.stdout.write(f'Drones Assigned: {", ".join(assigned_drones) if assigned_drones else "None"}')

        except DeliveryOperation.DoesNotExist:
            raise CommandError(f'DeliveryOperation with ID {operation_id} does not exist.')
        except Exception as e:
            raise CommandError(f'Error generating items: {str(e)}') 