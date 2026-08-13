from django.core.management.base import BaseCommand
from django.db import transaction
from orders.models import DeliveryOption
from core.multilanguage.request_handlers import update_model_with_translations, create_model_with_translations


class Command(BaseCommand):
    help = 'Creates default DeliveryOption records'

    @transaction.atomic
    def handle(self, *args, **options):
        delivery_options = [
            {
                "name": "Delivery to Door",
                "code": "delivery_to_door",
                "description": "Package will be delivered directly to the recipient's address.",
            },
            {
                "name": "Collect at Location",
                "code": "collect_at_location",
                "description": "Recipient will pick up the package from a designated terminal."
            }
        ]
        
        created_count = 0
        for option_data in delivery_options:
            # Check if option already exists by code
            option, created = DeliveryOption.objects.get_or_create(
                code=option_data["code"],
                defaults=option_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created DeliveryOption: {option.name}"))
            else:
                # create_model_with_translations(DeliveryOption, option_data)
                self.stdout.write(self.style.WARNING(f"DeliveryOption '{option.name}' already exists."))
        
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} new DeliveryOption records.")) 