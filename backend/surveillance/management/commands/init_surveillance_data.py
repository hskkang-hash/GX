"""
Django management command to initialize Surveillance data
Run: python manage.py init_surveillance_data
"""

from typing import Tuple

from django.core.management.base import BaseCommand

from surveillance.models import (
    MissionPurpose,
    SurveillanceProfileRepeatType,
    SurveillanceProfileRepeatUntilType,
    SurveillanceStatus,
    SurveyMissionStatus,
)
from core.multilanguage.request_handlers import create_model_with_translations, update_model_with_translations
from core.configuration.models import AdminConfig

class Command(BaseCommand):
    help = 'Initialize Survey Mission Status data with multi-language support (EN, KR, TH)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🚀 Starting Surveillance Data Initialization...\n'))
        
        self.init_surveillance_status()
        self.init_repeat_catalogs()
        self.init_survey_mission_status()
        self.init_overdue_profile_settings()
        self.stdout.write(self.style.SUCCESS('\n✅ All Surveillance data initialized successfully!\n'))
    
    def init_surveillance_status(self):
        """Initialize Surveillance Status data with multi-language support."""

        self.stdout.write(self.style.WARNING('\n📋 Initializing Surveillance Status...'))

        # Giữ lại danh sách trạng thái gốc (đã comment) làm tài liệu tham khảo và mở rộng cho luồng phê duyệt/lặp.
        SURVEILLANCE_STATUS_LIST = [
            {
                "code": "pending_approval",
                "name": {
                    "en": "Pending Approval",
                    "ko": "승인대기",
                    "th": "รอการอนุมัติ",
                },
                "description": {
                    "en": "Profile is waiting for approval",
                    "ko": "프로파일이 승인을 기다리고 있습니다",
                    "th": "โปรไฟล์กำลังรอการอนุมัติ",
                },
                "color_code": "#FFA500",
            },
            {
                "code": "pending_device_check",
                "name": {
                    "en": "Pending Device Check",
                    "ko": "장비 점검 대기",
                    "th": "รอตรวจสอบอุปกรณ์",
                },
                "description": {
                    "en": "Profile is waiting for device readiness confirmation",
                    "ko": "프로파일이 장비 점검 확인을 기다리고 있습니다",
                    "th": "โปรไฟล์กำลังรอการยืนยันความพร้อมของอุปกรณ์",
                },
                "color_code": "#7B68EE",
            },
            {
                "code": "approved",
                "name": {
                    "en": "Approved",
                    "ko": "승인됨",
                    "th": "อนุมัติ",
                },
                "description": {
                    "en": "Profile has been approved and ready for execution",
                    "ko": "프로파일이 승인되어 실행 준비가 되었습니다",
                    "th": "โปรไฟล์ได้รับการอนุมัติและพร้อมสำหรับการปฏิบัติการ",
                },
                "color_code": "#4CAF50",
            },
            {
                "code": "in_progress",
                "name": {
                    "en": "In Progress",
                    "ko": "진행 중",
                    "th": "กำลังดำเนินการ",
                },
                "description": {
                    "en": "Profile is currently being executed",
                    "ko": "프로파일이 실행 중입니다",
                    "th": "โปรไฟล์กำลังดำเนินการอยู่",
                },
                "color_code": "#2196F3",
            },
            {
                "code": "completed",
                "name": {
                    "en": "Completed",
                    "ko": "완료됨",
                    "th": "เสร็จสมบูรณ์",
                },
                "description": {
                    "en": "Profile execution has been completed",
                    "ko": "프로파일 실행이 완료되었습니다",
                    "th": "การปฏิบัติการของโปรไฟล์เสร็จสมบูรณ์แล้ว",
                },
                "color_code": "#2E7D32",
            },
            {
                "code": "rejected",
                "name": {
                    "en": "Rejected",
                    "ko": "반려됨",
                    "th": "ปฏิเสธ",
                },
                "description": {
                    "en": "Profile has been rejected",
                    "ko": "프로파일이 반려되었습니다",
                    "th": "โปรไฟล์ถูกปฏิเสธ",
                },
                "color_code": "#F44336",
            },
            {
                "code": "cancelled",
                "name": {
                    "en": "Cancelled",
                    "ko": "취소됨",
                    "th": "ยกเลิก",
                },
                "description": {
                    "en": "Profile has been cancelled",
                    "ko": "프로파일이 취소되었습니다",
                    "th": "โปรไฟล์ถูกยกเลิก",
                },
                "color_code": "#9E9E9E",
            },
        ]

        created_count = 0
        updated_count = 0

        for status in SURVEILLANCE_STATUS_LIST:
            existing_obj = SurveillanceStatus.objects.filter(code=status["code"]).first()
            if existing_obj:
                update_model_with_translations(existing_obj, status)
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'  ⟳ Updated: {status["code"]}'))
            else:
                create_model_with_translations(SurveillanceStatus, status)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {status["code"]}'))

        self.stdout.write(
            self.style.SUCCESS(
                '\n  📊 Surveillance Status Summary:'
                f'\n     Created: {created_count}'
                f'\n     Updated: {updated_count}'
                f'\n     Total: {created_count + updated_count}'
            )
        )
    
    def init_repeat_catalogs(self):
        """Seed repeat type & repeat-until catalogs (previously handled inline)."""

        self.stdout.write(self.style.WARNING('\n📋 Initializing Surveillance Repeat Catalogs...'))
        type_created, type_updated = self._init_repeat_types()
        until_created, until_updated = self._init_repeat_until_types()

        self.stdout.write(
            self.style.SUCCESS(
                '\n  📊 Repeat Catalog Summary:'
                f'\n     Repeat Types   → Created: {type_created}, Updated: {type_updated}'
                f'\n     Repeat Until   → Created: {until_created}, Updated: {until_updated}'
            )
        )

    def _init_repeat_types(self) -> Tuple[int, int]:
        """Helper để seed SurveillanceProfileRepeatType với đa ngôn ngữ."""

        REPEAT_TYPES = [
            {
                "code": "none",
                "name": {
                    "en": "None",
                    "ko": "반복 없음",
                    "th": "ไม่ทำซ้ำ",
                },
                "description": {
                    "en": "Execute once with no recurrence",
                    "ko": "한 번만 실행하고 반복하지 않습니다",
                    "th": "ทำงานเพียงครั้งเดียวโดยไม่ทำซ้ำ",
                },
            },
            {
                "code": "daily",
                "name": {
                    "en": "Daily",
                    "ko": "매일",
                    "th": "รายวัน",
                },
                "description": {
                    "en": "Repeat every day",
                    "ko": "매일 반복",
                    "th": "ทำซ้ำทุกวัน",
                },
            },
            {
                "code": "weekly",
                "name": {
                    "en": "Weekly",
                    "ko": "매주",
                    "th": "รายสัปดาห์",
                },
                "description": {
                    "en": "Repeat every week",
                    "ko": "매주 반복",
                    "th": "ทำซ้ำทุกสัปดาห์",
                },
            },
            {
                "code": "monthly",
                "name": {
                    "en": "Monthly",
                    "ko": "매월",
                    "th": "รายเดือน",
                },
                "description": {
                    "en": "Repeat every month",
                    "ko": "매월 반복",
                    "th": "ทำซ้ำทุกเดือน",
                },
            },
        ]

        created_count = 0
        updated_count = 0

        for repeat_type in REPEAT_TYPES:
            existing_obj = SurveillanceProfileRepeatType.objects.filter(code=repeat_type["code"]).first()
            if existing_obj:
                update_model_with_translations(existing_obj, repeat_type)
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'  ⟳ Updated repeat type: {repeat_type["code"]}'))
            else:
                create_model_with_translations(SurveillanceProfileRepeatType, repeat_type)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created repeat type: {repeat_type["code"]}'))

        return created_count, updated_count

    def _init_repeat_until_types(self) -> Tuple[int, int]:
        """Helper để seed SurveillanceProfileRepeatUntilType với đa ngôn ngữ."""

        REPEAT_UNTIL_TYPES = [
            {
                "code": "never",
                "name": {
                    "en": "Never",
                    "ko": "무기한",
                    "th": "ไม่สิ้นสุด",
                },
                "description": {
                    "en": "Repeat indefinitely until manually cancelled",
                    "ko": "수동으로 취소될 때까지 반복",
                    "th": "ทำซ้ำไปเรื่อย ๆ จนกว่าจะถูกยกเลิก",
                },
            },
            {
                "code": "on_date",
                "name": {
                    "en": "On Date",
                    "ko": "특정 날짜 종료",
                    "th": "สิ้นสุดในวันที่กำหนด",
                },
                "description": {
                    "en": "Stop repeating on a specific date",
                    "ko": "지정된 날짜에 반복을 중지",
                    "th": "หยุดทำซ้ำในวันที่กำหนด",
                },
            },
            {
                "code": "after_occurrences",
                "name": {
                    "en": "After N Occurrences",
                    "ko": "횟수 후 종료",
                    "th": "สิ้นสุดหลังครบจำนวนครั้ง",
                },
                "description": {
                    "en": "Stop after a defined number of repeats",
                    "ko": "설정된 횟수 이후 반복 중지",
                    "th": "หยุดหลังจากครบจำนวนครั้งที่กำหนด",
                },
            },
        ]

        created_count = 0
        updated_count = 0

        for repeat_until in REPEAT_UNTIL_TYPES:
            existing_obj = SurveillanceProfileRepeatUntilType.objects.filter(code=repeat_until["code"]).first()
            if existing_obj:
                update_model_with_translations(existing_obj, repeat_until)
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'  ⟳ Updated repeat-until: {repeat_until["code"]}'))
            else:
                create_model_with_translations(SurveillanceProfileRepeatUntilType, repeat_until)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created repeat-until: {repeat_until["code"]}'))

        return created_count, updated_count
    
    def init_survey_mission_status(self):
        """Initialize Survey Mission Status data"""
        self.stdout.write(self.style.WARNING('\n📋 Initializing Survey Mission Status...'))
        
        SURVEY_MISSION_STATUS_LIST = [
            {
                "code": "pending_approval",
                "name": {
                    "en": "Pending Approval",
                    "ko": "승인대기",
                    "th": "รอการอนุมัติ"
                },
                "description": {
                    "en": "Mission is waiting for approval",
                    "ko": "미션이 승인을 기다리고 있습니다",
                    "th": "ภารกิจกำลังรอการอนุมัติ"
                },
                "color_code": "#FFA500"  # Orange
            },
            {
                "code": "approved",
                "name": {
                    "en": "Approved",
                    "ko": "승인됨",
                    "th": "อนุมัติ"
                },
                "description": {
                    "en": "Mission has been approved and ready to activate",
                    "ko": "미션이 승인되어 활성화 준비가 되었습니다",
                    "th": "ภารกิจได้รับการอนุมัติและพร้อมเปิดใช้งาน"
                },
                "color_code": "#4CAF50"  # Green
            },
            {
                "code": "rejected",
                "name": {
                    "en": "Rejected",
                    "ko": "반려됨",
                    "th": "ปฏิเสธ"
                },
                "description": {
                    "en": "Mission has been rejected",
                    "ko": "미션이 거부되었습니다",
                    "th": "ภารกิจถูกปฏิเสธ"
                },
                "color_code": "#F44336"  # Red
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for status in SURVEY_MISSION_STATUS_LIST:
            existing_obj = SurveyMissionStatus.objects.filter(code=status["code"]).first()
            if existing_obj:
                update_model_with_translations(existing_obj, status)
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'  ⟳ Updated: {status["code"]}'))
            else:
                create_model_with_translations(SurveyMissionStatus, status)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {status["code"]}'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n  📊 Survey Mission Status Summary:'
                f'\n     Created: {created_count}'
                f'\n     Updated: {updated_count}'
                f'\n     Total: {created_count + updated_count}'
            )
        )
        # Surveillance, Firefighting, Other
        MISSION_PURPOSE_LIST = [
            {
                "code": "surveillance",
                "name": {
                    "en": "Surveillance",
                    "ko": "정찰",
                    "th": "การสอดส่อง"
                },
                "description": {
                    "en": "Mission is for surveillance",
                    "ko": "미션은 정찰을 위한 것입니다",
                    "th": "ภารกิจสำหรับการสอดส่อง"
                }
            },
            {
                "code": "firefighting",
                "name": {
                    "en": "Firefighting",
                    "ko": "화재 감지",
                    "th": "การดับไฟ"
                },
                "description": {
                    "en": "Mission is for firefighting",
                    "ko": "미션은 소화를 위한 것입니다",
                    "th": "ภารกิจสำหรับการดับไฟ"
                }
            },
            {
                "code": "other",
                "name": {
                    "en": "Other",
                    "ko": "기타",
                    "th": "อื่นๆ"
                },
                "description": {
                    "en": "Mission is for other purposes",
                    "ko": "미션은 다른 목적을 위한 것입니다",
                    "th": "ภารกิจสำหรับวัตถุประสงค์อื่นๆ"
                }
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for purpose in MISSION_PURPOSE_LIST:
            existing_obj = MissionPurpose.objects.filter(code=purpose["code"]).first()
            if existing_obj:
                update_model_with_translations(existing_obj, purpose)
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'  ⟳ Updated: {purpose["code"]}'))
            else:
                create_model_with_translations(MissionPurpose, purpose)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {purpose["code"]}'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n  📊 Mission Purpose Summary:'
                f'\n     Created: {created_count}'
                f'\n     Updated: {updated_count}'
                f'\n     Total: {created_count + updated_count}'
            )
        )

    def init_overdue_profile_settings(self):
        """Initialize Overdue Profile Setting data"""
        self.stdout.write(self.style.WARNING('\n📋 Initializing Overdue Profile Setting...'))
        
        config, created = AdminConfig.objects.get_or_create(
            name="Overdue Profile",
            description="Overdue Profile Setting",
            defaults={
                "settings": {
                    "overdue_hours": 24
                }
            }
        )
        if created:
            config.settings = {
                "overdue_hours": 24
            }
            config.save()
            self.stdout.write(self.style.SUCCESS('\n✅ Overdue Profile Setting initialized successfully!\n'))
        else:
            self.stdout.write(self.style.SUCCESS('\n📋 Overdue Profile Setting already exists!\n'))