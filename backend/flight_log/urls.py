from django.urls import path
from ninja_extra import NinjaExtraAPI
from .views import (
    FlightLogAPI
)
 
api = NinjaExtraAPI(urls_namespace="flight_log_api")  # Thêm namespace
api.register_controllers(
    FlightLogAPI
)

urlpatterns = [
    path("", api.urls),  
] 
