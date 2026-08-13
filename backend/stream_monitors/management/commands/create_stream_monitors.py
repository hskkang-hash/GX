import random
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist

from devices.models import Device
from stream_monitors.models import StreamMonitor


class Command(BaseCommand):
    help = 'Create 5 StreamMonitor records with random drones from Device model'

    def handle(self, *args, **options):
        # Check if there are any devices available
        devices = list(Device._base_manager.all())
        
        if not devices:
            self.stdout.write(
                self.style.ERROR('No devices found in the database. Please create some devices first.')
            )
            return

        stream_monitors_data = [
            {
                'name': 'Stream Monitor Alpha',
                'code': 'SM_ALPHA_001',
                'ip_source': '192.168.1.100',
                'is_active': True,
                'is_visualize': True
            },
            {
                'name': 'Stream Monitor Beta',
                'code': 'SM_BETA_002',
                'ip_source': '192.168.1.101',
                'is_active': True,
                'is_visualize': False
            },
            {
                'name': 'Stream Monitor Gamma',
                'code': 'SM_GAMMA_003',
                'ip_source': '192.168.1.102',
                'is_active': True,
                'is_visualize': True
            },
            {
                'name': 'Stream Monitor Delta',
                'code': 'SM_DELTA_004',
                'ip_source': '192.168.1.103',
                'is_active': False,
                'is_visualize': False
            },
            {
                'name': 'Stream Monitor Epsilon',
                'code': 'SM_EPSILON_005',
                'ip_source': '192.168.1.104',
                'is_active': True,
                'is_visualize': True
            }
        ]

        created_count = 0
        for monitor_data in stream_monitors_data:
            # Select a random drone for each stream monitor
            random_drone = random.choice(devices)
            
            # Check if StreamMonitor with this code already exists
            existing_monitor = StreamMonitor.objects.filter(code=monitor_data['code']).first()
            
            if not existing_monitor:
                stream_monitor = StreamMonitor.objects.create(
                    name=monitor_data['name'],
                    code=monitor_data['code'],
                    drone=random_drone,
                    ip_source=monitor_data['ip_source'],
                    is_active=monitor_data['is_active'],
                    is_visualize=monitor_data['is_visualize']
                )
                
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created StreamMonitor: {stream_monitor.name} '
                        f'with drone: {random_drone.name}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'StreamMonitor with code {monitor_data["code"]} already exists: {existing_monitor.name}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f'Command completed. {created_count} new StreamMonitors created.')
        )
        
        if devices:
            self.stdout.write(
                self.style.SUCCESS(f'Random drones were selected from {len(devices)} available devices.')
            ) 