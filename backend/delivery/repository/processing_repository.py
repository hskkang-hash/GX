from typing import Any, Dict, Optional, List

from delivery.schemas.schemas_djantic_in import CancelAwaitingOrderInSchema
from terminals.models import RouteTerminal, Terminal
from devices.models import CargoCompartments, DeviceStatus
from delivery.models import (
    DeliveryCancellationType,
    DeliveryOperationApprovalChecklist,
    DeliveryStatus, 
    DeliveryOperation, 
    DeliveryOperationItem,
    PackagingSpecification,
    Routes,
    Device,
    DeliveryCancellation,
    TerminalSequence
)
from orders.models import DeliveryEvent, Order, OrderAssignment, OrderHistory, OrderItem, OrderStatus, Payment
from django.utils import timezone
from django.db.models import QuerySet, OuterRef, Subquery, Count, Case, When, Value, CharField, F, IntegerField, Q, BooleanField
from django.db.models.functions import Coalesce, Concat, Round

# Multi-language support for drone disable reasons
class DroneDisableReasons:
    """
    Multi-language support for drone disable reasons
    """
    
    @staticmethod
    def get_reason(reason_type: str, language: str = 'en', **params) -> dict:
        """
        Get detailed reason message in specified language
        
        Args:
            reason_type: Type of reason (busy, missing_weight, missing_dims, insufficient_weight, insufficient_dims)
            language: Language code ('en' or 'ko')
            **params: Additional parameters for formatting
        
        Returns:
            dict: Formatted reason with type, code, and message
        """
        reasons = {
            'busy_select_drone': {
                'en': {
                    'type': 'busy',
                    'code': 'BUSY_DRONE_SELECTION',
                    'message': 'Drone is currently being selected for another delivery operation',
                    'detailed_message': 'This drone is currently in the selection process for another delivery. Please wait until the selection is complete or choose another drone.'
                },
                'ko': {
                    'type': 'busy',
                    'code': 'BUSY_DRONE_SELECTION', 
                    'message': '다른 배송 작업을 위해 드론이 선택되고 있습니다',
                    'detailed_message': '이 드론은 현재 다른 배송을 위한 선택 과정에 있습니다. 선택이 완료될 때까지 기다리거나 다른 드론을 선택해주세요.'
                },
                'th': {
                    'type': 'busy',
                    'code': 'BUSY_DRONE_SELECTION',
                    'message': 'หุ่นยนต์กำลังถูกเลือกสำหรับการจัดส่งอื่น',
                    'detailed_message': 'หุ่นยนต์นี้กำลังอยู่ในขั้นตอนการเลือกสำหรับการจัดส่งอื่น ๆ โปรดรอจนกว่าจะเลือกเสร็จหรือเลือกหุ่นยนต์อื่น'
                }
                
            },
            'busy_in_transit': {
                'en': {
                    'type': 'busy',
                    'code': 'BUSY_IN_TRANSIT',
                    'message': 'Drone is currently performing another delivery',
                    'detailed_message': 'This drone is actively performing a delivery mission and is not available for new assignments until the current delivery is completed.'
                },
                'ko': {
                    'type': 'busy',
                    'code': 'BUSY_IN_TRANSIT',
                    'message': '드론이 현재 다른 배송을 수행 중입니다',
                    'detailed_message': '이 드론은 현재 배송 임무를 수행 중이며, 현재 배송이 완료될 때까지 새로운 배정이 불가능합니다.'
                },
                'th': {
                    'type': 'busy',
                    'code': 'BUSY_IN_TRANSIT',
                    'message': 'หุ่นยนต์กำลังทำงานการจัดส่งอื่น',
                    'detailed_message': 'หุ่นยนต์นี้กำลังทำงานการจัดส่งอื่น ๆ และไม่พร้อมสำหรับการจัดส่งใหม่จนกว่าการจัดส่งปัจจุบันจะเสร็จสิ้น'
                }
            },
            'missing_weight_capacity': {
                'en': {
                    'type': 'configuration_error',
                    'code': 'MISSING_WEIGHT_DATA',
                    'message': 'Weight capacity data is not configured for this drone',
                    'detailed_message': 'The drone\'s weight capacity information is missing from the system configuration. Please contact the administrator to configure the drone specifications.'
                },
                'ko': {
                    'type': 'configuration_error', 
                    'code': 'MISSING_WEIGHT_DATA',
                    'message': '이 드론의 중량 용량 데이터가 구성되지 않았습니다',
                    'detailed_message': '시스템 구성에서 드론의 중량 용량 정보가 누락되었습니다. 드론 사양을 구성하려면 관리자에게 문의하세요.'
                },
                'th': {
                    'type': 'configuration_error',
                    'code': 'MISSING_WEIGHT_DATA',
                    'message': 'ข้อมูลความจุน้ำหนักของโดรนไม่ถูกต้อง',
                    'detailed_message': 'ข้อมูลความจุน้ำหนักของโดรนจะขาดหายไปจากการกำหนดค่าในระบบ โปรดติดต่อผู้ดูแลระบบเพื่อกำหนดค่าสำหรับโดรน'
                }
            },
            'missing_dimensions': {
                'en': {
                    'type': 'configuration_error',
                    'code': 'MISSING_DIMENSIONS_DATA', 
                    'message': 'Dimensions data is not configured for this drone',
                    'detailed_message': 'The drone\'s cargo compartment dimensions are missing from the system configuration. Please contact the administrator to configure the drone specifications.'
                },
                'ko': {
                    'type': 'configuration_error',
                    'code': 'MISSING_DIMENSIONS_DATA',
                    'message': '이 드론의 치수 데이터가 구성되지 않았습니다', 
                    'detailed_message': '시스템 구성에서 드론의 화물 구획 치수가 누락되었습니다. 드론 사양을 구성하려면 관리자에게 문의하세요.'
                },
                'th': {
                    'type': 'configuration_error',
                    'code': 'MISSING_DIMENSIONS_DATA',
                    'message': 'ข้อมูลขนาดของโดรนไม่ถูกต้อง',
                    'detailed_message': 'ข้อมูลขนาดของโดรนจะขาดหายไปจากการกำหนดค่าในระบบ โปรดติดต่อผู้ดูแลระบบเพื่อกำหนดค่าสำหรับโดรน'
                }
            },
            'insufficient_weight': {
                'en': {
                    'type': 'capacity_limitation',
                    'code': 'INSUFFICIENT_WEIGHT_CAPACITY',
                    'message': 'Drone weight capacity is insufficient for this package',
                    'detailed_message': f'Package weight ({params.get("package_weight", "N/A")}kg) exceeds drone capacity ({params.get("drone_capacity", "N/A")}kg). Please choose a drone with higher weight capacity.'
                },
                'ko': {
                    'type': 'capacity_limitation',
                    'code': 'INSUFFICIENT_WEIGHT_CAPACITY', 
                    'message': '이 패키지에 대한 드론 중량 용량이 부족합니다',
                    'detailed_message': f'패키지 중량({params.get("package_weight", "N/A")}kg)이 드론 용량({params.get("drone_capacity", "N/A")}kg)을 초과합니다. 더 높은 중량 용량의 드론을 선택해주세요.'
                },
                'th': {
                    'type': 'capacity_limitation',
                    'code': 'INSUFFICIENT_WEIGHT_CAPACITY',
                    'message': 'ความจุน้ำหนักของโดรนไม่เพียงพอสำหรับพัสดุนี้',
                    'detailed_message': f'น้ำหนักของพัสดุ({params.get("package_weight", "N/A")}kg)มากกว่าความจุน้ำหนักของโดรน({params.get("drone_capacity", "N/A")}kg). โปรดเลือกโดรนที่มีความจุน้ำหนักสูงกว่านี้.'
                }
            },
            'insufficient_dimensions': {
                'en': {
                    'type': 'capacity_limitation',
                    'code': 'INSUFFICIENT_DIMENSIONS',
                    'message': 'Drone cargo compartment is too small for this package',
                    'detailed_message': f'Package dimensions ({params.get("package_dims", "N/A")}mm) exceed drone compartment size ({params.get("drone_dims", "N/A")}mm). Please choose a drone with larger cargo compartment.'
                },
                'ko': {
                    'type': 'capacity_limitation', 
                    'code': 'INSUFFICIENT_DIMENSIONS',
                    'message': '이 패키지에 대한 드론 화물 구획이 너무 작습니다',
                    'detailed_message': f'패키지 치수({params.get("package_dims", "N/A")}mm)가 드론 구획 크기({params.get("drone_dims", "N/A")}mm)를 초과합니다. 더 큰 화물 구획의 드론을 선택해주세요.'
                },
                'th': {
                    'type': 'capacity_limitation',
                    'code': 'INSUFFICIENT_DIMENSIONS',
                    'message': 'ขนาดของโดรนจะขาดหายไปจากการกำหนดค่าในระบบ โปรดติดต่อผู้ดูแลระบบเพื่อกำหนดค่าสำหรับโดรน',
                    'detailed_message': f'ขนาดของพัสดุ({params.get("package_dims", "N/A")}mm)มากกว่าขนาดของโดรนจะขาดหายไปจากการกำหนดค่าในระบบ โปรดติดต่อผู้ดูแลระบบเพื่อกำหนดค่าสำหรับโดรน'
                }
                
            }
        }
        
        return reasons.get(reason_type, {}).get(language, reasons.get(reason_type, {}).get('en', {
            'type': 'unknown',
            'code': 'UNKNOWN_REASON',
            'message': 'Unknown disable reason',
            'detailed_message': 'The reason for disabling this drone is not specified.'
        }))
