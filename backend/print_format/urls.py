from django.urls import path, include
from print_format.views import PrintFormatController
from ninja_extra import NinjaExtraAPI

print_format_api = NinjaExtraAPI(urls_namespace='print_format')

print_format_api.register_controllers(
    PrintFormatController
)

urlpatterns = [
    path('', print_format_api.urls),
] 