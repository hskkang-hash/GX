from django.core.management.base import BaseCommand
from core.configuration.models import AdminConfig

class Command(BaseCommand):
    help = 'Creates an AdminConfig for Dashboard with specified settings'

    settings = [
        {
            'name': 'dashboard_refresh_interval',
            'value': 300
        }
    ]
    def handle(self, *args, **options):
        try:
            # Create or update the AdminConfig
            config, created = AdminConfig.objects.update_or_create(
                name='Dashboard',
                defaults={
                    'settings': {
                        setting['name']: setting['value']
                        for setting in self.settings
                    }
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS('Successfully created Dashboard AdminConfig')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('Successfully updated Dashboard AdminConfig')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating/updating AdminConfig: {str(e)}')
            ) 