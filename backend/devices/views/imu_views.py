from ninja_extra import api_controller, route
from typing import List
from ninja.errors import ValidationError
from common.pagination import OptimizedPaginator

from devices.models import IMU
from devices.schemas.schemas_djantic_in import IMUInSchema
from devices.schemas.schemas_djantic_out import IMUOutSchema
from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from core.common.search.dynamic_search import apply_dynamic_filters
from common.constant import MESSAGE_ENUM
from common.inbound_api_key import JwtOrInboundKey

@api_controller('/imus', tags=['IMUs'])
class IMUAPI:
    @route.get('', auth=JwtOrInboundKey())
    def list_imus(self, request):
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        imus = IMU.objects.all().order_by('-id')
        imus = apply_dynamic_filters(imus, request.GET, [], request.GET.get('sort_obj', None))

        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(imus, page_size)
        pages = paginator.page(current_page)
        data = IMUOutSchema.from_queryset(pages.object_list, many=True)

        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_IMU_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get('/{id}', auth=JwtOrInboundKey())
    def get_imu(self, id: int):
        try:
            imu = IMU.objects.get(id=id)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_IMU_DETAIL_SUCCESS),
                data=IMUOutSchema.from_queryset(imu)
            )
        except IMU.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "IMU"),
                data=None
            )

    @route.post('', auth=CustomJWTAuth())
    def create_imu(self, data: IMUInSchema):
        try:
            imu = IMU.objects.create(**data.dict())
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_IMU_SUCCESS),
                data=IMUOutSchema.from_queryset(imu)
            )
        except ValidationError as e:
            return {"success": False, "errors": e.errors()}

    @route.put('/{id}', auth=CustomJWTAuth())
    def update_imu(self, id: int, data: IMUInSchema):
        try:
            imu = IMU.objects.get(id=id)
            for key, value in data.dict().items():
                setattr(imu, key, value)
            imu.save()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_IMU_SUCCESS),
                data=IMUOutSchema.from_queryset(imu)
            )
        except IMU.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "IMU"),
                data=None
            )
        except ValidationError as e:
            return {"success": False, "errors": e.errors()}

    @route.delete('/{id}', auth=CustomJWTAuth())
    def delete_imu(self, id: int):
        try:
            imu = IMU.objects.get(id=id)
            imu.delete()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                data=None
            )
        except IMU.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "IMU"),
                data=None
            )
