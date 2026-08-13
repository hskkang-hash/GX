from typing import Optional, List
from ninja import Schema


class MediaItemOutSchema(Schema):
    """
    Output schema for a single media item in MinIO.
    """
    object_name: str
    type: str  # 'image' | 'video' | 'folder' | 'bucket' | 'other'
    size: Optional[str] = None
    last_modified: Optional[str] = None  # ISO datetime string
    group_name: Optional[str] = None


class MediaPreviewOutSchema(Schema):
    """
    Output schema for media preview URL.
    """
    url: str
    bucket: str
    object_path: str
    full_path: str
    type: str
    content_type: Optional[str] = None
    size: Optional[int] = None
    size_formatted: Optional[str] = None
    last_modified: Optional[str] = None
    expires_in_seconds: int


class MediaItemV2OutSchema(Schema):
    """
    Output schema for a single media item v2 with enhanced fields.
    """
    name: str  # File name
    from_drone: Optional[str] = None  # Drone name (e.g., "Drone 1")
    last_modified: Optional[str] = None  # Formatted date time (e.g., "04-10-2024 11:24:20")
    group: Optional[str] = None  # Group name (e.g., "Group 1")
    object_path: Optional[str] = None  # Full object path
    type: Optional[str] = None  # 'image' | 'video'
    size: Optional[str] = None  # Formatted size


class AIAnalysisResultOutSchema(Schema):
    """
    Output schema for AI analysis result.
    """
    model: str  # Detection model name (e.g., "person")
    object_count: int  # Number of detected objects
    object_image: Optional[str] = None  # URL to object thumbnail/image
    detect_time: Optional[str] = None  # Detection time


class MediaDetailV2OutSchema(Schema):
    """
    Output schema for media detail v2 with AI analysis.
    """
    name: str
    from_drone: Optional[str] = None
    last_modified: Optional[str] = None
    group: Optional[str] = None
    object_path: Optional[str] = None
    type: Optional[str] = None
    size: Optional[str] = None
    preview_url: Optional[str] = None
    ai_analysis: Optional[List[AIAnalysisResultOutSchema]] = None


class MediaDetectV2OutSchema(Schema):
    """
    Output schema for media detect v2.
    """
    object_path: str
    success: bool
    detections: Optional[List[dict]] = None
    error: Optional[str] = None
