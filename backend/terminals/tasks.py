"""
Celery tasks cho Terminal Operating Time và Exceptions
Background tasks cho import/export plan files với TaskStatus tracking
"""

import logging
import threading
import uuid
from datetime import datetime, time as dt_time, date, timedelta, tzinfo, timezone as dt_timezone
from typing import Optional, List, Tuple, Any, Dict

import pytz
from celery import shared_task
from django.utils import timezone
from django.db import close_old_connections

from task_status.models import TaskStatus
from task_status.services.task_status_service import TaskStatusService
from common.constant import get_message, MESSAGE_ENUM

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=30, ignore_result=True)
def upload_route_images(self, route_id: int, user_id: int, img_map_data: dict | None = None, img_route_data: dict | None = None) -> None:
    """
    Upload route images (img_map/img_route) in background to avoid blocking API response.
    img_*_data format: {"content": bytes, "name": str, "content_type": str}
    """
    try:
        from io import BytesIO
        from django.core.files.uploadedfile import InMemoryUploadedFile
        from core.user.models import CoreUser
        from terminals.models import Routes
        from core.file_management.helper import FileHelper
        from core.middleware.refresh_token import thread_local

        user = CoreUser._base_manager.get(id=user_id)

        # 🧵 Seed thread-local request context (some models/managers rely on it)
        previous_request = getattr(thread_local, "request", None)

        class _ThreadRequest:
            def __init__(self, user):
                self.user = user
                self.GET = {}
                self.META = {"REMOTE_ADDR": "127.0.0.1"}
                self.method = "CELERY"

        thread_local.request = _ThreadRequest(user)

        route = Routes._base_manager.get(id=route_id)

        def _upload_one(file_data: dict | None):
            if not file_data:
                return None
            content = file_data.get("content")
            name = file_data.get("name") or "file.bin"
            content_type = file_data.get("content_type") or "application/octet-stream"
            if content is None:
                return None
            bio = BytesIO(content)
            uploaded = InMemoryUploadedFile(
                file=bio,
                field_name="file",
                name=name,
                content_type=content_type,
                size=len(content),
                charset=None,
            )
            return FileHelper.user_upload_s3(user, uploaded, feature_path="RouteMap")

        img_map_file = _upload_one(img_map_data)
        if img_map_file:
            route.img_map = img_map_file

        img_route_file = _upload_one(img_route_data)
        if img_route_file:
            route.img_route = img_route_file

        if img_map_file or img_route_file:
            route.save(update_fields=["img_map", "img_route"])

    except Exception as exc:
        logger.exception("[ROUTE][UPLOAD] Failed to upload route images for route_id=%s: %s", route_id, exc)
        raise
    finally:
        # Restore/cleanup thread-local request (best-effort)
        try:
            from core.middleware.refresh_token import thread_local
            if previous_request is None:
                if hasattr(thread_local, "request"):
                    delattr(thread_local, "request")
            else:
                thread_local.request = previous_request
        except Exception:
            pass


def _extract_timezone_code(value: Any, seen: Optional[set] = None) -> Optional[str]:
    """
    Cố gắng trích xuất timezone code từ nhiều kiểu dữ liệu khác nhau.
    """
    if not value:
        return None

    if seen is None:
        seen = set()

    if isinstance(value, str):
        candidate = value.strip()
        return candidate or None

    value_id = id(value)
    if value_id in seen:
        return None
    seen.add(value_id)

    # Nếu là dict cấu hình
    if isinstance(value, dict):
        for key in ("code", "timezone", "tz", "name", "value"):
            if key in value:
                candidate = _extract_timezone_code(value.get(key), seen)
                if candidate:
                    return candidate
        return None

    # Các thuộc tính thường gặp
    for attr in ("code", "timezone", "tz", "name", "value"):
        if hasattr(value, attr):
            candidate = _extract_timezone_code(getattr(value, attr), seen)
            if candidate:
                return candidate

    return None


def _normalize_to_tzinfo(value: Any) -> Optional[tzinfo]:
    """
    Chuẩn hoá giá trị timezone (chuỗi, đối tượng hoặc tzinfo) thành tzinfo.
    """
    if not value:
        return None

    if isinstance(value, tzinfo):
        return value

    # pytz timezone có thuộc tính zone, zoneinfo có key
    zone_name = getattr(value, "zone", None) or getattr(value, "key", None)
    if isinstance(zone_name, str) and zone_name.strip():
        try:
            return pytz.timezone(zone_name.strip())
        except pytz.UnknownTimeZoneError:
            return None

    code = _extract_timezone_code(value)
    if code:
        try:
            return pytz.timezone(code)
        except pytz.UnknownTimeZoneError:
            return None

    return None


def get_terminal_timezone(terminal) -> tzinfo:
    """
    Lấy timezone cho terminal dựa trên user tạo hoặc thiết lập trực tiếp.
    """
    tz_sources: List[Any] = []

    try:
        user = getattr(terminal, "created_by", None)
        if not user and getattr(terminal, "created_by_id", None):
            from core.user.models import CoreUser

            try:
                user = CoreUser._base_manager.select_related(
                    "timezone",
                ).get(id=terminal.created_by_id)
            except CoreUser.DoesNotExist:
                user = None

        if user:
            user_timezone = getattr(user, "timezone", None)
            if user_timezone:
                tz_sources.append(user_timezone)
                tz_sources.append(getattr(user_timezone, "code", None))

            tz_sources.extend(
                [
                    getattr(user, "preferred_timezone", None),
                    getattr(getattr(user, "settings", None), "timezone", None),
                ]
            )

    except Exception as exc:
        logger.debug(
            "[TERMINAL][TIMEZONE] Unable to resolve user timezone for terminal %s (%s): %s",
            getattr(terminal, "name", terminal.id),
            terminal.id,
            exc,
        )

    tz_sources.extend(
        [
            getattr(terminal, "timezone", None),
            getattr(terminal, "operating_timezone", None),
            getattr(terminal, "timezone_code", None),
        ]
    )

    for source in tz_sources:
        tzinfo_obj = _normalize_to_tzinfo(source)
        if tzinfo_obj:
            return tzinfo_obj

        code = _extract_timezone_code(source)
        if code:
            try:
                return pytz.timezone(code)
            except pytz.UnknownTimeZoneError:
                logger.warning(
                    "[TERMINAL][TIMEZONE] Unknown timezone '%s' for terminal %s (ID: %s)",
                    code,
                    getattr(terminal, "name", terminal.id),
                    terminal.id,
                )

    return timezone.get_current_timezone()


