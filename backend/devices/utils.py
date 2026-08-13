from django.db import models
import json
import re
import copy
import logging
import time
from functools import lru_cache
from threading import Lock
from typing import Dict, Any, Optional, Tuple

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.core.cache import cache as django_cache
from pint import UnitRegistry
from django.db.models.functions import Coalesce
from django.db.models import Q, F, Value, FloatField, CharField, Case, When, OuterRef, Subquery, IntegerField
from django.db.models.functions import Cast
from core.common.base_response import BaseResponse

from geopy.geocoders import Nominatim
from geopy.distance import distance as geopy_distance

logger = logging.getLogger(__name__)

# =============================================================================
# 🚀 PERFORMANCE CACHING - Integrated with universal_optimization.py
# =============================================================================

# Pre-compiled regex patterns (avoid re-compilation each call)
_NUMBER_PATTERN = re.compile(r'-?\d+(?:\.\d+)?')
_UNIT_PATTERN = re.compile(r'([°%a-zA-Z/\\][°%a-zA-Z0-9/\\\-\^]*)')

# Cache TTL constants - aligned with UniversalOptimizer.CATEGORY_TTL
MEASUREMENT_CACHE_TTL = 300  # 5 minutes - 'operational' category
ADMIN_CONFIG_CACHE_TTL = 1800  # 30 minutes - 'reference' category
CONTENT_TYPE_CACHE_TTL = 7200  # 2 hours - 'master' category (very stable)

# Cache key prefixes for proper invalidation
CACHE_PREFIX_ADMIN_CONFIG = "measurement:admin_config"
CACHE_PREFIX_CONTENT_TYPE = "measurement:content_type"
CACHE_PREFIX_STANDARDIZE_UNIT = "measurement:standardize_unit"

def get_cached_admin_config(config_name: str = 'Unit Config') -> Dict[str, Any]:
    """
    Get AdminConfig with Django cache - integrated with universal cache system.
    Cache key pattern allows proper invalidation via universal_optimization signals.
    """
    cache_key = f"{CACHE_PREFIX_ADMIN_CONFIG}:{config_name}"
    
    # Try cache first
    cached_value = django_cache.get(cache_key)
    if cached_value is not None:
        return cached_value
    
    # Cache miss - fetch from DB
    try:
        from core.configuration.models import AdminConfig
        config = AdminConfig.objects.get(name=config_name).settings
        result = config.get('unit_preferences', {})
    except Exception:
        result = {}
    
    # Store in cache with TTL
    django_cache.set(cache_key, result, ADMIN_CONFIG_CACHE_TTL)
    return result

# ContentType cache (thread-safe, uses Django cache)
_CONTENT_TYPE_CACHE: Dict[type, 'ContentType'] = {}
_CONTENT_TYPE_CACHE_LOCK = Lock()

def get_cached_content_type(model_class: type) -> 'ContentType':
    """
    Get ContentType with in-memory cache (ContentType rarely changes).
    Django's ContentType already has internal caching, this adds extra layer.
    """
    # In-memory cache first (fastest)
    if model_class in _CONTENT_TYPE_CACHE:
        return _CONTENT_TYPE_CACHE[model_class]
    
    with _CONTENT_TYPE_CACHE_LOCK:
        if model_class not in _CONTENT_TYPE_CACHE:
            # Django's get_for_model already uses caching
            _CONTENT_TYPE_CACHE[model_class] = ContentType.objects.get_for_model(model_class)
        return _CONTENT_TYPE_CACHE[model_class]

def invalidate_measurement_caches():
    """
    🔄 Invalidate all measurement-related caches.
    Call this when AdminConfig 'Unit Config' changes.
    """
    try:
        # Clear Django cache patterns
        django_cache.delete_pattern(f"{CACHE_PREFIX_ADMIN_CONFIG}:*")
        django_cache.delete_pattern(f"{CACHE_PREFIX_STANDARDIZE_UNIT}:*")
        
        # Clear in-memory caches
        global _CONTENT_TYPE_CACHE, _STANDARDIZE_UNIT_CACHE
        _CONTENT_TYPE_CACHE.clear()
        if '_STANDARDIZE_UNIT_CACHE' in globals():
            _STANDARDIZE_UNIT_CACHE.clear()
        
        logger.info("🔄 [MEASUREMENT_CACHE] All measurement caches invalidated")
    except Exception as e:
        logger.warning(f"⚠️ [MEASUREMENT_CACHE] Error invalidating caches: {e}")

ureg = UnitRegistry()
ureg.define('percent = 0.01 = %')
# Định nghĩa đơn vị mA trước
ureg.define('milliampere = 0.001 * ampere = mA')
# Sau đó định nghĩa mAh
ureg.define('milliampere_hour = milliampere * hour = mAh')
STANDARD_INTERNATIONAL_UNITS = {
    # Dimensions & Weight
    'frame_size': 'mm',              # Millimeter - SI derived
    'maximum_takeoff_weight': 'kg',  # Kilogram - SI base
    'payload_capacity': 'kg',        # Kilogram - SI base
    'empty_weight': 'kg',            # Kilogram - SI base
    'weight': 'g',                  # Kilogram - SI base
    'weight_capacity': 'kg',         # Kilogram - SI base
    'dimensions': 'mm',              # Millimeter - SI derived
    'dimensions_weight': 'mm x kg',  # Millimeter x Kilogram - SI derived
    # Performance & Speed
    'maximum_speed': 'km/h',          # Meters per second - SI
    'cruise_speed': 'm/s',           # Meters per second - SI
    'maximum_altitude': 'm',         # Meter - SI base
    'operating_altitude': 'm',       # Meter - SI base
    'maximum_range': 'km',           # Kilometer - SI derived
    'wind_resistance': 'm/s',        # Meters per second - SI
    'wind_speed': 'm/s',            # Meters per second - SI

    # Power & Energy
    'motor_power': 'kW',            # Kilowatt - SI derived
    'battery_capacity': 'mAh',       # Industry standard for batteries
    'propeller_size': 'inch',         # Millimeter - SI derived

    # Time
    'flight_time': 'min',           # Minutes - SI accepted
    'charging_time': 'min',         # Minutes - SI accepted

    # Navigation & Communication
    'gps_accuracy': 'm',            # Meter - SI base
    'frequency': 'GHz',             # Gigahertz - SI derived
    'range': 'km',                  # Kilometer - SI derived

    # Camera & Optics
    'resolution': 'px',             # Industry standard
    'field_of_view': '°',           # Degrees - SI accepted
    'frame_rate': 'fps',            # Industry standard
    'zoom_capability': 'x',         # Industry standard

    # Environmental
    'temperature_range': '°C',      # Celsius - SI derived
    'humidity': '%',                # Percentage - SI accepted
    'precipitation': 'mm/h',        # SI derived
    
    # Sound
    'noise_takeoff': 'dB',         # Decibel - SI accepted
    'noise_cruise': 'dB',          # Decibel - SI accepted
    'noise_landing': 'dB',         # Decibel - SI accepted
}
# Định nghĩa biến toàn cục cho các đơn vị đặc biệt
SPECIAL_UNITS = {
    # Speed units
    'km/h': 'km/h',
    'km / h': 'km/h',
    'kmh': 'km/h',
    'km h-1': 'km/h',
    'kph': 'km/h',
    'm/s': 'm/s', 
    'm / s': 'm/s',
    'mps': 'm/s',
    'm s-1': 'm/s',
    'mph': 'mph',
    'knot': 'kn',
    'knots': 'kn',
    'kn': 'kn',
    
    # Time units - với các viết tắt phổ biến
    'seconds': 's',
    'second': 's',
    'sec': 's',
    'secs': 's',
    'minutes': 'min',
    'minute': 'min',
    'mins': 'min',
    # Note: 'm' excluded here to avoid conflict with meter - use context-specific handling
    'hours': 'h',
    'hour': 'h',
    'hrs': 'h',
    'hr': 'h',
    'days': 'd',
    'day': 'd',
    'weeks': 'w',
    'week': 'w',
    'months': 'month',
    'years': 'year',
    'yr': 'year',
    'yrs': 'year',
    
    # Power & Energy units
    'kw/h': 'kWh',
    'kw h': 'kWh',
    'kwh': 'kWh',
    'kilowatt hour': 'kWh',
    'kilowatt-hour': 'kWh',
    'kilowatthour': 'kWh',
    'w/h': 'Wh',
    'wh': 'Wh',
    'watt hour': 'Wh',
    'watt-hour': 'Wh',
    'watthour': 'Wh',
    'kw': 'kW',
    'kilowatt': 'kW',
    'kilowatts': 'kW',
    'w': 'W',
    'watt': 'W',
    'watts': 'W',
    
    # Current & Voltage units
    'mah': 'mAh',
    'ma.h': 'mAh',
    'ma h': 'mAh',
    'milliampere hour': 'mAh',
    'milliampere-hour': 'mAh',
    'milliamperehour': 'mAh',
    'ah': 'Ah',
    'ampere hour': 'Ah',
    'ampere-hour': 'Ah',
    'amperehour': 'Ah',
    'ma': 'mA',
    'milliampere': 'mA',
    'milliamperes': 'mA',
    'a': 'A',
    'amp': 'A',
    'amps': 'A',
    'ampere': 'A',
    'amperes': 'A',
    'v': 'V',
    'volt': 'V',
    'volts': 'V',
    'mv': 'mV',
    'millivolt': 'mV',
    'millivolts': 'mV',
    'kv': 'kV',
    'kilovolt': 'kV',
    'kilovolts': 'kV',
    
    # Frequency units
    'ghz': 'GHz',
    'gigahertz': 'GHz',
    'mhz': 'MHz',
    'megahertz': 'MHz',
    'khz': 'kHz',
    'kilohertz': 'kHz',
    'hz': 'Hz',
    'hertz': 'Hz',
    
    # Length units
    'millimeter': 'mm',
    'millimeters': 'mm',
    'centimeter': 'cm',
    'centimeters': 'cm',
    'meter': 'm',
    'meters': 'm',
    'kilometer': 'km',
    'kilometers': 'km',
    'inch': 'in',
    'inches': 'in',
    'foot': 'ft',
    'feet': 'ft',
    'yard': 'yd',
    'yards': 'yd',
    'mile': 'mi',
    'miles': 'mi',
    
    # Weight units
    'gram': 'g',
    'grams': 'g',
    'kilogram': 'kg',
    'kilograms': 'kg',
    'pound': 'lb',
    'pounds': 'lb',
    'lbs': 'lb',
    'ounce': 'oz',
    'ounces': 'oz',
    'ton': 't',
    'tons': 't',
    'tonne': 't',
    'tonnes': 't',
    
    # Temperature units
    'celsius': '°C',
    'centigrade': '°C',
    'fahrenheit': '°F',
    'kelvin': 'K',
    
    # Precipitation & Rate units
    'mm/h': 'mm/h',
    'mm / h': 'mm/h',
    'mm per hour': 'mm/h',
    'mm h-1': 'mm/h',
    'millimeter per hour': 'mm/h',
    'millimeters per hour': 'mm/h',
    'cm/h': 'cm/h',
    'cm / h': 'cm/h',
    'cm per hour': 'cm/h',
    'in/h': 'in/h',
    'in / h': 'in/h',
    'inch per hour': 'in/h',
    'inches per hour': 'in/h',
    
    # Sound units
    'db': 'dB',
    'decibel': 'dB',
    'decibels': 'dB',
    'dba': 'dBA',
    
    # Angle units
    'degree': '°',
    'degrees': '°',
    'deg': '°',
    'radian': 'rad',
    'radians': 'rad',
    
    # Resolution units
    'pixel': 'px',
    'pixels': 'px',
    'megapixel': 'MP',
    'megapixels': 'MP',
    'mp': 'MP',
    
    # Frame rate
    'fps': 'fps',
    'frame per second': 'fps',
    'frames per second': 'fps',
    'frame/s': 'fps',
    'frame / s': 'fps',
    
    # Volume units
    'liter': 'L',
    'liters': 'L',
    'litre': 'L',
    'litres': 'L',
    'l': 'L',
    'ml': 'mL',
    'milliliter': 'mL',
    'milliliters': 'mL',
    'millilitre': 'mL',
    'millilitres': 'mL',
    'gallon': 'gal',
    'gallons': 'gal',
    'gal': 'gal',
    
    # Percentage
    'percent': '%',
    'percentage': '%',
    'pct': '%',
}

# UTILITY FUNCTIONS

def create_simple_measurement(entity, name, value, unit, qualifier=None):
    from devices.models import Measurement
    """
    Tạo phép đo đơn giản (giá trị + đơn vị)
    Ví dụ: 65 dB, 25 kg, 20,000mAh
    """
    data = {
        'type': 'simple',
        'value': value,
        'unit': unit
    }
    if qualifier:
        data['qualifier'] = qualifier
        
    return Measurement.objects.create(
        content_type=ContentType.objects.get_for_model(entity),
        object_id=entity.id,
        measurement_type=name,
        data=data
    )

def create_range_measurement(entity, name, min_val, max_val, unit, qualifier=None):
    from devices.models import Measurement
    """
    Tạo phép đo kiểu dải giá trị (min-max)
    Ví dụ: -10°C to 50°C, 0-95%, 80-120°
    """
    data = {
        'type': 'range',
        'min': min_val,
        'max': max_val,
        'unit': unit
    }
    if qualifier:
        data['qualifier'] = qualifier
        
    return Measurement.objects.create(
        content_type=ContentType.objects.get_for_model(entity),
        object_id=entity.id,
        measurement_type=name,
        data=data
    )

def create_up_to_measurement(entity, name, max_val, unit, qualifier=None):
    from devices.models import Measurement
    """
    Tạo phép đo kiểu "up to" hoặc "maximum"
    Ví dụ: Up to 40 km/h
    """
    data = {
        'type': 'up_to',
        'max': max_val,
        'unit': unit
    }
    if qualifier:
        data['qualifier'] = qualifier
        
    return Measurement.objects.create(
        content_type=ContentType.objects.get_for_model(entity),
        object_id=entity.id,
        measurement_type=name,
        data=data
    )

def create_dimensions_measurement(entity, name, length, width, height=None, unit='mm'):
    from devices.models import Measurement
    """
    Tạo phép đo kích thước
    Ví dụ: 150mm x 100mm x 50mm
    """
    data = {
        'type': 'dimensions',
        'length': length,
        'width': width,
        'unit': unit
    }
    if height is not None:
        data['height'] = height
        
    return Measurement.objects.create(
        content_type=ContentType.objects.get_for_model(entity),
        object_id=entity.id,
        measurement_type=name,
        data=data
    )

def create_dimensions_weight_measurement(entity, name, length, width, height, weight, dim_unit='mm', weight_unit='kg'):
    from devices.models import Measurement
    """
    Tạo phép đo kích thước + trọng lượng
    Ví dụ: 150mm x 100mm x 50mm 0.5kg
    """
    data = {
        'type': 'dimensions_weight',
        'length': length,
        'width': width,
        'height': height,
        'weight': weight,
        'dimension_unit': dim_unit,
        'weight_unit': weight_unit
    }
        
    return Measurement.objects.create(
        content_type=ContentType.objects.get_for_model(entity),
        object_id=entity.id,
        measurement_type=name,
        data=data
    )

def create_error_margin_measurement(entity, name, value, margin, unit):
    from devices.models import Measurement
    """
    Tạo phép đo có sai số (±)
    Ví dụ: ±1.5m
    """
    return Measurement.objects.create(
        content_type=ContentType.objects.get_for_model(entity),
        object_id=entity.id,
        measurement_type=name,
        data={
            'type': 'error_margin',
            'value': value,
            'margin': margin,
            'unit': unit
        }
    )

def create_resolution_measurement(entity, name, resolution_name, width, height):
    from devices.models import Measurement
    """
    Tạo phép đo độ phân giải
    Ví dụ: 4K (3840×2160)
    """
    return Measurement.objects.create(
        content_type=ContentType.objects.get_for_model(entity),
        object_id=entity.id,
        measurement_type=name,
        data={
            'type': 'resolution',
            'name': resolution_name,
            'width': width,
            'height': height,
            'unit': 'px'
        }
    )

def create_multi_value_measurement(entity, name, values, unit, qualifier=None):
    from devices.models import Measurement
    """
    Tạo phép đo nhiều giá trị cùng đơn vị
    Ví dụ: 2.4GHz and 5.8GHz
    """
    if not isinstance(values, list):
        values = [values]
    data = {
        'type': 'multi_value',
        'values': values,
        'unit': standardize_unit(unit)
    }
    
    # Thêm qualifier nếu có
    if qualifier:
        data['qualifier'] = qualifier
    return Measurement.objects.create(
        content_type=ContentType.objects.get_for_model(entity),
        object_id=entity.id,
        measurement_type=name,
        data=data
    )

def create_string_measurement(entity, name, value_string):
    from devices.models import Measurement
    """
    Tạo phép đo kiểu chuỗi
    Ví dụ: "150mm x 100mm x 50mm"
    """
    return Measurement.objects.create(
        content_type=ContentType.objects.get_for_model(entity),
        object_id=entity.id,
        measurement_type=name,
        data={'type': 'string', 'value': value_string}
    )

# PARSER FUNCTIONS