from geopy.distance import distance as geopy_distance
from terminals.schemas.schemas_djantic_out import RouteOutSchema
from core.multilanguage.request_handlers import create_model_with_translations
from django.contrib.postgres.aggregates import ArrayAgg
from datetime import datetime, timedelta
import logging
from delivery.services.status_mapping_service import StatusMappingService
from devices.utils import convert_unit
from core.middleware.refresh_token import get_current_request
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class ProcessingRepository:
    @staticmethod
    def cancel_awaiting_order(data: CancelAwaitingOrderInSchema):
        from orders.services.order_service import OrderService
        operations = DeliveryOperation.objects.filter(order_id__in=data.order_ids)
        if any(operation.current_status.code == "in_transit_processing" or operation.current_status.code == "completed_order" for operation in operations):
            return False, operations
        user = get_current_request().user
        for operation in operations:
            operation.current_status = DeliveryStatus.objects.get(code="receipt_cancelled")
            operation.save()
            operation.order.cancel_reason = data.reason_note
            operation.order.status = OrderStatus.objects.filter(code="cancelled").first()
            operation.order.save()
            drone = operation.items.first().drone if operation.items.first() and operation.items.first().drone else None
            if drone:
                drone.approve_flight_now = False
                drone.on_approve_flight = False
                drone.save()
            operation.items.update(is_drone_approved=False)
            operation.items.update(is_arrived=False)
            operation.items.update(is_delivered=False)
            operation.items.update(drone_arrived_at=None)
            operation.items.update(arrived_at=None)
            operation.items.update(delivered_at=None)
            operation.items.update(drone=None)
            DeliveryCancellation.objects.create(
                delivery_operation=operation,
                reason_type=DeliveryCancellationType.objects.get(code="user_cancelled"),
                reason=data.reason_note,
                cancelled_by=user
            )
            
            OrderService.create_order_history(operation.order.id, user.username, "receipt_cancelled")  
            print(f"🚁 [CANCEL_AWAITING_ORDER] Order {operation.order.id} cancelled by user {user.username}")
        return True, operations
    
    @staticmethod
    def _get_base_annotations():
        """Helper method to get common annotations including status mapping"""
        # Get mapping annotations from StatusMappingService
        mapping_annotations = StatusMappingService.build_annotate_with_mapping(context='delivery_operation')
        return mapping_annotations
    
    @staticmethod
    def get_processing_statuses() -> QuerySet:
        return DeliveryStatus.objects.filter(code__in=[
            "select_route_processing", 
            "select_drone_processing", 
            "in_transit_processing"
        ])

    @staticmethod
    def get_items_by_processing(operation_id: int) -> QuerySet:
        return DeliveryOperationItem.objects.filter(delivery_operation_id=operation_id)
    
    @staticmethod
    def get_list_of_drones_by_package_id(package_id: int, status: str, route_id: int = None, language: str = 'en') -> list:
        try:
            print(f"🚁 [DRONE_SEARCH] Starting drone search for package {package_id}, route {route_id}")
            
            # Get delivery item and package
            delivery_item = DeliveryOperationItem.objects.get(id=package_id)
            selected_package = delivery_item.order_item.package_id
            print(f"📦 [DRONE_SEARCH] Selected package: {selected_package.name}, {selected_package.id}")
            
            # Get package measurements
            weight_measurement, length_measurement, width_measurement, height_measurement = ProcessingRepository.get_package_weight_dimensions(package_id)
            package_weight = weight_measurement.get("value", 0)
            package_weight_unit = weight_measurement.get("unit", "kg")
            # Normalize package weight to kg
            package_weight_kg = convert_unit(float(package_weight or 0), package_weight_unit, "kg")
            # Normalize package dimensions to mm
            pkg_len_mm = convert_unit(float(length_measurement.get("value", 0) or 0), length_measurement.get("unit", "mm"), "mm")
            pkg_w_mm = convert_unit(float(width_measurement.get("value", 0) or 0), width_measurement.get("unit", "mm"), "mm")
            pkg_h_mm = convert_unit(float(height_measurement.get("value", 0) or 0), height_measurement.get("unit", "mm"), "mm")
            print(f"✅ [DRONE_SEARCH] Package: {package_weight_kg}kg, dims: {pkg_len_mm}x{pkg_w_mm}x{pkg_h_mm}mm")
            
            # Get device status
            device_status = DeviceStatus.objects.get(code=status)
            print(f"✅ [DRONE_SEARCH] Device status: {device_status.name}")
            
            # Get potential drones
            
            potential_drones = Device.objects.filter(
                status=device_status, 
                active=True,
                # NEW FILTER: Only drones linked to this specific package
                # packaging_specification_device__option__specifications__package=selected_package
            ).distinct().select_related(
                'main_type', 
                'terminal'
            ).prefetch_related(
                'cargo_compartments__measurements',
                'packaging_specification_device',
                'delivery_items__delivery_operation__current_status',  # Add for busy status check
            ).order_by('-id')
            
            print(f"🔍 [DRONE_SEARCH] Found {potential_drones.count()} total drones for package {selected_package.name}, {selected_package.id}")
            
            # Get route starting terminal
            
            route_starting_terminal = None
            is_hub = False
            if route_id:
                try:
                    route = Routes.objects.get(id=route_id)
                    route_starting_terminal = ProcessingRepository.get_route_starting_terminal(route)
                    if route_starting_terminal:
                        print(f"📍 [DRONE_SEARCH] Route starting terminal: {route_starting_terminal.name} (ID: {route_starting_terminal.id})")
                        # Check if starting terminal is a hub
                        is_hub = route_starting_terminal.terminal_types.filter(code='DELIVERY_HUB').exists()
                        print(f"🏢 [DRONE_SEARCH] Starting terminal is hub: {is_hub}")
                except Routes.DoesNotExist:
                    print(f"⚠️ [DRONE_SEARCH] Route {route_id} not found")
                    pass
            
            # Apply conditional hub filtering
            if is_hub and route_starting_terminal:
                # Filter to only include drones at the route starting terminal (which is a hub)
                potential_drones = potential_drones.filter(terminal=route_starting_terminal)
                print(f"✅ [HUB_FILTER] Filtered to drones at starting hub terminal: {route_starting_terminal.name}")
            elif is_hub and not route_starting_terminal:
                # If is_hub but no route_starting_terminal, return empty list
                potential_drones = potential_drones.none()
                print(f"❌ [HUB_FILTER] is_hub=True but no route_starting_terminal found - returning empty list")
            else:
                # If not hub route, keep all drones (no additional filtering)
                print(f"ℹ️ [HUB_FILTER] Not a hub route - keeping all {potential_drones.count()} drones")
            
            # Extract drone data from pre-fetched ORM data
            all_drone_capacities, all_drone_dimensions, all_drone_batteries, all_drone_models = ProcessingRepository._extract_drone_data_from_orm(potential_drones)
            
            # Process and filter drones
            print(f"🔍 [DRONE_PROCESS] Processing drones for suitability...")
            
            # Initialize drone_positions dictionary
            # drone_positions = {}
            
            # Get all drone unit_ids for batch query
            drone_unit_ids = [drone.unit_id for drone in potential_drones]
            
            # Execute single batch query
            # try:
            #     from delivery.services.processing_service import ProcessingService
            #     batch_positions = ProcessingService.get_drone_positions_batch(drone_unit_ids)
                
            #     # Convert to drone.id mapping
            #     for drone in potential_drones:
            #         position_data = batch_positions.get(drone.unit_id, {})
            #         drone_positions[drone.id] = {
            #             'position': position_data,
            #             'api_time': 0,  # Will be calculated below
            #             'success': bool(position_data.get('latitude') or position_data.get('longitude'))
            #         }
                
            #     batch_time = (time.time() - batch_start) * 1000
            #     total_api_call_time = batch_time
            #     print(f"      ✅ [BATCH-QUERY] All positions fetched in {batch_time:.2f}ms")
                
            #     # Log individual drone positions
            #     for drone in potential_drones:
            #         position_data = drone_positions[drone.id]['position']
            #         print(f"         📍 [BATCH] Drone {drone.unit_id}: {position_data.get('latitude', 0)}, {position_data.get('longitude', 0)}")
                    
            # except Exception as e:
            #     print(f"      ❌ [BATCH-QUERY] Batch query failed: {str(e)}")
            #     # Fallback: create empty positions
            #     for drone in potential_drones:
            #         drone_positions[drone.id] = {
            #             'position': {'latitude': 0, 'longitude': 0},
            #             'api_time': 0,
            #             'success': False
            #         }
            
            # Filter drones by weight capacity and add capacity information
            hub_drones = []
            nearby_drones = []
            # other_drones = []
            processed_count = 0
            
            # OPTIMIZATION: Get route starting terminal coordinates once to avoid repeated calculations
            route_start_lat = None
            route_start_lng = None
            if route_starting_terminal and route_starting_terminal.latitude and route_starting_terminal.longitude:
                try:
                    route_start_lat = float(route_starting_terminal.latitude)
                    route_start_lng = float(route_starting_terminal.longitude)
                except (ValueError, TypeError) as e:
                    print(f"⚠️ [OPTIMIZATION] Could not parse route coordinates: {str(e)}")
            
            for i, drone in enumerate(potential_drones):
                try:
                    drone_id_str = str(drone.id)
                    print(f"🔍 [DRONE_PROCESS] Processing drone {drone.unit_id} (ID: {drone.id})")
                    # Get pre-fetched drone data
                    drone_weight_capacity = all_drone_capacities.get(drone_id_str, {"value": 0, "unit": "kg"})
                    drone_dimensions = all_drone_dimensions.get(drone_id_str, {"length": 0, "width": 0, "height": 0, "unit": "mm"})
                    
                    # Check for missing critical data first
                    has_missing_weight_data = drone_weight_capacity.get("missing_data", False)
                    has_missing_dims_data = drone_dimensions.get("missing_data", False)
                    
                    # Normalize capacities
                    cap_value = drone_weight_capacity.get("value") if isinstance(drone_weight_capacity, dict) else drone_weight_capacity
                    cap_unit = drone_weight_capacity.get("unit", "kg") if isinstance(drone_weight_capacity, dict) else "kg"
                    cap_kg = convert_unit(float(cap_value or 0), cap_unit, "kg")
                    # Normalize drone dimensions to mm
                    dr_unit = (drone_dimensions or {}).get("unit", "mm") if isinstance(drone_dimensions, dict) else "mm"
                    dr_len_mm = convert_unit(float((drone_dimensions or {}).get("length", 0) or 0), dr_unit, "mm")
                    dr_w_mm = convert_unit(float((drone_dimensions or {}).get("width", 0) or 0), dr_unit, "mm")
                    dr_h_mm = convert_unit(float((drone_dimensions or {}).get("height", 0) or 0), dr_unit, "mm")
                    
                    # Check if drone can carry the package: weight and dimensions
                    weight_ok = float(cap_kg or 0) >= float(package_weight_kg or 0)
                    dims_ok = (
                        float(dr_len_mm or 0) >= float(pkg_len_mm or 0)
                        and float(dr_w_mm or 0) >= float(pkg_w_mm or 0)
                        and float(dr_h_mm or 0) >= float(pkg_h_mm or 0)
                    )
                    
                    # Get pre-fetched battery capacity and model name (always needed)
                    battery_capacity = all_drone_batteries.get(drone_id_str, {"value": 0, "unit": "%"})
                    model_name = all_drone_models.get(drone_id_str, "Unknown")
                    
                    # Check if drone is currently busy (NEW LOGIC - replaces exclude) - MULTILINGUAL SUPPORT
                    is_busy = False
                    busy_reason = None
                    try:
                        # Check if drone has active delivery items in busy status
                        for delivery_item in DeliveryOperationItem._base_manager.filter(drone=drone):
                            if delivery_item.delivery_operation and delivery_item.delivery_operation.current_status:
                                status_code = delivery_item.delivery_operation.current_status.code
                                if status_code in ['select_drone_processing', 'in_transit_processing']:
                                    is_busy = True
                                    # Use multilingual reason system
                                    if status_code == 'select_drone_processing':
                                        busy_reason = DroneDisableReasons.get_reason('busy_select_drone', language)
                                    elif status_code == 'in_transit_processing':
                                        busy_reason = DroneDisableReasons.get_reason('busy_in_transit', language)
                                    
                                    break
                    except Exception as e:
                        print(f"⚠️ Could not check busy status for drone {drone.unit_id}: {str(e)}")
                    
                    # Determine if drone is suitable and reason if not - MULTILINGUAL SUPPORT
                    is_suitable = weight_ok and dims_ok and not has_missing_weight_data and not has_missing_dims_data and not is_busy
                    disable_reason = None
                    
                    if is_busy:
                        disable_reason = busy_reason
                    elif has_missing_weight_data:
                        disable_reason = DroneDisableReasons.get_reason('missing_weight_capacity', language)
                    elif has_missing_dims_data:
                        disable_reason = DroneDisableReasons.get_reason('missing_dimensions', language)
                    elif not weight_ok:
                        disable_reason = DroneDisableReasons.get_reason('insufficient_weight', language, 
                                                                       package_weight=package_weight_kg, 
                                                                       drone_capacity=cap_kg)
                    elif not dims_ok:
                        package_dims_str = f"{pkg_len_mm}x{pkg_w_mm}x{pkg_h_mm}"
                        drone_dims_str = f"{dr_len_mm}x{dr_w_mm}x{dr_h_mm}"
                        disable_reason = DroneDisableReasons.get_reason('insufficient_dimensions', language,
                                                                       package_dims=package_dims_str,
                                                                       drone_dims=drone_dims_str)
                    
                    if is_suitable:
                        processed_count += 1
                        
                        # Use pre-fetched parallel positions
                        # drone_position_data = drone_positions.get(drone.id, {})
                        # if drone_position_data.get('success'):
                        #     drone_position = drone_position_data['position']
                        #     drone_lat = drone_position.get('latitude', 0)
                        #     drone_lng = drone_position.get('longitude', 0)
                        #     position_source = "real-time-parallel"
                        #     api_call_single_time = drone_position_data.get('api_time', 0)
                        #     print(f"      📍 [PARALLEL-READY] Position: {drone_lat}, {drone_lng} (API: {api_call_single_time:.2f}ms)")
                        # else:
                        #     # Fallback to terminal position if parallel fetch failed
                        #     if drone.terminal and drone.terminal.latitude and drone.terminal.longitude:
                        #         try:
                        #             drone_lat = float(drone.terminal.latitude)
                        #             drone_lng = float(drone.terminal.longitude)
                        #             position_source = "terminal-fallback"
                        #             print(f"      📍 [FALLBACK] Terminal position: {drone_lat}, {drone_lng}")
                        #         except (ValueError, TypeError) as e2:
                        #             print(f"      ❌ [FALLBACK] Could not parse terminal coordinates: {str(e2)}")
                        #             drone_lat = 0
                        #             drone_lng = 0
                        #             position_source = "failed"
                        #     else:
                        #         drone_lat = 0
                        #         drone_lng = 0
                        #         position_source = "failed"
                        
                    # Create drone data (ALWAYS CREATE - no skipping)
                    # FIX: Create a copy to avoid reference corruption
                    current_drone = drone  # Store current drone reference
                    current_drone_id = drone.id  # Store current drone ID for debugging
                    
                    drone_data = {
                        'drone': current_drone,
                        'weight_capacity': {"value": cap_kg, "unit": "kg"},
                        'battery_capacity': battery_capacity,
                        'dimensions': {"length": dr_len_mm, "width": dr_w_mm, "height": dr_h_mm, "unit": "mm"},
                        'model_name': model_name,
                        # 'real_time_position': {
                        #     'latitude': drone_lat,
                        #     'longitude': drone_lng
                        # },
                        'terminal': current_drone.terminal,
                        'priority_score': 0,  # Will be calculated below
                        'disable': not is_suitable,  # NEW FIELD: Mark if drone is disabled
                        'reason': disable_reason,    # NEW FIELD: Reason why disabled
                        # 'position_source': position_source  # Track position source
                        '_debug_drone_id': current_drone_id,  # Debug field to track corruption
                    }
                    
                    # Calculate priority score based on location and route optimization (ORIGINAL LOGIC RESTORED)
                    if route_starting_terminal and drone.terminal:
                        # PRIORITY 1: Drone is at the starting terminal AND terminal is a hub
                        if (drone.terminal.id == route_starting_terminal.id and 
                            route_starting_terminal.terminal_types.filter(code='DELIVERY_HUB').exists()):
                            if is_hub:
                                print(f"      🎯 EXACT HUB MATCH: Drone at starting hub terminal {drone.terminal.name} ({'SUITABLE' if is_suitable else 'DISABLED'})")
                            else:
                                print(f"      🎯 EXACT MATCH: Drone at starting terminal {drone.terminal.name} ({'SUITABLE' if is_suitable else 'DISABLED'})")
                            
                        # PRIORITY 2: Drone is within 1km of starting terminal (sorted by distance) - ORIGINAL LOGIC
                            # elif drone_lat and drone_lng and route_starting_terminal.latitude and route_starting_terminal.longitude:
                            #     try:
                            #         from geopy.distance import geodesic
                            #         start_lat = float(route_starting_terminal.latitude)
                            #         start_lng = float(route_starting_terminal.longitude)
                            #         distance_km = geodesic((start_lat, start_lng), (drone_lat, drone_lng)).kilometers
                                    
                            #         # LOGIC FIX: Allow drones from other terminals (original logic)
                            #         # Instead of strict 1km limit, allow drones from different terminals
                            #         # This matches the original behavior that returned 3 drones
                            #         drone_data['distance_km'] = distance_km
                                    
                            #         if distance_km <= 1.0:  # Within 1km - high priority
                            #             nearby_drones.append(drone_data)
                            #             print(f"      📍 NEARBY: Drone at {drone.terminal.name} - {distance_km:.2f}km away ({position_source})")
                            #         else:  # Beyond 1km but still acceptable - lower priority
                            #             # Add to nearby_drones but with lower priority (will be sorted by distance)
                            #             nearby_drones.append(drone_data)
                            #             print(f"      📍 ACCEPTABLE: Drone at {drone.terminal.name} - {distance_km:.2f}km away ({position_source}) - added with lower priority")
                            #     except Exception as e:
                            #         print(f"      ⚠️ Distance calculation failed: {str(e)} - drone not added")
                        else:
                            # Drone có terminal nhưng không có đủ thông tin để tính distance
                            if is_hub:
                                print(f"      🏢 HUB DRONE: At different hub terminal {drone.terminal.name} ({'SUITABLE' if is_suitable else 'DISABLED'})")
                            else:
                                print(f"      ❌ INSUFFICIENT DATA: Drone at {drone.terminal.name} - insufficient position data")
                    else:
                        # Drone không có terminal hoặc route information
                        if is_hub:
                            print(f"      🏢 HUB DRONE: Hub terminal info missing ({'SUITABLE' if is_suitable else 'DISABLED'})")
                        else:
                            print(f"      ❌ NO ROUTE: Drone terminal/route info missing")
                        
                    
                    # Add ALL drones to the list (suitable and unsuitable) - MOVED TO END OF TRY BLOCK
                    hub_drones.append(drone_data)
                        
                except Exception as e:
                    print(f"      ❌ Error checking drone {drone.unit_id} (ID: {drone.id}): {str(e)} - MARKED FOR DISABLE")
                    # If we can't process drone, mark it as disabled instead of skipping
                    exception_drone_id = drone.id  # Store current drone ID for debugging
                    drone_data = {
                        'drone': drone,
                        'weight_capacity': {"value": 0, "unit": "kg"},
                        'battery_capacity': {"value": 0, "unit": "mAh"},
                        'dimensions': {"length": 0, "width": 0, "height": 0, "unit": "mm"},
                        'model_name': "Unknown",
                        'terminal': drone.terminal,
                        'priority_score': 0,
                        'disable': True,  # Mark as disabled
                        'reason': f"Processing error: {str(e)}",    # Error reason
                        '_debug_drone_id': exception_drone_id,  # Debug field to track corruption
                    }
                    hub_drones.append(drone_data)
                    list_type = "hub list" if is_hub else "drone list"
                    print(f"      ⚠️ Added DISABLED drone to {list_type} due to processing error")
            
            # Calculate statistics
            total_drones = len(hub_drones)
            suitable_drones_count = len([d for d in hub_drones if not d.get('disable', False)])
            disabled_drones_count = total_drones - suitable_drones_count
            
            # Log final drone counts for debugging
            print(f"🔍 [DEBUG] Processed {len(hub_drones)} drones total")
            
            # Calculate detailed disable reasons (FIXED: handle dict reason format)
            busy_drones_count = len([d for d in hub_drones if d.get('disable', False) and isinstance(d.get('reason'), dict) and d.get('reason', {}).get('type') == 'busy'])
            missing_data_count = len([d for d in hub_drones if d.get('disable', False) and isinstance(d.get('reason'), dict) and d.get('reason', {}).get('type') == 'configuration_error'])
            capacity_issues_count = len([d for d in hub_drones if d.get('disable', False) and isinstance(d.get('reason'), dict) and d.get('reason', {}).get('type') == 'capacity_limitation'])
            
            # Update variables for consistency with later usage
            suitable_hub_drones = suitable_drones_count
            disabled_hub_drones = disabled_drones_count
            
            # Sort hub drones: suitable drones first (by priority), then disabled drones
            hub_drones.sort(key=lambda x: (x.get('disable', False), -x.get('priority_score', 0)))
            suitable_drones = hub_drones
            
            print(f"📋 [FINAL_LIST] Returning {len(suitable_drones)} total drones: {suitable_hub_drones} suitable, {disabled_hub_drones} disabled")
            
            print(f"🚁 [DRONE_SEARCH] Completed - Found {len(suitable_drones)} drones: {suitable_hub_drones} suitable, {disabled_hub_drones} disabled")
            
            return suitable_drones
            
        except Exception as e:
            print(f"❌ [ERROR] Exception in get_list_of_drones_by_package_id: {str(e)}")
            return []
    
    @staticmethod
    def get_list_of_routes(operation: DeliveryOperation) -> list:
        """
        Get routes based on delivery option:
        - delivery_to_door: routes with last terminal near recipient_address, sorted by estimated_time (low to high)
        - collect_at_location: routes with last terminal matching delivery_terminal address
        """
        delivery_option = operation.order.delivery_option
        # Get all active routes with their terminals and measurements
        routes_queryset = Routes.objects.filter(is_active=True).prefetch_related(
            'route_terminals__terminal',
            'measurements',
            'route_terminals__terminal__terminal_types',
            'route_terminals__terminal__location_type',
            
        ).filter(
            route_terminals__terminal__isnull=False,
            route_terminals__terminal=operation.order.pickup_location
        )
        
        if delivery_option.code == "delivery_to_door":
            # For delivery to door: find routes with last terminal near recipient_address
            recipient_address = operation.order.recipient_address
            if not recipient_address or not recipient_address.lat or not recipient_address.lng:
                return []
            
            recipient_lat = float(recipient_address.lat)
            recipient_lng = float(recipient_address.lng)
            
            routes_with_distance = []
            for route in routes_queryset:
                # Get terminal with highest order (last terminal)
                last_terminal_relation = route.route_terminals.filter(
                    terminal__isnull=False
                ).order_by('-order').first()
                
                if last_terminal_relation and last_terminal_relation.terminal:
                    last_terminal = last_terminal_relation.terminal
                    # Calculate distance from last terminal to recipient address
                    try:
                        terminal_distance = geopy_distance(
                            (last_terminal.latitude, last_terminal.longitude),
                                (recipient_lat, recipient_lng)
                            ).kilometers
                    except Exception as e:
                        print("Error calculating distance", e)
                        terminal_distance = 0
                    
                    routes_with_distance.append((terminal_distance, route))
            
            # Sort by distance (nearest first), then get estimated_time for secondary sort
            routes_with_distance.sort(key=lambda x: x[0])
            
            # Get routes sorted by estimated_time (low to high)
            valid_routes = []
            for _, route in routes_with_distance:
                estimated_time_measurement = route.measurements.filter(measurement_type='estimated_time').first()
                if estimated_time_measurement:
                    # Get the numeric value for sorting
                    time_value = estimated_time_measurement.get_converted_data(None)
                    if time_value and 'value' in time_value:
                        valid_routes.append((time_value['value'], route))
                else:
                    # Routes without estimated_time go to the end
                    valid_routes.append((float('inf'), route))
            
            # Sort by estimated_time (low to high)
            valid_routes.sort(key=lambda x: x[0])
            sorted_routes = [route for _, route in valid_routes]
            
        elif delivery_option.code == "collect_at_location":
            # For collect at location: find routes with last terminal matching delivery_terminal
            delivery_terminal = operation.order.delivery_terminal
            if not delivery_terminal:
                return []
            
            matched_routes = []
            for route in routes_queryset:                 
                if RouteTerminal.objects.filter(route=route, terminal=delivery_terminal, stop=True).exists() and RouteTerminal.objects.filter(route=route, terminal=operation.order.pickup_location).exists():
                    if RouteTerminal.objects.filter(route=route, terminal=delivery_terminal, stop=True).order_by('-order').first().order > RouteTerminal.objects.filter(route=route, terminal=operation.order.pickup_location).order_by('-order').first().order:
                        matched_routes.append(route)
                    
            sorted_routes = matched_routes
            
        else:
            # Fallback: return empty list for unknown delivery options
            sorted_routes = []
        
        # Format data with measurements like in routes_views.py
        measurements_fields = ['total_distance', 'estimated_time']
        results = []
        
        for data in sorted_routes:
            route = RouteOutSchema.from_queryset(data, many=False)
            
            # Add measurements
            for measurement in measurements_fields:
                m = data.measurements.filter(measurement_type=measurement).first()
                if m:
                    route[measurement] = m.get_formatted_value(None)
            
            # Add full_address (last terminal address)
            last_terminal_relation = data.route_terminals.filter(
                terminal__isnull=False
            ).order_by('-order').first()
            
            if last_terminal_relation and last_terminal_relation.terminal:
                last_terminal = last_terminal_relation.terminal
                route['full_address'] = f"{last_terminal.name}({last_terminal.street_address}, {last_terminal.ward_town_township}, {last_terminal.city_county_district}, {last_terminal.city_province})"
            else:
                route['full_address'] = ""
            
            # Add full_description (all terminals with time stop)
            all_terminals = data.route_terminals.filter(
                terminal__isnull=False
            ).order_by('order')
            
            description_parts = []
            for terminal_relation in all_terminals:
                terminal = terminal_relation.terminal
                # Get time_stops measurement for this terminal
                time_stop_measurement = terminal.measurements.filter(measurement_type='time_stops').first()
                if time_stop_measurement and terminal_relation.stop:
                    time_stop = time_stop_measurement.get_formatted_value(None)
                    description_parts.append(f"{terminal.name} (Stop: {time_stop})")
                else:
                    description_parts.append(f"{terminal.name}")
            
            route['full_description'] = " → ".join(description_parts)
            
            results.append(route)

        # sort data by estimated_time
        results.sort(key=lambda x: x['estimated_time'])
        return results
    
    @staticmethod
    def get_list_of_routes_with_measurements(operation: DeliveryOperation) -> list:
        """
        Get routes with formatted measurements data like in routes_views.py
        Returns list of dictionaries with route data and measurements
        This method now simply calls get_list_of_routes for consistency
        """
        return ProcessingRepository.get_list_of_routes(operation)

    @staticmethod
    def get_list_of_drones() -> QuerySet:
        drones = Device.objects.filter(main_type__name="Drone", active=True)
        return drones
    
    @staticmethod
    def check_order_history(order_id: int) -> bool:
        """
        Check if order history completed
        """
        return OrderHistory._base_manager.filter(order_id=order_id).exists()

    
    @staticmethod
    def get_operation_select_route_processing() -> QuerySet:
        order_items_count = OrderItem.objects.filter(
            order=OuterRef('order')
        ).values('order').annotate(
            count=Count('id')
        ).values('count')
        
        # Subquery for origin (pickup_location address) with null handling
        origin_subquery = Order.objects.filter(
            id=OuterRef('order_id')
        ).select_related('pickup_location').annotate(
            address=Concat(
                Coalesce(F('pickup_location__name'), Value(''), output_field=CharField()),
                Value(' ('),
                Coalesce(F('pickup_location__street_address'), Value(''), output_field=CharField()),
                Case(
                    When(pickup_location__street_address__isnull=False, then=Value(', ')),
                    default=Value(''),
                    output_field=CharField()
                ),
                Coalesce(F('pickup_location__ward_town_township'), Value(''), output_field=CharField()),
                Case(
                    When(pickup_location__ward_town_township__isnull=False, then=Value(', ')),
                    default=Value(''),
                    output_field=CharField()
                ),
                Coalesce(F('pickup_location__city_county_district'), Value(''), output_field=CharField()),
                Case(
                    When(pickup_location__city_county_district__isnull=False, then=Value(', ')),
                    default=Value(''),
                    output_field=CharField()
                ),
                Coalesce(F('pickup_location__city_province'), Value(''), output_field=CharField()),
                Value(')'),
                output_field=CharField()
            )
        ).values('address')
        
        # Subquery for destination (recipient_address) with null handling
        destination_subquery = Order.objects.filter(
            id=OuterRef('order_id')
        ).select_related('delivery_option', 'recipient_address', 'delivery_terminal').annotate(
            address=Case(
                When(
                    delivery_option__code="delivery_to_door",
                    then=Coalesce(F('recipient_address__full_address'), Value(''), output_field=CharField())
                ),
                When(
                    delivery_option__code="collect_at_location",
                    then=Concat(
                        Coalesce(F('delivery_terminal__name'), Value(''), output_field=CharField()),
                        Value(' ('),
                        Coalesce(F('delivery_terminal__street_address'), Value(''), output_field=CharField()),
                        Case(
                            When(delivery_terminal__street_address__isnull=False, then=Value(', ')),
                            default=Value(''),
                            output_field=CharField()
                        ),
                        Coalesce(F('delivery_terminal__ward_town_township'), Value(''), output_field=CharField()),
                        Case(
                            When(delivery_terminal__ward_town_township__isnull=False, then=Value(', ')),
                            default=Value(''),
                            output_field=CharField()
                        ),
                        Coalesce(F('delivery_terminal__city_county_district'), Value(''), output_field=CharField()),
                        Case(
                            When(delivery_terminal__city_county_district__isnull=False, then=Value(', ')),
                            default=Value(''),
                            output_field=CharField()
                        ),
                        Coalesce(F('delivery_terminal__city_province'), Value(''), output_field=CharField()),
                        Value(')'),
                        output_field=CharField()
                    )
                ),
                default=Value('N/A'), 
                output_field=CharField()
            )
        ).values('address')
        
        # Latest cancellation for reason_for_rejection
        latest_cancellation = DeliveryCancellation.objects.filter(
            delivery_operation=OuterRef('pk')
        ).order_by('-cancelled_at')
        
        # Get mapping annotations
        mapping_annotations = ProcessingRepository._get_base_annotations()
        
        return DeliveryOperation.objects.filter(
            current_status__code="select_route_processing"
        ).select_related(
            'current_status',
            'order',
            'route',
            'created_by',
            'modified_by'
        ).prefetch_related(
            'items',
            'items__drone',
            'items__order_item',
            'returns',
            'cancellations'
        ).annotate(
            number_of_packages=Subquery(order_items_count, output_field=IntegerField(), distinct=True),
            origins=Subquery(origin_subquery, output_field=CharField()),
            destinations=Subquery(destination_subquery, output_field=CharField()),
            order_identifier=F('another_info__anyang__itemOrgId'),
            receipt_number=F('another_info__etri__receipt_id'),
            handler=Concat(
                Coalesce(F('created_by__last_name'), Value(''), output_field=CharField()),
                Value(' '),
                Coalesce(F('created_by__first_name'), Value(''), output_field=CharField()),
                output_field=CharField()
            ),
            tracking_number=F('another_info__etri__tracking_number'),
            reason_for_rejection=Coalesce(
                Subquery(latest_cancellation.values('reason')[:1]),
                F('order__cancel_reason')
            ),
            # Use dynamic mapping annotations
            **mapping_annotations
        ).order_by('-id')
    
    @staticmethod
    def get_operation_select_drone_processing() -> QuerySet:
        # Build expressions for origin/destination per order via joins
        origin_expr = Concat(
            Coalesce(F('delivery_items__delivery_operation__order__pickup_location__name'), Value(''), output_field=CharField()),
            Value(' ('),
            Coalesce(F('delivery_items__delivery_operation__order__pickup_location__street_address'), Value(''), output_field=CharField()),
            Case(When(delivery_items__delivery_operation__order__pickup_location__street_address__isnull=False, then=Value(', ')), default=Value(''), output_field=CharField()),
            Coalesce(F('delivery_items__delivery_operation__order__pickup_location__ward_town_township'), Value(''), output_field=CharField()),
            Case(When(delivery_items__delivery_operation__order__pickup_location__ward_town_township__isnull=False, then=Value(', ')), default=Value(''), output_field=CharField()),
            Coalesce(F('delivery_items__delivery_operation__order__pickup_location__city_county_district'), Value(''), output_field=CharField()),
            Case(When(delivery_items__delivery_operation__order__pickup_location__city_county_district__isnull=False, then=Value(', ')), default=Value(''), output_field=CharField()),
            Coalesce(F('delivery_items__delivery_operation__order__pickup_location__city_province'), Value(''), output_field=CharField()),
            Value(')'),
            output_field=CharField()
        )

        destination_expr = Case(
            When(
                delivery_items__delivery_operation__order__delivery_option__code="delivery_to_door",
                then=Coalesce(F('delivery_items__delivery_operation__order__recipient_address__full_address'), Value(''), output_field=CharField())
            ),
            When(
                delivery_items__delivery_operation__order__delivery_option__code="collect_at_location",
                then=Concat(
                    Coalesce(F('delivery_items__delivery_operation__order__delivery_terminal__name'), Value(''), output_field=CharField()),
                    Value(' ('),
                    Coalesce(F('delivery_items__delivery_operation__order__delivery_terminal__street_address'), Value(''), output_field=CharField()),
                    Case(When(delivery_items__delivery_operation__order__delivery_terminal__street_address__isnull=False, then=Value(', ')), default=Value(''), output_field=CharField()),
                    Coalesce(F('delivery_items__delivery_operation__order__delivery_terminal__ward_town_township'), Value(''), output_field=CharField()),
                    Case(When(delivery_items__delivery_operation__order__delivery_terminal__ward_town_township__isnull=False, then=Value(', ')), default=Value(''), output_field=CharField()),
                    Coalesce(F('delivery_items__delivery_operation__order__delivery_terminal__city_county_district'), Value(''), output_field=CharField()),
                    Case(When(delivery_items__delivery_operation__order__delivery_terminal__city_county_district__isnull=False, then=Value(', ')), default=Value(''), output_field=CharField()),
                    Coalesce(F('delivery_items__delivery_operation__order__delivery_terminal__city_province'), Value(''), output_field=CharField()),
                    Value(')'),
                    output_field=CharField()
                )
            ),
            default=Value('N/A'),
            output_field=CharField()
        )
        route_id_expr = Subquery(DeliveryOperationItem.objects.filter(
            delivery_operation=OuterRef('delivery_items__delivery_operation'),
            drone_id=OuterRef('id')
        ).values('delivery_operation__route__id').distinct(), output_field=IntegerField())
        # Unique drones with aggregated orders
        # Use values() to group by device before annotate to avoid duplicate rows
        return (
            Device.objects.filter(
                delivery_items__delivery_operation__current_status__code="select_drone_processing"
            )
            .annotate(
                drone__name = F('name'),
                drone__unit_id = F('unit_id'),
                drone__serial_number = F('serial_number'),
                drone__status = F('status'),
                order_ids=ArrayAgg('delivery_items__order_item__order_id', distinct=True),
                order_codes=ArrayAgg('delivery_items__delivery_operation__order__order_code', distinct=True),
                route_names=ArrayAgg('delivery_items__delivery_operation__route__name', distinct=True),
                number_of_packages=Count('delivery_items__id', distinct=True),
                origin=ArrayAgg(origin_expr, distinct=True),
                destination=ArrayAgg(destination_expr, distinct=True),
                can_fly=ArrayAgg('delivery_items__delivery_operation__is_partial_approved', distinct=True),
                checklist_items=ArrayAgg(
                    'operation_approvals__checklists__checklist_id', 
                    filter=Q(operation_approvals__delivery_operation__current_status__code="select_drone_processing"),
                    distinct=True
                ),
                group__name = F('group__name'),
                route_id=Subquery(route_id_expr, output_field=IntegerField())
            )
            .distinct()  
            .order_by('id')
        )
    
    @staticmethod
    def get_operation_in_transit_processing() -> QuerySet:
        order_items_count = OrderItem.objects.filter(
            order=OuterRef('order')
        ).values('order').annotate(
            count=Count('id')
        ).values('count')
        
        # Subquery for origin (pickup_location address) with null handling
        origin_subquery = Order.objects.filter(
            id=OuterRef('order_id')
        ).select_related('pickup_location').annotate(
            address=Concat(
                Coalesce(F('pickup_location__name'), Value(''), output_field=CharField()),
                Value(' ('),
                Coalesce(F('pickup_location__street_address'), Value(''), output_field=CharField()),
                Case(
                    When(pickup_location__street_address__isnull=False, then=Value(', ')),
                    default=Value(''),
                    output_field=CharField()
                ),
                Coalesce(F('pickup_location__ward_town_township'), Value(''), output_field=CharField()),
                Case(
                    When(pickup_location__ward_town_township__isnull=False, then=Value(', ')),
                    default=Value(''),
                    output_field=CharField()
                ),
                Coalesce(F('pickup_location__city_county_district'), Value(''), output_field=CharField()),
                Case(
                    When(pickup_location__city_county_district__isnull=False, then=Value(', ')),
                    default=Value(''),
                    output_field=CharField()
                ),
                Coalesce(F('pickup_location__city_province'), Value(''), output_field=CharField()),
                Value(')'),
                output_field=CharField()
            )
        ).values('address')
        
        # Subquery for destination based on delivery_option with null handling
        destination_subquery = Order.objects.filter(
            id=OuterRef('order_id')
        ).select_related('delivery_option', 'recipient_address', 'delivery_terminal').annotate(
            address=Case(
                When(
                    delivery_option__code="delivery_to_door",
                    then=Coalesce(F('recipient_address__full_address'), Value(''), output_field=CharField())
                ),
                When(
                    delivery_option__code="collect_at_location",
                    then=Concat(
                        Coalesce(F('delivery_terminal__name'), Value(''), output_field=CharField()),
                        Value(' ('),
                        Coalesce(F('delivery_terminal__street_address'), Value(''), output_field=CharField()),
                        Case(
                            When(delivery_terminal__street_address__isnull=False, then=Value(', ')),
                            default=Value(''),
                            output_field=CharField()
                        ),
                        Coalesce(F('delivery_terminal__ward_town_township'), Value(''), output_field=CharField()),
                        Case(
                            When(delivery_terminal__ward_town_township__isnull=False, then=Value(', ')),
                            default=Value(''),
                            output_field=CharField()
                        ),
                        Coalesce(F('delivery_terminal__city_county_district'), Value(''), output_field=CharField()),
                        Case(
                            When(delivery_terminal__city_county_district__isnull=False, then=Value(', ')),
                            default=Value(''),
                            output_field=CharField()
                        ),
                        Coalesce(F('delivery_terminal__city_province'), Value(''), output_field=CharField()),
                        Value(')'),
                        output_field=CharField()
                    )
                ),
                default=Value('N/A'),
                output_field=CharField()
            )
        ).values('address')
        
        # Latest cancellation for reason_for_rejection
        latest_cancellation = DeliveryCancellation.objects.filter(
            delivery_operation=OuterRef('pk')
        ).order_by('-cancelled_at')
        
        # Subqueries to get distinct and synchronized drone data
        # Using RawSQL with ARRAY constructor to ensure distinct and consistent ordering
        from django.db.models.expressions import RawSQL
        from django.contrib.postgres.fields import ArrayField
        
        # Raw SQL to get distinct drones ordered by drone_id
        streamming_data_sql = """
            SELECT ARRAY_AGG(DISTINCT d.id ORDER BY d.id)
            FROM delivery_deliveryoperationitem doi
            INNER JOIN devices_device d ON doi.drone_id = d.id
            WHERE doi.delivery_operation_id = delivery_deliveryoperation.id
            AND doi.drone_id IS NOT NULL
        """
        
        delivery_device_sql = """
            SELECT ARRAY(
                SELECT d.unit_id
                FROM delivery_deliveryoperationitem doi
                INNER JOIN devices_device d ON doi.drone_id = d.id
                WHERE doi.delivery_operation_id = delivery_deliveryoperation.id
                AND doi.drone_id IS NOT NULL
                GROUP BY d.id, d.unit_id
                ORDER BY d.id
            )
        """
        
        device_id_sql = """
            SELECT ARRAY(
                SELECT d.serial_number
                FROM delivery_deliveryoperationitem doi
                INNER JOIN devices_device d ON doi.drone_id = d.id
                WHERE doi.delivery_operation_id = delivery_deliveryoperation.id
                AND doi.drone_id IS NOT NULL
                GROUP BY d.id, d.serial_number
                ORDER BY d.id
            )
        """
        
        device_name_sql = """
            SELECT ARRAY(
                SELECT d.name
                FROM delivery_deliveryoperationitem doi
                INNER JOIN devices_device d ON doi.drone_id = d.id
                WHERE doi.delivery_operation_id = delivery_deliveryoperation.id
                AND doi.drone_id IS NOT NULL
                GROUP BY d.id, d.name
                ORDER BY d.id
            )
        """
        
        # Get mapping annotations
        mapping_annotations = ProcessingRepository._get_base_annotations()
        
        return DeliveryOperation.objects.filter(
            current_status__code="in_transit_processing"
        ).annotate(
            number_of_packages=Subquery(order_items_count, output_field=IntegerField()),
            origin=Subquery(origin_subquery, output_field=CharField()),
            destination=Subquery(destination_subquery, output_field=CharField()),
            # Get drone data using raw SQL for distinct and synchronized arrays
            # Specify output_field as ArrayField to enable isinstance checks
            streamming_data=RawSQL(streamming_data_sql, [], output_field=ArrayField(IntegerField())),
            delivery_device=RawSQL(delivery_device_sql, [], output_field=ArrayField(CharField())),
            device_id=RawSQL(device_id_sql, [], output_field=ArrayField(CharField())),
            device_name=RawSQL(device_name_sql, [], output_field=ArrayField(CharField())),
            # New columns
            order_identifier=F('another_info__anyang__itemOrgId'),
            receipt_number=F('another_info__etri__receipt_id'),
            handler=Concat(
                Coalesce(F('created_by__first_name'), Value(''), output_field=CharField()),
                Value(' '),
                Coalesce(F('created_by__last_name'), Value(''), output_field=CharField()),
                output_field=CharField()
            ),
            tracking_number=F('another_info__etri__tracking_number'),
            reason_for_rejection=Coalesce(
                Subquery(latest_cancellation.values('reason')[:1]),
                F('order__cancel_reason')
            ),
            order_terminal_id=F('order__delivery_terminal_id'),
            # Use dynamic mapping annotations
            **mapping_annotations
        ).order_by('-id')

    @staticmethod
    def get_operation_in_transit_processing_with_delivery_device() -> QuerySet:
        """
        Get operations in transit processing with delivery device annotation for filtering and sorting
        """
        order_items_count = OrderItem.objects.filter(
            order=OuterRef('order')
        ).values('order').annotate(
            count=Count('id')
        ).values('count')
        
        # Subquery for origin (pickup_location address) with null handling
        origin_subquery = Order.objects.filter(
            id=OuterRef('order_id')
        ).select_related('pickup_location').annotate(
            address=Concat(
                Coalesce(F('pickup_location__name'), Value(''), output_field=CharField()),
                Value(' ('),
                Coalesce(F('pickup_location__street_address'), Value(''), output_field=CharField()),
                Case(
                    When(pickup_location__street_address__isnull=False, then=Value(', ')),
                    default=Value(''),
                    output_field=CharField()
                ),
                Coalesce(F('pickup_location__ward_town_township'), Value(''), output_field=CharField()),
                Case(
                    When(pickup_location__ward_town_township__isnull=False, then=Value(', ')),
                    default=Value(''),
                    output_field=CharField()
                ),
                Coalesce(F('pickup_location__city_county_district'), Value(''), output_field=CharField()),
                Case(
                    When(pickup_location__city_county_district__isnull=False, then=Value(', ')),
                    default=Value(''),
                    output_field=CharField()
                ),
                Coalesce(F('pickup_location__city_province'), Value(''), output_field=CharField()),
                Value(')'),
                output_field=CharField()
            )
        ).values('address')
        
        # Subquery for destination based on delivery_option with null handling
        destination_subquery = Order.objects.filter(
            id=OuterRef('order_id')
        ).select_related('delivery_option', 'recipient_address', 'delivery_terminal').annotate(
            address=Case(
                When(
                    delivery_option__code="delivery_to_door",
                    then=Coalesce(F('recipient_address__full_address'), Value(''), output_field=CharField())
                ),
                When(
                    delivery_option__code="collect_at_location",
                    then=Concat(
                        Coalesce(F('delivery_terminal__name'), Value(''), output_field=CharField()),
                        Value(' ('),
                        Coalesce(F('delivery_terminal__street_address'), Value(''), output_field=CharField()),
                        Case(
                            When(delivery_terminal__street_address__isnull=False, then=Value(', ')),
                            default=Value(''),
                            output_field=CharField()
                        ),
                        Coalesce(F('delivery_terminal__ward_town_township'), Value(''), output_field=CharField()),
                        Case(
                            When(delivery_terminal__ward_town_township__isnull=False, then=Value(', ')),
                            default=Value(''),
                            output_field=CharField()
                        ),
                        Coalesce(F('delivery_terminal__city_county_district'), Value(''), output_field=CharField()),
                        Case(
                            When(delivery_terminal__city_county_district__isnull=False, then=Value(', ')),
                            default=Value(''),
                            output_field=CharField()
                        ),
                        Coalesce(F('delivery_terminal__city_province'), Value(''), output_field=CharField()),
                        Value(')'),
                        output_field=CharField()
                    )
                ),
                default=Value('N/A'),
                output_field=CharField()
            )
        ).values('address')
        
        # Latest cancellation for reason_for_rejection
        latest_cancellation = DeliveryCancellation.objects.filter(
            delivery_operation=OuterRef('pk')
        ).order_by('-cancelled_at')
        
        # Subqueries to get distinct and synchronized drone data
        from django.db.models.expressions import RawSQL
        from django.contrib.postgres.fields import ArrayField
        
        streamming_data_sql = """
            SELECT ARRAY_AGG(DISTINCT d.id ORDER BY d.id)
            FROM delivery_deliveryoperationitem doi
            INNER JOIN devices_device d ON doi.drone_id = d.id
            WHERE doi.delivery_operation_id = delivery_deliveryoperation.id
            AND doi.drone_id IS NOT NULL
        """
        
        delivery_device_sql = """
            SELECT ARRAY(
                SELECT d.unit_id
                FROM delivery_deliveryoperationitem doi
                INNER JOIN devices_device d ON doi.drone_id = d.id
                WHERE doi.delivery_operation_id = delivery_deliveryoperation.id
                AND doi.drone_id IS NOT NULL
                GROUP BY d.id, d.unit_id
                ORDER BY d.id
            )
        """
        
        # Get mapping annotations
        mapping_annotations = ProcessingRepository._get_base_annotations()
        
        return DeliveryOperation.objects.filter(
            current_status__code="in_transit_processing"
        ).annotate(
            number_of_packages=Subquery(order_items_count, output_field=IntegerField()),
            origin=Subquery(origin_subquery, output_field=CharField()),
            destination=Subquery(destination_subquery, output_field=CharField()),
            delivery_device=RawSQL(delivery_device_sql, [], output_field=ArrayField(CharField())),
            streamming_data=RawSQL(streamming_data_sql, [], output_field=ArrayField(IntegerField())),
            # New columns
            order_identifier=F('another_info__anyang__itemOrgId'),
            receipt_number=F('another_info__etri__receipt_id'),
            handler=Concat(
                Coalesce(F('created_by__last_name'), Value(''), output_field=CharField()),
                Value(' '),
                Coalesce(F('created_by__first_name'), Value(''), output_field=CharField()),
                output_field=CharField()
            ),
            tracking_number=F('another_info__etri__tracking_number'),
            reason_for_rejection=Coalesce(
                Subquery(latest_cancellation.values('reason')[:1]),
                F('order__cancel_reason')
            ),
            # Use dynamic mapping annotations
            **mapping_annotations
        ).order_by('-id')
    
    @staticmethod
    def get_operation_in_transit_processing_with_delivery_items() -> list:
        """
        Get operations in transit processing with their delivery items and associated drones
        """
        order_items_count = OrderItem.objects.filter(
            order=OuterRef('order')
        ).values('order').annotate(
            count=Count('id')
        ).values('count')
        
        operations = DeliveryOperation.objects.filter(
            current_status__code="in_transit_processing"
        ).annotate(
            number_of_packages=Subquery(order_items_count)
        ).prefetch_related('items__drone__main_type', 'items__order_item__package_id').order_by('-id')
        
        operations_with_items = []
        
        for operation in operations:
            # Get all delivery items for this operation
            delivery_items = operation.items.all()
            
            # Format delivery items with their drones
            items_data = []
            for item in delivery_items:
                item_data = {
                    'delivery_item': item,
                    'drone': item.drone.unit_id if item.drone else None
                }
                items_data.append(item_data)
            
            # Add operation with its delivery items and drones
            operations_with_items.append({
                'operation': operation,
                'delivery_items': items_data
            })
        
        return operations_with_items
    
    @staticmethod
    def update_route_to_operation(operation_id: int, route_id: int) -> None:
        try:
            print(f"🗺️ [ROUTE_ASSIGN] Assigning route {route_id} to operation {operation_id}")
            
            route = Routes.objects.get(id=route_id)
            print(f"✅ [ROUTE_ASSIGN] Found route: {route.name}")
            
            status = DeliveryStatus.objects.get(code="select_drone_processing")
            print(f"📊 [ROUTE_ASSIGN] Setting status to: {status.name}")
            
            operation = DeliveryOperation.objects.get(id=operation_id)
            print(f"✅ [ROUTE_ASSIGN] Found operation: {operation.id}")
            print(f"📊 [ROUTE_ASSIGN] Current operation status: {operation.current_status.code if operation.current_status else 'None'}")
            
            operation.route = route
            operation.current_status = status
            operation.save()
            
            print(f"✅ [ROUTE_ASSIGN] Successfully assigned route {route.name} to operation {operation.id}")
            print(f"✅ [ROUTE_ASSIGN] Updated operation status to {status.name}")
            
        except DeliveryOperation.DoesNotExist:
            print(f"❌ [ROUTE_ASSIGN] Operation with ID {operation_id} does not exist")
            raise ValueError(f"Operation with id {operation_id} does not exist")
        except Routes.DoesNotExist:
            print(f"❌ [ROUTE_ASSIGN] Route with ID {route_id} does not exist")
            raise ValueError(f"Route with id {route_id} does not exist")
        except DeliveryStatus.DoesNotExist:
            print(f"❌ [ROUTE_ASSIGN] DeliveryStatus 'select_drone_processing' does not exist")
            raise ValueError(f"DeliveryStatus 'select_drone_processing' does not exist")
        except Exception as e:
            print(f"❌ [ROUTE_ASSIGN] Error assigning route: {str(e)}")
            raise
    
    @staticmethod
    def update_drone_to_operation_item(operation_item_id: int, drone_id: int) -> None:
        try:
            drone = Device.objects.get(id=drone_id)
            status = DeliveryStatus.objects.get(code="in_transit_processing")
            operation_item = DeliveryOperationItem.objects.get(id=operation_item_id)
            operation_item.drone = drone
            operation_item.current_status = status
            operation_item.save()
        except DeliveryOperationItem.DoesNotExist:
            raise ValueError(f"Operation item with id {operation_item_id} does not exist")
        except Device.DoesNotExist:
            raise ValueError(f"Drone with id {drone_id} does not exist")
        
    
    @staticmethod
    def create_order_assignment(order_item: OrderItem, drone: Device, route: Routes) -> OrderAssignment:
        """
        Create order assignment by order item
        """
        return OrderAssignment.objects.create(
            order_item=order_item,
            device=drone,
            route_id=route,
            status="pending"
        )
    
    @staticmethod
    def update_drone_to_operation_items(operation_item_ids: list, drone_id: int) -> None:
        try:
            print(f"🔗 [DRONE_ASSIGN] Assigning drone {drone_id} to {len(operation_item_ids)} operation items")
            print(f"📝 [DRONE_ASSIGN] Operation item IDs: {operation_item_ids}")
            
            drone = Device._base_manager.get(id=drone_id)
            print(f"✅ [DRONE_ASSIGN] Found drone: {drone.unit_id}")
            
            operation_items = DeliveryOperationItem.objects.filter(id__in=operation_item_ids)
            operation_items_count = operation_items.count()
            print(f"📦 [DRONE_ASSIGN] Found {operation_items_count} operation items to update")
            
            if operation_items_count == 0:
                print(f"❌ [DRONE_ASSIGN] No operation items found with provided IDs")
                raise ValueError(f"No operation items found with IDs {operation_item_ids}")
            
            for i, operation_item in enumerate(operation_items):
                operation_item.drone = drone
                operation_item.save()
                print(f"   ✅ [DRONE_ASSIGN] Item {i+1}: Updated operation item {operation_item.id}")
            
            operation = DeliveryOperation._base_manager.get(id=operation_items[0].delivery_operation_id)
            route = operation.route
            print(f"🗺️ [DRONE_ASSIGN] Operation: {operation.id}, Route: {route.id if route else 'None'}")
            
            # create OrderAssignment
            print(f"📋 [DRONE_ASSIGN] Creating OrderAssignments...")
            assignments_created = 0
            for operation_item in operation_items:
                assignment = OrderAssignment.objects.create(
                    order_item=operation_item.order_item,
                    device=drone,
                    route_id=route,
                    status="pending"
                )
                assignments_created += 1
                print(f"   ✅ [DRONE_ASSIGN] Created assignment {assignments_created}: {assignment.id}")
            
            print(f"✅ [DRONE_ASSIGN] Successfully assigned drone {drone.unit_id} to {operation_items_count} items")
            print(f"✅ [DRONE_ASSIGN] Created {assignments_created} OrderAssignments")
            
        except DeliveryOperationItem.DoesNotExist:
            print(f"❌ [DRONE_ASSIGN] Operation items with IDs {operation_item_ids} do not exist")
            raise ValueError(f"Operation item with id {operation_item_ids} does not exist")
        except Device.DoesNotExist:
            print(f"❌ [DRONE_ASSIGN] Drone with ID {drone_id} does not exist")
            raise ValueError(f"Drone with id {drone_id} does not exist")
        except Exception as e:
            print(f"❌ [DRONE_ASSIGN] Error assigning drone: {str(e)}")
            raise
        
    @staticmethod
    def update_drone_status(drone_id: int, status_code: str) -> None:
        try:
            print(f"🔄 [DRONE_STATUS] Updating drone {drone_id} status to: {status_code}")
            
            drone = Device._base_manager.get(id=drone_id)
            print(f"✅ [DRONE_STATUS] Found drone: {drone.unit_id}")
            print(f"📊 [DRONE_STATUS] Current status: {drone.status.code if drone.status else 'None'}")
            
            status = DeviceStatus.objects.get(code=status_code)
            print(f"✅ [DRONE_STATUS] Found new status: {status.name}")
            
            drone.status = status
            drone.save()
            print(f"✅ [DRONE_STATUS] Successfully updated drone {drone.unit_id} status to {status.name}")
            
        except Device.DoesNotExist:
            print(f"❌ [DRONE_STATUS] Drone with ID {drone_id} does not exist")
            raise ValueError(f"Drone with id {drone_id} does not exist")
        except DeviceStatus.DoesNotExist:
            print(f"❌ [DRONE_STATUS] Status with code {status_code} does not exist")
            raise ValueError(f"Status with code {status_code} does not exist")
        except Exception as e:
            print(f"❌ [DRONE_STATUS] Error updating drone status: {str(e)}")
            raise
        
    @staticmethod
    def update_status_to_operation(operation_id: int, status_code: str) -> None:
        try:
            status = DeliveryStatus.objects.get(code=status_code)
            operation = DeliveryOperation._base_manager.get(id=operation_id)
            operation.current_status = status
            operation.save()
        except DeliveryOperation.DoesNotExist:
            raise ValueError(f"Operation with id {operation_id} does not exist")
        except DeliveryStatus.DoesNotExist:
            raise ValueError(f"Status with code {status_code} does not exist")
        

    @staticmethod
    def update_is_arrived_to_operation_item(operation_item_id: int, is_arrived: bool) -> None:
        try:
            operation_item = DeliveryOperationItem.objects.get(id=operation_item_id)
            operation_item.is_arrived = is_arrived
            operation_item.arrived_at = timezone.now()
            operation_item.save()
        except DeliveryOperationItem.DoesNotExist:
            raise ValueError(f"Operation item with id {operation_item_id} does not exist")
        
    @staticmethod
    def get_drone_payload(unique_id: str, user_units=None) -> float:
        try:
            print(f"🚁 [DRONE_PAYLOAD] Getting payload for drone ID: {unique_id}")
            
            device = Device._base_manager.get(id=unique_id)
            print(f"✅ [DRONE_PAYLOAD] Found device: {device.unit_id}")
            
            cargo_compartment = device.cargo_compartments.first()
            if not cargo_compartment:
                print(f"❌ [DRONE_PAYLOAD] No cargo compartment found for drone {device.unit_id}")
                raise ValueError(f"No cargo compartment found for drone {device.unit_id}")
            
            print(f"📦 [DRONE_PAYLOAD] Found cargo compartment: {cargo_compartment.id}")
            
            cargo_compartment_weight_capacity = cargo_compartment.measurements.filter(measurement_type='weight_capacity').first()
            cargo_compartment_dimensions = cargo_compartment.measurements.filter(measurement_type='dimensions').first()
            
            # Extract weight capacity data
            if cargo_compartment_weight_capacity:
                print(f"⚖️ [DRONE_PAYLOAD] Found weight capacity measurement")
                if user_units:
                    weight_capacity_data = cargo_compartment_weight_capacity.get_converted_data(user_units)
                else:
                    weight_capacity_data = cargo_compartment_weight_capacity.data
                
                # Sử dụng cấu trúc data thực tế, không giả định có field 'unit'
                weight_capacity = {
                    'value': weight_capacity_data.get('value', 0),
                    'unit': weight_capacity_data.get('unit', 'kg') if isinstance(weight_capacity_data, dict) else 'kg'
                }
                print(f"✅ [DRONE_PAYLOAD] Weight capacity: {weight_capacity}")
            else:
                weight_capacity = {'value': 0, 'unit': 'kg'}
                print(f"⚠️ [DRONE_PAYLOAD] No weight capacity measurement, using default: {weight_capacity}")
            
            # Extract dimensions data
            if cargo_compartment_dimensions:
                print(f"📏 [DRONE_PAYLOAD] Found dimensions measurement")
                if user_units:
                    dimensions_data = cargo_compartment_dimensions.get_converted_data(user_units)
                else:
                    dimensions_data = cargo_compartment_dimensions.data
                
                # Sử dụng cấu trúc data thực tế, không giả định có field 'unit'
                dimensions = {
                    'length': dimensions_data.get('length', 0),
                    'width': dimensions_data.get('width', 0),
                    'height': dimensions_data.get('height', 0),
                    'unit': dimensions_data.get('unit', 'mm') if isinstance(dimensions_data, dict) else 'mm'
                }
                print(f"✅ [DRONE_PAYLOAD] Dimensions: {dimensions}")
            else:
                dimensions = {
                    'length': 0,
                    'width': 0,
                    'height': 0,
                    'unit': 'mm'
                }
                print(f"⚠️ [DRONE_PAYLOAD] No dimensions measurement, using default: {dimensions}")
                
            return weight_capacity, dimensions
            
        except Device.DoesNotExist:
            print(f"❌ [DRONE_PAYLOAD] Drone with ID {unique_id} does not exist")
            raise ValueError(f"Drone with unique id {unique_id} does not exist")
        except Exception as e:
            print(f"❌ [DRONE_PAYLOAD] Error getting drone payload: {str(e)}")
            raise

    @staticmethod
    def get_drone_battery_capacity(unique_id: str, user_units=None) -> Dict[str, Any]:
        """
        Get the battery capacity of a drone by its unique ID.
        
        Args:
            unique_id: Unique ID of the drone
            user_units: Optional user units for conversion
            
        Returns:
            Dictionary containing battery capacity information
        """
        try:
            device = Device.objects.get(id=unique_id)
            # Fallback: try to get from cargo compartments if no direct measurement
            cargo_compartment = device.cargo_compartments.first()
            if cargo_compartment:
                battery_measurement = cargo_compartment.measurements.filter(measurement_type='battery_capacity').first()
                if battery_measurement:
                    if user_units:
                        battery_data = battery_measurement.get_converted_data(user_units)
                    else:
                        battery_data = battery_measurement.data
                    
                    # Sử dụng cấu trúc data thực tế, không giả định có field 'unit'
                    battery_capacity = {
                        'value': battery_data.get('value', 0),
                        'unit': battery_data.get('unit', 'mAh') if isinstance(battery_data, dict) else 'mAh'
                    }
                else:
                    # Default battery capacity if no measurement found
                    battery_capacity = {'value': 5000, 'unit': 'mAh'}
            else:
                # Default battery capacity if no cargo compartment
                battery_capacity = {'value': 5000, 'unit': 'mAh'}
                
            return battery_capacity
        except Device.DoesNotExist:
            raise ValueError(f"Drone with unique id {unique_id} does not exist")

    @staticmethod
    def get_drone_model_name(unique_id: str) -> str:
        try:
            device = Device.objects.get(id=unique_id)
            try:
                if device.manufacturer_information and device.manufacturer_information.model_number:
                    return device.manufacturer_information.model_number
                else:
                    return "Unknown Model"
            except Device.manufacturer_information.RelatedObjectDoesNotExist:
                return "Unknown Model"
        except Device.DoesNotExist:
            raise ValueError(f"Drone with unique id {unique_id} does not exist")


    @staticmethod
    def get_package_weight_dimensions(package_id: int) -> Dict[str, Any]:
        try:
            print(f"📦 [PACKAGE_DATA] Getting weight/dimensions for package ID: {package_id}")
            
            order_item = DeliveryOperationItem.objects.get(id=package_id).order_item
            package_spec = order_item.package_id
            print(f"📋 [PACKAGE_DATA] Package spec: {package_spec.name if package_spec else 'No spec'}")
            
            # 1) Dimensions come from 'dimensions' measurement (length/width/height only)
            length_measurement = {"value": 0, "unit": "mm"}
            width_measurement = {"value": 0, "unit": "mm"}
            height_measurement = {"value": 0, "unit": "mm"}
            if package_spec:
                dim_m = package_spec.measurements.filter(measurement_type='dimensions').first()
                if dim_m and isinstance(dim_m.data, dict):
                    dim_data = dim_m.data
                    # Sử dụng cấu trúc data thực tế, không giả định có field 'unit'
                    dim_unit = dim_data.get('unit') or dim_data.get('dimension_unit', 'mm')
                    length_measurement = {"value": dim_data.get('length', 0), "unit": dim_unit}
                    width_measurement = {"value": dim_data.get('width', 0), "unit": dim_unit}
                    height_measurement = {"value": dim_data.get('height', 0), "unit": dim_unit}
                else:
                    # Fallback to separate max_* measurements for dimensions
                    len_m = package_spec.get_measurement("max_length")
                    wid_m = package_spec.get_measurement("max_width")
                    hei_m = package_spec.get_measurement("max_height")
                    if len_m:
                        # Sử dụng cấu trúc data thực tế
                        len_data = len_m.data if hasattr(len_m, 'data') else {}
                        length_measurement = {"value": len_m.get_numeric_value(), "unit": len_data.get('unit', 'mm')}
                    if wid_m:
                        wid_data = wid_m.data if hasattr(wid_m, 'data') else {}
                        width_measurement = {"value": wid_m.get_numeric_value(), "unit": wid_data.get('unit', 'mm')}
                    if hei_m:
                        hei_data = hei_m.data if hasattr(hei_m, 'data') else {}
                        height_measurement = {"value": hei_m.get_numeric_value(), "unit": hei_data.get('unit', 'mm')}
            
            # 2) Weight comes from 'max_weight' measurement
            if package_spec:
                weight_m = package_spec.get_measurement("max_weight")
            else:
                weight_m = None
            if weight_m:
                # Sử dụng cấu trúc data thực tế
                weight_data = weight_m.data if hasattr(weight_m, 'data') else {}
                weight_measurement = {"value": weight_m.get_numeric_value(), "unit": weight_data.get('unit', 'kg')}
            else:
                weight_measurement = {"value": 0, "unit": "kg"}
            print(f"📊 [PACKAGE_DATA] Weight: {weight_measurement}")
            print(f"📊 [PACKAGE_DATA] Dimensions: {length_measurement} x {width_measurement} x {height_measurement}")
            return weight_measurement, length_measurement, width_measurement, height_measurement
        except Exception as e:
            print(f"❌ [PACKAGE_DATA] Error getting package data: {str(e)}")
            # Return default values in case of error
            default_weight = {'value': 1.0, 'unit': 'kg'}
            default_dim = {'value': 100, 'unit': 'mm'}
            print(f"⚠️ [PACKAGE_DATA] Using default values: weight={default_weight}, dims={default_dim}")
            return default_weight, default_dim, default_dim, default_dim

    @staticmethod
    def get_package_weight_dimensions_alternative(package_id: int) -> Dict[str, Any]:
        """Alternative method using get_numeric_value utility function"""
        package = OrderItem.objects.get(id=package_id)
        package_spec = package.package_id
        
        # Get the dimensions_weight measurement
        dimensions_weight_measurement = package_spec.measurements.first()
        
        if dimensions_weight_measurement and dimensions_weight_measurement.data.get('type') == 'dimensions_weight':
            # Use the get_numeric_value utility function with component parameter
            weight_value = dimensions_weight_measurement.get_numeric_value('weight')
            length_value = dimensions_weight_measurement.get_numeric_value('length')
            width_value = dimensions_weight_measurement.get_numeric_value('width')
            height_value = dimensions_weight_measurement.get_numeric_value('height')
            
            # Get units from the data
            data = dimensions_weight_measurement.data
            weight_unit = data.get('weight_unit', 'kg')
            dimension_unit = data.get('dimension_unit', 'mm')
            
            return {
                'weight': {'value': weight_value, 'unit': weight_unit},
                'length': {'value': length_value, 'unit': dimension_unit},
                'width': {'value': width_value, 'unit': dimension_unit},
                'height': {'value': height_value, 'unit': dimension_unit}
            }
        else:
            # Fallback: try to get separate measurements if they exist
            weight_measurement = package_spec.get_measurement("max_weight")
            length_measurement = package_spec.get_measurement("max_length")
            width_measurement = package_spec.get_measurement("max_width")
            height_measurement = package_spec.get_measurement("max_height")
            
            return {
                'weight': weight_measurement,
                'length': length_measurement,
                'width': width_measurement,
                'height': height_measurement
            }

    @staticmethod
    def get_operation_select_drone_processing_with_suitable_drones() -> list:
        """
        Get operations in select drone processing phase with suitable drones for each operation
        based on package weight requirements
        """
        order_items_count = OrderItem.objects.filter(
            order=OuterRef('order')
        ).values('order').annotate(
            count=Count('id')
        ).values('count')
        
        operations = DeliveryOperation.objects.filter(
            current_status__code="select_drone_processing"
        ).annotate(
            number_of_packages=Subquery(order_items_count)
        ).prefetch_related('items__order_item__package_id')
        
        operations_with_drones = []
        
        for operation in operations:
            # Get all packages in this operation
            operation_items = operation.items.all()
            
            # Collect all suitable drones with their capacity information
            suitable_drones_data = {}
            
            for item in operation_items:
                try:
                    # Get suitable drones for this specific package
                    drones_for_package = ProcessingRepository.get_list_of_drones_by_package_id(item.id, "available", None)
                    
                    # Add drone data to the dict (to avoid duplicates while keeping capacity info)
                    for drone_data in drones_for_package:
                        drone_id = drone_data['drone'].id
                        if drone_id not in suitable_drones_data:
                            suitable_drones_data[drone_id] = drone_data
                except Exception:
                    # If we can't get suitable drones for this package, skip it
                    continue
            
            # Convert to list
            suitable_drones = list(suitable_drones_data.values())
            
            # Add operation with its suitable drones
            operations_with_drones.append({
                'operation': operation,
                'suitable_drones': suitable_drones
            })
        
        return operations_with_drones

    @staticmethod
    def get_delivery_items_with_suitable_drones_by_operation_id(operation_id: int, route_id: int = None) -> list:
        """
        Get delivery operation items by operation ID with suitable drones for each item
        based on package weight requirements and route optimization
        
        Args:
            operation_id: DeliveryOperation ID
            route_id: Optional route ID for location-based drone prioritization
        """
        # Get all delivery operation items for this operation
        delivery_items = DeliveryOperationItem.objects.filter(
            delivery_operation_id=operation_id
        ).select_related('order_item__package_id', 'drone').prefetch_related(
            'order_item__package_id__measurements'
        )
        items_with_drones = []
        
        for item in delivery_items:
            try:
                # Get suitable drones for this specific delivery item with route optimization
                suitable_drones = ProcessingRepository.get_list_of_drones_by_package_id(item.id, "available", route_id)
                
                # Add delivery item with its suitable drones
                items_with_drones.append({
                    'delivery_item': item,
                    'suitable_drones': suitable_drones
                })
            except Exception as e:
                print(f"❌ [DELIVERY_ITEMS_WITH_SUITABLE_DRONES] Error: {str(e)}") 
                # If we can't get suitable drones for this item, add it with empty drones list
                items_with_drones.append({
                    'delivery_item': item,
                    'suitable_drones': []
                })
        
        return items_with_drones

    @staticmethod
    def get_delivery_items_with_suitable_drones_by_operation_id_optimized(operation_id: int, route_id: int = None) -> list:
        """
        Optimized version: Get delivery operation items by operation ID with suitable drones for each item
        This method reduces database queries by batching operations
        """
        # Get all delivery operation items for this operation in one query
        delivery_items = DeliveryOperationItem.objects.filter(
            delivery_operation_id=operation_id
        ).select_related('order_item__package_id', 'drone').prefetch_related(
            'order_item__package_id__measurements'
        )
        
        if not delivery_items:
            return []
        
        # Get all package IDs to batch fetch drone data
        package_ids = [item.id for item in delivery_items]
        
        # Batch fetch all suitable drones for all packages
        all_suitable_drones = {}
        for package_id in package_ids:
            try:
                suitable_drones = ProcessingRepository.get_list_of_drones_by_package_id(package_id, "available", route_id)
                all_suitable_drones[package_id] = suitable_drones
            except Exception as e:
                all_suitable_drones[package_id] = []
        
        # Build response
        items_with_drones = []
        for item in delivery_items:
            items_with_drones.append({
                'delivery_item': item,
                'suitable_drones': all_suitable_drones.get(item.id, [])
            })
        
        return items_with_drones

    @staticmethod
    def get_delivery_items_with_enhanced_drone_selection_by_operation_id(operation_id: int, route: 'Routes') -> list:
        """
        Enhanced workflow that always returns drone selections based on route terminal logic
        No fallbacks to original logic - always uses enhanced selection
        
        Args:
            operation_id: DeliveryOperation ID
            route: Selected route for terminal location check
            
        Returns:
            List of delivery items with enhanced drone selection (always successful)
        """
        try:
            print(f"🚀 [ENHANCED_WORKFLOW] Processing operation {operation_id} with route {route.name}")
            
            # Get delivery operation items
            operation_items = DeliveryOperationItem.objects.filter(
                delivery_operation_id=operation_id
            ).select_related('order_item__package_id')
            
            if not operation_items.exists():
                print(f"⚠️ [ENHANCED_WORKFLOW] No operation items - using fallback")
                return ProcessingRepository.get_delivery_items_with_suitable_drones_by_operation_id(operation_id, route.id if route else None)
            
            items_with_drones = []
            
            for item in operation_items:
                if item.order_item and item.order_item.package_id:
                    package_id = item.order_item.package_id.id
                    package_name = item.order_item.package_id.name
                    
                    # CURRENT: Enhanced selection with terminal logic (working)
                    suitable_drones = ProcessingRepository.get_list_of_drones_by_package_and_route(
                        package_id, route, 'available'
                    )
                    
                    # FUTURE: Battery-aware enhanced selection (uncomment to enable)
                    # suitable_drones = ProcessingRepository.get_enhanced_drones_with_battery_check(
                    #     package_id, route, 'available'
                    # )
                    
                    items_with_drones.append({
                        'delivery_item': item,
                        'package_id': package_id,
                        'package_name': package_name,
                        'suitable_drones': suitable_drones
                    })
                    
                    print(f"📦 [ENHANCED_WORKFLOW] Item {item.id}: {package_name} → {len(suitable_drones)} drones")
            
            print(f"✅ [ENHANCED_WORKFLOW] Processed {len(items_with_drones)} items successfully")
            return items_with_drones
            
        except Exception as e:
            print(f"❌ [ENHANCED_WORKFLOW] Error: {str(e)}")
            logger.error(f"Enhanced workflow error: {str(e)}")
            # Only fallback on complete failure
            return ProcessingRepository.get_delivery_items_with_suitable_drones_by_operation_id(operation_id, route.id if route else None)

    @staticmethod
    def get_delivery_items_with_suitable_drones_by_operation_item_id(operation_item_id: int, route_id: int = None) -> list:
        """
        Get delivery operation items by operation item ID with suitable drones for each item
        based on package weight requirements and route optimization
        
        Args:
            operation_item_id: Operation item ID
            route_id: Optional route ID for location-based drone prioritization
        """
        # Get all delivery operation items for this operation
        try:
            # Get suitable drones for this specific delivery item with route optimization
            return ProcessingRepository.get_list_of_drones_by_package_id(operation_item_id, "available", route_id)
        except Exception:
            # If we can't get suitable drones for this item, add it with empty drones list
            return []
        
    @staticmethod
    def get_operation_id_by_package_id(package_id: int) -> int:
        """
        Get operation ID by package ID
        """
        return DeliveryOperationItem.objects.get(id=package_id).delivery_operation_id
    
    @staticmethod
    def get_route_by_operation_id(operation_id: int) -> int:
        """
        Get route by operation ID
        """
        return DeliveryOperation._base_manager.get(id=operation_id).route.id
    
    
    @staticmethod
    def get_route_by_order_id(order_id: int) -> int:
        """
        Get route by order ID
        """
        return DeliveryOperation._base_manager.get(order_id=order_id).route.id
    
    
    @staticmethod
    def get_route_twoway_by_operation_id(route_id: int) -> bool:
        """
        Get route twoway by operation ID
        """
        try:
            return Routes._base_manager.get(id=route_id).two_way
        except Exception:
            return False

    @staticmethod
    def get_route_terminals_by_route_id(route_id: int) -> list:
        """
        Get route terminals by route ID
        """
        # get route terminals lat and lng
        return RouteTerminal._base_manager.filter(route_id=route_id).order_by('order').select_related('terminal').values_list('terminal__latitude', 'terminal__longitude', 'terminal__id')
    
    @staticmethod
    def get_route_terminals_queryset_by_route_id(route_id: int) -> list:
        """
        Get route terminals by route ID
        """
        # get route terminals lat and lng
        return RouteTerminal._base_manager.filter(route_id=route_id).order_by('order')
    
    @staticmethod
    def get_devices_by_operation_id(operation_id: int) -> list:
        """
        Get devices by operation ID
        """
        operation_items = DeliveryOperationItem.objects.filter(delivery_operation_id=operation_id)
        return Device._base_manager.filter(id__in=operation_items.values_list('drone_id', flat=True))
    
    @staticmethod
    def get_terminal_by_lat_long(lat: float, long: float) -> Terminal:
        """
        Get terminal by latitude and longitude
        Round both input and database coordinates to 1 decimal place for comparison
        """
        # Round input coordinates to 1 decimal place
        rounded_lat = round(lat, 1)
        rounded_long = round(long, 1)
        
        # Query with rounded database coordinates
        return Terminal._base_manager.annotate(
            rounded_latitude=Round('latitude', 1),
            rounded_longitude=Round('longitude', 1)
        ).filter(
            rounded_latitude=rounded_lat, 
            rounded_longitude=rounded_long
        ).first()
    
    @staticmethod
    def get_terminal_by_id(terminal_id: int) -> Terminal:
        """
        Get terminal by ID
        """
        return Terminal._base_manager.get(id=terminal_id)
    
    @staticmethod
    def get_terminal_time_stops(terminal_id: int) -> int:
        """
        Get terminal time stops
        """
        try:
            return Terminal._base_manager.get(id=terminal_id).measurements.filter(measurement_type="time_stops").first().get_numeric_value(user_units=None) or 0    
        except Exception:
            return 0

    @staticmethod
    def get_order_assignments_by_order_item(order_item: OrderItem) -> OrderAssignment:
        """
        Get order assignment by drone and order
        """
        return OrderAssignment._base_manager.filter(order_item=order_item).first()
    
    
    @staticmethod
    def get_netx_terminal_seq_by_current_terminal_seq(sequence_order: int, 
                                                      delivery_operation: DeliveryOperation,
                                                      drone: Device) -> TerminalSequence:
        """
        Get terminal sequence by terminal ID
        """
        return TerminalSequence._base_manager.filter(sequence_order=sequence_order, 
                                                     delivery_operation=delivery_operation,
                                                     drone=drone).first()

    @staticmethod
    def get_drone_by_unique_id(drone_uid: str) -> Device:
        """
        Get drone by unique ID
        """
        return Device._base_manager.filter(unit_id=drone_uid).first()

    @staticmethod
    def create_delivery_event(order_assignment: OrderAssignment, 
                              terminal: Terminal, 
                              terminal_seq: TerminalSequence, 
                              arrived_lat: float, 
                              arrived_long: float) -> DeliveryEvent:
        """
        Create a delivery event
        """
        # create a order history
        if terminal:
            order_history_data = {
                'order': order_assignment.order_item.order,
                'action': 'arrived_at_terminal',
                'description': {
                    "en": f"Package {order_assignment.order_item.code} is in transit to {terminal.name} {terminal_seq.sequence_order}",
                    "ko": f"패키지 {order_assignment.order_item.code} 현재 위치는 {terminal.name} {terminal_seq.sequence_order} 입니다.",
                    "th": f"พัสดุ {order_assignment.order_item.code} ตอนนี้อยู่ที่ {terminal.name} {terminal_seq.sequence_order}"
                }
            }
            create_model_with_translations(OrderHistory, order_history_data)
        return DeliveryEvent.objects.create(
            order_assignment=order_assignment,
            event_type='in_transit',
            description=f"Package {order_assignment.order_item.code} is in transit to {terminal.name}" if terminal else f"Package {order_assignment.order_item.code} is in transit to unknown terminal",
            event_time=timezone.now(),
            lat=terminal.latitude if terminal else arrived_lat,
            lng=terminal.longitude if terminal else arrived_long,
            terminal_stop=terminal if terminal else None
        )
    
    @staticmethod
    def check_terminal_is_delivery_terminal(terminal: Terminal, delivery_terminal: Terminal) -> bool:
        """
        Check if terminal is delivery terminal
        """
        return terminal.id == delivery_terminal.id
    
    @staticmethod
    def get_operation_by_order(order: Order) -> DeliveryOperation:
        """
        Get operation by order
        """
        return DeliveryOperation._base_manager.filter(order=order).first()
    
    @staticmethod
    def get_operation_items_by_operation_id_and_drone(operation_id: int, drone_id: int) -> DeliveryOperationItem:
        """
        Get operation items by operation ID and drone
        """
        return DeliveryOperationItem._base_manager.filter(delivery_operation_id=operation_id, 
                                                          drone_id=drone_id)
        
    @staticmethod
    def update_upload_mission_to_operation_item_by_order_ids_and_drone(order_ids: list, 
                                                                       drone: Device, 
                                                                       upload_mission: bool) -> None:
        """
        Update upload mission to operation items
        """
        return DeliveryOperationItem._base_manager.filter(order_item__order_id__in=order_ids, 
                                                          drone=drone).update(upload_mission=upload_mission)

    @staticmethod
    def get_operation_items_by_operation_and_drone(operation: DeliveryOperation, drone: Device) -> DeliveryOperationItem:
        """
        Get operation item by operation and drone
        """
        return DeliveryOperationItem._base_manager.filter(delivery_operation=operation, drone=drone)
    
    @staticmethod
    def check_drone_upload_mission_by_order_ids(order_ids: list, drone: Device) -> bool:
        """
        Check if drone upload mission by order ids
        """
        items = DeliveryOperationItem._base_manager.filter(order_item__order_id__in=order_ids, 
                                                           drone=drone)
        for item in items:
            if not item.upload_mission:
                return False
        return True
    
    @staticmethod
    def update_drone_status_to_available(drone: Device) -> None:
        """
        Update drone status to available
        """
        drone_available_status = DeviceStatus._base_manager.filter(code="available").first()
        if not drone_available_status:
            raise ValueError("DeviceStatus with code 'available' does not exist")
        drone.status = drone_available_status
        drone.save()

    @staticmethod
    def check_all_operation_items_delivered(operation: DeliveryOperation) -> bool:
        """
        Check if all operation items are delivered
        """
        return operation.items.filter(is_delivered_by_drone=True).count() == operation.items.count()

    @staticmethod
    def update_operation_status_to_arrived(operation: DeliveryOperation) -> None:
        """
        Update operation status to arrived
        """
        try:
            # check if DeliveryStatus code is "arrived_order" exists
            operation_arrived_status = DeliveryStatus._base_manager.filter(code="arrived_order").first()
            if not operation_arrived_status:
                # create a new DeliveryStatus
                status_data = {
                    "code": "arrived_order",
                    "name": {
                        "en": "Arrived Order",
                        "ko": "도착 주문"
                    },
                    "description": {
                        "en": "All packages have been delivered to the order",
                        "ko": "모든 패키지가 주문에 도착했습니다."
                    },
                    "color_code": "#EB7509"
                }
                operation_arrived_status = create_model_with_translations(DeliveryStatus, status_data)
            operation.current_status = operation_arrived_status
            operation.save()
        except Exception as e:
            raise ValueError(f"Error in update_operation_status_to_arrived: {str(e)}")

    @staticmethod
    def get_operation_item_by_drone(drone: Device) -> DeliveryOperationItem:
        """
        Get operation item by drone
        """
        return DeliveryOperationItem._base_manager.filter(drone=drone).order_by('-id').first()
    
    @staticmethod
    def get_drone_current_load_weight_kg(drone_id: int) -> float:
        """
        Get current load weight of drone in kg by summing up all assigned packages
        
        Args:
            drone_id: ID of the drone
            
        Returns:
            float: Total weight in kg of all packages currently assigned to the drone
        """
        try:
            total_weight = 0.0
            # Get only DeliveryOperationItem assigned to this drone that are currently active (not completed)
            # Filter by both item status and operation status to ensure we only get active items
            items = DeliveryOperationItem.objects.filter(
                drone_id=drone_id,
                # Item level: not yet delivered
                is_delivered=False,
                is_arrived=False,
                is_delivered_by_drone=False,
                # Operation level: only active operations (not completed)
                delivery_operation__current_status__code__in=[
                    'select_route_processing',
                    'select_drone_processing',
                ]
            ).select_related('order_item', 'delivery_operation__current_status')
            
            for item in items:
                if item.order_item and item.order_item.weight:
                    try:
                        weight_value = float(item.order_item.weight.get('value', 0))
                        weight_unit = item.order_item.weight.get('unit', 'kg')
                        # Convert to kg if needed
                        if weight_unit != 'kg':
                            from devices.utils import convert_unit
                            weight_kg = convert_unit(weight_value, weight_unit, 'kg')
                        else:
                            weight_kg = weight_value
                        total_weight += weight_kg
                    except (ValueError, TypeError):
                        # Skip items with invalid weight data
                        continue
            
            return total_weight
        except Exception as e:
            logger.error(f"Error calculating drone current load weight: {str(e)}")
            return 0.0
    
    @staticmethod
    def get_operation_from_terminal_sequence_by_drone(drone_uid: str) -> List[DeliveryOperation]:
        """
        Get delivery operations from terminal sequence by drone.
        Returns operations where:
        - Terminal sequence has this drone
        - is_visited = False (terminal not yet visited)
        - drone.status = return (drone is in return state)
        """
        return_status = DeviceStatus._base_manager.filter(code="return").first()
        if not return_status:
            return []
        
        # Filter terminal sequences with conditions
        terminal_sequences = TerminalSequence._base_manager.filter(
            drone__unit_id=drone_uid,
            is_visited=False,
            drone__status=return_status
        )
        
        # Get unique delivery_operation_ids
        operation_ids = terminal_sequences.values_list('delivery_operation_id', flat=True).distinct()
        
        # Get delivery operations
        operations = list(
            DeliveryOperation._base_manager.filter(id__in=operation_ids).distinct()
        )
        
        return operations
        
    @staticmethod
    def get_in_transit_operation_by_drone_uid(drone_uid: str) -> List[DeliveryOperation]:
        """
        Get in transit operations by drone uid.
        Always includes fallback operations (latest completed with drone in return state) so callers can decide how to handle both sets.
        """
        try:
            # First check if the status exists
            in_transit_status = DeliveryStatus._base_manager.filter(code="in_transit_processing").first()
            if not in_transit_status:
                # create a new DeliveryStatus
                status_data = {
                    "code": "in_transit_processing",
                    "name": {
                        "en": "In Transit Processing",
                        "ko": "이동 중"
                    },
                    "description": {
                        "en": "All packages have been delivered to the order",
                        "ko": "모든 패키지가 주문에 도착했습니다."
                    },
                    "color_code": "#6495ED"
                }
                in_transit_status = create_model_with_translations(DeliveryStatus, status_data)
                return None
            
            in_transit_operations_qs = DeliveryOperation._base_manager.filter(
                items__drone__unit_id=drone_uid,
                current_status=in_transit_status
            ).order_by('-id').distinct()
            in_transit_operations = list(in_transit_operations_qs)

            completed_operations = ProcessingRepository.get_operation_from_terminal_sequence_by_drone(drone_uid)

            return in_transit_operations + completed_operations
        except Exception as e:
            print(f"Error in get_in_transit_operation_by_drone_uid: {str(e)}")
            return None
    
    @staticmethod
    def get_last_terminal_of_route_by_order(route: Routes) -> RouteTerminal:
        """
        Get last terminal of route by order
        """
        return RouteTerminal._base_manager.filter(route=route).order_by('-order').first().terminal
    
    @staticmethod
    def get_terminals_by_route_id(route: Routes) -> list:
        """
        Get terminals by route ID
        """
        route_terminals = RouteTerminal._base_manager.filter(route=route).select_related('terminal').order_by('order')
        return [rt.terminal for rt in route_terminals if rt.terminal]
    
    @staticmethod
    def get_order_assignment_by_package(package: DeliveryOperationItem) -> OrderAssignment:
        """
        Get order assignment by package
        """
        return OrderAssignment._base_manager.filter(order_item=package.order_item).first()
    
    @staticmethod
    def get_order_items_by_order(order: Order) -> OrderItem:
        """
        Get order items by order
        """
        return OrderItem._base_manager.filter(order=order)
    
    @staticmethod
    def get_route_starting_terminal(route: Routes) -> Optional['Terminal']:
        """
        Get the starting terminal of a route
        
        Args:
            route: Routes instance
            
        Returns:
            Terminal instance or None
        """
        try:
            
            # Otherwise, get RouteTerminal with lowest order
            first_route_terminal = route.route_terminals.order_by('order').first()
            if first_route_terminal and first_route_terminal.terminal:
                return first_route_terminal.terminal
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting route starting terminal: {str(e)}")
            return None
    
    @staticmethod
    def get_list_of_drones_by_package_and_route(package_id: int, route: 'Routes', status: str) -> list:
        """
        Enhanced drone selection: Exact terminal match → Nearest terminal → All compatible drones
        Always returns results, no empty lists
        
        Args:
            package_id: Package ID for compatibility check
            route: Route instance to check starting terminal
            status: Drone status to filter by
            
        Returns:
            List of suitable drone data with capacity information and terminal compatibility flag
        """
        try:
            print(f"🚁 [ENHANCED_DRONE_SEARCH] Searching drones for package {package_id} and route {route.name}")
            
            # Get route starting terminal
            starting_terminal = ProcessingRepository.get_route_starting_terminal(route)
            if not starting_terminal:
                print(f"⚠️ [ENHANCED_DRONE_SEARCH] No starting terminal, using package-only logic")
                return ProcessingRepository.get_list_of_drones_by_package_id(package_id, status)
            
            print(f"📍 [ENHANCED_DRONE_SEARCH] Route starting terminal: {starting_terminal.name}")
            
            # Get the selected package
            selected_package = PackagingSpecification.objects.get(id=package_id)
            package_weight = ProcessingRepository.get_package_weight_dimensions(package_id)[0]["value"]
            device_status = DeviceStatus.objects.get(code=status)
            
            # Get ALL drones that support this package (without terminal filter)
            all_compatible_drones = Device.objects.filter(
                status=device_status,
                active=True,
                packaging_specification_device__option__specifications__package=selected_package,
                terminal__isnull=False  # Only drones with terminal location
            ).distinct().select_related('main_type', 'terminal').prefetch_related('cargo_compartments__measurements').order_by('-id')
            
            print(f"📦 [ENHANCED_DRONE_SEARCH] Found {all_compatible_drones.count()} package-compatible drones with terminals")
            
            suitable_drones = []
            exact_terminal_drones = []
            nearest_terminal_drones = []
            
            # Get starting terminal coordinates for distance calculation
            starting_lat = float(starting_terminal.latitude) if starting_terminal.latitude else None
            starting_lng = float(starting_terminal.longitude) if starting_terminal.longitude else None
            
            for drone in all_compatible_drones:
                try:
                    # Check weight capacity
                    drone_weight_capacity, drone_dimensions = ProcessingRepository.get_drone_payload(str(drone.id))
                    drone_max_weight = drone_weight_capacity["value"] if isinstance(drone_weight_capacity, dict) else drone_weight_capacity
                    
                    if drone_max_weight < package_weight:
                        continue  # Skip weight-incompatible drones
                    
                    # Get additional drone info
                    battery_capacity = ProcessingRepository.get_drone_battery_capacity(str(drone.id))
                    model_name = ProcessingRepository.get_drone_model_name(str(drone.id))
                    
                    # Create base drone data
                    drone_data = {
                        'drone': drone,
                        'weight_capacity': drone_weight_capacity,
                        'battery_capacity': battery_capacity,
                        'dimensions': drone_dimensions,
                        'model_name': model_name,
                        'terminal': drone.terminal
                    }
                    
                    # Check terminal compatibility
                    if drone.terminal.id == starting_terminal.id:
                        # EXACT MATCH: Best priority
                        drone_data['terminal_compatible'] = True
                        drone_data['distance_km'] = 0
                        exact_terminal_drones.append(drone_data)
                        print(f"✅ [EXACT] Drone {drone.unit_id} at exact terminal {drone.terminal.name}")
                        
                    elif starting_lat and starting_lng and drone.terminal.latitude and drone.terminal.longitude:
                        # NEAREST TERMINAL: Calculate distance
                        try:
                            from geopy.distance import geodesic
                            drone_lat = float(drone.terminal.latitude)
                            drone_lng = float(drone.terminal.longitude)
                            distance_km = geodesic((starting_lat, starting_lng), (drone_lat, drone_lng)).kilometers
                            
                            drone_data['terminal_compatible'] = False
                            drone_data['distance_km'] = distance_km
                            nearest_terminal_drones.append(drone_data)
                            print(f"📍 [NEAREST] Drone {drone.unit_id} at {drone.terminal.name} - {distance_km:.1f}km away")
                            
                        except Exception as e:
                            # If distance calculation fails, treat as compatible but no distance
                            drone_data['terminal_compatible'] = False
                            drone_data['distance_km'] = float('inf')
                            nearest_terminal_drones.append(drone_data)
                    else:
                        # NO COORDINATES: Treat as compatible but unknown distance
                        drone_data['terminal_compatible'] = False
                        drone_data['distance_km'] = float('inf')
                        nearest_terminal_drones.append(drone_data)
                        
                except Exception as e:
                    print(f"❌ [ENHANCED_DRONE_SEARCH] Error checking drone {drone.unit_id}: {str(e)}")
                    continue
            
            # PRIORITY ASSEMBLY: Exact → Nearest (sorted by distance) → All others
            suitable_drones.extend(exact_terminal_drones)
            
            # Sort nearest drones by distance (closest first)
            nearest_terminal_drones.sort(key=lambda x: x['distance_km'])
            suitable_drones.extend(nearest_terminal_drones)
            
            # ALWAYS RETURN RESULTS: If no enhanced drones found, get package-only drones
            if not suitable_drones:
                print(f"🔄 [ENHANCED_DRONE_SEARCH] No terminal-based drones, getting package-only drones")
                package_only_drones = ProcessingRepository.get_list_of_drones_by_package_id(package_id, status, None)
                
                # Add distance info to package-only drones
                for drone_data in package_only_drones:
                    drone_data['terminal_compatible'] = False
                    drone_data['distance_km'] = float('inf')
                
                suitable_drones.extend(package_only_drones)
            
            print(f"🎯 [ENHANCED_DRONE_SEARCH] Final result: {len(suitable_drones)} drones found")
            print(f"   ✅ Exact terminal: {len(exact_terminal_drones)}")
            print(f"   📍 Nearest terminal: {len(nearest_terminal_drones)}")
            print(f"   🔄 Package-only: {len(suitable_drones) - len(exact_terminal_drones) - len(nearest_terminal_drones)}")
            
            return suitable_drones
            
        except Exception as e:
            print(f"❌ [ENHANCED_DRONE_SEARCH] Error: {str(e)}")
            logger.error(f"Enhanced drone selection error: {str(e)}")
            # ALWAYS RETURN FALLBACK
            return ProcessingRepository.get_list_of_drones_by_package_id(package_id, status, None)
    
    @staticmethod
    def get_drones_by_package_and_route_optimized(package_id: int, route_id: int, status: str = "available") -> list:
        """
        Get drones optimized for a specific package and route with location-based prioritization
        
        Args:
            package_id: Package ID for compatibility check
            route_id: Route ID for location optimization
            status: Drone status to filter by
            
        Returns:
            List of drones sorted by priority: exact terminal match > hub-to-hub > nearby (≤1km) > others
        """
        try:
            print(f"🚁 [OPTIMIZED_DRONE_SEARCH] Searching drones for package {package_id} and route {route_id}")
            
            # Use the enhanced drone selection with route optimization
            return ProcessingRepository.get_list_of_drones_by_package_id(package_id, status, route_id)
            
        except Exception as e:
            print(f"❌ [OPTIMIZED_DRONE_SEARCH] Error: {str(e)}")
            logger.error(f"Optimized drone search error: {str(e)}")
            # Fallback to basic drone selection
            return ProcessingRepository.get_list_of_drones_by_package_id(package_id, status, None)

    # =================================================================================
    # CONSOLIDATED APPROACH: Battery logic moved to processing_repository.py only
    # This file will call repository methods to avoid duplicate code
    # Current ETA calculation already includes time_stops - keep as is
    # =================================================================================
    
    # COMPREHENSIVE BATTERY-AWARE WORKFLOW:
    # 
    # CURRENT WORKFLOW (Working):
    # Package → Route → Drone → ETA
    # 
    # BATTERY-AWARE WORKFLOW (When enabled):
    # Package → All-Compatible-Drones → Battery-Filter-by-Routes → Best-Drone-Route-Pair → Battery-Aware-ETA
    # 
    # DRONE SPECIFICATIONS TO ADD (for real implementation):
    # - max_flight_distance_km: float  # Khoảng cách tối đa 1 lần sạc (ví dụ: 50km)
    # - battery_capacity_mah: int      # Dung lượng pin (ví dụ: 5000mAh) 
    # - charging_time_minutes: int     # Thời gian sạc đầy (ví dụ: 45 phút)
    # - hover_consumption_rate: float  # % pin tiêu thụ mỗi phút hover (ví dụ: 0.8)
    # - cruise_consumption_rate: float # % pin tiêu thụ mỗi phút bay (ví dụ: 0.3)
    
    # INTEGRATION POINTS:
    # 1. get_delivery_items_with_enhanced_drone_selection_by_operation_id() 
    #    → calls get_enhanced_drones_with_battery_check() instead of basic drone selection
    # 2. _auto_select_route() in anyang_order_automation.py
    #    → calls get_battery_compatible_routes() to prefilter routes by drone battery
    # 3. _calculate_delivery_eta() in anyang_order_automation.py  
    #    → calls calculate_eta_with_battery_constraints() for accurate ETA with charging stops
    
    # =================================================================================
    # BATTERY-AWARE DRONE & ROUTE SELECTION FUNCTIONS (FUTURE IMPLEMENTATION)
    # Uncomment when real drones with battery specifications are available
    # =================================================================================
    
    # @staticmethod
    # def check_drone_battery_vs_route_distance(drone: Device, route: 'Routes') -> Dict:
    #     """
    #     CORE BATTERY LOGIC: Check if drone battery capacity is sufficient for route distance
    #     This function is used in BOTH drone selection AND ETA calculation
    #     
    #     Args:
    #         drone: Device instance
    #         route: Routes instance
    #         
    #     Returns:
    #         Dict with compatibility info, remaining battery %, and detailed breakdown
    #     """
    #     try:
    #         print(f"🔋 [BATTERY_CHECK] Checking drone {drone.unit_id} vs route {route.name}")
    #         
    #         # Get route distance
    #         distance_measurement = route.measurements.filter(measurement_type='total_distance').first()
    #         if not distance_measurement:
    #             return {'compatible': False, 'error': 'No route distance data'}
    #         
    #         distance_data = distance_measurement.get_converted_data(None)
    #         distance_km = float(distance_data['value'])
    #         distance_meters = distance_km * 1000
    #         
    #         print(f"   📏 Route distance: {distance_km}km")
    #         
    #         # DRONE SPECIFICATIONS (to be added to Device model in real implementation):
    #         # For now using default values - these should come from drone.max_flight_distance_km etc.
    #         drone_specs = {
    #             'max_flight_distance_km': 50.0,     # Khoảng cách tối đa 1 lần sạc 
    #             'hover_consumption_rate': 0.8,      # % pin/phút hover tại terminal
    #             'cruise_consumption_rate': 0.3,     # % pin/phút bay bình thường
    #             'payload_consumption_rate': 0.2,    # % pin thêm/kg hàng hóa
    #             'safety_margin_percent': 20         # % pin tối thiểu giữ lại
    #         }
    #         
    #         # Get drone speed (20m/s default)
    #         drone_speed_ms = 20.0
    #         flight_time_minutes = distance_meters / drone_speed_ms / 60
    #         
    #         # Calculate battery consumption for cruise flight
    #         cruise_consumption = flight_time_minutes * drone_specs['cruise_consumption_rate']
    #         
    #         # Add hover time at terminals (same logic as ETA calculation)
    #         route_terminals = route.route_terminals.filter(stop=True).select_related('terminal')
    #         total_hover_time = 0
    #         
    #         for route_terminal in route_terminals:
    #             terminal = route_terminal.terminal
    #             if terminal:
    #                 time_stop_measurement = terminal.measurements.filter(measurement_type='time_stops').first()
    #                 if time_stop_measurement:
    #                     stop_data = time_stop_measurement.get_converted_data(None)
    #                     if stop_data and 'value' in stop_data:
    #                         total_hover_time += float(stop_data['value'])
    #         
    #         hover_consumption = total_hover_time * drone_specs['hover_consumption_rate']
    #         
    #         # Add payload consumption (simplified - would need actual payload weight)
    #         payload_consumption = 5  # Assume 5% additional for typical payload
    #         
    #         # Total battery consumption
    #         total_consumption = cruise_consumption + hover_consumption + payload_consumption
    #         
    #         # Check if route distance exceeds drone's max range
    #         max_distance_km = drone_specs['max_flight_distance_km']
    #         distance_feasible = distance_km <= max_distance_km
    #         
    #         # Check battery percentage
    #         max_usable_battery = 100 - drone_specs['safety_margin_percent']
    #         battery_sufficient = total_consumption <= max_usable_battery
    #         
    #         # Overall compatibility (both distance and battery must be OK)
    #         is_compatible = distance_feasible and battery_sufficient
    #         remaining_battery = max_usable_battery - total_consumption
    #         
    #         print(f"   🔋 Battery analysis:")
    #         print(f"      ✈️  Flight time: {flight_time_minutes:.1f} min")
    #         print(f"      🚁 Cruise consumption: {cruise_consumption:.1f}%")
    #         print(f"      ⏱️  Hover time: {total_hover_time:.1f} min") 
    #         print(f"      🔄 Hover consumption: {hover_consumption:.1f}%")
    #         print(f"      📦 Payload consumption: {payload_consumption:.1f}%")
    #         print(f"      📊 Total consumption: {total_consumption:.1f}%")
    #         print(f"      🛡️  Safety margin: {drone_specs['safety_margin_percent']}%")
    #         print(f"      📏 Distance feasible: {distance_feasible} ({distance_km:.1f}km <= {max_distance_km}km)")
    #         print(f"      🔋 Battery sufficient: {battery_sufficient}")
    #         print(f"      ⚡ Remaining battery: {remaining_battery:.1f}%")
    #         print(f"      ✅ Overall compatible: {is_compatible}")
    #         
    #         return {
    #             'compatible': is_compatible,
    #             'distance_feasible': distance_feasible,
    #             'battery_sufficient': battery_sufficient,
    #             'total_consumption_percent': total_consumption,
    #             'remaining_battery_percent': remaining_battery,
    #             'max_flight_distance_km': max_distance_km,
    #             'flight_time_minutes': flight_time_minutes,
    #             'safety_margin_percent': drone_specs['safety_margin_percent'],
    #             'breakdown': {
    #                 'cruise_consumption': cruise_consumption,
    #                 'hover_consumption': hover_consumption,
    #                 'payload_consumption': payload_consumption
    #             }
    #         }
    #         
    #     except Exception as e:
    #         logger.error(f"Error checking battery vs route: {str(e)}")
    #         return {'compatible': False, 'error': str(e)}
    
    # @staticmethod
    # def get_enhanced_drones_with_battery_check(package_id: int, route: 'Routes', status: str) -> list:
    #     """
    #     INTEGRATION WITH DRONE SELECTION: Enhanced drone selection with battery-route compatibility
    #     This replaces get_list_of_drones_by_package_and_route when battery checking is enabled
    #     
    #     Args:
    #         package_id: Package ID for compatibility check
    #         route: Route instance to check battery compatibility 
    #         status: Drone status to filter by
    #         
    #     Returns:
    #         List of drones filtered by: package + terminal + battery compatibility
    #     """
    #     try:
    #         print(f"🚁🔋 [BATTERY_ENHANCED_SEARCH] Finding drones with battery check for route {route.name}")
    #         
    #         # Get base compatible drones (package + terminal)
    #         base_drones = ProcessingRepository.get_list_of_drones_by_package_and_route(
    #             package_id, route, status
    #         )
    #         
    #         battery_compatible_drones = []
    #         battery_incompatible_drones = []
    #         
    #         for drone_data in base_drones:
    #             drone = drone_data['drone']
    #             
    #             # Check battery compatibility for this specific route
    #             battery_check = ProcessingRepository.check_drone_battery_vs_route_distance(drone, route)
    #             
    #             # Add battery analysis to drone data
    #             drone_data['battery_analysis'] = battery_check
    #             
    #             if battery_check['compatible']:
    #                 drone_data['battery_compatible'] = True
    #                 battery_compatible_drones.append(drone_data)
    #                 print(f"   ✅ Drone {drone.unit_id}: Battery compatible ({battery_check['remaining_battery_percent']:.1f}% remaining)")
    #             else:
    #                 drone_data['battery_compatible'] = False
    #                 battery_incompatible_drones.append(drone_data)
    #                 print(f"   ❌ Drone {drone.unit_id}: Battery insufficient")
    #         
    #         print(f"🔋 [BATTERY_ENHANCED_SEARCH] {len(battery_compatible_drones)} of {len(base_drones)} drones are battery-compatible")
    #         
    #         # PRIORITIZE battery-compatible drones, but include incompatible as fallback with warnings
    #         if battery_compatible_drones:
    #             # Sort battery-compatible by remaining battery (most efficient first)
    #             battery_compatible_drones.sort(
    #                 key=lambda x: x['battery_analysis']['remaining_battery_percent'], 
    #                 reverse=True
    #             )
    #             return battery_compatible_drones
    #         else:
    #             # No battery-compatible drones - return incompatible ones with warnings
    #             print(f"⚠️ [BATTERY_ENHANCED_SEARCH] No battery-compatible drones, returning all with warnings")
    #             for drone_data in battery_incompatible_drones:
    #                 drone_data['battery_warning'] = 'May require charging stops or route modification'
    #             return battery_incompatible_drones
    #         
    #     except Exception as e:
    #         logger.error(f"Error in battery-enhanced drone selection: {str(e)}")
    #         # Fallback to base logic
    #         return ProcessingRepository.get_list_of_drones_by_package_and_route(package_id, route, status)
    
    # @staticmethod  
    # def get_battery_compatible_routes(operation: DeliveryOperation) -> list:
    #     """
    #     INTEGRATION WITH ROUTE SELECTION: Get routes suitable for available drones based on battery
    #     This should be called BEFORE drone selection to prefilter routes
    #     
    #     Args:
    #         operation: DeliveryOperation instance
    #         
    #     Returns:
    #         List of routes that have at least one battery-compatible drone available
    #     """
    #     try:
    #         print(f"🔋🗺️ [BATTERY_ROUTE_PREFILTER] Finding routes with battery-compatible drones")
    #         
    #         # Get base routes using current logic
    #         base_routes = ProcessingRepository.get_list_of_routes(operation)
    #         
    #         routes_with_battery_drones = []
    #         
    #         # Get available drones for this operation's packages
    #         operation_items = operation.items.all()
    #         if not operation_items:
    #             return base_routes  # No items to check
    #         
    #         for route_data in base_routes:
    #             route_id = route_data.get('id')
    #             route = Routes.objects.get(id=route_id)
    #             
    #             # Check if ANY package has battery-compatible drones for this route
    #             has_battery_compatible_drone = False
    #             
    #             for item in operation_items:
    #                 package = item.order_item.package_id if item.order_item else None
    #                 if package:
    #                     # Check drones for this package-route combination
    #                     battery_drones = ProcessingRepository.get_enhanced_drones_with_battery_check(
    #                         package.id, route, 'available'
    #                     )
    #                     
    #                     # If any drone is battery-compatible, this route is viable
    #                     if any(d.get('battery_compatible', False) for d in battery_drones):
    #                         has_battery_compatible_drone = True
    #                         break
    #             
    #             if has_battery_compatible_drone:
    #                 route_data['battery_compatible'] = True
    #                 routes_with_battery_drones.append(route_data)
    #                 print(f"   ✅ Route {route.name}: Has battery-compatible drones")
    #             else:
    #                 print(f"   ❌ Route {route.name}: No battery-compatible drones")
    #         
    #         print(f"🔋🗺️ [BATTERY_ROUTE_PREFILTER] {len(routes_with_battery_drones)} of {len(base_routes)} routes have battery-compatible drones")
    #         
    #         # If no routes have battery-compatible drones, return original routes with warnings
    #         if not routes_with_battery_drones:
    #             print(f"⚠️ [BATTERY_ROUTE_PREFILTER] No routes with battery-compatible drones - returning all with warnings")
    #             for route_data in base_routes:
    #                 route_data['battery_compatible'] = False
    #                 route_data['battery_warning'] = 'No drones have sufficient battery for this route'
    #             return base_routes
    #         
    #         return routes_with_battery_drones
    #         
    #     except Exception as e:
    #         logger.error(f"Error filtering routes by battery compatibility: {str(e)}")
    #         # Fallback to original route selection
    #         return ProcessingRepository.get_list_of_routes(operation)
    
    # @staticmethod
    # def calculate_eta_with_battery_constraints(operation: DeliveryOperation, route: 'Routes', drone: Device) -> Optional[datetime]:
    #     """
    #     FINAL ETA CALCULATION: Calculate ETA considering battery constraints and charging stops
    #     This replaces the basic ETA calculation when battery awareness is enabled
    #     
    #     Args:
    #         operation: DeliveryOperation instance
    #         route: Routes instance  
    #         drone: Device instance (already selected as battery-compatible)
    #         
    #     Returns:
    #         datetime with realistic ETA considering battery limitations
    #     """
    #     try:
    #         # Check battery compatibility for final validation
    #         battery_analysis = ProcessingRepository.check_drone_battery_vs_route_distance(drone, route)
    #         
    #         if battery_analysis['compatible']:
    #             # Battery sufficient - use existing ETA calculation (already includes time_stops)
    #             logger.info(f"✅ [BATTERY_ETA] Battery sufficient ({battery_analysis['remaining_battery_percent']:.1f}% remaining)")
    #             from third_api.services.anyang_order_automation import AnyangOrderAutomation
    #             return AnyangOrderAutomation._calculate_delivery_eta(operation, route, drone)
    #         else:
    #             # Battery insufficient - calculate with charging stops
    #             logger.warning(f"⚠️ [BATTERY_ETA] Battery insufficient, calculating ETA with charging stops")
    #             return ProcessingRepository._calculate_eta_with_charging_stops(operation, route, drone, battery_analysis)
    #             
    #     except Exception as e:
    #         logger.error(f"Error calculating ETA with battery constraints: {str(e)}")
    #         # Fallback to standard ETA calculation
    #         try:
    #             from third_api.services.anyang_order_automation import AnyangOrderAutomation
    #             return AnyangOrderAutomation._calculate_delivery_eta(operation, route, drone)
    #         except:
    #             return None
    
    # @staticmethod
    # def _calculate_eta_with_charging_stops(operation: DeliveryOperation, route: 'Routes', drone: Device, battery_analysis: Dict) -> Optional[datetime]:
    #     """
    #     Calculate ETA when drone requires charging stops during route
    #     """
    #     try:
    #         logger.info(f"🔌 [CHARGING_ETA] Calculating ETA with charging stops")
    #         
    #         # Get route distance
    #         distance_measurement = route.measurements.filter(measurement_type='total_distance').first()
    #         if not distance_measurement:
    #             return None
    #             
    #         distance_data = distance_measurement.get_converted_data(None)
    #         total_distance_km = float(distance_data['value'])
    #         
    #         # Battery specifications (should match check_drone_battery_vs_route_distance)
    #         max_flight_distance_km = battery_analysis.get('max_flight_distance_km', 50.0)
    #         charging_time_minutes = 45  # Fast charging time
    #         safety_margin_km = max_flight_distance_km * 0.2  # 20% safety margin
    #         
    #         # Calculate number of charging stops needed
    #         effective_flight_distance = max_flight_distance_km - safety_margin_km
    #         charging_stops_needed = max(0, int((total_distance_km - effective_flight_distance) / effective_flight_distance))
    #         
    #         # Calculate flight time (same logic as standard ETA)
    #         drone_speed_ms = 20.0
    #         total_flight_time_seconds = (total_distance_km * 1000) / drone_speed_ms
    #         
    #         # Add terminal stop times (reuse existing logic)
    #         total_stop_time_seconds = 0
    #         route_terminals = route.route_terminals.filter(stop=True).select_related('terminal')
    #         
    #         for route_terminal in route_terminals:
    #             terminal = route_terminal.terminal
    #             if terminal:
    #                 time_stop_measurement = terminal.measurements.filter(measurement_type='time_stops').first()
    #                 if time_stop_measurement:
    #                     stop_data = time_stop_measurement.get_converted_data(None)
    #                     if stop_data and 'value' in stop_data:
    #                         total_stop_time_seconds += float(stop_data['value']) * 60
    #         
    #         # Add charging time
    #         total_charging_time_seconds = charging_stops_needed * charging_time_minutes * 60
    #         
    #         # Total delivery time = flight + stops + charging
    #         total_delivery_time_seconds = total_flight_time_seconds + total_stop_time_seconds + total_charging_time_seconds
    #         
    #         # Get ready time (same logic as standard ETA)
    #         order = operation.order
    #         ready_time = timezone.now()
    #         
    #         if order.another_info and order.another_info.get('total_ready_time'):
    #             try:
    #                 ready_time_str = order.another_info['total_ready_time']
    #                 ready_time = datetime.strptime(ready_time_str, '%Y%m%d%H%M%S')
    #             except ValueError:
    #                 logger.error(f"Invalid total_ready_time format: {ready_time_str}")
    #         
    #         # Calculate final ETA
    #         delivery_eta = ready_time + timedelta(seconds=total_delivery_time_seconds)
    #         
    #         logger.info(f"🔌 [CHARGING_ETA] ETA with charging breakdown:")
    #         logger.info(f"   ✈️  Flight time: {total_flight_time_seconds/60:.1f} min")
    #         logger.info(f"   ⏱️  Stop time: {total_stop_time_seconds/60:.1f} min") 
    #         logger.info(f"   🔌 Charging time: {total_charging_time_seconds/60:.1f} min ({charging_stops_needed} stops)")
    #         logger.info(f"   📅 Final ETA: {delivery_eta}")
    #         
    #         return delivery_eta
    #         
    #     except Exception as e:
    #         logger.error(f"Error calculating ETA with charging stops: {str(e)}")
    #         return None

    @staticmethod
    def _extract_drone_data_from_orm(drones_queryset) -> tuple:
        """
        OPTIMIZED: Extract all drone data from pre-fetched ORM queryset
        NO additional database queries - all data extracted from memory
        Returns: (capacities, dimensions, batteries, models)
        """
        import time
        extract_start_time = time.time()
        print(f"   📊 [ORM_EXTRACT] Extracting data from {len(drones_queryset)} pre-fetched drones...")
        
        all_drone_capacities = {}
        all_drone_dimensions = {}
        all_drone_batteries = {}
        all_drone_models = {}
        
        # Extract data from pre-fetched ORM objects (NO additional DB queries)
        for drone in drones_queryset:
            drone_id_str = str(drone.id)
            
            try:
                # Extract payload data from pre-fetched cargo_compartments
                cargo_compartment = drone.cargo_compartments.first() if drone.cargo_compartments.exists() else None
                print(f"🔍 [ORM_EXTRACT] Cargo compartment: {cargo_compartment}")
                if cargo_compartment:
                    # Extract weight capacity from pre-fetched measurements
                    weight_measurement = None
                    dimensions_measurement = None
                    battery_measurement = None
                    
                    for measurement in cargo_compartment.measurements.all():
                        if measurement.measurement_type == 'weight_capacity':
                            weight_measurement = measurement
                        elif measurement.measurement_type == 'dimensions':
                            dimensions_measurement = measurement
                        elif measurement.measurement_type == 'battery_capacity':
                            battery_measurement = measurement
                    
                    # Extract weight capacity - CRITICAL DATA (mark as missing if not found)
                    if weight_measurement:
                        weight_data = weight_measurement.data
                        all_drone_capacities[drone_id_str] = {
                            'value': weight_data.get('value', 0),
                            'unit': weight_data.get('unit', 'kg') if isinstance(weight_data, dict) else 'kg',
                            'missing_data': False
                        }
                    else:
                        print(f"      ❌ [DATA_ERROR] Drone {drone.unit_id} (ID: {drone.id}) missing CRITICAL weight_capacity measurement - MARKED FOR DISABLE")
                        all_drone_capacities[drone_id_str] = {
                            'value': 0,
                            'unit': 'kg',
                            'missing_data': True,
                            'missing_reason': 'Missing weight capacity measurement'
                        }
                    
                    # Extract dimensions - CRITICAL DATA (mark as missing if not found)
                    if dimensions_measurement:
                        dimensions_data = dimensions_measurement.data
                        all_drone_dimensions[drone_id_str] = {
                            'length': dimensions_data.get('length', 0),
                            'width': dimensions_data.get('width', 0),
                            'height': dimensions_data.get('height', 0),
                            'unit': dimensions_data.get('unit', 'mm') if isinstance(dimensions_data, dict) else 'mm',
                            'missing_data': False
                        }
                    else:
                        print(f"      ❌ [DATA_ERROR] Drone {drone.unit_id} (ID: {drone.id}) missing CRITICAL dimensions measurement - MARKED FOR DISABLE")
                        all_drone_dimensions[drone_id_str] = {
                            'length': 0,
                            'width': 0,
                            'height': 0,
                            'unit': 'mm',
                            'missing_data': True,
                            'missing_reason': 'Missing dimensions measurement'
                        }
                    
                    # Extract battery capacity - OPTIONAL (can use reasonable default)
                    if battery_measurement:
                        battery_data = battery_measurement.data
                        all_drone_batteries[drone_id_str] = {
                            'value': battery_data.get('value', 0),
                            'unit': battery_data.get('unit', 'mAh') if isinstance(battery_data, dict) else 'mAh'
                        }
                    else:
                        print(f"      ⚠️ [DATA_WARNING] Drone {drone.unit_id} (ID: {drone.id}) missing battery measurement - using reasonable default")
                        all_drone_batteries[drone_id_str] = {"value": 5000, "unit": "mAh"}  # Reasonable default for battery
                else:
                    # No cargo compartment - CRITICAL ERROR (mark for disable)
                    print(f"      ❌ [CRITICAL_ERROR] Drone {drone.unit_id} (ID: {drone.id}) has NO cargo compartment - MARKED FOR DISABLE")
                    all_drone_capacities[drone_id_str] = {
                        'value': 0,
                        'unit': 'kg',
                        'missing_data': True,
                        'missing_reason': 'No cargo compartment found'
                    }
                    all_drone_dimensions[drone_id_str] = {
                        'length': 0,
                        'width': 0,
                        'height': 0,
                        'unit': 'mm',
                        'missing_data': True,
                        'missing_reason': 'No cargo compartment found'
                    }
                    all_drone_batteries[drone_id_str] = {
                        'value': 0,
                        'unit': 'mAh',
                        'missing_data': True,
                        'missing_reason': 'No cargo compartment found'
                    }
                
                # Extract model name from pre-fetched main_type
                if drone.main_type:
                    all_drone_models[drone_id_str] = drone.main_type.name
                else:
                    all_drone_models[drone_id_str] = "Unknown"
                    
            except Exception as e:
                print(f"      ❌ [CRITICAL_ERROR] Error extracting data for drone {drone.unit_id}: {str(e)} - MARKED FOR DISABLE")
                # Mark drone as having critical error instead of skipping
                all_drone_capacities[drone_id_str] = {
                    'value': 0,
                    'unit': 'kg',
                    'missing_data': True,
                    'missing_reason': f'Data extraction error: {str(e)}'
                }
                all_drone_dimensions[drone_id_str] = {
                    'length': 0,
                    'width': 0,
                    'height': 0,
                    'unit': 'mm',
                    'missing_data': True,
                    'missing_reason': f'Data extraction error: {str(e)}'
                }
                all_drone_batteries[drone_id_str] = {
                    'value': 0,
                    'unit': 'mAh',
                    'missing_data': True,
                    'missing_reason': f'Data extraction error: {str(e)}'
                }
                all_drone_models[drone_id_str] = "Unknown"
        
        # Final timing and statistics
        total_extract_time = (time.time() - extract_start_time) * 1000
        total_input_drones = len(drones_queryset)
        valid_drones_processed = len(all_drone_capacities)  # Only count drones that have all required data
        skipped_drones = total_input_drones - valid_drones_processed
        
        print(f"   📊 [ORM_EXTRACT] Completed in {total_extract_time:.2f}ms (ZERO DB queries)")
        print(f"      - Input drones: {total_input_drones}")
        print(f"      - Valid drones: {valid_drones_processed}")
        print(f"      - Skipped drones: {skipped_drones} (missing critical data)")
        if valid_drones_processed > 0:
            print(f"      - Average per valid drone: {total_extract_time/valid_drones_processed:.2f}ms")
        print(f"      - 🚀 PERFORMANCE BOOST: Eliminated {total_input_drones * 3} database queries!")
        
        if skipped_drones > 0:
            print(f"      ⚠️ [DATA_QUALITY] {skipped_drones} drones skipped due to missing critical measurements")
            print(f"         Consider reviewing drone data configuration for better selection accuracy")
        
        return all_drone_capacities, all_drone_dimensions, all_drone_batteries, all_drone_models

    @staticmethod
    def get_drones_for_operation_item_with_full_data(operation_item_id: int, route_id: int, page_size: int = 25, current_page: int = 1, language: str = 'en') -> dict:
        """
        Get complete drone data for operation item with pagination and full processing
        Includes: capacity, location, available payload, disable status, and reason
        
        Args:
            operation_item_id: ID of the delivery operation item
            route_id: ID of the route for optimization
            page_size: Number of items per page (default: 25)
            current_page: Current page number (default: 1)
            language: Language for disable reasons ('en' or 'ko', default: 'en')
        
        Returns:
            dict: {
                'data': list of processed drone data with multilingual disable reasons,
                'total_pages': int,
                'total_items': int,
                'current_page': int
            }
        """
        try:
            import time
            from common.pagination import OptimizedPaginator
            from delivery.services.delivery_system import DeliverySystem
            from devices.schemas.schemas_djantic_out import DeviceOutSchema
            
            print(f"🔄 [FULL_DRONE_DATA] Starting processing for operation_item {operation_item_id}, route {route_id}")
            
            # Get suitable drones with new disable/reason fields and multilingual support
            suitable_drones = ProcessingRepository.get_list_of_drones_by_package_id(operation_item_id, "available", route_id, language)
            
            # Check for duplicates in suitable_drones
            drone_ids = [d['drone'].id for d in suitable_drones]
            unique_drone_ids = set(drone_ids)
            if len(drone_ids) != len(unique_drone_ids):
                # Remove duplicates by keeping first occurrence of each drone ID
                seen_ids = set()
                deduplicated_drones = []
                for drone_data in suitable_drones:
                    drone_id = drone_data['drone'].id
                    if drone_id not in seen_ids:
                        seen_ids.add(drone_id)
                        deduplicated_drones.append(drone_data)
                
                suitable_drones = deduplicated_drones
                print(f"⚠️ [DEDUP] Removed duplicates: {len(suitable_drones)} unique drones")
            
            if not suitable_drones:
                print(f"ℹ️ [FULL_DRONE_DATA] No suitable drones found")
                return {
                    'data': [],
                    'total_pages': 1,
                    'total_items': 0,
                    'current_page': current_page
                }
            
            # Process each drone with full data
            
            drones_data = []
            for i, drone_data in enumerate(suitable_drones):
                try:
                    drone = drone_data['drone']
                    weight_capacity = drone_data['weight_capacity']
                    battery_capacity = drone_data['battery_capacity']
                    dimensions = drone_data['dimensions']
                    model_name = drone_data['model_name']
                    is_disabled = drone_data.get('disable', False)
                    disable_reason = drone_data.get('reason', None)
                    
                    # Create QuerySet for proper serialization
                    drone_queryset = Device.objects.filter(id=drone.id).select_related('main_type').prefetch_related('cargo_compartments__measurements')
                    drone_schema = DeviceOutSchema.from_queryset(drone_queryset, many=False, auto_resolve_fields=True)
                    
                    # Convert to dict and add enhanced data
                    drone_dict = dict(drone_schema)
                    drone_dict['weight_capacity'] = weight_capacity
                    drone_dict['battery_capacity'] = battery_capacity
                    drone_dict['dimensions'] = dimensions
                    drone_dict['model_name'] = model_name
                    drone_dict['disable'] = is_disabled  # NEW FIELD
                    drone_dict['reason'] = disable_reason  # NEW FIELD
                    
                    # Get drone last location
                    try:
                        drone_last_location = DeliverySystem.get_lat_long_drone(drone_dict['unit_id'])
                        drone_dict['last_location'] = drone_last_location
                    except Exception as e:
                        print(f"      ⚠️ Failed to get location for drone {drone.unit_id}: {str(e)}")
                        drone_dict['last_location'] = None
                    
                    # Calculate available payload
                    try:
                        current_load_weight = ProcessingRepository.get_drone_current_load_weight_kg(drone.id)
                        current_load_weight = float(current_load_weight) if current_load_weight is not None else 0.0
                        
                        # Extract weight value from weight_capacity
                        weight_capacity_value = weight_capacity.get('value', 0) if isinstance(weight_capacity, dict) else weight_capacity
                        weight_capacity_value = float(weight_capacity_value) if weight_capacity_value is not None else 0.0
                        
                        available_payload = max(0, weight_capacity_value - current_load_weight)
                        drone_dict['available_payload'] = available_payload
                        
                        print(f"      🔢 Drone {drone.unit_id}: capacity={weight_capacity_value}kg, current_load={current_load_weight}kg, available={available_payload}kg")
                        
                    except Exception as e:
                        print(f"      ⚠️ Failed to calculate payload for drone {drone.unit_id}: {str(e)}")
                        drone_dict['available_payload'] = 0.0
                    
                    drones_data.append(drone_dict)
                    
                    if is_disabled and disable_reason:
                        print(f"⚠️ Drone {drone.unit_id} disabled: {disable_reason.get('message', 'Unknown reason') if isinstance(disable_reason, dict) else disable_reason}")
                        
                except Exception as e:
                    print(f"❌ Error processing drone {i+1}: {str(e)}")
                    continue
            
            
            # Apply pagination
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(drones_data, page_size)
            pages = paginator.page(current_page)
            data = pages.object_list
        
            # Final statistics
            suitable_count = len([d for d in drones_data if not d.get('disable', False)])
            disabled_count = len(drones_data) - suitable_count
            
            print(f"🔄 [FULL_DRONE_DATA] Completed - {len(drones_data)} drones: {suitable_count} suitable, {disabled_count} disabled")
            
            return {
                'data': data,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'current_page': current_page
            }
            
        except Exception as e:
            print(f"❌ [FULL_DRONE_DATA] Error: {str(e)}")
            return {
                'data': [],
                'total_pages': 1,
                'total_items': 0,
                'current_page': current_page
            }

