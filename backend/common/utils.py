import json
import random
import html
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Type, Union, List
from ninja.parser import Parser
from ninja.schema import Schema
from ninja.errors import ValidationError
from django.http import HttpRequest
from django.apps import apps
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from core.user.models import UserGroup

class MultipartJsonParser(Parser):
    """
    Custom Parser cho Django Ninja để xử lý multipart/form-data với JSON và file uploads.
    
    Parser này sẽ:
    1. Tìm trường 'data' trong form-data và parse nó như một JSON string
    2. Tự động validate JSON với schema tương ứng
    3. Cho phép uploads file cùng lúc với dữ liệu JSON
    
    Cách sử dụng:
    ```python
    @route.post("", parser=MultipartJsonParser())
    def create_something(self, request, data: YourSchema, files: List[UploadedFile] = File(None)):
        # data đã được parse và validate, sẵn sàng sử dụng
    ```
    """
    def parse_body(self, request: HttpRequest) -> Dict[str, Any]:
        """
        Parse dữ liệu từ request body.
        
        Args:
            request: HttpRequest của Django
            
        Returns:
            Dict[str, Any]: Dictionary chứa dữ liệu đã parse
            
        Raises:
            ValidationError: Nếu dữ liệu JSON không hợp lệ
        """
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Lấy dữ liệu từ trường 'data' trong form
            data_json = request.POST.get('data')
            
            if data_json:
                try:
                    # Parse JSON string thành dict
                    parsed_data = json.loads(data_json)
                    # Các trường khác trong request.POST sẽ được giữ nguyên
                    result = dict(request.POST)
                    # Loại bỏ trường 'data' gốc vì sẽ được thay thế bằng parsed_data
                    if 'data' in result:
                        del result['data']
                    # Thêm dữ liệu đã parse vào kết quả
                    result.update(parsed_data)
                    return result
                except json.JSONDecodeError as e:
                    # Log lỗi và raise validation error
                    print(f"JSON decode error: {str(e)}")
                    raise ValidationError(f"Invalid JSON in 'data' field: {str(e)}")
        
        # Nếu không phải multipart/form-data hoặc không có trường 'data',
        # sử dụng parser mặc định (thường là cho application/json)
        return super().parse_body(request)


class FormDataWithJsonParser(Parser):
    """
    Parser nâng cao hơn cho Django Ninja, hỗ trợ:
    
    1. Tự động parse trường 'data' là JSON string
    2. Tự động chuyển đổi các trường dạng "key.subkey" thành nested dict
    3. Hỗ trợ cả multipart/form-data và application/json
    4. Xử lý các trường array với format "key[]"
    
    Cách sử dụng:
    ```python
    @route.post("", parser=FormDataWithJsonParser())
    def create_something(self, request, data: YourSchema, files: List[UploadedFile] = File(None)):
        # data đã được parse và validate
    ```
    """
    
    def parse_form_data(self, request: HttpRequest) -> Dict[str, Any]:
        """
        Parse form-data bao gồm cả nested fields.
        
        Hỗ trợ:
        - Trường 'data' chứa JSON
        - Trường 'user.name' chuyển thành {'user': {'name': value}}
        - Trường 'items[]' chuyển thành {'items': [value1, value2, ...]}
        """
        result = {}
        
        # Xử lý trường 'data' đặc biệt
        if 'data' in request.POST:
            try:
                data = json.loads(request.POST['data'])
                result.update(data)
            except json.JSONDecodeError:
                # Nếu không phải JSON hợp lệ, giữ nguyên giá trị
                result['data'] = request.POST['data']
        
        # Xử lý các trường khác trong POST data
        for key, value in request.POST.items():
            if key == 'data':
                continue  # Đã xử lý ở trên
            
            # Xử lý nested fields (dạng user.name)
            if '.' in key:
                parts = key.split('.')
                current = result
                for i, part in enumerate(parts[:-1]):
                    # Tạo dict lồng nhau nếu chưa tồn tại
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                # Gán giá trị cho key cuối cùng
                current[parts[-1]] = value
            # Xử lý array fields (dạng items[])
            elif key.endswith('[]'):
                array_key = key[:-2]
                if array_key not in result:
                    result[array_key] = []
                result[array_key].append(value)
            else:
                # Trường bình thường
                result[key] = value
        
        return result
    
    def parse_body(self, request: HttpRequest) -> Dict[str, Any]:
        """
        Parse body của request, hỗ trợ cả multipart/form-data và application/json
        """
        content_type = request.content_type or ""
        
        if 'multipart/form-data' in content_type or 'application/x-www-form-urlencoded' in content_type:
            # Parse form data với xử lý nâng cao
            return self.parse_form_data(request)
        
        # Sử dụng parser mặc định cho các content-type khác
        return super().parse_body(request)


