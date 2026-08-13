from devices.models import SafetyFeature

class SafetyFeatureService:
    @staticmethod
    def create_or_update(device=None, library=None, data=None):
        """Tạo hoặc cập nhật thông tin tính năng an toàn"""
        try:
            # Thử tìm kiếm trước
            if device:
                safety = SafetyFeature._base_manager.get(device=device)
            elif library:
                safety = SafetyFeature._base_manager.get(library=library)
            
        except SafetyFeature.DoesNotExist:
            # Tạo mới với các trường bắt buộc và giá trị mặc định
            safety = SafetyFeature(
                device=device,
                library=library,
                dual_imu=data.get('dual_imu', False),
                dual_gps=data.get('dual_gps', False),
                dual_battery=data.get('dual_battery', False),
                emergency_parachute=data.get('emergency_parachute', False),
                return_to_home=data.get('return_to_home', False),
                obstacle_detection_360=data.get('obstacle_detection_360', False),
                stereo_cameras=data.get('stereo_cameras', False),
                lidar_mapping=data.get('lidar_mapping', False),
                emergency_braking=data.get('emergency_braking', False)
            )
        
        # Cập nhật các trường boolean
        boolean_fields = [
            'dual_imu', 'dual_gps', 'dual_battery', 'emergency_parachute',
            'return_to_home', 'obstacle_detection_360', 'stereo_cameras',
            'lidar_mapping', 'emergency_braking'
        ]
        
        for field in boolean_fields:
            setattr(safety, field, data.get(field,False))
                
        safety.save()
        
        return True, safety

    @staticmethod
    def get_data(device=None, library=None, user_units=None, edit=False):
        """Lấy thông tin hiển thị"""
        try:
            if device:
                safety = device.safety_feature
            elif library:
                safety = library.safety_feature
            
            data = {
                'dual_imu': safety.dual_imu,
                'dual_gps': safety.dual_gps,
                'dual_battery': safety.dual_battery,
                'emergency_parachute': safety.emergency_parachute,
                'return_to_home': safety.return_to_home,
                'obstacle_detection_360': safety.obstacle_detection_360,
                'stereo_cameras': safety.stereo_cameras,
                'lidar_mapping': safety.lidar_mapping,
                'emergency_braking': safety.emergency_braking
            }
                
            return data
        except SafetyFeature.DoesNotExist:
            return None
