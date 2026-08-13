from django.urls import path
from ninja_extra import NinjaExtraAPI
from delivery.views.api import controllers

api = NinjaExtraAPI(
    title="Delivery API",
    version="1.0.0",
    description="API for delivery operations",
    urls_namespace="delivery_api",
    docs_url="docs/",
)

# Đăng ký tất cả controllers
for controller in controllers:
    api.register_controllers(controller)

urlpatterns = [
    path("", api.urls),
]
