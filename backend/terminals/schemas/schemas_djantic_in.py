"""
Schemas đầu vào (IN) sử dụng django-ninja Schema
Chỉ chứa các schemas cho dữ liệu đầu vào từ requests
"""

from ninja import Query, Schema
from typing import List, Optional
from datetime import datetime, date

from terminals.models import Terminal, TerminalType, Routes, RouteTerminal, TerminalOperatingTime, TerminalException, DayOfWeek

class TerminalTypeInSchema(Schema):
    """Schema cho TerminalType"""
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    
    model_config = {
        "protected_namespaces": {}
    }

class FunctionInSchema(Schema):
    """Schema cho Function"""
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    function_type: Optional[str] = None
    
    model_config = {
        "protected_namespaces": {}
    }

class OperatingTimeItemSchema(Schema):
    """Schema cho một operating time item trong danh sách"""
    day_of_week_id: int
    is_active: bool = False
    start_time: Optional[str] = None  # Format: "HH:MM"
    end_time: Optional[str] = None  # Format: "HH:MM"
    
    model_config = {
        "protected_namespaces": {}
    }

class ExceptionItemSchema(Schema):
    """Schema cho một exception item trong danh sách"""
    exception_date: str
    start_time: Optional[str] = None  # Format: "HH:MM"
    end_time: Optional[str] = None  # Format: "HH:MM"
    is_all_day: bool = False
    reason: Optional[str] = None
    
    model_config = {
        "protected_namespaces": {}
    }

class TerminalCreateSchema(Schema):
    """Schema cho việc tạo mới terminal"""
    name: str
    terminal_type_ids: Optional[List[int]] = None
    function_ids: Optional[List[int]] = None  
    location_type_id: Optional[int] = None
    sub_terminal_type_id: Optional[int] = None
    terminal_purpose_id: Optional[int] = None
    code: Optional[str] = None
    time_stops: Optional[str] = None 
    temperature_range: Optional[str] = None 
    weight : Optional[str] = None
    weather_resistant: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city_province: Optional[str] = None
    city_county_district: Optional[str] = None
    ward_town_township: Optional[str] = None
    street_address: Optional[str] = None
    postal_code: Optional[str] = None
    note: Optional[str] = None
    purpose_type_id: Optional[int] = None
    status: Optional[str] = "active"
    url: Optional[str] = None
    manager_name: Optional[str] = None
    manufacturer: Optional[str] = None
    year_of_manufacture: Optional[str] = None
    created_by_id: Optional[int] = None
    registration_date: Optional[date] = None
    delete_avatar: Optional[bool] = False
    address_note: Optional[str] = None
    group_id: Optional[int] = None
    compatible_drone: Optional[str] = None
    swap_time: Optional[str] = None
    weather_resistant: Optional[str] = None
    operating_times: Optional[List[OperatingTimeItemSchema]] = None
    exceptions: Optional[List[ExceptionItemSchema]] = None
    model_config = {
        "protected_namespaces": {}
    }

class TerminalUpdateSchema(Schema):
    """Schema cho việc cập nhật terminal"""
    name: Optional[str] = None
    terminal_type_ids: Optional[List[int]] = None
    function_ids: Optional[List[int]] = None  
    location_type_id: Optional[int] = None
    sub_terminal_type_id: Optional[int] = None
    terminal_purpose_id: Optional[int] = None
    code: Optional[str] = None
    time_stops: Optional[str] = None
    temperature_range: Optional[str] = None
    weight :Optional[str] = None
    weather_resistant: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city_province: Optional[str] = None
    city_county_district: Optional[str] = None
    ward_town_township: Optional[str] = None
    street_address: Optional[str] = None
    postal_code: Optional[str] = None
    note: Optional[str] = None
    purpose_type_id: Optional[int] = None
    status: Optional[str] = None
    url: Optional[str] = None
    manager_name: Optional[str] = None
    manufacturer: Optional[str] = None
    year_of_manufacture: Optional[str] = None
    registration_date: Optional[date] = None
    delete_avatar: Optional[bool] = False
    address_note: Optional[str] = None
    group_id: Optional[int] = None
    compatible_drone: Optional[str] = None
    swap_time: Optional[str] = None
    weather_resistant: Optional[str] = None
    operating_times: Optional[List[OperatingTimeItemSchema]] = None
    exceptions: Optional[List[ExceptionItemSchema]] = None
    model_config = {
        "protected_namespaces": {}
    }

