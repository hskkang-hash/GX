from django.urls import path
from report_template.api import report_template_api

urlpatterns = [
    path('', report_template_api.urls),
] 