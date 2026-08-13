"""
Django management command to initialize Handover Shift data
Run: python manage.py init_shifts
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from handover.models import HandoverShift
from core.multilanguage.request_handlers import create_model_with_translations, update_model_with_translations


class Command(BaseCommand):
    help = 'Initialize Handover Shift data with multi-language support (EN, KR, VI)'

    SHIFT_DATA = [
        {
            'name': {'en': 'Day Shift', 'ko': '주간 교대', 'vi': 'Ca ngày', 'th': 'กะกับวัน'},
            'start_time': '06:00',
            'end_time': '14:00',
            'color': '#FF5733',
        },
        {
            'name': {'en': 'Night Shift', 'ko': '야간 교대', 'vi': 'Ca đêm', 'th': 'กะกับกลางคืน'},
            'start_time': '22:00',
            'end_time': '06:00',
            'color': '#3357FF',
        }
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing shift data before creating new ones',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🚀 Starting Handover Shift Initialization...\n'))
        
        reset = options.get('reset', False)
        
        if reset:
            self.stdout.write(self.style.WARNING('Resetting existing shift data...'))
            HandoverShift.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data deleted.\n'))
        
        self.init_shifts()
        
        self.stdout.write(self.style.SUCCESS('\n✅ All Handover Shift data initialized successfully!\n'))
    
    def init_shifts(self):
        """Initialize Handover Shift data with multi-language support."""
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for shift_data in self.SHIFT_DATA:
                name_dict = shift_data['name']
                start_time = shift_data['start_time']
                end_time = shift_data['end_time']
                color = shift_data.get('color', None)
                
                # Check if shift already exists by name (using English name)
                existing_shift = HandoverShift.objects.filter(
                    name=name_dict.get('en', '')
                ).first()
                
                if existing_shift:
                    # Update existing shift
                    update_data_dict = {
                        'name': name_dict,
                        'start_time': start_time,
                        'end_time': end_time,
                        'color': color,
                    }
                    update_model_with_translations(existing_shift, update_data_dict)
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'↻ Updated: {name_dict.get("en", "Unknown")} ({start_time} - {end_time})')
                    )
                else:
                    # Create new shift
                    shift_data_dict = {
                        'name': name_dict,
                        'start_time': start_time,
                        'end_time': end_time,
                        'color': color,
                    }
                    shift = create_model_with_translations(HandoverShift, shift_data_dict)
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Created: {name_dict.get("en", "Unknown")} ({start_time} - {end_time})')
                    )
        
        self.stdout.write(self.style.SUCCESS(f'\n📊 Summary: Created {created_count}, Updated {updated_count}'))

