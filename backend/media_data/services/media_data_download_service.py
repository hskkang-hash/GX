from typing import List, Optional, Tuple, Set, Iterator
from django.http import HttpResponse, StreamingHttpResponse
from django.conf import settings
from stream_monitors.utils.minio_client import minio_client
from urllib.parse import quote
import tempfile
import zipfile
from datetime import datetime as dt
import os
import mimetypes
import logging
import re
import threading
from core.middleware.refresh_token import get_current_request
from core.user.models import CoreUser
from task_status.services.task_status_service import TaskStatusService
from common.constant import MESSAGE_ENUM, get_message

logger = logging.getLogger(__name__)


class MediaDataDownloadService:
    
    CHUNK_SIZE = 16 * 1024
    
    @staticmethod
    def _normalize_object_path_from_file_url(file_url: str) -> Optional[str]:
        """
        Convert file_url (e.g., '/guardianx-dev/son/file.jpg' or full URL) to bucket object path.
        """
        if not file_url:
            return None
        url = str(file_url)
        bucket = settings.MINIO_STORAGE_MEDIA_BUCKET_NAME
        # If full URL, strip protocol and endpoint
        if url.startswith('http://') or url.startswith('https://'):
            try:
                # Expect format: https://endpoint/bucket/path
                parts = url.split('://', 1)[1].split('/', 1)
                path_after_host = parts[1] if len(parts) > 1 else ''
            except Exception:
                path_after_host = ''
        else:
            path_after_host = url.lstrip('/')
        # Remove bucket prefix if present
        if path_after_host.startswith(f'{bucket}/'):
            object_path = path_after_host[len(bucket) + 1 :]
        else:
            object_path = path_after_host
        return object_path or None
    
    @classmethod
    def _get_allowed_paths_for_folder(cls, folder_prefix: Optional[str] = None) -> Set[str]:
        """
        Query DB to get files user has access to, optionally filtered by folder prefix.
        
        Args:
            folder_prefix: Optional folder path (e.g., '/guardianx-idc/features/OrderReports/')
                          If provided, only return files under this folder
        
        Returns: set of exact file paths user has access to
        """
        allowed_paths: Set[str] = set()
        try:
            from core.file_management.models import UserMediaFile
            request = get_current_request()
            group = getattr(getattr(getattr(request, 'user', None), 'userprofilelink', None), 'group', None) if request else None
            if not group:
                return allowed_paths
            
            # Query media files for the group
            qs = UserMediaFile._base_manager.filter(group=group).only('file_url')  # type: ignore
            
            # Filter by folder prefix if provided
            if folder_prefix:
                # Use LIKE query to find all files under this folder
                qs = qs.filter(file_url__startswith=folder_prefix)
                logger.info(f"[PERMISSION] Filtering by folder prefix: {folder_prefix}")
            
            for rec in qs:
                file_url = getattr(rec, 'file_url', None)
                object_path = cls._normalize_object_path_from_file_url(file_url) if file_url else None
                if object_path:
                    allowed_paths.add(object_path)
            
            if folder_prefix:
                logger.info(f"[PERMISSION] User has access to {len(allowed_paths)} files under folder {folder_prefix}")
            else:
                logger.info(f"[PERMISSION] User has access to {len(allowed_paths)} files")
            return allowed_paths
        except Exception as e:
            logger.error(f"[PERMISSION] Error getting allowed paths: {e}")
            return allowed_paths
    
    @classmethod
    def download_media(cls, object_paths: Optional[List[str]] = None, username: str = None, task_id: str = None, user_id: int = None):
        """
        Download media - ALWAYS ASYNC với WebSocket progress (DÙNG THREADING GIỐNG HANDOVER).
        
        - Single file → ZIP với 1 file
        - Folder → ZIP với files user có quyền  
        - Multiple items → ZIP tất cả
        
        Returns:
            - dict with task_id for WebSocket tracking
            - None: error occurred
        """
        try:
            if not object_paths:
                logger.error("Error: No object paths provided")
                return None
            
            if not user_id:
                logger.error("Error: user_id is required")
                return None
            
            collected_items, requested_folder = cls._collect_object_paths_from_minio(object_paths)
            if not collected_items:
                logger.error(f"Error: No items collected from paths: {object_paths}")
                return None
            
            # ALWAYS async + ZIP + WebSocket (no sync mode)
            total_size = sum(size for _, _, size in collected_items)
            logger.info(f"[DOWNLOAD] Async mode: {len(collected_items)} files, {total_size / (1024*1024):.2f}MB - creating ZIP async with WebSocket progress")
            return cls._build_async_download(collected_items, object_paths, requested_folder, username, task_id, user_id)
        except Exception as e:
            logger.exception(f"Error in download_media: {e}")
            return None
    
    # --------------------------------
    # Async Download
    # --------------------------------
    @classmethod
    def _build_async_download(cls, items: List[Tuple[str, str, int]], object_paths: List[str], requested_folder: bool, username: str, task_id: str, user_id: int):
        """
        Start background thread for ZIP creation (GIỐNG HANDOVER - DÙNG THREADING).
        Returns dict with task_id for tracking via WebSocket.
        """
        try:
            import re
            
            # Determine ZIP filename
            if requested_folder and len(object_paths) == 1:
                # Single folder → use folder name
                folder_name = object_paths[0].rstrip('/').split('/')[-1]
                safe_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name)
                safe_name = safe_name.strip('._')
                if not safe_name:
                    safe_name = 'download'
                zip_filename = f"{safe_name}.zip"
            else:
                # Multiple items → use timestamp
                ts = dt.now().strftime('%d-%m-%Y-%H-%M-%S')
                zip_filename = f"{ts}_files_list.zip"
            
            logger.info(f"[THREAD] Starting download thread {task_id} for user {username}")
            
            # Start background thread (GIỐNG HANDOVER)
            download_thread = threading.Thread(
                target=cls._process_download_in_thread,
                args=(items, zip_filename, task_id, user_id),
                daemon=True
            )
            download_thread.start()
            
            return {
                'async': True,
                'task_id': task_id,
                'message': 'Download task created. Connect to WebSocket for progress updates.',
                'websocket_url': 'ws/media/download/',
                'total_files': len(items),
            }
        except Exception as e:
            logger.exception(f"[THREAD] Error creating async download: {e}")
            return None
    
    @staticmethod
    def _process_download_in_thread(items: List[Tuple[str, str, int]], zip_filename: str, task_id: str, user_id: int):
        """
        Process download in background thread (GIỐNG HANDOVER).
        
        Args:
            items: List of (bucket, obj_path, size) tuples
            zip_filename: Name for the ZIP file
            task_id: Task ID for tracking
            user_id: User ID
        """
        
        temp_zip_path = None
        try:
            # Get user
            user = CoreUser.objects.get(id=user_id)
            username = user.username
            
            logger.info(f"🔄 Starting media download processing for task {task_id}")
            
            def send_progress(status: str, message: str, progress: int = 0, data: dict = None):
                """Send progress update via WebSocket"""
            
            # Update TaskStatus: pending → processing
            processing_message = f'Starting ZIP creation with {len(items)} files...'
            TaskStatusService.update_status(
                task_id,
                status='processing',
                message=processing_message,
            )
            send_progress('PROCESSING', processing_message, 0)
            
            # Calculate total size
            total_size = sum(size for _, _, size in items)
            logger.info(f"[THREAD] Creating ZIP: {zip_filename}, {len(items)} files, {total_size / (1024*1024):.2f} MB")
            
            # Find common prefix
            object_paths = [obj_path for _, obj_path, _ in items]
            common_prefix = ""
            if len(object_paths) > 1:
                try:
                    common_dir = os.path.commonpath(object_paths)
                    if common_dir and common_dir != '.':
                        parent = os.path.dirname(common_dir)
                        if parent:
                            common_prefix = parent.rstrip('/') + '/'
                except (ValueError, Exception):
                    common_prefix = ""
            
            # Create temp ZIP
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            temp_zip_path = temp_zip.name
            temp_zip.close()
            
            processed_size = 0
            failed_files = []
            
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for idx, (bucket, obj_path, size) in enumerate(items, 1):
                    try:
                        file_progress = int((idx / len(items)) * 90)
                        send_progress('PROCESSING', f'Adding file {idx}/{len(items)}: {os.path.basename(obj_path)}', file_progress)
                        
                        arcname = obj_path
                        if common_prefix and obj_path.startswith(common_prefix):
                            arcname = obj_path[len(common_prefix):]
                        arcname = arcname.lstrip('/')
                        
                        tmp_obj = tempfile.NamedTemporaryFile(delete=False)
                        tmp_obj_path = tmp_obj.name
                        tmp_obj.close()
                        
                        try:
                            minio_client.client.fget_object(bucket, obj_path, tmp_obj_path)
                            zf.write(tmp_obj_path, arcname=arcname)
                            processed_size += size
                        finally:
                            if os.path.exists(tmp_obj_path):
                                os.unlink(tmp_obj_path)
                    except Exception as e:
                        logger.error(f"[THREAD] Error adding {bucket}/{obj_path} to ZIP: {e}")
                        failed_files.append(obj_path)
                        continue
            
            zip_size = os.path.getsize(temp_zip_path)
            logger.info(f"[THREAD] ZIP created: {zip_size / (1024*1024):.2f} MB")
            
            # Upload ZIP to MinIO
            send_progress('PROCESSING', 'Uploading ZIP file to storage...', 90)
            
            download_bucket = settings.MINIO_STORAGE_MEDIA_BUCKET_NAME
            download_prefix = f'downloads/'
            timestamp = dt.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = re.sub(r'[<>:"/\\|?*]', '_', zip_filename)
            minio_path = f'{download_prefix}{timestamp}_{safe_filename}'
            
            minio_client.client.fput_object(
                download_bucket,
                minio_path,
                temp_zip_path,
                content_type='application/zip'
            )
            
            logger.info(f"[THREAD] ZIP uploaded to: {download_bucket}/{minio_path}")
            
            # Generate presigned download URL
            from datetime import timedelta
            download_url = minio_client.client.presigned_get_object(
                download_bucket,
                minio_path,
                expires=timedelta(hours=1)
            )
            
            # Update TaskStatus: processing → success
            done_message = get_message(MESSAGE_ENUM.ACTION_EXPORT_SUCCESS)
            success_payload = {
                'zip_size': zip_size,
                'total_files': len(items),
                'failed_files': len(failed_files),
                'minio_path': minio_path,
            }
            
            file_url_relative = f'/{download_bucket}/{minio_path}'
            
            TaskStatusService.update_status(
                task_id,
                status='success',
                message=done_message,
                data=success_payload,
                download_url=download_url,
                file_url=file_url_relative,
                filename=zip_filename,
                file_id=task_id,
                record_count=len(items),
            )
            logger.info(f"📊 TaskStatus updated to SUCCESS with download_url")
            
            # Send WebSocket notification
            send_progress('DONE', done_message, 100, {
                'download_url': download_url,
                'filename': zip_filename,
                'file_id': task_id,
            })
            
        except Exception as e:
            logger.exception(f"[THREAD] Error creating ZIP: {e}")
            
            # Update TaskStatus: → failed
            error_message = get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED)
            TaskStatusService.update_status(
                task_id,
                status='failed',
                message=error_message,
                data={'error': str(e)},
            )
            
        finally:
            # Cleanup temp ZIP
            if temp_zip_path and os.path.exists(temp_zip_path):
                try:
                    os.unlink(temp_zip_path)
                    logger.info(f"[THREAD] Cleaned up temp ZIP: {temp_zip_path}")
                except Exception as e:
                    logger.error(f"[THREAD] Error cleaning up temp ZIP: {e}")
    
    # --------------------------------
    # Helpers
    # --------------------------------
    @staticmethod
    def _set_download_headers(response: StreamingHttpResponse, filename: str, file_size: int) -> None:
        """
        Set common download headers for StreamingHttpResponse.
        Handles Content-Disposition, CORS, caching, and streaming optimization.
        """
        # Set filename for download (RFC 6266 format for proper filename handling)
        response['Content-Disposition'] = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'
        
        # CRITICAL: Set Content-Length for progress bar to work
        response['Content-Length'] = str(file_size)
        
        # Disable buffering for immediate streaming (critical for progress bar)
        response['X-Accel-Buffering'] = 'no'
        
        # Enable range requests for pause/resume support
        response['Accept-Ranges'] = 'bytes'
        
        # Cache control
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
    
    @staticmethod
    def _file_iterator(file_path: str, chunk_size: int, cleanup_after: bool = True) -> Iterator[bytes]:
        """
        Generator to read file in chunks and yield immediately.
        Each chunk is sent to browser right away for smooth progress bar.
        """
        try:
            with open(file_path, 'rb') as f:
                bytes_sent = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    bytes_sent += len(chunk)
                    # Yield chunk immediately - browser will receive and update progress
                    yield chunk
                logger.info(f"[STREAM] Finished streaming {bytes_sent / (1024*1024):.2f} MB")
        finally:
            # Cleanup temp file after streaming
            if cleanup_after:
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                        logger.info(f"[STREAM] Cleaned up temp file: {file_path}")
                except Exception as e:
                    logger.error(f"[STREAM] Error cleaning up temp file: {e}")
    
    @staticmethod
    def _extract_bucket_and_path(p: str) -> Tuple[str, str]:
        """Extract bucket name and object path from input path."""
        parts = p.lstrip('/').split('/', 1)
        if len(parts) == 1:
            return settings.MINIO_STORAGE_MEDIA_BUCKET_NAME, parts[0]
        
        # Check if first part is bucket name
        potential_bucket = parts[0]
        if potential_bucket.startswith('guardianx-') or potential_bucket == 'media':
            bucket = potential_bucket
            obj_path = parts[1] if len(parts) > 1 else ''
        else:
            bucket = settings.MINIO_STORAGE_MEDIA_BUCKET_NAME
            obj_path = p.lstrip('/')
        
        return bucket, obj_path
    
    @classmethod
    def _collect_object_paths_from_minio(cls, object_paths: Optional[List[str]]) -> Tuple[List[Tuple[str, str, int]], bool]:
        """
        Collect files to download.
        
        LOGIC:
        1. FOLDER (path ends with '/'): 
            - Check permission in DB
            - Query DB for files user has access to under this folder
            - Only download permitted files
        
        2. FILE (path doesn't end with '/'):
            - NO permission check
            - Download directly from MinIO
        
        Returns: (list of (bucket, object_path, size) tuples, is_folder_requested)
        """
        if not object_paths or not minio_client or not getattr(minio_client, 'available', False):
            return [], False
        
        collected: Set[Tuple[str, str, int]] = set()
        has_folder = False
        total_size = 0
        
        for p in object_paths:
            if not p:
                continue
            
            bucket, obj_path = cls._extract_bucket_and_path(p)
            if not obj_path:
                continue
            
            # If ends with '/', it's a folder - CHECK PERMISSION
            if obj_path.endswith('/'):
                has_folder = True
                logger.info(f"[FOLDER DOWNLOAD] User requested folder: {p}")
                
                # 🔒 SECURITY: Query DB for files under this folder that user has access to
                allowed_paths = cls._get_allowed_paths_for_folder(p)
                
                if not allowed_paths:
                    logger.warning(f"[PERMISSION] User has no access to any files in folder: {p}")
                    continue
                
                logger.info(f"[PERMISSION] Found {len(allowed_paths)} files user has access to in folder {p}")
                
                # Get size for each file from MinIO
                for file_path in allowed_paths:
                    try:
                        _, obj_name = cls._extract_bucket_and_path(file_path)
                        stat = minio_client.client.stat_object(bucket, obj_name)
                        size = stat.size or 0
                        total_size += size
                        collected.add((bucket, obj_name, size))
                        logger.debug(f"[DOWNLOAD] Added file: {obj_name} ({size / 1024:.2f} KB)")
                    except Exception as e:
                        logger.error(f"Error getting stat for {file_path}: {e}")
                        # Add with unknown size
                        _, obj_name = cls._extract_bucket_and_path(file_path)
                        collected.add((bucket, obj_name, 0))
            else:
                # Single file - NO PERMISSION CHECK, download directly from MinIO
                logger.info(f"[FILE DOWNLOAD] User requested file: {obj_path} (no permission check)")
                
                try:
                    stat = minio_client.client.stat_object(bucket, obj_path)
                    size = stat.size or 0
                    total_size += size
                    collected.add((bucket, obj_path, size))
                    logger.info(f"[DOWNLOAD] File added: {obj_path} ({size / (1024*1024):.2f} MB)")
                except Exception as e:
                    logger.error(f"Error getting stat for {bucket}/{obj_path}: {e}")
                    # Try to add anyway with unknown size
                    collected.add((bucket, obj_path, 0))
        
        logger.info(f"[DOWNLOAD] Collected {len(collected)} files, total size: {total_size / (1024*1024):.2f} MB")
        return list(collected), has_folder

    @classmethod
    def _build_single_file_response_from_path(cls, bucket: str, object_path: str) -> Optional[StreamingHttpResponse]:
        if not object_path or not bucket:
            return None
        
        if not minio_client or not getattr(minio_client, 'available', False):
            return None
        
        tmp_fp = None
        try:
            # Download to temp file
            tmp = tempfile.NamedTemporaryFile(delete=False)
            tmp_fp = tmp.name
            tmp.close()
            
            logger.info(f"[DOWNLOAD] Downloading single file: {bucket}/{object_path}")
            minio_client.client.fget_object(bucket, object_path, tmp_fp)
            
            # Get file info
            file_size = os.path.getsize(tmp_fp)
            filename = os.path.basename(object_path)
            content_type, _ = mimetypes.guess_type(filename)
            
            logger.info(f"[DOWNLOAD] File size: {file_size / (1024*1024):.2f} MB, streaming with {cls.CHUNK_SIZE / 1024:.0f}KB chunks")
            
            # Use StreamingHttpResponse with iterator for smooth progress
            response = StreamingHttpResponse(
                cls._file_iterator(tmp_fp, cls.CHUNK_SIZE, cleanup_after=True),
                content_type=content_type or 'application/octet-stream'
            )
            
            # Set all download headers
            cls._set_download_headers(response, filename, file_size)
            # Set all download headers
            cls._set_download_headers(response, filename, file_size)
            
            return response
        except Exception as e:
            logger.exception(f"[DOWNLOAD] Error downloading file: {e}")
            # Cleanup on error
            if tmp_fp and os.path.exists(tmp_fp):
                try:
                    os.unlink(tmp_fp)
                except Exception:
                    pass
            return None

    @classmethod
    def _write_path_to_zip(cls, zf: zipfile.ZipFile, bucket: str, object_path: str, common_prefix: str):
        if not object_path or not bucket:
            return
        # Strip common prefix from arcname
        arcname = object_path
        if common_prefix and object_path.startswith(common_prefix):
            arcname = object_path[len(common_prefix):]
        arcname = arcname.lstrip('/')
        
        if not minio_client or not getattr(minio_client, 'available', False):
            return
        
        tmp_obj_path = None
        try:
            # Try using temporary file first (more memory efficient)
            tmp_obj = tempfile.NamedTemporaryFile(delete=False)
            tmp_obj_path = tmp_obj.name
            tmp_obj.close()
            
            try:
                minio_client.client.fget_object(bucket, object_path, tmp_obj_path)
                zf.write(tmp_obj_path, arcname=arcname)
                return
            except Exception as e:
                logger.warning(f"Error using fget_object for {bucket}/{object_path}: {e}, falling back to get_object")
                # Fall back to get_object with streaming
                resp = minio_client.client.get_object(bucket, object_path)
                try:
                    content_bytes = resp.read()
                    zf.writestr(arcname, content_bytes)
                finally:
                    try:
                        resp.close()
                        resp.release_conn()
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Error writing {bucket}/{object_path} to zip: {e}")
        finally:
            # Always clean up temp file
            if tmp_obj_path and os.path.exists(tmp_obj_path):
                try:
                    os.unlink(tmp_obj_path)
                except Exception as e:
                    logger.error(f"Error cleaning up temp file {tmp_obj_path}: {e}")

    @classmethod
    def _build_zip_response_from_paths(cls, items: List[Tuple[str, str, int]], folder_name: Optional[str] = None) -> Optional[StreamingHttpResponse]:
        # Calculate total size
        total_size = sum(size for _, _, size in items)
        logger.info(f"[ZIP] Total uncompressed size: {total_size / (1024*1024):.2f} MB")
        
        # Find common prefix to strip from archive paths
        object_paths = [obj_path for _, obj_path, _ in items]
        common_prefix = ""
        
        if len(object_paths) > 1:
            try:
                common_dir = os.path.commonpath(object_paths)
                if common_dir and common_dir != '.':
                    # Use parent of common directory as prefix to preserve folder structure
                    parent = os.path.dirname(common_dir)
                    if parent:
                        common_prefix = parent.rstrip('/') + '/'
            except (ValueError, Exception):
                common_prefix = ""
        
        # Determine ZIP filename
        if folder_name:
            # Single folder → use folder name
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name)
            safe_name = safe_name.strip('._')
            if not safe_name:
                safe_name = 'download'
            zip_filename = f"{safe_name}.zip"
        else:
            # Multiple items → use timestamp
            ts = dt.now().strftime('%d-%m-%Y-%H-%M-%S')
            zip_filename = f"{ts}_files_list.zip"
        
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_zip_path = temp_zip.name
        temp_zip.close()
        
        try:
            logger.info(f"[ZIP] Creating archive '{zip_filename}' with {len(items)} items...")
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for idx, (bucket, obj_path, size) in enumerate(items, 1):
                    try:
                        size_mb = size / (1024*1024) if size > 0 else 0
                        logger.info(f"[ZIP] Adding file {idx}/{len(items)}: {obj_path} ({size_mb:.2f} MB)")
                        cls._write_path_to_zip(zf, bucket, obj_path, common_prefix)
                    except Exception as e:
                        logger.error(f"Error adding {bucket}/{obj_path} to zip: {e}")
                        continue
            
            # Get file size
            file_size = os.path.getsize(temp_zip_path)
            logger.info(f"[ZIP] Created ZIP file: {file_size / (1024*1024):.2f} MB, streaming with {cls.CHUNK_SIZE / 1024:.0f}KB chunks")
            
            # Use StreamingHttpResponse with iterator for smooth progress bar
            response = StreamingHttpResponse(
                cls._file_iterator(temp_zip_path, cls.CHUNK_SIZE, cleanup_after=True),
                content_type='application/zip'
            )
            
            # Set all download headers
            cls._set_download_headers(response, zip_filename, file_size)
            # Set all download headers
            cls._set_download_headers(response, zip_filename, file_size)
            
            return response
        except Exception as e:
            logger.error(f"Error building zip response: {e}")
            # Clean up on error
            try:
                if os.path.exists(temp_zip_path):
                    os.unlink(temp_zip_path)
            except Exception:
                pass
            return None

