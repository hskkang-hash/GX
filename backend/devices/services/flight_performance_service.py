from devices.models import FlightPerformance, Measurement
from devices.services.dimensions_service import DimensionsService

class FlightPerformanceService:
    @staticmethod
    def create_or_update(device=None, library=None, data=None):
        """Tạo hoặc cập nhật thông tin hiệu suất bay"""
        try:
            # Thử tìm kiếm trước
            if device:
                flight_performance = FlightPerformance._base_manager.get(device=device)
            elif library:
                flight_performance = FlightPerformance._base_manager.get(library=library)
            
        except FlightPerformance.DoesNotExist:
            # Tạo mới với các trường bắt buộc
            flight_performance = FlightPerformance(
                device=device,
                library=library
            )
        
        flight_performance.save()
        
        # Xử lý các measurements
        measurement_fields = [
            'maximum_speed', 'cruise_speed', 'maximum_altitude',
            'operating_altitude', 'maximum_range', 'wind_resistance'
        ]
        
        for field in measurement_fields:
            if field in data and data[field]:
                flight_performance.set_measurement(field, data[field])
            else:
                flight_performance.measurements.filter(measurement_type=field).delete()
        return True, flight_performance

    @staticmethod
    def get_data(device=None, library=None, user_units=None, edit=False):
        """Lấy thông tin hiển thị với unit conversion"""
        try:
            if device:
                flight_performance = device.flight_performance
            elif library:
                flight_performance = library.flight_performance
            
            data = {}
            # Map measurement types to their default units
            default_units = {
                'maximum_speed': 'km/h',
                'cruise_speed': 'm/s',
                'maximum_altitude': 'm',
                'operating_altitude': 'm',
                'maximum_range': 'km',
                'wind_resistance': 'm/s'
            }
            
            # Get and convert measurements
            for field, default_unit in default_units.items():
                m = flight_performance.measurements.filter(measurement_type=field).first()
                if m and edit:
                    data[field] = m.get_formatted_value(user_units)
                elif m:
                    data[field] = m.get_converted_data(user_units)
                    
            return data if data else None
        except FlightPerformance.DoesNotExist:
            return None
