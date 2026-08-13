from ninja_extra import api_controller, route
from ninja.errors import ValidationError
from django.http import HttpRequest
from typing import Union, List
import re
import ast

from core.common.base_response import BaseResponse
from core.api.v1.auth import CustomJWTAuth
from common.constant import MESSAGE_ENUM, get_message
from delivery.services.delivery_system import DeliverySystem
from delivery.schemas.schemas_djantic_in import ReceiveFromEtriSchema
from core.role.permission import path_permission
from orders.services.order_service import OrderService
from orders.schemas.schemas_djantic_in import OrderCreateSchema

# Import API Key Management Controller
from third_api.views.api_key_controller import ThirdPartyAPIKeyController

@api_controller("/third-party-integration", tags=["Third Party Integration"])
class ThirdPartyIntegrationController:
    """Controller for APIs that receive data from third-party systems - Swagger Accessible Version"""
    
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
    
    @route.post("/save-shipping-result-data", auth=CustomJWTAuth())
    # @path_permission("update", path_override='/etri-integration')
    def receive_status_from_etri_swagger(self, request, data: ReceiveFromEtriSchema):
        """
        API 8: ETRI 관제 시스템 → GAION 운영 시스템 송신 API (Swagger Access)
        Receive delivery status update from ETRI system - Swagger accessible version
        
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
            
    @route.post("/create-order", auth=CustomJWTAuth())
    @path_permission("create", path_override=['/order', '/etri-order'])
    def create_order(self, request, data: OrderCreateSchema):
        """
        Create a new order via third-party API integration
        
        sample data:
        {
            "sender_name": "Alice",
            "sender_phone": "0987654322",
            "sender_note": "Please handle with care",
            "recipient_name": "John Doe",
            "recipient_phone": "0987654321",
            "recipient_note": "Call before delivery",
            "pickup_location_id": 30,
            "delivery_option_code": "collect_at_location",
            "delivery_terminal_id": 28,
            "payment_method_code": "cash",
            "recipient_address": {
                "city": "Ho Chi Minh City",
                "district": "Tan Binh",
                "ward": "Ward 2",
                "street": "34B Bach Dang",
                "full_address": "34B Bach Dang, Ward 2, Tan Binh, Ho Chi Minh City",
                "lat": 10.773502,
                "lng": 106.704056
            },
            "items": [
                {
                "name": "Electronics Package",
                "weight": {"value": 2.5, "unit": "kg"},
                "dimension_l": {"value": 300, "unit": "mm"},
                "dimension_w": {"value": 200, "unit": "mm"},
                "dimension_h": {"value": 150, "unit": "mm"},
                "is_waterproof": true,
                "is_fragile": true,
                "item_type_id": 1,
                "package_id": 37,
                "note": "Contains a laptop"
                }
            ]
        }
        """
        try:
            # In a real implementation, this would call a service in the order module
            order = OrderService.create(data.dict(), request)
            
            # Calculate order totals after creation
            order.calculate_totals()
            order.save()
            
            # Convert order to schema for JSON serialization - keep original format
            order_data = {}
            order_data['order_code'] = order.order_code
            order_data['order_id'] = order.id
            order_data['status_name'] = order.status.name
            order_data['status_code'] = order.status.code
            
            # Add new financial_summary field only
            order_data['financial_summary'] = {
                'total_amount': {
                    'value': float(order.total_amount.raw_amount) if order.total_amount and not order.total_amount.is_null else 0,
                    'formatted': str(order.total_amount) if order.total_amount and not order.total_amount.is_null else None,
                    'currency_code': order.total_amount.currency_code if order.total_amount else None,
                    'currency_symbol': order.total_amount.currency_symbol if order.total_amount else None
                }
            }
            
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_ORDER_SUCCESS, "Order created successfully"),
                data=order_data
            )
        
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                message="Validation error",
                data={"errors": e.errors()}
            )
        except Exception as e:
            return BaseResponse(
                success=False, 
                status_code=400, 
                message=str(e)
            )

controllers = [
    ThirdPartyIntegrationController,
    ThirdPartyAPIKeyController,
]  