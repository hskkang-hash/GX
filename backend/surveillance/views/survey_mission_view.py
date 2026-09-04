"""
Survey Mission API Controller
RESTful endpoints for survey mission management with approval workflow
"""

import json
import hashlib
import logging
import time
from datetime import datetime
from common.pagination import OptimizedPaginator
from ninja_extra import api_controller, route
from typing import Any, List
from django.http import HttpRequest
from ninja.errors import ValidationError
from django.core.cache import cache

from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from common.tenant_filters import assert_scoped
from surveillance.models import SurveyMission
from core.role.permission import path_permission
from core.common.search.dynamic_search import apply_dynamic_filters
from devices.utils import filter_mensurement
from terminals.views.routes_views import RoutesController
from terminals.utils import calculate_distance_km
from surveillance.models import MissionWaypoint, SurveyMission
from common.constant import MESSAGE_ENUM, get_message

from common.utils import get_waypoint_speed
from surveillance.schemas.schemas_djantic_in import (
    SurveyMissionReviewInSchema,
    SurveyMissionCreateInSchema,
    SurveyMissionUpdateInSchema,
    SurveyMissionApproveInSchema,
    SurveyMissionRejectInSchema,
    SurveyMissionBulkActionInSchema,
    SurveyMissionDroneDivisionInSchema,
    SurveyMissionImportRoutesInSchema,
    SurveyMissionImportRoutesSimpleInSchema,
    SurveyMissionImportQGCInSchema,
)
from surveillance.schemas.schemas_djantic_out import (
    SurveyMissionDetailOutSchema,
    SurveyMissionOutSchema,
    SurveyMissionPreviewOutSchema,
    SurveyMissionDroneDivisionOutSchema,
)
from surveillance.services.survey_mission_service import SurveyMissionService
from surveillance.services.survey_mission_builder_service import SurveyMissionBuilderService
from ninja.files import UploadedFile
from ninja import Schema, Path, Query, Form, File
logger = logging.getLogger(__name__)