class RouteTerminalInSchema(Schema):
    """Schema cho RouteTerminal"""
    # Stable identifier for updating/deleting a RouteTerminal association
    route_terminal_id: Optional[int] = None
    terminal_id: Optional[int] = None
    stop: Optional[bool] = False
    order: Optional[int] = None
    code: Optional[str] = None
    name: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    note: Optional[str] = None
    for_robot: Optional[bool] = False
    cruise_speed: Optional[str] = None
    time_stops: Optional[str] = None
    operating_altitude: Optional[str] = None
    command_line: Optional[dict] = None
    frame: Optional[dict] = None
    do_jump_id: Optional[int] = None
    model_config = {
        "protected_namespaces": {}
    }

class RouteCreateSchema(Schema):
    """Schema cho việc tạo mới route"""
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = True
    status: Optional[str] = "active"
    total_stops: Optional[int] = 0
    terminal_from_id: Optional[int] = None
    total_distance: Optional[str] = None
    estimated_time: Optional[str] = None
    note: Optional[str] = None
    terminals: Optional[List[RouteTerminalInSchema]] = None
    two_way: Optional[bool] = False
    route_service_id: Optional[int] = None
    model_config = {
        "protected_namespaces": {}
    }

class RouteTerminalsPatchInSchema(Schema):
    """
    Patch terminals for a route without sending the full list.
    - create: items to add (route_terminal_id should be None)
    - update: items to update (route_terminal_id required)
    - delete: list of route_terminal_id to delete
    """
    create: Optional[List[RouteTerminalInSchema]] = None
    update: Optional[List[RouteTerminalInSchema]] = None
    delete: Optional[List[int]] = None

    model_config = {
        "protected_namespaces": {}
    }

class RouteUpdateSchema(Schema):
    """Schema cho việc cập nhật route"""
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    total_stops: Optional[int] = None
    terminal_from_id: Optional[int] = None
    total_distance: Optional[str] = None
    estimated_time: Optional[str] = None
    note: Optional[str] = None
    terminals_patch: Optional[RouteTerminalsPatchInSchema] = None
    terminals: Optional[List[RouteTerminalInSchema]] = None
    two_way: Optional[bool] = None
    route_service_id: Optional[int] = None
    model_config = {
        "protected_namespaces": {}
    }

class LocationTypeInSchema(Schema):
    """Schema cho LocationType"""
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    
    model_config = {
        "protected_namespaces": {}
    } 

class FunctionTypeInSchema(Schema):
    """Schema cho FunctionType"""
    function_type: str
    
    model_config = {
        "protected_namespaces": {}
    }

class QGroundControlPlanImportSchema(Schema):
    """Schema cho việc import file .plan từ QGroundController"""
    file: bytes  # File .plan được upload
    
    model_config = {
        "protected_namespaces": {}
    }

class QGroundControlPlanExportSchema(Schema):
    """Schema cho việc export file .plan cho QGroundController"""
    route_ids: List[int]  # Danh sách ID của các routes cần export
    
    model_config = {
        "protected_namespaces": {}
    }

class QGroundControlMissionItemSchema(Schema):
    """Schema cho mission item trong file .plan"""
    autoContinue: bool = True
    command: int
    doJumpId: int
    frame: int
    params: List[Optional[float]]
    type: str = "SimpleItem"
    AMSLAltAboveTerrain: Optional[float] = None
    Altitude: Optional[float] = None
    AltitudeMode: Optional[int] = None
    
    model_config = {
        "protected_namespaces": {}
    }

