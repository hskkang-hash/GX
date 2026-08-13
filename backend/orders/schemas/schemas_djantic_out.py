from terminals.models import Terminal
from delivery.schemas.schemas_djantic_out import AddressOutSchema
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from orders.models import DeliveryEvent, DeliveryOption, Invoice, Order, OrderItem, OrderItemType, Payment, Sender, Recipient, PaymentType, OrderHistory, Bank, RefundOrder
from core.common.schema_utils import DynamicSchema

# Financial Summary Schema for Money Fields
class MoneyFieldSchema(BaseModel):
    value: float
    formatted: Optional[str] = None

class FinancialSummarySchema(BaseModel):
    subtotal: Optional[MoneyFieldSchema] = None
    delivery_fee: Optional[MoneyFieldSchema] = None  
    tax_amount: Optional[MoneyFieldSchema] = None
    discount_amount: Optional[MoneyFieldSchema] = None
    total_amount: Optional[MoneyFieldSchema] = None

class PaymentTypeOutSchema(DynamicSchema):
    class Meta:
        model = PaymentType
        model_fields = ['id', 'name', 'code', 'provider', 'method', 'is_active', 'note', 'created_on', 'updated_on']

class SenderOutSchema(DynamicSchema):
    address: AddressOutSchema
    
    class Meta:
        model = Sender
        model_fields = ['id', 'name', 'phone', 'user_id', 'created_on', 'updated_on']

class RecipientOutSchema(DynamicSchema):
    address: AddressOutSchema
    
    class Meta:
        model = Recipient
        model_fields = ['id', 'name', 'phone', 'user_id', 'created_on', 'updated_on']

class OrderItemTypeOutSchema(DynamicSchema):
    class Meta:
        model = OrderItemType
        exclude = []

class OrderItemOutSchema(DynamicSchema):
    item_type_name: Optional[str] = None
    package_name: Optional[str] = None
    package_details: Optional[str] = None
    
    class Meta:
        model = OrderItem
        # DynamicSchema will automatically handle EnhancedMoneyField (amount)
        model_fields = ['id', 'code', 'name', 'weight', 'dimension_l', 'dimension_w', 'dimension_h', 
                       'is_waterproof', 'is_fragile', 'item_type_id', 'package_id', 'amount', 'note']
    
    # @classmethod
    # def from_queryset(cls, queryset_or_instance, many=False, **kwargs):
    #     # Use DynamicSchema's from_queryset and then enhance with package info
    #     result = super().from_queryset(queryset_or_instance, many=many, **kwargs)
        
    #     if many:
    #         for item_data, obj in zip(result, queryset_or_instance):
    #             cls._enhance_item_data(item_data, obj)
    #     else:
    #         cls._enhance_item_data(result, queryset_or_instance)
        
    #     return result
    
    # @classmethod
    # def _enhance_item_data(cls, item_data: dict, obj: OrderItem):
    #     """Enhance item data with package and type information"""
    #     # Add item type name
    #     # if obj.item_type:
    #     #     item_type = OrderItemTypeOutSchema.from_queryset(obj.item_type)
    #     #     item_data['item_type__name'] = item_type.get('name')
            
    #     # Add package information
    #     if obj.package_id:
    #         item_data['package_name'] = obj.package_id.name
    #         package_details = obj.package_id.name
    #         try:
    #             # Get dimensions measurement
    #             dimensions = obj.package_id.measurements.filter(measurement_type='dimensions').first()
    #             if dimensions:
    #                 package_details += ' - ' + str(dimensions.get_formatted_value())
                
    #             # Get max_weight measurement
    #             max_weight = obj.package_id.measurements.filter(measurement_type='max_weight').first()
    #             if max_weight:
    #                 package_details += ' - ' + str(max_weight.get_formatted_value())
    #         except Exception as e:
    #             print(f"Error processing package measurements: {str(e)}")
                
    #         item_data['package_details'] = package_details
    #     else:
    #         # Create details from dimensions if no package
    #         if obj.dimension_l and obj.dimension_w and obj.dimension_h:
    #             item_data['package_details'] = f"{obj.dimension_l['value']}{obj.dimension_l['unit']} x {obj.dimension_w['value']}{obj.dimension_w['unit']} x {obj.dimension_h['value']}{obj.dimension_h['unit']}"

