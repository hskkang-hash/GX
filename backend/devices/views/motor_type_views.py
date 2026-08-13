from ninja_extra import api_controller, route
from typing import List
from ninja.errors import ValidationError
from common.pagination import OptimizedPaginator

from devices.models import MotorType
from devices.schemas.schemas_djantic_in import MotorTypeInSchema
from devices.schemas.schemas_djantic_out import MotorTypeOutSchema
from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from core.common.search.dynamic_search import apply_dynamic_filters
from common.constant import MESSAGE_ENUM

@api_controller('/motor-types', tags=['Motor Types'])
class MotorTypeAPI:
    @route.get('')
    def list_motor_types(self, request):
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))
        
        motor_types = MotorType.objects.all().order_by('-id')
        motor_types = apply_dynamic_filters(motor_types, request.GET, [], request.GET.get('sort_obj', None))
        
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(motor_types, page_size)
        pages = paginator.page(current_page)
   
        data = MotorTypeOutSchema.from_queryset(pages.object_list, many=True)
        
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_MOTOR_TYPE_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get('/{id}')
    def get_motor_type(self, id: int):
        try:
            motor_type = MotorType.objects.get(id=id)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_MOTOR_TYPE_DETAIL_SUCCESS),
                data=MotorTypeOutSchema.from_queryset(motor_type) 
            )
        except MotorType.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Motor type"),
                data=None
            )

    @route.post('', auth=CustomJWTAuth())
    def create_motor_type(self, data: MotorTypeInSchema):
        try:
            motor_type = MotorType.objects.create(**data.dict())
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_MOTOR_TYPE_SUCCESS),
                data=MotorTypeOutSchema.from_queryset(motor_type)
            )
        except ValidationError as e:
            return {"success": False, "errors": e.errors()}

    @route.put('/{id}', auth=CustomJWTAuth())
    def update_motor_type(self, id: int, data: MotorTypeInSchema):
        try:
            motor_type = MotorType.objects.get(id=id)
            for key, value in data.dict().items():
                setattr(motor_type, key, value)
            motor_type.save()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_MOTOR_TYPE_SUCCESS),
                data=MotorTypeOutSchema.from_queryset(motor_type)
            )
        except MotorType.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Motor type"),
                data=None
            )
        except ValidationError as e:
            return {"success": False, "errors": e.errors()}

    @route.delete('/{id}', auth=CustomJWTAuth())
    def delete_motor_type(self, id: int):
        try:
            motor_type = MotorType.objects.get(id=id)
            motor_type.delete()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                data=None
            )
        except MotorType.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Motor type"),
                data=None
            )