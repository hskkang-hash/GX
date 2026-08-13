from django.core.management.base import BaseCommand
from devices.models import DeviceStatus

class Command(BaseCommand):
    help = 'Generate 10 sample bank records'

    def handle(self, *args, **kwargs):
        # Sample bank data
        statuses = [
            {'code': 'available', 'name': 'Available', 'description': 'Available'},
            {'code': 'on_mission', 'name': 'On mission', 'description': 'On mission'},
            {'code': 'return', 'name': 'Return', 'description': 'Return'}
        ]

        # Create bank records
        for status_data in statuses:
            existing_status = DeviceStatus.objects.filter(code=status_data['code']).first()
            if existing_status:
                self.stdout.write(f'Device status {status_data["name"]} already exists')
            else:
                DeviceStatus.objects.create(**status_data)
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created device status: {status_data["name"]}')
                ) 