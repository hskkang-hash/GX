"""
Schemas đầu ra (OUT) sử dụng django-ninja DynamicSchema
Chỉ chứa các schemas cho dữ liệu trả về từ API
"""

from ninja import  Schema
from typing import List, Optional, Dict, Any
from datetime import datetime, date


from common.schema_measurable import MeasurableDynamicSchema
from devices.models import (
    Device, DimensionsAndWeight, PropulsionSystem, FlightPerformance, 
    NavigationControl, RadioCommunication, Telemetry, SensorSuite, 
    CameraType, CargoCompartments, PackagingSpecification, PackagingOption, PackagingOptionSpecification,
    ManufacturerInformation, InsuranceInformation, 
    EnvironmentalSpecification, SafetyFeature, Protocol, DeviceProtocol,
    MotorType, BatteryType, IMU, ImageStabilization, GNSSSystem, PackageType,
    Library
)
from core.common.schema_utils import DynamicSchema
# Schema cơ bản cho measurement
class MeasurementValueOutSchema(DynamicSchema):
    value: Any
    unit: str
    formatted: str  # Giá trị đã được định dạng, ví dụ: "5 kg"

class MeasurementRangeOutSchema(Schema):
    min: Any
    max: Any
    unit: str
    formatted: str  # Giá trị đã được định dạng, ví dụ: "-10 to 50 °C"

class MeasurementDimensionsOutSchema(Schema):
    length: Any
    width: Any
    height: Optional[Any] = None
    unit: str
    formatted: str  # Giá trị đã được định dạng, ví dụ: "100 x 50 x 30 mm"

# Schemas cho các thành phần con - sử dụng Schema cho các model có Measurement
class DimensionsWeightOutSchema(Schema):
    id: int
    device_id: int
    created_on: datetime
    updated_at: Optional[datetime] = None
    
    # Các trường measurement định dạng chuỗi
    frame_size: Optional[str] = None
    maximum_takeoff_weight: Optional[str] = None
    payload_capacity: Optional[str] = None
    empty_weight: Optional[str] = None
    
    model_config = {
        "protected_namespaces": {}
    }
        
class PropulsionSystemOutSchema(DynamicSchema):
    class Meta:
        model = PropulsionSystem
        exclude = []
        depth = 0
class FlightPerformanceOutSchema(Schema):
    id: int
    device_id: int
    created_on: datetime
    updated_at: Optional[datetime] = None
    
    # Các trường measurement định dạng chuỗi
    maximum_speed: Optional[str] = None
    cruise_speed: Optional[str] = None
    maximum_altitude: Optional[str] = None
    operating_altitude: Optional[str] = None
    maximum_range: Optional[str] = None
    wind_resistance: Optional[str] = None
    
    model_config = {
        "protected_namespaces": {}
    }
        
class NavigationControlOutSchema(Schema):
    id: int
    device_id: int
    barometric_altimeter: bool
    imu_id: Optional[int] = None
    imu: Optional[str] = None  # Hiển thị tên, không phải id
    created_on: datetime
    updated_at: Optional[datetime] = None
    
    # Các trường measurement định dạng chuỗi
    gps_accuracy: Optional[str] = None
    
    model_config = {
        "protected_namespaces": {}
    }
        
class RadioCommunicationOutSchema(Schema):
    id: int
    device_id: int
    created_on: datetime
    updated_at: Optional[datetime] = None
    
    # Các trường measurement định dạng chuỗi
    frequency: Optional[str] = None
    range: Optional[str] = None
    
    model_config = {
        "protected_namespaces": {}
    }
        
class TelemetryOutSchema(DynamicSchema):
    class Meta:
        model = Telemetry
        exclude = []
        
class SensorSuiteOutSchema(DynamicSchema):
    class Meta:
        model = SensorSuite
        exclude = []

class CameraOutSchema(MeasurableDynamicSchema):
    class Meta:
        model = CameraType
        exclude = []
        

        
