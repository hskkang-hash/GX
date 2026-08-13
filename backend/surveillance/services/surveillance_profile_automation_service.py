"""Automation services for surveillance profile scheduling and notifications."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction, connections
from django.utils import timezone
from django.db import close_old_connections
from django.db.utils import OperationalError, InterfaceError
import pytz

from surveillance.models import SurveillanceProfile, SurveillanceStatus
from common.utils import get_gcs_api_headers

import requests


logger = logging.getLogger(__name__)


class SurveillanceProfileAutomationService:
    """Service layer helpers for delayed surveillance profile activation."""

    DEFAULT_PREFLIGHT_OFFSET_MINUTES: int = 5
    PREFLIGHT_TOLERANCE_SECONDS: int = 75
    BATCH_SIZE: int = 200

    _status_cache: Dict[str, SurveillanceStatus] = {}

    @classmethod
    def apply_auto_launch_metadata(
        cls,
        *,
        metadata: Dict[str, Any],
        profile: SurveillanceProfile,
        is_not_yet: bool,
        timestamp,
    ) -> Dict[str, Any]:
        """
        Update profile metadata to reflect auto-launch readiness state.

        When `is_not_yet` is True, we flag the profile for scheduled activation.
        Otherwise, the auto-launch state is cleared.
        """

        auto_launch: Dict[str, Any] = metadata.get("auto_launch") or {}

        offset_minutes = auto_launch.get("preflight_offset_minutes")
        if not offset_minutes or offset_minutes <= 0:
            offset_minutes = cls.DEFAULT_PREFLIGHT_OFFSET_MINUTES

        start_time = profile.start_time
        if start_time and timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time, timezone.get_current_timezone())

        start_time_iso: Optional[str] = cls._format_datetime_for_metadata(start_time, profile) if start_time else None

        if is_not_yet and start_time:
            auto_launch.update(
                {
                    "not_yet": True,
                    "preflight_offset_minutes": offset_minutes,
                    "preflight_sent": False,
                    "preflight_sent_at": None,
                    "preflight_skipped": False,
                    "preflight_skip_reason": None,
                    "activation_processed": False,
                    "activation_processed_at": None,
                    "start_time_snapshot": start_time_iso,
                }
            )
            auto_launch.pop("processing", None)
        elif is_not_yet and not start_time:
            logger.warning(
                "[SURVEILLANCE][AUTO] Profile %s flagged for delayed takeoff without start_time",
                profile.id,
            )
            auto_launch.update({
                "not_yet": False,
                "start_time_snapshot": start_time_iso,
            })
            auto_launch.pop("processing", None)
        else:
            auto_launch.update(
                {
                    "not_yet": False,
                    "start_time_snapshot": start_time_iso,
                }
            )
            auto_launch.pop("processing", None)

        auto_launch.pop("enabled", None)
        auto_launch.pop("ready", None)

        auto_launch["last_updated_at"] = cls._format_datetime_for_metadata(timestamp, profile)
        metadata["auto_launch"] = auto_launch
        metadata["not_yet"] = is_not_yet
        return metadata

    @classmethod
    def clear_auto_launch(
        cls,
        profile: SurveillanceProfile,
        *,
        timestamp,
        reason: Optional[str] = None,
        persist: bool = True,
    ) -> bool:
        """Disable auto-launch flags while preserving existing history fields."""

        metadata = profile.metadata or {}
        auto_launch = metadata.get("auto_launch")
        if not auto_launch:
            return False

        iso_timestamp = cls._format_datetime_for_metadata(timestamp, profile)

        auto_launch.update(
            {
                "not_yet": False,
                "last_updated_at": iso_timestamp,
                "cleared_at": iso_timestamp,
            }
        )
        auto_launch.pop("processing", None)
        auto_launch.pop("enabled", None)
        auto_launch.pop("ready", None)

        # Ensure commonly accessed flags exist for consistency even when disabled
        auto_launch.setdefault("preflight_sent", False)
        auto_launch.setdefault("preflight_skipped", False)
        auto_launch.setdefault("activation_processed", False)
        auto_launch.setdefault("not_yet", False)

        start_time = profile.start_time
        if start_time and timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time, timezone.get_current_timezone())
        auto_launch.setdefault("start_time_snapshot", cls._format_datetime_for_metadata(start_time, profile) if start_time else None)

        metadata["auto_launch"] = auto_launch
        metadata["not_yet"] = False
        profile.metadata = metadata
        profile.not_yet = False

        if persist:
            profile.save(update_fields=["metadata", "modified_on", "not_yet"])

        return True

    @classmethod
    def process_auto_launch(cls, now=None) -> Dict[str, List[Dict[str, Any]]]:
        """Process preflight notifications and activation transitions."""

        now = now or timezone.now()

        # Cleanup các activation task cũ không còn hợp lệ
        cls._cleanup_invalid_activation_tasks(now)

        preflight_payloads: List[Dict[str, Any]] = []
        activation_payloads: List[Dict[str, Any]] = []
        activation_dispatch_ids: List[int] = []

        while True:
            batch = cls._process_preflight_batch(now)
            if not batch:
                break
            preflight_payloads.extend(batch)
            if len(batch) < cls.BATCH_SIZE:
                break

        # Fetch GCS data once for all activation batches with timeout
        available_unit_ids_cache = []
        try:
            from surveillance.services.surveillance_profile_service import SurveillanceProfileService
            # Use shorter timeout to avoid blocking task too long
            FLIGHT_BIRD_URL = os.environ.get('FLIGHTBRID_URL')
            if FLIGHT_BIRD_URL:
                headers = get_gcs_api_headers()
                response = requests.get(f"{FLIGHT_BIRD_URL}/api/drone/drones/full-battery", headers=headers, timeout=5)
                if response.status_code == 200:
                    drones = response.json().get('drones', [])
                    available_unit_ids_cache = [drone.get('UniqueId') for drone in drones if drone.get('UniqueId')]
                else:
                    logger.warning("[SURVEILLANCE][AUTO] GCS returned status %s", response.status_code)
        except requests.Timeout:
            logger.warning("[SURVEILLANCE][AUTO] GCS request timeout, continuing without availability check")
        except Exception as exc:
            logger.warning("[SURVEILLANCE][AUTO] Failed to fetch available devices from GCS: %s", exc)
        
        while True:
            batch_payloads, batch_dispatch_ids = cls._process_activation_batch(now, available_unit_ids_cache=available_unit_ids_cache)
            if not batch_payloads:
                break
            activation_payloads.extend(batch_payloads)
            activation_dispatch_ids.extend(batch_dispatch_ids)
            if len(batch_payloads) < cls.BATCH_SIZE:
                break

        if preflight_payloads:
            cls._broadcast_event("surveillance_preflight", preflight_payloads)

        if activation_dispatch_ids:
            cls._dispatch_profiles_to_flightbridge(activation_dispatch_ids)

        return {"preflight": preflight_payloads, "activation": activation_payloads}
    
    @classmethod
    def _check_drone_availability(cls, profile: SurveillanceProfile, available_unit_ids_set: Optional[set] = None) -> Tuple[bool, Optional[str]]:
        """
        Check if all drones in profile are available with 100% battery.
        
        Args:
            profile: SurveillanceProfile to check
            available_unit_ids_set: Optional cached set of available unit IDs from GCS
        
        Returns:
            Tuple[bool, Optional[str]]: (is_available, error_message)
        """
        try:
            # Use cached GCS data if provided, otherwise fetch
            if available_unit_ids_set is None:
                from surveillance.services.surveillance_profile_service import SurveillanceProfileService
                available_unit_ids = SurveillanceProfileService.fetch_available_device_from_gcs()
                if not available_unit_ids:
                    return False, "No drones available from GCS"
                available_unit_ids_set = set(available_unit_ids)
            
            # Get all drone assignments for this profile using _base_manager to avoid filter
            from surveillance.models import SurveillanceProfileDrone
            from devices.models import Device
            # Use _base_manager for both SurveillanceProfileDrone and Device to avoid custom manager filters
            drone_assignments = SurveillanceProfileDrone._base_manager.filter(
                profile=profile
            ).select_related("device", "device__status")
            if not drone_assignments.exists():
                return False, "No drone assignments found"
            
            # Check each drone
            # Device is already loaded via select_related with _base_manager, so no additional query is made
            # This ensures device is loaded without filter from CustomManagerGroup
            for assignment in drone_assignments:
                # assignment.device is already loaded via select_related("device") with _base_manager
                # No new query will be triggered, device comes from the JOIN query
                device = assignment.device
                if not device:
                    return False, f"Drone assignment {assignment.id} has no device"
                
                # device.status is already loaded via select_related("device__status") with _base_manager
                # No new query will be triggered
                if not device.status or device.status.code != "available":
                    status_code = device.status.code if device.status else "unknown"
                    return False, f"Drone {device.unit_id} is not available (status: {status_code})"
                
                # Check if device has 100% battery (in available_unit_ids from GCS)
                if device.unit_id not in available_unit_ids_set:
                    return False, f"Drone {device.unit_id} does not have 100% battery or is not available"
            
            return True, None
            
        except Exception as exc:
            logger.exception("[SURVEILLANCE][AUTO] Error checking drone availability: %s", exc)
            return False, f"Error checking drone availability: {str(exc)}"
    
    @classmethod
    def _get_user_timezone(cls, profile: SurveillanceProfile) -> pytz.BaseTzInfo:
        """Get user timezone from profile creator.
        
        Optimized: Uses prefetched data from select_related to avoid additional queries.
        """
        try:
            user = None
            # Try to get from profile.created_by (already loaded via select_related)
            if hasattr(profile, 'created_by') and profile.created_by:
                user = profile.created_by
            # Fallback to mission.created_by (already loaded via select_related)
            elif hasattr(profile, 'mission') and profile.mission and hasattr(profile.mission, 'created_by') and profile.mission.created_by:
                user = profile.mission.created_by
            
            # If still no user, try querying (shouldn't happen if prefetch is correct)
            if not user:
                if hasattr(profile, 'created_by_id') and profile.created_by_id:
                    from core.user.models import CoreUser
                    try:
                        user = CoreUser._base_manager.select_related('timezone').get(id=profile.created_by_id)
                    except CoreUser.DoesNotExist:
                        pass
                if not user and hasattr(profile, 'mission_id') and profile.mission_id:
                    from surveillance.models import SurveyMission
                    try:
                        mission = SurveyMission._base_manager.select_related('created_by__timezone').get(id=profile.mission_id)
                        if hasattr(mission, 'created_by') and mission.created_by:
                            user = mission.created_by
                    except SurveyMission.DoesNotExist:
                        pass
            
            if user:
                # Try to get timezone from user.timezone
                if hasattr(user, 'timezone') and user.timezone:
                    tz_code = None
                    
                    # Priority 1: Use code field (most reliable)
                    if hasattr(user.timezone, 'code') and user.timezone.code:
                        tz_code = user.timezone.code
                    # Priority 2: Fallback to name if code not available
                    elif hasattr(user.timezone, 'name') and user.timezone.name:
                        tz_code = user.timezone.name
                    # Priority 3: If timezone is a string directly
                    elif isinstance(user.timezone, str):
                        tz_code = user.timezone
                    else:
                        tz_code = str(user.timezone)
                    
                    if tz_code:
                        try:
                            return pytz.timezone(tz_code)
                        except pytz.UnknownTimeZoneError:
                            logger.warning(
                                "[SURVEILLANCE][AUTO] Unknown timezone code '%s' for user %s, using default",
                                tz_code,
                                user.id,
                            )
            
            # Default to system timezone
            return timezone.get_current_timezone()
        except Exception as exc:
            logger.warning(
                "[SURVEILLANCE][AUTO] Error getting user timezone: %s, using default",
                exc,
            )
            return timezone.get_current_timezone()
    
    @classmethod
    def _convert_to_user_timezone(cls, dt: datetime, profile: SurveillanceProfile) -> datetime:
        """Convert datetime to user's timezone."""
        if dt is None:
            return None
        
        user_tz = cls._get_user_timezone(profile)
        
        # Ensure datetime is aware
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        
        # Convert to user timezone
        return dt.astimezone(user_tz)
    
    @classmethod
    def _format_datetime_for_metadata(cls, dt: datetime, profile: SurveillanceProfile) -> str:
        """Format datetime to ISO string in user's timezone for metadata storage."""
        if dt is None:
            return None
        
        user_tz_dt = cls._convert_to_user_timezone(dt, profile)
        return user_tz_dt.isoformat()
    
    @classmethod
    def _parse_datetime_from_metadata(cls, dt_str: str, profile: SurveillanceProfile) -> Optional[datetime]:
        """Parse datetime from metadata ISO string, assuming it's in user's timezone."""
        if not dt_str:
            return None
        
        try:
            # Parse ISO string
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            
            # If naive, assume it's in user's timezone
            if timezone.is_naive(dt):
                user_tz = cls._get_user_timezone(profile)
                dt = user_tz.localize(dt)
            
            # Convert to UTC for internal processing
            return dt.astimezone(pytz.UTC)
        except Exception as exc:
            logger.warning(
                "[SURVEILLANCE][AUTO] Error parsing datetime '%s': %s",
                dt_str,
                exc,
            )
            return None
    
    @classmethod
    def _log_activation_skipped(cls, profile: SurveillanceProfile, now, reason: str) -> None:
        """
        Log when activation is skipped due to drone unavailability.
        
        NOTE: No retry or auto-cancel here. Profile stays in pending_device_check status.
        Auto-cancel only happens via Overdue check (when profile runs too long in in_progress).
        """
        metadata = profile.metadata or {}
        auto_launch = metadata.get("auto_launch") or {}
        
        # Record the skip in metadata for debugging
        auto_launch["last_activation_skip"] = {
            "skipped_at": cls._format_datetime_for_metadata(now, profile),
            "reason": reason,
        }
        auto_launch["last_updated_at"] = cls._format_datetime_for_metadata(now, profile)
        metadata["auto_launch"] = auto_launch
        profile.metadata = metadata
        profile.save(update_fields=["metadata", "modified_on"])
        
        logger.warning(
            "[SURVEILLANCE][AUTO] Profile %s activation skipped - drone not available. Reason: %s",
            profile.id,
            reason,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _process_preflight_batch(cls, now) -> List[Dict[str, Any]]:
        upper_bound = now + timedelta(
            minutes=cls.DEFAULT_PREFLIGHT_OFFSET_MINUTES,
            seconds=cls.PREFLIGHT_TOLERANCE_SECONDS,
        )

        # NOTE: close_old_connections() đã được gọi tự động bởi task_prerun signal trong celery.py
        # Chỉ cần gọi lại khi retry sau SSL/connection errors

        with transaction.atomic():
            # Prefetch created_by__timezone to avoid N+1 queries in _get_user_timezone
            base_queryset = (
                SurveillanceProfile._base_manager.select_related(
                    "status",
                    "created_by",
                    "created_by__timezone",
                    "mission",
                    "mission__created_by",
                    "mission__created_by__timezone",
                )
                .only("id", "status_id", "metadata", "start_time", "device_count", "not_yet", "created_by_id", "mission_id")
                .filter(
                    not_yet=True,
                    metadata__auto_launch__not_yet=True,
                    metadata__auto_launch__preflight_sent=False,
                    metadata__auto_launch__processing__isnull=True,
                    start_time__isnull=False,
                    start_time__lte=upper_bound,
                )
                .order_by("start_time", "id")
            )

            # Retry logic để xử lý SSL/connection errors và AssertionError từ SQLAlchemy pool
            import time
            max_retries = 3
            candidate_ids = []
            for attempt in range(max_retries):
                try:
                    # Rebuild queryset mỗi lần retry để đảm bảo không dùng stale queryset
                    if attempt > 0:
                        base_queryset = (
                            SurveillanceProfile._base_manager.select_related(
                                "status",
                                "created_by",
                                "created_by__timezone",
                                "mission",
                                "mission__created_by",
                                "mission__created_by__timezone",
                            )
                            .only("id", "status_id", "metadata", "start_time", "device_count", "not_yet", "created_by_id", "mission_id")
                            .filter(
                                not_yet=True,
                                metadata__auto_launch__not_yet=True,
                                metadata__auto_launch__preflight_sent=False,
                                metadata__auto_launch__processing__isnull=True,
                                start_time__isnull=False,
                                start_time__lte=upper_bound,
                            )
                            .order_by("start_time", "id")
                        )
                    
                    candidate_ids = list(base_queryset.values_list("id", flat=True))
                    break  # Success, exit retry loop
                except AssertionError as e:
                    # AssertionError từ SQLAlchemy pool = connection đã chết trong pool
                    # Thường xảy ra khi start lại server với stale connections
                    if attempt < max_retries - 1:
                        logger.warning(
                            "[SURVEILLANCE][AUTO] SQLAlchemy pool AssertionError (stale connection) on attempt %s/%s, retrying: %s",
                            attempt + 1,
                            max_retries,
                            str(e)
                        )
                        # Close all connections và clear pool để force tạo connection mới
                        close_old_connections()
                        connections.close_all()
                        # Đợi một chút để pool refresh connection mới
                        time.sleep(0.1 * (attempt + 1))  # Exponential backoff: 0.1s, 0.2s, 0.3s
                        continue
                    else:
                        logger.error(
                            "[SURVEILLANCE][AUTO] SQLAlchemy pool AssertionError after %s attempts, giving up: %s",
                            max_retries,
                            str(e)
                        )
                        raise
                except (OperationalError, InterfaceError) as e:
                    error_msg = str(e).lower()
                    # Check if it's an SSL/connection error
                    if any(keyword in error_msg for keyword in ['ssl', 'connection', 'eof', 'closed', 'bad record', 'wrong version', 'syscall']):
                        if attempt < max_retries - 1:
                            logger.warning(
                                "[SURVEILLANCE][AUTO] SSL/Connection error on attempt %s/%s, retrying: %s",
                                attempt + 1,
                                max_retries,
                                str(e)
                            )
                            # Close all connections and retry
                            close_old_connections()
                            connections.close_all()
                            # Đợi một chút để pool refresh connection mới
                            time.sleep(0.1 * (attempt + 1))  # Exponential backoff: 0.1s, 0.2s, 0.3s
                            continue
                        else:
                            logger.error(
                                "[SURVEILLANCE][AUTO] SSL/Connection error after %s attempts, giving up: %s",
                                max_retries,
                                str(e)
                            )
                            raise
                    else:
                        # Not a connection error, re-raise immediately
                        raise
                except Exception as e:
                    # Các lỗi khác không liên quan đến connection, re-raise ngay
                    logger.error(
                        "[SURVEILLANCE][AUTO] Unexpected error on attempt %s/%s: %s",
                        attempt + 1,
                        max_retries,
                        str(e)
                    )
                    raise
            if not candidate_ids:
                return []

            # Use select_for_update to prevent race conditions
            locked_queryset = (
                SurveillanceProfile._base_manager
                .select_related(
                    "status",
                    "created_by",
                    "created_by__timezone",
                    "mission",
                    "mission__created_by",
                    "mission__created_by__timezone",
                )
                .only("id", "status_id", "metadata", "start_time", "device_count", "not_yet", "created_by_id", "mission_id")
                .filter(
                    id__in=candidate_ids,
                    not_yet=True,
                    metadata__auto_launch__not_yet=True,
                    metadata__auto_launch__preflight_sent=False,
                    start_time__isnull=False,
                    start_time__lte=upper_bound,
                )
                .order_by("start_time", "id")
            )

            candidates = list(locked_queryset)
            if not candidates:
                return []

            payloads: List[Dict[str, Any]] = []

            for profile in candidates:
                start_time = profile.start_time
                if start_time and timezone.is_naive(start_time):
                    start_time = timezone.make_aware(start_time, timezone.get_current_timezone())

                if not start_time:
                    cls._mark_preflight_skipped(profile, now, reason="missing_start_time")
                    continue

                metadata = profile.metadata or {}
                auto_launch = metadata.get("auto_launch") or {}
                offset_minutes = auto_launch.get("preflight_offset_minutes") or cls.DEFAULT_PREFLIGHT_OFFSET_MINUTES
                diff_seconds = (start_time - now).total_seconds()

                if not cls._set_processing_flag(profile, now, scope="preflight"):
                    continue

                # Update auto_launch with preflight info (don't re-read metadata)
                auto_launch["preflight_sent"] = True
                auto_launch["preflight_sent_at"] = cls._format_datetime_for_metadata(now, profile)
                auto_launch["preflight_skipped"] = False
                auto_launch["last_updated_at"] = cls._format_datetime_for_metadata(now, profile)
                auto_launch.pop("processing", None)
                metadata["auto_launch"] = auto_launch
                metadata["not_yet"] = True

                profile.metadata = metadata
                profile.save(update_fields=["metadata", "modified_on"])

                payloads.append(cls._build_profile_payload(profile, start_time=start_time, diff_seconds=diff_seconds))

            return payloads

    @classmethod
    def _process_activation_batch(cls, now, available_unit_ids_cache: Optional[List[str]] = None) -> Tuple[List[Dict[str, Any]], List[int]]:
        # NOTE: close_old_connections() đã được gọi tự động bởi task_prerun signal trong celery.py
        # Chỉ cần gọi lại khi retry sau SSL/connection errors
        
        # Cache GCS call - fetch once for entire batch
        if available_unit_ids_cache is None:
            try:
                from surveillance.services.surveillance_profile_service import SurveillanceProfileService
                available_unit_ids_cache = SurveillanceProfileService.fetch_available_device_from_gcs()
            except Exception as exc:
                logger.warning("[SURVEILLANCE][AUTO] Failed to fetch available devices from GCS: %s", exc)
                available_unit_ids_cache = []
        
        available_unit_ids_set = set(available_unit_ids_cache) if available_unit_ids_cache else set()
        
        with transaction.atomic():
            from django.db.models import Q, Prefetch
            from surveillance.models import SurveillanceProfileDrone
            from devices.models import Device, DeviceStatus
            
            # Use Prefetch with _base_manager to avoid filter in background task
            drone_prefetch = Prefetch(
                "drone_assignments",
                queryset=SurveillanceProfileDrone._base_manager.select_related(
                    "device", "device__status"
                )
            )
            
            # Prefetch created_by__timezone to avoid N+1 queries
            base_queryset = (
                SurveillanceProfile._base_manager.select_related(
                    "status",
                    "created_by",
                    "created_by__timezone",
                    "mission",
                    "mission__created_by",
                    "mission__created_by__timezone",
                )
                .prefetch_related(drone_prefetch)
                .only("id", "status_id", "metadata", "start_time", "device_count", "not_yet", "created_by_id", "mission_id")
                .filter(
                    not_yet=True,
                    metadata__auto_launch__not_yet=True,
                    metadata__auto_launch__activation_processed=False,
                    metadata__auto_launch__processing__isnull=True,
                    start_time__isnull=False,
                    actual_end_time__isnull=True,
                    status__code__in=["pending_device_check"],
                )
                .order_by("start_time", "id")
            )

            # Retry logic để xử lý SSL/connection errors và AssertionError từ SQLAlchemy pool
            import time
            max_retries = 3
            candidate_ids = []
            for attempt in range(max_retries):
                try:
                    # Rebuild queryset mỗi lần retry để đảm bảo không dùng stale queryset
                    if attempt > 0:
                        base_queryset = (
                            SurveillanceProfile._base_manager.select_related(
                                "status",
                                "created_by",
                                "created_by__timezone",
                                "mission",
                                "mission__created_by",
                                "mission__created_by__timezone",
                            )
                            .prefetch_related(drone_prefetch)
                            .only("id", "status_id", "metadata", "start_time", "device_count", "not_yet", "created_by_id", "mission_id")
                            .filter(
                                not_yet=True,
                                metadata__auto_launch__not_yet=True,
                                metadata__auto_launch__activation_processed=False,
                                metadata__auto_launch__processing__isnull=True,
                                start_time__isnull=False,
                                actual_end_time__isnull=True,
                                status__code__in=["pending_device_check"],
                            )
                            .order_by("start_time", "id")
                        )
                    
                    candidate_ids = list(base_queryset.values_list("id", flat=True)[: cls.BATCH_SIZE])
                    break  # Success, exit retry loop
                except AssertionError as e:
                    # AssertionError từ SQLAlchemy pool = connection đã chết trong pool
                    # Thường xảy ra khi start lại server với stale connections
                    if attempt < max_retries - 1:
                        logger.warning(
                            "[SURVEILLANCE][AUTO] SQLAlchemy pool AssertionError (stale connection) on attempt %s/%s, retrying: %s",
                            attempt + 1,
                            max_retries,
                            str(e)
                        )
                        # Close all connections và clear pool để force tạo connection mới
                        close_old_connections()
                        connections.close_all()
                        # Đợi một chút để pool refresh connection mới
                        time.sleep(0.1 * (attempt + 1))  # Exponential backoff: 0.1s, 0.2s, 0.3s
                        continue
                    else:
                        logger.error(
                            "[SURVEILLANCE][AUTO] SQLAlchemy pool AssertionError after %s attempts, giving up: %s",
                            max_retries,
                            str(e)
                        )
                        raise
                except (OperationalError, InterfaceError) as e:
                    error_msg = str(e).lower()
                    # Check if it's an SSL/connection error
                    if any(keyword in error_msg for keyword in ['ssl', 'connection', 'eof', 'closed', 'bad record', 'wrong version', 'syscall']):
                        if attempt < max_retries - 1:
                            logger.warning(
                                "[SURVEILLANCE][AUTO] SSL/Connection error on attempt %s/%s, retrying: %s",
                                attempt + 1,
                                max_retries,
                                str(e)
                            )
                            # Close all connections and retry
                            close_old_connections()
                            connections.close_all()
                            # Đợi một chút để pool refresh connection mới
                            time.sleep(0.1 * (attempt + 1))  # Exponential backoff: 0.1s, 0.2s, 0.3s
                            continue
                        else:
                            logger.error(
                                "[SURVEILLANCE][AUTO] SSL/Connection error after %s attempts, giving up: %s",
                                max_retries,
                                str(e)
                            )
                            raise
                    else:
                        # Not a connection error, re-raise immediately
                        raise
                except Exception as e:
                    # Các lỗi khác không liên quan đến connection, re-raise ngay
                    logger.error(
                        "[SURVEILLANCE][AUTO] Unexpected error on attempt %s/%s: %s",
                        attempt + 1,
                        max_retries,
                        str(e)
                    )
                    raise
            if not candidate_ids:
                return [], []

            locked_queryset = (
                SurveillanceProfile._base_manager.select_for_update(of=("self",), skip_locked=True)
                .select_related(
                    "status",
                    "created_by",
                    "created_by__timezone",
                    "mission",
                    "mission__created_by",
                    "mission__created_by__timezone",
                )
                .prefetch_related(drone_prefetch)
                .only("id", "status_id", "metadata", "start_time", "device_count", "not_yet", "created_by_id", "mission_id")
                .filter(
                    id__in=candidate_ids,
                    not_yet=True,
                    metadata__auto_launch__not_yet=True,
                    metadata__auto_launch__activation_processed=False,
                )
                .order_by("start_time", "id")
            )

            candidates = list(locked_queryset)
            if not candidates:
                return [], []

            in_process_status = cls._get_status_by_code("in_progress")
            if not in_process_status:
                in_process_status = cls._get_status_by_code("in_process")

            if not in_process_status:
                logger.error("[SURVEILLANCE][AUTO] Missing activation status code; activation skipped")
                return [], []

            payloads: List[Dict[str, Any]] = []
            dispatch_ids: List[int] = []

            for profile in candidates:
                start_time = profile.start_time
                # Ensure start_time is timezone-aware for proper comparison
                if start_time and timezone.is_naive(start_time):
                    start_time = timezone.make_aware(start_time, timezone.get_current_timezone())

                metadata = profile.metadata or {}
                auto_launch = metadata.get("auto_launch") or {}
                
                # Kiểm tra xem đã có scheduled task chưa để tránh duplicate activation
                activation_scheduled = metadata.get("activation_scheduled", {})
                scheduled_task_id = activation_scheduled.get("task_id")
                scheduled_for_str = activation_scheduled.get("scheduled_for")
                
                if scheduled_task_id and scheduled_for_str:
                    try:
                        from django.utils.dateparse import parse_datetime
                        scheduled_for = parse_datetime(scheduled_for_str)
                        if scheduled_for:
                            if timezone.is_naive(scheduled_for):
                                scheduled_for = timezone.make_aware(scheduled_for, timezone.get_current_timezone())
                            
                            # Nếu scheduled task sẽ chạy trong vòng 2 phút tới, để scheduled task xử lý
                            # Tránh race condition giữa process_auto_launch và activate_surveillance_profile
                            now_aware = now if timezone.is_aware(now) else timezone.make_aware(now, timezone.get_current_timezone())
                            time_diff = (scheduled_for - now_aware).total_seconds()
                            
                            if -60 <= time_diff <= 120:  # Trong khoảng 1 phút trước đến 2 phút sau
                                logger.info(
                                    "[SURVEILLANCE][AUTO] Profile %s đã có scheduled task %s sẽ chạy lúc %s, bỏ qua activation trong process_auto_launch",
                                    profile.id,
                                    scheduled_task_id,
                                    scheduled_for.isoformat(),
                                )
                                continue
                    except Exception as parse_exc:
                        logger.warning(
                            "[SURVEILLANCE][AUTO] Không thể parse scheduled_for cho profile %s: %s",
                            profile.id,
                            parse_exc,
                        )
                        # Tiếp tục xử lý nếu không parse được
                
                # Ensure now is timezone-aware for proper comparison
                now_aware = now if timezone.is_aware(now) else timezone.make_aware(now, timezone.get_current_timezone())
                
                # Check if start_time has arrived
                if start_time and start_time > now_aware:
                    continue  # Skip, start_time not reached yet
                
                if not cls._set_processing_flag(profile, now, scope="activation"):
                    continue

                # Validate drone availability before dispatch - use cached GCS data
                is_available, error_message = cls._check_drone_availability(profile, available_unit_ids_set=available_unit_ids_set)
                if not is_available:
                    # Just log and skip - no retry scheduling
                    # Auto-cancel will happen via Overdue check if profile stays stuck
                    cls._log_activation_skipped(profile, now, error_message or "Drone availability check failed")
                    cls._clear_processing_flag(profile)
                    continue

                # Update auto_launch with activation info (don't re-read metadata)
                auto_launch.update(
                    {
                        "not_yet": False,
                        "activation_processed": True,
                        "activation_processed_at": cls._format_datetime_for_metadata(now, profile),
                        "last_updated_at": cls._format_datetime_for_metadata(now, profile),
                    }
                )
                auto_launch.pop("processing", None)
                metadata["auto_launch"] = auto_launch
                metadata["not_yet"] = False

                profile.not_yet = False
                profile.metadata = metadata
                if profile.status_id != in_process_status.id:
                    profile.status = in_process_status
                    profile.save(update_fields=["metadata", "modified_on", "not_yet", "status"])
                else:
                    profile.save(update_fields=["metadata", "modified_on", "not_yet"])

                payloads.append(
                    cls._build_profile_payload(
                        profile,
                        start_time=start_time,
                        status_code=in_process_status.code if in_process_status else None,
                        diff_seconds=(start_time - now).total_seconds() if start_time else None,
                    )
                )
                dispatch_ids.append(profile.id)

            return payloads, dispatch_ids

    @classmethod
    def _mark_preflight_skipped(cls, profile: SurveillanceProfile, now, *, reason: str) -> None:
        metadata = profile.metadata or {}
        auto_launch = metadata.get("auto_launch") or {}
        auto_launch.update(
            {
                "not_yet": True,
                "preflight_sent": True,
                "preflight_skipped": True,
                "preflight_skip_reason": reason,
                "preflight_sent_at": cls._format_datetime_for_metadata(now, profile),
                "last_updated_at": cls._format_datetime_for_metadata(now, profile),
            }
        )
        metadata["auto_launch"] = auto_launch
        metadata["not_yet"] = True
        profile.metadata = metadata
        profile.not_yet = True
        profile.save(update_fields=["metadata", "modified_on", "not_yet"])

    @classmethod
    def _build_profile_payload(
        cls,
        profile: SurveillanceProfile,
        *,
        start_time,
        status_code: Optional[str] = None,
        diff_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        groups = list(profile.groups.all()) if hasattr(profile, "groups") else []
        group_codes = [getattr(group, "code", str(group.id)) for group in groups]
        group_ids = [group.id for group in groups if hasattr(group, "id")]

        if start_time and timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time, timezone.get_current_timezone())

        payload: Dict[str, Any] = {
            "profile_id": profile.id,
            "profile_code": profile.code,
            "profile_name": profile.name,
            "mission_id": profile.mission_id,
            "device_count": getattr(profile, "device_count", None),
            "start_time": start_time.isoformat() if start_time else None,
            "status_code": status_code or (profile.status.code if profile.status else None),
            "group_ids": group_ids,
            "group_codes": group_codes,
            "time_to_start_seconds": diff_seconds,
        }

        return payload

    @classmethod
    def _set_processing_flag(cls, profile: SurveillanceProfile, timestamp, *, scope: str) -> bool:
        metadata = profile.metadata or {}
        auto_launch = metadata.get("auto_launch") or {}

        processing = auto_launch.get("processing")
        if processing:
            started_at = processing.get("started_at")
            started_at_dt: Optional[datetime] = None
            try:
                if started_at:
                    started_at_dt = datetime.fromisoformat(started_at)
                    if started_at_dt and timezone.is_naive(started_at_dt):
                        started_at_dt = timezone.make_aware(started_at_dt, timezone.get_current_timezone())
            except Exception:
                started_at_dt = None

            if started_at_dt and timestamp - started_at_dt < timedelta(minutes=10):
                return False

        auto_launch["processing"] = {
            "scope": scope,
            "started_at": cls._format_datetime_for_metadata(timestamp, profile),
        }
        auto_launch["last_updated_at"] = cls._format_datetime_for_metadata(timestamp, profile)
        metadata["auto_launch"] = auto_launch
        profile.metadata = metadata
        profile.save(update_fields=["metadata", "modified_on"])
        return True

    @classmethod
    def _clear_processing_flag(cls, profile_or_id: Any) -> None:
        try:
            if isinstance(profile_or_id, SurveillanceProfile):
                profile = profile_or_id
            else:
                profile = SurveillanceProfile._base_manager.get(id=profile_or_id)
        except SurveillanceProfile.DoesNotExist:
            return

        metadata = profile.metadata or {}
        auto_launch = metadata.get("auto_launch") or {}
        if "processing" in auto_launch:
            auto_launch.pop("processing", None)
            auto_launch["last_updated_at"] = cls._format_datetime_for_metadata(timezone.now(), profile)

        metadata["auto_launch"] = auto_launch
        metadata["not_yet"] = auto_launch.get("not_yet", False)
        profile.metadata = metadata
        profile.not_yet = metadata["not_yet"]
        profile.save(update_fields=["metadata", "modified_on", "not_yet"])

    @classmethod
    def _dispatch_profiles_to_flightbridge(cls, profile_ids: List[int]) -> None:
        from surveillance.services.surveillance_profile_service import SurveillanceProfileService
        flightbridge_url = os.getenv("FLIGHTBRID_URL")
        if not flightbridge_url:
            logger.warning("[SURVEILLANCE][AUTO] FLIGHTBRID_URL not configured; skip dispatch")
            return

        endpoint_base = flightbridge_url.rstrip("/")

        for profile_id in profile_ids:
            detail_payload = SurveillanceProfileService.get_detail_payload(
                profile_id,
                use_base_manager=True,
            )

            if not detail_payload:
                logger.warning(
                    "[SURVEILLANCE][AUTO] Detail payload unavailable for profile %s; skipping dispatch",
                    profile_id,
                )
                cls._clear_processing_flag(profile_id)
                continue

            try:
                url = f"{endpoint_base}/api/surveillance/profile-detail"
                headers = get_gcs_api_headers()
                requests.post(url, json=detail_payload, headers=headers, timeout=3)
                logger.info(
                    "[SURVEILLANCE][AUTO] Dispatched profile %s to Flightbridge",
                    profile_id,
                )
                try:
                    profile_instance = SurveillanceProfile._base_manager.select_related("mission").get(id=profile_id)
                    SurveillanceProfileService.upload_profile_to_flightbird(profile_instance)
                except SurveillanceProfile.DoesNotExist:
                    logger.warning(
                        "[SURVEILLANCE][AUTO] Profile %s not found when uploading to Flightbird",
                        profile_id,
                    )
            except Exception as exc:
                logger.exception(
                    "[SURVEILLANCE][AUTO] Failed to dispatch profile %s to Flightbridge: %s",
                    profile_id,
                    exc,
                )
            finally:
                cls._clear_processing_flag(profile_id)

    @classmethod
    def refresh_start_time_snapshot(cls, profile: SurveillanceProfile, *, timestamp) -> bool:
        metadata = profile.metadata or {}
        auto_launch = metadata.get("auto_launch")
        if not auto_launch:
            return False

        if not auto_launch.get("not_yet"):
            return False

        start_time = profile.start_time
        if start_time and timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time, timezone.get_current_timezone())

        new_snapshot = cls._format_datetime_for_metadata(start_time, profile) if start_time else None

        if auto_launch.get("start_time_snapshot") == new_snapshot:
            return False

        auto_launch["start_time_snapshot"] = new_snapshot
        auto_launch["last_updated_at"] = cls._format_datetime_for_metadata(timestamp, profile)
        metadata["auto_launch"] = auto_launch
        profile.metadata = metadata
        profile.save(update_fields=["metadata", "modified_on"])
        return True

    @classmethod
    def _broadcast_event(cls, event_name: str, payloads: List[Dict[str, Any]]) -> None:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("[SURVEILLANCE][AUTO] Channel layer not configured; skip %s broadcast", event_name)
            return

        timestamp = timezone.now().isoformat()
        event_base = {
            "type": event_name,
            "timestamp": timestamp,
            "profiles": payloads,
        }

        try:
            async_to_sync(channel_layer.group_send)("surveillance_profiles_global", event_base)
        except Exception as exc:
            logger.exception("[SURVEILLANCE][AUTO] Failed to broadcast %s globally: %s", event_name, exc)

        group_map: Dict[str, List[Dict[str, Any]]] = {}
        for entry in payloads:
            for code in entry.get("group_codes", []):
                if not code:
                    continue
                group_map.setdefault(code, []).append(entry)

        for code, items in group_map.items():
            group_event = {
                "type": event_name,
                "timestamp": timestamp,
                "profiles": items,
            }
            group_name = f"surveillance_profiles_{code}"
            try:
                async_to_sync(channel_layer.group_send)(group_name, group_event)
            except Exception as exc:
                logger.exception(
                    "[SURVEILLANCE][AUTO] Failed to broadcast %s to %s: %s",
                    event_name,
                    group_name,
                    exc,
                )

    @classmethod
    def _get_status_by_code(cls, code: str) -> Optional[SurveillanceStatus]:
        if code in cls._status_cache:
            return cls._status_cache[code]

        status = SurveillanceStatus._base_manager.filter(code=code).first()
        if status:
            cls._status_cache[code] = status
        else:
            logger.error("[SURVEILLANCE][AUTO] Status with code '%s' not found", code)
        return status

    @classmethod
    def _cleanup_invalid_activation_tasks(cls, now=None) -> None:
        """
        Cleanup các activation task cũ không còn hợp lệ:
        - Profile không còn not_yet=True
        - start_time đã thay đổi khác với scheduled_for
        - Profile đã có actual_end_time
        - Task đã quá hạn quá lâu (> 5 phút)
        """
        now = now or timezone.now()
        if now.tzinfo != pytz.UTC:
            now = now.astimezone(pytz.UTC)
        
        from celery import current_app
        from django.utils.dateparse import parse_datetime
        
        try:
            # Tìm các profile có activation_scheduled nhưng không còn hợp lệ
            profiles = (
                SurveillanceProfile._base_manager
                .select_related("status")
                .filter(
                    metadata__activation_scheduled__isnull=False,
                )
            )
            
            cleaned_count = 0
            for profile in profiles[:cls.BATCH_SIZE]:  # Giới hạn để không block quá lâu
                try:
                    metadata = dict(profile.metadata or {})
                    activation_scheduled = metadata.get("activation_scheduled", {})
                    task_id = activation_scheduled.get("task_id")
                    scheduled_for_str = activation_scheduled.get("scheduled_for")
                    
                    if not task_id or not scheduled_for_str:
                        continue
                    
                    # Kiểm tra các điều kiện không hợp lệ
                    should_cleanup = False
                    reason = None
                    
                    # 1. Profile không còn not_yet=True
                    if not profile.not_yet:
                        should_cleanup = True
                        reason = "not_yet=False"
                    
                    # 2. Profile đã có actual_end_time
                    elif profile.actual_end_time:
                        should_cleanup = True
                        reason = "has_actual_end_time"
                    
                    # 3. start_time đã thay đổi
                    elif profile.start_time:
                        try:
                            scheduled_for = parse_datetime(scheduled_for_str)
                            if scheduled_for:
                                if timezone.is_naive(scheduled_for):
                                    scheduled_for = timezone.make_aware(scheduled_for, timezone.get_current_timezone())
                                
                                start_time = profile.start_time
                                if timezone.is_naive(start_time):
                                    start_time = timezone.make_aware(start_time, timezone.get_current_timezone())
                                
                                if start_time.tzinfo != pytz.UTC:
                                    start_time = start_time.astimezone(pytz.UTC)
                                if scheduled_for.tzinfo != pytz.UTC:
                                    scheduled_for = scheduled_for.astimezone(pytz.UTC)
                                
                                # Nếu chênh lệch > 1 giây, coi như đã thay đổi
                                if abs((start_time - scheduled_for).total_seconds()) > 1:
                                    should_cleanup = True
                                    reason = f"start_time_changed (current={start_time.isoformat()}, scheduled={scheduled_for.isoformat()})"
                        except Exception as parse_exc:
                            logger.warning(
                                "[SURVEILLANCE][AUTO] Không thể parse scheduled_for cho profile %s: %s",
                                profile.id,
                                parse_exc,
                            )
                    
                    # 4. Task đã quá hạn quá lâu (> 5 phút)
                    if not should_cleanup:
                        try:
                            scheduled_for = parse_datetime(scheduled_for_str)
                            if scheduled_for:
                                if timezone.is_naive(scheduled_for):
                                    scheduled_for = timezone.make_aware(scheduled_for, timezone.get_current_timezone())
                                
                                if scheduled_for.tzinfo != pytz.UTC:
                                    scheduled_for = scheduled_for.astimezone(pytz.UTC)
                                
                                # Nếu task đã quá hạn > 5 phút, cleanup
                                if scheduled_for < now - timedelta(minutes=5):
                                    should_cleanup = True
                                    reason = f"task_overdue (scheduled={scheduled_for.isoformat()}, now={now.isoformat()})"
                        except Exception:
                            pass
                    
                    if should_cleanup:
                        # Revoke task trong Celery
                        try:
                            current_app.control.revoke(task_id, terminate=False)
                            logger.info(
                                "[SURVEILLANCE][AUTO] Đã cleanup activation task %s cho profile %s (reason: %s)",
                                task_id,
                                profile.id,
                                reason,
                            )
                        except Exception as revoke_exc:
                            logger.warning(
                                "[SURVEILLANCE][AUTO] Không thể revoke activation task %s cho profile %s: %s",
                                task_id,
                                profile.id,
                                revoke_exc,
                            )
                        
                        # Xóa activation_scheduled khỏi metadata
                        metadata.pop("activation_scheduled", None)
                        profile.metadata = metadata
                        profile.save(update_fields=["metadata", "modified_on"])
                        cleaned_count += 1
                        
                except Exception as exc:
                    logger.warning(
                        "[SURVEILLANCE][AUTO] Lỗi khi cleanup activation task cho profile %s: %s",
                        profile.id if 'profile' in locals() else 'unknown',
                        exc,
                    )
                    continue
            
            if cleaned_count > 0:
                logger.info(
                    "[SURVEILLANCE][AUTO] Đã cleanup %s activation task(s) không hợp lệ",
                    cleaned_count,
                )
        except Exception as exc:
            logger.exception("[SURVEILLANCE][AUTO] Lỗi khi cleanup invalid activation tasks: %s", exc)


