"""
Schemas đầu vào (IN) sử dụng django-ninja Schema
Chỉ chứa các schemas cho dữ liệu đầu vào từ requests
"""

from ninja import Schema
from typing import List, Optional, Dict, Any
from datetime import datetime, date


class HandoverShiftCreateInSchema(Schema):
    """Schema tạo mới HandoverShift"""
    name: Any  # Có thể là str hoặc dict {"en": "...", "ko": "..."}
    start_time: str
    end_time: str
    color: Optional[str] = None


class HandoverShiftUpdateInSchema(Schema):
    """Schema cập nhật HandoverShift"""
    id: int
    name: Any  # Có thể là str hoặc dict {"en": "...", "ko": "..."}
    start_time: str
    end_time: str
    color: Optional[str] = None


class WorkShiftConfigInSchema(Schema):
    """Schema cấu hình hàng loạt ca làm việc"""
    create_shifts: Optional[List[HandoverShiftCreateInSchema]] = None
    update_shifts: Optional[List[HandoverShiftUpdateInSchema]] = None
    delete_shifts: Optional[List[int]] = None


class HandoverDocumentCreateInSchema(Schema):
    """Schema tạo mới HandoverDocument"""
    date: str  # YYYY-MM-DD
    shift_id: int


class HandoverDocumentDeleteInSchema(Schema):
    """Schema xóa HandoverDocument"""
    ids: List[int]


class HandoverContentCreateInSchema(Schema):
    """Schema tạo mới HandoverContent"""
    handover_doc_id: int
    content: str
    is_notice: Optional[bool] = False
    updated_time: Optional[datetime] = None


class HandoverContentUpdateInSchema(Schema):
    """Schema cập nhật HandoverContent"""
    content_id: int
    content: str
    is_notice: Optional[bool] = False
    updated_time: Optional[datetime] = None


class HandoverContentItemInSchema(Schema):
    """Schema cho một item trong danh sách HandoverContent"""
    content: str
    is_notice: Optional[bool] = False
    content_id: Optional[int] = None  # Nếu có thì update, không có thì create
    handover_doc_id: int


class HandoverContentsBatchInSchema(Schema):
    """Schema tạo/cập nhật hàng loạt HandoverContent"""
    handover_contents: List[HandoverContentItemInSchema]


class HandoverContentDeleteInSchema(Schema):
    """Schema xóa HandoverContent"""
    content_id: int
    handover_doc_id: Optional[int] = None


class HandoverDutyDetailInSchema(Schema):
    """Schema lấy chi tiết nhiều handover documents"""
    handover_ids: List[int]


class HandoverNoticeCreateInSchema(Schema):
    """Schema tạo mới HandoverNotice"""
    content: str
    notice_id: Optional[int] = None  # Nếu có thì update
    removed_file_ids: Optional[List[int]] = None


class HandoverNoticeDeleteInSchema(Schema):
    """Schema xóa HandoverNotice"""
    id: int


class HandoverNoticeProcessInSchema(Schema):
    """Schema đánh dấu xử lý HandoverNotice"""
    id: int
    is_processed: bool


class HandoverNoticeRestoreInSchema(Schema):
    """Schema khôi phục HandoverNotice"""
    id: int


class HandoverNoticeCommentCreateInSchema(Schema):
    """Schema tạo mới HandoverNoticeComment"""
    notice_id: int
    comment: str
    parent_id: Optional[int] = None  # Nếu có thì là reply


class HandoverNoticeCommentUpdateInSchema(Schema):
    """Schema cập nhật HandoverNoticeComment"""
    comment_id: int
    comment: str


class HandoverNoticeCommentDeleteInSchema(Schema):
    """Schema xóa HandoverNoticeComment"""
    id: int


class DownloadManagementInSchema(Schema):
    """Schema download handover management"""
    start_date_time: str
    end_date_time: str


class DownloadNoticeInSchema(Schema):
    """Schema download handover notice"""
    selected_field: List[str]
    get_delete_notice: Optional[bool] = False

