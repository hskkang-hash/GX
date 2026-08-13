from django.core.management.base import BaseCommand
from django.db import transaction
from orders.models import ExternalOrderStatus, OrderStatusMapping
from delivery.models import DeliveryStatus
from core.user.models import UserGroup


class Command(BaseCommand):
    help = 'Initialize ExternalOrderStatus and OrderStatusMapping data for ETRI status mapping'

    def add_arguments(self, parser):
        parser.add_argument(
            '--group-code',
            type=str,
            default='etri',
            help='Group code to create mappings for (default: etri)',
        )
        parser.add_argument(
            '--recreate',
            action='store_true',
            help='Delete existing data and recreate all mappings',
        )

    def handle(self, *args, **options):
        group_code = options['group_code']
        recreate = options['recreate']
        
        try:
            # Get or create the group
            group, created = UserGroup.objects.get_or_create(
                code=group_code,
                defaults={'name': f'{group_code.upper()} Group'}
            )
            
            if created:
                self.stdout.write(f'Created group: {group.name}')
            else:
                self.stdout.write(f'Using existing group: {group.name}')
            
            if recreate:
                self.stdout.write(self.style.WARNING('Recreating all status mapping data...'))
                # Delete existing data for this group
                ExternalOrderStatus.objects.filter(group=group).delete()
                OrderStatusMapping.objects.filter(group=group).delete()
                self.stdout.write('Deleted existing data')
            
            # Color mapping based on STATUS_MAPPING_COLOR provided by user
            status_color_mapping = {
                '0': '#0CBA47',  # completed_order - Green for completed
                '1': '#EE533D',  # cancelled - Red for cancelled/failed
                '2': '#6495ED',  # in_transit_processing - Blue for in transit
                '3': '#1E90FF',  # select_route_processing, select_drone_processing - Blue for waiting
                '4': '#9C9D9D',  # unverified_order - Gray for pending
                '5': '#EE533D',  # receipt_cancelled - Red for cancelled
                '6': '#EB7509',  # arrived_order - Orange for arrived
                '7': '#EE533D',  # returned statuses - Red for returned/cancelled
            }
            
            # ETRI External Status definitions with colors
            external_statuses_data = [
                {
                    'value': '0',
                    'name': 'Delivery Completed',
                    'name_kr': '배송완료',
                    'description': 'Delivery is complete (when the control system receives information that delivery is complete)',
                    'description_kr': '배송이 완료된 상태 (관제시스템에서 배송을 완료했다는 정보를 받았을 때)',
                    'background_color': status_color_mapping['0'],
                    'text_color': '#FFFFFF',
                    'border_color': status_color_mapping['0']
                },
                {
                    'value': '1',
                    'name': 'Delivery Cancelled',
                    'name_kr': '배송취소',
                    'description': 'Delivery is rejected or delivery failed (reason for cancellation must also be indicated)',
                    'description_kr': '배송이 거절된 상태 또는 배송이 실패한 상태 (취소된 이유도 같이 표시해야 함)',
                    'background_color': status_color_mapping['1'],
                    'text_color': '#FFFFFF',
                    'border_color': status_color_mapping['1']
                },
                {
                    'value': '2',
                    'name': 'In Delivery',
                    'name_kr': '배송중',
                    'description': 'Delivery is in progress (when the control system receives information that delivery has started)',
                    'description_kr': '배송 중인 상태 (관제시스템에서 배송을 시작했다는 정보를 받았을 때)',
                    'background_color': status_color_mapping['2'],
                    'text_color': '#FFFFFF',
                    'border_color': status_color_mapping['2']
                },
                {
                    'value': '3',
                    'name': 'Waiting for Delivery',
                    'name_kr': '배송대기',
                    'description': 'The operator has completed the delivery acceptance process, but delivery has not yet started',
                    'description_kr': '운영자가 배송 접수처리를 완료한 상태지만 아직 배송을 시작하지 않은 상태',
                    'background_color': status_color_mapping['3'],
                    'text_color': '#FFFFFF',
                    'border_color': status_color_mapping['3']
                },
                {
                    'value': '4',
                    'name': 'Receipt Completed',
                    'name_kr': '접수완료',
                    'description': 'The acceptance has been completed, but the operator has not confirmed it',
                    'description_kr': '접수된 상태지만 운영자가 확인하지 않은 상태',
                    'background_color': status_color_mapping['4'],
                    'text_color': '#FFFFFF',
                    'border_color': status_color_mapping['4']
                },
                {
                    'value': '5',
                    'name': 'Receipt Cancelled',
                    'name_kr': '접수취소',
                    'description': 'The operator or the orderer cancellation of application',
                    'description_kr': '운영자 또는 주문자가 접수를 취소한 상태',
                    'background_color': status_color_mapping['5'],
                    'text_color': '#FFFFFF',
                    'border_color': status_color_mapping['5']
                },
                {
                    'value': '6',
                    'name': 'Delivery Arrived',
                    'name_kr': '배송 도착',
                    'description': 'Delivery has arrived at destination but not yet completed',
                    'description_kr': '배송이 목적지에 도착했지만 아직 완료되지 않은 상태',
                    'background_color': status_color_mapping['6'],
                    'text_color': '#FFFFFF',
                    'border_color': status_color_mapping['6']
                },
                {
                    'value': '7',
                    'name': 'Delivery Returned',
                    'name_kr': '배송 반송',
                    'description': 'Delivery has been returned or is in return process',
                    'description_kr': '배송이 반송되었거나 반송 과정 중인 상태',
                    'background_color': status_color_mapping['7'],
                    'text_color': '#FFFFFF',
                    'border_color': status_color_mapping['7']
                }
            ]
            
            # Status mappings organized by delivery_status (ManyToMany structure)
            # Each delivery_status can map to multiple external_values
            # Updated to match STATUS_MAPPING provided by user
            status_mappings = {
                'completed_order': ['0'],                # Delivery Completed - 배송완료
                'cancelled': ['1'],                      # Delivery Cancelled - 배송취소
                'in_transit_processing': ['2'],          # In Delivery - 배송중
                'verified_order': ['4'],                 # Receipt Completed - 접수완료 (UPDATED to match STATUS_MAPPING)
                'unverified_order': ['4'],               # Receipt Completed - 접수완료
                'select_route_processing': ['3'],        # Waiting for Delivery - 배송대기
                'select_drone_processing': ['3'],        # Waiting for Delivery - 배송대기
                'arrived_order': ['6'],                  # Delivery Arrived - 배송 도착 (UPDATED to match STATUS_MAPPING_COLOR)
                'receipt_cancelled': ['5'],              # Receipt Cancelled - 접수취소
                # Added returned status mappings
                'overdue_order': ['7'],                  # Delivery Returned - 배송 반송
                'returned_order': ['7'],                 # Delivery Returned - 배송 반송
                'processed_order': ['7'],                # Delivery Returned - 배송 반송
                'order_pending_returned': ['7'],         # Delivery Returned - 배송 반송
                'order_due_for_returned': ['7'],         # Delivery Returned - 배송 반송
            }

            created_external_count = 0
            created_mapping_count = 0
            
            with transaction.atomic():
                # Create ExternalOrderStatus records
                self.stdout.write('Creating ExternalOrderStatus records...')
                for status_data in external_statuses_data:
                    external_status, created = ExternalOrderStatus.objects.get_or_create(
                        group=group,
                        value=status_data['value'],
                        defaults={
                            'name': status_data['name'],
                            'description': status_data['description'],
                            'is_active': True,
                            'background_color': status_data['background_color'],
                            'text_color': status_data['text_color'],
                            'border_color': status_data['border_color']
                        }
                    )
                    
                    if created:
                        created_external_count += 1
                        self.stdout.write(f'  ✓ Created: {status_data["value"]} - {status_data["name"]} (Color: {status_data["background_color"]})')
                    else:
                        # Update colors for existing records if they don't have colors
                        if not external_status.background_color:
                            external_status.background_color = status_data['background_color']
                            external_status.text_color = status_data['text_color']
                            external_status.border_color = status_data['border_color']
                            external_status.save(update_fields=['background_color', 'text_color', 'border_color'])
                            self.stdout.write(f'  ✓ Updated colors for: {status_data["value"]} - {status_data["name"]} (Color: {status_data["background_color"]})')
                        else:
                            self.stdout.write(f'  ✓ Exists: {status_data["value"]} - {status_data["name"]} (Color: {external_status.background_color})')
                
                # Create OrderStatusMapping records with ManyToMany relationships
                self.stdout.write('\nCreating OrderStatusMapping records...')
                for delivery_status_code, external_values in status_mappings.items():
                    try:
                        # Get the delivery status
                        delivery_status = DeliveryStatus.objects.get(code=delivery_status_code)
                        
                        # Get or create the mapping for this delivery status
                        mapping, created = OrderStatusMapping.objects.get_or_create(
                            group=group,
                            delivery_status=delivery_status,
                            defaults={
                                'is_active': True
                            }
                        )
                        
                        # Get all external statuses for this mapping
                        external_statuses = []
                        for external_value in external_values:
                            try:
                                external_status = ExternalOrderStatus.objects.get(
                                    group=group,
                                    value=external_value
                                )
                                external_statuses.append(external_status)
                            except ExternalOrderStatus.DoesNotExist:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f'  ✗ External status {external_value} not found'
                                    )
                                )
                        
                        if external_statuses:
                            # Set the ManyToMany relationships
                            mapping.external_order_statuses.set(external_statuses)
                            
                            if created:
                                created_mapping_count += 1
                                self.stdout.write(
                                    f'  ✓ Created: {delivery_status.code} ({delivery_status.name}) -> '
                                    f'[{", ".join([ext.value for ext in external_statuses])}]'
                                )
                            else:
                                self.stdout.write(
                                    f'  ✓ Updated: {delivery_status.code} ({delivery_status.name}) -> '
                                    f'[{", ".join([ext.value for ext in external_statuses])}]'
                                )
                            
                            # Show detailed mapping
                            for ext in external_statuses:
                                self.stdout.write(
                                    f'    - {ext.value} ({ext.name})'
                                )
                                
                    except DeliveryStatus.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ✗ Delivery status {delivery_status_code} not found'
                            )
                        )
            
            # Summary
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n=== SUMMARY ===\n'
                    f'Group: {group.name}\n'
                    f'ExternalOrderStatus created: {created_external_count}\n'
                    f'OrderStatusMapping created: {created_mapping_count}\n'
                    f'Total ExternalOrderStatus: {ExternalOrderStatus.objects.filter(group=group).count()}\n'
                    f'Total OrderStatusMapping: {OrderStatusMapping.objects.filter(group=group).count()}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error occurred: {str(e)}')
            )
            raise 