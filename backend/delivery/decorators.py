import json
import functools
import requests
from common.external_http import default_timeout
from django.http import JsonResponse
from delivery.constants import DELIVERY_STATUS_LIST
import logging
from ninja import Schema
from typing import Optional, Dict, Any, List
from delivery.schemas.schemas_djantic_out import (
    DeliveryOperationOutSchema,
    DeliveryOperationItemOutSchema,
    RouteOutSchema,
    DeviceOutSchema
)
from delivery.models import (
    DeliveryOperation,
    DeliveryStatus,
    DeliveryOperationHistory
)
from delivery.services.verification_service import VerificationService
from delivery.services.processing_service import ProcessingService
from delivery.services.completed_service import CompletedService
from delivery.services.returned_service import ReturnedService
from delivery.services.cancelled_service import CancelledService

logger = logging.getLogger(__name__)

# Define response schemas for each endpoint
class VerifiedOrderResponse(Schema):
    status: str
    operation_id: Optional[int] = None
    processed_operations: Optional[List[int]] = None
    verification_details: Optional[Dict[str, Any]] = None

class SelectRouteResponse(Schema):
    status: str
    operation_id: Optional[int] = None
    route_id: Optional[str] = None
    route_details: Optional[Dict[str, Any]] = None

class SelectDroneResponse(Schema):
    status: str
    operation_id: Optional[int] = None
    drone_id: Optional[str] = None
    drone_details: Optional[Dict[str, Any]] = None

class InTransitResponse(Schema):
    status: str
    operation_id: Optional[int] = None
    delivery_details: Optional[Dict[str, Any]] = None

class ArrivedOrderResponse(Schema):
    status: str
    operation_id: Optional[int] = None
    arrival_details: Optional[Dict[str, Any]] = None

class CompletedOrderResponse(Schema):
    status: str
    operation_id: Optional[int] = None
    completion_details: Optional[Dict[str, Any]] = None

class ReturnedOrderResponse(Schema):
    status: str
    operation_id: Optional[int] = None
    return_details: Optional[Dict[str, Any]] = None

class ProcessedOrderResponse(Schema):
    status: str
    operation_id: Optional[int] = None
    processing_details: Optional[Dict[str, Any]] = None

class CancelledOrderResponse(Schema):
    status: str
    operation_id: Optional[int] = None
    cancellation_details: Optional[Dict[str, Any]] = None

def get_schema_for_endpoint(endpoint: str) -> Optional[type[Schema]]:
    """
    Get the django-ninja Schema class for validating response from a specific endpoint.
    Maps each delivery status endpoint to its corresponding response schema.
    """
    schemas = {
        # Verification group
        '/api/v1/delivery/verified_order': VerifiedOrderResponse,

        # Processing group
        '/api/v1/delivery/select_route_processing': SelectRouteResponse,
        '/api/v1/delivery/select_drone_processing': SelectDroneResponse,
        '/api/v1/delivery/in_transit_processing': InTransitResponse,

        # Completed group
        '/api/v1/delivery/arrived_order': ArrivedOrderResponse,
        '/api/v1/delivery/completed_order': CompletedOrderResponse,

        # Return group
        '/api/v1/delivery/order_due_for_returned': ReturnedOrderResponse,
        '/api/v1/delivery/order_pending_returned': ReturnedOrderResponse,
        '/api/v1/delivery/overdue_order': ReturnedOrderResponse,
        '/api/v1/delivery/returned_order': ReturnedOrderResponse,
        '/api/v1/delivery/processed_order': ProcessedOrderResponse,

        # Cancelled group
        '/api/v1/delivery/cancelled': CancelledOrderResponse,
    }
    return schemas.get(endpoint)

def get_service_for_endpoint(endpoint: str):
    """
    Get the appropriate service class for handling the endpoint response
    """
    if endpoint.startswith('/api/v1/delivery/verified_order'):
        return VerificationService
    elif any(endpoint.startswith(f'/api/v1/delivery/{code}') for code in [
        'select_route_processing', 'select_drone_processing', 'in_transit_processing'
    ]):
        return ProcessingService
    elif any(endpoint.startswith(f'/api/v1/delivery/{code}') for code in [
        'arrived_order', 'completed_order'
    ]):
        return CompletedService
    elif any(endpoint.startswith(f'/api/v1/delivery/{code}') for code in [
        'order_due_for_returned', 'order_pending_returned', 'overdue_order',
        'returned_order', 'processed_order'
    ]):
        return ReturnedService
    elif endpoint.startswith('/api/v1/delivery/cancelled'):
        return CancelledService
    return None

