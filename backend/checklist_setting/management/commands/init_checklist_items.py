from core.multilanguage.request_handlers import (
    create_model_with_translations,
    update_model_with_translations,
)
from django.core.management.base import BaseCommand
from django.db import transaction
from checklist_setting.models import ChecklistSetting, ChecklistSettingCategory


class Command(BaseCommand):
    help = "Initialize default checklist items for each category"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-update",
            action="store_true",
            help="Force update existing checklist items with new names",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # Define checklist items for each category with translations
        checklist_items = {
            "pre-flight-check": [
                {
                    "item_name": {
                        "en": "Check propeller direction, damage, and fixation",
                        "ko": "프로펠러 방향, 손상 및 고정 상태 점검",
                        "th": "ตรวจสอบทิศทาง, ความเสียหาย และการติดตั้งของเครื่องยนต์"
                    }
                },
                {
                    "item_name": {
                        "en": "Check bolts, nuts, and looseness on the frame",
                        "ko": "프레임의 볼트, 너트 및 느슨함 점검",
                        "th": "ตรวจสอบคัน, น้ำมัน และการปล่อยตัวของเครื่องยนต์"
                    }
                },
                {
                    "item_name": {
                        "en": "Check battery fully charged and secured",
                        "ko": "배터리 완전 충전 및 고정 상태 점검",
                        "th": "ตรวจสอบการชาร์จครบและการติดตั้งของแบตเตอรี่"
                    }
                },
                {
                    "item_name": {
                        "en": "Check sensor values (GPS, IMU, compass, etc.)",
                        "ko": "센서 값 점검 (GPS, IMU, 나침반 등)",
                        "th": "ตรวจสอบค่าของส่วนประกอบ (GPS, IMU, ระบบสอบเทียน เป็นต้น)"
                    }
                },
                {
                    "item_name": {
                        "en": "Check camera and payload device operation",
                        "ko": "카메라 및 페이로드 장치 작동 점검",
                        "th": "ตรวจสอบการทำงานของกล้องและอุปกรณ์ที่พิมพ์"
                    }
                },
                {
                    "item_name": {
                        "en": "Check assigned items (hub, delivery point, route, etc.)",
                        "ko": "할당된 항목 점검 (허브, 배송 지점, 경로 등)",
                        "th": "ตรวจสอบอุปกรณ์ที่จัดส่ง (ศูนย์, จุดจัดส่ง, เส้นทาง เป็นต้น)"
                    }
                },
                {
                    "item_name": {
                        "en": "Check ID device and antenna installation",
                        "ko": "ID 장치 및 안테나 설치 상태 점검",
                        "th": "ตรวจสอบการติดตั้งอุปกรณ์ ID และอุปกรณ์สอบเทียน"
                    }
                },
                {
                    "item_name": {
                        "en": "Drone sensors",
                        "ko": "드론 센서",
                        "th": "ส่วนประกอบของสิ่งประดิษฐ์"
                    }
                },
            ],
            "controller-check": [
                {
                    "item_name": {
                        "en": "Check battery connection and power status",
                        "ko": "배터리 연결 및 전원 상태 점검",
                        "th": "ตรวจสอบการเชื่อมต่อและสถานะการใช้งานของแบตเตอรี่"
                    }
                },
                {
                    "item_name": {
                        "en": "Check control mode and operation status",
                        "ko": "제어 모드 및 작동 상태 점검",
                        "th": "ตรวจสอบการควบคุมและสถานะการใช้งานของสิ่งประดิษฐ์"
                    }
                },
                {
                    "item_name": {
                        "en": "Check controller signal",
                        "ko": "컨트롤러 신호 점검",
                        "th": "ตรวจสอบสัญญาณของสิ่งประดิษฐ์"
                    }
                },
                {
                    "item_name": {
                        "en": "Check for abnormal conditions in controller",
                        "ko": "컨트롤러의 비정상 상태 점검",
                        "th": "ตรวจสอบสถานะที่ผิดปกติในสิ่งประดิษฐ์"
                    }
                },
            ],
            "weather-check": [
                {
                    "item_name": {
                        "en": "Check for adverse weather: wind, rain, snow...",
                        "ko": "불리한 날씨 점검: 바람, 비, 눈...",
                        "th": "ตรวจสอบสภาพอากาศที่ไม่ดี: ลม, ฝน, หิมะ..."
                    }
                },
                {
                    "item_name": {
                        "en": "Check internal temperature of the drone",
                        "ko": "드론의 내부 온도 점검",
                        "th": "ตรวจสอบอุณหภูมิภายในของสิ่งประดิษฐ์"
                    }
                },
            ],
        }

        self.stdout.write("Starting checklist items initialization...")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for category_code, items in checklist_items.items():
            try:
                # Get the category
                category = ChecklistSettingCategory.objects.filter(code=category_code).first()
                if not category:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Category '{category_code}' not found. Please run init_checklist_categories first."
                        )
                    )
                    continue

                self.stdout.write(f"\nProcessing category: {category.name} ({category_code})")

                for item_data in items:
                    try:
                        item_name_en = item_data["item_name"]["en"]
                        # Check if item already exists in this category
                        existing_item = ChecklistSetting.objects.filter(
                            item_name=item_name_en,
                            category=category
                        ).first()

                        if existing_item:
                            if options["force_update"]:
                                # Update existing item with translations
                                update_model_with_translations(existing_item, item_data)
                                updated_count += 1
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"  Updated: {item_name_en}"
                                    )
                                )
                            else:
                                skipped_count += 1
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"  Skipped: {item_name_en} (already exists)"
                                    )
                                )
                        else:
                            # Create new item with translations
                            item_data["category"] = category
                            new_item = create_model_with_translations(
                                ChecklistSetting, item_data
                            )
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"  Created: {item_name_en}"
                                )
                            )

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"  Error processing item '{item_name_en}': {str(e)}"
                            )
                        )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error processing category {category_code}: {str(e)}"
                    )
                )

        # Summary
        self.stdout.write(self.style.SUCCESS(f"\nInitialization complete!"))
        self.stdout.write(f"  - Created: {created_count} new checklist items")
        self.stdout.write(f"  - Updated: {updated_count} checklist items")
        self.stdout.write(f"  - Skipped: {skipped_count} checklist items")

        # Show current checklist items by category
        self.stdout.write("\nCurrent checklist items in database:")
        all_categories = ChecklistSettingCategory.objects.all().order_by("code")
        for cat in all_categories:
            self.stdout.write(f"\n{cat.name} ({cat.code}):")
            items = ChecklistSetting.objects.filter(category=cat).order_by("item_name")
            for item in items:
                self.stdout.write(f"  - {item.item_name}")
            if not items.exists():
                self.stdout.write("  (No items)")
