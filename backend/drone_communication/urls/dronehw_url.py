from django.urls import path
from ninja_extra import NinjaExtraAPI
from drone_communication.views.drone_views import DroneCommunicationAPI
from drone_communication.views.group_views import GroupAPI

api = NinjaExtraAPI(urls_namespace="dronehw_api")  
api.register_controllers(
  DroneCommunicationAPI,
  GroupAPI
)

urlpatterns = [
    path("", api.urls),  
] 
