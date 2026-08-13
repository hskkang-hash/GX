from typing import List, Dict, Any
from core.api.v1.auth import CustomJWTAuth
from ninja import Query
from ninja_extra import api_controller, route
from django.shortcuts import get_object_or_404
from django.apps import apps
from core.base import BaseResponse
from report_template.models import ReportTemplate
from common.constant import MESSAGE_ENUM
from .models import PrintFormat
from .services import PrintFormatService
from print_format.schemas import (
    PrintFormatSchema,
    PrintFormatCreateSchema,
    PrintFormatUpdateSchema,
    ModelFieldSchema,
    PrintFormatPreviewSchema
)
from django.template import Template, Context as DjContext
from datetime import datetime, date
from jinja2 import Environment, BaseLoader
from django.utils.safestring import mark_safe
import re

@api_controller("/print-formats", tags=["Print Formats"])
class PrintFormatController:
    
    @staticmethod
    def render_jinja2_template(template_str: str, context: dict) -> str:
        """Helper method to render Jinja2 template with context"""
        # Create Jinja2 environment
        jinja_env = Environment(loader=BaseLoader())
        
        # Create template from string
        template = jinja_env.from_string(template_str)
        
        # Render with context
        rendered_html = template.render(context)
        
        # Clean up any escaped characters
        rendered_html = re.sub(r'\\"', '"', rendered_html)
        rendered_html = re.sub(r"\\'", "'", rendered_html)
        rendered_html = rendered_html.replace('\\n', ' ')
        rendered_html = rendered_html.replace('\\r', ' ')
        rendered_html = rendered_html.replace('\\t', ' ')
        
        return mark_safe(rendered_html)
    @route.get("/print-formats", response=List[PrintFormatSchema])
    def list_print_formats(self, request):
        return PrintFormatService.get_list_template(request)

    @route.post("", response=PrintFormatSchema)
    def create_print_format(self, request, payload: PrintFormatCreateSchema):
        print_format = PrintFormat.objects.create(
            name=payload.name,
            template=payload.template,
            css=payload.css,
            is_default=payload.is_default,
            is_enabled=payload.is_enabled,
        )
        result = f"<style>{print_format.css}</style>{print_format.template}"
        return BaseResponse(status_code=200,
                            message=MESSAGE_ENUM.get(MESSAGE_ENUM.CREATE_PRINT_FORMAT_SUCCESS),
                            data=result)

    @route.get("/{print_format_id}", response=PrintFormatSchema)
    def get_print_format(self, request, print_format_id: int):
        print_format = PrintFormatService.get_print_format_by_id(print_format_id)
        return BaseResponse(status_code=200,
                            message=MESSAGE_ENUM.get(MESSAGE_ENUM.GET_PRINT_FORMAT_SUCCESS),
                            data=print_format)

    @route.put("/{print_format_id}", response=PrintFormatSchema)
    def update_print_format(self, request, print_format_id: int, payload: PrintFormatUpdateSchema):
        print_format = get_object_or_404(PrintFormat, id=print_format_id)
        for key, value in payload.dict(exclude_unset=True).items():
            setattr(print_format, key, value)
        print_format.save()
        print_format = PrintFormatSchema.from_queryset(print_format)
        return BaseResponse(
            status_code=200,
            message=MESSAGE_ENUM.get(MESSAGE_ENUM.UPDATE_PRINT_FORMAT_SUCCESS),
            data=print_format
        )

    @route.delete("/{print_format_id}")
    def delete_print_format(self, request, print_format_id: str):
        PrintFormatService.delete_print_format(print_format_id)
        return BaseResponse(status_code=200,
                            message=MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                            )

    @route.get("/print-formats/fields/model", response=List[ModelFieldSchema])
    def get_model_fields(self, request, model_name: str = Query(...)):
        fields = PrintFormatService.get_model_fields(model_name)
        if not fields:
            raise ValueError(f"Model {model_name} not found")
        return fields

    @route.get("/print-formats/{print_format_id}/preview", response=PrintFormatPreviewSchema)
    def preview_print_format(self, request, print_format_id: int, instance_id: int, model_name: str = Query(...), language: str = Query('en')):
        print_format = get_object_or_404(PrintFormat, id=print_format_id)
        model = apps.get_model(model_name)
        instance = model.objects.get(id=instance_id)
        context = PrintFormatService.get_print_format_data(print_format, instance, model_name, language)
        try:
            # Use Jinja2 to render template
            rendered_html = self.render_jinja2_template(print_format.template, context)
        except Exception as e:
            print(e)
            template = Template(print_format.template)
            rendered_html = template.render(DjContext(context))
        
        if print_format.css:
            rendered_html = f"<style>{print_format.css}</style>{rendered_html}"
        return BaseResponse(status_code=200,
                            message=MESSAGE_ENUM.get(MESSAGE_ENUM.PREVIEW_PRINT_FORMAT_SUCCESS),
                            data={"html": print_format.template, "data": context})

    @route.get("/print-formats/{print_format_id}/preview/report-template", response=PrintFormatPreviewSchema, auth=CustomJWTAuth())
    def preview_report_template(self, print_format_id: int, instance_id: int, model_name: str = Query(...), language: str = Query('en')):
        report_template = ReportTemplate._base_manager.get(id=print_format_id)
        model = apps.get_model(model_name)
        instance = model._base_manager.get(id=instance_id)
        context = PrintFormatService.get_report_template_data(report_template, instance, model_name, language)
        template_str = PrintFormatService.normalize_template_content(report_template.template)
        
        # Use Jinja2 to render template
        try:
            # Use Jinja2 to render template
            rendered_html = self.render_jinja2_template(template_str, context)
        except Exception as e:
            print(e)
            template = Template(template_str)
            rendered_html = template.render(DjContext(context))
            # Fix escaped quotes in rendered HTML - more comprehensive approach
            from django.utils.safestring import mark_safe
            import re
            
            # Remove all escaped quotes that break CSS
            rendered_html = re.sub(r'\\"', '"', rendered_html)
            rendered_html = re.sub(r"\\'", "'", rendered_html)
            
            # Also fix any remaining escaped characters
            rendered_html = rendered_html.replace('\\n', ' ')
            rendered_html = rendered_html.replace('\\r', ' ')
            rendered_html = rendered_html.replace('\\t', ' ')
            rendered_html = mark_safe(rendered_html)
        return BaseResponse(status_code=200,
                            message=MESSAGE_ENUM.get(MESSAGE_ENUM.PREVIEW_PRINT_FORMAT_SUCCESS),
                            data={"html": template_str, "data": context, "rendered_html": rendered_html})

    @route.post("/print-formats/{print_format_id}/print")
    def print_template(self, request, print_format_id: int, data: Dict[str, Any], language: str = Query('en')):
        """In template với data truyền từ FE với hỗ trợ locale"""
        print_format = get_object_or_404(PrintFormat, id=print_format_id)
        
        # Format datetime fields in data according to locale if needed
        formatted_data = {}
        for key, value in data.items():
            if isinstance(value, (datetime, date)):
                if isinstance(value, datetime):
                    formatted_data[key] = PrintFormatService._format_datetime_by_locale(value, language)
                else:
                    formatted_data[key] = PrintFormatService._format_date_by_locale(value, language)
            else:
                formatted_data[key] = value
        
        try:
            # Use Jinja2 to render template
            rendered_html = self.render_jinja2_template(print_format.template, formatted_data)
        except Exception as e:
            print(e)
            template = Template(print_format.template)
            rendered_html = template.render(DjContext(formatted_data))
        rendered_html = self.render_jinja2_template(print_format.template, formatted_data)
        
        if print_format.css:
            rendered_html = f"<style>{print_format.css}</style>{rendered_html}"
        print_format.usage_count += 1
        print_format.save() 
        return {"html": rendered_html, "data": formatted_data} 
