from ninja_extra import api_controller, route
from ninja.errors import ValidationError
from typing import Optional
from common.pagination import OptimizedPaginator

from core.common.base_response import BaseResponse
from core.api.v1.auth import CustomJWTAuth
from orders.schemas.schemas_djantic_in import (
    OrderStatusMappingBulkUpdateSchema,
    OrderStatusMappingBulkCreateSchema,
)
from orders.schemas.schemas_djantic_out import ExternalOrderStatusOutSchema, OrderStatusMappingOutSchema
from orders.services.order_status_mapping_service import OrderStatusMappingService
from common.constant import MESSAGE_ENUM


@api_controller('/order-status-mappings', tags=['Order Status Mapping'])
class OrderStatusMappingAPI:

    @route.get("", auth=CustomJWTAuth())
    def list_order_status_mappings(
        self,
        request,
        group_id: Optional[int] = None,
        page_size: int = 10,
        current_page: int = 1
    ):
        """
        Get list of order status mappings with pagination and filtering.
        """
        try:
            # Convert string parameters if provided
            page_size = int(request.GET.get('page_size', page_size))
            current_page = int(request.GET.get('current_page', current_page))
            if not group_id:
                queryset = OrderStatusMappingService.get_list(
                    request=request,
                    group_id=group_id
                )
                # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
                paginator = OptimizedPaginator(queryset, page_size)
                pages = paginator.page(current_page)
                data = OrderStatusMappingOutSchema.from_queryset(pages.object_list,many=True)
            else:
                queryset = OrderStatusMappingService.get_list(
                    request=request,
                    group_id=group_id
                )
                # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
                paginator = OptimizedPaginator(queryset, page_size)
                pages = paginator.page(current_page)
                data = []
                for page in pages.object_list:
                    mapping = OrderStatusMappingOutSchema.from_queryset(page)
                    mapping['external_order_statuses'] = [ExternalOrderStatusOutSchema.from_queryset(eos) for eos in page.external_order_statuses.all()]
                    data.append(mapping)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_LIST_ORDER_STATUS_MAPPING_SUCCESS),
                data=data,
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page
            )
            
        except Exception as e:
            return BaseResponse(status_code=400, message=str(e))

    @route.get("/{mapping_id}", auth=CustomJWTAuth())
    def get_order_status_mapping(self, request, mapping_id: int): 
        """
        Get order status mapping by ID.
        """
        try:
            mapping = OrderStatusMappingService.get_by_id(mapping_id)
            data = OrderStatusMappingOutSchema.from_queryset(mapping)
            
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_ORDER_STATUS_MAPPING_DETAIL_SUCCESS),
                data=data
            )
            
        except ValidationError:
            return BaseResponse(status_code=404, message=MESSAGE_ENUM.get(MESSAGE_ENUM.ORDER_STATUS_MAPPING_NOT_FOUND))
        except Exception as e:
            return BaseResponse(status_code=400, message=str(e))

    @route.get("/available-statuses/{group_id}", auth=CustomJWTAuth())
    def get_available_statuses_for_group(self, request, group_id: int):
        """
        Get available delivery statuses and external order statuses for a group.
        This endpoint is used for the mapping form to show available options.
        """
        try:
            statuses = OrderStatusMappingService.get_available_statuses_for_group(group_id)
            
            # Format delivery statuses
            delivery_statuses = [
                {
                    'id': ds.id,
                    'name': ds.name,
                    'code': ds.code,
                    'description': ds.description,
                    'color_code': ds.color_code
                }
                for ds in statuses['delivery_statuses']
            ]
            
            # Format external order statuses  
            external_statuses = [
                {
                    'id': eos.id,
                    'name': eos.name,
                    'value': eos.value,
                    'description': eos.description,
                    'is_active': eos.is_active
                }
                for eos in statuses['external_order_statuses']
            ]
            
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_AVAILABLE_STATUSES_SUCCESS),
                data={
                    'delivery_statuses': delivery_statuses,
                    'external_order_statuses': external_statuses
                }
            )
            
        except Exception as e:
            return BaseResponse(status_code=400, message=str(e))

    @route.post("", auth=CustomJWTAuth())
    def bulk_upsert_order_status_mappings(self, request, payload: OrderStatusMappingBulkCreateSchema):
        """Create or replace mappings for a group from full payload (no id)."""
        try:
            data = payload.dict()
            group_id = data.get('group_id') or getattr(request.auth, 'group_id', None)
            if not group_id:
                raise ValidationError("group_id is required")
            mappings = data.get('mappings', [])
            OrderStatusMappingService.upsert_bulk(group_id, mappings, prune_missing=True, user=request.auth)
            # Return queryset (not the list returned from service)
            queryset = OrderStatusMappingService.get_list(request=None, group_id=group_id)
            response = OrderStatusMappingOutSchema.from_queryset(queryset, many=True)
            return BaseResponse(
                status_code=200,
                message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_ORDER_STATUS_MAPPING_SUCCESS),
                data=response
            )
        except ValidationError as e:
            return BaseResponse(status_code=400, message=str(e))
        except Exception as e:
            return BaseResponse(status_code=400, message=str(e))

    @route.put("update/{group_id}", auth=CustomJWTAuth())
    def update_order_status_mapping(
        self,
        request,
        group_id: int,
        payload: OrderStatusMappingBulkUpdateSchema,
    ):
        # """Update a group's mappings: upsert all items and prune statuses missing in payload (None = skip)."""
        # try:
        # existing = OrderStatusMappingService.get_by_id(mapping_id)
        # group_id = existing.group_id
        body = payload.dict()
        mappings = body.get('mappings') or [] 
        OrderStatusMappingService.upsert_bulk(group_id, mappings, prune_missing=True, user=request.auth) 
        # Return queryset for this group
        queryset = OrderStatusMappingService.get_list(request=None, group_id=group_id)
        response = OrderStatusMappingOutSchema.from_queryset(queryset, many=True)
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_ORDER_STATUS_MAPPING_SUCCESS),
            data=response,
        ) 
        # except ValidationError as e:
        #     return BaseResponse(status_code=400, message=str(e))
        # except Exception as e:
        #     return BaseResponse(status_code=400, message=str(e))

    @route.delete("delete/{group_ids}", auth=CustomJWTAuth())
    def delete_order_status_mapping(self, request, group_ids: str):
        """
        Delete an order status mapping.
        """
        try:
            group_ids = [int(id.strip()) for id in group_ids.split(",")]
            success, message = OrderStatusMappingService.delete(
                group_ids, user=request.auth
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

    @route.get("/resolve-status/{group_id}/{external_status_code}", auth=CustomJWTAuth())
    def resolve_delivery_status(self, request, group_id: int, external_status_code: str):
        """
        Resolve external status code to delivery status for a specific group.
        This endpoint is used to map external API status codes to internal delivery statuses.
        """
        try:
            delivery_status = OrderStatusMappingService.get_mapped_delivery_status(
                external_status_code, group_id
            )
            
            if delivery_status:
                data = {
                    'id': delivery_status.id,
                    'name': delivery_status.name,
                    'code': delivery_status.code,
                    'description': delivery_status.description,
                    'color_code': delivery_status.color_code
                }
                
                return BaseResponse(
                    status_code=200,
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.RESOLVE_STATUS_MAPPING_SUCCESS),
                    data=data
                )
            else:
                return BaseResponse(
                    status_code=404, 
                    message=MESSAGE_ENUM.get(MESSAGE_ENUM.STATUS_MAPPING_NOT_FOUND)
                )
            
        except Exception as e:
            return BaseResponse(status_code=400, message=str(e)) 