def get_current_status_from_request(request_data):
    """
    Extract current status from request data.
    Handles both single operation_id and multiple operation_ids.
    """
    try:
        # Try to get status directly from request
        if 'status' in request_data:
            return request_data['status']

        # Try to get from single operation_id
        if 'operation_id' in request_data:
            try:
                operation = DeliveryOperation.objects.get(id=request_data['operation_id'])
                return operation.current_status.code
            except DeliveryOperation.DoesNotExist:
                logger.error(f"Operation {request_data['operation_id']} not found")
                return None
            except Exception as e:
                logger.error(f"Error getting operation {request_data['operation_id']}: {str(e)}")
                return None

        # Try to get from multiple operation_ids (use first one as reference)
        if 'operation_ids' in request_data and request_data['operation_ids']:
            try:
                operation = DeliveryOperation.objects.get(id=request_data['operation_ids'][0])
                return operation.current_status.code
            except DeliveryOperation.DoesNotExist:
                logger.error(f"Operation {request_data['operation_ids'][0]} not found")
                return None
            except Exception as e:
                logger.error(f"Error getting operation {request_data['operation_ids'][0]}: {str(e)}")
                return None

        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_current_status_from_request: {str(e)}")
        return None

def get_next_status_info(current_status):
    """
    Get next status information based on current status.
    Returns (next_status_code, is_final_status)
    """
    try:
        current_status_index = next(
            (index for index, status in enumerate(DELIVERY_STATUS_LIST)
             if status['code'] == current_status),
            None
        )

        if current_status_index is None:
            return None, True

        # Check if current status is the last status in the list
        is_final_status = current_status_index == len(DELIVERY_STATUS_LIST) - 1

        if is_final_status:
            return current_status, True

        next_status_index = current_status_index + 1
        next_status = DELIVERY_STATUS_LIST[next_status_index]['code']
        return next_status, False
    except Exception as e:
        logger.error(f"Unexpected error in get_next_status_info for status {current_status}: {str(e)}")
        return None, True

def get_service_for_status(status_code):
    """
    Get the appropriate service class for handling the status
    """
    if status_code in ['unverified_order', 'verified_order']:
        return VerificationService
    elif status_code in ['select_route_processing', 'select_drone_processing', 'in_transit_processing']:
        return ProcessingService
    elif status_code in ['arrived_order', 'completed_order']:
        return CompletedService
    elif status_code in ['order_due_for_returned', 'order_pending_returned', 'overdue_order', 'returned_order', 'processed_order']:
        return ReturnedService
    elif status_code in ['cancelled']:
        return CancelledService
    return None

def get_operation_setting_for_status(status_code):
    """
    Get OperationSettings for the given status code
    Maps status codes to operation setting names
    """
    try:
        from operation_settings.models import OperationSettings

        # Status to operation setting name mapping
        status_to_setting_name = {
            'unverified_order': 'Order Verification',
            'verified_order': 'Order Verification',
            'select_route_processing': 'Order Processing',
            'select_drone_processing': 'Order Processing',
            'in_transit_processing': 'Order Processing',
            'arrived_order': 'Order Completion',
            'completed_order': 'Order Completion',
            'order_due_for_returned': 'Order Return',
            'order_pending_returned': 'Order Return',
            'overdue_order': 'Order Return',
            'returned_order': 'Order Return',
            'processed_order': 'Order Return',
            'cancelled': 'Order Cancellation'
        }

        setting_name = status_to_setting_name.get(status_code)
        if not setting_name:
            logger.warning(f"No operation setting mapping found for status: {status_code}")
            return None

        try:
            # Get delivery operation menu
            from core.menu.models import Menu
            menu = Menu.objects.get(path="/delivery-operation", deleted__isnull=True)

            operation_setting = OperationSettings.objects.filter(
                menu=menu,
                name=setting_name,
                is_active=True
            ).order_by('id').first()

            if not operation_setting:
                logger.warning(f"No active operation setting found for {setting_name}")

            return operation_setting
        except Menu.DoesNotExist:
            logger.error(f"Menu with path '/delivery-operation' not found")
            return None
        except Exception as e:
            logger.error(f"Database error getting operation setting for status {status_code}: {str(e)}")
            return None
    except ImportError as e:
        logger.error(f"Import error in get_operation_setting_for_status: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_operation_setting_for_status for status {status_code}: {str(e)}")
        return None

