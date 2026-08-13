from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import F, Value
from django.db.models.functions import Concat, Coalesce
from django.db.models.functions import Concat
from typing import Tuple, Optional, List, Dict

from handover.models import HandoverShift
from core.multilanguage.request_handlers import create_model_with_translations, update_model_with_translations
from common.constant import MESSAGE_ENUM, get_message


class HandoverShiftService:
    """Service layer for HandoverShift operations"""

    @staticmethod
    def get_list(user=None):
        """Lấy danh sách ca làm việc với đa ngôn ngữ"""
        queryset = HandoverShift.objects.select_related('group', 'created_by', 'modified_by').annotate(
            creator__full_name=Concat(Coalesce('created_by__first_name', Value('')), Value(' '), Coalesce('created_by__last_name', Value(''))),
            editor__full_name=Concat(Coalesce('modified_by__first_name', Value('')), Value(' '), Coalesce('modified_by__last_name', Value(''))),
        ).order_by('id')
        
        return queryset

    @staticmethod
    @transaction.atomic
    def create(data: Dict, user=None) -> Tuple[bool, Optional[HandoverShift]]:
        """Tạo ca làm việc mới với đa ngôn ngữ"""
        try:
            # Chuẩn bị dữ liệu cho create_model_with_translations
            shift_data = {
                'start_time': data.get('start_time'),
                'end_time': data.get('end_time'),
                'color': data.get('color'),
            }
            
            # Xử lý name - có thể là string hoặc dict
            name_value = data.get('name')
            if isinstance(name_value, dict):
                shift_data['name'] = name_value
            else:
                # Nếu là string, chuyển thành dict với en và ko
                shift_data['name'] = {
                    'en': name_value or '',
                    'ko': name_value or ''
                }
            
            # Tạo với đa ngôn ngữ
            shift = create_model_with_translations(HandoverShift, shift_data)
            
            return True, shift
        except Exception as e:
            return False, None

    @staticmethod
    @transaction.atomic
    def update(data: Dict, user=None) -> Tuple[bool, Optional[HandoverShift]]:
        """Cập nhật ca làm việc"""
        try:
            shift_id = data.get('id')
            shift = HandoverShift.objects.get(id=shift_id)
            
            # Chuẩn bị dữ liệu cho update_model_with_translations
            shift_data = {
                'start_time': data.get('start_time', shift.start_time),
                'end_time': data.get('end_time', shift.end_time),
                'color': data.get('color', shift.color),
            }
            
            # Xử lý name - có thể là string hoặc dict
            name_value = data.get('name')
            if name_value is not None:
                if isinstance(name_value, dict):
                    shift_data['name'] = name_value
                else:
                    # Nếu là string, giữ nguyên hoặc merge với translations hiện có
                    shift_data['name'] = name_value
            
            # Cập nhật với đa ngôn ngữ
            shift = update_model_with_translations(shift, shift_data)
            
            return True, shift
        except HandoverShift.DoesNotExist:
            raise ValidationError("Handover shift not found")
        except Exception as e:
            return False, None

    @staticmethod
    @transaction.atomic
    def delete(shift_id: int) -> Tuple[bool, str]:
        """Xóa ca làm việc với kiểm tra ràng buộc"""
        try:
            shift = HandoverShift.objects.get(id=shift_id)
            
            # Kiểm tra ràng buộc
            from handover.models import HandoverDocument
            if HandoverDocument.objects.filter(shift=shift).exists():
                return False, "Cannot delete shift: has related documents"
            
            # Xóa shift (translations sẽ tự động xóa qua cascade)
            shift.delete()
            
            return True, get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
        except HandoverShift.DoesNotExist:
            raise ValidationError("Handover shift not found")
        except Exception as e:
            return False, str(e)

    @staticmethod
    @transaction.atomic
    def batch_config(data: Dict, user=None) -> Tuple[bool, Dict]:
        """Cấu hình hàng loạt ca làm việc"""
        results = {
            'created': [],
            'updated': [],
            'deleted': [],
            'errors': []
        }
        
        try:
            # Tạo mới
            create_shifts = data.get('create_shifts', [])
            for shift_data in create_shifts:
                success, shift = HandoverShiftService.create(shift_data, user)
                if success:
                    results['created'].append(shift.id)
                else:
                    results['errors'].append(f"Failed to create shift: {shift_data.get('name')}")
            
            # Cập nhật
            update_shifts = data.get('update_shifts', [])
            for shift_data in update_shifts:
                success, shift = HandoverShiftService.update(shift_data, user)
                if success:
                    results['updated'].append(shift.id)
                else:
                    results['errors'].append(f"Failed to update shift: {shift_data.get('id')}")
            
            # Xóa
            delete_shifts = data.get('delete_shifts', [])
            for shift_id in delete_shifts:
                success, message = HandoverShiftService.delete(shift_id)
                if success:
                    results['deleted'].append(shift_id)
                else:
                    results['errors'].append(f"Failed to delete shift {shift_id}: {message}")
            
            return True, results
        except Exception as e:
            return False, {'errors': [str(e)]}