# Lớp tiện ích để tạo schema hiển thị trong OpenAPI/Swagger
class SchemaUtils:
    """
    Lớp tiện ích để tạo OpenAPI schema cho các endpoint có upload file
    """
    
    @staticmethod
    def create_multipart_schema(schema_class: Type[Schema], allow_avatar: bool = True, allow_files: bool = True) -> Dict:
        """
        Tạo OpenAPI schema cho endpoint với multipart/form-data
        
        Args:
            schema_class: Class schema của Django Ninja (ví dụ: DeviceCreateSchema)
            allow_avatar: Có cho phép upload avatar hay không
            allow_files: Có cho phép upload nhiều file hay không
            
        Returns:
            Dict: Cấu trúc openapi_extra có thể sử dụng trong route decorator
        """
        schema_ref = f"#/components/schemas/{schema_class.__name__}"
        
        properties = {
            "data": {
                "type": "string",
                "format": "json",
                "description": f"JSON string theo định dạng {schema_class.__name__}"
            }
        }
        
        if allow_avatar:
            properties["avatar"] = {
                "type": "string",
                "format": "binary",
                "description": "File hình ảnh đại diện"
            }
            
        if allow_files:
            properties["files"] = {
                "type": "array",
                "items": {
                    "type": "string",
                    "format": "binary"
                },
                "description": "Các file đính kèm"
            }
            
        return {
            "requestBody": {
                "content": {
                    "multipart/form-data": {
                        "schema": {
                            "type": "object",
                            "properties": properties,
                            "required": ["data"]
                        }
                    }
                }
            }
        }

def add_records_to_groups(model_name: str, record_ids: str, group_ids: str) -> Tuple[bool, int, int]:
    try:
        # Parse IDs
        record_id_list = [int(id.strip()) for id in record_ids.split(',') if id.strip()]
        group_id_list = [int(id.strip()) for id in group_ids.split(',') if id.strip()]
        
        if not record_id_list or not group_id_list:
            return False, 0, 0
            
        model = None
        app_name = None
        for app_config in apps.get_app_configs():
            for app_model in app_config.get_models():
                if app_model.__name__.lower() == model_name.lower():
                    model = app_model
                    app_name = app_config.name
                    break
            if model:
                break

        # Lấy model class
        try:
            model_class = apps.get_model(app_name, model_name)
        except LookupError:
            return False, 0, 0
            
        # Kiểm tra xem model có kế thừa BaseModelWithGroup không
        if not hasattr(model_class, 'groups'):
            return False, 0, 0
            
        # Lấy tất cả records và groups
        records = model_class.objects.filter(id__in=record_id_list)

        groups = UserGroup.objects.filter(id__in=group_id_list)
        
        if not records.exists() or not groups.exists():
            return False, 0, 0
            
        # Thêm records vào groups
        added_records = []
        added_groups = []
        
        for record in records:
            try:
                # Thêm tất cả groups vào record
                record.groups.add(*groups)
                added_records.append(record.id)
                added_groups.extend([g.id for g in groups])
            except Exception as e:
                print(f"Error adding groups to record {record.id}: {str(e)}")
                continue
                
        return True, len(added_records), len(set(added_groups))
        
    except Exception as e:
        print(f"Error in add_records_to_groups: {str(e)}")
        return False, 0, 0


