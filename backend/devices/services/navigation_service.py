from devices.models import NavigationControl, Measurement

class NavigationControlService:
    @staticmethod
    def create_or_update(device=None, library=None, data=None):
        """Tạo hoặc cập nhật thông tin điều khiển và dẫn đường"""
        try:
            print("NAVIGATION DATA",data)
            # Thử tìm kiếm trước
            if device:
                navigation = NavigationControl._base_manager.get(device=device)
            elif library:
                navigation = NavigationControl._base_manager.get(library=library)
            
            # Cập nhật thông tin boolean
            if 'barometric_altimeter' in data:
                navigation.barometric_altimeter = data['barometric_altimeter']
            else:
                navigation.barometric_altimeter = None
        except NavigationControl.DoesNotExist:
            # Tạo mới với các trường bắt buộc
            navigation = NavigationControl(
                device=device,
                library=library,
                barometric_altimeter=data.get('barometric_altimeter', False)
            )
            
        navigation.save()
        
        # Cập nhật measurements
        for field in ['gps_accuracy', 'imu']:
            if field in data and data[field]:
                # Xóa measurement cũ nếu có
                navigation.measurements.filter(measurement_type=field).delete()
                # Tạo measurement mới
                Measurement.create_from_string(navigation, field, data[field])
            else:
                navigation.measurements.filter(measurement_type=field).delete()
        return True, navigation

    @staticmethod
    def get_data(device=None, library=None, user_units=None, edit=False):
        """Lấy thông tin hiển thị"""
        try:
            if device:
                navigation = device.navigation_control
            elif library:
                navigation = library.navigation_control
            print("NAVIGATION DATA",navigation)
            data = {
                'barometric_altimeter': navigation.barometric_altimeter,
            }
            # Lấy dữ liệu từ measurements
            print("NAVIGATION DATA",navigation.measurements.all())
            for field in ['gps_accuracy', 'imu']:
                m = navigation.measurements.filter(measurement_type=field).first()           
                if m and edit:
                    data[field] = m.get_formatted_value(user_units)
                elif m:
                    data[field] = m.get_converted_data(user_units)
            return data
        except NavigationControl.DoesNotExist:
            return None
