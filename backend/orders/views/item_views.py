from orders.models import OrderItemType
from ninja_extra import api_controller, route
from core.common.base_response import BaseResponse
from core.common.search.dynamic_search import apply_dynamic_filters
from orders.schemas.schemas_djantic_out import OrderItemTypeOutSchema


@api_controller('/item-types', tags=['Item Types'])
class ItemTypesAPI:
    @route.get('/')
    def get_item_types(self, request):
        item_types = OrderItemType._base_manager.filter(is_active=True)
        item_types = apply_dynamic_filters(item_types, request, [], request.GET.get('sort_obj'))
        # Convert QuerySet to serializable data using PaymentTypeOutSchema
        serialized_item_types = [OrderItemTypeOutSchema.from_orm(item_type) for item_type in item_types]
        return BaseResponse(
            status_code=200,
            message="Item types retrieved successfully",
            data=serialized_item_types
        )
