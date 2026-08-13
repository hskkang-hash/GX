from core.common.schema_utils import DynamicSchema
from ninja import Schema
from datetime import datetime

from checklist_setting.models import ChecklistSetting, ChecklistSettingCategory


class ChecklistSettingInputSchema(Schema):
    item_name: dict[str, str]
    category: int


class ChecklistSettingOutputSchema(DynamicSchema):

    class Meta:

        model = ChecklistSetting
        model_fields = '__all__'


class ChecklistSettingCategoryInputSchema(Schema):
    name: str
    code: str


class ChecklistSettingCategoryOutputSchema(DynamicSchema):


    class Meta:
        model = ChecklistSettingCategory

        exclude = []
        depth = 0
