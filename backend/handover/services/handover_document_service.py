from core.common.search.dynamic_search import apply_dynamic_filters
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Q, Prefetch, Count, F, OuterRef, Subquery, Value, CharField, Case, When
from django.db.models.functions import Concat, Coalesce
from django.db.models.functions import Cast, Concat
from django.contrib.postgres.aggregates import ArrayAgg
from django.utils import timezone
from typing import Tuple, Optional, List, Dict
from datetime import datetime, date, timedelta, time
from dateutil import parser
import re
import csv
import io
import threading
import uuid
import logging
import pandas as pd
import pytz
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings
from django.http import QueryDict
from handover.models import HandoverDocument, HandoverShift, HandoverContent, HandoverDocumentAcceptor
from core.user.models import UserGroup, CoreUser, UserSettings
from common.tenant_filters import NoTenantGroupError, require_user_group
from core.middleware.refresh_token import get_current_request
from core.file_management.helper import FileHelper
from common.constant import MESSAGE_ENUM, get_message
from handover.tasks import _send_handover_download_notification
from task_status.models import TaskStatus
from task_status.services.task_status_service import TaskStatusService
from safedelete.models import HARD_DELETE
logger = logging.getLogger(__name__)


def parse_date_flexible(date_str: str) -> date:
    """
    Parse date string với nhiều format khác nhau.
    Sử dụng flexible_datetime_parser từ core.common.search.dynamic_search.

    Hỗ trợ các format:
    - YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY
    - Month DD, YYYY (e.g., December 02, 2025)
    - DD Month YYYY (e.g., 02 December 2025)
    - YYYY/MM/DD, YY/MM/DD
    """
    from core.common.search.dynamic_search import flexible_datetime_parser

    if not date_str:
        raise ValueError("Date string is empty")

    # Nếu đã là date object
    if isinstance(date_str, date) and not isinstance(date_str, datetime):
        return date_str
    if isinstance(date_str, datetime):
        return date_str.date()

    # Parse bằng flexible parser
    result = flexible_datetime_parser(date_str)

    if isinstance(result, datetime):
        return result.date()
    elif isinstance(result, date):
        return result
    elif result == date_str:
        # Parser trả về string gốc - không parse được
        raise ValueError(f"Invalid date format: {date_str}. Cannot parse date.")

    raise ValueError(f"Invalid date format: {date_str}. Cannot parse date.")


def parse_date_by_user_format(date_str: str, user: Optional[CoreUser] = None) -> date:
    """
    Parse date string dựa vào user settings (date_format).
    Nếu không có user hoặc parse fail, fallback về parse_date_flexible.

    Args:
        date_str: Date string cần parse
        user: CoreUser object để lấy date_format settings

    Returns:
        date object
    """
    if not date_str:
        raise ValueError("Date string is empty")

    # Nếu đã là date object
    if isinstance(date_str, date) and not isinstance(date_str, datetime):
        return date_str
    if isinstance(date_str, datetime):
        return date_str.date()

    # Nếu có user, thử parse theo user settings
    if user:
        try:
            # Get user settings
            user_settings = None
            if hasattr(user, 'user_settings'):
                user_settings = user.user_settings
            elif hasattr(user, 'usersettings'):
                user_settings = user.usersettings
            else:
                user_settings = UserSettings.objects.filter(user=user).first()

            # Get date format từ user settings
            if user_settings and hasattr(user_settings, 'date_format') and user_settings.date_format:
                if hasattr(user_settings.date_format, 'format_string'):
                    date_format_str = user_settings.date_format.format_string
                    try:
                        # Parse theo format của user
                        parsed_datetime = datetime.strptime(date_str.strip(), date_format_str)
                        logger.debug(f"Parsed '{date_str}' using user format '{date_format_str}': {parsed_datetime.date()}")
                        return parsed_datetime.date()
                    except ValueError:
                        # Parse fail với user format, fall through to flexible parser
                        logger.debug(f"Failed to parse '{date_str}' with user format '{date_format_str}', trying flexible parser")
        except Exception as e:
            logger.debug(f"Error getting user settings for date parsing: {e}, falling back to flexible parser")

    # Fallback về flexible parser
    return parse_date_flexible(date_str)


