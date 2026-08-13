"""
Schemas đầu vào (IN) sử dụng django-ninja Schema
Chỉ chứa các schemas cho dữ liệu đầu vào từ requests
"""

from ninja import ModelSchema, Schema, Schema
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from devices.models import (
    Device, DimensionsAndWeight, PropulsionSystem, FlightPerformance, 
    NavigationControl, RadioCommunication, Telemetry, SensorSuite, 
     CargoCompartments, PackagingSpecification, PackagingOption, PackagingOptionSpecification,
    ManufacturerInformation, InsuranceInformation, 
    EnvironmentalSpecification, SafetyFeature, DeviceProtocol, Protocol,
    MotorType, BatteryType, IMU, ImageStabilization, GNSSSystem, PackageType,
    DeviceCamera
)

# Schemas cho measurements
class MeasurementValueSchema(Schema):
    """Schema cho giá trị measurement đơn giản"""
    value: Optional[Any] = None
    unit: Optional[str] = None

class MeasurementRangeSchema(Schema):
    """Schema cho giá trị measurement dạng phạm vi"""
    min: Optional[Any] = None
    max: Optional[Any] = None
    unit: Optional[str] = None

class MeasurementDimensionsSchema(Schema):
    """Schema cho giá trị measurement dạng kích thước"""
    length: Optional[Any] = None
    width: Optional[Any] = None
    height: Optional[Any] = None
    unit: Optional[str] = None

# Schemas đầu vào cho các thành phần kế thừa từ MeasurableModel
class DimensionsWeightInSchema(Schema):
    """Schema cho DimensionsAndWeight với các trường measurement riêng biệt"""
    # Các trường measurement được định nghĩa trực tiếp thay vì sử dụng model_fields
    frame_size: Optional[str] = None  # Chuỗi giá trị như "100 x 50 x 30 mm"
    maximum_takeoff_weight: Optional[str] = None  # Chuỗi giá trị như "5 kg"
    payload_capacity: Optional[str] = None  # Chuỗi giá trị như "2 kg"
    empty_weight: Optional[str] = None  # Chuỗi giá trị như "3 kg"
    frame_class_id: Optional[int] = None
    frame_type_id: Optional[int] = None
    
class PropulsionSystemInSchema(Schema):
    """Schema cho PropulsionSystem với các trường model thực và measurement"""
    # Các trường model thực 
    number_of_motors: Optional[int] = None
    motor_type_id: Optional[int] = None
    battery_type_id: Optional[int] = None
    flight_time: Optional[str] = None
    charging_time: Optional[str] = None
    
    # Các trường measurement
    motor_power: Optional[str] = None  # Ví dụ: "2.5 kW"
    propeller_size: Optional[str] = None  # Ví dụ: "10 inch"
    battery_capacity: Optional[str] = None  # Ví dụ: "5000 mAh"
        
class FlightPerformanceInSchema(Schema):
    """Schema cho FlightPerformance với các trường measurement riêng biệt"""
    maximum_speed: Optional[str] = None
    cruise_speed: Optional[str] = None
    maximum_altitude: Optional[str] = None
    operating_altitude: Optional[str] = None
    maximum_range: Optional[str] = None
    wind_resistance: Optional[str] = None
        
class NavigationControlInSchema(Schema):
    """Schema cho NavigationControl với các trường model thực và measurement"""
    # Trường model thực
    barometric_altimeter: Optional[bool] = None
    imu: Optional[str] = None
    
    # Trường measurement
    gps_accuracy: Optional[str] = None
        
class RadioCommunicationInSchema(Schema):
    """Schema cho RadioCommunication với các trường measurement riêng biệt"""
    frequency: Optional[str] = None
    range: Optional[str] = None
        
class SensorSuiteInSchema(ModelSchema):
    """Schema cho SensorSuite - chủ yếu là boolean flags nên không cần xử lý đặc biệt"""
    gnss: Optional[List[int]] = None
    class Config:
        model = SensorSuite
        model_exclude = ['id', 'device']
        
