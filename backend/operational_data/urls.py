from django.urls import path
from ninja_extra import NinjaExtraAPI
from operational_data.views.operational_data_view import OperationalDataAPI
from operational_data.views.operational_notice_view import OperationalNoticeAPI
 
api = NinjaExtraAPI(urls_namespace="operational_data_api")
api.register_controllers(
    OperationalDataAPI,
    OperationalNoticeAPI
)

urlpatterns = [
    path("", api.urls),  
] 