def parse_date_range_with_validation(start_date_str, end_date_str, user: Optional[CoreUser] = None) -> Tuple[date, date]:
    """
    Parse start_date và end_date cùng lúc, đảm bảo end_date > start_date.
    Sử dụng logic thông minh để tránh parse sai format.

    Logic:
    1. Thử parse với user format trước
    2. Nếu parse được nhưng start_date > end_date, thử parse lại với format khác
    3. Thử các format phổ biến (MM/DD/YYYY, DD/MM/YYYY) và chọn format hợp lý nhất

    Args:
        start_date_str: Start date string
        end_date_str: End date string
        user: CoreUser object để lấy date_format settings

    Returns:
        Tuple (start_date, end_date) với end_date >= start_date
    """
    # Nếu đã là date object
    if isinstance(start_date_str, date) and not isinstance(start_date_str, datetime):
        start_date = start_date_str
    elif isinstance(start_date_str, datetime):
        start_date = start_date_str.date()
    else:
        start_date = None

    if isinstance(end_date_str, date) and not isinstance(end_date_str, datetime):
        end_date = end_date_str
    elif isinstance(end_date_str, datetime):
        end_date = end_date_str.date()
    else:
        end_date = None

    # Nếu cả hai đã là date object và hợp lệ
    if start_date and end_date:
        if start_date > end_date:
            logger.warning(f"start_date ({start_date}) > end_date ({end_date}), swapping dates")
            return end_date, start_date
        return start_date, end_date

    # Get user date format
    user_date_format = None
    if user:
        try:
            user_settings = None
            if hasattr(user, 'user_settings'):
                user_settings = user.user_settings
            elif hasattr(user, 'usersettings'):
                user_settings = user.usersettings
            else:
                user_settings = UserSettings.objects.filter(user=user).first()

            if user_settings and hasattr(user_settings, 'date_format') and user_settings.date_format:
                if hasattr(user_settings.date_format, 'format_string'):
                    user_date_format = user_settings.date_format.format_string
        except Exception:
            pass

    # Danh sách các format để thử (ưu tiên user format trước)
    formats_to_try = []
    if user_date_format:
        formats_to_try.append(user_date_format)

    # Thêm các format phổ biến để thử nếu user format fail
    common_formats = ['%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d', '%m-%d-%Y', '%d-%m-%Y']
    for fmt in common_formats:
        if fmt not in formats_to_try:
            formats_to_try.append(fmt)

    # Thử parse với từng format
    for fmt in formats_to_try:
        try:
            parsed_start = None
            parsed_end = None

            if not start_date and isinstance(start_date_str, str):
                parsed_start = datetime.strptime(start_date_str.strip(), fmt).date()
            else:
                parsed_start = start_date

            if not end_date and isinstance(end_date_str, str):
                parsed_end = datetime.strptime(end_date_str.strip(), fmt).date()
            else:
                parsed_end = end_date

            if parsed_start and parsed_end:
                # Kiểm tra tính hợp lý: end_date >= start_date
                if parsed_start <= parsed_end:
                    logger.debug(f"Successfully parsed date range with format '{fmt}': {parsed_start} to {parsed_end}")
                    return parsed_start, parsed_end
                else:
                    # Parse được nhưng start > end, có thể format sai
                    logger.debug(f"Parsed with format '{fmt}' but start_date ({parsed_start}) > end_date ({parsed_end}), trying next format")
                    continue
        except ValueError:
            # Format này không match, thử format tiếp theo
            continue

    # Nếu tất cả format đều fail, fallback về flexible parser
    logger.warning(f"All date formats failed, falling back to flexible parser for start='{start_date_str}', end='{end_date_str}'")
    if not start_date:
        start_date = parse_date_flexible(start_date_str)
    if not end_date:
        end_date = parse_date_flexible(end_date_str)

    # Đảm bảo end_date >= start_date
    if start_date > end_date:
        logger.warning(f"After flexible parsing, start_date ({start_date}) > end_date ({end_date}), swapping dates")
        return end_date, start_date

    return start_date, end_date


def normalize_date_to_iso(value) -> str:
    """
    Normalize date/datetime/string to ISO format (YYYY-MM-DD) for internal use.
    Used as grouping key.
    """
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date().strftime('%Y-%m-%d')
    elif isinstance(value, date):
        return value.strftime('%Y-%m-%d')
    elif isinstance(value, str):
        try:
            parsed = parse_date_flexible(value)
            return parsed.strftime('%Y-%m-%d')
        except ValueError:
            return value
    return str(value)


