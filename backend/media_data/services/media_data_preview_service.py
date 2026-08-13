from typing import Optional, Dict, Any
from core.file_management.models import UserMediaFile
from django.conf import settings
from surveillance.models import VideoAnalysis
from stream_monitors.utils.minio_client import minio_client
from datetime import timedelta
import logging
import os
import time

from media_data.services.media_data_service import MediaDataService

logger = logging.getLogger(__name__)


class MediaDataPreviewService:
    """
    Service for generating preview URLs for media files stored in MinIO.
    Uses presigned URLs for optimal performance.
    Only supports preview for images, videos, and PDFs.
    """
    
    # Default expiry time for preview URLs (shorter than download URLs for security)
    DEFAULT_EXPIRY = timedelta(minutes=15)
    
    # Supported file extensions for preview
    PREVIEWABLE_EXTENSIONS = {
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg',
        # Videos
        '.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.flv', '.wmv',
        # PDF
        '.pdf'
    }
    
    @staticmethod
    def _extract_bucket_and_path(path: str) -> tuple[str, str]:
        """
        Extract bucket name and object path from input path.
        Format: bucket-name/path/to/file.ext
        Example: guardianx-idc/features/data.csv -> ('guardianx-idc', 'features/data.csv')
        """
        parts = path.lstrip('/').split('/', 1)
        if len(parts) == 1:
            # No slash found, use default bucket
            return settings.MINIO_STORAGE_MEDIA_BUCKET_NAME, parts[0]
        
        # Check if first part is bucket name (starts with 'guardianx-' or is known bucket)
        potential_bucket = parts[0]
        if potential_bucket.startswith('guardianx-') or potential_bucket in ['media', 'lms-media']:
            bucket = potential_bucket
            obj_path = parts[1] if len(parts) > 1 else ''
        else:
            # Use default bucket
            bucket = settings.MINIO_STORAGE_MEDIA_BUCKET_NAME
            obj_path = path.lstrip('/')
        
        return bucket, obj_path
    
    @classmethod
    def _is_previewable(cls, file_path: str) -> bool:
        """
        Check if file extension is supported for preview.
        Only images, videos, and PDFs are previewable.
        """
        _, ext = os.path.splitext(file_path.lower())
        return ext in cls.PREVIEWABLE_EXTENSIONS
    
    @classmethod
    def get_preview_url(
        cls, 
        object_path: str,
        expiry: Optional[timedelta] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a presigned URL for previewing a media file.
        Only supports images, videos, and PDFs.
        
        Args:
            object_path: Full path with bucket (e.g., "guardianx-idc/features/photo.jpg")
            expiry: URL expiration time (default: 15 minutes)
        
        Returns:
            Dict with url and metadata, or None if error/unauthorized/unsupported
        """
        if not object_path:
            logger.error("Object path is required")
            return None
        
        if not minio_client or not getattr(minio_client, 'available', False):
            logger.error("MinIO client not available")
            return None
        
        # Extract bucket and object path
        bucket, obj_path = cls._extract_bucket_and_path(object_path)
        if not obj_path:
            logger.error(f"Invalid object path: {object_path}")
            return None
        
        # Check if file type is previewable
        if not cls._is_previewable(obj_path):
            logger.warning(f"File type not supported for preview: {obj_path}")
            return None
        
        try:
            expiry_time = expiry or cls.DEFAULT_EXPIRY
            
            max_retries = 3
            retry_delay = 0.3
            
            for attempt in range(max_retries):
                try:
                    stat = minio_client.client.stat_object(bucket, obj_path)
                    size = stat.size
                    content_type = stat.content_type
                    last_modified = stat.last_modified
                    
                    break
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"[PREVIEW] stat_object failed on attempt {attempt + 1}, retrying in {retry_delay}s: {e}")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"[PREVIEW] File not found on MinIO after {max_retries} attempts: {bucket}/{obj_path}: {e}")
                        return None
            
            # Generate presigned URL using MinIO client
            # This is the optimal approach - client accesses MinIO directly
            presigned_url = minio_client.client.presigned_get_object(
                bucket_name=bucket,
                object_name=obj_path,
                expires=expiry_time
            )
            
            # Detect media type
            media_type = MediaDataService._detect_media_type(obj_path)
            video_record = UserMediaFile.objects.filter(file_url=f'/{bucket}/{obj_path}').order_by('-id').first()
            if video_record:
                analysis_path = VideoAnalysis.objects.filter(video_file=video_record).order_by('-id').first().analysis_path if VideoAnalysis.objects.filter(video_file=video_record) else None 
                if analysis_path:
                    analysis_id = VideoAnalysis.objects.filter(video_file=video_record).order_by('-id').first().id if VideoAnalysis.objects.filter(video_file=video_record) else None
                    analysis_json = minio_client.get_json(analysis_path)
                elif VideoAnalysis.objects.filter(video_path__icontains=object_path).order_by('-id').first().analysis_path if VideoAnalysis.objects.filter(video_path__icontains=object_path) else None :
                    analysis_path = VideoAnalysis.objects.filter(video_path__icontains=object_path).order_by('-id').first().analysis_path
                    analysis_id = VideoAnalysis.objects.filter(video_path__icontains=object_path).order_by('-id').first().id
                    analysis_json = minio_client.get_json(analysis_path)
                else:
                    analysis_id = None
                    analysis_json = None
            return {
                "url": presigned_url,
                "bucket": bucket,
                "object_path": obj_path,
                "full_path": object_path,
                "type": media_type,
                "content_type": content_type,
                "size": size,
                "size_formatted": MediaDataService._format_bytes(size) if size else None,
                "last_modified": last_modified.isoformat() if last_modified else None,
                "expires_in_seconds": int(expiry_time.total_seconds()),
                "analysis": analysis_json,
                "analysis_id": analysis_id,
            }
            
        except Exception as e:
            logger.exception(f"Error generating preview URL for {object_path}: {e}")
            return None
