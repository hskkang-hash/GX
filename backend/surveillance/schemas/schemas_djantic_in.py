from datetime import date, datetime
from typing import Any, Dict, List, Optional

from ninja import Schema
from terminals.schemas.schemas_djantic_in import RouteTerminalInSchema


class SurveillanceProfileDroneUpsertInSchema(Schema):
    """Schema cho drone assignment trong Surveillance Profile."""

    id: Optional[int] = None
    device_id: Optional[int] = None
    order: Optional[int] = None
    scheduled_start_time: Optional[datetime] = None
    start_waypoint_id: Optional[int] = None
    end_waypoint_id: Optional[int] = None
    log_collection: Optional[bool] = True
    video_recording: Optional[bool] = True
    video_analysis: Optional[bool] = True
    estimated_distance_km: Optional[float] = None
    estimated_time_minutes: Optional[int] = None
    note: Optional[str] = None
    waiting_coordinates: Optional[List[float]] = None


class SurveillanceProfileCreateInSchema(Schema):
    """Schema for creating new surveillance profile."""

    name: str
    mission_id: int
    start_time: datetime
    status_id: Optional[int] = None
    operator_id: Optional[int] = None
    estimated_end_time: Optional[datetime] = None
    repeat_type_id: Optional[int] = None
    repeat_until_type_id: Optional[int] = None
    repeat_until_date: Optional[date] = None
    repeat_occurrences: Optional[int] = None
    repeat_metadata: Optional[dict] = None
    color_code: Optional[str] = "#1D9BE2"
    note: Optional[str] = None
    metadata: Optional[dict] = None
    total_distance_km: Optional[float] = None
    total_estimated_time_minutes: Optional[int] = None
    drones: Optional[List[SurveillanceProfileDroneUpsertInSchema]] = None
    takeoff_altitude: Optional[float] = None
    altitude_separation: Optional[float] = None

class SurveillanceProfileUpdateInSchema(Schema):
    """Schema for updating surveillance profile."""

    name: Optional[str] = None
    mission_id: Optional[int] = None
    start_time: Optional[datetime] = None
    status_id: Optional[int] = None
    operator_id: Optional[int] = None
    estimated_end_time: Optional[datetime] = None
    repeat_type_id: Optional[int] = None
    repeat_until_type_id: Optional[int] = None
    repeat_until_date: Optional[date] = None
    repeat_occurrences: Optional[int] = None
    repeat_metadata: Optional[dict] = None
    color_code: Optional[str] = None
    note: Optional[str] = None
    metadata: Optional[dict] = None
    total_distance_km: Optional[float] = None
    total_estimated_time_minutes: Optional[int] = None
    drones: Optional[List[SurveillanceProfileDroneUpsertInSchema]] = None
    takeoff_altitude: Optional[float] = None
    altitude_separation: Optional[float] = None

class SurveillanceProfileApproveInSchema(Schema):
    """Schema for approving surveillance profile."""

    note: Optional[str] = None


class SurveillanceProfileRejectInSchema(Schema):
    """Schema for rejecting surveillance profile."""

    reason: str


class SurveillanceProfileDeviceChecklistInSchema(Schema):
    """Per-drone checklist data for completing profile checks."""

    profile_drone_id: Optional[int] = None
    drone_id: Optional[int] = None
    check_lists: Optional[List[int]] = None
    auto_checklist: Optional[List[Dict[str, Any]]] = None


class SurveillanceProfileCheckCompleteInSchema(Schema):
    """Schema for completing device checks on a surveillance profile."""

    drone_checks: List[SurveillanceProfileDeviceChecklistInSchema]
    not_yet: Optional[bool] = None


class SurveillanceProfileChangeDroneInSchema(Schema):
    """Schema for changing drone assignment within a profile."""

    from_drone_id: int
    to_drone_id: int


class SurveillanceProfileDroneFlightMarkInSchema(Schema):
    """Schema for marking actual flight time for a specific drone (by device unit_id)."""

    drone_unit_id: str
    start_time: datetime
    end_time: datetime
    profile_id: Optional[int] = None

