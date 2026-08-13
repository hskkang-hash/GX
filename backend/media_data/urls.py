from ninja_extra import NinjaExtraAPI
from django.urls import path
from media_data.views.media_data_view import MediaDataAPI


media_data_api = NinjaExtraAPI(
    title="Media Data API",
    version="1.0.0",
    description="APIs for listing and managing media (images/videos) stored in MinIO.",
    urls_namespace='media_data',
    docs_url="docs/",
)

media_data_api.register_controllers(
    MediaDataAPI,
)

urlpatterns = [
    path('', media_data_api.urls),
]


