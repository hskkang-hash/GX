from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from core.base import BaseModel
from common.base_model import BaseModelWithGroup
from core.file_management.models import UserMediaFileItem, UserMediaFile
from devices.utils import standardize_unit 
from core.user.models import UserGroup
from pint import UnitRegistry
import json
from django.utils.translation import gettext_lazy as _
ureg = UnitRegistry()
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from core.user.models import Country
class Unit(BaseModel):
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10)
    type = models.CharField(max_length=50, help_text='temperature, weight, length, etc')
    base_unit = models.BooleanField(default=False, help_text='true for base units like C, kg, m')
    conversion_factor = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    conversion_formula = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = [('symbol', 'type')]
        indexes = [
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return f"{self.name} ({self.symbol})"



class Measurement(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    entity = GenericForeignKey('content_type', 'object_id')
    measurement_type = models.CharField(max_length=255, db_index=True)
    data = models.JSONField()
    
    class Meta:
        indexes = [
            models.Index(fields=['measurement_type']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['measurement_type', 'content_type', 'object_id']),
        ]

    VALID_TYPES = [
        'simple',      # Single value with unit (e.g., "5 kg")
        'range',       # Range with unit (e.g., "-20°C to 50°C")
        'dimensions',  # Length x Width x Height (e.g., "100mm x 50mm x 30mm")
        'multi_value', # Multiple values with same unit (e.g., frequencies)
        'error_margin' # Value with error margin (e.g., "±1.5m")
    ]
    def clean(self):
        super().clean()
        
        if not self.data or not isinstance(self.data, dict):
            raise ValidationError("Invalid data format")
            
        data_type = self.data.get('type')
        if not data_type or data_type not in self.VALID_TYPES:
            raise ValidationError(f"Invalid measurement type. Must be one of: {self.VALID_TYPES}")
            
        # Type-specific validation
        if data_type == 'simple':
            if 'value' not in self.data or 'unit' not in self.data:
                raise ValidationError("Simple measurement must have 'value' and 'unit'")
            if not isinstance(self.data['value'], (int, float)):
                raise ValidationError("Value must be numeric")
                
        elif data_type == 'range':
            if 'min' not in self.data or 'max' not in self.data or 'unit' not in self.data:
                raise ValidationError("Range measurement must have 'min', 'max' and 'unit'")
            if self.data['min'] > self.data['max']:
                raise ValidationError("Min value cannot be greater than max value")
                
        elif data_type == 'dimensions':
            required = ['length', 'width', 'unit']
            if not all(key in self.data for key in required):
                raise ValidationError(f"Dimensions measurement must have: {required}")
            
    def save(self, *args, **kwargs):
        self.full_clean()  # Run validation before saving
        super().save(*args, **kwargs)

    def get_formatted_value(self, user_units=None):
        """Trả về giá trị đã được định dạng dựa trên loại dữ liệu"""
        from devices.utils import get_formatted_measurement
        return get_formatted_measurement(self, user_units)
    
    def get_numeric_value(self, component=None, user_units=None):
        """Trả về giá trị số thuần túy để tính toán, có hỗ trợ chuyển đổi đơn vị"""
        from devices.utils import get_numeric_value
        return get_numeric_value(self, component, user_units)
        
    def get_converted_data(self, user_units=None):
        """Trả về data đã được chuyển đổi đơn vị theo tùy chọn người dùng"""
        from devices.utils import convert_measurement_data_to_user_units
        return convert_measurement_data_to_user_units(self, user_units)

    def __str__(self):
        return f"{self.measurement_type}: {self.get_formatted_value()}"

    @classmethod
    def create_from_string(cls, entity, measurement_type, value_string):
        """Tạo measurement từ chuỗi giá trị"""
        from devices.utils import process_measurement_string
        return process_measurement_string(entity, measurement_type, value_string)

    VALID_UNITS = {
        'weight': ['g', 'kg', 'lb', 'oz'],
        'length': ['mm', 'cm', 'm', 'km', 'in', 'ft'],
        'speed': ['m/s', 'km/h', 'mph', 'knot'],
        'temperature': ['°C', '°F', 'K'],
        'time': ['s', 'min', 'h'],
        'voltage': ['V', 'mV', 'kV'],
        'current': ['A', 'mA'],
        'power': ['W', 'kW'],
        'energy': ['mAh', 'Ah', 'Wh', 'kWh'],
        'frequency': ['Hz', 'kHz', 'MHz', 'GHz'],
        'angle': ['°', 'rad'],
        'percentage': ['%'],
        'precipitation': ['mm/h', 'cm/h', 'in/h'],
        'sound': ['dB', 'dBA'],
        'resolution': ['px', 'dpi', 'ppi'],
        'frame_rate': ['fps'],
    }

    def clean(self):
        """Validate measurement data"""
        data = self.data
        
        if not data or not isinstance(data, dict):
            raise ValidationError("Invalid measurement data format")
            
        data_type = data.get('type')
        if not data_type:
            raise ValidationError("Measurement type is required")
            
        # Validate based on data type
        if data_type == 'simple':
            if 'value' not in data:
                raise ValidationError("Value is required for simple measurement")
            if not isinstance(data['value'], (int, float)):
                raise ValidationError("Value must be numeric")
                
        elif data_type == 'range':
            if 'min' not in data or 'max' not in data:
                raise ValidationError("Min and max values are required for range")
            if data['min'] > data['max']:
                raise ValidationError("Min value cannot be greater than max value")
                
        # Validate unit if present
        if 'unit' in data:
            unit = standardize_unit(data['unit'])
            # Check if unit is valid for measurement type
            valid_units = []
            for category, units in self.VALID_UNITS.items():
                valid_units.extend(units)
            if unit not in valid_units:
                raise ValidationError(f"Invalid unit: {unit}")

class DeviceType(BaseModel):
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField()
    TRANSLATABLE_FIELDS = ['name', 'description']
    
    class Meta:
        indexes = [
            models.Index(fields=['name']),
        ]

class FrameClass(BaseModel):
    """FRAME_CLASS xác định loại khung tổng quát (ví dụ: Quad, Hexa, Octa, Heli, SingleCopter, CoaxCopter)"""
    name = models.CharField(max_length=255, db_index=True)
    code = models.CharField(max_length=255, db_index=True, unique=True)
    description = models.TextField(null=True, blank=True)
    order = models.IntegerField(default=0, help_text="Thứ tự hiển thị")
    
    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['code']),
            models.Index(fields=['order']),
        ]
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name

