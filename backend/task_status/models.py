from django.db import models
from django.utils import timezone

from core.base import BaseModel
from core.user.models import CoreUser


class TaskStatus(BaseModel):
    """
    Generic task status tracking model for socket-based background operations.
    Designed to support downloads/uploads and other async workflows.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    class Category(models.TextChoices):
        GENERIC = "generic", "Generic"
        DOWNLOAD = "download", "Download"
        UPLOAD = "upload", "Upload"
        MESSAGE = "message", "Message"
        BACKGROUND = "background", "Background Task"

    task_id = models.CharField(max_length=255, unique=True, db_index=True)
    task_type = models.CharField(max_length=255)
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.GENERIC,
    )
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.PENDING,
    )
    action = models.CharField(max_length=255, blank=True, null=True)
    task_channel = models.CharField(max_length=255, blank=True, null=True)
    trigger_source = models.CharField(max_length=255, blank=True, null=True)

    message = models.TextField(blank=True, null=True)
    message_title = models.CharField(max_length=255, blank=True, null=True)
    message_body = models.TextField(blank=True, null=True)

    data = models.JSONField(blank=True, null=True)
    payload = models.JSONField(blank=True, null=True)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    download_url = models.CharField(max_length=1024, blank=True, null=True)
    file_url = models.CharField(max_length=1024, blank=True, null=True)
    filename = models.CharField(max_length=255, blank=True, null=True)
    file_id = models.CharField(max_length=255, blank=True, null=True)
    record_count = models.IntegerField(blank=True, null=True)

    error_code = models.CharField(max_length=100, blank=True, null=True)
    error_details = models.JSONField(blank=True, null=True)

    user = models.ForeignKey(
        CoreUser,
        on_delete=models.CASCADE,
        related_name="task_statuses",
        null=True,
        blank=True,
    )
    related_model = models.CharField(max_length=255, blank=True, null=True)
    related_object_id = models.CharField(max_length=255, blank=True, null=True)

    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_on"]
        indexes = [
            models.Index(fields=["task_id"]),
            models.Index(fields=["task_type", "status"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["user", "status"]),
        ]
        verbose_name = "Task Status"
        verbose_name_plural = "Task Statuses"

    def mark_completed(self):
        if not self.completed_at:
            self.completed_at = timezone.now()

    @property
    def is_completed(self):
        return self.status in {
            self.Status.SUCCESS,
            self.Status.FAILED,
        }

