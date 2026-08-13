"""
Service để xử lý TerminalException
"""

from django.db import transaction
from django.db.models import Model, QuerySet
from typing import Tuple, Optional, List
from datetime import time as dt_time, date
from terminals.models import Terminal, TerminalException
from terminals.services.datetime_utils import flexible_time_parser, flexible_date_parser
from common.constant import MESSAGE_ENUM, get_message


class ExceptionService:
    """Service class cho TerminalException operations"""
    
    @staticmethod
    def parse_time_string(time_str: Optional[str]) -> Optional[dt_time]:
        """
        Chuyển đổi string time thành time object với hỗ trợ đa định dạng.
        
        Supported formats:
            - 24 hour: HH:MM (e.g., "14:30")
            - 12 hour: HH:MM AM/PM (e.g., "02:30 PM")
            - 24_full: HH:MM:SS (e.g., "14:30:45")
            - 12_full: HH:MM:SS AM/PM (e.g., "02:30:45 PM")
        
        Args:
            time_str: Time string to parse
            
        Returns:
            datetime.time object or None if parsing fails
        """
        return flexible_time_parser(time_str)
    
    @staticmethod
    def parse_date_string(date_str: Optional[str]) -> Optional[date]:
        """
        Chuyển đổi string date thành date object với hỗ trợ đa định dạng.
        
        Supported formats:
            - YYYY-MM-DD (%Y-%m-%d): "2024-01-15"
            - DD/MM/YYYY (%d/%m/%Y): "15/01/2024"
            - MM/DD/YYYY (%m/%d/%Y): "01/15/2024"
            - DD-MM-YYYY (%d-%m-%Y): "15-01-2024"
            - Month DD, YYYY (%B %d, %Y): "January 15, 2024"
            - DD Month YYYY (%d %B %Y): "15 January 2024"
            - YYYY/MM/DD (%Y/%m/%d): "2024/01/15"
            - YY/MM/DD (%y/%m/%d): "24/01/15"
        
        Args:
            date_str: Date string to parse
            
        Returns:
            datetime.date object or None if parsing fails
        """
        return flexible_date_parser(date_str)
    
    @staticmethod
    def get(exception_id: int) -> Optional[TerminalException]:
        """Lấy exception theo ID"""
        try:
            return TerminalException.objects.select_related('terminal').get(id=exception_id)
        except TerminalException.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_terminal(terminal_id: int) -> QuerySet[TerminalException]:
        """Lấy tất cả exceptions của một terminal"""
        return TerminalException.objects.filter(terminal_id=terminal_id).order_by('exception_date')
    
    @staticmethod
    @transaction.atomic
    def create(data: dict) -> Tuple[bool, TerminalException | str]:
        """Tạo mới exception"""
        try:
            terminal_id = data.get('terminal_id')
            if not terminal_id:
                return False, "Terminal ID is required"
            
            terminal = Terminal.objects.get(id=terminal_id)
            
            exception_date_raw = data.get('exception_date')
            if not exception_date_raw:
                return False, "Exception date is required"
            
            # Parse exception_date with flexible format support
            exception_date = ExceptionService.parse_date_string(exception_date_raw) \
                if isinstance(exception_date_raw, str) else exception_date_raw
            
            if not exception_date:
                return False, f"Invalid exception date format: {exception_date_raw}"
            
            is_all_day = data.get('is_all_day', False)
            start_time_str = data.get('start_time')
            end_time_str = data.get('end_time')
            reason = data.get('reason')
            
            start_time = None
            end_time = None
            
            if not is_all_day:
                start_time = ExceptionService.parse_time_string(start_time_str) if start_time_str else None
                end_time = ExceptionService.parse_time_string(end_time_str) if end_time_str else None
                
                if not start_time or not end_time:
                    return False, "Start time and end time are required when is_all_day is False"
            
            exception = TerminalException.objects.create(
                terminal=terminal,
                exception_date=exception_date,
                start_time=start_time,
                end_time=end_time,
                is_all_day=is_all_day,
                reason=reason
            )
            
            return True, exception
            
        except Terminal.DoesNotExist:
            return False, "Terminal not found"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def bulk_create(terminal_id: int, exceptions_data: List[dict]) -> Tuple[bool, List[TerminalException] | str]:
        """
        Tạo nhiều exceptions cùng lúc
        Tối ưu performance: sử dụng bulk_create thay vì loop INSERT
        """
        try:
            terminal = Terminal.objects.get(id=terminal_id)
            
            if not exceptions_data:
                return True, []
            
            exception_objects = []
            parsed_exception_dates = []
            
            for data in exceptions_data:
                exception_date_raw = data.get('exception_date')
                if not exception_date_raw:
                    return False, "Exception date is required"
                
                # Parse exception_date with flexible format support
                exception_date = ExceptionService.parse_date_string(exception_date_raw) \
                    if isinstance(exception_date_raw, str) else exception_date_raw
                
                if not exception_date:
                    return False, f"Invalid exception date format: {exception_date_raw}"
                
                parsed_exception_dates.append(exception_date)
                
                is_all_day = data.get('is_all_day', False)
                start_time_str = data.get('start_time')
                end_time_str = data.get('end_time')
                reason = data.get('reason')
                
                start_time = None
                end_time = None
                
                if not is_all_day:
                    start_time = ExceptionService.parse_time_string(start_time_str) if start_time_str else None
                    end_time = ExceptionService.parse_time_string(end_time_str) if end_time_str else None
                    
                    if not start_time or not end_time:
                        return False, "Start time and end time are required when is_all_day is False"
                
                exception_objects.append(
                    TerminalException(
                        terminal=terminal,
                        exception_date=exception_date,
                        start_time=start_time,
                        end_time=end_time,
                        is_all_day=is_all_day,
                        reason=reason
                    )
                )
            
            # OPTIMIZATION: Bulk create tất cả trong 1 query
            if exception_objects:
                TerminalException.objects.bulk_create(exception_objects, ignore_conflicts=False)
                # Query lại để lấy các objects đã tạo với IDs
                result = list(TerminalException.objects.filter(
                    terminal=terminal,
                    exception_date__in=parsed_exception_dates
                ))
            else:
                result = []
            
            return True, result
            
        except Terminal.DoesNotExist:
            return False, "Terminal not found"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def smart_sync(terminal_id: int, exceptions_data: List[dict]) -> Tuple[bool, List[TerminalException] | str]:
        """
        Smart sync: So sánh dữ liệu cũ và mới, chỉ UPDATE/CREATE/DELETE những gì thay đổi
        Ưu điểm:
        - Giữ được created_at, updated_at chính xác
        - Giữ được ID của records
        - Performance tốt hơn (ít queries)
        - Audit logs chính xác hơn
        
        Args:
            terminal_id: ID của terminal
            exceptions_data: List các exceptions mới (nếu có id thì UPDATE, không có id thì CREATE)
        
        Returns:
            Tuple[bool, List[TerminalException] | str]
        """
        try:
            terminal = Terminal.objects.get(id=terminal_id)
            
            # Lấy dữ liệu cũ (dùng id làm key)
            existing_exceptions = {
                exc.id: exc 
                for exc in TerminalException.objects.filter(terminal_id=terminal_id)
            }
            
            # Nếu không có dữ liệu mới, xóa hết
            if not exceptions_data:
                if existing_exceptions:
                    TerminalException.objects.filter(terminal_id=terminal_id).delete()
                return True, []
            
            # Phân loại: UPDATE, CREATE, DELETE
            to_update = []
            to_create = []
            # Lấy các id từ data (chỉ lấy những id hợp lệ, không phải None)
            new_exception_ids = {data.get('id') for data in exceptions_data if data.get('id') is not None}
            existing_exception_ids = set(existing_exceptions.keys())
            
            # DELETE: Những cái không còn trong list mới (có id nhưng không có trong list mới)
            to_delete_ids = existing_exception_ids - new_exception_ids
            if to_delete_ids:
                TerminalException.objects.filter(
                    terminal_id=terminal_id,
                    id__in=to_delete_ids
                ).delete()
            
            # UPDATE/CREATE: Xử lý từng item trong list mới
            for data in exceptions_data:
                exception_id = data.get('id')
                exception_date_raw = data.get('exception_date')
                if not exception_date_raw:
                    return False, "Exception date is required"
                
                # Parse exception_date with flexible format support
                exception_date = ExceptionService.parse_date_string(exception_date_raw) \
                    if isinstance(exception_date_raw, str) else exception_date_raw
                
                if not exception_date:
                    return False, f"Invalid exception date format: {exception_date_raw}"
                
                is_all_day = data.get('is_all_day', False)
                start_time_str = data.get('start_time')
                end_time_str = data.get('end_time')
                reason = data.get('reason')
                
                start_time = None
                end_time = None
                
                if not is_all_day:
                    start_time = ExceptionService.parse_time_string(start_time_str) if start_time_str else None
                    end_time = ExceptionService.parse_time_string(end_time_str) if end_time_str else None
                    
                    if not start_time or not end_time:
                        return False, "Start time and end time are required when is_all_day is False"
                
                # Kiểm tra xem có id không (nếu có id thì UPDATE, không có thì CREATE)
                if exception_id and exception_id in existing_exceptions:
                    # UPDATE: So sánh xem có thay đổi không
                    existing = existing_exceptions[exception_id]
                    if (existing.exception_date != exception_date or
                        existing.is_all_day != is_all_day or 
                        existing.start_time != start_time or 
                        existing.end_time != end_time or
                        existing.reason != reason):
                        existing.exception_date = exception_date
                        existing.is_all_day = is_all_day
                        existing.start_time = start_time
                        existing.end_time = end_time
                        existing.reason = reason
                        to_update.append(existing)
                else:
                    # CREATE (không có id hoặc id không tồn tại)
                    to_create.append(TerminalException(
                        terminal=terminal,
                        exception_date=exception_date,
                        start_time=start_time,
                        end_time=end_time,
                        is_all_day=is_all_day,
                        reason=reason
                    ))
            
            # Bulk update
            if to_update:
                TerminalException.objects.bulk_update(
                    to_update, 
                    ['exception_date', 'is_all_day', 'start_time', 'end_time', 'reason'],
                    batch_size=100
                )
            
            # Bulk create
            if to_create:
                TerminalException.objects.bulk_create(to_create, batch_size=100)
            
            # Query lại để trả về kết quả
            result = list(TerminalException.objects.filter(terminal_id=terminal_id))
            
            return True, result
            
        except Terminal.DoesNotExist:
            return False, "Terminal not found"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def update(exception_id: int, data: dict) -> Tuple[bool, TerminalException | str]:
        """Cập nhật exception"""
        try:
            exception = ExceptionService.get(exception_id)
            if not exception:
                return False, "Exception not found"
            
            exception_date_raw = data.get('exception_date')
            is_all_day = data.get('is_all_day')
            start_time_str = data.get('start_time')
            end_time_str = data.get('end_time')
            reason = data.get('reason')
            
            if exception_date_raw is not None:
                # Parse exception_date with flexible format support
                exception_date = ExceptionService.parse_date_string(exception_date_raw) \
                    if isinstance(exception_date_raw, str) else exception_date_raw
                
                if not exception_date:
                    return False, f"Invalid exception date format: {exception_date_raw}"
                
                exception.exception_date = exception_date
            
            if is_all_day is not None:
                exception.is_all_day = is_all_day
            
            if start_time_str is not None:
                exception.start_time = ExceptionService.parse_time_string(start_time_str) if start_time_str else None
            elif start_time_str == "":
                exception.start_time = None
            
            if end_time_str is not None:
                exception.end_time = ExceptionService.parse_time_string(end_time_str) if end_time_str else None
            elif end_time_str == "":
                exception.end_time = None
            
            if reason is not None:
                exception.reason = reason
            
            # Validation: nếu is_all_day=False thì phải có start_time và end_time
            if not exception.is_all_day and (not exception.start_time or not exception.end_time):
                return False, "Start time and end time are required when is_all_day is False"
            
            exception.save()
            return True, exception
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def delete(exception_id: int) -> Tuple[bool, str]:
        """Xóa exception"""
        try:
            exception = ExceptionService.get(exception_id)
            if not exception:
                return False, "Exception not found"
            
            exception.delete()
            return True, get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
            
        except Exception as e:
            return False, str(e)


# Backward compatibility: Export functions for existing code
def get_exception(exception_id: int) -> Optional[TerminalException]:
    return ExceptionService.get(exception_id)

def get_exceptions_by_terminal(terminal_id: int) -> List[TerminalException]:
    return ExceptionService.get_by_terminal(terminal_id)

def parse_time_string(time_str: Optional[str]) -> Optional[dt_time]:
    return ExceptionService.parse_time_string(time_str)

def create_exception(data: dict) -> Tuple[bool, TerminalException | str]:
    return ExceptionService.create(data)

def update_exception(exception_id: int, data: dict) -> Tuple[bool, TerminalException | str]:
    return ExceptionService.update(exception_id, data)

def delete_exception(exception_id: int) -> Tuple[bool, str]:
    return ExceptionService.delete(exception_id)

def bulk_create_exceptions(terminal_id: int, exceptions_data: List[dict]) -> Tuple[bool, List[TerminalException] | str]:
    return ExceptionService.bulk_create(terminal_id, exceptions_data)
