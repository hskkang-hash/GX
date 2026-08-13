from typing import List, Optional, Dict, Any
from ninja import Schema
from core.common.schema_utils import DynamicSchema

from print_format.models import PrintFormat
class ModelFieldSchema(Schema):
    name: str
    field_type: Optional[str] = None
    label: str
    is_required: Optional[bool] = None
    fields: Optional[List['ModelFieldSchema']] = None
    data_example: Optional[Any] = None
class PrintFormatSchema(DynamicSchema):
    class Meta:
        model = PrintFormat
        exclude = []
        depth = 0

class PrintFormatCreateSchema(Schema):
    name: str
    template: str
    css: Optional[str] = None
    is_default: bool = False
    is_enabled: bool = True

class PrintFormatUpdateSchema(Schema):
    name: Optional[str] = None
    template: Optional[str] = None
    css: Optional[str] = None
    is_default: Optional[bool] = None
    is_enabled: Optional[bool] = None

class PrintFormatPreviewSchema(Schema):
    html: str
    data: Dict[str, Any]

class PrintFormatRenderSchema(Schema):
    html: str
    data: Dict[str, Any] 