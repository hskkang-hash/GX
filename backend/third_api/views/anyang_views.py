"""
Anyang API Views
Controllers for Anyang drone delivery system integration
"""

import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict

from ninja_extra import api_controller, route
from ninja.errors import ValidationError
from django.http import HttpRequest, JsonResponse
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.db.models.expressions import RawSQL

from delivery.services.processing_service import ProcessingService

from ..services.anyang_services import (
    validate_service_key,
    AnyangOrderService
)

from ..common.utils import (
    get_anyang_target_url,
    format_anyang_response,
    format_anyang_drone_location_response,
    validate_required_fields
)

# Import schemas
from ..schemas.anyang_schemas_in import (
    BaseStatusQuerySchema,
    DroneLocationRequestSchema,
    OrderReceiptRequestSchema,
    DeliveryCancellationSchema,
    DroneBaseStatusSchema,
    UserNoticeSchema,
    OrderDeliveryStatusCallbackSchema,
)
from ..schemas.anyang_schemas_out import (
    BaseResponseSchema,
    CancelOrderResponseSchema,
    DroneLocationResponseSchema,
    OrderDeliveryStatusCallbackResponseSchema
)

# Import services
from ..services.anyang_services import (
    validate_service_key,
    AnyangOrderService,
    AnyangCallbackService
)

from delivery.services.processing_service import ProcessingService

# Import models from orders and delivery
from orders.models import Order, OrderStatus
from delivery.models import DeliveryCancellation, DeliveryCancellationType, DeliveryOperation, DeliveryOperationItem, DeliveryStatus
from devices.models import Device, DeviceStatus
from terminals.models import Terminal
from core.middleware.refresh_token import get_current_request
from django.db.models import QuerySet
from core.api.v1.auth import CustomJWTAuth
from core.user.services.usergroup_service import UserGroupService
from delivery.services.weather_service import WeatherService
from django.utils import timezone
logger = logging.getLogger(__name__)


# ============================================================================
# DELIVERY APP → GUARDIAN X CONTROLLER (Incoming APIs)
# ============================================================================

CANCELLATION_REASON = {
    0: {
        "en": "Normal status",
        "ko": "정상 상태일때 사용"
    },
    1: {
        "en": "Delivery unavailable due to weather",
        "ko": "날씨로 인한 배송불가"
    },
    2: {
        "en": "All drones under maintenance",
        "ko": "모든 드론 정비중"
    },
    3: {
        "en": "Loading impossible",
        "ko": "적재 불가"
    },
    4: {
        "en": "Customer cancellation",
        "ko": "주문자 취소"
    },
    5: {
        "en": "Store cancellation",
        "ko": "상점에서 취소"
    },
    6: {
        "en": "Not operating hours",
        "ko": "운영시간 아님"
    }
}
def check_terminal_open(terminal_code: str, start_terminal: bool = False) -> tuple[int, int]:
    """
    Check if the terminal is open
    Return:
        - int: open=1, close=0
        - int: Message response
    """
    terminal_status = 0 # Close
    message_response = 0 # Normal
    
    terminal = Terminal.objects.filter(code=terminal_code, active=True).first()
    
    if not terminal:
        message_response = 2 # Delivery route or delivery point suspended
        return terminal_status, message_response
    
    available_status = DeviceStatus.objects.filter(code__in=['available']).first()
    
    # Get list Drone in terminal
    drones = Device.objects.filter(terminal=terminal, 
                                   active=True)
    drone_available = drones.filter(status=available_status)
    if start_terminal:
        number_of_orders = DeliveryOperation.objects.filter(order__pickup_location=terminal, 
                                                current_status__code__in=['in_transit_processing',
                                                                        'select_route_processing',
                                                                        'select_drone_processing', 
                                                                        'unverified_order',
                                                                        'verified_order',
                                                                        ]).count()

        total_drones = drones.count()
        available_drones = drone_available.count()

        if total_drones > 0 and available_drones == 0:
            if number_of_orders < total_drones + 1:
                return 1, 0
            message_response = 4  # All drones in operation
            return terminal_status, message_response

    terminal_status = 1  # Open
        
    return terminal_status, message_response


def check_detailed_drone_status(terminal_code: str) -> int:
    """
    Enhanced drone status check to differentiate between maintenance vs operation
    Returns specific message code: 3=maintenance, 4=operation, 2=other issues
    """
    terminal = Terminal.objects.filter(code=terminal_code, active=True).first()
    
    if not terminal:
        return 2  # Route suspended
    
    # Get all drones at terminal
    drones = Device.objects.filter(terminal=terminal, active=True)
    
    if drones.count() == 0:
        return 2  # No drones - route suspended
    
    # Get different status types
    available_status = DeviceStatus.objects.filter(code='available').first()
    maintenance_statuses = DeviceStatus.objects.filter(code__in=['maintenance', 'under_maintenance', 'broken'])
    operation_statuses = DeviceStatus.objects.filter(code__in=['on_mission', 'assigned', 'in_flight', 'busy'])
    
    # Count drones by status
    available_drones = drones.filter(status=available_status).count()
    maintenance_drones = drones.filter(status__in=maintenance_statuses).count()
    operation_drones = drones.filter(status__in=operation_statuses).count()
    total_drones = drones.count()
    
    # If has available drones, should return 0 (this shouldn't be called in that case)
    if available_drones > 0:
        return 0  # Normal
    
    # No available drones - determine why
    if maintenance_drones == total_drones:
        return 3  # All drones maintenance
    elif operation_drones > 0:
        return 4  # All drones in operation
    else:
        return 2  # Unknown status - route suspended


