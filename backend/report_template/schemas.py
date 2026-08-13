from ninja import Schema
from core.common.schema_utils import DynamicSchema
from report_template.models import ReportTemplate
from typing import Optional


class ReportTemplateInputSchema(Schema):
    name: str
    template: str
    is_default: bool = False
    is_enabled: bool = True


class ReportTemplateOutputSchema(DynamicSchema):
    class Meta:
        model = ReportTemplate
        model_fields = '__all__'  
        exclude = []
        depth = 0


class ReportTemplateUpdateSchema(Schema):
    name: Optional[str] = None
    template: Optional[str] = None
    is_default: Optional[bool] = None
    is_enabled: Optional[bool] = None
