"""
Service layer for Surveillance Dashboard operations.
Optimized for high performance with efficient queries.
"""

import json
import logging
import threading
import hashlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time, timezone as dt_timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict
from django.db.models import Count, Q, Prefetch
from django.db.models.functions import Coalesce
from django.http import HttpRequest
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.core.cache import cache
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from dashboard.repository.dashboard_repository import DashboardRepository
from dashboard.models import WeatherSetting
from devices.models import Device, DeviceStatus
from surveillance.models import SurveillanceProfile, SurveillanceStatus, VideoAnalysis, SurveyMission, MissionWaypoint, SurveillanceProfileDrone
from stream_monitors.utils.minio_client import minio_client
from common.constant import MESSAGE_ENUM, get_message
from core.common.constant import Language
from core.user.models import CoreUser, UserSettings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import pytz

logger = logging.getLogger(__name__)

# Thread lock to prevent concurrent execution of detection processing
_detection_processing_lock = threading.Lock()


class SurveillanceDashboardService:
    """Service layer for Surveillance Dashboard operations."""

    @staticmethod
    def get_weather_setting(request: HttpRequest) -> Dict[str, Any]:
        """
        Get weather setting.
        Returns weather setting.
        """
        weather_setting = WeatherSetting.objects.filter(is_surveillance_dashboard=True, deleted__isnull=True, created_by = request.user).order_by("-id").first()
        if not weather_setting:
            return None
        return {
            'id': weather_setting.id,
            'latitude': weather_setting.latitude,
            'longitude': weather_setting.longitude,
            'address': weather_setting.address,
            'is_surveillance_dashboard': weather_setting.is_surveillance_dashboard,
        }

    @staticmethod
    def get_drone_status_overview() -> Dict[str, Any]:
        """
        Get drone status overview statistics.
        Returns counts for: Active, On Mission, Warning, Inactive
        
        Performance optimized with single aggregation query.
        
        Returns:
            Dict containing status counts
        """
        try:
            # Get status objects once (cached by Django)
            active_statuses = DeviceStatus.objects.filter(
                code__in=['available', 'operational']
            ).values_list('id', flat=True)
            
            on_mission_status = DeviceStatus.objects.filter(
                code='on_mission'
            ).values_list('id', flat=True).first()
            
            warning_status = DeviceStatus.objects.filter(
                code='warning'
            ).values_list('id', flat=True).first()
            
            inactive_status = DeviceStatus.objects.filter(
                code='inactive'
            ).values_list('id', flat=True).first()

            # Single optimized query with aggregation
            # Only count active devices (active=True)
            queryset = Device.objects.all()
            
            # Use aggregation for better performance
            aggregation_filters = {
                'active': Q(status_id__in=list(active_statuses)),
            }
            
            if on_mission_status:
                aggregation_filters['on_mission'] = Q(status_id=on_mission_status)
            else:
                aggregation_filters['on_mission'] = Q(pk__isnull=True)  # Always false
            
            if warning_status:
                aggregation_filters['warning'] = Q(status_id=warning_status)
            else:
                aggregation_filters['warning'] = Q(pk__isnull=True)  # Always false
            
            if inactive_status:
                aggregation_filters['inactive'] = Q(status_id=inactive_status)
            else:
                aggregation_filters['inactive'] = Q(pk__isnull=True)  # Always false
            
            status_counts = queryset.aggregate(
                active=Count('id', filter=aggregation_filters['active']),
                on_mission=Count('id', filter=aggregation_filters['on_mission']),
                warning=Count('id', filter=aggregation_filters['warning']),
                inactive=Count('id', filter=aggregation_filters['inactive']),
            )

            return {
                "active": status_counts.get('active', 0) or 0,
                "on_mission": status_counts.get('on_mission', 0) or 0,
                "warning": status_counts.get('warning', 0) or 0,
                "inactive": status_counts.get('inactive', 0) or 0,
            }
        except Exception as e:
            logger.error(f"Error getting drone status overview: {str(e)}", exc_info=True)
            return {
                "active": 0,
                "on_mission": 0,
                "warning": 0,
                "inactive": 0,
            }

    @staticmethod
    def get_daily_profile_overview(selected_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get daily surveillance profile overview statistics.
        Returns counts for: Total, Completed, Processing
        
        Performance optimized with date filtering and aggregation.
        
        Args:
            selected_date: UTC datetime string in ISO 8601 format (e.g., '2025-12-08T17:00:00+00:00')
                          Will be converted to system timezone before extracting date.
                          If None, uses today's date in system timezone
        
        Returns:
            Dict containing profile counts and date
        """
        try:
            # Parse UTC datetime string (ISO 8601 format)
            # Format: 2025-12-08T17:00:00+00:00
            if selected_date:
                try:
                    # Parse UTC datetime string
                    dt_utc = parse_datetime(selected_date)
                    if dt_utc is None:
                        # Try with fromisoformat as fallback
                        dt_utc = datetime.fromisoformat(selected_date.replace('Z', '+00:00'))
                    
                    # Ensure datetime is timezone-aware
                    if timezone.is_naive(dt_utc):
                        dt_utc = timezone.make_aware(dt_utc, dt_timezone.utc)
                    
                    # Convert UTC to system timezone
                    dt_system = timezone.localtime(dt_utc)
                    
                    # Extract date from system timezone
                    target_date = dt_system.date()
                except (ValueError, AttributeError, TypeError) as e:
                    logger.warning(f"Invalid UTC datetime format: {selected_date}, error: {str(e)}, using today")
                    target_date = timezone.now().date()
            else:
                target_date = timezone.now().date()

            # Get status objects once
            completed_status = SurveillanceStatus.objects.filter(
                code='completed'
            ).values_list('id', flat=True).first()
            
            processing_statuses = SurveillanceStatus.objects.filter(
                code__in=['in_progress', 'approved', 'pending_device_check']
            ).values_list('id', flat=True)

            # Single optimized query with date filtering and aggregation
            queryset = SurveillanceProfile.objects.annotate(effective_start_time=Coalesce('actual_start_time', 'start_time')).filter(
                effective_start_time__date=target_date
            ).exclude(status__code__in=['rejected', 'cancelled'])

            # Use aggregation for better performance
            profile_counts = queryset.aggregate(
                total=Count('id'),
                completed=Count(
                    'id',
                    filter=Q(status_id=completed_status)
                ) if completed_status else 0,
                processing=Count(
                    'id',
                    filter=Q(status_id__in=list(processing_statuses))
                ),
            )

            return {
                "date": target_date.strftime('%m-%d-%Y'),
                "total": profile_counts.get('total', 0) or 0,
                "completed": profile_counts.get('completed', 0) or 0,
                "processing": profile_counts.get('processing', 0) or 0,
            }
        except Exception as e:
            logger.error(f"Error getting daily profile overview: {str(e)}", exc_info=True)
            today = timezone.now().date()
            return {
                "date": today.strftime('%m-%d-%Y'),
                "total": 0,
                "completed": 0,
                "processing": 0,
            }

    @staticmethod
    def _read_json_file(file_path: str) -> Optional[List[Dict[str, Any]]]:
        """Read JSON file from MinIO. Returns None if error."""
        try:
            return minio_client.get_json(file_path)
        except Exception as e:
            logger.warning(f"Error reading JSON file {file_path}: {str(e)}")
            return None

    @staticmethod
    def _process_detection_data(detection_data: List[Dict[str, Any]], start_datetime: datetime, end_datetime: datetime, drone_name: str = 'Unknown') -> Tuple[Counter, List[Dict[str, Any]]]:
        """
        Process detection data and count by label.
        Also collects detailed detection information for messages.
        
        Args:
            detection_data: List of detection records
            start_datetime: Start datetime for filtering
            end_datetime: End datetime for filtering
            drone_name: Name of the drone that detected this
        
        Returns:
            Tuple of (Counter with label counts, List of detailed detection records)
        """
        label_counter = Counter()
        detailed_detections = []
        
        # Map label to category
        label_to_category = {
            'smoke': 'fire_smoke',
            'fire': 'fire_smoke',
            'animal': 'animals',
            'human': 'human',
            'person': 'human',
            'vehicle': 'vehicle',
            'car': 'vehicle',
            'truck': 'vehicle',
            'anomaly': 'anomaly',
        }
        
        # Process all detections in one pass
        for record in detection_data:
            try:
                # Parse datetime from record
                record_datetime_str = record.get('datetime', '')
                if not record_datetime_str:
                    continue
                
                # Parse datetime (format: "2025-11-11 04:21:43")
                try:
                    record_dt = datetime.strptime(record_datetime_str, '%Y-%m-%d %H:%M:%S')
                    # Make timezone-aware (assuming UTC)
                    if timezone.is_naive(record_dt):
                        record_dt = timezone.make_aware(record_dt, dt_timezone.utc)
                    
                    # Convert to system timezone for comparison
                    record_dt_system = timezone.localtime(record_dt)
                    start_dt_system = timezone.localtime(start_datetime)
                    end_dt_system = timezone.localtime(end_datetime)
                    
                    # Filter by date range
                    if not (start_dt_system <= record_dt_system <= end_dt_system):
                        continue
                except (ValueError, TypeError):
                    # If datetime parsing fails, skip this record
                    continue
                
                # Process detections in this record
                detections = record.get('detections', [])
                if not detections:
                    continue
                # Try to extract preview image if present
                image_url = (
                    record.get('image_url')
                    or record.get('image')
                    or record.get('thumbnail')
                    or record.get('thumb_url')
                    or record.get('file_url')
                    or record.get('detected_image_path')
                )
                
                # Group detections by category for this record
                record_categories = Counter()
                for det in detections:
                    label = det.get('label', '').lower()
                    if label:
                        category = label_to_category.get(label, 'anomaly')
                        record_categories[category] += 1
                        label_counter[category] += 1
                
                # Store detailed detection info
                if record_categories:
                    obj = minio_client.get_metadata(image_url)
                    detailed_detections.append({
                        'datetime': record_dt_system,
                        'date': record_dt_system.date(),
                        'categories': dict(record_categories),
                        'drone_name': drone_name,
                        'image_url': image_url,
                        'image_lat':obj.get('x-amz-meta-gps-latitude') or record.get('drone_location',{}).get('latitude'),
                        'image_lon':obj.get('x-amz-meta-gps-longitude') or record.get('drone_location',{}).get('longitude')

                    })
                    
            except Exception as e:
                logger.warning(f"Error processing detection record: {str(e)}")
                continue
        
        return label_counter, detailed_detections

    @staticmethod
    def _get_relative_time(detection_datetime: datetime, user_language: str = Language.EN) -> str:
        """
        Calculate relative time string like "10 minutes ago" in user's language.
        
        Args:
            detection_datetime: Detection datetime in system timezone
            user_language: User's language code (default: Language.EN)
        
        Returns:
            Relative time string in user's language (e.g., "10 minutes ago", "2 hours ago", "1 day ago")
        """
        now = timezone.now()
        diff = now - detection_datetime
        
        # Get translations for user's language
        just_now = MESSAGE_ENUM.RELATIVE_TIME_JUST_NOW.get(user_language, MESSAGE_ENUM.RELATIVE_TIME_JUST_NOW[Language.EN])
        ago = MESSAGE_ENUM.RELATIVE_TIME_AGO.get(user_language, MESSAGE_ENUM.RELATIVE_TIME_AGO[Language.EN])
        
        if diff.total_seconds() < 60:
            seconds = int(diff.total_seconds())
            if seconds <= 1:
                return just_now
            second_word = MESSAGE_ENUM.RELATIVE_TIME_SECOND.get(user_language, MESSAGE_ENUM.RELATIVE_TIME_SECOND[Language.EN]) if seconds == 1 else MESSAGE_ENUM.RELATIVE_TIME_SECONDS.get(user_language, MESSAGE_ENUM.RELATIVE_TIME_SECONDS[Language.EN])
            return f"{seconds} {second_word} {ago}"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            minute_word = MESSAGE_ENUM.RELATIVE_TIME_MINUTE.get(user_language, MESSAGE_ENUM.RELATIVE_TIME_MINUTE[Language.EN]) if minutes == 1 else MESSAGE_ENUM.RELATIVE_TIME_MINUTES.get(user_language, MESSAGE_ENUM.RELATIVE_TIME_MINUTES[Language.EN])
            return f"{minutes} {minute_word} {ago}"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            hour_word = MESSAGE_ENUM.RELATIVE_TIME_HOUR.get(user_language, MESSAGE_ENUM.RELATIVE_TIME_HOUR[Language.EN]) if hours == 1 else MESSAGE_ENUM.RELATIVE_TIME_HOURS.get(user_language, MESSAGE_ENUM.RELATIVE_TIME_HOURS[Language.EN])
            return f"{hours} {hour_word} {ago}"
        elif diff.days < 7:
            days = diff.days
            day_word = MESSAGE_ENUM.RELATIVE_TIME_DAY.get(user_language, MESSAGE_ENUM.RELATIVE_TIME_DAY[Language.EN]) if days == 1 else MESSAGE_ENUM.RELATIVE_TIME_DAYS.get(user_language, MESSAGE_ENUM.RELATIVE_TIME_DAYS[Language.EN])
            return f"{days} {day_word} {ago}"
        elif diff.days < 30:
            weeks = int(diff.days / 7)
            week_word = MESSAGE_ENUM.RELATIVE_TIME_WEEK.get(user_language, MESSAGE_ENUM.RELATIVE_TIME_WEEK[Language.EN]) if weeks == 1 else MESSAGE_ENUM.RELATIVE_TIME_WEEKS.get(user_language, MESSAGE_ENUM.RELATIVE_TIME_WEEKS[Language.EN])
            return f"{weeks} {week_word} {ago}"
        else:
            months = int(diff.days / 30)
            month_word = MESSAGE_ENUM.RELATIVE_TIME_MONTH.get(user_language, MESSAGE_ENUM.RELATIVE_TIME_MONTH[Language.EN]) if months == 1 else MESSAGE_ENUM.RELATIVE_TIME_MONTHS.get(user_language, MESSAGE_ENUM.RELATIVE_TIME_MONTHS[Language.EN])
            return f"{months} {month_word} {ago}"

    @staticmethod
    def _get_category_color(category: str) -> str:
        """
        Get color code for detection category.
        Colors match the notification style: warning (orange) for alerts, success (green) for normal.
        
        Args:
            category: Detection category
        
        Returns:
            Hex color code
        """
        color_map = {
            'fire_smoke': '#FF6B35',  # Orange/red for fire/smoke (warning)
            'animals': '#4CAF50',     # Green for animals (info)
            'human': '#FF9800',        # Orange for human detection (warning)
            'vehicle': '#2196F3',      # Blue for vehicle (info)
            'anomaly': '#F44336',      # Red for anomaly (critical)
        }
        return color_map.get(category, '#757575')  # Default gray

    @staticmethod
    def _get_category_icon_type(category: str) -> str:
        """
        Get icon type for detection category.
        
        Args:
            category: Detection category
        
        Returns:
            Icon type: 'warning' or 'info'
        """
        warning_categories = ['fire_smoke', 'human', 'anomaly']
        return 'warning' if category in warning_categories else 'info'

    @staticmethod
    def _get_user_format_settings(user: Optional[CoreUser] = None) -> Dict[str, Any]:
        """
        Get user format settings (date format, time format, timezone) optimized with single query.
        Uses select_related to avoid N+1 queries.
        
        Args:
            user: CoreUser object (optional, will try to get from request context if not provided)
        
        Returns:
            Dictionary with keys: date_format_str, time_format_str, user_timezone
        """
        # Try to get user from request context if not provided
        if user is None:
            try:
                from core.middleware.refresh_token import get_current_request
                request = get_current_request()
                if request and hasattr(request, 'user') and request.user:
                    user = request.user
            except Exception:
                pass
        
        # Default formats
        date_format_str = '%Y-%m-%d'
        time_format_str = '%H:%M:%S'
        user_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
        
        if not user:
            return {
                'date_format_str': date_format_str,
                'time_format_str': time_format_str,
                'user_timezone': user_timezone,
            }
        
        # Get user settings with select_related to optimize query
        user_settings = None
        try:
            if hasattr(user, 'user_settings'):
                user_settings = user.user_settings
            elif hasattr(user, 'usersettings'):
                user_settings = user.usersettings
            else:
                # Optimize query with select_related
                user_settings = UserSettings.objects.select_related(
                    'date_format', 'time_format'
                ).filter(user=user).first()
        except Exception:
            pass
        
        # Get timezone from user (already loaded if user was prefetched)
        if hasattr(user, 'timezone') and user.timezone:
            try:
                tz_code = getattr(user.timezone, 'code', None) or getattr(user.timezone, 'name', None)
                if tz_code:
                    user_timezone = pytz.timezone(tz_code)
            except Exception:
                pass
        
        # Get user's language for locale-based defaults
        if hasattr(user, 'language') and user.language:
            lang_code = getattr(user.language, 'code', 'en')
            if lang_code == 'ko':
                date_format_str = '%Y-%m-%d'
            elif lang_code == 'th':
                date_format_str = '%d/%m/%Y'
        
        # Get date format from user settings (already loaded via select_related)
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
        
        return {
            'date_format_str': date_format_str,
            'time_format_str': time_format_str,
            'user_timezone': user_timezone,
        }

    @staticmethod
    def _replace_month_names_with_translations(formatted_str: str, month_number: int, user_language: str, is_abbreviation: bool = False) -> str:
        """
        Replace month names in formatted string with translations based on user language.
        
        Args:
            formatted_str: Formatted date string that may contain month names
            month_number: Month number (1-12)
            user_language: User's language code
            is_abbreviation: Whether to use abbreviated month names (%b) or full names (%B)
        
        Returns:
            String with month names replaced by translations
        """
        # Month name mappings
        month_full_names = {
            1: MESSAGE_ENUM.MONTH_JANUARY,
            2: MESSAGE_ENUM.MONTH_FEBRUARY,
            3: MESSAGE_ENUM.MONTH_MARCH,
            4: MESSAGE_ENUM.MONTH_APRIL,
            5: MESSAGE_ENUM.MONTH_MAY,
            6: MESSAGE_ENUM.MONTH_JUNE,
            7: MESSAGE_ENUM.MONTH_JULY,
            8: MESSAGE_ENUM.MONTH_AUGUST,
            9: MESSAGE_ENUM.MONTH_SEPTEMBER,
            10: MESSAGE_ENUM.MONTH_OCTOBER,
            11: MESSAGE_ENUM.MONTH_NOVEMBER,
            12: MESSAGE_ENUM.MONTH_DECEMBER,
        }
        
        month_abbr_names = {
            1: MESSAGE_ENUM.MONTH_ABBR_JANUARY,
            2: MESSAGE_ENUM.MONTH_ABBR_FEBRUARY,
            3: MESSAGE_ENUM.MONTH_ABBR_MARCH,
            4: MESSAGE_ENUM.MONTH_ABBR_APRIL,
            5: MESSAGE_ENUM.MONTH_ABBR_MAY,
            6: MESSAGE_ENUM.MONTH_ABBR_JUNE,
            7: MESSAGE_ENUM.MONTH_ABBR_JULY,
            8: MESSAGE_ENUM.MONTH_ABBR_AUGUST,
            9: MESSAGE_ENUM.MONTH_ABBR_SEPTEMBER,
            10: MESSAGE_ENUM.MONTH_ABBR_OCTOBER,
            11: MESSAGE_ENUM.MONTH_ABBR_NOVEMBER,
            12: MESSAGE_ENUM.MONTH_ABBR_DECEMBER,
        }
        
        # Get the appropriate month name dictionary
        month_dict = month_abbr_names if is_abbreviation else month_full_names
        
        # Get English month name (default from strftime) and translated version
        english_month_dict = month_dict.get(month_number, {})
        english_month = english_month_dict.get(Language.EN, '')
        
        if not english_month:
            return formatted_str
        
        # Get translated month name
        translated_month = english_month_dict.get(user_language, english_month_dict.get(Language.EN, english_month))
        
        # If language is English, no replacement needed
        if user_language == Language.EN:
            return formatted_str
        
        # Replace English month name with translated version
        # Handle different capitalization: full match, lowercase, capitalized, uppercase
        result = formatted_str
        
        # Full match (most common case)
        if english_month in result:
            result = result.replace(english_month, translated_month)
        
        # Lowercase version
        if english_month.lower() in result.lower():
            # Preserve original capitalization context
            import re
            pattern = re.compile(re.escape(english_month.lower()), re.IGNORECASE)
            result = pattern.sub(translated_month, result)
        
        return result

    @staticmethod
    def _format_datetime_by_user_settings(
        dt: datetime,
        date_format_str: str,
        time_format_str: str,
        user_timezone: pytz.BaseTzInfo,
        user_language: str = Language.EN
    ) -> str:
        """
        Format datetime using provided format strings and timezone.
        Supports multilingual month names when format contains %B or %b.
        This method is optimized to avoid repeated queries - format settings should be
        obtained once via _get_user_format_settings() and reused.
        
        Args:
            dt: datetime object to format
            date_format_str: Date format string (e.g., '%Y-%m-%d', '%B %d, %Y')
            time_format_str: Time format string (e.g., '%H:%M:%S')
            user_timezone: pytz timezone object
            user_language: User's language code (default: Language.EN)
        
        Returns:
            Formatted datetime string according to provided settings with translated month names
        """
        if dt is None:
            return ''
        
        try:
            # Ensure datetime is timezone-aware
            if dt.tzinfo is None:
                # If naive, assume it's in UTC
                dt = pytz.UTC.localize(dt)
            elif dt.tzinfo != pytz.UTC:
                # Convert to UTC first if not already UTC
                dt = dt.astimezone(pytz.UTC)
            
            # Convert to user timezone
            localized = dt.astimezone(user_timezone)
            
            # Check if format contains month names
            has_full_month = '%B' in date_format_str
            has_abbr_month = '%b' in date_format_str
            
            # Format date and time parts
            date_part = localized.date().strftime(date_format_str)
            time_part = localized.time().strftime(time_format_str)
            
            # Replace month names with translations if needed
            if has_full_month or has_abbr_month:
                month_number = localized.month
                if has_full_month:
                    date_part = SurveillanceDashboardService._replace_month_names_with_translations(
                        date_part, month_number, user_language, is_abbreviation=False
                    )
                if has_abbr_month:
                    date_part = SurveillanceDashboardService._replace_month_names_with_translations(
                        date_part, month_number, user_language, is_abbreviation=True
                    )
            
            result = f"{date_part} {time_part}"
            
            return result
        except Exception as e:
            logger.warning(f"Error formatting datetime with user settings: {str(e)}, falling back to ISO format")
            # Fallback to ISO format
            return dt.isoformat() if isinstance(dt, datetime) else str(dt)

    @staticmethod
    def _generate_detection_messages(detailed_detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate user-friendly messages from detailed detection data.
        Format: "Drone {drone_name} detected {detect_name} at {time}"
        Messages are returned in user's preferred language (from request context).
        
        Args:
            detailed_detections: List of detection records with datetime, categories, and drone_name
        
        Returns:
            List of message dictionaries, each as a separate notification item with message in user's language
        """
        if not detailed_detections:
            return []
        
        messages = []
        
        # Map category to message template enum
        category_template_map = {
            'fire_smoke': MESSAGE_ENUM.DETECTION_MESSAGE_TEMPLATE_FIRE_SMOKE,
            'animals': MESSAGE_ENUM.DETECTION_MESSAGE_TEMPLATE_ANIMALS,
            'human': MESSAGE_ENUM.DETECTION_MESSAGE_TEMPLATE_HUMAN,
            'vehicle': MESSAGE_ENUM.DETECTION_MESSAGE_TEMPLATE_VEHICLE,
            'anomaly': MESSAGE_ENUM.DETECTION_MESSAGE_TEMPLATE_ANOMALY,
        }
        
        # Map category to detection name enum
        category_name_map = {
            'fire_smoke': MESSAGE_ENUM.DETECTION_NAME_FIRE_SMOKE,
            'animals': MESSAGE_ENUM.DETECTION_NAME_ANIMALS,
            'human': MESSAGE_ENUM.DETECTION_NAME_HUMAN,
            'vehicle': MESSAGE_ENUM.DETECTION_NAME_VEHICLE,
            'anomaly': MESSAGE_ENUM.DETECTION_NAME_ANOMALY,
        }
        
        # Get user and language from request context
        user = None
        user_language = Language.EN
        try:
            from core.middleware.refresh_token import get_current_request
            request = get_current_request()
            if request and hasattr(request, 'user') and request.user:
                user = request.user
                if hasattr(request.user, 'language') and request.user.language:
                    user_language = request.user.language.code
        except Exception:
            pass
        
        # Default to English if no language preference found
        if user_language not in [Language.EN, Language.KR, Language.TH]:
            user_language = Language.EN
        
        # Get user format settings once (optimized query with select_related)
        format_settings = SurveillanceDashboardService._get_user_format_settings(user)
        date_format_str = format_settings['date_format_str']
        time_format_str = format_settings['time_format_str']
        user_timezone = format_settings['user_timezone']
        
        # Create individual messages for each detection record
        for det in detailed_detections:
            detection_datetime = det['datetime']
            categories = det['categories']
            drone_name = det.get('drone_name', 'Unknown')
            image_url = det.get('image_url')
            if not image_url:
                continue
            # Format datetime according to user settings (date format, time format, timezone)
            # Format settings are already loaded once above, no additional queries
            # Include user_language for multilingual month names
            time_str = SurveillanceDashboardService._format_datetime_by_user_settings(
                detection_datetime,
                date_format_str,
                time_format_str,
                user_timezone,
                user_language
            )
            
            # Create a separate message for each category in this detection
            for category, count in categories.items():
                # Get message template and detection name for user's language
                message_template = category_template_map.get(category, MESSAGE_ENUM.DETECTION_MESSAGE_TEMPLATE_ANOMALY)
                detect_name_dict = category_name_map.get(category, MESSAGE_ENUM.DETECTION_NAME_ANOMALY)
                
                # Get template and detection name in user's language
                template = message_template.get(user_language, message_template[Language.EN])
                detect_name = detect_name_dict.get(user_language, detect_name_dict[Language.EN])
                
                # Format message in user's language
                message_text = template.format(
                    drone_name=drone_name,
                    detect_name=detect_name,
                    time=time_str
                )
                
                date_str = detection_datetime.strftime('%Y-%m-%d')
                
                # Calculate relative time in user's language
                relative_time = SurveillanceDashboardService._get_relative_time(detection_datetime, user_language)
                
                # Get color and icon type
                color = SurveillanceDashboardService._get_category_color(category)
                icon_type = SurveillanceDashboardService._get_category_icon_type(category)
                
                messages.append({
                    "id": f"{detection_datetime.isoformat()}_{category}_{count}",  # Unique ID
                    "message": message_text,  # Message in user's preferred language
                    "category": category,
                    "count": count,
                    "datetime": detection_datetime.isoformat(),
                    "date": date_str,
                    "relative_time": relative_time,
                    "color": color,
                    "icon_type": icon_type,
                    "image_url": image_url,
                    "image_lat":det.get('image_lat'),
                    "image_lng":det.get('image_lon')
                })
        
        # Sort by datetime (newest first)
        messages.sort(key=lambda x: x['datetime'], reverse=True)
        
        return messages

    @staticmethod
    def _fetch_detection_data(start_date: str, end_date: str, limit_files: Optional[int] = None) -> Tuple[List[Dict[str, Any]], datetime, datetime]:
        """
        Internal method to fetch detection data from JSON files.
        Optimized for performance with early filtering and batch processing.
        
        Args:
            start_date: UTC datetime string in ISO 8601 format
            end_date: UTC datetime string in ISO 8601 format
            limit_files: Optional limit on number of files to process (for performance)
        
        Returns:
            Tuple of (detailed_detections, start_dt, end_dt)
        """
        # Parse UTC datetime strings
        start_dt = parse_datetime(start_date)
        if start_dt is None:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        
        end_dt = parse_datetime(end_date)
        if end_dt is None:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Ensure timezone-aware
        if timezone.is_naive(start_dt):
            start_dt = timezone.make_aware(start_dt, dt_timezone.utc)
        if timezone.is_naive(end_dt):
            end_dt = timezone.make_aware(end_dt, dt_timezone.utc)
        
        # Convert to system timezone for comparison
        start_dt_system = timezone.localtime(start_dt)
        end_dt_system = timezone.localtime(end_dt)
        
        # Optimized query: Only get files that definitely overlap with date range
        # Use select_related/prefetch_related if needed, and limit results
        video_analyses_qs = VideoAnalysis.objects.filter(
            analysis_path__isnull=False,
            analysis_path__gt='',
            deleted__isnull=True,
            profile_device__isnull=False,
            drone_name__isnull=False
        ).filter(
            # More precise date filtering - only files that definitely overlap
            Q(created_at__lte=end_dt_system, created_at__gte=start_dt_system)
        ).order_by('-start_time')  # Order by newest first
        
        # Get analysis_paths with drone_name (must be before slice)
        video_analyses_data = video_analyses_qs.values('analysis_path','drone_name').distinct()
       
        # Create mapping of analysis_path to drone_name
        file_to_drone = {}
        file_paths = []
        for item in video_analyses_data:
            analysis_path = item['analysis_path']
            drone_name = item.get('drone_name') or 'Unknown'
            if analysis_path not in file_to_drone:
                file_to_drone[analysis_path] = drone_name
                file_paths.append(analysis_path)
        # Limit number of files if specified (for performance)
        if limit_files:
            file_paths = file_paths[:limit_files]
        
        if not file_paths:
            return [], start_dt, end_dt
        
        # Optimize: Process files in smaller batches to avoid memory issues
        all_detailed_detections = []
        batch_size = 50  # Process 50 files at a time
        max_workers = min(10, batch_size)
        
        for i in range(0, len(file_paths), batch_size):
            batch_files = file_paths[i:i + batch_size]
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(
                        SurveillanceDashboardService._read_json_file,
                        file_path
                    ): file_path
                    for file_path in batch_files
                }
                
                for future in as_completed(future_to_file):
                    file_url = future_to_file[future]
                    drone_name = file_to_drone.get(file_url, 'Unknown')
                    try:
                        # Add timeout to prevent hanging (30 seconds per file)
                        json_data = future.result(timeout=30)
                        if json_data and isinstance(json_data, list):
                            _, detailed_detections = SurveillanceDashboardService._process_detection_data(
                                json_data, start_dt, end_dt, drone_name
                            )
                            if detailed_detections:
                                all_detailed_detections.extend(detailed_detections)
                    except Exception as e:
                        logger.warning(f"Error processing file {file_url}: {str(e)}")
                        continue
        
        return all_detailed_detections, start_dt, end_dt

    @staticmethod
    def _paginate_list(items: List[Any], page: int, page_size: int) -> Dict[str, Any]:
        """
        Paginate a list of items.
        
        Args:
            items: List of items to paginate
            page: Page number (1-indexed)
            page_size: Number of items per page
        
        Returns:
            Dict with paginated items and pagination info
        """
        if not items:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
            }
        
        # Validate and normalize page
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Max 100 items per page
        
        # Calculate pagination
        total = len(items)
        total_pages = (total + page_size - 1) // page_size  # Ceiling division
        page = min(page, total_pages) if total_pages > 0 else 1
        
        # Calculate slice indices
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        
        # Get paginated items
        paginated_items = items[start_index:end_index]
        
        return {
            "items": paginated_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @staticmethod
    def get_abnormal_signs_messages(
        start_date: str, 
        end_date: str, 
        limit: Optional[int] = 100,
        page: Optional[int] = 1,
        page_size: Optional[int] = 10
    ) -> Dict[str, Any]:
        """
        Get detailed detection messages from detection JSON files with pagination.
        Optimized for performance with pagination and batch processing.
        
        **IMPORTANT: This API always fetches fresh data.**
        - Universal cache middleware is bypassed
        - Always returns the latest detection data from files
        - No service-level cache is used
        - Processes synchronously with pagination (no background processing needed)
        
        Uses thread lock to prevent concurrent execution and avoid server crash.
        Prepared for real-time socket integration.
        
        Args:
            start_date: UTC datetime string in ISO 8601 format (e.g., '2025-07-15T00:00:00+00:00')
            end_date: UTC datetime string in ISO 8601 format (e.g., '2025-07-18T23:59:59+00:00')
            limit: Maximum number of messages to fetch (default: 100, for performance)
            page: Page number for pagination (default: 1, 1-indexed)
            page_size: Number of messages per page (default: 10, max: 100)
        
        Returns:
            Dict with paginated 'messages' list, pagination info, and 'status'
        """
        # Always return 5 items per page as per new requirement
        page = max(1, page) if page else 1
        page_size = 5

        # Check active (in-progress) profiles for realtime mode
        now = timezone.now()
        active_profiles_qs = (
            SurveillanceProfile.objects.filter(
                status__code="in_progress",
                actual_start_time__lte=now,
            )
            .filter(Q(actual_end_time__isnull=True))
            .select_related("mission")
            .only("id", "name", "code", "mission__id", "mission__name", "mission__code", "drone_assignments")
        )

        if active_profiles_qs.exists():
            active_profiles = []
            for profile in active_profiles_qs:
                active_profiles.append(
                    {
                        "profile_id": profile.id,
                        "profile_name": profile.name,
                        "profile_code": profile.code,
                        "mission_id": profile.mission.id if profile.mission else None,
                        "mission_name": profile.mission.name if profile.mission else None,
                        "mission_code": getattr(profile.mission, "code", None) if profile.mission else None,
                        "stream_ids": list(profile.drone_assignments.all().values_list('device__unit_id', flat=True)) if profile.drone_assignments.all().exists() else None,
                    }
                )
            return {
                "messages": [],
                "status": "realtime",
                "active_profiles": active_profiles,
                "total": 0,
                "page": 1,
                "page_size": page_size,
                "total_pages": 0,
            }

        # No active profile -> fallback to log mode
        # Use thread lock to prevent concurrent execution.
        _detection_processing_lock.acquire()
        try:
            logger.info(f"Processing messages for {start_date} to {end_date}, page {page}, page_size {page_size}")

            # Parse once (avoid re-parsing twice)
            start_dt = parse_datetime(start_date)
            if start_dt is None and start_date:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))

            end_dt = parse_datetime(end_date)
            if end_dt is None and end_date:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

            # Ensure timezone-aware (assume UTC if naive)
            if start_dt and timezone.is_naive(start_dt):
                start_dt = timezone.make_aware(start_dt, dt_timezone.utc)
            if end_dt and timezone.is_naive(end_dt):
                end_dt = timezone.make_aware(end_dt, dt_timezone.utc)

            # NOTE:
            # FE should send proper UTC timestamps for the selected day in API/system timezone.
            # Backend should NOT shift days here to avoid double-shifting.
            # Performance optimization: Limit number of files processed
            date_range_days = (end_dt - start_dt).days if end_dt and start_dt else 7
            max_files = min(200, max(50, date_range_days * 10))
            
            # Fetch detection data with file limit
            detailed_detections, _, _ = SurveillanceDashboardService._fetch_detection_data(
                start_date, 
                end_date, 
                limit_files=max_files
            )
            
            # Generate messages
            messages = SurveillanceDashboardService._generate_detection_messages(detailed_detections)
            
            # Apply limit (get newest messages)
            if limit and len(messages) > limit:
                messages = messages[:limit]
            
            # Apply pagination with fixed page_size=5
            pagination_result = SurveillanceDashboardService._paginate_list(
                messages, page, page_size
            )
            
            logger.info(f"Processed {len(messages)} messages, returning page {page} with {len(pagination_result['items'])} items")
            
            return {
                "messages": pagination_result["items"],
                "status": "completed",
                "total": pagination_result["total"],
                "page": pagination_result["page"],
                "page_size": pagination_result["page_size"],
                "total_pages": pagination_result["total_pages"],
            }
        except Exception as e:
            logger.error(f"Error getting abnormal signs messages: {str(e)}", exc_info=True)
            return {
                "messages": [],
                "status": "error",
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
            }
        finally:
            # Always release lock
            try:
                _detection_processing_lock.release()
            except:
                pass

    @staticmethod
    def get_today_regions_with_drones(
        page: int = 1,
        page_size: int = 4
    ) -> Dict[str, Any]:
        """
        Get regions that have surveillance missions scheduled for today with their drones.
        Group missions by region and include unique drones per mission.
        
        Args:
            page: Page number for pagination (default: 1, 1-indexed)
            page_size: Number of regions per page (default: 4, max: 100)
        
        Returns:
            Dict with paginated regions and pagination info
        """
        today = timezone.now().date()
        start_of_day = datetime.combine(today, time.min)
        end_of_day = datetime.combine(today, time.max)

        try:
            device_prefetch = Prefetch(
                "drone_assignments",
                queryset=SurveillanceProfileDrone._base_manager.select_related(
                    "device",
                    "device__status",
                ).order_by("order", "id"),
            )

            profiles = (
                SurveillanceProfile.objects.annotate(
                    effective_start_time=Coalesce("actual_start_time", "start_time")
                )
                .filter(
                    effective_start_time__gte=start_of_day,
                    effective_start_time__lte=end_of_day,
                    status__code__in=["completed",  "in_progress"],
                )
                .select_related("mission")
                .prefetch_related(device_prefetch)
                .only(
                    "id",
                    "name",
                    "code",
                    "mission__id",
                    "mission__name",
                    "mission__code",
                    "mission__region",
                )
            )

            if not profiles.exists():
                return {
                    "items": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0,
                }
            regions_map: Dict[str, Dict[str, Any]] = {}

            for profile in profiles:
                mission = profile.mission
                if not mission:
                    continue

                region_name = mission.region or mission.name
                region_entry = regions_map.setdefault(
                    region_name, {"region": region_name, "missions": {}}
                )

                mission_entry = region_entry["missions"].setdefault(
                    mission.id,
                    {
                        "mission_id": mission.id,
                        "mission_name": mission.name,
                        "mission_code": getattr(mission, "code", None),
                        "profile_id": profile.id,
                        "profile_name": profile.name,
                        "profile_code": profile.code,
                        "drones": [],
                        "_drone_ids": set(),
                    },
                )

                assignments = getattr(profile, "drone_assignments", None)
                if assignments is None:
                    continue

                for assignment in assignments.all():
                    device = assignment.device
                    if not device or device.id in mission_entry["_drone_ids"]:
                        continue
                    if device.id not in [d["device_id"] for d in mission_entry["drones"]]:
                        mission_entry["_drone_ids"].add(device.id)
                        mission_entry["drones"].append(
                            {
                                "device_id": device.id,
                                "device_name": device.name,
                                "serial_number": device.serial_number,
                                "unit_id": device.unit_id,
                                "color": device.color,
                                "status_code": device.status.code if device.status else None,
                                "status_name": device.status.name if device.status else None,
                            }
                        )

            # Build simplified result: region and list of unique drones across all missions
            result = []
            for region_name, region_data in regions_map.items():
                drones_map = {}
                for mission_data in region_data["missions"].values():
                    for drone in mission_data.get("drones", []):
                        device_id = drone.get("device_id")
                        if device_id and device_id not in drones_map:
                            drones_map[device_id] = drone
                result.append({
                    "region": region_name,
                    "drones": list(drones_map.values())
                })

            # Apply pagination
            pagination_result = SurveillanceDashboardService._paginate_list(
                result, page, page_size
            )
            
            return {
                "items": pagination_result["items"],
                "total": pagination_result["total"],
                "page": pagination_result["page"],
                "page_size": pagination_result["page_size"],
                "total_pages": pagination_result["total_pages"],
            }
        except Exception as exc:
            logger.error(
                f"Error getting today regions with drones: {str(exc)}", exc_info=True
            )
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
            }

    @staticmethod
    def get_abnormal_signs_overview(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get abnormal signs overview statistics from detection JSON files.
        
        Performance optimized with:
        - Concurrent file reading using ThreadPoolExecutor
        - Counter-based aggregation instead of loops
        - Batch processing
        - Thread lock to prevent concurrent execution and avoid server crash
        
        Args:
            start_date: UTC datetime string in ISO 8601 format (e.g., '2025-07-15T00:00:00+00:00')
            end_date: UTC datetime string in ISO 8601 format (e.g., '2025-07-18T23:59:59+00:00')
        
        Returns:
            Dict containing detection counts by category
        """
        # Use thread lock to prevent concurrent execution.
        # IMPORTANT: We must return full data, so we BLOCK here instead of skipping.
        _detection_processing_lock.acquire()
        try:
            # Parse UTC datetime strings
            start_dt = parse_datetime(start_date) if start_date else None
                
            end_dt = parse_datetime(end_date) if end_date else None
            
            # Ensure timezone-aware
            if start_dt and timezone.is_naive(start_dt):
                start_dt = timezone.make_aware(start_dt, dt_timezone.utc)
            if end_dt and timezone.is_naive(end_dt):
                end_dt = timezone.make_aware(end_dt, dt_timezone.utc)
            
            # Convert to system timezone for comparison
            start_dt_system = timezone.localtime(start_dt) if start_dt else None
            end_dt_system = timezone.localtime(end_dt) if end_dt else None
            
            # Query VideoAnalysis for detection JSON files
            # Filter by analysis_path not null and date range
            video_analyses_qs = VideoAnalysis.objects.filter(
                analysis_path__isnull=False,
                analysis_path__gt='',  # Not empty
                deleted__isnull=True,  # Not deleted
                profile_device__isnull=False,
                drone_name__isnull=False
            )
            # Filter by date range if start_date and end_date are provided
            # If both are None, get all records (no date filtering)
            if start_dt_system and end_dt_system:
                date_filter = Q(
                    Q(created_at__lte=end_dt_system, created_at__gte=start_dt_system) 
                )
                video_analyses_qs = video_analyses_qs.filter(date_filter)
            
            video_analyses = video_analyses_qs.values_list('analysis_path', flat=True).distinct()
            if not video_analyses.exists():
                return {
                    "fire_smoke": 0,
                    "animals": 0,
                    "human": 0,
                    "vehicle": 0,
                    "anomaly": 0,
                }
            

            # Get all file paths - no limit, read ALL files in the date range
            # Use iterator to avoid loading all into memory at once
            # Whether date range is provided or not, we read ALL matching files
            file_paths_iterator = iter(video_analyses)
            
            # Optimize batch size and workers for concurrent processing
            # Larger batch size and more workers for better performance
            batch_size = 200  # Process more files per batch
            max_workers = min(20, batch_size)  # More concurrent workers
            
            # Read files concurrently using ThreadPoolExecutor with batch processing
            # Use iterator to process files in batches without loading all into memory
            all_counters = []
            
            # Prepare datetime range for processing
            process_start_dt = start_dt if start_dt else datetime(1900, 1, 1, tzinfo=dt_timezone.utc)
            process_end_dt = end_dt if end_dt else datetime(2100, 12, 31, 23, 59, 59, tzinfo=dt_timezone.utc)
            
            # Process files in batches using iterator to avoid memory issues
            batch_files = []
            for file_path in file_paths_iterator:
                batch_files.append(file_path)
                if len(batch_files) >= batch_size:
                    # Process this batch
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # Submit file reading tasks for this batch
                        future_to_file = {
                            executor.submit(
                                SurveillanceDashboardService._read_json_file,
                                file_path
                            ): file_path
                            for file_path in batch_files
                        }
                        
                        # Process results as they complete
                        for future in as_completed(future_to_file):
                            file_url = future_to_file[future]
                            try:
                                # Add timeout to prevent hanging (30 seconds per file)
                                json_data = future.result(timeout=30)
                                if json_data and isinstance(json_data, list):
                                    # Process detection data (only counter, no detailed detections)
                                    counter, _ = SurveillanceDashboardService._process_detection_data(
                                        json_data, process_start_dt, process_end_dt, 'Unknown'
                                    )
                                    if counter:
                                        all_counters.append(counter)
                            except Exception as e:
                                logger.warning(f"Error processing file {file_url}: {str(e)}")
                                continue
                    
                    # Clear batch for next iteration
                    batch_files = []
            
            # Process remaining files in the last batch (if any)
            if batch_files:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit file reading tasks for this batch
                    future_to_file = {
                        executor.submit(
                            SurveillanceDashboardService._read_json_file,
                            file_path
                        ): file_path
                        for file_path in batch_files
                    }
                    
                    # Process results as they complete
                    for future in as_completed(future_to_file):
                        file_url = future_to_file[future]
                        try:
                            # Add timeout to prevent hanging (30 seconds per file)
                            json_data = future.result(timeout=30)
                            if json_data and isinstance(json_data, list):
                                # Process detection data (only counter, no detailed detections)
                                counter, _ = SurveillanceDashboardService._process_detection_data(
                                    json_data, process_start_dt, process_end_dt, 'Unknown'
                                )
                                if counter:
                                    all_counters.append(counter)
                        except Exception as e:
                            logger.warning(f"Error processing file {file_url}: {str(e)}")
                            continue
            
            # Combine all counters
            total_counter = sum(all_counters, Counter())
            
            return {
                "fire_smoke": total_counter.get('fire_smoke', 0),
                "animals": total_counter.get('animals', 0),
                "human": total_counter.get('human', 0),
                "vehicle": total_counter.get('vehicle', 0),
                "anomaly": total_counter.get('anomaly', 0),
            }
        except Exception as e:
            logger.error(f"Error getting abnormal signs overview: {str(e)}", exc_info=True)
            return {
                "fire_smoke": 0,
                "animals": 0,
                "human": 0,
                "vehicle": 0,
                "anomaly": 0,
            }
        finally:
            # Always release lock
            try:
                _detection_processing_lock.release()
            except:
                pass

    @staticmethod
    def get_today_profiles_polygon() -> List[Dict[str, Any]]:
        """
        Get polygon data for all surveillance profiles starting today.
        Deduplicates polygons by mission_id - if multiple profiles share the same mission,
        only one polygon is returned.
        
        Performance optimized with:
        - Single query with select_related and prefetch_related
        - Efficient polygon extraction
        - Mission-based deduplication
        
        Returns:
            List of dictionaries containing profile polygon data (unique by mission)
        """
        try:
            # Get today's date in system timezone
            user_tz = DashboardRepository._resolve_user_or_system_timezone()
            current_tz = user_tz if user_tz else timezone.get_current_timezone()
            today = timezone.now().date()
            start_of_day = datetime.combine(today, time.min)
            end_of_day = datetime.combine(today, time.max)
            # Query profiles starting today with optimized prefetch
            # Filter profiles where effective start_time (actual_start_time or start_time) is within today
            # Priority: actual_start_time if exists, otherwise start_time
            profiles = SurveillanceProfile.objects.annotate(
                effective_start_time=Coalesce('actual_start_time', 'start_time')
            ).filter(
                effective_start_time__gte=start_of_day,
                effective_start_time__lte=end_of_day
            ).filter(status__code__in=['completed', 'pending_device_check', 'in_progress']).select_related(
                'mission',
                'status'
            ).prefetch_related(
                'mission__waypoints'
            ).only(
                'id',
                'name',
                'code',
                'color_code',
                'start_time',
                'mission__id',
                'mission__polygon',
                'status__code',
                'status__name'
            )
            if not profiles.exists():
                return []
            
            # Process profiles and extract polygon data
            # Use mission_id as key to avoid duplicates
            polygons_by_mission = {}
            
            for profile in profiles:
                mission = profile.mission
                if not mission or mission.id in polygons_by_mission:
                    # Skip if no mission or mission already processed
                    continue
                
                # Determine if line mission: check if any waypoint has terminal_id
                waypoints = list(mission.waypoints.all())
                is_line_mission = any(wp.terminal_id for wp in waypoints) if waypoints else False
                
                # Alternative check: if no polygon, it's a line mission
                if not is_line_mission and not (mission.polygon and len(mission.polygon) > 0):
                    is_line_mission = True
                
                # Extract polygon/waypoints
                polygon_points = None
                
                if is_line_mission:
                    # For line mission, get waypoints
                    if waypoints:
                        # Sort by order
                        sorted_waypoints = sorted(waypoints, key=lambda wp: wp.order)
                        polygon_points = [
                            [float(wp.latitude), float(wp.longitude)]
                            for wp in sorted_waypoints
                            if wp.latitude and wp.longitude
                        ]
                else:
                    # For polygon mission, get polygon from mission
                    if mission.polygon and isinstance(mission.polygon, list):
                        polygon_points = mission.polygon
                
                # Only add if polygon_points exists and is valid
                if polygon_points and len(polygon_points) > 0:
                    # Store polygon data keyed by mission_id to avoid duplicates
                    polygons_by_mission[mission.id] = {
                        "profile_id": profile.id,
                        "profile_name": profile.name,
                        "profile_code": profile.code,
                        "color_code": profile.color_code or "#1D9BE2",
                        "start_time": profile.start_time.isoformat() if profile.start_time else None,
                        "mission_id": mission.id,
                        "is_line_mission": is_line_mission,
                        "polygon": polygon_points,
                        "status_code": profile.status.code if profile.status else None,
                        "status_name": profile.status.name if profile.status else None,
                    }
            
            # Return list of unique polygons (one per mission)
            return list(polygons_by_mission.values())
            
        except Exception as e:
            logger.error(f"Error getting today profiles polygon: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def broadcast_detection_message(message_data: Dict[str, Any]) -> None:
        """
        Broadcast detection message via WebSocket to connected clients.
        
        **🔌 SOCKET INTEGRATION POINT:**
        Call this method when a new detection is found to push real-time updates to clients.
        
        **Example usage:**
            # When new detection is found (e.g., in VideoAnalysis signal or after processing):
            message = {
                "id": "2025-11-28T18:07:44+07:00_vehicle_1",
                "message": "Drone Drone-001 phát hiện phương tiện vào lúc 18:07",
                "category": "vehicle",
                "count": 1,
                "datetime": "2025-11-28T18:07:44+07:00",
                "date": "2025-11-28",
                "relative_time": "just now",
                "color": "#2196F3",
                "icon_type": "info"
            }
            SurveillanceDashboardService.broadcast_detection_message(message)
        
        **Where to call this:**
        1. In VideoAnalysis post_save signal when analysis_path is updated
        2. After processing new detection JSON file
        3. In background task that processes detection files
        
        Args:
            message_data: Dictionary containing detection message data (same format as returned by _generate_detection_messages)
        """
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("[SURVEILLANCE][DASHBOARD] Channel layer not configured; skip detection message broadcast")
            return
        
        event = {
            "type": "detection_message",
            "timestamp": timezone.now().isoformat(),
            "message": message_data,
        }
        
        try:
            # Broadcast to global surveillance group
            async_to_sync(channel_layer.group_send)("surveillance_profiles_global", event)
            logger.info(f"[SURVEILLANCE][DASHBOARD] Broadcast detection message: {message_data.get('id', 'unknown')}")
        except Exception as exc:
            logger.exception(f"[SURVEILLANCE][DASHBOARD] Failed to broadcast detection message: {exc}")

