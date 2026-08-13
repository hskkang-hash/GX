from django.db import models
from core.base import BaseModelWithGroup
from core.user.models import CoreUser


# Create your models here.
class Partner(BaseModelWithGroup):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255, unique=True)
    api_key = models.CharField(max_length=255, unique=True)
    refresh_token = models.CharField(max_length=512, unique=True, null=True, blank=True)
    refresh_token_expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    expired_at = models.DateTimeField(null=True, blank=True) #by days
    api_callback_url = models.JSONField(null=True, blank=True)
    expired_days = models.IntegerField(null=True, blank=True)
    service_key = models.CharField(max_length=255, null=True, blank=True)
    # Link to existing CoreUser system for authentication
    proxy_user = models.OneToOneField(
        CoreUser,
        on_delete=models.CASCADE,
        related_name='partner_profile',
        null=True,  # Allow existing partners without proxy_user
        blank=True
    )

    class Meta:
        ordering = ["-created_on"]
        verbose_name = "Partner"
        verbose_name_plural = "Partners"

    def __str__(self):
        return f"{self.name} ({self.code})"
