import os
from typing import List

from common.pagination import OptimizedPaginator
from common.utils import get_gcs_api_headers
from django.db.models import F
from django.utils import timezone
from ninja_extra import api_controller, route
import requests


from checklist_setting.models import ChecklistSetting, ChecklistSettingCategory
from checklist_setting.schemas import (
    ChecklistSettingCategoryInputSchema,
    ChecklistSettingCategoryOutputSchema,
)
from checklist_setting.schemas import ChecklistSettingInputSchema
from checklist_setting.schemas import ChecklistSettingOutputSchema
from common.tenant_filters import assert_scoped
from common.constant import MESSAGE_ENUM
from core.api.v1.auth import CustomJWTAuth
from core.base import BaseResponse
from core.common.search.dynamic_search import apply_dynamic_filters
from core.role.permission import path_permission
from core.multilanguage.request_handlers import (
    create_model_with_translations,
    update_model_with_translations,
)
from delivery.models import DeliveryOperation, DeliveryOperationApprovalChecklist
from devices.models import Device

# Create your views here.
@api_controller("/", tags=["Checklist Setting"])
class ChecklistSettingController:
    """
    Checklist Setting Controller
    """

    @route.get("", response=List[ChecklistSettingOutputSchema], auth=CustomJWTAuth())
    @path_permission("read", path_override="/checklist-setting")
    def list(self, request, page_size: int = 25, current_page: int = 1, device_id: str = None, active: bool = None):
        """
        Get paginated list of checklist settings with optional filtering and sorting

        Parameters:
        - page_size: Number of items per page
        - current_page: Current page number
        - sort_obj: JSON string for sorting (e.g. {"field": "created_on", "order": "desc"})
        - device_id: ID of the device
        """
        try:
            data = ChecklistSetting.objects.annotate(
                category_name=F("category__name"),
                category_code=F("category__code"),
            ).order_by("-created_on")
            if active:
                data = data.filter(is_active=active)
            data = apply_dynamic_filters(
                data, request, [], request.GET.get("sort_obj", None)
            )
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(data, page_size)
            pages = paginator.page(current_page)
            all_template = ChecklistSettingOutputSchema.from_queryset(
                pages.object_list, many=True
            )
            auto_checklist = None
            if device_id:
                flightbrid_url = os.getenv('FLIGHTBRID_URL')
                if not flightbrid_url:
                    return BaseResponse(
                        status_code=500,
                        message="FLIGHTBRID_URL not configured",
                        success=False,
                        data=None
                    )
                params = {
                    'page': current_page,
                    'pageSize': page_size
                }

                headers = get_gcs_api_headers()
                response = requests.get(
                    f"{flightbrid_url}/api/drone/health/sensor-status/{device_id}",
                    params=params,
                    headers=headers,
                    timeout=30
                )

                if response.status_code == 200:
                    auto_checklist = response.json()
                    auto_checklist['drone_status'] = Device.objects.get(unit_id=device_id).status.code
                else:
                    return BaseResponse(
                        status_code=response.status_code,
                        message=f"Error from FLIGHTBRID: {response.text}",
                        success=False,
                        data=None
                    )
            return BaseResponse(
                status_code=200,
                success=True,
                message=MESSAGE_ENUM.get(
                    MESSAGE_ENUM.GET_LIST_CHECKLIST_SETTING_SUCCESS
                ),
                data=all_template,
                auto_checklist=auto_checklist,
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page,
            )
        except Exception as e:
            print(e)
            return BaseResponse(
                status_code=400,
                success=False,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.post("", response=ChecklistSettingOutputSchema, auth=CustomJWTAuth())
    @path_permission("create", path_override="/checklist-setting")
    def create(self, request, data: ChecklistSettingInputSchema):
        """
        Create checklist setting
        Request body:
        - item_name: Name of the checklist setting
        - category: Category of the checklist setting
        """
        try:
            checklist_data = data.dict()
            checklist_data["category"] = ChecklistSettingCategory.objects.get(
                id=checklist_data["category"]
            )
            created_data = create_model_with_translations(
                ChecklistSetting, checklist_data
            )
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_CHECKLIST_SETTING_SUCCESS),
                data=ChecklistSettingOutputSchema.from_queryset(created_data),
            )
        except Exception:
            return BaseResponse(
                status_code=400,
                success=False,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.put("/{id}", response=ChecklistSettingOutputSchema, auth=CustomJWTAuth())
    @path_permission("update", path_override="/checklist-setting")
    def update(self, request, id: int, data: ChecklistSettingInputSchema):
        """
        Update checklist setting

        Parameters:
        - id: ID of the checklist setting

        Request body:
        - item_name: Item name of the checklist setting
        - category: Category of the checklist setting
        """
        # W0-14c — 문지기는 **try 밖**이다. 이 핸들러의 except 가 모든 예외를 삼켜
        # HTTP 200 + 본문 404 로 바꾸기 때문이다 (W0-18 대상).
        assert_scoped(ChecklistSetting, id, request.user)
        try:
            checklist_setting = ChecklistSetting.objects.get(id=id)
            checklist_data = data.dict()
            checklist_data["category"] = ChecklistSettingCategory.objects.get(
                id=checklist_data["category"]
            )
            updated_data = update_model_with_translations(
                checklist_setting, checklist_data
            )
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_CHECKLIST_SETTING_SUCCESS),
                data=ChecklistSettingOutputSchema.from_queryset(updated_data),
            )
        except Exception:
            return BaseResponse(
                status_code=400,
                success=False,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.delete(
        "/delete/{ids}", response=ChecklistSettingOutputSchema, auth=CustomJWTAuth()
    )
    @path_permission("delete", path_override="/checklist-setting")
    def delete(self, request, ids: str):
        """
        Delete checklist setting

        Parameters:
        - ids: Comma-separated IDs of the checklist settings to delete
        """
        # W0-14c — 문지기는 try 밖이다 (위 update 주석 참조).
        assert_scoped(ChecklistSetting, ids, request.user)
        try:

            ids = ids.split(",")
            for item in ids:
                checklist_setting = ChecklistSetting.objects.get(id=item)
                checklist_setting.delete()
            return BaseResponse(
                status_code=200,
                success=True,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
            )
        except Exception:
            return BaseResponse(
                status_code=400,
                success=False,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                data=None,
            )

    @route.put("/{id}/activate", response=ChecklistSettingOutputSchema, auth=CustomJWTAuth())
    @path_permission("update", path_override="/checklist-setting")
    def activate(self, request, id: int):
        """
        Activate checklist setting
        """
        try:
            checklist_setting = ChecklistSetting.objects.get(id=id)
            checklist_setting.is_active = not checklist_setting.is_active
            checklist_setting.save()
            message_key = (
                MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS
                if checklist_setting.is_active
                else MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS
            )
            return BaseResponse(
                status_code=200,
                success=True,
                message=MESSAGE_ENUM.get(message_key)
            )
        except Exception:
            return BaseResponse(
                status_code=400,
                success=False,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UNEXPECTED_ERROR)
            )

