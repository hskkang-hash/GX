from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import logging

from django.apps import apps
from django.db import transaction
from ninja.errors import ValidationError

from task_status.models import TaskStatus

logger = logging.getLogger(__name__)


class TaskStatusService:
    """
    Service layer for managing TaskStatus records.
    Provides reusable helpers so that all socket-based workflows share the same tracking logic.
    """

    @staticmethod
    @transaction.atomic
    def create_or_update(
        task_id: str,
        task_type: str,
        *,
        user=None,
        category: str = TaskStatus.Category.GENERIC,
        status: str = TaskStatus.Status.PENDING,
        message: Optional[str] = None,
        message_title: Optional[str] = None,
        message_body: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
        progress: Optional[float] = None,
        action: Optional[str] = None,
        task_channel: Optional[str] = None,
        trigger_source: Optional[str] = None,
        download_url: Optional[str] = None,
        file_url: Optional[str] = None,
        filename: Optional[str] = None,
        file_id: Optional[str] = None,
        record_count: Optional[int] = None,
        error_code: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        related_model: Optional[str] = None,
        related_object_id: Optional[str] = None,
    ) -> Tuple[bool, TaskStatus]:
        if not task_id:
            raise ValidationError("task_id is required")
        if not task_type:
            raise ValidationError("task_type is required")

        defaults: Dict[str, Any] = {
            "task_type": task_type,
            "category": category,
            "status": status,
            "message": message,
            "message_title": message_title,
            "message_body": message_body,
            "data": data,
            "payload": payload,
            "related_model": related_model,
            "related_object_id": related_object_id,
            "action": action,
            "task_channel": task_channel,
            "trigger_source": trigger_source,
            "download_url": download_url,
            "file_url": file_url,
            "filename": filename,
            "file_id": file_id,
            "record_count": record_count,
            "error_code": error_code,
            "error_details": error_details,
        }
        if progress is not None:
            defaults["progress"] = progress
        if user is not None:
            defaults["user"] = user

        task_status, _ = TaskStatus.objects.update_or_create(
            task_id=task_id,
            defaults=defaults,
        )

        completion_triggered = (
            status in (TaskStatus.Status.SUCCESS, TaskStatus.Status.FAILED)
            and task_status.completed_at is None
        )
        if status in (TaskStatus.Status.SUCCESS, TaskStatus.Status.FAILED):
            task_status.mark_completed()
            task_status.save(
                update_fields=[
                    "status",
                    "message",
                    "message_title",
                    "message_body",
                    "data",
                    "payload",
                    "progress",
                    "related_model",
                    "related_object_id",
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
                    "completed_at",
                    "modified_on",
                ]
            )

        if completion_triggered:
            transaction.on_commit(
                lambda: TaskStatusService._invalidate_cache_on_completion(task_status.id)
            )

        return True, task_status

    @staticmethod
    @transaction.atomic
    def update_status(
        task_id: str,
        status: str,
        *,
        message: Optional[str] = None,
        message_title: Optional[str] = None,
        message_body: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
        progress: Optional[float] = None,
        action: Optional[str] = None,
        task_channel: Optional[str] = None,
        trigger_source: Optional[str] = None,
        download_url: Optional[str] = None,
        file_url: Optional[str] = None,
        filename: Optional[str] = None,
        file_id: Optional[str] = None,
        related_model: Optional[str] = None,
        related_object_id: Optional[str] = None,
        record_count: Optional[int] = None,
        error_code: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, TaskStatus]:
        if not task_id:
            raise ValidationError("task_id is required")

        try:
            task_status = TaskStatus.objects.get(task_id=task_id)
        except TaskStatus.DoesNotExist:
            raise ValidationError("Task status not found")

        task_status.status = status
        completed_at_changed = False
        if message is not None:
            task_status.message = message
        if message_title is not None:
            task_status.message_title = message_title
        if message_body is not None:
            task_status.message_body = message_body
        if data is not None:
            task_status.data = data
        if payload is not None:
            task_status.payload = payload
        if progress is not None:
            task_status.progress = progress
        if action is not None:
            task_status.action = action
        if task_channel is not None:
            task_status.task_channel = task_channel
        if trigger_source is not None:
            task_status.trigger_source = trigger_source
        if download_url is not None:
            task_status.download_url = download_url
        if file_url is not None:
            task_status.file_url = file_url
        if filename is not None:
            task_status.filename = filename
        if file_id is not None:
            task_status.file_id = file_id
        if record_count is not None:
            task_status.record_count = record_count
        if error_code is not None:
            task_status.error_code = error_code
        if error_details is not None:
            task_status.error_details = error_details
        if related_model is not None:
            task_status.related_model = related_model
        if related_object_id is not None:
            task_status.related_object_id = related_object_id
        if status in (TaskStatus.Status.SUCCESS, TaskStatus.Status.FAILED):
            task_status.mark_completed()
            completed_at_changed = True
        elif status in (TaskStatus.Status.PENDING, TaskStatus.Status.PROCESSING):
            if task_status.completed_at is not None:
                task_status.completed_at = None
                completed_at_changed = True

        update_fields = ["status", "modified_on"]
        if message is not None:
            update_fields.append("message")
        if message_title is not None:
            update_fields.append("message_title")
        if message_body is not None:
            update_fields.append("message_body")
        if data is not None:
            update_fields.append("data")
        if payload is not None:
            update_fields.append("payload")
        if progress is not None:
            update_fields.append("progress")
        if action is not None:
            update_fields.append("action")
        if task_channel is not None:
            update_fields.append("task_channel")
        if trigger_source is not None:
            update_fields.append("trigger_source")
        if download_url is not None:
            update_fields.append("download_url")
        if file_url is not None:
            update_fields.append("file_url")
        if filename is not None:
            update_fields.append("filename")
        if file_id is not None:
            update_fields.append("file_id")
        if record_count is not None:
            update_fields.append("record_count")
        if error_code is not None:
            update_fields.append("error_code")
        if error_details is not None:
            update_fields.append("error_details")
        if completed_at_changed:
            update_fields.append("completed_at")
        if related_model is not None:
            update_fields.append("related_model")
        if related_object_id is not None:
            update_fields.append("related_object_id")
        task_status.save(update_fields=update_fields)

        if status in (TaskStatus.Status.SUCCESS, TaskStatus.Status.FAILED) and completed_at_changed:
            transaction.on_commit(
                lambda: TaskStatusService._invalidate_cache_on_completion(task_status.id)
            )
        return True, task_status

    @staticmethod
    def get_by_task_id(task_id: str) -> TaskStatus:
        if not task_id:
            raise ValidationError("task_id is required")

        try:
            return TaskStatus.objects.select_related("user").get(task_id=task_id)
        except TaskStatus.DoesNotExist:
            raise ValidationError("Task status not found")

    @staticmethod
    def serialize(task_status: TaskStatus) -> Dict[str, Any]:
        return {
            "id": task_status.id,
            "task_id": task_status.task_id,
            "task_type": task_status.task_type,
            "category": task_status.category,
            "status": task_status.status,
            "message": task_status.message,
            "message_title": task_status.message_title,
            "message_body": task_status.message_body,
            "data": task_status.data,
            "payload": task_status.payload,
            "progress": float(task_status.progress),
            "user_id": task_status.user_id,
            "user_username": getattr(task_status.user, "username", None),
            "related_model": task_status.related_model,
            "related_object_id": task_status.related_object_id,
            "action": task_status.action,
            "task_channel": task_status.task_channel,
            "trigger_source": task_status.trigger_source,
            "download_url": task_status.download_url,
            "file_url": task_status.file_url,
            "filename": task_status.filename,
            "file_id": task_status.file_id,
            "record_count": task_status.record_count,
            "error_code": task_status.error_code,
            "error_details": task_status.error_details,
            "created_on": task_status.created_on,
            "modified_on": task_status.modified_on,
            "completed_at": task_status.completed_at,
            "is_completed": task_status.is_completed,
        }

    @staticmethod
    def _invalidate_cache_on_completion(task_status_id: int) -> None:
        try:
            task_status = TaskStatus.objects.get(id=task_status_id)
        except TaskStatus.DoesNotExist:
            return

        if not task_status.is_completed:
            return

        instance = TaskStatusService._resolve_related_instance(task_status)
        if instance is None:
            return

        try:
            from common.selective_cache_optimization import SelectiveCacheInvalidator

            SelectiveCacheInvalidator.selective_invalidate(instance, operation="update", verbose=False)
        except Exception as exc:
            logger.warning(
                "[TASK_STATUS] Cache invalidation failed for task_id=%s (model=%s, object_id=%s): %s",
                task_status.task_id,
                task_status.related_model,
                task_status.related_object_id,
                exc,
            )

    @staticmethod
    def _resolve_related_instance(task_status: TaskStatus):
        model_label, object_id = TaskStatusService._infer_related_model(task_status)
        if not model_label or not object_id:
            return None

        model = TaskStatusService._get_model_from_label(model_label)
        if model is None:
            return None

        try:
            pk_value = model._meta.pk.to_python(object_id)
        except Exception:
            pk_value = object_id

        try:
            return model._base_manager.get(pk=pk_value)
        except model.DoesNotExist:
            return None
        except Exception:
            return None

    @staticmethod
    def _infer_related_model(task_status: TaskStatus) -> Tuple[Optional[str], Optional[str]]:
        if task_status.related_model and task_status.related_object_id:
            return task_status.related_model, str(task_status.related_object_id)

        data = task_status.data if isinstance(task_status.data, dict) else {}

        key_to_model = {
            "route_id": "terminals.Routes",
            "mission_id": "surveillance.SurveyMission",
            "profile_id": "surveillance.SurveillanceProfile",
            "terminal_id": "terminals.Terminal",
        }
        for key, model_label in key_to_model.items():
            value = data.get(key)
            if value is not None:
                return model_label, str(value)

        task_type_hints = {
            "qground_control_import_plan": ("terminals.Routes", "route_id"),
            "survey_mission_import_routes": ("surveillance.SurveyMission", "mission_id"),
            "survey_mission_import_routes_simple": ("surveillance.SurveyMission", "mission_id"),
        }
        hint = task_type_hints.get(task_status.task_type)
        if hint:
            model_label, key = hint
            value = data.get(key)
            if value is not None:
                return model_label, str(value)

        return None, None

    @staticmethod
    def _get_model_from_label(model_label: str):
        if not model_label:
            return None

        if "." in model_label:
            app_label, model_name = model_label.split(".", 1)
            try:
                return apps.get_model(app_label, model_name)
            except Exception:
                return None

        normalized = model_label.lower()
        for model in apps.get_models():
            if model._meta.model_name == normalized or model.__name__ == model_label:
                return model

        return None

