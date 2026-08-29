import random
import threading
import re
import ast
from ninja import Query, Router
from ninja_extra import NinjaExtraAPI, api_controller, route
from typing import List, Dict, Any, Optional, Union
from ninja.errors import ValidationError
from django.http import HttpRequest
from django.core.serializers.json import DjangoJSONEncoder
from common.pagination import OptimizedPaginator
from django.db.models import Value, IntegerField, Case, When, Count, F, CharField, Q, OuterRef, Subquery
from django.db.models.functions import Concat, Coalesce, Cast
from django.db.models.fields import DateTimeField
from django.contrib.postgres.aggregates import ArrayAgg
from core.common.base_response import BaseResponse
from core.api.v1.auth import CustomJWTAuth
from devices.schemas.schemas_djantic_out import DeviceListOutSchema
from stream_monitors.models import StreamMonitor
from orders.models import Order, OrderHistory
from delivery.models import DeliveryOperation, DeliveryOperationItem
from devices.models import Device
from common.constant import MESSAGE_ENUM, get_message
from delivery.services.delivery_system import DeliverySystem
from delivery.services.processing_service import ProcessingService
from delivery.services.confirmation_service import ConfirmationService
# StatusMappingService removed since status mapping moved to orders app
from delivery.schemas.schemas_djantic_in import (
    AddressSchema,
    CancelOrderSchema,
    SendDataToEtriSchema,
    VerifyOrdersSchema,
    PendingTimeoutSchema,
    ExecuteOrdersSchema,
    UpdateStatusSchema,
    InputListSchema,
    AssignPackagesToDroneSchema,
    UpdateDeliveryEventSchema,
    SendToEtriSchema,
    ReceiveFromEtriSchema,
    AssignPackagesToDronesInSchema,
    CancelFlightInSchema,
    ChangeDroneInSchema,
    ApproveFlightInSchema,
    CancelAwaitingOrderInSchema,
    UploadMissionToGcsInSchema,
    StartMissionToGcsInSchema,
    DroneMonitoringRequestInSchema
    # DeliveryStatusMappingCreateSchema, DeliveryStatusMappingUpdateSchema removed - moved to orders app
)
from delivery.schemas.schemas_djantic_out import (
    DeliveryOperationEtriOutSchema, DeliveryOperationOutSchema, RouteOutSchema, DeviceOutSchema, SelectDroneRowOutSchema,
    VerificationOperationOutSchema, ProcessingOperationOutSchema,
    CompletedOperationOutSchema, ReturnedOperationOutSchema,
    CancelledOperationOutSchema,
    OrderOutSchema,
    DeliveryOperationItemOutSchema,
    DroneStatusSchema,
    DroneDashboardSchema,
    DeliveryStatusOutSchema, DeliveryStatusWithMappingOutSchema
    # DeliveryStatusMappingOutSchema removed - moved to orders app
)
from core.common.search.dynamic_search import build_dynamic_query_from_queryset
from core.common.search.dynamic_search import apply_dynamic_filters
from core.middleware.refresh_token import get_current_request
from delivery.decorators import delivery_operation_execution
from core.role.permission import path_permission
from delivery.services.drone_state_service import DroneStateAnalyzer
import logging
logger = logging.getLogger(__name__)

@api_controller("/verification", tags=["Verification"])
class VerificationController:
    @route.get("/unverified-operations", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/verification')
    def get_unverified_operations(self, request,):
        """Get unverified operations"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        operations = DeliverySystem.get_unverified_operations()
        query = build_dynamic_query_from_queryset(operations, request.GET)
        operations = operations.filter(query)
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(operations, page_size)
        pages = paginator.page(current_page)
        data = VerificationOperationOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get("/verified-operations", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/verification')
    def get_verified_operations(self, request):
        """Get verified operations"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        operations = DeliverySystem.get_verified_operations()
        query = build_dynamic_query_from_queryset(operations, request.GET)
        operations = operations.filter(query)
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(operations, page_size)
        pages = paginator.page(current_page)
        data = VerificationOperationOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.post("/verify-orders")
    @path_permission("update", path_override='/delivery-operation/verification')
    @delivery_operation_execution
    def verify_orders(self, request, data: VerifyOrdersSchema):
        """Verify multiple orders"""
        result = DeliverySystem.verify_orders(data.operation_ids)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.UPDATE_DEVICE_SUCCESS)
        )

    @route.post("/cancel-order/{operation_id}", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/verification')
    def cancel_order(self, request, operation_id: int, data: CancelOrderSchema):
        """Cancel an order"""
        result = DeliverySystem.cancel_order(operation_id, data.reason_note, data.is_system)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.CANCEL_ORDER_SUCCESS)
        )

    @route.get("/print-waybill/{operation_id}/{template_id}", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/verification')
    def print_waybill(self, request, operation_id: int, template_id: int):
        """Print waybill for an order"""
        waybill = DeliverySystem.print_waybill(operation_id, template_id)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS)
        )

