from ninja_extra import api_controller, route
from typing import List
from ninja.errors import ValidationError
from common.pagination import OptimizedPaginator

from devices.models import BatteryType
from devices.schemas.schemas_djantic_in import BatteryTypeInSchema
from devices.schemas.schemas_djantic_out import BatteryTypeOutSchema
from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from core.common.search.dynamic_search import apply_dynamic_filters
from common.constant import MESSAGE_ENUM
from common.inbound_api_key import JwtOrInboundKey

@api_controller('/battery-types', tags=['Battery Types'])
class BatteryTypeAPI:
    @route.get('', auth=JwtOrInboundKey())
    def list_battery_types(self, request):
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        battery_types = BatteryType.objects.all().order_by('-id')
        battery_types = apply_dynamic_filters(battery_types, request.GET, [], request.GET.get('sort_obj', None))

        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(battery_types, page_size)
        pages = paginator.page(current_page)
        data = BatteryTypeOutSchema.from_queryset(pages.object_list, many=True)

        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_BATTERY_TYPE_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get('/{id}', auth=JwtOrInboundKey())
    def get_battery_type(self, id: int):
        try:
            battery_type = BatteryType.objects.get(id=id)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_BATTERY_TYPE_DETAIL_SUCCESS),
                data=BatteryTypeOutSchema.from_queryset(battery_type)
            )
        except BatteryType.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Battery type"),
                data=None
            )

    @route.post('', auth=CustomJWTAuth())
    def create_battery_type(self, data: BatteryTypeInSchema):
        try:
            battery_type = BatteryType.objects.create(**data.dict())
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_BATTERY_TYPE_SUCCESS),
                data=BatteryTypeOutSchema.from_queryset(battery_type)
            )
        except ValidationError as e:
            return {"success": False, "errors": e.errors()}

    @route.put('/{id}', auth=CustomJWTAuth())
    def update_battery_type(self, id: int, data: BatteryTypeInSchema):
        try:
            battery_type = BatteryType.objects.get(id=id)
            # for key, value in data.dict().items():
            #     setattr(battery_type, key, value)
            battery_type.update(**data.dict())
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_BATTERY_TYPE_SUCCESS),
                data=BatteryTypeOutSchema.from_queryset(battery_type)
            )
        except BatteryType.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Battery type"),
                data=None
            )
        except ValidationError as e:
            return {"success": False, "errors": e.errors()}

    @route.delete('/{id}', auth=CustomJWTAuth())
    def delete_battery_type(self, id: int):
        try:
            battery_type = BatteryType.objects.get(id=id)
            battery_type.delete()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                data=None
            )
        except BatteryType.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Battery type"),
                data=None
            )
