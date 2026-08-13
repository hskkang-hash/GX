from django.test import TestCase
from django.core.exceptions import ValidationError
from devices.models import (
    Device, DimensionsAndWeight, PropulsionSystem, FlightPerformance,
    NavigationControl, RadioCommunication, Telemetry, SensorSuite,
    Camera, CargoCompartments, PackagingSpecification,
    ManufacturerInformation, InsuranceInformation,
    EnvironmentalSpecification, SafetyFeature, Protocol, DeviceProtocol
)
from devices.services.devices_service import DeviceService
from devices.services.dimensions_service import DimensionsService
from devices.services.telemetry_service import TelemetryService
from devices.services.safety_service import SafetyFeatureService
from devices.services.camera_service import CameraService
from devices.services.flight_performance_service import FlightPerformanceService

class DeviceServicesTestCase(TestCase):
    def setUp(self):
        # Tạo device cơ bản cho test
        self.device_data = {
            'name': 'Test Drone',
            'model': 'TD-1000',
            'serial_number': 'TD1000-001',
            'status': 'active'
        }
        self.device = Device.objects.create(**self.device_data)

    def test_device_creation(self):
        """Test tạo thiết bị mới"""
        data = {
            'name': 'New Drone',
            'model': 'ND-2000',
            'serial_number': 'ND2000-001',
            'status': 'active'
        }
        device = DeviceService.create(data, None)
        self.assertIsNotNone(device)
        self.assertEqual(device.name, 'New Drone')

    def test_device_creation_missing_required(self):
        """Test tạo thiết bị thiếu thông tin bắt buộc"""
        data = {
            'name': 'New Drone',
            # Thiếu model và serial_number
        }
        with self.assertRaises(ValidationError):
            DeviceService.create(data, None)

    def test_dimensions_service(self):
        """Test service dimensions"""
        data = {
            'frame_size': '50 cm',
            'maximum_takeoff_weight': '2.5 kg',
            'payload_capacity': '1 kg',
            'empty_weight': '1.5 kg'
        }
        success, dimensions = DimensionsService.create_or_update(self.device, data)
        self.assertTrue(success)
        self.assertIsNotNone(dimensions)
        
        # Kiểm tra các measurement được tạo
        self.assertEqual(dimensions.get_measurement('frame_size').get_value(), 50)
        self.assertEqual(dimensions.get_measurement('maximum_takeoff_weight').get_value(), 2.5)

    def test_telemetry_service(self):
        """Test service telemetry"""
        data = {
            'realtime_flight_data': True,
            'video_streaming': True,
            'battery_status_monitoring': True,
            'gps_position_tracking': True,
            'system_health_monitoring': True
        }
        success, telemetry = TelemetryService.create_or_update(self.device, data)
        self.assertTrue(success)
        self.assertTrue(telemetry.realtime_flight_data)
        self.assertTrue(telemetry.video_streaming)

    def test_safety_features(self):
        """Test service safety features"""
        data = {
            'dual_imu': True,
            'dual_gps': True,
            'dual_battery': True,
            'emergency_parachute': True,
            'return_to_home': True
        }
        success, safety = SafetyFeatureService.create_or_update(self.device, data)
        self.assertTrue(success)
        self.assertTrue(safety.dual_imu)
        self.assertTrue(safety.emergency_parachute)

    def test_camera_service(self):
        """Test service camera"""
        data = {
            'name': 'Main Camera',
            'model': 'CAM-4K',
            'type': 'RGB',
            'resolution': '4K',
            'field_of_view': '120°',
            'night_vision': True
        }
        success, camera = CameraService.create_or_update(data)
        self.assertTrue(success)
        self.assertEqual(camera.name, 'Main Camera')
        self.assertTrue(camera.night_vision)

    def test_flight_performance(self):
        """Test service flight performance"""
        data = {
            'maximum_speed': '100 km/h',
            'cruise_speed': '60 km/h',
            'maximum_altitude': '500 m',
            'operating_altitude': '300 m',
            'maximum_range': '10 km',
            'wind_resistance': '12 m/s'
        }
        success, performance = FlightPerformanceService.create_or_update(self.device, data)
        self.assertTrue(success)
        self.assertIsNotNone(performance.get_measurement('maximum_speed'))
        self.assertIsNotNone(performance.get_measurement('maximum_altitude'))

    def test_invalid_measurement_values(self):
        """Test xử lý giá trị measurement không hợp lệ"""
        data = {
            'frame_size': 'invalid value',
            'maximum_takeoff_weight': 'abc kg'
        }
        success, dimensions = DimensionsService.create_or_update(self.device, data)
        self.assertFalse(success)

    def test_update_existing_device(self):
        """Test cập nhật thiết bị đã tồn tại"""
        # Tạo các thông tin ban đầu
        initial_data = {
            'frame_size': '50 cm',
            'maximum_takeoff_weight': '2.5 kg'
        }
        DimensionsService.create_or_update(self.device, initial_data)

        # Cập nhật thông tin
        update_data = {
            'frame_size': '55 cm',
            'maximum_takeoff_weight': '3 kg'
        }
        success, dimensions = DimensionsService.create_or_update(self.device, update_data)
        self.assertTrue(success)
        self.assertEqual(dimensions.get_measurement('frame_size').get_value(), 55)

    def test_complete_device_workflow(self):
        """Test quy trình hoàn chỉnh tạo thiết bị với đầy đủ thông tin"""
        device_data = {
            'name': 'Complete Drone',
            'model': 'CD-3000',
            'serial_number': 'CD3000-001',
            'status': 'active',
            'dimensions_and_weight': {
                'frame_size': '60 cm',
                'maximum_takeoff_weight': '3 kg'
            },
            'telemetry': {
                'realtime_flight_data': True,
                'video_streaming': True
            },
            'safety_feature': {
                'dual_imu': True,
                'emergency_parachute': True
            },
            'flight_performance': {
                'maximum_speed': '120 km/h',
                'maximum_altitude': '600 m'
            }
        }
        
        device = DeviceService.create(device_data, None)
        self.assertIsNotNone(device)
        self.assertEqual(device.name, 'Complete Drone')
        
        # Verify all components
        self.assertIsNotNone(device.dimensions_and_weight)
        self.assertIsNotNone(device.telemetry)
        self.assertIsNotNone(device.safety_feature)
        self.assertIsNotNone(device.flight_performance)
