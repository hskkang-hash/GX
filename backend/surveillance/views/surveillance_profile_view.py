import json
import logging
import time
from datetime import date, datetime
from typing import Any, Dict, Optional
from dateutil import parser as date_parser
import pytz

from django.core.paginator import EmptyPage
from common.pagination import OptimizedPaginator
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from ninja.errors import ValidationError
from ninja_extra import api_controller, route

from core.api.v1.auth import CustomJWTAuth
from core.common.base_response import BaseResponse
from core.common.search.dynamic_search import apply_dynamic_filters
from core.common.schema_utils import DynamicSchema
from core.role.permission import path_permission
from surveillance.services.video_analysis_service import VideoAnalysisService
from flight_log.services.flight_log_service import FlightLogService
from stream_monitors.utils.minio_client import minio_client
from common.tenant_filters import assert_scoped
from surveillance.models import SurveillanceProfile, VideoAnalysis
from terminals.utils import calculate_distance_km
from terminals.views.routes_views import RoutesController
from common.constant import MESSAGE_ENUM, get_message
from config import settings

from surveillance.services.surveillance_profile_service import SurveillanceProfileService
from surveillance.schemas.schemas_djantic_in import (
    SurveillanceProfileApproveInSchema,
    SurveillanceProfileCancelInSchema,
    SurveillanceProfileChangeDroneInSchema,
    SurveillanceProfileCheckCompleteInSchema,
    SurveillanceProfileCreateInSchema,
    SurveillanceProfileDroneFlightMarkInSchema,
    SurveillanceProfileRejectInSchema,
    SurveillanceProfileUpdateInSchema,
)
from surveillance.schemas.schemas_djantic_out import (
    SurveillanceProfileOutSchema,
    SurveillanceProfileSelectedOutSchema,
    SurveillanceProfileTimelineDroneOutSchema,
    SurveillanceProfileTimelineOutSchema,
    SurveillanceProfileTimelineProfileOutSchema,
    SurveillanceProfileWithMapOutSchema,
    SurveyMissionDetailOutSchema,
    SurveillanceProfileDroneOutSchema,
    SurveillanceProfileChangeDroneOptionOutSchema,
    VideoAnalysisOutSchema,
)
from devices.utils import  filter_mensurement
from common.inbound_api_key import JwtOrInboundKey

logger = logging.getLogger(__name__)


