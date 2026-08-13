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
