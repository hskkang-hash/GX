"""
Schemas đầu ra (OUT) cho module Task Status
"""

from typing import Any

from core.common.schema_utils import DynamicSchema

from task_status.models import TaskStatus


class TaskStatusOutSchema(DynamicSchema):
    """Schema đầu ra cho TaskStatus"""

    class Meta:
        model = TaskStatus
        model_fields = [
            "id",
            "task_id",
            "task_type",
            "category",
            "status",
            "message",
            "message_title",
            "message_body",
            "data",
            "payload",
            "progress",
            "related_model",
            "related_object_id",
            "user_id",
            "created_on",
            "modified_on",
            "completed_at",
            "action",
            "task_channel",
            "trigger_source",
            "download_url",
            "file_url",
            "filename",
            "file_id",
            "record_count",
            "error_code",
            "error_details",
        ]

    @classmethod
    def from_queryset(cls, queryset_or_instance, many: bool = False, **kwargs: Any):
        result = super().from_queryset(queryset_or_instance, many=many, **kwargs)

        if many:
            if hasattr(queryset_or_instance, "__iter__"):
                instances = list(queryset_or_instance)
            else:
                instances = [queryset_or_instance]

            for idx, item in enumerate(result):
                instance = instances[idx] if idx < len(instances) else None
                if instance:
                    item["user_username"] = getattr(instance.user, "username", None)
                    item["is_completed"] = instance.is_completed
        else:
            instance = (
                queryset_or_instance.first()
                if hasattr(queryset_or_instance, "first")
                else queryset_or_instance
            )
            if instance:
                result["user_username"] = getattr(instance.user, "username", None)
                result["is_completed"] = instance.is_completed

        return result