def parse_dimension_string(dimension_str):
    """Phân tích chuỗi kích thước như '150mm x 100mm x 50mm', '150x100x50mm', '150 x 100 x 50 mm'"""
    # Xử lý các ký tự đặc biệt
    dimension_str = dimension_str.replace('×', 'x').replace('*', 'x')
    
    # Pattern cho trường hợp không có đơn vị - kiểm tra đầu tiên
    no_unit_pattern = r'^(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*(?:x\s*(\d+(?:\.\d+)?))?$'
    no_unit_match = re.search(no_unit_pattern, dimension_str)
    
    if no_unit_match:
        length = float(no_unit_match.group(1))
        width = float(no_unit_match.group(2))
        
        if no_unit_match.group(3):
            height = float(no_unit_match.group(3))
            return {'length': length, 'width': width, 'height': height, 'unit': None}  # Mặc định là mm
        else:
            return {'length': length, 'width': width, 'unit': None}  # Mặc định là mm
    
    # Pattern cho dạng '150mm x 100mm x 50mm' hoặc '150mm x 100mm'
    pattern1 = r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+(?!\s*x))\s*x\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]*(?!\s*x))\s*(?:x\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]*(?!\s*x)))?'
    match1 = re.search(pattern1, dimension_str, re.IGNORECASE)
    if match1:
        values = []
        units = []
        
        # Lấy chiều dài và đơn vị
        values.append(float(match1.group(1)))
        unit = match1.group(2)
        if unit.lower() != 'x':  # Kiểm tra nếu unit không phải là 'x'
            units.append(unit)
        
        # Lấy chiều rộng và đơn vị (nếu có)
        values.append(float(match1.group(3)))
        unit2 = match1.group(4).strip() if match1.group(4) else ''
        if unit2 and unit2.lower() != 'x':  # Kiểm tra nếu unit không phải là 'x'
            units.append(unit2)
        
        # Lấy chiều cao và đơn vị nếu có
        if match1.group(5):
            values.append(float(match1.group(5)))
            unit3 = match1.group(6).strip() if match1.group(6) else ''
            if unit3 and unit3.lower() != 'x':  # Kiểm tra nếu unit không phải là 'x'
                units.append(unit3)
        
        # Nếu không có unit hợp lệ nào, sử dụng mm làm đơn vị mặc định
        if not units:
            unit = None
        else:
            unit = units[0]
        
        if len(values) == 3:
            return {'length': values[0], 'width': values[1], 'height': values[2], 'unit': unit}
        elif len(values) == 2:
            return {'length': values[0], 'width': values[1], 'unit': unit}
    
    # Pattern cho dạng '150 x 100 x 50 mm' hoặc '150x100x50 mm'
    pattern2 = r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*(?:x\s*(\d+(?:\.\d+)?)\s*)?\s+([a-zA-Z]+)'
    match2 = re.search(pattern2, dimension_str, re.IGNORECASE)
    if match2:
        length = float(match2.group(1))
        width = float(match2.group(2))
        unit = match2.group(4).strip()
        
        # Kiểm tra nếu unit là 'x'
        if unit.lower() == 'x':
            # Nếu unit là 'x', coi như không có unit và dùng mm
            if match2.group(3):
                height = float(match2.group(3))
                return {'length': length, 'width': width, 'height': height, 'unit': None}
            else:
                return {'length': length, 'width': width, 'unit': None}
        
        if match2.group(3):
            height = float(match2.group(3))
            return {'length': length, 'width': width, 'height': height, 'unit': unit}
        else:
            return {'length': length, 'width': width, 'unit': unit}
    
    # Pattern cho dạng LxWxH hoặc LxW với kích thước
    pattern3 = r'L\s*(\d+(?:\.\d+)?)\s*x\s*W\s*(\d+(?:\.\d+)?)\s*(?:x\s*H\s*(\d+(?:\.\d+)?)\s*)?([a-zA-Z]+(?!\s*x))?'
    match3 = re.search(pattern3, dimension_str, re.IGNORECASE)
    if match3:
        length = float(match3.group(1))
        width = float(match3.group(2))
        unit = match3.group(4).strip() if match3.group(4) else None  # Mặc định là mm
        
        if match3.group(3):
            height = float(match3.group(3))
            return {'length': length, 'width': width, 'height': height, 'unit': unit}
        else:
            return {'length': length, 'width': width, 'unit': unit}
    
    # Pattern đơn giản cho 3 số và đơn vị cuối
    simple_pattern = r'(\d+(?:\.\d+)?)\D+(\d+(?:\.\d+)?)\D+(\d+(?:\.\d+)?)\D*([a-zA-Z]+(?!\s*x))'
    simple_match = re.search(simple_pattern, dimension_str)
    if simple_match:
        length = float(simple_match.group(1))
        width = float(simple_match.group(2))
        height = float(simple_match.group(3))
        unit = simple_match.group(4).strip()
        
        return {'length': length, 'width': width, 'height': height, 'unit': unit}
    
    # Pattern cho kích thước 2D
    simple_2d_pattern = r'(\d+(?:\.\d+)?)\D+(\d+(?:\.\d+)?)\D*([a-zA-Z]+(?!\s*x))'
    simple_2d_match = re.search(simple_2d_pattern, dimension_str)
    
    if simple_2d_match:
        length = float(simple_2d_match.group(1))
        width = float(simple_2d_match.group(2))
        unit = simple_2d_match.group(3).strip()
        
        return {'length': length, 'width': width, 'unit': unit}
    
    return None

def parse_dimensions_weight(text):
    """Phân tích chuỗi chứa kích thước và trọng lượng"""
    # Các đơn vị khối lượng phổ biến (viết thường)
    weight_units = ['kg', 'g', 'lb', 'oz', 'gram', 'kilogram']
    
    # Pattern tìm khối lượng: số + đơn vị khối lượng, không phân biệt chữ hoa/thường
    # và có thể có hoặc không có khoảng cách giữa số và đơn vị
    weight_pattern = r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)'
    
    # Tìm tất cả các cặp số + đơn vị trong chuỗi
    matches = re.finditer(weight_pattern, text, re.IGNORECASE)
    
    weight_data = None
    weight_span = None  # lưu vị trí của phần khối lượng trong chuỗi
    
    for match in matches:
        value = float(match.group(1))
        unit = match.group(2).lower()  # chuyển về chữ thường để so sánh
        
        # Kiểm tra xem đơn vị có phải là đơn vị khối lượng không
        for weight_unit in weight_units:
            if unit == weight_unit or unit.startswith(weight_unit):
                # Kiểm tra xem phần này có phải là phần của kích thước không
                # (thường là phần kích thước sẽ có ký tự 'x' gần đó)
                context_start = max(0, match.start() - 5)
                context_end = min(len(text), match.end() + 5)
                context = text[context_start:context_end]
                
                # Nếu 'x' nằm gần với match và không phải là phần của khối lượng
                if 'x' in context and (match.start() - context.find('x') < 5 or context.rfind('x') - match.end() < 5):
                    continue
                
                # Nếu tìm thấy khối lượng
                weight_data = {
                    'weight': value,
                    'weight_unit': standardize_unit(unit)  # chuẩn hóa đơn vị
                }
                weight_span = (match.start(), match.end())
                break
        
        if weight_data:
            break
    
    if weight_data:
        # Tạo chuỗi mới không chứa phần khối lượng
        dimensions_str = text[:weight_span[0]] + ' ' + text[weight_span[1]:]
        dimensions_str = dimensions_str.strip()
        
        # Phân tích phần kích thước
        dimensions = parse_dimension_string(dimensions_str)
        
        if dimensions:
            return {
                'dimensions': dimensions,
                'weight': weight_data['weight'],
                'weight_unit': weight_data['weight_unit']
            }
    
    # Nếu các phương pháp trên không hoạt động, thử phương pháp hiện tại
    parts = text.split()
    for i, part in enumerate(parts):
        if 'x' not in part.lower():  # không chứa 'x' (để tránh nhầm với kích thước)
            # Kiểm tra xem phần này có phải là khối lượng không
            match = re.match(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)', part, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2).lower()
                
                # Kiểm tra đơn vị
                if any(unit == weight_unit or unit.startswith(weight_unit) for weight_unit in weight_units):
                    # Phần còn lại là kích thước
                    dimensions_str = ' '.join(parts[:i] + parts[i+1:])
                    dimensions = parse_dimension_string(dimensions_str)
                    
                    if dimensions:
                        return {
                            'dimensions': dimensions,
                            'weight': value,
                            'weight_unit': standardize_unit(unit)
                        }
    
    return None

def parse_range(text):
    """Phân tích chuỗi dải giá trị như '-10°C to 50°C' hoặc '0-95%' hoặc 'from X to Y'"""
    # Tiền xử lý: loại bỏ dấu phẩy trong số
    text_for_parse = re.sub(r'(\d),(\d)', r'\1\2', text)
    
    # Kiểm tra dạng "min to max" - cho phép đơn vị ở cả min và max là tùy chọn
    to_pattern = r'(-?\d+(?:\.\d+)?)\s*([a-zA-Z°%/µ·]*)\s+(?:to|through|thru)\s+(-?\d+(?:\.\d+)?)\s*([a-zA-Z°%/µ·]*)'
    to_match = re.search(to_pattern, text_for_parse, re.IGNORECASE)
    
    if to_match:
        min_val = float(to_match.group(1))
        min_unit = to_match.group(2).strip()
        max_val = float(to_match.group(3))
        max_unit = to_match.group(4).strip()
        
        # Nếu chỉ có một đơn vị được cung cấp (cuối cùng), áp dụng cho cả min và max
        if not min_unit and max_unit:
            min_unit = max_unit
        elif not max_unit and min_unit:
            max_unit = min_unit
            
        # Nếu không có đơn vị nào được cung cấp, sử dụng đơn vị mặc định là rỗng
        unit = min_unit or max_unit or ""
        
        # Kiểm tra qualifier
        result = {
            'min': min_val,
            'max': max_val,
            'unit': unit,
            'is_mixed_units': min_unit != "" and max_unit != "" and min_unit.lower() != max_unit.lower()
        }
        
        # Kiểm tra qualifier trong chuỗi
        rest_of_text = text_for_parse[to_match.end():].strip()
        if rest_of_text:
            result['qualifier'] = rest_of_text
            
        return result
    
    # Kiểm tra dạng "from min to max"
    from_to_pattern = r'from\s+(-?\d+(?:\.\d+)?)\s*([a-zA-Z°%/µ·]*)\s+(?:to|through|thru)\s+(-?\d+(?:\.\d+)?)\s*([a-zA-Z°%/µ·]*)'
    from_to_match = re.search(from_to_pattern, text_for_parse, re.IGNORECASE)
    
    if from_to_match:
        min_val = float(from_to_match.group(1))
        min_unit = from_to_match.group(2).strip()
        max_val = float(from_to_match.group(3))
        max_unit = from_to_match.group(4).strip()
        
        # Nếu chỉ có một đơn vị được cung cấp (cuối cùng), áp dụng cho cả min và max
        if not min_unit and max_unit:
            min_unit = max_unit
        elif not max_unit and min_unit:
            max_unit = min_unit
            
        # Nếu không có đơn vị nào được cung cấp, sử dụng đơn vị mặc định là rỗng
        unit = min_unit or max_unit or ""
        
        # Kiểm tra qualifier
        result = {
            'min': min_val,
            'max': max_val,
            'unit': unit,
            'is_mixed_units': min_unit != "" and max_unit != "" and min_unit.lower() != max_unit.lower()
        }
        
        # Kiểm tra qualifier trong chuỗi
        rest_of_text = text_for_parse[from_to_match.end():].strip()
        if rest_of_text:
            result['qualifier'] = rest_of_text
            
        return result
    
    # Kiểm tra dạng "min-max unit"
    dash_pattern = r'(-?\d+(?:\.\d+)?)\s*[-–—]\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z°%/µ·]*)'
    dash_match = re.search(dash_pattern, text_for_parse)
    
    if dash_match:
        min_val = float(dash_match.group(1))
        max_val = float(dash_match.group(2))
        unit = dash_match.group(3).strip()
        
        result = {
            'min': min_val,
            'max': max_val,
            'unit': unit
        }
        
        # Kiểm tra qualifier trong chuỗi
        rest_of_text = text_for_parse[dash_match.end():].strip()
        if rest_of_text:
            result['qualifier'] = rest_of_text
            
        return result
    
    # Kiểu phạm vi số % (không có đơn vị % sau mỗi số)
    percent_range_pattern = r'(-?\d+(?:\.\d+)?)\s*[-–—]\s*(-?\d+(?:\.\d+)?)\s*%'
    percent_range_match = re.search(percent_range_pattern, text_for_parse)
    
    if percent_range_match:
        result = {
            'min': float(percent_range_match.group(1)),
            'max': float(percent_range_match.group(2)),
            'unit': '%'
        }
        
        # Kiểm tra qualifier trong chuỗi
        rest_of_text = text_for_parse[percent_range_match.end():].strip()
        if rest_of_text:
            result['qualifier'] = rest_of_text
            
        return result
    
    # Kiểu phạm vi nhiệt độ (không lặp lại °C hoặc °F)
    temp_range_pattern = r'(-?\d+(?:\.\d+)?)\s*[-–—]\s*(-?\d+(?:\.\d+)?)\s*(°[CF])'
    temp_range_match = re.search(temp_range_pattern, text_for_parse)
    
    if temp_range_match:
        result = {
            'min': float(temp_range_match.group(1)),
            'max': float(temp_range_match.group(2)),
            'unit': temp_range_match.group(3)
        }
        
        # Kiểm tra qualifier trong chuỗi
        rest_of_text = text_for_parse[temp_range_match.end():].strip()
        if rest_of_text:
            result['qualifier'] = rest_of_text
            
        return result
    
    # Kiểm tra dạng "range từ min đến max"
    range_pattern = r'range\s+(?:of\s+|from\s+)?(-?\d+(?:\.\d+)?)\s*([a-zA-Z°%/µ·]*)\s+(?:to|through|thru)\s+(-?\d+(?:\.\d+)?)\s*([a-zA-Z°%/µ·]*)'
    range_match = re.search(range_pattern, text_for_parse, re.IGNORECASE)
    
    if range_match:
        min_val = float(range_match.group(1))
        min_unit = range_match.group(2).strip()
        max_val = float(range_match.group(3))
        max_unit = range_match.group(4).strip() if len(range_match.groups()) >= 4 else ""
        
        # Nếu chỉ có một đơn vị được cung cấp, áp dụng cho cả min và max
        if not min_unit and max_unit:
            min_unit = max_unit
        elif not max_unit and min_unit:
            max_unit = min_unit
            
        unit = min_unit or max_unit or ""
        
        result = {
            'min': min_val,
            'max': max_val,
            'unit': unit,
            'is_mixed_units': min_unit != "" and max_unit != "" and min_unit.lower() != max_unit.lower()
        }
        
        # Kiểm tra qualifier trong chuỗi
        rest_of_text = text_for_parse[range_match.end():].strip()
        if rest_of_text:
            result['qualifier'] = rest_of_text
            
        return result
    
    # Thêm pattern cho chuỗi "between min and max" 
    between_pattern = r'between\s+(-?\d+(?:\.\d+)?)\s*([a-zA-Z°%/µ·]*)\s+and\s+(-?\d+(?:\.\d+)?)\s*([a-zA-Z°%/µ·]*)'
    between_match = re.search(between_pattern, text_for_parse, re.IGNORECASE)
    
    if between_match:
        min_val = float(between_match.group(1))
        min_unit = between_match.group(2).strip()
        max_val = float(between_match.group(3))
        max_unit = between_match.group(4).strip()
        
        # Xử lý trường hợp chỉ có một đơn vị
        if not min_unit and max_unit:
            min_unit = max_unit
        elif not max_unit and min_unit:
            max_unit = min_unit
            
        unit = min_unit or max_unit or ""
        
        result = {
            'min': min_val,
            'max': max_val,
            'unit': unit,
            'is_mixed_units': min_unit != "" and max_unit != "" and min_unit.lower() != max_unit.lower()
        }
        
        # Kiểm tra qualifier trong chuỗi
        rest_of_text = text_for_parse[between_match.end():].strip()
        if rest_of_text:
            result['qualifier'] = rest_of_text
            
        return result
    
    # Thử phân tích dạng "min unit - max unit" hoặc "min - max unit"
    complex_dash_pattern = r'(-?\d+(?:\.\d+)?)\s*([a-zA-Z°%/µ·]*)\s*[-–—]\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z°%/µ·]*)'
    complex_dash_match = re.search(complex_dash_pattern, text_for_parse)
    
    if complex_dash_match:
        min_val = float(complex_dash_match.group(1))
        min_unit = complex_dash_match.group(2).strip()
        max_val = float(complex_dash_match.group(3))
        max_unit = complex_dash_match.group(4).strip()
        
        # Trường hợp đặc biệt: xử lý khi có hai đơn vị khác nhau như "10µA-100mA"
        if min_unit and max_unit and min_unit.lower() != max_unit.lower():
            result = {
                'min': min_val,
                'max': max_val,
                'unit': f"{min_unit}-{max_unit}",
                'is_mixed_units': True
            }
        else:
            # Xử lý trường hợp chỉ có một đơn vị
            if not min_unit and max_unit:
                min_unit = max_unit
            elif not max_unit and min_unit:
                max_unit = min_unit
                
            unit = min_unit or max_unit or ""
            
            result = {
                'min': min_val,
                'max': max_val,
                'unit': unit,
                'is_mixed_units': False
            }
        
        # Kiểm tra qualifier trong chuỗi
        rest_of_text = text_for_parse[complex_dash_match.end():].strip()
        if rest_of_text:
            result['qualifier'] = rest_of_text
            
        return result
    
    return None

def parse_up_to(text):
    """Phân tích chuỗi 'Up to X' hoặc 'Maximum X'"""
    # Pattern chính cho 'up to X unit' hoặc 'maximum X unit'
    pattern = r'(?:up\s+to|maximum|max\.?|up\s+to\s+a\s+maximum\s+of|up\s+to\s+max\.?)\s+(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        value = float(match.group(1).replace(',', ''))
        unit = match.group(2).strip()
        
        # Xử lý các đơn vị đặc biệt để đảm bảo định dạng nhất quán
        if unit.lower() in SPECIAL_UNITS:
            unit = SPECIAL_UNITS[unit.lower()]
            
        return {
            'max': value,
            'unit': unit
        }
    
    # Pattern cho dạng số sau đó đến max
    pattern_to_max = r'(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]+)\s+max(?:imum)?'
    match_to_max = re.search(pattern_to_max, text, re.IGNORECASE)
    
    if match_to_max:
        value = float(match_to_max.group(1).replace(',', ''))
        unit = match_to_max.group(2).strip()
        
        if unit.lower() in SPECIAL_UNITS:
            unit = SPECIAL_UNITS[unit.lower()]
            
        return {
            'max': value,
            'unit': unit
        }
    
    # Pattern cho dạng "Not exceeding X unit"
    pattern_not_exceeding = r'(?:not\s+exceeding|less\s+than|below)\s+(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]+)'
    match_not_exceeding = re.search(pattern_not_exceeding, text, re.IGNORECASE)
    
    if match_not_exceeding:
        value = float(match_not_exceeding.group(1).replace(',', ''))
        unit = match_not_exceeding.group(2).strip()
        
        if unit.lower() in SPECIAL_UNITS:
            unit = SPECIAL_UNITS[unit.lower()]
            
        return {
            'max': value,
            'unit': unit
        }
    
    return None