def combine_with_timezone(date_value: date, time_value: dt_time, tz: Optional[tzinfo] = None) -> datetime:
    """
    Combine date và time thành datetime có timezone cụ thể.
    """
    tz = tz or timezone.get_current_timezone()
    naive_dt = datetime.combine(date_value, time_value)

    if timezone.is_aware(naive_dt):
        return naive_dt.astimezone(tz)

    try:
        return timezone.make_aware(naive_dt, tz)
    except Exception:
        localize = getattr(tz, "localize", None)
        if callable(localize):
            try:
                return localize(naive_dt, is_dst=None)
            except Exception:
                return localize(naive_dt, is_dst=False)
        return naive_dt.replace(tzinfo=tz)


def collapse_time_ranges(ranges: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
    """
    Gộp (collapse) các khoảng thời gian overlap hoặc liền kề thành các khoảng lớn hơn.
    
    Args:
        ranges: List các tuple (start_datetime, end_datetime)
    
    Returns:
        List các tuple đã được collapse (không overlap, không liền kề)
    
    Ví dụ:
        Input: [(00:05, 00:12), (00:11, 00:14)]
        Output: [(00:05, 00:14)]  # Gộp thành một khoảng
    """
    if not ranges:
        return []
    
    # Sắp xếp theo start_time
    sorted_ranges = sorted(ranges, key=lambda x: (x[0], x[1]))
    
    collapsed = []
    current_start, current_end = sorted_ranges[0]
    
    for start, end in sorted_ranges[1:]:
        # Nếu khoảng hiện tại overlap hoặc liền kề với khoảng tiếp theo
        # (start <= current_end nghĩa là overlap hoặc liền kề)
        if start <= current_end:
            # Mở rộng khoảng hiện tại đến end lớn hơn
            current_end = max(current_end, end)
        else:
            # Không overlap -> thêm khoảng hiện tại vào kết quả và bắt đầu khoảng mới
            collapsed.append((current_start, current_end))
            current_start, current_end = start, end
    
    # Thêm khoảng cuối cùng
    collapsed.append((current_start, current_end))
    
    return collapsed


def should_terminal_be_active(terminal, current_datetime: datetime, tz: Optional[tzinfo] = None) -> bool:
    """
    Kiểm tra xem terminal có nên active hay không dựa trên:
    1. Operating times (thời gian hoạt động theo ngày trong tuần)
    2. Exceptions (các ngoại lệ)
    
    Logic:
    - Nếu có exception cho ngày hiện tại và is_all_day=True -> inactive
    - Nếu có exception cho ngày hiện tại và không phải all_day -> kiểm tra thời gian
    - Nếu không có exception -> kiểm tra operating time theo ngày trong tuần
    
    LƯU Ý: Function này được dùng trong task context, cần dùng _base_manager
    """
    from terminals.models import DayOfWeek, TerminalException, TerminalOperatingTime

    tz = tz or get_terminal_timezone(terminal)
    if timezone.is_naive(current_datetime):
        current_datetime = timezone.make_aware(current_datetime, tz)
    else:
        current_datetime = current_datetime.astimezone(tz)

    current_date = current_datetime.date()
    current_time = current_datetime.time()  # Naive time ở timezone của terminal
    current_weekday = current_datetime.weekday()  # 0=Monday, 6=Sunday
    
    # Kiểm tra exceptions trước (ưu tiên cao hơn) - dùng _base_manager
    exceptions = TerminalException._base_manager.filter(
        terminal=terminal,
        exception_date=current_date
    )
    
    for exception in exceptions:
        if exception.is_all_day:
            # Nếu là all day exception -> inactive
            return False
        else:
            # Nếu có time range exception
            if exception.start_time and exception.end_time:
                # Nếu thời gian hiện tại nằm trong khoảng exception -> inactive
                if exception.start_time <= current_time < exception.end_time:
                    return False
    
    # Tìm DayOfWeek tương ứng với weekday hiện tại (dựa trên order) - dùng _base_manager
    try:
        current_day_of_week = DayOfWeek._base_manager.filter(
            order=current_weekday, 
            is_active=True
        ).first()
        if not current_day_of_week:
            # Nếu không tìm thấy day_of_week tương ứng -> inactive (mặc định)
            return False
    except Exception:
        return False
    
    # Kiểm tra operating time theo ngày trong tuần - dùng _base_manager
    operating_time = TerminalOperatingTime._base_manager.filter(
        terminal=terminal,
        day_of_week=current_day_of_week
    ).first()
    
    if not operating_time:
        # Nếu không có cấu hình operating time cho ngày này -> inactive (mặc định)
        return False
    
    if not operating_time.is_active:
        # Nếu ngày này không active -> inactive
        return False
    
    # Kiểm tra thời gian hoạt động
    if operating_time.start_time and operating_time.end_time:
        # Nếu thời gian hiện tại nằm trong khoảng hoạt động -> active
        return operating_time.start_time <= current_time < operating_time.end_time
    
    # Nếu không có thời gian cụ thể nhưng is_active=True -> active
    return True


def calculate_next_activation_times(
    terminal,
    from_datetime: datetime,
    days_ahead: int = 7,
    tz: Optional[tzinfo] = None,
) -> List[Tuple[datetime, bool]]:
    """
    Tính toán tất cả các thời điểm activate/deactivate trong khoảng thời gian từ from_datetime
    Trả về list các tuple (datetime, should_be_active)
    
    QUAN TRỌNG - Mapping giữa Operating Time và Exception:
    - Operating Time: Lưu trữ theo THỨ TRONG TUẦN (day_of_week) và giờ (start_time/end_time)
    - Exception: Lưu trữ theo NGÀY CỤ THỂ (exception_date) và giờ hoặc all_day
    
    Logic mapping:
    1. Với mỗi ngày cụ thể (check_date), tìm thứ trong tuần (weekday: 0=Monday, 6=Sunday)
    2. Map weekday -> DayOfWeek (dựa trên order)
    3. Tìm OperatingTime cho terminal và day_of_week đó
    4. Combine ngày cụ thể (check_date) với giờ từ OperatingTime để tạo datetime
    5. Áp dụng Exception cho ngày cụ thể đó (nếu có)
    
    LƯU Ý: Function này được dùng trong task context, cần dùng _base_manager cho tất cả model access
    """
    from terminals.models import DayOfWeek, TerminalOperatingTime, TerminalException

    tz = tz or get_terminal_timezone(terminal)

    if timezone.is_naive(from_datetime):
        from_datetime = timezone.make_aware(from_datetime, tz)
    else:
        from_datetime = from_datetime.astimezone(tz)

    activation_times = []
    current_date = from_datetime.date()

    # Tính toán cho N ngày tiếp theo
    for day_offset in range(days_ahead):
        check_date = current_date + timedelta(days=day_offset)
        
        # ============================================================
        # BƯỚC 1: Kiểm tra EXCEPTIONS cho NGÀY CỤ THỂ này
        # Exception được lưu theo ngày cụ thể (exception_date)
        # ============================================================
        exceptions = TerminalException._base_manager.filter(
            terminal=terminal,
            exception_date=check_date  # Filter theo ngày cụ thể
        )
        all_day_exceptions = exceptions.filter(is_all_day=True)
        time_range_exceptions = exceptions.filter(is_all_day=False, start_time__isnull=False, end_time__isnull=False)
        
        # Case 1: Có all day exception -> cả ngày inactive
        if all_day_exceptions.exists():
            # Thêm thời điểm deactivate vào đầu ngày (00:00:00)
            activation_times.append((combine_with_timezone(check_date, dt_time.min, tz), False))
            # Không cần xử lý operating time nữa vì cả ngày inactive
            continue
        
        # ============================================================
        # BƯỚC 2: Map NGÀY CỤ THỂ -> THỨ TRONG TUẦN -> OPERATING TIME
        # Operating Time được lưu theo thứ trong tuần (day_of_week)
        # ============================================================
        # Lấy thứ trong tuần của ngày cụ thể (0=Monday, 6=Sunday)
        weekday = check_date.weekday()
        
        # Tìm DayOfWeek tương ứng với weekday (dựa trên order)
        day_of_week = DayOfWeek._base_manager.filter(
            order=weekday,  # Map weekday -> DayOfWeek.order
            is_active=True
        ).first()
        
        if not day_of_week:
            # Không tìm thấy day_of_week tương ứng -> terminal nên inactive cả ngày
            # Thêm thời điểm deactivate vào đầu ngày để đảm bảo terminal được deactivate
            activation_times.append((combine_with_timezone(check_date, dt_time.min, tz), False))
            continue
            
        # Tìm OperatingTime cho terminal và thứ trong tuần này
        # Lưu ý: Cần check cả is_active=False để xử lý đúng
        operating_time = TerminalOperatingTime._base_manager.filter(
            terminal=terminal,
            day_of_week=day_of_week  # OperatingTime lưu theo day_of_week (thứ trong tuần)
        ).first()
        
        if not operating_time:
            # Không có operating time cho thứ này -> terminal nên inactive cả ngày
            # Thêm thời điểm deactivate vào đầu ngày để đảm bảo terminal được deactivate
            activation_times.append((combine_with_timezone(check_date, dt_time.min, tz), False))
            continue
        
        # Kiểm tra is_active của operating time
        if not operating_time.is_active:
            # Operating time có nhưng is_active=False -> terminal nên inactive cả ngày
            # Thêm thời điểm deactivate vào đầu ngày để đảm bảo terminal được deactivate
            activation_times.append((combine_with_timezone(check_date, dt_time.min, tz), False))
            continue
        
        # ============================================================
        # BƯỚC 3: Combine NGÀY CỤ THỂ với GIỜ từ OPERATING TIME
        # OperatingTime chỉ có giờ (start_time/end_time), cần combine với ngày cụ thể
        # ============================================================
        if operating_time.start_time and operating_time.end_time:
            # Có thời gian cụ thể từ OperatingTime
            # Combine ngày cụ thể (check_date) với giờ từ OperatingTime
            activate_time = combine_with_timezone(check_date, operating_time.start_time, tz)
            deactivate_time = combine_with_timezone(check_date, operating_time.end_time, tz)
            
            # ============================================================
            # BƯỚC 4: Áp dụng EXCEPTIONS cho NGÀY CỤ THỂ này
            # Exception có giờ (start_time/end_time) cho ngày cụ thể (check_date)
            # Cần combine ngày cụ thể với giờ từ Exception
            # ============================================================
            # Xử lý tất cả time range exceptions (có thể có nhiều exceptions trong một ngày)
            # Tạo danh sách các khoảng thời gian bị exception
            # Combine ngày cụ thể (check_date) với giờ từ Exception
            exception_ranges = []
            for exception in time_range_exceptions:
                if exception.start_time and exception.end_time:
                    # Exception lưu giờ cho ngày cụ thể (exception_date = check_date)
                    # Combine ngày cụ thể với giờ từ Exception
                    exc_start = combine_with_timezone(check_date, exception.start_time, tz)
                    exc_end = combine_with_timezone(check_date, exception.end_time, tz)
                    exception_ranges.append((exc_start, exc_end))
            
            # Collapse các exceptions overlap hoặc liền kề thành các khoảng lớn hơn
            exception_ranges = collapse_time_ranges(exception_ranges)
            
            # Tính toán các khoảng thời gian active dựa trên operating time và exceptions
            if not exception_ranges:
                # Không có exception -> operating time bình thường
                activation_times.append((activate_time, True))
                activation_times.append((deactivate_time, False))
            else:
                # Có exceptions -> tính toán các khoảng active
                current_start = activate_time
                
                for exc_start, exc_end in exception_ranges:
                    # Case 1: Exception nằm hoàn toàn trước operating time -> bỏ qua
                    if exc_end <= activate_time:
                        continue
                    
                    # Case 2: Exception nằm hoàn toàn sau operating time -> dừng (không cần xử lý exceptions sau)
                    if exc_start >= deactivate_time:
                        break
                    
                    # Case 3: Exception bao phủ toàn bộ operating time
                    # exc_start <= activate_time AND exc_end >= deactivate_time
                    if exc_start <= activate_time and exc_end >= deactivate_time:
                        # Exception bao phủ hoàn toàn operating time -> không có khoảng active nào
                        # Cập nhật current_start để đảm bảo không thêm khoảng active sau
                        current_start = deactivate_time
                        # Không cần xử lý các exceptions tiếp theo vì đã bao phủ hết
                        break
                    
                    # Case 4: Exception nằm một phần trong operating time
                    # Có khoảng active trước exception (nếu có)
                    if current_start < exc_start and current_start < deactivate_time:
                        # Thêm khoảng active trước exception
                        activation_times.append((current_start, True))
                        activation_times.append((min(exc_start, deactivate_time), False))
                    
                    # Cập nhật current_start để tiếp tục sau exception
                    current_start = max(exc_end, current_start)
                
                # Nếu còn khoảng thời gian active sau exceptions cuối cùng
                # (chỉ khi không có exception nào bao phủ toàn bộ operating time)
                if current_start < deactivate_time:
                    activation_times.append((current_start, True))
                    activation_times.append((deactivate_time, False))
        else:
            # ============================================================
            # Case: OperatingTime không có start_time/end_time -> active cả ngày
            # Nhưng vẫn cần kiểm tra time range exceptions cho ngày cụ thể này
            # ============================================================
            if time_range_exceptions.exists():
                # Có exceptions trong ngày cụ thể -> cần xử lý
                day_start = combine_with_timezone(check_date, dt_time.min, tz)
                day_end = combine_with_timezone(check_date, dt_time.max, tz)
                
                # Tạo danh sách các khoảng thời gian bị exception
                exception_ranges = []
                for exception in time_range_exceptions:
                    if exception.start_time and exception.end_time:
                        # Exception có giờ cho ngày cụ thể (exception_date = check_date)
                        # Combine ngày cụ thể với giờ từ Exception
                        exc_start = combine_with_timezone(check_date, exception.start_time, tz)
                        exc_end = combine_with_timezone(check_date, exception.end_time, tz)
                        exception_ranges.append((exc_start, exc_end))
                
                # Collapse các exceptions overlap hoặc liền kề thành các khoảng lớn hơn
                exception_ranges = collapse_time_ranges(exception_ranges)
                
                current_start = day_start
                for exc_start, exc_end in exception_ranges:
                    # Nếu có khoảng active trước exception
                    if current_start < exc_start:
                        activation_times.append((current_start, True))
                        activation_times.append((exc_start, False))
                    
                    # Cập nhật current_start để tiếp tục sau exception
                    current_start = max(exc_end, current_start)
                
                # Nếu còn khoảng thời gian active sau exceptions cuối cùng
                if current_start < day_end:
                    activation_times.append((current_start, True))
                    activation_times.append((day_end, False))
            else:
                # Không có exception -> active cả ngày
                activation_times.append((combine_with_timezone(check_date, dt_time.min, tz), True))
    
    # Sắp xếp theo thời gian và lọc các thời điểm trong tương lai
    activation_times = [
        (dt, active) for dt, active in activation_times 
        if dt > from_datetime
    ]
    activation_times.sort(key=lambda x: x[0])
    
    return activation_times


@shared_task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def schedule_terminal_activation_for_terminal(terminal_id: int, days_ahead: int = 7) -> None:
    """
    Schedule các task activate/deactivate cho một terminal cụ thể
    Được gọi ngay khi exception hoặc operating time được tạo/cập nhật/xóa
    
    Args:
        terminal_id: ID của terminal cần schedule
        days_ahead: Số ngày tính toán trước (mặc định 7 ngày)
    
    LƯU Ý: Sử dụng _base_manager cho tất cả model access vì task không có request context
    """
    try:
        from terminals.models import Terminal
        
        # NOTE: close_old_connections() đã được gọi tự động bởi task_prerun signal trong celery.py
        # Chỉ cần gọi lại khi retry sau SSL/connection errors
        
        now = timezone.now()
        if now.tzinfo != pytz.UTC:
            now = now.astimezone(pytz.UTC)
        
        # Lấy terminal - dùng _base_manager
        try:
            terminal = Terminal._base_manager.select_related(
                "created_by",
                "created_by__timezone",
                "created_by__userprofilelink",
                "created_by__userprofilelink__group"
            ).get(id=terminal_id)
        except Terminal.DoesNotExist:
            logger.warning(
                "[TERMINAL][SCHEDULE] Terminal with ID %s not found",
                terminal_id
            )
            return
        
        # Bỏ qua TEMP terminals
        if terminal.terminal_types.filter(code="TEMP").exists():
            return
        
        terminal_tz = get_terminal_timezone(terminal)
        localized_now = now.astimezone(terminal_tz) if timezone.is_aware(now) else timezone.make_aware(now, terminal_tz)

        # Kiểm tra trạng thái hiện tại và schedule task để cập nhật ngay nếu cần
        # Điều này đảm bảo terminal được cập nhật ngay khi operating time thay đổi
        should_be_active_now = should_terminal_be_active(terminal, localized_now, tz=terminal_tz)
        if terminal.active != should_be_active_now:
            # Schedule task để cập nhật ngay lập tức (countdown=0 hoặc eta=now)
            try:
                activate_single_terminal.apply_async(
                    args=[terminal.id, should_be_active_now],
                    countdown=0,  # Chạy ngay lập tức
                    expires=now + timedelta(minutes=5)  # Expire sau 5 phút
                )
                logger.info(
                    "[TERMINAL][SCHEDULE] Scheduled immediate %s for terminal %s (ID: %s) due to operating time change",
                    "activation" if should_be_active_now else "deactivation",
                    terminal.name,
                    terminal.id
                )
            except Exception as e:
                logger.error(
                    "[TERMINAL][SCHEDULE] Error scheduling immediate update for terminal %s (ID: %s): %s",
                    terminal.name,
                    terminal.id,
                    str(e)
                )

        # Tính toán các thời điểm activate/deactivate trong khoảng thời gian chỉ định
        activation_times = calculate_next_activation_times(
            terminal,
            localized_now,
            days_ahead=days_ahead,
            tz=terminal_tz,
        )
        
        scheduled_count = 0
        skipped_count = 0
        
        # Schedule các task với ETA
        for activation_datetime, should_be_active in activation_times:
            # Convert activation_datetime về UTC để tính seconds_until chính xác
            # activation_datetime đã ở timezone của terminal, cần convert về UTC để so sánh với now (UTC)
            activation_datetime_utc = activation_datetime.astimezone(dt_timezone.utc) if timezone.is_aware(activation_datetime) else timezone.make_aware(activation_datetime, terminal_tz).astimezone(dt_timezone.utc)
            
            # Tính số giây từ bây giờ (UTC) đến thời điểm đó (UTC)
            seconds_until = (activation_datetime_utc - now).total_seconds()
            
            # Chỉ schedule các task trong tương lai và không quá xa (tối đa days_ahead ngày)
            if seconds_until > 0:
                # Tạo unique task_id dựa trên terminal_id, datetime và action
                # Format: terminal_activation_{terminal_id}_{timestamp}_{action}
                # Ví dụ: terminal_activation_988_20251125120000_activate
                timestamp_str = activation_datetime.strftime("%Y%m%d%H%M%S")
                action_str = "activate" if should_be_active else "deactivate"
                task_id = f"terminal_activation_{terminal.id}_{timestamp_str}_{action_str}"
                
                try:
                    # Sử dụng task_id để Celery tự động handle duplicate
                    # Nếu task với cùng task_id đã tồn tại, Celery sẽ replace nó
                    activate_single_terminal.apply_async(
                        args=[terminal.id, should_be_active],
                        countdown=int(seconds_until),
                        expires=activation_datetime_utc + timedelta(minutes=5),  # Expire sau 5 phút (UTC)
                        task_id=task_id  # Unique task ID để tránh duplicate
                    )
                    scheduled_count += 1
                    
                    logger.info(
                        "[TERMINAL][SCHEDULE] Scheduled terminal %s (ID: %s) to %s at %s (UTC: %s, task_id: %s)",
                        terminal.name,
                        terminal.id,
                        action_str,
                        activation_datetime.strftime("%Y-%m-%d %H:%M:%S %Z"),
                        activation_datetime_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        task_id
                    )
                except Exception as e:
                    # Nếu task đã tồn tại hoặc có lỗi khác, log và tiếp tục
                    logger.debug(
                        "[TERMINAL][SCHEDULE] Task %s may already exist or error: %s",
                        task_id,
                        str(e)
                    )
                    skipped_count += 1
        
        logger.info(
            "[TERMINAL][SCHEDULE] Scheduled %s activation tasks for terminal %s (ID: %s), skipped %s duplicates",
            scheduled_count,
            terminal.name,
            terminal.id,
            skipped_count
        )
        
    except Exception as exc:
        logger.exception(
            "[TERMINAL][SCHEDULE] Error scheduling terminal %s activations: %s",
            terminal_id,
            exc
        )
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def schedule_terminal_activation_tasks(self) -> None:
    """
    Task chạy định kỳ (mỗi 30 phút hoặc 1 giờ) để tính toán và schedule các task activate/deactivate
    cho tất cả terminals có operating times hoặc exceptions
    Sử dụng Celery ETA (estimated time of arrival)
    
    LƯU Ý: Sử dụng _base_manager cho tất cả model access vì task không có request context
    """
    try:
        from terminals.models import Terminal, TerminalOperatingTime, TerminalException
        from django.db.models import Q
        
        # NOTE: close_old_connections() đã được gọi tự động bởi task_prerun signal trong celery.py
        # Chỉ cần gọi lại khi retry sau SSL/connection errors
        
        now = timezone.now()
        if now.tzinfo != pytz.UTC:
            now = now.astimezone(pytz.UTC)
        
        # Lấy tất cả terminals có operating times hoặc exceptions - dùng _base_manager
        # Retry logic để xử lý SSL/connection errors và AssertionError từ SQLAlchemy pool
        from django.db import close_old_connections, connections
        from django.db.utils import OperationalError, InterfaceError
        
        max_query_retries = 3
        terminals = None
        for query_attempt in range(max_query_retries):
            try:
                terminals_qs = Terminal._base_manager.filter(
                    Q(operating_times__isnull=False) | Q(exceptions__isnull=False)
                ).exclude(terminal_types__code__in=["TEMP"])

                terminals_qs = terminals_qs.select_related(
                    "created_by",
                    "created_by__timezone",
                    "created_by__userprofilelink",
                    "created_by__userprofilelink__group"
                )

                terminals = terminals_qs.distinct()
                # Test query by getting first item
                _ = terminals.first()
                break  # Success, exit retry loop
            except AssertionError as e:
                # AssertionError từ SQLAlchemy pool = connection đã chết trong pool
                if query_attempt < max_query_retries - 1:
                    logger.warning(
                        "[TERMINAL][SCHEDULE] SQLAlchemy pool AssertionError (stale connection) on attempt %s/%s, retrying: %s",
                        query_attempt + 1,
                        max_query_retries,
                        str(e)
                    )
                    close_old_connections()
                    connections.close_all()
                    continue
                else:
                    logger.error(
                        "[TERMINAL][SCHEDULE] SQLAlchemy pool AssertionError after %s attempts: %s",
                        max_query_retries,
                        str(e)
                    )
                    raise
            except (OperationalError, InterfaceError) as e:
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ['ssl', 'connection', 'eof', 'closed', 'bad record', 'wrong version', 'decryption']):
                    if query_attempt < max_query_retries - 1:
                        logger.warning(
                            "[TERMINAL][SCHEDULE] SSL/Connection error khi query terminals (attempt %s/%s): %s, retrying...",
                            query_attempt + 1,
                            max_query_retries,
                            str(e)
                        )
                        close_old_connections()
                        connections.close_all()
                        continue
                    else:
                        logger.error(
                            "[TERMINAL][SCHEDULE] SSL/Connection error sau %s attempts khi query terminals: %s",
                            max_query_retries,
                            str(e)
                        )
                        raise
                else:
                    # Not a connection error, re-raise immediately
                    raise
        
        if terminals is None:
            logger.error("[TERMINAL][SCHEDULE] Không thể query terminals sau %s attempts", max_query_retries)
            return
        
        scheduled_count = 0
        error_count = 0
        
        # Sử dụng iterator để tránh load tất cả vào memory và giảm connection timeout
        for terminal in terminals.iterator(chunk_size=50):
            try:
                terminal_tz = get_terminal_timezone(terminal)
                localized_now = now.astimezone(terminal_tz) if timezone.is_aware(now) else timezone.make_aware(now, terminal_tz)
                
                # Kiểm tra trạng thái hiện tại và schedule task để cập nhật ngay nếu cần
                # Điều này đảm bảo terminal được cập nhật ngay khi task chạy
                should_be_active_now = should_terminal_be_active(terminal, localized_now, tz=terminal_tz)
                if terminal.active != should_be_active_now:
                    # Schedule task để cập nhật ngay lập tức (countdown=0)
                    try:
                        activate_single_terminal.apply_async(
                            args=[terminal.id, should_be_active_now],
                            countdown=0,  # Chạy ngay lập tức
                            expires=now + timedelta(minutes=5)  # Expire sau 5 phút
                        )
                        logger.info(
                            "[TERMINAL][SCHEDULE] Scheduled immediate %s for terminal %s (ID: %s) due to status mismatch",
                            "activation" if should_be_active_now else "deactivation",
                            terminal.name,
                            terminal.id
                        )
                    except Exception as e:
                        logger.error(
                            "[TERMINAL][SCHEDULE] Error scheduling immediate update for terminal %s (ID: %s): %s",
                            terminal.name,
                            terminal.id,
                            str(e)
                        )
                
                # Tính next_hour ở timezone của terminal để so sánh chính xác
                localized_next_hour = localized_now + timedelta(hours=1)

                # Tính toán các thời điểm activate/deactivate trong giờ tiếp theo
                activation_times = calculate_next_activation_times(
                    terminal,
                    localized_now,
                    days_ahead=1,
                    tz=terminal_tz,
                )
                
                # Chỉ lấy các thời điểm trong giờ tiếp theo (so sánh ở cùng timezone)
                next_hour_times = [
                    (dt, active) for dt, active in activation_times
                    if dt <= localized_next_hour
                ]
                
                # Schedule các task với ETA
                for activation_datetime, should_be_active in next_hour_times:
                    # Convert activation_datetime về UTC để tính seconds_until chính xác
                    # activation_datetime đã ở timezone của terminal, cần convert về UTC để so sánh với now (UTC)
                    activation_datetime_utc = activation_datetime.astimezone(dt_timezone.utc) if timezone.is_aware(activation_datetime) else timezone.make_aware(activation_datetime, terminal_tz).astimezone(dt_timezone.utc)
                    
                    # Tính số giây từ bây giờ (UTC) đến thời điểm đó (UTC)
                    seconds_until = (activation_datetime_utc - now).total_seconds()
                    
                    if seconds_until > 0 and seconds_until <= 3600:  # Chỉ schedule trong vòng 1 giờ
                        activate_single_terminal.apply_async(
                            args=[terminal.id, should_be_active],
                            countdown=int(seconds_until),
                            expires=activation_datetime_utc + timedelta(minutes=5)  # Expire sau 5 phút
                        )
                        scheduled_count += 1
                        
                        logger.info(
                            "[TERMINAL][SCHEDULE] Scheduled terminal %s (ID: %s) to %s at %s (UTC: %s)",
                            terminal.name,
                            terminal.id,
                            "activate" if should_be_active else "deactivate",
                            activation_datetime.strftime("%Y-%m-%d %H:%M:%S %Z"),
                            activation_datetime_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
                        )
            except Exception as e:
                error_count += 1
                logger.error(
                    "[TERMINAL][SCHEDULE] Error scheduling terminal %s (ID: %s): %s",
                    terminal.name,
                    terminal.id,
                    str(e)
                )
                continue
        
        logger.info(
            "[TERMINAL][SCHEDULE] Scheduled %s activation tasks for next hour, errors %s (task=%s)",
            scheduled_count,
            error_count,
            getattr(self.request, "id", None)
        )
        
    except Exception as exc:
        logger.exception("[TERMINAL][SCHEDULE] Error scheduling terminal activations: %s", exc)
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def activate_single_terminal(self, terminal_id: int, should_be_active: bool) -> None:
    """
    Task để activate/deactivate một terminal cụ thể
    Được schedule với ETA để chạy đúng thời điểm
    
    LƯU Ý: Sử dụng _base_manager cho tất cả model access vì task không có request context
    """
    try:
        from terminals.models import Terminal
        from terminals.services.terminal_service import TerminalService
        
        # Dùng _base_manager để bypass custom manager filter
        # Prefetch created_by và group để cache invalidation có thể detect group đúng cách
        terminal = Terminal._base_manager.select_related(
            'created_by',
            'created_by__userprofilelink',
            'created_by__userprofilelink__group'
        ).prefetch_related('terminal_types').get(id=terminal_id)
        service = TerminalService()
        
        # Kiểm tra lại trạng thái hiện tại (có thể đã thay đổi)
        if terminal.active == should_be_active:
            logger.info(
                "[TERMINAL][AUTO] Terminal %s (ID: %s) already in correct state (%s)",
                terminal.name,
                terminal.id,
                "active" if should_be_active else "inactive"
            )
            return
        
        if should_be_active:
            success, error = service._activate_single_terminal(
                terminal,
                skip_transit_check=True
            )
            action = "activated"
        else:
            success, error = service._deactivate_single_terminal(
                terminal,
                skip_transit_check=True,
                skip_validation=True,
                deactivate_reason=None
            )
            action = "deactivated"
        
        if success:
            logger.info(
                "[TERMINAL][AUTO] %s terminal %s (ID: %s)",
                action.capitalize(),
                terminal.name,
                terminal.id
            )
        else:
            logger.warning(
                "[TERMINAL][AUTO] Failed to %s terminal %s (ID: %s): %s",
                action,
                terminal.name,
                terminal.id,
                error
            )
            
    except Terminal.DoesNotExist:
        logger.warning(
            "[TERMINAL][AUTO] Terminal with ID %s not found",
            terminal_id
        )
    except Exception as exc:
        logger.exception(
            "[TERMINAL][AUTO] Error processing terminal %s: %s",
            terminal_id,
            exc
        )
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60, ignore_result=True)
def process_terminal_auto_activation(self) -> None:
    """
    Task chạy định kỳ để tự động active/inactive terminal theo lịch
    Chạy mỗi phút để kiểm tra và cập nhật trạng thái (backup/fallback)
    Sử dụng logic activate/deactivate để đảm bảo đồng bộ hub-docking relationships
    
    LƯU Ý: Sử dụng _base_manager cho tất cả model access vì task không có request context
    """
    try:
        from terminals.models import Terminal, TerminalOperatingTime, TerminalException
        from terminals.services.terminal_service import TerminalService
        from django.db.models import Q
        
        # NOTE: close_old_connections() đã được gọi tự động bởi task_prerun signal trong celery.py
        # Chỉ cần gọi lại khi retry sau SSL/connection errors
        
        now = timezone.now()
        if now.tzinfo != pytz.UTC:
            now = now.astimezone(pytz.UTC)
        updated_count = 0
        error_count = 0
        
        # Lấy tất cả terminals có operating times hoặc exceptions - dùng _base_manager
        # Retry logic để xử lý SSL/connection errors và AssertionError từ SQLAlchemy pool
        from django.db import close_old_connections, connections
        from django.db.utils import OperationalError, InterfaceError
        
        max_query_retries = 3
        terminals = None
        for query_attempt in range(max_query_retries):
            try:
                terminals = (
                    Terminal._base_manager.filter(
                        Q(operating_times__isnull=False) | Q(exceptions__isnull=False)
                    )
                    .select_related(
                        "created_by", 
                        "created_by__timezone",
                        "created_by__userprofilelink",
                        "created_by__userprofilelink__group"
                    )
                    .distinct()
                )
                # Test query by getting first item
                _ = terminals.first()
                break  # Success, exit retry loop
            except AssertionError as e:
                # AssertionError từ SQLAlchemy pool = connection đã chết trong pool
                if query_attempt < max_query_retries - 1:
                    logger.warning(
                        "[TERMINAL][AUTO] SQLAlchemy pool AssertionError (stale connection) on attempt %s/%s, retrying: %s",
                        query_attempt + 1,
                        max_query_retries,
                        str(e)
                    )
                    close_old_connections()
                    connections.close_all()
                    continue
                else:
                    logger.error(
                        "[TERMINAL][AUTO] SQLAlchemy pool AssertionError after %s attempts: %s",
                        max_query_retries,
                        str(e)
                    )
                    raise
            except (OperationalError, InterfaceError) as e:
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ['ssl', 'connection', 'eof', 'closed', 'bad record', 'wrong version', 'decryption']):
                    if query_attempt < max_query_retries - 1:
                        logger.warning(
                            "[TERMINAL][AUTO] SSL/Connection error khi query terminals (attempt %s/%s): %s, retrying...",
                            query_attempt + 1,
                            max_query_retries,
                            str(e)
                        )
                        close_old_connections()
                        connections.close_all()
                        continue
                    else:
                        logger.error(
                            "[TERMINAL][AUTO] SSL/Connection error sau %s attempts khi query terminals: %s",
                            max_query_retries,
                            str(e)
                        )
                        raise
                else:
                    # Not a connection error, re-raise immediately
                    raise
        
        if terminals is None:
            logger.error("[TERMINAL][AUTO] Không thể query terminals sau %s attempts", max_query_retries)
            return
        
        service = TerminalService()
        
        # Sử dụng iterator để tránh load tất cả vào memory và giảm connection timeout
        for terminal in terminals.iterator(chunk_size=50):
            try:
                terminal_tz = get_terminal_timezone(terminal)
                localized_now = now.astimezone(terminal_tz) if timezone.is_aware(now) else timezone.make_aware(now, terminal_tz)

                should_be_active = should_terminal_be_active(terminal, localized_now, tz=terminal_tz)
                
                # Chỉ cập nhật nếu trạng thái khác với trạng thái hiện tại
                if terminal.active != should_be_active:
                    if should_be_active:
                        # Activate terminal với logic đầy đủ (bao gồm activate dockings liên quan)
                        success, error = service._activate_single_terminal(
                            terminal, 
                            skip_transit_check=True  # Skip transit check cho auto activation
                        )
                        if success:
                            updated_count += 1
                            logger.info(
                                "[TERMINAL][AUTO] Activated terminal %s (ID: %s)",
                                terminal.name,
                                terminal.id
                            )
                        else:
                            error_count += 1
                            logger.warning(
                                "[TERMINAL][AUTO] Failed to activate terminal %s (ID: %s): %s",
                                terminal.name,
                                terminal.id,
                                error
                            )
                    else:
                        # Deactivate terminal với logic đầy đủ (bao gồm deactivate dockings liên quan)
                        # Skip validation cho auto activation vì đây là tự động theo lịch
                        success, error = service._deactivate_single_terminal(
                            terminal,
                            skip_transit_check=True,  # Skip transit check cho auto activation
                            skip_validation=True,     # Skip validation cho auto activation
                            deactivate_reason=None    # Không set reason cho auto activation
                        )
                        if success:
                            updated_count += 1
                            logger.info(
                                "[TERMINAL][AUTO] Deactivated terminal %s (ID: %s)",
                                terminal.name,
                                terminal.id
                            )
                        else:
                            error_count += 1
                            logger.warning(
                                "[TERMINAL][AUTO] Failed to deactivate terminal %s (ID: %s): %s",
                                terminal.name,
                                terminal.id,
                                error
                            )
            except Exception as e:
                error_count += 1
                logger.error(
                    "[TERMINAL][AUTO] Error processing terminal %s (ID: %s): %s",
                    terminal.name,
                    terminal.id,
                    str(e)
                )
                continue
        
        if updated_count > 0 or error_count > 0:
            logger.info(
                "[TERMINAL][AUTO] Processed %s terminals, updated %s, errors %s (task=%s)",
                terminals.count(),
                updated_count,
                error_count,
                getattr(self.request, "id", None)
            )
        
    except Exception as exc:
        logger.exception("[TERMINAL][AUTO] Error processing terminal auto activation: %s", exc)
        raise