def generate_order_code() -> str:
    """
    Tạo mã đơn hàng duy nhất với format: ORD + YYMMDDHHMMSS + 3 chữ số ngẫu nhiên
    
    Ví dụ: ORD240918143052123
    
    Returns:
        str: Mã đơn hàng duy nhất với 18 ký tự
        
    Features:
        - Prefix ORD để dễ nhận biết đây là mã đơn hàng
        - YYMMDDHHMMSS để biết chính xác thời gian tạo đơn hàng (đến giây)
        - 3 chữ số ngẫu nhiên để đảm bảo tính duy nhất trong cùng 1 giây (1000 combination)
        - Có thể sort chính xác theo thứ tự thời gian tạo
        - Dễ đọc và dễ nhận biết
        - Không dựa vào database count nên tránh được race condition
    """
    now = datetime.now()
    timestamp_part = now.strftime("%y%m%d%H%M%S")  # YYMMDDHHMMSS format
    random_part = f"{random.randint(100, 999)}"  # 3 random digits
    
    return f"ORD{timestamp_part}{random_part}"


def generate_item_code() -> str:
    """
    Tạo mã sản phẩm duy nhất với format: ITM + YYMMDDHHMMSS + 3 chữ số ngẫu nhiên
    
    Ví dụ: ITM240918143052456
    
    Returns:
        str: Mã sản phẩm duy nhất với 18 ký tự
        
    Features:
        - Prefix ITM để dễ nhận biết đây là mã sản phẩm
        - YYMMDDHHMMSS để biết chính xác thời gian tạo sản phẩm (đến giây)
        - 3 chữ số ngẫu nhiên để đảm bảo tính duy nhất trong cùng 1 giây (1000 combination)
        - Có thể sort chính xác theo thứ tự thời gian tạo
        - Dễ đọc và dễ nhận biết  
        - Không dựa vào database count nên tránh được race condition
    """
    now = datetime.now()
    timestamp_part = now.strftime("%y%m%d%H%M%S")  # YYMMDDHHMMSS format
    random_part = f"{random.randint(100, 999)}"  # 3 random digits
    
    return f"ITM{timestamp_part}{random_part}"


def generate_unique_code(prefix: str, length: int = 3) -> str:
    """
    Tạo mã duy nhất với prefix tùy chọn
    
    Args:
        prefix (str): Tiền tố cho mã (ví dụ: ORD, ITM, PKG)
        length (int): Độ dài phần số ngẫu nhiên (mặc định 3)
        
    Returns:
        str: Mã duy nhất với format PREFIX + YYMMDDHHMMSS + RANDOM_DIGITS
        
    Example:
        generate_unique_code("PKG", 3) -> PKG240918143052123
        generate_unique_code("TXN", 4) -> TXN2409181430521234
        
    Features:
        - Sử dụng timestamp đầy đủ để có thể sort chính xác theo thời gian
        - Phần random ngắn hơn (3 digits) vì đã có timestamp chi tiết
    """
    now = datetime.now()
    timestamp_part = now.strftime("%y%m%d%H%M%S")  # YYMMDDHHMMSS format
    
    # Tạo số ngẫu nhiên với độ dài được chỉ định
    min_val = 10 ** (length - 1)
    max_val = (10 ** length) - 1
    random_part = f"{random.randint(min_val, max_val)}"
    
    return f"{prefix}{timestamp_part}{random_part}"


def decode_template_html_entities(template_content):
    """
    Decode HTML entities in template content.
    Converts &gt; to >, &lt; to <, &amp; to &, etc.
    
    Args:
        template_content (str): Template content with HTML entities
        
    Returns:
        str: Decoded template content
    """
    if not template_content or not isinstance(template_content, str):
        return template_content
    
    # Decode HTML entities like &gt; &lt; &amp; &quot; &#39; etc.
    decoded_content = html.unescape(template_content)
    
    return decoded_content


