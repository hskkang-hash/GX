from ninja_extra import api_controller, route
from ninja.errors import ValidationError
from typing import List, Optional
from common.pagination import OptimizedPaginator

from core.common.base_response import BaseResponse
from core.api.v1.auth import CustomJWTAuth
from orders.schemas.schemas_djantic_in import ExternalOrderStatusCreateSchema, ExternalOrderStatusUpdateSchema
from orders.schemas.schemas_djantic_out import ExternalOrderStatusOutSchema
from orders.services.external_order_status_service import ExternalOrderStatusService
from common.constant import MESSAGE_ENUM


@api_controller('/external-order-statuses', tags=['External Order Status'])
class ExternalOrderStatusAPI:

    @route.get("", auth=CustomJWTAuth())
    def list_external_order_statuses(
        self,
        request,
        group_id: Optional[int] = None,
        page_size: int = 10,
        current_page: int = 1
    ):
        """
        Get list of external order statuses with pagination and filtering.
        """
        try:
            # Convert string parameters if provided
            page_size = int(request.GET.get('page_size', page_size))
            current_page = int(request.GET.get('current_page', current_page))
            
            queryset = ExternalOrderStatusService.get_list(
                request=request,
                group_id=group_id
            )
            
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(queryset, page_size)
            pages = paginator.page(current_page)
            
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_EXTERNAL_ORDER_STATUS_SUCCESS),
                data=ExternalOrderStatusOutSchema.from_queryset(pages.object_list, many=True),
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page
            )
            
        except Exception as e:
            return BaseResponse(status_code=400, message=str(e))

    @route.get("/{external_status_id}", auth=CustomJWTAuth())
    def get_external_order_status(self, request, external_status_id: int):
        """
        Get external order status by ID.
        """
        try:
            external_status = ExternalOrderStatusService.get_by_id(external_status_id)
            data = ExternalOrderStatusOutSchema.from_queryset(external_status)
            
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_EXTERNAL_ORDER_STATUS_DETAIL_SUCCESS),
                data=data
            )
            
        except ValidationError as e:
            return BaseResponse(status_code=404, message=MESSAGE_ENUM.get(MESSAGE_ENUM.EXTERNAL_ORDER_STATUS_NOT_FOUND))
        except Exception as e:
            return BaseResponse(status_code=400, message=str(e))

    @route.post("", auth=CustomJWTAuth())
    def create_external_order_status(self, request, payload: ExternalOrderStatusCreateSchema):
        """
        Create a new external order status.
        """
        try:
            # Get user's group if not provided in payload
            data = payload.dict()
            
                
            external_status = ExternalOrderStatusService.create(data, request.user)
            response_data = ExternalOrderStatusOutSchema.from_queryset(external_status)
            
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_EXTERNAL_ORDER_STATUS_SUCCESS),
                data=response_data
            )
            
        except ValidationError as e:
            return BaseResponse(status_code=400, message=str(e))
        except Exception as e:
            return BaseResponse(status_code=400, message=str(e))

    @route.put("/{external_status_id}", auth=CustomJWTAuth())
    def update_external_order_status(
        self,
        request, 
        external_status_id: int, 
        payload: ExternalOrderStatusUpdateSchema
    ):
        """
        Update an external order status.
        """
        try:
            data = payload.dict(exclude_unset=True)
            external_status = ExternalOrderStatusService.update(
                external_status_id, data, user=request.auth
            )
            response_data = ExternalOrderStatusOutSchema.from_queryset(external_status)
            
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_EXTERNAL_ORDER_STATUS_SUCCESS),
                data=response_data
            )
            
        except ValidationError as e:
            return BaseResponse(status_code=400, message=str(e))
        except Exception as e:
            return BaseResponse(status_code=400, message=str(e))

    @route.delete("/external-order-statuses/{external_status_ids}", auth=CustomJWTAuth())
    def delete_external_order_status(self, request, external_status_ids: str):
        """
        Delete an external order status.
        """
        try:
            external_status_ids = [int(id.strip()) for id in external_status_ids.split(",")]
            success, message = ExternalOrderStatusService.delete(
                external_status_ids, user=request.auth
            )
            
            if success:
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                    data={'error': message},
                )
                
        except Exception as e:
            return BaseResponse(status_code=400, message=str(e)) 