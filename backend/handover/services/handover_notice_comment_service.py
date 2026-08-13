from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import F, Count, Q, Value
from django.db.models.functions import Concat, Coalesce
from django.utils import timezone
from typing import Tuple, Optional, List, Dict

from handover.models import HandoverNoticeComment, HandoverNotice
from core.user.models import CoreUser
from common.constant import MESSAGE_ENUM, get_message


class HandoverNoticeCommentService:
    """Service layer for HandoverNoticeComment operations"""

    @staticmethod
    def get_list(notice_id: int, parent_id: int = None):
        """Lấy danh sách bình luận với đầy đủ annotations
        Args:
            notice_id: ID của notice
            parent_id: Nếu None thì lấy parent comments, nếu có giá trị thì lấy replies của comment đó
        """
        queryset = HandoverNoticeComment.objects.filter(
            notice_id=notice_id
        ).select_related('writer', 'created_by', 'modified_by').annotate(
            has_replies=Count('replies', filter=Q(replies__deleted__isnull=True), distinct=True),
            creator__full_name=Concat(Coalesce('created_by__first_name', Value('')), Value(' '), Coalesce('created_by__last_name', Value(''))),
            editor__full_name=Concat(Coalesce('modified_by__first_name', Value('')), Value(' '), Coalesce('modified_by__last_name', Value(''))),
            content_text=F('content') ,
            writer__first_name=F('writer__first_name'),
            writer__last_name=F('writer__last_name'),
        )
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        else:
            queryset = queryset.filter(parent__isnull=True)
        
        return queryset.order_by('-updated_time')
    
    @staticmethod
    def get_replies(comment_id: int):
        """Lấy replies của một comment cụ thể với đầy đủ annotations
        Args:
            comment_id: ID của comment cần lấy replies
        Returns:
            QuerySet: Danh sách replies của comment
        """
        return HandoverNoticeComment.objects.filter(
            parent_id=comment_id,
            deleted__isnull=True
        ).select_related('writer', 'created_by', 'modified_by').annotate(
            has_replies=Count('replies', filter=Q(replies__deleted__isnull=True), distinct=True),
            creator__full_name=Concat(Coalesce('created_by__first_name', Value('')), Value(' '), Coalesce('created_by__last_name', Value(''))),
            editor__full_name=Concat(Coalesce('modified_by__first_name', Value('')), Value(' '), Coalesce('modified_by__last_name', Value(''))),
            content_text=F('content') ,
            writer__first_name=F('writer__first_name'),
            writer__last_name=F('writer__last_name'),
        ).order_by('-updated_time')

    @staticmethod
    @transaction.atomic
    def create(data: Dict, user: CoreUser) -> Tuple[bool, Optional[HandoverNoticeComment]]:
        """Tạo bình luận mới"""
        try:
            notice_id = data.get('notice_id')
            comment_text = data.get('comment')
            parent_id = data.get('parent_id')
            
            notice = HandoverNotice.objects.get(id=notice_id)
            parent = None
            if parent_id:
                parent = HandoverNoticeComment.objects.get(id=parent_id)
            
            comment = HandoverNoticeComment.objects.create(
                notice=notice,
                writer=user,
                content=comment_text,
                parent=parent,
                created_by=user
            )
            
            return True, comment
        except HandoverNotice.DoesNotExist:
            raise ValidationError("Handover notice not found")
        except HandoverNoticeComment.DoesNotExist:
            raise ValidationError("Parent comment not found")
        except Exception as e:
            return False, None

    @staticmethod
    @transaction.atomic
    def update(comment_id: int, comment_text: str, user: CoreUser) -> Tuple[bool, Optional[HandoverNoticeComment]]:
        """Cập nhật bình luận"""
        try:
            comment = HandoverNoticeComment.objects.get(id=comment_id)
            
            # Chỉ người tạo mới được cập nhật
            if comment.writer != user:
                raise ValidationError("Only comment creator can update")
            
            comment.content = comment_text
            comment.updated_time = timezone.now()
            comment.save()
            
            return True, comment
        except HandoverNoticeComment.DoesNotExist:
            raise ValidationError("Comment not found")
        except Exception as e:
            return False, None

    @staticmethod
    @transaction.atomic
    def delete(comment_id: int) -> Tuple[bool, str]:
        """Xóa bình luận (soft delete sử dụng deleted field từ BaseModel cho comment và tất cả replies)"""
        try:
            comment = HandoverNoticeComment.objects.get(id=comment_id)
            
            # Xóa mềm comment và tất cả replies sử dụng SafeDeleteModel.delete()
            # SafeDeleteModel sẽ tự động set deleted và trigger signals (cache clearing)
            def soft_delete_recursive(comm):
                # Sử dụng _base_manager để lấy cả replies đã deleted
                replies = HandoverNoticeComment._base_manager.filter(parent_id=comm.id, deleted__isnull=True)
                for reply in replies:
                    soft_delete_recursive(reply)
                # Gọi delete() của SafeDeleteModel - sẽ tự động set deleted và trigger post_save signal
                comm.delete()  # SafeDeleteModel với SOFT_DELETE_CASCADE sẽ tự động xử lý
            soft_delete_recursive(comment)
            
            return True, get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
        except HandoverNoticeComment.DoesNotExist:
            raise ValidationError("Comment not found")
        except Exception as e:
            return False, str(e)

