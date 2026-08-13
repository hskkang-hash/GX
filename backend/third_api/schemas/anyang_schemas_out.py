"""
Anyang API Output Schemas
Schema định nghĩa cho các response từ Anyang APIs
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel


class BaseResponseSchema(BaseModel):
    """Base response schema for all Anyang APIs"""
    status: str
    message: str
    timestamp: str
    data: Optional[Dict[str, Any]] = None
    errorCode: Optional[str] = None

class DroneBaseStatusResponseSchema(BaseModel):
    """Schema for drone base status response"""
    code: int
    message: str

class CancelOrderResponseSchema(BaseModel):
    """Schema for cancel order response"""
    itemOrgId: str
    status: int
    message: int
    resTimestamp: str


class OrderDeliveryStatusCallbackResponseSchema(BaseModel):
    """
    Schema for Order/Delivery Status Change API Response 
    API 5.1 according to specification
    """
    itemOrgId: str      # Order identifier
    code: int           # Result code reference (0=success)
    message: str        # Result message
    resTimestamp: str   # Response time (YYYYMMDDHHmmss)


class DroneLocationResponseSchema(BaseModel):
    """Schema for drone location response"""
    itemOrgId: str
    location: Dict[str, Any]
    deliveryETA: str
    resTimestamp: str




class RouteStatusResponseSchema(BaseModel):
    """Schema for route status response according to specification"""
    startDeliveryPoint: str  # Base(delivery point) ID
    endDeliveryPoint: str    # Delivery point ID
    status: int              # Open: 1, Close: 0
    message: int             # Reason content if status is Close (0-4)
    resTimestamp: str        # Response time (YYYYMMDDHHmmss)

class LegacyOrderReceiptResponseSchema(BaseModel):
    """Schema for legacy order receipt response"""
    deliveryRequestId: str
    orderCode: str
    status: str
    trackingNumber: str
    registrationTime: str
    packageInfo: Dict[str, Any]
    pricing: Dict[str, Any]



class CallbackResponseSchema(BaseModel):
    """Schema for callback response"""
    orderId: str
    trackingId: str
    status: str
    processed: bool
    timestamp: str


class ErrorResponseSchema(BaseModel):
    """Schema for error responses"""
    status: str
    message: str
    errorCode: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None 