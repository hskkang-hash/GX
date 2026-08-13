from django.core.management.base import BaseCommand
from django.db import transaction
from terminals.models import LocationType
from core.multilanguage.request_handlers import update_model_with_translations, create_model_with_translations



class Command(BaseCommand):
    help = 'Creates default LocationType records'

    @transaction.atomic
    def handle(self, *args, **options):
        sample_types = [
            {
                "name": {
                    "en": "Island",
                    "ko": "섬"
                },
                "code": "ISLAND",
                "description": {''
                    "en": "Island",
                    "ko": "섬"
                }
            },
            {
                "name": {
                    "en": "Mountain",
                    "ko": "산간"
                },
                "code": "MOUNTAIN",
                "description": {
                    "en": "Mountain",
                    "ko": "산간"
                }
            },
            {
                "name": {
                    "en": "Harbor",
                    "ko": "항구"
                },
                "code": "HARBOR",
                "description": {
                    "en": "Harbor",
                    "ko": "항구"
                }
            },
            {
                "name": {
                    "en": "City",
                    "ko": "도시"
                },
                "code": "CITY",
                "description": {
                    "en": "City",
                    "ko": "도시"
                }
            }
        ]
        
        created_count = 0
        for item_type in sample_types:
            # Check if item type already exists
            existing_obj = LocationType.objects.filter(name__icontains=item_type["name"]["en"], code=item_type["code"]).first()
            if existing_obj:
                item_type["created_by"] = None
                item_type["modified_by"] = None
                update_model_with_translations(existing_obj, item_type)
                self.stdout.write(self.style.SUCCESS(f"Created LocationType: {item_type['name']} ({item_type['code']})"))
            else:
                item_type["created_by"] = None
                item_type["modified_by"] = None
                create_model_with_translations(LocationType, item_type)
                self.stdout.write(self.style.WARNING(f"LocationType with code {item_type['code']} already exists."))
        
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} new LocationType records.")) 