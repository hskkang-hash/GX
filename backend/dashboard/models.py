# app/models.py
from django.db import models
from common.base_model import BaseModelWithGroup
from core.base import BaseModel
from core.user.models import CoreUser

class Dashboard(BaseModelWithGroup):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    layout_config = models.JSONField(blank=True, null=True)
    data_updated_at = models.DateTimeField(blank=True, null=True)
    TRANSLATABLE_FIELDS = ['name']

    def __str__(self):
        return self.name

class DashboardPanel(BaseModelWithGroup):
    PANEL_TYPES = [
        ("chart", "Chart"),
        ("table", "Table"),
        ("metric", "Metric"),
        ("text", "Text"),
    ]

    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name="panels")
    panel_title = models.CharField(max_length=255)
    panel_type = models.CharField(max_length=20, choices=PANEL_TYPES)
    panel_config = models.JSONField(blank=True, null=True)
    panel_data = models.JSONField(blank=True, null=True)
    TRANSLATABLE_FIELDS = ['panel_title']

    def __str__(self):
        return self.panel_title
    
class WeatherSetting(BaseModel):
    latitude = models.FloatField()
    longitude = models.FloatField()
    address = models.CharField(max_length=1024)
    is_surveillance_dashboard = models.BooleanField(default=False)