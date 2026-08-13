from datetime import datetime
from typing import Optional, Dict, Any
from core.common.schema_utils import DynamicSchema
from operation_settings.models import OperationSettings


class OperationSettingsOutSchema(DynamicSchema):
    class Meta:
        model = OperationSettings
        model_fields = []
