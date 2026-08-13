from typing import List, Dict, Any, Optional
import logging
from core.user.models import UserGroup
from devices.models import Device
from django.db.models import Q

logger = logging.getLogger(__name__)

class GroupService:
    @staticmethod
    def get_all_groups_with_drones() -> Dict[str, Any]:
        """
        Lấy tất cả groups và danh sách drones thuộc mỗi group.
        
        Returns:
            Dict[str, Any]: Dictionary chứa danh sách groups và drones
        """
        try:
            # Lấy tất cả groups
            groups = UserGroup._base_manager.all().order_by('name')
            
            result = {
                "groups": []
            }
            
            for group in groups:
                # Lấy tất cả devices thuộc group này
                # Vì Device không có quan hệ trực tiếp với UserGroup,
                # chúng ta sẽ lấy tất cả devices và filter theo created_by
                devices = Device._base_manager.filter(
                    Q(group=group)
                ).select_related(
                    'status', 'main_type', 'terminal'
                ).order_by('name')
                # Format device data
                device_list = []
                for device in devices:
                    device_data = {
                        "id": device.id,
                        "name": device.name,
                        "serial_number": device.serial_number,
                        "unit_id": device.unit_id,
                        "status": {
                            "id": device.status.id if device.status else None,
                            "name": device.status.name if device.status else None,
                            "code": device.status.code if device.status else None
                        } if device.status else None,
                        "active": device.active,
                        "main_type": {
                            "id": device.main_type.id if device.main_type else None,
                            "name": device.main_type.name if device.main_type else None
                        } if device.main_type else None,
                        "sub_type": device.sub_type,
                        "terminal": {
                            "id": device.terminal.id if device.terminal else None,
                            "name": device.terminal.name if device.terminal else None
                        } if device.terminal else None,
                        "color": device.color,
                        "approve_flight_now": device.approve_flight_now,
                        "on_approve_flight": device.on_approve_flight,
                        "created_on": device.created_on.isoformat() if device.created_on else None,
                        "modified_on": device.modified_on.isoformat() if device.modified_on else None
                    }
                    device_list.append(device_data)
                
                # Format group data
                group_data = {
                    "id": group.id,
                    "name": group.name,
                    "drones": device_list,
                    "drone_count": len(device_list)
                }
                result["groups"].append(group_data)
            
            return result
                
        except Exception as e:
            logger.error(f"Error getting groups with drones: {str(e)}")
            return {
                "groups": []
            }
    
    @staticmethod
    def get_group_drones_by_group_id(group_id: int) -> Dict[str, Any]:
        """
        Lấy danh sách drones của một group cụ thể.
        
        Args:
            group_id (int): ID của group
            
        Returns:
            Dict[str, Any]: Dictionary chứa thông tin group và danh sách drones
        """
        try:
            # Lấy group
            group = UserGroup.objects.get(id=group_id)
            
            # Lấy devices thuộc group này
            devices = Device.objects.filter(
                Q(created_by__userprofilelink__group=group) |
                Q(created_by__isnull=True)
            ).select_related(
                'status', 'main_type', 'terminal'
            ).order_by('name')
            
            # Format device data
            device_list = []
            for device in devices:
                device_data = {
                    "id": device.id,
                    "name": device.name,
                    "serial_number": device.serial_number,
                    "unit_id": device.unit_id,
                    "status": {
                        "id": device.status.id if device.status else None,
                        "name": device.status.name if device.status else None,
                        "code": device.status.code if device.status else None
                    } if device.status else None,
                    "active": device.active,
                    "main_type": {
                        "id": device.main_type.id if device.main_type else None,
                        "name": device.main_type.name if device.main_type else None
                    } if device.main_type else None,
                    "sub_type": device.sub_type,
                    "terminal": {
                        "id": device.terminal.id if device.terminal else None,
                        "name": device.terminal.name if device.terminal else None
                    } if device.terminal else None,
                    "color": device.color,
                    "approve_flight_now": device.approve_flight_now,
                    "on_approve_flight": device.on_approve_flight,
                    "created_on": device.created_on.isoformat() if device.created_on else None,
                    "modified_on": device.modified_on.isoformat() if device.modified_on else None
                }
                device_list.append(device_data)
            
            return {
                "group": {
                    "id": group.id,
                    "name": group.name
                },
                "drones": device_list,
                "drone_count": len(device_list)
            }
                
        except UserGroup.DoesNotExist:
            logger.error(f"Group with id {group_id} not found")
            return {
                "group": None,
                "drones": [],
                "drone_count": 0
            }
        except Exception as e:
            logger.error(f"Error getting group drones: {str(e)}")
            return {
                "group": None,
                "drones": [],
                "drone_count": 0
            }
