from devices.models import RadioCommunication, Measurement

class RadioCommunicationService:
    @staticmethod
    def create_or_update(device=None, library=None, data=None):
        """Tạo hoặc cập nhật thông tin liên lạc vô tuyến"""
        try:
            # Thử tìm kiếm trước
            if device:
                radio = RadioCommunication._base_manager.get(device=device)
            elif library:
                radio = RadioCommunication._base_manager.get(library=library)
            
        except RadioCommunication.DoesNotExist:
            # Tạo mới với các trường bắt buộc
            radio = RadioCommunication(
                device=device,
                library=library
            )
        
        radio.save()
        
        # Xử lý measurements
        for field in ['frequency', 'range']:
            if field in data and data[field]:
                radio.set_measurement(field, data[field])
            else:
                radio.measurements.filter(measurement_type=field).delete()
        
        return True, radio

    @staticmethod
    def get_data(device=None, library=None, user_units=None, edit=False):
        """Lấy thông tin hiển thị"""
        try:
            if device:
                radio = device.radio_communication
            elif library:
                radio = library.radio_communication
            
            data = {}
            
            # Lấy dữ liệu từ measurements
            for field in ['frequency', 'range']:
                m = radio.measurements.filter(measurement_type=field).first()
                if m and edit:
                    data[field] = m.get_formatted_value(user_units)
                elif m:
                    data[field] = m.get_converted_data(user_units)
                
            return data
        except RadioCommunication.DoesNotExist:
            return None
