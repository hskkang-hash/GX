from typing import List
from core.common.base_response import BaseResponse
from core.api.v1.auth import CustomJWTAuth
from operation_settings.schemas.schemas_djantic_out import OperationSettingsOutSchema
from operation_settings.services.menu_integration_service import MenuIntegrationService
from common.constant import MESSAGE_ENUM, get_message
from ninja_extra import api_controller, route

@api_controller('/menu-integration', tags=['Menu Integration'])
class MenuIntegrationView:
    """API Views for Menu Integration functionality"""

    @route.get("/menus", auth=CustomJWTAuth())
    def get_available_menus(self, request):
        """Get all available menus for operation settings"""
        try:
            menus = MenuIntegrationService.get_available_menus()
            
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=menus
            )
        except Exception as e:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.INTERNAL_SERVER_ERROR),
                data=None
            )

    @route.get("/tabs", auth=CustomJWTAuth())
    def get_available_tabs(self, request, menu_id: int = None):
        """Get all available tabs for operation settings"""
        try:
            tabs = MenuIntegrationService.get_available_tabs(menu_id)
            
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=tabs
            )
        except Exception as e:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.INTERNAL_SERVER_ERROR),
                data=None
            )

    @route.get("/groups", auth=CustomJWTAuth())
    def get_available_groups(self, request):
        """Get all available user groups for operation settings"""
        try:
            groups = MenuIntegrationService.get_available_groups()
            
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=groups
            )
        except Exception as e:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.INTERNAL_SERVER_ERROR),
                data=None
            )

    @route.get("/structure", auth=CustomJWTAuth())
    def get_menu_tab_structure(self, request):
        """Get hierarchical menu/tab structure with operation settings info"""
        try:
            structure = MenuIntegrationService.get_menu_tab_structure()
            
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=structure
            )
        except Exception as e:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.INTERNAL_SERVER_ERROR),
                data=None
            )

    @route.post("/create-defaults/{menu_id}", auth=CustomJWTAuth())
    def create_default_settings(self, request, menu_id: int, include_tabs: bool = True, group_id: int = None):
        """Create default operation settings for a menu and its tabs"""
        try:
            success, created_settings = MenuIntegrationService.create_default_settings_for_menu(
                menu_id, request.auth, include_tabs, group_id
            )
            
            if success:
                return BaseResponse(
                    status_code=200,
                    message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_CREATE_SUCCESS),
                    data={
                        'created_count': len(created_settings),
                        'settings': OperationSettingsOutSchema.from_queryset(created_settings, many=True)
                    }
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_CREATE_ERROR),
                    data=None
                )
        except Exception as e:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.OPERATION_SETTINGS_CREATE_ERROR),
                data=None
            )

    @route.get("/validate/{menu_id}", auth=CustomJWTAuth())
    def validate_menu_tab_group(self, request, menu_id: int, tab_id: int = None, group_id: int = None):
        """Validate menu/tab/group combination"""
        try:
            is_valid, message = MenuIntegrationService.validate_menu_tab_group_combination(menu_id, tab_id, group_id)
            
            return BaseResponse(
                status_code=200 if is_valid else 400,
                message=message,
                data={'is_valid': is_valid, 'menu_id': menu_id, 'tab_id': tab_id, 'group_id': group_id}
            )
        except Exception as e:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.INTERNAL_SERVER_ERROR),
                data=None
            )

    @route.get("/summary", auth=CustomJWTAuth())
    def get_operation_settings_summary(self, request):
        """Get summary statistics of operation settings"""
        try:
            summary = MenuIntegrationService.get_operation_settings_summary()
            
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=summary
            )
        except Exception as e:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.INTERNAL_SERVER_ERROR),
                data=None
            ) 