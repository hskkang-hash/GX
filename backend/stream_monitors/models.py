from core.base import BaseModel, BaseModelWithGroup
from django.db import models
from django.conf import settings

from devices.models import Device

class AIModel(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
    code = models.CharField(max_length=255)
    link = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    TRANSLATABLE_FIELDS = ['name', 'description']

# Create your models here.
class StreamMonitor(BaseModelWithGroup):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    drone = models.ForeignKey(Device, on_delete=models.CASCADE, null=True, blank=True)
    ip_source = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_visualize = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    is_external = models.BooleanField(default=False)
    external_drone_name = models.CharField(max_length=255, null=True, blank=True)
    external_operation_name = models.CharField(max_length=255, null=True, blank=True)
    external_registration_number = models.CharField(max_length=255, null=True, blank=True)
    external_manufacturer = models.CharField(max_length=255, null=True, blank=True)
    external_flight_distance = models.FloatField(null=True, blank=True)
    external_flight_time = models.IntegerField(null=True, blank=True)
    external_flight_altitude = models.FloatField(null=True, blank=True)
    external_start_point_x = models.CharField(max_length=255, null=True, blank=True)
    external_start_point_y = models.CharField(max_length=255, null=True, blank=True)
    external_end_point_x = models.CharField(max_length=255, null=True, blank=True)
    external_end_point_y = models.CharField(max_length=255, null=True, blank=True)
    external_start_time = models.DateTimeField(null=True, blank=True)
    external_end_time = models.DateTimeField(null=True, blank=True)
    external_remark = models.TextField(null=True, blank=True)
    TRANSLATABLE_FIELDS = ['name']

    def __str__(self):
        return self.name
    
class StreamMonitorAIModel(BaseModel):
    stream_monitor = models.ForeignKey(StreamMonitor, on_delete=models.CASCADE)
    ai_model = models.ForeignKey(AIModel, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    in_use = models.BooleanField(default=True)
    ai_stream_url = models.CharField(max_length=255, null=True, blank=True)
    def __str__(self):
        return self.stream_monitor.name


class DrawingSession(BaseModel):
    """Model for managing drawing sessions"""
    name = models.CharField(max_length=255)
    stream_monitor = models.ForeignKey(StreamMonitor, on_delete=models.CASCADE, related_name='drawing_sessions')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.stream_monitor.name}"


class DrawingElement(models.Model):
    """Model for storing individual drawing elements"""
    ELEMENT_TYPES = [
        ('line', 'Line'),
        ('rectangle', 'Rectangle'),
        ('circle', 'Circle'),
        ('polygon', 'Polygon'),
        ('text', 'Text'),
        ('arrow', 'Arrow'),
    ]
    
    session = models.ForeignKey(DrawingSession, on_delete=models.CASCADE, related_name='elements')
    element_type = models.CharField(max_length=20, choices=ELEMENT_TYPES)
    data = models.JSONField()  # Store drawing data (coordinates, style, etc.)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.element_type} - {self.session.name}"


class DrawingParticipant(models.Model):
    """Model for tracking users participating in drawing sessions"""
    session = models.ForeignKey(DrawingSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_online = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['session', 'user']
    
    def __str__(self):
        return f"{self.user.username} - {self.session.name}"
    
class StreamMonitorRecord(models.Model):
    stream_id = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    status = models.CharField(max_length=255, default='running')
    object_path = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    # Auto-stop functionality fields
    auto_stop_task_id = models.CharField(max_length=255, null=True, blank=True, help_text="Celery task ID for auto-stop")

    def __str__(self):
        return str(self.id)