def get_waypoint_speed(default: float = 10.0, cache_timeout: int = 300, force_refresh: bool = False) -> float:
    """Retrieve waypoint (cruise) speed from AdminConfig with caching."""
    cache_key = "config:waypoint_speed"
    try:
        from django.core.cache import cache
    except Exception:
        cache = None  # Cache may not be available during early imports or tests

    if cache and not force_refresh:
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cached_value

    value = default

    try:
        from core.configuration.models import AdminConfig

        config = (
            AdminConfig.objects.filter(name='Waypoint Settings').first()
            or AdminConfig.objects.filter(description='Waypoint speed setting').first()
        )

        if config and isinstance(getattr(config, 'settings', None), dict):
            raw_value = config.settings.get('waypoint_speed')
            if raw_value is not None:
                if isinstance(raw_value, (int, float)):
                    value = float(raw_value)
                else:
                    value = float(str(raw_value).strip())
    except Exception:
        value = default

    if cache:
        try:
            cache.set(cache_key, value, cache_timeout)
        except Exception:
            pass

    return value


def get_last_mission_waypoint(
    default: str = "return_to_launch",
    cache_timeout: int = 300,
    force_refresh: bool = False,
) -> str:
    """
    Retrieve last mission waypoint mode from AdminConfig (Waypoint Settings).

    NOTE: caching is intentionally disabled so config changes take effect immediately.

    Always returns one of:
    - "land"
    - "return_to_launch"
    """
    def _normalize(value: Any, default_value: str) -> str:
        # Current format (stored in DB): string "land" | "return_to_launch"
        if isinstance(value, str):
            v = value.strip().lower().replace("-", "_")
            if v == "land":
                return "land"
            if v in {"return_to_launch", "rtl", "return_to_home", "return_home", "return"}:
                return "return_to_launch"
            return default_value

        # Legacy format: dict {"land": bool, "return_to_launch": bool}
        if isinstance(value, dict):
            try:
                if bool(value.get("land")):
                    return "land"
                if bool(value.get("return_to_launch")) or bool(value.get("return_to_home")) or bool(value.get("returnToLaunch")):
                    return "return_to_launch"
            except Exception:
                return default_value
            return default_value

        # Legacy format: list [{"name": "...", "value": ...}, ...]
        if isinstance(value, list):
            try:
                truthy = {True, 1, "1", "true", "True", "yes", "on"}
                for item in value:
                    if not isinstance(item, dict):
                        continue
                    name = item.get("name") or item.get("key")
                    if not name:
                        continue
                    name_norm = str(name).strip().lower().replace("-", "_")
                    item_value = item.get("value")
                    if item_value is None and "value " in item:
                        item_value = item.get("value ")
                    if item_value in truthy:
                        if name_norm == "land":
                            return "land"
                        if name_norm in {"return_to_launch", "return_to_home", "rtl"}:
                            return "return_to_launch"
            except Exception:
                return default_value
            return default_value

        return default_value

    default_value = _normalize(default, "return_to_launch")

    raw_value: Any = None
    try:
        from core.configuration.models import AdminConfig

        config = (
            AdminConfig.objects.filter(name="Waypoint Settings").first()
            or AdminConfig.objects.filter(description="Waypoint speed setting").first()
        )
        if config and isinstance(getattr(config, "settings", None), dict):
            raw_value = config.settings.get("last_mission_waypoint")
    except Exception:
        raw_value = None

    return _normalize(raw_value if raw_value is not None else default_value, default_value)


