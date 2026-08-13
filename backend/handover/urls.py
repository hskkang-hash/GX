from django.urls import path
from ninja_extra import NinjaExtraAPI

from handover.views.handover_views import (
    HandoverShiftController,
    HandoverManagementController,
    HandoverContentController,
    HandoverNoticeController,
    HandoverNoticeCommentController
)

api = NinjaExtraAPI(
    title="Handover API",
    version="1.0.0",
    description="API for Handover Management",
    urls_namespace="handover_api",
    docs_url="docs/",
)

# Register controllers
api.register_controllers(
    HandoverShiftController,
    HandoverManagementController,
    HandoverContentController,
    HandoverNoticeController,
    HandoverNoticeCommentController,
)

urlpatterns = [
    path("", api.urls),
]