def parse_error_margin(text):
    """Phân tích chuỗi có sai số như '±1.5m'"""
    pattern = r'[±](\d+(?:\.\d+)?)\s*([a-zA-Z]+)'
    match = re.search(pattern, text)
    
    if match:
        return {
            'value': 0,  # Giá trị tâm mặc định là 0
            'margin': float(match.group(1)),
            'unit': match.group(2)
        }
    
    return None

def parse_resolution(text):
    """Phân tích chuỗi độ phân giải như '4K (3840 × 2160px)' hoặc đơn giản như '22 x 333px'"""
    
    # Pattern 1: Tìm kiếm dạng có tên và kích thước trong ngoặc "4K (3840 × 2160px)"
    pattern1 = r'(\w+)\s*\((\d+)(?:[×x])(\d+)(?:px)\)'
    match1 = re.search(pattern1, text)
    
    if match1:
        return {
            'name': match1.group(1),
            'width': int(match1.group(2)),
            'height': int(match1.group(3)),
            'unit': 'px'
        }
    
    # Pattern 2: Tìm kiếm dạng đơn giản "22 x 333px"
    pattern2 = r'(\d+)\s*(?:[×x])\s*(\d+)(?:px)'
    match2 = re.search(pattern2, text)
    
    if match2:
        return {
            'name': '',  # Gán tên mặc định
            'width': int(match2.group(1)),
            'height': int(match2.group(2)),
            'unit': 'px'
        }
    
    return None

def parse_multi_value(text):
    """
    Parse chuỗi có nhiều giá trị (hoặc một giá trị) với các dấu phân cách khác nhau.
    Hỗ trợ nhiều format và nhận diện qualifier.
    Tối ưu performance với cách tiếp cận từng bước.
    """
    original_text = text.strip()
    if not original_text:
        return None
    
    # Bước 1: Chuẩn hóa và tách các phần
    # Thay thế tất cả dấu phân cách thành dấu phẩy chuẩn
    normalized = original_text
    separators = [
        (r'\s+and\s+', ', '),     # "and" -> ","
        (r'\s+or\s+', ', '),      # "or" -> ","
        (r'\s*\|\s*', ', '),      # "|" -> ","
        (r'\s*;\s*', ', '),       # ";" -> ","
        (r'\s*\+\s*', ', '),      # "+" -> ","
        (r'\s*&\s*', ', '),       # "&" -> ","
        (r'\s*/\s*', ', '),       # "/" -> ","
        (r'\s+as\s+well\s+as\s+', ', '),  # "as well as" -> ","
        (r'\s+along\s+with\s+', ', '),    # "along with" -> ","
        (r'\s+plus\s+', ', '),            # "plus" -> ","
        (r'\s+together\s+with\s+', ', '), # "together with" -> ","
        (r'\s+with\s+', ', '),            # "with" -> ","
        (r'both\s+', '')                  # remove "both"
    ]
    
    for pattern, replacement in separators:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    
    # Bước 2: Trích xuất qualifier
    # Các từ khóa qualifier phổ biến
    qualifier_keywords = [
        'approximately', 'approx', 'average', 'avg', 'typical', 'typ',
        'nominal', 'nom', 'maximum', 'max', 'minimum', 'min', 'up to'
    ]
    
    # Tìm qualifier ở đầu và cuối chuỗi
    qualifier = None
    
    # Trước tiên tìm qualifier chuẩn ở đầu chuỗi
    for kw in qualifier_keywords:
        if normalized.lower().startswith(kw):
            qualifier = kw
            normalized = normalized[len(kw):].strip()
            break
            
    # Sau đó tìm qualifier ở cuối chuỗi
    for kw in qualifier_keywords:
        if normalized.lower().endswith(kw):
            qualifier = kw if not qualifier else f"{qualifier} {kw}"
            normalized = normalized[:-len(kw)].strip()
            break
    
    # Bước 3: Xử lý dạng ngoặc đặc biệt
    bracket_pattern = r'([-+]?\d+(?:\.\d+)?)\s*([a-zA-Z°%/]+)?\s*(?:\(|\[)\s*([-+]?\d+(?:\.\d+)?)\s*([a-zA-Z°%/]+)?\s*(?:\)|\])'
    bracket_match = re.search(bracket_pattern, normalized)
    if bracket_match:
        groups = bracket_match.groups()
        val1 = float(groups[0])
        unit1 = groups[1] if groups[1] else ''
        val2 = float(groups[2])
        unit2 = groups[3] if groups[3] else ''
        
        # Kết hợp đơn vị, ưu tiên đơn vị đầu tiên
        unit = unit1 if unit1 else unit2
        
        # Loại bỏ phần đã xử lý để tìm qualifier bổ sung
        matched_text = normalized[bracket_match.start():bracket_match.end()]
        remaining = normalized.replace(matched_text, '').strip()
        
        # Nếu còn phần dư, coi như qualifier bổ sung
        if remaining and not qualifier:
            qualifier = remaining
        elif remaining and qualifier:
            qualifier = f"{qualifier} {remaining}"
        
        result = {
            'type': 'multi_value',
            'values': [val1, val2],
            'unit': unit.lower() if unit else None
        }
        
        if qualifier:
            result['qualifier'] = qualifier
            
        return result
    
    # Bước 4: Xử lý các phần được phân tách bằng dấu phẩy
    parts = [p.strip() for p in normalized.split(',') if p.strip()]
    if not parts:
        return None
        
    # Pattern đơn giản để bắt số và đơn vị
    value_pattern = r'([-+]?\d+(?:\.\d+)?)\s*([a-zA-Z°%/]*)'
    
    values = []
    units = []
    remaining_parts = []
    
    for part in parts:
        match = re.match(value_pattern, part.strip())
        if match:
            val, unit = match.groups()
            values.append(float(val))
            
            # Lưu đơn vị nếu có
            if unit:
                units.append(unit.lower())
                
            # Kiểm tra có phần còn lại không
            matched_text = part[match.start():match.end()]
            remaining = part.replace(matched_text, '').strip()
            if remaining:
                remaining_parts.append(remaining)
        else:
            # Phần này không chứa số, có thể là phần của qualifier
            remaining_parts.append(part)
    
    # Nếu không tìm thấy giá trị nào, trả về None
    if not values:
        return None
        
    # Lấy đơn vị phổ biến nhất
    unit = None
    if units:
        # Sử dụng Counter để tìm đơn vị phổ biến nhất hiệu quả
        from collections import Counter
        unit_counts = Counter(units)
        unit = unit_counts.most_common(1)[0][0]
    
    # Kết hợp các phần còn lại làm qualifier bổ sung
    if remaining_parts and not qualifier:
        qualifier = ' '.join(remaining_parts)
    elif remaining_parts and qualifier:
        qualifier = f"{qualifier} {' '.join(remaining_parts)}"
    
    result = {
        'type': 'multi_value',
        'values': values,
        'unit': unit
    }
    
    if qualifier:
        result['qualifier'] = qualifier.strip()
        
    return result

def parse_measurement_string(text):
    """Parse các định dạng đo lường phổ biến"""
    patterns = [
        # Range patterns
        # 1. Basic range with unit
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*-\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]+)',
        # 2. Range with units on both sides
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]+)\s*-\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]+)',
        # 3. Range with "to" keyword
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]*)\s+(?:to|through|thru)\s+(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]*)',
        # 4. Range with "from...to" format
        r'from\s+(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]*)\s+(?:to|through|thru)\s+(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]*)',
        # 5. Range with "between...and" format
        r'between\s+(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]*)\s+and\s+(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]*)',
        # 6. Range with different dash types
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*[-–—]\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]*)',
        # 7. Range with parentheses
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*\(([a-zA-Z°%/]*)\)\s*[-–—]\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*\(([a-zA-Z°%/]*)\)',
        
        # Simple value patterns
        # 1. Basic value with unit
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]+)',
        # 2. Value with unit in parentheses
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*\(([a-zA-Z°%/]+)\)',
        # 3. Value with unit after space
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s+([a-zA-Z°%/]+)',
        
        # Percentage patterns
        # 1. Basic percentage
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*%',
        # 2. Percentage with parentheses
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*\(%\)',
        # 3. Percentage with "percent" word
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s+percent',
        
        # Dimension patterns
        # 1. Basic LxWxH
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*x\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*x\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z]+)',
        # 2. LxW with unit
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*x\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z]+)',
        # 3. LxWxH with units on each dimension
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z]+)\s*x\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z]+)\s*x\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z]+)',
        # 4. LxWxH with parentheses
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*x\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*x\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*\(([a-zA-Z]+)\)',
        
        # Time patterns
        # 1. HH:MM:SS
        r'(\d{2}):(\d{2}):(\d{2})',
        # 2. HH:MM
        r'(\d{2}):(\d{2})',
        # 3. Time with AM/PM
        r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)',
        
        # Frequency patterns
        # 1. Basic frequency
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(Hz|kHz|MHz|GHz)',
        # 2. Frequency with parentheses
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*\(([a-zA-Z]+)\)',
        
        # Storage patterns
        # 1. Basic storage
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(KB|MB|GB|TB)',
        # 2. Storage with i prefix
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(KiB|MiB|GiB|TiB)',
        
        # Angle patterns
        # 1. Basic angle
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*°',
        # 2. Angle with direction
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*°\s*(N|S|E|W|NE|NW|SE|SW)',
        
        # Speed patterns
        # 1. Basic speed
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(m/s|km/h|mph)',
        # 2. Speed with parentheses
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*\(([a-zA-Z/]+)\)',
        
        # Resolution patterns
        # 1. Basic resolution
        r'(\d+)\s*[x×]\s*(\d+)\s*(?:px)?',
        # 2. Resolution with unit
        r'(\d+)\s*[x×]\s*(\d+)\s*px',
        # 3. Resolution with name
        r'(\w+)\s*\((\d+)\s*[x×]\s*(\d+)\s*(?:px)?\)',
        
        # Temperature patterns
        # 1. Basic temperature
        r'(-?\d+(?:,\d+)*(?:\.\d+)?)\s*°[CF]',
        # 2. Temperature range
        r'(-?\d+(?:,\d+)*(?:\.\d+)?)\s*°[CF]\s*[-–—]\s*(-?\d+(?:,\d+)*(?:\.\d+)?)\s*°[CF]',
        
        # Error margin patterns
        # 1. Basic error margin
        r'[±]\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]+)',
        # 2. Error margin with plus/minus
        r'[+]\s*/\s*-\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]+)',
        
        # Multi-value patterns
        # 1. Basic multi-value
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]+)\s+(?:and|or|,)\s+(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/]*)',
        # 2. Multi-value with parentheses
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*\(([a-zA-Z°%/]+)\)\s+(?:and|or|,)\s+(\d+(?:,\d+)*(?:\.\d+)?)\s*\(([a-zA-Z°%/]+)\)'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            return match.groups()
            
    return None

# 🚀 PERFORMANCE: Cached standardize_unit lookup
_STANDARDIZE_UNIT_CACHE: Dict[Tuple[str, Optional[str]], str] = {}
_CONTEXT_TOKEN_PATTERN = re.compile(r'[^a-z0-9]+')

def standardize_unit(unit, context=None):
    """
    Chuẩn hóa đơn vị về dạng chuẩn với context awareness
    
    Args:
        unit (str): Đơn vị cần chuẩn hóa
        context (str): Loại measurement để xử lý ambiguous units như 'm'
                      Có thể là: 'time', 'length', 'speed', 'weight', etc.
    """
    # 🚀 PERFORMANCE: Check cache first
    cache_key = (unit, context)
    if cache_key in _STANDARDIZE_UNIT_CACHE:
        return _STANDARDIZE_UNIT_CACHE[cache_key]
    
    original_unit = unit
    unit = unit.lower().strip()
    context_lower = context.lower() if isinstance(context, str) else None
    context_tokens = set()
    if context_lower:
        context_tokens = {token for token in _CONTEXT_TOKEN_PATTERN.split(context_lower) if token}
    
    # Helper to cache and return
    def _cache_and_return(val):
        _STANDARDIZE_UNIT_CACHE[cache_key] = val
        return val
    
    # Handle context-specific ambiguous units
    if unit == 'm' and (context_lower or context_tokens):
        is_time_context = any(
            token in {
                'time', 'duration', 'eta', 'interval', 'mission_time',
                'estimated', 'estimated_time', 'mins', 'min', 'minute', 'minutes'
            } or 'time' in token for token in context_tokens
        )
        if is_time_context:
            return _cache_and_return('min')  # minutes
        elif context_lower and (
            context_lower in ['length', 'dimensions', 'height', 'width', 'distance', 'range'] or
            any(keyword in context_lower for keyword in ['length', 'height', 'width', 'distance', 'range', 'altitude', 'radius'])
        ):
            return _cache_and_return('m')    # meters
        # Default to meters if context is unclear
        else:
            return _cache_and_return('m')
    
    # Kiểm tra các đơn vị đặc biệt 
    if unit in SPECIAL_UNITS:
        return _cache_and_return(SPECIAL_UNITS[unit])
    
    # Kiểm tra các trường hợp đặc biệt được hardcode để tránh conflicts
    special_cases = {
        '°c': '°C', 'celsius': '°C',
        '°f': '°F', 'fahrenheit': '°F',
        '°': '°', 'deg': '°', 'degree': '°',
        '%': '%', 'percent': '%',
        'mah': 'mAh',
        'ma.h': 'mAh', 
        'ma·h': 'mAh',
        'ma h': 'mAh',
        'milliampere hour': 'mAh',
        'milliampere-hour': 'mAh',
        'mAh': 'mAh',
        'kmh': 'km/h',
        'km/h': 'km/h',
        'km / h': 'km/h',
        'kwh': 'kWh', 'kilowatt-hour': 'kWh',
        'kw': 'kW', 'kilowatt': 'kW',
        'w': 'W', 'watt': 'W',
        'wh': 'Wh', 'watt-hour': 'Wh',
        'v': 'V', 'volt': 'V',
        'a': 'A', 'ampere': 'A',
        'mm/h': 'mm/h',
        'mm / h': 'mm/h',
    }
    
    result = None  # Will hold the final result
    
    if unit in special_cases:
        result = special_cases[unit]
    else:
        # Thử xác thực đơn vị với Pint
        try:
            # Nếu là đơn vị hợp lệ, lấy ký hiệu chuẩn
            valid_unit = ureg.Unit(unit)
            # Lấy format chuẩn từ Pint
            standard_symbol = f"{valid_unit:~}"
            
            # Kiểm tra và sửa lại một số đơn vị hay gặp vấn đề với khoảng trắng
            if standard_symbol == 'km / h':
                result = 'km/h'
            elif standard_symbol == 'm / s':
                result = 'm/s'
            # Kiểm tra các đơn vị tần số và năng lượng
            elif standard_symbol.lower() in ['ghz', 'mhz', 'khz', 'hz', 'kw', 'kwh', 'mah', 'ma']:
                unit_lower = standard_symbol.lower()
                if unit_lower in SPECIAL_UNITS:
                    result = SPECIAL_UNITS[unit_lower]
                else:
                    result = standard_symbol
            else:
                result = standard_symbol
        except (ValueError, AttributeError, KeyError):
            # Giữ nguyên định dạng viết hoa ban đầu nếu không nhận dạng được
            result = original_unit
    
    # 🚀 PERFORMANCE: Cache the result before returning
    _STANDARDIZE_UNIT_CACHE[cache_key] = result
    return result

