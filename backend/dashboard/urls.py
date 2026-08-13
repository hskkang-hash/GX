from django.urls import path
from ninja_extra import NinjaExtraAPI
from .views import (
    DashboardAPI,
)

api = NinjaExtraAPI(urls_namespace="dashboard_api", title="Dashboard API", description="API for dashboard") 
api.register_controllers(
    DashboardAPI,
)

urlpatterns = [
    path("", api.urls),  
] 