@api_controller("/processing", tags=["Processing"])
class ProcessingController:
    @route.get("/routes", auth=CustomJWTAuth(), response=List[RouteOutSchema])
    @path_permission("read", path_override='/delivery-operation/processing')
    @delivery_operation_execution
    def get_list_of_routes(self, request, operation_id: int):
        """Get list of routes"""
        if not operation_id:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.NO_OPERATION_FOUND)
            )

        operation = DeliveryOperation.objects.get(id=operation_id)
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        routes = DeliverySystem.get_list_of_routes(operation)

        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(routes, page_size)
        pages = paginator.page(current_page)
        # data = RouteOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_ROUTE_SUCCESS),
            data=pages.object_list,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get("/drones", auth=CustomJWTAuth(), response=List[DeviceOutSchema])
    @path_permission("read", path_override='/delivery-operation/processing')
    def get_list_of_drones(self, request):
        """Get list of drones"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        drones = DeliverySystem.get_list_of_drones()
        query = build_dynamic_query_from_queryset(drones, request.GET)
        drones = drones.filter(query)
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(drones, page_size)
        pages = paginator.page(current_page)
        data = DeviceOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_DEVICE_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get("/operation-items/{operation_id}", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/processing')
    def get_items_by_processing(self, request, operation_id: int):
        """Get items by processing operation ID"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        items = DeliverySystem.get_items_by_processing(operation_id)
        query = build_dynamic_query_from_queryset(items, request.GET)
        items = items.filter(query)
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(items, page_size)
        pages = paginator.page(current_page)
        data = DeliveryOperationItemOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get("/select-route-operations", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/processing')
    def get_tab_operation_select_route_processing(self, request):
        """Get operations in select route phase"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        operations, routes = DeliverySystem.get_tab_operation_select_route_processing()
        query = build_dynamic_query_from_queryset(operations, request.GET)
        operations = operations.filter(query)
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(operations, page_size)
        pages = paginator.page(current_page)
        data = RouteOutSchema.from_queryset(pages.object_list, many=True)
        routes = RouteOutSchema.from_queryset(routes, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data={
                "operations": data,
                "routes": routes
            },
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get("/select-drone-operations", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/processing')
    def get_tab_operation_select_drone_processing(self, request):
        """Get operations in select drone phase"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        operations, drones = DeliverySystem.get_tab_operation_select_drone_processing()
        query = build_dynamic_query_from_queryset(operations, request.GET)
        operations = operations.filter(query)
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(operations, page_size)
        pages = paginator.page(current_page)
        data = DeliveryOperationOutSchema.from_queryset(pages.object_list, many=True)
        drones = DeviceOutSchema.from_queryset(drones, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data={
                "operations": data,
                "drones": drones
            },
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get("/select-drone-operations/{operation_id}", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/processing')
    def get_tab_operation_select_drone_processing_by_operation_id(self, request, operation_id: int):
        """Get delivery items for a specific operation (simplified version without drone selection)"""
        # Get delivery items directly without drone selection
        delivery_items = DeliveryOperationItem.objects.filter(
            delivery_operation_id=operation_id
        ).select_related(
            'order_item__package_id', 'drone'
        ).prefetch_related('order_item__package_id__measurements').order_by('id')
        print("delivery_items", delivery_items)
        # Format the response
        items_data = []
        for item in delivery_items:
            # Convert delivery item to dict using schema
            item_schema = DeliveryOperationItemOutSchema.from_queryset(item)

            # Add item to response data
            item_dict = dict(item_schema)
            items_data.append(item_dict)

        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=items_data
        )

    @route.get("/get-drones-by-package-and-route-optimized", response=List[DeviceOutSchema])
    def get_drones_by_package_and_route_optimized(self, request, package_id: int, route_id: int):
        """Get suitable drones for a package and route with optimization."""
        try:
            print(f"🚁 [API] Starting drone search for package {package_id}, route {route_id}")

            suitable_drones = DeliverySystem.get_drones_by_package_and_route_optimized(package_id, route_id)

            # Format response
            response_data = []
            for drone_data in suitable_drones:
                drone_dict = {
                    'id': drone_data['id'],
                    'unit_id': drone_data['unit_id'],
                    'name': drone_data['name'],
                    'description': drone_data.get('description', ''),
                    'main_type_id': drone_data.get('main_type_id'),
                    'main_type': drone_data.get('main_type'),
                    'battery_capacity': drone_data.get('battery_capacity'),
                    'payload_capacity': drone_data.get('payload_capacity'),
                    'distance_km': drone_data.get('distance_km'),
                    'terminal_name': drone_data.get('terminal_name'),
                    'eta_minutes': drone_data.get('eta_minutes')
                }

                # Get drone real-time position (OPTIMIZED - batch call)
                try:
                    # OPTIMIZATION: Use the position already calculated in repository
                    # This avoids duplicate API calls since we already have the position
                    if 'real_time_position' in drone_data:
                        drone_dict['last_location'] = drone_data['real_time_position']
                    else:
                        # Fallback: call API only if position not available
                        drone_last_location = DeliverySystem.get_lat_long_drone(drone_dict['unit_id'])
                        drone_dict['last_location'] = drone_last_location
                except Exception as e:
                    drone_dict['last_location'] = {'latitude': 0, 'longitude': 0}

                response_data.append(drone_dict)

            # Sort by distance and ETA
            response_data.sort(key=lambda x: (x.get('distance_km', float('inf')), x.get('eta_minutes', float('inf'))))

            print(f"🚁 [API] Found {len(response_data)} suitable drones")
            return response_data

        except Exception as e:
            print(f"❌ [API] Error: {str(e)}")
            raise ValidationError(f"Failed to get suitable drones: {str(e)}")

    @route.get("/select-drone-operations-items/{operation_item_id}/{route_id}", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/processing')
    def get_tab_operation_select_drone_processing_by_operation_item_id(self, request, operation_item_id: int, route_id: int ):
        """Get suitable drones for a specific operation item with optional route optimization and multilingual support"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))
        language = request.user.language.code if request.user.language else 'en'

        # Validate language parameter
        if language not in ['en', 'ko']:
            language = 'en'  # Default to English for invalid values

        # Use new repository method that handles all processing logic with multilingual support
        from delivery.repository.processing_repository import ProcessingRepository
        result = ProcessingRepository.get_drones_for_operation_item_with_full_data(
            operation_item_id=operation_item_id,
            route_id=route_id,
            page_size=page_size,
            current_page=current_page,
            language=language
        )

        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=result['data'],
            total_pages=result['total_pages'],
            total_items=result['total_items'],
            current_page=result['current_page']
        )

    @route.get("/in-transit-operations", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/processing')
    def get_tab_operation_in_transit_processing(self, request, status_codes: List[str] = Query(None, description="Danh sách mã trạng thái cần lọc")):
        """Get operations in transit phase with streaming data from StreamMonitor"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        # Get operations with streaming data (returns list with processed streaming URLs)
        operations = DeliverySystem.get_tab_operation_in_transit_processing()

        # Apply dynamic filters - need to get the original QuerySet for filtering
        from delivery.repository.processing_repository import ProcessingRepository
        original_operations = ProcessingRepository.get_operation_in_transit_processing()
        filtered_operations = apply_dynamic_filters(original_operations, request, [], request.GET.get('sort_obj', None))

        # Get the IDs of filtered operations
        filtered_ids = list(filtered_operations.values_list('id', flat=True))
        ops_dict = {op.id: op for op in operations}
        # Filter the processed operations list to match the filtered IDs
        filtered_processed_operations = [ops_dict[op_id] for op_id in filtered_ids if op_id in ops_dict]

        # Apply pagination to the filtered list
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(filtered_processed_operations, page_size)
        pages = paginator.page(current_page)

        # Serialize the data - handle list of objects
        data = []
        for operation in pages.object_list:
            # Convert each operation to dict format using the schema
            operation_data = DeliveryOperationOutSchema.from_queryset(operation, many=False)
            data.append(operation_data)

        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.put("/update-route/{operation_id}/{route_id}", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/processing')
    @delivery_operation_execution
    def update_route_to_operation(self, request, operation_id: int, route_id: int):
        """Update route to operation"""
        DeliverySystem.update_route_to_operation(operation_id, route_id)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.UPDATE_ROUTE_SUCCESS),
        )

    @route.put("/update-drone/{operation_item_id}/{drone_id}", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/processing')
    def update_drone_to_operation_item(self, request, operation_item_id: int, drone_id: int):
        """Update drone to operation item"""
        DeliverySystem.update_drone_to_operation_item(operation_item_id, drone_id)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.UPDATE_DEVICE_SUCCESS),
        )

    @route.put("/update-status/{operation_id}", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/processing')
    def update_status_to_operation(self, request, operation_id: int, data: UpdateStatusSchema):
        """Update status to operation"""
        DeliverySystem.update_status_to_operation(operation_id, data.status_code)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.UPDATE_DEVICE_SUCCESS),
        )

    @route.put("/update-is-arrived/{operation_item_id}", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/processing')
    def update_is_arrived_to_operation_item(self, request, operation_item_id: int, is_arrived: bool):
        """Update is_arrived status to operation item"""
        DeliverySystem.update_is_arrived_to_operation_item(operation_item_id, is_arrived)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.UPDATE_DEVICE_SUCCESS),
        )

    @route.put("/update-is-delivered/{operation_item_id}", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/processing')
    def update_is_delivered_by_drone_to_operation_item(self, request, operation_item_id: int, is_delivered_by_drone: bool):
        """Update is_delivered_by_drone status to operation item"""
        DeliverySystem.update_is_delivered_by_drone_to_operation_item(operation_item_id, is_delivered_by_drone)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.UPDATE_DEVICE_SUCCESS),
        )

    @route.post("/assign-packages-to-drone")
    @path_permission("update", path_override='/delivery-operation/processing')
    def assign_packages_to_drone(self, request, data: List[AssignPackagesToDroneSchema]):
        """Assign packages to drone"""
        result = ProcessingService.assign_packages_to_drone(data)
        if result:
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.SELECT_DRONE_SUCCESS),
                data={}
            )
        else:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.SELECT_DRONE_FAILED),
                data={}
            )

    @route.post("/update-delivery-event", auth=CustomJWTAuth())
    # @path_permission("update", path_override='/delivery-operation/processing')
    def update_delivery_event(self, request, data: UpdateDeliveryEventSchema):
        """Update delivery event"""
        try:
            result = ProcessingService.update_delivery_status(data.drone_uid, data.lat, data.lng)
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.UPDATE_DEVICE_SUCCESS),
                data={}
            )
        except ValueError as e:
            logger.error(f"ValueError in update_delivery_event: {str(e)}")
            return BaseResponse(
                status_code=400,
                message=str(e),
                data={}
            )
        except Exception as e:
            logger.error(f"Unexpected error in update_delivery_event: {str(e)}", exc_info=True)
            return BaseResponse(
                status_code=500,
                message=f"Internal server error: {str(e)}",
                data={}
            )
    @route.get("/get-drone-by-route/{route_id}", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/processing')
    def get_drone_by_route(self, request, route_id: int, operation_id: int):
        """Get drone by route"""
        result = ProcessingService.get_drone_by_route(route_id, operation_id)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=result
        )

    @route.post("/assign-packages-to-drones")
    @path_permission("update", path_override='/delivery-operation/processing')
    def assign_packages_to_drones(self, request, data: AssignPackagesToDronesInSchema):
        """Assign packages to drones"""
        success, message = ProcessingService.assign_packages_to_drones(data)
        if success:
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.ASSIGN_PACKAGES_TO_DRONES_SUCCESS),
                data=message
            )
        else:
            # Prefer detailed message from service if present
            detail_msg = message.get('message') if isinstance(message, dict) else None
            error_code = message.get('error') if isinstance(message, dict) else None
            # Map known error codes to multilingual messages

            code_to_enum = {
                'INSUFFICIENT_WEIGHT_CAPACITY': MESSAGE_ENUM.INSUFFICIENT_WEIGHT_CAPACITY,
                'INSUFFICIENT_PACKAGE_SLOTS': MESSAGE_ENUM.INSUFFICIENT_PACKAGE_SLOTS,
                'DIMENSION_NOT_FIT': MESSAGE_ENUM.DIMENSION_NOT_FIT,
            }
            localized = get_message(code_to_enum[error_code]) if error_code in code_to_enum else None
            return BaseResponse(
                status_code=400,
                message=localized or detail_msg or get_message(MESSAGE_ENUM.SELECT_DRONE_FAILED),
                data={"error": error_code, **(message or {})} if isinstance(message, dict) else {"error": "UNKNOWN"}
            )

    @route.post("/cancel-flight", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/processing')
    def cancel_flight(self, request, data: CancelFlightInSchema):
        result = ProcessingService.cancel_flight(data)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.CANCEL_FLIGHT_SUCCESS),
            data=result
        )

    @route.post("/change-drone", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/processing')
    def change_drone(self, request, data: ChangeDroneInSchema):
        result = ProcessingService.change_drone(data)
        if result.get('devices'):
            page_size = int(request.GET.get('page_size', 25))
            current_page = int(request.GET.get('current_page', 1))
            devices = result.get('devices')
            query = apply_dynamic_filters(devices, request.GET, [], request.GET.get('sort_obj', ''))
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(query, page_size)
            pages = paginator.page(current_page)
            result = DeviceListOutSchema.from_queryset(pages.object_list, many=True, auto_resolve_fields=False)
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.GET_LIST_DEVICE_SUCCESS),
                data=result,
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page
            )
        elif result.get('success'):
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.CHANGE_DRONE_SUCCESS),
                data=[]
            )

        else:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.UPDATE_DEVICE_FAILED),
                data=result
            )

    @route.post("/approve-flight", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/processing')
    def approve_flight(self, request, data: ApproveFlightInSchema):
        if data.not_yet:
            ops = ProcessingService.approve_flight_not_yet(data)
            page_size = int(request.GET.get('page_size', 25))
            current_page = int(request.GET.get('current_page', 1))
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(ops, page_size)
            pages = paginator.page(current_page)
            data = SelectDroneRowOutSchema.from_queryset(pages.object_list, many=True)
            for op in data:
                drone = Device._base_manager.filter(id=op['id']).first()
                op['delivery_start_display'] = drone.on_approve_flight
                if drone.approve_flight_now == True:
                    op['delivery_start_active'] = ProcessingService.check_if_all_others_package_are_approved(op['id'], op['order_ids'])
                    op['disable_row'] = True
                else:
                    op['delivery_start_active'] = False
                    op['disable_row'] = ProcessingService.check_is_approved_by_drone(op['id'], op['order_ids'])
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=data,
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page
            )
        else:
            result = ProcessingService.approve_flight(data)
            if result.get('success'):
                return BaseResponse(
                    status_code=200,
                    message=get_message(MESSAGE_ENUM.APPROVE_FLIGHT_SUCCESS),
                    data=result
                )
            else:
                # Build a helpful message including pending drones if available or take from service
                service_message = result.get('message')
                pending = []
                for comp in result.get('components', []):
                    if not comp.get('fully_approved'):
                        pending.extend(comp.get('pending_drone_ids', []))
                pending = sorted(list(set(pending)))
                base_msg = get_message(MESSAGE_ENUM.PENDING_APPROVALS)
                failure_message = service_message or (f"{base_msg} Waiting for drones: {pending}" if pending else base_msg)
                return BaseResponse(
                    status_code=400,
                    message=failure_message,
                    data={"error": result.get('error'), **result}
            )

    @route.post("/cancel-awaiting-order", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/processing')
    def cancel_awaiting_order(self, request, data: CancelAwaitingOrderInSchema):
        result, operations = ProcessingService.cancel_awaiting_order(data)
        if result:
            return BaseResponse(
                    status_code=200,
                    message=get_message(MESSAGE_ENUM.CANCEL_ORDER_SUCCESS),
                    data=DeliveryOperationOutSchema.from_queryset(operations)
                )
        else:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.CANCEL_ORDER_FAILED),
                data=operations
            )

    @route.post("/start-mission-to-gcs", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/processing')
    def start_mission_to_gcs(self, request, data: StartMissionToGcsInSchema):
        result = ProcessingService.gx_start_mission_to_gcs(data)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.UPDATE_DEVICE_SUCCESS),
            data=result
        )

    @route.post("/upload-mission-to-gcs", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/processing')
    def upload_mission_to_gcs(self, request, data: UploadMissionToGcsInSchema):
        try:
            result = ProcessingService.gx_upload_mission_to_gcs(data)
        except ValueError as e:
            logger.error(f"ValueError in upload_mission_to_gcs: {str(e)}")
            return BaseResponse(
                status_code=400,
                message=str(e),
                data=False
            )
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.UPDATE_DEVICE_SUCCESS),
            data=result
        )