class CameraInSchema(Schema):
    """Schema cho Camera với các trường model thực và measurement"""
    # Các trường model thực
    name: Optional[str] = None
    image_stabilization_id: Optional[int] = None
    night_vision: Optional[bool] = None
    thermal_imaging: Optional[bool] = None
    status: Optional[str] = None
    note: Optional[str] = None
    # Các trường measurement
    resolution: Optional[str] = None
    field_of_view: Optional[str] = None
    frame_rate: Optional[str] = None
    weight: Optional[str] = None
    zoom_capability: Optional[str] = None
        
class CargoCompartmentsInSchema(Schema):
    """Schema cho CargoCompartments với các trường model thực và measurement"""
    # Các trường model thực
    compartment_number: int
    name: str
    secure_locking: bool
    quick_release: bool
    temperature_control: bool
    status: str
    
    # Các trường measurement
    dimensions: Optional[str] = None  # Ví dụ: "500 x 300 x 200 mm"
    weight_capacity: Optional[str] = None  # Ví dụ: "10 kg"
    
        
class PackagingSpecificationDevice(Schema):
    """Schema cho PackagingSpecification với các trường model thực và measurement"""
    # Trường model thực
    package: Optional[int] = None

class PackagingOptionSpecificationInSchema(Schema):
    """Schema cho PackagingOptionSpecification"""
    package: int
    
class PackagingOptionInSchema(Schema):
    """Schema cho PackagingOption"""
    name: Optional[str] = None
    order: Optional[int] = 1
    specifications: Optional[List[int]] = None

class ManufacturerInformationInSchema(Schema):
    """Schema cho ManufacturerInformation - không có measurement cần xử lý riêng"""
    manufacturer: Optional[str] = None
    country_of_origin_id: Optional[int] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    production_date: Optional[str] = None
    note: Optional[str] = None
    insurance_type: Optional[str] = None
    insurance_provider: Optional[str] = None
    policy_number: Optional[str] = None
    validity_period_from: Optional[datetime] = None
    validity_period_to: Optional[datetime] = None
    current_status: Optional[str] = None
    registration_number: Optional[str] = None
        
class InsuranceInformationInSchema(ModelSchema):
    """Schema cho InsuranceInformation - không có measurement cần xử lý riêng"""
    class Config:
        model = InsuranceInformation
        model_exclude = ['id', 'device']
        
class EnvironmentalSpecificationInSchema(Schema):
    """Schema cho EnvironmentalSpecification với các trường measurement riêng biệt"""
    temperature_range: Optional[str] = None
    humidity: Optional[str] = None
    precipitation: Optional[str] = None
    wind_speed: Optional[str] = None
    noise_takeoff: Optional[str] = None
    noise_cruise: Optional[str] = None
    noise_landing: Optional[str] = None
        
class SafetyFeatureInSchema(ModelSchema):
    """Schema cho SafetyFeature - không có measurement cần xử lý riêng"""
    class Config:
        model = SafetyFeature
        model_exclude = ['id', 'device'] 

class DeviceProtocolInSchema(ModelSchema):
    """Schema cho DeviceProtocol - không có measurement cần xử lý riêng"""
    class Config:
        model = DeviceProtocol
        model_exclude = ['id', 'device']

class ProtocolInSchema(ModelSchema):
    """Schema cho Protocol - không có measurement cần xử lý riêng"""
    class Config:
        model = Protocol
        model_exclude = ['id']

class TelemetryInSchema(ModelSchema):
    """Schema cho Telemetry - không có measurement cần xử lý riêng"""
    class Config:
        model = Telemetry
        model_exclude = ['id', 'device']


class MotorTypeInSchema(ModelSchema):
    """Schema cho MotorType - không có measurement cần xử lý riêng"""
    name: str
    description: Optional[str] = None

    class Config:
        model = MotorType
        model_exclude = ['id']

class BatteryTypeInSchema(ModelSchema):
    """Schema cho BatteryType - không có measurement cần xử lý riêng"""
    name: str
    description: Optional[str] = None

    class Config:
        model = BatteryType
        model_exclude = ['id']