def convert_unit(value, from_unit, to_unit, context=None):
    """Chuyển đổi giá trị giữa các đơn vị"""
    # Chuẩn hóa đơn vị với context awareness
    from_unit = standardize_unit(from_unit, context)
    to_unit = standardize_unit(to_unit, context)
    
    if from_unit == to_unit:
        return value
    
    # Thử sử dụng thư viện Pint trước
    try:
        quantity = value * ureg(from_unit)
        converted = quantity.to(to_unit)
        return converted.magnitude
    except Exception as e:
        # Nếu Pint không xử lý được, thử sử dụng các conversion factor đã định nghĩa
        pass
        
    # Định nghĩa các conversion factor
    conversions = {
        # Khối lượng
        'g_to_kg': 0.001,
        'kg_to_g': 1000,
        'kg_to_lb': 2.20462,
        'lb_to_kg': 0.453592,
        'g_to_oz': 0.035274,
        'oz_to_g': 28.3495,
        'lb_to_oz': 16,
        'oz_to_lb': 0.0625,
        
        # Chiều dài
        'm_to_cm': 100,
        'cm_to_m': 0.01,
        'km_to_m': 1000,
        'm_to_km': 0.001,
        'mm_to_m': 0.001,
        'm_to_mm': 1000,
        'cm_to_mm': 10,
        'mm_to_cm': 0.1,
        'in_to_cm': 2.54,
        'cm_to_in': 0.393701,
        'in_to_mm': 25.4,
        'mm_to_in': 0.0393701,
        'ft_to_m': 0.3048,
        'm_to_ft': 3.28084,
        'ft_to_cm': 30.48,
        'cm_to_ft': 0.0328084,
        'ft_to_in': 12,
        'in_to_ft': 0.0833333,
        
        # Tốc độ
        'kmh_to_ms': 0.277778,
        'km/h_to_m/s': 0.277778,
        'kph_to_mps': 0.277778,
        'ms_to_kmh': 3.6,
        'm/s_to_km/h': 3.6,
        'mps_to_kph': 3.6,
        'mph_to_kmh': 1.60934,
        'mph_to_km/h': 1.60934,
        'kmh_to_mph': 0.621371,
        'km/h_to_mph': 0.621371,
        'mph_to_ms': 0.44704,
        'mph_to_m/s': 0.44704,
        'ms_to_mph': 2.23694,
        'm/s_to_mph': 2.23694,
        'kn_to_kmh': 1.852,  # hải lý/giờ (knot) sang km/h
        'kn_to_km/h': 1.852,
        'kmh_to_kn': 0.539957,
        'km/h_to_kn': 0.539957,
        
        # Nhiệt độ
        'C_to_F': lambda c: c * 9/5 + 32,
        'F_to_C': lambda f: (f - 32) * 5/9,
        'C_to_K': lambda c: c + 273.15,
        'K_to_C': lambda k: k - 273.15,
        'F_to_K': lambda f: (f - 32) * 5/9 + 273.15,
        'K_to_F': lambda k: (k - 273.15) * 9/5 + 32,
        
        # Công suất/Năng lượng
        'W_to_kW': 0.001,
        'kW_to_W': 1000,
        'kWh_to_Wh': 1000,
        'Wh_to_kWh': 0.001,
        'mAh_to_Ah': 0.001,
        'Ah_to_mAh': 1000,
        'J_to_kJ': 0.001,
        'kJ_to_J': 1000,
        'Wh_to_J': 3600,
        'J_to_Wh': 0.000277778,
        
        # Thể tích
        'L_to_mL': 1000,
        'mL_to_L': 0.001,
        'L_to_m3': 0.001,
        'm3_to_L': 1000,
        'gal_to_L': 3.78541,  # gallon (US) sang lít
        'L_to_gal': 0.264172,
        'in3_to_mL': 16.3871,  # inch khối sang millilít
        'mL_to_in3': 0.0610237,
        
        # Áp suất
        'Pa_to_kPa': 0.001,
        'kPa_to_Pa': 1000,
        'kPa_to_bar': 0.01,
        'bar_to_kPa': 100,
        'psi_to_kPa': 6.89476,
        'kPa_to_psi': 0.145038,
        
        # Tần số
        'Hz_to_kHz': 0.001,
        'kHz_to_Hz': 1000,
        'kHz_to_MHz': 0.001,
        'MHz_to_kHz': 1000,
        'MHz_to_GHz': 0.001,
        'GHz_to_MHz': 1000,
        
        # Thời gian - với tất cả viết tắt phổ biến
        # Seconds conversions
        'min_to_s': 60,
        'mins_to_s': 60,
        'sec_to_s': 1,
        'secs_to_s': 1,
        's_to_min': 1/60,
        's_to_mins': 1/60,
        's_to_sec': 1,
        's_to_secs': 1,
        
        # Minutes conversions
        'h_to_min': 60,
        'h_to_mins': 60,
        'hr_to_min': 60,
        'hrs_to_min': 60,
        'hour_to_min': 60,
        'hours_to_min': 60,
        'min_to_h': 1/60,
        'mins_to_h': 1/60,
        'min_to_hr': 1/60,
        'mins_to_hr': 1/60,
        'min_to_hour': 1/60,
        'mins_to_hour': 1/60,
        
        # Hours conversions
        'h_to_s': 3600,
        'hr_to_s': 3600,
        'hrs_to_s': 3600,
        'hour_to_s': 3600,
        'hours_to_s': 3600,
        's_to_h': 1/3600,
        's_to_hr': 1/3600,
        's_to_hour': 1/3600,
        
        # Days conversions
        'd_to_h': 24,
        'd_to_hr': 24,
        'd_to_hrs': 24,
        'd_to_hour': 24,
        'd_to_hours': 24,
        'day_to_h': 24,
        'days_to_h': 24,
        'h_to_d': 1/24,
        'hr_to_d': 1/24,
        'hrs_to_d': 1/24,
        'hour_to_d': 1/24,
        'hours_to_d': 1/24,
        'h_to_day': 1/24,
        'h_to_days': 1/24,
        
        'd_to_min': 1440,
        'd_to_mins': 1440,
        'day_to_min': 1440,
        'days_to_min': 1440,
        'min_to_d': 1/1440,
        'mins_to_d': 1/1440,
        'min_to_day': 1/1440,
        'mins_to_day': 1/1440,
        
        'd_to_s': 86400,
        'day_to_s': 86400,
        'days_to_s': 86400,
        's_to_d': 1/86400,
        's_to_day': 1/86400,
        's_to_days': 1/86400,
        
        # Weeks conversions
        'w_to_d': 7,
        'week_to_d': 7,
        'weeks_to_d': 7,
        'w_to_day': 7,
        'w_to_days': 7,
        'week_to_day': 7,
        'week_to_days': 7,
        'weeks_to_day': 7,
        'weeks_to_days': 7,
        'd_to_w': 1/7,
        'day_to_w': 1/7,
        'days_to_w': 1/7,
        'd_to_week': 1/7,
        'd_to_weeks': 1/7,
        'day_to_week': 1/7,
        'day_to_weeks': 1/7,
        'days_to_week': 1/7,
        'days_to_weeks': 1/7,
        
        'w_to_h': 168,
        'week_to_h': 168,
        'weeks_to_h': 168,
        'w_to_hr': 168,
        'w_to_hrs': 168,
        'w_to_hour': 168,
        'w_to_hours': 168,
        'h_to_w': 1/168,
        'hr_to_w': 1/168,
        'hrs_to_w': 1/168,
        'hour_to_w': 1/168,
        'hours_to_w': 1/168,
        'h_to_week': 1/168,
        'h_to_weeks': 1/168,
        
        # Months and Years conversions
        'month_to_d': 30,  # Tháng trung bình 30 ngày
        'months_to_d': 30,
        'month_to_day': 30,
        'month_to_days': 30,
        'months_to_day': 30,
        'months_to_days': 30,
        'd_to_month': 1/30,
        'day_to_month': 1/30,
        'days_to_month': 1/30,
        'd_to_months': 1/30,
        'day_to_months': 1/30,
        'days_to_months': 1/30,
        
        'year_to_d': 365,  # Năm thường 365 ngày
        'years_to_d': 365,
        'yr_to_d': 365,
        'yrs_to_d': 365,
        'year_to_day': 365,
        'year_to_days': 365,
        'years_to_day': 365,
        'years_to_days': 365,
        'd_to_year': 1/365,
        'day_to_year': 1/365,
        'days_to_year': 1/365,
        'd_to_years': 1/365,
        'day_to_years': 1/365,
        'days_to_years': 1/365,
        'd_to_yr': 1/365,
        'd_to_yrs': 1/365,
        
        'year_to_h': 8760,  # 365 * 24
        'years_to_h': 8760,
        'yr_to_h': 8760,
        'yrs_to_h': 8760,
        'year_to_hr': 8760,
        'year_to_hrs': 8760,
        'year_to_hour': 8760,
        'year_to_hours': 8760,
        'h_to_year': 1/8760,
        'hr_to_year': 1/8760,
        'hrs_to_year': 1/8760,
        'hour_to_year': 1/8760,
        'hours_to_year': 1/8760,
        'h_to_years': 1/8760,
        'h_to_yr': 1/8760,
        'h_to_yrs': 1/8760,
        
        # Thời gian với đơn vị đầy đủ
        'second_to_minute': 1/60,
        'minute_to_second': 60,
        'minute_to_hour': 1/60,
        'hour_to_minute': 60,
        'hour_to_second': 3600,
        'second_to_hour': 1/3600,
        'day_to_hour': 24,
        'hour_to_day': 1/24,
        'week_to_day': 7,
        'day_to_week': 1/7,
        
        # Milliseconds
        'ms_to_s': 0.001,
        'millisecond_to_s': 0.001,
        'milliseconds_to_s': 0.001,
        's_to_ms': 1000,
        's_to_millisecond': 1000,
        's_to_milliseconds': 1000,
        'ms_to_min': 1/60000,
        'ms_to_mins': 1/60000,
        'min_to_ms': 60000,
        'mins_to_ms': 60000,
        
        # Extended Length conversions với viết tắt từ SPECIAL_UNITS
        'millimeter_to_mm': 1,
        'millimeters_to_mm': 1,
        'mm_to_millimeter': 1,
        'mm_to_millimeters': 1,
        'centimeter_to_cm': 1,
        'centimeters_to_cm': 1,
        'cm_to_centimeter': 1,
        'cm_to_centimeters': 1,
        'meter_to_m': 1,
        'meters_to_m': 1,
        'm_to_meter': 1,
        'm_to_meters': 1,
        'kilometer_to_km': 1,
        'kilometers_to_km': 1,
        'km_to_kilometer': 1,
        'km_to_kilometers': 1,
        'inch_to_in': 1,
        'inches_to_in': 1,
        'in_to_inch': 1,
        'in_to_inches': 1,
        'foot_to_ft': 1,
        'feet_to_ft': 1,
        'ft_to_foot': 1,
        'ft_to_feet': 1,
        'yard_to_yd': 1,
        'yards_to_yd': 1,
        'yd_to_yard': 1,
        'yd_to_yards': 1,
        'mile_to_mi': 1,
        'miles_to_mi': 1,
        'mi_to_mile': 1,
        'mi_to_miles': 1,
        
        # Extended Weight conversions
        'gram_to_g': 1,
        'grams_to_g': 1,
        'g_to_gram': 1,
        'g_to_grams': 1,
        'kilogram_to_kg': 1,
        'kilograms_to_kg': 1,
        'kg_to_kilogram': 1,
        'kg_to_kilograms': 1,
        'pound_to_lb': 1,
        'pounds_to_lb': 1,
        'lbs_to_lb': 1,
        'lb_to_pound': 1,
        'lb_to_pounds': 1,
        'lb_to_lbs': 1,
        'ounce_to_oz': 1,
        'ounces_to_oz': 1,
        'oz_to_ounce': 1,
        'oz_to_ounces': 1,
        'ton_to_t': 1,
        'tons_to_t': 1,
        'tonne_to_t': 1,
        'tonnes_to_t': 1,
        't_to_ton': 1,
        't_to_tons': 1,
        't_to_tonne': 1,
        't_to_tonnes': 1,
        
        # Extended Temperature conversions  
        'celsius_to_°C': 1,
        'centigrade_to_°C': 1,
        '°C_to_celsius': 1,
        '°C_to_centigrade': 1,
        'fahrenheit_to_°F': 1,
        '°F_to_fahrenheit': 1,
        'kelvin_to_K': 1,
        'K_to_kelvin': 1,
        
        # Extended Power & Energy conversions
        'kilowatt_to_kW': 1,
        'kilowatts_to_kW': 1,
        'kW_to_kilowatt': 1,
        'kW_to_kilowatts': 1,
        'watt_to_W': 1,
        'watts_to_W': 1,
        'W_to_watt': 1,
        'W_to_watts': 1,
        'kilowatthour_to_kWh': 1,
        'kWh_to_kilowatthour': 1,
        'watthour_to_Wh': 1,
        'Wh_to_watthour': 1,
        
        # Extended Current & Voltage conversions
        'milliampere_to_mA': 1,
        'milliamperes_to_mA': 1,
        'mA_to_milliampere': 1,
        'mA_to_milliamperes': 1,
        'amp_to_A': 1,
        'amps_to_A': 1,
        'ampere_to_A': 1,
        'amperes_to_A': 1,
        'A_to_amp': 1,
        'A_to_amps': 1,
        'A_to_ampere': 1,
        'A_to_amperes': 1,
        'volt_to_V': 1,
        'volts_to_V': 1,
        'V_to_volt': 1,
        'V_to_volts': 1,
        'millivolt_to_mV': 1,
        'millivolts_to_mV': 1,
        'mV_to_millivolt': 1,
        'mV_to_millivolts': 1,
        'kilovolt_to_kV': 1,
        'kilovolts_to_kV': 1,
        'kV_to_kilovolt': 1,
        'kV_to_kilovolts': 1,
        
        # Extended Frequency conversions
        'gigahertz_to_GHz': 1,
        'GHz_to_gigahertz': 1,
        'megahertz_to_MHz': 1,
        'MHz_to_megahertz': 1,
        'kilohertz_to_kHz': 1,
        'kHz_to_kilohertz': 1,
        'hertz_to_Hz': 1,
        'Hz_to_hertz': 1,
        
        # Extended Sound conversions
        'decibel_to_dB': 1,
        'decibels_to_dB': 1,
        'dB_to_decibel': 1,
        'dB_to_decibels': 1,
        
        # Extended Angle conversions
        'degree_to_°': 1,
        'degrees_to_°': 1,
        'deg_to_°': 1,
        '°_to_degree': 1,
        '°_to_degrees': 1,
        '°_to_deg': 1,
        'radian_to_rad': 1,
        'radians_to_rad': 1,
        'rad_to_radian': 1,
        'rad_to_radians': 1,
        '°_to_rad': 0.0174533,  # degrees to radians
        'rad_to_°': 57.2958,    # radians to degrees
        'degree_to_rad': 0.0174533,
        'rad_to_degree': 57.2958,
        
        # Extended Resolution conversions
        'pixel_to_px': 1,
        'pixels_to_px': 1,
        'px_to_pixel': 1,
        'px_to_pixels': 1,
        'megapixel_to_MP': 1,
        'megapixels_to_MP': 1,
        'mp_to_MP': 1,
        'MP_to_megapixel': 1,
        'MP_to_megapixels': 1,
        'MP_to_mp': 1,
        
        # Extended Volume conversions
        'liter_to_L': 1,
        'liters_to_L': 1,
        'litre_to_L': 1,
        'litres_to_L': 1,
        'l_to_L': 1,
        'L_to_liter': 1,
        'L_to_liters': 1,
        'L_to_litre': 1,
        'L_to_litres': 1,
        'L_to_l': 1,
        'milliliter_to_mL': 1,
        'milliliters_to_mL': 1,
        'millilitre_to_mL': 1,
        'millilitres_to_mL': 1,
        'ml_to_mL': 1,
        'mL_to_milliliter': 1,
        'mL_to_milliliters': 1,
        'mL_to_millilitre': 1,
        'mL_to_millilitres': 1,
        'mL_to_ml': 1,
        'gallon_to_gal': 1,
        'gallons_to_gal': 1,
        'gal_to_gallon': 1,
        'gal_to_gallons': 1,
        
        # Extended Percentage conversions
        'percent_to_%': 1,
        'percentage_to_%': 1,
        'pct_to_%': 1,
        '%_to_percent': 1,
        '%_to_percentage': 1,
        '%_to_pct': 1,
        
        # Extended Frame rate conversions
        'frame per second_to_fps': 1,
        'frames per second_to_fps': 1,
        'frame/s_to_fps': 1,
        'frame / s_to_fps': 1,
        'fps_to_frame per second': 1,
        'fps_to_frames per second': 1,
        'fps_to_frame/s': 1,
        'fps_to_frame / s': 1,
        
        # Extended Speed unit conversions
        'kph_to_km/h': 1,
        'km/h_to_kph': 1,
        'knot_to_kn': 1,
        'knots_to_kn': 1,
        'kn_to_knot': 1,
        'kn_to_knots': 1,
        
        # Additional commonly used conversions
        'yd_to_m': 0.9144,
        'm_to_yd': 1.09361,
        'yd_to_ft': 3,
        'ft_to_yd': 0.333333,
        'yd_to_in': 36,
        'in_to_yd': 0.0277778,
        'mi_to_km': 1.60934,
        'km_to_mi': 0.621371,
        'mi_to_m': 1609.34,
        'm_to_mi': 0.000621371,
        'mi_to_ft': 5280,
        'ft_to_mi': 0.000189394,
        
        # Ton conversions
        't_to_kg': 1000,
        'kg_to_t': 0.001,
        't_to_lb': 2204.62,
        'lb_to_t': 0.000453592,
        
        # Additional volume conversions
        'gal_to_mL': 3785.41,  # US gallon to milliliters
        'mL_to_gal': 0.000264172,
        'gal_to_m3': 0.00378541,
        'm3_to_gal': 264.172,
        
        # Additional energy conversions
        'mAh_to_mWh': lambda mah, voltage=3.7: mah * voltage,  # requires voltage
        'Wh_to_mAh': lambda wh, voltage=3.7: (wh / voltage) * 1000 if voltage != 0 else 0,
        
        # Additional pressure conversions
        'atm_to_Pa': 101325,
        'Pa_to_atm': 9.86923e-6,
        'atm_to_psi': 14.6959,
        'psi_to_atm': 0.068046,
        'mmHg_to_Pa': 133.322,
        'Pa_to_mmHg': 0.00750062,
        
        # Velocity squared (for kinetic energy calculations)
        'm/s_to_m2/s2': lambda v: v * v,
        'km/h_to_m2/s2': lambda v: (v * 0.277778) ** 2,
        
        # Additional temperature difference conversions (for ΔT)
        '°C_diff_to_°F_diff': 1.8,
        '°F_diff_to_°C_diff': 0.555556,
        'K_diff_to_°C_diff': 1,
        '°C_diff_to_K_diff': 1,
    }
    
    # Chuẩn hóa key để tìm kiếm
    def normalize_unit(unit):
        return unit.lower().replace('/', '').replace(' ', '').replace('-', '')
    
    # Tạo các key khác nhau có thể có
    possible_keys = [
        f"{from_unit}_to_{to_unit}".lower(),
        f"{normalize_unit(from_unit)}_to_{normalize_unit(to_unit)}",
        f"{from_unit.replace('/', '')}_to_{to_unit.replace('/', '')}".lower()
    ]
    
    # Tìm kiếm qua các key có thể
    for key in possible_keys:
        if key in conversions:
            if callable(conversions[key]):
                return conversions[key](value)
            return value * conversions[key]
    
    # Thử một lần nữa với pint nếu không tìm thấy trong conversions
    try:
        quantity = value * ureg(from_unit)
        converted = quantity.to(to_unit)
        return converted.magnitude
    except Exception:
        # Nếu tất cả phương pháp đều thất bại, raise exception để caller handle
        raise ValueError(f"Unsupported unit conversion: {from_unit} to {to_unit}")

# COMMON PROCESSING FUNCTIONS

