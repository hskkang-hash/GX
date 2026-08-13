import copy
import calendar
import json
import logging
import math
import asyncio
import threading
import os
import time as pytime
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from itertools import combinations
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
import uuid
from zoneinfo import ZoneInfo

from asgiref.sync import async_to_sync
from core.configuration.models import AdminConfig
import requests
from common.utils import get_gcs_api_headers
from core.common.schema_utils import DynamicSchema
from core.middleware.refresh_token import get_current_request
from core.multilanguage.models import MultiLanguageContent
from core.user.models import CoreUser
from dateutil.rrule import DAILY, MONTHLY, WEEKLY, rrule
from django.contrib.contenttypes.models import ContentType
from django.db import connection, transaction
from django.db.utils import OperationalError, DatabaseError
from django.db.models import (
    BooleanField,
    Case,
    CharField,
    Count,
    Exists,
    F,
    Func,
    JSONField,
    Max,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Sum,
    TextField,
    Value,
    When,
)
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Concat, Coalesce, Lower
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from geopy.distance import geodesic
from ninja.errors import ValidationError
from dateutil.relativedelta import relativedelta

from delivery.services.processing_service import ProcessingService
from surveillance.services.video_analysis_service import VideoAnalysisService
from surveillance.services.surveillance_profile_media_service import SurveillanceProfileMediaService
from flight_log.services.flight_log_service import FlightLogService
from checklist_setting.models import ChecklistSetting
from stream_monitors.models import StreamMonitorRecord
from stream_monitors.services.stream_monitor_services import StreamMonitorService
from stream_monitors.utils.minio_client import minio_client
from common.constant import MESSAGE_ENUM, get_message
from common.utils import get_waypoint_speed
from devices.models import Device, DeviceStatus
from devices.services.flight_estimation_service import FlightEstimationService
from surveillance.models import (
    MissionPurpose,
    MissionWaypoint,
    SurveillanceProfile,
    SurveillanceProfileChecklist,
    SurveillanceProfileChecklistItem,
    SurveillanceProfileDrone,
    SurveillanceProfileRepeatType,
    SurveillanceProfileRepeatUntilType,
    SurveillanceStatus,
    SurveyMission,
    VideoAnalysis,
)
from surveillance.schemas.schemas_djantic_out import (
    SurveyMissionDetailOutSchema,
    SurveillanceProfileDroneOutSchema,
)
from surveillance.services.surveillance_profile_automation_service import (
    SurveillanceProfileAutomationService,
)
from terminals.utils import calculate_distance_km
from terminals.views.routes_views import RoutesController
from django.conf import settings
from devices.utils import convert_unit

logger = logging.getLogger(__name__)

DEFAULT_REPEAT_OCCURRENCES = 10
MAX_REPEAT_GENERATION = 60
AUTO_ADJUST_SEGMENT_OFFSET_MINUTES = 5


