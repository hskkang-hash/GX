from typing import Tuple, Optional, List
from django.db import transaction
from django.contrib.auth.models import AnonymousUser
from django.db.models import Q, Subquery, OuterRef
from ninja.errors import ValidationError
from operation_settings.constants.api_documentation import DELIVERY_APIS
from operation_settings.models import OperationSettings
from operation_settings.schemas.schemas_djantic_in import (
    OperationSettingsCreateSchema, 
    OperationSettingsUpdateSchema
)
from core.common.base_response import BaseResponse
from core.user.models import CoreUser, UserGroup
from core.middleware.refresh_token import get_current_request
from safedelete.models import HARD_DELETE
from core.menu.models import Tab
from common.constant import MESSAGE_ENUM

class OperationSettingsService:
    """Service class for OperationSettings business logic"""

    @staticmethod
    def _duplicate_default_settings_for_group(user_group, user_id):
        """
        Helper method to duplicate default settings for a user group
        Logic: Duplicate tất cả default settings chưa có trong group của user
        Args:
            user_group: UserGroup instance
            user_id: ID of the user performing the operation
        """
        # Lấy tất cả default settings (created_by=null)
        default_settings = OperationSettings._base_manager.filter(created_by__isnull=True)
        
        # Đếm số default settings chưa có bản sao cho group này
        unduplicated_count = 0
        for default_setting in default_settings:
            # Kiểm tra xem đã có record với cùng menu, tab, name và group chưa
            has_duplicate = OperationSettings.objects.filter(
                menu_id=default_setting.menu_id,
                tab_id=default_setting.tab_id,
                name=default_setting.name,
                group=user_group
            ).exists()
            
            if not has_duplicate:
                unduplicated_count += 1
        
        # Nếu có default settings chưa được duplicate, duplicate trực tiếp (không chạy task)
        if unduplicated_count > 0:
            # Duplicate trực tiếp trong service thay vì chạy Celery task
            for default_setting in default_settings:
                # Kiểm tra xem đã có record với cùng menu, tab, name và group chưa
                has_duplicate = OperationSettings.objects.filter(
                    menu_id=default_setting.menu_id,
                    tab_id=default_setting.tab_id,
                    name=default_setting.name,
                    group=user_group
                ).exists()
                
                if not has_duplicate:
                    # Tạo record duplicate mới
                    new_setting = OperationSettings.objects.create(
                        menu_id=default_setting.menu_id,
                        tab_id=default_setting.tab_id,
                        name=default_setting.name,
                        is_active=default_setting.is_active,
                        api_url=default_setting.api_url,
                        http_method=default_setting.http_method,
                        api_params=default_setting.api_params,
                        expected_response=default_setting.expected_response,
                        timeout_seconds=default_setting.timeout_seconds,
                        retry_count=default_setting.retry_count,
                        description=default_setting.description,
                        notes=default_setting.notes,
                        last_tested_on=default_setting.last_tested_on,
                        last_test_status=default_setting.last_test_status,
                        send_data=default_setting.send_data,
                        receive_data=default_setting.receive_data,
                        created_by_id=user_id,
                        modified_by_id=user_id,
                        group=user_group
                    )

        
        return unduplicated_count
    """Service class for OperationSettings business logic"""

    @staticmethod
    def get_all_settings() -> List[OperationSettings]:
        """
        Get all operation settings based on BaseModelWithGroup logic
        - Superuser can see all settings
        - Regular users see their group's settings + default settings (created_by=null)
        - Priority: group-specific settings > default settings for same menu/tab/name/group combination
        """
        request = get_current_request()
        user = request.user
        profile = getattr(user, 'userprofilelink', None)
        user_group = profile.group if profile else None

        # Check if user is superuser: is_superuser=True OR has role.id=1
        is_superuser = user.is_superuser or any(role.code == 'superuser' for role in user.roles.all())

        if user_group and OperationSettings.objects.filter(group=user_group).exists() and not is_superuser:
            queryset = OperationSettings.objects.filter(
                Q(group=user_group)
            )
        else:
            queryset = OperationSettings.objects.all()

        # Annotate with group_name from the first group
        queryset = queryset.annotate(
            group_name=Subquery(
                UserGroup.objects.filter(
                    operationsettings=OuterRef('group')
                ).values('name')[:1]
            ),
            tab_name=Subquery(
                Tab.objects.filter(
                    id=OuterRef('tab_id')
                ).values('name')[:1]
            )
        )

        return queryset.select_related('menu', 'tab','group').order_by('group_name')

    @staticmethod
    def get_settings_by_menu(menu_id: int) -> List[OperationSettings]:
        """Get operation settings by menu with group filtering"""
        base_queryset = OperationSettingsService.get_all_settings()
        return base_queryset.filter(menu_id=menu_id)

    @staticmethod
    def get_settings_by_tab(tab_id: int) -> List[OperationSettings]:
        """Get operation settings by tab with group filtering"""
        base_queryset = OperationSettingsService.get_all_settings()
        return base_queryset.filter(tab_id=tab_id)

    @staticmethod
    def get_settings_by_group(group_id: int) -> List[OperationSettings]:
        """Get operation settings by group with group filtering"""
        base_queryset = OperationSettingsService.get_all_settings()
        return base_queryset.filter(group_id=group_id)

    @staticmethod
    def get_settings_by_menu_and_tab(menu_id: int, tab_id: Optional[int] = None) -> List[OperationSettings]:
        """Get operation settings by menu and tab with group filtering"""
        base_queryset = OperationSettingsService.get_all_settings()
        queryset = base_queryset.filter(menu_id=menu_id)
        if tab_id:
            queryset = queryset.filter(tab_id=tab_id)
        else:
            queryset = queryset.filter(tab_id__isnull=True)
        return queryset

    @staticmethod
    def get_setting_by_id(setting_id: int) -> Optional[OperationSettings]:
        """Get single operation setting by ID with group filtering"""
        try:
            base_queryset = OperationSettingsService.get_all_settings()
            return base_queryset.filter(id=setting_id).first()
        except OperationSettings.DoesNotExist:
            return None

    @staticmethod
    @transaction.atomic
    def create_operation_setting(
        data: OperationSettingsCreateSchema,
        user: CoreUser
    ) -> Tuple[bool, OperationSettings]:
        """Create new operation setting"""
        try:
            # Validate required fields
            if not data.menu_id:
                raise ValidationError("menu_id is required")
            if not data.name:
                raise ValidationError("name is required")
            if not data.api_url:
                raise ValidationError("api_url is required")

            # Check if combination already exists
            existing = OperationSettings.objects.filter(
                menu_id=data.menu_id,
                tab_id=data.tab_id,
                name=data.name,
            ).first()
            
            if existing:
                raise ValidationError(f"Operation setting for menu {data.menu_id} - tab {data.tab_id} - {data.name} already exists")

            # Create new setting
            setting = OperationSettings.objects.create(
                menu_id=data.menu_id,
                tab_id=data.tab_id,
                name=data.name,
                is_active=data.is_active,
                api_url=str(data.api_url),
                http_method=data.http_method,
                api_params=data.api_params,
                expected_response=data.expected_response,
                timeout_seconds=data.timeout_seconds,
                retry_count=data.retry_count,
                description=data.description,
                notes=data.notes,
            )

            return True, setting

        except Exception as e:
            raise ValidationError(f"Error creating operation setting: {str(e)}")



    @staticmethod
    @transaction.atomic
    def update_operation_setting(
        setting_id: int,
        data: OperationSettingsUpdateSchema,
        user: CoreUser
    ) -> Tuple[bool, Optional[OperationSettings]]:
        """
        Update existing operation setting with group duplication logic
        When a user updates a setting:
        1. If user is not superuser, check if the record has a group
        2. If the record has the user's group, update directly
        3. If not, duplicate the record and assign the user's group to it
        """
        try:
            # Get the original setting (bypass group filtering to get the actual record)
            original_setting = OperationSettings._base_manager.get(id=setting_id)
            
            # Get user's group
            profile = getattr(user, 'userprofilelink', None)
            if data.group_id:
                user_group = UserGroup.objects.get(id=data.group_id)
            else:
                user_group = profile.group if profile else None
            
            # Check if user is superuser: is_superuser=True OR has role.id=1
            is_superuser = user.is_superuser or any(role.code == 'superuser' for role in user.roles.all())
            
            # Logic: Check if the record belongs to user's group or needs to be duplicated
            if not is_superuser and user_group:
                # Check if the record has any groups
                has_groups = original_setting.group is not None
                
                # Check if the record belongs to user's group
                belongs_to_user_group = user_group == original_setting.group
                
                if has_groups and belongs_to_user_group:
                    # If record already belongs to user's group, update directly
                    setting = original_setting
                else:
                    # Kiểm tra xem đã có record nào với cùng menu, tab, name và group chưa
                    from django.db.models import Q
                    
                    existing_setting = OperationSettings.objects.filter(
                        Q(menu_id=original_setting.menu_id) &
                        Q(tab_id=original_setting.tab_id) &
                        Q(name=original_setting.name) &
                        Q(group=user_group)
                    ).distinct().first()
                    
                    if existing_setting:
                        # Nếu đã có record với group của user, update record đó
                        setting = existing_setting
                    else:
                        # Nếu chưa có, tạo record duplicate mới
                        setting = OperationSettings.objects.create(
                            menu_id=original_setting.menu_id,
                            tab_id=original_setting.tab_id,
                            name=original_setting.name,
                            is_active=original_setting.is_active,
                            api_url=original_setting.api_url,
                            http_method=original_setting.http_method,
                            api_params=original_setting.api_params,
                            expected_response=original_setting.expected_response,
                            timeout_seconds=original_setting.timeout_seconds,
                            retry_count=original_setting.retry_count,
                            description=original_setting.description,
                            notes=original_setting.notes,
                            last_tested_on=original_setting.last_tested_on,
                            last_test_status=original_setting.last_test_status,
                            send_data=original_setting.send_data,
                            receive_data=original_setting.receive_data,
                            created_by=user,
                            modified_by=user,
                        )
                
                # Sau khi xử lý record chính, duplicate tất cả default settings còn lại cho group của user
                # Đảm bảo group của user có đầy đủ tất cả default settings
                OperationSettingsService._duplicate_default_settings_for_group(
                    user_group, 
                    user.id
                )
            else:
                # If user is superuser or has no group, update directly
                setting = original_setting
            
            # Update the record with new data
            for key, value in data.model_dump().items():
                if value is not None:
                    setattr(setting, key, value)
            setting.modified_by = user
            setting.save()
            
            # KHÔNG duplicate default settings ở đây nữa vì đã được xử lý ở trên
            # Logic duplicate chỉ chạy một lần khi cần thiết
            
            return True, setting 

        except OperationSettings.DoesNotExist:
            return False, None
        except Exception as e:
            raise ValidationError(f"Error updating operation setting: {str(e)}")

    @staticmethod
    @transaction.atomic
    def delete_operation_setting(setting_id: int) -> Tuple[bool, str]:
        """Delete operation setting"""
        try:
            # Use group-filtered query to ensure user can only delete settings they can see
            base_queryset = OperationSettingsService.get_all_settings()
            setting = base_queryset.get(id=setting_id)
            setting.delete(force_policy=HARD_DELETE)
            return True, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
            
        except OperationSettings.DoesNotExist:
            return False, "Operation setting not found"
        except Exception as e:
            return False, f"Error deleting operation setting: {str(e)}"

    @staticmethod
    def get_data(queryset) -> List[dict]:
        """Prepare data for response"""
        data = []
        for setting in queryset:
            data.append({
                'id': setting.id,
                'name': setting.name,
                'is_active': setting.is_active,
                'api_url': setting.api_url,
                'http_method': setting.http_method,
                'api_params': setting.api_params,
                'expected_response': setting.expected_response,
                'timeout_seconds': setting.timeout_seconds,
                'retry_count': setting.retry_count,
                'description': setting.description,
                'notes': setting.notes,
                'last_tested_on': setting.last_tested_on,
                'last_test_status': setting.last_test_status,
                'created_on': setting.created_on,
                'modified_on': setting.modified_on,
                'menu_id': setting.menu_id,
                'menu_name': setting.menu.menu_name,
                'menu_path': setting.menu.path,
                'tab_id': setting.tab_id,
                'tab_name': setting.tab.name if setting.tab else None,
                'tab_path': setting.tab.path if setting.tab else None,
                'group_name': setting.group.name if setting.group else None,
                'group_description': setting.group.description if setting.group else None,
                # Backward compatibility
                'menu_type': setting.menu_type,
                'step': setting.step,
                # Group information
                'user_groups': [group.name for group in setting.group.all()],
                'is_default': setting.created_by is None,
                'select':True if setting.api_url in DELIVERY_APIS else False
            })
        return data 