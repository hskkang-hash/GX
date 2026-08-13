#List api for delivery operation and delivery delivery inquiry

from ninja_extra import api_controller, route
from ninja_schema import Schema
from core.common.base_response import BaseResponse
from core.common.search.dynamic_search import apply_dynamic_filters
from core.api.v1.auth import CustomJWTAuth
from operation_settings.models import OperationSettings
from operation_settings.schemas.schemas_djantic_in import (
    OperationSettingsCreateSchema, 
    OperationSettingsUpdateSchema
)
from django.db import transaction
from django.shortcuts import get_object_or_404
from common.constant import MESSAGE_ENUM, get_message
from django.utils import timezone
from typing import List, Optional, Dict, Any
from django.core.exceptions import ValidationError


class ChangeOrderStatusSchema(Schema):
    order_id: int


class AddressSchema(Schema):
    street: str
    city: str
    district: str
    ward: str
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class MeasurementSchema(Schema):
    value: float
    unit: str


class OrderItemSchema(Schema):
    package_id: int
    weight: MeasurementSchema
    dimension_l: MeasurementSchema
    dimension_w: MeasurementSchema
    dimension_h: MeasurementSchema
    is_waterproof: Optional[bool] = False
    is_fragile: Optional[bool] = False
    item_type_id: Optional[int] = None
    note: Optional[str] = None


class OrderInquirySchema(Schema):
    # Required fields
    recipient_name: str
    recipient_phone: str
    pickup_location_id: int
    
    # Optional fields
    sender_name: Optional[str] = None
    sender_phone: Optional[str] = None
    recipient_address: Optional[AddressSchema] = None
    delivery_option_code: Optional[str] = "terminal_to_terminal"
    payment_method_code: Optional[str] = "cash"
    delivery_terminal_id: Optional[int] = None
    sender_note: Optional[str] = None
    recipient_note: Optional[str] = None
    currency: Optional[str] = "KRW"
    items: Optional[List[OrderItemSchema]] = []
    another_info: Optional[Dict[str, Any]] = None

