from django.core.management.base import BaseCommand
from core.configuration.models import AdminConfig

class Command(BaseCommand):
    help = 'Creates an AdminConfig for Operation with specified settings'

    settings = [
        {
            'name': 'order_arrived_timeout_no_pickup',
            'value': 15
        },
        {
            'name': 'order_pending_timeout_no_pickup',
            'value': 15
        },
        {
            'name': 'order_returned_timeout_no_pickup',
            'value': 15
        }
    ]
    def handle(self, *args, **options):
        try:
            # Create or update the AdminConfig
            config, created = AdminConfig.objects.update_or_create(
                name='Operation',
                defaults={
                    'settings': {
                        setting['name']: setting['value']
                        for setting in self.settings
                    }
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS('Successfully created Operation AdminConfig')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('Successfully updated Operation AdminConfig')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating/updating AdminConfig: {str(e)}')
            ) 