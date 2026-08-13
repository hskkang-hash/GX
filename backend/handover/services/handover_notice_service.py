from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Q, Prefetch, Count, F, Case, When, CharField, Value
from django.db.models.functions import Concat, Coalesce
from django.db.models.functions import Concat
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.http import HttpRequest, QueryDict
from django.utils import timezone
from typing import Tuple, Optional, List, Dict
from datetime import datetime
from dateutil import parser
import pytz
import os
import csv
import io
import threading
import uuid
import logging
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings
from core.common.search.dynamic_search import apply_dynamic_filters
from print_format.services import PrintFormatService
from handover.models import HandoverNotice, HandoverNoticeComment
from core.user.models import CoreUser, UserGroup
from core.file_management.models import UserMediaFile
from core.file_management.helper import FileHelper
from common.constant import MESSAGE_ENUM, get_message
from handover.tasks import _send_handover_download_notification
from task_status.models import TaskStatus
from task_status.services.task_status_service import TaskStatusService

logger = logging.getLogger(__name__)


class HandoverNoticeService:
    """Service layer for HandoverNotice operations"""

    @staticmethod
    def get_list(user=None):
        """Lấy danh sách thông báo với filters và đầy đủ annotations"""
        queryset = HandoverNotice.objects.select_related(
            'creator', 'user_processed', 'group', 'created_by', 'modified_by'
        ).prefetch_related(
            'files',
            Prefetch(
                'comments',
                queryset=HandoverNoticeComment.objects.filter(deleted__isnull=True).select_related('writer')
            )
        ).annotate(
            comment_count=Count('comments', filter=Q(comments__deleted__isnull=True), distinct=True),
            editor_names=ArrayAgg(F('editors__username'), distinct=True, filter=Q(editors__isnull=False)),
            status= Case(
                When(Q(is_processed=True) & Q(deleted__isnull=True), then=Value('Complete')),
                When(Q(deleted__isnull=False), then=Value('Delete')),
                default=Value('Pending'),
                output_field=CharField() 
            ),
            creator__full_name=Concat(Coalesce('created_by__first_name', Value('')), Value(' '), Coalesce('created_by__last_name', Value(''))),
            editor__full_name=Concat(Coalesce('modified_by__first_name', Value('')), Value(' '), Coalesce('modified_by__last_name', Value(''))),
            content_text=F('content') ,

        )
        
        return queryset.order_by('-created_time')

    @staticmethod
    @transaction.atomic
    def create_or_update(data: Dict, user: CoreUser, files: List = None) -> Tuple[bool, Optional[HandoverNotice]]:
        """Tạo hoặc cập nhật thông báo"""
        try:
            notice_id = data.get('notice_id')
            content = data.get('content')
            removed_file_ids = data.get('removed_file_ids', [])
            
            if notice_id:
                # Update
                notice = HandoverNotice.objects.get(id=notice_id)
                notice.content = content
                notice.updated_time = timezone.now()
                notice.save()
                
                # Thêm user vào editors
                notice.editors.add(user)
                
                # Xóa files
                if removed_file_ids:
                    notice.files.filter(id__in=removed_file_ids).delete()
            else:
                # Create
                group = None
                if hasattr(user, 'userprofilelink') and user.userprofilelink.group:
                    group = user.userprofilelink.group
                else:
                    group = UserGroup.objects.first()
                
                notice = HandoverNotice.objects.create(
                    creator=user,
                    content=content,
                    group=group,
                    created_by=user
                )
            
            # Thêm files mới
            if files:
                for file_obj in files:
                    notice.files.add(file_obj)
            
            return True, notice
        except HandoverNotice.DoesNotExist:
            raise ValidationError("Handover notice not found")
        except Exception as e:
            return False, None

    @staticmethod
    @transaction.atomic
    def delete(notice_id: int) -> Tuple[bool, str]:
        """Xóa thông báo (soft delete sử dụng deleted field từ BaseModel)"""
        try:
            notice = HandoverNotice.objects.get(id=notice_id)
            notice.delete()
            return True, "Notice deleted"
        except HandoverNotice.DoesNotExist:
            raise ValidationError("Handover notice not found")
        except Exception as e:
            return False, str(e)

    @staticmethod
    @transaction.atomic
    def process(notice_id: int, is_processed: bool, user: CoreUser) -> Tuple[bool, Optional[HandoverNotice]]:
        """Đánh dấu thông báo đã xử lý hoặc chưa xử lý"""
        try:
            notice = HandoverNotice.objects.get(id=notice_id)
            notice.is_processed = is_processed
            if is_processed:
                notice.user_processed = user
                notice.processed_time = timezone.now()
            else:
                notice.user_processed = None
                notice.processed_time = None
            notice.save()
            return True, notice
        except HandoverNotice.DoesNotExist:
            raise ValidationError("Handover notice not found")
        except Exception as e:
            return False, None

    @staticmethod
    @transaction.atomic
    def restore(notice_id: int) -> Tuple[bool, Optional[HandoverNotice]]:
        """Khôi phục thông báo đã xóa (restore bằng cách set deleted = None)"""
        try:
            # Sử dụng _base_manager để lấy cả record đã deleted
            notice = HandoverNotice._base_manager.get(id=notice_id, deleted__isnull=False)
            notice.deleted = None
            notice.is_processed = True  # Tự động đánh dấu đã xử lý khi khôi phục
            notice.save()
            return True, notice
        except HandoverNotice.DoesNotExist:
            raise ValidationError("Handover notice not found or not deleted")
        except Exception as e:
            return False, None

    @staticmethod
    def get_detail(notice_id: int):
        """Lấy chi tiết thông báo - chỉ lấy parent comments (không có replies)"""
        return HandoverNotice.objects.select_related(
            'creator', 'user_processed', 'group', 'created_by', 'modified_by'
        ).prefetch_related(
            'editors',
            'files',
            Prefetch(
                'comments',
                queryset=HandoverNoticeComment.objects.filter(deleted__isnull=True, parent=None).select_related('writer')
            )
        ).annotate(
            creator__full_name=Concat(Coalesce('created_by__first_name', Value('')), Value(' '), Coalesce('created_by__last_name', Value(''))),
            editor__full_name=Concat(Coalesce('modified_by__first_name', Value('')), Value(' '), Coalesce('modified_by__last_name', Value(''))),
        ).get(id=notice_id)

    @staticmethod
    def get_download_data(notice_status: str = None, 
                         get_delete_notice: bool = False, selected_fields: List[str] = None, user: CoreUser = None, processed: bool = False, request: QueryDict = None):
        """Lấy dữ liệu để download CSV cho handover notice"""

        filters = {}
        extra_filter = Q()
        if notice_status == "processing":
            extra_filter = Q(is_processed=False) & Q(deleted__isnull=True)
        elif notice_status == "processed":
            if get_delete_notice:
                extra_filter = Q(is_processed=True) | (Q(deleted__isnull=False) & Q(is_processed=True))
            else:
                extra_filter = Q(is_processed=True) & Q(deleted__isnull=True)
        if not processed:
            extra_filter = Q(is_processed=False) & Q(deleted__isnull=True)
        else:
            extra_filter = Q(is_processed=True) | (Q(deleted__isnull=False) & Q(is_processed=True))
        if not selected_fields:
            return ['id']
        # if "id" not in selected_fields:
        #     selected_fields.append('id')
        user_settings = None
        if hasattr(user, 'user_settings'):
            user_settings = user.user_settings
        elif hasattr(user, 'usersettings'):
            user_settings = user.usersettings
        if not user.is_superuser and not (any(role.id == 1 for role in user.roles.all())):
            filters['group'] = user.userprofilelink.group
        processing_notice_list = HandoverNotice._base_manager.filter(extra_filter).filter(**filters).annotate(
            comment_count=Count('comments', filter=Q(comments__deleted__isnull=True), distinct=True),
            creator__full_name=Concat(Coalesce('created_by__first_name', Value('')), Value(' '), Coalesce('created_by__last_name', Value(''))),
            editor__full_name=Concat(Coalesce('modified_by__first_name', Value('')), Value(' '), Coalesce('modified_by__last_name', Value(''))),
            status= Case(
                When(Q(is_processed=True) & Q(deleted__isnull=True), then=Value('Complete')),
                When(Q(deleted__isnull=False), then=Value('Delete')),
                default=Value('Pending'),
                output_field=CharField() 
            ),
            content_text=F('content') ,
        ).order_by("-created_time")
        processing_notice_list = apply_dynamic_filters(processing_notice_list, request, [], request.GET.get("sort_obj"))
        processing_notice_list = processing_notice_list.values(*selected_fields)
        # Format datetime fields
        tz = pytz.timezone(os.getenv('TIME_ZONE', 'Asia/Ho_Chi_Minh'))
        for data in processing_notice_list:
            if isinstance(data.get('created_time'), datetime):
                data['created_time'] = PrintFormatService._format_datetime_with_user_settings(data.get('created_time'), user_settings)
            if isinstance(data.get('updated_time'), datetime):
                data['updated_time'] = PrintFormatService._format_datetime_with_user_settings(data.get('updated_time'), user_settings)
            if isinstance(data.get('processed_time'), datetime):
                data['processed_time'] = PrintFormatService._format_datetime_with_user_settings(data.get('processed_time'), user_settings)
        
        return processing_notice_list

    @staticmethod
    def _get_header_mapping(selected_fields: List[str]) -> Dict[str, str]:
        """
        Tạo mapping từ field names sang display names cho CSV headers
        """
        # Mapping mặc định cho các field phổ biến
        default_mapping = {
            'id': 'ID',
            'content': 'Content',
            'status': 'Status',
            'created_time': 'Created Time',
            'updated_time': 'Updated Time',
            'processed_time': 'Processed Time',
            'creator__full_name': 'Creator',
            'editor__full_name': 'Editor',
            'comment_count': 'Comment Count',
            'is_processed': 'Is Processed',
            'user_processed__username': 'Processed By',
            'group__name': 'Group',
        }
        
        # Tạo mapping động cho các field không có trong default_mapping
        mapping = {}
        for field in selected_fields:
            if field in default_mapping:
                mapping[field] = default_mapping[field]
            else:
                # Normalize field name: thay thế __ bằng space, _ bằng space, và title case
                normalized = field.replace('__', ' / ').replace('_', ' ')
                # Title case nhưng giữ nguyên các từ viết tắt
                words = normalized.split()
                title_words = []
                for word in words:
                    if word.isupper() and len(word) <= 3:
                        title_words.append(word)
                    else:
                        title_words.append(word.capitalize())
                mapping[field] = ' '.join(title_words)
        
        return mapping

    @staticmethod
    def download_notice(notice_status: str = None,
                       get_delete_notice: bool = False, selected_fields: List[str] = None, user: CoreUser = None, processed: bool = False, request: QueryDict = None):
        """
        Queue handover notice download as background thread with WebSocket notifications
        Returns immediately with download status information
        
        download_type được xác định động:
        - notice_status == 'processed' → download_type = 'completed_notice'
        - notice_status == 'processing' hoặc None → download_type = 'notice'
        """
        try:
            # Xác định download_type dựa vào notice_status
            if notice_status == 'processed':
                download_type = 'completed_notice'
            else:
                download_type = 'notice'  # processing notice hoặc None
            
            # Generate unique task ID for download tracking
            download_task_id = str(uuid.uuid4())
            task_type = f"handover_{download_type}_download"
            
            # Persist initial task status for client-side polling
            pending_message = get_message(MESSAGE_ENUM.START_DOWNLOAD_FILE)
            TaskStatusService.create_or_update(
                task_id=download_task_id,
                task_type=task_type,
                user=user,
                category=TaskStatus.Category.DOWNLOAD,
                status='pending',
                message=pending_message,
                action='handover_notice_download',
                task_channel=f'handover_{user.username}',
                trigger_source='handover.notice.download',
                related_model='handover.HandoverNotice',
                related_object_id=None,
            )
            
            # Send initial notification
            _send_handover_download_notification(
                user.username,
                download_type,
                'pending',
                pending_message,
                download_task_id
            )
            
            # Start background thread for download processing
            # Truyền download_type vào thread để sử dụng trong _process_download_in_thread
            download_thread = threading.Thread(
                target=HandoverNoticeService._process_download_in_thread,
                args=(notice_status, get_delete_notice, selected_fields, download_task_id, user.id, download_type, task_type, processed, request),
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
    def _process_download_in_thread(notice_status: str,
                                    get_delete_notice: bool, selected_fields: List[str],
                                    download_task_id: str, user_id: int, download_type: str = None,
                                    task_type: str = None, processed: bool = False, request: QueryDict = None):
        """
        Process download in background thread with WebSocket notifications
        
        Args:
            download_type: 'notice' hoặc 'completed_notice' (được truyền từ download_notice)
        """
        try:
            # Nếu không có download_type, xác định dựa vào notice_status
            if not download_type:
                if notice_status == 'processed':
                    download_type = 'completed_notice'
                else:
                    download_type = 'notice'  # processing notice hoặc None
            if not task_type:
                task_type = f"handover_{download_type}_download"
            
            logger.info(f"🔄 Starting handover {download_type} download processing for task {download_task_id}")
            
            # Get user
            user = CoreUser.objects.get(id=user_id)
            
            # Send processing notification
            processing_message = get_message(MESSAGE_ENUM.DOWNLOAD_HANDOVER_NOTICE_PROCESSING)
            TaskStatusService.update_status(
                download_task_id,
                status='processing',
                message=processing_message,
                action='handover_notice_download',
                task_channel=f'handover_{user.username}',
                trigger_source='handover.notice.download',
            )
            _send_handover_download_notification(
                user.username,
                download_type,
                'processing',
                processing_message,
                download_task_id
            )
            
            # Get data
            notice_list = HandoverNoticeService.get_download_data(
                notice_status,
                get_delete_notice,
                selected_fields,
                user,
                processed,
                request
            )
            
            # Create CSV với header names đã được normalize
            output = io.StringIO()
            if notice_list and selected_fields:
                # Tạo mapping từ field names sang display names cho header
                header_mapping = HandoverNoticeService._get_header_mapping(selected_fields)
                # Tạo fieldnames đã được normalize
                normalized_headers = [header_mapping.get(field, field.replace('_', ' ').title()) for field in selected_fields]
                
                # Tạo data với keys đã được normalize
                normalized_data = []
                for row in notice_list:
                    normalized_row = {header_mapping.get(key, key.replace('_', ' ').title()): value for key, value in row.items()}
                    normalized_data.append(normalized_row)
                
                writer = csv.DictWriter(output, fieldnames=normalized_headers)
                writer.writeheader()
                writer.writerows(normalized_data)
            
            csv_content = output.getvalue().encode('utf-8')
            if download_type == 'completed_notice':
                file_name = f"completed_notice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            else:
                file_name = f"notice_management_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            # Create InMemoryUploadedFile
            file_obj = InMemoryUploadedFile(
                file=BytesIO(csv_content),
                field_name='file',
                name=file_name,
                content_type='text/csv',
                size=len(csv_content),
                charset='utf-8'
            )
            
            # Upload to MinIO/S3
            feature_path = f"HandoverDownloads/{download_type.replace('_', '').title()}"  # HandoverDownloads/Notice hoặc CompletedNotice
            uploaded_file = FileHelper.user_upload_s3(
                user, 
                file_obj, 
                is_avatar=False, 
                only_image=False,
                feature_path=feature_path
            )
            
            if not uploaded_file:
                raise ValueError("Failed to upload file to MinIO")
            
            download_url = None
            file_url = None
            if hasattr(uploaded_file, 'file_url') and uploaded_file.file_url:
                file_url = uploaded_file.file_url  # Relative path: /media/exports/file.csv
                protocol = 'https' if settings.MINIO_USE_HTTPS else 'http'
                download_url = f'{protocol}://{settings.MINIO_ENDPOINT}{file_url}'
            else:
                if hasattr(uploaded_file, 'file') and uploaded_file.file:
                    file_url = uploaded_file.file.name if hasattr(uploaded_file.file, 'name') else ''
                if not file_url:
                    raise ValueError("File uploaded but no file_url available")
            
            logger.info(f"📁 File uploaded to MinIO: {file_url}, File ID: {uploaded_file.id}")
            
            success_payload = {
                'download_url': download_url,
                'file_url': file_url,
                'filename': file_name,
                'file_id': uploaded_file.id,
                'total_records': len(notice_list),
            }

            TaskStatusService.update_status(
                download_task_id,
                status='success',
                message=get_message(MESSAGE_ENUM.ACTION_EXPORT_SUCCESS),
                data=success_payload,
                download_url=download_url,
                file_url=file_url,
                filename=file_name,
                file_id=str(uploaded_file.id),
                record_count=len(notice_list),
                action='handover_notice_download',
                task_channel=f'handover_{user.username}',
                trigger_source='handover.notice.download',
            )

            # Send success notification
            success_message = get_message(MESSAGE_ENUM.ACTION_EXPORT_SUCCESS)
            _send_handover_download_notification(
                user.username,
                download_type,
                'success',
                f'{success_message} {len(notice_list)} records exported.',
                download_task_id,
                success_payload
            )
            
            logger.info(f"✅ Handover notice download completed for task {download_task_id}")
        
        except Exception as e:
            logger.error(f"❌ Error in handover notice download processing: {str(e)}")
            TaskStatusService.update_status(
                download_task_id,
                status='failed',
                message=str(e),
                data={'error': str(e)},
                error_code='download_failed',
                error_details={'error': str(e)},
                action='handover_notice_download',
                task_channel=f'handover_{user.username}' if 'user' in locals() else None,
                trigger_source='handover.notice.download',
            )

            try:
                user = CoreUser.objects.get(id=user_id)
                failure_message = get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED)
                _send_handover_download_notification(
                    user.username,
                    download_type,
                    'failed',
                    f'{failure_message} {str(e)}',
                    download_task_id,
                    {'error': str(e)}
                )
            except Exception:
                pass

