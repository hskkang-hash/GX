from devices.schemas.schemas_djantic_out import CameraOutSchema
from devices.models import CameraType, Measurement, DeviceCamera
from devices.utils import convert_measurement_data_to_user_units

class CameraService:
    @staticmethod
    def create_or_update(camera_data):
        """Tạo hoặc cập nhật camera"""
        camera_id = camera_data.get('id')
        if camera_id:
            camera = CameraType._base_manager.get(id=camera_id)
        else:
            camera = CameraType()
            
        # Cập nhật thông tin cơ bản
        for field in ['name', 'model', 'type', 'status', 'night_vision', 'thermal_imaging', 'note', 'image_stabilization_id']:
            setattr(camera, field, camera_data.get(field,None))
        
        camera.save()
        
        # Cập nhật measurements
        for field in ['resolution', 'field_of_view', 'frame_rate', 'weight', 'zoom_capability']:
            if field in camera_data and camera_data[field]:
                Measurement.create_from_string(camera, field, camera_data[field])
            else:
                camera.measurements.filter(measurement_type=field).delete()
        return True, camera
    
    @staticmethod
    def add_to_device(device, camera, position, enabled=True, config=None):
        """Thêm camera vào thiết bị"""
        if not config:
            config = {}
            
        # Kiểm tra xem camera đã gắn vào device chưa
        device_camera, created = DeviceCamera.objects.get_or_create(
            device=device,
            camera=camera,
            defaults={
                'position': position,
                'enabled': enabled,
                'config': config
            }
        )
        
        if not created:
            device_camera.position = position
            device_camera.enabled = enabled
            device_camera.config = config
            device_camera.save()
            
        return device_camera
        
    @staticmethod
    def get_data(camera, user_units=None, edit=False):
        """Lấy thông tin hiển thị của camera"""
        data = CameraOutSchema.from_queryset(camera)
        
        # Thêm dữ liệu từ measurements
        for field in ['resolution', 'field_of_view', 'frame_rate', 'weight', 'zoom_capability']:
            m = camera.measurements.filter(measurement_type=field).first()
            if m and edit:
                data[field] = m.get_formatted_value(user_units)
            elif m:
                data[field] = m.get_converted_data(user_units)
            
        return data
    
    @staticmethod
    def get_device_cameras(device, user_units=None):
        """Lấy danh sách camera của thiết bị"""
        device_cameras = device.device_cameras.all()
        
        result = []
        for dc in device_cameras:
            camera_data = CameraService.get_data(dc.camera, user_units)
            camera_data.update({
                'position': dc.position,
                'enabled': dc.enabled,
                'config': dc.config
            })
            result.append(camera_data)
            
        return result
