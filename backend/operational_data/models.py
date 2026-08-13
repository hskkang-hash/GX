from django.db import models
from delivery.models import DeliveryOperationItem
from core.base import BaseModel
from core.file_management.models import UserMediaFileItem, UserMediaFile
from core.user.models import CoreUser
from orders.models import OrderItem

# Create your models here.
class OperationalData(BaseModel):
    operation_item = models.ForeignKey(DeliveryOperationItem, on_delete=models.CASCADE, related_name='operational_data')
    operation_item_type = models.CharField(max_length=255)
    device_type = models.CharField(max_length=255)
    media_file = models.ForeignKey(UserMediaFile, on_delete=models.CASCADE)

class OperationalDataUploadStatus(BaseModel):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('partial_success', 'Partial Success'),
        ('failed', 'Failed'),
    ]
    
    UPLOAD_TYPE_CHOICES = [
        ('video', 'Video'),
        ('log', 'Log'),
    ]
    
    DEVICE_TYPE_CHOICES = [
        ('drone', 'Drone'),
        ('robot', 'Robot'),
    ]
    
    # Core fields
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='upload_statuses')
    user = models.ForeignKey(CoreUser, on_delete=models.CASCADE, related_name='upload_statuses')
    task_id = models.CharField(max_length=255, unique=True, db_index=True)
    is_notification_sent = models.BooleanField(default=False)
    
    # Upload details
    upload_type = models.CharField(max_length=50, choices=UPLOAD_TYPE_CHOICES, default='video')
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPE_CHOICES, default='drone')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    
    # Progress tracking
    total_files = models.IntegerField(default=0)
    uploaded_files = models.IntegerField(default=0)
    failed_files = models.IntegerField(default=0)
    
    # Status details
    message = models.TextField(blank=True, null=True)
    error_details = models.JSONField(blank=True, null=True)
    failed_file_details = models.JSONField(blank=True, null=True)
    
    # Queue management
    queue_position = models.IntegerField(default=0, db_index=True)
    file_data = models.JSONField(blank=True, null=True)  # Store file data for queued uploads
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    queued_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    donwload_url = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['queue_position', 'queued_at']
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['order_item', 'upload_type', 'device_type']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'queue_position']),
            models.Index(fields=['upload_type', 'device_type', 'status']),
        ]
    
    def __str__(self):
        return f"Upload {self.task_id} - {self.upload_type}/{self.device_type} - {self.status}"
    
    @property
    def progress_percentage(self):
        if self.total_files == 0:
            return 0
        return (self.uploaded_files / self.total_files) * 100
    
    @property
    def is_completed(self):
        return self.status in ['success', 'partial_success', 'failed']
    
    @property
    def is_queued(self):
        return self.status == 'queued'
    
    @property
    def is_active(self):
        return self.status in ['pending', 'processing']


class OperationalNotice(BaseModel):
    name = models.CharField(max_length=255)
    content1 = models.TextField(null=True, blank=True)
    content2 = models.TextField(null=True, blank=True)
    content3 = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self.active:
            OperationalNotice.objects.filter(active=True).exclude(id=self.id).update(active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