class IMUInSchema(ModelSchema):
    """Schema cho IMU - không có measurement cần xử lý riêng"""
    name: str
    description: Optional[str] = None

    class Config:
        model = IMU
        model_exclude = ['id']

class ImageStabilizationInSchema(ModelSchema):
    """Schema cho ImageStabilization - không có measurement cần xử lý riêng"""
    name: str
    description: Optional[str] = None

    class Config:
        model = ImageStabilization
        model_exclude = ['id']

class GNSSSystemInSchema(ModelSchema):
    """Schema cho GNSSSystem - không có measurement cần xử lý riêng"""
    name: str
    version: Optional[str] = None
    accuracy: Optional[float] = None
    update_rate: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = None

    class Config:
        model = GNSSSystem
        model_exclude = ['id']

class PackageTypeInSchema(ModelSchema):
    """Schema cho PackageType - không có measurement cần xử lý riêng"""
    name: str
    description: Optional[str] = None

    class Config:
        model = PackageType
        model_exclude = ['id']

class PackagingSpecificationInSchema(Schema):
    name: Optional[str] = None
    code: Optional[str] = None
    dimensions: Optional[str] = None
    max_weight: Optional[str] = None
    package_type_id: Optional[int] = None
    water_proof: Optional[str] = None
    fragile: Optional[bool] = None
    note: Optional[str] = None
    class Config:
        model = PackagingSpecification
        model_fields = ['name', 'code', 'dimensions', 'package_type_id', 'water_proof', 'fragile', 'note', 'max_weight']

class SurveillanceSystemInSchema(Schema):
    """Schema cho SurveillanceSystem"""
    id: Optional[int] = None

    model_config = {
        "protected_namespaces": {}
    }

class LibraryCreateSchema(Schema):
    """Schema cho việc tạo mới library (template)"""
    name: str
    status: Optional[str] = "active"
    active: Optional[bool] = True
    main_type_id: Optional[int] = None  # ForeignKey - chỉ cần id
    sub_type: Optional[str] = "standard"
    created_by_id: Optional[int] = None  # ForeignKey - chỉ cần id
    note: Optional[str] = None
    dimensions: Optional[DimensionsWeightInSchema] = None
    propulsion_system: Optional[PropulsionSystemInSchema] = None
    flight_performance: Optional[FlightPerformanceInSchema] = None
    navigation_control: Optional[NavigationControlInSchema] = None
    radio_communication: Optional[RadioCommunicationInSchema] = None
    telemetry: Optional[TelemetryInSchema] = None
    sensor_suite: Optional[SensorSuiteInSchema] = None
    packaging_options: Optional[List[PackagingOptionInSchema]] = None
    manufacturer_information: Optional[ManufacturerInformationInSchema] = None
    insurance_information: Optional[InsuranceInformationInSchema] = None
    environmental_specification: Optional[EnvironmentalSpecificationInSchema] = None
    safety_feature: Optional[SafetyFeatureInSchema] = None
    device_protocols: Optional[List[int]] = None
    cargo_compartments: Optional[CargoCompartmentsInSchema] = None
    cameras: Optional[List[int]] = None
    surveillance_systems: Optional[List[int]] = None

class LibraryUpdateSchema(Schema):
    """Schema cho việc cập nhật library (template)"""
    name: Optional[str] = None
    status: Optional[str] = None
    active: Optional[bool] = None
    main_type_id: Optional[int] = None  # ForeignKey - chỉ cần id
    sub_type: Optional[str] = None
    modified_by_id: Optional[int] = None  # ForeignKey - chỉ cần id
    note: Optional[str] = None
    dimensions: Optional[DimensionsWeightInSchema] = None
    propulsion_system: Optional[PropulsionSystemInSchema] = None
    flight_performance: Optional[FlightPerformanceInSchema] = None
    navigation_control: Optional[NavigationControlInSchema] = None
    radio_communication: Optional[RadioCommunicationInSchema] = None
    telemetry: Optional[TelemetryInSchema] = None
    sensor_suite: Optional[SensorSuiteInSchema] = None
    packaging_options: Optional[List[PackagingOptionInSchema]] = None
    manufacturer_information: Optional[ManufacturerInformationInSchema] = None
    insurance_information: Optional[InsuranceInformationInSchema] = None
    environmental_specification: Optional[EnvironmentalSpecificationInSchema] = None
    safety_feature: Optional[SafetyFeatureInSchema] = None
    device_protocols: Optional[List[int]] = None
    cargo_compartments: Optional[CargoCompartmentsInSchema] = None
    cameras: Optional[List[int]] = None
    surveillance_systems: Optional[List[int]] = None

