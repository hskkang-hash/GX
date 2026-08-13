from devices.schemas.schemas_djantic_out import DimensionsWeightOutSchema
from devices.models import DimensionsAndWeight, Measurement
from django.core.exceptions import ValidationError

from devices.utils import convert_unit
from core.middleware.refresh_token import get_current_request
class DimensionsService:
    @staticmethod
    def create_or_update(device=None, library=None, data=None):
        try:
            # Validate required fields
            if device:
                dimensions, created = DimensionsAndWeight._base_manager.get_or_create(device=device)
            elif library:
                dimensions, created = DimensionsAndWeight._base_manager.get_or_create(library=library)
            # Cập nhật frame_class và frame_type nếu có
            if 'frame_class_id' in data:
                dimensions.frame_class_id = data['frame_class_id']
            else:
                dimensions.frame_class_id = None
            if 'frame_type_id' in data:
                dimensions.frame_type_id = data['frame_type_id']
            else:
                dimensions.frame_type_id = None
            # Cập nhật measurements
            for field in ['frame_size', 'maximum_takeoff_weight', 'payload_capacity', 'empty_weight']:
                if field in data and data[field]:
                    try:
                        dimensions.measurements.filter(measurement_type=field).delete()
                        Measurement.create_from_string(dimensions, field, data[field])
                    except Exception as e:
                        raise ValidationError(f"Invalid {field} measurement: {str(e)}")
                
                else:
                    dimensions.measurements.filter(measurement_type=field).delete()
            
            dimensions.save()
            return True, dimensions
        
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_data(device=None, library=None, user_units=None, edit=False):
        """Lấy thông tin hiển thị"""
        try:
            if device:
                dimensions = device.dimensions_and_weight
            elif library:
                dimensions = library.dimensions_and_weight
            request = get_current_request()
            language = request.user.language.code if request.user.language else 'en'
            result = {}
            for field in ['frame_size', 'maximum_takeoff_weight', 'payload_capacity', 'empty_weight']:
                m = dimensions.measurements.filter(measurement_type=field).first()
                if m and edit:
                    result[field] = m.get_formatted_value(user_units)
                elif m:
                    result[field] = m.get_converted_data(user_units)
            frame_type = dimensions.frame_type
            frame_class = dimensions.frame_class
            result['frame_type'] = frame_type.get_translation('name', language) if frame_type else None
            result['frame_class'] = frame_class.get_translation('name', language) if frame_class else None
            result['frame_type_id'] = frame_type.id if frame_type else None
            result['frame_class_id'] = frame_class.id if frame_class else None
            return result if result else None
        except DimensionsAndWeight.DoesNotExist:
            return None

    @staticmethod
    def get_formatted_value(measurement, user_units=None):
        """Format giá trị measurement với unit conversion"""
        data = measurement.data
        data_type = data.get('type')
        
        if not user_units:
            return measurement.get_formatted_value()
        
        try:
            if data_type == 'simple':
                value = data['value']
                unit = data['unit']
                
                # Kiểm tra và chuyển đổi đơn vị nếu cần
                if measurement.measurement_type in user_units:
                    target_unit = user_units[measurement.measurement_type]
                    if target_unit != unit:
                        value = convert_unit(value, unit, target_unit)
                        unit = target_unit
                    
                return f"{value:,g} {unit}"
                
            elif data_type == 'range':
                min_val = data['min']
                max_val = data['max']
                unit = data['unit']
                
                # Chuyển đổi cả min và max
                if measurement.measurement_type in user_units:
                    target_unit = user_units[measurement.measurement_type]
                    if target_unit != unit:
                        min_val = convert_unit(min_val, unit, target_unit)
                        max_val = convert_unit(max_val, unit, target_unit)
                        unit = target_unit
                    
                return f"{min_val:,g} - {max_val:,g} {unit}"
                
            elif data_type == 'dimensions':
                length = data['length']
                width = data['width']
                height = data.get('height')
                unit = data['unit']
                
                # Chuyển đổi tất cả chiều
                if measurement.measurement_type in user_units:
                    target_unit = user_units[measurement.measurement_type]
                    if target_unit != unit:
                        length = convert_unit(length, unit, target_unit)
                        width = convert_unit(width, unit, target_unit)
                        if height:
                            height = convert_unit(height, unit, target_unit)
                        unit = target_unit
                    
                if height:
                    return f"{length:,g} × {width:,g} × {height:,g} {unit}"
                return f"{length:,g} × {width:,g} {unit}"
                
        except Exception as e:
            # Log error và trả về giá trị gốc
            print(f"Error formatting measurement: {str(e)}")
            return measurement.get_formatted_value()
