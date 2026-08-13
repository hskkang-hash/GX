from ninja import Schema
from typing import Optional, Dict
from datetime import datetime


class PartnerCreateMinimalSchema(Schema):
    """Minimal schema for creating partner - only name required"""
    name: str
    expired_days: int 
    group: Optional[str] = None
    api_callback_url: Optional[Dict] = None
    service_key: Optional[str] = None
class PartnerCreateResponseSchema(Schema):
    """
    Schema for partner creation response
    
    This is the ONLY place where full API key is returned
    """
    id: int
    name: str
    code: str
    api_key: str  # Full API key for initial setup only
    is_active: bool
    proxy_user: dict
    group: Optional[str]
    created_on: datetime
    message: str = "Partner created successfully. Save the API key securely - it won't be shown again."


class RefreshTokenSchema(Schema):
    """Schema for refresh token request"""
    refresh_token: str


class ManageRefreshTokenSchema(Schema):
    """Schema for smart refresh token management"""
    refresh_token: Optional[str] = None  # Optional - if provided, will validate against current


class ApiCallbackInSchema(Schema):
    """Schema for API callback URL structure"""
    DeliveryStatusCallback: Optional[str] = ""
    DroneBaseStation: Optional[str] = ""
    DroneUserNotice: Optional[str] = ""


class PartnerCallbackUpdateSchema(Schema):
    """Schema specifically for updating API callback URLs"""
    api_callback_url: ApiCallbackInSchema


class PartnerApiKeyUpdateSchema(Schema):
    """Schema for updating partner API key"""
    name: str
    api_key: Optional[str] = None
    code: Optional[str] = None
    expired_days: Optional[int] = 30
    group: Optional[str] = None
    api_callback_url: Optional[Dict] = None
    is_active: Optional[bool] = True
    service_key: Optional[str] = None

# ============= PARTNER CALLBACK MOCKUP SCHEMAS =============

class DeliveryStatusCallbackInSchema(Schema):
    """Schema for DeliveryStatusCallback webhook từ signals"""
    serviceKey: str
    itemOrgId: str
    deliveryStatus: str
    message: int
    updateTime: str
    deliveryPhoto: Optional[Dict] = {}


class DroneBaseStationCallbackInSchema(Schema):
    """Schema for DroneBaseStation webhook từ signals"""
    serviceKey: str
    startDeliveryPoint: str
    status: str
    message: str
    updateTime: str


class DroneUserNoticeCallbackInSchema(Schema):
    """Schema for DroneUserNotice webhook từ signals"""
    serviceKey: str
    BCode: str
    IsNotice: int
    Html1: str
    Html2: Optional[str] = ""
    Html3: Optional[str] = ""