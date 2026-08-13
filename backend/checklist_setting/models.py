from django.db import models
from core.base import BaseModel
from core.base import BaseModelWithGroup 

# Create your models here.
class ChecklistSetting(BaseModelWithGroup):
    item_name = models.CharField(max_length=255)
    category = models.ForeignKey(
        "ChecklistSettingCategory",
        on_delete=models.CASCADE,
        related_name="checklist_settings",
    )
    TRANSLATABLE_FIELDS = ["item_name"]
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_on"]
        db_table = "checklist_setting"
        verbose_name = "Checklist Setting"
        verbose_name_plural = "Checklist Settings"

    def __str__(self):
        return f"{self.item_name} - {self.category}"


class ChecklistSettingCategory(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255, unique=True)

    TRANSLATABLE_FIELDS = ["name"]

    class Meta:
        ordering = ["-created_on"]
        db_table = "checklist_setting_category"
        verbose_name = "Checklist Setting Category"
        verbose_name_plural = "Checklist Setting Categories"

    def __str__(self):
        return str(self.name)
