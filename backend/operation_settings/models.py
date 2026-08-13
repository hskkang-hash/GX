from django.db import models
from common.base_model import BaseModelWithGroup
from core.user.models import CoreUser, UserGroup
from core.menu.models import Menu, Tab
from core.base import BaseModel
class OperationSettings(BaseModel):
    """
    Model for Operation Settings that manage API configurations for different menus and tabs
    """
    
    HTTP_METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH'),
    ]

    # Link to Menu/Tab/Group system
    menu = models.ForeignKey(
        Menu, 
        on_delete=models.CASCADE, 
        related_name='operation_settings',
        help_text="Related menu from core menu system",
        default=None,
        null=True, 
        blank=True
    )
    tab = models.ForeignKey(
        Tab, 
        on_delete=models.CASCADE, 
        related_name='operation_settings',
        help_text="Related tab from core menu system (optional)",
        default=None,
        null=True, 
        blank=True,
    )
    # Basic info
    name = models.CharField(max_length=100, help_text="Name of this operation setting",null=True, blank=True)
    
    # API Configuration
    is_active = models.BooleanField(default=True)
    api_url = models.URLField(max_length=1000,null=True, blank=True)
    http_method = models.CharField(max_length=10, choices=HTTP_METHOD_CHOICES, default='GET',null=True, blank=True)
    
    # Optional fields for advanced configuration
    api_params = models.JSONField(null=True, blank=True, help_text="API parameters in JSON format")
    body_params = models.JSONField(null=True, blank=True, help_text="Body parameters in JSON format")
    expected_response = models.JSONField(null=True, blank=True, help_text="Expected response structure in JSON format")
    timeout_seconds = models.IntegerField(default=30, help_text="API timeout in seconds",null=True, blank=True)
    retry_count = models.IntegerField(default=3, help_text="Number of retries on failure",null=True, blank=True)
    
    # Metadata
    description = models.TextField(null=True, blank=True, help_text="Description of this operation setting")
    notes = models.TextField(null=True, blank=True, help_text="Additional notes")
    receive_data = models.BooleanField(default=False, help_text="Receive data from API")
    send_data = models.BooleanField(default=False, help_text="Send data to API")
    # Tracking
    last_tested_on = models.DateTimeField(null=True, blank=True)
    last_test_status = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = 'Operation Setting'
        verbose_name_plural = 'Operation Settings'
        ordering = ['menu__menu_name', 'tab__name', 'name']

    def __str__(self):
        if self.tab:
            return f"{self.menu.menu_name} - {self.tab.name} - {self.name}"
        return f"{self.menu.menu_name} - {self.name}"

    @property
    def menu_type(self):
        """Backward compatibility property"""
        return self.menu.path.strip('/').replace('/', '_')

    @property
    def step(self):
        """Backward compatibility property"""
        return self.tab.path.split('/')[-1] if self.tab else 'default'