def process_measurement_string(entity, name, value_string):
    from devices.models import Measurement
    """
    Tự động xác định loại dữ liệu và tạo phép đo phù hợp dựa trên type khai báo trong model
    """
    measurement_type = None
    expected_format = None
    
    # Kiểm tra xem entity có khai báo MEASUREMENT_TYPES không
    if hasattr(entity, 'MEASUREMENT_TYPES') and name in entity.MEASUREMENT_TYPES:
        # Lấy kiểu được khai báo trong model
        measurement_info = entity.MEASUREMENT_TYPES[name]
        declared_type = measurement_info['type']
        default_unit = measurement_info.get('default_unit', '')
        measurement_type = declared_type
        
        # Định nghĩa expected_format để hiển thị gợi ý nếu parse thất bại
        formats = {
            'simple': f"10 {default_unit}",
            'range': f"10 {default_unit} to 20 {default_unit} or 10-20 {default_unit}",
            'up_to': f"Up to 10 {default_unit}",
            'multi_value': f"10 {default_unit} and 20 {default_unit}",
            'error_margin': f"±1.5 {default_unit}",
            'dimensions': f"100mm x 200mm x 300mm or 100mm x 200mm",
            'resolution': "4K (3840×2160)",
            'dimensions_weight': "100mm x 200mm x 300mm 500g or 100mm x 200mm 300g",
        }
        expected_format = formats.get(declared_type, "")
        
        # Ưu tiên parse theo kiểu khai báo trước
        result = None
        if declared_type == 'string':
            result = create_string_measurement(
                entity, name, value_string
            )
        elif declared_type == 'simple':
            simple_pattern = r'(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/\.]+)'
            simple_match = re.search(simple_pattern, value_string)
            
            if simple_match:
                try:
                    value = simple_match.group(1).replace(',', '')
                    unit = simple_match.group(2).strip()
                    
                    qualifier = None
                    if "each" in value_string:
                        qualifier = "each"
                        
                    result = create_simple_measurement(
                        entity, name, float(value), unit, qualifier
                    )
                except (ValueError, TypeError) as e:
                    pass
        
        elif declared_type == 'range':
            range_data = parse_range(value_string)
            if range_data:
                qualifier = None
                if "non-condensing" in value_string:
                    qualifier = "non-condensing"
                
                result = create_range_measurement(
                    entity, name,
                    range_data['min'], range_data['max'], 
                    range_data['unit'], qualifier
                )
        
        elif declared_type == 'up_to':
            up_to = parse_up_to(value_string)
            if up_to:
                result = create_up_to_measurement(
                    entity, name, up_to['max'], up_to['unit']
                )
        
        elif declared_type == 'multi_value':
            multi_value = parse_multi_value(value_string)
            if multi_value:
                result = create_multi_value_measurement(
                    entity, name, 
                    multi_value['values'], multi_value['unit']
                )
                
        elif declared_type == 'error_margin':
            error_margin = parse_error_margin(value_string)
            if error_margin:
                result = create_error_margin_measurement(
                    entity, name,
                    error_margin['value'], error_margin['margin'], 
                    error_margin['unit']
                )
                
        elif declared_type == 'dimensions':
            dims = parse_dimension_string(value_string)
           
            if dims and 'height' in dims:
                result = create_dimensions_measurement(
                    entity, name, 
                    dims['length'], dims['width'], dims['height'], 
                    dims['unit']
                )
            elif dims:
                result = create_dimensions_measurement(
                    entity, name, 
                    dims['length'], dims['width'], 
                    unit=dims['unit']
                )
                
        elif declared_type == 'resolution':
            resolution = parse_resolution(value_string)
            if resolution:
                result = create_resolution_measurement(
                    entity, name,
                    resolution['name'], resolution['width'], resolution['height']
                )
        elif declared_type == 'dimensions_weight':
            dims_weight = parse_dimensions_weight(value_string)
            if dims_weight:
                result = create_dimensions_weight_measurement(
                    entity, name, 
                    dims_weight['dimensions']['length'], dims_weight['dimensions']['width'], dims_weight['dimensions']['height'],
                    dims_weight['weight'], dims_weight['dimensions']['unit'], dims_weight['weight_unit']
                ) 
        # Nếu parse theo kiểu khai báo thành công
        if result:
            result = standardize_measurement_on_save(result)
            return result
        
        # Nếu không parse được theo kiểu khai báo, trả về lỗi
        from django.core.exceptions import ValidationError
        return HttpResponse(status=400, content=f"{name.title()} error, please use format {expected_format}")
    
    # Nếu không có khai báo MEASUREMENT_TYPES, thực hiện phân tích tự động
    # Code cũ cho trường hợp không có khai báo
    # 1. Kiểm tra kiểu kích thước + trọng lượng
    dims_weight = parse_dimensions_weight(value_string)
    if dims_weight:
        dims = dims_weight['dimensions']
        return create_dimensions_weight_measurement(
            entity, name, 
            dims['length'], dims['width'], dims.get('height', 0),
            dims_weight['weight'],
            dims['unit'], dims_weight['weight_unit']
        )
    
    # 2. Kiểm tra kiểu kích thước
    dims = parse_dimension_string(value_string)
    if dims and 'height' in dims:
        return create_dimensions_measurement(
            entity, name, 
            dims['length'], dims['width'], dims['height'], 
            dims['unit']
        )
    elif dims:
        return create_dimensions_measurement(
            entity, name, 
            dims['length'], dims['width'], 
            unit=dims['unit']
        )
    
    # 3. Kiểm tra kiểu độ phân giải
    resolution = parse_resolution(value_string)
    if resolution:
        return create_resolution_measurement(
            entity, name,
            resolution['name'], resolution['width'], resolution['height']
        )
    
    # 4. Kiểm tra kiểu dải giá trị
    range_data = parse_range(value_string)
    if range_data:
        qualifier = None
        # Kiểm tra có từ ngữ bổ sung không (như "non-condensing")
        if "non-condensing" in value_string:
            qualifier = "non-condensing"
            
        return create_range_measurement(
            entity, name,
            range_data['min'], range_data['max'], 
            range_data['unit'], qualifier
        )
    
    # 5. Kiểm tra kiểu "up to"
    up_to = parse_up_to(value_string)
    if up_to:
        return create_up_to_measurement(
            entity, name, up_to['max'], up_to['unit']
        )
    
    # 6. Kiểm tra kiểu sai số
    error_margin = parse_error_margin(value_string)
    if error_margin:
        return create_error_margin_measurement(
            entity, name,
            error_margin['value'], error_margin['margin'], 
            error_margin['unit']
        )
    
    # 7. Kiểm tra kiểu nhiều giá trị
    multi_value = parse_multi_value(value_string)
    if multi_value:
        return create_multi_value_measurement(
            entity, name, 
            multi_value['values'], multi_value['unit']
        )
    
    # 8. Kiểu đơn giản - cố gắng phân tích
    simple_pattern = r'(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/\.]+)'
    simple_match = re.search(simple_pattern, value_string)
    
    if simple_match:
        try:
            value = simple_match.group(1).replace(',', '')
            unit = simple_match.group(2).strip()
            
            qualifier = None
            if "each" in value_string:
                qualifier = "each"
                
            return create_simple_measurement(
                entity, name, float(value), unit, qualifier
            )
        except (ValueError, TypeError) as e:
            print(f"Error parsing measurement value: {e}")
    
    # Nếu không thể phân tích được giá trị bằng bất kỳ phương pháp nào
    if measurement_type:
        return HttpResponse(status=400, content=f"{name.title()} error, please use format {expected_format}")
    else:
        return HttpResponse(status=400, content=f"Could not parse measurement value: {value_string}")

def format_number(num):
    """Định dạng số, loại bỏ .0 không cần thiết"""
    return int(num) if num == int(num) else num

def get_formatted_measurement(measurement, user_units=None, model_class=None):
    """
    Trả về chuỗi định dạng đẹp cho hiển thị dựa trên loại dữ liệu
    Convert từ base unit (MEASUREMENT_TYPES) sang display unit (Config)
    
    🚀 PERFORMANCE: model_class parameter avoids N+1 query for measurement.entity
    """

    # If no user_units provided, try to get from system config
    # 🚀 PERFORMANCE: Use cached AdminConfig instead of querying every time
    if not user_units:
        config = get_cached_admin_config()
        if config:
            user_units = config.get('unit_preferences', {})
        else:
            user_units = {}

    # Get entity model name for context-specific units
    # 🚀 PERFORMANCE: Use model_class if provided to avoid measurement.entity query
    # Also check for cached entity to avoid N+1 queries
    model_name = None
    if model_class:
        model_name = model_class.__name__
    elif hasattr(measurement, '_cached_entity') and measurement._cached_entity:
        # Use cached entity to avoid N+1 query
        model_name = measurement._cached_entity.__class__.__name__
    elif hasattr(measurement, 'entity') and measurement.entity:
        model_name = measurement.entity.__class__.__name__
    
    data = measurement.data
    data_type = data.get('type')
    measurement_type = measurement.measurement_type
    
    # Determine target unit based on hierarchical preferences
    target_unit = None
    
    # Check if we have a hierarchical structure
    if isinstance(user_units, dict) and model_name in user_units and isinstance(user_units[model_name], dict):
        # First try model-specific preference
        target_unit = user_units.get(model_name, {}).get(measurement_type)
    
    # If not found and we have a default section, try that
    if not target_unit and isinstance(user_units, dict) and 'default' in user_units:
        target_unit = user_units.get('default', {}).get(measurement_type)
    
    # For backward compatibility, check flat structure
    if not target_unit and isinstance(user_units, dict):
        target_unit = user_units.get(measurement_type)
    
    # Get base unit from entity's MEASUREMENT_TYPES
    # 🚀 PERFORMANCE: Use model_class if provided to avoid measurement.entity query
    # Also check for cached entity to avoid N+1 queries
    base_unit = None
    if model_class and hasattr(model_class, 'MEASUREMENT_TYPES') and measurement_type in model_class.MEASUREMENT_TYPES:
        base_unit = model_class.MEASUREMENT_TYPES[measurement_type].get('default_unit')
    elif hasattr(measurement, '_cached_entity') and measurement._cached_entity:
        # Use cached entity to avoid N+1 query
        entity = measurement._cached_entity
        if entity and hasattr(entity, 'MEASUREMENT_TYPES') and measurement_type in entity.MEASUREMENT_TYPES:
            base_unit = entity.MEASUREMENT_TYPES[measurement_type].get('default_unit')
    elif hasattr(measurement, 'entity') and measurement.entity:
        entity = measurement.entity
        if entity and hasattr(entity, 'MEASUREMENT_TYPES') and measurement_type in entity.MEASUREMENT_TYPES:
            base_unit = entity.MEASUREMENT_TYPES[measurement_type].get('default_unit')
    
    if data_type == 'simple':
        value = data['value']
        unit = data['unit']  # This should be base unit now
        qualifier = data.get('qualifier', '')
        
        # Nếu không có target_unit từ config, hiển thị bằng base unit
        if not target_unit:
            target_unit = base_unit
            
        # Xử lý trường hợp đặc biệt cho 'original' - sử dụng input_unit
        if target_unit == 'original' and 'input_unit' in data:
            target_unit = data['input_unit']
        
        # Chuyển đổi từ base unit sang display unit
        if target_unit and unit != target_unit:
            try:
                converted_value = convert_unit(value, unit, target_unit, measurement_type)
                return f"{format_number(converted_value)} {target_unit}{' ' + qualifier if qualifier else ''}"
            except Exception as e:
                pass  # Sử dụng giá trị base nếu chuyển đổi thất bại
        
        return f"{format_number(value)} {unit}{' ' + qualifier if qualifier else ''}" 
        
    elif data_type == 'string':
        return data['value']
        
    elif data_type == 'range':
        min_val = data['min']
        max_val = data['max']
        unit = data['unit']  # This should be base unit now
        qualifier = data.get('qualifier', '')
        
        # Nếu không có target_unit từ config, hiển thị bằng base unit
        if not target_unit:
            target_unit = base_unit
            
        # Xử lý trường hợp đặc biệt cho 'original' - sử dụng input_unit
        if target_unit == 'original' and 'input_unit' in data:
            target_unit = data['input_unit']
        
        # Chuyển đổi từ base unit sang display unit
        if target_unit and unit != target_unit:
            try:
                min_converted = convert_unit(min_val, unit, target_unit, measurement_type)
                max_converted = convert_unit(max_val, unit, target_unit, measurement_type)
                return f"{format_number(min_converted)}{target_unit} - {format_number(max_converted)}{target_unit}{' ' + qualifier if qualifier else ''}"
            except Exception as e:
                pass  # Sử dụng giá trị base nếu chuyển đổi thất bại
        
        return f"{format_number(min_val)}{unit} - {format_number(max_val)}{unit}{' ' + qualifier if qualifier else ''}"
        
    elif data_type == 'up_to':
        max_val = data['max']
        unit = data['unit']  # This should be base unit now
        
        # Nếu không có target_unit từ config, hiển thị bằng base unit
        if not target_unit:
            target_unit = base_unit
            
        # Xử lý trường hợp đặc biệt cho 'original' - sử dụng input_unit
        if target_unit == 'original' and 'input_unit' in data:
            target_unit = data['input_unit']
        
        # Chuyển đổi từ base unit sang display unit
        if target_unit and unit != target_unit:
            try:
                max_converted = convert_unit(max_val, unit, target_unit, measurement_type)
                return f"Up to {format_number(max_converted)} {target_unit}"
            except Exception as e:
                pass  # Sử dụng giá trị base nếu chuyển đổi thất bại
        
        return f"Up to {format_number(max_val)} {unit}"
        
    elif data_type == 'dimensions':
        length = data['length']
        width = data['width']
        height = data.get('height')
        unit = data['unit']  # This should be base unit now
        
        # Nếu không có target_unit từ config, hiển thị bằng base unit
        if not target_unit:
            target_unit = base_unit
            
        # Xử lý trường hợp đặc biệt cho 'original' - sử dụng input_unit
        if target_unit == 'original' and 'input_unit' in data:
            target_unit = data['input_unit']
        
        # Chuyển đổi từ base unit sang display unit
        if target_unit and unit != target_unit:
            try:
                length_converted = convert_unit(length, unit, target_unit, 'length')
                width_converted = convert_unit(width, unit, target_unit, 'length')
                
                if height is not None:
                    height_converted = convert_unit(height, unit, target_unit, 'length')
                    return f"{format_number(length_converted)}{target_unit} × {format_number(width_converted)}{target_unit} × {format_number(height_converted)}{target_unit}"
                return f"{format_number(length_converted)}{target_unit} × {format_number(width_converted)}{target_unit}"
            except Exception as e:
                pass  # Sử dụng giá trị base nếu chuyển đổi thất bại
        
        if height:
            return f"{format_number(length)}{unit} × {format_number(width)}{unit} × {format_number(height)}{unit}"
        return f"{format_number(length)}{unit} × {format_number(width)}{unit}"
        
    elif data_type == 'error_margin':
        value = data['value']
        margin = data['margin']
        unit = data['unit']  # This should be base unit now
        
        # Nếu không có target_unit từ config, hiển thị bằng base unit
        if not target_unit:
            target_unit = base_unit
            
        # Xử lý trường hợp đặc biệt cho 'original' - sử dụng input_unit
        if target_unit == 'original' and 'input_unit' in data:
            target_unit = data['input_unit']
        
        # Chuyển đổi từ base unit sang display unit
        if target_unit and unit != target_unit:
            try:
                value_converted = convert_unit(value, unit, target_unit, measurement_type)
                margin_converted = convert_unit(margin, unit, target_unit, measurement_type)
                
                if value_converted == 0:
                    return f"±{format_number(margin_converted)} {target_unit}"
                else:
                    return f"{format_number(value_converted)} ±{format_number(margin_converted)} {target_unit}"
            except Exception as e:
                pass  # Sử dụng giá trị base nếu chuyển đổi thất bại
        
        if value == 0:
            return f"±{format_number(margin)} {unit}"
        else:
            return f"{format_number(value)} ±{format_number(margin)} {unit}"
            
    elif data_type == 'resolution':
        name = data['name']
        width = data['width']
        height = data['height']
        unit = data.get('unit', 'px')  # Default to px if not specified
        
        # Không cần chuyển đổi đơn vị cho độ phân giải
        if name:
            return f"{name} ({format_number(width)} × {format_number(height)} {unit})"
        return f"{format_number(width)}{unit} × {format_number(height)}{unit}"
        
    elif data_type == 'multi_value':
        values = data['values']
        unit = data['unit']  # This should be base unit now
        
        # Nếu không có target_unit từ config, hiển thị bằng base unit
        if not target_unit:
            target_unit = base_unit
            
        # Xử lý trường hợp đặc biệt cho 'original' - sử dụng input_unit
        if target_unit == 'original' and 'input_unit' in data:
            target_unit = data['input_unit']
        
        # Chuyển đổi từ base unit sang display unit
        if target_unit and unit != target_unit:
            try:
                converted_values = [convert_unit(value, unit, target_unit, measurement_type) for value in values]
                return " and ".join([f"{format_number(value)} {target_unit}" for value in converted_values])
            except Exception as e:
                pass  # Sử dụng giá trị base nếu chuyển đổi thất bại
        
        return " and ".join([f"{format_number(value)} {unit}" for value in values])
        
    elif data_type == 'dimensions_weight':
        length = data['length']
        width = data['width']
        height = data['height']
        weight = data['weight']
        dimension_unit = data['dimension_unit']
        weight_unit = data['weight_unit']
        
        # Get target units for dimensions and weight
        target_dim_unit = None
        target_weight_unit = None
        
        # Try to get dimension unit preference
        if model_name and 'dimensions' in (user_units.get(model_name, {})):
            target_dim_unit = user_units[model_name]['dimensions']
        elif 'default' in user_units and 'dimensions' in user_units['default']:
            target_dim_unit = user_units['default']['dimensions']
        elif 'dimensions' in user_units:
            target_dim_unit = user_units['dimensions']
            
        # Try to get weight unit preference
        if model_name and 'weight' in (user_units.get(model_name, {})):
            target_weight_unit = user_units[model_name]['weight']
        elif 'default' in user_units and 'weight' in user_units['default']:
            target_weight_unit = user_units['default']['weight']
        elif 'weight' in user_units:
            target_weight_unit = user_units['weight']
        
        # Handle original unit preference
        if target_dim_unit == 'original' and 'original_dimension_unit' in data:
            target_dim_unit = data['original_dimension_unit']
        if target_weight_unit == 'original' and 'original_weight_unit' in data:
            target_weight_unit = data['original_weight_unit']
        
        # Chuyển đổi kích thước nếu cần
        if target_dim_unit and dimension_unit != target_dim_unit:
            try:
                length = convert_unit(length, dimension_unit, target_dim_unit)
                width = convert_unit(width, dimension_unit, target_dim_unit)
                height = convert_unit(height, dimension_unit, target_dim_unit)
                dimension_unit = target_dim_unit
            except Exception:
                pass
        
        # Chuyển đổi trọng lượng nếu cần
        if target_weight_unit and weight_unit != target_weight_unit:
            try:
                weight = convert_unit(weight, weight_unit, target_weight_unit)
                weight_unit = target_weight_unit
            except Exception:
                pass
        
        return f"{format_number(length)} × {format_number(width)} × {format_number(height)} {dimension_unit} {format_number(weight)} {weight_unit}"
    
    # Mặc định trả về chuỗi rỗng cho các loại không nhận diện được
    return ""

