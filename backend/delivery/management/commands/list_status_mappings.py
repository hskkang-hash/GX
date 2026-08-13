from django.core.management.base import BaseCommand
from django.db.models import Count
from orders.models import OrderStatusMapping as DeliveryStatusMapping  # Using alias for compatibility
from delivery.models import DeliveryStatus
from core.user.models import UserGroup


class Command(BaseCommand):
    help = 'List existing status mappings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--groups',
            nargs='*',
            help='Group codes to filter by (default: show all groups)',
        )
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Show only active mappings',
        )

    def handle(self, *args, **options):
        """Execute the command"""
        groups_filter = options.get('groups')
        active_only = options['active_only']

        self.stdout.write(
            self.style.SUCCESS('📋 Status Mappings Report')
        )
        self.stdout.write("=" * 80)

        # Build queryset
        queryset = DeliveryStatusMapping.objects.filter(deleted__isnull=True)
        
        if active_only:
            queryset = queryset.filter(is_active=True)
            
        if groups_filter:
            queryset = queryset.filter(group__code__in=groups_filter)

        # Get mappings with related data using ForeignKey
        mappings = queryset.select_related('status', 'group').order_by('status__code')

        if not mappings.exists():
            self.stdout.write(
                self.style.WARNING('No status mappings found with the specified criteria.')
            )
            return

        # Group by status for better display
        mappings_by_status = {}
        for mapping in mappings:
            status_code = mapping.status.code
            if status_code not in mappings_by_status:
                mappings_by_status[status_code] = []
            mappings_by_status[status_code].append(mapping)

        # Display statistics
        total_mappings = mappings.count()
        active_mappings = mappings.filter(is_active=True).count()
        inactive_mappings = total_mappings - active_mappings
        total_groups = mappings.values('group').distinct().count()

        self.stdout.write(f"\n📊 STATISTICS:")
        self.stdout.write(f"  Total mappings: {total_mappings}")
        self.stdout.write(f"  Active: {active_mappings}")
        self.stdout.write(f"  Inactive: {inactive_mappings}")
        self.stdout.write(f"  Groups involved: {total_groups}")

        # Display mappings by status
        self.stdout.write(f"\n📝 MAPPINGS BY STATUS:")
        self.stdout.write("-" * 80)

        for status_code, status_mappings in mappings_by_status.items():
            status_name = status_mappings[0].status.name
            self.stdout.write(f"\n🏷️  Status: {status_code} ({status_name})")
            
            for mapping in status_mappings:
                # Get group
                group = mapping.group
                group_name = f"{group.code}({group.name})" if group else None
                
                # Status indicator
                status_indicator = "✅" if mapping.is_active else "❌"
                
                # Colors
                bg_color = mapping.background_color or "None"
                text_color = mapping.text_color or "None"
                border_color = mapping.border_color or "None"
                
                self.stdout.write(f"  {status_indicator} {mapping.custom_name}")
                self.stdout.write(f"     Group: {group_name}")
                self.stdout.write(f"     Colors: BG={bg_color}, Text={text_color}, Border={border_color}")
                if mapping.custom_code:
                    self.stdout.write(f"     Custom Code: {mapping.custom_code}")
                self.stdout.write(f"     ID: {mapping.id}")

        # Display groups summary
        if not groups_filter:
            self.stdout.write(f"\n👥 GROUPS SUMMARY:")
            self.stdout.write("-" * 80)
            
            groups_with_mappings = UserGroup.objects.filter(
                deliverystatusmapping__in=mappings
            ).annotate(
                mapping_count=Count('deliverystatusmapping', distinct=True)
            ).order_by('code')

            for group in groups_with_mappings:
                active_count = mappings.filter(group=group, is_active=True).count()
                inactive_count = mappings.filter(group=group, is_active=False).count()
                self.stdout.write(
                    f"  🏢 {group.code} ({group.name}): "
                    f"{group.mapping_count} total (✅{active_count}, ❌{inactive_count})"
                )

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(
            self.style.SUCCESS('✅ Report completed!')
        )

    def get_version(self):
        return "1.0.0" 