"""
Django management command to initialize Days of Week data
Run: python manage.py init_days_of_week
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from terminals.models import DayOfWeek
from core.multilanguage.request_handlers import update_model_with_translations


class Command(BaseCommand):
    help = 'Initialize Days of Week data with multi-language support (EN, KR, TH)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing days of week data before creating new ones',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🚀 Starting Days of Week Initialization...\n'))
        
        reset = options.get('reset', False)
        
        if reset:
            self.stdout.write(self.style.WARNING('Resetting existing days of week data...'))
            DayOfWeek.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data deleted.\n'))
        
        self.init_days_of_week()
        
        self.stdout.write(self.style.SUCCESS('\n✅ All Days of Week data initialized successfully!\n'))
    
    def init_days_of_week(self):
        """Initialize Days of Week data with multi-language support."""
        days_data = [
            {
                'name': 'Monday',
                'code': 'monday',
                'order': 0,
                'description': 'The first day of the week',
                'translations': {
                    'en': {'name': 'Monday', 'description': 'The first day of the week'},
                    'kr': {'name': '월요일', 'description': '주간의 첫 번째 날'},
                    'th': {'name': 'วันจันทร์', 'description': 'วันแรกของสัปดาห์'},
                }
            },
            {
                'name': 'Tuesday',
                'code': 'tuesday',
                'order': 1,
                'description': 'The second day of the week',
                'translations': {
                    'en': {'name': 'Tuesday', 'description': 'The second day of the week'},
                    'kr': {'name': '화요일', 'description': '주간의 두 번째 날'},
                    'th': {'name': 'วันอังคาร', 'description': 'วันที่สองของสัปดาห์'},
                }
            },
            {
                'name': 'Wednesday',
                'code': 'wednesday',
                'order': 2,
                'description': 'The third day of the week',
                'translations': {
                    'en': {'name': 'Wednesday', 'description': 'The third day of the week'},
                    'kr': {'name': '수요일', 'description': '주간의 세 번째 날'},
                    'th': {'name': 'วันพุธ', 'description': 'วันที่สามของสัปดาห์'},
                }
            },
            {
                'name': 'Thursday',
                'code': 'thursday',
                'order': 3,
                'description': 'The fourth day of the week',
                'translations': {
                    'en': {'name': 'Thursday', 'description': 'The fourth day of the week'},
                    'kr': {'name': '목요일', 'description': '주간의 네 번째 날'},
                    'th': {'name': 'วันพฤหัสบดี', 'description': 'วันที่สี่ของสัปดาห์'},
                }
            },
            {
                'name': 'Friday',
                'code': 'friday',
                'order': 4,
                'description': 'The fifth day of the week',
                'translations': {
                    'en': {'name': 'Friday', 'description': 'The fifth day of the week'},
                    'kr': {'name': '금요일', 'description': '주간의 다섯 번째 날'},
                    'th': {'name': 'วันศุกร์', 'description': 'วันที่ห้าของสัปดาห์'},
                }
            },
            {
                'name': 'Saturday',
                'code': 'saturday',
                'order': 5,
                'description': 'The sixth day of the week',
                'translations': {
                    'en': {'name': 'Saturday', 'description': 'The sixth day of the week'},
                    'kr': {'name': '토요일', 'description': '주간의 여섯 번째 날'},
                    'th': {'name': 'วันเสาร์', 'description': 'วันที่หกของสัปดาห์'},
                }
            },
            {
                'name': 'Sunday',
                'code': 'sunday',
                'order': 6,
                'description': 'The seventh day of the week',
                'translations': {
                    'en': {'name': 'Sunday', 'description': 'The seventh day of the week'},
                    'kr': {'name': '일요일', 'description': '주간의 일곱 번째 날'},
                    'th': {'name': 'วันอาทิตย์', 'description': 'วันที่เจ็ดของสัปดาห์'},
                }
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for day_data in days_data:
                code = day_data['code']
                translations = day_data.pop('translations', {})
                
                day_of_week, created = DayOfWeek.objects.get_or_create(
                    code=code,
                    defaults=day_data
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ Created: {day_of_week.name}'))
                else:
                    # Update existing
                    for key, value in day_data.items():
                        setattr(day_of_week, key, value)
                    day_of_week.save()
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f'↻ Updated: {day_of_week.name}'))
                
                # Create/Update translations
                if translations:
                    # Convert translations format from {lang: {field: value}} to {field: {lang: value}}
                    translation_data = {}
                    for lang_code, lang_translations in translations.items():
                        for field_name, field_value in lang_translations.items():
                            if field_name not in translation_data:
                                translation_data[field_name] = {}
                            translation_data[field_name][lang_code] = field_value
                    
                    update_model_with_translations(day_of_week, translation_data)
        
        self.stdout.write(self.style.SUCCESS(f'\n📊 Summary: Created {created_count}, Updated {updated_count}'))