class FrameType(BaseModel):
    """FRAME_TYPE xác định cấu hình cụ thể trong loại khung đó (ví dụ: X, H, V, Plus)"""
    name = models.CharField(max_length=255, db_index=True)
    code = models.CharField(max_length=255, db_index=True, unique=True)
    description = models.TextField(null=True, blank=True)
    order = models.IntegerField(default=0, help_text="Thứ tự hiển thị")
    
    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['code']),
            models.Index(fields=['order']),
        ]
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
class Library(BaseModel):
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, null=True, blank=True)
    is_enabled = models.BooleanField(default=True)
    active = models.BooleanField(default=False)
    main_type = models.ForeignKey(DeviceType, on_delete=models.CASCADE, related_name='library_main_type',null=True,blank=True)
    sub_type = models.CharField(max_length=255, null=True, blank=True)
    avatar = models.ForeignKey(UserMediaFile, on_delete=models.SET_NULL, related_name='library_avatar', null=True, blank=True)
    file_attachments = GenericRelation(UserMediaFileItem)
    note = models.TextField(null=True, blank=True)
    def __str__(self): 
        return f"{self.name}"

    def get_all_measurements(self):
        """Get all measurements associated with this device and its related entities"""
        from django.contrib.contenttypes.models import ContentType
        
        # Get measurements directly related to the device
        device_type = ContentType.objects.get_for_model(self)
        measurements = list(Measurement.objects.filter(
            content_type=device_type,
            object_id=self.id
        ))
        
        # Get measurements for related entities
        related_entities = [
            self.dimensions_and_weight if hasattr(self, 'dimensions_and_weight') else None,
            self.propulsion_system if hasattr(self, 'propulsion_system') else None,
            self.flight_performance if hasattr(self, 'flight_performance') else None,
            self.navigation_control if hasattr(self, 'navigation_control') else None,
            self.radio_communication if hasattr(self, 'radio_communication') else None,
            self.telemetry if hasattr(self, 'telemetry') else None,
            self.cargo_compartment if hasattr(self, 'cargo_compartment') else None,
            self.sensor_suite if hasattr(self, 'sensor_suite') else None,
            self.packaging_specification if hasattr(self, 'packaging_specification') else None,
            self.manufacturer_information if hasattr(self, 'manufacturer_information') else None,
            self.insurance_information if hasattr(self, 'insurance_information') else None,
            self.environmental_specification if hasattr(self, 'environmental_specification') else None,
            self.safety_feature if hasattr(self, 'safety_feature') else None,
        ]

        # Add cargo compartments (many-to-one relationship)
        related_entities.extend(list(self.cargo_compartments.all()))
        
        # Add device protocols (many-to-many relationship through model)
        related_entities.extend(list(self.library_protocols.all()))
        
        # Add device cameras (many-to-many relationship through model)
        related_entities.extend(list(self.library_cameras.all()))
        
        # Get measurements for all related entities
        for entity in filter(None, related_entities):
            entity_type = ContentType.objects.get_for_model(entity)
            entity_measurements = Measurement.objects.filter(
                content_type=entity_type,
                object_id=entity.id
            )
            measurements.extend(entity_measurements)
        
        return measurements

    def get_entity_measurements(self, entity_model_name, measurement_type=None):
        """
        Get measurements for a specific related entity type
        
        Args:
            entity_model_name: String name of the model (e.g. 'DimensionsAndWeight')
            measurement_type: Optional filter by measurement type
        """
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType
        
        model = apps.get_model('devices', entity_model_name)
        
        # Find all instances of this model related to the device
        if hasattr(self, entity_model_name.lower()):
            # One-to-one relationship
            entity = getattr(self, entity_model_name.lower())
            if entity:
                entity_type = ContentType.objects.get_for_model(entity)
                query = {
                    'content_type': entity_type,
                    'object_id': entity.id
                }
                if measurement_type:
                    query['measurement_type'] = measurement_type
                
                return Measurement.objects.filter(**query)
            
        else:
            # Try related_name based on model name (lowercase + 's')
            related_name = f"{entity_model_name.lower()}s"
            if hasattr(self, related_name):
                entities = getattr(self, related_name).all()
                
                measurements = []
                entity_type = ContentType.objects.get_for_model(model)
                for entity in entities:
                    query = {
                        'content_type': entity_type,
                        'object_id': entity.id
                    }
                    if measurement_type:
                        query['measurement_type'] = measurement_type
                    
                    entity_measurements = Measurement.objects.filter(**query)
                    measurements.extend(entity_measurements)
                
                return measurements
        
        return Measurement.objects.none()
    
    def clean(self):
        if not self.name:
            raise ValidationError("Device name is required")
        if not self.model:
            raise ValidationError("Device model is required")
        if not self.serial_number:
            raise ValidationError("Serial number is required")
            
        # Validate status
        valid_statuses = ['active', 'inactive', 'maintenance', 'retired']
        if self.status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
            
        # Validate device type
        valid_types = ['drone', 'robot', 'vehicle']
        if self.main_type not in valid_types:
            raise ValidationError(f"Invalid device type. Must be one of: {', '.join(valid_types)}")


