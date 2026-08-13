from django.core.management.base import BaseCommand
from core.configuration.models import AdminConfig

class Command(BaseCommand):
    help = 'Creates an AdminConfig for Delivery Inquiry Refresh with specified settings'

    settings = [
        {
            'name': 'delivery_inquiry_refresh_interval',
            'value': 30
        },
        {
            'name': 'delivery_inquiry_auto_refresh',
            'value': False
        }
    ]
    def handle(self, *args, **options):
        try:
            # delete all AdminConfig with name 'Delivery inquiry refresh'
            AdminConfig.objects.filter(name='delivery_inquiry_refresh').delete()
            # Create or update the AdminConfig
            config, created = AdminConfig.objects.update_or_create(
                name='Delivery inquiry refresh',
                defaults={
                    'settings': {
                        setting['name']: setting['value']
                        for setting in self.settings
                    }
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS('Successfully created Delivery Inquiry Refresh AdminConfig')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('Successfully updated Delivery Inquiry Refresh AdminConfig')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating/updating AdminConfig: {str(e)}')
            ) 