class CargoCompartmentsOutSchema(DynamicSchema):
    class Meta:
        model = CargoCompartments
        exclude = []
        
class PackagingSpecificationOutSchema(MeasurableDynamicSchema):
    class Meta:
        model = PackagingSpecification
        exclude = []

class PackagingOptionSpecificationOutSchema(DynamicSchema):
    class Meta:
        model = PackagingOptionSpecification
        exclude = []

class PackagingOptionOutSchema(Schema):
    id: int
    name: Optional[str] = None
    order: int
    created_on: datetime
    updated_at: Optional[datetime] = None
    specifications: Optional[List[PackagingSpecificationOutSchema]] = None
    
    model_config = {
        "protected_namespaces": {}
    }
        
class ManufacturerInformationOutSchema(DynamicSchema):
    class Meta:
        model = ManufacturerInformation
        exclude = []
        
class InsuranceInformationOutSchema(DynamicSchema):
    class Meta:
        model = InsuranceInformation
        exclude = []
        
class EnvironmentalSpecificationOutSchema(Schema):
    id: int
    device_id: int
    created_on: datetime
    updated_at: Optional[datetime] = None
    
    # Các trường measurement định dạng chuỗi
    temperature_range: Optional[str] = None
    humidity: Optional[str] = None
    precipitation: Optional[str] = None
    wind_speed: Optional[str] = None
    noise_takeoff: Optional[str] = None
    noise_cruise: Optional[str] = None
    noise_landing: Optional[str] = None
    
    model_config = {
        "protected_namespaces": {}
    }
        
class SafetyFeatureOutSchema(DynamicSchema):
    class Meta:
        model = SafetyFeature
        exclude = []
        
class ProtocolOutSchema(DynamicSchema):
    class Meta:
        model = Protocol
        exclude = []
        depth = 2
        
class DeviceProtocolOutSchema(DynamicSchema):
    class Meta:
        model = DeviceProtocol
        exclude = []

class MotorTypeOutSchema(DynamicSchema):
    class Meta:
        model = MotorType
        exclude = []
        
class BatteryTypeOutSchema(DynamicSchema):
    class Meta:
        model = BatteryType
        exclude = []
        
class IMUOutSchema(DynamicSchema):
    class Meta:
        model = IMU
        exclude = []
        
class ImageStabilizationOutSchema(DynamicSchema):
    class Meta:
        model = ImageStabilization
        exclude = []
        
class GNSSSystemOutSchema(DynamicSchema):
    class Meta:
        model = GNSSSystem
        exclude = []
        depth = 0
class PackageTypeOutSchema(DynamicSchema):
    class Meta:
        model = PackageType
        exclude = []
class LibraryOutSchema(DynamicSchema):
    """Schema đầy đủ cho Library bao gồm tất cả các trường và mối quan hệ"""
    id: int
    name: Optional[str] = None
    status: Optional[str] = None
    active: Optional[bool] = None
    sub_type: Optional[str] = None
    note: Optional[str] = None
    
    created_on: datetime
    updated_at: Optional[datetime] = None

    # Các mối quan hệ được tự động xử lý (tương tự Device)
    dimensions_and_weight: Optional[DimensionsWeightOutSchema] = None
    propulsion_system: Optional[PropulsionSystemOutSchema] = None
    flight_performance: Optional[FlightPerformanceOutSchema] = None
    navigation_control: Optional[NavigationControlOutSchema] = None
    radio_communication: Optional[RadioCommunicationOutSchema] = None
    telemetry: Optional[TelemetryOutSchema] = None
    sensor_suite: Optional[SensorSuiteOutSchema] = None
    
    # Collections
    cargo_compartments: Optional[CargoCompartmentsOutSchema] = None
    device_cameras: Optional[List[CameraOutSchema]] = None
    device_protocols: Optional[List[DeviceProtocolOutSchema]] = None
    
    # Các thông tin cụ thể khác
    packaging_options: Optional[List[PackagingOptionOutSchema]] = None
    manufacturer_information: Optional[ManufacturerInformationOutSchema] = None
    insurance_information: Optional[InsuranceInformationOutSchema] = None
    environmental_specification: Optional[EnvironmentalSpecificationOutSchema] = None
    safety_feature: Optional[SafetyFeatureOutSchema] = None

    class Meta:
        model = Library
        depth = 2

