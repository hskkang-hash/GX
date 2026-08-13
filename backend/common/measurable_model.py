from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from core.base import BaseModelWithGroup

class MeasurableModelWithGroup(BaseModelWithGroup):
    """
    Model kết hợp tính năng của MeasurableModel và BaseModelWithGroup
    """
    measurements = GenericRelation('devices.Measurement')
    
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
                
        return self.measurements.create(
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
            user_units = get_unit_config().get('unit_preferences', {})
                
        return get_unit_preference(user_units, measurement_type, self.__class__.__name__) 

def get_unit_config():
    """Get unit configuration with fallback"""
    try:
        from core.configuration.models import AdminConfig
        config = AdminConfig.objects.get(name='Unit Config').settings
        return config
    except (ImportError, AdminConfig.DoesNotExist, Exception):
        # Fallback to default configuration
        return {
            'length': 'mm',
            'weight': 'kg',
            'temperature': 'celsius',
            'speed': 'km/h',
            'time': 'seconds'
        } 