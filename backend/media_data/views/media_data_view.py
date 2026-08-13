from typing import List
from core.file_management.helper import UserMediaFile
from ninja_extra import api_controller, route
from core.common.base_response import BaseResponse
from core.api.v1.auth import CustomJWTAuth
from devices.models import Device
from common.constant import MESSAGE_ENUM, get_message
from common.pagination import OptimizedPaginator
from media_data.schemas.schemas_djantic_in import MediaDetectCallbackInSchema, MediaDetectInSchema, MediaListInSchema, MediaDownloadInSchema, MediaPreviewInSchema
from media_data.services.media_data_service import MediaDataService
from media_data.services.media_data_download_service import MediaDataDownloadService
from media_data.services.media_data_preview_service import MediaDataPreviewService
from media_data.services.media_data_detect_service import MediaDataDetectService
from datetime import timedelta
from task_status.models import TaskStatus
from task_status.services.task_status_service import TaskStatusService
from surveillance.models import VideoAnalysis
from django.db import transaction
import uuid
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
import hashlib
from urllib.parse import urlparse
from stream_monitors.utils.minio_client import minio_client

logger = logging.getLogger(__name__)


@api_controller('/', tags=['Media Data'])
class MediaDataAPI:
    @route.get('', auth=CustomJWTAuth())
    def list_media(
        self, 
        request, 
        media_type: str = None, 
        prefix: str = None,
        current_page: int = 1, 
        page_size: int = 25
    ):
        """
        List media items (images/videos) stored in MinIO with pagination, search and sort.
        
        Query params:
        - media_type: filter by 'image', 'video', or 'all'
        - prefix: path prefix (e.g., 'features/')
        - current_page: page number (default: 1)
        - page_size: items per page (default: 25)
        
        Search params (handled automatically via request.GET):
        - object_name: search by file name
        - type: search by type (image, video, document, etc.)
        - group__name: search by group name
        - size: search by size
        
        Sort params:
        - sort_obj: JSON string, e.g. [{"key":"object_name","value":"desc"}]
        """
        # Validate inputs via schema
        _ = MediaListInSchema(
            media_type=media_type,
            prefix=prefix,
            current_page=current_page,
            page_size=page_size,
        )

        # Service returns combined list (folders + files) already filtered & sorted
        success, result = MediaDataService.list_media(
            media_type=media_type, 
            prefix=prefix,
            request=request,
        )
        if not success:
            return BaseResponse(
                status_code=500,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_FAILED, "Failed to fetch list"),
                data=[],
            )

        # Get combined list (already filtered + sorted by service)
        items = result.get('items', [])
        current_prefix = result.get('prefix', '')

        # Pagination
        paginator = OptimizedPaginator(items, page_size)
        page = paginator.page(current_page)
        data = list(page.object_list)
        
        # Compute previous prefix for navigation
        prev_prefix = ''
        if current_prefix:
            trimmed = current_prefix.rstrip('/')
            last_slash = trimmed.rfind('/')
            prev_prefix = trimmed[:last_slash + 1] if last_slash != -1 else ''

        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_SUCCESS, "List fetched successfully"),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page,
            prev_prefix=prev_prefix,
        )

    @route.post('/download', auth=CustomJWTAuth())
    def download_media(self, request, data: MediaDownloadInSchema):
        """
        Download media files - ALWAYS ASYNC với WebSocket progress.
        
        Returns:
        - task_id immediately
        - Connect to WebSocket (ws/media/download/) for real-time progress
        - Receive download_url when ZIP is ready
        """
        if not data.object_paths or len(data.object_paths) == 0:
            return BaseResponse(
                status_code=400,
                message="No object paths provided",
                data=[]
            )
        
        # Get username for WebSocket room
        username = request.user.username if request.user else None
        if not username:
            return BaseResponse(
                status_code=401,
                message="User not authenticated",
                data=[]
            )
        
        # Generate unique task ID for download tracking
        download_task_id = str(uuid.uuid4())
        task_type = "media_data_download"
        
        # Persist initial task status for client-side polling
        pending_message = get_message(MESSAGE_ENUM.START_DOWNLOAD_FILE)
        success, task_status = TaskStatusService.create_or_update(
            task_id=download_task_id,
            task_type=task_type,
            user=request.user,
            category=TaskStatus.Category.DOWNLOAD,
            status='pending',
            message=pending_message,
            action='media_data_download',
            task_channel=f'media_download_{username}',
            trigger_source='media_data.download',
            related_model='media_data.MediaData',
            related_object_id=None,
        )
        
        logger.info(f"📊 Created TaskStatus: task_id={download_task_id}, success={success}")
        
        response = MediaDataDownloadService.download_media(
            object_paths=data.object_paths,
            username=username,
            task_id=download_task_id,
            user_id=request.user.id,
        )
        
        if response is None:
            # Update TaskStatus to failed if no files found
            TaskStatusService.update_status(
                download_task_id,
                status='failed',
                message=get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED),
            )
            return BaseResponse(
                status_code=404,
                message=get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED),
                data={'error': "Media not found or cannot be downloaded"},
            )
        
        # Always async mode - return task_id
        logger.info(f"📤 Returning download response with task_id={download_task_id}")
        
        # Ensure response has correct task_id
        if isinstance(response, dict):
            response['task_id'] = download_task_id
        
        return BaseResponse(
            status_code=200,
            message="Download task created successfully",
            data=response
        )

    @route.post('/detect', auth=CustomJWTAuth())
    def detect_media(self, request, data: MediaDetectInSchema):
        """
        Detect media files, save detection results as JSON to MinIO,
        and create VideoAnalysis records.
        """
        success, result = MediaDataDetectService.detect_and_save(data)
        
        if not success:
            return BaseResponse(
                status_code=400,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.DETECT_MEDIA_FAILED, "Detection failed"),
                data=[]
            )
        
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.DETECT_MEDIA_SUCCESS, "Detection completed successfully"),
            data=result,
            total_items=len(result)
        )
    
    @route.post('/preview', auth=CustomJWTAuth())
    def preview_media(self, request, data: MediaPreviewInSchema):
        """
        Get a presigned URL to preview a media file.
        Uses MinIO presigned URLs for optimal performance.
        
        The URL will expire after the specified time (default: 15 minutes).
        Path format: bucket/path/to/file.ext (e.g., 'guardianx-idc/features/data.csv')
        """
        # Validate expiry time
        expiry_minutes = data.expiry_minutes or 15
        if expiry_minutes < 1:
            expiry_minutes = 1
        if expiry_minutes > 60:
            expiry_minutes = 60
        
        expiry = timedelta(minutes=expiry_minutes)
        
        # Get preview URL
        preview_data = MediaDataPreviewService.get_preview_url(
            object_path=data.object_path,
            expiry=expiry
        )
        
        if preview_data is None:
            return BaseResponse(
                status_code=400,
                message="File not found or file type not supported for preview (only images, videos, and PDFs are supported)",
                data=None
            )
        
        return BaseResponse(
            status_code=200,
            message="Preview URL generated successfully",
            data=preview_data
        )

    @route.post('/detect-callback')
    def detect_callback(self, request, data: MediaDetectCallbackInSchema):
        """
        Callback for detect media.
        """
        detection_id = data.detection_id
        batch_id = data.batch_id
        frames = data.frames
        url_callback = data.url_callback
        stream_id = data.stream_id
        safe_stream_id = stream_id.rsplit("/", 1)[-1] if stream_id else None
        if safe_stream_id:
            group_code = Device._base_manager.get(unit_id=safe_stream_id).group.code if Device._base_manager.filter(unit_id=safe_stream_id).exists() else None
        else:
            group_code = None
        print("detection_id: ", detection_id)
        print("batch_id: ", batch_id)
        print("frames: ", frames)
        print("url_callback: ", url_callback)
        print("stream_id: ", stream_id)
        logger.info(f"Detect callback received for detection_id={detection_id}, batch_id={batch_id}, url_callback={url_callback}, stream_id={stream_id}")
        
        # 1) Forward callback to WebSocket so FE can render detection frames progressively
        channel_layer = get_channel_layer()
        if channel_layer:
            target_group = f"media_detect_{group_code}" if group_code else "media_detect_global"

            object_name = get_message(MESSAGE_ENUM.MEDIA_DETECT_LABEL_DEFAULT)
            raw_labels = []
            if isinstance(frames, list) and frames:
                for frame in frames:
                    if not isinstance(frame, dict):
                        continue
                    labels = frame.get("labels")
                    if isinstance(labels, list) and labels:
                        raw_labels.extend([str(item) for item in labels if item])
                        continue
                    objects = frame.get("objects")
                    if isinstance(objects, list) and objects:
                        for obj in objects:
                            if not isinstance(obj, dict):
                                continue
                            label = obj.get("label") or obj.get("class_id")
                            if label:
                                raw_labels.append(str(label))

            if raw_labels:
                seen = set()
                unique_raw_labels = []
                for label in raw_labels:
                    if label in seen:
                        continue
                    seen.add(label)
                    unique_raw_labels.append(label)

                translated_labels = []
                for label in unique_raw_labels:
                    label_dict = MESSAGE_ENUM.MEDIA_DETECT_LABEL_TRANSLATIONS.get(label)
                    if label_dict:
                        translated_labels.append(get_message(label_dict))
                    else:
                        translated_labels.append(label)

                object_name = " / ".join(translated_labels)

            message_template = get_message(MESSAGE_ENUM.MEDIA_DETECT_OBJECT_FOUND)
            msg = message_template.format(object_name=object_name)

            event = {
                'type': 'media_detect_notification',
                'msg': msg,
                'data': frames,
                'timestamp': timezone.now().isoformat(),
            }
            async_to_sync(channel_layer.group_send)(target_group, event)
            print(f"Forwarded detect callback to group {target_group}")

        # 2) Batch completion callback: persist analysis_path -> VideoAnalysis (fast lookup in detail)
        # Expected from ai-streaming-service /detect_media callback:
        # {
        #   "batch_id": "...",
        #   "status": "complete",
        #   "results": [
        #     {"object_path": "<source video url/path>", "analysis_path": "<full url>", ...},
        #     ...
        #   ]
        # }
        try:
            from surveillance.models import VideoAnalysis
            results = getattr(data, "results", None) or []
            if results and isinstance(results, list):
                for item in results:
                    if not isinstance(item, dict):
                        continue
                    object_path = item.get("object_path") or item.get("source_object_path")
                    analysis_path = item.get("analysis_path")
                    if not object_path or not analysis_path:
                        continue

                    raw = str(object_path).strip()
                    # Normalize: strip domain/query => keep bucket/key if present
                    try:
                        if raw.startswith("http://") or raw.startswith("https://"):
                            parsed = urlparse(raw)
                            raw = parsed.path.lstrip("/")
                    except Exception:
                        pass

                    # Upsert: keep latest analysis_path (user detect lại -> hiển thị mới nhất)
                    VideoAnalysis._base_manager.update_or_create(
                        defaults={
                            "video_path": object_path,
                            "analysis_path": analysis_path,
                            "updated_at": timezone.now(),
                        },
                    )
        except Exception as e:
            logger.warning(f"Persist VideoAnalysis from callback failed: {e}")
        
        return BaseResponse(status_code=200, message="Detect callback received successfully", data=None)
    
    

    @route.post('/upload-detection')
    def upload_detection(self, request, data: MediaDetectCallbackInSchema, **kwargs):
        """
        Callback when AI service finishes uploading detection result JSON to MinIO.
        We update the corresponding `VideoAnalysis` records so that `analysis_path`
        (and other info in the future) reflect the final location returned by the
        AI service instead of the placeholder value that was generated earlier.
        """
        stream_id = data.stream_id
        safe_stream_id = stream_id.rsplit("/", 1)[-1] if stream_id else None
        if safe_stream_id:
            group_code = Device._base_manager.get(unit_id=safe_stream_id).group.code if Device._base_manager.filter(unit_id=safe_stream_id).exists() else None
        else:
            group_code = None

        channel_layer = get_channel_layer()
        target_group = f"media_upload_detection_{group_code}" if group_code else "media_upload_detection_global"

        # Iterate through each detection result and update (or create) VideoAnalysis
        updated = 0 
        created = 0
        for item in (data.results or []):
            object_path = item.get("object_path")
            analysis_path = item.get("analysis_path")
            file_url = urlparse(object_path).path
            if not object_path or not analysis_path:
                continue  # skip invalid items
            # Try to find existing VideoAnalysis by exact video_path
            va = VideoAnalysis._base_manager.filter(video_path=object_path).order_by('-created_at').first()
            user_file = UserMediaFile._base_manager.filter(file_url=file_url).order_by('-id').first()
            if user_file:
                va.video_file = user_file
                va.save(update_fields=["video_file", "updated_at"])
            if va:
                # Update analysis_path if different
                if va.analysis_path != analysis_path:
                    va.analysis_path = analysis_path
                    va.save(update_fields=["analysis_path", "updated_at"])
                updated += 1
            else:
                # Create a new record as fallback (should rarely happen)
                va = VideoAnalysis._base_manager.create(
                    video_path=object_path,
                    analysis_path=analysis_path,
                    video_file=user_file,
                )
                created += 1

            # Ping socket with analysis JSON + basic VideoAnalysis data
            if channel_layer:
                try:
                    analysis_json = minio_client.get_json(analysis_path) if analysis_path else None
                except Exception as e:
                    logger.warning(f"Failed to load analysis JSON from {analysis_path}: {e}")
                    analysis_json = None

                event = {
                    'type': 'media_upload_detection_notification',
                    'msg': 'upload_detection_completed',
                    'data': {
                        'analysis': analysis_json,
                        'video_analysis': {
                            'id': va.id,
                            'video_path': va.video_path,
                            'analysis_path': va.analysis_path,
                            'drone_name': va.drone_name,
                            'profile_device_id': va.profile_device_id,
                            'stream_monitor_id': va.stream_monitor_id,
                            'created_at': va.created_at.isoformat() if va.created_at else None,
                            'updated_at': va.updated_at.isoformat() if va.updated_at else None,
                        }
                    },
                    'timestamp': timezone.now().isoformat(),
                }
                async_to_sync(channel_layer.group_send)(target_group, event)
        message = f"VideoAnalysis updated: {updated}, created: {created}"
        return BaseResponse(
            status_code=200,
            message=message,
            data={
                "updated": updated,
                "created": created,
                "batch_id": data.batch_id,
                "status": data.status,
            }
        )