@api_controller("/surveillance-profiles", tags=["Surveillance Profile"])
class SurveillanceProfileController:
    """Surveillance profile CRUD controller."""

    @route.get("", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-profile")
    def list_profiles(self, request: HttpRequest, name: str = None):
        try:
            page_size = int(request.GET.get("page_size", 25))
            current_page = int(request.GET.get("current_page", 1))

            queryset = SurveillanceProfileService.get_list()
            queryset = filter_mensurement(queryset, SurveillanceProfile, request)
            queryset = apply_dynamic_filters(queryset, request, [], request.GET.get("sort_obj"))
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(queryset, page_size)
            try:
                pages = paginator.page(current_page)
            except EmptyPage:
                current_page = paginator.num_pages or 1
                pages = paginator.page(current_page)

            profiles = SurveillanceProfileOutSchema.from_queryset(pages.object_list, many=True)

            items = profiles

            response_payload: Dict[str, Any] = {"items": items}

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=response_payload,
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page,
            )
        except Exception as exc:
            logger.exception("Error getting surveillance profiles: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/list-selected-profiles", auth=CustomJWTAuth())
    # @path_permission("read", path_override="/survey-profile")
    def list_selected_profiles(self, request: HttpRequest):
        try:
            page_size = int(request.GET.get("page_size", 25))
            current_page = int(request.GET.get("current_page", 1))
            request_data = request.GET.copy()
            start_time_start = request_data.pop('start_time_start')
            start_time_end = request_data.pop('start_time_end')

            queryset = SurveillanceProfileService.get_selected_list(start_time_start, start_time_end)
            queryset = filter_mensurement(queryset, SurveillanceProfile, request)
            queryset = apply_dynamic_filters(queryset, request_data, [], request.GET.get("sort_obj"))
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(queryset, page_size)
            try:
                pages = paginator.page(current_page)
            except EmptyPage:
                current_page = paginator.num_pages or 1
                pages = paginator.page(current_page)
            items = SurveillanceProfileSelectedOutSchema.from_queryset(pages.object_list, many=True)
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=items,
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page,
            )
        except Exception as exc:
            logger.exception("Error getting in progress profiles: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/list-completed-profiles", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-profile")
    def list_completed_profiles(self, request: HttpRequest):
        try:
            page_size = int(request.GET.get("page_size", 25))
            current_page = int(request.GET.get("current_page", 1))
            queryset = SurveillanceProfileService.get_list('completed')
            queryset = filter_mensurement(queryset, SurveillanceProfile, request)
            queryset = apply_dynamic_filters(queryset, request, [], request.GET.get("sort_obj"))
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(queryset, page_size)
            try:
                pages = paginator.page(current_page)
            except EmptyPage:
                current_page = paginator.num_pages or 1
                pages = paginator.page(current_page)
            items = SurveillanceProfileOutSchema.from_queryset(pages.object_list, many=True)
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=items,
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page,
            )
        except Exception as exc:
            logger.exception("Error getting completed profiles: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/list-rejected-profiles", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-profile")
    def list_rejected_profiles(self, request: HttpRequest):
        try:
            page_size = int(request.GET.get("page_size", 25))
            current_page = int(request.GET.get("current_page", 1))
            queryset = SurveillanceProfileService.get_list('rejected,cancelled')
            queryset = filter_mensurement(queryset, SurveillanceProfile, request)
            queryset = apply_dynamic_filters(queryset, request, [], request.GET.get("sort_obj"))
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(queryset, page_size)
            try:
                pages = paginator.page(current_page)
            except EmptyPage:
                current_page = paginator.num_pages or 1
                pages = paginator.page(current_page)
            items = SurveillanceProfileOutSchema.from_queryset(pages.object_list, many=True)
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=items,
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page,
            )
        except Exception as exc:
            logger.exception("Error getting rejected profiles: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )
    @route.get("/timeline", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-profile")
    def get_profiles_timeline(self, request: HttpRequest, created_on: str, profile_ids: str):
        """
        Get surveillance profiles timeline for a specific day.
        """
        try:
            profile_ids = profile_ids.split(",")
            created_on_dt = date_parser.parse(created_on)
            queryset, start_of_day, end_of_day = SurveillanceProfileService.get_timeline_queryset_for_day(
                created_on=created_on_dt,
                params=request.GET,
                profile_ids=profile_ids,
            )

            # queryset = apply_dynamic_filters(queryset, request, [], request.GET.get("sort_obj"))
            queryset = queryset.order_by("start_time", "id").distinct()

            timeline_raw = SurveillanceProfileService.build_timeline_payload(
                profiles=queryset,
                window_start=start_of_day,
                window_end=end_of_day,
            )

            response_payload: Dict[str, Any] = {
                "timeline":timeline_raw,
                "time_range": {
                    "start": start_of_day.isoformat(),
                    "end": end_of_day.isoformat(),
                },
                "created_on": start_of_day.date().isoformat(),
            }

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=response_payload,
            )
        except ValidationError as exc:
            logger.warning("Validation error when building timeline: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data={"success": False, "errors": exc.errors()} if hasattr(exc, "errors") else None,
            )
        except Exception as exc:
            logger.exception("Error getting surveillance profile timeline: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/create/context", auth=CustomJWTAuth())
    @path_permission("create", path_override="/survey-profile")
    def get_create_context(self, request: HttpRequest):
        mission_id = request.GET.get("mission_id")
        if not mission_id:
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.VALIDATION_ERROR),
                data={"error": "mission_id is required"},
            )

        start_time_param = request.GET.get("start_time")
        parsed_start_time: Optional[datetime] = None
        if start_time_param:
            parsed_start_time = parse_datetime(start_time_param)
            if parsed_start_time is None:
                try:
                    parsed_start_time = datetime.fromisoformat(start_time_param)
                except ValueError:
                    parsed_start_time = None

        try:
            context = SurveillanceProfileService.get_create_context(
                mission_id=int(mission_id),
                start_time=parsed_start_time,
            )
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_DETAIL_SUCCESS),
                data=context,
            )
        except ValidationError as exc:
            logger.warning("Validation error when preparing create context: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data=None,
            )
        except Exception as exc:
            logger.exception("Error getting profile create context: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/available-devices/", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-profile")
    def get_available_devices(
        self,
        request: HttpRequest,
        mission_id: int,
        start_time: Optional[datetime] = None,
    ):
        try:
            payload = SurveillanceProfileService.get_available_devices_for_mission(
                mission_id=mission_id,
                start_time=start_time,
            )
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=payload,
            )
        except ValidationError as exc:
            logger.warning("Validation error when getting available devices: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data=None,
            )
        except Exception as exc:
            logger.exception("Error getting available devices for mission %s: %s", mission_id, exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/{profile_id}/change-drone/options", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-profile")
    def get_change_drone_options(
        self,
        request: HttpRequest,
        profile_id: int,
        start_waypoint_id: int,
        end_waypoint_id: int,
        page_size: int = 10,
        current_page: int = 1,
    ):
        try:
            result = SurveillanceProfileService.get_change_drone_options(
                profile_id=profile_id,
                start_waypoint_id=start_waypoint_id,
                end_waypoint_id=end_waypoint_id,
                page_size=page_size,
                current_page=current_page,
            )
            items = [
                SurveillanceProfileChangeDroneOptionOutSchema(**item).dict()
                for item in result.get("items", [])
            ]
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data={"items": items},
                total_pages=result.get("total_pages", 0),
                total_items=result.get("total_items", 0),
                current_page=result.get("current_page", current_page),
            )
        except ValidationError as exc:
            logger.warning("Validation error when getting change drone options: %s", exc)
            details = {"success": False, "errors": exc.errors()} if hasattr(exc, "errors") else None
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data=details,
            )
        except Exception as exc:
            logger.exception(
                "Error getting change drone options for profile %s: %s",
                profile_id,
                exc,
            )
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.post("/{profile_id}/change-drone", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-profile")
    def change_drone(
        self,
        request: HttpRequest,
        profile_id: int,
        data: SurveillanceProfileChangeDroneInSchema,
    ):
        try:
            result = SurveillanceProfileService.change_profile_drone(
                profile_id=profile_id,
                from_device_id=data.from_drone_id,
                to_device_id=data.to_drone_id,
            )
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.UPDATE_SUCCESS),
                data=result,
            )
        except ValidationError as exc:
            logger.warning("Validation error when changing drone: %s", exc)
            details = {"success": False, "errors": exc.errors()} if hasattr(exc, "errors") else None
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data=details,
            )
        except Exception as exc:
            logger.exception("Error changing drone for profile %s: %s", profile_id, exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/check-scheduled-activations", auth=CustomJWTAuth())
    # @path_permission("read")
    def list_scheduled_activations(self, request):
        """Danh sách các task đã được lập lịch (kích hoạt hoặc overdue check)."""
        try:
            queryset = SurveillanceProfileService.get_scheduled_activations()
            # Áp dụng filter và sort nếu có
            queryset = apply_dynamic_filters(queryset, request, [], request.GET.get("sort_obj"))

            # Pagination
            page_size = int(request.GET.get("page_size", 25))
            current_page = int(request.GET.get("current_page", 1))
            paginator = OptimizedPaginator(queryset, page_size)

            try:
                pages = paginator.page(current_page)
            except EmptyPage:
                current_page = paginator.num_pages or 1
                pages = paginator.page(current_page)

            # Chỉ lấy thông tin task, không cần dữ liệu profile đầy đủ
            all_tasks = []
            for profile in pages.object_list:
                profile_id = profile.id
                all_tasks_info = SurveillanceProfileService.get_all_profile_tasks(profile_id)
                if all_tasks_info and all_tasks_info.get("tasks"):
                    # Thêm profile_id vào mỗi task để biết task thuộc profile nào
                    for task in all_tasks_info.get("tasks", []):
                        task_with_profile = task.copy()
                        task_with_profile["profile_id"] = profile_id
                        task_with_profile["profile_code"] = all_tasks_info.get("profile_code")
                        task_with_profile["profile_name"] = all_tasks_info.get("profile_name")
                        all_tasks.append(task_with_profile)

            response_payload: Dict[str, Any] = {"items": all_tasks}

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_LIST_SUCCESS),
                data=response_payload,
                total_pages=paginator.num_pages,
                total_items=len(all_tasks),
                current_page=current_page,
            )
        except Exception as exc:
            logger.exception("Error getting scheduled activations: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )
        # except Exception as exc:
        #     logger.exception("Error getting scheduled activations: %s", exc)
        #     return BaseResponse(
        #         status_code=400,
        #         success=False,
        #         message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
        #         data=None,
        #     )

    @route.get("/{profile_id}", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-profile")
    def get_profile(self, request: HttpRequest, profile_id: int):
        try:
            profile = SurveillanceProfileService.get_detail(profile_id)
            if not profile:
                return BaseResponse(
                    status_code=404,
                    success=False,
                    message=get_message(MESSAGE_ENUM.NOT_FOUND),
                    data=None,
                )

            # Get profile instance
            profile_instance = profile.first()

            data = SurveyMissionDetailOutSchema.from_queryset(profile, many=False)
            # if not profile_instance.mission.from_route:
            #     data['altitude'] = profile_instance.mission.get_measurement('altitude').get_formatted_value()
            #     use_command_altitude_range = False
            # else:
            data['altitude'] = None
            use_command_altitude_range = True

            min_altitude = None
            max_altitude = None
            drone_assignments = SurveillanceProfileService._drone_prefetch_queryset().filter(profile=profile_instance)
            for assignment in drone_assignments:
                if assignment.log_collection:
                    flight_log_raw_data = FlightLogService.get_drone_log_raw_data(assignment.device.unit_id, assignment.profile.actual_start_time, assignment.profile.actual_end_time)
                    # save flight_log_raw_data as json file to minio
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{assignment.device.unit_id}.json"
                    log_path = minio_client.save_json(flight_log_raw_data, assignment.device.unit_id, filename)
                    assignment.log_path = log_path
                    assignment.save()

            # Build route_paths mapping for all assignments
            route_paths_map = SurveillanceProfileService.build_route_paths_for_assignments(
                drone_assignments,
                profile_instance.mission
            )

            # Serialize drone assignments
            assignments_data = []
            for assignment in drone_assignments:
                assignments_data.append(SurveillanceProfileDroneOutSchema.from_queryset(assignment, many=False))

            # Add route_path to each assignment from the mapping
            for assignment_dict in assignments_data:
                assignment_id = assignment_dict.get('id')
                if assignment_id and assignment_id in route_paths_map:
                    assignment_dict['route_path'] = route_paths_map[assignment_id]

            data['drone_assignments'] = assignments_data
                        # Chỉ lấy waypoint với command nằm trong danh sách cho phép để vẽ biểu đồ
            allowed_command_ids = {16, 21, 17, 18, 19, 31, 192, 195, 22, 186, 20, 86, 84}
            chart_entries = []
            routes_controller = RoutesController()
                        # Build measurements cache for cruise_speed & operating_altitude
            measurements_cache = {}
            waypoints_qs = profile_instance.mission.waypoints.all().prefetch_related('measurements')
            waypoints_list = list(waypoints_qs)
            for wp in waypoints_list:
                cached_measurements = wp.measurements.filter(
                    measurement_type__in=["cruise_speed", "operating_altitude"]
                )
                measurements_cache[wp.id] = {m.measurement_type: m for m in cached_measurements}
            for index, waypoint in enumerate(waypoints_list):
                command_id_str = None
                measurement_map = measurements_cache.get(waypoint.id, {})
                cruise_speed_measurement = measurement_map.get('cruise_speed')
                cruise_speed_value = cruise_speed_measurement.get_numeric_value(user_units='m/s') if cruise_speed_measurement else 0
                # Skip waypoint if command id not allowed
                if waypoint.command_line:
                    command_id_str = next(iter(waypoint.command_line.keys()), None)
                    try:
                        command_id = int(command_id_str) if command_id_str else None
                    except ValueError:
                        command_id = None

                    raw_command_line = waypoint.command_line
                    command_name = None
                    if raw_command_line and command_id_str:
                        command_data = raw_command_line.get(command_id_str)
                        if isinstance(command_data, dict):
                            command_name = next(iter(command_data.keys()), None)
                    if use_command_altitude_range and command_name:
                        normalized_command_name = command_name.upper()
                        if not normalized_command_name.endswith("TAKEOFF"):

                            operating_altitude_measurement = measurement_map.get('operating_altitude')
                            operating_altitude_value = (
                                operating_altitude_measurement.get_numeric_value(user_units='m')
                                if operating_altitude_measurement
                                else None
                            )
                            if operating_altitude_value is not None:
                                min_altitude = (
                                    operating_altitude_value
                                    if min_altitude is None
                                    else min(min_altitude, operating_altitude_value)
                                )
                                max_altitude = (
                                    operating_altitude_value
                                    if max_altitude is None
                                    else max(max_altitude, operating_altitude_value)
                                )
                    if command_id is not None and command_id not in allowed_command_ids:
                        continue



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

            if use_command_altitude_range and min_altitude is not None and max_altitude is not None:
                data['altitude'] = f"{round(min_altitude, 2)} m - {round(max_altitude, 2)} m"
            data['chart_data'] = chart_entries
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.MESSAGE_GET_DETAIL_PROFILE_SUCCESS),
                data=data,
            )
        except Exception as exc:
            logger.exception("Error getting surveillance profile detail: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.post("", auth=CustomJWTAuth())
    @path_permission("create", path_override="/survey-profile")
    def create_profile(self, request: HttpRequest, data: SurveillanceProfileCreateInSchema):
        try:
            success, profile = SurveillanceProfileService.create(data.dict())
            if not success:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.CREATE_SURVEILLANCE_PROFILE_FAILED),
                    data=None,
                )

            result = SurveillanceProfileOutSchema.from_queryset(profile, many=False)

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.CREATE_SURVEILLANCE_PROFILE_SUCCESS),
                data=result,
            )
        except ValidationError as exc:
            logger.warning("Validation error when creating profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data=None,
            )
        except Exception as exc:
            logger.exception("Error creating surveillance profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.post("/drone/mark-flight-time")
    def mark_drone_flight_time(self, request: HttpRequest, data: SurveillanceProfileDroneFlightMarkInSchema):
        try:
            success, result = SurveillanceProfileService.mark_drone_flight_time(
                drone_unit_id=data.drone_unit_id,
                start_time=data.start_time,
                end_time=data.end_time,
                profile_id=data.profile_id,
            )
            if not success:
                return BaseResponse(
                    status_code=404,
                    success=False,
                    message=get_message(MESSAGE_ENUM.MESSAGE_OPERATION_FAILED),
                    data={"error": result},
                )

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.MARK_SURVEILLANCE_PROFILE_DRONE_FLIGHT_TIME_SUCCESS),
                data=SurveillanceProfileDroneOutSchema.from_queryset(result, many=False),
            )
        except ValidationError as exc:
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data=None,
            )
        except Exception as exc:
            logger.exception("Error marking drone flight time: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.put("/{profile_id}", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-profile")
    def update_profile(
        self,
        request: HttpRequest,
        profile_id: int,
        data: SurveillanceProfileUpdateInSchema,
    ):
        # W0-14c — 문지기는 **try 밖**이다 (except 가 예외를 200 으로 바꾼다 · W0-18 대상).
        assert_scoped(SurveillanceProfile, profile_id, request.user)
        try:
            success, profile = SurveillanceProfileService.update(profile_id, data.dict(exclude_unset=True))
            if not success:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.UPDATE_FAILED),
                    data=None,
                )

            result = SurveillanceProfileOutSchema.from_queryset(profile, many=False)

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.UPDATE_SUCCESS),
                data=result,
            )
        except ValidationError as exc:
            logger.warning("Validation error when updating profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data=None,
            )
        except Exception as exc:
            logger.exception("Error updating surveillance profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.post("/{profile_id}/approve", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-profile")
    def approve_profile(
        self,
        request: HttpRequest,
        profile_id: int,
    ):
        try:
            success, profile = SurveillanceProfileService.approve_profile(
                profile_id=profile_id,
                approved_by=request.user,
            )

            if not success:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.UPDATE_FAILED),
                    data=None,
                )

            result = SurveillanceProfileOutSchema.from_queryset(profile, many=False)

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.APPROVE_SURVEILLANCE_PROFILE_SUCCESS),
                data=result,
            )
        except ValidationError as exc:
            logger.warning("Validation error when approving profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data=None,
            )
        except Exception as exc:
            logger.exception("Error approving surveillance profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.post("/{profile_id}/check-complete", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-profile")
    def complete_device_check(
        self,
        request: HttpRequest,
        profile_id: int,
        data: SurveillanceProfileCheckCompleteInSchema,
    ):
        try:
            drone_checks_payload = [entry.dict() for entry in data.drone_checks]
            success, profile = SurveillanceProfileService.complete_device_check(
                profile_id=profile_id,
                drone_checks=drone_checks_payload,
                checked_by=request.user,
                not_yet=data.not_yet,
            )

            if not success:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.UPDATE_FAILED),
                    data=None,
                )

            result = SurveillanceProfileOutSchema.from_queryset(profile, many=False)

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.COMPLETE_SURVEILLANCE_PROFILE_CHECK_SUCCESS),
                data=result,
            )
        except ValidationError as exc:
            logger.warning("Validation error when completing device check: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data=None,
            )
        except Exception as exc:
            logger.exception("Error completing device check for surveillance profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.post("/{profile_id}/reject", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-profile")
    def reject_profile(
        self,
        request: HttpRequest,
        profile_id: int,
        data: SurveillanceProfileRejectInSchema,
    ):
        try:
            success, profile = SurveillanceProfileService.reject_profile(
                profile_id=profile_id,
                reason=data.reason,
                rejected_by=request.user,
            )

            if not success:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.UPDATE_FAILED),
                    data=None,
                )

            result = SurveillanceProfileOutSchema.from_queryset(profile, many=False)

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.REJECT_SURVEILLANCE_PROFILE_SUCCESS),
                data=result,
            )
        except ValidationError as exc:
            logger.warning("Validation error when rejecting profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data=None,
            )
        except Exception as exc:
            logger.exception("Error rejecting surveillance profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.delete("/{profile_id}", auth=CustomJWTAuth())
    @path_permission("delete", path_override="/survey-profile")
    def delete_profile(self, request: HttpRequest, profile_id: int):
        # W0-14c — 문지기는 try 밖.
        assert_scoped(SurveillanceProfile, profile_id, request.user)
        try:
            success, message = SurveillanceProfileService.delete(profile_id)
            if not success:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.ACTION_DELETE_FAILED),
                    data=None,
                )

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS),
                data=None,
            )
        except ValidationError as exc:
            logger.warning("Validation error when deleting profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data=None,
            )
        except Exception as exc:
            logger.exception("Error deleting surveillance profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/{profile_id}/with-map", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-profile")
    def get_profile_with_map(self, request: HttpRequest, profile_id: int):
        try:
            result = SurveillanceProfileService.get_profile_with_route_map(profile_id)
            if not result:
                return BaseResponse(
                    status_code=404,
                    success=False,
                    message=get_message(MESSAGE_ENUM.NOT_FOUND),
                    data=None,
                )

            payload = SurveillanceProfileWithMapOutSchema(
                profile=SurveillanceProfileOutSchema.from_queryset(result["profile"], many=False),
                route_waypoints=result.get("route_waypoints"),
                devices_positions=result.get("devices_positions"),
            )

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_DETAIL_SUCCESS),
                data=payload,
            )
        except Exception as exc:
            logger.exception("Error getting surveillance profile map data: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.post("/{profile_id}/completed-profile", auth=CustomJWTAuth())
    # @path_permission("update", path_override="/surveillance/profile")
    def completed_profile(self, request: HttpRequest, profile_id: int):
        try:
            success, profile = SurveillanceProfileService.completed_profile(profile_id)
            if not success:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.COMPLETED_SURVEILLANCE_PROFILE_FAILED),
                    data=None,
                )
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.COMPLETED_SURVEILLANCE_PROFILE_SUCCESS),
                data=SurveillanceProfileOutSchema.from_queryset(profile, many=False),
            )
        except ValidationError as exc:
            logger.warning("Validation error when completing profile: %s", exc)
            return BaseResponse(
                status_code=404,
                success=False,
                message=str(exc),
                data=None,
            )
        except Exception as exc:
            logger.exception("Error completing surveillance profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.post("/{profile_id}/cancel-profile", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-profile")
    def cancel_profile(self, request: HttpRequest, profile_id: int, data: SurveillanceProfileCancelInSchema):
        try:
            success, profile = SurveillanceProfileService.cancel_profile(
                profile_id,
                data.reason,
                cancelled_by=request.user,
            )
            if not success:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.CANCEL_SURVEILLANCE_PROFILE_FAILED),
                    data=None,
                )
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.CANCEL_SURVEILLANCE_PROFILE_SUCCESS),
                data=SurveillanceProfileOutSchema.from_queryset(profile, many=False),
            )
        except Exception as exc:
            logger.exception("Error canceling surveillance profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.post("/{profile_id}/cancel", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-profile")
    def cancel_profile_by_payload(
        self,
        request: HttpRequest,
        profile_id: int,
        data: SurveillanceProfileCancelInSchema,
    ):
        try:
            success, profile = SurveillanceProfileService.cancel_profile(
                profile_id,
                data.reason,
                cancelled_by=request.user,
            )
            if not success or profile is None:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.CANCEL_SURVEILLANCE_PROFILE_FAILED),
                    data=None,
                )

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.CANCEL_SURVEILLANCE_PROFILE_SUCCESS),
                data=SurveillanceProfileOutSchema.from_queryset(profile, many=False),
            )
        except ValidationError as exc:
            logger.warning("Validation error when canceling profile via payload: %s", exc)
            details = {"success": False, "errors": exc.errors()} if hasattr(exc, "errors") else None
            return BaseResponse(
                status_code=400,
                success=False,
                message=str(exc),
                data=details,
            )
        except Exception as exc:
            logger.exception("Error canceling surveillance profile via payload: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.post("/{profile_id}/stop-repeat", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-profile")
    def stop_repeat(self, request: HttpRequest, profile_id: int):
        try:
            success, profile = SurveillanceProfileService.stop_repeat(profile_id)
            if not success:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.STOP_REPEAT_SURVEILLANCE_PROFILE_FAILED),
                    data=None,
                )
            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.STOP_REPEAT_SURVEILLANCE_PROFILE_SUCCESS),
                data=SurveillanceProfileOutSchema.from_queryset(profile, many=False),
            )
        except Exception as exc:
            logger.exception("Error stopping repeat for surveillance profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/{profile_drone_id}/download-log", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-profile")
    def download_log(self, request: HttpRequest, profile_drone_id: int):
        try:
            success, file_content, filename = SurveillanceProfileService.download_log(profile_drone_id)
            if not success or not file_content:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED),
                    data=None,
                )

            # Return file as HttpResponse with proper headers
            response = HttpResponse(file_content, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(file_content)
            return response

        except Exception as exc:
            logger.exception("Error downloading log for surveillance profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/{profile_drone_id}/download-analysis", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-profile")
    def download_analysis(self, request: HttpRequest, profile_drone_id: int):
        try:
            success, file_content, filename = SurveillanceProfileService.download_analysis(profile_drone_id)
            if not success or not file_content:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message=get_message(MESSAGE_ENUM.ACTION_EXPORT_FAILED),
                    data=None,
                )

            # Return file as HttpResponse with proper headers
            response = HttpResponse(file_content, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(file_content)
            return response

        except Exception as exc:
            logger.exception("Error downloading log for surveillance profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/{profile_id}/test-upload-profile-to-flightbird", auth=CustomJWTAuth())
    def test_upload_profile_to_flightbird(self, request: HttpRequest, profile_id: int):
        # try:
        profile = SurveillanceProfile._base_manager.get(id=profile_id)
        SurveillanceProfileService.upload_profile_to_flightbird(profile)
        return BaseResponse(
            status_code=200,
            success=True,
            message="Success",
            data=None,
        )
        # except Exception as exc:
        #     logger.exception("Error testing upload profile to flightbird: %s", exc)
        #     return BaseResponse(
        #         status_code=400,
        #         success=False,
        #         message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
        #         data=None,
        #     )

    @route.get("/{profile_id}/tasks", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-profile")
    def get_all_profile_tasks(self, request: HttpRequest, profile_id: int):
        """Lấy thông tin tất cả các task liên quan đến một profile."""
        try:
            all_tasks_info = SurveillanceProfileService.get_all_profile_tasks(profile_id)

            if not all_tasks_info or not all_tasks_info.get("tasks"):
                return BaseResponse(
                    status_code=404,
                    success=False,
                    message="Không tìm thấy task nào cho profile này",
                    data=None,
                )

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_DETAIL_SUCCESS),
                data=all_tasks_info,
            )
        except Exception as exc:
            logger.exception("Error getting profile tasks: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/{profile_id}/scheduled-activation", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-profile")
    def get_scheduled_activation(self, request: HttpRequest, profile_id: int):
        """Chi tiết lịch kích hoạt của một profile (deprecated - dùng /tasks)."""
        try:
            scheduled_info = SurveillanceProfileService.get_scheduled_activation_info(profile_id)

            if not scheduled_info:
                return BaseResponse(
                    status_code=404,
                    success=False,
                    message="Không tìm thấy lịch kích hoạt cho profile này",
                    data=None,
                )

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_DETAIL_SUCCESS),
                data=scheduled_info,
            )
        except Exception as exc:
            logger.exception("Error getting scheduled activation: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.delete("/{profile_id}/tasks/{task_type}", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-profile")
    def cancel_profile_task(self, request: HttpRequest, profile_id: int, task_type: str):
        """Hủy một task cụ thể của profile (activation hoặc overdue_check)."""
        try:
            if task_type not in ["activation", "overdue_check"]:
                return BaseResponse(
                    status_code=400,
                    success=False,
                    message="task_type phải là 'activation' hoặc 'overdue_check'",
                    data=None,
                )

            success, error_message, cancelled_count = SurveillanceProfileService.cancel_profile_task(
                profile_id, task_type=task_type
            )

            if not success:
                return BaseResponse(
                    status_code=404 if error_message == "Profile not found" else 400,
                    success=False,
                    message=error_message or get_message(MESSAGE_ENUM.UPDATE_FAILED),
                    data=None,
                )

            return BaseResponse(
                status_code=200,
                success=True,
                message=f"Đã hủy {cancelled_count} task thành công",
                data={"cancelled_count": cancelled_count},
            )
        except Exception as exc:
            logger.exception("Error canceling profile task: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.delete("/{profile_id}/tasks", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-profile")
    def cancel_all_profile_tasks(self, request: HttpRequest, profile_id: int):
        """Hủy tất cả các task của profile."""
        try:
            success, error_message, cancelled_count = SurveillanceProfileService.cancel_profile_task(
                profile_id, task_type=None
            )

            if not success:
                return BaseResponse(
                    status_code=404 if error_message == "Profile not found" else 400,
                    success=False,
                    message=error_message or get_message(MESSAGE_ENUM.UPDATE_FAILED),
                    data=None,
                )

            return BaseResponse(
                status_code=200,
                success=True,
                message=f"Đã hủy {cancelled_count} task thành công",
                data={"cancelled_count": cancelled_count},
            )
        except Exception as exc:
            logger.exception("Error canceling all profile tasks: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.delete("/{profile_id}/scheduled-activation", auth=CustomJWTAuth())
    @path_permission("update", path_override="/survey-profile")
    def cancel_scheduled_activation(self, request: HttpRequest, profile_id: int):
        """Hủy lịch kích hoạt đã lập cho một profile (deprecated - dùng /tasks/activation)."""
        try:
            success, error_message = SurveillanceProfileService.cancel_scheduled_activation(profile_id)

            if not success:
                return BaseResponse(
                    status_code=404 if error_message == "Profile not found" else 400,
                    success=False,
                    message=error_message or get_message(MESSAGE_ENUM.UPDATE_FAILED),
                    data=None,
                )

            return BaseResponse(
                status_code=200,
                success=True,
                message="Đã hủy lịch kích hoạt thành công",
                data=None,
            )
        except Exception as exc:
            logger.exception("Error canceling scheduled activation: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.post("/{profile_id}/download-analysis-for-profile", auth=CustomJWTAuth())
    @path_permission("read", path_override="/survey-profile")
    def download_analysis_async(self, request: HttpRequest, profile_id: int):
        try:
            import threading
            import uuid
            from task_status.models import TaskStatus
            from task_status.services.task_status_service import TaskStatusService

            from surveillance.tasks import _process_download_video_analysis_reports_in_thread

            download_task_id = str(uuid.uuid4())
            task_type = "surveillance_profile_download_analysis_pdf"

            pending_message = get_message(MESSAGE_ENUM.START_DOWNLOAD_FILE)
            TaskStatusService.create_or_update(
                task_id=download_task_id,
                task_type=task_type,
                category=TaskStatus.Category.DOWNLOAD,
                user=request.user,
                status=TaskStatus.Status.PENDING,
                message=pending_message,
                action="surveillance_profile_download_analysis_pdf",
                task_channel=f"survey_profile_{request.user.username}",
                trigger_source="surveillance.profile.download_analysis_pdf",
                related_model="surveillance.SurveillanceProfile",
                related_object_id=str(profile_id),
                payload={"profile_id": profile_id},
                progress=0.0,
            )

            download_thread = threading.Thread(
                target=_process_download_video_analysis_reports_in_thread,
                args=(profile_id, download_task_id, request.user.id),
                daemon=True,
            )
            download_thread.start()

            return BaseResponse(
                status_code=200,
                success=True,
                message=pending_message,
                data={
                    "task_id": download_task_id,
                    "status": TaskStatus.Status.PENDING,
                    "message": pending_message,
                },
            )
        except Exception as exc:
            logger.exception("Error downloading analysis for surveillance profile: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

@api_controller("/video-analysis", tags=["Video Analysis"])
class VideoAnalysisController:
    @route.get("", auth=JwtOrInboundKey())
    def get_video_analysis(self, request: HttpRequest, page_size: int = 25, current_page: int = 1):
        try:
            page_size = int(page_size)
            current_page = int(current_page)
            video_analysis = VideoAnalysisService.get_video_analysis()
            queryset = filter_mensurement(video_analysis, VideoAnalysis, request)
            queryset = apply_dynamic_filters(queryset, request, [], request.GET.get("sort_obj"))
            # 🚀 OPTIMIZED: Use OptimizedPaginator to automatically optimize COUNT query
            paginator = OptimizedPaginator(queryset, page_size)
            try:
                pages = paginator.page(current_page)
            except EmptyPage:
                current_page = paginator.num_pages or 1
                pages = paginator.page(current_page)
            data = VideoAnalysisOutSchema.from_queryset(pages.object_list, many=True)

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_VIDEO_ANALYSIS_SUCCESS),
                data=data,
                total_pages=paginator.num_pages,
                total_items=paginator.count,
                current_page=current_page,
            )
        except Exception as exc:
            logger.exception("Error analyzing video: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/{video_analysis_id}", auth=CustomJWTAuth())
    def get_video_analysis_detail(self, request: HttpRequest, video_analysis_id: int):
        # ★ 문지기는 try **밖**이다 (W0-14c 1차의 교훈) — 아래 except 가 모든 예외를
        #   삼켜 400 으로 바꾸므로, 안에 두면 Http404 도 삼켜져 아무것도 막지 못한다.
        #   실측(2026-08-27): 남의 테넌트 레코드에 **400** 이 나갔다. 매니저가 걸러
        #   누출은 없었으나 "없는 것과 같아야" 한다는 규약은 404 다 — 400 은
        #   "요청이 틀렸다"여서 존재 여부에 대해 다른 말을 한다.
        #   그리고 우연한 차단에 기대지 않는다: 매니저의 필터에는 created_by__isnull
        #   OR 절이 있어(§0.4) 소유가 빈 행에서는 걸러 주지 못한다.
        assert_scoped(VideoAnalysis, video_analysis_id, request.user)
        try:
            video_analysis = VideoAnalysisService.get_video_analysis_detail(video_analysis_id)
            # Use from_queryset instead of from_orm for DynamicSchema to get all fields including video_size
            data = VideoAnalysisOutSchema.from_queryset(video_analysis, many=False)
            user = request.user
            # Download and parse AI analysis JSON from analysis_path
            if video_analysis.analysis_path:
                analysis_json = minio_client.get_json(video_analysis.analysis_path)
                if analysis_json is not None:
                    data['analysis'] = analysis_json
                else:
                    logger.warning(f"Failed to retrieve analysis JSON from {video_analysis.analysis_path}")
                    data['analysis'] = None
            data['purpose'] = "Surveillance" if user.language.code == "en" else "정찰" if user.language.code == "ko" else "การสอดส่อง" if user.language.code == "th" else "Surveillance"
            if not data['profile_device'] or data['profile_device'] == '':
                data['purpose'] = "Other" if user.language.code == "en" else "기타" if user.language.code == "ko" else "อื่นๆ" if user.language.code == "th" else "Other"
            # --- Enrich altitude, timings, remarks and register_number with safe fallbacks ---
            if getattr(video_analysis, "profile_device", None) and getattr(video_analysis.profile_device, "profile", None):
                mission_obj = video_analysis.profile_device.profile.mission
                data['capture_altitude'] = mission_obj.get_measurement('altitude').get_formatted_value() if mission_obj.get_measurement('altitude') else None
                data['takeoff_altitude'] = mission_obj.get_measurement('takeoff_altitude').get_formatted_value() if mission_obj.get_measurement('takeoff_altitude') else None
                data['altitude_separation'] = mission_obj.get_measurement('altitude_separation').get_formatted_value() if mission_obj.get_measurement('altitude_separation') else None
                data['landing_time'] = video_analysis.profile_device.profile.actual_end_time
                if data.get('remark') in (None, ''):
                    data['remark'] = getattr(video_analysis.profile_device.profile, 'note', None)
                if not data.get('register_number'):
                    try:
                        data['register_number'] = getattr(getattr(video_analysis.profile_device.device, 'manufacturer_information', None), 'registration_number', None)
                    except Exception:
                        pass

            return BaseResponse(
                status_code=200,
                success=True,
                message=get_message(MESSAGE_ENUM.GET_VIDEO_ANALYSIS_SUCCESS),
                data=data,
            )
        except Exception as exc:
            logger.exception("Error analyzing video: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )

    @route.get("/{video_analysis_id}/download-detail", auth=JwtOrInboundKey())
    def download_video_analysis_detail(self, request: HttpRequest, video_analysis_id: int):
        # ★ 문지기는 try **밖**이다 (W0-14c 1차의 교훈) — 아래 except 가 모든 예외를
        #   삼켜 400 으로 바꾸므로, 안에 두면 Http404 도 삼켜져 아무것도 막지 못한다.
        #   실측(2026-08-27): 남의 테넌트 레코드에 **400** 이 나갔다. 매니저가 걸러
        #   누출은 없었으나 "없는 것과 같아야" 한다는 규약은 404 다 — 400 은
        #   "요청이 틀렸다"여서 존재 여부에 대해 다른 말을 한다.
        #   그리고 우연한 차단에 기대지 않는다: 매니저의 필터에는 created_by__isnull
        #   OR 절이 있어(§0.4) 소유가 빈 행에서는 걸러 주지 못한다.
        assert_scoped(VideoAnalysis, video_analysis_id, request.user)
        try:
            video_analysis = VideoAnalysisService.get_video_analysis_detail(video_analysis_id)
            # Use from_queryset instead of from_orm for DynamicSchema to get all fields including video_size
            data = VideoAnalysisOutSchema.from_queryset(video_analysis, many=False)
            # Download and parse AI analysis JSON from analysis_path
            if video_analysis.analysis_path:
                analysis_json = minio_client.get_json(video_analysis.analysis_path)
                if analysis_json is not None:
                    data['analysis'] = analysis_json
                else:
                    logger.warning(f"Failed to retrieve analysis JSON from {video_analysis.analysis_path}")
                    data['analysis'] = None
            # Parse data to JSON using DjangoJSONEncoder to handle datetime objects
            json_data = json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False, indent=2)
            # Return file as HttpResponse with proper headers
            response = HttpResponse(json_data, content_type='application/json; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="video_analysis_{video_analysis.id}.json"'
            response['Content-Length'] = len(json_data.encode('utf-8'))
            return response
        except Exception as exc:
            logger.exception("Error downloading video analysis detail: %s", exc)
            return BaseResponse(
                status_code=400,
                success=False,
                message=get_message(MESSAGE_ENUM.UNEXPECTED_ERROR),
                data=None,
            )
