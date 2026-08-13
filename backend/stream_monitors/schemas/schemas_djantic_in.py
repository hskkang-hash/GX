"""
Input schemas for stream monitors drawing functionality
"""
from datetime import datetime
from ninja import Schema
from typing import List, Optional, Dict, Any


class DrawingSessionCreateInSchema(Schema):
    name: str
    stream_monitor_id: int


class DrawingSessionUpdateInSchema(Schema):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class DrawingElementCreateInSchema(Schema):
    session_id: int
    element_type: str
    data: Dict[str, Any]


class DrawingElementUpdateInSchema(Schema):
    data: Dict[str, Any]

class StreamMonitorInSchema(Schema):
    id: int
    drone_id: Optional[int] = None
    ip_source: Optional[str] = None
    ai_models: Optional[List[int]] = None
    is_visualize: Optional[bool] = None
    order: Optional[int] = None
    in_use: Optional[bool] = None
    is_active: Optional[bool] = None

class StreamMonitorsInSchema(Schema):
    stream_monitors: List[StreamMonitorInSchema]

class StreamMonitorCaptureInSchema(Schema):
    stream_monitor_code: str
    ai_model__code: Optional[str] = None

class AIStreamUrlInSchema(Schema):
    event_stream: Optional[str] = None
    json_data: Optional[Dict[str, Any]] = None

class ExternalStreamMonitorInSchema(Schema):
    id: Optional[int] = None
    name: str
    ip_source: str
    external_drone_name: Optional[str] = None
    external_operation_name: Optional[str] = None
    external_registration_number: Optional[str] = None
    external_manufacturer: Optional[str] = None
    external_flight_distance: Optional[float] = None
    external_flight_time: Optional[int] = None
    external_flight_altitude: Optional[float] = None
    external_start_point_x: Optional[str] = None
    external_start_point_y: Optional[str] = None
    external_end_point_x: Optional[str] = None
    external_end_point_y: Optional[str] = None
    external_start_time: Optional[datetime] = None
    external_end_time: Optional[datetime] = None
    remark: Optional[str] = None


class StopRecordingInSchema(Schema):
    group: Optional[str] = None

class StartRecordingInSchema(Schema):
    group: Optional[str] = None