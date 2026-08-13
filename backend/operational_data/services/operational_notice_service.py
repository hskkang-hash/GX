from django.db import transaction
from ninja.errors import ValidationError
from typing import Tuple, Dict, Any, Optional, List
from operational_data.models import OperationalNotice
from operational_data.schemas.schemas_djantic_in import OperationalNoticeCreateInSchema, OperationalNoticeUpdateInSchema, OperationalNoticeBulkDeleteInSchema
from operational_data.schemas.schemas_djantic_out import OperationalNoticeOutSchema
from common.constant import MESSAGE_ENUM


class OperationalNoticeService:
    """Service layer cho OperationalNotice CRUD operations"""
    
    @staticmethod
    @transaction.atomic
    def create_operational_notice(data: OperationalNoticeCreateInSchema) -> Tuple[bool, Dict[str, Any]]:
        """
        Tạo mới operational notice
        
        Args:
            data: OperationalNoticeCreateInSchema với thông tin notice
            
        Returns:
            Tuple (success, result) với thông tin notice đã tạo hoặc lỗi
        """
        try:
            # Validation
            if not data.name or not data.name.strip():
                raise ValidationError("name is required")
            
            # Tạo operational notice
            operational_notice = OperationalNotice.objects.create(
                name=data.name.strip(),
                content1=data.content1,
                content2=data.content2,
                content3=data.content3,
                active=data.active
            )
            
            # Prepare response data
            result_data = OperationalNoticeOutSchema.from_queryset(operational_notice)
            
            return True, {
                'data': result_data,
                'message': 'Operational notice created successfully'
            }
            
        except ValidationError as e:
            return False, {
                'error': 'Validation error',
                'message': str(e),
                'details': e.errors if hasattr(e, 'errors') else None
            }
        except Exception as e:
            return False, {
                'error': 'Internal server error',
                'message': f'Failed to create operational notice: {str(e)}'
            }
    
    @staticmethod
    def get_operational_notice_list() -> Tuple[bool, Dict[str, Any]]:
        """
        Lấy danh sách tất cả operational notices
        
        Returns:
            Tuple (success, result) với danh sách notices
        """
        try:
            notices = OperationalNotice.objects.all()
            # Convert queryset to list using schema
            result_data = notices
            
            return True, {
                'data': result_data,
                'total': len(result_data),
                'message': 'Operational notices retrieved successfully'
            }
            
        except Exception as e:
            return False, {
                'error': 'Internal server error',
                'message': f'Failed to retrieve operational notices: {str(e)}'
            }
    
    @staticmethod
    def get_operational_notice_detail(notice_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Lấy chi tiết một operational notice
        
        Args:
            notice_id: ID của notice cần lấy
            
        Returns:
            Tuple (success, result) với thông tin notice hoặc lỗi
        """
        try:
            notice = OperationalNotice.objects.get(id=notice_id)
            
            # Convert to schema
            result_data = OperationalNoticeOutSchema.from_queryset(notice)
            
            return True, {
                'data': result_data,
                'message': 'Operational notice retrieved successfully'
            }
            
        except OperationalNotice.DoesNotExist:
            return False, {
                'error': 'Not found',
                'message': 'Operational notice not found'
            }
        except Exception as e:
            return False, {
                'error': 'Internal server error',
                'message': f'Failed to retrieve operational notice: {str(e)}'
            }
    
    @staticmethod
    @transaction.atomic
    def update_operational_notice(notice_id: int, data: OperationalNoticeUpdateInSchema) -> Tuple[bool, Dict[str, Any]]:
        """
        Cập nhật operational notice
        
        Args:
            notice_id: ID của notice cần cập nhật
            data: OperationalNoticeUpdateInSchema với thông tin mới
            
        Returns:
            Tuple (success, result) với thông tin notice đã cập nhật hoặc lỗi
        """
        try:
            notice = OperationalNotice.objects.get(id=notice_id)
            
            # Validate name if provided
            if data.name is not None:
                if not data.name.strip():
                    raise ValidationError("name cannot be empty")
                notice.name = data.name.strip()
            
            # Update content if provided
            if data.content1 is not None:
                notice.content1 = data.content1
            if data.content2 is not None:
                notice.content2 = data.content2
            if data.content3 is not None:
                notice.content3 = data.content3
                
            # Update active if provided
            if data.active is not None:
                notice.active = data.active
            
            notice.save()
            
            # Prepare response data
            result_data = OperationalNoticeOutSchema.from_queryset(notice)
            
            return True, {
                'data': result_data,
                'message': 'Operational notice updated successfully'
            }
            
        except OperationalNotice.DoesNotExist:
            return False, {
                'error': 'Not found',
                'message': 'Operational notice not found'
            }
        except ValidationError as e:
            return False, {
                'error': 'Validation error',
                'message': str(e),
                'details': e.errors if hasattr(e, 'errors') else None
            }
        except Exception as e:
            return False, {
                'error': 'Internal server error',
                'message': f'Failed to update operational notice: {str(e)}'
            }
    
    @staticmethod
    @transaction.atomic
    def delete_operational_notice(notice_ids: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Xóa operational notice
        
        Args:
            notice_ids: ID của notice cần xóa
            
        Returns:
            Tuple (success, result) với thông báo kết quả
        """
        try:
            notice_ids = notice_ids.split(',')
            notice = OperationalNotice.objects.filter(id__in=notice_ids)
            notice.delete()

            return True, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
            
        except OperationalNotice.DoesNotExist:
            return False, {
                'error': 'Not found',
                'message': 'No operational notices found with the provided IDs'
            }
        except Exception as e:
            return False, e
    
    @staticmethod
    @transaction.atomic
    def change_status_operational_notice(notice_id: int) -> Tuple[bool, str, Optional[int]]:
        """
        Thay đổi trạng thái operational notice
        
        Args:
            notice_id: ID của notice cần thay đổi trạng thái
            
        Returns:
            Tuple (success, result) với thông báo kết quả
        """
        try:
            notice = OperationalNotice.objects.get(id=notice_id)
            notice.active = not notice.active
            notice.save()
            return True, "Operational notice status changed successfully", notice.id
        except OperationalNotice.DoesNotExist:
            return False, "No operational notices found with the provided ID", None