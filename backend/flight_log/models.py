from django.db import models
from surveillance.models import SurveillanceProfile, SurveillanceProfileDrone
from terminals.models import Terminal, Routes
from devices.models import Device, DeviceStatus
from orders.models import OrderItem
from common.measurable_model import MeasurableModelWithGroup
from core.base import BaseModel


class DroneAnomalyPrediction(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name']


# Create your models here.
class FlightLog(MeasurableModelWithGroup):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='flight_logs_order_item', null=True, blank=True)
    drone = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='flight_logs_drone', null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    start_point = models.ForeignKey(Terminal, on_delete=models.CASCADE, related_name='flight_logs_start_point', null=True, blank=True)
    end_point = models.ForeignKey(Terminal, on_delete=models.CASCADE, related_name='flight_logs_end_point', null=True, blank=True)
    drone_state_prediction = models.ForeignKey(DeviceStatus, on_delete=models.CASCADE, related_name='flight_logs_drone_state_prediction', null=True, blank=True)
    drone_anomaly_prediction = models.ForeignKey(DroneAnomalyPrediction, on_delete=models.CASCADE, related_name='flight_logs_drone_anomaly_prediction', null=True, blank=True)
    log_file_path = models.CharField(max_length=255, null=True, blank=True)
    fetch_data_status = models.CharField(max_length=255, null=True, blank=True, default='done')
    fetch_count = models.IntegerField(default=3)
    profile_drone = models.ForeignKey(SurveillanceProfileDrone, on_delete=models.CASCADE, related_name='flight_logs_profile_drone', null=True, blank=True)
    service_name = models.CharField(max_length=255, null=True, blank=True)
    fetch_anomaly_status = models.CharField(max_length=255, null=True, blank=True, default='done')
    fetch_anomaly_count = models.IntegerField(default=3)
    MEASUREMENT_TYPES = {
        'total_distance': {'type': 'simple', 'default_unit': 'km'},
    }