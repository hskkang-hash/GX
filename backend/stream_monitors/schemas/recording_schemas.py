from pydantic import BaseModel
from typing import Optional


class RecordingResponse(BaseModel):
    """Response model for recording operations."""
    stream_id: str
    is_recording: bool = False
    object_path: Optional[str] = None
    message: str
    success: bool = True


class RecordingStatusResponse(BaseModel):
    """Response model for recording status operations."""
    record_code: str
    stream_id: Optional[str] = None
    record_id: Optional[str] = None
    status: str
    is_recording: bool = False
    object_path: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    completed_at: Optional[str] = None
    updated_at: Optional[str] = None
    success: bool = True
