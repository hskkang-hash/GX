from django.core.management.base import BaseCommand
from django.apps import apps
from core.configuration.models import AdminConfig
from devices.utils import create_hierarchical_unit_preferences
from devices.models import MeasurableModel
from common.measurable_model import MeasurableModelWithGroup
import json

class Command(BaseCommand):
    help = 'Generates a new hierarchical unit preferences configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update the database with the generated configuration',
        )

    def get_measurable_models(self):
        """Tự động tìm tất cả models có MEASUREMENT_TYPES trong hệ thống"""
        measurable_models = []
        
        # Lấy tất cả models trong tất cả apps
        for model in apps.get_models():
            # Kiểm tra xem model có kế thừa từ MeasurableModel hoặc MeasurableModelWithGroup không
            if (issubclass(model, MeasurableModel) or issubclass(model, MeasurableModelWithGroup)) and hasattr(model, 'MEASUREMENT_TYPES'):
                if model.MEASUREMENT_TYPES:  # Chỉ lấy những model có MEASUREMENT_TYPES không rỗng
                    measurable_models.append(model)
        
        return measurable_models

    def generate_default_preferences(self, measurable_models):
        """Tự động tạo default_preferences từ tất cả measurement fields trong hệ thống"""
        default_preferences = {}
        
        for model in measurable_models:
            for measurement_type, config in model.MEASUREMENT_TYPES.items():
                if 'default_unit' in config:
                    # Chỉ thêm vào nếu chưa có hoặc đơn vị mới khác với đơn vị cũ
                    if measurement_type not in default_preferences:
                        default_preferences[measurement_type] = config['default_unit']
        
        return default_preferences

    def generate_model_preferences(self, measurable_models):
        """Tự động tạo model_preferences từ tất cả models có MEASUREMENT_TYPES"""
        model_preferences = {}
        
        for model in measurable_models:
            model_name = model.__name__
            model_prefs = {}
            
            for measurement_type, config in model.MEASUREMENT_TYPES.items():
                if 'default_unit' in config:
                    model_prefs[measurement_type] = config['default_unit']
            
            if model_prefs:  # Chỉ thêm model nếu có preferences
                model_preferences[model_name] = model_prefs
        
        return model_preferences

    def handle(self, *args, **options):
        self.stdout.write("Tìm kiếm tất cả models có measurement types...")
        
        # Tự động tìm tất cả models có measurement types
        measurable_models = self.get_measurable_models()
        
        self.stdout.write(f"Tìm thấy {len(measurable_models)} models có measurement types:")
        for model in measurable_models:
            self.stdout.write(f"  - {model.__name__}: {len(model.MEASUREMENT_TYPES)} measurement types")
        
        # Tạo default_preferences từ tất cả measurement fields
        self.stdout.write("\nTạo default_preferences từ tất cả measurement fields...")
        default_preferences = self.generate_default_preferences(measurable_models)
        
        # Tạo model_preferences từ tất cả models
        self.stdout.write("Tạo model_preferences từ tất cả models có MEASUREMENT_TYPES...")
        model_preferences = self.generate_model_preferences(measurable_models)
        
        # In thống kê
        self.stdout.write(f"\nThống kê:")
        self.stdout.write(f"  - Tổng số measurement types: {len(default_preferences)}")
        self.stdout.write(f"  - Tổng số models có measurements: {len(model_preferences)}")
        
        # Create hierarchical unit preferences  
        self.stdout.write("\nTạo hierarchical unit preferences...")
        unit_preferences = create_hierarchical_unit_preferences(
            defaults=default_preferences,
            model_preferences=model_preferences
        )
        
        # Print một số default preferences để kiểm tra
        self.stdout.write("\nMột số default preferences được tạo:")
        count = 0
        for key, value in default_preferences.items():
            if count < 10:  # Chỉ hiển thị 10 cái đầu tiên
                self.stdout.write(f"  - {key}: {value}")
                count += 1
            else:
                break
        if len(default_preferences) > 10:
            self.stdout.write(f"  ... và {len(default_preferences) - 10} preferences khác")
        
        # Print the generated configuration
        self.stdout.write(f"\nGenerated configuration:")
        self.stdout.write(json.dumps(unit_preferences, indent=2))
        
        # Update the database if requested
        if options['update']:
            try:
                config, created = AdminConfig.objects.get_or_create(
                    name='Unit Config',
                    defaults={'settings': {'unit_preferences': unit_preferences}}
                )
                
                if not created:
                    settings = config.settings
                    settings['unit_preferences'] = unit_preferences
                    config.settings = settings
                    config.save()
                
                self.stdout.write(self.style.SUCCESS(
                    f"{'Created' if created else 'Updated'} Unit Config with hierarchical unit preferences"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error updating database: {str(e)}")) 