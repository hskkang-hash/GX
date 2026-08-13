from ninja_extra import NinjaExtraAPI
from checklist_setting.views import (
    ChecklistSettingCategoryController,
    ChecklistSettingController,
)

checklist_setting_api = NinjaExtraAPI(urls_namespace="checklist_setting")
checklist_setting_api.register_controllers(ChecklistSettingController)
checklist_setting_api.register_controllers(ChecklistSettingCategoryController)
