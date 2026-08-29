"""
API endpoints cho DayOfWeek
"""

import json
from ninja_extra import api_controller, route
from typing import List, Optional
from ninja.errors import ValidationError
from django.core.paginator import Paginator

from terminals.models import DayOfWeek
from terminals.schemas.schemas_djantic_in import DayOfWeekInSchema
from terminals.schemas.schemas_djantic_out import DayOfWeekOutSchema
from terminals.services import day_of_week_service
from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from common.constant import MESSAGE_ENUM
from core.role.permission import path_permission
from ninja import Form


@api_controller('/days-of-week', tags=['Days of Week'])
class DayOfWeekController:
    @route.get('', auth=CustomJWTAuth())
    # @path_permission("read", path_override=['/terminals', '/delivery-hubs', '/docking-stations', '/infrastructure'])
    def list_days_of_week(self):
        """Lấy danh sách tất cả days of week"""
        days_of_week = day_of_week_service.get_all()
        data = DayOfWeekOutSchema.from_queryset(days_of_week, many=True, auto_resolve_fields=False)

        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_TERMINAL_TYPE_SUCCESS),
            data=data
        )

    @route.get('/{id}', auth=CustomJWTAuth())
    # @path_permission("read", path_override=['/terminals', '/delivery-hubs', '/docking-stations', '/infrastructure-terminals'])
    def get_day_of_week(self, id: int):
        """Lấy chi tiết một day of week"""
        day_of_week = day_of_week_service.get(id)

        if not day_of_week:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Day of week"),
                data=None
            )

        data = DayOfWeekOutSchema.from_queryset(day_of_week, many=False, auto_resolve_fields=False)
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_TERMINAL_TYPE_DETAIL_SUCCESS),
            data=data
        )

    @route.post('', auth=CustomJWTAuth())
    @path_permission("create", path_override=['/terminals', '/delivery-hubs', '/docking-stations', '/infrastructure-terminals'])
    def create_day_of_week(self, request, data: str = Form(..., description="JSON string của DayOfWeekInSchema")):
        """Tạo mới day of week"""
        try:
            data_dict = json.loads(data)
            schema = DayOfWeekInSchema(**data_dict)
            validated_data = schema.dict(exclude_unset=True)
        except Exception as e:
            return BaseResponse(
                status_code=422,
                message=str(e),
                data=None
            )

        success, result = day_of_week_service.create(validated_data)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )

        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_TERMINAL_TYPE_SUCCESS),
            data=DayOfWeekOutSchema.from_queryset(result, many=False)
        )

    @route.put('/{id}', auth=CustomJWTAuth())
    @path_permission("update", path_override=['/terminals', '/delivery-hubs', '/docking-stations', '/infrastructure-terminals'])
    def update_day_of_week(self, id: int, request, data: str = Form(..., description="JSON string của DayOfWeekInSchema")):
        """Cập nhật day of week"""
        try:
            data_dict = json.loads(data)
            schema = DayOfWeekInSchema(**data_dict)
            validated_data = schema.dict(exclude_unset=True)
        except Exception as e:
            return BaseResponse(
                status_code=422,
                message=str(e),
                data=None
            )

        success, result = day_of_week_service.update(id, validated_data)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )

        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_TERMINAL_TYPE_SUCCESS),
            data=DayOfWeekOutSchema.from_queryset(result, many=False)
        )

    @route.delete('/{id}', auth=CustomJWTAuth())
    @path_permission("delete", path_override=['/terminals', '/delivery-hubs', '/docking-stations', '/infrastructure-terminals'])
    def delete_day_of_week(self, id: int):
        """Xóa day of week"""
        success, result = day_of_week_service.delete(id)
        if not success:
            return BaseResponse(
                status_code=400,
                message=str(result),
                data=None
            )

        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
            data=None
        )