def format_datetime_for_download(value, user: CoreUser, preserve_in_excel: bool = True):
    """
    Format datetime/date value according to user settings for download.
    Used in background threads where request context is not available.

    Args:
        value: datetime or date object to format
        user: CoreUser object (the user who initiated the download)
        preserve_in_excel: If True, prefix with single quote to prevent Excel auto-formatting

    Returns:
        Formatted string according to user's settings
    """
    if value is None:
        return None

    # Get user settings
    user_settings = None
    try:
        if hasattr(user, 'user_settings'):
            user_settings = user.user_settings
        elif hasattr(user, 'usersettings'):
            user_settings = user.usersettings
        else:
            user_settings = UserSettings.objects.filter(user=user).first()
    except Exception:
        pass

    # Default formats
    date_format_str = '%m-%d-%Y'
    time_format_str = '%H:%M:%S'
    user_timezone = pytz.timezone('Asia/Ho_Chi_Minh')

    # Get user's language for locale-based defaults
    if hasattr(user, 'language') and user.language:
        lang_code = getattr(user.language, 'code', 'en')
        if lang_code == 'ko':
            date_format_str = '%Y-%m-%d'

    # Get timezone from user
    if hasattr(user, 'timezone') and user.timezone:
        try:
            tz_code = getattr(user.timezone, 'code', None) or getattr(user.timezone, 'name', None)
            if tz_code:
                user_timezone = pytz.timezone(tz_code)
        except Exception:
            pass

    # Get date format from user settings
    if user_settings:
        if hasattr(user_settings, 'date_format') and user_settings.date_format:
            if hasattr(user_settings.date_format, 'format_string'):
                date_format_str = user_settings.date_format.format_string

        if hasattr(user_settings, 'time_format') and user_settings.time_format:
            if hasattr(user_settings.time_format, 'format_string'):
                time_format_str = user_settings.time_format.format_string
    try:
        if isinstance(value, datetime):
            # Convert to user timezone
            if value.tzinfo is None:
                value = pytz.UTC.localize(value)
            localized = value.astimezone(user_timezone)

            # Format date and time parts
            date_part = localized.date().strftime(date_format_str)
            time_part = localized.time().strftime(time_format_str)
            result = f"{date_part} {time_part}"
            # Add single quote prefix to prevent Excel auto-formatting
            return result

        elif isinstance(value, date):
            result = value.strftime(date_format_str)
            # Add single quote prefix to prevent Excel auto-formatting
            return result

        else:
            return str(value)
    except Exception as e:
        # Fallback to ISO format
        if isinstance(value, datetime):
            fallback = value.isoformat()
        elif isinstance(value, date):
            fallback = value.isoformat()
        else:
            fallback = str(value)
        return f"'{fallback}" if preserve_in_excel else fallback


def parse_time_flexible(time_str: str) -> tuple:
    """
    Parse time string với nhiều format khác nhau
    Hỗ trợ các format:
    - 24: %H:%M
    - 12: %I:%M %p
    - 24_full: %H:%M:%S
    - 12_full: %I:%M:%S %p

    Returns: (time_object, is_24h_format)
    """
    if not time_str:
        raise ValueError("Time string is empty")

    time_str = time_str.strip()

    # Danh sách các format time để thử parse
    time_formats = [
        ('%H:%M:%S', True),      # 24_full: HH:MM:SS
        ('%H:%M', True),          # 24: HH:MM
        ('%I:%M:%S %p', False),   # 12_full: HH:MM:SS AM/PM
        ('%I:%M %p', False),      # 12: HH:MM AM/PM
        ('%I:%M:%S%p', False),    # 12_full without space: HH:MM:SSAM/PM
        ('%I:%M%p', False),       # 12 without space: HH:MMAM/PM
    ]

    # Thử parse với các format cố định
    for fmt, is_24h in time_formats:
        try:
            time_obj = datetime.strptime(time_str, fmt).time()
            return time_obj, is_24h
        except ValueError:
            continue

    # Nếu không parse được với format cố định, thử dùng dateutil.parser
    try:
        parsed_datetime = parser.parse(time_str)
        time_obj = parsed_datetime.time()
        # Kiểm tra xem có AM/PM không để xác định format
        is_24h = 'AM' not in time_str.upper() and 'PM' not in time_str.upper()
        return time_obj, is_24h
    except (ValueError, TypeError, AttributeError) as e:
        raise ValueError(f"Invalid time format: {time_str}. Cannot parse time.")