class DeviceStatus(BaseModel):
    # choose status from list
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('on_mission', 'On mission'),
        ('operational', 'Operational'),
        ('maintenance', 'Maintenance'),
        ('inactive', 'Inactive'),
        ('retired', 'Retired'),
        ('warning', 'Warning'),
        ('return', 'Return'),
    ]
    name = models.CharField(max_length=255, default='Available')
    code = models.CharField(max_length=255, choices=STATUS_CHOICES, unique=True, default='available', db_index=True)
    description = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name']
    class Meta:
        indexes = [
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"
    
    

class Device(BaseModel):
    name = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=255, unique=True)
    unit_id = models.CharField(unique=True,null=True,blank=True)
    library = models.ForeignKey(Library, on_delete=models.CASCADE, related_name='devices',null=True,blank=True)
    status = models.ForeignKey(DeviceStatus, on_delete=models.CASCADE, related_name='devices',null=True,blank=True, db_index=True)
    active = models.BooleanField(default=False, db_index=True)
    main_type = models.ForeignKey(DeviceType, on_delete=models.CASCADE, related_name='main_type',null=True,blank=True, db_index=True)
    sub_type = models.CharField(max_length=255, null=True, blank=True)
    avatar = models.ForeignKey(UserMediaFile, on_delete=models.SET_NULL, related_name='device_avatar', null=True, blank=True)
    file_attachments = GenericRelation(UserMediaFileItem)
    note = models.TextField(null=True, blank=True)
    terminal = models.ForeignKey("terminals.Terminal", on_delete=models.CASCADE, related_name='devices',null=True,blank=True, db_index=True)
    color = models.CharField(max_length=255, null=True, blank=True)
    approve_flight_now = models.BooleanField(default=None, db_index=True, null=True, blank=True)
    on_approve_flight = models.BooleanField(default=False, db_index=True, null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'active']),
            models.Index(fields=['main_type', 'active']),
            models.Index(fields=['terminal', 'active']),
            models.Index(fields=['status', 'main_type', 'active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

    def get_all_measurements(self):
        """Get all measurements associated with this device and its related entities"""
        from django.contrib.contenttypes.models import ContentType
        
        # Get measurements directly related to the device
        device_type = ContentType.objects.get_for_model(self)
        measurements = list(Measurement.objects.filter(
            content_type=device_type,
            object_id=self.id
        ))
        
        # Get measurements for related entities
        related_entities = [
            self.dimensions_and_weight if hasattr(self, 'dimensions_and_weight') else None,
            self.propulsion_system if hasattr(self, 'propulsion_system') else None,
            self.flight_performance if hasattr(self, 'flight_performance') else None,
            self.navigation_control if hasattr(self, 'navigation_control') else None,
            self.radio_communication if hasattr(self, 'radio_communication') else None,
            self.telemetry if hasattr(self, 'telemetry') else None,
            self.cargo_compartment if hasattr(self, 'cargo_compartment') else None,
            self.sensor_suite if hasattr(self, 'sensor_suite') else None,
            self.packaging_specification if hasattr(self, 'packaging_specification') else None,
            self.manufacturer_information if hasattr(self, 'manufacturer_information') else None,
            self.insurance_information if hasattr(self, 'insurance_information') else None,
            self.environmental_specification if hasattr(self, 'environmental_specification') else None,
            self.safety_feature if hasattr(self, 'safety_feature') else None,
        ]

        # Add cargo compartments (many-to-one relationship)
        related_entities.extend(list(self.cargo_compartments.all()))
        
        # Add device protocols (many-to-many relationship through model)
        related_entities.extend(list(self.device_protocols.all()))
        
        # Add device cameras (many-to-many relationship through model)
        related_entities.extend(list(self.device_cameras.all()))
        
        # Get measurements for all related entities
        for entity in filter(None, related_entities):
            entity_type = ContentType.objects.get_for_model(entity)
            entity_measurements = Measurement.objects.filter(
                content_type=entity_type,
                object_id=entity.id
            )
            measurements.extend(entity_measurements)
        
        return measurements

    def get_entity_measurements(self, entity_model_name, measurement_type=None):
        """
        Get measurements for a specific related entity type
        
        Args:
            entity_model_name: String name of the model (e.g. 'DimensionsAndWeight')
            measurement_type: Optional filter by measurement type
        """
        from django.apps import apps
        from django.contrib.contenttypes.models import ContentType
        
        model = apps.get_model('devices', entity_model_name)
        
        # Find all instances of this model related to the device
        if hasattr(self, entity_model_name.lower()):
            # One-to-one relationship
            entity = getattr(self, entity_model_name.lower())
            if entity:
                entity_type = ContentType.objects.get_for_model(entity)
                query = {
                    'content_type': entity_type,
                    'object_id': entity.id
                }
                if measurement_type:
                    query['measurement_type'] = measurement_type
                
                return Measurement.objects.filter(**query)
            
        else:
            # Try related_name based on model name (lowercase + 's')
            related_name = f"{entity_model_name.lower()}s"
            if hasattr(self, related_name):
                entities = getattr(self, related_name).all()
                
                measurements = []
                entity_type = ContentType.objects.get_for_model(model)
                for entity in entities:
                    query = {
                        'content_type': entity_type,
                        'object_id': entity.id
                    }
                    if measurement_type:
                        query['measurement_type'] = measurement_type
                    
                    entity_measurements = Measurement.objects.filter(**query)
                    measurements.extend(entity_measurements)
                
                return measurements
        
        return Measurement.objects.none()
    
    def clean(self):
        if not self.name:
            raise ValidationError("Device name is required")
        if not self.model:
            raise ValidationError("Device model is required")
        if not self.serial_number:
            raise ValidationError("Serial number is required")
            
        # Validate status
        valid_statuses = ['active', 'inactive', 'maintenance', 'retired']
        if self.status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
            
        # Validate device type
        valid_types = ['drone', 'robot', 'vehicle']
        if self.main_type not in valid_types:
            raise ValidationError(f"Invalid device type. Must be one of: {', '.join(valid_types)}")



class MeasurableModel(BaseModel):
    measurements = GenericRelation(Measurement)
    
    class Meta:
        abstract = True

    @classmethod
    def get_valid_measurement_types(cls):
        if not hasattr(cls, 'MEASUREMENT_TYPES'):
            raise NotImplementedError(f"{cls.__name__} must define MEASUREMENT_TYPES")
        return cls.MEASUREMENT_TYPES

    def get_all_measurements_formatted(self, user_units=None):
        """Get all measurements with formatted values"""
        result = {}
        for m_type in self.MEASUREMENT_TYPES.keys():
            measurement = self.measurements.filter(measurement_type=m_type).first()
            if measurement:
                result[m_type] = measurement.get_formatted_value(user_units)
        return result
        
    def get_all_measurements_converted(self, user_units=None):
        """Get all measurements with data converted to user units"""
        result = {}
        for m_type in self.MEASUREMENT_TYPES.keys():
            measurement = self.measurements.filter(measurement_type=m_type).first()
            if measurement:
                result[m_type] = measurement.get_converted_data(user_units)
        return result

    def validate_measurement_type(self, measurement_type):
        valid_types = self.get_valid_measurement_types()
        if measurement_type not in valid_types:
            raise ValidationError(
                f"Invalid measurement_type '{measurement_type}' for {self.__class__.__name__}. "
                f"Valid types are: {list(valid_types.keys())}"
            )
        return valid_types[measurement_type]

    def create_measurement(self, measurement_type, data):
        measurement_info = self.validate_measurement_type(measurement_type)
        
        # Validate data structure based on type
        if not isinstance(data, dict):
            raise ValidationError("Data must be a dictionary")
            
        expected_type = measurement_info['type']
        if data.get('type') != expected_type:
            raise ValidationError(f"Data type must be '{expected_type}'")
            
        # Validate required fields based on type
        if expected_type == 'simple':
            if 'value' not in data or 'unit' not in data:
                raise ValidationError("Simple measurement must have 'value' and 'unit'")
        elif expected_type == 'range':
            if 'min' not in data or 'max' not in data or 'unit' not in data:
                raise ValidationError("Range measurement must have 'min', 'max' and 'unit'")
        elif expected_type == 'dimensions':
            if 'length' not in data or 'width' not in data or 'unit' not in data:
                raise ValidationError("Dimensions measurement must have 'length', 'width' and 'unit'")
                
        return Measurement.objects.create(
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.id,
            measurement_type=measurement_type,
            data=data
        )

    def get_measurement(self, measurement_type):
        """Lấy đối tượng measurement theo loại"""
        return self.measurements.filter(measurement_type=measurement_type).first()
    
    def get_formatted_value(self, measurement_type, user_units=None):
        """Lấy giá trị định dạng của measurement"""
        measurement = self.get_measurement(measurement_type)
        if measurement:
            return measurement.get_formatted_value(user_units)
        return None
    
    def get_numeric_value(self, measurement_type, component=None, user_units=None):
        """Lấy giá trị số cho tính toán, có hỗ trợ chuyển đổi đơn vị"""
        measurement = self.get_measurement(measurement_type)
        if measurement:
            return measurement.get_numeric_value(component, user_units)
        return None
    
    def set_measurement(self, measurement_type, value_string):
        """Đặt giá trị cho measurement từ chuỗi"""
        from devices.utils import process_measurement_string
        
        # Xóa measurement cũ nếu có
        existing = self.get_measurement(measurement_type)
        if existing:
            existing.delete()
            
        # Tạo measurement mới
        if measurement_type in self.MEASUREMENT_TYPES:
            return process_measurement_string(self, measurement_type, value_string)
        return None

    def get_converted_data(self, measurement_type, user_units=None):
        """Lấy dữ liệu measurement đã được chuyển đổi đơn vị theo tùy chọn người dùng"""
        measurement = self.get_measurement(measurement_type)
        if measurement:
            return measurement.get_converted_data(user_units)
        return None
        
    def get_unit_preference(self, measurement_type, user_units=None):
        """Lấy đơn vị ưu tiên cho loại measurement cụ thể"""
        from devices.utils import get_unit_preference
        
        if not user_units:
            from core.configuration.models import AdminConfig
            try:
                config = AdminConfig.objects.get(name='Unit Config').settings 
                user_units = config.get('unit_preferences', {})
            except AdminConfig.DoesNotExist:
                user_units = {}
                
        return get_unit_preference(user_units, measurement_type, self.__class__.__name__)

class DimensionsAndWeight(MeasurableModel):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='dimensions_and_weight',null=True,blank=True)
    library = models.OneToOneField(Library, on_delete=models.CASCADE, related_name='dimensions_and_weight',null=True,blank=True)
    frame_class = models.ForeignKey(FrameClass, on_delete=models.SET_NULL, related_name='dimensions_and_weights', null=True, blank=True, db_index=True)
    frame_type = models.ForeignKey(FrameType, on_delete=models.SET_NULL, related_name='dimensions_and_weights', null=True, blank=True, db_index=True)
    MEASUREMENT_TYPES = {
        'frame_size': {'type': 'dimensions', 'default_unit': 'mm'},
        'maximum_takeoff_weight': {'type': 'simple', 'default_unit': 'kg'},
        'payload_capacity': {'type': 'simple', 'default_unit': 'kg'},
        'empty_weight': {'type': 'simple', 'default_unit': 'kg'}
    }
    
    def clean(self):
        """Kiểm tra ràng buộc dữ liệu"""
        max_weight = self.get_numeric_value('maximum_takeoff_weight')
        empty_weight = self.get_numeric_value('empty_weight')
        
        if max_weight is not None and empty_weight is not None:
            if max_weight <= empty_weight:
                raise ValidationError("Maximum takeoff weight must be greater than empty weight")

class MotorType(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name', 'description']
class BatteryType(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name', 'description']
class PropulsionSystem(MeasurableModel):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='propulsion_system',null=True,blank=True)
    library = models.OneToOneField(Library, on_delete=models.CASCADE, related_name='propulsion_system',null=True,blank=True)
    number_of_motors = models.IntegerField(null=True, blank=True)
    motor_type = models.ForeignKey(MotorType, on_delete=models.CASCADE, related_name='motor_type',null=True,blank=True)
    battery_type = models.ForeignKey(BatteryType, on_delete=models.CASCADE, related_name='battery_type',null=True,blank=True)
    
    MEASUREMENT_TYPES = {
        'motor_power': {'type': 'simple', 'default_unit': 'kW',},
        'propeller_size': {'type': 'simple', 'default_unit': 'inch'},
        'battery_capacity': {'type': 'simple', 'default_unit': 'mAh'},
        'flight_time': {'type': 'simple', 'default_unit': 'min'},
        'charging_time': {'type': 'simple', 'default_unit': 'min'}
    }
    
    def clean(self):
        """Kiểm tra ràng buộc dữ liệu"""
        max_weight = self.get_numeric_value('maximum_takeoff_weight')
        empty_weight = self.get_numeric_value('empty_weight')
        
        if max_weight is not None and empty_weight is not None:
            if max_weight <= empty_weight:
                raise ValidationError("Maximum takeoff weight must be greater than empty weight")

class FlightPerformance(MeasurableModel):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='flight_performance',null=True,blank=True)
    library = models.OneToOneField(Library, on_delete=models.CASCADE, related_name='flight_performance',null=True,blank=True)
    MEASUREMENT_TYPES = {
        'maximum_speed': {'type': 'simple', 'default_unit': 'km/h'},
        'cruise_speed': {'type': 'simple', 'default_unit': 'm/s'},
        'maximum_altitude': {'type': 'simple', 'default_unit': 'm'},
        'operating_altitude': {'type': 'range', 'default_unit': 'm'},
        'maximum_range': {'type': 'simple', 'default_unit': 'km'},
        'wind_resistance': {'type': 'simple', 'default_unit': 'm/s'}
    }
       
class IMU(BaseModel):   
    name = models.CharField(max_length=255)
    description = models.TextField()
    TRANSLATABLE_FIELDS = ['name', 'description']
class NavigationControl(MeasurableModel):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='navigation_control',null=True,blank=True)
    barometric_altimeter = models.BooleanField(default=False)
    library = models.OneToOneField(Library, on_delete=models.CASCADE, related_name='navigation_control',null=True,blank=True)
    MEASUREMENT_TYPES = {
        'gps_accuracy': {'type': 'error_margin', 'default_unit': 'm'},
        'imu': {'type': 'string', 'default_unit': 'm'}
    }

