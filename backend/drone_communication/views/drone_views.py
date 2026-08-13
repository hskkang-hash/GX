import logging
import json
from django.forms import Form
from ninja_extra import api_controller, route
from ninja import Schema, Path, Query, Form, File
from typing import List, Optional, Dict, Any
from ninja.errors import ValidationError
from django.core.paginator import Paginator
from django.utils.translation import gettext as _
from drone_communication.schemas.schemas_djantic_in import ChangeStatusInSchema
from common.utils import SchemaUtils

from django.db import connection, reset_queries
from django.conf import settings
from core.role.permission import path_permission
from core.common.base_response import BaseResponse

from drone_communication.services.drone_service import DroneComunicationService
from common.constant import MESSAGE_ENUM



logger = logging.getLogger(__name__)

@api_controller('/drone-communication-management', 
                tags=['Drone Communication Management'])
class DroneCommunicationAPI:
    @route.get('/online-drones')
    # @path_permission("read")
    def get_online_drones(
        self, 
        page: int = Query(1, description="Page number, starting from 1"),
        page_size: int = Query(10, description="Number of items per page"),
        search_field: Optional[str] = Query(None, description="Search by DRONE_UNIQUE_ID")
    ):
        """
        Get a paginated list of online drones from the SignalR hub.
        
        Args:
            page (int): Page number, starting from 1 (default: 1)
            page_size (int): Number of items per page (default: 10)
            search_field (str, optional): Search term for filtering by DRONE_UNIQUE_ID
        
        Returns:
            BaseResponse: A list of online drones with pagination metadata.
        """
        try:
            # Get online drones with pagination and search
            result = DroneComunicationService.get_online_drones(
                page=page,
                page_size=page_size,
                search_field=search_field
            )
            
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_DEVICE_SUCCESS),
                data=result
            )
        except Exception as e:
            logger.error(f"Error getting online drones: {str(e)}")
            return BaseResponse(
                status_code=500,
                message=f"Error getting online drones: {str(e)}",
                data=[]
            )
            

    @route.post('/change-status')
    def change_status(self, data: ChangeStatusInSchema):
        try:
            result = DroneComunicationService.change_status(data.drone_uid, data.status, data.active)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CHANGE_STATUS_SUCCESS),
                data=result
            )
        except Exception as e:
            logger.error(f"Error changing status: {str(e)}")
            return BaseResponse(
                status_code=500,
                message=f"Error changing status: {str(e)}",
                data=[]
            )