def check_weather_conditions(request: HttpRequest, data) -> bool:
    """
    Check weather conditions for drone delivery
    Logic:
    1. Check allow_order_in_bad_weather setting from UserGroupService
    2. If true -> return True (allow order)
    3. If false -> check weather at endDeliveryPoint:
       - Get Terminal by endDeliveryPoint code
       - Get lat/long from Terminal
       - Check weather at that location
       - If weather code is in restricted list -> return False
       - Otherwise -> return True
    
    Args:
        request: HttpRequest object to get user info
        data: OrderReceiptRequestSchema object containing endDeliveryPoint
        
    Returns: 
        True if weather is suitable for order creation, False if not suitable
    """
    try:
        # Step 1: Check allow_order_in_bad_weather setting
        user = request.user
        if hasattr(user, 'userprofilelink') and user.userprofilelink.group:
            allow_order_in_bad_weather = UserGroupService.get_user_group_settings(
                user.userprofilelink.group.id, 
                'allow_order_in_bad_weather'
            )
            
            # If setting is active (True), allow order regardless of weather
            if allow_order_in_bad_weather.get('active', False):
                return True
        
        # Step 2: If not allowed, check actual weather at endDeliveryPoint
        # Get Terminal by code
        try:
            end_terminal = Terminal.objects.get(code=data.endDeliveryPoint, active=True)
        except Terminal.DoesNotExist:
            logger.warning(f"Terminal not found for endDeliveryPoint: {data.endDeliveryPoint}")
            # If terminal not found, default to allowing order (fail-safe)
            return True
        
        # Get coordinates from terminal
        if not end_terminal.latitude or not end_terminal.longitude:
            logger.warning(f"Terminal {end_terminal.code} has no coordinates")
            # If no coordinates, default to allowing order (fail-safe)
            return True
        
        try:
            lat = float(end_terminal.latitude)
            lon = float(end_terminal.longitude)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid coordinates for terminal {end_terminal.code}: {e}")
            # If invalid coordinates, default to allowing order (fail-safe)
            return True
        
        # Get current weather at terminal location
        weather_data = WeatherService._get_current_weather(lat, lon)
        if not weather_data:
            logger.warning(f"Could not fetch weather data for terminal {end_terminal.code}")
            # If weather API fails, default to allowing order (fail-safe)
            return True
        
        # Get weather code
        weather_code = weather_data.get('weather_code')
        
        if weather_code is None:
            logger.warning(f"Weather code not found in weather data for terminal {end_terminal.code}")
            # If no weather code, default to allowing order (fail-safe)
            return True
        
        # List of weather codes that are NOT allowed for order creation
        # Based on WMO weather codes: 45, 48-51, 53, 55-61, 63, 65-66, 67-71, 73, 75-77, 80-82, 85-86, 95-96, 99
        def is_restricted_weather_code(code: int) -> bool:
            """Check if weather code is in restricted list"""
            if code == 45:
                return True
            if 48 <= code <= 51:
                return True
            if code == 53:
                return True
            if 55 <= code <= 61:
                return True
            if code == 63:
                return True
            if 65 <= code <= 66:
                return True
            if 67 <= code <= 71:
                return True
            if code == 73:
                return True
            if 75 <= code <= 77:
                return True
            if 80 <= code <= 82:
                return True
            if 85 <= code <= 86:
                return True
            if 95 <= code <= 96:
                return True
            if code == 99:
                return True
            return False
        
        # Check if weather code is restricted
        if is_restricted_weather_code(weather_code):
            logger.info(f"Weather code {weather_code} is restricted for terminal {end_terminal.code}")
            return False
        
        # Weather is suitable for order creation
        return True
        
    except Exception as e:
        logger.error(f"Error checking weather conditions: {str(e)}")
        # On error, default to allowing order (fail-safe)
        return True