class RadioCommunication(MeasurableModel):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='radio_communication',null=True,blank=True)
    library = models.OneToOneField(Library, on_delete=models.CASCADE, related_name='radio_communication',null=True,blank=True)
    MEASUREMENT_TYPES = {
        'frequency': {'type': 'simple', 'default_unit': 'GHz'},
        'range': {'type': 'simple', 'default_unit': 'km'}
    }

class Telemetry(BaseModel):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='telemetry',null=True,blank=True)
    library = models.OneToOneField(Library, on_delete=models.CASCADE, related_name='telemetry',null=True,blank=True)
    realtime_flight_data = models.BooleanField(default=False)
    video_streaming = models.BooleanField(default=False)
    battery_status_monitoring = models.BooleanField(default=False)
    gps_position_tracking = models.BooleanField(default=False)
    system_health_monitoring = models.BooleanField(default=False)
    TRANSLATABLE_FIELDS = ['name', 'description']
class Protocol(BaseModel):
    name = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)
    version = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name', 'description','type']
    def __str__(self):
        return f"{self.name} v{self.version}"


class DeviceProtocol(BaseModel):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='device_protocols',null=True,blank=True)
    library = models.ForeignKey(Library, on_delete=models.CASCADE, related_name='library_protocols',null=True,blank=True)
    protocol = models.ForeignKey(Protocol, on_delete=models.CASCADE, related_name='device_protocols')
    enabled = models.BooleanField(default=False)
    config = models.JSONField(null=True, blank=True)


