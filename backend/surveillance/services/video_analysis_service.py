import logging
from core.file_management.models import UserMediaFile
from core.user.models import CoreUser, UserGroup
from django.utils import timezone
from django.db.models import F, Q
from typing import Optional
from asgiref.sync import sync_to_async
from stream_monitors.models import StreamMonitor
from surveillance.models import SurveillanceProfile, SurveillanceProfileDrone, VideoAnalysis
from config import settings
from core.middleware.refresh_token import get_current_request

logger = logging.getLogger(__name__)


class VideoAnalysisService:
    @staticmethod
    def create_video_analysis(profile_device: SurveillanceProfileDrone, 
                              stream_monitor: StreamMonitor, 
                              video_path: str, 
                              analysis_path: str, 
                              created_user: CoreUser,
                              group: Optional[UserGroup] = None):
        logger.info(f"🎬 [CREATE_VIDEO_ANALYSIS] ===== START =====")
        logger.info(f"🎬 [CREATE_VIDEO_ANALYSIS] profile_device={profile_device.id if profile_device else None}, stream_monitor={stream_monitor.id if stream_monitor else None}, video_path={video_path}, analysis_path={analysis_path}, user={created_user.username if created_user else None}")
        
        try:
            if not group and created_user:
                # Explicitly fetch userprofilelink to avoid lazy loading in async context
                try:
                    from core.user.models import UserProfileLink
                    profile_link = UserProfileLink._base_manager.select_related('group').filter(user=created_user).first()
                    if profile_link and profile_link.group:
                        group = profile_link.group
                except Exception as e:
                    logger.warning(f"⚠️ [CREATE_VIDEO_ANALYSIS] Could not fetch group from user profile: {e}")
                    group = None
                
            # create add video data to created instance
            logger.info(f"🎬 [CREATE_VIDEO_ANALYSIS] Creating UserMediaFile with video_path={video_path}")
            if not video_path:
                error_msg = "video_path is None or empty, cannot create UserMediaFile"
                logger.error(f"❌ [CREATE_VIDEO_ANALYSIS] {error_msg}")
                raise ValueError(error_msg)
            
            file_instance = UserMediaFile()
            file_instance._is_avatar_upload = False
            file_instance.file_url = f"/{settings.MINIO_STORAGE_MEDIA_BUCKET_NAME}/{video_path}"
            file_instance.is_minio = True  # Should be True for MinIO files
            file_instance.created_by = created_user
            file_instance.modified_by = created_user
            file_instance.group = group
            file_instance.save()
            logger.info(f"✅ [CREATE_VIDEO_ANALYSIS] UserMediaFile created: id={file_instance.id}, file_url={file_instance.file_url}")
            
            logger.info(f"🎬 [CREATE_VIDEO_ANALYSIS] Creating VideoAnalysis object")
                
            video_analysis = VideoAnalysis.objects.create(
                profile_device=profile_device,
                stream_monitor=stream_monitor,
                video_path=f"https://{settings.MINIO_ENDPOINT}/{settings.MINIO_STORAGE_MEDIA_BUCKET_NAME}/{video_path}",
                analysis_path=f"{settings.MINIO_ENDPOINT}/{settings.MINIO_STORAGE_MEDIA_BUCKET_NAME}/{analysis_path}" if analysis_path else None,
                created_at=timezone.now(),
                updated_at=timezone.now(),
                video_file = file_instance,
                created_by = created_user,
                modified_by = created_user,
                group = group,
                drone_name = stream_monitor.drone.name if stream_monitor and stream_monitor.drone else None,
            )
            logger.info(f"✅ [CREATE_VIDEO_ANALYSIS] VideoAnalysis created: id={video_analysis.id}")
            
            if stream_monitor and stream_monitor.is_external:
                logger.info(f"🎬 [CREATE_VIDEO_ANALYSIS] Updating VideoAnalysis with external stream_monitor data")
                video_analysis.drone_name = stream_monitor.external_drone_name
                video_analysis.operator_name = stream_monitor.external_operation_name
                video_analysis.register_number = stream_monitor.external_registration_number
                video_analysis.manufacturer = stream_monitor.external_manufacturer
                video_analysis.flight_distance = stream_monitor.external_flight_distance
                video_analysis.flight_time = stream_monitor.external_flight_time
                video_analysis.flight_altitude = stream_monitor.external_flight_altitude
                video_analysis.start_point_x = stream_monitor.external_start_point_x
                video_analysis.start_point_y = stream_monitor.external_start_point_y
                video_analysis.end_point_x = stream_monitor.external_end_point_x
                video_analysis.end_point_y = stream_monitor.external_end_point_y
                video_analysis.start_time = stream_monitor.external_start_time
                video_analysis.end_time = stream_monitor.external_end_time
                video_analysis.remark = stream_monitor.external_remark
                video_analysis.save()
                logger.info(f"✅ [CREATE_VIDEO_ANALYSIS] VideoAnalysis updated with external data")
            else:
                if profile_device and profile_device.device:
                    logger.info(f"🎬 [CREATE_VIDEO_ANALYSIS] Updating VideoAnalysis with profile_device data")
                    video_analysis.drone_name = profile_device.device.name
                    video_analysis.operator_name = profile_device.profile.operator.username
                    video_analysis.register_number = profile_device.device.manufacturer_information.registration_number
                    # Lazy import to avoid circular import
                    if profile_device.profile and profile_device.profile.mission:
                        from surveillance.services.surveillance_profile_service import SurveillanceProfileService
                        total_distance = profile_device.profile.mission.get_numeric_value(SurveillanceProfileService.MEASUREMENT_TOTAL_DISTANCE)
                        if total_distance:
                            video_analysis.flight_distance = float(total_distance)
                        estimated_time = profile_device.profile.mission.get_numeric_value(SurveillanceProfileService.MEASUREMENT_ESTIMATED_TIME)
                        if estimated_time:
                            video_analysis.flight_time = int(estimated_time)
                    video_analysis.save()
                    logger.info(f"✅ [CREATE_VIDEO_ANALYSIS] VideoAnalysis updated with profile_device data")
                    if profile_device.start_waypoint:
                        video_analysis.start_point_x = profile_device.start_waypoint.latitude
                        video_analysis.start_point_y = profile_device.start_waypoint.longitude
                        video_analysis.save()
                    if profile_device.end_waypoint:
                        video_analysis.end_point_x = profile_device.end_waypoint.latitude
                        video_analysis.end_point_y = profile_device.end_waypoint.longitude
                        video_analysis.save()
                    if profile_device.profile.mission:
                        video_analysis.mission_name = profile_device.profile.mission.name
                        video_analysis.mission_id = profile_device.profile.mission.id
                        video_analysis.save()
            
            logger.info(f"✅ [CREATE_VIDEO_ANALYSIS] ===== COMPLETE =====")
            return video_analysis
        except Exception as e:
            logger.exception(f"❌ [CREATE_VIDEO_ANALYSIS] Error creating VideoAnalysis: {type(e).__name__}: {str(e)}")
            raise

    @staticmethod
    async def create_video_analysis_from_stream_monitor(stream_monitor_id: str, 
                                                        object_path: str, 
                                                        analysis_path: str, 
                                                        user: CoreUser,
                                                        group_id: Optional[str] = None):
        logger.info(f"🎬 [VIDEO_ANALYSIS] ===== START =====")
        logger.info(f"🎬 [VIDEO_ANALYSIS] stream_monitor_id={stream_monitor_id}, object_path={object_path}, analysis_path={analysis_path}, user={user.username if user else None}")
        
        def _get_stream_monitor():
            return StreamMonitor._base_manager.select_related('drone').filter(code=stream_monitor_id).first()
        
        def _get_in_progress_profiles():
            return list(SurveillanceProfile._base_manager.filter(status__code="in_progress"))
        
        def _get_profile_drone(device, profile_list):
            return SurveillanceProfileDrone._base_manager.select_related(
                'device', 
                'profile', 
                'profile__operator',
                'profile__mission',
                'start_waypoint', 
                'end_waypoint'
            ).filter(device=device, profile__in=profile_list).first()
        
        def _get_device_from_stream_monitor(stream_monitor):
            return stream_monitor.drone if stream_monitor else None
        
        def _get_group_by_id(group_id):
            try:
                return UserGroup._base_manager.get(id=group_id)
            except UserGroup.DoesNotExist:
                return None
        
        def _get_user(user_obj):
            """Ensure user is properly loaded from database to avoid lazy loading issues."""
            if user_obj and user_obj.pk:
                return CoreUser._base_manager.get(pk=user_obj.pk)
            return user_obj
        
        try:
            logger.info(f"🎬 [VIDEO_ANALYSIS] Fetching stream_monitor with code={stream_monitor_id}")
            # Properly load user object to avoid lazy loading issues
            user = await sync_to_async(_get_user)(user)
            stream_monitor = await sync_to_async(_get_stream_monitor)()
            group = await sync_to_async(_get_group_by_id)(group_id) if group_id else None
            
            if stream_monitor:
                logger.info(f"✅ [VIDEO_ANALYSIS] Found stream_monitor: id={stream_monitor.id}, code={stream_monitor.code}, drone={stream_monitor.drone.name if stream_monitor.drone else None}")
                
                device = await sync_to_async(_get_device_from_stream_monitor)(stream_monitor)
                logger.info(f"🎬 [VIDEO_ANALYSIS] Device: {device.name if device else None}")
                
                logger.info(f"🎬 [VIDEO_ANALYSIS] Fetching in_progress profiles")
                in_progress_profile_list = await sync_to_async(_get_in_progress_profiles)()
                logger.info(f"✅ [VIDEO_ANALYSIS] Found {len(in_progress_profile_list)} in_progress profiles")
                
                profile_drone = await sync_to_async(_get_profile_drone)(device, in_progress_profile_list)
                if profile_drone:
                    logger.info(f"✅ [VIDEO_ANALYSIS] Found profile_drone: id={profile_drone.id}, profile_id={profile_drone.profile.id if profile_drone.profile else None}")
                    logger.info(f"🎬 [VIDEO_ANALYSIS] Creating VideoAnalysis with profile_drone")
                    video_analysis = await sync_to_async(VideoAnalysisService.create_video_analysis)(
                        profile_drone, stream_monitor, object_path, analysis_path, user
                    )
                    logger.info(f"✅ [VIDEO_ANALYSIS] VideoAnalysis created successfully: id={video_analysis.id}")
                    return video_analysis
                else:
                    logger.warning(f"⚠️ [VIDEO_ANALYSIS] No profile_drone found, creating VideoAnalysis without profile_drone")
                    logger.info(f"🎬 [VIDEO_ANALYSIS] Creating VideoAnalysis without profile_drone")
                    video_analysis = await sync_to_async(VideoAnalysisService.create_video_analysis)(None, stream_monitor, object_path, analysis_path, user, group)
                    logger.info(f"✅ [VIDEO_ANALYSIS] VideoAnalysis created successfully: id={video_analysis.id}")
                    return video_analysis
            else:
                logger.warning(f"⚠️ [VIDEO_ANALYSIS] StreamMonitor with code={stream_monitor_id} not found")
                return None
        except Exception as e:
            logger.exception(f"❌ [VIDEO_ANALYSIS] Error creating VideoAnalysis: {type(e).__name__}: {str(e)}")
            raise

    @staticmethod
    async def create_video_analysis_from_profile_drone(
        profile_drone_id: int,
        stream_monitor_id: str,
        object_path: str,
        analysis_path: str,
        user: CoreUser,
        group_id: Optional[str] = None,
        **_kwargs,
    ):
        """
        Deterministically create VideoAnalysis for a specific SurveillanceProfileDrone.

        This is the safe option when the profile might no longer be in_progress (e.g. completed)
        by the time async/background detection finishes.
        """
        logger.info(f"🎬 [VIDEO_ANALYSIS_BY_PROFILE_DRONE] ===== START =====")
        logger.info(
            "🎬 [VIDEO_ANALYSIS_BY_PROFILE_DRONE] profile_drone_id=%s stream_monitor_id=%s object_path=%s analysis_path=%s user=%s group_id=%s",
            profile_drone_id,
            stream_monitor_id,
            object_path,
            analysis_path,
            user.username if user else None,
            group_id,
        )

        def _get_stream_monitor():
            return StreamMonitor._base_manager.select_related('drone').filter(code=stream_monitor_id).first()

        def _get_profile_drone_by_id():
            return (
                SurveillanceProfileDrone._base_manager.select_related(
                    'device',
                    'profile',
                    'profile__operator',
                    'profile__mission',
                    'start_waypoint',
                    'end_waypoint',
                )
                .filter(id=int(profile_drone_id))
                .first()
            )

        def _get_group_by_id(gid: Optional[str]):
            if not gid:
                return None
            try:
                return UserGroup._base_manager.get(id=gid)
            except UserGroup.DoesNotExist:
                return None

        def _get_user(user_obj):
            """Ensure user is properly loaded from database to avoid lazy loading issues."""
            if user_obj and user_obj.pk:
                return CoreUser._base_manager.get(pk=user_obj.pk)
            return user_obj

        try:
            user = await sync_to_async(_get_user)(user)
            stream_monitor = await sync_to_async(_get_stream_monitor)()
            profile_drone = await sync_to_async(_get_profile_drone_by_id)()
            group = await sync_to_async(_get_group_by_id)(group_id) if group_id else None

            if not stream_monitor:
                logger.warning(
                    "⚠️ [VIDEO_ANALYSIS_BY_PROFILE_DRONE] StreamMonitor with code=%s not found",
                    stream_monitor_id,
                )
                return None
            if not profile_drone:
                logger.warning(
                    "⚠️ [VIDEO_ANALYSIS_BY_PROFILE_DRONE] SurveillanceProfileDrone id=%s not found",
                    profile_drone_id,
                )
                return None

            video_analysis = await sync_to_async(VideoAnalysisService.create_video_analysis)(
                profile_drone,
                stream_monitor,
                object_path,
                analysis_path,
                user,
                group,
            )
            logger.info(
                "✅ [VIDEO_ANALYSIS_BY_PROFILE_DRONE] VideoAnalysis created successfully: id=%s profile_id=%s",
                video_analysis.id if video_analysis else None,
                profile_drone.profile_id if profile_drone else None,
            )
            return video_analysis
        except Exception as e:
            logger.exception(
                "❌ [VIDEO_ANALYSIS_BY_PROFILE_DRONE] Error creating VideoAnalysis: %s: %s",
                type(e).__name__,
                str(e),
            )
            raise

    def get_video_analysis():
        stream_monitor = StreamMonitor.objects.all()
        video_analysis = VideoAnalysis.objects.filter(
            Q(stream_monitor__isnull=True) | Q(stream_monitor__in=stream_monitor)
        ).filter(video_path__isnull=False, analysis_path__isnull=False).order_by("-id").annotate(stream_monitor__name=F('stream_monitor__name'))
        return video_analysis

    def get_video_analysis_detail(video_analysis_id: int):
        video_analysis = VideoAnalysis.objects.get(id=video_analysis_id)
        if video_analysis.profile_device and video_analysis.profile_device.profile:
            video_analysis.start_time = video_analysis.profile_device.profile.actual_start_time if video_analysis.profile_device.profile.actual_start_time else video_analysis.profile_device.profile.start_time
            video_analysis.end_time = video_analysis.profile_device.profile.actual_end_time if video_analysis.profile_device.profile.actual_end_time else video_analysis.profile_device.profile.estimated_end_time
            video_analysis.save()
        return video_analysis