class OrderListOutSchema(DynamicSchema):
    items_count: Optional[int] = None
    financial_summary: Optional[Dict[str, Any]] = None  # Will be added by API
    
    class Meta:
        model = Order
        model_fields = '__all__'
        # DynamicSchema will automatically use '__all__' if model_fields is not specified
        # All fields from Order model will be included automatically

class PaymentOutSchema(DynamicSchema):
    payment_type_name: Optional[str] = None
    
    class Meta:
        model = Payment
        # DynamicSchema will automatically handle EnhancedMoneyField (amount)
        model_fields = ['id', 'amount', 'transaction_id', 'gateway_order_id', 'status', 'paid_at',
                       'created_on', 'updated_on']
    
    @classmethod
    def from_queryset(cls, queryset_or_instance, many=False, **kwargs):
        result = super().from_queryset(queryset_or_instance, many=many, **kwargs)
        
        if many:
            for payment_data, obj in zip(result, queryset_or_instance):
                cls._enhance_payment_data(payment_data, obj)
        else:
            cls._enhance_payment_data(result, queryset_or_instance)
        
        return result
    
    @classmethod
    def _enhance_payment_data(cls, payment_data: dict, obj: Payment):
        """Add payment type information"""
        if obj.payment_type:
            payment_data['payment_type_name'] = obj.payment_type.name
        
class InvoiceOutSchema(DynamicSchema):
    class Meta:
        model = Invoice
        # DynamicSchema will automatically handle EnhancedMoneyField (total_amount)
        model_fields = ['id', 'invoice_number', 'issued_at', 'total_amount',
                       'payment_status', 'created_on', 'updated_on']
        
class DeliveryOptionOutSchema(DynamicSchema):
    class Meta:
        model = DeliveryOption
        model_fields = ['id', 'name', 'code', 'description']

class TerminalOutSchema(DynamicSchema):
    class Meta:
        model = Terminal
        model_fields = ['id', 'name', 'code', 'description']
        
class OrderHistoryOutSchema(DynamicSchema):
    class Meta:
        model = OrderHistory
        model_fields = ['id', 'action', 'description', 'created_on']
    
    @classmethod
    def from_queryset(cls, queryset_or_instance, many=False, **kwargs):
        result = super().from_queryset(queryset_or_instance, many=many, **kwargs)
        
        if many:
            # Filter out records with duplicate descriptions
            seen_descriptions = set()
            filtered_result = []
            
            for item in result:
                description = item.get('description')
                if description not in seen_descriptions:
                    seen_descriptions.add(description)
                    filtered_result.append(item)
            
            return filtered_result
        else:
            return result

class DeliveryEventOutSchema(DynamicSchema):
    class Meta:
        model = DeliveryEvent
        model_fields = ['id', 'event_type', 'description', 'lat', 'lng', 'terminal_stop', 'created_on']

class OrderDetailOutSchema(DynamicSchema):
    recipient_address: Optional[AddressOutSchema] = None
    delivery_address: Optional[AddressOutSchema] = None
    items: Optional[List[OrderItemOutSchema]] = None
    payments: Optional[List[PaymentOutSchema]] = None
    pickup_location: Optional[TerminalOutSchema] = None
    delivery_option: Optional[DeliveryOptionOutSchema] = None
    history: Optional[List[OrderHistoryOutSchema]] = None
    delivery_events: Optional[List[DeliveryEventOutSchema]] = None
    financial_summary: Optional[FinancialSummarySchema] = None  # Will be added by API
    
    class Meta:
        model = Order
        # DynamicSchema will automatically handle all EnhancedMoneyFields
        model_fields = ['id', 'order_code', 'recipient_name', 'recipient_phone',
                       'status__name', 'status__code', 'sender_name', 'sender_phone', 'sender_note', 'recipient_note',
                       'created_on', 'updated_on', 'cancel_reason',
                       # Money fields will be auto-formatted by DynamicSchema
                       'subtotal', 'delivery_fee', 'tax_amount', 'discount_amount', 'total_amount']