class ImageStabilization(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name', 'description']


class CameraType(MeasurableModel):
    name = models.CharField(max_length=255)
    model = models.CharField(max_length=255)
    image_stabilization = models.ForeignKey(ImageStabilization, on_delete=models.CASCADE, related_name='image_stabilization',null=True,blank=True)
    night_vision = models.BooleanField(default=False)
    thermal_imaging = models.BooleanField(default=False)
    status = models.CharField(max_length=50, null=True, blank=True)
    active = models.BooleanField(default=True)
    specifications = models.JSONField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    MEASUREMENT_TYPES = {
        'resolution': {'type': 'resolution', 'default_unit': 'px'},
        'field_of_view': {'type': 'range', 'default_unit': '°'},
        'frame_rate': {'type': 'simple', 'default_unit': 'fps'},
        'weight': {'type': 'range', 'default_unit': 'g'},
        'zoom_capability': {'type': 'simple', 'default_unit': 'x'},
        'avg_weight': {'type': 'simple', 'default_unit': 'g'},
        'sensor_size': {'type': 'simple', 'default_unit': 'inch'},
        'sensor_resolution': {'type': 'simple', 'default_unit': 'MP'},
        'min_illumination': {'type': 'simple', 'default_unit': 'lux'},
        'dynamic_range': {'type': 'simple', 'default_unit': 'dB'},
        'thermal_sensitivity': {'type': 'simple', 'default_unit': 'mK'},
        'depth_range': {'type': 'range', 'default_unit': 'm'},
    }
    
    def __str__(self):
        return f"{self.name} ({self.model})"
 

class SensorSuite(BaseModel):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='sensor_suite',null=True,blank=True)
    library = models.OneToOneField(Library, on_delete=models.CASCADE, related_name='sensor_suite',null=True,blank=True)
    gnss = models.ForeignKey('GNSSSystem', on_delete=models.CASCADE, related_name='sensor_suite_gnss',null=True,blank=True)
    optical_flow_sensor = models.BooleanField(default=False)
    ultrasonic_sensors = models.BooleanField(default=False)
    lidar = models.BooleanField(default=False)
    ais = models.BooleanField(default=False)
    ads_b_receiver = models.BooleanField(default=False)
    rf_signal_detector = models.BooleanField(default=False)
    chemical_sensor_array = models.BooleanField(default=False)
    radiation_detector = models.BooleanField(default=False)
    weather_sensors = models.BooleanField(default=False)