class SurveyMissionReviewInSchema(Schema):
    """
    Schema for reviewing survey mission (generate QGC file without saving)
    Only requires survey parameters - no mission metadata
    Used for /review endpoint to test QGC file before creating mission
    """
    # Required field
    polygon: List[List[float]]  # [[lat, lon], ...] - survey area drawn from map
    
    # Optional survey parameters (with defaults)
    altitude: Optional[float] = 200.0  # Survey altitude in meters
    survey_angle: Optional[float] = 0.0  # Grid rotation (0-360 degrees)
    frontal_overlap: Optional[float] = 70.0  # Photo overlap %
    side_overlap: Optional[float] = 70.0  # Transect spacing overlap %
    entry_location: Optional[int] = 1  # 0=BL, 1=TL, 2=TR, 3=BR
    cruise_speed: Optional[float] = None  # Speed in m/s (defaults to admin waypoint_speed)
    hover_speed: Optional[float] = 5.0  # Hover speed in m/s
    spacing: Optional[float] = None
    trigger_distance: Optional[float] = None
    turnaround_distance: Optional[float] = 60.96
    review : Optional[bool] = False
    
    # QGC Survey Options (only applicable for SURVEY missions with polygon)
    hover_and_capture: Optional[bool] = False
    refly_90_degrees: Optional[bool] = False
    camera_trigger_in_turnaround: Optional[bool] = False


class SurveyMissionWaypointModificationInSchema(Schema):
    """Schema for adding action commands between waypoints"""
    insert_after_order: int  # Thêm action sau waypoint có order này
    command: int  # Command ID (183, 206, 2000, etc.)
    params: List  # [param1, param2, ..., param7]
    frame: int  # Frame ID (2 for MISSION, 3 for GLOBAL_RELATIVE_ALT)
    auto_continue: Optional[bool] = True
    type: Optional[str] = "SimpleItem"  # Always SimpleItem for action commands


class SurveyMissionWaypointInSchema(Schema):
    """Schema for creating/updating survey mission waypoints"""
    name: Optional[str] = None
    latitude: float
    longitude: float
    command_line: Optional[dict] = None
    frame: Optional[dict] = None
    

class SurveyMissionCreateInSchema(Schema):
    """
    Schema for creating survey mission - based on UI form
    Mission type auto-detected:
    - If terminals provided → LINE mission (simple waypoints)
    - If polygon provided → SURVEY mission (auto-generated survey for any shape)
    
    Survey parameters (altitude, angle, overlaps) will use DEFAULT values:
    - altitude: 200m
    - survey_angle: 0°
    - frontal_overlap: 70%
    - side_overlap: 70%
    - entry_location: 1 (Top Left)
    - cruise_speed: Lấy từ cấu hình waypoint_speed
    - hover_speed: 5.0 m/s
    """
    # Required fields from UI
    name: str
    maximum_drones: int
    purpose_id: int
    polygon: Optional[List[List[float]]] = None  # For SURVEY mission
    total_distance: Optional[float] = None
    estimated_time: Optional[float] = None

    terminals: Optional[List[RouteTerminalInSchema]] = None
    
    # Optional checkboxes from UI
    log_collection: Optional[bool] = False
    video_recording: Optional[bool] = False
    video_analysis: Optional[bool] = False
    
    # Optional fields
    note: Optional[str] = None
    
    # Survey parameters - NOT in UI, will use defaults (optional for override)
    altitude: Optional[float] = 150.0  # Default 150m
    takeoff_altitude: Optional[float] = 100.0  # Default 100m
    altitude_separation: Optional[float] = 10.0  # Default 10m
    survey_angle: Optional[float] = 0.0  # Default 0°
    frontal_overlap: Optional[float] = 70.0  # Default 70%
    side_overlap: Optional[float] = 70.0  # Default 70%
    entry_location: Optional[int] = 1  # Default Top Left
    cruise_speed: Optional[float] = None  # Default to waypoint_speed config
    hover_speed: Optional[float] = 5.0  # Default 5 m/s
    spacing: Optional[float] = None
    trigger_distance: Optional[float] = None
    turnaround_distance: Optional[float] = 60.96
    
    # QGC Survey Options (only applicable for SURVEY missions with polygon)
    hover_and_capture: Optional[bool] = False  # Hover at each waypoint to capture
    refly_90_degrees: Optional[bool] = False  # Add cross-hatch pattern (90° transects)
    camera_trigger_in_turnaround: Optional[bool] = False  # Continue triggering in turnaround
    
    # Action commands to add between waypoints
    # FE can send action commands to insert after specific waypoints
    action_commands: Optional[List[SurveyMissionWaypointModificationInSchema]] = None
    region: Optional[str] = None

