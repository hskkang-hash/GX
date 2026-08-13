"""
Management command to create a test drawing session
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from stream_monitors.models import StreamMonitor, DrawingSession

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a test drawing session for WebSocket testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            default=None,
            help='User ID to create the session for (default: first user)',
        )
        parser.add_argument(
            '--stream-monitor-id',
            type=int,
            default=None,
            help='Stream Monitor ID to associate with (default: first stream monitor)',
        )
        parser.add_argument(
            '--session-name',
            type=str,
            default='Test Drawing Session',
            help='Name for the drawing session',
        )

    def handle(self, *args, **options):
        try:
            # Get or create a user
            user_id = options['user_id']
            if user_id:
                user = User.objects.get(id=user_id)
            else:
                user = User.objects.first()
                if not user:
                    self.stdout.write(
                        self.style.ERROR('No users found. Create a user first with: python manage.py createsuperuser')
                    )
                    return

            # Get or create a stream monitor
            stream_monitor_id = options['stream_monitor_id']
            if stream_monitor_id:
                try:
                    stream_monitor = StreamMonitor.objects.get(id=stream_monitor_id)
                except StreamMonitor.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'StreamMonitor with ID {stream_monitor_id} not found')
                    )
                    return
            else:
                stream_monitor = StreamMonitor.objects.first()
                if not stream_monitor:
                    # Create a dummy stream monitor for testing
                    from devices.models import Device
                    device = Device.objects.first()
                    if not device:
                        self.stdout.write(
                            self.style.WARNING('No devices found. Creating a dummy device...')
                        )
                        # This might fail if Device model has required fields
                        # In that case, you'll need to create proper device first
                        return
                    
                    stream_monitor = StreamMonitor.objects.create(
                        name='Test Stream Monitor',
                        code='test_monitor_001',
                        drone=device,
                        ip_source='127.0.0.1',
                        is_active=True
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'Created test StreamMonitor: {stream_monitor.name} (ID: {stream_monitor.id})')
                    )

            # check if drawing session already exists
            if DrawingSession.objects.filter(name=options['session_name']).exists():
                self.stdout.write(
                    self.style.WARNING(f'Drawing session with name {options["session_name"]} already exists')
                )
                return
            else:
                # Create drawing session
                session = DrawingSession.objects.create(
                    id=1,
                    name=options['session_name'],
                    stream_monitor=stream_monitor,
                    created_by=user
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Successfully created drawing session!\n'
                        f'   Session ID: {session.id}\n'
                        f'   Session Name: {session.name}\n'
                        f'   Created by: {user.username}\n'
                        f'   Stream Monitor: {stream_monitor.name}\n'
                        f'\n'
                        f'🔗 WebSocket URL: ws://localhost:8000/ws/drawing/session/{session.id}/?token=YOUR_JWT_TOKEN\n'
                        f'\n'
                        f'📝 Use Session ID "{session.id}" in the frontend example.'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating drawing session: {e}')
            )