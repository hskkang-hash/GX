from django.core.management.base import BaseCommand
from django.db import transaction
from terminals.models import DeactivateReason
from core.multilanguage.request_handlers import update_model_with_translations, create_model_with_translations



class Command(BaseCommand):
    help = 'Creates default DeactivateReason records'

    @transaction.atomic
    def handle(self, *args, **options):
        deactivate_reasons = [
            {
                "name": {
                    "en": "Weather",
                    "ko": "날씨"
                },
                "code": "WEATHER",
                "description": {
                    "en": "Weather",
                    "ko": "날씨"
                }
            },
            {
                "name": {
                    "en": "Closed",
                    "ko": "운행중지"
                },
                "code": "CLOSED",
                "description": {
                    "en": "Closed",
                    "ko": "운행중지"
                }
            },
            {
                "name": {
                    "en": "Under maintenance",
                    "ko": "정비중"
                },
                "code": "UNDER_MAINTENANCE",
                "description": {
                    "en": "Under maintenance",
                    "ko": "정비중"
                }
            },
            {
                "name": {
                    "en": "In operation",
                    "ko": "운행중"
                },
                "code": "IN_OPERATION",
                "description": {
                    "en": "In operation",
                    "ko": "운행중"
                }
            }
        ]
        
        created_count = 0
        updated_count = 0
        for reason in deactivate_reasons:
            # Check if reason already exists
            existing_obj = DeactivateReason.objects.filter(code=reason["code"]).first()
            if existing_obj:
                reason["created_by"] = None
                reason["modified_by"] = None
                update_model_with_translations(existing_obj, reason)
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"Updated DeactivateReason: {reason['name']['en']} ({reason['code']})"))
            else:
                reason["created_by"] = None
                reason["modified_by"] = None
                create_model_with_translations(DeactivateReason, reason)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created DeactivateReason: {reason['name']['en']} ({reason['code']})"))
        
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} new DeactivateReason records."))
        self.stdout.write(self.style.SUCCESS(f"Updated {updated_count} existing DeactivateReason records."))

