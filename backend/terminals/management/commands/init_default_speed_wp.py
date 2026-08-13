from django.core.management.base import BaseCommand
from core.configuration.models import AdminConfig
from django.db import transaction


class Command(BaseCommand):
    help = 'Initialize waypoint speed setting in AdminConfig'

    def handle(self, *args, **options):
        self.stdout.write('Starting to initialize waypoint speed setting...')
        
        try:
            with transaction.atomic():
                # Thiết lập setting mặc định cho waypoint speed
                default_settings = {
                    '_options':{
                        'last_mission_waypoint': [{'name': 'land', 'value': False}, {'name': 'return_to_launch', 'value ': True}],
                    },
                    'waypoint_speed': '7',
                    'last_mission_waypoint': {
                        'land': False,
                        'return_to_launch': True,
                    }
                }
                
                # Lấy hoặc tạo AdminConfig cho waypoint settings
                config, created = AdminConfig.objects.get_or_create(
                    defaults={
                        'name':'Waypoint Settings',

                    },
                    description='Waypoint speed setting'
                )
                
                if not created:
                    # Nếu config đã tồn tại, merge settings
                    old_settings = config.settings or {}
                    new_settings = old_settings.copy()
                    
                    # Thêm từng key từ default_settings nếu chưa có
                    updated = False
                    for key, value in default_settings.items():
                        if key not in new_settings:
                            new_settings[key] = value
                            updated = True
                    
                    # Chỉ cập nhật nếu có thay đổi
                    if updated:
                        config.settings = new_settings
                        config.save()
                        
                        self.stdout.write(f"Updated AdminConfig: {config.name}")
                        self.stdout.write(f"  Old settings: {old_settings}")
                        self.stdout.write(f"  New settings: {new_settings}")
                    else:
                        self.stdout.write(f"No changes needed for AdminConfig: {config.name}")
                        self.stdout.write(f"  Current settings: {config.settings}")
                else:
                    self.stdout.write(f"Created new AdminConfig: {config.name}")
                    self.stdout.write(f"  Settings: {config.settings}")
                
                self.stdout.write(
                    self.style.SUCCESS(
                        'Successfully initialized waypoint speed setting!'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error initializing waypoint speed setting: {str(e)}')
            )