@api_controller("/survey-missions", tags=["Survey Missions"])
class SurveyMissionController:
    """Controller for survey mission operations with approval workflow"""
    @route.get("mission/check_permission", auth=CustomJWTAuth())
    # @path_permission("update", path_override="/survey-mission")
    def check_permission(self, request: HttpRequest):
        """
        Kiểm tra xem user có quyền approve không
        Trả về True nếu có bất kỳ role code nào của user nằm trong approve_permission
        """
        group = request.user.userprofilelink.group
        all_roles = request.user.roles.all().values_list('id', flat=True)
        role_permission = group.settings.get('approve_permission', {}).get('roles', [])
        permission_id = {role for role in role_permission if role}
        user_role_id = set(all_roles)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_LIST_SUCCESS),
            data=bool(user_role_id & permission_id)
        )

    @staticmethod
    def check_permission_mission(request):
        group = request.user.userprofilelink.group
        all_roles = request.user.roles.all().values_list('id', flat=True)
        role_permission = group.settings.get('approve_permission', {}).get('roles', [])
        permission_id = {role for role in role_permission if role}
        user_role_id = set(all_roles)
        return bool(user_role_id & permission_id)
    @route.get("", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-mission")
    def list_survey_missions(self, request: HttpRequest):
        """
        Get list of survey missions with dynamic filtering, sorting, and pagination
        """

        page_size = int(request.GET.get('page_size', 25))
        current_page = int(request.GET.get('current_page', 1))
        queryset = SurveyMissionService.get_queryset_optimized()
        queryset = filter_mensurement(queryset, SurveyMission, request)
        result = apply_dynamic_filters(
            queryset,
            request.GET,
            [],
            request.GET.get('sort_obj', None)
        )
        # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
        paginator = OptimizedPaginator(result, page_size)
        pages = paginator.page(current_page)
        data = SurveyMissionOutSchema.from_queryset(pages.object_list, many=True)
        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_LIST_SUCCESS),
            data=data,
            total_pages=paginator.num_pages,
            total_items=paginator.count,
            current_page=current_page
        )

    @route.get("/{survey_mission_id}", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-mission")
    def get_survey_mission(self, request: HttpRequest, survey_mission_id: int):
        """Get survey mission detail"""
        # ★ D-272 — 이 경로는 `MissionWaypoint`(8,877행)의 **부모 경로**다.
        #   자식에 자기 pk 경로가 없다는 것은 안전이 아니다. 부모를 막아야 자식이 안 샌다.
        #   실측(2026-08-28): 남의 미션에 **500**('NoneType' has no 'waypoints')이 나갔다 —
        #   막힌 뒤 죽은 것이지만, 그 500 은 "막혔다"를 말해 주지 않는다.
        assert_scoped(SurveyMission, survey_mission_id, request.user)
        success, result = SurveyMissionService.get_detail(survey_mission_id)

        if not success:
            return BaseResponse(
                status_code=404,
                message=get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_NOT_FOUND),
                data=None
            )

        # Prepare output data
        data = SurveyMissionDetailOutSchema.from_queryset(result, many = False)

        # Lấy danh sách waypoint đã được prefetch sẵn trong service
        waypoints_list = list(result.first().waypoints.all())
        data['line_mission'] = any(waypoint.terminal_id for waypoint in waypoints_list) and not result.first().from_route

        serialized_waypoints = []
        measurements_cache = {}
        for waypoint in waypoints_list:
            # Lấy measurements từ prefetch cache hoặc query trực tiếp
            cached_measurements = getattr(waypoint, '_prefetched_objects_cache', {}).get('measurements')
            if cached_measurements is None:
                # Nếu không có trong cache, query trực tiếp
                cached_measurements = waypoint.measurements.filter(
                    measurement_type__in=['cruise_speed', 'operating_altitude']
                )
            else:
                # Nếu có trong cache, filter lại để chỉ lấy cruise_speed và operating_altitude
                cached_measurements = [m for m in cached_measurements if m.measurement_type in ['cruise_speed', 'operating_altitude']]

            measurement_map = {m.measurement_type: m for m in cached_measurements}
            measurements_cache[waypoint.id] = measurement_map

            cruise_speed_measurement = measurement_map.get('cruise_speed')
            operating_altitude_measurement = measurement_map.get('operating_altitude')

            serialized_waypoints.append({
                "id": waypoint.id,
                "order": waypoint.order,
                "name": waypoint.name,
                "latitude": waypoint.latitude,
                "longitude": waypoint.longitude,
                "command_line": waypoint.command_line,
                "frame": waypoint.frame,
                "note": waypoint.note,
                "created_on": waypoint.created_on,
                "modified_on": waypoint.modified_on,
                "terminal_id": waypoint.terminal_id,
                "cruise_speed": cruise_speed_measurement.get_formatted_value() if cruise_speed_measurement else None,
                "operating_altitude": operating_altitude_measurement.get_formatted_value() if operating_altitude_measurement else None,
            })

        data['all_waypoints'] = serialized_waypoints

                    # Chỉ lấy waypoint với command nằm trong danh sách cho phép để vẽ biểu đồ

        allowed_command_ids = {16, 21, 17, 18, 19, 31, 192, 195, 22, 186, 20}
        chart_entries = []
        routes_controller = RoutesController()

        for index, waypoint in enumerate(waypoints_list):
            # Skip waypoint if command id not allowed
            if waypoint.command_line:
                # command_line format: {"21": {"NAV_LAND": ["0", "0", ...]}}
                command_id_str = next(iter(waypoint.command_line.keys()), None)
                try:
                    command_id = int(command_id_str) if command_id_str else None
                except ValueError:
                    command_id = None
                if command_id is not None and command_id not in allowed_command_ids:
                    continue
            measurement_map = measurements_cache.get(waypoint.id, {})
            cruise_speed_measurement = measurement_map.get('cruise_speed')
            cruise_speed_value = cruise_speed_measurement.get_numeric_value(user_units='m/s') if cruise_speed_measurement else 0

            distance = 0
            if index > 0:
                prev_waypoint = waypoints_list[index - 1]
                current_waypoint = waypoint
                distance = calculate_distance_km(
                    prev_waypoint.latitude,
                    prev_waypoint.longitude,
                    current_waypoint.latitude,
                    current_waypoint.longitude
                )

            raw_command_line = waypoint.command_line
            operating_altitude = routes_controller.extract_altitude_from_command_line(raw_command_line)

            chart_entries.append({
                "name": waypoint.name,
                "cruise_speed": round(float(cruise_speed_value or 0), 2),
                "operating_altitude": operating_altitude,
                "order": waypoint.order,
                "distance": round(distance, 2)
            })

        data['chart_data'] = chart_entries

        return BaseResponse(
            status_code=200,
            message="Survey mission retrieved successfully",
            data=data
        )


    @route.post("/mission/review-mission", auth=CustomJWTAuth())
    @path_permission("create", path_override="/survey-mission")
    def review_survey_mission(self, request: HttpRequest, data: SurveyMissionReviewInSchema):
        """
        Review survey mission without creating
        Returns QGC JSON file data for testing/download
        FE can use this to download .plan file before creating mission

        Request body only requires survey parameters (polygon + optional settings)
        No mission metadata needed (name, group, purpose, etc.)
        """
        payload_dict = data.dict()
        payload_str = json.dumps(payload_dict, sort_keys=True, separators=(",", ":"), default=str)

        user = getattr(request, "user", None)
        user_id = getattr(user, "id", "anonymous") if user else "anonymous"

        group_id = "no_group"
        if user:
            try:
                user_group_link = user.userprofilelink
                if user_group_link:
                    group_id = getattr(user_group_link, "group_id", "no_group") or "no_group"
            except Exception:
                group_id = "no_group"

        cache_key = "survey_mission_review:user:{user_id}:group:{group}:payload:{hash_value}".format(
            user_id=user_id,
            group=group_id,
            hash_value=hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        )

        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return BaseResponse(
                status_code=200,
                message="QGC mission file generated successfully",
                data=cached_result
            )

        success, result = SurveyMissionService.review(
            polygon=data.polygon,
            altitude=data.altitude,
            survey_angle=data.survey_angle,
            frontal_overlap=data.frontal_overlap,
            side_overlap=data.side_overlap,
            entry_location=data.entry_location,
            cruise_speed=data.cruise_speed if data.cruise_speed is not None else get_waypoint_speed(),
            hover_speed=data.hover_speed,
            spacing=data.spacing,
            trigger_distance=data.trigger_distance,
            turnaround_distance=data.turnaround_distance,
            review=data.review,
            # QGC Survey Options (default to False if not provided)
            hover_and_capture=data.hover_and_capture if hasattr(data, 'hover_and_capture') else False,
            refly_90_degrees=data.refly_90_degrees if hasattr(data, 'refly_90_degrees') else False,
            camera_trigger_in_turnaround=data.camera_trigger_in_turnaround if hasattr(data, 'camera_trigger_in_turnaround') else False,
        )

        if not success:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.MESSAGE_OPERATION_FAILED),
                data={"error": result}
            )

        cache.set(cache_key, result, timeout=60 * 10)

        return BaseResponse(
            status_code=200,
            message="QGC mission file generated successfully",
            data=result
        )

    @route.post("", auth=CustomJWTAuth())
    @path_permission("create", path_override="/survey-mission")
    def create_survey_mission(self, request: HttpRequest, data: SurveyMissionCreateInSchema):
        """Create new survey mission (status = pending_approval)"""
        success, result = SurveyMissionService.create(
            name=data.name,
            maximum_drones=data.maximum_drones,
            purpose_id=data.purpose_id,
            polygon=data.polygon,
            region=data.region,
            altitude=data.altitude if data.altitude is not None else 150.0,
            takeoff_altitude=data.takeoff_altitude,
            altitude_separation=data.altitude_separation,
            terminals=[t.dict() for t in data.terminals] if data.terminals else None,  # Convert schema to dict
            survey_angle=data.survey_angle or 0,
            frontal_overlap=data.frontal_overlap or 70,
            side_overlap=data.side_overlap or 70,
            entry_location=data.entry_location or 1,
            cruise_speed=data.cruise_speed if data.cruise_speed is not None else get_waypoint_speed(),
            hover_speed=data.hover_speed or 5.0,
            log_collection=data.log_collection or False,
            video_recording=data.video_recording or False,
            video_analysis=data.video_analysis or False,
            note=data.note,
            spacing=data.spacing,
            trigger_distance=data.trigger_distance,
            turnaround_distance=data.turnaround_distance,
            hover_and_capture=data.hover_and_capture or False,
            refly_90_degrees=data.refly_90_degrees or False,
            camera_trigger_in_turnaround=data.camera_trigger_in_turnaround or False,
            action_commands=[cmd.dict() for cmd in data.action_commands] if data.action_commands else None,
            total_distance=data.total_distance,
            estimated_time=data.estimated_time
        )

        if not success:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.MESSAGE_OPERATION_FAILED),
                data={"error": result}
            )

        # Prepare output data
        output_data = SurveyMissionOutSchema.from_queryset(result, many = False)


        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_CREATED),
            data=output_data
        )

    @route.put("/{survey_mission_id}", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-mission")
    def update_survey_mission(
        self, request: HttpRequest, survey_mission_id: int, data: SurveyMissionUpdateInSchema
    ):
        """
        Update survey mission
        Auto resubmit (reset to pending_approval) if params changed
        """
        success, result = SurveyMissionService.update(
            survey_mission_id=survey_mission_id,
            name=data.name,
            maximum_drones=data.maximum_drones,
            purpose_id=data.purpose_id,
            polygon=data.polygon,
            region=data.region,
            altitude=data.altitude,
            takeoff_altitude=data.takeoff_altitude,
            altitude_separation=data.altitude_separation,
            terminals=[t.dict() for t in data.terminals] if data.terminals else None,  # Convert schema to dict
            survey_angle=data.survey_angle,
            frontal_overlap=data.frontal_overlap,
            side_overlap=data.side_overlap,
            entry_location=data.entry_location,
            cruise_speed=data.cruise_speed,
            hover_speed=data.hover_speed,
            log_collection=data.log_collection,
            video_recording=data.video_recording,
            video_analysis=data.video_analysis,
            note=data.note,
            spacing=data.spacing,
            trigger_distance=data.trigger_distance,
            turnaround_distance=data.turnaround_distance,
            total_distance=data.total_distance,
            estimated_time=data.estimated_time,
            action_commands=[cmd.dict() for cmd in data.action_commands] if data.action_commands else None,
            hover_and_capture=data.hover_and_capture or False,
        )

        if not success:
            return BaseResponse(
                status_code=400 if result != "Survey mission not found" else 404,
                message=get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_NOT_FOUND) if result == "Survey mission not found" else get_message(MESSAGE_ENUM.MESSAGE_OPERATION_FAILED),
                data={"error": result} if result != "Survey mission not found" else None
            )

        # Prepare output data
        output_data = SurveyMissionOutSchema.from_queryset(result, many=False)


        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_UPDATED),
            data=output_data
        )

    @route.post("/{survey_mission_id}/approve", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-mission")
    def approve_mission(
        self, request: HttpRequest, survey_mission_id: int
    ):
        """Approve survey mission"""
        if not self.check_permission_mission(request):
            return BaseResponse(
                status_code=403,
                message=get_message(MESSAGE_ENUM.MESSAGE_PERMISSION_DENIED),
                data={"error": get_message(MESSAGE_ENUM.MESSAGE_PERMISSION_DENIED)}
            )

        success, result = SurveyMissionService.approve(
            survey_mission_id=survey_mission_id,
            user=request.user,
        )

        if not success:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.MESSAGE_OPERATION_FAILED),
                data={"error": result}
            )

        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_APPROVED),
            data=SurveyMissionOutSchema.from_queryset(result, many=False)
        )

    @route.post("/{survey_mission_id}/reject", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-mission")
    def reject_mission(
        self, request: HttpRequest, survey_mission_id: int, data: SurveyMissionRejectInSchema
    ):
        """Reject survey mission with reason"""
        if not self.check_permission_mission(request):
            return BaseResponse(
                status_code=403,
                message=get_message(MESSAGE_ENUM.MESSAGE_PERMISSION_DENIED),
                data={"error": get_message(MESSAGE_ENUM.MESSAGE_PERMISSION_DENIED)}
            )
        success, result = SurveyMissionService.reject(
            survey_mission_id=survey_mission_id,
            user=request.user,
            reason=data.reason
        )

        if not success:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.MESSAGE_OPERATION_FAILED),
                data={"error": result}
            )

        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_REJECTED),
            data=SurveyMissionOutSchema.from_queryset(result, many=False)
        )

    @route.post("/activate/{ids}", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-mission")
    def activate_missions(self, request: HttpRequest, ids: str):
        """Activate multiple missions (bulk action)"""
        success, result = SurveyMissionService.activate_missions(ids)

        if not success:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.ACTION_ACTIVATE_FAILED),
                data={"error": result}
            )

        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS),
            data=None
        )

    @route.post("/deactivate/{ids}", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-mission")
    def deactivate_missions(self, request: HttpRequest, ids: str):
        """Deactivate multiple missions (bulk action)"""
        success, result = SurveyMissionService.deactivate_missions(ids)

        if not success:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.ACTION_DEACTIVATE_FAILED),
                data={"error": result}
            )

        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS),
            data=None
        )

    @route.post("/mission/import-plan", auth=CustomJWTAuth())
    @path_permission("create", path_override="/survey-mission")
    def import_survey_mission_from_plan(self, request: HttpRequest, file: UploadedFile = File(...)):
        """
        Import survey mission from QGC plan file

        Args:
            data: Schema chứa file .plan và thông tin import

        Returns:
            SurveyMission được tạo từ file .plan
        """
        try:
            # Import survey mission from plan file
            success, result = SurveyMissionService.import_plan_file(
                plan_file=file,
                group_id=request.user.userprofilelink.group.id
            )

            if not success:
                return BaseResponse(
                    status_code=400,
                    message=get_message(MESSAGE_ENUM.MESSAGE_OPERATION_FAILED),
                    data={"error": result},
                    success=False
                )

            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_CREATED),
            )

        except Exception as e:
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.MESSAGE_OPERATION_FAILED),
                data={"error": str(e)},
                success=False
            )

    @route.post("/mission/import-routes", auth=CustomJWTAuth())
    @path_permission("create", path_override="/survey-mission")
    def import_routes_to_mission(self, request: HttpRequest, data: SurveyMissionImportRoutesInSchema):
        """
        Import nhiều route thành 1 mission (Background Job)
        Tất cả RouteTerminal từ các route sẽ được chuyển thành MissionWaypoint
        Polygon sẽ được detect tự động từ tất cả RouteTerminal

        Chạy ngầm để tránh timeout khi xử lý số lượng lớn.
        Sử dụng task_id để check status qua API /mission/import-status/{task_id}

        Args:
            data: SurveyMissionImportRoutesInSchema chứa route_ids và thông số mission

        Returns:
            task_id để check status
        """
        try:
            import threading
            import uuid
            from surveillance.tasks import _process_import_routes_in_thread
            from task_status.models import TaskStatus
            from task_status.services.task_status_service import TaskStatusService

            # Generate unique task ID for import tracking
            import_task_id = str(uuid.uuid4())
            task_type = "survey_mission_import_routes"

            # Persist initial task status for client-side polling
            pending_message = get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_IMPORT_STARTED)
            TaskStatusService.create_or_update(
                task_id=import_task_id,
                task_type=task_type,
                category=TaskStatus.Category.BACKGROUND,
                user=request.user,
                status=TaskStatus.Status.PENDING,
                message=pending_message,
                action='survey_mission_import_routes',
                task_channel=f'survey_mission_{request.user.username}',
                trigger_source='survey.mission.import_routes',
                related_model='surveillance.SurveyMission',
                payload=data.dict(),
            )

            # Start background thread for import processing
            import_thread = threading.Thread(
                target=_process_import_routes_in_thread,
                args=(
                    data.name,
                    data.purpose_id,
                    data.route_ids,
                    request.user.id,
                    import_task_id,
                    data.altitude if data.altitude is not None else 150.0,
                    data.takeoff_altitude,
                    data.altitude_separation,
                    data.survey_angle or 0.0,
                    data.frontal_overlap or 70.0,
                    data.side_overlap or 70.0,
                    data.entry_location or 1,
                    data.cruise_speed if data.cruise_speed is not None else get_waypoint_speed(),
                    data.hover_speed or 5.0,
                    data.log_collection or False,
                    data.video_recording or False,
                    data.video_analysis or False,
                    data.note,
                    data.spacing,
                    data.trigger_distance,
                    data.turnaround_distance,
                    data.hover_and_capture or False,
                    data.refly_90_degrees or False,
                    data.camera_trigger_in_turnaround or False,
                    [cmd.dict() for cmd in data.action_commands] if data.action_commands else None,
                    data.total_distance,
                    data.estimated_time,
                ),
                daemon=True
            )
            import_thread.start()

            return BaseResponse(
                status_code=200,
                message=pending_message,
                data={
                    'task_id': import_task_id,
                    'status': 'pending',
                    'message': pending_message
                }
            )

        except Exception as e:
            logger.error(f"Error starting import routes to mission task: {str(e)}")
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.MESSAGE_OPERATION_FAILED),
                data={"error": str(e)},
                success=False
            )

    @route.post("/mission/import-routes-simple", auth=CustomJWTAuth())
    @path_permission("create", path_override="/survey-mission")
    def import_routes_to_mission_simple(self, request: HttpRequest, data: SurveyMissionImportRoutesSimpleInSchema):
        """
        Import nhiều route thành 1 mission (Simple mode - Background Job)
        - Chỉ tạo polygon bao bọc các route (không tính toán survey grid)
        - Số lượng MissionWaypoint = số lượng RouteTerminal
        - Vị trí và thứ tự theo route_ids truyền vào (ví dụ: [102, 103, 101] → bay từ 102 → 103 → 101)
        - Tất cả thông số waypoint lấy từ RouteTerminal
        - Chỉ thông số mission level lấy từ schema hoặc default

        Chạy ngầm để tránh timeout khi xử lý số lượng lớn.
        Sử dụng task_id để check status qua API /mission/import-status/{task_id}

        Args:
            data: SurveyMissionImportRoutesSimpleInSchema chứa route_ids và thông số mission

        Returns:
            task_id để check status
        """
        try:
            import threading
            import uuid
            from surveillance.tasks import _process_import_routes_simple_in_thread
            from task_status.models import TaskStatus
            from task_status.services.task_status_service import TaskStatusService

            # Generate unique task ID for import tracking
            import_task_id = str(uuid.uuid4())
            task_type = "survey_mission_import_routes_simple"

            # Persist initial task status for client-side polling
            pending_message = get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_IMPORT_STARTED)
            TaskStatusService.create_or_update(
                task_id=import_task_id,
                task_type=task_type,
                category=TaskStatus.Category.BACKGROUND,
                user=request.user,
                status=TaskStatus.Status.PENDING,
                message=pending_message,
                action='survey_mission_import_routes_simple',
                task_channel=f'survey_mission_{request.user.username}',
                trigger_source='survey.mission.import_routes_simple',
                related_model='surveillance.SurveyMission',
            )

            # Start background thread for import processing
            import_thread = threading.Thread(
                target=_process_import_routes_simple_in_thread,
                args=(
                    data.name,
                    data.purpose_id,
                    data.route_ids,
                    request.user.id,
                    import_task_id,
                    data.altitude if data.altitude is not None else 150.0,
                    data.takeoff_altitude,
                    data.altitude_separation,
                    data.cruise_speed if data.cruise_speed is not None else get_waypoint_speed(),
                    data.hover_speed or 5.0,
                    data.log_collection or False,
                    data.video_recording or False,
                    data.video_analysis or False,
                    data.note,
                    data.total_distance,
                    data.estimated_time
                ),
                daemon=True
            )
            import_thread.start()

            return BaseResponse(
                status_code=200,
                message=pending_message,
                data={
                    'task_id': import_task_id,
                    'status': 'pending',
                    'message': pending_message
                }
            )

        except Exception as e:
            logger.error(f"Error starting import routes to mission simple task: {str(e)}")
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.MESSAGE_OPERATION_FAILED),
                data={"error": str(e)},
                success=False
            )

    @route.get("/mission/import-status/{task_id}", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-mission")
    def get_import_routes_status(self, request: HttpRequest, task_id: str):
        """
        Check status của import routes task (sử dụng TaskStatus model)

        Args:
            task_id: Task ID từ response của import-routes hoặc import-routes-simple

        Returns:
            Task status với progress và result (nếu completed)
        """
        try:
            from task_status.services.task_status_service import TaskStatusService
            from task_status.schemas.schemas_djantic_out import TaskStatusOutSchema

            # Lấy TaskStatus từ database
            task_status = TaskStatusService.get_by_task_id(task_id)

            # Serialize TaskStatus
            response_data = TaskStatusService.serialize(task_status)

            # Nếu SUCCESS và có mission_id, lấy thông tin mission
            if task_status.status == 'success' and task_status.data and task_status.data.get('mission_id'):
                mission_id = task_status.data.get('mission_id')
                try:
                    mission = SurveyMissionService.get_by_id(mission_id)
                    if mission:
                        mission_data = SurveyMissionOutSchema.from_queryset(mission, many=False)
                        response_data['mission'] = mission_data
                except Exception as e:
                    logger.warning(f"Could not fetch mission {mission_id}: {str(e)}")

            return BaseResponse(
                status_code=200,
                message="Task status retrieved successfully",
                data=response_data
            )

        except ValidationError as e:
            logger.error(f"Validation error retrieving import routes task status: {str(e)}")
            return BaseResponse(
                status_code=404,
                message="Task status not found",
                data={'error': str(e), 'task_id': task_id},
                success=False
            )
        except Exception as e:
            logger.error(f"Error retrieving import routes task status: {str(e)}")
            return BaseResponse(
                status_code=500,
                message="Error retrieving task status",
                data={'error': str(e), 'task_id': task_id},
                success=False
            )
    @route.post("/mission/duplicate", auth=CustomJWTAuth())
    def import_from_qgc_calculated_data(self, request: HttpRequest, data: SurveyMissionImportQGCInSchema):
        """
        Import survey mission từ QGC calculated data với drone_missions

        Nhận vào data đã được tính toán từ QGC với:
        - drone_missions: List các drone mission với QGC structure
        - survey_config: Config của survey
        - polygon: Polygon coordinates

        Tự động:
        - Parse QGC items thành waypoints
        - Tạo drone_segments từ drone_missions
        - Đảm bảo số lượng waypoint bằng số lượng items có coordinate
        - Build QGC file đúng format
        """
        try:


            # Override group_id nếu có trong request
            if data.group_id:
                group_id = data.group_id

            # Call service method
            success, result = SurveyMissionService.import_from_qgc_calculated_data(
                name=data.name,
                purpose_id=data.purpose_id,
                polygon=data.polygon,
                drone_missions=data.drone_missions,
                maximum_drones=data.maximum_drones,
                survey_config=data.survey_config,
                survey_id=data.survey_id,
                color=data.color,
                total_distance=data.total_distance,
                total_distance_km=data.total_distance_km,
                estimated_time=data.estimated_time,
                log_collection=data.log_collection,
                video_recording=data.video_recording,
                video_analysis=data.video_analysis,
                from_route=data.from_route,
                note=data.note,
                group_id=group_id,
            )

            if success:
                # Serialize result
                from surveillance.schemas.schemas_djantic_out import SurveyMissionDetailOutSchema
                mission_data = SurveyMissionDetailOutSchema.from_orm(result)

                return BaseResponse(
                    status_code=200,
                    message=get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_CREATED),
                    data=mission_data.dict()
                )
            else:
                return BaseResponse(
                    status_code=400,
                    message=get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_IMPORT_FAILED),
                    success=False,
                    data={"error": str(result)}
                )

        except ValidationError as e:
            return BaseResponse(
                status_code=400,
                message=str(e),
                success=False
            )
        except Exception as e:
            logger.exception(f"Error importing QGC calculated data: {str(e)}")
            return BaseResponse(
                status_code=400,
                message=get_message(MESSAGE_ENUM.MESSAGE_SURVEY_MISSION_IMPORT_FAILED),
                success=False,
                data={"error": str(e)}
            )


    @route.delete("mission/{survey_mission_ids}", auth=CustomJWTAuth())
    @path_permission("delete", path_override="/survey-mission")
    def delete_survey_mission(self, request: HttpRequest, survey_mission_ids: str):
        """Delete survey mission"""
        success, result = SurveyMissionService.delete(survey_mission_ids.split(","))

        if not success:
            return BaseResponse(
                status_code=404 if result == "Survey mission not found" else 400,
                message=get_message(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                data={"error": result}
            )

        return BaseResponse(
            status_code=200,
            message=get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
            data=None
        )

    @route.post("/export/{mission_ids}", auth=CustomJWTAuth())
    def export_survey_missions(self, request: HttpRequest, mission_ids:str):
        """
        Export multiple survey missions to ZIP file

        Args:
            mission_ids: List of survey mission IDs to export

        Returns:
            ZIP file containing .plan files for each mission
        """
        try:
            # Validate mission IDs
            if not mission_ids:
                return BaseResponse(
                    status_code=400,
                    message=get_message(MESSAGE_ENUM.MESSAGE_INVALID_INPUT),
                    data={"error": "Mission IDs list cannot be empty"}
                )

            # Export missions to ZIP
            success, result = SurveyMissionService.export_survey_missions_to_plans(mission_ids, create_zip=True)

            if not success:
                return BaseResponse(
                    status_code=400,
                    message=get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED),
                    data={"error": result}
                )

            # Create filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"survey_missions_export_{timestamp}.zip"

            # Return ZIP file
            from django.http import HttpResponse
            response = HttpResponse(result.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except Exception as e:
            logger.error(f"Error exporting survey missions: {str(e)}")
            return BaseResponse(
                status_code=500,
                message=get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED),
                data={"error": str(e)}
            )

    @route.post("mission/drone-division/{survey_mission_id}", auth=CustomJWTAuth())
    @path_permission("read")
    def create_drone_division_from_mission(self, request: HttpRequest, survey_mission_id: int):
        """
        Tạo mission chia cho nhiều drone từ survey mission có sẵn

        Args:
            survey_mission_id: ID của survey mission

        Returns:
            SurveyMissionDroneDivisionOutSchema: Thông tin mission chia cho drone

        Note:
            Các thông số khác được lấy từ mission measurements:
            - altitude: từ measurement 'altitude' (m)
            - survey_angle: từ measurement 'survey_angle' (°)
            - trigger_distance: từ measurement 'trigger_distance' (m)
            - spacing: từ measurement 'spacing' (m)
            - turnaround_distance: từ measurement 'turnaround_distance' (m)
            - frontal_overlap: từ measurement 'frontal_overlap' (%)
            - side_overlap: từ measurement 'side_overlap' (%)
            - cruise_speed: từ qgc_mission_data.mission.cruiseSpeed (m/s)
            - hover_speed: từ qgc_mission_data.mission.hoverSpeed (m/s)
        """
        try:
            # 1. Lấy survey mission từ database
            try:
                survey_mission = SurveyMission.objects.get(id=survey_mission_id)
            except SurveyMission.DoesNotExist:
                return BaseResponse(
                    status_code=404,
                    message=get_message(MESSAGE_ENUM.MESSAGE_NOT_FOUND),
                    success=False
                )

            # 2. Kiểm tra mission có polygon không
            if not survey_mission.polygon:
                return BaseResponse(
                    status_code=400,
                    message="Survey mission không có polygon để tạo drone division",
                    success=False
                )

            # 3. Lấy tham số từ mission hoặc từ request
            maximum_drones = survey_mission.maximum_drones
            if not maximum_drones or maximum_drones < 1:
                maximum_drones = 1

            # 4. Lấy các thông số từ mission measurements
            from devices.utils import get_numeric_value

            altitude_measurement = survey_mission.get_measurement('altitude')
            altitude = get_numeric_value(altitude_measurement) if altitude_measurement else 100.0

            survey_angle_measurement = survey_mission.get_measurement('survey_angle')
            survey_angle = get_numeric_value(survey_angle_measurement) if survey_angle_measurement else 0.0

            trigger_distance_measurement = survey_mission.get_measurement('trigger_distance')
            trigger_distance = get_numeric_value(trigger_distance_measurement) if trigger_distance_measurement else 25.0

            spacing_measurement = survey_mission.get_measurement('spacing')
            spacing = get_numeric_value(spacing_measurement) if spacing_measurement else 30.0

            turnaround_distance_measurement = survey_mission.get_measurement('turnaround_distance')
            turnaround_distance = get_numeric_value(turnaround_distance_measurement) if turnaround_distance_measurement else 60.96

            frontal_overlap_measurement = survey_mission.get_measurement('frontal_overlap')
            frontal_overlap = get_numeric_value(frontal_overlap_measurement) if frontal_overlap_measurement else 70.0

            side_overlap_measurement = survey_mission.get_measurement('side_overlap')
            side_overlap = get_numeric_value(side_overlap_measurement) if side_overlap_measurement else 70.0

            # 5. Lấy thông số từ qgc_mission_data nếu có
            default_cruise_speed = get_waypoint_speed()
            cruise_speed = default_cruise_speed
            hover_speed = 5.0    # Default
            entry_location = 1   # Default

            if survey_mission.qgc_mission_data and 'mission' in survey_mission.qgc_mission_data:
                mission_data = survey_mission.qgc_mission_data['mission']
                cruise_speed = mission_data.get('cruiseSpeed', default_cruise_speed)
                hover_speed = mission_data.get('hoverSpeed', 5.0)

            # 6. Khởi tạo builder service
            builder = SurveyMissionBuilderService()

            # 7. Lấy danh sách device active từ database
            from devices.models import Device
            available_devices = list(Device.objects.filter(
                active=True,
                main_type__name__icontains='drone'  # Chỉ lấy device có type là drone
            ).values('id', 'name', 'serial_number')[:maximum_drones])

            # 8. Tạo drone division mission
            result = builder.build_survey_mission_with_drone_division(
                polygon=survey_mission.polygon,
                altitude=altitude,
                maximum_drones=maximum_drones,
                survey_angle=survey_angle,
                trigger_distance=trigger_distance,
                spacing=spacing,
                turnaround_distance=turnaround_distance,
                frontal_overlap=frontal_overlap,
                side_overlap=side_overlap,
                entry_location=entry_location,
                cruise_speed=cruise_speed,
                hover_speed=hover_speed,
                return_to_home=bool(getattr(survey_mission, "return_to_home", True)),
                available_devices=available_devices,
            )

            # 8. Trả về kết quả
            return BaseResponse(
                status_code=200,
                message=get_message(MESSAGE_ENUM.ADD_RECORD_TO_GROUP_SUCCESS),
                data=result
            )

        except Exception as e:
            logger.error(f"Error creating drone division: {str(e)}")
            return BaseResponse(
                status_code=500,
                message=get_message(MESSAGE_ENUM.MESSAGE_OPERATION_FAILED),
                success=False
            )
