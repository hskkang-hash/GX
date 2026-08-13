from ninja import ModelSchema, Schema
from typing import Optional, List
from pydantic import Field

from devices.schemas.schemas_djantic_out import DeviceOutSchema
from delivery.models import (
    Address, DeliveryOperation, DeliveryOperationItem, 
    DeliveryStatus, DeliveryCancellation, DeliveryReturn
)
from terminals.models import Routes
from orders.models import Order
from devices.models import Device
from core.common.schema_utils import DynamicSchema


class AddressOutSchema(DynamicSchema):
    class Meta:
        model = Address
        model_fields = ['id', 'city', 'district', 'ward', 'street', 
                        'province_name', 'postal_code', 'full_address',
                        'lat', 'lng', 'created_on', 'updated_on']
class OrderOutSchema(DynamicSchema):
    class Meta:
        model = Order
        exclude = []
        depth = 0

class DeliveryStatusOutSchema(DynamicSchema):
    class Meta:
        model = DeliveryStatus
        exclude = []
        depth = 0

class RouteOutSchema(DynamicSchema):
    class Meta:
        model = Routes
        exclude = []
        depth = 0

class DeviceOutSchema(DynamicSchema):
    class Meta:
        model = Device
        exclude = []
        depth = 0

class DeliveryOperationItemOutSchema(DynamicSchema):
    drone: Optional[DeviceOutSchema] = None
    
    class Meta:
        model = DeliveryOperationItem
        exclude = []
        depth = 0

class DeliveryOperationOutSchema(DynamicSchema):
    class Meta:
        model = DeliveryOperation
        model_fields = '__all__'
        exclude = []
        depth = 1

class DeliveryCancellationOutSchema(DynamicSchema):
    class Meta:
        model = DeliveryCancellation
        exclude = []
        depth = 1

class DeliveryReturnOutSchema(DynamicSchema):
    class Meta:
        model = DeliveryReturn
        exclude = []
        depth = 1

# Schemas for operation response in different statuses
class VerificationOperationOutSchema(DynamicSchema):
    class Meta:
        model = DeliveryOperation
        exclude = []
        depth = 1

class ProcessingOperationOutSchema(DynamicSchema):
    class Meta:
        model = DeliveryOperation
        exclude = []
        depth = 1

class CompletedOperationOutSchema(DynamicSchema):
    class Meta:
        model = DeliveryOperation
        exclude = []
        depth = 1

class ReturnedOperationOutSchema(DynamicSchema):
    class Meta:
        model = DeliveryOperation
        exclude = []
        depth = 1

class CancelledOperationOutSchema(DynamicSchema):
    class Meta:
        model = DeliveryOperation
        exclude = []
        depth = 1

class DroneAxesSchema(DynamicSchema):
    x: int
    y: int
    z: int

class DroneVibrationSchema(DynamicSchema):
    x: float
    y: float
    z: float

class DroneTelemetrySchema(DynamicSchema):
    temperature: int
    battery_percent: int
    distance_traveled: float
    wind_speed: int
    axes: DroneAxesSchema
    vibration: Optional[DroneVibrationSchema] = None

class DroneHistorySchema(DynamicSchema):
    timestamps: List[float]
    temperature: List[int]

class DroneStatusSchema(DynamicSchema):
    drone_id: str
    unique_id: str
    telemetry: DroneTelemetrySchema
    history: DroneHistorySchema

class DroneDashboardSchema(DynamicSchema):
    all_drones: List[DroneStatusSchema]
    active_drone: Optional[DroneStatusSchema] = None

class DeliveryOperationEtriOutSchema(DynamicSchema):
    """
    Special schema for ETRI delivery operations with mapped status
    Includes fields optimized for search and sorting
    """
    mapped_status: Optional[str] = None  # For search/sort on mapped status
    
    class Meta:
        model = DeliveryOperation
        exclude = []
        depth = 1


# Status Mapping Output Schemas
class DeliveryStatusWithMappingOutSchema(DynamicSchema):
    """Output schema for delivery status with its mapping information"""
    
    class Meta:
        model = DeliveryStatus
        exclude = []
        depth = 0

class SelectDroneRowOutSchema(DynamicSchema):
    class Meta:
        model = DeliveryOperationItem
        model_fields = '__all__'
        exclude = []
        depth = 0

        