"""
Schemas đầu ra (OUT) sử dụng django-ninja DynamicSchema
Chỉ chứa các schemas cho dữ liệu trả về từ API
"""

from ninja import Schema
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from handover.models import (
    HandoverShift, HandoverDocument, 
    HandoverDocumentAcceptor, HandoverContent, HandoverNotice, 
    HandoverNoticeComment
)
from core.common.schema_utils import DynamicSchema


class HandoverShiftOutSchema(DynamicSchema):
    """Schema đầu ra cho HandoverShift"""
    class Meta:
        model = HandoverShift
        model_fields = '__all__'

class HandoverDocumentAcceptorOutSchema(DynamicSchema):
    """Schema đầu ra cho HandoverDocumentAcceptor"""
    class Meta:
        model = HandoverDocumentAcceptor


class HandoverContentOutSchema(DynamicSchema):
    """Schema đầu ra cho HandoverContent"""
    class Meta:
        model = HandoverContent


class HandoverDocumentOutSchema(DynamicSchema):
    """Schema đầu ra cho HandoverDocument"""
    class Meta:
        model = HandoverDocument


class HandoverDocumentListOutSchema(DynamicSchema):
    """Schema đầu ra cho danh sách HandoverDocument với trạng thái"""
    class Meta:
        model = HandoverDocument


class HandoverDutyDetailOutSchema(DynamicSchema):
    """Schema đầu ra cho chi tiết Handover Duty"""
    class Meta:
        model = HandoverDocument


class HandoverNoticeCommentOutSchema(DynamicSchema):
    """Schema đầu ra cho HandoverNoticeComment"""
    class Meta:
        model = HandoverNoticeComment


class HandoverNoticeOutSchema(DynamicSchema):
    """Schema đầu ra cho HandoverNotice"""
    class Meta:
        model = HandoverNotice


class HandoverNoticeDetailOutSchema(HandoverNoticeOutSchema):
    """Schema đầu ra cho chi tiết HandoverNotice"""
    class Meta:
        model = HandoverNotice

