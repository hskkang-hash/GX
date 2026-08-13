from devices.schemas.schemas_djantic_out import PropulsionSystemOutSchema
from devices.models import PropulsionSystem, Measurement

class PropulsionSystemService:
    @staticmethod
    def create_or_update(device=None, library=None, data=None):
        """Tạo hoặc cập nhật thông tin hệ thống đẩy"""
        try:
            data_fields = ['number_of_motors', 'motor_type_id', 'battery_type_id']
            # Thử tìm kiếm trước
            if device:
                propulsion = PropulsionSystem._base_manager.get(device=device)
            elif library:
                propulsion = PropulsionSystem._base_manager.get(library=library)
            # Cập nhật nếu đã tồn tại
            for field in data_fields:
                setattr(propulsion, field, data.get(field,None))

        except PropulsionSystem.DoesNotExist:
            # Tạo mới với các trường bắt buộc
            propulsion = PropulsionSystem(
                device=device,
                library=library,
                number_of_motors=data.get('number_of_motors', 0),
                motor_type_id=data.get('motor_type_id'),
                battery_type_id=data.get('battery_type_id'),

            )
        
        propulsion.save()
        
        # Xử lý measurements
        for field in ['motor_power', 'propeller_size', 'battery_capacity']:
            if field in data and data[field]:
                propulsion.set_measurement(field, data[field])
            else:
                propulsion.measurements.filter(measurement_type=field).delete()
        # Xử lý flight_time và charging_time nếu là chuỗi (measurement)
        if 'flight_time' in data and isinstance(data['flight_time'], str):
            propulsion.set_measurement('flight_time', data['flight_time'])
        else:
            propulsion.measurements.filter(measurement_type='flight_time').delete()
        if 'charging_time' in data and isinstance(data['charging_time'], str):
            propulsion.set_measurement('charging_time', data['charging_time'])
        else:
            propulsion.measurements.filter(measurement_type='charging_time').delete()
        
        return True, propulsion

    @staticmethod
    def get_data(device=None, library=None, user_units=None, edit=False):
        """Lấy thông tin hiển thị"""
        try:
            if device:
                propulsion = device.propulsion_system
            elif library:
                propulsion = library.propulsion_system
            
            data = PropulsionSystemOutSchema.from_queryset(propulsion)
            
            # Thêm dữ liệu từ measurements
            for field in ['motor_power', 'propeller_size', 'battery_capacity', 
                        'flight_time', 'charging_time']:
                m = propulsion.measurements.filter(measurement_type=field).first()
                if m and edit:
                    data[field] = m.get_formatted_value(user_units)
                elif m:
                    data[field] = m.get_converted_data(user_units)
                
            return data
        except PropulsionSystem.DoesNotExist:
            return None
