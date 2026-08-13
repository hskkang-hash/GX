"""
Service để xử lý TerminalOperatingTime
"""

from django.db import transaction
from django.db.models import Model, QuerySet
from typing import Tuple, Optional, List
from datetime import time as dt_time
from terminals.models import Terminal, TerminalOperatingTime, DayOfWeek
from terminals.services.datetime_utils import flexible_time_parser
from common.constant import MESSAGE_ENUM, get_message


class OperatingTimeService:
    """Service class cho TerminalOperatingTime operations"""
    
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
    def get(operating_time_id: int) -> Optional[TerminalOperatingTime]:
        """Lấy operating time theo ID"""
        try:
            return TerminalOperatingTime.objects.select_related('terminal', 'day_of_week').get(id=operating_time_id)
        except TerminalOperatingTime.DoesNotExist:
            return None
    
    @staticmethod
    def get_by_terminal(terminal_id: int) -> QuerySet[TerminalOperatingTime]:
        """Lấy tất cả operating times của một terminal"""
        return TerminalOperatingTime.objects.filter(terminal_id=terminal_id).select_related('day_of_week').order_by('day_of_week__order')
    
    @staticmethod
    @transaction.atomic
    def create(data: dict) -> Tuple[bool, TerminalOperatingTime | str]:
        """Tạo mới operating time"""
        try:
            terminal_id = data.get('terminal_id')
            if not terminal_id:
                return False, "Terminal ID is required"
            
            terminal = Terminal.objects.get(id=terminal_id)
            
            day_of_week_id = data.get('day_of_week_id')
            if not day_of_week_id:
                return False, "Day of week ID is required"
            
            try:
                day_of_week = DayOfWeek.objects.get(id=day_of_week_id)
            except DayOfWeek.DoesNotExist:
                return False, "Day of week not found"
            
            # Kiểm tra xem đã tồn tại chưa
            if TerminalOperatingTime.objects.filter(terminal_id=terminal_id, day_of_week_id=day_of_week_id).exists():
                return False, f"Operating time for {day_of_week.name} already exists"
            
            is_active = data.get('is_active', False)
            start_time_str = data.get('start_time')
            end_time_str = data.get('end_time')
            
            start_time = OperatingTimeService.parse_time_string(start_time_str) if start_time_str else None
            end_time = OperatingTimeService.parse_time_string(end_time_str) if end_time_str else None
            
            # Validation: nếu is_active=True thì phải có start_time và end_time
            if is_active and (not start_time or not end_time):
                return False, "Start time and end time are required when is_active is True"
            
            operating_time = TerminalOperatingTime.objects.create(
                terminal=terminal,
                day_of_week=day_of_week,
                is_active=is_active,
                start_time=start_time,
                end_time=end_time
            )
            
            return True, operating_time
            
        except Terminal.DoesNotExist:
            return False, "Terminal not found"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def update(operating_time_id: int, data: dict) -> Tuple[bool, TerminalOperatingTime | str]:
        """Cập nhật operating time"""
        try:
            operating_time = OperatingTimeService.get(operating_time_id)
            if not operating_time:
                return False, "Operating time not found"
            
            is_active = data.get('is_active')
            start_time_str = data.get('start_time')
            end_time_str = data.get('end_time')
            
            day_of_week_id = data.get('day_of_week_id')
            if day_of_week_id is not None:
                try:
                    day_of_week = DayOfWeek.objects.get(id=day_of_week_id)
                    # Kiểm tra xem có conflict không (nếu đổi sang day_of_week khác)
                    if operating_time.day_of_week_id != day_of_week_id:
                        if TerminalOperatingTime.objects.filter(terminal_id=operating_time.terminal_id, day_of_week_id=day_of_week_id).exclude(id=operating_time_id).exists():
                            return False, f"Operating time for {day_of_week.name} already exists"
                    operating_time.day_of_week = day_of_week
                except DayOfWeek.DoesNotExist:
                    return False, "Day of week not found"
            
            if is_active is not None:
                operating_time.is_active = is_active
            
            if start_time_str is not None:
                start_time = OperatingTimeService.parse_time_string(start_time_str)
                operating_time.start_time = start_time
            elif start_time_str == "":
                operating_time.start_time = None
            
            if end_time_str is not None:
                end_time = OperatingTimeService.parse_time_string(end_time_str)
                operating_time.end_time = end_time
            elif end_time_str == "":
                operating_time.end_time = None
            
            # Validation: nếu is_active=True thì phải có start_time và end_time
            if operating_time.is_active and (not operating_time.start_time or not operating_time.end_time):
                return False, "Start time and end time are required when is_active is True"
            
            operating_time.save()
            return True, operating_time
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def delete(operating_time_id: int) -> Tuple[bool, str]:
        """Xóa operating time"""
        try:
            operating_time = OperatingTimeService.get(operating_time_id)
            if not operating_time:
                return False, "Operating time not found"
            
            operating_time.delete()
            return True, get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def bulk_create_or_update(terminal_id: int, operating_times_data: List[dict]) -> Tuple[bool, List[TerminalOperatingTime] | str]:
        """
        Tạo hoặc cập nhật nhiều operating times cùng lúc
        Tối ưu performance: sử dụng bulk_create thay vì loop INSERT
        """
        try:
            terminal = Terminal.objects.get(id=terminal_id)
            
            if not operating_times_data:
                return True, []
            
            # OPTIMIZATION: Prefetch tất cả DayOfWeek cần thiết trong 1 query
            day_of_week_ids = [data.get('day_of_week_id') for data in operating_times_data if data.get('day_of_week_id')]
            if not day_of_week_ids:
                return False, "Day of week ID is required"
            
            day_of_weeks = {dow.id: dow for dow in DayOfWeek.objects.filter(id__in=day_of_week_ids)}
            
            # Validate và prepare objects
            operating_time_objects = []
            for data in operating_times_data:
                day_of_week_id = data.get('day_of_week_id')
                if not day_of_week_id:
                    return False, "Day of week ID is required"
                
                day_of_week = day_of_weeks.get(day_of_week_id)
                if not day_of_week:
                    return False, f"Day of week with ID {day_of_week_id} not found"
                
                is_active = data.get('is_active', False)
                start_time_str = data.get('start_time')
                end_time_str = data.get('end_time')
                
                start_time = OperatingTimeService.parse_time_string(start_time_str) if start_time_str else None
                end_time = OperatingTimeService.parse_time_string(end_time_str) if end_time_str else None
                
                # Validation: nếu is_active=True thì phải có start_time và end_time
                if is_active and (not start_time or not end_time):
                    return False, f"Start time and end time are required when is_active is True for {day_of_week.name}"
                
                operating_time_objects.append(
                    TerminalOperatingTime(
                        terminal=terminal,
                        day_of_week=day_of_week,
                        is_active=is_active,
                        start_time=start_time,
                        end_time=end_time
                    )
                )
            
            # OPTIMIZATION: Bulk create tất cả trong 1 query
            if operating_time_objects:
                TerminalOperatingTime.objects.bulk_create(operating_time_objects, ignore_conflicts=False)
                # Query lại để lấy các objects đã tạo với IDs
                result = list(TerminalOperatingTime.objects.filter(
                    terminal=terminal,
                    day_of_week_id__in=day_of_week_ids
                ).select_related('day_of_week'))
            else:
                result = []
            
            return True, result
            
        except Terminal.DoesNotExist:
            return False, "Terminal not found"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def smart_sync(terminal_id: int, operating_times_data: List[dict]) -> Tuple[bool, List[TerminalOperatingTime] | str]:
        """
        Smart sync: So sánh dữ liệu cũ và mới, chỉ UPDATE/CREATE/DELETE những gì thay đổi
        Ưu điểm:
        - Giữ được created_at, updated_at chính xác
        - Giữ được ID của records (nếu có foreign keys khác)
        - Performance tốt hơn (ít queries)
        - Audit logs chính xác hơn
        
        Args:
            terminal_id: ID của terminal
            operating_times_data: List các operating times mới (nếu có id thì UPDATE, không có id thì CREATE)
        
        Returns:
            Tuple[bool, List[TerminalOperatingTime] | str]
        """
        try:
            terminal = Terminal.objects.get(id=terminal_id)
            
            # Lấy dữ liệu cũ (dùng id làm key)
            existing_operating_times = {
                ot.id: ot 
                for ot in TerminalOperatingTime.objects.filter(terminal_id=terminal_id).select_related('day_of_week')
            }
            
            # Nếu không có dữ liệu mới, xóa hết
            if not operating_times_data:
                if existing_operating_times:
                    TerminalOperatingTime.objects.filter(terminal_id=terminal_id).delete()
                return True, []
            
            # Prefetch DayOfWeek (lấy tất cả day_of_week_ids từ data)
            day_of_week_ids = [data.get('day_of_week_id') for data in operating_times_data if data.get('day_of_week_id')]
            if not day_of_week_ids:
                return False, "Day of week ID is required"
            
            day_of_weeks = {dow.id: dow for dow in DayOfWeek.objects.filter(id__in=day_of_week_ids)}
            
            # Phân loại: UPDATE, CREATE, DELETE
            to_update = []
            to_create = []
            # Lấy các id từ data (chỉ lấy những id hợp lệ, không phải None)
            new_operating_time_ids = {data.get('id') for data in operating_times_data if data.get('id') is not None}
            existing_operating_time_ids = set(existing_operating_times.keys())
            
            # DELETE: Những cái không còn trong list mới (có id nhưng không có trong list mới)
            to_delete_ids = existing_operating_time_ids - new_operating_time_ids
            if to_delete_ids:
                TerminalOperatingTime.objects.filter(
                    terminal_id=terminal_id,
                    id__in=to_delete_ids
                ).delete()
            
            # UPDATE/CREATE: Xử lý từng item trong list mới
            for data in operating_times_data:
                operating_time_id = data.get('id')
                day_of_week_id = data.get('day_of_week_id')
                if not day_of_week_id:
                    return False, "Day of week ID is required"
                
                day_of_week = day_of_weeks.get(day_of_week_id)
                if not day_of_week:
                    return False, f"Day of week with ID {day_of_week_id} not found"
                
                is_active = data.get('is_active', False)
                start_time_str = data.get('start_time')
                end_time_str = data.get('end_time')
                
                start_time = OperatingTimeService.parse_time_string(start_time_str) if start_time_str else None
                end_time = OperatingTimeService.parse_time_string(end_time_str) if end_time_str else None
                
                # Validation
                if is_active and (not start_time or not end_time):
                    return False, f"Start time and end time are required when is_active is True for {day_of_week.name}"
                
                # Kiểm tra xem có id không (nếu có id thì UPDATE, không có thì CREATE)
                if operating_time_id and operating_time_id in existing_operating_times:
                    # UPDATE: So sánh xem có thay đổi không
                    existing = existing_operating_times[operating_time_id]
                    if (existing.day_of_week_id != day_of_week_id or
                        existing.is_active != is_active or 
                        existing.start_time != start_time or 
                        existing.end_time != end_time):
                        existing.day_of_week = day_of_week
                        existing.is_active = is_active
                        existing.start_time = start_time
                        existing.end_time = end_time
                        to_update.append(existing)
                else:
                    # CREATE (không có id hoặc id không tồn tại)
                    to_create.append(TerminalOperatingTime(
                        terminal=terminal,
                        day_of_week=day_of_week,
                        is_active=is_active,
                        start_time=start_time,
                        end_time=end_time
                    ))
            
            # Bulk update
            if to_update:
                TerminalOperatingTime.objects.bulk_update(
                    to_update, 
                    ['day_of_week', 'is_active', 'start_time', 'end_time'],
                    batch_size=100
                )
            
            # Bulk create
            if to_create:
                TerminalOperatingTime.objects.bulk_create(to_create, batch_size=100)
            
            # Query lại để trả về kết quả
            result = list(TerminalOperatingTime.objects.filter(
                terminal_id=terminal_id
            ).select_related('day_of_week'))
            
            return True, result
            
        except Terminal.DoesNotExist:
            return False, "Terminal not found"
        except Exception as e:
            return False, str(e)


# Backward compatibility: Export functions for existing code
def get_operating_time(operating_time_id: int) -> Optional[TerminalOperatingTime]:
    return OperatingTimeService.get(operating_time_id)

def get_operating_times_by_terminal(terminal_id: int) -> List[TerminalOperatingTime]:
    return OperatingTimeService.get_by_terminal(terminal_id)

def parse_time_string(time_str: Optional[str]) -> Optional[dt_time]:
    return OperatingTimeService.parse_time_string(time_str)

def create_operating_time(data: dict) -> Tuple[bool, TerminalOperatingTime | str]:
    return OperatingTimeService.create(data)

def update_operating_time(operating_time_id: int, data: dict) -> Tuple[bool, TerminalOperatingTime | str]:
    return OperatingTimeService.update(operating_time_id, data)

def delete_operating_time(operating_time_id: int) -> Tuple[bool, str]:
    return OperatingTimeService.delete(operating_time_id)

def bulk_create_or_update_operating_times(terminal_id: int, operating_times_data: List[dict]) -> Tuple[bool, List[TerminalOperatingTime] | str]:
    return OperatingTimeService.bulk_create_or_update(terminal_id, operating_times_data)
