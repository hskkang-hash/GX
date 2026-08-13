from delivery.schemas.schemas_djantic_in import AddressSchema
from ninja import Schema
from typing import Dict, Optional, List
from decimal import Decimal

class MoneyFieldInSchema(Schema):
    value: float
    
class OrderItemCreateSchema(Schema):
    name: Optional[str] = None
    weight: Optional[object] = None
    dimension_l: Optional[object] = None
    dimension_w: Optional[object] = None
    dimension_h: Optional[object] = None
    is_waterproof: bool = False
    is_fragile: bool = False
    item_type_id: Optional[int] = None
    package_id: Optional[int] = None
    amount: Optional[MoneyFieldInSchema] = None
    note: Optional[str] = None

class GuessUserCreateSchema(Schema):
    name: str
    phone: str
    address: AddressSchema

class OrderCreateSchema(Schema):
    order_code: Optional[str] = None
    sender_name: str
    sender_phone: str
    sender_address: Optional[AddressSchema] = None
    recipient_name: str
    recipient_phone: str
    recipient_address: AddressSchema
    pickup_location_id: int
    delivery_option_code: str
    delivery_terminal_id: Optional[int] = None
    delivery_address: Optional[AddressSchema] = None
    created_by_guess: Optional[GuessUserCreateSchema] = None
    created_by_id: Optional[int] = None
    sender_note: Optional[str] = None
    recipient_note: Optional[str] = None
    items: Optional[List[OrderItemCreateSchema]] = None
    payment_method_code: Optional[str] = None
    delivery_fee: Optional[MoneyFieldInSchema] = None
    tax_amount: Optional[MoneyFieldInSchema] = None
    discount_amount: Optional[MoneyFieldInSchema] = None
    order_org: Optional[str] = None

class OrderUpdateSchema(Schema):
    sender_name: Optional[str] = None
    sender_phone: Optional[str] = None
    sender_address: Optional[AddressSchema] = None
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    recipient_address: Optional[AddressSchema] = None
    pickup_location_id: Optional[int] = None
    status: Optional[str] = None
    delivery_option_id: Optional[int] = None 
    delivery_fee: Optional[MoneyFieldInSchema] = None
    tax_amount: Optional[MoneyFieldInSchema] = None
    discount_amount: Optional[MoneyFieldInSchema] = None

class OrderCancelSchema(Schema):
    """
    Schema for cancelling an order
    """
    reason: str  # Required field, can't be empty
    
    model_config = {
        "protected_namespaces": {}
    }
     

class OrderRefundSchema(Schema):
    refund_method: str
    bank_code: Optional[str] = None
    account_number: Optional[str] = None
    account_holder_name: Optional[str] = None
    reason: Optional[str] = None
    refund_amount: Optional[MoneyFieldInSchema] = None
    processing_fee: Optional[MoneyFieldInSchema] = None

class PaymentCreateSchema(Schema):
    order_id: int
    amount: MoneyFieldInSchema
    payment_type_id: int
    transaction_id: Optional[str] = None
    gateway_order_id: Optional[str] = None

class InvoiceCreateSchema(Schema):
    payment_id: int
    invoice_number: str
    total_amount: MoneyFieldInSchema
    payment_status: str


# External Order Status Schemas
class ExternalOrderStatusCreateSchema(Schema):
    name: Optional[Dict[str, str]] = None
    value: str
    description: Optional[str] = None
    is_active: Optional[bool] = True
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    border_color: Optional[str] = None
    group_id: Optional[int] = None

class ExternalOrderStatusUpdateSchema(Schema):
    name: Optional[Dict[str, str]] = None
    value: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    border_color: Optional[str] = None
    group_id: Optional[int] = None

# Order Status Mapping Schemas
class OrderStatusMappingCreateSchema(Schema):
    delivery_status_id: int
    external_order_statuses: List[int]  # Changed to list for ManyToMany
    is_active: Optional[bool] = True
    name: Optional[str] = None
    group_id: Optional[int] = None

class OrderStatusMappingUpdateSchema(Schema):
    delivery_status_id: Optional[int] = None
    external_order_statuses: Optional[List[int]] = None  # Changed to list for ManyToMany
    is_active: Optional[bool] = None
    name: Optional[str] = None
    group_id: Optional[int] = None

# Bulk payloads to support UI form
class OrderStatusMappingItemSchema(Schema):
    delivery_status_id: int
    external_order_statuses: Optional[List[int]] = None
    external_order_status_ids: Optional[List[int]] = None
    name: Optional[str] = None

class OrderStatusMappingBulkCreateSchema(Schema):
    group_id: int
    mappings: List[OrderStatusMappingItemSchema]

class OrderStatusMappingBulkUpdateSchema(Schema):
    group_id: int
    mappings: List[OrderStatusMappingItemSchema]