@api_controller("/returned", tags=["Returned"])
class ReturnedController:
    @route.get("/due-for-return-operations", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/returned')
    @delivery_operation_execution
    def get_due_for_return_operations(self, request):
        """Get due for return operations"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        operations = DeliverySystem.get_due_for_return_operations()
        query = build_dynamic_query_from_queryset(operations, request.GET)
        operations = operations.filter(query)
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(operations, page_size)
        pages = paginator.page(current_page)
        data = ReturnedOperationOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get("/pending-return-operations", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/returned')
    def get_pending_return_operations(self, request):
        """Get pending return operations"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        operations = DeliverySystem.get_pending_return_operations()
        query = build_dynamic_query_from_queryset(operations, request.GET)
        operations = operations.filter(query)
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(operations, page_size)
        pages = paginator.page(current_page)
        data = ReturnedOperationOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get("/overdue-operations", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/returned')
    def get_overdue_operations(self, request):
        """Get overdue operations"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        operations = DeliverySystem.get_overdue_operations()
        query = build_dynamic_query_from_queryset(operations, request.GET)
        operations = operations.filter(query)
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(operations, page_size)
        pages = paginator.page(current_page)
        data = ReturnedOperationOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get("/returned-operations", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/returned')
    def get_returned_operations(self, request):
        """Get returned operations"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        operations = DeliverySystem.get_returned_operations()
        query = build_dynamic_query_from_queryset(operations, request.GET)
        operations = operations.filter(query)
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(operations, page_size)
        pages = paginator.page(current_page)
        data = ReturnedOperationOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get("/processed-return-operations", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/returned')
    def get_processed_return_operations(self, request):
        """Get processed return operations"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        operations = DeliverySystem.get_processed_return_operations()
        query = build_dynamic_query_from_queryset(operations, request.GET)
        operations = operations.filter(query)
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(operations, page_size)
        pages = paginator.page(current_page)
        data = ReturnedOperationOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get("/check-arrived-timeout/{operation_id}", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/returned')
    def check_arrived_order_timeout_no_pickup(self, request, operation_id: int):
        """Check if arrived order has timed out with no pickup"""
        result = DeliverySystem.check_arrived_order_timeout_no_pickup(operation_id)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=result
        )

    @route.get("/check-pending-timeout/{operation_id}", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-operation/returned')
    def check_pending_order_timeout_no_pickup(self, request, operation_id: int):
        """Check if pending order has timed out with no pickup"""
        result = DeliverySystem.check_pending_order_timeout_no_pickup(operation_id)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=result
        )

    @route.post("/execute-pending-timeout", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/returned')
    def execute_pending_order_timeout_no_pickup(self, request, data: PendingTimeoutSchema):
        """Execute pending order timeout no pickup process"""
        DeliverySystem.execute_pending_order_timeout_no_pickup(data.operation_ids, data.terminal_id)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.RETURN_ORDER_SUCCESS),
        )

    @route.post("/execute-returned", auth=CustomJWTAuth())
    @delivery_operation_execution
    @path_permission("update", path_override='/delivery-operation/returned')
    def execute_returned_order(self, request, data: ExecuteOrdersSchema):
        """Execute returned order process"""
        DeliverySystem.execute_returned_order(data.operation_ids)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.RETURN_ORDER_SUCCESS),
        )

    @route.post("/execute-processed", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/returned')
    def execute_processed_order(self, request, data: ExecuteOrdersSchema):
        """Execute processed order after return"""
        DeliverySystem.execute_processed_order(data.operation_ids)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.RETURN_ORDER_SUCCESS),
        )

@api_controller("/completed", tags=["Completed"])
class CompletedController:
    @route.post("/complete-order/{operation_id}", auth=CustomJWTAuth())
    @delivery_operation_execution
    @path_permission("update", path_override='/delivery-operation/completed')
    def complete_order(self, request, operation_id: int):
        """Complete an order"""
        result = DeliverySystem.complete_order(operation_id)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.UPDATE_DEVICE_SUCCESS)
        )

    @route.post("/complete-orders", auth=CustomJWTAuth())
    @path_permission("update", path_override='/delivery-operation/completed')
    def complete_orders(self, request, data: ExecuteOrdersSchema):
        """Complete multiple orders"""
        result = DeliverySystem.complete_orders(data.operation_ids)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.UPDATE_DEVICE_SUCCESS)
        )

    @route.post("/arrived-order/{operation_id}", auth=CustomJWTAuth())
    @delivery_operation_execution
    @path_permission("update", path_override='/delivery-operation/completed')
    def arrived_order(self, request, operation_id: int):
        """Mark order as arrived"""
        result = DeliverySystem.arrived_order(operation_id)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.UPDATE_DEVICE_SUCCESS)
        )

    @route.get("/arrived-operations", auth=CustomJWTAuth(), response=List[CompletedOperationOutSchema])
    @path_permission("read", path_override='/delivery-operation/completed')
    def get_arrived_operations(self, request):
        """Get arrived operations"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        operations = DeliverySystem.get_arrived_operations()
        query = build_dynamic_query_from_queryset(operations, request.GET)
        operations = operations.filter(query)
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(operations, page_size)
        pages = paginator.page(current_page)
        data = CompletedOperationOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get("/completed-operations", auth=CustomJWTAuth(), response=List[CompletedOperationOutSchema])
    @path_permission("read", path_override='/delivery-operation/completed')
    def get_completed_operations(self, request):
        """Get completed operations"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        operations = DeliverySystem.get_completed_operations()
        query = build_dynamic_query_from_queryset(operations, request.GET)
        operations = operations.filter(query)
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(operations, page_size)
        pages = paginator.page(current_page)
        data = CompletedOperationOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )
    @route.get("download-report/{operation_id}", auth=CustomJWTAuth())
    def download_report(self, request, operation_id: int):
        """Dowload report"""
        result = DeliverySystem.download_report(operation_id)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=result
        )

@api_controller("/delivery-report", tags=["Delivery Report"])
class DeliveryReportController:
    @route.get("/operations", auth=CustomJWTAuth())
    @delivery_operation_execution
    @path_permission("read", path_override='/delivery-report')
    def get_delivery_report_operations(self, request, status_codes: List[str] = Query(None, description="Danh sách mã trạng thái cần lọc")):
        """Get delivery report operations - filtered for completed orders"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        # Default to completed_order if no status_codes provided
        if not status_codes:
            status_codes = ["completed_order"]

        # Only allow completed_order status for delivery report
        if "completed_order" not in status_codes:
            status_codes = ["completed_order"]

        # Get completed operations
        operations = DeliverySystem.get_completed_operations()

        # Get dynamic mapping annotations
        from delivery.services.status_mapping_service import StatusMappingService
        mapping_annotations = StatusMappingService.build_annotate_with_mapping(context='delivery_operation')

        # Apply annotations to queryset before filtering
        operations = operations.annotate(**mapping_annotations)

        # Apply dynamic query filters
        query = apply_dynamic_filters(operations, request, [], request.GET.get('sort_obj', None))

        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(query, page_size)
        pages = paginator.page(current_page)

        data = CompletedOperationOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get("/download-report/{operation_id}", auth=CustomJWTAuth())
    @path_permission("read", path_override='/delivery-report')
    def download_report(self, request, operation_id: int):
        """Download report for completed operation"""
        result = DeliverySystem.download_report(operation_id)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=result
        )

@api_controller("/cancelled", tags=["Cancelled"])
class CancelledController:
    @route.post("/cancel-order/{operation_id}", auth=CustomJWTAuth())
    @delivery_operation_execution
    @path_permission("update", path_override='/cancelled')
    def cancel_order_service(self, request, operation_id: int, data: CancelOrderSchema):
        """Cancel an order using cancellation service"""
        result = DeliverySystem.cancel_order(operation_id, data.reason_note, data.is_system)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.CANCEL_ORDER_SUCCESS)
        )

    @route.get("/cancelled-operations", auth=CustomJWTAuth(), response=List[CancelledOperationOutSchema])
    @path_permission("read", path_override='/cancelled')
    def get_cancelled_operations(self, request):
        """Get cancelled operations"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        operations = DeliverySystem.get_cancelled_operations()
        query = build_dynamic_query_from_queryset(operations, request.GET)
        operations = operations.filter(query)
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(operations, page_size)
        pages = paginator.page(current_page)
        data = CancelledOperationOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

@api_controller("/delivery", tags=["Delivery"])
class DeliveryController:
    @route.get("/operations", auth=CustomJWTAuth())
    @delivery_operation_execution
    @path_permission("read", path_override='/delivery-operation')
    def get_delivery_operations(self, request, status_codes: List[str] = Query(None, description="Danh sách mã trạng thái cần lọc")):
        """Get delivery operations"""
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        # Get operations based on status codes
        operations = None
        if status_codes:
            # Group status codes by their type
            verification_codes = [code for code in status_codes if code in ["unverified_order", "verified_order"]]
            processing_codes = [code for code in status_codes if code in ["select_route_processing", "select_drone_processing", "in_transit_processing"]]
            completed_codes = [code for code in status_codes if code in ["arrived_order", "completed_order"]]
            returned_codes = [code for code in status_codes if code in ["order_due_for_returned", "order_pending_returned", "overdue_order", "returned_order", "processed_order"]]
            cancelled_codes = [code for code in status_codes if code == "cancelled"]

            # Collect operations from all relevant services
            operations_list = []

            # Get verification operations
            if verification_codes:
                if "unverified_order" in verification_codes:
                    operations_list.append(DeliverySystem.get_unverified_operations())
                if "verified_order" in verification_codes:
                    operations_list.append(DeliverySystem.get_verified_operations())

            # Get processing operations
            if processing_codes:
                if "select_route_processing" in processing_codes:
                    ops = DeliverySystem.get_tab_operation_select_route_processing()
                    operations_list.append(ops)
                if "select_drone_processing" in processing_codes:
                    ops, _ = DeliverySystem.get_tab_operation_select_drone_processing()
                    ops = apply_dynamic_filters(ops, request, [], request.GET.get('sort_obj', None))
                    # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
                    paginator = OptimizedPaginator(ops, page_size)
                    pages = paginator.page(current_page)
                    data = SelectDroneRowOutSchema.from_queryset(pages.object_list, many=True)
                    for op in data:
                        drone = Device._base_manager.filter(id=op['id']).first()
                        op['delivery_start_display'] = drone.on_approve_flight
                        if drone.approve_flight_now == True:
                            op['delivery_start_active'] = ProcessingService.check_if_all_others_package_are_approved(op['id'], op['order_ids'])
                            op['disable_row'] = True
                        else:
                            op['delivery_start_active'] = False
                            op['disable_row'] = ProcessingService.check_is_approved_by_drone(op['id'], op['order_ids'])
                        op['is_upload_mission'] = ProcessingService.check_drone_upload_mission_by_order_ids(op['order_ids'], drone)
                    return BaseResponse(
                        status_code=200,
                        message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                        data=data,
                        total_pages=paginator.num_pages,
                        total_items=paginator.count,
                        current_page=current_page
                    )
                if "in_transit_processing" in processing_codes:
                    operations_list.append(DeliverySystem.get_tab_operation_in_transit_processing())

            # Get completed operations
            if completed_codes:
                if "arrived_order" in completed_codes:
                    operations_list.append(DeliverySystem.get_arrived_operations())
                if "completed_order" in completed_codes:
                    operations_list.append(DeliverySystem.get_completed_operations())

            # Get returned operations
            if returned_codes:
                if "order_due_for_returned" in returned_codes:
                    operations_list.append(DeliverySystem.get_due_for_return_operations())
                if "order_pending_returned" in returned_codes:
                    operations_list.append(DeliverySystem.get_pending_return_operations())
                if "overdue_order" in returned_codes:
                    operations_list.append(DeliverySystem.get_overdue_operations())
                if "returned_order" in returned_codes:
                    operations_list.append(DeliverySystem.get_returned_operations())
                if "processed_order" in returned_codes:
                    operations_list.append(DeliverySystem.get_processed_return_operations())

            # Get cancelled operations
            if cancelled_codes:
                operations_list.append(DeliverySystem.get_cancelled_operations())

            # Combine all operations
            if operations_list:
                # Get all operation IDs from different querysets while preserving order
                operation_ids = []
                seen_ids = set()
                for ops in operations_list:
                    if ops and hasattr(ops, 'values_list'):
                        try:
                            for op_id in ops.values_list('id', flat=True):
                                if op_id not in seen_ids:
                                    operation_ids.append(op_id)
                                    seen_ids.add(op_id)
                        except Exception:
                            continue

                if operation_ids:
                    # Create a simple queryset without complex annotations to avoid conflicts
                    # Using Case/When to preserve order based on the original list
                    preserved_order = Case(
                        *[When(id=pk, then=pos) for pos, pk in enumerate(operation_ids)],
                        output_field=IntegerField()
                    )

                    operations = DeliveryOperation.objects.filter(id__in=operation_ids).annotate(
                        preserved_order=preserved_order
                    ).order_by('preserved_order')

                    # Add basic annotations that are commonly needed
                    # try:
                        # Get latest cancellation subquery
                    from delivery.models import DeliveryCancellation
                    latest_cancellation = DeliveryCancellation.objects.filter(
                        delivery_operation=OuterRef('pk')
                    ).order_by('-id')

                    # Get dynamic mapping annotations
                    from delivery.services.status_mapping_service import StatusMappingService

                    # Get group context for mapping

                    mapping_annotations = StatusMappingService.build_annotate_with_mapping(context='delivery_operation')
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
                    operations = operations.annotate(
                        number_of_packages=Count('order__items__id', distinct=True),
                        order_identifier=Coalesce(
                            F('order__order_code'),
                            Cast(F('another_info__anyang__itemOrgId'), CharField()),
                            Cast(F('another_info__etri__receipt_id'), CharField()),
                            output_field=CharField()
                        ),
                        receipt_number=Coalesce(
                            Cast(F('another_info__etri__receipt_number'), CharField()),
                            Cast(F('another_info__anyang__receipt_number'), CharField()),
                            F('order__order_code'),
                            output_field=CharField()
                        ),
                        handler=Concat(F('order__created_by__first_name'), Value(' '), F('order__created_by__last_name'), output_field=CharField()),
                        tracking_number=Cast(F('another_info__etri__tracking_number'), CharField()),
                        reason_for_rejection=Coalesce(
                            Subquery(latest_cancellation.values('reason')[:1]),
                            F('order__cancel_reason'),
                            output_field=CharField()
                        ),
                        cancel_reason=Coalesce(
                            Subquery(latest_cancellation.values('reason')[:1]),
                            F('order__cancel_reason')
                        ),
                        origin=Subquery(origin_subquery, output_field=CharField()),
                        destination=Subquery(destination_subquery, output_field=CharField()),
                        order_terminal_id=F('order__delivery_terminal_id'),
                        streamming_data=ArrayAgg('items__drone__streammonitor__code', filter=Q(items__drone__streammonitor__is_active=True), distinct=True),
                        # Cancel time với logic ưu tiên OrderHistory trước
                        cancel_time=Coalesce(
                            # Lấy từ OrderHistory action 'cancelled' trước
                            Subquery(
                                OrderHistory.objects.filter(
                                    order=OuterRef('order'),
                                    action='cancelled'
                                ).values('created_on')[:1]
                            ),
                            # Nếu không có thì lấy từ action 'receipt_cancelled'
                            Subquery(
                                OrderHistory.objects.filter(
                                    order=OuterRef('order'),
                                    action='receipt_cancelled'
                                ).values('created_on')[:1]
                            ),
                            # Cuối cùng lấy từ DeliveryCancellation
                            Subquery(latest_cancellation.values('cancelled_at')[:1]),
                            output_field=DateTimeField()
                        ),
                        # Cancelled by name với logic ưu tiên OrderHistory trước
                        cancelled_by__name=Coalesce(
                            # Lấy từ OrderHistory action 'cancelled' trước
                            Subquery(
                                OrderHistory.objects.filter(
                                    order=OuterRef('order'),
                                    action='cancelled'
                                ).annotate(
                                    full_name=Concat(
                                        F('created_by__first_name'),
                                        Value(' '),
                                        F('created_by__last_name'),
                                        output_field=CharField()
                                    )
                                ).values('full_name')[:1]
                            ),
                            # Nếu không có thì lấy từ action 'receipt_cancelled'
                            Subquery(
                                OrderHistory.objects.filter(
                                    order=OuterRef('order'),
                                    action='receipt_cancelled'
                                ).annotate(
                                    full_name=Concat(
                                        F('created_by__first_name'),
                                        Value(' '),
                                        F('created_by__last_name'),
                                        output_field=CharField()
                                    )
                                ).values('full_name')[:1]
                            ),
                            # Cuối cùng lấy từ DeliveryCancellation
                            Subquery(
                                latest_cancellation.annotate(
                                    full_name=Concat(
                                        F('cancelled_by__first_name'),
                                        Value(' '),
                                        F('cancelled_by__last_name'),
                                        output_field=CharField()
                                    )
                                ).values('full_name')[:1]
                            ),
                            Value(None),
                            output_field=CharField()
                        ),
                        creator=Concat(F('order__created_by__first_name'), Value(' '), F('order__created_by__last_name'), output_field=CharField()),
                        # Apply dynamic mapping
                        **mapping_annotations,
                        order__id = F('order__id'),
                        order__order_code = F('order__order_code'),
                        order__sender_name = F('order__sender_name'),
                        order__recipient_name = F('order__recipient_name'),
                        order__created_on = F('order__created_on'),
                    )
                    # except Exception as e:
                    #     # If annotation fails, use basic queryset
                    #     operations = DeliveryOperation.objects.filter(id__in=operation_ids).annotate(
                    #         preserved_order=preserved_order
                    #     ).order_by('preserved_order')

        # Apply dynamic filters and pagination
        if operations:
            operations = apply_dynamic_filters(operations, request, [], request.GET.get('sort_obj', None))
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(operations, page_size)
            pages = paginator.page(current_page)
            data = DeliveryOperationOutSchema.from_queryset(pages.object_list, many=True)
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=data,
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page
            )

        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=[],
            total_pages=0,
            total_items=0,
            current_page=current_page
        )


    @route.get("/get-delivery-for-etri", auth=CustomJWTAuth())
    @path_permission("read", path_override='/etri-tracking')
    def get_delivery_for_etri(self, request):
        """
        Get delivery operations for ETRI with mapped status names and images
        Status mapping:
        - Unverified -> Received
        - Canceled -> Canceled
        - Select route & Select drone -> Pending shipment
        - Intransit -> Intransit
        - Completed -> Shipped

        Supports dynamic search and sorting via query parameters:
        - Search by order code, status, mapped_status, recipient info
        - Sort by any field including mapped_status
        """
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        # Get QuerySet with mapped_status annotation
        operations = DeliverySystem.get_delivery_for_etri()

        # Apply dynamic filters and sorting
        operations = apply_dynamic_filters(
            operations,
            request,
            [],
            request.GET.get('sort_obj', None)
        )

        # Apply pagination on QuerySet
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(operations, page_size)
        pages = paginator.page(current_page)

        # Format the paginated data with images and additional info
        formatted_data = DeliveryOperationEtriOutSchema.from_queryset(pages.object_list, many=True)

        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=formatted_data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

@api_controller("/drone-monitoring", tags=["Drone Monitoring"])
class DroneMonitoringController:
    @route.get("/drone-status")
    def get_drone_status_monitoring(self, request, unique_id: Optional[str] = None, msg_type: Optional[str] = None):
        """
        Retrieve drone status monitoring data (GET method for backward compatibility).

        Parameters:
        - unique_id (optional): Unique ID of the drone to view details
        - msg_type (optional): Message type to filter (RAW_IMU, VIBRATION, SCALED_PRESSURE, RC_CHANNELS, SERVO_OUTPUT_RAW, etc.)

        Behavior:
        - If `unique_id` is not provided, the API returns all active drones.
        - If `unique_id` is provided but `msg_type` is not, the API returns all measurement data from that drone including RC channels and servo outputs.
        - If both `unique_id` and `msg_type` are provided, the API returns raw data from OpenSearch filtered by message type.
        """
        if not unique_id:
            # Case 1: No unique_id provided – return all active drones
            data = ProcessingService.get_drone_status_dashboard()
        elif not msg_type:
            # Case 2: unique_id provided but no msg_type – return detailed measurement data
            data = ProcessingService.get_drone_status_dashboard(unique_id)
        else:
            # Case 3: Both unique_id and msg_type provided – return raw OpenSearch data
            data = ProcessingService.get_opensearch_data_service(
                unique_id=unique_id,
                msg_type=msg_type,
                size=100
            )

        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=data
        )

    @route.post("/drone-status")
    def post_drone_status_monitoring(self, request, data: DroneMonitoringRequestInSchema):
        """
        Retrieve drone status monitoring data with selected monitoring items (POST method).

        Request body:
        {
            "unique_id": "drone_3_1_conn_4ef01b03",
            "monitoring_items": ["x-axis", "y-axis", "z-axis", "vibe", "ch1in", "ch2out", ...],
            "time_window_minutes": 15
        }

        Returns filtered data based on selected monitoring items.
        """
        print(f"✅ [DRONE_MONITORING] Data: {data}")
        # Get telemetry data with filtering
        result = ProcessingService.get_drone_telemetry_by_unique_id_filtered(
            unique_id=data.unique_id,
            monitoring_items=data.monitoring_items,
            time_window_minutes=data.time_window_minutes or 15
        )

        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
            data=result
        )

@api_controller("/order-confirmation", tags=["Order Confirmation"])
class OrderConfirmationController:
    @route.post("/{package_id}", auth=CustomJWTAuth())
    def confirm_order(self, request, package_id: int):
        """Confirm order"""
        confirmation = ConfirmationService.confirm_order(package_id)
        if confirmation["status"] == "success":
            return BaseResponse(status_code=200, message=get_message(MESSAGE_ENUM.CONFIRM_ORDER_SUCCESS), data=confirmation)
        else:
            return BaseResponse(status_code=400, message=get_message(MESSAGE_ENUM.CONFIRM_ORDER_FAILED), data=confirmation)

@api_controller("/etri-integration", tags=["ETRI Integration"])
class EtriIntegrationController:
    @staticmethod
    def _normalize_path_to_list(path: Union[str, List[List[float]]]) -> List[List[float]]:
        """
        Normalize path data to list format (format chuẩn của hệ thống).
        Converts string format "[(lat, lng), ...]" hoặc "'[(lat, lng), ...]'" to list format [[lat, lng], ...]
        Hỗ trợ cả string có nháy đơn bên ngoài: "'[(36.6485432, 126.6714442)]'"
        """
        if isinstance(path, list):
            # Đã là list format rồi, return nguyên
            return path
        elif isinstance(path, str):
            # Strip các nháy đơn hoặc nháy kép bên ngoài nếu có
            path = path.strip()
            if (path.startswith("'") and path.endswith("'")) or (path.startswith('"') and path.endswith('"')):
                path = path[1:-1]

            # Parse string format "[(lat, lng), (lat2, lng2), ...]" thành list
            try:
                # Sử dụng ast.literal_eval để parse an toàn
                parsed = ast.literal_eval(path)
                if isinstance(parsed, list):
                    # Nếu là list of tuples, convert sang list of lists
                    if parsed and isinstance(parsed[0], tuple):
                        return [[float(coord[0]), float(coord[1])] for coord in parsed]
                    # Nếu đã là list of lists, return nguyên
                    return [[float(coord[0]), float(coord[1])] for coord in parsed]
                return parsed
            except (ValueError, SyntaxError):
                # Fallback: parse bằng regex nếu ast.literal_eval fail
                # Tìm tất cả các tuple (lat, lng)
                pattern = r'\(([\d.]+),\s*([\d.]+)\)'
                matches = re.findall(pattern, path)
                if matches:
                    return [[float(match[0]), float(match[1])] for match in matches]
                return []
        else:
            return []

    @route.post("/send-to-etri/{operation_id}", auth=CustomJWTAuth())
    def send_delivery_to_etri(self, request, operation_id: int):
        """
        API 7: GAION 운영 시스템 → ETRI 관제 시스템 송신 API
        Send delivery operation data to ETRI system
        """
        try:
            # Get delivery operation
            delivery_operation = DeliveryOperation.objects.select_related(
                'order',
                'order__recipient_address',
                'order__pickup_location',
                'order__created_by'
            ).prefetch_related(
                'order__items__item_type'
            ).get(id=operation_id)

            # Send to ETRI
            result = DeliverySystem.send_delivery_to_etri(delivery_operation, request)

            if result['success']:
                return BaseResponse(
                    status_code=200,
                    message=get_message(MESSAGE_ENUM.UPDATE_DEVICE_SUCCESS),
                    data=result
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=result['message'],
                    data=result
                )

        except DeliveryOperation.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=get_message(MESSAGE_ENUM.NO_OPERATION_FOUND)
            )
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"Unexpected error: {str(e)}"
            )

    @route.post("/receive-from-etri")
    def receive_status_from_etri(self, request, data: ReceiveFromEtriSchema):
        """
        API 8: ETRI 관제 시스템 → GAION 운영 시스템 송신 API
        Receive delivery status update from ETRI system

        Hỗ trợ cả 2 format, normalize về list format (format chuẩn):
        - String format: "[(36.6485432, 126.6714442)]" -> [[36.6485432, 126.6714442]]
        - List format: [[36.6485432, 126.6714442]] -> giữ nguyên
        """
        try:
            # Convert schema to dict
            etri_data = dict(data)

            # Normalize path fields to list format (format chuẩn của hệ thống)
            if 'DRONE_PATH' in etri_data:
                etri_data['DRONE_PATH'] = self._normalize_path_to_list(etri_data['DRONE_PATH'])
            if 'ROBOT_PATH' in etri_data:
                etri_data['ROBOT_PATH'] = self._normalize_path_to_list(etri_data['ROBOT_PATH'])
            if 'DOCKING_POINT' in etri_data:
                etri_data['DOCKING_POINT'] = self._normalize_path_to_list(etri_data['DOCKING_POINT'])

            # Process ETRI status update
            result = DeliverySystem.receive_status_from_etri(etri_data, request)

            if result['success']:
                return BaseResponse(
                    status_code=200,
                    message=get_message(MESSAGE_ENUM.UPDATE_DEVICE_SUCCESS),
                    data=result
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=result['message'],
                    data=result
                )

        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                message="Validation error",
                data={"errors": e.errors()}
            )
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"Unexpected error: {str(e)}"
            )

    @route.get("/etri-data-format/{operation_id}", auth=CustomJWTAuth())
    def get_etri_data_format(self, request, operation_id: int):
        """
        Get delivery operation data in ETRI format for testing/preview
        """
        try:
            # Get delivery operation
            delivery_operation = DeliveryOperation.objects.select_related(
                'order',
                'order__recipient_address',
                'order__pickup_location',
                'order__created_by'
            ).prefetch_related(
                'order__items__item_type'
            ).get(id=operation_id)

            # Get ETRI formatted data
            from delivery.services.etri_service import EtriService
            etri_data = EtriService._prepare_etri_data(delivery_operation, request)

            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=etri_data
            )

        except DeliveryOperation.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=get_message(MESSAGE_ENUM.NO_OPERATION_FOUND)
            )
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"Unexpected error: {str(e)}"
            )

@api_controller("/etri-mock", tags=["ETRI Mock APIs (Development Only)"])
class EtriMockController:
    """Mock ETRI APIs for development testing"""

    @route.post("/receive-delivery")
    def mock_receive_delivery(self, request, data: SendToEtriSchema):
        """
        Mock ETRI API - Receive delivery data from GAION
        Simulates ETRI system receiving delivery operation data
        """
        try:
            # Simulate ETRI processing
            etri_data = dict(data)

            # Mock response scenarios based on data
            receipt_id = etri_data.get('RECEIPT_ID')
            mission_id = etri_data.get('MISSION_ID')
            # Simulate different response scenarios
            import random
            scenario = random.choice(['success'])

            if scenario == 'success':
                return {
                    "status": "success",
                    "message": "Delivery data received successfully",
                    "data": {
                        "RECEIPT_ID": receipt_id,
                        "MISSION_ID": mission_id,
                        "ETRI_TRACKING_ID": f"ETRI_{receipt_id}_{random.randint(1000, 9999)}",
                        "ESTIMATED_DELIVERY_TIME": "2024-12-26 14:30:00",
                        "ASSIGNED_DRONE_ID": f"DRONE_{random.randint(100, 999)}",
                        "STATUS": "ACCEPTED"
                    }
                }
            elif scenario == 'validation_error':
                return BaseResponse(
                    status_code=400,
                    message="Validation error in ETRI system",
                    data={
                        "error_code": "VALIDATION_ERROR",
                        "errors": [
                            "RECEIVER_ADDRESS is required",
                            "WEIGHT must be greater than 0"
                        ]
                    }
                )
            else:
                return BaseResponse(
                    status_code=500,
                    message="ETRI system temporarily unavailable",
                    data={
                        "error_code": "SYSTEM_ERROR",
                        "retry_after": 300
                    }
                )

        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"Mock ETRI API error: {str(e)}"
            )

    @route.post("/send-status-update", auth=CustomJWTAuth())
    def mock_send_status_update(self, request, data: SendDataToEtriSchema):
        """
        Mock API to simulate ETRI sending status updates to GAION
        Use this to test the receive-from-etri endpoint
        """
        try:
            # Get a random delivery operation for testing
            from delivery.models import DeliveryOperation
            # Get delivery operations that have receipt_id in another_info
            operations = DeliveryOperation.objects.filter(
                id=data.operation_id,
                another_info__etri__receipt_id__isnull=False
            ).exclude(another_info__etri__receipt_id='')
            if not operations.exists():
                return BaseResponse(
                    status_code=404,
                    message="No delivery operations found for testing"
                )
            if not OrderHistory.objects.filter(
                order=operations.first().order,
                action='verified'
            ).exists():
                return BaseResponse(
                    status_code=400,
                    message="Delivery operation is not verified"
                )
            # Get the specific operation
            operation = operations.first()
            receipt_id = operation.another_info.get('etri', {}).get('receipt_id')

            # Generate mock status update data with all ETRI status values (0-5)
            mock_statuses = [
                {
                    "MISSION_STATUS": 0,  # 배송완료 -> delivered
                    "STATUS_NAME": "Delivery Completed",
                    "DESCRIPTION": "Delivery is complete (when the control system receives information that delivery is complete)",
                    "CANCELLATION_REASON": None
                },
                {
                    "MISSION_STATUS": 1,  # 배송취소 -> cancelled
                    "STATUS_NAME": "Delivery Cancelled",
                    "DESCRIPTION": "Delivery is rejected or delivery failed",
                    "CANCELLATION_REASON": random.choice([
                        "날씨",
                        "기체고장",
                        "물품상태 이상",
                    ])
                },
                {
                    "MISSION_STATUS": 2,  # 배송중 -> in_transit_processing
                    "STATUS_NAME": "In Delivery",
                    "DESCRIPTION": "Delivery is in progress (when the control system receives information that delivery has started)",
                    "CANCELLATION_REASON": None
                },
                {
                    "MISSION_STATUS": 3,  # 배송대기 -> awaiting_shipment
                    "STATUS_NAME": "Waiting for Delivery",
                    "DESCRIPTION": "The operator has completed the delivery acceptance process, but delivery has not yet started",
                    "CANCELLATION_REASON": None
                },
                {
                    "MISSION_STATUS": 4,  # 접수완료 -> pending_confirmation
                    "STATUS_NAME": "Receipt Completed",
                    "DESCRIPTION": "The acceptance has been completed, but the operator has not confirmed it",
                    "CANCELLATION_REASON": None
                },
                {
                    "MISSION_STATUS": 5,  # 접수취소 -> receipt_cancelled
                    "STATUS_NAME": "Receipt Cancelled",
                    "DESCRIPTION": "The operator or the orderer cancellation of application",
                    "CANCELLATION_REASON": random.choice([
                       "날씨",
                        "기체고장",
                        "물품상태 이상",
                    ])
                }
            ]

            selected_status = random.choice(mock_statuses)

            # Generate transmission data as shown in the image
            from datetime import datetime, timedelta
            from delivery.config.route_dummy_data import get_random_route

            mission_date = datetime.now() + timedelta(hours=random.randint(1, 48))
            receipt_date = datetime.now()

            # Get random route data
            selected_route = get_random_route()
            # drone_path = selected_route["drone_path"]
            # robot_path = selected_route["robot_path"]
            docking_point = selected_route["docking_point"]
            def generate_coordinates_list(count=5):
                base_lat, base_lng = 37.5665, 126.9780  # Seoul coordinates
                coords = []
                for i in range(count):
                    lat = base_lat + random.uniform(-0.01, 0.01)
                    lng = base_lng + random.uniform(-0.01, 0.01)
                    coords.append((round(lat, 3), round(lng, 3)))
                return coords
            def generate_robot_coordinates_list(start_coord, count=5):
                """Generate robot path starting from drone's end point"""
                coords = [start_coord]  # Start with drone's end point
                current_lat, current_lng = start_coord
                for i in range(count - 1):
                    # Generate next coordinates based on current position
                    current_lat += random.uniform(-0.005, 0.005)
                    current_lng += random.uniform(-0.005, 0.005)
                    coords.append((round(current_lat, 3), round(current_lng, 3)))
                return coords

            # Generate drone path first
            drone_path = generate_coordinates_list(5)
            # Generate robot path starting from drone's end point
            robot_path = generate_robot_coordinates_list(drone_path[-1], 5)
            # Create complete transmission data format
            mock_data = {
                # GAION to ETRI transmission format
                "CONTROL_ID": "gcs_user_001",
                "USER_ID": "gaion_user_001",
                "ORG_ID": "gaion",
                "RECEIPT_ID": receipt_id,
                "MISSION_ID": f"ms_gaion_{receipt_id}",
                "RECEIPT_DATE": receipt_date.strftime("%Y-%m-%d %H:%M:%S"),
                "MISSION_STATUS": selected_status["MISSION_STATUS"],
                "CANCELLATION_REASON": "",
                "MISSION_DATE": mission_date.strftime("%Y-%m-%d %H:%M:%S"),
                "DRONE_PATH": drone_path,  # List of GPS coordinates from real Korean routes
                "ROBOT_PATH": robot_path,  # List of GPS coordinates from real Korean routes
                "DOCKING_POINT": docking_point,  # Docking point from real Korean routes
                "ROUTE_NAME": selected_route["name"],  # Route name for reference
                "ROUTE_ID": selected_route["id"],  # Route ID for reference
                "DRONE_PATH_DISTANCE": selected_route["drone_path_distance"],  # Calculated distance in km
                "ROBOT_PATH_DISTANCE": selected_route["robot_path_distance"]   # Calculated distance in km
            }

            # Add cancellation reason if status is cancelled (1)
            if selected_status["MISSION_STATUS"] == 1 and selected_status["CANCELLATION_REASON"]:
                mock_data["CANCELLATION_REASON"] = selected_status["CANCELLATION_REASON"]

            # Update operation with transmission data using organized structure
            if not operation.another_info:
                operation.another_info = {}

            # Get or create etri section for organized data structure
            etri_info = operation.another_info.get('etri', {})

            # Update etri section with transmission data
            user = operation.order.created_by
            group_code = user.userprofilelink.group.code if user.userprofilelink.group else None
            tracking_number = f"ms_{group_code}_{str(operation.order.id).zfill(6)}"
            etri_info.update({
                'mission_id': mock_data["MISSION_ID"],
                'control_id': mock_data["CONTROL_ID"],
                'receipt_id': mock_data["RECEIPT_ID"],
                'tracking_number': tracking_number,
                'transmission_data': mock_data,
                'last_mock_update': datetime.now().isoformat(),
            })

            operation.another_info['etri'] = etri_info
            operation.save()

            # Send to our own receive endpoint
            from delivery.services.etri_service import EtriService
            result = EtriService.receive_status_from_etri(mock_data, request)

            return BaseResponse(
                status_code=200,
                message="Mock status update sent successfully with complete transmission data",
                data={
                    "sent_data": mock_data,
                    "processing_result": result,
                    "selected_operation_id": operation.id,
                    "status_description": selected_status,
                    "transmission_format_note": "Includes both GAION->ETRI transmission format and status update data"
                }
            )

        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"Mock status update error: {str(e)}"
            )



    @route.get("/test-scenarios")
    def get_test_scenarios(self, request):
        """
        Get available test scenarios for ETRI integration testing
        """
        scenarios = {
            "send_to_etri_scenarios": [
                {
                    "name": "Success Response",
                    "description": "ETRI accepts delivery data successfully",
                    "probability": "70%"
                },
                {
                    "name": "Validation Error",
                    "description": "ETRI returns validation errors",
                    "probability": "20%"
                },
                {
                    "name": "System Error",
                    "description": "ETRI system temporarily unavailable",
                    "probability": "10%"
                }
            ],
            "receive_from_etri_scenarios": [
                {
                    "status_code": 0,
                    "status_name": "Delivery Completed",
                    "gaion_status": "delivered",
                    "description": "Delivery is complete (when the control system receives information that delivery is complete)"
                },
                {
                    "status_code": 1,
                    "status_name": "Delivery Cancelled",
                    "gaion_status": "cancelled",
                    "description": "Delivery is rejected or delivery failed (reason for cancellation must also be indicated)"
                },
                {
                    "status_code": 2,
                    "status_name": "In Delivery",
                    "gaion_status": "in_transit_processing",
                    "description": "Delivery is in progress (when the control system receives information that delivery has started)"
                },
                {
                    "status_code": 3,
                    "status_name": "Waiting for Delivery",
                    "gaion_status": "awaiting_shipment",
                    "description": "The operator has completed the delivery acceptance process, but delivery has not yet started"
                },
                {
                    "status_code": 4,
                    "status_name": "Receipt Completed",
                    "gaion_status": "pending_confirmation",
                    "description": "The acceptance has been completed, but the operator has not confirmed it"
                },
                {
                    "status_code": 5,
                    "status_name": "Receipt Cancelled",
                    "gaion_status": "receipt_cancelled",
                    "description": "The operator or the orderer cancellation of application"
                }
            ],
            "test_endpoints": {
                "send_to_etri": "/api/etri-integration/send-to-etri/{operation_id}",
                "receive_from_etri": "/api/etri-integration/receive-from-etri",
                "mock_etri_receive": "/api/etri-mock/receive-delivery",
                "mock_status_update": "/api/etri-mock/send-status-update",
                "etri_data_format": "/api/etri-integration/etri-data-format/{operation_id}"
            }
        }

        return BaseResponse(
            status_code=200,
            message="ETRI test scenarios retrieved successfully",
            data=scenarios
        )

# Remove old status mapping controllers and their routes
# StatusMappingController, get_all_delivery_statuses, get_status_mappings, get_status_mapping_detail, create_status_mapping, update_status_mapping, delete_status_mapping

controllers = [
    VerificationController,
    ProcessingController,
    ReturnedController,
    CompletedController,
    CancelledController,
    DroneMonitoringController,
    DeliveryController,
    DeliveryReportController,
    OrderConfirmationController,
    EtriIntegrationController,
    EtriMockController,
]
