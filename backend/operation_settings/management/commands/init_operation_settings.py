import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from operation_settings.models import OperationSettings
from core.menu.models import Menu, Tab
from core.user.models import UserGroup, CoreUser

# Note: This command uses _base_manager to bypass any custom logic
# and avoid triggering the duplication task when updating operation settings


class Command(BaseCommand):
    help = 'Initialize Operation Settings from sample JSON data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='operation_settings/sample_api_data.json',
            help='Path to JSON file containing operation settings data'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing operation settings before importing'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        clear_existing = options['clear']
        dry_run = options['dry_run']

        # Check if file exists
        if not os.path.exists(file_path):
            raise CommandError(f'File "{file_path}" does not exist.')

        # Load JSON data
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON in file "{file_path}": {e}')
        except Exception as e:
            raise CommandError(f'Error reading file "{file_path}": {e}')

        # Get operation settings samples
        if 'operation_settings_samples' not in data:
            raise CommandError('JSON file must contain "operation_settings_samples" key')

        samples = data['operation_settings_samples']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        # Clear existing data if requested
        if clear_existing:
            if dry_run:
                existing_count = OperationSettings._base_manager.count()
                self.stdout.write(f'Would delete {existing_count} existing operation settings')
            else:
                deleted_count = OperationSettings._base_manager.count()
                OperationSettings._base_manager.all().delete()
                self.stdout.write(
                    self.style.SUCCESS(f'Deleted {deleted_count} existing operation settings')
                )

        # Process each sample
        created_count = 0
        updated_count = 0
        error_count = 0

        with transaction.atomic():
            for sample in samples:
                try:
                    result = self.process_sample(sample, dry_run)
                    if result == 'created':
                        created_count += 1
                    elif result == 'updated':
                        updated_count += 1
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'Error processing sample "{sample.get("name", "Unknown")}": {e}')
                    )

        # Summary
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'DRY RUN COMPLETE: Would create {created_count}, update {updated_count} operation settings. '
                    f'Errors: {error_count}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created {created_count}, updated {updated_count} operation settings. '
                    f'Errors: {error_count}'
                )
            )

    def process_sample(self, sample, dry_run=False):
        """Process a single operation setting sample"""
        
        # Get or create menu
        menu_path = sample.get('menu')
        if not menu_path:
            raise ValueError('Menu path is required')

        menu = Menu.objects.filter(path=menu_path, deleted__isnull=True).first()
        if not menu:
            raise ValueError(f'Menu with path "{menu_path}" not found')

        # Get or create tab (optional)
        tab = None
        tab_path = sample.get('tab')
        if tab_path:
            tab = Tab.objects.filter(path=tab_path, deleted__isnull=True).first()
            if not tab:
                raise ValueError(f'Tab with path "{tab_path}" not found')

        # Prepare operation setting data
        setting_data = {
            'menu': menu,
            'tab': tab,
            'name': sample.get('name'),
            'send_data': sample.get('send_data', False),
            'receive_data': sample.get('receive_data', False),
            'api_url': sample.get('api_url'),
            'http_method': sample.get('http_method', 'GET'),
            'api_params': sample.get('api_params'),
            'body_params': sample.get('body_params'),
            'expected_response': sample.get('expected_response'),
            'timeout_seconds': sample.get('timeout_seconds', 30),
            'retry_count': sample.get('retry_count', 3),
            'description': sample.get('description'),
            'notes': sample.get('notes'),
            'is_active': True if sample.get('send_data', False) else False,
        }

        if dry_run:
            # Check if would create or update
            existing = OperationSettings._base_manager.filter(
                menu=menu,
                tab=tab,
                name=sample.get('name'),
            ).first()
            
            if existing:
                self.stdout.write(f'Would update: {setting_data["name"]} for {menu.menu_name}')
                return 'updated'
            else:
                self.stdout.write(f'Would create: {setting_data["name"]} for {menu.menu_name}')
                return 'created'
        else:
            # Use _base_manager to bypass any custom logic and avoid triggering tasks
            # This ensures the command doesn't interfere with the duplication logic
            operation_setting, created = OperationSettings._base_manager.update_or_create(
                menu=menu,
                tab=tab,
                name=sample.get('name'),
                defaults=setting_data
            )

            if created:
                self.stdout.write(f'Created: {operation_setting.name} for {menu.menu_name}')
                return 'created'
            else:
                self.stdout.write(f'Updated: {operation_setting.name} for {menu.menu_name}')
                return 'updated' 