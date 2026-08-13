"""
Schemas đầu ra (OUT) sử dụng django-ninja ModelSchema
Chỉ chứa các schemas cho dữ liệu đầu ra từ responses
"""

from ninja import ModelSchema, Schema
from typing import List, Optional, Dict, Any
from datetime import datetime, date, time
from core.common.schema_utils import DynamicSchema
from terminals.models import LocationType, Terminal, TerminalType, Routes, RouteTerminal, Function, TerminalOperatingTime, TerminalException, DayOfWeek
from common.schema_measurable import MeasurableDynamicSchema

class TerminalTypeOutSchema(DynamicSchema):
    class Meta:
        model = TerminalType

class FunctionOutSchema(DynamicSchema):
    class Meta:
        model = Function
        
class LocationTypeOutSchema(DynamicSchema):
    class Meta:
        model = LocationType

class DayOfWeekOutSchema(DynamicSchema):
    class Meta:
        model = DayOfWeek
        fields = '__all__'
class TerminalOperatingTimeOutSchema(DynamicSchema):
    terminal_id: Optional[int] = None
    day_of_week_id: Optional[int] = None
    day_of_week: Optional[DayOfWeekOutSchema] = None
    
    class Meta:
        model = TerminalOperatingTime

class TerminalExceptionOutSchema(DynamicSchema):
    terminal_id: Optional[int] = None
    
    class Meta:
        model = TerminalException

class TerminalOutSchema(MeasurableDynamicSchema):
    # Additional fields for UI display
    full_address: Optional[str] = None
    type: Optional[str] = None
    type_name: Optional[str] = None
    terminal_types_names: Optional[List[str]] = None
    related_routes_count: Optional[int] = None
    is_in_multiple_routes: Optional[bool] = None
    location_type__name: Optional[str] = None
    location_type__description: Optional[str] = None
    registration_date: Optional[date] = None
    terminal_purpose__name: Optional[str] = None
    # New functions-related fields
    functions_names: Optional[List[str]] = None
    functions: Optional[List[FunctionOutSchema]] = None
    # Operating times and exceptions
    operating_times: Optional[List[TerminalOperatingTimeOutSchema]] = None
    exceptions: Optional[List[TerminalExceptionOutSchema]] = None
    
    class Meta:
        model = Terminal
        fields = "__all__"
class RouteTerminalOutSchema(DynamicSchema):
    terminal: Optional[TerminalOutSchema] = None
    # Fields from the terminal model explicitly included for detail view
    terminal_name: Optional[str] = None
    terminal_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    note: Optional[str] = None
     
    class Meta:
        model = RouteTerminal

class RouteOutSchema(MeasurableDynamicSchema):
    route_terminals: Optional[List[RouteTerminalOutSchema]] = None
    start_point: Optional[str] = None
    end_point: Optional[str] = None
    
    class Meta:
        model = Routes

class FunctionTypeOutSchema(DynamicSchema):
    class Meta:
        model = Function