class GNSSSystem(BaseModel):
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=255, null=True, blank=True)
    accuracy = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    update_rate = models.IntegerField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name', 'description']

    def __str__(self):
        return f"{self.name} v{self.version}"


class DeviceGNSS(BaseModel):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='device_gnss',null=True,blank=True)
    library = models.ForeignKey(Library, on_delete=models.CASCADE, related_name='library_gnss',null=True,blank=True)
    gnss = models.ForeignKey(GNSSSystem, on_delete=models.CASCADE, related_name='device_gnss')
    is_primary = models.BooleanField(default=False)
    enabled = models.BooleanField(default=False)
    config = models.JSONField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name', 'description']
class PackageType(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name', 'description']
class PackagingSpecification(MeasurableModel):
    name = models.CharField(max_length=255, null=True, blank=True)
    code = models.CharField(max_length=255, null=True, blank=True, unique=True, db_index=True)
    water_proof = models.CharField(null=True, blank=True)
    fragile = models.BooleanField(default=False)
    package_type = models.ForeignKey(PackageType, on_delete=models.CASCADE, related_name='packaging_specification',null=True,blank=True)
    note = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['active']),
            models.Index(fields=['code', 'active']),
        ]
    
    MEASUREMENT_TYPES = {
        'dimensions': {'type': 'dimensions', 'default_unit': 'mm'},
        'max_weight': {'type': 'simple', 'default_unit': 'kg'},
        'max_volume': {'type': 'simple', 'default_unit': 'm3'},
        'max_length': {'type': 'simple', 'default_unit': 'm'},
        'max_width': {'type': 'simple', 'default_unit': 'm'},
        'max_height': {'type': 'simple', 'default_unit': 'm'},

    }
    
    def clean(self):
        """Kiểm tra ràng buộc dữ liệu"""
        max_weight = self.get_numeric_value('max_weight')
        
        if max_weight is not None:
            if max_weight <= 0:
                raise ValidationError("Weight must be positive")
            
        max_volume = self.get_numeric_value('max_volume')
        if max_volume is not None:
            if max_volume <= 0:
                raise ValidationError("Volume must be positive")
                
    def __str__(self):
        return f"{self.name} ({self.code})"