class BankOutSchema(DynamicSchema):
    class Meta:
        model = Bank
        model_fields = ['id', 'name', 'code']

# Refund related schemas
class RefundDetailsSchema(BaseModel):
    refund_amount: Optional[MoneyFieldSchema] = None
    processing_fee: Optional[MoneyFieldSchema] = None
    net_refund_amount: Optional[MoneyFieldSchema] = None
    refund_type: Optional[str] = None
    refund_status: Optional[str] = None
    account_info: Optional[Dict[str, Any]] = None

class RefundOrderOutSchema(DynamicSchema):
    bank_name: Optional[str] = None
    net_refund_amount: Optional[Dict[str, Any]] = None
    
    class Meta:
        model = RefundOrder
        # DynamicSchema will automatically handle EnhancedMoneyFields (refund_amount, processing_fee)
        model_fields = ['id', 'refund_type', 'account_number', 'account_holder_name',
                       'refund_amount', 'processing_fee', 'refund_status', 
                       'refund_processed_at', 'refund_reference']
    
    @classmethod
    def from_queryset(cls, queryset_or_instance, many=False, **kwargs):
        result = super().from_queryset(queryset_or_instance, many=many, **kwargs)
        
        if many:
            for refund_data, obj in zip(result, queryset_or_instance):
                cls._enhance_refund_data(refund_data, obj)
        else:
            cls._enhance_refund_data(result, queryset_or_instance)
        
        return result
    
    @classmethod
    def _enhance_refund_data(cls, refund_data: dict, obj):
        """Add calculated fields"""
        if obj.bank:
            refund_data['bank_name'] = obj.bank.name
            
        # Add net refund amount calculation
        if hasattr(obj, 'get_net_refund_amount'):
            net_amount = obj.get_net_refund_amount()
            if net_amount:
                from core.fields.money import Money
                money_obj = Money(net_amount, None)
                refund_data['net_refund_amount'] = {
                    'value': float(net_amount),
                    'formatted': str(money_obj)
                }


# External Order Status Output Schemas
class ExternalOrderStatusOutSchema(DynamicSchema):
    group_name: Optional[str] = None
    
    @staticmethod
    def resolve_group_name(obj):
        return obj.group.name if obj.group else None
    
    class Meta:
        model = "orders.ExternalOrderStatus"
        fields = ['id', 'name', 'value', 'description', 'is_active', 'group_id', 'group_name', 
                 'background_color', 'text_color', 'border_color', 'created_on', 'modified_on']


# Order Status Mapping Output Schemas  
class OrderStatusMappingOutSchema(DynamicSchema):
    delivery_status_name: Optional[str] = None
    external_order_statuses: Optional[List[dict]] = None
    group_name: Optional[str] = None
    
    @staticmethod
    def resolve_delivery_status_name(obj):
        return obj.delivery_status.name if obj.delivery_status else None
    
    @staticmethod
    def resolve_external_order_statuses(obj):
        # Return list of external order statuses for ManyToMany
        return [
            {
                'id': ext.id,
                'name': ext.name,
                'value': ext.value,
                'background_color': ext.background_color,
                'text_color': ext.text_color,
                'border_color': ext.border_color,
            }
            for ext in obj.external_order_statuses.all()
        ] if hasattr(obj, 'external_order_statuses') else []
    
    @staticmethod
    def resolve_group_name(obj):
        return obj.group.name if obj.group else None
    
    class Meta:
        model = "orders.OrderStatusMapping"
        fields = ['id', 'name', 'delivery_status_id', 'delivery_status_name', 'external_order_statuses', 
                 'is_active', 'group_id', 'group_name', 'created_on', 'modified_on']