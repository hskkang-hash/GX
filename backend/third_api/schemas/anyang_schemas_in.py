"""
Anyang API Input Schemas
Schema định nghĩa cho các request đến Anyang APIs
"""

from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel


class BaseStatusQuerySchema(BaseModel):
    """Schema for base status query request"""
    serviceKey: str
    startDeliveryPoint: str  # code of start terminal
    endDeliveryPoint: str    # code of end terminal  
    updateTime: str


class DroneLocationRequestSchema(BaseModel):
    """Schema for drone location request"""
    serviceKey: str
    itemOrgId: str
    updateTime: str


class OrderItemSchema(BaseModel):
    """Schema for order item in orderItems array"""
    ItemName: str  # Item name - range  
    quantity: int  # Quantity
    price: int     # Unit price(KRW)


class OrderReceiptRequestSchema(BaseModel):
    """Schema for order receipt request according to specification"""
    serviceKey: str                    # Service key for API authentication
    itemOrgId: str                     # Order identifier
    itemType: int                      # Item type
    receiptDate: str                   # Order receipt date (YYYYMMDDHHMMMSS)
    startDeliveryPoint: str            # Drone departure point(terminal ID)
    endDeliveryPoint: str              # Drone delivery point(delivery terminal ID)
    weight: Optional[float] = 0                      # weight(kg)
    height: float                      # Item box height(cm)
    depth: float                       # Item box depth(cm)
    width: float                       # Item box width(cm)
    senderName: str                    # Sender name
    senderContact: str                 # Sender contact
    senderZipcode: str                 # Sender postal code
    senderAddress: str                 # Sender address
    receiverName: str                  # Receiver name
    receiverContact: str               # Receiver contact
    receiverZipcode: str               # Receiver postal code
    receiverAddress: str               # Receiver address
    orderItems: List[OrderItemSchema]  # Order item information
    totalReadyTime: str                # Total preparation expected completion time (YYYYMMDDHHMMMSS)




class DeliveryCancellationSchema(BaseModel):
    """Schema for delivery cancellation request"""
    serviceKey: str
    itemOrgId: str
    status: int
    message: int
    updateTime: str


class DeliveryPhotoSchema(BaseModel):
    """Schema for delivery completion photo object"""
    url: str        # Delivery completion photo URL
    timestamp: str  # Photo capture time (YYYYMMDDHHmmss)


class OrderDeliveryStatusCallbackSchema(BaseModel):
    """
    Schema for Order/Delivery Status Change API (GuardianX → Delivery App)
    API 5.1 according to specification
    """
    serviceKey: str                                    # Service key for API authentication
    itemOrgId: str                                    # Order identifier
    deliveryStatus: int                               # Delivery status code (0-5)
    message: int                                      # Message code (0=Normal, refer to cancellation table)
    deliveryPhoto: Union[DeliveryPhotoSchema, Dict, None] = None  # Delivery photo (only for completion) - can be {} or None
    updateTime: str                                   # Status update time (YYYYMMDDHHmmss)



class DroneBaseStatusSchema(BaseModel):
    """Schema for drone base status notification"""
    serviceKey: str
    startDeliveryPoint: str
    status: int
    message: int
    updateTime: str


class UserNoticeSchema(BaseModel):
    """Schema for user notice notification"""
    serviceKey: str
    BCode: str
    IsNotice: bool
    Html1: Optional[str] = None
    Html2: Optional[str] = None
    Html3: Optional[str] = None