class LibraryListOutSchema(DynamicSchema):
    """Schema rút gọn cho danh sách Library, chỉ bao gồm các trường cần thiết cho list view"""
    model: Optional[str] = None
    manufacturer: Optional[str] = None

    class Meta:
        model = Library
        # Chỉ lấy các trường hiển thị trong grid
        fields = '__all__'
        depth = 2
        annotated_fields = ['model', 'manufacturer']
# Schema chính cho Device
class DeviceOutSchema(DynamicSchema):
    """Schema đầy đủ cho Device bao gồm tất cả các trường và mối quan hệ"""
    id: int
    name: Optional[str] = None
    serial_number: Optional[str] = None
    status: Optional[str] = None
    active: Optional[bool] = None
    unit_id: Optional[str] = None
    sub_type: Optional[str] = None
    library: Optional[LibraryOutSchema] = None  # Updated to include library info
    
    created_on: datetime
    updated_at: Optional[datetime] = None


    # Các mối quan hệ được tự động xử lý
    dimensions_and_weight: Optional[DimensionsWeightOutSchema] = None
    propulsion_system: Optional[PropulsionSystemOutSchema] = None
    flight_performance: Optional[FlightPerformanceOutSchema] = None
    navigation_control: Optional[NavigationControlOutSchema] = None
    radio_communication: Optional[RadioCommunicationOutSchema] = None
    telemetry: Optional[TelemetryOutSchema] = None
    sensor_suite: Optional[SensorSuiteOutSchema] = None
    
    # Collections
    cargo_compartments: Optional[CargoCompartmentsOutSchema] = None
    device_cameras: Optional[List[CameraOutSchema]] = None
    device_protocols: Optional[List[DeviceProtocolOutSchema]] = None
    
    # Các thông tin cụ thể khác
    packaging_options: Optional[List[PackagingOptionOutSchema]] = None
    manufacturer_information: Optional[ManufacturerInformationOutSchema] = None
    insurance_information: Optional[InsuranceInformationOutSchema] = None
    environmental_specification: Optional[EnvironmentalSpecificationOutSchema] = None
    safety_feature: Optional[SafetyFeatureOutSchema] = None

    class Meta:
        model = Device
        depth=2

class MainTypeOutSchema(Schema):
    id: int
    name: str
    
    
class AddToGroupsResponse(Schema):
    success: bool
    message: str
    added_records: List[int]
    added_groups: List[int]
    errors: Optional[List[str]] = None


class DeviceListOutSchema(DynamicSchema):
    class Meta:
        model = Device
        # Chỉ lấy các trường hiển thị trong grid
        fields = '__all__'

class DeviceDetailOutSchema(DeviceOutSchema):
    """Schema chi tiết cho một Device cụ thể, kế thừa từ DeviceOutSchema
    nhưng có thể thêm các trường tính toán hoặc tùy chỉnh nếu cần"""
    id: int
    name: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    status: Optional[str] = None
    active: Optional[bool] = None
    main_type: Optional[MainTypeOutSchema] = None
    sub_type: Optional[str] = None
    created_on: datetime
    production_date: Optional[datetime] = None
    # Ví dụ về trường tính toán (có thể thêm nếu cần)
    # total_flight_time: Optional[int]
    
    # @validator('total_flight_time', pre=True)
    # def calculate_total_flight_time(cls, v, values):
    #     # Logic tính toán tổng thời gian bay
    #     return v

