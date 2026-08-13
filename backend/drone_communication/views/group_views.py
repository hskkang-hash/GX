import logging
from ninja_extra import api_controller, route
from ninja import Query
from typing import Optional
from core.common.base_response import BaseResponse
from drone_communication.services.group_service import GroupService
from common.constant import MESSAGE_ENUM

logger = logging.getLogger(__name__)

@api_controller('/group-management', 
                tags=['Group Management'])
class GroupAPI:
    @route.get('/groups-with-drones')
    def get_all_groups_with_drones(self):
        """
        Lấy tất cả groups và danh sách drones thuộc mỗi group cho GCS.
        
        Returns:
            BaseResponse: Danh sách groups với drones của mỗi group
        """
        try:
            result = GroupService.get_all_groups_with_drones()
            
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_DEVICE_SUCCESS),
                data=result
            )
        except Exception as e:
            logger.error(f"Error getting groups with drones: {str(e)}")
            return BaseResponse(
                status_code=500,
                message=f"Error getting groups with drones: {str(e)}",
                data={"groups": []}
            )
    
    @route.get('/group/{group_id}/drones')
    def get_group_drones(self, group_id: int):
        """
        Lấy danh sách drones của một group cụ thể.
        
        Args:
            group_id (int): ID của group
            
        Returns:
            BaseResponse: Danh sách drones của group
        """
        try:
            result = GroupService.get_group_drones_by_group_id(group_id)
            
            if result["group"] is None:
                return BaseResponse(
                    status_code=404,
                    message="Group not found",
                    data=result
                )
            
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_DEVICE_SUCCESS),
                data=result
            )
        except Exception as e:
            logger.error(f"Error getting group drones: {str(e)}")
            return BaseResponse(
                status_code=500,
                message=f"Error getting group drones: {str(e)}",
                data={"group": None, "drones": [], "drone_count": 0}
            )