from django.core.exceptions import ValidationError
from devices.utils import (
    parse_measurement_string, parse_range, parse_up_to,
    parse_error_margin, parse_multi_value, parse_resolution,
    parse_not_exceeding
)

from django.test import TestCase
from django.core.exceptions import ValidationError
from devices.utils import (
    parse_measurement_string, parse_range, parse_up_to,
    parse_error_margin, parse_multi_value, parse_resolution,
    parse_not_exceeding
)

class MeasurementParsingTestCase(TestCase):
    def test_simple_measurement(self):
        """Test parse giá trị đơn giản với đơn vị"""
        test_cases = [
            # Số nguyên cơ bản
            ("50 cm", {'value': 50, 'unit': 'cm'}),
            ("2.5 kg", {'value': 2.5, 'unit': 'kg'}),
            ("100 km/h", {'value': 100, 'unit': 'km/h'}),
            
            # Số thập phân
            ("0.001 mm", {'value': 0.001, 'unit': 'mm'}),
            ("1.23456 m", {'value': 1.23456, 'unit': 'm'}),
            (".5 kg", {'value': 0.5, 'unit': 'kg'}),
            
            # Số âm
            ("-40 °C", {'value': -40, 'unit': '°C'}),
            ("-273.15 K", {'value': -273.15, 'unit': 'K'}),
            ("-0.5 m/s", {'value': -0.5, 'unit': 'm/s'}),
            
            # Số có dấu phẩy hàng nghìn
            ("1,000 mAh", {'value': 1000, 'unit': 'mAh'}),
            ("1,234,567.89 W", {'value': 1234567.89, 'unit': 'W'}),
            ("10,000,000 Hz", {'value': 10000000, 'unit': 'Hz'}),
            
            # Đơn vị đặc biệt
            ("45°", {'value': 45, 'unit': '°'}),
            ("75%", {'value': 75, 'unit': '%'}),
            ("9.81 m/s²", {'value': 9.81, 'unit': 'm/s²'}),
            ("1 µm", {'value': 1, 'unit': 'µm'}),
            ("100 Ω", {'value': 100, 'unit': 'Ω'}),
            ("5 µA", {'value': 5, 'unit': 'µA'}),
            
            # Khoảng trắng và định dạng
            ("100    km/h", {'value': 100, 'unit': 'km/h'}),
            ("50\tkm", {'value': 50, 'unit': 'km'}),
            ("30\n\rm", {'value': 30, 'unit': 'm'}),
            
            # Đơn vị phức tạp
            ("100 km/h²", {'value': 100, 'unit': 'km/h²'}),
            ("20 mA/cm²", {'value': 20, 'unit': 'mA/cm²'}),
            ("5 kN·m", {'value': 5, 'unit': 'kN·m'}),
            ("3 kg·m/s²", {'value': 3, 'unit': 'kg·m/s²'}),
            
            # Số cực lớn/nhỏ
            ("1e-6 m", {'value': 0.000001, 'unit': 'm'}),
            ("1e6 Hz", {'value': 1000000, 'unit': 'Hz'}),
            ("1.23e-9 m", {'value': 1.23e-9, 'unit': 'm'}),
        ]
        
        for input_str, expected in test_cases:
            result = parse_measurement_string(input_str)
            self.assertEqual(result, expected, f"Failed to parse: {input_str}")

    def test_range_values(self):
        """Test parse các giá trị dạng khoảng"""
        test_cases = [
            # Dạng cơ bản
            ("10-20 km", {'min': 10, 'max': 20, 'unit': 'km'}),
            ("2.5-3.5 kg", {'min': 2.5, 'max': 3.5, 'unit': 'kg'}),
            
            # Dạng từ ... đến ...
            ("from 10 to 20 km", {'min': 10, 'max': 20, 'unit': 'km'}),
            ("from -10 through 50 °C", {'min': -10, 'max': 50, 'unit': '°C'}),
            ("from 0.5 thru 1.5 A", {'min': 0.5, 'max': 1.5, 'unit': 'A'}),
            
            # Số âm
            ("-10-50 °C", {'min': -10, 'max': 50, 'unit': '°C'}),
            ("-40--20 °C", {'min': -40, 'max': -20, 'unit': '°C'}),
            ("from -273.15 to -50 K", {'min': -273.15, 'max': -50, 'unit': 'K'}),
            
            # Số có dấu phẩy
            ("1,000-2,000 mAh", {'min': 1000, 'max': 2000, 'unit': 'mAh'}),
            ("1,000,000-2,000,000 Hz", {'min': 1000000, 'max': 2000000, 'unit': 'Hz'}),
            
            # Đơn vị đặc biệt
            ("0-100%", {'min': 0, 'max': 100, 'unit': '%'}),
            ("0°-360°", {'min': 0, 'max': 360, 'unit': '°'}),
            ("10µA-100mA", {'min': 10, 'max': 100, 'unit': 'µA-mA'}),
            
            # Khoảng trắng không đều
            ("10    -    20 km", {'min': 10, 'max': 20, 'unit': 'km'}),
            ("5\t-\t10 m", {'min': 5, 'max': 10, 'unit': 'm'}),
            
            # Đơn vị phức tạp
            ("10-20 km/h²", {'min': 10, 'max': 20, 'unit': 'km/h²'}),
            ("0.5-1.5 kg·m/s²", {'min': 0.5, 'max': 1.5, 'unit': 'kg·m/s²'}),
            
            # Với qualifier
            ("10-20 °C non-condensing", {'min': 10, 'max': 20, 'unit': '°C', 'qualifier': 'non-condensing'}),
            ("20-80% RH", {'min': 20, 'max': 80, 'unit': '%', 'qualifier': 'RH'}),
        ]
        
        for input_str, expected in test_cases:
            result = parse_range(input_str)
            self.assertEqual(result, expected, f"Failed to parse range: {input_str}")

    def test_up_to_values(self):
        """Test parse các giá trị dạng 'up to'"""
        test_cases = [
            # Dạng cơ bản
            ("up to 100 km/h", {'max': 100, 'unit': 'km/h'}),
            ("up to 1,000 m", {'max': 1000, 'unit': 'm'}),
            
            # Các biến thể của "up to"
            ("maximum 50 kg", {'max': 50, 'unit': 'kg'}),
            ("max. 100 m", {'max': 100, 'unit': 'm'}),
            ("up to a maximum of 200 W", {'max': 200, 'unit': 'W'}),
            
            # Số thập phân
            ("up to 5.5 kg", {'max': 5.5, 'unit': 'kg'}),
            ("maximum 0.001 mm", {'max': 0.001, 'unit': 'mm'}),
            
            # Số có dấu phẩy
            ("up to 1,000,000 Hz", {'max': 1000000, 'unit': 'Hz'}),
            ("maximum 10,000 rpm", {'max': 10000, 'unit': 'rpm'}),
            
            # Đơn vị đặc biệt
            ("up to 90%", {'max': 90, 'unit': '%'}),
            ("maximum 360°", {'max': 360, 'unit': '°'}),
            ("up to 100 µA", {'max': 100, 'unit': 'µA'}),
            
            # Khoảng trắng không đều
            ("up    to    100 km", {'max': 100, 'unit': 'km'}),
            ("maximum\t50\tm", {'max': 50, 'unit': 'm'}),
            
            # Với qualifier
            ("up to 80% RH", {'max': 80, 'unit': '%', 'qualifier': 'RH'}),
            ("maximum 40°C non-condensing", {'max': 40, 'unit': '°C', 'qualifier': 'non-condensing'}),
        ]
        
        for input_str, expected in test_cases:
            result = parse_up_to(input_str)
            self.assertEqual(result, expected, f"Failed to parse up to: {input_str}")

    def test_not_exceeding_values(self):
        """Test parse các giá trị dạng 'not exceeding'"""
        test_cases = [
            # Dạng cơ bản
            ("not exceeding 50 kg", {'max': 50, 'unit': 'kg'}),
            ("less than 100 m", {'max': 100, 'unit': 'm'}),
            
            # Các biến thể
            ("below 30 km/h", {'max': 30, 'unit': 'km/h'}),
            ("not more than 200 W", {'max': 200, 'unit': 'W'}),
            ("no more than 500 mA", {'max': 500, 'unit': 'mA'}),
            
            # Số thập phân
            ("not exceeding 1.5 m", {'max': 1.5, 'unit': 'm'}),
            ("less than 0.001 mm", {'max': 0.001, 'unit': 'mm'}),
            
            # Số có dấu phẩy
            ("not exceeding 1,000,000 Hz", {'max': 1000000, 'unit': 'Hz'}),
            ("less than 10,000 rpm", {'max': 10000, 'unit': 'rpm'}),
            
            # Đơn vị đặc biệt
            ("not exceeding 90%", {'max': 90, 'unit': '%'}),
            ("less than 360°", {'max': 360, 'unit': '°'}),
            ("below 100 µA", {'max': 100, 'unit': 'µA'}),
            
            # Khoảng trắng không đều
            ("not    exceeding    100 km", {'max': 100, 'unit': 'km'}),
            ("less\tthan\t50\tm", {'max': 50, 'unit': 'm'}),
            
            # Với qualifier
            ("not exceeding 80% RH", {'max': 80, 'unit': '%', 'qualifier': 'RH'}),
            ("less than 40°C non-condensing", {'max': 40, 'unit': '°C', 'qualifier': 'non-condensing'}),
        ]
        
        for input_str, expected in test_cases:
            result = parse_not_exceeding(input_str)
            self.assertEqual(result, expected, f"Failed to parse not exceeding: {input_str}")

    def test_error_margin_values(self):
        """Test parse các giá trị có sai số"""
        test_cases = [
            # Dạng cơ bản
            ("±1.5m", {'value': 0, 'margin': 1.5, 'unit': 'm'}),
            ("±2.0kg", {'value': 0, 'margin': 2.0, 'unit': 'kg'}),
            
            # Số nguyên
            ("±5 cm", {'value': 0, 'margin': 5, 'unit': 'cm'}),
            ("±100 Hz", {'value': 0, 'margin': 100, 'unit': 'Hz'}),
            
            # Số thập phân nhỏ
            ("±0.001 mm", {'value': 0, 'margin': 0.001, 'unit': 'mm'}),
            ("±0.0001 µm", {'value': 0, 'margin': 0.0001, 'unit': 'µm'}),
            
            # Đơn vị đặc biệt
            ("±0.5°", {'value': 0, 'margin': 0.5, 'unit': '°'}),
            ("±10%", {'value': 0, 'margin': 10, 'unit': '%'}),
            ("±5 µA", {'value': 0, 'margin': 5, 'unit': 'µA'}),
            
            # Khoảng trắng
            ("± 1.5 m", {'value': 0, 'margin': 1.5, 'unit': 'm'}),
            ("±\t2.0\tkg", {'value': 0, 'margin': 2.0, 'unit': 'kg'}),
            
            # Với giá trị trung tâm
            ("10 ±0.5 m", {'value': 10, 'margin': 0.5, 'unit': 'm'}),
            ("100 ± 5 Hz", {'value': 100, 'margin': 5, 'unit': 'Hz'}),
            
            # Đơn vị phức tạp
            ("±2 km/h", {'value': 0, 'margin': 2, 'unit': 'km/h'}),
            ("±0.5 kg·m/s²", {'value': 0, 'margin': 0.5, 'unit': 'kg·m/s²'}),
        ]
        
        for input_str, expected in test_cases:
            result = parse_error_margin(input_str)
            self.assertEqual(result, expected, f"Failed to parse error margin: {input_str}")

    def test_multi_value_measurements(self):
        """Test parse các giá trị nhiều thành phần"""
        test_cases = [
            # Dạng phân cách bằng dấu phẩy
            ("10, 20, 30 cm", {'values': [10, 20, 30], 'unit': 'cm'}),
            ("1.5, 2.5, 3.5 kg", {'values': [1.5, 2.5, 3.5], 'unit': 'kg'}),
            
            # Dạng "and"
            ("10 and 20 km", {'values': [10, 20], 'unit': 'km'}),
            ("2.4GHz and 5.8GHz", {'values': [2.4, 5.8], 'unit': 'GHz'}),
            
            # Số thập phân
            ("0.1, 0.2, 0.3 mm", {'values': [0.1, 0.2, 0.3], 'unit': 'mm'}),
            ("1.23, 4.56, 7.89 m", {'values': [1.23, 4.56, 7.89], 'unit': 'm'}),
            
            # Số có dấu phẩy hàng nghìn
            ("1,000, 2,000, 3,000 Hz", {'values': [1000, 2000, 3000], 'unit': 'Hz'}),
            ("10,000 and 20,000 rpm", {'values': [10000, 20000], 'unit': 'rpm'}),
            
            # Dạng kích thước
            ("100x200x300 mm", {'values': [100, 200, 300], 'unit': 'mm'}),
            ("5 x 10 x 15 cm", {'values': [5, 10, 15], 'unit': 'cm'}),
            ("2.5x3.5x4.5 m", {'values': [2.5, 3.5, 4.5], 'unit': 'm'}),
            
            # Đơn vị đặc biệt
            ("45°, 90°, 180°", {'values': [45, 90, 180], 'unit': '°'}),
            ("10%, 20%, 30%", {'values': [10, 20, 30], 'unit': '%'}),
            
            # Khoảng trắng không đều
            ("10    ,    20    ,    30 km", {'values': [10, 20, 30], 'unit': 'km'}),
            ("5\tx\t10\tx\t15 m", {'values': [5, 10, 15], 'unit': 'm'}),
            
            # Đơn vị phức tạp
            ("10, 20, 30 km/h", {'values': [10, 20, 30], 'unit': 'km/h'}),
            ("1.5, 2.5 kg·m/s²", {'values': [1.5, 2.5], 'unit': 'kg·m/s²'}),
        ]
        
        for input_str, expected in test_cases:
            result = parse_multi_value(input_str)
            self.assertEqual(result, expected, f"Failed to parse multi value: {input_str}")


    def test_complex_unit_measurements(self):
        """Test parse các giá trị với đơn vị phức tạp"""
        test_cases = [
            # Moment và lực
            ("50 N·m", {'value': 50, 'unit': 'N·m'}),
            ("25 kN·m", {'value': 25, 'unit': 'kN·m'}),
            ("2.5 N/mm²", {'value': 2.5, 'unit': 'N/mm²'}),
            
            # Năng lượng và công suất
            ("1000 W·h", {'value': 1000, 'unit': 'W·h'}),
            ("2.5 kW·h", {'value': 2.5, 'unit': 'kW·h'}),
            ("100 J/kg·K", {'value': 100, 'unit': 'J/kg·K'}),
            
            # Áp suất và mật độ
            ("1.013 kg/m³", {'value': 1.013, 'unit': 'kg/m³'}),
            ("100 Pa·s", {'value': 100, 'unit': 'Pa·s'}),
            
            # Điện và từ
            ("10 V/m", {'value': 10, 'unit': 'V/m'}),
            ("0.5 A/m²", {'value': 0.5, 'unit': 'A/m²'}),
            ("1.5 Wb/m²", {'value': 1.5, 'unit': 'Wb/m²'}),
            
            # Tần số và sóng
            ("2.4 GHz", {'value': 2.4, 'unit': 'GHz'}),
            ("300 MHz/s", {'value': 300, 'unit': 'MHz/s'}),
            
            # Nhiệt độ và nhiệt dung
            ("4.18 kJ/kg·K", {'value': 4.18, 'unit': 'kJ/kg·K'}),
            ("0.5 W/m·K", {'value': 0.5, 'unit': 'W/m·K'}),
            
            # Độ nhớt và lưu lượng
            ("1.5 m³/s", {'value': 1.5, 'unit': 'm³/s'}),
            ("20 kg/m·s", {'value': 20, 'unit': 'kg/m·s'}),
            
            # Đơn vị quang học
            ("100 cd/m²", {'value': 100, 'unit': 'cd/m²'}),
            ("1000 lm/W", {'value': 1000, 'unit': 'lm/W'})
        ]
        
        for input_str, expected in test_cases:
            result = parse_measurement_string(input_str)
            self.assertEqual(result, expected, f"Failed to parse complex unit: {input_str}")

    def test_complex_unit_ranges(self):
        """Test parse các khoảng giá trị với đơn vị phức tạp"""
        test_cases = [
            # Moment và lực
            ("20-50 N·m", {'min': 20, 'max': 50, 'unit': 'N·m'}),
            ("10-25 kN·m", {'min': 10, 'max': 25, 'unit': 'kN·m'}),
            
            # Năng lượng và công suất
            ("500-1000 W·h", {'min': 500, 'max': 1000, 'unit': 'W·h'}),
            ("1.5-2.5 kW·h", {'min': 1.5, 'max': 2.5, 'unit': 'kW·h'}),
            
            # Áp suất và mật độ
            ("1.0-1.5 kg/m³", {'min': 1.0, 'max': 1.5, 'unit': 'kg/m³'}),
            ("50-150 Pa·s", {'min': 50, 'max': 150, 'unit': 'Pa·s'}),
            
            # Điện và từ
            ("5-15 V/m", {'min': 5, 'max': 15, 'unit': 'V/m'}),
            ("0.2-0.8 A/m²", {'min': 0.2, 'max': 0.8, 'unit': 'A/m²'})
        ]
        
        for input_str, expected in test_cases:
            result = parse_range(input_str)
            self.assertEqual(result, expected, f"Failed to parse complex unit range: {input_str}")

    def test_complex_unit_error_margins(self):
        """Test parse các giá trị sai số với đơn vị phức tạp"""
        test_cases = [
            # Moment và lực
            ("30 ±5 N·m", {'value': 30, 'margin': 5, 'unit': 'N·m'}),
            ("15 ±2.5 kN·m", {'value': 15, 'margin': 2.5, 'unit': 'kN·m'}),
            
            # Năng lượng và công suất
            ("750 ±50 W·h", {'value': 750, 'margin': 50, 'unit': 'W·h'}),
            ("2.0 ±0.2 kW·h", {'value': 2.0, 'margin': 0.2, 'unit': 'kW·h'}),
            
            # Áp suất và mật độ
            ("1.2 ±0.1 kg/m³", {'value': 1.2, 'margin': 0.1, 'unit': 'kg/m³'}),
            ("100 ±10 Pa·s", {'value': 100, 'margin': 10, 'unit': 'Pa·s'})
        ]
        
        for input_str, expected in test_cases:
            result = parse_error_margin(input_str)
            self.assertEqual(result, expected, f"Failed to parse complex unit error margin: {input_str}") 