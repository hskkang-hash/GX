from ninja_extra import api_controller, route
from typing import List
from ninja.errors import ValidationError
from common.pagination import OptimizedPaginator

from devices.models import ImageStabilization
from devices.schemas.schemas_djantic_in import ImageStabilizationInSchema
from devices.schemas.schemas_djantic_out import ImageStabilizationOutSchema
from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from core.common.search.dynamic_search import apply_dynamic_filters
from common.constant import MESSAGE_ENUM
from common.inbound_api_key import JwtOrInboundKey

@api_controller('/image-stabilizations', tags=['Image Stabilizations'])
class ImageStabilizationAPI:
    @route.get('', auth=JwtOrInboundKey())
    def list_image_stabilizations(self, request):
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        stabilizations = ImageStabilization.objects.all().order_by('-id')
        stabilizations = apply_dynamic_filters(stabilizations, request.GET, [], request.GET.get('sort_obj', None))

        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(stabilizations, page_size)
        pages = paginator.page(current_page)
        data = ImageStabilizationOutSchema.from_queryset(pages.object_list, many=True)

        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_IMAGE_STABILIZATION_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get('/{id}', auth=JwtOrInboundKey())
    def get_image_stabilization(self, id: int):
        try:
            stabilization = ImageStabilization.objects.get(id=id)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_IMAGE_STABILIZATION_DETAIL_SUCCESS),
                data=ImageStabilizationOutSchema.from_queryset(stabilization)
            )
        except ImageStabilization.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Image stabilization"),
                data=None
            )

    @route.post('', auth=CustomJWTAuth())
    def create_image_stabilization(self, data: ImageStabilizationInSchema):
        try:
            stabilization = ImageStabilization.objects.create(**data.dict())
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_IMAGE_STABILIZATION_SUCCESS),
                data=ImageStabilizationOutSchema.from_queryset(stabilization)
            )
        except ValidationError as e:
            return {"success": False, "errors": e.errors()}

    @route.put('/{id}', auth=CustomJWTAuth())
    def update_image_stabilization(self, id: int, data: ImageStabilizationInSchema):
        try:
            stabilization = ImageStabilization.objects.get(id=id)
            for key, value in data.dict().items():
                setattr(stabilization, key, value)
            stabilization.save()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_IMAGE_STABILIZATION_SUCCESS),
                data=ImageStabilizationOutSchema.from_queryset(stabilization)
            )
        except ImageStabilization.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Image stabilization"),
                data=None
            )
        except ValidationError as e:
            return {"success": False, "errors": e.errors()}

    @route.delete('/{id}', auth=CustomJWTAuth())
    def delete_image_stabilization(self, id: int):
        try:
            stabilization = ImageStabilization.objects.get(id=id)
            stabilization.delete()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                data=None
            )
        except ImageStabilization.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Image stabilization"),
                data=None
            )
