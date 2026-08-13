from django.urls import path
from ninja_extra import NinjaExtraAPI
from .views import (
    OrderAPI,
    DeliveryOptionAPI,
    PackageAPI,
    PaymentMethodsAPI,
    ItemTypesAPI,
    BankAPI,
    PickupLocationAPI,
    ExternalOrderStatusAPI,
    OrderStatusMappingAPI
)
 
api = NinjaExtraAPI(urls_namespace="orders_api")  # Thêm namespace
api.register_controllers(
    OrderAPI,
    DeliveryOptionAPI,
    PackageAPI,
    PaymentMethodsAPI,
    ItemTypesAPI,
    BankAPI,
    PickupLocationAPI,
    ExternalOrderStatusAPI,
    OrderStatusMappingAPI
)

urlpatterns = [
    path("", api.urls),  
] 