def get_numeric_value(measurement, component=None, user_units=None):
    """
    Trả về giá trị số thuần túy cho tính toán, có hỗ trợ chuyển đổi đơn vị
    component: Chỉ định phần cụ thể muốn lấy giá trị (min, max, length, etc.)
    user_units: Dictionary of user's unit preferences for conversion
    """
    data = measurement.data
    data_type = data.get('type')
    
    # Get target unit if user_units is provided
    target_unit = None
    # 🚀 PERFORMANCE: Use cached AdminConfig instead of querying every time
    if not user_units:
        config = get_cached_admin_config()
        if config:
            user_units = config.get('unit_preferences', {})
        else:
            user_units = {}
    
    if user_units:
        
        # Get entity model name for context-specific units
        model_name = None
        if hasattr(measurement, 'entity') and measurement.entity:
            model_name = measurement.entity.__class__.__name__
        
        # Determine target unit based on hierarchical preferences
        measurement_type = measurement.measurement_type
        
        # Check if we have a hierarchical structure
        if isinstance(user_units, dict) and model_name in user_units and isinstance(user_units[model_name], dict):
            # First try model-specific preference
            target_unit = user_units.get(model_name, {}).get(measurement_type)
        
        # If not found and we have a default section, try that
        if not target_unit and isinstance(user_units, dict) and 'default' in user_units:
            target_unit = user_units.get('default', {}).get(measurement_type)
        
        # For backward compatibility, check flat structure
        if not target_unit and isinstance(user_units, dict):
            target_unit = user_units.get(measurement_type)
        
        # Handle special case for 'original' unit preference
        if target_unit == 'original' and 'original_unit' in data:
            target_unit = data['original_unit']
    
    # Helper function to convert value if needed
    def convert_if_needed(value, current_unit):
        if target_unit and current_unit and target_unit != current_unit:
            try:
                return convert_unit(value, current_unit, target_unit)
            except Exception:
                return value  # Return original if conversion fails
        return value
    
    if component:
        value = data.get(component)
        if value is not None and target_unit:
            current_unit = data.get('unit')
            return convert_if_needed(value, current_unit)
        return value
        
    if data_type == 'simple':
        value = data['value']
        current_unit = data.get('unit')
        return convert_if_needed(value, current_unit)
        
    elif data_type == 'range':
        current_unit = data.get('unit')
        if component == 'min':
            return convert_if_needed(data['min'], current_unit)
        elif component == 'max':
            return convert_if_needed(data['max'], current_unit)
        else:
            # Mặc định trả về trung bình
            avg_value = (data['min'] + data['max']) / 2
            return convert_if_needed(avg_value, current_unit)
            
    elif data_type == 'up_to':
        current_unit = data.get('unit')
        return convert_if_needed(data['max'], current_unit)
        
    elif data_type == 'dimensions':
        current_unit = data.get('unit')
        # Mặc định trả về thể tích nếu đủ 3 chiều
        if 'height' in data:
            volume = data['length'] * data['width'] * data['height']
            # For volume, we need to convert the unit cubed
            if target_unit and current_unit and target_unit != current_unit:
                try:
                    # Convert each dimension and calculate volume
                    length_conv = convert_unit(data['length'], current_unit, target_unit)
                    width_conv = convert_unit(data['width'], current_unit, target_unit) 
                    height_conv = convert_unit(data['height'], current_unit, target_unit)
                    return length_conv * width_conv * height_conv
                except Exception:
                    return volume
            return volume
        else:
            area = data['length'] * data['width']
            # For area, we need to convert the unit squared
            if target_unit and current_unit and target_unit != current_unit:
                try:
                    length_conv = convert_unit(data['length'], current_unit, target_unit)
                    width_conv = convert_unit(data['width'], current_unit, target_unit)
                    return length_conv * width_conv
                except Exception:
                    return area
            return area
            
    elif data_type == 'dimensions_weight':
        if component == 'weight':
            weight_unit = data.get('weight_unit')
            weight_target = None
            if user_units:
                # Try to get weight unit preference
                if model_name and 'weight' in (user_units.get(model_name, {})):
                    weight_target = user_units[model_name]['weight']
                elif 'default' in user_units and 'weight' in user_units['default']:
                    weight_target = user_units['default']['weight']
                elif 'weight' in user_units:
                    weight_target = user_units['weight']
            return convert_if_needed(data['weight'], weight_unit) if weight_target else data['weight']
        else:
            # Return volume - similar to dimensions case
            current_unit = data.get('dimension_unit')
            volume = data['length'] * data['width'] * data['height']
            if target_unit and current_unit and target_unit != current_unit:
                try:
                    length_conv = convert_unit(data['length'], current_unit, target_unit)
                    width_conv = convert_unit(data['width'], current_unit, target_unit)
                    height_conv = convert_unit(data['height'], current_unit, target_unit)
                    return length_conv * width_conv * height_conv
                except Exception:
                    return volume
            return volume
            
    elif data_type == 'error_margin':
        current_unit = data.get('unit')
        if component == 'margin':
            return convert_if_needed(data['margin'], current_unit)
        else:
            return convert_if_needed(data['value'], current_unit)
            
    elif data_type == 'resolution':
        # Resolution typically doesn't need unit conversion
        if component == 'megapixels':
            return (data['width'] * data['height']) / 1000000
        elif component == 'width':
            return data['width']
        elif component == 'height':
            return data['height']
        else:
            return data['width'] * data['height']
            
    elif data_type == 'multi_value':
        # Trả về giá trị đầu tiên nếu không có chỉ định cụ thể
        if isinstance(data['values'], list) and len(data['values']) > 0:
            current_unit = data.get('unit')
            return convert_if_needed(data['values'][0], current_unit)
    
    return None

def standardize_measurement_on_save(measurement):
    """
    Chuẩn hóa đơn vị của một measurement trước khi lưu vào DB,
    sử dụng default_unit từ MEASUREMENT_TYPES của model làm đơn vị gốc.
    """
    measurement_type = measurement.measurement_type
    data = measurement.data
    data_type = data.get('type')
    
    # Lấy entity để access MEASUREMENT_TYPES
    entity = measurement.entity
    if not entity or not hasattr(entity, 'MEASUREMENT_TYPES'):
        return measurement
    
    # Kiểm tra xem measurement_type có trong MEASUREMENT_TYPES không
    if measurement_type not in entity.MEASUREMENT_TYPES:
        return measurement
    
    # Lấy default_unit từ MEASUREMENT_TYPES làm base unit
    measurement_config = entity.MEASUREMENT_TYPES[measurement_type]
    base_unit = measurement_config.get('default_unit')
    if not base_unit:
        return measurement
    
    # Xử lý theo từng loại phép đo
    try:
        if data_type == 'simple':
            current_unit = data.get('unit')
            if current_unit and current_unit != base_unit:
                value = data.get('value')
                base_value = convert_unit(value, current_unit, base_unit, measurement_type)
                data['value'] = base_value
                data['input_unit'] = current_unit  # Lưu đơn vị input
                data['unit'] = base_unit  # Lưu về base unit
        
        elif data_type == 'range':
            current_unit = data.get('unit')
            if current_unit and current_unit != base_unit:
                min_val = data.get('min')
                max_val = data.get('max')
                base_min = convert_unit(min_val, current_unit, base_unit, measurement_type)
                base_max = convert_unit(max_val, current_unit, base_unit, measurement_type)
                data['min'] = base_min
                data['max'] = base_max
                data['input_unit'] = current_unit  # Lưu đơn vị input
                data['unit'] = base_unit  # Lưu về base unit
        
        elif data_type == 'up_to':
            current_unit = data.get('unit')
            if current_unit and current_unit != base_unit:
                max_val = data.get('max')
                base_max = convert_unit(max_val, current_unit, base_unit, measurement_type)
                data['max'] = base_max
                data['input_unit'] = current_unit  # Lưu đơn vị input
                data['unit'] = base_unit  # Lưu về base unit
        
        elif data_type == 'dimensions':
            current_unit = data.get('unit')
            if current_unit and current_unit != base_unit:
                length = data.get('length')
                width = data.get('width')
                height = data.get('height')
                
                data['length'] = convert_unit(length, current_unit, base_unit, 'length')
                data['width'] = convert_unit(width, current_unit, base_unit, 'length')
                if height is not None:
                    data['height'] = convert_unit(height, current_unit, base_unit, 'length')
                
                data['input_unit'] = current_unit  # Lưu đơn vị input
                data['unit'] = base_unit  # Lưu về base unit
        
        elif data_type == 'dimensions_weight':
            dim_unit = data.get('dimension_unit')
            weight_unit = data.get('weight_unit')
            
            # Lấy base units từ measurement config
            base_dim_unit = measurement_config.get('default_dimension_unit', 'mm')
            base_weight_unit = measurement_config.get('default_weight_unit', 'kg')
            
            # Nếu không có config riêng, parse từ base_unit chung (format: 'mm x kg')
            if 'default_dimension_unit' not in measurement_config and 'default_weight_unit' not in measurement_config:
                if ' x ' in base_unit:
                    parts = base_unit.split(' x ')
                    base_dim_unit = parts[0].strip()
                    base_weight_unit = parts[1].strip() if len(parts) > 1 else 'kg'
                else:
                    base_dim_unit = 'mm'
                    base_weight_unit = 'kg'
            
            # Xử lý đơn vị kích thước
            if dim_unit and dim_unit != base_dim_unit:
                length = data.get('length')
                width = data.get('width')
                height = data.get('height')
                
                data['length'] = convert_unit(length, dim_unit, base_dim_unit, 'length')
                data['width'] = convert_unit(width, dim_unit, base_dim_unit, 'length')
                if height is not None:
                    data['height'] = convert_unit(height, dim_unit, base_dim_unit, 'length')
                
                data['input_dimension_unit'] = dim_unit  # Lưu đơn vị input
                data['dimension_unit'] = base_dim_unit
            
            # Xử lý đơn vị trọng lượng
            if weight_unit and weight_unit != base_weight_unit:
                weight = data.get('weight')
                data['weight'] = convert_unit(weight, weight_unit, base_weight_unit, 'weight')
                data['input_weight_unit'] = weight_unit  # Lưu đơn vị input
                data['weight_unit'] = base_weight_unit
        
        elif data_type == 'multi_value':
            current_unit = data.get('unit')
            if current_unit and current_unit != base_unit:
                values = data.get('values', [])
                base_values = [convert_unit(val, current_unit, base_unit, measurement_type) for val in values]
                data['values'] = base_values
                data['input_unit'] = current_unit  # Lưu đơn vị input
                data['unit'] = base_unit  # Lưu về base unit
        
        elif data_type == 'error_margin':
            current_unit = data.get('unit')
            if current_unit and current_unit != base_unit:
                value = data.get('value')
                margin = data.get('margin')
                
                data['value'] = convert_unit(value, current_unit, base_unit, measurement_type)
                data['margin'] = convert_unit(margin, current_unit, base_unit, measurement_type)
                data['input_unit'] = current_unit  # Lưu đơn vị input
                data['unit'] = base_unit  # Lưu về base unit
        
        # Lưu lại thay đổi
        measurement.data = data
        measurement.save()
        
    except Exception as e:
        print(f"Error standardizing {measurement_type} (type: {data_type}): {e}")
    
    return measurement