class PackagingOption(BaseModel):
    name = models.CharField(max_length=255, null=True, blank=True)
    order = models.IntegerField(default=1, db_index=True)
    
    def __str__(self):
        return f"Option {self.order}: {self.name}"
    
    class Meta:
        indexes = [
            models.Index(fields=['order']),
        ]

class PackagingOptionSpecification(BaseModel):
    option = models.ForeignKey(PackagingOption, on_delete=models.CASCADE, related_name='specifications',null=True,blank=True, db_index=True)
    package = models.ForeignKey(PackagingSpecification, on_delete=models.CASCADE, related_name='options',null=True,blank=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['option']),
            models.Index(fields=['package']),
            models.Index(fields=['option', 'package']),
        ]

class PackagingSpecificationDevice(BaseModel):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='packaging_specification_device',null=True,blank=True, db_index=True)
    library = models.ForeignKey(Library, on_delete=models.CASCADE, related_name='packaging_specification_library',null=True,blank=True)
    option = models.ForeignKey(PackagingOption, on_delete=models.CASCADE, related_name='devices',null=True,blank=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['device']),
            models.Index(fields=['option']),
            models.Index(fields=['device', 'option']),
        ]



class ManufacturerInformation(MeasurableModel):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='manufacturer_information',null=True,blank=True)
    library = models.OneToOneField(Library, on_delete=models.CASCADE, related_name='manufacturer_information',null=True,blank=True)
    manufacturer = models.CharField(max_length=255, null=True, blank=True)
    country_of_origin = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='manufacturer_information',null=True,blank=True)
    model_number = models.CharField(max_length=255, null=True, blank=True)
    serial_number = models.CharField(max_length=255, null=True, blank=True)
    production_date = models.DateField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    insurance_type = models.CharField(max_length=255, null=True, blank=True)
    insurance_provider = models.CharField(max_length=255, null=True, blank=True)
    policy_number = models.CharField(max_length=255, null=True, blank=True)
    validity_period_from = models.DateField(null=True, blank=True)
    validity_period_to = models.DateField(null=True, blank=True)
    current_status = models.CharField(max_length=255, null=True, blank=True)
    registration_number = models.CharField(max_length=255, null=True, blank=True)
    MEASUREMENT_TYPES = {
        # Add any measurement types specific to ManufacturerInformation if needed
    }