@api_controller("/api", tags=["Anyang - Delivery App APIs (Delivery App → GuardianX)"])
class AnyangDeliveryAppController:
    """Controller for APIs that receive requests from Anyang Delivery App"""

    @route.post("/route/status", response={200: Dict, 400: Dict, 401: Dict}, auth=CustomJWTAuth())
    def route_status_query(self, request: HttpRequest, data: BaseStatusQuerySchema):
        """
        API 1: Route Status Query  
        Request drone base open/close status between delivery points
        
        Logic:
        - Find terminals by code
        - Check drone availability using all_drones
        - Return status: 1=open, 0=close
        - Return message: 0=Normal, 1=Weather, 2=Route suspended, 3=All drones maintenance, 4=All drones in operation, 5=Weight exceeded, 6=Size exceeded
        """
        status = 0 # Close
        message = 0 # Normal
        try:
            # Validate serviceKey
            is_valid, error_msg = validate_service_key(data.serviceKey)
            if not is_valid:
                return {
                    'startDeliveryPoint': data.startDeliveryPoint,
                    'endDeliveryPoint': data.endDeliveryPoint,
                    'status': status,
                    'message': message,
                    'resTimestamp': datetime.now().strftime('%Y%m%d%H%M%S')
                }
            
            # Check weather conditions first
            # weather_suitable = check_weather_conditions()
            # if not weather_suitable:
            #     return {
            #         'startDeliveryPoint': data.startDeliveryPoint,
            #         'endDeliveryPoint': data.endDeliveryPoint,
            #         'status': 0,  # Close
            #         'message': 1,  # Weather
            #         'resTimestamp': datetime.now().strftime('%Y%m%d%H%M%S')
            #     }

            # message deactivate reason code mapping (reverse mapping from code to message number)
            deactivate_reason_code_to_message = {
                'NO_ABNORMALITIES': 0,
                'WEATHER': 1,
                'CLOSED': 2,
                'UNDER_MAINTENANCE': 3,
                'IN_OPERATION': 4,
            }
            
            # Check start_terminal - first check if it exists (with deactivate_reason prefetch)
            try:
                start_terminal = Terminal.objects.select_related('deactivate_reason').get(code=data.startDeliveryPoint)
            except Terminal.DoesNotExist:
                message = 2 # Delivery route or delivery point suspended
                return {
                    'startDeliveryPoint': data.startDeliveryPoint,
                    'endDeliveryPoint': data.endDeliveryPoint,
                    'status': status,
                    'message': message,
                    'resTimestamp': datetime.now().strftime('%Y%m%d%H%M%S')
                }
            
            # Check if start_terminal is deactivated
            if not start_terminal.active:
                # Get deactivate reason code and map to message
                if start_terminal.deactivate_reason and start_terminal.deactivate_reason.code:
                    reason_code = start_terminal.deactivate_reason.code
                    message = deactivate_reason_code_to_message.get(reason_code, 2)  # Default to 2 if code not found
                else:
                    message = 2  # Default message if no reason specified
                
                return {
                    'startDeliveryPoint': data.startDeliveryPoint,
                    'endDeliveryPoint': data.endDeliveryPoint,
                    'status': status,
                    'message': message,
                    'resTimestamp': datetime.now().strftime('%Y%m%d%H%M%S')
                }
            
            # If start_terminal is active, check end_terminal (with deactivate_reason prefetch)
            try:
                end_terminal = Terminal.objects.select_related('deactivate_reason').get(code=data.endDeliveryPoint)
            except Terminal.DoesNotExist:
                message = 2 # Delivery route or delivery point suspended
                return {
                    'startDeliveryPoint': data.startDeliveryPoint,
                    'endDeliveryPoint': data.endDeliveryPoint,
                    'status': status,
                    'message': message,
                    'resTimestamp': datetime.now().strftime('%Y%m%d%H%M%S')
                }
            
            # Check if end_terminal is deactivated
            if not end_terminal.active:
                # Get deactivate reason code and map to message
                if end_terminal.deactivate_reason and end_terminal.deactivate_reason.code:
                    reason_code = end_terminal.deactivate_reason.code
                    message = deactivate_reason_code_to_message.get(reason_code, 2)  # Default to 2 if code not found
                else:
                    message = 2  # Default message if no reason specified
                
                return {
                    'startDeliveryPoint': data.startDeliveryPoint,
                    'endDeliveryPoint': data.endDeliveryPoint,
                    'status': status,
                    'message': message,
                    'resTimestamp': datetime.now().strftime('%Y%m%d%H%M%S')
                }
            
            # Check terminal open using terminal codes (not objects)
            start_terminal_status, start_terminal_message = check_terminal_open(data.startDeliveryPoint, start_terminal=True)
            end_terminal_status, end_terminal_message = check_terminal_open(data.endDeliveryPoint)
            
            if start_terminal_status == 0 or end_terminal_status == 0:
                status = 0 # Close
                # If message is 4 (all drones in operation), check if it should be 3 (maintenance)
                if start_terminal_message == 4:
                    detailed_message = check_detailed_drone_status(data.startDeliveryPoint)
                    message = detailed_message
                elif end_terminal_message == 4:
                    detailed_message = check_detailed_drone_status(data.endDeliveryPoint)
                    message = detailed_message
                else:
                    message = start_terminal_message if start_terminal_message != 0 else end_terminal_message
            else:
                status = 1 # Open
                message = 0 # Normal
            
            return {
                'startDeliveryPoint': data.startDeliveryPoint,
                'endDeliveryPoint': data.endDeliveryPoint,
                'status': status,
                'message': message,
                'resTimestamp': datetime.now().strftime('%Y%m%d%H%M%S')
            }
                
        except Exception as e:
            message = 2 #  Delivery route or delivery point suspended
            return {
                'startDeliveryPoint': data.startDeliveryPoint,
                'endDeliveryPoint': data.endDeliveryPoint,
                'status': status,
                'message': message,
                'resTimestamp': datetime.now().strftime('%Y%m%d%H%M%S')
            }

    @route.post("/orders/order/", response={200: Dict, 400: Dict, 401: Dict}, auth=CustomJWTAuth()) 
    def order_receipt(self, request: HttpRequest, data: OrderReceiptRequestSchema):
        # """
        # API 4: Order Receipt
        # This API sends (receipts) new order information from users to GuardianX by the delivery app.
        # Returns whether drone delivery is possible and expected delivery completion time.
        
        # Logic:
        # - Validate terminals by code
        # - Check drone availability  
        # - Calculate delivery ETA
        # - Return status: 0=unavailable, 1=available
        # - Return message: 0=Normal, 1=Weather, 2=Route suspended, 3=All drones maintenance, 4=All drones in operation, 5=Weight exceeded, 6=Size exceeded
        # """
        try:
            # Validate serviceKey
            is_valid, error_msg = validate_service_key(data.serviceKey)
            if not is_valid:
                return {
                    'itemOrgId': data.itemOrgId,
                    'status': 0,
                    'message': -1,  # Route suspended
                    'deliveryETA': '',
                    'resTimestamp': datetime.now().strftime('%Y%m%d%H%M%S')
                }

            # Validate terminals exist by code
            try:
                start_terminal = Terminal.objects.get(code=data.startDeliveryPoint, active=True)
                end_terminal = Terminal.objects.get(code=data.endDeliveryPoint, active=True)
            except Terminal.DoesNotExist:
                return {
                    'itemOrgId': data.itemOrgId,
                    'status': 0,
                    'message': 2,  # Route suspended (terminal not found)
                    'deliveryETA': '',
                    'resTimestamp': datetime.now().strftime('%Y%m%d%H%M%S')
                }
            
            # Step 1: Check weather conditions first (fastest check)
            weather_suitable = check_weather_conditions(request, data)
            if not weather_suitable:
                return {
                    'itemOrgId': data.itemOrgId,
                    'status': 0,
                    'message': 1,
                    'deliveryETA': '',
                    'resTimestamp': datetime.now().strftime('%Y%m%d%H%M%S')
                }
            
            # Step 2: Check terminal and drone availability using existing check_terminal_open function
            start_terminal_status, start_terminal_message = check_terminal_open(data.startDeliveryPoint, start_terminal=True)
            end_terminal_status, end_terminal_message = check_terminal_open(data.endDeliveryPoint)
            # If either terminal is closed, return immediately (fast response)
            if start_terminal_status == 0 or end_terminal_status == 0:
                # Enhanced message detection: differentiate maintenance vs operation
                if start_terminal_message == 4:
                    message = check_detailed_drone_status(data.startDeliveryPoint)
                elif end_terminal_message == 4:
                    message = check_detailed_drone_status(data.endDeliveryPoint)
                else:
                    message = start_terminal_message if start_terminal_message != 0 else end_terminal_message
                
                return {
                    'itemOrgId': data.itemOrgId,
                    'status': 0,
                    'message': message,
                    'deliveryETA': '',
                    'resTimestamp': datetime.now().strftime('%Y%m%d%H%M%S')
                }
            
            # Create order using the new method (includes automation)
            # QUY TRÌNH PHẢI THÀNH CÔNG HOÀN TOÀN - nếu automation fail thì return status=0
            success, result = AnyangOrderService.create_order_from_receipt_request(data.model_dump())
            print( success, result)
            # Initialize variables for response
            operation = None
            route = None
            drone = None
            automation_eta = ''
            automation_result_data = {}
            success_details = {}
            error_msg = ''
            user_message = ''
            error_code = ''
            step_failed = ''
            error_details = {}
            
            # Determine status and message based on automation result
            if not success:
                # Order creation or automation failed - ALWAYS return status=0
                error_msg = result.get('error', 'Unknown error')
                step_failed = result.get('step_failed', 'unknown')
                user_message = result.get('user_message', 'Lỗi hệ thống')
                error_code = result.get('error_code', 'SYSTEM_ERROR')
                error_details = result.get('error_details', {})
                
                # Determine specific error message based on failure type
                if error_code == 'ROUTE_NOT_FOUND':
                    status = 0  # Unavailable
                    message = 2  # Route suspended
                elif error_code == 'DRONE_NOT_AVAILABLE':
                    status = 0  # Unavailable
                    message = 3  # All drones under maintenance
                elif error_code == 'DUPLICATE_ORDER':
                    status = 0  # Unavailable
                    message = -1  # Duplicate order
                elif error_code == 'AUTOMATION_FAILED':
                    status = 0  # Unavailable
                    message = 2  # Route suspended (automation failure)
                elif error_code == 'CALCULATION_ERROR':
                    status = 0  # Unavailable
                    message = 2  # Route suspended (calculation failure)
                elif error_code == 'INVALID_TERMINAL':
                    status = 0  # Unavailable
                    message = 2  # Route suspended (terminal error)
                elif error_code == 'WEIGHT_EXCEEDED':
                    status = 0  # Unavailable
                    message = 5  # Weight exceeded
                elif error_code == 'SIZE_EXCEEDED':
                    status = 0  # Unavailable
                    message = 6  # Size exceeded
                else:
                    status = 0  # Unavailable
                    message = 2  # Route suspended (general failure)
                
                delivery_eta = ''
                
            
                
            else:
                # Order and automation successful - use calculated ETA
                # automation_eta = result.get('delivery_eta_formatted', '')
                automation_result_data = result.get('automation_result', {})
                operation = result.get('operation')
                # route = result.get('route')
                # drone = result.get('drone')
                success_details = result.get('success_details', {})
                
                if automation_result_data:
                    # delivery_eta = automation_eta
                    status = 1  # Available
                    message = 0  # Normal
                    
                    # Success case
                else:
                    # This should not happen since we require full automation success
                    status = 0  # Unavailable
                    message = 2  # Route suspended
                    delivery_eta = ''
                    error_details = {
                        'missing_automation_result': not automation_result_data,
                        'operation_exists': operation is not None,
                        # 'route_exists': route is not None,
                        # 'drone_exists': drone is not None
                    }
            
            # Check if this is an internal/swagger request
            is_internal_request = (
                request.META.get('HTTP_USER_AGENT', '').lower().find('swagger') != -1 or
                request.META.get('HTTP_USER_AGENT', '').lower().find('python') != -1 or
                request.META.get('HTTP_HOST', '').find('localhost') != -1 or
                request.META.get('HTTP_HOST', '').find('127.0.0.1') != -1 or
                'debug' in request.GET
            )
            
            # Prepare base response
            response_data = {
                'itemOrgId': data.itemOrgId,
                'status': status,
                'message': message,
                # 'deliveryETA': delivery_eta,
                'resTimestamp': datetime.now().strftime('%Y%m%d%H%M%S')
            }
            
            # Add detailed debug information ONLY for internal/swagger requests
      
            return response_data
                
        except Exception as e:
            print(e)
            return {
                'itemOrgId': data.itemOrgId,
                'status': 0,
                'message': -999,  # Route suspended (internal error)
                'deliveryETA': '',
                'resTimestamp': datetime.now().strftime('%Y%m%d%H%M%S')
            }

    @route.post("/orders/order/cancel", response={200: CancelOrderResponseSchema, 400: CancelOrderResponseSchema, 401: CancelOrderResponseSchema}, auth=CustomJWTAuth())
    def order_cancellation(self, request: HttpRequest, data: DeliveryCancellationSchema):
        """
        API 3: Order Cancellation (App→GX)
        Delivery app sends order cancellation callback to GuardianX
        """
        try:
            # Validate serviceKey
            is_valid, error_msg = validate_service_key(data.serviceKey)
            if not is_valid:
                CancelOrderResponseSchema(
                    itemOrgId=data.itemOrgId,
                    status=1,
                    message=0,
                    resTimestamp=datetime.now().strftime('%Y%m%d%H%M%S')
                )
            
            # Find order by delivery request ID or order code
            order = None
            try:
                # get order by another_info.item_org_id (another_info is a jsonb field)
                order = Order.objects.get(another_info__item_org_id=data.itemOrgId)
            except Order.DoesNotExist:
                try:
                    delivery_op = DeliveryOperation.objects.get(order__order_code=data.itemOrgId)
                    order = delivery_op.order
                except DeliveryOperation.DoesNotExist:
                    return CancelOrderResponseSchema(
                        itemOrgId=data.itemOrgId,
                        status=1,
                        message=0,
                        resTimestamp=datetime.now().strftime('%Y%m%d%H%M%S')
                    )
            
            # Check if order can be cancelled
            if order.status and order.status.code in ['delivered', 'cancelled', 'returned']:
                return CancelOrderResponseSchema(
                    itemOrgId=data.itemOrgId,
                    status=1,
                    message=1,
                    resTimestamp=datetime.now().strftime('%Y%m%d%H%M%S')
                )
            
            if order.status and order.status.code in ['awaiting_shipment']:
                return CancelOrderResponseSchema(
                    itemOrgId=data.itemOrgId,
                    status=1,
                    message=2,
                    resTimestamp=datetime.now().strftime('%Y%m%d%H%M%S')
                )
            
            # Update order status to cancelled
            cancelled_status = OrderStatus.objects.filter(code='cancelled').first()
            if not cancelled_status:
                cancelled_status = OrderStatus.objects.create(
                    name='Cancelled', code='cancelled'
                )
            try:
                language = get_current_request().user.language.code if get_current_request().user.language else 'en'
            except:
                language = 'en'
            cancellation_reason = CANCELLATION_REASON.get(data.message, {}).get(language, "Unknown")
            
            order.status = cancelled_status
            order.cancel_reason = cancellation_reason
            order.save()
            
            # Update delivery operations
            DeliveryOperation.objects.filter(order=order).update(
                current_status=DeliveryStatus._base_manager.filter(code='cancelled').first()
            )
            DeliveryCancellation.objects.create(
                delivery_operation=DeliveryOperation._base_manager.filter(order=order).first(),
                reason_type=DeliveryCancellationType._base_manager.get(code="user_cancelled"),
                reason=cancellation_reason,
                cancelled_by=request.user
            )
            return CancelOrderResponseSchema(
                itemOrgId=data.itemOrgId,
                status=0,
                message=0,
                resTimestamp=datetime.now().strftime('%Y%m%d%H%M%S')
            )
            
        except Exception as e:
            return CancelOrderResponseSchema(
                itemOrgId=data.itemOrgId,
                status=1,
                message=0,
                resTimestamp=datetime.now().strftime('%Y%m%d%H%M%S')
            )

    @route.post("/orders/order/drone-location", auth=CustomJWTAuth())
    def drone_location_request(self, request: HttpRequest, data: DroneLocationRequestSchema):
        """
        API 4: Drone Location Request
        Delivery app requests drone location from GuardianX
        """
        try:
            itemOrgId = data.itemOrgId
            
            # Find order
            order = None
            if itemOrgId:
                try:
                    order = Order.objects.get(another_info__item_org_id=itemOrgId)
                except Order.DoesNotExist:
                    return format_anyang_drone_location_response(
                        itemOrgId=itemOrgId,
                        latitude=None,
                        longitude=None,
                        deliveryETA=None,
                        resTimestamp=None
                    )
            else:
                return format_anyang_drone_location_response(
                    itemOrgId=itemOrgId,
                    latitude=None,
                    longitude=None,
                    deliveryETA=None,
                    resTimestamp=None
                )
            
            if not order:
                return format_anyang_drone_location_response(
                    itemOrgId=itemOrgId,
                    latitude=None,
                    longitude=None,
                    deliveryETA=None,
                    resTimestamp=None
                )
            
            # Get delivery operation and drone info
            delivery_operation = DeliveryOperation._base_manager.filter(order=order).first()
            delivery_item = DeliveryOperationItem._base_manager.filter(delivery_operation=delivery_operation).first()
            selected_device = delivery_item.drone
            
            if not delivery_operation:
                return format_anyang_drone_location_response(
                    itemOrgId=itemOrgId,
                    latitude=None,
                    longitude=None,
                    deliveryETA=None,
                    resTimestamp=None
                )

            drone_location = ProcessingService.get_lat_long_drone(selected_device.unit_id)
            # get delivery_eta_formatted from delivery_operation.another_info.anyang.automation_result
            delivery_eta_formatted = delivery_operation.another_info.get('anyang', {}).get('automation_result', {}).get('delivery_eta_formatted', None)
            
            return format_anyang_drone_location_response(
                itemOrgId=itemOrgId,
                latitude=drone_location.get('latitude', 0),
                longitude=drone_location.get('longitude', 0),
                deliveryETA=delivery_eta_formatted,
                resTimestamp=delivery_eta_formatted
            )
            
        except Exception as e:
            return format_anyang_drone_location_response(
                itemOrgId=None,
                latitude=None,
                longitude=None,
                deliveryETA=None,
                resTimestamp=None
            )


