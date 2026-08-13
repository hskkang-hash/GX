from django.urls import path
from ninja_extra import NinjaExtraAPI
from .views.api import (
    ThirdPartyIntegrationController,
    ThirdPartyAPIKeyController
)
from .views.anyang_views import (
    AnyangDeliveryAppController,
    AnyangGuardianXController
)

api = NinjaExtraAPI(
    title="Third Party Integration API",
    version="1.0.0",
    description="API for third-party integrations including ETRI and Anyang systems",
    docs_url="/docs/",
    urls_namespace="third_party_api"
)

api.register_controllers(
    ThirdPartyIntegrationController,
    ThirdPartyAPIKeyController,
    AnyangDeliveryAppController,
    AnyangGuardianXController
)

urlpatterns = [
    path("", api.urls),
] 