def filter_mensurement(queryset, entity, request):
    from django.db.models import Q
    from devices.models import Measurement
    from django.db import connection

    if not hasattr(entity, 'MEASUREMENT_TYPES') or not entity.MEASUREMENT_TYPES:
        return queryset

    # 🚀 PERFORMANCE: Use cached AdminConfig instead of DB query
    user_unit = get_cached_admin_config('Unit Config')

    # 🚀 PERFORMANCE: Use cached ContentType
    content_type = get_cached_content_type(entity)
    base_queryset = queryset
    
    # OPTIMIZATION: Xử lý sorting với database-level optimization
    if request.GET.get('sort_obj'):
        order_params = json.loads(request.GET.get('sort_obj'))
        
        # OPTIMIZATION: Batch process tất cả measurement types cần sort
        measurement_types_to_sort = []
        for order_param in order_params:
            if order_param['key'] in entity.MEASUREMENT_TYPES:
                measurement_types_to_sort.append({
                    'key': order_param['key'],
                    'direction': order_param['value'].lower(),
                    'info': entity.MEASUREMENT_TYPES[order_param['key']]
                })
        
        if measurement_types_to_sort:
            # OPTIMIZATION: Sử dụng PostgreSQL JSONB optimization nếu có thể
            if connection.vendor == 'postgresql':
                # Tạo một annotation duy nhất cho tất cả measurement types
                annotation_fields = {}
                order_fields = []
                
                for sort_info in measurement_types_to_sort:
                    measurement_type = sort_info['key']
                    direction = sort_info['direction']
                    data_type = sort_info['info'].get('type')
                    
                    # Tạo field name cho annotation
                    sort_field = f"sort_{measurement_type}"
                    
                    # Tạo SQL query tối ưu cho PostgreSQL JSONB
                    if data_type in ['simple', 'range', 'up_to', 'multi_value', 'error_margin']:
                        # Sử dụng JSONB operators trực tiếp
                        jsonb_sql = f"""
                        SELECT 
                            CASE 
                                WHEN data->>'type' = '{data_type}' THEN
                                    CASE 
                                        WHEN data->>'type' = 'range' THEN CAST(data->>'max' AS FLOAT)
                                        WHEN data->>'type' = 'up_to' THEN CAST(data->>'max' AS FLOAT)
                                        WHEN data->>'type' = 'multi_value' THEN CAST(data->'values'->>0 AS FLOAT)
                                        WHEN data->>'type' = 'error_margin' THEN CAST(data->>'value' AS FLOAT)
                                        ELSE CAST(data->>'value' AS FLOAT)
                                    END
                                ELSE 0.0
                            END
                        FROM {Measurement._meta.db_table}
                        WHERE content_type_id = %s 
                        AND measurement_type = %s 
                        AND object_id = {base_queryset.model._meta.db_table}.id
                        LIMIT 1
                        """
                        
                        # Thêm annotation field
                        annotation_fields[sort_field] = Subquery(
                            Measurement.objects.filter(
                                content_type=content_type,
                                measurement_type=measurement_type,
                                object_id=OuterRef('id')
                            ).extra(
                                select={'jsonb_value': jsonb_sql},
                                select_params=[content_type.id, measurement_type]
                            ).values('jsonb_value')[:1],
                            output_field=FloatField()
                        )
                        
                        # Thêm vào order fields
                        order_fields.append(f"{'-' if direction == 'desc' else ''}{sort_field}")
                    
                    elif data_type == 'dimensions':
                        # Xử lý dimensions với JSONB optimization
                        for dim in ['length', 'width', 'height']:
                            dim_field = f"sort_{measurement_type}_{dim}"
                            jsonb_sql = f"""
                            SELECT CAST(data->>'{dim}' AS FLOAT)
                            FROM {Measurement._meta.db_table}
                            WHERE content_type_id = %s 
                            AND measurement_type = %s 
                            AND object_id = {base_queryset.model._meta.db_table}.id
                            AND data->>'type' = 'dimensions'
                            LIMIT 1
                            """
                            
                            annotation_fields[dim_field] = Subquery(
                                Measurement.objects.filter(
                                    content_type=content_type,
                                    measurement_type=measurement_type,
                                    object_id=OuterRef('id')
                                ).extra(
                                    select={'jsonb_value': jsonb_sql},
                                    select_params=[content_type.id, measurement_type]
                                ).values('jsonb_value')[:1],
                                output_field=FloatField()
                            )
                            
                            order_fields.append(f"{'-' if direction == 'desc' else ''}{dim_field}")
                    
                    elif data_type == 'dimensions_weight':
                        # Xử lý weight với JSONB optimization
                        weight_field = f"sort_{measurement_type}_weight"
                        jsonb_sql = f"""
                        SELECT CAST(data->>'weight' AS FLOAT)
                        FROM {Measurement._meta.db_table}
                        WHERE content_type_id = %s 
                        AND measurement_type = %s 
                        AND object_id = {base_queryset.model._meta.db_table}.id
                        AND data->>'type' = 'dimensions_weight'
                        LIMIT 1
                        """
                        
                        annotation_fields[weight_field] = Subquery(
                            Measurement.objects.filter(
                                content_type=content_type,
                                measurement_type=measurement_type,
                                object_id=OuterRef('id')
                            ).extra(
                                select={'jsonb_value': jsonb_sql},
                                select_params=[content_type.id, measurement_type]
                            ).values('jsonb_value')[:1],
                            output_field=FloatField()
                        )
                        
                        order_fields.append(f"{'-' if direction == 'desc' else ''}{weight_field}")
                    
                    elif data_type == 'resolution':
                        # Xử lý resolution với JSONB optimization
                        for dim in ['width', 'height']:
                            res_field = f"sort_{measurement_type}_{dim}"
                            jsonb_sql = f"""
                            SELECT CAST(data->>'{dim}' AS INTEGER)
                            FROM {Measurement._meta.db_table}
                            WHERE content_type_id = %s 
                            AND measurement_type = %s 
                            AND object_id = {base_queryset.model._meta.db_table}.id
                            AND data->>'type' = 'resolution'
                            LIMIT 1
                            """
                            
                            annotation_fields[res_field] = Subquery(
                                Measurement.objects.filter(
                                    content_type=content_type,
                                    measurement_type=measurement_type,
                                    object_id=OuterRef('id')
                                ).extra(
                                    select={'jsonb_value': jsonb_sql},
                                    select_params=[content_type.id, measurement_type]
                                ).values('jsonb_value')[:1],
                                output_field=IntegerField()
                            )
                            
                            order_fields.append(f"{'-' if direction == 'desc' else ''}{res_field}")
                
                # 🚀 CRITICAL FIX: Apply annotations preserving original measure field names
                if annotation_fields:
                    base_queryset = base_queryset.annotate(**annotation_fields)
                    
                    # 🔧 PRESERVE MEASURE FIELDS: Add original measure field names
                    # Issue: sort_time_stops được tạo nhưng time_stops bị mất trong schema
                    measure_field_preservation = {}
                    for sort_info in measurement_types_to_sort:
                        measurement_type = sort_info['key']
                        sort_field = f"sort_{measurement_type}"
                        
                        # Add original measure field name pointing to same annotation value
                        if sort_field in annotation_fields:
                            measure_field_preservation[measurement_type] = annotation_fields[sort_field]
                    
                    # Apply preserved measure fields so both sort_time_stops AND time_stops exist
                    if measure_field_preservation:
                        base_queryset = base_queryset.annotate(**measure_field_preservation)
                    
                    # Áp dụng ordering
                    if order_fields:
                        base_queryset = base_queryset.order_by(*order_fields)
            
            else:
                # Fallback cho database khác PostgreSQL - sử dụng logic cũ nhưng tối ưu hơn
                for sort_info in measurement_types_to_sort:
                    measurement_type = sort_info['key']
                    direction = sort_info['direction']
                    data_type = sort_info['info'].get('type')
                    
                    # Tạo subquery tối ưu
                    subquery = Measurement.objects.filter(
                        content_type=content_type,
                        measurement_type=measurement_type,
                        object_id=OuterRef('id')
                    ).only('data')  # Chỉ lấy data field cần thiết
                    
                    # Áp dụng ordering dựa trên data type
                    if data_type == 'simple':
                        base_queryset = base_queryset.annotate(
                            sort_value=Coalesce(
                                Cast(Subquery(subquery.values('data__value')[:1]), FloatField()),
                                Value(0.0),
                                output_field=FloatField()
                            )
                        ).order_by(
                            '-sort_value' if direction == 'desc' else 'sort_value'
                        )
                    
                    elif data_type in ['range', 'up_to']:
                        base_queryset = base_queryset.annotate(
                            sort_value=Coalesce(
                                Cast(Subquery(subquery.values('data__max')[:1]), FloatField()),
                                Value(0.0),
                                output_field=FloatField()
                            )
                        ).order_by(
                            '-sort_value' if direction == 'desc' else 'sort_value'
                        )
                    
                    elif data_type == 'dimensions':
                        base_queryset = base_queryset.annotate(
                            sort_length=Coalesce(
                                Cast(Subquery(subquery.values('data__length')[:1]), FloatField()),
                                Value(0.0),
                                output_field=FloatField()
                            ),
                            sort_width=Coalesce(
                                Cast(Subquery(subquery.values('data__width')[:1]), FloatField()),
                                Value(0.0),
                                output_field=FloatField()
                            ),
                            sort_height=Coalesce(
                                Cast(Subquery(subquery.values('data__height')[:1]), FloatField()),
                                Value(0.0),
                                output_field=FloatField()
                            )
                        ).order_by(
                            '-sort_length' if direction == 'desc' else 'sort_length',
                            '-sort_width' if direction == 'desc' else 'sort_width',
                            '-sort_height' if direction == 'desc' else 'sort_height'
                        )
                    
                    elif data_type == 'dimensions_weight':
                        base_queryset = base_queryset.annotate(
                            sort_value=Coalesce(
                                Cast(Subquery(subquery.values('data__weight')[:1]), FloatField()),
                                Value(0.0),
                                output_field=FloatField()
                            )
                        ).order_by(
                            '-sort_value' if direction == 'desc' else 'sort_value'
                        )
                    
                    elif data_type == 'multi_value':
                        base_queryset = base_queryset.annotate(
                            sort_value=Coalesce(
                                Cast(Subquery(subquery.values('data__values__0')[:1]), FloatField()),
                                Value(0.0),
                                output_field=FloatField()
                            )
                        ).order_by(
                            '-sort_value' if direction == 'desc' else 'sort_value'
                        )
                    
                    elif data_type == 'resolution':
                        base_queryset = base_queryset.annotate(
                            sort_width=Coalesce(
                                Cast(Subquery(subquery.values('data__width')[:1]), IntegerField()),
                                Value(0),
                                output_field=IntegerField()
                            ),
                            sort_height=Coalesce(
                                Cast(Subquery(subquery.values('data__height')[:1]), IntegerField()),
                                Value(0),
                                output_field=IntegerField()
                            )
                        ).order_by(
                            '-sort_width' if direction == 'desc' else 'sort_width',
                            '-sort_height' if direction == 'desc' else 'sort_height'
                        )
                    
                    elif data_type == 'error_margin':
                        base_queryset = base_queryset.annotate(
                            sort_value=Coalesce(
                                Cast(Subquery(subquery.values('data__value')[:1]), FloatField()),
                                Value(0.0),
                                output_field=FloatField()
                            )
                        ).order_by(
                            '-sort_value' if direction == 'desc' else 'sort_value'
                        )
        
    
    measurement_filters = {}
    has_measurement_filters = False
    
    # Thu thập tất cả measurement filters
    for key, value in request.GET.items():
        if key in entity.MEASUREMENT_TYPES and value:
            measurement_filters[key] = value
            has_measurement_filters = True
    if not has_measurement_filters:
        return base_queryset
    
    if measurement_filters:
        # OPTIMIZATION: Sử dụng PostgreSQL JSONB optimization cho filtering
        if connection.vendor == 'postgresql':
            # Tạo một query duy nhất cho tất cả measurement types
            all_filter_conditions = []
            
            for measurement_type, value in measurement_filters.items():
                measurement_config = entity.MEASUREMENT_TYPES.get(measurement_type, {})
                default_unit = measurement_config.get('default_unit')
                data_type = measurement_config.get('type')
                context_key = measurement_type
                if default_unit:
                    context_key = f"{measurement_type}|{default_unit}"
                
                standard_unit = STANDARD_INTERNATIONAL_UNITS.get(measurement_type) or default_unit or ''
                user_units = []
                if standard_unit:
                    user_units.append(standard_unit)
                if default_unit and default_unit not in user_units:
                    user_units.append(default_unit)
                
                if isinstance(user_unit, dict):
                    user_units += [u for u in user_unit.get('default', {}).values() if u]
                
                # 🚀 PERFORMANCE: Use pre-compiled regex patterns
                all_numbers = _NUMBER_PATTERN.findall(value)
                unit_candidates = _UNIT_PATTERN.findall(value)
                unit = unit_candidates[-1] if unit_candidates else ''
                
                # 🚀 FIX: Check if unit is a partial/prefix of standard_unit (e.g., 'k' → 'km')
                # This handles cases like "2.77k" where user types partial unit
                partial_unit_match = False
                if unit and standard_unit:
                    unit_lower = unit.lower()
                    std_lower = standard_unit.lower()
                    # Check if unit is prefix of standard_unit (e.g., 'k' is prefix of 'km')
                    if std_lower.startswith(unit_lower) and len(unit_lower) < len(std_lower):
                        partial_unit_match = True
                        # Treat as if user typed the full standard unit
                        unit = standard_unit
                
                standardized_unit = standardize_unit(unit, context_key) if unit else ''
                target_standard_unit = standardize_unit(standard_unit, context_key) if standard_unit else ''
                valid_unit = any(
                    u for u in user_units
                    if u and standardize_unit(u, context_key) == standardized_unit
                ) or partial_unit_match  # Include partial matches as valid
                unit_terms = set()
                
                # 🚀 FIX: Create parameterized JSONB SQL query (no % formatting conflicts)
                jsonb_conditions = []
                jsonb_expression_groups = []
                query_params = [content_type.id, measurement_type]  # Base params
                
                if all_numbers:
                    try:
                        numbers = []
                        for num in all_numbers:
                            try:
                                numbers.append(float(num))
                            except ValueError:
                                pass
                        if not numbers:
                            raise ValueError("No numeric values parsed")
                        
                        # 🚀 FIX: Only convert when valid_unit=True AND units are different
                        # This prevents invalid conversions like Kelvin → km
                        original_numbers = numbers.copy()  # Keep backup for fallback
                        if (
                            valid_unit  # ✅ CRITICAL: Only convert valid units
                            and unit
                            and standard_unit
                            and standardized_unit
                            and target_standard_unit
                            and standardized_unit != target_standard_unit
                        ):
                            try:
                                converted_numbers = []
                                for num in numbers:
                                    converted = convert_unit(num, unit, standard_unit, measurement_type)
                                    # Ensure we got a valid number back
                                    if isinstance(converted, (int, float)):
                                        converted_numbers.append(converted)
                                    else:
                                        raise ValueError(f"Invalid conversion result: {converted}")
                                numbers = converted_numbers
                                unit = standard_unit
                                standardized_unit = target_standard_unit
                            except (ValueError, TypeError) as conv_err:
                                # Conversion failed - fallback to original numbers
                                logger.debug(f"[MEASURE_FILTER] Conversion failed ({unit}→{standard_unit}): {conv_err}, using original numbers")
                                numbers = original_numbers
                        
                        if len(numbers) == 2:
                            min_val, max_val = min(numbers), max(numbers)
                            jsonb_expression_groups.append(
                                """
                                (data->>'type' = 'range' AND 
                                 CAST(data->>'min' AS FLOAT) >= %s AND 
                                 CAST(data->>'max' AS FLOAT) <= %s)
                                OR
                                (data->>'type' = 'dimensions' AND 
                                 CAST(data->>'length' AS FLOAT) >= %s AND 
                                 CAST(data->>'width' AS FLOAT) <= %s)
                                OR
                                (data->>'type' = 'resolution' AND 
                                 CAST(data->>'width' AS INTEGER) >= %s AND 
                                 CAST(data->>'height' AS INTEGER) <= %s)
                                OR
                                (data->>'type' = 'multi_value' AND 
                                 data->'values'::text ILIKE %s AND 
                                 data->'values'::text ILIKE %s)
                                """
                            )
                            query_params.extend([min_val, max_val, min_val, max_val, int(min_val), int(max_val), f'%{min_val}%', f'%{max_val}%'])
                        else:
                            number_value = numbers[0]
                            if isinstance(number_value, (int, float)):
                                if float(number_value).is_integer():
                                    number_str = str(int(number_value))
                                else:
                                    number_str = format(number_value, 'f').rstrip('0').rstrip('.')
                                    if not number_str:
                                        number_str = str(number_value)
                            else:
                                number_str = str(number_value)

                            clause_parts = []
                            clause_params = []

                            if data_type == 'simple' and isinstance(number_value, (int, float)):
                                numeric_values = [float(number_value)]
                                if float(number_value).is_integer():
                                    numeric_values.append(int(number_value))
                                numeric_clause = "(" + " OR ".join(["(data->>'value')::FLOAT = %s"] * len(numeric_values)) + ")"
                                clause_parts.append(numeric_clause)
                                clause_params.extend(numeric_values)

                            clause_parts.append("data::text ILIKE %s")
                            clause_params.append(f'%{number_str}%')

                            jsonb_expression_groups.append("(" + " OR ".join(clause_parts) + ")")
                            query_params.extend(clause_params)
                    
                    except Exception as e:
                        # Fallback to text search
                        for num in all_numbers:
                            jsonb_conditions.append("data::text ILIKE %s")
                            query_params.append(f'%{num}%')
                
                if unit and valid_unit:
                    ambiguous_unit_terms = {'m'}

                    def add_unit_term(term):
                        if not term:
                            return
                        normalized = term.strip()
                        if not normalized:
                            return
                        if normalized.lower() in ambiguous_unit_terms:
                            return
                        unit_terms.add(normalized)

                    add_unit_term(unit)
                    add_unit_term(standardized_unit)
                    add_unit_term(default_unit)

                    if (standardized_unit and standardized_unit.lower() == 'min') or (
                        default_unit and standardize_unit(default_unit, context_key) == 'min'
                    ):
                        unit_terms.update({'min', 'mins', 'minute', 'minutes'})

                    if unit_terms:
                        ordered_unit_terms = sorted(unit_terms)
                        unit_clauses = ["data::text ILIKE %s" for _ in ordered_unit_terms]
                        jsonb_expression_groups.append(f"({' OR '.join(unit_clauses)})")
                        query_params.extend([f'%{term}%' for term in ordered_unit_terms])
                
                # 🚀 FIX: Search in specific fields, EXCLUDE "type" field from search
                if not all_numbers and not valid_unit:
                    # Check if search value is meaningful (not just single letter like 'p')
                    if len(value.strip()) >= 2 or value.strip().isdigit():
                        # Search only in meaningful fields, EXCLUDE "type" field
                        search_value = f'%{value}%'
                        field_conditions = [
                            "(data->>'unit' ILIKE %s)",           # unit field
                            "(data->>'name' ILIKE %s)",           # name field  
                            "(data->>'value'::text ILIKE %s)",    # value field
                            "(data->>'width'::text ILIKE %s)",    # resolution width
                            "(data->>'height'::text ILIKE %s)",   # resolution height
                            "(data->>'min'::text ILIKE %s)",      # range min
                            "(data->>'max'::text ILIKE %s)"       # range max
                        ]
                        jsonb_expression_groups.append(" OR ".join(field_conditions))
                        # Add search value for each condition (7 fields = 7 params)
                        query_params.extend([search_value] * 7)
                    # If value is too short/meaningless, don't add any condition (will return empty)
                
                # 🚀 FIX: Build SQL with proper parameterized queries
                jsonb_conditions = [expr for expr in jsonb_expression_groups if expr]

                produced_sql = ' AND '.join(jsonb_conditions) if jsonb_conditions else ''
                

                if jsonb_conditions:
                    # Tạo SQL query tối ưu với proper parameters
                    jsonb_sql = f"""
                    SELECT DISTINCT object_id
                    FROM {Measurement._meta.db_table}
                    WHERE content_type_id = %s 
                    AND measurement_type = %s 
                    AND ({' AND '.join(jsonb_conditions)})
                    """
                    
                    all_filter_conditions.append({
                        'sql': jsonb_sql,
                        'params': query_params  # Use the complete parameter list
                    })
                else:
                    # 🔧 NO CONDITIONS: If no valid search conditions found, return empty
                    # This happens when search value is meaningless (like single letter 'p')
                    empty_sql = f"""
                    SELECT DISTINCT object_id
                    FROM {Measurement._meta.db_table}
                    WHERE content_type_id = %s 
                    AND measurement_type = %s 
                    AND 1=0
                    """
                    
                    all_filter_conditions.append({
                        'sql': empty_sql,
                        'params': [content_type.id, measurement_type]
                    })
            
            # Thực thi tất cả queries và lấy intersection
            if all_filter_conditions:
                all_matching_ids = set()
                first_query = True
                
                for filter_condition in all_filter_conditions:
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(filter_condition['sql'], filter_condition['params'])
                            results = cursor.fetchall()
                            # 🚀 SAFETY: Check if results exist and have proper structure
                            matching_ids = {row[0] for row in results if row and len(row) > 0}
                            
                            if first_query:
                                all_matching_ids = matching_ids
                                first_query = False
                            else:
                                all_matching_ids &= matching_ids
                    except Exception as e:
                        # 🚨 ERROR HANDLING: Log error and continue with empty set
                        print(f"⚠️ [MEASURE_SEARCH] Error executing SQL: {e}")
                        print(f"📝 SQL: {filter_condition['sql']}")
                        print(f"📝 Params: {filter_condition['params']}")
                        
                        # Continue with empty matching set for this condition
                        if first_query:
                            all_matching_ids = set()
                            first_query = False
                        else:
                            all_matching_ids &= set()
                
                # 🚀 FIX: Áp dụng filter cho cả empty set (trả về 0 results khi search không match)
                # Chỉ skip filter nếu all_filter_conditions rỗng (không có conditions nào)
                if all_filter_conditions:  # Có conditions được tạo
                    if all_matching_ids:    # Có matches
                        base_queryset = base_queryset.filter(id__in=list(all_matching_ids))
                    else:                   # Không có matches → return empty 
                        base_queryset = base_queryset.filter(id__in=[])
        
        else:
            # Fallback cho database khác PostgreSQL
            for measurement_type, value in measurement_filters.items():
                measurement_config = entity.MEASUREMENT_TYPES.get(measurement_type, {})
                default_unit = measurement_config.get('default_unit')
                data_type = measurement_config.get('type')
                context_key = measurement_type
                if default_unit:
                    context_key = f"{measurement_type}|{default_unit}"
                
                standard_unit = STANDARD_INTERNATIONAL_UNITS.get(measurement_type) or default_unit or ''
                user_units = []
                if standard_unit:
                    user_units.append(standard_unit)
                if default_unit and default_unit not in user_units:
                    user_units.append(default_unit)
                
                if isinstance(user_unit, dict):
                    user_units += [u for u in user_unit.get('default', {}).values() if u]
                
                # 🚀 PERFORMANCE: Use pre-compiled regex patterns
                all_numbers = _NUMBER_PATTERN.findall(value)
                unit_candidates = _UNIT_PATTERN.findall(value)
                unit = unit_candidates[-1] if unit_candidates else ''
                
                # 🚀 FIX: Check if unit is a partial/prefix of standard_unit (e.g., 'k' → 'km')
                partial_unit_match = False
                if unit and standard_unit:
                    unit_lower = unit.lower()
                    std_lower = standard_unit.lower()
                    if std_lower.startswith(unit_lower) and len(unit_lower) < len(std_lower):
                        partial_unit_match = True
                        unit = standard_unit
                
                standardized_unit = standardize_unit(unit, context_key) if unit else ''
                target_standard_unit = standardize_unit(standard_unit, context_key) if standard_unit else ''
                valid_unit = any(
                    u for u in user_units
                    if u and standardize_unit(u, context_key) == standardized_unit
                ) or partial_unit_match
                unit_terms = set()
                
                q = Q(content_type=content_type, measurement_type=measurement_type)
                
                if all_numbers:
                    try:
                        numbers = []
                        for num in all_numbers:
                            try:
                                numbers.append(float(num))
                            except ValueError:
                                pass
                        if not numbers:
                            raise ValueError("No numeric values parsed")
                        
                        # 🚀 FIX: Only convert when valid_unit=True
                        original_numbers = numbers.copy()
                        if (
                            valid_unit
                            and unit
                            and standard_unit
                            and standardized_unit
                            and target_standard_unit
                            and standardized_unit != target_standard_unit
                        ):
                            try:
                                converted_numbers = []
                                for num in numbers:
                                    converted = convert_unit(num, unit, standard_unit, measurement_type)
                                    if isinstance(converted, (int, float)):
                                        converted_numbers.append(converted)
                                    else:
                                        raise ValueError(f"Invalid conversion result: {converted}")
                                numbers = converted_numbers
                                unit = standard_unit
                                standardized_unit = target_standard_unit
                            except (ValueError, TypeError) as conv_err:
                                logger.debug(f"[MEASURE_FILTER] ORM Conversion failed ({unit}→{standard_unit}): {conv_err}")
                                numbers = original_numbers
                        
                        if len(numbers) == 2:
                            min_val, max_val = min(numbers), max(numbers)
                            q &= (
                                (Q(data__type='range') & 
                                Q(data__min__gte=min_val) & 
                                Q(data__max__lte=max_val)) |
                                (Q(data__type='dimensions') & 
                                Q(data__length__gte=min_val) & 
                                Q(data__width__lte=max_val)) |
                                (Q(data__type='resolution') & 
                                Q(data__width__gte=min_val) & 
                                Q(data__height__lte=max_val)) |
                                (Q(data__type='multi_value') & 
                                Q(data__values__icontains=str(min_val)) & 
                                Q(data__values__icontains=str(max_val)))
                            )
                        else:
                            number_value = numbers[0]
                            if isinstance(number_value, (int, float)):
                                if float(number_value).is_integer():
                                    number_str = str(int(number_value))
                                else:
                                    number_str = format(number_value, 'f').rstrip('0').rstrip('.')
                                    if not number_str:
                                        number_str = str(number_value)
                            else:
                                number_str = str(number_value)

                            number_condition = Q(data__icontains=number_str)

                            if data_type == 'simple' and isinstance(number_value, (int, float)):
                                numeric_condition = Q()
                                numeric_values = [float(number_value)]
                                if float(number_value).is_integer():
                                    numeric_values.append(int(number_value))
                                for numeric_value in numeric_values:
                                    numeric_condition |= Q(data__value=numeric_value)
                                number_condition = number_condition | numeric_condition

                            q &= number_condition
                    
                    except Exception as e:
                        number_conditions = Q()
                        for num in all_numbers:
                            number_conditions |= Q(data__icontains=num)
                        q &= number_conditions
                
                if unit and valid_unit:
                    ambiguous_unit_terms = {'m'}

                    def add_unit_term(term):
                        if not term:
                            return
                        normalized = term.strip()
                        if not normalized:
                            return
                        if normalized.lower() in ambiguous_unit_terms:
                            return
                        unit_terms.add(normalized)

                    add_unit_term(unit)
                    add_unit_term(standardized_unit)
                    add_unit_term(default_unit)

                    if (standardized_unit and standardized_unit.lower() == 'min') or (
                        default_unit and standardize_unit(default_unit, context_key) == 'min'
                    ):
                        unit_terms.update({'min', 'mins', 'minute', 'minutes'})

                    if unit_terms:
                        unit_conditions = Q()
                        for term in unit_terms:
                            unit_conditions |= Q(data__icontains=term)
                        q &= unit_conditions
                
                # 🚀 FIX: Search in specific fields, EXCLUDE "type" field from search
                if not all_numbers and not valid_unit:
                    # Check if search value is meaningful (not just single letter like 'p')
                    if len(value.strip()) >= 2 or value.strip().isdigit():
                        # Search only in meaningful fields, EXCLUDE "type" field
                        field_conditions = Q(
                            Q(data__unit__icontains=value) |           # unit field
                            Q(data__name__icontains=value) |           # name field
                            Q(data__value__icontains=value) |          # value field
                            Q(data__width__icontains=value) |          # resolution width
                            Q(data__height__icontains=value) |         # resolution height
                            Q(data__min__icontains=value) |            # range min
                            Q(data__max__icontains=value)              # range max
                        )
                        q &= field_conditions
                    # If value is too short/meaningless, create impossible condition (will return empty)
                    else:
                        q &= Q(id__in=[])
                
                logger.debug(
                    "[MEASURE_FILTER][ORM] type=%s value=%s numbers=%s unit=%s std_unit=%s default_unit=%s unit_terms=%s",
                    measurement_type,
                    value,
                    all_numbers,
                    unit,
                    standardized_unit,
                    default_unit,
                    sorted(unit_terms)
                )
                filtered_ids = Measurement.objects.filter(q).values_list('object_id', flat=True)
                base_queryset = base_queryset.filter(id__in=filtered_ids)
    
    
    return base_queryset