def _process_import_plan_in_thread(plan_file_content: bytes, plan_file_name: str, import_task_id: str, user_id: int, service_id: int | None = None):
    """
    Process plan file import in background thread
    Updates TaskStatus để FE có thể poll status qua API
    
    Args:
        plan_file_content: Content of the plan file (bytes)
        plan_file_name: Name of the plan file
        import_task_id: Task ID for tracking
        user_id: ID of the user who initiated the import
    """
    from core.user.models import CoreUser
    from terminals.services.qground_control_service import QGroundControlService
    from django.core.files.uploadedfile import InMemoryUploadedFile
    from io import BytesIO
    from core.middleware.refresh_token import thread_local
    
    task_type = "qground_control_import_plan"
    
    try:
        logger.info(f"🔄 Starting plan file import processing for task {import_task_id}")
        
        # Get user
        user = CoreUser.objects.get(id=user_id)

        # 🧵 IMPORTANT: Seed thread-local "request" context for background thread
        # Many BaseModel / CustomManagerGroup implementations rely on get_current_request().user
        # to auto-populate created_by/modified_by/group (and sometimes to allow queryset access).
        previous_request = getattr(thread_local, "request", None)

        class _ThreadRequest:
            def __init__(self, user):
                self.user = user
                self.GET = {}
                self.META = {"REMOTE_ADDR": "127.0.0.1"}
                self.method = "THREAD"

        thread_local.request = _ThreadRequest(user)
        
        # Update status to processing
        processing_message = get_message(MESSAGE_ENUM.IMPORT_PLAN_SUCCESS)  # Có thể tạo message riêng cho processing
        TaskStatusService.update_status(
            import_task_id,
            status="processing",
            message=processing_message,
            action="qground_control_import_plan",
            task_channel=f"terminals_{user.username}",
            trigger_source="qground_control.import_plan",
            progress=10.0,
        )
        
        # Create InMemoryUploadedFile from bytes
        file_obj = BytesIO(plan_file_content)
        uploaded_file = InMemoryUploadedFile(
            file_obj,
            None,
            plan_file_name,
            'application/json',
            len(plan_file_content),
            None
        )
        
        # Update progress: File parsed
        TaskStatusService.update_status(
            import_task_id,
            "processing",  # status vẫn là processing
            progress=20.0,
        )
        
        # Import plan file
        service = QGroundControlService()
        success, result = service.import_plan_file(uploaded_file, plan_file_name, service_id)
        
        if success:
            # Import successful
            route = result
            success_message = get_message(MESSAGE_ENUM.IMPORT_PLAN_SUCCESS)
            
            # Prepare data for notification
            data = {
                'route_id': route.id,
                'route_name': route.name,
                'terminal_count': route.route_terminals.count() if hasattr(route, 'route_terminals') else 0,
            }
            
            TaskStatusService.update_status(
                import_task_id,
                status="success",
                message=success_message,
                progress=100.0,
                data=data,
            )
            logger.info(f"✅ Plan file import completed successfully for task {import_task_id}")
        else:
            # Import failed
            error_message = f"{get_message(MESSAGE_ENUM.IMPORT_PLAN_FAILED)}: {result}"
            TaskStatusService.update_status(
                import_task_id,
                status="failed",
                message=error_message,
                progress=0.0,
                error_code="IMPORT_FAILED",
                error_details={"error": str(result)},
            )
            logger.error(f"❌ Plan file import failed for task {import_task_id}: {result}")
            
    except Exception as e:
        logger.exception(f"❌ Error processing plan file import for task {import_task_id}: {e}")
        
        # Update task status to failed
        try:
            user = CoreUser.objects.get(id=user_id)
            error_message = f"{get_message(MESSAGE_ENUM.IMPORT_PLAN_FAILED)}: {str(e)}"
            TaskStatusService.update_status(
                import_task_id,
                status="failed",
                message=error_message,
                progress=0.0,
                error_code="IMPORT_ERROR",
                error_details={"error": str(e)},
            )
        except Exception as update_error:
            logger.error(f"❌ Error updating task status: {update_error}")
    finally:
        # Restore/cleanup thread-local request (best-effort)
        try:
            if previous_request is None:
                if hasattr(thread_local, "request"):
                    delattr(thread_local, "request")
            else:
                thread_local.request = previous_request
        except Exception:
            pass

