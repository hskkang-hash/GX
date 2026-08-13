import json
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from operation_settings.models import OperationSettings
from core.user.models import CoreUser, UserGroup


class Command(BaseCommand):
    help = 'Load sample operation settings data from JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='./sample_api_data.json',
            help='Path to JSON file with sample data'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing operation settings before loading'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        
        # Get full path relative to project root
        if not os.path.isabs(file_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            file_path = os.path.join(base_dir, file_path)
        
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'Sample data file not found: {file_path}')
            )
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if options['clear']:
                self.stdout.write('Clearing existing operation settings...')
                OperationSettings.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS('Existing operation settings cleared.')
                )
            
            # Get or create a default user for updated_by field
            try:
                default_user = CoreUser.objects.filter(is_superuser=True).first()
                if not default_user:
                    default_user = CoreUser.objects.first()
            except:
                default_user = None
            
            samples = data.get('operation_settings_samples', [])
            created_count = 0
            updated_count = 0
            skipped_count = 0
            
            for sample in samples:
                try:
                    # Remove fields that are not in the model or should be auto-generated
                    sample_copy = sample.copy()
                    sample_copy.pop('id', None)
                    sample_copy.pop('created_on', None)
                    sample_copy.pop('updated_on', None)
                    sample_copy.pop('updated_by', None)
                    
                    # Lookup menu by path
                    menu = None
                    if sample_copy.get('menu'):
                        try:
                            from core.menu.models import Menu
                            menu = Menu.objects.get(path=sample_copy['menu'], deleted__isnull=True)
                        except Menu.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f'Menu with path "{sample_copy["menu"]}" not found. Skipping...')
                            )
                            skipped_count += 1
                            continue
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Error finding menu "{sample_copy["menu"]}": {str(e)}')
                            )
                            skipped_count += 1
                            continue
                    
                    # Lookup tab by path (if provided)
                    tab = None
                    if sample_copy.get('tab') and menu:
                        try:
                            from core.menu.models import Tab
                            tab = Tab.objects.get(path=sample_copy['tab'], deleted__isnull=True, parent_menu=menu)
                        except Tab.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f'Tab with path "{sample_copy["tab"]}" not found in menu "{menu.path}". Skipping...')
                            )
                            skipped_count += 1
                            continue
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Error finding tab "{sample_copy["tab"]}": {str(e)}')
                            )
                            skipped_count += 1
                            continue
                    
                    # Lookup group by name
                    group = None
                    if sample_copy.get('group'):
                        try:
                            group = UserGroup.objects.get(name=sample_copy['group'], deleted__isnull=True)
                        except UserGroup.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f'UserGroup with name "{sample_copy["group"]}" not found. Skipping...')
                            )
                            skipped_count += 1
                            continue
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Error finding group "{sample_copy["group"]}": {str(e)}')
                            )
                            skipped_count += 1
                            continue
                    
                    # Check if record already exists
                    existing = OperationSettings.objects.filter(
                        menu=menu,
                        tab=tab,
                        name=sample_copy['name'],
                        group=group
                    ).first()
                    
                    # Prepare data for creation/update
                    operation_data = {
                        'menu': menu,
                        'tab': tab,
                        'group': group,
                        'name': sample_copy['name'],
                        'is_active': sample_copy.get('is_active', True),
                        'api_url': sample_copy['api_url'],
                        'http_method': sample_copy.get('http_method', 'GET'),
                        'api_params': sample_copy.get('api_params'),
                        'expected_response': sample_copy.get('expected_response'),
                        'timeout_seconds': sample_copy.get('timeout_seconds', 30),
                        'retry_count': sample_copy.get('retry_count', 3),
                        'description': sample_copy.get('description'),
                        'notes': sample_copy.get('notes'),
                    }
                    
                    if existing:
                        # Update existing record
                        for key, value in operation_data.items():
                            setattr(existing, key, value)
                        existing.save()
                        updated_count += 1
                        tab_display = f" - Tab {existing.tab.path}" if existing.tab else ""
                        self.stdout.write(
                            f'Updated: Menu {existing.menu.path}{tab_display} - {existing.name} - Group {existing.group.name}'
                        )
                    else:
                        # Create new record
                        operation_setting = OperationSettings.objects.create(**operation_data)
                        created_count += 1
                        tab_display = f" - Tab {operation_setting.tab.path}" if operation_setting.tab else ""
                        self.stdout.write(
                            f'Created: Menu {operation_setting.menu.path}{tab_display} - {operation_setting.name} - Group {operation_setting.group.name}'
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error processing sample "{sample.get("name", "unknown")}": {str(e)}')
                    )
                    skipped_count += 1
                    continue
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully processed operation settings data. '
                    f'Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}'
                )
            )
            
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f'Invalid JSON format: {str(e)}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error loading sample data: {str(e)}')
            ) 