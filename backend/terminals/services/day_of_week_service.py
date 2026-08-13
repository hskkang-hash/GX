"""
Service để xử lý DayOfWeek
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from typing import Tuple, Optional, List
from terminals.models import DayOfWeek
from common.constant import MESSAGE_ENUM, get_message


class DayOfWeekService:
    """Service class cho DayOfWeek operations"""
    
    @staticmethod
    def get(day_of_week_id: int) -> Optional[DayOfWeek]:
        """Lấy day of week theo ID"""
        try:
            return DayOfWeek.objects.get(id=day_of_week_id)
        except DayOfWeek.DoesNotExist:
            return None
    
    @staticmethod
    def get_all() -> List[DayOfWeek]:
        """Lấy tất cả days of week"""
        return DayOfWeek.objects.filter(is_active=True).order_by('order')
    
    @staticmethod
    @transaction.atomic
    def create(data: dict) -> Tuple[bool, DayOfWeek | str]:
        """Tạo mới day of week"""
        try:
            code = data.get('code')
            if not code:
                return False, "Code is required"
            
            # Kiểm tra code đã tồn tại chưa
            if DayOfWeek.objects.filter(code=code).exists():
                return False, f"Day of week with code '{code}' already exists"
            
            day_of_week = DayOfWeek.objects.create(**data)
            return True, day_of_week
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def update(day_of_week_id: int, data: dict) -> Tuple[bool, DayOfWeek | str]:
        """Cập nhật day of week"""
        try:
            day_of_week = DayOfWeekService.get(day_of_week_id)
            if not day_of_week:
                return False, "Day of week not found"
            
            code = data.get('code')
            if code and code != day_of_week.code:
                # Kiểm tra code mới đã tồn tại chưa
                if DayOfWeek.objects.filter(code=code).exclude(id=day_of_week_id).exists():
                    return False, f"Day of week with code '{code}' already exists"
            
            # Cập nhật các trường
            for key, value in data.items():
                if hasattr(day_of_week, key):
                    setattr(day_of_week, key, value)
            
            day_of_week.save()
            return True, day_of_week
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    @transaction.atomic
    def delete(day_of_week_id: int) -> Tuple[bool, str]:
        """Xóa day of week"""
        try:
            day_of_week = DayOfWeekService.get(day_of_week_id)
            if not day_of_week:
                return False, "Day of week not found"
            
            # Kiểm tra xem có đang được sử dụng không
            if day_of_week.operating_times.exists():
                return False, f"Cannot delete day of week '{day_of_week.name}' because it is being used by {day_of_week.operating_times.count()} operating times"
            
            day_of_week.delete()
            return True, get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
            
        except Exception as e:
            return False, str(e)


# Backward compatibility: Export functions for existing code
def get_day_of_week(day_of_week_id: int) -> Optional[DayOfWeek]:
    return DayOfWeekService.get(day_of_week_id)

def get_all_days_of_week() -> List[DayOfWeek]:
    return DayOfWeekService.get_all()

def create_day_of_week(data: dict) -> Tuple[bool, DayOfWeek | str]:
    return DayOfWeekService.create(data)

def update_day_of_week(day_of_week_id: int, data: dict) -> Tuple[bool, DayOfWeek | str]:
    return DayOfWeekService.update(day_of_week_id, data)

def delete_day_of_week(day_of_week_id: int) -> Tuple[bool, str]:
    return DayOfWeekService.delete(day_of_week_id)