class InsuranceInformation(MeasurableModel):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='insurance_information',null=True,blank=True)
    library = models.OneToOneField(Library, on_delete=models.CASCADE, related_name='insurance_information',null=True,blank=True)
    insurance_status = models.BooleanField(default=False)
    insurance_type = models.CharField(max_length=255, null=True, blank=True)
    insurance_provider = models.CharField(max_length=255, null=True, blank=True)
    policy_number = models.CharField(max_length=255, null=True, blank=True)
    validity_period_from = models.DateField(null=True, blank=True)
    validity_period_to = models.DateField(null=True, blank=True)
    current_status = models.CharField(max_length=255, null=True, blank=True)
    
    MEASUREMENT_TYPES = {
        # Add any measurement types specific to InsuranceInformation if needed
    }

class EnvironmentalSpecification(MeasurableModel):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='environmental_specification',null=True,blank=True)
    library = models.OneToOneField(Library, on_delete=models.CASCADE, related_name='environmental_specification',null=True,blank=True)
    MEASUREMENT_TYPES = {
        'temperature_range': {'type': 'range', 'default_unit': '°C'},
        'humidity': {'type': 'range', 'default_unit': '%'},
        'precipitation': {'type': 'string', 'default_unit': 'mm/h'},
        'wind_speed': {'type': 'up_to', 'default_unit': 'km/h'},
        'noise_takeoff': {'type': 'simple', 'default_unit': 'dB'},
        'noise_cruise': {'type': 'simple', 'default_unit': 'dB'},
        'noise_landing': {'type': 'simple', 'default_unit': 'dB'}
    }

class SafetyFeature(MeasurableModel):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name='safety_feature',null=True,blank=True)
    library = models.OneToOneField(Library, on_delete=models.CASCADE, related_name='safety_feature',null=True,blank=True)
    dual_imu = models.BooleanField(default=False)
    dual_gps = models.BooleanField(default=False)
    dual_battery = models.BooleanField(default=False)
    emergency_parachute = models.BooleanField(default=False)
    return_to_home = models.BooleanField(default=False)
    obstacle_detection_360 = models.BooleanField(default=False)
    stereo_cameras = models.BooleanField(default=False)
    lidar_mapping = models.BooleanField(default=False)
    emergency_braking = models.BooleanField(default=False)
    
    MEASUREMENT_TYPES = {
        # Add any measurement types specific to SafetyFeature if needed
    }










class DeviceCamera(BaseModel):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='device_cameras',null=True,blank=True)
    library = models.ForeignKey(Library, on_delete=models.CASCADE, related_name='library_cameras',null=True,blank=True)
    camera = models.ForeignKey(CameraType, on_delete=models.CASCADE, related_name='device_cameras')
    position = models.CharField(max_length=255,null=True,blank=True)
    enabled = models.BooleanField(default=True)
    config = models.JSONField(null=True,blank=True)



# class Package(BaseModel):
#     name = models.CharField(max_length=255)
#     tracking_number = models.CharField(max_length=255)
#     weight = models.DecimalField(max_digits=10, decimal_places=2)
#     volume = models.DecimalField(max_digits=10, decimal_places=2)
#     dimensions = models.CharField(max_length=255)
#     priority = models.IntegerField()
#     status = models.CharField(max_length=50)
#     special_handling_instructions = models.TextField()
#     temperature_requirements = models.CharField(max_length=255)
#     hazmat_classification = models.CharField(max_length=255)


#     def __str__(self):
#         return f"{self.name} ({self.tracking_number})"


# class DevicePackage(BaseModel):
#     device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='device_packages')
#     package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='device_packages')
#     loading_time = models.DateTimeField()
#     unloading_time = models.DateTimeField(null=True, blank=True)
#     position = models.CharField(max_length=255)
#     status = models.CharField(max_length=50)



# class PackageTracking(BaseModel):
#     package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='tracking_history')
#     device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='package_tracking')
    # location_lat = models.DecimalField(max_digits=10, decimal_places=6)
    # location_long = models.DecimalField(max_digits=10, decimal_places=6)
    # altitude = models.DecimalField(max_digits=10, decimal_places=2)
    # temperature = models.DecimalField(max_digits=10, decimal_places=2)
    # humidity = models.DecimalField(max_digits=10, decimal_places=2)
    # status = models.CharField(max_length=50)
    # timestamp = models.DateTimeField()


class CargoCompartments(MeasurableModel):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='cargo_compartments',null=True,blank=True, db_index=True)
    library = models.ForeignKey(Library, on_delete=models.CASCADE, related_name='cargo_compartments',null=True,blank=True)
    compartment_number = models.IntegerField()
    name = models.CharField(max_length=255)
    secure_locking = models.BooleanField(default=False)
    quick_release = models.BooleanField(default=False)
    temperature_control = models.BooleanField(default=False)
    status = models.CharField(max_length=50, null=True, blank=True)
    
    MEASUREMENT_TYPES = {
        'dimensions': {'type': 'dimensions', 'default_unit': 'mm'},
        'weight_capacity': {'type': 'simple', 'default_unit': 'kg'}
    }
    
    def clean(self):
        """Kiểm tra ràng buộc dữ liệu"""
        max_weight = self.get_numeric_value('max_weight')
        
        if max_weight is not None:
            if max_weight <= 0:
                raise ValidationError("Weight capacity must be positive")

