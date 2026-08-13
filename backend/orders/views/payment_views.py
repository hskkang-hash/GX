from orders.models import PaymentType
from ninja_extra import api_controller, route
from core.common.base_response import BaseResponse
from orders.schemas.schemas_djantic_out import PaymentTypeOutSchema


@api_controller('/payment-methods', tags=['Payment Methods'])
class PaymentMethodsAPI:
    @route.get('/')
    def get_payment_methods(self, request):
        payment_methods = PaymentType.objects.filter(is_active=True)
        # Convert QuerySet to serializable data using PaymentTypeOutSchema
        serialized_payment_methods = [PaymentTypeOutSchema.from_orm(payment_method) for payment_method in payment_methods]
        return BaseResponse(
            status_code=200,
            message="Payment methods retrieved successfully",
            data=serialized_payment_methods
        )
