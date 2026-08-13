from django.core.management.base import BaseCommand
from django.db import transaction
from orders.models import Order
from delivery.models import DeliveryOperation
import json


class Command(BaseCommand):
    help = 'Update external_status_code field from MISSION_STATUS in another_info JSON'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making actual changes to see what would be updated',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get all orders that have delivery operations with ETRI data
        orders_with_etri_data = Order.objects.filter(
            delivery_operation__another_info__isnull=False,
            delivery_operation__another_info__etri__isnull=False
        ).select_related('delivery_operation')
        
        total_orders = orders_with_etri_data.count()
        updated_count = 0
        error_count = 0
        
        self.stdout.write(f'Found {total_orders} orders with ETRI data to process...')
        
        with transaction.atomic():
            for order in orders_with_etri_data:
                try:
                    delivery_op = order.delivery_operation
                    another_info = delivery_op.another_info
                    
                    # Extract MISSION_STATUS from different possible paths
                    mission_status = None
                    
                    # Path 1: etri.receive_data.MISSION_STATUS (most common)
                    if ('etri' in another_info and 
                        'receive_data' in another_info['etri'] and 
                        'MISSION_STATUS' in another_info['etri']['receive_data']):
                        mission_status = another_info['etri']['receive_data']['MISSION_STATUS']
                    
                    # Path 2: etri.transmission_data.MISSION_STATUS
                    elif ('etri' in another_info and 
                          'transmission_data' in another_info['etri'] and 
                          'MISSION_STATUS' in another_info['etri']['transmission_data']):
                        mission_status = another_info['etri']['transmission_data']['MISSION_STATUS']
                    
                    # Path 3: etri.mission_status (direct field)
                    elif ('etri' in another_info and 
                          'mission_status' in another_info['etri']):
                        mission_status = another_info['etri']['mission_status']
                    
                    if mission_status is not None:
                        print(mission_status)
                        # Convert to string for external_status_code field
                        external_status_code = str(mission_status)
                        
                        # Only update if different from current value
                        if order.external_status_code != external_status_code:
                            self.stdout.write(
                                f'Order {order.order_code}: '
                                f'{order.external_status_code or "None"} -> {external_status_code}'
                            )
                            
                            if not dry_run:
                                order.external_status_code = external_status_code
                                order.save(update_fields=['external_status_code'])
                            
                            updated_count += 1
                        else:
                            self.stdout.write(
                                f'Order {order.order_code}: Already has correct status {external_status_code}'
                            )
                    else:
                        delivery_status = order.delivery_operation.current_status.code
                        if delivery_status == 'completed_order':
                            external_status_code = '4'
                        elif delivery_status == 'arrived_order':
                            external_status_code = '6'
                        elif delivery_status == 'in_transit_processing':
                            external_status_code = '5'
                        elif delivery_status == 'select_route_processing':
                            external_status_code = '3'
                        elif delivery_status == 'select_drone_processing':
                            external_status_code = '3'
                        elif delivery_status == 'verified_order':
                            external_status_code = '4'
                        elif delivery_status == 'unverified_order':
                            external_status_code = '4'
                        elif delivery_status == 'receipt_cancelled':
                            external_status_code = '5'
                        elif delivery_status == 'overdue_order':
                            external_status_code = '7'
                        elif delivery_status == 'returned_order':
                            external_status_code = '7'
                        elif delivery_status == 'processed_order':
                            external_status_code = '7'
                        elif delivery_status == 'order_pending_returned':
                            external_status_code = '7'
                        elif delivery_status == 'order_due_for_returned':
                            external_status_code = '7'
                        elif delivery_status == 'cancelled':
                            external_status_code = '5'

                        
                        if not dry_run:
                            order.external_status_code = external_status_code
                            order.save(update_fields=['external_status_code'])
                            updated_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'Order {order.order_code}: No MISSION_STATUS found in another_info'
                            )
                        )
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error processing order {order.order_code}: {str(e)}'
                        )
                    )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n=== SUMMARY ===\n'
                f'Total orders processed: {total_orders}\n'
                f'Orders updated: {updated_count}\n'
                f'Errors: {error_count}\n'
                f'Mode: {"DRY RUN" if dry_run else "LIVE UPDATE"}'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\nTo apply these changes, run the command without --dry-run flag'
                )
            ) 