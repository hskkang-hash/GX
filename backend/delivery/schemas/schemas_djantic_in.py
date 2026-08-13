from ninja import Schema
from typing import Optional, List, Any, Dict, Union
from datetime import datetime

class InputListSchema(Schema):
    """
    Schema for pagination, sorting and filtering in list endpoints.
    Used as query parameters for GET requests.
    
    Usage in frontend:
    GET /api/verification/unverified-operations?page_size=10&current_page=2&sort_field=created_at&sort_direction=desc&from_date=2023-01-01T00:00:00&to_date=2023-12-31T23:59:59&search=order123
    """
    page_size: Optional[int] = 25
    current_page: Optional[int] = 1
    sort_field: Optional[str] = None
    sort_direction: Optional[str] = "desc"
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    search: Optional[str] = None
    
class AddressSchema(Schema):
    city: Optional[str] = None
    district: Optional[str] = None
    ward: Optional[str] = None
    street: Optional[str] = None
    province_name: Optional[str] = None
    postal_code: Optional[str] = None
    full_address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None 
    
class CancelOrderSchema(Schema):
    reason_note: str
    is_system: bool = False

class VerifyOrdersSchema(Schema):
    operation_ids: List[int]

class PendingTimeoutSchema(Schema):
    operation_ids: List[int]
    terminal_id: int

class ExecuteOrdersSchema(Schema):
    operation_ids: List[int]

class UpdateStatusSchema(Schema):
    status_code: str 
    
class AssignPackagesToDroneSchema(Schema):
    drone_id: int
    package_id: int

class UpdateDeliveryEventSchema(Schema):
    drone_uid: str
    lat: float
    lng: float


class AssignPackagesToDroneSchema(Schema):
    drone_ids: List[int]
    package_ids: List[int]

# Schema for ETRI Integration
class SendToEtriSchema(Schema):
    """Schema for sending delivery data to ETRI system"""
    USER_ID: str
    ORG_ID: str
    RECEIPT_ID: str
    MISSION_ID: str
    RECEIPT_DATE: str  # Format: YYYY-MM-DD HH:MM:SS
    SENDER_NAME: str
    SENDER_ADDRESS: str
    SENDER_ZIPCODE: str
    SENDER_TERMINAL_ID: int
    SENDER_TERMINAL_NAME: str
    SENDER_TERMINAL_ADDRESS: str
    RECEIVER_NAME: str
    RECEIVER_ADDRESS: str
    RECEIVER_ZIPCODE: str
    LOGISTICS_TYPE: str  # 승강물, 수산물, 전자제품, 서적, 의약품, 의류, 건자재, 음식, 식품, 시료, 선물, 보급 기타
    WEIGHT: int

class ReceiveFromEtriSchema(Schema):
    """Schema for receiving delivery status from ETRI system"""
    CONTROL_ID: str
    USER_ID: str
    ORG_ID: str
    RECEIPT_ID: str
    MISSION_ID: str
    RECEIPT_DATE: str  # Format: YYYY-MM-DD HH:MM:SS
    MISSION_STATUS: int  # 0: 업무생성, 1: 업무실패, 2: 반려
    CANCEL_REJECT_REASON: str
    MISSION_DATE: str  # Format: YYYY-MM-DD HH:MM:SS
    DRONE_PATH_DISTANCE: float
    DRONE_PATH: Union[str, List[List[float]]]  # 임무 수행 중 드론의 비행한 경로의 좌표 리스트 - hỗ trợ cả string "[(lat, lng), ...]" và list [[lat, lng], ...] format, sẽ normalize về list format (chuẩn)
    ROBOT_PATH_DISTANCE: float
    ROBOT_PATH: Union[str, List[List[float]]]  # 임무 수행 중 로봇이 주행한 경로의 좌표 리스트 - hỗ trợ cả string "[(lat, lng), ...]" và list [[lat, lng], ...] format, sẽ normalize về list format (chuẩn)
    DOCKING_POINT: Union[str, List[List[float]]]  # 임무 수행 중, 드론과 로봇이 연계되는 도킹 스테이션의 좌표 - hỗ trợ cả string "[(lat, lng), ...]" và list [[lat, lng], ...] format, sẽ normalize về list format (chuẩn)

class SendDataToEtriSchema(Schema):
    operation_id: int



class AssignOrderPackagesSchema(Schema):
    order_id: int
    package_ids: List[int]


class AssignDroneOrdersSchema(Schema):
    drone_id: int
    orders: List[AssignOrderPackagesSchema]


class AssignPackagesToDronesInSchema(Schema):
    route_id: int
    drone_ids: List[AssignDroneOrdersSchema]


# Flight management schemas
class CancelFlightInSchema(Schema):
    drone_id: int
    order_ids: List[int]

class ChangeDroneInSchema(Schema):
    order_ids: List[int]
    from_drone: int
    to_drone: Optional[int] = None
    route_id: int

class ApproveFlightInSchema(Schema):
    order_ids: List[int]
    check_lists: Optional[List[int]] = None
    auto_checklist: Optional[List[Dict[str, Any]]] = None
    drone_id: int
    not_yet: Optional[bool] = None
    
class UploadMissionToGcsInSchema(Schema):
    order_ids: List[int]
    drone_unique_id: str
    
class StartMissionToGcsInSchema(Schema):
    drone_unique_id: str

class CancelAwaitingOrderInSchema(Schema):
    order_ids: List[int]
    reason_note: str

class DroneMonitoringRequestInSchema(Schema):
    """Schema for drone monitoring data request with selected items"""
    unique_id: str
    monitoring_items: Optional[List[str]] = None  # List of items to include: ['x-axis', 'y-axis', 'z-axis', 'vibe', 'gps', 'ch1in', 'ch2in', ..., 'ch1out', 'ch2out', ...]
    time_window_minutes: Optional[int] = 15  # Time window for historical data