class DeviceCreateSchema(Schema):
    """Schema cho việc tạo mới thiết bị"""
    name: str
    terminal_id: Optional[int] = None # ForeignKey - chỉ cần id
    serial_number: str
    unit_id: Optional[str] = None
    library_id: Optional[int] = None  # New field for template reference
    status: Optional[str] = "operational"
    active: Optional[bool] = True
    main_type_id: Optional[int] = None  # ForeignKey - chỉ cần id
    sub_type: Optional[str] = "standard"
    created_by_id: Optional[int] = None  # ForeignKey - chỉ cần id
    note: Optional[str] = None
    dimensions: Optional[DimensionsWeightInSchema] = None
    propulsion_system: Optional[PropulsionSystemInSchema] = None
    flight_performance: Optional[FlightPerformanceInSchema] = None
    navigation_control: Optional[NavigationControlInSchema] = None
    radio_communication: Optional[RadioCommunicationInSchema] = None
    telemetry: Optional[TelemetryInSchema] = None
    sensor_suite: Optional[SensorSuiteInSchema] = None
    packaging_options: Optional[List[PackagingOptionInSchema]] = None
    manufacturer_information: Optional[ManufacturerInformationInSchema] = None
    insurance_information: Optional[InsuranceInformationInSchema] = None
    environmental_specification: Optional[EnvironmentalSpecificationInSchema] = None
    safety_feature: Optional[SafetyFeatureInSchema] = None
    device_protocols: Optional[List[int]] = None
    cargo_compartments: Optional[CargoCompartmentsInSchema] = None
    cameras: Optional[List[int]] = None
    surveillance_systems: Optional[List[int]] = None
    color: Optional[str] = None
    status_id: Optional[int] = None
    registration_number: Optional[str] = None
    
class DeviceUpdateSchema(Schema):
    """Schema cho việc cập nhật thiết bị"""
    name: Optional[str] = None
    terminal_id: Optional[int] = None # ForeignKey - chỉ cần id
    library_id: Optional[int] = None  # New field for template reference
    status: Optional[str] = None
    active: Optional[bool] = None
    main_type_id: Optional[int] = None  # ForeignKey - chỉ cần id
    sub_type: Optional[str] = None
    modified_by_id: Optional[int] = None  # ForeignKey - chỉ cần id
    note: Optional[str] = None
    unit_id: Optional[str] = None
    dimensions: Optional[DimensionsWeightInSchema] = None
    propulsion_system: Optional[PropulsionSystemInSchema] = None
    flight_performance: Optional[FlightPerformanceInSchema] = None
    navigation_control: Optional[NavigationControlInSchema] = None
    radio_communication: Optional[RadioCommunicationInSchema] = None
    telemetry: Optional[TelemetryInSchema] = None
    sensor_suite: Optional[SensorSuiteInSchema] = None
    packaging_options: Optional[List[PackagingOptionInSchema]] = None
    manufacturer_information: Optional[ManufacturerInformationInSchema] = None
    insurance_information: Optional[InsuranceInformationInSchema] = None
    environmental_specification: Optional[EnvironmentalSpecificationInSchema] = None
    safety_feature: Optional[SafetyFeatureInSchema] = None
    device_protocols: Optional[List[int]] = None
    cargo_compartments: Optional[CargoCompartmentsInSchema] = None
    cameras: Optional[List[int]] = None
    surveillance_systems: Optional[List[int]] = None
    color: Optional[str] = None
    status_id: Optional[int] = None
class AddToGroupsSchema(Schema):
    model_name: Optional[str] = None
    record_ids: Optional[str] = None
    group_ids: Optional[str] = None 