def delivery_operation_execution(view_func):
    @functools.wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        # Wrap the entire decorator logic in try-catch to prevent any unhandled exceptions
        try:
            if request.method not in ['POST', 'PUT']:
                return view_func(self, request, *args, **kwargs)

            try:
                request_data = json.loads(request.body)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in request body")
                return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
            except Exception as e:
                logger.error(f"Error parsing request body: {str(e)}")
                return view_func(self, request, *args, **kwargs)

            # Get current status from request
            try:
                current_status = get_current_status_from_request(request_data)
                if not current_status:
                    logger.warning("No status found in request, proceeding with normal flow")
                    return view_func(self, request, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error getting current status from request: {str(e)}")
                return view_func(self, request, *args, **kwargs)

            # Get next status information
            try:
                target_status, is_final_status = get_next_status_info(current_status)
                if target_status is None:
                    logger.warning(f"Status {current_status} not found in DELIVERY_STATUS_LIST")
                    return view_func(self, request, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error getting next status info: {str(e)}")
                return view_func(self, request, *args, **kwargs)

            # Check if there's an external API configured for target status
            try:
                operation_setting = get_operation_setting_for_status(target_status)
                if not operation_setting:
                    logger.info(f"No external API configured for status {target_status}, proceeding with normal flow")
                    return view_func(self, request, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error getting operation setting for status {target_status}: {str(e)}")
                return view_func(self, request, *args, **kwargs)

            # Validate operation setting configuration
            try:
                if not operation_setting.api_url:
                    logger.error(f"Operation setting {operation_setting.id} has no API URL")
                    return view_func(self, request, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error validating operation setting: {str(e)}")
                return view_func(self, request, *args, **kwargs)

            # Call external API first
            try:
                logger.info(f"Calling external API: {operation_setting.api_url}")
                logger.info(f"Current status: {current_status} -> Target status: {target_status}")

                # Prepare request parameters based on HTTP method
                request_kwargs = {
                    'method': operation_setting.http_method,
                    'url': operation_setting.api_url,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Authorization': request.headers.get('Authorization', ''),
                        'X-Original-Request-Path': request.path,
                        'X-Original-Request-Method': request.method,
                    },
                    'timeout': operation_setting.timeout_seconds
                }

                # Merge operation settings parameters with request data
                merged_data = request_data.copy() if request_data else {}

                # Add api_params if exists (for GET requests)
                if operation_setting.api_params:
                    try:
                        api_params = operation_setting.api_params
                        if isinstance(api_params, dict):
                            merged_data.update(api_params)
                        else:
                            logger.warning(f"Invalid api_params format in operation setting {operation_setting.id}")
                    except Exception as e:
                        logger.error(f"Error processing api_params: {str(e)}")

                # Add body_params if exists (for non-GET requests)
                if operation_setting.body_params:
                    try:
                        body_params = operation_setting.body_params
                        if isinstance(body_params, dict):
                            merged_data.update(body_params)
                        else:
                            logger.warning(f"Invalid body_params format in operation setting {operation_setting.id}")
                    except Exception as e:
                        logger.error(f"Error processing body_params: {str(e)}")

                # Handle different HTTP methods
                if operation_setting.http_method.upper() == 'GET':
                    # For GET requests, convert merged_data to URL parameters
                    request_kwargs['params'] = merged_data
                else:
                    # For other methods (POST, PUT, etc.), send merged_data as JSON body
                    request_kwargs['json'] = merged_data

                # W0-17 — 외부 API 호출에 타임아웃을 강제한다. 값은 설정 1곳 (D-212).
                request_kwargs.setdefault('timeout', default_timeout())
                response = requests.request(**request_kwargs)

                # Handle different HTTP status codes
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        logger.info(f"External API call successful for {operation_setting.api_url}")

                        # Handle another_info if present in response
                        if 'another_info' in response_data:
                            try:
                                # Get operation_id from request data
                                operation_id = None
                                if 'operation_id' in request_data:
                                    operation_id = request_data['operation_id']
                                elif 'operation_ids' in request_data and request_data['operation_ids']:
                                    operation_id = request_data['operation_ids'][0]

                                if operation_id:
                                    try:
                                        operation = DeliveryOperation.objects.get(id=operation_id)
                                        # Update another_info field
                                        operation.another_info = response_data['another_info']
                                        operation.save(update_fields=['another_info'])
                                        logger.info(f"Updated another_info for operation {operation_id}")
                                    except DeliveryOperation.DoesNotExist:
                                        logger.error(f"Operation {operation_id} not found when updating another_info")
                                    except Exception as e:
                                        logger.error(f"Error updating another_info for operation {operation_id}: {str(e)}")
                                else:
                                    logger.warning("No operation_id found in request data to update another_info")
                            except Exception as e:
                                logger.error(f"Error processing another_info from response: {str(e)}")

                        # Validate response data using expected response structure
                        if operation_setting.expected_response:
                            try:
                                # Basic validation - check if response has expected structure
                                expected_keys = operation_setting.expected_response.keys()
                                for key in expected_keys:
                                    if key not in response_data:
                                        logger.warning(f"Expected key '{key}' not found in response")

                                logger.info(f"Response validation successful for {operation_setting.api_url}")
                            except Exception as e:
                                logger.error(f"Response validation failed for {operation_setting.api_url}: {str(e)}")
                        else:
                            logger.warning(f"No expected response defined for {operation_setting.name}, skipping validation")

                        # Check if external API returned success
                        external_success = False
                        if 'success' in response_data:
                            external_success = response_data.get('success', False)
                        elif 'status' in response_data:
                            # Consider it successful if status matches target status
                            external_success = response_data.get('status') == target_status
                        elif response.status_code == 200:
                            # If no explicit success field, consider 200 as success
                            external_success = True

                        if external_success:
                            logger.info(f"External API approved the operation")
                        else:
                            logger.warning(f"External API returned unsuccessful response: {response_data}")

                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON response from external API: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error processing external API response: {str(e)}")

                elif response.status_code == 404:
                    logger.error(f"External API endpoint not found (404): {operation_setting.api_url}")
                    # Don't log response.text for 404 as it might contain HTML

                elif response.status_code == 401:
                    logger.error(f"External API authentication failed (401): {operation_setting.api_url}")

                elif response.status_code == 403:
                    logger.error(f"External API access forbidden (403): {operation_setting.api_url}")

                elif response.status_code == 500:
                    logger.error(f"External API internal server error (500): {operation_setting.api_url}")

                elif response.status_code == 502:
                    logger.error(f"External API bad gateway (502): {operation_setting.api_url}")

                elif response.status_code == 503:
                    logger.error(f"External API service unavailable (503): {operation_setting.api_url}")

                elif response.status_code == 504:
                    logger.error(f"External API gateway timeout (504): {operation_setting.api_url}")

                else:
                    # For other status codes, log status code but limit response text
                    response_preview = response.text[:200] if response.text else "No response body"
                    # Check if response looks like HTML (starts with < or contains html tags)
                    if response_preview.strip().startswith('<') or '<html' in response_preview.lower():
                        logger.error(f"External API call failed with status {response.status_code}: HTML response received (not logged to avoid clutter)")
                    else:
                        logger.error(f"External API call failed with status {response.status_code}: {response_preview}")

            except requests.exceptions.Timeout as e:
                logger.error(f"External API call timed out after {operation_setting.timeout_seconds}s: {str(e)}")
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Failed to connect to external API: {str(e)}")
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error calling external API: {str(e)}")
            except requests.RequestException as e:
                logger.error(f"Request exception calling external API: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error calling external API: {str(e)}")

        except Exception as e:
            # Catch-all exception handler to prevent any unhandled exceptions
            logger.error(f"Unexpected error in delivery_operation_execution decorator: {str(e)}")
            logger.exception("Full exception traceback:")

        # Always continue with normal system flow regardless of any errors
        return view_func(self, request, *args, **kwargs)

    return wrapper
