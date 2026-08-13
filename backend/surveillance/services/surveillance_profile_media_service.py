import logging
from typing import Optional, Tuple

from asgiref.sync import sync_to_async
from django.db.models import Q
from django.utils import timezone

from config import settings
from stream_monitors.models import StreamMonitor
from surveillance.models import SurveillanceProfile, SurveillanceProfileDrone


logger = logging.getLogger(__name__)


class SurveillanceProfileMediaService:
    """
    Central place to persist media paths (video_path / analysis_path) onto SurveillanceProfileDrone.

    - video_path is saved when recording is stopped (record-only mode is allowed).
    - analysis_path is saved only when detection/analysis mode is enabled (requires detect flow).
    - Paths are stored as FULL URLs (legacy behavior).
    """

    @staticmethod
    def build_media_url(raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        s = str(raw).strip()
        if not s:
            return None
        if s.startswith("http://") or s.startswith("https://"):
            return s
        return f"https://{settings.MINIO_ENDPOINT}/{settings.MINIO_STORAGE_MEDIA_BUCKET_NAME}/{s.lstrip('/')}"

    @staticmethod
    def _resolve_profile_drone_for_stream_monitor(stream_monitor_id: str) -> Optional[SurveillanceProfileDrone]:
        """
        Find the most relevant in-progress profile assignment for the given stream monitor.
        This mirrors existing behavior: pick the first matching assignment among in-progress profiles.
        """
        stream_monitor = StreamMonitor.objects.select_related("drone").filter(code=stream_monitor_id).first()
        if not stream_monitor or not stream_monitor.drone:
            return None
        in_progress_profiles = list(SurveillanceProfile.objects.filter(status__code="in_progress"))
        if not in_progress_profiles:
            return None
        return (
            SurveillanceProfileDrone.objects.filter(device=stream_monitor.drone, profile__in=in_progress_profiles)
            .select_related("profile", "device")
            .first()
        )

    @staticmethod
    def save_recording_result_for_profile_drone(profile_drone_id: int, object_path: Optional[str]) -> bool:
        """
        Persist video_path (FULL URL) onto a specific assignment.
        """
        video_url = SurveillanceProfileMediaService.build_media_url(object_path)
        if not video_url:
            return False
        updated = SurveillanceProfileDrone._base_manager.filter(id=profile_drone_id).update(
            video_path=video_url,
            modified_on=timezone.now(),
        )
        return bool(updated)

    @staticmethod
    def save_detection_result_for_profile_drone(
        profile_drone_id: int,
        *,
        object_path: Optional[str] = None,
        analysis_path: Optional[str] = None,
    ) -> bool:
        """
        Persist analysis_path (FULL URL) and optionally video_path onto a specific assignment.
        """
        video_url = SurveillanceProfileMediaService.build_media_url(object_path)
        analysis_url = SurveillanceProfileMediaService.build_media_url(analysis_path)

        update_fields = {"modified_on": timezone.now()}
        if video_url:
            update_fields["video_path"] = video_url
        if analysis_url:
            update_fields["analysis_path"] = analysis_url

        if len(update_fields) == 1:
            return False

        updated = SurveillanceProfileDrone.objects.filter(id=profile_drone_id).update(**update_fields)
        return bool(updated)

    @staticmethod
    def save_recording_result_for_stream_monitor(stream_monitor_id: str, object_path: Optional[str]) -> bool:
        """
        Persist video_path for the matching in-progress assignment of this stream monitor.
        """
        profile_drone = SurveillanceProfileMediaService._resolve_profile_drone_for_stream_monitor(stream_monitor_id)
        if not profile_drone:
            return False
        return SurveillanceProfileMediaService.save_recording_result_for_profile_drone(profile_drone.id, object_path)

    @staticmethod
    def save_detection_result_for_stream_monitor(
        stream_monitor_id: str,
        *,
        object_path: Optional[str] = None,
        analysis_path: Optional[str] = None,
    ) -> bool:
        """
        Persist analysis_path (and optionally video_path) for the matching in-progress assignment of this stream monitor.
        """
        profile_drone = SurveillanceProfileMediaService._resolve_profile_drone_for_stream_monitor(stream_monitor_id)
        if not profile_drone:
            return False
        return SurveillanceProfileMediaService.save_detection_result_for_profile_drone(
            profile_drone.id,
            object_path=object_path,
            analysis_path=analysis_path,
        )


