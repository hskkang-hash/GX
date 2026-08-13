from django.urls import path, include
from ninja_extra import NinjaExtraAPI
from partner.views import PartnerController
from partner.views.partner_callback_mockup_controller import PartnerCallbackMockupController

partner_api = NinjaExtraAPI(urls_namespace="partner_api")
partner_api.register_controllers(PartnerController, PartnerCallbackMockupController)

urlpatterns = [
    path("", partner_api.urls),
]
