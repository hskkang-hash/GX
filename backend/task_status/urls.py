from django.urls import path
from ninja_extra import NinjaExtraAPI

from task_status.views.task_status_views import TaskStatusController

task_status_api = NinjaExtraAPI(urls_namespace="task_status")
task_status_api.register_controllers(TaskStatusController)

urlpatterns = [
    path("", task_status_api.urls),
]