@api_controller('/delivery', tags=['Delivery'])
class DeliveryAPI:
    
    # Status mapping based on tabs order
    STATUS_TAB_MAPPING = {
        'verification': ["unverified_order", "verified_order"],
        'processing': ["select_route_processing", "select_drone_processing", "in_transit_processing"],
        'completed': ["arrived_order", "completed_order"], 
        'returned': ["order_due_for_returned", "order_pending_returned", "overdue_order", "returned_order", "processed_order"],
        'cancelled': ["cancelled"]
    }
    
    # Tab order for progression
    TAB_ORDER = ['verification', 'processing', 'completed', 'returned', 'cancelled']
    
    @route.get('/operation', auth=CustomJWTAuth())
    def get_delivery_operation(self, request):
        """Get delivery operation"""
        return BaseResponse(status_code=200, message="Delivery operation", data=[])
    
    @route.get('/delivery-inquiry', auth=CustomJWTAuth())
    def get_delivery_inquiry(self, request):
        """Get delivery inquiry"""
        return BaseResponse(status_code=200, message="Delivery inquiry", data=[])
    
    @route.post('/order-inquiry', auth=CustomJWTAuth())
    @transaction.atomic
    def order_inquiry(self, request, payload: OrderInquirySchema):
        """
        Create new order inquiry
        Initialize order with required validation and data
        """
        try:
            # Import models here to avoid circular imports
            from orders.models import (
                Order, OrderItem, Payment, OrderHistory, OrderStatus,
                DeliveryOption, PaymentType, OrderItemType
            )
            from delivery.models import Address
            from terminals.models import Terminal
            from devices.models import PackagingSpecification
            
            # Validate required fields
            if not payload.recipient_name:
                return BaseResponse(
                    status_code=400,
                    message="Recipient name is required",
                    data=None
                )
            
            if not payload.recipient_phone:
                return BaseResponse(
                    status_code=400,
                    message="Recipient phone is required",
                    data=None
                )
            
            if not payload.pickup_location_id:
                return BaseResponse(
                    status_code=400,
                    message="Pickup location is required",
                    data=None
                )
            
            # Validate pickup location exists
            try:
                pickup_location = Terminal.objects.get(id=payload.pickup_location_id)
            except Terminal.DoesNotExist:
                return BaseResponse(
                    status_code=404,
                    message="Pickup location not found",
                    data=None
                )
            
            # Validate delivery terminal if provided
            delivery_terminal = None
            if payload.delivery_terminal_id:
                try:
                    delivery_terminal = Terminal.objects.get(id=payload.delivery_terminal_id)
                except Terminal.DoesNotExist:
                    return BaseResponse(
                        status_code=404,
                        message="Delivery terminal not found",
                        data=None
                    )
            
            # Create recipient address if provided
            recipient_address = None
            if payload.recipient_address:
                recipient_address = Address.objects.create(
                    street=payload.recipient_address.street,
                    city=payload.recipient_address.city,
                    district=payload.recipient_address.district,
                    ward=payload.recipient_address.ward,
                    postal_code=payload.recipient_address.postal_code,
                    latitude=payload.recipient_address.latitude,
                    longitude=payload.recipient_address.longitude
                )
            else:
                # For terminal delivery, create a default address
                recipient_address = Address.objects.create(
                    street="Terminal Address",
                    city="City",
                    district="District", 
                    ward="Ward"
                )
            
            # Get delivery option
            try:
                delivery_option = DeliveryOption.objects.get(code=payload.delivery_option_code)
            except DeliveryOption.DoesNotExist:
                return BaseResponse(
                    status_code=404,
                    message=f"Delivery option '{payload.delivery_option_code}' not found",
                    data=None
                )
            
            # Get payment method
            try:
                payment_method = PaymentType.objects.get(code=payload.payment_method_code)
            except PaymentType.DoesNotExist:
                return BaseResponse(
                    status_code=404,
                    message=f"Payment method '{payload.payment_method_code}' not found",
                    data=None
                )
            
            # Generate order code
            order_code = str(Order._default_manager.count() + 1).zfill(8)
            
            # Get pending order status
            try:
                pending_order_status = OrderStatus.objects.get(code='awaiting_payment')
            except OrderStatus.DoesNotExist:
                return BaseResponse(
                    status_code=404,
                    message="Order status 'awaiting_payment' not found",
                    data=None
                )
            
            # Create order
            order = Order.objects.create(
                order_code=order_code,
                sender_name=payload.sender_name,
                sender_phone=payload.sender_phone,
                recipient_name=payload.recipient_name,
                recipient_phone=payload.recipient_phone,
                recipient_address=recipient_address,
                pickup_location=pickup_location,
                delivery_option=delivery_option,
                delivery_terminal=delivery_terminal,
                created_by=request.user,
                sender_note=payload.sender_note,
                recipient_note=payload.recipient_note,
                created_on=timezone.now(),
                status=pending_order_status,
                another_info=payload.another_info
            )
            
            # Create order items (packages)
            total_amount = 0
            created_items = []
            
            for item_data in payload.items:
                # Validate package specification exists
                try:
                    package_specification = PackagingSpecification.objects.get(id=item_data.package_id)
                except PackagingSpecification.DoesNotExist:
                    return BaseResponse(
                        status_code=404,
                        message=f"Package specification with ID {item_data.package_id} not found",
                        data=None
                    )
                
                # Generate item code with pattern PK00000X
                item_count = OrderItem.objects.count() + 1
                item_code = f"PK{str(item_count).zfill(6)}"
                
                # Validate item type if provided
                item_type = None
                if item_data.item_type_id:
                    try:
                        item_type = OrderItemType.objects.get(id=item_data.item_type_id)
                    except OrderItemType.DoesNotExist:
                        return BaseResponse(
                            status_code=404,
                            message=f"Item type with ID {item_data.item_type_id} not found",
                            data=None
                        )
                
                # Create the order item
                order_item = OrderItem.objects.create(
                    order=order,
                    name="",
                    code=item_code,
                    weight={"value": item_data.weight.value, "unit": item_data.weight.unit},
                    dimension_l={"value": item_data.dimension_l.value, "unit": item_data.dimension_l.unit},
                    dimension_w={"value": item_data.dimension_w.value, "unit": item_data.dimension_w.unit},
                    dimension_h={"value": item_data.dimension_h.value, "unit": item_data.dimension_h.unit},
                    is_waterproof=item_data.is_waterproof,
                    is_fragile=item_data.is_fragile,
                    item_type=item_type,
                    package_id=package_specification,
                    amount=10000,  # Fixed amount for now
                    currency=payload.currency,
                    note=item_data.note
                )
                
                created_items.append({
                    "item_id": order_item.id,
                    "code": order_item.code,
                    "package_id": item_data.package_id,
                    "amount": 10000
                })
                
                # Add to total amount
                total_amount += 10000
            
            # Create payment record
            payment = Payment.objects.create(
                order=order,
                amount=total_amount,
                currency=payload.currency,
                payment_type=payment_method,
                status='completed' if payload.payment_method_code != 'cash' else 'pending',
                payer_phone=payload.sender_phone or payload.recipient_phone
            )
            
            # Create order history
            self._create_order_history_for_inquiry(order, request.user, "created")
            
            # Change order status to pending confirmation if payment is not cash
            if payload.payment_method_code != 'cash':
                try:
                    pending_confirmation_status = OrderStatus.objects.get(code="pending_confirmation")
                    order.status = pending_confirmation_status
                    order.save()
                    
                    self._create_order_history_for_inquiry(order, request.user, "paid")
                except OrderStatus.DoesNotExist:
                    # Continue without changing status if pending_confirmation not found
                    pass
            
            return BaseResponse(
                status_code=201,
                message="Order inquiry created successfully",
                data={
                    "order_id": order.id,
                    "order_code": order.order_code,
                    "status": order.status.code if order.status else None,
                    "total_amount": float(total_amount),
                    "currency": payload.currency,
                    "payment_status": payment.status,
                    "items_count": len(created_items),
                    "items": created_items,
                    "pickup_location": {
                        "id": pickup_location.id,
                        "name": pickup_location.name
                    },
                    "delivery_terminal": {
                        "id": delivery_terminal.id,
                        "name": delivery_terminal.name
                    } if delivery_terminal else None,
                    "recipient": {
                        "name": payload.recipient_name,
                        "phone": payload.recipient_phone
                    },
                    "sender": {
                        "name": payload.sender_name,
                        "phone": payload.sender_phone
                    } if payload.sender_name else None
                }
            )
            
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"Error creating order inquiry: {str(e)}",
                data=None
            )
    
    def _create_order_history_for_inquiry(self, order, user, action):
        """Create order history record for inquiry"""
        try:
            from orders.models import OrderHistory
            
            action_descriptions = {
                "created": "Order created via inquiry API",
                "paid": "Payment completed via inquiry API"
            }
            
            OrderHistory.objects.create(
                order=order,
                action=action,
                description=action_descriptions.get(action, f"Order {action}"),
                created_on=timezone.now()
            )
        except Exception as e:
            # Log error but don't fail the main operation
            print(f"Error creating order history: {str(e)}")
            pass

    @route.post('/change-order-status', auth=CustomJWTAuth())
    @transaction.atomic
    def change_order_status(self, request, payload: ChangeOrderStatusSchema):
        """
        Change order status based on operation settings and workflow
        
        Logic:
        1. Find order in delivery_operation, if not found then find in order table
        2. Case 1: Order not in delivery_operation but exists in order table
           - Create operation for that order
           - Change status based on operation_settings
        3. Case 2: Order exists in delivery_operation
           - Continue logic to find appropriate status and update
        """
        try:
            order_id = payload.order_id
            
            # Try to find order in delivery_operation first
            try:
                # Import here to avoid circular imports
                from delivery.models import DeliveryOperation
                delivery_operation = DeliveryOperation.objects.get(order_id=order_id)
                order_exists_in_delivery = True
                current_order = delivery_operation.order
            except DeliveryOperation.DoesNotExist:
                # Try to find in order table
                try:
                    from orders.models import Order
                    current_order = Order.objects.get(id=order_id)
                    delivery_operation = None
                    order_exists_in_delivery = False
                except Order.DoesNotExist:
                    return BaseResponse(
                        status_code=404,
                        message="Order not found in both delivery_operation and order tables",
                        data=None
                    )
            
            # Get delivery menu and tabs from operation_settings
            delivery_menu = self._get_delivery_menu()
            if not delivery_menu:
                return BaseResponse(
                    status_code=404,
                    message="Delivery menu not found in operation_settings",
                    data=None
                )
            
            # Get active operation settings for delivery
            active_settings = self._get_active_delivery_settings(delivery_menu)
            
            if not order_exists_in_delivery:
                # Case 1: Create delivery operation and set initial status
                result = self._create_delivery_operation_and_set_status(
                    current_order, delivery_menu, active_settings, request.user
                )
            else:
                # Case 2: Update existing delivery operation status
                result = self._update_existing_delivery_operation_status(
                    delivery_operation, current_order, delivery_menu, active_settings, request.user
                )
            
            if result['success']:
                return BaseResponse(
                    status_code=200,
                    message="Order status changed successfully",
                    data=result['data']
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=result['message'],
                    data=None
                )
                
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"Error changing order status: {str(e)}",
                data=None
            )
    
    def _get_delivery_menu(self):
        """Get delivery menu from operation settings"""
        try:
            from core.menu.models import Menu
            return Menu.objects.get(path="/delivery-operation", deleted__isnull=True)
        except Menu.DoesNotExist:
            return None
    
    def _get_active_delivery_settings(self, delivery_menu):
        """Get active operation settings for delivery menu ordered by tab"""
        settings = {}
        
        for tab_name in self.TAB_ORDER:
            try:
                from core.menu.models import Tab
                tab = Tab.objects.get(
                    path=f"/delivery-operation/{tab_name}", 
                    deleted__isnull=True, 
                    parent_menu=delivery_menu
                )
                
                # Get active operation settings for this tab
                active_setting = OperationSettings.objects.filter(
                    menu=delivery_menu,
                    tab=tab,
                    is_active=True
                ).first()
                
                settings[tab_name] = {
                    'tab': tab,
                    'setting': active_setting,
                    'is_active': bool(active_setting)
                }
            except Tab.DoesNotExist:
                settings[tab_name] = {
                    'tab': None,
                    'setting': None,
                    'is_active': False
                }
        
        return settings
    
    def _create_delivery_operation_and_set_status(self, order, delivery_menu, active_settings, user):
        """Create delivery operation and set initial status"""
        try:
            from delivery.models import DeliveryOperation
            
            # Find first active tab to set initial status
            initial_status = None
            initial_tab = None
            
            for tab_name in self.TAB_ORDER:
                if active_settings[tab_name]['is_active']:
                    initial_status = self.STATUS_TAB_MAPPING[tab_name][0]  # First status of the tab
                    initial_tab = tab_name
                    break
            
            if not initial_status:
                return {
                    'success': False,
                    'message': 'No active operation settings found for delivery workflow'
                }
            
            # Create delivery operation
            delivery_operation = DeliveryOperation.objects.create(
                order=order,
                status=initial_status,
                updated_by=user
            )
            
            # Update order status
            order.status = initial_status
            order.save()
            
            # Create history record
            self._create_order_history(order, initial_status, f"Created delivery operation and set to {initial_tab}", user)
            
            return {
                'success': True,
                'data': {
                    'order_id': order.id,
                    'delivery_operation_id': delivery_operation.id,
                    'old_status': None,
                    'new_status': initial_status,
                    'current_tab': initial_tab,
                    'action': 'created_delivery_operation'
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error creating delivery operation: {str(e)}"
            }
    
    def _update_existing_delivery_operation_status(self, delivery_operation, order, delivery_menu, active_settings, user):
        """Update existing delivery operation status"""
        try:
            current_status = delivery_operation.status
            current_tab = self._get_current_tab_from_status(current_status)
            
            if not current_tab:
                return {
                    'success': False,
                    'message': f'Cannot determine current tab from status: {current_status}'
                }
            
            # Find next status in current tab or next active tab
            next_status, next_tab = self._find_next_status(current_status, current_tab, active_settings)
            
            if not next_status:
                return {
                    'success': False,
                    'message': 'No next status available in workflow'
                }
            
            # Update delivery operation and order
            old_status = delivery_operation.status
            delivery_operation.status = next_status
            delivery_operation.updated_by = user
            delivery_operation.save()
            
            order.status = next_status
            order.save()
            
            # Create history record
            action = f"Advanced from {current_tab} to {next_tab}" if current_tab != next_tab else f"Advanced within {current_tab}"
            self._create_order_history(order, next_status, action, user)
            
            return {
                'success': True,
                'data': {
                    'order_id': order.id,
                    'delivery_operation_id': delivery_operation.id,
                    'old_status': old_status,
                    'new_status': next_status,
                    'old_tab': current_tab,
                    'new_tab': next_tab,
                    'action': 'updated_status'
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error updating delivery operation: {str(e)}"
            }
    
    def _get_current_tab_from_status(self, status):
        """Determine current tab from status"""
        for tab_name, status_list in self.STATUS_TAB_MAPPING.items():
            if status in status_list:
                return tab_name
        return None
    
    def _find_next_status(self, current_status, current_tab, active_settings):
        """Find next appropriate status based on current status and active settings"""
        current_tab_statuses = self.STATUS_TAB_MAPPING[current_tab]
        current_status_index = current_tab_statuses.index(current_status)
        
        # Check if there's a next status in current tab and tab is active
        if (current_status_index < len(current_tab_statuses) - 1 and 
            active_settings[current_tab]['is_active']):
            next_status = current_tab_statuses[current_status_index + 1]
            return next_status, current_tab
        
        # Find next active tab
        current_tab_index = self.TAB_ORDER.index(current_tab)
        for i in range(current_tab_index + 1, len(self.TAB_ORDER)):
            next_tab = self.TAB_ORDER[i]
            if active_settings[next_tab]['is_active']:
                next_status = self.STATUS_TAB_MAPPING[next_tab][0]  # First status of next active tab
                return next_status, next_tab
        
        return None, None
    
    def _create_order_history(self, order, status, note, user):
        """Create order history record"""
        try:
            from orders.models import OrderHistory
            OrderHistory.objects.create(
                order=order,
                status=status,
                note=note,
                created_by=user,
                created_on=timezone.now()
            )
        except Exception as e:
            # Log error but don't fail the main operation
            print(f"Error creating order history: {str(e)}")
            pass