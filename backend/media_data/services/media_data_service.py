"""
MediaDataService - Service for listing media objects from MinIO
Performance optimized: single DB query with select_related, no N+1
"""
from typing import List, Optional, Tuple, Dict, Any, Set
from django.conf import settings
from stream_monitors.utils.minio_client import minio_client
import datetime
import json
import logging
from core.middleware.refresh_token import get_current_request
from core.file_management.models import UserMediaFile
from stream_monitors.utils.minio_client import minio_client
logger = logging.getLogger(__name__)


class MediaDataService:
    """
    Service for listing media objects (images/videos) stored in MinIO.
    """

    # ============== SEARCH/SORT CONFIG ==============
    # Mapping: FE param -> item field
    SEARCH_FIELDS = {
        'object_name': 'object_name',
        'type': 'type',
        'group__name': 'group_name',
        'size': 'size',
    }
    
    SORT_FIELDS = {
        'object_name': 'object_name',
        'type': 'type',
        'size': 'size_bytes',
        'group__name': 'group_name',
        'last_modified': 'last_modified',
    }

    # ============== PUBLIC API ==============
    @classmethod
    def list_media(
        cls,
        media_type: Optional[str] = None,
        prefix: Optional[str] = None,
        request=None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        List media objects with search/sort/pagination support.
        
        Returns combined list (folders + files) already filtered and sorted.
        """
        if not minio_client.available or not minio_client.client:
            return False, {"items": [], "prefix": prefix or ""}

        try:
            # Get request if not provided
            if not request:
                request = get_current_request()
            
            # Get user's group
            group = cls._get_user_group(request)
            if not group:
                return True, {"items": [], "prefix": prefix or "", "group_name": ""}

            group_name = getattr(group, 'name', "") or ""
            
            # Normalize prefix
            effective_prefix = cls._normalize_prefix(prefix)
            
            # Query DB - single query with select_related (no N+1)
            qs = cls._build_queryset(group, effective_prefix)
            
            # Build combined list (folders + files) from DB
            combined = cls._build_combined_list(qs, effective_prefix, media_type, group_name)
            
            # Apply search filters
            combined = cls._filter_items(combined, request)
            
            # Apply sort
            sort_obj = request.GET.get("sort_obj") if request and hasattr(request, 'GET') else None
            combined = cls._sort_items(combined, sort_obj)
            
            # Clean up internal fields
            for item in combined:
                item.pop('size_bytes', None)

            return True, {
                "items": combined,
                "prefix": effective_prefix,
                "group_name": group_name,
            }
            
        except Exception as e:
            logger.exception(f"Error listing media: {e}")
            return False, {"items": [], "prefix": prefix or "", "group_name": ""}

    # ============== SEARCH/SORT METHODS ==============
    @classmethod
    def _filter_items(cls, items: List[dict], request) -> List[dict]:
        """Apply search filters from request.GET params."""
        if not items or not request or not hasattr(request, 'GET'):
            return items
        
        result = items
        for param, field in cls.SEARCH_FIELDS.items():
            value = request.GET.get(param)
            if value:
                search_term = str(value).lower()
                result = [
                    item for item in result
                    if search_term in str(item.get(field, '')).lower()
                ]
                logger.debug(f"Filter by {param}='{value}': {len(items)} -> {len(result)} items")
        
        return result

    @classmethod
    def _sort_items(cls, items: List[dict], sort_obj_raw: Optional[str]) -> List[dict]:
        """Apply sort from sort_obj JSON."""
        if not items or not sort_obj_raw:
            return items
        
        try:
            sort_list = json.loads(sort_obj_raw) if isinstance(sort_obj_raw, str) else sort_obj_raw
            if not isinstance(sort_list, list) or not sort_list:
                return items
            
            result = items.copy()
            
            # Apply sorts in reverse order (first in list = primary sort)
            for sort_item in reversed(sort_list):
                if not isinstance(sort_item, dict):
                    continue
                
                key = sort_item.get('key')
                if key not in cls.SORT_FIELDS:
                    continue
                
                field = cls.SORT_FIELDS[key]
                desc = str(sort_item.get('value', 'asc')).lower() == 'desc'
                
                if field == 'size_bytes':
                    result.sort(key=lambda x: x.get(field) or 0, reverse=desc)
                elif field == 'last_modified':
                    result.sort(key=lambda x: x.get(field) or '', reverse=desc)
                else:
                    result.sort(key=lambda x: str(x.get(field, '')).lower(), reverse=desc)
            
            return result
            
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Invalid sort_obj: {e}")
            return items

    # ============== HELPER METHODS ==============
    @staticmethod
    def _get_user_group(request):
        """Get user's group from request."""
        if not request or not hasattr(request, 'user'):
            return None
        user = request.user
        if not user:
            return None
        profile = getattr(user, 'userprofilelink', None)
        if not profile:
            return None
        return getattr(profile, 'group', None)

    @staticmethod
    def _normalize_prefix(prefix: Optional[str]) -> str:
        """Normalize prefix to end with /"""
        if not prefix:
            return ""
        result = prefix.lstrip('/')
        if result and not result.endswith('/'):
            result = f"{result}/"
        return result

    @classmethod
    def _build_queryset(cls, group, prefix: str):
        """Build optimized queryset - single query, no N+1."""
        qs = UserMediaFile._base_manager.filter(group=group).select_related('group').only(
            'file_url', 'file_size', 'modified_on', 'created_on', 'group__name'
        )
        if prefix:
            qs = qs.filter(file_url__contains=f'/{prefix}')
        return qs

    @classmethod
    def _build_combined_list(
        cls, 
        qs, 
        prefix: str, 
        media_type: Optional[str],
        group_name: str
    ) -> List[dict]:
        """
        Build combined list of folders + files from queryset.
        Folders come first, then files.
        When prefix is empty, return bucket entry only.
        """
        bucket = settings.MINIO_STORAGE_MEDIA_BUCKET_NAME
        media_type_filter = (media_type or 'all').lower()
        
        # When prefix is empty, return bucket entry only
        if not prefix:
            return [{
                'object_name': bucket,
                'full_object_name': f'/{bucket}/',
                'type': 'bucket',
                'size': "",
                'size_bytes': 0,
                'last_modified': "",
                'group_name': group_name,
            }]
        
        folder_names: Set[str] = set()
        files: List[dict] = []
        
        for rec in qs.iterator():
            file_url = getattr(rec, 'file_url', None)
            if not file_url:
                continue
            
            # Convert file_url to object path
            object_path = cls._normalize_object_path(file_url, bucket)
            if not object_path:
                continue
            
            # Check if path matches prefix
            if prefix and not object_path.startswith(prefix):
                continue
            
            # Get remainder after prefix
            remainder = object_path[len(prefix):] if prefix else object_path
            if not remainder:
                continue
            
            # Check if it's a folder (has more path segments)
            if '/' in remainder:
                folder_name = remainder.split('/', 1)[0]
                if folder_name:
                    folder_names.add(folder_name)
                continue
            
            # It's a file at current level
            detected_type = cls._detect_media_type(object_path)
            if media_type_filter in ('image', 'video') and detected_type != media_type_filter:
                continue
            
            # Get metadata
           
            size = getattr(rec, 'file_size', None) or getattr(rec, 'size', None) or minio_client.get_file_size(f"{object_path}")
            modified = getattr(rec, 'modified_on', None) or getattr(rec, 'created_on', None)
            
            files.append({
                'object_name': remainder,
                'full_object_name': f'/{object_path}' if not object_path.startswith('/') else object_path,
                'type': detected_type,
                'size': cls._format_bytes(size),
                'size_bytes': size or 0,
                'last_modified': modified.isoformat() if isinstance(modified, datetime.datetime) else str(modified) if modified else "",
                'group_name': group_name,
            })
        
        # Build folder entries
        entry_type = "bucket" if not prefix else "folder"
        folders = []
        for name in sorted(folder_names):
            folder_path = f'{prefix}{name}/'
            folders.append({
                'object_name': name,
                'full_object_name': f'/{folder_path}' if not folder_path.startswith('/') else folder_path,
                'type': entry_type,
                'size': "",
                'size_bytes': 0,
                'last_modified': "",
                'group_name': group_name,
            })
        
        # Folders first, then files
        return folders + files

    @staticmethod
    def _normalize_object_path(file_url: str, bucket: str) -> Optional[str]:
        """Convert file_url to object path (without bucket prefix)."""
        if not file_url:
            return None
        
        url = str(file_url)
        
        # Handle full URLs
        if url.startswith('http://') or url.startswith('https://'):
            try:
                parts = url.split('://', 1)[1].split('/', 1)
                path = parts[1] if len(parts) > 1 else ''
            except Exception:
                return None
        else:
            path = url.lstrip('/')
        
        # Remove bucket prefix
        # if path.startswith(f'{bucket}/'):
        #     path = path[len(bucket) + 1:]
        
        return path or None

    @staticmethod
    def _detect_media_type(path: str) -> str:
        """Detect media type from file extension."""
        lower = path.lower()
        
        if lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg')):
            return 'image'
        if lower.endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv')):
            return 'video'
        if lower.endswith('.pdf'):
            return 'document'
        
        return 'other'

    @staticmethod
    def _format_bytes(num) -> str:
        """Format bytes to human readable string."""
        if num is None:
            return ""
        try:
            num = float(num)
        except (TypeError, ValueError):
            return ""
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(num) < 1024.0:
                if unit == 'B':
                    return f"{int(num)}B"
                return f"{num:.1f}{unit}".rstrip('0').rstrip('.')
            num /= 1024.0
        return f"{num:.1f}PB"
    