class QGroundControlMissionSchema(Schema):
    """Schema cho mission trong file .plan"""
    cruiseSpeed: float = 15
    firmwareType: int = 12
    globalPlanAltitudeMode: int = 1
    hoverSpeed: float = 5
    items: List[QGroundControlMissionItemSchema]
    plannedHomePosition: List[Optional[float]]
    vehicleType: int = 2
    version: int = 2
    
    model_config = {
        "protected_namespaces": {}
    }

class QGroundControlPlanSchema(Schema):
    """Schema cho file .plan hoàn chỉnh"""
    fileType: str = "Plan"
    geoFence: dict
    groundStation: str = "QGroundControl"
    mission: QGroundControlMissionSchema
    rallyPoints: dict
    version: int = 1
    
    model_config = {
        "protected_namespaces": {}
    }

# Schemas cho MAVLink API
class MavlinkFrameQuerySchema(Schema):
    """Schema cho query parameters của MAVLink frames API"""
    page: int = Query(default=1, description="Số trang (mặc định: 1)")
    pageSize: int = Query(default=20, description="Số lượng items trên mỗi trang (mặc định: 20)")
    searchTerm: str = Query(default=None, description="Từ khóa tìm kiếm trong tên hoặc mô tả frame")
    category: str = Query(default=None, description="Lọc theo danh mục frame (GLOBAL, LOCAL, BODY, etc.)")

class MavlinkCommandQuerySchema(Schema):
    """Schema cho query parameters của MAVLink commands API"""
    page: int = Query(default=1, description="Số trang (mặc định: 1)")
    pageSize: int = Query(default=20, description="Số lượng items trên mỗi trang (mặc định: 20)")
    searchTerm: str = Query(default=None, description="Từ khóa tìm kiếm trong tên hoặc mô tả lệnh")
    category: str = Query(default=None, description="Lọc theo danh mục lệnh (NAV, DO, CONDITION, etc.)")

class TerminalDeactivateSchema(Schema):
    """Schema cho việc deactivate terminal"""
    deactivate_reason_id: Optional[int] = None
    
    model_config = {
        "protected_namespaces": {}
    }

class DayOfWeekInSchema(Schema):
    """Schema cho DayOfWeek"""
    name: str
    code: str
    order: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = True
    
    model_config = {
        "protected_namespaces": {}
    }

class TerminalOperatingTimeInSchema(Schema):
    """Schema cho TerminalOperatingTime"""
    terminal_id: int
    day_of_week_id: int  # ID của DayOfWeek
    is_active: bool = False
    start_time: Optional[str] = None  # Format: "HH:MM"
    end_time: Optional[str] = None  # Format: "HH:MM"
    
    model_config = {
        "protected_namespaces": {}
    }

class TerminalOperatingTimeUpdateSchema(Schema):
    """Schema cho việc cập nhật TerminalOperatingTime"""
    day_of_week_id: Optional[int] = None
    is_active: Optional[bool] = None
    start_time: Optional[str] = None  # Format: "HH:MM"
    end_time: Optional[str] = None  # Format: "HH:MM"
    
    model_config = {
        "protected_namespaces": {}
    }

class TerminalExceptionInSchema(Schema):
    """Schema cho TerminalException"""
    terminal_id: int
    exception_date: date
    start_time: Optional[str] = None  # Format: "HH:MM"
    end_time: Optional[str] = None  # Format: "HH:MM"
    is_all_day: bool = False
    reason: Optional[str] = None
    
    model_config = {
        "protected_namespaces": {}
    }

class TerminalExceptionUpdateSchema(Schema):
    """Schema cho việc cập nhật TerminalException"""
    exception_date: Optional[date] = None
    start_time: Optional[str] = None  # Format: "HH:MM"
    end_time: Optional[str] = None  # Format: "HH:MM"
    is_all_day: Optional[bool] = None
    reason: Optional[str] = None
    
    model_config = {
        "protected_namespaces": {}
    }