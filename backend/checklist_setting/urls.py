from django.urls import path
from checklist_setting.api import checklist_setting_api

urlpatterns = [
    path("", checklist_setting_api.urls),
]
