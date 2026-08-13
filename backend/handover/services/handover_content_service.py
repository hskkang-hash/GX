from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import F, OuterRef, Subquery, Value

from django.db.models.functions import Concat, Coalesce
from django.utils import timezone
from typing import Tuple, Optional, List, Dict
from datetime import datetime

from handover.models import HandoverContent, HandoverDocument, HandoverDocumentAcceptor, HandoverNotice
from core.user.models import CoreUser
from common.constant import MESSAGE_ENUM, get_message


class HandoverContentService:
    """Service layer for HandoverContent operations"""

    @staticmethod
    @transaction.atomic
    def create_or_update(data: Dict, user: CoreUser) -> Tuple[bool, Optional[HandoverContent]]:
        """Tạo hoặc cập nhật handover content"""
        try:
            content_id = data.get('content_id')
            handover_doc_id = data.get('handover_doc_id')
            content_text = data.get('content')
            is_notice = data.get('is_notice', False)
            
            if content_id:
                # Update
                content = HandoverContent.objects.get(id=content_id)
                old_is_notice = content.is_notice
                old_content = content.content
                
                content.content = content_text
                content.is_notice = is_notice
                content.updated_time = data.get('updated_time') or timezone.now()
                content.save()
                
                # Thêm user vào editors
                content.editors.add(user)
                
                # Cập nhật updated_time của document
                content.handover_doc.updated_time = timezone.now()
                content.handover_doc.save()
                
                # Nếu is_notice=True, tạo HandoverNotice (giống logic cũ)
                if is_notice:
                    # Nếu trước đó không phải notice, hoặc đã là notice nhưng content thay đổi
                    if not old_is_notice or (old_is_notice and old_content != content_text):
                        HandoverNotice.objects.create(
                            content=content_text,
                            creator=user,
                            group=content.handover_doc.group,
                            created_by=user
                        )
            else:
                # Create
                handover_doc = HandoverDocument.objects.get(id=handover_doc_id)
                content = HandoverContent.objects.create(
                    handover_doc=handover_doc,
                    content=content_text,
                    is_notice=is_notice,
                    creator=user,
                    created_by=user
                )
                
                # Thêm user vào acceptor của document
                HandoverDocumentAcceptor.objects.get_or_create(
                    handover_document=handover_doc,
                    acceptor=user
                )
                
                # Cập nhật updated_time của document
                handover_doc.updated_time = timezone.now()
                handover_doc.save()
                
                # Nếu is_notice=True, tạo HandoverNotice (giống logic cũ)
                if is_notice:
                    HandoverNotice.objects.create(
                        content=content_text,
                        creator=user,
                        group=handover_doc.group,
                        created_by=user
                    )
            
            return True, content
        except HandoverDocument.DoesNotExist:
            raise ValidationError("Handover document not found")
        except HandoverContent.DoesNotExist:
            raise ValidationError("Handover content not found")
        except Exception as e:
            return False, None

    @staticmethod
    @transaction.atomic
    def delete(content_id: int, handover_doc_id: int = None) -> Tuple[bool, str]:
        """Xóa handover content"""
        try:
            content = HandoverContent.objects.get(id=content_id)
            content.delete()  # Hard delete
            return True, get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
        except HandoverContent.DoesNotExist:
            raise ValidationError("Handover content not found")
        except Exception as e:
            return False, str(e)

    @staticmethod
    @transaction.atomic
    def batch_create_or_update(contents: List[Dict], user: CoreUser) -> Tuple[bool, Dict]:
        """Tạo/cập nhật hàng loạt handover content"""
        results = {
            'created': [],
            'updated': [],
            'errors': []
        }
        
        for content_data in contents:
            success, content = HandoverContentService.create_or_update(content_data, user)
            if success:
                if content_data.get('content_id'):
                    results['updated'].append(content.id)
                else:
                    results['created'].append(content.id)
            else:
                results['errors'].append(f"Failed to process content: {content_data.get('content', '')[:50]}")
        
        return True, results

    @staticmethod
    def get_by_document(document_id: int):
        """Lấy danh sách content của một handover document với đầy đủ annotations"""
        return HandoverContent.objects.filter(
            handover_doc_id=document_id
        ).select_related(
            'creator', 
            'handover_doc__shift',
            'handover_doc__handover',
            'created_by',
            'modified_by'
        ).prefetch_related('editors').annotate(
            shift_name=F('handover_doc__shift__name'),
            creator_full_name=Concat(Coalesce('created_by__first_name', Value('')), Value(' '), Coalesce('created_by__last_name', Value(''))),
            editor_full_name=Concat(Coalesce('modified_by__first_name', Value('')), Value(' '), Coalesce('modified_by__last_name', Value(''))),
            content_text=F('content'),
        ).order_by('-created_time')

    @staticmethod
    def get_duty_detail(handover_ids: List[int]):
        """Lấy chi tiết nhiều handover documents"""
        shift_name_subquery = HandoverDocument.objects.filter(
            id=OuterRef('handover_doc')
        ).values('shift__name')[:1]
        
        return HandoverContent.objects.filter(
            handover_doc__in=handover_ids
        ).select_related(
            'creator', 
            'handover_doc__shift',
            'handover_doc__handover',
            'created_by',
            'modified_by'
        ).prefetch_related('editors').annotate(
            shift_name=Subquery(shift_name_subquery),
            creator__full_name=Concat(Coalesce('created_by__first_name', Value('')), Value(' '), Coalesce('created_by__last_name', Value(''))),
            editor__full_name=Concat(Coalesce('modified_by__first_name', Value('')), Value(' '), Coalesce('modified_by__last_name', Value(''))),
        ).order_by('-created_time')

