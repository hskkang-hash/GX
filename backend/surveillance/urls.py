from django.urls import path
from ninja_extra import NinjaExtraAPI


from surveillance.views.surveillance_profile_view import SurveillanceProfileController, VideoAnalysisController
# from surveillance.views.patrol_gcs_view import PatrolGCSController
from surveillance.views.survey_mission_view import SurveyMissionController
from surveillance.views.surveillance_dashboard_view import SurveillanceDashboardController


api = NinjaExtraAPI(
    title="Surveillance API",
    version="1.0.0",
    description="API for Survey Mission operations - 조사 미션 관리",
    urls_namespace="surveillance_api",
    docs_url="docs/",
)

# Register controllers
api.register_controllers(
    SurveillanceProfileController,
    # PatrolGCSController,
    SurveyMissionController,
    VideoAnalysisController,
    SurveillanceDashboardController,
)

urlpatterns = [
    path("", api.urls),
]
