from celery import shared_task
from django.conf import settings
import django
from django.db import connection, transaction
from django.utils import timezone
from datetime import timedelta

# Ensure Django is properly set up
if not settings.configured:
    django.setup()

from operation_settings.models import OperationSettings
from core.user.models import CoreUser, UserGroup

@shared_task
def duplicate_default_operation_settings(user_group_id: int, modified_by_id: int, created_by_id: int):
    """
    Task to duplicate all default operation settings (created_by=null) 
    and assign them to a specific user group
    """
    try:
        with transaction.atomic():
            # Get the user group
            user_group = UserGroup.objects.get(id=user_group_id)
            
            # Get all default operation settings (created_by=null)
            default_settings = OperationSettings._base_manager.filter(created_by__isnull=True)
            
            duplicated_count = 0
            skipped_count = 0
            
            for default_setting in default_settings:
                # Check if this setting already exists for this group
                # We need to check if ANY record with the same menu, tab, name, group exists in this user's group
                existing_setting = OperationSettings.objects.filter(
                    menu_id=default_setting.menu_id,
                    tab_id=default_setting.tab_id,
                    name=default_setting.name,
                    groups=user_group
                ).first()
                
                if not existing_setting:
                    # Create a duplicate for this group
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
                        created_by_id=created_by_id,
                        modified_by_id=modified_by_id,
                    )
                    
                    # Add the group to the new setting
                    new_setting.groups.add(user_group)
                    duplicated_count += 1
                else:
                    skipped_count += 1
            
            return f"Successfully duplicated {duplicated_count} operation settings for group {user_group.name}. Skipped {skipped_count} existing settings."
        
    except UserGroup.DoesNotExist:
        return f"User group with ID {user_group_id} not found"
    except Exception as e:
        return f"Error duplicating operation settings: {str(e)}"

@shared_task
def smart_duplicate_default_operation_settings(user_group_id: int, modified_by_id: int, created_by_id: int):
    """
    Smart task to duplicate default operation settings with conflict detection
    This task checks for bulk operations and avoids conflicts with init_operation_settings
    """
    try:
        with transaction.atomic():
            # Get the user group
            user_group = UserGroup.objects.get(id=user_group_id)
            
            # Check if there are recent bulk operations (like init_operation_settings)
            recent_updates = OperationSettings.objects.filter(
                modified_on__gte=timezone.now() - timedelta(minutes=10)
            ).count()
            
            # If there are many recent updates, this might be a bulk operation
            # Skip duplication to avoid conflicts
            if recent_updates > 20:  # Threshold for bulk operations
                return f"Skipped duplication for group {user_group.name} due to recent bulk operations ({recent_updates} updates in last 10 minutes)"
            
            # Get all default operation settings (created_by=null)
            default_settings = OperationSettings._base_manager.filter(created_by__isnull=True)
            
            duplicated_count = 0
            skipped_count = 0
            
            # Lấy danh sách các cặp (menu_id, tab_id, name) đã tồn tại cho group này
            from django.db.models import Q
            existing_combinations = set()
            
            existing_settings = OperationSettings.objects.filter(groups=user_group).values_list(
                'menu_id', 'tab_id', 'name'
            )
            
            for menu_id, tab_id, name in existing_settings:
                # Tạo key duy nhất cho mỗi cặp (menu_id, tab_id, name)
                key = f"{menu_id}:{tab_id}:{name}"
                existing_combinations.add(key)
            
            for default_setting in default_settings:
                # Tạo key cho default setting này
                key = f"{default_setting.menu_id}:{default_setting.tab_id}:{default_setting.name}"
                
                # Kiểm tra xem key này đã tồn tại trong danh sách chưa
                if key in existing_combinations:
                    skipped_count += 1
                    continue
                
                # Double-check bằng query trực tiếp để đảm bảo không có trùng lặp
                existing = OperationSettings.objects.filter(
                    Q(menu_id=default_setting.menu_id) &
                    Q(tab_id=default_setting.tab_id) &
                    Q(name=default_setting.name) &
                    Q(groups=user_group)
                ).exists()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Create a duplicate for this group
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
                    created_by_id=created_by_id,
                    modified_by_id=modified_by_id,
                )
                
                # Add the group to the new setting
                new_setting.groups.add(user_group)
                
                # Thêm key mới vào danh sách đã tồn tại để tránh duplicate trong cùng một lần chạy
                existing_combinations.add(key)
                
                duplicated_count += 1
            
            return f"Successfully duplicated {duplicated_count} operation settings for group {user_group.name}. Skipped {skipped_count} existing settings."
        
    except UserGroup.DoesNotExist:
        return f"User group with ID {user_group_id} not found"
    except Exception as e:
        return f"Error duplicating operation settings: {str(e)}" 