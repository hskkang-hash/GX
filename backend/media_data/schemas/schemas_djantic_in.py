from typing import Optional
from ninja import Schema


class MediaListInSchema(Schema):
    """
    Input schema for listing media from MinIO.
    - media_type: filter by 'image', 'video', or 'all' (default: 'all')
    - prefix: optional path prefix under bucket (e.g., 'images/', 'videos/stream123/')
    - current_page: page number (1-based)
    - page_size: items per page
    """
    media_type: Optional[str] = None
    prefix: Optional[str] = None
    current_page: Optional[int] = 1
    page_size: Optional[int] = 25


class MediaDownloadInSchema(Schema):
    """
    Input schema for downloading media.
    - object_paths: list of full object paths (file or folder ending with '/')
        e.g., 'guardianx-idc/features/OrderReports/a.pdf' or 'guardianx-idc/features/OrderReports/'
    
    Behavior:
    - Single file → streamed directly (fast)
    - Multiple files or folder → async with WebSocket progress
    """
    object_paths: Optional[list[str]] = None


class MediaPreviewInSchema(Schema):
    """
    Input schema for getting preview URL of a media file.
    - object_path: full object path with bucket (e.g., 'guardianx-idc/features/photo.jpg')
    - expiry_minutes: URL expiration time in minutes (default: 15, max: 60)
    """
    object_path: str
    expiry_minutes: Optional[int] = 15

class MediaItemDetectInSchema(Schema):
    """
    Input schema for detecting media files.
    - object_path: full object path (file or folder ending with '/')
    - detection_result: detection result
    """
    object_path: str
    media_type: str
    json_filename: Optional[str] = None
    
class MediaDetectInSchema(Schema):
    """
    Input schema for detecting media files.
    - object_paths: list of full object paths (file or folder ending with '/')
        e.g., 'guardianx-idc/features/OrderReports/a.pdf' or 'guardianx-idc/features/OrderReports/'
    """
    media_items: Optional[list[MediaItemDetectInSchema]] = None
    detection_type: Optional[str] = "person"

class MediaDetectCallbackInSchema(Schema):
    """
    Input schema for detecting media callback.
    - batch_id: batch ID
    - status: status
    - results: results
    """
    detection_id: Optional[str] = None
    batch_id: Optional[str] = None
    stream_id: Optional[str] = None
    url_callback: Optional[str] = None
    frames: Optional[list[dict]] = None
    # Batch callback (ai-streaming-service /detect_media completion)
    status: Optional[str] = None
    total_items: Optional[int] = None
    successful_items: Optional[int] = None
    failed_items: Optional[int] = None
    results: Optional[list[dict]] = None
class MediaListV2InSchema(Schema):
    """
    Input schema for listing media v2 with enhanced filtering.
    - media_type: filter by 'image', 'video', or 'all' (default: 'all')
    - from: filter by drone name (e.g., 'Drone 1')
    - group: filter by group name (e.g., 'Group 1')
    - name: search by file name
    - current_page: page number (1-based)
    - page_size: items per page (default: 25)
    - sort_obj: JSON string for sorting, e.g. [{"key":"name","value":"desc"}]
    """
    media_type: Optional[str] = None
    from_drone: Optional[str] = None  # Filter by drone name
    group: Optional[str] = None  # Filter by group name
    name: Optional[str] = None  # Search by file name
    current_page: Optional[int] = 1
    page_size: Optional[int] = 25
    sort_obj: Optional[str] = None  # JSON string for sorting


class MediaDetailV2InSchema(Schema):
    """
    Input schema for getting media detail v2.
    - id: media file id
    """
    id: str


class MediaDetectV2InSchema(Schema):
    """
    Input schema for detecting media v2 using TorchServe.
    - object_path: full object path (e.g., 'guardianx-idc/features/image.jpg')
    - model_name: TorchServe model name (default: 'yolo11n')
    """
    object_path: str
    model_name: Optional[str] = "yolo11n"