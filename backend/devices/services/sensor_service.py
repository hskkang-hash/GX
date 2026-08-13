from devices.schemas.schemas_djantic_out import GNSSSystemOutSchema, SensorSuiteOutSchema
from devices.models import DeviceGNSS, GNSSSystem, SensorSuite

class SensorSuiteService:
    @staticmethod
    def create_or_update(device=None, library=None, data=None):
        """Tạo hoặc cập nhật thông tin bộ cảm biến"""
        try:
            # Thử tìm kiếm trước
            if device:
                sensor = SensorSuite._base_manager.get(device=device)
            elif library:
                sensor = SensorSuite._base_manager.get(library=library)
            
        except SensorSuite.DoesNotExist:
            # Tạo mới với các trường bắt buộc
            sensor = SensorSuite(device=device, library=library)
        # Cập nhật thông tin text
        if 'gnss' in data:
            if device:
                device.device_gnss.all().delete()
                gnss = GNSSSystem.objects.filter(id__in=data['gnss'])
                for g in gnss:
                    DeviceGNSS.objects.get_or_create(device=device, gnss=g)
            elif library:
                library.library_gnss.all().delete()
                gnss = GNSSSystem.objects.filter(id__in=data['gnss'])
                for g in gnss:
                    DeviceGNSS.objects.get_or_create(library=library, gnss=g)
        else:
            if device:
                device.device_gnss.all().delete()
            elif library:
                library.library_gnss.all().delete()
        # Cập nhật các trường boolean
        boolean_fields = [
            'optical_flow_sensor', 'ultrasonic_sensors', 'lidar', 'ais', 
            'ads_b_receiver', 'rf_signal_detector', 'chemical_sensor_array',
            'radiation_detector', 'weather_sensors'
        ]
        
        for field in boolean_fields:
            setattr(sensor, field, data.get(field,False))
                
        sensor.save()
        
        return True, sensor

    @staticmethod
    def get_data(device=None, library=None, user_units=None, edit=False):
        """Lấy thông tin hiển thị"""
        try:
            if device:
                sensor = device.sensor_suite
                data = SensorSuiteOutSchema.from_queryset(sensor)
                gnss = device.device_gnss.all().values_list('gnss_id', flat=True)
                data['gnss'] = GNSSSystemOutSchema.from_queryset(GNSSSystem.objects.filter(id__in=gnss), many=True, auto_resolve_fields=False)
            elif library:
                sensor = library.sensor_suite
                data = SensorSuiteOutSchema.from_queryset(sensor)
                gnss = library.library_gnss.all().values_list('gnss_id', flat=True)
                data['gnss'] = GNSSSystemOutSchema.from_queryset(GNSSSystem.objects.filter(id__in=gnss), many=True, auto_resolve_fields=False)
            
            return data
        except SensorSuite.DoesNotExist:
            return None
