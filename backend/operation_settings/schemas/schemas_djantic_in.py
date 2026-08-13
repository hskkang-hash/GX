from ninja_schema import Schema
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any


class OperationSettingsInSchema(Schema):
    menu_id: int
    tab_id: Optional[int] = None
    group_id: int
    name: str
    is_active: bool = True
    api_url: HttpUrl
    http_method: str = "GET"
    api_params: Optional[Dict[str, Any]] = None
    expected_response: Optional[Dict[str, Any]] = None
    timeout_seconds: int = 30
    retry_count: int = 3
    description: Optional[str] = None
    notes: Optional[str] = None
    send_data: Optional[bool] = None
    body_params: Optional[Dict[str, Any]] = None    
    receive_data: Optional[bool] = None

class OperationSettingsCreateSchema(OperationSettingsInSchema):
    pass


class OperationSettingsUpdateSchema(Schema):
    menu_id: Optional[int] = None
    tab_id: Optional[int] = None
    group_id: Optional[int] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None
    api_url: Optional[HttpUrl] = None
    http_method: Optional[str] = None
    api_params: Optional[Dict[str, Any]] = None
    expected_response: Optional[Dict[str, Any]] = None
    timeout_seconds: Optional[int] = None
    retry_count: Optional[int] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    receive_data: Optional[bool] = None
    send_data: Optional[bool] = None
    body_params: Optional[Dict[str, Any]] = None
    