class SurveyMissionUpdateInSchema(Schema):
    """Schema for updating survey mission"""
    name: Optional[str] = None
    maximum_drones: Optional[int] = None
    purpose_id: Optional[int] = None
    polygon: Optional[List[List[float]]] = None
    total_distance: Optional[float] = None
    estimated_time: Optional[float] = None
    terminals: Optional[List[RouteTerminalInSchema]] = None  # Update waypoints
    altitude: Optional[float] = None
    takeoff_altitude: Optional[float] = None
    altitude_separation: Optional[float] = None
    survey_angle: Optional[float] = None
    frontal_overlap: Optional[float] = None
    side_overlap: Optional[float] = None
    entry_location: Optional[int] = None
    cruise_speed: Optional[float] = None
    hover_speed: Optional[float] = None
    log_collection: Optional[bool] = None
    video_recording: Optional[bool] = None
    video_analysis: Optional[bool] = None
    note: Optional[str] = None
    spacing: Optional[float] = None
    trigger_distance: Optional[float] = None
    turnaround_distance: Optional[float] = None
    
    # QGC Survey Options
    hover_and_capture: Optional[bool] = None
    refly_90_degrees: Optional[bool] = None
    camera_trigger_in_turnaround: Optional[bool] = None
    
    action_commands: Optional[List[SurveyMissionWaypointModificationInSchema]] = None
    region: Optional[str] = None

class SurveyMissionApproveInSchema(Schema):
    """Schema for approving survey mission"""
    note: Optional[str] = None


class SurveyMissionRejectInSchema(Schema):
    """Schema for rejecting survey mission"""
    reason: str


class SurveyMissionBulkActionInSchema(Schema):
    """Schema for bulk activate/deactivate missions"""
    mission_ids: List[int]


class SurveyMissionDroneDivisionInSchema(Schema):
    """Schema for creating drone division from survey mission"""
    mission_id: int
    maximum_drones: Optional[int] = None  # Nếu None thì dùng giá trị từ mission

class SurveillanceProfileCancelInSchema(Schema):
    """Schema for canceling surveillance profile"""
    reason: Optional[str] = None


class SurveyMissionImportRoutesSimpleInSchema(Schema):
    """
    Schema for importing multiple routes into one mission (Simple mode)
    - Chỉ tạo polygon bao bọc các route (không tính toán survey grid)
    - Số lượng MissionWaypoint = số lượng RouteTerminal
    - Vị trí và thứ tự theo route_ids truyền vào
    - Tất cả thông số waypoint lấy từ RouteTerminal
    - Chỉ thông số mission level lấy từ schema hoặc default
    """
    # Required fields
    name: str
    purpose_id: int
    route_ids: List[int]  # Thứ tự route_ids quyết định thứ tự đường bay
    
    # Optional checkboxes from UI
    log_collection: Optional[bool] = False
    video_recording: Optional[bool] = False
    video_analysis: Optional[bool] = False
    
    # Optional fields
    note: Optional[str] = None
    total_distance: Optional[float] = None
    estimated_time: Optional[float] = None
    
    # Mission-level parameters (không dùng cho survey, chỉ để lưu vào mission)
    altitude: Optional[float] = 150.0  # Default 150m (chỉ để lưu vào mission)
    takeoff_altitude: Optional[float] = 100.0  # Default 100m
    altitude_separation: Optional[float] = 10.0  # Default 10m
    cruise_speed: Optional[float] = None  # Default to waypoint_speed config (chỉ để lưu vào mission)
    hover_speed: Optional[float] = 5.0  # Default 5 m/s