def get_return_to_home_default(
    default: bool = True,
    cache_timeout: int = 300,
    force_refresh: bool = False,
) -> bool:
    """
    Return default return_to_home based on AdminConfig (Waypoint Settings).

    Mapping:
    - last_mission_waypoint == "return_to_launch" -> True
    - last_mission_waypoint == "land" -> False
    """
    default_mode = "return_to_launch" if default else "land"
    return (
        get_last_mission_waypoint(
            default=default_mode,
            cache_timeout=cache_timeout,
            force_refresh=force_refresh,
        )
        == "return_to_launch"
    )


def get_gcs_api_headers(additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Create headers for GCS API requests with Authorization Bearer token.
    
    Get GCS_APIKEY from environment variable and create Authorization header.
    If GCS_APIKEY is not found, return headers without Authorization.
    
    Args:
        additional_headers: Dict containing additional headers (optional)
        
    Returns:
        Dict[str, str]: Headers dictionary with Authorization Bearer token if available
        
    Example:
        headers = get_gcs_api_headers()
        response = requests.get(url, headers=headers)
        
        # With additional headers
        headers = get_gcs_api_headers({"Content-Type": "application/json"})
        response = requests.post(url, headers=headers, json=data)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    headers = {}
    
    # Get GCS_APIKEY from Django settings (loaded from .env in settings.py)
    gcs_api_key = None
    
    try:
        from django.conf import settings
        # Get from Django settings (loaded from .env)
        gcs_api_key = getattr(settings, 'GCS_APIKEY', None)
        # Check if empty string, treat as None
        if gcs_api_key == "":
            gcs_api_key = None
        logger.debug(f"[GCS_API] From Django settings: {'Found' if gcs_api_key else 'Not found'}")
        
        # If not found in settings or is empty string, try reading directly from .env
        if not gcs_api_key:
            import environ
            from pathlib import Path
            # Get BASE_DIR from Django settings
            base_dir = getattr(settings, 'BASE_DIR', None)
            if not base_dir:
                # Fallback: calculate from current file location
                # backend/common/utils.py -> backend -> project root
                base_dir = Path(__file__).resolve().parent.parent
            
            # Create env object and read .env file
            env = environ.Env()
            env_file = os.path.join(base_dir, ".env")
            logger.debug(f"[GCS_API] Trying to read from .env file: {env_file}")
            if os.path.exists(env_file):
                env.read_env(env_file)
                gcs_api_key = env('GCS_APIKEY', default=None)
                # Check if empty string, treat as None
                if gcs_api_key == "":
                    gcs_api_key = None
                logger.debug(f"[GCS_API] From .env file: {'Found' if gcs_api_key else 'Not found'}")
            else:
                logger.warning(f"[GCS_API] .env file not found at: {env_file}")
    except Exception as e:
        logger.error(f"[GCS_API] Failed to load from Django settings: {e}", exc_info=True)
        # Fallback: try to get from os.environ
        if not gcs_api_key:
            gcs_api_key = os.environ.get('GCS_APIKEY') or os.getenv('GCS_APIKEY')
            logger.debug(f"[GCS_API] From os.environ: {gcs_api_key[:10] + '...' if gcs_api_key else 'None'}")
    
    # Add Authorization header if API key is available
    if gcs_api_key:
        headers['Authorization'] = f'Bearer {gcs_api_key}'
        logger.debug(f"[GCS_API] API key found, length: {len(gcs_api_key)}")
    else:
        logger.warning("[GCS_API] GCS_APIKEY not found in environment variables. API calls may fail with 401 Unauthorized.")
        # Debug: List env vars containing 'GCS' or 'API'
        gcs_vars = [k for k in os.environ.keys() if 'GCS' in k.upper() or ('API' in k.upper() and 'KEY' in k.upper())]
        if gcs_vars:
            logger.debug(f"[GCS_API] Available related env vars: {gcs_vars[:5]}")
    
    # Add default Content-Type if not present
    if not additional_headers or 'Content-Type' not in additional_headers:
        headers['Content-Type'] = 'application/json'
    
    # Merge with additional headers if provided
    if additional_headers:
        headers.update(additional_headers)
    
    return headers

