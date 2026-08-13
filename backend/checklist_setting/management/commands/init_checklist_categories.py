from core.multilanguage.request_handlers import (
    create_model_with_translations,
    update_model_with_translations,
)
from django.core.management.base import BaseCommand
from django.db import transaction
from checklist_setting.models import ChecklistSettingCategory


class Command(BaseCommand):
    help = "Initialize default checklist setting categories"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-update",
            action="store_true",
            help="Force update existing categories with new names",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        categories = [
            {
                "code": "pre-flight-check",
                "name": {"en": "Pre-flight Check", "ko": "비행 전 점검","th": "การตรวจสอบก่อนการบิน"},
            },
            {
                "code": "controller-check",
                "name": {"en": "Controller Check", "ko": "조종 장치 점검","th": "การตรวจสอบการควบคุม"},
            },
            {
                "code": "weather-check",
                "name": {"en": "Weather Check", "ko": "날씨 점검","th": "การตรวจสอบสภาพอากาศ"},
            },
        ]

        self.stdout.write("Starting checklist categories initialization...")

        # Check if any categories already exist
        existing_categories = ChecklistSettingCategory.objects.filter(
            code__in=[cat["code"] for cat in categories]
        )

        if existing_categories.exists() and not options["force_update"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Found {existing_categories.count()} existing categories. "
                    "Use --force-update to update existing records."
                )
            )

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for category_data in categories:
            try:
                # Check if category exists first
                if ChecklistSettingCategory.objects.filter(
                    code=category_data["code"]
                ).exists():
                    existing_category = ChecklistSettingCategory.objects.get(
                        code=category_data["code"]
                    )

                    if (
                        options["force_update"]
                        or existing_category.name != category_data["name"]
                    ):
                        update_model_with_translations(existing_category, category_data)
                        updated_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"Updated ChecklistSettingCategory: {existing_category.name} ({existing_category.code})"
                            )
                        )
                    else:
                        skipped_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Skipped ChecklistSettingCategory '{existing_category.name}' - already exists with correct data."
                            )
                        )
                else:
                    # Create new category
                    category = create_model_with_translations(
                        ChecklistSettingCategory, category_data
                    )
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created ChecklistSettingCategory: {category.name} ({category.code})"
                        )
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error processing category {category_data['code']}: {str(e)}"
                    )
                )

        # Summary
        self.stdout.write(self.style.SUCCESS(f"\nInitialization complete!"))
        self.stdout.write(f"  - Created: {created_count} new categories")
        self.stdout.write(f"  - Updated: {updated_count} categories")
        self.stdout.write(f"  - Skipped: {skipped_count} categories")

        # Show current categories
        self.stdout.write("\nCurrent checklist categories in database:")
        all_categories = ChecklistSettingCategory.objects.all().order_by("code")
        for cat in all_categories:
            self.stdout.write(f"  - {cat.code}: {cat.name}")
