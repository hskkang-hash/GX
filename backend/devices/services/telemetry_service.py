from devices.models import Telemetry

class TelemetryService:
    @staticmethod
    def create_or_update(device=None, library=None, data=None):
        """Tạo hoặc cập nhật thông tin viễn trắc"""
        try:
            # Thử tìm kiếm trước
            if device:
                telemetry = Telemetry._base_manager.get(device=device)
            elif library:
                telemetry = Telemetry._base_manager.get(library=library)
            
        except Telemetry.DoesNotExist:
            # Tạo mới với các trường bắt buộc
            telemetry = Telemetry(
                device=device,
                library=library,
                realtime_flight_data=data.get('realtime_flight_data', False),
                video_streaming=data.get('video_streaming', False),
                battery_status_monitoring=data.get('battery_status_monitoring', False),
                gps_position_tracking=data.get('gps_position_tracking', False),
                system_health_monitoring=data.get('system_health_monitoring', False)
            )
        
        # Cập nhật các trường boolean
        boolean_fields = [
            'realtime_flight_data', 'video_streaming', 
            'battery_status_monitoring', 'gps_position_tracking',
            'system_health_monitoring'
        ]
        
        for field in boolean_fields:
            setattr(telemetry, field, data.get(field,False))
                
        telemetry.save()
        
        return True, telemetry

    @staticmethod
    def get_data(device=None, library=None, user_units=None, edit=False):
        """Lấy thông tin hiển thị"""
        try:
            if device:
                telemetry = device.telemetry
            elif library:
                telemetry = library.telemetry
            
            data = {
                'realtime_flight_data': telemetry.realtime_flight_data,
                'video_streaming': telemetry.video_streaming,
                'battery_status_monitoring': telemetry.battery_status_monitoring,
                'gps_position_tracking': telemetry.gps_position_tracking,
                'system_health_monitoring': telemetry.system_health_monitoring
            }
                
            return data
        except Telemetry.DoesNotExist:
            return None
