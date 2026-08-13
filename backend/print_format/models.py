from django.db import models
from django.template import Template, Context
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from django.core.cache import cache
from django.conf import settings
from typing import Dict, Any, Optional
import json
from django.contrib.contenttypes.models import ContentType

from core.base import BaseModel
from core.user.models import CoreUser

class PrintFormat(BaseModel):
    name = models.CharField(max_length=255)
    # model_name/models_supported đã bị loại bỏ
    template = models.TextField(null=True, blank=True)
    css = models.TextField(null=True, blank=True)  # Custom CSS
    is_default = models.BooleanField(default=False)
    is_enabled = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0)
    class Meta:
        unique_together = []  # Không enforce unique theo model_name nữa

    def save(self, *args, **kwargs):
        # Nếu template này được đánh dấu là default
        if self.is_default:
            # Tắt default của các template khác cùng model và company
            PrintFormat.objects.filter(
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)

    def render_template(self, instance: models.Model) -> Dict[str, Any]:
        """Render template với dữ liệu thực"""
        from .services import PrintFormatService
        data = PrintFormatService.get_print_format_data(self, instance)

        # Nếu có items trong data, render nhiều template
        template_list = []
        if 'items' in data and data['items']:
            rendered_htmls = []
            for item in data['items']:
                fields_dict = dict(
                    (field['name'], field['value'])
                    for field in item.get('fields', [])
                    if field.get('value')
                )
                context = {
                    'instance': instance,
                    'fields': fields_dict,
                    'data': item
                }
                
                template = Template(self.template)
                rendered_html = template.render(Context(context.get('fields')))
                rendered_htmls.append(rendered_html)
                template_list.append(rendered_html)
        else:
            # Xử lý trường hợp không có items
            fields_dict = dict(
                (field['name'], field['value'])
                for field in data['fields']
                if field.get('value')
            )
            context = {
                'instance': instance,
                'fields': fields_dict,
                'data': data
            }
            
            template = Template(self.template)
            rendered_html = template.render(Context(context.get('fields')))
            template_list.append(rendered_html)
        if self.css:
            rendered_html = f"<style>{self.css}</style>{rendered_html}"
 
        return {
            'html': template_list,
            'data': data
        }

    def get_preview_data(self) -> Dict[str, Any]:
        """Lấy dữ liệu mẫu để preview"""
        # Cache key dựa trên template id
        cache_key = f"print_format_{self.id}_preview"
        
        # Kiểm tra cache
        cached_result = cache.get(cache_key)
        if cached_result:
            return json.loads(cached_result)

        # Lấy model class
        from django.apps import apps
        model = apps.get_model(self.model_name)

        # Lấy instance mẫu (instance đầu tiên)
        instance = model.objects.first()
        if not instance:
            return {'html': '', 'data': {}}

        result = self.render_template(instance)

        # Cache kết quả
        cache.set(cache_key, json.dumps(result), timeout=settings.PRINT_FORMAT_CACHE_TIMEOUT or 3600)

        return result

    def __str__(self):
        return f"{self.name}" 