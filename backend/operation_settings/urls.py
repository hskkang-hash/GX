from django.urls import path
from ninja_extra import NinjaExtraAPI
from operation_settings.views.operation_settings_view import OperationSettingsView
from operation_settings.views.menu_integration_view import MenuIntegrationView

api = NinjaExtraAPI(urls_namespace="operation_settings_api")
api.register_controllers(OperationSettingsView, MenuIntegrationView)


urlpatterns = [
    path("", api.urls),
]
