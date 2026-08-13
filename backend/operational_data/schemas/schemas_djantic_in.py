"""
Schemas đầu vào (IN) sử dụng django-ninja Schema
Chỉ chứa các schemas cho dữ liệu đầu vào từ requests
"""

from ninja import Schema
from typing import List, Optional

class DownloadOperationalDataInSchema(Schema):
    """Schema cho request download operational data với danh sách delivery operation item IDs"""
    delivery_operation_item_ids: List[int]

class OperationalNoticeCreateInSchema(Schema):
    """Schema cho tạo mới operational notice"""
    name: str
    content1: Optional[str] = None
    content2: Optional[str] = None
    content3: Optional[str] = None
    active: bool = True

class OperationalNoticeUpdateInSchema(Schema):
    """Schema cho cập nhật operational notice"""
    name: Optional[str] = None
    content1: Optional[str] = None
    content2: Optional[str] = None
    content3: Optional[str] = None
    active: Optional[bool] = None

class OperationalNoticeBulkDeleteInSchema(Schema):
    """Schema cho xóa nhiều operational notices"""
    ids: str  
