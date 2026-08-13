from datetime import timedelta
import functools
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from typing import Dict, Any
from core.middleware.refresh_token import get_current_request


def anyang_service_key_required(view_func):
    """
    Decorator để kiểm tra serviceKey trong request
    Nếu serviceKey không trùng với anyang_service_key trong env thì return lỗi authentication
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Lấy serviceKey từ request parameters
        service_key = request.GET.get('serviceKey') or request.POST.get('serviceKey')
        
        # Lấy anyang_service_key từ settings
        expected_service_key = getattr(settings, 'ANYANG_SERVICE_KEY', None)
        
        if not service_key:
            return JsonResponse({
                'status': 'error',
                'message': 'serviceKey is required',
                'errorCode': 'AUTH_001'
            }, status=401)
        
        if not expected_service_key:
            return JsonResponse({
                'status': 'error', 
                'message': 'Service configuration error',
                'errorCode': 'AUTH_002'
            }, status=500)
            
        if service_key != expected_service_key:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid serviceKey',
                'errorCode': 'AUTH_003'
            }, status=401)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def get_anyang_target_url() -> str:
    """
    Get Anyang API base URL based on environment configuration
    
    Environments:
    - Production: https://delivery.whee-param.kr/Ext/Delivery/Gaion  
    - Development: https://dev.whee-param.kr/Ext/Delivery/Gaion
    
    Returns:
        str: Base URL for Anyang API endpoints
    """
    # Get environment setting from Django settings
    environment = getattr(settings, 'GUARDIANX_ENVIRONMENT', 'development')
    
    # Anyang API Base URLs according to specification table
    ANYANG_API_ENDPOINTS = {
        'production': 'https://delivery.whee-param.kr/Ext/Delivery/Gaion',
        'development': 'https://dev.whee-param.kr/Ext/Delivery/Gaion'
    }
    
    # Get base URL based on environment
    base_url = ANYANG_API_ENDPOINTS.get(environment)
    
    if not base_url:
        # Fallback to development if invalid environment specified
        base_url = ANYANG_API_ENDPOINTS['development']
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Invalid Anyang environment '{environment}', falling back to development")
    
    return base_url


def format_anyang_response(status: str, message: str, data: Any = None, error_code: str = None, itemOrgId: str = None) -> Dict[str, Any]:
    """
    Format response theo chuẩn của Anyang system
    """
    response = {
        'status': status,
        'message': message,
        'timestamp': timezone.now().isoformat()
    }
    
    if itemOrgId is not None:
        response['itemOrgId'] = itemOrgId
    
    if data is not None:
        response['data'] = data
        
    if error_code:
        response['errorCode'] = error_code
        
    return response

def format_anyang_drone_location_response(itemOrgId: str, latitude: float, longitude: float, deliveryETA: str, resTimestamp: str = None) -> Dict[str, Any]:
    """
    Format response theo chuẩn của Anyang system
    """
    response = {
        'itemOrgId': itemOrgId,
        'location': {
            'latitude': latitude,
            'longitude': longitude
        },
        'deliveryETA': deliveryETA,
        'resTimestamp': resTimestamp
    }
        
    return response


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> tuple:
    """
    Validate required fields trong request data
    Returns: (is_valid, missing_fields)
    """
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] in [None, '', []]:
            missing_fields.append(field)
    
    return len(missing_fields) == 0, missing_fields 

# def generate_unique_code(prefix: str, length: int = 3) -> str:
#     """
#     Tạo mã duy nhất với prefix tùy chọn
    
#     Args:
#         prefix (str): Tiền tố cho mã (ví dụ: ORD, ITM, PKG)
#         length (int): Độ dài phần số ngẫu nhiên (mặc định 3)
        
#     Returns:
#         str: Mã duy nhất với format PREFIX + YYMMDDHHMMSS + RANDOM_DIGITS
        
#     Example:
#         generate_unique_code("PKG", 3) -> PKG240918143052123
#         generate_unique_code("TXN", 4) -> TXN2409181430521234
        
#     Features:
#         - Sử dụng timestamp đầy đủ để có thể sort chính xác theo thời gian
#         - Phần random ngắn hơn (3 digits) vì đã có timestamp chi tiết
#     """
#     now = datetime.now()
#     timestamp_part = now.strftime("%y%m%d%H%M%S")  # YYMMDDHHMMSS format
    
#     # Tạo số ngẫu nhiên với độ dài được chỉ định
#     min_val = 10 ** (length - 1)
#     max_val = (10 ** length) - 1
#     random_part = f"{random.randint(min_val, max_val)}"
    
#     return f"{prefix}{timestamp_part}{random_part}"


