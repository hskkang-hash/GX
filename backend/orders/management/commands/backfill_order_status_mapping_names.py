from django.core.management.base import BaseCommand
from django.db import transaction
from django.db import models

from orders.models import OrderStatusMapping


class Command(BaseCommand):
    help = "Backfill 'name' for OrderStatusMapping as 'Status mapping for {group-name}' when missing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show changes without saving to the database",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run: bool = options.get("dry_run", False)
        qs = OrderStatusMapping.objects.select_related("group").filter(
            models.Q(name__isnull=True) | models.Q(name="")
        )
        updated = 0
        skipped = 0
        for mapping in qs:
            group = getattr(mapping, "group", None)
            if not group:
                skipped += 1
                continue
            new_name = f"Status mapping for {group.name}"
            self.stdout.write(f"Mapping ID {mapping.id}: '{mapping.name}' -> '{new_name}'")
            mapping.name = new_name
            if not dry_run:
                mapping.save(update_fields=["name"]) 
            updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Completed. Updated: {updated}, Skipped (no group): {skipped}. Dry-run: {dry_run}"
        )) 