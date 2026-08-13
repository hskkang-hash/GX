from typing import List
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import ValidationError
from core.common.base_response import BaseResponse
from common.pagination import OptimizedPaginator
from core.api.v1.auth import CustomJWTAuth
from ninja_extra import api_controller, route
from operation_settings.models import OperationSettings
from operation_settings.schemas.schemas_djantic_in import (
    OperationSettingsCreateSchema,
    OperationSettingsUpdateSchema
)
from operation_settings.schemas.schemas_djantic_out import OperationSettingsOutSchema
from operation_settings.services.operation_settings_service import OperationSettingsService
from operation_settings.services.api_documentation_service import ApiDocumentationService
from common.constant import *
from common.constant import MESSAGE_ENUM, get_message
from core.common.search.dynamic_search import apply_dynamic_filters

@api_controller('/operation-settings', tags=['Operation Settings']) 
class OperationSettingsView:
    """API Views for Operation Settings management"""
 
    @route.get("/supported-apis", auth=CustomJWTAuth())
    def get_supported_apis(self, request):
        """Get list of supported APIs for external systems integration"""
        try:
            supported_apis = ApiDocumentationService.get_supported_apis()
            
            return BaseResponse(
                status_code=200,
                message="Supported APIs retrieved successfully",
                data=supported_apis
            )
            
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"Error retrieving supported APIs: {str(e)}",
                data=None
            )

    @route.get("/supported-apis/{api_name}", auth=CustomJWTAuth())
    def get_api_by_name(self, request, api_name: str):
        """Get specific API documentation by name"""
        try:
            api_doc = ApiDocumentationService.get_api_by_name(api_name)
            
            if not api_doc:
                return BaseResponse(
                    status_code=404,
                    message=f"API documentation for '{api_name}' not found",
                    data=None
                )
            
            return BaseResponse(
                status_code=200,
                message=f"API documentation for '{api_name}' retrieved successfully",
                data=api_doc
            )
            
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"Error retrieving API documentation: {str(e)}",
                data=None
            )

    @route.get("/supported-apis/method/{method}", auth=CustomJWTAuth())
    def get_apis_by_method(self, request, method: str):
        """Get APIs filtered by HTTP method"""
        try:
            apis = ApiDocumentationService.get_apis_by_method(method)
            
            return BaseResponse(
                status_code=200,
                message=f"APIs with method '{method.upper()}' retrieved successfully",
                data={"apis": apis, "count": len(apis)}
            )
            
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"Error retrieving APIs by method: {str(e)}",
                data=None
            )

    @route.get("/supported-apis/endpoints", auth=CustomJWTAuth())
    def get_api_endpoints_list(self, request):
        """Get list of all API endpoints"""
        try:
            endpoints = ApiDocumentationService.get_api_endpoints_list()
            
            return BaseResponse(
                status_code=200,
                message="API endpoints list retrieved successfully",
                data={"endpoints": endpoints, "count": len(endpoints)}
            )
            
        except Exception as e:
            return BaseResponse(
                status_code=500,
                message=f"Error retrieving API endpoints: {str(e)}",
                data=None
            )

    @route.get("/", auth=CustomJWTAuth())
    def list_operation_settings(self, request):
        """Get all operation settings with pagination"""
        try:
            page_size = int(request.GET.get('page_size', 10))
            current_page = int(request.GET.get('current_page', 1))
            queryset = OperationSettingsService.get_all_settings()
            queryset = apply_dynamic_filters(queryset, request, [], request.GET.get('sort_obj', None))
            paginator = OptimizedPaginator(queryset, page_size)
            pages = paginator.page(current_page)
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_LIST_SUCCESS),
                data=OperationSettingsOutSchema.from_queryset(pages.object_list, many=True, auto_resolve_fields=False),
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page,
            )
        except Exception as e:
            print(e)
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_LIST_ERROR),
                data=None
            )

    @route.get("/{setting_id}", auth=CustomJWTAuth())
    def get_operation_setting(self, request, setting_id: int):
        """Get single operation setting by ID"""
        try:
            setting = OperationSettingsService.get_setting_by_id(setting_id)
            
            if not setting:
                return BaseResponse(
                    status_code=404,
                    message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_NOT_FOUND),
                    data=None
                )
            
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_GET_SUCCESS),
                data=OperationSettingsOutSchema.from_queryset(setting)
            )
        except Exception as e:
            print(e)
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_GET_ERROR),
                data=None
            )

    @route.get("/menu/{menu_id}", auth=CustomJWTAuth())
    def get_settings_by_menu(self, request, menu_id: int):
        """Get operation settings by menu"""
        try:
            queryset = OperationSettingsService.get_settings_by_menu(menu_id)
            
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_LIST_SUCCESS),
                data=OperationSettingsOutSchema.from_queryset(queryset, many=True)
            )
        except Exception as e:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_LIST_ERROR),
                data=None
            )

    @route.get("/tab/{tab_id}", auth=CustomJWTAuth())
    def get_settings_by_tab(self, request, tab_id: int):
        """Get operation settings by tab"""
        try:
            queryset = OperationSettingsService.get_settings_by_tab(tab_id)
            
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_LIST_SUCCESS),
                data=OperationSettingsOutSchema.from_queryset(queryset, many=True)
            )
        except Exception as e:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_LIST_ERROR),
                data=None
            )

    @route.get("/group/{group_id}", auth=CustomJWTAuth())
    def get_settings_by_group(self, request, group_id: int):
        """Get operation settings by group"""
        try:
            queryset = OperationSettingsService.get_settings_by_group(group_id)
            
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_LIST_SUCCESS),
                data=OperationSettingsOutSchema.from_queryset(queryset, many=True)
            )
        except Exception as e:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_LIST_ERROR),
                data=None
            )

    @route.get("/menu/{menu_id}/tab/{tab_id}", auth=CustomJWTAuth())
    def get_settings_by_menu_and_tab(self, request, menu_id: int, tab_id: int):
        """Get operation settings by menu and tab"""
        try:
            queryset = OperationSettingsService.get_settings_by_menu_and_tab(menu_id, tab_id)
            
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_LIST_SUCCESS),
                data=OperationSettingsOutSchema.from_queryset(queryset, many=True)
            )
        except Exception as e:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_LIST_ERROR),
                data=None
            )

    @route.post("", auth=CustomJWTAuth())
    def create_operation_setting(self, request, payload: OperationSettingsCreateSchema):
        """Create new operation setting"""
        try:
            success, setting = OperationSettingsService.create_operation_setting(
                payload, request.user
            )
            
            if success:
                return BaseResponse(
                    status_code=200,
                    message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_CREATE_SUCCESS),
                    data=OperationSettingsOutSchema.from_queryset(setting)
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_CREATE_ERROR),
                    data=None
                )
        
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                message={"success": False, "errors": str(e)},
                data=None
            )
        except Exception as e:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_CREATE_ERROR),
                data=None
            )

    @route.put("/{setting_id}", auth=CustomJWTAuth())
    def update_operation_setting(self, request, setting_id: int, payload: OperationSettingsUpdateSchema):
        """Update existing operation setting"""
        try:
            success, setting = OperationSettingsService.update_operation_setting(
                setting_id, payload, request.user
            )
            
            if success and setting:
                return BaseResponse(
                    status_code=200,
                    message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_UPDATE_SUCCESS),
                    data=OperationSettingsOutSchema.from_queryset(setting)
                )
            else:
                return BaseResponse(
                    status_code=404,
                    message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_NOT_FOUND),
                    data=None
                )
        
        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                message={"success": False, "errors": str(e)},
                data=None
            )
        except Exception as e:
            print(e)
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_UPDATE_ERROR),
                data=None
            )


    @route.delete("/{setting_id}", auth=CustomJWTAuth())
    def delete_operation_setting(self, request, setting_id: int):
        """Delete operation setting"""
        try:
            success, message = OperationSettingsService.delete_operation_setting(setting_id)
            
            if success:
                return BaseResponse(
                    status_code=200,
                    message=get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                    data=None
                )
            else:
                return BaseResponse(
                    status_code=404,
                    message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_NOT_FOUND),
                    data=None
                )
        except Exception as e:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                data=None
            ) 