from typing import List, Dict, Any, Tuple, Optional
from django.db import transaction
from operation_settings.models import OperationSettings
from core.user.models import CoreUser, UserGroup
from ninja.errors import ValidationError
AVAILABLE_MENUS = [
    '/delivery-operation',
]

class MenuIntegrationService:
    """Service for integrating Operation Settings with Menu/Tab/Group system"""

    @staticmethod
    def get_available_menus() -> List[Dict[str, Any]]:
        """Get all available menus that can be used for operation settings"""
        try:
            # Import here to avoid circular imports
            from core.menu.models import Menu
            
            menus = Menu.objects.filter(path__in=AVAILABLE_MENUS,deleted__isnull=True).order_by('ordering', 'menu_name') 
            return [
                {
                    'id': menu.id,
                    'name': menu.menu_name,
                    'path': menu.path,
                    'parent_id': menu.parent_id,
                    'depth': menu.depth,
                    'has_settings': OperationSettings.objects.filter(menu=menu).exists()
                }
                for menu in menus
            ]
        except Exception as e:
            return []

    @staticmethod
    def get_available_tabs(menu_id: int = None) -> List[Dict[str, Any]]:
        """Get all available tabs that can be used for operation settings"""
        try:
            # Import here to avoid circular imports
            from core.menu.models import Tab
            
            queryset = Tab.objects.all()
            if menu_id:
                queryset = queryset.filter(parent_menu_id=menu_id)
            
            tabs = queryset.order_by('order', 'name')
            return [
                {
                    'id': tab.id,
                    'name': tab.name,
                    'path': tab.path,
                    'parent_menu_id': tab.parent_menu_id,
                    'parent_tab_id': tab.parent_tab_id,
                    'order': tab.order,
                    'has_settings': OperationSettings.objects.filter(tab=tab).exists()
                }
                for tab in tabs
            ]
        except Exception as e:
            return []

    @staticmethod
    def get_available_groups() -> List[Dict[str, Any]]:
        """Get all available user groups that can be used for operation settings"""
        try:
            groups = UserGroup.objects.all().order_by('name')
            return [
                {
                    'id': group.id,
                    'name': group.name,
                    'description': group.description,
                    'is_active': group.is_active,
                    'has_settings': OperationSettings.objects.filter(group=group).exists()
                }
                for group in groups
            ]
        except Exception as e:
            return []

    @staticmethod
    def get_menu_tab_structure() -> List[Dict[str, Any]]:
        """Get hierarchical menu/tab structure with operation settings info"""
        try:
            # Import here to avoid circular imports
            from core.menu.models import Menu, Tab
            
            menus = Menu.objects.filter(parent__isnull=True).order_by('ordering')
            result = []
            
            for menu in menus:
                menu_data = {
                    'id': menu.id,
                    'name': menu.menu_name,
                    'path': menu.path,
                    'type': 'menu',
                    'settings_count': OperationSettings.objects.filter(menu=menu).count(),
                    'tabs': [],
                    'children': []
                }
                
                # Get tabs for this menu
                tabs = Tab.objects.filter(parent_menu=menu).order_by('order')
                for tab in tabs:
                    tab_data = {
                        'id': tab.id,
                        'name': tab.name,
                        'path': tab.path,
                        'type': 'tab',
                        'settings_count': OperationSettings.objects.filter(tab=tab).count()
                    }
                    menu_data['tabs'].append(tab_data)
                
                # Get child menus recursively
                child_menus = Menu.objects.filter(parent=menu).order_by('ordering')
                for child_menu in child_menus:
                    child_data = MenuIntegrationService._get_menu_recursive(child_menu)
                    menu_data['children'].append(child_data)
                
                result.append(menu_data)
            
            return result
        except Exception as e:
            return []

    @staticmethod
    def _get_menu_recursive(menu) -> Dict[str, Any]:
        """Recursively get menu structure with tabs and children"""
        menu_data = {
            'id': menu.id,
            'name': menu.menu_name,
            'path': menu.path,
            'type': 'menu',
            'settings_count': OperationSettings.objects.filter(menu=menu).count(),
            'tabs': [],
            'children': []
        }
        
        # Get tabs for this menu
        from core.menu.models import Tab, Menu
        tabs = Tab.objects.filter(parent_menu=menu).order_by('order')
        for tab in tabs:
            tab_data = {
                'id': tab.id,
                'name': tab.name,
                'path': tab.path,
                'type': 'tab',
                'settings_count': OperationSettings.objects.filter(tab=tab).count()
            }
            menu_data['tabs'].append(tab_data)
        
        # Get child menus recursively
        child_menus = Menu.objects.filter(parent=menu).order_by('ordering')
        for child_menu in child_menus:
            child_data = MenuIntegrationService._get_menu_recursive(child_menu)
            menu_data['children'].append(child_data)
        
        return menu_data

    @staticmethod
    @transaction.atomic
    def create_default_settings_for_menu(
        menu_id: int, 
        user: CoreUser,
        include_tabs: bool = True,
        group_id: Optional[int] = None
    ) -> Tuple[bool, List[OperationSettings]]:
        """Create default operation settings for a menu and optionally its tabs"""
        try:
            from core.menu.models import Menu, Tab
            
            menu = Menu.objects.get(id=menu_id)
            created_settings = []
            
            # Get default group if not provided
            if not group_id:
                default_group = UserGroup.objects.filter(is_active=True).first()
                if not default_group:
                    raise ValidationError("No active user group found. Please create a user group first.")
                group_id = default_group.id
            
            # Create default setting for the menu itself
            if not OperationSettings.objects.filter(menu=menu, tab__isnull=True, group_id=group_id).exists():
                setting = OperationSettings.objects.create(
                    menu=menu,
                    tab=None,
                    group_id=group_id,
                    name=f"Default {menu.menu_name} API",
                    is_active=True,
                    api_url=f"https://api.example.com{menu.path}",
                    http_method="GET",
                    timeout_seconds=30,
                    retry_count=3,
                    description=f"Default API setting for {menu.menu_name}",
                )
                created_settings.append(setting)
            
            # Create settings for tabs if requested
            if include_tabs:
                tabs = Tab.objects.filter(parent_menu=menu)
                for tab in tabs:
                    if not OperationSettings.objects.filter(menu=menu, tab=tab, group_id=group_id).exists():
                        setting = OperationSettings.objects.create(
                            menu=menu,
                            tab=tab,
                            group_id=group_id,
                            name=f"{tab.name} API",
                            is_active=True,
                            api_url=f"https://api.example.com{tab.path}",
                            http_method="GET",
                            timeout_seconds=30,
                            retry_count=3,
                            description=f"Default API setting for {menu.menu_name} - {tab.name}",
                        )
                        created_settings.append(setting)
            
            return True, created_settings
            
        except Menu.DoesNotExist:
            raise ValidationError(f"Menu with id {menu_id} not found")
        except UserGroup.DoesNotExist:
            raise ValidationError(f"User group with id {group_id} not found")
        except Exception as e:
            raise ValidationError(f"Error creating default settings: {str(e)}")

    @staticmethod
    def validate_menu_tab_group_combination(
        menu_id: int, 
        tab_id: Optional[int] = None, 
        group_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """Validate that a menu/tab/group combination is valid"""
        try:
            from core.menu.models import Menu, Tab
            
            # Check if menu exists
            try:
                menu = Menu.objects.get(id=menu_id)
            except Menu.DoesNotExist:
                return False, f"Menu with id {menu_id} does not exist"
            
            # If tab_id is provided, check if it belongs to the menu
            if tab_id:
                try:
                    tab = Tab.objects.get(id=tab_id)
                    if tab.parent_menu_id != menu_id:
                        return False, f"Tab {tab_id} does not belong to menu {menu_id}"
                except Tab.DoesNotExist:
                    return False, f"Tab with id {tab_id} does not exist"
            
            # If group_id is provided, check if it exists and is active
            if group_id:
                try:
                    group = UserGroup.objects.get(id=group_id)
                    if not group.is_active:
                        return False, f"User group {group_id} is not active"
                except UserGroup.DoesNotExist:
                    return False, f"User group with id {group_id} does not exist"
            
            return True, "Valid menu/tab/group combination"
            
        except Exception as e:
            return False, f"Error validating combination: {str(e)}"

    @staticmethod
    def get_operation_settings_summary() -> Dict[str, Any]:
        """Get summary statistics of operation settings"""
        try:
            total_settings = OperationSettings.objects.count()
            active_settings = OperationSettings.objects.filter(is_active=True).count()
            inactive_settings = total_settings - active_settings
            
            # Group by HTTP methods
            method_stats = {}
            for method_choice in OperationSettings.HTTP_METHOD_CHOICES:
                method = method_choice[0]
                count = OperationSettings.objects.filter(http_method=method).count()
                method_stats[method] = count
            
            # Group by user groups
            group_stats = []
            groups = UserGroup.objects.all()
            for group in groups:
                count = OperationSettings.objects.filter(group=group).count()
                group_stats.append({
                    'group_id': group.id,
                    'group_name': group.name,
                    'settings_count': count
                })
            
            return {
                'total_settings': total_settings,
                'active_settings': active_settings,
                'inactive_settings': inactive_settings,
                'method_distribution': method_stats,
                'group_distribution': group_stats,
                'menus_with_settings': OperationSettings.objects.values('menu_id').distinct().count(),
                'tabs_with_settings': OperationSettings.objects.filter(tab__isnull=False).values('tab_id').distinct().count(),
                'groups_with_settings': OperationSettings.objects.values('group_id').distinct().count()
            }
        except Exception as e:
            return {
                'error': f"Error getting summary: {str(e)}"
            } 