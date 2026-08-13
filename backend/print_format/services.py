import math
from pickle import TRUE
from typing import Any, Dict, List

from devices.services.flight_estimation_service import FlightEstimationService
from common.utils import decode_template_html_entities
from django.db import models
from django.apps import apps
from django.contrib.contenttypes.models import ContentType

from delivery.models import DeliveryOperationApproval, DeliveryOperationApprovalChecklist, DeliveryOperationItem
from devices.models import Device
from print_format.schemas import PrintFormatSchema
from .models import PrintFormat
from report_template.models import ReportTemplate
from django.db import transaction
from core.configuration.models import AdminConfig
import qrcode
import base64
from io import BytesIO
from decimal import Decimal
from datetime import datetime, date, time
from django.utils import timezone
from uuid import UUID
import os
from core.base import BaseResponse
from common.constant import MESSAGE_ENUM
from django.core.cache import cache
from delivery.services.weather_service import WeatherService
from delivery.services.map_service import MapService
from common.pagination import OptimizedPaginator
from django.db.models import Q
from core.common.search.dynamic_search import apply_dynamic_filters
from core.common.schema_utils import DynamicSchema
from core.middleware.refresh_token import get_current_request
import pytz
from core.user.models import UserSettings, CoreUser

HOST = os.getenv('HOST','http://localhost:8000')
class PrintFormatService:
    # Danh sách các field nhạy cảm cần loại trừ
    
    @staticmethod
    def _get_drone_battery_levels(drone_queryset):
        """Lấy battery levels từ drone queryset"""
        if not drone_queryset:
            return []
        
        from devices.models import Measurement, Device
        from django.contrib.contenttypes.models import ContentType
        
        battery_levels = []
        for drone in drone_queryset:
            # Lấy cargo compartments của drone
            cargo_compartments = drone.cargo_compartments.all()
            for compartment in cargo_compartments:
                # Lấy measurement battery_capacity
                measurement = compartment.measurements.filter(
                    measurement_type='battery_capacity'
                ).first()
                if measurement and measurement.data.get('value'):
                    battery_levels.append(measurement.data.get('value'))
        return battery_levels

    @staticmethod
    def _get_drone_wind_resistance(drone_queryset):
        """Lấy wind resistance từ drone queryset"""
        try:
            if not drone_queryset:
                return []
            
            from devices.models import Measurement, Device
            from django.contrib.contenttypes.models import ContentType
            
            wind_resistance_ms = []
            for drone in drone_queryset:
                if drone.flight_performance and drone.flight_performance.measurements.filter(measurement_type='wind_resistance').exists():
                    wind_resistance_ms.append(drone.flight_performance.measurements.filter(measurement_type='wind_resistance').first().get_formatted_value())
                elif drone.library.flight_performance and drone.library.flight_performance.measurements.filter(measurement_type='wind_resistance').exists():
                    wind_resistance_ms.append(drone.library.flight_performance.measurements.filter(measurement_type='wind_resistance').first().get_formatted_value())
            return wind_resistance_ms
        except Exception as e:
            return []

    @staticmethod
    def _get_drone_flight_time(drone_queryset):
        """Lấy flight time từ drone queryset"""
        try:
            if not drone_queryset:
                return []
            
            from devices.models import Measurement, Device
            from django.contrib.contenttypes.models import ContentType
            
            flight_times = []
            for drone in drone_queryset:
                if drone.propulsion_system:
                    propulsion_system = drone.propulsion_system
                    if propulsion_system.get_measurement('flight_time'):
                        flight_times.append(propulsion_system.get_measurement('flight_time').get_numeric_value())
                elif drone.library and drone.library.propulsion_system:
                    propulsion_system = drone.library.propulsion_system
                    if propulsion_system.get_measurement('flight_time'):
                        flight_times.append(propulsion_system.get_measurement('flight_time').get_numeric_value())
            print('flight_times', flight_times)
            return flight_times
        except Exception as e:
            return []

    @staticmethod
    def _get_drone_manufacturer_name(drone_queryset):
        try:
            """Lấy manufacturer name từ drone queryset"""
            if not drone_queryset:
                return []
        
            manufacturer_names = []
            for drone in drone_queryset:
                if drone.manufacturer_information:
                    manufacturer_information = drone.manufacturer_information
                    print('manufacturer_information manufacturer', manufacturer_information.manufacturer)
                    if manufacturer_information.manufacturer:
                        manufacturer_names.append(manufacturer_information.manufacturer)
            print('manufacturer_names', manufacturer_names)
            return manufacturer_names
        except Exception as e:
            return []

    @staticmethod
    def _get_drone_registration_number(drone_queryset):
        try:
            """Lấy registration number từ drone queryset"""
            if not drone_queryset:
                return []
        
            registration_numbers = []
            for drone in drone_queryset:
                if drone.manufacturer_information:
                    manufacturer_information = drone.manufacturer_information
                    print('manufacturer_information registration_number', manufacturer_information.registration_number)
                    if manufacturer_information.registration_number:    
                        registration_numbers.append(manufacturer_information.registration_number)
            print('registration_numbers', registration_numbers)
            return registration_numbers
        except Exception as e:
            return []
    
    @staticmethod
    def _get_drone_weight(drone_queryset):
        """Lấy weight từ drone queryset"""
        try:
            if not drone_queryset:
                return []
            
            wind_resistance_ms = []
            for drone in drone_queryset:
                if drone.dimensions_and_weight and drone.dimensions_and_weight.measurements.filter(measurement_type='empty_weight').exists():
                    wind_resistance_ms.append(drone.dimensions_and_weight.measurements.filter(measurement_type='empty_weight').first().get_formatted_value())
                elif drone.library and drone.library.dimensions_and_weight:
                    wind_resistance_ms.append(drone.library.dimensions_and_weight.measurements.filter(measurement_type='empty_weight').first().get_formatted_value())
            return wind_resistance_ms
        except Exception as e:
            return []

    @staticmethod
    def _get_drone_weight_capacity(drone_queryset):
        try:
            """Lấy weight từ drone queryset"""
            if not drone_queryset:
                return []
            
            from devices.models import Measurement, Device
            from django.contrib.contenttypes.models import ContentType
            
            weight_capacities = []
            for drone in drone_queryset:
                # Lấy cargo compartments của drone
                cargo_compartments = drone.cargo_compartments.all()
                for compartment in cargo_compartments:
                    # Lấy measurement wind_resistance
                    measurement = compartment.measurements.filter(
                        measurement_type='weight_capacity'
                    ).first()
                    if measurement and measurement.data.get('value'):
                        weight_capacities.append(measurement.data.get('value'))
            return weight_capacities
        except Exception as e:
            return []

    @staticmethod
    def _get_drone_temperature(drone_queryset):
        """Lấy weight từ drone queryset"""
        try:
            if not drone_queryset:
                return []
            
            from devices.models import Measurement, Device
            from django.contrib.contenttypes.models import ContentType
            
            temperatures = []
            for drone in drone_queryset:
                # Lấy cargo compartments của drone
                if drone.environmental_specification and drone.environmental_specification.measurements.filter(measurement_type='temperature_range').exists():
                    temperatures.append(drone.environmental_specification.measurements.filter(measurement_type='temperature_range').first().get_formatted_value())
                elif drone.library and drone.library.environmental_specification and drone.library.environmental_specification.measurements.filter(measurement_type='temperature_range').exists():
                    temperatures.append(drone.library.environmental_specification.measurements.filter(measurement_type='temperature_range').first().get_formatted_value())
            return temperatures
        except Exception as e:
            return []

    @staticmethod
    def _get_drone_data_from_queryset(drone_queryset):
        """Lấy drone data từ queryset an toàn"""
        if not drone_queryset or not drone_queryset.exists():
            return {
                'drone__id': '',
                'drone__name': '',
                'drone__serial_number': '',
                'drone__model': '',
                'drone__status': '',
                'drone__battery_level': '',
                'drone__weight': '',
                'drone__weight_capacity': '',
                'drone__temperature': '',
                'drone__wind_resistance': '',
                'drone__flight_time': '',
                'drone__manufacturer_name': '',
                'drone__registration_number': ''
            }
        
        try:
            # Lấy data dưới dạng list trước
            ids = list(drone_queryset.values_list('id', flat=True))
            names = list(drone_queryset.values_list('name', flat=True))
            serial_numbers = list(drone_queryset.values_list('serial_number', flat=True))
            models = list(drone_queryset.values_list('manufacturer_information__model_number', flat=True))
            statuses = list(drone_queryset.values_list('status__name', flat=True))
            battery_levels = PrintFormatService._get_drone_battery_levels(drone_queryset)
            wind_resistances = PrintFormatService._get_drone_wind_resistance(drone_queryset)
            flight_times = PrintFormatService._get_drone_flight_time(drone_queryset)
            weights = PrintFormatService._get_drone_weight(drone_queryset)
            weight_capacities = PrintFormatService._get_drone_weight_capacity(drone_queryset)
            drone__temperature = PrintFormatService._get_drone_temperature(drone_queryset)
            manufacturer_names = PrintFormatService._get_drone_manufacturer_name(drone_queryset)
            registration_numbers = PrintFormatService._get_drone_registration_number(drone_queryset)
            city_provinces = list(drone_queryset.values_list('terminal__city_province', flat=True))
            # Chuyển thành chuỗi với dấu phẩy
            return {
                'drone__id': ', '.join(str(x) for x in ids if x is not None),
                'drone__name': ', '.join(str(x) for x in names if x is not None),
                'drone__serial_number': ', '.join(str(x) for x in serial_numbers if x is not None),
                'drone__model': ', '.join(str(x) for x in models if x is not None),
                'drone__status': ', '.join(str(x) for x in statuses if x is not None),
                'drone__battery_level': ', '.join(str(x) for x in battery_levels if x is not None),
                'drone__wind_resistance': ', '.join(str(x) for x in wind_resistances if x is not None),
                'drone__flight_time': ', '.join(str(x) for x in flight_times if x is not None),
                'drone__weight': ', '.join(str(x) for x in weights if x is not None),
                'drone__weight_capacity': ', '.join(str(x) for x in weight_capacities if x is not None),
                'drone__temperature': ', '.join(str(x) for x in drone__temperature if x is not None),
                'drone__manufacturer_name': ', '.join(str(x) for x in manufacturer_names if x is not None),
                'drone__registration_number': ', '.join(str(x) for x in registration_numbers if x is not None),
                'drone__city_province': ', '.join(str(x) for x in city_provinces if x is not None)
            }
        except Exception:
            # Fallback data nếu có lỗi
            ids = list(drone_queryset.values_list('id', flat=True))
            names = list(drone_queryset.values_list('name', flat=True))
            serial_numbers = list(drone_queryset.values_list('serial_number', flat=True))
            statuses = list(drone_queryset.values_list('status__name', flat=True))
            battery_levels = PrintFormatService._get_drone_battery_levels(drone_queryset)
            wind_resistances = PrintFormatService._get_drone_wind_resistance(drone_queryset)
            flight_times = PrintFormatService._get_drone_flight_time(drone_queryset)
            weights = PrintFormatService._get_drone_weight(drone_queryset)
            weight_capacities = PrintFormatService._get_drone_weight_capacity(drone_queryset)
            temperatures = PrintFormatService._get_drone_temperature(drone_queryset)
            manufacturer_names = PrintFormatService._get_drone_manufacturer_name(drone_queryset)
            registration_numbers = PrintFormatService._get_drone_registration_number(drone_queryset)
            city_provinces = list(drone_queryset.values_list('terminal__city_province', flat=True))
            return {
                'drone__id': ', '.join(str(x) for x in ids if x is not None),
                'drone__name': ', '.join(str(x) for x in names if x is not None),
                'drone__serial_number': ', '.join(str(x) for x in serial_numbers if x is not None),
                'drone__model': '',
                'drone__status': ', '.join(str(x) for x in statuses if x is not None),
                'drone__battery_level': ', '.join(str(x) for x in battery_levels if x is not None),
                'drone__wind_resistance': ', '.join(str(x) for x in wind_resistances if x is not None),
                'drone__flight_time': ', '.join(str(x) for x in flight_times if x is not None),
                'drone__weight': ', '.join(str(x) for x in weights if x is not None),
                'drone__weight_capacity': ', '.join(str(x) for x in weight_capacities if x is not None),
                'drone__temperature': ', '.join(str(x) for x in temperatures if x is not None),
                'drone__manufacturer_name': ', '.join(str(x) for x in manufacturer_names if x is not None),
                'drone__registration_number': ', '.join(str(x) for x in registration_numbers if x is not None),
                'drone__city_province': ', '.join(str(x) for x in city_provinces if x is not None)
            }

    @staticmethod
    def _get_drone_data_from_single_object(drone_obj):
        """Lấy drone data từ single object an toàn"""
        if not drone_obj:
            return {
                'drone__id': '',
                'drone__name': '',
                'drone__serial_number': '',
                'drone__model': '',
                'drone__status': '',
                'drone__battery_level': '',
                'drone__wind_resistance': '',
                'drone__flight_time': '',
                'drone__weight': '',
                'drone__weight_capacity': '',
                'drone__temperature': '',
                'drone__manufacturer_name': ''
            }
        
        from devices.models import Device
        
        # Tạo queryset từ single object để tái sử dụng logic
        single_drone_qs = Device._base_manager.filter(id=drone_obj.id)
        return PrintFormatService._get_drone_data_from_queryset(single_drone_qs)
    SENSITIVE_FIELDS = {
        'password', 'password_hash', 'password_salt', 'secret_key', 'api_key','changed_by',
        'modified_on', 'modified_by',
        'token', 'access_token', 'refresh_token', 'auth_token',
        'deleted', 'is_deleted', 'deleted_at', 'deleted_by','deleted_by_cascade',
        'updated_by', 'created_at', 'updated_at',
        'last_login', 'last_logout', 'last_activity',
        'ip_address', 'mac_address', 'device_id',
        'session_key', 'session_data',
        'private_key', 'public_key', 'encryption_key',
        'security_question', 'security_answer',
        'otp_secret', 'otp_code',
        'backup_codes', 'recovery_codes',
        'verification_code', 'verification_token',
        'reset_token', 'reset_code',
        'activation_code', 'activation_token',
        'remember_token', 'remember_me',
        'auth_code', 'auth_secret',
        'signature', 'signature_key',
        'hash', 'hash_key',
        'salt', 'salt_key',
        'nonce', 'nonce_key',
        'iv', 'iv_key',
        'key', 'key_id',
        'secret', 'secret_id',
        'credential', 'credential_id',
        'certificate', 'certificate_id',
        'license', 'license_key',
        'subscription', 'subscription_key',
        'api_secret', 'api_id',
        'client_secret', 'client_id',
        'consumer_secret', 'consumer_key',
        'access_secret', 'access_id',
        'refresh_secret', 'refresh_id',
        'bearer_token', 'bearer_id',
        'jwt_token', 'jwt_id',
        'oauth_token', 'oauth_id',
        'saml_token', 'saml_id',
        'ldap_password', 'ldap_id',
        'kerberos_ticket', 'kerberos_id',
        'radius_secret', 'radius_id',
        'tacacs_secret', 'tacacs_id',
        'vpn_secret', 'vpn_id',
        'ssh_key', 'ssh_id',
        'pgp_key', 'pgp_id',
        'gpg_key', 'gpg_id',
        'ssl_key', 'ssl_id',
        'tls_key', 'tls_id',
        'crypto_key', 'crypto_id',
        'encryption_key', 'encryption_id',
        'decryption_key', 'decryption_id',
        'signing_key', 'signing_id',
        'verification_key', 'verification_id',
        'authentication_key', 'authentication_id',
        'authorization_key', 'authorization_id',
        'session_key', 'session_id',
        'cookie_key', 'cookie_id',
        'csrf_token', 'csrf_id',
        'xss_token', 'xss_id',
        'sql_injection_token', 'sql_injection_id',
        'command_injection_token', 'command_injection_id',
        'file_upload_token', 'file_upload_id',
        'path_traversal_token', 'path_traversal_id',
        'xml_external_entity_token', 'xml_external_entity_id',
        'server_side_inclusion_token', 'server_side_inclusion_id',
        'remote_code_execution_token', 'remote_code_execution_id',
        'buffer_overflow_token', 'buffer_overflow_id',
        'integer_overflow_token', 'integer_overflow_id',
        'format_string_token', 'format_string_id',
        'race_condition_token', 'race_condition_id',
        'time_of_check_time_of_use_token', 'time_of_check_time_of_use_id',
        'use_after_free_token', 'use_after_free_id',
        'double_free_token', 'double_free_id',
        'heap_overflow_token', 'heap_overflow_id',
        'stack_overflow_token', 'stack_overflow_id',
        'null_pointer_dereference_token', 'null_pointer_dereference_id',
        'dangling_pointer_token', 'dangling_pointer_id',
        'memory_leak_token', 'memory_leak_id',
        'resource_leak_token', 'resource_leak_id',
        'deadlock_token', 'deadlock_id',
        'livelock_token', 'livelock_id',
        'starvation_token', 'starvation_id',
        'denial_of_service_token', 'denial_of_service_id',
        'elevation_of_privilege_token', 'elevation_of_privilege_id',
        'information_disclosure_token', 'information_disclosure_id',
        'spoofing_token', 'spoofing_id',
        'tampering_token', 'tampering_id',
        'repudiation_token', 'repudiation_id',
        'non_repudiation_token', 'non_repudiation_id',
        'cancelled_by', 'created_by_guess'
    }

    @staticmethod
    def _format_datetime_with_user_settings(value, user_settings=None, instance=None):
        """
        Format datetime/date/time using user settings.
        This ensures consistent formatting with user preferences across the application.
        
        Args:
            value: datetime, date, or time object
            user_settings: User settings object (optional)
            instance: Model instance to get user from created_by (optional, takes priority over user_settings)
        
        Returns:
            Formatted string according to user settings, system defaults, or language fallback
        """
        if value is None:
            return None
        
        # Priority 1: Get user from instance.created_by if instance is provided
        user = None
        if instance and hasattr(instance, 'created_by') and instance.created_by:
            user = instance.created_by
            # Try to get user_settings from created_by user
            if user_settings is None:
                try:
                    if hasattr(user, 'user_settings'):
                        user_settings = user.user_settings
                    elif hasattr(user, 'usersettings'):
                        user_settings = user.usersettings
                except Exception:
                    pass
        
        # Priority 2: Get user from user_settings if available
        if user is None and user_settings and hasattr(user_settings, 'user'):
            user = user_settings.user
        
        # If still no user_settings but we have user, try to fetch it
        if user_settings is None and user:
            try:
                user_settings = UserSettings.objects.select_related(
                    'date_format', 'time_format'
                ).filter(user=user).first()
            except Exception:
                pass
        
        # Default formats
        date_format_str = '%Y-%m-%d'
        time_format_str = '%H:%M:%S'
        user_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
        
        # Get user's language for locale-based defaults
        if user and hasattr(user, 'language') and user.language:
            try:
                lang_code = getattr(user.language, 'code', 'en')
                if lang_code == 'ko':
                    date_format_str = '%Y-%m-%d'
                elif lang_code == 'th':
                    date_format_str = '%d/%m/%Y'
            except Exception:
                pass
        
        # Get timezone from user
        if user and hasattr(user, 'timezone') and user.timezone:
            try:
                tz_code = getattr(user.timezone, 'code', None) or getattr(user.timezone, 'name', None)
                if tz_code:
                    user_timezone = pytz.timezone(tz_code)
            except Exception:
                pass
        
        # Get date format and time format from user settings
        if user_settings:
            try:
                if hasattr(user_settings, 'date_format') and user_settings.date_format:
                    if hasattr(user_settings.date_format, 'format_string'):
                        date_format_str = user_settings.date_format.format_string
                
                if hasattr(user_settings, 'time_format') and user_settings.time_format:
                    if hasattr(user_settings.time_format, 'format_string'):
                        time_format_str = user_settings.time_format.format_string
            except Exception:
                pass
        
        # Format the value according to type
        try:
            if isinstance(value, datetime):
                # Convert to user timezone
                if value.tzinfo is None:
                    # If naive, assume it's in UTC
                    value = pytz.UTC.localize(value)
                else:
                    # Convert to UTC first if not already UTC
                    if value.tzinfo != pytz.UTC:
                        value = value.astimezone(pytz.UTC)
                
                # Convert to user timezone
                localized = value.astimezone(user_timezone)
                
                # Format date and time parts
                date_part = localized.date().strftime(date_format_str)
                time_part = localized.time().strftime(time_format_str)
                result = f"{date_part} {time_part}"
                return result
            
            elif isinstance(value, date):
                result = value.strftime(date_format_str)
                return result
            
            elif isinstance(value, time):
                result = value.strftime(time_format_str)
                return result
            
            else:
                return str(value)
        except Exception as e:
            # Fallback to ISO format if any error occurs
            if isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, date):
                return value.isoformat()
            elif isinstance(value, time):
                return value.isoformat()
            return str(value)

    @staticmethod
    def _format_time_by_locale(t: time, language: str = 'en') -> str:
        """Format time according to locale preferences"""
        if t is None:
            return None
        
        # Define format patterns for different locales
        time_formats = {
            'en': '%I:%M:%S %p',  # US format: 12-hour with AM/PM
            'ko': '%H:%M:%S',     # Korean format: 24-hour
        }
        
        format_pattern = time_formats.get(language, time_formats['en'])
        return t.strftime(format_pattern)

    @staticmethod
    def get_relation_label(field: models.Field) -> str:
        """Lấy label cho quan hệ"""
        if hasattr(field, 'verbose_name') and field.verbose_name:
            return field.verbose_name.title().capitalize()
        elif hasattr(field, 'related_name') and field.related_name:
            return field.related_name.replace('_', ' ').title().capitalize()
        elif hasattr(field, 'name'):
            return field.name.replace('_', ' ').title().capitalize()
        return ''

    @staticmethod
    def get_field_example(field_type: str, field_name: str) -> Any:
        """Generate example data based on field type with comprehensive examples"""
        field_name_lower = field_name.lower()
        
        if field_type == 'text':
            if 'name' in field_name_lower:
                if 'status' in field_name_lower:
                    return 'ACTIVE'
                elif 'sender' in field_name_lower:
                    return 'Nguyễn Văn A'
                elif 'recipient' in field_name_lower:
                    return 'Trần Thị B'
                elif 'drone' in field_name_lower:
                    return 'Drone X-15'
                elif 'order' in field_name_lower:
                    return 'ORDER123'
                else:
                    return 'John Doe'
            elif 'phone' in field_name_lower:
                return '+84 123 456 789'
            elif 'email' in field_name_lower:
                return 'example@email.com'
            elif 'code' in field_name_lower:
                if 'order' in field_name_lower:
                    return '00000182'
                elif 'category' in field_name_lower:
                    return 'SAFETY-CHECK'
                else:
                    return 'CODE123'
            elif 'address' in field_name_lower:
                if 'full' in field_name_lower:
                    return '123 Đường ABC, Quận 1, TP.HCM'
                else:
                    return '123 Main Street'
            elif 'note' in field_name_lower:
                return 'Sample note for testing'
            elif 'description' in field_name_lower:
                return 'Sample description for testing purposes'
            elif 'url' in field_name_lower:
                return 'https://example.com'
            elif 'status' in field_name_lower:
                if 'order' in field_name_lower:
                    return 'received'
                elif 'operation' in field_name_lower:
                    return 'completed'
                elif 'drone' in field_name_lower:
                    return 'active'
                else:
                    return 'ACTIVE'
            elif 'city' in field_name_lower:
                if 'sender' in field_name_lower:
                    return 'TP.HCM'
                elif 'recipient' in field_name_lower:
                    return 'Hà Nội'
                else:
                    return 'City Name'
            elif 'district' in field_name_lower:
                if 'sender' in field_name_lower:
                    return 'Quận 1'
                elif 'recipient' in field_name_lower:
                    return 'Quận Ba Đình'
                else:
                    return 'District Name'
            elif 'ward' in field_name_lower:
                if 'sender' in field_name_lower:
                    return 'Phường Bến Nghé'
                elif 'recipient' in field_name_lower:
                    return 'Phường Phúc Xá'
                else:
                    return 'Ward Name'
            else:
                return 'Sample text data'
                
        elif field_type == 'number':
            if 'id' in field_name_lower:
                if 'order' in field_name_lower:
                    return 470
                elif 'operation' in field_name_lower:
                    return 428
                elif 'drone' in field_name_lower:
                    return 15
                else:
                    return 1
            elif 'amount' in field_name_lower:
                if 'total' in field_name_lower:
                    return '₫ 12500.0'
                elif 'subtotal' in field_name_lower:
                    return '₫ 10000.0'
                elif 'delivery_fee' in field_name_lower:
                    return '₫ 2000.0'
                elif 'tax' in field_name_lower:
                    return '₫ 500.0'
                elif 'discount' in field_name_lower:
                    return '₫ 0.0'
                else:
                    return 1000000
            elif 'price' in field_name_lower:
                return 50000
            elif 'quantity' in field_name_lower:
                return 5
            elif 'weight' in field_name_lower:
                return 2.5
            elif 'dimension' in field_name_lower:
                return 10
            elif 'battery' in field_name_lower:
                return 85
            elif 'distance' in field_name_lower:
                return '45.2 km'
            elif 'duration' in field_name_lower:
                return '2h 30m'
            elif 'temperature' in field_name_lower:
                return '25°C'
            elif 'humidity' in field_name_lower:
                return '65%'
            else:
                return 100
                
        elif field_type == 'date':
            if 'created' in field_name_lower:
                return '08-17-2025'
            elif 'modified' in field_name_lower:
                return '08-18-2025'
            elif 'start' in field_name_lower:
                return '08-18-2025'
            elif 'end' in field_name_lower:
                return '08-18-2025'
            else:
                return '2025-08-18'
                
        elif field_type == 'datetime':
            if 'created' in field_name_lower:
                return '08-17-2025 12:28:43'
            elif 'modified' in field_name_lower:
                return '08-18-2025 07:45:40'
            elif 'start' in field_name_lower:
                return '08-18-2025 08:00:00'
            elif 'end' in field_name_lower:
                return '08-18-2025 10:30:00'
            else:
                return '2025-08-18 10:30:00'
                
        elif field_type == 'boolean':
            if 'is_checked' in field_name_lower:
                return True
            elif 'is_active' in field_name_lower:
                return True
            elif 'is_enabled' in field_name_lower:
                return True
            else:
                return True
                
        elif field_type == 'foreign_key':
            if 'drone' in field_name_lower:
                return {
                    'id': 15,
                    'name': 'Drone X-15',
                    'model': 'X-Series',
                    'status': 'active'
                }
            elif 'order' in field_name_lower:
                return {
                    'id': 470,
                    'order_code': '00000182',
                    'status': 'active'
                }
            else:
                return {
                    'id': 1,
                    'name': 'Sample Reference'
                }
                
        elif field_type == 'table':
            if 'checklist' in field_name_lower:
                return [
                    {
                        'item_name': 'Safety Check',
                        'is_checked': True,
                        'category_code': 'SAFETY'
                    },
                    {
                        'item_name': 'Weather Check',
                        'is_checked': False,
                        'category_code': 'WEATHER'
                    }
                ]
            else:
                return []
                
        elif field_type == 'qr_code':
            return f"{HOST}/landing/order/ORDER123"
            
        return None

    @staticmethod
    def get_model_fields(model_name: str) -> List[Dict[str, Any]]:
        """Trả về field tường minh cho Order và các model liên quan (bao gồm khóa ngoại và 1-nhiều, name luôn là ORM)"""
        model = None
        for app_config in apps.get_app_configs():
            try:
                model = apps.get_model(app_config.label, model_name)
                if model:
                    break
            except LookupError:
                continue
        if not model:
            raise LookupError(f"Model {model_name} not found in any app")

        def get_verbose_label(field):
            return field.verbose_name.title() if hasattr(field, 'verbose_name') and field.verbose_name else field.name

        def build_fields_for_model(m, prefix=None, depth=0, max_depth=1):
            """Build fields for model with limited nested relationship support for performance"""
            if depth >= max_depth:
                return []
                
            fields = []
            for field in m._meta.fields:
                # Kiểm tra field có nằm trong danh sách sensitive không
                if field.name.lower() in PrintFormatService.SENSITIVE_FIELDS:
                    continue
                    
                if isinstance(field, models.ForeignKey):
                    rel_model = field.related_model
                    # Chỉ lấy các field quan trọng từ related model
                    important_fields = ['name', 'id', 'code', 'title', 'description', 'status']
                    for rel_field in rel_model._meta.fields:
                        # Loại bỏ created_by và modified_by từ nested models
                        if rel_field.name.lower() in ['created_by', 'modified_by']:
                            continue
                        if rel_field.name.lower() in PrintFormatService.SENSITIVE_FIELDS:
                            continue
                        # Chỉ lấy các field quan trọng
                        if rel_field.name.lower() not in important_fields and not rel_field.name.endswith('_id'):
                            continue
                        name = f'{field.name}__{rel_field.name}'
                        if prefix:
                            name = f'{prefix}__{name}'
                        field_type = PrintFormatService.get_field_type(rel_field)
                        fields.append({
                            'name': name,
                            'field_type': field_type,
                            'label': f"{get_verbose_label(field)} - {get_verbose_label(rel_field)}",
                            'is_required': not rel_field.null and not rel_field.blank,
                            'data_example': PrintFormatService.get_field_example(field_type, name)
                        })
                    
                    # Không traverse sâu hơn để tránh data explosion
                else:
                    name = field.name
                    if prefix:
                        name = f'{prefix}__{name}'
                    field_type = PrintFormatService.get_field_type(field)
                    fields.append({
                        'name': name,
                        'field_type': field_type,
                        'label': get_verbose_label(field),
                        'is_required': not field.null and not field.blank,
                        'data_example': PrintFormatService.get_field_example(field_type, name)
                    })
            return fields

        # Main model fields
        main_fields = build_fields_for_model(model)

        # Add system fields
        system_fields = [
            {
                'name': 'qr_code',
                'field_type': 'qr_code',
                'label': 'QR Code',
                'is_required': False,
                'data_example': f"{HOST}/landing/order/ORDER123"
            }
        ]
        
        # Add hard-coded checklist fields for DeliveryOperation to improve performance
        if model_name.lower() == 'deliveryoperation':
            special_fields = [
                {
                    'name': 'total_checklist_items',
                    'field_type': 'number',
                    'label': 'Total Checklist Items',
                    'is_required': False,
                    'data_example': 10
                },
                {
                    'name': 'checked_checklist_items',
                    'field_type': 'number',
                    'label': 'Checked Checklist Items',
                    'is_required': False,
                    'data_example': 8
                },
                {
                    'name': 'unchecked_checklist_items',
                    'field_type': 'number',
                    'label': 'Unchecked Checklist Items',
                    'is_required': False,
                    'data_example': 2
                },
                {
                    'name': 'checklist_by_category',
                    'field_type': 'table',
                    'label': 'Checklist By Category',
                    'is_required': False,
                    'fields': [
                        {
                            'name': 'item_name',
                            'field_type': 'text',
                            'label': 'Item Name',
                            'is_required': False,
                            'data_example': 'Safety Check'
                        },
                        {
                            'name': 'is_checked',
                            'field_type': 'boolean',
                            'label': 'Is Checked',
                            'is_required': False,
                            'data_example': True
                        },
                        {
                            'name': 'category_code',
                            'field_type': 'text',
                            'label': 'Category Code',
                            'is_required': False,
                            'data_example': 'SAFETY'
                        },
                        {
                            'name': 'checked_by_drones',
                            'field_type': 'table',
                            'label': 'Checked By Drones',
                            'is_required': False,
                            'fields': [
                                {
                                    'name': 'drone_name',
                                    'field_type': 'text',
                                    'label': 'Drone Name',
                                    'is_required': False,
                                    'data_example': 'Drone-001'
                                },
                                {
                                    'name': 'drone_id',
                                    'field_type': 'number',
                                    'label': 'Drone ID',
                                    'is_required': False,
                                    'data_example': 1
                                },
                                {
                                    'name': 'approved_at',
                                    'field_type': 'date',
                                    'label': 'Approved At',
                                    'is_required': False,
                                    'data_example': '2024-03-20 10:30:00'
                                }
                            ],
                            'data_example': []
                        }
                    ],
                    'data_example': []
                },
                # Thêm các field mới cho delivery operation
                {
                    'name': 'drone__id',
                    'field_type': 'number',
                    'label': 'Drone ID',
                    'is_required': False,
                    'data_example': 15
                },
                {
                    'name': 'drone__name',
                    'field_type': 'text',
                    'label': 'Drone Name',
                    'is_required': False,
                    'data_example': 'Drone X-15'
                },
                {
                    'name': 'drone__model',
                    'field_type': 'text',
                    'label': 'Drone Model',
                    'is_required': False,
                    'data_example': 'X-Series'
                },
                {
                    'name': 'drone__status',
                    'field_type': 'text',
                    'label': 'Drone Status',
                    'is_required': False,
                    'data_example': 'active'
                },
                {
                    'name': 'drone__battery_level',
                    'field_type': 'number',
                    'label': 'Drone Battery Level',
                    'is_required': False,
                    'data_example': 85
                },
                {
                    'name': 'drone__flight_time',
                    'field_type': 'text',
                    'label': 'Flight Time',
                    'is_required': False,
                    'data_example': '2025-08-18 08:00:00 - 2025-08-18 10:30:00'
                },
                {
                    'name': 'weather_conditions',
                    'field_type': 'text',
                    'label': 'Weather Conditions',
                    'is_required': False,
                    'data_example': 'Clear, Wind: 5-10 km/h'
                },
                {
                    'name': 'route__terminals',
                    'field_type': 'table',
                    'label': 'Route Terminals',
                    'is_required': False,
                    'fields': [
                        {
                            'name': 'id',
                            'field_type': 'number',
                            'label': 'Terminal ID',
                            'is_required': False,
                            'data_example': 1
                        },
                        {
                            'name': 'name',
                            'field_type': 'text',
                            'label': 'Terminal Name',
                            'is_required': False,
                            'data_example': 'Terminal TP.HCM'
                        }
                    ],
                    'data_example': []
                },
                {
                    'name': 'order__items__name',
                    'field_type': 'text',
                    'label': 'Order Items Names',
                    'is_required': False,
                    'data_example': 'Package A - Electronics'
                },
                {
                    'name': 'confirmation_photo',
                    'field_type': 'text',
                    'label': 'Confirmation Photo',
                    'is_required': False,
                    'data_example': '/media/delivery_confirmations/sample_photo.jpg'
                },
                {
                    'name': 'start_delivery_at',
                    'field_type': 'text',
                    'label': 'Start Delivery At',
                    'is_required': False,
                    'data_example': '2025-08-18 08:00:00'
                },
                {
                    'name': 'delivered_at',
                    'field_type': 'text',
                    'label': 'Delivery At',
                    'is_required': False,
                    'data_example': '2025-08-18 10:00:00'
                },
                {
                    'name': 'drone__wind_resistance',
                    'field_type': 'number',
                    'label': 'Drone Wind Resistance',
                    'is_required': False,
                    'data_example': 10
                },
                {
                    'name': 'drone__weight',
                    'field_type': 'number',
                    'label': 'Drone Weight',
                    'is_required': False,
                    'data_example': 10
                },
                {
                    'name': 'drone__weight_capacity',
                    'field_type': 'number',
                    'label': 'Drone Weight Capacity',
                    'is_required': False,
                    'data_example': 10
                },
                {
                    'name': 'drone__temperature',
                    'field_type': 'number',
                    'label': 'Drone Temperature',
                    'is_required': False,
                    'data_example': 10
                },
                {
                    'name': 'drone__manufacturer_name',
                    'field_type': 'text',
                    'label': 'Drone Manufacturer Name',
                    'is_required': False,
                    'data_example': 'Drone Manufacturer Name'
                },
                {
                    'name': 'process_history',
                    'field_type': 'table',
                    'label': 'Process History',
                    'is_required': False,
                    'fields': [
                        {
                            'name': 'create_on',
                            'field_type': 'datetime',
                            'label': 'Create On',
                            'is_required': False,
                            'data_example': '2025-08-18 08:00:00'
                        },
                        {
                            'name': 'description',
                            'field_type': 'text',
                            'label': 'Description',
                            'is_required': False,
                            'data_example': 'Order is being processed'
                        }
                    ],
                    'data_example': []
                },
                {
                    'name': 'route__total_distance',
                    'field_type': 'text',
                    'label': 'Route Total Distance',
                    'is_required': False,
                    'data_example': '100 km'
                },
                {
                    'name': 'delivery_arrive_at',
                    'field_type': 'text',
                    'label': 'Delivery Arrive At',
                    'is_required': False,
                    'data_example': '2025-08-18 10:00:00'
                },
                {
                    'name': 'delivery_arrive_at_terminal',
                    'field_type': 'text',
                    'label': 'Delivery Arrive At Terminal',
                    'is_required': False,
                    'data_example': ''
                },
                {
                    'name': 'order__order_code',
                    'field_type': 'text',
                    'label': 'Order Code',
                    'is_required': False,
                    'data_example': ''
                },
                {
                    'name': 'drone__registration_number',
                    'field_type': 'text',
                    'label': 'Drone Registration Number',
                    'is_required': False,
                    'data_example': ''
                },
                {
                    'name': 'drone__city_province',
                    'field_type': 'text',
                    'label': 'Drone City Province',
                    'is_required': False,
                    'data_example': ''
                },
            ]
            system_fields.extend(special_fields)
        
        main_fields.extend(system_fields)

        # Related tables (OneToMany và ManyToMany) - Giới hạn để tránh data explosion
        related_tables = []
        
        # 1. OneToMany relationships (reverse foreign keys) - Chỉ lấy các relationship quan trọng
        important_relationships = ['items', 'approvals', 'status_history', 'returns', 'cancellations']
        for rel in model._meta.related_objects:
            rel_name = rel.get_accessor_name()
            # Chỉ lấy các relationship quan trọng
            if rel_name.lower() not in important_relationships:
                continue
                
            rel_model = rel.related_model
            # Giới hạn fields cho related model
            rel_fields = []
            for field in rel_model._meta.fields:
                if field.name.lower() in PrintFormatService.SENSITIVE_FIELDS:
                    continue
                # Chỉ lấy các field cơ bản
                if field.name.lower() in ['id', 'name', 'status', 'created_on', 'modified_on']:
                    rel_fields.append({
                        'name': field.name,
                        'field_type': PrintFormatService.get_field_type(field),
                        'label': get_verbose_label(field),
                        'is_required': not field.null and not field.blank,
                        'data_example': PrintFormatService.get_field_example(PrintFormatService.get_field_type(field), field.name)
                    })
            
            related_tables.append({
                'name': rel_name,
                'field_type': 'table',
                'label': rel_model._meta.verbose_name.title() if rel_model._meta.verbose_name else rel_model._meta.model_name,
                'fields': rel_fields,
                'data_example': []
            })
        
        # 2. ManyToMany relationships - Bỏ qua để giảm complexity
        # for field in model._meta.many_to_many:
        #     if field.name.lower() in PrintFormatService.SENSITIVE_FIELDS:
        #         continue
        #     rel_model = field.related_model
        #     rel_fields = build_fields_for_model(rel_model)
        #     related_tables.append({
        #         'name': field.name,
        #         'field_type': 'table',
        #         'label': rel_model._meta.verbose_name.title() if rel_model._meta.verbose_name else rel_model._meta.model_name,
        #         'fields': rel_fields,
        #         'data_example': []
        #     })

        return [{
            'name': model._meta.model_name,
            'label': model._meta.verbose_name.title() if model._meta.verbose_name else model._meta.model_name,
            'fields': main_fields + related_tables
        }]

    @staticmethod
    def get_field_type(field: models.Field) -> str:
        """Xác định loại field"""
        if isinstance(field, models.ForeignKey):
            return 'foreign_key'
        elif isinstance(field, models.ManyToManyField):
            return 'many_to_many'
        elif hasattr(field, 'related_name'):
            return 'child_table'
        elif isinstance(field, models.CharField):
            return 'text'
        elif isinstance(field, (models.IntegerField, models.DecimalField, models.FloatField)):
            return 'number'
        elif isinstance(field, models.DateField):
            return 'date'
        elif isinstance(field, models.DateTimeField):
            return 'datetime'
        elif isinstance(field, models.BooleanField):
            return 'boolean'
        return 'text'

    @staticmethod
    def get_field_options(field: models.Field) -> Dict[str, Any]:
        """Lấy các options của field"""
        options = {}
        
        if isinstance(field, models.ForeignKey):
            options['model'] = field.related_model._meta.model_name
            options['label_field'] = 'name'  # hoặc field nào bạn muốn hiển thị
        elif isinstance(field, models.ManyToManyField):
            options['model'] = field.related_model._meta.model_name
        elif hasattr(field, 'related_name'):
            options['model'] = field.related_model._meta.model_name
            options['columns'] = PrintFormatService.get_child_table_columns(field.related_model)
            
        return options

    @staticmethod
    def get_child_table_columns(model: models.Model) -> List[Dict[str, Any]]:
        """Lấy columns cho child table"""
        columns = []
        for field in model._meta.fields:
            # Bỏ qua các field nhạy cảm
            if field.name.lower() in PrintFormatService.SENSITIVE_FIELDS:
                continue

            columns.append({
                'name': field.name,
                'label': field.verbose_name.title().capitalize() if field.verbose_name else field.name.replace('_', ' ').title().capitalize(),
                'type': PrintFormatService.get_field_type(field)
            })
        return columns

    @staticmethod
    def _handle_enum_value(value: Any) -> Any:
        """Xử lý giá trị enum và model instances"""
        if value is None:
            return None
            
        # Kiểm tra nếu là model instance
        if hasattr(value, '_meta'):
            # Nếu là foreign key, trả về dict với id và name
            if hasattr(value, 'id'):
                return {
                    'id': value.id,
                    'name': str(value)
                }
            return str(value)
            
        # Kiểm tra nếu là enum
        if hasattr(value, '__class__'):
            # Kiểm tra nếu là enum Django
            if hasattr(value, 'value'):
                return value.value
            # Kiểm tra nếu là enum Python
            elif hasattr(value, 'name'):
                return value.name
            # Kiểm tra nếu là enum Django model field
            elif hasattr(value, 'label'):
                return value.label
            # Nếu không có thuộc tính nào phù hợp, trả về string representation
            return str(value)
                
        return value

    @staticmethod
    def format_field_value(value: Any, field_type: str, format_string: str = None, language: str = 'en') -> Any:
        """Format giá trị field theo type với hỗ trợ locale"""
        if value is None:
            return None

        # Xử lý enum values và model instances
        value = PrintFormatService._handle_enum_value(value)

        if field_type == 'foreign_key':
            if isinstance(value, dict) and 'name' in value:
                return value['name']
            return str(value) if value else None
        elif field_type == 'child_table':
            if isinstance(value, list):
                return [{
                    'id': item.get('id'),
                    'name': item.get('name', str(item))
                } for item in value]
            return []
        elif field_type == 'many_to_many':
            if isinstance(value, list):
                return [{
                    'id': item.get('id'),
                    'name': item.get('name', str(item))
                } for item in value]
            return []
        elif field_type == 'number' and format_string:
            try:
                return format(float(value), format_string)
            except (ValueError, TypeError):
                return str(value)
        elif field_type == 'date':
            if format_string:
                try:
                    return value.strftime(format_string)
                except (AttributeError, TypeError):
                    return str(value)
            else:
                # Use locale-aware formatting when no custom format is specified
                return PrintFormatService._format_date_by_locale(value, language)
        elif field_type == 'datetime':
            if format_string:
                try:
                    return value.strftime(format_string)
                except (AttributeError, TypeError):
                    return str(value)
            else:
                # Use locale-aware formatting when no custom format is specified
                return PrintFormatService._format_datetime_by_locale(value, language)
            
        return str(value) if value is not None else None

    @staticmethod
    def generate_qr_base64(data: str) -> str:
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"

    @staticmethod
    def get_system_fields(instance=None, model_name: str = None) -> dict:
        """Trả về các biến hệ thống như logo, qr_code_url cho context template"""
        # Lấy logo từ config hệ thống hoặc hardcode demo
        logo = f"{HOST}/static/logo.png"
        try:
            config = AdminConfig.objects.get(name='system').settings
            logo = config.get('ui', {}).get('base', {}).get('logo', logo)
        except Exception:
            pass
        # QR code URL: link đến landing page của order
        qr_code_url = ''
        qr_code_list = []
        qr_terminal_name = ''
        if instance and hasattr(instance, 'order_code') and hasattr(instance, 'items'):
            for item in instance.delivery_operation.items.all()  :
                if item:
                    qr_status = instance.delivery_operation.current_status.code
                    
                    if instance.delivery_option.code == 'delivery_to_door':
                        qr_terminal_name = f'{instance.recipient_address.full_address}'
                    elif instance.delivery_option.code == 'collect_at_location':
                        qr_terminal_name = f'{instance.delivery_terminal.name}'
                    qr_code_list.append({
                        'qr_package_id': item.id,
                        'qr_order_code': instance.order_code,
                        'qr_status': qr_status, 
                        'qr_terminal_name': qr_terminal_name
                    })
        return {
            'logo': logo,
            'qr_code': qr_code_list,

        }

    @staticmethod
    def get_print_format_data(print_format: PrintFormat, instance: models.Model, model_name: str = None, language: str = None) -> Dict[str, Any]:
        """Build context data tường minh cho template (bao gồm cả các trường khóa ngoại, các bảng 1-nhiều), đảm bảo JSON serializable và format datetime theo locale"""
        # Get user_settings from created_by user
        user_settings = None
        if hasattr(instance, 'created_by') and instance.created_by:
            # Get user settings from created_by user
            try:
                if hasattr(instance.created_by, 'user_settings'):
                    user_settings = instance.created_by.user_settings
                elif hasattr(instance.created_by, 'usersettings'):
                    user_settings = instance.created_by.usersettings
            except Exception:
                pass
        
        def to_json_value(val):
            """Convert any value to JSON serializable format with user settings-aware datetime formatting"""
            if val is None:
                return None
            
            # Using dictionary mapping with type checking for cleaner code
            type_handlers = {
                dict: lambda v: f"{v['value']} {v['unit']}" if 'value' in v and 'unit' in v else v,
                int: lambda v: v,
                float: lambda v: v,
                str: lambda v: v,
                bool: lambda v: v,
                Decimal: lambda v: float(v),
                datetime: lambda v: PrintFormatService._format_datetime_with_user_settings(v, user_settings, instance),
                date: lambda v: PrintFormatService._format_datetime_with_user_settings(v, user_settings, instance),
                time: lambda v: PrintFormatService._format_datetime_with_user_settings(v, user_settings, instance),
            }
            
            # Check for exact type match first
            for type_class, handler in type_handlers.items():
                if isinstance(val, type_class):
                    return handler(val)
                    
            # Handle special cases
            if hasattr(val, '_meta'):  # Model instance
                return str(val)
            if hasattr(val, 'name') and hasattr(val, 'value'):  # Enum
                return str(val.value)
                
            return str(val)
            
        data = {}
        
        # Field trực tiếp - using dictionary comprehension for more concise code
        data.update({
            f'{field.name}__{rel_field.name}': to_json_value(getattr(getattr(instance, field.name, None), rel_field.name, None))
            for field in instance._meta.fields
            if isinstance(field, models.ForeignKey) and getattr(instance, field.name, None) is not None and not field.name.lower() in PrintFormatService.SENSITIVE_FIELDS
            for rel_field in field.related_model._meta.fields
        })
        
        data.update({
            field.name: to_json_value(getattr(instance, field.name, None))
            for field in instance._meta.fields
            if not isinstance(field, models.ForeignKey) and not field.name.lower() in PrintFormatService.SENSITIVE_FIELDS
        })
        
        # Quan hệ 1-nhiều - using generator expressions for improved performance
        def get_regular_fields(rel_model, rel_obj):
            return {
                rel_field.name: to_json_value(getattr(rel_obj, rel_field.name, None))
                for rel_field in rel_model._meta.fields
                if not isinstance(rel_field, models.ForeignKey) and not rel_field.name.lower() in PrintFormatService.SENSITIVE_FIELDS
            }
        
        def get_foreign_key_fields(rel_model, rel_obj):
            return {
                f'{rel_field.name}__{fk_field.name}': to_json_value(getattr(getattr(rel_obj, rel_field.name, None), fk_field.name, None))
                for rel_field in rel_model._meta.fields
                if isinstance(rel_field, models.ForeignKey) and getattr(rel_obj, rel_field.name, None) is not None and not rel_field.name.lower() in PrintFormatService.SENSITIVE_FIELDS
                for fk_field in rel_field.related_model._meta.fields
            }
        
        def process_relation(rel):
            accessor = rel.get_accessor_name()
            rel_manager = getattr(instance, accessor, None)
            
            if rel_manager is None:
                return None
    
            
            # Handle both queryset and single object cases
            if hasattr(rel_manager, 'all'):
                # It's a queryset
                items = rel_manager.all()
            else:
                # It's a single object
                items = [rel_manager] if rel_manager else []
                
            return (
                accessor,
                list(map(
                    lambda rel_obj: {
                        **get_regular_fields(rel.related_model, rel_obj),
                        **get_foreign_key_fields(rel.related_model, rel_obj)
                    },
                    items
                ))
            )
        
        relations = filter(None, map(process_relation, instance._meta.related_objects))
        data.update(dict(relations)) 
                
        # Thêm biến hệ thống
        data.update(PrintFormatService.get_system_fields(instance, model_name))
        return data

    @staticmethod
    def get_report_template_data(report_template: ReportTemplate, instance: models.Model, model_name: str = None, language: str = None) -> Dict[str, Any]:
        """Build context data cho report template (bao gồm cả các trường khóa ngoại, các bảng 1-nhiều), đảm bảo JSON serializable và format datetime theo locale"""
        # Get user_settings from created_by user
        user_settings = None
        group = None
        print("REPORT TEWMPLATE DATA: ", report_template.id)
        if hasattr(instance, 'created_by') and instance.created_by:
            group = instance.created_by.userprofilelink.group if hasattr(instance.created_by, 'userprofilelink') else None
            # Get user settings from created_by user
            try:
                if hasattr(instance.created_by, 'user_settings'):
                    user_settings = instance.created_by.user_settings
                elif hasattr(instance.created_by, 'usersettings'):
                    user_settings = instance.created_by.usersettings
            except Exception:
                pass
        
        def to_json_value(val):
            """Convert any value to JSON serializable format with user settings-aware datetime formatting"""
            if val is None:
                return None
                
            
            
            # Using dictionary mapping with type checking for cleaner code
            type_handlers = {
                dict: lambda v: f"{v['value']} {v['unit']}" if 'value' in v and 'unit' in v else v,
                int: lambda v: v,
                float: lambda v: v,
                str: lambda v: v,
                bool: lambda v: v,
                Decimal: lambda v: float(v),
                datetime: lambda v: PrintFormatService._format_datetime_with_user_settings(v, user_settings, instance),
                date: lambda v: PrintFormatService._format_datetime_with_user_settings(v, user_settings, instance),
                time: lambda v: PrintFormatService._format_datetime_with_user_settings(v, user_settings, instance),
                UUID: lambda v: str(v),
                list: lambda v: [to_json_value(item) for item in v] if v else [],
                tuple: lambda v: [to_json_value(item) for item in v] if v else [],
                set: lambda v: [to_json_value(item) for item in v] if v else [],
            }
            
            # Check for exact type match first
            for type_class, handler in type_handlers.items():
                if isinstance(val, type_class):
                    return handler(val)
                    
            # Handle special cases - Chuyển đổi FK objects thành giá trị có thể serialize
            if val is None:
                return None
            if hasattr(val, '_meta'):  # Model instance
                # Chỉ lấy ID của model, không trả về toàn bộ object
                return val.id if hasattr(val, 'id') else str(val)
            if hasattr(val, 'name') and hasattr(val, 'value'):  # Enum
                return str(val.value)
            if hasattr(val, 'all'):  # QuerySet
                return list(val.values_list('id', flat=True)) if val.exists() else []
            if hasattr(val, '__iter__') and not isinstance(val, (str, bytes, dict)):
                # Convert iterables to list, but handle strings and dicts separately
                try:
                    return [to_json_value(item) for item in val]
                except:
                    return str(val)
                
            return str(val)
            
        data = {}
        
        # Field trực tiếp - using dictionary comprehension for more concise code
        data.update({
            f'{field.name}__{rel_field.name}': to_json_value(getattr(getattr(instance, field.name, None), rel_field.name, None))
            for field in instance._meta.fields
            if isinstance(field, models.ForeignKey) and getattr(instance, field.name, None) is not None and not field.name.lower() in PrintFormatService.SENSITIVE_FIELDS
            for rel_field in field.related_model._meta.fields
        })
        
        data.update({
            field.name: to_json_value(getattr(instance, field.name, None))
            for field in instance._meta.fields
            if not isinstance(field, models.ForeignKey) and not field.name.lower() in PrintFormatService.SENSITIVE_FIELDS
        })
        
        # Quan hệ 1-nhiều - using generator expressions for improved performance
        def get_regular_fields(rel_model, rel_obj):
            return {
                rel_field.name: to_json_value(getattr(rel_obj, rel_field.name, None))
                for rel_field in rel_model._meta.fields
                if not isinstance(rel_field, models.ForeignKey) and not rel_field.name.lower() in PrintFormatService.SENSITIVE_FIELDS
            }
        
        def get_foreign_key_fields(rel_model, rel_obj):
            return {
                f'{rel_field.name}__{fk_field.name}': to_json_value(getattr(getattr(rel_obj, rel_field.name, None), fk_field.name, None))
                for rel_field in rel_model._meta.fields
                if isinstance(rel_field, models.ForeignKey) and getattr(rel_obj, rel_field.name, None) is not None and not rel_field.name.lower() in PrintFormatService.SENSITIVE_FIELDS
                for fk_field in rel_field.related_model._meta.fields
            }
        
        def process_relation(rel):
            accessor = rel.get_accessor_name()
            rel_manager = getattr(instance, accessor, None)
            
            if rel_manager is None:
                return None
    
            
            # Handle both queryset and single object cases
            if hasattr(rel_manager, 'all'):
                # It's a queryset
                items = rel_manager.all()
            else:
                # It's a single object
                items = [rel_manager] if rel_manager else []
                
            return (
                accessor,
                list(map(
                    lambda rel_obj: {
                        **get_regular_fields(rel.related_model, rel_obj),
                        **get_foreign_key_fields(rel.related_model, rel_obj)
                    },
                    items
                ))
            )
        
        relations = filter(None, map(process_relation, instance._meta.related_objects))
        for accessor, items in relations:
            if items:
                # Đảm bảo items có thể serialize được
                serializable_items = []
                for item in items:
                    serializable_item = {}
                    for key, value in item.items():
                        serializable_item[key] = to_json_value(value)
                    serializable_items.append(serializable_item)
                data[accessor] = serializable_items
            else:
                data[accessor] = [] 
        
        # Xử lý tất cả FK fields một cách linh động
        processed_objects = set()  
        
        def process_foreign_key_fields(obj, prefix='', depth=0, max_depth=3):
            
            if not obj or not hasattr(obj, '_meta'):
                return
            
            
            if depth >= max_depth:
                return
            
            # Tạo unique key cho object (model_name + id)
            obj_key = f"{obj._meta.model.__name__}_{obj.pk}" if hasattr(obj, 'pk') and obj.pk else None
            
            # Kiểm tra xem object đã được xử lý chưa để tránh chu trình
            if obj_key and obj_key in processed_objects:
                return
            
            # Đánh dấu object đã được xử lý
            if obj_key:
                processed_objects.add(obj_key)
            
            for field in obj._meta.fields:
                # Kiểm tra cả field name và pattern *__field_name
                field_name = field.name.lower()
                if field_name in PrintFormatService.SENSITIVE_FIELDS:
                    continue
                
                # Kiểm tra pattern *__field_name - chỉ loại bỏ created_by và modified_by từ nested models
                if prefix:
                    full_field_name = f'{prefix}{field_name}'
                    # Chỉ loại bỏ created_by và modified_by từ nested models
                    if field_name in ['created_by', 'modified_by']:
                        continue
                    
                field_value = getattr(obj, field.name, None)
                
                if isinstance(field, models.ForeignKey) and field_value is not None:
                    # Xử lý FK field - lấy tất cả fields của related object
                    if hasattr(field_value, '_meta'):
                        for fk_field in field_value._meta.fields:
                            fk_field_name = fk_field.name.lower()
                            if fk_field_name not in PrintFormatService.SENSITIVE_FIELDS:
                                field_key = f'{prefix}{field.name}__{fk_field.name}' if prefix else f'{field.name}__{fk_field.name}'
                                
                                # Kiểm tra pattern *__field_name cho field_key - chỉ loại bỏ created_by và modified_by từ nested models
                                if not (field_key.lower().endswith('__created_by') or field_key.lower().endswith('__modified_by')):
                                    data[field_key] = to_json_value(getattr(field_value, fk_field.name, None))
                        
                        # Đệ quy xử lý FK fields của FK object (nested FK) với kiểm tra depth
                        process_foreign_key_fields(
                            field_value, 
                            f'{prefix}{field.name}__' if prefix else f'{field.name}__',
                            depth=depth + 1,
                            max_depth=max_depth
                        )
                else:
                    # Field thường - thêm vào data
                    field_key = f'{prefix}{field.name}' if prefix else field.name
                    
                    # Kiểm tra pattern *__field_name cho field_key - chỉ loại bỏ created_by và modified_by từ nested models
                    if not (field_key.lower().endswith('__created_by') or field_key.lower().endswith('__modified_by')):
                        data[field_key] = to_json_value(field_value)
        
        # Xử lý tất cả FK fields của instance chính
        process_foreign_key_fields(instance)
        
        # Xử lý các related objects (OneToOne, OneToMany, ManyToMany)
        for rel in instance._meta.related_objects:
            accessor = rel.get_accessor_name()
            rel_manager = getattr(instance, accessor, None)
            
            if rel_manager is None:
                continue
            
            # Xử lý cả queryset và single object
            if hasattr(rel_manager, 'all'):
                # Queryset (OneToMany, ManyToMany)
                items = list(rel_manager.all())
                if items:
                    # Lấy item đầu tiên để xử lý fields
                    first_item = items[0]
                    process_foreign_key_fields(first_item, f'{accessor}__', depth=1)
                    
                    # Thêm danh sách items - chỉ lấy ID để tránh serialization issues
                    data[accessor] = [item.id for item in items if hasattr(item, 'id')]
                else:
                    data[accessor] = []
            else:
                # Single object (OneToOne)
                if rel_manager:
                    process_foreign_key_fields(rel_manager, f'{accessor}__', depth=1)
                    # Thêm ID của related object
                    data[accessor] = rel_manager.id if hasattr(rel_manager, 'id') else None
                else:
                    data[accessor] = None
                
        # Thêm biến hệ thống
        data.update(PrintFormatService.get_system_fields(instance, model_name))
        
        if model_name and ('deliveryoperation' in model_name.lower() or 'delivery.deliveryoperation' in model_name.lower()):
            # Kiểm tra template content để quyết định có xử lý expensive operations hay không
            template_content = report_template.template if report_template else ""
            template_content = decode_template_html_entities(template_content)
            
            # Conditional processing dựa trên template content
            needs_weather = any(key in template_content for key in ['weather', 'summary_weather', 'temperature', 'wind_speed'])
            needs_map = 'map_delivery' in template_content
            
            checklist_data = PrintFormatService._get_checklist_data(
                instance, group, template_content, needs_weather, needs_map, user_settings, language
            )
            data.update(checklist_data)
        
        # Thêm thông tin report template nếu cần
        if report_template:
            data['report_template_name'] = report_template.name
            data['report_template_id'] = report_template.id
        
        # Đảm bảo tất cả các giá trị trong data đều có thể serialize được
        serializable_data = {}
        for key, value in data.items():
            try:
                serializable_data[key] = to_json_value(value)
            except Exception as e:
                # Nếu không thể serialize, bỏ qua field này
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not serialize field {key}: {str(e)}")
                continue
        
        return serializable_data

    @staticmethod
    def normalize_template_content(template_str: str) -> str:
        """Remove invisible characters and normalize template variables that can break Django template parsing.
        
        - Zero-width characters: \u200b, \u200c, \u200d
        - BOM: \ufeff
        - Non-breaking space: \u00A0
        - Newlines inside template variables
        - All carriage returns and line feeds
        - Remove escaped quotes that break CSS
        - Convert <style> tags to inline styles where possible
        """
        if not isinstance(template_str, str):
            return template_str
        template_str = decode_template_html_entities(template_str)
        # Remove invisible characters
        invisible_chars = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u00A0"]
        for ch in invisible_chars:
            template_str = template_str.replace(ch, "")
        
        # Remove escaped quotes that break CSS styling
        template_str = template_str.replace('\\"', '"')  # Remove escaped quotes
        template_str = template_str.replace("\\'", "'")  # Remove escaped single quotes
        
        # Remove all carriage returns and line feeds
        template_str = template_str.replace('\r\n', ' ')  # Replace \r\n with space
        template_str = template_str.replace('\r', ' ')    # Replace remaining \r with space
        template_str = template_str.replace('\n', ' ')    # Replace remaining \n with space
        
        # Clean up multiple spaces
        import re
        template_str = re.sub(r'\s+', ' ', template_str)  # Replace multiple spaces with single space
        
        # Normalize template variables - ensure proper spacing
        template_str = re.sub(r'\{\{\s*([^}]+?)\s*\}\}', lambda m: '{{ ' + m.group(1).strip() + ' }}', template_str)
        
        return template_str

    @staticmethod
    def calculate_distance_between_coordinates(lat1, lon1, lat2, lon2):
        # Radius of Earth (km)
        R = 6371.0

        # Convert degrees → radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    @staticmethod
    def _get_checklist_data(instance, group, template_content: str = None, needs_weather: bool = False, needs_map: bool = False, user_settings=None, language: str = 'en') -> Dict[str, Any]:
        # """Xử lý checklist data cho DeliveryOperation với conditional processing"""
        # try:
            from checklist_setting.models import ChecklistSetting, ChecklistSettingCategory
            
            # Lấy drone thực tế đã chở operation này
            drone = None
            drone_ids = set()
            
            # Thử lấy từ DeliveryOperationItem trước
            delivery_items = DeliveryOperationItem._base_manager.filter(delivery_operation=instance)
          
            if delivery_items:
                item_drone_ids = delivery_items.all().values_list('drone_id', flat=True)
                drone_ids.update([d_id for d_id in item_drone_ids if d_id is not None])
            
            # Nếu không có, thử lấy từ DeliveryOperationApproval
            if not drone_ids:
                approvals = getattr(instance, 'approvals', None)
                if approvals:
                    for approval in approvals.all():
                        if approval.drone and approval.drone.id:
                            drone_ids.add(approval.drone.id)
            
            # Tạo QuerySet từ drone_ids
            if drone_ids:
                drone = Device._base_manager.filter(id__in=list(drone_ids))

            # Nếu không có drone nào, trả về mock data

            # Lấy checklist settings được nhóm theo category (filter theo group)
            all_checklist_settings = ChecklistSetting._base_manager.select_related('category').filter(group=group, deleted__isnull=True, is_active=True) 
            
            # Lấy TẤT CẢ categories (không filter theo group) để đảm bảo hiển thị đầy đủ
            all_category_checklist_settings = ChecklistSettingCategory._base_manager.filter(deleted__isnull=True)
            
            # Lấy approvals của delivery operation để kiểm tra item nào đã được check
            approvals = DeliveryOperationApproval._base_manager.filter(delivery_operation=instance)
            checked_checklist_ids = set()
           
            if approvals:
                for approval in approvals:
                    # Chỉ lấy checklist của drone thực tế
                    if approval.drone and drone and approval.drone.id in drone.values_list('id', flat=True):
                        checklists = DeliveryOperationApprovalChecklist._base_manager.filter(approval=approval)
      
                        if checklists:
                            for checklist in checklists.all():
                                checklist_setting = getattr(checklist, 'checklist', None)
                                if checklist_setting:
                                    checked_checklist_ids.add(checklist_setting.id)
            
            # Khởi tạo checklist_by_category với tất cả categories (mảng rỗng)
            checklist_by_category = {}
            for category in all_category_checklist_settings:
                category_name = category.get_translation('name', language) if category.get_translation('name', language) else category.name if category else 'Uncategorized'
                if category_name not in checklist_by_category:
                    checklist_by_category[category_name] = []
            
            # Map checklist settings vào các categories tương ứng
            total_items = 0
            checked_items = 0
            
            for checklist_setting in all_checklist_settings:
                category = checklist_setting.category
                category_name = category.get_translation('name', language) if category.get_translation('name', language) else category.name if category else 'Uncategorized'
                
                # Đảm bảo category có trong checklist_by_category (nếu category không có trong all_category_checklist_settings)
                if category_name not in checklist_by_category:
                    checklist_by_category[category_name] = []
                
                # Kiểm tra xem item này đã được check chưa
                is_checked = checklist_setting.id in checked_checklist_ids
                if is_checked:
                    checked_items += 1
                total_items += 1
                
                # Tạo item data
                item_data = {
                    'item_name': checklist_setting.get_translation('item_name', language) if checklist_setting.get_translation('item_name', language) else checklist_setting.item_name,
                    'is_checked': is_checked,
                    'category_code': category.code if category else 'N/A',
                    'checked_by_drones': []
                }
                
                # Lấy thông tin drone approval nếu item đã được check
                if is_checked and approvals:
         
                    for approval in approvals.all():
                        # Chỉ lấy thông tin của drone thực tế
                        if approval.drone and drone and approval.drone.id in drone.values_list('id', flat=True):
                            checklists = getattr(approval, 'checklists', None)
                          
                            if checklists:
                                for checklist in checklists.all():
                                    if checklist.checklist_id == checklist_setting.id:
                                        item_data['checked_by_drones'].append({
                                            'drone_name': approval.drone.name if approval.drone.name else 'Unknown Drone',
                                            'drone_id': approval.drone.id if approval.drone.id else None,
                                            'approved_at': approval.created_on if approval.created_on else None
                                        })
                
                checklist_by_category[category_name].append(item_data)
            
            unchecked_items = total_items - checked_items
            
            # Thêm delivery operation fields mới
            delivery_data = {
                'total_checklist_items': total_items,
                'checked_checklist_items': checked_items,
                'unchecked_checklist_items': unchecked_items,
                'checklist_by_category': checklist_by_category,
                'auto_check_list': instance.another_info.get('auto_checklist', [])
            }
            delivery_data['approve_by'] = f'{instance.modified_by.first_name} {instance.modified_by.last_name}' if instance.modified_by else None
            # Thêm thông tin drone chính của delivery operation
            if drone:
                drone_data = PrintFormatService._get_drone_data_from_queryset(drone)
                delivery_data.update(drone_data)
                delivery_data['drone__manufacturer_name'] = drone_data['drone__manufacturer_name']
                delivery_data['drone__flight_time'] = drone_data['drone__flight_time']
                delivery_data['drone__temperature'] = drone_data['drone__temperature']
                delivery_data['drone__wind_resistance'] = drone_data['drone__wind_resistance']
                delivery_data['drone__weight'] = drone_data['drone__weight']
                delivery_data['drone__registration_number'] = drone_data['drone__registration_number']
                delivery_data['drone__city_province'] = drone_data['drone__city_province']
            else:
                # Nếu không có drone, thử lấy từ delivery items
                delivery_items = getattr(instance, 'items', None)
                if delivery_items:
                    for item in delivery_items.all():
                        if item.drone:
                            drone_data = PrintFormatService._get_drone_data_from_single_object(item.drone)
                            delivery_data['drone__manufacturer_name'] = drone_data['drone__manufacturer_name']
                            delivery_data['drone__flight_time'] = drone_data['drone__flight_time']
                            delivery_data['drone__temperature'] = drone_data['drone__temperature']
                            delivery_data['drone__wind_resistance'] = drone_data['drone__wind_resistance']
                            delivery_data['drone__weight'] = drone_data['drone__weight']
                            delivery_data['drone__registration_number'] = drone_data['drone__registration_number']
                            delivery_data['drone__city_province'] = drone_data['drone__city_province']
                            delivery_data.update(drone_data)
                            break
            
            # Thêm delivery items nếu có
            delivery_items = getattr(instance, 'items', None)
            if delivery_items:
                items_data = []
                for item in delivery_items.all():
                    item_info = {
                        'id': item.id,
                        'timestamp': PrintFormatService._format_datetime_with_user_settings(item.timestamp, user_settings, instance) if item.timestamp else None,
                        'is_drone_approved': item.is_drone_approved,
                        'is_delivered_by_drone': item.is_delivered_by_drone,
                        'drone_arrived_at': PrintFormatService._format_datetime_with_user_settings(item.drone_arrived_at, user_settings, instance) if item.drone_arrived_at else None,
                        'is_arrived': item.is_arrived,
                        'arrived_at': PrintFormatService._format_datetime_with_user_settings(item.arrived_at, user_settings, instance) if item.arrived_at else None,
                        'is_delivered': item.is_delivered,
                        'delivered_at': PrintFormatService._format_datetime_with_user_settings(item.delivered_at, user_settings, instance) if item.delivered_at else None,
                    }
                    
                    # Thêm thông tin drone nếu có
                    if item.drone:
                        drone_data = PrintFormatService._get_drone_data_from_single_object(item.drone)
                        item_info.update(drone_data)
                    
                    # Thêm thông tin order item nếu có
                    if item.order_item:
                        item_info['order_item__id'] = item.order_item.id
                        item_info['order_item__name'] = item.order_item.name if item.order_item.name else item.order_item.item_type.name
                        item_info['order_item__description'] = item.order_item.note if item.order_item.note else None
                        item_info['order_item__quantity'] = 1
                    
                    items_data.append(item_info)
                
                delivery_data['items'] = items_data
            
            # Thêm route information nếu có
            route = getattr(instance, 'route', None)
            delivery_data['route__total_distance'] = None
            if route:
                delivery_data['route__id'] = route.id
                delivery_data['route__name'] = route.name
                delivery_data['route__description'] = route.description if route.description else None
                delivery_data['route__estimated_distance'] = route.measurements.filter(measurement_type='estimated_distance').first().data.get('value', None) if route.measurements.filter(measurement_type='estimated_distance').first() else None
                delivery_data['route__img_map'] = route.img_map.file_url if route.img_map else None
                delivery_data['route__img_route'] = route.img_route.file_url if route.img_route else None
                # Thêm thông tin terminals trong route
                try:
                    route_terminals = route.route_terminals.all()
                    if route_terminals:
                        terminals_data = []
                        for terminal in route_terminals:
                            terminal_info = {
                                'id': terminal.terminal.id,
                                'name': terminal.terminal.name,
                                'code': terminal.terminal.code,
                            }
                            terminals_data.append(terminal_info)
                        delivery_data['route__terminals'] = terminals_data
                except Exception as e:
                    print("error", e)
                    # Nếu không thể lấy terminals, bỏ qua
                    pass
                delivery_data['route__total_distance'] = route.measurements.filter(measurement_type='total_distance').first().get_formatted_value() if route.measurements.filter(measurement_type='total_distance').first() else None
            
            # Thêm process history nếu có
            order = getattr(instance, 'order', None)
            process_history_data = []
            delivery_data['order__order_code'] = order.order_code if order else None
            # language = get_current_request().user.language.code if get_current_request().user.language else 'en'
            if order:
                process_history = order.histories.all()
                if process_history:
                    seen_descriptions = set()  # Track descriptions to avoid duplicates
                    for history in process_history:
                        description = history.get_translation('description', language)
                        # Only add if description is not already in the list
                        if description not in seen_descriptions:
                            seen_descriptions.add(description)
                            process_history_data.append({
                                'create_on': PrintFormatService._format_datetime_with_user_settings(history.created_on, None, instance) if history.created_on else None,
                                'description': description
                            })
                else:
                    process_history_data = []
            delivery_data['process_history'] = process_history_data
            # Thêm confirmation photo nếu có
            confirmation_photo = getattr(instance, 'confirmation_photo', None)
            if confirmation_photo:
                delivery_data['confirmation_photo'] = confirmation_photo
            completed_time = getattr(instance, 'modified_on', None)
            if completed_time:
                delivery_data['completed_time'] = PrintFormatService._format_datetime_with_user_settings(completed_time, user_settings, instance) if completed_time else None
                print("completed_time: ", completed_time)
            delivery_data['start_delivery_at'] = getattr(instance, 'modified_on', None)
            if order and order.histories.filter(action='arrived_at_terminal').exists():
                delivery_data['start_delivery_at'] = order.histories.filter(action='arrived_at_terminal').order_by('created_on').first().created_on
            delivery_data['start_delivery_at'] = PrintFormatService._format_datetime_with_user_settings(delivery_data['start_delivery_at'], user_settings, instance) if delivery_data['start_delivery_at'] else None
            delivery_data['delivery_arrive_at'] = getattr(instance, 'modified_on', None)
            if order and order.histories.filter(action='arrived').exists():
                delivery_data['delivery_arrive_at'] = order.histories.filter(action='arrived').last().created_on
                delivery_data['delivery_arrive_at'] = PrintFormatService._format_datetime_with_user_settings(delivery_data['delivery_arrive_at'], user_settings, instance) if delivery_data['delivery_arrive_at'] else None
            report_date = timezone.now().strftime('%Y-%m%d')
            order_code = order.order_code if order else ''
            delivery_data['serial_number'] = f'{report_date}-{order_code}'
            if order.delivery_option.code == "delivery_to_door":
                try:
                    delivery_address_lat = order.recipient_address.full_address.lat
                    delivery_address_lng = order.recipient_address.full_address.lng
                    # find the nearest terminal in route to the delivery address
                    for terminal in route.route_terminals.all():
                        terminal_lat = terminal.terminal.latitude
                        terminal_lng = terminal.terminal.longitude
                        distance = PrintFormatService.calculate_distance_between_coordinates(delivery_address_lat, delivery_address_lng, terminal_lat, terminal_lng)
                        if distance < min_distance:
                            min_distance = distance
                            nearest_terminal = terminal
                    delivery_data['delivery_arrive_at_terminal'] = nearest_terminal.name
                except Exception as e:
                    if order and order.delivery_terminal:
                        delivery_data['delivery_arrive_at_terminal'] = order.delivery_terminal.name
                    elif route:
                        delivery_data['delivery_arrive_at_terminal'] = route.route_terminals.order_by('order').last().terminal.name if route.route_terminals.order_by('order').last() else None
                    else:
                        delivery_data['delivery_arrive_at_terminal'] = None
            else:
                if order and order.delivery_terminal:
                    delivery_data['delivery_arrive_at_terminal'] = order.delivery_terminal.name
                elif route:
                    delivery_data['delivery_arrive_at_terminal'] = route.route_terminals.order_by('order').last().terminal.name if route.route_terminals.order_by('order').last() else None
                else:
                    delivery_data['delivery_arrive_at_terminal'] = None

            # Thêm thông tin order items
            try:
                order = getattr(instance, 'order', None)
                if order:
                    order_items = order.items.all()
                    if order_items:
                        items_data = []
                        for item in order_items:
                            item_info = {
                                'id': item.id,
                                'name': item.name if item.name else item.item_type.name,
                                'description': item.description if item.description else None,
                                'quantity': item.quantity if item.quantity else None,
                                'weight': item.weight if item.weight else None,
                            }
                            items_data.append(item_info)
                        
                        # Thêm vào delivery_data với key phù hợp cho template
                        delivery_data['order__items'] = items_data
                        
                        # Thêm order__items__name cho template (lấy tên item đầu tiên)
                        if order_items:
                            delivery_data['order__items__name'] = [item.name if item.name else item.item_type.name for item in order_items]
                        else:
                            delivery_data['order__items__name'] = 'N/A'
                    else:
                        delivery_data['order__items__name'] = 'N/A'
                else:
                    delivery_data['order__items__name'] = 'N/A'
            except Exception as e:
                # Nếu không thể lấy order items, bỏ qua
                delivery_data['order__items__name'] = 'N/A'
                pass
            
            # Conditional weather processing - chỉ xử lý khi template cần
            if needs_weather:
                try:
                    # Lấy tọa độ từ delivery operation
                    coordinates = WeatherService.get_coordinates_from_delivery_operation(instance)
                    
                    if coordinates and instance.modified_on:
                        latitude, longitude = coordinates
                        
                        # Lấy thông tin thời tiết tại thời điểm modified_on
                        weather_data = WeatherService.get_weather_at_time(
                            latitude=latitude,
                            longitude=longitude, 
                            target_datetime=instance.modified_on
                        )
                        
                        # Lấy ngôn ngữ từ user language
                        lang = instance.created_by.language.code if instance.created_by and hasattr(instance.created_by, 'language') and instance.created_by.language else 'en'
                        if weather_data:
                            # Format weather data cho cả 2 ngôn ngữ
                            formatted_weather = WeatherService.format_weather_for_display(weather_data, lang)
                            
                            # Tạo summary_weather cho template (format ngắn gọn như ảnh)
                            temp_value = weather_data.get('temperature')
                            wind_value = weather_data.get('wind_speed')
                            
                            # Convert wind speed từ km/h sang m/s
                            wind_ms = round(wind_value / 3.6, 2) if wind_value else None
                            
                            # Tạo summary_weather format với icon dễ nhận biết
                            if temp_value and wind_ms:
                                summary_weather = f"🌤 {temp_value}°C 💨 {wind_ms} m/s"
                            elif temp_value:
                                summary_weather = f"🌤 {temp_value}°C"
                            elif wind_ms:
                                summary_weather = f"💨 {wind_ms} m/s"
                            else:
                                summary_weather = "Weather data unavailable"
                            
                            # Thêm weather check vào delivery_data (hỗ trợ đa ngôn ngữ)
                            delivery_data.update({
                                # Default format
                                'weather_conditions': formatted_weather['weather_conditions'],
                                'temperature': formatted_weather['temperature'],
                                'humidity': formatted_weather['humidity'],
                                'wind_speed': formatted_weather['wind_speed'],
                                'weather_description': formatted_weather['weather_description'],
                                'weather_coordinates': formatted_weather['coordinates'],
                                'weather_timestamp': weather_data.get('timestamp'),
                                'weather_check_status': 'completed',
                                
                                # Summary weather cho template (format ngắn gọn)
                                'summary_weather': summary_weather,
                                
                                # Multi-language support
                                'weather_multilang': {
                                    'en': {
                                        'weather_conditions': formatted_weather['weather_conditions'],
                                        'weather_description': formatted_weather['weather_description']
                                    },
                                    'ko': {
                                        'weather_conditions': formatted_weather['weather_conditions'],
                                        'weather_description': formatted_weather['weather_description']
                                    }
                                }
                            })
                            
                            # Update checklist by category
                            delivery_data['checklist_by_category'] = checklist_by_category
                        
                    else:
                        # Không lấy được weather data (đa ngôn ngữ)
                        delivery_data.update({
                            'weather_conditions': 'No weather data available',
                            'temperature': 'N/A',
                            'humidity': 'N/A', 
                            'wind_speed': 'N/A',
                            'weather_description': 'Unknown',
                            'weather_coordinates': None,
                            'weather_check_status': 'failed',
                            'summary_weather': '❌ Weather data unavailable',
                            'weather_multilang': {
                                'en': {
                                    'weather_conditions': 'No weather data available',
                                    'weather_description': 'Unknown'
                                },
                                'ko': {
                                    'weather_conditions': '기상 데이터가 없습니다',
                                    'weather_description': '알 수 없음'
                                }
                            }
                        })   
                except Exception as e:
                    # Log error nếu có lỗi khi lấy weather data
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error getting weather data for delivery operation {instance.id}: {str(e)}")
                    
                    # Fallback weather data (đa ngôn ngữ)
                    delivery_data.update({
                        'weather_conditions': 'Error retrieving weather data',
                        'temperature': 'N/A',
                        'humidity': 'N/A',
                        'wind_speed': 'N/A',
                        'weather_description': 'System error',
                        'weather_coordinates': 'N/A',
                        'weather_check_status': 'error',
                        'summary_weather': '⚠️ Weather system error',
                        'weather_multilang': {
                            'en': {
                                'weather_conditions': 'Error retrieving weather data',
                                'weather_description': 'System error'
                            },
                            'ko': {
                                'weather_conditions': '기상 데이터 검색 오류',
                                'weather_description': '시스템 오류'
                            }
                        }
                    })
            else:
                # Không cần weather processing
                delivery_data.update({
                    'weather_conditions': 'Weather processing skipped',
                    'temperature': 'N/A',
                    'humidity': 'N/A',
                    'wind_speed': 'N/A',
                    'weather_description': 'Not required by template',
                    'weather_coordinates': 'N/A',
                    'weather_check_status': 'skipped',
                    'summary_weather': 'N/A - template doesn\'t require weather data'
                })
            
            # Conditional map processing - chỉ xử lý khi template cần
            # if needs_map:
            #     try:
            #         import logging
            #         logger = logging.getLogger(__name__)
            #         map_data = MapService.format_map_data_for_template(instance)
            #         delivery_data.update(map_data)
                    
            #         logger.info(f"Map data generated for delivery operation {instance.id}: {map_data.get('map_status')}")
                    
            #     except Exception as e:
            #         # Log error nếu có lỗi khi tạo map
            #         import logging
            #         logger = logging.getLogger(__name__)
            #         logger.error(f"Error generating map for delivery operation {instance.id}: {str(e)}")
                    
            #         # Fallback map data
            #         delivery_data.update({
            #             'map_delivery': None,
            #             'map_delivery_html': None,

            #             'map_message': f'Error generating map: {str(e)}'
            #         })
            # else:
                # Không cần map processing
            delivery_data.update({
                'map_delivery': None,
                'map_delivery_html': None,

                'map_message': 'Map processing skipped - not required by template'
            })
            
            return delivery_data
            
        # except Exception as e:
        #     # Log error và trả về data mặc định
        #     import logging
        #     logger = logging.getLogger(__name__)
        #     logger.error(f"Error processing checklist data: {str(e)}")
        #     print("error", e)
        #     # Trả về mock data để template có thể render
        #     return {}

    @staticmethod
    def get_user_print_formats(user, *args, **kwargs):
        """Lấy tất cả print formats mà user có quyền xem (không lọc theo model)"""
        if user.is_superuser:
            return PrintFormat.objects.all()
        return PrintFormat.objects.filter(created_by__group=user.group)

    @staticmethod
    @transaction.atomic
    def create_print_format(data: Dict[str, Any]) -> PrintFormat:
        """Tạo print format mới với các fields và columns, không gắn với model nào"""
        print_format = PrintFormat.objects.create(
            name=data['name'],
            template=data['template'],
            css=data.get('css'),
            is_default=data.get('is_default', False),
            is_enabled=data.get('is_enabled', True)
        )

        # Tạo các fields
        for field_data in data['fields']:
            field = print_format.fields.create(
                field_name=field_data['field_name'],
                field_type=field_data['field_type'],
                label=field_data['label'],
                is_visible=field_data.get('is_visible', True),
                width=field_data.get('width'),
                format_string=field_data.get('format_string'),
                display_field=field_data.get('display_field')
            )

            # Tạo các columns cho child table
            if field_data.get('columns'):
                for col_data in field_data['columns']:
                    field.columns.create(
                        field_name=col_data['field_name'],
                        label=col_data['label'],
                        field_type=col_data['field_type'],
                        width=col_data.get('width'),
                        is_visible=col_data.get('is_visible', True),
                        display_field=col_data.get('display_field')
                    )

        return print_format

    @staticmethod
    def get_list_template(request):
        data = PrintFormat.objects.all().order_by('-id')
        
        data = apply_dynamic_filters(data, request, [], request.GET.get('sort_obj',None))
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(data, page_size)
        pages = paginator.page(current_page)
        all_template = PrintFormatSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(status_code=200,
                            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_TEMPLATE_SUCCESS),
                            data=all_template,
                            total_pages=paginator.num_pages,
                            total_items=paginator.count,
                            current_page=current_page,
                            )

    @staticmethod
    def get_print_format_by_id(print_format_id: int):
        """Lấy print format theo id"""
        print_format = PrintFormat.objects.get(id=print_format_id)
        return PrintFormatSchema.from_queryset(print_format)

    @staticmethod
    def delete_print_format(print_format_id: str):
        """Xóa print format"""
        print_format_id = [int(id.strip()) for id in print_format_id.split(",")]
        if PrintFormat.objects.filter(id__in=print_format_id, is_default=True, is_enabled=True).exists():
            return BaseResponse(status_code=400,
                                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                                )
        PrintFormat.objects.filter(id__in=print_format_id).delete()
        return BaseResponse(status_code=200,
                          message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                          )

    @staticmethod
    def get_example_data() -> Dict[str, Any]:
        """Trả về data example đầy đủ để test template delivery checklist"""
        return {
            # Basic operation info
            'id': 428,
            'status': 'completed',
            'operation_type': 'delivery',
            'created_on': '2025-08-17 12:28:43',
            'modified_on': '2025-08-18 07:45:40',

            # Order information
            'order__id': 470,
            'order__order_code': '00000182',
            'order__created_on': '08-17-2025 12:28:43',
            'order__modified_on': '08-18-2025 07:45:40',
            'order__status': 'received',
            'order__priority': 'high',
            'order__items': [
                {
                    'id': 101,
                    'name': 'Package A - Electronics',
                    'description': 'Electronics package containing mobile devices',
                    'quantity': 1,
                    'weight': '2.5 kg'
                },
                {
                    'id': 102,
                    'name': 'Package B - Documents',
                    'description': 'Important business documents',
                    'quantity': 2,
                    'weight': '0.5 kg'
                }
            ],
            'order__items__name': 'Package A - Electronics',

            # Sender information
            'order__sender_name': 'Nguyễn Văn A',
            'order__sender_phone': '03245234657',
            'order__sender_address__full_address': '123 Đường ABC, Quận 1, TP.HCM',
            'order__sender_address__city': 'TP.HCM',
            'order__sender_address__district': 'Quận 1',
            'order__sender_address__ward': 'Phường Bến Nghé',
            'order__pickup_location__name': 'Terminal TP.HCM',
            'order__pickup_location__city_province': 'TP.HCM',
            'order__pickup_location__city_county_district': 'Quận 1',
            'order__pickup_location__ward_town_township': 'Phường Bến Nghé',
            'order__sender_note': 'Giao hàng trong giờ hành chính',

            # Recipient information
            'order__recipient_name': 'Trần Thị B',
            'order__recipient_phone': '04897098765',
            'order__recipient_address__full_address': '456 Đường XYZ, Quận Ba Đình, Hà Nội',
            'order__recipient_address__city': 'Hà Nội',
            'order__recipient_address__district': 'Quận Ba Đình',
            'order__recipient_address__ward': 'Phường Phúc Xá',
            'order__delivery_option__code': 'delivery_to_door',
            'order__delivery_terminal__name': 'Terminal Hà Nội',
            'order__delivery_terminal__city_province': 'Hà Nội',
            'order__delivery_terminal__city_county_district': 'Quận Ba Đình',
            'order__delivery_terminal__ward_town_township': 'Phường Phúc Xá',
            'order__recipient_note': 'Giao hàng tại cổng chính',

            # Financial information
            'order__subtotal': '₫ 10000.0',
            'order__delivery_fee': '₫ 2000.0',
            'order__tax_amount': '₫ 500.0',
            'order__discount_amount': '₫ 0.0',
            'order__total_amount': '₫ 12500.0',

            # Drone information
            'drone__id': 15,
            'drone__name': 'Drone X-15',
            'drone__model': 'X-Series',
            'drone__status': 'active',
            'drone__battery_level': 85,

            # Flight Information
            'drone__flight_time': '2025-08-18 08:00:00',
            'weather_conditions': 'Trời quang, Gió: 5-10 km/h, Nhiệt độ: 25°C, Độ ẩm: 65%',
            
            # Operator Information
            'created_by__first_name': 'Nguyễn',
            'created_by__last_name': 'Văn C',
            'created_by__email': 'operator@example.com',

            # Delivery Operation Information
            'current_status__name': 'completed',
            'is_partial_approved': False,
            'confirmation_photo': '/media/delivery_confirmations/sample_photo.jpg',
            
            # Route Information
            'route__id': 25,
            'route__name': 'Route TP.HCM - Hà Nội',
            'route__description': 'Tuyến đường giao hàng từ TP.HCM đến Hà Nội qua các điểm trung chuyển',
            'route__estimated_distance': '1,650 km',
            'route__estimated_duration': '48 hours',
            'route__terminals': [
                {
                    'id': 1,
                    'name': 'Terminal TP.HCM',
                    'city_province': 'TP.HCM',
                    'city_county_district': 'Quận 1',
                    'ward_town_township': 'Phường Bến Nghé'
                },
                {
                    'id': 2,
                    'name': 'Terminal Đà Nẵng',
                    'city_province': 'Đà Nẵng',
                    'city_county_district': 'Quận Hải Châu',
                    'ward_town_township': 'Phường Hải Châu 1'
                },
                {
                    'id': 3,
                    'name': 'Terminal Hà Nội',
                    'city_province': 'Hà Nội',
                    'city_county_district': 'Quận Ba Đình',
                    'ward_town_township': 'Phường Phúc Xá'
                }
            ],
            
            # Delivery Items
            'items': [
                {
                    'id': 1,
                    'timestamp': '2025-08-18T08:00:00Z',
                    'is_drone_approved': True,
                    'is_delivered_by_drone': True,
                    'drone_arrived_at': '2025-08-18T09:30:00Z',
                    'is_arrived': True,
                    'arrived_at': '2025-08-18T09:30:00Z',
                    'is_delivered': True,
                    'delivered_at': '2025-08-18T10:30:00Z',
                    'drone__id': 15,
                    'drone__name': 'Drone X-15',
                    'drone__model': 'X-Series',
                    'drone__status': 'active',
                    'order_item__id': 101,
                    'order_item__name': 'Package A',
                    'order_item__description': 'Electronics package',
                    'order_item__quantity': 1
                },
                {
                    'id': 2,
                    'timestamp': '2025-08-18T08:15:00Z',
                    'is_drone_approved': True,
                    'is_delivered_by_drone': True,
                    'drone_arrived_at': '2025-08-18T09:45:00Z',
                    'is_arrived': True,
                    'arrived_at': '2025-08-18T09:45:00Z',
                    'is_delivered': True,
                    'delivered_at': '2025-08-18T10:45:00Z',
                    'drone__id': 15,
                    'drone__name': 'Drone X-15',
                    'drone__model': 'X-Series',
                    'drone__status': 'active',
                    'order_item__id': 102,
                    'order_item__name': 'Package B',
                    'order_item__description': 'Documents package',
                    'order_item__quantity': 2
                }
            ],

            # Checklist data grouped by category
            'checklist_by_category': {
                'Controller Check': [
                    {
                        'item_name': 'Kiểm tra điều khiển từ xa',
                        'is_checked': False,
                        'category_code': 'controller-check',
                        'checked_by_drones': []
                    },
                    {
                        'item_name': 'Kiểm tra kết nối Bluetooth',
                        'is_checked': False,
                        'category_code': 'controller-check',
                        'checked_by_drones': []
                    }
                ],
                'Pre-flight Check': [
                    {
                        'item_name': 'Kiểm tra cánh quạt',
                        'is_checked': False,
                        'category_code': 'pre-flight-check',
                        'checked_by_drones': []
                    }
                ],
                'Weather Check': [
                    {
                        'item_name': 'Kiểm tra điều kiện thời tiết',
                        'is_checked': True,
                        'category_code': 'weather-check',
                        'checked_by_drones': [15]
                    },
                    {
                        'item_name': 'Kiểm tra tốc độ gió',
                        'is_checked': False,
                        'category_code': 'weather-check',
                        'checked_by_drones': []
                    }
                ]
            },

            # Additional metadata
            'total_checklist_items': 5,
            'checked_checklist_items': 1,
            'unchecked_checklist_items': 4,
            'completion_percentage': 20.0,

            # Operation details
            'operation_start_time': '2025-08-18 08:00:00',
            'operation_end_time': '2025-08-18 10:30:00',
            'total_distance': '45.2 km',
            'total_duration': '2h 30m',
            'weather_conditions': 'Clear, Wind: 5-10 km/h',
            'temperature': '25°C',
            'humidity': '65%',

            # Additional data
            'start_delivery_at': '2025-08-18 08:00:00',
            'delivered_at': '2025-08-18 10:00:00',
            'drone__wind_resistance': 10,
            'drone__weight': 10,
            'drone__weight_capacity': 10,
            'drone__temperature': 10
        }