def convert_measurement_data_to_user_units(measurement, user_units=None, model_class=None):
    """
    Converts the numeric values in the measurement data from base unit (MEASUREMENT_TYPES)
    to user's preferred display units but keeps the original data structure intact.
    
    Args:
        measurement: The Measurement object
        user_units: Dictionary of user's unit preferences
        model_class: Model class to avoid N+1 query for measurement.entity
        
    Returns:
        Dict with the same structure as measurement.data but with converted values
    """
    # 🚀 PERFORMANCE: Use cached AdminConfig instead of querying every time
    if not user_units:
        config = get_cached_admin_config()
        if config:
            user_units = config.get('unit_preferences', {})
        else:
            user_units = {}
    
    # Get entity model name for context-specific units
    # 🚀 PERFORMANCE: Use model_class if provided to avoid measurement.entity query
    # Also check for cached entity to avoid N+1 queries
    model_name = None
    if model_class:
        model_name = model_class.__name__
    elif hasattr(measurement, '_cached_entity') and measurement._cached_entity:
        # Use cached entity to avoid N+1 query
        model_name = measurement._cached_entity.__class__.__name__
    elif hasattr(measurement, 'entity') and measurement.entity:
        model_name = measurement.entity.__class__.__name__
    
    # Determine target unit based on hierarchical preferences
    target_unit = None
    measurement_type = measurement.measurement_type
    
    # Check if we have a hierarchical structure
    if isinstance(user_units, dict) and model_name in user_units and isinstance(user_units[model_name], dict):
        # First try model-specific preference
        target_unit = user_units.get(model_name, {}).get(measurement_type)
    
    # If not found and we have a default section, try that
    if not target_unit and isinstance(user_units, dict) and 'default' in user_units:
        target_unit = user_units.get('default', {}).get(measurement_type)
    
    # For backward compatibility, check flat structure
    if not target_unit and isinstance(user_units, dict):
        target_unit = user_units.get(measurement_type)
    
    # If no preference found for this measurement type, return original data
    if not target_unit:
        return measurement.data
    
    # Create a deep copy of the data to avoid modifying the original
    data = copy.deepcopy(measurement.data)
    data_type = data.get('type')
    
    # Handle special case for 'original' unit preference - use input_unit
    if target_unit == 'original' and 'input_unit' in data:
        target_unit = data['input_unit']
    
    # No conversion needed if target unit matches current unit
    if data_type == 'simple' and target_unit == data.get('unit'):
        return data
    elif data_type == 'range' and target_unit == data.get('unit'):
        return data
    elif data_type == 'up_to' and target_unit == data.get('unit'):
        return data
    
    # Convert values based on data type
    if data_type == 'simple':
        current_unit = data.get('unit')
        if current_unit and target_unit and current_unit != target_unit:
            try:
                data['value'] = convert_unit(data['value'], current_unit, target_unit, measurement_type)
                data['unit'] = target_unit
            except Exception:
                pass  # Keep original if conversion fails
    
    elif data_type == 'range':
        current_unit = data.get('unit')
        if current_unit and target_unit and current_unit != target_unit:
            try:
                data['min'] = convert_unit(data['min'], current_unit, target_unit, measurement_type)
                data['max'] = convert_unit(data['max'], current_unit, target_unit, measurement_type)
                data['unit'] = target_unit
            except Exception:
                pass
    
    elif data_type == 'up_to':
        current_unit = data.get('unit')
        if current_unit and target_unit and current_unit != target_unit:
            try:
                data['max'] = convert_unit(data['max'], current_unit, target_unit, measurement_type)
                data['unit'] = target_unit
            except Exception:
                pass
    
    elif data_type == 'dimensions':
        current_unit = data.get('unit')
        if current_unit and target_unit and current_unit != target_unit:
            try:
                data['length'] = convert_unit(data['length'], current_unit, target_unit, 'length')
                data['width'] = convert_unit(data['width'], current_unit, target_unit, 'length')
                if 'height' in data:
                    data['height'] = convert_unit(data['height'], current_unit, target_unit, 'length')
                data['unit'] = target_unit
            except Exception:
                pass
    
    elif data_type == 'multi_value':
        current_unit = data.get('unit')
        if current_unit and target_unit and current_unit != target_unit:
            try:
                data['values'] = [convert_unit(value, current_unit, target_unit, measurement_type) for value in data['values']]
                data['unit'] = target_unit
            except Exception:
                pass
    
    elif data_type == 'dimensions_weight':
        dim_unit = data.get('dimension_unit')
        weight_unit = data.get('weight_unit')
        
        # Get target units for dimensions and weight
        target_dim_unit = None
        target_weight_unit = None
        
        # Try to get dimension unit preference
        if model_name and 'dimensions' in (user_units.get(model_name, {})):
            target_dim_unit = user_units[model_name]['dimensions']
        elif 'default' in user_units and 'dimensions' in user_units['default']:
            target_dim_unit = user_units['default']['dimensions']
        elif 'dimensions' in user_units:
            target_dim_unit = user_units['dimensions']
            
        # Try to get weight unit preference
        if model_name and 'weight' in (user_units.get(model_name, {})):
            target_weight_unit = user_units[model_name]['weight']
        elif 'default' in user_units and 'weight' in user_units['default']:
            target_weight_unit = user_units['default']['weight']
        elif 'weight' in user_units:
            target_weight_unit = user_units['weight']
        
        # Handle original unit preference
        if target_dim_unit == 'original' and 'original_dimension_unit' in data:
            target_dim_unit = data['original_dimension_unit']
        if target_weight_unit == 'original' and 'original_weight_unit' in data:
            target_weight_unit = data['original_weight_unit']
            
        # Convert dimensions if needed
        if dim_unit and target_dim_unit and dim_unit != target_dim_unit:
            try:
                data['length'] = convert_unit(data['length'], dim_unit, target_dim_unit)
                data['width'] = convert_unit(data['width'], dim_unit, target_dim_unit)
                data['height'] = convert_unit(data['height'], dim_unit, target_dim_unit)
                data['dimension_unit'] = target_dim_unit
            except Exception:
                pass
        
        # Convert weight if needed
        if weight_unit and target_weight_unit and weight_unit != target_weight_unit:
            try:
                data['weight'] = convert_unit(data['weight'], weight_unit, target_weight_unit)
                data['weight_unit'] = target_weight_unit
            except Exception:
                pass
    
    # Return the converted data
    return data

def create_hierarchical_unit_preferences(defaults=None, model_preferences=None):
    """
    Creates a well-structured hierarchical unit preferences object.
    
    Args:
        defaults (dict): Default units for measurement types
        model_preferences (dict): Model-specific unit preferences
    
    Returns:
        dict: A properly structured unit preferences object
        
    Example:
        preferences = create_hierarchical_unit_preferences(
            defaults={
                'weight': 'kg',
                'dimensions': 'mm',
                'temperature': '°C'
            },
            model_preferences={
                'CameraType': {
                    'weight': 'g',
                    'resolution': 'px'
                },
                'PackagingSpecification': {
                    'weight': 'kg',
                    'dimensions': 'cm'
                }
            }
        )
    """
    result = {}
    
    # Add defaults
    if defaults:
        result['default'] = defaults
    
    # Add model-specific preferences
    if model_preferences:
        for model_name, preferences in model_preferences.items():
            result[model_name] = preferences
    
    return result

def get_unit_preference(user_units, measurement_type, model_name=None):
    """
    Gets the appropriate unit preference for a measurement type, considering 
    model-specific overrides.
    
    Args:
        user_units (dict): User unit preferences
        measurement_type (str): The type of measurement
        model_name (str, optional): The model class name
    
    Returns:
        str: The preferred unit or None if not found
    """
    target_unit = None
    
    # Check if we have a hierarchical structure
    if isinstance(user_units, dict):
        # First try model-specific preference if model_name is provided
        if model_name and model_name in user_units and isinstance(user_units[model_name], dict):
            target_unit = user_units[model_name].get(measurement_type)
        
        # If not found and we have a default section, try that
        if not target_unit and 'default' in user_units:
            target_unit = user_units['default'].get(measurement_type)
        
        # For backward compatibility, check flat structure
        if not target_unit:
            target_unit = user_units.get(measurement_type)
    
    return target_unit

def validate_unit_preferences(unit_preferences):
    """
    Validates the structure of unit preferences to ensure it follows the expected format.
    
    Args:
        unit_preferences (dict): The unit preferences to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(unit_preferences, dict):
        return False, "Unit preferences must be a dictionary"
    
    # Check if using hierarchical format
    if 'default' in unit_preferences:
        if not isinstance(unit_preferences['default'], dict):
            return False, "'default' section must be a dictionary"
        
        # Validate all model sections
        for key, value in unit_preferences.items():
            if not isinstance(value, dict):
                return False, f"Section '{key}' must be a dictionary"
    
    # If flat structure, all values should be strings
    else:
        for key, value in unit_preferences.items():
            if not isinstance(value, str) and not isinstance(value, dict):
                return False, f"Value for '{key}' must be a string or dictionary"
    
    return True, "Valid unit preferences"

def migrate_to_hierarchical_preferences(flat_preferences):
    """
    Migrates a flat unit preferences structure to the hierarchical format.
    
    Args:
        flat_preferences (dict): Old flat structure of unit preferences
    
    Returns:
        dict: New hierarchical structure with all preferences in the 'default' section
    """
    return {'default': flat_preferences.copy()} if flat_preferences else {'default': {}}

def sort_terminal_by_location(terminals, city_province, city_county_district, ward_town_township, street_address):
    """
    Sorts terminals by geographic distance from the provided address.
    Returns original terminals list if geocoding fails or times out.
    """
    try:
        # 1. Geocode the address to get coordinates with timeout
        geolocator = Nominatim(user_agent="guardianx_terminal_locator", timeout=5)
        full_address = f"0, {ward_town_township if ward_town_township else ''}, {city_county_district if city_county_district else ''}, {city_province if city_province else ''}"
        location = geolocator.geocode(full_address)
        
        if not location:
            print(f"Address not found: {full_address}")
            return terminals  # Return original order if address not found

        user_coords = (location.latitude, location.longitude)
        
        def is_valid_coordinate(lat, lng):
            """Check if coordinates are valid for geopy distance calculation"""
            try:
                # Check if values exist and are not None
                if lat is None or lng is None:
                    return False
                
                # Convert to float if they're strings
                lat = float(lat)
                lng = float(lng)
                
                # Check if latitude is in valid range [-90, 90]
                if lat < -90 or lat > 90:
                    return False
                    
                # Check if longitude is in valid range [-180, 180]
                if lng < -180 or lng > 180:
                    return False
                    
                return True
            except (ValueError, TypeError):
                return False
        
        # 2. Annotate each terminal with distance
        def terminal_with_distance(terminal):
            # Validate coordinates before using them
            if not is_valid_coordinate(terminal.latitude, terminal.longitude):
                return (float('inf'), terminal)
                
            terminal_coords = (float(terminal.latitude), float(terminal.longitude))
            try:
                dist = geopy_distance(user_coords, terminal_coords).km
                return (dist, terminal)
            except Exception as e:
                # If distance calculation fails for any reason, put terminal at the end
                print(f"Error calculating distance for terminal {getattr(terminal, 'id', 'unknown')}: {e}")
                return (float('inf'), terminal)

        # 3. Sort terminals by computed distance
        sorted_terminals = sorted(terminals, key=lambda t: terminal_with_distance(t)[0])
        
        return sorted_terminals
    except Exception as e:
        print(f"Unexpected error during geocoding for address '{full_address}': {e}")
        return terminals  # Return original order on any other error

def sort_terminal_by_address(terminals, address):
    """
    Sorts terminals by geographic distance from the provided address.
    Returns original terminals list if geocoding fails or times out.
    """
    try:
        # 1. Geocode the address to get coordinates with timeout
        geolocator = Nominatim(user_agent="guardianx_terminal_locator", timeout=5)
        location = geolocator.geocode(address)

        if not location:
            print(f"Address not found: {address}")
            return terminals  # Return original order if address not found

        user_coords = (location.latitude, location.longitude)

        # 2. Annotate each terminal with distance
        def terminal_with_distance(terminal):
            try:
                # Validate coordinates
                if terminal.latitude is None or terminal.longitude is None:
                    return (float('inf'), terminal)
                    
                terminal_coords = (float(terminal.latitude), float(terminal.longitude))
                dist = geopy_distance(user_coords, terminal_coords).km
                return (dist, terminal)
            except Exception as e:
                print(f"Error calculating distance for terminal {getattr(terminal, 'id', 'unknown')}: {e}")
                return (float('inf'), terminal)

        # 3. Sort terminals by computed distance
        sorted_terminals = sorted(terminals, key=lambda t: terminal_with_distance(t)[0])
        return sorted_terminals
    
    except Exception as e:
        print(f"Unexpected error during geocoding for address '{address}': {e}")
        return terminals  # Return original order on any other error


# =============================================================================
# 🔗 SIGNAL HANDLERS - Integration with universal_optimization.py
# =============================================================================

def _on_admin_config_change(sender, instance, **kwargs):
    """
    Signal handler to invalidate measurement caches when AdminConfig changes.
    Integrated with universal_optimization.py cache invalidation system.
    """
    try:
        # Only invalidate if Unit Config changed
        if hasattr(instance, 'name') and instance.name == 'Unit Config':
            invalidate_measurement_caches()
            logger.info("🔄 [MEASUREMENT_SIGNAL] Unit Config changed - caches invalidated")
    except Exception as e:
        logger.warning(f"⚠️ [MEASUREMENT_SIGNAL] Error handling AdminConfig change: {e}")

# Register signal handler for AdminConfig changes
try:
    from django.db.models.signals import post_save, post_delete
    from core.configuration.models import AdminConfig
    
    post_save.connect(_on_admin_config_change, sender=AdminConfig, dispatch_uid="measurement_admin_config_save")
    post_delete.connect(_on_admin_config_change, sender=AdminConfig, dispatch_uid="measurement_admin_config_delete")
    
    logger.debug("✅ [MEASUREMENT_SIGNAL] AdminConfig signal handlers registered")
except ImportError:
    # AdminConfig model not available yet (during migrations)
    pass
except Exception as e:
    logger.warning(f"⚠️ [MEASUREMENT_SIGNAL] Could not register signal handlers: {e}")
