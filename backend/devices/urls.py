from django.urls import path
from ninja_extra import NinjaExtraAPI
from .views import (
    PackagingSpecificationAPI,
    ProtocolAPI,
    DeviceAPI,
    MotorTypeAPI,
    BatteryTypeAPI,
    IMUAPI,
    ImageStabilizationAPI,
    GNSSSystemAPI,
    CameraAPI,
    LibraryAPI
)

api = NinjaExtraAPI(urls_namespace="devices_api")  # Thêm namespace
api.register_controllers(
   
    ProtocolAPI,
    DeviceAPI,
    MotorTypeAPI,
    BatteryTypeAPI,
    IMUAPI,
    ImageStabilizationAPI,
    GNSSSystemAPI,
    PackagingSpecificationAPI,
    CameraAPI,
    LibraryAPI
)

urlpatterns = [
    path("", api.urls),  
] 