class SurveyMissionImportRoutesInSchema(Schema):
    """
    Schema for importing multiple routes into one mission
    Tất cả RouteTerminal từ các route sẽ được chuyển thành MissionWaypoint
    Polygon sẽ được detect tự động từ RouteTerminal:
    - Nếu chỉ có 1 route: giữ nguyên polygon từ các điểm RouteTerminal theo thứ tự
    - Nếu có nhiều route: tính convex hull từ tất cả điểm
    
    maximum_drones sẽ tự động = số lượng route import vào
    """
    # Required fields
    name: str
    purpose_id: int
    route_ids: List[int]  # Danh sách route IDs để import (maximum_drones = len(route_ids))
    
    # Optional checkboxes from UI
    log_collection: Optional[bool] = False
    video_recording: Optional[bool] = False
    video_analysis: Optional[bool] = False
    
    # Optional fields
    note: Optional[str] = None
    total_distance: Optional[float] = None
    estimated_time: Optional[float] = None
    
    # Survey parameters - Optional, sẽ dùng để tạo polygon nếu cần
    altitude: Optional[float] = 150.0  # Default 150m
    takeoff_altitude: Optional[float] = 100.0  # Default 100m
    altitude_separation: Optional[float] = 10.0  # Default 10m
    survey_angle: Optional[float] = 0.0  # Default 0°
    frontal_overlap: Optional[float] = 70.0  # Default 70%
    side_overlap: Optional[float] = 70.0  # Default 70%
    entry_location: Optional[int] = 1  # Default Top Left
    cruise_speed: Optional[float] = None  # Default to waypoint_speed config
    hover_speed: Optional[float] = 5.0  # Default 5 m/s
    spacing: Optional[float] = None
    trigger_distance: Optional[float] = None
    turnaround_distance: Optional[float] = 60.96
    
    # QGC Survey Options (nếu cần tạo survey mission từ polygon)
    hover_and_capture: Optional[bool] = False
    refly_90_degrees: Optional[bool] = False
    camera_trigger_in_turnaround: Optional[bool] = False
    
    # Action commands to add between waypoints
    action_commands: Optional[List[SurveyMissionWaypointModificationInSchema]] = None

class SurveyMissionWaypointDuplicateInSchema(Schema):
    """Schema for waypoint data when duplicating mission"""
    order: int
    name: Optional[str] = None
    latitude: str
    longitude: str
    command_line: Optional[dict] = None
    frame: Optional[dict] = None
    note: Optional[str] = None
    cruise_speed: Optional[str] = None  # e.g., "7 m/s"
    operating_altitude: Optional[str] = None  # e.g., "20 m"


class SurveyMissionImportQGCInSchema(Schema):
    """Schema for importing survey mission from QGC calculated data"""
    name: str
    survey_id: Optional[str] = None
    color: Optional[str] = None
    polygon: List[List[float]]
    survey_config: Optional[dict] = None
    drone_missions: List[dict]  # List of drone mission data with QGC structure
    is_survey_calculated: Optional[bool] = True
    is_survey_assigned: Optional[bool] = False
    total_distance: Optional[str] = None
    total_distance_km: Optional[str] = None
    estimated_time: Optional[str] = None
    maximum_drones: int
    purpose_id: int
    log_collection: Optional[bool] = False
    video_recording: Optional[bool] = False
    video_analysis: Optional[bool] = False
    from_route: Optional[bool] = False
    note: Optional[str] = None
    group_id: Optional[str] = None