class SurveillanceProfileService:
    """Service layer for Surveillance Profile operations."""

    MEASUREMENT_TOTAL_DISTANCE = "total_distance"
    MEASUREMENT_ESTIMATED_TIME = "estimated_time"
    MEASUREMENT_TOTAL_FLIGHT_TIME = "total_flight_time"

    @staticmethod
    def _drone_prefetch_queryset() -> QuerySet:
        return (
            SurveillanceProfileDrone._base_manager.select_related(
                "device",
                "start_waypoint",
                "end_waypoint",
            ).order_by("order", "id")
        )

    @staticmethod
    def get_purpose_translation_queryset() -> QuerySet:
        try:
            current_request = get_current_request()
            if current_request and hasattr(current_request.user, 'language') and current_request.user.language:
                language_code = current_request.user.language.code
            else:
                language_code = 'en'
        except:
            language_code = 'en'
        
        # 🆕 FIX: Map language codes (ko ↔ kr) for compatibility
        # User language might be 'ko' but translations might use 'kr' or vice versa
        language_code_variants = [language_code]
        if language_code == 'ko':
            language_code_variants.append('kr')
        elif language_code == 'kr':
            language_code_variants.append('ko')
        
        try:
            translations_data = MultiLanguageContent.objects.filter(
                content_type=ContentType.objects.get_for_model(MissionPurpose),
                field_name='name'
            ).values('object_id', 'translations')
            translation_mapping = {}
            fallback_mapping = {}
            for item in translations_data:
                try:
                    translations = json.loads(item['translations'])
                    object_id = item['object_id']
                    for lang_code in language_code_variants:
                        if lang_code in translations:
                            translation_mapping[object_id] = translations[lang_code]
                            break  # Found translation, stop trying variants
                    if 'en' in translations:
                        fallback_mapping[object_id] = translations['en']
                except (json.JSONDecodeError, KeyError):
                    continue
            
        except Exception as e:
            logger.error(f"[TRANSLATION] Error loading translations: {e}")
            return Subquery(
                MissionPurpose.objects.filter(
                    id=OuterRef('mission__purpose_id')
                ).values('name')[:1],
                output_field=CharField()
            )
        from django.db import connection
        if connection.vendor == 'postgresql':
            case_conditions = []
            for mp_id, translated_name in translation_mapping.items():
                # Escape single quotes trong translated_name
                escaped_name = translated_name.replace("'", "''")
                case_conditions.append(f"WHEN mp.id = {mp_id} THEN '{escaped_name}'")
            for tt_id, fallback_name in fallback_mapping.items():
                if tt_id not in translation_mapping:
                    escaped_name = fallback_name.replace("'", "''")
                    case_conditions.append(f"WHEN mp.id = {tt_id} THEN '{escaped_name}'")
            if case_conditions:
                case_sql = "CASE " + " ".join(case_conditions) + " ELSE mp.name END"
            else:
                case_sql = "mp.name"
            sql = f"""
                SELECT STRING_AGG(
                    {case_sql}, ', ' ORDER BY mp.name
                )
                FROM surveillance_missionpurpose mp
                WHERE mp.id = (
                    SELECT sm.purpose_id 
                    FROM surveillance_surveymission sm 
                    WHERE sm.id = surveillance_surveillanceprofile.mission_id
                )
                """
            
        else:
            case_conditions = []
            for tt_id, translated_name in translation_mapping.items():
                    # Escape single quotes trong translated_name
                    escaped_name = translated_name.replace("'", "''")
                    case_conditions.append(f"WHEN mp.id = {tt_id} THEN '{escaped_name}'")
            for tt_id, fallback_name in fallback_mapping.items():
                if tt_id not in translation_mapping:
                    escaped_name = fallback_name.replace("'", "''")
                    case_conditions.append(f"WHEN mp.id = {tt_id} THEN '{escaped_name}'")
            if case_conditions:
                case_sql = "CASE " + " ".join(case_conditions) + " ELSE mp.name END"
            else:
                case_sql = "mp.name"
            sql = f"""
                SELECT GROUP_CONCAT(
                    {case_sql} SEPARATOR ', '
                )
                FROM surveillance_missionpurpose mp
                WHERE mp.id = (
                    SELECT sm.purpose_id 
                    FROM surveillance_surveymission sm 
                    WHERE sm.id = surveillance_surveillanceprofile.mission_id
                )
                """
        from django.db.models.expressions import RawSQL
        from django.db.models import CharField
        return RawSQL(sql, [], output_field=CharField())
        
    @staticmethod
    def get_queryset_optimized(status: Optional[str] = None, *, use_base_manager: bool = False) -> QuerySet:
        """Return queryset with required prefetch/select_related."""

        manager = SurveillanceProfile._base_manager if use_base_manager else SurveillanceProfile.objects

        drone_prefetch = Prefetch("drone_assignments", queryset=SurveillanceProfileService._drone_prefetch_queryset())
        query = manager.select_related(       
                    "mission"
                ).defer("mission__qgc_mission_data")\
                .select_related(
                    "status",
                    "mission__purpose",
                    "operator",
                    "created_by",
                    "repeat_type",
                    "repeat_until_type",
                    "approved_by",
                    "cancelled_by",
                )\
                .prefetch_related(drone_prefetch, "mission__measurements", "measurements")\
                .annotate(
                    operator_full_name=Concat(F('operator__first_name'), Value(" "), F('operator__last_name')),
                    purpose__name=SurveillanceProfileService.get_purpose_translation_queryset(),
                    created_by_full_name = Concat(F('created_by__first_name'), Value(" "), F('created_by__last_name')),
                    # Check if profile has any checklist data (disable if has checklist)
                    disable=Exists(
                        SurveillanceProfileChecklist.objects.filter(profile=OuterRef('pk'))
                    ),
                    mission__log_collection=F('mission__log_collection'),
                    mission__video_recording=F('mission__video_recording'),
                    mission__video_analysis=F('mission__video_analysis'),
                    repeat_type__code=F('repeat_type__code'),
                    cancel_reject_reason = Coalesce(F('cancel_reason'), F('reject_reason'), output_field=CharField()),
                    mission__name = F('mission__name'),
                    has_video_analysis = Exists(
                        VideoAnalysis.objects.filter(profile_device__profile=OuterRef('pk'), analysis_path__isnull=False)
                    )
                )
        if status:
            query = query.filter(status__code__in=status.split(","))
        return query
        
    @staticmethod
    def completed_profile(profile_id: int) -> Tuple[bool, Optional[SurveillanceProfile]]:
        try:
            
            profile = SurveillanceProfile._base_manager.get(id=profile_id)
            previous_status_code = profile.status.code if profile.status else None
            if previous_status_code != "in_progress":
                raise ValidationError("Surveillance profile is not in progress, cannot be completed")
            completion_time = timezone.now()
            profile.status = SurveillanceStatus._base_manager.get(code="completed")
            profile.actual_end_time = completion_time
            profile.save(update_fields=["status", "actual_end_time", "modified_on"])
            
            # Calculate and set total_flight_time
            SurveillanceProfileService._calculate_and_set_total_flight_time(profile)
            
            drone_assignments = SurveillanceProfileDrone._base_manager.filter(profile=profile)
            status_available = DeviceStatus._base_manager.get(code="available") 
            for drone_assignment in drone_assignments:
                device = drone_assignment.device
                device.status = status_available
                device.save(update_fields=["status"])

                # Release drone reservation if this profile owns it
                try:
                    from django.core.cache import cache
                    key = f"surveillance:drone_reservation:{drone_assignment.device_id}"
                    existing = cache.get(key)
                    existing_profile_id = None
                    if isinstance(existing, int):
                        existing_profile_id = existing
                    elif isinstance(existing, dict):
                        try:
                            existing_profile_id = int(existing.get("profile_id"))
                        except Exception:
                            existing_profile_id = None
                    else:
                        try:
                            existing_profile_id = int(existing)
                        except Exception:
                            existing_profile_id = None
                    if existing_profile_id == profile.id:
                        cache.delete(key)
                except Exception:
                    pass

                # create flight log if has actual_start_time and actual_end_time
                if drone_assignment.profile.actual_start_time and drone_assignment.profile.actual_end_time:
                    FlightLogService.create_flight_log_from_profile(drone_assignment)
                    # send data to AI analysis
                    anomaly_prediction = ProcessingService._send_data_to_ai_analysis(drone_assignment.device, drone_assignment.profile.code)
                    # update flight log with anomaly prediction
                    if anomaly_prediction:
                        FlightLogService.update_flight_log_surveillance_with_anomaly_prediction(drone_assignment, anomaly_prediction)
                else:
                    logger.warning("Skipping flight log creation for drone assignment %s because it has no actual_start_time or actual_end_time", drone_assignment.id)
            SurveillanceProfileService._handle_profile_completion(profile, previous_status_code)
            return True, profile
        except SurveillanceProfile.DoesNotExist as exc:
            logger.warning("SurveillanceProfile with id %s does not exist", profile_id)
            raise ValidationError("Surveillance profile not found") from exc
        except Exception as exc:
            logger.exception("Error completing surveillance profile: %s", exc)
            return False, None
    @staticmethod
    @transaction.atomic
    def cancel_profile(
        profile_id: int,
        reason: Optional[str] = None,
        cancelled_by: Optional[CoreUser] = None,
        *,
        use_base_manager: bool = False,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[SurveillanceProfile]]:
        try:
            profile_manager = SurveillanceProfile._base_manager if use_base_manager else SurveillanceProfile.objects
            status_manager = SurveillanceStatus._base_manager if use_base_manager else SurveillanceStatus.objects
            device_status_manager = DeviceStatus._base_manager if use_base_manager else DeviceStatus.objects
            assignment_manager = SurveillanceProfileDrone._base_manager if use_base_manager else SurveillanceProfileDrone.objects

            # Lock profile để tránh race condition với các task khác hoặc user cancel thủ công
            # Sử dụng select_for_update để đảm bảo chỉ một process được cancel tại một thời điểm
            # Lưu ý: Không thể dùng select_related với select_for_update trên nullable ForeignKey
            # vì PostgreSQL không cho phép FOR UPDATE trên nullable side của outer join
            try:
                profile = (
                    profile_manager
                    .select_for_update(nowait=False, skip_locked=False)
                    .get(id=profile_id)
                )
                # Fetch status sau khi đã lock để tránh lỗi outer join
                if profile.status_id:
                    profile.status = status_manager.get(id=profile.status_id)
            except (OperationalError, DatabaseError) as db_exc:
                # Nếu select_for_update bị timeout hoặc deadlock, thử lại với nowait=True
                logger.warning(
                    "[SURVEILLANCE][CANCEL] Database error when locking profile %s: %s. Retrying with nowait=True",
                    profile_id,
                    str(db_exc)
                )
                try:
                    profile = (
                        profile_manager
                        .select_for_update(nowait=True, skip_locked=False)
                        .get(id=profile_id)
                    )
                    # Fetch status sau khi đã lock
                    if profile.status_id:
                        profile.status = status_manager.get(id=profile.status_id)
                except (OperationalError, DatabaseError) as retry_exc:
                    # Nếu vẫn lỗi, thử không lock
                    logger.warning(
                        "[SURVEILLANCE][CANCEL] Still failed with nowait=True for profile %s: %s. Trying without lock",
                        profile_id,
                        str(retry_exc)
                    )
                    profile = (
                        profile_manager
                        .select_related("status")
                        .get(id=profile_id)
                    )
            
            # Double check sau khi lock để đảm bảo profile chưa bị cancel bởi process khác
            if profile.actual_end_time:
                logger.info(
                    "[SURVEILLANCE][CANCEL] Profile %s đã có actual_end_time, có thể đã bị cancel bởi process khác",
                    profile_id,
                )
                return False, profile
            
            cancel_time = timezone.now()

            cancelled_status = status_manager.get(code="cancelled")
            profile.status = cancelled_status
            profile.cancel_reason = reason
            profile.actual_end_time = cancel_time
            profile.cancelled_by = cancelled_by

            metadata = profile.metadata or {}
            metadata.update({
                "cancelled_at": cancel_time.isoformat(),
                "cancel_reason": reason,
            })
            metadata.pop("overdue_check_eta", None)
            metadata.pop("overdue_check_task_id", None)
            metadata.pop("overdue_check_scheduled_at", None)
            metadata.pop("overdue_check_processed_at", None)
            if extra_metadata:
                metadata.update(extra_metadata)
            profile.metadata = metadata

            update_fields = [
                "status",
                "actual_end_time",
                "modified_on",
                "cancel_reason",
                "metadata",
            ]
            if cancelled_by is not None:
                update_fields.append("cancelled_by")
            profile.save(update_fields=update_fields)

            available_status = device_status_manager.get(code="available")
            assignments = assignment_manager.select_related("device").filter(profile=profile)
            for assignment in assignments:
                if assignment.device_id and assignment.device.status_id != available_status.id:
                    assignment.device.status = available_status
                    assignment.device.save(update_fields=["status"])

                # Release drone reservation if this profile owns it
                if assignment.device_id:
                    try:
                        from django.core.cache import cache
                        key = f"surveillance:drone_reservation:{assignment.device_id}"
                        existing = cache.get(key)
                        existing_profile_id = None
                        if isinstance(existing, int):
                            existing_profile_id = existing
                        elif isinstance(existing, dict):
                            try:
                                existing_profile_id = int(existing.get("profile_id"))
                            except Exception:
                                existing_profile_id = None
                        else:
                            try:
                                existing_profile_id = int(existing)
                            except Exception:
                                existing_profile_id = None
                        if existing_profile_id == profile.id:
                            cache.delete(key)
                    except Exception:
                        pass

            SurveillanceProfileAutomationService.clear_auto_launch(
                profile,
                timestamp=cancel_time,
                reason="cancelled",
            )
            return True, profile
        except SurveillanceProfile.DoesNotExist:
            logger.warning("SurveillanceProfile with id %s does not exist for cancellation", profile_id)
            raise ValidationError("Surveillance profile not found")
        except SurveillanceStatus.DoesNotExist:
            logger.error("SurveillanceStatus 'cancelled' not found when cancelling profile %s", profile_id)
            raise ValidationError("Cancellation status not configured")
        except DeviceStatus.DoesNotExist:
            logger.error("DeviceStatus 'available' not found when cancelling profile %s", profile_id)
            raise ValidationError("Available device status not configured")
        except Exception as exc:
            logger.exception("Error canceling surveillance profile %s: %s", profile_id, exc)
            return False, None
    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    @staticmethod
    def get_list(status: str = None) -> QuerySet:
        return SurveillanceProfileService.get_queryset_optimized(status).order_by("-id")
    @staticmethod
    def get_selected_list(start_time_start: str, start_time_end: str) -> QuerySet:
        queryset = SurveillanceProfile.objects.all().exclude(status__code__in=["rejected", "cancelled"])
        queryset = queryset.annotate(
            # Only use actual_start_time when BOTH actual_start_time and actual_end_time exist;
            # otherwise fall back to planned start_time.
            effective_start_time=Case(
                When(
                    actual_start_time__isnull=False,
                    actual_end_time__isnull=False,
                    then=F("actual_start_time"),
                ),
                default=F("start_time"),
            )
        )

        # Handle list input (from query parameters)
        if isinstance(start_time_start, list):
            start_time_start = start_time_start[0] if start_time_start else None
        if isinstance(start_time_end, list):
            start_time_end = start_time_end[0] if start_time_end else None
        
        if not start_time_start or not start_time_end:
            raise ValidationError("start_time_start and start_time_end are required")
        
        # Parse ISO 8601 datetime strings (format: 2025-12-10T17:00:00+00:00)
        # datetime.fromisoformat() supports both Z and +00:00 formats
        try:
            dt_start = datetime.fromisoformat(str(start_time_start).replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            raise ValidationError(f"Invalid start_time_start format: {start_time_start}") from e
        
        try:
            dt_end = datetime.fromisoformat(str(start_time_end).replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            raise ValidationError(f"Invalid start_time_end format: {start_time_end}") from e
        

        
        queryset = queryset.filter(
            effective_start_time__gte=dt_start,
            effective_start_time__lte=dt_end
        )
        
        queryset = queryset.order_by("-id").values("id", "name", "code", "status__code", "start_time", "actual_start_time", "actual_end_time")
        return queryset 
    @staticmethod
    def get_detail(profile_id: int) -> Optional[SurveillanceProfile]:
        try:
            return SurveillanceProfileService.get_queryset_optimized().filter(id=profile_id)
        except SurveillanceProfile.DoesNotExist:
            return None

    @staticmethod
    def get_detail_payload(profile_id: int, *, use_base_manager: bool = False) -> Optional[Dict[str, Any]]:
        queryset = SurveillanceProfileService.get_queryset_optimized(use_base_manager=use_base_manager).filter(id=profile_id)
        if not queryset.exists():
            return None

        profile_instance = queryset.first()
        data = SurveyMissionDetailOutSchema.from_queryset(queryset)

        drone_assignments_qs = SurveillanceProfileService._drone_prefetch_queryset().filter(profile=profile_instance)
        route_paths_map = SurveillanceProfileService.build_route_paths_for_assignments(
            drone_assignments_qs,
            profile_instance.mission,
        )
        for assignment in drone_assignments_qs:
            if assignment.log_path is None or assignment.log_path == '':
                # get log drone data
                flight_log_raw_data = FlightLogService.get_drone_log_raw_data(assignment.device.unit_id, assignment.profile.actual_start_time, assignment.profile.actual_end_time)
                # save flight_log_raw_data as json file to minio
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{assignment.device.unit_id}.json"
                log_path = minio_client.save_json(flight_log_raw_data, assignment.device.unit_id, filename)
                assignment.log_path = log_path
                assignment.save()

        assignments_data = SurveillanceProfileDroneOutSchema.from_queryset(drone_assignments_qs, many=True)
        for assignment_dict in assignments_data:
            assignment_id = assignment_dict.get("id")
            if assignment_id and assignment_id in route_paths_map:
                assignment_dict["route_path"] = route_paths_map[assignment_id]

        data["drone_assignments"] = assignments_data

        return data

    @staticmethod
    def _get_command_id_from_command_line(command_line: Optional[Dict]) -> Optional[int]:
        """Extract command_id from command_line dict."""
        if not command_line:
            return None
        
        try:
            # Try to get command_id from digit keys
            digit_keys = [
                key for key in command_line.keys() if isinstance(key, str) and key.isdigit()
            ]
            if digit_keys:
                return int(digit_keys[0])
            
            # Try to get from command field
            command = command_line.get("command")
            if isinstance(command, dict):
                return command.get("id")
            elif isinstance(command, (int, str)):
                try:
                    return int(command)
                except (ValueError, TypeError):
                    pass
            
            # Try command_id field
            command_id = command_line.get("command_id")
            if command_id is not None:
                try:
                    return int(command_id)
                except (ValueError, TypeError):
                    pass
        except Exception:
            pass
        
        return None

    @staticmethod
    def _get_overall_mission_end_command_id(
        mission: SurveyMission,
        waypoints_cache: Optional[Dict[int, List[Dict]]] = None,
    ) -> int:
        """
        Determine end command for the overall mission.

        Preference order:
        1) mission.return_to_home when explicitly set (False -> 21 LAND, True -> 20 RTL)
        2) If return_to_home is null/unknown: infer from last MissionWaypoint command_id (20/21)
        3) Default: RTL (20)
        """
        try:
            rth = getattr(mission, "return_to_home", None)
            if rth is True:
                return 20  # RTL
            if rth is False:
                return 21  # LAND
        except Exception:
            pass

        cmd_id: Optional[int] = None
        try:
            if waypoints_cache is not None and mission.id in waypoints_cache and waypoints_cache[mission.id]:
                last_wp = waypoints_cache[mission.id][-1]
                cmd_id = SurveillanceProfileService._get_command_id_from_command_line(last_wp.get("command_line"))
            else:
                last_cmd_line = (
                    mission.waypoints.order_by("-order")
                    .values_list("command_line", flat=True)
                    .first()
                )
                cmd_id = SurveillanceProfileService._get_command_id_from_command_line(last_cmd_line)
        except Exception:
            cmd_id = None

        if cmd_id in (20, 21):
            return int(cmd_id)

        return 20

    @staticmethod
    def _get_overall_mission_takeoff_point(
        mission: SurveyMission,
        waypoints_cache: Optional[Dict[int, List[Dict]]] = None,
    ) -> Optional[Tuple[float, float]]:
        """
        Determine overall mission takeoff/home point (lat, lon).

        Preference order:
        1) First waypoint with command_id == 22 (TAKEOFF)
        2) First waypoint with valid coordinates
        """
        waypoints: List[Dict[str, Any]] = []
        try:
            if waypoints_cache is not None and mission.id in waypoints_cache and waypoints_cache[mission.id]:
                waypoints = waypoints_cache[mission.id]
            else:
                waypoints = list(
                    mission.waypoints.order_by("order").values(
                        "id",
                        "order",
                        "name",
                        "latitude",
                        "longitude",
                        "command_line",
                        "frame",
                    )
                )
                if waypoints_cache is not None:
                    waypoints_cache[mission.id] = waypoints
        except Exception:
            waypoints = []

        def _safe_lat_lon(wp: Dict[str, Any]) -> Optional[Tuple[float, float]]:
            try:
                lat = wp.get("latitude")
                lon = wp.get("longitude")
                if lat is None or lon is None:
                    return None
                lat_f = float(lat)
                lon_f = float(lon)
                if lat_f == 0.0 and lon_f == 0.0:
                    return None
                return lat_f, lon_f
            except Exception:
                return None

        # Prefer TAKEOFF waypoint
        for wp in waypoints:
            try:
                cmd_id = SurveillanceProfileService._get_command_id_from_command_line(wp.get("command_line"))
                if cmd_id == 22:
                    point = _safe_lat_lon(wp)
                    if point:
                        return point
            except Exception:
                continue

        # Fallback: first valid coordinate
        for wp in waypoints:
            point = _safe_lat_lon(wp)
            if point:
                return point

        return None

    @staticmethod
    def _get_last_mission_waypoint_config() -> str:
        """
        Get "last_mission_waypoint" setting from AdminConfig.

        Normalizes legacy formats and always returns one of:
        - "land"
        - "return_to_launch"
        """
        default_value = "return_to_launch"

        raw_value: Any = None
        try:
            config = AdminConfig.objects.filter(name="Waypoint Settings").first()
            if config and isinstance(getattr(config, "settings", None), dict):
                raw_value = config.settings.get("last_mission_waypoint", default_value)
        except Exception:
            raw_value = None

        value: Any = raw_value if raw_value is not None else default_value

        # Current format (stored in DB): string "land" | "return_to_launch"
        if isinstance(value, str):
            v = value.strip().lower().replace("-", "_")
            if v == "land":
                return "land"
            if v in {"return_to_launch", "rtl", "return_to_home", "return_home", "return"}:
                return "return_to_launch"
            return default_value

        # Legacy format: dict {"land": bool, "return_to_launch": bool}
        if isinstance(value, dict):
            try:
                if bool(value.get("land")):
                    return "land"
                if bool(value.get("return_to_launch")) or bool(value.get("returnToLaunch")):
                    return "return_to_launch"
            except Exception:
                return default_value
            return default_value

        # Legacy format: list [{"name": "...", "value": ...}, ...]
        if isinstance(value, list):
            try:
                truthy = {True, 1, "1", "true", "True", "yes", "on"}
                for item in value:
                    if not isinstance(item, dict):
                        continue
                    name = item.get("name") or item.get("key")
                    if not name:
                        continue
                    name_norm = str(name).strip().lower().replace("-", "_")
                    item_value = item.get("value")
                    if item_value is None and "value " in item:
                        item_value = item.get("value ")
                    if item_value in truthy:
                        if name_norm == "land":
                            return "land"
                        if name_norm in {"return_to_launch", "rtl"}:
                            return "return_to_launch"
            except Exception:
                return default_value
            return default_value

        return default_value

    @staticmethod
    def _build_command_line_for_route(command_id: int, lat: float, lon: float, altitude: float = 0.0) -> Dict[str, Any]:
        """Build command_line dict for takeoff, land, RTL, or waypoint according to MAVLink standard."""
        # Command name mapping (MAVLink standard format)
        command_names = {
            22: "NAV_TAKEOFF",  # MAV_CMD_NAV_TAKEOFF
            21: "NAV_LAND",     # MAV_CMD_NAV_LAND
            20: "NAV_RETURN_TO_LAUNCH",  # MAV_CMD_NAV_RETURN_TO_LAUNCH
            16: "NAV_WAYPOINT",  # MAV_CMD_NAV_WAYPOINT
        }
        
        command_name = command_names.get(command_id, "NAV_WAYPOINT")
        
        # Build params array (7 elements) as strings (to match format of other waypoints)
        if command_id == 22:  # TAKEOFF
            params = ["0.0", "0.0", "0.0", "0", str(lat), str(lon), str(altitude)]
        elif command_id == 21:  # LAND
            params = ["0.0", "0.0", "0.0", "0", str(lat), str(lon), "0.0"]
        elif command_id == 16:  # NAV_WAYPOINT
            params = ["0.0", "0.0", "0.0", "0", str(lat), str(lon), str(altitude)]
        else:  # RTL (20)
            params = ["0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0"]
        
        return {
            str(command_id): {
                command_name: params
            }
        }

    @staticmethod
    def _add_waiting_coordinates_to_route_path(
        route_path: List[Dict[str, Any]],
        assignment: 'SurveillanceProfileDrone',
        all_mission_waypoints: Optional[List[Dict]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Add waiting_coordinates to route_path if exists.
        Adds waiting_coordinates after takeoff and at the end with land/rtl.
        
        Args:
            route_path: Existing route_path list
            assignment: Drone assignment instance
            all_mission_waypoints: Optional list of mission waypoints for getting config
            
        Returns:
            Updated route_path with waiting_coordinates added
        """
        if not route_path:
            return route_path
        
        # Parse waiting_coordinates
        waiting_coordinates_raw = assignment.waiting_coordinates
        waiting_lat = None
        waiting_lon = None
        waiting_alt = None
        
        if waiting_coordinates_raw:
            coords_list = None
            if isinstance(waiting_coordinates_raw, list):
                coords_list = waiting_coordinates_raw
            elif isinstance(waiting_coordinates_raw, str):
                try:
                    coords_list = json.loads(waiting_coordinates_raw)
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
            elif isinstance(waiting_coordinates_raw, dict):
                coords_list = list(waiting_coordinates_raw.values()) if waiting_coordinates_raw else None
            
            if coords_list and isinstance(coords_list, list) and len(coords_list) >= 2:
                try:
                    waiting_lat = float(coords_list[0])
                    waiting_lon = float(coords_list[1])
                    if len(coords_list) >= 3:
                        waiting_alt = float(coords_list[2])
                except (ValueError, TypeError, IndexError):
                    pass
        
        if waiting_lat is None or waiting_lon is None:
            return route_path
        
        # Get takeoff altitude from first waypoint
        takeoff_altitude = 0.0
        first_wp = route_path[0] if route_path else None
        if first_wp:
            try:
                # Try to get altitude from first waypoint
                if first_wp.get("altitude"):
                    try:
                        takeoff_altitude = float(first_wp["altitude"])
                    except (ValueError, TypeError):
                        pass
            except Exception:
                pass
        
        # Set waiting_alt from takeoff altitude if not provided
        if waiting_alt is None:
            waiting_alt = takeoff_altitude if takeoff_altitude > 0 else 0.0
        try:
            waiting_alt = float(waiting_alt)
        except (ValueError, TypeError):
            waiting_alt = 0.0
        
        # Get frame from first waypoint
        frame_id = first_wp.get("frame_id", "3") if first_wp else "3"
        frame_name = first_wp.get("frame_name", "GLOBAL_RELATIVE_ALT") if first_wp else "GLOBAL_RELATIVE_ALT"
        
        # Find takeoff waypoint (command_id == "22")
        takeoff_index = None
        for idx, wp in enumerate(route_path):
            if wp.get("command_id") == "22":  # TAKEOFF
                takeoff_index = idx
                break
        
        # Add waiting_coordinates after takeoff
        if takeoff_index is not None:
            # Insert after takeoff
            takeoff_wp = route_path[takeoff_index]
            takeoff_lat = takeoff_wp.get("latitude")
            takeoff_lon = takeoff_wp.get("longitude")
            
            # Calculate distance from takeoff to waiting_coordinates
            distance_to_waiting = 0.0
            if takeoff_lat and takeoff_lon:
                try:
                    distance_to_waiting = geodesic(
                        (float(takeoff_lat), float(takeoff_lon)),
                        (waiting_lat, waiting_lon),
                    ).kilometers
                except (ValueError, TypeError):
                    pass
            
            # Calculate cumulative distance up to takeoff
            cumulative_distance = takeoff_wp.get("distance_from_start", 0.0)
            try:
                cumulative_distance = float(cumulative_distance)
            except (ValueError, TypeError):
                cumulative_distance = 0.0
            
            waiting_command_name_dict = {"16": "MAV_CMD_16"}
            waiting_params_dict = {"16": [0, 0, 0, 0, waiting_lat, waiting_lon, waiting_alt]}
            
            # Insert waiting_coordinates after takeoff
            waiting_order = takeoff_wp.get("order", 1)
            try:
                waiting_order = float(waiting_order) + 0.5
            except (ValueError, TypeError):
                waiting_order = 1.5
            
            waiting_wp = {
                "order": waiting_order,
                "latitude": waiting_lat,
                "longitude": waiting_lon,
                "altitude": str(waiting_alt),
                "distance_from_start": round(cumulative_distance + distance_to_waiting, 3),
                "type": "waypoint",
                "mission_waypoint_id": None,
                "name": "Waiting Point",
                "command_id": "16",  # NAV_WAYPOINT
                "command_name": waiting_command_name_dict,
                "params": waiting_params_dict,
                "frame_id": frame_id,
                "frame_name": frame_name,
            }
            
            route_path.insert(takeoff_index + 1, waiting_wp)
            
            # Recalculate distances for subsequent waypoints
            prev_distance = cumulative_distance + distance_to_waiting
            for idx in range(takeoff_index + 2, len(route_path)):
                wp = route_path[idx]
                prev_wp = route_path[idx - 1]
                try:
                    prev_lat = float(prev_wp.get("latitude", 0))
                    prev_lon = float(prev_wp.get("longitude", 0))
                    curr_lat = float(wp.get("latitude", 0))
                    curr_lon = float(wp.get("longitude", 0))
                    distance_km = geodesic((prev_lat, prev_lon), (curr_lat, curr_lon)).kilometers
                    prev_distance += distance_km
                    wp["distance_from_start"] = round(prev_distance, 3)
                except (ValueError, TypeError):
                    pass
        
        # Add waiting_coordinates at the end with land/rtl
        last_wp = route_path[-1] if route_path else None
        if last_wp:
            last_command_id = last_wp.get("command_id")
            
            # Get config for last mission waypoint
            last_mission_config = SurveillanceProfileService._get_last_mission_waypoint_config()
            
            # Determine which command to use
            if last_mission_config == "land":
                end_command_id = 21  # LAND
            else:
                end_command_id = 20  # RTL
            
            # Calculate cumulative distance up to last waypoint
            cumulative_distance = last_wp.get("distance_from_start", 0.0)
            try:
                cumulative_distance = float(cumulative_distance)
            except (ValueError, TypeError):
                cumulative_distance = 0.0
            

            if last_command_id in ["21", "20"]:
                route_path.pop()

                if route_path:
                    last_wp = route_path[-1]
                    cumulative_distance = last_wp.get("distance_from_start", 0.0)
                    try:
                        cumulative_distance = float(cumulative_distance)
                    except (ValueError, TypeError):
                        cumulative_distance = 0.0
            
            # Calculate distance from last waypoint to waiting_coordinates (for land/rtl)
            last_lat = last_wp.get("latitude") if last_wp else None
            last_lon = last_wp.get("longitude") if last_wp else None
            distance_to_end = 0.0
            if last_lat and last_lon:
                try:
                    distance_to_end = geodesic(
                        (float(last_lat), float(last_lon)),
                        (waiting_lat, waiting_lon),
                    ).kilometers
                except (ValueError, TypeError):
                    pass
            
            # Build land/rtl command with waiting coordinates
            end_command_name_dict = {str(end_command_id): f"MAV_CMD_{end_command_id}"}
            if end_command_id == 21:  # LAND
                end_params_dict = {str(end_command_id): [0, 0, 0, 0, waiting_lat, waiting_lon, waiting_alt]}
            else:  # RTL (20)
                end_params_dict = {str(end_command_id): [0, 0, 0, 0, 0, 0, 0]}
            
            # Add land/rtl at waiting_coordinates (no separate waiting point)
            end_order = last_wp.get("order", len(route_path)) if last_wp else len(route_path)
            try:
                end_order = float(end_order)
            except (ValueError, TypeError):
                end_order = len(route_path)
            
            end_wp = {
                "order": end_order + 0.5,
                "latitude": waiting_lat,
                "longitude": waiting_lon,
                "altitude": str(waiting_alt),
                "distance_from_start": round(cumulative_distance + distance_to_end, 3),
                "type": "waypoint",
                "mission_waypoint_id": None,
                "name": "Waiting Point",
                "command_id": str(end_command_id),
                "command_name": end_command_name_dict,
                "params": end_params_dict,
                "frame_id": frame_id,
                "frame_name": frame_name,
            }
            
            route_path.append(end_wp)
        
        return route_path

    @staticmethod
    def _build_route_path_for_assignment(
        assignment: SurveillanceProfileDrone,
        mission: SurveyMission,
        waypoints_cache: Optional[Dict[int, List[Dict]]] = None,
        mission_end_command_id: Optional[int] = None,
        mission_takeoff_point: Optional[Tuple[float, float]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Build route_path for a drone assignment based on start and end waypoints.
        Ensures route_path starts with takeoff and ends with land or RTL.
        Nếu mission có from_route hoặc drone_segments, sử dụng route_path từ drone_segments.
        
        Args:
            assignment: Drone assignment instance
            mission: Survey mission instance
            waypoints_cache: Optional cache of waypoints by mission_id to avoid repeated queries
            mission_end_command_id: Overall mission end command (20=RTL, 21=LAND) used when a segment needs an end command
            mission_takeoff_point: Overall mission takeoff/home point (lat, lon) used for synthetic takeoff/RTL
        """
        
        if not assignment.start_waypoint_id or not assignment.end_waypoint_id:
            return None

        try:
            if mission_end_command_id is None:
                mission_end_command_id = SurveillanceProfileService._get_overall_mission_end_command_id(
                    mission, waypoints_cache
                )
            if mission_takeoff_point is None:
                mission_takeoff_point = SurveillanceProfileService._get_overall_mission_takeoff_point(
                    mission, waypoints_cache
                )
            start_order = assignment.start_waypoint.order
            end_order = assignment.end_waypoint.order
            
            # Logic 1: Nếu mission có from_route hoặc drone_segments, build từ QGC mission trong drone_segments
            # QUAN TRỌNG: Giữ nguyên số lượng và thứ tự waypoint, KHÔNG thêm custom waypoints
            # (Tương tự logic trong _build_segments_from_imported_routes)
            if (getattr(mission, 'from_route', False) or 
                (hasattr(mission, 'drone_segments') and mission.drone_segments)):
                
                # Lấy waypoints từ database để map mission_waypoint_id
                if waypoints_cache is not None and mission.id in waypoints_cache:
                    all_mission_waypoints = waypoints_cache[mission.id]
                else:
                    all_mission_waypoints = list(
                        mission.waypoints.order_by("order")
                        .values("id", "order", "latitude", "longitude", "name", "command_line", "frame")
                    )
                    if waypoints_cache is not None:
                        waypoints_cache[mission.id] = all_mission_waypoints
                
                # Filter waypoints trong range này - GIỮ NGUYÊN THỨ TỰ
                # QUAN TRỌNG: Phải bao gồm TẤT CẢ waypoints từ start_order đến end_order (bao gồm cả 2 điểm đầu cuối)
                route_waypoints = [
                    wp for wp in all_mission_waypoints
                    if wp.get('order') is not None and start_order <= wp.get('order') <= end_order
                ]
                
                # Sắp xếp lại theo order để đảm bảo thứ tự đúng (phòng trường hợp all_mission_waypoints không được sort)
                route_waypoints = sorted(route_waypoints, key=lambda x: x.get('order', 0))
                
                if not route_waypoints:
                    logger.warning(
                        "No waypoints found for assignment %s (from_route/drone_segments): start_order=%d, end_order=%d",
                        assignment.id, start_order, end_order
                    )
                    return None
                
                # Validation: Đảm bảo số lượng waypoints khớp với expected count
                expected_count = end_order - start_order + 1
                actual_count = len(route_waypoints)
                if actual_count != expected_count:
                    logger.warning(
                        "Waypoint count mismatch for assignment %s: expected=%d (from %d to %d), actual=%d. "
                        "Some waypoints may be missing in database.",
                        assignment.id, expected_count, start_order, end_order, actual_count
                    )
                
                # Validation: Đảm bảo first và last waypoint khớp với start_order và end_order
                first_wp_order = route_waypoints[0].get('order')
                last_wp_order = route_waypoints[-1].get('order')
                if first_wp_order != start_order or last_wp_order != end_order:
                    logger.warning(
                        "Waypoint range mismatch for assignment %s: expected start=%d end=%d, "
                        "actual start=%d end=%d",
                        assignment.id, start_order, end_order, first_wp_order, last_wp_order
                    )
                
                # Tìm drone_segment tương ứng với assignment này (nếu có)
                drone_segment = None
                qgc_mission = None
                route_id = None
                if mission.drone_segments and isinstance(mission.drone_segments, list):
                    for segment in mission.drone_segments:
                        if (segment.get('start_waypoint_order') == start_order and
                            segment.get('end_waypoint_order') == end_order):
                            drone_segment = segment
                            qgc_mission = segment.get('qgc_mission')
                            route_id = segment.get('route_id')
                            break
                
                # Build route_path từ mission waypoints - GIỮ NGUYÊN SỐ LƯỢNG VÀ THỨ TỰ
                # Map với qgc_items nếu có để lấy command/params/frame chính xác
                route_path = []
                cumulative_distance = 0.0
                
                # Tạo map từ qgc_mission items nếu có (để lấy command/params/frame)
                qgc_items_map = {}
                if qgc_mission and not route_id:
                    mission_data = qgc_mission.get('mission', {})
                    items = mission_data.get('items', [])
                    # Map items theo doJumpId để có thể lookup sau
                    for item in items:
                        do_jump_id = item.get('doJumpId')
                        if do_jump_id is not None:
                            qgc_items_map[do_jump_id] = item
                
                # Build route_path từ mission waypoints và map với qgc_items
                # QUAN TRỌNG: Loop qua TẤT CẢ waypoints trong range (từ start_order đến end_order)
                # để đảm bảo bao gồm đầy đủ các điểm của route, không bỏ sót điểm nào
                # route_waypoints đã được filter và sort theo order, bao gồm cả start và end waypoint
                for i, wp in enumerate(route_waypoints):
                    wp_order = wp.get('order')
                    
                    # Tính distance từ điểm trước
                    if i > 0:
                        try:
                            prev_wp = route_waypoints[i - 1]
                            distance_km = geodesic(
                                (float(prev_wp.get('latitude', 0)), float(prev_wp.get('longitude', 0))),
                                (float(wp.get('latitude', 0)), float(wp.get('longitude', 0))),
                            ).kilometers
                            cumulative_distance += distance_km
                        except (ValueError, TypeError):
                            pass
                    
                    # Tìm qgc_item tương ứng (nếu có) để lấy command/params/frame
                    qgc_item = None
                    if qgc_items_map:
                        for do_jump_id, item in qgc_items_map.items():
                            params = item.get('params', [])
                            if isinstance(params, list) and len(params) >= 7:
                                item_lat = params[4] if params[4] is not None and params[4] != 0.0 else None
                                item_lon = params[5] if params[5] is not None and params[5] != 0.0 else None
                                if item_lat and item_lon:
                                    wp_lat = float(wp.get('latitude', 0))
                                    wp_lon = float(wp.get('longitude', 0))
                                    # So sánh với độ chính xác hợp lý (khoảng 0.0001 độ ≈ 11m)
                                    if abs(item_lat - wp_lat) < 0.0001 and abs(item_lon - wp_lon) < 0.0001:
                                        qgc_item = item
                                        break
                    
                    # Extract command/params/frame từ qgc_item hoặc từ waypoint trong database
                    if qgc_item:
                        command_id = str(qgc_item.get('command', 16))
                        params = {command_id: qgc_item.get('params', [])}
                        frame = qgc_item.get('frame', 3)
                        frame_id = str(frame)
                        frame_name = 'GLOBAL_RELATIVE_ALT' if frame == 3 else 'GLOBAL'
                        command_name = {command_id: f'MAV_CMD_{qgc_item.get("command", 16)}'}
                        item_params = qgc_item.get('params', [])
                        altitude = item_params[6] if (isinstance(item_params, list) and len(item_params) >= 7 and item_params[6] is not None and item_params[6] != 0.0) else None
                    else:
                        # Fallback: sử dụng thông tin từ waypoint trong database
                        command_line = wp.get('command_line', {})
                        command_id = list(command_line.keys())[0] if command_line else "16"
                        command_name = list(command_line.values())[0] if command_line else {command_id: "MAV_CMD_16"}
                        params = command_name if isinstance(command_name, dict) else {command_id: command_name}
                        frame = wp.get('frame', {})
                        frame_id = list(frame.keys())[0] if frame else "3"
                        frame_name = list(frame.values())[0] if frame else "GLOBAL_RELATIVE_ALT"
                        # Extract altitude từ command_line params
                        altitude = None
                        if command_line:
                            for cmd_data in command_line.values():
                                if isinstance(cmd_data, dict):
                                    for cmd_params in cmd_data.values():
                                        if isinstance(cmd_params, list) and len(cmd_params) >= 7:
                                            altitude = cmd_params[6]
                                            break
                                elif isinstance(cmd_data, list) and len(cmd_data) >= 7:
                                    altitude = cmd_data[6]
                                    break
                    
                    route_path.append({
                        "order": wp_order,
                        "latitude": float(wp.get('latitude', 0)),
                        "longitude": float(wp.get('longitude', 0)),
                        "altitude": altitude,
                        "distance_from_start": round(cumulative_distance, 3),
                        "type": "waypoint",
                        "mission_waypoint_id": wp.get('id'),
                        "name": wp.get('name') or f"Waypoint {wp_order}",
                        "command_id": command_id,
                        "command_name": command_name,
                        "params": params,
                        "frame_id": frame_id,
                        "frame_name": frame_name,
                    })
                
                # Return route_path - KHÔNG thêm custom waypoints (DO_GRIPPER, waiting_coordinates)
                # Đảm bảo giữ nguyên số lượng và thứ tự waypoint theo đúng mission
                # NOTE: Nếu Flightbird yêu cầu route_path tuân thủ rule (Takeoff/Gripper/Waiting/StartSep/...),
                # thì nhánh này PHẢI đảm bảo QGC mission đã chứa sẵn các command đó. Nếu không, payload sẽ thiếu steps.
                try:
                    required_cmds = {"22", "16", "203"}  # TAKEOFF, WAYPOINT, CAMERA_TRIGGER (DO_DIGICAM_CONTROL)
                    cmds_in_route = {str(wp.get("command_id")) for wp in route_path if wp.get("command_id") is not None}
                    missing = sorted(list(required_cmds - cmds_in_route))
                    if missing:
                        logger.warning(
                            "Flightbird route_path (from_route/drone_segments) for assignment %s may miss required commands per rule. missing_command_ids=%s",
                            assignment.id,
                            missing,
                        )
                except Exception:
                    pass
                return route_path
            
            # Logic 2: Nếu KHÔNG có from_route hoặc drone_segments, build từ waypoints trong database
            # và thêm custom waypoints (DO_GRIPPER, waiting_coordinates) như logic cũ
            if waypoints_cache is not None and mission.id in waypoints_cache:
                all_mission_waypoints = waypoints_cache[mission.id]
            else:
                all_mission_waypoints = list(
                    mission.waypoints.order_by("order")
                    .values("id", "order", "name", "latitude", "longitude", "command_line", "frame")
                )
                if waypoints_cache is not None:
                    waypoints_cache[mission.id] = all_mission_waypoints
            
            # Filter waypoints for this assignment's range
            
            all_waypoints = [
                wp for wp in all_mission_waypoints
                if start_order <= wp["order"] <= end_order
            ]
            
            # Debug: Log filtering info
            
            # Debug: Log filtered waypoints
            if all_waypoints:
                logger.debug(
                    "Filtered waypoints for assignment %s: count=%d, first_order=%d, last_order=%d",
                    assignment.id, len(all_waypoints), all_waypoints[0]["order"], all_waypoints[-1]["order"]
                )
            else:
                logger.warning(
                    "No waypoints found for assignment %s: start_order=%d, end_order=%d",
                    assignment.id, start_order, end_order
                )
                return None

            # Get first and last waypoints
            first_wp = all_waypoints[0]
            last_wp = all_waypoints[-1]
            
            # Get command_id for first and last waypoints
            first_command_id = SurveillanceProfileService._get_command_id_from_command_line(first_wp.get("command_line"))
            last_command_id = SurveillanceProfileService._get_command_id_from_command_line(last_wp.get("command_line"))

            route_path = []
            cumulative_distance = 0.0
            

            waiting_coordinates_raw = assignment.waiting_coordinates
            waiting_lat = None
            waiting_lon = None
            waiting_alt = None 
            waiting_coordinates = None  
            
            if waiting_coordinates_raw:
                # Try to parse as list first
                coords_list = None
                if isinstance(waiting_coordinates_raw, list):
                    coords_list = waiting_coordinates_raw
                elif isinstance(waiting_coordinates_raw, str):
                    # Try to parse JSON string
                    try:
                        coords_list = json.loads(waiting_coordinates_raw)
                    except (json.JSONDecodeError, ValueError, TypeError):
                        pass
                elif isinstance(waiting_coordinates_raw, dict):
                    # If it's a dict, try to extract values
                    coords_list = list(waiting_coordinates_raw.values()) if waiting_coordinates_raw else None
                
                # Parse coordinates from list
                if coords_list and isinstance(coords_list, list) and len(coords_list) >= 2:
                    try:
                        waiting_lat = float(coords_list[0])
                        waiting_lon = float(coords_list[1])
                        if len(coords_list) >= 3:
                            waiting_alt = float(coords_list[2])
                        # Mark as valid if we got lat and lon
                        if waiting_lat is not None and waiting_lon is not None:
                            waiting_coordinates = True
                    except (ValueError, TypeError, IndexError):
                        pass
            
            frame_id = "3" 
            frame_name = "GLOBAL_RELATIVE_ALT"
            if first_wp.get("frame"):
                try:
                    frame_key = list(first_wp["frame"].keys())[0] if isinstance(first_wp["frame"], dict) else "3"
                    frame_id = str(frame_key) if frame_key else "3"
                    frame_name = list(first_wp["frame"].values())[0] if isinstance(first_wp["frame"], dict) else "GLOBAL_RELATIVE_ALT"
                except (KeyError, IndexError, TypeError, ValueError):
                    frame_id = "3"
                    frame_name = "GLOBAL_RELATIVE_ALT"
            
            takeoff_altitude = 0.0
            if first_wp.get("command_line"):
                try:
                    for cmd_data in first_wp["command_line"].values():
                        if isinstance(cmd_data, dict):
                            for params in cmd_data.values():
                                if isinstance(params, list) and len(params) >= 7:
                                    try:
                                        takeoff_altitude = float(params[6])
                                    except (ValueError, TypeError):
                                        pass
                                    break
                        elif isinstance(cmd_data, list) and len(cmd_data) >= 7:
                            try:
                                takeoff_altitude = float(cmd_data[6])
                            except (ValueError, TypeError):
                                pass
                            break
                except (KeyError, IndexError, TypeError):
                    pass
            
            if waiting_lat is not None and waiting_lon is not None:
                if waiting_alt is None:
                    waiting_alt = takeoff_altitude if takeoff_altitude > 0 else 0.0
                if waiting_alt is None:
                    waiting_alt = 0.0
                try:
                    waiting_alt = float(waiting_alt)
                except (ValueError, TypeError):
                    waiting_alt = 0.0
            
            first_lat = float(first_wp["latitude"]) if first_wp.get("latitude") else None
            first_lon = float(first_wp["longitude"]) if first_wp.get("longitude") else None
            
            # Xác định start_idx: nếu điểm đầu tiên là takeoff (command_id == 22) thì start_idx = 1, ngược lại = 0
            start_idx = 1 if (first_command_id == 22) else 0
            
            # QUAN TRỌNG: Chỉ thêm takeoff nếu điểm đầu tiên không phải là takeoff (first_command_id != 22)
            # Nếu đã có takeoff rồi thì không thêm nữa
            if first_command_id != 22 and first_lat is not None and first_lon is not None:
                # Prefer mission takeoff/home point for synthetic takeoff (so each segment is self-contained)
                takeoff_lat = first_lat
                takeoff_lon = first_lon
                if mission_takeoff_point and len(mission_takeoff_point) == 2:
                    try:
                        takeoff_lat = float(mission_takeoff_point[0])
                        takeoff_lon = float(mission_takeoff_point[1])
                    except Exception:
                        takeoff_lat = first_lat
                        takeoff_lon = first_lon
                
                takeoff_command_line = SurveillanceProfileService._build_command_line_for_route(
                    22, takeoff_lat, takeoff_lon, takeoff_altitude
                )
                
                command_name_dict = takeoff_command_line["22"]
                params_dict = takeoff_command_line["22"]
                
                # Rule 1: Takeoff (độ cao separated)
                takeoff_order = float(first_wp["order"] or 0) - 0.2
                route_path.append({
                    "order": takeoff_order,
                    "latitude": takeoff_lat,
                    "longitude": takeoff_lon,
                    "altitude": str(takeoff_altitude),  
                    "distance_from_start": 0,  
                    "type": "waypoint",  
                    "mission_waypoint_id": None,
                    "name": f"Waypoint {int(first_wp['order'])}",  
                    "command_id": "22",  
                    "command_name": command_name_dict,  
                    "params": params_dict,  
                    "frame_id": frame_id,  
                    "frame_name": frame_name,
                })
                
                # Rule 2: Gripper Mechanism(param2=0) immediately after Takeoff
                try:
                    gripper_command_id = "211"
                    gripper_command_name_dict = {gripper_command_id: "MAV_CMD_DO_GRIPPER"}
                    gripper_params_dict = {gripper_command_id: ["0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0"]}
                    # Set param 2 = 0 (open/release gripper)
                    gripper_params_dict[gripper_command_id][1] = "0.0"
                    
                    gripper_order = takeoff_order + 0.05
                    
                    route_path.append({
                        "order": gripper_order,
                        "latitude": takeoff_lat,
                        "longitude": takeoff_lon,
                        "altitude": str(takeoff_altitude),
                        "distance_from_start": 0.0,
                        "type": "waypoint",
                        "mission_waypoint_id": None,
                        "name": "Gripper Open",
                        "command_id": gripper_command_id,
                        "command_name": gripper_command_name_dict,
                        "params": gripper_params_dict,
                        "frame_id": frame_id,
                        "frame_name": frame_name,
                    })
                except Exception as e:
                    logger.warning("Error adding Gripper Open after synthetic takeoff for assignment %s: %s", assignment.id, e)
                
                if waiting_coordinates and waiting_lat is not None and waiting_lon is not None:
                    try:
                        distance_km = geodesic(
                            (takeoff_lat, takeoff_lon),
                            (waiting_lat, waiting_lon),
                        ).kilometers
                        cumulative_distance += distance_km
                    except (ValueError, TypeError):
                        pass
            
            if first_command_id == 22 and first_lat is not None and first_lon is not None:
                # Rule 1: Takeoff (độ cao separated)
                takeoff_order = float(first_wp["order"] or 0) - 0.2
                route_path.append({
                    "order": takeoff_order,
                    "latitude": float(first_wp["latitude"]) if first_wp.get("latitude") else None,
                    "longitude": float(first_wp["longitude"]) if first_wp.get("longitude") else None,
                    "altitude": takeoff_altitude,
                    "distance_from_start": 0,
                    "type": "waypoint",
                    "mission_waypoint_id": first_wp["id"],
                    "name": first_wp.get("name") or f"Waypoint {first_wp['order']}",
                    "command_id": list(first_wp.get("command_line", {}).keys())[0] if first_wp.get("command_line") else None,
                    "command_name": list(first_wp.get("command_line", {}).values())[0] if first_wp.get("command_line") else None,
                    "params": list(first_wp.get("command_line", {}).values())[0] if first_wp.get("command_line") else None,
                    "frame_id": list(first_wp.get("frame", {}).keys())[0] if first_wp.get("frame") else None,
                    "frame_name": list(first_wp.get("frame", {}).values())[0] if first_wp.get("frame") else None,
                })
                
                # Rule 2: Gripper Mechanism(param2=0) immediately after Takeoff
                try:
                    gripper_command_id = "211"
                    gripper_command_name_dict = {gripper_command_id: "MAV_CMD_DO_GRIPPER"}
                    gripper_params_dict = {gripper_command_id: ["0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0"]}
                    # Set param 2 = 0 (open/release gripper)
                    gripper_params_dict[gripper_command_id][1] = "0.0"
                    
                    gripper_order = takeoff_order + 0.05
                    
                    route_path.append({
                        "order": gripper_order,
                        "latitude": first_lat,
                        "longitude": first_lon,
                        "altitude": takeoff_altitude,
                        "distance_from_start": 0.0,
                        "type": "waypoint",
                        "mission_waypoint_id": None,
                        "name": "Gripper Open",
                        "command_id": gripper_command_id,
                        "command_name": gripper_command_name_dict,
                        "params": gripper_params_dict,
                        "frame_id": list(first_wp.get("frame", {}).keys())[0] if first_wp.get("frame") else frame_id,
                        "frame_name": list(first_wp.get("frame", {}).values())[0] if first_wp.get("frame") else frame_name,
                    })
                except Exception as e:
                    logger.warning("Error adding Gripper Open after existing takeoff for assignment %s: %s", assignment.id, e)
                
                # Tính distance từ takeoff đến điểm tiếp theo (waiting point hoặc start point)
                if waiting_lat is not None and waiting_lon is not None:
                    try:
                        distance_km = geodesic(
                            (first_lat, first_lon),
                            (waiting_lat, waiting_lon),
                        ).kilometers
                        cumulative_distance += distance_km
                    except (ValueError, TypeError):
                        pass
                elif len(all_waypoints) > start_idx:
                    # Nếu không có waiting point, tính distance từ takeoff đến start point
                    try:
                        start_wp_for_distance = all_waypoints[start_idx]
                        distance_km = geodesic(
                            (first_lat, first_lon),
                            (float(start_wp_for_distance["latitude"]), float(start_wp_for_distance["longitude"])),
                        ).kilometers
                        cumulative_distance += distance_km
                    except (ValueError, TypeError, IndexError):
                        pass
            
            # Thứ tự mong muốn: takeoff -> waiting point (nếu có) -> start point -> DO_GRIPPER (open) -> route -> DO_GRIPPER (close) -> land/rtl
            # Bước 1: Thêm waiting point sau takeoff (nếu có)
            if waiting_lat is not None and waiting_lon is not None:
                try:
                    if waiting_alt is None:
                        waiting_alt = takeoff_altitude if takeoff_altitude > 0 else 0.0
                    try:
                        waiting_alt = float(waiting_alt)
                    except (ValueError, TypeError):
                        waiting_alt = 0.0
                    
                    if not route_path and first_lat is not None and first_lon is not None:
                        try:
                            distance_km = geodesic(
                                (first_lat, first_lon),
                                (waiting_lat, waiting_lon),
                            ).kilometers
                            cumulative_distance += distance_km
                        except (ValueError, TypeError):
                            pass
                    
                    waiting_command_name_dict = {"16": "MAV_CMD_16"}
                    waiting_params_dict = {"16": [0, 0, 0, 0, waiting_lat, waiting_lon, waiting_alt]}
                    
                    # Rule 3: Điểm tọa độ chờ (waiting coordinate) - luôn SAU takeoff
                    base_order = None
                    if route_path:
                        base_order = route_path[-1].get("order")
                    if base_order is None:
                        base_order = first_wp.get("order")
                    try:
                        base_order = float(base_order)
                    except (ValueError, TypeError):
                        base_order = float(first_wp.get("order") or 0)
                    waiting_order = base_order + 0.05
                    
                    route_path.append({
                        "order": waiting_order,
                        "latitude": waiting_lat,
                        "longitude": waiting_lon,
                        "altitude": str(waiting_alt),
                        "distance_from_start": round(cumulative_distance, 3),
                        "type": "waypoint",
                        "mission_waypoint_id": None,
                        "name": "Waiting Point",
                        "command_id": "16",  
                        "command_name": waiting_command_name_dict,
                        "params": waiting_params_dict,
                        "frame_id": frame_id,
                        "frame_name": frame_name,
                    })
                except Exception as e:
                    logger.warning("Error adding waiting_coordinates to route_path for assignment %s: %s", assignment.id, e)

            # Bước 2: Thêm start point (waypoint đầu tiên của route) và DO_GRIPPER open ngay sau đó
       

            has_waiting_coords = waiting_lat is not None and waiting_lon is not None
            # Nếu mission đã có LAND/RTL ở cuối range, tách LAND/RTL ra để luôn có thể chèn:
            # End Separated -> (Gripper Close) -> (Waiting End) -> LAND/RTL
            has_end_command_in_mission = last_command_id in [21, 20]
            end_idx = len(all_waypoints) - 1 if has_end_command_in_mission else len(all_waypoints)

            waypoints_added_count = 0
            
            # Thêm start point đầu tiên (nếu có)
            if start_idx < len(all_waypoints) and start_idx < end_idx:
                start_wp = all_waypoints[start_idx]
                
                # Tính distance từ điểm trước (takeoff hoặc waiting point)
                if route_path:
                    try:
                        prev_wp = route_path[-1]
                        distance_km = geodesic(
                            (prev_wp.get("latitude"), prev_wp.get("longitude")),
                            (float(start_wp["latitude"]), float(start_wp["longitude"])),
                        ).kilometers
                        cumulative_distance += distance_km
                    except (ValueError, TypeError):
                        pass
                
                # Extract altitude từ start waypoint
                altitude = None
                if start_wp.get("command_line"):
                    try:
                        for cmd_data in start_wp["command_line"].values():
                            if isinstance(cmd_data, dict):
                                for params in cmd_data.values():
                                    if isinstance(params, list) and len(params) >= 7:
                                        altitude = params[6]
                                        break
                            elif isinstance(cmd_data, list) and len(cmd_data) >= 7:
                                altitude = cmd_data[6]
                                break
                    except (KeyError, IndexError, TypeError):
                        pass

                # Rule 4: Điểm đầu mission (độ cao separated)
                # RULE: Start Separated comes AFTER Waiting Point or Gripper Open
                try:
                    base_order = None
                    if route_path:
                        base_order = route_path[-1].get("order")
                    if base_order is None:
                        base_order = float(first_wp.get("order") or 0)
                    
                    start_sep_order = float(base_order) + 0.05
                    start_sep_lat = float(start_wp["latitude"]) if start_wp.get("latitude") else None
                    start_sep_lon = float(start_wp["longitude"]) if start_wp.get("longitude") else None
                    if start_sep_lat is not None and start_sep_lon is not None:
                        start_sep_alt = altitude if altitude is not None else str(takeoff_altitude)
                        route_path.append({
                            "order": start_sep_order,
                            "latitude": start_sep_lat,
                            "longitude": start_sep_lon,
                            "altitude": start_sep_alt,
                            "distance_from_start": round(cumulative_distance, 3),
                            "type": "waypoint",
                            "mission_waypoint_id": None,
                            "name": "Start Separated",
                            "command_id": "16",
                            "command_name": {"16": "MAV_CMD_16"},
                            "params": {"16": [0, 0, 0, 0, start_sep_lat, start_sep_lon, start_sep_alt]},
                            "frame_id": list(start_wp.get("frame", {}).keys())[0] if start_wp.get("frame") else frame_id,
                            "frame_name": list(start_wp.get("frame", {}).values())[0] if start_wp.get("frame") else frame_name,
                        })
                except Exception as e:
                    logger.warning("Error adding Start Separated point for assignment %s: %s", assignment.id, e)
                
                # Rule 5: Điểm đầu mission (độ cao mission)
                route_path.append({
                    "order": start_wp["order"],
                    "latitude": float(start_wp["latitude"]) if start_wp["latitude"] else None,
                    "longitude": float(start_wp["longitude"]) if start_wp["longitude"] else None,
                    "altitude": altitude,
                    "distance_from_start": round(cumulative_distance, 3),
                    "type": "waypoint",
                    "mission_waypoint_id": start_wp["id"],
                    "name": start_wp.get("name") or f"Waypoint {start_wp['order']}",
                    "command_id": list(start_wp.get("command_line", {}).keys())[0] if start_wp.get("command_line") else None,
                    "command_name": list(start_wp.get("command_line", {}).values())[0] if start_wp.get("command_line") else None,
                    "params": list(start_wp.get("command_line", {}).values())[0] if start_wp.get("command_line") else None,
                    "frame_id": list(start_wp.get("frame", {}).keys())[0] if start_wp.get("frame") else None,
                    "frame_name": list(start_wp.get("frame", {}).values())[0] if start_wp.get("frame") else None,
                })
                waypoints_added_count += 1
            
            # Bước 4: Thêm các waypoint còn lại (từ start_idx + 1 đến end_idx)
            for idx, wp in enumerate(all_waypoints[start_idx + 1:end_idx], start=start_idx + 1):
                if idx > start_idx:
                    prev_wp = all_waypoints[idx - 1]
                    try:
                        distance_km = geodesic(
                            (float(prev_wp["latitude"]), float(prev_wp["longitude"])),
                            (float(wp["latitude"]), float(wp["longitude"])),
                        ).kilometers
                        cumulative_distance += distance_km
                    except (ValueError, TypeError):
                        pass
                altitude = None
                if wp.get("command_line"):
                    try:
                        for cmd_data in wp["command_line"].values():
                            if isinstance(cmd_data, dict):
                                for params in cmd_data.values():
                                    if isinstance(params, list) and len(params) >= 7:
                                        altitude = params[6]
                                        break
                            elif isinstance(cmd_data, list) and len(cmd_data) >= 7:
                                altitude = cmd_data[6]
                                break
                    except (KeyError, IndexError, TypeError):
                        pass

                route_path.append({
                    "order": wp["order"],
                    "latitude": float(wp["latitude"]) if wp["latitude"] else None,
                    "longitude": float(wp["longitude"]) if wp["longitude"] else None,
                    "altitude": altitude,
                    "distance_from_start": round(cumulative_distance, 3),
                    "type": "waypoint",
                    "mission_waypoint_id": wp["id"],
                    "name": wp.get("name") or f"Waypoint {wp['order']}",
                    "command_id": list(wp.get("command_line", {}).keys())[0] if wp.get("command_line") else None,
                    "command_name": list(wp.get("command_line", {}).values())[0] if wp.get("command_line") else None,
                    "params": list(wp.get("command_line", {}).values())[0] if wp.get("command_line") else None,
                    "frame_id": list(wp.get("frame", {}).keys())[0] if wp.get("frame") else None,
                    "frame_name": list(wp.get("frame", {}).values())[0] if wp.get("frame") else None,
                })
                waypoints_added_count += 1

            # Rule 7: CameraTrigger param5=1 (Add immediately after mission waypoints)
            if route_path:
                try:
                    last_route_wp = route_path[-1]
                    trigger_order = (float(last_route_wp["order"]) if last_route_wp.get("order") is not None else 0) + 0.05
                    route_path.append({
                        "order": trigger_order,
                        "latitude": last_route_wp["latitude"],
                        "longitude": last_route_wp["longitude"],
                        "altitude": last_route_wp["altitude"],
                        "distance_from_start": last_route_wp["distance_from_start"],
                        "type": "waypoint",
                        "mission_waypoint_id": None,
                        "name": "Camera Trigger",
                        "command_id": "203",
                        "command_name": {"203": "MAV_CMD_DO_DIGICAM_CONTROL"},
                        "params": {"203": [0, 0, 0, 0, 1, 0, 0]},
                        "frame_id": "2",
                        "frame_name": "MISSION",
                    })
                except Exception as e:
                    logger.warning("Error adding Camera Trigger for assignment %s: %s", assignment.id, e)

            last_lat = float(last_wp["latitude"]) if last_wp.get("latitude") else None
            last_lon = float(last_wp["longitude"]) if last_wp.get("longitude") else None
            
            # End mission point: LUÔN là waypoint cuối của mission (trước LAND/RTL nếu có).
            # Waiting End (nếu có) sẽ là 1 điểm riêng (Rule 10) và LAND/RTL sẽ dùng waiting coords.
            mission_end_wp = None
            if end_idx > 0:
                mission_end_wp = all_waypoints[end_idx - 1]

            mission_end_lat = (
                float(mission_end_wp["latitude"])
                if (mission_end_wp and mission_end_wp.get("latitude"))
                else last_lat
            )
            mission_end_lon = (
                float(mission_end_wp["longitude"])
                if (mission_end_wp and mission_end_wp.get("longitude"))
                else last_lon
            )

            if mission_end_lat is not None and mission_end_lon is not None:
                has_waiting_coords = waiting_lat is not None and waiting_lon is not None
                # Landing point: nếu có waiting_coords thì LAND/RTL ở waiting coords; nếu không thì ở mission end.
                landing_lat = waiting_lat if has_waiting_coords else mission_end_lat
                landing_lon = waiting_lon if has_waiting_coords else mission_end_lon

                # Xác định end command (LAND/RTL):
                # - Nếu mission đã có LAND/RTL ở cuối range -> giữ nguyên command đó
                # - Nếu chưa có -> dùng end command của mission lớn để quyết định
                landing_wp = last_wp if has_end_command_in_mission else None
                if has_end_command_in_mission:
                    end_command_id = last_command_id
                else:
                    end_command_id = (
                        int(mission_end_command_id)
                        if mission_end_command_id in (20, 21)
                        else (20 if bool(getattr(mission, "return_to_home", True)) else 21)
                    )

                # End altitude: keep original logic for params (usually 0.0), but use separated altitude for root field
                params_end_altitude = waiting_alt if (has_waiting_coords and waiting_alt is not None) else 0.0
                root_end_altitude = waiting_alt if (has_waiting_coords and waiting_alt is not None) else takeoff_altitude

                # Helper: check if mission already has a gripper close (param2=1) near the end
                has_existing_gripper_close = False
                try:
                    for wp in reversed(all_waypoints[-10:]):
                        cmd_id = SurveillanceProfileService._get_command_id_from_command_line(wp.get("command_line"))
                        if cmd_id != 211:
                            continue
                        cmd_line = wp.get("command_line") or {}
                        params_array = None
                        for cmd_data in cmd_line.values():
                            if isinstance(cmd_data, dict):
                                for p in cmd_data.values():
                                    if isinstance(p, list):
                                        params_array = p
                                        break
                            elif isinstance(cmd_data, list):
                                params_array = cmd_data
                            if params_array:
                                break
                        if params_array and len(params_array) >= 2:
                            try:
                                has_existing_gripper_close = float(params_array[1]) == 1.0
                            except (ValueError, TypeError):
                                has_existing_gripper_close = False
                        if has_existing_gripper_close:
                            break
                except Exception:
                    has_existing_gripper_close = False

                # Rule 8: Điểm cuối mission (độ cao separated) - cùng vị trí với điểm cuối mission (Rule 6)
                try:
                    end_sep_order = float(mission_end_wp.get("order") if mission_end_wp else last_wp.get("order")) + 0.1
                    route_path.append({
                        "order": end_sep_order,
                        "latitude": mission_end_lat,
                        "longitude": mission_end_lon,
                        "altitude": str(root_end_altitude),
                        "distance_from_start": round(cumulative_distance, 3),
                        "type": "waypoint",
                        "mission_waypoint_id": None,
                        "name": "End Separated",
                        "command_id": "16",
                        "command_name": {"16": "MAV_CMD_16"},
                        "params": {"16": [0, 0, 0, 0, mission_end_lat, mission_end_lon, params_end_altitude]},
                        "frame_id": frame_id,
                        "frame_name": frame_name,
                    })
                except Exception as e:
                    logger.warning("Error adding End Separated point for assignment %s: %s", assignment.id, e)

                # 2) Gripper Close (param2=1) - luôn trước waiting/end command, trừ khi mission đã có sẵn gripper close
                if not has_existing_gripper_close:
                    try:
                        gripper_command_id = "211"
                        gripper_command_name_dict = {gripper_command_id: "MAV_CMD_DO_GRIPPER"}
                        gripper_params_dict = {gripper_command_id: ["0.0", "1.0", "0.0", "0.0", "0.0", "0.0", "0.0"]}
                        gripper_order = None
                        if mission_end_wp and mission_end_wp.get("order") is not None:
                            try:
                                gripper_order = float(mission_end_wp.get("order")) + 0.2
                            except (ValueError, TypeError):
                                # Rule 9: Gripper Mechanism(param2=1)
                                pass
                        gripper_order = end_sep_order + 0.1
                        route_path.append({
                            "order": gripper_order,
                            "latitude": mission_end_lat,
                            "longitude": mission_end_lon,
                            "altitude": str(root_end_altitude),
                            "distance_from_start": round(cumulative_distance, 3),
                            "type": "waypoint",
                            "mission_waypoint_id": None,
                            "name": "Gripper Close",
                            "command_id": gripper_command_id,
                            "command_name": gripper_command_name_dict,
                            "params": gripper_params_dict,
                            "frame_id": frame_id,
                            "frame_name": frame_name,
                        })
                    except Exception as e:
                        logger.warning("Error adding DO_GRIPPER (close) to route_path for assignment %s: %s", assignment.id, e)

                # Rule 10: Điểm tọa độ chờ (waiting coordinate cuối) - luôn sau Gripper Close và trước LAND/RTL
                if has_waiting_coords:
                    try:
                        waiting_command_name_dict = {"16": "MAV_CMD_16"}
                        waiting_params_dict = {"16": [0, 0, 0, 0, waiting_lat, waiting_lon, waiting_alt]}
                        waiting_end_order = float(mission_end_wp.get("order") if mission_end_wp else last_wp.get("order")) + 0.3
                        route_path.append({
                            "order": waiting_end_order,
                            "latitude": waiting_lat,
                            "longitude": waiting_lon,
                            "altitude": str(waiting_alt),
                            "distance_from_start": round(cumulative_distance, 3),
                            "type": "waypoint",
                            "mission_waypoint_id": None,
                            "name": "Waiting Point",
                            "command_id": "16",
                            "command_name": waiting_command_name_dict,
                            "params": waiting_params_dict,
                            "frame_id": frame_id,
                            "frame_name": frame_name,
                        })
                    except Exception as e:
                        logger.warning("Error adding waiting_coordinates (end) to route_path for assignment %s: %s", assignment.id, e)

                # 4) LAND/RTL command cuối cùng
                try:
                    if landing_wp and isinstance(landing_wp, dict):
                        # Giữ nguyên LAND/RTL từ mission (command_line + frame) để không làm mất params
                        landing_cmd_line = landing_wp.get("command_line") or {}
                        landing_frame = landing_wp.get("frame") or {}
                        landing_command_id = list(landing_cmd_line.keys())[0] if landing_cmd_line else str(end_command_id)
                        landing_command_name = list(landing_cmd_line.values())[0] if landing_cmd_line else {landing_command_id: f"MAV_CMD_{end_command_id}"}
                        landing_params = (
                            list(landing_cmd_line.values())[0]
                            if landing_cmd_line
                            else {landing_command_id: [0, 0, 0, 0, landing_lat, landing_lon, params_end_altitude]}
                        )
                        landing_frame_id = list(landing_frame.keys())[0] if landing_frame else frame_id
                        landing_frame_name = list(landing_frame.values())[0] if landing_frame else frame_name
                        route_path.append({
                            "order": landing_wp.get("order"),
                            "latitude": float(landing_wp.get("latitude")) if landing_wp.get("latitude") else landing_lat,
                            "longitude": float(landing_wp.get("longitude")) if landing_wp.get("longitude") else landing_lon,
                            "altitude": landing_params.get(list(landing_params.keys())[0], [None]*7)[6] if isinstance(landing_params, dict) else str(root_end_altitude),
                            "distance_from_start": round(cumulative_distance, 3),
                            "type": "waypoint",
                            "mission_waypoint_id": landing_wp.get("id"),
                            "name": landing_wp.get("name") or ("Land" if end_command_id == 21 else "RTL"),
                            "command_id": landing_command_id,
                            "command_name": landing_command_name,
                            "params": landing_params,
                            "frame_id": landing_frame_id,
                            "frame_name": landing_frame_name,
                        })
                    else:
                        # Rule 11: RTL/LAND (đảm bảo order cuối cùng)
                        rtl_order = float(mission_end_wp.get("order") if mission_end_wp else last_wp.get("order")) + 0.5
                        rtl_command_name_dict = {str(end_command_id): f"MAV_CMD_{end_command_id}"}
                        if end_command_id == 21:
                            rtl_params_dict = {str(end_command_id): [0, 0, 0, 0, landing_lat, landing_lon, params_end_altitude]}
                            rtl_lat = landing_lat
                            rtl_lon = landing_lon
                        else:
                            rtl_params_dict = {str(end_command_id): [0, 0, 0, 0, 0, 0, 0]}
                            # For RTL, use mission takeoff/home point for coordinates (if available)
                            rtl_lat = landing_lat
                            rtl_lon = landing_lon
                            if mission_takeoff_point and len(mission_takeoff_point) == 2:
                                try:
                                    rtl_lat = float(mission_takeoff_point[0])
                                    rtl_lon = float(mission_takeoff_point[1])
                                except Exception:
                                    rtl_lat = landing_lat
                                    rtl_lon = landing_lon
                        route_path.append({
                            "order": rtl_order,
                            "latitude": rtl_lat,
                            "longitude": rtl_lon,
                            "altitude": str(root_end_altitude),
                            "distance_from_start": round(cumulative_distance, 3),
                            "type": "waypoint",
                            "mission_waypoint_id": None,
                            "name": "Land" if end_command_id == 21 else "RTL",
                            "command_id": str(end_command_id),
                            "command_name": rtl_command_name_dict,
                            "params": rtl_params_dict,
                            "frame_id": frame_id,
                            "frame_name": frame_name,
                        })
                except Exception as e:
                    logger.warning("Error adding end LAND/RTL command for assignment %s: %s", assignment.id, e)

            expected_mission_waypoints = assignment.end_waypoint.order - assignment.start_waypoint.order + 1
            # Count mission waypoints in route_path (those with mission_waypoint_id not None)
            actual_mission_waypoints = sum(1 for wp in route_path if wp.get("mission_waypoint_id") is not None)
            
            # Debug: Log detailed info
            first_wp_order = first_wp.get("order") if first_wp else None
            last_wp_order = last_wp.get("order") if last_wp else None
            
            if actual_mission_waypoints != expected_mission_waypoints:
                logger.warning(
                    "Route path count mismatch for assignment %s: expected %d mission waypoints, got %d. "
                    "Start order: %d, End order: %d, "
                    "all_waypoints_count=%d, waypoints_added_in_loop=%d",
                    assignment.id, expected_mission_waypoints, actual_mission_waypoints,
                    assignment.start_waypoint.order, assignment.end_waypoint.order,
                    len(all_waypoints), waypoints_added_count
                )
            return route_path

        except Exception as exc:
            logger.warning("Error building route_path for assignment %s: %s", assignment.id, exc)
            return None

    @staticmethod
    def build_route_paths_for_assignments(
        assignments: Union[QuerySet, List[SurveillanceProfileDrone]], 
        mission: SurveyMission
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Build route_path for each assignment and return as dict mapping.
        
        Uses waypoints cache to avoid N+1 queries when processing multiple assignments
        from the same mission.
        
        Args:
            assignments: QuerySet or list of SurveillanceProfileDrone instances
            mission: The survey mission
            
        Returns:
            Dict mapping assignment_id -> route_path
            Example: {123: [{order: 1, lat: 37.5, ...}, ...], 124: [...]}
        """
        if not assignments:
            return {}

        # Cache waypoints to avoid repeated queries for same mission
        waypoints_cache: Dict[int, List[Dict]] = {}
        try:
            waypoints_cache[mission.id] = list(
                mission.waypoints.order_by("order").values(
                    "id",
                    "order",
                    "name",
                    "latitude",
                    "longitude",
                    "command_line",
                    "frame",
                )
            )
        except Exception:
            pass
        mission_end_command_id = SurveillanceProfileService._get_overall_mission_end_command_id(mission, waypoints_cache)
        mission_takeoff_point = SurveillanceProfileService._get_overall_mission_takeoff_point(mission, waypoints_cache)
        
        # Build route_path for each assignment
        route_paths_map = {}
        for assignment in assignments:
            route_path = SurveillanceProfileService._build_route_path_for_assignment(
                assignment,
                mission,
                waypoints_cache,
                mission_end_command_id=mission_end_command_id,
                mission_takeoff_point=mission_takeoff_point,
            )
            if route_path:
                route_paths_map[assignment.id] = route_path

        return route_paths_map

    @staticmethod
    def get_active_profiles() -> QuerySet:
        return SurveillanceProfileService.get_queryset_optimized().filter(status__code="in_progress").order_by("-start_time")

    @staticmethod
    def apply_filters(queryset: QuerySet, params) -> QuerySet:
        """Apply high level filters coming from query parameters."""

        if not params:
            return queryset

        def _get_list(key: str) -> List[str]:
            if hasattr(params, "getlist"):
                return [item for item in params.getlist(key) if item not in (None, "")]
            value = params.get(key)
            if value in (None, ""):
                return []
            if isinstance(value, (list, tuple)):
                return [str(item) for item in value if item not in (None, "")]
            return [item.strip() for item in str(value).split(",") if item.strip()]

        def _parse_datetime(value: Optional[str], end_of_day: bool = False) -> Optional[datetime]:
            if not value:
                return None
            dt = parse_datetime(value)
            if dt is None:
                try:
                    dt_date = datetime.strptime(value, "%Y-%m-%d").date()
                    dt = datetime.combine(dt_date, time.max if end_of_day else time.min)
                except ValueError:
                    return None
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt

        status_codes = _get_list("status") or _get_list("status_code")
        if status_codes:
            queryset = queryset.filter(status__code__in=status_codes)

        status_ids = _get_list("status_id")
        if status_ids:
            queryset = queryset.filter(status_id__in=[int(s) for s in status_ids if s.isdigit()])

        mission_ids = _get_list("mission_id")
        if mission_ids:
            queryset = queryset.filter(mission_id__in=[int(m) for m in mission_ids if m.isdigit()])

        operator_ids = _get_list("operator_id")
        if operator_ids:
            queryset = queryset.filter(operator_id__in=[int(o) for o in operator_ids if o.isdigit()])

        repeat_type_ids = _get_list("repeat_type_id")
        if repeat_type_ids:
            queryset = queryset.filter(repeat_type_id__in=[int(r) for r in repeat_type_ids if r.isdigit()])

        repeat_until_type_ids = _get_list("repeat_until_type_id")
        if repeat_until_type_ids:
            queryset = queryset.filter(repeat_until_type_id__in=[int(r) for r in repeat_until_type_ids if r.isdigit()])

        start_from = params.get("start_from") or params.get("start_time_from") or params.get("start_date_from")
        start_to = params.get("start_to") or params.get("start_time_to") or params.get("start_date_to")
        if start_from:
            dt_from = _parse_datetime(start_from)
            if dt_from:
                queryset = queryset.filter(start_time__gte=dt_from)
        if start_to:
            dt_to = _parse_datetime(start_to, end_of_day=True)
            if dt_to:
                queryset = queryset.filter(start_time__lte=dt_to)

        end_from = params.get("end_from") or params.get("end_time_from")
        end_to = params.get("end_to") or params.get("end_time_to")
        if end_from:
            dt_from = _parse_datetime(end_from)
            if dt_from:
                queryset = queryset.filter(
                    Q(actual_end_time__gte=dt_from)
                    | (Q(actual_end_time__isnull=True) & Q(estimated_end_time__gte=dt_from))
                )
        if end_to:
            dt_to = _parse_datetime(end_to, end_of_day=True)
            if dt_to:
                queryset = queryset.filter(
                    Q(actual_end_time__lte=dt_to)
                    | (Q(actual_end_time__isnull=True) & Q(estimated_end_time__lte=dt_to))
                )

        keyword = params.get("keyword") or params.get("search") or params.get("q")
        if keyword:
            keyword = keyword.strip()
            if keyword:
                queryset = queryset.filter(
                    Q(name__icontains=keyword)
                    | Q(code__icontains=keyword)
                    | Q(mission__name__icontains=keyword)
                    | Q(operator__username__icontains=keyword)
                )

        return queryset

    # ------------------------------------------------------------------
    # Repeat utilities
    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_repeat_catalogs() -> None:
        type_defaults = [
            ("none", "None", "Do not repeat"),
            ("daily", "Daily", "Repeat every day"),
            ("weekly", "Weekly", "Repeat every week"),
            ("monthly", "Monthly", "Repeat every month"),
        ]
        for code, name, description in type_defaults:
            SurveillanceProfileRepeatType.objects.get_or_create(
                code=code,
                defaults={"name": name, "description": description},
            )

        until_defaults = [
            ("never", "Never", "Never stop repeating"),
            ("on_date", "On Date", "Stop on a specific date"),
            ("after_occurrences", "After N Occurrences", "Stop after N repeats"),
        ]
        for code, name, description in until_defaults:
            SurveillanceProfileRepeatUntilType.objects.get_or_create(
                code=code,
                defaults={"name": name, "description": description},
            )

    @staticmethod
    def _get_repeat_type_options() -> List[Dict[str, Any]]:
        SurveillanceProfileService._ensure_repeat_catalogs()
        return list(
            SurveillanceProfileRepeatType.objects.all()
            .order_by("id")
            .values("id", "code", "name", "description")
        )

    @staticmethod
    def _get_repeat_until_type_options() -> List[Dict[str, Any]]:
        SurveillanceProfileService._ensure_repeat_catalogs()
        return list(
            SurveillanceProfileRepeatUntilType.objects.all()
            .order_by("id")
            .values("id", "code", "name", "description")
        )

    @staticmethod
    def _get_available_devices(
        limit: Optional[int] = None,
        available: bool = False,
        raise_on_empty: bool = False,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        unit_ids = SurveillanceProfileService.fetch_available_device_from_gcs()
        if diagnostics is not None:
            diagnostics["gcs_unit_ids_count"] = len(unit_ids or [])
        if not unit_ids:
            if raise_on_empty:
                raise ValidationError(get_message(MESSAGE_ENUM.SURVEILLANCE_AVAILABLE_DEVICES_GCS_EMPTY))
            return []
        queryset = Device.objects.filter(
            active=True,
            main_type__name__icontains="drone",
            unit_id__in=unit_ids,
        ).select_related(
            "terminal",
            "flight_performance",
            "propulsion_system",
        ).prefetch_related(
            "flight_performance__measurements",
            "propulsion_system__measurements",
        ).order_by("id")
        if available:
            queryset = queryset.filter(status__code="available")
        devices: List[Dict[str, Any]] = []
        for device in queryset:
            terminal = getattr(device, "terminal", None)
            terminal_lat = (
                SurveillanceProfileService._safe_number(getattr(terminal, "latitude", None), float)
                if terminal
                else None
            )
            terminal_lon = (
                SurveillanceProfileService._safe_number(getattr(terminal, "longitude", None), float)
                if terminal
                else None
            )
            
            # Lấy cruise_speed từ FlightPerformance measurement với chuyển đổi đơn vị
            cruise_speed_ms = None
            flight_performance = getattr(device, "flight_performance", None)
            if flight_performance:
                cruise_speed_measurement = flight_performance.get_measurement('cruise_speed')
                if cruise_speed_measurement:
                    # Lấy giá trị số và đơn vị hiện tại
                    cruise_speed_value = cruise_speed_measurement.get_numeric_value()
                    if cruise_speed_value is not None:
                        measurement_data = cruise_speed_measurement.data or {}
                        current_unit = measurement_data.get('unit') or measurement_data.get('original_unit')
                        # Convert về m/s nếu cần
                        if current_unit and current_unit != 'm/s':
                            try:
                                cruise_speed_ms = convert_unit(cruise_speed_value, current_unit, 'm/s', context='speed')
                            except Exception:
                                cruise_speed_ms = cruise_speed_value
                        else:
                            cruise_speed_ms = cruise_speed_value
            
            # Nếu không có, lấy từ AdminConfig (get_waypoint_speed)
            if cruise_speed_ms is None or cruise_speed_ms <= 0:
                cruise_speed_ms = get_waypoint_speed(default=7.0)
            
            # Lấy flight_time từ PropulsionSystem measurement với chuyển đổi đơn vị
            flight_time_min = None
            propulsion_system = getattr(device, "propulsion_system", None)
            if propulsion_system:
                flight_time_measurement = propulsion_system.get_measurement('flight_time')
                if flight_time_measurement:
                    # Lấy giá trị số và đơn vị hiện tại
                    flight_time_value = flight_time_measurement.get_numeric_value()
                    if flight_time_value is not None:
                        measurement_data = flight_time_measurement.data or {}
                        current_unit = measurement_data.get('unit') or measurement_data.get('original_unit')
                        # Convert về min nếu cần
                        if current_unit and current_unit != 'min':
                            try:
                                flight_time_min = convert_unit(flight_time_value, current_unit, 'min', context='time')
                            except Exception:
                                flight_time_min = flight_time_value
                        else:
                            flight_time_min = flight_time_value
            if flight_time_min is not None and flight_time_min > 0:
                max_distance_km = (cruise_speed_ms * flight_time_min * 60) / 1000.0
            else:
                max_distance_km = None
            devices.append(
                {
                    "id": device.id,
                    "name": device.name,
                    "serial_number": device.serial_number,
                    "color": device.color,
                    "terminal_id": getattr(terminal, "id", None),
                    "terminal_name": getattr(terminal, "name", None),
                    "terminal_latitude": terminal_lat,
                    "terminal_longitude": terminal_lon,
                    "max_distance_km": max_distance_km,
                }
            )

        if diagnostics is not None:
            diagnostics["db_devices_count"] = len(devices)
        if not devices and raise_on_empty:
            raise ValidationError(
                get_message(MESSAGE_ENUM.SURVEILLANCE_AVAILABLE_DEVICES_NO_MATCHING_DB_DRONES).format(
                    unit_ids_count=len(unit_ids or [])
                )
            )
        return devices

    @staticmethod
    def _build_device_context(device_ids: Iterable[int]) -> Dict[int, Device]:
        ids = [idx for idx in set(device_ids) if idx]
        if not ids:
            return {}

        queryset = (
            Device.objects.filter(id__in=ids)
            .select_related(
                "terminal",
                "propulsion_system",
                "flight_performance",
                "manufacturer_information",
                "telemetry",
            )
            .prefetch_related(
                "propulsion_system__measurements",
                "flight_performance__measurements",
            )
        )

        return {device.id: device for device in queryset}

    def _normalise_start_time(start_time: Optional[datetime]) -> datetime:
        if not start_time:
            start_time = timezone.now()
        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time, timezone.get_current_timezone())
        else:
            # Chuyển đổi datetime có timezone sang timezone hệ thống
            start_time = timezone.localtime(start_time, timezone.get_current_timezone())
        return start_time

    @staticmethod
    def _convert_utc_to_system_timezone_date(utc_datetime):
        """
        Chuyển đổi UTC datetime string hoặc datetime object sang date trong timezone của hệ thống.
        
        Args:
            utc_datetime: datetime object hoặc string (UTC) hoặc date object
            
        Returns:
            date object trong timezone hệ thống, hoặc None nếu không parse được
        """
        if utc_datetime is None:
            return None
        
        # Nếu đã là date object, trả về luôn
        if isinstance(utc_datetime, date) and not isinstance(utc_datetime, datetime):
            return utc_datetime
        
        # Nếu là string, parse thành datetime
        if isinstance(utc_datetime, str):
            try:
                # Thử parse ISO format với timezone
                if 'T' in utc_datetime or '+' in utc_datetime or utc_datetime.endswith('Z'):
                    utc_datetime = datetime.fromisoformat(utc_datetime.replace('Z', '+00:00'))
                else:
                    # Nếu chỉ là date string, parse thành date
                    return datetime.strptime(utc_datetime, '%Y-%m-%d').date()
            except (ValueError, AttributeError):
                # Fallback: thử parse các format khác
                try:
                    utc_datetime = datetime.strptime(utc_datetime, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return None
        
        # Nếu là datetime nhưng chưa có timezone, giả định là UTC
        if isinstance(utc_datetime, datetime):
            if timezone.is_naive(utc_datetime):
                # Nếu là naive datetime, giả định là UTC
                utc_datetime = timezone.make_aware(utc_datetime, dt_timezone.utc)
            else:
                # Đảm bảo datetime là UTC
                if utc_datetime.tzinfo != dt_timezone.utc:
                    utc_datetime = utc_datetime.astimezone(dt_timezone.utc)
            
            # Chuyển đổi sang timezone của hệ thống
            system_tz = timezone.get_current_timezone()
            system_datetime = utc_datetime.astimezone(system_tz)
            
            # Trả về date trong timezone hệ thống
            return system_datetime.date()
        
        return None

    @staticmethod
    def _build_drone_flight_segments(
        mission: SurveyMission,
        _available_devices: List[Dict[str, Any]],
        device_instances: Optional[Dict[int, Device]] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool]:
        if diagnostics is not None:
            diagnostics.setdefault("failure_stage", None)
            diagnostics["available_devices_count"] = len(_available_devices or [])
            diagnostics["mission_from_route"] = bool(getattr(mission, "from_route", False))
            diagnostics["mission_has_drone_segments"] = bool(getattr(mission, "drone_segments", None))

        maximum_drones = mission.maximum_drones or 1
        if maximum_drones <= 0:
            maximum_drones = 1

        # Nếu mission được import từ route và có drone_segments, giữ nguyên đường bay theo route
        if mission.from_route or mission.drone_segments:
            segments, candidate_points, ok = SurveillanceProfileService._build_segments_from_imported_routes(
                mission,
                _available_devices,
                device_instances,
                diagnostics=diagnostics,
            )
            if diagnostics is not None and not ok:
                diagnostics["failure_stage"] = diagnostics.get("failure_stage") or "imported_route_no_segments"
            return segments, candidate_points, ok

        # Logic chia mission bình thường (cho cả trường hợp không có from_route hoặc có from_route nhưng không có drone_segments)
        mission_points, candidate_points, fallback_cruise_speed_ms = SurveillanceProfileService._collect_mission_points(mission)

        if len(mission_points) < 2:
            return [], candidate_points, True

        cumulative_distances = [point["distance_from_start"] for point in mission_points]

        instance_map = device_instances if device_instances is not None else {}
        candidate_diagnostics: Optional[Dict[str, Any]] = {} if diagnostics is not None else None
        candidates = SurveillanceProfileService._prepare_drone_candidates(
            _available_devices,
            instance_map,
            fallback_cruise_speed_ms,
            diagnostics=candidate_diagnostics,
        )
        if not candidates:
            if diagnostics is not None:
                diagnostics["failure_stage"] = "prepare_drone_candidates_empty"
                if candidate_diagnostics:
                    diagnostics.update(candidate_diagnostics)
            return [], candidate_points, False

        max_drones_usable = min(maximum_drones, len(candidates))
        if max_drones_usable <= 0:
            if diagnostics is not None:
                diagnostics["failure_stage"] = "no_usable_drones"
            return [], candidate_points, False
        
        for drones_to_use in range(max_drones_usable, 0, -1):
            segment_templates = SurveillanceProfileService._split_mission_points(
                mission_points,
                cumulative_distances,
                drones_to_use,
            )
            for candidate_combo in combinations(candidates, drones_to_use):
                attempt_diagnostics: Optional[Dict[str, Any]] = {} if diagnostics is not None else None
                assigned_segments = SurveillanceProfileService._assign_segments_for_candidates(
                    segment_templates,
                    candidate_combo,
                    fallback_cruise_speed_ms,
                    diagnostics=attempt_diagnostics,
                )

                if assigned_segments:
                    return assigned_segments, candidate_points, True
                if diagnostics is not None and attempt_diagnostics:
                    # Preserve the first meaningful failure explanation.
                    if not diagnostics.get("segment_failure") and attempt_diagnostics.get("segment_failure"):
                        diagnostics["segment_failure"] = attempt_diagnostics.get("segment_failure")
                    if not diagnostics.get("failure_stage"):
                        diagnostics["failure_stage"] = "assign_segments_failed"

        if diagnostics is not None and not diagnostics.get("failure_stage"):
            diagnostics["failure_stage"] = "assign_segments_failed"
        return [], candidate_points, False
    
    @staticmethod
    def _build_segments_from_imported_routes(
        mission: SurveyMission,
        _available_devices: List[Dict[str, Any]],
        device_instances: Optional[Dict[int, Device]] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool]:
        """
        Tạo segments từ imported routes - mỗi route được gán cho một drone
        Giữ nguyên đường bay của từng route, không tự động chia
        Giờ dùng drone_segments thay vì MissionRoute
        """
        # Nếu có drone_segments, dùng logic mới
        if mission.drone_segments:
            return SurveillanceProfileService._build_segments_from_drone_segments(
                mission,
                _available_devices,
                device_instances,
                diagnostics=diagnostics,
            )
        mission_points, candidate_points, fallback_cruise_speed_ms = SurveillanceProfileService._collect_mission_points(mission)
        if len(mission_points) < 2:
            return [], candidate_points, True
        if diagnostics is not None:
            diagnostics["failure_stage"] = diagnostics.get("failure_stage") or "imported_route_no_segments"
        return [], candidate_points, False
    
    @staticmethod
    def _extract_route_path_from_qgc_mission(
        qgc_mission: Dict[str, Any],
        start_order: Optional[int] = None,
        end_order: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract route_path từ qgc_mission trong drone_segments
        Trả về danh sách các điểm với thông tin đầy đủ từ QGC mission items
        """
        route_path = []
        if not qgc_mission or not isinstance(qgc_mission, dict):
            return route_path
        
        mission_data = qgc_mission.get('mission', {})
        if not mission_data:
            return route_path
        
        items = mission_data.get('items', [])
        if not items:
            return route_path
        
        cumulative_distance = 0.0
        # Không sử dụng start_order/end_order để filter items vì doJumpId có thể không khớp với order
        # Thay vào đó, extract tất cả items và sẽ map với mission waypoints sau
        order_counter = 1
        
        for idx, item in enumerate(items):
            item_type = item.get('type', 'SimpleItem')
            command = item.get('command', 16)
            params = item.get('params', [])
            frame = item.get('frame', 3)
            
            # Extract coordinates từ params
            lat = None
            lon = None
            alt = None
            
            if isinstance(params, list) and len(params) >= 7:
                lat = params[4] if params[4] is not None and params[4] != 0.0 else None
                lon = params[5] if params[5] is not None and params[5] != 0.0 else None
                alt = params[6] if params[6] is not None and params[6] != 0.0 else None
            
            # Xử lý ComplexItem (survey polygon)
            if item_type == 'ComplexItem' and item.get('complexItemType') == 'survey':
                transect_item = item.get('TransectStyleComplexItem', {})
                transect_items = transect_item.get('Items', [])
                
                # Lấy VisualTransectPoints nếu có
                visual_points = transect_item.get('VisualTransectPoints', [])
                if visual_points:
                    for point_idx, point in enumerate(visual_points):
                        if isinstance(point, list) and len(point) >= 2:
                            point_lat = point[0]
                            point_lon = point[1]
                            
                            # Tính distance từ điểm trước
                            if route_path:
                                try:
                                    prev_point = route_path[-1]
                                    distance_km = geodesic(
                                        (prev_point.get('latitude'), prev_point.get('longitude')),
                                        (point_lat, point_lon),
                                    ).kilometers
                                    cumulative_distance += distance_km
                                except (ValueError, TypeError):
                                    pass
                            
                            route_path.append({
                                'order': order_counter,
                                'latitude': point_lat,
                                'longitude': point_lon,
                                'altitude': alt,
                                'distance_from_start': round(cumulative_distance, 3),
                                'type': 'waypoint',
                                'mission_waypoint_id': None,
                                'name': f'Waypoint {order_counter}',
                                'command_id': str(command),
                                'command_name': {str(command): f'MAV_CMD_{command}'},
                                'params': {str(command): params},
                                'frame_id': str(frame),
                                'frame_name': 'GLOBAL_RELATIVE_ALT' if frame == 3 else 'GLOBAL',
                            })
                            order_counter += 1
                elif transect_items:
                    # Fallback: sử dụng transect items
                    for transect_item_data in transect_items:
                        transect_params = transect_item_data.get('params', [])
                        if isinstance(transect_params, list) and len(transect_params) >= 7:
                            point_lat = transect_params[4]
                            point_lon = transect_params[5]
                            point_alt = transect_params[6]
                            
                            if point_lat is not None and point_lon is not None:
                                # Tính distance từ điểm trước
                                if route_path:
                                    try:
                                        prev_point = route_path[-1]
                                        distance_km = geodesic(
                                            (prev_point.get('latitude'), prev_point.get('longitude')),
                                            (point_lat, point_lon),
                                        ).kilometers
                                        cumulative_distance += distance_km
                                    except (ValueError, TypeError):
                                        pass
                                
                                route_path.append({
                                    'order': order_counter,
                                    'latitude': point_lat,
                                    'longitude': point_lon,
                                    'altitude': point_alt,
                                    'distance_from_start': round(cumulative_distance, 3),
                                    'type': 'waypoint',
                                    'mission_waypoint_id': None,
                                    'name': f'Waypoint {order_counter}',
                                    'command_id': str(transect_item_data.get('command', 16)),
                                    'command_name': {str(transect_item_data.get('command', 16)): f'MAV_CMD_{transect_item_data.get("command", 16)}'},
                                    'params': {str(transect_item_data.get('command', 16)): transect_params},
                                    'frame_id': str(transect_item_data.get('frame', 3)),
                                    'frame_name': 'GLOBAL_RELATIVE_ALT' if transect_item_data.get('frame', 3) == 3 else 'GLOBAL',
                                })
                                order_counter += 1
            
            # Xử lý SimpleItem
            elif item_type == 'SimpleItem' and lat is not None and lon is not None:
                # Tính distance từ điểm trước
                if route_path:
                    try:
                        prev_point = route_path[-1]
                        distance_km = geodesic(
                            (prev_point.get('latitude'), prev_point.get('longitude')),
                            (lat, lon),
                        ).kilometers
                        cumulative_distance += distance_km
                    except (ValueError, TypeError):
                        pass
                
                route_path.append({
                    'order': order_counter,
                    'latitude': lat,
                    'longitude': lon,
                    'altitude': alt,
                    'distance_from_start': round(cumulative_distance, 3),
                    'type': 'waypoint',
                    'mission_waypoint_id': None,
                    'name': f'Waypoint {order_counter}',
                    'command_id': str(command),
                    'command_name': {str(command): f'MAV_CMD_{command}'},
                    'params': {str(command): params},
                    'frame_id': str(frame),
                    'frame_name': 'GLOBAL_RELATIVE_ALT' if frame == 3 else 'GLOBAL',
                })
                order_counter += 1
        
        return route_path

    @staticmethod
    def _build_segments_from_drone_segments(
        mission: SurveyMission,
        _available_devices: List[Dict[str, Any]],
        device_instances: Optional[Dict[int, Device]] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool]:
        """
        Tạo segments từ drone_segments (format mới với drone_missions)
        Mỗi phần tử trong drone_segments là một đường bay cho một drone
        Sử dụng qgc_mission để build route_path thay vì tính toán từ waypoints
        """
        if not mission.drone_segments or not isinstance(mission.drone_segments, list):
            mission_points, candidate_points, fallback_cruise_speed_ms = SurveillanceProfileService._collect_mission_points(mission)
            if diagnostics is not None:
                diagnostics["failure_stage"] = diagnostics.get("failure_stage") or "imported_route_no_segments"
            return [], candidate_points, False
        
        # Lấy waypoints của mission để lấy ID và order mapping
        waypoints = list(
            mission.waypoints.order_by('order')
            .values('id', 'order', 'latitude', 'longitude')
        )
        
        if len(waypoints) < 2:
            mission_points, candidate_points, fallback_cruise_speed_ms = SurveillanceProfileService._collect_mission_points(mission)
            return [], candidate_points, True
        
        instance_map = device_instances if device_instances is not None else {}
        mission_points, candidate_points, fallback_cruise_speed_ms = SurveillanceProfileService._collect_mission_points(mission)
        
        candidate_diagnostics: Optional[Dict[str, Any]] = {} if diagnostics is not None else None
        candidates = SurveillanceProfileService._prepare_drone_candidates(
            _available_devices,
            instance_map,
            fallback_cruise_speed_ms,
            diagnostics=candidate_diagnostics,
        )
        
        if not candidates:
            if diagnostics is not None:
                diagnostics["failure_stage"] = diagnostics.get("failure_stage") or "prepare_drone_candidates_empty"
                if candidate_diagnostics:
                    diagnostics.update(candidate_diagnostics)
            return [], candidate_points, False
        
        # Sort drone_segments theo area_index từ thấp đến cao để đảm bảo thứ tự đúng
        sorted_drone_segments = sorted(
            mission.drone_segments,
            key=lambda x: x.get('area_index', 0) if x.get('area_index') is not None else 0
        )
        
        # QUAN TRỌNG: Với from_route hoặc drone_segments, phải tạo segments cho TẤT CẢ drone_segments
        # Không giới hạn bởi số lượng candidates - đảm bảo số lượng assignments = số lượng segments
        segments = []
        for idx, drone_segment in enumerate(sorted_drone_segments):
            start_order = drone_segment.get('start_waypoint_order')
            end_order = drone_segment.get('end_waypoint_order')
            
            if start_order is None or end_order is None:
                continue
            
            # Filter waypoints trong range này để lấy ID
            route_waypoints = [
                wp for wp in waypoints
                if start_order <= wp.get('order', 0) <= end_order
            ]
            
            if len(route_waypoints) < 2:
                continue
            
            # Lấy candidate tương ứng, nếu không đủ thì dùng candidate đầu tiên hoặc None
            # QUAN TRỌNG: Vẫn tạo segment ngay cả khi không có candidate phù hợp
            candidate = candidates[idx] if idx < len(candidates) else (candidates[0] if candidates else None)
            start_wp = route_waypoints[0]
            end_wp = route_waypoints[-1]
            
            # Kiểm tra xem có route_id không
            route_id = drone_segment.get('route_id')
            qgc_mission = drone_segment.get('qgc_mission')
            
            # Tính distance từ estimated_duration hoặc từ waypoints
            route_distance = drone_segment.get('distance_km', 0)
            if route_distance == 0:
                route_distance = drone_segment.get('estimated_duration', 0) * 15 / 60  # Giả sử tốc độ 15 m/s
            if route_distance == 0:
                # Tính từ waypoints
                for i in range(len(route_waypoints) - 1):
                    wp1 = route_waypoints[i]
                    wp2 = route_waypoints[i + 1]
                    try:
                        lat1 = float(wp1.get('latitude', 0))
                        lon1 = float(wp1.get('longitude', 0))
                        lat2 = float(wp2.get('latitude', 0))
                        lon2 = float(wp2.get('longitude', 0))
                        route_distance += geodesic((lat1, lon1), (lat2, lon2)).kilometers
                    except (ValueError, TypeError):
                        pass
            
            # Luôn sử dụng mission waypoints từ start_waypoint_order đến end_waypoint_order
            # Map với qgc_mission items để lấy command/params/frame nếu có
            converted_points = []
            cumulative_distance = 0.0
            
            # Tạo map từ qgc_mission items nếu có (để lấy command/params/frame)
            qgc_items_map = {}
            if qgc_mission and not route_id:
                mission_data = qgc_mission.get('mission', {})
                items = mission_data.get('items', [])
                # Map items theo doJumpId để có thể lookup sau
                for item in items:
                    do_jump_id = item.get('doJumpId')
                    if do_jump_id is not None:
                        qgc_items_map[do_jump_id] = item
            
            # Build route_path từ mission waypoints
            for i, wp in enumerate(route_waypoints):
                wp_order = wp.get('order')
                
                # Tính distance từ điểm trước
                if i > 0:
                    try:
                        prev_wp = route_waypoints[i - 1]
                        distance_km = geodesic(
                            (float(prev_wp.get('latitude', 0)), float(prev_wp.get('longitude', 0))),
                            (float(wp.get('latitude', 0)), float(wp.get('longitude', 0))),
                        ).kilometers
                        cumulative_distance += distance_km
                    except (ValueError, TypeError):
                        pass
                
                # Tìm qgc_item tương ứng (nếu có) để lấy command/params/frame
                # doJumpId trong qgc_mission có thể bắt đầu từ 0 hoặc 1, cần map với order
                qgc_item = None
                if qgc_items_map:
                    # Thử map với doJumpId = wp_order hoặc wp_order - start_order + offset
                    # Vì doJumpId có thể bắt đầu từ 0 hoặc 1
                    for do_jump_id, item in qgc_items_map.items():
                        # Kiểm tra xem item này có tọa độ khớp với waypoint không
                        params = item.get('params', [])
                        if isinstance(params, list) and len(params) >= 7:
                            item_lat = params[4] if params[4] is not None and params[4] != 0.0 else None
                            item_lon = params[5] if params[5] is not None and params[5] != 0.0 else None
                            if item_lat and item_lon:
                                wp_lat = float(wp.get('latitude', 0))
                                wp_lon = float(wp.get('longitude', 0))
                                # So sánh với độ chính xác hợp lý (khoảng 0.0001 độ ≈ 11m)
                                if abs(item_lat - wp_lat) < 0.0001 and abs(item_lon - wp_lon) < 0.0001:
                                    qgc_item = item
                                    break
                
                # Extract command/params/frame từ qgc_item nếu có
                command_id = None
                params = None
                frame_id = None
                frame_name = None
                command_name = None
                altitude = None
                
                if qgc_item:
                    command_id = str(qgc_item.get('command', 16))
                    params = {command_id: qgc_item.get('params', [])}
                    frame = qgc_item.get('frame', 3)
                    frame_id = str(frame)
                    frame_name = 'GLOBAL_RELATIVE_ALT' if frame == 3 else 'GLOBAL'
                    command_name = {command_id: f'MAV_CMD_{qgc_item.get("command", 16)}'}
                    # Lấy altitude từ params nếu có
                    item_params = qgc_item.get('params', [])
                    if isinstance(item_params, list) and len(item_params) >= 7:
                        altitude = item_params[6] if item_params[6] is not None and item_params[6] != 0.0 else None
                
                converted_point = {
                    'order': wp_order,
                    'lat': float(wp.get('latitude', 0)),
                    'lon': float(wp.get('longitude', 0)),
                    'alt': altitude,
                    'distance_from_start': round(cumulative_distance, 3),
                    'type': 'waypoint',
                    'id': wp.get('id'),
                    'name': f"Waypoint {wp_order}",
                    'command_id': command_id,
                    'params': params,
                    'frame_id': frame_id,
                    'frame_name': frame_name,
                    'command_name': command_name,
                }
                converted_points.append(converted_point)
            
            # Fallback: nếu không có converted_points (không nên xảy ra)
            if not converted_points:
                converted_points = [
                    {
                        'order': wp.get('order'),
                        'lat': float(wp.get('latitude', 0)),
                        'lon': float(wp.get('longitude', 0)),
                        'alt': None,
                        'distance_from_start': 0,
                        'type': 'waypoint',
                        'id': wp.get('id'),
                        'name': f"Waypoint {wp.get('order')}",
                    }
                    for wp in route_waypoints
                ]
            # Extract device info from candidate
            # Xử lý trường hợp candidate = None (khi không đủ devices)
            if candidate is None:
                device_info = {}
            else:
                device_info = candidate.get('device', {}) if isinstance(candidate, dict) else {}
            segment = {
                'device_id': device_info.get('id') if isinstance(device_info, dict) else None,
                'device_name': device_info.get('name', '') if isinstance(device_info, dict) else '',
                'start_waypoint_id': start_wp['id'],
                'end_waypoint_id': end_wp['id'],
                'points': converted_points,
                'start_point': {
                    'id': start_wp['id'],
                    'order': start_order,
                    'lat': float(start_wp.get('latitude', 0)),
                    'lon': float(start_wp.get('longitude', 0)),
                    'name': f"Waypoint {start_order}",
                },
                'end_point': {
                    'id': end_wp['id'],
                    'order': end_order,
                    'lat': float(end_wp.get('latitude', 0)),
                    'lon': float(end_wp.get('longitude', 0)),
                    'name': f"Waypoint {end_order}",
                },
                'assigned_device': device_info.copy() if isinstance(device_info, dict) else {},
                'distance_km': route_distance,
                'path_distance_km': route_distance,
                'takeoff_distance_km': 0,
                'estimated_time_minutes': drone_segment.get('estimated_duration', 0),
                'flight_estimation': None,
            }
            segments.append(segment)
        
        if segments:
            return segments, candidate_points, True
        if diagnostics is not None:
            diagnostics["failure_stage"] = diagnostics.get("failure_stage") or "imported_route_no_segments"
        return [], candidate_points, False

    @staticmethod
    def _validate_duplicate_assignments(assignments: List[Dict[str, Any]]) -> None:
        if not assignments:
            return

        duplicates: Dict[Any, List[int]] = {}

        for idx, assignment in enumerate(assignments, start=1):
            start_wp = assignment.get("start_waypoint_id")
            end_wp = assignment.get("end_waypoint_id")
            if start_wp is None and end_wp is None:
                metadata = assignment.get("metadata") or {}
                start_point = metadata.get("start_point") or {}
                end_point = metadata.get("end_point") or {}
                key = (
                    SurveillanceProfileService._safe_number(start_point.get("lat"), float),
                    SurveillanceProfileService._safe_number(start_point.get("lon"), float),
                    SurveillanceProfileService._safe_number(end_point.get("lat"), float),
                    SurveillanceProfileService._safe_number(end_point.get("lon"), float),
                )
            else:
                key = (start_wp, end_wp)
            duplicates.setdefault(key, []).append(idx)

        if any(len(indexes) > 1 for indexes in duplicates.values()):
            raise ValidationError(
                "Có drone có cùng điểm start/end. Vui lòng điều chỉnh thời gian hoặc độ cao cho từng drone trước khi lưu profile."
            )

    @staticmethod
    def _adjust_duplicate_assignment_times(
        raw_assignments: List[Dict[str, Any]],
        display_assignments: List[Dict[str, Any]],
    ) -> None:
        if not raw_assignments:
            return

        duplicate_groups: Dict[Any, List[int]] = {}

        for index, assignment in enumerate(raw_assignments):
            start_wp = assignment.get("start_waypoint_id")
            end_wp = assignment.get("end_waypoint_id")
            if start_wp is None and end_wp is None:
                metadata = assignment.get("metadata") or {}
                start_point = metadata.get("start_point") or {}
                end_point = metadata.get("end_point") or {}
                key = (
                    SurveillanceProfileService._safe_number(start_point.get("lat"), float),
                    SurveillanceProfileService._safe_number(start_point.get("lon"), float),
                    SurveillanceProfileService._safe_number(end_point.get("lat"), float),
                    SurveillanceProfileService._safe_number(end_point.get("lon"), float),
                )
            else:
                key = (start_wp, end_wp)
            duplicate_groups.setdefault(key, []).append(index)

        for indexes in duplicate_groups.values():
            if len(indexes) <= 1:
                continue
            base_time = raw_assignments[indexes[0]].get("scheduled_start_time")
            if not base_time:
                continue
            for offset_position, assignment_index in enumerate(indexes):
                if offset_position == 0:
                    continue
                adjusted_time = base_time + timezone.timedelta(
                    minutes=AUTO_ADJUST_SEGMENT_OFFSET_MINUTES * offset_position
                )
                raw_assignments[assignment_index]["scheduled_start_time"] = adjusted_time
                if assignment_index < len(display_assignments):
                    display_assignments[assignment_index]["scheduled_start_time"] = adjusted_time

    @staticmethod
    def _find_waypoint_index_by_distance(
        cumulative: List[float], target: float, minimum_index: int
    ) -> int:
        if not cumulative:
            return 0
        target = max(target, 0.0)
        n = len(cumulative)
        index = max(minimum_index, 0)
        epsilon = 1e-9
        while index < n and cumulative[index] + epsilon < target:
            index += 1
        if index >= n:
            return n - 1
        if index == minimum_index:
            return index
        prev_index = max(index - 1, minimum_index)
        prev_distance = cumulative[prev_index]
        current_distance = cumulative[index]
        if abs(target - prev_distance) <= abs(current_distance - target):
            return prev_index
        return index

    @staticmethod
    def _calculate_path_distance(points: List[Dict[str, Any]]) -> float:
        if not points or len(points) < 2:
            return 0.0

        distance_km = 0.0
        for idx in range(1, len(points)):
            prev_point = points[idx - 1]
            current_point = points[idx]

            prev_lat = SurveillanceProfileService._safe_number(prev_point.get("lat"), float)
            prev_lon = SurveillanceProfileService._safe_number(prev_point.get("lon"), float)
            curr_lat = SurveillanceProfileService._safe_number(current_point.get("lat"), float)
            curr_lon = SurveillanceProfileService._safe_number(current_point.get("lon"), float)

            if None in (prev_lat, prev_lon, curr_lat, curr_lon):
                continue

            try:
                distance_km += geodesic((prev_lat, prev_lon), (curr_lat, curr_lon)).kilometers
            except (ValueError, TypeError):
                continue

        return distance_km

    @staticmethod
    def _safe_number(value: Any, cast_type):
        if value is None:
            return None
        try:
            return cast_type(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_navigation_polyline_from_qgc_mission(qgc_mission_data: Dict[str, Any]) -> List[Tuple[float, float]]:
        """
        Extract a navigation polyline (lat, lon) from QGC mission data.
        Includes navigation commands (waypoint/takeoff/land) which carry coordinates.
        Excludes action commands like DO_DIGICAM_CONTROL (203).
        """
        if not qgc_mission_data or not isinstance(qgc_mission_data, dict):
            return []
        items = qgc_mission_data.get("mission", {}).get("items", [])
        if not isinstance(items, list):
            return []

        navigation_commands = {16, 21, 22}  # WAYPOINT, LAND, TAKEOFF
        coords: List[Tuple[float, float]] = []

        def _cmd_id(cmd_val: Any) -> Optional[int]:
            if isinstance(cmd_val, dict):
                cmd_val = cmd_val.get("id")
            try:
                return int(cmd_val)
            except (TypeError, ValueError):
                return None

        def _append_from_simple_item(item: Dict[str, Any]) -> None:
            cmd = _cmd_id(item.get("command"))
            if cmd not in navigation_commands:
                return
            params = item.get("params") or []
            if not (isinstance(params, list) and len(params) >= 6):
                return
            lat = SurveillanceProfileService._safe_number(params[4], float)
            lon = SurveillanceProfileService._safe_number(params[5], float)
            if lat is None or lon is None:
                return
            coords.append((lat, lon))

        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "ComplexItem" and item.get("complexItemType") == "survey":
                transect = item.get("TransectStyleComplexItem") or {}
                survey_items = transect.get("Items") or []
                if isinstance(survey_items, list):
                    for s_item in survey_items:
                        if isinstance(s_item, dict):
                            _append_from_simple_item(s_item)
            elif item.get("type") == "SimpleItem":
                _append_from_simple_item(item)

        return coords

    @staticmethod
    def _sum_polyline_km(points: List[Tuple[float, float]]) -> float:
        if not points or len(points) < 2:
            return 0.0
        total = 0.0
        for i in range(1, len(points)):
            try:
                total += geodesic(points[i - 1], points[i]).kilometers
            except (ValueError, TypeError):
                continue
        return total

    @staticmethod
    def _find_index_by_latlon(points: List[Tuple[float, float]], lat: float, lon: float, tol: float = 1e-5) -> Optional[int]:
        if not points:
            return None
        best_idx = None
        best_err = None
        for idx, (p_lat, p_lon) in enumerate(points):
            err = abs(p_lat - lat) + abs(p_lon - lon)
            if err <= tol:
                if best_err is None or err < best_err:
                    best_err = err
                    best_idx = idx
        return best_idx

    @staticmethod
    def _compute_assignment_distance_km_from_mission(
        mission: SurveyMission,
        start_wp: Optional[MissionWaypoint],
        end_wp: Optional[MissionWaypoint],
    ) -> Optional[float]:
        """
        Compute per-drone distance along the mission flight path (polyline), not straight line.
        Priority:
        1) Use mission.qgc_mission_data navigation polyline (best match to actual flight path)
        2) Fallback to MissionWaypoint polyline between start/end orders
        """
        if not mission or not start_wp or not end_wp:
            return None
        start_lat = SurveillanceProfileService._safe_number(getattr(start_wp, "latitude", None), float)
        start_lon = SurveillanceProfileService._safe_number(getattr(start_wp, "longitude", None), float)
        end_lat = SurveillanceProfileService._safe_number(getattr(end_wp, "latitude", None), float)
        end_lon = SurveillanceProfileService._safe_number(getattr(end_wp, "longitude", None), float)
        if None in (start_lat, start_lon, end_lat, end_lon):
            return None

        # 1) From QGC mission data (nav polyline)
        qgc_poly = SurveillanceProfileService._extract_navigation_polyline_from_qgc_mission(
            getattr(mission, "qgc_mission_data", None) or {}
        )
        if qgc_poly:
            s_idx = SurveillanceProfileService._find_index_by_latlon(qgc_poly, start_lat, start_lon)
            e_idx = SurveillanceProfileService._find_index_by_latlon(qgc_poly, end_lat, end_lon)
            if s_idx is not None and e_idx is not None:
                if s_idx > e_idx:
                    s_idx, e_idx = e_idx, s_idx
                segment = qgc_poly[s_idx : e_idx + 1]
                km = SurveillanceProfileService._sum_polyline_km(segment)
                if km > 0:
                    return km

        # 2) Fallback: MissionWaypoint polyline between orders
        try:
            start_order = int(getattr(start_wp, "order", 0))
            end_order = int(getattr(end_wp, "order", 0))
        except (TypeError, ValueError):
            return None
        if start_order > end_order:
            start_order, end_order = end_order, start_order
        qs = MissionWaypoint.objects.filter(mission=mission, order__gte=start_order, order__lte=end_order).order_by("order", "id")
        pts: List[Tuple[float, float]] = []
        for wp in qs:
            lat = SurveillanceProfileService._safe_number(getattr(wp, "latitude", None), float)
            lon = SurveillanceProfileService._safe_number(getattr(wp, "longitude", None), float)
            if lat is None or lon is None:
                continue
            pts.append((lat, lon))
        km = SurveillanceProfileService._sum_polyline_km(pts)
        return km if km > 0 else None

    @staticmethod
    def _calculate_assignment_totals(
        assignments: Optional[Iterable[Dict[str, Any]]]
    ) -> Tuple[Optional[float], Optional[float]]:
        if not assignments:
            return None, None

        total_distance_km = 0.0
        total_time_minutes = 0.0
        distance_found = False
        time_found = False

        for payload in assignments:
            if not isinstance(payload, dict):
                continue

            metadata = payload.get("metadata") or {}

            distance = SurveillanceProfileService._safe_number(metadata.get("distance_km"), float)

            if distance is not None:
                total_distance_km += distance
                distance_found = True

            time_minutes = SurveillanceProfileService._safe_number(
                metadata.get("estimated_time_minutes"),
                float,
            )
            if time_minutes is not None:
                total_time_minutes += time_minutes
                time_found = True

        return (
            total_distance_km if distance_found else None,
            total_time_minutes if time_found else None,
        )

    @staticmethod
    def _get_mission_metric(mission: Optional[SurveyMission], measurement_type: str, cast_type) -> Optional[Any]:
        if not mission:
            return None
        try:
            raw_value = mission.get_numeric_value(measurement_type)
        except Exception:
            raw_value = None
        if raw_value is None:
            return None
        return SurveillanceProfileService._safe_number(raw_value, cast_type)

    @staticmethod
    def _get_profile_metric(profile: SurveillanceProfile, measurement_type: str, cast_type) -> Optional[Any]:
        try:
            raw_value = profile.get_numeric_value(measurement_type)
        except Exception:
            raw_value = None
        if raw_value is None:
            return None
        return SurveillanceProfileService._safe_number(raw_value, cast_type)

    @staticmethod
    def _set_profile_measurement(profile: SurveillanceProfile, measurement_type: str, value: Optional[Any], unit: str) -> None:
        try:
            if value is None:
                existing = profile.get_measurement(measurement_type)
                if existing:
                    existing.delete()
                return

            if measurement_type in [
                SurveillanceProfileService.MEASUREMENT_ESTIMATED_TIME,
                SurveillanceProfileService.MEASUREMENT_TOTAL_FLIGHT_TIME,
            ]:
                formatted = f"{int(value)} {unit}"
            else:
                formatted = f"{float(value):.2f} {unit}" if isinstance(value, float) else f"{value} {unit}"
            profile.set_measurement(measurement_type, formatted)
        except Exception as exc:
            logger.warning(
                "Failed to set measurement %s for profile %s: %s",
                measurement_type,
                getattr(profile, "id", None),
                exc,
            )

    @staticmethod
    def _calculate_and_set_total_flight_time(profile: SurveillanceProfile) -> None:
        """
        Calculate and set total_flight_time measurement for a completed profile
        based on actual_start_time and actual_end_time.
        """
        try:
            actual_start = profile.actual_start_time
            actual_end = profile.actual_end_time

            if not actual_start or not actual_end:
                logger.warning(
                    "Cannot calculate total_flight_time for profile %s: "
                    "missing actual_start_time or actual_end_time",
                    profile.id
                )
                return

            # Ensure timezone-aware
            if timezone.is_naive(actual_start):
                actual_start = timezone.make_aware(actual_start, timezone.get_current_timezone())
            if timezone.is_naive(actual_end):
                actual_end = timezone.make_aware(actual_end, timezone.get_current_timezone())

            # Calculate difference in minutes
            time_diff = actual_end - actual_start
            total_minutes = time_diff.total_seconds() / 60.0

            # Only set if time_diff is positive
            if total_minutes <= 0:
                logger.warning(
                    "Cannot calculate total_flight_time for profile %s: "
                    "Invalid time range (actual_end_time <= actual_start_time)",
                    profile.id
                )
                return

            # Set measurement using the same format as other time measurements
            # Format: "{int_value} mins" for consistency with estimated_time
            SurveillanceProfileService._set_profile_measurement(
                profile,
                SurveillanceProfileService.MEASUREMENT_TOTAL_FLIGHT_TIME,
                int(total_minutes),
                "mins",
            )
            logger.info(
                "Set total_flight_time for profile %s (%s): %d mins",
                profile.id,
                profile.code,
                int(total_minutes)
            )
        except Exception as exc:
            logger.exception(
                "Failed to calculate total_flight_time for profile %s: %s",
                getattr(profile, "id", None),
                exc
            )

    @staticmethod
    def _sync_profile_measurements(
        profile: SurveillanceProfile,
        total_distance_km: Any = None,
        total_estimated_time_minutes: Any = None,
        apply_distance: bool = True,
        apply_time: bool = True,
    ) -> None:
        if apply_distance:
            SurveillanceProfileService._set_profile_measurement(
                profile,
                SurveillanceProfileService.MEASUREMENT_TOTAL_DISTANCE,
                total_distance_km,
                "km",
            )
        if apply_time:
            SurveillanceProfileService._set_profile_measurement(
                profile,
                SurveillanceProfileService.MEASUREMENT_ESTIMATED_TIME,
                total_estimated_time_minutes,
                "mins",
            )

    # ------------------------------------------------------------------
    # Creation & update helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_status_by_id(status_id: Optional[int]) -> Optional[SurveillanceStatus]:
        if not status_id:
            return None
        try:
            return SurveillanceStatus.objects.get(id=status_id)
        except SurveillanceStatus.DoesNotExist as exc:
            raise ValidationError(f"Status with id {status_id} not found") from exc

    @staticmethod
    def _get_status_by_code(code: str) -> SurveillanceStatus:
        try:
            return SurveillanceStatus.objects.get(code=code)
        except SurveillanceStatus.DoesNotExist as exc:
            raise ValidationError(f"Status with code '{code}' not found. Please initialise surveillance statuses.") from exc

    @staticmethod
    def _get_default_status() -> Optional[SurveillanceStatus]:
        preferred_codes = ["pending_approval"]
        for code in preferred_codes:
            status = SurveillanceStatus.objects.filter(code=code).first()
            if status:
                return status
        return SurveillanceStatus.objects.first()

    @staticmethod
    def _get_mission(mission_id: int) -> SurveyMission:
        try:
            return SurveyMission.objects.get(id=mission_id)
        except SurveyMission.DoesNotExist as exc:
            raise ValidationError(f"Mission with id {mission_id} not found") from exc

    @staticmethod
    def _get_repeat_type(repeat_type_id: Optional[int]) -> Optional[SurveillanceProfileRepeatType]:
        if repeat_type_id is None:
            return None
        if isinstance(repeat_type_id, bool):  # guard against True/False
            return None
        if repeat_type_id:
            try:
                repeat_type_id = int(repeat_type_id)
            except (TypeError, ValueError) as exc:
                raise ValidationError("repeat_type_id must be an integer") from exc
            if repeat_type_id <= 0:
                return None
            try:
                return SurveillanceProfileRepeatType.objects.get(id=repeat_type_id)
            except SurveillanceProfileRepeatType.DoesNotExist as exc:
                raise ValidationError(f"Repeat type with id {repeat_type_id} not found") from exc
        return None

    @staticmethod
    def _get_repeat_until_type(repeat_until_type_id: Optional[int]) -> Optional[SurveillanceProfileRepeatUntilType]:
        if repeat_until_type_id is None:
            return None
        if isinstance(repeat_until_type_id, bool):
            return None
        if repeat_until_type_id:
            try:
                repeat_until_type_id = int(repeat_until_type_id)
            except (TypeError, ValueError) as exc:
                raise ValidationError("repeat_until_type_id must be an integer") from exc
            if repeat_until_type_id <= 0:
                return None
            try:
                return SurveillanceProfileRepeatUntilType.objects.get(id=repeat_until_type_id)
            except SurveillanceProfileRepeatUntilType.DoesNotExist as exc:
                raise ValidationError(f"Repeat until type with id {repeat_until_type_id} not found") from exc
        return None

    @staticmethod
    def _get_default_repeat_type() -> Optional[SurveillanceProfileRepeatType]:
        for code in ["none", "off"]:
            repeat_type = SurveillanceProfileRepeatType.objects.filter(code=code).first()
            if repeat_type:
                return repeat_type
        return SurveillanceProfileRepeatType.objects.first()

    @staticmethod
    def _get_default_repeat_until_type() -> Optional[SurveillanceProfileRepeatUntilType]:
        for code in ["never", "no_limit"]:
            repeat_until_type = SurveillanceProfileRepeatUntilType.objects.filter(code=code).first()
            if repeat_until_type:
                return repeat_until_type
        return SurveillanceProfileRepeatUntilType.objects.first()

    @staticmethod
    def _validate_repeat_config(
        repeat_type: Optional[SurveillanceProfileRepeatType],
        repeat_until_type: Optional[SurveillanceProfileRepeatUntilType],
        repeat_until_date: Optional[date],
        repeat_occurrences: Optional[int],
    ) -> None:
        repeat_code = repeat_type.code if repeat_type else None
        until_code = repeat_until_type.code if repeat_until_type else None

        if repeat_code in (None, "none", "off"):
            return

        if repeat_until_type is None:
            raise ValidationError("repeat_until_type_id is required when repeat_type is provided")

        if until_code in ("on_date", "date") and not repeat_until_date:
            raise ValidationError("repeat_until_date is required when repeat_until_type is 'on_date'")

        if until_code in ("after_occurrences", "after_n") and repeat_occurrences is None:
            raise ValidationError("repeat_occurrences must be provided when repeat_until_type is 'after_occurrences'")

        if until_code in ("after_occurrences", "after_n") and repeat_occurrences is not None and repeat_occurrences < 1:
            raise ValidationError("repeat_occurrences must be >= 1 when repeat_until_type is 'after_occurrences'")

    @staticmethod
    def _normalise_color(color_code: Optional[str]) -> Optional[str]:
        if not color_code:
            return None
        color = color_code.strip()
        if not color.startswith("#"):
            color = f"#{color}"
        return color[:7]

    @staticmethod
    def _mission_waypoints_summary(mission: SurveyMission) -> List[Dict[str, Any]]:
        waypoints = mission.waypoints.order_by("order")
        summary = []
        for wp in waypoints:
            try:
                lat = float(wp.latitude) if wp.latitude is not None else None
            except (TypeError, ValueError):
                lat = None
            try:
                lon = float(wp.longitude) if wp.longitude is not None else None
            except (TypeError, ValueError):
                lon = None

            summary.append(
                {
                    "id": wp.id,
                    "order": wp.order,
                    "name": wp.name,
                    "latitude": lat,
                    "longitude": lon,
                }
            )
        return summary

    @staticmethod
    def _collect_mission_points(
        mission: SurveyMission,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[float]]:
        mission_points: List[Dict[str, Any]] = []
        total_distance = 0.0
        previous_point: Optional[Dict[str, Any]] = None

        fallback_cruise_speed_ms = SurveillanceProfileService._safe_number(get_waypoint_speed(), float)
        if fallback_cruise_speed_ms is not None and fallback_cruise_speed_ms <= 0:
            fallback_cruise_speed_ms = None

        waypoints_qs = mission.waypoints.order_by("order", "id")
        for display_order, waypoint in enumerate(waypoints_qs, start=1):
            lat = SurveillanceProfileService._safe_number(waypoint.latitude, float)
            lon = SurveillanceProfileService._safe_number(waypoint.longitude, float)
            if lat is None or lon is None:
                continue

            altitude = None
            command_type = "waypoint"
            command_id_int: Optional[int] = None
            params: Optional[List[Any]] = None
            command_name: Optional[str] = None
            command_id_raw: Optional[Any] = None

            payload = waypoint.command_line
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except ValueError:
                    payload = None

            if isinstance(payload, dict) and payload:
                digit_keys = [
                    key for key in payload.keys() if isinstance(key, str) and key.isdigit()
                ]

                if digit_keys:
                    command_id_raw = digit_keys[0]
                    command_data = payload.get(command_id_raw)

                    if isinstance(command_data, dict) and command_data:
                        command_name, params_candidate = next(iter(command_data.items()))
                        if isinstance(params_candidate, (list, tuple)):
                            params = list(params_candidate)
                        elif params_candidate is not None:
                            params = [params_candidate]
                    elif isinstance(command_data, (list, tuple)):
                        params = list(command_data)
                else:
                    params_candidate = payload.get("params")
                    if isinstance(params_candidate, (list, tuple)):
                        params = list(params_candidate)
                    elif params_candidate is not None:
                        params = [params_candidate]

                    command = payload.get("command")
                    if isinstance(command, dict):
                        command_id_raw = command.get("id")
                        command_name = command.get("name")
                    elif isinstance(command, (int, str)):
                        command_id_raw = command
                    else:
                        command_id_raw = payload.get("command_id")

                    if not command_name:
                        command_name = (
                            payload.get("command_name")
                            or payload.get("name")
                            or payload.get("commandName")
                        )

                if command_id_raw is not None:
                    try:
                        command_id_int = int(command_id_raw)
                    except (TypeError, ValueError):
                        command_id_int = None

                if isinstance(params, (list, tuple)) and len(params) >= 7:
                    altitude = SurveillanceProfileService._safe_number(params[6], float)

                if not command_name and command_id_int is not None:
                    command_data = payload.get(str(command_id_int)) if isinstance(command_id_int, int) else None
                    if isinstance(command_data, dict) and command_data:
                        command_name = next(iter(command_data.keys()))

                if command_name:
                    upper_name = str(command_name).upper()
                    if "TAKEOFF" in upper_name:
                        command_type = "takeoff"
                    elif "RETURN" in upper_name and "LAUNCH" in upper_name:
                        command_type = "rtl"
                    elif "WAYPOINT" in upper_name:
                        command_type = "waypoint"

                if command_id_int == 22:
                    command_type = "takeoff"
                elif command_id_int == 20:
                    command_type = "rtl"

            include_point = False
            if command_id_int == 16:
                include_point = True
            elif command_type == "waypoint" and command_id_int is None:
                include_point = True

            frame_id = None
            frame_name = None
            frame_payload = waypoint.frame
            if isinstance(frame_payload, str):
                try:
                    frame_payload = json.loads(frame_payload)
                except ValueError:
                    frame_payload = None

            if isinstance(frame_payload, dict) and frame_payload:
                frame_keys = [
                    key for key in frame_payload.keys() if isinstance(key, str) and key.isdigit()
                ]
                if frame_keys:
                    primary_key = frame_keys[0]
                    frame_id = primary_key
                    frame_name = frame_payload.get(primary_key)
                else:
                    frame_id = frame_payload.get("id")
                    frame_name = frame_payload.get("name")
            elif isinstance(frame_payload, (int, float)):
                frame_id = frame_payload

            point: Dict[str, Any] = {
                "id": waypoint.id,
                "name": waypoint.name,
                "order": display_order,
                "mission_order": waypoint.order,
                "lat": lat,
                "lon": lon,
                "alt": altitude,
                "type": command_type,
                "command_id": command_id_int,
                "command_name": command_name,
                "params": params,
                "frame_id": frame_id,
                "frame_name": frame_name,
            }

            if include_point:
                if previous_point is not None:
                    segment_distance = geodesic(
                        (previous_point["lat"], previous_point["lon"]),
                        (lat, lon),
                    ).kilometers
                    if segment_distance and segment_distance > 0:
                        total_distance += segment_distance
                point["distance_from_start"] = total_distance
                previous_point = point
            else:
                point["distance_from_start"] = total_distance

            mission_points.append(point)

        candidate_points: List[Dict[str, Any]] = [
            {
                "order": point["order"],
                "latitude": point["lat"],
                "longitude": point["lon"],
                "altitude": point.get("alt"),
                "type": point.get("type"),
                "command_name": point.get("command_name"),
                "description": point.get("name") or f"Waypoint {point['order']}",
                "transect_index": None,
                "waypoint_index": point["order"] - 1,
                "mission_waypoint_id": point.get("id"),
                "distance_from_start": point.get("distance_from_start"),
            }
            for point in mission_points
        ]

        return mission_points, candidate_points, fallback_cruise_speed_ms

    @staticmethod
    def _format_device_model(device: Device) -> Optional[str]:
        manufacturer = getattr(device, "manufacturer_information", None)
        if manufacturer:
            model_number = getattr(manufacturer, "model_number", None)
            if model_number:
                return str(model_number)
        sub_type = getattr(device, "sub_type", None)
        if sub_type:
            return str(sub_type)
        library = getattr(device, "library", None)
        if library and getattr(library, "name", None):
            return str(library.name)
        return None

    @staticmethod
    def _extract_device_battery_display(device: Device) -> Optional[str]:
        measurement_sources: List[Any] = []
        telemetry = getattr(device, "telemetry", None)
        if telemetry is not None:
            measurement_sources.append(telemetry)
        propulsion = getattr(device, "propulsion_system", None)
        if propulsion is not None:
            measurement_sources.append(propulsion)
        cargo_compartments = getattr(device, "cargo_compartments", None)
        if cargo_compartments is not None:
            measurement_sources.extend(list(cargo_compartments.all()))

        for source in measurement_sources:
            try:
                measurements_qs = getattr(source, "measurements", None)
                if measurements_qs is None:
                    continue
                measurement = measurements_qs.filter(
                    measurement_type__in=["battery_level", "battery_capacity"]
                ).first()
                if not measurement:
                    continue
                data = measurement.data or {}
                value = data.get("value")
                unit = data.get("unit")
                if value is None:
                    continue
                value_str = str(value)
                if unit:
                    unit_str = str(unit)
                    if value_str.endswith(unit_str):
                        return value_str
                    if unit_str.startswith("%") or unit_str == "%":
                        return f"{value_str}%"
                    return f"{value_str} {unit_str}"
                return value_str
            except Exception:
                continue
        return None

    @staticmethod
    def _generate_default_assignments(
        mission: SurveyMission,
        start_time: datetime,
        available_devices: Optional[List[Dict[str, Any]]] = None,
        device_instances: Optional[Dict[int, Device]] = None,
        validate_duplicates: bool = True,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        # start_time = SurveillanceProfileService._normalise_start_time(start_time)
        maximum_drones = mission.maximum_drones or 1
        instances_map = dict(device_instances or {})

        if available_devices is None:
            available_devices = SurveillanceProfileService._get_available_devices(maximum_drones)

        missing_device_ids = [
            device.get("id")
            for device in available_devices
            if isinstance(device, dict) and device.get("id") not in instances_map
        ]
        if missing_device_ids:
            instances_map.update(
                SurveillanceProfileService._build_device_context(missing_device_ids)
            )

        log_default = mission.log_collection if mission.log_collection is not None else True
        video_default = mission.video_recording if mission.video_recording is not None else True
        analysis_default = mission.video_analysis if mission.video_analysis is not None else True

        segments, candidate_points, segments_viable = SurveillanceProfileService._build_drone_flight_segments(
            mission,
            available_devices,
            device_instances=instances_map,
            diagnostics=diagnostics,
        )
        segments = segments or []
        candidate_points = candidate_points or []

        raw_assignments: List[Dict[str, Any]] = []
        display_assignments: List[Dict[str, Any]] = []
        start_end_choices: List[Dict[str, Any]] = []
        if not segments_viable:
            start_end_choices = [point.copy() for point in candidate_points]
            return raw_assignments, display_assignments, start_end_choices

        if segments:
            for index, segment in enumerate(segments, start=1):
                segment_points = segment.get("points") or []
                start_point = segment.get("start_point") or {}
                end_point = segment.get("end_point") or {}

                assigned_device = segment.get("assigned_device")
                device_info = assigned_device.copy() if isinstance(assigned_device, dict) else None
                if not device_info:
                    device_info = {"id": None, "name": f"Drone {index}", "serial_number": None}
                route_path = [
                    {
                        "order": point.get("order"),
                        "latitude": point.get("lat"),
                        "longitude": point.get("lon"),
                        "altitude": point.get("alt"),
                        "distance_from_start": point.get("distance_from_start"),
                        "type": point.get("type"),
                        "mission_waypoint_id": point.get("id"),
                        "name": point.get("name"),
                        "command_id": point.get("command_id"),
                        "params": point.get("params"),
                        "frame_id": point.get("frame_id"),
                        "frame_name": point.get("frame_name"),
                        "command_name": point.get("command_name"),
                    }
                    for point in segment_points
                ]

                metadata = {
                    "start_point": start_point,
                    "end_point": end_point,
                    "takeoff_point": None,
                    "landing_point": None,
                    "route_path": route_path,
                    "transect_path": None,
                    "transect_range": None,
                    "waypoint_range": {
                        "start": start_point.get("order"),
                        "end": end_point.get("order"),
                    },
                    "distance_km": segment.get("distance_km"),
                    "path_distance_km": segment.get("path_distance_km"),
                    "takeoff_distance_km": segment.get("takeoff_distance_km"),
                    "estimated_time_minutes": segment.get("estimated_time_minutes"),
                    "flight_estimation": segment.get("flight_estimation"),
                }

                if device_info:
                    metadata["takeoff_point"] = {
                        "terminal_id": device_info.get("terminal_id"),
                        "terminal_name": device_info.get("terminal_name"),
                        "latitude": device_info.get("terminal_latitude"),
                        "longitude": device_info.get("terminal_longitude"),
                    }

                raw_assignments.append(
                    {
                        "order": index,
                        "device_id": device_info.get("id"),
                        "scheduled_start_time": start_time,
                        "start_waypoint_id": start_point.get("id"),
                        "end_waypoint_id": end_point.get("id"),
                        "log_collection": log_default,
                        "video_recording": video_default,
                        "video_analysis": analysis_default,
                        "metadata": metadata,
                    }
                )

                display_assignments.append(
                    {
                        "order": index,
                        "device": device_info,
                        "device_id": device_info.get("id"),
                        "scheduled_start_time": start_time,
                        "start_waypoint": {
                            "id": start_point.get("id"),
                            "name": start_point.get("name") or f"Waypoint {start_point.get('order')}",
                            "latitude": start_point.get("lat"),
                            "longitude": start_point.get("lon"),
                        },
                        "end_waypoint": {
                            "id": end_point.get("id"),
                            "name": end_point.get("name") or f"Waypoint {end_point.get('order')}",
                            "latitude": end_point.get("lat"),
                            "longitude": end_point.get("lon"),
                        },
                        "log_collection": log_default,
                        "video_recording": video_default,
                        "video_analysis": analysis_default,
                        "distance_km": segment.get("distance_km"),
                        "takeoff_distance_km": segment.get("takeoff_distance_km"),
                        "path_distance_km": segment.get("path_distance_km"),
                        "flight_estimation": segment.get("flight_estimation"),
                        "takeoff_point": metadata.get("takeoff_point"),
                        "estimated_time_minutes": segment.get("estimated_time_minutes"),
                        "route_path": route_path,
                        "transect_path": None,
                    }
                )

            if validate_duplicates:
                SurveillanceProfileService._validate_duplicate_assignments(raw_assignments)
                SurveillanceProfileService._adjust_duplicate_assignment_times(raw_assignments, display_assignments)

            start_end_choices = [point.copy() for point in candidate_points]

            return raw_assignments, display_assignments, start_end_choices

        # Fallback: use mission waypoints start/end
        waypoints = list(mission.waypoints.order_by("order"))
        first_wp = waypoints[0] if waypoints else None
        last_wp = waypoints[-1] if waypoints else None

        def waypoint_payload(wp):
            if not wp:
                return None, None
            try:
                lat = float(wp.latitude) if wp.latitude is not None else None
            except (TypeError, ValueError):
                lat = None
            try:
                lon = float(wp.longitude) if wp.longitude is not None else None
            except (TypeError, ValueError):
                lon = None
            return wp.id, {
                "id": wp.id,
                "name": wp.name,
                "order": wp.order,
                "latitude": lat,
                "longitude": lon,
            }

        start_wp_id, start_wp_display = waypoint_payload(first_wp)
        end_wp_id, end_wp_display = waypoint_payload(last_wp)

        for index in range(maximum_drones):
            device = available_devices[index] if index < len(available_devices) else None
            raw_assignments.append(
                {
                    "order": index + 1,
                    "device_id": device["id"] if device else None,
                    "scheduled_start_time": start_time,
                    "start_waypoint_id": start_wp_id,
                    "end_waypoint_id": end_wp_id,
                    "log_collection": log_default,
                    "video_recording": video_default,
                    "video_analysis": analysis_default,
                }
            )

            display_assignments.append(
                {
                    "order": index + 1,
                    "device": device,
                    "device_id": device["id"] if device else None,
                    "scheduled_start_time": start_time,
                    "start_waypoint": start_wp_display,
                    "end_waypoint": end_wp_display,
                    "log_collection": log_default,
                    "video_recording": video_default,
                    "video_analysis": analysis_default,
                    "estimated_time_minutes": None,
                }
            )

        if validate_duplicates:
            SurveillanceProfileService._validate_duplicate_assignments(raw_assignments)
            SurveillanceProfileService._adjust_duplicate_assignment_times(raw_assignments, display_assignments)

        if waypoints and not start_end_choices:
            for idx, wp in enumerate(waypoints):
                try:
                    lat = float(wp.latitude) if wp.latitude is not None else None
                except (TypeError, ValueError):
                    lat = None
                try:
                    lon = float(wp.longitude) if wp.longitude is not None else None
                except (TypeError, ValueError):
                    lon = None
                start_end_choices.append(
                    {
                        "order": idx + 1,
                        "latitude": lat,
                        "longitude": lon,
                        "altitude": None,
                        "type": "waypoint",
                        "description": wp.name or f"Waypoint {idx + 1}",
                        "transect_index": None,
                        "waypoint_index": idx,
                        "mission_waypoint_id": wp.id,
                        "distance_from_start": None,
                    }
                )

        if validate_duplicates:
            SurveillanceProfileService._validate_duplicate_assignments(
                raw_assignments,
                display_assignments,
            )

        return raw_assignments, display_assignments, start_end_choices

    @staticmethod
    def get_create_context(mission_id: int, start_time: Optional[datetime] = None) -> Dict[str, Any]:
        try:
            mission = SurveyMission.objects.select_related("purpose").get(id=mission_id)
        except SurveyMission.DoesNotExist as exc:
            raise ValidationError(f"Mission with id {mission_id} not found") from exc

        start_time = SurveillanceProfileService._normalise_start_time(start_time)

        repeat_types = SurveillanceProfileService._get_repeat_type_options()
        repeat_until_types = SurveillanceProfileService._get_repeat_until_type_options()

        max_drones = mission.maximum_drones or 1
        available_devices_all = SurveillanceProfileService._get_available_devices(max_drones)
        device_instances_map = SurveillanceProfileService._build_device_context(
            [
                device.get("id")
                for device in available_devices_all
                if isinstance(device, dict)
            ]
        )
        if not available_devices_all:
            return {
                "mission": None,
                "profile_defaults": None,
                "drones": [],
                "raw_assignments": [],
                "start_end_points": [],
            }
        if len(available_devices_all) < max_drones:
            max_drones = len(available_devices_all)
        devices_for_assignment = available_devices_all[:max_drones]
        raw_assignments, display_assignments, start_end_choices = SurveillanceProfileService._generate_default_assignments(
            mission,
            start_time,
            available_devices=devices_for_assignment,
            device_instances=device_instances_map,
            validate_duplicates=False,
        )

        if not display_assignments:
            available_devices_all = []
            raw_assignments = []
            start_end_choices = []
        else:
            SurveillanceProfileService._adjust_duplicate_assignment_times(raw_assignments, display_assignments)

        mission_distance = None
        mission_time = None
        try:
            distance_value = mission.get_numeric_value(
                SurveillanceProfileService.MEASUREMENT_TOTAL_DISTANCE
            )
            if distance_value is not None:
                mission_distance = float(distance_value)
        except Exception:
            mission_distance = None
        try:
            time_value = mission.get_numeric_value(
                SurveillanceProfileService.MEASUREMENT_ESTIMATED_TIME
            )
            if time_value is not None:
                mission_time = int(time_value)
        except Exception:
            mission_time = None

        mission_detail = {
            "id": mission.id,
            "name": mission.name,
            "purpose": getattr(mission.purpose, "name", None),
            "maximum_drones": mission.maximum_drones or 1,
            "log_collection": mission.log_collection if mission.log_collection is not None else True,
            "video_recording": mission.video_recording if mission.video_recording is not None else True,
            "video_analysis": mission.video_analysis if mission.video_analysis is not None else True,
            "total_distance_km": mission_distance,
            "total_estimated_time_minutes": mission_time,
            "polygon": mission.polygon,
            "waypoints": SurveillanceProfileService._mission_waypoints_summary(mission),
        }

        return {
            "mission": mission_detail,
            "profile_defaults": {
                "start_time": start_time,
                "color_code": "#1D9BE2",
                "log_collection": mission_detail["log_collection"],
                "video_recording": mission_detail["video_recording"],
                "video_analysis": mission_detail["video_analysis"],
                "total_distance_km": mission_distance,
                "total_estimated_time_minutes": mission_time,
            },
            "drones": display_assignments,
            "raw_assignments": raw_assignments,
            "start_end_points": start_end_choices,
            "repeat_type_options": repeat_types,
            "repeat_until_type_options": repeat_until_types,
            "available_devices": available_devices_all,
        }

    @staticmethod
    def get_change_drone_options(
        profile_id: int,
        start_waypoint_id: int,
        end_waypoint_id: int,
        page_size: int,
        current_page: int,
    ) -> Dict[str, Any]:
        page_size = max(1, int(page_size or 10))
        current_page = max(1, int(current_page or 1))

        try:
            profile = (
                SurveillanceProfile.objects.select_related("mission")
                .prefetch_related("drone_assignments__device")
                .get(id=profile_id)
            )
        except SurveillanceProfile.DoesNotExist as exc:
            raise ValidationError("Surveillance profile not found") from exc

        mission = profile.mission
        if mission is None:
            raise ValidationError("Profile does not have an associated mission")

        mission_points, _, fallback_cruise_speed_ms = SurveillanceProfileService._collect_mission_points(mission)
        start_point = next((point for point in mission_points if point["id"] == start_waypoint_id), None)
        if start_point is None:
            raise ValidationError("Start waypoint does not belong to mission")
        end_point = next((point for point in mission_points if point["id"] == end_waypoint_id), None)
        if end_point is None:
            raise ValidationError("End waypoint does not belong to mission")

        start_index = mission_points.index(start_point)
        end_index = mission_points.index(end_point)
        if end_index <= start_index:
            raise ValidationError("End waypoint must come after start waypoint")

        segment_points = mission_points[start_index : end_index + 1]
        path_distance_km = SurveillanceProfileService._calculate_path_distance(segment_points)
        required_distance_km = max(path_distance_km, 0.0)

        assigned_device_ids = set(
            profile.drone_assignments.exclude(device_id__isnull=True).values_list("device_id", flat=True)
        )
        available_devices = SurveillanceProfileService._get_available_devices(available=True)
        candidate_devices = [
            device
            for device in available_devices
            if device.get("id") not in assigned_device_ids
            and device.get("id")
        ]

        device_instances = SurveillanceProfileService._build_device_context(
            [device.get("id") for device in candidate_devices]
        )
        candidates = SurveillanceProfileService._prepare_drone_candidates(
            candidate_devices,
            device_instances,
            fallback_cruise_speed_ms,
        )

        start_lat = SurveillanceProfileService._safe_number(start_point.get("lat"), float)
        start_lon = SurveillanceProfileService._safe_number(start_point.get("lon"), float)

        results: List[Dict[str, Any]] = []
        for candidate in candidates:
            device_info = candidate.get("device") or {}
            device_instance = candidate.get("instance")
            if device_instance is None:
                continue

            device_id = device_info.get("id")
            if not device_id:
                continue

            takeoff_distance_km = 0.0
            terminal_lat = SurveillanceProfileService._safe_number(device_info.get("terminal_latitude"), float)
            terminal_lon = SurveillanceProfileService._safe_number(device_info.get("terminal_longitude"), float)
            if (
                terminal_lat is not None
                and terminal_lon is not None
                and start_lat is not None
                and start_lon is not None
            ):
                try:
                    takeoff_distance_km = geodesic(
                        (terminal_lat, terminal_lon),
                        (start_lat, start_lon),
                    ).kilometers
                except (ValueError, TypeError):
                    takeoff_distance_km = 0.0

            total_distance_km = required_distance_km + takeoff_distance_km
            distance_m = max(total_distance_km, 0.0) * 1000.0

            try:
                estimation = FlightEstimationService.estimate_duration_for_distance(
                    device_instance,
                    distance_m,
                    default_cruise_speed=fallback_cruise_speed_ms,
                )
            except Exception:
                continue

            if not estimation.get("can_complete"):
                continue

            estimated_duration_min = estimation.get("estimated_duration_min")
            if estimated_duration_min is None and estimation.get("estimated_duration_s") is not None:
                estimated_duration_min = round(float(estimation["estimated_duration_s"]) / 60.0, 2)

            flight_time_s = estimation.get("flight_time_s")
            estimated_s = estimation.get("estimated_duration_s")
            battery_margin_percent: Optional[float] = None
            if flight_time_s and estimated_s is not None and flight_time_s > 0:
                battery_margin_percent = max(
                    0.0,
                    min(100.0, round((flight_time_s - estimated_s) / flight_time_s * 100.0, 2)),
                )

            

            results.append(
                {
                    "device_id": device_instance.id,
                    "serial_number": device_instance.name,
                    "model": SurveillanceProfileService._format_device_model(device_instance),
                    "battery": "100%",
                }
            )

        total_items = len(results)
        if total_items == 0:
            return {
                "items": [],
                "total_items": 0,
                "total_pages": 0,
                "current_page": 1,
            }

        total_pages = math.ceil(total_items / page_size)
        current_page = min(current_page, total_pages) if total_pages > 0 else 1
        start_index = (current_page - 1) * page_size
        end_index = start_index + page_size
        paginated_items = results[start_index:end_index]

        return {
            "items": paginated_items,
            "total_items": total_items,
            "total_pages": total_pages,
            "current_page": current_page,
        }

    @staticmethod
    def _build_flightbird_upload_payload(profile: SurveillanceProfile) -> Dict[str, Any]:
        assignments_qs = SurveillanceProfileService._drone_prefetch_queryset().filter(profile=profile)
        assignments = list(assignments_qs)

        mission = profile.mission
        route_paths_map: Dict[int, List[Dict[str, Any]]] = {}
        if mission:
            route_paths_map = SurveillanceProfileService.build_route_paths_for_assignments(assignments, mission)
        surveillance_profile_drone_schema = [SurveillanceProfileDroneOutSchema.from_queryset(assignment, many=False) for assignment in assignments]
        for assignment in surveillance_profile_drone_schema:
            assignment_id = assignment.get("id")
            if assignment_id and assignment_id in route_paths_map:
                assignment["route_path"] = route_paths_map[assignment_id]

        # Extract polygon data - handle both line mission and polygon mission
        polygon_data = None
        if mission:
            # Prefetch waypoints if not already prefetched
            if not hasattr(mission, '_prefetched_objects_cache') or 'waypoints' not in getattr(mission, '_prefetched_objects_cache', {}):
                waypoints = list(mission.waypoints.all().order_by('order'))
            else:
                waypoints = list(mission.waypoints.all())
            
            # Determine if line mission: check if any waypoint has terminal_id
            is_line_mission = any(wp.terminal_id for wp in waypoints) if waypoints else False
            
            # Alternative check: if no polygon, it's a line mission
            has_polygon = mission.polygon and isinstance(mission.polygon, list) and len(mission.polygon) > 0
            if not is_line_mission and not has_polygon:
                is_line_mission = True
            
            # Extract polygon based on mission type
            if is_line_mission:
                # For line mission, convert waypoints to polygon format [[lat, lon], ...]
                if waypoints:
                    sorted_waypoints = sorted(waypoints, key=lambda wp: wp.order)
                    polygon_data = [
                        [float(wp.latitude), float(wp.longitude)]
                        for wp in sorted_waypoints
                        if wp.latitude and wp.longitude and wp.latitude != '0' and wp.longitude != '0'
                    ]
            else:
                # For polygon mission, use polygon from mission
                if has_polygon:
                    polygon_data = mission.polygon
            
            # Fallback: if still no polygon data, try to get from waypoints as last resort
            if not polygon_data and waypoints:
                sorted_waypoints = sorted(waypoints, key=lambda wp: wp.order)
                polygon_data = [
                    [float(wp.latitude), float(wp.longitude)]
                    for wp in sorted_waypoints
                    if wp.latitude and wp.longitude and wp.latitude != '0' and wp.longitude != '0'
                ]
        
        # Ensure polygon_data is always a list (empty list if no data)
        if polygon_data is None:
            polygon_data = []

        altitude_separation = profile.get_measurement('altitude_separation').get_numeric_value() if profile.get_measurement('altitude_separation') else None
        takeoff_altitude = profile.get_measurement('takeoff_altitude').get_numeric_value() if profile.get_measurement('takeoff_altitude') else None
        capture_altitude = mission.get_measurement('altitude').get_numeric_value() if mission.get_measurement('altitude') else None
        return {
            "id": profile.id,
            "drone_assignments": surveillance_profile_drone_schema,
            "polygon": polygon_data,
            "altitude_separation": altitude_separation,
            "takeoff_altitude": takeoff_altitude,
            "capture_altitude":capture_altitude
        }

    @staticmethod
    async def _record_video_with_timeout(
        stream_monitor_id: str,
        duration_seconds: int = 60,
        detection_type: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Helper async function to start AI dual stream and video recording, wait for specified duration, then stop.
        
        Returns:
            Tuple[Optional[str], Optional[str]]: (video_path, analysis_path) or (None, None) on failure
        """
        # NOTE:
        # - We intentionally call StreamMonitorService.start_record/stop_record (not *_optimize) to match
        #   the canonical record flow and get rich logs.
        # - We intentionally manage start_detect/stop_detect synchronously here. Reason: stop_record uses
        #   asyncio.create_task for stop_detect in background; when this function is executed via asyncio.run,
        #   pending tasks may be cancelled when the loop closes, losing detect logs/results.
        ai_model_code = detection_type or "person"
        record_id: Optional[str] = None
        video_path: Optional[str] = None
        analysis_path: Optional[str] = None
        detect_started = False
        headers = {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }
        
        try:
            # Start video recording (canonical flow)
            started_record_id, _stream_id = await StreamMonitorService.start_record(
                stream_monitor_id,
                ai_model_code,
                enable_detection=True,
                from_fe=False,
            )
            if not started_record_id:
                logger.warning("[SURVEILLANCE][SIM] Failed to start_record for stream %s", stream_monitor_id)
                return None, None
            record_id = str(started_record_id)

            logger.info(
                "[SURVEILLANCE][SIM] Started recording for stream %s with record_id=%s (detection_type=%s)",
                stream_monitor_id,
                record_id,
                ai_model_code,
            )

            # Start detection (explicit, synchronous)
            detection_url = f"{settings.AI_GRPC_URL}/start_detect"
            start_detect_body = {
                'detection_id': record_id,
                'detection_type': ai_model_code,
                'input_rtsp': f"{settings.RTSP_URL}/stream/{stream_monitor_id}",
            }
            start_result = await asyncio.to_thread(
                requests.post,
                detection_url,
                json=start_detect_body,
                headers=headers,
                timeout=30,
                verify=False,
            )
            start_json = start_result.json()
            detect_started = bool(start_json.get("running"))
            if not detect_started:
                logger.warning(
                    "[SURVEILLANCE][SIM] Failed to start_detect for stream %s record_id=%s resp=%s",
                    stream_monitor_id,
                    record_id,
                    start_json,
                )
            else:
                logger.info(
                    "[SURVEILLANCE][SIM] Started detect for stream %s record_id=%s detection_type=%s",
                    stream_monitor_id,
                    record_id,
                    ai_model_code,
                )
            
            # Wait for specified duration with timeout protection
            # Use wait_for to ensure we don't wait indefinitely and can handle cancellation
            try:
                # Add buffer time (10 seconds) to ensure cleanup happens even if there's a delay
                max_wait_time = duration_seconds + 10
                await asyncio.wait_for(asyncio.sleep(duration_seconds), timeout=max_wait_time)
            except asyncio.TimeoutError:
                logger.warning(f"Wait timeout exceeded for stream {stream_monitor_id}, proceeding with cleanup")
            except asyncio.CancelledError:
                logger.warning(f"Recording task cancelled for stream {stream_monitor_id}, proceeding with cleanup")
                raise  # Re-raise to ensure proper cancellation handling
            
            # Stop video recording first (if it was started)
            if record_id:
                try:
                    video_path = await StreamMonitorService.stop_record(
                        stream_monitor_id,
                        record_id,
                        user=None,
                        enable_detection=False,  # detect is stopped explicitly below
                    )
                    if video_path:
                        logger.info(
                            "[SURVEILLANCE][SIM] Stopped recording for stream %s record_id=%s object_path=%s",
                            stream_monitor_id,
                            record_id,
                            video_path,
                        )
                    else:
                        logger.warning(
                            "[SURVEILLANCE][SIM] stop_record returned no object_path for stream %s record_id=%s",
                            stream_monitor_id,
                            record_id,
                        )
                except Exception as record_exc:
                    logger.exception(f"Error stopping video recording for stream {stream_monitor_id}: {record_exc}")

            # Stop detection (explicit, synchronous) and extract detections
            detections = []
            if record_id and detect_started:
                stop_detection_url = f"{settings.AI_GRPC_URL}/stop_detect"
                stop_detection_body_data = {'detection_id': record_id}
                stop_result = await asyncio.to_thread(
                    requests.post,
                    stop_detection_url,
                    json=stop_detection_body_data,
                    headers=headers,
                    timeout=30,
                    verify=False,
                )
                stop_api_response = stop_result.json()
                if not stop_api_response.get('status'):
                    logger.warning(
                        "[SURVEILLANCE][SIM] Failed to stop_detect for stream %s record_id=%s resp=%s",
                        stream_monitor_id,
                        record_id,
                        stop_api_response,
                    )
                else:
                    logger.info(
                        "[SURVEILLANCE][SIM] Stopped detect for stream %s record_id=%s",
                        stream_monitor_id,
                        record_id,
                    )
                detections = stop_api_response.get('detections', []) or []
            
            # Save detections as JSON
            # For debugging we still save an analysis JSON even when detections are empty,
            # as long as stop_detect returned successfully and we have a record_id.
            if record_id and detect_started:
                try:
                    # Generate filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{stream_monitor_id}"
                    analysis_path = await asyncio.to_thread(
                        minio_client.save_json,
                        detections,
                        stream_monitor_id,
                        filename,
                    )
                    if analysis_path:
                        logger.info(f"Saved detections JSON for stream {stream_monitor_id} to {analysis_path}")
                    else:
                        logger.warning(f"Failed to save detections JSON for stream {stream_monitor_id}")
                except Exception as json_exc:
                    logger.exception(f"Error saving detections JSON for stream {stream_monitor_id}: {json_exc}")
            
            # Return video_path and analysis_path
            return video_path, analysis_path
            
        except asyncio.CancelledError:
            logger.warning(f"Recording task cancelled for stream {stream_monitor_id}, cleaning up resources")
            # Cleanup will happen in finally block
            raise  # Re-raise to properly propagate cancellation
        except Exception as exc:
            logger.exception(f"Error in AI dual stream and recording process for stream {stream_monitor_id}: {exc}")
        finally:
            # Always ensure cleanup happens, even if task is cancelled or exception occurs
            logger.info(
                "[SURVEILLANCE][SIM] Ensuring cleanup for stream %s (record_id: %s, detect_started: %s)",
                stream_monitor_id,
                record_id,
                detect_started,
            )
            
            # Stop video recording if it was started
            if record_id and not video_path:
                try:
                    logger.info(
                        "[SURVEILLANCE][SIM] Cleaning up recording for stream %s record_id=%s",
                        stream_monitor_id,
                        record_id,
                    )
                    cleanup_video_path = await StreamMonitorService.stop_record(
                        stream_monitor_id,
                        record_id,
                        user=None,
                        enable_detection=False,
                    )
                    if cleanup_video_path and not video_path:
                        video_path = cleanup_video_path
                        logger.info(f"Recovered video path during cleanup: {cleanup_video_path}")
                except Exception as cleanup_exc:
                    logger.exception(f"Error during cleanup of video recording for stream {stream_monitor_id}: {cleanup_exc}")

            # Stop detection if it was started and we haven't produced analysis yet
            if record_id and detect_started and not analysis_path:
                try:
                    stop_detection_url = f"{settings.AI_GRPC_URL}/stop_detect"
                    stop_detection_body_data = {'detection_id': record_id}
                    stop_result = await asyncio.to_thread(
                        requests.post,
                        stop_detection_url,
                        json=stop_detection_body_data,
                        headers=headers,
                        timeout=30,
                        verify=False,
                    )
                    stop_api_response = stop_result.json()
                    detections = stop_api_response.get('detections', []) or []
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{stream_monitor_id}"
                    analysis_path = await asyncio.to_thread(
                        minio_client.save_json,
                        detections,
                        stream_monitor_id,
                        filename,
                    )
                    if analysis_path:
                        logger.info(f"Recovered detections JSON during cleanup: {analysis_path}")
                except Exception as cleanup_exc:
                    logger.exception(
                        "[SURVEILLANCE][SIM] Error during cleanup of detection for stream %s: %s",
                        stream_monitor_id,
                        cleanup_exc,
                    )
            
            # # Stop AI dual stream if it was started
            # if stream_id:
            #     try:
            #         logger.info(f"Cleaning up AI dual stream for stream {stream_monitor_id}, stream_id: {stream_id}")
            #         cleanup_stop_result = StreamMonitorService.stop_ai_dual_stream_optimized(stream_id, stream_monitor_id)
            #         if not cleanup_stop_result.get('success'):
            #             logger.warning(f"Failed to stop AI dual stream during cleanup for stream {stream_monitor_id}: {cleanup_stop_result.get('error')}")
            #         else:
            #             # Try to extract detections if we haven't already
            #             if not analysis_path:
            #                 stop_api_response = cleanup_stop_result.get('api_response', {})
            #                 detections = stop_api_response.get('detections', [])
            #                 if detections:
            #                     try:
            #                         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            #                         filename = f"{timestamp}_{stream_monitor_id}"
            #                         analysis_path = minio_client.save_json(detections, stream_monitor_id, filename)
            #                         if analysis_path:
            #                             logger.info(f"Recovered detections JSON during cleanup: {analysis_path}")
            #                     except Exception as json_exc:
            #                         logger.exception(f"Error saving detections JSON during cleanup: {json_exc}")
            #     except Exception as cleanup_exc:
            #         logger.exception(f"Error during cleanup of AI dual stream for stream {stream_monitor_id}: {cleanup_exc}")
        
        # Return results (will be None, None if cleanup was needed)
        return video_path, analysis_path

    @staticmethod
    def simulate_upload_profile_to_flightbird(
        *,
        profile: Optional["SurveillanceProfile"] = None,
        profile_id: Optional[int] = None,
        duration_seconds: int = 30,
        limit: Optional[int] = None,
        wait_analysis_seconds: int = 15,
    ) -> Dict[str, Any]:
        """
        Run a lightweight simulation of the "record video + detect" part that is related to
        `upload_profile_to_flightbird`, so engineers can inspect logs around:
        - AI detect start/stop (AI_GRPC_URL)
        - video record start/stop (StreamMonitorService.*_record_optimize)

        Notes:
        - This DOES NOT call Flightbird upload endpoint.
        - This function is meant for debugging/logging and should be run manually (CLI/shell).
        - It relies on configured `settings.AI_GRPC_URL`, `settings.RTSP_URL` and streaming services.
        """

        if profile is None and profile_id is None:
            raise ValidationError("profile or profile_id is required")

        if duration_seconds <= 0:
            raise ValidationError("duration_seconds must be > 0")

        if limit is not None and int(limit) <= 0:
            raise ValidationError("limit must be > 0")
        if wait_analysis_seconds < 0:
            raise ValidationError("wait_analysis_seconds must be >= 0")

        if profile is None:
            profile = (
                SurveillanceProfile._base_manager
                .select_related("mission__purpose")
                .prefetch_related("drone_assignments__device")
                .get(id=int(profile_id))
            )

        mission_purpose_code = getattr(getattr(getattr(profile, "mission", None), "purpose", None), "code", None)
        resolved_detection_type = (
            SurveillanceProfileService.mapping_mission_purpose_code_to_ai_model_code(mission_purpose_code)
            if mission_purpose_code
            else "person"
        )

        stream_ids: List[str] = []
        for assignment in profile.drone_assignments.all():
            device = getattr(assignment, "device", None)
            unit_id = getattr(device, "unit_id", None)
            if unit_id:
                stream_ids.append(str(unit_id))

        # Deduplicate while preserving order
        seen = set()
        stream_ids = [sid for sid in stream_ids if not (sid in seen or seen.add(sid))]
        if limit is not None:
            stream_ids = stream_ids[: int(limit)]

        results: Dict[str, Any] = {
            "profile_id": getattr(profile, "id", profile_id),
            "stream_monitor_ids": stream_ids,
            "duration_seconds": int(duration_seconds),
            "detection_type": resolved_detection_type,
            "wait_analysis_seconds": int(wait_analysis_seconds),
            "items": [],
        }

        # NOTE:
        # We intentionally implement the simulation flow using the same entrypoints as runtime:
        # - start: StreamMonitorService.start_record(...)
        # - stop: stop_record(...) with enable_detection=True (so it triggers background stop_detect),
        #         and persist video_path like mark_drone_flight_time does.
        #
        # This avoids double-starting detection (which causes "already running") and matches production.

        original_status_id = getattr(profile.status, "id", None) if getattr(profile, "status", None) else None
        try:
            # Ensure this profile is discoverable as in-progress during analysis persistence.
            in_progress = SurveillanceProfileService._get_status_by_code("in_progress")
            if getattr(profile.status, "code", None) != "in_progress":
                profile.status = in_progress
                profile.save(update_fields=["status", "modified_on"])

            # Map stream_id -> assignment (for deterministic persistence)
            assignment_by_stream: Dict[str, SurveillanceProfileDrone] = {}
            for a in profile.drone_assignments.select_related("device", "profile", "profile__operator", "profile__mission"):
                unit_id = getattr(getattr(a, "device", None), "unit_id", None)
                if unit_id:
                    assignment_by_stream[str(unit_id)] = a

            # Start recordings for all streams first (so drones run "concurrently" during sleep)
            started: Dict[str, Any] = {}
            analysis_enabled = True  # simulation aims to exercise detect+analysis path
            ai_model_code = resolved_detection_type or "person"

            for sid in stream_ids:
                try:
                    record_id, _sid = async_to_sync(StreamMonitorService.start_record)(
                        sid,
                        ai_model_code,
                        enable_detection=analysis_enabled,
                        from_fe=False,
                    )
                    started[sid] = {
                        "record_id": str(record_id) if record_id else None,
                        "start_time": timezone.now(),
                    }
                    logger.info("[SURVEILLANCE][SIM] Started stream=%s record_id=%s", sid, started[sid]["record_id"])
                except Exception as exc:
                    logger.exception("[SURVEILLANCE][SIM] Failed to start_record stream=%s: %s", sid, exc)
                    started[sid] = {"record_id": None, "start_time": timezone.now(), "start_error": str(exc)}

            # Simulate flight time
            pytime.sleep(int(duration_seconds))

            # Stop recordings one-by-one like mark_drone_flight_time does (per drone / per record / per detect)
            for sid in stream_ids:
                assignment = assignment_by_stream.get(str(sid))
                record_id = (started.get(sid) or {}).get("record_id")
                start_time = (started.get(sid) or {}).get("start_time") or timezone.now()

                if not assignment:
                    results["items"].append(
                        {
                            "stream_monitor_id": sid,
                            "video_path": None,
                            "analysis_path": None,
                            "success": False,
                            "error": "No assignment found for this stream in the provided profile",
                        }
                    )
                    continue

                # Persist flight_time measurement onto assignment (same as mark_drone_flight_time)
                try:
                    end_time = timezone.now()
                    flight_minutes = (end_time - start_time).total_seconds() / 60.0
                    assignment.set_measurement("flight_time", f"{round(flight_minutes, 2)} mins")
                except Exception:
                    logger.exception("[SURVEILLANCE][SIM] Failed to set flight_time measurement for stream=%s", sid)

                try:
                    if not record_id:
                        record = (
                            StreamMonitorRecord._base_manager.filter(stream_id=str(sid), status="running")
                            .order_by("-created_at", "-id")
                            .first()
                        )
                        record_id = str(record.id) if record else None

                    if not record_id:
                        results["items"].append(
                            {
                                "stream_monitor_id": sid,
                                "video_path": None,
                                "analysis_path": None,
                                "success": False,
                                "error": "No running StreamMonitorRecord found to stop",
                            }
                        )
                        continue

                    user = assignment.profile.operator if assignment.profile else None
                    group_id = getattr(getattr(assignment.profile, "mission", None), "group_id", None)

                    object_path = async_to_sync(StreamMonitorService.stop_record)(
                        str(sid),
                        str(record_id),
                        user=user,
                        enable_detection=analysis_enabled,
                        group_id=group_id,
                        # Ensure analysis_path is persisted deterministically for this assignment.
                        profile_drone_id=assignment.id,
                    )
                    if object_path:
                        SurveillanceProfileMediaService.save_recording_result_for_profile_drone(assignment.id, object_path)

                    results["items"].append(
                        {
                            "stream_monitor_id": sid,
                            "video_path": assignment.video_path,
                            "analysis_path": assignment.analysis_path,
                            "success": True,
                            "record_id": record_id,
                            "object_path": object_path,
                        }
                    )
                except Exception as exc:
                    logger.exception("[SURVEILLANCE][SIM] Failed to stop stream=%s: %s", sid, exc)
                    results["items"].append(
                        {
                            "stream_monitor_id": sid,
                            "video_path": None,
                            "analysis_path": None,
                            "success": False,
                            "error": str(exc),
                        }
                    )

            # Give background stop_detect time to finish and persist analysis_path, then refresh assignments.
            if int(wait_analysis_seconds) > 0:
                pytime.sleep(int(wait_analysis_seconds))
                for item in results["items"]:
                    sid = item.get("stream_monitor_id")
                    assignment = assignment_by_stream.get(str(sid))
                    if assignment:
                        assignment.refresh_from_db(fields=["video_path", "analysis_path", "modified_on"])
                        item["video_path"] = assignment.video_path
                        item["analysis_path"] = assignment.analysis_path

        finally:
            # Restore original profile status
            if original_status_id and getattr(profile.status, "id", None) != original_status_id:
                original_status = SurveillanceStatus.objects.filter(id=original_status_id).first()
                if original_status:
                    profile.status = original_status
                    profile.save(update_fields=["status", "modified_on"])

        return results

    @staticmethod
    def mapping_mission_purpose_code_to_ai_model_code(mission_purpose_code: str) -> str:
        if mission_purpose_code == 'firefighting':
            return 'fire_smoke'
        else:
            return 'person'
    @staticmethod
    def upload_profile_to_flightbird(profile: SurveillanceProfile) -> None:
        flightbird_url = os.environ.get("FLIGHTBRID_URL")
        if not flightbird_url:
            logger.warning("FLIGHTBRID_URL environment variable not configured; skip upload to Flightbird")
            return

        payload = SurveillanceProfileService._build_flightbird_upload_payload(profile)
        endpoint = f"{flightbird_url.rstrip('/')}/api/drone/profile/upload"
        # get list devices profile
        devices = profile.drone_assignments.all()
        # Mission flags:
        # - video_recording: record only
        # - video_analysis: record + detect (analysis requires stream, so implies recording)
        mission_recording = bool(getattr(profile.mission, "video_recording", False))
        mission_analysis = bool(getattr(profile.mission, "video_analysis", False))

        for device in devices:
            assignment_recording = bool(getattr(device, "video_recording", False))
            assignment_analysis = bool(getattr(device, "video_analysis", False))

            record_enabled = assignment_recording
            analysis_enabled = assignment_analysis
            
            if not record_enabled:
                continue
            if not getattr(device, "device", None) or not getattr(device.device, "unit_id", None):
                continue
            # Start AI dual stream and stop after 60 seconds (runs in background thread)
            
            def run_recording(stream_id: str, device_instance):
                try:
                    asyncio.run(
                        StreamMonitorService.start_record(
                            stream_id,
                            SurveillanceProfileService.mapping_mission_purpose_code_to_ai_model_code(profile.mission.purpose.code)
                            if analysis_enabled
                            else None,
                            enable_detection=analysis_enabled,
                            from_fe=False,
                        )
                    )
                    # video_path, analysis_path = asyncio.run(SurveillanceProfileService._record_video_with_timeout(stream_id, 180))
                    # if video_path:
                    #     device_instance.video_path = f"https://{settings.MINIO_ENDPOINT}/{settings.MINIO_STORAGE_MEDIA_BUCKET_NAME}/{video_path}"
                    #     VideoAnalysisService.create_video_analysis(device_instance, None, video_path, analysis_path, profile.created_by)
                    # if analysis_path:
                    #     device_instance.analysis_path = analysis_path
                    # if video_path or analysis_path:
                    #     device_instance.save()
                except Exception as exc:
                    logger.exception(f"Failed to start/stop AI dual stream for device {stream_id}: {exc}")
            if record_enabled:
                thread = threading.Thread(target=run_recording, args=(device.device.unit_id, device))
                thread.daemon = True
                thread.start()
                
        try:
            cancel_message ={
                "en": "Profile cancelled because assigned drones are performing other missions",
                "kr": "정찰 프로파일 취소됨 할당 드론이 다른 임무 수행 중으로 프로파일 취소됨",
                "th": "การดำเนินการล้มเหลว ยกเลิกโปรไฟล์เนื่องจากโดรนที่กำหนดกำลังปฏิบัติภารกิจอื่น",
            }
            if profile.drone_assignments.count() > 1:
                if profile.drone_assignments.filter(device__status__code="on_mission").count() > 0:
                    profile.status = SurveillanceProfileService._get_status_by_code("cancelled")
                    profile.cancel_reason = cancel_message.get(profile.created_by.language.code.lower(), cancel_message["en"])
                    profile.save(update_fields=["status", "cancel_reason", "modified_on"])
                    return
                
            headers = get_gcs_api_headers()
            response = requests.post(endpoint, json=payload, headers=headers)
            on_mission_status = DeviceStatus.objects.get(code='on_mission')
            in_process_status = SurveillanceProfileService._get_status_by_code("in_progress")
            if response.status_code in [200, 201]:
                # Chỉ set actual_start_time khi upload thành công
                profile.actual_start_time = timezone.now()
                for device in devices:
                    device.device.status = on_mission_status
                    device.device.save(update_fields=["status"])    
                profile.status = in_process_status
                profile.save(update_fields=["status", "actual_start_time", "modified_on"])
                logger.info(f"Upload profile {profile.id} to Flightbird successfully")
            else:
                logger.warning(
                    "Flightbird upload returned status %s for profile %s",
                    response.status_code,
                    profile.id,
                )
        except Exception as exc:
            logger.exception("Failed to upload profile %s to Flightbird: %s", profile.id, exc)

    @staticmethod
    @transaction.atomic
    def change_profile_drone(
        profile_id: int,
        from_device_id: int,
        to_device_id: int,
    ) -> Dict[str, Any]:
        if from_device_id == to_device_id:
            raise ValidationError("Target drone must be different from current drone")

        try:
            profile = (
                SurveillanceProfile.objects.select_related("mission")
                .prefetch_related("drone_assignments__device")
                .get(id=profile_id)
            )
        except SurveillanceProfile.DoesNotExist as exc:
            raise ValidationError("Surveillance profile not found") from exc

        assignment = profile.drone_assignments.filter(device_id=from_device_id).first()
        if assignment is None:
            raise ValidationError("Source drone is not assigned to this profile")

        if profile.drone_assignments.filter(device_id=to_device_id).exists():
            raise ValidationError("Target drone is already assigned to this profile")

        try:
            target_device = (
                Device.objects.select_related(
                    "terminal",
                    "manufacturer_information",
                    "propulsion_system",
                    "flight_performance",
                )
                .prefetch_related(
                    "propulsion_system__measurements",
                    "flight_performance__measurements",
                )
                .get(id=to_device_id)
            )
        except Device.DoesNotExist as exc:
            raise ValidationError("Target drone not found") from exc

        status_code = getattr(getattr(target_device, "status", None), "code", None)
        if status_code != "available":
            raise ValidationError("Target drone is not available")

        assignment.device = target_device
        assignment.save(update_fields=["device", "modified_on"])

        return {
            "profile_id": profile.id,
            "assignment_id": assignment.id,
            "from_device_id": from_device_id,
            "to_device_id": to_device_id,
            "device_name": target_device.name,
            "device_code": target_device.serial_number,
            "device_unit_id": target_device.unit_id,
            "model": SurveillanceProfileService._format_device_model(target_device),
        }
    @staticmethod
    def fetch_available_device_from_gcs() -> List[str]:
        FLIGHT_BIRD_URL = os.environ.get("FLIGHTBRID_URL")
        if not FLIGHT_BIRD_URL:
            raise ValidationError(
                get_message(MESSAGE_ENUM.SURVEILLANCE_AVAILABLE_DEVICES_GCS_URL_NOT_CONFIGURED)
            )

        try:
            headers = get_gcs_api_headers()
            response = requests.get(
                f"{FLIGHT_BIRD_URL}/api/drone/drones/full-battery",
                headers=headers,
                timeout=15,
            )
        except Exception as exc:
            raise ValidationError(
                get_message(MESSAGE_ENUM.SURVEILLANCE_AVAILABLE_DEVICES_GCS_FETCH_FAILED).format(
                    error=str(exc)
                )
            ) from exc

        if response.status_code != 200:
            raise ValidationError(
                get_message(MESSAGE_ENUM.SURVEILLANCE_AVAILABLE_DEVICES_GCS_FETCH_FAILED).format(
                    error=f"HTTP {response.status_code}"
                )
            )

        try:
            payload = response.json()
        except Exception as exc:
            raise ValidationError(
                get_message(MESSAGE_ENUM.SURVEILLANCE_AVAILABLE_DEVICES_GCS_FETCH_FAILED).format(
                    error=f"Invalid JSON: {exc}"
                )
            ) from exc

        drones = payload.get("drones", []) if isinstance(payload, dict) else []
        if not isinstance(drones, list):
            drones = []

        unique_ids: List[str] = []
        for drone in drones:
            if not isinstance(drone, dict):
                continue
            unique_id = drone.get("UniqueId")
            if unique_id:
                unique_ids.append(unique_id)
        return unique_ids

    @staticmethod
    def get_available_devices_for_mission(
        mission_id: int,
        start_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        
        mission = SurveillanceProfileService._get_mission(mission_id)
        # normalised_start = SurveillanceProfileService._normalise_start_time(start_time)

        limit = mission.maximum_drones or 1
        diagnostics: Dict[str, Any] = {}
        available_devices = SurveillanceProfileService._get_available_devices(
            limit,
            raise_on_empty=True,
            diagnostics=diagnostics,
        )
        device_instances_map = SurveillanceProfileService._build_device_context(
            [
                device.get("id")
                for device in available_devices
                if isinstance(device, dict)
            ]
        )
        raw_assignments, display_assignments, start_end_choices = SurveillanceProfileService._generate_default_assignments(
            mission,
            start_time,
            available_devices=available_devices,
            device_instances=device_instances_map,
            validate_duplicates=False,
            diagnostics=diagnostics,
        )
        if not display_assignments:
            raise ValidationError(
                SurveillanceProfileService._build_available_devices_failure_message(diagnostics)
            )
        else:
            SurveillanceProfileService._adjust_duplicate_assignment_times(raw_assignments, display_assignments)

        return {
            "mission_id": mission.id,
            "start_time": start_time,
            "maximum_drones": mission.maximum_drones,
            "devices": available_devices,
            "default_assignments": display_assignments,
            "start_end_points": start_end_choices,
        }

    @staticmethod
    def _build_available_devices_failure_message(diagnostics: Optional[Dict[str, Any]] = None) -> str:
        """Build a translated error message explaining why assignments are not possible."""
        diag: Dict[str, Any] = diagnostics or {}
        stage = diag.get("failure_stage")

        if stage == "imported_route_no_segments":
            return get_message(MESSAGE_ENUM.SURVEILLANCE_AVAILABLE_DEVICES_IMPORTED_ROUTE_NO_SEGMENTS)

        if stage in {"prepare_drone_candidates_empty", "no_usable_drones"}:
            devices_count = diag.get("devices_count")
            if devices_count is None:
                devices_count = diag.get("available_devices_count", 0)
            missing_instances_count = diag.get("missing_instances_count", 0)
            return get_message(MESSAGE_ENUM.SURVEILLANCE_AVAILABLE_DEVICES_NO_CANDIDATES).format(
                devices_count=devices_count or 0,
                missing_instances_count=missing_instances_count or 0,
            )

        segment_failure = diag.get("segment_failure") if isinstance(diag.get("segment_failure"), dict) else None
        if stage == "assign_segments_failed" or segment_failure:
            segment_failure = segment_failure or {}
            detail = get_message(MESSAGE_ENUM.SURVEILLANCE_AVAILABLE_DEVICES_SEGMENT_UNASSIGNABLE).format(
                segment_index=segment_failure.get("segment_index") or 1,
                distance_km=segment_failure.get("distance_km") or 0.0,
                example=segment_failure.get("example")
                or get_message(MESSAGE_ENUM.SURVEILLANCE_ESTIMATION_FAIL_UNKNOWN),
            )
            return get_message(MESSAGE_ENUM.SURVEILLANCE_AVAILABLE_DEVICES_ASSIGNMENT_FAILED).format(
                detail=detail
            )

        return get_message(MESSAGE_ENUM.SURVEILLANCE_AVAILABLE_DEVICES_ASSIGNMENT_FAILED).format(
            detail=get_message(MESSAGE_ENUM.SURVEILLANCE_ESTIMATION_FAIL_UNKNOWN)
        )

    @staticmethod
    def _delete_child_profiles(profile: SurveillanceProfile) -> None:
        for child in SurveillanceProfile.objects.filter(repeat_parent=profile):
            child.delete()

    @staticmethod
    def _calculate_estimated_end_time(start_time: datetime, mission: SurveyMission) -> Optional[datetime]:
        try:
            mission_time = mission.get_numeric_value(SurveillanceProfileService.MEASUREMENT_ESTIMATED_TIME)
        except Exception:
            mission_time = None
        if mission_time is None:
            return None
        return start_time + timezone.timedelta(minutes=int(mission_time))

    @staticmethod
    def _advance_start_time(current: datetime, repeat_code: str, original_day: Optional[int] = None) -> Optional[datetime]:
        if not repeat_code:
            return None

        normalized = repeat_code.lower()
        if normalized == "daily":
            return current + relativedelta(days=+1)
        if normalized == "weekly":
            return current + relativedelta(weeks=+1)
        if normalized == "monthly":
            next_month = current + relativedelta(months=+1)
            max_day = calendar.monthrange(next_month.year, next_month.month)[1]
            next_month_is_february = next_month.month == 2
            
            if original_day is not None:
                # Xử lý các case đặc biệt:
                # - Ngày 31: luôn là cuối tháng (28/29/30/31 tùy tháng)
                # - Ngày 30, 29: chỉ là cuối tháng khi tháng tiếp theo là tháng 2
                # - Ngày 28 trở lên: không có gì đặc biệt, dùng min(original_day, max_day)
                if original_day == 31:
                    # Ngày 31 luôn map sang cuối tháng
                    target_day = max_day
                elif original_day >= 29 and next_month_is_february:
                    # Ngày 29, 30 chỉ đặc biệt với tháng 2
                    target_day = max_day
                else:
                    # Các trường hợp khác: dùng ngày gốc hoặc cuối tháng nếu vượt quá
                    target_day = min(original_day, max_day)
            else:
                # Khi không có original_day, dùng ngày hiện tại của current
                # Áp dụng logic tương tự để đảm bảo tính nhất quán
                current_day = current.day
                if current_day == 31:
                    # Ngày 31 luôn map sang cuối tháng
                    target_day = max_day
                elif current_day >= 29 and next_month_is_february:
                    # Ngày 29, 30 chỉ đặc biệt với tháng 2
                    target_day = max_day
                else:
                    # Các trường hợp khác: dùng ngày hiện tại hoặc cuối tháng nếu vượt quá
                    target_day = min(current_day, max_day)
            
            return next_month.replace(day=target_day)

        return None

    @staticmethod
    def _get_repeat_generation_key(target: Optional[datetime], repeat_code: Optional[str]) -> Optional[str]:
        if target is None or not repeat_code:
            return None

        normalized = repeat_code.lower()
        if normalized == "daily":
            return target.strftime("%Y-%m-%d")
        if normalized == "weekly":
            iso_year, iso_week, _ = target.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        if normalized == "monthly":
            return target.strftime("%Y-%m")
        return target.strftime("%Y-%m-%d")

    @staticmethod
    def _determine_recurring_clone_status(
        source_profile: SurveillanceProfile,
        root_profile: SurveillanceProfile,
    ) -> Optional[SurveillanceStatus]:
        """Determine the status for a newly generated recurring profile."""

        priority_codes: List[str] = []

        source_status = getattr(source_profile, "status", None)
        source_code = getattr(source_status, "code", None)
        root_status = getattr(root_profile, "status", None)
        root_code = getattr(root_status, "code", None)

        if source_code in {"completed", "cancelled", "in_progress"}:
            priority_codes.append("pending_device_check")
        elif source_code in {"pending_device_check", "pending_approval"}:
            priority_codes.append(source_code)
        elif source_code:
            priority_codes.append(source_code)

        if root_code:
            priority_codes.append(root_code)

        # Ensure sensible fallbacks even when the preferred codes are missing
        priority_codes.extend(["pending_device_check", "pending_approval"])

        for code in priority_codes:
            if not code:
                continue
            status = SurveillanceStatus.objects.filter(code=code).first()
            if status:
                return status

        return source_status or root_status

    @staticmethod
    @transaction.atomic
    def _generate_recurring_profiles(
        profile: SurveillanceProfile,
        max_to_generate: Optional[int] = None,
        base_profile: Optional[SurveillanceProfile] = None,
        generate_if_start_before: Optional[datetime] = None,
        force: bool = False,
    ) -> int:
        """
        Tạo thêm các profile lặp lại dựa trên cấu hình repeat của profile gốc.

        Mỗi profile chỉ sinh ra tối đa một bản lặp tại một thời điểm. Sau khi tạo,
        metadata `repeat_has_generated_child` của profile nguồn được đánh dấu để
        tránh tạo trùng lặp; bản mới tạo sẽ được đặt `repeat_parent` trỏ ngược về
        profile nguồn để đảm bảo chuỗi A → B → C → ... được duy trì tuần tự.
        
        Sử dụng transaction.atomic và select_for_update để tránh race condition
        khi nhiều task Celery chạy song song.
        """
        # Reload với lock để tránh race condition
        # Use _base_manager for background task to avoid filter
        source_profile_id = (base_profile or profile).id
        
        # Tìm root_profile trước khi lock để tránh deadlock
        # Nếu source_profile đã được lock từ bên ngoài (process_due_recurring_profiles),
        # không lock lại để tránh nested lock trên cùng một row
        temp_source = SurveillanceProfile._base_manager.get(id=source_profile_id)
        source_metadata_temp = temp_source.metadata or {}
        if not isinstance(source_metadata_temp, dict):
            source_metadata_temp = {}
        
        root_profile: Optional[SurveillanceProfile] = None
        root_id = source_metadata_temp.get("repeat_root_id")
        if root_id:
            if root_id == source_profile_id:
                root_profile = temp_source
            else:
                root_profile = SurveillanceProfile._base_manager.filter(id=root_id).first()

        if not root_profile:
            # Nếu không có root_id trong metadata, dùng profile hiện tại làm root
            # Hoặc tìm root bằng cách traverse repeat_parent chain (đi lên đến root)
            # Use _base_manager for background task to avoid filter
            root_profile = temp_source
            visited_root: set[int] = set()
            while root_profile and root_profile.repeat_parent_id:
                if root_profile.id in visited_root:
                    break
                visited_root.add(root_profile.id)
                # Use _base_manager to get repeat_parent to avoid filter
                parent_id = root_profile.repeat_parent_id
                try:
                    parent_profile = SurveillanceProfile._base_manager.select_related("repeat_parent").get(id=parent_id)
                    root_profile = parent_profile
                except SurveillanceProfile.DoesNotExist:
                    break
        if not root_profile:
            return 0
        root_id = root_profile.id
        
        # Lock root_profile trước để tránh race condition và deadlock
        # Nếu root_id == source_profile_id, chỉ lock một lần
        # Sử dụng nowait=False để tránh deadlock nếu root_profile đã được lock từ bên ngoài
        try:
            root_profile = SurveillanceProfile._base_manager.select_for_update(nowait=False).get(id=root_id)
        except Exception as e:
            # Nếu không lock được root_profile, có thể đã bị lock bởi task khác
            logger.warning(
                "[SURVEILLANCE][REPEAT] Failed to lock root_profile %s: %s",
                root_id,
                str(e),
            )
            return 0
        
        # Nếu source_profile khác root_profile, lock source_profile sau
        # Nếu cùng một profile, dùng root_profile đã lock
        if source_profile_id == root_id:
            source_profile = root_profile
        else:
            try:
                source_profile = SurveillanceProfile._base_manager.select_for_update(nowait=False).get(id=source_profile_id)
            except Exception as e:
                # Nếu không lock được source_profile, có thể đã bị lock bởi task khác
                logger.warning(
                    "[SURVEILLANCE][REPEAT] Failed to lock source_profile %s: %s",
                    source_profile_id,
                    str(e),
                )
                return 0
        
        source_metadata = source_profile.metadata or {}
        if not isinstance(source_metadata, dict):
            source_metadata = {}

        # Mỗi profile chỉ clone 1 lần, sau đó không kiểm tra lại nữa
        # Flag này được set = True sau khi clone xong, và query sẽ filter ra những profile có flag = True
        if source_metadata.get("repeat_has_generated_child") and not force:
            return 0
        repeat_type = source_profile.repeat_type
        repeat_code = repeat_type.code if repeat_type else None
        normalized_repeat_code = repeat_code.lower() if repeat_code else None
        if not normalized_repeat_code or normalized_repeat_code in {"none", "off"}:
            return 0
        if max_to_generate is None or max_to_generate <= 0:
            max_to_generate = 1
        else:
            max_to_generate = 1

        if generate_if_start_before and timezone.is_naive(generate_if_start_before):
            generate_if_start_before = timezone.make_aware(
                generate_if_start_before,
                timezone.get_current_timezone(),
            )

        template_profile = source_profile
        status_source_profile = template_profile

        # Chỉ dùng start_time của profile hiện tại (source_profile) để check
        # Không fallback về root_profile vì mỗi profile clone phải đợi đến start_time của chính nó
        latest_start = source_profile.start_time

        if not latest_start:
            return 0

        repeat_until = status_source_profile.repeat_until_type
        until_code = repeat_until.code if repeat_until else None

        repeat_occurrences = status_source_profile.repeat_occurrences
        mission = template_profile.mission

        checklist_prefetch = Prefetch(
            "checklists",
            queryset=SurveillanceProfileChecklist._base_manager.prefetch_related("items"),
        )

        def _fetch_assignment_templates(source: Optional[SurveillanceProfile]) -> List[SurveillanceProfileDrone]:
            if not source:
                return []
            return list(
                SurveillanceProfileDrone._base_manager.filter(profile=source)
                .select_related("device", "start_waypoint", "end_waypoint")
                .prefetch_related(checklist_prefetch)
            )

        occurrences_created = 0

        # Lấy ngày gốc từ root_profile để đảm bảo monthly luôn dùng đúng ngày gốc
        original_day = None
        if normalized_repeat_code == "monthly" and root_profile.start_time:
            original_day = root_profile.start_time.day

        next_start = SurveillanceProfileService._advance_start_time(latest_start, repeat_code, original_day=original_day)
        if not next_start:
            return 0

        generation_key = SurveillanceProfileService._get_repeat_generation_key(next_start, repeat_code)
        
        # Chỉ clone khi start_time của profile hiện tại (source_profile) đã qua
        # Ví dụ: Profile A (16/11 08:00) -> qua 16/11 08:00 mới clone B (17/11 08:00)
        # Profile B (17/11 08:00) -> qua 17/11 08:00 mới clone C (18/11 08:00)
        if generate_if_start_before and latest_start > generate_if_start_before:
            return 0
        
        # Không tạo profile nếu next_start có cùng generation_key với generate_if_start_before
        # Đảm bảo không tạo duplicate trong cùng period (ngày/tuần/tháng)
        if generate_if_start_before and not force:
            next_start_key = SurveillanceProfileService._get_repeat_generation_key(next_start, repeat_code)
            generate_if_start_before_key = SurveillanceProfileService._get_repeat_generation_key(
                generate_if_start_before, repeat_code
            )
            # Chỉ skip nếu cùng generation_key (cùng ngày/tuần/tháng)
            # Nếu khác generation_key, cho phép tạo vì đây là period tiếp theo
            if next_start_key and generate_if_start_before_key and next_start_key == generate_if_start_before_key:
                logger.debug(
                    "[SURVEILLANCE][REPEAT] Skipping: next_start (%s) has same generation_key (%s) as generate_if_start_before (%s)",
                    next_start, next_start_key, generate_if_start_before
                )
                return 0
        
        # Sau khi lock root_profile, check duplicate dựa trên generation_key và start_time
        # Đảm bảo không có race condition
        root_metadata = root_profile.metadata or {}
        if not isinstance(root_metadata, dict):
            root_metadata = {}
        last_generation_key = root_metadata.get("repeat_last_generation_key")
        
        # Check duplicate theo generation_key (primary check mechanism)
        if generation_key and not force and last_generation_key == generation_key:
            logger.debug(
                "[SURVEILLANCE][REPEAT] Skipping duplicate generation_key: %s",
                generation_key
            )
            return 0
        
        # Check duplicate theo period (ngày/tuần/tháng) thay vì exact start_time
        # Đảm bảo không tạo duplicate trong cùng period
        chain_queryset_locked = SurveillanceProfile._base_manager.filter(
            Q(id=root_id) | Q(metadata__repeat_root_id=root_id)
        )
        
        # Check duplicate theo generation_key period
        if generation_key and not force:
            # Query tất cả profiles trong chain và check generation_key của chúng
            for existing_profile in chain_queryset_locked.exclude(id=source_profile.id):
                if not existing_profile.start_time:
                    continue
                existing_generation_key = SurveillanceProfileService._get_repeat_generation_key(
                    existing_profile.start_time, repeat_code
                )
                if existing_generation_key == generation_key:
                    logger.debug(
                        "[SURVEILLANCE][REPEAT] Skipping: already exists profile with generation_key %s (start_time=%s)",
                        generation_key, existing_profile.start_time
                    )
                    return 0
        
        # Check duplicate với exact start_time (backup check)
        if chain_queryset_locked.filter(start_time=next_start).exists():
            logger.debug(
                "[SURVEILLANCE][REPEAT] Skipping: already exists profile with exact start_time %s",
                next_start
            )
            return 0
        existing_chain_count = chain_queryset_locked.count()
        existing_children_count = max(existing_chain_count - 1, 0)
        sequence_number = existing_children_count + 1

        repeat_until_date = status_source_profile.repeat_until_date or root_profile.repeat_until_date
        if until_code in ("on_date", "date") and repeat_until_date and next_start.date() > repeat_until_date:
            return 0

        if repeat_occurrences:
            max_children_allowed = max(int(repeat_occurrences), 0)
            if existing_children_count >= max_children_allowed and not force:
                return 0


        clone_status = SurveillanceProfileService._determine_recurring_clone_status(
            status_source_profile,
            root_profile,
        )

        metadata_source = template_profile.metadata or {}
        if isinstance(metadata_source, dict):
            clone_metadata = copy.deepcopy(metadata_source)
        else:
            clone_metadata = {}
        clone_metadata.pop("scheduled_task_ids", None)
        clone_metadata.pop("repeat_has_generated_child", None)
        clone_metadata.pop("repeat_last_generated_child_id", None)
        clone_metadata.pop("repeat_last_generated_at", None)
        clone_metadata.pop("repeat_last_generation_key", None)
        # Xóa các field cancellation không nên được copy từ template profile
        clone_metadata.pop("cancelled_at", None)
        clone_metadata.pop("cancel_reason", None)
        clone_metadata.pop("overdue_auto_cancelled", None)
        clone_metadata.pop("overdue_check_processed_at", None)
        clone_metadata.pop("overdue_check_reason_language", None)
        clone_metadata.pop("auto_cancelled_type", None)
        clone_metadata.pop("overdue_hours_config", None)
        clone_metadata.pop("overdue_check_eta", None)
        clone_metadata.pop("overdue_check_task_id", None)
        clone_metadata.pop("overdue_check_scheduled_at", None)
        clone_metadata.pop("overdue_check_skipped_status", None)
        clone_metadata.pop("overdue_check_skipped_reason", None)
        clone_metadata["generated_from_profile_id"] = template_profile.id
        clone_metadata["repeat_root_id"] = root_id
        clone_metadata["repeat_has_generated_child"] = False
        clone_metadata["repeat_sequence_number"] = sequence_number

        operator = (
            getattr(template_profile, "operator", None)
            or getattr(root_profile, "operator", None)
        )

        approval_operator = (
            getattr(template_profile, "approved_by", None)
            or getattr(root_profile, "approved_by", None)
        )

        base_name = root_metadata.get("repeat_base_name")
        if not base_name:
            base_name = root_profile.name
            root_metadata["repeat_base_name"] = base_name

        clone_metadata["repeat_base_name"] = base_name

        # Use _base_manager for background task to avoid filter
        repeat_metadata_value = (
            copy.deepcopy(template_profile.repeat_metadata)
            if template_profile.repeat_metadata is not None
            else None
        )

        clone = SurveillanceProfile(
            name=f"{base_name} ({sequence_number})",
            mission=mission,
            status=clone_status,
            operator=operator,
            start_time=next_start,
            estimated_end_time=SurveillanceProfileService._calculate_estimated_end_time(next_start, mission)
            if mission
            else template_profile.estimated_end_time,
            actual_end_time=None,
            repeat_type=template_profile.repeat_type,
            repeat_until_type=template_profile.repeat_until_type,
            repeat_until_date=template_profile.repeat_until_date,
            repeat_occurrences=template_profile.repeat_occurrences,
            repeat_metadata=repeat_metadata_value,
            color_code=template_profile.color_code,
            note=template_profile.note,
            metadata=clone_metadata,
            repeat_parent=template_profile,
            created_by=template_profile.created_by or root_profile.created_by,
            modified_by=template_profile.modified_by or root_profile.modified_by,
            group=template_profile.group or root_profile.group,
            approved_by=approval_operator,
            cancelled_by=None,
            
        )
        clone.save()

        approval_operator = approval_operator
        approval_entry = {
            "approved_at": timezone.now().isoformat() if approval_operator else None,
            "approved_by_id": approval_operator.id if approval_operator else None,
            "approved_by_username": approval_operator.username if approval_operator else None,
            "note": None,
        }
        clone_metadata = clone.metadata or {}
        if not isinstance(clone_metadata, dict):
            clone_metadata = {}
        approval_history = clone_metadata.setdefault("approval_history", [])
        approval_history.append(approval_entry)
        clone_metadata["last_approved_by_id"] = approval_entry["approved_by_id"]
        clone_metadata["last_approved_at"] = approval_entry["approved_at"]
        clone_metadata.pop("approval_note", None)
        clone.metadata = clone_metadata
        clone.save(update_fields=["metadata", "modified_on"])

        measurement_sources: List[SurveillanceProfile] = [
            template_profile,
            root_profile,
        ]
        distance_value: Optional[float] = None
        for measurement_source in measurement_sources:
            if not measurement_source:
                continue
            distance_value = SurveillanceProfileService._get_profile_metric(
                measurement_source,
                SurveillanceProfileService.MEASUREMENT_TOTAL_DISTANCE,
                float,
            )
            if distance_value is not None:
                break

        time_value: Optional[int] = None
        for measurement_source in measurement_sources:
            if not measurement_source:
                continue
            time_value = SurveillanceProfileService._get_profile_metric(
                measurement_source,
                SurveillanceProfileService.MEASUREMENT_ESTIMATED_TIME,
                int,
            )
            if time_value is not None:
                break

        SurveillanceProfileService._sync_profile_measurements(
            clone,
            total_distance_km=distance_value,
            total_estimated_time_minutes=time_value,
        )

        template_assignments = _fetch_assignment_templates(template_profile)

        assignment_payload: List[Dict[str, Any]] = []
        for assignment in template_assignments:
            assignment_payload.append(
                {
                    "order": assignment.order,
                    "device_id": assignment.device_id,
                    "scheduled_start_time": next_start,
                    "start_waypoint_id": assignment.start_waypoint_id,
                    "end_waypoint_id": assignment.end_waypoint_id,
                    "log_collection": assignment.log_collection,
                    "video_recording": assignment.video_recording,
                    "video_analysis": assignment.video_analysis,
                    "note": assignment.note,
                }
            )

        SurveillanceProfileService._validate_duplicate_assignments(assignment_payload)
        SurveillanceProfileService._upsert_assignments(clone, mission, assignment_payload)

        clone_assignments = list(
            SurveillanceProfileDrone._base_manager.filter(profile=clone)
            .select_related("device", "start_waypoint", "end_waypoint")
        )
        clone_assignment_map: Dict[
            Tuple[Optional[int], Optional[int], Optional[int], Optional[int]], SurveillanceProfileDrone
        ] = {
            (
                assignment.order,
                assignment.device_id,
                assignment.start_waypoint_id,
                assignment.end_waypoint_id,
            ): assignment
            for assignment in clone_assignments
        }

        for source_assignment in template_assignments:
            key = (
                source_assignment.order,
                source_assignment.device_id,
                source_assignment.start_waypoint_id,
                source_assignment.end_waypoint_id,
            )
            clone_assignment = clone_assignment_map.get(key)
            if not clone_assignment:
                continue

            for source_checklist in source_assignment.checklists.all():
                clone_checklist = (
                    SurveillanceProfileChecklist.objects.filter(
                        profile=clone,
                        profile_drone=clone_assignment,
                    ).first()
                )

                if not clone_checklist:
                    clone_checklist = SurveillanceProfileChecklist.objects.create(
                        profile=clone,
                        profile_drone=clone_assignment,
                        checked_by=source_checklist.checked_by,
                        auto_check_data=source_checklist.auto_check_data,
                        metadata=source_checklist.metadata,
                    )
                else:
                    clone_checklist.checked_by = source_checklist.checked_by
                    clone_checklist.auto_check_data = source_checklist.auto_check_data
                    clone_checklist.metadata = source_checklist.metadata
                    clone_checklist.save(
                        update_fields=[
                            "checked_by",
                            "auto_check_data",
                            "metadata",
                            "modified_on",
                        ]
                    )

                clone_checklist.items.all().delete()
                items_to_create = [
                    SurveillanceProfileChecklistItem(
                        checklist=clone_checklist,
                        checklist_setting=item.checklist_setting,
                        item_name_snapshot=item.item_name_snapshot,
                        category_code_snapshot=item.category_code_snapshot,
                    )
                    for item in source_checklist.items.all()
                ]
                if items_to_create:
                    SurveillanceProfileChecklistItem.objects.bulk_create(items_to_create)

        occurrences_created = 1

        # Đánh dấu profile này đã clone xong, không kiểm tra lại nữa
        # Flag này đảm bảo mỗi profile chỉ clone đúng 1 lần
        source_metadata["repeat_has_generated_child"] = True
        source_metadata["repeat_last_generated_child_id"] = clone.id
        source_metadata["repeat_last_generated_at"] = timezone.now().isoformat()
        source_metadata["repeat_root_id"] = root_id
        source_metadata["repeat_last_generated_sequence"] = sequence_number
        source_metadata["repeat_base_name"] = base_name
        if generation_key:
            source_metadata["repeat_last_generation_key"] = generation_key
        source_profile.metadata = source_metadata
        source_profile.save(update_fields=["metadata", "modified_on"])

        root_metadata = root_profile.metadata or {}
        if not isinstance(root_metadata, dict):
            root_metadata = {}
        root_metadata.update(
            {
                "repeat_last_generated_at": timezone.now().isoformat(),
                "repeat_occurrences_generated": existing_children_count + occurrences_created,
                "repeat_root_id": root_id,
                "repeat_last_generated_child_id": clone.id,
                "repeat_last_sequence_number": sequence_number,
                "repeat_base_name": base_name,
            }
        )
        if generation_key:
            root_metadata["repeat_last_generation_key"] = generation_key
        root_metadata["repeat_has_generated_child"] = True
        root_profile.metadata = root_metadata
        root_profile.save(update_fields=["metadata", "modified_on"])

        return occurrences_created

    @staticmethod
    def process_due_recurring_profiles(
        now: Optional[datetime] = None,
        *,
        chunk_size: int = 200,
    ) -> int:
        """Generate recurring profiles whose next start time is due."""

        now = now or timezone.now()
        if timezone.is_naive(now):
            now = timezone.make_aware(now, timezone.get_current_timezone())

        total_created = 0

        # Query những profile chưa clone (repeat_has_generated_child = null hoặc False)
        # Query cả root profiles và child profiles để tiếp tục tạo profile tiếp theo
        # Sau khi clone xong, flag được set = True, profile đó sẽ không được query ra nữa
        # Logic: Root profile tạo child đầu tiên, sau đó child profile tiếp tục tạo child tiếp theo
        base_queryset = (
            SurveillanceProfile._base_manager.select_related("repeat_type", "repeat_until_type", "status", "repeat_parent")
            .filter(repeat_type__isnull=False)
            .filter(start_time__isnull=False)
            .filter(
                Q(metadata__repeat_has_generated_child__isnull=True)
                | Q(metadata__repeat_has_generated_child=False)
            )
            .annotate(repeat_type_code_lower=Lower("repeat_type__code"))
            .exclude(repeat_type_code_lower__in=["none", "off"])
            .order_by("start_time", "id")
            .exclude(status__code__in=["rejected"])
        )

        for profile in base_queryset.iterator(chunk_size=chunk_size):
            # Skip nếu profile có start_time trong tương lai và là child profile
            # Root profile có thể có start_time trong tương lai và vẫn cần được xử lý
            if profile.start_time and profile.start_time > now and profile.repeat_parent_id is not None:
                continue

            # Wrap mỗi profile processing trong transaction riêng để có thể dùng select_for_update
            try:
                with transaction.atomic():
                    # Lock profile row để tránh race condition khi nhiều task chạy song song
                    # Dùng _base_manager để nhất quán với query và tránh custom filter
                    locked_profile = SurveillanceProfile._base_manager.select_for_update(nowait=True).get(id=profile.id)
                    
                    # Double-check flag sau khi lock
                    locked_metadata = locked_profile.metadata or {}
                    if not isinstance(locked_metadata, dict):
                        locked_metadata = {}
                    if locked_metadata.get("repeat_has_generated_child"):
                        continue
                    
                    # _generate_recurring_profiles đã có @transaction.atomic nhưng sẽ dùng transaction hiện tại
                    created = SurveillanceProfileService._generate_recurring_profiles(
                        locked_profile,
                        max_to_generate=1,
                        base_profile=locked_profile,
                        generate_if_start_before=now,
                    )
                    if created:
                        total_created += created
            except SurveillanceProfile.DoesNotExist:
                # Profile đã bị xóa, skip
                continue
            except Exception as e:
                # Nếu lock failed (nowait=True sẽ raise nếu row đã bị lock), skip profile này
                # Log để debug nhưng không fail toàn bộ process
                logger.warning(
                    "[SURVEILLANCE][REPEAT] Failed to process profile %s: %s",
                    profile.id,
                    str(e),
                )
                continue

        return total_created

    @staticmethod
    def _handle_profile_completion(profile: SurveillanceProfile, previous_status_code: Optional[str]) -> None:
        if not profile.status or profile.status.code != "completed":
            return
        if previous_status_code == "completed":
            return

        completion_time = timezone.now()

        SurveillanceProfileAutomationService.clear_auto_launch(
            profile,
            timestamp=completion_time,
            reason="completed",
        )


    def _regenerate_recurring_profiles(profile: SurveillanceProfile, max_to_generate: Optional[int] = None) -> int:
        return SurveillanceProfileService._generate_recurring_profiles(
            profile,
            max_to_generate=max_to_generate,
            force=True,
        )

    @staticmethod
    def _resolve_waypoint(assignment_data: Dict[str, Any], key: str, mission: SurveyMission) -> Optional[MissionWaypoint]:
        waypoint_id = assignment_data.get(key)
        if waypoint_id is None:
            return None

        try:
            waypoint = mission.waypoints.get(id=waypoint_id)
        except MissionWaypoint.DoesNotExist as exc:
            raise ValidationError(f"Mission waypoint with id {waypoint_id} not found or does not belong to mission") from exc
        return waypoint

    @staticmethod
    def _prepare_assignment(profile: SurveillanceProfile, mission: SurveyMission, payload: Dict[str, Any], default_order: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "profile": profile,
            "order": payload.get("order") or default_order,
            "scheduled_start_time": payload.get("scheduled_start_time"),
            "log_collection": payload.get(
                "log_collection",
                mission.log_collection if mission and mission.log_collection is not None else True,
            ),
            "video_recording": payload.get(
                "video_recording",
                mission.video_recording if mission and mission.video_recording is not None else True,
            ),
            "video_analysis": payload.get(
                "video_analysis",
                mission.video_analysis if mission and mission.video_analysis is not None else True,
            ),
            "note": payload.get("note"),
        }

        device_id = payload.get("device_id")
        if device_id:
            try:
                Device.objects.get(id=device_id)
            except Device.DoesNotExist as exc:
                raise ValidationError(f"Device with id {device_id} not found") from exc
            result["device_id"] = device_id
        else:
            result["device_id"] = None

        start_waypoint = SurveillanceProfileService._resolve_waypoint(payload, "start_waypoint_id", mission)
        end_waypoint = SurveillanceProfileService._resolve_waypoint(payload, "end_waypoint_id", mission)

        result["start_waypoint"] = start_waypoint
        result["end_waypoint"] = end_waypoint
        result["waiting_coordinates"] = payload.get("waiting_coordinates")
        return result

    @staticmethod
    def _upsert_assignments(profile: SurveillanceProfile, mission: SurveyMission, assignments: Optional[Iterable[Dict[str, Any]]]) -> None:
        if assignments is None:
            return

        existing_map: Dict[int, SurveillanceProfileDrone] = {
            assignment.id: assignment for assignment in profile.drone_assignments.all()
        }
        keep_ids: set[int] = set()

        for default_order, payload in enumerate(assignments, start=1):
            assignment_id = payload.get("id")
            prepared = SurveillanceProfileService._prepare_assignment(profile, mission, payload, default_order)

            if assignment_id:
                assignment = existing_map.get(assignment_id)
                if not assignment:
                    raise ValidationError(f"Drone assignment with id {assignment_id} not found")

                for field, value in prepared.items():
                    setattr(assignment, field, value)
                assignment.save()
                keep_ids.add(assignment.id)
            else:
                assignment = SurveillanceProfileDrone.objects.create(**prepared)
                keep_ids.add(assignment.id)

            # Sync assignment measurements (estimated/actual) from payload metadata.
            # - estimated_distance: use polyline distance along route_path (not straight line)
            # - estimated_time: use estimated_time_minutes from flight estimation (if any)
            metadata = payload.get("metadata") or {}
            try:
                # 1) Prefer explicit fields provided in payload (per-drone overrides)
                payload_estimated_distance_km = SurveillanceProfileService._safe_number(
                    payload.get("estimated_distance_km"), float
                )
                payload_estimated_time_minutes = SurveillanceProfileService._safe_number(
                    payload.get("estimated_time_minutes"), float
                )

                path_distance_km = SurveillanceProfileService._safe_number(
                    metadata.get("path_distance_km"), float
                )
                total_distance_km = SurveillanceProfileService._safe_number(
                    metadata.get("distance_km"), float
                )
                estimated_time_minutes = SurveillanceProfileService._safe_number(
                    metadata.get("estimated_time_minutes"), float
                )

                # 2) If metadata doesn't include path_distance_km, compute from per-drone route_path polyline
                if path_distance_km is None:
                    route_path = metadata.get("route_path") or []
                    if isinstance(route_path, list) and len(route_path) >= 2:
                        computed_km = 0.0
                        prev_lat = prev_lon = None
                        for pt in route_path:
                            if not isinstance(pt, dict):
                                continue
                            lat = SurveillanceProfileService._safe_number(pt.get("latitude") or pt.get("lat"), float)
                            lon = SurveillanceProfileService._safe_number(pt.get("longitude") or pt.get("lon"), float)
                            if lat is None or lon is None:
                                continue
                            if prev_lat is not None and prev_lon is not None:
                                try:
                                    computed_km += geodesic((prev_lat, prev_lon), (lat, lon)).kilometers
                                except (ValueError, TypeError):
                                    pass
                            prev_lat, prev_lon = lat, lon
                        if computed_km > 0:
                            path_distance_km = computed_km

                # 2b) If still missing (payload doesn't include metadata), compute from mission flight path
                if path_distance_km is None and payload_estimated_distance_km is None:
                    computed = SurveillanceProfileService._compute_assignment_distance_km_from_mission(
                        mission,
                        prepared.get("start_waypoint"),
                        prepared.get("end_waypoint"),
                    )
                    if computed is not None:
                        path_distance_km = computed

                # 3) Prefer polyline distance inside mission (path_distance_km). Fallback to distance_km if provided.
                effective_distance_km = (
                    payload_estimated_distance_km
                    if payload_estimated_distance_km is not None
                    else path_distance_km
                    if path_distance_km is not None
                    else total_distance_km
                )
                if effective_distance_km is not None:
                    assignment.set_measurement(
                        "estimated_distance", f"{round(float(effective_distance_km), 3)} km"
                    )

                # 4) estimated time: prefer payload override, else metadata, else flight_estimation duration
                if payload_estimated_time_minutes is not None:
                    assignment.set_measurement(
                        "estimated_time", f"{round(float(payload_estimated_time_minutes), 2)} mins"
                    )
                else:
                    if estimated_time_minutes is None:
                        estimation = metadata.get("flight_estimation") or {}
                        duration_s = SurveillanceProfileService._safe_number(
                            estimation.get("estimated_duration_s"), float
                        )
                        if duration_s is not None:
                            estimated_time_minutes = duration_s / 60.0
                    if estimated_time_minutes is None and effective_distance_km is not None:
                        cruise_speed_ms = SurveillanceProfileService._safe_number(
                            mission.get_numeric_value("cruise_speed"), float
                        )
                        if cruise_speed_ms is None or cruise_speed_ms <= 0:
                            cruise_speed_ms = SurveillanceProfileService._safe_number(get_waypoint_speed(), float)
                        if cruise_speed_ms and cruise_speed_ms > 0:
                            estimated_time_minutes = (float(effective_distance_km) * 1000.0) / float(cruise_speed_ms) / 60.0
                    if estimated_time_minutes is not None:
                        assignment.set_measurement(
                            "estimated_time", f"{round(float(estimated_time_minutes), 2)} mins"
                        )
            except Exception as exc:
                logger.warning(
                    "Failed to sync measurements for SurveillanceProfileDrone %s: %s",
                    getattr(assignment, "id", None),
                    exc,
                )

        if existing_map:
            to_delete = set(existing_map.keys()) - keep_ids
            if to_delete:
                SurveillanceProfileDrone.objects.filter(id__in=to_delete).delete()

        profile.device_count = profile.drone_assignments.count()
        profile.save(update_fields=["device_count", "modified_on"])

    @staticmethod
    def _apply_profile_updates(profile: SurveillanceProfile, data: Dict[str, Any], mission: Optional[SurveyMission] = None) -> None:
        if "mission" in data and data["mission"] is not None:
            profile.mission = data["mission"]

        for field in [
            "name",
            "start_time",
            "estimated_end_time",
            "actual_end_time",
            "repeat_type",
            "repeat_until_type",
            "repeat_until_date",
            "repeat_occurrences",
            "repeat_metadata",
            "color_code",
            "note",
            "metadata",
        ]:
            if field in data:
                setattr(profile, field, data[field])

        if "status" in data:
            profile.status = data["status"]
        if "operator_id" in data:
            profile.operator_id = data["operator_id"]
        if "repeat_parent" in data:
            profile.repeat_parent = data["repeat_parent"]

        if not profile.estimated_end_time:
            mission_ref = mission or profile.mission
            if mission_ref:
                try:
                    mission_time_value = mission_ref.get_numeric_value(
                        SurveillanceProfileService.MEASUREMENT_ESTIMATED_TIME
                    )
                except Exception:
                    mission_time_value = None
                if mission_time_value:
                    profile.estimated_end_time = profile.start_time + timezone.timedelta(
                        minutes=int(mission_time_value)
                    )

        profile.save()

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def create(data: Dict[str, Any]) -> Tuple[bool, SurveillanceProfile]:
        try:
            assignments = data.pop("drones", None)
            status_id = data.pop("status_id", None)
            mission_id = data.pop("mission_id")
            operator_id = data.pop("operator_id", None)
            repeat_parent_id = data.pop("repeat_parent_id", None)
            repeat_type_id = data.pop("repeat_type_id", None)
            repeat_until_type_id = data.pop("repeat_until_type_id", None)
            takeoff_altitude = data.pop("takeoff_altitude", None)
            altitude_separation = data.pop("altitude_separation", None)
            total_distance_override = SurveillanceProfileService._safe_number(
                data.pop("total_distance_km", None), float
            )
            total_time_override = SurveillanceProfileService._safe_number(
                data.pop("total_estimated_time_minutes", None), int
            )

            mission = SurveillanceProfileService._get_mission(mission_id)
            status = SurveillanceProfileService._get_status_by_id(status_id) or SurveillanceProfileService._get_default_status()

            repeat_type = SurveillanceProfileService._get_repeat_type(repeat_type_id) or SurveillanceProfileService._get_default_repeat_type()
            repeat_until_type = (
                SurveillanceProfileService._get_repeat_until_type(repeat_until_type_id)
                or SurveillanceProfileService._get_default_repeat_until_type()
            )

            # Convert repeat_until_date từ UTC datetime string sang date trong timezone hệ thống
            if "repeat_until_date" in data and data["repeat_until_date"] is not None:
                data["repeat_until_date"] = SurveillanceProfileService._convert_utc_to_system_timezone_date(data["repeat_until_date"])

            SurveillanceProfileService._validate_repeat_config(
                repeat_type,
                repeat_until_type,
                data.get("repeat_until_date"),
                data.get("repeat_occurrences"),
            )

            data["start_time"] = SurveillanceProfileService._normalise_start_time(data.get("start_time"))

            if not assignments:
                assignments, _, _ = SurveillanceProfileService._generate_default_assignments(
                    mission,
                    data["start_time"],
                )

            SurveillanceProfileService._validate_duplicate_assignments(assignments)

            data["color_code"] = SurveillanceProfileService._normalise_color(data.get("color_code")) or "#1D9BE2"

            assignment_distance, assignment_time = (
                SurveillanceProfileService._calculate_assignment_totals(assignments)
                if assignments
                else (None, None)
            )

            mission_distance_default = SurveillanceProfileService._get_mission_metric(
                mission,
                SurveillanceProfileService.MEASUREMENT_TOTAL_DISTANCE,
                float,
            )
            mission_time_default = SurveillanceProfileService._get_mission_metric(
                mission,
                SurveillanceProfileService.MEASUREMENT_ESTIMATED_TIME,
                int,
            )

            profile_distance = (
                total_distance_override
                if total_distance_override is not None
                else assignment_distance
                if assignment_distance is not None
                else mission_distance_default
            )
            profile_time = (
                total_time_override
                if total_time_override is not None
                else assignment_time
                if assignment_time is not None
                else mission_time_default
            )

            if not data.get("estimated_end_time") and profile_time is not None:
                data["estimated_end_time"] = data["start_time"] + timezone.timedelta(
                    minutes=int(profile_time)
                )

            profile = SurveillanceProfile(
                mission=mission,
                status=status,
                repeat_type=repeat_type,
                repeat_until_type=repeat_until_type,
                **{k: v for k, v in data.items() if k not in {"repeat_parent", "repeat_parent_id"}},
            )

            if operator_id:
                profile.operator_id = operator_id
            if repeat_parent_id:
                profile.repeat_parent_id = repeat_parent_id
            
            profile.save()
            if takeoff_altitude:
                profile.set_measurement('takeoff_altitude', f"{takeoff_altitude} m")
            if altitude_separation:
                profile.set_measurement('altitude_separation', f"{altitude_separation} m")
            profile.save()
            SurveillanceProfileService._sync_profile_measurements(
                profile,
                total_distance_km=profile_distance,
                total_estimated_time_minutes=profile_time,
            )

            SurveillanceProfileService._upsert_assignments(profile, mission, assignments)

            logger.info("Created surveillance profile %s", profile.code)
            return True, profile
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("Error creating surveillance profile: %s", exc)
            raise ValidationError(str(exc)) from exc

    @staticmethod
    @transaction.atomic
    def mark_drone_flight_time(
        *,
        drone_unit_id: str,
        start_time: datetime,
        end_time: datetime,
        profile_id: Optional[int] = None,
    ) -> Tuple[bool, Any]:
        """
        Find the most relevant profile assignment for a drone (by Device.unit_id) and record flight_time.

        - If profile_id is provided, we will prefer the assignment within that profile (regardless of status).
        - Otherwise, we fall back to the currently running assignment (profile status = in_progress).
        """
        logger.info(f"🔍 [MARK_DRONE_FLIGHT_TIME] ===== START =====")
        logger.info(f"🔍 [MARK_DRONE_FLIGHT_TIME] drone_unit_id={drone_unit_id}, start_time={start_time}, end_time={end_time}, profile_id={profile_id}")
        if not drone_unit_id:
            raise ValidationError("drone_unit_id is required")
        if start_time is None or end_time is None:
            raise ValidationError("start_time and end_time are required")
        if end_time <= start_time:
            raise ValidationError("end_time must be greater than start_time")
        if profile_id is not None and int(profile_id) <= 0:
            raise ValidationError("profile_id must be a positive integer")

        # Find the most relevant assignment for this drone.
        qs = SurveillanceProfileDrone._base_manager.select_related("profile", "profile__status", "device").filter(
            device__unit_id=drone_unit_id
        )

        if profile_id is not None:
            assignment = qs.filter(profile_id=int(profile_id)).order_by("-id").first()
            if assignment is None:
                return False, "No profile assignment found for this drone and profile"
        else:
            qs_processing = qs.filter(profile__status__code="in_progress")
            assignment = qs_processing.order_by("-profile__start_time", "-id").first()
        if assignment is None:
            return False, "No running profile assignment found for this drone"
        logger.info(f"🔍 [MARK_DRONE_FLIGHT_TIME] Assignment found: {assignment.id}")
        flight_minutes = (end_time - start_time).total_seconds() / 60.0
        assignment.set_measurement("flight_time", f"{round(flight_minutes, 2)} mins")
        logger.info(f"🔍 [MARK_DRONE_FLIGHT_TIME] Flight time: {flight_minutes} mins")
        try:
            record = (
                StreamMonitorRecord._base_manager.filter(stream_id=drone_unit_id, status="running")
                .order_by("-created_at", "-id")
                .first()
            )
            if record:
                user = assignment.profile.operator if assignment.profile else None
                enable_detection = assignment.video_analysis
                logger.info(f"🔍 [MARK_DRONE_FLIGHT_TIME] Enable detection:{assignment.video_analysis} {enable_detection} with assignment {assignment.id}")
                mission = getattr(assignment.profile, "mission", None) if assignment.profile else None
                group_id = getattr(mission, "group_id", None)
                object_path = async_to_sync(StreamMonitorService.stop_record)(
                    drone_unit_id,
                    str(record.id),
                    user=user,
                    enable_detection=enable_detection,
                    group_id=group_id,
                    # Ensure analysis_path is persisted deterministically to the assignment we just marked.
                    profile_drone_id=assignment.id,
                )
                if object_path:
                    # Persist video_path via centralized media service (record-only mode)
                    SurveillanceProfileMediaService.save_recording_result_for_profile_drone(
                        assignment.id, object_path
                    )
            else:
                logger.warning("No running StreamMonitorRecord found for drone_unit_id=%s", drone_unit_id)
        except Exception as exc:
            logger.exception("Failed to stop record for drone_unit_id=%s: %s", drone_unit_id, exc)

        return True, assignment

    @staticmethod
    @transaction.atomic
    def update(profile_id: int, data: Dict[str, Any]) -> Tuple[bool, SurveillanceProfile]:
        try:
            profile = SurveillanceProfile.objects.select_for_update().get(id=profile_id)
            previous_status_code = profile.status.code if profile.status else None
            previous_start_time = profile.start_time

            assignments = data.pop("drones", None)
            status_id = data.pop("status_id", None)
            mission_id = data.pop("mission_id", None)
            operator_id = data.pop("operator_id", None)
            repeat_parent_id = data.pop("repeat_parent_id", None)
            repeat_type_id = data.pop("repeat_type_id", None)
            repeat_until_type_id = data.pop("repeat_until_type_id", None)
            UNSET = object()
            total_distance_token = data.pop("total_distance_km", UNSET)
            total_time_token = data.pop("total_estimated_time_minutes", UNSET)
            estimated_end_provided = "estimated_end_time" in data

            if mission_id:
                mission = SurveillanceProfileService._get_mission(mission_id)
                data["mission"] = mission
            else:
                mission = profile.mission

            if "start_time" in data and data["start_time"] is not None:
                data["start_time"] = SurveillanceProfileService._normalise_start_time(data["start_time"])

            if status_id is not None:
                data["status"] = SurveillanceProfileService._get_status_by_id(status_id)

            if operator_id is not None:
                data["operator_id"] = operator_id

            if repeat_parent_id is not None:
                data["repeat_parent"] = SurveillanceProfile.objects.filter(id=repeat_parent_id).first()

            if repeat_type_id is not None:
                data["repeat_type"] = SurveillanceProfileService._get_repeat_type(repeat_type_id)
                if data["repeat_type"] is None:
                    data["repeat_type"] = SurveillanceProfileService._get_default_repeat_type()

            if repeat_until_type_id is not None:
                data["repeat_until_type"] = SurveillanceProfileService._get_repeat_until_type(repeat_until_type_id)
                if data["repeat_until_type"] is None:
                    data["repeat_until_type"] = SurveillanceProfileService._get_default_repeat_until_type()

            if "color_code" in data:
                data["color_code"] = SurveillanceProfileService._normalise_color(data.get("color_code"))

            # Convert repeat_until_date từ UTC datetime string sang date trong timezone hệ thống
            if "repeat_until_date" in data and data["repeat_until_date"] is not None:
                data["repeat_until_date"] = SurveillanceProfileService._convert_utc_to_system_timezone_date(data["repeat_until_date"])

            repeat_type_obj = data.get("repeat_type", profile.repeat_type)
            repeat_until_type_obj = data.get("repeat_until_type", profile.repeat_until_type)
            SurveillanceProfileService._validate_repeat_config(
                repeat_type_obj,
                repeat_until_type_obj,
                data.get("repeat_until_date", profile.repeat_until_date),
                data.get("repeat_occurrences", profile.repeat_occurrences),
            )

            SurveillanceProfileService._apply_profile_updates(profile, data, mission)

            mission_changed = mission_id is not None
            assignment_distance, assignment_time = (
                SurveillanceProfileService._calculate_assignment_totals(assignments)
                if assignments is not None
                else (None, None)
            )

            update_distance = (
                total_distance_token is not UNSET
                or mission_changed
                or assignment_distance is not None
            )
            update_time = (
                total_time_token is not UNSET
                or mission_changed
                or assignment_time is not None
            )

            if total_distance_token is not UNSET:
                profile_distance = SurveillanceProfileService._safe_number(total_distance_token, float)
            elif assignment_distance is not None:
                profile_distance = assignment_distance
            elif mission_changed:
                profile_distance = SurveillanceProfileService._get_mission_metric(
                    mission,
                    SurveillanceProfileService.MEASUREMENT_TOTAL_DISTANCE,
                    float,
                )
            else:
                profile_distance = None

            if total_time_token is not UNSET:
                profile_time = SurveillanceProfileService._safe_number(total_time_token, int)
            elif assignment_time is not None:
                profile_time = assignment_time
            elif mission_changed:
                profile_time = SurveillanceProfileService._get_mission_metric(
                    mission,
                    SurveillanceProfileService.MEASUREMENT_ESTIMATED_TIME,
                    int,
                )
            else:
                profile_time = None

            if profile_distance is None:
                update_distance = False
            if profile_time is None:
                update_time = False

            if not estimated_end_provided and profile_time is not None:
                profile.estimated_end_time = profile.start_time + timezone.timedelta(minutes=int(profile_time))
                profile.save(update_fields=["estimated_end_time", "modified_on"])

            if update_distance or update_time:
                SurveillanceProfileService._sync_profile_measurements(
                    profile,
                    total_distance_km=profile_distance,
                    total_estimated_time_minutes=profile_time,
                    apply_distance=update_distance,
                    apply_time=update_time,
                )

            if assignments is not None:
                SurveillanceProfileService._validate_duplicate_assignments(assignments)
                SurveillanceProfileService._upsert_assignments(profile, mission, assignments)

            SurveillanceProfileService._handle_profile_completion(profile, previous_status_code)

            def _normalise_dt(value: Optional[datetime]) -> Optional[datetime]:
                if not value:
                    return None
                if timezone.is_naive(value):
                    return timezone.make_aware(value, timezone.get_current_timezone())
                return timezone.localtime(value, timezone.get_current_timezone())

            if _normalise_dt(previous_start_time) != _normalise_dt(profile.start_time):
                SurveillanceProfileAutomationService.refresh_start_time_snapshot(
                    profile=profile,
                    timestamp=timezone.now(),
                )


            logger.info("Updated surveillance profile %s", profile.code)
            return True, profile
        except SurveillanceProfile.DoesNotExist as exc:
            raise ValidationError(f"Profile with id {profile_id} not found") from exc
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("Error updating surveillance profile: %s", exc)
            raise ValidationError(str(exc)) from exc

    @staticmethod
    @transaction.atomic
    def complete_device_check(
        profile_id: int,
        drone_checks: List[Dict[str, Any]],
        checked_by,
        not_yet: Optional[bool] = None,
    ) -> Tuple[bool, SurveillanceProfile]:
        if not drone_checks:
            raise ValidationError("At least one drone check entry is required.")

        try:
            profile = (
                SurveillanceProfile.objects
                .select_related("status")
                .prefetch_related(
                    Prefetch(
                        "drone_assignments",
                        queryset=SurveillanceProfileService._drone_prefetch_queryset(),
                    )
                )
                .get(id=profile_id)
            )
        except SurveillanceProfile.DoesNotExist as exc:
            raise ValidationError(f"Profile with id {profile_id} not found") from exc

        current_status_code = profile.status.code if profile.status else None
        allowed_statuses = {"pending_device_check", "approved", "in_progress"}
        if current_status_code not in allowed_statuses:
            raise ValidationError("Profile cannot be checked in its current status.")

        assignments = list(profile.drone_assignments.all())
        if not assignments:
            raise ValidationError("Profile has no drone assignments configured for device check.")

        assignments_by_id = {assignment.id: assignment for assignment in assignments}
        assignments_by_device_id = {
            assignment.device_id: assignment
            for assignment in assignments
            if assignment.device_id
        }

        processed_entries: List[Dict[str, Any]] = []
        all_checklist_ids: set[int] = set()

        for entry in drone_checks:
            entry_dict = entry if isinstance(entry, dict) else entry.dict()
            profile_drone_id = entry_dict.get("profile_drone_id")

            assignment = None
            if profile_drone_id is not None:
                assignment = assignments_by_id.get(profile_drone_id)
                if not assignment:
                    raise ValidationError(
                        f"Drone assignment with id {profile_drone_id} not found for this profile."
                    )

            else:
                raise ValidationError(
                    "Each drone check entry must include profile_drone_id or drone_id."
                )

            check_lists = entry_dict.get("check_lists") or []
            auto_checklist = entry_dict.get("auto_checklist") or []

            if not isinstance(check_lists, list):
                raise ValidationError("check_lists must be a list of checklist setting IDs.")
            if not isinstance(auto_checklist, list):
                raise ValidationError("auto_checklist must be a list of automatic checklist entries.")

            unique_checklist_ids = list(dict.fromkeys(check_lists))
            all_checklist_ids.update(unique_checklist_ids)

            processed_entries.append(
                {
                    "assignment": assignment,
                    "check_lists": unique_checklist_ids,
                    "auto_checklist": auto_checklist,
                }
            )

        checklist_map: Dict[int, ChecklistSetting] = {}
        if all_checklist_ids:
            existing_checklists = ChecklistSetting.objects.filter(id__in=all_checklist_ids)
            checklist_map = {item.id: item for item in existing_checklists}
            missing_ids = all_checklist_ids.difference(checklist_map.keys())
            if missing_ids:
                missing_str = ", ".join(str(value) for value in sorted(missing_ids))
                raise ValidationError(f"Checklist setting(s) not found: {missing_str}.")

        is_not_yet = bool(not_yet)

        for entry in processed_entries:
            assignment = entry["assignment"]
            checklist_instance = (
                SurveillanceProfileChecklist.objects
                .filter(profile=profile, profile_drone=assignment)
                .first()
            )

            auto_data = entry["auto_checklist"] or None

            if checklist_instance:
                checklist_instance.checked_by = checked_by
                checklist_instance.auto_check_data = auto_data
                checklist_instance.save(
                    update_fields=[
                        "checked_by",
                        "auto_check_data",
                        "modified_on",
                    ]
                )
            else:
                checklist_instance = SurveillanceProfileChecklist.objects.create(
                    profile=profile,
                    profile_drone=assignment,
                    checked_by=checked_by,
                    auto_check_data=auto_data,
                )

            checklist_instance.items.all().delete()

            for checklist_id in entry["check_lists"]:
                checklist_setting = checklist_map.get(checklist_id)
                if not checklist_setting:
                    # Should not happen due to earlier validation, but guard against race conditions
                    continue
                SurveillanceProfileChecklistItem.objects.create(
                    checklist=checklist_instance,
                    checklist_setting=checklist_setting,
                    item_name_snapshot=checklist_setting.item_name,
                    category_code_snapshot=(
                        checklist_setting.category.code if checklist_setting.category else None
                    ),
                )

        metadata = profile.metadata or {}
        check_timestamp = timezone.now()
        metadata["not_yet"] = is_not_yet
        metadata["last_device_check"] = {
            "checked_at": check_timestamp.isoformat(),
            "checked_by_id": getattr(checked_by, "id", None),
            "checked_by_username": getattr(checked_by, "username", None),
            "not_yet": is_not_yet,
            "assignments": [entry["assignment"].id for entry in processed_entries],
        }

        metadata = SurveillanceProfileAutomationService.apply_auto_launch_metadata(
            metadata=metadata,
            profile=profile,
            is_not_yet=is_not_yet,
            timestamp=check_timestamp,
        )

        profile.not_yet = is_not_yet
        update_fields = ["metadata", "modified_on", "not_yet"]

        if is_not_yet:
            # Khi not_yet=True: Lập lịch kích hoạt khi đến giờ start_time
            # Lock profile để tránh race condition khi nhiều request cùng lúc schedule task
            locked_profile = (
                SurveillanceProfile._base_manager
                .select_for_update(nowait=False, skip_locked=False)
                .get(id=profile.id)
            )
            # Merge metadata đã được cập nhật từ apply_auto_launch_metadata với metadata hiện tại của locked_profile
            locked_metadata = dict(locked_profile.metadata or {})
            # Cập nhật các thay đổi từ metadata đã được apply_auto_launch_metadata xử lý
            locked_metadata.update(metadata)
            
            start_time = locked_profile.start_time
            if start_time and timezone.is_naive(start_time):
                start_time = timezone.make_aware(start_time, timezone.get_current_timezone())
            
            if start_time:
                # ------------------------------------------------------------------
                # Deterministic drone contention (NO RETRY):
                # - Profile that completes device check FIRST will reserve drones.
                # - Any later profile that checks the same drone(s) will be auto-cancelled.
                # Priority timestamp requested by user is based on SurveillanceProfileDrone.modified_on,
                # so we sync assignment.modified_on to this device-check timestamp.
                # ------------------------------------------------------------------
                try:
                    from django.core.cache import cache

                    assignment_ids = [
                        entry["assignment"].id
                        for entry in processed_entries
                        if entry.get("assignment") is not None
                    ]
                    if assignment_ids:
                        # Force modified_on to device-check timestamp for deterministic ordering
                        SurveillanceProfileDrone._base_manager.filter(id__in=assignment_ids).update(
                            modified_on=check_timestamp
                        )

                    device_ids: List[int] = []
                    for entry in processed_entries:
                        assignment = entry.get("assignment")
                        if assignment and getattr(assignment, "device_id", None):
                            device_ids.append(int(assignment.device_id))
                    device_ids = sorted(set(device_ids))

                    # Keep reservation until after scheduled start_time (+1h buffer)
                    now_ts = timezone.now()
                    if timezone.is_naive(now_ts):
                        now_ts = timezone.make_aware(now_ts, timezone.get_current_timezone())
                    ttl_seconds = int(max(60, (start_time - now_ts).total_seconds() + 3600))

                    reservation_added_keys: List[str] = []
                    conflict_owner_profile_ids: set[int] = set()

                    for device_id in device_ids:
                        key = f"surveillance:drone_reservation:{device_id}"
                        value = {"profile_id": locked_profile.id, "checked_at": check_timestamp.isoformat()}
                        added = cache.add(key, value, timeout=ttl_seconds)
                        if added:
                            reservation_added_keys.append(key)
                            continue

                        existing = cache.get(key)
                        existing_profile_id: Optional[int] = None
                        if isinstance(existing, int):
                            existing_profile_id = existing
                        elif isinstance(existing, dict):
                            try:
                                existing_profile_id = int(existing.get("profile_id"))
                            except Exception:
                                existing_profile_id = None
                        else:
                            try:
                                existing_profile_id = int(existing)
                            except Exception:
                                existing_profile_id = None

                        if existing_profile_id and existing_profile_id != locked_profile.id:
                            conflict_owner_profile_ids.add(existing_profile_id)

                    if conflict_owner_profile_ids:
                        # Do NOT auto-cancel at device-check time.
                        # User may cancel the earlier (winner) profile before start_time; in that case,
                        # this profile should still be able to activate later.
                        # Release any partial reservations we created, and mark conflict in metadata.
                        for k in reservation_added_keys:
                            try:
                                cache.delete(k)
                            except Exception:
                                pass

                        locked_metadata["drone_reservation_conflict"] = {
                            "conflict_at": check_timestamp.isoformat(),
                            "owner_profile_ids": sorted(conflict_owner_profile_ids),
                            "note": "Conflict detected at device-check; activation will decide winner at runtime.",
                        }
                    else:
                        locked_metadata.pop("drone_reservation_conflict", None)
                except Exception as reserve_exc:
                    logger.warning(
                        "[SURVEILLANCE] Không thể xử lý drone reservation khi complete device check cho profile %s: %s",
                        locked_profile.code,
                        reserve_exc,
                    )

                from surveillance.tasks import activate_surveillance_profile
                from celery import current_app
                
                # Kiểm tra xem đã có task được lập lịch trước đó chưa
                existing_scheduled = locked_metadata.get("activation_scheduled", {})
                existing_task_id = existing_scheduled.get("task_id")
                existing_scheduled_for = existing_scheduled.get("scheduled_for")
                
                # Nếu đã có task cũ và start_time không thay đổi, bỏ qua
                if existing_task_id and existing_scheduled_for:
                    try:
                        existing_scheduled_time = parse_datetime(existing_scheduled_for)
                        if existing_scheduled_time:
                            if timezone.is_naive(existing_scheduled_time):
                                existing_scheduled_time = timezone.make_aware(existing_scheduled_time, timezone.get_current_timezone())
                        else:
                            raise ValueError("Could not parse datetime")
                        
                        # Nếu thời gian giống nhau (chênh lệch < 1 giây), không cần lập lịch lại
                        if abs((start_time - existing_scheduled_time).total_seconds()) < 1:
                            logger.info(
                                "[SURVEILLANCE] Profile %s đã có lịch kích hoạt tại %s, bỏ qua lập lịch lại",
                                locked_profile.code,
                                start_time.isoformat(),
                            )
                            # Cập nhật metadata đã được lock
                            locked_profile.metadata = locked_metadata
                            locked_profile.not_yet = is_not_yet
                            locked_profile.save(update_fields=["metadata", "modified_on", "not_yet"])
                            return
                        else:
                            # Thời gian thay đổi, hủy task cũ
                            try:
                                current_app.control.revoke(existing_task_id, terminate=False)
                                logger.info(
                                    "[SURVEILLANCE] Đã hủy task cũ %s cho profile %s do start_time thay đổi",
                                    existing_task_id,
                                    locked_profile.code,
                                )
                            except Exception as revoke_exc:
                                logger.warning(
                                    "[SURVEILLANCE] Không thể hủy task cũ %s cho profile %s: %s",
                                    existing_task_id,
                                    locked_profile.code,
                                    revoke_exc,
                                )
                    except (ValueError, TypeError) as parse_exc:
                        logger.warning(
                            "[SURVEILLANCE] Không thể parse thời gian đã lập lịch cho profile %s: %s",
                            locked_profile.code,
                            parse_exc,
                        )
                        # Nếu không parse được, tiếp tục lập lịch mới
                
                # Lập lịch task mới
                try:
                    # Priority cao (0) cho task auto flight để được xử lý trước
                    async_result = activate_surveillance_profile.apply_async(
                        args=[locked_profile.id],
                        eta=start_time,
                        priority=0,  # Priority cao nhất để được xử lý trước các task khác
                    )
                    locked_metadata["activation_scheduled"] = {
                        "scheduled_at": check_timestamp.isoformat(),
                        "scheduled_for": start_time.isoformat(),
                        "task_id": async_result.id,
                    }
                    locked_profile.metadata = locked_metadata
                    locked_profile.not_yet = is_not_yet
                    locked_profile.save(update_fields=["metadata", "modified_on", "not_yet"])
                    logger.info(
                        "[SURVEILLANCE] Profile %s đã được lập lịch kích hoạt lúc %s (task_id=%s)",
                        locked_profile.code,
                        start_time.isoformat(),
                        async_result.id,
                    )
                except Exception as exc:
                    logger.exception(
                        "[SURVEILLANCE] Không thể lập lịch kích hoạt profile %s: %s",
                        locked_profile.code,
                        exc,
                    )
            else:
                logger.warning(
                    "[SURVEILLANCE] Profile %s có not_yet=True nhưng không có start_time",
                    profile.code,
                )
        else:
            # Khi not_yet=False: Kích hoạt ngay
            # Hủy task đã lập lịch trước đó nếu có
            existing_scheduled = metadata.get("activation_scheduled", {})
            existing_task_id = existing_scheduled.get("task_id")
            if existing_task_id:
                try:
                    from celery import current_app
                    current_app.control.revoke(existing_task_id, terminate=False)
                    logger.info(
                        "[SURVEILLANCE] Đã hủy task lập lịch %s cho profile %s do not_yet=False",
                        existing_task_id,
                        profile.code,
                    )
                except Exception as revoke_exc:
                    logger.warning(
                        "[SURVEILLANCE] Không thể hủy task lập lịch %s cho profile %s: %s",
                        existing_task_id,
                        profile.code,
                        revoke_exc,
                    )
                metadata.pop("activation_scheduled", None)
            
            SurveillanceProfileService.upload_profile_to_flightbird(profile)
            metadata.pop("auto_launch", None)

        profile.metadata = metadata
        profile.save(update_fields=update_fields)

        return True, profile

    @staticmethod
    def get_scheduled_activations() -> QuerySet:
        """Lấy danh sách các profile đã được lập lịch (kích hoạt hoặc overdue check)."""
        return (
            SurveillanceProfile.objects
            .select_related("status", "mission")
            .filter(
                Q(metadata__activation_scheduled__isnull=False) | Q(metadata__overdue_check_task_id__isnull=False),
                actual_end_time__isnull=True,
            )
            .order_by("start_time")
        )

    @staticmethod
    def _verify_task_status(task_id: str) -> Tuple[bool, Optional[str]]:
        """Verify task còn tồn tại trong Celery không và trả về status."""
        if not task_id:
            return False, None
        
        try:
            from celery import current_app
            from celery.result import AsyncResult
            
            # Kiểm tra task status
            result = AsyncResult(task_id, app=current_app)
            task_status = result.state
            
            # Task tồn tại nếu không phải là PENDING hoặc không tồn tại
            if task_status:
                # Kiểm tra trong scheduled tasks nếu state là PENDING
                if task_status == "PENDING":
                    inspect = current_app.control.inspect()
                    scheduled = inspect.scheduled()
                    if scheduled:
                        for worker_tasks in scheduled.values():
                            for task in worker_tasks:
                                if task.get("request", {}).get("id") == task_id:
                                    return True, task_status
                    return False, task_status
                else:
                    # Task đã được schedule hoặc đang chạy
                    return True, task_status
            return False, None
        except Exception as exc:
            logger.warning(
                "[SURVEILLANCE] Không thể kiểm tra task %s trong Celery: %s",
                task_id,
                exc,
            )
            return False, None

    @staticmethod
    def diagnose_task_not_running(task_id: str, scheduled_for: Optional[str] = None) -> Dict[str, Any]:
        """
        Chẩn đoán chi tiết tại sao một task với ETA không chạy.
        
        Returns:
            Dict chứa thông tin chi tiết về nguyên nhân task không chạy
        """
        diagnosis = {
            "task_id": task_id,
            "scheduled_for": scheduled_for,
            "task_exists": False,
            "task_status": None,
            "reasons": [],
            "details": {},
        }
        
        if not task_id:
            diagnosis["reasons"].append("task_id_is_empty")
            return diagnosis
        
        try:
            from celery import current_app
            from celery.result import AsyncResult
            from django.utils import timezone
            from django.utils.dateparse import parse_datetime
            import pytz
            
            # 1. Kiểm tra task status cơ bản
            result = AsyncResult(task_id, app=current_app)
            task_status = result.state
            diagnosis["task_status"] = task_status
            
            if not task_status:
                diagnosis["reasons"].append("task_not_found_in_celery")
                diagnosis["details"]["task_not_found"] = "Task không tồn tại trong Celery result backend"
            
            # 2. Kiểm tra trong scheduled tasks
            try:
                inspect = current_app.control.inspect()
                
                # Check scheduled tasks
                scheduled = inspect.scheduled()
                found_in_scheduled = False
                if scheduled:
                    for worker_name, worker_tasks in scheduled.items():
                        for task in worker_tasks:
                            task_request = task.get("request", {})
                            if task_request.get("id") == task_id:
                                found_in_scheduled = True
                                diagnosis["task_exists"] = True
                                diagnosis["details"]["scheduled_info"] = {
                                    "worker": worker_name,
                                    "eta": task_request.get("eta"),
                                    "expires": task_request.get("expires"),
                                    "task": task_request.get("task"),
                                }
                                break
                        if found_in_scheduled:
                            break
                
                # Check active tasks
                active = inspect.active()
                found_in_active = False
                if active:
                    for worker_name, worker_tasks in active.items():
                        for task in worker_tasks:
                            if task.get("id") == task_id:
                                found_in_active = True
                                diagnosis["task_exists"] = True
                                diagnosis["details"]["active_info"] = {
                                    "worker": worker_name,
                                    "name": task.get("name"),
                                    "time_start": task.get("time_start"),
                                }
                                break
                        if found_in_active:
                            break
                
                # Check reserved tasks
                reserved = inspect.reserved()
                found_in_reserved = False
                if reserved:
                    for worker_name, worker_tasks in reserved.items():
                        for task in worker_tasks:
                            if task.get("id") == task_id:
                                found_in_reserved = True
                                diagnosis["task_exists"] = True
                                diagnosis["details"]["reserved_info"] = {
                                    "worker": worker_name,
                                    "name": task.get("name"),
                                }
                                break
                        if found_in_reserved:
                            break
                
                # Check revoked tasks
                revoked = inspect.revoked()
                found_in_revoked = False
                if revoked:
                    for worker_name, revoked_tasks in revoked.items():
                        if task_id in revoked_tasks:
                            found_in_revoked = True
                            diagnosis["reasons"].append("task_was_revoked")
                            diagnosis["details"]["revoked_info"] = {
                                "worker": worker_name,
                            }
                            break
                
                if not found_in_scheduled and not found_in_active and not found_in_reserved:
                    if task_status == "PENDING":
                        diagnosis["reasons"].append("task_not_in_worker_queues")
                        diagnosis["details"]["task_not_in_queues"] = "Task có status PENDING nhưng không có trong scheduled/active/reserved của worker"
                
            except Exception as inspect_exc:
                diagnosis["reasons"].append("cannot_inspect_workers")
                diagnosis["details"]["inspect_error"] = str(inspect_exc)
                diagnosis["details"]["inspect_error_type"] = type(inspect_exc).__name__
            
            # 3. Kiểm tra nếu task đã quá hạn
            if scheduled_for:
                try:
                    scheduled_for_dt = parse_datetime(scheduled_for)
                    if scheduled_for_dt:
                        if timezone.is_naive(scheduled_for_dt):
                            scheduled_for_dt = timezone.make_aware(scheduled_for_dt, timezone.get_current_timezone())
                        if scheduled_for_dt.tzinfo != pytz.UTC:
                            scheduled_for_dt = scheduled_for_dt.astimezone(pytz.UTC)
                        
                        now = timezone.now()
                        if now.tzinfo != pytz.UTC:
                            now = now.astimezone(pytz.UTC)
                        
                        if scheduled_for_dt < now:
                            diagnosis["reasons"].append("task_scheduled_time_passed")
                            diagnosis["details"]["time_check"] = {
                                "scheduled_for_utc": scheduled_for_dt.isoformat(),
                                "now_utc": now.isoformat(),
                                "seconds_passed": (now - scheduled_for_dt).total_seconds(),
                            }
                            
                            # Nếu task không tồn tại và đã quá hạn, có thể đã expire
                            if not diagnosis["task_exists"]:
                                diagnosis["reasons"].append("task_likely_expired")
                                diagnosis["details"]["expired_reason"] = "Task đã quá thời gian scheduled và không còn trong Celery, có thể đã bị expire"
                except Exception as time_exc:
                    diagnosis["reasons"].append("cannot_parse_scheduled_time")
                    diagnosis["details"]["time_parse_error"] = str(time_exc)
            
            # 4. Kiểm tra task result để xem có error không
            try:
                if result.ready():
                    if result.successful():
                        diagnosis["reasons"].append("task_already_completed")
                        diagnosis["details"]["completed"] = "Task đã chạy thành công"
                    elif result.failed():
                        diagnosis["reasons"].append("task_failed")
                        diagnosis["details"]["failure"] = {
                            "error": str(result.info) if result.info else "Unknown error",
                            "traceback": result.traceback if hasattr(result, 'traceback') else None,
                        }
            except Exception as result_exc:
                pass
            
            # 5. Kiểm tra Celery workers có đang chạy không
            try:
                inspect = current_app.control.inspect()
                active_workers = inspect.active_queues()
                if not active_workers:
                    diagnosis["reasons"].append("no_active_workers")
                    diagnosis["details"]["no_workers"] = "Không có Celery worker nào đang chạy"
                else:
                    diagnosis["details"]["active_workers"] = list(active_workers.keys())
            except Exception as worker_exc:
                diagnosis["reasons"].append("cannot_check_workers")
                diagnosis["details"]["worker_check_error"] = str(worker_exc)
            
        except Exception as exc:
            diagnosis["reasons"].append("diagnosis_error")
            diagnosis["details"]["error"] = str(exc)
            diagnosis["details"]["error_type"] = type(exc).__name__
            logger.exception(
                "[SURVEILLANCE] Error diagnosing task %s: %s",
                task_id,
                exc,
            )
        
        return diagnosis

    @staticmethod
    def get_all_profile_tasks(profile_id: int) -> Optional[Dict[str, Any]]:
        """Lấy thông tin tất cả các task liên quan đến một profile."""
        try:
            profile = SurveillanceProfile.objects.select_related("status").get(id=profile_id)
        except SurveillanceProfile.DoesNotExist:
            return None

        metadata = profile.metadata or {}
        tasks = []

        # Task kích hoạt (activation)
        activation_scheduled = metadata.get("activation_scheduled")
        if activation_scheduled:
            task_id = activation_scheduled.get("task_id")
            task_exists, task_status = SurveillanceProfileService._verify_task_status(task_id)
            
            tasks.append({
                "type": "activation",
                "task_name": "activate_surveillance_profile",
                "description": "Kích hoạt profile khi đến giờ start_time",
                "task_id": task_id,
                "scheduled_at": activation_scheduled.get("scheduled_at"),
                "scheduled_for": activation_scheduled.get("scheduled_for"),
                "task_exists": task_exists,
                "task_status": task_status,
            })

        # Task kiểm tra quá hạn (overdue check)
        overdue_task_id = metadata.get("overdue_check_task_id")
        if overdue_task_id:
            overdue_check_eta = metadata.get("overdue_check_eta")
            overdue_check_scheduled_at = metadata.get("overdue_check_scheduled_at")
            task_exists, task_status = SurveillanceProfileService._verify_task_status(overdue_task_id)
            
            # Kiểm tra nếu task đã quá hạn và không còn tồn tại
            is_expired = False
            if overdue_check_eta:
                try:
                    from django.utils.dateparse import parse_datetime
                    scheduled_for_dt = parse_datetime(overdue_check_eta)
                    if scheduled_for_dt:
                        from django.utils import timezone
                        import pytz
                        if timezone.is_naive(scheduled_for_dt):
                            scheduled_for_dt = timezone.make_aware(scheduled_for_dt, timezone.get_current_timezone())
                        if scheduled_for_dt.tzinfo != pytz.UTC:
                            scheduled_for_dt = scheduled_for_dt.astimezone(pytz.UTC)
                        now = timezone.now()
                        if now.tzinfo != pytz.UTC:
                            now = now.astimezone(pytz.UTC)
                        if scheduled_for_dt < now and not task_exists:
                            is_expired = True
                except Exception:
                    pass
            
            # Chẩn đoán chi tiết nếu task không tồn tại
            diagnosis = None
            if not task_exists:
                diagnosis = SurveillanceProfileService.diagnose_task_not_running(
                    overdue_task_id,
                    overdue_check_eta
                )
            
            tasks.append({
                "type": "overdue_check",
                "task_name": "check_surveillance_profile_overdue",
                "description": "Kiểm tra và tự động hủy profile nếu quá hạn",
                "task_id": overdue_task_id,
                "scheduled_at": overdue_check_scheduled_at,
                "scheduled_for": overdue_check_eta,
                "task_exists": task_exists,
                "task_status": task_status,
                "overdue_hours_config": metadata.get("overdue_hours_config"),
                "is_expired": is_expired,
                "diagnosis": diagnosis,
            })

        return {
            "profile_id": profile.id,
            "profile_code": profile.code,
            "profile_name": profile.name,
            "status_code": profile.status.code if profile.status else None,
            "start_time": profile.start_time.isoformat() if profile.start_time else None,
            "actual_start_time": profile.actual_start_time.isoformat() if profile.actual_start_time else None,
            "tasks": tasks,
            "total_tasks": len(tasks),
        }

    @staticmethod
    def get_scheduled_activation_info(profile_id: int) -> Optional[Dict[str, Any]]:
        """Lấy thông tin lịch kích hoạt của một profile (deprecated - dùng get_all_profile_tasks)."""
        all_tasks_info = SurveillanceProfileService.get_all_profile_tasks(profile_id)
        if not all_tasks_info:
            return None
        
        # Tìm task activation
        activation_task = next(
            (task for task in all_tasks_info["tasks"] if task["type"] == "activation"),
            None
        )
        
        if not activation_task:
            return None

        return {
            "profile_id": all_tasks_info["profile_id"],
            "profile_code": all_tasks_info["profile_code"],
            "profile_name": all_tasks_info["profile_name"],
            "status_code": all_tasks_info["status_code"],
            "start_time": all_tasks_info["start_time"],
            "scheduled_at": activation_task.get("scheduled_at"),
            "scheduled_for": activation_task.get("scheduled_for"),
            "task_id": activation_task.get("task_id"),
            "task_exists": activation_task.get("task_exists"),
            "task_status": activation_task.get("task_status"),
        }

    @staticmethod
    @transaction.atomic
    def cancel_profile_task(profile_id: int, task_type: Optional[str] = None) -> Tuple[bool, Optional[str], int]:
        """
        Hủy task đã lập cho một profile.
        
        Args:
            profile_id: ID của profile
            task_type: Loại task cần hủy ('activation', 'overdue_check', hoặc None để hủy tất cả)
        
        Returns:
            Tuple[bool, Optional[str], int]: (success, error_message, cancelled_count)
        """
        try:
            profile = SurveillanceProfile.objects.select_related("status").get(id=profile_id)
        except SurveillanceProfile.DoesNotExist:
            return False, "Profile not found", 0

        metadata = profile.metadata or {}
        cancelled_count = 0

        try:
            from celery import current_app
        except ImportError:
            return False, "Celery not available", 0

        # Hủy task activation
        if task_type is None or task_type == "activation":
            activation_scheduled = metadata.get("activation_scheduled")
            if activation_scheduled:
                task_id = activation_scheduled.get("task_id")
                if task_id:
                    try:
                        current_app.control.revoke(task_id, terminate=False)
                        logger.info(
                            "[SURVEILLANCE] Đã hủy task activation %s cho profile %s",
                            task_id,
                            profile.code,
                        )
                        cancelled_count += 1
                    except Exception as revoke_exc:
                        logger.warning(
                            "[SURVEILLANCE] Không thể hủy task activation %s cho profile %s: %s",
                            task_id,
                            profile.code,
                            revoke_exc,
                        )
                metadata.pop("activation_scheduled", None)

        # Hủy task overdue check
        if task_type is None or task_type == "overdue_check":
            overdue_task_id = metadata.get("overdue_check_task_id")
            if overdue_task_id:
                try:
                    current_app.control.revoke(overdue_task_id, terminate=False)
                    logger.info(
                        "[SURVEILLANCE] Đã hủy task overdue_check %s cho profile %s",
                        overdue_task_id,
                        profile.code,
                    )
                    cancelled_count += 1
                except Exception as revoke_exc:
                    logger.warning(
                        "[SURVEILLANCE] Không thể hủy task overdue_check %s cho profile %s: %s",
                        overdue_task_id,
                        profile.code,
                        revoke_exc,
                    )
                metadata.pop("overdue_check_task_id", None)
                metadata.pop("overdue_check_eta", None)
                metadata.pop("overdue_check_scheduled_at", None)

        if cancelled_count > 0:
            profile.metadata = metadata
            profile.save(update_fields=["metadata", "modified_on"])

        return True, None, cancelled_count

    @staticmethod
    @transaction.atomic
    def cancel_scheduled_activation(profile_id: int) -> Tuple[bool, Optional[str]]:
        """Hủy lịch kích hoạt đã lập cho một profile (deprecated - dùng cancel_profile_task)."""
        success, error_message, cancelled_count = SurveillanceProfileService.cancel_profile_task(
            profile_id, task_type="activation"
        )
        if not success:
            return False, error_message or "No scheduled activation found for this profile"
        return True, None

    @staticmethod
    @transaction.atomic
    def stop_repeat(profile_id: int) -> Tuple[bool, SurveillanceProfile]:
        try:
            profile = SurveillanceProfile.objects.get(id=profile_id)
            profile.repeat_parent = None
            profile.repeat_type = SurveillanceProfileRepeatType.objects.get(code='none')
            profile.repeat_until_type = None
            profile.repeat_until_date = None
            profile.repeat_occurrences = None
            profile.save(update_fields=["repeat_parent", "repeat_type", "repeat_until_type", "repeat_until_date", "repeat_occurrences", "modified_on"])
        except SurveillanceProfile.DoesNotExist as exc:
            raise ValidationError(f"Profile with id {profile_id} not found") from exc

        return True, profile
    @staticmethod
    @transaction.atomic
    def approve_profile(profile_id: int, approved_by, note: Optional[str] = None) -> Tuple[bool, SurveillanceProfile]:
        try:
            profile = (
                SurveillanceProfile.objects
                .select_related("status", "repeat_parent")
                .get(id=profile_id)
            )
        except SurveillanceProfile.DoesNotExist as exc:
            raise ValidationError(f"Profile with id {profile_id} not found") from exc

        current_status_code = profile.status.code if profile.status else None
        allowed_statuses = {"pending_approval", "pending_device_check"}
        if current_status_code not in allowed_statuses:
            raise ValidationError("Profile cannot be approved in its current status.")


       
        device_check_status = SurveillanceProfileService._get_status_by_code("pending_device_check")
        metadata = profile.metadata or {}
        approval_history = metadata.setdefault("approval_history", [])
        approval_entry = {
            "approved_at": timezone.now().isoformat(),
            "approved_by_id": getattr(approved_by, "id", None),
            "approved_by_username": getattr(approved_by, "username", None),
        }
        if note:
            approval_entry["note"] = note
            metadata["approval_note"] = note

        approval_history.append(approval_entry)
        metadata["last_approved_by_id"] = approval_entry["approved_by_id"]
        metadata["last_approved_at"] = approval_entry["approved_at"]

        # Reset rejection markers when approved again
        metadata.pop("last_rejected_by_id", None)
        metadata.pop("last_rejected_at", None)
        metadata.pop("rejection_note", None)
        profile.status = device_check_status
        profile.metadata = metadata
        profile.approved_by = approved_by
        profile.save(update_fields=["status", "metadata", "modified_on", "approved_by"])

        return True, profile

    @staticmethod
    @transaction.atomic
    def reject_profile(profile_id: int, reason: str, rejected_by) -> Tuple[bool, SurveillanceProfile]:
        if not reason:
            raise ValidationError("Reject reason is required.")

        try:
            profile = (
                SurveillanceProfile.objects
                .select_related("status")
                .get(id=profile_id)
            )
        except SurveillanceProfile.DoesNotExist as exc:
            raise ValidationError(f"Profile with id {profile_id} not found") from exc

        current_status_code = profile.status.code if profile.status else None
        allowed_statuses = {"pending_approval", "pending_device_check", "approved"}
        if current_status_code not in allowed_statuses:
            raise ValidationError("Profile cannot be rejected in its current status.")

        rejected_status = SurveillanceProfileService._get_status_by_code("rejected")

        SurveillanceProfileService._delete_child_profiles(profile)

        metadata = profile.metadata or {}
        rejection_history = metadata.setdefault("rejection_history", [])
        rejection_time = timezone.now()
        rejection_entry = {
            "rejected_at": rejection_time.isoformat(),
            "rejected_by_id": getattr(rejected_by, "id", None),
            "rejected_by_username": getattr(rejected_by, "username", None),
            "reason": reason,
        }
        rejection_history.append(rejection_entry)

        metadata["last_rejected_by_id"] = rejection_entry["rejected_by_id"]
        metadata["last_rejected_at"] = rejection_entry["rejected_at"]
        metadata["rejection_note"] = reason

        profile.status = rejected_status
        profile.metadata = metadata
        profile.reject_reason = reason
        profile.rejected_by = rejected_by
        profile.rejected_at = rejection_time
        profile.approved_by = None
        profile.save(update_fields=[
            "status",
            "metadata",
            "modified_on",
            "approved_by",
            "reject_reason",
            "rejected_by",
            "rejected_at",
        ])

        SurveillanceProfileAutomationService.clear_auto_launch(
            profile,
            timestamp=rejection_time,
            reason="rejected",
        )

        return True, profile

    @staticmethod
    @transaction.atomic
    def delete(profile_id: int) -> Tuple[bool, str]:
        try:
            profile = SurveillanceProfile.objects.get(id=profile_id)
            code = profile.code
            SurveillanceProfileService._delete_child_profiles(profile)
            profile.delete()
            logger.info("Deleted surveillance profile %s", code)
            return True, get_message(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
        except SurveillanceProfile.DoesNotExist as exc:
            raise ValidationError(f"Profile with id {profile_id} not found") from exc
        except Exception as exc:
            logger.exception("Error deleting surveillance profile: %s", exc)
            raise ValidationError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Map helpers
    # ------------------------------------------------------------------
    @staticmethod
    def get_profile_with_route_map(profile_id: int) -> Optional[Dict[str, Any]]:
        profile = SurveillanceProfileService.get_detail(profile_id)
        if not profile:
            return None

        mission = profile.mission
        waypoints = mission.waypoints.select_related("terminal").order_by("order")

        route_waypoints: List[Dict[str, Any]] = []
        for waypoint in waypoints:
            route_waypoints.append(
                {
                    "id": waypoint.id,
                    "order": waypoint.order,
                    "name": waypoint.name,
                    "latitude": waypoint.latitude,
                    "longitude": waypoint.longitude,
                    "terminal_name": waypoint.terminal.name if waypoint.terminal else None,
                }
            )

        devices_positions: List[Dict[str, Any]] = []

        return {
            "profile": profile,
            "route_waypoints": route_waypoints,
            "devices_positions": devices_positions,
        }

    @staticmethod
    def _resolve_user_or_system_timezone():
        """
        Resolve timezone used for "user-local" date calculations.

        Rule:
        - Use `request.user.timezone` if set.
        - Otherwise, use timezone from `AdminConfig` (system config).
        - Input datetimes are assumed to be UTC.
        """
        request = None
        try:
            request = get_current_request()
        except Exception:
            request = None

        # 1) User timezone (preferred)
        try:
            user = getattr(request, "user", None) if request is not None else None
            user_tz = getattr(user, "timezone", None) if user is not None else None
            if user_tz is not None:
                code = getattr(user_tz, "code", None)
                if code:
                    try:
                        return ZoneInfo(str(code).strip())
                    except Exception:
                        pass
                offset = getattr(user_tz, "offset", None)
                if offset is not None:
                    offset_int = int(offset)
                    # DB in this project may store timezone offset as hours (e.g. +7) or minutes (e.g. +420).
                    # Heuristic: abs <= 24 => hours, otherwise minutes.
                    if abs(offset_int) <= 24:
                        return dt_timezone(timedelta(hours=offset_int))
                    return dt_timezone(timedelta(minutes=offset_int))
        except Exception as e:
            logger.error("Error resolving user timezone: %s", e)
            pass

        # 2) System timezone from AdminConfig
        try:
            config = AdminConfig.objects.filter(name="System", is_active=True).values("settings").first()
            settings_data = config["settings"] if config and isinstance(config.get("settings"), dict) else {}
            tz_value = settings_data.get("timezone") or settings_data.get("time_zone") or settings_data.get("tz")
        
            if isinstance(tz_value, str) and tz_value.strip():
                try:
                    return ZoneInfo(tz_value.strip())
                except Exception as e:
                    logger.error("Error resolving system timezone: %s", e)
                    pass
           
        except Exception as e:
            logger.error("Error resolving system timezone: %s", e)
            pass

        # Final fallback: Django current timezone
        return timezone.get_current_timezone()

    @staticmethod
    def get_timeline_queryset_for_day(
        created_on: datetime,
        params,
        profile_ids: Optional[List[int]] = None,
    ) -> Tuple[QuerySet, datetime, datetime]:
        """
        Get timeline queryset for a specific day.
        
        Args:
            created_on: The datetime to extract date from (e.g. 2025-12-08T17:00:00+00:00)
            params: Filter parameters
            profile_ids: Optional list of profile IDs to filter
            
        Returns:
            Tuple of (queryset, start_of_day, end_of_day)
        """
        if not created_on:
            raise ValidationError("created_on is required")

        user_tz = SurveillanceProfileService._resolve_user_or_system_timezone()
        # Ensure timezone-aware input (assume UTC if missing tzinfo) - input is always UTC
        if timezone.is_naive(created_on):
            created_on = timezone.make_aware(created_on, dt_timezone.utc)

        # Convert to user's timezone before extracting date (do NOT rely on Django settings timezone)
        local_datetime = created_on.astimezone(user_tz)
        target_date = local_datetime.date()
        start_of_day = timezone.make_aware(datetime.combine(target_date, time.min), user_tz)
        end_of_day = timezone.make_aware(datetime.combine(target_date, time.max), user_tz)
        
        queryset = SurveillanceProfileService.get_queryset_optimized()
        queryset = SurveillanceProfileService.apply_filters(queryset, params)
        # Filter profiles where effective start_time (actual_start_time or start_time) is within the day
        # Only use actual_start_time when BOTH actual_start_time and actual_end_time exist;
        # otherwise fall back to planned start_time.
        queryset = queryset.annotate(
            effective_start_time=Case(
                When(
                    actual_start_time__isnull=False,
                    actual_end_time__isnull=False,
                    then=F("actual_start_time"),
                ),
                default=F("start_time"),
            )
        ).filter(
            effective_start_time__gte=start_of_day,
            effective_start_time__lte=end_of_day
        )
        
        if profile_ids:
            queryset = queryset.filter(id__in=profile_ids)
        queryset = queryset.distinct()

        return queryset, start_of_day, end_of_day


    @staticmethod
    def build_timeline_payload(
        profiles: Iterable[SurveillanceProfile],
        window_start: Optional[datetime] = None,
        window_end: Optional[datetime] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        by_profile: List[Dict[str, Any]] = []
        by_drone: List[Dict[str, Any]] = []
        for profile in profiles:
            profile_start = profile.actual_start_time if (profile.actual_start_time and profile.actual_end_time)  else profile.start_time
            timeline_end = profile.actual_end_time if (profile.actual_end_time and profile.actual_start_time)  else profile.estimated_end_time
            # if window_start and profile_start < window_start:
            #     profile_start = window_start
            # if window_end and timeline_end > window_end:
            #     timeline_end = window_end
            by_profile.append(
                {
                    "profile_id": profile.id,
                    "profile_name": profile.name,
                    "start_time": profile_start.isoformat() if isinstance(profile_start, datetime) else profile_start,
                    "end_time": timeline_end.isoformat() if isinstance(timeline_end, datetime) else timeline_end,
                    "color_code": profile.color_code,
                    "status_code": profile.status.code if profile.status else None,
                }
            )
 
        drone_list = Device.objects.filter(active=True)
        for drone in drone_list:
            drone_profiles = []
            
            for profile in profiles:
                drone_assignments = profile.drone_assignments.filter(device=drone)
                
                if drone_assignments.exists():
                    assignment = drone_assignments.first().profile
                    start_time = assignment.actual_start_time if (assignment.actual_start_time and assignment.actual_end_time) else assignment.start_time
                    end_time = assignment.actual_end_time if (assignment.actual_end_time and assignment.actual_start_time) else assignment.estimated_end_time
                    
                    # if window_start and start_time < window_start:
                    #     start_time = window_start
                    # if window_end and end_time > window_end:
                    #     end_time = window_end
                    
                    drone_profiles.append(
                        {
                            "profile_id": profile.id,
                            "profile_name": profile.name,
                            "start_time": start_time.isoformat() if isinstance(start_time, datetime) else start_time,
                            "end_time": end_time.isoformat() if isinstance(end_time, datetime) else end_time,
                            "color_code": profile.color_code,
                            "status_code": profile.status.code if profile.status else None,
                        }
                    )
            
           
            by_drone.append(
                {
                    "drone_id": drone.id,
                    "drone_serial": drone.name, 
                    "profiles": drone_profiles
                }
            )

        return {"by_profile": by_profile, "by_drone": by_drone}

    @staticmethod
    def _prepare_drone_candidates(
        devices: List[Dict[str, Any]],
        device_instances: Optional[Dict[int, Device]],
        fallback_cruise_speed: Optional[float],
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        devices_list = devices or []
        missing_instances_count = 0
        invalid_records_count = 0

        for device in devices_list:
            if not isinstance(device, dict):
                invalid_records_count += 1
                continue
            device_id = device.get("id")
            if not device_id:
                invalid_records_count += 1
                continue

            instance = device_instances.get(device_id) if device_instances else None
            if instance is None:
                context = SurveillanceProfileService._build_device_context([device_id])
                instance = context.get(device_id)
                if instance and isinstance(device_instances, dict):
                    device_instances[device_id] = instance

            if not instance:
                missing_instances_count += 1
                continue

            capability = SurveillanceProfileService._estimate_drone_capability(
                instance,
                fallback_cruise_speed,
            )

            candidates.append(
                {
                    "device": device.copy(),
                    "instance": instance,
                    "capability_distance_m": capability if capability is not None else 0.0,
                }
            )

        candidates.sort(
            key=lambda item: item.get("capability_distance_m") or 0.0,
            reverse=True,
        )
        if diagnostics is not None:
            diagnostics["devices_count"] = len(devices_list)
            diagnostics["missing_instances_count"] = missing_instances_count
            diagnostics["invalid_device_records_count"] = invalid_records_count
            diagnostics["candidates_count"] = len(candidates)
        return candidates

    @staticmethod
    def _estimate_drone_capability(
        device_instance: Device,
        fallback_cruise_speed: Optional[float],
    ) -> Optional[float]:
        try:
            estimation = FlightEstimationService.estimate_duration_for_distance(
                device_instance,
                0.0,
                default_cruise_speed=fallback_cruise_speed,
            )
        except Exception:
            return None

        cruise_speed = SurveillanceProfileService._safe_number(
            estimation.get("cruise_speed_ms"),
            float,
        )
        if cruise_speed is None and fallback_cruise_speed is not None:
            cruise_speed = fallback_cruise_speed

        flight_time_s = SurveillanceProfileService._safe_number(
            estimation.get("flight_time_s"),
            float,
        )
        maximum_range_m = SurveillanceProfileService._safe_number(
            estimation.get("maximum_range_m"),
            float,
        )

        capability: Optional[float] = None
        if cruise_speed and flight_time_s:
            capability = cruise_speed * flight_time_s
        if maximum_range_m is not None:
            capability = (
                maximum_range_m
                if capability is None
                else min(capability, maximum_range_m)
            )

        return capability

    @staticmethod
    def _split_mission_points(
        mission_points: List[Dict[str, Any]],
        cumulative_distances: List[float],
        segments_count: int,
    ) -> List[Dict[str, Any]]:
        segments: List[Dict[str, Any]] = []
        previous_end_index = -1
        total_distance = cumulative_distances[-1] if cumulative_distances else 0.0

        # When mission_points include interleaved action commands (ex: hover_and_capture adds
        # DO_DIGICAM_CONTROL after each waypoint), we must not split in the middle of a
        # waypoint->action pair. We treat navigation points as anchors and attach any
        # subsequent non-navigation points to the previous navigation point.
        navigation_command_ids = {16, 20, 21, 22}  # WAYPOINT, RTL, LAND, TAKEOFF

        def _is_navigation_point(point: Dict[str, Any]) -> bool:
            cmd = point.get("command_id")
            if cmd in navigation_command_ids:
                return True
            # Some legacy rows may not have command_id but are still navigation waypoints
            return point.get("type") in ("waypoint", "takeoff", "rtl") and cmd is None

        def _find_prev_navigation_index(index: int, minimum: int) -> int:
            i = min(index, len(mission_points) - 1)
            while i > minimum and not _is_navigation_point(mission_points[i]):
                i -= 1
            return max(i, minimum)

        def _extend_end_including_attached_actions(index: int) -> int:
            i = max(min(index, len(mission_points) - 1), 0)
            # Include any following non-navigation points (attached to this navigation point)
            while i + 1 < len(mission_points) and not _is_navigation_point(mission_points[i + 1]):
                i += 1
            return i

        for segment_index in range(segments_count):
            if total_distance > 0:
                segment_start_target = (total_distance / segments_count) * segment_index
                segment_end_target = (
                    total_distance
                    if segment_index == segments_count - 1
                    else (total_distance / segments_count) * (segment_index + 1)
                )
                start_index = SurveillanceProfileService._find_waypoint_index_by_distance(
                    cumulative_distances,
                    segment_start_target,
                    previous_end_index + 1,
                )
                end_index = SurveillanceProfileService._find_waypoint_index_by_distance(
                    cumulative_distances,
                    segment_end_target,
                    start_index,
                )
            else:
                start_index = min(
                    int((len(mission_points) - 1) * segment_index / segments_count),
                    len(mission_points) - 1,
                )
                end_index = min(
                    int((len(mission_points) - 1) * (segment_index + 1) / segments_count),
                    len(mission_points) - 1,
                )

            if start_index <= previous_end_index:
                start_index = min(previous_end_index + 1, len(mission_points) - 1)
            if end_index < start_index:
                end_index = start_index
            if segment_index == segments_count - 1:
                end_index = len(mission_points) - 1

            # --- Pair-safe boundary adjustment (waypoint + attached action commands) ---
            # Ensure segment starts at a navigation point (not at an action command).
            if not _is_navigation_point(mission_points[start_index]):
                start_index = _find_prev_navigation_index(start_index, previous_end_index + 1)

            # Ensure segment ends at a navigation point, then extend to include its attached actions.
            if not _is_navigation_point(mission_points[end_index]):
                end_index = _find_prev_navigation_index(end_index, start_index)
            end_index = _extend_end_including_attached_actions(end_index)

            # Avoid overlapping with next segment start
            if end_index < start_index:
                end_index = start_index
            # -------------------------------------------------------------------------

            segment_points = mission_points[start_index : end_index + 1]
            if not segment_points:
                segment_points = [mission_points[min(start_index, len(mission_points) - 1)]]

            path_distance_km = SurveillanceProfileService._calculate_path_distance(segment_points)

            segments.append(
                {
                    "start_point": segment_points[0],
                    "end_point": segment_points[-1],
                    "points": segment_points,
                    "path_distance_km": path_distance_km,
                }
            )

            previous_end_index = end_index

        return segments

    @staticmethod
    def _format_estimation_failure_reasons(estimation: Dict[str, Any], distance_m: float) -> str:
        """Build a translated, human-readable explanation for can_complete=False."""
        distance_m_value = SurveillanceProfileService._safe_number(distance_m, float) or 0.0
        distance_km = round(distance_m_value / 1000.0, 2)

        cruise_speed_ms = SurveillanceProfileService._safe_number(
            estimation.get("cruise_speed_ms") if isinstance(estimation, dict) else None,
            float,
        )
        estimated_duration_s = SurveillanceProfileService._safe_number(
            estimation.get("estimated_duration_s") if isinstance(estimation, dict) else None,
            float,
        )
        flight_time_s = SurveillanceProfileService._safe_number(
            estimation.get("flight_time_s") if isinstance(estimation, dict) else None,
            float,
        )
        maximum_range_m = SurveillanceProfileService._safe_number(
            estimation.get("maximum_range_m") if isinstance(estimation, dict) else None,
            float,
        )
        wind_speed_ms = SurveillanceProfileService._safe_number(
            estimation.get("wind_speed_ms") if isinstance(estimation, dict) else None,
            float,
        )
        wind_resistance_ms = SurveillanceProfileService._safe_number(
            estimation.get("wind_resistance_ms") if isinstance(estimation, dict) else None,
            float,
        )

        reasons: List[str] = []

        if cruise_speed_ms is None or cruise_speed_ms <= 0:
            reasons.append(get_message(MESSAGE_ENUM.SURVEILLANCE_ESTIMATION_FAIL_MISSING_CRUISE_SPEED))

        if estimated_duration_s is None:
            # If cruise speed is present but duration still missing, fall back to unknown.
            if cruise_speed_ms is not None and cruise_speed_ms > 0:
                reasons.append(get_message(MESSAGE_ENUM.SURVEILLANCE_ESTIMATION_FAIL_UNKNOWN))
        else:
            if flight_time_s is None:
                reasons.append(get_message(MESSAGE_ENUM.SURVEILLANCE_ESTIMATION_FAIL_MISSING_FLIGHT_TIME))
            else:
                if estimated_duration_s > flight_time_s:
                    reasons.append(
                        get_message(MESSAGE_ENUM.SURVEILLANCE_ESTIMATION_FAIL_BATTERY_TIME).format(
                            estimated_min=round(estimated_duration_s / 60.0, 2),
                            flight_time_min=round(flight_time_s / 60.0, 2),
                        )
                    )

        if maximum_range_m is not None and distance_m_value > maximum_range_m:
            reasons.append(
                get_message(MESSAGE_ENUM.SURVEILLANCE_ESTIMATION_FAIL_RANGE).format(
                    distance_km=distance_km,
                    max_range_km=round(maximum_range_m / 1000.0, 2),
                )
            )

        if (
            wind_speed_ms is not None
            and wind_resistance_ms is not None
            and wind_speed_ms > wind_resistance_ms
        ):
            reasons.append(
                get_message(MESSAGE_ENUM.SURVEILLANCE_ESTIMATION_FAIL_WIND).format(
                    wind_ms=round(wind_speed_ms, 2),
                    resistance_ms=round(wind_resistance_ms, 2),
                )
            )

        reasons = [reason for reason in reasons if reason]
        if not reasons:
            reasons.append(get_message(MESSAGE_ENUM.SURVEILLANCE_ESTIMATION_FAIL_UNKNOWN))

        return "; ".join(reasons)

    @staticmethod
    def _assign_segments_for_candidates(
        segment_templates: List[Dict[str, Any]],
        candidate_tuple: Iterable[Dict[str, Any]],
        fallback_cruise_speed: Optional[float],
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        candidate_list = list(candidate_tuple)
        candidates = [
            {
                "device": candidate.get("device", {}).copy(),
                "instance": candidate.get("instance"),
            }
            for candidate in candidate_list
            if candidate.get("device") and candidate.get("instance")
        ]
        if len(candidates) != len(candidate_list):
            if diagnostics is not None:
                diagnostics["segment_failure"] = {
                    "segment_index": 1,
                    "distance_km": 0.0,
                    "example": get_message(MESSAGE_ENUM.SURVEILLANCE_ESTIMATION_FAIL_UNKNOWN),
                }
            return None

        remaining_candidates = candidates.copy()
        assigned_segments: List[Dict[str, Any]] = []
        estimation_cache: Dict[Tuple[int, float], Dict[str, Any]] = {}

        for template_index, template in enumerate(segment_templates, start=1):
            assigned_segment: Optional[Dict[str, Any]] = None
            points = template.get("points") or []
            if not points:
                continue
            start_point = points[0]
            start_lat = SurveillanceProfileService._safe_number(start_point.get("lat"), float)
            start_lon = SurveillanceProfileService._safe_number(start_point.get("lon"), float)

            failure_example: Optional[str] = None
            failure_distance_km: Optional[float] = None
            for idx, candidate in enumerate(list(remaining_candidates)):
                device_info = candidate.get("device") or {}
                device_instance = candidate.get("instance")
                device_id = device_info.get("id") if isinstance(device_info, dict) else None
                if device_instance is None or device_id is None:
                    continue

                takeoff_distance_km = 0.0
                takeoff_lat = SurveillanceProfileService._safe_number(device_info.get("terminal_latitude"), float)
                takeoff_lon = SurveillanceProfileService._safe_number(device_info.get("terminal_longitude"), float)
                if (
                    takeoff_lat is not None
                    and takeoff_lon is not None
                    and start_lat is not None
                    and start_lon is not None
                ):
                    try:
                        takeoff_distance_km = geodesic(
                            (takeoff_lat, takeoff_lon),
                            (start_lat, start_lon),
                        ).kilometers
                    except (ValueError, TypeError):
                        takeoff_distance_km = 0.0
                segment_distance_km = max(template.get("path_distance_km") or 0.0, 0.0) + takeoff_distance_km
                distance_m = segment_distance_km * 1000.0
                cache_key = (device_id, round(distance_m, 3))
                if cache_key in estimation_cache:
                    estimation = estimation_cache[cache_key]
                else:
                    estimation = FlightEstimationService.estimate_duration_for_distance(
                        device_instance,
                        distance_m,
                        default_cruise_speed=fallback_cruise_speed,
                    )
                    estimation_cache[cache_key] = estimation
                if estimation.get("can_complete"):
                    duration_s = estimation.get("estimated_duration_s")
                    estimated_time_minutes = (
                        round(float(duration_s) / 60.0, 2)
                        if duration_s is not None
                        else None
                    )

                    if (
                        estimated_time_minutes is None
                        and fallback_cruise_speed is not None
                        and fallback_cruise_speed > 0
                    ):
                        time_seconds = distance_m / fallback_cruise_speed if distance_m > 0 else 0.0
                        estimated_time_minutes = round(time_seconds / 60.0, 2)

                    assigned_segment = {
                        "start_point": start_point,
                        "end_point": points[-1],
                        "points": points,
                        "distance_km": segment_distance_km,
                        "path_distance_km": template.get("path_distance_km") or 0.0,
                        "takeoff_distance_km": takeoff_distance_km,
                        "estimated_time_minutes": estimated_time_minutes,
                        "flight_estimation": estimation,
                        "assigned_device": device_info.copy(),
                    }

                    assigned_segments.append(assigned_segment)
                    remaining_candidates.pop(idx)
                    break
                else:
                    if failure_example is None:
                        drone_name = None
                        if isinstance(device_info, dict):
                            drone_name = device_info.get("name") or device_info.get("serial_number")
                        if not drone_name:
                            drone_name = str(device_id)

                        reasons = SurveillanceProfileService._format_estimation_failure_reasons(
                            estimation or {},
                            distance_m,
                        )
                        failure_example = get_message(
                            MESSAGE_ENUM.SURVEILLANCE_AVAILABLE_DEVICES_DRONE_CANNOT_COMPLETE
                        ).format(drone_name=drone_name, reasons=reasons)
                        failure_distance_km = round(float(segment_distance_km), 2)

            if not assigned_segment:
                if diagnostics is not None:
                    diagnostics["segment_failure"] = {
                        "segment_index": template_index,
                        "distance_km": (
                            failure_distance_km
                            if failure_distance_km is not None
                            else round(float(template.get("path_distance_km") or 0.0), 2)
                        ),
                        "example": failure_example
                        or get_message(MESSAGE_ENUM.SURVEILLANCE_ESTIMATION_FAIL_UNKNOWN),
                    }
                return None

        return assigned_segments

    @staticmethod
    def download_log(profile_drone_id: int):
        """Download log file for a surveillance profile drone.
        
        Returns:
            Tuple[bool, Optional[bytes], Optional[str]]: (success, file_content, filename) or (False, None, None) on failure
        """
        try:
            profile_drone = SurveillanceProfileDrone.objects.get(id=profile_drone_id)
            log_path = profile_drone.log_path
            if not log_path:
                logger.warning(f"No log_path found for profile_drone {profile_drone_id}")
                return False, None, None
            
            # Construct download URL
            # Accept both full URL and object key (legacy compatibility)
            log_path_clean = str(log_path).strip()
            if log_path_clean.startswith("http://") or log_path_clean.startswith("https://"):
                download_url = log_path_clean
            else:
                # Remove leading slash if present to avoid double slashes
                log_path_clean = log_path_clean.lstrip('/')
                download_url = f'https://{settings.MINIO_ENDPOINT}/{settings.MINIO_STORAGE_MEDIA_BUCKET_NAME}/{log_path_clean}'
            
            response = requests.get(download_url, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to download log from {download_url}, status: {response.status_code}")
                return False, None, None
            
            # Extract filename from path
            filename = os.path.basename(log_path) or f"log_{profile_drone_id}.tlog"
            
            return True, response.content, filename
            
        except SurveillanceProfileDrone.DoesNotExist:
            logger.error(f"SurveillanceProfileDrone with id {profile_drone_id} not found")
            return False, None, None
        except Exception as exc:
            logger.exception(f"Error downloading log for surveillance profile drone {profile_drone_id}: {exc}")
            return False, None, None

    @staticmethod
    def download_analysis(profile_drone_id: int):
        """Download log file for a surveillance profile drone.
        
        Returns:
            Tuple[bool, Optional[bytes], Optional[str]]: (success, file_content, filename) or (False, None, None) on failure
        """
        try:
            profile_drone = SurveillanceProfileDrone.objects.get(id=profile_drone_id)
            log_path = profile_drone.analysis_path
            if not log_path:
                logger.warning(f"No log_path found for profile_drone {profile_drone_id}")
                return False, None, None
            
            # Construct download URL
            # Accept both full URL and object key (legacy compatibility)
            log_path_clean = str(log_path).strip()
            if log_path_clean.startswith("http://") or log_path_clean.startswith("https://"):
                download_url = log_path_clean
            else:
                # Remove leading slash if present to avoid double slashes
                log_path_clean = log_path_clean.lstrip('/')
                download_url = f'https://{settings.MINIO_ENDPOINT}/{settings.MINIO_STORAGE_MEDIA_BUCKET_NAME}/{log_path_clean}'
            
            response = requests.get(download_url, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to download log from {download_url}, status: {response.status_code}")
                return False, None, None
            
            # Extract filename from path
            filename = os.path.basename(log_path) or f"log_{profile_drone_id}"
            
            return True, response.content, filename
            
        except SurveillanceProfileDrone.DoesNotExist:
            logger.error(f"SurveillanceProfileDrone with id {profile_drone_id} not found")
            return False, None, None
        except Exception as exc:
            logger.exception(f"Error downloading log for surveillance profile drone {profile_drone_id}: {exc}")
            return False, None, None

    @staticmethod
    def get_video_analyses_for_profile(profile_id: int):
        """Return queryset of VideoAnalysis records for a given SurveillanceProfile."""
        from surveillance.models import VideoAnalysis
        return (
            VideoAnalysis.objects.filter(
                profile_device__profile_id=profile_id,
                analysis_path__isnull=False,
            )
            .exclude(analysis_path="")
            .order_by("-updated_at")
        )