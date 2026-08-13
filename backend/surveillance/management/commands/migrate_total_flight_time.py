"""Management command to migrate total_flight_time for completed surveillance profiles."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from surveillance.models import SurveillanceProfile


class Command(BaseCommand):
    help = (
        "Migrate total_flight_time measurement for completed surveillance profiles "
        "based on actual_start_time and actual_end_time."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview profiles that would be updated without persisting changes.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of profiles to process (useful for testing).",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print detailed information for each updated profile.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Update even if total_flight_time already exists.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options.get("dry_run", False)
        limit: int | None = options.get("limit")
        verbose: bool = options.get("verbose", False)
        force: bool = options.get("force", False)

        # Query completed profiles with actual_start_time and actual_end_time
        queryset = (
            SurveillanceProfile._base_manager.select_related("status")
            .filter(
                status__code="completed",
                actual_start_time__isnull=False,
                actual_end_time__isnull=False,
            )
            .order_by("id")
        )

        if limit:
            queryset = queryset[:limit]

        processed_count = 0
        skipped_count = 0
        error_count = 0

        self.stdout.write(
            self.style.SUCCESS(
                f"Found {queryset.count()} completed profiles with actual_start_time and actual_end_time"
            )
        )

        for profile in queryset:
            try:
                # Check if total_flight_time already exists
                existing_flight_time = profile.get_measurement("total_flight_time")
                if existing_flight_time and not force:
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping profile {profile.id} ({profile.code}): "
                                f"total_flight_time already exists: {existing_flight_time.get_numeric_value()} mins"
                            )
                        )
                    skipped_count += 1
                    continue

                # Calculate total_flight_time in minutes
                actual_start = profile.actual_start_time
                actual_end = profile.actual_end_time

                if actual_start and actual_end:
                    # Ensure timezone-aware
                    if timezone.is_naive(actual_start):
                        actual_start = timezone.make_aware(actual_start, timezone.get_current_timezone())
                    if timezone.is_naive(actual_end):
                        actual_end = timezone.make_aware(actual_end, timezone.get_current_timezone())

                    # Calculate difference in minutes
                    time_diff = actual_end - actual_start
                    total_minutes = time_diff.total_seconds() / 60.0

                    # Only update if time_diff is positive
                    if total_minutes <= 0:
                        if verbose:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Skipping profile {profile.id} ({profile.code}): "
                                    f"Invalid time range (actual_end_time <= actual_start_time)"
                                )
                            )
                        skipped_count += 1
                        continue

                    if dry_run:
                        if verbose:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"[DRY-RUN] Would set total_flight_time for profile {profile.id} ({profile.code}): "
                                    f"{total_minutes:.2f} mins "
                                    f"(from {actual_start.strftime('%Y-%m-%d %H:%M:%S')} to {actual_end.strftime('%Y-%m-%d %H:%M:%S')})"
                                )
                            )
                        processed_count += 1
                    else:
                        with transaction.atomic():
                            # Set measurement using the same format as other time measurements
                            # Format: "{int_value} mins" for consistency with estimated_time
                            profile.set_measurement("total_flight_time", f"{int(total_minutes)} mins")
                            
                            if verbose:
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"Updated profile {profile.id} ({profile.code}): "
                                        f"total_flight_time = {int(total_minutes)} mins "
                                        f"(from {actual_start.strftime('%Y-%m-%d %H:%M:%S')} to {actual_end.strftime('%Y-%m-%d %H:%M:%S')})"
                                    )
                                )
                            processed_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Error processing profile {profile.id} ({profile.code}): {str(e)}"
                    )
                )
                if verbose:
                    import traceback
                    self.stdout.write(traceback.format_exc())

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nMigration complete - "
                f"Processed: {processed_count}, "
                f"Skipped: {skipped_count}, "
                f"Errors: {error_count}"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nThis was a dry run. No changes were persisted. "
                    "Run without --dry-run to apply changes."
                )
            )

