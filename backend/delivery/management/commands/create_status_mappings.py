from django.core.management.base import BaseCommand
from core.middleware.refresh_token import set_current_request
from django.contrib.auth.models import AnonymousUser  
from delivery.models import DeliveryStatus
from orders.models import OrderStatusMapping as DeliveryStatusMapping  # Using alias for compatibility
from core.user.models import UserGroup


class Command(BaseCommand):
    help = 'Create status mappings for ETRI and Anyang groups based on legacy hardcoded logic'

    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing mappings if they exist',
        )
        parser.add_argument(
            '--groups',
            nargs='*',
            default=['etri', 'anyang'],
            help='Group codes to create mappings for (default: etri anyang)',
        )

    def handle(self, *args, **options):
        """Execute the command"""
        self.stdout.write(
            self.style.SUCCESS('Starting status mappings creation...')
        )

        groups_to_process = options['groups']
        overwrite = options['overwrite']

        # Status mapping configuration based on legacy hardcoded logic
        STATUS_MAPPINGS = {
            'unverified_order': {
                'custom_name': 'Receipt Completed',
                'background_color': '#9C9D9D',
                'text_color': '#FFFFFF'
            },
            'verified_order': {
                'custom_name': 'Waiting for Delivery', 
                'background_color': '#1D9BE2',
                'text_color': '#FFFFFF'
            },
            'select_route_processing': {
                'custom_name': 'Waiting for Delivery',
                'background_color': '#1E90FF',
                'text_color': '#FFFFFF'
            },
            'select_drone_processing': {
                'custom_name': 'Waiting for Delivery',
                'background_color': '#4682B4',
                'text_color': '#FFFFFF'
            },
            'in_transit_processing': {
                'custom_name': 'In Delivery',
                'background_color': '#6495ED',
                'text_color': '#FFFFFF'
            },
            'completed_order': {
                'custom_name': 'Delivery Completed',
                'background_color': '#0CBA47',
                'text_color': '#FFFFFF'
            },
            'arrived_order': {
                'custom_name': 'Delivery Completed',
                'background_color': '#EB7509',
                'text_color': '#FFFFFF'
            },
            'delivered': {
                'custom_name': 'Delivery Completed',
                'background_color': '#0CBA47',
                'text_color': '#FFFFFF'
            },
            'cancelled': {
                'custom_name': 'Delivery Cancelled',
                'background_color': '#EE533D',
                'text_color': '#FFFFFF'
            },
            'receipt_cancelled': {
                'custom_name': 'Receipt Cancelled',
                'background_color': '#EE533D',
                'text_color': '#FFFFFF'
            },
            'returned': {
                'custom_name': 'Delivery Cancelled',
                'background_color': '#EE533D',
                'text_color': '#FFFFFF'
            }
        }

        try:
            
                total_created = 0
                total_updated = 0
                total_skipped = 0

                for group_code in groups_to_process:
                    self.stdout.write(f"\nProcessing group: {group_code}")
                    
                    # Get the group
                    try:
                        group = UserGroup.objects.get(code=group_code)
                        self.stdout.write(f"  Found group: {group.name}")
                    except UserGroup.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(f"  Group with code '{group_code}' not found. Skipping...")
                        )
                        continue

                    # Process each status mapping
                    for status_code, mapping_config in STATUS_MAPPINGS.items():
                        try:
                            # Get the delivery status
                            status = DeliveryStatus.objects.get(code=status_code)
                        except DeliveryStatus.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f"    Status '{status_code}' not found. Skipping...")
                            )
                            continue

                        # Check if mapping already exists
                        existing_mapping = DeliveryStatusMapping.objects.filter(
                            status=status,
                            group=group,
                            deleted__isnull=True
                        ).first()

                        if existing_mapping:
                            if overwrite:
                                # Update existing mapping
                                existing_mapping.custom_name = mapping_config['custom_name']
                                existing_mapping.background_color = mapping_config['background_color']
                                existing_mapping.text_color = mapping_config['text_color']
                                existing_mapping.border_color = mapping_config['background_color']  # Use same as background
                                existing_mapping.is_active = True
                                existing_mapping.save()
                                
                                self.stdout.write(f"    ✓ Updated mapping: {status_code} -> {mapping_config['custom_name']}")
                                total_updated += 1
                            else:
                                self.stdout.write(f"    - Skipped existing mapping: {status_code}")
                                total_skipped += 1
                        else:
                            # Create new mapping with ForeignKey group
                            mapping = DeliveryStatusMapping.objects.create(
                                status=status,
                                group=group,  # ForeignKey assignment
                                custom_name=mapping_config['custom_name'],
                                background_color=mapping_config['background_color'],
                                text_color=mapping_config['text_color'],
                                border_color=mapping_config['background_color'],  # Use same as background
                                is_active=True
                            )
                            
                            self.stdout.write(f"    ✓ Created mapping: {status_code} -> {mapping_config['custom_name']}")
                            total_created += 1

                # Summary
                self.stdout.write(f"\n" + "="*50)
                self.stdout.write(f"SUMMARY:")
                self.stdout.write(f"  Created: {total_created} mappings")
                self.stdout.write(f"  Updated: {total_updated} mappings") 
                self.stdout.write(f"  Skipped: {total_skipped} mappings")
                self.stdout.write(f"  Total:   {total_created + total_updated + total_skipped} mappings")
                
                if total_created > 0 or total_updated > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f"\n✓ Status mappings created/updated successfully!")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"\n- No mappings were created or updated.")
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\n✗ Error creating status mappings: {str(e)}")
            )
            raise e

    def get_version(self):
        return "1.0.0" 