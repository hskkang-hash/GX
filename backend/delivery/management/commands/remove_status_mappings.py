from django.core.management.base import BaseCommand
from django.db import transaction
from orders.models import OrderStatusMapping as DeliveryStatusMapping  
from core.user.models import UserGroup


class Command(BaseCommand):
    help = 'Remove status mappings for specified groups'

    def add_arguments(self, parser):
        parser.add_argument(
            '--groups',
            nargs='*',
            default=['etri', 'anyang'],
            help='Group codes to remove mappings for (default: etri anyang)',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm the deletion (required to actually delete)',
        )

    def handle(self, *args, **options):
        """Execute the command"""
        groups_to_process = options['groups']
        confirm = options['confirm']

        if not confirm:
            self.stdout.write(
                self.style.WARNING('This is a DRY RUN. Use --confirm to actually delete mappings.')
            )

        self.stdout.write(
            self.style.SUCCESS('Starting status mappings removal...')
        )

        try:
            with transaction.atomic():
                total_removed = 0

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

                    # Find all mappings for this group using ForeignKey
                    mappings = DeliveryStatusMapping.objects.filter(
                        group=group,
                        deleted__isnull=True
                    )

                    count = mappings.count()
                    self.stdout.write(f"  Found {count} mappings for group {group_code}")

                    if count > 0:
                        if confirm:
                            # Actually delete the mappings (soft delete)
                            for mapping in mappings:
                                status_code = mapping.status.code
                                custom_name = mapping.custom_name
                                mapping.delete()  # Soft delete through BaseModel
                                self.stdout.write(f"    ✓ Removed mapping: {status_code} -> {custom_name}")
                                total_removed += 1
                        else:
                            # Dry run - just show what would be deleted
                            for mapping in mappings:
                                status_code = mapping.status.code
                                custom_name = mapping.custom_name
                                self.stdout.write(f"    [DRY RUN] Would remove: {status_code} -> {custom_name}")
                                total_removed += 1

                # Summary
                self.stdout.write(f"\n" + "="*50)
                if confirm:
                    self.stdout.write(f"SUMMARY:")
                    self.stdout.write(f"  Removed: {total_removed} mappings")
                    
                    if total_removed > 0:
                        self.stdout.write(
                            self.style.SUCCESS(f"\n✓ Status mappings removed successfully!")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"\n- No mappings were found to remove.")
                        )
                else:
                    self.stdout.write(f"DRY RUN SUMMARY:")
                    self.stdout.write(f"  Would remove: {total_removed} mappings")
                    self.stdout.write(
                        self.style.WARNING(f"\n- This was a dry run. Use --confirm to actually delete.")
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\n✗ Error removing status mappings: {str(e)}")
            )
            raise e

    def get_version(self):
        return "1.0.0" 