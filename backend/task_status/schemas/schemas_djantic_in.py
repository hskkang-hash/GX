"""
Schemas đầu vào (IN) cho module Task Status
"""

from typing import Any, Dict, Optional

from ninja import Schema


class TaskStatusCreateInSchema(Schema):
    """Schema đầu vào cho việc tạo mới TaskStatus"""

    task_id: str
    task_type: str
    category: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    message_title: Optional[str] = None
    message_body: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None
    progress: Optional[float] = None
    action: Optional[str] = None
    task_channel: Optional[str] = None
    trigger_source: Optional[str] = None
    download_url: Optional[str] = None
    file_url: Optional[str] = None
    filename: Optional[str] = None
    file_id: Optional[str] = None
    record_count: Optional[int] = None
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    related_model: Optional[str] = None
    related_object_id: Optional[str] = None


class TaskStatusUpdateInSchema(Schema):
    """Schema đầu vào cho việc cập nhật TaskStatus"""

    status: Optional[str] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    progress: Optional[float] = None
    message_title: Optional[str] = None
    message_body: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    action: Optional[str] = None
    task_channel: Optional[str] = None
    trigger_source: Optional[str] = None
    download_url: Optional[str] = None
    file_url: Optional[str] = None
    filename: Optional[str] = None
    file_id: Optional[str] = None
    record_count: Optional[int] = None
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

