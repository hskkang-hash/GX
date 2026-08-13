from django.core.management.base import BaseCommand
from core.configuration.models import AdminConfig 
from devices.utils import create_hierarchical_unit_preferences, validate_unit_preferences, migrate_to_hierarchical_preferences

class Command(BaseCommand):
    help = 'Migrates unit preferences to hierarchical format'

    def handle(self, *args, **options):
        try:
            # Get current config
            config = AdminConfig.objects.get(name='Unit Config')
            settings = config.settings
            
            # Check if unit_preferences exists and is flat
            if 'unit_preferences' in settings and isinstance(settings['unit_preferences'], dict):
                # Skip if already migrated
                if 'default' in settings['unit_preferences']:
                    self.stdout.write(self.style.SUCCESS("Already in hierarchical format"))
                    return
                
                # Make a backup of the original preferences
                original_preferences = settings['unit_preferences'].copy()
                self.stdout.write("Original preferences:")
                self.stdout.write(str(original_preferences))
                
                # Migrate to hierarchical format
                settings['unit_preferences'] = migrate_to_hierarchical_preferences(
                    settings['unit_preferences']
                )
                
                # Save the updated config
                config.settings = settings
                config.save()
                
                self.stdout.write(self.style.SUCCESS("Successfully migrated unit preferences to hierarchical format"))
            else:
                self.stdout.write(self.style.WARNING("No unit preferences found to migrate"))
                
        except AdminConfig.DoesNotExist:
            self.stdout.write(self.style.ERROR("Unit Config not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during migration: {str(e)}"))
        
        # Example of how to manually create model-specific preferences
        self.stdout.write("\n" + self.style.WARNING(
            "Example of hierarchical unit preferences structure:"
        ))
        
        example = create_hierarchical_unit_preferences(
            defaults={
                'weight': 'kg',
                'dimensions': 'mm',
                'length': 'm',
                'temperature': '°C',
            },
            model_preferences={
                'CameraType': {
                    'weight': 'g',
                    'resolution': 'px',
                    'field_of_view': '°',
                },
                'PackagingSpecification': {
                    'dimensions': 'cm',
                    'max_weight': 'kg',
                }
            }
        )
        
        # Display the example structure
        import json
        self.stdout.write(json.dumps(example, indent=2))
        
        # Validate the example
        is_valid, error_message = validate_unit_preferences(example)
        if is_valid:
            self.stdout.write(self.style.SUCCESS("Example structure is valid"))
        else:
            self.stdout.write(self.style.ERROR(f"Example structure is invalid: {error_message}")) 