@api_controller("/categories", tags=["Checklist Setting Category"])
class ChecklistSettingCategoryController:
    """
    Checklist Setting Category Controller
    """

    @route.get(
        "/",
        response=List[ChecklistSettingCategoryOutputSchema],
    )
    def get_categories(self, request):
        """
        Get all checklist setting categories
        Response body:
        - id: ID of the checklist setting category
        - name: Name of the checklist setting category
        - code: Code of the checklist setting category
        """
        categories = ChecklistSettingCategory.objects.all().order_by("id")

        return BaseResponse(
            status_code=200,
            success=True,
            message=MESSAGE_ENUM.get(
                MESSAGE_ENUM.GET_LIST_CHECKLIST_SETTING_CATEGORY_SUCCESS
            ),
            data=ChecklistSettingCategoryOutputSchema.from_queryset(
                categories, many=True
            ),
        )

    @route.post(
        "/",
        response=ChecklistSettingCategoryOutputSchema,
        auth=CustomJWTAuth(),
    )
    def create_category(self, request, data: ChecklistSettingCategoryInputSchema):
        """
        Create checklist setting category
        Request body:
        - name: Name of the checklist setting category
        - code: Code of the checklist setting category
        """
        try:
            category = ChecklistSettingCategory.objects.create(
                name=data.name, code=data.code
            )
            return BaseResponse(
                status_code=200,
                success=True,
                message=MESSAGE_ENUM.get(
                    MESSAGE_ENUM.CREATE_CHECKLIST_SETTING_CATEGORY_SUCCESS
                ),
                data=ChecklistSettingCategoryOutputSchema.from_queryset(category),
            )
        except Exception:
            return BaseResponse(
                status_code=400,
                success=False,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.delete(
        "/{id}",
        response=ChecklistSettingCategoryOutputSchema,
        auth=CustomJWTAuth(),
    )
    def delete_category(self, request, id: int):
        """
        Delete checklist setting category
        Parameters:
        - id: ID of the checklist setting category
        """
        try:
            category = ChecklistSettingCategory.objects.get(id=id)
            category.delete()
            return BaseResponse(
                status_code=200,
                success=True,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                data=ChecklistSettingCategoryOutputSchema.from_queryset(category),
            )
        except Exception:
            return BaseResponse(
                status_code=400,
                success=False,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )
