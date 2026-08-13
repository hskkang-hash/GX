from devices.models import EnvironmentalSpecification, Measurement

class EnvironmentalSpecificationService:
    @staticmethod
    def create_or_update(device=None, library=None, data=None):
        """Tạo hoặc cập nhật thông tin môi trường hoạt động"""
        try:
            # Thử tìm kiếm trước
            if device:
                environmental = EnvironmentalSpecification._base_manager.get(device=device)
            elif library:
                environmental = EnvironmentalSpecification._base_manager.get(library=library)
            
        except EnvironmentalSpecification.DoesNotExist:
            # Tạo mới với các trường bắt buộc
            environmental = EnvironmentalSpecification(
                device=device,
                library=library
            )
        
        environmental.save()
        
        # Xử lý measurements
        measurement_fields = [
            'temperature_range', 'humidity', 'precipitation', 
            'wind_speed', 'noise_takeoff', 'noise_cruise', 'noise_landing'
        ]
        
        for field in measurement_fields:
            if field in data and data[field]:
                environmental.set_measurement(field, data[field])
            else:
                environmental.measurements.filter(measurement_type=field).delete()
        return True, environmental

    @staticmethod
    def get_data(device=None, library=None, user_units=None, edit=False):
        """Lấy thông tin hiển thị"""
        try:
            if device:
                environmental = device.environmental_specification
            elif library:
                environmental = library.environmental_specification
            
            data = {}
            
            # Lấy dữ liệu từ measurements
            measurement_fields = [
                'temperature_range', 'humidity', 'precipitation', 
                'wind_speed', 'noise_takeoff', 'noise_cruise', 'noise_landing'
            ]
            
            for field in measurement_fields:
                m = environmental.measurements.filter(measurement_type=field).first()
                if m and edit:
                    data[field] = m.get_formatted_value(user_units)
                elif m:
                    data[field] = m.get_converted_data(user_units)
                
            return data
        except EnvironmentalSpecification.DoesNotExist:
            return None