# ============================================================================
# GUARDIAN X → DELIVERY APP CONTROLLER (Outbound APIs)
# ============================================================================

@api_controller("", tags=["Anyang - GuardianX Outbound APIs (GuardianX → Delivery App)"])
class AnyangGuardianXController:
    """Controller for APIs that send requests to Anyang Delivery App"""

    @route.post("/callback", response={200: OrderDeliveryStatusCallbackResponseSchema, 400: OrderDeliveryStatusCallbackResponseSchema}, auth=CustomJWTAuth())
    def order_delivery_status_alert(self, request: HttpRequest, data: OrderDeliveryStatusCallbackSchema):
        """
        API 5.1: Order/Delivery Status Change Alert (GuardianX → Delivery App)
        Send real-time notifications of order/delivery status changes to Anyang delivery app
        Authentication via serviceKey in request body
        """
        try:
            # Validate serviceKey
            is_valid, error_msg = validate_service_key(data.serviceKey)
            if not is_valid:
                return OrderDeliveryStatusCallbackResponseSchema(
                    itemOrgId=data.itemOrgId,
                    code=1,  # Error code
                    message="Invalid service key",
                    resTimestamp=datetime.now().strftime('%Y%m%d%H%M%S')
                )
            
            # Prepare callback data according to API specification
            callback_data = {
                'serviceKey': data.serviceKey,
                'itemOrgId': data.itemOrgId,
                'deliveryStatus': data.deliveryStatus,
                'message': data.message,
                'updateTime': data.updateTime
            }
            
            # Add deliveryPhoto if provided (for delivery completion)
            if data.deliveryPhoto:
                callback_data['deliveryPhoto'] = {
                    'url': data.deliveryPhoto.url,
                    'timestamp': data.deliveryPhoto.timestamp
                }
            else:
                callback_data['deliveryPhoto'] = {}
            
            # Get target URL for external Delivery App
            target_url = get_anyang_target_url()
            
            # Send to external Delivery App
            try:
                response = requests.post(
                    f"{target_url}/callback",
                    json=callback_data,
                    headers={
                        'Content-Type': 'application/json',
                        # No Authorization header - authentication via serviceKey in body
                    },
                    timeout=30
                )
                
                # Parse response from external system
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        # External API should return: itemOrgId, code, message, resTimestamp
                        return OrderDeliveryStatusCallbackResponseSchema(
                            itemOrgId=response_data.get('itemOrgId', data.itemOrgId),
                            code=response_data.get('code', 0),  # 0 = success
                            message=response_data.get('message', ''),
                            resTimestamp=response_data.get('resTimestamp', datetime.now().strftime('%Y%m%d%H%M%S'))
                        )
                    except (ValueError, KeyError) as e:
                        return OrderDeliveryStatusCallbackResponseSchema(
                            itemOrgId=data.itemOrgId,
                            code=1,  # Error code
                            message="Invalid response from external system",
                            resTimestamp=datetime.now().strftime('%Y%m%d%H%M%S')
                        )
                else:
                    return OrderDeliveryStatusCallbackResponseSchema(
                        itemOrgId=data.itemOrgId,
                        code=1,  # Error code
                        message=f"External API error: {response.status_code}",
                        resTimestamp=datetime.now().strftime('%Y%m%d%H%M%S')
                    )
                    
            except requests.exceptions.RequestException as e:
                return OrderDeliveryStatusCallbackResponseSchema(
                    itemOrgId=data.itemOrgId,
                    code=1,  # Error code
                    message="Failed to connect to external delivery app",
                    resTimestamp=datetime.now().strftime('%Y%m%d%H%M%S')
                )
                
        except Exception as e:
            return OrderDeliveryStatusCallbackResponseSchema(
                itemOrgId=getattr(data, 'itemOrgId', 'UNKNOWN'),
                code=1,  # Error code
                message="Internal server error",
                resTimestamp=datetime.now().strftime('%Y%m%d%H%M%S')
            )

    @route.post("/DroneBaseStation", response={200: BaseResponseSchema, 400: BaseResponseSchema}, auth=CustomJWTAuth())
    def drone_base_status_change(self, request: HttpRequest, data: DroneBaseStatusSchema):
        """
        API 2: Drone Base Status Change
        Send base status change alert to delivery app
        Authentication via serviceKey in request body
        """
        try:
            target_url = get_anyang_target_url()
            print(f"target_url: {target_url}")

            base_status_data = {
                'serviceKey': data.serviceKey,
                'startDeliveryPoint': data.startDeliveryPoint,
                'status': data.status,
                'message': data.message,
                'updateTime': data.updateTime
            }
            
            # Send to external Delivery App
            response = requests.post(
                f"{target_url}/DroneBaseStation",
                json=base_status_data,
                headers={
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                # Safely parse JSON response
                external_response = {}
                if response.content:
                    try:
                        external_response = response.json()
                    except (ValueError, requests.exceptions.JSONDecodeError, json.JSONDecodeError) as e:
                        logger.warning(f"Invalid JSON response from external API: {str(e)}")
                        external_response = {'raw_content': response.text}
                
                return format_anyang_response(
                    status='success',
                    message='Base status alert sent successfully',
                    data={'externalResponse': external_response}
                )
            else:
                return format_anyang_response(
                    status='error',
                    message=f'Failed to send base status alert. External API returned: {response.status_code}',
                    error_code='EXTERNAL_API_ERROR'
                )
                
        except requests.exceptions.RequestException as e:
            logger.error(f"External API call failed: {str(e)}")
            return format_anyang_response(
                status='error',
                message='Failed to connect to external delivery app',
                error_code='EXTERNAL_CONNECTION_ERROR'
            )
                
        except Exception as e:
            return format_anyang_response(
                status='error', 
                message='Internal server error',
                error_code='INTERNAL_001'
            )

    @route.post("/DroneUserNotice", response={200: BaseResponseSchema, 400: BaseResponseSchema}, auth=CustomJWTAuth())
    def user_notice(self, request: HttpRequest, data: UserNoticeSchema):
        """
        API 3: User Notice
        Send user notice change alert to delivery app
        Authentication via serviceKey in request body
        
        Request Parameters:
        - serviceKey: Service key for authentication
        - BCode: Anyang area legal dong code (e.g., "4117")
        - IsNotice: Notice usage (1: use, 0: not use)
        - Html1: HTML for banner notice
        - Html2: HTML for order change notice  
        - Html3: Additional HTML (optional)
        """
        try:
            # Validate serviceKey
            is_valid, error_msg = validate_service_key(data.serviceKey)
            if not is_valid:
                return format_anyang_response(
                    status='error',
                    message='Invalid service key',
                    error_code='AUTH_ERROR'
                )
            
            request_data = data.model_dump()
            target_url = get_anyang_target_url()
            
            # Prepare user notice data according to API specification
            user_notice_data = {
                'serviceKey': request_data.get('serviceKey'),
                'BCode': request_data.get('BCode'),
                'IsNotice': request_data.get('IsNotice'),
                'Html1': request_data.get('Html1', ''),
                'Html2': request_data.get('Html2', ''),
                'Html3': request_data.get('Html3', '')
            }
            
            # Send to external Delivery App
            try:
                response = requests.post(
                    f"{target_url}/DroneUserNotice", 
                    json=user_notice_data,
                    headers={
                        'Content-Type': 'application/json',
                    },
                    timeout=30
                )
                
                # Safely handle response parsing to avoid JSON decode errors
                try:
                    if response.headers.get('content-type', '').startswith('application/json'):
                        response_data = response.json()
                        print(f"response: {response_data}")
                    else:
                        response_data = response.text
                        print(f"response (non-JSON): {response_data}")
                except json.JSONDecodeError as e:
                    response_data = response.text
                    print(f"response (JSON decode failed): {response_data}")
                    print(f"JSON decode error: {str(e)}")
                
                # Handle response according to API specification
                if response.status_code == 200:
                    try:
                        # Try to parse JSON response, fallback to raw text if failed
                        if response.headers.get('content-type', '').startswith('application/json'):
                            external_response = response.json()
                        else:
                            external_response = {'raw_response': response.text}
                    except json.JSONDecodeError:
                        external_response = {'raw_response': response.text}
                    
                    return format_anyang_response(
                        status='success',
                        message='User notice sent successfully',
                        data={'externalResponse': external_response}
                    )
                else:
                    return format_anyang_response(
                        status='error',
                        message=f'Failed to send user notice. External API returned: {response.status_code}',
                        error_code='EXTERNAL_API_ERROR'
                    )
                        
            except requests.exceptions.RequestException as e:
                logger.error(f"External API call failed: {str(e)}")
                return format_anyang_response(
                    status='error',
                    message='Failed to connect to external delivery app',
                    error_code='EXTERNAL_CONNECTION_ERROR'
                )
                
        except Exception as e:
            logger.error(f"User notice error: {str(e)}")
            return format_anyang_response(
                status='error', 
                message='Internal server error',
                error_code='INTERNAL_001'
            )

    @route.post("/delivery/confirmation/{operation_id}/photo/", auth=CustomJWTAuth())
    def upload_delivery_confirmation_photo(self, request: HttpRequest, operation_id: int):
        """
        Upload delivery confirmation photo and mark delivery as completed
        """
        try:
            from django.http import JsonResponse
            from django.shortcuts import get_object_or_404
            from django.db import transaction
            from datetime import datetime
            from core.file_management.helper import FileHelper
            
            # Get delivery operation
            delivery_operation = get_object_or_404(DeliveryOperation, id=operation_id)
            
            # Check if this is an Anyang order
            if not AnyangCallbackService.should_send_callback(delivery_operation):
                return JsonResponse({"error": "Not an Anyang order"}, status=404)
            
            # Check if photo file is provided
            if 'photo' not in request.FILES:
                return JsonResponse({"error": "No photo file provided"}, status=400)
            
            photo_file = request.FILES['photo']
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            if photo_file.content_type not in allowed_types:
                return JsonResponse({"error": "Invalid file type. Only JPEG, PNG, WEBP allowed"}, status=400)
            
            # Validate file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if photo_file.size > max_size:
                return JsonResponse({"error": "File too large. Max 10MB allowed"}, status=400)
            
            # Get completed status
            completed_status = DeliveryStatus.objects.filter(code='completed_order').first()
            if not completed_status:
                completed_status = DeliveryStatus.objects.create(
                    name='Completed Order',
                    code='completed_order'
                )
            
            # Save photo and mark as completed
            status_changed = False
            old_status_code = None
            
            with transaction.atomic():
                # Delete old confirmation photo if exists
                if delivery_operation.confirmation_photo:
                    delivery_operation.confirmation_photo.delete()
                
                # Upload new photo using FileHelper (similar to avatar upload)
                avatar_file = FileHelper.user_upload_s3(
                    request.user, 
                    photo_file, 
                    is_avatar=False,  # This is not an avatar
                    only_image=True   # Only allow images
                )
                
                # Save the new photo
                delivery_operation.confirmation_photo = avatar_file
                
                # Mark as completed if not already
                if delivery_operation.current_status.code != 'completed_order':
                    old_status_code = delivery_operation.current_status.code
                    delivery_operation.current_status = completed_status
                    delivery_operation.actual_delivery_time = datetime.now()
                    status_changed = True
                
                delivery_operation.save()
                
                logger.info(f"📷 Photo uploaded for delivery {operation_id}: {photo_file.name}")
                if status_changed:
                    logger.info(f"📷 Delivery completed: {old_status_code} → completed_order")
            
            return JsonResponse({
                "success": True,
                "message": "Photo uploaded and delivery completed",
                "data": {
                    "operation_id": operation_id,
                    "photo_url": delivery_operation.confirmation_photo.url if delivery_operation.confirmation_photo else None,
                    "status_changed": status_changed,
                    "old_status": old_status_code,
                    "new_status": "completed_order",
                    "completion_time": delivery_operation.actual_delivery_time.isoformat() if delivery_operation.actual_delivery_time else None
                }
            })
            
        except Exception as e:
            return JsonResponse({"error": "Internal server error"}, status=500)

    @route.get("/delivery/confirmation/{operation_id}/photo/", auth=CustomJWTAuth())
    def delivery_confirmation_photo(self, request: HttpRequest, operation_id: int):
        """
        Serve delivery confirmation photo for completed deliveries
        Priority: uploaded photo > auto-generated photo
        If no uploaded photo and not completed, auto-complete and generate photo
        """
        try:
            from django.http import HttpResponse
            from django.shortcuts import get_object_or_404
            from PIL import Image, ImageDraw, ImageFont
            import io
            from datetime import datetime
            from django.db import transaction
            from django.conf import settings
            
            # Get delivery operation
            delivery_operation = get_object_or_404(DeliveryOperation, id=operation_id)
            
            # Check if this is an Anyang order
            if not AnyangCallbackService.should_send_callback(delivery_operation):
                return HttpResponse("Not an Anyang order", status=404)
            
            # Get completed status
            completed_status = DeliveryStatus.objects.filter(
                code='completed_order'
            ).first()
            
            completed_status = DeliveryStatus.objects.filter(code='completed_order').first()
            if not completed_status:
                completed_status = DeliveryStatus.objects.create(
                    name='Completed Order',
                    code='completed_order'
                )
            
            # Auto-complete delivery if not already completed
            status_changed = False
            old_status_code = None
            
            with transaction.atomic():
                if delivery_operation.current_status.code not in ['completed_order']:
                    old_status_code = delivery_operation.current_status.code
                    
                    # Store photo URL in another_info BEFORE changing status
                    another_info = delivery_operation.another_info or {}
                    if 'anyang' not in another_info:
                        another_info['anyang'] = {}
                    
                    # Store photo URL for callback
                    photo_url = f"{getattr(settings, 'SITE_URL', 'https://guardianx.com')}/api/delivery/confirmation/{operation_id}/photo/"
                    another_info['anyang']['delivery_photo'] = {
                        'url': photo_url,
                        'timestamp': datetime.now().strftime('%Y%m%d%H%M%S'),
                        'source': 'auto_completion_endpoint',
                        'auto_generated': True
                    }
                    
                    # Set flag to prevent signal conflicts
                    another_info['anyang']['auto_completing'] = True
                    
                    # Save photo info first (this won't trigger callback because status unchanged)
                    delivery_operation.another_info = another_info
                    delivery_operation.save()
                    
                    # Update ONLY delivery status - Order will sync automatically via signals
                    delivery_operation.current_status = completed_status
                    
                    # Remove auto_completing flag and save (this WILL trigger signal)
                    del another_info['anyang']['auto_completing']
                    delivery_operation.another_info = another_info
                    delivery_operation.save()  # This triggers post_save signal with photo ready
                    
                    status_changed = True
                    logger.info(f"📷 Auto-completed delivery {operation_id}: {old_status_code} → completed_order")
                    logger.info(f"📷 Photo URL stored: {photo_url}")
                    logger.info(f"📷 Order status will sync automatically via signals")
            
            # Generate delivery confirmation image
            img_width, img_height = 800, 600
            img = Image.new('RGB', (img_width, img_height), color='white')
            draw = ImageDraw.Draw(img)
            
            try:
                # Try to use a nice font
                font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 36)
                font_medium = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
                font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
            except:
                # Fallback to default font
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Draw header
            draw.rectangle([(0, 0), (img_width, 80)], fill='#4CAF50')
            header_text = 'DELIVERY COMPLETED'
            if status_changed:
                header_text += ' ✓'
            draw.text((50, 25), header_text, font=font_large, fill='white')
            
            # Draw order information
            y_pos = 120
            order = delivery_operation.order
            anyang_info = delivery_operation.another_info.get('anyang', {}) if delivery_operation.another_info else {}
            
            info_items = [
                ('Order ID:', anyang_info.get('itemOrgId', 'N/A')),
                ('Order Code:', order.order_code if order else 'N/A'),
                ('Completion Time:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                ('Status:', 'Delivery Completed'),
                ('Delivery Method:', 'Drone Delivery'),
            ]
            
            if order:
                info_items.extend([
                    ('Recipient:', order.recipient_name or 'N/A'),
                    ('Address:', (order.recipient_address.full_address if order.recipient_address else 'N/A')[:50] + '...')
                ])
            
            # Add status change notification if applicable
            if status_changed:
                info_items.insert(3, ('Status Updated:', 'Auto-completed via photo access'))
            
            for label, value in info_items:
                draw.text((50, y_pos), label, font=font_medium, fill='#333333')
                draw.text((250, y_pos), str(value), font=font_medium, fill='#666666')
                y_pos += 40
            
            # Draw footer
            draw.rectangle([(0, img_height-60), (img_width, img_height)], fill='#2196F3')
            draw.text((50, img_height-40), 'GuardianX Drone Delivery System', font=font_small, fill='white')
            footer_right = f'ID: {operation_id}'
            if status_changed:
                footer_right += ' [Auto-Completed]'
            draw.text((img_width-250, img_height-40), footer_right, font=font_small, fill='white')
            
            # Save image to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=85)
            img_bytes.seek(0)
            
            # Return image response
            response = HttpResponse(img_bytes, content_type='image/jpeg')
            response['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
            response['Content-Disposition'] = f'inline; filename="delivery_confirmation_{operation_id}.jpg"'
            
            # Add custom headers to indicate status change
            if status_changed:
                response['X-Status-Changed'] = 'true'
                response['X-Previous-Status'] = old_status_code
                response['X-New-Status'] = 'completed_order'
                response['X-Callback-Status'] = 'triggered'
            
            return response
            
        except Exception as e:
            return HttpResponse("Error generating photo", status=500)


# Export controllers for direct import
__all__ = [
    'AnyangDeliveryAppController',
    'AnyangGuardianXController',
]