class HandoverDocumentService:
    """Service layer for HandoverDocument operations"""

    @staticmethod
    def get_list(user=None, start_date_time=None, end_date_time=None):
        """
        Lấy danh sách handover documents với logic giống old feature
        - Trả về queryset cho documents đã tồn tại (có thể dùng apply_dynamic_filters)
        - Empty shifts sẽ được xử lý ở view layer vì không thể tạo từ queryset
        """
        # Nếu không có date range, trả về queryset đơn giản
        if not start_date_time or not end_date_time:
            queryset = HandoverDocument.objects.select_related(
                'shift', 'handover', 'group', 'created_by', 'modified_by'
            ).prefetch_related(
                'acceptors__acceptor',
                'contents'
            ).annotate(
                total_content=Count('contents', distinct=True),
                is_notice=Count('contents', filter=Q(contents__is_notice=True), distinct=True),
                creator__full_name=Concat(Coalesce('created_by__first_name', Value('')), Value(' '), Coalesce('created_by__last_name', Value(''))),
                editor__full_name=Concat(Coalesce('modified_by__first_name', Value('')), Value(' '), Coalesce('modified_by__last_name', Value(''))),
            )
            return queryset

        # Parse dates với validation để đảm bảo end_date >= start_date
        try:
            start_date, end_date = parse_date_range_with_validation(start_date_time, end_date_time, user)
        except Exception as e:
            logger.error(f"Error parsing date range: {e}, falling back to simple queryset")
            # Fallback về logic đơn giản nếu parse lỗi
            queryset = HandoverDocument.objects.select_related(
                'shift', 'handover', 'group', 'created_by', 'modified_by'
            ).prefetch_related(
                'acceptors__acceptor',
                'contents'
            ).annotate(
                total_content=Count('contents', distinct=True),
                is_notice=Count('contents', filter=Q(contents__is_notice=True), distinct=True),
                creator__full_name=Concat(Coalesce('created_by__first_name', Value('')), Value(' '), Coalesce('created_by__last_name', Value(''))),
                editor__full_name=Concat(Coalesce('modified_by__first_name', Value('')), Value(' '), Coalesce('modified_by__last_name', Value(''))),
            )
            return queryset

        # Tạo date range
        date_range = pd.date_range(start=start_date, end=end_date)
        date_list = date_range.strftime("%Y-%m-%d").tolist()

        # Group filter
        filters = {}
        if user and not (user.is_superuser or any(role.code == 'superuser' for role in user.roles.all())):
            if hasattr(user, 'userprofilelink') and user.userprofilelink.group:
                filters['group'] = user.userprofilelink.group

        # Tạo Subquery cho shift name translation
        shift_name_subquery = HandoverShift.objects.filter(
            id=OuterRef('shift_id')
        ).values('name')[:1]

        # Trả về queryset cho documents đã tồn tại (có thể dùng apply_dynamic_filters)
        queryset = HandoverDocument.objects.filter(
            date_create_shift__in=date_list,
            deleted__isnull=True,
            **filters
        ).select_related(
            'shift', 'handover', 'group', 'created_by', 'modified_by'
        ).prefetch_related(
            'acceptors__acceptor',
            'contents'
        ).annotate(
            acceptor_name=ArrayAgg('acceptors__acceptor__username', distinct=True),
            acceptor_id=ArrayAgg('acceptors__acceptor__id', distinct=True),
            total_content=Count('contents', distinct=True),
            date=Cast('date_create_shift', output_field=CharField()),
            shift__name=Subquery(shift_name_subquery, output_field=CharField()),
            handover__name=F('handover__username'),
            group__name=F('group__name'),
            creator__full_name=Concat('created_by__first_name', Value(' '), 'created_by__last_name'),
            editor__full_name=Concat('modified_by__first_name', Value(' '), 'modified_by__last_name'),
        )

        return queryset

    @staticmethod
    def get_empty_shifts(user=None, start_date_time=None, end_date_time=None, existing_documents=None):
        """
        Lấy empty shifts cho các date chưa có document
        Trả về list với format: [{"date": date, "data": [shifts]}, ...]
        """
        if not start_date_time or not end_date_time:
            return []
        start_date, end_date = parse_date_range_with_validation(start_date_time, end_date_time, user)
        # Tạo date range (đã đảm bảo start_date <= end_date từ parse_date_range_with_validation)
        date_range = pd.date_range(start=start_date, end=end_date)
        date_list = date_range.strftime("%Y-%m-%d").tolist()

        # Lấy user language
        language = 'en'
        if user:
            if hasattr(user, 'language') and user.language:
                language = user.language.code

        # Lấy tất cả shift IDs (HandoverShift không có field group, nên lấy tất cả)
        handover_shift_id = set(HandoverShift._base_manager.values_list('id', flat=True))

        # Tạo mapping: date -> set of shift_ids đã có document từ existing_documents
        # existing_documents đã được filter theo group từ hàm get_list, nên chỉ cần map date -> shift_ids
        date_shift_map = {}
        if existing_documents:
            for doc in existing_documents:
                doc_date = doc.get('date') or doc.get('date_create_shift')
                doc_date = normalize_date_to_iso(doc_date)
                shift_id = doc.get('shift_id')
                if doc_date and doc_date not in date_shift_map:
                    date_shift_map[doc_date] = set()
                if doc_date and shift_id:
                    date_shift_map[doc_date].add(shift_id)

        # Batch query tất cả shifts một lần (không filter vì HandoverShift không có field group)
        all_shifts = list(
            HandoverShift._base_manager.values('id', 'name')
        )
        shifts_dict = {}
        for shift in all_shifts:
            shift_id = shift['id']
            # Lấy translated name nếu có
            try:
                shift_obj = HandoverShift._base_manager.get(id=shift_id)
                if hasattr(shift_obj, 'get_translated_field_name'):
                    shift_name = shift_obj.get_translated_field_name('name', language) or shift['name']
                else:
                    shift_name = shift['name']
            except:
                shift_name = shift['name']
            shifts_dict[shift_id] = shift_name

        # Tạo list empty shifts cho các date chưa có document
        empty_shifts_list = []
        for date_str in date_list:
            existing_shift_ids = date_shift_map.get(date_str, set())
            non_existing_shift_ids = handover_shift_id - existing_shift_ids

            if non_existing_shift_ids:
                # Tạo list shifts chưa có document cho date này
                data_shift = [
                    {
                        'id': shift_id,
                        'name': shifts_dict.get(shift_id, ''),
                        'handover_shift': shift_id
                    }
                    for shift_id in non_existing_shift_ids
                    if shift_id in shifts_dict
                ]

                if data_shift:
                    empty_shifts_list.append({
                        'date': date_str,
                        'data': data_shift
                    })
        return empty_shifts_list

    @staticmethod
    @transaction.atomic
    def create(data: Dict, user: CoreUser) -> Tuple[bool, Optional[HandoverDocument], Optional[Dict]]:
        """Tạo handover document mới"""
        try:
            date_str = data.get('date')  # YYYY-MM-DD
            shift_id = data.get('shift_id')

            if not date_str or not shift_id:
                raise ValidationError("date and shift_id are required")

            shift = HandoverShift.objects.get(id=shift_id)

            # Parse date với nhiều format khác nhau
            try:
                doc_date = parse_date_flexible(date_str)
            except ValueError as e:
                raise ValidationError(f"Invalid date format: {date_str}. {str(e)}")

            # Tính start_date và end_date từ shift.start_time và shift.end_time
            start_time_str = shift.start_time
            end_time_str = shift.end_time

            # Parse time string thành time object với nhiều format khác nhau
            # Fallback về giá trị mặc định nếu start_time hoặc end_time không hợp lệ (giống logic cũ)
            try:
                start_time_obj, _ = parse_time_flexible(start_time_str)
            except ValueError:
                logger.warning(
                    f"Shift {shift_id} (name: {shift.name}) has invalid start_time='{start_time_str}'. "
                    f"Using default value '09:00'"
                )
                start_time_obj = datetime.strptime("09:00", '%H:%M').time()

            try:
                end_time_obj, _ = parse_time_flexible(end_time_str)
            except ValueError:
                logger.warning(
                    f"Shift {shift_id} (name: {shift.name}) has invalid end_time='{end_time_str}'. "
                    f"Using default value '21:00'"
                )
                end_time_obj = datetime.strptime("21:00", '%H:%M').time()

            # Tạo datetime từ date và time
            start_date = timezone.make_aware(datetime.combine(doc_date, start_time_obj))
            end_date = timezone.make_aware(datetime.combine(doc_date, end_time_obj))

            # Nếu end_time < start_time thì end_date là ngày hôm sau
            if end_time_obj < start_time_obj:
                end_date += timedelta(days=1)
            # 소유 group 은 요청자(actor)에서만 온다 — W0-12.
            # 이전 구현은 group 이 없으면 저장된 첫 UserGroup 을 집어 썼다.
            # 테넌트가 둘 이상이면 남의 group 에 인수인계 문서가 생긴다.
            try:
                group = require_user_group(user)
            except NoTenantGroupError as exc:
                raise ValidationError(str(exc)) from exc
            # Kiểm tra trùng lặp (check cả bản đã deleted - giống logic cũ)
            # Logic cũ: HandoverDocument.objects.filter(...).exists() - không filter deleted
            # Sử dụng _base_manager để check cả bản đã deleted
            existing = HandoverDocument._base_manager.filter(
                start_date=start_date,
                end_date=end_date,
                shift=shift,
                group=group
            ).first()

            if existing:
                return False, None, {'message_key': MESSAGE_ENUM.HANDOVER_DOCS_EXIST}



            # Tạo document
            document = HandoverDocument.objects.create(
                start_date=start_date,
                end_date=end_date,
                handover=user,
                shift=shift,
                date_create_shift=doc_date,
                group=group,
                created_by=user
            )

            return True, document, None
        except HandoverShift.DoesNotExist:
            raise ValidationError("Handover shift not found")
        except ValidationError:
            raise
        except Exception as e:
            logger.exception(f"Error creating handover document: {e}")
            raise ValidationError(f"Failed to create handover document: {str(e)}")

    @staticmethod
    @transaction.atomic
    def delete(ids: List[int], user: CoreUser) -> Tuple[bool, Dict]:
        """Xóa handover documents"""
        results = {
            'deleted': [],
            'failed': []
        }

        documents = HandoverDocument.objects.filter(id__in=ids)

        for doc in documents:
            # Kiểm tra xem có content không
            if HandoverContent.objects.filter(handover_doc=doc).exists():
                results['failed'].append({
                    'id': doc.id,
                    'reason': 'Document has content'
                })
            else:

                HandoverDocumentAcceptor.objects.filter(handover_document=doc).delete()
                doc_to_delete = HandoverDocument._base_manager.get(id=doc.id)
                doc_to_delete.delete(force_policy=HARD_DELETE)
                results['deleted'].append(doc.id)

        # Xác định message dựa trên kết quả
        if len(results['failed']) == 0:
            # Tất cả đều xóa thành công
            results['message_key'] = MESSAGE_ENUM.REMOVED_BLANK_JOURNALS
        elif len(results['deleted']) > 0:
            # Có một số record có content nhưng vẫn xóa được những record không có content
            results['message_key'] = MESSAGE_ENUM.HANDOVER_DOCUMENT_WARNING
        else:
            # Tất cả đều thất bại (không có record nào được xóa)
            results['message_key'] = MESSAGE_ENUM.HANDOVER_DOCUMENT_WARNING

        return True, results

    @staticmethod
    def get_download_data(start_date_time: str, end_date_time: str, user: CoreUser, request: QueryDict = None):
        """Lấy dữ liệu để download CSV cho handover management"""
        # Parse date string (format: YYYY-MM-DD)
        try:
            # Parse date từ string
            if isinstance(start_date_time, str):
                start_date = parse_date_by_user_format(start_date_time, user)
            elif isinstance(start_date_time, date):
                start_date = start_date_time
            elif isinstance(start_date_time, datetime):
                start_date = start_date_time.date()
            else:
                raise ValueError(f"Invalid start_date_time format: {start_date_time}")

            if isinstance(end_date_time, str):
                end_date = parse_date_by_user_format(end_date_time, user)
            elif isinstance(end_date_time, date):
                end_date = end_date_time
            elif isinstance(end_date_time, datetime):
                end_date = end_date_time.date()
            else:
                raise ValueError(f"Invalid end_date_time format: {end_date_time}")

            # Đảm bảo end_date >= start_date
            if start_date > end_date:
                start_date, end_date = end_date, start_date

            # Combine với time: start = 00:00:00, end = 23:59:59.999999
            start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
            end_dt = timezone.make_aware(datetime.combine(end_date, time(23, 59, 59, 999999)))

        except Exception as e:
            logger.error(f"Error parsing date: {e}, falling back to date parsing")
            # Fallback về date parsing nếu parse fail
            start_date, end_date = parse_date_range_with_validation(start_date_time, end_date_time, user)
            start_dt = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
            end_dt = timezone.make_aware(datetime.combine(end_date, time(23, 59, 59, 999999)))

        filters = {}
        filters['start_date__gte'] = start_dt
        filters['end_date__lte'] = end_dt
        if not user.is_superuser and not (any(role.id == 1 for role in user.roles.all())):
            filters['group'] = user.userprofilelink.group
        handover_doc_ids = list(
            HandoverDocument.objects.filter(**filters)
            .filter(deleted__isnull=True)
            .values_list('id', flat=True)
        )
        content_list = list(
            HandoverContent.objects.filter(handover_doc_id__in=handover_doc_ids)
            .annotate(
                editors_name=ArrayAgg('editors__username', distinct=True),
            )
            .values(
                'handover_doc__start_date',
                'handover_doc__shift__name',
                'content',
                'creator__username',
                'editors_name',
                'is_notice',
                'created_time',
                'updated_time'
            )
            .order_by('-handover_doc__start_date')
        )
        content_list = apply_dynamic_filters(content_list, request, [], request.GET.get("sort_obj"))
        return content_list

    @staticmethod
    def download_management(start_date_time: str, end_date_time: str, user: CoreUser, request: QueryDict = None):
        """
        Queue handover management download as background thread with WebSocket notifications
        Returns immediately with download status information
        """
        try:
            # Generate unique task ID for download tracking
            download_task_id = str(uuid.uuid4())
            task_type = "handover_management_download"

            # Persist initial task status for client-side polling
            pending_message = get_message(MESSAGE_ENUM.START_DOWNLOAD_FILE)
            TaskStatusService.create_or_update(
                task_id=download_task_id,
                task_type=task_type,
                category=TaskStatus.Category.DOWNLOAD,
                user=user,
                status="pending",
                message=pending_message,
                action="handover_management_download",
                task_channel=f"handover_{user.username}",
                trigger_source="handover.management.download",
                related_model="handover.HandoverDocument",
            )

            # Send initial notification
            _send_handover_download_notification(
                user.username,
                'management',
                'pending',
                pending_message,
                download_task_id
            )

            # Start background thread for download processing
            download_thread = threading.Thread(
                target=HandoverDocumentService._process_download_in_thread,
                args=(start_date_time, end_date_time, download_task_id, user.id, task_type, request),
                daemon=True
            )
            download_thread.start()

            return {
                'success': True,
                'download_task_id': download_task_id,
                'message': pending_message
            }

        except Exception as e:
            logger.error(f"Error queueing download: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to queue download task'
            }

    @staticmethod
    def _process_download_in_thread(start_date_time: str, end_date_time: str, download_task_id: str, user_id: int, task_type: str = None, request: QueryDict = None):
        """
        Process download in background thread with WebSocket notifications
        """
        download_type = 'management'  # Xác định download_type
        if not task_type:
            task_type = "handover_management_download"
        try:
            logger.info(f"🔄 Starting handover {download_type} download processing for task {download_task_id}")

            # Get user
            user = CoreUser.objects.get(id=user_id)

            # Send processing notification
            processing_message = get_message(MESSAGE_ENUM.DOWNLOAD_HANDOVER_MANAGEMENT_PROCESSING)
            TaskStatusService.update_status(
                download_task_id,
                status="processing",
                message=processing_message,
                action="handover_management_download",
                task_channel=f"handover_{user.username}",
                trigger_source="handover.management.download",
            )
            _send_handover_download_notification(
                user.username,
                download_type,
                'processing',
                processing_message,
                download_task_id
            )

            # Get data
            content_list = HandoverDocumentService.get_download_data(start_date_time, end_date_time, user, request=request)

            # Format datetime fields according to user settings
            datetime_fields = ['created_time', 'updated_time']
            date_fields = ['handover_doc__start_date']

            for item in content_list:
                # Format date fields
                for field in date_fields:
                    if field in item and item[field] is not None:
                        if isinstance(item[field], datetime):
                            item[field] = format_datetime_for_download(item[field].date(), user)
                        elif isinstance(item[field], date):
                            item[field] = format_datetime_for_download(item[field], user)

                # Format datetime fields
                for field in datetime_fields:
                    if field in item and item[field] is not None:
                        item[field] = format_datetime_for_download(item[field], user)

            # Create CSV
            output = io.StringIO()

            # Get user language for column headers
            user_lang = 'en'
            if hasattr(user, 'language') and user.language:
                user_lang = getattr(user.language, 'code', 'en')

            # Load translations from JSON file
            translations = {}
            try:
                import json
                import os
                translation_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'core', 'advanced_table', 'translations', f'{user_lang}.json'
                )
                if os.path.exists(translation_path):
                    with open(translation_path, 'r', encoding='utf-8') as f:
                        translations = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load translations for {user_lang}: {e}")

            # Translation keys mapping (field_name -> translation_key)
            translation_keys = {
                'handover_doc__start_date': 'handover.HandoverDocument.start_date',
                'handover_doc__shift__name': 'custom.handover_management.shift__name',
                'content': 'handover.HandoverNotice.content',
                'creator__username': 'custom.handover_management.created_by__username',
                'editors_name': 'custom.notice_management.editor_names',
                'is_notice': 'handover.HandoverNotice.status',
                'created_time': 'handover.HandoverNotice.created_time',
                'updated_time': 'handover.HandoverNotice.updated_time'
            }

            # Fallback headers (English)
            fallback_headers = {
                'handover_doc__start_date': 'Date',
                'handover_doc__shift__name': 'Shift',
                'content': 'Content',
                'creator__username': 'Creator',
                'editors_name': 'Editors',
                'is_notice': 'Notice',
                'created_time': 'Created Time',
                'updated_time': 'Updated Time'
            }

            # Build header mapping from translations
            header_mapping = {}
            for field, trans_key in translation_keys.items():
                header_mapping[field] = fallback_headers.get(field, field)

            # Original field names (for data extraction)
            original_fieldnames = [
                'handover_doc__start_date',
                'handover_doc__shift__name',
                'content',
                'creator__username',
                'editors_name',
                'is_notice',
                'created_time',
                'updated_time'
            ]

            # Display names for CSV header
            display_fieldnames = [header_mapping[f] for f in original_fieldnames]

            if content_list:
                # Rename keys in each item to display names
                formatted_content_list = []
                for item in content_list:
                    formatted_item = {}
                    for orig_key in original_fieldnames:
                        display_key = header_mapping[orig_key]
                        formatted_item[display_key] = item.get(orig_key, '')
                    formatted_content_list.append(formatted_item)

                writer = csv.DictWriter(output, fieldnames=display_fieldnames)
                writer.writeheader()
                writer.writerows(formatted_content_list)

            csv_content = output.getvalue().encode('utf-8')
            csv_filename = f"handover_management_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            # Create InMemoryUploadedFile
            file_obj = InMemoryUploadedFile(
                file=BytesIO(csv_content),
                field_name='file',
                name=csv_filename,
                content_type='text/csv',
                size=len(csv_content),
                charset='utf-8'
            )

            # Upload to MinIO/S3 - File được lưu vào MinIO tạm thời để user có thể download
            # File này sẽ được cleanup sau một thời gian vì không có tính năng xem lại file đã download
            # Sử dụng feature_path động theo download_type để phân loại file
            # download_type: 'handover_management' → 'HandoverDownloads/HandoverManagement'
            feature_path = f"HandoverDownloads/{download_type.replace('_', '').title()}"  # HandoverDownloads/HandoverManagement
            uploaded_file = FileHelper.user_upload_s3(
                user,
                file_obj,
                is_avatar=False,
                only_image=False,
                feature_path=feature_path
            )

            # Kiểm tra file đã được upload thành công chưa
            if not uploaded_file:
                raise ValueError("Failed to upload file to MinIO")

            # Get download URL with proper protocol và file_url (relative path)
            download_url = None
            file_url = None
            if hasattr(uploaded_file, 'file_url') and uploaded_file.file_url:
                file_url = uploaded_file.file_url  # Relative path: /media/exports/file.csv
                protocol = 'https' if settings.MINIO_USE_HTTPS else 'http'
                download_url = f'{protocol}://{settings.MINIO_ENDPOINT}{file_url}'
            else:
                # Nếu không có file_url, thử lấy từ các attribute khác
                if hasattr(uploaded_file, 'file') and uploaded_file.file:
                    file_url = uploaded_file.file.name if hasattr(uploaded_file.file, 'name') else ''
                if not file_url:
                    raise ValueError("File uploaded but no file_url available")

            logger.info(f"📁 File uploaded to MinIO: {file_url}, File ID: {uploaded_file.id}")

            success_payload = {
                'download_url': download_url,
                'file_url': file_url,
                'filename': csv_filename,
                'file_id': uploaded_file.id,
                'total_records': len(content_list)
            }

            TaskStatusService.update_status(
                download_task_id,
                status='success',
                message=get_message(MESSAGE_ENUM.ACTION_EXPORT_SUCCESS),
                data=success_payload,
                download_url=download_url,
                file_url=file_url,
                filename=csv_filename,
                file_id=str(uploaded_file.id),
                record_count=len(content_list),
                action="handover_management_download",
                task_channel=f"handover_{user.username}",
                trigger_source="handover.management.download",
            )

            # Send success notification
            success_message = get_message(MESSAGE_ENUM.ACTION_EXPORT_SUCCESS)
            _send_handover_download_notification(
                user.username,
                download_type,
                'success',
                f'{success_message} {len(content_list)} records exported.',
                download_task_id,
                success_payload
            )

            logger.info(f"✅ Handover management download completed for task {download_task_id}")

        except Exception as e:
            logger.error(f"❌ Error in handover management download processing: {str(e)}")

            # Send failure notification
            try:
                user = CoreUser.objects.get(id=user_id)
                download_type = 'handover_management'  # Xác định download_type cho error case
                error_message = get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED)
                TaskStatusService.update_status(
                    download_task_id,
                    status="failed",
                    message=str(e),
                    data={'error': str(e)},
                    error_code="download_failed",
                    error_details={'error': str(e)},
                    action="handover_management_download",
                    task_channel=f"handover_{user.username}",
                    trigger_source="handover.management.download",
                )
                _send_handover_download_notification(
                    user.username,
                    download_type,
                    'failed',
                    f'{error_message} {str(e)}',
                    download_task_id,
                    {'error': str(e)}
                )
            except:
                pass
