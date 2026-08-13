from ninja.errors import ValidationError
from ninja_extra import api_controller, route

from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from common.constant import MESSAGE_ENUM, get_message
from task_status.schemas.schemas_djantic_out import TaskStatusOutSchema
from task_status.services.task_status_service import TaskStatusService


@api_controller("/task-status", tags=["Task Status"])
class TaskStatusController:
    """Controller cung cấp API để kiểm tra trạng thái task thông qua task_id"""

    @route.get("/{task_id}", auth=CustomJWTAuth())
    def get_task_status(self, request, task_id: str):
        try:
            task_status = TaskStatusService.get_by_task_id(task_id)
            data = TaskStatusOutSchema.from_queryset(task_status)

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_TASK_STATUS_SUCCESS),
                data=data,
            )
        except ValidationError as exc:
            errors = exc.errors if hasattr(exc, "errors") else str(exc)
            if callable(errors):
                errors = errors()
            return BaseResponse(
                status_code=404,
                success=False,
                message=get_message(MESSAGE_ENUM.GET_TASK_STATUS_FAILED),
                data={"success": False, "errors": errors},
            )
        except Exception as exc:
            return BaseResponse(
                status_code=500,
                success=False,
                message=get_message(MESSAGE_ENUM.GET_TASK_STATUS_FAILED),
                data={"success": False, "errors": str(exc)},
            )

