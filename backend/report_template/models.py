from django.db import models
from core.base import BaseModel


class ReportTemplate(BaseModel):
    name = models.CharField(max_length=255, null=False, blank=False)
    template = models.TextField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    is_enabled = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0)

    class Meta:
        db_table = "report_template"
        verbose_name = "Report Template"
        verbose_name_plural = "Report Templates"

    def __str__(self):
        return f"{self.name}"
