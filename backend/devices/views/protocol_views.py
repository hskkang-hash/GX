from ninja_extra import api_controller, route
from typing import List
from ninja.errors import ValidationError
from common.pagination import OptimizedPaginator

from devices.models import Protocol
from devices.schemas.schemas_djantic_in import ProtocolInSchema
from devices.schemas.schemas_djantic_out import ProtocolOutSchema
from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from core.common.search.dynamic_search import apply_dynamic_filters
from common.constant import MESSAGE_ENUM
from common.inbound_api_key import JwtOrInboundKey

@api_controller('/protocols', tags=['Protocols'])
class ProtocolAPI:
    @route.get('', response=List[ProtocolOutSchema], auth=JwtOrInboundKey())
    def list_protocols(self, request):
        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))

        protocols = Protocol.objects.all().order_by('-id')
        protocols = apply_dynamic_filters(protocols, request.GET, [], request.GET.get('sort_obj', None))


        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(protocols, page_size)
        pages = paginator.page(current_page)
        data = ProtocolOutSchema.from_queryset(pages.object_list, many=True)

        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_PROTOCOL_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get('/{id}', auth=JwtOrInboundKey())
    def get_protocol(self, id: int):
        try:
            protocol = Protocol.objects.get(id=id)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_PROTOCOL_DETAIL_SUCCESS),
                data=ProtocolOutSchema.from_queryset(protocol)
            )
        except Protocol.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Protocol"),
                data=None
            )

    @route.post('', auth=CustomJWTAuth())
    def create_protocol(self, data: ProtocolInSchema):
        try:
            protocol = Protocol.objects.create(**data.dict())
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_PROTOCOL_SUCCESS),
                data=ProtocolOutSchema.from_queryset(protocol)
            )
        except ValidationError as e:
            return {"success": False, "errors": e.errors()}

    @route.put('/{id}', auth=CustomJWTAuth())
    def update_protocol(self, id: int, data: ProtocolInSchema):
        try:
            protocol = Protocol.objects.get(id=id)
            for key, value in data.dict().items():
                setattr(protocol, key, value)
            protocol.save()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_PROTOCOL_SUCCESS),
                data=ProtocolOutSchema.from_queryset(protocol)
            )
        except Protocol.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Protocol"),
                data=None
            )
        except ValidationError as e:
            return {"success": False, "errors": e.errors()}

    @route.delete('/{id}', auth=CustomJWTAuth())
    def delete_protocol(self, id: int):
        try:
            protocol = Protocol.objects.get(id=id)
            protocol.delete()
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                data=None
            )
        except Protocol.DoesNotExist:
            return BaseResponse(
                status_code=404,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.NOT_FOUND, "Protocol"),
                data=None
            )
